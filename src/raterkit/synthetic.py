"""Synthetic annotation projects with implantable defects.

Each defect is a dial: a spammer count, a leaning rater, a competence drift, a
gold error rate. The tests turn one dial at a time and require the matching
probe — and only it — to move.

The rater model: each item has a latent true label. On a normal item a rater
answers correctly with probability ``competence`` and errs uniformly
otherwise. A ``hard_share`` fraction of items are genuinely ambiguous — every
rater sees a coin flip between the truth and one fixed alternative — which is
what lets a *leaning* rater diverge in label distribution without disagreeing
more than anyone else does: on hard items the leaner always takes the same
side of the coin, an equally defensible answer with a skewed marginal.
"""

from __future__ import annotations

import numpy as np

from .schema import Config, Gold, Rating


def _hard_options(truth: int) -> tuple[int, int]:
    """The two defensible labels on a hard item: the truth and the 0-side alternative."""
    return (truth, 0 if truth != 0 else 1)


def simulate(
    n_items: int = 300,
    n_raters: int = 10,
    per_item: int = 3,
    n_cats: int = 4,
    seed: int = 0,
    competence: float = 0.9,
    prevalence: list[float] | None = None,
    spammers: int = 0,
    spammer_load: float = 1.0,
    leaners: int = 0,
    hard_share: float = 0.0,
    drift: float = 0.0,
    dup_across_splits: int = 0,
    gold_error: float = 0.0,
    with_gold: bool = True,
    with_text: bool = True,
    with_split: bool = True,
) -> tuple[list[Rating], list[Gold] | None, Config]:
    """Generate one annotation project.

    Rater roles by index: raters ``0..spammers-1`` label uniformly at random
    (rating ``spammer_load`` of the items they are assigned); the next
    ``leaners`` raters always take the 0-side option on hard items. ``drift``
    is the competence every normal rater loses linearly from the first item to
    the last. ``dup_across_splits`` test items receive the text of a train
    item; ``gold_error`` is the fraction of gold labels flipped to a random
    wrong category.
    """
    rng = np.random.Generator(np.random.PCG64(seed))
    p = np.array(prevalence if prevalence is not None else [1.0 / n_cats] * n_cats)
    p = p / p.sum()
    truth = rng.choice(n_cats, size=n_items, p=p)
    hard = rng.random(n_items) < hard_share

    spammer_ids = set(range(spammers))
    leaner_ids = set(range(spammers, spammers + leaners))

    texts = [f"item text number {i}" for i in range(n_items)]
    splits = ["train" if i % 2 == 0 else "test" for i in range(n_items)]
    test_items = [i for i in range(n_items) if splits[i] == "test"]
    train_items = [i for i in range(n_items) if splits[i] == "train"]
    for d in range(min(dup_across_splits, len(test_items), len(train_items))):
        texts[test_items[d]] = texts[train_items[d]]

    ratings: list[Rating] = []
    for i in range(n_items):
        frac = i / (n_items - 1) if n_items > 1 else 0.0
        chosen = rng.choice(n_raters, size=min(per_item, n_raters), replace=False)
        for r in chosen:
            if r in spammer_ids:
                if rng.random() > spammer_load:
                    continue
                label = int(rng.integers(0, n_cats))
            elif hard[i]:
                a, b = _hard_options(int(truth[i]))
                if r in leaner_ids:
                    label = min(a, b)
                else:
                    label = a if rng.random() < 0.5 else b
            else:
                skill = competence - drift * frac
                if rng.random() < skill:
                    label = int(truth[i])
                else:
                    others = [c for c in range(n_cats) if c != truth[i]]
                    label = int(others[rng.integers(0, len(others))])
            ratings.append(
                Rating(
                    item_id=f"i{i:05d}",
                    rater_id=f"r{r:02d}",
                    label=label,
                    t=float(i) + 0.1 * float(r) / n_raters,
                    split=splits[i] if with_split else None,
                    text=texts[i] if with_text else None,
                )
            )

    gold: list[Gold] | None = None
    if with_gold:
        gold = []
        flip = rng.random(n_items) < gold_error
        for i in range(n_items):
            label = int(truth[i])
            if flip[i]:
                others = [c for c in range(n_cats) if c != label]
                label = int(others[rng.integers(0, len(others))])
            gold.append(Gold(item_id=f"i{i:05d}", label=label))

    config = Config(level="nominal", labels=list(range(n_cats)))
    return ratings, gold, config
