"""Audit the GoEmotions crowd labels with raterkit's statistics.

211,225 ratings by 82 raters over 58,011 Reddit comments, 28 binary emotion
labels each (Demszky et al., ACL 2020). Each emotion is audited as its own
binary labeling task: Krippendorff's alpha with a bootstrap CI, per-rater
agreement against the rest, and Spearman-Brown projections of what the
observed reliability implies.

The per-label alpha here uses a vectorized binary formula for speed; it is
asserted equal (1e-10) to raterkit.stats.krippendorff_alpha on a subsample
before anything else runs.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from raterkit.stats import krippendorff_alpha, raters_needed, spearman_brown  # noqa: E402

DATA_DIR = Path(__file__).parent / "data"
OUT_DIR = Path(__file__).parent / "results"
FILES = ["goemotions_1.csv", "goemotions_2.csv", "goemotions_3.csv"]

ALPHA_FLOOR = 0.667
ACCENT = "#4338ca"
ALERT = "#b91c1c"
NEUTRAL = "#6b7280"
N_BOOT_LABEL = 1000
N_BOOT_RATER = 500
MIN_RATER_ITEMS = 300
SEED = 0


def load() -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """Returns (emotions, item_of_row, rater_of_row, votes, unclear, texts_by_item)."""
    emotions: list[str] = []
    item_ids: dict[str, int] = {}
    rater_ids: dict[str, int] = {}
    rows_item, rows_rater, rows_votes, rows_unclear = [], [], [], []
    texts: list[str] = []
    for name in FILES:
        with open(DATA_DIR / name, encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            if not emotions:
                emotions = header[header.index("example_very_unclear") + 1 :]
            e0 = header.index("example_very_unclear") + 1
            id_col, rater_col = header.index("id"), header.index("rater_id")
            unclear_col, text_col = header.index("example_very_unclear"), header.index("text")
            for row in reader:
                item = row[id_col]
                if item not in item_ids:
                    item_ids[item] = len(item_ids)
                    texts.append(row[text_col])
                rater = row[rater_col]
                if rater not in rater_ids:
                    rater_ids[rater] = len(rater_ids)
                rows_item.append(item_ids[item])
                rows_rater.append(rater_ids[rater])
                rows_votes.append([int(v) for v in row[e0:]])
                rows_unclear.append(row[unclear_col] in ("True", "TRUE", "1", "true"))
    return (
        emotions,
        np.array(rows_item),
        np.array(rows_rater),
        np.array(rows_votes, dtype=np.int16),
        np.array(rows_unclear),
        texts,
    )


def binary_alpha(m: np.ndarray, n1: np.ndarray) -> float:
    """Krippendorff's nominal alpha for a binary label from per-item counts."""
    mask = m >= 2
    mm, p = m[mask].astype(float), n1[mask].astype(float)
    if mm.size == 0:
        return float("nan")
    mismatches = (2.0 * p * (mm - p) / (mm - 1.0)).sum()
    n_pres, n_tot = p.sum(), mm.sum()
    n_abs = n_tot - n_pres
    if n_tot <= 1:
        return float("nan")
    d_o = mismatches / n_tot
    d_e = 2.0 * n_pres * n_abs / (n_tot * (n_tot - 1.0))
    if d_e == 0.0:
        return float("nan")
    return 1.0 - d_o / d_e


def validate_binary_alpha(m: np.ndarray, n1: np.ndarray) -> None:
    take = slice(0, 2000)
    counts = np.stack([(m - n1)[take], n1[take]], axis=1).astype(float)
    reference = krippendorff_alpha(counts, [0, 1], "nominal")
    fast = binary_alpha(m[take], n1[take])
    assert abs(fast - reference) < 1e-10, (fast, reference)


def label_alphas(
    emotions: list[str], m: np.ndarray, n1_by_e: np.ndarray, rng: np.random.Generator
) -> list[dict]:
    out = []
    n_items = m.size
    for e, emotion in enumerate(emotions):
        point = binary_alpha(m, n1_by_e[:, e])
        draws = np.empty(N_BOOT_LABEL)
        for b in range(N_BOOT_LABEL):
            idx = rng.integers(0, n_items, size=n_items)
            draws[b] = binary_alpha(m[idx], n1_by_e[idx, e])
        lo, hi = float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))
        out.append(
            {
                "emotion": emotion,
                "alpha": point,
                "ci": [lo, hi],
                "prevalence": float(n1_by_e[:, e].sum() / m.sum()),
                "below_floor": hi < ALPHA_FLOOR,
            }
        )
    return out


