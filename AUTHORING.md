# Authoring reference

How to write pages for this site. **Deliberately outside `docs/`** so it never renders
as a reader-facing page: it documents the machine, not the theatre.

> ⚠️ **This file is CANONICAL.** If a rule here disagrees with the live config, the
> config wins and **this file gets corrected in the same pass**. Every file this
> describes carries a pointer back here, so a standards change and a doc change
> land in one PR or the pointer has failed.

**Describes:** `mkdocs.yml` · `requirements.txt` · `.github/workflows/deploy.yml` ·
`docs/.nav.yml` and per-folder `.nav.yml` · `hooks/links.py` · `hooks/buildstamp.py` ·
`hooks/sizecheck.py` + `size-budget.tsv`

🔒 **Gates, keys and page visibility live in [AUTHORING-GATES.md](AUTHORING-GATES.md)**
(`hooks/visibility.py` + `docs/javascripts/gate.js`).

🎨 **Theme, colour, type, chrome and search behaviour live in
[AUTHORING-LOOK.md](AUTHORING-LOOK.md)** (`theme/` + `hooks/theme.py` +
`hooks/pagefoot.py` + `docs/stylesheets/`).

📐 **Why a given CSS rule exists lives in [CSS-NOTES.md](CSS-NOTES.md)**, one section
per numbered stylesheet.

All three were split out for the same reason: there is no partial-edit path
through this toolchain, so every change re-emits the whole file, and a 29KB canonical
document rewritten five times in a day is five chances to silently drop a section.
**Highest churn, smallest file.**

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

⚠️ **A folder with no `index.md` is a toggle, not a link.** Since 2026-08-01 the
sidebar is **collapsed by default**, so clicking a section name opens or closes it;
only a folder carrying an `index.md` also goes somewhere. If a section keeps getting
clicked in the hope of a landing page, that is the fix — add the `index.md`. The
reasoning is in CSS-NOTES → *80 Mobile → Desktop-only changes*.

---

## Page anatomy

Frontmatter, one H1, one lede paragraph.

**One H1 per page**, always the page title. Two H1s break the right-hand outline.
Sections are `##`. Sub-points are `###`. Deeper than that means the page wants
splitting. The theme styles the **first paragraph after the H1** as lede text
automatically; do not try to make it big yourself.

⭐ **That lede is also what the search result shows.** It is not decoration and it is
not optional. See AUTHORING-LOOK → *What the search result says*.

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
exception is a **gated** page: while it is locked it has no H1 to show, so Material
falls back to `title:`. Unlock it and the authored H1 takes over. Keeping the two
spellings identical is what stops the heading appearing to change as you unlock.

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
build ran `--strict`, the deploy died and the live site silently froze on an older
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

⚠️ ~~Instant previews (`material.extensions.preview`) show a hover card of the target
page on desktop.~~ **Removed 2026-08-01.** It attached to every internal link
including the navigation, on a site read mostly from a phone, where hover does not
exist and the preview can never fire. `Linked from` is the mechanism that works
everywhere. ⚠️ It was ALSO blamed for the nav icons, wrongly — see CSS-NOTES → *20
Chrome*.

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

⚠️ **NONE OF THE SYNTAX ON THIS PAGE IS MARKDOWN.** `!!!` comes from the `admonition`
extension, `???` from `pymdownx.details`, `===` from `pymdownx.tabbed` and `{.tbc}`
from `attr_list` — four lines in `mkdocs.yml`, all of which can be switched off. Paste
any of it into a plain renderer (a GitHub preview, a phone notes app, an email) and it
comes out as literal punctuation. **This is the site's dialect, not a portable format.**

### The word after the marker is never checked

The extension does not validate the type. It lowercases whatever you typed and passes
it through as a CSS class, so `!!! wanring` builds clean and renders as an unstyled
default box: **no error, no warning, no report line.** A misspelled callout looks like
a deliberately plain one. That is why the list below is short and closed by
convention — nothing in the build can enforce it.

| Type | Use for | Reads as |
|---|---|---|
| `warning` | Anything that costs money or hurts someone | Amber |
| `note` | Context, gaps, placeholders | The theme accent |
| `danger` | A genuine safety stop | Red |

**Resist inventing more.** Four callout colors on one page means none read as urgent.

