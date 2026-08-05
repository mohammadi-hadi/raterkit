# raterkit demo

Eight synthetic annotation projects, seven implanted defects. Each audit
must flag exactly the defect its row implants — and nothing on the clean row.

| project | implanted defect | alpha | rogue | biased | drift gap | leaks | stale gold | flags |
|---|---|---|---|---|---|---|---|---|
| clean | nothing | 0.80 | 0 | 0 | +0.00 | 0 | 0.0% | none |
| careless-crowd | every rater at 55% accuracy | **0.18** | 0 | 0 | -0.02 | 0 | 0.7% | reliability |
| one-spammer | one rater answers uniformly at random | 0.72 | **1** | 0 | +0.05 | 0 | 0.0% | rogue raters |
| leaning-rater | one rater always takes the same side of ambiguous items | 0.65 | 0 | **1** | +0.05 | 0 | - | rater bias |
| tiring-crowd | competence decays 0.97 to 0.73 over the queue | 0.64 | 0 | 0 | **+0.25** | 0 | 0.0% | drift |
| leaky-split | 12 test items duplicate a train item's text | 0.80 | 0 | 0 | +0.00 | **12** | 0.0% | split leakage |
| stale-gold | 8% of gold labels are wrong | 0.80 | 0 | 0 | +0.00 | 0 | **6.7%** | stale gold |
| easy-but-skewed | 94% of items are one class; raters 90% accurate | **0.34** | 0 | 0 | +0.12 | 0 | 0.0% | reliability |

## clean (seed 0)

Implanted: nothing.

**No flags.**

| probe | value | 95% CI | innocent band | flag |
|---|---|---|---|---|
| reliability | 0.796 alpha | (0.751, 0.835) | alpha at or above 0.667 |  |
| rogue raters | 0.000 raters | - | no rater credibly below the pool |  |
| rater bias | 0.000 raters | - | every rater within 0.10 total variation of the rest |  |
| drift | 0.003 alpha gap | (-0.084, 0.093) | early-late alpha gap within ±0.10 |  |
| split leakage | 0.000 texts | - | no duplicated text spanning splits |  |
| stale gold | 0.000 share | (0.000, 0.000) | at most 2% of gold contradicted by a unanimous crowd |  |
| ambiguity | 0.220 share | (0.177, 0.267) | descriptive |  |
| prevalence | 0.312 share | - | descriptive |  |
| rating depth | 3.000 ratings/item | - | descriptive |  |

- **reliability** (n=900): Krippendorff's alpha (nominal) = 0.796 over 900 pairable ratings; the conventional floor is 0.667.
- **rogue raters** (n=10): 0 of 10 raters agree with the rest credibly worse than the pool agrees with itself. Lowest rater-vs-rest alpha: 0.740 (r08).
- **rater bias** (n=10): 0 of 10 raters use the labels credibly differently from the rest (total variation distance beyond 0.1). Largest divergence: 0.09 (r06).
- **drift** (n=300): alpha on the earlier half of items minus the later half = +0.003; a credible gap means the guidelines meant something different over time.
- **split leakage** (n=300): 0 duplicated texts span more than one split (0 items are duplicates of another item). Any leak means the test split is partly memorized.
- **stale gold** (n=300): 0.0% of 300 double-rated gold items are contradicted by a unanimous crowd; those golds are likely wrong or outdated.
- **ambiguity** (n=300): 22.0% of 300 multi-rated items are contested (at least one dissenting rating) — where disagreement lives, and where a single 'true' label may not exist. Descriptive; never flags.
- **prevalence** (n=900): most common label covers 31.2% of ratings; raw agreement 84.8% vs alpha 0.796. When these disagree, the skew — not the raters — is doing the agreeing. Descriptive; never flags.
- **rating depth** (n=300): mean 3.0 ratings per item, 0% single-rated. Spearman-Brown: majority-of-k labels need ~1.0 raters per item for 80% reliability at this alpha. Descriptive; never flags.

## careless-crowd (seed 0)

Implanted: every rater at 55% accuracy.

**1 flag(s):** reliability

