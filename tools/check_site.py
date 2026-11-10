#!/usr/bin/env python3
"""
Pre-publication checks for the site, and assembly of the folder to upload.

    python3 tools/check_site.py                     # static checks; exit 1 on errors
    python3 tools/check_site.py --strict            # also fail on [confirm]/[missing] markers and placeholders
    python3 tools/check_site.py --layout            # also check horizontal overflow at 360/390/1440 px
    python3 tools/check_site.py --dist              # strict checks, then copy the public files to dist/
    python3 tools/check_site.py --dist --allow-todo # private preview build that keeps the markers

Public files: the root *.html pages, assets/ and science/. Everything else
(README.md, AGENTS.md, CLAUDE.md, content/, data/, tools/) is source material
and is never uploaded.

Static checks:
  - every local link, image, script, stylesheet and #anchor resolves to a public file;
  - no external scripts, stylesheets, fonts or images (fonts are self-hosted);
  - every page has lang, <title>, meta description and the same Content-Security-Policy;
  - rel="canonical" and og:url give the page's own address under SITE; og:image is a public file;
  - no inline <script>/<style>, style="" or on*="" attributes (the CSP blocks them anyway);
  - target="_blank" links carry rel="noopener";
  - every <img> has alt, width and height; JPEG/PNG files carry no EXIF/XMP/IPTC/text metadata;
  - text policy: no protected titles, e-mail addresses or phone numbers; plus the rules for
    internal project codes and non-public European XFEL terms from the local, git-ignored
    data/private.json (a warning if that file is missing, e.g. in CI);
  - [confirm]/[missing] markers and the Web3Forms placeholder (warnings; errors with --strict/--dist).

--layout needs Google Chrome (headless) and serves the site on a random local port.
Standard library only.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIRS = ("assets", "science")
JUNK = {".DS_Store", "Thumbs.db", "desktop.ini"}
DIST_MARK = ".konst-site-dist"
SITE = "https://konst-su.fyi/"   # public address of the site
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
WIDTHS = (360, 390, 1440)

# (pattern, reason, scope) — scope "all" = every public page, "own" = pages about Konstantin
TEXT_RULES = [
    (r"Dipl\.?\s?-?\s?Ing", "protected title (Dipl.-Ing.)", "all"),
    (r"Dr\.-Ing", "protected title (Dr.-Ing.)", "all"),
    (r"\bIngenieur\b", "protected title (Ingenieur)", "all"),
    (r"\bDr\.?\s+(?:K\.|Konstantin|Sukharnikov)", "title 'Dr.' with the owner's name", "all"),
    (r"Sukharnikov,?\s+(?:PhD|Ph\.D\.|Dr)\b", "'PhD'/'Dr' used as a title", "all"),
    (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}", "e-mail address (contact goes through the form and LinkedIn)", "all"),
    (r"(?<![\w/.=-])\+\d[\d ()/-]{8,}\d", "phone number", "all"),
]
PRIVATE = ROOT / "data" / "private.json"   # local only, never committed


def private_rules(r: "Report") -> list[tuple[str, str, str]]:
    """Text rules that would reveal non-public information if they were tracked in git."""
    if not PRIVATE.exists():
        r.warn(f"{PRIVATE.relative_to(ROOT)} not found: private text rules (internal codes, non-public XFEL terms) not checked")
        return []
    data = json.loads(PRIVATE.read_text(encoding="utf-8"))
    return [(x["pattern"], x["reason"], "all") for x in data.get("text_rules", [])]


TODO_RE = re.compile(r"\[(?:confirm|missing)\b[^\]]*\]")
PLACEHOLDER = "YOUR_WEB3FORMS_KEY"


def is_junk(p: Path) -> bool:
    return p.name in JUNK or p.name.startswith("._") or "__pycache__" in p.parts


def public_files() -> list[Path]:
    files = sorted(ROOT.glob("*.html"))
    for d in PUBLIC_DIRS:
        files += sorted(p for p in (ROOT / d).rglob("*") if p.is_file() and not is_junk(p))
    return files


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.refs: list[tuple[str, str, int]] = []      # (tag, url, line)
        self.imgs: list[tuple[int, dict]] = []
        self.csp = self.title = self.desc = self.lang = None
        self.canonical = self.og_url = self.og_image = None
        self.inline_scripts: list[int] = []
        self.style_tags: list[int] = []
        self.style_attrs: list[int] = []
        self.handlers: list[int] = []
        self.no_noopener: list[int] = []
        self.todo: list[int] = []
        self.text: list[str] = []
        self._skip = False
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        line = self.getpos()[0]
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and "name" in a:
            self.ids.add(a["name"])
        if tag == "html":
            self.lang = a.get("lang")
        if "style" in a:
            self.style_attrs.append(line)
        if any(k.startswith("on") for k in a):
            self.handlers.append(line)
        if "todo" in a.get("class", "").split():
            self.todo.append(line)
        if tag == "meta":
            if a.get("http-equiv", "").lower() == "content-security-policy":
                self.csp = a.get("content", "")
            if a.get("name") == "description":
                self.desc = a.get("content", "")
            if a.get("property") == "og:url":
                self.og_url = a.get("content", "")
            if a.get("property") == "og:image":
                self.og_image = a.get("content", "")
        elif tag == "title":
            self._in_title = True
            self.title = ""
        elif tag == "script":
            if a.get("src"):
                self.refs.append(("script", a["src"], line))
            elif a.get("type") != "application/ld+json":
                self.inline_scripts.append(line)
            self._skip = True
        elif tag == "style":
            self.style_tags.append(line)
            self._skip = True
        elif tag == "link" and "canonical" in a.get("rel", "").split():
            self.canonical = a.get("href", "")
        elif tag == "link" and a.get("href"):
            self.refs.append(("link", a["href"], line))
        elif tag == "a" and "href" in a:
            self.refs.append(("a", a["href"], line))
            if a.get("target") == "_blank" and "noopener" not in a.get("rel", "").split():
                self.no_noopener.append(line)
        elif tag == "form" and a.get("action"):
            self.refs.append(("form", a["action"], line))
        if tag in ("img", "source", "iframe", "video", "audio", "embed") and a.get("src"):
            self.refs.append((tag, a["src"], line))
        if tag == "img":
            self.imgs.append((line, a))

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if not self._skip:
            self.text.append(data)


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def jpeg_metadata(data: bytes) -> list[str]:
    """Names of metadata segments in a JPEG (empty list = clean)."""
    if data[:2] != b"\xff\xd8":
        return ["not a JPEG"]
    found, i = [], 2
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            return found + ["broken segment structure"]
        m = data[i + 1]
        if m == 0xDA:                     # start of scan: image data follows
            break
        length = int.from_bytes(data[i + 2:i + 4], "big")
        seg = data[i + 4:i + 2 + length]
        if m == 0xE1:
            found.append("XMP" if seg.startswith(b"http://ns.adobe.com") else "EXIF")
        elif m == 0xED:
            found.append("IPTC")
        elif m == 0xFE:
            found.append("comment")
        elif 0xE3 <= m <= 0xEF and m != 0xEE:
            found.append(f"APP{m - 0xE0}")
        i += 2 + length
    return found


def png_metadata(data: bytes) -> list[str]:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return ["not a PNG"]
    found, i = [], 8
    while i + 8 <= len(data):
        n = int.from_bytes(data[i:i + 4], "big")
        kind = data[i + 4:i + 8].decode("latin-1")
        if kind in ("tEXt", "iTXt", "zTXt", "eXIf", "tIME"):
            found.append(kind)
        i += 12 + n
    return found


def check_static(r: Report, strict: bool) -> dict[Path, Page]:
    files = public_files()
    public = {p.resolve() for p in files}
    rules = TEXT_RULES + private_rules(r)
    pages: dict[Path, Page] = {}
    for p in files:
        if p.suffix == ".html":
            pg = Page()
            pg.feed(p.read_text(encoding="utf-8"))
            pages[p.resolve()] = pg

    # junk inside public folders (would be uploaded by a careless copy, never by --dist)
    for d in PUBLIC_DIRS:
        for j in (q for q in (ROOT / d).rglob("*") if q.is_file() and is_junk(q)):
            r.warn(f"{rel(j)}: system file inside a public folder (left out of dist/)")

    csp_ref = pages.get((ROOT / "index.html").resolve())
    csp_ref = csp_ref.csp if csp_ref else None
    todo_total, todo_pages = 0, []
    for path, pg in pages.items():
        name = rel(path)
        if not pg.lang:
            r.err(f"{name}: <html> without lang")
        if not (pg.title or "").strip():
            r.err(f"{name}: no <title>")
        if not pg.desc:
            r.err(f"{name}: no meta description")
        if not pg.csp:
            r.err(f"{name}: no Content-Security-Policy meta")
        elif pg.csp != csp_ref:
            r.err(f"{name}: Content-Security-Policy differs from index.html")
        for what, lines in (("inline <script>", pg.inline_scripts), ("<style> element", pg.style_tags),
                            ("style=\"\" attribute", pg.style_attrs), ("on*=\"\" handler", pg.handlers)):
            if lines:
                r.err(f"{name}:{lines[0]}: {what} ({len(lines)}×); the CSP blocks it — use assets/css or assets/js")
        own = SITE + ("" if name == "index.html" else name)
        if pg.canonical != own:
            r.err(f"{name}: rel=\"canonical\" is {pg.canonical!r}, expected {own!r}")
        if pg.og_url is not None and pg.og_url != own:
            r.err(f"{name}: og:url is {pg.og_url!r}, expected {own!r}")
        if pg.og_image is not None:
            img = ROOT / pg.og_image[len(SITE):] if pg.og_image.startswith(SITE) else None
            if img is None or not img.is_file() or img.resolve() not in public:
                r.err(f"{name}: og:image {pg.og_image!r} is not a public file under {SITE}")
        for line in pg.no_noopener:
            r.err(f"{name}:{line}: target=\"_blank\" without rel=\"noopener\"")
        for line, a in pg.imgs:
            if "alt" not in a:
                r.err(f"{name}:{line}: <img> without alt")
            if not a.get("width") or not a.get("height"):
                r.err(f"{name}:{line}: <img> without width/height (layout shift)")

        # links and resources
        for tag, url, line in pg.refs:
            u = urlsplit(url)
            if u.scheme in ("http", "https") or url.startswith("//"):
                if tag in ("script", "link", "img", "source", "iframe", "video", "audio", "embed"):
                    r.err(f"{name}:{line}: external {tag} {url} (everything is self-hosted)")
                if u.scheme == "http":
                    r.warn(f"{name}:{line}: plain http link {url}")
                continue
            if u.scheme in ("mailto", "tel"):
                r.err(f"{name}:{line}: {u.scheme}: link (no personal contact data on the site)")
                continue
            if u.scheme:
                r.err(f"{name}:{line}: unexpected link scheme {url}")
                continue
            if u.path.startswith("/"):
                r.err(f"{name}:{line}: root-relative link {url}; use relative paths")
                continue
            target = (path.parent / unquote(u.path)).resolve() if u.path else path
            if target.is_dir():
                target = target / "index.html"
            if target not in public:
                what = "missing file" if not target.exists() else "points outside the public files"
                r.err(f"{name}:{line}: {url} — {what}")
                continue
            if u.fragment and target.suffix == ".html":
                tp = pages.get(target)
                if tp is not None and unquote(u.fragment) not in tp.ids:
                    r.err(f"{name}:{line}: anchor #{u.fragment} not found in {rel(target)}")

        # text policy
        raw = path.read_text(encoding="utf-8")
        for pat, why, _scope in rules:
            for m in re.finditer(pat, raw):
                line = raw.count("\n", 0, m.start()) + 1
                r.err(f"{name}:{line}: {why}: “{m.group(0)}”")
        markers = len(TODO_RE.findall(" ".join(pg.text)))
        n = max(markers, len(pg.todo))
        if n:
            todo_total += n
            todo_pages.append(f"{name} {n}")
        if PLACEHOLDER in raw:
            (r.err if strict else r.warn)(f"{name}: Web3Forms key is still the placeholder {PLACEHOLDER}")

    if todo_total:
        (r.err if strict else r.warn)(
            f"{todo_total} unresolved [confirm]/[missing] marker(s): {', '.join(sorted(todo_pages))}")

    # stylesheets: url() references must be local and exist
    for css in sorted((ROOT / "assets").rglob("*.css")):
        text = css.read_text(encoding="utf-8")
        for m in re.finditer(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", text):
            url = m.group(1)
            if url.startswith("data:"):
                continue
            if re.match(r"(?:https?:)?//", url):
                r.err(f"{rel(css)}: external url({url})")
                continue
            target = (css.parent / unquote(urlsplit(url).path)).resolve()
            if target not in public:
                r.err(f"{rel(css)}: url({url}) — missing file")
        if "@import" in text:
            r.err(f"{rel(css)}: @import (keep one stylesheet)")

    # images: metadata and size
    for p in files:
        ext = p.suffix.lower()
        if ext in (".jpg", ".jpeg", ".png"):
            data = p.read_bytes()
            meta = jpeg_metadata(data) if ext != ".png" else png_metadata(data)
            if meta:
                r.err(f"{rel(p)}: image metadata present ({', '.join(meta)}); run tools/prepare_photo.py")
            if len(data) > 400_000:
                r.warn(f"{rel(p)}: {len(data) // 1024} KB; aim for ≤ 250 KB")
    return pages


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def check_layout(r: Report, pages: dict[Path, Page]) -> None:
    chrome = Path(CHROME)
    if not chrome.exists():
        r.err(f"--layout: Google Chrome not found at {CHROME}")
        return
    names = sorted(rel(p) for p in pages)
    handler = functools.partial(Quiet, directory=str(ROOT))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = (f"http://127.0.0.1:{srv.server_address[1]}/tools/layout_check.html"
           f"#w={','.join(map(str, WIDTHS))}&p={','.join(names)}")
    try:
        with tempfile.TemporaryDirectory() as prof:
            out = subprocess.run(
                [str(chrome), "--headless=new", "--disable-gpu", "--no-first-run",
                 "--no-default-browser-check", "--hide-scrollbars", f"--user-data-dir={prof}",
                 "--window-size=1500,900", "--virtual-time-budget=600000", "--dump-dom", url],
                capture_output=True, text=True, timeout=600).stdout
    except subprocess.TimeoutExpired:
        r.err("--layout: Chrome timed out")
        return
    finally:
        srv.shutdown()
    m = re.search(r'<pre id="out">(.*?)</pre>', out, re.S)
    if not m or m.group(1).strip() in ("", "pending"):
        r.err("--layout: no result from Chrome")
        return
    lines = [ln for ln in m.group(1).strip().splitlines() if ln.strip()]
    bad = [ln for ln in lines if " OVER " in ln]
    for ln in bad:
        r.err(f"layout: {ln}")
    print(f"layout: {len(lines)} checks ({len(names)} pages × {len(WIDTHS)} widths), {len(bad)} with horizontal overflow")


def make_dist(r: Report, target: Path) -> None:
    target = target.resolve()
    if target == ROOT or ROOT.is_relative_to(target):
        raise SystemExit(f"refusing to use {target} as the output folder")
    if target.exists():
        if any(target.iterdir()) and not (target / DIST_MARK).exists():
            raise SystemExit(f"{target} exists and was not made by this script; choose another folder")
        shutil.rmtree(target)
    files = public_files()
    size = 0
    for p in files:
        dst = target / p.relative_to(ROOT)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst)
        size += p.stat().st_size
    (target / ".nojekyll").write_text("", encoding="utf-8")       # GitHub Pages: serve files as they are
    (target / DIST_MARK).write_text("made by tools/check_site.py --dist; safe to delete\n", encoding="utf-8")
    print(f"dist: {len(files)} files, {size / 1e6:.1f} MB → {rel(target)}/  (upload this folder only)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strict", action="store_true", help="markers and placeholders are errors")
    ap.add_argument("--layout", action="store_true", help="check horizontal overflow in headless Chrome")
    ap.add_argument("--dist", nargs="?", const="dist", metavar="DIR", help="copy public files to DIR (default dist/)")
    ap.add_argument("--allow-todo", action="store_true", help="with --dist: keep markers (private preview only)")
    args = ap.parse_args()

    strict = args.strict or (args.dist is not None and not args.allow_todo)
    r = Report()
    pages = check_static(r, strict)
    if args.layout:
        check_layout(r, pages)

    for w in r.warnings:
        print(f"  ~ {w}")
    for e in r.errors:
        print(f"  ! {e}")
    n_pages = len(pages)
    n_links = sum(len(pg.refs) for pg in pages.values())
    print(f"{n_pages} pages, {n_links} links/resources checked: {len(r.errors)} error(s), {len(r.warnings)} warning(s)")
    if r.errors:
        if args.dist is not None:
            print("dist/ not written: fix the errors first")
        return 1
    if args.dist is not None:
        make_dist(r, ROOT / args.dist if not Path(args.dist).is_absolute() else Path(args.dist))
    return 0


if __name__ == "__main__":
    sys.exit(main())
