"""
Footer build stamp.

Answers one question from any page, without opening Actions: **is what I am
looking at the latest push?** When a build fails, GitHub Pages keeps serving the
previous commit with no banner and no error page. The site simply stops
changing. This stamp is the only signal that has happened.

It renders two things:

    PR #18 · 1 Aug 2026, 12:19 AM ET

The PR number is the house standard (a quiet linked pointer, not a changelog).
The timestamp is kept deliberately, against that standard, because on 2026-08-01
the site froze twice and BOTH diagnoses came off the clock, not the number: a
footer reading 11:23 PM at 11:34 PM is instantly, obviously wrong to anybody,
whereas "PR #16" only reads as stale if you already know the latest PR is #18.
A staleness signal that requires prior knowledge is not a staleness signal.
One of those two is doing the actual work; it costs eight words to keep both.

The PR number is parsed from the head commit SUBJECT, passed in by the workflow
as BUILD_COMMIT_MESSAGE:

    squash merge   "fix: repair the venue links (#16)"        -> PR #16
    merge commit   "Merge pull request #16 from maw-agents/x" -> PR #16
    direct push    "Update todd-theatre.md"                   -> short SHA

The fallback is load-bearing, not a nicety: most edits to this repo are made
from the GitHub UI edit pencil and never see a branch, so a stamp that could
only render a PR number would be blank most of the time. Every direct push
tonight would have shown nothing.

Only the subject line is read. A commit body that happens to mention another
issue number must not win.

Works by extending `copyright` at config time rather than overriding Material's
footer template: one small hook, no theme override to maintain across upgrades.

Wired in mkdocs.yml under `hooks:`. Documented in README.md.
"""

import datetime
import os
import re

REPO = "https://github.com/maw-agents/uritp-docs"

_PR = re.compile(r"#(\d+)")


def _link(href, label):
    return '<a href="' + REPO + href + '">' + label + "</a>"


def on_config(config):
    lines = os.environ.get("BUILD_COMMIT_MESSAGE", "").strip().splitlines()
    found = _PR.findall(lines[0]) if lines else []
    sha = os.environ.get("GITHUB_SHA", "")

    if found:
        source = _link("/pull/" + found[-1], "PR #" + found[-1])
    elif sha:
        source = _link("/commit/" + sha, sha[:7])
    else:
        source = "local"

    # Actions runners are UTC. Stamp Eastern so the number means something to a
    # human in Rochester rather than needing mental arithmetic at 4am.
    eastern = datetime.timezone(datetime.timedelta(hours=-4))
    when = datetime.datetime.now(datetime.timezone.utc).astimezone(eastern)
    stamp = when.strftime("%-d %b %Y, %-I:%M %p ET")

    config.copyright = (
        (config.copyright or "")
        + ' &middot; <span class="buildstamp">'
        + source
        + " &middot; "
        + stamp
        + "</span>"
    )
    return config
