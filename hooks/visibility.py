"""
Page visibility gate + inline span markers.

Reads `status:` from each page's frontmatter and decides whether the page is
built, listed, indexed, or encrypted. **A page with no `status:` is hidden.**

    status: public      listed in the sidebar, indexed, plaintext
    status: gated       listed, body AES-encrypted, needs a password
    status: unlisted    direct link only: no nav, no search, no search engines
    status: hidden      never built                          (DEFAULT)

NONE of these are access control while the repository is public. The markdown
source of every page, INCLUDING a gated page's plaintext and its password, is
readable at github.com by anyone. `gated` is a deterrent and a signal, not a
lock. See AUTHORING.md -> "What the gate actually does".

Wired in mkdocs.yml under `hooks:`. Documented in AUTHORING.md.
"""

import base64
import gzip
import os
import re
import secrets

import yaml
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from mkdocs.structure.files import Files, InclusionLevel

DEFAULT = "hidden"
ALLOWED = {"public", "gated", "unlisted", "hidden"}
ITERATIONS = 250000

NOINDEX = '<meta name="robots" content="noindex, nofollow">'

_FRONTMATTER = re.compile(rb"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)

# [To be confirmed]{.tbc} -> <span class="tbc">To be confirmed</span>
#
# Python-Markdown's attr_list does NOT reliably produce a span from the bare
# bracket form, so the documented marker rendered as literal text on the live
# site. Doing the substitution here is deterministic and independent of what
# attr_list decides to support. The `\]\{` with no gap is what keeps ordinary
# markdown links `[text](url)` out of the match.
_SPAN = re.compile(r"\[([^\[\]\n]+)\]\{\s*\.([A-Za-z][\w-]*)\s*\}")

# Fenced code blocks, so a page documenting the marker still shows it literally.
_FENCE = re.compile(r"(^```.*?^```)", re.DOTALL | re.MULTILINE)

_status = {}
_noindex_paths = set()


def _read_meta(abs_path):
    try:
        with open(abs_path, "rb") as fh:
            head = fh.read(4096)
    except OSError:
        return {}
    match = _FRONTMATTER.match(head)
    if not match:
        return {}
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}
    return meta if isinstance(meta, dict) else {}


def _read_status(abs_path):
    """Anything unreadable or unrecognised falls back to the default, which is
    the safe direction: a malformed page stays off the site rather than
    leaking onto it."""
    status = str(_read_meta(abs_path).get("status", DEFAULT)).strip().lower()
    return status if status in ALLOWED else DEFAULT


def _password_for(page):
    """Frontmatter `password:` wins; otherwise `gate: designers` reads the
    environment variable URITP_GATE_DESIGNERS. The env-var form keeps the
    secret out of the repo, so it is the only form worth using once the repo
    is private."""
    pw = page.meta.get("password")
    if pw:
        return str(pw)
    gate = page.meta.get("gate")
    if gate:
        return os.environ.get("URITP_GATE_" + str(gate).strip().upper())
    return None


def _expand_spans(markdown):
    """Rewrite [text]{.class} outside fenced code blocks."""
    parts = _FENCE.split(markdown)
    for i, part in enumerate(parts):
        if part.startswith("```"):
            continue
        parts[i] = _SPAN.sub(r'<span class="\2">\1</span>', part)
    return "".join(parts)


def _b64(raw):
    return base64.b64encode(raw).decode()


def _encrypt(plaintext, password):
    salt = secrets.token_bytes(16)
    key = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS
    ).derive(password.encode())
    nonce = secrets.token_bytes(12)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode(), None)
    return _b64(salt), _b64(nonce), _b64(ct)


def on_files(files, config):
    """Drop hidden pages before anything can link to or index them."""
    _status.clear()
    _noindex_paths.clear()
    kept = []

    for f in files:
        if not f.is_documentation_page():
            kept.append(f)
            continue

        status = _read_status(f.abs_src_path)
        _status[f.src_uri] = status

        if status == "hidden":
            continue

        if status == "unlisted":
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
                    continue
            out.append(item)
        return out

    nav.items = prune(nav.items)
    return nav


