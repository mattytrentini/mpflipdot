"""Loops through some line-drawing demos (needs mpflipdot_draw.py as well as mpflipdot.py)."""
from mpflipdot import FlipDot, open_uart
from mpflipdot_draw import line

# Settings for your sign and wiring. Currently: Waveshare Pico-2CH-RS485 channel 1 and the 20x14 sign
# with rotary switch on 5. (Channel 0 is UART 0 on GP0/GP1; channel 1 is UART 1 on GP4/GP5.)
UART_ID, TX, RX = 1, 4, 5
ADDRESS = 6
W, H = 20, 14
ROW_OFFSET = 1  # 1 for the 20x14 sign, 0 for the 84x7

uart = open_uart(UART_ID, tx=TX, rx=RX)
sign = FlipDot(uart, address=ADDRESS, width=W, height=H, row_offset=ROW_OFFSET)

ROUNDS = None  # None loops forever; set a number to stop after that many rounds




def widths():
    """The same diagonal at widths 1 to 5."""
    for width in range(1, 6):
        sign.fill(0)
        line(sign, 0, H - 1, W - 1, 0, width)
        sign.show()
    for width in range(1, 6):
        sign.fill(0)
        line(sign, 0, H // 2, W - 1, H // 2, width)
        sign.show()


def cross():
    for width in (1, 2, 3):
        sign.fill(0)
        line(sign, 0, 0, W - 1, H - 1, width)
        line(sign, W - 1, 0, 0, H - 1, width)
        sign.show()


def spinner(width):
    """A line through the middle, turning once."""
    for i in range(0, W + H - 2, 2):
        if i < W:
            x, y = i, 0
        else:
            x, y = W - 1, i - W + 1
        sign.fill(0)
        line(sign, x, y, W - 1 - x, H - 1 - y, width)
        sign.show()


def fan():
    """Lines from the bottom-left corner sweeping across the top, kept on screen as they build up."""
    sign.fill(0)
    for x in range(0, W, 2):
        sign.line(0, H - 1, x, 0, 1)
        sign.show()
    for y in range(0, H, 2):
        sign.line(0, H - 1, W - 1, y, 1)
        sign.show()


def offscreen():
    """Lines running past the edges are clipped, not rejected."""
    for k in range(-W, W, 3):
        sign.fill(0)
        line(sign, k, -5, k + W, H + 5, 2)
        sign.show()


rounds = 0
while ROUNDS is None or rounds < ROUNDS:
    widths()
    cross()
    spinner(1)
    spinner(3)
    fan()
    offscreen()
    rounds += 1

sign.fill(0)
sign.show()  # leave the sign blank when ROUNDS runs out
