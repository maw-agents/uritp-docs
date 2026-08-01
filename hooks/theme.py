"""
The 4-vector theme resolver.

Reads ``theme/`` and injects the composed result into every page's ``<head>``
as ``--u-*`` custom properties. ``docs/stylesheets/uritp.css`` consumes them
and holds no literal colour, font, size or radius of its own.

    theme/active.txt      one slug: the site default
    theme/themes.tsv      the JOIN -- one row per theme, four pointers
    theme/<vector>.json   the VALUES those pointers name
    a page's `theme:`     that one page (or folder) wears a different theme

WHY JSON FOR THE VECTORS AND TSV FOR THE JOIN (changed 2026-08-01, Michael:
"any clearer way to edit the values than the TSV which is dense prose when in
edit mode? at least with JSON i get the variable names in line")

The two formats answer two different questions, and that is the whole rule:

    A TABLE you read ACROSS stays a grid.   themes.tsv, contrast.tsv
    A RECORD you edit one at a time is JSON. the four vectors

``themes.tsv`` is six short rows compared column by column -- which theme uses
which palette -- and that is exactly what a grid is for. A palette is fifteen
tokens times two modes, edited one palette at a time and almost never compared
cell-to-cell against another. As a TSV row that is thirty anonymous values in
tab-separated sequence: correct, diffable, and unreadable in an editor, where
the header is scrolled off the top and the only way to know which value you are
changing is to count columns. JSON puts the name on the line.

This was not the original call. The grids replaced YAML earlier the same day
for a good reason (a table belongs in a table) and the mistake was applying it
to all four vectors instead of asking which of them are actually tables.

THE FALLBACK CHAIN -- one rule, at both levels

    An ABSENT value inherits. A PRESENT value wins.

  * ``themes.tsv``: an empty vector cell takes its value from the ``_default``
    row. So a theme that only changes colour names one thing.
  * a vector file: a token that is not listed comes from the entry named in
    ``inherits``, walking that chain, then from ``_base`` in the same file.

``_base`` is the safety net and must be COMPLETE. ``_default`` is the join's
equivalent. Neither may be named by ``active.txt``.

[!] ABSENT means INHERIT, never "nothing". A token that wants to be off says so
with a real value: ``"shadow": "none"``.

THE WEBFONT SEAM IS CLOSED -- this hook writes the config
The typography vector says which family the CSS ASKS FOR; it also now sets
``theme.font``, which is what Material DOWNLOADS. They used to be two files
kept in agreement by hand, and a mismatch silently rendered the next entry in
the fallback stack with no error anywhere.

=======================================================================
THE SKIN WATERFALL -- a page or a folder can wear its own theme
=======================================================================

    ---
    title: Electrics
    theme: utility
    ---

On an ``index.md`` that skins the whole subtree.

[!][!] THERE ARE TWO WATERFALLS AND THEY RUN IN OPPOSITE DIRECTIONS. Do not
unify them, and do not "make them consistent":

    THE LOCK waterfall (hooks/visibility.py)   PARENT WINS.
        A lock you can undo by accident, in a file nobody is looking at,
        is not a lock.

    THE SKIN waterfall (this file)             CHILD WINS.
        A skin is a preference. Nothing is at risk, so the more specific
        statement is the one to honour.

Precedence follows CONSEQUENCE, not symmetry. The day somebody merges these
into one "inheritance" concept is the day a locked page quietly publishes.

``theme: default`` means "whatever active.txt says", so a page can stand
outside a themed folder without hard-coding a name that will rot.

A PAGE theme that does not resolve FALLS BACK AND REPORTS; a bad ``active.txt``
FAILS THE BUILD. Opposite outcomes, one rule: a failure should be local and
visible. The site theme has no single page to fail on, so it must stop
everything; a page theme has exactly one, so it fails there and says so.

[!] A PAGE THEME CANNOT CHANGE WHICH WEBFONT IS DOWNLOADED -- Material's font
loader is global config. A theme whose typography names a family the site does
not load is REPORTED, because the symptom (one page silently in the fallback
face) is invisible to every other check here.

REQUIRED is owned HERE, not in the data: the stylesheet is what consumes these
names, so the code that pairs with the stylesheet is what knows which ones may
not be missing.

Wired in mkdocs.yml under ``hooks:``. Documented in theme/README.md.
``hooks/contrast.py`` imports this module to reuse ``_read``, ``_index`` and
``_compose``, so the numbers it measures are the numbers a page really gets.
"""

