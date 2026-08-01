"""
Page visibility gate.

Reads `status:` from each page's frontmatter and decides whether the page is
built, listed, or dropped entirely. **A page with no `status:` is hidden.**

    status: public      in the sidebar, in search, in the sitemap
    status: unlisted    built and reachable by direct link only
    status: hidden      never built                        (DEFAULT)

⚠️ `hidden` means "not published to the site." It does NOT mean secret: the
   markdown still sits in a PUBLIC repo and anyone can read it on github.com.
   Obscurity is not access control. See AUTHORING.md.

Wired in mkdocs.yml under `hooks:`. Documented in AUTHORING.md.
"""

import re

import yaml
from mkdocs.structure.files import Files, InclusionLevel

DEFAULT = "hidden"
ALLOWED = {"public", "unlisted", "hidden"}

_FRONTMATTER = re.compile(rb"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)

# src_uri -> status, populated in on_files and read by the later events.
_status: dict[str, str] = {}


def _read_status(abs_path: str) -> str:
    """Parse just the frontmatter block. Anything unreadable or unrecognised
    falls back to the default, which is the safe direction: a malformed page
    stays off the site rather than leaking onto it."""
    try:
        with open(abs_path, "rb") as fh:
            head = fh.read(4096)
    except OSError:
        return DEFAULT

    match = _FRONTMATTER.match(head)
    if not match:
        return DEFAULT

    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return DEFAULT
    if not isinstance(meta, dict):
        return DEFAULT

    status = str(meta.get("status", DEFAULT)).strip().lower()
    return status if status in ALLOWED else DEFAULT


def on_files(files, config):
    """Drop hidden pages before anything can link to or index them."""
    _status.clear()
    kept = []

    for f in files:
        if not f.is_documentation_page():
            kept.append(f)
            continue

        status = _read_status(f.abs_src_path)
        _status[f.src_uri] = status

        if status == "hidden":
            continue  # never built, never served, never indexed

        if status == "unlisted":
            # Native MkDocs 1.6 signal. Also stops --strict complaining that a
            # built page is missing from the nav.
            f.inclusion = InclusionLevel.NOT_IN_NAV

        kept.append(f)

    return Files(kept)


def on_nav(nav, config, files):
    """Prune unlisted pages from the finished nav tree.

    Belt and braces: awesome-nav builds navigation from scratch rather than
    filtering what MkDocs generates, so it may not honour InclusionLevel.
    Pruning here works regardless of who built the tree.
    """

    def prune(items):
        out = []
        for item in items:
            if getattr(item, "is_page", False):
                if _status.get(item.file.src_uri) == "unlisted":
                    continue
            elif getattr(item, "is_section", False):
                item.children = prune(item.children)
                if not item.children:
                    continue  # drop a section left empty by the pruning
            out.append(item)
        return out

    nav.items = prune(nav.items)
    return nav


def on_page_markdown(markdown, page, config, files):
    """Keep unlisted pages out of the search index."""
    if _status.get(page.file.src_uri) == "unlisted":
        search = page.meta.get("search")
        if not isinstance(search, dict):
            search = {}
        search["exclude"] = True
        page.meta["search"] = search
    return markdown
