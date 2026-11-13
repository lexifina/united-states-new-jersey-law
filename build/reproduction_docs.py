"""The documentation files of the New Jersey Statutes git history, filled in by build.py with the figures of each build."""

from __future__ import annotations

import json

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
read. [REPRODUCE.md](REPRODUCE.md) records source observations, the historical access record and reproduction instructions;
[CHANGES.md](CHANGES.md) records how the history changes.

Lexifina keeps the US Code and the CFR in the same form; all are part of
[lexifina/global-law](https://github.com/lexifina/global-law). Built by [Lexifina](https://lexifina.com). For
corrections, open an issue.

## License

New Jersey claims no copyright in its statutes. The history, commit messages, tools and documentation are © Lexifina
under [CC BY 4.0](LICENSE.md).
"""


def reproduce(i: dict) -> str:
    return """# Reproducing the New Jersey snapshots

The official Legislature ZIP responses and their exact source URLs are pinned
in `build/DATA-SHA256SUMS`. Supply the original response bodies in the directory
named by NJ_SOURCE_CACHE; name each by its response SHA-256, URL SHA-256, or URL
SHA-256 plus .gz for a gzip-compressed response. All checksums refer to
uncompressed bytes. The reader makes no network requests.

    python -X utf8 -I build/source.py verify
    python -X utf8 -I build/reproduce.py check
    python -X utf8 -I build/reproduce.py repo ./rebuilt

Verification fails when any recorded response is missing or has a wrong checksum.
The builder compares every rendered word with the official plain-text file,
allowing Markdown formatting and a section number's trailing period. Rebuild
only into an empty directory; existing histories are refused. Dates are source
observations, not effective dates. Credits come from the source's chapter-law
notes. No model generates or corrects statutory wording during the build.

The rich-text member's normative image content is not independently inventoried.
The source-response reader was added on 13 November 2026; the original builder
was authored on 28 October 2026. Later documentation and date overlays in the
published repository are outside the original snapshot reconstruction.

| Date seen | Address captured | STATUTES.TXT dated | Updated through | Sections | ZIP bytes |
| --- | --- | --- | --- | ---: | ---: |
""" + _snap_rows(i) + "\n\n" + HISTORICAL_ROBOTS + "\n"


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


HISTORICAL_ROBOTS = "## Historical robots.txt record - 28 October 2026\n\n- **pub.njleg.state.nj.us** (the official file's host) and **www.njleg.state.nj.us**: not reachable from where this\n  was built (connections timed out, from a non-US address), so the live file was not used and the Archive's copies were\n  used instead. The Internet Archive's newest copy of `https://pub.njleg.state.nj.us/robots.txt` (19 January 2026) is a\n  redirect to the main site's robots.txt. The newest archived main-site copy (9 May 2026) allowed `/` for the wildcard\n  crawler group `*`, then listed the host and two sitemap URLs. No archived robots.txt exists for pub.njleg.gov.\n  Nothing disallows the statutes files.\n- **web.archive.org**: `/robots.txt` answers 404 (no rules).\n\nThis is the original build's recorded account, preserved from published main; it was not independently refreshed during this tooling repair.\n"
