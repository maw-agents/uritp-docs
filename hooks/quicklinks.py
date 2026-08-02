"""
The Quick Links section in the sidebar.

Reads `quick-links.yml` at the repo root -- `Label: slug` -- resolves each slug
against the registry hooks/links.py already built, and inserts a section of
LINKS immediately below Home.

    quick-links.yml        the list. Data, editable by anyone.
    this file              resolution, placement, and what to say when a slug
                           does not exist.

=======================================================================
🔴 WHY THIS IS A HOOK AND NOT FOUR LINES OF .nav.yml
=======================================================================

The obvious version is a section in docs/.nav.yml naming the pages:

    nav:
      - index.md
      - Quick links:
        - venues/spac/smith-theatre.md      # <- DO NOT
      - Venues: venues

That is a bug, and awesome-nav's own documentation says so: *"Glob patterns
will never match files or directories that are already part of the
navigation."* Naming Smith Theatre there would REMOVE it from Venues -- the
page MOVES into Quick links rather than being shortcut to. A page can appear in
the nav exactly once.

awesome-nav's stated workaround is to "create a link instead of the page
entry", which means a hardcoded relative path. That is precisely the fragility
hooks/links.py exists to abolish: on 2026-08-01 one page move stale-ed eight
path links across six files and froze the live site twice inside forty minutes.

So a LINK is right and a hardcoded path is not, which leaves exactly one
option: links built from slugs, resolved at build time. Michael asked for it
"by @-slug that can be found and traced back for reporting" -- that instinct is
not a nicety, it is the only version that is not a regression.

=======================================================================
ONE REGISTRY, ONE REPORT
=======================================================================

This hook does NOT parse frontmatter. It reads `config["_uritp_slugs"]`, which
hooks/links.py publishes from the same table that resolves every `@slug` in
every page body. Two parsers would drift, and only one of them would be
reported on.

Misses are filed through `links.add_issue()`, so a broken quick link lands in
`link-report.json` and the same run-summary table as a broken body link. That
is the answer to "which slugs need updating if I rename a page": ONE place,
not one per feature.

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
quick link to one reads as a miss and is reported like any other. An `unlisted`
page DOES resolve, and pointing a quick link at one is arguably the whole
feature: it is out of the main sidebar but reachable by direct link.

Documented for authors in quick-links.yml itself, which is where someone
editing the list is already looking.
"""

import difflib
import os
import sys

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

# The section is inserted immediately AFTER the nav item with this title.
# Matched by title rather than by index so that reordering docs/.nav.yml cannot
# silently move the shortcuts somewhere surprising. No match -> the top.
AFTER_ITEM = "Home"

_report = []      # (label, slug, url_or_None, detail_or_None). Safe to print.


def _load(config):
    """Read quick-links.yml from the repo root, beside mkdocs.yml.

    Returns (title, [(label, slug)], problem_or_None). A missing file is NOT a
    problem -- the feature is optional and a repo without the file simply has
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
            "If a slug starts with @, it must be quoted: \"@smith-theatre\". "
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
        return title, [], SOURCE + ": `links:` must be a mapping of Label: slug"

    clean = []
    for label, slug in pairs:
        label = str(label).strip()
        # The `@` is optional on the way in. Michael thinks in @slug and YAML
        # hates a bare one, so accept both spellings rather than making the
        # quoting rule load-bearing.
        slug = str(slug or "").strip().lstrip("@").strip()
        if label and slug:
            clean.append((label, slug))
    return title, clean, None


def _resolve(pairs, slugs):
    """(links, misses). `slugs` is links.py's registry: slug -> (url, title)."""
    known = _links.known_ids()
    found = []
    misses = []

    for label, slug in pairs:
        entry = slugs.get(slug)
        if entry:
            url, _title = entry
            found.append((label, slug, url))
            _report.append((label, slug, url, None))
            continue

        near = difflib.get_close_matches(slug, known, n=2, cutoff=0.6)
        detail = "no page carries id '" + slug + "'"
        if near:
            detail += " -- did you mean " + " or ".join(near) + "?"
        elif known:
            detail += ". This link was dropped from the sidebar"
        misses.append((label, slug, detail))
        _report.append((label, slug, None, detail))

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

    found, misses = _resolve(pairs, slugs)

    for label, slug, detail in misses:
        print("::warning::quick links: " + label + " -> " + detail)
        _links.add_issue("quick-link", SOURCE, "@" + slug, detail)

    if not found:
        print("quick links: nothing resolved, no section added")
        return nav

    section = Section(title=title, children=[Link(label, url) for label, _s, url in found])
    # MkDocs sets `parent` while it builds the tree; anything added afterwards
    # has to do it by hand or the breadcrumb/active logic sees an orphan.
    for child in section.children:
        child.parent = section

    at = 0
    for index, item in enumerate(nav.items):
        if getattr(item, "title", None) == AFTER_ITEM:
            at = index + 1
            break
    nav.items.insert(at, section)

    print(
        "quick links: " + str(len(found)) + " link(s) below " + AFTER_ITEM
        + (", " + str(len(misses)) + " dropped" if misses else "")
    )
    return nav


def on_post_build(config):
    """One table saying where every shortcut points.

    🔒 Slugs and URLs only -- nothing here touches page content or keys.

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
        "its `id:` does, and this table is where that shows up.",
        "",
        "| Label | Slug | Resolves to |",
        "|---|---|---|",
    ]
    for label, slug, url, detail in _report:
        target = "`/" + url + "`" if url else "🔴 " + detail
        lines.append("| " + label + " | `@" + slug + "` | " + target + " |")

    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
