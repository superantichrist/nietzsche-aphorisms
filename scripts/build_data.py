#!/usr/bin/env python3
"""Build stable quote JSON from the two vendored German source texts."""

from __future__ import annotations

import hashlib
import html
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw"
DATA = ROOT / "data"
TRANSLATIONS = ROOT / "translations" / "ko.json"

WORKS = {
    "jgb": {
        "title_de": "Jenseits von Gut und Böse",
        "title_ko": "선악의 저편",
        "source_file": "sources/raw/jgb-ekgwb-mirror.md",
    },
    "gm": {
        "title_de": "Zur Genealogie der Moral",
        "title_ko": "도덕의 계보",
        "source_file": "sources/raw/gm-uva39.md",
    },
}

JGB_PARTS = {
    "Vorrede": ("Vorrede", "서문"),
    "Erstes Hauptstück": ("I", "철학자들의 편견에 관하여"),
    "Zweites Hauptstück": ("II", "자유정신"),
    "Drittes Hauptstück": ("III", "종교적 본성"),
    "Viertes Hauptstück": ("IV", "잠언과 간주곡"),
    "Fünftes Hauptstück": ("V", "도덕의 자연사"),
    "Sechstes Hauptstück": ("VI", "우리 학자들"),
    "Siebentes Hauptstück": ("VII", "우리의 덕"),
    "Achtes Hauptstück": ("VIII", "민족과 조국"),
    "Neuntes Hauptstück": ("IX", "고귀함이란 무엇인가?"),
    "Aus hohen Bergen": ("Nachgesang", "높은 산에서 — 후가"),
}

GM_PARTS = {
    "Vorrede": ("Vorrede", "서문"),
    "Erste Abhandlung": ("I", "‘선과 악’, ‘좋음과 나쁨’"),
    "Zweite Abhandlung": ("II", "‘죄’, ‘양심의 가책’ 및 그와 관련된 것"),
    "Dritte Abhandlung": ("III", "금욕주의적 이상은 무엇을 의미하는가?"),
}

PART_LINK_RE = re.compile(r"^\[(.+?)\]\(javascript:;\)\s*$")
SECTION_RE = re.compile(r"^###\s+\[(\d+(?:\s*a)?)[.]?\]\(javascript:;\)\s*$", re.I)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
HTML_TAG_RE = re.compile(r"<[^>]+>")
DATE_LINE_RE = re.compile(r"^(?:\*{0,2})?(?:Sils-Maria|Oberengadin|im (?:Juni|Juli) 18\d{2})", re.I)


