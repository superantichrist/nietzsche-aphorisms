#!/usr/bin/env python3
"""Export translation differences from a Git revision as small JSON overlays."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "translations" / "ko.json"


def translation_map(payload: dict) -> dict[str, dict]:
    translations = payload.get("translations", payload)
    if not isinstance(translations, dict):
        raise ValueError("translation payload must contain an object map")
    return translations


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-ref", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--chunk-size", type=int, default=40)
    args = parser.parse_args()

    if args.chunk_size < 1:
        raise SystemExit("--chunk-size must be positive")
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(f"output directory is not empty: {output_dir}")

    baseline_text = subprocess.check_output(
        ["git", "show", f"{args.baseline_ref}:translations/ko.json"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    )
    baseline = translation_map(json.loads(baseline_text))
    current = translation_map(json.loads(CURRENT.read_text(encoding="utf-8")))
    changed = [(quote_id, entry) for quote_id, entry in current.items() if baseline.get(quote_id) != entry]
    removed = sorted(set(baseline) - set(current))
    if removed:
        raise SystemExit(f"cannot encode removals as additive overlays: {len(removed)} IDs")

    output_dir.mkdir(parents=True, exist_ok=True)
    for index in range(0, len(changed), args.chunk_size):
        chunk = dict(changed[index : index + args.chunk_size])
        path = output_dir / f"ko-{index // args.chunk_size + 1:03d}.json"
        path.write_text(
            json.dumps(
                {"schemaVersion": 1, "translations": chunk},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    print(f"Exported {len(changed):,} changed translations to {(len(changed) - 1) // args.chunk_size + 1:,} files.")


if __name__ == "__main__":
    main()
