#!/usr/bin/env python3
"""Vendor the pinned eKGWB mirror snapshots for Za, EH, and late Nachlass."""

from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw"
COMMIT = "2e7114646ef4cff4010a736a35efa32aad71fe75"
REPOSITORY = "uva39/Nietzsche-KR-Translation"
RAW_BASE = f"https://raw.githubusercontent.com/{REPOSITORY}/{COMMIT}/"


def source_specs() -> list[tuple[str, str]]:
    specs = [
        ("za-i-ekgwb-mirror.md", "독일어 텍스트/공개 출판/Also sprach Zarathustra I.md"),
        ("za-ii-ekgwb-mirror.md", "독일어 텍스트/공개 출판/Also sprach Zarathustra II.md"),
        ("za-iii-ekgwb-mirror.md", "독일어 텍스트/공개 출판/Also sprach Zarathustra III.md"),
        ("za-iv-ekgwb-mirror.md", "독일어 텍스트/미공개 출판/Also sprach Zarathustra IV.md"),
        ("eh-ekgwb-mirror.md", "독일어 텍스트/공식 유고/Ecce Homo.md"),
    ]
    groups = {
        1885: [1, 2, *range(34, 46)],
        1886: range(3, 8),
        1887: range(8, 12),
        1888: range(12, 26),
    }
    for year, numbers in groups.items():
        for number in numbers:
            specs.append(
                (
                    f"nf-{year}-{number:02d}.md",
                    f"독일어 텍스트/노트 유고/NF {year}, Gruppe {number}.md",
                )
            )
    return specs


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    files = []
    for local_name, repository_path in source_specs():
        url = RAW_BASE + urllib.parse.quote(repository_path, safe="/")
        request = urllib.request.Request(url, headers={"User-Agent": "nietzsche-aphorisms-source-vendor/1"})
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read()
        target = RAW / local_name
        target.write_bytes(content)
        files.append(
            {
                "file": target.relative_to(ROOT).as_posix(),
                "repositoryPath": repository_path,
                "acquisitionUrl": url,
                "bytes": len(content),
                "sha256": hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest(),
            }
        )
        print(f"Fetched {local_name} ({len(content):,} bytes)")

    manifest = {
        "schemaVersion": 1,
        "repository": f"https://github.com/{REPOSITORY}",
        "commit": COMMIT,
        "editionBasis": "Digitale Kritische Gesamtausgabe Werke und Briefe (eKGWB)",
        "files": files,
    }
    manifest_path = ROOT / "sources" / "extended_sources.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {manifest_path.relative_to(ROOT)} with {len(files)} pinned files")


if __name__ == "__main__":
    main()
