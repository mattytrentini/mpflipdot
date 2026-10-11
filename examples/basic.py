import time
from mpflipdot import FlipDot, open_uart

# Waveshare Pico-2CH-RS485 channel 0 = UART0 on GP0/GP1; channel 1 = UART1 on GP4/GP5
uart = open_uart(0, tx=0, rx=1)

# Tested config for the 20x14 sign with rotary switch on 5. Change these for your sign.
W, H = 20, 14
sign = FlipDot(uart, address=6, width=W, height=H, row_offset=1)

sign.clear()
sign.set_pixel(0, 0, True)
sign.set_pixel(W - 1, H - 1, True)  # others keep their state
time.sleep(2)

sign.set_pixels((x, x % H, 1) for x in range(W))  # diagonal sawtooth, one send
time.sleep(2)

sign.test(True)
time.sleep(10)
sign.test(False)
sign.show()
