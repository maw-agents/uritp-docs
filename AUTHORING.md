# Authoring reference

How to write pages for this site. **Deliberately outside `docs/`** so it never renders
as a reader-facing page: it documents the machine, not the theatre.

> ⚠️ **This file is CANONICAL.** If a rule here disagrees with the live config, the
> config wins and **this file gets corrected in the same pass**. Every file this
> describes carries a pointer back here, so a standards change and a doc change
> land in one PR or the pointer has failed.

**Describes:** `mkdocs.yml` · `requirements.txt` · `.github/workflows/deploy.yml` ·
`docs/.nav.yml` and per-folder `.nav.yml` · `docs/stylesheets/uritp.css` ·
`docs/stylesheets/links.css` · `hooks/links.py` · `hooks/buildstamp.py`

🔒 **Gates, keys and page visibility live in [AUTHORING-GATES.md](AUTHORING-GATES.md)**
(`hooks/visibility.py` + `docs/javascripts/gate.js`). Split out 2026-08-01: the gate
changed five times in twelve hours and re-emitting a 29KB file for each change is how a
section gets silently dropped. **Highest churn, smallest file.**

---

## Publication status — the short version

**Every page needs a `status:` line, or it inherits one, or it is hidden.**

| Status | Sidebar? | Direct link? | Search? | In the served HTML |
|---|---|---|---|---|
| `public` | **Yes** | Works | **Yes** | The real text |
| `gated` | **Yes** | Password box | Title only | Ciphertext |
| `unlisted` | No | **Works** | No | The real text |
| `hidden` | No | **404** | No | Nothing. Never built. |

```markdown
---
title: Smith Theatre
id: smith-theatre
status: public
---
```

⚠️ **`hidden` is *not published*. `unlisted` is *published without a signpost*** — an
unlisted URL forwarded in one email is public from then on.

**Everything else about gating** — the keystore, key groups, folder inheritance, the
session keyring, what the gate honestly protects, and how to verify a change actually
deployed — is in **[AUTHORING-GATES.md](AUTHORING-GATES.md)**. Read it before locking
anything.

---

## Adding a page

**Drop a `.md` file in the right folder under `docs/`. That is the entire procedure.**

The sidebar is generated from the file tree, so a `public` or `gated` page appears in
its section automatically, sorted alphabetically by filename.

```markdown
---
title: Rehearsal Studio
id: rehearsal-studio
status: hidden
---

# Rehearsal Studio

One line on what this space is and who uses it.
```

### Adding a folder

A new folder becomes a new sidebar section and lands at the bottom. Two optional files
shape it, and **neither is needed to make the pages appear**:

| To do this | Add |
|---|---|
| Place the section somewhere specific | its folder name in `docs/.nav.yml` |
| Set the section's displayed title | a `.nav.yml` **inside the folder**, holding `title: Todd Union` |
| Give the section a landing page | an `index.md` in the folder |

Without a folder `.nav.yml` the sidebar title-cases the folder name, producing `Spac`
for an acronym and `Todd union` with a lowercase U. That is the only reason to add one.

A folder's `index.md` becomes the page you land on when you click the section name
(`navigation.indexes`). Give it an `id:` like any other page — **and note that gating
it locks the whole folder** (see AUTHORING-GATES).

---

## Page anatomy

Frontmatter, one H1, one lede paragraph.

**One H1 per page**, always the page title. Two H1s break the right-hand outline.
Sections are `##`. Sub-points are `###`. Deeper than that means the page wants
splitting. The theme styles the **first paragraph after the H1** as lede text
automatically; do not try to make it big yourself.

### Which title shows where

Three surfaces read three different sources, which is why two pages can look
inconsistent without either being wrong:

| Surface | Reads |
|---|---|
| Sidebar entry, browser tab | frontmatter `title:` |
| The big heading on the page | the `# H1` in the body |
| Search result heading | the H1, falling back to `title:` |

So `title: safety test page` with `# Safety test page` gives a lowercase sidebar entry
and a capitalised page heading. **Keep them the same unless you mean it.** The
exception is a **gated** page, which has no H1 to show — the gate replaces the body, so
Material falls back to `title:`.

---

## Links

**A link points at a page's `id`, never at its file path.**

```markdown
[Smith Theatre](@smith-theatre)
[the venue notes](@smith-theatre#venue-notes)
```

No relative path to count, no `../`, and nothing about the link changes when the
target moves. `@smith-theatre` resolves at build time to wherever that page lives.

### Why, in one paragraph

On 2026-08-01 Smith Theatre moved from `docs/venues/` into `docs/venues/SPAC/`. That
single rename broke **eight links across six files**, in both directions. Because the
build runs `--strict`, the deploy died and the live site silently froze on an older
commit for over half an hour. Two rounds of hand-patching still missed three. Paths
encode where a page sits today, the one fact most likely to change.

