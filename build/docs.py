"""The documentation files of the New Jersey Statutes git history, filled in by build.py with the figures of each build."""

from __future__ import annotations

import json

ROBOTS_WWW = """User-agent: *
Allow: /

# Host
Host: https://www.njleg.state.nj.us

# Sitemaps
Sitemap: https://www.njleg.state.nj.us/sitemaps/sitemap.xml
Sitemap: https://www.njleg.state.nj.us/sitemaps/bills-sitemap.xml"""


def _snap_rows(i: dict) -> str:
    rows = []
    for date, ts, original, url, stamp, updated, n, size in i["snaps"]:
        rows.append(f"| {date} | `{original}` | {stamp} | {updated} | {n:,} | {size:,} |")
    return "\n".join(rows)


def readme(i: dict) -> str:
    ex = "title-2A/4A-22.md"
    return f"""# Git for the New Jersey Statutes

The New Jersey Statutes, section by section, as printed in the Legislature's official plain-text file
(`STATUTES-TEXT.zip`) on each day a copy of that file was archived, from {i['history_from']} to {i['record_to']}. The
first copy is the starting point; each later copy adds a commit for every section that changed, **credited to the
chapter law ("P.L.2025, c.35") the section's source note gained** where it gained exactly one.

**Dates here are the days the official file was seen, not the days the changes took effect.** The Legislature rebuilds
the file every weekday and keeps no past copies; the Internet Archive captured it on {len(i['snaps'])} days. A change
committed on a capture date was made by a law enacted at some point since the capture before.

| The question | The command |
| --- | --- |
| What did N.J.S. 2A:4A-22 say in the official file as of 1 January 2026? | `python tools/nj.py on 2026-01-01 {ex}` |
| Which law last changed each provision (within this record)? | `git blame {ex}` |
| What changed between two dates? | `python tools/nj.py diff {i['history_from']} {i['record_to']} {ex} --words` |
| Everything one chapter law changed | `python tools/nj.py law "P.L.2025, c.35"` |
| Every change to a section, with its dates | `python tools/nj.py log {ex}` |
| The most changed sections of a title | `git log --format= --name-only -- title-2C \\| sort \\| uniq -c \\| sort -rn \\| head` |

`tools/nj.py` needs only Python 3 and git, and picks the text by each commit's `In-force:` trailer (here, the capture
date), so the answer does not depend on your time zone or the time of day.

## What is here

{i['sections']:,} section files in {i['titles']} folders ({i['in_force_now']:,} sections in the newest file; the
rest are sections that dropped out of the file during the record and keep a one-line note). There are {i['commits']}
commits: one starting point, {i['law_commits']} credited to a single chapter law, {i['several_commits']} for sections
that gained several laws between two captures, {i['unnamed_commits']} for changes whose source note names no new law,
{i['dropped_commits']} for sections that left the file, and the documentation.

Each section is one Markdown file, `title-<title>/<section>.md` (for N.J.S. 2A:4A-22, `title-2A/4A-22.md`; the
Appendix A acts are in `appendix-A/`). The first line is `# N.J.S. <number>. <heading>`; then one paragraph or
designated provision per line (`- a.`, `  - (1)`, `    - (a)`, two spaces per level), so `git blame` names a commit for
each provision; the last line is the section's source note as printed (`Source: L.1982, c.77, s.3; amended ...`).
A number the file prints twice (an act saved under a number the Revised Statutes also use) gets `-2`.

## How a change is dated and credited

- **Dated by the capture.** Each commit is dated (noon UTC) the day the Internet Archive fetched the official file.
  The file was built up to a day earlier (the date of `STATUTES.TXT` inside the zip, given in the starting commit).
- **Credited by the source note.** Between two captures, a section whose text changed is credited to the chapter law
  its source note gained, when it gained exactly one (`Law:` trailer, and the commit author). When it gained several,
  the commit lists them and credits none. When it gained none, the change is shown as one with no law named (often a
  correction or a change made by a law whose note was not updated).
- **Sections that left the file.** The file says nothing about them; the section keeps a one-line note saying when it
  was last seen missing.

## What it does not show

- **In-force dates.** A chapter law's effective date is in the law itself (often "takes effect immediately" or a set
  number of days after enactment). This history only knows when the official file first printed the change.
- **Text between captures.** Between {i['snaps'][1][0]} and {i['snaps'][2][0]} there is no archived copy at all, so
  several years of amendments arrive in one commit per law on {i['snaps'][2][0]}; where a section was amended more than
  once in a gap, only the text after the last amendment is shown.
- **Anything before {i['history_from']}.** The source notes list every law back to 1937 or enactment, but the text
  they made is not here.
- **Future changes.** Laws enacted but not yet printed in the file of {i['record_to']} are not here.
- **Official status.** The New Jersey Legislature publishes this file; for anything that matters, read the chapter laws
  and the current statute on njleg.gov.

## How it is built

From the Internet Archive's copies of `STATUTES-TEXT.zip` (the live file could not be reached from where this was
built), read only from a local cache, checked word for word against the source file, and written with `git fast-import`,
so the same responses give the same commits. The build is in [`build/`](build/), with the checksums of every response it
read. [REPRODUCE.md](REPRODUCE.md) records the sources, the robots.txt check, the commands and what AI models did;
[CHANGES.md](CHANGES.md) records how the history changes.

Lexifina keeps the US Code and the CFR in the same form; all are part of
[lexifina/global-law](https://github.com/lexifina/global-law). Built by [Lexifina](https://lexifina.com). For
corrections, open an issue.

## License

New Jersey claims no copyright in its statutes. The history, commit messages, tools and documentation are © Lexifina
under [CC BY 4.0](LICENSE.md).
"""


