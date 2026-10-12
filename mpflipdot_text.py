"""Optional text helpers for mpflipdot: a 5x7 font, text at any position, and scrolling."""

# 5 bytes per character for ASCII 32 (space) to 93 (']'). Each byte is one column, left to right,
# and bit 0 is the top row. Lowercase is drawn as uppercase; anything else is blank.
_FIRST = 32
_COUNT = 62  # the contiguous run, space to "]"
_BAR = _COUNT  # "|" is stored after the run (it is ASCII 124, too far on to keep the table contiguous)
_FONT = (
    b"\x00\x00\x00\x00\x00"  # space
    b"\x00\x00\x5f\x00\x00"  # !
    b"\x00\x07\x00\x07\x00"  # "
    b"\x14\x7f\x14\x7f\x14"  # #
    b"\x24\x2a\x7f\x2a\x12"  # $
    b"\x23\x13\x08\x64\x62"  # %
    b"\x36\x49\x55\x22\x50"  # &
    b"\x00\x00\x07\x00\x00"  # '
    b"\x00\x1c\x22\x41\x00"  # (
    b"\x00\x41\x22\x1c\x00"  # )
    b"\x14\x08\x3e\x08\x14"  # *
    b"\x08\x08\x3e\x08\x08"  # +
    b"\x00\x50\x30\x00\x00"  # ,
    b"\x08\x08\x08\x08\x08"  # -
    b"\x00\x60\x60\x00\x00"  # .
    b"\x20\x10\x08\x04\x02"  # /
    b"\x3e\x41\x41\x41\x3e"  # 0 (no slash; same as O)
    b"\x00\x42\x7f\x40\x00"  # 1
    b"\x42\x61\x51\x49\x46"  # 2
    b"\x21\x41\x45\x4b\x31"  # 3
    b"\x18\x14\x12\x7f\x10"  # 4
    b"\x27\x45\x45\x45\x39"  # 5
    b"\x3c\x4a\x49\x49\x30"  # 6
    b"\x01\x71\x09\x05\x03"  # 7
    b"\x36\x49\x49\x49\x36"  # 8
    b"\x06\x49\x49\x29\x1e"  # 9
    b"\x00\x36\x36\x00\x00"  # :
    b"\x00\x56\x36\x00\x00"  # ;
    b"\x08\x14\x22\x41\x00"  # <
    b"\x14\x14\x14\x14\x14"  # =
    b"\x00\x41\x22\x14\x08"  # >
    b"\x02\x01\x51\x09\x06"  # ?
    b"\x32\x49\x79\x41\x3e"  # @
    b"\x7e\x11\x11\x11\x7e"  # A
    b"\x7f\x49\x49\x49\x36"  # B
    b"\x3e\x41\x41\x41\x22"  # C
    b"\x7f\x41\x41\x22\x1c"  # D
    b"\x7f\x49\x49\x49\x41"  # E
    b"\x7f\x09\x09\x09\x01"  # F
    b"\x3e\x41\x49\x49\x7a"  # G
    b"\x7f\x08\x08\x08\x7f"  # H
    b"\x00\x41\x7f\x41\x00"  # I
    b"\x20\x40\x41\x3f\x01"  # J
    b"\x7f\x08\x14\x22\x41"  # K
    b"\x7f\x40\x40\x40\x40"  # L
    b"\x7f\x02\x0c\x02\x7f"  # M
    b"\x7f\x04\x08\x10\x7f"  # N
    b"\x3e\x41\x41\x41\x3e"  # O
    b"\x7f\x09\x09\x09\x06"  # P
    b"\x3e\x41\x51\x21\x5e"  # Q
    b"\x7f\x09\x19\x29\x46"  # R
    b"\x46\x49\x49\x49\x31"  # S
    b"\x01\x01\x7f\x01\x01"  # T
    b"\x3f\x40\x40\x40\x3f"  # U
    b"\x1f\x20\x40\x20\x1f"  # V
    b"\x3f\x40\x38\x40\x3f"  # W
    b"\x63\x14\x08\x14\x63"  # X
    b"\x07\x08\x70\x08\x07"  # Y
    b"\x61\x51\x49\x45\x43"  # Z
    b"\x00\x7f\x41\x41\x00"  # [
    b"\x02\x04\x08\x10\x20"  # backslash
    b"\x00\x41\x41\x7f\x00"  # ]
    b"\x00\x00\x7f\x00\x00"  # |
)


