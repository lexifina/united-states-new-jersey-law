"""Builds a git history of the New Jersey Statutes from dated copies of the Legislature's official plain-text file,
STATUTES-TEXT.zip, in the form of Lexifina's US Code and CFR histories.

    python -I scripts/state-law/nj/fetch.py robots && python -I scripts/state-law/nj/fetch.py zips   # cached
    python -I scripts/state-law/nj/build.py check            # parse every capture and check each section word for word
    python -I scripts/state-law/nj/build.py repo <out>       # write the history with git fast-import

The New Jersey Legislature (Office of Legislative Services) rebuilds STATUTES-TEXT.zip every weekday and keeps no past
copies. The Internet Archive has captured it on a few dates. The oldest capture is the baseline; at each later capture,
every section whose text changed is committed, dated by the capture (the day the official file was seen, which is not
the day the change took effect). A change is credited to a chapter law ("P.L.2025, c.123") when the section's source
note gained exactly one; otherwise the commit says how many it gained, or that it gained none.

Reads only the cache written by fetch.py; makes no network requests; the same cache gives the same commit hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import re
import subprocess
import sys
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fetch  # noqa: E402

COMMITTER = ("Lexifina", "state-law@lexifina.com")
CITE = re.compile(r"^((?:\d+[A-Z]?|App\.A):\d+[A-Z]*-\d+[A-Za-z0-9.]*?)\.?(?=\s|$)\s*(.*)$")
TITLE = re.compile(r"^TITLE\s+(\S+)\s+(.*)$")
LAW = re.compile(r"(?<!\d)((?:17|18|19|20)\d\d),\s*(?:(?:First|Second|Third|Fourth|Fifth)\s+Sp\.\s*Sess\.,\s*)?"
                 r"(c\.|J\.\s*R\.|JR)\s*(\d+)")
NOTE = re.compile(r"^(?:P\.\s*L\.|L\.\s*\d|L\.\d|Amended|amended|Repealed|repealed|Source|Deleted|Supplemented|Renumbered|"
                  r"Approved|New\b|\d{4},\s*c\.)")
UPDATED = re.compile(r"UPDATED THROUGH\s+(.*?)\)?\s*$")


# ---- Reading one capture ----

class Section:
    __slots__ = ("cite", "heading", "lines", "note", "title")

    def __init__(self, cite: str, heading: str, title: str):
        self.cite, self.heading, self.title, self.lines, self.note = cite, heading, title, [], ""


def _ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def parse(text: str) -> tuple[list[Section], dict[str, str], str, list]:
    """The sections of STATUTES.TXT in file order, the titles' names, the "updated through" line, and every item of
    the file in order (a Section, or a line of text outside any section) for the word-for-word check."""
    sections: list[Section] = []
    items: list = []
    titles: dict[str, str] = {}
    updated = ""
    title = ""
    cur: Section | None = None
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not sections and cur is None and not updated:
            m = UPDATED.search(raw)
            if m:
                updated = _ws(m.group(1))
            items.append(raw)
            continue
        m = TITLE.match(raw)
        if m and not raw[:1].isspace():
            title = m.group(1)
            titles[title] = _ws(m.group(2))
            cur = None
            items.append(raw)
            continue
        m = CITE.match(raw) if raw[:1] and not raw[:1].isspace() else None
        if m is None and cur is not None and raw[:1].isspace():
            # A few headings are printed indented. One counts when it follows the previous section's source note
            # and names another section.
            m = CITE.match(raw.lstrip())
            if m:
                last = next((_ws(x) for x in reversed(cur.lines) if x.strip()), "")
                if m.group(1) == cur.cite or not (NOTE.match(last) and LAW.search(last)):
                    m = None
        if m:
            cite = m.group(1)
            # A section's first line sometimes repeats its own number at the margin ("12A:9-210.  Request for ...")
            # right under the heading line: that is the start of its text, not a new section.
            if cur is not None and cur.cite == cite and not any(x.strip() for x in cur.lines):
                cur.lines.append(raw)
                continue
            cur = Section(cite, _ws(m.group(2)), title if not cite.startswith("App.") else "App.A")
            sections.append(cur)
            items.append(cur)
            continue
        if cur is not None:
            cur.lines.append(raw)
        else:
            items.append(raw)   # text between a title line and its first section; reported by the check
    for s in sections:
        body = [_ws(x) for x in s.lines]
        body = [x for x in body if x]
        if body and NOTE.match(body[-1]) and LAW.search(body[-1]):
            s.note = body.pop()
        s.lines = body
    return sections, titles, updated, items


def source_check(text: str, items: list) -> list[str]:
    """Rebuild the file's words, in order, from the rendered sections (Markdown taken out) and the lines outside them,
    and compare with every word of the source. Only a section number may differ, by its trailing period."""
    src = text.split()
    got: list[tuple[str, bool]] = []
    loose: list[str] = []
    for it in items:
        if isinstance(it, Section):
            ws = words_of_render(render(it), bool(it.note))
            got += [(w, i == 0) for i, w in enumerate(ws)]
        else:
            got += [(w, False) for w in it.split()]
            if it.strip() and not TITLE.match(it) and "STATUTES" not in it and not UPDATED.search(it):
                loose.append(it.strip()[:80])
    problems = [f"text outside any section: {x}" for x in loose]
    if len(src) != len(got):
        problems.append(f"{len(src)} source words, {len(got)} rendered")
    for i, (a, (b, lenient)) in enumerate(zip(src, got)):
        if a != b and not (lenient and a.rstrip(".") == b.rstrip(".")):
            problems.append(f"word {i}: source {' '.join(src[max(0, i - 5):i + 5])!r} rendered {' '.join(x for x, _ in got[max(0, i - 5):i + 5])!r}")
            break
    return problems


def read_capture(data: bytes) -> tuple[list[Section], dict[str, str], str, str]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        name = next(n for n in z.namelist() if n.upper().endswith(".TXT"))
        info = z.getinfo(name)
        text = z.read(name).decode("cp1252")
    secs, titles, updated, items = parse(text)
    problems = source_check(text, items)
    if problems:
        raise SystemExit("the rendering does not match the source word for word:\n" + "\n".join(problems[:20]))
    stamp = "%04d-%02d-%02d" % info.date_time[:3]
    return secs, titles, updated, stamp


# ---- Rendering ----

_MD = re.compile(r"([\\*_`<\[\]])")
_LABEL = re.compile(r"^(\(([0-9]{1,3}|[a-z]{1,5}|[A-Z]{1,5})\)|([0-9]{1,3}|[a-z]{1,2}|[A-Z]{1,2})\.)(?=\s)\s*(.*)$")
_ROMAN = re.compile(r"^(?=[ivxl]+$)l?x{0,3}(ix|iv|v?i{0,3})$")


def _style(label: str, last: dict[str, str]) -> str:
    inner = label.strip("().")
    paren = label.startswith("(")
    if inner.isdigit():
        return "(1)" if paren else "1."
    if inner.islower():
        prev = last.get("(a)" if paren else "a.", "")
        is_letter = len(inner) == 1 and (inner not in "ivxl" or (len(prev) == 1 and ord(inner) == ord(prev) + 1))
        if len(inner) > 1 and not _ROMAN.match(inner):
            is_letter = True   # (aa), (bb): letters doubled
        if is_letter:
            return "(a)" if paren else "a."
        return "(i)" if paren else "i."
    if inner.isupper():
        prev = last.get("(A)" if paren else "A.", "")
        roman = len(inner) > 1 and bool(_ROMAN.match(inner.lower())) and not (len(set(inner)) == 1 and prev[:1] == inner[:1])
        if inner in ("I", "V", "X") and not (prev and ord(inner) == ord(prev[-1]) + 1):
            roman = True
        return ("(I)" if paren else "I.") if roman else ("(A)" if paren else "A.")
    return "?"


def _escape(line: str) -> str:
    out = _MD.sub(r"\\\1", line)
    if re.match(r"^(\d+)([.)])(\s|$)", out):
        out = re.sub(r"^(\d+)([.)])", r"\1\\\2", out)
    elif out[:1] in "#>+-|=~":
        out = "\\" + out
    return out


def body_lines(sec: Section) -> list[str]:
    """One line per paragraph or table row; a designated provision as "- (a) ...", indented two spaces per level."""
    out: list[str] = []
    stack: list[str] = []
    last: dict[str, str] = {}
    for i, line in enumerate(sec.lines):
        m = _LABEL.match(line)
        # The first line often opens with the section number of the act it came from ("3. General definitions."):
        # that is not a provision.
        if not m or (i == 0 and m.group(3) and m.group(3).isdigit()):
            out.append(_escape(line))
            continue
        label, rest = m.group(1), m.group(4)
        style = _style(label, last)
        last[style] = label.strip("().")
        if style in stack:
            del stack[stack.index(style) + 1:]
        else:
            stack.append(style)
        depth = len(stack) - 1
        shown = re.sub(r"^(\d+)\.$", r"\1\\.", label)   # "- 1. x" would open a numbered list inside the item
        out.append("  " * depth + "- " + shown + (" " + _MD.sub(r"\\\1", rest) if rest else ""))
    return out


def citation(cite: str) -> str:
    return f"N.J.S. {cite}"


def render(sec: Section) -> str:
    head = sec.heading
    lines = [f"# {_MD.sub(r'\\\1', citation(sec.cite))}" + (f". {_MD.sub(r'\\\1', head)}" if head else ""), ""]
    lines += body_lines(sec)
    if sec.note:
        lines += ["", "Source: " + _MD.sub(r"\\\1", sec.note)]
    return "\n".join(lines).rstrip() + "\n"


def words_of_render(md: str, has_note: bool) -> list[str]:
    """The words of a rendered file with the Markdown taken out, to compare with the source."""
    out: list[str] = []
    lines = md.rstrip("\n").split("\n")
    for i, line in enumerate(lines):
        s = line
        if i == 0:
            s = re.sub(r"^# N\.J\.S\. ", "", s)
        s = re.sub(r"^\s*- ", "", s)
        if has_note and i == len(lines) - 1 and s.startswith("Source: "):
            s = s[len("Source: "):]
        s = re.sub(r"\\(.)", r"\1", s)
        out += s.split()
    return out


# ---- Files ----

def folder(sec: Section) -> str:
    return "appendix-A" if sec.cite.startswith("App.") else f"title-{sec.cite.split(':')[0]}"


def keyed(sections: list[Section]) -> dict[str, Section]:
    """path -> section. A number printed twice (a section and an older act saved under the same number) gets -2, -3."""
    out: dict[str, Section] = {}
    seen: dict[str, int] = defaultdict(int)
    for s in sections:
        base = re.sub(r"[^A-Za-z0-9.-]+", "-", s.cite.split(":", 1)[1]).strip("-.")
        stem = f"{folder(s)}/{base}"
        seen[stem.lower()] += 1
        n = seen[stem.lower()]
        out[f"{stem}{'' if n == 1 else f'-{n}'}.md"] = s
    return out


def laws(note: str) -> list[str]:
    seen: list[str] = []
    """The chapter laws ("P.L.2025, c.35") and joint resolutions ("P.L.2021, J.R.9") a source note cites, in order."""
    for y, kind, c in LAW.findall(note):
        k = f"P.L.{y}, {'c.' if kind == 'c.' else 'J.R.'}{int(c)}"
        if k not in seen:
            seen.append(k)
    return seen


# ---- Snapshots ----

def snapshots():
    """(meta, {path: Section}) for each capture, oldest first, one at a time (each capture is checked word for word
    against its source as it is read). Two different files seen on one day: the later one is that day's text."""
    caps = fetch.captures()
    keep = [r for k, r in enumerate(caps) if k + 1 == len(caps) or caps[k + 1]["timestamp"][:8] != r["timestamp"][:8]]
    for r in keep:
        url = fetch.capture_url(r)
        data = fetch.cached(url)
        if data is None:
            sys.exit(f"not fetched yet: {url} (run fetch.py zips)")
        secs, titles, updated, stamp = read_capture(data)
        ts = r["timestamp"]
        meta = {"date": f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}", "ts": ts, "url": url, "original": r["original"],
                "titles": titles, "updated": updated, "stamp": stamp, "bytes": len(data), "sections": len(secs)}
        yield meta, keyed(secs)


