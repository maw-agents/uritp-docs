# Look and feel reference

How this site is themed, how its chrome behaves, and how search decides what to
show. Companion to [AUTHORING.md](AUTHORING.md) (writing pages) and
[AUTHORING-GATES.md](AUTHORING-GATES.md) (visibility and keys).

**Describes:** `theme.yml` · `hooks/theme.py` · `hooks/pagefoot.py` ·
`docs/stylesheets/uritp.css` · `docs/stylesheets/links.css` · the `theme:` and
`extra:` blocks in `mkdocs.yml`

> ⚠️ **Split out 2026-08-01, for the reason the gate reference was.** There is no
> partial-edit path through this toolchain, so every change re-emits the whole
> file. A 15KB canonical document rewritten five times in a day is five chances
> to silently drop a section. Highest churn, smallest file.

---

## Everything about the look lives in ONE file

`theme.yml`, at the repo root. Not in `docs/`, not in a stylesheet, not split
across palettes. **The four vectors, every palette, and the join table that names
their combinations are all in that one file**, in this order:

| Section | What is in it |
|---|---|
| `active:` | The one line that picks a theme |
| `themes:` | The join table — `uritp-prp`, `uritp-prp-large`, `utility`, `paper` |
| `color:` | Palettes — `uritp-prp`, `maw-dark-utility`, `paper-mono` |
| `typography:` | `plex-docs`, `plex-large`, `system-quick` |
| `forms:` | `hairline`, `square`, `soft` |
| `spacing:` | `standard`, `dense`, `roomy` |

⚠️ **A theme NAME and a palette NAME are not the same thing**, and this catches
people. `paper` and `utility` are rows in the **join table** — each one is four
pointers, not values. The values they point at are palettes with different names:

```yaml
themes:
  paper:
    color: paper-mono      # <- edit the colours HERE, under `color:`
    typography: plex-docs
    forms: square
    spacing: roomy
```

So **to change how `paper` looks, edit `paper-mono` under `color:`** (or point the
`paper` row at a different vector). To change how `utility` looks, edit
`maw-dark-utility`. The indirection is the point: `utility` and `paper` share
`plex-docs`, so fixing a font size once fixes it in both.

**`chrome` is not a vector.** It is one of the fifteen colour tokens, so it lives
inside each palette, twice — once under `dark:` and once under `light:`.

---

## Changing how the whole site looks

**One line, in `theme.yml`.**

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

### Changing just the header banner

```yaml
color:
  uritp-prp:
    dark:
      chrome:    oklch(26% 0.030 250)     # <- this line, and its light: twin
```

`chrome` is the header bar, the tab strip, and the drawer header on a phone. All
three read the one token, so **that is the single line for "change the colour of
the top bar everywhere"** — no CSS, no Material variable names, no hunting.

Every palette we ship sets `chrome` equal to `bg`, which is the deliberate flat
house look: the header is the same ground as the page, separated by a rule rather
than a block of colour. Give it its own value and the banner detaches.

⚠️ **If you take `chrome` far from a dark neutral, mirror it in `mkdocs.yml` →
`theme.palette` → `primary`.** That entry is the first-paint floor and the source
of the phone browser's own `<meta theme-color>`; leave it behind and the browser
chrome above your header is a different colour from the header.

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

Fifteen tokens, per mode. This is the complete list; there is no sixteenth colour
hiding in the stylesheet.

| Token | Used for |
|---|---|
| `bg` | The page |
| `surface-1` | Code blocks, inset panels |
| `surface-2` | Raised strips: callout headers, table row hover |
| `border` | A line you are meant to **see** — inputs, the table header underline |
| `hairline` | A line you are meant to barely notice — row rules, dividers |
| `text` | Body copy |
| `text-strong` | Headings, the first cell of a table row |
| `text-soft` | Ledes, captions, the small uppercase labels, the sidebar badges |
| `accent` | Links, the active nav item, focus rings |
| `accent-hover` | Its hover and press state |
| `on-accent` | Text sitting **on** an accent fill (the Unlock button) |
| `chrome` | **The header banner**, the tab strip, the mobile drawer header |
| `on-chrome` | Text and icons sitting on the chrome |
| `marker` | `[To be confirmed]{.tbc}` and the gate label |
| `bad` | Dead links, errors |

⭐ **`accent` used to not exist.** Link colour came from whatever Material defaults
to under `primary: black` — a blue nobody chose, set in a different file from every
other colour on the site. It is a token now, which means it can be changed in one
place and it can be contrast-checked. That is the single biggest thing this port
fixed.

⭐ **`chrome` used to not exist either** (added 2026-08-01, same reasoning, same
question from Michael: *where is the one line*). The header took `bg` through the
bridge, so "a different colour top bar" was not a value you could set — it was a
stylesheet edit. Now it is a row in the palette.

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
   **all fifteen tokens** in each.
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
PR. `chrome` is the worked example of exactly that.

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
| `material.extensions.preview` | Hover card previewing a link's target | Previews need hover and this site is read on a phone. **⚠️ The second reason once given — that it iconised every nav row — was WRONG; see below.** The removal stands on the hover argument alone, and adding it back now costs nothing in icons. |

And one thing that is deliberately **kept**, which is rarer and therefore worth more
words: **the sidebar status badge.**

### ⓘ / 🔒 The sidebar badge — a reserved key we did not know we were using

**`status:` is a Material key. We also use it. Both at once.**

Material's `partials/nav-item.html` finishes rendering a nav link with:

