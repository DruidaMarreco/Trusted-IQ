"""Unit tests for the pure evaluation helpers."""

from app.eval import classified_intent, extract_figures, groundedness_overlap, parse_intent_json


def test_parse_and_classify_intent() -> None:
    text = 'noise {"intent": "data_query", "confidence": 0.9} trailing'
    assert parse_intent_json(text)["confidence"] == 0.9
    assert classified_intent(text) == "DATA_QUERY"


def test_classify_invalid_returns_empty() -> None:
    assert classified_intent("no json here") == ""
    assert classified_intent('{"intent": "NONSENSE"}') == ""


def test_extract_figures_expands_suffixes() -> None:
    figs = extract_figures("ROI **142%**, uplift 1.8x, £2.1m incremental")
    assert {"142", "1.8", "2100000"} <= figs


def test_groundedness_overlap() -> None:
    tool_output = {"roi_predicted_pct": 142, "uplift_factor": 1.8, "incremental_volume_gbp": 2100000}
    grounded = "ROI **142%**, uplift 1.8x, £2.1m incremental."
    assert groundedness_overlap(grounded, tool_output) == 1.0

    fabricated = "ROI 142% plus a guaranteed 999% bonus uplift."
    assert groundedness_overlap(fabricated, tool_output) < 1.0

    assert groundedness_overlap("no figures at all", tool_output) == 1.0
