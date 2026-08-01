"""
Reading key material out of a page's frontmatter.

=======================================================================
ONE RULE. THE SHAPE DECIDES, NOT THE WORD.
=======================================================================

    BRACKETS  ->  names of groups in the URITP_GATE_KEYS secret
    BARE      ->  a literal password, written right here

That is the entire grammar:

    gates: [dev, admin]        the dev and admin group passwords
    password: need2026         literally need2026
    keys: [psm]                the psm group password
    gate: rehearsal            literally rehearsal

SIX WORDS, ALL IDENTICAL: gate, gates, key, keys, password, passwords.
Singular and plural both work because remembering which one is "correct" is
exactly the kind of trivia that makes an author guess, and a wrong guess used
to be silent. Say it however it comes out of your head.

⚠️ THE WORD CARRIES NO MEANING. `password: [dev]` is a GROUP because of the
brackets, not a literal because of the word; `gates: dev` is a LITERAL for the
same reason inverted. That looks backwards written down and it is deliberate:
one rule you can see in the value beats six words you have to remember. There
is nothing to look up, and nothing to get subtly wrong.

🔴 WHY THIS EXISTS. Until 2026-08-01 the WORD decided, and docs/safety/index.md
said `password: [ dev, admin, pm]` -- the literal key holding a list of group
names. It was str()'d, so the safety folder's real password became the
characters of a Python list repr. No keystore lookup ever happened. Nothing
warned, because a password HAD been supplied. Green build, correct encryption,
openable by nobody, and the whole safety subtree waterfalled off it.

Under shape-decides that exact frontmatter is simply CORRECT and always would
have been. The bug could not be written.

=======================================================================
COMBINE FREELY. ANY ONE OF THEM OPENS THE PAGE.
=======================================================================

    gates: [dev, admin]
    passwords: need2026

The envelope wraps one content key per password, ~100 bytes each, so listing
more ways in costs nothing and there is no reason to ration them. Repeat keys,
mix words, add a folder key on top through the waterfall -- it all unions.

An EMPTY value (`key:` with nothing after it) is ignored and noted. Half-typed
frontmatter is a normal state to leave a file in for ten minutes; it should not
be an error, and it should not be silent either.

=======================================================================
⚠️ THE ONE GENUINE AMBIGUITY, AND IT IS RESOLVED BY TRYING BOTH
=======================================================================

`gate: psm` is a literal by the shape rule. But `psm` is also a real group, so
the author probably meant the group and forgot the brackets.

Rather than guess, a bare scalar that MATCHES A KNOWN GROUP NAME resolves as
BOTH -- the literal AND the group's password -- and says so in the build log.
The page opens either way, nobody is locked out by a missing pair of brackets,
and the log tells you exactly what happened so you can tighten it if you meant
one and not the other.

That trade is only correct because of what this gate IS. Michael, 2026-08-01:
"we're OBVI not actually locking this shit down so it's super casual." The
repository is public and every gated page's plaintext is readable at
github.com; this keeps a casual reader out of a document they were not handed a
password for. Being forgiving costs nothing real and saves a lockout. In a
system that genuinely gated access, this would be the wrong call and it should
be re-argued rather than inherited.

Called only by hooks/visibility.py. Reader-facing docs: AUTHORING-GATES.md.
"""

import difflib

# All six are the same key. Order is only the order they are read in, which
# affects nothing: every value found is unioned.
WORDS = ("gate", "gates", "key", "keys", "password", "passwords")


