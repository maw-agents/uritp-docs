"""
Footer build stamp.

Prints the PULL REQUEST the live site was built from, so any page answers "is
what I am looking at the latest push?" without opening Actions. PR numbers only
ever go up, so a stamp that has not moved is the fastest possible signal that a
build failed and the site is frozen on an older commit.

House standard, carried over from the ClickUp app builds: the stamp is a quiet
pointer, not a changelog. One token, linked. No timestamp, no SHA.

The number is parsed from the head commit SUBJECT, which the workflow passes in
as BUILD_COMMIT_MESSAGE:

    squash merge   "fix: repair the venue links (#16)"        -> PR #16
    merge commit   "Merge pull request #16 from maw-agents/x" -> PR #16
    direct push    "Update todd-theatre.md"                   -> short SHA

The fallback is load-bearing, not a nicety: most edits to this repo are made
from the GitHub UI edit pencil and never see a branch, so a stamp that could
only render a PR number would be blank most of the time.

Only the subject line is read. A commit body that happens to mention another
issue number must not win.

Works by extending `copyright` at config time rather than overriding Material's
footer template: one small hook, no theme override to maintain across upgrades.

Wired in mkdocs.yml under `hooks:`. Documented in README.md.
"""

import os
import re

REPO = "https://github.com/maw-agents/uritp-docs"

_PR = re.compile(r"#(\d+)")


def _link(href, label):
    return '<a href="' + REPO + href + '">' + label + "</a>"


def on_config(config):
    lines = os.environ.get("BUILD_COMMIT_MESSAGE", "").strip().splitlines()
    found = _PR.findall(lines[0]) if lines else []

    if found:
        stamp = _link("/pull/" + found[-1], "PR #" + found[-1])
    else:
        sha = os.environ.get("GITHUB_SHA", "")
        stamp = _link("/commit/" + sha, sha[:7]) if sha else "local"

    config.copyright = (
        (config.copyright or "")
        + ' &middot; <span class="buildstamp">'
        + stamp
        + "</span>"
    )
    return config
