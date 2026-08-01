# Authoring reference

How to write pages for this site. **Deliberately outside `docs/`** so it never renders
as a reader-facing page: it documents the machine, not the theatre.

> ⚠️ **This file is CANONICAL.** If a rule here disagrees with the live config, the
> config wins and **this file gets corrected in the same pass**. Every file this
> describes carries a pointer back here, so a standards change and a doc change
> land in one PR or the pointer has failed.

**Describes:** `mkdocs.yml` · `requirements.txt` · `.github/workflows/deploy.yml` ·
`docs/.nav.yml` and per-folder `.nav.yml` · `docs/stylesheets/uritp.css` ·
`docs/stylesheets/links.css` · `hooks/visibility.py` · `hooks/links.py` ·
`hooks/buildstamp.py` · `docs/javascripts/gate.js`

---

## Publication status (read this first)

**Every page needs a `status:` line, or it inherits one, or it is hidden.**

| Status | In the sidebar? | Direct link? | In search? | What is in the served HTML |
|---|---|---|---|---|
| `public` | **Yes** | Works | **Yes** | The real text |
| `gated` | **Yes** | Works, shows a password box | Title only | Ciphertext |
| `unlisted` | No | **Works** | No | The real text |
| `hidden` | No | **404** | No | Nothing. Page is never built. |

Plus one independent switch that composes with any of them:

```markdown
listed: false      # keep this page out of the nav, search and sitemap
```

### The two questions that separate them

**1. Can someone reach it by typing or pasting the URL?**

- `hidden` → **no.** The file is dropped before the build. The URL 404s.
- `unlisted` → **yes.** Fully built and fully readable, just not linked and not in
  search. Anyone holding the URL reads it instantly.

`hidden` is *not published*. `unlisted` is *published without a signpost*. An unlisted
URL forwarded in one email is public from then on.

**2. Do you want people to know the page exists?**

- `gated` → **yes.** It sits in the sidebar where everyone sees it and asks for a
  password. Use it when the existence of the page is not the secret.
- `unlisted` → **no.** Nobody discovers it; you hand out the link.

### Gated AND unlisted, together

```markdown
status: gated
listed: false
gates: [psm]
```

Encrypted **and** undiscoverable: no sidebar entry, no search result, no sitemap, and
the body is ciphertext even for someone holding the URL. `status: unlisted` is now
just shorthand for *public + `listed: false`*, kept because it reads better.

### Choosing

| Situation | Use |
|---|---|
| Finished, gatekept, safe to design from | `public` |
| Draft you are circulating to named people for comment | `gated` |
| One-off for a single person, no password ceremony | `unlisted` |
| Locked *and* not advertised | `gated` + `listed: false` |
| Half-written, not for anyone yet | `hidden` |

### A status change only exists once it deploys

Marking a page `gated` does nothing until a build succeeds. On 2026-08-01 a page was
switched to `gated` two minutes after the last passing build, then served in full
plaintext for the next half hour while six consecutive builds failed on an unrelated
broken link. **Check the footer build stamp after changing a status.**

### ⚠️ And a green build is still not proof: check with a cache-buster

Even after a passing deploy, **the old page can keep being served from cache** — the
Pages CDN, a phone browser, or anything between. On 2026-08-01 `docs/safety/index.md`
was reported as "gated but serving plaintext" across what looked like two green
builds. **The gate had been working the whole time.** Every check had read a cache.

1. Load the page with a junk query string: `…/safety/?x=1`. A query the CDN has never
   seen forces a fresh fetch. **The single most useful trick on this page.**
2. Cross-check `/search/search_index.json`. Regenerated every build, rarely cached in
   step with the HTML. A gated page appears there as *"Restricted page … Unlock"*.

**A check that returns the same answer whether or not you are right has verified
nothing.** A plain reload is exactly that check.

---

## The gate

```markdown
---
title: Todd Lock-up
id: todd-lockup-procedure
status: gated
gates: [psm, admin]
---
```

The page renders, then the build **encrypts the finished HTML** (PBKDF2-SHA256, 250k
iterations, AES-256-GCM) and replaces the body with an unlock form plus ciphertext.
The browser decrypts with Web Crypto when a password is entered.

