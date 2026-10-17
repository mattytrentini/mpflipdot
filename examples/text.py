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
sign = FlipDot(uart, address=ADDRESS, width=W, height=H, row_offset=ROW_OFFSET, auto_show=False)

ROUNDS = None  # None loops forever; set a number to stop after that many rounds
MID = (H - 7) // 2  # top row that centres 7-dot-high text


def show(points):
    """Show exactly these dots (everything else off) as a single frame."""
    sign.clear()
    sign.set_pixels(points)
    sign.show()


def positioned():
    """Three characters fit across this sign: place them, then move them about."""
    show(text_centered(sign, "HI!", MID))
    time.sleep(2)
    for y in list(range(H - 7 + 1)) + list(range(H - 7 - 1, 0, -1)):
        show(text(sign, "ABC", 1, y))
    for x in list(range(-6, 4)) + list(range(3, -6, -1)):
        show(text(sign, "XYZ", x, MID))  # partly off the edge is fine: it is clipped


def counter():
    for n in range(0, 31):
        show(text(sign, "%03d" % n, 1, MID))


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

sign.clear()
sign.show()  # leave the sign blank when ROUNDS runs out
