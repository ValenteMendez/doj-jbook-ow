from __future__ import annotations

from typing import Dict, List, Optional

from .schema import EnrichedRecord


def fuse_r3_with_r2(
    source_file: str,
    r3_rows: List[Dict],
    r2_lookup: Dict[str, Dict[str, Optional[str]]],
    use_r1d_description: bool = False,
) -> List[EnrichedRecord]:
    """
    Given parsed R-3 rows and a lookup of PE -> R-2 text sections, build enriched records.

    - r3_rows: list of dicts with keys: PENumber, PEName, ProjectNumber, ProjectName,
      CostCategory, FY2023_Cost, FY2024_Cost, FY2025_Base_Cost
    - r2_lookup: mapping PENumber -> {mission, accomplishments, acquisition, is_new_start}
    """
    enriched: List[EnrichedRecord] = []
    for row in r3_rows:
        pe = (row.get("PENumber") or "").strip()
        pe_texts = r2_lookup.get(pe, {})
        is_new_start_val = pe_texts.get("is_new_start")
        is_new_start = None
        if isinstance(is_new_start_val, str):
            if is_new_start_val.lower() in ("true", "yes", "1"):
                is_new_start = True
            elif is_new_start_val.lower() in ("false", "no", "0"):
                is_new_start = False

        # Fallback narrative from R-1D Description, if requested and R-2 text missing
        r1d_desc = (row.get("R1D_Description") or "").strip()
        accomplishments_text = pe_texts.get("accomplishments")
        mission_text = pe_texts.get("mission")
        acquisition_text = pe_texts.get("acquisition")
        if use_r1d_description:
            if not accomplishments_text and r1d_desc:
                accomplishments_text = r1d_desc
            if not mission_text and r1d_desc:
                mission_text = r1d_desc

        enriched.append(
            EnrichedRecord(
                SourceFile=source_file,
                PENumber=row.get("PENumber", ""),
                PEName=row.get("PEName", ""),
                ProjectNumber=row.get("ProjectNumber", ""),
                ProjectName=row.get("ProjectName", ""),
                CostCategory=row.get("CostCategory", ""),
                FY2023_Cost=row.get("FY2023_Cost"),
                FY2024_Cost=row.get("FY2024_Cost"),
                FY2025_Base_Cost=row.get("FY2025_Base_Cost"),
                AccomplishmentsText=accomplishments_text,
                AcquisitionStrategyText=acquisition_text,
                IsNewStart=is_new_start,
                MissionDescriptionText=mission_text,
            )
        )

    return enriched
