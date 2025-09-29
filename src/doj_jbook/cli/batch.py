from __future__ import annotations

import argparse
import glob
import os
from typing import Dict, List, Set

import pandas as pd

from doj_jbook.etl import (
    parse_r3_projects,
    fuse_r3_with_r2,
    extract_r2_sections_for_pe,
    find_r2_pages_for_pe,
)
from doj_jbook.etl.schema import ENRICHED_COLUMNS


def _gather_files(dirs: List[str] | None, globs: List[str] | None, exts: List[str]) -> List[str]:
    files: List[str] = []
    if dirs:
        for d in dirs:
            if not d:
                continue
            try:
                for name in os.listdir(d):
                    p = os.path.join(d, name)
                    if os.path.isfile(p) and any(p.lower().endswith(e) for e in exts):
                        files.append(p)
            except FileNotFoundError:
                continue
    if globs:
        for pattern in globs:
            files.extend(glob.glob(pattern))
    # Deduplicate, keep stable order
    seen = set()
    uniq: List[str] = []
    for f in files:
        if f not in seen:
            uniq.append(f)
            seen.add(f)
    return uniq


def run_batch(
    out_csv: str,
    xlsx_dirs: List[str] | None,
    xlsx_globs: List[str] | None,
    pdf_dirs: List[str] | None,
    pdf_globs: List[str] | None,
    skip_r2: bool,
    use_r1d_description: bool,
) -> None:
    # 1) Collect Excel/XML inputs
    excel_files = _gather_files(xlsx_dirs, xlsx_globs, exts=[".xlsx", ".xlsm", ".xml"])
    if not excel_files:
        raise SystemExit("No Excel/XML files found. Provide --xlsx-dir/--xlsx-glob inputs.")

    # 2) Parse structured rows from all Excel/XML
    r3_rows = parse_r3_projects(excel_files)

    # 3) Optional: Build R-2 lookup by scanning PDFs for PEs
    r2_lookup: Dict[str, Dict] = {}
    if not skip_r2:
        pdf_files = _gather_files(pdf_dirs, pdf_globs, exts=[".pdf"]) if pdf_dirs or pdf_globs else []
        if not pdf_files:
            print("No PDFs provided; proceeding without R-2 extraction.")
        else:
            unique_pes: List[str] = sorted({(r.get("PENumber") or "").strip() for r in r3_rows if (r.get("PENumber") or "").strip()})
            unresolved: Set[str] = set(unique_pes)
            print(f"Scanning {len(pdf_files)} PDFs for {len(unique_pes)} unique PEs...")
            for pdf in pdf_files:
                still = list(unresolved)
                for pe in still:
                    try:
                        pages = find_r2_pages_for_pe(pdf, pe)
                    except Exception:
                        pages = []
                    if not pages:
                        continue
                    try:
                        r2_lookup[pe] = extract_r2_sections_for_pe(pdf, pe)
                        unresolved.discard(pe)
                    except Exception:
                        pass
                if not unresolved:
                    break
            found = len(r2_lookup)
            print(f"Resolved R-2 narratives for {found} PEs; {len(unresolved)} unresolved.")

    # 4) Fuse and write CSV
    enriched = fuse_r3_with_r2("batch", r3_rows, r2_lookup, use_r1d_description=use_r1d_description)
    rows = [e.to_row() for e in enriched]
    df = pd.DataFrame(rows, columns=ENRICHED_COLUMNS)
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    df.to_csv(out_csv, index=False)
    print(f"Wrote {len(df)} rows to {out_csv}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Batch pipeline across multiple PDFs and Excel/XML inputs")
    ap.add_argument("--out", required=True, help="Output CSV path for merged dataset")
    ap.add_argument("--xlsx-dir", nargs="*", default=None, help="Directories containing .xlsx/.xlsm/.xml files")
    ap.add_argument("--xlsx-glob", nargs="*", default=None, help="Glob pattern(s) for Excel/XML files")
    ap.add_argument("--pdf-dir", nargs="*", default=None, help="Directories containing .pdf files for R-2 extraction")
    ap.add_argument("--pdf-glob", nargs="*", default=None, help="Glob pattern(s) for PDFs")
    ap.add_argument("--skip-r2", action="store_true", help="Skip R-2 narrative extraction from PDFs")
    ap.add_argument("--use-r1d-description", action="store_true", help="Fallback to R-1D Description for narratives when R-2 missing")
    args = ap.parse_args()

    run_batch(
        out_csv=args.out,
        xlsx_dirs=args.xlsx_dir,
        xlsx_globs=args.xlsx_glob,
        pdf_dirs=args.pdf_dir,
        pdf_globs=args.pdf_glob,
        skip_r2=args.skip_r2,
        use_r1d_description=args.use_r1d_description,
    )


if __name__ == "__main__":
    main()