- A wrong password **fails to decrypt**. Not a JavaScript comparison you can step
  around in devtools; there is no plaintext in the page to find.
- The right-hand outline is suppressed, or it would list the headings of a locked page.
- Gated pages **never print**. The lock box is hidden, so nobody prints an empty page.
- A gated page's visible H1 comes from `title:`, not the `# Heading` in the body — the
  gate replaces the body, so no H1 survives and Material substitutes the title.

### Key groups

**`gates:` is a list, and ANY ONE of the named groups' passwords opens the page.**

```markdown
gates: [psm]                 # one group
gates: [psm, admin]          # either password works
gate: psm                    # singular, still valid, same as [psm]
```

Each name reads `URITP_GATE_<NAME>` from the build environment, uppercased with
hyphens turned into underscores (`front-of-house` → `URITP_GATE_FRONT_OF_HOUSE`).

| Group | Secret | Roughly |
|---|---|---|
| `admin` | `URITP_GATE_ADMIN` | Program leadership |
| `dev` | `URITP_GATE_DEV` | Whoever is building this site |
| `psm` | `URITP_GATE_PSM` | Production stage management |

**How it works, because the shape matters if you ever debug it.** The body is
encrypted **once** with a random content key. That content key is then encrypted
separately for each group. A wrapped key is ~100 bytes, so:

- Page weight barely moves as you add groups. It is not N copies of the page.
- Rotating one group's key rewraps ~100 bytes. Body and other groups untouched.
- Revoking a group from a page is deleting one word from `gates:`.

The wrapped keys ship shuffled and unlabelled. **Which desk can open a document is
itself information**, and an ordered, named list would hand it to anyone reading the
built HTML.

### Unlock once per session, not once per page

A password that opens anything is remembered for the browser session, and every gated
page afterwards tries the whole **keyring** before showing its form. Unlock the Safety
index with the PSM key and every other PSM page opens by itself.

- **Closing the tab re-locks everything.** sessionStorage, not localStorage, because a
  shared machine in a shop or a lab is the normal case here.
- The browser never learns which *group* a key belongs to. It re-runs the same trial
  decryption it would have run anyway, so **access is proven by decryption every time**
  — never by a remembered "I am PSM" flag somebody could set in devtools.
- The lock box is hidden while the keyring runs, so a page you can already open does
  not flash a password prompt at you.
- Ceiling: 8 remembered keys. Each candidate costs a PBKDF2 derivation (~100-200ms on
  a phone) per wrap until one succeeds, so a handful is imperceptible and dozens would
  not be.

### A gated folder index locks its whole subtree

**Gating a folder's `index.md` gates every page inside it, at any depth.**

```
docs/safety/index.md          status: gated, gates: [psm]
docs/safety/lockup.md         -> inherits: gated, gates: [psm]
docs/safety/keys/master.md    -> inherits too
```

The children are **genuinely encrypted**, not merely hidden from the sidebar. That
distinction is the whole design: hiding child entries until the index unlocks leaves
every child fully readable by direct URL and in search *while looking protected*. On a
safety section that is the worst of both — the appearance of a lock with none of it.

Because inheritance is real, the sidebar keeps showing the children honestly. A reader
sees the section exists and is asked for a password, which is what `gated` is for. And
with the keyring, unlocking the index opens the rest of the folder as you walk it.

**Overriding.** The nearest gated ancestor wins. A page opts out by declaring its own
`status:` — *any* value, including `public` — or with `inherit: false`. A page that
said something about itself is never silently overridden; only silence inherits.

~~⚠️ **Gating a folder's `index.md` does NOT gate the pages inside it.** Each page
carries its own `status:`, and a locked section landing page sits above a sidebar full
of unlocked children.~~ **Reversed 2026-08-01, hours after it was written.** That was
true of the build at the time and is exactly the trap described above, so the
behaviour changed rather than the warning being restated.

### Keeping the password out of the repo

`password: theatre2026` in frontmatter still works and is fine for a throwaway draft.
It also **publishes the password**, since the markdown is world-readable. `gates:` is
the form to use for anything you would repeat out loud in a meeting.