# ---- Commands ----

def cmd_check(_: argparse.Namespace) -> None:
    """Every capture is checked word for word as it is read (read_capture); this prints what each one holds."""
    for s, files in snapshots():
        notes = sum(1 for x in files.values() if x.note)
        print(f"{s['date']} {len(files)} sections ({notes} with a source note), {len(s['titles'])} titles, "
              f"updated through {s['updated']!r}, STATUTES.TXT dated {s['stamp']}: word for word OK", flush=True)


def cmd_repo(args: argparse.Namespace) -> None:
    out = Path(args.out).resolve()
    if out.exists() and any(out.iterdir()) and not (out / ".git").exists():
        sys.exit(f"{out} is not empty and is not a git repository; refusing to overwrite it")
    # (date, kind, key) -> {"files": {path: text}, "added": [...], "changed": [...], "removed": [...], "laws": set}
    groups: dict[tuple[str, int, str], dict] = {}

    def group(day: str, kind: int, key: str) -> dict:
        return groups.setdefault((day, kind, key), {"files": {}, "added": [], "changed": [], "removed": [], "laws": set()})

    snaps: list[dict] = []
    prev_text: dict[str, str] = {}     # path -> the file as committed so far (a dropped section's note included)
    prev_laws: dict[str, list] = {}    # path -> the laws in its source note when last printed
    gone: set[str] = set()             # paths whose section has left the file
    for meta, files in snapshots():
        day = meta["date"]
        snaps.append(meta)
        now = {p: render(s) for p, s in files.items()}
        if len(snaps) == 1:
            group(day, 0, "baseline")["files"].update(now)
            prev_text = dict(now)
            prev_laws = {p: laws(s.note) for p, s in files.items()}
            print(f"{day}: baseline, {len(now)} sections", flush=True)
            continue
        changed = 0
        for path in sorted(set(prev_text) | set(now)):
            before, after = prev_text.get(path), now.get(path)
            if after is None:
                if path in gone:
                    continue
                cite = re.sub(r"^# N\.J\.S\. ", "", before.split("\n", 1)[0]).split(" ")[0].rstrip(".")
                cite = re.sub(r"\\(.)", r"\1", cite)
                text = (before.split("\n", 1)[0] + f"\n\nNot in the official text file seen on {day}: repealed, renumbered "
                        "or withdrawn (the file does not say which).\n")
                g = group(day, 3, "removed")
                g["files"][path] = text
                g["removed"].append(cite)
                prev_text[path] = text
                gone.add(path)
                changed += 1
                continue
            if before == after:
                continue
            sec = files[path]
            new_laws = [x for x in laws(sec.note) if x not in prev_laws.get(path, [])]
            kind, key = (1, new_laws[0]) if len(new_laws) == 1 else (2, "several" if new_laws else "none")
            g = group(day, kind, key)
            g["files"][path] = after
            g["added" if before is None or path in gone else "changed"].append(sec.cite)
            g["laws"].update(new_laws)
            gone.discard(path)
            prev_text[path] = after
            prev_laws[path] = laws(sec.note)
            changed += 1
        print(f"{day}: {changed} sections changed", flush=True)
    write(out, snaps, groups)