def normalize_space(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    value = value.replace("\u00a0", " ").replace("\u2009", " ")
    value = re.sub(r"[ \t\r\n]+", " ", value)
    value = re.sub(r"\s+([,;:.!?])", r"\1", value)
    value = re.sub(r"([„‚])\s+", r"\1", value)
    value = re.sub(r"\.{3,}", "…", value)
    return value.strip()


def clean_markdown(value: str) -> str:
    value = html.unescape(value)
    value = value.replace("[if !IE]", "").replace("[endif]", "")
    value = re.sub(r"^\s*>\s?", "", value, flags=re.M)
    value = MARKDOWN_LINK_RE.sub(r"\1", value)
    value = HTML_TAG_RE.sub(" ", value)
    value = value.replace("**", "").replace("__", "")
    value = re.sub(r"(?<!\\)[*_]", "", value)
    value = value.replace(r"\*", "")
    return normalize_space(value)


def heading_info(raw_heading: str, work: str) -> tuple[str, str, str] | None:
    mapping = JGB_PARTS if work == "jgb" else GM_PARTS
    clean = clean_markdown(raw_heading)
    for needle, (part, title_ko) in mapping.items():
        if needle.casefold() in clean.casefold():
            title_de = clean.rstrip(".")
            if needle == "Aus hohen Bergen":
                title_de = "Aus hohen Bergen — Nachgesang"
            return part, title_de, title_ko
    return None


def source_url(work: str, part: str, section: str) -> str:
    base = "https://www.nietzschesource.org/eKGWB"
    if work == "jgb":
        if part == "Vorrede":
            return f"{base}/JGB-Vorrede"
        if part == "Nachgesang":
            return f"{base}/JGB-Lied"
        return f"{base}/JGB-{section}"
    if part == "Vorrede":
        return f"{base}/GM-Vorrede-{section}"
    return f"{base}/GM-{part}-{section}"


def body_blocks(lines: list[str], *, poem: bool = False) -> list[str]:
    cleaned_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or set(stripped) <= {"-", "_"}:
            cleaned_lines.append("")
            continue
        if stripped.startswith("![](") or "visore" in stripped:
            continue
        cleaned = clean_markdown(stripped)
        if not cleaned or DATE_LINE_RE.match(cleaned):
            continue
        cleaned_lines.append(cleaned)

    if poem:
        verse_lines = [line for line in cleaned_lines if line and len(line) > 1]
        return [normalize_space(" / ".join(verse_lines[i : i + 5])) for i in range(0, len(verse_lines), 5)]

    blocks: list[str] = []
    current: list[str] = []
    for line in cleaned_lines + [""]:
        if line:
            current.append(line)
        elif current:
            text = normalize_space(" ".join(current))
            if text:
                blocks.append(text)
            current = []
    return blocks


def parse_markdown_work(path: Path, work: str) -> list[dict]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    events: list[dict] = []

    for index, line in enumerate(lines):
        section_match = SECTION_RE.match(line.strip())
        if section_match:
            events.append({"kind": "section", "index": index, "section": section_match.group(1).replace(" ", "").lower()})
            continue
        part_match = PART_LINK_RE.match(line.strip())
        if part_match:
            info = heading_info(part_match.group(1), work)
            if info:
                events.append({"kind": "part", "index": index, "info": info})

    if not events:
        raise ValueError(f"No structural events found in {path}")

    sections: list[dict] = []
    current_part: tuple[str, str, str] | None = None
    for position, event in enumerate(events):
        next_index = events[position + 1]["index"] if position + 1 < len(events) else len(lines)
        if event["kind"] == "part":
            current_part = event["info"]
            has_numbered_child = position + 1 < len(events) and events[position + 1]["kind"] == "section"
            if has_numbered_child:
                continue
            part, title_de, title_ko = current_part
            blocks = body_blocks(lines[event["index"] + 1 : next_index], poem=part == "Nachgesang")
            if blocks:
                sections.append(
                    {
                        "part": part,
                        "part_title_de": title_de,
                        "part_title_ko": title_ko,
                        "section": "Nachgesang" if part == "Nachgesang" else "Vorrede",
                        "paragraphs": blocks,
                    }
                )
            continue

        if current_part is None:
            raise ValueError(f"Section before part at line {event['index'] + 1} in {path}")
        part, title_de, title_ko = current_part
        blocks = body_blocks(lines[event["index"] + 1 : next_index])
        if not blocks:
            raise ValueError(f"Empty {work} {part} {event['section']}")
        sections.append(
            {
                "part": part,
                "part_title_de": title_de,
                "part_title_ko": title_ko,
                "section": event["section"],
                "paragraphs": blocks,
            }
        )
    return sections


ABBREVIATIONS = (
    "Dr.", "Prof.", "resp.", "etc.", "u. s. w.", "u. a.", "z. B.", "d. h.",
    "vergl.", "vgl.", "S.", "Bd.", "Nr.", "sc.", "ca.", "ff.",
)


def protect_abbreviations(text: str) -> str:
    protected = text
    for abbreviation in ABBREVIATIONS:
        protected = protected.replace(abbreviation, abbreviation.replace(".", "∯"))
    protected = re.sub(r"(?<=\d)\.(?=\d)", "∯", protected)
    return protected


def split_long(text: str, max_chars: int = 500) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    result: list[str] = []
    remaining = text
    while len(remaining) > max_chars:
        window = remaining[: max_chars + 1]
        candidates: list[tuple[int, int]] = []
        for match in re.finditer(r"(?:;|:|,| —| –)\s+", window):
            if match.end() >= int(max_chars * 0.48):
                candidates.append((match.end(), match.end()))
        cut = candidates[-1][0] if candidates else window.rfind(" ", int(max_chars * 0.65))
        if cut <= 0:
            cut = max_chars
        result.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        result.append(remaining)
    return result


def merge_tiny(parts: list[str], min_chars: int = 28, min_words: int = 4) -> list[str]:
    merged: list[str] = []
    pending = ""
    for part in parts:
        part = normalize_space(part)
        if not part:
            continue
        tiny = len(part) < min_chars or len(part.split()) < min_words
        if tiny and not merged:
            pending = normalize_space(f"{pending} {part}")
            continue
        if pending:
            part = normalize_space(f"{pending} {part}")
            pending = ""
        if tiny and merged:
            merged[-1] = normalize_space(f"{merged[-1]} {part}")
        else:
            merged.append(part)
    if pending:
        if merged:
            merged[-1] = normalize_space(f"{merged[-1]} {pending}")
        elif len(pending) >= min_chars:
            merged.append(pending)
    return merged


def quote_units(paragraph: str) -> list[str]:
    protected = protect_abbreviations(normalize_space(paragraph))
    raw = re.split(r"(?<=[.!?…])(?:[”’\"])?\s+(?=(?:[„‚\"(\[])?[A-ZÄÖÜ—–-])", protected)
    restored = [part.replace("∯", ".") for part in raw]
    expanded: list[str] = []
    for part in restored:
        expanded.extend(split_long(part))
    return merge_tiny(expanded)


def load_translations() -> dict[str, dict]:
    if not TRANSLATIONS.exists():
        return {}
    payload = json.loads(TRANSLATIONS.read_text(encoding="utf-8"))
    translations = payload.get("translations", payload)
    if not isinstance(translations, dict):
        raise ValueError("translations/ko.json must contain an object map")
    return translations


def stable_id(work: str, part: str, section: str, paragraph: int, german: str) -> str:
    identity = "\0".join((work, part, section, str(paragraph), normalize_space(german)))
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    section_slug = re.sub(r"[^a-z0-9]+", "-", section.casefold()).strip("-") or "text"
    return f"{work}-{section_slug}-{digest}"


def build_quotes() -> tuple[list[dict], dict[str, list[dict]]]:
    translations = load_translations()
    by_work: dict[str, list[dict]] = {"jgb": [], "gm": []}

    for work, filename in (("jgb", "jgb-ekgwb-mirror.md"), ("gm", "gm-uva39.md")):
        sections = parse_markdown_work(RAW / filename, work)
        metadata = WORKS[work]
        for section_data in sections:
            for paragraph_index, paragraph in enumerate(section_data["paragraphs"]):
                for sentence_index, german in enumerate(quote_units(paragraph)):
                    quote_id = stable_id(work, section_data["part"], section_data["section"], paragraph_index, german)
                    translation = translations.get(quote_id, {})
                    korean = translation.get("korean", "") if isinstance(translation, dict) else str(translation)
                    record = {
                        "id": quote_id,
                        "work": work,
                        "workTitleDe": metadata["title_de"],
                        "workTitleKo": metadata["title_ko"],
                        "part": section_data["part"],
                        "partTitleDe": section_data["part_title_de"],
                        "partTitleKo": section_data["part_title_ko"],
                        "section": section_data["section"],
                        "paragraph": paragraph_index,
                        "sentence": sentence_index,
                        "german": german,
                        "korean": korean.strip(),
                        "translationStatus": translation.get("status", "pending") if isinstance(translation, dict) else "draft",
                        "sourceUrl": source_url(work, section_data["part"], section_data["section"]),
                    }
                    by_work[work].append(record)

    quotes = by_work["jgb"] + by_work["gm"]
    ids = [quote["id"] for quote in quotes]
    duplicates = [quote_id for quote_id, count in Counter(ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"Stable ID collision(s): {duplicates[:5]}")
    return quotes, by_work


def write_json(path: Path, payload: object, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def file_descriptor(path: Path, count: int) -> dict:
    content = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "count": count,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def main() -> None:
    quotes, by_work = build_quotes()
    DATA.mkdir(parents=True, exist_ok=True)
    write_json(DATA / "quotes.json", quotes, compact=True)
    write_json(DATA / "jgb.json", by_work["jgb"], compact=True)
    write_json(DATA / "gm.json", by_work["gm"], compact=True)

    corpus_identity = "\n".join(f"{quote['id']}\0{quote['german']}" for quote in quotes)
    corpus_version = hashlib.sha256(corpus_identity.encode("utf-8")).hexdigest()[:16]
    data_identity = "\n".join(f"{quote['id']}\0{quote['german']}\0{quote['korean']}" for quote in quotes)
    data_version = hashlib.sha256(data_identity.encode("utf-8")).hexdigest()[:16]
    translated = sum(bool(quote["korean"]) for quote in quotes)
    manifest = {
        "schemaVersion": 1,
        "corpusVersion": corpus_version,
        "dataVersion": data_version,
        "quoteCount": len(quotes),
        "translatedCount": translated,
        "pendingTranslationCount": len(quotes) - translated,
        "works": {
            "jgb": {"titleDe": WORKS["jgb"]["title_de"], "titleKo": WORKS["jgb"]["title_ko"], "count": len(by_work["jgb"])},
            "gm": {"titleDe": WORKS["gm"]["title_de"], "titleKo": WORKS["gm"]["title_ko"], "count": len(by_work["gm"])},
        },
        "files": {
            "quotes": file_descriptor(DATA / "quotes.json", len(quotes)),
            "jgb": file_descriptor(DATA / "jgb.json", len(by_work["jgb"])),
            "gm": file_descriptor(DATA / "gm.json", len(by_work["gm"])),
        },
        "sources": "sources/sources.json",
    }
    write_json(DATA / "manifest.json", manifest)
    print(
        f"Built {len(quotes):,} quotes "
        f"(JGB {len(by_work['jgb']):,}, GM {len(by_work['gm']):,}; "
        f"Korean {translated:,}/{len(quotes):,}) - corpus {corpus_version}, data {data_version}"
    )


if __name__ == "__main__":
    main()
