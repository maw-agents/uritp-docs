"""
The size gate.

Every build: measure every file in this repo and refuse to grow one past the
point where a maintainer -- human or agent -- can read it whole.

    theme/contrast.tsv  ->  a colour pair nobody can READ fails the build
    size-budget.tsv     ->  a FILE nobody can read fails the build

WHY THIS EXISTS
On 2026-08-01 ``docs/stylesheets/uritp.css`` reached 34.9KB and every attempt
to read it back clipped at the same byte, silently, four times in one session.
The last ~6KB of the site's only stylesheet -- tabs, links, the gate, the page
foot, mobile and print -- was being reasoned about from the section index at
the top of the file rather than from the rules themselves, and answers were
given about rules nobody had actually seen. Nothing in the build said a word.

That is the whole argument. The cap was already a rule; it was enforced by
whoever happened to notice, which is not enforcement. ``hooks/contrast.py``
already proved the shape works for colour: a build-time check turns a standard
nobody remembers into a standard nobody can miss. This is the same gate
pointed at bytes.

⚠️ THE FAIL NUMBER IS A POLICY LINE, NOT A MEASURED WALL, AND SAYING OTHERWISE
WOULD REPEAT THE DEFECT THIS REPO KEEPS SCORING. What has actually been
observed: a 30.6KB file read back WHOLE on 2026-07-29, and a 34.9KB file
clipped on 2026-08-01. So the real ceiling is somewhere between those two and
nobody has characterised it. The thresholds here sit BELOW the lowest observed
failure on purpose -- a budget you hit before the cliff, not a measurement of
where the cliff is. If you narrow the range, correct this paragraph with it.

WHY THE BUDGET IS A TSV AND NOT A DICT IN THIS FILE
Same reason the theme is, and the same reason contrast.tsv is: the maths
belongs in code and the policy does not. A threshold becomes a cell Michael
can edit, an exemption becomes a row with a NOTE COLUMN explaining itself, and
every waiver shows up in a diff instead of hiding in an ignore-list in Python.

⚠️ IT LIVES AT THE REPO ROOT, NOT IN theme/. The theme folder is documented as
"everything about the look"; a read-size budget is not a look. Putting it there
would be the exact filing-by-nearest-surface mistake the repo has logged before.

FIRST MATCHING ROW WINS, so the budget is ordered specific-to-general. Note
that fnmatch's ``*`` SPANS SLASHES -- ``*.md`` matches ``docs/venues/x.md`` --
which is why ``docs/*.md`` has to sit above ``*.md`` and why the catch-all is
last. A file that reaches the catch-all is reported as unbudgeted rather than
quietly accepted: a file nobody chose a limit for is a file nobody thought
about.

WHAT IS DELIBERATELY NOT GATED
Authored pages under ``docs/`` get a generous budget and, in practice, only
ever warn. A gate that blocks Michael from writing a long venue page would be
a gate that gets switched off, and the problem this solves is source files
agents have to edit, not prose humans have to read on a screen with a scroll
bar.

``URITP_SIZE_STRICT=1`` promotes every warning to a failure, for when someone
wants the whole house clean. ``URITP_SIZE_GATE=0`` disables it entirely -- and
if you find yourself setting that, the honest move is to raise a number in the
TSV and say why in its note, where the next person can see it.

Runs in ``on_config`` so it fails in the first second of a build rather than
after a full render. Registered in mkdocs.yml under ``hooks:``. Its position in
that list does not matter: it reads the filesystem, not the config.
Documented in AUTHORING.md.
"""

import fnmatch
import os

BUDGET = "size-budget.tsv"
KB = 1000                    # what GitHub's file listing shows, so the numbers
                             # in the TSV match the numbers you see in the UI

ENABLED = os.environ.get("URITP_SIZE_GATE") != "0"
STRICT = os.environ.get("URITP_SIZE_STRICT") == "1"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", ".github/ISSUE_TEMPLATE", "site", "__pycache__",
             ".venv", "node_modules", ".mypy_cache", ".ruff_cache"}
CATCH_ALL = "*"


def _fail(message):
    raise ValueError(BUDGET + ": " + message)


