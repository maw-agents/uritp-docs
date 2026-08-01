"""
Where a page's key material comes from. Two tiers of secret, six spellings,
and one resolution rule.

A page writes something; this module turns it into passwords and TELLS YOU what
it did with each value. It never decides what publishes, never touches a page,
and never remembers anything between calls: load() returns a Keystore and the
hook holds it.

=======================================================================
WHAT A PAGE MAY WRITE  (all six are the same key, 2026-08-01, Michael)
=======================================================================

    gates:  gate:  keys:  key:  password:  passwords:

Six spellings, ZERO difference between them. Singular or plural, and every word
anyone has reached for. Each takes ONE value or A LIST, and a page may use more
than one at once -- everything found is merged, and ANY ONE of them opens the
page.

    gates: [dev, admin]        two groups
    password: need2026         one literal
    key: psm                   one group
    passwords: [a, b]          two literals, or groups, or one of each

    gates: [dev, admin]        <- and all three on the same page is fine.
    passwords: need2026           dev OR admin OR need2026 opens it.
    key: psm                      psm too.

⚠️ WHY NOT ONE CANONICAL SPELLING: because a wrong guess used to fail SILENTLY
and expensively. `password: [dev, admin, pm]` -- the plural-looking list under
the singular key -- was str()'d into the characters of a Python list repr and
shipped as the page's real password. Encrypted correctly, reported clean,
openable by nobody, and it took the whole docs/safety/ subtree with it because
that page is a folder switch. Accepting every spelling costs one tuple. Making
Michael remember which of six words is the magic one costs a locked section
nobody notices for a month.

=======================================================================
GROUP NAME OR LITERAL PASSWORD -- the rule, and it is one line
=======================================================================

    A value that MATCHES A GROUP in the keystore resolves to that group's
    password. Anything else IS the password, exactly as written.

So `dev` finds the keystore's `dev` line; `need2026` is not a group, so it is
just the password. No prefix, no sigil, no second key to learn. Add a group to
the secret and every page already naming it starts working; delete the group
and that page falls back to treating the word as a literal, which is reported.

⚠️ THE ONE AMBIGUITY, NAMED RATHER THAN ENGINEERED AWAY: a literal password
that happens to be spelled exactly like a group name resolves as the GROUP.
So do not use a group name as a page's one-off password -- and if the keystore
later gains a group whose name equals some page's literal, that page silently
changes which secret opens it. That is why every resolution is printed by name
and kind at build time: the trace is the mitigation, not a cleverer rule.

This is a CASUAL gate on a PUBLIC repo. The whole page source, including a
gated page's plaintext, is readable on github.com. Guessing right about intent
and saying so out loud beats a strict grammar that locks a section by accident.

=======================================================================
TIER 1, THE CONTAINER -- the default, and where a group should live
=======================================================================

ONE repository secret, URITP_GATE_KEYS, holding a block of lines:

    # URITP docs gate keys. One group per line: name = password
    admin = ...
    dev   = ...
    psm   = ...

The key in that block is the EXACT string a page writes. No uppercasing, no
prefix, no transformation. Adding a group is adding a line to that secret's
value -- no file in this repository changes, and no name is chosen by anything
but Michael.

=======================================================================
TIER 2, THE ROTATION HATCH -- rare, and deliberately inconvenient
=======================================================================

A single group MAY instead live in its own secret, URITP_GATE_<GROUP>,
uppercased with hyphens as underscores.

    THIS EXISTS FOR EXACTLY ONE REASON and it is not "the other way to do it":
    rotating a key inside the container means repasting the WHOLE block from
    memory, because GitHub never shows you a secret's current value. For a
    high-churn key -- the one reissued to a new cohort every September -- that
    risks every other group each time it turns over. Its own secret makes that
    rotation atomic. It also needs one line in deploy.yml, because GitHub only
    hands a workflow the secrets it names. That cost is why it is the
    exception rather than the default.

PRECEDENCE: the container wins. A name in both tiers resolves from the
container and the duplicate is reported -- silently preferring either one would
make a half-finished migration undetectable.

🔴 ONE GROUP NAME IS RESERVED. hatch_var("keys") derives URITP_GATE_KEYS, which
IS the container. A group literally named `keys` would have resolved its
"password" to the entire keystore block -- every group's secret concatenated
into one string, with no warning. available() guarded against LISTING it, which
is the kind of half-guard that reads as handled. Lookup refuses it now, by name.

🔒 THIS MODULE NEVER EMITS A PASSWORD -- not the value, not its length, not a
fragment. Group NAMES are already in page frontmatter and are not secret;
values are. Everything in Keystore.notes and every Resolved.name is safe to
print, and must stay that way: GitHub's log masking is a literal string match
that is NOT known to survive a multi-line secret being split into lines.

⚠️ A KNOWN ASYMMETRY, PRESERVED RATHER THAN QUIETLY CHANGED. Hatch names are
DERIVED from environment variables for available() (URITP_GATE_MY_GROUP ->
`my_group`) while a page may spell the same group `my-group`, which maps back
to the same variable. Lookup works either way; the available list shows the
underscored spelling. Harmless today, confusing in a mismatch report. Use
hyphen-free group names and the question never arises.

Called only by hooks/visibility.py. Reader-facing docs: AUTHORING-GATES.md.
The readable master copy of the key block is the ClickUp Accounts task -- a
secret cannot be read back, so this build is the copy, not the source.
"""

