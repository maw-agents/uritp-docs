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

## Repo shape

```
mkdocs.yml                    site config + navigation (the theme swap point)
.github/workflows/deploy.yml  build and deploy on every push to main
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

## Adding a page

Drop a new `.md` file in the right folder, then add one line to `nav:` in `mkdocs.yml`.
The build runs `--strict`, so a nav entry pointing at a file that does not exist
fails loudly instead of shipping a broken link.

## Access

Public repo, public site. Reads are open to anyone with the link; writes require
repo access. If genuinely private reads are ever needed, the answer is Cloudflare
Access in front of the Pages URL, not a private repo.
