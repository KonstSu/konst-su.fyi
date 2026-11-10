#!/usr/bin/env python3
"""
Prepare a photo for the site: resize, convert to JPEG, apply the EXIF rotation,
and strip all metadata (camera, phone model, date, GPS, XMP, IPTC, comments).

    python3 tools/prepare_photo.py ~/Pictures/IMG_1234.HEIC assets/img/new-photo.jpg
    python3 tools/prepare_photo.py SRC DST --max 640          # portrait: longest side 640 px
    python3 tools/prepare_photo.py SRC DST --quality 70

Defaults: longest side 880 px (two figures side by side on Projects), JPEG quality 62,
which keeps a typical photo at 80–250 KB. Prints the width/height attributes for
the <img> tag. Uses macOS `sips`; keeps only JFIF and the ICC colour profile.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROTATE = {3: ["-r", "180"], 6: ["-r", "90"], 8: ["-r", "270"],
          2: ["-f", "horizontal"], 4: ["-f", "vertical"],
          5: ["-r", "90", "-f", "horizontal"], 7: ["-r", "270", "-f", "horizontal"]}


def exif_orientation(data: bytes) -> int:
    """EXIF orientation of a JPEG (1 = as stored, or no EXIF)."""
    i = 2
    while i + 4 <= len(data) and data[i] == 0xFF:
        m = data[i + 1]
        if m == 0xDA:
            break
        n = int.from_bytes(data[i + 2:i + 4], "big")
        seg = data[i + 4:i + 2 + n]
        if m == 0xE1 and seg[:6] == b"Exif\0\0":
            t = seg[6:]
            bo = "little" if t[:2] == b"II" else "big"
            ifd = int.from_bytes(t[4:8], bo)
            for k in range(int.from_bytes(t[ifd:ifd + 2], bo)):
                e = t[ifd + 2 + 12 * k: ifd + 14 + 12 * k]
                if int.from_bytes(e[:2], bo) == 0x0112:
                    return int.from_bytes(e[8:10], bo)
            return 1
        i += 2 + n
    return 1


def strip(data: bytes) -> bytes:
    """Keep SOI, JFIF (APP0), the ICC profile (APP2), tables and image data; drop the rest."""
    assert data[:2] == b"\xff\xd8", "not a JPEG"
    out, i = bytearray(b"\xff\xd8"), 2
    while i < len(data):
        assert data[i] == 0xFF, f"broken JPEG segment at byte {i}"
        m = data[i + 1]
        if m == 0xDA:
            out += data[i:]
            break
        n = int.from_bytes(data[i + 2:i + 4], "big")
        seg = data[i:i + 2 + n]
        meta = 0xE1 <= m <= 0xEF or m == 0xFE
        if not meta or (m == 0xE2 and seg[4:15] == b"ICC_PROFILE"):
            out += seg
        i += 2 + n
    return bytes(out)


def size(data: bytes) -> tuple[int, int]:
    i = 2
    while i + 9 <= len(data):
        m = data[i + 1]
        n = int.from_bytes(data[i + 2:i + 4], "big")
        if m in (0xC0, 0xC1, 0xC2):
            return int.from_bytes(data[i + 7:i + 9], "big"), int.from_bytes(data[i + 5:i + 7], "big")
        i += 2 + n
    raise ValueError("no frame header")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--max", type=int, default=880, help="longest side in px (default 880)")
    ap.add_argument("--quality", type=int, default=62, help="JPEG quality 1–100 (default 62)")
    args = ap.parse_args()
    if not shutil.which("sips"):
        raise SystemExit("sips not found (macOS only)")
    if args.dst.suffix.lower() not in (".jpg", ".jpeg"):
        raise SystemExit("destination must be a .jpg file")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work.jpg"
        subprocess.run(["sips", "-s", "format", "jpeg", str(args.src), "--out", str(work)],
                       check=True, capture_output=True)
        o = exif_orientation(work.read_bytes())
        if o in ROTATE:
            subprocess.run(["sips", *ROTATE[o], str(work)], check=True, capture_output=True)
        subprocess.run(["sips", "-Z", str(args.max), "-s", "format", "jpeg",
                        "-s", "formatOptions", str(args.quality), str(work)],
                       check=True, capture_output=True)
        data = strip(work.read_bytes())
    args.dst.parent.mkdir(parents=True, exist_ok=True)
    args.dst.write_bytes(data)
    w, h = size(data)
    print(f"{args.dst}: {w}×{h}, {len(data) // 1024} KB, metadata stripped"
          + (f", rotated (EXIF orientation {o})" if o in ROTATE else ""))
    print(f'<img src="{args.dst.as_posix()}" width="{w}" height="{h}" alt="…" loading="lazy" decoding="async">')
    return 0


if __name__ == "__main__":
    sys.exit(main())