| probe | value | 95% CI | innocent band | flag |
|---|---|---|---|---|
| reliability | 0.178 alpha | (0.130, 0.225) | alpha at or above 0.667 | **yes** |
| rogue raters | 0.000 raters | - | no rater credibly below the pool |  |
| rater bias | 0.000 raters | - | every rater within 0.10 total variation of the rest |  |
| drift | -0.016 alpha gap | (-0.107, 0.078) | early-late alpha gap within ±0.10 |  |
| split leakage | 0.000 texts | - | no duplicated text spanning splits |  |
| stale gold | 0.007 share | (0.000, 0.017) | at most 2% of gold contradicted by a unanimous crowd |  |
| ambiguity | 0.823 share | (0.780, 0.867) | descriptive |  |
| prevalence | 0.272 share | - | descriptive |  |
| rating depth | 3.000 ratings/item | - | descriptive |  |

- **reliability** (n=900): Krippendorff's alpha (nominal) = 0.178 over 900 pairable ratings; the conventional floor is 0.667.
- **rogue raters** (n=10): 0 of 10 raters agree with the rest credibly worse than the pool agrees with itself. Lowest rater-vs-rest alpha: 0.108 (r09).
- **rater bias** (n=10): 0 of 10 raters use the labels credibly differently from the rest (total variation distance beyond 0.1). Largest divergence: 0.14 (r05).
- **drift** (n=300): alpha on the earlier half of items minus the later half = -0.016; a credible gap means the guidelines meant something different over time.
- **split leakage** (n=300): 0 duplicated texts span more than one split (0 items are duplicates of another item). Any leak means the test split is partly memorized.
- **stale gold** (n=300): 0.7% of 300 double-rated gold items are contradicted by a unanimous crowd; those golds are likely wrong or outdated.
- **ambiguity** (n=300): 82.3% of 300 multi-rated items are contested (at least one dissenting rating) — where disagreement lives, and where a single 'true' label may not exist. Descriptive; never flags.
- **prevalence** (n=900): most common label covers 27.2% of ratings; raw agreement 38.3% vs alpha 0.178. When these disagree, the skew — not the raters — is doing the agreeing. Descriptive; never flags.
- **rating depth** (n=300): mean 3.0 ratings per item, 0% single-rated. Spearman-Brown: majority-of-k labels need ~18.5 raters per item for 80% reliability at this alpha. Descriptive; never flags.

## one-spammer (seed 0)

Implanted: one rater answers uniformly at random.

**1 flag(s):** rogue raters

| probe | value | 95% CI | innocent band | flag |
|---|---|---|---|---|
| reliability | 0.717 alpha | (0.669, 0.768) | alpha at or above 0.667 |  |
| rogue raters | 1.000 raters | - | no rater credibly below the pool | **yes** |
| rater bias | 0.000 raters | - | every rater within 0.10 total variation of the rest |  |
| drift | 0.055 alpha gap | (-0.050, 0.151) | early-late alpha gap within ±0.10 |  |
| split leakage | 0.000 texts | - | no duplicated text spanning splits |  |
| stale gold | 0.000 share | (0.000, 0.000) | at most 2% of gold contradicted by a unanimous crowd |  |
| ambiguity | 0.293 share | (0.243, 0.343) | descriptive |  |
| prevalence | 0.303 share | - | descriptive |  |
| rating depth | 2.937 ratings/item | - | descriptive |  |

- **reliability** (n=881): Krippendorff's alpha (nominal) = 0.717 over 881 pairable ratings; the conventional floor is 0.667.
- **rogue raters** (n=12): 1 of 12 raters agree with the rest credibly worse than the pool agrees with itself: r00. Lowest rater-vs-rest alpha: 0.031 (r00).
- **rater bias** (n=12): 0 of 12 raters use the labels credibly differently from the rest (total variation distance beyond 0.1). Largest divergence: 0.16 (r06).
- **drift** (n=300): alpha on the earlier half of items minus the later half = +0.055; a credible gap means the guidelines meant something different over time.
- **split leakage** (n=300): 0 duplicated texts span more than one split (0 items are duplicates of another item). Any leak means the test split is partly memorized.
- **stale gold** (n=300): 0.0% of 300 double-rated gold items are contradicted by a unanimous crowd; those golds are likely wrong or outdated.
- **ambiguity** (n=300): 29.3% of 300 multi-rated items are contested (at least one dissenting rating) — where disagreement lives, and where a single 'true' label may not exist. Descriptive; never flags.
- **prevalence** (n=881): most common label covers 30.3% of ratings; raw agreement 78.9% vs alpha 0.717. When these disagree, the skew — not the raters — is doing the agreeing. Descriptive; never flags.
- **rating depth** (n=300): mean 2.9 ratings per item, 0% single-rated. Spearman-Brown: majority-of-k labels need ~1.6 raters per item for 80% reliability at this alpha. Descriptive; never flags.

