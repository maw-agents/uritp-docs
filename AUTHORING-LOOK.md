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
> by editing one cell. **How light and dark work is explained there too.**
> This file used to restate all of that and now points at it instead: **one
> place, referenced, never restated.** A copy of a value is a copy that rots,
> and this document proved that twice on 2026-08-01.

**This file describes:** `docs/stylesheets/uritp.css` · `docs/stylesheets/links.css`
· `hooks/pagefoot.py` · the `theme:` and `extra:` blocks in `mkdocs.yml`

> ⚠️ **Split out of AUTHORING.md 2026-08-01, for the reason the gate reference
> was.** There is no partial-edit path through this toolchain, so every change
> re-emits the whole file. A 20KB document rewritten five times in a day is
> five chances to silently drop a section. Highest churn, smallest file.

---

## 🔴 `uritp.css` has crossed the size wall — read this before planning a style change

**The stylesheet is 34.8KB. The read and write ceiling for an agent is ~30KB.**
That is not a style rule, it is a hard tooling limit: a fetch clips silently at
about 30KB, and a write of a file that cannot be read back whole cannot be
verified. **So no agent can currently edit `uritp.css` safely at all** — which
is why the nav typography Michael asked for on 2026-08-01 (*"folder headers
stand out a bit differently than the actual files underneath them"*) is **not
shipped**, while the two things reachable from `mkdocs.yml` are.

The file did not get careless; it got documented. Most of its bulk is the
commentary this repo runs on, and that commentary is the reason its repairs
stopped repeating.

**The fix is a split, and it is structural** — awaiting Michael's word. The
natural seams are already the file's own section banners: BRIDGE + A11Y + TYPE
in the core, CHROME + NAV + the mobile drawer in a second file, the components
(TABLES, MARKERS, CALLOUTS, TABS, LINKS, GATE, PAGE FOOT) in a third, PRINT in
its own. `extra_css` takes a list, so the split costs one line in `mkdocs.yml`.

⚠️ **Do not "solve" this by starting a second stylesheet beside the current
one.** The file's own header argues against exactly that: two sheets drift the
moment one gains a rule. A SPLIT is one system in four files with the section
banners as the boundaries; a SECOND SHEET is two systems. `links.css` is the
allowed exception because it owns one marker and nothing else.

---

## Editing the stylesheet

`docs/stylesheets/uritp.css` contains **no colour, no font name, and no size,
radius or gap that anyone would want to reskin.** Those are `--u-*` tokens
composed from `theme/`.

⚠️ **A literal value committed there silently opts that element out of every
future swap.** The build fails by name when a palette forgets a token; it
cannot detect a stylesheet that stopped asking for one. If you need a value
with no token, add the column to the right grid in `theme/` **and** its name to
`REQUIRED` in `hooks/theme.py`, in the same PR. `chrome`, `pad-row` and
`fs-nav` all arrived that way, each because a real question — *where do I make
the header a different colour / the menu rows roomier / the menu text bigger* —
turned out to have no answer in the grid.

**The numbers that remain are proportions, not style**, and the distinction is
why the file is not one giant variable list. A token answers *what should this
look like*. A literal answers *where does this sit relative to the thing beside
it*: a heading's bottom margin in `em` of its own size, an icon's offset inside
its box, a 1.3 line-height. Those track the tokens automatically because they
are relative. Turning them into dials would mean fifty columns nobody sets.

**Two named exceptions**, both of which must stay hard-coded:

- **Breakpoints.** The two widths where the layout changes are Material's own,
  matched deliberately so our rules switch on the same line its rules do. A
  theme that could move them would let a palette desynchronise our layout from
  the component's — the exact collision class that cost two fixes in one day.
- **The `@media print` block.** It overrides the tokens rather than Material's
  variables, so the bridge keeps doing the translating and the block stays
  short forever. Paper is not a theme, it is a physical constraint: ink on
  white at full contrast, whichever skin was on screen. A themeable print
  palette would let a swap produce an unreadable printout, and a venue page
  carried into a production meeting is the case that must never break.

The file has one **bridge** block at the top mapping `--u-*` onto Material's
`--md-*` variables. That is the only place the two systems touch.

⚠️ **The bridge must stay scoped to `[data-md-color-scheme=...]`, never
`:root`.** Material sets its scheme colours from those attribute selectors; an
unscoped rule loses the specificity contest and the dark toggle breaks in a way
that only shows up in one mode.

⚠️ **A bridge variable only works if Material actually reads that variable for
the thing you are trying to change.** See the `primary: black` trap below: for
several of its palette values Material writes a *literal* onto the component
instead, and no amount of correct variable-setting reaches it.

### Which file owns which question

Every look question splits the same way, and asking it in the wrong file is how
an hour disappears:

| The question | Lives in |
|---|---|
| What colour / size / weight is this | a **cell** in a `theme/*.tsv` grid |
| Which element gets that value at all | a **rule** in `uritp.css` |
| Whether the component exists to be styled | a **feature or extension** in `mkdocs.yml` |

So *"make the header bar a different colour"* is a cell (`chrome`), *"make the
header bar taller"* is a rule, and *"collapse the sidebar by default"* is
neither — it is a feature flag, and no amount of CSS reaches it.

---

## The sidebar tree

**Collapsed by default since 2026-08-01** (Michael). Sections open on click; the
ancestors of the page you are on open by themselves, so a deep link never lands
inside a closed tree.

**Two features had to go, and removing either one alone does nothing:**

| Removed | Did |
|---|---|
| `navigation.expand` | Forced every section open on desktop. |
| `navigation.sections` | Rendered every **top-level** folder as a flat label group — a shape Material draws with **no toggle at all**. |

That second one is the whole complaint. Michael: *"I keep clicking the folder
titles that don't hold anything."* Under `navigation.sections` a section title
is only a link if the folder happens to carry an `index.md`, and most do not —
so the row looked identical to a page and did nothing when tapped. With the
feature gone those rows are real expand/collapse toggles with a chevron, which
is simultaneously the fix for the dead click **and** the first honest visual
difference between a folder and a page.

**Desktop only.** The phone drawer has always drilled down and neither feature
touched it.

### ⚠️ Per-folder defaults are not available from config

*"Can we set it per folder?"* — **no, and not from any file we currently own.**
Material's `navigation.expand` is a global boolean with no per-section
equivalent, and `awesome-nav` (which builds our sidebar) has **no expand or
collapse feature at all**; it controls order, titles, visibility and nothing
about open state. Verified against its own docs, not assumed.

What it would actually take, if the answer ever needs to be yes:

`partials/nav-item.html` renders one checkbox per section and decides `checked`
from `"navigation.expand" in features or nav_item.active`. A `custom_dir`
override of that partial could read the folder's own frontmatter instead — e.g.
`expand: true` in a section's `index.md` — and check the box for that section
only.

Three things to know before anyone starts:

- **It would be this repo's first template override.** Everything so far is
  config, hooks and CSS, which survive a Material upgrade. A copied partial
  does not: it silently keeps rendering the old version's markup.
- **It only reaches folders that have an `index.md`.** A bare section has no
  page meta — the same limitation that gives those rows no `status:` badge.
- **Do not try it with a post-build regex on the checkbox ids.** They are
  positional (`__nav_3`), so the rule would re-point itself the day somebody
  adds a folder above.

### Making a folder row *look* different from a page row

Asked for on 2026-08-01 and **not yet shipped** — it is a `uritp.css` change and
that file is over the write cap (see the top of this document). When the split
lands, the rules belong in the NAV block, keyed on `.md-nav__item--nested >
.md-nav__link` for the folder rows, and every value must come from a token:
case and tracking from `track-caps`, colour from `text-soft` or `text-strong`,
never a literal.

---

## The chrome

What is deliberately **not** on this site, and why. Every one is a reversal of
a Material default; none should be restored without reading the reason.

| Removed | Was | Why |
|---|---|---|
| The GitHub repo block | Name, star count and fork count in the header and at the top of the mobile drawer | It reported **0 stars, 0 forks** on a venue reference nobody stars. `repo_url` stays in `mkdocs.yml` — this hides the display, not the config, and `page.edit_url` is built from it. |
| `content.action.edit` | A pencil icon top-right of every page | It reads as an invitation to edit a document whose job is to be the settled answer, and it rendered as an anchor with **no text at all** — a screen reader announced the raw URL. Replaced by `hooks/pagefoot.py`. |
| `material.extensions.preview` | Hover card previewing a link's target | Previews need hover and this site is read on a phone. **⚠️ The second reason once given — that it iconised every nav row — was WRONG; see below.** The removal stands on the hover argument alone, and adding it back now costs nothing in icons. |
| `navigation.expand` + `navigation.sections` | The whole sidebar tree open, top folders as untoggleable labels | Removed together 2026-08-01 for a default-collapsed tree. See *The sidebar tree* above. **Removing one without the other does nothing.** |
| `theme.font` | A font block in `mkdocs.yml` | It named the same families as the typography grid, in a second file, kept in agreement by hand. `hooks/theme.py` writes it from `webfont-text` / `webfont-code` now. **Do not add it back** — it would be overwritten every build. |
| `theme.palette[].primary` | `primary: black` on both palette entries | It **silently defeated the `chrome` token** in both modes. See below. **Do not add it back.** |

And one thing deliberately **kept**, which is rarer and therefore worth more
words.

### 🔴 `primary: black`, and a variable that could never win

Michael, 2026-08-01: *"the header didn't render well in light mode… it kept
banner color but swapped color text."* Exactly right, and the cause is not in
our stylesheet at all.

Material special-cases `black` in `palette/_primary.scss`. For every ordinary
colour it only sets variables, which our bridge overrides cleanly. For `black`
it **writes literals onto the components**:

```scss
[data-md-color-primary="black"] {
  .md-header { background-color: hsla(var(--md-hue), 15%, 9%, 1); }
  html & .md-nav--primary .md-nav__title[for="__drawer"] { ... }
  .md-tabs { background-color: ... }
}
```

So `--md-primary-fg-color: var(--u-chrome)` was correct, live, and **unread**.
The banner was hard black in *both* modes. Nobody caught it in dark mode
because that black is close to our dark `bg`. In light mode the background
stayed black while `--md-primary-bg-color` — which Material *does* read from
the variable — flipped the text to the light-mode `on-chrome`. Dark brown text
on a black bar.

Note the drawer rule carries `html &`, which outranks our own drawer-title rule
on specificity. Two of our tokens were being ignored, not one.

**The fix is deletion.** With no `primary` key, no `[data-md-color-primary]`
rule matches and Material's own default applies —
`.md-header { background-color: var(--md-primary-fg-color) }` — which is the
variable we were setting correctly all along.

⚠️ **The reason that key was kept was itself false, and it was written down
twice.** Both this file and `mkdocs.yml` claimed `primary` was the source of
the phone browser's `<meta name="theme-color">`. It is not. Material's palette
component reads the **header's computed background** and writes that into the
meta tag on every scheme change:

```ts
const style = window.getComputedStyle(getComponentElement("header"))
return style.backgroundColor…   // → meta.content
```

So removing the key did not cost the browser-bar colour — it **fixed** it. The
phone's bar now tracks the `chrome` token per mode, with nothing to keep in
sync.

**The transferable lesson**, and it is the third time today: *a plausible
reason is not a verified one.* "Keep `primary` for the theme-color meta" was
never tested, survived in two canonical files, and defended a line that was
actively breaking the feature it sat next to. It took reading
`palette/index.ts` to disprove — the same move that found the ⓘ badge and the
nav row height.

### What `theme.palette` still does

**One job: the toggle needs two entries to switch between.** That is the whole
remit. Each entry names a `scheme` and its toggle icon, and nothing else.

There is also no flash-of-unstyled-colour to guard against, whatever an older
comment implied: `hooks/theme.py` writes its `<style>` into the HTML at **build**
time, so the tokens are present in the first byte the browser parses. That idea
was inherited from the runtime app resolver and never applied to a static site.

### Changing an icon — three different answers to one question

"The icon in the header" means at least three separate things here, and each
lives somewhere else. Get the wrong one and you will edit a file that has no
effect.

| The icon | Where it comes from | How to change it |
|---|---|---|
| **The callout's title-bar glyph** (⚠ on a warning, ✕ on a danger) | A Material CSS variable per type — `--md-admonition-icon--warning` — holding an **inline SVG data-URI**, painted through `mask-image` | Redefine that variable in `uritp.css` with your own SVG. It is a variable, so this is an override and not a patch. |
| **The site logo** beside the title | `theme.logo` / `theme.icon.logo` in `mkdocs.yml` | Currently unset, so the header shows text alone. Point it at a file in `docs/` or a bundled Material icon name. |
| **The ⓘ / 🔒 sidebar badge** | Material's `status:` renderer, already overridden by us | See the badge section below — `gated` is re-pointed at the shield-lock in `uritp.css` → NAV. |

⚠️ **An admonition icon is a MASK, not an image.** It is painted in the current
text colour through `mask-image`, so the SVG's own `fill` is discarded — a
multi-colour glyph will arrive as a flat silhouette. Use a single-path outline
icon, and if it needs to be a specific colour, that colour is a token in
`theme/colors.tsv`, not a fill in the SVG.

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

Menu rows, the password field and the Unlock button all take their minimum
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
- **A folded `???` callout is fully indexed.** Collapsing is a display state;
  the text is in the HTML either way. Folding is never hiding.
- **`Linked from` and the edit link are in the index.** They are rendered
  content. They sit at the bottom, after the last heading, so they only surface
  as a teaser on a search that matched nothing better.

---

## Changing the standards themselves

| File | Holds | Update here when |
|---|---|---|
| [`theme/`](theme/) | **Every colour, font, size, radius and gap** — both modes, and which webfonts download | Any look change at all — see its README |
| `hooks/theme.py` | Composition, the fallback chain, `REQUIRED`, `theme.font` | A token is added, or the injection changes |
| `hooks/pagefoot.py` | The page-foot edit link | Its label, placement, or condition changes |
| `docs/stylesheets/uritp.css` | Every rule on the site | A custom class is added, renamed, or dropped — **and [AUTHORING.md](AUTHORING.md) too**, since authors type `.tbc` by hand |
| `docs/stylesheets/links.css` | The `.deadlink` marker | The marker is restyled or renamed |
| `mkdocs.yml` → `theme.palette` | **Only** the two entries the scheme toggle switches between | Almost never. It is not the design, and **it must not regain a `primary` key.** |
| `mkdocs.yml` → `extra.status` | Sidebar badge tooltips | A `status:` value is added or renamed — **and `docs/using-these-docs.md`** |
| `mkdocs.yml` → `theme.features` | Which Material chrome is on | Anything in *The chrome* table above is restored or removed — **and grep `docs/` for pages that describe it** |
| `requirements.txt` → the 9.x floor | Which Material template ships | Never casually. `partials/nav-item.html` is behaviour we depend on. |

⚠️ **Anything that describes the chrome to READERS lives in `docs/`, and nothing
points at it.** Removing the pencil left `docs/using-these-docs.md` telling guest
designers to click an icon that no longer existed, and the repo's pointer
discipline did not catch it because every pointer runs *code → AUTHORING\*.md*.
`mkdocs.yml` has no idea an orientation page documents its feature flags.
**Turning a chrome feature on or off means grepping `docs/` for it too.**
