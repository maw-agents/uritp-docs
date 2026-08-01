"""
Colour parsing and WCAG contrast, and nothing else.

No MkDocs, no TSV, no knowledge of this site. Pure functions in, numbers out,
so the arithmetic can be read and checked on its own. hooks/theme.py imports
this by path and owns every decision about WHICH pairs get checked.

[!] IF THIS FILE IS WRONG, THE GATE LIES, which is worse than having no gate.
A check nobody trusts gets switched off; a check that quietly passes bad values
teaches you the palette was fine. So the working is written out rather than
compressed, and every constant is attributable to a spec.

THE PIPELINE, and why it is two different paths

    #rrggbb   -> sRGB 0..1 -> UNDO GAMMA    -> linear RGB
    oklch()   -> OKLab -> LMS -> matrix     -> linear RGB  (already linear)

    linear RGB -> 0.2126 R + 0.7152 G + 0.0722 B -> relative luminance
    two luminances -> (lighter + .05) / (darker + .05) -> contrast ratio

The two formats meet at LINEAR RGB, which is the only place a comparison is
meaningful. A hex value is gamma-encoded and must be linearised first; the
OKLab matrix already emits linear light, so linearising it again would be the
classic double-gamma bug -- it would report every oklch colour as darker than
it is and fail palettes that are fine.

SOURCES
  * Gamma transfer, luminance coefficients and the ratio formula: WCAG 2.1,
    the 'relative luminance' and 'contrast ratio' definitions.
  * OKLab matrices: Bjorn Ottosson's reference implementation (oklab, 2020).
"""

import math
import re

# WCAG relative-luminance weights, applied to LINEAR light.
R_WEIGHT = 0.2126
G_WEIGHT = 0.7152
B_WEIGHT = 0.0722

# sRGB gamma transfer, WCAG's piecewise form.
GAMMA_KNEE = 0.04045
GAMMA_SLOPE = 12.92
GAMMA_OFFSET = 0.055
GAMMA_SCALE = 1.055
GAMMA_EXP = 2.4

_HEX = re.compile('^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')
_OKLCH = re.compile(
    '^oklch\\(\\s*([0-9.]+)(%?)\\s+([0-9.]+)\\s+([0-9.]+)(?:deg)?\\s*\\)$',
    re.IGNORECASE,
)


class ColorError(ValueError):
    """A value this module cannot read. Raised rather than guessed at: a colour
    we cannot parse is a colour we cannot check, and silently skipping it would
    leave a hole in the gate exactly where somebody wrote something unusual."""


def _srgb_to_linear(channel):
    """Undo the sRGB gamma curve on one 0..1 channel."""
    if channel <= GAMMA_KNEE:
        return channel / GAMMA_SLOPE
    return ((channel + GAMMA_OFFSET) / GAMMA_SCALE) ** GAMMA_EXP


def _from_hex(text):
    """#rgb or #rrggbb -> linear RGB."""
    digits = _HEX.match(text).group(1)
    if len(digits) == 3:
        digits = ''.join(ch * 2 for ch in digits)
    channels = [int(digits[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(_srgb_to_linear(c) for c in channels)


def _from_oklch(text):
    """oklch(L C H) -> linear RGB, via OKLab and LMS.

    L is accepted as either 0.62 or 62%; both spellings appear in the wild and
    CSS treats them the same.
    """
    raw_l, percent, raw_c, raw_h = _OKLCH.match(text).groups()
    lightness = float(raw_l)
    if percent or lightness > 1:
        lightness /= 100
    chroma = float(raw_c)
    hue = math.radians(float(raw_h))

    # Polar -> cartesian. OKLCH is OKLab in polar form, nothing more.
    a = chroma * math.cos(hue)
    b = chroma * math.sin(hue)

    # OKLab -> non-linear LMS, then cube to linear LMS.
    l_ = lightness + 0.3963377774 * a + 0.2158037573 * b
    m_ = lightness - 0.1055613458 * a - 0.0638541728 * b
    s_ = lightness - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3

    # LMS -> linear sRGB.
    return (
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def to_linear(value):
    """Any supported colour string -> linear RGB, clamped to the display gamut.

    [!] THE CLAMP IS NOT TIDINESS. An oklch value can name a colour sRGB cannot
    show, and the matrix then returns a channel below 0 or above 1. A negative
    channel would SUBTRACT luminance and make a colour measure darker than
    black. The browser clamps when it paints, so clamping here measures what a
    reader actually sees rather than what the notation asked for.
    """
    text = str(value).strip()
    if _HEX.match(text):
        rgb = _from_hex(text)
    elif _OKLCH.match(text):
        rgb = _from_oklch(text)
    else:
        raise ColorError(
            'cannot read colour `' + text + '`. This gate understands '
            '#rrggbb and oklch(L C H).'
        )
    return tuple(min(1.0, max(0.0, channel)) for channel in rgb)


def luminance(value):
    """WCAG relative luminance, 0 (black) to 1 (white)."""
    r, g, b = to_linear(value)
    return R_WEIGHT * r + G_WEIGHT * g + B_WEIGHT * b


def ratio(foreground, background):
    """WCAG contrast ratio, 1.0 (identical) to 21.0 (black on white).

    Symmetric on purpose: the brighter of the two is always the numerator, so
    getting fg and bg the wrong way round in the data cannot produce a
    flattering number.
    """
    a = luminance(foreground)
    b = luminance(background)
    light, dark = (a, b) if a > b else (b, a)
    return (light + 0.05) / (dark + 0.05)


# -- Self-check --------------------------------------------------------------
# Anchors whose values are fixed by the spec, not by our taste. Run
# `python hooks/color.py` to confirm the arithmetic before trusting a report.
if __name__ == '__main__':
    checks = [
        ('#000000', '#ffffff', 21.0),    # the defined maximum
        ('#ffffff', '#ffffff', 1.0),     # the defined minimum
        ('#777777', '#ffffff', 4.478),   # the classic mid-grey worked example
    ]
    ok = True
    for fg, bg, expected in checks:
        got = ratio(fg, bg)
        good = abs(got - expected) < 0.01
        ok = ok and good
        print(
            ('  ok  ' if good else '  FAIL')
            + '  ' + fg + ' on ' + bg
            + '  expected ' + str(expected) + ', got ' + str(round(got, 3))
        )

    # oklch and hex naming the same colour must agree. White is exact in both,
    # so any drift here is the OKLab path being wrong rather than rounding.
    delta = abs(luminance('oklch(100% 0 0)') - luminance('#ffffff'))
    good = delta < 0.001
    print(('  ok  ' if good else '  FAIL')
          + '  oklch white == hex white (delta ' + str(round(delta, 6)) + ')')
    print('self-check ' + ('passed' if ok and good else 'FAILED'))