## leaning-rater (seed 0)

Implanted: one rater always takes the same side of ambiguous items.

**1 flag(s):** rater bias

| probe | value | 95% CI | innocent band | flag |
|---|---|---|---|---|
| reliability | 0.648 alpha | (0.600, 0.692) | alpha at or above 0.667 |  |
| rogue raters | 0.000 raters | - | no rater credibly below the pool |  |
| rater bias | 1.000 raters | - | every rater within 0.10 total variation of the rest | **yes** |
| drift | 0.053 alpha gap | (-0.036, 0.147) | early-late alpha gap within ±0.10 |  |
| split leakage | 0.000 texts | - | no duplicated text spanning splits |  |
| ambiguity | 0.388 share | (0.340, 0.440) | descriptive |  |
| prevalence | 0.352 share | - | descriptive |  |
| rating depth | 3.000 ratings/item | - | descriptive |  |

- **reliability** (n=1200): Krippendorff's alpha (nominal) = 0.648 over 1200 pairable ratings; the conventional floor is 0.667.
- **rogue raters** (n=8): 0 of 8 raters agree with the rest credibly worse than the pool agrees with itself. Lowest rater-vs-rest alpha: 0.597 (r00).
- **rater bias** (n=8): 1 of 8 raters use the labels credibly differently from the rest (total variation distance beyond 0.1): r00. Largest divergence: 0.22 (r00).
- **drift** (n=400): alpha on the earlier half of items minus the later half = +0.053; a credible gap means the guidelines meant something different over time.
- **split leakage** (n=400): 0 duplicated texts span more than one split (0 items are duplicates of another item). Any leak means the test split is partly memorized.
- **ambiguity** (n=400): 38.8% of 400 multi-rated items are contested (at least one dissenting rating) — where disagreement lives, and where a single 'true' label may not exist. Descriptive; never flags.
- **prevalence** (n=1200): most common label covers 35.2% of ratings; raw agreement 74.1% vs alpha 0.648. When these disagree, the skew — not the raters — is doing the agreeing. Descriptive; never flags.
- **rating depth** (n=400): mean 3.0 ratings per item, 0% single-rated. Spearman-Brown: majority-of-k labels need ~2.2 raters per item for 80% reliability at this alpha. Descriptive; never flags.

## Skipped checks

- **stale gold**: needs a gold file; pass --gold gold.jsonl

## tiring-crowd (seed 0)

Implanted: competence decays 0.97 to 0.73 over the queue.

**1 flag(s):** drift

| probe | value | 95% CI | innocent band | flag |
|---|---|---|---|---|
| reliability | 0.642 alpha | (0.589, 0.691) | alpha at or above 0.667 |  |
| rogue raters | 0.000 raters | - | no rater credibly below the pool |  |
| rater bias | 0.000 raters | - | every rater within 0.10 total variation of the rest |  |
| drift | 0.248 alpha gap | (0.150, 0.350) | early-late alpha gap within ±0.10 | **yes** |
| split leakage | 0.000 texts | - | no duplicated text spanning splits |  |
| stale gold | 0.000 share | (0.000, 0.000) | at most 2% of gold contradicted by a unanimous crowd |  |
| ambiguity | 0.380 share | (0.327, 0.433) | descriptive |  |
| prevalence | 0.302 share | - | descriptive |  |
| rating depth | 3.000 ratings/item | - | descriptive |  |

