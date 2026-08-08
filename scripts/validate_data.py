#!/usr/bin/env python3
"""Validate corpus structure, IDs, source coverage, and quote sizing."""

from __future__ import annotations

import json
import hashlib
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def fail(message: str) -> None:
    raise SystemExit(f"Validation failed: {message}")


def main() -> None:
    quotes = json.loads((DATA / "quotes.json").read_text(encoding="utf-8"))
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    source_manifest = json.loads((ROOT / "sources" / "sources.json").read_text(encoding="utf-8"))
    required = {
        "id", "work", "workTitleDe", "workTitleKo", "part", "section",
        "paragraph", "german", "korean",
    }

    if len(quotes) < 2_000:
        fail(f"expected at least 2,000 quote units, found {len(quotes)}")
    if manifest.get("quoteCount") != len(quotes):
        fail("manifest quoteCount does not match quotes.json")

    for work in ("jgb", "gm"):
        for role in ("buildInput", "crossCheck"):
            descriptor = source_manifest["works"][work][role]
            source_path = ROOT / descriptor["file"]
            normalized_source = source_path.read_bytes().replace(b"\r\n", b"\n")
            actual_hash = hashlib.sha256(normalized_source).hexdigest()
            expected_hash = descriptor.get("normalizedSha256", descriptor["sha256"])
            if actual_hash != expected_hash:
                fail(f"source hash mismatch for {descriptor['file']}")

    ids: set[str] = set()
    sections: dict[str, set[tuple[str, str]]] = defaultdict(set)
    work_counts: Counter[str] = Counter()
    for index, quote in enumerate(quotes):
        missing = required - quote.keys()
        if missing:
            fail(f"record {index} missing {sorted(missing)}")
        if quote["id"] in ids:
            fail(f"duplicate ID {quote['id']}")
        ids.add(quote["id"])
        if quote["work"] not in {"jgb", "gm"}:
            fail(f"invalid work {quote['work']}")
        if not isinstance(quote["paragraph"], int) or quote["paragraph"] < 0:
            fail(f"invalid paragraph in {quote['id']}")
        if len(quote["german"]) < 24:
            fail(f"too-short German unit {quote['id']}: {quote['german']!r}")
        if len(quote["german"]) > 650:
            fail(f"too-long German unit {quote['id']}: {len(quote['german'])} chars")
        if not quote.get("sourceUrl", "").startswith("https://www.nietzschesource.org/"):
            fail(f"missing canonical source URL in {quote['id']}")
        sections[quote["work"]].add((quote["part"], str(quote["section"])))
        work_counts[quote["work"]] += 1

    jgb_numbered = {section for part, section in sections["jgb"] if section[0].isdigit()}
    expected_jgb = {str(i) for i in range(1, 297)} | {"65a", "73a"}
    if jgb_numbered != expected_jgb:
        fail(f"JGB section coverage mismatch: missing={sorted(expected_jgb - jgb_numbered)[:10]}")

    gm_expected = {
        "Vorrede": 8,
        "I": 17,
        "II": 25,
        "III": 28,
    }
    for part, expected_count in gm_expected.items():
        found = {section for found_part, section in sections["gm"] if found_part == part}
        if len(found) != expected_count:
            fail(f"GM {part} expected {expected_count} sections, found {len(found)}")

    print(
        f"Validated {len(quotes):,} unique quotes; "
        f"JGB {work_counts['jgb']:,}, GM {work_counts['gm']:,}; "
        f"{len(sections['jgb'])} / {len(sections['gm'])} source sections."
    )


if __name__ == "__main__":
    main()
