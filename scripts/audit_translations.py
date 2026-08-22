#!/usr/bin/env python3
"""Audit translation completeness and keep public footnotes philological."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS = ROOT / "translations" / "ko.json"

PLACEHOLDER_RE = re.compile(
    r"TODO|미번역|번역 준비|translation pending|machine translation|DeepL|Google Translate",
    re.I,
)

# Public notes may identify a word, source, person, historical referent, or the
# register of Nietzsche's language.  They must not tell the reader to replace
# the source's claim with a modern moral, political, or clinical verdict.
EDITORIAL_FOOTNOTE_RE = re.compile(
    r"성차별|인종차별|여성혐오|장애차별|연령차별|동성애\s*혐오|편견|"
    r"현대의|오늘날|"
    r"현대\s+(?:의학|역사학|유전학|윤리|과학|사회과학|인류학|정신의학|진화생물학|"
    r"성별\s*연구|젠더\s*연구)|현대적\s+(?:판단|정책|표현|기준)|"
    r"윤리적\s*(?:사실|위험|권고)|사실\s*(?:판단|진술|서술)|"
    r"객관적|타당한\s*(?:설명|심리)|"
    r"받아들일\s*(?:필요|수)\s*없|받아들여서는\s*안|"
    r"정당화|승인한다는\s*뜻|편집자의\s*동의|구분해\s*읽|비판적으로\s*읽|"
    r"평등한\s*혼인|보편적\s*심리|권고하는\s*문장|"
    r"역사적\s*단순화|과도한\s*단순화|"
    r"의학적[^.]{0,80}아니|경험적\s*사실|사실적으로\s*평가|"
    r"중립적[^.]{0,80}아니|근거(?:가|는)?\s*(?:없|않)|"
    r"자해\s*위험|위기지원|응급",
    re.I,
)


def load_cache() -> dict:
    return json.loads(TRANSLATIONS.read_text(encoding="utf-8"))


def editorial_footnotes(translations: dict) -> list[tuple[str, int, dict]]:
    findings = []
    for quote_id, entry in translations.items():
        for index, footnote in enumerate(entry.get("footnotes", [])):
            searchable = f"{footnote.get('label', '')} {footnote.get('text', '')}"
            if EDITORIAL_FOOTNOTE_RE.search(searchable):
                findings.append((quote_id, index, footnote))
    return findings


def basic_errors(translations: dict) -> list[str]:
    errors = []
    for quote_id, entry in translations.items():
        korean = entry.get("korean", "")
        if not isinstance(korean, str) or not korean.strip():
            errors.append(f"{quote_id}: blank Korean")
        elif not re.search(r"[가-힣]", korean):
            errors.append(f"{quote_id}: no Hangul")
        elif PLACEHOLDER_RE.search(korean):
            errors.append(f"{quote_id}: placeholder or machine-translation marker")
        if entry.get("status") not in {"draft", "reviewed"}:
            errors.append(f"{quote_id}: invalid status {entry.get('status')!r}")
        for index, footnote in enumerate(entry.get("footnotes", [])):
            if not footnote.get("label", "").strip() or not footnote.get("text", "").strip():
                errors.append(f"{quote_id}: malformed footnote {index}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strip-editorial-footnotes",
        action="store_true",
        help="remove public footnotes that impose modern editorial verdicts",
    )
    parser.add_argument("--list", action="store_true", help="print every editorial footnote")
    args = parser.parse_args()

    payload = load_cache()
    translations = payload.get("translations", {})
    errors = basic_errors(translations)
    findings = editorial_footnotes(translations)

    if args.list:
        for quote_id, index, footnote in findings:
            print(f"{quote_id} [{index}] {footnote['label']}: {footnote['text']}")

    if args.strip_editorial_footnotes and findings:
        remove_by_id: dict[str, set[int]] = {}
        for quote_id, index, _ in findings:
            remove_by_id.setdefault(quote_id, set()).add(index)
        for quote_id, indexes in remove_by_id.items():
            footnotes = translations[quote_id].get("footnotes", [])
            translations[quote_id]["footnotes"] = [
                footnote for index, footnote in enumerate(footnotes) if index not in indexes
            ]
        TRANSLATIONS.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Removed {len(findings):,} editorial footnotes from {len(remove_by_id):,} quotes.")
        findings = []

    if errors:
        raise SystemExit("Translation audit failed:\n" + "\n".join(errors[:30]))
    if findings:
        raise SystemExit(
            f"Translation audit failed: {len(findings):,} editorial footnotes remain "
            "(run with --list to inspect)."
        )
    print(f"Audited {len(translations):,} translations; no placeholders or editorial footnotes.")


if __name__ == "__main__":
    main()
