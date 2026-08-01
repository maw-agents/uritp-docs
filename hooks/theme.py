"""
The 4-vector theme resolver.

Reads the grids in ``theme/`` and injects the composed result into every page's
``<head>`` as ``--u-*`` custom properties. ``docs/stylesheets/uritp.css``
consumes them and holds no literal colour, font, size or radius of its own.

    theme/active.txt   ->  one slug
    theme/themes.tsv   ->  that slug's row: colour x typography x forms x spacing
    theme/*.tsv        ->  the four grids those four names point into

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

``_base`` is the safety net and must be COMPLETE -- it is what a half-written
row resolves against. ``_default`` is the join's equivalent.

⚠️ An empty cell is INHERIT, never "nothing". A token that wants to be off
says so with a real value: ``shadow`` is the word ``none``, not a blank.

WHY A BAD NAME STILL FAILS THE BUILD
The house rule is that failures should be local and visible, not global and
silent -- a dead link marks one link, a missing gate key locks one page. A
theme has no page to fail on: it is the whole site or nothing. And a theme
that quietly fell back to something else is precisely the invisible failure
that rule exists to prevent. So this raises, names the file, and lists what IS
defined; the PR build check catches it on the branch before it reaches main.

REQUIRED is owned HERE, not in the grids, and deliberately: the stylesheet is
what consumes these names, so the code that pairs with the stylesheet is what
knows which ones may not be missing. After the whole chain resolves, a token
still absent fails BY NAME rather than rendering one element invisible.

Wired in mkdocs.yml under ``hooks:``. Documented in theme/README.md.
"""

import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "theme")

ACTIVE = os.path.join(DIR, "active.txt")
JOIN = os.path.join(DIR, "themes.tsv")

VECTORS = ("color", "typography", "forms", "spacing")
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

# Every token docs/stylesheets/uritp.css reads. Adding a var() there means
# adding its name here AND a column to that vector's grid, in the SAME PR.
REQUIRED = {
    "color": (
        "bg surface-1 surface-2 border hairline text text-strong text-soft "
        "accent accent-hover on-accent chrome on-chrome marker bad"
    ).split(),
    "typography": (
        "font-body font-mono fs-body fs-lead fs-sm fs-xs fs-h1-min "
        "fs-h1-fluid fs-h1-max fs-h2 fs-h3 lh-body lh-tight track-body "
        "track-tight track-caps"
    ).split(),
    "forms": "radius radius-lg border-w rule-w shadow motion ease focus-w".split(),
    "spacing": "touch pad-cell pad-block gap-xs gap-md gap-lg measure".split(),
}

# Colour is the only vector with modes, because the site has a scheme toggle.
MODES = {
    "dark": "[data-md-color-scheme=slate]",
    "light": "[data-md-color-scheme=default]",
}

_style = ""
_trace = []


def _fail(where, message):
    raise ValueError("theme/" + where + ": " + message)


def _read(filename):
    """A grid as a list of dicts. Values are stripped -- a trailing space in a
    spreadsheet cell is invisible and would otherwise become part of a colour.
    A short row (fewer cells than headers) reads as empty, not as None."""
    path = os.path.join(DIR, filename)
    if not os.path.exists(path):
        _fail(filename, "file is missing")
    with open(path, encoding="utf-8", newline="") as fh:
        rows = []
        for raw in csv.DictReader(fh, delimiter="\t"):
            row = {}
            for key, value in raw.items():
                if key is None:
                    continue
                row[key.strip()] = (value or "").strip()
            if row.get("slug"):
                rows.append(row)
    if not rows:
        _fail(filename, "no rows")
    return rows


def _index(vector, rows):
    """Colour rows are keyed by (slug, mode); everything else by slug."""
    table = {}
    for row in rows:
        if vector == "color":
            mode = row.get("mode", "")
            if mode not in MODES:
                _fail(
                    GRID[vector],
                    "row `" + row["slug"] + "` has mode `" + mode
                    + "`; it must be dark or light",
                )
            table[(row["slug"], mode)] = row
        else:
            table[row["slug"]] = row
    return table


