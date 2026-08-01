# Authoring reference

How to write pages for this site. **Deliberately outside `docs/`** so it never renders
as a reader-facing page: it documents the machine, not the theatre.

> ⚠️ **This file is CANONICAL.** If a rule here disagrees with the live config, the
> config wins and **this file gets corrected in the same pass**. Every file this
> describes carries a pointer back here, so a standards change and a doc change
> land in one PR or the pointer has failed.

**Describes:** `mkdocs.yml` · `docs/.nav.yml` · `docs/stylesheets/uritp.css` ·
`hooks/visibility.py` · `docs/javascripts/gate.js`

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

### Linking to a hidden page fails the build

A hidden page is not built, so a link pointing at it cannot resolve, and `--strict`
kills the deploy. Deliberate: you cannot publish a dead end. Promote the target to
`unlisted` or remove the link.

---

## Adding a page

**Drop a `.md` file in the right folder under `docs/`. That is the entire procedure.**

The sidebar is generated from the file tree, so a `public` or `gated` page appears in
its section automatically, sorted alphabetically by filename. Nothing to register.

```markdown
---
title: Rehearsal Studio
status: hidden
---

# Rehearsal Studio

One line on what this space is and who uses it.

!!! note "Not yet documented"
    This page is a placeholder.
```

A new **folder** becomes a new sidebar section and lands at the bottom. To place it
somewhere specific, add its name to `docs/.nav.yml`. That is the only reason to open
that file.

---

## Page anatomy

Every page opens the same way: frontmatter, one H1, one lede paragraph.

```markdown
---
title: Smith Theatre
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

## Links

Internal links point at the **`.md` file**, not the live URL. The build rewrites them
and fails loudly if the target does not exist or is `hidden`.

```markdown
Same folder:       [SPAC Lobby](spac-lobby.md)
Different folder:  [Safety](../safety/index.md)
To a heading:      [see the notes](smith-theatre.md#venue-notes)
External:          [Technical drawings](https://rochester.box.com/s/x5582ig...)
```

Heading anchors are the heading text, lowercased, spaces to hyphens.
`## Venue notes` becomes `#venue-notes`.

**Never use a full `https://` URL for an internal page.** It works, which is the
problem: it dodges the broken-link check and rots silently.

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

## What breaks the build

The site builds with `--strict`, so these **fail the deploy** instead of quietly
shipping something broken. A red X in Actions is the system working; the log names
the file.

| # | Failure | Why |
|---|---|---|
| 1 | Callout or tab body not indented four spaces | Content falls out of the box. Four spaces, not a tab, not two. |
| 2 | Link pointing at a missing or `hidden` page | Typo, or you linked something not published yet. |
| 3 | `status: gated` with no password | The build refuses rather than shipping the page wide open. |
| 4 | No blank line before a table or list | Renders as one mashed paragraph. **Does not fail the build**, which makes it worse. |
| 5 | Two H1s on a page | Breaks the outline and the page title. |
| 6 | Missing or misspelled `status:` | The page silently will not build. Nothing errors: it just is not there. |

---

## The loop

No git, no terminal, nothing installed. Works from a phone.

1. Open the page on the live site, click the **pencil icon** in the header.
2. Edit the markdown. Commit.
3. Wait about ninety seconds. Actions rebuilds and the page updates.

---

## Changing the standards themselves

If you change any file this document describes, **update this file in the same PR**.
Each carries a pointer comment at the top saying so.

| File | Holds | Update here when |
|---|---|---|
| `mkdocs.yml` | Theme, features, markdown extensions | An extension is added or removed (changes what syntax works) |
| `docs/.nav.yml` | Sidebar order and section titles | The add-a-page procedure changes |
| `docs/stylesheets/uritp.css` | Palette, headings, `.tbc`, `.gate`, print rules | A custom class is added, renamed, or dropped |
| `hooks/visibility.py` | The `status:` gate and the encryption | A status value is added or renamed, or its behaviour changes |
| `docs/javascripts/gate.js` | Browser-side unlock | The crypto parameters or the unlock flow change |

A syntax rule described here that no longer has an extension behind it is worse than
no documentation: it teaches something that silently renders as literal text. A status
value described here that the hook does not recognise is worse still: the page falls
back to `hidden` and quietly disappears.

**The two halves of the gate must change together.** `hooks/visibility.py` and
`docs/javascripts/gate.js` share the cipher, the KDF, and the iteration count. Change
one without the other and every gated page fails to unlock with no error anyone can
read.
