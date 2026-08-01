"""
The 4-vector theme resolver, and the contrast gate.

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

``_base`` is the safety net and must be COMPLETE -- it is what a half-written
row resolves against. ``_default`` is the join's equivalent.

[!] An empty cell is INHERIT, never "nothing". A token that wants to be off
says so with a real value: ``shadow`` is the word ``none``, not a blank.

THE WEBFONT SEAM IS CLOSED (2026-08-01) -- this hook writes the config
Until then the typography grid said which family the CSS ASKED FOR while
``mkdocs.yml -> theme.font`` said which family Material DOWNLOADED, in a
different file, kept in agreement by hand. ``on_config`` runs before any
template renders, so the grid simply SETS ``theme.font`` from its own
``webfont-text`` and ``webfont-code`` columns. One file decides.

THE CONTRAST GATE (added 2026-08-01)
Every check in this file until now proved a token EXISTS. None proved the
result could be READ. That gap was not theoretical: hand-mapping one palette
produced four pairs below the WCAG floor, and every check we had passed them
green.

The PAIRS ARE DATA, in ``theme/contrast.tsv``, for the same reason the palette
is: the threshold becomes a cell, an exemption becomes a deleted row, and
every waiver shows up in a diff instead of hiding in a list inside this file.

SCOPE: every palette in ``colors.tsv``, both modes, every build -- not just the
active one. It is arithmetic on a few dozen pairs and costs nothing, and it
means a parked palette is known-broken BEFORE somebody switches to it.

SEVERITY, and the asymmetry is deliberate:

  * the ACTIVE palette FAILS the build. It is what readers are looking at.
  * a PARKED palette WARNS. Nobody can see it, so it is a defect in waiting
    rather than a defect -- and a build that goes red over a palette nobody
    uses is a build people learn to override.

``URITP_CONTRAST_STRICT=1`` promotes every warning to a failure.
``URITP_CONTRAST_OFF=1`` skips the gate; it exists so a colour experiment can
be deployed and LOOKED AT before it is defensible, and it prints a loud line
saying the gate was skipped.

WHY A BAD NAME STILL FAILS THE BUILD
The house rule is that failures should be local and visible, not global and
silent -- a dead link marks one link, a missing gate key locks one page. A
theme has no page to fail on: it is the whole site or nothing. And a theme
that quietly fell back to something else is precisely the invisible failure
that rule exists to prevent.

REQUIRED is owned HERE, not in the grids, and deliberately: the stylesheet is
what consumes these names, so the code that pairs with the stylesheet is what
knows which ones may not be missing.

Wired in mkdocs.yml under ``hooks:``. Documented in theme/README.md.
"""

import csv
import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(ROOT, "theme")

ACTIVE = os.path.join(DIR, "active.txt")

VECTORS = ("color", "typography", "forms", "spacing")
JOIN = "themes.tsv"
CONTRAST = "contrast.tsv"
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

STRICT = os.environ.get("URITP_CONTRAST_STRICT") == "1"
SKIP = os.environ.get("URITP_CONTRAST_OFF") == "1"

# Every token docs/stylesheets/uritp.css reads, plus the two webfont names.
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
_report = {}


