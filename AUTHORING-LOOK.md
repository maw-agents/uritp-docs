# Look and feel reference

How this site is themed, how its chrome behaves, and how search decides what to
show. Companion to [AUTHORING.md](AUTHORING.md) (writing pages) and
[AUTHORING-GATES.md](AUTHORING-GATES.md) (visibility and keys).

**Describes:** `theme.yml` · `hooks/theme.py` · `hooks/pagefoot.py` ·
`docs/stylesheets/uritp.css` · `docs/stylesheets/links.css` · the `theme:` block
in `mkdocs.yml`

> ⚠️ **Split out 2026-08-01, for the reason the gate reference was.** There is no
> partial-edit path through this toolchain, so every change re-emits the whole
> file. A 15KB canonical document rewritten five times in a day is five chances
> to silently drop a section. Highest churn, smallest file.

---

## Changing how the whole site looks

**One line, in `theme.yml` at the repo root.**

```yaml
active: uritp-prp
```

That is the entire procedure. There is no second file, no stylesheet to swap, and
nothing in `docs/` changes.

| `active:` | What you get |
|---|---|
| `uritp-prp` | The house look. Neutral slate, one owned blue, hairline rules. |
| `uritp-prp-large` | Same skin, bigger type, more air. Callboard or arm's length. |
| `utility` | The ClickUp app palette (teal on cool slate). |
| `paper` | Greyscale, squared corners, roomy. Closest to a printed document. |

Commit, wait ninety seconds, check the footer stamp. Same loop as any page edit.

---

## Why a theme is four things, not one

A theme here is **not a stylesheet**. It is four independent choices:

```
colour  ×  typography  ×  forms  ×  spacing
```

They are separate because they change for different reasons. Wanting bigger type
for a shop callboard has nothing to do with wanting a warmer palette, and a system
that bundles them makes you copy a whole design to move one dial.

Ported from `mawizorek/ClickUp_apps` → `shared/themes/`, the 4-vector matrix every
ClickUp app build points at. Token **names** match that system wherever the concept
exists, so the vocabulary transfers in both directions.

**Two deliberate differences from the ClickUp_apps original, both because this is a
docs site and not an app:**

1. **Every palette declares `dark:` and `light:`.** The app themes are single-mode.
   This site has a scheme toggle in the header, so a one-mode palette would
   half-work.
2. **The vectors resolve at BUILD time, not in the browser.** There is no
   `resolve.js` here and no runtime theme picker. MkDocs produces static HTML;
   composing on every page load would buy nothing and cost a flash of unstyled
   colour.

---

## What you can actually change

### Colour — "what colours do I have to design with?"

Thirteen tokens, per mode. This is the complete list; there is no fourteenth colour
hiding in the stylesheet.

| Token | Used for |
|---|---|
| `bg` | The page |
| `surface-1` | Code blocks, inset panels |
| `surface-2` | Raised strips: callout headers, table row hover, drawer header |
| `border` | A line you are meant to **see** — inputs, the table header underline |
| `hairline` | A line you are meant to barely notice — row rules, dividers |
| `text` | Body copy |
| `text-strong` | Headings, the first cell of a table row |
| `text-soft` | Ledes, captions, the small uppercase labels |
| `accent` | Links, the active nav item, focus rings |
| `accent-hover` | Its hover and press state |
| `on-accent` | Text sitting **on** an accent fill (the Unlock button) |
| `marker` | `[To be confirmed]{.tbc}` and the gate label |
| `bad` | Dead links, errors |

⭐ **`accent` used to not exist.** Link colour came from whatever Material defaults
to under `primary: black` — a blue nobody chose, set in a different file from every
other colour on the site. It is a token now, which means it can be changed in one
place and it can be contrast-checked. That is the single biggest thing this port
fixed.

**`marker` is deliberately not `accent`.** "This value is unconfirmed" and "this is
a link" must not be the same colour, or the amber pill stops reading as a warning.

### Forms — "which edges are mutable?"

These eight, and only these. Anything not on this list is structural and lives in
the stylesheet on purpose.

| Token | Controls |
|---|---|
| `radius` / `radius-lg` | Corner rounding: small things / panels |
| `border-w` | Thickness of a line you are meant to see |
| `rule-w` | Thickness of a line you are meant to barely notice |
| `shadow` | Depth. `none` is a real value and it is the house answer. |
| `motion` / `ease` | Transition duration and curve |
| `focus-w` | Thickness of the keyboard focus ring. **Never 0.** |

### Typography and spacing

Typography sets the family, the four-step size ramp (`fs-lead`, `fs-body`, `fs-sm`,
`fs-xs`), the heading ramp, line height and tracking. Spacing sets tap-target size,
cell and block padding, the three gap sizes, and `measure` (maximum line length for
prose).

