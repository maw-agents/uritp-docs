"""
The 4-vector theme resolver, and the gates that keep a theme honest.

Reads the grids in ``theme/`` and injects the composed result into every page's
``<head>`` as ``--u-*`` custom properties. ``docs/stylesheets/uritp.css``
consumes them and holds no literal colour, font, size or radius of its own.

    theme/active.txt    ->  one slug
    theme/themes.tsv    ->  that slug's row: colour x typography x forms x spacing
    theme/*.tsv         ->  the four grids those four names point into
    theme/contrast.tsv  ->  the pairs that must stay legible

WHY GRIDS AND NOT ONE YAML FILE (changed 2026-08-01, Michael)
The values are a table and a table belongs in a table. ``theme.yml`` held all
four vectors as nested YAML, which meant every tweak was an edit inside a
structured document where indentation is load-bearing and a stray colon kills
the parse -- it cost a build the day it shipped. A TSV opens as a grid on
GitHub, in Numbers, in anything, and a wrong cell is visible as a wrong cell.

WHY TSV AND NOT CSV
Half these values contain commas: font stacks, ``cubic-bezier(.2,.7,.2,1)``,
``rgba(0,0,0,.18)``. Tab-separated means none of them need quoting and none of
them can be broken by a quote that went missing.

THE FALLBACK CHAIN -- one rule, applied at both levels

    An EMPTY CELL inherits. A FILLED CELL wins.

  * ``themes.tsv``: an empty vector cell takes its value from the ``_default``
    row. So a theme that only changes colour names one thing.
  * a vector grid: an empty token cell takes its value from the row named in
    ``inherits``, walking that chain, then from the ``_base`` row of that same
    file. So a palette that only nudges its neutrals names only its neutrals.

``_base`` is the safety net and must be COMPLETE. ``_default`` is the join's
equivalent. An empty cell is INHERIT, never "nothing": a token that wants to be
off says so with a real value (``shadow`` is the word ``none``, not a blank).

THE WEBFONT SEAM IS CLOSED -- this hook writes the config
The typography grid used to say which family the CSS ASKED FOR while
``mkdocs.yml -> theme.font`` said which family Material DOWNLOADED, in a
different file, kept in agreement by hand. ``on_config`` runs before any
template renders, so the grid now SETS ``theme.font`` from its own
``webfont-text`` / ``webfont-code`` columns. One file decides, so the two
cannot disagree. Those two columns are the only ones NOT emitted as CSS.

=======================================================================
THE GATES -- what makes a theme WRONG, as opposed to missing
=======================================================================

Every check below fails the build rather than warning, with one exception
noted. The reasoning is the house rule inverted: failures should be local and
visible, and a theme has NO PAGE to fail locally on -- it is the whole site or
nothing. A theme that quietly rendered unreadable is the invisible failure the
rule exists to prevent.

  1. MISSING TOKEN     a token absent after the whole fallback chain
  2. CONTRAST          a pair in contrast.tsv below its floor, IN ANY PALETTE
  3. ORPHAN TOKEN      a token in REQUIRED that no stylesheet reads (WARNS)
  4. PARKED PALETTE    a palette no theme points at (WARNS)
  5. WEBFONT MISMATCH  font-body asks for a family we never downloaded
  6. DUPLICATE SLUG    two rows claiming one name

WHY CONTRAST CHECKS EVERY PALETTE AND NOT JUST THE ACTIVE ONE
It is arithmetic on a handful of rows and costs nothing, and it means a parked
palette is known-broken BEFORE somebody switches to it rather than after. The
first run of this gate found four failing pairs in a palette added an hour
earlier, all of which had passed a human eye.

WHY THE PAIRS ARE A DATA FILE
``theme/contrast.tsv`` holds fg / bg / min / note. So the threshold is a cell
Michael can edit, an exemption is a deleted row, and every waiver shows up in
a diff -- instead of an ignore-list buried in Python that nobody reviews.

⚠️ ``hairline`` IS DELIBERATELY NOT IN THAT FILE. It is designed to be barely
visible; gating it would fail the design on purpose, and a gate that flags an
intentional choice teaches people to ignore the gate.

⚠️ NON-TEXT CONTRAST (WCAG 1.4.11: 3:1 for control boundaries) IS A KNOWN GAP.
``border`` against ``bg`` is around 1.5:1 in every palette we ship, including
the house one. That is a real finding and it is deliberately NOT gated yet,
because a gate whose first act is to fail every palette gets switched off
rather than obeyed. It needs a design pass, not a threshold. Recorded in
next-build-spec.md so it is a decision rather than an oversight.

Wired in mkdocs.yml under ``hooks:``. Documented in theme/README.md.
"""

