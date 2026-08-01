"""
Page visibility gate + inline span markers.

Reads `status:` from each page's frontmatter and decides whether the page is
built, listed, indexed, or encrypted. **A page with no `status:` is hidden.**

    status: public      listed in the sidebar, indexed, plaintext
    status: gated       listed, body AES-encrypted, needs a password
    status: unlisted    direct link only: no nav, no search, no search engines
    status: hidden      never built                          (DEFAULT)

And one independent switch, because the four statuses conflated two questions:

    listed: false       keep this page out of the nav, search and sitemap,
                        WHATEVER its status is

That is what makes `status: gated` + `listed: false` possible -- a page that is
encrypted AND undiscoverable, which the single-value `status:` could not express
(you had to pick one). `status: unlisted` is now simply shorthand for
"public + listed: false" and is kept because it reads better.

MULTIPLE KEYS (added 2026-08-01)
A gated page may name several groups, and ANY ONE of their passwords opens it:

    status: gated
    gates: [psm, admin]

This is ENVELOPE encryption, not N copies of the page:

  1. a random content key (CEK) is generated per page
  2. the finished HTML is encrypted ONCE with the CEK
  3. for each group, a key-encrypting key is derived from that group's secret
     and used to encrypt *the CEK*
  4. the page ships one ciphertext body plus a small list of wrapped CEKs

A wrapped CEK is ~100 bytes, so page weight is effectively independent of how
many groups can open it, and rotating one group's key rewraps 100 bytes without
touching the body or any other group. Encrypting the whole page once per group
would instead cost content-size x group-count and make every rotation a full
re-encrypt.

The wrap list is SHUFFLED and carries no labels. Which desk can open a document
is itself information, and an ordered list would hand it over.

NONE of these are access control while the repository is public. The markdown
source of every page, INCLUDING a gated page's plaintext, is readable at
github.com by anyone. Secrets keep the PASSWORD out of the repo; they do not
keep the CONTENT out. `gated` is a deterrent and a signal, not a lock.
See AUTHORING.md -> "What the gate actually does".

Wired in mkdocs.yml under `hooks:`. Documented in AUTHORING.md.
Its browser half is docs/javascripts/gate.js: the two share the cipher, the KDF
and the iteration count, so they change in the SAME PR or every gated page
fails to unlock with no error anyone can read.
"""

import base64
import gzip
import os
import random
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

ENV_PREFIX = "URITP_GATE_"

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
_nolist = set()
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


def _read_status(meta):
    """Anything unrecognised falls back to the default, which is the safe
    direction: a malformed page stays off the site rather than leaking onto
    it."""
    status = str(meta.get("status", DEFAULT)).strip().lower()
    return status if status in ALLOWED else DEFAULT


def _is_unlisted(meta, status):
    """Two ways to be undiscoverable, and they compose: the `unlisted` status,
    or `listed: false` on top of any other status."""
    if status == "unlisted":
        return True
    listed = meta.get("listed")
    return listed is False or str(listed).strip().lower() == "false"


def _gate_names(meta):
    """`gates: [psm, admin]`, or the singular `gate: psm` kept for the pages
    already written against it."""
    names = meta.get("gates")
    if names is None:
        names = meta.get("gate")
    if names is None:
        return []
    if isinstance(names, str):
        names = [names]
    return [str(n).strip() for n in names if str(n).strip()]


def _env_key(name):
    return ENV_PREFIX + name.upper().replace("-", "_")


def _secrets_for(meta, src_uri):
    """Every secret that may open this page, in no meaningful order.

    A NAMED gate whose environment variable is absent is a hard build failure.
    Not a warning: the failure mode it prevents is a page everyone believes is
    locked shipping in full plaintext, silently, which is worse than no deploy.
    """
    found = []

    literal = meta.get("password")
    if literal:
        found.append(str(literal))

    missing = []
    for name in _gate_names(meta):
        secret = os.environ.get(_env_key(name))
        if secret:
            found.append(secret)
        else:
            missing.append(name)

    if missing:
        raise ValueError(
            src_uri + ": status is 'gated' and names the gate(s) "
            + ", ".join(missing)
            + ", but the environment carries no "
            + ", ".join(_env_key(n) for n in missing)
            + ". Add the secret in GitHub -> Settings -> Secrets and variables "
            "-> Actions, and pass it through in .github/workflows/deploy.yml. "
            "Refusing to build rather than publish this page unencrypted."
        )

    if not found:
        raise ValueError(
            src_uri + ": status is 'gated' but no password was found. Add "
            "`gates: [name]` plus a " + ENV_PREFIX + "NAME secret, or "
            "`password:` in the frontmatter for a throwaway draft."
        )

    # Two groups sharing one password would otherwise ship two wraps that both
    # open, which leaks that they are the same secret.
    seen = set()
    unique = []
    for value in found:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


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