def _slugs(table):
    seen = []
    for key in table:
        slug = key[0] if isinstance(key, tuple) else key
        if slug not in seen and not slug.startswith("_"):
            seen.append(slug)
    return ", ".join(sorted(seen)) or "(none)"


def _compose(vector, table, slug, mode=None):
    """Walk the inherits chain, then fall through to _base. First value wins,
    so the row you named always beats what it inherits."""
    filename = GRID[vector]
    tokens = {}
    chain = []
    current = slug

    while current:
        if current in chain:
            _fail(
                filename,
                "`inherits` loops: " + " -> ".join(chain + [current]),
            )
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

    base_key = (BASE, mode) if vector == "color" else BASE
    base = table.get(base_key)
    if base is None:
        _fail(filename, "no `" + BASE + "` row; it is the fallback and is required")
    filled = []
    for name, value in base.items():
        if name in META or not value:
            continue
        if name not in tokens:
            tokens[name] = value
            filled.append(name)

    label = " <- ".join(chain)
    if filled:
        label += " <- " + BASE + " (" + ", ".join(sorted(filled)) + ")"
    _trace.append("  " + vector + (":" + mode if mode else "") + " = " + label)

    missing = [k for k in REQUIRED[vector] if k not in tokens]
    if missing:
        _fail(
            filename,
            "`" + slug + "`" + ((" " + mode) if mode else "")
            + " resolves without token(s): " + ", ".join(missing)
            + ". Add the column, or fill it in `" + BASE + "`.",
        )
    return tokens


def _declare(tokens, vector):
    """Only the tokens the stylesheet actually reads. A `note` is prose for a
    human and has no business in the CSS."""
    return "".join(
        "--u-" + key + ":" + tokens[key] + ";" for key in REQUIRED[vector]
    )


def _block(selector, body):
    return selector + "{" + body + "}"


def on_config(config):
    global _style
    del _trace[:]

    if not os.path.exists(ACTIVE):
        _fail("active.txt", "file is missing; it names the live theme")
    with open(ACTIVE, encoding="utf-8") as fh:
        active = "".join(
            line.split("#")[0].strip()
            for line in fh
            if line.split("#")[0].strip()
        )
    if not active:
        _fail("active.txt", "is empty; it must hold one theme slug")

    joins = _index("join", _read("themes.tsv")) if False else {
        row["slug"]: row for row in _read("themes.tsv")
    }

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
            "`" + active + "` is not a row in themes.tsv. Available: "
            + _slugs(joins),
        )

    fallback = joins.get(DEFAULT)
    if fallback is None:
        _fail("themes.tsv", "no `" + DEFAULT + "` row; it fills empty cells")

    chosen = {}
    for vector in VECTORS:
        name = theme.get(vector) or fallback.get(vector)
        if not name:
            _fail(
                "themes.tsv",
                "`" + active + "` names no " + vector
                + " and `" + DEFAULT + "` does not fill it either",
            )
        chosen[vector] = name

    css = []
    palette = _index("color", _read(GRID["color"]))
    for mode, selector in MODES.items():
        tokens = _compose("color", palette, chosen["color"], mode)
        css.append(_block(selector, _declare(tokens, "color")))

    root = ""
    for vector in ("typography", "forms", "spacing"):
        table = _index(vector, _read(GRID[vector]))
        tokens = _compose(vector, table, chosen[vector])
        root += _declare(tokens, vector)
    css.insert(0, _block(":root", root))

    _style = '<style id="u-theme">' + "".join(css) + "</style>"

    # Printed every build so a fallback that fired is visible in the log,
    # rather than being the quiet thing nobody notices for a month.
    print(
        "theme: " + active + " = "
        + " x ".join(chosen[v] for v in VECTORS)
    )
    for line in _trace:
        print(line)
    return config


def on_post_page(output, page, config):
    """Last thing in <head>, so these declarations win any tie with Material's
    own scheme variables without needing a specificity trick."""
    return output.replace("</head>", _style + "</head>", 1)
