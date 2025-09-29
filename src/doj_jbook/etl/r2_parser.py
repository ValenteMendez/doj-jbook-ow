from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None  # type: ignore


# Common section markers we expect in Exhibit R-2 pages
R2_TITLE_MARKERS = [
    "Exhibit R-2",
    "Exhibit R-2A",
    "R-2 Budget Item Justification",
    "R-2A",
]

SECTION_PATTERNS = {
    "mission": r"A\.\s*Mission Description and Budget Item Justification\b",
    "accomplishments": r"C\.\s*Accomplishments/Planned Programs\b",
    "acquisition": r"D\.\s*Acquisition Strategy\b",
}


def _normalize_text(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def _extract_text_blocks(page) -> str:
    # Use text page extraction; PyMuPDF preserves layout reasonably well
    return page.get_text("text")


def find_r2_pages_for_pe(pdf_path: str, pe_number: str) -> List[int]:
    """
    Heuristically find page indices that correspond to R-2 pages for the given PE number.
    Returns zero-based page indices.
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF (pymupdf) not installed. Please install requirements.")

    pe_pattern = re.compile(rf"\b(?:PE\s*)?{re.escape(pe_number)}\b")
    pages: List[int] = []

    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        txt = _extract_text_blocks(page)
        if any(m in txt for m in R2_TITLE_MARKERS) and re.search(pe_pattern, txt):
            pages.append(i)
    return pages


def _extract_section(text: str, start_regex: str, end_regexes: List[str]) -> Optional[str]:
    start = re.search(start_regex, text, re.IGNORECASE)
    if not start:
        return None
    start_idx = start.end()

    # Find nearest next section header as an end marker
    end_matches = [m for r in end_regexes for m in re.finditer(r, text[start_idx:], re.IGNORECASE)]
    if not end_matches:
        return _normalize_text(text[start_idx:])
    first_end = min(end_matches, key=lambda m: m.start())
    end_idx = start_idx + first_end.start()
    return _normalize_text(text[start_idx:end_idx])


def _detect_new_start_flag(text: str) -> Optional[bool]:
    # Look for New Start mentions in header blocks
    # Common header might include: "Is this a New Start? Yes/No"
    m = re.search(r"New\s*Start\s*[:\-]?\s*(Yes|No)\b", text, re.IGNORECASE)
    if m:
        return m.group(1).lower() == "yes"
    return None


def extract_r2_sections_for_pe(pdf_path: str, pe_number: str) -> Dict[str, Optional[str]]:
    """
    Extract key R-2 sections for a given PE across its R-2 pages.
    Returns a dict with: mission, accomplishments, acquisition, is_new_start (as stringified bool or None).
    """
    page_ids = find_r2_pages_for_pe(pdf_path, pe_number)
    if fitz is None:
        raise RuntimeError("PyMuPDF (pymupdf) not installed. Please install requirements.")
    doc = fitz.open(pdf_path)

    collected_text = []
    for pid in page_ids:
        page = doc[pid]
        collected_text.append(_extract_text_blocks(page))
    text = "\n".join(collected_text)

    # Prepare section boundaries
    mission = _extract_section(
        text,
        SECTION_PATTERNS["mission"],
        [SECTION_PATTERNS["accomplishments"], SECTION_PATTERNS["acquisition"], r"^\s*[A-Z]\.\s"],
    )
    accomplishments = _extract_section(
        text,
        SECTION_PATTERNS["accomplishments"],
        [SECTION_PATTERNS["acquisition"], r"^\s*[A-Z]\.\s"],
    )
    acquisition = _extract_section(
        text,
        SECTION_PATTERNS["acquisition"],
        [r"^\s*[A-Z]\.\s"],
    )

    is_new_start = _detect_new_start_flag(text)

    return {
        "mission": mission,
        "accomplishments": accomplishments,
        "acquisition": acquisition,
        "is_new_start": None if is_new_start is None else str(bool(is_new_start)),
    }
