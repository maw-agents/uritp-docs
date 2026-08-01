"""
Stable-identity internal links, and the backlinks they make possible.

A link names a page's IDENTITY, never its location:

    [Smith Theatre](@smith-theatre)
    [the venue notes](@smith-theatre#venue-notes)

`@smith-theatre` is the target's `id:`, declared once in frontmatter and never
changed again. Moving the file, renaming its folder, retitling the page, or
rewriting a heading cannot break that link, because none of those things are
what the link points at. This hook resolves each id to the target's real URL at
build time.

WHY IT EXISTS
On 2026-08-01 the live site froze twice inside forty minutes, the same way both
times: a page moved, relative `.md` paths went stale, and because the workflow
runs `mkdocs build --strict` the whole deploy died while Pages kept serving an
older commit with no visible signal. The second incident was ONE rename (Smith
Theatre into SPAC/) breaking EIGHT links across six files in both directions --
inbound links to the moved page, and the moved page's own outbound links. Two
rounds of hand-patching missed three of them, because finding every link to a
page by reading is exactly the job a human is worst at.

So this hook deliberately takes the opposite stance to --strict:

    An unresolvable link renders as a visible inline marker, is reported,
    and THE BUILD CONTINUES.

One typo must never again freeze an entire reference site that somebody is
trying to load a show from. The failure becomes local and visible instead of
global and silent. Set URITP_LINKS_STRICT=1 to restore hard-fail behaviour.

BACKLINKS (added 2026-08-01)
The id registry already knows every link on the site, so the reverse map is
free: each page renders a `Linked from` section naming every page that points
at it. Michael's ask was for a link to "pop up to link to both pages" -- the
relationship is mutual, so both ends should show it.

Why this and not only hover previews: previews fire on HOVER, and this site is
read on a phone at least as often as on a desktop. A backlink is a rendered
list. It works on a touch screen, in print, and in the search index. Instant
previews are enabled too (mkdocs.yml), but they are the desktop bonus, not the
mechanism.

Two rules the backlink index must not break:

  1. An `unlisted` page is NEVER named as a source. Unlisted means nobody
     discovers it; listing it on a public page is precisely discovery, and
     would quietly convert the weakest visibility state into the loudest.
     `hidden` needs no rule -- visibility.py drops those before this hook
     ever sees the file list.
  2. Self-links are dropped, or a page's own Related section would cite it.

WHAT IT DELIBERATELY DOES NOT DO
It does not resolve by heading text. `mkdocs-autorefs` does, and that trades one
fragile key for another: an anchor derived from a heading slug dies the moment
someone rewrites the heading, which is a far more frequent edit than moving a
file. Explicit `{#anchor}` ids are the stable form, and this hook reports any
deep link that is riding on heading text instead.

Wired in mkdocs.yml under `hooks:`, AFTER visibility.py so the registry never
holds a page that will not be built. Documented in AUTHORING.md.
"""

import datetime
import difflib
import json
import os
import posixpath
import re

import yaml
from mkdocs.utils import get_relative_url

STRICT = os.environ.get("URITP_LINKS_STRICT") == "1"

# Set URITP_BACKLINKS=0 to turn the Linked-from sections off without unwiring
# the hook, which would take id resolution down with it.
BACKLINKS = os.environ.get("URITP_BACKLINKS", "1") != "0"

BACKLINK_HEADING = "Linked from"
BACKLINK_ANCHOR = "linked-from"

_FRONTMATTER = re.compile(rb"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
_FENCE = re.compile(r"(^```.*?^```)", re.DOTALL | re.MULTILINE)

# [text](@page-id)  /  [text](@page-id#anchor)
_IDLINK = re.compile(r"\[([^\[\]]*)\]\(@([A-Za-z0-9][\w.-]*)(#[\w.-]+)?\)")

# [text](../legacy/path.md#anchor) -- the old form, still resolved, but reported
_MDLINK = re.compile(
    r"\[([^\[\]]*)\]\((?!https?://|mailto:|@|#)([^()\s]+?\.md)(#[\w.-]+)?\)"
)

_HEADING = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t]*$", re.MULTILINE)
_H1 = re.compile(r"^#[ \t]+(.+?)[ \t]*$", re.MULTILINE)
_EXPLICIT_ID = re.compile(r"\{#([\w.-]+)\}\s*$")
_TRAILING_ID = re.compile(r"\s*\{#[\w.-]+\}\s*$")

