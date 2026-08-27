#!/usr/bin/env python3
"""Parse the pinned Perseus TEI editions of Seneca into traceable reading units."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path


TEI = "{http://www.tei-c.org/ns/1.0}"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
SKIP_TEXT = {"note", "pb", "milestone", "fw", "ref"}
LATIN_INITIAL_RE = re.compile(r"\b(?:A|Ap|C|Cn|D|K|L|M|Mam|N|P|Q|S|Ser|Sex|Sp|T|Ti|V)\.")
COMMON_ABBREVIATIONS = (
    "a. d.", "a. u. c.", "c.", "cf.", "e. g.", "i. e.", "lib.", "n.",
    "p.", "pp.", "sc.", "v.", "vol.",
)


WORK_CONFIG = {
    "dbv": {
        "source": "dbv-perseus.xml",
        "urn": "urn:cts:latinLit:stoa0255.stoa004",
        "citation": "chapter",
        "part": "Text",
        "part_title_original": "Ad Paulinum",
        "part_title_ko": "파울리누스에게",
    },
    "em": {
        "source": "em-perseus.xml",
        "urn": "urn:cts:latinLit:phi1017.phi015",
        "citation": "letter",
    },
    "dta": {
        "source": "dta-perseus.xml",
        "urn": "urn:cts:latinLit:stoa0255.stoa013",
        "citation": "chapter",
        "part": "Text",
        "part_title_original": "Ad Serenum",
        "part_title_ko": "세레누스에게",
    },
    "dvb": {
        "source": "dvb-perseus.xml",
        "urn": "urn:cts:latinLit:stoa0255.stoa014",
        "citation": "chapter",
        "part": "Text",
        "part_title_original": "Ad Gallionem",
        "part_title_ko": "갈리오에게",
    },
    "di": {
        "source": "di-perseus.xml",
        "urn": "urn:cts:latinLit:stoa0255.stoa010",
        "citation": "chapter",
    },
    "dc": {
        "source": "dc-perseus.xml",
        "urn": "urn:cts:latinLit:phi1017.phi014",
        "citation": "chapter",
    },
    "dp": {
        "source": "dp-perseus.xml",
        "urn": "urn:cts:latinLit:stoa0255.stoa012",
        "citation": "chapter",
        "part": "Text",
        "part_title_original": "Ad Lucilium",
        "part_title_ko": "루킬리우스에게",
    },
}


# The pinned Basore TEI is our reproducible source, but a handful of obvious
# character-recognition errors remain in its transcription. Keep the raw XML
# untouched and apply only context-specific corrections to reading text.
WORK_TEXT_CORRECTIONS = {
    "dta": (
        ("nostrum eum quodam", "nostrum cum quodam"),
        ("in fidem eum armis", "in fidem cum armis"),
        ("exemplar, eum inter", "exemplar, cum inter"),
        ("qui eum amicorum officiis", "qui cum amicorum officiis"),
        ("patientiam, eum iis", "patientiam, cum iis"),
        ("eum monstraretur", "cum monstraretur"),
        ("praesertim eum in", "praesertim cum in"),
        ("quae eum sciret", "quae cum sciret"),
        ("Nee enim is solus", "Nec enim is solus"),
        ("in Corinthia pietasque tabulas", "in Corinthia pictasque tabulas"),
        ("formicis per arbusta Tepentibus", "formicis per arbusta repentibus"),
        ("nomeneulatores", "nomenclatores"),
        ("natus est, eum Gaio", "natus est, cum Gaio"),
        ("Cane, nune cogitas", "Cane, nunc cogitas"),
        ("nisi eum expedit", "nisi cum expedit"),
        ("non flere, eum omnes", "non flere, cum omnes"),
        ("ut nune mos est", "ut nunc mos est"),
        ("exhauriet'numquam", "exhauriet numquam"),
        ("Aristoteli'nullum", "Aristoteli 'nullum"),
    ),
    "dvb": (
        ("Nostram autem eum dico", "Nostram autem cum dico"),
        ("parva ae fragilia", "parva ac fragilia"),
        ("si e vagari velis", "si evagari velis"),
        ("in iliis qui summum", "in illis qui summum"),
        ("non honestaquaedam vero", "non honesta; quaedam vero"),
        ("quae eum cursum suum", "quae cum cursum suum"),
        ("delicias fluentis", "deliciis fluentis"),
        ("aurem pervenit", "aurem pervellit"),
        ("quod dest aliquid tibi", "quod deest aliquid tibi"),
        ("Quod arte alligati sunt", "Quod arcte alligati sunt"),
        ("ob aliquam eximiam laudent virorum", "ob aliquam eximiam laudem virorum"),
        ("Quid mirum, eum loquantur", "Quid mirum, cum loquantur"),
        ("in ahenam contumeliam", "in alienam contumeliam"),
        ("donabit eum summo consilio", "donabit cum summo consilio"),
        ("deprenditur diei bonum", "deprenditur dici bonum"),
        ("superbi ae feri", "superbi ac feri"),
        ("tela vestra Agantur", "tela vestra agantur"),
        ("Otiosi divitiis Inditis", "Otiosi divitiis luditis"),
        ("ipsam ut deos ae professores", "ipsam ut deos ac professores"),
        ("invicem mutum alentes stuporem", "invicem mutuum alentes stuporem"),
    ),
    "dp": (
        ("quibus virium cura est, eum fortissimis", "quibus virium cura est, cum fortissimis"),
        ("quibus e veniunt ista", "quibus eveniunt ista"),
        ("bellum tam eum Pyrrho quam eum divitiis", "bellum tam cum Pyrrho quam cum divitiis"),
        ("quibus parcere, molles Venturis malis", "quibus parcere, molles venturis malis"),
        ("in vanas mentes imagines evocat", "in vanas mentem imagines evocat"),
        ("agilia Sunt membra", "agilia sunt membra"),
        ("bonis viris tribu erit", "bonis viris tribuerit"),
        ("et Elius leno", "et Aelius leno"),
        ("in campo Otium suum Oblectet", "in campo otium suum oblectet"),
        ("fortiter Omne patiendum", "fortiter omne patiendum"),
    ),
    "dc": (
        ("nisi quod iudex severus absolvent", "nisi quod iudex severus absolverit"),
        ("constat, eum hanc poenam", "constat, cum hanc poenam"),
        ("Hoc est ignoscere, eum scias", "Hoc est ignoscere, cum scias"),
        ("Magnos et Felices et Angustos diximus", "Magnos et Felices et Augustos diximus"),
        ("filio adulescentulo impulse in id scelus", "filio adulescentulo impulso in id scelus"),
        ("bonitatem tuam eum fortuna tua litigantem", "bonitatem tuam cum fortuna tua litigantem"),
        ("par error est a vero recedendum", "par error est a vero recedentium"),
        ("liquidum socerumque ex turbido", "liquidum sincerumque ex turbido"),
        ("quae, qui miserentur, volo facere", "quae, qui miserentur, volunt facere"),
        ("ob erus alicuius aridum", "ob crus alicuius aridum"),
        ("Agricolas bonos mutabitur", "Agricolas bonos imitabitur"),
        ("in rectum prava Sectantur", "in rectum prava flectantur"),
    ),
}


def _repair_cross_section_breaks(
    work: str,
    book: str,
    citation: str,
    paragraphs: list[dict],
) -> None:
    """Move an editorially stranded phrase to the section it grammatically opens."""
    moves: tuple[tuple[str, str, str, str], ...] = ()
    if work == "dvb" and citation == "25":
        moves = (("1", "2", "Pone in", "instrumentis"),)
    elif work == "dc" and book == "1":
        moves = {
            "1": (("5", "6", "nemo iam divum Augustum nec Ti.", "Caesaris"),),
            "2": (("1", "2", "Non tamen vulgo ignoscere decet;", "nam"),),
            "18": (("1", "2", "Servis ad statuam licet confugere;", "cum"),),
        }.get(citation, ())
    elif work == "dc" and book == "2" and citation == "5":
        moves = (("4", "5", "Maeror contundit mentes, abicit, contrahit;", "hoc"),)

    for left_section, right_section, stranded, right_start in moves:
        left = next(item for item in paragraphs if item["source_section"] == left_section)
        right = next(item for item in paragraphs if item["source_section"] == right_section)
        if not left["text"].endswith(stranded) or not right["text"].startswith(right_start):
            raise ValueError(
                f"unexpected {work.upper()} {book}.{citation} cross-section text"
            )
        left["text"] = left["text"][: -len(stranded)].rstrip()
        right["text"] = normalize_latin(f"{stranded} {right['text']}")
        if right["text"]:
            right["text"] = right["text"][0].upper() + right["text"][1:]


def local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _text_without_apparatus(element: ET.Element) -> str:
    """Return reading text, excluding page furniture and critical apparatus."""
    parts: list[str] = []
    if element.text:
        parts.append(element.text)
    for child in element:
        name = local_name(child)
        if name == "choice":
            preferred = next(
                (child.find(f"{TEI}{tag}") for tag in ("corr", "reg") if child.find(f"{TEI}{tag}") is not None),
                None,
            )
            if preferred is None and len(child):
                preferred = child[0]
            if preferred is not None:
                parts.append(_text_without_apparatus(preferred))
        elif name == "gap":
            parts.append(" […] ")
        elif name not in SKIP_TEXT:
            parts.append(_text_without_apparatus(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def normalize_latin(text: str) -> str:
    text = text.replace("\u00a0", " ")
    # The Basore TEI snapshots retain some print line-end hyphenation as
    # ``num- quam``.  A hyphen followed by layout whitespace inside two
    # alphabetic runs is therefore a broken word, not Latin punctuation.
    text = re.sub(r"(?<=[^\W\d_])-\s+(?=[^\W\d_])", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([‘'\"])[ ]+", r"\1", text)
    text = re.sub(r"[ ]+([’'\"])", r"\1", text)
    return text


def _protect_abbreviations(text: str) -> str:
    marker = "\u2024"
    text = LATIN_INITIAL_RE.sub(lambda match: match.group(0).replace(".", marker), text)
    for abbreviation in COMMON_ABBREVIATIONS:
        pattern = re.compile(re.escape(abbreviation), re.IGNORECASE)
        text = pattern.sub(lambda match: match.group(0).replace(".", marker), text)
    return text


def _restore_abbreviations(text: str) -> str:
    return text.replace("\u2024", ".")


def _split_long_unit(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    pieces = [text]
    for punctuation in (";", ":", ","):
        expanded: list[str] = []
        for piece in pieces:
            if len(piece) <= limit:
                expanded.append(piece)
                continue
            candidates = [match.end() for match in re.finditer(re.escape(punctuation) + r"\s+", piece)]
            start = 0
            while len(piece) - start > limit and candidates:
                viable = [position for position in candidates if start + 120 <= position <= start + limit]
                if not viable:
                    break
                target = start + min(limit, max(180, limit * 2 // 3))
                cut = min(viable, key=lambda position: abs(position - target))
                expanded.append(piece[start:cut].strip())
                start = cut
                candidates = [position for position in candidates if position > start]
            remainder = piece[start:].strip()
            if remainder:
                expanded.append(remainder)
        pieces = expanded
    return pieces


def split_latin_units(text: str, *, limit: int = 680) -> list[str]:
    """Pack complete sentences into readable source-section units."""
    protected = _protect_abbreviations(normalize_latin(text))
    raw = re.split(r"(?<=[.!?])\s+(?=[\"'‘“(\[]?[A-ZĀĒĪŌŪÆ])", protected)
    sentences: list[str] = []
    for item in raw:
        restored = normalize_latin(_restore_abbreviations(item))
        if restored:
            sentences.extend(_split_long_unit(restored, limit))

    units: list[str] = []
    current = ""
    for sentence in sentences:
        combined = normalize_latin(f"{current} {sentence}") if current else sentence
        if current and len(combined) > limit:
            units.append(current)
            current = sentence
        else:
            current = combined
    if current:
        units.append(current)

    merged: list[str] = []
    for unit in units:
        if len(unit) < 24 and merged:
            merged[-1] = normalize_latin(f"{merged[-1]} {unit}")
        else:
            merged.append(unit)
    if len(merged) > 1 and len(merged[0]) < 24:
        merged[1] = normalize_latin(f"{merged[0]} {merged[1]}")
        merged.pop(0)
    return merged


def _direct_children(element: ET.Element, subtype: str) -> list[ET.Element]:
    return [
        child
        for child in element
        if local_name(child) == "div" and child.get("subtype") == subtype
    ]


def parse_seneca(path: Path, work: str) -> list[dict]:
    config = WORK_CONFIG[work]
    root = ET.parse(path).getroot()
    edition = next(
        element
        for element in root.iter(f"{TEI}div")
        if element.get("type") == "edition"
    )
    books = _direct_children(edition, "book")
    section_kind = config["citation"]
    output: list[dict] = []

    for book in books:
        book_number = book.get("n", "")
        if section_kind == "letter":
            cited_sections = _direct_children(book, "letter")
            part = f"Liber-{book_number}"
            part_title_original = f"Liber {book_number}"
            part_title_ko = f"제{book_number}권"
        else:
            cited_sections = _direct_children(book, "chapter")
            if "part" in config:
                part = config["part"]
                part_title_original = config["part_title_original"]
                part_title_ko = config["part_title_ko"]
            else:
                part = f"Liber-{book_number}"
                part_title_original = f"Liber {book_number}"
                part_title_ko = f"제{book_number}권"

        for cited in cited_sections:
            citation_number = cited.get("n", "")
            source_sections = _direct_children(cited, "section")
            paragraphs: list[dict] = []
            for source_section in source_sections:
                source_number = source_section.get("n", "")
                paragraph_nodes = source_section.findall(f"./{TEI}p")
                if not paragraph_nodes:
                    paragraph_nodes = [source_section]
                for source_paragraph, node in enumerate(paragraph_nodes):
                    text = normalize_latin(_text_without_apparatus(node))
                    for before, after in WORK_TEXT_CORRECTIONS.get(work, ()):
                        text = text.replace(before, after)
                    if not text:
                        continue
                    paragraphs.append(
                        {
                            "text": text,
                            "source_section": source_number,
                            "source_paragraph": source_paragraph,
                            "source_paragraph_count": len(paragraph_nodes),
                        }
                    )

            _repair_cross_section_breaks(work, book_number, citation_number, paragraphs)

            if not paragraphs:
                continue
            label = (
                f"제{citation_number}서한"
                if section_kind == "letter"
                else f"제{citation_number}장"
            )
            output.append(
                {
                    "part": part,
                    "part_title_original": part_title_original,
                    "part_title_ko": part_title_ko,
                    "section": citation_number,
                    "section_label": label,
                    "paragraphs": paragraphs,
                    "source_file": f"sources/raw/seneca/{config['source']}",
                    "source_url": (
                        "https://atlas.perseus.tufts.edu/library/"
                        f"{config['urn']}/"
                    ),
                }
            )
    return output


def parse_work(root: Path, work: str) -> list[dict]:
    return parse_seneca(root / WORK_CONFIG[work]["source"], work)
