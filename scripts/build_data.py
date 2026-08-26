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

from parse_schopenhauer_epub import parse_parerga, strip_note_markers
from translation_sources import load_translations


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw"
DATA = ROOT / "data"

AUTHORS = {
    "nietzsche": {
        "name_de": "Friedrich Nietzsche",
        "name_ko": "프리드리히 니체",
    },
    "schopenhauer": {
        "name_de": "Arthur Schopenhauer",
        "name_ko": "아르투어 쇼펜하우어",
    },
}

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
    "za": {
        "title_de": "Also sprach Zarathustra",
        "title_ko": "차라투스트라는 이렇게 말했다",
        "source_files": [
            "sources/raw/za-i-ekgwb-mirror.md",
            "sources/raw/za-ii-ekgwb-mirror.md",
            "sources/raw/za-iii-ekgwb-mirror.md",
            "sources/raw/za-iv-ekgwb-mirror.md",
        ],
    },
    "eh": {
        "title_de": "Ecce homo",
        "title_ko": "이 사람을 보라",
        "source_file": "sources/raw/eh-ekgwb-mirror.md",
    },
    "nf": {
        "title_de": "Nachgelassene Fragmente 1885–1888",
        "title_ko": "후기 유고 1885–1888",
        "source_glob": "sources/raw/nf-*.md",
    },
    "pp": {
        "author": "schopenhauer",
        "title_de": "Parerga und Paralipomena",
        "title_ko": "소품과 부록",
        "source_file": "sources/raw/pp-1874-virtual-library.epub",
        "edition": "3. Auflage (1874)",
        "editor": "Julius Frauenstädt",
        "transcription_status": "검증 중인 구조화 전사본",
    },
}

WORK_ORDER = tuple(WORKS)
WIDGET_SHARD_SIZE = 256

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

ZA_PARTS = {
    "I": ("Erster Theil", "제1부"),
    "II": ("Zweiter Theil", "제2부"),
    "III": ("Dritter Theil", "제3부"),
    "IV": ("Vierter und letzter Theil", "제4부"),
}

ZA_CHAPTERS = {
    "Zarathustra’s Vorrede": ("Vorrede", "차라투스트라의 서문"),
    "Von den drei Verwandlungen": ("Verwandlungen", "세 가지 변신에 관하여"),
    "Von den Lehrstühlen der Tugend": ("Lehrstuehle", "덕을 가르치는 강단에 관하여"),
    "Von den Hinterweltlern": ("Hinterweltler", "배후세계를 믿는 자들에 관하여"),
    "Von den Verächtern des Leibes": ("Leib", "몸을 경멸하는 자들에 관하여"),
    "Von den Freuden- und Leidenschaften": ("Freuden", "기쁨과 열정에 관하여"),
    "Vom bleichen Verbrecher": ("Verbrecher", "창백한 범죄자에 관하여"),
    "Vom Lesen und Schreiben": ("Lesen", "읽기와 쓰기에 관하여"),
    "Vom Baum am Berge": ("Baum", "산 위의 나무에 관하여"),
    "Von den Predigern des Todes": ("Prediger", "죽음을 설교하는 자들에 관하여"),
    "Vom Krieg und Kriegsvolke": ("Krieg", "전쟁과 전사들에 관하여"),
    "Vom neuen Götzen": ("Goetzen", "새로운 우상에 관하여"),
    "Von den Fliegen des Marktes": ("Fliegen", "시장의 파리들에 관하여"),
    "Von der Keuschheit": ("Keuschheit", "순결에 관하여"),
    "Vom Freunde": ("Freund", "벗에 관하여"),
    "Von tausend und Einem Ziele": ("Ziele", "천 개와 하나의 목표에 관하여"),
    "Von der Nächstenliebe": ("Naechstenliebe", "이웃 사랑에 관하여"),
    "Vom Wege des Schaffenden": ("Schaffenden", "창조하는 자의 길에 관하여"),
    "Von alten und jungen Weiblein": ("Weiblein", "늙은 여인과 젊은 여인에 관하여"),
    "Vom Biss der Natter": ("Natter", "독사의 물림에 관하여"),
    "Von Kind und Ehe": ("Kind-Ehe", "아이와 결혼에 관하여"),
    "Vom freien Tode": ("Tod", "자유로운 죽음에 관하여"),
    "Von der schenkenden Tugend": ("Tugend", "베푸는 덕에 관하여"),
    "Das Kind mit dem Spiegel": ("Kind", "거울을 든 아이"),
    "Auf den glückseligen Inseln": ("Inseln", "행복의 섬들에서"),
    "Von den Mitleidigen": ("Mitleidige", "연민하는 자들에 관하여"),
    "Von den Priestern": ("Priester", "사제들에 관하여"),
    "Von den Tugendhaften": ("Tugendhaften", "덕 있는 자들에 관하여"),
    "Vom Gesindel": ("Gesindel", "천민에 관하여"),
    "Von den Taranteln": ("Taranteln", "타란툴라들에 관하여"),
    "Von den berühmten Weisen": ("Weise", "유명한 현자들에 관하여"),
    "Das Nachtlied": ("Nachtlied", "밤의 노래"),
    "Das Tanzlied": ("Tanzlied", "춤의 노래"),
    "Das Grablied": ("Grablied", "무덤의 노래"),
    "Von der Selbst-Ueberwindung": ("Selbst-Ueberwindung", "자기 극복에 관하여"),
    "Von den Erhabenen": ("Erhabene", "숭고한 자들에 관하여"),
    "Vom Lande der Bildung": ("Bildung", "교양의 나라에 관하여"),
    "Von der unbefleckten Erkenntniss": ("Erkenntniss", "티 없는 인식에 관하여"),
    "Von den Gelehrten": ("Gelehrte", "학자들에 관하여"),
    "Von den Dichtern": ("Dichter", "시인들에 관하여"),
    "Von grossen Ereignissen": ("Ereignisse", "큰 사건들에 관하여"),
    "Der Wahrsager": ("Wahrsager", "예언자"),
    "Von der Erlösung": ("Erloesung", "구원에 관하여"),
    "Von der Menschen-Klugheit": ("Klugheit", "인간적 영리함에 관하여"),
    "Die stillste Stunde": ("Stunde", "가장 고요한 시간"),
    "Der Wanderer": ("Wanderer", "방랑자"),
    "Von Gesicht und Räthsel": ("Gesicht", "환영과 수수께끼에 관하여"),
    "Von der Seligkeit wider Willen": ("Seligkeit", "뜻하지 않은 행복에 관하여"),
    "Vor Sonnen-Aufgang": ("Sonnen-Aufgang", "해 뜨기 전에"),
    "Von der verkleinernden Tugend": ("Tugend", "왜소하게 만드는 덕에 관하여"),
    "Auf dem Oelberge": ("Oelberge", "올리브산에서"),
    "Vom Vorübergehen": ("Voruebergehen", "그냥 지나쳐 감에 관하여"),
    "Von den Abtrünnigen": ("Abtruennigen", "배교자들에 관하여"),
    "Die Heimkehr": ("Heimkehr", "귀향"),
    "Von den drei Bösen": ("Boesen", "세 가지 악에 관하여"),
    "Vom Geist der Schwere": ("Geist-Schwere", "중력의 영에 관하여"),
    "Von alten und neuen Tafeln": ("Tafeln", "낡은 서판과 새로운 서판에 관하여"),
    "Der Genesende": ("Genesende", "회복 중인 자"),
    "Von der grossen Sehnsucht": ("Sehnsucht", "위대한 동경에 관하여"),
    "Das andere Tanzlied": ("Tanzlied", "또 하나의 춤 노래"),
    "Die sieben Siegel. (Oder: das Ja- und Amen-Lied.)": ("Siegel", "일곱 봉인 — 또는 ‘예’와 ‘아멘’의 노래"),
    "Das Honig-Opfer": ("Honig", "꿀 제물"),
    "Der Nothschrei": ("Nothschrei", "위급한 외침"),
    "Gespräch mit den Königen": ("Koenige", "왕들과의 대화"),
    "Der Blutegel": ("Blutegel", "거머리"),
    "Der Zauberer": ("Zauberer", "마술사"),
    "Ausser Dienst": ("Dienst", "은퇴하여"),
    "Der hässlichste Mensch": ("Haesslichste", "가장 추한 인간"),
    "Der freiwillige Bettler": ("Bettler", "자발적 거지"),
    "Der Schatten": ("Schatten", "그림자"),
    "Mittags": ("Mittag", "정오"),
    "Die Begrüssung": ("Begruessung", "환영"),
    "Das Abendmahl": ("Abendmahl", "만찬"),
    "Vom höheren Menschen": ("Mensch", "더 높은 인간에 관하여"),
    "Das Lied der Schwermuth": ("Schwermuth", "우울의 노래"),
    "Von der Wissenschaft": ("Wissenschaft", "학문에 관하여"),
    "Unter Töchtern der Wüste": ("Wuesten", "사막의 딸들 사이에서"),
    "Die Erweckung": ("Erweckung", "각성"),
    "Das Eselsfest": ("Eselsfest", "나귀 축제"),
    "Das Nachtwandler-Lied": ("Nachtwandler", "몽유병자의 노래"),
    "Das Zeichen": ("Zeichen", "징표"),
}

