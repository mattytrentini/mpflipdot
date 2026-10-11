"""Loops through text demos: positioned text, a counter, and scrolling (needs mpflipdot_text.py too)."""
import time
from mpflipdot import FlipDot, open_uart
from mpflipdot_text import scroll, text

uart = open_uart(0, tx=0, rx=1)

# Tested config for the 20x14 sign with rotary switch on 5. Change these for your sign.
W, H = 20, 14
sign = FlipDot(uart, address=6, width=W, height=H, row_offset=1, auto_show=False)

ROUNDS = None  # None loops forever; set a number to stop after that many rounds
MID = (H - 7) // 2  # top row that centres 7-dot-high text


def show(points):
    """Show exactly these dots (everything else off) as a single frame."""
    sign.clear()
    sign.set_pixels(points)
    sign.show()


def positioned():
    """Three characters fit across this sign: place them, then move them about."""
    show(text(sign, "HI!", 1, MID))
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