def reproduce(i: dict) -> str:
    return f"""# How this history was made, and how to make it again

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
by decompressing each and hashing it). sha256 of that list: `{i['data_sha256']}`. The last change commit is
`{i['last']}`.

## Sources

| What | Where | Requests |
| --- | --- | ---: |
| The Internet Archive's lists of its captures of the official file, at its three addresses | `http://web.archive.org/cdx/search/cdx?url=<address>&output=json` for `pub.njleg.state.nj.us/statutes/STATUTES-TEXT.zip`, its alias `pub.njleg.gov/statutes/STATUTES-TEXT.zip` and its earlier home `njleg.state.nj.us/statutes/STATUTES-TEXT.zip` | 3 |
| Each distinct capture (by the Archive's content digest), unmodified | `http://web.archive.org/web/<timestamp>id_/<address>` | {len(i['snaps'])} |
| robots.txt checks (see below), and one more address searched for copies (`njleg.gov/statutes/`, none) | `web.archive.org/robots.txt`, the archived robots.txt files and their capture lists | {i['requests'] - 3 - len(i['snaps'])} |
| The live robots.txt of the official host | `https://pub.njleg.state.nj.us/robots.txt` | 0 answered (timed out) |

{i['requests']} responses were received and cached in all ({i['bytes']:,} bytes of zip files), each listed in
`build/DATA-SHA256SUMS`. The captures used:

| Date seen (commit date) | Address captured | STATUTES.TXT dated | File says "updated through" | Sections | Zip bytes |
| --- | --- | --- | --- | ---: | ---: |
{_snap_rows(i)}

Each zip holds `STATUTES.TXT` (plain text, used here) and `STATUTES.RTF` (the same text as rich text, not used). Two
different files captured on one day would keep only the later one; the earliest capture of identical content is used.
Captures whose content is identical to the one before give no commits.

## robots.txt, checked 28 October 2026

- **pub.njleg.state.nj.us** (the official file's host) and **www.njleg.state.nj.us**: not reachable from where this
  was built (connections timed out, from a non-US address), so the live file was not used and the Archive's copies were
  used instead. The Internet Archive's newest copy of `https://pub.njleg.state.nj.us/robots.txt` (19 January 2026) is a
  redirect to the main site's robots.txt, whose newest archived copy (9 May 2026) reads:

  ```
{chr(10).join('  ' + l for l in ROBOTS_WWW.splitlines())}
  ```

  No archived robots.txt exists for pub.njleg.gov. Nothing disallows the statutes files.
- **web.archive.org**: `/robots.txt` answers 404 (no rules).

Requests went one at a time, at least 5 seconds apart, with the user agent
`Mozilla/5.0 (compatible; Lexifina state law history; +https://lexifina.com/watch)`; 429 and 5xx answers would have
been retried with backoff honouring Retry-After (none came). While the first fetch ran, a few one-off capture-list
queries were sent by hand, so for about a minute two requests to web.archive.org were in flight at once. Every response
is cached on disk and never fetched twice.

## The build, step by step

1. `python -I fetch.py robots`, `python -I fetch.py zips` (Python {i['python']}, standard library only).
2. `python -I build.py repo <out>` reads each capture, splits `STATUTES.TXT` into sections at each line that starts at the
   margin with a section number (`2A:4A-22`, `App.A:11-4`), and checks the result word for word: the words of every
   rendered section, with the Markdown taken out, and of the lines outside sections (the file's header and the title
   lines) must equal, in order, every word of the source file. Then it writes the history with `git fast-import`
   (git {i['git']}): the oldest capture, then each later capture's changes in date order, then the documentation commit
   dated {i['record_to']}.

`build/build.py` has git blob `{i['blob']}`, the same file as `scripts/state-law/nj/build.py` in Lexifina's repository.

## Decisions made by hand

1. **Route.** The official file from the Internet Archive only, because the Legislature's hosts refused connections
   from where this was built. The Archive holds the same file at three addresses (the one asked for, its `pub.njleg.gov`
   alias, and its pre-2022 home on `www.njleg.state.nj.us/Statutes/`); all three were used, which takes the record back
   from 2025 to {i['history_from']}.
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
"""