def _derive(password, salt):
    return PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS
    ).derive(password.encode())


def _encrypt(plaintext, passwords):
    """Envelope: one body ciphertext, one wrapped content key per password."""
    cek = AESGCM.generate_key(bit_length=256)
    nonce = secrets.token_bytes(12)
    body = AESGCM(cek).encrypt(nonce, plaintext.encode(), None)

    wraps = []
    for password in passwords:
        salt = secrets.token_bytes(16)
        wrap_nonce = secrets.token_bytes(12)
        wrapped = AESGCM(_derive(password, salt)).encrypt(wrap_nonce, cek, None)
        wraps.append(
            {"s": _b64(salt), "n": _b64(wrap_nonce), "w": _b64(wrapped)}
        )

    # Position must not identify the group. Frontmatter order would otherwise
    # say "the first key is psm" to anyone reading the built HTML.
    random.SystemRandom().shuffle(wraps)

    return _b64(nonce), _b64(body), wraps


def _keys_attr(wraps):
    """Base64 of a compact JSON array, so no quoting can break the attribute
    and the group count is the only thing legible at a glance."""
    parts = [
        '{"s":"' + w["s"] + '","n":"' + w["n"] + '","w":"' + w["w"] + '"}'
        for w in wraps
    ]
    return base64.b64encode(("[" + ",".join(parts) + "]").encode()).decode()


def on_files(files, config):
    """Drop hidden pages before anything can link to or index them, and fail
    the build NOW if a gated page names a gate with no secret behind it --
    before a single page renders, rather than part-way through."""
    _status.clear()
    _nolist.clear()
    _noindex_paths.clear()
    kept = []

    for f in files:
        if not f.is_documentation_page():
            kept.append(f)
            continue

        meta = _read_meta(f.abs_src_path)
        status = _read_status(meta)
        _status[f.src_uri] = status

        if status == "hidden":
            continue

        if status == "gated":
            _secrets_for(meta, f.src_uri)   # raises if a key is missing

        if _is_unlisted(meta, status):
            _nolist.add(f.src_uri)
            f.inclusion = InclusionLevel.NOT_IN_NAV

        kept.append(f)

    return Files(kept)


def on_nav(nav, config, files):
    """Prune undiscoverable pages from the finished nav tree.

    Belt and braces: awesome-nav builds navigation from scratch rather than
    filtering what MkDocs generates, so it may not honour InclusionLevel.
    Pruning here works regardless of who built the tree.
    """

    def prune(items):
        out = []
        for item in items:
            if getattr(item, "is_page", False):
                if item.file.src_uri in _nolist:
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
    if page.file.src_uri in _nolist:
        search = page.meta.get("search")
        search = search if isinstance(search, dict) else {}
        search["exclude"] = True
        page.meta["search"] = search

    if _status.get(page.file.src_uri) == "gated":
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

    passwords = _secrets_for(page.meta, page.file.src_uri)
    nonce, ciphertext, wraps = _encrypt(html, passwords)

    # Never let a secret reach a template.
    page.meta.pop("password", None)

    note = (
        "This page is not public. Enter the password you were given, or ask "
        "production management."
    )

    return (
        '<div class="gate" data-nonce="' + nonce + '"'
        ' data-iter="' + str(ITERATIONS) + '"'
        ' data-keys="' + _keys_attr(wraps) + '"'
        ' data-ct="' + ciphertext + '">'
        '<form class="gate__form" autocomplete="off">'
        '<p class="gate__label">Restricted page</p>'
        '<p class="gate__note">' + note + '</p>'
        '<div class="gate__row">'
        '<input class="gate__input" type="password" name="gatepw"'
        ' placeholder="Password" aria-label="Page password" required>'
        '<button class="gate__btn" type="submit">Unlock</button>'
        '</div>'
        '<p class="gate__error" hidden>That password did not work.</p>'
        '</form></div>'
    )


def on_post_page(output, page, config):
    """Tell crawlers to skip undiscoverable pages.

    Site search and the sidebar were already handled, but MkDocs writes EVERY
    built page into sitemap.xml, which hands them straight to Google.
    `noindex` asks them not to list it; on_post_build below stops us pointing
    at it in the first place. Honest limits: this is a request, not a barrier,
    and it does nothing about anyone who already has the URL.
    """
    if page.file.src_uri not in _nolist:
        return output

    _noindex_paths.add(page.file.dest_uri.replace("\\", "/"))
    return output.replace("<head>", "<head>" + NOINDEX, 1)


def on_post_build(config):
    """Strip undiscoverable pages out of the generated sitemap (and its .gz)."""
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
