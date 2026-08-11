#!/usr/bin/env python3
"""Build stable quote JSON from the vendored German source texts."""

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
    "ac": {
        "title_de": "Der Antichrist",
        "title_ko": "안티크리스트",
        "source_file": "sources/raw/ac-ekgwb-mirror.md",
    },
    "gd": {
        "title_de": "Götzen-Dämmerung",
        "title_ko": "우상의 황혼",
        "source_file": "sources/raw/gd-ekgwb-mirror.md",
    },
    "fw": {
        "title_de": "Die fröhliche Wissenschaft",
        "title_ko": "즐거운 학문",
        "source_file": "sources/raw/fw-ekgwb-mirror.md",
    },
}

WORK_ORDER = tuple(WORKS)

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

AC_PARTS = {
    "Vorwort": ("Vorrede", "서문"),
}

GD_PARTS = {
    "Vorwort": ("Vorrede", "서문"),
    "Sprüche und Pfeile": ("Sprueche", "잠언과 화살"),
    "Das Problem des Sokrates": ("Sokrates", "소크라테스의 문제"),
    "Vernunft“ in der Philosophie": ("Vernunft", "철학에서의 ‘이성’"),
    "wahre Welt“ endlich zur Fabel": ("Wahre-Welt", "‘참된 세계’가 마침내 우화가 된 경위"),
    "Moral als Widernatur": ("Moral", "반자연으로서의 도덕"),
    "vier grossen Irrthümer": ("Irrthuemer", "네 가지 큰 오류"),
    "Verbesserer“ der Menschheit": ("Verbesserer", "인류를 ‘개선한다는 자들’"),
    "Was den Deutschen abgeht": ("Deutschen", "독일인들에게 결여된 것"),
    "Streifzüge eines Unzeitgemässen": ("Streifzuege", "어느 반시대적 인간의 편력"),
    "Was ich den Alten verdanke": ("Alten", "내가 고대인들에게 빚진 것"),
    "Der Hammer redet": ("Hammer", "망치가 말한다"),
}

FW_PARTS = {
    "Vorrede zur zweiten Ausgabe": ("Vorrede", "제2판 서문"),
    "Scherz, List und Rache": ("Vorspiel", "농담, 간계 그리고 복수 — 독일 운문의 전주곡"),
    "Erstes Buch": ("I", "제1서"),
    "Zweites Buch": ("II", "제2서"),
    "Drittes Buch": ("III", "제3서"),
    "Viertes Buch": ("IV", "제4서 — 성스러운 야누아리우스"),
    "Fünftes Buch": ("V", "제5서 — 두려움을 모르는 우리"),
    "Anhang": ("Anhang", "부록 — 자유로운 새 왕자의 노래"),
}

PARTS_BY_WORK = {
    "jgb": JGB_PARTS,
    "gm": GM_PARTS,
    "ac": AC_PARTS,
    "gd": GD_PARTS,
    "fw": FW_PARTS,
}

PART_LINK_RE = re.compile(r"^\[(.+?)\]\(javascript:;\)\s*$", re.S)
SECTION_RE = re.compile(r"^###\s+\[(.+?)\]\(javascript:;\)\s*$", re.I | re.S)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
HTML_TAG_RE = re.compile(r"<[^>]+>")
DATE_LINE_RE = re.compile(
    r"^(?:\*{0,2})?(?:Sils-Maria|Oberengadin|Turin|Ruta|Friedrich Nietzsche|im (?:Juni|Juli|Herbst) 18\d{2})",
    re.I,
)


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


def clean_new_markdown(value: str) -> str:
    """Flatten eKGWB correction markers without changing legacy corpus IDs."""
    value = html.unescape(value)
    value = re.sub(r"&lt;(.*?)&gt;", r"\1", value)
    value = re.sub(r"\s*\|\s*", " ", value).strip()
    return clean_markdown(value)


def heading_info(raw_heading: str, work: str) -> tuple[str, str, str] | None:
    mapping = PARTS_BY_WORK[work]
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
    if work == "gm":
        if part == "Vorrede":
            return f"{base}/GM-Vorrede-{section}"
        return f"{base}/GM-{part}-{section}"
    if work == "ac":
        target = "Vorwort" if section == "Vorrede" else section
        return f"{base}/AC-{target}"
    if work == "gd":
        if part == "Vorrede":
            return f"{base}/GD-Vorwort"
        if part == "Wahre-Welt":
            return f"{base}/GD-Welt-Fabel"
        if part == "Hammer":
            return f"{base}/GD-Hammer"
        return f"{base}/GD-{part}-{section}"
    if work == "fw":
        if part == "Vorrede":
            return f"{base}/FW-Vorrede-{section}"
        if part == "Vorspiel":
            return f"{base}/FW-Vorspiel-{section}"
        if part == "Anhang":
            return f"{base}/FW-Lieder-{section}"
        return f"{base}/FW-{section}"
    raise ValueError(f"Unknown work {work}")


