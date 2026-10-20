"""Optional thick-line drawing that modifies a framebuffer without displaying it."""


def line(sign, x0, y0, x1, y1, width=1, on=True):
    """Draw a line from (x0, y0) to (x1, y1), width dots thick, clipped to the sign.

    Bresenham, thickened along the minor axis: a diagonal line comes out about 0.7 x width thick.
    An even width puts its extra dot below / to the right of the centre line.
    on=False erases the same line. Call sign.show() to display it.
    """
    if width < 1:
        raise ValueError("width")
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    horizontal = dx >= dy
    lo = -((width - 1) // 2)
    hi = width // 2
    err = dx - dy
    x, y = x0, y0
    while True:
        if horizontal:
            sign.vline(x, y + lo, hi - lo + 1, int(on))
        else:
            sign.hline(x + lo, y, hi - lo + 1, int(on))
        if x == x1 and y == y1:
            return
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
