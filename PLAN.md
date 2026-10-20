# mpflipdot – Plan

A minimal, dependency-free MicroPython driver for Hanover Displays flip-dot
signs, targeting a Raspberry Pi Pico with an RS485 transceiver.

## Goals

- Pure MicroPython. Only built-ins (`machine.UART`, `machine.Pin`) – no third-party packages.
- One small source file (`mpflipdot.py`) that can be copied to the board.
- Hanover Displays signs only. No attempt to support other vendors.
- Configurable per sign: bus address, width, height (e.g. 84x7, plus a smaller sign).
- Public API:
  - clear the display
  - start / stop the manufacturer's test mode
  - set one dot at (x, y) on/off, preserving all other dots
  - set many dots from an iterable of `(x, y, on)` (and a way to replace the whole frame)

## Protocol (derived from pyflipdot 0.2.2)

Serial: **4800 baud**, 8N1 (pyserial defaults), RS485 half duplex, write-only
(the sign never replies in this protocol, and there is no way to read dot state back).

Every packet is ASCII:

```
STX  CMD ADDR  [payload]  ETX  CHK
0x02 1 hex     ASCII hex  0x03 2 hex chars
     nibble    digits          digits
```

- `CMD` – one hex digit: `1` write image, `3` start test, `C` (12) stop test.
- `ADDR` – one hex digit (so addresses 0–15). Test commands use address `0`.
- Checksum – sum all bytes **after STX up to and including ETX**, take `& 0xFF`,
  then two's complement (`((sum ^ 0xFF) + 1) & 0xFF`), send as two upper-case ASCII hex digits.
- Image payload – `LEN` (one byte as 2 hex digits) followed by the pixel bytes
  (each as 2 hex digits). `LEN` is the pixel byte count `& 0xFF`.
- Pixel bytes are **column-major**: for each column left to right, `ceil(height/8)`
  bytes, least-significant byte first; within a byte, bit 0 is the topmost row
  of that 8-row group. Unused high bits in the last byte are 0.
  Example: 84x7 → 84 bytes → `LEN = 0x54`.
- Whole-frame writes only: there is no per-dot command, so the driver keeps a
  local framebuffer and resends it.

Items to confirm on real hardware (flagged in the code/docs until verified):

1. Test-mode commands using address `0` (broadcast) vs. the sign's own address.
2. Whether signs need an inter-packet delay when updating quickly.
3. Behaviour of `LEN` when the frame exceeds 255 bytes (reference just truncates; we will raise `ValueError` instead for sizes we know are wrong, or mirror reference – decide after testing).
4. Upside-down mounting (`flip`) – implemented as optional 180° rotation as in the reference.

## Design

### Module layout

```
mpflipdot/
├── mpflipdot.py        # the driver (single file, deploy this)
├── examples/
│   ├── basic.py        # clear, set a pixel, test mode
│   └── bulk.py         # set_pixels / whole-frame updates
├── tests/
│   └── test_mpflipdot.py  # CPython unittest with a fake UART (no hardware)
├── PLAN.md  README.md  LICENSE  .gitignore
```

### API sketch

```python
from machine import UART, Pin
from mpflipdot import FlipDot

uart = UART(0, baudrate=4800, tx=Pin(0), rx=Pin(1))     # see FlipDot.BAUD
sign = FlipDot(uart, address=1, width=84, height=7,
               de_pin=None,        # optional Pin for RS485 driver-enable (DE/RE)
               flip=False,         # sign mounted upside-down
               auto_show=True)     # push to sign after each mutating call

sign.clear()                        # all dots off (sends frame)
sign.fill()                         # all dots on
sign.test(True) / sign.test(False)  # start / stop manufacturer test mode
sign.set_pixel(x, y, True)          # others retained
sign.set_pixels([(0, 0, 1), (5, 3, 0), ...])   # one frame send for the batch
sign.get_pixel(x, y)                # read from local framebuffer
sign.show()                         # explicit send of current framebuffer
```

Design notes:

- **Framebuffer**: a `bytearray` already in the wire layout (column-major,
  `ceil(h/8)` bytes per column). `set_pixel` is then one bit operation, and
  `show()` only has to hex-encode. 84x7 = 84 bytes; trivial RAM on a Pico.
