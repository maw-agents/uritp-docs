"""
Page foot: the edit link.

One quiet text link at the bottom of every page::

    ------------------------------------------
    Edit this page on GitHub

WHY IT MOVED (2026-08-01, Michael)
Material's ``content.action.edit`` puts a pencil icon at the TOP RIGHT of every
page, level with the title. That reads as an invitation -- this document is
editable, have a go -- on a site whose whole job is to be the settled answer.
There is exactly one editor. The affordance he needs is a way back to the
source when he is already finished reading, not a button competing with the
heading.

So the theme feature is OFF and this renders the link at the foot instead.

IT ALSO FIXES A REAL DEFECT, which is why it is a link with WORDS and not a
smaller icon. The pencil was an anchor with no text and no label: fetched live
on 2026-08-01 it came back as an empty link wrapping only the edit URL. A
screen reader announces the address. "Edit this page on GitHub" is
self-describing, works without the icon font, and survives being read aloud.

WHAT IT IS NOT
Not a second build stamp -- that is ``buildstamp.py``, in the site footer, and
it answers a different question (is this page current, rather than where does
it live). Not a byline. Not a last-edited date: git already knows, and a date
rendered here would be one more thing to go stale.

``page.edit_url`` is computed by MkDocs from ``repo_url`` + ``edit_uri`` in
mkdocs.yml, so it stays correct if the repo moves. A page with no edit_url --
an alias redirect stub, anything generated -- simply gets no link rather than a
broken one.

Kill switch: ``URITP_EDITLINK=0`` in the build environment.

Wired in mkdocs.yml under ``hooks:``, AFTER links.py so the link lands below
the ``Linked from`` section. Documented in AUTHORING-LOOK.md.
"""

import os

LABEL = "Edit this page on GitHub"


def on_page_content(html, page, config, files):
    if os.environ.get("URITP_EDITLINK") == "0":
        return html

    url = getattr(page, "edit_url", None)
    if not url:
        return html

    return (
        html
        + '<hr class="pagefoot__rule">'
        '<p class="pagefoot">'
        '<a class="pagefoot__edit" href="' + url + '">' + LABEL + "</a>"
        "</p>"
    )
