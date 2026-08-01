# URITP Production Resources

Markdown source for the URITP production documentation site.

**Live site:** https://maw-agents.github.io/uritp-docs/

## What this is

Venue information, technical standards, and production reference for designers,
guest artists, and students. Write markdown, commit, and the site rebuilds itself.

## Writing pages

**[AUTHORING.md](AUTHORING.md) is the full reference:** publication states, callouts,
department tabs, the unconfirmed marker, links, and what breaks the build. Read it
before writing a page.

The short version: **drop a `.md` file in the right folder under `docs/`.** The sidebar
is generated from the file tree, so the page appears in its section automatically.
Nothing to register.

```markdown
---
title: Rehearsal Studio
status: hidden
---

# Rehearsal Studio
```

Every page needs a `status:` line or it will not build. A new **folder** becomes a new
sidebar section at the bottom; add its name to `docs/.nav.yml` to place it.

## Editing an existing page

1. Click the **edit pencil** in the page header on the live site. Phone is fine.
2. Edit the markdown. Commit.
3. Wait about 90 seconds. Actions rebuilds and redeploys.

## Changing the look

Everything visual lives in `docs/stylesheets/uritp.css`. The palette is six OKLCH
values at the top; change those and the whole site follows. Keep the `@import` on
line 1: CSS silently drops an `@import` that follows any other rule.

## Repo shape

```
AUTHORING.md                  how to write pages (canonical)
mkdocs.yml                    site config (the theme swap point)
requirements.txt              pinned build dependencies
hooks/visibility.py           the `status:` gate + page encryption
.github/workflows/deploy.yml  build and deploy on every push to main
docs/.nav.yml                 sidebar order and section titles
docs/stylesheets/uritp.css    the URITP theme layer
docs/javascripts/gate.js      browser-side unlock for gated pages
docs/
  index.md                    landing page
  using-these-docs.md         orientation for readers
  venues/                     one file per space
  production/                 standards and paperwork
  safety/                     safety and health
  reference/                  revision history, contacts
```

`AUTHORING.md` sits outside `docs/` on purpose: it documents the machine, not the
theatre, and readers of the site should never land on it.

## Changing the standards

`mkdocs.yml`, `docs/.nav.yml`, `docs/stylesheets/uritp.css`, and `hooks/visibility.py`
each carry a **pointer comment** at the top: change one, update `AUTHORING.md` in the
same PR. A syntax rule with no extension behind it teaches something that renders as
literal text.

`hooks/visibility.py` and `docs/javascripts/gate.js` share the cipher and iteration
count. Change one alone and gated pages stop unlocking with no readable error.

## Swapping the theme

Change `theme.name` in `mkdocs.yml`. Content files are untouched by a theme swap,
which is the entire point of keeping them as plain markdown. `uritp.css` carries the
URITP look on top of whichever theme is active; it targets Material's CSS custom
properties, so a swap means rewriting that one file, not the docs.

## Builds

The build runs `mkdocs build --strict`, so a link pointing at a file that does not
exist fails the deploy instead of shipping a dead link. A red X in Actions names the
offending file.

## Access

Public repo, public site. Reads are open to anyone with the link; writes require repo
access. Publication states (`hidden`, `unlisted`, `gated`) control what reaches the
**site**, not what is readable in this repo. See AUTHORING.md for the honest limits and
what it would take to make the gate real.
