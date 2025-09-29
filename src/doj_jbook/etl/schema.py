from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any, List


ENRICHED_COLUMNS: List[str] = [
    "SourceFile",
    "PENumber",
    "PEName",
    "ProjectNumber",
    "ProjectName",
    "CostCategory",
    "FY2023_Cost",
    "FY2024_Cost",
    "FY2025_Base_Cost",
    "AccomplishmentsText",
    "AcquisitionStrategyText",
    "IsNewStart",
    "MissionDescriptionText",
]


@dataclass
class EnrichedRecord:
    SourceFile: str
    PENumber: str
    PEName: str
    ProjectNumber: str
    ProjectName: str
    CostCategory: str
    FY2023_Cost: float | None
    FY2024_Cost: float | None
    FY2025_Base_Cost: float | None
    AccomplishmentsText: str | None
    AcquisitionStrategyText: str | None
    IsNewStart: bool | None
    MissionDescriptionText: str | None

    def to_row(self) -> Dict[str, Any]:
        row = asdict(self)
        # Cast booleans to True/False, leave None as-is
        return row

