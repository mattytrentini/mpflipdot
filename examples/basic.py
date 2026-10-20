import time
from mpflipdot import FlipDot, open_uart

# Settings for your sign and wiring. Currently: Waveshare Pico-2CH-RS485 channel 1 and the 20x14 sign
# with rotary switch on 5. (Channel 0 is UART 0 on GP0/GP1; channel 1 is UART 1 on GP4/GP5.)
UART_ID, TX, RX = 1, 4, 5
ADDRESS = 6
W, H = 20, 14
ROW_OFFSET = 1  # 1 for the 20x14 sign, 0 for the 84x7

uart = open_uart(UART_ID, tx=TX, rx=RX)
sign = FlipDot(uart, address=ADDRESS, width=W, height=H, row_offset=ROW_OFFSET)

sign.fill(0)
sign.pixel(0, 0, 1)
sign.pixel(W - 1, H - 1, 1)  # others keep their state
sign.show()
time.sleep(2)

for x in range(W):
    sign.pixel(x, x % H, 1)  # diagonal sawtooth
sign.show()
time.sleep(2)

sign.test(True)
time.sleep(10)
sign.test(False)
sign.show()
