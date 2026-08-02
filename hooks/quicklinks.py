"""
The Quick Links section in the sidebar.

Reads `quick-links.yml` at the repo root -- `Label: target` -- and inserts a
section of LINKS immediately below Home. A target is either a slug in this site
or a URL somewhere else.

    quick-links.yml        the list. Data, editable by anyone.
    this file              resolution, placement, and what to say on a miss.

=======================================================================
THE RULE: A SCHEME MEANS ELSEWHERE. ANYTHING ELSE IS A SLUG.
=======================================================================

    Smith Theatre: smith-theatre                  -> a page in this site
    UR Theatre Program: https://www.rochester.edu/college/ttp/
                                                  -> straight out to the web
    Production office: mailto:pm@example.edu      -> also fine

Same shape-decides principle the gate keys use: the VALUE tells you what it is,
so there is no second key to learn and no way to say it wrong. A slug is
resolved against the registry and reported if it misses; a URL is passed
through verbatim and never validated, because this build cannot know whether
somebody else's site is up.

⚠️ ONLY `http`, `https` and `mailto` ARE ACCEPTED. Anything else with a colon
is refused by name rather than emitted into an href -- `javascript:` in a nav
link is the obvious reason, and a scheme nobody recognised is far more likely
to be a typo than an intention.

=======================================================================
🔴 WHY THIS IS A HOOK AND NOT FOUR LINES OF .nav.yml
=======================================================================

awesome-nav CAN write an external link in `.nav.yml`, so for a purely external
list this hook would be unnecessary. It exists for the INTERNAL half, and the
reason is specific:

    nav:
      - Quick links:
        - venues/spac/smith-theatre.md      # <- DO NOT

awesome-nav's own documentation: *"Glob patterns will never match files or
directories that are already part of the navigation."* Naming Smith Theatre
there REMOVES it from Venues -- the page MOVES rather than being shortcut to. A
page appears in the nav exactly once.

Its stated workaround is "create a link instead of the page entry", meaning a
hardcoded relative path -- precisely the fragility hooks/links.py exists to
abolish, which froze this site twice inside forty minutes on 2026-08-01.

So internal shortcuts have to be links built from slugs, resolved at build
time. Externals ride along in the same list because splitting them across two
files would mean remembering which list a shortcut lives in.

=======================================================================
⚠️ WHY AN INTERNAL HREF IS ROOT-RELATIVE AND NOT PAGE-RELATIVE
=======================================================================

A nav Link holds ONE url string rendered on EVERY page, so a page-relative href
(`../venues/smith-theatre/`) cannot be right everywhere. It is only correct if
the theme passes it through MkDocs' `| url` filter, which rewrites it per page.

Whether mkdocs-material's partials/nav-item.html applies that filter to a Link
COULD NOT BE READ: the template fetched back with its tags stripped, which is
the documented plaintext-flattening hazard in the GitHub read path. Rather than
assume -- three separate bugs on 2026-08-01 came from a plausible assumption
about Material's internals -- the URL is built in the form that is correct
under BOTH answers:

    /uritp-docs/venues/spac/smith-theatre/

mkdocs.utils.templates.normalize_url returns any path beginning with `/`
UNCHANGED, so `| url` is a no-op on it. With no filter at all, a root-absolute
href is still correct from every page. One form, no dependency on an unverified
detail. An external URL has a scheme, and normalize_url leaves those alone too.

The prefix comes from `site_url`'s path at build time, never hardcoded, so
moving the site to another base path moves these with it.

=======================================================================
ONE REGISTRY, ONE REPORT
=======================================================================

This hook does NOT parse frontmatter. It reads `config["_uritp_slugs"]`, which
hooks/links.py publishes from the same table that resolves every `@slug` in
every page body. Two parsers would drift, and only one would be reported on.

Misses are filed through `links.add_issue()`, so a broken quick link lands in
`link-report.json` and the same run-summary table as a broken body link. That
is the answer to "which slugs need updating if I rename a page": ONE place, not
one per feature.

⚠️ ORDER: registered AFTER links.py in mkdocs.yml. The registry is written in
its `on_files`, and issues are collected until its `on_post_build`; `on_nav`
sits between the two. Move this earlier and the section silently empties --
which is why the empty case is reported rather than shrugged at.

=======================================================================
WHAT IT DOES WHEN A SLUG IS WRONG
=======================================================================

Drops that one link, names it, suggests the closest real slug, and builds.

Never fails the build, never renders a dead nav row. A nav entry that goes
nowhere is worse than a missing one: the sidebar is chrome a reader trusts
without thinking, and one 404 from it costs more than the shortcut was worth.
`--strict` was removed from deploy.yml the same day for the same reason.

A `hidden` page has no slug in the registry at all -- it is never built -- so a
quick link to one reads as a miss. An `unlisted` page DOES resolve, and
pointing a quick link at one is arguably the whole feature: out of the main
sidebar, reachable by shortcut.

Documented for authors in quick-links.yml itself, which is where someone
editing the list is already looking.
"""