def _rows():
    """The budget, in order. Order is the matching precedence."""
    path = os.path.join(ROOT, BUDGET)
    if not os.path.exists(path):
        _fail("is missing. The gate cannot run without its policy.")

    out = []
    with open(path, encoding="utf-8") as fh:
        lines = [ln.rstrip("\n") for ln in fh if ln.strip()]
    if not lines:
        _fail("is empty.")

    header = lines[0].split("\t")
    for needed in ("glob", "warn", "fail"):
        if needed not in header:
            _fail("has no `" + needed + "` column.")

    for line in lines[1:]:
        cells = line.split("\t")
        row = dict(zip(header, cells))
        glob = (row.get("glob") or "").strip()
        if not glob:
            continue
        try:
            warn = float(row["warn"])
            fail = float(row["fail"])
        except (KeyError, ValueError):
            _fail("`" + glob + "` has a non-numeric warn or fail.")
        if warn <= 0 or fail <= 0:
            _fail("`" + glob + "` has a threshold at or below zero.")
        if fail < warn:
            _fail(
                "`" + glob + "` fails at " + str(fail) + "KB but only warns at "
                + str(warn) + "KB, so the warning can never fire."
            )
        out.append((glob, warn, fail, (row.get("note") or "").strip()))

    if not out:
        _fail("has no usable rows.")
    if out[-1][0] != CATCH_ALL:
        _fail(
            "must end with a `" + CATCH_ALL + "` row, or a new kind of file "
            "would be measured against nothing at all."
        )
    return out


def _walk():
    """Every tracked-ish file, as (relative posix path, bytes)."""
    found = []
    for base, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".git")]
        for name in names:
            full = os.path.join(base, name)
            rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
            if any(rel.startswith(skip + "/") for skip in SKIP_DIRS):
                continue
            try:
                found.append((rel, os.path.getsize(full)))
            except OSError:
                # A file that vanished mid-walk is not a size problem.
                continue
    return sorted(found)


def _match(rel, rows):
    for glob, warn, fail, note in rows:
        if fnmatch.fnmatch(rel, glob):
            return glob, warn, fail, note
    return None


def on_config(config):
    if not ENABLED:
        print("size: gate disabled by URITP_SIZE_GATE=0")
        return config

    rows = _rows()
    failures = []
    warnings = []
    unbudgeted = []
    biggest = []

    for rel, size in _walk():
        glob, warn, fail, _note = _match(rel, rows)
        kb = size / KB
        biggest.append((kb, rel, glob, warn, fail))

        if glob == CATCH_ALL and kb >= warn:
            unbudgeted.append(
                rel + " is " + format(kb, ".1f") + "KB and matches no rule but "
                "the catch-all"
            )

        detail = (
            rel + " is " + format(kb, ".1f") + "KB (" + glob + " allows "
            + format(fail, ".0f") + "KB)"
        )
        if kb >= fail:
            failures.append(detail)
        elif kb >= warn:
            warnings.append(
                rel + " is " + format(kb, ".1f") + "KB, past the "
                + format(warn, ".0f") + "KB warning for " + glob
            )

    if STRICT:
        failures.extend(warnings)
        warnings = []

    biggest.sort(reverse=True)

    print("size: " + str(len(biggest)) + " file(s) against " + str(len(rows))
          + " budget row(s)")
    for kb, rel, _glob, _warn, _fail in biggest[:5]:
        print("  " + format(kb, "6.1f") + "KB  " + rel)
    for note in warnings + unbudgeted:
        print("::warning::size: " + note)

    _summary(failures, warnings, unbudgeted, biggest)

    if failures:
        raise ValueError(
            "size-budget.tsv: " + str(len(failures))
            + " file(s) are too big to read whole --\n  "
            + "\n  ".join(failures)
            + "\nSplit the file, or raise its row in size-budget.tsv and say "
            "why in the note. Do not reach for URITP_SIZE_GATE=0: a limit "
            "nobody can see is the thing this gate was built to replace."
        )
    return config


def _summary(failures, warnings, unbudgeted, biggest):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return

    lines = ["### 📏 Size", ""]
    if failures:
        lines += [
            "🔴 **" + str(len(failures)) + " file(s) cannot be read whole.** "
            "The build stopped.",
            "",
        ]
        lines += ["- `" + f + "`" for f in failures]
        lines.append("")
    else:
        lines += ["✅ Every file is inside its budget.", ""]

    lines += ["| File | Size | Budget | Fails at |", "|---|---|---|---|"]
    for kb, rel, glob, warn, fail in biggest[:12]:
        mark = " ⚠️" if kb >= warn else ""
        lines.append(
            "| `" + rel + "`" + mark + " | " + format(kb, ".1f") + "KB | `"
            + glob + "` | " + format(fail, ".0f") + "KB |"
        )

    extra = warnings + unbudgeted
    if extra:
        lines += [
            "",
            "<details><summary>" + str(len(extra)) + " warning(s)</summary>",
            "",
        ]
        lines += ["- " + w for w in extra]
        lines += ["", "</details>"]

    lines += [
        "",
        "Budgets live in `size-budget.tsv`, first matching row wins. A warning "
        "is the file telling you it wants splitting before it has to. "
        "`URITP_SIZE_STRICT=1` enforces every warning.",
    ]
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
