"""
What the gate tells you about the build it just did.

Every function here PRINTS and returns nothing. It is handed a snapshot of what
hooks/visibility.py decided and turns it into workflow annotations plus a run
summary. It owns no state, reads no frontmatter, and makes no decisions.

=======================================================================
THE TRACE IS THE POINT
=======================================================================

This gate deliberately GUESSES: any of six frontmatter spellings, one value or
a list, and a value that matches a keystore group becomes that group's secret
while anything else is the password itself. That is the right trade for a
casual lock on a public repo -- but a system that guesses MUST show its work,
or a wrong guess is exactly the silent failure the guessing was meant to avoid.

So every build prints, per gated page, every key it resolved and whether it
came from the keystore or from the page. Michael's ask, verbatim: "easy to
debug and trace back but also implement."

=======================================================================
🔒 THE ONE HARD RULE: NAMES, NEVER VALUES
=======================================================================

Nothing here may print a password, its length, or a fragment. Group NAMES are
already in page frontmatter and are not secret. Values are.

⚠️ THAT NOW CUTS BOTH WAYS AND IT IS EASY TO GET WRONG. A LITERAL key's `name`
IS its password -- `password: need2026` means the word in the trace would be
the secret. So a literal is reported by its FIELD and its PAGE, never by its
value, while a group is reported by name. `Resolved.describe()` in keystore.py
is the only formatter allowed to make that distinction, and this module calls
it rather than formatting names itself.

GitHub masks secrets in logs by literal string match, and that masking is NOT
known to survive a multi-line secret being split into lines -- which is exactly
what the keystore does. So this file does not rely on masking. It never has a
secret in scope it is willing to print.

=======================================================================
NOTHING IN HERE FAILS A BUILD
=======================================================================

A report is the ALTERNATIVE to failing. The whole design is that a bad page is
local and visible rather than global and silent -- one page shows an unopenable
notice while the rest of the site deploys. If a report ever raises, that trade
quietly reverses and one page's config takes the site down, which is the exact
failure that removed `--strict` from deploy.yml on 2026-08-01. Print, never
raise.

Called only by hooks/visibility.py.
"""

import os


def _summary(lines):
    """Append to the GitHub Actions run summary, if there is one. Silently does
    nothing on a local build, which is correct -- a local build has a terminal.
    """
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _defaults(defaulted):
    """Pages hidden purely because they never said otherwise.

    NOT a warning. The default is correct and a new page SHOULD start
    unpublished. But a forgotten frontmatter block should be visible once per
    build rather than never.
    """
    if not defaulted:
        return
    print(
        "gate: " + str(len(defaulted))
        + " page(s) hidden by DEFAULT (no `status:` at all): "
        + ", ".join(sorted(defaulted))
    )


