"""Enumerates the full generation grid from configs/experiment_grid.yaml +
configs/scenarios/ -- the single source of truth for what "the 5,760-trace
full sweep" means. No factor values are hard-coded here; everything is
read from the frozen config files so a future edit to the grid (through
the deviation-log protocol, not silently) is picked up automatically.
"""
from pathlib import Path

import yaml

from .scenarios import load_all_scenarios

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def trace_key(*, scenario_id: str, top_k: int, write_fanout: int,
              derivation_transform: str, seed: int) -> str:
    return f"{scenario_id}__tk{top_k}__wf{write_fanout}__{derivation_transform}__seed{seed}"


def load_generation_factors(grid_path: Path) -> dict:
    with open(grid_path) as f:
        grid = yaml.safe_load(f)
    gf = grid["generation_factors"]
    return {
        "top_k": gf["top_k"],
        "write_fanout": gf["write_fanout"],
        "derivation_transform": gf["derivation_transform"],
        "seeds": gf["seeds"],
    }


def enumerate_cells(
    *,
    grid_path: Path = REPO_ROOT / "configs" / "experiment_grid.yaml",
    scenarios_dir: Path = REPO_ROOT / "configs" / "scenarios",
) -> list[dict]:
    """Returns one dict per (scenario_id, top_k, write_fanout,
    derivation_transform, seed) combination -- the full enumerated grid,
    each with a deterministic trace_id."""
    factors = load_generation_factors(grid_path)
    specs = load_all_scenarios(scenarios_dir)

    cells = []
    for spec in specs:
        for top_k in factors["top_k"]:
            for write_fanout in factors["write_fanout"]:
                for transform in factors["derivation_transform"]:
                    for seed in factors["seeds"]:
                        cells.append({
                            "scenario_id": spec["scenario_id"],
                            "top_k": top_k,
                            "write_fanout": write_fanout,
                            "derivation_transform": transform,
                            "seed": seed,
                            "trace_id": trace_key(
                                scenario_id=spec["scenario_id"],
                                top_k=top_k,
                                write_fanout=write_fanout,
                                derivation_transform=transform,
                                seed=seed,
                            ),
                        })
    return cells


def sanity_check(cells: list[dict], factors: dict, n_scenarios: int) -> None:
    """Asserts the enumeration matches the frozen design exactly. Raises
    AssertionError (not a soft warning) on any mismatch -- this must pass
    before any generation call is made."""
    expected_n = (
        n_scenarios
        * len(factors["top_k"])
        * len(factors["write_fanout"])
        * len(factors["derivation_transform"])
        * len(factors["seeds"])
    )
    assert len(cells) == expected_n, f"expected {expected_n} cells, got {len(cells)}"

    ids = [c["trace_id"] for c in cells]
    assert len(ids) == len(set(ids)), f"duplicate trace_ids found: {len(ids) - len(set(ids))}"

    seen_scenarios = {c["scenario_id"] for c in cells}
    assert len(seen_scenarios) == n_scenarios, \
        f"expected {n_scenarios} distinct scenario_ids, saw {len(seen_scenarios)}"

    for factor_name, key in [
        ("top_k", "top_k"), ("write_fanout", "write_fanout"),
        ("derivation_transform", "derivation_transform"), ("seeds", "seed"),
    ]:
        seen = {c[key] for c in cells}
        expected = set(factors[factor_name])
        assert seen == expected, f"{factor_name}: expected {expected}, saw {seen}"

    for scenario_id in seen_scenarios:
        for factor_name, key in [
            ("top_k", "top_k"), ("write_fanout", "write_fanout"),
            ("derivation_transform", "derivation_transform"), ("seeds", "seed"),
        ]:
            per_scenario = {c[key] for c in cells if c["scenario_id"] == scenario_id}
            assert per_scenario == set(factors[factor_name]), (
                f"{scenario_id} missing some {factor_name} values: "
                f"expected {set(factors[factor_name])}, saw {per_scenario}"
            )
