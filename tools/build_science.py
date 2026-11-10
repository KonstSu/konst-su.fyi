#!/usr/bin/env python3
"""
Build the "Science & Space" section of the site (science/*.html) and the
teaser on the home page.

Sources, written in Russian and maintained by their own agents (read only):
    ../space-explorer/    missions/*.md, calendar.md, launches.md
    ../science-explorer/  facilities/*.md, calendar.md, results/*.md

English layer, kept in this repository:
    content/missions/<id>.md     translated mission card
    content/facilities/<id>.md   translated facility card
    content/results.md           notable results
    content/launches.md          upcoming deep-space launches
    content/method.md            how the section is made
    data/calendar.json           calendar translations, exclusions, extra links
    data/private.json            local only, git-ignored: exclusion rules that name
                                 non-public information (required to build)

Each content file records a hash of the Russian source it was translated from.
When the source changes, the site keeps showing the previous English text with
its own "checked" date, and --check lists the file as stale until the English
has been updated and re-stamped. A card without an English file is not
published. Calendar rows without a translation are left out (see
data/calendar.json).

    python3 tools/build_science.py                     # build
    python3 tools/build_science.py --check             # report only; exit 1 if anything needs work
    python3 tools/build_science.py --stamp hera,juno   # mark these translations as up to date
    python3 tools/build_science.py --stamp all
    python3 tools/build_science.py --today 2026-12-01  # build as if it were that day
    python3 tools/build_science.py --space PATH --science PATH   # sources elsewhere

If either source repository is missing, the script stops with exit code 2 and
leaves science/ untouched.

Standard library only; no network access.
"""
from __future__ import annotations

import argparse
import calendar as cal
import hashlib
import html
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
OUT = ROOT / "science"
CONFIG = ROOT / "data" / "calendar.json"
PRIVATE = ROOT / "data" / "private.json"   # local only, never committed
HOME = ROOT / "index.html"

HOME_FACILITY = "european-xfel"          # where Konstantin works
PLURAL = {"mission": "missions", "facility": "facilities"}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

REGIONS = [  # inner to outer solar system
    ("sun", "Sun"), ("mercury", "Mercury"), ("venus", "Venus"), ("moon", "Moon"),
    ("mars", "Mars"), ("small-bodies", "Asteroids & comets"), ("jupiter", "Jupiter"),
    ("saturn", "Saturn"), ("outer", "Kuiper belt & beyond"),
]
REGION = dict(REGIONS)

MISSION_STATUS = {
    "upcoming": ("Awaiting launch", "way"),
    "cruise": ("Cruise", "way"),
    "approach": ("Arriving", "way"),
    "active": ("At target", "go"),
    "extended": ("Extended mission", "go"),
    "uncertain": ("Status unclear", "warn"),
    "ended": ("Ended", "end"),
    "lost": ("Lost", "end"),
}
MISSION_GROUPS = [  # filter groups: (key, label, statuses)
    ("flying", "On the way", {"upcoming", "cruise", "approach"}),
    ("target", "At target", {"active", "extended"}),
    ("unclear", "Unclear", {"uncertain"}),
    ("ended", "Ended", {"ended", "lost"}),
]

DOMAINS = [
    ("xfel", "X-ray lasers"), ("synchrotron", "Synchrotrons"), ("gw", "Gravitational waves"), ("neutrino", "Neutrinos"),
    ("astro", "Telescopes"), ("neutron", "Neutrons"), ("particle", "Particle physics"),
    ("fusion", "Fusion"),
]
DOMAIN = dict(DOMAINS)
RESULT_DOMAINS = {**DOMAIN, "detectors": "Detectors", "space": "Space science",
                  "laser": "Laser physics", "other": "Other"}

FACILITY_STATUS = {
    "planned": ("Planned", "way"),
    "construction": ("Under construction", "way"),
    "commissioning": ("Commissioning", "way"),
    "operating": ("Operating", "go"),
    "upgrade": ("Upgrade", "warn"),
    "shutdown": ("Long shutdown", "warn"),
    "ended": ("Data taking ended", "end"),
}
FACILITY_GROUPS = [
    ("planned", "Planned", {"planned"}),
    ("building", "Being built", {"construction", "commissioning"}),
    ("running", "Running", {"operating"}),
    ("paused", "Upgrade or shutdown", {"upgrade", "shutdown"}),
    ("ended", "Ended", {"ended"}),
]

KEYDATE_STATUS = {"done": "done", "planned": "planned", "expected": "expected",
                  "ongoing": "ongoing", "failed": "failed", "event": "event"}

SUBNAV = [
    ("index", "Overview"), ("missions", "Missions"), ("facilities", "Facilities"),
    ("calendar", "Calendar"), ("results", "Results"), ("launches", "Launches"),
    ("method", "Method"),
]

CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
       "font-src 'self'; connect-src https://api.web3forms.com; "
       "form-action https://api.web3forms.com https://web3forms.com; base-uri 'self'; "
       "object-src 'none'; upgrade-insecure-requests")

LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
INTERNAL_REF_RE = re.compile(
    r"\s*(?:\(\s*\[[^\]]+\]\((?:phd|results|digests)/[^)]*\)\s*\)"
    r"|[—–-]\s*\[[^\]]+\]\((?:phd|results|digests)/[^)]*\))")
DATE_RE = re.compile(
    r"""^(?P<approx>≈\s*)?
        (?P<y>\d{4})(?:-(?P<m>\d{2})(?:-(?P<d>\d{2}))?)?
        (?:/(?P<r>\d{2,4}(?:-\d{2})?))?
        (?:\s+(?P<tapprox>≈)?(?P<time>\d{1,2}:\d{2}))?
        (?:\s*\((?P<q>[^)]*)\))?\s*$""", re.X)


# ================================================================ helpers

