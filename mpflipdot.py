"""MicroPython driver for Hanover Displays flip-dot signs (RS485, 4800 baud)."""

try:
    from time import ticks_ms, ticks_diff, sleep_ms
except ImportError:  # CPython, used by the unit tests
    from time import monotonic, sleep

    def ticks_ms():
        return int(monotonic() * 1000)

    def ticks_diff(a, b):
        return a - b

    def sleep_ms(ms):
        sleep(ms / 1000)


BAUD = 4800
_HEX = b"0123456789ABCDEF"
_CMD_WRITE = 1
_CMD_TEST_START = 3
_CMD_TEST_STOP = 12


def open_uart(uart_id=0, tx=0, rx=1):
    """Create a UART at the sign's baud rate on the given pins.

    Defaults match channel 0 of the Waveshare Pico-2CH-RS485
    (UART0: GP0/GP1); channel 1 is open_uart(1, tx=4, rx=5).
    """
    from machine import UART, Pin

    return UART(uart_id, baudrate=BAUD, bits=8, parity=None, stop=1, tx=Pin(tx), rx=Pin(rx))


def _hex(out, value):
    out.append(_HEX[value >> 4])
    out.append(_HEX[value & 15])


def _packet(cmd, address, data=b""):
    """Build a complete packet. data is raw bytes, sent as ASCII hex preceded by its length."""
    p = bytearray(b"\x02")
    p.append(_HEX[cmd])
    p.append(_HEX[address])
    if data:
        _hex(p, len(data) & 0xFF)
        for b in data:
            _hex(p, b)
    p.append(3)
    _hex(p, -sum(p[1:]) & 0xFF)  # two's complement of everything after STX
    return p


class FlipDot:
    def __init__(self, uart, address=1, width=84, height=7, flip=False, auto_show=True, de_pin=None, row_offset=0, min_gap_ms=300, skip_unchanged=True):
        """uart: configured UART (see open_uart). address: 0-15.
        flip: sign is mounted upside-down. auto_show: send the frame after every change.
        de_pin: optional Pin to drive RS485 DE/RE for adapters without automatic direction.
        row_offset: bit position of the top row in each column (1 for the 20x14 test sign).
        min_gap_ms: minimum time between sends; later sends wait (0 turns this off). The
        20x14 test sign skipped frames sent 200 ms apart but kept up at 300 ms.
        skip_unchanged: show() sends nothing if the frame is identical to the last one sent
        (show(force=True) always sends, e.g. to repair a frame the sign dropped).
        """
        if not 0 <= address <= 15:
            raise ValueError("address 0-15")
        self._bpc = (height + row_offset + 7) // 8  # bytes per column
        if width < 1 or height < 1 or width * self._bpc > 255:
            raise ValueError("bad size")
        self.uart = uart
        self.address = address
        self.width = width
        self.height = height
        self.flip = flip
        self.row_offset = row_offset
        self.auto_show = auto_show
        self.de_pin = de_pin
        self.min_gap_ms = min_gap_ms
        self.skip_unchanged = skip_unchanged
        self._last = None
        self._sent = None  # the last frame sent, to spot repeats
        self._buf = bytearray(width * self._bpc)  # wire layout: column-major, bit0 = top row

    def _write(self, packet):
        if self.min_gap_ms and self._last is not None:
            wait = self.min_gap_ms - ticks_diff(ticks_ms(), self._last)
            if wait > 0:
                sleep_ms(wait)
        self._last = ticks_ms()
        if self.de_pin:
            self.de_pin.value(1)
        self.uart.write(packet)
        if self.de_pin:
            self.uart.flush()
            self.de_pin.value(0)

    def _pos(self, x, y):
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError("out of range")
        if self.flip:
            x = self.width - 1 - x
            y = self.height - 1 - y
        y += self.row_offset
        return x * self._bpc + (y >> 3), 1 << (y & 7)

    def _changed(self):
        if self.auto_show:
            self.show()

    def show(self, force=False):
        """Send the current frame to the sign (nothing if it's unchanged since the last send, unless force)."""
        buf = self._buf
        p = 0 if self.row_offset else self.height  # first bit that is not a visible row
        if p < 8 * self._bpc and not any(buf):
            # the sign ignores all-zero frames, so set a bit that lights no dot
            buf = bytearray(buf)
            buf[p >> 3] |= 1 << (p & 7)
        if self.skip_unchanged and not force and self._sent == buf:
            return
        self._write(_packet(_CMD_WRITE, self.address, buf))
        self._sent = bytes(buf)

    def clear(self):
        """All dots off."""
        for i in range(len(self._buf)):
            self._buf[i] = 0
        self._changed()

    def fill(self):
        """All dots on."""
        v = ((1 << self.height) - 1) << self.row_offset
        for x in range(self.width):
            for b in range(self._bpc):
                self._buf[x * self._bpc + b] = (v >> (8 * b)) & 0xFF
        self._changed()

    def get_pixel(self, x, y):
        i, m = self._pos(x, y)
        return bool(self._buf[i] & m)

    def _set(self, x, y, on):
        i, m = self._pos(x, y)
        if on:
            self._buf[i] |= m
        else:
            self._buf[i] &= ~m

    def set_pixel(self, x, y, on=True):
        """Set one dot; all others keep their state."""
        self._set(x, y, on)
        self._changed()

    def set_pixels(self, pixels):
        """pixels: iterable of (x, y, on). One frame is sent for the whole batch."""
        for x, y, on in pixels:
            self._set(x, y, on)
        self._changed()

    def test(self, on=True):
        """Start or stop the manufacturer's test mode (broadcast to all signs)."""
        self._write(_packet(_CMD_TEST_START if on else _CMD_TEST_STOP, 0))
        self._sent = None  # test mode changes what the sign shows, so the next frame must be sent