import csv
import math
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "theme")
CSS = os.path.join(ROOT, "docs", "stylesheets")

ACTIVE = os.path.join(DIR, "active.txt")

VECTORS = ("color", "typography", "forms", "spacing")
JOIN = "themes.tsv"
PAIRS = "contrast.tsv"
GRID = {
    "color": "colors.tsv",
    "typography": "typography.tsv",
    "forms": "forms.tsv",
    "spacing": "spacing.tsv",
}

BASE = "_base"          # the complete fallback row inside every vector grid
DEFAULT = "_default"    # the same idea, one level up, inside themes.tsv
META = {"slug", "mode", "inherits", "name", "note"}
MAX_HOPS = 8

# Required, but NOT written into the CSS: these configure Material's webfont
# loader instead of describing a style.
NOT_CSS = {"webfont-text", "webfont-code"}
OFF = "none"            # `webfont-text = none` means download nothing

# Every token docs/stylesheets/uritp.css reads, plus the two webfont names.
# Adding a var() to the stylesheet means adding its name here AND a column to
# that vector's grid, in the SAME PR.
REQUIRED = {
    "color": (
        "bg surface-1 surface-2 border hairline text text-strong text-soft "
        "accent accent-hover on-accent chrome on-chrome marker bad"
    ).split(),
    "typography": (
        "webfont-text webfont-code font-body font-mono "
        "fs-body fs-lead fs-sm fs-xs fs-micro fs-nav fs-nav-mobile "
        "fs-h1-min fs-h1-fluid fs-h1-max fs-h2 fs-h3 "
        "lh-body lh-tight track-body track-tight track-caps"
    ).split(),
    "forms": (
        "radius radius-lg border-w rule-w bar-w shadow motion ease "
        "focus-w icon-dim"
    ).split(),
    "spacing": (
        "touch pad-cell pad-block pad-row gap-xs gap-md gap-lg measure"
    ).split(),
}

# Colour is the only vector with modes, because the site has a scheme toggle.
MODES = {
    "dark": "[data-md-color-scheme=slate]",
    "light": "[data-md-color-scheme=default]",
}

_style = ""
_trace = []
_notes = []


def _fail(where, message):
    raise ValueError("theme/" + where + ": " + message)


def _warn(message):
    """Loud in the log, does not stop the build. Used only where failing would
    be wrong -- a parked palette is a real thing somebody meant to leave."""
    _notes.append(message)


# ════════════════════════════════════════════════════════════════════════
#  COLOUR MATH.  Everything below is here so the contrast gate can be told
#  the truth rather than an approximation. It has no dependency, because a
#  build dependency for thirty lines of arithmetic is a bad trade.
# ════════════════════════════════════════════════════════════════════════

_OKLCH = re.compile(
    r"^oklch\(\s*([\d.]+)(%?)\s+([\d.]+)\s+([\d.]+)\s*\)$", re.IGNORECASE
)


def _expand(channel):
    """sRGB 0-1 -> linear light. The WCAG 2.x curve, threshold and all."""
    return (
        channel / 12.92
        if channel <= 0.03928
        else ((channel + 0.055) / 1.055) ** 2.4
    )


