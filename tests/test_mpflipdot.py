import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import mpflipdot  # noqa: E402
from mpflipdot import FlipDot, _packet  # noqa: E402


class FakeUART:
    def __init__(self):
        self.sent = []

    def write(self, data):
        self.sent.append(bytes(data))

    def flush(self):
        pass


def make(**kw):
    kw.setdefault("min_gap_ms", 0)  # keep the unit tests fast
    u = FakeUART()
    return u, FlipDot(u, **kw)


class PacketTests(unittest.TestCase):
    def test_test_mode_packets(self):
        # checksum = two's complement of sum("30" + ETX) etc.
        self.assertEqual(bytes(_packet(3, 0)), b"\x0230\x03" + b"%02X" % (-(0x33 + 0x30 + 3) & 0xFF))
        self.assertEqual(bytes(_packet(12, 0)), b"\x02C0\x03" + b"%02X" % (-(0x43 + 0x30 + 3) & 0xFF))

    def test_image_packet_layout(self):
        u, s = make(address=5, width=2, height=9, auto_show=False)
        s.set_pixel(0, 0)  # col 0, byte 0, bit 0
        s.set_pixel(1, 8)  # col 1, byte 1, bit 0
        s.show()
        body = u.sent[0][1:-3]  # strip STX, ETX and checksum
        self.assertEqual(body, b"15" + b"04" + b"01" + b"00" + b"00" + b"01")
        self.assertEqual(u.sent[0][0], 2)

    def test_84x7_length_byte(self):
        u, s = make(width=84, height=7)
        self.assertTrue(u.sent == [])
        s.clear()
        self.assertEqual(u.sent[0][3:5], b"54")
        self.assertEqual(len(u.sent[0]), 1 + 2 + 2 + 84 * 2 + 1 + 2)


