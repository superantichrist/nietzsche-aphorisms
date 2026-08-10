#!/usr/bin/env python3
"""Export pending translation batches and import reviewed Korean text."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUOTES = ROOT / "data" / "quotes.json"
CACHE = ROOT / "translations" / "ko.json"


def read_quotes() -> list[dict]:
    if not QUOTES.exists():
        raise SystemExit("Run `python scripts/build_data.py` first.")
    return json.loads(QUOTES.read_text(encoding="utf-8"))


def read_cache() -> dict:
    if not CACHE.exists():
        return {"schemaVersion": 1, "translations": {}}
    payload = json.loads(CACHE.read_text(encoding="utf-8"))
    payload.setdefault("schemaVersion", 1)
    payload.setdefault("translations", {})
    return payload


def export_batch(args: argparse.Namespace) -> None:
    cache = read_cache()["translations"]
    pending = []
    for quote in read_quotes():
        if args.work and quote["work"] != args.work:
            continue
        if cache.get(quote["id"], {}).get("korean"):
            continue
        pending.append(
            {
                "id": quote["id"],
                "work": quote["work"],
                "part": quote["part"],
                "section": quote["section"],
                "german": quote["german"],
                "korean": "",
                "status": "draft",
            }
        )
        if len(pending) >= args.limit:
            break

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in pending), encoding="utf-8")
    print(f"Exported {len(pending)} pending records to {output}.")


def import_batch(args: argparse.Namespace) -> None:
    quotes = {quote["id"]: quote for quote in read_quotes()}
    payload = read_cache()
    translations = payload["translations"]
    imported = 0
    for line_number, line in enumerate(Path(args.input).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        quote_id = item.get("id")
        korean = str(item.get("korean", "")).strip()
        if quote_id not in quotes:
            raise SystemExit(f"Line {line_number}: unknown quote ID {quote_id!r}")
        if item.get("german") and item["german"] != quotes[quote_id]["german"]:
            raise SystemExit(f"Line {line_number}: German source mismatch for {quote_id}")
        if not korean:
            continue
        translations[quote_id] = {
            "korean": korean,
            "status": item.get("status", "draft"),
            "notes": item.get("notes", ""),
        }
        imported += 1

    payload["translations"] = dict(sorted(translations.items()))
    CACHE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Imported {imported} translations into {CACHE}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="write pending quote records as NDJSON")
    export_parser.add_argument("--work", choices=("jgb", "gm", "ac", "gd", "fw"))
    export_parser.add_argument("--limit", type=int, default=100)
    export_parser.add_argument("--output", default="translations/batches/pending.ndjson")
    export_parser.set_defaults(func=export_batch)

    import_parser = subparsers.add_parser("import", help="merge translated NDJSON into the stable cache")
    import_parser.add_argument("input")
    import_parser.set_defaults(func=import_batch)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
