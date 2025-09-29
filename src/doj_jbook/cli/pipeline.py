from __future__ import annotations

import argparse
import os
from typing import Dict, List

import pandas as pd

from doj_jbook.etl import (
    extract_embedded_files,
    list_embedded_files,
    parse_r3_projects,
    extract_r2_sections_for_pe,
    fuse_r3_with_r2,
)
from doj_jbook.etl.schema import ENRICHED_COLUMNS


def run_pipeline(
    pdf_path: str | None,
    out_csv: str,
    extra_inputs: List[str] | None = None,
    skip_r2: bool = False,
    use_r1d_description: bool = False,
) -> None:
    base = os.path.splitext(os.path.basename(pdf_path))[0] if pdf_path else "excel_only"
    work_dir = os.path.join(os.path.dirname(out_csv), base)
    attach_dir = os.path.join(work_dir, "attachments")
    os.makedirs(attach_dir, exist_ok=True)

    # 1) Extract embedded files if a PDF is provided
    extracted_paths: List[str] = []
    if pdf_path:
        try:
            extracted_paths = extract_embedded_files(pdf_path, attach_dir)
        except Exception:
            extracted_paths = []
    all_inputs: List[str] = list(extracted_paths)
    if extra_inputs:
        # include user-provided XML/XLSX files
        all_inputs.extend(extra_inputs)

    # 2) Parse R-3 XML rows
    r3_rows = parse_r3_projects(all_inputs)

    # 3) Extract R-2 text for each PE (optional)
    r2_lookup: Dict[str, Dict] = {}
    if not skip_r2 and pdf_path:
        unique_pes = sorted({(r.get("PENumber") or "").strip() for r in r3_rows if (r.get("PENumber") or "").strip()})
        for pe in unique_pes:
            try:
                r2_lookup[pe] = extract_r2_sections_for_pe(pdf_path, pe)
            except Exception:
                r2_lookup[pe] = {"mission": None, "accomplishments": None, "acquisition": None, "is_new_start": None}

    # 4) Fuse and write CSV
    src_name = os.path.basename(pdf_path) if pdf_path else "excel_only"
    enriched = fuse_r3_with_r2(src_name, r3_rows, r2_lookup, use_r1d_description=use_r1d_description)
    rows = [e.to_row() for e in enriched]
    df = pd.DataFrame(rows, columns=ENRICHED_COLUMNS)
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    df.to_csv(out_csv, index=False)
    print(f"Wrote {len(df)} rows to {out_csv}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Module 1 pipeline: PDF + XML → enriched CSV")
    ap.add_argument("--pdf", required=False, help="Path to J-Book PDF (optional if using Excel only)")
    ap.add_argument("--out", required=True, help="Output CSV path")
    ap.add_argument("--xlsx", nargs="*", default=None, help="Optional additional XML/XLSX files to include")
    ap.add_argument("--xlsx-dir", nargs="*", default=None, help="Directory/directories to scan for .xlsx/.xlsm files")
    ap.add_argument("--xlsx-glob", nargs="*", default=None, help="Glob pattern(s) to include Excel/XML files (quotes recommended)")
    ap.add_argument("--skip-r2", action="store_true", help="Skip R-2 narrative extraction (use when PDF not available)")
    ap.add_argument("--use-r1d-description", action="store_true", help="Fallback to R-1D Description for narratives when R-2 missing")
    args = ap.parse_args()
    inputs: List[str] = []
    if args.xlsx:
        inputs.extend(args.xlsx)
    # scan directories
    if args.xlsx_dir:
        for d in args.xlsx_dir:
            if not d:
                continue
            for name in os.listdir(d):
                if name.lower().endswith((".xlsx", ".xlsm", ".xml")):
                    inputs.append(os.path.join(d, name))
    # glob patterns
    if args.xlsx_glob:
        import glob
        for pattern in args.xlsx_glob:
            inputs.extend(glob.glob(pattern))

    run_pipeline(
        args.pdf,
        args.out,
        extra_inputs=inputs or None,
        skip_r2=args.skip_r2,
        use_r1d_description=args.use_r1d_description,
    )


if __name__ == "__main__":
    main()
