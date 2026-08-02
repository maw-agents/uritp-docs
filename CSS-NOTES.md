# CSS notes

Why the stylesheets are the way they are. **Deliberately outside `docs/`** so it
never renders as a reader-facing page: it documents the machine, not the theatre.

One section per sheet in `docs/stylesheets/`, same numbers. Each sheet carries a
short header with the load-bearing warnings and a pointer here; the long version
lives below.

> ⚠️ **This file is a RECORD, not a rule.** If a note here disagrees with the
> CSS, the CSS wins and this file gets corrected in the same pass.

**Values** (colour, type, spacing) live in `theme/*.tsv`, see `theme/README.md`.
**Rules** live in `docs/stylesheets/`. **Reasons** live here. Three layers, and
keeping them apart is the entire point of the 2026-08-02 split.

---

## Why this file exists at all

`uritp.css` reached **34.9KB** on 2026-08-01, and roughly two thirds of it was
prose. Every bug fixed that day got written up where it happened, which was the
right instinct and the wrong location.

**Tokenising the theme made the file bigger, not smaller.** It removed *values*
and never removed *rules*, and `color: var(--u-text-soft)` is longer than the
hex it replaced. The file grew from both ends at once: more prose above, longer
declarations below.

At 34.9KB it crossed the line where an agent can read it back whole. Four reads
in one session clipped at the same byte with no error, so the last ~6KB (tabs,
links, the gate, the page foot, mobile and print) was being *reasoned about*
from the section index at the top rather than from the rules themselves.

⚠️ **That is the real cost and it is worth naming precisely: the file did not
stop working, it stopped being editable.** A stylesheet nobody can read whole is
a stylesheet nobody can safely change, and the site's entire look sat behind it.

`hooks/sizecheck.py` + `size-budget.tsv` now fail the build before that can
happen again. **The split was the cure; the gate is the vaccine.**

---

## 00 Bridge

### `primary:` in mkdocs.yml is a trap, and the reason it was kept was false

`primary: black` sat in `mkdocs.yml` until 2026-08-01 silently **defeating** the
`chrome` colour token. Material special-cases black in `palette/_primary.scss`:
instead of only setting `--md-primary-fg-color` (which our bridge overrides), it
writes a **literal background** onto the component, so no variable could reach
the header at all. The banner was hard black in **both** modes.

Nobody caught it in dark mode because black is close enough to our dark `bg`; in
light mode the background stayed black while `--md-primary-bg-color` (which we
do control) flipped the text to the light-mode `on-chrome`, giving dark-brown
text on a black bar. Michael: *"the header didn't render well in light mode... it
kept banner color but swapped color text."*

⚠️ **And the documented reason for keeping the key was wrong.** It was recorded
as the source of the phone browser's `theme-color` meta tag. It is not.
Material's palette component reads the **header's computed background** and
writes that into the meta tag on every scheme change. With the key gone, the
phone's browser bar now tracks the `chrome` token per mode, for free, which is
what was wanted all along.

The two palette entries still have to exist: the scheme **toggle** needs two
palettes to switch between. That is now their only job. First entry is the
default, so the site opens dark.

---

## 10 Type

### `font-weight` is a literal in every rule and arguably should not be

The stylesheets claim their remaining literals are *proportions, not style*: a
heading's bottom margin in `em` of its own size, an icon's offset inside its
box, the 1.3 line-height on an h2. Those track the tokens automatically because
they are relative.

**`font-weight` does not survive that test.** Weight is a style decision, and a
typography vector that cannot set it is missing a real dial. `plex-large` would
plausibly want lighter headings at its larger sizes. Not changed because it is
eight rules and its own PR. Named so it stops being invisible.

Zero top margin on `p` is load-bearing and has a known victim: see **30 Content**.

---

## 20 Chrome

### The GitHub repo block

Name, star count, fork count, in the header and at the top of the mobile drawer.
Removed 2026-08-01, Michael: *"the git icons doing nothing in the main menu."*
They were not doing nothing, they were reporting **0 stars and 0 forks on a
private-audience venue reference**, which is worse. The way back to source is now
one worded line at the foot of each page (`hooks/pagefoot.py`).