⚠️ **`success`, `tip` and `question` are wired but have never been used.** All three
render in the `good` green from `theme/colors.tsv`. **No page on this site writes one**,
so that whole colour column ships unseen and its two rows in `theme/contrast.tsv` are
still first-draft guesses rather than measured numbers. Writing the first one is what
turns those two warnings into a real reading.

### Collapsible callouts

```markdown
??? note "Full rigging plot"
    Folded away until somebody asks for it.

???+ note "Load-in times"
    The same box, but it opens expanded.
```

**`???` folds shut. `???+` starts open.** Every type, colour and the four-space indent
are identical to `!!!` — the only change is that the title bar becomes a toggle.

Use it for bulk a page must *contain* but should not have to *show*: a full fixture
inventory, a procedure a returning reader already knows, a dimension table under the
paragraph that summarises it.

⚠️ **Never fold a `warning` or a `danger`.** A safety stop behind a click is a safety
stop nobody read. Collapse detail, never consequence.

⚠️ **Folding is not hiding.** The text is in the HTML either way, so a folded callout
is fully in the search index and readable in the page source. To actually withhold
content, see AUTHORING-GATES.

⚠️ **UNVERIFIED — check before folding anything that matters on paper.** A browser
prints a closed `<details>` closed. The print block forces *tabs* open; whether it does
the same for a folded callout has not been tested, and a venue page carried into a
production meeting is exactly the case that must not lose content. Logged in
`next-build-spec.md`.

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
URITP | MAW · PR #19
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

## The size gate

**`hooks/sizecheck.py` measures every file in the repo against `size-budget.tsv` and
fails the build on anything nobody can read whole.** Same shape as the contrast gate:
the maths is in the hook, the policy is a row you can edit.

It exists because `docs/stylesheets/uritp.css` reached 34.9KB and started clipping
silently on read, so its last ~6KB was being edited blind. **The cap was already a
rule; it was enforced by whoever happened to notice.** Now it is enforced by the build.

- **A warning** means the file wants splitting before it has to. Nothing breaks.
- **A failure** stops the build and names the file, its size, and its budget.
- Raise a threshold by editing its row and **saying why in the note column**, so the
  waiver shows up in a diff. `URITP_SIZE_STRICT=1` promotes every warning to a failure.
- Authored pages under `docs/` get a generous budget and in practice only ever warn. A
  gate that blocks a long venue page is a gate that gets switched off.

⚠️ **The fail number is a policy line, not a measured wall.** What has been observed:
a 30.6KB file read back whole, and a 34.9KB file clipped. The thresholds sit below the
lower of those on purpose. If anyone narrows that range, correct the hook's docstring.

---

## Stylesheets

Seven numbered sheets in `docs/stylesheets/`, one concern each, listed in cascade order
under `extra_css`. **The numbers ARE the order and reordering the list is a silent
restyle.**

| Sheet | Owns |
|---|---|
| `00-bridge.css` | our tokens → Material's variables; the focus ring |
| `10-type.css` | the prose scale |
| `20-chrome.css` | header, tab strip, desktop sidebar |
| `30-content.css` | tables, `.tbc`, callouts and their flavours, department tabs |
| `40-components.css` | links, the gate, the page foot, the build stamp |
| `links.css` | `@page-id` link states (`hooks/links.py`) |
| `80-mobile.css` | every breakpoint, both of them |
| `90-print.css` | paper. **Must load last.** |

**Three layers, deliberately apart:** values in `theme/*.tsv`, rules in the sheets,
reasons in [CSS-NOTES.md](CSS-NOTES.md). Split out of one 34.9KB file on 2026-08-02.

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
| 8 | Lowering `mkdocs-material` below 9.7 | No, **as of 2026-08-01** | It was a hard failure while `material.extensions.preview` was enabled; that extension is gone. The floor stays because below it is missing features for no gain. |
| 9 | A workflow change that trips an approval gate | **Worse than Yes** | Reports `action_required` with zero jobs and never deploys. **Every PR now runs a build check** so this is caught on a branch. |
| 10 | An `active:` theme, a vector row, or a token that does not resolve | **Yes, deliberately** | A theme has no single page to fail on, and a silent fallback to the wrong design is the invisible failure this repo's other rules exist to prevent. Caught on the branch. See AUTHORING-LOOK. |
| 11 | The ACTIVE palette failing an enforced contrast pair | **Yes** | `hooks/contrast.py`. A parked palette only warns. |
| 12 | A source file over its row in `size-budget.tsv` | **Yes, as of 2026-08-02** | `hooks/sizecheck.py`. A file nobody can read whole is a file nobody can safely edit. |
| 13 | A misspelled callout or tab type | No, renders plain | Not validated anywhere. See *Callouts* above. |

