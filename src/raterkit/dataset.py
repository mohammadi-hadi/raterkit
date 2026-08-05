"""Indexed view over a list of ratings.

Builds the items x categories count table Krippendorff's alpha needs, plus the
per-rater and pairwise structures the rater-level probes need. All ordering is
deterministic: categories follow the config order when given, otherwise sorted
label order; items and raters are sorted by id.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .schema import Config, Label, Rating


def _category_order(ratings: list[Rating], config: Config) -> list[Label]:
    if config.labels is not None:
        return list(config.labels)
    seen = {r.label for r in ratings}
    if all(isinstance(v, int | float) and not isinstance(v, bool) for v in seen):
        return sorted(seen)
    return sorted(str(v) for v in seen)


@dataclass
class Dataset:
    items: list[str]
    raters: list[str]
    cats: list[Label]
    values: list[float]
    counts: np.ndarray  # items x categories
    ratings: list[Rating]
    config: Config

    @classmethod
    def build(cls, ratings: list[Rating], config: Config) -> Dataset:
        cats = _category_order(ratings, config)
        cat_index = {c: i for i, c in enumerate(cats)}
        items = sorted({r.item_id for r in ratings})
        raters = sorted({r.rater_id for r in ratings})
        item_index = {it: i for i, it in enumerate(items)}
        counts = np.zeros((len(items), len(cats)), dtype=float)
        for r in ratings:
            key = r.label if r.label in cat_index else str(r.label)
            if key not in cat_index:
                raise ValueError(f"label {r.label!r} not in configured labels {cats!r}")
            counts[item_index[r.item_id], cat_index[key]] += 1
        values = [
            float(c) if isinstance(c, int | float) and not isinstance(c, bool) else float(i)
            for i, c in enumerate(cats)
        ]
        return cls(items, raters, cats, values, counts, list(ratings), config)

    # -- derived structures -------------------------------------------------

    def cat_of(self, label: Label) -> int:
        try:
            return self.cats.index(label)
        except ValueError:
            return self.cats.index(str(label))

    def by_item(self) -> dict[str, list[Rating]]:
        out: dict[str, list[Rating]] = {it: [] for it in self.items}
        for r in self.ratings:
            out[r.item_id].append(r)
        return out

    def ratings_of(self, rater_id: str) -> list[Rating]:
        return [r for r in self.ratings if r.rater_id == rater_id]

    def pair_table(self, rater_id: str) -> tuple[np.ndarray, list[int]]:
        """Pair units between one rater and every co-rater.

        Each pair of (rater, other) labels on the same item becomes one
        two-rating unit (a row with two counts). Returns the pair count table
        and, per row, the index of the item it came from, so bootstrap
        resampling can stay item-level.
        """
        rows: list[np.ndarray] = []
        row_items: list[int] = []
        item_index = {it: i for i, it in enumerate(self.items)}
        for item_id, group in self.by_item().items():
            mine = [r for r in group if r.rater_id == rater_id]
            others = [r for r in group if r.rater_id != rater_id]
            for a in mine:
                for b in others:
                    row = np.zeros(len(self.cats))
                    row[self.cat_of(a.label)] += 1
                    row[self.cat_of(b.label)] += 1
                    rows.append(row)
                    row_items.append(item_index[item_id])
        if not rows:
            return np.zeros((0, len(self.cats))), []
        return np.stack(rows), row_items

    def marginal(self, rater_id: str | None = None, exclude: str | None = None) -> np.ndarray:
        """Label distribution of one rater, or of everyone but ``exclude``."""
        vec = np.zeros(len(self.cats))
        for r in self.ratings:
            if rater_id is not None and r.rater_id != rater_id:
                continue
            if exclude is not None and r.rater_id == exclude:
                continue
            vec[self.cat_of(r.label)] += 1
        return vec

    def item_times(self) -> dict[str, float] | None:
        """Median rating time per item; None unless every rating has ``t``."""
        if any(r.t is None for r in self.ratings) or not self.ratings:
            return None
        times: dict[str, list[float]] = {}
        for r in self.ratings:
            assert r.t is not None
            times.setdefault(r.item_id, []).append(r.t)
        return {it: float(np.median(np.array(ts))) for it, ts in times.items()}
