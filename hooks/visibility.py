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

That is what makes `status: gated` + `listed: false` possible -- encrypted AND
undiscoverable, which the single-value `status:` could not express.
`status: unlisted` is now shorthand for "public + listed: false".

MULTIPLE KEYS (2026-08-01)
A gated page may name several groups, and ANY ONE of their passwords opens it:

    status: gated
    gates: [psm, admin]

ENVELOPE encryption, not N copies: a random content key (CEK) encrypts the
finished HTML ONCE, then the CEK is separately encrypted for each group. A
wrapped CEK is ~100 bytes, so page weight is effectively independent of how
many groups can open it, and rotating one group's key rewraps 100 bytes
without touching the body or any other group.

The wrap list is SHUFFLED and carries no labels. Which desk can open a document
is itself information, and an ordered list would hand it over.

FOLDER INHERITANCE (2026-08-01)
**A gated `index.md` locks its whole subtree.** Every page beneath it inherits
the same `gates:` and is genuinely encrypted -- not merely hidden from the
sidebar.

    docs/safety/index.md          status: gated, gates: [psm]
    docs/safety/lockup.md         -> inherits: gated, gates: [psm]
    docs/safety/keys/master.md    -> inherits too, at any depth

WHY REAL ENCRYPTION AND NOT A HIDDEN SIDEBAR: hiding child entries until the
index unlocks leaves every child fully readable by direct URL and in search,
while *looking* protected. On a safety section that is the worst combination --
the appearance of a lock with none of it. Inheritance means the sidebar can
keep showing the children honestly, because they are actually locked.

The nearest gated ancestor wins. A page opts out or overrides by declaring its
own `status:` (any value, including `public`), or with `inherit: false`.

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
import posixpath
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
# site. Doing the substitution here is deterministic. The `\]\{` with no gap is
# what keeps ordinary markdown links `[text](url)` out of the match.
_SPAN = re.compile(r"\[([^\[\]\n]+)\]\{\s*\.([A-Za-z][\w-]*)\s*\}")

# Fenced code blocks, so a page documenting the marker still shows it literally.
_FENCE = re.compile(r"(^```.*?^```)", re.DOTALL | re.MULTILINE)

_status = {}      # src_uri -> resolved status
_keys = {}        # src_uri -> resolved list of passwords (gated pages only)
_nolist = set()
_inherited = set()  # src_uri -> gated by an ancestor rather than by itself
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


def _declared_status(meta):
    """The page's OWN status, or None if it did not declare one. Distinguishing
    'said nothing' from 'said hidden' is what makes inheritance possible."""
    raw = meta.get("status")
    if raw is None:
        return None
    status = str(raw).strip().lower()
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
            + ", but the build environment carries no "
            + ", ".join(_env_key(n) for n in missing)
            + ". Add it in Settings -> Secrets and variables -> Actions, AND "
            "name it in the env: block of .github/workflows/deploy.yml -- a "
            "secret that exists but is not passed through is invisible here. "
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


def _ancestors(src_uri):
    """Folder paths above this page, nearest first."""
    parts = posixpath.dirname(src_uri).split("/") if posixpath.dirname(src_uri) else []
    out = []
    while parts:
        out.append("/".join(parts))
        parts = parts[:-1]
    out.append("")
    return out


def _opted_out(meta):
    value = meta.get("inherit")
    return value is False or str(value).strip().lower() == "false"


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
        wraps.append({"s": _b64(salt), "n": _b64(wrap_nonce), "w": _b64(wrapped)})

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
    """Resolve status for every page, THEN drop what must not be built.

    Two passes, because inheritance cannot be decided while still walking: a
    folder's index.md may be read after one of its children.
    """
    for store in (_status, _keys):
        store.clear()
    _nolist.clear()
    _inherited.clear()
    _noindex_paths.clear()

    pages = []
    folder_gate = {}   # folder path -> (meta, src_uri of its index)

    for f in files:
        if not f.is_documentation_page():
            continue
        meta = _read_meta(f.abs_src_path)
        pages.append((f, meta))

        if posixpath.basename(f.src_uri) == "index.md":
            if _declared_status(meta) == "gated":
                folder_gate[posixpath.dirname(f.src_uri)] = (meta, f.src_uri)

    kept = []
    page_uris = {f.src_uri for f, _ in pages}

    for f in files:
        if not f.is_documentation_page():
            kept.append(f)

    for f, meta in pages:
        status = _declared_status(meta)
        source_meta = meta
        source_uri = f.src_uri

        # Inherit only when the page said nothing about its own status. A page
        # that declares anything -- even `public` -- has made a decision, and
        # silently overriding it would be worse than not inheriting at all.
        if status is None and not _opted_out(meta):
            for folder in _ancestors(f.src_uri):
                if folder in folder_gate and folder_gate[folder][1] != f.src_uri:
                    source_meta, source_uri = folder_gate[folder]
                    status = "gated"
                    _inherited.add(f.src_uri)
                    break

        if status is None:
            status = DEFAULT

        _status[f.src_uri] = status

        if status == "hidden":
            continue

        if status == "gated":
            # Raises here, before a single page renders, if a key is missing.
            _keys[f.src_uri] = _secrets_for(source_meta, source_uri)

        if _is_unlisted(meta, status):
            _nolist.add(f.src_uri)
            f.inclusion = InclusionLevel.NOT_IN_NAV

        kept.append(f)

    # Preserve the original file order; `kept` was built in two chunks.
    order = {f.src_uri: i for i, f in enumerate(files)}
    kept.sort(key=lambda f: order.get(f.src_uri, 0))

    return Files(kept)


def on_nav(nav, config, files):
    """Prune undiscoverable pages from the finished nav tree.

    Belt and braces: awesome-nav builds navigation from scratch rather than
    filtering what MkDocs generates, so it may not honour InclusionLevel.

    NOTE: inherited-gated children are deliberately LEFT in the sidebar. They
    are genuinely encrypted, so showing them is honest -- a reader sees the
    section exists and is asked for a password, which is the whole point of
    `gated` over `unlisted`.
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

    passwords = _keys[page.file.src_uri]
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
    """Tell crawlers to skip undiscoverable pages."""
    if page.file.src_uri not in _nolist:
        return output

    _noindex_paths.add(page.file.dest_uri.replace("\\", "/"))
    return output.replace("<head>", "<head>" + NOINDEX, 1)


def on_post_build(config):
    """Strip undiscoverable pages out of the generated sitemap (and its .gz)."""
    inherited = len(_inherited)
    if inherited:
        print("gate: " + str(inherited) + " page(s) locked by a parent index")

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
