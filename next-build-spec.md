# Next build spec

What this repo builds next, and why. **Design lives here. Open questions for Michael
do NOT** — markdown renders `- [ ]` as inert text, so a question asked in a repo file
cannot be answered in a repo file. Those go to a ClickUp Decision Log with a pointer
left here.

Status values: **Scratch** (idea, not agreed) · **Next build** (agreed, not started) ·
**Futures** (agreed, deferred) · **In review** (shipped, watching it).

---

## 1. Multi-key gate groups — `psm` / `designers` / `supervisors`

**Status: Scratch.** Raised by Michael 2026-08-01: *"could we offer multiple password
'groups' if we implemented real git secrets. like a psm key or a designer key or a
supervisor key that might be used to unlock the same or select layouts/files."*

**Feasible, and the mechanism is standard.** It is not a bigger version of what we
have; it is a different shape, and the difference is what makes it cheap.

### Why the obvious approach is wrong

The naive version encrypts the page body once per group and ships N copies. Three
groups on a 40KB page is 120KB, every reader downloads all of it, and rotating one
key means re-encrypting everything. It also scales the wrong way: cost grows with
content size times group count.

### Envelope encryption: encrypt the body once, wrap the key N times

1. Build generates a random **content key** (CEK) per page.
2. The finished HTML is encrypted **once** with the CEK. This is the only large blob.
3. For each group named on the page, derive a **key-encrypting key** from that group's
   secret (PBKDF2, its own salt) and use it to encrypt *the CEK*.
4. The page ships one ciphertext body plus a small list of wrapped CEKs.

A wrapped CEK is about **100 bytes**. Five groups costs ~500 bytes, not five copies of
the page. **Page weight is effectively independent of how many groups can open it**,
which is the whole reason to do it this way.

Unlocking: the reader types one password, the client tries each wrapped key until one
unwraps, then decrypts the body with the recovered CEK. A wrong password unwraps
nothing — same property as today, no plaintext in the page to read around.

### What it buys beyond "more passwords"

| Operation | Cost |
|---|---|
| Rotate one group's key | Rewrap that group's ~100 bytes. Body untouched, other groups unaffected. |
| Revoke a group from one page | Delete one line of frontmatter. |
| Add a group to a page | Add one line. |
| Add a whole new group | One Actions secret + one line per page that wants it. |

### Authoring surface

```markdown
---
title: Todd Lock-up
id: todd-lockup-procedure
status: gated
gates: [psm, supervisors]
---
```

`gates:` is a list; `gate:` (singular, existing) stays valid as a one-element list so
no page has to change. `password:` in frontmatter stays supported for a throwaway
draft and stays documented as **publishing the password**.

~~Each name reads `URITP_GATE_<NAME>` from the build environment.~~ **Superseded
2026-08-01:** names resolve from the `URITP_GATE_KEYS` container secret with no
transformation at all, and the per-group variable survives only as the rotation
hatch. See AUTHORING-GATES.

That answers the "select layouts/files" half directly: a supervisor key on venue
pages, a PSM key on lock-up procedures, a designer key on paperwork standards, and
pages that want two just name two.

### Hard requirements, each earned tonight

1. ~~**A named gate with no secret in the environment FAILS THE BUILD.** Not a
   warning.~~ **REVERSED 2026-08-01, same night.** Failing the build took the entire
   site stale over one page's missing config, and a frozen site pressures whoever is
   debugging it into reverting the gate to get the deploy back — which is how a locked
   page ends up public at 2am. A missing key now DROPS the content and locks that one
   page. `URITP_GATES_STRICT=1` restores hard-fail. The concern behind the original
   rule was right; the remedy was the wrong shape.
2. **`visibility.py` and `gate.js` change in the SAME PR.** They share the cipher, the
   KDF and the iteration count. Change one and every gated page fails to unlock with
   no readable error. **Scope clarified 2026-08-01:** this binds the CRYPTO. A DOM-only
   change to `gate.js` (a heading tidy-up, an ARIA attribute) does not fire it and is
   documented in AUTHORING-LOOK instead.