⚠️ **`touch` is an accessibility floor, not a taste dial.** 44px minimum, and the
mobile nav rows, the password field and the Unlock button all read it. A vector that
goes under it is a bug even if it looks tidier.

---

## The one seam that is not closed

**The typography vector says which font family the CSS asks for. `mkdocs.yml` →
`theme.font` says which font Material downloads.** Two files.

That is not an oversight and it is not fixable from here: Material owns webfont
loading, and reimplementing it to close the seam would mean duplicating machinery
that already works. So it is named instead of hidden.

**Consequence:** point the vector at a family Material has not been told to fetch
and you get the next entry in the fallback stack, silently, with no error anywhere.
Stay inside a family already loaded, or change both lines.

`system-quick` is the exception — it asks only for fonts the device already has, so
it needs no download at all.

---

## Adding a palette

1. Add a block under `color:` in `theme.yml` with **both** `dark:` and `light:` and
   **all thirteen tokens** in each.
2. Add a row to `themes:` naming it.
3. Point `active:` at that row.

A missing token **fails the build and names the token**. That check lives in
`hooks/theme.py` (`REQUIRED`), not in `theme.yml`, because the stylesheet is what
consumes the names, so the code that pairs with the stylesheet is what knows which
ones may not go missing.

⚠️ **A theme name that does not resolve fails the build too**, deliberately, and
against this repo's usual instinct. A dead link marks one link and a missing gate
key locks one page, because both have a page to fail on. A theme does not — it is
the whole site or nothing — and a theme that quietly fell back to something else is
exactly the invisible failure that rule exists to prevent. Every PR runs a build
check, so a typo dies on the branch.

⚠️ **A `note:` in `theme.yml` may not contain a colon followed by a space.** It is a
plain YAML scalar; `set theme.font: false` reads as a nested mapping and kills the
whole parse, pointing at the wrong line. Quote it or reword it. Cost one build on
2026-08-01.

---

## Editing the stylesheet

`docs/stylesheets/uritp.css` contains **no colour, no font name, no size and no
radius.** Every value is a `--u-*` token.

⚠️ **A literal value committed there silently opts that element out of every future
swap.** The build fails by name when a palette forgets a token; it cannot detect a
stylesheet that stopped asking for one. If you need a value that has no token, add
the token — to `theme.yml` **and** to `REQUIRED` in `hooks/theme.py` — in the same
PR.

The file has one **bridge** block at the top mapping `--u-*` onto Material's own
`--md-*` variables. That is the only place the two systems touch.

⚠️ **The bridge must stay scoped to `[data-md-color-scheme=...]`, never `:root`.**
Material sets its scheme colours from those attribute selectors; an unscoped rule
loses the specificity contest and the dark toggle breaks in a way that only shows
up in one mode.

---

## The chrome

What is deliberately **not** on this site, and why. Every one of these is a
reversal of a Material default; none of them should be restored without reading
the reason.

| Removed | Was | Why |
|---|---|---|
| The GitHub repo block | Name, star count and fork count in the header and at the top of the mobile drawer | It reported **0 stars, 0 forks** on a venue reference nobody stars. `repo_url` stays in `mkdocs.yml` — this hides the display, not the config, and `page.edit_url` is built from it. |
| `content.action.edit` | A pencil icon top-right of every page | It reads as an invitation to edit a document whose job is to be the settled answer, and it rendered as an anchor with **no text at all** — a screen reader announced the raw URL. Replaced by `hooks/pagefoot.py`. |
| `material.extensions.preview` | Hover card previewing a link's target | It attaches to **every** internal link including the navigation, and marks each one with a small icon. Previews need hover. Phones have no hover. So the primary reading surface was carrying a row of icons for a feature it can never use. `Linked from` is the mechanism that works everywhere. |

### The edit link

`hooks/pagefoot.py` renders one worded line at the bottom of every page, below
`Linked from`:

```
────────────────────────────
Edit this page on GitHub
```

Words rather than an icon, on purpose: it is self-describing, it survives being
read aloud, and it works if the icon font never loads. Kill switch
`URITP_EDITLINK=0`. A page with no `edit_url` — a redirect stub, anything generated
— gets no link rather than a broken one.

### 🔴 The blocked chevron, and how one fix broke another

Michael's screenshot showed the mobile drawer's back arrow sitting **on top of the
first letter** of the section title: a chevron through the V of `VENUES`.

Material positions that arrow **absolutely**, at top `.4rem` / left `.4rem`, because
its own drawer title is a tall block with the text pushed to the bottom. The
dark-mode drawer repair — which was necessary, the panels render white-on-white
without it — flattened that title to a single line and moved the text **up, into
the arrow's corner.** Neither change was wrong on its own.

The repair is to stop fighting the absolute position and lay the row out honestly:
a flex row, arrow first, title second, real space between them. They now cannot
overlap whatever the title height becomes.

