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
WORKS = ("jgb", "gm", "ac", "gd", "fw", "za", "eh", "nf")
LEGACY_REVIEWED_WORKS = {"jgb", "gm", "ac", "gd", "fw"}
ORDINAL_CONTINUATION_RE = re.compile(
    r"^(?:Jahrhundert(?:s|e|en)?|"
    r"Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\b"
)


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

    extended_manifest = json.loads(
        (ROOT / "sources" / "extended_sources.json").read_text(encoding="utf-8")
    )
    if extended_manifest.get("commit") != "2e7114646ef4cff4010a736a35efa32aad71fe75":
        fail("unexpected extended source snapshot commit")
    if len(extended_manifest.get("files", [])) != 42:
        fail("extended source manifest must describe 42 files")
    for descriptor in extended_manifest["files"]:
        source_path = ROOT / descriptor["file"]
        if not source_path.is_file():
            fail(f"missing extended source snapshot {descriptor['file']}")
        actual_hash = hashlib.sha256(source_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if actual_hash != descriptor["sha256"]:
            fail(f"extended source hash mismatch for {descriptor['file']}")


def check_section_coverage(sections: dict[str, set[tuple[str, str]]]) -> None:
    jgb_numbered = {section for _, section in sections["jgb"] if section[0].isdigit()}
    expected_jgb = numbered(1, 296) | {"65a", "73a", "237a"}
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

    za_expected_counts = {"I": 34, "II": 23, "III": 61, "IV": 59}
    for part, expected_count in za_expected_counts.items():
        found = {section for found_part, section in sections["za"] if found_part == part}
        if len(found) != expected_count:
            fail(f"ZA {part} section coverage mismatch: {len(found)}/{expected_count}")

    eh_expected_counts = {
        "Vorspruch": 1, "Vorwort": 4, "Weise": 8, "Klug": 10, "Bücher": 6,
        "GT": 4, "Unzeitgemaesse": 3, "MA": 6, "M": 2, "FW": 1, "Za": 8,
        "JGB": 2, "GM": 1, "GD": 3, "WA": 4, "Schicksal": 9,
    }
    for part, expected_count in eh_expected_counts.items():
        found = {section for found_part, section in sections["eh"] if found_part == part}
        if len(found) != expected_count:
            fail(f"EH {part} section coverage mismatch: {len(found)}/{expected_count}")

    nf_sections = sections["nf"]
    if len({part for part, _ in nf_sections}) != 37 or len(nf_sections) != 2_644:
        fail("late Nachlass group or fragment coverage mismatch")
    if any(not re.fullmatch(r"188[5-8]-\d+", part) for part, _ in nf_sections):
        fail("invalid late Nachlass group key")
    if any(not re.fullmatch(r"\d+\[\d+\]", section) for _, section in nf_sections):
        fail("invalid late Nachlass fragment citation")


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

    if len(quotes) < 17_900:
        fail(f"expected at least 17,900 quote units, found {len(quotes)}")
    if manifest.get("quoteCount") != len(quotes):
        fail("manifest quoteCount does not match quotes.json")
    check_source_hashes(source_manifest)

    ids: set[str] = set()
    translated_ids: set[str] = set()
    sections: dict[str, set[tuple[str, str]]] = defaultdict(set)
    work_counts: Counter[str] = Counter()
    preserved_short_ids = {"jgb-256-cb5b5089f133"}
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
        if len(quote["german"]) < 24 and quote["id"] not in preserved_short_ids:
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
    for current, following in zip(quotes, quotes[1:]):
        same_paragraph = all(
            current[field] == following[field]
            for field in ("work", "part", "section", "paragraph")
        )
        if (
            current["work"] in {"za", "eh", "nf"}
            and same_paragraph
            and re.search(r"\b\d{1,2}\.$", current["german"])
            and ORDINAL_CONTINUATION_RE.match(following["german"])
        ):
            fail(
                f"split German ordinal across quote boundary: "
                f"{current['id']} -> {following['id']}"
            )
        if (
            current["work"] in {"za", "eh", "nf"}
            and same_paragraph
            and re.search(r"\bV[.]$", current["german"])
        ):
            fail(
                f"split abbreviated name across quote boundary: "
                f"{current['id']} -> {following['id']}"
            )
    joined_boundaries = ("Obhutzeigte", "Wagner’sgehabt")
    if any(
        token in quote["german"]
        for quote in quotes
        for token in joined_boundaries
    ):
        fail("joined eKGWB emphasis boundary remains in German corpus")

    eh_venice = [
        quote for quote in quotes
        if quote["work"] == "eh" and quote["part"] == "Klug" and quote["section"] == "7"
    ]
    verse_units = [
        quote["german"] for quote in eh_venice
        if "An der Brücke stand" in quote["german"]
        or "Meine Seele, ein Saitenspiel" in quote["german"]
    ]
    expected_verse_lines = (
        "An der Brücke stand", "jüngst ich in brauner Nacht.",
        "Fernher kam Gesang:", "goldener Tropfen quoll’s",
        "über die zitternde Fläche weg.", "Gondeln, Lichter, Musik —",
        "trunken schwamm’s in die Dämmrung hinaus…",
        "Meine Seele, ein Saitenspiel,", "sang sich, unsichtbar berührt,",
        "heimlich ein Gondellied dazu,", "zitternd vor bunter Seligkeit.",
        "— Hörte Jemand ihr zu?…",
    )
    if len(verse_units) != 2 or any(
        line not in " ".join(verse_units) for line in expected_verse_lines
    ):
        fail("EH-Klug §7 Venice poem is incomplete or incorrectly packed")
    eh_klug_nine = [
        quote for quote in quotes
        if quote["work"] == "eh" and quote["part"] == "Klug" and quote["section"] == "9"
    ]
    if any(
        quote["german"].count("(") != quote["german"].count(")")
        for quote in eh_klug_nine
    ):
        fail("EH-Klug §9 contains an independently displayed unbalanced aside")
    eh_reader_verse = [
        quote["german"] for quote in quotes
        if quote["work"] == "eh" and quote["part"] == "Bücher"
        and quote["section"] == "3" and "Euch, den kühnen Suchern" in quote["german"]
    ]
    if len(eh_reader_verse) != 1 or any(
        line not in eh_reader_verse[0]
        for line in (
            "Euch, den kühnen Suchern", "euch, den Räthsel-Trunkenen",
            "wo ihr errathen könnt, da hasst ihr es, zu erschliessen",
        )
    ):
        fail("EH-Bücher §3 reader verse is incomplete or incorrectly packed")
    chastity_quote = [
        quote["german"] for quote in quotes
        if quote["work"] == "eh" and quote["part"] == "Bücher"
        and quote["section"] == "5" and "die Predigt der Keuschheit" in quote["german"]
    ]
    if (
        len(chastity_quote) != 1
        or "heiligen Geist des Lebens.“" not in chastity_quote[0]
    ):
        fail("EH-Bücher §5 chastity quotation is split or incomplete")
    eh_january_verse = [
        quote for quote in quotes
        if quote["work"] == "eh" and quote["part"] == "FW"
        and "Der du mit dem Flammenspeere" in quote["german"]
    ]
    expected_january_lines = (
        "Der du mit dem Flammenspeere", "Meiner Seele Eis zertheilt,",
        "Dass sie brausend nun zum Meere", "Ihrer höchsten Hoffnung eilt:",
        "Heller stets und stets gesunder,", "Frei im liebevollsten Muss —",
        "Also preist sie deine Wunder,", "Schönster Januarius!",
    )
    if (
        len(eh_january_verse) != 1
        or any(line not in eh_january_verse[0]["german"] for line in expected_january_lines)
        or eh_january_verse[0]["paragraphCount"] != 3
    ):
        fail("EH-FW January poem is incomplete or incorrectly packed")
    if cache_ids != translated_ids:
        fail(
            "translation cache ID mismatch: "
            f"missing={len(translated_ids - cache_ids)}, orphaned={len(cache_ids - translated_ids)}"
        )
    widget_quotes = json.loads((DATA / "widget.json").read_text(encoding="utf-8"))
    widget_ids = {quote["id"] for quote in widget_quotes}
    if widget_ids != translated_ids or len(widget_quotes) != len(translated_ids):
        fail("widget data must contain every translated quote exactly once")
    if manifest.get("widgetQuoteCount") != len(widget_quotes):
        fail("manifest widgetQuoteCount does not match widget.json")
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
    legacy_count = sum(quote["work"] in LEGACY_REVIEWED_WORKS for quote in quotes)
    legacy_reviewed = sum(
        quote["work"] in LEGACY_REVIEWED_WORKS and quote.get("translationStatus") == "reviewed"
        for quote in quotes
    )
    if legacy_reviewed != legacy_count:
        fail(f"previously reviewed corpus regressed: {legacy_reviewed}/{legacy_count}")
    if manifest.get("pendingTranslationCount") != len(quotes) - len(translated_ids):
        fail("manifest pendingTranslationCount does not match pending records")

    jgb_237a = [
        quote
        for quote in quotes
        if quote["id"] == "jgb-237-243eadd853a7"
    ]
    if (
        len(jgb_237a) != 1
        or jgb_237a[0]["section"] != "237a"
        or not jgb_237a[0]["sourceUrl"].endswith("/JGB-237a")
    ):
        fail("JGB 237a display citation or legacy stable ID mismatch")

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