import difflib
import os
import posixpath
import sys
from urllib.parse import urlsplit

import yaml
from mkdocs.structure.nav import Link, Section

# MkDocs loads a hook as a standalone module, not as part of a package, so a
# relative import does not work. Same bootstrap hooks/contrast.py uses.
_HOOKS = os.path.dirname(os.path.abspath(__file__))
if _HOOKS not in sys.path:
    sys.path.insert(0, _HOOKS)

import links as _links      # noqa: E402  (path set above, deliberately)

SOURCE = "quick-links.yml"
DEFAULT_TITLE = "Quick Links"

# The only schemes allowed straight into an href. `javascript:` is the obvious
# reason for an allow-list rather than a block-list, and an unrecognised scheme
# is far more likely to be a typo than an intention.
SCHEMES = ("http", "https", "mailto")

# The section is inserted immediately AFTER the nav item with this title.
# Matched by title rather than by index so that reordering docs/.nav.yml cannot
# silently move the shortcuts somewhere surprising. No match -> the top.
AFTER_ITEM = "Home"

_report = []      # (label, target, href_or_None, kind, detail). Safe to print.


def _base(config):
    """The site's root path, with both slashes, from site_url. `/` if unset.

    Never hardcoded: move the site to another base and every quick link moves
    with it, because this is read at build time from the same value MkDocs uses
    for everything else.
    """
    path = urlsplit(config.get("site_url") or "").path or "/"
    if not path.startswith("/"):
        path = "/" + path
    if not path.endswith("/"):
        path += "/"
    return path


def _scheme(value):
    """The URL scheme, lowercased, or None if this is not a URL.

    Deliberately not a regex on `://`: `mailto:` has no slashes. urlsplit gets
    it right and also refuses to call a Windows-ish `C:foo` a scheme.
    """
    try:
        found = urlsplit(value).scheme.lower()
    except ValueError:
        return None
    return found or None


def _load(config):
    """Read quick-links.yml from the repo root, beside mkdocs.yml.

    Returns (title, [(label, target)], problem_or_None). A missing file is NOT
    a problem -- the feature is optional and a repo without the file simply has
    no shortcuts.
    """
    root = os.path.dirname(os.path.abspath(config["config_file_path"]))
    path = os.path.join(root, SOURCE)
    if not os.path.exists(path):
        return DEFAULT_TITLE, [], None

    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except (OSError, yaml.YAMLError) as error:
        # A YAML error here is usually an unquoted `@slug`: `@` is a reserved
        # first character in YAML. Say so, because the parser's own message
        # does not mention this file or that rule.
        return DEFAULT_TITLE, [], (
            SOURCE + " could not be read (" + str(error).split("\n")[0] + "). "
            "If a value starts with @, it must be quoted: \"@smith-theatre\". "
            "No quick links were added this build."
        )

    if not isinstance(data, dict):
        return DEFAULT_TITLE, [], SOURCE + " must be a mapping with a `links:` key"

    title = str(data.get("title") or DEFAULT_TITLE).strip()
    raw = data.get("links")

    pairs = []
    # A mapping is the normal form and keeps its order in PyYAML. A list of
    # one-key mappings is accepted too, because someone who wants the order to
    # be visibly explicit will reach for it and being wrong about that should
    # not be an error.
    if isinstance(raw, dict):
        pairs = list(raw.items())
    elif isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, dict):
                pairs.extend(entry.items())
    elif raw is not None:
        return title, [], SOURCE + ": `links:` must be a mapping of Label: target"

    clean = []
    for label, target in pairs:
        label = str(label).strip()
        target = str(target or "").strip()
        # The `@` is optional on a slug. Michael thinks in @slug and YAML hates
        # a bare one, so accept both spellings rather than making the quoting
        # rule load-bearing. A URL never starts with @, so this is safe.
        if target.startswith("@"):
            target = target.lstrip("@").strip()
        if label and target:
            clean.append((label, target))
    return title, clean, None


