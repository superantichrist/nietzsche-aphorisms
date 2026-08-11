#!/usr/bin/env python3
"""Validate corpus structure, IDs, source coverage, and quote sizing."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
WORKS = ("jgb", "gm", "ac", "gd", "fw")


def fail(message: str) -> None:
    raise SystemExit(f"Validation failed: {message}")


def numbered(start: int, end: int) -> set[str]:
    return {str(value) for value in range(start, end + 1)}


def check_source_hashes(source_manifest: dict) -> None:
    for work in WORKS:
        for role in ("buildInput", "crossCheck"):
            descriptor = source_manifest["works"][work].get(role, {})
            if "file" not in descriptor:
                continue
            source_path = ROOT / descriptor["file"]
            if not source_path.is_file():
                fail(f"missing source snapshot {descriptor['file']}")
            normalized_source = source_path.read_bytes().replace(b"\r\n", b"\n")
            actual_hash = hashlib.sha256(normalized_source).hexdigest()
            expected_hash = descriptor.get("normalizedSha256", descriptor["sha256"])
            if actual_hash != expected_hash:
                fail(f"source hash mismatch for {descriptor['file']}")


def check_section_coverage(sections: dict[str, set[tuple[str, str]]]) -> None:
    jgb_numbered = {section for _, section in sections["jgb"] if section[0].isdigit()}
    expected_jgb = numbered(1, 296) | {"65a", "73a"}
    if jgb_numbered != expected_jgb:
        fail("JGB numbered section coverage mismatch")

    gm_expected = {"Vorrede": 8, "I": 17, "II": 25, "III": 28}
    for part, expected_count in gm_expected.items():
        found = {section for found_part, section in sections["gm"] if found_part == part}
        if found != numbered(1, expected_count):
            fail(f"GM {part} section coverage mismatch")

    ac_expected = {
        "Vorrede": {"Vorrede"},
        "Haupttext": numbered(1, 62),
        "Anhang": {"Gesetz"},
    }
    gd_expected = {
        "Vorrede": {"Vorrede"},
        "Sprueche": numbered(1, 44),
        "Sokrates": numbered(1, 12),
        "Vernunft": numbered(1, 6),
        "Wahre-Welt": {"Wahre-Welt"},
        "Moral": numbered(1, 6),
        "Irrthuemer": numbered(1, 8),
        "Verbesserer": numbered(1, 5),
        "Deutschen": numbered(1, 7),
        "Streifzuege": numbered(1, 51),
        "Alten": numbered(1, 5),
        "Hammer": {"Hammer"},
    }
    fw_expected = {
        "Vorrede": numbered(1, 4),
        "Vorspiel": numbered(1, 63),
        "I": numbered(1, 56),
        "II": numbered(57, 107),
        "III": numbered(108, 275),
        "IV": numbered(276, 342),
        "V": numbered(343, 383),
        "Anhang": numbered(1, 14),
    }
    for work, expected in (("ac", ac_expected), ("gd", gd_expected), ("fw", fw_expected)):
        for part, expected_sections in expected.items():
            found = {section for found_part, section in sections[work] if found_part == part}
            if found != expected_sections:
                fail(
                    f"{work.upper()} {part} section coverage mismatch: "
                    f"missing={sorted(expected_sections - found)[:8]}, "
                    f"extra={sorted(found - expected_sections)[:8]}"
                )


def main() -> None:
    quotes = json.loads((DATA / "quotes.json").read_text(encoding="utf-8"))
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    translation_cache = json.loads(
        (ROOT / "translations" / "ko.json").read_text(encoding="utf-8")
    )["translations"]
    source_manifest = json.loads((ROOT / "sources" / "sources.json").read_text(encoding="utf-8"))
    required = {
        "id", "work", "workTitleDe", "workTitleKo", "part", "section",
        "paragraph", "paragraphCount", "sentence", "german", "korean", "footnotes",
    }

    if len(quotes) < 5_000:
        fail(f"expected at least 5,000 quote units, found {len(quotes)}")
    if manifest.get("quoteCount") != len(quotes):
        fail("manifest quoteCount does not match quotes.json")
    check_source_hashes(source_manifest)

    ids: set[str] = set()
    translated_ids: set[str] = set()
    sections: dict[str, set[tuple[str, str]]] = defaultdict(set)
    work_counts: Counter[str] = Counter()
    for index, quote in enumerate(quotes):
        missing = required - quote.keys()
        if missing:
            fail(f"record {index} missing {sorted(missing)}")
        if quote["id"] in ids:
            fail(f"duplicate ID {quote['id']}")
        ids.add(quote["id"])
        if quote["work"] not in WORKS:
            fail(f"invalid work {quote['work']}")
        if not isinstance(quote["paragraph"], int) or quote["paragraph"] < 0:
            fail(f"invalid paragraph in {quote['id']}")
        if not isinstance(quote["paragraphCount"], int) or quote["paragraphCount"] < 1:
            fail(f"invalid paragraph count in {quote['id']}")
        if quote["paragraph"] >= quote["paragraphCount"]:
            fail(f"paragraph exceeds paragraph count in {quote['id']}")
        if not isinstance(quote["sentence"], int) or quote["sentence"] < 0:
            fail(f"invalid sentence in {quote['id']}")
        if len(quote["german"]) < 24:
            fail(f"too-short German unit {quote['id']}: {quote['german']!r}")
        if len(quote["german"]) > 700:
            fail(f"too-long German unit {quote['id']}: {len(quote['german'])} chars")
        if not quote.get("sourceUrl", "").startswith("https://www.nietzschesource.org/"):
            fail(f"missing canonical source URL in {quote['id']}")
        if not isinstance(quote["footnotes"], list):
            fail(f"invalid footnotes in {quote['id']}")
        for footnote in quote["footnotes"]:
            if (
                not isinstance(footnote, dict)
                or not isinstance(footnote.get("label"), str)
                or not footnote["label"].strip()
                or not isinstance(footnote.get("text"), str)
                or not footnote["text"].strip()
            ):
                fail(f"invalid footnote in {quote['id']}")

        korean = quote["korean"].strip()
        if korean:
            translated_ids.add(quote["id"])
            if not re.search(r"[가-힣]", korean):
                fail(f"Korean translation has no Hangul in {quote['id']}")
            if quote.get("translationStatus") not in {"draft", "reviewed"}:
                fail(f"invalid translated status in {quote['id']}")
        elif quote.get("translationStatus") != "pending":
            fail(f"missing translation is not marked pending in {quote['id']}")

        sections[quote["work"]].add((quote["part"], str(quote["section"])))
        work_counts[quote["work"]] += 1

    cache_ids = set(translation_cache)
    if cache_ids != translated_ids:
        fail(
            "translation cache ID mismatch: "
            f"missing={len(translated_ids - cache_ids)}, orphaned={len(cache_ids - translated_ids)}"
        )
    for quote_id, translation in translation_cache.items():
        if not translation.get("korean", "").strip():
            fail(f"blank translation cache entry {quote_id}")
        if translation.get("status") not in {"draft", "reviewed"}:
            fail(f"invalid translation cache status {quote_id}")

    if manifest.get("translatedCount") != len(translated_ids):
        fail("manifest translatedCount does not match translated records")
    reviewed_count = sum(quote.get("translationStatus") == "reviewed" for quote in quotes)
    if manifest.get("reviewedCount") != reviewed_count:
        fail("manifest reviewedCount does not match reviewed records")
    if manifest.get("pendingTranslationCount") != len(quotes) - len(translated_ids):
        fail("manifest pendingTranslationCount does not match pending records")

    for work in WORKS:
        work_file = json.loads((DATA / f"{work}.json").read_text(encoding="utf-8"))
        expected_records = [quote for quote in quotes if quote["work"] == work]
        if work_file != expected_records:
            fail(f"data/{work}.json does not match quotes.json")
        if manifest["works"][work]["count"] != len(work_file):
            fail(f"manifest count mismatch for {work}")
        expected_reviewed = sum(
            quote.get("translationStatus") == "reviewed" for quote in work_file
        )
        if manifest["works"][work].get("reviewedCount") != expected_reviewed:
            fail(f"manifest reviewedCount mismatch for {work}")

    check_section_coverage(sections)
    counts = ", ".join(f"{work.upper()} {work_counts[work]:,}" for work in WORKS)
    print(
        f"Validated {len(quotes):,} unique quotes ({counts}); "
        f"Korean {len(translated_ids):,}, pending {len(quotes) - len(translated_ids):,}."
    )


if __name__ == "__main__":
    main()