---

## Adding a key group

Three steps. Two of them are one line each.

**1. Add the secret.** GitHub → **Settings → Secrets and variables → Actions → New
repository secret**. Name it `URITP_GATE_` plus the group in capitals, so group `psm`
is the secret `URITP_GATE_PSM`. Paste the password as the value.

GitHub will never show you that value again. **Write it down wherever you keep
passwords before you click Add.**

**2. Pass it through to the build.** Secrets are *not* automatically visible to a
workflow. In `.github/workflows/deploy.yml`, find the `env:` block under *Build site*:

```yaml
          URITP_GATE_PSM: ${{ secrets.URITP_GATE_PSM }}
```

⚠️ **This is the step everybody forgets.** A secret that exists but is not listed here
is invisible to the build, and the symptom is identical to never having created it.

**3. Use it.**

```markdown
status: gated
gates: [psm]
```

Push. About ninety seconds later the page asks for that password.

### Secrets or variables?

Both work. `${{ vars.URITP_GATE_PSM }}` reaches the build identically and the hook
cannot tell the difference — it reads an environment variable either way. The
temptation is real, because **a variable can be read back later and a secret cannot**.

**Use secrets anyway.** One difference decides it: **Actions logs on a public
repository are world-readable, and secrets are masked in them while variables are
not.** Nothing in this workflow echoes the environment today, but a future debugging
step, a crashing hook printing its context, or an action that dumps `env` on failure
would put a variable's value in a public log permanently. A secret shows as `***`.

The readability problem is real and has a better answer than downgrading: **keep the
password list somewhere you can actually read it** — the ClickUp Accounts list is
already the house home for credentials. GitHub holds the copy the build uses; you hold
the copy you can look up. Reaching for variables solves a filing problem by removing a
safety net.

⚠️ Masking is a literal string match, not magic. A password that gets transformed
before printing (base64, URL-encoded, split) will not be masked even as a secret.

### Rotating a password

Update the secret's value in Settings, then push anything (or re-run the workflow from
the Actions tab). Every page carrying that group rewraps on the next build. **No page
needs editing** and no other group is affected. Anyone mid-session keeps their access
until they close the tab; the keyring holds the old password and it stops working on
the next page load after the rebuild.

### If the build fails with "the environment carries no URITP_GATE_…"

That error is deliberate: a gated page named a group whose secret the build cannot
see, and refusing to deploy beats publishing a page everyone believes is locked.

1. Does the secret exist in **Settings → Secrets and variables → Actions**?
2. Is it listed in the `env:` block of `deploy.yml`? (Step 2 above.)
3. Do the two names match **exactly**? An unset secret interpolates to an empty string
   rather than erroring, so a typo in the workflow looks exactly like a missing secret.

---

## ⚠️ What the gate actually does (and does not)

**While this repository is public, none of this is access control.**

Secrets fix the **password** leak. They do nothing about the **content** leak. The
site is one copy of the content; the other is the markdown, world-readable at
`github.com/maw-agents/uritp-docs`:

| | On the site | In the public repo |
|---|---|---|
| A `hidden` page | Not there at all | **Fully readable** |
| A `gated` page | Encrypted | **Fully readable** |
| An `unlisted` page | Readable by URL | **Fully readable** |

And git never forgets: deleting a page tomorrow leaves it in history forever.

- **`hidden`** stops a half-written page reaching a student by accident. Real job,
  done perfectly.
- **`gated`** signals "this is not for casual circulation" and stops a forwarded link
  being instantly readable. **Deterrence and framing, which is the job it was chosen
  for** (Michael, 2026-08-01: *"don't circulate this is enough"*).
- **Nothing here protects anything from someone who thinks to look at the repo.**

Never put student data, personal contact details, credentials, medical or disciplinary
information, or contract terms in a page and rely on `hidden` or `gated` to hold it.
If it must not be read, it does not belong in this repo.

### If that ever needs to change

