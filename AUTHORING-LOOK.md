# Look and feel reference

How this site is themed, and how to change it. Companion to
[AUTHORING.md](AUTHORING.md) (writing pages) and
[AUTHORING-GATES.md](AUTHORING-GATES.md) (visibility and keys).

**Describes:** `theme.yml` · `hooks/theme.py` · `docs/stylesheets/uritp.css` ·
`docs/stylesheets/links.css` · the `theme:` block in `mkdocs.yml`

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

⚠️ **`touch` is an accessibility floor, not a taste dial.** 44px minimum. A vector
that goes under it is a bug even if it looks tidier.

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

---

## Changing the standards themselves

| File | Holds | Update here when |
|---|---|---|
| `theme.yml` | The four vectors + the join table | A palette, vector row, or token is added or changed |
| `hooks/theme.py` | Composition, validation, `REQUIRED` | A token is added or the injection changes |
| `docs/stylesheets/uritp.css` | Every rule on the site | A custom class is added, renamed, or dropped — **and [AUTHORING.md](AUTHORING.md) too**, since authors type `.tbc` by hand |
| `docs/stylesheets/links.css` | The `.deadlink` marker | The marker is restyled or renamed |
| `mkdocs.yml` → `theme.font` | Which webfont is downloaded | The typography vector points at a new family |
