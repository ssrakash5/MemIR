# Kappa validation report (pipeline vs. human, NOT a substitute for human<->human)

N = 120
Adjudication triggered on 22/120 samples (18.3%)

**Cohen's kappa: 0.8103**
**Raw agreement: 0.8917** (107/120)

## Confusion matrix (rows=human, columns=pipeline)

| | CARRIES | REFERENCES | CLEAN |
|---|---|---|---|
| **CARRIES** | 48 | 3 | 0 |
| **REFERENCES** | 9 | 3 | 1 |
| **CLEAN** | 0 | 0 | 56 |

## Per-class precision/recall (human labels as ground truth)

```
              precision    recall  f1-score   support

     CARRIES       0.84      0.94      0.89        51
  REFERENCES       0.50      0.23      0.32        13
       CLEAN       0.98      1.00      0.99        56

    accuracy                           0.89       120
   macro avg       0.77      0.72      0.73       120
weighted avg       0.87      0.89      0.87       120

```

## Gate check (docs/labeling_protocol.md)

kappa >= 0.6 -- PASSES the hard gate.

## IMPORTANT CAVEAT

This compares the pipeline against ONE human's blind labels. Per docs/labeling_protocol.md's 2026-08-12 correction, this is real human validation (not an AI-vs-AI audit), but it is NOT the same as having a human<->human agreement baseline. A low kappa here could reflect genuine rubric ambiguity (plausible given the multi_hop_setup boundary case found during worked-example construction) rather than a labeler failure specifically -- a second human labeling a subset would be needed to distinguish those two explanations.