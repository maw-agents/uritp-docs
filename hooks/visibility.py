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
many groups can open it. The wrap list is SHUFFLED and unlabelled: which desk
can open a document is itself information.

A LITERAL PER-PAGE PASSWORD IS SUPPORTED AND IS NOT A SECOND-CLASS PATH

    status: gated
    password: pmgate

One page, one password, visible in the frontmatter, no keystore round trip and
no repository secret to edit. It composes with `gates:` (both are collected and
any one opens the page), it inherits down a folder exactly like a group key
does, and gate.js remembers it on the session keyring like any other. The
literal is stripped from `page.meta` before render, so it never reaches the
HTML.

What it costs, stated plainly rather than discouraged: the password is in the
repository and in git history forever, so rotating it is a rewrite rather than
a secret edit, and it cannot be shared across pages without repeating it. That
is the correct trade for a fast local lock during beta and the wrong one for a
key that outlives the page. Use a group in the keystore the moment two pages
want the same password.

=======================================================================
WHERE A GROUP NAME FINDS ITS PASSWORD -- two tiers, and the name never
changes shape
=======================================================================

TIER 1, the container. ONE repository secret, URITP_GATE_KEYS, holding a
block of lines:

    # URITP docs gate keys. One group per line: name = password
    admin = ...
    dev   = ...
    psm   = ...

The key in that block is the EXACT string a page writes in `gates:`. No
uppercasing, no prefix, no transformation. `gates: [psm]` looks up `psm`.
Adding a group is adding a line to that secret's value -- no file in this
repository changes, and no name is chosen by anything but Michael.

TIER 2, the rotation hatch. A single group MAY instead live in its own
secret, URITP_GATE_<GROUP>, uppercased with hyphens as underscores.

    THIS EXISTS FOR EXACTLY ONE REASON and it is not "the other way to do
    it": rotating a key inside the container means repasting the WHOLE block
    from memory, because GitHub never shows you a secret's current value. For
    a high-churn key -- the one reissued to a new cohort every September --
    that risks the other nine every time it turns over. Its own secret makes
    that rotation atomic.

    A group in its own secret needs one line in deploy.yml, because GitHub
    only hands a workflow the secrets it names. That is the cost of the
    hatch and it is why the hatch is the exception, not the default.

PRECEDENCE: the container wins. A name present in both tiers resolves from
the container and the duplicate is reported -- silently preferring either one
would make a half-finished migration undetectable.

NOTE what disappeared with the old single-tier design: `_env_key()` for
container groups, the mandatory URITP_GATE_ prefix, the reserved-namespace
rule, and the URITP_GATE_STRICT collision that rule existed to prevent. The
derivation survives ONLY inside the hatch, where a real environment variable
name is unavoidable.

FOLDER INHERITANCE -- THE LOCK WINS
**A gated `index.md` locks its whole subtree, and the lock BEATS the page.**
Every page beneath it is genuinely encrypted -- not merely hidden from the
sidebar, which would leave every child readable by direct URL while looking
protected. The nearest gated ancestor wins at ANY depth, so this composes
through nested folders. Only a folder that HAS an index.md gates anything; a
folder without one is transparent and the walk continues straight past it,
which is what makes the index file itself the switch.

⚠️ PRECEDENCE FLIPPED 2026-08-01, Michael. It used to be the opposite: a page
that declared anything at all, even `public`, opted itself out, and "only
silence inherits" was the rule. The result was `docs/safety/safety-test-1.md`
serving plaintext by direct link while the Safety section looked locked. A lock
whose opt-out is spelled the same as an ordinary setting is not a lock. The
folder is now the unit of protection.

Three pass-throughs, and they are the only three:

    status: hidden      still wins. `hidden` means NOT BUILT, and a lock must
                        never PUBLISH a page whose author suppressed it.
                        Escalating somebody's half-written draft into a live
                        encrypted page is a worse failure than the one this
                        flip fixes.

    status: gated       keeps its OWN keys. The page is already locked, so the
                        folder lock has nothing to add -- and merging the two
                        keyrings would hand the folder's group a page that was
                        deliberately locked to a different one. Widening access
                        is not inheritance.

    inherit: false      the explicit, greppable escape hatch. One string to
                        search for when you want to know what is loose inside a
                        locked tree.

An overridden page KEEPS ITS OWN UNLISTED-NESS. A page that chose `unlisted`,
or set `listed: false`, stays out of the nav, the search index and the sitemap
after the lock takes it -- otherwise locking a folder would quietly promote its
most invisible page into the sidebar, which is an escalation dressed as a
security fix.

Every override is REPORTED BY NAME at the end of the build. A silent override
would just relocate the invisible failure this flip exists to remove.

A MISSING KEY LOCKS THE PAGE, IT DOES NOT FREEZE THE SITE
A gated page naming a group with no password behind it publishes as an
unopenable notice: the content is DROPPED (not encrypted, not shipped), the
page says so plainly, the build reports it loudly, and everything else
deploys. Failing the whole build here took the entire site stale over one
page's missing config on 2026-08-01 -- the same trade `--strict` used to make
over a single dead link, rejected for the same reason. The failure must be
local and visible, not global and silent. URITP_GATES_STRICT=1 restores
hard-fail.

