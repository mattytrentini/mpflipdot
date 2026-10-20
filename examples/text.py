"""Loops through text demos: positioned text, a counter, and scrolling (needs mpflipdot_text.py too)."""
import time
from mpflipdot import FlipDot, open_uart
from mpflipdot_text import scroll, text, text_centered

# Settings for your sign and wiring. Currently: Waveshare Pico-2CH-RS485 channel 1 and the 20x14 sign
# with rotary switch on 5. (Channel 0 is UART 0 on GP0/GP1; channel 1 is UART 1 on GP4/GP5.)
UART_ID, TX, RX = 1, 4, 5
ADDRESS = 6
W, H = 20, 14
ROW_OFFSET = 1  # 1 for the 20x14 sign, 0 for the 84x7

uart = open_uart(UART_ID, tx=TX, rx=RX)
sign = FlipDot(uart, address=ADDRESS, width=W, height=H, row_offset=ROW_OFFSET)

ROUNDS = None  # None loops forever; set a number to stop after that many rounds
MID = (H - 7) // 2  # top row that centres 7-dot-high text


def positioned():
    """Three characters fit across this sign: place them, then move them about."""
    sign.fill(0)
    text_centered(sign, "HI!", MID)
    sign.show()
    time.sleep(2)
    for y in range(H - 7 + 1):
        sign.fill(0)
        text(sign, "ABC", 1, y)
        sign.show()
    for y in range(H - 8, 0, -1):
        sign.fill(0)
        text(sign, "ABC", 1, y)
        sign.show()
    for x in range(-6, 4):
        sign.fill(0)
        text(sign, "XYZ", x, MID)  # partly off the edge is fine: it is clipped
        sign.show()
    for x in range(3, -6, -1):
        sign.fill(0)
        text(sign, "XYZ", x, MID)
        sign.show()


def counter():
    for n in range(0, 31):
        sign.fill(0)
        text(sign, "%03d" % n, 1, MID)
        sign.show()


def scrolling():
    scroll(sign, "HELLO WORLD", y=MID)
    if H >= 14:
        scroll(sign, "FLIP DOT", y=H // 2 - 7, scale=2, step=3)  # 10x14 characters
    scroll(sign, "ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789 !/.", y=MID, step=4)


rounds = 0
while ROUNDS is None or rounds < ROUNDS:
    positioned()
    counter()
    scrolling()
    rounds += 1

sign.fill(0)
sign.show()  # leave the sign blank when ROUNDS runs out