_REDIRECT = (
    '<!doctype html>\n<html lang="en">\n<head>\n'
    '<meta charset="utf-8">\n'
    '<title>Moved</title>\n'
    '<link rel="canonical" href="{href}">\n'
    '<meta name="robots" content="noindex">\n'
    '<meta http-equiv="refresh" content="0; url={href}">\n'
    '</head>\n<body>\n'
    '<p>This page moved. Redirecting to <a href="{href}">{href}</a>.</p>\n'
    '</body>\n</html>\n'
)

_by_id = {}      # page id        -> src_uri
_id_of = {}      # src_uri        -> page id
_files = {}      # src_uri        -> mkdocs File
_anchors = {}    # src_uri        -> (explicit ids, heading-text slugs)
_alias = {}      # retired url    -> src_uri
_bodies = {}     # src_uri        -> raw markdown, for the backlink pass
_titles = {}     # src_uri        -> display title
_nameable = {}   # src_uri        -> may this be NAMED as a backlink source?
_backlinks = {}  # target src_uri -> set of source src_uri
_issues = []


def _slug(text):
    """Approximate Python-Markdown's toc slugify, for FRAGILE detection only.
    It never decides whether a link resolves, so a near miss is harmless."""
    text = re.sub(r"\{#[\w.-]+\}", "", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_]", "", text).strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text).strip("-")