EH_PARTS = {
    "Vorwort": ("Vorwort", "서문"),
    "Warum ich so weise bin": ("Weise", "나는 왜 이토록 현명한가"),
    "Warum ich so klug bin": ("Klug", "나는 왜 이토록 영리한가"),
    "Warum ich so gute Bücher schreibe": ("Bücher", "나는 왜 이토록 좋은 책을 쓰는가"),
    "Die Geburt der Tragödie": ("GT", "비극의 탄생"),
    "Die Unzeitgemässen": ("Unzeitgemaesse", "반시대적 고찰들"),
    "Menschliches, Allzumenschliches": ("MA", "인간적인, 너무나 인간적인"),
    "Morgenröthe": ("M", "아침놀"),
    "Die fröhliche Wissenschaft": ("FW", "즐거운 학문"),
    "Also sprach Zarathustra": ("Za", "차라투스트라는 이렇게 말했다"),
    "Jenseits von Gut und Böse": ("JGB", "선악의 저편"),
    "Genealogie der Moral": ("GM", "도덕의 계보"),
    "Götzen-Dämmerung": ("GD", "우상의 황혼"),
    "Der Fall Wagner": ("WA", "바그너의 경우"),
    "Warum ich ein Schicksal bin": ("Schicksal", "나는 왜 하나의 운명인가"),
}

# EH-Klug §7 contains the complete "An der Brücke stand" poem.  The source
# snapshot stores every verse as a separate Markdown line, including several
# lines that are deliberately too short for the general prose block parser.
# Keep the canonical line order here so the parser can preserve the poem
# without silently discarding those short lines.
EH_VENICE_VERSE_LINES = (
    "An der Brücke stand",
    "jüngst ich in brauner Nacht.",
    "Fernher kam Gesang:",
    "goldener Tropfen quoll’s",
    "über die zitternde Fläche weg.",
    "Gondeln, Lichter, Musik —",
    "trunken schwamm’s in die Dämmrung hinaus…",
    "Meine Seele, ein Saitenspiel,",
    "sang sich, unsichtbar berührt,",
    "heimlich ein Gondellied dazu,",
    "zitternd vor bunter Seligkeit.",
    "— Hörte Jemand ihr zu?…",
)

EH_READER_VERSE_LINES = (
    "Euch, den kühnen Suchern, Versuchern, und wer je sich mit listigen Segeln auf furchtbare Meere einschiffte, —",
    "euch, den Räthsel-Trunkenen, den Zwielicht-Frohen, deren Seele mit Flöten zu jedem Irrschlunde gelockt wird:",
    "— denn nicht wollt ihr mit feiger Hand einem Faden nachtasten; und wo ihr errathen könnt, da hasst ihr es, zu erschliessen…",
)