def body_blocks(lines: list[str], *, work: str, poem: bool = False) -> list[str]:
    cleaned_lines: list[str] = []
    correction_gap = False
    for line in lines:
        stripped = line.strip()
        if not stripped or set(stripped) <= {"-", "_", "|", ":", " ", "*", "\\"}:
            if correction_gap:
                continue
            cleaned_lines.append("")
            continue
        if stripped.startswith("![](") or "visore" in stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith(("*Erratum:*", "*lies:*", "[eKGWB Berichtigung]", "[Nach KGW/KGB Nachberichte]")):
            while cleaned_lines and not cleaned_lines[-1]:
                cleaned_lines.pop()
            correction_gap = True
            continue
        cleaned = clean_new_markdown(stripped) if work in {"ac", "gd", "fw"} else clean_markdown(stripped)
        if not cleaned or DATE_LINE_RE.match(cleaned) or cleaned in {"Der Antichrist", "Götzen-Dämmerung"}:
            continue
        correction_gap = False
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


def linked_heading_events(lines: list[str], work: str) -> list[dict]:
    events: list[dict] = []
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("###"):
            match = SECTION_RE.match(stripped)
            if match:
                label = clean_new_markdown(match.group(1)) if work in {"ac", "gd", "fw"} else clean_markdown(match.group(1))
                number_match = re.match(r"^(\d+(?:\s*a)?)[.]?(?:\s+(.*))?$", label, re.I)
                if number_match:
                    events.append(
                        {
                            "kind": "section",
                            "index": index,
                            "body_start": index + 1,
                            "section": number_match.group(1).replace(" ", "").lower(),
                            "title_de": normalize_space((number_match.group(2) or "").strip(" .*")),
                        }
                    )
                elif work == "ac" and label.strip("[] ").casefold() == "gesetz":
                    events.append(
                        {
                            "kind": "section",
                            "index": index,
                            "body_start": index + 1,
                            "section": "Gesetz",
                            "title_de": "Gesetz wider das Christenthum",
                        }
                    )
            index += 1
            continue

        if not stripped.startswith("["):
            index += 1
            continue
        if "](" in stripped and "](javascript:;)" not in stripped:
            index += 1
            continue
        candidate = stripped
        end_index = index
        while "](javascript:;)" not in candidate and end_index + 1 < len(lines) and end_index - index < 4:
            end_index += 1
            candidate = normalize_space(f"{candidate} {lines[end_index].strip()}")
        match = PART_LINK_RE.match(candidate)
        if not match:
            index += 1
            continue
        raw_heading = match.group(1)
        info = heading_info(raw_heading, work)
        if info:
            events.append({"kind": "part", "index": index, "body_start": end_index + 1, "info": info})
        elif work == "fw":
            events.append(
                {
                    "kind": "named_section",
                    "index": index,
                    "body_start": end_index + 1,
                    "title_de": clean_new_markdown(raw_heading).rstrip("."),
                }
            )
        index = end_index + 1
    return events


