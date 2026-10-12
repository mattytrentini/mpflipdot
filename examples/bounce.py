"""A ball bouncing round the sign forever. Press Ctrl-C to stop (the sign is cleared)."""
from mpflipdot import FlipDot, open_uart
from mpflipdot_draw import circle

uart = open_uart(0, tx=0, rx=1)

# Tested config for the 20x14 sign with rotary switch on 5. Change these for your sign.
W, H = 20, 14
sign = FlipDot(uart, address=6, width=W, height=H, row_offset=1, auto_show=False)

RADIUS = 2  # the ball is 2 * RADIUS + 1 dots across
SCALE = 4  # positions and speeds are in quarter dots, so the angle isn't a plain 45 degrees
VX, VY = 7, 3  # speed in quarter dots per frame; these two give a long, non-repeating path on 20x14

x, y = W // 2 * SCALE, H // 2 * SCALE
vx, vy = VX, VY
left, right = RADIUS * SCALE, (W - 1 - RADIUS) * SCALE
top, bottom = RADIUS * SCALE, (H - 1 - RADIUS) * SCALE

try:
    while True:
        sign.clear()
        sign.set_pixels(circle(sign, x // SCALE, y // SCALE, RADIUS, True))
        sign.show()  # the driver's frame gap keeps this within what the sign can take
        x += vx
        y += vy
        if x < left or x > right:
            vx = -vx
            x = min(max(x, left), right)
        if y < top or y > bottom:
            vy = -vy
            y = min(max(y, top), bottom)
except KeyboardInterrupt:
    pass
finally:
    sign.clear()
    sign.show()