- **reliability** (n=900): Krippendorff's alpha (nominal) = 0.642 over 900 pairable ratings; the conventional floor is 0.667.
- **rogue raters** (n=10): 0 of 10 raters agree with the rest credibly worse than the pool agrees with itself. Lowest rater-vs-rest alpha: 0.558 (r00).
- **rater bias** (n=10): 0 of 10 raters use the labels credibly differently from the rest (total variation distance beyond 0.1). Largest divergence: 0.10 (r09).
- **drift** (n=300): alpha on the earlier half of items minus the later half = +0.248; a credible gap means the guidelines meant something different over time.
- **split leakage** (n=300): 0 duplicated texts span more than one split (0 items are duplicates of another item). Any leak means the test split is partly memorized.
- **stale gold** (n=300): 0.0% of 300 double-rated gold items are contradicted by a unanimous crowd; those golds are likely wrong or outdated.
- **ambiguity** (n=300): 38.0% of 300 multi-rated items are contested (at least one dissenting rating) — where disagreement lives, and where a single 'true' label may not exist. Descriptive; never flags.
- **prevalence** (n=900): most common label covers 30.2% of ratings; raw agreement 73.2% vs alpha 0.642. When these disagree, the skew — not the raters — is doing the agreeing. Descriptive; never flags.
- **rating depth** (n=300): mean 3.0 ratings per item, 0% single-rated. Spearman-Brown: majority-of-k labels need ~2.2 raters per item for 80% reliability at this alpha. Descriptive; never flags.

## leaky-split (seed 0)

Implanted: 12 test items duplicate a train item's text.

**1 flag(s):** split leakage

| probe | value | 95% CI | innocent band | flag |
|---|---|---|---|---|
| reliability | 0.796 alpha | (0.751, 0.835) | alpha at or above 0.667 |  |
| rogue raters | 0.000 raters | - | no rater credibly below the pool |  |
| rater bias | 0.000 raters | - | every rater within 0.10 total variation of the rest |  |
| drift | 0.003 alpha gap | (-0.084, 0.093) | early-late alpha gap within ±0.10 |  |
| split leakage | 12.000 texts | - | no duplicated text spanning splits | **yes** |
| stale gold | 0.000 share | (0.000, 0.000) | at most 2% of gold contradicted by a unanimous crowd |  |
| ambiguity | 0.220 share | (0.177, 0.267) | descriptive |  |
| prevalence | 0.312 share | - | descriptive |  |
| rating depth | 3.000 ratings/item | - | descriptive |  |

- **reliability** (n=900): Krippendorff's alpha (nominal) = 0.796 over 900 pairable ratings; the conventional floor is 0.667.
- **rogue raters** (n=10): 0 of 10 raters agree with the rest credibly worse than the pool agrees with itself. Lowest rater-vs-rest alpha: 0.740 (r08).
- **rater bias** (n=10): 0 of 10 raters use the labels credibly differently from the rest (total variation distance beyond 0.1). Largest divergence: 0.09 (r06).
- **drift** (n=300): alpha on the earlier half of items minus the later half = +0.003; a credible gap means the guidelines meant something different over time.
- **split leakage** (n=300): 12 duplicated texts span more than one split (24 items are duplicates of another item). Any leak means the test split is partly memorized.
- **stale gold** (n=300): 0.0% of 300 double-rated gold items are contradicted by a unanimous crowd; those golds are likely wrong or outdated.
- **ambiguity** (n=300): 22.0% of 300 multi-rated items are contested (at least one dissenting rating) — where disagreement lives, and where a single 'true' label may not exist. Descriptive; never flags.
- **prevalence** (n=900): most common label covers 31.2% of ratings; raw agreement 84.8% vs alpha 0.796. When these disagree, the skew — not the raters — is doing the agreeing. Descriptive; never flags.
- **rating depth** (n=300): mean 3.0 ratings per item, 0% single-rated. Spearman-Brown: majority-of-k labels need ~1.0 raters per item for 80% reliability at this alpha. Descriptive; never flags.

## stale-gold (seed 0)

Implanted: 8% of gold labels are wrong.

**1 flag(s):** stale gold

| probe | value | 95% CI | innocent band | flag |
|---|---|---|---|---|
| reliability | 0.796 alpha | (0.751, 0.835) | alpha at or above 0.667 |  |
| rogue raters | 0.000 raters | - | no rater credibly below the pool |  |
| rater bias | 0.000 raters | - | every rater within 0.10 total variation of the rest |  |
| drift | 0.003 alpha gap | (-0.084, 0.093) | early-late alpha gap within ±0.10 |  |
| split leakage | 0.000 texts | - | no duplicated text spanning splits |  |
| stale gold | 0.067 share | (0.040, 0.097) | at most 2% of gold contradicted by a unanimous crowd | **yes** |
| ambiguity | 0.220 share | (0.177, 0.267) | descriptive |  |
| prevalence | 0.312 share | - | descriptive |  |
| rating depth | 3.000 ratings/item | - | descriptive |  |

