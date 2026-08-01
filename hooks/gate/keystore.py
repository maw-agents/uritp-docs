"""
Where a group name finds its password. Two tiers, one shape.

A page writes a group name; this module turns it into a password. That is the
whole job. It never decides what is published, never touches a page, and never
remembers anything between calls: load() returns a Keystore and the hook holds
it.

🔒 THIS MODULE NEVER EMITS A PASSWORD -- not the value, not its length, not a
fragment. Group NAMES are already written in page frontmatter and are not
secret; values are. Everything in Keystore.notes is safe to print, and it has
to stay that way, because GitHub's log masking is a literal string match that
is NOT known to survive a multi-line secret being split into lines.

=======================================================================
TIER 1, THE CONTAINER -- the default, and where a name should live
=======================================================================

ONE repository secret, URITP_GATE_KEYS, holding a block of lines:

    # URITP docs gate keys. One group per line: name = password
    admin = ...
    dev   = ...
    psm   = ...

The key in that block is the EXACT string a page writes in `gates:`. No
uppercasing, no prefix, no transformation. `gates: [psm]` looks up `psm`.
Adding a group is adding a line to that secret's value -- no file in this
repository changes, and no name is chosen by anything but Michael.

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
    rotation atomic.

    A group in its own secret needs one line in deploy.yml, because GitHub only
    hands a workflow the secrets it names. That is the cost of the hatch, and
    it is why the hatch is the exception rather than the default.

PRECEDENCE: the container wins. A name present in both tiers resolves from the
container and the duplicate is reported -- silently preferring either one would
make a half-finished migration undetectable.

🔴 ONE GROUP NAME IS RESERVED, AND IT WAS A LIVE HOLE UNTIL 2026-08-01.
hatch_var("keys") derives URITP_GATE_KEYS, which IS the container. A group
literally named `keys` would therefore have resolved its "password" to the
entire keystore block -- every group's secret, concatenated, as one password
string, with no warning anywhere. available() had guarded against LISTING it,
which is exactly the kind of half-guard that reads as "handled". Lookup is now
guarded too, by name, and refuses rather than resolves.

The old single-tier design's _env_key(), the mandatory prefix on container
groups, and the reserved-namespace rule are all gone; the derivation survives
ONLY inside the hatch, where a real environment variable name is unavoidable.

⚠️ A KNOWN ASYMMETRY, PRESERVED RATHER THAN QUIETLY CHANGED. Hatch names are
DERIVED from environment variables for available() (URITP_GATE_MY_GROUP ->
`my_group`) but a page may spell the same group `my-group`, which maps back to
the same variable. So lookup works either way while the available-groups list
shows the underscored spelling. Harmless today, confusing in a mismatch report.
Use hyphen-free group names and the question never arises.

Called only by hooks/visibility.py. Reader-facing documentation of all of this
lives in AUTHORING-GATES.md -> Adding a key group; the readable master copy of
the block itself is the ClickUp Accounts task, because a secret cannot be read
back and this build is therefore the copy, not the source.
"""

import os

CONTAINER = "URITP_GATE_KEYS"
ENV_PREFIX = "URITP_GATE_"      # tier 2 only: the rotation hatch


def hatch_var(name):
    """Tier 2 only. psm -> URITP_GATE_PSM."""
    return ENV_PREFIX + name.upper().replace("-", "_")


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

    def password_for(self, name):
        """Returns (password_or_None, note_or_None).

        Never raises and never prints: the caller decides how loud a miss
        should be, because only the caller knows whether a page actually asked
        for this group.
        """
        if hatch_var(name) == CONTAINER:
            # A group named `keys`. Refuse: the derived variable IS the
            # container, so resolving it would hand back every secret at once.
            return None, (
                "group '" + name + "' cannot be used: its rotation-hatch "
                "variable would collide with the " + CONTAINER + " container "
                "itself. Rename the group."
            )

        inside = self._container.get(name)
        outside = self._hatch.get(name)

        if inside and outside:
            return inside, (
                "group '" + name + "' is in both " + CONTAINER + " and "
                + hatch_var(name) + "; the container wins -- remove one"
            )
        if inside:
            return inside, None
        if outside:
            return outside, None
        return None, None


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
