# URITP Production Resources

Markdown source for the URITP production documentation site.

**Live site:** https://maw-agents.github.io/uritp-docs/

## What this is

Venue information, technical standards, and production reference for designers,
guest artists, and students. Write markdown, commit, and the site rebuilds itself.

## Writing pages

**[AUTHORING.md](AUTHORING.md) is the full reference:** publication states, links,
callouts, department tabs, the unconfirmed marker, and what breaks the build. Read it
before writing a page.

The short version: **drop a `.md` file in the right folder under `docs/`.** The sidebar
is generated from the file tree, so the page appears in its section automatically.
Nothing to register.

```markdown
---
title: Rehearsal Studio
id: rehearsal-studio
status: hidden
---

# Rehearsal Studio
```

Every page needs a `status:` line or it will not build. A new **folder** becomes a new
sidebar section at the bottom; add its name to `docs/.nav.yml` to place it, and a
`.nav.yml` inside the folder to set its displayed title.

## Linking between pages

**Links name a page's `id`, never its file path.**

```markdown
[Smith Theatre](@smith-theatre)
[the venue notes](@smith-theatre#venue-notes)
```

Moving the file, renaming its folder, or retitling the page cannot break that link,
because none of those are what it points at. Set `id:` once in frontmatter and never
change it. Full rules, including heading anchors and retired-URL redirects, are in
[AUTHORING.md](AUTHORING.md#links).

## Editing an existing page

1. Click the **edit pencil** in the page header on the live site. Phone is fine.
2. Edit the markdown. Commit.
3. Wait about 90 seconds. Actions rebuilds and redeploys.
4. **Check the footer stamp.** If it is not your PR or push, the build failed.

## Changing the look

Everything visual lives in `docs/stylesheets/uritp.css`. The palette is a set of OKLCH
values at the top of each scheme block; change those and the whole site follows.

⚠️ **Chrome color is `theme.palette` in `mkdocs.yml`, not the stylesheet.** Setting
`--md-primary-fg-color` in an unscoped `:root` hits both schemes and breaks the dark
toggle.

## Repo shape

```
AUTHORING.md                  how to write pages (canonical)
mkdocs.yml                    site config (the theme swap point)
requirements.txt              pinned build dependencies
hooks/visibility.py           the `status:` gate + page encryption
hooks/links.py                @page-id resolution, link report, redirects
hooks/buildstamp.py           footer PR number + deploy time
.github/workflows/deploy.yml  build and deploy on every push to main
docs/.nav.yml                 top-level sidebar order
docs/stylesheets/uritp.css    the URITP theme layer
docs/stylesheets/links.css    the dead-link marker
docs/javascripts/gate.js      browser-side unlock for gated pages
docs/_TEMPLATE.md             starter page, every block prepped
docs/
  index.md                    landing page
  using-these-docs.md         orientation for readers
  venues/                     one folder per building, one file per space
  production/                 standards and paperwork
  safety/                     safety and health
  reference/                  revision history, contacts
```

`AUTHORING.md` sits outside `docs/` on purpose: it documents the machine, not the
theatre, and readers of the site should never land on it.

## Changing the standards

`mkdocs.yml`, `docs/.nav.yml`, both stylesheets, and both content hooks each carry a
**pointer comment** at the top: change one, update `AUTHORING.md` in the same PR. A
syntax rule with no extension behind it teaches something that renders as literal text.

`hooks/visibility.py` and `docs/javascripts/gate.js` share the cipher and iteration
count. Change one alone and gated pages stop unlocking with no readable error.

**Hook order in `mkdocs.yml` is load-bearing.** `visibility.py` drops hidden pages
before `links.py` indexes them; reversed, a link to a hidden page would resolve to a
URL that 404s.

## Swapping the theme

Change `theme.name` in `mkdocs.yml`. Content files are untouched by a theme swap,
which is the entire point of keeping them as plain markdown. `uritp.css` carries the
URITP look on top of whichever theme is active; it targets Material's CSS custom
properties, so a swap means rewriting that one file, not the docs.

## Builds

The build runs `mkdocs build --strict`. ~~A link pointing at a file that does not
exist fails the deploy.~~ **Changed 2026-08-01:** a broken internal link now renders as
a visible marker on that page and appears in the build's link report, and the deploy
continues. One typo used to freeze the entire site, twice in forty minutes, while Pages
kept serving a stale commit.

Every build publishes `/link-report.json` and writes a Link report table into the
Actions run summary: dead links, legacy path-based links, fragile heading anchors,
duplicate ids, and skipped redirects.

**A failed build is silent on the live site.** No banner, no error page: it just stops
updating. The footer stamp is the signal.

## Access

Public repo, public site. Reads are open to anyone with the link; writes require repo
access. Publication states (`hidden`, `unlisted`, `gated`) control what reaches the
**site**, not what is readable in this repo. See AUTHORING.md for the honest limits and
what it would take to make the gate real.
