#!/usr/bin/env python3
"""Parse the supplied 1874 Parerga und Paralipomena EPUB.

The EPUB is a structured transcription, not an image/OCR container.  Its XHTML
uses the HTML entity ``&nbsp;`` without declaring it, so the parser normalizes that
single entity before strict XML parsing.  Historical spelling and punctuation
are otherwise preserved.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
import unicodedata
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
EPUB_PATH = ROOT / "sources" / "raw" / "pp-1874-virtual-library.epub"
CORRECTIONS_PATH = ROOT / "sources" / "pp-transcription-corrections.json"
EXPECTED_SHA256 = "42b70273663391ce572b2ad20bb00f79caf7c76e89b9d6504eb794556d956819"

VOLUME_URLS = {
    "I": "https://books.google.com/books?id=8g2CD8RLADQC",
    "II": "https://books.google.com/books?id=T4lhAAAAcAAJ",
}

VOLUME_ONE_SPECS = {
    4: ("I-Vorrede", "초판 서문"),
    8: ("I-01", "관념적인 것과 실재적인 것의 학설사 개요"),
    10: ("I-02", "철학사의 단편들"),
    12: ("I-03", "대학 철학에 관하여"),
    14: ("I-04", "개인의 운명에 나타나는 듯한 의도성에 관하여"),
    16: ("I-05", "유령을 보는 일과 그에 관련된 것에 관한 시론"),
    19: ("I-06-00", "삶의 지혜를 위한 아포리즘 · 서론"),
    20: ("I-06-01", "삶의 지혜를 위한 아포리즘 · 제1장 기본 구분"),
    21: ("I-06-02", "삶의 지혜를 위한 아포리즘 · 제2장 사람이 무엇인가"),
    22: ("I-06-03", "삶의 지혜를 위한 아포리즘 · 제3장 사람이 무엇을 가지고 있는가"),
    23: ("I-06-04", "삶의 지혜를 위한 아포리즘 · 제4장 사람이 무엇으로 보이는가"),
    24: ("I-06-05", "삶의 지혜를 위한 아포리즘 · 제5장 권고와 금언"),
    25: ("I-06-06", "삶의 지혜를 위한 아포리즘 · 제6장 생애 연령의 차이에 관하여"),
}

VOLUME_TWO_TITLES_KO = (
    "철학 및 그 방법에 관하여",
    "논리학과 변증술에 관하여",
    "지성 일반 및 모든 관계에서의 지성에 관한 생각들",
    "물자체와 현상의 대립에 관한 몇 가지 고찰",
    "범신론에 관한 몇 마디",
    "자연철학과 자연과학에 관하여",
    "색채론에 관하여",
    "윤리학에 관하여",
    "법론과 정치에 관하여",
    "죽음으로도 파괴되지 않는 우리의 참된 본질에 관한 학설",
    "현존재의 허무성 학설에 대한 보충",
    "세계의 고통 학설에 대한 보충",
    "자살에 관하여",
    "삶에의 의지의 긍정과 부정 학설에 대한 보충",
    "종교에 관하여",
    "산스크리트 문헌에 관한 몇 가지",
    "몇 가지 고고학적 고찰",
    "몇 가지 신화학적 고찰",
    "아름다움의 형이상학과 미학에 관하여",
    "판단·비평·갈채·명성에 관하여",
    "학식과 학자에 관하여",
    "스스로 생각하기",
    "저술과 문체에 관하여",
    "독서와 책에 관하여",
    "언어와 말에 관하여",
    "심리학적 소견",
    "여성에 관하여",
    "교육에 관하여",
    "관상학에 관하여",
    "소음과 잡음에 관하여",
    "비유·비유담·우화",
)

VOLUME_TWO_SPECS = {
    file_number: (f"II-{chapter:02d}", f"제2권 · 제{chapter}장 {title}")
    for chapter, (file_number, title) in enumerate(
        zip(range(28, 59), VOLUME_TWO_TITLES_KO), start=1
    )
}
VOLUME_TWO_SPECS[59] = ("II-Verse", "제2권 · 몇 편의 시")

CONTENT_SPECS = {
    **{number: ("I", *spec) for number, spec in VOLUME_ONE_SPECS.items()},
    **{number: ("II", *spec) for number, spec in VOLUME_TWO_SPECS.items()},
}

SECTION_TITLES_KO = {
    "A. Allgemeine": "A. 일반 원칙",
    "B. Unser Verhalten gegen uns selbst betreffend": "B. 자신을 대하는 태도",
    "C. Unser Verhalten gegen Andere betreffend": "C. 타인을 대하는 태도",
    "D. Unser Verhalten gegen den Weltlauf und das Schicksal betreffend": "D. 세계의 흐름과 운명을 대하는 태도",
    "Anhang": "부록",
    "Anhang verwandter Stellen": "관련 구절 부록",
    "Ein Dialog": "대화",
    "Glauben und Wissen": "믿음과 앎",
    "Offenbarung": "계시",
    "Ueber das Christenthum": "그리스도교에 관하여",
    "Ueber Theismus": "유신론에 관하여",
    "A. und N. T": "구약과 신약",
    "Sekten": "종파",
    "Rationalismus": "합리주의",
}

FOOTNOTE_FILES = {
    "OEBPS/Text/TheVirtualLibrary026.xhtml",
    "OEBPS/Text/TheVirtualLibrary060.xhtml",
}
NOTE_MARKER_RE = re.compile(r"\[\[PP-NOTE:([^\]]+)\]\]")
NUMBERED_SECTION_RE = re.compile(
    r"^§\.\s*(\d+)\s*([ab])?\s*\.(?:\s*(.*?))?\s*$",
    re.I,
)
NOTE_DEFINITION_ID_RE = re.compile(r"^fn[ab]_0\d+$", re.I)


def normalize_space(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    value = value.replace("\u00a0", " ").replace("\u00ad", "")
    value = re.sub(r"[ \t\r\n]+", " ", value)
    value = re.sub(r"\s+([,;:.!?])", r"\1", value)
    return value.strip()


def local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def is_source_note_link(href: str) -> bool:
    target, _, fragment = href.partition("#")
    return bool(fragment) and any(target.endswith(posixpath.basename(name)) for name in FOOTNOTE_FILES)


def element_text(
    element: ET.Element,
    *,
    mark_source_notes: bool = True,
    skip_all_links: bool = False,
) -> str:
    pieces: list[str] = [element.text or ""]
    for child in element:
        href = child.attrib.get("href", "") if local_name(child) == "a" else ""
        if skip_all_links and local_name(child) == "a":
            pass
        elif mark_source_notes and href and is_source_note_link(href):
            fragment = href.partition("#")[2]
            pieces.append(f" [[PP-NOTE:{fragment}]] ")
        else:
            pieces.append(
                element_text(
                    child,
                    mark_source_notes=mark_source_notes,
                    skip_all_links=skip_all_links,
                )
            )
        pieces.append(child.tail or "")
    return normalize_space("".join(pieces))


def semantic_blocks(body: ET.Element) -> list[tuple[str, ET.Element, str]]:
    blocks: list[tuple[str, ET.Element, str]] = []

    def visit(element: ET.Element) -> None:
        tag = local_name(element)
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            text = element_text(element)
            if text:
                blocks.append((tag, element, text))
            return
        if tag == "blockquote":
            text = element_text(element)
            if text:
                blocks.append(("p", element, text))
            return
        if tag == "p":
            text = element_text(element)
            if text:
                blocks.append(("p", element, text))
            return
        if tag in {"ul", "ol"}:
            items = [
                (child, element_text(child))
                for child in element
                if local_name(child) == "li" and element_text(child)
            ]
            if not items:
                return
            # A compact enumerating list completes the preceding colon and is
            # one readable source unit.  Longer list entries are independent
            # paragraphs and must retain their boundaries.  The EPUB uses
            # both forms, and silently skipping <li> used to drop substantial
            # passages from volumes II, chapters 1–3.
            if (
                blocks
                and blocks[-1][0] == "p"
                and blocks[-1][2].endswith(":")
                and all(len(text) < 100 for _, text in items)
            ):
                kind, previous, text = blocks[-1]
                joined = normalize_space(" ".join(item_text for _, item_text in items))
                blocks[-1] = (kind, previous, normalize_space(f"{text} {joined}"))
            else:
                blocks.extend(("p", child, text) for child, text in items)
            return
        for child in element:
            visit(child)

    visit(body)
    return blocks


def parse_xml(zipped: zipfile.ZipFile, name: str) -> ET.Element:
    raw = zipped.read(name).decode("utf-8-sig").replace("&nbsp;", "&#160;")
    return ET.fromstring(raw)


def find_body(root: ET.Element) -> ET.Element:
    return next(element for element in root.iter() if local_name(element) == "body")


def note_definition_id(element: ET.Element) -> str:
    for child in element.iter():
        candidate = child.attrib.get("id", "")
        if NOTE_DEFINITION_ID_RE.fullmatch(candidate):
            return candidate
    return ""


def load_source_notes(zipped: zipfile.ZipFile) -> dict[str, str]:
    notes: dict[str, str] = {}
    for name in sorted(FOOTNOTE_FILES):
        blocks = semantic_blocks(find_body(parse_xml(zipped, name)))
        current_id = ""
        current_parts: list[str] = []
        for kind, element, _ in blocks:
            if kind != "p":
                continue
            candidate = note_definition_id(element)
            if candidate:
                if current_id:
                    notes[current_id] = normalize_space(" ".join(current_parts))
                current_id = candidate
                current_parts = []
            if not current_id:
                continue
            text = element_text(element, mark_source_notes=False, skip_all_links=True)
            if text:
                current_parts.append(text)
        if current_id:
            notes[current_id] = normalize_space(" ".join(current_parts))
    if len(notes) != 164:
        raise ValueError(f"Expected 164 edition notes, found {len(notes)}")
    return notes


def strip_note_markers(value: str) -> tuple[str, list[str]]:
    refs = NOTE_MARKER_RE.findall(value)
    return normalize_space(NOTE_MARKER_RE.sub(" ", value)), refs


def section_key(label: str) -> str:
    label = label.rstrip(".")
    if label.startswith("Anhang verwandter Stellen"):
        return "Anhang-verwandter-Stellen"
    if label.startswith("Anhang"):
        return "Anhang"
    letter = re.match(r"^([A-D])[.]", label)
    return letter.group(1) if letter else label


def section_title_ko(label: str) -> str:
    return SECTION_TITLES_KO.get(label.rstrip("."), "")


def paragraph_payload(text: str, source_notes: dict[str, str]) -> dict:
    refs = NOTE_MARKER_RE.findall(text)
    missing = [ref for ref in refs if ref not in source_notes]
    if missing:
        raise ValueError(f"Unresolved Parerga edition notes: {missing[:5]}")
    return {
        "text": text,
        "source_notes": {
            ref: {
                "label": f"판본 각주 {int(ref.rsplit('_', 1)[1])}",
                "text": source_notes[ref],
                "language": "de",
                "kind": "source-edition",
            }
            for ref in dict.fromkeys(refs)
        },
    }


def parse_content_file(
    zipped: zipfile.ZipFile,
    file_number: int,
    source_notes: dict[str, str],
) -> list[dict]:
    volume, part, part_title_ko = CONTENT_SPECS[file_number]
    name = f"OEBPS/Text/TheVirtualLibrary{file_number:03d}.xhtml"
    blocks = semantic_blocks(find_body(parse_xml(zipped, name)))
    primary = next((text for kind, _, text in blocks if kind in {"h2", "h3"}), "")
    primary, _ = strip_note_markers(primary)
    if not primary:
        raise ValueError(f"Missing primary heading in {name}")

    sections: list[dict] = []
    current: dict | None = None
    pending_heading_refs: list[str] = []

    def start_section(
        key: str,
        *,
        label: str = "",
        title_de: str = "",
        title_ko: str = "",
        heading_refs: list[str] | None = None,
    ) -> dict:
        return {
            "part": part,
            "part_title_de": f"Band {volume} · {primary.rstrip('.')}",
            "part_title_ko": part_title_ko,
            "section": key,
            "section_label": label,
            "section_title_de": title_de,
            "section_title_ko": title_ko,
            "volume": volume,
            "volume_title_de": f"Band {volume}",
            "volume_title_ko": f"제{'1' if volume == 'I' else '2'}권",
            "source_url": VOLUME_URLS[volume],
            "source_file": name,
            "paragraphs": [],
            "_heading_refs": list(heading_refs or []),
        }

    def flush() -> None:
        nonlocal current
        if current and current["paragraphs"]:
            current.pop("_heading_refs", None)
            sections.append(current)
        current = None

    primary_seen = False
    for kind, _, raw_text in blocks:
        if kind in {"h2", "h3"} and not primary_seen:
            primary_seen = True
            continue
        if kind == "h4":
            label, heading_refs = strip_note_markers(raw_text)
            numbered = NUMBERED_SECTION_RE.fullmatch(label)
            if numbered:
                flush()
                key = f"{numbered.group(1)}{(numbered.group(2) or '').lower()}"
                title_de = (numbered.group(3) or "").rstrip(".")
                current = start_section(
                    key,
                    label=f"§{key}",
                    title_de=title_de,
                    title_ko=section_title_ko(title_de),
                    heading_refs=heading_refs,
                )
                continue
            clean_label = label.rstrip(".")
            if (
                current
                and not current["paragraphs"]
                and current["section"][:1].isdigit()
                and not current["section_title_de"]
            ):
                current["section_title_de"] = clean_label
                current["section_title_ko"] = section_title_ko(clean_label)
                current["_heading_refs"].extend(heading_refs)
                continue
            flush()
            current = start_section(
                section_key(clean_label),
                label=section_title_ko(clean_label) or clean_label,
                title_de=clean_label,
                heading_refs=heading_refs,
            )
            continue
        if kind != "p":
            continue
        if current is None:
            default_key = "Vorrede" if file_number == 4 else "Haupttext"
            default_label = "서문" if file_number == 4 else "본문"
            current = start_section(default_key, label=default_label)
        text = raw_text
        if current["_heading_refs"]:
            markers = " ".join(f"[[PP-NOTE:{ref}]]" for ref in current["_heading_refs"])
            text = normalize_space(f"{markers} {text}")
            current["_heading_refs"] = []
        current["paragraphs"].append(paragraph_payload(text, source_notes))

    flush()
    return sections


def parse_parerga() -> list[dict]:
    if not EPUB_PATH.is_file():
        raise FileNotFoundError(f"Missing source EPUB: {EPUB_PATH.relative_to(ROOT)}")
    digest = hashlib.sha256(EPUB_PATH.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError(f"Unexpected Parerga EPUB hash: {digest}")

    with zipfile.ZipFile(EPUB_PATH) as zipped:
        source_notes = load_source_notes(zipped)
        sections = [
            section
            for file_number in CONTENT_SPECS
            for section in parse_content_file(zipped, file_number, source_notes)
        ]

    corrections = json.loads(CORRECTIONS_PATH.read_text(encoding="utf-8"))["corrections"]
    for correction in corrections:
        source_file = correction["sourceFile"]
        before = correction["from"]
        after = correction["to"]
        expected = correction.get("expectedOccurrences", 1)
        occurrences = 0
        for section in sections:
            if section.get("source_file") != source_file:
                continue
            for paragraph in section["paragraphs"]:
                occurrences += paragraph["text"].count(before)
                paragraph["text"] = paragraph["text"].replace(before, after)
        if occurrences != expected:
            raise ValueError(
                "Parerga transcription correction occurrence mismatch: "
                f"{before!r} expected={expected}, actual={occurrences}"
            )

    numbered = {
        section["section"]
        for section in sections
        if section["volume"] == "II" and section["section"][:1].isdigit()
    }
    expected = {str(value) for value in range(1, 414)} - {"90", "103"}
    expected |= {"90a", "90b", "103a", "103b"}
    if numbered != expected:
        raise ValueError(
            "Parerga § coverage mismatch: "
            f"missing={sorted(expected - numbered)[:8]}, extra={sorted(numbered - expected)[:8]}"
        )
    if any("\ufffd" in paragraph["text"] for section in sections for paragraph in section["paragraphs"]):
        raise ValueError("Replacement character found in Parerga transcription")
    return sections


if __name__ == "__main__":
    parsed = parse_parerga()
    paragraphs = sum(len(section["paragraphs"]) for section in parsed)
    referenced_notes = {
        ref
        for section in parsed
        for paragraph in section["paragraphs"]
        for ref in paragraph["source_notes"]
    }
    print(
        f"Parsed {len(parsed)} sections, {paragraphs} paragraphs, "
        f"{len(referenced_notes)} referenced edition notes from {EPUB_PATH.name}."
    )