- **`auto_show`**: default on for simplicity; `set_pixels` always batches into
  one send. Turn off for manual `show()` control when drawing many things.
- **Whole-frame replace**: `set_pixels` accepts any iterable of `(x, y, on)`;
  a full frame is just a long iterable. A `load(rows)` helper for a list of
  rows of 0/1 may be added if it stays small.
- **Encoding**: hex via a precomputed 16-char lookup / `"%02X"` into a single
  preallocated `bytearray` to avoid heap churn; no `ubinascii` dependency needed
  (though `binascii.hexlify` is acceptable if smaller).
- **RS485 direction**: optional `de_pin`. Many cheap Pico RS485 modules auto-switch
  direction (no pin needed); others need DE/RE held high while transmitting.
  When given, set high → write → wait for TX to drain → set low.
- **Validation**: bounds-check x/y and address (0–15) with `ValueError`/`IndexError`;
  keep messages short for MicroPython.
- **Packet building** is split into pure functions (`_checksum`, `_packet`) so they
  can be unit-tested on CPython with known byte sequences.

### Testing

1. **Unit tests (CPython, no hardware)** – checksum, packet framing, bit layout for
   84x7 and a second size (including heights > 8 for multi-byte columns), flip, and
   state retention across `set_pixel` calls. Cross-check packet bytes against
   pyflipdot output for the same images (one-off, not a runtime dependency).
2. **On-device smoke tests** – `examples/basic.py` on the Pico: clear → single dot
   → test mode on/off, then the bulk example.

## Milestones

1. Repo scaffolding (this commit): PLAN, README, LICENSE, .gitignore.
2. `mpflipdot.py` core: packet encoding, framebuffer, `clear`, `set_pixel`, `set_pixels`, `test`.
3. Unit tests + pyflipdot cross-check.
4. Examples, then hardware bring-up on the 84x7 sign (pinout, RS485 module details, resolve the open items above).
5. Verify on the second, smaller sign; finalise docs; tag v0.1.0.

## Open questions for the user

- Pico pins and RS485 adapter model (auto-direction or DE/RE?).
- Address of each sign, and size of the second sign.
- Is the Node.js library worth looking at? Only if hardware testing disagrees with the pyflipdot-derived protocol.
- Packaging: plain file copy only, or also `mip` install support (`package.json`)?

## Status / decisions (update)

- Decided: Pico W / 2 W, Waveshare Pico-2CH-RS485 (no DE/RE pin in its pin table, so assumed auto direction; `de_pin` stays optional),
  pins configurable via `open_uart(uart_id, tx, rx)`, addresses/sizes configurable, test mode uses address 0, `mip` install via `package.json`.
- Done: milestones 1-3. Packets verified byte-identical to pyflipdot for 84x7, 20x14, 10x9, 5x16 (flip and non-flip).
- Frames over 255 bytes raise `ValueError` rather than truncating the length.
- MicroPython version: tested target is 1.29.0 on Pico W and Pico 2 W. Unverified expectation of ~1.20+ (mip and rp2 `UART.flush()`);
  the docs give no version-added notes. Only claim what we test; revisit if someone needs an older firmware.

## Hardware findings (20x14 test sign, rotary switch SW2 = 5)

Found by changing one thing at a time, first with a USB-RS485 adapter on a Mac (pyflipdot and this driver), then on the Pico W:

- **Address:** frames only take effect at address **6** (switch + 1) or 0 (broadcast). Test mode is broadcast and works regardless.
- **Row layout:** the top row is **bit 1**, not bit 0 (bit 0 lights nothing; the bottom row is bit 14). Handled by `row_offset=1`.
  A 14-bit fill from bit 0 left the bottom row off.
- **All-zero frames are ignored** by the sign, so a plain "clear" never took effect. `show()` sets one bit that lights no dot
  when the frame would otherwise be all zero. Verified from the Pico with the driver's own `clear()`.
- **Power supply:** a 24 V / 1 A supply made the sign drop frames at random (about half, regardless of content, gap or lead-in/trailing bytes)
  and made every Pico test fail. Swapping to 24 V / 5 A fixed both. Earlier suspicions about the Waveshare board's weak idle level
  (DI tied low, so only 0 bits are driven; 1/idle is a ~40 mV bias into a fixed 120 ohm terminator) and about the USB adapter were wrong;
  no external bias resistors or DE pin are needed.
