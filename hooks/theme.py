"""
The 4-vector theme resolver.

Reads the grids in ``theme/`` and injects the composed result into every page's
``<head>`` as ``--u-*`` custom properties. ``docs/stylesheets/uritp.css``
consumes them and holds no literal colour, font, size or radius of its own.

    theme/active.txt   ->  one slug: the site default
    theme/themes.tsv   ->  each slug's row: colour x typography x forms x spacing
    theme/*.tsv        ->  the four grids those names point into
    a page's `theme:`  ->  that ONE page (or folder) wears a different one

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

=======================================================================
THE SKIN WATERFALL -- a page or a folder can wear its own theme
=======================================================================

    ---
    title: Electrics
    theme: utility          # this page, or this whole folder from its index.md
    ---

A gated ``index.md`` locks its subtree; a THEMED ``index.md`` skins its
subtree the same way. Every theme in ``themes.tsv`` is composed at config
time, so picking one per page is a dictionary lookup, not extra work.

⚠️⚠️ THERE ARE NOW TWO WATERFALLS AND THEY RUN IN OPPOSITE DIRECTIONS. Do not
unify them, and do not "make them consistent":

    THE LOCK waterfall (hooks/visibility.py)   PARENT WINS.
        A lock you can undo by accident, in a file nobody is looking at,
        is not a lock.

    THE SKIN waterfall (this file)             CHILD WINS.
        A skin is a preference. Nothing is at risk, so the more specific
        statement is the one to honour.

The asymmetry is the point: precedence follows CONSEQUENCE, not symmetry. The
day somebody merges these into one "inheritance" concept is the day a locked
page quietly publishes.

``theme: default`` is the escape -- it means "whatever active.txt says", so a
page can stand outside a themed folder without hard-coding the site theme's
name (which would rot the moment ``active.txt`` changed).

A NAME THAT DOES NOT RESOLVE FALLS BACK, IT DOES NOT FAIL THE BUILD, and that
is the opposite of the rule for ``active.txt`` -- for a reason. A bad global
theme has no page to fail on: it is the whole site or nothing, so it must
stop the build. A bad PAGE theme has exactly one page to fail on, so it does
what every other local failure here does: renders anyway, wearing the site
theme, and reports itself by name.

⚠️ ONE THING A PAGE THEME CANNOT CHANGE: WHICH WEBFONT IS DOWNLOADED.
Material's font loader is global config, not per page. A parked theme whose
typography row names a family the active theme does not load is REPORTED at
build time, because the symptom -- one page silently rendering in the fallback
font -- is invisible to every other check we have.

WHY A BAD ``active.txt`` NAME STILL FAILS THE BUILD
The house rule is that failures should be local and visible, not global and
silent. See the paragraph above: the active theme is the one with nowhere
local to fail. Parked themes that will not compose are reported and skipped,
the same trade the contrast gate makes -- the active one must be perfect,
parked ones only have to tell you.

REQUIRED is owned HERE, not in the grids, and deliberately: the stylesheet is
what consumes these names, so the code that pairs with the stylesheet is what
knows which ones may not be missing.

Wired in mkdocs.yml under ``hooks:``. Documented in theme/README.md.
``hooks/contrast.py`` imports this module to reuse ``_read``, ``_index`` and
``_compose``, so the numbers it measures are the numbers a page really gets.
"""

import csv
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
    "color": "colors.tsv",
    "typography": "typography.tsv",
    "forms": "forms.tsv",
    "spacing": "spacing.tsv",
}

BASE = "_base"          # the complete fallback row inside every vector grid
DEFAULT = "_default"    # the same idea, one level up, inside themes.tsv
META = {"slug", "mode", "inherits", "name", "note"}
MAX_HOPS = 8

# What a page writes to opt OUT of a themed folder and back to the site theme.
# A word rather than the active theme's name, which would rot on the next swap.
SITE = "default"

# Required, but NOT written into the CSS: these configure Material's webfont
# loader instead of describing a style. See THE WEBFONT SEAM in the README.
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
    """A grid as a list of dicts. Values are stripped -- a trailing space in a
    spreadsheet cell is invisible and would otherwise become part of a colour.
    A short row (fewer cells than headers) reads as empty, not as None.

    ``key`` is the column that must be present for a row to count, which also
    skips the blank lines a spreadsheet leaves at the end of a file. It is a
    parameter rather than a hard-coded "slug" because contrast.tsv is a grid
    too and is keyed by `fg` -- assuming every table in this folder has the
    same key column is what broke the contrast gate's first build.
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


def _index(vector, filename):
    """Colour rows are keyed by (slug, mode); everything else by slug."""
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
            table[(row["slug"], mode)] = row
        else:
            table[row["slug"]] = row
    return table


def _slugs(table):
    """Public row names, so an error tells you what you CAN use."""
    seen = set()
    for key in table:
        slug = key[0] if isinstance(key, tuple) else key
        if not slug.startswith("_"):
            seen.add(slug)
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


def _build(slug, chosen, tables):
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
    """Write the family names Material should DOWNLOAD, from the same grid row
    that decided which families the CSS asks for. This is the seam-closing
    move: one file decides, so the two cannot drift apart.

    Material takes `font: false` to mean "load nothing", and it is all or
    nothing -- there is no per-face switch. So `none` in one column and a real
    family in the other is a contradiction, and it is refused rather than
    silently resolved in whichever direction happens to be first."""
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


# Kept for hooks/contrast.py, which asks the same question.
def _active_slug():
    return _read_active()


_active_alias = _active_slug


def _frontmatter_theme(abs_path):
    """Just the `theme:` line out of a page's frontmatter.

    ⚠️ This reads the file directly rather than using `page.meta`, because the
    FOLDER waterfall has to know about every index.md before any page is
    rendered, and MkDocs only parses a page's meta when it reaches that page.
    hooks/visibility.py reads frontmatter the same way for the same reason;
    they are two small parses of a generic format, not two claimants on one
    truth, and sharing them would mean this hook depending on the gate that
    runs after it.
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
            slug, source = _folder_theme[folder]
            return slug, source
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
    style, typography = _build(_active, chosen, tables)
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
            _styles[slug], parked = _build(slug, other, tables)
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
        lines.append(
            "| `" + src + "` | `" + slug + "` | `" + source + "` |"
        )
    with open(summary, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
