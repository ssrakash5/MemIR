"""Run the automated labeler pipeline against the kappa-validation sample
and compute agreement against the human's completed blind labels.

Usage:
    python eval/run_kappa_validation.py

Reads:
    results/kappa_sample/blind_annotation_sheet.csv (sample_id, semantic_target, candidate_memory)
    results/kappa_sample/blind_annotation_sheet_completed.csv (+ your_label, human-filled)

Writes:
    results/kappa_sample/pipeline_labels.csv (per-sample pipeline output + full trace)
    results/kappa_sample/kappa_report.md (Cohen's kappa, agreement, confusion matrix, per-class P/R)
"""
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from sklearn.metrics import classification_report, cohen_kappa_score, confusion_matrix

from memoryir.labeler import LLMJudge, NLIVerifier, label_one

SAMPLE_DIR = REPO_ROOT / "results" / "kappa_sample"
LABELS = ["CARRIES", "REFERENCES", "CLEAN"]


def main() -> None:
    with open(SAMPLE_DIR / "blind_annotation_sheet_completed.csv", encoding="utf-8") as f:
        human_rows = {r["sample_id"]: r for r in csv.DictReader(f)}

    missing = [sid for sid, r in human_rows.items() if not r["your_label"].strip()]
    if missing:
        raise SystemExit(f"{len(missing)} samples still unlabeled by human: {missing[:5]}...")

    print(f"Loaded {len(human_rows)} human-labeled samples.")
    print("Loading LLM judge + NLI verifier...")
    judge = LLMJudge()
    nli = NLIVerifier()

    pipeline_rows = []
    human_labels, pipeline_labels = [], []
    n_adjudicated = 0

    for i, (sid, row) in enumerate(sorted(human_rows.items()), start=1):
        result = label_one(
            semantic_target=row["semantic_target"],
            candidate=row["candidate_memory"],
            judge=judge,
            nli=nli,
        )
        human_label = row["your_label"].strip().upper()
        pipeline_rows.append(
            {
                "sample_id": sid,
                "human_label": human_label,
                "pipeline_final_label": result.final_label,
                "llm_label": result.llm_label,
                "nli_relation": result.nli_relation,
                "nli_score": f"{result.nli_score:.3f}",
                "adjudicated": result.adjudicated,
                "adjudicator_label": result.adjudicator_label or "",
                "llm_evidence_span": result.llm_evidence_span,
                "llm_reason": result.llm_reason,
                "adjudicator_reason": result.adjudicator_reason or "",
                "agree": human_label == result.final_label,
            }
        )
        human_labels.append(human_label)
        pipeline_labels.append(result.final_label)
        if result.adjudicated:
            n_adjudicated += 1
        print(f"  [{i}/{len(human_rows)}] {sid}: human={human_label} pipeline={result.final_label} "
              f"{'<-- DISAGREE' if human_label != result.final_label else ''}")

    with open(SAMPLE_DIR / "pipeline_labels.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(pipeline_rows[0].keys()))
        w.writeheader()
        w.writerows(pipeline_rows)

    kappa = cohen_kappa_score(human_labels, pipeline_labels, labels=LABELS)
    raw_agreement = sum(h == p for h, p in zip(human_labels, pipeline_labels)) / len(human_labels)
    cm = confusion_matrix(human_labels, pipeline_labels, labels=LABELS)
    report = classification_report(
        human_labels, pipeline_labels, labels=LABELS, zero_division=0
    )

    report_lines = [
        "# Kappa validation report (pipeline vs. human, NOT a substitute for human<->human)",
        "",
        "**Methodology (2026-08-12 revision):** final_label = primary LLM "
        "judge's label, unconditionally. Adjudication is DIAGNOSTIC ONLY --",
        "still run and logged whenever the disagreement condition flags a "
        "sample, but never overrides the primary judge. See "
        "src/memoryir/labeler.py's module docstring and "
        "results/kappa_sample/kappa_report_v1_with_adjudication_SUPERSEDED.md "
        "for the original (adjudicator-can-override) methodology this "
        "supersedes, and why it was changed.",
        "",
        f"N = {len(human_labels)}",
        f"Flagged for diagnostic adjudication (did not override): "
        f"{n_adjudicated}/{len(human_labels)} samples "
        f"({100*n_adjudicated/len(human_labels):.1f}%)",
        "",
        f"**Cohen's kappa: {kappa:.4f}**",
        f"**Raw agreement: {raw_agreement:.4f}** ({sum(h==p for h,p in zip(human_labels,pipeline_labels))}/{len(human_labels)})",
        "",
        "## Confusion matrix (rows=human, columns=pipeline)",
        "",
        "| | " + " | ".join(LABELS) + " |",
        "|---|" + "---|" * len(LABELS),
    ]
    for i, label in enumerate(LABELS):
        report_lines.append("| **" + label + "** | " + " | ".join(str(x) for x in cm[i]) + " |")
    report_lines += [
        "",
        "## Per-class precision/recall (human labels as ground truth)",
        "",
        "```",
        report,
        "```",
        "",
        "## Gate check (docs/labeling_protocol.md)",
        "",
        f"kappa {'>= 0.6 -- PASSES the hard gate' if kappa >= 0.6 else '< 0.6 -- FAILS the hard gate: rubric/adjudication logic needs redesign and re-validation before any full run'}.",
        "",
        "## IMPORTANT CAVEAT",
        "",
        "This compares the pipeline against ONE human's blind labels. Per "
        "docs/labeling_protocol.md's 2026-08-12 correction, this is real "
        "human validation (not an AI-vs-AI audit), but it is NOT the same "
        "as having a human<->human agreement baseline. A low kappa here "
        "could reflect genuine rubric ambiguity (plausible given the "
        "multi_hop_setup boundary case found during worked-example "
        "construction) rather than a labeler failure specifically -- a "
        "second human labeling a subset would be needed to distinguish "
        "those two explanations.",
    ]

    report_path = SAMPLE_DIR / "kappa_report.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"\nCohen's kappa: {kappa:.4f}")
    print(f"Raw agreement: {raw_agreement:.4f}")
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
