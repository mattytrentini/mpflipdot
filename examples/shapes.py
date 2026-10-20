"""Loops through native framebuffer rectangle and ellipse demos."""
from mpflipdot import FlipDot, open_uart

# Settings for your sign and wiring. Currently: Waveshare Pico-2CH-RS485 channel 1 and the 20x14 sign
# with rotary switch on 5. (Channel 0 is UART 0 on GP0/GP1; channel 1 is UART 1 on GP4/GP5.)
UART_ID, TX, RX = 1, 4, 5
ADDRESS = 6
W, H = 20, 14
ROW_OFFSET = 1  # 1 for the 20x14 sign, 0 for the 84x7

uart = open_uart(UART_ID, tx=TX, rx=RX)
sign = FlipDot(uart, address=ADDRESS, width=W, height=H, row_offset=ROW_OFFSET)
# For dots taller than wide, use a larger horizontal radius in ellipse() calls.

ROUNDS = None  # None loops forever; set a number to stop after that many rounds
CX, CY = W // 2, H // 2


def centred_rect(w, h, solid):
    sign.rect(CX - w // 2, CY - h // 2, w, h, 1, solid)


def growing_rects():
    for solid in (False, True):
        for n in range(1, min(W, H) // 2 + 1):
            sign.fill(0)
            centred_rect(2 * n, 2 * n, solid)
            sign.show()
        sign.fill(0)
        centred_rect(W, H, solid)
        sign.show()


def nested_rects():
    """Outlines two dots apart, added one at a time."""
    sign.fill(0)
    for i in range(0, min(W, H) // 2, 2):
        sign.rect(i, i, W - 2 * i, H - 2 * i, 1)
        sign.show()


def growing_circles():
    r = min(CX, CY) - 1
    for solid in (False, True):
        for n in range(r + 1):
            sign.fill(0)
            sign.ellipse(CX, CY, n, n, 1, solid)
            sign.show()


def target():
    """Concentric circles added from the outside in, then a solid dot in the middle."""
    sign.fill(0)
    for n in range(min(CX, CY) - 1, 0, -2):
        sign.ellipse(CX, CY, n, n, 1)
        sign.show()
    sign.ellipse(CX, CY, 1, 1, 1, True)
    sign.show()


def bouncing_ball():
    """A solid ball with its edge ringed by an outline, bouncing off the walls."""
    r = 2
    x, y, dx, dy = r, r, 1, 1
    for _ in range(40):
        sign.fill(0)
        sign.ellipse(x, y, r, r, 1, True)
        sign.ellipse(x, y, r + 1, r + 1, 1)
        sign.show()
        if not r <= x + dx < W - r:
            dx = -dx
        if not r <= y + dy < H - r:
            dy = -dy
        x += dx
        y += dy


def hole_punch():
    """A solid rectangle with an expanding circular hole (colour 0)."""
    for n in range(0, min(CX, CY)):
        sign.fill(1)
        sign.ellipse(CX, CY, n, n, 0, True)
        sign.show()


rounds = 0
while ROUNDS is None or rounds < ROUNDS:
    growing_rects()
    nested_rects()
    growing_circles()
    target()
    bouncing_ball()
    hole_punch()
    rounds += 1

sign.fill(0)
sign.show()  # leave the sign blank when ROUNDS runs out
