# How this history was made, and how to make it again

## Short version

```sh
cd build
python -I fetch.py robots && python -I fetch.py zips   # read every source (cached; one request at a time, 5 s apart)
sha256sum -c DATA-SHA256SUMS                           # see the note on the format below
python -I build.py check                               # parse every capture and check it word for word
python -I build.py repo ../../rebuilt                  # the same commits, with the same hashes
```

`fetch.py` and `build.py` expect each other and `docs.py`/`tool.py` in one folder, and write their cache to `cache/`
beside them. `DATA-SHA256SUMS` lists `sha256  URL` for each response (the cache keeps gzip-compressed copies, so check
by decompressing each and hashing it). sha256 of that list: `cf5489365b2d59f792b08348aca30a4ee83da12650901a0df19a5b62d9fae1f4`. The last change commit is
`2fec8cca199f85de702fa490310f051f2b412f65`.

## Sources

| What | Where | Requests |
| --- | --- | ---: |
| The Internet Archive's lists of its captures of the official file, at its three addresses | `http://web.archive.org/cdx/search/cdx?url=<address>&output=json` for `pub.njleg.state.nj.us/statutes/STATUTES-TEXT.zip`, its alias `pub.njleg.gov/statutes/STATUTES-TEXT.zip` and its earlier home `njleg.state.nj.us/statutes/STATUTES-TEXT.zip` | 3 |
| Each distinct capture (by the Archive's content digest), unmodified | `http://web.archive.org/web/<timestamp>id_/<address>` | 10 |
| robots.txt checks (see below), and one more address searched for copies (`njleg.gov/statutes/`, none) | `web.archive.org/robots.txt`, the archived robots.txt files and their capture lists | 7 |
| The live robots.txt of the official host | `https://pub.njleg.state.nj.us/robots.txt` | 0 answered (timed out) |

20 responses were received and cached in all (406,189,860 bytes of zip files), each listed in
`build/DATA-SHA256SUMS`. The captures used:

| Date seen (commit date) | Address captured | STATUTES.TXT dated | File says "updated through" | Sections | Zip bytes |
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

Each zip holds `STATUTES.TXT` (plain text, used here) and `STATUTES.RTF` (the same text as rich text, not used). Two
different files captured on one day would keep only the later one; the earliest capture of identical content is used.
Captures whose content is identical to the one before give no commits.

## robots.txt, checked 28 October 2026

- **pub.njleg.state.nj.us** (the official file's host) and **www.njleg.state.nj.us**: not reachable from where this
  was built (connections timed out, from a non-US address), so the live file was not used and the Archive's copies were
  used instead. The Internet Archive's newest copy of `https://pub.njleg.state.nj.us/robots.txt` (19 January 2026) is a
  redirect to the main site's robots.txt, whose newest archived copy (9 May 2026) reads:

  ```
  User-agent: *
  Allow: /
  
  # Host
  Host: https://www.njleg.state.nj.us
  
  # Sitemaps
  Sitemap: https://www.njleg.state.nj.us/sitemaps/sitemap.xml
  Sitemap: https://www.njleg.state.nj.us/sitemaps/bills-sitemap.xml
  ```

  No archived robots.txt exists for pub.njleg.gov. Nothing disallows the statutes files.
- **web.archive.org**: `/robots.txt` answers 404 (no rules).

Requests went one at a time, at least 5 seconds apart, with the user agent
`Mozilla/5.0 (compatible; Lexifina state law history; +https://lexifina.com/watch)`; 429 and 5xx answers would have
been retried with backoff honouring Retry-After (none came). While the first fetch ran, a few one-off capture-list
queries were sent by hand, so for about a minute two requests to web.archive.org were in flight at once. Every response
is cached on disk and never fetched twice.

## The build, step by step

1. `python -I fetch.py robots`, `python -I fetch.py zips` (Python 3.12.10, standard library only).
2. `python -I build.py repo <out>` reads each capture, splits `STATUTES.TXT` into sections at each line that starts at the
   margin with a section number (`2A:4A-22`, `App.A:11-4`), and checks the result word for word: the words of every
   rendered section, with the Markdown taken out, and of the lines outside sections (the file's header and the title
   lines) must equal, in order, every word of the source file. Then it writes the history with `git fast-import`
   (git 2.46.0.windows.1): the oldest capture, then each later capture's changes in date order, then the documentation commit
   dated 2026-10-25.

`build/build.py` has git blob `415311386c95f94c5983b6ff99db3663989e5d90`, the same file as `scripts/state-law/nj/build.py` in Lexifina's repository.

## Decisions made by hand

1. **Route.** The official file from the Internet Archive only, because the Legislature's hosts refused connections
   from where this was built. The Archive holds the same file at three addresses (the one asked for, its `pub.njleg.gov`
   alias, and its pre-2022 home on `www.njleg.state.nj.us/Statutes/`); all three were used, which takes the record back
   from 2025 to 2021-09-22.
2. **Dates are capture dates**, at noon UTC, with an `In-force:` trailer carrying that date so the tools work, and every
   message saying it is the date the file was seen, not the date the change took effect.
3. **Credit.** A changed section is credited to a chapter law when its source note gained exactly one citation
   (`<year>, c.<n>`, with or without `L.`/`P.L.` and special-session words) between two captures. Author
   `"P.L.2025, c.35" <nj-2025-35@session-law.invalid>`. Otherwise no law is credited.
4. **Splitting.** A line at the margin that repeats the number of the section just opened, before any text, is the
   section's first line, not a new section. The last paragraph is the source note when it starts like one (`L.`,
   `P.L.`, `amended`, `Repealed`, `Source`, `New`, ...) and cites a chapter law; otherwise it stays in the text.
5. **Lines.** One source line per output line (the file already prints one paragraph per line; tables and forms print
   one row per line), with runs of spaces and tabs made single. Designations (`a.`, `(1)`, `(a)`, `(i)`, `(A)`) become
   list items, nested by the order the styles appear in the section; the act's own section number at the start of the
   first line (`3. General definitions.`) is not a designation. Markdown characters are escaped.
6. **Repeated numbers.** A number printed twice in one file (a few dozen, mostly older acts printed under a number the Revised Statutes also
   use) gets `-2` on its second printing, in file order.
7. **Sections that leave the file** keep a one-line note rather than being deleted.

## What AI models did

This repository was built on 28 October 2026 in **Claude Code**, Anthropic's coding tool, by the model **Claude Opus
5.5** (model id `claude-opus-5-5`), from a brief set by the user at Lexifina: to bring US state law into git in the same
form as the US Code history. The model wrote `build/`, `tools/nj.py` and these documents, ran the commands above, and
chose the route when the Legislature's hosts could not be reached. **No model wrote or edited any statutory text, and no
model is called when the history is built.** Every word comes from the Legislature's file; every date from the Internet
Archive's capture records; every chapter-law credit from the sections' own source notes. The work has not been reviewed
line by line by a lawyer.
