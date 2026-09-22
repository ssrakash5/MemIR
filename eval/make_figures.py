"""Generates the paper's primary figures directly from
results/metrics/*.csv -- no hand-edited plots, regenerable by one
command, per CLAUDE.md's standards section.

Figures (matching week4.md's original spec):
  1. Precision vs. depth, one line per top_k, 95% CI ribbons
  2. Precision/recall frontier as attribution threshold varies (H2)
  3. Laundering rate by depth and poison_form (H3)
  4. Blast radius growth: flagged objects vs. depth (H1/H4)
  5. False-positive rate on clean controls

Usage:
    python eval/make_figures.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from memoryir.scenarios import load_all_scenarios

METRICS_DIR = REPO_ROOT / "results" / "metrics"
FIG_DIR = REPO_ROOT / "results" / "figures"
MODELS = ["gpt-4o-mini", "gpt-4o", "llama-3.3-70b"]
COLORS = {"gpt-4o-mini": "#1f77b4", "gpt-4o": "#ff7f0e", "llama-3.3-70b": "#2ca02c"}

RNG_SEED = 0
N_BOOT = 10_000


def bootstrap_ci(values: np.ndarray, strata: np.ndarray, n_boot: int, rng: np.random.Generator):
    unique_strata = np.unique(strata)
    idx_by_stratum = [np.where(strata == s)[0] for s in unique_strata]
    boot_means = np.empty(n_boot)
    for b in range(n_boot):
        resampled = np.concatenate([rng.choice(idx, size=len(idx), replace=True) for idx in idx_by_stratum])
        boot_means[b] = values[resampled].mean()
    return float(values.mean()), float(np.percentile(boot_means, 2.5)), float(np.percentile(boot_means, 97.5))


def fig1_precision_vs_depth_by_topk():
    """Context-exposure P_BR vs depth, one line per top_k, CI ribbons.
    Held-explicit per H1's marginalization spec (top_k x depth explicit,
    marginalize write_fanout x derivation_transform x seed within scenario)."""
    df = pd.read_csv(METRICS_DIR / "blast_radius_raw.csv")
    specs = load_all_scenarios(REPO_ROOT / "configs" / "scenarios")
    pf = {s["scenario_id"]: s["poison_form"] for s in specs}
    df = df[df["policy"] == "context_exposure"].dropna(subset=["P_BR"])
    df["poison_form"] = df["scenario_id"].map(pf)

    sl = df.groupby(["model", "top_k", "depth", "scenario_id", "poison_form"])["P_BR"].mean().reset_index()

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)
    rng = np.random.default_rng(RNG_SEED)
    for ax, model in zip(axes, MODELS):
        for top_k in sorted(sl["top_k"].unique()):
            sub = sl[(sl["model"] == model) & (sl["top_k"] == top_k)]
            depths, means, los, his = [], [], [], []
            for depth in sorted(sub["depth"].unique()):
                g = sub[sub["depth"] == depth]
                vals = g["P_BR"].to_numpy()
                strata = g["poison_form"].to_numpy()
                if len(vals) < 2:
                    continue
                mean, lo, hi = bootstrap_ci(vals, strata, N_BOOT, rng)
                depths.append(depth); means.append(mean); los.append(lo); his.append(hi)
            ax.plot(depths, means, marker="o", label=f"top_k={top_k}")
            ax.fill_between(depths, los, his, alpha=0.15)
        ax.set_title(model)
        ax.set_xlabel("depth")
        ax.set_ylim(0, 1.05)
    axes[0].set_ylabel("Blast-radius precision (P_BR)\ncontext-exposure policy")
    axes[0].legend(fontsize=8)
    # No embedded "Figure N: ..." title here -- the LaTeX \caption is the
    # only title (duplicating it in the image itself read as inconsistent
    # IEEE-template formatting and, for fig2, literally clipped off the
    # canvas edge -- see docs/paper/latex/README.md's formatting-fix note).
    fig.tight_layout()
    out = FIG_DIR / "fig1_precision_vs_depth_by_topk.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Wrote {out}")


def fig2_precision_recall_frontier():
    ci = pd.read_csv(METRICS_DIR / "h2_bootstrap_ci.csv")
    ci = ci[ci["depth"] == 5]
    fig, ax = plt.subplots(figsize=(6, 5))
    for model in MODELS:
        sub = ci[ci["model"] == model]
        p = sub[sub["metric"] == "P_BR"].sort_values("attribution_threshold")
        r = sub[sub["metric"] == "R_BR"].sort_values("attribution_threshold")
        ax.plot(r["mean"], p["mean"], marker="o", color=COLORS[model], label=model)
        for _, (pr, rr) in enumerate(zip(p.itertuples(), r.itertuples())):
            ax.annotate(f"{pr.attribution_threshold}", (rr.mean, pr.mean), fontsize=7,
                        textcoords="offset points", xytext=(5, 5))
    ax.set_xlabel("Recall (R_BR)")
    ax.set_ylabel("Precision (P_BR)")
    ax.legend()
    fig.tight_layout()
    out = FIG_DIR / "fig2_precision_recall_frontier.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Wrote {out}")


def fig3_laundering_rate():
    ci = pd.read_csv(METRICS_DIR / "h3_bootstrap_ci.csv").dropna(subset=["mean"])
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)
    for ax, model in zip(axes, MODELS):
        sub = ci[ci["model"] == model]
        for transform in sorted(sub["derivation_transform"].unique()):
            g = sub[sub["derivation_transform"] == transform].sort_values("depth")
            if g.empty:
                continue
            ax.plot(g["depth"], g["mean"], marker="o", label=transform)
            ax.fill_between(g["depth"], g["ci95_lo"], g["ci95_hi"], alpha=0.15)
        ax.set_title(model)
        ax.set_xlabel("depth")
    axes[0].set_ylabel("Laundering rate")
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    out = FIG_DIR / "fig3_laundering_rate.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Wrote {out}")


def fig4_blast_radius_growth():
    df = pd.read_csv(METRICS_DIR / "blast_radius_raw.csv")
    fig, ax = plt.subplots(figsize=(7, 5))
    for model in MODELS:
        for policy, ls in [("context_exposure", "-"), ("structural", "--")]:
            sub = df[(df["model"] == model) & (df["policy"] == policy)]
            g = sub.groupby("depth")["b_flagged_n"].mean().reset_index()
            ax.plot(g["depth"], g["b_flagged_n"], ls, color=COLORS[model],
                    label=f"{model} ({policy})", alpha=0.85)
    ax.set_xlabel("depth")
    ax.set_ylabel("Mean flagged objects (blast radius)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    out = FIG_DIR / "fig4_blast_radius_growth.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Wrote {out}")


def fig5_clean_control_false_positive():
    df = pd.read_csv(METRICS_DIR / "clean_control_false_positive.csv")
    fig, ax = plt.subplots(figsize=(7, 5))
    for model in MODELS:
        for policy in ["structural", "context_exposure", "depth_aware"]:
            sub = df[(df["model"] == model) & (df["policy"] == policy)].sort_values("depth")
            if sub.empty:
                continue
            style = "-" if model == "gpt-4o-mini" else ("--" if model == "gpt-4o" else ":")
            ax.plot(sub["depth"], sub["mean"], style, label=f"{model} / {policy}", alpha=0.8)
    ax.set_xlabel("depth")
    ax.set_ylabel("Mean objects flagged (B_true = 0 for all)")
    ax.legend(fontsize=6, ncol=2)
    fig.tight_layout()
    out = FIG_DIR / "fig5_clean_control_false_positive.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig1_precision_vs_depth_by_topk()
    fig2_precision_recall_frontier()
    fig3_laundering_rate()
    fig4_blast_radius_growth()
    fig5_clean_control_false_positive()
    print(f"\nAll figures written to {FIG_DIR}")