---

## The loop

No git, no terminal, nothing installed. Works from a phone.

1. Open the page on the live site, scroll to the bottom, click **Edit this page on
   GitHub**.
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
| `mkdocs.yml` | Features, extensions, hook order, `extra_css` order | An extension, plugin, or hook is added or removed |
| `requirements.txt` | Build dependency floors | A floor moves, or a pinned feature changes |
| `.github/workflows/deploy.yml` | The keystore wiring + the PR build check | The keystore mechanism changes → **AUTHORING-GATES too** |
| `docs/.nav.yml` | Top-level sidebar order | The add-a-page procedure changes |
| `docs/<folder>/.nav.yml` | That section's displayed title | The per-folder title mechanism changes |
| `hooks/links.py` | `@id` resolution, backlinks, aliases, link report | Link syntax, a report kind, or backlink rules change |
| `hooks/buildstamp.py` | The footer stamp | What the stamp shows changes |
| **`hooks/sizecheck.py`** | The size gate | The mechanism changes. A THRESHOLD move is a `size-budget.tsv` row + its note, and needs nothing here |
| **`size-budget.tsv`** | Per-glob read-size budgets | A new kind of file needs a row, or the catch-all starts matching things |
| **`theme/*.tsv`** | The five vectors + the join table | → **[AUTHORING-LOOK.md](AUTHORING-LOOK.md)** and `theme/README.md`, not here |
| **`hooks/theme.py`** | Token composition + validation | → **[AUTHORING-LOOK.md](AUTHORING-LOOK.md)**, not here |
| **`hooks/contrast.py`** | The contrast gate | → **[AUTHORING-LOOK.md](AUTHORING-LOOK.md)**, not here |
| **`hooks/pagefoot.py`** | The page-foot edit link | → **[AUTHORING-LOOK.md](AUTHORING-LOOK.md)**, not here |
| **`docs/stylesheets/*`** | Every rule on the site | → **[CSS-NOTES.md](CSS-NOTES.md)** for the reasoning — **except** a renamed author-typed class like `.tbc`, which belongs in both, and a NEW SHEET, which needs its line in `extra_css` and its row in the table above |
| **`hooks/visibility.py`** | Status, the keystore, encryption | → **[AUTHORING-GATES.md](AUTHORING-GATES.md)**, not here |
| **`docs/javascripts/gate.js`** | Browser-side unlock, the keyring | → **[AUTHORING-GATES.md](AUTHORING-GATES.md)**, not here. DOM-only changes go to AUTHORING-LOOK. |

A syntax rule described here with no extension behind it is worse than no
documentation: it teaches something that silently renders as literal text. A status
value the hook does not recognise is worse still: the page falls back to `hidden` and
quietly disappears.

⚠️ **AND THE INVERSE HAPPENED, 2026-08-01: an extension with no syntax behind it.**
The stylesheet carried a full set of `details`/`summary` rules — box, title bar, body
inset — for a component **no author could produce**, because `pymdownx.details` was
never enabled. Anyone typing `???` got three question marks. The CSS looked used and
the syntax looked supported, and neither was true. **Check both directions: a rule
without syntax is as invisible as syntax without a rule.**

**Hook order in `mkdocs.yml` is load-bearing for three of the eight.** `visibility.py`
resolves status and drops `hidden` pages before `links.py` builds its id registry, and
`pagefoot.py` appends after `links.py` so the edit link lands below `Linked from`.
`theme.py` must precede `contrast.py`, which imports it. `sizecheck.py`, `theme.py` and
`buildstamp.py` touch neither the file list nor the page body, so their position does
not matter — `sizecheck.py` is listed first only so an unreadable file stops the build
before a full render rather than after one.
