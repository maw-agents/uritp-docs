# Authoring reference

How to write pages for this site. **Deliberately outside `docs/`** so it never renders
as a reader-facing page: it documents the machine, not the theatre.

> ⚠️ **This file is CANONICAL.** If a rule here disagrees with the live config, the
> config wins and **this file gets corrected in the same pass**. Every file this
> describes carries a pointer back here, so a standards change and a doc change
> land in one PR or the pointer has failed.

**Describes:** `mkdocs.yml` · `docs/.nav.yml` and per-folder `.nav.yml` ·
`docs/stylesheets/uritp.css` · `docs/stylesheets/links.css` · `hooks/visibility.py` ·
`hooks/links.py` · `hooks/buildstamp.py` · `docs/javascripts/gate.js`

---

## Publication status (read this first)

**Every page needs a `status:` line. A page without one is never built.**

| Status | In the sidebar? | Direct link? | In search? | What is in the served HTML |
|---|---|---|---|---|
| `public` | **Yes** | Works | **Yes** | The real text |
| `gated` | **Yes** | Works, shows a password box | Title only | Ciphertext |
| `unlisted` | No | **Works** | No | The real text |
| `hidden` | No | **404** | No | Nothing. Page is never built. |

### The two questions that separate them

**1. Can someone reach it by typing or pasting the URL?**

- `hidden` → **no.** The file is dropped before the build. The URL 404s. It does not
  exist on the site in any form.
- `unlisted` → **yes.** The page is fully built and fully readable. It is simply not
  linked from anywhere and not in search. Anyone holding the URL reads it instantly.

That is the whole difference. `hidden` is *not published*. `unlisted` is *published
without a signpost*. An unlisted URL forwarded in one email is public from then on.

**2. Do you want people to know the page exists?**

- `gated` → **yes.** It sits in the sidebar where everyone sees it, and asks for a
  password. Use it when the existence of the page is not the secret.
- `unlisted` → **no.** Nobody discovers it; you hand out the link.

### Choosing

| Situation | Use |
|---|---|
| Finished, gatekept, safe to design from | `public` |
| Draft you are circulating to named people for comment | `gated` |
| One-off you want to send to a single person, no password ceremony | `unlisted` |
| Half-written, not for anyone yet | `hidden` |

### A status change only exists once it deploys

Marking a page `gated` does nothing until a build succeeds. On 2026-08-01 a page was
switched to `gated` two minutes after the last passing build, and then served in full
plaintext for the next half hour while six consecutive builds failed on an unrelated
broken link. **Check the footer build stamp after changing a status.** If it is not
your PR or push, your change is not live, whatever the source says.

---

## The gate

```markdown
---
title: Paperwork standards
status: gated
password: theatre2026
---
```

The page renders, then the build **encrypts the finished HTML** (PBKDF2-SHA256, 250k
iterations, AES-256-GCM) and replaces the body with an unlock form plus the
ciphertext. The browser decrypts with Web Crypto when the password is entered.

- A wrong password **fails to decrypt**. It is not a JavaScript comparison you can
  step around in devtools; there is no plaintext in the page to find.
- Unlocking is remembered for the **browser session only**. Closing the tab re-locks,
  because shared shop and lab machines are the normal case here.
- The right-hand outline is suppressed on gated pages, or it would list the section
  headings of a locked page.
- Gated pages **never print**. The lock box is hidden, so nobody prints an empty page.

### Keeping the password out of the repo

`password:` in frontmatter is convenient and **publishes the password**. The better
form names a gate and reads the secret from the build environment:

```markdown
status: gated
gate: designers      # reads URITP_GATE_DESIGNERS from a GitHub Actions secret
```

Same gate, secret never committed. Use this the moment a password protects anything
that actually matters.

---

## ⚠️ What the gate actually does (and does not)

**While this repository is public, none of the four states are access control.**

The site is only one copy of the content. The other copy is the markdown in the repo,
and that copy is world-readable at `github.com/maw-agents/uritp-docs`:

| | On the site | In the public repo |
|---|---|---|
| A `hidden` page | Not there at all | **Fully readable** |
| A `gated` page | Encrypted | **Fully readable, password included** |
| An `unlisted` page | Readable by URL | **Fully readable** |

And git never forgets: deleting a page tomorrow leaves it in the commit history
forever.