The gate becomes genuine protection the moment the markdown stops being public: **make
the repo private** (Pages from a private repo needs GitHub Pro, ~$4/month). The
`gates:` plumbing is already in place, so that is the only remaining step. Until then
the group keys are organisational, not protective, and that is a deliberate choice.

### Linking to a hidden page

~~A hidden page is not built, so a link pointing at it cannot resolve, and `--strict`
kills the deploy.~~ **Changed 2026-08-01.** That rule let one unpublished target
freeze the entire site. A link to a hidden or missing page now renders as a visible
dead-link marker on that page only, is listed in the link report, and the build
continues.

---

## Adding a page

**Drop a `.md` file in the right folder under `docs/`. That is the entire procedure.**

The sidebar is generated from the file tree, so a `public` or `gated` page appears in
its section automatically, sorted alphabetically by filename.

```markdown
---
title: Rehearsal Studio
id: rehearsal-studio
status: hidden
---

# Rehearsal Studio

One line on what this space is and who uses it.
```

### Adding a folder

A new folder becomes a new sidebar section and lands at the bottom. Two optional files
shape it, and **neither is needed to make the pages appear**:

| To do this | Add |
|---|---|
| Place the section somewhere specific | its folder name in `docs/.nav.yml` |
| Set the section's displayed title | a `.nav.yml` **inside the folder**, holding `title: Todd Union` |
| Give the section a landing page | an `index.md` in the folder |

Without a folder `.nav.yml` the sidebar title-cases the folder name, producing `Spac`
for an acronym and `Todd union` with a lowercase U. That is the only reason to add one.

A folder's `index.md` becomes the page you land on when you click the section name
(`navigation.indexes`). Give it an `id:` like any other page — **and note that gating
it locks the whole folder** (see *A gated folder index locks its whole subtree*).

---

## Page anatomy

Frontmatter, one H1, one lede paragraph.

```markdown
---
title: Smith Theatre
id: smith-theatre
status: public
---

# Smith Theatre

Primary performance space in the Sloan Performing Arts Center.
```

**One H1 per page**, always the page title. Two H1s break the right-hand outline.
Sections are `##`. Sub-points are `###`. Deeper than that means the page wants
splitting. The theme styles the **first paragraph after the H1** as lede text
automatically; do not try to make it big yourself.

### Which title shows where

Three surfaces read three different sources, which is why two pages can look
inconsistent without either being wrong:

| Surface | Reads |
|---|---|
| Sidebar entry, browser tab | frontmatter `title:` |
| The big heading on the page | the `# H1` in the body |
| Search result heading | the H1, falling back to `title:` |

So `title: safety test page` with `# Safety test page` gives a lowercase sidebar entry
and a capitalised page heading. **Keep them the same unless you mean it.** The
exception is a **gated** page, which has no H1 to show (see *The gate*).

---

## Links

**A link points at a page's `id`, never at its file path.**

```markdown
[Smith Theatre](@smith-theatre)
[the venue notes](@smith-theatre#venue-notes)
```

No relative path to count, no `../`, and nothing about the link changes when the
target moves. `@smith-theatre` resolves at build time to wherever that page lives.

### Why, in one paragraph

On 2026-08-01 Smith Theatre moved from `docs/venues/` into `docs/venues/SPAC/`. That
single rename broke **eight links across six files**, in both directions. Because the
build runs `--strict`, the deploy died and the live site silently froze on an older
commit for over half an hour. Two rounds of hand-patching still missed three. Paths
encode where a page sits today, the one fact most likely to change.

### Declaring an id

Add `id:` to frontmatter. **Set it once and never change it** — that promise is the
entire mechanism. No `id:` is fine for a page nothing links to yet: the filename
stands in, and a folder's `index.md` takes the folder's name.

**House style: lowercase kebab-case**, matching the filename (`todd-lockup-procedure`,
not `Todd-Lock-up`). Capitals resolve fine, so this is convention rather than rule,
but an id is typed by hand in every link pointing at it and a mixed-case one gets
mistyped.

### Linking to a heading

```markdown
## Venue notes {#venue-notes}

[the venue notes](@smith-theatre#venue-notes)
```

