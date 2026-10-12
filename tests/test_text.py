import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import mpflipdot_text  # noqa: E402
from mpflipdot import FlipDot  # noqa: E402
from mpflipdot_text import scroll, scroll_frames, text, text_centered, text_width  # noqa: E402


class Sign:
    def __init__(self, width=20, height=14):
        self.width = width
        self.height = height


def dots(string, x=0, y=0, sign=None, **kw):
    return set((px, py) for px, py, on in text(sign or Sign(100, 40), string, x, y, **kw))


def art(string, **kw):
    """The text as rows of # and . on a canvas big enough that nothing is clipped."""
    pts = dots(string, **kw)
    w = text_width(string, kw.get("scale", 1))
    h = 7 * kw.get("scale", 1)
    return ["".join("#" if (x, y) in pts else "." for x in range(w)) for y in range(h)]


class FontTests(unittest.TestCase):
    def test_table_shape(self):
        self.assertEqual(len(mpflipdot_text._FONT), (mpflipdot_text._COUNT + 1) * 5)  # the run plus |
        self.assertTrue(all(b < 0x80 for b in mpflipdot_text._FONT))  # 7 rows only

    def test_every_wanted_character_is_distinct_and_drawn(self):
        wanted = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!/.-:'()[]\\<>|"
        shapes = set()
        for ch in wanted:
            shape = frozenset(dots(ch))
            self.assertTrue(shape, ch)
            shapes.add(shape)
        self.assertEqual(len(shapes), len(wanted) - 1)  # all different except 0 and O, which match
        self.assertEqual(dots("0"), dots("O"))
        self.assertEqual(dots(" "), set())

    def test_some_glyphs_exactly(self):
        self.assertEqual(art("L"), ["#....", "#....", "#....", "#....", "#....", "#....", "#####"])
        self.assertEqual(art("T"), ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."])
        self.assertEqual(art("."), [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."])
        self.assertEqual(art("H"), ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"])
        self.assertEqual(art("/"), [".....", "....#", "...#.", "..#..", ".#...", "#....", "....."])
        self.assertEqual(art("1")[0], "..#..")
        self.assertEqual(art("0"), [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."])  # no slash
        self.assertEqual(art("'"), ["..#..", "..#..", "..#..", ".....", ".....", ".....", "....."])
        self.assertEqual(art("[")[:3], [".###.", ".#...", ".#..."])
        self.assertEqual(art("["), [r[::-1] for r in art("]")])  # ] is [ mirrored
        self.assertEqual(art("("), [r[::-1] for r in art(")")])  # ( and ) mirror each other
        self.assertEqual(art("\\"), [r[::-1] for r in art("/")])  # backslash is / mirrored
        self.assertEqual(art("|"), ["..#.."] * 7)  # full height
        self.assertEqual(art("<"), ["...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."])
        self.assertEqual(art(">"), [".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."])
        self.assertEqual(art("-"), [".....", ".....", ".....", "#####", ".....", ".....", "....."])
        self.assertEqual(art(":"), [".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."])


class TextTests(unittest.TestCase):
    def test_centered(self):
        sign = Sign(20, 14)
        got = set((x, y) for x, y, on in text_centered(sign, "HI", 3))
        self.assertEqual(got, set((x, y) for x, y, on in text(sign, "HI", 5, 3)))  # ink is 10 dots wide (the I leaves a blank column), so (20 - 10) // 2
        scaled = set((x, y) for x, y, on in text_centered(sign, "H", 0, scale=2))
        self.assertEqual(min(x for x, _ in scaled), 5)  # (20 - 10) // 2
        self.assertEqual(max(x for x, _ in scaled), 14)

    def test_centred_on_the_ink_not_the_cell(self):
        sign = Sign(20, 14)

        def span(string, scale=1):
            xs = [x for x, _, _ in text_centered(sign, string, 0, scale)]
            return min(xs), max(xs)

        self.assertEqual(span("I"), (8, 10))     # 3 dots wide, not the 5-dot cell
        self.assertEqual(span("."), (9, 10))     # 2 dots wide
        self.assertEqual(span("!"), (9, 9))      # a single column
        self.assertEqual(span("H"), (7, 11))     # full cell: same as cell centring
        self.assertEqual(span("I", 2), (7, 12))  # scaled
        self.assertEqual(span("ABC"), (1, 17))
        self.assertEqual(span("a b"), span("A B"))  # lowercase is the same text
        for s in ("I.", ".I", "1", ":", "ABC"):
            lo, hi = span(s)
            self.assertLessEqual(abs(lo - (19 - hi)), 1, s)  # left and right margins within one dot
        self.assertEqual(list(text_centered(sign, "   ", 0)), [])  # nothing to draw, nothing returned
        self.assertEqual(list(text_centered(sign, "", 0)), [])
        wide = set((x, y) for x, y, on in text_centered(Sign(10, 14), "ABCD"))  # 23 wide: clipped both ends
        self.assertTrue(wide and all(0 <= x < 10 for x, _ in wide))
        self.assertTrue(all(on is False for _, _, on in text_centered(sign, "A", on=False)))

    def test_width(self):
        self.assertEqual([text_width(s) for s in ("", "A", "AB", "ABC")], [0, 5, 11, 17])
        self.assertEqual([text_width(s, 2) for s in ("", "A", "AB")], [0, 10, 22])

    def test_position_offsets_the_text(self):
        base = dots("HI")
        self.assertEqual(dots("HI", 3, 4), {(x + 3, y + 4) for x, y in base})

    def test_characters_are_six_dots_apart(self):
        self.assertEqual(dots("II", 0, 0), dots("I") | {(x + 6, y) for x, y in dots("I")})

    def test_lowercase_matches_uppercase_and_unknown_is_blank(self):
        self.assertEqual(dots("hello 1"), dots("HELLO 1"))
        self.assertEqual(dots("A~B"), dots("A B"))
        self.assertEqual(dots("AéB"), dots("A B"))

    def test_scale(self):
        one, two = dots("A"), dots("A", scale=2)
        self.assertEqual(two, {(x * 2 + dx, y * 2 + dy) for x, y in one for dx in (0, 1) for dy in (0, 1)})
        self.assertEqual(max(y for _, y in two), 13)  # 14 rows tall
        self.assertEqual(dots("AB", scale=3) & {(x, y) for x in range(15) for y in range(21)}, dots("A", scale=3))

    def test_clipping(self):
        s = Sign(20, 14)
        for string, x, y in (("ABC", -4, -3), ("ABC", 15, 10), ("ABCDEFG", 0, 0), ("A", -10, 0), ("A", 25, 0), ("A", 0, 20)):
            for px, py in dots(string, x, y, sign=s):
                self.assertTrue(0 <= px < 20 and 0 <= py < 14, (string, x, y, px, py))
        self.assertEqual(dots("A", -10, 0, sign=s), set())
        self.assertEqual(dots("A", 25, 0, sign=s), set())
        self.assertEqual(dots("A", 0, 20, sign=s), set())
        # an A starting 2 dots off the left edge shows just its last 3 columns
        full = dots("A")
        self.assertEqual(dots("A", -2, 0, sign=s), {(x - 2, y) for x, y in full if x >= 2})

    def test_on_flag_and_bad_scale(self):
        self.assertTrue(all(on is False for _, _, on in text(Sign(), "AB", 0, 0, on=False)))
        with self.assertRaises(ValueError):
            list(text(Sign(), "A", 0, 0, scale=0))


class ScrollTests(unittest.TestCase):
    def test_frames_move_right_to_left_and_end_blank(self):
        s = Sign(20, 14)
        frames = [set((x, y) for x, y, _ in f) for f in scroll_frames(s, "HI", y=2, step=3)]
        self.assertEqual(frames[0], dots("HI", 17, 2, sign=s))
        self.assertEqual(frames[1], dots("HI", 14, 2, sign=s))
        self.assertEqual(frames[-1], set())
        self.assertTrue(frames[0] and frames[len(frames) // 2])  # entering, and still on show half way
        # x = 17, 14, ..., -13: the first position at or past -11 (HI is 11 wide) is where it stops
        self.assertEqual(len(frames), 11)
        for k, f in enumerate(frames):
            self.assertEqual(f, dots("HI", 17 - 3 * k, 2, sign=s))

    def test_scroll_sends_one_frame_per_step_and_restores_auto_show(self):
        class U:
            sent = 0

            def write(self, d):
                self.sent += 1

        u = U()
        s = FlipDot(u, width=20, height=14, row_offset=1, min_gap_ms=0, auto_show=True)
        n = len(list(scroll_frames(s, "OK", step=4)))
        scroll(s, "OK", step=4)
        self.assertEqual(u.sent, n)
        self.assertTrue(s.auto_show)
        self.assertFalse(any(s._buf))  # ends blank

    def test_bad_step(self):
        with self.assertRaises(ValueError):
            list(scroll_frames(Sign(), "A", step=0))


if __name__ == "__main__":
    unittest.main()
