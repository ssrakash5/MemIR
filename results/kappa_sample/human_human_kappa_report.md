# Human<->human kappa baseline

Independent blind annotation of the same 120-row sample by two human annotators, same rubric (`docs/labeling_protocol.md`), neither shown the other's labels or the answer key before submitting (see `README_second_annotator.md`).

N = 120

**Cohen's kappa: 0.9277**
**Raw agreement: 0.9583** (115/120)

## Confusion matrix (rows=annotator 1, columns=annotator 2)

| | CARRIES | REFERENCES | CLEAN |
|---|---|---|---|
| **CARRIES** | 51 | 0 | 0 |
| **REFERENCES** | 5 | 8 | 0 |
| **CLEAN** | 0 | 0 | 56 |

## Per-class agreement (annotator 1 as reference)

```
              precision    recall  f1-score   support

     CARRIES       0.91      1.00      0.95        51
  REFERENCES       1.00      0.62      0.76        13
       CLEAN       1.00      1.00      1.00        56

    accuracy                           0.96       120
   macro avg       0.97      0.87      0.91       120
weighted avg       0.96      0.96      0.95       120

```

## Disagreements

| sample_id | annotator_1 | annotator_2 |
|---|---|---|
| S005 | REFERENCES | CARRIES |
| S056 | REFERENCES | CARRIES |
| S061 | REFERENCES | CARRIES |
| S087 | REFERENCES | CARRIES |
| S117 | REFERENCES | CARRIES |

## Comparison to pipeline-vs-human1 (kappa_report.md)

This baseline exists to distinguish genuine rubric ambiguity from labeler failure in the pipeline-vs-human comparison (see that report's IMPORTANT CAVEAT). Compare this kappa and the REFERENCES-class agreement specifically against the pipeline's REFERENCES precision/recall reported there.