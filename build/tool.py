#!/usr/bin/env python3
"""Read the New Jersey Statutes history by date. Needs Python 3.8 or later and git; run it inside the repository.

  python tools/nj.py on 2026-01-01 title-2A/4A-22.md          the text in the official file as of a date
  python tools/nj.py diff 2025-08-08 2026-10-25 title-2A/4A-22.md [--words]
  python tools/nj.py log title-2A/4A-22.md                    every change to a section, with its dates
  python tools/nj.py law "P.L.2025, c.35"                     every change credited to one chapter law

A commit's date is its In-force: trailer. In this history that is the day the Internet Archive captured the official
text file (STATUTES-TEXT.zip), so "on DATE" means "as printed in the last official file seen on or before DATE", not
"in force on DATE". The text on a date is the file in the last commit dated on or before it, so the answer does not
depend on your time zone or the time of day.
"""
import re
import subprocess
import sys


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", check=True).stdout


def history():
    fmt = "%H%x1f%ad%x1f%an%x1f%s%x1f%(trailers:key=In-force,valueonly,separator=%x2c)%x1e"
    out = []
    for rec in git("log", "--reverse", "--date=short", "--format=" + fmt, "HEAD").split("\x1e"):
        rec = rec.strip("\n")
        if rec:
            commit, authored, author, subject, in_force = rec.split("\x1f")
            out.append(((in_force.strip().split(",")[0] or authored), commit, author, subject))
    return out


def day(text):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        sys.exit("Dates are written YYYY-MM-DD, not %r." % text)
    return text


def commit_on(date):
    hist = history()
    chosen = [h for h in hist if h[0] <= date]
    if not chosen:
        sys.exit("%s is before this history starts (%s)." % (date, hist[0][0]))
    return chosen[-1]


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[1]
    if cmd == "on" and len(argv) == 4:
        try:
            sys.stdout.write(git("show", "%s:%s" % (commit_on(day(argv[2]))[1], argv[3])))
            return 0
        except subprocess.CalledProcessError:
            print("%s was not in the New Jersey Statutes file as of %s." % (argv[3], argv[2]))
            return 1
    if cmd == "log" and len(argv) == 3:
        dates = {h[1]: h[0] for h in history()}
        for line in git("log", "--reverse", "--format=%H%x1f%an%x1f%s", "--", argv[2]).splitlines():
            commit, author, subject = line.split("\x1f")
            print("%s  %s  %s\n            %s" % (dates.get(commit, "?"), commit[:10], author, subject))
        return 0
    if cmd == "diff" and len(argv) in (5, 6):
        a, b = commit_on(day(argv[2]))[1], commit_on(day(argv[3]))[1]
        sys.stdout.write(git("diff", *(["--word-diff"] if argv[-1] == "--words" else []), a, b, "--", argv[4]))
        return 0
    if cmd == "law" and len(argv) == 3:
        name = re.sub(r"\s+", "", argv[2]).replace("c.", ", c.").replace(",,", ",")
        sys.stdout.write(git("log", "--stat", "--format=%n%ad  %s", "--date=short", "--grep=^Law: " + re.escape(name) + "$"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
