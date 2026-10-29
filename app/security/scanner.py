"""Deterministic prompt-injection scanner for a PDF's text layer."""
from pathlib import Path

import re

import pymupdf

PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"disregard (all )?(previous|prior|above)",
    r"skip (all )?validation",
    r"approved by (the )?(ceo|cfo|manager|director)",
    r"pay immediately",
    r"mark (this invoice )?as (approved|paid)",
    r"set (the )?risk",
    r"system prompt",
]
PHRASES = re.compile("|".join(PATTERNS), re.IGNORECASE)
WHITE = 0xFFFFFF
MIN_FONT_SIZE = 4.0


def scan_pdf(path: Path) -> list[str]:
    """Return flags such as 'injection_phrase' or 'hidden_text'. Empty list means nothing found.
    Limit: scanned (image-only) PDFs have no text layer, so this cannot see injected text in them."""
    findings = set()
    doc = pymupdf.open(str(path))
    for page in doc:
        if PHRASES.search(page.get_text()):
            findings.add("injection_phrase")
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    if not span["text"].strip():
                        continue
                    if span["color"] == WHITE or span["size"] < MIN_FONT_SIZE:
                        findings.add("hidden_text")
    return sorted(findings)