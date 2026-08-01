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

MULTIPLE KEYS
A gated page may name several groups, and ANY ONE of their passwords opens it:

    status: gated
    gates: [psm, admin]

ENVELOPE encryption, not N copies: a random content key (CEK) encrypts the
finished HTML ONCE, then the CEK is separately encrypted for each group. A
wrapped CEK is ~100 bytes, so page weight is effectively independent of how
many groups can open it, and rotating one group's key rewraps 100 bytes
without touching the body or any other group. The wrap list is SHUFFLED and
unlabelled: which desk can open a document is itself information.

HOW A GROUP NAME FINDS ITS KEY -- four names, all the same string

    page frontmatter        gates: [psm]
    this hook derives       URITP_GATE_ + PSM   (upper, hyphens -> underscores)
    reads                   os.environ["URITP_GATE_PSM"]
    put there by            deploy.yml: URITP_GATE_PSM: ${{ secrets.<same> }}
    whose value is          the repository secret URITP_GATE_PSM

The hook's half is a DERIVATION, not a lookup: `_env_key()` is three string
operations and consults no table. The prefix is load-bearing -- without it
every environment variable would be a candidate password, including PATH.

~~The workflow discovers keys by this prefix (see deploy.yml -> Collect gate
keys) rather than naming them.~~ **FALSE as of 2026-08-01, and it was false
the moment the revert landed.** That step existed for about four minutes.
Prefix discovery needed `${{ toJSON(secrets) }}`, whose first run came back
`action_required` with zero jobs and never deployed. deploy.yml now carries an
explicit list of PRE-WIRED slots: names are plumbed through whether or not
their secret exists, since an unset secret is an empty string and empty values
are ignored here. A group named outside that list needs one line added there.

FOLDER INHERITANCE
**A gated `index.md` locks its whole subtree.** Every page beneath it inherits
the same keys and is genuinely encrypted -- not merely hidden from the sidebar,
which would leave every child readable by direct URL while looking protected.
The nearest gated ancestor wins; a page overrides by declaring its own
`status:` (any value) or `inherit: false`. Only silence inherits.

A MISSING KEY LOCKS THE PAGE, IT DOES NOT FREEZE THE SITE
A gated page naming a group with no secret behind it publishes as an
unopenable notice: the content is DROPPED (not encrypted, not shipped), the
page says so plainly, the build reports it loudly, and everything else
deploys. Failing the whole build here took the entire site stale over one
page's missing config on 2026-08-01 -- the same trade `--strict` used to make
over a single dead link, rejected for the same reason. The failure must be
local and visible, not global and silent. URITP_GATES_STRICT=1 restores
hard-fail.

NONE of these are access control while the repository is public. The markdown
source of every page, INCLUDING a gated page's plaintext, is readable at
github.com by anyone. Secrets keep the PASSWORD out of the repo; they do not
keep the CONTENT out. See AUTHORING.md -> "What the gate actually does".

Wired in mkdocs.yml under `hooks:`. Documented in AUTHORING.md. Its browser
half is docs/javascripts/gate.js: the two share the cipher, the KDF and the
iteration count, so they change in the SAME PR or every gated page fails to
unlock with no error anyone can read.
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

# NOT URITP_GATE_STRICT. This hook treats every URITP_GATE_* variable as a
# password group, so that name would register a gate called "strict" whose
# password is "1". A control flag inside the namespace it controls is a
# collision waiting to happen; keep flags on URITP_GATES_* (plural) and keys on
# URITP_GATE_* (singular).
STRICT = os.environ.get("URITP_GATES_STRICT") == "1"

NOINDEX = '<meta name="robots" content="noindex, nofollow">'

