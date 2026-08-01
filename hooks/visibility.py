"""
Page visibility. Reads `status:` from frontmatter and decides what publishes.

    status: public      listed in the sidebar, indexed, plaintext
    status: gated       listed, body AES-encrypted, needs a password
    status: unlisted    direct link only: no nav, no search, no search engines
    status: hidden      never built                          (DEFAULT)

    listed: false       an INDEPENDENT switch: out of the nav, search and
                        sitemap WHATEVER the status is. The four statuses
                        conflated two questions (is it published / can it be
                        found); this separates them. `unlisted` is the
                        shorthand for public + not-listed.

⚠️ `hidden` IS NOT ACCESS CONTROL, IT IS NOT-PUBLISHED. This repository is
public, so the markdown source of every page -- including a `hidden` page and a
`gated` page's plaintext -- is readable at github.com by anyone. `hidden` keeps
a page off the SITE. It is the strongest thing this file can do and it is still
not a permission.

📋 AUTHORING REFERENCE: AUTHORING-GATES.md. Deliberately not repeated here --
it is read by whoever writes a page, this file is read by whoever changes the
machine, and one document serving both is how both go stale.

=======================================================================
FOUR FILES, ONE HOOK
=======================================================================

    hooks/visibility.py      THIS FILE. MkDocs events, the status decision,
                             the folder waterfall, and ALL build state.
    hooks/gate/keystore.py   group name -> password. Two tiers.
    hooks/gate/envelope.py   AES-GCM + PBKDF2 + the unlock markup.
                             ⚠️ PAIRED WITH docs/javascripts/gate.js.
    hooks/gate/report.py     every warning and run-summary table.

Split 2026-08-01 at 33.8KB, past the ~30KB an agent can fetch whole: a file
that cannot be read before it is edited cannot be edited safely, and this is
the file where a silent mistake is most expensive.

🔴 THE LIBRARIES ARE NOT HOOKS AND MUST NEVER BE REGISTERED. The hook order in
mkdocs.yml is load-bearing -- this file drops `hidden` pages BEFORE links.py
builds its id registry. One feature, one slot in that order. gate/__init__.py
has the full rule, including why every name over there is public not private.

ALL MUTABLE BUILD STATE LIVES HERE. The modules in gate/ are pure.

=======================================================================
NOTHING FAILS SILENTLY, AND NOTHING FAILS THE BUILD
=======================================================================

An unrecognised `status:` falls through to `hidden` -- guessing what someone
meant is worse than not publishing -- but it used to do that WITHOUT SAYING SO.
`status: publi` and the page vanished, green build, no signal. That is worse
than a broken build: a build that breaks screams, a page that quietly stops
existing does not, and this site's promise is "assume the PDF is stale, check
here instead." Four things are now reported BY NAME every build and none of
them fail it: an unrecognised status, pages hidden only by default, a
`password:` holding a list, and groups/pages that do not match up.

🔴 `password:` WITH A LIST IS THE ONE THAT COST US. Frontmatter takes either

    password: rehearsal26        ONE literal value, this page only
    gates: [psm, admin]          NAMES of keystore groups, any one opens it

and `password: [dev, admin, pm]` looks like the second while being the first.
It used to be str()'d, so the page's real password became the characters of a
Python list repr -- which no human would type -- and NOTHING WARNED, because a
password had technically been supplied. Encrypted correctly, reported clean,
openable by nobody, and it takes the whole subtree with it under the waterfall.
Now it lands in the unconfigured path: content dropped, page says it is
unavailable, build names it.

⚠️ It does NOT fail the build, deliberately. Failing here took the site stale
over one page's config on 2026-08-01 -- the same trade `--strict` used to make,
rejected for the same reason and removed from deploy.yml the same day. Local
and visible beats global and silent. URITP_GATES_STRICT=1 restores hard-fail.

=======================================================================
THE FOLDER WATERFALL  (precedence FLIPPED 2026-08-01, Michael)
=======================================================================

**A gated `index.md` locks its whole subtree, at any depth, and it BEATS what
the child declared.** Dropping an index.md in IS the switch. Every page beneath
a locked index is genuinely encrypted, not merely hidden from the sidebar --
which would leave every child readable by direct URL while looking protected.

    docs/safety/index.md         status: gated   <- the switch
    docs/safety/test.md          status: public  <- LOCKED ANYWAY, and reported
    docs/safety/keys/master.md   (silent)        <- locked, at any depth

~~A page overrides by declaring its own `status:` (any value).~~ REVERSED on
the day it shipped: it meant `status: public` on one child quietly punched a
hole in a locked safety section, and the page that did it looked normal.

Two things it deliberately CANNOT do: it cannot publish a `hidden` page (a rule
whose job is to RAISE protection must never be why something reached a reader),
and it cannot be silent (`inherit: false` is the one escape hatch, one greppable
line, and every overruled page is named at build time).

⚠️ THERE IS A SECOND WATERFALL AND IT RUNS THE OTHER WAY. hooks/theme.py's SKIN
waterfall is child-wins; this LOCK waterfall is parent-wins. Precedence follows
CONSEQUENCE, not symmetry: a skin is a preference, a lock is not. Both fire off
index.md and walk the same ancestors, so merging them will look like tidying.
That is the day a locked page publishes. Do not.

KEYS UNDER THE WATERFALL: a locked child KEEPS its own `password:`/`gates:` and
GAINS the parent's. Any one opens the page, which the envelope already
supported, so a one-page password stays a one-line thing to add and delete
without disturbing the folder key.

A MISSING KEY LOCKS THE PAGE, IT DOES NOT FREEZE THE SITE: content DROPPED,
page says so, build reports it, everything else deploys.

Wired in mkdocs.yml under `hooks:`.
"""