def parse_markdown_work(path: Path, work: str) -> list[dict]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    events = linked_heading_events(lines, work)

    if not events:
        raise ValueError(f"No structural events found in {path}")

    sections: list[dict] = []
    current_part: tuple[str, str, str] | None = None
    named_section_number = 0
    for position, event in enumerate(events):
        next_index = events[position + 1]["index"] if position + 1 < len(events) else len(lines)
        if event["kind"] == "part":
            current_part = event["info"]
            part, title_de, title_ko = current_part
            named_section_number = 0
            next_is_numbered = position + 1 < len(events) and events[position + 1]["kind"] == "section"
            implicit_first_section = (
                work == "gd"
                and part == "Irrthuemer"
                and next_is_numbered
                and events[position + 1]["section"] == "2"
            )
            capture_intro = (
                not next_is_numbered
                or (work == "ac" and part == "Vorrede")
                or implicit_first_section
            )
            blocks = (
                body_blocks(
                    lines[event["body_start"] : next_index],
                    work=work,
                    poem=part in {"Nachgesang", "Vorspiel", "Anhang"},
                )
                if capture_intro
                else []
            )
            if blocks:
                # GD's "Die vier grossen Irrthümer" prints the first essay
                # directly under the part heading; numbering begins at §2.
                # Preserve any such unlabelled opening as §1 instead of
                # silently discarding it.
                section = "Nachgesang" if part == "Nachgesang" else part
                if implicit_first_section:
                    section = "1"
                sections.append(
                    {
                        "part": part,
                        "part_title_de": title_de,
                        "part_title_ko": title_ko,
                        "section": section,
                        "section_title_de": "",
                        "paragraphs": blocks,
                    }
                )
            continue

        if event["kind"] == "named_section":
            if current_part is None or current_part[0] != "Anhang":
                continue
            named_section_number += 1
            part, title_de, title_ko = current_part
            blocks = body_blocks(lines[event["body_start"] : next_index], work=work, poem=True)
            if blocks:
                sections.append(
                    {
                        "part": part,
                        "part_title_de": title_de,
                        "part_title_ko": title_ko,
                        "section": str(named_section_number),
                        "section_title_de": event["title_de"],
                        "paragraphs": blocks,
                    }
                )
            continue

        if current_part is None:
            raise ValueError(f"Section before part at line {event['index'] + 1} in {path}")
        part, title_de, title_ko = current_part
        if work == "ac" and event["section"] == "Gesetz":
            part, title_de, title_ko = "Anhang", "Gesetz wider das Christenthum", "그리스도교에 반대하는 법"
        elif work == "ac" and part == "Vorrede":
            part, title_de, title_ko = "Haupttext", "Der Antichrist", "본문"
        section = event["section"]
        id_section = section
        # The source snapshot repeats the printed number 237. Scholarly
        # editions distinguish the prose aphorism following the seven short
        # poems as JGB 237a. Expose that traceable citation without changing
        # the already published stable ID, whose identity section remains
        # 237 for this one legacy record.
        if (
            work == "jgb"
            and part == "VII"
            and section == "237"
            and any(item["part"] == part and item["section"] == "237" for item in sections)
        ):
            section = "237a"
        blocks = body_blocks(
            lines[event["body_start"] : next_index],
            work=work,
            poem=part in {"Nachgesang", "Vorspiel", "Anhang"},
        )
        # JGB §8 ends with a two-line Latin acclamation. Each verse is too
        # short to stand alone under the quote filter, but together they are
        # the punch line of the aphorism and must not disappear from the
        # corpus. Keep the existing prose paragraph (and therefore its ID)
        # intact while packing the two verse lines as one traceable unit.
        if (
            work == "jgb"
            and event["section"] == "8"
            and len(blocks) >= 3
            and blocks[1] == "adventavit asinus"
            and blocks[2] == "pulcher et fortissimus."
        ):
            blocks = [blocks[0], normalize_space(f"{blocks[1]} / {blocks[2]}"), *blocks[3:]]
        # The last three lines of the comic verse in JGB §228 form one
        # syntactic and rhythmic unit. Packing them keeps the short French
        # punch line without changing the IDs of the preceding verse lines.
        if (
            work == "jgb"
            and event["section"] == "228"
            and len(blocks) >= 7
            and blocks[4:7]
            == [
                "Unbegeistert, ungespässig,",
                "Unverwüstlich-mittelmässig,",
                "Sans genie et sans esprit!",
            ]
        ):
            blocks = [*blocks[:4], normalize_space(" / ".join(blocks[4:7])), *blocks[7:]]
        if not blocks:
            raise ValueError(f"Empty {work} {part} {event['section']}")
        sections.append(
            {
                "part": part,
                "part_title_de": title_de,
                "part_title_ko": title_ko,
                "section": section,
                "id_section": id_section,
                "section_title_de": event.get("title_de", ""),
                "paragraphs": blocks,
            }
        )
    return sections


ABBREVIATIONS = (
    "Dr.", "Prof.", "resp.", "etc.", "u. s. w.", "u. a.", "z. B.", "d. h.",
    "vergl.", "vgl.", "S.", "Bd.", "Nr.", "sc.", "ca.", "ff.",
)

# Short refrains and closing verse lines that are semantically complete even
# though they fall below the general quote-size threshold. Dialogue cues such
# as "— Weiter!" remain excluded from the random quote pool.
PRESERVE_SHORT_UNITS = {
    "— Ist das noch deutsch? —",
    "— Ist Das noch deutsch?",
    "Mir zu sieben neuen Muth.",
    "Flamme bin ich sicherlich.",
}


def protect_abbreviations(text: str, extra: tuple[str, ...] = ()) -> str:
    protected = text
    for abbreviation in (*ABBREVIATIONS, *extra):
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


def sentence_units(
    paragraph: str,
    *,
    max_chars: int = 500,
    extra_abbreviations: tuple[str, ...] = (),
) -> list[str]:
    normalized = normalize_space(paragraph)
    if normalized in PRESERVE_SHORT_UNITS:
        return [normalized]
    protected = protect_abbreviations(normalized, extra_abbreviations)
    raw = re.split(r"(?<=[.!?…])(?:[”’\"])?\s+(?=(?:[„‚\"(\[])?[A-ZÄÖÜ—–-])", protected)
    restored = [part.replace("∯", ".") for part in raw]
    expanded: list[str] = []
    for part in restored:
        expanded.extend(split_long(part, max_chars=max_chars))
    return merge_tiny(expanded)


