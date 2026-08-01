# The theme

Everything about how this site looks is in this folder, in seven files you read
as tables. **No CSS. No code. No YAML.**

| File | What it is |
|---|---|
| [`active.txt`](active.txt) | **The switch.** One word: which theme is live. |
| [`themes.tsv`](themes.tsv) | **The join.** One row per theme, pointing at four vectors. |
| [`colors.tsv`](colors.tsv) | Vector 1 — the paint |
| [`typography.tsv`](typography.tsv) | Vector 2 — the voice |
| [`forms.tsv`](forms.tsv) | Vector 3 — the edges |
| [`spacing.tsv`](spacing.tsv) | Vector 4 — the density |
| [`contrast.tsv`](contrast.tsv) | **The gate.** Which pairs must be readable, and how readable. |

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

### 3. Repaint a theme without making a new one — edit ITS colour cell

A theme is four pointers, so you can repoint one and leave the rest alone.
Changing the `color` cell of the `uritp-prp` row swaps that theme's entire
palette — same type, same edges, same density, different paint. That is what
happened on 2026-08-01: the house theme's colour cell was pointed at
`mclaren`, and putting `uritp-prp` back in that one cell restores the slate.

**A new theme is for a new COMBINATION.** Repointing is for "same site,
different paint."

### 4. Build a variant — add a row, fill only what changes

That is what the `inherits` column is for. `uritp-granite` and `mclaren` in
`colors.tsv` are both worked examples: each names a parent, fills what it
changes, and leaves the rest **blank** to inherit.

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

## Is it readable? — `contrast.tsv`

**Every build measures every palette, in both modes, and reports anything that
cannot be read.** The pairs are data, so the policy is yours to edit:

| Column | Means |
|---|---|
| `fg` | The colour of the thing |
| `bg` | What it sits on |
| `min` | The ratio it must reach. **4.5** for text, **3.0** for non-text UI. |
| `level` | `fail` stops the build. `warn` only reports. |
| `note` | Why the row exists. Write one. |

**Only the ACTIVE palette can fail the build.** A parked palette cannot hurt a
reader today, and one nobody uses should not be able to hold the site hostage
— but every palette is still measured, so **you find out `uritp-granite` is
broken before you switch to it**, not after.

To grant an exemption, change `level` to `warn` **and say why in the note.**
To remove a check, delete the row. Both show up in a diff, which is the whole
reason this is a file and not a list inside the code.

**The build log prints the tightest pair in every palette**, so you can watch a
number get worse over time instead of only hearing about it when it breaks.

### What the gate found on its first run

Three real failures in `mclaren`, the palette that was live at the time:

| Pair | Was | Now |
|---|---|---|
| dark `text-soft` on `bg` | 3.91:1 | **5.21:1** |
| light `text-soft` on `surface-2` | 4.26:1 | **4.73:1** |
| light `accent` on `bg` | 4.02:1 | **5.14:1** |

The middle one is the argument for the whole gate: that colour had been
corrected by hand an hour earlier, checked against the page, and **passed** —
but nobody thought to check it against a *callout*, where it failed. Pairs you
think to check are not the problem. The pairs you do not think of are.

### Two rows ship as `warn` on purpose

- **`border` at 3.0.** ⚠️ **Every palette here fails it.** The hairline look
  trades away the WCAG non-text floor deliberately. It is a `warn` rather than
  a deleted row so the shortfall stays visible and countable — if these ever
  become real form borders rather than quiet rules, promote it.
- **`marker` and `bad`.** Honest placeholders: these were not hand-verifiable
  when the gate was written. **Read the build log for their real numbers and
  promote both to `fail`.**

**`hairline` is absent, not exempted.** It is designed to be barely visible.
A row for it would only invite someone to "fix" the design, and a gate that
flags intentional choices teaches people to ignore the gate.

⚠️ **The gate measures colour, not design.** It cannot tell you a palette is
ugly, that two links are indistinguishable from each other, or that an amber
warning reads as decorative. Passing is a floor, not an opinion.

`URITP_CONTRAST_STRICT=1` promotes every warning to a failure.

---

## How light and dark work

**Light and dark belong to the PALETTE, not to the theme.** A palette is two
rows in `colors.tsv` with the same `slug` and different `mode`:

```
slug       mode    bg          text        accent      ...
mclaren    dark    #292420     #f2f1ec     #f5842f
mclaren    light   #faf6f1     #2a2420     #a84f14
```