def _list(cites: list[str], n: int = 3) -> str:
    cites = sorted(cites, key=_order)
    shown = ", ".join(cites[:n])
    return shown + (f" and {len(cites) - n} more" if len(cites) > n else "")


def _order(cite: str) -> list:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", cite)]


def _what(g: dict) -> str:
    parts = []
    if g["changed"]:
        parts.append(f"amends {_list(g['changed'])}")
    if g["added"]:
        parts.append(f"adds {_list(g['added'])}")
    if g["removed"]:
        parts.append(f"drops {_list(g['removed'])}")
    return "; ".join(parts)


def write(out: Path, snaps: list[dict], groups: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    if not (out / ".git").exists():
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=out, check=True)
    fi = subprocess.Popen(["git", "fast-import", "--quiet", "--done", "--force"], cwd=out, stdin=subprocess.PIPE)
    w = fi.stdin
    mark = [0]
    by_date = {s["date"]: s for s in snaps}

    def blob(b: bytes) -> None:
        w.write(b"data %d\n" % len(b)); w.write(b); w.write(b"\n")

    def epoch(day: str) -> int:
        return int((datetime.strptime(day, "%Y-%m-%d") - datetime(1970, 1, 1)).total_seconds()) + 12 * 3600

    def commit(author: tuple[str, str], day: str, message: str, files: dict[str, str | None]) -> None:
        mark[0] += 1
        w.write(f"commit refs/heads/main\nmark :{mark[0]}\nauthor {author[0]} <{author[1]}> {epoch(day)} +0000\n"
                f"committer {COMMITTER[0]} <{COMMITTER[1]}> {epoch(day)} +0000\n".encode())
        blob(message.encode("utf-8"))
        if mark[0] > 1:
            w.write(f"from :{mark[0] - 1}\n".encode())
        for path in sorted(files):
            if files[path] is None:
                w.write(f"D {path}\n".encode())
            else:
                w.write(f"M 100644 inline {path}\n".encode()); blob(files[path].encode("utf-8"))
        w.write(b"\n")

    seen_note = ("Dated by the Internet Archive's capture of the official file: the day the text was seen, "
                 "not the day the change took effect.")
    counts = defaultdict(int)
    for (day, kind, key) in sorted(groups, key=lambda k: (k[0], k[1], _order(k[2]))):
        g = groups[(day, kind, key)]
        s = by_date[day]
        src = f"Source: {s['url']}"
        counts[kind] += 1
        if kind == 0:
            commit((f"New Jersey Statutes, official text file of {day}", f"edition-{day}@nj-statutes.invalid"), day,
                   f"New Jersey Statutes as in the official text file seen on {day} (updated through {s['updated']})\n\n"
                   f"{len(g['files'])} sections. {seen_note} The file itself is dated {s['stamp']} and says it is "
                   f"updated through {s['updated']}.\n\nIn-force: {day}\nConsolidated: {day}\n"
                   f"Printed-in: STATUTES-TEXT.zip (STATUTES.TXT dated {s['stamp']}), updated through {s['updated']}\n{src}\n", g["files"])
        elif kind == 1:
            law = key
            y, jr, c = re.match(r"P\.L\.(\d+), (c\.|J\.R\.)(\d+)", law).groups()
            commit((law, f"nj-{y}-{'jr' if jr == 'J.R.' else ''}{c}@session-law.invalid"), day,
                   f"{law} {_what(g)}\n\n{seen_note}\n\nIn-force: {day}\nLaw: {law}\n{src}\n", g["files"])
        elif kind == 2:
            if key == "several":
                ls = sorted(g["laws"], key=_order)
                body = ("Each section here gained more than one chapter law in its source note between two captures, so "
                        "no single law is credited. Laws named: " + ", ".join(ls) + ".")
                subj = "Several chapter laws " + re.sub(r"\b(amend|add|drop)s\b", r"\1", _what(g))
                author = ("Several chapter laws", "nj-several@session-law.invalid")
            else:
                body = "The source notes of these sections name no new chapter law (a correction or an editorial change)."
                subj = f"Changes with no new law named: {_what(g)}"
                author = ("New Jersey Statutes, no law named", "nj-unnamed@nj-statutes.invalid")
            commit(author, day, f"{subj}\n\n{body}\n{seen_note}\n\nIn-force: {day}\n{src}\n", g["files"])
        else:
            commit(("New Jersey Statutes, sections dropped", "nj-dropped@nj-statutes.invalid"), day,
                   f"Sections no longer in the official file: {_list(g['removed'])}\n\nThe official text file seen on {day} "
                   f"no longer prints these sections; it does not say whether they were repealed or renumbered. Each "
                   f"keeps a one-line note.\n{seen_note}\n\nIn-force: {day}\n{src}\n", g["files"])
    w.write(b"done\n"); w.close(); fi.wait()
    last = subprocess.run(["git", "rev-parse", "main"], cwd=out, capture_output=True, text=True).stdout.strip()

    from docs import CHANGES, LICENSE, corpus, readme, reproduce

    files_now = subprocess.run(["git", "ls-tree", "-r", "--name-only", "main"], cwd=out, capture_output=True, text=True).stdout.split()
    emails = subprocess.run(["git", "log", "--format=%ae", "main"], cwd=out, capture_output=True, text=True).stdout.split()
    for url in fetch.CHECKS:
        fetch.cached(url)   # list the robots.txt checks in the manifest too (those that answered)
    manifest = "".join(f"{h}  {u}\n" for u, h in sorted(fetch.READ.items()))
    record_to = snaps[-1]["date"]
    info = {
        "sections": len(files_now), "titles": len({f.split("/")[0] for f in files_now}),
        "in_force_now": snaps[-1]["sections"], "record_to": record_to, "history_from": snaps[0]["date"],
        "commits": len(emails) + 1, "law_commits": sum(1 for e in emails if re.match(r"nj-\d", e)),
        "several_commits": sum(1 for e in emails if e.startswith("nj-several")),
        "unnamed_commits": sum(1 for e in emails if e.startswith("nj-unnamed")),
        "dropped_commits": sum(1 for e in emails if e.startswith("nj-dropped")),
        "snaps": [(s["date"], s["ts"], s["original"], s["url"], s["stamp"], s["updated"], s["sections"], s["bytes"]) for s in snaps],
        "requests": len(fetch.READ), "bytes": sum(s["bytes"] for s in snaps),
        "data_sha256": hashlib.sha256(manifest.encode()).hexdigest(), "last": last, "python": sys.version.split()[0],
        "git": subprocess.run(["git", "--version"], capture_output=True, text=True).stdout.split()[-1],
        "blob": subprocess.run(["git", "hash-object", str(Path(__file__).resolve())], capture_output=True, text=True).stdout.strip(),
    }
    fi = subprocess.Popen(["git", "fast-import", "--quiet", "--done", "--force"], cwd=out, stdin=subprocess.PIPE)
    w = fi.stdin
    docs = {
        "README.md": readme(info), "REPRODUCE.md": reproduce(info), "CHANGES.md": CHANGES, "LICENSE.md": LICENSE,
        "corpus.json": corpus(info), "tools/nj.py": (HERE / "tool.py").read_text(encoding="utf-8"),
        "build/build.py": Path(__file__).read_text(encoding="utf-8"), "build/fetch.py": (HERE / "fetch.py").read_text(encoding="utf-8"),
        "build/docs.py": (HERE / "docs.py").read_text(encoding="utf-8"), "build/tool.py": (HERE / "tool.py").read_text(encoding="utf-8"),
        "build/DATA-SHA256SUMS": manifest,
    }
    w.write(f"commit refs/heads/main\nmark :1\nauthor {COMMITTER[0]} <{COMMITTER[1]}> {epoch(record_to)} +0000\n"
            f"committer {COMMITTER[0]} <{COMMITTER[1]}> {epoch(record_to)} +0000\n".encode())
    blob(b"Documentation, the tool, and the build with the checksums of its data\n")
    w.write(f"from {last}\n".encode())
    for path in sorted(docs):
        w.write(f"M 100644 inline {path}\n".encode()); blob(docs[path].replace("\r\n", "\n").encode("utf-8"))
    w.write(b"\ndone\n"); w.close(); fi.wait()
    subprocess.run(["git", "checkout", "-q", "-f", "main"], cwd=out, check=True)
    count = subprocess.run(["git", "rev-list", "--count", "main"], cwd=out, capture_output=True, text=True).stdout.strip()
    print(f"{count} commits ({dict(counts)}), {snaps[0]['date']} to {record_to} -> {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    r = sub.add_parser("repo"); r.add_argument("out")
    a = ap.parse_args()
    {"check": cmd_check, "repo": cmd_repo}[a.cmd](a)


if __name__ == "__main__":
    main()
