# J-Book Analysis App: Overview

This document explains how the app works end-to-end and how to use it.

## Modules

- Module 1: ETL (Extract, Transform, Load)
  - Inputs: J‑Book PDF (optional), R‑1D Excel workbooks and/or XML attachments.
  - Tasks:
    - Extract embedded files from PDFs (if provided).
    - Parse structured budget rows (R‑3/R‑1D) from Excel/XML.
    - Locate Exhibit R‑2 pages in the PDF for each Program Element (PE), extract narratives:
      - A. Mission Description and Budget Item Justification
      - C. Accomplishments/Planned Programs
      - D. Acquisition Strategy
      - Detect “New Start” flag heuristically.
    - Fuse structured rows and narratives into a tabular dataset.
  - Output: An enriched CSV with one row per cost item and fields:
    - SourceFile, PENumber, PEName, ProjectNumber, ProjectName, CostCategory
    - FY2023_Cost, FY2024_Cost, FY2025_Base_Cost
    - AccomplishmentsText, AcquisitionStrategyText, IsNewStart, MissionDescriptionText

- Module 2: Analysis + UI
  - Tagging (CLI): Assigns relevance labels (High/Medium/Low) to each row based on narratives and keywords.
    - Uses OpenAI (if configured) or a deterministic keyword heuristic fallback.
  - Streamlit UI: Interactive table with filtering and manual overrides of relevance labels.
    - Displays weighted totals using a configurable weight per label.

## Workflow Variants

- PDF + Excel (preferred)
  - Use the PDF to extract R‑2 narratives; use the Excel to collect structured rows.
- Excel-only
  - If a PDF is not available, parse R‑1D workbooks directly and skip R‑2.
  - Optional: `--use-r1d-description` fills narrative fields from the R‑1D “Description” column.

## Commands

- Build enriched CSV

```
python -m doj_jbook.cli.pipeline \
  --pdf "data/FY25 Air Force Research, Development, Test and Evaluation Vol II.pdf" \
  --xlsx "data/FY25 - addt. excel files/RDTE_OSD_FY2025_Exhibit_R-1D.xlsx" \
  --out data/processed/enriched.csv
```

- Excel-only with narrative fallback

```
python -m doj_jbook.cli.pipeline \
  --xlsx "data/FY25 - addt. excel files/RDTE_OSD_FY2025_Exhibit_R-1D.xlsx" \
  --skip-r2 --use-r1d-description \
  --out data/processed/enriched.csv
```

- Apply LLM tagging

```
python -m doj_jbook.cli.tagging \
  --input data/processed/enriched.csv \
  --output data/processed/enriched_tagged.csv \
  --keywords "C-UAS" hypersonics \
  --provider openai --model gpt-4o-mini \
  --env-file .env
```

- Launch the Streamlit UI

```
streamlit run app/streamlit_app.py -- \
  --input data/processed/enriched_tagged.csv \
  --weights "High=1.0,Medium=0.5,Low=0.0"
```

## Data Notes

- R‑1D parsing
  - Interprets row Type to maintain context (PE → Project → A/PP & CA rows).
  - Skips aggregate “Totals (sum of …)” lines to avoid double-counting.
  - Keeps a per-row `R1D_Description` for optional narrative fallback.

- R‑2 extraction
  - Identifies Exhibit R‑2/R‑2A pages by title markers and PE number match.
  - Extracts section bodies using regex boundaries, tolerant to minor format variations.

## Security and Keys

- Add your OpenAI key only to `.env` (not committed): `OPENAI_API_KEY=sk-...`.
- Rotate any keys that were pasted into chat.

## Extending

- More FY columns: Expand schema and header detection to include FY26–FY29.
- Service-specific patterns: Add refined regex and tag mappings per Service/Volume.
- Vector search (future): Embed narratives for RAG-style semantic queries.
