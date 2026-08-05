"""Validation by implantation: turn one defect dial, require the matching probe
— and only it — to move; the clean project must stay silent."""

import numpy as np
import pytest

from raterkit.dataset import Dataset
from raterkit.probes import run_audit
from raterkit.schema import Config, Gold, Rating
from raterkit.synthetic import simulate


def audit_of(**kwargs):
    ratings, gold, config = simulate(**kwargs)
    return run_audit(ratings, gold, config)


@pytest.fixture(scope="module")
def clean():
    return audit_of(seed=0, competence=0.92)


def flag_names(audit):
    return sorted(f.name for f in audit.flags)


def test_clean_project_is_silent(clean):
    assert flag_names(clean) == []


def test_reliability_recovers_competence_ordering():
    alphas = [audit_of(seed=0, competence=c).probe("reliability").value for c in [0.55, 0.75, 0.92]]
    assert alphas[0] < alphas[1] < alphas[2]


def test_careless_crowd_flags_reliability_only():
    audit = audit_of(seed=0, competence=0.55)
    assert flag_names(audit) == ["reliability"]


def test_spammer_is_found_by_name():
    audit = audit_of(seed=0, competence=0.93, n_raters=12, spammers=1, spammer_load=0.7)
    rogue = audit.probe("rogue raters")
    assert rogue.triggered and rogue.value == 1
    assert "r00" in rogue.detail


def test_leaner_flags_bias_not_rogue():
    audit = audit_of(
        seed=0,
        competence=0.95,
        n_items=400,
        n_raters=8,
        hard_share=0.4,
        leaners=1,
        with_gold=False,
    )
    assert audit.probe("rater bias").triggered
    assert not audit.probe("rogue raters").triggered


def test_drift_dial_moves_the_gap():
    still = audit_of(seed=0, competence=0.97).probe("drift")
    tired = audit_of(seed=0, competence=0.97, drift=0.24).probe("drift")
    assert tired.value > still.value
    assert tired.triggered and not still.triggered


def test_leakage_counts_the_implanted_duplicates():
    audit = audit_of(seed=0, competence=0.92, dup_across_splits=12)
    leak = audit.probe("split leakage")
    assert leak.triggered and leak.value == 12


def test_leakage_skips_without_text_or_split():
    ratings, gold, config = simulate(seed=0, with_text=False)
    audit = run_audit(ratings, gold, config)
    assert audit.probe("split leakage") is None
    assert any(s.name == "split leakage" for s in audit.skipped)


def test_stale_gold_flags_flipped_gold():
    good = audit_of(seed=0, competence=0.92)
    bad = audit_of(seed=0, competence=0.92, gold_error=0.08)
    assert not good.probe("stale gold").triggered
    assert bad.probe("stale gold").triggered
    assert bad.probe("stale gold").value > good.probe("stale gold").value


def test_gold_skipped_without_gold_file():
    ratings, _gold, config = simulate(seed=0, with_gold=False)
    audit = run_audit(ratings, None, config)
    assert any(s.name == "stale gold" for s in audit.skipped)


def test_drift_skipped_without_timestamps():
    ratings, gold, config = simulate(seed=0)
    stripped = [r.model_copy(update={"t": None}) for r in ratings]
    audit = run_audit(stripped, gold, config)
    assert any(s.name == "drift" for s in audit.skipped)


def test_ambiguity_tracks_hard_share(clean):
    hard = audit_of(seed=0, competence=0.95, hard_share=0.4, with_gold=False)
    assert hard.probe("ambiguity").value > clean.probe("ambiguity").value


def test_prevalence_never_flags_even_when_extreme():
    audit = audit_of(seed=0, prevalence=[0.94, 0.02, 0.02, 0.02], competence=0.9)
    prev = audit.probe("prevalence")
    assert prev.value > 0.8 and not prev.triggered


def test_prevalence_exhibits_the_kappa_paradox():
    audit = audit_of(seed=0, prevalence=[0.94, 0.02, 0.02, 0.02], competence=0.9)
    # raw agreement high, chance-corrected agreement far lower
    assert "raw agreement" in audit.probe("prevalence").detail
    assert audit.probe("reliability").value < 0.5


def test_rating_depth_reports_spearman_brown(clean):
    depth = clean.probe("rating depth")
    assert depth.value == pytest.approx(3.0, abs=0.2)
    assert "raters per item" in depth.detail


def test_probe_set_is_stable(clean):
    names = [p.name for p in clean.probes]
    assert names == [
        "reliability",
        "rogue raters",
        "rater bias",
        "drift",
        "split leakage",
        "stale gold",
        "ambiguity",
        "prevalence",
        "rating depth",
    ]


def test_audit_is_deterministic():
    a = audit_of(seed=3, competence=0.9)
    b = audit_of(seed=3, competence=0.9)
    assert a.to_dict() == b.to_dict()


def test_dataset_category_order_prefers_config():
    ratings = [
        Rating(item_id="i1", rater_id="a", label="cold"),
        Rating(item_id="i1", rater_id="b", label="hot"),
    ]
    ds = Dataset.build(ratings, Config(labels=["hot", "warm", "cold"]))
    assert ds.cats == ["hot", "warm", "cold"]
    with pytest.raises(ValueError):
        Dataset.build(
            [Rating(item_id="i", rater_id="a", label="tepid")],
            Config(labels=["hot", "cold"]),
        )


def test_pair_table_groups_by_item():
    ratings, _gold, config = simulate(seed=0, n_items=20, n_raters=4, per_item=3)
    ds = Dataset.build(ratings, config)
    rows, groups = ds.pair_table(ds.raters[0])
    assert rows.shape[0] == len(groups)
    assert rows.sum(axis=1).tolist() == [2.0] * rows.shape[0]


def test_marginal_exclude_partitions_totals():
    ratings, _gold, config = simulate(seed=0, n_items=30)
    ds = Dataset.build(ratings, config)
    r = ds.raters[0]
    total = ds.marginal()
    assert np.allclose(ds.marginal(rater_id=r) + ds.marginal(exclude=r), total)


def test_gold_probe_unanimity_logic():
    # 25 items, 2 raters unanimous on label 1, gold says 0 on five of them
    ratings = []
    for i in range(25):
        for r in ["a", "b"]:
            ratings.append(Rating(item_id=f"i{i}", rater_id=r, label=1))
    gold = [Gold(item_id=f"i{i}", label=0 if i < 5 else 1) for i in range(25)]
    audit = run_audit(ratings, gold, Config(labels=[0, 1]))
    stale = audit.probe("stale gold")
    assert stale.value == pytest.approx(0.2)
