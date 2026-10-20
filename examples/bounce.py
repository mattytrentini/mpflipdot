"""A ball bouncing round the sign forever. Press Ctrl-C to stop (the sign is cleared)."""
from mpflipdot import FlipDot, open_uart

# Settings for your sign and wiring. Currently: Waveshare Pico-2CH-RS485 channel 1 and the 20x14 sign
# with rotary switch on 5. (Channel 0 is UART 0 on GP0/GP1; channel 1 is UART 1 on GP4/GP5.)
UART_ID, TX, RX = 1, 4, 5
ADDRESS = 6
W, H = 20, 14
ROW_OFFSET = 1  # 1 for the 20x14 sign, 0 for the 84x7

uart = open_uart(UART_ID, tx=TX, rx=RX)
sign = FlipDot(uart, address=ADDRESS, width=W, height=H, row_offset=ROW_OFFSET)

RADIUS = 2  # the ball is 2 * RADIUS + 1 dots across
SCALE = 4  # positions and speeds are in quarter dots, so the angle isn't a plain 45 degrees
VX, VY = 7, 3  # speed in quarter dots per frame; these two give a long, non-repeating path on 20x14

x, y = W // 2 * SCALE, H // 2 * SCALE
vx, vy = VX, VY
left, right = RADIUS * SCALE, (W - 1 - RADIUS) * SCALE
top, bottom = RADIUS * SCALE, (H - 1 - RADIUS) * SCALE

try:
    while True:
        sign.fill(0)
        sign.ellipse(x // SCALE, y // SCALE, RADIUS, RADIUS, 1, True)
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
    sign.fill(0)
    sign.show()
