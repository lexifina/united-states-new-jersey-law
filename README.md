# Git for the New Jersey Statutes

The New Jersey Statutes, section by section, as printed in the Legislature's official plain-text file
(`STATUTES-TEXT.zip`) on each day a copy of that file was archived, from 2021-09-22 to 2026-10-25. The
first copy is the starting point; each later copy adds a commit for every section that changed, **credited to the
chapter law ("P.L.2025, c.35") the section's source note gained** where it gained exactly one.

**Dates here are the days the official file was seen, not the days the changes took effect.** The Legislature rebuilds
the file every weekday and keeps no past copies; the Internet Archive captured it on 10 days. A change
committed on a capture date was made by a law enacted at some point since the capture before.

| The question | The command |
| --- | --- |
| What did N.J.S. 2A:4A-22 say in the official file as of 1 January 2026? | `python tools/nj.py on 2026-01-01 title-2A/4A-22.md` |
| Which law last changed each provision (within this record)? | `git blame title-2A/4A-22.md` |
| What changed between two dates? | `python tools/nj.py diff 2021-09-22 2026-10-25 title-2A/4A-22.md --words` |
| Everything one chapter law changed | `python tools/nj.py law "P.L.2025, c.35"` |
| Every change to a section, with its dates | `python tools/nj.py log title-2A/4A-22.md` |
| The most changed sections of a title | `git log --format= --name-only -- title-2C \| sort \| uniq -c \| sort -rn \| head` |

`tools/nj.py` needs only Python 3 and git, and picks the text by each commit's `In-force:` trailer (here, the capture
date), so the answer does not depend on your time zone or the time of day.

## What is here

56,605 section files in 69 folders (56,339 sections in the newest file; the
rest are sections that dropped out of the file during the record and keep a one-line note). There are 1146
commits: one starting point, 1125 credited to a single chapter law, 6 for sections
that gained several laws between two captures, 7 for changes whose source note names no new law,
6 for sections that left the file, and the documentation.

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
- **Text between captures.** Between 2021-12-15 and 2025-08-08 there is no archived copy at all, so
  several years of amendments arrive in one commit per law on 2025-08-08; where a section was amended more than
  once in a gap, only the text after the last amendment is shown.
- **Anything before 2021-09-22.** The source notes list every law back to 1937 or enactment, but the text
  they made is not here.
- **Future changes.** Laws enacted but not yet printed in the file of 2026-10-25 are not here.
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
