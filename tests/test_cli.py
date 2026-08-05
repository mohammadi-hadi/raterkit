"""CLI behavior and the demo diagonal."""

import json

import pytest

from raterkit.cli import main
from raterkit.demo import build
from raterkit.probes import run_audit
from raterkit.report import inject_readme, render_report
from raterkit.synthetic import simulate


@pytest.fixture()
def ratings_file(tmp_path):
    ratings, gold, config = simulate(seed=0, n_items=120, competence=0.92)
    path = tmp_path / "ratings.jsonl"
    path.write_text("\n".join(r.model_dump_json(exclude_none=True) for r in ratings) + "\n")
    gold_path = tmp_path / "gold.jsonl"
    gold_path.write_text("\n".join(g.model_dump_json() for g in gold) + "\n")
    config_path = tmp_path / "config.json"
    config_path.write_text(config.model_dump_json())
    return path, gold_path, config_path


def test_report_command_writes_outputs(tmp_path, ratings_file, capsys):
    ratings, gold, config = ratings_file
    out = tmp_path / "audit"
    code = main(
        ["report", str(ratings), "--gold", str(gold), "--config", str(config), "--out", str(out)]
    )
    assert code == 0
    payload = json.loads((out / "report.json").read_text())
    assert "probes" in payload and (out / "report.md").exists()
    assert "flag(s)" in capsys.readouterr().out


def test_fail_on_flags_exit_code(tmp_path):
    ratings, gold, config = simulate(seed=0, n_items=150, competence=0.55)
    path = tmp_path / "r.jsonl"
    path.write_text("\n".join(r.model_dump_json(exclude_none=True) for r in ratings) + "\n")
    assert main(["report", str(path), "--out", str(tmp_path / "a")]) == 0
    assert main(["report", str(path), "--out", str(tmp_path / "b"), "--fail-on-flags"]) == 2


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "raterkit" in capsys.readouterr().out


def test_render_report_lists_skips():
    ratings, _gold, config = simulate(seed=0, n_items=60, with_text=False, with_gold=False)
    audit = run_audit(ratings, None, config)
    text = render_report(audit)
    assert "Skipped checks" in text and "stale gold" in text


def test_inject_readme_roundtrip(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    (results / "table.md").write_text("| a |\n|---|\n| 1 |")
    readme = tmp_path / "README.md"
    readme.write_text("before\n<!-- raterkit:demo -->\nold\n<!-- /raterkit:demo -->\nafter\n")
    inject_readme(readme, results)
    text = readme.read_text()
    assert "| 1 |" in text and "old" not in text and text.count("raterkit:demo") == 2


def test_demo_flags_land_on_the_diagonal():
    results = build()
    expected = {
        "clean": set(),
        "careless-crowd": {"reliability"},
        "one-spammer": {"rogue raters"},
        "leaning-rater": {"rater bias"},
        "tiring-crowd": {"drift"},
        "leaky-split": {"split leakage"},
        "stale-gold": {"stale gold"},
        "easy-but-skewed": {"reliability"},
    }
    assert len(results) == len(expected)
    for row, _seed, audit in results:
        assert {f.name for f in audit.flags} == expected[row.name], row.name
