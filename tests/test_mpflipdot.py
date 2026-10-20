"""Driver behavior exercised with MicroPython's real framebuf implementation."""

import framebuf
import mpflipdot
from mpflipdot import FlipDot


class FakeUART:
    def __init__(self):
        self.sent = []

    def write(self, data):
        self.sent.append(bytes(data))


def make(**kw):
    kw.setdefault("min_gap_ms", 0)
    uart = FakeUART()
    return uart, FlipDot(uart, **kw)


def payload(packet):
    assert packet[0] == 2 and packet[-3] == 3
    assert int(packet[-2:], 16) == (-sum(packet[1:-2]) & 0xFF)
    data = bytes(int(packet[i:i + 2], 16) for i in range(5, len(packet) - 3, 2))
    assert int(packet[3:5], 16) == len(data)
    return data


def test_drawing_is_batched_and_native_blit_uses_canvas():
    uart, sign = make(width=4, height=9, address=5)
    sign.fill(0)
    sign.line(0, 0, 3, 0, 1)
    sign.rect(1, 1, 2, 2, 1, True)
    icon = framebuf.FrameBuffer(bytearray(b"\x01\x01"), 1, 9, framebuf.MONO_VLSB)
    sign.blit(icon, 0, 0)
    sign.pixel(3, 0, 0)
    assert uart.sent == []
    sign.show()
    assert uart.sent[0][1:3] == b"15"
    assert payload(uart.sent[0]) == b"\x01\x01\x07\x00\x07\x00\x00\x00"
    # The sign itself must also be usable as a source by the native blitter.
    copied = framebuf.FrameBuffer(bytearray(8), 4, 9, framebuf.MONO_VLSB)
    copied.blit(sign, 0, 0)
    assert copied.pixel(0, 8) == 1 and copied.pixel(2, 2) == 1
    assert copied.pixel(3, 0) == 0


def test_column_order_rotation_offsets_and_partial_bands():
    # Exercise both sides of byte boundaries, including offsets that span bytes.
    for height in (1, 7, 8, 9, 14, 15, 16, 17):
        for offset in (0, 1, 7, 8, 9):
            for flip in (False, True):
                width = 3
                uart, sign = make(width=width, height=height, row_offset=offset, flip=flip)
                bpc = (height + offset + 7) // 8
                expected = bytearray(width * bpc)
                for x in range(width):
                    for y in range(height):
                        on = (x * 3 + y * 5) % 7 < 2
                        sign.pixel(x, y, on)
                        if on:
                            px = width - 1 - x if flip else x
                            py = (height - 1 - y if flip else y) + offset
                            expected[px * bpc + (py >> 3)] |= 1 << (py & 7)
                # Dirty native padding must never escape onto the wire.
                if height & 7:
                    for x in range(width):
                        sign.buffer[(height >> 3) * width + x] |= (0xFF << (height & 7)) & 0xFF
                before = bytes(sign.buffer)
                sign.show()
                assert payload(uart.sent[0]) == expected, (height, offset, flip)
                assert sign.buffer == before
                assert sign.pixel(0, 0) == 1


def test_fill_masks_nonvisible_rows_and_blanking_preserves_canvas():
    for width, height, offset in ((84, 7, 0), (20, 14, 1), (2, 9, 0)):
        uart, sign = make(width=width, height=height, row_offset=offset)
        sign.fill(1)
        sign.show()
        bpc = (height + offset + 7) // 8
        column = ((1 << height) - 1) << offset
        expected = bytes((column >> (8 * b)) & 0xFF for b in range(bpc)) * width
        assert payload(uart.sent[-1]) == expected
        sign.fill(0)
        sign.show()
        blank = bytearray(width * bpc)
        bit = 0 if offset else height
        blank[bit >> 3] = 1 << (bit & 7)
        assert payload(uart.sent[-1]) == blank
        assert not any(sign.buffer)
        sign.show(force=True)
        assert uart.sent[-1] == uart.sent[-2]
        sign.pixel(0, 0, 1)
        sign.show()
        assert payload(uart.sent[-1])[0] == 1 << offset


