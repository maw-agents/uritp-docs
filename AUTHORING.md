# Authoring reference

How to write pages for this site. **Deliberately outside `docs/`** so it never renders
as a reader-facing page: it documents the machine, not the theatre.

> ⚠️ **This file is CANONICAL.** If a rule here disagrees with the live config, the
> config wins and **this file gets corrected in the same pass**. Every file this
> describes carries a pointer back here, so a standards change and a doc change
> land in one PR or the pointer has failed.

**Describes:** `mkdocs.yml` · `docs/.nav.yml` · `docs/stylesheets/uritp.css` ·
`hooks/visibility.py`

---

## Publication status (read this first)

**Every page needs a `status:` line. A page without one is never built.**

| Status | Sidebar | Direct link | Search | Use for |
|---|---|---|---|---|
| `public` | Listed | Works | Indexed | Finished, gatekept, ready to be relied on |
| `unlisted` | Not listed | Works | Not indexed | A draft you want to hand to one person |
| `hidden` | Not listed | 404 | No | Not ready. **This is the default.** |

```markdown
---
title: Rehearsal Studio
status: hidden
---
```

Default-hidden means a half-written page cannot reach a student by accident. You
promote it deliberately: `hidden` while you draft, `unlisted` when you want a
specific person to review it, `public` when you stand behind it.

### ⚠️ What `hidden` does NOT mean

**`hidden` means "not published to the site." It does not mean secret.**

This repository is public. The markdown for a hidden page is readable by anyone at
`github.com/maw-agents/uritp-docs`, and it stays in the commit history forever even
after you delete it. `unlisted` is weaker still: it is a live public URL that simply
is not linked, and a URL shared once is a URL that exists.

So:

- **Not ready yet** → `hidden` is exactly the right tool.
- **Must not be read by outsiders** → it does not belong in this repo at all. Real
  read control means a private repo plus Cloudflare Access in front of the site, or
  keeping the document somewhere else entirely.

Never put student data, personal contact details, credentials, or anything
contractual in a page and rely on `hidden` to protect it.

### Linking to a hidden page fails the build

A hidden page is not built, so a link pointing at it cannot resolve, and `--strict`
kills the deploy. This is deliberate: you cannot publish a dead end. Either promote
the target to `unlisted` or remove the link.

---

## Adding a page

**Drop a `.md` file in the right folder under `docs/`. That is the entire procedure.**

The sidebar is generated from the file tree, so a `public` page appears in its
section automatically, sorted alphabetically by filename. Nothing to register.

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
| 3 | No blank line before a table or list | Renders as one mashed paragraph. **Does not fail the build**, which makes it worse. |
| 4 | Two H1s on a page | Breaks the outline and the page title. |
| 5 | Missing or misspelled `status:` | The page silently will not build. Nothing errors: it just is not there. |

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
| `docs/stylesheets/uritp.css` | Palette, headings, `.tbc`, print rules | A custom class is added, renamed, or dropped |
| `hooks/visibility.py` | The `status:` gate | A status value is added, renamed, or its behaviour changes |

A syntax rule described here that no longer has an extension behind it is worse than
no documentation: it teaches something that silently renders as literal text. A status
value described here that the hook does not recognise is worse still: the page falls
back to `hidden` and quietly disappears.
