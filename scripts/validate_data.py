#!/usr/bin/env python3
"""Validate corpus structure, IDs, source coverage, and quote sizing."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from translation_sources import load_translations


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
WORKS = ("jgb", "gm", "ac", "gd", "fw", "za", "eh", "nf", "pp")
LEGACY_REVIEWED_WORKS = {"jgb", "gm", "ac", "gd", "fw"}
ORDINAL_CONTINUATION_RE = re.compile(
    r"^(?:Jahrhundert(?:s|e|en)?|"
    r"Aufl(?:age|agen)?|"
    r"Kap(?:itel)?|B(?:uch|ücher)|"
    r"Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\b"
)

PP_CITATION_FRAGMENT_RE = re.compile(
    r"\b(?:spekul|edit|somn|vergl|Arist|Cic|Clem|Alex|Apulej|Jambl|Pyth|"
    r"Diog|Laert|Herod|Schol|vit|adv|Math|Enn)\.$",
    re.IGNORECASE,
)
PP_LOWER_CITATION_FRAGMENT_RE = re.compile(
    r"(?:\b(?:eth|nat)\.|\ba\. a\. O\.)$"
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
            source_bytes = source_path.read_bytes()
            normalized_source = (
                source_bytes
                if source_path.suffix.lower() == ".epub"
                else source_bytes.replace(b"\r\n", b"\n")
            )
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

    pp_sections = sections["pp"]
    pp_numbered = {section for _, section in pp_sections if section[:1].isdigit()}
    expected_pp = numbered(1, 413) - {"90", "103"} | {"90a", "90b", "103a", "103b"}
    if pp_numbered != expected_pp:
        fail("Parerga numbered section coverage mismatch")
    if len({part for part, _ in pp_sections}) != 45 or len(pp_sections) != 458:
        fail("Parerga volume/chapter coverage mismatch")


def main() -> None:
    quotes = json.loads((DATA / "quotes.json").read_text(encoding="utf-8"))
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    translation_cache = load_translations()
    source_manifest = json.loads((ROOT / "sources" / "sources.json").read_text(encoding="utf-8"))
    required = {
        "id", "author", "authorNameDe", "authorNameKo", "work", "workTitleDe", "workTitleKo", "part", "section",
        "paragraph", "paragraphCount", "sentence", "german", "korean", "footnotes",
    }

    if len(quotes) < 24_000:
        fail(f"expected at least 24,000 quote units, found {len(quotes)}")
    if manifest.get("quoteCount") != len(quotes):
        fail("manifest quoteCount does not match quotes.json")
    check_source_hashes(source_manifest)

    ids: set[str] = set()
    translated_ids: set[str] = set()
    sections: dict[str, set[tuple[str, str]]] = defaultdict(set)
    work_counts: Counter[str] = Counter()
    paragraph_coverage: dict[tuple[str, str, str], set[int]] = defaultdict(set)
    paragraph_counts: dict[tuple[str, str, str], int] = {}
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
        expected_author = "schopenhauer" if quote["work"] == "pp" else "nietzsche"
        if quote["author"] != expected_author:
            fail(f"invalid author in {quote['id']}")
        if not isinstance(quote["paragraph"], int) or quote["paragraph"] < 0:
            fail(f"invalid paragraph in {quote['id']}")
        if not isinstance(quote["paragraphCount"], int) or quote["paragraphCount"] < 1:
            fail(f"invalid paragraph count in {quote['id']}")
        if quote["paragraph"] >= quote["paragraphCount"]:
            fail(f"paragraph exceeds paragraph count in {quote['id']}")
        if not isinstance(quote["sentence"], int) or quote["sentence"] < 0:
            fail(f"invalid sentence in {quote['id']}")
        if (
            len(quote["german"]) < 24
            and quote["work"] not in {"za", "pp"}
            and quote["id"] not in preserved_short_ids
        ):
            fail(f"too-short German unit {quote['id']}: {quote['german']!r}")
        # Parerga occasionally needs the complete quoted sentence plus its
        # parenthetical source; the reflow packer deliberately permits 820.
        # The Cid comparison is one grammatical sentence whose source and
        # assessment become misleading if detached, so retain its modest
        # 838-character overrun as a named exception.
        max_german_chars = (
            1400
            if quote["work"] == "pp"
            and quote["part"] == "II-22"
            and quote["section"] == "278"
            and quote["paragraph"] == 0
            else 850
            if quote["id"] == "pp-180-cabdd951e06e"
            else 820
            if quote["work"] == "pp"
            else 700
        )
        if len(quote["german"]) > max_german_chars:
            fail(f"too-long German unit {quote['id']}: {len(quote['german'])} chars")
        valid_source = (
            quote.get("sourceUrl", "").startswith("https://www.nietzschesource.org/")
            if quote["work"] != "pp"
            else quote.get("sourceUrl", "").startswith("https://books.google.com/")
        )
        if not valid_source:
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
        paragraph_key = (quote["work"], quote["part"], str(quote["section"]))
        paragraph_coverage[paragraph_key].add(quote["paragraph"])
        previous_count = paragraph_counts.setdefault(paragraph_key, quote["paragraphCount"])
        if previous_count != quote["paragraphCount"]:
            fail(f"inconsistent paragraph count in {quote['id']}")

    for paragraph_key, count in paragraph_counts.items():
        if paragraph_key[0] not in {"za", "pp"}:
            continue
        missing_paragraphs = set(range(count)) - paragraph_coverage[paragraph_key]
        if missing_paragraphs:
            fail(
                "source paragraph coverage gap in "
                f"{paragraph_key[1]} {paragraph_key[2]}: {sorted(missing_paragraphs)[:10]}"
            )

    cache_ids = set(translation_cache)
    pp_long_clause_splits: list[tuple[dict, dict]] = []
    for current, following in zip(quotes, quotes[1:]):
        same_paragraph = all(
            current[field] == following[field]
            for field in ("work", "part", "section", "paragraph")
        )
        if (
            current["work"] in {"za", "eh", "nf", "pp"}
            and same_paragraph
            and re.search(r"\b\d{1,2}\.$", current["german"])
            and ORDINAL_CONTINUATION_RE.match(following["german"])
        ):
            fail(
                f"split German ordinal across quote boundary: "
                f"{current['id']} -> {following['id']}"
            )
        if (
            current["work"] in {"za", "eh", "nf", "pp"}
            and same_paragraph
            and re.search(r"\bV[.]$", current["german"])
        ):
            fail(
                f"split abbreviated name across quote boundary: "
                f"{current['id']} -> {following['id']}"
            )
        if (
            current["work"] == "pp"
            and same_paragraph
            and (
                PP_CITATION_FRAGMENT_RE.search(current["german"])
                or PP_LOWER_CITATION_FRAGMENT_RE.search(current["german"])
            )
        ):
            fail(
                f"split German citation abbreviation across quote boundary: "
                f"{current['id']} -> {following['id']}"
            )
        if (
            current["work"] == "pp"
            and same_paragraph
            and re.fullmatch(r"II-\d{2}", current["part"])
            and current["part"] != "II-01"
            and current["german"].endswith(",")
            and re.match(r"[a-zäöü]", following["german"])
        ):
            if current["part"] == "II-02":
                fail(
                    f"split Parerga dialectic clause at a comma: "
                    f"{current['id']} -> {following['id']}"
                )
            pp_long_clause_splits.append((current, following))
        if (
            current["work"] == "pp"
            and same_paragraph
            and current["german"].endswith(" Z.")
            and following["german"].startswith("B. ")
        ):
            fail(
                f"split German Z. B. abbreviation across quote boundary: "
                f"{current['id']} -> {following['id']}"
            )
        if (
            current["work"] == "pp"
            and same_paragraph
            and current["german"].endswith(" A.")
            and following["german"].startswith("T. ")
        ):
            fail(
                f"split German A. T. abbreviation across quote boundary: "
                f"{current['id']} -> {following['id']}"
            )
        if (
            current["work"] == "pp"
            and same_paragraph
            and current["german"].endswith("(Eth.")
            and following["german"].startswith("Pars ")
        ):
            fail(
                f"split Spinoza Ethics citation across quote boundary: "
                f"{current['id']} -> {following['id']}"
            )
        if (
            current["work"] == "pp"
            and same_paragraph
            and current["german"].endswith(" u.")
            and following["german"].startswith("A. m. ")
        ):
            fail(
                f"split German u. A. m. abbreviation across quote boundary: "
                f"{current['id']} -> {following['id']}"
            )
    if len(pp_long_clause_splits) > 12 or any(
        len(current["german"]) < 600 for current, _ in pp_long_clause_splits
    ):
        fail(
            "too many or too-short Parerga weak clause boundaries: "
            f"{len(pp_long_clause_splits)}"
        )

    pp_broken_volume_citations = [
        (current, following)
        for current, following in zip(quotes, quotes[1:])
        if current["work"] == following["work"] == "pp"
        and current["paragraph"] == following["paragraph"]
        and re.search(r"\b\d{1,2}[.]$", current["german"])
        and re.match(r"(?:Band|Bande|Bänden)\b", following["german"])
    ]
    if pp_broken_volume_citations:
        current, following = pp_broken_volume_citations[0]
        fail(
            "split German volume citation across quote boundary: "
            f"{current['id']} -> {following['id']}"
        )

    joined_boundaries = ("Obhutzeigte", "Wagner’sgehabt", "Zarathutra")
    if any(
        token in quote["german"]
        for quote in quotes
        for token in joined_boundaries
    ):
        fail("joined eKGWB emphasis boundary remains in German corpus")

    pp_stale_ocr_tokens = (
        "Achillesverse seiner Philosophie",
        "endlich entäuschte Geschlecht",
        "feria, oomo le va",
        "τον σεφον",
        "der l. Aufl.",
        "ed. 0relli",
        "Albrecht Paneritius",
        "is sure to he outdone",
        "the endeavour, by an affected",
        "tout recu",
        "Siehe DEuvres complètes",
        "ήρασθη το πνευμα των ίδιων άρχων",
        "Sehnsucht, ποθος,",
        "ελιλνωσκε",
        "von Taant, dem Aegypter",
        "άπλους ό της αληθειας λογος εφυ",
        "wo moglich aber sie noch",
        "προηγειται τοινυν παντων",
        "το βουλεσθαι. αί γαρ λογικαι δυναμεις",
        "πεφυκασι",
        "ipsa hominjs essentia",
        "Mit großem Rechte sagt Helvetius",
        "Quiconque so plaît",
        "animnal perdu",
        "Zwergfell",
        "von l bis 9",
        "Urtheils kraft",
        "moraliichen Schlechtigkeit",
        "belebten Kunstgriffe",
        "κατασκευαζειν",
        "ανασκευαζειν",
        "Αγωνιστικον υης περι υους",
        "αντιλογικη τεχνη",
        "Halle´schen",
        "Unredlichseiten",
        "Fakultäten waare",
        "Bei ietzt vorgenommener",
        "hingegen sioßen wir",
        "Zugesständnissen",
        "im einem, wie im andern Fall",
        "falsitaem rationis",
        "Die Instanz, ενστασις",
        "Gränze hinaus geführt",
        "eine Unwahre, meistens",
        "mutatio controversiae also",
        "Viertelstunde wieder holen",
        "auf´s Tapet",
        "nichts zn thun",
        "wenige Dinge solche Indignation hervorrufem",
        "eigenen Willens unterdrücken, also",
        "Im Gefühl hie von",
        "deutliche Erkenntnis der hier dargelegten",
        "Dies nämlich besagt das δος μοι που στω",
        "ergänzendem Philosophem",
        "Sujektive aus dem Objektiven",
        "klar uns verständlich",
        "einzigen Inhalt an jenen Fiktionen",
        "der Realimus",
        "Judenthum hingegen isi",
        "explodirt worden zn seyn",
        "annehme, voraussetzte, bejahe",
        "Wahrheit einstweilen ertheilt",
        "Philosophie and ist Fichtes Werk",
        "d. i. cerebrale Phantasmagorie",
        "analoge und Parallele über den Raum",
        "Zertheiluug",
        "Zusammenpressnng",
        "geradlienige Bewegung",
        "affectio renum",
        "κινηυη ο χρονος",
        "Bd. 8, Std. 3",
        "— 2. Aufl. 53)",
        "Objekt dargestellt werden soll",
        "Gestalt, Größe und Bewegung hat, ist es subjektiv bedingt",
        "Haupt-und Grundcharakter",
        "Göttingen 1801. Bd. II, 287 fg.",
        "werthwolle eigene Meditationen",
        "die wir dabei thätig find",
        "wobei nur, wenn es bloße Worte",
        "indem mir denselben, wenigstens zum Theil",
        "Leitung des Vorstandes",
        "Vorsorge; auf einige Jahre",
        "metaphpsische Bedürfnis;",
        "noch weniger-ihren etwanigen Einfluß",
        "Bd. 2., Kap. 14, S. 134,",
        "Frucht der Reise und Erfahrung",
        "Fortschreiten der Erkenntnis; und Einsicht",
        "Abnahme der Intensität der Geisteskräfte;",
        "γηρασκω δ αει πολλα διδασκομενος",
        "2. Aufl. 1854, S. IV.",
        "zum Philosophen befähigte",
        "S. 17., welches",
        "das Verhältnis der beharrenden Materie",
        "an der οψιμαθια",
        "Gedanken, welche wert waren, aufgeschrieben",
        "die Notwendigkeit einer Ursache zu jeder Veränderung",
        "müß´t so seyn",
        "verneinend Verhalten",
        "WahrheitJ",
        "Dass dem Bako von Verulam Nachgesprochene",
        "Πολλακι και κηπωρος ανηρ μαλα καιριον ἑιπε",
        "Subjetktives",
        "Persönlichkeit Entspringendes",
        "unschätz-barem",
        "Aussgangs politischer Angelegenheiten",
        "umfaßt, nützliche Kenntnisse heißen",
        "un-bedeutendsten Vorgänge",
        "auf das rein, Objektive",
        "das Stämpel unsrer Armsäligkeit",
        "3. Aufl. 433.) Demgemäß",
        "anzukommem gleicht",
        "institut. L. III, e. 5",
        "Vollkommenheit und seine Empfänglichkeit",
        "Abmessuug der Hierarchie",
        "Auffassnng unterscheiden",
        "als eine Parasit",
        "Seil-oder Solo-Tänzer",
        "Labrüpere",
        "Irr-und Wandelsterne",
        "Labrüyere sagt",
        "Ben Johnson Massinger",
        "mediocribus esse poetis",
        "Nicht weniger Newton:",
        "Newtonische Gravitationssystem",
        "Obgleich Newton das Erscheinen",
        "während er ausserhalb seines Vaterlandes",
        "Darstellung des Newtonianismus",
        "Newtons absurde Farbenlehre",
        "auf den Camoens, ihren einzigen Dichter",
        "versschlossenen Zauberschrank",
        "nicht Vielmehr die zwingende Auktorität",
        "aus der die Möglichkeit des festen",
        "zusammenkommenden Bandes aller Mittelmäßigen",
        "Unfähigkeit, Planheit und Stümperhaftigkeit",
        "die vermaladeite Parade",
        "in meinen Hauptwerke",
        "La modestie devroit êtra",
        "qua todo poeta",
        "das ehr-und gewissenlose Lobpreisen",
        "Schandtweg der Kamaraderie",
        "σοφον ειναι δει τον επιγνωσομενον τον σοφον",
        "Mahlmamn",
        "Vevielfältigung",
        "berühtmer Mann",
        "sprangen sie allezu",
        "verchworene litterarische",
        "seinen Zeit-und Altersgenossen",
        "vielleicht aus Kondescendenz— eine schlechte Sache",
        "beschließt er, S 44, mit:",
        "soche unwissende Patrone",
        "Quanität",
        "l) daß Keiner vor seinem 20. Jahre",
        "never to he read.Pope",
        "Vätern hast,Erwirb",
        "Auskunft ertheilten",
        "unusquisque mavult credere",
        "nachgeahmtem d. h. halb",
        "hetruxischen Vase",
        "beikeideten Mauer",
        "laudes laudaris ut absens",
        "κατ εξοχην",
        "nuscetur ridiculus mus",
        "πλεον ημισυ παντος",
        "ομοιος statt ομοιως",
        "Sujektives",
        "Moralistes francais l838",
        "ni le dégout est une marque",
        "σεμνοτης",
        "Gedächtsniß",
        "πολυ δε μεγιστον το μεταφορικον",
        "πολυ ριεχουσι",
        "Χειλεα μεν τ εδιην",
        "de11a Causa",
        "nicht andersist es mir",
        "die Werte großer Geister",
        "Ehr läßt es sich indirekt ausdrücken",
        "die füchtigen Gestalten dieser Welt",
        "qualle sit vel non sit",
        "deutliche uud bestimmte",
        "metaphpysischen",
        "Erkenntnis; des Dinges an sich",
        "Selbstbeweußtseyn",
        "Versständlichkeit eines Vorganges",
        "mit dem Pantheimus",
        "es doch ganz, anders gewohnt",
        "bloß potantia vorhanden seyn",
        "das Oxyen der Basis",
        "Wirkung znrückzuführen",
        "eigenschafts-und formlosen Materie",
        "Erkennntiß des Wesens der Dinge",
        "Kraftäußeruug",
        "Ellen langes, gespanntes Strick",
        "chromatolgische Theil",
        "Quanitativen",
        "Pouil1et",
        "Licht-und Wärme-Entwickelung",
        "Gemengeheile",
        "Dies ale Hypothese",
        "Careil 1854 her-ausgegeben",
        "principio vituli",
        "Wahrheit um nächsten",
        "imponderabilis,,",
        "schmilzt l lb Wasser",
        "Aenderung der Quanität",
        "z. B. das Strick",
        "offen-stehenden",
        "Hinein-und Herausfahren",
        "legelförmig",
        "elasitscher",
        "(ganz, hypothetischen, Aethers",
        "phénomênes",
        "fieng an zu radotiren",
        "sthwach",
        "znsammenstoßen",
        "Glimmer-und Gypsspath-Blättchen",
        "beim Ein-und Ausgange",
        "p. l56, 57. ed. Bip.",
        "Im, Jahr 1815",
        "Januar l853",
        "ungeschenen Ursache",
        "Ptolemäer-und Römer-Zeit",
        "Glühehitze",
        "Fourrier",
        "astronomisehe Gründe",
        "selhst die im luftleeren Raume",
        "Quanität Wärme",
        "systême du monde",
        "Cirlulation der Planeten",
        "gewesen sehn, welche jedem Planeten",
        "Gravitations-und Centrifugalgesetzen",
        "znsammenzog",
        "7° O’ 6”",
        "χαριν τθ βελτιονος",
        "Ampere geschildert",
        "Animalisacion",
        "Pflanzen-und Thierwelt",
        "Sphären zusammengesetzt sehn",
        "usichtbaren und unfühlbaren Stoff",
        "irrevelant beseitigt",
        "Biographia Brittannica",
        "pag. 704 note l",
        "which is aaid to have",
        "Mr. Conduit, as, as I have not",
        "Erst hinterher viel ihm die alte Hypothese ein",
        "welterklärenden Hppothese",
        "dem blossen Auge sichtbaren",
        "aus See-und nicht aus Flußwasser",
        "generatio univoca (εξ ομωνυμου",
        "die Gedurten allemal",
        "beigebrachten Phänomem",
        "mutatis mutandis dieses Gesetz",
        "versperrt wäre, dann auf die generatio aequivoca werfen",
        "generatio in utero heterogeno",
        "völlig ansgelöscht haben",
        "das Gebiet der Physik ungebürlich ausdehnt",
        "plumpester Judensuperfiktion",
        "am Lichte der Erkennntiß",
        "prostititiren und zum Spott",
        "zunehmen nnd dadurch",
        "Pflanzen-und Thiergeschlecht",
        "(und dies ist der eigentliche Begriff des Genus, und zerfallen manche",
        "first saw Buropean women",
        "durch die stärkere Be kleidung",
        "ihn nicht wieder in Besitz, nehmen",
        "fortgesetzten Hervorbringungj",
        "Hervorzu-bringenden",
        "wie der Magnetismuß",
        "vom Gehn durchdaus nicht ermüdet",
        "ανιη και πολυς υπνος",
        "(0d. XV. 394)",
        "Dieserhalb soll mann",
        "die rüstigen Affekt wie Freude",
        "mit dem Blutumlauß",
        "schöne Entdeckuug der Reflexbewegungen",
        "angehäuften, montentanen Ueberschuß",
        "die sensibelen Nerven",
        "Medulla ablongata",
        "im scharfem Zickzack",
        "geründeter Biegung",
        "nach Wagenbie, Physiol.",
        "das tentoicum cerebelli",
        "äußern Haut paralpsirt",
        "peu de médecin, peu de médecin.",
        "verschiedenen Thiergesta1ten",
        "nicht so besimmt angeben",
        "nur Einen Beleg zu dem Ge—sagten",
        "Ausführung dieser Betrachtungen der Sache",
        "herein,Und beweist euch",
        "sein Urphänomem nachdem",
        "die specifiche Verschiedenheit",
        "qualitus occulta",
        "homogenen Farbestrahlen",
        "Diese Auslegung der Sache laßt sich",
        "auf einer grauen) Flache",
        "physiologisch als Spektenm ihm",
        "in sehr verschiedenen Produktionen getheilt",
        "Blätter in Roch, beim ersten Frost",
        "unabweisbare Wiederlegung derselben",
        "hin und her, hinaus und herab gezogen",
        "das Sichentfernen der einzelnen farbigen Lichter",
        "Krown-und",
        "vom Flint-anders",
        "Konkav-und Konvexglas",
        "Thätigkeit der Netzhant",
        "in der Edinburgh’ review recensirt",
        "Nationaleigenthum πυξ και λαξ",
        "Sancta Simplicitas!",
        "à l’acadèmie des sciences",
        "geist-und verdienstlosen",
        "luftleere Glasröhre ausströmen",
        "in Folge welcher sie als dann",
        "im Jahr l849",
        "in ihrer Blbliothek",
        "den Leuten von Fachs",
        "sich hatten anfbinden lassen",
        "ihre Schuld verhundetfacht",
        "wollenwir uns gebärden",
        "das unverschämte Vorgehen, daß",
        "Daher laßt, unter dem Einfluß",
        "in ihrer mysthischen Weise",
        "lettres édifiantes et, curieuses",
        "Die, welche von Cicero temperantia",
        "von σωον εχειν το φρονειν",
        "Ταυτην την αρετην σωφροσυνην εκαλεσαν",
        "Schon Geulinx (Ethica",
        "London 1841, p. l97",
        "nicht Kardinal-sondern Theologal-Tugenden",
        "dem Chrißtlichen Sinne",
        "Tugend, virtus, αρετη,",
        "für αρετη erklärt wird",
        "σκυτοτομου αρετην λεγεσθαι",
        "seine Stammverwandschaft mit dem",
        "und ihn seyn ließe, wie wenig",
        "dieses Gottes και εξοχην",
        "ich bin ich! Ich, ich, ich will daseyn",
        "folgenden Kaiteln",
        "Aeußerungen - Fulgurationen",
        "Vernichtuug",
        "zu venichten",
        "steten Hemmung des Sterbens",
        "Plato’s beständiges Werden und nie Seyn",
        "Znvörderst",
        "entäuscht",
        "Menschen-und Thierwelt",
        "αει ωσαυτως ον",
        "ουτε γιγνομενον",
        "Jetzt και εξοχην",
        "desengano",
        "kein οντως ον ist",
        "so laugweilige",
        "Masken-An-und Aufzüge",
        "angenfällig der Venichtung",
        "schönem Liede Hoch auf dem alten Thurme",
        "nicht vergehn, Daß aber nur",
        "im Bewußtsein anderer Dinge",
        "im Gegensatz, der Dinge an sich",
        "beständige Ab-und Zufluß",
        "Anstrengung aller Körper-und Geisteskräfte",
        "ist das Negative nämlich",
        "Atmosphäre von ihr genommen",
        "gewissen Quatums Sorge",
        "anderes Dasseyn",
        "zum Verfolgen oder Fliehen",
        "Abwesende und zukünftige",
        "seines Glückes und Unglücks",
        "nach den Resourcen des Ortes",
        "η προσδοκιατων κακων",
        "durch das blosse Daseyn",
        "dem blossen kahlen Daseyn",
        "sagen: Du bist nicht mein Herr",
        "(Bd. l. §. 56)",
        "Ressonanzboden",
        "darin es heißt: es ist heute schlecht",
        "gar nicht ein mal nöthig",
        "Durchkreuzung, oder Änderung, deren Vibration",
        "nach Beliebe bestellen",
        "Philososphieprofessoren",
        "mit παντα καλα λιαν",
        "ein εργαστηριον",
        "Socî malorum",
        "Entschuldigung: und doch ist es dem Menschen natürlich",
        "erwidern: eben weil es schlecht ist",
        "Erinnerung dieser Art: Dies ist Sansara",
        "der Selbstmord sei unrecht",
        "histor. nat. lib. 28, c. l;",
        "dedit optimumin tantis vitae poenis",
        "Φευκτον δε τονβιον",
        "pravisvero",
        "πολιτευσεσθαιetc.",
        "tum iterum,cogente",
        "eine edele und heldenmüthige Handlung",
        "absolut venichtet zu werden",
        "there lies the, rub",
        "124 S. 80.",
        "Hauptwerk Bd. l. §. 69.",
        "gesagt hat παντα καλα λιαν",
        "gegenwärtigen διαστολη auch eine συστολη",
        "Oupnekhat Vol. l. p. 163",
        "mit dem επεκεινα der Neuplatoniker",
        "die Venichtung einer Substanz",
        "zum N. T von der Herrschaft",
        "bei ber Auffassung der Welt",
        "besagt: der Wille zum Leben hat sich aufs Neue bejaht",
        "Floskel wehe, wehe! der Lingam",
        "besagt: dem Willen ist auch wieder das Licht",
        "Lichtes der Erkenntnis, und zwar",
        "επι μονη παιδοποιια",
        "δευτερος πλους",
        "(Matth. l9, 24)",
        "καμιλον ρια τρυπηματος",
        "gefragt: Nun, Herr Franz",
        "3. Aufl. Bd. II. S. 405.)",
        "till grief und oldage",
        "painfull et so long",
        "Der Mensch, ο ανθρωπος",
        "Mensch, τις ανθρωπος",
        "sufficit irae, Iuv. Sat. XIII",
        "το οργιζεσθαι ηδυ",
        "sie sogleich zer-trat",
        "sie venichten möchte",
        "alle Kampf-und Kriegslust",
        "Stelle einer Erkärung vertritt",
        "Expansions-und Kontraktionskraft",
        "an seiner Quaal dich weiden",
        "gänzlich venichtet wäre",
        "watchmaker, showmaker",
        "Uhrmachet, Schuhmacher",
        "notre faiseurwiederzugeben",
        "jenem maker aus nichs",
        "with e refutation of his arguments",
        "the exellence of the moral system",
        "Pfründen-und Allongen-perücken-Träger",
        "Mahmud dem Gahznewiden",
        "von allem Bilder-und Götterwesen",
        "θεοις μεν καν ο μηδεν ων ομου",
        "Sept-1858",
        "Uebersetztungen heiliger Bücher",
        "Mythologie gereinigt sein wird",
        "das Ur-und Grundwollen",
        "De legib. X. p 106",
        "die unbedeutendesten herab",
        "Tangential-und der von seiner Sonne",
        "Shakespear’s Dramen",
        "moralische νουτεθησις",
        "durch die strenge Notwendigkeit",
        "gänzlichen Notwendigkeit, mit der",
        "le medesime cose, che bora",
        "Das Fatum, die ειμαρμενη",
        "nicht des Geringste thun sie",
        "Ueberhanpt wirkt das Beispiel",
        "quantum Potentiâ valet",
        "Eth. IV. pr. 37. sch. l",
        "de cive e. l. §. l4",
        "il ne sagit que de voler",
        "Moral-und Rechtslehre",
        "Ως κρειττον εστι δεσποτου",
        "Fabrik-vοrsteher",
        "dem Namen der Skaverei",
        "Millionen Negerskaven",
        "ως εν σοπον βουλευμα",
        "Περσαις νομος ην, οποτε βασιλευς",
        "sondern appercus",
        "Ueberlegenheιτ",
        "Kraft Verliere",
        "darstellen lassen, wie. z. B. Fluor",
        "Lenker und Negierer",
        "das ηγεμονικον",
        "Ουκ αλαθον πολυκοιρανιη",
        "à Leyde l665",
        "καλλισιον η μοναρχια",
        "das feiner Gläubiger",
        "σεισαχθεια",
        "Οισθα λαρ οιος θυμος",
        "nie erlöst verden",
        "zum Unrechte ge-braucht",
        "be-unruhigt",
        "Art von Geistern",
        "dessen so homogene",
        "Realitat innerhalb",
        "Venichtung darstellt",
        "Ein individuelles Bewußtsein, also",
        "Nerven-und Gefäßsystems",
        "geheimnisvollen Bau",
        "Voraussetzung daß",
        "ο λαμβανων και διδους",
        "falsch Und richtig",
        "Geheimnis der Palingenesie",
        "p. p. 386, 387 et. 395",
        "Isisbild zu Gais",
        "Kleine dialogische Schlußbelustigung Thrasymachos.",
        "altmodische kantische Kunstsprache",
        "Philalethes (leise für sich).",
        "Succession, großer Männer",
        "von allen Dem zurück",
        "Dein Wesen an sich Selbst",
        "von seiner Individualität ausgeschlossen",
        "φιλοσοφον πληθος αδυνατον ειναι",
        "Erimirten",
        "Sprichtwörtern",
        "Volksmethaphysik",
        "unbefangenen urtheilen",
        "d. h, in fast allen Fällen",
        "auto de fè",
        "(de incantat c. 7)",
        "Zurichtuug",
        "Pythagorrers",
        "τσς φυχας",
        "απειργομες φευδεσι",
        "Gemüthe führen Doch, guter Freund",
        "Gewalt-und Schandthaten",
        "mysthisch-allegorischer",
        "grossen Haufens",
        "Ader seitdem",
        "in jemen sie",
        "Bändigungs-und Besänftigungsmittel",
        "execellentes",
        "Zähmungs-und Abrichtungsmittel",
        "Trost-und Beruhigungsgründe",
        "Uederdies",
        "Länder-und Völkerkunde",
        "qu’on ee permet",
        "laisser an peuple",
        "expérer qu’une agonie",
        "(ep 5)",
        "Im ganzes Verlaufe",
        "Arisioteles",
        "Bändigungs-und Zähmungsmittel",
        "Akadenmieen",
        "Statisiker",
        "Feierlichleit",
        "Unterweisung der Priesterauktorität",
        "beigezähl.",
        "Mord-und Raubzug",
        "dich versichen",
        "A man convinced against his will",
        "Suceession",
        "Verleumdung des eignen Willens",
        "Die Absurditäten im Dogma sind eben das Stämpel",
        "systemisches Ganzes",
        "venichten könne",
        "quaecunque vouit",
        "decendus improvidus",
        "Shakva Muni",
        "12, 1O",
        "Sc. l.",
        "Göttingen studierte",
        "durchsaus das Selbe",
        "Psalm 99, l. In der Septuaginta",
        "der Mackabäer, Kap. l und 2",
        "ο ιροχος της γενεσεως",
        "Abel Nemüsat",
        "Foe Koue Ki",
        "l’embelême",
        "un embléme familier",
        "d’exestence",
        "qui ne connâit",
        "triomphé de toutes les détruisant",
        "Pradbod’h Chandrodaya",
        "destructions et reproductions",
        "von Aegytischen Priestern",
        "Beispielen klar, machen",
        "avec un essay sur l’origine",
        "rechereches sur l’histoire",
        "Bd. 1., — der zuerst",
        "Begreiflichkeit und Planheit",
        "ist Optimisimus",
        "hinauszuexegesiren",
        "hinausexegesirt",
        "nordischen Nüchternheit und Planheit",
        "oben angezogenen Sprichwort",
        "cruz està el diablo",
        "so geschmacklos und monstros",
        "die Ueberssetzungen europäischer Gelehrten",
        "Anquetil dü Perron",
        "Stellen in Colebrook’s Uebersetzungen",
        "Bibliotheca India No. 41",
        "hat Colebrook, in seiner Abhandlung",
        "diese ganze Philososphie verdorben",
        "Phantastische Beschäftigung haben will",
        "du Nirvana Indien l856",
        "Dasjenige odjektiv darzustellen",
        "specimen ingorantiae veterum",
        "το θερμον και φυχρον",
        "vielgepriesenen Hhymnus",
        "eingeweiht, besondere der Isis",
        "antikes Kostüm, trägt",
        "die Wohnungen, die Gefässe",
        "in den Studien zu Göthe’s Werken",
        "211 f. f.",
        "226 f. f.",
        "Schlaf und Tod (V. 746—765.)",
        "nach eigener Konjetkur",
        "Auslegen der Mythlogie",
        "αλλαπερι μεν των μυθικως",
        "σπουδηςσκοπειν",
        "die Zeit venichtet jede Zeugungskraft",
        "(Enn. IV, l. l. c. 14)",
        "Ζεθς εν πιθωτα",
        "Epitheton λιγυφωνοι welches",
        "waum sollten die Hesperiden",
        "Steine verschlingen und verdauen laßt",
        "Bd. l. §. 54",
        "in Finanz-oder Handelsgeschäften",
        "Maler dazustellen",
        "suceessiven Zustände",
        "ridete, puellae, ridete!.",
        "Raphael und Rembrand,",
        "Wachsfiguren keine ästhetischen Eindruck",
        "Schön ist, ohne Zweifel, verwandt",
        "In Korn-und Gemüse-Feldern",
        "ducontos versus, stans pode in uno",
        "lebhaftesten Licht-und Farben-Eindrücke",
        "gedrängte, geist-und gedankenvolle Poesie",
        "vox humana welche, musikalisch genommen",
        "Tenor-oder Baßstimme",
        "Baryton-oder Baß-Arie",
        "das allein Natur-und Kunstgemäße",
        "Teatro della Balle",
        "Harlekinsjackes der Potpourri",
        "kompletiren Ein Roman",
        "Ritter-oder Räuberroman",
        "latitantia cernuut",
        "a riveder lestelle",
        "Das ganze lnferno des Dante",
        "Ehr-und Gewissenlosigleit",
        "gedanken-und wahrheitsreichen Bücher",
        "zahl-und endlos sind",
        "Jedem drückt er sein Stämpel auf",
        "Ornamente, Gefässe, Möbeln",
        "Boisseree’sche jetzt in München",
        "ausszumerzen",
        "συλληφις",
        "γενομενονποιουμενον",
        "Gewordene istein Gemachtes",
        "Delrii disquisitionibus magicis, L. I, c. l,",
        "LuftLuft kommt",
        "bradype, 0edype, Andromaque",
        "ungestühmer und leidenschaftlicher",
        "extravagiren Das Genie hingegen",
    )
    pp_transcription_texts = [
        "\n".join(
            [
                quote["german"],
                *(
                    footnote["text"]
                    for footnote in quote["footnotes"]
                    if footnote.get("kind") == "source-edition"
                ),
            ]
        )
        for quote in quotes
        if quote["work"] == "pp"
    ]
    if any(
        token in transcription_text
        for transcription_text in pp_transcription_texts
        for token in pp_stale_ocr_tokens
    ):
        fail("known Parerga transcription OCR error remains in German corpus")

    if any(
        quote["work"] == "pp"
        and (
            quote["german"].startswith("Boas, Schiller und Göthe im Xenienkampf")
            or quote["german"].startswith("II, p. 226 fg.; 3. Aufl.")
            or quote["german"].startswith("Mos. 17, 8.)")
            or quote["german"].startswith("Brunus (ed. Wagner")
            or quote["german"].startswith("Dei, L. XI, c. 23.);")
            or quote["german"].startswith("L. II. c. 6, §. 7 et 8.).")
            or quote["german"].startswith("Tom. 142) das Leben")
            or quote["german"].startswith("(Nachlaß, Bd. 17. p. 297.)")
        )
        for quote in quotes
    ):
        fail("Parerga bibliographic citation split into an orphan quote")

    pp_style_citations = [
        quote
        for quote in quotes
        if quote["work"] == "pp"
        and quote["part"] == "II-23"
        and quote["section"] == "291"
    ]
    if not any(
        "sqq. Tom. 142) das Leben des Benvenuto Cellini" in quote["german"]
        for quote in pp_style_citations
    ):
        fail("Parerga § 291 Italian bibliography split inside its volume citation")
    if not any(
        "Der Edle strebt nach Ordnung und Gesetz. (Nachlaß, Bd. 17. p. 297.)"
        in quote["german"]
        for quote in pp_style_citations
    ):
        fail("Parerga § 291 Goethe source detached from its quotation")

    pp_language_appendix = [
        quote
        for quote in quotes
        if quote["work"] == "pp"
        and quote["part"] == "II-23"
        and quote["section"] == "Anhang-verwandter-Stellen"
    ]
    if any(
        quote["german"].startswith("und jenen Elenden,")
        or quote["german"].endswith("Welch’ ein Abstand ist doch zwischen Denen, —")
        for quote in pp_language_appendix
    ) or not any(
        quote["german"].startswith("Welch’ ein Abstand ist doch zwischen Denen,")
        and "und jenen Elenden" in quote["german"]
        for quote in pp_language_appendix
    ):
        fail("Parerga language-grammar comparison split before its second term")

    pp_reading_advice = [
        quote
        for quote in quotes
        if quote["work"] == "pp"
        and quote["part"] == "II-24"
        and quote["section"] == "303"
    ]
    if any(
        quote["german"].endswith("Stoff zur Konversation daran zu haben:")
        or quote["german"].startswith("zu diesem Zweck dienen denn")
        for quote in pp_reading_advice
    ) or not any(
        "zu diesem Zweck dienen denn schlechte Romane"
        in quote["german"]
        and "Eugen Sue u. s. w." in quote["german"]
        for quote in pp_reading_advice
    ):
        fail("Parerga § 303 conversational-reading example split at its colon")

    if any(
        quote["work"] == "pp"
        and (
            quote["german"].endswith("urkräftigen Gedanken verscheuchen, um ein")
            or quote["german"].startswith("Buch zur Hand zu nehmen, ist Sünde")
        )
        for quote in quotes
    ):
        fail("Parerga § 266 sentence split at a false EPUB paragraph boundary")

    pp_language_etymology_appendix = [
        quote
        for quote in quotes
        if quote["work"] == "pp"
        and quote["part"] == "II-25"
        and quote["section"] == "Anhang-verwandter-Stellen"
    ]
    if any(
        quote["german"].startswith("um so mehr,")
        or quote["german"].startswith("Keltisch, und bedeutete")
        or quote["german"].endswith("d. i.")
        for quote in pp_language_etymology_appendix
    ):
        fail("Parerga language appendix contains an orphaned continuation")
    if not any(
        quote["german"].startswith("Ich wollte, daß die illustres confrères")
        and "um so mehr, als man" in quote["german"]
        and quote["german"].endswith("enträthseln.")
        for quote in pp_language_etymology_appendix
    ):
        fail("Parerga French-language appeal split after its semicolon")
    if not any(
        quote["german"].startswith("— Wälsch ist höchst wahrscheinlich")
        and "d. i. Keltisch" in quote["german"]
        for quote in pp_language_etymology_appendix
    ):
        fail("Parerga Wälsch etymology split inside d. i. Keltisch")

    pp_278_opening = [
        quote
        for quote in quotes
        if quote["work"] == "pp"
        and quote["part"] == "II-22"
        and quote["section"] == "278"
        and quote["paragraph"] == 0
    ]
    if (
        len(pp_278_opening) != 1
        or not pp_278_opening[0]["german"].startswith("Wenn man wohl erwägt")
        or not pp_278_opening[0]["german"].endswith("anzunehmen pflegt.")
    ):
        fail("Parerga § 278 conditional sentence split into dependent fragments")

    if any(
        quote["work"] == "pp"
        and quote["german"].endswith("Und Dies hier ist die Bevölkerung der Sansara.")
        for quote in quotes
    ):
        fail("Parerga Buddhist reminder split inside quotation marks")

    pp_apuleius = [
        quote
        for quote in quotes
        if quote["work"] == "pp"
        and quote["part"] == "II-15"
        and quote["section"] == "175"
        and "Apulejus de Deo Socratis" in quote["german"]
    ]
    if (
        len(pp_apuleius) != 1
        or pp_apuleius[0]["german"].startswith("(Apulejus de Deo Socratis")
        or "Laren und Penaten" not in pp_apuleius[0]["german"]
    ):
        fail("Parerga § 175 Apuleius citation detached from its printed sentence")

    pp_century = [
        quote
        for quote in quotes
        if quote["work"] == "pp"
        and quote["part"] == "II-15"
        and quote["section"] == "175"
        and "des 16. und 17. Jahrhunderts in die Hand nehme" in quote["german"]
    ]
    if (
        len(pp_century) != 1
        or any(
            quote["work"] == "pp"
            and quote["part"] == "II-15"
            and quote["section"] == "175"
            and quote["german"].startswith("Jahrhunderts in die Hand nehme")
            for quote in quotes
        )
    ):
        fail("Parerga § 175 century phrase split at a print page turn")

    pp_demopheles_interruption = [
        quote
        for quote in quotes
        if quote["work"] == "pp"
        and quote["part"] == "II-15"
        and quote["section"] == "175"
        and "Da findest du sie aber nicht!" in quote["german"]
    ]
    if (
        len(pp_demopheles_interruption) != 1
        or not pp_demopheles_interruption[0]["german"].startswith("Demopheles.")
        or "Philalethes." in pp_demopheles_interruption[0]["german"]
    ):
        fail("Parerga § 175 speaker change flattened into one quote")
    if any(
        re.search(
            r"(?:Philalethes|Demopheles)[.]",
            re.sub(r"^(?:Philalethes|Demopheles)[.]\s*", "", quote["german"]),
        )
        for quote in quotes
        if quote["work"] == "pp"
        and quote["part"] == "II-15"
        and quote["section"] == "175"
    ):
        fail("Parerga § 175 quote contains more than one dialogue turn")

    pp_hamlet = [
        quote
        for quote in quotes
        if quote["work"] == "pp"
        and quote["part"] == "II-14"
        and quote["section"] == "166"
    ]
    if (
        len(pp_hamlet) != 3
        or "for thou hast been" not in pp_hamlet[0]["german"]
        or "(Denn du bist" not in pp_hamlet[0]["german"]
    ):
        fail("Parerga Hamlet quotation is not a coherent § 166 unit")

    pp_affirmation_appendix = [
        quote
        for quote in quotes
        if quote["work"] == "pp"
        and quote["part"] == "II-14"
        and quote["section"] == "Anhang-verwandter-Stellen"
    ]
    if (
        not pp_affirmation_appendix
        or "Then old age and experience" not in pp_affirmation_appendix[0]["german"]
        or any(
            quote["german"].startswith("Then old age and experience")
            for quote in pp_affirmation_appendix
        )
    ):
        fail("Parerga chapter XIV appendix verse is detached from its introduction")

    pp_text = "\n".join(quote["german"] for quote in quotes if quote["work"] == "pp")
    pp_required_list_fragments = (
        "Hauptwerk, Bd. 2. Kap. 44. S. 550",
        "Flourens, Buffon. Histoire de ses travaux",
        "Metaphysik der Natur, Metaphysik des Schönen, Metaphysik der Sitten.",
        "Die Modi sind: ad rem und ad hominem",
        "Merkur: 0 / 4; Venus: 3 / 7; Erde: 6 / 10; Mars: 12 / 16; Planetoiden: 24 / 28",
        "Die zwei Wege nun ferner sind der direkte, und der indirekte.",
        "Auf dem indirekten Wege widerlegend",
        "Die Apagoge bringen wir dadurch zu Wege",
        "Das Subjekt des Erkennens ist nichts Selbstständiges",
        "Der Wille in uns ist allerdings Ding an sich",
        "Selbstmord ist eine feige Handlung.",
        "Wer Andern mißtraut ist selbst unredlich.",
        "Verdienst und Genie sind aufrichtig bescheiden.",
        "Die Wahnsinnigen sind überaus unglücklich.",
        "Die Philosophie läßt sich nicht lernen, sondern nur das Philosophiren.",
        "Es ist leichter eine gute Tragödie, als eine gute Komödie zu schreiben.",
        "Das dem Bako von Verulam Nachgesprochene",
        "Knowledge is power. Den Teufel auch!",
        "Του δε οντως οντος και καθ’ αυτο υφεστηκοτος αυτου",
        "daß Der, zu dem geredet wird, den Subjektbegriff",
        "weshalb denn auch Herr Prof. Rosas in Wien",
    )
    missing_pp_list_fragments = [
        fragment for fragment in pp_required_list_fragments if fragment not in pp_text
    ]
    if missing_pp_list_fragments:
        fail(f"Parerga XHTML list content missing: {missing_pp_list_fragments[:3]}")

    pp_death_appendix = [
        quote
        for quote in quotes
        if quote["work"] == "pp"
        and quote["part"] == "II-10"
        and quote["section"] == "Anhang-verwandter-Stellen"
    ]
    if (
        len(pp_death_appendix) != 6
        or {quote["paragraphCount"] for quote in pp_death_appendix} != {1}
        or [quote["sentence"] for quote in pp_death_appendix] != list(range(6))
    ):
        fail("Parerga chapter X printed appendix paragraph was split incorrectly")
    if any(
        quote["german"].count("„") != quote["german"].count("“")
        for quote in pp_death_appendix
    ):
        fail("Parerga chapter X appendix contains a quote cut inside direct speech")

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
    eh_za_quotes = [
        quote for quote in quotes
        if quote["work"] == "eh" and quote["part"] == "Za"
    ]
    for current, following in zip(eh_za_quotes, eh_za_quotes[1:]):
        same_source_paragraph = (
            current["section"] == following["section"]
            and current["paragraph"] == following["paragraph"]
            and following["sentence"] == current["sentence"] + 1
        )
        if (
            same_source_paragraph
            and current["german"].rstrip().endswith(",")
            and following["german"][:1].islower()
        ):
            fail(
                "EH-Za long sentence was split at a weak comma boundary: "
                f"{current['id']} -> {following['id']}"
            )
    if cache_ids != translated_ids:
        fail(
            "translation cache ID mismatch: "
            f"missing={len(translated_ids - cache_ids)}, orphaned={len(cache_ids - translated_ids)}"
        )
    widget_quotes = json.loads((DATA / "widget.json").read_text(encoding="utf-8"))
    widget_ids = {quote["id"] for quote in widget_quotes}
    if widget_ids != ids or len(widget_quotes) != len(ids):
        fail("widget data must contain every quote exactly once")
    if manifest.get("widgetQuoteCount") != len(widget_quotes):
        fail("manifest widgetQuoteCount does not match widget.json")
    shard_catalog = manifest.get("widgetShards", {})
    if (
        shard_catalog.get("schemaVersion") != 1
        or shard_catalog.get("basePath") != "data/widget-shards"
        or shard_catalog.get("workOrder") != list(WORKS)
        or shard_catalog.get("totalCount") != len(widget_quotes)
    ):
        fail("invalid widget shard catalog")
    shard_size = shard_catalog.get("shardSize")
    if not isinstance(shard_size, int) or shard_size < 1:
        fail("invalid widget shard size")
    reconstructed_widget_quotes = []
    expected_offset = 0
    for work in WORKS:
        descriptor = shard_catalog.get("works", {}).get(work, {})
        expected_work_quotes = [quote for quote in widget_quotes if quote["work"] == work]
        expected_shard_count = (len(expected_work_quotes) + shard_size - 1) // shard_size
        if descriptor != {
            "offset": expected_offset,
            "count": len(expected_work_quotes),
            "shardCount": expected_shard_count,
        }:
            fail(f"invalid widget shard descriptor for {work}")
        for shard_index in range(expected_shard_count):
            shard_path = DATA / "widget-shards" / f"{work}-{shard_index:03d}.json"
            if not shard_path.is_file():
                fail(f"missing widget shard {shard_path.relative_to(ROOT)}")
            shard = json.loads(shard_path.read_text(encoding="utf-8"))
            expected_shard = expected_work_quotes[
                shard_index * shard_size : (shard_index + 1) * shard_size
            ]
            if shard != expected_shard:
                fail(f"widget shard mismatch in {shard_path.relative_to(ROOT)}")
            reconstructed_widget_quotes.extend(shard)
        expected_offset += len(expected_work_quotes)
    if reconstructed_widget_quotes != widget_quotes:
        fail("widget shards do not reconstruct widget.json exactly")
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