- **Update rate:** frames 0.5 s and 0.3 s apart all took effect; at 0.2 s frames were skipped. One 88-byte frame takes about 0.18 s at 4800 baud.
- **Host-side USB adapter:** a script that exits straight after writing can lose the last frame; keep the port open for a few seconds.
- **Pico + Waveshare Pico-2CH-RS485:** automatic direction control works as documented. Verified: `fill`, `clear`, `set_pixel` with state
  retention, `set_pixels` (a 64-dot border in one frame), `test(True/False)`, 0.3 s frame cadence.

Open items are listed under "Parked: resume here" at the end.
- 84x7 sign tested on the same 24 V / 5 A supply as the 20x14 sign: address 6 (the rotary switch was not read, so it is probably 5, matching the 20x14), `row_offset=0`, all-zero frames handled by the same workaround.
- `min_gap_ms=300` guard added (blocks until the gap has passed). Verified on the 20x14 sign: a loop sending every 0.2 s, which skipped rows before, showed every row.
- `flip=True` verified on the 20x14 sign (with `row_offset=1`): an L-shape drawn at (0,0) appeared rotated in the bottom-right corner.
- `mpremote mip install github:simonprickett/mpflipdot` verified on the Pico W, twice: first with the single module, then (after commit `76aa15f`) with all three, `mpflipdot.py`, `mpflipdot_draw.py` and `mpflipdot_text.py`, installed to `/lib` after clearing the board, each byte-identical to the repo file. A script importing only from `/lib` drove the sign (circle plus centred text). The on-board `mip.install` path (Wi-Fi) is still untried.
- Pico 2 W (bare MicroPython 1.29.0, nothing else on it) drove the 20x14 on Waveshare channel 1 with `examples/demo.py`, address 6; the user confirmed it worked perfectly. The non-wireless Pico and Pico 2 should work too (nothing wireless-specific is used) but are untested.
- Planned, sometime: try the driver with a single colour Hanover LED sign, to see whether it works with those as well as flip-dot signs. Untested; whether they use the same protocol, and what address, size and row layout they need, is unknown.
- `examples/demo.py` (seven looping patterns, paced by `min_gap_ms`) watched running on the 20x14 sign; looked right with no skipped frames.
- **84x7 timing, handled in software:** `min_gap_ms` is now `None` by default, which waits for the previous packet's send time (length x 10 bits / 4800 baud, rounded up) plus `quiet_ms` (100 ms). That gives 284 ms on the 20x14 (88-byte frames, close to the 300 ms known to work) and 467 ms on the 84x7 (176 bytes, 367 ms to send). A number for `min_gap_ms` is the old fixed start-to-start gap; 0 turns it off. 100 ms of quiet is inferred from two data points (0.2 s dropped frames, 0.3 s did not), so it is a setting. Unit-tested (55 tests). Verified on the 20x14 sign (gap 284 ms) with no dropped frames: the 14-row sweep twice (3697 ms both times), 20 frames of 1 dot and 20 of a 14-dot column (5399 and 5400 ms), 20 inverting checkerboards (5418 ms) and 20 random frames alternating 5 and 275 dots (5406 ms). Frame size on the wire is fixed by the sign, so the dot count only changes the load on the sign. The 84x7 sign (address 6, `row_offset=0`) was then checked too: test mode, `fill`, `clear`, a 7-row sweep twice (2817 ms for 7 frames both times, every row lit in order) and `scroll(sign, "HELLO WORLD", step=5)` (13552 ms, no missing frames). At rest on the 84x7: centred, edge-aligned and clipped text and the punctuation glyphs all looked right. Dense frames, `flip=True` and the drawing demos on the 84x7 are still to do.
  Measured rate on the 20x14 with the old fixed gap: ~3.4 fps (14 frames in 4.1 s). Not measured between 0.2 s and 0.3 s.