So be honest about what each one buys you **today**:

- **`hidden`** stops a half-written page reaching a student by accident. That is a
  real and worthwhile job and it does it perfectly.
- **`gated`** signals "this is not for casual circulation" and stops a forwarded link
  from being instantly readable. Deterrence and framing, not security.
- **Nothing here protects anything from someone who thinks to look at the repo.**

Never put student data, personal contact details, credentials, medical or disciplinary
information, or contract terms in a page and rely on `hidden` or `gated` to hold it.
If it must not be read, it does not belong in this repo.

### Making the gate real

The gate becomes genuine protection the moment the markdown stops being public. That
needs two changes:

1. **Make the repo private.** GitHub Pages from a private repository requires **GitHub
   Pro** (about $4/month). On the Free plan the repo must be public, full stop.
2. **Move passwords to Actions secrets** using the `gate:` form above.

With both done, the site stays public, the source is not, the served page holds only
ciphertext, and the password lives in a secret store. That is a real lock.

A fully private *site* (readers must be logged-in GitHub users with repo access) is
Enterprise Cloud only, and would be wrong here anyway: guest designers and students
do not have GitHub accounts.

### Linking to a hidden page

~~A hidden page is not built, so a link pointing at it cannot resolve, and `--strict`
kills the deploy.~~ **Changed 2026-08-01.** That rule made one unpublished target
capable of freezing the entire site. A link to a hidden or missing page now renders as
a visible dead-link marker on that page only, is listed in the link report, and the
build continues. You still cannot publish a working dead end; you can no longer take
the whole site down with one.

---

## Adding a page

**Drop a `.md` file in the right folder under `docs/`. That is the entire procedure.**

The sidebar is generated from the file tree, so a `public` or `gated` page appears in
its section automatically, sorted alphabetically by filename. Nothing to register.

```markdown
---
title: Rehearsal Studio
id: rehearsal-studio
status: hidden
---

# Rehearsal Studio

One line on what this space is and who uses it.

!!! note "Not yet documented"
    This page is a placeholder.
```

### Adding a folder

A new folder becomes a new sidebar section and lands at the bottom. Two optional files
shape it, and **neither is needed to make the pages appear**:

| To do this | Add |
|---|---|
| Place the section somewhere specific | its folder name in `docs/.nav.yml` |
| Set the section's displayed title | a `.nav.yml` **inside the folder**, holding `title: Todd Union` |
| Give the section a landing page | an `index.md` in the folder |

Without a folder `.nav.yml` the sidebar title-cases the folder name, which produces
`Spac` for an acronym and `Todd union` with a lowercase U. That is the only reason to
add one.

A folder's `index.md` becomes the page you land on when you click the section name
(`navigation.indexes`), instead of the name doing nothing. Give it an `id:` like any
other page.

---

## Page anatomy

Every page opens the same way: frontmatter, one H1, one lede paragraph.

```markdown
---
title: Smith Theatre
id: smith-theatre
status: public
---

# Smith Theatre

Primary performance space in the Sloan Performing Arts Center.

## Technical specifications
```

**One H1 per page**, always the page title. Two H1s break the right-hand outline.
Sections are `##`. Sub-points are `###`. Do not go deeper: if you need a fourth
level, the page wants splitting.

The theme styles the **first paragraph after the H1** as large light lede text
automatically. Do not try to make it big yourself.

---

## Links

**A link points at a page's `id`, never at its file path.**

```markdown
[Smith Theatre](@smith-theatre)
[the venue notes](@smith-theatre#venue-notes)
[Technical drawings](https://rochester.box.com/s/x5582ig...)
```

That is the whole syntax. There is no relative path to count, no `../`, and nothing
about the link changes when the target moves. `@smith-theatre` resolves at build time
to wherever that page currently lives.

### Why, in one paragraph

On 2026-08-01 Smith Theatre moved from `docs/venues/` into `docs/venues/SPAC/`. That
single rename broke **eight links across six files**, in both directions: every page
linking *to* Smith, plus Smith's own links *out*. Because the build runs `--strict`,
the deploy died and the live site silently froze on an older commit for over half an
hour. Two rounds of hand-patching the paths still missed three of them. Paths encode
where a page happens to sit today, which is the one fact about a page most likely to
change.

### Declaring an id

Add `id:` to frontmatter. **Set it once and never change it** — that promise is the
entire mechanism.

