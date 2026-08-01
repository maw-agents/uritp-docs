"""
Footer build stamp.

Appends the build time and the short commit SHA to the site footer, so any page
answers "is what I am looking at actually the latest deploy?" without opening
Actions. A stale stamp is the fastest possible signal that a build failed and
the site is frozen on an older commit.

Works by extending `copyright` at config time rather than overriding Material's
footer template: one small hook, no theme override to maintain across upgrades.

GITHUB_SHA is set by Actions. Local builds fall back to "local".

Wired in mkdocs.yml under `hooks:`. Documented in README.md.
"""

import datetime
import os

REPO = "https://github.com/maw-agents/uritp-docs"


def on_config(config):
    sha = os.environ.get("GITHUB_SHA", "")
    short = sha[:7] if sha else "local"

    # Actions runners are UTC. Stamp Eastern so the number means something to a
    # human in Rochester rather than needing mental arithmetic at 4am.
    eastern = datetime.timezone(datetime.timedelta(hours=-4))
    when = datetime.datetime.now(datetime.timezone.utc).astimezone(eastern)
    stamp = when.strftime("%d %b %Y, %-I:%M %p ET")

    build = (
        '<span class="buildstamp">Built ' + stamp + " &middot; "
        + (
            '<a href="' + REPO + "/commit/" + sha + '">' + short + "</a>"
            if sha else short
        )
        + "</span>"
    )

    config.copyright = (config.copyright or "") + " &middot; " + build
    return config
