# The theme

Everything about how this site looks is in this folder. **No CSS. No code.**

| File | What it is | Format |
|---|---|---|
| [`active.txt`](active.txt) | **The switch.** One word: which theme the site wears. | one line |
| [`themes.tsv`](themes.tsv) | **The join.** One row per theme, four pointers. | grid |
| [`colors.json`](colors.json) | Vector 1 — the paint | record |
| [`typography.json`](typography.json) | Vector 2 — the voice | record |
| [`forms.json`](forms.json) | Vector 3 — the edges | record |
| [`spacing.json`](spacing.json) | Vector 4 — the density | record |
| [`contrast.tsv`](contrast.tsv) | **The gate.** Which pairs must be readable. | grid |

**Every file explains itself when you open it.** The JSON files carry a
`_README` block at the top and a `note` on every entry; this document is the
why, not the reference.

Edit, commit, wait ninety seconds, check the footer stamp.

---

## Why two formats

> **A table you read ACROSS stays a grid. A record you edit one at a time is
> JSON.**

`themes.tsv` is six short rows compared column by column — *which theme uses
which palette* — and that is exactly what a grid is for. `contrast.tsv` is the
same shape: thirteen uniform rows of the same four fields.

A **palette** is not that. It is fifteen tokens times two modes, edited one
palette at a time and almost never compared cell-to-cell against another. As a
TSV row that is thirty anonymous values in tab-separated sequence: correct,
diffable, and unreadable in an editor, where the header has scrolled off the
top and the only way to know which value you are changing is to **count
columns**. JSON puts the name on the line.

The grids replaced YAML earlier the same day for a good reason — a table
belongs in a table — and the mistake was applying that to all four vectors
instead of asking which of them are actually tables.

---

## The four things you will actually do

### 1. Swap the whole look — edit `active.txt`

One word. The names available are the `slug` column of `themes.tsv`.

### 2. Nudge one value — edit one line

Body text bigger? `typography.json` → `plex-docs` → `fs-body`. Background less
black? `colors.json` → `uritp-prp` → `dark` → `bg`. Menu rows too tight?
`spacing.json` → `standard` → `pad-row`.

That line is the only place the value exists.

### 3. Repaint a theme without making a new one

A theme is four pointers, so repoint one and leave the rest. Changing the
`color` cell of the `uritp-prp` row in `themes.tsv` swaps that theme's entire
palette — same type, edges and density, different paint. That is how the house
theme came to be wearing `mclaren`; put `uritp-prp` back in that one cell and
the slate returns.

**A new theme is for a new COMBINATION.** Repointing is for *same site,
different paint*.

### 4. Build a variant — add an entry, list only what changes

That is what `inherits` is for. `uritp-granite` in `colors.json` is the worked
example: it names `uritp-prp` as its parent, lists ten neutrals, and **does not
mention the accents at all**, so it keeps the house blue automatically.

---

## The one rule

> **An absent value inherits. A present value wins.**

Same rule at both levels, so you learn it once.

- **`themes.tsv`** — an empty vector cell takes the `_default` row's value.
- **a vector file** — a token you do not list comes from the entry named in
  `inherits`, then from `_base` in the same file.

The chain is **your value → what you inherit from → `_base` → the build fails
and names the token.**

⚠️ **Absent means inherit, never "nothing".** A value that is deliberately off
is written out: `"shadow": "none"`.

**`_base` and `_default` are the safety net.** They must stay complete, and
`active.txt` may never point at one.

---

## Colour: why some values are oklch and some are hex

**Both are legal, the contrast gate parses both, and the difference is not an
accident — but it is not a rule you have to obey either.**

**`oklch(lightness chroma hue)` is the house default**, because it is the one
you can *nudge*. Three numbers you can reason about: the percentage is
brightness, chroma is saturation (`0` is pure grey), hue is an angle (90 warm,
250 cool). Want it warmer? Move one number. Want it less black? Raise the
lightness on `bg`. In hex you would be guessing at three channels at once.

