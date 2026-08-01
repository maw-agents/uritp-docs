# Gates, keys and page visibility

Everything about locking a page: the four publication states, the keystore, key
groups, the folder waterfall, and what the gate honestly does and does not
protect.

> **Split out of `AUTHORING.md` on 2026-08-01, and the reason is worth recording.**
> The gate changed five times in twelve hours, and every change meant re-emitting a
> 29KB canonical document whole — no partial-edit path exists through the tooling in
> use. Each full rewrite is a chance to silently drop a section nobody notices for
> weeks. **The highest-churn subject gets the smallest file.** `AUTHORING.md` keeps a
> one-paragraph summary and points here.

> ⚠️ **This file is CANONICAL for the gate.** If it disagrees with the live config,
> the config wins and this file gets corrected **in the same PR**.

**Describes:** `hooks/visibility.py` · `docs/javascripts/gate.js` ·
the `env:` block of `.github/workflows/deploy.yml`

🔑 **The readable copy of the passwords lives in ClickUp:**
[URITP Docs site — gate key groups](https://app.clickup.com/t/86ajukbme). A GitHub
secret cannot be read back, so **that task is the master and the secret is the copy.**
An agent discussing these passwords should hand Michael that link rather than asking
him to remember what is in the box.

---

## Publication status

**Every page needs a `status:` line, or it inherits one, or it is hidden.**

| Status | Sidebar? | Direct link? | Search? | In the served HTML |
|---|---|---|---|---|
| `public` | **Yes** | Works | **Yes** | The real text |
| `gated` | **Yes** | Password box | Title only | Ciphertext |
| `unlisted` | No | **Works** | No | The real text |
| `hidden` | No | **404** | No | Nothing. Never built. |

Plus one independent switch that composes with any of them:

```markdown
listed: false      # keep out of the nav, search and sitemap
```

⚠️ **A page's `status:` is not the last word.** A gated `index.md` in the folder
above it wins. See [The folder waterfall](#the-folder-waterfall).

### The two questions that separate them

**Can someone reach it by pasting the URL?** `hidden` no — the file is dropped before
the build and the URL 404s. `unlisted` **yes** — fully built and fully readable, just
not linked and not in search. `hidden` is *not published*; `unlisted` is *published
without a signpost*, and an unlisted URL forwarded in one email is public from then on.

**Should people know it exists?** `gated` yes — it sits in the sidebar and asks for a
password; use it when the existence of the page is not the secret. `unlisted` no.

### Gated AND unlisted

```markdown
status: gated
listed: false
gates: [psm]
```

Encrypted **and** undiscoverable. `status: unlisted` is now shorthand for *public +
`listed: false`*, kept because it reads better.

| Situation | Use |
|---|---|
| Finished, safe to design from | `public` |
| Draft circulating to named people | `gated` |
| One page, one password, for a fortnight | `gated` + a literal `password:` |
| One-off for one person, no password ceremony | `unlisted` |
| Locked *and* not advertised | `gated` + `listed: false` |
| Half-written | `hidden` |

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

- A wrong password **fails to decrypt** — not a JavaScript comparison you can step
  around in devtools. There is no plaintext in the page to find.
- The right-hand outline is suppressed, or it would list a locked page's headings.
- Gated pages **never print**.
- A gated page's visible H1 comes from `title:`, not the body `# Heading` — the gate
  replaces the body, so no H1 survives and Material substitutes the title.

**`gates:` is a list and ANY ONE of the named groups' passwords opens the page.**

```markdown
gates: [psm]                 # one group
gates: [psm, admin]          # either password works
gate: psm                    # singular, still valid
```

### A one-page password

**Yes, a password written straight into the page works, and it is a first-class
option rather than a leftover.**

```markdown
---
title: Load-in call
status: gated
password: rehearsal26
---
```

That locks **that one page and nothing else**. No secret to update, no group to
invent, nothing else on the site affected — one line in, one line out. It is the
right tool for a page that needs a lock for a fortnight and a password you are
going to say out loud in a production meeting.

| Use a literal `password:` when | Use a `gates:` group when |
|---|---|
| One page | Several pages share an audience |
| The lock is temporary | The lock outlives any one page |
| You want it obvious in the file | It must be rotatable without editing pages |

⚠️ **The one real cost, and it is the entire reason the keystore exists: a literal
password is committed to a public repository in plaintext, and git keeps it
forever.** Deleting the line tomorrow does not remove it from history. So a literal
password must be **disposable and must never open anything else** — never a group
password, never anything reused elsewhere, never anything close to one.

Both forms compose. A page may carry a literal password *and* name groups, and every
one of them opens it.

### How the encryption works

The body is encrypted **once** with a random content key; that content key is then
encrypted separately per group. A wrapped key is ~100 bytes, so page weight barely
moves as groups are added, rotating one group rewraps ~100 bytes without touching the
body or any other group, and revoking a group from a page is deleting one word.

The wrapped keys ship **shuffled and unlabelled**. Which desk can open a document is
itself information, and an ordered named list would hand it to anyone reading the HTML.

### Unlock once per session, not once per page

A password that opens anything is remembered for the browser session, and every gated
page afterwards tries the whole **keyring** before showing its form. Unlock the Safety
index with the PSM key and every other PSM page opens by itself.

- **Closing the tab re-locks everything** — sessionStorage, not localStorage, because
  a shared shop or lab machine is the normal case here.
- The browser never learns which *group* a key belongs to. It re-runs the same trial
  decryption, so **access is proven by decryption every time** — never by a remembered
  "I am PSM" flag anyone could set in devtools.
- Ceiling 8 keys; each candidate costs a PBKDF2 derivation (~100-200ms on a phone).

---

## The folder waterfall

**Put a gated `index.md` in a folder and the whole folder is locked, at any depth.**
The index file *is* the switch. Folders that have one are locked as a unit; folders
that do not are ordinary folders. Nothing else needs editing and nothing needs
registering.

```
docs/safety/index.md          status: gated, gates: [psm]   <- the switch
docs/safety/lockup.md         (says nothing)      -> locked
docs/safety/test.md           status: public      -> LOCKED ANYWAY, and reported
docs/safety/keys/master.md    (says nothing)      -> locked, two levels down
```

The children are **genuinely encrypted**, not merely hidden from the sidebar. That is
the whole design: hiding child entries until the index unlocks leaves every child
readable by direct URL and in search *while looking protected*, which on a safety
section is the worst of both. Because the lock is real, the sidebar keeps showing the
children honestly, and the keyring opens them as you walk the folder.

### The parent wins

> ~~A page opts out by declaring its own `status:` — *any* value, including `public`
> — or `inherit: false`. **Only silence inherits.**~~
>
> **Reversed 2026-08-01, the day it shipped.** It meant one child writing
> `status: public` quietly punched a hole in a locked safety section, and the page
> that did it looked completely ordinary. A lock you can undo by accident, in a file
> nobody is looking at, is not a lock.

**The nearest gated `index.md` beats whatever the child declared.** Every override is
**named in the build log and in the Actions run summary**, because an override you
cannot see is the same class of defect as the hole it closed.

**Two things the waterfall deliberately cannot do:**

1. **It cannot publish a `hidden` page.** `hidden` is the author saying *this is not
   finished*. A rule whose whole job is to raise protection must never be the reason
   something reached a reader.
2. **It cannot be silent.** `inherit: false` is the one escape, it is one greppable
   line, and using it is a decision somebody made on purpose.

```markdown
---
title: Public safety poster
status: public
inherit: false     # genuinely outside the folder's lock, and says so
---
```

### Keys under the waterfall

A locked child **keeps its own `password:`/`gates:` and gains the parent's.** Any one
of them opens the page. So a local one-page password inside a gated folder still
works, still comes out in one line, and does not disturb the folder key.

---

## The keystore — where a group name finds its password

**Two tiers. In both, the name you type in `gates:` is the name the store is keyed by.**

### Tier 1 — the container (default, and where everything should live)

ONE repository secret, **`URITP_GATE_KEYS`**, whose value is a block of lines:

```
# URITP docs gate keys. One group per line: name = password
admin = ...
dev   = ...
psm   = ...
```

`gates: [psm]` looks up `psm`. **No prefix, no uppercasing, no transformation.**
Adding a group is adding a line to that secret's value — **no file in this repository
changes, and no name is chosen by anything but you.**

Format rules, each one a real silent failure someone would otherwise hit:

| Rule | Because |
|---|---|
| Split on the **first** `=` only | A password may legitimately contain `=` |
| Surrounding whitespace is stripped | A trailing space is invisible in the GitHub box and breaks every unlock with no error |
| `#` is a comment **only at line start** | Mid-line it is an ordinary password character |
| Duplicate group → **first wins**, warned | Last-wins would be silent |
| Blank name or blank password → skipped, warned | Half-typed line |

### Tier 2 — the rotation hatch (rare, deliberate)

A single group MAY instead live in its own secret, `URITP_GATE_<GROUP>` (uppercase,
hyphens to underscores).

**It exists for exactly one reason and it is not "the other way to do it":** rotating a
key inside the container means repasting the whole block, because GitHub never shows
you a secret's current value. For a high-churn key — the one reissued to a new cohort
every September — that risks the other groups every time it turns over. Its own secret
makes that rotation atomic.

**Cost:** GitHub only hands a workflow the secrets it names, so a hatch group needs one
line in `deploy.yml`. That is why the hatch is the exception.

**Precedence:** the container wins, and the duplicate is reported. Silently preferring
either would make a half-finished migration undetectable.

---

## Adding a key group

**Two steps. Neither touches a file in this repository.**

1. **Update the [ClickUp Accounts task](https://app.clickup.com/t/86ajukbme) first.**
   Add your `name = password` line to the block there. This is the master copy.
2. **Paste the whole block** into `URITP_GATE_KEYS` (Settings → Secrets and variables
   → Actions).

Then use it: `gates: [yourgroup]`. Push, wait ~90 seconds.

⚠️ **Always ClickUp first, then GitHub.** The secret box is empty when you open it —
if you edit from memory and your copy is stale by one line, **you silently delete a
group** and find out when someone cannot open a page.

### Rotating

Update the line in ClickUp, repaste the block, push anything (or re-run the workflow).
Every page carrying that group rewraps on the next build; **no page needs editing**.
Anyone mid-session keeps access until they close the tab.

### Repository secret or environment secret?

**Repository. An environment secret silently will not work here.** Environment secrets
are only visible to a job declaring `environment:`, and the **build** job has none —
only **deploy** does, and deploy runs no build. A key on `github-pages` would never
reach the encryption step, and the symptom is the *unavailable* notice with nothing
obviously wrong.

### Secrets or variables?

Both reach the build identically and the hook cannot tell. **Use secrets:** Actions
logs on a public repository are world-readable, and **secrets are masked in them while
variables are not.** Nothing echoes the environment today, but one future debugging
step would put a variable's value in a permanent public log.

⚠️ Masking is a literal string match. A transformed password is not reliably masked —
and **whether GitHub masks a multi-line secret line-by-line is unverified** (checked
2026-08-01, no first-party answer found). The build therefore **never prints a
password, only group names**, which are public in frontmatter anyway.

### If a page says its key is not configured

The page publishes as an **unopenable notice**: content dropped rather than encrypted,
nobody can read it, rest of the site deploys normally. The Actions run summary names
the page and lists **which groups the keystore actually loaded**, and distinguishes
*no keystore at all* from *keystore fine, this group missing* — identical symptoms,
different fixes.

~~A named gate with no secret FAILS THE BUILD.~~ **Changed 2026-08-01, within the hour,
after it froze the whole site over one page.** Taking the entire site stale for one
page's missing config is the same trade `--strict` used to make over a single dead
link. The failure must be *local and visible*, not *global and silent* — and a frozen
site pressures whoever is debugging it into ripping the gate out to get the deploy
back, which is how a locked page ends up public. `URITP_GATES_STRICT=1` restores
hard-fail.

---

## ⚠️ What the gate actually does (and does not)

**While this repository is public, none of this is access control.** The keystore keeps
the **password** out of the repo. It does nothing about the **content**: the markdown
is world-readable at `github.com/maw-agents/uritp-docs`.

| | On the site | In the public repo |
|---|---|---|
| A `hidden` page | Not there at all | **Fully readable** |
| A `gated` page | Encrypted | **Fully readable** |
| An `unlisted` page | Readable by URL | **Fully readable** |
| A literal `password:` | Never rendered | **Fully readable, forever, in history** |

And git never forgets: deleting a page tomorrow leaves it in history forever.

- **`hidden`** stops a half-written page reaching a student by accident. Real job,
  done perfectly.
- **`gated`** signals "not for casual circulation" and stops a forwarded link being
  instantly readable. **Deterrence and framing, which is the job it was chosen for**
  (Michael, 2026-08-01: *"don't circulate this is enough"*).
- **Nothing here protects anything from someone who thinks to look at the repo.**

**Never put student data, personal contact details, credentials, medical or
disciplinary information, or contract terms on a page and rely on the gate.** If it
must not be read, it does not belong in this repo.

**If that changes:** make the repo private (Pages from a private repo needs GitHub Pro,
~$4/month). The keystore plumbing is already in place; that is the only remaining step.

---

## Verifying a visibility change

**A green build is not proof.** The Pages CDN or a phone browser can keep serving the
old page. On 2026-08-01 a page was reported as "gated but serving plaintext" across two
green builds; **the gate had been working the whole time** and every check had read a
cache.

1. **Load it with a junk query string:** `…/safety/?x=1`. A query the CDN has never seen
   forces a fresh fetch. **The single most useful trick here.**
2. **Cross-check `/search/search_index.json`** — regenerated every build, rarely cached
   in step with the HTML. A gated page appears there as *"Restricted page … Unlock"*.
3. **For a waterfall change, read the run summary.** Every page the folder overruled is
   listed there by name. If a page you expected to be locked is not on that list,
   nothing locked it.

**A check that returns the same answer whether or not you are right has verified
nothing.** A plain reload is exactly that check.

Also: a status change does nothing until a build succeeds. **Check the footer stamp.**

---

## Changing the gate itself

**`hooks/visibility.py` and `docs/javascripts/gate.js` share the cipher, the KDF and
the iteration count. They change in the SAME PR** or every gated page fails to unlock
with no error anyone can read.

**Hook order in `mkdocs.yml` is load-bearing:** `visibility.py` resolves status and
drops `hidden` pages before `links.py` builds its id registry.

**Test a workflow change on a branch.** Every PR now runs a build-only check (deploy is
skipped on PRs). This exists because a workflow edit went straight to `main` on
2026-08-01, came back `action_required` with zero jobs, and stopped the site deploying —
a failure mode you cannot see by reading the file.
