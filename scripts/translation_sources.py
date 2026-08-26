#!/usr/bin/env python3
"""Load the canonical Korean cache plus optional additive overrides."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_TRANSLATIONS = ROOT / "translations" / "ko.json"
CORPUS_DIR = ROOT / "translations" / "corpora"
OVERRIDE_DIR = ROOT / "translations" / "overrides"


def _read_translation_map(path: Path) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    translations = payload.get("translations", payload)
    if not isinstance(translations, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object map")
    return translations


def load_translations() -> dict[str, dict]:
    """Return the merged translation map, with sorted override files winning."""
    translations = (
        dict(_read_translation_map(BASE_TRANSLATIONS))
        if BASE_TRANSLATIONS.exists()
        else {}
    )
    if CORPUS_DIR.is_dir():
        for path in sorted(CORPUS_DIR.glob("*.json")):
            translations.update(_read_translation_map(path))
    if OVERRIDE_DIR.is_dir():
        for path in sorted(OVERRIDE_DIR.glob("*.json")):
            translations.update(_read_translation_map(path))
    return translations