**Hex is for values copied verbatim from somewhere else.** `mclaren` came from
`mawizorek/ClickUp_apps`, which is a hex grid. Converting thirty brand colours
by hand would mean typing numbers nobody could check against the source, and
"is this the real McLaren papaya" would stop being answerable. Verbatim beats
converted.

**So the rule is: author in oklch, copy in hex.** If you want `mclaren`
normalised to oklch anyway, that is a real option and the contrast gate makes
it safe — it prints a measured ratio for every pair, so a conversion that
shifted a colour would show up as a moved number rather than a vibe.

---

## One page, or one folder, wearing something else

```yaml
---
title: Electrics
theme: utility
---
```

On an `index.md` that skins the **whole folder**, at any depth. Write
`theme: default` to stay on the site theme inside a themed folder — a word
rather than the site theme's name, which would rot on the next swap.

### ⚠️ Two waterfalls, opposite directions

| | Direction |
|---|---|
| **The LOCK** — a gated `index.md` | **The parent wins.** |
| **The SKIN** — a themed `index.md` | **The child wins.** |

**Precedence follows consequence.** A lock you can undo by accident, in a file
nobody is looking at, is not a lock — so the folder overrules the page. A skin
is a preference with nothing at risk, so the more specific statement wins.

🔴 **Do not "make them consistent."** Both fire off `index.md` and walk the same
folders, which makes unifying them look like tidying. The day somebody does, a
locked page quietly publishes.

### When the name is wrong

**It falls back to the site theme, renders normally, and is reported by name.**
It does not fail the build — the opposite of what a bad name in `active.txt`
does, and for a reason: the site theme has no single page to fail on, so it has
to stop everything. A page theme has exactly one.

### Three things to know before using it

1. **It reskins the WHOLE WINDOW.** Sidebar, header and drawer share the page's
   tokens. Landing on a themed page recolours everything; it is not a tint.
2. **It cannot change which webfont downloads.** Material's loader is global. A
   page whose theme names another family gets its sizes and colours but the
   site's typeface. The build warns by name.
3. **Think twice about theming by MEANING.** The palette already uses colour
   semantically — `bad` is red, `marker` is amber for unconfirmed values. A
   red-tinted Safety section would stop the danger colour reading as danger on
   the only pages where danger is the subject. Department wayfinding
   (Electrics, Audio) has no such collision.

---

## Is it readable? — `contrast.tsv`

**Every build measures every palette, both modes, and reports anything that
cannot be read.** `fg` · `bg` · `min` (4.5 text, 3.0 non-text) · `level`
(`fail` stops the build, `warn` only reports) · `note`.

**Only the ACTIVE palette can fail.** A parked one cannot hurt a reader today
and should not hold the site hostage — but it is still measured, so **you find
out a palette is broken before you switch to it.**

To grant an exemption, set `level` to `warn` **and say why in the note.** To
remove a check, delete the row. Both show up in a diff, which is the whole
reason this is a file and not a list inside the code.

### What it found on its first run

Three real failures in the live palette: dark `text-soft` 3.91 → **5.21**,
light `text-soft` on `surface-2` 4.26 → **4.73**, light `accent` 4.02 →
**5.14**.

The middle one is the argument for the whole gate. That colour had been
corrected by hand an hour earlier, checked against the page, and **passed** —
but nobody thought to check it against a *callout*. **The pairs you think to
check are not the problem.**

### Two rows ship as `warn` on purpose

- **`border` at 3.0** — ⚠️ **every palette fails it.** The hairline look trades
  the WCAG non-text floor away deliberately. Kept as a warning rather than a
  deleted row so the shortfall stays visible and countable.
- **`marker` and `bad`** — honest placeholders, not hand-verifiable when the
  gate was written. **Read the build log for their real numbers and promote
  both to `fail`.**

**`hairline` is absent, not exempted.** It is designed to be barely visible; a
row for it would only invite someone to "fix" the design.

⚠️ **The gate measures colour, not design.** It cannot tell you a palette is
ugly or that two links are indistinguishable. Passing is a floor, not an
opinion. `URITP_CONTRAST_STRICT=1` promotes every warning to a failure.

---

## How light and dark work

