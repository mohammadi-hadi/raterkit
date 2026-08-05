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