def on_page_markdown(markdown, page, config, files):
    status = _status.get(page.file.src_uri)

    if status == "unlisted":
        search = page.meta.get("search")
        search = search if isinstance(search, dict) else {}
        search["exclude"] = True
        page.meta["search"] = search

    if status == "gated":
        # The right-hand outline is built from the markdown headings, so it
        # would happily list the section titles of a locked page. Hide it.
        hide = page.meta.get("hide") or []
        page.meta["hide"] = sorted(set(list(hide) + ["toc"]))

    return _expand_spans(markdown)


def on_page_content(html, page, config, files):
    """Replace a gated page's rendered body with ciphertext plus an unlock form.

    Runs AFTER markdown rendering, so what gets encrypted is the finished HTML.
    Material builds its search index from this same content, which means the
    index picks up the unlock form and never the real text.
    """
    if _status.get(page.file.src_uri) != "gated":
        return html

    password = _password_for(page)
    if not password:
        raise ValueError(
            page.file.src_uri + ": status is 'gated' but no password was found. "
            "Add `password:` to the frontmatter, or `gate: <name>` plus a "
            "URITP_GATE_<NAME> environment variable."
        )

    salt, nonce, ciphertext = _encrypt(html, password)

    # Never let the secret reach a template.
    page.meta.pop("password", None)

    return (
        '<div class="gate" data-salt="' + salt + '" data-nonce="' + nonce + '"'
        ' data-iter="' + str(ITERATIONS) + '" data-ct="' + ciphertext + '">'
        '<form class="gate__form" autocomplete="off">'
        '<p class="gate__label">Restricted page</p>'
        '<p class="gate__note">This page is not public. Enter the password you '
        'were given, or ask production management.</p>'
        '<div class="gate__row">'
        '<input class="gate__input" type="password" name="gatepw"'
        ' placeholder="Password" aria-label="Page password" required>'
        '<button class="gate__btn" type="submit">Unlock</button>'
        '</div>'
        '<p class="gate__error" hidden>That password did not work.</p>'
        '</form></div>'
    )


def on_post_page(output, page, config):
    """Tell crawlers to skip unlisted pages.

    Site search and the sidebar were already handled, but MkDocs writes EVERY
    built page into sitemap.xml, which hands unlisted pages straight to Google.
    `noindex` asks them not to list it; on_post_build below stops us pointing
    at it in the first place. Honest limits: this is a request, not a barrier,
    and it does nothing about anyone who already has the URL.
    """
    if _status.get(page.file.src_uri) != "unlisted":
        return output

    _noindex_paths.add(page.file.dest_uri.replace("\\", "/"))
    return output.replace("<head>", "<head>" + NOINDEX, 1)


def on_post_build(config):
    """Strip unlisted pages out of the generated sitemap (and its .gz twin)."""
    if not _noindex_paths:
        return

    site_dir = config["site_dir"]
    sitemap = os.path.join(site_dir, "sitemap.xml")
    if not os.path.exists(sitemap):
        return

    with open(sitemap, encoding="utf-8") as fh:
        xml = fh.read()

    def drop(match):
        block = match.group(0)
        for path in _noindex_paths:
            # dest_uri is like venues/rigging/index.html; the sitemap carries
            # the pretty URL, so compare on the directory part.
            pretty = path[: -len("index.html")] if path.endswith("index.html") else path
            if pretty and pretty in block:
                return ""
        return block

    cleaned = re.sub(r"<url>.*?</url>\s*", drop, xml, flags=re.DOTALL)

    with open(sitemap, "w", encoding="utf-8") as fh:
        fh.write(cleaned)

    gz = sitemap + ".gz"
    if os.path.exists(gz):
        with gzip.open(gz, "wb") as fh:
            fh.write(cleaned.encode("utf-8"))