Without `{#...}` the anchor is generated from the heading **text**, so retitling breaks
every link into it, silently. The build reports those as `fragile-anchor`. Fix by
adding the explicit id, not by editing the links.

### When a page moves anyway

Ids keep *internal* links working. They cannot fix a bookmark, an email, a syllabus or
a QR code on a callboard. Record the retired address:

```markdown
aliases:
  - venues/smith-theatre     # lived here until 2026-08-01
```

The build writes a redirect at the old URL. An alias colliding with a real page is
skipped and reported rather than overwriting it.

---

## Backlinks — "Linked from"

**Every page automatically grows a `Linked from` section listing the pages that point
at it. You never write one and you cannot get one wrong.**

Because `hooks/links.py` resolves every internal link, it knows every link in reverse.
Link Safety → Smith Theatre once, and Smith Theatre gains a link back on its own.

- **Built from the source files, not render order**, so a link added on a page built
  later still registers.
- **Undiscoverable pages are never named as a source.** If a page is `unlisted` or
  carries `listed: false`, listing it on a public page is exactly the discovery it is
  avoiding. The one rule here you should not "fix".
- **Self-links are dropped.** The heading carries a stable `{#linked-from}` anchor.
- A page nothing links to has no section, and appears as an `orphan` in the link
  report. **Not an error** — a section landing page is reached from the sidebar.
- Kill switch: `URITP_BACKLINKS=0` in the build environment.

### Instant previews (desktop)

Hovering an internal link shows a card previewing the target. Enabled in `mkdocs.yml`
via `material.extensions.preview`, free as of Material 9.7 — which is why
`requirements.txt` floors there.

⚠️ **A desktop-only nicety, never the mechanism.** It fires on hover and focus, and
there is no hover on a phone. The thing that works everywhere is `Linked from`.

A preview over a `gated` link shows the unlock box, not the content: the preview
fetches the **built** page, which holds only the form plus ciphertext.

### What a broken link looks like now

It does **not** fail the build. The link renders in red with a dashed underline and a
⚠ on that page only, and the reason appears in the link report — a table in the
Actions run summary, and `/link-report.json` on the live site.

| Report kind | Means |
|---|---|
| `dead-link` | Nothing carries that id, or the target is `hidden`. Includes a did-you-mean. |
| `legacy-path` | An old `path.md` link. Still resolved, but rewrite it as `@id`. |
| `fragile-anchor` | Deep link riding on heading text. Add `{#anchor}` to the heading. |
| `missing-anchor` | The anchor does not exist; the link lands at the top of the page. |
| `duplicate-id` | Two pages claim one id. The second is unreachable by id. |
| `alias-collision` | A retired URL is already a real page. Redirect skipped. |

**Never use a full `https://` URL for an internal page.** It works, which is the
problem: it dodges every check above and rots silently.

---

## Callouts

```markdown
!!! warning "Before you design"
    Smith is a blackbox with real constraints that will bite
    a design late if you learn them late.
```

**The body must be indented four spaces.** That indent is the whole trick.

| Type | Use for | Reads as |
|---|---|---|
| `warning` | Anything that costs money or hurts someone | Amber |
| `note` | Context, gaps, placeholders | Purple |
| `danger` | A genuine safety stop | Red |

**Resist inventing more.** Four callout colors on one page means none read as urgent.

⚠️ **The GitHub web editor sometimes collapses that four-space indent to one** when you
edit a line next to it. The body then falls silently out of the box. If a callout
looks wrong after a phone edit, check the indent first.

---

## Department tabs

```markdown
=== "Lighting"

    All catwalk fixtures are yoked at **45 degrees**.
```

Body indented four spaces, blank line between tabs. **When the page is printed, all
tabs stack** so nothing is lost on paper.

**Keep labels identical across pages:** General staging · Scenic · Lighting · Audio ·
Directors. A reader who picks Lighting on one page gets Lighting on the next, but only
if the label matches character for character.

---

## Tables and the unconfirmed marker

```markdown
| Item | Value |
|---|---|
| Grid height | [To be confirmed]{.tbc} |
```

