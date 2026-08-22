#!/usr/bin/env python3
"""Copy generated corpus and Scriptable source into Vite's output."""

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def main() -> None:
    for source_dir_name in ("data", "scriptable"):
        source_dir = ROOT / source_dir_name
        target_dir = DIST / source_dir_name
        target_dir.mkdir(parents=True, exist_ok=True)
        for source in source_dir.glob("*"):
            if source.is_file():
                shutil.copy2(source, target_dir / source.name)
            elif source.is_dir():
                shutil.copytree(source, target_dir / source.name, dirs_exist_ok=True)
    for filename in ("manifest.webmanifest", "robots.txt", ".nojekyll"):
        shutil.copy2(ROOT / filename, DIST / filename)
    print("Copied data and Scriptable assets into dist/.")


if __name__ == "__main__":
    main()