_FRONTMATTER = re.compile(rb"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
_SPAN = re.compile(r"\[([^\[\]\n]+)\]\{\s*\.([A-Za-z][\w-]*)\s*\}")
_FENCE = re.compile(r"(^```.*?^```)", re.DOTALL | re.MULTILINE)

_status = {}        # src_uri -> resolved status
_keys = {}          # src_uri -> passwords that open it
_unconfigured = {}  # src_uri -> gate names with no secret behind them
_nolist = set()
_inherited = set()
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
    if status == "unlisted":
        return True
    listed = meta.get("listed")
    return listed is False or str(listed).strip().lower() == "false"


def _gate_names(meta):
    """`gates: [psm, admin]`, or the singular `gate: psm`."""
    names = meta.get("gates")
    if names is None:
        names = meta.get("gate")
    if names is None:
        return []
    if isinstance(names, str):
        names = [names]
    return [str(n).strip() for n in names if str(n).strip()]


def _env_key(name):
    """psm -> URITP_GATE_PSM. Three string operations, no table."""
    return ENV_PREFIX + name.upper().replace("-", "_")


def _available():
    """Group names the build environment can actually satisfy, lowercased back
    into the form a page would write. Used only to make the error message
    useful -- a NAME is not a secret, it is written in frontmatter."""
    found = []
    for key, value in os.environ.items():
        if key.startswith(ENV_PREFIX) and value:
            found.append(key[len(ENV_PREFIX):].lower())
    return sorted(found)


def _resolve_keys(meta, src_uri):
    """Return (passwords, problems). Never raises unless URITP_GATES_STRICT=1.

    `problems` non-empty means this page cannot be published at all: it is
    rendered as an unopenable notice rather than encrypted, and reported.
    """
    found = []
    missing = []

    literal = meta.get("password")
    if literal:
        found.append(str(literal))

    for name in _gate_names(meta):
        secret = os.environ.get(_env_key(name))
        if secret:
            found.append(secret)
        else:
            missing.append(name)

    problems = []
    if missing:
        have = _available()
        detail = (
            "no secret named "
            + ", ".join(_env_key(n) for n in missing)
            + " reached the build"
        )
        detail += (
            "; groups available right now: " + ", ".join(have)
            if have else "; no gate keys reached the build at all"
        )
        problems.append(detail)

    if not found and not problems:
        problems.append(
            "status is 'gated' but no `gates:` and no `password:` was given"
        )

    if problems and STRICT:
        raise ValueError(src_uri + ": " + "; ".join(problems))

    # Two groups sharing one password would ship two wraps that both open,
    # which leaks that they are the same secret.
    seen = set()
    unique = []
    for value in found:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique, problems


def _ancestors(src_uri):
    """Folder paths above this page, nearest first."""
    parent = posixpath.dirname(src_uri)
    parts = parent.split("/") if parent else []
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

    random.SystemRandom().shuffle(wraps)
    return _b64(nonce), _b64(body), wraps


def _keys_attr(wraps):
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
    for store in (_status, _keys, _unconfigured):
        store.clear()
    _nolist.clear()
    _inherited.clear()
    _noindex_paths.clear()

    pages = []
    folder_gate = {}

    for f in files:
        if not f.is_documentation_page():
            continue
        meta = _read_meta(f.abs_src_path)
        pages.append((f, meta))
        if posixpath.basename(f.src_uri) == "index.md":
            if _declared_status(meta) == "gated":
                folder_gate[posixpath.dirname(f.src_uri)] = (meta, f.src_uri)

    kept = []

    for f in files:
        if not f.is_documentation_page():
            kept.append(f)

    for f, meta in pages:
        status = _declared_status(meta)
        source_meta, source_uri = meta, f.src_uri

        # Inherit only when the page said nothing about its own status. A page
        # that declares anything -- even `public` -- has made a decision.
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
            passwords, problems = _resolve_keys(source_meta, source_uri)
            if problems:
                _unconfigured[f.src_uri] = problems
            else:
                _keys[f.src_uri] = passwords

        if _is_unlisted(meta, status):
            _nolist.add(f.src_uri)
            f.inclusion = InclusionLevel.NOT_IN_NAV

        kept.append(f)

    order = {f.src_uri: i for i, f in enumerate(files)}
    kept.sort(key=lambda f: order.get(f.src_uri, 0))

    return Files(kept)


def on_nav(nav, config, files):
    """Prune undiscoverable pages from the finished nav tree.

    Belt and braces: awesome-nav builds navigation from scratch rather than
    filtering what MkDocs generates, so it may not honour InclusionLevel.

    Inherited-gated children are deliberately LEFT in the sidebar: they are
    genuinely encrypted, so showing them is honest.
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
        hide = page.meta.get("hide") or []
        page.meta["hide"] = sorted(set(list(hide) + ["toc"]))

    return _expand_spans(markdown)


def _notice(problems):
    """A page whose key is not configured. The content is DROPPED, not
    encrypted and not published: there is no key to open it with, so shipping
    ciphertext nobody can decrypt would only be confusing."""
    return (
        '<div class="gate">'
        '<p class="gate__label">Unavailable</p>'
        '<p class="gate__note">This page is restricted and its key has not been '
        'set up yet, so it cannot be opened by anyone. Nothing is missing from '
        'the page itself. Ask production management, or see AUTHORING.md '
        '&rarr; Adding a key group.</p>'
        '<p class="gate__error">' + "; ".join(problems) + '</p>'
        '</div>'
    )


def on_page_content(html, page, config, files):
    """Replace a gated page's rendered body with ciphertext plus an unlock form.

    Runs AFTER markdown rendering, so what gets encrypted is the finished HTML.
    Material builds its search index from this same content, which means the
    index picks up the unlock form and never the real text.
    """
    src = page.file.src_uri

    if src in _unconfigured:
        page.meta.pop("password", None)
        return _notice(_unconfigured[src])

    if _status.get(src) != "gated":
        return html

    nonce, ciphertext, wraps = _encrypt(html, _keys[src])
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


def _report():
    """Loud, because the whole point of not failing the build is that the
    problem must not become invisible instead."""
    have = _available()
    print("gate: keys available -- " + (", ".join(have) if have else "none"))

    if _inherited:
        print("gate: " + str(len(_inherited)) + " page(s) locked by a parent index")

    if not _unconfigured:
        return

    print(
        "gate: " + str(len(_unconfigured))
        + " page(s) UNAVAILABLE, key not configured:"
    )
    for src, problems in sorted(_unconfigured.items()):
        print("  " + src + " -- " + "; ".join(problems))

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return

    lines = [
        "### \u26a0\ufe0f Gate keys not configured",
        "",
        "These pages published as an unopenable notice. Their content was NOT "
        "shipped, and the rest of the site deployed normally.",
        "",
        "| Page | Problem |",
        "|---|---|",
    ]
    for src, problems in sorted(_unconfigured.items()):
        lines.append("| `" + src + "` | " + "; ".join(problems) + " |")
    lines += [
        "",
        "Add a repository secret named `" + ENV_PREFIX + "<GROUP>` in "
        "**Settings -> Secrets and variables -> Actions**. If the group name is "
        "not one of the pre-wired slots in `.github/workflows/deploy.yml`, add "
        "a line there too. See AUTHORING.md -> Adding a key group.",
    ]
    with open(summary, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def on_post_build(config):
    """Report, then strip undiscoverable pages out of the sitemap."""
    _report()

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
