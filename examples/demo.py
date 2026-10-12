"""Loops through a set of patterns as fast as the sign allows (the driver's frame gap sets the pace)."""
import random
from mpflipdot import FlipDot, open_uart

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


def rows_down():
    for y in range(H):
        frame((x, y, 1) for x in range(W))


def columns_across():
    for x in range(W):
        frame((x, y, 1) for y in range(H))


def box(i):
    """Outline of the rectangle inset i dots from the edge."""
    pts = []
    for x in range(i, W - i):
        pts += [(x, i, 1), (x, H - 1 - i, 1)]
    for y in range(i, H - i):
        pts += [(i, y, 1), (W - 1 - i, y, 1)]
    return pts


def boxes():
    steps = (min(W, H) - 1) // 2
    for i in list(range(steps + 1)) + list(range(steps - 1, 0, -1)):
        frame(box(i))


def checkerboard():
    for n in range(6):
        frame((x, y, 1) for x in range(W) for y in range(H) if (x + y + n) % 2 == 0)


def diagonal():
    for d in range(W + H - 1):
        frame((x, d - x, 1) for x in range(W) if 0 <= d - x < H)


def sparkle():
    dots = [(x, y, 1) for x in range(W) for y in range(H)]
    for i in range(len(dots) - 1, 0, -1):  # shuffle
        j = random.getrandbits(16) % (i + 1)
        dots[i], dots[j] = dots[j], dots[i]
    step = len(dots) // 8 + 1
    for n in range(step, len(dots) + step, step):
        frame(dots[:n])
    for n in range(len(dots) - step, -step, -step):
        frame(dots[: max(n, 0)])


def flash():
    for _ in range(3):
        sign.fill()
        sign.show()
        sign.clear()
        sign.show()


rounds = 0
while ROUNDS is None or rounds < ROUNDS:
    for pattern in (rows_down, columns_across, boxes, checkerboard, diagonal, sparkle, flash):
        pattern()
    rounds += 1

sign.clear()
sign.show()  # leave the sign blank when ROUNDS runs out
