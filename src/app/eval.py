"""Pure evaluation helpers for the TradeIQ model comparison.

Used by scripts/evaluate_models.py and unit-tested independently of any LLM.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.prompts import INTENTS

# Matches a number (with optional thousands separators / decimals) and an
# optional unit suffix: % , x (multiplier), or magnitude k / m / bn.
_NUM_RE = re.compile(r"(?P<num>\d[\d,]*(?:\.\d+)?)\s*(?P<suffix>bn|%|x|k|m|b)?", re.IGNORECASE)
_SUFFIX_MULT = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000, "bn": 1_000_000_000}


def parse_intent_json(text: str) -> dict[str, Any]:
    """Extract the intent-classifier JSON object from a model response."""
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        data = json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def classified_intent(text: str) -> str:
    """Return the predicted intent label (upper-cased), or '' if invalid."""
    intent = str(parse_intent_json(text).get("intent", "")).strip().upper()
    return intent if intent in INTENTS else ""


def extract_figures(text: str) -> set[str]:
    """Extract normalised numeric figures (expanding k/m/bn, keeping %/x values)."""
    figures: set[str] = set()
    for match in _NUM_RE.finditer(text):
        raw = match.group("num").replace(",", "")
        suffix = (match.group("suffix") or "").lower()
        try:
            value = float(raw)
        except ValueError:
            continue
        if suffix in _SUFFIX_MULT:
            value *= _SUFFIX_MULT[suffix]
        figures.add(str(int(value)) if value.is_integer() else str(value))
    return figures


def groundedness_overlap(answer: str, tool_output: Any) -> float:
    """Fraction of figures in the answer that also appear in the tool output.

    A rough, deterministic signal for fabricated numbers (1.0 = every figure in
    the answer is supported). The LLM judge is the primary groundedness measure.
    """
    answer_figs = extract_figures(answer)
    if not answer_figs:
        return 1.0
    output_figs = extract_figures(json.dumps(tool_output))
    return len(answer_figs & output_figs) / len(answer_figs)