### Declaring an id

Add `id:` to frontmatter. **Set it once and never change it** — that promise is the
entire mechanism. No `id:` is fine for a page nothing links to yet: the filename
stands in, and a folder's `index.md` takes the folder's name.

**House style: lowercase kebab-case**, matching the filename (`todd-lockup-procedure`,
not `Todd-Lock-up`). Capitals resolve fine, so this is convention rather than rule,
but an id is typed by hand in every link pointing at it.

### Linking to a heading

```markdown
## Venue notes {#venue-notes}

[the venue notes](@smith-theatre#venue-notes)
```

Without `{#...}` the anchor is generated from the heading **text**, so retitling breaks
every link into it, silently. The build reports those as `fragile-anchor`. Fix by
adding the explicit id, not by editing the links.

### When a page moves anyway

Ids keep *internal* links working. They cannot fix a bookmark, an email, a syllabus or
a QR code on a callboard. Record the retired address:

```markdown
aliases:
  - venues/smith-theatre     # lived here until 2026-08-01
```

The build writes a redirect at the old URL. An alias colliding with a real page is
skipped and reported rather than overwriting it.

---

## Backlinks — "Linked from"

**Every page automatically grows a `Linked from` section listing the pages that point
at it. You never write one and you cannot get one wrong.**

Because `hooks/links.py` resolves every internal link, it knows every link in reverse.
Link Safety → Smith Theatre once, and Smith Theatre gains a link back on its own.

- **Built from the source files, not render order**, so a link added on a page built
  later still registers.
- **Undiscoverable pages are never named as a source.** If a page is `unlisted` or
  carries `listed: false`, listing it on a public page is exactly the discovery it is
  avoiding. The one rule here you should not "fix".
- **Self-links are dropped.** The heading carries a stable `{#linked-from}` anchor.
- A page nothing links to has no section, and appears as an `orphan` in the link
  report. **Not an error** — a section landing page is reached from the sidebar.
- Kill switch: `URITP_BACKLINKS=0` in the build environment.

### Instant previews (desktop)

Hovering an internal link shows a card previewing the target. Enabled in `mkdocs.yml`
via `material.extensions.preview`, free as of Material 9.7 — which is why
`requirements.txt` floors there.

⚠️ **A desktop-only nicety, never the mechanism.** It fires on hover and focus, and
there is no hover on a phone. The thing that works everywhere is `Linked from`.

A preview over a `gated` link shows the unlock box, not the content: the preview
fetches the **built** page, which holds only the form plus ciphertext.

### What a broken link looks like

It does **not** fail the build. The link renders in red with a dashed underline and a
⚠ on that page only, and the reason appears in the link report — a table in the
Actions run summary, and `/link-report.json` on the live site.

| Report kind | Means |
|---|---|
| `dead-link` | Nothing carries that id, or the target is `hidden`. Includes a did-you-mean. |
| `legacy-path` | An old `path.md` link. Still resolved, but rewrite it as `@id`. |
| `fragile-anchor` | Deep link riding on heading text. Add `{#anchor}` to the heading. |
| `missing-anchor` | The anchor does not exist; the link lands at the top of the page. |
| `duplicate-id` | Two pages claim one id. The second is unreachable by id. |
| `alias-collision` | A retired URL is already a real page. Redirect skipped. |

**Never use a full `https://` URL for an internal page.** It works, which is the
problem: it dodges every check above and rots silently.

---

## Callouts

```markdown
!!! warning "Before you design"
    Smith is a blackbox with real constraints that will bite
    a design late if you learn them late.
```

**The body must be indented four spaces.** That indent is the whole trick.

| Type | Use for | Reads as |
|---|---|---|
| `warning` | Anything that costs money or hurts someone | Amber |
| `note` | Context, gaps, placeholders | Purple |
| `danger` | A genuine safety stop | Red |

**Resist inventing more.** Four callout colors on one page means none read as urgent.

⚠️ **The GitHub web editor sometimes collapses that four-space indent to one** when you
edit a line next to it. The body then falls silently out of the box. If a callout looks
wrong after a phone edit, check the indent first.

---

## Department tabs

```markdown
=== "Lighting"

    All catwalk fixtures are yoked at **45 degrees**.
```

Body indented four spaces, blank line between tabs. **When the page is printed, all
tabs stack** so nothing is lost on paper.

**Keep labels identical across pages:** General staging · Scenic · Lighting · Audio ·
Directors. A reader who picks Lighting on one page gets Lighting on the next, but only
if the label matches character for character.

---

## Tables and the unconfirmed marker

