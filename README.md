# mpflipdot

![A Hanover Displays flip-dot sign driven by mpflipdot](flipdot_example.jpg)

[Watch a video demo on YouTube](https://www.youtube.com/watch?v=nHq_gT024Bs).

A [MicroPython](https://micropython.org/) framebuffer driver for [Hanover Displays](https://www.hanoverdisplays.com/) flip-dot signs, aimed at a Raspberry Pi Pico (or Pico 2) with an RS485 adapter. No dependencies beyond MicroPython's built-in `framebuf`, `time` and `machine` modules.

> **Status:** 0.2.0 is a breaking framebuf-based revision. Native MicroPython software checks pass; this revision has not yet driven a physical sign. The previous driver was verified on 20x14 and 84x7 signs with a Pico W and Waveshare Pico-2CH-RS485. See [Tested hardware](#tested-hardware) and [PLAN.md](PLAN.md).

## Features

- A real `framebuf.FrameBuffer` subclass: pixels, lines, rectangles, text, scrolling and blitting use the standard MicroPython API
- A 2D monochrome canvas with `0` for off and `1` for on; drawing changes RAM, then `show()` sends one complete frame
- Configurable address, width, height, row offset and upside-down mounting
- Manufacturer test mode (broadcast, address 0)
- Optional thick lines (`mpflipdot_draw.py`); native ellipses cover circles and stretched shapes
- Optional 5x7 text, scaling, ink-based centring and animated scrolling (`mpflipdot_text.py`)
- Automatic inter-frame timing and suppression of repeated frames, with forced refresh available

## Usage

```python
from mpflipdot import FlipDot, open_uart

uart = open_uart(1, tx=4, rx=5)          # any UART id / pins (this is channel 1 of the Waveshare board)
sign = FlipDot(uart, address=6, width=20, height=14, row_offset=1)   # see "Sign quirks" below

sign.fill(0)
sign.pixel(10, 3, 1)
sign.rect(0, 0, 20, 14, 1)
sign.line(0, 13, 19, 0, 1)
sign.text("Hi", 2, 3, 1)                 # Native 8x8 font
sign.show()                              # One complete serial update

state = sign.pixel(10, 3)                 # Read the logical canvas, not the hardware
sign.test(True)                          # Manufacturer test mode
sign.test(False)
sign.show()                              # Restore the canvas after test mode
```

All drawing methods are inherited from [MicroPython's framebuf API](https://docs.micropython.org/en/latest/library/framebuf.html); the methods available depend on your firmware. They never transmit automatically. Pass colour `0` to erase. Drawing is clipped by framebuf.

`FlipDot(uart, address=1, width=84, height=7, flip=False, de_pin=None, row_offset=0, min_gap_ms=None, skip_unchanged=True, quiet_ms=100)` accepts:

- `row_offset`: bit position of the top physical row; use `1` on the tested 20x14 sign.
- `flip=True`: rotate the transmitted image 180 degrees for upside-down mounting. The logical canvas and pixel readback stay top-left.
- `de_pin`: an optional output Pin for adapters without automatic RS485 direction control.
- `min_gap_ms` / `quiet_ms`: transmission pacing; see [Sign quirks](#sign-quirks).
- `skip_unchanged=False`: resend even unchanged frames. With the default, `show(force=True)` forces a refresh after a dropped frame.

Addresses are 0-15. Multiple sign instances may share a UART, but timing guards are per instance, not a shared-bus scheduler. Each transmitted image replaces the whole sign; the protocol has no per-dot write.

`sign.buffer` exposes the logical `MONO_VLSB` bytearray, sized `width * ((height + 7) // 8)`. It is not the serial payload: `show()` converts eight-row bands into column-major bytes, applies rotation and row offset, and masks unused bits. The wire buffer is reused; the logical buffer is never changed by transmission.

## Drawing helpers

Use native `sign.line`, `sign.hline`, `sign.vline`, `sign.rect` and `sign.ellipse` for standard shapes. `mpflipdot_draw.py` only adds thick lines, drawing directly into the canvas:

```python
from mpflipdot_draw import line

sign.fill(0)
sign.rect(2, 3, 10, 6, 1, True)               # Native filled rectangle
line(sign, 0, 0, 19, 13, width=3)
sign.ellipse(10, 7, 5, 5, 1)                 # Circle outline
sign.ellipse(10, 7, 3, 3, 0, True)           # Erase a filled circular hole
sign.show()
```

The line helper returns `None` and never displays automatically. Later drawing wins where shapes overlap; `on=False` erases a thick line.

Native `ellipse(cx, cy, xr, yr, colour[, fill])` draws circles when the two radii match. Pass `True` for a filled shape and colour `0` to erase. Ellipse rasterisation is native C code rather than a separate Python circle implementation.

**Round circles.** Dots on some signs are taller than wide. A horizontal stretch of 1.25 looked round with the previous renderer on the 84x7 sign. Express that directly as `sign.ellipse(cx, cy, round(radius * 1.25), radius, 1)`. The radii must be integers, and native ellipse rasterisation differs from the old circle helper, so small shapes may need visual adjustment. The 20x14 sign's dot proportions were not compared.

Thick lines expand along their minor axis: diagonal thickness is about 0.7 times the requested width, and an even width puts the extra dot below or to the right of the centre line.

## Text

Native `sign.text(string, x, y[, c])` uses fixed 8x8 character cells; the optional colour defaults to `1`. On a seven-row sign the eighth row is clipped; use the optional 5x7 font when the smaller layout matters.

`mpflipdot_text.py` retains the small font, scaling and ink-based centring. Its drawing helpers modify the canvas directly:

```python
from mpflipdot_text import text, text_centered, scroll, text_width

sign.fill(0)
text(sign, "OK", 2, 0, scale=2)             # 10x14 characters
sign.show()

sign.fill(0)
text_centered(sign, "HI!", y=3)
sign.show()

scroll(sign, "HELLO WORLD", y=3)             # Blocking animation; ends blank
scroll(sign, "BIG", y=0, scale=2, step=3)
width = text_width("HELLO", scale=1)
```

- Characters are 5 dots wide with a 1-dot gap, so a 20-dot-wide sign fits three at scale 1.
- `text_centered` centres on drawn ink rather than character cells; any odd spare dot goes on the right.
- Lowercase is drawn as uppercase. The font covers ASCII space through `]`, plus `|`; other characters are blank. Zero is an oval, matching O.
- `text(..., on=False)` and `text_centered(..., on=False)` erase their glyphs. These helpers return `None`, without sending.
- `scroll` clears, draws and calls `show()` for each step. The driver's timing guard sets the pace; larger steps scroll faster.
- For a custom animation, loop over positions and call `fill(0)`, `text(...)`, then `show()`. Native `sign.scroll(dx, dy)` only shifts the canvas; it neither animates nor clears exposed areas automatically.

## Migrating from 0.1.x

0.2.0 removes the old drawing API rather than providing compatibility aliases:

| Previous API | Replacement |
|---|---|
| `sign.clear()` | `sign.fill(0)` |
| `sign.fill()` | `sign.fill(1)` |
| `sign.set_pixel(x, y, on)` | `sign.pixel(x, y, on)` |
| `sign.get_pixel(x, y)` | `sign.pixel(x, y)` |
| `sign.set_pixels(points)` | Draw with native methods or loop over `pixel(...)`, then `show()` |
| `auto_show` | Removed; call `show()` explicitly |
| `sign.set_pixels(line(...))` or other helper iterators | Call the helper directly, then `show()` |
| `mpflipdot_draw.rect(...)` | Native `sign.rect(x, y, w, h, colour[, fill])` |
| `mpflipdot_draw.circle(..., solid=solid, on=on)` | Native `sign.ellipse(cx, cy, radius, radius, int(on), solid)` |
| `FlipDot(..., aspect=ratio)` | Removed; choose ellipse radii explicitly, e.g. `round(radius * ratio), radius` |
| `scroll_frames(...)` | An explicit position/draw/show loop |

Native clipping and pixel access replace the old coordinate checks. Font metrics change if you switch from the optional 5x7 helper to native text. `show(force=True)`, timing options, RS485 direction control and manufacturer test mode remain supported.

## Examples

- `examples/basic.py`: clear, single dots, a batch update and test mode.
- `examples/text.py`: centred and positioned text, a counter, and scrolling text at scale 1 and 2.
- `examples/bounce.py`: a ball bouncing round the sign forever; Ctrl-C clears the sign and stops it.
- `examples/shapes.py`: loops through native rectangle and ellipse demos (growing and nested rectangles, circles, a target, a bouncing ball, a hole punched in a solid block).
- `examples/lines.py`: loops through line demos (widths, a cross, spinning lines, a fan, lines clipped at the edges).
- `examples/demo.py`: loops through patterns (sweeps, boxes, checkerboard, diagonal wipe, sparkle, flash) as fast as
  the sign allows. Run it with `mpremote run examples/demo.py`; edit `W`, `H` and `address` first for your sign.
  Stop it with Ctrl-C, or `mpremote soft-reset` if it's detached.

## Tested hardware

The physical results below belong to the **0.1.x driver**, not the framebuf revision.

| Item | Previous physical verification |
|---|---|
| Board | Pico W, MicroPython 1.29.0. Pico 2 W has not driven a sign. |
| RS485 | Waveshare Pico-2CH-RS485 with automatic direction control; red sign wire on A, black on B. |
| 20x14 sign | Address 6 (switch 5), `row_offset=1`, 24 V / 5 A. Blank/full images, state retention, rotation, shapes, text, test mode and dense alternating patterns worked. Automatic 284 ms frame spacing showed no dropped frames in the recorded trials. |
| 84x7 sign | Address 6, `row_offset=0`, same supply. Blank/full images, test mode, row sweeps, text and shape demos worked. Automatic spacing was about 467 ms; `aspect=1.25` looked round. Dense frames, rotation and remaining demos were not fully verified. |
| Framebuf revision | Native MicroPython 1.29.0-preview Unix execution: mapping, rotation, row-offset boundaries, padding, blank frames, timing, direction-control ordering and helper behavior. All six examples smoke-ran with recording UARTs at 20x14 and 84x7, including bounce interrupt cleanup. No physical sign run yet. |

Physical checks still needed: this revision on both signs, Pico 2 W, manual DE/RE hardware, multiple signs sharing a bus, and on-board Wi-Fi installation.

## Sign quirks

These came out of testing on the 20x14 sign and may differ on other signs, so check yours:

- **Address is the rotary switch plus 1.** Switch on 5 means `address=6`. Address 0 is broadcast, and test mode always uses it.
- **Row offset.** On the 20x14 sign the top row is bit 1 of each column, not bit 0, so use `row_offset=1`.
  With `row_offset=0` the bottom row stays off. If a row is missing on your sign, try a different offset.
- **All-zero frames are ignored by the tested signs.** For a blank image, `show()` sets an invisible bit in the wire payload (bit 0 with a row offset, or the first spare bit above the rows). The logical framebuffer stays blank. If every bit is a visible row (`row_offset=0` and height divisible by 8), there is no safe spare bit: the driver sends zeros, but clearing such a sign is unverified.
- **Power it properly.** An underpowered sign behaves unreliably: it drops frames at random, or looks completely
  unresponsive (no clicking, nothing changes) even though the wiring and code are fine, which looks just like a
  signalling problem. In testing a 24 V / 5 A supply was reliable and a 24 V / 1 A supply was not. If frames go
  missing or the sign seems dead, check the supply before the wiring.
- **Update rate.** The sign needs a quiet moment after each frame. On the 20x14 sign frames 0.3 s apart were fine and
  at 0.2 s it skipped them. One 88-byte frame takes about 0.18 s just to send at 4800 baud, so that leaves roughly
  0.1 s of quiet. The driver works the same way for any size: by default (`min_gap_ms=None`) a send waits until the
  previous frame has finished going out plus `quiet_ms` (100 ms), which is about 0.28 s on the 20x14 sign (verified) and
  about 0.47 s on an 84x7 (176 bytes, 0.37 s to send; verified on the sign, though only about 2 frames a second). A fast loop is slowed down, not dropped, and the last update
  always lands. `quiet_ms=100` is a guess from the 20x14 sign, so raise it if a bigger sign still drops frames. A
  number for `min_gap_ms` is a fixed gap from the start of one send to the start of the next, and `min_gap_ms=0`
  turns the guard off.
- **USB-RS485 adapters on a computer** (for debugging): keep the port open for a few seconds after the last write,
  or the final frame can be lost.

## Hardware

- Raspberry Pi Pico W or Pico 2 W running MicroPython
- [Waveshare Pico-2CH-RS485](https://www.waveshare.com/pico-2ch-rs485.htm) (SP3485): channel 0 = UART0 on GP0/GP1, channel 1 = UART1 on GP4/GP5
- Hanover Displays flip-dot sign, 4800 baud serial, powered from a **24 V / 5 A** supply. A 24 V / 1 A supply made it drop frames
  at random or seem unresponsive, so don't skimp on current (see [Sign quirks](#sign-quirks))
- MicroPython firmware with built-in `framebuf`. The 0.2.0 software checks used the 1.29.0-preview Unix port; previous physical checks used 1.29.0 on Pico W. Older releases and this revision on RP2 hardware are unverified. `UART.flush()` is required only with `de_pin`.

## Install

```
mpremote mip install github:simonprickett/mpflipdot
```

That command installs the published upstream version, not an unpushed local feature branch. GitHub installation of this revision requires publishing it first; a fork must also update the GitHub owner/repository paths in `package.json`.

To try a local checkout, create `/lib` on the device if needed, then copy the files:

```sh
mpremote fs cp mpflipdot.py mpflipdot_draw.py mpflipdot_text.py :/lib/
```

Only `mpflipdot.py` is required; the drawing and text modules are optional. Firmware must include `framebuf`.

## Development checks

Run the native MicroPython Unix executable from the repository root:

```sh
micropython tests/run.py
```

The tests use the real native `framebuf` and recording UARTs; no third-party test framework or framebuffer shim is needed. CPython alone does not provide `framebuf`.

## Acknowledgements

Protocol details were worked out by studying [pyflipdot](https://pypi.org/project/pyflipdot/).

## License

[MIT](LICENSE)