EH_JANUARY_VERSE_LINES = (
    "Der du mit dem Flammenspeere",
    "Meiner Seele Eis zertheilt,",
    "Dass sie brausend nun zum Meere",
    "Ihrer höchsten Hoffnung eilt:",
    "Heller stets und stets gesunder,",
    "Frei im liebevollsten Muss —",
    "Also preist sie deine Wunder,",
    "Schönster Januarius!",
)

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
    correction_label = r"\[Nach KGW/KGB Nachberichte\]\([^)]*\)"
    value = re.sub(
        rf"\s*\*Erratum:\*.*?\*lies:\*(.*?)\]\(javascript:;\)\s*{correction_label}",
        "",
        value,
    )
    value = re.sub(
        rf"\s*\*Erratum:\*.*?\*lies:\*(.*?)\s*{correction_label}",
        "",
        value,
    )
    value = re.sub(
        r"\s*\*lies:\*\d+\[\d+\]\s*\[Nach KGW Nachberichte\]\([^)]*\).*$",
        "",
        value,
    )
    value = re.sub(r"&lt;(.*?)&gt;", r"\1", value)
    value = re.sub(r"\s*\|\s*", " ", value).strip()
    value = clean_markdown(value)
    # The eKGWB Markdown mirror joins this bold-span boundary without a space.
    return (
        value
        .replace("Obhutzeigte", "Obhut zeigte")
        .replace("Wagner’sgehabt", "Wagner’s gehabt")
        .replace("Zarathutra", "Zarathustra")
    )


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
        if stripped.startswith(("*Erratum:*", "*lies:*", "[eKGWB Berichtigung]", "[Nach KGW")):
            while cleaned_lines and not cleaned_lines[-1]:
                cleaned_lines.pop()
            correction_gap = True
            continue
        cleaned = clean_new_markdown(stripped) if work in {"ac", "gd", "fw", "za", "eh", "nf"} else clean_markdown(stripped)
        if (
            not cleaned
            or DATE_LINE_RE.match(cleaned)
            or cleaned in {"Der Antichrist", "Götzen-Dämmerung", "Leipzig"}
            or cleaned.startswith("Verlag von ")
            or (
                work == "za"
                and re.match(r"^(?:Zarathustra,|Also sprach Zarathustra\s+\d+\s+p[.])", cleaned)
            )
        ):
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
            # This poem has a subtitle before its thirty verse lines, so the
            # five-line packer leaves its short final line on its own. Keep
            # that conclusion by attaching it to the preceding verse unit.
            if (
                event["title_de"] == "Rimus remedium"
                and len(blocks) >= 2
                and blocks[-1] == "Der gienge drauf!"
            ):
                blocks = [*blocks[:-2], normalize_space(f"{blocks[-2]} / {blocks[-1]}")]
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


def generic_linked_headings(lines: list[str]) -> list[dict]:
    headings: list[dict] = []
    for index, line in enumerate(lines):
        match = PART_LINK_RE.match(line.strip())
        if not match:
            continue
        title = clean_new_markdown(match.group(1)).rstrip(".")
        headings.append({"index": index, "body_start": index + 1, "title": title})
    return headings


def numbered_heading_events(lines: list[str], start: int, end: int) -> list[dict]:
    events: list[dict] = []
    for index in range(start, end):
        match = SECTION_RE.match(lines[index].strip())
        if not match:
            continue
        label = clean_new_markdown(match.group(1)).strip(" .")
        if label.isdigit():
            events.append({"index": index, "body_start": index + 1, "number": label})
    return events


def section_record(
    *,
    part: str,
    part_title_de: str,
    part_title_ko: str,
    section: str,
    section_label: str,
    section_title_de: str,
    section_title_ko: str,
    paragraphs: list[str],
    source_url_value: str,
) -> dict:
    return {
        "part": part,
        "part_title_de": part_title_de,
        "part_title_ko": part_title_ko,
        "section": section,
        "section_label": section_label,
        "section_title_de": section_title_de,
        "section_title_ko": section_title_ko,
        "paragraphs": paragraphs,
        "source_url": source_url_value,
    }


def parse_zarathustra() -> list[dict]:
    sections: list[dict] = []
    files = WORKS["za"]["source_files"]
    if len(files) != len(ZA_PARTS):
        raise ValueError("Zarathustra source file/part count mismatch")
    for part, source_file in zip(ZA_PARTS, files):
        path = ROOT / source_file
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        headings = generic_linked_headings(lines)
        known_titles = set(ZA_CHAPTERS)
        unknown = [
            heading["title"]
            for heading in headings
            if heading["title"] not in known_titles and heading["title"] != "Die Reden Zarathustra’s"
        ]
        if unknown:
            raise ValueError(f"Unmapped Zarathustra headings in {path}: {unknown}")

        part_title_de, part_title_ko = ZA_PARTS[part]
        first_chapter_index = next(heading["index"] for heading in headings if heading["title"] in known_titles)
        if part != "I":
            prelude_start = next(
                (
                    index
                    for index, line in enumerate(lines[:first_chapter_index])
                    if index > 20 and line.strip().startswith(("„", "Ach,"))
                ),
                None,
            )
            if prelude_start is not None:
                prelude = body_blocks(lines[prelude_start:first_chapter_index], work="za")
                if prelude:
                    sections.append(
                        section_record(
                            part=part,
                            part_title_de=part_title_de,
                            part_title_ko=part_title_ko,
                            section="Vorspruch",
                            section_label=f"{part_title_ko} 머리글",
                            section_title_de="Vorspruch",
                            section_title_ko=f"{part_title_ko} 머리글",
                            paragraphs=prelude,
                            source_url_value=f"https://www.nietzschesource.org/eKGWB/Za-{part}",
                        )
                    )

        for position, heading in enumerate(headings):
            if heading["title"] not in known_titles:
                continue
            next_index = headings[position + 1]["index"] if position + 1 < len(headings) else len(lines)
            slug, title_ko = ZA_CHAPTERS[heading["title"]]
            numbered_events = numbered_heading_events(lines, heading["body_start"], next_index)
            if numbered_events:
                for event_position, event in enumerate(numbered_events):
                    body_end = (
                        numbered_events[event_position + 1]["index"]
                        if event_position + 1 < len(numbered_events)
                        else next_index
                    )
                    paragraphs = body_blocks(lines[event["body_start"] : body_end], work="za")
                    if not paragraphs:
                        raise ValueError(f"Empty Za {part} {slug}-{event['number']}")
                    sections.append(
                        section_record(
                            part=part,
                            part_title_de=part_title_de,
                            part_title_ko=part_title_ko,
                            section=f"{slug}-{event['number']}",
                            section_label=f"{title_ko} · §{event['number']}",
                            section_title_de=heading["title"],
                            section_title_ko=title_ko,
                            paragraphs=paragraphs,
                            source_url_value=(
                                f"https://www.nietzschesource.org/eKGWB/Za-{part}-{slug}-{event['number']}"
                            ),
                        )
                    )
            else:
                paragraphs = body_blocks(lines[heading["body_start"] : next_index], work="za")
                if not paragraphs:
                    raise ValueError(f"Empty Za {part} {slug}")
                sections.append(
                    section_record(
                        part=part,
                        part_title_de=part_title_de,
                        part_title_ko=part_title_ko,
                        section=slug,
                        section_label=title_ko,
                        section_title_de=heading["title"],
                        section_title_ko=title_ko,
                        paragraphs=paragraphs,
                        source_url_value=f"https://www.nietzschesource.org/eKGWB/Za-{part}-{slug}",
                    )
                )
    return sections


