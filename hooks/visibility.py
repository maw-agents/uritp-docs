"""
Page visibility. Reads `status:` from frontmatter and decides what publishes.

    status: public      listed in the sidebar, indexed, plaintext
    status: gated       listed, body AES-encrypted, needs a password
    status: unlisted    direct link only: no nav, no search, no search engines
    status: hidden      never built                          (DEFAULT)

    listed: false       an INDEPENDENT switch: keep this page out of the nav,
                        search and sitemap WHATEVER its status is. The four
                        statuses conflated two questions (is it published / can
                        it be found); this separates them. `unlisted` is the
                        shorthand for public + not-listed.

⚠️ `hidden` IS NOT ACCESS CONTROL, IT IS NOT-PUBLISHED. This repository is
public, so the markdown source of every page -- including a `hidden` page and a
`gated` page's plaintext -- is readable at github.com by anyone. `hidden` keeps
a page off the SITE. It is the strongest thing this file can do and it is still
not a permission.

FULL AUTHORING REFERENCE: AUTHORING-GATES.md. Kept there rather than here on
purpose -- it is read by whoever writes a page, this file is read by whoever
changes the machine, and one document serving both is how both go stale.

=======================================================================
THE THREE FILES, AND WHY THIS ONE IS THE ONLY HOOK
=======================================================================

    hooks/visibility.py      THIS FILE. MkDocs events, the status decision,
                             the folder waterfall, and all build state.
    hooks/gate/keystore.py   group name -> password. Two tiers.
    hooks/gate/envelope.py   AES-GCM + PBKDF2 + the unlock markup.
                             ⚠️ PAIRED WITH docs/javascripts/gate.js.

Split 2026-08-01 at 33.8KB, which is past the ~30KB cap an agent can fetch
whole -- a file that cannot be read before it is edited cannot be edited
safely, and this is the file where a silent mistake is most expensive.

🔴 THE LIBRARIES ARE NOT HOOKS AND MUST NEVER BE REGISTERED. The hook order in
mkdocs.yml is load-bearing (this file drops `hidden` pages BEFORE links.py
builds its id registry). One feature, one slot in that order. See
gate/__init__.py for the full rule, including why every name over there is
public rather than underscored.

ALL MUTABLE BUILD STATE LIVES HERE. The modules in gate/ are pure.

=======================================================================
A TYPO MUST NOT DELETE A PAGE IN SILENCE   (2026-08-01, Michael)
=======================================================================

An unrecognised value falls through to `hidden`, because guessing what someone
meant is worse than not publishing. But it used to do that WITHOUT SAYING SO:
`status: publi`, a stray capital, `status: new` -- the page vanished, the build
went green, and the only way to find out was for a reader to go looking for
something that used to be there.

That is a worse failure than a broken build. A build that breaks screams. A
page that quietly stops existing does not, and this site's whole promise is
"assume the PDF is out of date, check here instead."

So four things are REPORTED BY NAME every build, and none of them fail it:

  * an unrecognised `status:`, quoted back exactly as written
  * the count of pages hidden purely by DEFAULT (no `status:` at all)
  * a `password:` holding a LIST rather than one value -- see below
  * a keystore group no page names, and a page naming a group that does not
    exist. Two halves of the same question, and neither used to be asked.

The list of hidden pages is handed to hooks/links.py as `_uritp_hidden` on the
config (src_uri -> declared `id:` or None) so a link to a hidden page can say
"hidden" instead of "broken". A plain dict rather than an import: unwire this
hook and links.py reads an empty dict and behaves exactly as it did before.

🔴 `password:` WITH A LIST IS THE ONE THAT COST US. Frontmatter takes either

    password: rehearsal26        ONE literal value, this page only
    gates: [psm, admin]          NAMES of keystore groups, any one opens it

and `password: [dev, admin, pm]` looks like the second while being the first.
It used to be stringified -- the page's actual password became the seven-odd
characters of a Python list repr, which no human would ever type, and NOTHING
WARNED because a password had technically been supplied. Encrypted correctly,
reported clean, openable by nobody. Now it lands in the unconfigured path: the
content is dropped, the page says it is unavailable, and the build names it.

⚠️ It does NOT fail the build, and that is deliberate. Failing here took the
whole site stale over one page's config on 2026-08-01 -- the same trade
`--strict` used to make, rejected for the same reason and removed from
deploy.yml the same day. Local and visible beats global and silent.
URITP_GATES_STRICT=1 restores hard-fail for anyone who wants it.

=======================================================================
THE FOLDER WATERFALL  (precedence FLIPPED 2026-08-01, Michael)
=======================================================================

**A gated `index.md` locks its whole subtree, at any depth, and it BEATS what
the child page declared.** Dropping an index.md into a folder IS the switch.
Every page beneath a locked index is genuinely encrypted, not merely hidden
from the sidebar -- which would leave every child readable by direct URL while
looking protected.

    docs/safety/index.md         status: gated   <- the switch
    docs/safety/test.md          status: public  <- LOCKED ANYWAY, and reported
    docs/safety/keys/master.md   (silent)        <- locked, at any depth

~~A page overrides by declaring its own `status:` (any value) or
`inherit: false`. Only silence inherits.~~ REVERSED on the day it shipped: it
meant `status: public` on one child quietly punched a hole in a locked safety
section, and the page that did it looked completely normal.

Two things it deliberately CANNOT do:

  * It cannot publish a `hidden` page. A rule whose job is to RAISE protection
    must never be the reason something reached a reader.
  * It cannot be silent. `inherit: false` is the one escape hatch, it is one
    greppable line, and every overruled page is REPORTED BY NAME.

⚠️ THERE IS A SECOND WATERFALL AND IT RUNS THE OTHER WAY. hooks/theme.py's
SKIN waterfall is child-wins; this LOCK waterfall is parent-wins. Precedence
follows CONSEQUENCE, not symmetry: a skin is a preference, a lock is not.
Both fire off index.md and walk the same ancestors, so merging them will look
like tidying. That is the day a locked page publishes. Do not.

KEYS UNDER THE WATERFALL: a locked child KEEPS its own `password:`/`gates:` and
GAINS the parent's. Any one opens the page, which the envelope already
supported, so a one-page password stays a one-line thing to add and delete
without disturbing the folder key.

A MISSING KEY LOCKS THE PAGE, IT DOES NOT FREEZE THE SITE. A gated page naming
a group with no password behind it publishes as an unopenable notice: content
DROPPED, page says so, build reports it loudly, everything else deploys.

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

from gate import envelope, keystore      # noqa: E402  (path set above)

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
    """The page's OWN status, or None if it did not declare one. Distinguishing
    'said nothing' from 'said hidden' is what makes the waterfall safe: silence
    inherits, `hidden` is never overruled.

    Pass `src_uri` to RECORD what happened. It is optional because this runs
    twice over index.md files -- once in the folder-gate pre-pass and once in
    the main walk -- and a page must not be reported twice. The main walk is
    the one that passes it.
    """
    raw = meta.get("status")
    if raw is None:
        if src_uri is not None:
            _defaulted.add(src_uri)
        return None
    status = str(raw).strip().lower()
    if status in ALLOWED:
        return status
    # Unrecognised. Fall through to hidden -- guessing what someone meant is
    # worse than not publishing -- but never in silence again.
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

    🔴 A LIST HERE IS ALWAYS A MISTAKE and it used to be a silent one. See the
    module docstring: `password: [dev, admin, pm]` reads like `gates:` but is
    the one-literal-value key, so it used to be str()'d into a Python list repr
    and shipped as the page's real password. Refused now, by name.
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
    contributes its own local password and the locking index contributes the
    folder key, and either one opens the page. Never raises unless
    URITP_GATES_STRICT=1.

    `problems` non-empty means this page cannot be published at all: it is
    rendered as an unopenable notice rather than encrypted, and reported.
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

    ⚠️ THIS DOES NOT BELONG IN A VISIBILITY HOOK and it may not need to exist
    at all. It is a markdown transform with no relationship to publishing,
    gating or encryption -- a second thing that moved into this file, which is
    half of why the file got too big to read.

    AND IT MAY BE REDUNDANT: `attr_list` is enabled in mkdocs.yml and the
    comment beside it credits that extension with exactly this syntax.
    attr_list natively supports `[text]{.class}`. So either this function is
    dead code or that comment is wrong -- two claimants on one behaviour, and
    one of them is lying. UNMEASURED as of 2026-08-01, deliberately: settle it
    by deleting this on a branch and looking at a rendered `.tbc`, not by
    reasoning. Do not fold that test into an unrelated PR.
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
            # No src_uri: this is the pre-pass, and the main walk below will
            # report this same file. Passing it here would double-count.
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
        # `hidden` is the one status it may not overrule: this rule raises
        # protection and must never be the reason a page got published.
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


def _summary(lines):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _report_status_typos():
    """The loudest thing this file does, because it is the quietest failure it
    can produce: a page that stopped existing while the build went green."""
    if _defaulted:
        # Not a warning. The default is correct and a new page SHOULD start
        # unpublished. But a forgotten frontmatter block should be visible
        # once rather than never.
        print(
            "gate: " + str(len(_defaulted))
            + " page(s) hidden by DEFAULT (no `status:` at all): "
            + ", ".join(sorted(_defaulted))
        )

    if not _unknown:
        return

    legal = ", ".join(sorted(ALLOWED))
    for src, written in sorted(_unknown.items()):
        print(
            "::warning file=" + src + "::status: '" + written + "' is not one of "
            + legal + " -- this page is being treated as `hidden` and will NOT "
            "publish. If that is not what you meant, it is a typo."
        )

    lines = [
        "### \u26a0\ufe0f Unrecognised `status:` -- these pages did not publish",
        "",
        "An unrecognised value falls through to `hidden`, because guessing what "
        "you meant is worse than publishing the wrong thing. The build did not "
        "fail. **The page simply is not on the site.**",
        "",
        "Legal values: `public`, `gated`, `unlisted`, `hidden`.",
        "",
        "| Page | It says | Result |",
        "|---|---|---|",
    ]
    for src, written in sorted(_unknown.items()):
        lines.append("| `" + src + "` | `" + written + "` | not published |")
    _summary(lines + [""])


def _report_unused_groups():
    """A group in the keystore that no page names.

    Not an error -- a key can legitimately be added before the page that uses
    it. But an unused group is indistinguishable from a MISSPELLED one from the
    keystore's side, and the two are usually the same incident seen from
    opposite ends: a page asks for `psm` while the secret says `PSM `, and you
    get one missing group and one unused group in the same build. Printing both
    halves is what makes that obvious.

    🔒 Names only.
    """
    have = set(_store.available())
    used = set(_named_groups)
    unused = sorted(have - used)
    if not unused:
        return

    print(
        "gate: " + str(len(unused)) + " keystore group(s) that no page names: "
        + ", ".join(unused)
        + ("  -- and no page names ANY group; every gated page here is on a "
           "literal `password:`" if not used else "")
    )


def _report():
    """Loud, because the whole point of not failing the build is that the
    problem must not become invisible instead.

    🔒 Group NAMES only. Never a password, never a length, never a fragment.
    """
    _report_status_typos()

    if _hidden:
        print("gate: " + str(len(_hidden)) + " page(s) not published (`hidden`)")

    have = _store.available()
    print("gate: " + str(len(have)) + " group(s) loaded -- "
          + (", ".join(have) if have else "NONE"))

    for note in _store_notes:
        print("::warning::gate keystore: " + note)

    _report_unused_groups()

    if _inherited:
        print("gate: " + str(len(_inherited)) + " page(s) locked by a parent index")

    # The waterfall overruling a page is legitimate and expected. It is
    # reported anyway, by name: an override you cannot see is the same class of
    # defect as the hole the override closed.
    if _overridden:
        print("gate: " + str(len(_overridden)) + " page(s) OVERRULED by a parent index:")
        for src, (was, parent) in sorted(_overridden.items()):
            print("  " + src + " -- declared '" + was + "', locked by " + parent)
        lines = [
            "### 🔒 Locked by a parent index",
            "",
            "These pages declared their own status and the folder's gated "
            "`index.md` overruled it. This is the intended behaviour -- the "
            "folder is the switch. Add `inherit: false` to a page that must "
            "genuinely stand outside its folder's lock.",
            "",
            "| Page | It declared | Locked by |",
            "|---|---|---|",
        ]
        for src, (was, parent) in sorted(_overridden.items()):
            lines.append("| `" + src + "` | `" + was + "` | `" + parent + "` |")
        _summary(lines + [""])

    if not _unconfigured:
        return

    print(
        "gate: " + str(len(_unconfigured))
        + " page(s) UNAVAILABLE, key not configured:"
    )
    for src, problems in sorted(_unconfigured.items()):
        print("::warning file=" + src + "::gate: " + "; ".join(problems))

    if not os.environ.get("GITHUB_STEP_SUMMARY"):
        return

    # Distinguish "no keystore at all" from "keystore present but this group
    # is not in it" -- identical symptoms, completely different fixes.
    if not have:
        cause = (
            "**No gate keys reached this build at all.** Either the "
            "`" + keystore.CONTAINER + "` secret does not exist, or it is "
            "empty, or everything in it failed to parse (see any keystore "
            "warnings above)."
        )
    else:
        cause = (
            "The keystore loaded **" + str(len(have)) + " group(s)** ("
            + ", ".join(have) + "). Check the spelling in `gates:` against "
            "that list -- and check that a list of group names is in `gates:` "
            "rather than in `password:`, which takes one literal value."
        )

    lines = [
        "### \u26a0\ufe0f Gated pages that nobody can open",
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
        "Add the group to the `" + keystore.CONTAINER + "` secret as a "
        "`name = password` line (**Settings -> Secrets and variables -> "
        "Actions**). The readable copy of that block lives in the ClickUp "
        "Accounts task -- update it there first, then paste. "
        "See AUTHORING-GATES.md -> Adding a key group.",
    ]
    _summary(lines)


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
