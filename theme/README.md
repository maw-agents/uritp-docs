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
column `bg`.

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
the banner detaches. If you take it far from a dark neutral, mirror it in
`mkdocs.yml` → `theme.palette` → `primary`, which is first paint and the phone
browser's own bar colour.

⚠️ **`marker` is deliberately not `accent`.** "This number is unconfirmed" and
"this is a link" must not be the same colour.

### `typography.tsv` — the voice

Families, the four-step size ramp (`fs-lead`, `fs-body`, `fs-sm`, `fs-xs`),
the heading ramp, line height, letter tracking.

⚠️ **One seam that cannot be closed from here.** This grid says which family
the CSS **asks for**. `mkdocs.yml` → `theme.font` says which family Material
**downloads**. Point at something Material was not told to fetch and you get a
silent fallback. Stay inside a family already loaded, or change both.

### `forms.tsv` — the edges

Corner radius, border weights, shadow, motion timing, focus ring thickness.
`shadow` = `none` is the house answer and a real value.

### `spacing.tsv` — the density

Tap target, cell and block padding, the three gaps, and `measure` (maximum
line length for prose).

⚠️ **`touch` is an accessibility floor, not a taste dial.** 44px minimum. The
mobile nav rows, the password field and the Unlock button all read it.

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
fallback — so an inherited value is something you can see, not something you
have to remember.

---

## What is NOT in here

**Which Material class reads which token.** That is
`docs/stylesheets/uritp.css`, which holds no colour, no font name, no size and
no radius of its own — only `var(--u-*)` references and the rules that place
them. If you need a value with no token, add the column here **and** its name
to `REQUIRED` in `hooks/theme.py`, in the same commit.

**A link to the app themes.** These four vectors are a deliberate port of
`mawizorek/ClickUp_apps` → `shared/themes/` so the vocabulary matches, but it
is **a port, not a link.** That system resolves in the browser at runtime for
apps with a live theme picker; this one composes at build time because MkDocs
emits static HTML. Editing a grid there changes nothing here. The schemas also
differ — that one carries light mode as extra columns and has tokens for
objects a docs site does not have. Same words, separate files, on purpose.
