import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mpflipdot_draw import line, rect, circle  # noqa: E402


class Sign:
    def __init__(self, width=20, height=14):
        self.width = width
        self.height = height


def dots(*args, **kw):
    return set((x, y) for x, y, on in line(Sign(), *args, **kw))


class LineTests(unittest.TestCase):
    def test_horizontal_and_vertical(self):
        self.assertEqual(dots(2, 3, 5, 3), {(2, 3), (3, 3), (4, 3), (5, 3)})
        self.assertEqual(dots(4, 1, 4, 3), {(4, 1), (4, 2), (4, 3)})

    def test_single_point(self):
        self.assertEqual(dots(7, 7, 7, 7), {(7, 7)})

    def test_diagonal(self):
        self.assertEqual(dots(0, 0, 3, 3), {(0, 0), (1, 1), (2, 2), (3, 3)})
        self.assertEqual(dots(3, 0, 0, 3), {(3, 0), (2, 1), (1, 2), (0, 3)})

    def test_endpoints_always_included_and_connected(self):
        for x1, y1 in ((19, 13), (0, 13), (19, 0), (7, 2), (3, 12), (10, 13)):
            d = dots(0, 0, x1, y1)
            self.assertIn((0, 0), d)
            self.assertIn((x1, y1), d)
            self.assertEqual(len(d), max(x1, y1) + 1)  # one dot per step on the major axis

    def test_width_is_thickened_along_minor_axis(self):
        self.assertEqual(dots(2, 5, 4, 5, width=3), {(x, y) for x in (2, 3, 4) for y in (4, 5, 6)})
        self.assertEqual(dots(5, 2, 5, 4, width=3), {(x, y) for x in (4, 5, 6) for y in (2, 3, 4)})

    def test_even_width_extra_dot_below_or_right(self):
        self.assertEqual(dots(2, 5, 4, 5, width=2), {(x, y) for x in (2, 3, 4) for y in (5, 6)})
        self.assertEqual(dots(5, 2, 5, 4, width=2), {(x, y) for x in (5, 6) for y in (2, 3, 4)})

    def test_clipped_to_the_sign(self):
        d = dots(-5, 3, 25, 3)
        self.assertEqual(d, {(x, 3) for x in range(20)})
        self.assertEqual(dots(-9, -9, -2, -2), set())
        self.assertEqual(dots(0, 0, 5, 0, width=3), {(x, y) for x in range(6) for y in (0, 1)})

    def test_on_flag_and_tuple_shape(self):
        self.assertEqual(list(line(Sign(), 0, 0, 1, 0)), [(0, 0, True), (1, 0, True)])
        self.assertTrue(all(on is False for _, _, on in line(Sign(), 0, 0, 3, 0, on=False)))

    def test_bad_width(self):
        with self.assertRaises(ValueError):
            list(line(Sign(), 0, 0, 1, 1, width=0))

    def test_feeds_set_pixels(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from mpflipdot import FlipDot

        class U:
            sent = 0

            def write(self, d):
                self.sent += 1

        u = U()
        s = FlipDot(u, width=20, height=14, row_offset=1, min_gap_ms=0)
        s.set_pixels(line(s, 0, 0, 19, 13, width=2))
        self.assertEqual(u.sent, 1)  # whole line in one frame
        self.assertTrue(s.get_pixel(0, 0) and s.get_pixel(19, 13))


def shape(fn, *args, sign=None, **kw):
    out = list(fn(sign or Sign(), *args, **kw))
    pts = [(x, y) for x, y, on in out]
    assert len(pts) == len(set(pts)), "duplicate dots"
    return set(pts)


class RectTests(unittest.TestCase):
    def test_outline_is_default(self):
        d = shape(rect, 2, 3, 4, 3)
        self.assertEqual(d, {(x, y) for x in range(2, 6) for y in range(3, 6)} - {(3, 4), (4, 4)})

    def test_solid(self):
        self.assertEqual(shape(rect, 2, 3, 4, 3, solid=True), {(x, y) for x in range(2, 6) for y in range(3, 6)})

    def test_thin_rects(self):
        self.assertEqual(shape(rect, 1, 1, 4, 1), {(x, 1) for x in range(1, 5)})
        self.assertEqual(shape(rect, 1, 1, 1, 4), {(1, y) for y in range(1, 5)})
        self.assertEqual(shape(rect, 5, 5, 1, 1), {(5, 5)})
        self.assertEqual(shape(rect, 1, 1, 2, 2), {(1, 1), (2, 1), (1, 2), (2, 2)})

    def test_clipped_keeps_only_visible_edges(self):
        # left and top edges are off the sign, so only the right and bottom edges show
        self.assertEqual(shape(rect, -2, -2, 5, 5), {(2, y) for y in range(0, 3)} | {(x, 2) for x in range(0, 3)})
        self.assertEqual(shape(rect, 18, 12, 6, 6, solid=True), {(x, y) for x in (18, 19) for y in (12, 13)})
        self.assertEqual(shape(rect, 30, 30, 4, 4), set())

    def test_on_flag_and_bad_size(self):
        self.assertTrue(all(on is False for _, _, on in rect(Sign(), 0, 0, 3, 3, on=False)))
        for args in ((0, 0, 0, 3), (0, 0, 3, 0), (0, 0, -1, 3)):
            with self.assertRaises(ValueError):
                list(rect(Sign(), *args))


class CircleTests(unittest.TestCase):
    def test_radius_zero_is_one_dot(self):
        self.assertEqual(shape(circle, 5, 5, 0), {(5, 5)})
        self.assertEqual(shape(circle, 5, 5, 0, solid=True), {(5, 5)})

    def test_small_circles(self):
        ring = {(x, y) for x in (4, 5, 6) for y in (4, 5, 6)} - {(5, 5)}
        self.assertEqual(shape(circle, 5, 5, 1), ring)
        self.assertEqual(shape(circle, 5, 5, 1, solid=True), ring | {(5, 5)})
        self.assertEqual(len(shape(circle, 8, 8, 2, solid=True)), 21)
        self.assertEqual(len(shape(circle, 8, 8, 2)), 12)

    def test_outline_is_the_edge_of_the_solid(self):
        for r in range(0, 8):
            big = Sign(40, 40)  # large enough that nothing is clipped
            solid = shape(circle, 20, 20, r, solid=True, sign=big)
            edge = {(x, y) for x, y in solid if not all(n in solid for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))}
            self.assertEqual(shape(circle, 20, 20, r, sign=big), edge, r)

    def test_symmetric_and_diameter(self):
        for r in range(0, 7):
            for solid in (False, True):
                d = shape(circle, 9, 7, r, solid=solid)
                self.assertEqual(d, {(18 - x, y) for x, y in d})  # left-right
                self.assertEqual(d, {(x, 14 - y) for x, y in d})  # up-down
                self.assertEqual(d, {(9 + (y - 7), 7 + (x - 9)) for x, y in d})  # diagonal
                self.assertEqual(max(x for x, _ in d) - min(x for x, _ in d) + 1, 2 * r + 1)
                self.assertEqual(max(y for _, y in d) - min(y for _, y in d) + 1, 2 * r + 1)

    def test_clipped(self):
        d = shape(circle, 0, 0, 3, solid=True)
        self.assertTrue(all(0 <= x < 20 and 0 <= y < 14 for x, y in d))
        self.assertIn((0, 0), d)
        self.assertEqual(shape(circle, -20, 5, 3), set())

    def test_on_flag_and_bad_radius(self):
        self.assertTrue(all(on is False for _, _, on in circle(Sign(), 5, 5, 3, on=False)))
        with self.assertRaises(ValueError):
            list(circle(Sign(), 5, 5, -1))


if __name__ == "__main__":
    unittest.main()