def rater_alphas(
    item_of_row: np.ndarray,
    rater_of_row: np.ndarray,
    votes: np.ndarray,
    m: np.ndarray,
    n1_by_e: np.ndarray,
    rng: np.random.Generator,
) -> tuple[list[dict], float, tuple[float, float]]:
    """Per-rater pooled binary alpha against co-raters, plus the pooled pool alpha."""

    def pair_alpha(v: np.ndarray, others_pres: np.ndarray, others_n: np.ndarray) -> float:
        # v: this side's votes per (row, emotion); others_*: co-rater counts.
        pairs = others_n.sum()
        if pairs <= 0:
            return float("nan")
        mismatch = (v * (others_n - others_pres) + (1 - v) * others_pres).sum()
        n_vals = 2.0 * pairs
        n_pres = (v * others_n).sum() + others_pres.sum()
        n_abs = n_vals - n_pres
        d_o = mismatch / pairs
        d_e = 2.0 * n_pres * n_abs / (n_vals * (n_vals - 1.0))
        if d_e == 0.0:
            return float("nan")
        return 1.0 - d_o / d_e

    others_pres_all = n1_by_e[item_of_row] - votes  # per row: co-rater present counts
    others_n_all = (m[item_of_row] - 1)[:, None] * np.ones_like(votes)

    pool_point = pair_alpha(votes, others_pres_all, others_n_all)
    n_rows = votes.shape[0]
    draws = np.empty(200)
    for b in range(200):
        idx = rng.integers(0, n_rows, size=n_rows)
        draws[b] = pair_alpha(votes[idx], others_pres_all[idx], others_n_all[idx])
    pool_ci = (float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975)))

    out = []
    for rater in range(int(rater_of_row.max()) + 1):
        rows = np.flatnonzero(rater_of_row == rater)
        if rows.size < MIN_RATER_ITEMS:
            continue
        v, op, on = votes[rows], others_pres_all[rows], others_n_all[rows]
        point = pair_alpha(v, op, on)
        rdraws = np.empty(N_BOOT_RATER)
        for b in range(N_BOOT_RATER):
            idx = rng.integers(0, rows.size, size=rows.size)
            rdraws[b] = pair_alpha(v[idx], op[idx], on[idx])
        lo, hi = float(np.quantile(rdraws, 0.025)), float(np.quantile(rdraws, 0.975))
        out.append(
            {
                "rater": int(rater),
                "n_ratings": int(rows.size),
                "alpha": point,
                "ci": [lo, hi],
                "below_pool": hi < pool_ci[0],
            }
        )
    return out, pool_point, pool_ci