def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def strip_md(s: str) -> str:
    s = LINK_RE.sub(r"\1", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    return norm(s.replace("`", ""))


def rel(path: str, depth: int) -> str:
    return "../" * depth + path


def fmt_day(d: date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def fmt_iso(s: str) -> str:
    try:
        return fmt_day(date.fromisoformat(s))
    except (TypeError, ValueError):
        return s or "unknown"


def split_doc(text: str) -> tuple[dict[str, str], str]:
    """YAML-like front matter (flat key: value) and the body."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    meta = {}
    for line in text[3:end].split("\n"):
        if ":" in line and not line.lstrip().startswith("#"):
            k, v = line.split(":", 1)
            v = re.sub(r"\s{2,}#.*$", "", v).strip().strip('"')
            meta[k.strip()] = v
    return meta, text[end + 4:].lstrip("\n")


def sections(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    head = None
    buf: list[str] = []
    for line in body.split("\n"):
        if line.startswith("## "):
            if head is not None:
                out[head] = "\n".join(buf).strip()
            head, buf = line[3:].strip(), []
        elif head is not None:
            buf.append(line)
    if head is not None:
        out[head] = "\n".join(buf).strip()
    return out


def table_rows(body: str, keep_header: bool = False) -> list[list[str]]:
    rows = []
    for line in body.split("\n"):
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            continue
        rows.append(cells)
    return rows if keep_header else rows[1:]


def updated_on(md: str) -> str:
    m = re.search(r"Обновлено:\s*(\d{4}-\d{2}-\d{2})", md)
    return m.group(1) if m else ""


def source_hash(path: Path) -> str:
    """Hash of a source file, ignoring the 'last checked' / 'updated' stamps."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^last_checked:.*\n", "", text)
    text = re.sub(r"_Обновлено:[^_]*_", "", text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def source_checked(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    meta, _ = split_doc(text)
    return meta.get("last_checked") or updated_on(text)


def write_stamp(path: Path, h: str, checked: str) -> None:
    text = path.read_text(encoding="utf-8")
    end = text.find("\n---", 3)
    head, rest = text[:end], text[end:]
    for key, val in (("source_hash", h), ("checked", checked)):
        pat = re.compile(rf"(?m)^{key}:.*$")
        if pat.search(head):
            head = pat.sub(f"{key}: {val}", head, count=1)
        else:
            head += f"\n{key}: {val}"
    path.write_text(head + rest, encoding="utf-8")


# ================================================================ dates

@dataclass
class When:
    start: date
    end: date
    text: str          # English display
    iso: str           # for <time datetime>
    precision: str     # day | month | year


def parse_when(raw: str, tr=lambda s: s) -> When | None:
    m = DATE_RE.match(norm(raw))
    if not m:
        return None
    y = int(m["y"])
    mo = int(m["m"]) if m["m"] else None
    d = int(m["d"]) if m["d"] else None
    r = m["r"]

    if d:
        start = end = date(y, mo, d)
        if r:
            if "-" in r:                       # 2026-10-12/12-12
                em, ed = (int(x) for x in r.split("-"))
                end = date(y if em >= mo else y + 1, em, ed)
            else:                              # 2026-11-07/14
                end = date(y, mo, int(r))
        if start == end:
            text = fmt_day(start)
        elif start.year != end.year:
            text = f"{fmt_day(start)} – {fmt_day(end)}"
        elif start.month != end.month:
            text = f"{start.day} {MONTHS[start.month - 1]} – {fmt_day(end)}"
        else:
            text = f"{start.day}–{end.day} {MONTHS[start.month - 1]} {start.year}"
        iso, precision = start.isoformat(), "day"
    elif mo:
        start = date(y, mo, 1)
        em, ey = mo, y
        if r:                                  # 2026-10/11 or 2026-12/2027-01
            if "-" in r:
                ey, em = (int(x) for x in r.split("-"))
            else:
                em = int(r)
                ey = y if em >= mo else y + 1
        end = date(ey, em, cal.monthrange(ey, em)[1])
        if (em, ey) == (mo, y):
            text = f"{MONTHS[mo - 1]} {y}"
        elif ey == y:
            text = f"{MONTHS[mo - 1]}–{MONTHS[em - 1]} {y}"
        else:
            text = f"{MONTHS[mo - 1]} {y} – {MONTHS[em - 1]} {ey}"
        iso, precision = f"{y:04d}-{mo:02d}", "month"
    else:
        ey = int(r) if r else y                # 2026/2027
        start, end = date(y, 1, 1), date(ey, 12, 31)
        text = f"{y}–{ey}" if ey != y else f"{y}"
        iso, precision = f"{y:04d}", "year"

    if m["time"]:
        text += f", {'≈' if m['tapprox'] else ''}{m['time']} UTC"
    if m["q"]:
        text += f" ({tr(m['q'])})"
    if m["approx"]:
        text = "≈ " + text
    return When(start, end, text, iso, precision)


def date_label(token: str) -> str:
    """Format a date written in the source style; anything else is shown as written."""
    w = parse_when(token)
    return w.text if w else token


# ================================================================ markdown (English layer)

def resolve(url: str, depth: int) -> tuple[str, bool]:
    if re.match(r"https?://", url):
        return url, True
    kind, _, rest = url.partition(":")
    if kind == "mission":
        return rel(f"science/missions/{rest}.html", depth), False
    if kind == "facility":
        return rel(f"science/facilities/{rest}.html", depth), False
    if kind == "science":
        return rel(f"science/{rest}.html", depth), False
    if kind == "page":
        return rel(f"{rest}.html", depth), False
    return url, False


def inline(text: str, depth: int) -> str:
    stash: list[str] = []

    def keep(fragment: str) -> str:
        stash.append(fragment)
        return f"\x00{len(stash) - 1}\x00"

    text = re.sub(r"`([^`]+)`", lambda m: keep(f"<code>{esc(m.group(1))}</code>"), text)

    def link(m: re.Match) -> str:
        href, external = resolve(m.group(2), depth)
        attrs = ' class="ext" target="_blank" rel="noopener"' if external else ""
        return keep(f'<a href="{esc(href)}"{attrs}>{emphasis(esc(m.group(1)))}</a>')

    text = LINK_RE.sub(link, text)
    text = emphasis(html.escape(text, quote=False))
    while "\x00" in text:
        text = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], text)
    return text


def emphasis(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    return s


def blocks(md: str, depth: int) -> str:
    """Paragraphs, '### ' headings, '- ' lists and pipe tables."""
    out: list[str] = []
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        if s.startswith("### "):
            out.append(f"<h3>{inline(s[4:], depth)}</h3>")
            i += 1
        elif s.startswith("|"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                buf.append(lines[i])
                i += 1
            rows = table_rows("\n".join(buf), keep_header=True)
            head, body = rows[0], rows[1:]
            th = "".join(f"<th>{inline(c, depth)}</th>" for c in head)
            trs = "".join("<tr>" + "".join(f"<td>{inline(c, depth)}</td>" for c in r) + "</tr>" for r in body)
            out.append(f'<div class="table-wrap"><table class="dtable"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>')
        elif re.match(r"[-*]\s+", s):
            items: list[str] = []
            while i < len(lines) and lines[i].strip():
                t = lines[i].strip()
                if re.match(r"[-*]\s+", t):
                    items.append(re.sub(r"^[-*]\s+", "", t))
                elif items:
                    items[-1] += " " + t
                i += 1
            out.append("<ul>" + "".join(f"<li>{inline(t, depth)}</li>" for t in items) + "</ul>")
        else:
            buf = []
            while i < len(lines) and lines[i].strip() and not re.match(r"(\||[-*]\s+|### )", lines[i].strip()):
                buf.append(lines[i].strip())
                i += 1
            out.append(f"<p>{inline(' '.join(buf), depth)}</p>")
    return "\n".join(out)


def list_items(md: str) -> list[str]:
    items: list[str] = []
    for line in md.split("\n"):
        t = line.strip()
        if re.match(r"[-*]\s+", t):
            items.append(re.sub(r"^[-*]\s+", "", t))
        elif t and items:
            items[-1] += " " + t
    return items


# ================================================================ cards

@dataclass
class Item:
    kind: str                     # mission | facility
    id: str
    src: dict                     # Russian front matter (structured fields)
    meta: dict                    # English front matter
    sec: dict                     # English sections
    stale: bool
    checked: str

    @property
    def name(self) -> str:
        return self.meta.get("short") or self.meta.get("name") or self.src.get("name", self.id)

    @property
    def full_name(self) -> str:
        return self.meta.get("name") or self.name

    @property
    def status(self) -> str:
        return self.src.get("status", "")

    def path(self) -> str:
        return f"science/{PLURAL[self.kind]}/{self.id}.html"

    @property
    def official(self) -> str:
        return self.src.get("official", "")


class Site:
    def __init__(self, cfg: dict, today: date, space: Path, science: Path, private_exclude: list | None = None):
        self.cfg = cfg
        self.private_exclude = private_exclude or []
        self.today = today
        self.space = space
        self.science = science
        self.problems: list[str] = []
        self.stale: list[str] = []
        self.untranslated: list[str] = []
        self.missions: list[Item] = []
        self.facilities: list[Item] = []
        self.docs: dict[str, tuple[dict, str]] = {}
        # calendar
        self.tr_map: dict = cfg.setdefault("translations", {})
        self.missing: list[str] = []
        self.excluded: list[str] = []
        self.updated: dict[str, str] = {}
        self.row_missing = False

    # ------------------------------------------------ English layer
    def check_source(self, label: str, meta: dict, src: Path) -> tuple[bool, str]:
        if not src.exists():
            self.problems.append(f"{label}: source not found ({src})")
            return False, meta.get("checked", "")
        h = source_hash(src)
        if meta.get("source_hash") == h:
            return False, source_checked(src)
        why = "never stamped" if not meta.get("source_hash") else "source changed since translation"
        self.stale.append(f"{label} ({why}; English as of {meta.get('checked') or 'unknown'})")
        return True, meta.get("checked", "")

    def load_items(self, kind: str, repo: Path) -> list[Item]:
        src_dir = repo / PLURAL[kind]
        en_dir = CONTENT / PLURAL[kind]
        items = []
        for src in sorted(src_dir.glob("*.md")):
            if src.name.startswith(("_", "README")):
                continue
            src_meta, _ = split_doc(src.read_text(encoding="utf-8"))
            cid = src_meta.get("id", src.stem)
            en = en_dir / f"{src.stem}.md"
            if not en.exists():
                self.untranslated.append(f"{kind} {cid}: no English file ({en.relative_to(ROOT)}); not published")
                continue
            meta, body = split_doc(en.read_text(encoding="utf-8"))
            stale, checked = self.check_source(f"{kind} {cid}", meta, src)
            items.append(Item(kind, src.stem, src_meta, meta, sections(body), stale, checked))
        for en in sorted(en_dir.glob("*.md")) if en_dir.exists() else []:
            if not (src_dir / en.name).exists():
                self.problems.append(f"{kind} {en.stem}: English file without a source card (removed upstream?)")
        return items

    def load_doc(self, name: str, src: Path | None) -> tuple[dict, str, bool, str]:
        path = CONTENT / f"{name}.md"
        if not path.exists():
            self.problems.append(f"content/{name}.md is missing")
            return {}, "", False, ""
        meta, body = split_doc(path.read_text(encoding="utf-8"))
        if src is None:
            return meta, body, False, meta.get("checked", "")
        stale, checked = self.check_source(f"content/{name}.md", meta, src)
        return meta, body, stale, checked

    def load(self) -> None:
        self.missions = self.load_items("mission", self.space)
        order = {k: i for i, (k, _) in enumerate(REGIONS)}
        self.missions.sort(key=lambda it: (order.get(it.src.get("region", ""), 99), it.name.lower()))
        self.facilities = self.load_items("facility", self.science)
        dorder = {k: i for i, (k, _) in enumerate(DOMAINS)}
        self.facilities.sort(key=lambda it: (dorder.get(it.src.get("domain", ""), 99), it.name.lower()))
        self.by_id = {("mission", it.id): it for it in self.missions}
        self.by_id.update({("facility", it.id): it for it in self.facilities})
        results_src = sorted((self.science / "results").glob("*.md"))
        self.results = self.load_doc("results", results_src[-1] if results_src else None)
        self.launches = self.load_doc("launches", self.space / "launches.md")
        self.method = self.load_doc("method", None)
        self.events = self.load_events()

    # ------------------------------------------------ calendar
    def tr(self, ru: str) -> str:
        key = norm(ru)
        val = self.tr_map.get(key)
        if val:
            return val
        if key not in self.tr_map:
            self.tr_map[key] = ""
        if key not in self.missing:
            self.missing.append(key)
        self.row_missing = True
        return key

    def is_excluded(self, raw_row: str) -> bool:
        for rule in self.cfg.get("exclude", []) + self.private_exclude:
            if rule["match"] in raw_row:
                self.excluded.append(f"{strip_md(raw_row)[:90]}…  ({rule.get('reason', '')})")
                return True
        return False

    @staticmethod
    def bucket_of(heading: str) -> str | None:
        h = heading.lower()
        if h.startswith("ближайш"):
            return "upcoming"
        if h.startswith("дальше"):
            return "later"
        if h.startswith("недавно"):
            return "recent"
        return None

    def load_events(self) -> list["Event"]:
        evs = self.load_space_calendar() + self.load_science_calendar()
        past_note = self.cfg.get("past_planned_note", "")
        for e in evs:
            if e.bucket == "upcoming" and e.when.end < self.today:
                e.bucket = "recent"          # planned, date passed, not confirmed
                e.note = past_note
        return evs

    def load_space_calendar(self) -> list["Event"]:
        path = self.space / "calendar.md"
        if not path.exists():
            self.problems.append(f"not found: {path}")
            return []
        md = path.read_text(encoding="utf-8")
        self.updated["space"] = updated_on(md)
        events = []
        for heading, body in sections(md).items():
            bucket = self.bucket_of(heading)
            if not bucket:
                continue
            for i, row in enumerate(table_rows(body)):
                if len(row) < 3 or self.is_excluded("|".join(row)):
                    continue
                self.row_missing = False
                when = parse_when(row[0], self.tr)
                if not when:
                    self.problems.append(f"space calendar: unreadable date {row[0]!r}")
                    continue
                links = LINK_RE.findall(row[1])
                title = links[0][0] if links else strip_md(row[1])
                ref = ("mission", Path(links[0][1]).stem) if links else None
                text = self.tr(strip_md(row[2]).lstrip("✅❔ ").strip())
                note = self.tr(strip_md(row[3])) if bucket == "upcoming" and len(row) > 3 and row[3] else ""
                if self.row_missing:
                    continue
                item = self.by_id.get(ref) if ref else None
                region = REGION.get(item.src.get("region", "")) if item else ""
                events.append(Event(
                    bucket=bucket, when=when, cat="space",
                    cat_label="Space" + (f" · {region}" if region else ""),
                    title=title, ref=ref if item else None,
                    url=item.official if item else "", text=text, note=note, order=i,
                ))
        return events

    def load_science_calendar(self) -> list["Event"]:
        path = self.science / "calendar.md"
        if not path.exists():
            self.problems.append(f"not found: {path}")
            return []
        md = path.read_text(encoding="utf-8")
        self.updated["science"] = updated_on(md)
        directions = self.cfg.get("directions", {})
        links_cfg = self.cfg.get("links", {})
        events = []
        for heading, body in sections(md).items():
            bucket = self.bucket_of(heading)
            if not bucket:
                continue
            for i, row in enumerate(table_rows(body)):
                if len(row) < 3 or self.is_excluded("|".join(row)):
                    continue
                direction = directions.get(norm(row[2]))
                if not direction:
                    self.problems.append(f"science calendar: unknown direction {row[2]!r} (add it to data/calendar.json → directions)")
                    continue
                cell = INTERNAL_REF_RE.sub("", row[1]).strip()
                fac_links = [l for l in LINK_RE.findall(cell) if l[1].startswith("facilities/")]
                ref = ("facility", Path(fac_links[0][1]).stem) if fac_links else None
                item = self.by_id.get(ref) if ref else None
                self.row_missing = False
                when = parse_when(row[0], self.tr)
                if not when:
                    self.problems.append(f"science calendar: unreadable date {row[0]!r}")
                    continue
                lead = re.match(r"\[([^\]]+)\]\((facilities/[^)]+)\)\s*[:,]\s*(.*)$", cell)
                if lead:
                    title, text = lead.group(1), self.tr(strip_md(lead.group(3)))
                else:
                    en = self.tr(strip_md(cell))
                    title, _, text = en.partition(": ") if ": " in en else ("", "", en)
                note = self.tr(strip_md(row[3])) if bucket == "upcoming" and len(row) > 3 and row[3] else ""
                if self.row_missing:
                    continue
                url = links_cfg.get(title) or (item.official if item else "")
                if title in links_cfg:
                    item = None       # an explicit link wins over the facility page
                events.append(Event(
                    bucket=bucket, when=when, cat=direction["cat"], cat_label=direction["label"],
                    title=title, ref=ref if item else None, url=url, text=text, note=note, order=i,
                ))
        return events


@dataclass
class Event:
    bucket: str                  # upcoming | later | recent
    when: When
    cat: str                     # space | facility | conference
    cat_label: str
    title: str = ""
    ref: tuple | None = None     # ("mission"|"facility", id) when a page exists
    url: str = ""
    text: str = ""
    note: str = ""
    order: int = 0


def sort_events(evs: list[Event], reverse: bool = False) -> list[Event]:
    return sorted(evs, key=lambda e: (e.when.start, e.when.end, e.order), reverse=reverse)


# ================================================================ HTML pieces

def status_html(item: Item) -> str:
    table = MISSION_STATUS if item.kind == "mission" else FACILITY_STATUS
    label, tone = table.get(item.status, (item.status or "Unknown", "end"))
    return f'<span class="st st-{tone}"><span class="st-dot" aria-hidden="true"></span>{esc(label)}</span>'


def group_of(item: Item) -> str:
    groups = MISSION_GROUPS if item.kind == "mission" else FACILITY_GROUPS
    for key, _, statuses in groups:
        if item.status in statuses:
            return key
    return "other"


def next_event_html(text: str) -> str:
    if not text or text.strip() in {"—", "-"}:
        return ""
    head, sep, tail = text.partition(" — ")
    w = parse_when(head) if sep else None
    if w:
        return f'<span class="nx-d">{esc(w.text)}</span> {esc(tail)}'
    return esc(text)


def event_title_html(e: Event, site: Site, depth: int) -> str:
    if e.title and e.ref and e.ref in site.by_id:
        return f'<a class="ev-title" href="{esc(rel(site.by_id[e.ref].path(), depth))}">{esc(e.title)}</a>'
    if e.title and e.url:
        return f'<a class="ev-title ext" href="{esc(e.url)}" target="_blank" rel="noopener">{esc(e.title)}</a>'
    if e.title:
        return f'<span class="ev-title">{esc(e.title)}</span>'
    return ""


def event_html(e: Event, site: Site, depth: int, show_cat: bool = True) -> str:
    title = event_title_html(e, site, depth)
    sep = " — " if title and e.text else ""
    text = e.text[:1].upper() + e.text[1:]
    note = f'<span class="ev-note">{esc(e.note)}</span>' if e.note else ""
    cat = (f'<div class="ev-cat"><span class="px {e.cat}" aria-hidden="true"></span>{esc(e.cat_label)}</div>'
           if show_cat else "")
    return (
        f'<li class="ev" data-cat="{e.cat}">'
        f'<div class="ev-date"><time datetime="{e.when.iso}">{esc(e.when.text)}</time></div>'
        f'<div class="ev-main">{title}{sep}<span class="ev-text">{esc(text)}</span>{note}</div>'
        f'{cat}</li>'
    )


def countdown_html(site: Site, depth: int, n: int = 4) -> str:
    """Next events with a known day; science.js turns dates into 'in N days'
    and drops events that have passed since the build."""
    items = [e for e in site.events if e.bucket == "upcoming" and e.when.precision == "day"
             and e.when.start >= site.today]          # only events that have not started yet
    items = sort_events(items)[: n + 3]          # spares in case some pass before the next build
    if not items:
        return '<p class="cal-empty">Nothing with a fixed date in the next weeks.</p>'
    out = []
    for k, e in enumerate(items):
        title = event_title_html(e, site, depth)
        sep = " — " if title and e.text else ""
        text = e.text[:1].upper() + e.text[1:]
        cls = "nx is-lead" if k == 0 else ("nx" if k <= n - 1 else "nx is-spare")
        out.append(
            f'<li class="{cls}" data-start="{e.when.start.isoformat()}" data-end="{e.when.end.isoformat()}">'
            f'<div class="nx-when"><span class="nx-count" data-count></span>'
            f'<time datetime="{e.when.iso}">{esc(e.when.text)}</time></div>'
            f'<div class="nx-what">{title}{sep}<span>{esc(text)}</span></div>'
            f'<div class="ev-cat"><span class="px {e.cat}" aria-hidden="true"></span>{esc(e.cat_label)}</div>'
            f'</li>'
        )
    return f'<ol class="next-list" data-show="{n}">\n' + "\n".join(out) + "\n</ol>"


FKEYS = [("1", "Home", "index.html"), ("2", "About", "about.html"), ("3", "Projects", "projects.html"),
         ("4", "CV", "cv.html"), ("5", "Skills", "cv.html#skills"), ("6", "Papers", "cv.html#publications"),
         ("7", "Explore", "science/index.html"), ("8", "Contact", "contact.html"), ("9", "Privacy", "privacy.html")]


def dos_name(name: str, taken: set[str]) -> str:
    """8.3 file name in the style of Windows 95: HAYABU~1.HTM"""
    stem = name.upper()
    if len(stem) <= 8:
        short = stem
    else:
        n = 1
        while f"{stem[:6]}~{n}" in taken:
            n += 1
        short = f"{stem[:6]}~{n}"
    taken.add(short)
    return short


def page(site: Site, *, slug: str, title: str, description: str, depth: int, body: str,
         sub: str | None, dos: str, scripts: tuple[str, ...] = ("science.js",)) -> str:
    def nav(href: str, label: str, current: bool) -> str:
        cur = ' aria-current="page"' if current else ""
        return f'<li><a href="{esc(rel(href, depth))}"{cur}>{label}</a></li>'

    main_nav = "\n      ".join([
        nav("index.html", "Home", False), nav("about.html", "About", False),
        nav("projects.html", "Projects", False), nav("cv.html", "CV", False),
        nav("science/index.html", "Science &amp; Space", True), nav("contact.html", "Contact", False),
    ])
    current = ' aria-current="page"'
    sub_nav = "\n      ".join(
        f'<li><a href="{esc(rel("science/" + k + ".html", depth))}"'
        f'{current if k == sub else ""}>{label}</a></li>'
        for k, label in SUBNAV)
    js = "\n".join(f'<script src="{esc(rel(f"assets/js/{s}", depth))}" defer></script>' for s in (*scripts, "retro.js"))
    cur_key = "science/index.html"  # F7 "Explore" stands for the whole Science & Space section
    fkeys = "".join(
        f'<a href="{esc(rel(h, depth))}"{current if h == cur_key else ""}><b>{n}</b><span>{l}</span></a>'
        for n, l, h in FKEYS) + '<a href="#"><b>10</b><span>Top</span></a>'
    full_title = f"{title} — Science & Space — Konstantin Sukharnikov" if slug != "index" else \
        "Science & Space — Konstantin Sukharnikov"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Content-Security-Policy" content="{CSP}">
  <meta name="referrer" content="strict-origin-when-cross-origin">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(full_title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{esc(full_title)}">
  <meta property="og:description" content="{esc(description)}">
  <link rel="icon" href="{rel('assets/favicon.svg', depth)}" type="image/svg+xml">
  <link rel="preload" href="{rel('assets/fonts/jetbrains-mono-latin-400-normal.woff2', depth)}" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="{rel('assets/css/style.css', depth)}">
</head>
<body class="sci">
<!-- generated by tools/build_science.py — do not edit by hand -->
<a class="skip" href="#main">Skip to content</a>

<header class="site-header">
  <div>
    <a class="brand" href="{rel('index.html', depth)}">Konstantin Sukharnikov</a>
    <span class="label brand-note">Scientific instrumentation</span>
  </div>
  <nav class="site-nav" aria-label="Main">
    <ul>
      {main_nav}
    </ul>
  </nav>
</header>
<div class="dos-path wrap" aria-hidden="true">{esc(dos)}&gt;<span class="cursor"></span></div>

<div class="sci-bar wrap">
  <nav class="sub-nav" aria-label="Science &amp; Space">
    <ul>
      {sub_nav}
    </ul>
  </nav>
  <p class="side-note"><span class="px space" aria-hidden="true"></span><span><strong>A hobby.</strong> An independent overview compiled from public sources by a science and space enthusiast. I am not involved in these missions or facilities; my own work is detector electronics at European XFEL. <a href="{rel('projects.html', depth)}">My projects&nbsp;→</a></span></p>
</div>

<main id="main">
{body}
</main>

<aside class="author wrap" aria-label="About the author">
  <div class="author-in">
    <p class="label">Who keeps this page</p>
    <p class="author-text"><strong>Konstantin Sukharnikov</strong> works on scientific instrumentation: detector electronics for X-ray experiments at <a href="{rel(f'science/facilities/{HOME_FACILITY}.html', depth)}">European XFEL</a> in the Hamburg area. Outside work he is a science and space enthusiast, and this section is his hobby.</p>
    <p class="author-links"><a href="{rel('projects.html', depth)}">Projects&nbsp;→</a> <a href="{rel('cv.html', depth)}">CV&nbsp;→</a> <a href="{rel('contact.html', depth)}">Contact&nbsp;→</a></p>
  </div>
</aside>

<footer class="site-footer">
  <div class="foot-row">
    <span>© 2026 Konstantin Sukharnikov · Hamburg</span>
    <span data-lastmod></span>
    <ul>
      <li><a href="{rel('science/method.html', depth)}">How this section is made</a></li>
      <li><a href="{rel('contact.html', depth)}">Contact</a></li>
      <li><a href="{rel('privacy.html', depth)}">Privacy</a></li>
      <li><a class="ext" href="https://www.linkedin.com/in/konstantineng/" target="_blank" rel="noopener">LinkedIn</a></li>
    </ul>
  </div>
  <ul class="badges" aria-label="About this website">
    <li>Static<br>HTML</li><li>No<br>cookies</li><li>No<br>tracking</li><li>UTF-8<br>inside</li><li>Any<br>browser</li>
  </ul>
</footer>
<nav class="fkeys" aria-label="Function keys">{fkeys}</nav>
{js}
</body>
</html>
"""


def head_block(title: str, lead: str, wrap: bool = True) -> str:
    inner = f'<div class="page-head">\n  <h1>{title}</h1>\n  <p class="lead">{lead}</p>\n</div>'
    return f'<div class="wrap">\n{inner}\n</div>' if wrap else inner


# ================================================================ cards & lists

def card_html(item: Item, depth: int) -> str:
    if item.kind == "mission":
        place = REGION.get(item.src.get("region", ""), "")
        attrs = f'data-a="{esc(item.src.get("region", ""))}" data-b="{group_of(item)}"'
        sub = item.meta.get("agencies", "")
        px = "space"
    else:
        place = DOMAIN.get(item.src.get("domain", ""), "")
        attrs = f'data-a="{esc(item.src.get("domain", ""))}" data-b="{group_of(item)}"'
        sub = item.meta.get("location", "")
        px = "facility"
    search = " ".join([item.full_name, item.name, item.meta.get("agencies", ""), item.meta.get("target", ""),
                       item.meta.get("location", ""), item.meta.get("operator", ""), place]).lower()
    home = '<span class="home-tag">Where I work</span>' if item.id == HOME_FACILITY else ""
    nxt = next_event_html(item.meta.get("next_event", ""))
    nxt = f'<p class="card-next"><span class="label">Next</span> {nxt}</p>' if nxt else ""
    return (
        f'<li class="card" {attrs} data-q="{esc(search)}">'
        f'<a class="card-link" href="{esc(rel(item.path(), depth))}">'
        f'<span class="card-top"><span class="card-place"><span class="px {px}" aria-hidden="true"></span>{esc(place)}</span>{status_html(item)}</span>'
        f'<span class="card-name">{esc(item.name)}</span>{home}'
        f'<span class="card-sub">{esc(sub)}</span>'
        f'<span class="card-summary">{esc(item.meta.get("tagline", ""))}</span>'
        f'</a>{nxt}</li>'
    )


def filter_bar(name: str, a_label: str, a_opts: list[tuple[str, str]],
               b_label: str, b_opts: list[tuple[str, str]], placeholder: str) -> str:
    def chips(key: str, label: str, opts) -> str:
        btns = [f'<button type="button" data-key="{key}" data-val="all" aria-pressed="true">All</button>']
        btns += [f'<button type="button" data-key="{key}" data-val="{esc(v)}" aria-pressed="false">{esc(t)}</button>'
                 for v, t in opts]
        return f'<div class="chips" role="group" aria-label="{esc(label)}"><span class="label">{esc(label)}</span>{"".join(btns)}</div>'
    return (
        f'<div class="grid-tools" data-grid="{name}" hidden>'
        f'{chips("a", a_label, a_opts)}{chips("b", b_label, b_opts)}'
        f'<label class="search"><span class="label">Search</span>'
        f'<input type="search" placeholder="{esc(placeholder)}" autocomplete="off"></label>'
        f'</div>'
    )


# ================================================================ item pages

def keydates_html(md: str, depth: int) -> str:
    rows = table_rows(md)
    if not rows:
        return ""
    out = []
    for r in rows:
        when = date_label(r[0]) if r else ""
        what = inline(r[1], depth) if len(r) > 1 else ""
        st = r[2].strip().lower() if len(r) > 2 else ""
        tone = KEYDATE_STATUS.get(st, "planned")
        out.append(f'<li><span class="kd-date">{esc(when)}</span><span class="kd-what">{what}</span>'
                   f'<span class="kd-st kd-{tone}">{esc(st)}</span></li>')
    return '<ol class="kd">' + "".join(out) + "</ol>"


def timeline_html(md: str, depth: int) -> str:
    items = list_items(md)
    if not items:
        return ""
    out = []
    for t in items:
        head, sep, tail = t.partition(" — ")
        if sep and re.match(r"≈?\s*\d{4}", head):
            out.append(f'<li><span class="tl-date">{esc(date_label(head))}</span><span class="tl-text">{inline(tail, depth)}</span></li>')
        else:
            out.append(f'<li><span class="tl-date"></span><span class="tl-text">{inline(t, depth)}</span></li>')
    return '<ol class="tl">' + "".join(out) + "</ol>"


def item_page(site: Site, item: Item, prev_it: Item | None, next_it: Item | None, dos: str) -> str:
    d = 2
    m = item.meta
    is_m = item.kind == "mission"
    place = REGION.get(item.src.get("region", ""), "") if is_m else DOMAIN.get(item.src.get("domain", ""), "")
    kind_label = "Mission" if is_m else "Facility"
    list_page = "missions" if is_m else "facilities"

    facts = [("Status", status_html(item))]
    if is_m:
        if item.src.get("launch_date"):
            facts.append(("Launched", esc(fmt_iso(item.src["launch_date"]))))
        if m.get("target"):
            facts.append(("Target", esc(m["target"])))
        if m.get("agencies"):
            facts.append(("Agencies", esc(m["agencies"])))
    else:
        if m.get("location"):
            facts.append(("Location", esc(m["location"])))
        if m.get("operator"):
            facts.append(("Operator", esc(m["operator"])))
    nxt = next_event_html(m.get("next_event", ""))
    if nxt:
        facts.append(("Next", nxt))
    facts_html = "".join(f'<div><dt class="label">{k}</dt><dd>{v}</dd></div>' for k, v in facts)

    main = []
    for head, key in (("Summary", "Summary"), ("Now", "Now")):
        if item.sec.get(key):
            extra = f' <span class="asof">as of {esc(fmt_iso(item.checked))}</span>' if key == "Now" else ""
            main.append(f"<h2>{head}{extra}</h2>\n{blocks(item.sec[key], d)}")
    if item.sec.get("Key dates"):
        kd = item.sec["Key dates"]
        table_part = "\n".join(l for l in kd.split("\n") if l.strip().startswith("|"))
        note_part = "\n".join(l for l in kd.split("\n") if not l.strip().startswith("|")).strip()
        main.append("<h2>Key dates</h2>\n" + keydates_html(table_part, d)
                    + (f'\n<div class="kd-note">{blocks(note_part, d)}</div>' if note_part else ""))
    if item.sec.get("Results"):
        main.append("<h2>Results</h2>\n" + timeline_html(item.sec["Results"], d))
    if item.sec.get("Timeline"):
        main.append("<h2>Timeline</h2>\n" + timeline_html(item.sec["Timeline"], d))

    aside = []
    if item.official:
        what = "mission" if is_m else "facility"
        aside.append(f'<a class="out" href="{esc(item.official)}" target="_blank" rel="noopener">Official {what} site&nbsp;↗</a>')
    if item.sec.get("Links"):
        aside.append('<h2 class="label">Sources and links</h2>' + blocks(item.sec["Links"], d))
    evs = [e for e in site.events if e.ref == (item.kind, item.id) and e.bucket in ("upcoming", "later")]
    if evs:
        lis = "".join(f'<li><time datetime="{e.when.iso}">{esc(e.when.text)}</time>{esc(e.text[:1].upper() + e.text[1:])}</li>'
                      for e in sort_events(evs))
        aside.append(f'<h2 class="label">In the calendar</h2><ul class="mini-cal">{lis}</ul>'
                     f'<p class="mini-more"><a href="{rel("science/calendar.html", d)}">Full calendar →</a></p>')
    if item.id == HOME_FACILITY:
        aside.append(
            '<div class="note home-note"><p class="label">Where I work</p>'
            '<p>I work at European XFEL, in the Detectors Group. This page is my own summary of public '
            'information and does not speak for the company.</p>'
            f'<p><a href="{rel("projects.html", d)}">What I work on here →</a></p></div>')
    else:
        orgs = [a.strip() for a in (m.get("agencies") or "").split(",") if a.strip()]
        agencies = (", ".join(orgs[:-1]) + " or " + orgs[-1]) if len(orgs) > 1 else \
            (orgs[0] if orgs else (m.get("operator") or "the organisations named above"))
        aside.append(
            '<div class="note"><p class="label">Not affiliated</p>'
            f'<p>Independent summary from the public sources linked on this page. I am not involved in '
            f'this {"mission" if is_m else "facility"} and not affiliated with {esc(agencies)}.</p></div>')

    pager = []
    if prev_it:
        pager.append(f'<a class="prev" href="{esc(rel(prev_it.path(), d))}"><span class="label">Previous</span>{esc(prev_it.name)}</a>')
    if next_it:
        pager.append(f'<a class="next" href="{esc(rel(next_it.path(), d))}"><span class="label">Next</span>{esc(next_it.name)}</a>')

    home_tag = '<span class="home-tag">Where I work</span>' if item.id == HOME_FACILITY else ""
    body = f"""<article class="item wrap">
  <nav class="bc label" aria-label="Breadcrumb"><a href="{rel('science/index.html', d)}">Science &amp; Space</a> / <a href="{rel(f'science/{list_page}.html', d)}">{'Missions' if is_m else 'Facilities'}</a></nav>
  <header class="item-head">
    <p class="label item-kind"><span class="px {'space' if is_m else 'facility'}" aria-hidden="true"></span>{kind_label} · {esc(place)}</p>
    <h1>{esc(item.full_name)}</h1>{home_tag}
    <p class="item-sub">{esc(m.get('kind', ''))}</p>
  </header>
  <dl class="item-facts">{facts_html}</dl>
  <div class="item-body">
    <div class="item-main prose" data-title="{esc(item.name)}">
{chr(10).join(main)}
    </div>
    <aside class="item-aside" data-title="Info">
{chr(10).join(aside)}
    </aside>
  </div>
  <nav class="pager" aria-label="More {list_page}">{''.join(pager)}</nav>
</article>"""
    desc = m.get("tagline") or strip_md(item.sec.get("Summary", ""))[:200]
    return page(site, slug=item.id, title=item.full_name, description=desc, depth=d, body=body, sub=list_page, dos=dos)


# ================================================================ section pages

def orbit_html(site: Site, depth: int) -> str:
    by_region: dict[str, list[Item]] = {k: [] for k, _ in REGIONS}
    for it in site.missions:
        by_region.setdefault(it.src.get("region", ""), []).append(it)
    lis = []
    for key, label in REGIONS:
        items = by_region.get(key, [])
        live = [it for it in items if it.status not in ("ended", "lost")]
        ms = "".join(
            f'<li class="{"gone" if it.status in ("ended", "lost") else ""}">'
            f'<a href="{esc(rel(it.path(), depth))}">{esc(it.name)}</a></li>' for it in items)
        ms = f'<ul class="orb-m">{ms}</ul>' if ms else '<p class="orb-none">No mission tracked</p>'
        lis.append(
            f'<li class="orb orb-{key}{" is-empty" if not items else ""}">'
            f'<span class="body" aria-hidden="true"></span>'
            f'<span class="orb-name">{esc(label)}</span>'
            f'{f"<span class=\"orb-n label\">{len(live)} active</span>" if items else ""}{ms}</li>')
    return '<ol class="orbit">' + "".join(lis) + "</ol>"


def stages_html(site: Site, depth: int) -> str:
    cols = []
    tag = '<span class="home-tag">Where I work</span>'
    for key, label, statuses in FACILITY_GROUPS:
        items = [it for it in site.facilities if it.status in statuses]
        if not items:
            continue
        lis = "".join(
            f'<li><a href="{esc(rel(it.path(), depth))}">{esc(it.name)}</a>'
            f'{tag if it.id == HOME_FACILITY else ""}'
            f'<span class="stage-d">{esc(DOMAIN.get(it.src.get("domain", ""), ""))}</span></li>' for it in items)
        cols.append(f'<div class="stage"><h3 class="label">{esc(label)} <span>{len(items)}</span></h3><ul>{lis}</ul></div>')
    return '<div class="stages">' + "".join(cols) + "</div>"


def result_entries(site: Site) -> list[dict]:
    meta, body, _, _ = site.results
    out = []
    for month, md in sections(body).items():
        for t in list_items(md):
            m = re.match(r"\*\*(.+?)\s*·\s*([^*]+?)\*\*\s*—\s*(.*)$", t)
            if not m:
                site.problems.append(f"results: unreadable entry {t[:60]!r}")
                continue
            dom = m.group(2).strip()
            out.append({"month": month, "date": m.group(1).strip(), "domain": dom,
                        "label": RESULT_DOMAINS.get(dom.split()[0], dom), "text": m.group(3)})
    return out


def results_list_html(entries: list[dict], depth: int) -> str:
    lis = "".join(
        f'<li class="res" data-dom="{esc(e["domain"].split()[0])}"><span class="res-date">{esc(date_label(e["date"]))}</span>'
        f'<span class="res-dom label">{esc(e["label"])}</span>'
        f'<span class="res-text">{inline(e["text"], depth)}</span></li>' for e in entries)
    return f'<ol class="res-list">{lis}</ol>'


def overview_page(site: Site) -> str:
    d = 1
    upcoming = sort_events([e for e in site.events if e.bucket == "upcoming"])[:7]
    up_html = "\n".join(event_html(e, site, d) for e in upcoming)
    entries = result_entries(site)[:5]
    n_active = sum(it.status not in ("ended", "lost") for it in site.missions)
    body = f"""{head_block("Science &amp; Space",
        "I am a science and space enthusiast, and this section is my hobby: interplanetary missions and the big machines of physics on Earth, what is flying, what is being built and what comes next. Every entry links to its source.")}

<section class="sci-sec wrap" aria-labelledby="h-next">
  <div class="sec-head"><h2 id="h-next">Next up</h2><a href="calendar.html">Full calendar →</a></div>
  {countdown_html(site, d)}
</section>

<section class="sci-sec wrap" aria-labelledby="h-orbit">
  <div class="sec-head"><h2 id="h-orbit">Where they fly</h2><a href="missions.html">All {len(site.missions)} missions →</a></div>
  <p class="sec-sub">{len(site.missions)} missions tracked across the solar system, from the Sun outwards; {n_active} of them still working.</p>
  {orbit_html(site, d)}
</section>

<section class="sci-sec wrap" aria-labelledby="h-earth">
  <div class="sec-head"><h2 id="h-earth">Big science on Earth</h2><a href="facilities.html">All {len(site.facilities)} facilities →</a></div>
  <p class="sec-sub">X-ray lasers, gravitational-wave and neutrino detectors, telescopes, neutron sources and colliders, by stage.</p>
  {stages_html(site, d)}
</section>

<section class="sci-sec wrap" aria-labelledby="h-results">
  <div class="sec-head"><h2 id="h-results">Recent results</h2><a href="results.html">All results →</a></div>
  {results_list_html(entries, d)}
</section>

<section class="sci-sec wrap" aria-labelledby="h-soon">
  <div class="sec-head"><h2 id="h-soon">Coming up</h2><a href="calendar.html">Full calendar →</a></div>
  <ol class="cal-list">
{up_html}
  </ol>
</section>"""
    return page(site, slug="index", title="Science & Space",
                description="Interplanetary missions and large research facilities: countdown, calendar, results and launches, compiled from public sources by Konstantin Sukharnikov.",
                depth=d, body=body, sub="index", dos="C:\\KS\\SCIENCE\\INDEX.HTM")


def missions_page(site: Site) -> str:
    d = 1
    regions = [(k, l) for k, l in REGIONS if any(it.src.get("region") == k for it in site.missions)]
    groups = [(k, l) for k, l, s in MISSION_GROUPS if any(it.status in s for it in site.missions)]
    cards = "\n".join(card_html(it, d) for it in site.missions)
    body = f"""{head_block("Missions", "Spacecraft beyond Earth orbit, from the Sun to interstellar space. Status, next milestone and key dates for each, with links to the agencies.")}
<section class="sci-sec wrap" data-title="C:\\KS\\SCIENCE\\MISSIONS\\*.*">
  {filter_bar("missions", "Destination", regions, "Status", groups, "Name, agency or target")}
  <ul class="cards">
{cards}
  </ul>
  <p class="cal-empty" hidden>No mission matches.</p>
</section>"""
    return page(site, slug="missions", title="Missions",
                description="Interplanetary missions: status, next milestones and key dates, with links to NASA, ESA, JAXA and CNSA.",
                depth=d, body=body, sub="missions", dos="C:\\KS\\SCIENCE\\MISSIONS.HTM")


def facilities_page(site: Site) -> str:
    d = 1
    domains = [(k, l) for k, l in DOMAINS if any(it.src.get("domain") == k for it in site.facilities)]
    groups = [(k, l) for k, l, s in FACILITY_GROUPS if any(it.status in s for it in site.facilities)]
    cards = "\n".join(card_html(it, d) for it in site.facilities)
    body = f"""{head_block("Facilities", "Large research infrastructures on Earth: X-ray free-electron lasers, synchrotrons, gravitational-wave and neutrino observatories, telescopes, neutron sources and colliders.")}
<section class="sci-sec wrap" data-title="C:\\KS\\SCIENCE\\FACILI~1\\*.*">
  {filter_bar("facilities", "Field", domains, "Stage", groups, "Name, place or operator")}
  <ul class="cards">
{cards}
  </ul>
  <p class="cal-empty" hidden>No facility matches.</p>
</section>"""
    return page(site, slug="facilities", title="Facilities",
                description="Large research facilities: X-ray lasers, gravitational-wave and neutrino observatories, telescopes, neutron sources and colliders.",
                depth=d, body=body, sub="facilities", dos="C:\\KS\\SCIENCE\\FACILI~1.HTM")


CAL_SECTIONS = [
    ("upcoming", "Coming up", "The next weeks and months."),
    ("later", "Further ahead", "Planned milestones over the next years. Plans in big science move; treat these as targets."),
    ("recent", "Recently", "What happened over the last weeks."),
]


def calendar_page(site: Site) -> str:
    d = 1
    out = []
    for key, head, sub in CAL_SECTIONS:
        items = sort_events([e for e in site.events if e.bucket == key], reverse=(key == "recent"))
        lis = "\n".join(event_html(e, site, d) for e in items)
        out.append(
            f'<section class="cal-section" aria-labelledby="h-{key}">\n'
            f'  <h2 id="h-{key}">{head}</h2>\n  <p class="sub">{sub}</p>\n'
            f'  <ol class="cal-list">\n{lis}\n  </ol>\n'
            f'  <p class="cal-empty" hidden>Nothing in this category.</p>\n</section>')
    body = f"""<div class="wrap">
{head_block("Calendar", "Flybys, orbit insertions and landings; first beams, observing runs and site decisions at large facilities; and conferences on detectors and their electronics.", wrap=False)}
  <div class="cal-filter" id="cal-filter" role="group" aria-label="Filter events" hidden>
    <button type="button" data-filter="all" aria-pressed="true">All</button>
    <button type="button" data-filter="space" aria-pressed="false"><span class="px space" aria-hidden="true"></span>Space missions</button>
    <button type="button" data-filter="facility" aria-pressed="false"><span class="px facility" aria-hidden="true"></span>Facilities</button>
    <button type="button" data-filter="conference" aria-pressed="false"><span class="px conference" aria-hidden="true"></span>Detector conferences</button>
  </div>
{chr(10).join(out)}
  <div class="cal-meta">
    <p>Space missions as of {fmt_iso(site.updated.get("space", ""))}; facilities and conferences as of {fmt_iso(site.updated.get("science", ""))}. Names link to the mission or facility page here, or to the official site.</p>
    <p>Dates are the organisers’ plans and often shift. “≈” marks an estimate; times are UTC.</p>
  </div>
</div>"""
    return page(site, slug="calendar", title="Calendar",
                description="A calendar of science and space events: interplanetary missions, large research facilities and detector conferences.",
                depth=d, body=body, sub="calendar", scripts=("calendar.js",), dos="C:\\KS\\SCIENCE\\CALENDAR.HTM")


def results_page(site: Site) -> str:
    d = 1
    meta, body_md, stale, checked = site.results
    groups = []
    entries = result_entries(site)
    for month in dict.fromkeys(e["month"] for e in entries):
        es = [e for e in entries if e["month"] == month]
        groups.append(f'<section class="res-group"><h2>{esc(month)}</h2>{results_list_html(es, d)}</section>')
    body = f"""{head_block("Results", "Notable scientific results from large facilities and space missions: what was found, with the paper (DOI or arXiv) and the press release where there is one.")}
<div class="sci-sec wrap" data-title="RESULTS.TXT">
{chr(10).join(groups)}
  <div class="cal-meta"><p>As of {esc(fmt_iso(checked))}. A preprint is marked as such until it is published.</p></div>
</div>"""
    return page(site, slug="results", title="Results",
                description="Notable results from large research facilities and space missions, with links to the papers.",
                depth=d, body=body, sub="results", dos="C:\\KS\\SCIENCE\\RESULTS.HTM")


def doc_page(site: Site, slug: str, title: str, lead: str, doc: tuple, description: str) -> str:
    d = 1
    meta, body_md, stale, checked = doc
    parts = []
    for head, md in sections(body_md).items():
        parts.append(f'<section class="doc-sec"><h2>{esc(head)}</h2>{blocks(md, d)}</section>')
    asof = f'<div class="cal-meta"><p>As of {esc(fmt_iso(checked))}. “NET” means “no earlier than”.</p></div>' if slug == "launches" else ""
    body = f"""{head_block(title, lead)}
<div class="sci-sec wrap doc prose-wide" data-title="{slug.upper()}.TXT">
{chr(10).join(parts)}
{asof}
</div>"""
    return page(site, slug=slug, title=title, description=description, depth=d, body=body, sub=slug,
                dos=f"C:\\KS\\SCIENCE\\{slug.upper()}.HTM")


# ================================================================ home teaser

def replace_block(text: str, name: str, content: str) -> str:
    pat = re.compile(rf"(<!-- BEGIN {name}[^>]*-->)(.*?)(<!-- END {name} -->)", re.S)
    if not pat.search(text):
        raise SystemExit(f"marker <!-- BEGIN {name} --> … <!-- END {name} --> not found in index.html")
    return pat.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(3)}", text, count=1)


# ================================================================ main

def build(site: Site) -> dict[str, str]:
    pages: dict[str, str] = {
        "index.html": overview_page(site),
        "missions.html": missions_page(site),
        "facilities.html": facilities_page(site),
        "calendar.html": calendar_page(site),
        "results.html": results_page(site),
        "launches.html": doc_page(site, "launches", "Launches",
                                  "Upcoming launches to the planets and small bodies, with a short list for the Moon. Dates are “no earlier than”.",
                                  site.launches, "Upcoming deep-space launches: missions to the planets, small bodies and the Moon."),
        "method.html": doc_page(site, "method", "Method",
                                "How this section is put together, where the information comes from, and what it is not.",
                                site.method, "How the Science & Space section is compiled and which sources it uses."),
    }
    for items, folder in ((site.missions, "MISSIONS"), (site.facilities, "FACILI~1")):
        taken: set[str] = set()
        for i, it in enumerate(items):
            prev_it = items[i - 1] if i > 0 else None
            next_it = items[i + 1] if i + 1 < len(items) else None
            dos = f"C:\\KS\\SCIENCE\\{folder}\\{dos_name(it.id, taken)}.HTM"
            pages[f"{PLURAL[it.kind]}/{it.id}.html"] = item_page(site, it, prev_it, next_it, dos)
    return pages


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report only; do not write anything")
    ap.add_argument("--stamp", metavar="IDS", help="comma-separated card ids, 'results', 'launches', or 'all'")
    ap.add_argument("--today", type=date.fromisoformat, default=date.today())
    ap.add_argument("--space", type=Path, default=ROOT.parent / "space-explorer")
    ap.add_argument("--science", type=Path, default=ROOT.parent / "science-explorer")
    args = ap.parse_args()

    # Without the source repositories every card would look "removed upstream" and
    # science/ would be rebuilt empty. Stop before touching anything.
    for name, repo in (("space-explorer", args.space), ("science-explorer", args.science)):
        if not repo.is_dir():
            print(f"source repository {name} not found at {repo}; nothing was built or stamped.\n"
                  f"science/ stays as last built. Pass --space / --science if it lives elsewhere.",
                  file=sys.stderr)
            return 2

    if args.stamp:
        wanted = {s.strip() for s in args.stamp.split(",") if s.strip()}
        pairs = [(p, args.space / "missions" / p.name) for p in sorted((CONTENT / "missions").glob("*.md"))]
        pairs += [(p, args.science / "facilities" / p.name) for p in sorted((CONTENT / "facilities").glob("*.md"))]
        res = sorted((args.science / "results").glob("*.md"))
        if res:
            pairs.append((CONTENT / "results.md", res[-1]))
        pairs.append((CONTENT / "launches.md", args.space / "launches.md"))
        done = 0
        for en, src in pairs:
            key = en.stem
            if "all" in wanted or key in wanted:
                if not src.exists() or not en.exists():
                    print(f"  ! cannot stamp {en.relative_to(ROOT)} (missing file)")
                    continue
                write_stamp(en, source_hash(src), source_checked(src))
                done += 1
        print(f"stamped {done} file(s)")
        return 0

    # The private exclusion rules keep non-public rows out of the site. Without them
    # such rows could be published, so stop before touching anything.
    if not PRIVATE.exists():
        print(f"{PRIVATE.relative_to(ROOT)} not found (local, git-ignored exclusion rules); nothing was built.\n"
              f"science/ stays as last built. Restore the file from your own copy.", file=sys.stderr)
        return 2
    private = json.loads(PRIVATE.read_text(encoding="utf-8"))
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    site = Site(cfg, args.today, args.space, args.science, private.get("exclude", []))
    site.load()

    counts = {k: sum(e.bucket == k for e in site.events) for k, _, _ in CAL_SECTIONS}
    print(f"missions {len(site.missions)}, facilities {len(site.facilities)}, "
          f"events {len(site.events)} ({', '.join(f'{k} {v}' for k, v in counts.items())}); today = {args.today}")
    for p in site.problems:
        print(f"  ! {p}")
    for x in site.untranslated:
        print(f"  ! {x}")
    for x in site.stale:
        print(f"  ~ stale: {x}")
    for x in site.excluded:
        print(f"  – excluded: {x}")
    if site.missing:
        print(f"  ! {len(site.missing)} calendar text(s) without translation; these events are left out:")
        for k in site.missing:
            print(f"      {k}")

    pages = build(site)
    if args.check:
        return 1 if (site.missing or site.problems or site.untranslated or site.stale) else 0

    if site.missing:
        CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  → added empty entries to {CONFIG.relative_to(ROOT)}; fill them in and run again")

    if OUT.exists():
        shutil.rmtree(OUT)                       # generated folder: rebuilt from scratch
    for name, text in pages.items():
        path = OUT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    home = HOME.read_text(encoding="utf-8")
    HOME.write_text(replace_block(home, "next", countdown_html(site, 0)), encoding="utf-8")
    print(f"  wrote {len(pages)} pages to science/ and the teaser in index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