class Source:
    """One thing a page said, and what it turned out to mean.

    Kept as an object rather than a bare string so the build log can say WHERE
    a password came from without ever printing the password. Every field here
    is safe to print.
    """

    def __init__(self, word, written, kind, group=None):
        self.word = word          # the frontmatter key, as the author typed it
        self.written = written    # the value, as written. A NAME or a literal.
        self.kind = kind          # "group" | "literal" | "both" | "unknown"
        self.group = group        # the group name, when one was resolved

    def trace(self):
        """🔒 One line for the build log. Names only, never a password value.

        A `literal` deliberately does NOT echo what was written -- that value
        IS the password.
        """
        if self.kind == "group":
            return self.word + ": [" + self.group + "] -> group '" + self.group + "'"
        if self.kind == "both":
            return (
                self.word + ": " + self.group + " -> a literal AND the group '"
                + self.group + "' (no brackets, but that is a real group name, "
                "so both were used and either opens the page)"
            )
        if self.kind == "unknown":
            return self.word + ": [" + self.written + "] -> NO SUCH GROUP"
        return self.word + ": <a literal password, not shown>"


def _values(meta):
    """Every key-material entry a page declared, as (word, value, is_list).

    A list stays a list, a scalar stays a scalar: the SHAPE is the meaning, so
    it must survive to the caller intact.
    """
    out = []
    for word in WORDS:
        if word not in meta:
            continue
        raw = meta[word]
        if raw is None:
            out.append((word, None, False))          # `key:` with nothing
            continue
        if isinstance(raw, (list, tuple, set)):
            out.append((word, list(raw), True))
            continue
        if isinstance(raw, dict):
            out.append((word, raw, None))            # nonsense; caller reports
            continue
        out.append((word, str(raw), False))
    return out


def declares(meta):
    """Did this page bring key material of its own?

    True even for an empty `key:` -- the page tried to say something, and the
    caller needs to know that in order to report the emptiness rather than
    treating the page as having said nothing at all.
    """
    return any(word in meta for word in WORDS)


def read(meta, store):
    """Resolve one page's frontmatter against the keystore.

    Returns (passwords, sources, problems).

      passwords  every secret that opens this page, deduped, order preserved
      sources    one Source per thing the page said, for the build log
      problems   reasons this page cannot be opened AT ALL. Non-empty means the
                 caller drops the content and publishes a notice instead.

    Never raises. Never prints. The caller owns both.
    """
    passwords = []
    sources = []
    problems = []
    known = store.available()

    for word, raw, is_list in _values(meta):
        if is_list is None:
            problems.append(
                "`" + word + ":` was given a mapping. It takes either a bare "
                "value (a literal password) or a list in brackets (group "
                "names from the keystore)"
            )
            continue

        if raw is None or (not is_list and not str(raw).strip()):
            sources.append(Source(word, "", "empty"))
            continue

        # ── BRACKETS: group names ────────────────────────────────────────
        if is_list:
            for item in raw:
                name = str(item).strip().lower()
                if not name:
                    continue
                password, note = store.password_for(name)
                if note:
                    problems.append(note)
                if password:
                    passwords.append(password)
                    sources.append(Source(word, name, "group", name))
                else:
                    sources.append(Source(word, name, "unknown"))
                    near = difflib.get_close_matches(name, known, n=2, cutoff=0.6)
                    detail = "no group named '" + name + "'"
                    if near:
                        detail += " -- did you mean " + " or ".join(near) + "?"
                    elif known:
                        detail += ". Groups in the keystore: " + ", ".join(known)
                    else:
                        detail += ", and the keystore is empty entirely"
                    problems.append(detail)
            continue

        # ── BARE: a literal password ─────────────────────────────────────
        literal = str(raw).strip()
        passwords.append(literal)

        # ...unless it is also a real group name, in which case take both and
        # say so. A forgotten pair of brackets must not lock anyone out.
        match = literal.lower()
        if match in known:
            password, note = store.password_for(match)
            if note:
                problems.append(note)
            if password:
                passwords.append(password)
            sources.append(Source(word, match, "both", match))
        else:
            sources.append(Source(word, literal, "literal"))

    # Two identical secrets would ship two wraps that both open, which tells an
    # observer those two ways in are the same secret. Deduping also makes a
    # child repeating its parent's password free.
    seen = set()
    unique = []
    for value in passwords:
        if value not in seen:
            seen.add(value)
            unique.append(value)

    return unique, sources, problems