```markdown
---
title: Smith Theatre
id: smith-theatre
status: public
---
```

No `id:` is fine for a page nothing links to yet: the filename stands in, and a
folder's `index.md` takes the folder's name. Declare one properly the moment anything
links to the page.

### Linking to a heading

Give the heading an explicit anchor and link to that:

```markdown
## Venue notes {#venue-notes}

[the venue notes](@smith-theatre#venue-notes)
```

Without `{#...}` the anchor is generated from the heading **text**, so retitling
"Venue notes" to "Notes by department" breaks every link into it, silently. The build
reports any deep link riding on heading text as `fragile-anchor`. Fix those by adding
the explicit id, not by editing the links.

### When a page moves anyway

Ids keep *internal* links working. They cannot fix a bookmark, an email, a syllabus, or
a QR code on a callboard. Record the retired address:

```markdown
aliases:
  - venues/smith-theatre     # lived here until 2026-08-01
```

The build writes a redirect at the old URL. An alias that collides with a real page is
skipped and reported rather than overwriting it.

### What a broken link looks like now

It does **not** fail the build. The link text renders in red with a dashed underline
and a ⚠, on that page only, and the reason appears in the build's link report. One
typo can no longer freeze a site people are trying to load a show from.

Every build writes:

- a **Link report** table in the Actions run summary, and
- `/link-report.json` on the live site, listing every issue with its page and reason.

| Report kind | Means |
|---|---|
| `dead-link` | Nothing carries that id, or the target is `hidden`. Rendered as a marker. Includes a did-you-mean. |
| `legacy-path` | An old `path.md` link. Still resolved, but rewrite it as `@id`. |
| `fragile-anchor` | Deep link riding on heading text. Add `{#anchor}` to the heading. |
| `missing-anchor` | The anchor does not exist; the link lands at the top of the page. |
| `duplicate-id` | Two pages claim one id. The second is unreachable by id. |
| `alias-collision` | A retired URL is already a real page. Redirect skipped. |

**Never use a full `https://` URL for an internal page.** It works, which is the
problem: it dodges every check above and rots silently.

---

## Callouts

Three exclamation marks, the type, a quoted title. **The body must be indented four
spaces.** That indent is the whole trick and it is the thing people get wrong.

```markdown
!!! warning "Before you design"
    Smith is a blackbox with real constraints that will bite
    a design late if you learn them late.

!!! note "Not yet documented"
    This page is a placeholder.
```

| Type | Use for | Reads as |
|---|---|---|
| `warning` | Anything that costs money or hurts someone | Amber |
| `note` | Context, gaps, placeholders | Purple |
| `danger` | A genuine safety stop | Red |

That is the whole vocabulary. **Resist inventing more.** Four callout colors on one
page means none of them read as urgent.

⚠️ **The GitHub web editor sometimes collapses that four-space indent to one** when you
edit a line next to it. The body then falls silently out of the box. If a callout looks
wrong after a phone edit, check the indent first.

---

## Department tabs

How venue notes split by department. `===` then a quoted label, **body indented four
spaces**, blank line between tabs.

```markdown
=== "Lighting"

    All catwalk fixtures are yoked at **45 degrees**.

=== "Audio"

    The two repertory Fulcrums under catwalk 3 cannot move north or south.
```

Readers see one department at a time. **When the page is printed, all tabs stack** so
nothing is lost on paper.

**Keep labels identical across pages:** General staging · Scenic · Lighting · Audio ·
Directors. A reader who picks Lighting on one venue page gets Lighting selected on the
next one, but only if the label matches character for character.

---

## Tables and the unconfirmed marker

Columns do not need to line up in the source. The renderer does not care.

```markdown
| Item | Value |
|---|---|
| Configuration | Blackbox, flexible seating |
| Grid height | [To be confirmed]{.tbc} |
```

**`[To be confirmed]{.tbc}`** renders as an amber pill. Use it instead of guessing,
and instead of leaving the row out. A missing row reads as "there is nothing to know
here." An unconfirmed row reads as "measure this before you draft it," which is true.

---

## Text

Standard markdown, nothing exotic. **Blank line between every block** (paragraphs,
lists, headings, tables). That one rule prevents most formatting surprises.