**`[To be confirmed]{.tbc}`** renders as an amber pill. Use it instead of guessing,
and instead of leaving the row out. A missing row reads as "there is nothing to know
here." An unconfirmed row reads as "measure this before you draft it," which is true.

---

## The footer build stamp

```
University of Rochester International Theatre Program · PR #19
```

**The only signal that a build failed.** When one does, Pages keeps serving the
previous commit: no banner, no error page, the site simply stops changing. A footer
showing a PR older than your edit means your change is not live.

The **deploy time** lives in the stamp's `title` attribute: hover on desktop, or read
the source. ~~It used to sit on the face of the footer~~ and was moved 2026-08-01.

⚠️ **A PR number only reads as stale if you know the current one.** When a build looks
suspicious, check the [Actions runs](https://github.com/maw-agents/uritp-docs/actions).
And the stamp itself can be cached — see the cache-buster note above.

---

## What breaks the build

| # | Failure | Fails the deploy? | Why |
|---|---|---|---|
| 1 | Callout or tab body not indented four spaces | No, renders wrong | Content falls out of the box. |
| 2 | Link to a missing, moved, or `hidden` page | **No, as of 2026-08-01** | Dead-link marker + link report. |
| 3 | `status: gated` with no password at all | **Yes** | Refuses rather than shipping the page wide open. |
| 4 | `gates:` naming a group whose secret is not in the build env | **Yes** | Same reason, and the likelier one. |
| 5 | No blank line before a table or list | No | Renders as one mashed paragraph. |
| 6 | Two H1s on a page | No, renders wrong | Breaks the outline and the page title. |
| 7 | Missing `status:` with no gated ancestor | No | The page silently will not build. |
| 8 | Lowering `mkdocs-material` below 9.7 | **Yes** | `material.extensions.preview` does not exist there. |

---

## The loop

No git, no terminal, nothing installed. Works from a phone.

1. Open the page on the live site, click the **pencil icon**.
2. Edit the markdown. Commit.
3. Wait about ninety seconds.
4. **Check the footer stamp.** If it is not your edit, the build failed.
5. If the page looks unchanged but the stamp is current, **add `?x=1` to the URL**.
   You were reading a cache.

---

## Changing the standards themselves

If you change any file this document describes, **update this file in the same PR**.

| File | Holds | Update here when |
|---|---|---|
| `mkdocs.yml` | Theme, features, extensions, hook order | An extension, plugin, or hook is added or removed |
| `requirements.txt` | Build dependency floors | A floor moves, or a pinned feature changes |
| `.github/workflows/deploy.yml` | Which secrets reach the build | A key group is added, renamed, or retired |
| `docs/.nav.yml` | Top-level sidebar order | The add-a-page procedure changes |
| `docs/<folder>/.nav.yml` | That section's displayed title | The per-folder title mechanism changes |
| `docs/stylesheets/uritp.css` | Palette, headings, `.tbc`, `.gate`, print | A custom class is added, renamed, or dropped |
| `docs/stylesheets/links.css` | The `.deadlink` marker | The marker is restyled or renamed |
| `hooks/visibility.py` | `status:`, `listed:`, `gates:`, `inherit:`, encryption | Any status, inheritance, or gate behaviour changes |
| `hooks/links.py` | `@id` resolution, backlinks, aliases, link report | Link syntax, a report kind, or backlink rules change |
| `hooks/buildstamp.py` | The footer stamp | What the stamp shows changes |
| `docs/javascripts/gate.js` | Browser-side unlock, the keyring | Crypto parameters or the unlock flow change |

A syntax rule described here with no extension behind it is worse than no
documentation: it teaches something that silently renders as literal text. A status
value the hook does not recognise is worse still: the page falls back to `hidden` and
quietly disappears.

**The two halves of the gate must change together.** `hooks/visibility.py` and
`docs/javascripts/gate.js` share the cipher, the KDF and the iteration count. Change
one without the other and every gated page fails to unlock with no readable error.

**Hook order in `mkdocs.yml` is load-bearing.** `visibility.py` resolves status and
drops `hidden` pages before `links.py` builds its id registry. Swap them and a link to
a hidden page would resolve to a URL that 404s instead of being caught.