3. **A wrapped-key list must not leak the group names to the reader.** Ship the wraps
   as an unlabelled array. Which desk can open a document is itself information.
4. **Verify with a cache-buster after deploying.** A plain reload of a gated page
   returns identical bytes whether the gate works or not.

### ⚠️ The part that is not a build task

**Multiple keys do not make the gate real, and neither do Actions secrets.** While the
repository is public the markdown is world-readable, so the *content* is exposed no
matter how the *password* is stored. Secrets fix the password leak only.

The order that actually matters:

1. **Repo private** (GitHub Pages from a private repo needs GitHub Pro, ~$4/month).
   This is the step that converts the gate from deterrence into a lock.
2. **Secrets** via `gates:`, so no key is ever committed.
3. **Groups**, which is this spec.

Building 3 before 1 produces a more sophisticated deterrent, not security. Worth doing
anyway — the group model is the right shape and costs little — but it must not be
mistaken for the lock.

### Out of scope, named so it is not assumed

- **Per-section gating within one page** (a supervisor block inside a public page) is a
  different and much harder problem: partial encryption breaks the table of contents,
  the search index, and print. If a section needs a different audience, it is a
  different page.
- **Per-reader identity, audit logging, or revocation of someone who already unlocked.**
  A shared password cannot do any of those. Anyone who has read a page has read it.

---

## 2. `safety/safety-test-1.md` still carries the only two link-report issues

**Status: Next build.** One `legacy-path` (`index.md` → `@safety`) and one `dead-link`
(`../venues/smith-theatre.md`, stale since Smith moved into `SPAC/`). It is a scratch
page, so this is a one-minute fix rather than a risk — but it is the only red in the
report, and a report that is never clean stops being read.

---

## 3. Headings on a gated page

**Status: In review — the visible half is FIXED, one cosmetic remnant is still open.**

Original observation, 2026-08-01: on `safety/todd-lockup-procedure` the source H1 reads
`# Todd Lock-up 🔐 Procedure` and the served page shows **Todd Lock-up**.

The mechanism was diagnosed correctly. The gate replaces the rendered body, so no
`<h1>` survives into the content and Material's fallback injects `page.title` in its
place. A gated page's heading therefore comes from `title:` while a public page's comes
from its H1.

### 🔴 What this spec got wrong, kept visible rather than deleted

> ~~Cheapest fix: have `visibility.py` emit an `<h1>` carrying the page title above the
> lock box, so the heading source is the same whether or not a page is gated. Needs a
> look at whether that then double-renders under Material's fallback check.~~

**That fix would have shipped the bug it was worried about — and the bug was already
live by a different route.** Material's fallback fires when the *built* content holds
no `<h1>`, which it does not. Then `gate.js` inserts the decrypted body, which carries
the page's real `<h1>`. **The reader saw the title twice, every time, on every gated
page — but only after unlocking.** Michael's screenshot showed it plainly.

It hid for a day because *the built page is right and the live page is right*, right up
until somebody types the password. Any verification that stopped short of unlocking was
structurally incapable of finding it.

**Fixed 2026-08-01:** `reveal()` in `gate.js` drops the injected heading and keeps the
authored one, identified by what it structurally lacks — Material injects a bare `<h1>`
with no `id`, while an authored heading gets an `id` and a `.headerlink` from the `toc`
extension. See AUTHORING-LOOK → *Two `gate.js` behaviours documented here*.

### Still open

**Before unlocking, *Skip to content* on a gated page points at an anchor that is not
in the DOM.** It is built from the original H1, which does not exist until the page is
unlocked; after unlocking it resolves correctly. Cosmetic, keyboard-only, and the fix
(teaching `visibility.py` to carry the anchor onto the lock box) touches the gate for
a benefit measured in one tab press. Logged, not scheduled.

---

## 4. Sidebar cascade — hide a section's children until its index unlocks

**Status: Futures.** Asked for 2026-08-01 and deliberately not built. A hidden nav
entry implies protection it does not provide: the children stay reachable by direct
URL and stay in search. Folder gate *inheritance* shipped instead, which is real
encryption, so the sidebar can stay honest. Revisit only as a convenience layer on
top of per-page gates, never as a substitute.
