"""Monochrome framebuf driver for Hanover flip-dot signs (RS485, 4800 baud)."""

import framebuf
from time import ticks_ms, ticks_diff, sleep_ms


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


class FlipDot(framebuf.FrameBuffer):
    """A logical monochrome canvas; call show() to update the physical sign."""

    def __init__(
        self, uart, address=1, width=84, height=7, flip=False, de_pin=None,
        row_offset=0, min_gap_ms=None, skip_unchanged=True, quiet_ms=100,
    ):
        """uart: configured UART (see open_uart). address: 0-15.
        flip: sign is mounted upside-down; drawing coordinates stay top-left.
        de_pin: optional Pin to drive RS485 DE/RE for adapters without automatic direction.
        row_offset: bit position of the top row in each column (1 for the 20x14 test sign).
        min_gap_ms: None (the default) waits for the previous frame to finish sending plus quiet_ms
        of silence, so the gap grows with the frame size. A number is a fixed gap from the start of
        one send to the start of the next (0 turns the guard off). On the 20x14 test sign (88 byte
        frames, ~183 ms to send) 200 ms apart dropped frames and 300 ms was fine.
        quiet_ms: silence the sign needs after a frame (a guess of 100 ms from the 20x14 sign).
        skip_unchanged: show() sends nothing if the frame is identical to the last one sent
        (show(force=True) always sends, e.g. to repair a frame the sign dropped).
        """
        if not 0 <= address <= 15:
            raise ValueError("address 0-15")
        if row_offset < 0:
            raise ValueError("row_offset must be non-negative")
        self._bpc = (height + row_offset + 7) // 8  # bytes per column
        if width < 1 or height < 1 or width * self._bpc > 255:
            raise ValueError("bad size")
        self.uart = uart
        self.address = address
        self.width = width
        self.height = height
        self.flip = flip
        self.row_offset = row_offset
        self.de_pin = de_pin
        self.min_gap_ms = min_gap_ms
        self.quiet_ms = quiet_ms
        self.skip_unchanged = skip_unchanged
        self._last = None
        self._last_tx = 0  # ms the previous packet took to send
        self._sent = None  # the last frame sent, to spot repeats
        self._pages = (height + 7) // 8
        self.buffer = bytearray(width * self._pages)
        self._wire = bytearray(width * self._bpc)
        super().__init__(self.buffer, width, height, framebuf.MONO_VLSB)

    def _write(self, packet):
        gap = self._last_tx + self.quiet_ms if self.min_gap_ms is None else self.min_gap_ms
        if gap and self._last is not None:
            wait = gap - ticks_diff(ticks_ms(), self._last)
            if wait > 0:
                sleep_ms(wait)
        self._last = ticks_ms()
        self._last_tx = (len(packet) * 10 * 1000 + BAUD - 1) // BAUD  # 10 bits a byte on the wire, rounded up
        if self.de_pin:
            self.de_pin.value(1)
        self.uart.write(packet)
        if self.de_pin:
            self.uart.flush()
            self.de_pin.value(0)

    def _pack(self):
        """Reorder eight-row bands into wire columns, without changing the canvas."""
        buf = self._wire
        for i in range(len(buf)):
            buf[i] = 0
        for page in range(self._pages):
            # Mask the partial final band before rotating or shifting it.
            mask = (1 << min(8, self.height - page * 8)) - 1
            top = self.height - (page + 1) * 8 if self.flip else page * 8
            top += self.row_offset
            byte = top >> 3
            shift = top & 7
            for x in range(self.width):
                value = self.buffer[page * self.width + x] & mask
                column = x
                if self.flip:
                    column = self.width - 1 - x
                    value = ((value & 0x55) << 1) | ((value >> 1) & 0x55)
                    value = ((value & 0x33) << 2) | ((value >> 2) & 0x33)
                    value = (value << 4 | value >> 4) & 0xFF
                base = column * self._bpc
                # A rotated partial band can begin above row zero (byte == -1).
                if byte >= 0:
                    buf[base + byte] |= (value << shift) & 0xFF
                if shift and byte + 1 < self._bpc:
                    buf[base + byte + 1] |= value >> (8 - shift)

    def show(self, force=False):
        """Send the current frame to the sign (nothing if it's unchanged since the last send, unless force)."""
        self._pack()
        buf = self._wire
        p = 0 if self.row_offset else self.height  # first bit that is not a visible row
        if p < 8 * self._bpc and not any(buf):
            # the sign ignores all-zero frames, so set a bit that lights no dot
            buf[p >> 3] |= 1 << (p & 7)
        if self.skip_unchanged and not force and self._sent == buf:
            return
        self._write(_packet(_CMD_WRITE, self.address, buf))
        self._sent = bytes(buf)


    def test(self, on=True):
        """Start or stop the manufacturer's test mode (broadcast to all signs)."""
        self._write(_packet(_CMD_TEST_START if on else _CMD_TEST_STOP, 0))
        self._sent = None  # test mode changes what the sign shows, so the next frame must be sent