def _from_hex(value):
    raw = value[1:]
    if len(raw) == 3:
        raw = "".join(c * 2 for c in raw)
    if len(raw) != 6:
        return None
    try:
        parts = [int(raw[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    except ValueError:
        return None
    return tuple(_expand(p) for p in parts)


def _from_oklch(match):
    """OKLCH -> OKLab -> LMS -> LINEAR sRGB.

    Returns linear light directly, which is what relative luminance wants, so
    there is no gamma round trip to get wrong. Out-of-gamut components are
    clamped: a colour the screen cannot show is shown as the nearest one it
    can, which is also what the browser does.
    """
    lightness = float(match.group(1))
    if match.group(2):                     # written as a percentage
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


def _linear(value):
    """Any colour we allow in a grid -> linear RGB, or None if unparseable."""
    value = value.strip()
    if value.startswith("#"):
        return _from_hex(value)
    match = _OKLCH.match(value)
    return _from_oklch(match) if match else None


def _luminance(rgb):
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def _ratio(one, two):
    """WCAG relative contrast. Order does not matter."""
    a, b = _luminance(one), _luminance(two)
    if a < b:
        a, b = b, a
    return (a + 0.05) / (b + 0.05)


# ════════════════════════════════════════════════════════════════════════
#  READING THE GRIDS
# ════════════════════════════════════════════════════════════════════════


def _read(filename, key="slug"):
    """A grid as a list of dicts. Values are stripped -- a trailing space in a
    spreadsheet cell is invisible and would otherwise become part of a colour.
    A short row (fewer cells than headers) reads as empty, not as None."""
    path = os.path.join(DIR, filename)
    if not os.path.exists(path):
        _fail(filename, "file is missing")
    rows = []
    with open(path, encoding="utf-8", newline="") as fh:
        for raw in csv.DictReader(fh, delimiter="\t"):
            row = {}
            for name, value in raw.items():
                if name is None:
                    continue
                row[name.strip()] = (value or "").strip()
            if row.get(key):
                rows.append(row)
    if not rows:
        _fail(filename, "no rows")
    return rows


def _index(vector, filename):
    """Colour rows are keyed by (slug, mode); everything else by slug.

    ⚠️ A DUPLICATE KEY IS AN ERROR, not a silent overwrite. This used to do
    `table[key] = row` in a loop, so a second row with the same name quietly
    replaced the first and the file you were reading was not the file that
    rendered. The keystore in visibility.py had already ruled on this exact
    case months earlier -- first wins, and SAY SO -- and this disagreed with
    it for nine hours. Same house, same answer.
    """
    table = {}
    for row in _read(filename):
        if vector == "color":
            mode = row.get("mode", "")
            if mode not in MODES:
                _fail(
                    filename,
                    "row `" + row["slug"] + "` has mode `" + mode
                    + "`; it must be dark or light",
                )
            key = (row["slug"], mode)
            label = row["slug"] + " (" + mode + ")"
        else:
            key = row["slug"]
            label = row["slug"]

        if key in table:
            _fail(
                filename,
                "`" + label + "` appears twice. Delete one -- two rows with "
                "one name means the file you read is not the file that "
                "renders.",
            )
        table[key] = row
    return table


def _slugs(table):
    """Public row names, so an error tells you what you CAN use."""
    seen = set()
    for key in table:
        slug = key[0] if isinstance(key, tuple) else key
        if not slug.startswith("_"):
            seen.add(slug)
    return ", ".join(sorted(seen)) or "(none)"


def _compose(vector, table, slug, mode=None, trace=True):
    """Walk the inherits chain, then fall through to _base. First value wins,
    so the row you named always beats what it inherits."""
    filename = GRID[vector]
    tokens = {}
    chain = []
    current = slug

    while current:
        if current in chain:
            _fail(filename, "`inherits` loops: " + " -> ".join(chain + [current]))
        if len(chain) >= MAX_HOPS:
            _fail(filename, "`inherits` chain is too deep from `" + slug + "`")
        chain.append(current)

        key = (current, mode) if vector == "color" else current
        row = table.get(key)
        if row is None:
            detail = "`" + current + "`"
            if mode:
                detail += " (" + mode + ")"
            if current != slug:
                detail += ", inherited from `" + chain[-2] + "`"
            _fail(filename, "no row " + detail + ". Defined: " + _slugs(table))

        for name, value in row.items():
            if name in META or not value:
                continue
            tokens.setdefault(name, value)

        current = row.get("inherits", "")

    base = table.get((BASE, mode) if vector == "color" else BASE)
    if base is None:
        _fail(filename, "no `" + BASE + "` row; it is the fallback and is required")
    filled = []
    for name, value in base.items():
        if name in META or not value:
            continue
        if name not in tokens:
            tokens[name] = value
            filled.append(name)

    if trace:
        label = " <- ".join(chain)
        if filled:
            label += " <- " + BASE + " (" + ", ".join(sorted(filled)) + ")"
        _trace.append("  " + vector + ((":" + mode) if mode else "") + " = " + label)

    missing = [k for k in REQUIRED[vector] if k not in tokens]
    if missing:
        _fail(
            filename,
            "`" + slug + "`" + ((" " + mode) if mode else "")
            + " resolves without token(s): " + ", ".join(missing)
            + ". Add the column, or fill it in `" + BASE + "`.",
        )
    return tokens


# ════════════════════════════════════════════════════════════════════════
#  THE GATES
# ════════════════════════════════════════════════════════════════════════


def _gate_contrast(palettes):
    """Every pair in contrast.tsv, in every palette, in both modes.

    Reports ALL failures rather than stopping at the first: a palette usually
    fails as a family (one background that is too close to everything), and
    fixing them one build at a time would be five round trips.
    """
    pairs = _read(PAIRS, key="fg")
    for pair in pairs:
        if not pair.get("bg"):
            _fail(PAIRS, "row `" + pair["fg"] + "` has no `bg`")
        try:
            pair["_min"] = float(pair.get("min") or 0)
        except ValueError:
            _fail(
                PAIRS,
                "row `" + pair["fg"] + " on " + pair["bg"] + "` has min `"
                + pair["min"] + "`, which is not a number",
            )
        for role in (pair["fg"], pair["bg"]):
            if role not in REQUIRED["color"]:
                _fail(
                    PAIRS,
                    "`" + role + "` is not a colour token. Known: "
                    + ", ".join(REQUIRED["color"]),
                )

    names = sorted({
        slug for slug, _ in palettes if not slug.startswith("_")
    })
    table = _index("color", GRID["color"])

    failures = []
    checked = 0
    for slug in names:
        for mode in MODES:
            tokens = _compose("color", table, slug, mode, trace=False)
            for pair in pairs:
                fg = _linear(tokens[pair["fg"]])
                bg = _linear(tokens[pair["bg"]])
                if fg is None or bg is None:
                    bad = pair["fg"] if fg is None else pair["bg"]
                    _fail(
                        GRID["color"],
                        "`" + slug + "` " + mode + " has `" + bad + " = "
                        + tokens[bad] + "`, which is not a hex or oklch colour "
                        "this build can measure.",
                    )
                checked += 1
                got = _ratio(fg, bg)
                if got + 0.005 < pair["_min"]:
                    failures.append((slug, mode, pair, got))

    print(
        "contrast: " + str(checked) + " pair(s) checked across "
        + str(len(names)) + " palette(s) -- "
        + (str(len(failures)) + " FAILED" if failures else "all pass")
    )
    if not failures:
        return

    lines = [
        "### 🔴 Contrast below the floor",
        "",
        "These pairs are unreadable, or close enough that somebody will "
        "struggle. Raise the lightness difference in `theme/colors.tsv`, or "
        "change the floor in `theme/contrast.tsv` if the pair genuinely does "
        "not need it.",
        "",
        "| Palette | Mode | Pair | Needs | Got |",
        "|---|---|---|---|---|",
    ]
    detail = []
    for slug, mode, pair, got in failures:
        where = pair["fg"] + " on " + pair["bg"]
        detail.append(
            "  " + slug + " " + mode + ": " + where + " is "
            + format(got, ".2f") + ":1, needs " + format(pair["_min"], ".1f")
        )
        lines.append(
            "| `" + slug + "` | " + mode + " | `" + where + "` | "
            + format(pair["_min"], ".1f") + " | **" + format(got, ".2f") + "** |"
        )
    for line in detail:
        print(line)
    _summary(lines + [""])

    _fail(
        PAIRS,
        str(len(failures)) + " pair(s) below the floor:\n" + "\n".join(detail),
    )


def _gate_orphans():
    """A token nothing reads. WARNS, because the honest answer is 'probably
    dead weight' rather than 'definitely wrong' -- a token could be consumed
    by something this crude scan cannot see.

    The mirror of the missing-token check: that one catches a stylesheet
    asking for something the grid lost, this catches a grid still carrying
    something the stylesheet stopped asking for.
    """
    if not os.path.isdir(CSS):
        return
    text = ""
    for name in sorted(os.listdir(CSS)):
        if name.endswith(".css"):
            with open(os.path.join(CSS, name), encoding="utf-8") as fh:
                text += fh.read()

    orphans = []
    for vector, names in REQUIRED.items():
        for token in names:
            if token in NOT_CSS:
                continue
            if ("--u-" + token) not in text:
                orphans.append(vector + "." + token)
    if orphans:
        _warn(
            "token(s) no stylesheet reads: " + ", ".join(orphans)
            + " -- drop the column, or start using it"
        )


def _gate_parked(palettes, joins):
    """A palette no theme points at. WARNS and never fails: parking a palette
    to look at later is a real thing somebody meant to do. But silence lets
    dead rows pile up forever, so the distinction between parked and forgotten
    has to be visible."""
    used = {row.get("color") for row in joins.values() if row.get("color")}
    parked = sorted({
        slug for slug, _ in palettes
        if not slug.startswith("_") and slug not in used
    })
    if parked:
        _warn(
            "palette(s) no theme points at: " + ", ".join(parked)
            + " -- parked, or forgotten?"
        )


def _gate_webfont(config, tokens):
    """Write the family names Material should DOWNLOAD, from the same grid row
    that decided which families the CSS asks for -- then check they agree.

    Material takes `font: false` to mean "load nothing", and it is all or
    nothing: there is no per-face switch. So `none` in one column and a real
    family in the other is a contradiction, and it is refused rather than
    silently resolved in whichever direction happens to be first.

    ⚠️ The agreement check only became POSSIBLE when the seam closed and both
    values landed in one row. Closing a seam did not just remove a failure
    mode, it created a new invariant worth checking.
    """
    text = tokens["webfont-text"]
    code = tokens["webfont-code"]

    if (text == OFF) != (code == OFF):
        _fail(
            GRID["typography"],
            "webfont-text is `" + text + "` and webfont-code is `" + code
            + "`. Material loads webfonts all-or-nothing, so these must both "
            "be `" + OFF + "` or both name a family.",
        )

    if text == OFF:
        config["theme"]["font"] = False
        return OFF

    for column, stack in (("text", "font-body"), ("code", "font-mono")):
        family = text if column == "text" else code
        first = tokens[stack].split(",")[0].strip().strip("'\"")
        if first.lower() != family.lower():
            _fail(
                GRID["typography"],
                "webfont-" + column + " downloads `" + family + "` but "
                + stack + " asks for `" + first + "` first, so the download "
                "is wasted and the page renders something else.",
            )

    config["theme"]["font"] = {"text": text, "code": code}
    return text + " + " + code


# ════════════════════════════════════════════════════════════════════════
#  COMPOSE
# ════════════════════════════════════════════════════════════════════════


def _declare(tokens, vector):
    """Only the tokens the stylesheet actually reads. A `note` is prose for a
    human, and the webfont names configure Material -- neither belongs in CSS."""
    return "".join(
        "--u-" + key + ":" + tokens[key] + ";"
        for key in REQUIRED[vector]
        if key not in NOT_CSS
    )


def _block(selector, body):
    return selector + "{" + body + "}"


def _summary(lines):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _active():
    """One slug. Blank lines and `#` comments are ignored, so the file can
    explain itself without the explanation becoming the theme name."""
    if not os.path.exists(ACTIVE):
        _fail("active.txt", "file is missing; it names the live theme")
    with open(ACTIVE, encoding="utf-8") as fh:
        names = [
            line.split("#")[0].strip()
            for line in fh
            if line.split("#")[0].strip()
        ]
    if not names:
        _fail("active.txt", "is empty; it must hold one theme slug")
    if len(names) > 1:
        # Commenting the old name out is the intended way to park it. Two live
        # names would make the theme depend on line order, silently.
        _fail(
            "active.txt",
            "holds " + str(len(names)) + " names (" + ", ".join(names)
            + "); it must hold exactly one. Comment the others out with #.",
        )
    return names[0]


def on_config(config):
    global _style
    del _trace[:]
    del _notes[:]

    active = _active()

    joins = {}
    for row in _read(JOIN):
        if row["slug"] in joins:
            _fail(JOIN, "`" + row["slug"] + "` appears twice. Delete one.")
        joins[row["slug"]] = row

    if active.startswith("_"):
        _fail(
            "active.txt",
            "`" + active + "` is a fallback row, not a theme. Available: "
            + _slugs(joins),
        )
    theme = joins.get(active)
    if theme is None:
        _fail(
            "active.txt",
            "`" + active + "` is not a row in " + JOIN + ". Available: "
            + _slugs(joins),
        )

    fallback = joins.get(DEFAULT)
    if fallback is None:
        _fail(JOIN, "no `" + DEFAULT + "` row; it is what fills empty cells")

    chosen = {}
    for vector in VECTORS:
        name = theme.get(vector) or fallback.get(vector)
        if not name:
            _fail(
                JOIN,
                "`" + active + "` names no " + vector + " and `" + DEFAULT
                + "` does not fill it either",
            )
        chosen[vector] = name

    css = []
    palette = _index("color", GRID["color"])
    for mode, selector in MODES.items():
        tokens = _compose("color", palette, chosen["color"], mode)
        css.append(_block(selector, _declare(tokens, "color")))

    root = ""
    webfont = ""
    for vector in ("typography", "forms", "spacing"):
        tokens = _compose(vector, _index(vector, GRID[vector]), chosen[vector])
        if vector == "typography":
            webfont = _gate_webfont(config, tokens)
        root += _declare(tokens, vector)
    css.insert(0, _block(":root", root))

    _style = '<style id="u-theme">' + "".join(css) + "</style>"

    # Printed every build so a fallback that fired is VISIBLE in the log,
    # rather than being the quiet thing nobody notices for a month.
    print("theme: " + active + " = " + " x ".join(chosen[v] for v in VECTORS))
    for line in _trace:
        print(line)
    print("  webfont = " + webfont)

    _gate_orphans()
    _gate_parked(list(palette), joins)
    for note in _notes:
        print("::warning::theme: " + note)

    # Last, because it is the expensive one and the loudest.
    _gate_contrast(list(palette))
    return config


def on_post_page(output, page, config):
    """Last thing in <head>, so these declarations win any tie with Material's
    own scheme variables without needing a specificity trick."""
    return output.replace("</head>", _style + "</head>", 1)
