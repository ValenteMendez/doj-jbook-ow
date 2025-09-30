from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Dict, Tuple, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import json

try:
    # OpenAI SDK v1
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None  # type: ignore


RelevanceTag = str  # "High" | "Medium" | "Low"


def _to_text(val: Any) -> str:
    if val is None:
        return ""
    try:
        # Handle pandas NaN (float("nan"))
        if isinstance(val, float) and (val != val):  # NaN check
            return ""
    except Exception:
        pass
    return str(val)


def build_corpus(row: Dict, max_length: int = 8000) -> str:
    parts_raw = [
        row.get("AccomplishmentsText"),
        row.get("AcquisitionStrategyText"),
        row.get("MissionDescriptionText"),
    ]
    parts: List[str] = []
    for pr in parts_raw:
        text = _to_text(pr).strip()
        if text:
            # Truncate individual parts to prevent API timeouts
            if len(text) > max_length // 3:
                text = text[:max_length // 3] + "... [truncated]"
            parts.append(text)

    corpus = "\n\n".join(parts)
    # Final check to ensure total corpus is within limits
    if len(corpus) > max_length:
        corpus = corpus[:max_length] + "... [truncated]"

    return corpus


def _rule_based_relevance(corpus: str, keywords: List[str]) -> Tuple[RelevanceTag, str]:
    c = corpus.lower()
    k_hits = 0
    primary_hits = 0
    for k in keywords:
        k = k.lower().strip()
        if not k:
            continue
        if k in c:
            k_hits += 1
            # crude heuristic for primary focus phrases
            if any(p in c for p in [f"focus on {k}", f"developing {k}", f"{k} program", f"{k} system", f"{k} capability"]):
                primary_hits += 1

    if primary_hits >= 1:
        return ("High", "Primary focus phrases matched")
    if k_hits >= 1:
        return ("Medium", "Keyword mentioned in context")
    return ("Low", "No direct keyword match")


def _openai_tag_one(
    corpus: str,
    keywords: List[str],
    definitions: Dict[str, str] | None,
    model: str,
    client: Any | None = None,
) -> Tuple[RelevanceTag, str]:
    if OpenAI is None:
        raise RuntimeError("openai package not installed. Install requirements.txt")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in environment")
    client = client or OpenAI(api_key=api_key)

    sys_prompt = (
        "You are a defense technology analyst. Classify relevance of budget text to target technologies.\n"
        "Return a strict JSON object with keys: label (one of High, Medium, Low) and rationale (short string)."
    )
    user_content = {
        "keywords": keywords,
        "definitions": definitions or {},
        "corpus": corpus,
        "instructions": {
            "High": "technology is a primary focus or core deliverable",
            "Medium": "technology is a secondary component or enabling area",
            "Low": "technology only mentioned in passing or unrelated",
        },
    }
    prompt = json.dumps(user_content)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        content = resp.choices[0].message.content or "{}"

        # Strip markdown code blocks if present
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        data = json.loads(content)
        label = str(data.get("label", "Low"))
        rationale = str(data.get("rationale", ""))
        if label not in ("High", "Medium", "Low"):
            label = "Low"
        return label, rationale
    except json.JSONDecodeError as e:
        return ("Low", f"JSON parse error: {e}. Content was: {repr(content)}")
    except Exception as e:
        return ("Low", f"OpenAI error: {e}")


def tag_relevance_batch(
    rows: List[Dict],
    keywords: List[str],
    definitions: Dict[str, str] | None = None,
    provider: str | None = None,
    model: str | None = None,
    concurrency: int = 1,
) -> List[Tuple[RelevanceTag, str]]:
    """
    Tag each row with a relevance label and a brief rationale.
    - If no LLM provider is configured, fall back to a deterministic heuristic.
    - Integrate LLM providers later by replacing the internals here.
    """
    results: List[Tuple[RelevanceTag, str]] = []
    use_openai = provider and provider.lower() == "openai" and model

    # Sequential, non-LLM or concurrency=1 path
    if not use_openai or concurrency <= 1:
        for row in rows:
            corpus = build_corpus(row)
            if use_openai:
                try:
                    results.append(_openai_tag_one(corpus, keywords, definitions, model=model or "gpt-4o-mini"))
                    continue
                except Exception:
                    pass
            label, why = _rule_based_relevance(corpus, keywords)
            results.append((label, why))
        return results

    # Parallel OpenAI tagging with threads; preserve order
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # fail closed to rule-based
        return [
            _rule_based_relevance(build_corpus(row), keywords)
            for row in rows
        ]

    client = OpenAI(api_key=api_key) if OpenAI is not None else None

    def task(idx_row: Tuple[int, Dict]) -> Tuple[int, RelevanceTag, str]:
        i, r = idx_row
        corpus = build_corpus(r)
        try:
            label, why = _openai_tag_one(corpus, keywords, definitions, model=model or "gpt-4o-mini", client=client)
        except Exception:
            label, why = _rule_based_relevance(corpus, keywords)
        return i, label, why

    indexed = list(enumerate(rows))
    out: List[Optional[Tuple[RelevanceTag, str]]] = [None] * len(indexed)
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
        futures = [ex.submit(task, item) for item in indexed]
        for fut in as_completed(futures):
            i, lab, rat = fut.result()
            out[i] = (lab, rat)

    return [o if o is not None else ("Low", "Missing result") for o in out]
