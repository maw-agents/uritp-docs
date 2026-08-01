# URITP Production Resources

Markdown source for the URITP production documentation site.

**Live site:** https://maw-agents.github.io/uritp-docs/

## What this is

Venue information, technical standards, and production reference for designers,
guest artists, and students. Write markdown, commit, and the site rebuilds itself.

## How to change something

1. Open the `.md` file under `docs/`. The web editor on GitHub is fine, phone included.
2. Commit to `main`.
3. Wait about 90 seconds. The Actions workflow rebuilds and redeploys.

Every page on the live site has an **edit pencil** in its header that drops you
straight into the right file.

## Adding a page

**Drop a `.md` file in the right folder. That is the whole procedure.**

The sidebar is generated from the file tree, so a new page appears in its section
automatically, sorted alphabetically by filename. Give it frontmatter and an H1:

```markdown
---
title: Rehearsal Studio
---

# Rehearsal Studio
```

A new **folder** becomes a new sidebar section and appears at the bottom. To place
it somewhere specific, add its name to `docs/.nav.yml`. That file controls order
and section titles, and it is the only navigation file in the repo.

## Repo shape

```
mkdocs.yml                    site config (the theme swap point)
docs/.nav.yml                 sidebar order and section titles
.github/workflows/deploy.yml  build and deploy on every push to main
requirements.txt              pinned build dependencies
docs/
  index.md                    landing page
  using-these-docs.md         orientation for new readers
  stylesheets/uritp.css       the URITP theme layer
  venues/                     one file per space
  production/                 standards and paperwork
  safety/                     safety and health
  reference/                  revision history, contacts
```

## Swapping the theme

Change `theme.name` in `mkdocs.yml`. Content files are untouched by a theme swap,
which is the entire point of keeping them as plain markdown. `docs/stylesheets/uritp.css`
carries the URITP look on top of whichever theme is active; it targets Material's
CSS custom properties, so a swap means rewriting that one file, not the docs.

## Builds

The build runs `mkdocs build --strict`, so a link pointing at a file that does not
exist fails the deploy instead of shipping a dead link. A red X in Actions names
the offending file.

## Access

Public repo, public site. Reads are open to anyone with the link; writes require
repo access. If genuinely private reads are ever needed, the answer is Cloudflare
Access in front of the Pages URL, not a private repo.