import os

CONTAINER = "URITP_GATE_KEYS"
ENV_PREFIX = "URITP_GATE_"      # tier 2 only: the rotation hatch

# Every frontmatter key that means "key material". All equivalent, all accept
# one value or a list, all merge. Add a spelling here and it works everywhere;
# there is no second place to register it.
#
# ⚠️ Keep `gates` first: it is the one AUTHORING-GATES.md teaches, so it is the
# one named first in any error message built from this tuple.
FIELDS = ("gates", "gate", "keys", "key", "password", "passwords")


def hatch_var(name):
    """Tier 2 only. psm -> URITP_GATE_PSM."""
    return ENV_PREFIX + name.upper().replace("-", "_")


class Resolved:
    """One value from frontmatter, and what it turned out to be.

    `name` and `kind` are SAFE TO PRINT. `password` is not, and nothing outside
    the envelope should ever read it.

        kind == "group"    matched a keystore group; password is the secret
        kind == "literal"  matched nothing; the word itself is the password
        kind == "refused"  cannot be used at all; password is None
    """

    def __init__(self, name, kind, password, field, note=None):
        self.name = name          # exactly as written in frontmatter
        self.kind = kind
        self.password = password
        self.field = field        # which of FIELDS it came from
        self.note = note

    def describe(self):
        """🔒 Names only. Never the value of a literal -- a one-off password is
        still a password, and it would land in a public build log."""
        if self.kind == "group":
            return self.name + " (group)"
        if self.kind == "literal":
            return self.name + " (literal password on this page)"
        return self.name + " (REFUSED)"


def _values(meta):
    """Every value from every accepted field, as (field, value) in FIELDS order.

    Scalars and lists both flatten to the same thing. A None, an empty string
    or a bare `gates:` with nothing after it contributes nothing rather than
    an empty-string password that would open the page for anyone who submits
    a blank form.
    """
    out = []
    for field in FIELDS:
        raw = meta.get(field)
        if raw is None:
            continue
        items = raw if isinstance(raw, (list, tuple, set)) else [raw]
        for item in items:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                out.append((field, text))
    return out


def declares_keys(meta):
    """Did this page bring key material of its own? Used by the waterfall to
    decide whether a locked child contributes anything beyond its parent."""
    return bool(_values(meta))


