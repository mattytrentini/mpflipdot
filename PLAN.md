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
- TODO: replace `simonprickett` in `package.json` and README once the GitHub repo exists; hardware bring-up (84x7 @ 4800 baud, then 20x14).
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

Open items: test the 84x7 sign (address, row layout, whether it needs the blank-frame workaround and what `row_offset` it uses);
test the Pico 2 W against a sign; consider a minimum-gap helper or rate limit in the driver.
- 84x7 sign deferred (swapping it in is awkward); do it later on the same 24 V / 5 A supply as the 20x14 sign.
- `min_gap_ms=300` guard added (blocks until the gap has passed). Verified on the 20x14 sign: a loop sending every 0.2 s, which skipped rows before, showed every row.
- `flip=True` verified on the 20x14 sign (with `row_offset=1`): an L-shape drawn at (0,0) appeared rotated in the bottom-right corner.
- `mpremote mip install github:simonprickett/mpflipdot` verified on the Pico W, twice: first with the single module, then (after commit `76aa15f`) with all three, `mpflipdot.py`, `mpflipdot_draw.py` and `mpflipdot_text.py`, installed to `/lib` after clearing the board, each byte-identical to the repo file. A script importing only from `/lib` drove the sign (circle plus centred text). The on-board `mip.install` path (Wi-Fi) is still untried.
- Pico 2 W has not driven a sign yet; planned. The 84x7 sign is also still to do.
- Planned, sometime: try the driver with a single colour Hanover LED sign, to see whether it works with those as well as flip-dot signs. Untested; whether they use the same protocol, and what address, size and row layout they need, is unknown.
- `examples/demo.py` (seven looping patterns, paced by `min_gap_ms`) watched running on the 20x14 sign; looked right with no skipped frames.
- **84x7 timing, handled in software:** `min_gap_ms` is now `None` by default, which waits for the previous packet's send time (length x 10 bits / 4800 baud, rounded up) plus `quiet_ms` (100 ms). That gives 284 ms on the 20x14 (88-byte frames, close to the 300 ms known to work) and 467 ms on the 84x7 (176 bytes, 367 ms to send). A number for `min_gap_ms` is the old fixed start-to-start gap; 0 turns it off. 100 ms of quiet is inferred from two data points (0.2 s dropped frames, 0.3 s did not), so it is a setting. Unit-tested (55 tests). Verified on the 20x14 sign (gap 284 ms) with no dropped frames: the 14-row sweep twice (3697 ms both times), 20 frames of 1 dot and 20 of a 14-dot column (5399 and 5400 ms), 20 inverting checkerboards (5418 ms) and 20 random frames alternating 5 and 275 dots (5406 ms). Frame size on the wire is fixed by the sign, so the dot count only changes the load on the sign. The 84x7 run is still to do.
  Measured rate on the 20x14 with the old fixed gap: ~3.4 fps (14 frames in 4.1 s). Not measured between 0.2 s and 0.3 s.
- `mpflipdot_draw.py` added: `line(sign, x0, y0, x1, y1, width=1, on=True)` (Bresenham, thickened along the minor axis, clipped to the sign). Unit-tested; `examples/lines.py` watched on the 20x14 sign and looked right. Installs via `package.json` (re-tested with all three modules).
- Frame skip done: `show()` sends nothing when the frame matches the last one sent (`show(force=True)` overrides, `skip_unchanged=False` disables; `test()` resets it). Ran alongside the text demos on the 20x14 sign with no problems seen; the effect of skipping a repeat frame hasn't been looked at on its own.
- `mpflipdot_text.py` added: 5x7 font (bit 0 = top; ASCII space to `]`, plus `|` stored just past that run as a special case, ~315 bytes), `text`, `text_width`, `text_centered`, `scroll_frames`, `scroll`. `text_centered` centres on the drawn dots, not the 5-dot cells. Zero is a plain oval (same as O); `'` is a vertical tick; `[ \ ] |` were added later (`( ) < > + # ! - :` were already there). Unit-tested (51 tests in all); font data checked by rendering every glyph as ASCII art. `examples/text.py`, `text_centered` and the added glyphs have been watched on the 20x14 sign and look right.

## Ideas for later (suggested, not started)

- **Bigger font / more text:** a taller or bolder font for the 84x7 sign, more symbols, right-aligned text, vertical centring. (`text_centered` already centres on the ink of the fixed-width font; a proportional font would need its own widths.)
- **Bitmap / sprite blit:** draw a small image from bytes or strings at x, y, with transparency. Base for icons and simple games.
- **Scroll pacing:** pick the scroll step from the sign width so it feels smooth at ~3 fps; vertical scroll.
- **Multi-sign helper:** a `Display` wrapper treating several signs on one bus as one wider canvas.
- **Wi-Fi demos (examples only):** NTP clock, weather ticker, message board over HTTP.
- **Hardware tests waiting on kit:** the 84x7 sign, a Pico 2 W with a second Waveshare board, and a single colour Hanover LED sign.
