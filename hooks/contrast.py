"""
The contrast gate.

Every build, for every palette, in both modes: measure the pairs listed in
``theme/contrast.tsv`` and report anything that cannot be read.

    theme/contrast.tsv   ->  fg, bg, min, level, note   (the pairs, as data)
    this file            ->  the colour maths and the verdict

WHY THIS EXISTS
``hooks/theme.py`` proves every token EXISTS. Nothing proved the result was
LEGIBLE. On 2026-08-01 a palette was hand-mapped from another repo, three
contrast calls were made by eye, and two of them were wrong -- one of those
being the colour of every lede and caption on the site. Every check the repo
had passed it green. This is the check that would not have.

WHY THE PAIRS ARE A TSV AND NOT A LIST IN THIS FILE
Same reason the theme is. The threshold becomes a cell Michael can edit, an
exemption becomes a deleted row, and every waiver shows up in a diff instead
of hiding in an ignore-list inside Python. The maths belongs in code; the
policy does not.

WHAT IS DELIBERATELY NOT CHECKED
``hairline`` -- it is designed to be barely visible. Gating it would fail the
design on purpose, and a gate that flags an intentional choice teaches people
to ignore the gate. It is absent from contrast.tsv rather than exempted there,
because the row would only invite someone to "fix" it.

ACTIVE PALETTE FAILS, THE REST WARN
Every palette is measured, but only the ACTIVE one can break the build. A
parked palette cannot hurt a reader today, and failing on it would mean a
palette nobody uses could hold the site hostage. You still learn it is broken
BEFORE you switch to it, which was the whole point of measuring all of them.

``level`` in the TSV is the ceiling, not the floor: a ``warn`` row never fails,
even on the active palette.  ``URITP_CONTRAST_STRICT=1`` promotes every warning
to a failure, for when someone wants the whole house clean.

⚠️ THE ARITHMETIC HAS TO BE RIGHT OR THE GATE LIES, which is worse than no
gate. Two colour spaces are in the grids, so both are parsed:

  * hex -> divide by 255 -> linearise (the sRGB transfer curve)
  * oklch -> OKLab -> LMS -> cube -> the linear-sRGB matrix (ALREADY linear;
    do not linearise again, that is the easy way to get quietly wrong numbers)

Then the WCAG relative luminance (0.2126 R + 0.7152 G + 0.0722 B) and the WCAG
ratio, (lighter + 0.05) / (darker + 0.05).

⚠️ Out-of-gamut oklch is CLAMPED per channel, which is the naive approach and
not true gamut mapping. It is honest for the values we use (all well inside
sRGB) and it errs toward reporting MORE contrast than a browser would show, so
a clamped colour that passes here might still be marginal. Keep palettes in
gamut.

A colour this file cannot parse is REPORTED, not silently skipped: an unchecked
pair that looks checked is the failure mode the gate exists to prevent.

Wired in mkdocs.yml under ``hooks:``, AFTER hooks/theme.py -- it reuses that
module's grid reading and fallback chain rather than re-implementing them, so
the numbers measured here are the numbers the page actually gets.
Documented in theme/README.md.
"""

import math
import os
import re
import sys

_HOOKS = os.path.dirname(os.path.abspath(__file__))
if _HOOKS not in sys.path:
    sys.path.insert(0, _HOOKS)

import theme as _theme       # noqa: E402  (path set above, deliberately)

PAIRS = "contrast.tsv"
KEY = "fg"                   # the column that makes a row real in THIS grid
STRICT = os.environ.get("URITP_CONTRAST_STRICT") == "1"

_HEX = re.compile(r"\A#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\Z")
_OKLCH = re.compile(
    r"\Aoklch\(\s*([\d.]+)(%?)\s+([\d.]+)\s+([\d.]+)\s*\)\Z", re.IGNORECASE
)


