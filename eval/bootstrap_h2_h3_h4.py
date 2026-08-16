"""Bootstrap CIs for H2, H3, H4 -- same method already validated for H1
(eval/bootstrap_h1.py): paired bootstrap, 10,000 resamples, stratified
by poison_form, scenario_id as the resampling unit (n=24), per
docs/preregistration.md SS5. Extends H1's statistical rigor to the
other three hypotheses, which were previously reported as pooled means
with no significance testing.

H3 note: laundering rate is a per-memory boolean (laundered/not),
aggregated here as (# laundered / # CARRIES) per scenario_id within
each (model, derivation_transform, depth) cell, then bootstrapped over
scenario_id -- a reasonable treatment of a rate statistic, though it
does not "average seeds first" the way H1/H2/H4's continuous per-trace
metrics do (there is no natural per-seed unit for a marker-survival
event). Cells with fewer than 2 scenarios contributing CARRIES memories
are skipped (report n, not a fabricated CI).

Usage:
    python eval/bootstrap_h2_h3_h4.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

RNG_SEED = 0
N_BOOT = 10_000
OUT_DIR = REPO_ROOT / "results" / "metrics"


def bootstrap_ci(values: np.ndarray, strata: np.ndarray, n_boot: int, rng: np.random.Generator):
    unique_strata = np.unique(strata)
    idx_by_stratum = [np.where(strata == s)[0] for s in unique_strata]
    boot_means = np.empty(n_boot)
    for b in range(n_boot):
        resampled = np.concatenate([rng.choice(idx, size=len(idx), replace=True) for idx in idx_by_stratum])
        boot_means[b] = values[resampled].mean()
    return float(values.mean()), float(np.percentile(boot_means, 2.5)), float(np.percentile(boot_means, 97.5))


def run_bootstrap(df: pd.DataFrame, group_cols: list[str], metric_cols: list[str], label: str) -> pd.DataFrame:
    rng = np.random.default_rng(RNG_SEED)
    rows = []
    for keys, g in df.groupby(group_cols):
        g = g.sort_values("scenario_id")
        strata = g["poison_form"].to_numpy()
        for metric in metric_cols:
            vals = g[metric].to_numpy()
            n = len(vals)
            if n < 2 or len(np.unique(strata)) < 1:
                rows.append(dict(zip(group_cols, keys if isinstance(keys, tuple) else (keys,)),
                                  metric=metric, n_scenarios=n, mean=None, ci95_lo=None, ci95_hi=None,
                                  note="insufficient scenarios for bootstrap"))
                continue
            mean, lo, hi = bootstrap_ci(vals, strata, N_BOOT, rng)
            rows.append(dict(zip(group_cols, keys if isinstance(keys, tuple) else (keys,)),
                              metric=metric, n_scenarios=n, mean=mean, ci95_lo=lo, ci95_hi=hi, note=""))
    out = pd.DataFrame(rows)
    path = OUT_DIR / f"{label}_bootstrap_ci.csv"
    out.to_csv(path, index=False)
    print(f"{label} bootstrap CIs ({len(out)} rows): {path}")
    return out


def h2():
    df = pd.read_csv(OUT_DIR / "h2_attribution_threshold_raw.csv")
    valid = df.dropna(subset=["P_BR", "R_BR", "inflation_ratio"])
    sl = (
        valid.groupby(["model", "attribution_threshold", "depth", "scenario_id", "poison_form"])
        [["P_BR", "R_BR", "inflation_ratio"]].mean().reset_index()
    )
    run_bootstrap(sl, ["model", "attribution_threshold", "depth"], ["P_BR", "R_BR", "inflation_ratio"], "h2")


def h3():
    df = pd.read_csv(OUT_DIR / "h3_marker_survival_raw.csv")
    scored = df[df["marker_survived"].notna()].copy()
    per_scenario = (
        scored.groupby(["model", "derivation_transform", "depth", "scenario_id", "poison_form"])
        .agg(laundering_rate=("laundered", "mean"), n_carries=("laundered", "size"))
        .reset_index()
    )
    run_bootstrap(per_scenario, ["model", "derivation_transform", "depth"], ["laundering_rate"], "h3")

    # Overall laundering rate CI (fully marginalized, one number per model)
    per_scenario_overall = (
        scored.groupby(["model", "scenario_id", "poison_form"])
        .agg(laundering_rate=("laundered", "mean")).reset_index()
    )
    run_bootstrap(per_scenario_overall, ["model"], ["laundering_rate"], "h3_overall")


def h4():
    df = pd.read_csv(OUT_DIR / "h4_containment_raw.csv")
    df["regen_overhead"] = df.apply(
        lambda r: (r["c_regen"] / r["c_regen_oracle"]) if r["c_regen_oracle"] > 0 else np.nan, axis=1
    )
    sl = (
        df.groupby(["model", "policy", "depth", "scenario_id", "poison_form"])
        [["c_regen", "missed_contaminated_n", "regen_overhead"]].mean().reset_index()
    )
    run_bootstrap(sl, ["model", "policy", "depth"], ["c_regen", "missed_contaminated_n", "regen_overhead"], "h4")

    # Wilcoxon: flat_transitive vs depth_aware, paired by scenario_id, per (model, depth)
    wil_rows = []
    for (model, depth), g in sl.groupby(["model", "depth"]):
        piv = g.pivot(index="scenario_id", columns="policy", values=["missed_contaminated_n", "regen_overhead"])
        for metric in ["missed_contaminated_n", "regen_overhead"]:
            flat = piv[(metric, "flat_transitive")].to_numpy()
            aware = piv[(metric, "depth_aware")].to_numpy()
            mask = ~(np.isnan(flat) | np.isnan(aware))
            flat, aware = flat[mask], aware[mask]
            if len(flat) < 2 or np.allclose(flat, aware):
                stat, p = np.nan, np.nan
            else:
                stat, p = wilcoxon(flat, aware)
            wil_rows.append({"model": model, "depth": depth, "metric": metric, "n_pairs": len(flat),
                              "flat_transitive_mean": float(np.mean(flat)) if len(flat) else np.nan,
                              "depth_aware_mean": float(np.mean(aware)) if len(aware) else np.nan,
                              "wilcoxon_stat": stat, "wilcoxon_p": p})
    wil_df = pd.DataFrame(wil_rows)
    path = OUT_DIR / "h4_wilcoxon.csv"
    wil_df.to_csv(path, index=False)
    print(f"H4 Wilcoxon (flat_transitive vs depth_aware): {path}")
    print(wil_df[wil_df["depth"] == 5].to_string(index=False))


if __name__ == "__main__":
    print("=== H2 ===")
    h2()
    print("\n=== H3 ===")
    h3()
    print("\n=== H4 ===")
    h4()
