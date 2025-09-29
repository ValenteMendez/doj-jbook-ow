from __future__ import annotations

import argparse
import sys
from typing import Dict, List, Tuple
from pathlib import Path
import json
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Ensure local package import works when not installed
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from doj_jbook.analysis import tag_relevance_batch
except Exception:
    tag_relevance_batch = None  # type: ignore


def parse_weights(s: str) -> Dict[str, float]:
    # format: "High=1.0,Medium=0.5,Low=0.0"
    parts = [p.strip() for p in s.split(",") if p.strip()]
    out: Dict[str, float] = {"High": 1.0, "Medium": 0.5, "Low": 0.0}
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            try:
                out[k.strip()] = float(v.strip())
            except Exception:
                pass
    return out


def main_cli() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--input", required=True)
    parser.add_argument("--weights", default="High=1.0,Medium=0.5,Low=0.0")
    # streamlit injects its own args, ignore unknown
    args, _ = parser.parse_known_args()
    run_app(args.input, parse_weights(args.weights))


def run_app(csv_path: str, weights: Dict[str, float]):
    load_dotenv()  # load OPENAI_API_KEY if present
    st.set_page_config(page_title="J-Book Tech Tagging", layout="wide")
    st.title("J-Book Technology Relevance Review")

    df = pd.read_csv(csv_path)
    if "Relevance" not in df.columns:
        df["Relevance"] = "Low"
    if "Rationale" not in df.columns:
        df["Rationale"] = ""

    st.sidebar.header("Weights")
    high_w = st.sidebar.number_input("High", value=float(weights.get("High", 1.0)), step=0.1)
    med_w = st.sidebar.number_input("Medium", value=float(weights.get("Medium", 0.5)), step=0.1)
    low_w = st.sidebar.number_input("Low", value=float(weights.get("Low", 0.0)), step=0.1)
    weights = {"High": high_w, "Medium": med_w, "Low": low_w}

    # Filters
    tech_filter = st.sidebar.text_input("Filter by keyword (PE/Project/CostCategory)")
    rel_filter = st.sidebar.multiselect("Filter by Relevance", ["High", "Medium", "Low"], default=["High", "Medium", "Low"])

    st.sidebar.header("LLM Tagging")
    kw_text = st.sidebar.text_input("Keywords (comma-separated)", value="C-UAS, hypersonics")
    provider = st.sidebar.selectbox("Provider", ["openai", "rule-based"], index=0)
    model = st.sidebar.text_input("Model (OpenAI)", value="gpt-4o-mini")
    defs_text = st.sidebar.text_area("Definitions JSON (optional)")
    concurrency = st.sidebar.number_input("Concurrency", min_value=1, max_value=16, value=4, step=1)
    run_llm = st.sidebar.button("Run tagging on filtered rows")

    display_df = df.copy()
    if tech_filter:
        t = tech_filter.lower()
        mask = (
            display_df["PENumber"].astype(str).str.lower().str.contains(t)
            | display_df["PEName"].astype(str).str.lower().str.contains(t)
            | display_df["ProjectName"].astype(str).str.lower().str.contains(t)
            | display_df["CostCategory"].astype(str).str.lower().str.contains(t)
        )
        display_df = display_df[mask]
    display_df = display_df[display_df["Relevance"].isin(rel_filter)]

    if run_llm:
        if tag_relevance_batch is None:
            st.error("LLM tagging not available (package not importable). Ensure PYTHONPATH includes 'src' or install with 'pip install -e .'")
        else:
            keywords: List[str] = [k.strip() for k in kw_text.split(",") if k.strip()]
            try:
                definitions = json.loads(defs_text) if defs_text.strip() else None
            except Exception as e:
                st.error(f"Invalid JSON for definitions: {e}")
                definitions = None
            rows = display_df.to_dict(orient="records")
            prov = provider if provider != "rule-based" else None
            tags = tag_relevance_batch(rows, keywords, definitions=definitions, provider=prov, model=model if prov else None, concurrency=int(concurrency))
            labels, rationales = zip(*tags) if tags else ([], [])
            # Update original df using indices from display_df
            for (idx, (lab, rat)) in zip(display_df.index, zip(labels, rationales)):
                df.loc[idx, "Relevance"] = lab
                df.loc[idx, "Rationale"] = rat
            st.success("Tagging complete. Table updated below.")

    # Weighted total
    def weighted_amount(row):
        w = weights.get(row["Relevance"], 0.0)
        val = 0.0
        for col in ["FY2023_Cost", "FY2024_Cost", "FY2025_Base_Cost"]:
            try:
                val += float(row.get(col) or 0.0)
            except Exception:
                pass
        return w * val

    total = df[df["Relevance"].isin(rel_filter)].apply(weighted_amount, axis=1).sum()
    st.subheader(f"Weighted Total: ${total:,.2f}")

    st.caption("Click a row to view/edit details. Edits persist only in this session.")

    st.dataframe(display_df[[
        "PENumber", "PEName", "ProjectNumber", "ProjectName", "CostCategory",
        "FY2023_Cost", "FY2024_Cost", "FY2025_Base_Cost", "Relevance"
    ]], use_container_width=True)

    st.divider()

    # Row editor
    idx = st.number_input("Row index to edit (from filtered view)", min_value=0, max_value=len(display_df)-1 if len(display_df)>0 else 0, value=0)
    if len(display_df) > 0:
        row = display_df.iloc[int(idx)]
        st.markdown(f"**PE {row['PENumber']} - {row['PEName']}**")
        st.markdown(f"**Project {row['ProjectNumber']} - {row['ProjectName']}**")
        st.markdown(f"**Cost Category:** {row['CostCategory']}")

        with st.expander("Mission Description (A)"):
            st.write(row.get("MissionDescriptionText") or "")
        with st.expander("Accomplishments / Planned (C)"):
            st.write(row.get("AccomplishmentsText") or "")
        with st.expander("Acquisition Strategy (D)"):
            st.write(row.get("AcquisitionStrategyText") or "")

        new_rel = st.selectbox("Relevance", ["High", "Medium", "Low"], index=["High","Medium","Low"].index(row["Relevance"]))
        new_rat = st.text_area("Rationale", value=row.get("Rationale") or "")

        if st.button("Apply override to source dataset"):
            # Update df using original index
            df.loc[row.name, "Relevance"] = new_rel
            df.loc[row.name, "Rationale"] = new_rat
            st.success("Row updated in-memory. Use 'Download CSV' to save.")

    st.divider()
    st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), file_name="enriched_tagged.csv", mime="text/csv")


if __name__ == "__main__":
    main_cli()
