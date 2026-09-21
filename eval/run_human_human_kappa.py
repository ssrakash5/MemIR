"""Compute the human<->human agreement baseline for the labeling rubric.

This is the follow-up analysis step referenced in kappa_report.md's
IMPORTANT CAVEAT and results/kappa_sample/README_second_annotator.md:
compares the first annotator's blind labels against a second, independent
annotator's blind labels on the same 120-row sample.

Usage:
    python eval/run_human_human_kappa.py

Reads:
    results/kappa_sample/blind_annotation_sheet_completed.csv (annotator 1)
    results/kappa_sample/blind_annotation_sheet_annotator2.csv (annotator 2)

Writes:
    results/kappa_sample/human_human_kappa_report.md
"""
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from sklearn.metrics import classification_report, cohen_kappa_score, confusion_matrix

SAMPLE_DIR = REPO_ROOT / "results" / "kappa_sample"
LABELS = ["CARRIES", "REFERENCES", "CLEAN"]


def load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return {r["sample_id"]: r["your_label"].strip().upper() for r in csv.DictReader(f)}


def main() -> None:
    a1 = load(SAMPLE_DIR / "blind_annotation_sheet_completed.csv")
    a2 = load(SAMPLE_DIR / "blind_annotation_sheet_annotator2.csv")

    if set(a1) != set(a2):
        raise SystemExit(
            f"sample_id mismatch between annotators: "
            f"only in a1={set(a1)-set(a2)}, only in a2={set(a2)-set(a1)}"
        )

    ids = sorted(a1)
    labels1 = [a1[i] for i in ids]
    labels2 = [a2[i] for i in ids]

    bad = [l for l in labels1 + labels2 if l not in LABELS]
    if bad:
        raise SystemExit(f"unexpected label values: {set(bad)}")

    kappa = cohen_kappa_score(labels1, labels2, labels=LABELS)
    raw_agreement = sum(x == y for x, y in zip(labels1, labels2)) / len(ids)
    cm = confusion_matrix(labels1, labels2, labels=LABELS)
    report = classification_report(labels1, labels2, labels=LABELS, zero_division=0)

    disagreements = [
        (sid, labels1[i], labels2[i]) for i, sid in enumerate(ids) if labels1[i] != labels2[i]
    ]

    report_lines = [
        "# Human<->human kappa baseline",
        "",
        "Independent blind annotation of the same 120-row sample by two human "
        "annotators, same rubric (`docs/labeling_protocol.md`), neither shown "
        "the other's labels or the answer key before submitting "
        "(see `README_second_annotator.md`).",
        "",
        f"N = {len(ids)}",
        "",
        f"**Cohen's kappa: {kappa:.4f}**",
        f"**Raw agreement: {raw_agreement:.4f}** "
        f"({sum(x==y for x,y in zip(labels1,labels2))}/{len(ids)})",
        "",
        "## Confusion matrix (rows=annotator 1, columns=annotator 2)",
        "",
        "| | " + " | ".join(LABELS) + " |",
        "|---|" + "---|" * len(LABELS),
    ]
    for i, label in enumerate(LABELS):
        report_lines.append("| **" + label + "** | " + " | ".join(str(x) for x in cm[i]) + " |")
    report_lines += [
        "",
        "## Per-class agreement (annotator 1 as reference)",
        "",
        "```",
        report,
        "```",
        "",
        "## Disagreements",
        "",
        "| sample_id | annotator_1 | annotator_2 |",
        "|---|---|---|",
    ]
    for sid, l1, l2 in disagreements:
        report_lines.append(f"| {sid} | {l1} | {l2} |")
    report_lines += [
        "",
        "## Comparison to pipeline-vs-human1 (kappa_report.md)",
        "",
        "This baseline exists to distinguish genuine rubric ambiguity from "
        "labeler failure in the pipeline-vs-human comparison (see that "
        "report's IMPORTANT CAVEAT). Compare this kappa and the "
        "REFERENCES-class agreement specifically against the pipeline's "
        "REFERENCES precision/recall reported there.",
    ]

    report_path = SAMPLE_DIR / "human_human_kappa_report.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Cohen's kappa (human1 vs human2): {kappa:.4f}")
    print(f"Raw agreement: {raw_agreement:.4f}")
    print(f"Disagreements: {len(disagreements)}/{len(ids)}")
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