```jinja
{% if nav_item.meta and nav_item.meta.status %}
  {{ render_status(nav_item, nav_item.meta.status) }}
{% endif %}
```

It knows three values — `new`, `deprecated`, `encrypted` — and falls back to
`--md-status`, the **information-outline** glyph, for anything else. Our four values
are all "anything else". So every page carried an ⓘ, and `Venues` / `Production` /
`Reference` did not, **because a folder with no `index.md` has no page meta to read.**

That is *also* exactly what instant previews would have looked like — which is how it
got misdiagnosed on 2026-08-01 and cost a working feature. Two clues were sitting
there: removing the extension changed nothing, and the icons kept appearing on
precisely the set of rows that have frontmatter.

**It is now deliberate, and it is load-bearing.** The badge was hidden for about two
hours the same morning and Michael asked for it back immediately (*"lost the info
icon which i want back"*). Do not tidy it away as leftover Material chrome.

**Only two values can ever reach the sidebar.** `hidden` is never built and `unlisted`
is pruned from the nav, so the badge is a **two-state legend**, not decoration:

| Rendered | Status | Glyph |
|---|---|---|
| ⓘ | `public` | Material's default, `information-outline` |
| 🔒 | `gated` | `--md-status--encrypted`, re-pointed in `uritp.css` → NAV |

The padlock is the reason the badge earns its place: a locked page stays visible in
the sidebar on purpose, so a reader can see it exists and go ask for the password.
Before, that row looked identical to every other one until you tapped it.

**Hidden meaning, made explicit:** the two marks are explained to readers in
`docs/using-these-docs.md` → *The icons in the sidebar*. That page is the only place
a guest designer will ever learn what 🔒 means, so it changes whenever this does.

**Tooltips** come from `extra.status` in `mkdocs.yml`. They render as `title=`, so
they are hover text on a desktop and an accessible name for a screen reader — and
**nothing at all on a phone**, which is the same limitation that killed instant
previews. The glyph has to carry the meaning on its own.

⚠️ **Do not write `status: new` or `status: deprecated`** to get a different icon.
`hooks/visibility.py` treats an unrecognised value as `hidden` and the page vanishes
from the site.

⚠️ **The `gated` rule uses a fallback on purpose:**
`mask-image: var(--md-status--encrypted, var(--md-status))`. If a future Material
drops that variable, the row degrades to the plain ⓘ instead of rendering an empty
box where an icon should be.

**The transferable lesson:** a plausible cause that explains the symptom is not the
cause. Two independent things here produce an identical icon on an identical set of
rows, and the only way to tell them apart was to read the template.

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

### 🔴 The tall Safety row, and the fix that had to be done twice

Michael, 2026-08-01: *"nav menu has weird spacing for safety?"* It did, and Safety
was the only row it happened to.

**Safety was the only top-level section carrying an `index.md`.** Under
`navigation.indexes` Material renders that case as a `.md-nav__container`: a wrapper
that **also carries `.md-nav__link`**, holding a nested `<a>` and `<label>` that carry
it too. Three elements, one class.

**Attempt 1 blamed the padding and was wrong.** Material already writes
`.md-nav--primary .md-nav__link > .md-nav__link { padding: 0 }` — the wrapper is
padded, the children are not, and it has handled this since long before us. Zeroing
the wrapper removed the row's *only* padding, and the title went flush to the drawer
edge with the chevron hard against the other. **A fix that changes the symptom instead
of removing it means the diagnosis was wrong** — that is the tell, and it is cheap to
act on.

**The actual culprit was `min-height: var(--u-touch)`.** Our 44px tap floor, which
Material has no equivalent of and therefore no rule to cancel, applied at all three
levels: a 44px child inside a 44px padded parent.

The fix cancels the tap floor in exactly the place Material cancels the padding, then
stretches the children so the whole row stays tappable rather than just the line of
text at the top of it.

**Same lesson as the chevron, one layer out:** a blanket rule on a component class is
a bet that the component only ever renders one shape. It renders two here, and the
second only appears when a folder gains an index page — so the bug arrives on the day
somebody adds a file, nowhere near the CSS. **Read the component's own stylesheet
before overriding it.** Both of these cost a round trip that reading `_nav.scss`
would have saved.

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
  leak. That is a property of hook order, not a filter. **This now covers every page
  under a gated folder index**, since the waterfall locks them for real.
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
| `mkdocs.yml` → `theme.palette` → `primary` | First paint + `<meta theme-color>` | The `chrome` token moves far from a dark neutral |
| `mkdocs.yml` → `extra.status` | Sidebar badge tooltips | A `status:` value is added or renamed — **and `docs/using-these-docs.md`** |
| `mkdocs.yml` → `theme.features` | Which Material chrome is on | Anything in *The chrome* table above is restored or removed — **and grep `docs/` for pages that describe it** |
| `requirements.txt` → the 9.x floor | Which Material template ships | Never casually. `partials/nav-item.html` is behaviour we depend on. |

⚠️ **Anything that describes the chrome to READERS lives in `docs/`, and nothing
points at it.** Removing the pencil left `docs/using-these-docs.md` telling guest
designers to click an icon that no longer existed, and the repo's pointer discipline
did not catch it because every pointer runs *code → AUTHORING\*.md*. `mkdocs.yml` has
no idea an orientation page documents its feature flags. **Turning a chrome feature
on or off means grepping `docs/` for it too.** The sidebar-badge legend on that page
is the first thing written under this rule rather than in spite of it.
