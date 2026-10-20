"""Loops through a set of patterns as fast as the sign allows (the driver's frame gap sets the pace)."""
import random
from mpflipdot import FlipDot, open_uart

# Settings for your sign and wiring. Currently: Waveshare Pico-2CH-RS485 channel 1 and the 20x14 sign
# with rotary switch on 5. (Channel 0 is UART 0 on GP0/GP1; channel 1 is UART 1 on GP4/GP5.)
UART_ID, TX, RX = 1, 4, 5
ADDRESS = 6
W, H = 20, 14
ROW_OFFSET = 1  # 1 for the 20x14 sign, 0 for the 84x7

uart = open_uart(UART_ID, tx=TX, rx=RX)
sign = FlipDot(uart, address=ADDRESS, width=W, height=H, row_offset=ROW_OFFSET)

ROUNDS = None  # None loops forever; set a number to stop after that many rounds


def box(i):
    """Show the rectangle inset i dots from the edge."""
    sign.fill(0)
    sign.rect(i, i, W - 2 * i, H - 2 * i, 1)
    sign.show()


def rows_down():
    for y in range(H):
        sign.fill(0)
        sign.hline(0, y, W, 1)
        sign.show()


def columns_across():
    for x in range(W):
        sign.fill(0)
        sign.vline(x, 0, H, 1)
        sign.show()


def boxes():
    steps = (min(W, H) - 1) // 2
    for i in range(steps + 1):
        box(i)
    for i in range(steps - 1, 0, -1):
        box(i)


def checkerboard():
    for n in range(6):
        sign.fill(0)
        for x in range(W):
            for y in range(H):
                if (x + y + n) % 2 == 0:
                    sign.pixel(x, y, 1)
        sign.show()


def diagonal():
    for d in range(W + H - 1):
        sign.fill(0)
        for x in range(max(0, d - H + 1), min(W, d + 1)):
            sign.pixel(x, d - x, 1)
        sign.show()


def sparkle():
    # Shuffle flat pixel indices, rather than allocating a tuple for every dot.
    dots = list(range(W * H))
    for i in range(len(dots) - 1, 0, -1):
        j = random.getrandbits(16) % (i + 1)
        dots[i], dots[j] = dots[j], dots[i]
    step = len(dots) // 8 + 1
    sign.fill(0)
    for start in range(0, len(dots), step):
        for i in range(start, min(start + step, len(dots))):
            dot = dots[i]
            sign.pixel(dot % W, dot // W, 1)
        sign.show()
    for start in range(len(dots) - 1, -1, -step):
        for i in range(start, max(start - step, -1), -1):
            dot = dots[i]
            sign.pixel(dot % W, dot // W, 0)
        sign.show()


def flash():
    for _ in range(3):
        sign.fill(1)
        sign.show()
        sign.fill(0)
        sign.show()


rounds = 0
while ROUNDS is None or rounds < ROUNDS:
    for pattern in (rows_down, columns_across, boxes, checkerboard, diagonal, sparkle, flash):
        pattern()
    rounds += 1

sign.fill(0)
sign.show()  # leave the sign blank when ROUNDS runs out
