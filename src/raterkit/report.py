"""Markdown reports and figures."""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .dataset import Dataset
from .demo import ROWS, DemoRow, build
from .probes import rater_agreements
from .result import AuditResult
from .schema import Config
from .stats import spearman_brown
from .synthetic import simulate

ACCENT = "#4338ca"
ALERT = "#b91c1c"
NEUTRAL = "#6b7280"

_BAND_TEXT = {
    "reliability": "alpha at or above 0.667",
    "rater bias": "every rater within 0.10 total variation of the rest",
    "drift": "early-late alpha gap within ±0.10",
    "stale gold": "at most 2% of gold contradicted by a unanimous crowd",
    "rogue raters": "no rater credibly below the pool",
    "split leakage": "no duplicated text spanning splits",
    "ambiguity": "descriptive",
    "prevalence": "descriptive",
    "rating depth": "descriptive",
}


def _fmt(value: float, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    if value == float("inf"):
        return "inf"
    return f"{value:.{digits}f}"


def render_report(audit: AuditResult, title: str = "raterkit audit") -> str:
    lines = [f"# {title}", ""]
    flags = audit.flags
    if flags:
        lines.append(f"**{len(flags)} flag(s):** " + ", ".join(p.name for p in flags))
    else:
        lines.append("**No flags.**")
    lines += ["", "| probe | value | 95% CI | innocent band | flag |", "|---|---|---|---|---|"]
    for p in audit.probes:
        ci = f"({_fmt(p.ci[0])}, {_fmt(p.ci[1])})" if p.ci else "-"
        band = _BAND_TEXT.get(p.name, "-")
        mark = "**yes**" if p.triggered else ""
        lines.append(f"| {p.name} | {_fmt(p.value)} {p.unit} | {ci} | {band} | {mark} |")
    lines.append("")
    for p in audit.probes:
        lines.append(f"- **{p.name}** (n={p.n}): {p.detail}")
    if audit.skipped:
        lines += ["", "## Skipped checks", ""]
        for s in audit.skipped:
            lines.append(f"- **{s.name}**: {s.reason}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


def _cell(audit: AuditResult, name: str, kind: str) -> str:
    p = audit.probe(name)
    if p is None:
        return "-"
    if kind == "count":
        text = f"{int(p.value)}"
    elif kind == "share":
        text = f"{p.value:.1%}"
    elif kind == "gap":
        text = f"{p.value:+.2f}"
    else:
        text = _fmt(p.value, 2)
    return f"**{text}**" if p.triggered else text


def demo_table(results: list[tuple[DemoRow, int, AuditResult]]) -> str:
    lines = [
        "| project | implanted defect | alpha | rogue | biased | drift gap | leaks "
        "| stale gold | flags |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row, _seed, audit in results:
        flags = ", ".join(sorted(f.name for f in audit.flags)) or "none"
        lines.append(
            f"| {row.name} | {row.defect} | {_cell(audit, 'reliability', 'value')} "
            f"| {_cell(audit, 'rogue raters', 'count')} | {_cell(audit, 'rater bias', 'count')} "
            f"| {_cell(audit, 'drift', 'gap')} | {_cell(audit, 'split leakage', 'count')} "
            f"| {_cell(audit, 'stale gold', 'share')} | {flags} |"
        )
    return "\n".join(lines)


def demo_report(results: list[tuple[DemoRow, int, AuditResult]]) -> str:
    lines = [
        "# raterkit demo",
        "",
        "Eight synthetic annotation projects, seven implanted defects. Each audit",
        "must flag exactly the defect its row implants — and nothing on the clean row.",
        "",
        demo_table(results),
        "",
    ]
    for row, seed, audit in results:
        lines.append(f"## {row.name} (seed {seed})")
        lines.append("")
        lines.append(f"Implanted: {row.defect}.")
        lines.append("")
        lines.append(render_report(audit, title=f"audit: {row.name}").split("\n", 2)[2])
    return "\n".join(lines)


def rater_forest_figure(results: list[tuple[DemoRow, int, AuditResult]], path: Path) -> None:
    """Rater-vs-rest alpha with CIs for the one-spammer project."""
    row, seed, audit = next(r for r in results if r[0].name == "one-spammer")
    ratings, _gold, config = simulate(seed=seed, **row.kwargs)
    ds = Dataset.build(ratings, Config.model_validate(config.model_dump()))
    agreements = rater_agreements(ds)
    pool = audit.probe("reliability")
    assert pool is not None and pool.ci is not None
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.axhspan(pool.ci[0], pool.ci[1], color=ACCENT, alpha=0.12, lw=0)
    ax.axhline(pool.value, color=ACCENT, lw=1.2, label="pool alpha (95% CI band)")
    labels, worst = [], min(a[1] for a in agreements)
    for i, (rater, value, ci, _n) in enumerate(agreements):
        color = ALERT if ci is not None and ci[1] < pool.ci[0] else NEUTRAL
        if ci is not None:
            ax.vlines(i, ci[0], ci[1], color=color, lw=2)
        ax.plot([i], [value], "o", color=color, ms=5)
        labels.append(rater)
    ax.set_xticks(range(len(labels)), labels, rotation=45, fontsize=8)
    ax.set_ylabel("rater-vs-rest alpha")
    ax.set_title("One spammer, found: each rater's agreement with the rest")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper right")
    ax.annotate(
        "credibly below the pool",
        xy=(labels.index(min(agreements, key=lambda a: a[1])[0]), worst),
        xytext=(len(labels) * 0.45, worst + 0.08),
        color=ALERT,
        fontsize=9,
        arrowprops=dict(arrowstyle="->", color=ALERT, lw=1),
    )
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def depth_curve_figure(results: list[tuple[DemoRow, int, AuditResult]], path: Path) -> None:
    """Spearman-Brown projection: raters per item vs reliability of the averaged label."""
    picks = [("clean", ACCENT), ("careless-crowd", ALERT)]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ks = [k / 4.0 for k in range(4, 61)]
    for name, color in picks:
        audit = next(a for r, _s, a in results if r.name == name)
        pool = audit.probe("reliability")
        assert pool is not None
        ax.plot(
            ks,
            [spearman_brown(pool.value, k) for k in ks],
            color=color,
            lw=2,
            label=f"{name} (alpha {pool.value:.2f})",
        )
    ax.axhline(0.8, color=NEUTRAL, lw=1, ls="--")
    ax.text(14.2, 0.805, "target 0.80", color=NEUTRAL, fontsize=9, ha="right")
    ax.set_xlabel("raters per item (aggregated label)")
    ax.set_ylabel("projected reliability (Spearman-Brown)")
    ax.set_title("What another rater per item buys, at two starting alphas")
    ax.set_xlim(1, 15)
    ax.set_ylim(0, 1)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_demo(out_dir: str | Path) -> list[tuple[DemoRow, int, AuditResult]]:
    out = Path(out_dir)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    results = build()
    (out / "table.md").write_text(demo_table(results) + "\n", encoding="utf-8")
    (out / "report.md").write_text(demo_report(results) + "\n", encoding="utf-8")
    (out / "demo.json").write_text(
        json.dumps(
            {row.name: {"seed": seed, **audit.to_dict()} for row, seed, audit in results},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    rater_forest_figure(results, out / "figures" / "rater_forest.png")
    depth_curve_figure(results, out / "figures" / "depth_curve.png")
    return results


MARK_START = "<!-- raterkit:demo -->"
MARK_END = "<!-- /raterkit:demo -->"


def inject_readme(readme_path: str | Path, results_dir: str | Path) -> None:
    readme = Path(readme_path)
    table = (Path(results_dir) / "table.md").read_text(encoding="utf-8").rstrip()
    text = readme.read_text(encoding="utf-8")
    start = text.index(MARK_START) + len(MARK_START)
    end = text.index(MARK_END)
    readme.write_text(text[:start] + "\n" + table + "\n" + text[end:], encoding="utf-8")


assert ROWS  # imported for demo consumers; keeps the import explicit