def test_exact_byte_height_has_no_invisible_blank_bit():
    uart, sign = make(width=2, height=8)
    sign.fill(1)
    sign.show()
    sign.fill(0)
    sign.show()
    # No spare row exists: do not invent a bit that would light a visible dot.
    assert payload(uart.sent[-1]) == b"\x00\x00"
    assert not any(sign.buffer)


def test_repeat_force_opt_out_and_test_mode_invalidation():
    uart, sign = make(width=4, height=7)
    sign.pixel(1, 1, 1)
    sign.show()
    first = uart.sent[0]
    sign.pixel(1, 1, 1)
    sign.show()
    assert uart.sent == [first]
    sign.show(force=True)
    assert uart.sent == [first, first]
    sign.test(True)
    sign.test(False)
    sign.show()
    assert uart.sent == [first, first, b"\x0230\x039A", b"\x02C0\x038A", first]
    sign.fill(0)
    sign.show()
    sign.show()
    assert len(uart.sent) == 6
    other_uart, other = make(width=1, height=7, skip_unchanged=False)
    other.show()
    other.show()
    assert len(other_uart.sent) == 2 and other_uart.sent[0] == other_uart.sent[1]


class Clock:
    def __enter__(self):
        self.now = 1000
        self.sleeps = []
        self.real = mpflipdot.ticks_ms, mpflipdot.sleep_ms
        mpflipdot.ticks_ms = lambda: self.now
        mpflipdot.sleep_ms = self.sleep
        return self

    def sleep(self, ms):
        self.sleeps.append(ms)
        self.now += ms

    def __exit__(self, *args):
        mpflipdot.ticks_ms, mpflipdot.sleep_ms = self.real


def test_automatic_gap_depends_on_previous_packet_and_quiet_time():
    for width, height, offset, quiet, gap in ((20, 14, 1, 100, 284), (84, 7, 0, 100, 467), (20, 14, 1, 50, 234)):
        with Clock() as clock:
            _, sign = make(width=width, height=height, row_offset=offset, min_gap_ms=None, quiet_ms=quiet)
            sign.show()
            sign.show()  # Skipped frames must not wait or advance the send clock.
            assert clock.sleeps == []
            sign.show(force=True)
            assert clock.sleeps == [gap]
            clock.now += gap + 1
            sign.show(force=True)
            assert clock.sleeps == [gap]
    with Clock() as clock:
        _, sign = make(min_gap_ms=None)
        sign.test(True)  # Six-byte packet takes 13 ms, then 100 ms quiet.
        sign.show()
        assert clock.sleeps == [113]


def test_fixed_gap_is_start_to_start_and_can_be_disabled():
    with Clock() as clock:
        _, sign = make(width=4, height=7, min_gap_ms=300)
        sign.show()
        clock.now += 100
        sign.pixel(0, 0, 1)
        sign.show()
        clock.now += 500
        sign.pixel(1, 0, 1)
        sign.show()
        assert clock.sleeps == [200]
    with Clock() as clock:
        _, sign = make(min_gap_ms=0)
        sign.show()
        sign.show(force=True)
        assert clock.sleeps == []


def test_direction_control_surrounds_write_and_flush():
    events = []

    class UART:
        def write(self, packet):
            events.append(("write", bytes(packet)))

        def flush(self):
            events.append("flush")

    class Pin:
        def value(self, value):
            events.append(value)

    sign = FlipDot(UART(), width=1, height=7, de_pin=Pin(), min_gap_ms=0)
    sign.pixel(0, 0, 1)
    sign.show()
    assert events[0] == 1 and events[2:] == ["flush", 0]
    assert payload(events[1][1]) == b"\x01"


def test_packet_size_limit_includes_row_offset():
    for options in ({"address": 16}, {"address": -1}, {"width": 0}, {"height": 0}, {"row_offset": -1}, {"width": 128, "height": 8, "row_offset": 1}):
        try:
            make(**options)
        except ValueError:
            pass
        else:
            raise AssertionError(options)
    uart, sign = make(width=255, height=8)
    sign.fill(1)
    sign.show()
    assert payload(uart.sent[0]) == b"\xFF" * 255
