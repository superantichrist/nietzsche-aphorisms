#!/usr/bin/env python3
"""Re-download the pinned source snapshots and verify SHA-256."""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw"

SOURCES = (
    (
        "jgb-ekgwb-mirror.md",
        "https://raw.githubusercontent.com/uva39/Nietzsche-KR-Translation/2e7114646ef4cff4010a736a35efa32aad71fe75/%EB%8F%85%EC%9D%BC%EC%96%B4%20%ED%85%8D%EC%8A%A4%ED%8A%B8/%EA%B3%B5%EA%B0%9C%20%EC%B6%9C%ED%8C%90/Jenseits%20von%20Gut%20und%20B%C3%B6se.md",
        "37fba1a47cbab03e55efc5a321a071a9f2d8c89743f1de4b9adc144f9875d73d",
    ),
    (
        "gm-uva39.md",
        "https://raw.githubusercontent.com/uva39/Nietzsche-KR-Translation/2e7114646ef4cff4010a736a35efa32aad71fe75/%EB%8F%85%EC%9D%BC%EC%96%B4%20%ED%85%8D%EC%8A%A4%ED%8A%B8/%EA%B3%B5%EA%B0%9C%20%EC%B6%9C%ED%8C%90/Zur%20Genealogie%20der%20Moral.md",
        "cf005ec3643477a6eb1a7b05e2f19983d89d33138847b94f476b3f165ff1e0cb",
    ),
    (
        "jgb-gutenberg-7204.txt",
        "https://www.gutenberg.org/cache/epub/7204/pg7204.txt",
        "0fb771d68ec489ba9d8b9fcda2f53e59ee12057da2c16b2556515a50847fa30f",
    ),
    (
        "gm-1892-ocr.txt",
        "https://archive.org/download/zurgenealogieder00niet/zurgenealogieder00niet_djvu.txt",
        "0d64d5380ed3e3f213f16879dfce97928357100ad1e7d57da24df4d5e416b218",
    ),
    (
        "ac-ekgwb-mirror.md",
        "https://raw.githubusercontent.com/uva39/Nietzsche-KR-Translation/2e7114646ef4cff4010a736a35efa32aad71fe75/%EB%8F%85%EC%9D%BC%EC%96%B4%20%ED%85%8D%EC%8A%A4%ED%8A%B8/%EA%B3%B5%EC%8B%9D%20%EC%9C%A0%EA%B3%A0/Der%20Antichrist.md",
        "34e88fbcd5f7a69d0c38856f4cb99edaf38474b6e7bd4d14c3704e77cf634d10",
    ),
    (
        "gd-ekgwb-mirror.md",
        "https://raw.githubusercontent.com/uva39/Nietzsche-KR-Translation/2e7114646ef4cff4010a736a35efa32aad71fe75/%EB%8F%85%EC%9D%BC%EC%96%B4%20%ED%85%8D%EC%8A%A4%ED%8A%B8/%EA%B3%B5%EA%B0%9C%20%EC%B6%9C%ED%8C%90/G%C3%B6tzen-D%C3%A4mmerung.md",
        "6c0ccf9876a4470d884451bd3af66ae90486d90d265134488d573ae17510c88f",
    ),
    (
        "fw-ekgwb-mirror.md",
        "https://raw.githubusercontent.com/uva39/Nietzsche-KR-Translation/2e7114646ef4cff4010a736a35efa32aad71fe75/%EB%8F%85%EC%9D%BC%EC%96%B4%20%ED%85%8D%EC%8A%A4%ED%8A%B8/%EA%B3%B5%EA%B0%9C%20%EC%B6%9C%ED%8C%90/Die%20fr%C3%B6hliche%20Wissenschaft.md",
        "54b699c99e87a61d5a0b3095a936e0263a7449c739a621242dda3d1e60d0a2a9",
    ),
)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for filename, url, expected in SOURCES:
        request = urllib.request.Request(url, headers={"User-Agent": "nietzsche-aphorisms-source-fetch/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                content = response.read()
        except urllib.error.URLError:
            existing = RAW / filename
            if not existing.exists() or hashlib.sha256(existing.read_bytes()).hexdigest() != expected:
                raise
            print(f"Network unavailable; retained verified {filename}: {expected}")
            continue
        actual = hashlib.sha256(content).hexdigest()
        if actual != expected:
            raise SystemExit(f"Hash mismatch for {filename}: expected {expected}, got {actual}")
        (RAW / filename).write_bytes(content)
        print(f"Verified {filename}: {actual}")


if __name__ == "__main__":
    main()
