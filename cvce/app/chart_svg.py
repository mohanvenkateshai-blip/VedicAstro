"""
chart_svg.py — Server-side South Indian Kundali chart as pure SVG.

No external rendering deps — generates clean SVG strings directly from
chart_data geometry. Suitable for PDF reports, Open Graph images, and
email previews.
"""

from __future__ import annotations

RASHI_SHORT = ["Ar", "Ta", "Ge", "Ca", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi"]
PLANET_SHORT = {
    "Sun": "Su",
    "Moon": "Mo",
    "Mars": "Ma",
    "Mercury": "Me",
    "Jupiter": "Ju",
    "Venus": "Ve",
    "Saturn": "Sa",
    "Rahu": "Ra",
    "Ketu": "Ke",
}

# South Indian chart layout: fixed rashi positions, counter-clockwise
# Row 0: Pi(11) Ar(0) Ta(1) Ge(2)
# Row 1: Cp(10)           Ca(3)
# Row 2: Sg(9)            Le(4)
# Row 3: Sc(7) Li(6) Vi(5)

SOUTH_ORDER = [11, 0, 1, 2, 10, None, None, 3, 9, None, None, 4, 7, 6, 5]
# Positions in a 4x4 grid (row, col)
SOUTH_GRID = {
    11: (0, 0),
    0: (0, 1),
    1: (0, 2),
    2: (0, 3),
    10: (1, 0),
    3: (1, 3),
    9: (2, 0),
    4: (2, 3),
    8: (3, 0),
    7: (3, 1),
    6: (3, 2),
    5: (3, 3),
}


def chart_svg(chart_data: dict, size: int = 400) -> str:
    """Generate a South Indian Kundali SVG from chart_data geometry.

    Args:
        chart_data: Canonical chart_data dict from /chart endpoint.
        size: SVG width/height in pixels.

    Returns:
        Complete SVG string suitable for inline or file serving.
    """
    cell = size / 4.0
    pad = cell * 0.08
    font_body = cell * 0.14
    font_small = cell * 0.10
    font_rashi = cell * 0.11
    stroke = 1.0
    fg = "#F1F5FB"
    dim = "#7E8AA0"
    accent = "#5EE6D0"
    bg = "#0c1220"
    hairline = "#1e293b"

    # Build planet placement: {sign_index: [planet_codes]}
    signs: dict[int, list[str]] = {i: [] for i in range(12)}
    for p in chart_data.get("planets", []):
        si = p.get("signIndex", -1)
        if 0 <= si < 12:
            code = PLANET_SHORT.get(p.get("planet", ""), p.get("planet", ""))
            retro = p.get("retro", False)
            flags = []
            if retro:
                flags.append("(r)")
            signs[si].append(code)
            if flags:
                signs[si].append("".join(flags))

    # Lagna
    lagna_sign = chart_data.get("lagna", {}).get("signIndex", -1)
    if 0 <= lagna_sign < 12:
        signs[lagna_sign].insert(0, "Asc")

    def rx(x):
        return round(x, 1)

    def ry(y):
        return round(y, 1)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {rx(size)} {rx(size)}" width="{rx(size)}" height="{rx(size)}">',
        f'<rect width="{rx(size)}" height="{rx(size)}" fill="{bg}" rx="12"/>',
        # Title
        f'<text x="{rx(size / 2)}" y="{rx(pad + font_body)}" text-anchor="middle" fill="{fg}" font-size="{rx(font_body)}" font-family="sans-serif" font-weight="600">',
        f"{_esc(chart_data.get('meta', {}).get('name', ''))}",
        "</text>",
        f'<text x="{rx(size / 2)}" y="{rx(pad + font_body + font_small + 4)}" text-anchor="middle" fill="{dim}" font-size="{rx(font_small)}" font-family="monospace">',
        f"D1 · {chart_data.get('ayanamsa', '')}",
        "</text>",
    ]

    # Outer border
    parts.append(
        f'<rect x="0" y="0" width="{rx(size)}" height="{rx(size)}" fill="none" stroke="{hairline}" stroke-width="{stroke}" rx="12"/>'
    )

    # Draw cells
    for si, (row, col) in SOUTH_GRID.items():
        x = col * cell
        y = row * cell + 28  # offset for title
        parts.append(
            f'<rect x="{rx(x)}" y="{rx(y)}" width="{rx(cell)}" height="{rx(cell)}" '
            f'fill="none" stroke="{hairline}" stroke-width="{stroke}"/>'
        )
        # Rashi label
        parts.append(
            f'<text x="{rx(x + pad)}" y="{rx(y + pad + font_rashi)}" '
            f'fill="{dim}" font-size="{rx(font_rashi)}" font-family="monospace">{RASHI_SHORT[si]}</text>'
        )
        # Planets
        planets = signs.get(si, [])
        pfont = font_body * 0.85 if len(planets) <= 3 else font_small
        for j, pcode in enumerate(planets):
            py = y + pad + font_rashi + 8 + (j + 1) * (pfont + 4)
            if py > y + cell - pad:
                break
            color = accent if pcode == "Asc" else fg
            parts.append(
                f'<text x="{rx(x + pad)}" y="{rx(py)}" '
                f'fill="{color}" font-size="{rx(pfont)}" font-family="monospace">{_esc(pcode)}</text>'
            )

    # Lagna marker on the correct sign cell
    if 0 <= lagna_sign < 12:
        lrow, lcol = SOUTH_GRID[lagna_sign]
        lx = lcol * cell
        ly = lrow * cell + 28
        parts.append(
            f'<line x1="{rx(lx)}" y1="{rx(ly)}" x2="{rx(lx + cell)}" y2="{rx(ly)}" '
            f'stroke="{accent}" stroke-width="2"/>'
        )
        parts.append(
            f'<line x1="{rx(lx)}" y1="{rx(ly)}" x2="{rx(lx)}" y2="{rx(ly + cell)}" '
            f'stroke="{accent}" stroke-width="2"/>'
        )

    # Footer
    parts.append(
        f'<text x="{rx(size / 2)}" y="{rx(size - pad)}" text-anchor="middle" fill="{dim}" '
        f'font-size="{rx(font_small * 0.8)}" font-family="monospace">'
        f"VedicAstro · Swiss Ephemeris · Lahiri ayanamsa</text>"
    )

    parts.append("</svg>")
    return "\n".join(parts)


def _esc(s: str) -> str:
    """XML-escape a string."""
    if not s:
        return ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
