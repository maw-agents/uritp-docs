# The theme

Everything about how this site looks is in this folder, in six files you read
as tables. **No CSS. No code. No YAML.**

| File | What it is |
|---|---|
| [`active.txt`](active.txt) | **The switch.** One word: which theme is live. |
| [`themes.tsv`](themes.tsv) | **The join.** One row per theme, pointing at four vectors. |
| [`colors.tsv`](colors.tsv) | Vector 1 — the paint |
| [`typography.tsv`](typography.tsv) | Vector 2 — the voice |
| [`forms.tsv`](forms.tsv) | Vector 3 — the edges |
| [`spacing.tsv`](spacing.tsv) | Vector 4 — the density |

Every `.tsv` opens as a **grid** on GitHub, in Numbers, in Excel, anywhere.
Edit a cell, commit, wait ninety seconds, check the footer stamp.

---

## The three things you will actually do

### 1. Swap the whole look — edit `active.txt`

One word, one file:

    uritp-granite

That is the entire procedure. The names available are the `slug` column of
`themes.tsv`.

### 2. Nudge one value — edit one cell

Body text a little bigger? `typography.tsv`, row `plex-docs`, column
`fs-body`. Background less black? `colors.tsv`, row `uritp-prp`, mode `dark`,
column `bg`. Menu rows too tight? `spacing.tsv`, column `pad-row`.

That cell is the only place the value exists. Nothing else needs touching.

### 3. Build a variant — add a row, fill only what changes

That is what the `inherits` column is for, and `uritp-granite` in
`colors.tsv` is the worked example. It inherits `uritp-prp`, fills the ten
neutrals, and leaves the accent cells **blank** — so it keeps the house blue
automatically. Change that blue once and the granite variant follows it.

---

## The one rule

> **An empty cell inherits. A filled cell wins.**

Same rule at both levels, so you learn it once.

**In `themes.tsv`** — an empty vector cell takes the `_default` row's value.
Look at `uritp-granite`: it names a colour and leaves typography, forms and
spacing blank, so it gets the defaults. One cell, one theme.

**In a vector grid** — an empty token cell takes the value from the row named
in `inherits`, then from the `_base` row of the same file.

So the chain is **your cell → what you inherit from → `_base` → the build
fails and names the token.**

⚠️ **Empty means inherit, never "nothing".** A value that is deliberately off
is written out: `shadow` is the word `none`, not a blank cell.

---

## The two rows that are not themes

**`_default` in `themes.tsv`** and **`_base` in each vector grid.** They are
the safety net, they must stay complete, and `active.txt` may never point at
one. Everything falls back to them, so a half-finished row still renders
instead of breaking the site.

---

## Colour has two modes

The site has a dark/light toggle, so **every palette needs two rows** in
`colors.tsv` — one `dark`, one `light`, same `slug`. Miss one and the build
says so.

The other three vectors have no modes. Type, edges and density do not change
when you flip the scheme.

---

## What each vector holds

### `colors.tsv` — the paint

| Column | Used for |
|---|---|
| `bg` | The page |
| `surface-1` | Code blocks, inset panels |
| `surface-2` | Raised strips: callout headers, table row hover |
| `border` | A line you are meant to **see** — inputs, table header underline |
| `hairline` | A line you are meant to barely notice — row rules, dividers |
| `text` | Body copy |
| `text-strong` | Headings, the first cell of a table row |
| `text-soft` | Ledes, captions, small caps labels, sidebar badges |
| `accent` | Links, the active nav item, focus rings |
| `accent-hover` | Its hover and press state |
| `on-accent` | Text sitting **on** an accent fill (the Unlock button) |
| `chrome` | **The header banner**, the tab strip, the mobile drawer header |
| `on-chrome` | Text and icons sitting on the chrome |
| `marker` | `[To be confirmed]` pills and the gate label |
| `bad` | Dead links, errors |

**Values are `oklch(lightness chroma hue)`.** Lightness is the percentage,
chroma is how saturated it is (`0` is pure grey), hue is the angle. Warmer
means moving hue toward 90. Greyer means dropping chroma. Less black means
raising the lightness on `bg`.

⚠️ **`chrome` is the header bar.** Every palette here sets it equal to `bg`,
which is the deliberate flat look: the header is the same ground as the page,
separated by a rule instead of a block of colour. Give it its own value and
the banner detaches.

⚠️ **`marker` is deliberately not `accent`.** "This number is unconfirmed" and
"this is a link" must not be the same colour.

### `typography.tsv` — the voice

| Column | Used for |
|---|---|
| `webfont-text` / `webfont-code` | **Which fonts get downloaded.** See below. |
| `font-body` / `font-mono` | The CSS font stack, including fallbacks |
| `fs-lead` | The one paragraph under a page title |
| `fs-body` | Body copy |
| `fs-sm` | Tables, callouts |
| `fs-xs` | Small caps labels, table headers, the page-foot link |
| `fs-micro` | The footer build stamp |
| `fs-nav` | **Sidebar text**, content tabs, the gate's small print |
| `fs-nav-mobile` | Sidebar text in the phone drawer, where it needs to be bigger |
| `fs-h1-min` / `fs-h1-fluid` / `fs-h1-max` | The page title, which scales with the window |
| `fs-h2` / `fs-h3` | Section headings |
| `lh-body` / `lh-tight` | Line height: prose / headings |
| `track-body` / `track-tight` / `track-caps` | Letter spacing: prose / headings / small caps |