🔒 NEVER PRINT A PASSWORD, ONLY A GROUP NAME. Names are already public in page
frontmatter. Values are not, and GitHub's log masking is a literal string
match that is NOT known to survive splitting a multi-line secret into lines --
unverified as of 2026-08-01, so this file simply never emits one.

NONE of this is access control while the repository is public. The markdown
source of every page, INCLUDING a gated page's plaintext, is readable at
github.com by anyone. The keystore keeps PASSWORDS out of the repo; it does
not keep CONTENT out. See AUTHORING.md -> "What the gate actually does".

📋 The readable copy of the keys lives in the ClickUp Accounts task, linked
from AUTHORING.md -> Adding a key group. A secret cannot be read back, so
that task is the master and this build is the copy.

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

CONTAINER = "URITP_GATE_KEYS"
ENV_PREFIX = "URITP_GATE_"      # tier 2 only: the rotation hatch

# A page that declares one of these is NOT taken over by a parent folder lock.
# See FOLDER INHERITANCE at the top of this file -- each one is a pass-through
# for a different reason, and neither of them leaves a page readable.
LOCK_EXEMPT = {"hidden", "gated"}

# NOT URITP_GATE_STRICT -- that name would read as a hatch group called
# "strict" whose password is "1". Flags are plural, keys are singular.
STRICT = os.environ.get("URITP_GATES_STRICT") == "1"

NOINDEX = '<meta name="robots" content="noindex, nofollow">'