def _load_sibling(name):
    """Import a module living next to this file, by path.

    MkDocs loads each hook by path under a synthetic module name, so a plain
    `import color` would not find it, and a sys.path insertion would risk
    colliding with anything else called `color`. This is explicit and local.
    """
    path = os.path.join(HOOKS, name + ".py")
    spec = importlib.util.spec_from_file_location("uritp_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COLOR = _load_sibling("color")


def _fail(where, message):
    raise ValueError("theme/" + where + ": " + message)


def _read(filename):
    """A grid as a list of dicts. Values are stripped -- a trailing space in a
    spreadsheet cell is invisible and would otherwise become part of a colour.
    A short row (fewer cells than headers) reads as empty, not as None.

    A row whose FIRST column starts with `#` is a comment. That is how these
    files carry their own explanation without a second document to keep in
    sync.
    """
    path = os.path.join(DIR, filename)
    if not os.path.exists(path):
        _fail(filename, "file is missing")
    rows = []
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        first = reader.fieldnames[0] if reader.fieldnames else None
        for raw in reader:
            row = {}
            for key, value in raw.items():
                if key is None:
                    continue
                row[key.strip()] = (value or "").strip()
            if first and row.get(first, "").startswith("#"):
                continue
            if any(row.values()):
                rows.append(row)
    if not rows:
        _fail(filename, "no rows")
    return rows


def _index(vector, filename):
    """Colour rows are keyed by (slug, mode); everything else by slug.

    [!] A DUPLICATE KEY FAILS. It used to overwrite silently, last-wins, which
    contradicted this repo's own keystore rule (first wins, and say so) and
    would let a second `mclaren` row further down the file quietly become the
    real one. Fixed 2026-08-01.
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
            label = "`" + row["slug"] + "` (" + mode + ")"
        else:
            key = row["slug"]
            label = "`" + key + "`"
        if key in table:
            _fail(
                filename,
                "row " + label + " is defined twice. Delete one -- a duplicate "
                "used to overwrite silently, which is how a palette you edited "
                "stops being the one that renders.",
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


def _apply_webfont(config, tokens):
    """Write the family names Material should DOWNLOAD, from the same grid row
    that decided which families the CSS asks for.

    Material takes `font: false` to mean "load nothing", and it is all or
    nothing -- there is no per-face switch. So `none` in one column and a real
    family in the other is a contradiction, and it is refused rather than
    silently resolved in whichever direction happens to be first.
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

    config["theme"]["font"] = {"text": text, "code": code}
    return text + " + " + code


def _pairs():
    """theme/contrast.tsv -> [(fg, bg, minimum, note)]."""
    rows = []
    for row in _read(CONTRAST):
        fg, bg = row.get("fg", ""), row.get("bg", "")
        if not fg or not bg:
            _fail(CONTRAST, "a row is missing `fg` or `bg`")
        try:
            minimum = float(row.get("min", ""))
        except ValueError:
            _fail(
                CONTRAST,
                "`" + fg + " on " + bg + "` has min `" + row.get("min", "")
                + "`, which is not a number",
            )
        for token in (fg, bg):
            if token not in REQUIRED["color"]:
                _fail(
                    CONTRAST,
                    "`" + token + "` is not a colour token. Available: "
                    + ", ".join(REQUIRED["color"]),
                )
        rows.append((fg, bg, minimum, row.get("note", "")))
    return rows


def _check_contrast(palettes, active_palette):
    """Measure every pair against every palette, in both modes.

    Returns (failures, warnings, measurements). A failure is a shortfall in the
    palette that is actually rendering; a warning is the same shortfall in one
    nobody can currently see.
    """
    pairs = _pairs()
    failures, warnings, measurements = [], [], []

    slugs = sorted({
        slug for slug, _mode in palettes if not slug.startswith("_")
    })

    for slug in slugs:
        for mode in sorted(MODES):
            tokens = _compose("color", palettes, slug, mode, trace=False)
            for fg, bg, minimum, note in pairs:
                try:
                    value = COLOR.ratio(tokens[fg], tokens[bg])
                except COLOR.ColorError as problem:
                    _fail(
                        GRID["color"],
                        "`" + slug + "` " + mode + ": " + str(problem),
                    )
                # Rounded before comparing, so a pair that REPORTS 4.5 is not
                # failed for being 4.4996 underneath.
                shown = round(value, 2)
                short = shown < minimum
                record = {
                    "palette": slug,
                    "mode": mode,
                    "pair": fg + " on " + bg,
                    "ratio": shown,
                    "min": minimum,
                    "pass": not short,
                    "active": slug == active_palette,
                    "note": note,
                }
                measurements.append(record)
                if not short:
                    continue
                if slug == active_palette or STRICT:
                    failures.append(record)
                else:
                    warnings.append(record)

    return failures, warnings, measurements


def _line(record):
    return (
        record["palette"] + " " + record["mode"] + ": " + record["pair"]
        + " = " + str(record["ratio"]) + ":1, needs " + str(record["min"])
    )


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
        _fail(
            "active.txt",
            "holds " + str(len(names)) + " names (" + ", ".join(names)
            + "); it must hold exactly one. Comment the others out with #.",
        )
    return names[0]


def on_config(config):
    global _style
    del _trace[:]
    _report.clear()

    active = _active()
    joins = {row["slug"]: row for row in _read(JOIN)}

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
    palettes = _index("color", GRID["color"])
    for mode, selector in MODES.items():
        tokens = _compose("color", palettes, chosen["color"], mode)
        css.append(_block(selector, _declare(tokens, "color")))

    root = ""
    webfont = ""
    for vector in ("typography", "forms", "spacing"):
        tokens = _compose(vector, _index(vector, GRID[vector]), chosen[vector])
        if vector == "typography":
            webfont = _apply_webfont(config, tokens)
        root += _declare(tokens, vector)
    css.insert(0, _block(":root", root))

    _style = '<style id="u-theme">' + "".join(css) + "</style>"

    print("theme: " + active + " = " + " x ".join(chosen[v] for v in VECTORS))
    for line in _trace:
        print(line)
    print("  webfont = " + webfont)

    # -- the contrast gate --------------------------------------------------
    if SKIP:
        print("::warning::contrast: GATE SKIPPED (URITP_CONTRAST_OFF=1). "
              "Nothing was measured.")
        _report["skipped"] = True
        return config

    failures, warnings, measurements = _check_contrast(palettes, chosen["color"])
    _report.update({
        "active_palette": chosen["color"],
        "strict": STRICT,
        "checked": len(measurements),
        "failures": failures,
        "warnings": warnings,
        "measurements": measurements,
    })

    print("contrast: " + str(len(measurements)) + " pairs measured, "
          + str(len(failures)) + " failing, " + str(len(warnings))
          + " warning")

    for record in warnings:
        print("::warning::contrast: " + _line(record)
              + " (parked palette, not rendering)")

    if failures:
        detail = "; ".join(_line(record) for record in failures)
        _fail(
            CONTRAST,
            str(len(failures)) + " pair(s) below the floor in the ACTIVE "
            "palette -- " + detail + ". Fix the colour, or change the `min` "
            "cell, or delete the row if the pair should not be checked.",
        )

    return config


def on_post_page(output, page, config):
    """Last thing in <head>, so these declarations win any tie with Material's
    own scheme variables without needing a specificity trick."""
    return output.replace("</head>", _style + "</head>", 1)


def on_post_build(config):
    """Write every measurement to the built site.

    Same move as links.py -> link-report.json, and for the same reason: a
    number you can fetch beats a number you have to trust. The whole table is
    written, passes included, so a pair sitting just above the floor is visible
    before it slips under.
    """
    if not _report:
        return
    path = os.path.join(config["site_dir"], "contrast-report.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(_report, fh, indent=2)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary or _report.get("skipped"):
        return

    rows = _report["failures"] + _report["warnings"]
    lines = ["### Contrast", ""]
    if rows:
        lines += [
            str(len(rows)) + " pair(s) below the floor. The active palette is "
            "**" + _report["active_palette"] + "**; a parked palette warns "
            "rather than failing, because nobody can see it yet.",
            "",
            "| Palette | Mode | Pair | Ratio | Needs | |",
            "|---|---|---|---|---|---|",
        ]
        for record in rows:
            lines.append(
                "| `" + record["palette"] + "` | " + record["mode"] + " | `"
                + record["pair"] + "` | " + str(record["ratio"]) + ":1 | "
                + str(record["min"]) + " | "
                + ("**FAIL**" if record["active"] or _report["strict"]
                   else "warn") + " |"
            )
    else:
        lines.append(
            "All " + str(_report["checked"]) + " pairs clear their floor, in "
            "every palette, in both modes."
        )
    lines += [
        "",
        "Full table, passes included: `/contrast-report.json` on the built "
        "site.",
    ]
    with open(summary, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
