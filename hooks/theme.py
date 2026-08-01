"""
The 4-vector theme resolver.

Reads ``theme.yml`` at the repo root, composes the four vectors named by the
active theme, and injects the result into every page's ``<head>`` as ``--u-*``
custom properties. ``docs/stylesheets/uritp.css`` consumes them and holds no
literal colour, font, size or radius of its own.

    theme.yml  active: uritp-prp
               -> colour uritp-prp x typography plex-docs
                  x forms hairline x spacing standard

SWAPPING THE WHOLE SITE IS ONE LINE. That is the entire point of the file and
the reason this hook exists rather than a second stylesheet: a theme kept as
"another CSS file" means every swap is a diff nobody can read, and the two
files drift the moment one gains a rule the other never got.

WHY NOT A GENERATED .css FILE
An inline ``<style>`` costs about 1.5KB per page and buys two things a
separate file cannot: no extra request, and no window in which the page is
painted before its own colours arrive. The site is read on phones on venue
wifi. A flash of the wrong theme is worse than 1.5KB.

WHY A BAD THEME NAME FAILS THE BUILD
The house rule is that failures should be local and visible, not global and
silent -- a dead link marks one link, a missing gate key locks one page. A
theme has no page to fail on: it is the whole site or nothing. And a theme
that quietly fell back to something else is precisely the invisible failure
that rule exists to prevent. So this raises, and the PR build check catches it
on the branch before it can reach ``main``.

REQUIRED is owned HERE, not in theme.yml, and deliberately: the stylesheet is
what consumes these names, so the code that pairs with the stylesheet is what
knows which ones may not be missing. A palette that forgets a token fails by
name instead of rendering one element invisible.

Wired in mkdocs.yml under ``hooks:``. Documented in AUTHORING-LOOK.md.
"""

import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "theme.yml")

VECTORS = ("color", "typography", "forms", "spacing")

# Every token docs/stylesheets/uritp.css reads. Adding a var() there means
# adding its name here and to every row of that vector, in the SAME PR.
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

MODES = {
    "dark": "[data-md-color-scheme=slate]",
    "light": "[data-md-color-scheme=default]",
}

_style = ""


def _fail(message):
    raise ValueError("theme.yml: " + message)


def _row(data, vector, name):
    table = data.get(vector)
    if not isinstance(table, dict):
        _fail("no `" + vector + ":` section")
    row = table.get(name)
    if not isinstance(row, dict):
        defined = ", ".join(sorted(table)) if table else "(none)"
        _fail(
            vector + " `" + str(name) + "` does not exist. Defined: " + defined
        )
    return row


def _check(tokens, vector, label):
    missing = [k for k in REQUIRED[vector] if k not in tokens]
    if missing:
        _fail(label + " is missing token(s): " + ", ".join(missing))


def _declare(tokens, vector):
    """Only the tokens the stylesheet actually reads. A `note:` is prose for a
    human and has no business in the CSS."""
    return "".join(
        "--u-" + key + ":" + str(tokens[key]) + ";" for key in REQUIRED[vector]
    )


def _block(selector, body):
    return selector + "{" + body + "}"


def on_config(config):
    global _style

    with open(SOURCE, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    active = data.get("active")
    themes = data.get("themes")
    if not isinstance(themes, dict):
        _fail("no `themes:` join table")
    if active not in themes:
        _fail(
            "active theme `" + str(active) + "` is not in the join table. "
            "Available: " + ", ".join(sorted(themes))
        )

    combo = themes[active] or {}
    chosen = {}
    for vector in VECTORS:
        name = combo.get(vector)
        if not name:
            _fail("theme `" + active + "` names no " + vector + " vector")
        chosen[vector] = (name, _row(data, vector, name))

    # Colour is the only vector with modes, because the site has a toggle.
    palette_name, palette = chosen["color"]
    css = []
    for mode, selector in MODES.items():
        tokens = palette.get(mode)
        if not isinstance(tokens, dict):
            _fail("colour `" + palette_name + "` has no `" + mode + ":` mode")
        _check(tokens, "color", "colour `" + palette_name + "` " + mode)
        css.append(_block(selector, _declare(tokens, "color")))

    root = ""
    for vector in ("typography", "forms", "spacing"):
        name, tokens = chosen[vector]
        _check(tokens, vector, vector + " `" + name + "`")
        root += _declare(tokens, vector)
    css.insert(0, _block(":root", root))

    _style = '<style id="u-theme">' + "".join(css) + "</style>"

    print("theme: " + active + " = " + " x ".join(chosen[v][0] for v in VECTORS))
    return config


def on_post_page(output, page, config):
    """Last thing in <head>, so these declarations win any tie with Material's
    own scheme variables without needing a specificity trick."""
    return output.replace("</head>", _style + "</head>", 1)