```markdown
| Item | Value |
|---|---|
| Grid height | [To be confirmed]{.tbc} |
```

**`[To be confirmed]{.tbc}`** renders as an amber pill. Use it instead of guessing,
and instead of leaving the row out. A missing row reads as "there is nothing to know
here." An unconfirmed row reads as "measure this before you draft it," which is true.

---

## Text

Standard markdown. **Blank line between every block** (paragraphs, lists, headings,
tables). That one rule prevents most formatting surprises.

---

## The footer build stamp

```
University of Rochester International Theatre Program · PR #19
```

**The only signal that a build failed.** When one does, Pages keeps serving the
previous commit: no banner, no error page, the site simply stops changing. A footer
showing a PR older than your edit means your change is not live.

The **deploy time** lives in the stamp's `title` attribute: hover on desktop, or read
the source. ~~It used to sit on the face of the footer~~ and was moved 2026-08-01.

⚠️ **A PR number only reads as stale if you know the current one.** When a build looks
suspicious, check the [Actions runs](https://github.com/maw-agents/uritp-docs/actions).
And **the stamp itself can be cached** — add `?x=1` to the URL before concluding
anything (see AUTHORING-GATES → *Verifying a visibility change*).

---

## What breaks the build

The list is deliberately short and keeps getting shorter. **Neither a broken link nor a
missing gate key is on it**: both used to take the whole site stale over one page, and
both now fail locally and loudly instead.

| # | Failure | Fails the deploy? | Why |
|---|---|---|---|
| 1 | Callout or tab body not indented four spaces | No, renders wrong | Content falls out of the box. |
| 2 | Link to a missing, moved, or `hidden` page | **No, as of 2026-08-01** | Dead-link marker + link report. |
| 3 | `status: gated` with no password at all | **No, as of 2026-08-01** | Content dropped; page shows an unavailable notice. |
| 4 | `gates:` naming a group not in the keystore | **No, as of 2026-08-01** | Same. Run summary lists the groups that DO exist. |
| 5 | No blank line before a table or list | No | Renders as one mashed paragraph. |
| 6 | Two H1s on a page | No, renders wrong | Breaks the outline and the page title. |
| 7 | Missing `status:` with no gated ancestor | No | The page silently will not build. |
| 8 | Lowering `mkdocs-material` below 9.7 | **Yes** | `material.extensions.preview` does not exist there. |
| 9 | A workflow change that trips an approval gate | **Worse than Yes** | Reports `action_required` with zero jobs and never deploys. **Every PR now runs a build check** so this is caught on a branch. |

---

## The loop

No git, no terminal, nothing installed. Works from a phone.

1. Open the page on the live site, click the **pencil icon**.
2. Edit the markdown. Commit.
3. Wait about ninety seconds.
4. **Check the footer stamp.** If it is not your edit, the build failed.
5. If the page looks unchanged but the stamp is current, **add `?x=1` to the URL**.
   You were reading a cache.

---

## Changing the standards themselves

If you change any file this document describes, **update this file in the same PR**.

| File | Holds | Update here when |
|---|---|---|
| `mkdocs.yml` | Theme, features, extensions, hook order | An extension, plugin, or hook is added or removed |
| `requirements.txt` | Build dependency floors | A floor moves, or a pinned feature changes |
| `.github/workflows/deploy.yml` | The keystore wiring + the PR build check | The keystore mechanism changes → **AUTHORING-GATES too** |
| `docs/.nav.yml` | Top-level sidebar order | The add-a-page procedure changes |
| `docs/<folder>/.nav.yml` | That section's displayed title | The per-folder title mechanism changes |
| `docs/stylesheets/uritp.css` | Palette, headings, `.tbc`, `.gate`, print | A custom class is added, renamed, or dropped |
| `docs/stylesheets/links.css` | The `.deadlink` marker | The marker is restyled or renamed |
| `hooks/links.py` | `@id` resolution, backlinks, aliases, link report | Link syntax, a report kind, or backlink rules change |
| `hooks/buildstamp.py` | The footer stamp | What the stamp shows changes |
| **`hooks/visibility.py`** | Status, the keystore, encryption | → **[AUTHORING-GATES.md](AUTHORING-GATES.md)**, not here |
| **`docs/javascripts/gate.js`** | Browser-side unlock, the keyring | → **[AUTHORING-GATES.md](AUTHORING-GATES.md)**, not here |

A syntax rule described here with no extension behind it is worse than no
documentation: it teaches something that silently renders as literal text. A status
value the hook does not recognise is worse still: the page falls back to `hidden` and
quietly disappears.

**Hook order in `mkdocs.yml` is load-bearing.** `visibility.py` resolves status and
drops `hidden` pages before `links.py` builds its id registry.