**They belong to the PALETTE, not the theme.** Each palette in `colors.json`
has a `dark` block and a `light` block. The theme names the palette once; the
toggle decides which block the browser reads. Both are always in the page as
two scoped sets of CSS variables — nothing is recomputed, nothing is fetched.

**Why here and not in the join:** a palette is a *relationship*, not a list —
its two forms are tuned against each other, and splitting them into join
columns would let you pair `mclaren` dark with `paper-mono` light for no
reason. Only colour has modes at all. And a palette stays portable: copy the
entry, both modes come with it.

⚠️ **They are not automatic inversions.** A hue that reads well on near-black is
often unreadable on near-white: `mclaren` uses papaya for links in dark mode
and a deeper orange in light, because papaya on near-white measures about
2.5:1. Each mode is authored, and the gate checks both.

### The toggle, and one trap that cost an afternoon

The two entries under `theme.palette` in `mkdocs.yml` exist for one reason:
**the toggle needs two palettes to switch between.** They set nothing.

🔴 **Do not add a `primary:` key.** `primary: black` lived there until
2026-08-01 and silently defeated the `chrome` token: Material special-cases
black and writes a *literal* background onto `.md-header`, so no variable could
reach it. Hard black in both modes — invisible in dark, and obvious the moment
anyone opened light mode and found dark text on a black bar.

---

## Adding a whole new palette

1. Add an entry to `colors.json` with a `dark` and a `light` block.
2. List every token — **or** name a parent in `inherits` and list only what
   differs.
3. Point an existing theme's `color` cell at it, or add a row to `themes.tsv`
   if you also want different type, edges or density.
4. Push. **The gate measures it immediately, before you switch to it** — read
   the warnings and fix them while it is still parked.
5. Point `active.txt` at it when it is clean, or name it in one page's
   frontmatter to try it in place.

**The build log prints what resolved** — which values came from a fallback,
which fonts were requested, the tightest contrast pair in every palette, and
any page wearing a theme other than the site's.

---

## What is deliberately NOT a dial

`docs/stylesheets/uritp.css` still contains numbers. The test: **a token
answers "what should this look like"; a literal answers "where does this sit
relative to the thing beside it".** A heading's bottom margin in `em` of its
own size, an icon's offset inside its box, a line height of 1.3 — those follow
the tokens automatically because they are relative. Fifty more columns nobody
sets would make this worse, not better.

Three named exceptions, none of which should become themeable:

- **Breakpoints.** Material's own, matched deliberately so our rules switch on
  the same line its rules do. A theme that could move them would desynchronise
  our layout from the component's — the collision class that cost two fixes in
  one day.
- **The print block.** Paper is a physical constraint, not a theme: ink on
  white at full contrast, whichever skin was on screen. A venue page carried
  into a production meeting is the case that must never break.
- **Which Material class reads which token.** That is the wiring, not the look.

If you need a value with no home, add it to `_base` in the right file **and** to
`REQUIRED` in `hooks/theme.py`, in the same commit. `chrome`, `pad-row` and
`fs-nav` all arrived that way, each because a real question turned out to have
no answer.

---

## Relation to the app themes

A deliberate port of `mawizorek/ClickUp_apps` → `shared/themes/` so the
vocabulary matches, but **a port, not a link.** That system resolves in the
browser at runtime for apps with a live theme picker; this one composes at
build time because MkDocs emits static HTML. Editing a grid there changes
nothing here, and the schemas differ — that one carries light mode as extra
columns and has tokens for objects a docs site does not have.

**`mclaren` is the first palette copied across**, and copying it showed where
the schemas do not line up. Three mappings are judgement calls, not
translations:

- **Their `text-soft` is teal** — a deliberate McLaren secondary. Here
  `text-soft` is every lede and caption, so teal prose would fight the links.
  Warm grey instead.
- **Their teal lives in `accent-hover`**, so links go papaya → teal on hover.
  Upstream calls `accent` → `accent-2` a "two-hue sweep"; this spends it on the
  one interaction a docs site has.
- **Light mode does not use papaya at all**, and the gate settled the exact
  replacement rather than an eye.
