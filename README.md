# URITP Production Resources

Markdown source for the URITP production documentation site.

**Live site:** https://maw-agents.github.io/uritp-docs/

## What this is

Venue information, technical standards, and production reference for designers,
guest artists, and students. Write markdown, commit, and the site rebuilds itself.

## Writing pages

**[AUTHORING.md](AUTHORING.md) is the full reference:** callouts, department tabs, the
unconfirmed marker, links, and what breaks the build. Read it before writing a page.

The short version: **drop a `.md` file in the right folder under `docs/`.** The sidebar
is generated from the file tree, so the page appears in its section automatically.
Nothing to register.

```markdown
---
title: Rehearsal Studio
---

# Rehearsal Studio
```

A new **folder** becomes a new sidebar section at the bottom. Add its name to
`docs/.nav.yml` to place it somewhere specific.

## Editing an existing page

1. Click the **edit pencil** in the page header on the live site. Phone is fine.
2. Edit the markdown. Commit.
3. Wait about 90 seconds. Actions rebuilds and redeploys.

## Repo shape

```
AUTHORING.md                  how to write pages (canonical)
mkdocs.yml                    site config (the theme swap point)
docs/.nav.yml                 sidebar order and section titles
docs/stylesheets/uritp.css    the URITP theme layer
.github/workflows/deploy.yml  build and deploy on every push to main
requirements.txt              pinned build dependencies
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

`mkdocs.yml`, `docs/.nav.yml`, and `docs/stylesheets/uritp.css` each carry a **pointer
comment** at the top: change one, update `AUTHORING.md` in the same PR. A syntax rule
with no extension behind it teaches something that renders as literal text.

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
access. If genuinely private reads are ever needed, the answer is Cloudflare Access in
front of the Pages URL, not a private repo.
