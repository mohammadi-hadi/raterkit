"""Schema validation, loaders and result semantics."""

import json
import math

import pytest
from pydantic import ValidationError

from raterkit.result import AuditResult, ProbeResult, SkippedProbe
from raterkit.schema import Config, Rating, load_config, load_gold, load_ratings


def test_rating_rejects_extra_and_empty_fields():
    with pytest.raises(ValidationError):
        Rating(item_id="i", rater_id="r", label=1, extra="no")
    with pytest.raises(ValidationError):
        Rating(item_id="", rater_id="r", label=1)


def test_config_validation():
    assert Config().level == "nominal"
    with pytest.raises(ValidationError):
        Config(level="cardinal")
    with pytest.raises(ValidationError):
        Config(target_reliability=1.5)


def test_loaders_roundtrip(tmp_path):
    ratings_path = tmp_path / "ratings.jsonl"
    ratings_path.write_text(
        '{"item_id": "i1", "rater_id": "a", "label": "x"}\n'
        '\n{"item_id": "i1", "rater_id": "b", "label": "y", "t": 3.0}\n'
    )
    gold_path = tmp_path / "gold.jsonl"
    gold_path.write_text('{"item_id": "i1", "label": "x"}\n')
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"level": "ordinal", "labels": ["x", "y"]}))
    assert len(load_ratings(ratings_path)) == 2
    assert load_gold(gold_path)[0].label == "x"
    assert load_config(config_path).level == "ordinal"


def test_loader_errors_carry_line_numbers(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"item_id": "i1", "rater_id": "a", "label": 1}\n{"nope": 1}\n')
    with pytest.raises(ValueError, match="bad.jsonl:2"):
        load_ratings(path)


def test_band_probe_triggers_only_when_ci_disjoint():
    band = (0.667, 1.0)
    inside = ProbeResult("p", 0.7, "", 1, ci=(0.68, 0.75), innocent=band)
    overlap = ProbeResult("p", 0.65, "", 1, ci=(0.6, 0.7), innocent=band)
    below = ProbeResult("p", 0.5, "", 1, ci=(0.4, 0.6), innocent=band)
    assert not inside.triggered and not overlap.triggered and below.triggered


def test_flagged_overrides_band():
    p = ProbeResult("p", 0.9, "", 1, ci=(0.85, 0.95), innocent=(0.667, 1.0), flagged=True)
    assert p.triggered
    q = ProbeResult("p", 0.2, "", 1, ci=(0.1, 0.3), innocent=(0.667, 1.0), flagged=False)
    assert not q.triggered


def test_no_ci_no_band_never_triggers():
    assert not ProbeResult("p", 0.1, "", 1).triggered


def test_audit_result_to_dict_replaces_nan():
    audit = AuditResult(
        probes=[ProbeResult("p", float("nan"), "detail", 3)],
        skipped=[SkippedProbe("q", "reason")],
    )
    d = audit.to_dict()
    assert d["probes"][0]["value"] is None
    assert not math.isnan(d["probes"][0]["n"])
    assert d["skipped"][0]["name"] == "q"
    assert d["flags"] == []