class Keystore:
    """Group name -> password, resolved once per build and then read-only.

    Deliberately a value the hook HOLDS rather than module state this file
    keeps: see gate/__init__.py. Two builds in one process cannot contaminate
    each other, and nothing here has to be reset between them.
    """

    def __init__(self, container, hatch, notes):
        self._container = container   # name -> password, from URITP_GATE_KEYS
        self._hatch = hatch           # name -> password, one secret each
        self.notes = notes            # parse warnings. NAMES ONLY. printable.

    def __len__(self):
        return len(self.available())

    def available(self):
        """Every group this build can satisfy. NAMES ONLY -- these are already
        written in page frontmatter and are not secret."""
        return sorted(set(self._container) | set(self._hatch))

    def _group(self, name):
        """(password, note) for a group NAME, or (None, note) if it is not one."""
        if hatch_var(name) == CONTAINER:
            # A group named `keys`. Refuse: the derived variable IS the
            # container, so resolving it would hand back every secret at once.
            return None, (
                "'" + name + "' cannot be a group name: its rotation-hatch "
                "variable would collide with the " + CONTAINER + " container "
                "itself"
            )

        inside = self._container.get(name)
        outside = self._hatch.get(name)

        if inside and outside:
            return inside, (
                "group '" + name + "' is in both " + CONTAINER + " and "
                + hatch_var(name) + "; the container wins -- remove one"
            )
        return inside or outside, None

    def resolve(self, meta):
        """Every key this page declares, in any spelling, as [Resolved].

        A value matching a group becomes that group's password; anything else
        is the password itself. Nothing raises and nothing is dropped silently:
        the caller gets the full list with its provenance and decides how loud
        to be.

        DEDUPED BY RESOLVED PASSWORD, because two wraps opening on the same
        secret would tell an observer those two names share a password. First
        occurrence wins, so the FIELDS order above decides which name gets
        reported -- `gates` before `password`, which is the more useful trace.
        """
        out = []
        seen = set()

        for field, value in _values(meta):
            lowered = value.lower()
            password, note = self._group(lowered)

            if password:
                kind = "group"
            elif note:
                # Refused outright: a name that cannot be a group, and that
                # would be a bizarre literal password. Do not silently demote.
                out.append(Resolved(value, "refused", None, field, note))
                continue
            else:
                kind, password = "literal", value

            if password in seen:
                continue
            seen.add(password)
            out.append(Resolved(value, kind, password, field, note))

        return out


def load(env=None):
    """Parse both tiers out of the environment. Returns a Keystore.

    Every rule below is a real failure mode raised in review, not defensive
    habit -- each one is silent, and each one produces a working site with one
    broken group, which is worse than a loud failure.
    """
    env = os.environ if env is None else env
    container = {}
    hatch = {}
    notes = []

    raw = env.get(CONTAINER, "")
    for number, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        # `#` is a comment ONLY at the start of a line. Mid-line it is an
        # ordinary password character and must survive.
        if line.startswith("#"):
            continue
        if "=" not in line:
            notes.append("line " + str(number) + " has no '=', skipped")
            continue

        # Split on the FIRST '=' only: a password may legitimately contain one.
        name, _, value = line.partition("=")
        name = name.strip().lower()
        # Trailing spaces are invisible in the GitHub secret box and would
        # break every unlock with no error anywhere.
        value = value.strip()

        if not name:
            notes.append("line " + str(number) + " has no name, skipped")
            continue
        if not value:
            notes.append("group '" + name + "' has an empty password, skipped")
            continue
        if name in container:
            # FIRST wins, and say so. Last-wins would be silent.
            notes.append(
                "group '" + name + "' appears twice; the first one is used"
            )
            continue

        container[name] = value

    for key, value in env.items():
        if not key.startswith(ENV_PREFIX) or not value or key == CONTAINER:
            continue
        hatch[key[len(ENV_PREFIX):].lower()] = value

    return Keystore(container, hatch, notes)
