#!/usr/bin/env python3
"""Copy generated corpus and Scriptable source into Vite's output."""

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def copy_tree_merge(source: Path, target: Path) -> None:
    """Merge a generated asset tree without requiring Python 3.8 copytree options."""
    target.mkdir(parents=True, exist_ok=True)
    for item in source.rglob("*"):
        destination = target / item.relative_to(source)
        if item.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination)


def main() -> None:
    for source_dir_name in ("data", "scriptable"):
        source_dir = ROOT / source_dir_name
        target_dir = DIST / source_dir_name
        target_dir.mkdir(parents=True, exist_ok=True)
        for source in source_dir.glob("*"):
            if source.is_file():
                shutil.copy2(source, target_dir / source.name)
            elif source.is_dir():
                copy_tree_merge(source, target_dir / source.name)
    for filename in ("manifest.webmanifest", "robots.txt", ".nojekyll"):
        shutil.copy2(ROOT / filename, DIST / filename)
    print("Copied data and Scriptable assets into dist/.")


if __name__ == "__main__":
    main()