import csv
import json
import os
import posixpath
import re

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "theme")

ACTIVE = os.path.join(DIR, "active.txt")

VECTORS = ("color", "typography", "forms", "spacing")
JOIN = "themes.tsv"
GRID = {
    "color": "colors.json",
    "typography": "typography.json",
    "forms": "forms.json",
    "spacing": "spacing.json",
}

BASE = "_base"          # the complete fallback entry inside every vector file
DEFAULT = "_default"    # the same idea, one level up, inside themes.tsv

# Keys that describe an entry rather than being a token it carries.
META = {"slug", "mode", "inherits", "name", "note"}
MAX_HOPS = 8

# What a page writes to opt OUT of a themed folder and back to the site theme.
# A word rather than the active theme's name, which would rot on the next swap.
SITE = "default"

# Required, but NOT written into the CSS: these configure Material's webfont
# loader instead of describing a style.
NOT_CSS = {"webfont-text", "webfont-code"}
OFF = "none"            # `webfont-text: none` means download nothing

# Every token docs/stylesheets/uritp.css reads, plus the two webfont names.
# Adding a var() to the stylesheet means adding its name here AND to `_base`
# in that vector's file, in the SAME PR.
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

_FRONTMATTER = re.compile(rb"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)

_styles = {}        # theme slug   -> the <style> block for it
_active = ""        # the site theme, from active.txt
_page_theme = {}    # src_uri      -> the theme that page ASKED for
_folder_theme = {}  # folder path  -> (slug, the index.md that said so)
_unresolved = {}    # src_uri      -> a name that did not resolve
_worn = {}          # src_uri      -> the theme actually applied
_trace = []


def _fail(where, message):
    raise ValueError("theme/" + where + ": " + message)


def _read(filename, key="slug"):
    """A TSV as a list of dicts. Used by the JOIN and by contrast.tsv -- the two
    files that really are tables read across.

    Values are stripped: a trailing space in a spreadsheet cell is invisible and
    would otherwise become part of a value. ``key`` is the column that makes a
    row real, which also skips the blank lines a spreadsheet leaves at the end.
    It is a parameter rather than a hard-coded "slug" because contrast.tsv is
    keyed by `fg` -- assuming every table here shares one key column is what
    broke the contrast gate's first build.
    """
    path = os.path.join(DIR, filename)
    if not os.path.exists(path):
        _fail(filename, "file is missing")
    rows = []
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        if reader.fieldnames and key not in [
            (name or "").strip() for name in reader.fieldnames
        ]:
            _fail(filename, "has no `" + key + "` column")
        for raw in reader:
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


def _load(filename):
    """A vector file. `_README` is prose for whoever opens it and is dropped.

    A JSON syntax error is reported with its line and column, which is the one
    real cost of this format over a grid -- and the reason the error message
    says where to look rather than just what went wrong.
    """
    path = os.path.join(DIR, filename)
    if not os.path.exists(path):
        _fail(filename, "file is missing")
    with open(path, encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except ValueError as problem:
            _fail(filename, "is not valid JSON -- " + str(problem))
    if not isinstance(data, dict):
        _fail(filename, "must be an object of named entries")
    return {
        name: entry
        for name, entry in data.items()
        if name != "_README" and isinstance(entry, dict)
    }


def _index(vector, filename):
    """Name -> the values under it. Colour is keyed by (slug, mode) because it
    is the only vector with a dark and a light form; `inherits` is copied onto
    each mode so the chain walker does not need to know the difference."""
    data = _load(filename)
    table = {}
    for slug, entry in data.items():
        parent = str(entry.get("inherits") or "").strip()
        if vector != "color":
            row = {k: str(v) for k, v in entry.items() if k not in METAMETA}
            row["inherits"] = parent
            table[slug] = row
            continue
        for mode in MODES:
            block = entry.get(mode)
            if block is None:
                # Not a warning: a palette with one mode half-works, which is
                # the failure this split exists to prevent.
                _fail(
                    filename,
                    "`" + slug + "` has no `" + mode + "` block. Every palette "
                    "needs both, because the site has a scheme toggle.",
                )
            if not isinstance(block, dict):
                _fail(filename, "`" + slug + "`." + mode + " must be an object")
            row = {k: str(v) for k, v in block.items() if k not in METAMETA}
            row["inherits"] = parent
            table[(slug, mode)] = row
    if not table:
        _fail(filename, "has no entries")
    return table


# Keys that never carry a token value, at either nesting level.
METAMETA = {"note", "inherits", "name", "dark", "light"}


def _slugs(table):
    """Public names, so an error tells you what you CAN use."""
    seen = set()
    for key in table:
        slug = key[0] if isinstance(key, tuple) else key
        if not slug.startswith("_"):
            seen.add(slug)
    return ", ".join(sorted(seen)) or "(none)"


def _compose(vector, table, slug, mode=None):
    """Walk the inherits chain, then fall through to _base. First value wins,
    so the entry you named always beats what it inherits."""
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
            _fail(filename, "no entry " + detail + ". Defined: " + _slugs(table))

        for name, value in row.items():
            if name in META or not value:
                continue
            tokens.setdefault(name, value)

        current = row.get("inherits", "")

    base = table.get((BASE, mode) if vector == "color" else BASE)
    if base is None:
        _fail(filename, "no `" + BASE + "` entry; it is the fallback and is required")
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
    _trace.append("  " + vector + ((":" + mode) if mode else "") + " = " + label)

    missing = [k for k in REQUIRED[vector] if k not in tokens]
    if missing:
        _fail(
            filename,
            "`" + slug + "`" + ((" " + mode) if mode else "")
            + " resolves without token(s): " + ", ".join(missing)
            + ". Add them, or fill them in `" + BASE + "`.",
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


def _vectors_for(slug, joins, fallback):
    chosen = {}
    row = joins[slug]
    for vector in VECTORS:
        name = row.get(vector) or fallback.get(vector)
        if not name:
            _fail(
                JOIN,
                "`" + slug + "` names no " + vector + " and `" + DEFAULT
                + "` does not fill it either",
            )
        chosen[vector] = name
    return chosen


def _build(chosen, tables):
    """One theme -> one <style> block, and the typography it wants."""
    css = []
    for mode, selector in MODES.items():
        tokens = _compose("color", tables["color"], chosen["color"], mode)
        css.append(_block(selector, _declare(tokens, "color")))

    root = ""
    typography = None
    for vector in ("typography", "forms", "spacing"):
        tokens = _compose(vector, tables[vector], chosen[vector])
        if vector == "typography":
            typography = tokens
        root += _declare(tokens, vector)
    css.insert(0, _block(":root", root))

    return '<style id="u-theme">' + "".join(css) + "</style>", typography


def _apply_webfont(config, tokens):
    """Write the family names Material should DOWNLOAD, from the same entry
    that decided which families the CSS asks for. One file decides, so the two
    cannot drift apart.

    Material takes `font: false` to mean "load nothing", and it is all or
    nothing -- there is no per-face switch. So `none` in one and a real family
    in the other is a contradiction, refused rather than silently resolved."""
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


def _read_active():
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


def _frontmatter_theme(abs_path):
    """Just the `theme:` line out of a page's frontmatter.

    [!] This reads the file directly rather than using `page.meta`, because the
    FOLDER waterfall has to know about every index.md before any page is
    rendered, and MkDocs only parses a page's meta when it reaches that page.
    hooks/visibility.py reads frontmatter the same way for the same reason.
    """
    try:
        with open(abs_path, "rb") as fh:
            head = fh.read(4096)
    except OSError:
        return ""
    match = _FRONTMATTER.match(head)
    if not match:
        return ""
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return ""
    if not isinstance(meta, dict):
        return ""
    return str(meta.get("theme") or "").strip()


def _ancestors(src_uri):
    """Folder paths above this page, nearest first."""
    parent = posixpath.dirname(src_uri)
    parts = parent.split("/") if parent else []
    out = []
    while parts:
        out.append("/".join(parts))
        parts = parts[:-1]
    out.append("")
    return out


def _wanted(src_uri):
    """What this page ASKED to wear, and who asked. CHILD WINS -- see the
    module docstring on the two waterfalls."""
    own = _page_theme.get(src_uri)
    if own:
        return own, src_uri
    for folder in _ancestors(src_uri):
        if folder in _folder_theme and _folder_theme[folder][1] != src_uri:
            return _folder_theme[folder]
    return "", ""


def on_config(config):
    global _active
    del _trace[:]
    _styles.clear()

    _active = _read_active()
    joins = {row["slug"]: row for row in _read(JOIN)}

    if _active.startswith("_"):
        _fail(
            "active.txt",
            "`" + _active + "` is a fallback row, not a theme. Available: "
            + _slugs(joins),
        )
    if _active not in joins:
        _fail(
            "active.txt",
            "`" + _active + "` is not a row in " + JOIN + ". Available: "
            + _slugs(joins),
        )
    if DEFAULT not in joins:
        _fail(JOIN, "no `" + DEFAULT + "` row; it is what fills empty cells")

    fallback = joins[DEFAULT]
    tables = {v: _index(v, GRID[v]) for v in VECTORS}

    # The ACTIVE theme first, and strictly: it is the one with no page to fail
    # on, so anything wrong with it stops the build.
    chosen = _vectors_for(_active, joins, fallback)
    style, typography = _build(chosen, tables)
    _styles[_active] = style
    webfont = _apply_webfont(config, typography)
    print("theme: " + _active + " = " + " x ".join(chosen[v] for v in VECTORS))
    for line in _trace:
        print(line)
    print("  webfont = " + webfont)

    # Then every other theme, so a page can name one. A parked theme that will
    # not compose is REPORTED and skipped rather than taking the site down --
    # the same trade the contrast gate makes.
    wanted_font = typography["webfont-text"]
    for slug in sorted(joins):
        if slug == _active or slug.startswith("_"):
            continue
        try:
            other = _vectors_for(slug, joins, fallback)
            _styles[slug], parked = _build(other, tables)
        except ValueError as problem:
            print("::warning::theme: `" + slug + "` will not compose, so no "
                  "page can wear it -- " + str(problem))
            continue
        # A page theme cannot change which webfont downloads: Material's font
        # loader is global. A mismatch means one page silently renders in the
        # fallback face, which no other check here can see.
        if parked["webfont-text"] != wanted_font:
            print(
                "::warning::theme: `" + slug + "` wants the webfont `"
                + parked["webfont-text"] + "` but the site loads `"
                + wanted_font + "`. A page wearing `" + slug + "` gets its "
                "sizes and colours but NOT its typeface."
            )

    print("theme: " + str(len(_styles)) + " theme(s) composed and available "
          "to pages")
    return config


def on_files(files, config):
    """Note which pages, and which folders, asked for a theme. Runs before any
    page is rendered, which is why the frontmatter is read directly."""
    _page_theme.clear()
    _folder_theme.clear()
    _unresolved.clear()
    _worn.clear()

    for f in files:
        if not f.is_documentation_page():
            continue
        slug = _frontmatter_theme(f.abs_src_path)
        if not slug:
            continue
        _page_theme[f.src_uri] = slug
        if posixpath.basename(f.src_uri) == "index.md" and slug != SITE:
            _folder_theme[posixpath.dirname(f.src_uri)] = (slug, f.src_uri)
    return files


def on_post_page(output, page, config):
    """Last thing in <head>, so these declarations win any tie with Material's
    own scheme variables without needing a specificity trick."""
    src = page.file.src_uri
    slug, source = _wanted(src)

    if slug and slug != SITE and slug not in _styles:
        _unresolved[src] = (slug, source)
        slug = ""
    if not slug or slug == SITE:
        slug = _active

    if slug != _active:
        _worn[src] = slug
    return output.replace("</head>", _styles[slug] + "</head>", 1)


def on_post_build(config):
    """Report the skin waterfall. A page wearing something other than the site
    theme is a deliberate choice and should be visible; a page that asked for
    something that does not exist is a typo and must be."""
    if _worn:
        print("theme: " + str(len(_worn)) + " page(s) wearing another theme")
        for src, slug in sorted(_worn.items()):
            print("  " + src + " -> " + slug)

    if not _unresolved:
        return

    print("theme: " + str(len(_unresolved)) + " page(s) asked for a theme that "
          "does not exist, and are wearing `" + _active + "` instead:")
    for src, (slug, source) in sorted(_unresolved.items()):
        where = src if source == src else src + " (via " + source + ")"
        print("::warning::theme: " + where + " asked for `" + slug + "`")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return
    lines = [
        "### ⚠️ Page themes that did not resolve",
        "",
        "These pages named a theme that is not a row in `theme/themes.tsv`, "
        "or one that failed to compose. They rendered in the site theme "
        "**`" + _active + "`** instead -- nothing is broken, but nobody got "
        "the skin they asked for.",
        "",
        "| Page | Asked for | Named in |",
        "|---|---|---|",
    ]
    for src, (slug, source) in sorted(_unresolved.items()):
        lines.append("| `" + src + "` | `" + slug + "` | `" + source + "` |")
    with open(summary, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
