# Kappa validation report (pipeline vs. human, NOT a substitute for human<->human)

**Methodology (2026-08-12 revision):** final_label = primary LLM judge's label, unconditionally. Adjudication is DIAGNOSTIC ONLY --
still run and logged whenever the disagreement condition flags a sample, but never overrides the primary judge. See src/memoryir/labeler.py's module docstring and results/kappa_sample/kappa_report_v1_with_adjudication_SUPERSEDED.md for the original (adjudicator-can-override) methodology this supersedes, and why it was changed.

N = 120
Flagged for diagnostic adjudication (did not override): 21/120 samples (17.5%)

**Cohen's kappa: 0.8838**
**Raw agreement: 0.9333** (112/120)

## Confusion matrix (rows=human, columns=pipeline)

| | CARRIES | REFERENCES | CLEAN |
|---|---|---|---|
| **CARRIES** | 50 | 1 | 0 |
| **REFERENCES** | 6 | 6 | 1 |
| **CLEAN** | 0 | 0 | 56 |

## Per-class precision/recall (human labels as ground truth)

```
              precision    recall  f1-score   support

     CARRIES       0.89      0.98      0.93        51
  REFERENCES       0.86      0.46      0.60        13
       CLEAN       0.98      1.00      0.99        56

    accuracy                           0.93       120
   macro avg       0.91      0.81      0.84       120
weighted avg       0.93      0.93      0.92       120

```

## Gate check (docs/labeling_protocol.md)

kappa >= 0.6 -- PASSES the hard gate.

## Real measured token usage (judge.usage_summary(), replaces the earlier template-based estimate)

```
{'calls': 141, 'total_prompt_tokens': 51309, 'total_completion_tokens': 8988, 'avg_prompt_tokens': 363.8936170212766, 'avg_completion_tokens': 63.744680851063826}
```

This is the true measured average across judge + diagnostic-adjudicator calls on this sample -- use this, not an estimate, when projecting full-run labeling cost (see docs/preregistration.md SS4 / the cost discussion this closes the measurement gap for).

## IMPORTANT CAVEAT

This compares the pipeline against ONE human's blind labels. Per docs/labeling_protocol.md's 2026-08-12 correction, this is real human validation (not an AI-vs-AI audit), but it is NOT the same as having a human<->human agreement baseline. A low kappa here could reflect genuine rubric ambiguity (plausible given the multi_hop_setup boundary case found during worked-example construction) rather than a labeler failure specifically -- a second human labeling a subset would be needed to distinguish those two explanations.