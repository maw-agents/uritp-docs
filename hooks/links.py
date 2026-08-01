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
ran `mkdocs build --strict` the whole deploy died while Pages kept serving an
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

(`--strict` itself was finally removed from deploy.yml later the same day,
after it froze the site a THIRD time -- over one word of frontmatter. This
hook's stance was right and the pipeline had been quietly overruling it.)

HIDDEN IS NOT BROKEN  (added 2026-08-01, Michael)
There are two completely different reasons a link can fail to resolve, and
until now this hook could not tell them apart:

    @usnig-these-docs      a typo. Nobody meant this. Show the marker.
    @using-these-docs      the target is `status: hidden`. Somebody meant it.

hooks/visibility.py drops hidden pages from the file list BEFORE this hook
runs, so a link to one used to look exactly like a misspelling. It now hands
over what it refused to build, on the config as `_uritp_hidden`, and a link to
a known-hidden page renders as PLAIN TEXT: the words stay readable in the
sentence, nothing pretends to be clickable, and it is reported as
`hidden-target` rather than `dead-link`.

    ⚠️ DELIBERATELY NOT A REDIRECT TO HOME. That was considered and rejected:
    a redirect takes a reader somewhere they did not ask to go and hides that
    anything is missing -- a guest designer clicks "Using these docs", lands
    on the homepage, and concludes the site is broken or that they misclicked.
    Redirects are the right tool for a page that MOVED, which is why this hook
    already writes them for `aliases:`. A hidden page has not moved. It is not
    there, and the honest render says so by not being a link.

And because hiding a page should tell you what you just did, the build now
prints a HIDE IMPACT report: every hidden page, every page that still links to
it, and whether any `.nav.yml` still names it by filename. That last one is the
exact defect that froze the site -- a nav entry pointing at a page that is
never built -- caught by name, in the same build, instead of as a red X.

BACKLINKS (added 2026-08-01)
The id registry already knows every link on the site, so the reverse map is
free: each page renders a `Linked from` section naming every page that points
at it. Michael's ask was for a link to "pop up to link to both pages" -- the
relationship is mutual, so both ends should show it.

Why this and not only hover previews: previews fire on HOVER, and this site is
read on a phone at least as often as on a desktop. A backlink is a rendered
list. It works on a touch screen, in print, and in the search index.

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

# Written by hooks/visibility.py in its on_files, which runs BEFORE this one
# (see the hook order in mkdocs.yml). src_uri -> declared `id:` or None.
# A plain config key rather than an import: unwire that hook and this reads an
# empty dict and behaves exactly as it did before.
HANDOFF = "_uritp_hidden"

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

_hidden_by_id = {}   # page id -> src_uri, for pages visibility.py did not build
_hidden_src = set()  # those same pages, by src_uri
_hits = {}           # hidden src_uri -> set of pages still linking to it


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


def _index_hidden(config):
    """Register the pages visibility.py refused to build, so a link to one can
    say `hidden` instead of `broken`.

    A LIVE page always wins the id: if something else has since claimed the
    name, the link should resolve to the live page, not report a ghost.
    """
    _hidden_by_id.clear()
    _hidden_src.clear()
    _hits.clear()

    handed = config.get(HANDOFF) or {}
    for src_uri, declared_id in handed.items():
        _hidden_src.add(src_uri)
        page_id = str(declared_id).strip() if declared_id else _fallback_id(src_uri)
        if page_id and page_id not in _by_id:
            _hidden_by_id[page_id] = src_uri


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

    # AFTER the live registry, so a live page always wins a contested id.
    _index_hidden(config)

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


def _hidden_target(text, shown, target_src, page):
    """The target exists in the tree and was deliberately not published.

    Renders as PLAIN TEXT, not a marker and not a redirect: the sentence still
    reads, and nothing invites a click that cannot go anywhere. Never raises,
    even under URITP_LINKS_STRICT -- somebody meant to do this, so it is not an
    error, it is a consequence, and the report below names it.
    """
    _note(
        "hidden-target", page.file.src_uri, shown,
        "target " + target_src + " is `status: hidden`, so it is not built; "
        "this link rendered as plain text. Set that page to `unlisted` if you "
        "want it linkable but out of the sidebar.",
    )
    _hits.setdefault(target_src, set()).add(page.file.src_uri)
    return text


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
        # Deliberately hidden, or genuinely a typo? Two different sentences.
        hidden = _hidden_by_id.get(page_id)
        if hidden:
            return _hidden_target(text, shown, hidden, page)
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
        if target_src in _hidden_src:
            return _hidden_target(text, shown, target_src, page)
        return _dead(
            text, shown,
            "no page at " + target_src + " (moved or renamed)",
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


def _nav_files(docs_dir):
    """Every .nav.yml under docs/, as (path relative to docs_dir, text)."""
    out = []
    for root, _dirs, names in os.walk(docs_dir):
        for name in names:
            if name != ".nav.yml":
                continue
            full = os.path.join(root, name)
            try:
                with open(full, encoding="utf-8") as fh:
                    out.append((os.path.relpath(full, docs_dir), fh.read()))
            except OSError:
                continue
    return out


def _nav_claims(docs_dir):
    """Which hidden pages are still named BY FILENAME in a .nav.yml.

    THIS IS THE ONE THAT FROZE THE SITE. A folder entry in .nav.yml is a
    container and shrinks harmlessly when a page inside it is hidden. A
    FILENAME entry is a hard reference, and hiding that page leaves the nav
    pointing at something that is never built.

    Deliberately a text scan and not a YAML parse: a commented-out line is NOT
    a claim, and the comment form is exactly how a filename entry gets parked
    while its page is hidden. Parsing would silently ignore both.
    """
    claims = {}
    if not _hidden_src:
        return claims

    navs = _nav_files(docs_dir)
    for src_uri in _hidden_src:
        basename = posixpath.basename(src_uri)
        for rel, text in navs:
            for line in text.splitlines():
                bare = line.strip()
                if bare.startswith("#") or basename not in bare:
                    continue
                claims.setdefault(src_uri, []).append(rel)
                break
    return claims


def _hide_report(docs_dir):
    """Hiding a page should say what it just orphaned, in the same build."""
    if not _hidden_src:
        return []

    claims = _nav_claims(docs_dir)
    loud = bool(claims)

    for src_uri, navs in sorted(claims.items()):
        print(
            "::warning::" + src_uri + " is `status: hidden` but is still named "
            "by filename in " + ", ".join(sorted(set(navs))) + " -- that nav "
            "entry points at a page which is never built. Comment the line "
            "out, or set the page to `unlisted` instead."
        )

    linked = sum(len(v) for v in _hits.values())
    print(
        "links: hide impact -- " + str(len(_hidden_src)) + " hidden page(s), "
        + str(linked) + " inbound link(s) rendered as plain text, "
        + str(len(claims)) + " still named in a .nav.yml"
    )

    lines = [
        "### " + ("\u26a0\ufe0f" if loud else "\U0001f648") + " Hide impact",
        "",
        "What is not published, and what still points at it. A hidden page is "
        "never built, so an inbound link renders as plain text rather than a "
        "dead click. **`unlisted` is the status you want if a page should stay "
        "linkable but out of the sidebar.**",
        "",
        "| Hidden page | Linked from | Named in a .nav.yml |",
        "|---|---|---|",
    ]
    for src_uri in sorted(_hidden_src):
        sources = sorted(_hits.get(src_uri, ()))
        where = ", ".join("`" + s + "`" for s in sources) if sources else "--"
        navs = claims.get(src_uri)
        flag = (
            "🔴 " + ", ".join("`" + n + "`" for n in sorted(set(navs)))
            if navs else "no"
        )
        lines.append("| `" + src_uri + "` | " + where + " | " + flag + " |")

    if loud:
        lines += [
            "",
            "🔴 **A nav entry naming a page that is never built is what froze "
            "this site on 2026-08-01.** It no longer fails the build -- "
            "`--strict` is gone -- but it will leave a gap in the sidebar. "
            "Fix it by commenting the line out or by using `unlisted`.",
        ]
    return lines + [""]


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
        "hidden_pages": sorted(_hidden_src),
        "hidden_inbound": {k: sorted(v) for k, v in sorted(_hits.items())},
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

    hide_lines = _hide_report(config["docs_dir"])

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

    lines += [""] + hide_lines

    with open(summary, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
