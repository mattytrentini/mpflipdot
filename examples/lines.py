"""Loops through some line-drawing demos (needs mpflipdot_draw.py as well as mpflipdot.py)."""
from mpflipdot import FlipDot, open_uart
from mpflipdot_draw import line

uart = open_uart(0, tx=0, rx=1)

# Tested config for the 20x14 sign with rotary switch on 5. Change these for your sign.
W, H = 20, 14
sign = FlipDot(uart, address=6, width=W, height=H, row_offset=1, auto_show=False)

ROUNDS = None  # None loops forever; set a number to stop after that many rounds


def frame(points):
    """Show exactly these dots (everything else off) as a single frame."""
    sign.clear()
    sign.set_pixels(points)
    sign.show()


def perimeter():
    """Every dot round the edge of the display, clockwise from the top-left."""
    return (
        [(x, 0) for x in range(W)]
        + [(W - 1, y) for y in range(1, H)]
        + [(x, H - 1) for x in range(W - 2, -1, -1)]
        + [(0, y) for y in range(H - 2, 0, -1)]
    )


def widths():
    """The same diagonal at widths 1 to 5."""
    for width in range(1, 6):
        frame(line(sign, 0, H - 1, W - 1, 0, width))
    for width in range(1, 6):
        frame(line(sign, 0, H // 2, W - 1, H // 2, width))


def cross():
    for width in (1, 2, 3):
        frame(list(line(sign, 0, 0, W - 1, H - 1, width)) + list(line(sign, W - 1, 0, 0, H - 1, width)))


def spinner(width):
    """A line through the middle, turning once."""
    edge = perimeter()
    half = len(edge) // 2
    for i in range(0, half, 2):
        x0, y0 = edge[i]
        x1, y1 = edge[i + half]
        frame(line(sign, x0, y0, x1, y1, width))


def fan():
    """Lines from the bottom-left corner sweeping across the top, kept on screen as they build up."""
    dots = []
    for x in range(0, W, 2):
        dots += list(line(sign, 0, H - 1, x, 0))
        frame(dots)
    for y in range(0, H, 2):
        dots += list(line(sign, 0, H - 1, W - 1, y))
        frame(dots)


def offscreen():
    """Lines running past the edges are clipped, not rejected."""
    for k in range(-W, W, 3):
        frame(line(sign, k, -5, k + W, H + 5, 2))


rounds = 0
while ROUNDS is None or rounds < ROUNDS:
    widths()
    cross()
    spinner(1)
    spinner(3)
    fan()
    offscreen()
    rounds += 1

sign.clear()
sign.show()  # leave the sign blank when ROUNDS runs out
