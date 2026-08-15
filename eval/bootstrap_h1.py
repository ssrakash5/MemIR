"""Bootstrap CIs + Wilcoxon signed-rank for H1, per docs/preregistration.md
SS5: paired bootstrap, 10,000 resamples, 95% CIs, resampling unit =
scenario_id stratified by poison_form (n=24, 6/stratum) -- NOT raw trace
rows (pseudo-replication). Reads results/metrics/blast_radius_raw.csv
(already seed-averaged per scenario-condition upstream is NOT assumed;
this script does its own seed-averaging step here, explicitly).

Headline level: fully marginalized over top_k/write_fanout/derivation_transform,
per (model, policy, depth) -- this is the paper-ready number.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

from memoryir.scenarios import load_all_scenarios

RNG_SEED = 0
N_BOOT = 10_000
METRICS = ["P_BR", "R_BR", "inflation_ratio"]


def scenario_level_means(df: pd.DataFrame) -> pd.DataFrame:
    """Average seeds AND top_k/write_fanout/derivation_transform within
    each (model, policy, depth, scenario_id) -- one value per scenario,
    matching the headline marginalization."""
    valid = df.dropna(subset=METRICS)
    return (
        valid.groupby(["model", "policy", "depth", "scenario_id"])[METRICS]
        .mean().reset_index()
    )


def bootstrap_ci(values: np.ndarray, strata: np.ndarray, n_boot: int, rng: np.random.Generator) -> tuple[float, float, float]:
    """Stratified bootstrap (resample WITHIN each poison_form stratum,
    same stratum sizes each draw) -- mean + 95% percentile CI."""
    unique_strata = np.unique(strata)
    boot_means = np.empty(n_boot)
    idx_by_stratum = [np.where(strata == s)[0] for s in unique_strata]
    for b in range(n_boot):
        resampled = np.concatenate([
            rng.choice(idx, size=len(idx), replace=True) for idx in idx_by_stratum
        ])
        boot_means[b] = values[resampled].mean()
    return float(values.mean()), float(np.percentile(boot_means, 2.5)), float(np.percentile(boot_means, 97.5))


def main() -> None:
    raw_path = REPO_ROOT / "results" / "metrics" / "blast_radius_raw.csv"
    df = pd.read_csv(raw_path)
    print(f"Loaded {len(df)} raw rows.")

    specs = load_all_scenarios(REPO_ROOT / "configs" / "scenarios")
    poison_form_by_scenario = {s["scenario_id"]: s["poison_form"] for s in specs}

    sl = scenario_level_means(df)
    sl["poison_form"] = sl["scenario_id"].map(poison_form_by_scenario)

    rng = np.random.default_rng(RNG_SEED)
    ci_rows = []
    for (model, policy, depth), g in sl.groupby(["model", "policy", "depth"]):
        g = g.sort_values("scenario_id")
        strata = g["poison_form"].to_numpy()
        for metric in METRICS:
            vals = g[metric].to_numpy()
            n = len(vals)
            mean, lo, hi = bootstrap_ci(vals, strata, N_BOOT, rng)
            ci_rows.append({"model": model, "policy": policy, "depth": depth,
                             "metric": metric, "n_scenarios": n,
                             "mean": mean, "ci95_lo": lo, "ci95_hi": hi})
    ci_df = pd.DataFrame(ci_rows)
    ci_path = REPO_ROOT / "results" / "metrics" / "h1_bootstrap_ci.csv"
    ci_df.to_csv(ci_path, index=False)
    print(f"\nBootstrap CIs (n_boot={N_BOOT}, stratified by poison_form): {ci_path}")

    # Wilcoxon signed-rank: structural vs context_exposure, paired by
    # scenario_id, at each (model, depth) -- the direct H1 test.
    wil_rows = []
    for (model, depth), g in sl.groupby(["model", "depth"]):
        piv = g.pivot(index="scenario_id", columns="policy", values=METRICS)
        for metric in METRICS:
            struct = piv[(metric, "structural")].to_numpy()
            ctx = piv[(metric, "context_exposure")].to_numpy()
            mask = ~(np.isnan(struct) | np.isnan(ctx))
            struct, ctx = struct[mask], ctx[mask]
            if len(struct) < 2 or np.allclose(struct, ctx):
                stat, p = np.nan, np.nan
            else:
                stat, p = wilcoxon(struct, ctx)
            wil_rows.append({
                "model": model, "depth": depth, "metric": metric,
                "n_pairs": len(struct),
                "structural_mean": float(np.mean(struct)) if len(struct) else np.nan,
                "context_exposure_mean": float(np.mean(ctx)) if len(ctx) else np.nan,
                "wilcoxon_stat": stat, "wilcoxon_p": p,
            })
    wil_df = pd.DataFrame(wil_rows)
    wil_path = REPO_ROOT / "results" / "metrics" / "h1_wilcoxon.csv"
    wil_df.to_csv(wil_path, index=False)
    print(f"Wilcoxon signed-rank (structural vs context_exposure, paired by scenario_id): {wil_path}")

    print("\n=== Headline: R_BR and inflation_ratio, pooled + 95% CI, all 3 models, depth 1 vs 5 ===")
    show = ci_df[ci_df["depth"].isin([1, 5]) & ci_df["metric"].isin(["R_BR", "inflation_ratio", "P_BR"])]
    print(show.sort_values(["model", "policy", "metric", "depth"]).to_string(index=False))

    print("\n=== Wilcoxon: is structural vs context_exposure difference significant? (depth=5) ===")
    print(wil_df[wil_df["depth"] == 5].to_string(index=False))


if __name__ == "__main__":
    main()