- `mpflipdot_draw.py` added: `line(sign, x0, y0, x1, y1, width=1, on=True)` (Bresenham, thickened along the minor axis, clipped to the sign). Unit-tested; `examples/lines.py` watched on the 20x14 sign and looked right. Installs via `package.json` (re-tested with all three modules).
- Frame skip done: `show()` sends nothing when the frame matches the last one sent (`show(force=True)` overrides, `skip_unchanged=False` disables; `test()` resets it). Ran alongside the text demos on the 20x14 sign with no problems seen; the effect of skipping a repeat frame hasn't been looked at on its own.
- `mpflipdot_text.py` added: 5x7 font (bit 0 = top; ASCII space to `]`, plus `|` stored just past that run as a special case, ~315 bytes), `text`, `text_width`, `text_centered`, `scroll_frames`, `scroll`. `text_centered` centres on the drawn dots, not the 5-dot cells. Zero is a plain oval (same as O); `'` is a vertical tick; `[ \ ] |` were added later (`( ) < > + # ! - :` were already there). Unit-tested (51 tests in all); font data checked by rendering every glyph as ASCII art. `examples/text.py`, `text_centered` and the added glyphs have been watched on the 20x14 sign and look right.

- `circle(..., aspect=None)` and `FlipDot(..., aspect=1)` added (60 tests): on the 84x7, circles at aspect 1 looked too tall; four were compared side by side (1.0, 1.25, 1.5, 1.75) and 1.25 looked round. `aspect` widens a circle (its height stays `2 * radius + 1`). Not set anywhere by default; the 20x14 was not compared, so its value is unknown.
- Demos `lines.py` and `shapes.py` ran out of memory on the Pico W at 84 wide because they built long lists of dots; they now set shapes straight into the sign buffer (`frame(*shapes)`), and run fine there with free memory unchanged (~181 KB). `demo.py` still builds lists (e.g. `sparkle`, 588 dots at 84x7) and is untested at that size.

## Ideas for later (suggested, not started)

- **Bigger font / more text:** a taller or bolder font for the 84x7 sign, more symbols, right-aligned text, vertical centring. (`text_centered` already centres on the ink of the fixed-width font; a proportional font would need its own widths.)
- **Bitmap / sprite blit:** draw a small image from bytes or strings at x, y, with transparency. Base for icons and simple games.
- **Scroll pacing:** pick the scroll step from the sign width so it feels smooth at ~3 fps; vertical scroll.
- **Multi-sign helper:** a `Display` wrapper treating several signs on one bus as one wider canvas.
- **Wi-Fi demos (examples only):** NTP clock, weather ticker, message board over HTTP.
- **Hardware tests waiting on kit:** the 84x7 sign, a Pico 2 W with a second Waveshare board, and a single colour Hanover LED sign.

## Parked: resume here

Paused with the 84x7 sign on the Pico W. A wire to the Waveshare board came loose during a `demo.py` run on the 84x7, and the sign stopped responding to frames. Test mode (a broadcast) then did not start either, which pointed at the data wires. The user will solder the wires properly, then resume.

**State when parked**
- Changes since the user's last commit are staged in git for them to commit (I never commit). 60 unit tests pass (`python3 -I -m unittest discover -s tests`). The Pico's `/lib` holds the current `mpflipdot.py`, `mpflipdot_draw.py` and `mpflipdot_text.py` (copied by hand after the `mip` install check).
- The sign may be left in test mode (the last command sent was test-mode start). Send `test(False)` once the wiring works, or power cycle it.
- Working settings: Pico W, UART0 on GP0/GP1 (`open_uart(0, tx=0, rx=1)`), sign data red to A and black to B. 84x7: `address=6`, `row_offset=0`, `aspect=1.25` for circles. 20x14: `address=6`, `row_offset=1`. Both on a 24 V / 5 A supply. The Pico showed up as `/dev/cu.usbmodem1201`, later `usbmodem1101`.

**On resuming, in this order (one test at a time)**
1. `test(True)` (broadcast) to prove the wiring, then `test(False)`.
2. `fill`, then `clear`, at address 6.
3. Re-run `examples/demo.py` on the 84x7 (`W, H = 84, 7`, no `row_offset`, `ROUNDS = 1`). It ran without errors and with memory unchanged (~182 KB free) when the wiring failed, but the sign's response was not trusted, so it counts as untested. It still builds dot lists (e.g. `sparkle`, 588 dots at 84x7) and could be rewritten like `lines.py` and `shapes.py` if memory is a problem.

