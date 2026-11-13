# Reproducing the New Jersey snapshots

The history records the Legislature's official `STATUTES-TEXT.zip` on ten archived
observation dates, from 2021-09-22 to 2026-10-25. Its dates describe observations,
not when chapter laws took effect. The current published history also includes
later documentation and date-status overlays; reconstructing the original
snapshots does not reproduce those later commits.

## Source responses

The unchanged `build/DATA-SHA256SUMS` records the SHA-256 and exact original URL
of each of the 20 responses used for the original build. Ten are archived copies
of the official ZIP; the others are source-listing and robots records. Each ZIP
contains `STATUTES.TXT` and `STATUTES.RTF`. The builder uses the plain-text file.
The RTF's normative image content has not been independently inventoried.

Supply the original response bodies in a source directory. A body may be named
by its SHA-256 from the manifest, by the SHA-256 of its URL, or by the latter plus
`.gz` for a gzip-compressed body. Checksums apply to uncompressed response bytes.
The reader makes no network requests and rejects a checksum mismatch.

```powershell
$env:NJ_SOURCE_CACHE = (Resolve-Path ./source-responses).Path
python -X utf8 -I build/source.py verify
python -X utf8 -I build/build.py check
python -X utf8 -I build/build.py repo ./rebuilt
```

`verify` checks every recorded response and exits 1 if any is missing. `check`
requires the ten ZIP responses and compares every rendered word with the
original `STATUTES.TXT`, allowing only a section number's trailing period and
Markdown formatting. It reports unassigned text as an error. `repo` uses the
same checks and writes a new history; it refuses a directory with existing
commits. Use a separate empty destination for each reconstruction.

The source-response reader was added on 13 November 2026 to replace an absent
dependency. Source availability and a full reconstruction remain to be checked
when the original response bodies are available. No statute was changed by
this tooling repair.

## Observations in the original build

| Date seen | Address captured | STATUTES.TXT dated | File says "updated through" | Sections | ZIP bytes |
| --- | --- | --- | --- | ---: | ---: |
| 2021-09-22 | `https://www.njleg.state.nj.us/Statutes/STATUTES-TEXT.zip` | 2021-09-21 | P.L.2021, c.181 and J.R.3 | 54,145 | 38,342,769 |
| 2021-12-15 | `https://www.njleg.state.nj.us/Statutes/STATUTES-TEXT.zip` | 2021-12-14 | P.L.2021, c.272 and J.R.3 | 54,328 | 38,609,367 |
| 2025-08-08 | `https://pub.njleg.state.nj.us/statutes/STATUTES-TEXT.zip` | 2025-08-07 | P.L.2025, c.80, and J.R.10 | 55,698 | 40,576,348 |
| 2025-10-05 | `https://pub.njleg.state.nj.us/statutes/STATUTES-TEXT.zip` | 2025-10-04 | P.L.2025, c.138, and J.R.10 | 55,802 | 40,698,637 |
| 2026-07-05 | `https://pub.njleg.state.nj.us/statutes/STATUTES-TEXT.zip` | 2026-07-04 | P.L.2025, c.346, and J.R.22 | 56,145 | 41,173,019 |
| 2026-07-12 | `https://pub.njleg.state.nj.us/statutes/STATUTES-TEXT.zip` | 2026-07-11 | P.L.2025, c.346, and J.R.22 | 56,145 | 41,173,019 |
| 2026-08-30 | `https://pub.njleg.gov/statutes/STATUTES-TEXT.zip` | 2026-08-29 | P.L.2025, c.405, and J.R.22 | 56,235 | 41,284,079 |
| 2026-10-18 | `https://pub.njleg.gov/Statutes/STATUTES-TEXT.zip` | 2026-10-17 | P.L.2026, c.50, and J.R.1 | 56,338 | 41,443,870 |
| 2026-10-23 | `https://pub.njleg.gov/statutes/STATUTES-TEXT.zip` | 2026-10-23 | P.L.2026, c.50, and J.R.1 | 56,339 | 41,444,376 |
| 2026-10-25 | `https://pub.njleg.gov/statutes/STATUTES-TEXT.zip` | 2026-10-24 | P.L.2026, c.50, and J.R.1 | 56,339 | 41,444,376 |

## Text, dates and credits

Every statute word comes from the official plain-text file. Whitespace and
Markdown structure are normalized; statutory wording is preserved. A repeated
section number receives a numbered suffix in file order. Sections absent from
a later observation retain the original repository's absence note.

Changes are credited to a chapter law only when exactly one new citation appears
in the section's source note between observations. Multiple citations or none
receive the original repository's explicit uncredited treatment. An observation
does not establish a chapter law's effective date or the text between captures.

The original builder and documents were authored with Claude Code on 28 October
2026; the response reader and reproduction repair were authored with Codex on
13 November 2026. No model generated or corrected statutory wording. No model
is invoked by the build. The text has not been reviewed line by line by a lawyer.