⚠️ `repo_url` in `mkdocs.yml` **stays**. MkDocs builds `page.edit_url` from it.
Hiding the display is not deleting the config.

### The badge beside a nav title is OUR OWN frontmatter

`status:` is a **reserved Material key** that renders a badge beside a nav title
(`partials/nav-item.html` calls `render_status` whenever `nav_item.meta.status`
exists). Material knows `new`, `deprecated` and `encrypted`, and falls back to
`--md-status` (information-outline) for anything else. Every page here carries
`status:` for `hooks/visibility.py`, so every page got the fallback glyph, and a
folder with no `index.md` got none, because a bare section has no page meta.

⚠️ **That pattern was blamed on `material.extensions.preview` on 2026-08-01,
wrongly, and it cost a working feature.** The badge was then hidden for about two
hours, and Michael asked for it back the same morning: *"lost the info icon which
i want back."* It is deliberate, it is wanted, and it is **not** leftover
Material chrome to be tidied away.

Only two values can ever reach the sidebar (`hidden` is never built, `unlisted`
is pruned from the nav) so the badge is a **two-state legend**, readable page vs
locked page, rather than an icon on every row for its own sake. That is the whole
argument for re-pointing `gated` at Material's shield-lock.

Tooltips come from `extra.status` in `mkdocs.yml`. Hover-only, so they are a
desktop and screen-reader affordance; **on a phone the glyph carries all of it.**

⚠️ A **quick link carries no badge**: `hooks/quicklinks.py` emits `Link` objects,
not `Page`s, and that template block only fires on a page's own meta. So the same
document shows a glyph in Venues and a bare label under Quick Links. A real
inconsistency, accepted: a shortcut bar is about speed, and Material gives a
`Link` no meta to read.

---

## 30 Content

### The callout body inset, and why it needs padding instead of a margin

⚠️ Material pads the callout box **horizontally only** (`.admonition
{ padding: 0 .6rem }`) and leaves the gap under the title bar entirely to the
first child's **own top margin**, which its default type scale supplies as
`p { margin: 1em 0 }`.

`10-type.css` sets `p { margin: 0 0 .85em }`. **Zero top.** So there was nothing
left to make that gap, and the first line of every callout sat flush against the
title bar's bottom rule. Michael, 2026-08-01: *"content boxes are a bit tight to
their header banners."*

Neither half is wrong on its own. Material leaning on a child margin is ordinary;
a prose rhythm with no top margins is deliberate. **The pair is the bug**, the
same shape as the drawer chevron in *80 Mobile*, where a component's absolute
positioning depended on a title height we had flattened. **A component whose
spacing lives somewhere we can reach is a collision waiting for the day we reach
there.**

So the body carries real padding, and the first body element's top margin is
zeroed so that padding is the **only** source of the gap: an h3 or a nested
callout landing first cannot stack its own margin on top of it.

`details` gets every rule too. It extends `.admonition` in Material's own SCSS,
so it inherits the identical box and the identical omission, and it was **also**
missing our horizontal inset entirely, because a `details` element does not carry
the `.admonition` *class* the old selector keyed on.

⚠️ **The horizontal inset is a SUM:** Material's `.6rem` on the box **plus**
`--u-pad-block` on the child. Recorded because it is not obvious from either
half. Zeroing Material's share would make `pad-block` the single dial, but
`.md-typeset__scrollwrap` (`margin: 1em -.6rem`) and `.md-typeset__table`
(`padding: 0 .6rem`) both escape that padding to let a table inside a callout run
full width, so removing it breaks them. **Left as a sum on purpose.**

### Callout flavours: the last place on the site wearing colours nobody chose

Until 2026-08-01, Material shipped twelve admonition flavours each with a
hardcoded Material-Design tint in `extensions/markdown/_admonition.scss`: a
border colour, a title background mixed from the same tint, and the icon.

So the callout's **shape** was ours and its **colour** was Material's. Two owners
on one component, and a theme swap moved only one of them. Michael spotted it the
honest way: **a blue note callout on a site whose palette has no blue in it at
all.** McLaren is papaya and teal.