**Resumed (2026-10-20):** the wiring works again. On the 84x7 from the Pico W on Waveshare channel 1 (UART1, GP4/GP5, `open_uart(1, tx=4, rx=5)`; `address=6`, `row_offset=0`) the user confirmed: a test sequence (fill, clear, 7-row sweep, column sweep, four alternating checkerboards, shrinking box), left-aligned `text` ("69 BULWELL"), only the four corner dots (all 84 columns and 7 rows addressed), and the same text with `flip=True` (rotated 180 degrees). With the backlight switched on (extra power draw, same 24 V / 5 A supply) the user confirmed 20 alternating checkerboards (8928 ms), 20 sparse frames (a dot, then a full column; 9341 ms), a 7-row sweep plus the corner dots (3736 ms) and centred `TESTING 1 2 3` all showed in order with none dropped, at 0.47 s per frame as predicted. The 20x14 has no backlight. One of my scripts showed a blank sign because `text()` only yields dots and I didn't pass them to `set_pixels`.

**Still to do on the 84x7:** `demo.py`, `bounce.py`, and reading the rotary switch (the sign answered at address 6, so it is probably 5).

**Other open items**
- Pico 2 W on the 84x7, and the non-wireless Pico / Pico 2 (untested, expected to work).
- `de_pin`, which needs an RS485 module with DE/RE pins; several signs on one bus.
- On-board `mip.install(...)` over Wi-Fi.
- `aspect` for the 20x14 sign was not compared.
- A single colour Hanover LED sign.
- Software ideas still not started are in "Ideas for later". The suggested order was a bitmap/sprite blit, scroll pacing, then text extras.
- Wiring tip: the break hid itself, because the scripts exit with no error whether or not the sign gets a frame (the sign never replies). When a sign stops responding, send test mode first.

### Next task when resuming (agreed, in this order)

1. **Further testing on the 84x7** (the resume list above): wiring check, then dense frames, `flip=True`, `demo.py`, `bounce.py`, reading the rotary switch.
2. **Drive both signs, the 20x14 and the 84x7, as fast as possible without dropping frames, with the speed worked out dynamically from the sign size and the data.** Where we are:
   - The driver already works the gap out per frame: wait for the previous packet's send time (length x 10 bits / 4800 baud, rounded up) plus `quiet_ms` (100), measured from the start of the previous send. Verified with no drops at 284 ms on the 20x14 (88-byte frames) and 467 ms on the 84x7 (176-byte frames, about 2 frames a second).
   - `quiet_ms=100` is a guess from two data points on the 20x14 only (0.2 s dropped frames and 0.3 s did not, which is about 17 ms and 117 ms of quiet). Nothing between was tried, and the 84x7 may need a different amount. So the fastest safe quiet time is not known for either sign, and may depend on how many dots flip per frame.
   - Ideas to work through: (a) find the smallest `quiet_ms` that never drops a frame on each sign, using dense, worst-case frames (alternating checkerboards, near-empty then near-full), stepping it down from 100 ms; (b) decide whether the quiet time should be a fixed number, scale with the frame size, or depend on the dots that change since the last frame (the sign flips only dots that change, so a small change may need less time; unconfirmed); (c) check whether `uart.write` returns before the bytes are out on the Pico, which affects when the gap really starts; (d) keep skipping unchanged frames and consider sending nothing for tiny no-op changes; (e) possibly a calibration helper or a speed-test example that sends a numbered sequence a person can check.
   - A catch: the sign never replies, so a dropped frame can only be seen by a person watching it. Use patterns where a dropped frame is obvious (a moving single dot, alternating inverse checkerboards, a counter) and one test per prompt, as before. Keep the 24 V / 5 A supply: an underpowered sign also drops frames, and that must not be mistaken for a timing limit.
   - The baud rate is fixed at 4800 as far as we know; the sign's own limits on this are not documented here, so do not assume it can go faster.
   - Whatever is chosen has to stay doable on the original Pico W, and the 20x14 and 84x7 results should go in the README's "Update rate" quirk and the tested-hardware table.