def _read(abs_path):
    try:
        with open(abs_path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return {}, ""
    meta = {}
    match = _FRONTMATTER.match(raw)
    if match:
        try:
            parsed = yaml.safe_load(match.group(1))
            if isinstance(parsed, dict):
                meta = parsed
        except yaml.YAMLError:
            meta = {}
    return meta, raw.decode("utf-8", "replace")


def _fallback_id(src_uri):
    """No `id:` in frontmatter is fine for a page nobody links to yet. The
    filename stands in, and a folder's index.md takes the folder's name."""
    stem = posixpath.basename(src_uri)[: -len(".md")]
    if stem != "index":
        return stem
    parent = posixpath.dirname(src_uri)
    return posixpath.basename(parent) if parent else "home"


def _title_for(meta, body, src_uri):
    """Frontmatter title, else the H1, else the filename. The H1 fallback is
    what keeps a backlink readable on a page whose author skipped `title:`."""
    declared = meta.get("title")
    if declared:
        return str(declared).strip()
    found = _H1.search(body)
    if found:
        return _TRAILING_ID.sub("", found.group(1)).strip()
    return _fallback_id(src_uri).replace("-", " ")


def _note(kind, page_src, link, detail):
    _issues.append(
        {"kind": kind, "page": page_src, "link": link, "detail": detail}
    )


def _prose_parts(body):
    """Everything outside fenced code. A page documenting the link syntax must
    not have its examples counted as real links."""
    return [p for p in _FENCE.split(body) if not p.startswith("```")]


def _outbound(src_uri, body):
    """Every page this one points at, as src_uris. Unresolvable links are
    ignored here: they are already reported during rendering, and reporting
    them twice would double every count in the link report."""
    targets = set()
    base = posixpath.dirname(src_uri)

    for part in _prose_parts(body):
        for match in _IDLINK.finditer(part):
            target = _by_id.get(match.group(2))
            if target:
                targets.add(target)
        for match in _MDLINK.finditer(part):
            target = posixpath.normpath(posixpath.join(base, match.group(2)))
            if target in _files:
                targets.add(target)

    targets.discard(src_uri)
    return targets


def _index_backlinks():
    """Runs after every id is registered, never inside the first pass: a page
    linking to one declared later in the walk would otherwise be dropped."""
    for src_uri, body in _bodies.items():
        for target in _outbound(src_uri, body):
            _backlinks.setdefault(target, set()).add(src_uri)


def _backlink_block(src_uri):
    sources = _backlinks.get(src_uri)
    if not sources:
        return ""

    rows = []
    for source in sources:
        if not _nameable.get(source, True):
            continue          # unlisted: naming it here IS discovery
        page_id = _id_of.get(source)
        if page_id:
            rows.append((_titles.get(source, page_id), page_id))

    if not rows:
        return ""

    rows.sort(key=lambda row: row[0].lower())
    lines = ["- [" + title + "](@" + pid + ")" for title, pid in rows]
    return (
        "\n\n## " + BACKLINK_HEADING + " {#" + BACKLINK_ANCHOR + "}\n\n"
        + "\n".join(lines)
        + "\n"
    )


def on_files(files, config):
    for store in (
        _by_id, _id_of, _files, _anchors, _alias,
        _bodies, _titles, _nameable, _backlinks,
    ):
        store.clear()
    del _issues[:]

    for f in files:
        if not f.is_documentation_page():
            continue

        meta, body = _read(f.abs_src_path)
        status = str(meta.get("status", "")).strip().lower()

        _files[f.src_uri] = f
        _bodies[f.src_uri] = body
        _titles[f.src_uri] = _title_for(meta, body, f.src_uri)
        _nameable[f.src_uri] = status != "unlisted"

        declared = meta.get("id")
        page_id = str(declared).strip() if declared else _fallback_id(f.src_uri)
        if page_id in _by_id:
            _note(
                "duplicate-id", f.src_uri, "@" + page_id,
                "already claimed by " + _by_id[page_id] + "; this page is "
                "unreachable by id until one of them is renamed",
            )
        else:
            _by_id[page_id] = f.src_uri
            _id_of[f.src_uri] = page_id

        explicit, auto = set(), set()
        for heading in _HEADING.findall(body):
            found = _EXPLICIT_ID.search(heading)
            if found:
                explicit.add(found.group(1))
            auto.add(_slug(heading))
        explicit.add(BACKLINK_ANCHOR)   # this hook emits it; it is a real target
        _anchors[f.src_uri] = (explicit, auto)

        for old in meta.get("aliases") or []:
            key = str(old).strip().strip("/")
            if key.endswith(".md"):
                key = key[: -len(".md")]
            if key.endswith("/index"):
                key = key[: -len("/index")]
            if key:
                _alias[key] = f.src_uri

    if BACKLINKS:
        _index_backlinks()

    return files


def _dead(text, shown, why, page):
    _note("dead-link", page.file.src_uri, shown, why)
    if STRICT:
        raise ValueError(page.file.src_uri + ": " + shown + " -- " + why)
    return (
        '<span class="deadlink" title="' + why.replace('"', "'") + '">'
        + text + "</span>"
    )


def _check_anchor(target_src, anchor, shown, page):
    """An anchor that only matches heading TEXT still works today and would
    break silently on a copy-edit, so it is reported rather than accepted."""
    explicit, auto = _anchors.get(target_src, (set(), set()))
    if anchor in explicit:
        return
    if anchor in auto:
        _note(
            "fragile-anchor", page.file.src_uri, shown,
            "resolves off heading text; add {#" + anchor + "} to that heading "
            "so a reworded heading cannot break it",
        )
        return
    _note(
        "missing-anchor", page.file.src_uri, shown,
        "no heading in the target carries this anchor; the link lands at the "
        "top of the page",
    )


def _resolve_id(match, page):
    text, page_id = match.group(1), match.group(2)
    anchor = match.group(3) or ""
    shown = "@" + page_id + anchor

    target_src = _by_id.get(page_id)
    if target_src is None:
        near = difflib.get_close_matches(page_id, list(_by_id), n=2, cutoff=0.6)
        why = "no page carries id '" + page_id + "'"
        if near:
            why += " -- did you mean @" + " or @".join(near) + "?"
        return _dead(text, shown, why, page)

    if anchor:
        _check_anchor(target_src, anchor[1:], shown, page)

    url = get_relative_url(_files[target_src].url, page.file.url)
    return "[" + text + "](" + url + anchor + ")"


def _resolve_md(match, page):
    text, rel = match.group(1), match.group(2)
    anchor = match.group(3) or ""
    shown = rel + anchor

    base = posixpath.dirname(page.file.src_uri)
    target_src = posixpath.normpath(posixpath.join(base, rel))
    target = _files.get(target_src)

    if target is None:
        return _dead(
            text, shown,
            "no page at " + target_src + " (moved, renamed, or status: hidden)",
            page,
        )

    _note(
        "legacy-path", page.file.src_uri, shown,
        "path-based link; rewrite as @"
        + _id_of.get(target_src, "?")
        + " so a future move cannot break it",
    )

    if anchor:
        _check_anchor(target_src, anchor[1:], shown, page)

    url = get_relative_url(target.url, page.file.url)
    return "[" + text + "](" + url + anchor + ")"


def on_page_markdown(markdown, page, config, files):
    # Appended BEFORE resolution so the generated @id links travel exactly the
    # same path, and the same reporting, as a hand-written one.
    if BACKLINKS:
        markdown += _backlink_block(page.file.src_uri)

    parts = _FENCE.split(markdown)
    for i, part in enumerate(parts):
        if part.startswith("```"):
            continue          # a page documenting the syntax must show it raw
        part = _IDLINK.sub(lambda m: _resolve_id(m, page), part)
        part = _MDLINK.sub(lambda m: _resolve_md(m, page), part)
        parts[i] = part
    return "".join(parts)


def _write_aliases(site_dir):
    """A retired URL keeps working. Moving a page breaks every bookmark, email
    link and QR code pointing at the old address, and none of those are things
    this repo can go and fix."""
    live = {f.url.strip("/") for f in _files.values()}
    written = 0

    for old, target_src in sorted(_alias.items()):
        target = _files.get(target_src)
        if target is None:
            continue
        if old in live:
            _note(
                "alias-collision", target_src, "/" + old + "/",
                "a real page already publishes at this address; the alias was "
                "skipped rather than overwrite it",
            )
            continue

        href = get_relative_url(target.url, old + "/")
        folder = os.path.join(site_dir, *old.split("/"))
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(_REDIRECT.format(href=href))
        written += 1

    return written


def _orphans():
    """Pages nothing links to. Not an error: a section landing page is reached
    from the sidebar and needs no inbound link. But it is the one thing a
    backlink index can see that nobody else can, so it is worth printing
    rather than acting on."""
    return sorted(
        src for src in _files
        if src not in _backlinks and posixpath.basename(src) != "index.md"
    )


def on_post_build(config):
    site_dir = config["site_dir"]
    redirects = _write_aliases(site_dir)
    orphans = _orphans() if BACKLINKS else []

    report = {
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "pages_indexed": len(_by_id),
        "redirects_written": redirects,
        "backlinks_enabled": BACKLINKS,
        "pages_with_backlinks": len(_backlinks),
        "orphans": orphans,
        "issues": _issues,
    }
    with open(os.path.join(site_dir, "link-report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    counts = {}
    for issue in _issues:
        counts[issue["kind"]] = counts.get(issue["kind"], 0) + 1

    headline = (
        "links: " + str(len(_by_id)) + " pages indexed, "
        + str(len(_backlinks)) + " with backlinks, "
        + str(redirects) + " redirects written"
    )
    if counts:
        headline += " -- " + ", ".join(
            k + " x" + str(v) for k, v in sorted(counts.items())
        )
    print(headline)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return

    lines = ["### Link report", "", headline, ""]
    if _issues:
        lines += ["| Kind | Page | Link | Detail |", "|---|---|---|---|"]
        for issue in _issues:
            lines.append(
                "| `" + issue["kind"] + "` | `" + issue["page"] + "` | `"
                + issue["link"] + "` | " + issue["detail"] + " |"
            )
    else:
        lines.append("No issues. Every internal link resolved.")

    if orphans:
        lines += [
            "",
            "<details><summary>Nothing links to these "
            + str(len(orphans)) + " pages</summary>",
            "",
        ]
        lines += ["- `" + src + "`" for src in orphans]
        lines += ["", "</details>"]

    with open(summary, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