⚠️ **THIRD TIME THIS EXACT PATTERN HAS BITTEN.** `primary: black` wrote a literal
onto `.md-header` where we expected a variable; the drawer chevron's absolute
position depended on a height we had changed; now this. **The rule that keeps
emerging: MATERIAL WRITES LITERALS, NOT VARIABLES, WHENEVER A VALUE CAME FROM ITS
OWN CONFIG RATHER THAN A SCHEME. Assume a literal and go and look.**

⚠️ **Specificity.** Material's flavour rules are (0,3,0) and ours would tie at
(0,3,0), winning only on load order. Order is real but invisible, and a tie that
depends on it is a trap for whoever reorders `extra_css`, which the 2026-08-02
split made a much easier thing to do by accident. The `[data-md-color-scheme]`
prefix (always present; it is what the whole bridge keys on) takes ours to
(0,4,0) and they win outright.

**The map. Twelve flavours, five tokens, and the collapse is deliberate:**

| Flavours | Token | Why |
|---|---|---|
| `note` `abstract` `info` | `accent` | the theme's own voice |
| `tip` `success` `question` | `good` | the positive one |
| `warning` `caution` | `marker` | already the "unconfirmed" amber |
| `failure` `danger` `bug` | `bad` | already the error red |
| `example` `quote` | `text-soft` | neutral, not a signal |

Michael's call, 2026-08-01: *"danger is the only one that should stay red, note
and warning could align with the chosen theme colors."* **Danger stays red**
because red means stop, and on a site whose subject includes rigging and lock-up
that is worth more than palette purity. But it stays red **as a token**, so each
palette tunes its own red and none can drift into something illegible. `bad` and
`marker` already did exactly this job; adding `danger` and `warning` columns
beside them would have been two names for one truth.

⚠️ **`good` is the one genuinely new colour.** No palette had a positive hue.
Every value was **derived rather than invented**: each palette's own `bad`
supplied the lightness and chroma, and only the hue swung to 150. **That is
derived, not measured.** OKLCH lightness is not perceptually flat across hue, so
a lightness that works at red may not at green. `theme/contrast.tsv` carries
`good` against both `bg` and `surface-2` as **warn**, and the first build's
printed numbers are the thing to read before trusting any of them.

⚠️ **As of 2026-08-02 no page on this site writes a `success`, `tip` or
`question` callout**, so that colour column ships unseen and those two contrast
rows are still first-draft guesses. Writing the first one turns them into a real
reading.

The **icons** are still Material's and that is correct: a pencil, an alert
triangle, a lightning bolt. Those are semantics, not style.

### Syntax highlighting is the remaining hardcode, and it is not ours

A fenced code block is coloured by Pygments through Material's own
`_codehilite.scss`: dozens of literal hues for keywords, strings and comments,
none of them tokens, none of them measured by the contrast gate. **It does not
show today because no page here has a code block.** The moment one lands it will
be the most off-palette thing on the screen. Same class as the callout flavours
above, an order of magnitude more values.

---

## 40 Components

The page foot is deliberately the quietest thing on the page: a way back to the
source for the one person who edits this, not a call to action for the fifty who
read it. Underlined only on hover or focus, so it is still obviously a link the
moment anyone goes looking for one.

⚠️ `content.action.edit` is **not** enabled, on purpose. It puts a pencil at the
top right of every page, which reads as an invitation to edit on a site whose job
is to be the settled answer, and it renders as an anchor with **no text**, which
a screen reader announces as a raw URL.

⚠️ The **build stamp** is the only signal that a build failed. Pages keeps
serving the previous commit: no banner, no error page, the site simply stops
changing. Do not hide it to tidy the footer.

---

## 80 Mobile

### Three separate repairs. Do not collapse them.

**1. Scheme.** Material's slide-in drawer panels do not inherit the slate scheme
and render white-on-white in dark mode: the submenu is unusable. Force every
drawer surface onto the page background.

**2. The blocked chevron** (fixed 2026-08-01). Material positions the drawer's
back arrow **absolutely**, at `top .4rem / left .4rem`, because its own title is
a tall block with the text pushed to the bottom. Repair 1 flattened that title to
a single line and moved the text up, straight underneath the arrow, which then
sat on top of the first letter (*"VENUES" with a chevron through the V*).
**One fix quietly broke the other.**