def _typos(unknown, allowed):
    """The loudest thing the gate does, because it is the quietest failure it
    can produce: a page that stopped existing while the build went green."""
    if not unknown:
        return

    legal = ", ".join(sorted(allowed))
    for src, written in sorted(unknown.items()):
        print(
            "::warning file=" + src + "::status: '" + written + "' is not one "
            "of " + legal + " -- this page is being treated as `hidden` and "
            "will NOT publish. If that is not what you meant, it is a typo."
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
    for src, written in sorted(unknown.items()):
        lines.append("| `" + src + "` | `" + written + "` | not published |")
    _summary(lines + [""])


def _keytrace(trace, fields):
    """Every gated page and every key that opens it.

    🔒 A group is named. A literal is NOT -- its name is its password. Both go
    through Resolved.describe(), which is the only place that distinction is
    encoded.
    """
    opened = {src: items for src, items in trace.items() if items}
    if not opened:
        return

    print("gate: key trace --")
    for src, items in sorted(opened.items()):
        print("  " + src)
        for item in items:
            print(
                "      " + item.field + ": " + item.describe()
            )

    lines = [
        "### 🔑 Which key opens which page",
        "",
        "Any **one** of a page's keys opens it. A value matching a keystore "
        "group resolves to that group's secret; anything else is the password "
        "itself. All of `" + "`, `".join(fields) + "` mean the same thing and "
        "each takes one value or a list.",
        "",
        "🔒 A literal password is shown by the field it came from, never by "
        "its value -- this log is public.",
        "",
        "| Page | Written as | Resolved |",
        "|---|---|---|",
    ]
    for src, items in sorted(opened.items()):
        for item in items:
            shown = (
                "`" + item.name + "` → keystore group"
                if item.kind == "group"
                else (
                    "🔴 refused" if item.kind == "refused"
                    else "a literal password on this page"
                )
            )
            lines.append(
                "| `" + src + "` | `" + item.field + ":` | " + shown + " |"
            )
    _summary(lines + [""])


def _groups(store, notes, named):
    """What the keystore holds, what asked for it, and what nothing asked for.

    An unused group is not an error -- a key can legitimately be added before
    the page that uses it. But an unused group is indistinguishable from a
    MISSPELLED one from the keystore's side, and the two are usually the same
    incident seen from opposite ends: a page asks for `psm` while the secret
    says `PSM `, giving one missing group and one unused group in one build.
    Printing both halves is what makes that obvious.
    """
    have = store.available()
    print(
        "gate: " + str(len(have)) + " group(s) loaded -- "
        + (", ".join(have) if have else "NONE")
    )
    for note in notes:
        print("::warning::gate keystore: " + note)

    if not have:
        return

    unused = sorted(set(have) - set(named))
    if not unused:
        return

    tail = ""
    if not named:
        tail = (
            "  -- and NO page names any group at all, so every gated page here "
            "is running on a literal password and the keystore is doing "
            "nothing"
        )
    print(
        "gate: " + str(len(unused)) + " keystore group(s) no page names: "
        + ", ".join(unused) + tail
    )


def _overrules(overridden, inherited):
    """The waterfall doing its job. Reported anyway, by name: an override you
    cannot see is the same class of defect as the hole it closed."""
    if inherited:
        print(
            "gate: " + str(len(inherited)) + " page(s) locked by a parent index"
        )
    if not overridden:
        return

    print(
        "gate: " + str(len(overridden)) + " page(s) OVERRULED by a parent index:"
    )
    for src, (was, parent) in sorted(overridden.items()):
        print("  " + src + " -- declared '" + was + "', locked by " + parent)

    lines = [
        "### 🔒 Locked by a parent index",
        "",
        "These pages declared their own status and the folder's gated "
        "`index.md` overruled it. This is the intended behaviour -- the folder "
        "is the switch. Add `inherit: false` to a page that must genuinely "
        "stand outside its folder's lock.",
        "",
        "| Page | It declared | Locked by |",
        "|---|---|---|",
    ]
    for src, (was, parent) in sorted(overridden.items()):
        lines.append("| `" + src + "` | `" + was + "` | `" + parent + "` |")
    _summary(lines + [""])


def _unopenable(unconfigured, store, container, fields):
    """Gated pages nobody can open. Content dropped, site still deployed."""
    if not unconfigured:
        return

    print(
        "gate: " + str(len(unconfigured))
        + " page(s) UNAVAILABLE, no usable key:"
    )
    for src, problems in sorted(unconfigured.items()):
        print("::warning file=" + src + "::gate: " + "; ".join(problems))

    have = store.available()
    if not have:
        cause = (
            "**No gate keys reached this build at all.** Either the `"
            + container + "` secret does not exist, or it is empty, or "
            "everything in it failed to parse (see any keystore warnings "
            "above). A page can still lock itself with a literal password."
        )
    else:
        cause = (
            "The keystore loaded **" + str(len(have)) + " group(s)** ("
            + ", ".join(have) + "). Any of `" + "`, `".join(fields)
            + "` takes a group name, a literal password, or a list of either."
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
    for src, problems in sorted(unconfigured.items()):
        lines.append("| `" + src + "` | " + "; ".join(problems) + " |")
    lines += [
        "",
        "Add the group to the `" + container + "` secret as a "
        "`name = password` line (**Settings -> Secrets and variables -> "
        "Actions**). The readable copy of that block lives in the ClickUp "
        "Accounts task -- update it there first, then paste. See "
        "AUTHORING-GATES.md -> Adding a key group.",
    ]
    _summary(lines)


def build(state, container):
    """The whole report, in the order a reader wants it: what did not publish,
    then what opens what, then what could not be opened.

    `state` is a plain dict assembled by the hook rather than this module
    reaching into it -- so the seam is one call with visible arguments, not a
    set of imported privates. hooks/contrast.py importing five underscored
    names out of hooks/theme.py is the counter-example; renaming one of them
    nearly broke that gate on 2026-08-01.
    """
    _defaults(state["defaulted"])
    _typos(state["unknown"], state["allowed"])

    if state["hidden"]:
        print(
            "gate: " + str(len(state["hidden"]))
            + " page(s) not published (`hidden`)"
        )

    _groups(state["store"], state["notes"], state["named"])
    _keytrace(state["trace"], state["fields"])
    _overrules(state["overridden"], state["inherited"])
    _unopenable(
        state["unconfigured"], state["store"], container, state["fields"]
    )