- **reliability** (n=900): Krippendorff's alpha (nominal) = 0.796 over 900 pairable ratings; the conventional floor is 0.667.
- **rogue raters** (n=10): 0 of 10 raters agree with the rest credibly worse than the pool agrees with itself. Lowest rater-vs-rest alpha: 0.740 (r08).
- **rater bias** (n=10): 0 of 10 raters use the labels credibly differently from the rest (total variation distance beyond 0.1). Largest divergence: 0.09 (r06).
- **drift** (n=300): alpha on the earlier half of items minus the later half = +0.003; a credible gap means the guidelines meant something different over time.
- **split leakage** (n=300): 0 duplicated texts span more than one split (0 items are duplicates of another item). Any leak means the test split is partly memorized.
- **stale gold** (n=300): 6.7% of 300 double-rated gold items are contradicted by a unanimous crowd; those golds are likely wrong or outdated.
- **ambiguity** (n=300): 22.0% of 300 multi-rated items are contested (at least one dissenting rating) — where disagreement lives, and where a single 'true' label may not exist. Descriptive; never flags.
- **prevalence** (n=900): most common label covers 31.2% of ratings; raw agreement 84.8% vs alpha 0.796. When these disagree, the skew — not the raters — is doing the agreeing. Descriptive; never flags.
- **rating depth** (n=300): mean 3.0 ratings per item, 0% single-rated. Spearman-Brown: majority-of-k labels need ~1.0 raters per item for 80% reliability at this alpha. Descriptive; never flags.

## easy-but-skewed (seed 0)

Implanted: 94% of items are one class; raters 90% accurate.

**1 flag(s):** reliability

| probe | value | 95% CI | innocent band | flag |
|---|---|---|---|---|
| reliability | 0.340 alpha | (0.238, 0.440) | alpha at or above 0.667 | **yes** |
| rogue raters | 0.000 raters | - | no rater credibly below the pool |  |
| rater bias | 0.000 raters | - | every rater within 0.10 total variation of the rest |  |
| drift | 0.121 alpha gap | (-0.090, 0.328) | early-late alpha gap within ±0.10 |  |
| split leakage | 0.000 texts | - | no duplicated text spanning splits |  |
| stale gold | 0.000 share | (0.000, 0.000) | at most 2% of gold contradicted by a unanimous crowd |  |
| ambiguity | 0.273 share | (0.220, 0.323) | descriptive |  |
| prevalence | 0.838 share | - | descriptive |  |
| rating depth | 3.000 ratings/item | - | descriptive |  |

- **reliability** (n=900): Krippendorff's alpha (nominal) = 0.340 over 900 pairable ratings; the conventional floor is 0.667.
- **rogue raters** (n=10): 0 of 10 raters agree with the rest credibly worse than the pool agrees with itself. Lowest rater-vs-rest alpha: 0.151 (r09).
- **rater bias** (n=10): 0 of 10 raters use the labels credibly differently from the rest (total variation distance beyond 0.1). Largest divergence: 0.11 (r08).
- **drift** (n=300): alpha on the earlier half of items minus the later half = +0.121; a credible gap means the guidelines meant something different over time.
- **split leakage** (n=300): 0 duplicated texts span more than one split (0 items are duplicates of another item). Any leak means the test split is partly memorized.
- **stale gold** (n=300): 0.0% of 300 double-rated gold items are contradicted by a unanimous crowd; those golds are likely wrong or outdated.
- **ambiguity** (n=300): 27.3% of 300 multi-rated items are contested (at least one dissenting rating) — where disagreement lives, and where a single 'true' label may not exist. Descriptive; never flags.
- **prevalence** (n=900): most common label covers 83.8% of ratings; raw agreement 80.9% vs alpha 0.340. When these disagree, the skew — not the raters — is doing the agreeing. Descriptive; never flags.
- **rating depth** (n=300): mean 3.0 ratings per item, 0% single-rated. Spearman-Brown: majority-of-k labels need ~7.8 raters per item for 80% reliability at this alpha. Descriptive; never flags.