class StateTests(unittest.TestCase):
    def test_set_pixel_retains_others(self):
        u, s = make(width=20, height=14)
        s.set_pixel(3, 12)
        s.set_pixel(19, 0)
        s.set_pixel(3, 12, False)
        self.assertFalse(s.get_pixel(3, 12))
        self.assertTrue(s.get_pixel(19, 0))
        self.assertEqual(len(u.sent), 3)

    def test_set_pixels_single_send(self):
        u, s = make()
        s.set_pixels([(0, 0, 1), (1, 1, 1), (0, 0, 0)])
        self.assertEqual(len(u.sent), 1)
        self.assertFalse(s.get_pixel(0, 0))
        self.assertTrue(s.get_pixel(1, 1))

    def test_fill_respects_height(self):
        u, s = make(width=1, height=7, auto_show=False)
        s.fill()
        self.assertEqual(s._buf[0], 0x7F)
        s2 = FlipDot(FakeUART(), width=1, height=10, auto_show=False)
        s2.fill()
        self.assertEqual(list(s2._buf), [0xFF, 0x03])

    def test_row_offset(self):
        u, s = make(width=2, height=14, row_offset=1, auto_show=False)
        s.set_pixel(0, 0)  # top row is bit 1
        s.set_pixel(1, 13)  # bottom row is bit 14
        self.assertEqual(list(s._buf), [0x02, 0x00, 0x00, 0x40])
        s.fill()
        self.assertEqual(list(s._buf), [0xFE, 0x7F, 0xFE, 0x7F])
        s.flip = True
        self.assertTrue(s.get_pixel(0, 0))

    def test_blank_frame_is_never_all_zero(self):
        # the 20x14 sign ignores all-zero frames; send a spare (invisible) bit instead
        u, s = make(address=6, width=20, height=14, row_offset=1)
        s.clear()
        self.assertIn(b"01", u.sent[0][5:-3])
        self.assertEqual(u.sent[0][5:9], b"0100")
        self.assertEqual(list(s._buf), [0] * 40)  # buffer itself stays clear
        u, s = make(width=4, height=7)
        s.clear()
        self.assertEqual(u.sent[0][5:7], b"80")  # bit 7 is above the 7 rows

    def test_min_gap_waits_between_sends(self):
        now = [1000]
        sleeps = []
        real = mpflipdot.ticks_ms, mpflipdot.sleep_ms
        mpflipdot.ticks_ms = lambda: now[0]
        mpflipdot.sleep_ms = lambda ms: (sleeps.append(ms), now.__setitem__(0, now[0] + ms))
        try:
            s = FlipDot(FakeUART(), width=4, height=7, min_gap_ms=300)
            s.set_pixel(0, 0)  # first send never waits
            now[0] += 100
            s.set_pixel(1, 0)  # 100 ms later: wait the other 200
            now[0] += 500
            s.set_pixel(2, 0)  # 500 ms later: no wait
        finally:
            mpflipdot.ticks_ms, mpflipdot.sleep_ms = real
        self.assertEqual(sleeps, [200])

    def _timed(self, **kw):
        """A sign whose clock and sleep are fake: returns (sign, now, sleeps)."""
        now = [1000]
        sleeps = []
        real = mpflipdot.ticks_ms, mpflipdot.sleep_ms
        mpflipdot.ticks_ms = lambda: now[0]
        mpflipdot.sleep_ms = lambda ms: (sleeps.append(ms), now.__setitem__(0, now[0] + ms))
        self.addCleanup(lambda: setattr(mpflipdot, "ticks_ms", real[0]) or setattr(mpflipdot, "sleep_ms", real[1]))
        return FlipDot(FakeUART(), auto_show=False, **kw), now, sleeps

    def test_auto_gap_follows_frame_size(self):
        # 20x14 (row_offset 1): 88 bytes = 880 bits = 184 ms at 4800 baud (rounded up), plus 100 ms quiet
        s, now, sleeps = self._timed(width=20, height=14, row_offset=1, min_gap_ms=None)
        s.show()
        s.show(force=True)  # straight away
        self.assertEqual(sleeps, [284])
        # 84x7: 176 bytes = 367 ms, plus 100 ms quiet
        s, now, sleeps = self._timed(width=84, height=7)
        s.show()
        s.show(force=True)
        self.assertEqual(sleeps, [467])

    def test_auto_gap_counts_from_the_start_of_the_send(self):
        s, now, sleeps = self._timed(width=20, height=14, row_offset=1)
        s.show()
        now[0] += 300  # 300 ms passed since the send began: more than the 284 needed
        s.show(force=True)
        self.assertEqual(sleeps, [])

    def test_auto_gap_uses_the_previous_packet_size(self):
        s, now, sleeps = self._timed(width=84, height=7)
        s.test(True)  # 6 bytes: 13 ms to send (rounded up)
        s.show()
        self.assertEqual(sleeps, [113])

    def test_quiet_ms_and_fixed_gap(self):
        s, now, sleeps = self._timed(width=20, height=14, row_offset=1, quiet_ms=50)
        s.show()
        s.show(force=True)
        self.assertEqual(sleeps, [234])
        s, now, sleeps = self._timed(width=84, height=7, min_gap_ms=300, quiet_ms=50)  # a number ignores frame size
        s.show()
        s.show(force=True)
        self.assertEqual(sleeps, [300])
        s, now, sleeps = self._timed(width=84, height=7, min_gap_ms=0)  # off
        s.show()
        s.show(force=True)
        self.assertEqual(sleeps, [])

    def test_unchanged_frames_are_not_resent(self):
        u, s = make(width=4, height=7)
        s.set_pixel(1, 1)
        self.assertEqual(len(u.sent), 1)
        s.set_pixel(1, 1)  # no change
        s.show()
        self.assertEqual(len(u.sent), 1)
        s.set_pixel(1, 1, False)
        s.set_pixel(1, 1, False)
        self.assertEqual(len(u.sent), 2)
        s.clear()  # blank again after a blank send: skipped
        self.assertEqual(len(u.sent), 2)

    def test_force_and_opt_out(self):
        u, s = make(width=4, height=7)
        s.set_pixel(0, 0)
        s.show(force=True)
        self.assertEqual(len(u.sent), 2)
        self.assertEqual(u.sent[0], u.sent[1])
        u2, s2 = make(width=4, height=7, skip_unchanged=False)
        s2.show()
        s2.show()
        self.assertEqual(len(u2.sent), 2)

    def test_test_mode_resets_the_skip(self):
        u, s = make(width=4, height=7)
        s.set_pixel(0, 0)
        s.test(True)
        s.test(False)
        s.show()  # the sign was left showing something else, so this must go out
        self.assertEqual(len(u.sent), 4)

    def test_flip(self):
        _, s = make(width=4, height=7, flip=True, auto_show=False)
        s.set_pixel(0, 0)
        self.assertEqual(s._buf[3], 1 << 6)
        self.assertTrue(s.get_pixel(0, 0))

    def test_bounds_and_config(self):
        _, s = make()
        with self.assertRaises(IndexError):
            s.set_pixel(84, 0)
        with self.assertRaises(ValueError):
            FlipDot(FakeUART(), address=16)
        with self.assertRaises(ValueError):
            FlipDot(FakeUART(), width=200, height=16)

    def test_test_uses_broadcast_address(self):
        u, s = make(address=7)
        s.test(True)
        self.assertEqual(u.sent[0][1:3], b"30")


if __name__ == "__main__":
    unittest.main()