def quote_units(paragraph: str) -> list[str]:
    return sentence_units(paragraph)


def quote_units_for_work(paragraph: str, work: str) -> list[str]:
    if work in {"jgb", "gm"}:
        return quote_units(paragraph)
    units = sentence_units(paragraph, max_chars=650, extra_abbreviations=("St.",))
    packed: list[str] = []
    current = ""
    for unit in units:
        candidate = normalize_space(f"{current} {unit}")
        if current and len(candidate) > 500:
            packed.append(current)
            current = unit
        else:
            current = candidate
    if current:
        packed.append(current)
    return packed


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
    by_work: dict[str, list[dict]] = {work: [] for work in WORK_ORDER}

    for work in WORK_ORDER:
        metadata = WORKS[work]
        source_path = ROOT / metadata["source_file"]
        sections = parse_markdown_work(source_path, work)
        for section_data in sections:
            paragraph_count = len(section_data["paragraphs"])
            for paragraph_index, paragraph in enumerate(section_data["paragraphs"]):
                for sentence_index, german in enumerate(quote_units_for_work(paragraph, work)):
                    quote_id = stable_id(
                        work,
                        section_data["part"],
                        section_data.get("id_section", section_data["section"]),
                        paragraph_index,
                        german,
                    )
                    translation = translations.get(quote_id, {})
                    korean = translation.get("korean", "") if isinstance(translation, dict) else str(translation)
                    footnotes = translation.get("footnotes", []) if isinstance(translation, dict) else []
                    record = {
                        "id": quote_id,
                        "work": work,
                        "workTitleDe": metadata["title_de"],
                        "workTitleKo": metadata["title_ko"],
                        "part": section_data["part"],
                        "partTitleDe": section_data["part_title_de"],
                        "partTitleKo": section_data["part_title_ko"],
                        "section": section_data["section"],
                        "sectionTitleDe": section_data.get("section_title_de", ""),
                        "paragraph": paragraph_index,
                        "paragraphCount": paragraph_count,
                        "sentence": sentence_index,
                        "german": german,
                        "korean": korean.strip(),
                        "translationStatus": translation.get("status", "pending") if isinstance(translation, dict) else "draft",
                        "footnotes": footnotes,
                        "sourceUrl": source_url(work, section_data["part"], section_data["section"]),
                    }
                    by_work[work].append(record)

    quotes = [quote for work in WORK_ORDER for quote in by_work[work]]
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
    for work in WORK_ORDER:
        write_json(DATA / f"{work}.json", by_work[work], compact=True)

    corpus_identity = "\n".join(f"{quote['id']}\0{quote['german']}" for quote in quotes)
    corpus_version = hashlib.sha256(corpus_identity.encode("utf-8")).hexdigest()[:16]
    data_identity = json.dumps(quotes, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    data_version = hashlib.sha256(data_identity.encode("utf-8")).hexdigest()[:16]
    translated = sum(bool(quote["korean"]) for quote in quotes)
    reviewed = sum(quote["translationStatus"] == "reviewed" for quote in quotes)
    manifest = {
        "schemaVersion": 2,
        "corpusVersion": corpus_version,
        "dataVersion": data_version,
        "quoteCount": len(quotes),
        "translatedCount": translated,
        "reviewedCount": reviewed,
        "pendingTranslationCount": len(quotes) - translated,
        "works": {
            work: {
                "titleDe": WORKS[work]["title_de"],
                "titleKo": WORKS[work]["title_ko"],
                "count": len(by_work[work]),
                "reviewedCount": sum(
                    quote["translationStatus"] == "reviewed" for quote in by_work[work]
                ),
            }
            for work in WORK_ORDER
        },
        "files": {
            "quotes": file_descriptor(DATA / "quotes.json", len(quotes)),
            **{
                work: file_descriptor(DATA / f"{work}.json", len(by_work[work]))
                for work in WORK_ORDER
            },
        },
        "sources": "sources/sources.json",
    }
    write_json(DATA / "manifest.json", manifest)
    print(
        f"Built {len(quotes):,} quotes "
        f"({', '.join(f'{work.upper()} {len(by_work[work]):,}' for work in WORK_ORDER)}; "
        f"Korean {translated:,}/{len(quotes):,}, reviewed {reviewed:,}) - corpus {corpus_version}, data {data_version}"
    )


if __name__ == "__main__":
    main()
