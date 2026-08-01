---
title: safety test page
status: public
---

<!-- ─────────────────────────────────────────────────────────
     URITP DOCS — NEW PAGE TEMPLATE

     1. Copy this file. Rename it kebab-case: rehearsal-studio.md
     2. Drop it in the right folder under docs/. That registers it.
     3. Set `title:` above. Leave `status: hidden` until it is worth reading.
     4. Delete every block you do not use, including this comment.

     STATUS      hidden -> not built at all, URL 404s        (start here)
                 unlisted -> live URL, no sidebar, no search
                 gated -> in the sidebar, asks for a password
                 public -> listed, searchable, done

     GATED also needs, on its own line under status:
                 password: theatre2026
                 gate: designers   (reads URITP_GATE_DESIGNERS instead)

     Full reference: AUTHORING.md at the repo root.
     ───────────────────────────────────────────────────────── -->

# New title here

One sentence on what this is and who needs it. This first paragraph
renders as large light lede text automatically. Do not try to make it
big yourself, and keep it to one or two lines.

<!-- ── CALLOUT ── warning = costs money or hurts someone
                   note    = context, gaps, placeholders
                   danger  = a genuine safety stop
     Body MUST be indented four spaces. That is the whole trick. -->

!!! warning "Read before you design"
    The one constraint that will wreck a design if it is learned late.
    Delete this block if the page has no such constraint.

!!! note "Not yet documented"
    Placeholder wording while the page is still `hidden`. Say what is
    missing and who to ask in the meantime.

## Section heading

Plain paragraph. Blank line between every block: paragraphs, lists,
headings, tables. That single rule prevents most formatting surprises.

**Bold** for the thing that matters. *Italic* sparingly. `Code` for
filenames and exact values.

- Bulleted item
- Another item

1. Numbered step
2. Next step

### Sub-point

Do not go deeper than `###`. If you need a fourth level, the page
wants splitting into two.

<!-- ── SPEC TABLE ── source columns need not line up.
     [To be confirmed]{.tbc} is the amber pill. Use it instead of
     guessing, and instead of leaving the row out entirely. -->

## Technical specifications

| Item | Value |
|---|---|
| Something known | The confirmed value |
| Something else | Another confirmed value |
| Something unmeasured | [To be confirmed]{.tbc} |

<!-- ── DEPARTMENT TABS ── body indented four spaces, blank line
     between tabs. Keep these five labels spelled EXACTLY like this
     across every page or the reader's choice stops carrying over. -->

## Venue notes

Every note here exists because it caught someone out. Pick your
department.

=== "General staging"

    Crossovers, travel paths, transition timing.

=== "Scenic"

    Walls, permanent rigging, what is not as flat as it looks.

=== "Lighting"

    Positions, yoke angles, dimming, power.

=== "Audio"

    Speaker positions, what moves and what does not.

=== "Directors"

    Consequences for staging. What the room simply cannot do.

<!-- ── LINKS ── internal links point at the .md FILE, never the live
     URL. The build rewrites them and fails loudly on a bad target,
     which is the protection. A full https:// link to an internal page
     dodges that check and rots silently. -->

## Drawings and files

Hosted in Box. Access follows your University of Rochester account.

- [Technical drawings](https://rochester.box.com/s/REPLACE)
- [Reference images](https://rochester.box.com/s/REPLACE)

## Who to ask

| Topic | Ask |
|---|---|
| Rigging, hanging, load-in scheduling | Production Management |
| Power, relays, console time | Lighting Supervisor |
| Speaker position, comms, playback | Audio Supervisor |
| Shop time, materials, budget | Technical Direction |

## Related

- [Smith Theatre](venues/smith-theatre.md)
- [Safety and health](safety/index.md)

---

*Revised Month Year.*