**`webfont-text` and `webfont-code` are the two cells that are not a style.**
They name the font families Material should **download**, and
`hooks/theme.py` writes them into the build. Everything else in this grid is a
CSS value; these two are configuration.

    webfont-text = IBM Plex Sans      download it
    webfont-text = none               download nothing, use system fonts

⚠️ **They are all-or-nothing.** Material has no per-face switch, so both must
say `none` or both must name a family. One of each fails the build rather than
picking a winner quietly.

> **This used to be a seam and it is now closed.** Until 2026-08-01 the font
> the CSS *asked for* lived here and the font Material *downloaded* lived in
> `mkdocs.yml`, two files kept in agreement by hand — and a mismatch silently
> rendered the next fallback in the stack with no error anywhere. One row
> decides both now, so they cannot disagree. **Do not add a `font:` block back
> to `mkdocs.yml`**; it would be overwritten every build and would read as
> configuration while doing nothing.

### `forms.tsv` — the edges

| Column | Used for |
|---|---|
| `radius` / `radius-lg` | Corner rounding: small things / panels |
| `border-w` | A line you are meant to see |
| `rule-w` | A line you are meant to barely notice |
| `bar-w` | The accent bar marking the row you are on in the menu |
| `shadow` | Depth. `none` is the house answer and a real value. |
| `motion` / `ease` | Transition duration and curve |
| `focus-w` | Keyboard focus ring thickness. **Never 0.** |
| `icon-dim` | How faded the menu chevrons are (`1` = full strength) |

### `spacing.tsv` — the density

| Column | Used for |
|---|---|
| `touch` | Minimum tap target |
| `pad-cell` | Table cell padding |
| `pad-block` | Padding inside a callout or the password box |
| `pad-row` | **Menu row padding** — vertical then horizontal |
| `gap-xs` / `gap-md` / `gap-lg` | The rhythm between things |
| `measure` | Maximum line length for prose |

⚠️ **`touch` is an accessibility floor, not a taste dial.** 44px minimum. The
menu rows, the password field and the Unlock button all read it.

---

## Adding a whole new palette

1. Add **two rows** to `colors.tsv`, `dark` and `light`, same slug.
2. Fill every column — **or** name a row in `inherits` and fill only what
   differs.
3. Add a row to `themes.tsv` pointing at it. Leave the other three vectors
   blank unless you want something other than the defaults.
4. Point `active.txt` at it when you want to see it.

A token still missing after the whole fallback chain **fails the build and
names the token**. A theme name that does not exist fails and lists the names
that do. Both are deliberate: a theme has no single page to fail on, so a
theme that quietly fell back to something else would be invisible.

**The build log prints what resolved**, including which cells came from a
fallback and which fonts were requested — so an inherited value is something
you can see, not something you have to remember.

---

## What is deliberately NOT a dial

The stylesheet still contains numbers. They are there on purpose and this is
the test: **a token answers "what should this look like"; a literal answers
"where does this sit relative to the thing beside it".** A heading's bottom
margin measured in its own size, an icon's offset inside its box, a line
height of 1.3 — those follow the tokens automatically because they are
relative, and turning them into cells would mean fifty columns nobody will
ever set.

Three things are named exceptions, and none of them should become themeable:

- **Breakpoints.** The two widths where the layout changes are Material's own,
  matched deliberately so our rules switch on the same line its rules do. A
  theme that could move them would let a palette desynchronise our layout from
  the component's — the exact collision class that cost two fixes in one day.
- **The print block.** Paper is not a theme, it is a physical constraint: ink
  on white at full contrast, whichever skin was on screen. A themeable print
  palette would let a swap produce an unreadable printout, and a venue page
  carried into a production meeting is the case that must never break.
- **Which Material class reads which token.** That mapping is
  `docs/stylesheets/uritp.css` — the wiring, not the look.

If you need a value that has no cell, add the column here **and** its name to
`REQUIRED` in `hooks/theme.py`, in the same commit. `chrome`, `pad-row` and
`fs-nav` all arrived that way, each one because a real question turned out to
have no answer in the grid.

---

## Relation to the app themes

These four vectors are a deliberate port of `mawizorek/ClickUp_apps` →
`shared/themes/` so the vocabulary matches, but it is **a port, not a link.**
That system resolves in the browser at runtime for apps with a live theme
picker; this one composes at build time because MkDocs emits static HTML.
Editing a grid there changes nothing here. The schemas also differ — that one
carries light mode as extra columns and has tokens for objects a docs site
does not have. Same words, separate files, on purpose.
