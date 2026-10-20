from mpflipdot import FlipDot
from mpflipdot_text import text, text_centered, text_width, scroll
from test_draw import Canvas, pixels
from test_mpflipdot import FakeUART, payload


def dots(string, x=0, y=0, scale=1, width=100, height=40):
    sign = Canvas(width, height)
    text(sign, string, x, y, scale)
    return pixels(sign)


def art(string):
    drawn = dots(string)
    return ["".join("#" if (x, y) in drawn else "." for x in range(text_width(string))) for y in range(7)]


def test_font_visible_glyphs():
    assert art("L") == ["#...."] * 6 + ["#####"]
    assert art("T") == ["#####"] + ["..#.."] * 6
    assert art("H") == ["#...#"] * 3 + ["#####"] + ["#...#"] * 3
    assert art(".") == ["....."] * 5 + [".##.."] * 2
    assert art("|") == ["..#.."] * 7
    assert art("[") == ["".join(reversed(row)) for row in art("]")]
    assert art("(") == ["".join(reversed(row)) for row in art(")")]
    assert art("\\") == ["".join(reversed(row)) for row in art("/")]
    assert dots("0") == dots("O")
    assert not dots(" ")
    assert dots("hello 1") == dots("HELLO 1")
    assert dots("A~B") == dots("A B")
    assert dots("AéB") == dots("A B")


def test_text_position_spacing_and_scaling():
    base = dots("HI")
    assert dots("HI", 3, 4) == {(x+3, y+4) for x, y in base}
    assert dots("II") == dots("I") | {(x+6, y) for x, y in dots("I")}
    for scale in (2, 3):
        assert dots("AB", scale=scale) == {(x*scale+dx, y*scale+dy) for x, y in dots("AB") for dx in range(scale) for dy in range(scale)}
    assert [text_width(s) for s in ("", "A", "AB", "ABC")] == [0, 5, 11, 17]
    assert [text_width(s, 2) for s in ("", "A", "AB")] == [0, 10, 22]


def test_text_clipping():
    for string, x, y, scale in (("ABC", -4, -3, 1), ("ABC", 15, 10, 1), ("ABCDEFG", 0, 0, 1), ("A", -10, 0, 1), ("A", 25, 0, 1), ("A", 0, 20, 1), ("AB", -3, -5, 2)):
        expected = {(px+x, py+y) for px, py in dots(string, scale=scale) if 0 <= px+x < 20 and 0 <= py+y < 14}
        assert dots(string, x, y, scale, width=20, height=14) == expected


def test_centering_on_ink():
    for string, scale, expected in (("I", 1, (8, 10)), (".", 1, (9, 10)), ("!", 1, (9, 9)), ("H", 1, (7, 11)), ("I", 2, (7, 12)), ("ABC", 1, (1, 17))):
        sign = Canvas(20, 14)
        text_centered(sign, string, scale=scale)
        xs = [x for x, y in pixels(sign)]
        assert (min(xs), max(xs)) == expected
    sign = Canvas(20, 14)
    text_centered(sign, "HI", 3)
    assert pixels(sign) == dots("HI", 5, 3, width=20, height=14)
    for string in ("", "   "):
        sign.fill(0)
        text_centered(sign, string)
        assert not pixels(sign)
    sign = Canvas(10, 14)
    text_centered(sign, "ABCD")
    assert pixels(sign) == dots("ABCD", -7, width=10, height=14)


def test_text_erase_and_no_hidden_transmission():
    uart = FakeUART()
    sign = FlipDot(uart, width=20, height=14, row_offset=1, min_gap_ms=0)
    text(sign, "L", 0, 0, scale=2)
    expected = {(x, y) for x in (0, 1) for y in range(14)}
    expected |= {(x, y) for x in range(10) for y in (12, 13)}
    assert pixels(sign) == expected
    text(sign, "L", 0, 0, scale=2, on=False)
    assert not pixels(sign)
    text_centered(sign, "L", 0)
    assert pixels(sign) == {(7, y) for y in range(7)} | {(x, 6) for x in range(7, 12)}
    text_centered(sign, "L", 0, on=False)
    assert not pixels(sign)
    assert uart.sent == []
    text(sign, "L", 0, 0)
    sign.show()
    assert len(uart.sent) == 1
    assert payload(uart.sent[0]) == b"\xFE\x00" + b"\x80\x00" * 4 + b"\x00" * 30


def test_scroll_visible_frames_and_final_blank():
    class RecordingCanvas(Canvas):
        def __init__(self):
            super().__init__(20, 14)
            self.frames = []

        def show(self):
            self.frames.append(pixels(self))

    sign = RecordingCanvas()
    sign.fill(1)
    scroll(sign, "HI", y=2, step=3)
    assert len(sign.frames) == 11
    for k, frame in enumerate(sign.frames):
        assert frame == dots("HI", 17-3*k, 2, width=20, height=14)
    assert not sign.frames[-1] and not pixels(sign)
    sign.frames = []
    scroll(sign, "A", scale=2, step=50)
    assert len(sign.frames) == 1 and not sign.frames[-1]


def test_scroll_explicit_uart_frames():
    uart = FakeUART()
    sign = FlipDot(uart, width=20, height=14, row_offset=1, min_gap_ms=0, skip_unchanged=False)
    scroll(sign, "L", y=0, step=5)
    # x = 15, 10, 5, 0, -5: complete glyph, then a final blank frame.
    assert len(uart.sent) == 5
    glyph = b"\xFE\x00" + b"\x80\x00" * 4
    for packet, x in zip(uart.sent[:-1], (15, 10, 5, 0)):
        assert payload(packet) == b"\x00" * (x * 2) + glyph + b"\x00" * ((15 - x) * 2)
    assert payload(uart.sent[-1]) == b"\x01" + b"\x00" * 39
    assert not pixels(sign)


def test_invalid_scale_and_step():
    sign = Canvas()
    for fn, args, kwargs in ((text, ("A", 0, 0), {"scale": 0}), (text_centered, ("",), {"scale": 0}), (scroll, ("A",), {"step": 0}), (scroll, ("A",), {"scale": 0})):
        try:
            fn(sign, *args, **kwargs)
        except ValueError:
            pass
        else:
            assert False, "invalid text geometry accepted"