import gzip
import os
import posixpath
import re
import sys

import yaml
from mkdocs.structure.files import Files, InclusionLevel

# MkDocs loads a hook as a standalone module, not as part of a package, so a
# relative import does not work. Same bootstrap hooks/contrast.py uses.
_HOOKS = os.path.dirname(os.path.abspath(__file__))
if _HOOKS not in sys.path:
    sys.path.insert(0, _HOOKS)

from gate import envelope, keystore, report      # noqa: E402  (path set above)

DEFAULT = "hidden"
ALLOWED = {"public", "gated", "unlisted", "hidden"}

# The key links.py reads off the config to learn what this hook refused to
# build. Underscored because it is not MkDocs configuration, it is a handoff.
HANDOFF = "_uritp_hidden"

# NOT URITP_GATE_STRICT -- that name would read as a hatch group called
# "strict" whose password is "1". Flags are plural, keys are singular.
STRICT = os.environ.get("URITP_GATES_STRICT") == "1"

NOINDEX = '<meta name="robots" content="noindex, nofollow">'

_FRONTMATTER = re.compile(rb"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
_SPAN = re.compile(r"\[([^\[\]\n]+)\]\{\s*\.([A-Za-z][\w-]*)\s*\}")
_FENCE = re.compile(r"(^```.*?^```)", re.DOTALL | re.MULTILINE)

_store = None       # the Keystore for this build. Loaded in on_files.
_store_notes = []   # parse + resolution warnings. NAMES ONLY, safe to print.
_status = {}
_keys = {}
_unconfigured = {}
_overridden = {}    # src_uri -> (status it declared, the index that overruled)
_nolist = set()
_inherited = set()
_noindex_paths = set()
_unknown = {}       # src_uri -> the unrecognised status, exactly as written
_defaulted = set()  # src_uri -> no `status:` key at all
_hidden = {}        # src_uri -> declared `id:` or None. Handed to links.py.
_named_groups = {}  # group name -> set of pages that asked for it


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


def _declared_status(meta, src_uri=None):
    """The page's OWN status, or None if it did not declare one.

    Distinguishing 'said nothing' from 'said hidden' is what makes the
    waterfall safe: silence inherits, `hidden` is never overruled.

    Pass `src_uri` to RECORD what happened. Optional because this runs twice
    over index.md files -- once in the folder-gate pre-pass, once in the main
    walk -- and a page must not be reported twice. The main walk passes it.
    """
    raw = meta.get("status")
    if raw is None:
        if src_uri is not None:
            _defaulted.add(src_uri)
        return None
    status = str(raw).strip().lower()
    if status in ALLOWED:
        return status
    if src_uri is not None:
        _unknown[src_uri] = str(raw)
    return DEFAULT


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


def _has_own_keys(meta):
    """Did this page bring key material of its own to the party?"""
    return meta.get("password") is not None or bool(_gate_names(meta))


def _literal_password(meta, problems):
    """The page's own `password:`, or None.

    🔴 A LIST HERE IS ALWAYS A MISTAKE and it used to be a silent one -- see
    the module docstring. Refused by name now rather than str()'d into a
    password nobody could type.
    """
    literal = meta.get("password")
    if literal is None:
        return None
    if isinstance(literal, (list, tuple, set, dict)):
        problems.append(
            "`password:` was given a list, but it takes ONE literal value. A "
            "list of GROUP NAMES belongs in `gates:` -- change `password: "
            "[...]` to `gates: [...]` and the names resolve against the "
            + keystore.CONTAINER + " keystore"
        )
        return None
    return str(literal)


def _resolve_keys(metas, src_uri):
    """Return (passwords, problems) for a LIST of key sources, nearest first.

    More than one source is the normal case under the waterfall: a locked child
    contributes its own password and the locking index contributes the folder
    key, and either opens the page. Never raises unless URITP_GATES_STRICT=1.

    `problems` non-empty means the page cannot be published at all: it renders
    as an unopenable notice rather than ciphertext, and is reported.
    """
    found = []
    missing = []
    problems = []

    for meta in metas:
        literal = _literal_password(meta, problems)
        if literal:
            found.append(literal)

        for name in _gate_names(meta):
            _named_groups.setdefault(name, set()).add(src_uri)
            password, note = _store.password_for(name)
            if note and note not in _store_notes:
                _store_notes.append(note)
            if password:
                found.append(password)
            elif name not in missing:
                missing.append(name)

    if missing:
        have = _store.available()
        detail = "no password for group(s): " + ", ".join(missing)
        detail += (
            "; groups available right now: " + ", ".join(have)
            if have else
            "; the keystore is empty -- is " + keystore.CONTAINER + " set?"
        )
        problems.append(detail)

    if not found and not problems:
        problems.append(
            "status is 'gated' but no `gates:` and no `password:` was given"
        )

    if problems and STRICT:
        raise ValueError(src_uri + ": " + "; ".join(problems))

    # Two groups sharing one password would ship two wraps that both open,
    # which leaks that they are the same secret. Deduping also means a child
    # repeating its parent's password costs nothing.
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
    """`[To be confirmed]{.tbc}` -> a real span.

    ⚠️ THIS DOES NOT BELONG IN A VISIBILITY HOOK and it may not need to exist.
    It is a markdown transform with no relationship to publishing, gating or
    encryption -- a second thing that moved into this file, which is half of
    why the file got too big to read.

    AND IT MAY BE REDUNDANT: `attr_list` is enabled in mkdocs.yml and the
    comment beside it credits that extension with exactly this syntax.
    attr_list natively supports `[text]{.class}`. So either this is dead code
    or that comment is wrong -- two claimants on one behaviour, one of them
    lying. UNMEASURED as of 2026-08-01, deliberately: settle it by deleting
    this on a branch and looking at a rendered `.tbc`, not by reasoning, and
    not folded into an unrelated PR.
    """
    parts = _FENCE.split(markdown)
    for i, part in enumerate(parts):
        if part.startswith("```"):
            continue
        parts[i] = _SPAN.sub(r'<span class="\2">\1</span>', part)
    return "".join(parts)


def on_files(files, config):
    """Load the keystore, resolve status for every page, THEN drop what must
    not be built.

    Two passes over the pages, because the waterfall cannot be decided while
    still walking: a folder's index.md may be read after one of its children.
    """
    global _store
    _store = keystore.load()

    for store in (
        _status, _keys, _unconfigured, _overridden, _unknown, _hidden,
        _named_groups,
    ):
        store.clear()
    _nolist.clear()
    _inherited.clear()
    _noindex_paths.clear()
    _defaulted.clear()
    del _store_notes[:]
    _store_notes.extend(_store.notes)

    pages = []
    folder_gate = {}

    for f in files:
        if not f.is_documentation_page():
            continue
        meta = _read_meta(f.abs_src_path)
        pages.append((f, meta))
        if posixpath.basename(f.src_uri) == "index.md":
            # No src_uri: this is the pre-pass, and the main walk below reports
            # this same file. Passing it here would double-count.
            if _declared_status(meta) == "gated":
                folder_gate[posixpath.dirname(f.src_uri)] = (meta, f.src_uri)

    kept = []

    for f in files:
        if not f.is_documentation_page():
            kept.append(f)

    for f, meta in pages:
        declared = _declared_status(meta, f.src_uri)
        status = declared
        source_uri = f.src_uri

        # A page's own key material always counts, even when a parent locks it.
        # That is what keeps a one-page local password a one-line thing.
        key_metas = [meta] if _has_own_keys(meta) else []

        # THE WATERFALL. The nearest gated index.md wins over whatever this page
        # declared -- see the module docstring for why that precedence flipped.
        # `hidden` is the one status it may not overrule.
        if declared != "hidden" and not _opted_out(meta):
            for folder in _ancestors(f.src_uri):
                if folder in folder_gate and folder_gate[folder][1] != f.src_uri:
                    parent_meta, parent_uri = folder_gate[folder]
                    if declared is not None and declared != "gated":
                        _overridden[f.src_uri] = (declared, parent_uri)
                    key_metas.append(parent_meta)
                    source_uri = parent_uri
                    status = "gated"
                    _inherited.add(f.src_uri)
                    break

        if status is None:
            status = DEFAULT

        _status[f.src_uri] = status

        if status == "hidden":
            # Remembered, with its id, so links.py can tell a deliberate hide
            # apart from a typo in a link. A hidden page never reaches links.py
            # any other way: it is dropped from the file list two lines below.
            declared_id = meta.get("id")
            _hidden[f.src_uri] = str(declared_id).strip() if declared_id else None
            continue

        if status == "gated":
            passwords, problems = _resolve_keys(key_metas or [meta], source_uri)
            if problems:
                _unconfigured[f.src_uri] = problems
            else:
                _keys[f.src_uri] = passwords

        # Listing is judged on what the page ITSELF said. Being locked by a
        # parent must not quietly drag an `unlisted` page back into the nav.
        if _is_unlisted(meta, declared or status):
            _nolist.add(f.src_uri)
            f.inclusion = InclusionLevel.NOT_IN_NAV

        kept.append(f)

    # The handoff to links.py. A plain dict on the config, not an import: unwire
    # this hook and links.py reads nothing and behaves exactly as it did before.
    config[HANDOFF] = dict(_hidden)

    order = {f.src_uri: i for i, f in enumerate(files)}
    kept.sort(key=lambda f: order.get(f.src_uri, 0))

    return Files(kept)


def on_nav(nav, config, files):
    """Prune undiscoverable pages from the finished nav tree.

    Belt and braces: awesome-nav builds navigation from scratch rather than
    filtering what MkDocs generates, so it may not honour InclusionLevel.

    Pages locked by a parent index are deliberately LEFT in the sidebar: they
    are genuinely encrypted, so showing them is honest.
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


def on_page_content(html, page, config, files):
    """Replace a gated page's rendered body with ciphertext plus an unlock form.

    Runs AFTER markdown rendering, so what gets encrypted is the finished HTML.
    Material builds its search index from this same content, which means the
    index picks up the unlock form and never the real text.
    """
    src = page.file.src_uri

    if src in _unconfigured:
        page.meta.pop("password", None)
        return envelope.notice(_unconfigured[src])

    if _status.get(src) != "gated":
        return html

    nonce, ciphertext, wraps = envelope.encrypt(html, _keys[src])
    page.meta.pop("password", None)
    return envelope.form(nonce, ciphertext, wraps)


def on_post_page(output, page, config):
    """Tell crawlers to skip undiscoverable pages."""
    if page.file.src_uri not in _nolist:
        return output
    _noindex_paths.add(page.file.dest_uri.replace("\\", "/"))
    return output.replace("<head>", "<head>" + NOINDEX, 1)


def on_post_build(config):
    """Report, then strip undiscoverable pages out of the sitemap."""
    report.build(
        {
            "store": _store,
            "notes": _store_notes,
            "hidden": _hidden,
            "defaulted": _defaulted,
            "unknown": _unknown,
            "named": _named_groups,
            "inherited": _inherited,
            "overridden": _overridden,
            "unconfigured": _unconfigured,
            "allowed": ALLOWED,
        },
        keystore.CONTAINER,
    )

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