def figure(per_label: list[dict], path: Path) -> None:
    ordered = sorted(per_label, key=lambda d: d["alpha"])
    names = [d["emotion"] for d in ordered]
    alphas = [d["alpha"] for d in ordered]
    los = [d["alpha"] - d["ci"][0] for d in ordered]
    his = [d["ci"][1] - d["alpha"] for d in ordered]
    colors = [ALERT if d["ci"][1] < ALPHA_FLOOR else ACCENT for d in ordered]
    fig, ax = plt.subplots(figsize=(7.6, 7.0))
    y = np.arange(len(names))
    ax.barh(y, alphas, xerr=[los, his], color=colors, height=0.7, error_kw=dict(lw=0.8))
    ax.axvline(ALPHA_FLOOR, color=NEUTRAL, lw=1.2, ls="--")
    ax.text(ALPHA_FLOOR + 0.01, len(names) - 0.6, "0.667 floor", color=NEUTRAL, fontsize=9)
    ax.set_yticks(y, names, fontsize=8)
    ax.set_xlabel("Krippendorff's alpha (binary, 95% bootstrap CI)")
    ax.set_title("GoEmotions: per-emotion agreement, 211k ratings")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(left=min(0.0, min(alphas) - 0.05))
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    rng = np.random.Generator(np.random.PCG64(SEED))
    emotions, item_of_row, rater_of_row, votes, unclear, texts = load()
    n_items = int(item_of_row.max()) + 1
    m = np.bincount(item_of_row, minlength=n_items)
    n1_by_e = np.zeros((n_items, len(emotions)))
    for e in range(len(emotions)):
        n1_by_e[:, e] = np.bincount(item_of_row, weights=votes[:, e], minlength=n_items)

    validate_binary_alpha(m, n1_by_e[:, emotions.index("neutral")].astype(int))

    per_label = label_alphas(emotions, m, n1_by_e, rng)
    per_rater, pool_alpha, pool_ci = rater_alphas(item_of_row, rater_of_row, votes, m, n1_by_e, rng)

    below = [d for d in per_label if d["below_floor"]]
    median_alpha = float(np.median([d["alpha"] for d in per_label]))
    rogue = [d for d in per_rater if d["below_pool"]]

    multi = m >= 2
    contested_any = np.zeros(n_items, dtype=bool)
    for e in range(len(emotions)):
        n1 = n1_by_e[:, e]
        contested_any |= (n1 > 0) & (n1 < m)
    contested_share = float(contested_any[multi].mean())
    unclear_share = float(unclear.mean())

    norm = {}
    dup_items = 0
    for t in texts:
        key = " ".join(t.lower().split())
        norm[key] = norm.get(key, 0) + 1
    dup_texts = sum(1 for v in norm.values() if v > 1)
    dup_items = sum(v for v in norm.values() if v > 1)

    mean_depth = float(m.mean())
    k_for_target = raters_needed(median_alpha, 0.8)
    reliability_at_depth = spearman_brown(median_alpha, mean_depth)

    summary = {
        "n_ratings": int(votes.shape[0]),
        "n_items": n_items,
        "n_raters": int(rater_of_row.max()) + 1,
        "mean_ratings_per_item": mean_depth,
        "pool_alpha_binary_pooled": pool_alpha,
        "pool_alpha_ci": list(pool_ci),
        "median_label_alpha": median_alpha,
        "labels_below_floor": len(below),
        "labels_total": len(emotions),
        "worst_labels": [
            {"emotion": d["emotion"], "alpha": d["alpha"]}
            for d in sorted(per_label, key=lambda d: d["alpha"])[:5]
        ],
        "best_labels": [
            {"emotion": d["emotion"], "alpha": d["alpha"]}
            for d in sorted(per_label, key=lambda d: -d["alpha"])[:3]
        ],
        "raters_tested": len(per_rater),
        "raters_below_pool": len(rogue),
        "contested_item_share": contested_share,
        "very_unclear_rating_share": unclear_share,
        "duplicate_texts": dup_texts,
        "duplicate_items": dup_items,
        "raters_needed_for_080_at_median_alpha": k_for_target,
        "projected_reliability_at_actual_depth": reliability_at_depth,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "figures").mkdir(exist_ok=True)
    (OUT_DIR / "goemotions.json").write_text(
        json.dumps({"summary": summary, "per_label": per_label, "per_rater": per_rater}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    figure(per_label, OUT_DIR / "figures" / "label_alpha.png")

    lines = [
        "# GoEmotions, audited",
        "",
        f"{summary['n_ratings']:,} ratings, {summary['n_items']:,} comments, "
        f"{summary['n_raters']} raters, {mean_depth:.1f} ratings per comment. Each of the "
        "28 emotions audited as a binary labeling task.",
        "",
        f"- **{len(below)} of {len(emotions)} emotions** have a 95% CI entirely below the "
        f"0.667 reliability floor; the median per-emotion alpha is **{median_alpha:.2f}**.",
        "- Best: "
        + ", ".join(f"{d['emotion']} ({d['alpha']:.2f})" for d in summary["best_labels"])
        + ". Worst: "
        + ", ".join(f"{d['emotion']} ({d['alpha']:.2f})" for d in summary["worst_labels"][:3])
        + ".",
        f"- Pooled over all 28 binary decisions, alpha = **{pool_alpha:.2f}** "
        f"(95% CI {pool_ci[0]:.2f}-{pool_ci[1]:.2f}).",
        f"- Rater-vs-rest alpha spans **{min(d['alpha'] for d in per_rater):.2f} to "
        f"{max(d['alpha'] for d in per_rater):.2f}** across the {len(per_rater)} raters with "
        f"{MIN_RATER_ITEMS}+ ratings; "
        f"{sum(1 for d in per_rater if d['alpha'] < 0.2)} of them sit below 0.20. "
        "(At 211k ratings the pooled CI is so tight that 'credibly below the pool' only means "
        "below average — the range is the honest statistic here.)",
        f"- {contested_share:.0%} of multi-rated comments are contested on at least one "
        f"emotion; raters marked {unclear_share:.1%} of ratings 'very unclear'.",
        f"- {dup_texts:,} duplicated texts appear under {dup_items:,} different item ids.",
        f"- Spearman-Brown: at the median alpha, reaching 0.8 reliability would take "
        f"~{k_for_target:.0f} raters per item; at the actual {mean_depth:.1f}, the aggregated "
        f"label projects to {reliability_at_depth:.2f}.",
        "",
        "![per-label alpha](figures/label_alpha.png)",
        "",
        "Regenerate: `make goemotions` (downloads ~43 MB, not redistributed here).",
        "",
    ]
    (OUT_DIR / "goemotions.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
