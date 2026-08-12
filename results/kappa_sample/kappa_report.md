# Kappa validation report (pipeline vs. human, NOT a substitute for human<->human)

**Methodology (2026-08-12 revision):** final_label = primary LLM judge's label, unconditionally. Adjudication is DIAGNOSTIC ONLY --
still run and logged whenever the disagreement condition flags a sample, but never overrides the primary judge. See src/memoryir/labeler.py's module docstring and results/kappa_sample/kappa_report_v1_with_adjudication_SUPERSEDED.md for the original (adjudicator-can-override) methodology this supersedes, and why it was changed.

N = 120
Flagged for diagnostic adjudication (did not override): 25/120 samples (20.8%)

**Cohen's kappa: 0.8699**
**Raw agreement: 0.9250** (111/120)

## Confusion matrix (rows=human, columns=pipeline)

| | CARRIES | REFERENCES | CLEAN |
|---|---|---|---|
| **CARRIES** | 49 | 2 | 0 |
| **REFERENCES** | 7 | 6 | 0 |
| **CLEAN** | 0 | 0 | 56 |

## Per-class precision/recall (human labels as ground truth)

```
              precision    recall  f1-score   support

     CARRIES       0.88      0.96      0.92        51
  REFERENCES       0.75      0.46      0.57        13
       CLEAN       1.00      1.00      1.00        56

    accuracy                           0.93       120
   macro avg       0.88      0.81      0.83       120
weighted avg       0.92      0.93      0.92       120

```

## Gate check (docs/labeling_protocol.md)

kappa >= 0.6 -- PASSES the hard gate.

## IMPORTANT CAVEAT

This compares the pipeline against ONE human's blind labels. Per docs/labeling_protocol.md's 2026-08-12 correction, this is real human validation (not an AI-vs-AI audit), but it is NOT the same as having a human<->human agreement baseline. A low kappa here could reflect genuine rubric ambiguity (plausible given the multi_hop_setup boundary case found during worked-example construction) rather than a labeler failure specifically -- a second human labeling a subset would be needed to distinguish those two explanations.