_FRONTMATTER = re.compile(rb"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
_SPAN = re.compile(r"\[([^\[\]\n]+)\]\{\s*\.([A-Za-z][\w-]*)\s*\}")
_FENCE = re.compile(r"(^```.*?^```)", re.DOTALL | re.MULTILINE)

_keystore = {}      # group name -> password
_store_notes = []   # parse warnings, safe to print (names only)
_status = {}
_keys = {}
_unconfigured = {}
_overridden = {}    # src_uri -> (status it declared, the index that took it)
_nolist = set()
_inherited = set()
_noindex_paths = set()


def _load_keystore():
    """Parse URITP_GATE_KEYS once per build.

    Every rule below is a real failure mode raised in review, not defensive
    habit -- each one is silent and each one produces a working site with one
    broken group, which is worse than a loud failure.
    """
    _keystore.clear()
    del _store_notes[:]

    raw = os.environ.get(CONTAINER, "")
    if not raw.strip():
        return

    for number, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        # `#` is a comment ONLY at the start of a line. Mid-line it is an
        # ordinary password character and must survive.
        if line.startswith("#"):
            continue
        if "=" not in line:
            _store_notes.append("line " + str(number) + " has no '=', skipped")
            continue

        # Split on the FIRST '=' only: a password may legitimately contain one.
        name, _, value = line.partition("=")
        name = name.strip().lower()
        # Trailing spaces are invisible in the GitHub secret box and would
        # break every unlock with no error anywhere.
        value = value.strip()

        if not name:
            _store_notes.append("line " + str(number) + " has no name, skipped")
            continue
        if not value:
            _store_notes.append("group '" + name + "' has an empty password, skipped")
            continue
        if name in _keystore:
            # FIRST wins, and say so. Last-wins would be silent.
            _store_notes.append(
                "group '" + name + "' appears twice; the first one is used"
            )
            continue

        _keystore[name] = value


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
    return [str(n).strip().lower() for n in names if str(n).strip()]


def _hatch_var(name):
    """Tier 2 only. psm -> URITP_GATE_PSM."""
    return ENV_PREFIX + name.upper().replace("-", "_")


def _password_for(name):
    """Container first, then the rotation hatch. Returns (password, note)."""
    inside = _keystore.get(name)
    outside = os.environ.get(_hatch_var(name))

    if inside and outside:
        return inside, (
            "group '" + name + "' is in both " + CONTAINER + " and "
            + _hatch_var(name) + "; the container wins -- remove one"
        )
    if inside:
        return inside, None
    if outside:
        return outside, None
    return None, None


def _available():
    """Every group the build can satisfy, from both tiers. NAMES ONLY -- these
    are already written in page frontmatter and are not secret."""
    found = set(_keystore)
    for key, value in os.environ.items():
        if key.startswith(ENV_PREFIX) and value and key != CONTAINER:
            found.add(key[len(ENV_PREFIX):].lower())
    return sorted(found)


def _resolve_keys(meta, src_uri):
    """Return (passwords, problems). Never raises unless URITP_GATES_STRICT=1.

    `problems` non-empty means this page cannot be published at all: it is
    rendered as an unopenable notice rather than encrypted, and reported.
    """
    found = []
    missing = []

    # The per-page literal. Deliberately first and deliberately equal: a page
    # may carry a literal AND groups, and any one of them opens it.
    literal = meta.get("password")
    if literal:
        found.append(str(literal))

    for name in _gate_names(meta):
        password, note = _password_for(name)
        if note and note not in _store_notes:
            _store_notes.append(note)
        if password:
            found.append(password)
        else:
            missing.append(name)

    problems = []
    if missing:
        have = _available()
        detail = "no password for group(s): " + ", ".join(missing)
        detail += (
            "; groups available right now: " + ", ".join(have)
            if have else "; the keystore is empty -- is " + CONTAINER + " set?"
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
    """Load the keystore, resolve status for every page, THEN drop what must
    not be built.

    Two passes over the pages, because inheritance cannot be decided while
    still walking: a folder's index.md may be read after one of its children.
    """
    _load_keystore()

    for store in (_status, _keys, _unconfigured, _overridden):
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
        declared = _declared_status(meta)

        # Captured BEFORE any override. A page the lock takes over keeps the
        # discoverability it chose for itself; locking a folder must not
        # promote its quietest page into the sidebar.
        unlisted = _is_unlisted(meta, declared)

        status = declared
        source_meta, source_uri = meta, f.src_uri

        # THE LOCK BEATS THE PAGE. Only LOCK_EXEMPT statuses and an explicit
        # `inherit: false` walk past a gated ancestor -- see FOLDER
        # INHERITANCE at the top of this file for why each one is safe.
        if declared not in LOCK_EXEMPT and not _opted_out(meta):
            for folder in _ancestors(f.src_uri):
                if folder in folder_gate and folder_gate[folder][1] != f.src_uri:
                    source_meta, source_uri = folder_gate[folder]
                    if declared is not None:
                        # It said something and the lock overruled it. That is
                        # the whole class of change this flip introduced, so it
                        # never happens quietly.
                        _overridden[f.src_uri] = (declared, source_uri)
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

        if unlisted:
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


def _write_summary(lines):
    """Append a block to the Actions run summary, if we are in one."""
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return
    with open(summary, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _report_overrides():
    """Pages whose own `status:` was overruled by a parent folder lock.

    NOT a warning and NOT a problem -- it is the feature working. But the flip
    that introduced it traded one invisible behaviour for another, and the only
    thing that makes the trade honest is saying out loud which pages changed
    meaning.
    """
    if not _overridden:
        return

    print(
        "gate: " + str(len(_overridden))
        + " page(s) OVERRIDDEN by a parent index lock:"
    )
    for src, (declared, source) in sorted(_overridden.items()):
        print(
            "  " + src + " -- declared '" + declared + "', locked by " + source
        )

    lines = [
        "### \U0001f512 Locked by a parent index",
        "",
        "These pages declared their own `status:` and a gated folder index "
        "overruled it. This is the folder lock doing its job. To let one out, "
        "add `inherit: false` to its frontmatter.",
        "",
        "| Page | It declared | Locked by |",
        "|---|---|---|",
    ]
    for src, (declared, source) in sorted(_overridden.items()):
        lines.append(
            "| `" + src + "` | `" + declared + "` | `" + source + "` |"
        )
    _write_summary(lines)


def _report():
    """Loud, because the whole point of not failing the build is that the
    problem must not become invisible instead.

    🔒 Group NAMES only. Never a password, never a length, never a fragment.
    """
    have = _available()
    print("gate: " + str(len(have)) + " group(s) loaded -- "
          + (", ".join(have) if have else "NONE"))

    for note in _store_notes:
        print("::warning::gate keystore: " + note)

    if _inherited:
        print("gate: " + str(len(_inherited)) + " page(s) locked by a parent index")

    _report_overrides()

    if not _unconfigured:
        return

    print(
        "gate: " + str(len(_unconfigured))
        + " page(s) UNAVAILABLE, key not configured:"
    )
    for src, problems in sorted(_unconfigured.items()):
        print("  " + src + " -- " + "; ".join(problems))

    # Distinguish "no keystore at all" from "keystore present but this group
    # is not in it" -- identical symptoms, completely different fixes.
    if not have:
        cause = (
            "**No gate keys reached this build at all.** Either the "
            "`" + CONTAINER + "` secret does not exist, or it is empty, or "
            "everything in it failed to parse (see any keystore warnings "
            "above)."
        )
    else:
        cause = (
            "The keystore loaded **" + str(len(have)) + " group(s)** ("
            + ", ".join(have) + "), but the page(s) below name something else. "
            "Check the spelling in `gates:` against that list."
        )

    lines = [
        "### \u26a0\ufe0f Gate keys not configured",
        "",
        cause,
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
        "Add the group to the `" + CONTAINER + "` secret as a "
        "`name = password` line (**Settings -> Secrets and variables -> "
        "Actions**). The readable copy of that block lives in the ClickUp "
        "Accounts task -- update it there first, then paste. "
        "See AUTHORING.md -> Adding a key group.",
    ]
    _write_summary(lines)


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