The repair is to stop fighting the absolute position and lay the title out
honestly: a flex row, arrow first, text second, real space between them. Now the
two cannot overlap no matter what the title height becomes.

**3. The tall section row** (fixed 2026-08-01, **on the second attempt**).
Michael: *"nav menu has weird spacing for safety."* Safety was the only top-level
section with an `index.md`, so under `navigation.indexes` it was the only row
Material renders as a `.md-nav__container`: a wrapper that **also** carries
`.md-nav__link`, holding a nested anchor and label that carry it too. Three
elements, one class.

⚠️ **The padding was never the problem, and the first fix assumed it was.**
Material already writes `.md-nav--primary .md-nav__link > .md-nav__link
{ padding: 0 }`: the wrapper is padded and the children are not. Zeroing the
wrapper therefore removed the row's **only** padding and the title went flush to
the drawer edge. The real culprit was `min-height: var(--u-touch)`, which
Material has no equivalent of and no rule to cancel, so the row became a 44px
child inside a 44px padded parent.

So: cancel the tap floor exactly where Material cancels the padding, and let the
wrapper be the row. Children stretch to fill it, which keeps the whole 44px
tappable instead of just the text.

**Two lessons, and the second is the expensive one.** A blanket rule on a
component class is a bet the component only renders one shape. And **when a fix
changes the symptom instead of removing it, the diagnosis was wrong.**

### Breakpoints are a named exception

`76.1875em` (drawer) and `44.9375em` (phone) are **Material's own** widths,
matched deliberately so our rules switch on the same line its rules do. A theme
that could move them would let a palette desynchronise our layout from the
component's, the collision class that cost two separate fixes in one day.

### Desktop-only changes are easy to over-claim

Dropping `navigation.expand` and `navigation.sections` on 2026-08-01 changed the
**desktop** sidebar only. The phone drawer always drilled down and is untouched
by either feature. ⚠️ **Both had to go**: removing either alone leaves the tree
open, which is why they are commented out in `mkdocs.yml` rather than deleted.

⚠️ **Per-folder expand defaults are not possible from config.** Material has no
per-section expand key and `awesome-nav` has no expand feature at all, so *"open
Venues but collapse the rest"* needs a `custom_dir` override of
`partials/nav-item.html`, which means vendoring a template that drifts on every
Material upgrade. Not done; recorded so the next person does not go looking.

---

## 90 Print

Overrides the **tokens**, not Material's variables, so the bridge keeps doing the
translating and the block stays short forever.

⚠️ **Named exception: these literals are deliberate.** Paper is not a theme, it
is a physical constraint: ink on white, at maximum contrast, whichever skin was
on screen. A themeable print palette would let a swap produce an unreadable
printout, and **a venue page taken into a production meeting is exactly the case
that must never break.**

⚠️ The **callout tints come through here too**, now that they are tokens. On
paper they collapse toward ink: a printed callout is told apart by its rule and
its title, not by a wash of colour that costs toner and reads as grey anyway.
`marker` and `bad` keep a little hue because caution and danger are worth
distinguishing on a page somebody is holding in a theatre.

⚠️ **UNVERIFIED.** A browser prints a closed `details` element **closed**. The
print block forces *tabs* open; whether it does the same for a folded `???`
callout has not been tested, and losing content on paper is the failure that
matters most here. Logged in `next-build-spec.md`.

---

## The pattern underneath most of this page

Six of the bugs recorded above are the same bug:

**Two systems own one component, and only one of them knows it.**

- Material wrote a literal background where we expected a variable (`primary`)
- Material's absolute positioning depended on a title height we had flattened
- Material's callout gap depended on a paragraph margin we had zeroed
- Material's flavour tints were literals the theme could not reach
- Material's `status:` badge read frontmatter we had put there for something else
- Material's `.md-nav__container` renders one class as three elements

**The test before changing anything Material also styles: go and read its SCSS
for that component.** Not the docs, the source. Every one of these was visible
there and none of them was visible from our side.