def parse_ecce_homo(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    headings = generic_linked_headings(lines)
    known_titles = set(EH_PARTS)
    unknown = [heading["title"] for heading in headings if heading["title"] not in known_titles and heading["title"] != "Inhalt"]
    if unknown:
        raise ValueError(f"Unmapped Ecce homo headings in {path}: {unknown}")

    sections: list[dict] = []
    contents_heading = next(heading for heading in headings if heading["title"] == "Inhalt")
    next_after_contents = headings[headings.index(contents_heading) + 1]
    prelude_start = next(
        index
        for index in range(contents_heading["body_start"], next_after_contents["index"])
        if lines[index].strip().startswith("An diesem vollkommnen Tage")
    )
    prelude = body_blocks(lines[prelude_start:next_after_contents["index"]], work="eh")
    sections.append(
        section_record(
            part="Vorspruch",
            part_title_de="Vorspruch",
            part_title_ko="머리글",
            section="Vorspruch",
            section_label="머리글",
            section_title_de="Vorspruch",
            section_title_ko="머리글",
            paragraphs=prelude,
            source_url_value="https://www.nietzschesource.org/eKGWB/EH",
        )
    )

    for position, heading in enumerate(headings):
        if heading["title"] not in known_titles:
            continue
        next_index = headings[position + 1]["index"] if position + 1 < len(headings) else len(lines)
        slug, title_ko = EH_PARTS[heading["title"]]
        numbered_events = numbered_heading_events(lines, heading["body_start"], next_index)
        if not numbered_events:
            section_lines = lines[heading["body_start"] : next_index]
            paragraphs = body_blocks(section_lines, work="eh")
            if slug == "FW":
                cleaned_source_lines = {
                    clean_new_markdown(line.strip())
                    for line in section_lines
                    if line.strip()
                }
                missing_verses = [
                    line for line in EH_JANUARY_VERSE_LINES
                    if line not in cleaned_source_lines
                ]
                if missing_verses:
                    raise ValueError(
                        "Incomplete EH-FW January poem in source snapshot: "
                        f"{missing_verses}"
                    )
                verse_lines = set(EH_JANUARY_VERSE_LINES)
                paragraphs = [
                    paragraph for paragraph in paragraphs
                    if paragraph not in verse_lines and paragraph != "(„la gaya scienza“)"
                ]
                paragraphs.insert(
                    1,
                    normalize_space(" / ".join(EH_JANUARY_VERSE_LINES)),
                )
            if not paragraphs:
                raise ValueError(f"Empty unnumbered EH section {heading['title']}")
            sections.append(
                section_record(
                    part=slug,
                    part_title_de=heading["title"],
                    part_title_ko=title_ko,
                    section="Text",
                    section_label=title_ko,
                    section_title_de=heading["title"],
                    section_title_ko=title_ko,
                    paragraphs=paragraphs,
                    source_url_value=f"https://www.nietzschesource.org/eKGWB/EH-{slug}",
                )
            )
            continue
        for event_position, event in enumerate(numbered_events):
            body_end = (
                numbered_events[event_position + 1]["index"]
                if event_position + 1 < len(numbered_events)
                else next_index
            )
            section_lines = lines[event["body_start"] : body_end]
            paragraphs = body_blocks(section_lines, work="eh")
            if slug == "Klug" and event["number"] == "7":
                cleaned_source_lines = {
                    clean_new_markdown(line.strip())
                    for line in section_lines
                    if line.strip()
                }
                missing_verses = [
                    line for line in EH_VENICE_VERSE_LINES
                    if line not in cleaned_source_lines
                ]
                if missing_verses:
                    raise ValueError(
                        "Incomplete EH-Klug-7 Venice poem in source snapshot: "
                        f"{missing_verses}"
                    )
                verse_lines = set(EH_VENICE_VERSE_LINES)
                paragraphs = [
                    paragraph for paragraph in paragraphs
                    if paragraph not in verse_lines
                ]
                paragraphs.extend(
                    (
                        normalize_space(" / ".join(EH_VENICE_VERSE_LINES[:7])),
                        normalize_space(" / ".join(EH_VENICE_VERSE_LINES[7:])),
                    )
                )
            if slug == "Klug" and event["number"] == "9":
                # Keep the long Ritschl aside inside one balanced parenthesis.
                # A generic length split otherwise leaves two independently
                # displayed quotation records with unmatched brackets.
                ritschl_marker = " (Ritschl —"
                balanced_paragraphs: list[str] = []
                for paragraph in paragraphs:
                    if ritschl_marker in paragraph:
                        lead, aside = paragraph.split(ritschl_marker, 1)
                        balanced_paragraphs.extend((lead.strip(), f"(Ritschl —{aside}".strip()))
                    else:
                        balanced_paragraphs.append(paragraph)
                paragraphs = balanced_paragraphs
            if slug == "Bücher" and event["number"] == "3":
                reader_verses = set(EH_READER_VERSE_LINES)
                if not reader_verses.issubset(set(paragraphs)):
                    raise ValueError("Incomplete EH-Bücher-3 reader verse in source snapshot")
                paragraphs = [
                    paragraph for paragraph in paragraphs
                    if paragraph not in reader_verses
                ] + [normalize_space(" / ".join(EH_READER_VERSE_LINES))]
            if slug == "Bücher" and event["number"] == "5":
                # Keep the two-sentence quotation about chastity together so
                # every independently displayed unit has both quotation marks.
                quotation_marker = " Der Satz heisst: „die Predigt der Keuschheit"
                quoted_paragraphs: list[str] = []
                for paragraph in paragraphs:
                    if quotation_marker in paragraph:
                        lead, quotation = paragraph.split(quotation_marker, 1)
                        quoted_paragraphs.extend(
                            (lead.strip(), f"Der Satz heisst: „die Predigt der Keuschheit{quotation}".strip())
                        )
                    else:
                        quoted_paragraphs.append(paragraph)
                paragraphs = quoted_paragraphs
            if not paragraphs:
                raise ValueError(f"Empty EH {slug}-{event['number']}")
            sections.append(
                section_record(
                    part=slug,
                    part_title_de=heading["title"],
                    part_title_ko=title_ko,
                    section=event["number"],
                    section_label=f"§{event['number']}",
                    section_title_de="",
                    section_title_ko="",
                    paragraphs=paragraphs,
                    source_url_value=f"https://www.nietzschesource.org/eKGWB/EH-{slug}-{event['number']}",
                )
            )
    return sections


NF_FILE_RE = re.compile(r"nf-(188[5-8])-(\d{2})[.]md$")
NF_FRAGMENT_RE = re.compile(r"^\[((\d+)\[(\d+)\])\]\(javascript:;\)\s*$")


def parse_late_nachlass() -> list[dict]:
    sections: list[dict] = []
    paths = sorted(RAW.glob("nf-*.md"))
    if not paths:
        raise ValueError("No late Nachlass source files found")
    for path in paths:
        file_match = NF_FILE_RE.match(path.name)
        if not file_match:
            continue
        year, expected_group = file_match.groups()
        raw_lines = path.read_text(encoding="utf-8-sig").splitlines()
        lines: list[str] = []
        for line in raw_lines:
            malformed_heading = re.match(
                r"^\[(\d+\[\d+\]) \*Erratum:\*\]\(javascript:;\)\s+\[(.*)$",
                line.strip(),
            )
            if malformed_heading:
                lines.extend(
                    [
                        f"[{malformed_heading.group(1)}](javascript:;)",
                        malformed_heading.group(2),
                    ]
                )
            else:
                lines.append(line)
        events: list[dict] = []
        for index, line in enumerate(lines):
            match = NF_FRAGMENT_RE.match(line.strip())
            if not match:
                continue
            citation, group, fragment = match.groups()
            if int(group) != int(expected_group):
                raise ValueError(f"Unexpected group {group} in {path}")
            events.append(
                {
                    "index": index,
                    "body_start": index + 1,
                    "citation": citation,
                    "group": group,
                    "fragment": fragment,
                }
            )
        if not events:
            raise ValueError(f"No Nachlass fragments found in {path}")
        for position, event in enumerate(events):
            next_index = events[position + 1]["index"] if position + 1 < len(events) else len(lines)
            paragraphs = body_blocks(lines[event["body_start"] : next_index], work="nf")
            joined_paragraphs: list[str] = []
            for paragraph in paragraphs:
                if (
                    joined_paragraphs
                    and paragraph[:1].islower()
                    and not re.search(r"[.!?…][”’\"]?$", joined_paragraphs[-1])
                ):
                    joined_paragraphs[-1] = normalize_space(f"{joined_paragraphs[-1]} {paragraph}")
                else:
                    joined_paragraphs.append(paragraph)
            paragraphs = [
                paragraph
                for paragraph in joined_paragraphs
                if len(paragraph) >= 40
                and len(paragraph.split()) >= 5
                and not (
                    len(paragraph) < 120
                    and (paragraph.count("(") != paragraph.count(")") or paragraph.count("[") != paragraph.count("]"))
                )
            ]
            if not paragraphs:
                continue
            citation = event["citation"]
            sections.append(
                section_record(
                    part=f"{year}-{event['group']}",
                    part_title_de=f"Nachgelassene Fragmente {year} · Gruppe {event['group']}",
                    part_title_ko=f"{year}년 · 노트군 {event['group']}",
                    section=citation,
                    section_label=citation,
                    section_title_de="",
                    section_title_ko="",
                    paragraphs=paragraphs,
                    source_url_value=f"https://www.nietzschesource.org/eKGWB/NF-{year},{citation}",
                )
            )
    return sections


ABBREVIATIONS = (
    "Dr.", "Prof.", "resp.", "etc.", "u. s. w.", "u. a.", "z. B.", "Z. B.", "d. h.",
    "vergl.", "vgl.", "S.", "Bd.", "Nr.", "sc.", "ca.", "ff.",
)

PP_CITATION_ABBREVIATIONS = (
    "St.", "V.", "Aufl.", "P.", "p.", "L.", "Art.", "Vol.",
    "Lib.", "lib.", "Liv.", "liv.", "Tom.", "C.", "c.", "ibid.",
    "Med.", "Part.", "publ.", "prop.", "pr.", "schol.", "seqq.",
    "sq.", "Opp.", "opp.", "ed.", "edit.", "cap.", "ch.", "Dial.", "institut.", "vierf.", "spekul.",
    "somn.", "Vergl.", "disp.", "sect.", "Sept.", "i. J.",
    "Arist.", "Cic.", "Clem.", "Alex.", "Apulej.", "Jambl.", "Pyth.",
    "Diog.", "Laert.", "Herod.", "Schol.", "vit.", "Buffon.",
    "adv.", "Math.", "math.", "eth.", "nat.", "Enn.", "a. a. O.",
    "A. T.", "Eth. Pars", "u. A. m.",
)

# Short refrains and closing verse lines that are semantically complete even
# though they fall below the general quote-size threshold. Dialogue cues such
# as "— Weiter!" remain excluded from the random quote pool.
PRESERVE_SHORT_UNITS = {
    "— Ist das noch deutsch? —",
    "— Ist Das noch deutsch?",
    "Mir zu sieben neuen Muth.",
    "Flamme bin ich sicherlich.",
    "Frankfurt a. M. im Dezember 1850.",
}


def protect_abbreviations(
    text: str,
    extra: tuple[str, ...] = (),
    *,
    require_token_boundaries: bool = False,
) -> str:
    protected = text
    for abbreviation in (*ABBREVIATIONS, *extra):
        replacement = abbreviation.replace(".", "∯")
        if require_token_boundaries:
            protected = re.sub(
                rf"(?<!\w){re.escape(abbreviation)}(?=$|[\s)\]}}»”’'\",;:!?—–-])",
                lambda _: replacement,
                protected,
            )
        else:
            protected = protected.replace(abbreviation, replacement)
    protected = re.sub(r"(?<=\d)\.(?=\d)", "∯", protected)
    return protected


ORDINAL_CONTINUATIONS = (
    "Jahrhundert", "Jahrhunderts", "Jahrhunderte", "Jahrhunderten",
    "Aufl", "Auflage", "Auflagen",
    "Kap", "Kapitel", "Buch", "Bücher",
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "Sept", "September", "Oktober", "November", "Dezember",
)


def protect_ordinal_continuations(text: str) -> str:
    """Keep German ordinals with a following century or month name."""
    continuations = "|".join(map(re.escape, ORDINAL_CONTINUATIONS))
    return re.sub(
        rf"\b(\d{{1,2}})\.(?=\s+(?:{continuations})\b)",
        r"\1∯",
        text,
    )


INNER_QUOTE_BOUNDARY_MARKERS = {
    ".": "\ue000",
    "!": "\ue001",
    "?": "\ue002",
    "…": "\ue003",
}


def protect_inner_german_quote_boundaries(text: str) -> str:
    """Protect non-final sentence marks inside a complete German quotation."""

    def protect_match(match: re.Match[str]) -> str:
        content = match.group(1)
        content = re.sub(
            r"([.!?…])(?=\s+(?:[—–-]\s*)?(?:[„‚\"(\[])?[A-ZÄÖÜ])",
            lambda boundary: INNER_QUOTE_BOUNDARY_MARKERS[boundary.group(1)],
            content,
        )
        return f"„{content}“"

    return re.sub(r"„([^„“]*?)“", protect_match, text)


def split_long(
    text: str,
    max_chars: int = 500,
    *,
    prefer_strong_boundaries: bool = False,
    strong_boundary_min_ratio: float = 0.48,
) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    result: list[str] = []
    remaining = text
    while len(remaining) > max_chars:
        window = remaining[: max_chars + 1]
        candidates: list[tuple[int, int]] = []
        boundary_patterns = (
            (r"(?:;|:| —| –)\s+", r",\s+")
            if prefer_strong_boundaries
            else (r"(?:;|:|,| —| –)\s+",)
        )
        for pattern_index, pattern in enumerate(boundary_patterns):
            min_ratio = (
                strong_boundary_min_ratio
                if prefer_strong_boundaries and pattern_index == 0
                else 0.48
            )
            candidates = [
                (match.end(), match.end())
                for match in re.finditer(pattern, window)
                if match.end() >= int(max_chars * min_ratio)
            ]
            if candidates:
                break
        cut = candidates[-1][0] if candidates else window.rfind(" ", int(max_chars * 0.65))
        if cut <= 0:
            cut = max_chars
        result.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        result.append(remaining)
    return result


def merge_tiny(
    parts: list[str],
    min_chars: int = 28,
    min_words: int = 4,
    *,
    preserve_lone: bool = False,
) -> list[str]:
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
        elif preserve_lone or len(pending) >= min_chars:
            merged.append(pending)
    return merged


def sentence_units(
    paragraph: str,
    *,
    max_chars: int = 500,
    extra_abbreviations: tuple[str, ...] = (),
    protect_ordinals: bool = False,
    prefer_strong_boundaries: bool = False,
    strong_boundary_min_ratio: float = 0.48,
    preserve_lone: bool = False,
    protect_citation_initials: bool = False,
    require_abbreviation_token_boundaries: bool = False,
    min_chars: int = 28,
    min_words: int = 4,
    lone_min_chars: int = 28,
    lone_min_words: int = 4,
    protect_inner_german_quotes: bool = False,
) -> list[str]:
    normalized = normalize_space(paragraph)
    if normalized in PRESERVE_SHORT_UNITS:
        return [normalized]
    protected = protect_abbreviations(
        normalized,
        extra_abbreviations,
        require_token_boundaries=require_abbreviation_token_boundaries,
    )
    if protect_citation_initials:
        protected = re.sub(r"(?<!\w)([dv])[.](?=\s+[A-ZÄÖÜ])", r"\1∯", protected)
        protected = re.sub(
            r"\bKap[.]\s+44[.](?=\s+S∯\s+550\b)",
            "Kap∯ 44∯",
            protected,
        )
        protected = re.sub(
            r"(?<=S∯\s)(\d{1,4})[.](?=\s+—\s+\d+[.]\s+Aufl∯)",
            r"\1∯",
            protected,
        )
    if protect_ordinals:
        protected = protect_ordinal_continuations(protected)
    if protect_inner_german_quotes:
        protected = protect_inner_german_quote_boundaries(protected)
    sentence_boundary = (
        r"(?:(?<=[.!?…])|(?<=[.!?…][”’\"“]))\s+(?=(?:[„‚\"(\[])?[A-ZÄÖÜ—–-])"
        if protect_inner_german_quotes
        else r"(?<=[.!?…])(?:[”’\"])?\s+(?=(?:[„‚\"(\[])?[A-ZÄÖÜ—–-])"
    )
    raw = re.split(sentence_boundary, protected)
    restored = []
    for part in raw:
        restored_part = part.replace("∯", ".")
        for punctuation, marker in INNER_QUOTE_BOUNDARY_MARKERS.items():
            restored_part = restored_part.replace(marker, punctuation)
        restored.append(restored_part)
    expanded: list[str] = []
    for part in restored:
        expanded.extend(
            split_long(
                part,
                max_chars=max_chars,
                prefer_strong_boundaries=prefer_strong_boundaries,
                strong_boundary_min_ratio=strong_boundary_min_ratio,
            )
        )
    return merge_tiny(
        expanded,
        min_chars=lone_min_chars if len(expanded) == 1 else min_chars,
        min_words=lone_min_words if len(expanded) == 1 else min_words,
        preserve_lone=preserve_lone,
    )


def quote_units(paragraph: str) -> list[str]:
    return sentence_units(paragraph)


def quote_units_for_work(
    paragraph: str,
    work: str,
    part: str = "",
    section: str = "",
    paragraph_index: int = -1,
) -> list[str]:
    if work in {"jgb", "gm"}:
        return quote_units(paragraph)
    pp_dialectic = work == "pp" and part == "II-02"
    pp_untranslated_chapter = (
        work == "pp"
        and re.fullmatch(r"II-\d{2}", part) is not None
        and int(part[3:]) >= 3
    )
    pp_reflow = pp_untranslated_chapter and (
        int(part[3:]) > 3
        or (
            part == "II-03"
            and re.fullmatch(r"\d+", str(section)) is not None
            and (
                int(str(section)) >= 30
                or (int(str(section)) == 29 and paragraph_index >= 8)
            )
        )
    )
    units = sentence_units(
        paragraph,
        max_chars=(780 if pp_reflow else 720 if pp_untranslated_chapter else 640 if pp_dialectic else 650),
        extra_abbreviations=PP_CITATION_ABBREVIATIONS if work == "pp" else ("St.", "V."),
        protect_ordinals=work in {"za", "eh", "nf", "pp"},
        prefer_strong_boundaries=(
            (work == "eh" and part == "Za")
            or pp_dialectic
            or pp_untranslated_chapter
        ),
        strong_boundary_min_ratio=0.25 if pp_untranslated_chapter else 0.48,
        preserve_lone=work in {"za", "pp"},
        protect_citation_initials=work == "pp",
        require_abbreviation_token_boundaries=pp_untranslated_chapter,
        min_chars=40 if work == "pp" else 28,
        min_words=5 if work == "pp" else 4,
        protect_inner_german_quotes=(
            work == "pp"
            and part == "II-10"
            and section == "Anhang-verwandter-Stellen"
        ),
    )
    packed: list[str] = []
    current = ""
    pack_max_chars = 780 if pp_reflow else 500
    pp_attach_leading_parentheticals = pp_reflow and (
        int(part[3:]) > 3
        or (part == "II-03" and re.fullmatch(r"\d+", str(section)) is not None and int(str(section)) >= 51)
    )
    for unit in units:
        candidate = normalize_space(f"{current} {unit}")
        if current and len(candidate) > pack_max_chars:
            leading_parenthetical = (
                re.match(r"^(\([^()]{1,240}\))\s+(.+)$", unit)
                if pp_attach_leading_parentheticals
                else None
            )
            current_with_citation = (
                normalize_space(f"{current} {leading_parenthetical.group(1)}")
                if leading_parenthetical
                else ""
            )
            if leading_parenthetical and len(current_with_citation) <= 820:
                packed.append(current_with_citation)
                current = leading_parenthetical.group(2)
            else:
                packed.append(current)
                current = unit
        else:
            current = candidate
    if current:
        packed.append(current)
    # Keep a trailing bibliographic parenthesis attached when an author
    # abbreviation caused the citation to split at the packing boundary.
    # The quoted sentence and its source belong to one readable unit.
    citation_rejoined: list[str] = []
    for unit in packed:
        speaker_boundary = (
            re.search(r"\s((?:Thrasymachos|Philalethes)[.])$", citation_rejoined[-1])
            if citation_rejoined and unit.startswith("—")
            else None
        )
        if speaker_boundary:
            # A long dialogue turn can hit the pack limit directly after the
            # next speaker's label.  Carry that label into the continuation
            # instead of leaving it stranded at the end of the prior quote.
            speaker = speaker_boundary.group(1)
            citation_rejoined[-1] = citation_rejoined[-1][
                : speaker_boundary.start()
            ].rstrip()
            unit = normalize_space(f"{speaker} {unit}")
        world_citation = "II, p. 226 fg.; 3. Aufl. II, 251 fg.)"
        if (
            citation_rejoined
            and citation_rejoined[-1].endswith("(Vergl. Welt als Wille u. Vorstell.")
            and unit.startswith(world_citation)
            and len(normalize_space(f"{citation_rejoined[-1]} {world_citation}")) <= 820
        ):
            citation_rejoined[-1] = normalize_space(
                f"{citation_rejoined[-1]} {world_citation}"
            )
            remainder = normalize_space(unit[len(world_citation) :])
            if remainder:
                citation_rejoined.append(remainder)
            continue
        if (
            citation_rejoined
            and citation_rejoined[-1].endswith("(S. Ed.")
            and unit.startswith("Boas, Schiller und Göthe im Xenienkampf")
        ):
            citation_rejoined[-1] = normalize_space(f"{citation_rejoined[-1]} {unit}")
        elif (
            citation_rejoined
            and citation_rejoined[-1].endswith("Ausspruch des J.")
            and unit.startswith("Brunus (ed. Wagner")
            and len(normalize_space(f"{citation_rejoined[-1]} {unit}")) <= 820
        ):
            citation_rejoined[-1] = normalize_space(f"{citation_rejoined[-1]} {unit}")
        elif (
            citation_rejoined
            and citation_rejoined[-1].endswith("(1.")
            and unit.startswith("Mos. 17, 8.),")
            and len(
                normalize_space(f"{citation_rejoined[-1]} Mos. 17, 8.),")
            )
            <= 820
        ):
            # Do not leave the tail of Genesis 17:8 as a standalone quote.
            # Only attach the citation; the following prose remains its own
            # readable unit when the pack boundary requires it.
            citation_rejoined[-1] = normalize_space(
                f"{citation_rejoined[-1]} Mos. 17, 8.),"
            )
            remainder = normalize_space(unit[len("Mos. 17, 8.),") :])
            if remainder:
                citation_rejoined.append(remainder)
        else:
            citation_rejoined.append(unit)
    packed = citation_rejoined
    return packed


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
        author_key = metadata.get("author", "nietzsche")
        author = AUTHORS[author_key]
        if work == "za":
            sections = parse_zarathustra()
        elif work == "eh":
            sections = parse_ecce_homo(ROOT / metadata["source_file"])
        elif work == "nf":
            sections = parse_late_nachlass()
        elif work == "pp":
            sections = parse_parerga()
        else:
            sections = parse_markdown_work(ROOT / metadata["source_file"], work)
        for section_data in sections:
            paragraph_count = len(section_data["paragraphs"])
            for paragraph_index, paragraph in enumerate(section_data["paragraphs"]):
                paragraph_text = paragraph["text"] if isinstance(paragraph, dict) else paragraph
                source_notes = paragraph.get("source_notes", {}) if isinstance(paragraph, dict) else {}
                units = quote_units_for_work(
                    paragraph_text,
                    work,
                    section_data["part"],
                    str(section_data["section"]),
                    paragraph_index,
                )
                if work in {"za", "pp"} and paragraph_text.strip() and not units:
                    raise ValueError(
                        f"{work.upper()} source block disappeared during quote splitting: "
                        f"{section_data['part']} {section_data['section']} paragraph {paragraph_index}"
                    )
                for sentence_index, marked_german in enumerate(units):
                    german, source_note_refs = (
                        strip_note_markers(marked_german)
                        if work == "pp"
                        else (marked_german, [])
                    )
                    quote_id = stable_id(
                        work,
                        section_data["part"],
                        section_data.get("id_section", section_data["section"]),
                        paragraph_index,
                        german,
                    )
                    translation = translations.get(quote_id, {})
                    korean = translation.get("korean", "") if isinstance(translation, dict) else str(translation)
                    editorial_footnotes = translation.get("footnotes", []) if isinstance(translation, dict) else []
                    source_footnotes = [
                        source_notes[ref]
                        for ref in dict.fromkeys(source_note_refs)
                        if ref in source_notes
                    ]
                    footnotes = source_footnotes + editorial_footnotes
                    record = {
                        "id": quote_id,
                        "author": author_key,
                        "authorNameDe": author["name_de"],
                        "authorNameKo": author["name_ko"],
                        "work": work,
                        "workTitleDe": metadata["title_de"],
                        "workTitleKo": metadata["title_ko"],
                        "edition": metadata.get("edition", "eKGWB"),
                        "editor": metadata.get("editor", ""),
                        "transcriptionStatus": metadata.get("transcription_status", "검증 완료"),
                        "volume": section_data.get("volume", ""),
                        "volumeTitleDe": section_data.get("volume_title_de", ""),
                        "volumeTitleKo": section_data.get("volume_title_ko", ""),
                        "part": section_data["part"],
                        "partTitleDe": section_data["part_title_de"],
                        "partTitleKo": section_data["part_title_ko"],
                        "section": section_data["section"],
                        "sectionLabel": section_data.get("section_label", ""),
                        "sectionTitleDe": section_data.get("section_title_de", ""),
                        "sectionTitleKo": section_data.get("section_title_ko", ""),
                        "paragraph": paragraph_index,
                        "paragraphCount": paragraph_count,
                        "sentence": sentence_index,
                        "german": german,
                        "korean": korean.strip(),
                        "translationStatus": translation.get("status", "pending") if isinstance(translation, dict) else "draft",
                        "footnotes": footnotes,
                        "sourceUrl": (
                            section_data["source_url"]
                            if "source_url" in section_data
                            else source_url(work, section_data["part"], section_data["section"])
                        ),
                        "sourceFile": section_data.get("source_file", metadata.get("source_file", "")),
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

    widget_fields = (
        "id", "author", "authorNameKo", "work", "workTitleKo", "part", "partTitleKo", "section", "sectionLabel",
        "paragraph", "paragraphCount", "sentence", "german", "korean",
    )
    widget_quotes = [
        {field: quote[field] for field in widget_fields}
        for quote in quotes
    ]
    write_json(DATA / "widget.json", widget_quotes, compact=True)

    widget_shard_dir = DATA / "widget-shards"
    widget_shard_works = {}
    widget_offset = 0
    for work in WORK_ORDER:
        work_widget_quotes = [quote for quote in widget_quotes if quote["work"] == work]
        shard_count = (len(work_widget_quotes) + WIDGET_SHARD_SIZE - 1) // WIDGET_SHARD_SIZE
        for shard_index in range(shard_count):
            start = shard_index * WIDGET_SHARD_SIZE
            shard = work_widget_quotes[start : start + WIDGET_SHARD_SIZE]
            write_json(
                widget_shard_dir / f"{work}-{shard_index:03d}.json",
                shard,
                compact=True,
            )
        widget_shard_works[work] = {
            "offset": widget_offset,
            "count": len(work_widget_quotes),
            "shardCount": shard_count,
        }
        widget_offset += len(work_widget_quotes)

    corpus_identity = "\n".join(f"{quote['id']}\0{quote['german']}" for quote in quotes)
    corpus_version = hashlib.sha256(corpus_identity.encode("utf-8")).hexdigest()[:16]
    data_identity = json.dumps(quotes, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    data_version = hashlib.sha256(data_identity.encode("utf-8")).hexdigest()[:16]
    translated = sum(bool(quote["korean"]) for quote in quotes)
    reviewed = sum(quote["translationStatus"] == "reviewed" for quote in quotes)
    manifest = {
        "schemaVersion": 3,
        "corpusVersion": corpus_version,
        "dataVersion": data_version,
        "quoteCount": len(quotes),
        "translatedCount": translated,
        "widgetQuoteCount": len(widget_quotes),
        "reviewedCount": reviewed,
        "pendingTranslationCount": len(quotes) - translated,
        "widgetShards": {
            "schemaVersion": 1,
            "basePath": "data/widget-shards",
            "shardSize": WIDGET_SHARD_SIZE,
            "totalCount": len(widget_quotes),
            "workOrder": list(WORK_ORDER),
            "works": widget_shard_works,
        },
        "authors": {
            author_key: {
                "nameDe": author["name_de"],
                "nameKo": author["name_ko"],
                "count": sum(quote["author"] == author_key for quote in quotes),
                "works": [
                    work for work in WORK_ORDER
                    if WORKS[work].get("author", "nietzsche") == author_key
                ],
            }
            for author_key, author in AUTHORS.items()
        },
        "works": {
            work: {
                "author": WORKS[work].get("author", "nietzsche"),
                "titleDe": WORKS[work]["title_de"],
                "titleKo": WORKS[work]["title_ko"],
                "edition": WORKS[work].get("edition", "eKGWB"),
                "editor": WORKS[work].get("editor", ""),
                "transcriptionStatus": WORKS[work].get("transcription_status", "검증 완료"),
                "count": len(by_work[work]),
                "reviewedCount": sum(
                    quote["translationStatus"] == "reviewed" for quote in by_work[work]
                ),
            }
            for work in WORK_ORDER
        },
        "files": {
            "quotes": file_descriptor(DATA / "quotes.json", len(quotes)),
            "widget": file_descriptor(DATA / "widget.json", len(widget_quotes)),
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
