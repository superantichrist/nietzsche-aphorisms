#!/usr/bin/env python3
"""Download and verify the pinned Perseus Seneca source snapshots."""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw" / "seneca"
PERSEUS_COMMIT = "422896dde7f07509f151d18bb5fe351b77458748"
BASE_URL = (
    "https://raw.githubusercontent.com/PerseusDL/canonical-latinLit/"
    f"{PERSEUS_COMMIT}/"
)

SOURCES = (
    (
        "dbv-perseus.xml",
        "data/stoa0255/stoa004/stoa0255.stoa004.perseus-lat2.xml",
        "3a835ce9154a08804a7fcb74562860f54bbd389d213c26171cc98afc8e357c34",
    ),
    (
        "em-perseus.xml",
        "data/phi1017/phi015/phi1017.phi015.perseus-lat2.xml",
        "79f18a0e9796cc0de140792b2dd5f879cfb37405ece40e98b7443420e1d721ad",
    ),
    (
        "dta-perseus.xml",
        "data/stoa0255/stoa013/stoa0255.stoa013.perseus-lat2.xml",
        "1267f58cb19b5e52c318459842cb7dad231fff35b21157140d482e1a6d836b4a",
    ),
    (
        "dvb-perseus.xml",
        "data/stoa0255/stoa014/stoa0255.stoa014.perseus-lat2.xml",
        "7c66fe578afd01a79f8e3ed7a4730ef43069026232a07459c7494f965a567a03",
    ),
    (
        "di-perseus.xml",
        "data/stoa0255/stoa010/stoa0255.stoa010.perseus-lat2.xml",
        "094c5c2f3d2cfc2f2691ab084601ea677275608fe21e9d4c1c2291d45e6f58e1",
    ),
    (
        "dc-perseus.xml",
        "data/phi1017/phi014/phi1017.phi014.perseus-lat2.xml",
        "50c22cc21326ee80b030a28ecf0ef1ab57f30167af85a47533594509b07339a2",
    ),
    (
        "dp-perseus.xml",
        "data/stoa0255/stoa012/stoa0255.stoa012.perseus-lat2.xml",
        "c194099f17ceadec6ede23aae2fe6c72850af74013411be1afc159b291373e07",
    ),
)


def source_hash(content: bytes) -> str:
    """Hash normalized newlines so Windows checkouts remain reproducible."""
    return hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest()


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for filename, source_path, expected in SOURCES:
        destination = RAW / filename
        request = urllib.request.Request(
            BASE_URL + source_path,
            headers={"User-Agent": "today-sentence-source-fetch/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                content = response.read()
        except urllib.error.URLError:
            if (
                not destination.exists()
                or source_hash(destination.read_bytes()) != expected
            ):
                raise
            print(f"Network unavailable; retained verified {filename}: {expected}")
            continue
        actual = source_hash(content)
        if actual != expected:
            raise SystemExit(
                f"Hash mismatch for {filename}: expected {expected}, got {actual}"
            )
        destination.write_bytes(content)
        print(f"Verified {filename}: {actual}")


if __name__ == "__main__":
    main()
