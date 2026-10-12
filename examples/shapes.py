"""Loops through rect and circle demos (needs mpflipdot_draw.py as well as mpflipdot.py)."""
from mpflipdot import FlipDot, open_uart
from mpflipdot_draw import circle, rect

uart = open_uart(0, tx=0, rx=1)

# Tested config for the 20x14 sign with rotary switch on 5. Change these for your sign.
W, H = 20, 14
sign = FlipDot(uart, address=6, width=W, height=H, row_offset=1, auto_show=False)
# On the 84x7 sign, add aspect=1.25 here so circles look round (its dots are taller than wide).

ROUNDS = None  # None loops forever; set a number to stop after that many rounds
CX, CY = W // 2, H // 2


def frame(*shapes):
    """Show exactly these shapes (everything else off) as a single frame. Later shapes win where they overlap."""
    sign.clear()
    for dots in shapes:
        sign.set_pixels(dots)  # straight into the sign's buffer, so no big lists are built (they run a Pico W out of memory)
    sign.show()


def centred_rect(w, h, solid):
    return rect(sign, CX - w // 2, CY - h // 2, w, h, solid)


def growing_rects():
    for solid in (False, True):
        for n in range(1, min(W, H) // 2 + 1):
            frame(centred_rect(2 * n, 2 * n, solid))
        frame(centred_rect(W, H, solid))


def nested_rects():
    """Outlines two dots apart, added one at a time."""
    sign.clear()
    for i in range(0, min(W, H) // 2, 2):
        sign.set_pixels(rect(sign, i, i, W - 2 * i, H - 2 * i))  # added to what is already set
        sign.show()


def growing_circles():
    r = min(CX, CY) - 1
    for solid in (False, True):
        for n in range(r + 1):
            frame(circle(sign, CX, CY, n, solid))


def target():
    """Concentric circles added from the outside in, then a solid dot in the middle."""
    sign.clear()
    for n in range(min(CX, CY) - 1, 0, -2):
        sign.set_pixels(circle(sign, CX, CY, n))
        sign.show()
    sign.set_pixels(circle(sign, CX, CY, 1, True))
    sign.show()


def bouncing_ball():
    """A solid ball with its edge ringed by an outline, bouncing off the walls."""
    r = 2
    x, y, dx, dy = r, r, 1, 1
    for _ in range(40):
        frame(circle(sign, x, y, r, True), circle(sign, x, y, r + 1))
        if not r <= x + dx < W - r:
            dx = -dx
        if not r <= y + dy < H - r:
            dy = -dy
        x += dx
        y += dy


def hole_punch():
    """A solid rectangle with a circle of growing size switched off in the middle (on=False)."""
    for n in range(0, min(CX, CY)):
        frame(rect(sign, 0, 0, W, H, True), circle(sign, CX, CY, n, True, on=False))


rounds = 0
while ROUNDS is None or rounds < ROUNDS:
    growing_rects()
    nested_rects()
    growing_circles()
    target()
    bouncing_ball()
    hole_punch()
    rounds += 1

sign.clear()
sign.show()  # leave the sign blank when ROUNDS runs out