def _resolve(pairs, slugs, base):
    """(links, misses). `slugs` is links.py's registry: slug -> (url, title)."""
    known = _links.known_ids()
    found = []
    misses = []

    for label, target in pairs:
        scheme = _scheme(target)

        # ── A SCHEME MEANS ELSEWHERE ─────────────────────────────────────
        if scheme:
            if scheme not in SCHEMES:
                detail = (
                    "'" + scheme + ":' is not a link scheme this site will "
                    "emit. Use " + ", ".join(SCHEMES)
                )
                misses.append((label, target, detail))
                _report.append((label, target, None, "external", detail))
                continue
            found.append((label, target))
            _report.append((label, target, target, "external", None))
            continue

        # ── OTHERWISE IT IS A SLUG IN THIS SITE ──────────────────────────
        entry = slugs.get(target)
        if entry:
            url, _title = entry
            href = posixpath.join(base, url.lstrip("/"))
            found.append((label, href))
            _report.append((label, target, href, "page", None))
            continue

        near = difflib.get_close_matches(target, known, n=2, cutoff=0.6)
        detail = "no page carries id '" + target + "'"
        if near:
            detail += " -- did you mean " + " or ".join(near) + "?"
        elif known:
            detail += ". This link was dropped from the sidebar"
        # The commonest way to get here is pasting a URL without its scheme,
        # which reads as a slug and misses. Say so rather than only suggesting
        # page names it obviously is not.
        if "." in target or "/" in target:
            detail += (
                ". If this was meant to be an external link, it needs its "
                "scheme: https://" + target.lstrip("/")
            )
        misses.append((label, target, detail))
        _report.append((label, target, None, "page", detail))

    return found, misses


def on_nav(nav, config, files):
    del _report[:]

    title, pairs, problem = _load(config)
    if problem:
        print("::warning::quick links: " + problem)
        _links.add_issue("quick-link", SOURCE, "-", problem)
        return nav
    if not pairs:
        return nav

    slugs = config.get(_links.SLUGS) or {}
    if not slugs:
        # The registry is empty, which means this hook ran before links.py or
        # links.py is unwired. Either way the section would be silently empty,
        # and a shortcut bar that quietly vanishes is worse than a loud one.
        print(
            "::warning::quick links: the slug registry is empty -- is "
            "hooks/quicklinks.py registered AFTER hooks/links.py in mkdocs.yml?"
        )
        return nav

    found, misses = _resolve(pairs, slugs, _base(config))

    for label, target, detail in misses:
        print("::warning::quick links: " + label + " -> " + detail)
        _links.add_issue("quick-link", SOURCE, target, detail)

    if not found:
        print("quick links: nothing resolved, no section added")
        return nav

    section = Section(title=title, children=[Link(label, href) for label, href in found])
    # MkDocs sets `parent` while it builds the tree; anything added afterwards
    # has to do it by hand or the breadcrumb and active logic see an orphan.
    for child in section.children:
        child.parent = section

    at = 0
    for index, item in enumerate(nav.items):
        if getattr(item, "title", None) == AFTER_ITEM:
            at = index + 1
            break
    nav.items.insert(at, section)

    external = sum(1 for row in _report if row[3] == "external" and row[2])
    print(
        "quick links: " + str(len(found)) + " link(s) below " + AFTER_ITEM
        + " (" + str(external) + " external)"
        + (", " + str(len(misses)) + " dropped" if misses else "")
    )
    return nav


def on_post_build(config):
    """One table saying where every shortcut points.

    🔒 Labels, slugs and URLs only -- nothing here touches page content or keys.

    ⚠️ This runs AFTER links.py's on_post_build (hook order), so the misses
    filed above are already in link-report.json by now. This table is the
    human-readable half; that file is the machine-readable one.
    """
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path or not _report:
        return

    broken = [row for row in _report if row[2] is None]
    lines = [
        "### 🔗 Quick links",
        "",
        ("🔴 **" + str(len(broken)) + " of " + str(len(_report))
         + " did not resolve and were dropped from the sidebar.**"
         if broken else
         "✅ All " + str(len(_report)) + " resolved."),
        "",
        "Edit the list in `" + SOURCE + "`. A slug is a page's permanent `id:`, "
        "so moving or retitling a page does not break these -- only changing "
        "its `id:` does, and this table is where that shows up. An external "
        "URL is passed through as written and is never checked from here.",
        "",
        "| Label | Target | Kind | Goes to |",
        "|---|---|---|---|",
    ]
    for label, target, href, kind, detail in _report:
        shown = target if kind == "external" else "`@" + target + "`"
        mark = "↗ external" if kind == "external" else "page"
        goes = "`" + href + "`" if href else "🔴 " + detail
        lines.append(
            "| " + label + " | " + shown + " | " + mark + " | " + goes + " |"
        )

    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
