from __future__ import annotations

import argparse
import json
import os
from typing import Dict, List

import pandas as pd

from doj_jbook.analysis import tag_relevance_batch
from dotenv import load_dotenv


def run_tagging(
    input_csv: str,
    output_csv: str,
    keywords: List[str],
    definitions_path: str | None,
    provider: str | None,
    model: str | None,
    env_file: str | None,
    concurrency: int,
) -> None:
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()
    df = pd.read_csv(input_csv)
    defs: Dict[str, str] | None = None
    if definitions_path and os.path.isfile(definitions_path):
        with open(definitions_path, "r", encoding="utf-8") as f:
            defs = json.load(f)

    # Build rows to tag
    rows = df.to_dict(orient="records")
    tags = tag_relevance_batch(rows, keywords, definitions=defs, provider=provider, model=model, concurrency=concurrency)
    labels, rationales = zip(*tags) if tags else ([], [])

    df["Relevance"] = list(labels)
    df["Rationale"] = list(rationales)
    df.to_csv(output_csv, index=False)
    print(f"Wrote tagged dataset to {output_csv}")


def main():
    ap = argparse.ArgumentParser(description="Module 2 tagging: attach relevance labels to enriched CSV")
    ap.add_argument("--input", required=True, help="Path to enriched CSV")
    ap.add_argument("--output", required=True, help="Output CSV path")
    ap.add_argument("--keywords", nargs="+", required=True, help="Technology keywords e.g. C-UAS hypersonics")
    ap.add_argument("--definitions", default=None, help="Optional JSON file of definitions/taxonomy")
    ap.add_argument("--provider", default=None, help="LLM provider (e.g., openai)")
    ap.add_argument("--model", default=None, help="LLM model (e.g., gpt-4o-mini)")
    ap.add_argument("--env-file", default=None, help="Optional .env file to load (for OPENAI_API_KEY)")
    ap.add_argument("--concurrency", type=int, default=4, help="Parallel request workers for OpenAI provider")
    args = ap.parse_args()

    run_tagging(
        args.input,
        args.output,
        args.keywords,
        args.definitions,
        args.provider,
        args.model,
        args.env_file,
        args.concurrency,
    )


if __name__ == "__main__":
    main()
