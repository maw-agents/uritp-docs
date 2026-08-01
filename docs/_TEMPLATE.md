---
title: New page
id: new-page
status: hidden
---

<!-- ─────────────────────────────────────────────────────────
     URITP DOCS — NEW PAGE TEMPLATE

     1. Copy this file. Rename it kebab-case: rehearsal-studio.md
     2. Drop it in the right folder under docs/. That registers it.
     3. Set `title:` and `id:` above. Leave `status: hidden` until it
        is worth reading.
     4. Delete every block you do not use, including this comment.

     ID          The permanent name other pages link to. Usually the
                 filename without .md. SET IT ONCE AND NEVER CHANGE IT:
                 that promise is what makes links survive a move.

     STATUS      hidden -> not built at all, URL 404s        (start here)
                 unlisted -> live URL, no sidebar, no search
                 gated -> in the sidebar, asks for a password
                 public -> listed, searchable, done

     GATED also needs, on its own line under status:
                 password: theatre2026     (this page only)
                 gates: [psm]              (a named key group)

                 ⚠️ A gated index.md LOCKS ITS WHOLE FOLDER, and the
                 folder WINS over anything a child page declares.
                 Full reference: AUTHORING-GATES.md

     THEME       Optional. Makes this page wear a different skin:
                 theme: utility

                 On an index.md it skins the WHOLE FOLDER. Unlike the
                 lock above, the more specific statement wins here — a
                 page's own `theme:` beats its folder's. Write
                 `theme: default` to stay on the site theme inside a
                 themed folder. Names come from theme/themes.tsv.
                 A name that does not exist falls back and is reported;
                 it will not break the build.

     Full reference: AUTHORING.md at the repo root.
     ───────────────────────────────────────────────────────── -->

# New page

One sentence on what this is and who needs it. This first paragraph
renders as large light lede text automatically. Do not try to make it
big yourself, and keep it to one or two lines.

<!-- ⚠️ That lede is ALSO what the search result shows for this page.
     See AUTHORING-LOOK.md -> "What the search result says". -->

<!-- ── CALLOUT ── warning = costs money or hurts someone
                   note    = context, gaps, placeholders
                   danger  = a genuine safety stop
     Body MUST be indented four spaces. That is the whole trick. -->


## Section heading

Plain paragraph. Blank line between every block: paragraphs, lists,
headings, tables. That single rule prevents most formatting surprises.


## Related

<!-- INTERNAL LINKS ARE IDS, NOT PATHS. Nothing to count, nothing that
     breaks when this file is copied into a subfolder or moved later:

       a page      [Smith Theatre](@smith-theatre)
       a heading   [the notes](@smith-theatre#venue-notes)

     A heading you link to needs an explicit {#anchor}, as above, or
     the link is riding on the heading TEXT and dies when someone
     rewords it. Never use a full https:// URL for an internal page.
     Full reference: AUTHORING.md -> Links. -->

- [Using these docs](@using-these-docs)

---

*Revised Month Year.*
