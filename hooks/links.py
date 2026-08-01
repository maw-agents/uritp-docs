"""
Stable-identity internal links.

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

_FRONTMATTER = re.compile(rb"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
_FENCE = re.compile(r"(^```.*?^```)", re.DOTALL | re.MULTILINE)

# [text](@page-id)  /  [text](@page-id#anchor)
_IDLINK = re.compile(r"\[([^\[\]]*)\]\(@([A-Za-z0-9][\w.-]*)(#[\w.-]+)?\)")

# [text](../legacy/path.md#anchor) -- the old form, still resolved, but reported
_MDLINK = re.compile(
    r"\[([^\[\]]*)\]\((?!https?://|mailto:|@|#)([^()\s]+?\.md)(#[\w.-]+)?\)"
)

_HEADING = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t]*$", re.MULTILINE)
_EXPLICIT_ID = re.compile(r"\{#([\w.-]+)\}\s*$")

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

_by_id = {}      # page id            -> src_uri
_files = {}      # src_uri            -> mkdocs File
_anchors = {}    # src_uri            -> (explicit ids, heading-text slugs)
_alias = {}      # retired url path   -> src_uri
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


def _note(kind, page_src, link, detail):
    _issues.append(
        {"kind": kind, "page": page_src, "link": link, "detail": detail}
    )


def on_files(files, config):
    for store in (_by_id, _files, _anchors, _alias):
        store.clear()
    del _issues[:]

    for f in files:
        if not f.is_documentation_page():
            continue

        meta, body = _read(f.abs_src_path)
        _files[f.src_uri] = f

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

        explicit, auto = set(), set()
        for heading in _HEADING.findall(body):
            found = _EXPLICIT_ID.search(heading)
            if found:
                explicit.add(found.group(1))
            auto.add(_slug(heading))
        _anchors[f.src_uri] = (explicit, auto)

        for old in meta.get("aliases") or []:
            key = str(old).strip().strip("/")
            if key.endswith(".md"):
                key = key[: -len(".md")]
            if key.endswith("/index"):
                key = key[: -len("/index")]
            if key:
                _alias[key] = f.src_uri

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
        + next((i for i, s in _by_id.items() if s == target_src), "?")
        + " so a future move cannot break it",
    )

    if anchor:
        _check_anchor(target_src, anchor[1:], shown, page)

    url = get_relative_url(target.url, page.file.url)
    return "[" + text + "](" + url + anchor + ")"


def on_page_markdown(markdown, page, config, files):
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


def on_post_build(config):
    site_dir = config["site_dir"]
    redirects = _write_aliases(site_dir)

    report = {
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "pages_indexed": len(_by_id),
        "redirects_written": redirects,
        "issues": _issues,
    }
    with open(os.path.join(site_dir, "link-report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    counts = {}
    for issue in _issues:
        counts[issue["kind"]] = counts.get(issue["kind"], 0) + 1

    headline = "links: " + str(len(_by_id)) + " pages indexed, " + str(redirects) \
        + " redirects written"
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

    with open(summary, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
