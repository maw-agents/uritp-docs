# Look and feel reference

How this site's **chrome** behaves and how **search** decides what to show.
Companion to [AUTHORING.md](AUTHORING.md) (writing pages) and
[AUTHORING-GATES.md](AUTHORING-GATES.md) (visibility and keys).

> ## 🎨 Changing colours, type, edges or density? Not here.
>
> **→ [`theme/README.md`](theme/README.md)**
>
> The four vectors are TSV grids in [`theme/`](theme/). Swap the whole site by
> editing one word in [`theme/active.txt`](theme/active.txt). Nudge one value
> by editing one cell. This file used to explain all of that and now points at
> it instead: **one place, referenced, never restated.** A copy of a value is a
> copy that rots, and this document proved that twice on 2026-08-01.

**This file describes:** `docs/stylesheets/uritp.css` · `docs/stylesheets/links.css`
· `hooks/pagefoot.py` · the `theme:` and `extra:` blocks in `mkdocs.yml`

> ⚠️ **Split out of AUTHORING.md 2026-08-01, for the reason the gate reference
> was.** There is no partial-edit path through this toolchain, so every change
> re-emits the whole file. A 20KB document rewritten five times in a day is
> five chances to silently drop a section. Highest churn, smallest file.

---

## Editing the stylesheet

`docs/stylesheets/uritp.css` contains **no colour, no font name, no size and no
radius.** Every value is a `--u-*` token composed from `theme/`.

⚠️ **A literal value committed there silently opts that element out of every
future swap.** The build fails by name when a palette forgets a token; it
cannot detect a stylesheet that stopped asking for one. If you need a value
with no token, add the column to the right grid in `theme/` **and** its name to
`REQUIRED` in `hooks/theme.py`, in the same PR. `chrome` is the worked example:
it did not exist until Michael asked where the one line for the header banner
was, and the honest answer was that there wasn't one.

The file has one **bridge** block at the top mapping `--u-*` onto Material's
`--md-*` variables. That is the only place the two systems touch.

⚠️ **The bridge must stay scoped to `[data-md-color-scheme=...]`, never
`:root`.** Material sets its scheme colours from those attribute selectors; an
unscoped rule loses the specificity contest and the dark toggle breaks in a way
that only shows up in one mode.

The `@media print` block is **the one deliberate exception** to the no-literals
rule. It overrides the tokens rather than Material's variables, so the bridge
keeps doing the translating and the block stays short forever. Paper is not a
theme, it is a physical constraint.

---

## The chrome

What is deliberately **not** on this site, and why. Every one is a reversal of
a Material default; none should be restored without reading the reason.

| Removed | Was | Why |
|---|---|---|
| The GitHub repo block | Name, star count and fork count in the header and at the top of the mobile drawer | It reported **0 stars, 0 forks** on a venue reference nobody stars. `repo_url` stays in `mkdocs.yml` — this hides the display, not the config, and `page.edit_url` is built from it. |
| `content.action.edit` | A pencil icon top-right of every page | It reads as an invitation to edit a document whose job is to be the settled answer, and it rendered as an anchor with **no text at all** — a screen reader announced the raw URL. Replaced by `hooks/pagefoot.py`. |
| `material.extensions.preview` | Hover card previewing a link's target | Previews need hover and this site is read on a phone. **⚠️ The second reason once given — that it iconised every nav row — was WRONG; see below.** The removal stands on the hover argument alone, and adding it back now costs nothing in icons. |

And one thing deliberately **kept**, which is rarer and therefore worth more
words.

### ⓘ / 🔒 The sidebar badge — a reserved key we did not know we were using

**`status:` is a Material key. We also use it. Both at once.**

Material's `partials/nav-item.html` finishes rendering a nav link with:

```jinja
{% if nav_item.meta and nav_item.meta.status %}
  {{ render_status(nav_item, nav_item.meta.status) }}
{% endif %}
```

It knows three values — `new`, `deprecated`, `encrypted` — and falls back to
`--md-status`, the **information-outline** glyph, for anything else. Our four
values are all "anything else". So every page carried an ⓘ, and `Venues` /
`Production` / `Reference` did not, **because a folder with no `index.md` has no
page meta to read.**

That is *also* exactly what instant previews would have looked like — which is
how it got misdiagnosed and cost a working feature. Two clues were sitting
there: removing the extension changed nothing, and the icons kept appearing on
precisely the set of rows that have frontmatter.