The theme names `mclaren` once. The toggle in the header decides which of the
two rows the browser reads. **That is the whole mechanism** — both rows are
always in the page, as two scoped blocks of CSS variables, and switching modes
switches which block applies. Nothing is recomputed and nothing is fetched.

**Why here and not in the join**, which is the obvious alternative:

1. **A palette is a relationship, not a list.** Its light and dark forms are
   two expressions of one identity, tuned against each other. Splitting them
   into two join columns would let you pair mismatched halves — `mclaren` dark
   with `paper-mono` light — and there is no reason to make that expressible.
2. **Only colour has modes.** Type, edges and density do not change when you
   flip the toggle. Putting modes in the join would force all four vectors to
   be mode-aware, or force one special case into the join's schema.
3. **A palette stays portable.** Copy the two `mclaren` rows into another
   project and both modes come along. If the light half lived in the join,
   half the palette would stay behind.

⚠️ **They are not automatic inversions and must not be treated as one.** The
same hue that reads well on near-black is often unreadable on near-white:
`mclaren` uses papaya for links in dark mode and a **deeper orange** in light,
because papaya on near-white measures about 2.5:1. Each mode is authored, and
the contrast gate checks both.

**If you ever genuinely need one theme's dark with another's light**, the
escape is a `color-light` column in `themes.tsv`, empty meaning "use the
palette's own light row." It is deliberately **not built** — an unused column
is a second place to look for a value, and no real case has appeared yet.

### The toggle, and one trap that cost an afternoon

The two entries under `theme.palette` in `mkdocs.yml` exist for exactly one
reason: **the toggle needs two palettes to switch between.** They set nothing
about the look.

🔴 **Do not add a `primary:` key to them.** `primary: black` lived there until
2026-08-01 and it silently defeated the `chrome` token: Material special-cases
black and writes a *literal* background onto `.md-header`, so no variable
could reach it. The banner was hard black in both modes — invisible in dark
mode because black is close to our dark `bg`, and obvious the moment anyone
opened light mode and found dark text on a black bar.

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

**Any CSS colour works** — the contrast gate parses hex and `oklch()`. Most
rows use `oklch(lightness chroma hue)` because it is the easiest thing to nudge
by hand: lightness is the percentage, chroma is how saturated it is (`0` is
pure grey), hue is the angle. Warmer means moving hue toward 90. Greyer means
dropping chroma. Less black means raising the lightness on `bg`.

⚠️ **The `mclaren` row is hex, deliberately.** Those values are copied verbatim
from `mawizorek/ClickUp_apps` → `shared/themes/colors.tsv`, which is a hex
grid. Converting them by hand would mean typing numbers nobody could check
against the source. Verbatim beats converted; the browser does not care.

⚠️ **`chrome` is the header bar**, and it is also the tab strip and the phone
drawer header. Every palette here sets it equal to `bg`, which is the
deliberate flat look: the header is the same ground as the page, separated by
a rule instead of a block of colour. Give it its own value and the banner
detaches. The phone browser's own bar colour follows it automatically —
Material reads the header's *rendered* background, so there is nothing to keep
in sync.

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
3. Either point an existing theme's `color` cell at it, or add a new row to
   `themes.tsv` if you also want different type, edges or density.
4. Push. **The contrast gate measures it immediately, even before you switch to
   it** — read the warnings in the run summary and fix them while the palette
   is still parked.
5. Point `active.txt` at that theme when it is clean.

A token still missing after the whole fallback chain **fails the build and
names the token**. A theme name that does not exist fails and lists the names
that do. Both are deliberate: a theme has no single page to fail on, so a
theme that quietly fell back to something else would be invisible.

**The build log prints what resolved**, including which cells came from a
fallback, which fonts were requested, and the tightest contrast pair in every
palette — so an inherited value is something you can see, not something you
have to remember.

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

**`mclaren` is the first palette copied across**, and copying it showed where
the two schemas do not line up. Three mappings are judgement calls, not
translations, and they are worth knowing about if you edit that row:

- **Their `text-soft` is teal** (`#5fc9d8`) — a deliberate McLaren secondary.
  Here `text-soft` is every lede and caption on the site, so teal prose would
  fight the links. It is warm grey instead.
- **Their teal lives in `accent-hover`**, so links go papaya → teal on hover.
  Upstream calls `accent` → `accent-2` "a two-hue sweep"; this is that sweep,
  spent on the one interaction a docs site has.
- **Light mode does not use papaya at all.** Papaya on near-white is around
  2.5:1. It uses a deeper orange, and the contrast gate is what settled the
  exact value rather than an eye.