```markdown
**Bold** for the thing that matters.
*Italic* for emphasis, sparingly.
`Code` for filenames and exact values.

- Bulleted item
- Another item

1. Numbered step
2. Next step
```

---

## The footer build stamp

Every page's footer carries the PR (or short SHA) the live site was built from:

```
University of Rochester International Theatre Program · PR #19
```

**This is the only signal that a build failed.** When one does, GitHub Pages keeps
serving the previous commit: no banner, no error page, the site simply stops changing.
A footer showing a PR older than your edit means your change is not live and the
Actions log is where to look.

The **deploy time** is still there, in the stamp's `title` attribute: hover it on a
desktop, or read the page source. ~~It used to sit on the face of the footer~~ and was
moved on 2026-08-01 at Michael's instruction. The reasoning it replaced was real — both
of that night's frozen-deploy diagnoses came off the clock, not the number — but a
clock in front of every reader of every page is furniture for everyone except the two
or three people debugging a deploy.

⚠️ **A PR number only reads as stale if you know the current one.** When a build looks
suspicious, check the [Actions runs](https://github.com/maw-agents/uritp-docs/actions)
rather than squinting at the footer.

---

## What breaks the build

The site builds with `--strict`. The list of things that can take the whole deploy down
is deliberately short, and **links are no longer on it**.

| # | Failure | Fails the deploy? | Why |
|---|---|---|---|
| 1 | Callout or tab body not indented four spaces | No, renders wrong | Content falls out of the box. Four spaces, not a tab, not two. |
| 2 | Link to a missing, moved, or `hidden` page | **No, as of 2026-08-01** | Renders as a dead-link marker and appears in the link report. |
| 3 | `status: gated` with no password | **Yes** | The build refuses rather than shipping the page wide open. |
| 4 | No blank line before a table or list | No | Renders as one mashed paragraph, which makes it easier to miss. |
| 5 | Two H1s on a page | No, renders wrong | Breaks the outline and the page title. |
| 6 | Missing or misspelled `status:` | No | The page silently will not build. Nothing errors: it just is not there. |

**When a build does fail, the live site keeps serving the previous commit.** There is
no banner and no error page: it simply stops updating. The footer build stamp is the
only signal, which is why it exists. Check it before concluding a change did not work.

---

## The loop

No git, no terminal, nothing installed. Works from a phone.

1. Open the page on the live site, click the **pencil icon** in the header.
2. Edit the markdown. Commit.
3. Wait about ninety seconds. Actions rebuilds and the page updates.
4. **Check the footer stamp.** If it is not your edit, the build failed.

---

## Changing the standards themselves

If you change any file this document describes, **update this file in the same PR**.
Each carries a pointer comment at the top saying so.

| File | Holds | Update here when |
|---|---|---|
| `mkdocs.yml` | Theme, features, markdown extensions, hook order | An extension, plugin, or hook is added or removed |
| `docs/.nav.yml` | Top-level sidebar order | The add-a-page procedure changes |
| `docs/<folder>/.nav.yml` | That section's displayed title | The per-folder title mechanism changes |
| `docs/stylesheets/uritp.css` | Palette, headings, `.tbc`, `.gate`, print rules | A custom class is added, renamed, or dropped |
| `docs/stylesheets/links.css` | The `.deadlink` marker | The marker is restyled or renamed |
| `hooks/visibility.py` | The `status:` gate and the encryption | A status value is added or renamed, or its behaviour changes |
| `hooks/links.py` | `@id` resolution, aliases, the link report | The link syntax, a report kind, or the fail-vs-report stance changes |
| `hooks/buildstamp.py` | The footer stamp | What the stamp shows changes |
| `docs/javascripts/gate.js` | Browser-side unlock | The crypto parameters or the unlock flow change |

A syntax rule described here that no longer has an extension behind it is worse than
no documentation: it teaches something that silently renders as literal text. A status
value described here that the hook does not recognise is worse still: the page falls
back to `hidden` and quietly disappears.

**The two halves of the gate must change together.** `hooks/visibility.py` and
`docs/javascripts/gate.js` share the cipher, the KDF, and the iteration count. Change
one without the other and every gated page fails to unlock with no error anyone can
read.

**Hook order in `mkdocs.yml` is load-bearing.** `visibility.py` drops `hidden` pages
before `links.py` builds its id registry. Swap them and a link to a hidden page would
resolve to a URL that 404s instead of being caught.