**It is now deliberate and load-bearing.** The badge was hidden for about two
hours the same morning and Michael asked for it back immediately (*"lost the
info icon which i want back"*). Do not tidy it away as leftover Material chrome.

**Only two values can ever reach the sidebar.** `hidden` is never built and
`unlisted` is pruned from the nav, so the badge is a **two-state legend**, not
decoration:

| Rendered | Status | Glyph |
|---|---|---|
| ⓘ | `public` | Material's default, `information-outline` |
| 🔒 | `gated` | `--md-status--encrypted`, re-pointed in `uritp.css` → NAV |

The padlock is why the badge earns its place: a locked page stays visible in the
sidebar on purpose, so a reader can see it exists and go ask for the password.
Before, that row looked identical to every other one until you tapped it.

**The meaning is explained to readers** in `docs/using-these-docs.md` → *The
icons in the sidebar*. That page is the only place a guest designer will ever
learn what 🔒 means, so it changes whenever this does.

**Tooltips** come from `extra.status` in `mkdocs.yml`. They render as `title=`,
so they are hover text on a desktop and an accessible name for a screen reader —
and **nothing at all on a phone**, the same limitation that killed instant
previews. The glyph carries the meaning alone on mobile.

⚠️ **Do not write `status: new` or `status: deprecated`** to get a different
icon. `hooks/visibility.py` treats an unrecognised value as `hidden` and the
page vanishes from the site.

⚠️ **The `gated` rule uses a fallback on purpose:**
`mask-image: var(--md-status--encrypted, var(--md-status))`. If a future
Material drops that variable, the row degrades to the plain ⓘ instead of
rendering an empty box.

**The transferable lesson:** a plausible cause that explains the symptom is not
the cause. Two independent things here produce an identical icon on an identical
set of rows, and the only way to tell them apart was to read the template.

### The edit link

`hooks/pagefoot.py` renders one worded line at the bottom of every page, below
`Linked from`:

```
────────────────────────────
Edit this page on GitHub
```

Words rather than an icon, on purpose: self-describing, survives being read
aloud, works if the icon font never loads. Kill switch `URITP_EDITLINK=0`. A
page with no `edit_url` gets no link rather than a broken one.

### 🔴 The blocked chevron, and how one fix broke another

Michael's screenshot showed the mobile drawer's back arrow sitting **on top of
the first letter** of the section title: a chevron through the V of `VENUES`.

Material positions that arrow **absolutely**, at top `.4rem` / left `.4rem`,
because its own drawer title is a tall block with the text pushed to the bottom.
The dark-mode drawer repair — necessary, the panels render white-on-white
without it — flattened that title to a single line and moved the text **up, into
the arrow's corner.** Neither change was wrong on its own.

The repair is to stop fighting the absolute position and lay the row out
honestly: flex row, arrow first, title second, real space between. They now
cannot overlap whatever the title height becomes.

**The general lesson:** overriding a component's *layout* while leaving its
*absolutely positioned children* alone is a collision waiting to happen.
Absolute positioning is a contract with a box you just changed the shape of.

### 🔴 The tall Safety row, and the fix that had to be done twice

Michael: *"nav menu has weird spacing for safety?"* It did, and Safety was the
only row it happened to.

**Safety was the only top-level section carrying an `index.md`.** Under
`navigation.indexes` Material renders that case as a `.md-nav__container`: a
wrapper that **also carries `.md-nav__link`**, holding a nested `<a>` and
`<label>` that carry it too. Three elements, one class.

**Attempt 1 blamed the padding and was wrong.** Material already writes
`.md-nav--primary .md-nav__link > .md-nav__link { padding: 0 }` — the wrapper is
padded, the children are not, and it has handled this since long before us.
Zeroing the wrapper removed the row's *only* padding, and the title went flush
to the drawer edge. **A fix that changes the symptom instead of removing it
means the diagnosis was wrong** — that is the tell, and it is cheap to act on.

**The actual culprit was `min-height: var(--u-touch)`.** Our 44px tap floor,
which Material has no equivalent of and therefore no rule to cancel, applied at
all three levels: a 44px child inside a 44px padded parent.

The fix cancels the tap floor in exactly the place Material cancels the padding,
then stretches the children so the whole row stays tappable rather than just the
line of text at the top of it.

**Same lesson as the chevron, one layer out:** a blanket rule on a component
class is a bet that the component only ever renders one shape. It renders two
here, and the second only appears when a folder gains an index page — so the bug
arrives on the day somebody adds a file, nowhere near the CSS. **Read the
component's own stylesheet before overriding it.** Both of these cost a round
trip that reading `_nav.scss` would have saved.

### Focus and tap targets

One `:focus-visible` ring for the whole site, in `accent`, at `focus-w`. It
appears for keyboard and assistive navigation and never for a mouse click.

⚠️ **Never write `outline: none` on a control here.** The gate password field
used to do exactly that and signal focus with a border colour alone — invisible
to anyone who cannot distinguish two greys, and gone entirely in forced-colours
mode.

Mobile nav rows, the password field and the Unlock button all take their minimum
height from `touch` in `theme/spacing.tsv`, so density stays a theme decision
and never quietly drops below the 44px floor.

### Two `gate.js` behaviours documented here, not in AUTHORING-GATES

Both are DOM presentation. Neither touches the cipher, the KDF, the iteration
count or the keystore, so the same-PR rule binding `visibility.py` to `gate.js`
does not fire.

1. **`role="alert"` on the failure line.** It appears by un-hiding an element
   already in the DOM, which a screen reader does not announce on its own.
2. **🔴 The duplicate title after unlocking.** A gated page is built with its
   body already replaced by the lock box, so Material finds no `<h1>` and
   injects one from `title:`. Then `gate.js` decrypts the real body — carrying
   the page's own `<h1>` — and inserts it. Two identical headings, stacked.

   It survived a day because **the built page is right and the live page is
   right, until the moment somebody types the password.** No check that stopped
   short of unlocking could have found it.

   `reveal()` now drops the injected heading and keeps the authored one,
   identified by what it structurally lacks: Material injects a bare `<h1>` with
   no `id`, while an authored heading gets an `id` and a `.headerlink` permalink
   from the `toc` extension. Position would break the first time anything else
   rendered above the content.

   ⚠️ **Still open:** before unlocking, *Skip to content* on a gated page points
   at an anchor built from an H1 that is not in the DOM yet. Cosmetic,
   keyboard-only, logged in `next-build-spec.md`.

---

## What the search result says

**The text under a search result is the page's own opening text. There is no
separate description field, and nothing is generated.**

The built-in search plugin scans the **rendered HTML** and splits each page into
one record per heading. Each record holds a location, a title, and the text
following that heading up to the next one. The result list shows the title, then
a teaser cut from that text around your search term.

So for the entry representing the page itself:

| It shows | Which is |
|---|---|
| the heading | the page's `# H1`, falling back to frontmatter `title:` |
| the text under it | **everything between the H1 and the first `##`** |

On every page here that is the **lede paragraph**. Rewrite the lede and you have
rewritten the search result. That is the answer to "where do I edit that text":
you already were.

A result that reads badly almost always means the page opens with something
other than a plain sentence — a callout, a table, a bare link — and the teaser is
quoting it verbatim.

### Ranking and exclusion

```yaml
---
title: Smith Theatre
search:
  boost: 2        # >1 pushes it up, <1 pushes it down
---
```

```yaml
---
search:
  exclude: true   # keep the whole page out
---
```

Or a single section, using `attr_list` (already enabled):

```markdown
## Internal notes { data-search-exclude }
```

### What happens automatically

- **`unlisted` pages and anything with `listed: false`** are excluded already,
  by `hooks/visibility.py`. See AUTHORING-GATES.
- **A `gated` page indexes its unlock box, never its content.** The gate
  replaces the body *before* the search plugin sees it, so the real text was
  never in the index to leak. A property of hook order, not a filter. **This
  covers every page under a gated folder index**, since the waterfall locks them
  for real.
- **`Linked from` and the edit link are in the index.** They are rendered
  content. They sit at the bottom, after the last heading, so they only surface
  as a teaser on a search that matched nothing better.

---

## Changing the standards themselves

| File | Holds | Update here when |
|---|---|---|
| [`theme/`](theme/) | **Every colour, font, size, radius and gap** | Any look change at all — see its README |
| `hooks/theme.py` | Composition, the fallback chain, `REQUIRED` | A token is added, or the injection changes |
| `hooks/pagefoot.py` | The page-foot edit link | Its label, placement, or condition changes |
| `docs/stylesheets/uritp.css` | Every rule on the site | A custom class is added, renamed, or dropped — **and [AUTHORING.md](AUTHORING.md) too**, since authors type `.tbc` by hand |
| `docs/stylesheets/links.css` | The `.deadlink` marker | The marker is restyled or renamed |
| `mkdocs.yml` → `theme.font` | Which webfont is downloaded | `theme/typography.tsv` points at a new family |
| `mkdocs.yml` → `theme.palette` → `primary` | First paint + `<meta theme-color>` | The `chrome` column moves far from a dark neutral |
| `mkdocs.yml` → `extra.status` | Sidebar badge tooltips | A `status:` value is added or renamed — **and `docs/using-these-docs.md`** |
| `mkdocs.yml` → `theme.features` | Which Material chrome is on | Anything in *The chrome* table above is restored or removed — **and grep `docs/` for pages that describe it** |
| `requirements.txt` → the 9.x floor | Which Material template ships | Never casually. `partials/nav-item.html` is behaviour we depend on. |

⚠️ **Anything that describes the chrome to READERS lives in `docs/`, and nothing
points at it.** Removing the pencil left `docs/using-these-docs.md` telling guest
designers to click an icon that no longer existed, and the repo's pointer
discipline did not catch it because every pointer runs *code → AUTHORING\*.md*.
`mkdocs.yml` has no idea an orientation page documents its feature flags.
**Turning a chrome feature on or off means grepping `docs/` for it too.**
