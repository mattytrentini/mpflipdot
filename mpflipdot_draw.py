"""Optional drawing helpers for mpflipdot. Each returns (x, y, on) dots for FlipDot.set_pixels."""


def line(sign, x0, y0, x1, y1, width=1, on=True):
    """Dots for a line from (x0, y0) to (x1, y1), width dots thick, clipped to the sign.

    Bresenham, thickened along the minor axis: a diagonal line comes out about 0.7 x width thick.
    An even width puts its extra dot below / to the right of the centre line.
    on=False gives dots to erase the same line.
    """
    if width < 1:
        raise ValueError("width")
    w, h = sign.width, sign.height
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    horizontal = dx >= dy
    lo = -((width - 1) // 2)
    hi = width // 2
    err = dx - dy
    x, y = x0, y0
    while True:
        for o in range(lo, hi + 1):
            px, py = (x, y + o) if horizontal else (x + o, y)
            if 0 <= px < w and 0 <= py < h:
                yield (px, py, on)
        if x == x1 and y == y1:
            return
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy


def _span(sign, x0, x1, y, on):
    """Dots of the horizontal run x0..x1 on row y, clipped to the sign."""
    if 0 <= y < sign.height:
        for x in range(max(x0, 0), min(x1, sign.width - 1) + 1):
            yield (x, y, on)


def rect(sign, x, y, width, height, solid=False, on=True):
    """Dots for a rectangle with its top-left corner at (x, y), width x height dots, clipped to the sign.

    An outline by default, 1 dot thick; solid=True fills it. Each dot is returned once.
    """
    if width < 1 or height < 1:
        raise ValueError("size")
    x1, y1 = x + width - 1, y + height - 1
    for py in range(max(y, 0), min(y1, sign.height - 1) + 1):
        if solid or py == y or py == y1:
            yield from _span(sign, x, x1, py, on)
        else:
            yield from _span(sign, x, x, py, on)
            if x1 != x:
                yield from _span(sign, x1, x1, py, on)


def circle(sign, cx, cy, radius, solid=False, on=True, aspect=None):
    """Dots for a circle centred on (cx, cy), 2 * radius + 1 dots tall, clipped to the sign.

    An outline by default, 1 dot thick; solid=True fills it. The outline is the edge of the solid disc,
    so the two always match. radius=0 is a single dot. Each dot is returned once.

    aspect stretches it sideways, for signs whose dots are taller than they are wide, so it comes out as an
    ellipse that looks round: 1.25 makes it 1.25 times as wide as it is tall. None uses sign.aspect if the
    sign has one, else 1 (exactly 2 * radius + 1 dots across as well).
    """
    if radius < 0:
        raise ValueError("radius")
    if aspect is None:
        aspect = getattr(sign, "aspect", 1)
    if aspect <= 0:
        raise ValueError("aspect")
    limit = radius * radius + radius
    a2 = aspect * aspect
    half = []  # half[dy] = how far the disc reaches left and right of the centre on row cy +/- dy
    x = int(aspect * (radius + 1))
    for dy in range(radius + 1):
        while x * x > a2 * (limit - dy * dy):
            x -= 1
        half.append(x)
    half.append(-1)  # the row past the end is empty
    for dy in range(radius + 1):
        reach = half[dy]
        # outline: the dots whose neighbour on the next row out is empty, plus the two ends
        inner = half[dy + 1] + 1 if half[dy + 1] < reach else reach
        for py in ((cy,) if dy == 0 else (cy - dy, cy + dy)):
            if solid or inner == 0:
                yield from _span(sign, cx - reach, cx + reach, py, on)
            else:
                yield from _span(sign, cx - reach, cx - inner, py, on)
                yield from _span(sign, cx + inner, cx + reach, py, on)