def _index(ch):
    """Position of ch's glyph in _FONT, or -1 if the font doesn't have it."""
    i = ord(ch) - _FIRST
    if 0 <= i < _COUNT:
        return i
    return _BAR if ch == "|" else -1


def text_width(string, scale=1):
    """Width in dots of string drawn at this scale (5-dot characters with a 1-dot gap, no trailing gap)."""
    return len(string) * 6 * scale - scale if string else 0


def text(sign, string, x, y, scale=1, on=True):
    """Dots for string with its top-left corner at (x, y), clipped to the sign.

    Characters are 5x7 dots, times scale (a whole number: 2 gives 10x14). Lowercase is drawn as
    uppercase and characters the font doesn't have are blank. The corner can be off the sign.
    """
    if scale < 1:
        raise ValueError("scale")
    w, h = sign.width, sign.height
    for n, ch in enumerate(string.upper()):
        gx = x + n * 6 * scale
        if gx >= w:
            break  # this character and the rest are off the right edge
        i = _index(ch)
        if gx + 5 * scale <= 0 or i < 0:
            continue
        for col in range(5):
            bits = _FONT[i * 5 + col]
            for row in range(7):
                if bits >> row & 1:
                    for dx in range(scale):
                        px = gx + col * scale + dx
                        if 0 <= px < w:
                            for dy in range(scale):
                                py = y + row * scale + dy
                                if 0 <= py < h:
                                    yield (px, py, on)


def _ink(string):
    """(first, last) unscaled columns that have a dot in them, or None if nothing would be drawn."""
    first = last = None
    for n, ch in enumerate(string.upper()):
        i = _index(ch)
        if i >= 0:
            for col in range(5):
                if _FONT[i * 5 + col]:
                    if first is None:
                        first = n * 6 + col
                    last = n * 6 + col
    return None if first is None else (first, last)


def text_centered(sign, string, y=0, scale=1, on=True):
    """Dots for string centred left to right on the sign by the dots drawn, with its top at y.

    Blank columns at the start and end of the text (as in I, 1, . and !) don't count, so what you see is
    centred. Any odd dot left over goes on the right. Too wide to fit: both ends are clipped.
    """
    ink = _ink(string)
    if ink is None:
        return text(sign, string, 0, y, scale, on)  # nothing to draw
    first, last = ink
    x = (sign.width - (last - first + 1) * scale) // 2 - first * scale
    return text(sign, string, x, y, scale, on)


def scroll_frames(sign, string, y=0, scale=1, step=2):
    """Yield the dots for each frame of string scrolling right to left once across the sign.

    The text slides in from the right edge, moving step dots a frame, and the last frame is empty.
    Show each one as a whole frame: sign.clear(), sign.set_pixels(dots), sign.show().
    """
    if step < 1:
        raise ValueError("step")
    end = -text_width(string, scale)
    x = sign.width - step
    while True:
        yield text(sign, string, x, y, scale)
        if x <= end:
            break
        x -= step


def scroll(sign, string, y=0, scale=1, step=2):
    """Scroll string across the sign once and leave it blank. Blocks; the driver's min_gap_ms sets the pace."""
    auto = sign.auto_show
    sign.auto_show = False  # one frame per step, whatever the setting was
    try:
        for dots in scroll_frames(sign, string, y, scale, step):
            sign.clear()
            sign.set_pixels(dots)
            sign.show()
    finally:
        sign.auto_show = auto
