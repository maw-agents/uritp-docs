# Gates, keys and page visibility

Everything about locking a page: the four publication states, the keystore, key
groups, folder inheritance, and what the gate honestly does and does not protect.

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
[URITP Docs site — gate key groups](https://app.clickup.com/t/86ajv5xnh). A GitHub
secret cannot be read back, so **that task is the master and the secret is the copy.**
An agent discussing these passwords should hand Michael that link rather than asking
him to remember what is in the box.

---

## Publication status

**Every page needs a `status:` line, or it is inside a locked folder, or it is
hidden.**

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

### The one-page password

A page can carry its own password directly, with no keystore and no repository
secret involved:

```markdown
---
title: Todd Lock-up
status: gated
password: pmgate
---
```

**This is a first-class path, not a fallback.** It behaves exactly like a group key
everywhere it matters:

- It encrypts the same way, with the same cipher and the same iteration count.
- It **composes** with `gates:`. A page may carry both, and any one of them opens it.
- It **inherits** down a folder. A gated `index.md` with a literal password locks its
  whole subtree with that password.
- The session **keyring** remembers it like any other key, so it opens every other
  page using the same literal without asking again.
- The literal is stripped from the page metadata before render. It never reaches the
  served HTML.

**What it costs, stated rather than discouraged:** the password sits in the
repository, and git remembers it forever, so rotating it is a history problem rather
than a secret edit. And it cannot be shared between pages without being retyped in
each one, which is a divergence waiting to happen.

| Reach for | When |
|---|---|
| `password:` | One page. A quick lock you want to see and change in the file you are already editing. Beta, drafts, a single procedure. |
| `gates:` | Two or more pages want the same password, or the password must be rotatable, or it must not be in the repo. |

**The moment a second page wants the same password, move it to a group.** That is the
line, and it is the only one.

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

## 🔒 A gated folder index locks its whole subtree, and the lock WINS

**The `index.md` is the switch.** A folder that has one, gated, is a locked folder. A
folder without one is transparent and inheritance walks straight past it. That is why
not every folder needs an index file, and why the ones that have it can still be
opened and read as pages in their own right.

```
docs/safety/index.md            status: gated, gates: [psm]
docs/safety/lockup.md           -> locked
docs/safety/safety-test-1.md    status: public   -> locked ANYWAY
docs/safety/keys/master.md      -> locked, at any depth
```

The children are **genuinely encrypted**, not merely hidden from the sidebar. That is
the whole design: hiding child entries until the index unlocks leaves every child
readable by direct URL and in search *while looking protected*, which on a safety
section is the worst of both. Because inheritance is real, the sidebar keeps showing
the children honestly, and the keyring opens them as you walk the folder.

**Nesting composes.** The nearest gated ancestor wins, at any depth, so a locked
folder inside a locked folder behaves the way it reads.

### ⚠️ Precedence flipped 2026-08-01

~~A page opts out by declaring its own `status:` — *any* value, including `public` —
or `inherit: false`. **Only silence inherits.**~~

**Changed the same day, by Michael.** Under the old rule `docs/safety/safety-test-1.md`
declared `status: public`, was therefore treated as having opted out, and served
plaintext by direct link while the Safety section looked locked. **A lock whose opt-out
is spelled the same as an ordinary setting is not a lock.** The folder is now the unit
of protection.

**Three pass-throughs, and they are the only three:**

| Frontmatter | What happens | Why |
|---|---|---|
| `status: hidden` | Still hidden. Not built, not published. | `hidden` means *not built*. A lock must never **publish** a page its author suppressed — escalating a half-written draft into a live encrypted page is worse than the leak this flip fixed. |
| `status: gated` | Keeps its **own** keys. Not merged with the folder's. | The page is already locked, so the folder lock has nothing to add. Merging keyrings would hand the folder's group a page deliberately locked to a different one. **Widening access is not inheritance.** |
| `inherit: false` | Published as declared, loose inside the locked tree. | The explicit escape hatch. One greppable string, so "what is loose in here?" is a search, not a reading exercise. |

**An overridden page keeps its own unlisted-ness.** A page that chose `unlisted`, or
set `listed: false`, stays out of the nav, search and sitemap after the lock takes it.
Otherwise locking a folder would quietly promote its quietest page into the sidebar,
which is an escalation dressed up as a security fix.

**Every override is named in the build output** and in the Actions run summary: the
page, the status it declared, and the index that overruled it. The flip traded one
invisible behaviour for another, and printing the list is what makes that trade
honest.

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

1. **Update the [ClickUp Accounts task](https://app.clickup.com/t/86ajv5xnh) first.**
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
| A `password:` literal | Never in the HTML | **Fully readable, and in history forever** |

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
**That is also the step that turns the weak beta passwords into a real question** — as
long as the source is public, key strength changes nothing, so it is not worth
spending on until the repo turns private.

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