**The general lesson, worth more than the fix:** overriding a component's *layout*
while leaving its *absolutely positioned children* alone is a collision waiting to
happen. Absolute positioning is a contract with a box you just changed the shape of.

### Focus and tap targets

One `:focus-visible` ring for the whole site, in `accent`, at `focus-w`. It appears
for keyboard and assistive navigation and never for a mouse click.

⚠️ **Never write `outline: none` on a control here.** The gate password field used
to do exactly that and signal focus with a border colour alone — invisible to anyone
who cannot distinguish two greys, and gone entirely in forced-colours mode.

Mobile nav rows, the password field and the Unlock button all take their minimum
height from the spacing vector's `touch`, so density stays a theme decision and
never quietly drops below the 44px floor.

### Two `gate.js` behaviours documented here, not in AUTHORING-GATES

Both are DOM presentation. Neither touches the cipher, the KDF, the iteration count
or the keystore, so the same-PR rule that binds `visibility.py` to `gate.js` does
not fire, and a 14KB canonical file is not re-emitted whole to record a tidy-up.

1. **`role="alert"` on the failure line.** It appears by un-hiding an element that
   was already in the DOM, which a screen reader does not announce on its own.
2. **🔴 The duplicate title after unlocking.** A gated page is built with its body
   already replaced by the lock box, so Material finds no `<h1>` and injects one
   from `title:`. Then `gate.js` decrypts the real body — carrying the page's own
   `<h1>` — and inserts it. Two identical headings, stacked.

   It survived a day because **the built page is right and the live page is right,
   until the moment somebody types the password.** No check that stopped short of
   unlocking could have found it.

   `reveal()` now drops the injected heading and keeps the authored one, identified
   by what it structurally lacks: Material injects a bare `<h1>` with no `id`, while
   an authored heading gets an `id` and a `.headerlink` permalink from the `toc`
   extension. Position would break the first time anything else rendered above the
   content.

   ⚠️ **Still open:** before unlocking, *Skip to content* on a gated page points at
   an anchor built from an H1 that is not in the DOM yet. Cosmetic, keyboard-only,
   logged in `next-build-spec.md`.

---

## What the search result says

**The text under a search result is the page's own opening text. There is no
separate description field, and nothing is generated.**

The built-in search plugin scans the **rendered HTML** and splits each page into one
record per heading. Each record holds a location, a title, and the text that follows
that heading up to the next one. The result list shows the title, then a teaser cut
from that text around your search term.

So for the entry that represents the page itself:

| It shows | Which is |
|---|---|
| the heading | the page's `# H1`, falling back to frontmatter `title:` |
| the text under it | **everything between the H1 and the first `##`** |

On every page here that is the **lede paragraph** — the one sentence under the
title. Rewrite the lede and you have rewritten the search result. That is the answer
to "where do I edit that text": you already were.

A result that reads badly almost always means the page opens with something other
than a plain sentence — a callout, a table, a bare link — and the teaser is quoting
it verbatim.

### Making a page rank higher or lower

```yaml
---
title: Smith Theatre
search:
  boost: 2        # >1 pushes it up, <1 pushes it down
---
```

### Keeping something out of search entirely

```yaml
---
search:
  exclude: true   # the whole page
---
```

Or a single section or block, using `attr_list` (already enabled):

```markdown
## Internal notes { data-search-exclude }

This heading and everything under it stays out of the index.
```

### What happens automatically, so you do not have to

- **`unlisted` pages and anything with `listed: false`** are excluded already, by
  `hooks/visibility.py`. See AUTHORING-GATES.
- **A `gated` page indexes its unlock box, never its content.** The gate replaces the
  body *before* the search plugin sees it, so the real text was never in the index to
  leak. That is a property of hook order, not a filter.
- **`Linked from` and the edit link are in the index.** They are rendered content, so
  the plugin sees them. They sit at the bottom of a page, after the last heading, so
  they only surface as a teaser on a search that matched nothing better.

---

## Changing the standards themselves

| File | Holds | Update here when |
|---|---|---|
| `theme.yml` | The four vectors + the join table | A palette, vector row, or token is added or changed |
| `hooks/theme.py` | Composition, validation, `REQUIRED` | A token is added or the injection changes |
| `hooks/pagefoot.py` | The page-foot edit link | Its label, placement, or condition changes |
| `docs/stylesheets/uritp.css` | Every rule on the site | A custom class is added, renamed, or dropped — **and [AUTHORING.md](AUTHORING.md) too**, since authors type `.tbc` by hand |
| `docs/stylesheets/links.css` | The `.deadlink` marker | The marker is restyled or renamed |
| `mkdocs.yml` → `theme.font` | Which webfont is downloaded | The typography vector points at a new family |
| `mkdocs.yml` → `theme.features` | Which Material chrome is on | Anything in *The chrome* table above is restored or removed |