def _linear_from_hex(value):
    digits = value.lstrip("#")
    if len(digits) == 3:
        digits = "".join(c * 2 for c in digits)
    out = []
    for i in (0, 2, 4):
        c = int(digits[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def _linear_from_oklch(match):
    """OKLCh -> linear sRGB. The matrix output IS linear-light; it must not go
    through the transfer curve again."""
    lightness = float(match.group(1))
    if match.group(2) == "%":
        lightness /= 100
    chroma = float(match.group(3))
    hue = math.radians(float(match.group(4)))

    a = chroma * math.cos(hue)
    b = chroma * math.sin(hue)

    l_ = lightness + 0.3963377774 * a + 0.2158037573 * b
    m_ = lightness - 0.1055613458 * a - 0.0638541728 * b
    s_ = lightness - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3

    rgb = (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )
    return tuple(min(1.0, max(0.0, c)) for c in rgb)


def _luminance(value):
    """WCAG relative luminance, or None if the colour cannot be parsed."""
    value = value.strip()
    if _HEX.match(value):
        r, g, b = _linear_from_hex(value)
    else:
        match = _OKLCH.match(value)
        if not match:
            return None
        r, g, b = _linear_from_oklch(match)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(fg, bg):
    a, b = _luminance(fg), _luminance(bg)
    if a is None or b is None:
        return None
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def _pairs():
    checks = []
    for row in _theme._read(PAIRS, key=KEY):
        fg, bg = row.get("fg", ""), row.get("bg", "")
        if not bg:
            _theme._fail(PAIRS, "`" + fg + "` has no `bg` to sit on")
        try:
            minimum = float(row.get("min") or 0)
        except ValueError:
            _theme._fail(
                PAIRS, "`" + fg + " on " + bg + "` has a non-numeric `min`"
            )
        if minimum <= 1:
            _theme._fail(
                PAIRS,
                "`" + fg + " on " + bg + "` has min " + str(minimum)
                + "; 1.0 is identical colours, so that check can never fail",
            )
        level = (row.get("level") or "fail").lower()
        if level not in ("fail", "warn"):
            _theme._fail(
                PAIRS,
                "`" + fg + " on " + bg + "` has level `" + level
                + "`; it must be fail or warn",
            )
        checks.append((fg, bg, minimum, level))
    return checks


def on_config(config):
    checks = _pairs()

    named = set()
    for fg, bg, _min, _level in checks:
        named.add(fg)
        named.add(bg)
    unknown = sorted(named - set(_theme.REQUIRED["color"]))
    if unknown:
        _theme._fail(
            PAIRS,
            "names token(s) that do not exist: " + ", ".join(unknown)
            + ". Available: " + ", ".join(_theme.REQUIRED["color"]),
        )

    # The palette the site is actually wearing. Only this one can fail.
    active = _theme._active()
    joins = {row["slug"]: row for row in _theme._read(_theme.JOIN)}
    fallback = joins.get(_theme.DEFAULT) or {}
    live = (joins.get(active) or {}).get("color") or fallback.get("color")

    table = _theme._index("color", _theme.GRID["color"])
    palettes = sorted({
        slug for slug, _mode in table if not slug.startswith("_")
    })

    failures = []
    warnings = []
    worst = {}

    for slug in palettes:
        for mode in _theme.MODES:
            tokens = _theme._compose("color", table, slug, mode)
            for fg, bg, minimum, level in checks:
                ratio = _ratio(tokens[fg], tokens[bg])
                where = slug + " " + mode + ": " + fg + " on " + bg

                if ratio is None:
                    warnings.append(
                        where + " -- NOT MEASURED, a value did not parse"
                    )
                    continue

                key = (slug, mode)
                if key not in worst or ratio < worst[key][0]:
                    worst[key] = (ratio, fg + " on " + bg)

                if ratio >= minimum:
                    continue

                detail = (
                    where + " = " + format(ratio, ".2f") + ":1, needs "
                    + format(minimum, ".1f")
                )
                if slug == live and (level == "fail" or STRICT):
                    failures.append(detail)
                else:
                    if slug != live and level == "fail":
                        detail += "  (parked palette, so a warning)"
                    warnings.append(detail)

    print(
        "contrast: " + str(len(checks)) + " pair(s) x " + str(len(palettes))
        + " palette(s) x 2 modes"
    )
    for (slug, mode), (ratio, pair) in sorted(worst.items()):
        print(
            "  " + slug + " " + mode + " tightest = "
            + format(ratio, ".2f") + ":1  (" + pair + ")"
        )
    for note in warnings:
        print("::warning::contrast: " + note)

    _summary(live, failures, warnings, worst)

    if failures:
        raise ValueError(
            "theme/contrast.tsv: the ACTIVE palette `" + str(live)
            + "` is not readable --\n  " + "\n  ".join(failures)
            + "\nFix the colour in theme/colors.tsv, or change the pair's "
            "`min` or `level` in theme/contrast.tsv and say why in its note."
        )
    return config


def _summary(live, failures, warnings, worst):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return

    lines = ["### 🎨 Contrast", ""]
    if failures:
        lines += [
            "🔴 **The active palette `" + str(live) + "` is not readable.** "
            "The build stopped.",
            "",
        ]
        lines += ["- `" + f + "`" for f in failures]
        lines.append("")
    else:
        lines += [
            "✅ The active palette **`" + str(live) + "`** passes every "
            "enforced pair.",
            "",
        ]

    lines += [
        "| Palette | Mode | Tightest pair | Ratio |",
        "|---|---|---|---|",
    ]
    for (slug, mode), (ratio, pair) in sorted(worst.items()):
        mark = " ⬅️" if slug == live else ""
        lines.append(
            "| `" + slug + "`" + mark + " | " + mode + " | " + pair + " | "
            + format(ratio, ".2f") + ":1 |"
        )

    if warnings:
        lines += [
            "",
            "<details><summary>" + str(len(warnings))
            + " warning(s)</summary>",
            "",
        ]
        lines += ["- " + w for w in warnings]
        lines += ["", "</details>"]

    lines += [
        "",
        "Pairs and thresholds live in `theme/contrast.tsv`. A parked palette "
        "warns rather than fails, so you learn it is broken before you switch "
        "to it. `URITP_CONTRAST_STRICT=1` enforces every warning.",
    ]
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