CHANGES = """# Changes and updates

Newest first. Lexifina's global-law repository keeps the log for every corpus (`CHANGELOG.md` there).

## 28 October 2026

First build: every section of the New Jersey Statutes from the official STATUTES-TEXT.zip, as archived by the
Internet Archive on ten days between September 2021 and October 2026, one commit per chapter law per capture date.
"""

LICENSE = """# License

The text of the New Jersey Statutes in the `title-*` and `appendix-A` folders is published by the New Jersey
Legislature (Office of Legislative Services). The State claims no copyright in its statutes or its chapter laws (as
recorded by the American Association of Law Libraries' survey of state online legal information; no claim appears with
the file), and under Georgia v. Public.Resource.Org, Inc., 590 U.S. 255 (2020), the text of the law is not subject to
copyright.

The arrangement of the history (which commits exist, their dates and authors), the commit messages, the tools and the
documentation are © Lexifina, released under the Creative Commons Attribution 4.0 International License (CC BY 4.0):
https://creativecommons.org/licenses/by/4.0/
"""


def corpus(i: dict) -> str:
    return json.dumps({
        "corpus": "us/new-jersey/statutes", "code": "NJ", "name": "New Jersey Statutes", "label": "New Jersey statutes",
        "language": "en", "history_from": i["history_from"], "record_to": i["record_to"],
        "record_note": (f"The official STATUTES-TEXT.zip as archived by the Internet Archive on {len(i['snaps'])} days from "
                        f"{i['history_from']} to {i['record_to']}; commits are dated by capture, not by effective date."),
        "in_force_trailer": "In-force", "baseline_trailer": "Consolidated", "has_future_branch": False,
        "author": "the chapter law the section's source note gained (Law trailer), when exactly one",
        "granularity": "capture date of the official file; one commit per chapter law per capture",
        "scope": {
            "when_absent": "the file records no case-by-case scope; a law's effective date and application are in the chapter law",
            "default_reach": {"rule": "presumption against retroactivity: statutes apply prospectively unless the Legislature clearly says otherwise",
                              "authority": "Gibbons v. Gibbons, 86 N.J. 515 (1981)", "decided_here": False},
        },
        "tool": "tools/nj.py",
    }, indent=2) + "\n"
