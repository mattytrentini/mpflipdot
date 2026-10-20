import framebuf
from mpflipdot import FlipDot
from test_mpflipdot import FakeUART, payload
from mpflipdot_draw import line


class Canvas(framebuf.FrameBuffer):
    def __init__(self, width=40, height=40):
        self.width = width
        self.height = height
        self.buffer = bytearray(width * ((height + 7) // 8))
        super().__init__(self.buffer, width, height, framebuf.MONO_VLSB)


def pixels(sign):
    return {(x, y) for y in range(sign.height) for x in range(sign.width) if sign.pixel(x, y)}


def shape(fn, *args, **kwargs):
    sign = Canvas()
    fn(sign, *args, **kwargs)
    return pixels(sign)


def test_line_axes_and_diagonals():
    assert shape(line, 2, 3, 5, 3) == {(x, 3) for x in range(2, 6)}
    assert shape(line, 4, 1, 4, 3) == {(4, y) for y in range(1, 4)}
    assert shape(line, 7, 7, 7, 7) == {(7, 7)}
    assert shape(line, 0, 0, 3, 3) == {(i, i) for i in range(4)}
    assert shape(line, 3, 0, 0, 3) == {(3 - i, i) for i in range(4)}
    for x, y in ((19, 13), (0, 13), (19, 0), (7, 2), (3, 12)):
        drawn = shape(line, 0, 0, x, y)
        assert (0, 0) in drawn and (x, y) in drawn
        assert len(drawn) == max(x, y) + 1


def test_line_thickness_and_clipping():
    assert shape(line, 2, 5, 4, 5, width=3) == {(x, y) for x in (2, 3, 4) for y in (4, 5, 6)}
    assert shape(line, 5, 2, 5, 4, width=2) == {(x, y) for x in (5, 6) for y in (2, 3, 4)}
    assert shape(line, -5, 3, 45, 3) == {(x, 3) for x in range(40)}
    assert shape(line, -9, -9, -2, -2) == set()
    assert shape(line, 0, 0, 5, 0, width=3) == {(x, y) for x in range(6) for y in (0, 1)}


def test_erasing_and_explicit_show():
    uart = FakeUART()
    sign = FlipDot(uart, width=20, height=14, row_offset=1, min_gap_ms=0)
    line(sign, 2, 5, 4, 5, width=3)
    assert pixels(sign) == {(x, y) for x in (2, 3, 4) for y in (4, 5, 6)}
    line(sign, 2, 5, 4, 5, width=3, on=False)
    assert not pixels(sign)
    assert uart.sent == []
    line(sign, 0, 0, 2, 0, width=2)
    sign.show()
    assert len(uart.sent) == 1
    assert payload(uart.sent[0]) == b"\x06\x00" * 3 + b"\x00" * 34


def test_invalid_line_width():
    try:
        line(Canvas(), 0, 0, 1, 1, width=0)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid line width accepted")
