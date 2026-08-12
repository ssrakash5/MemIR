"""Scenario spec loading for the eval/ generation harness.

Loads and lightly validates the human-approved YAML specs under
configs/scenarios/ -- does not re-derive or second-guess oracle
true_parents assignments, those are the approved ground truth per
configs/scenarios/README.md.
"""
from pathlib import Path

import yaml

REQUIRED_TOP_LEVEL = [
    "scenario_id",
    "poison_form",
    "signal_strength",
    "prompt_style",
    "semantic_target",
    "source_facts",
    "derivation_plan",
    "distractor_pool",
]


class ScenarioError(ValueError):
    pass


def load_scenario(path: Path) -> dict:
    with open(path) as f:
        spec = yaml.safe_load(f)

    missing = [k for k in REQUIRED_TOP_LEVEL if k not in spec]
    if missing:
        raise ScenarioError(f"{path}: missing required fields {missing}")

    all_ids = {f["id"] for f in spec["source_facts"].get("poisoned", [])}
    all_ids |= {f["id"] for f in spec["source_facts"].get("benign", [])}
    depth1 = spec["derivation_plan"]["depth_1"]
    for child_key in ("child_1", "child_2"):
        if child_key not in depth1:
            raise ScenarioError(f"{path}: derivation_plan.depth_1 missing {child_key}")
        for parent_id in depth1[child_key]["true_parents"]:
            if parent_id not in all_ids:
                raise ScenarioError(
                    f"{path}: {child_key}.true_parents references unknown id {parent_id!r}"
                )

    if len(spec["distractor_pool"]) < 9:
        raise ScenarioError(
            f"{path}: distractor_pool has {len(spec['distractor_pool'])} entries, "
            f"needs >=9 to cover top_k=10 per the frozen distractor rule"
        )

    return spec


def load_all_scenarios(scenarios_dir: Path) -> list[dict]:
    """Loads every *.yaml directly under scenarios_dir and its pilot/ subdir."""
    paths = sorted(scenarios_dir.glob("*.yaml")) + sorted((scenarios_dir / "pilot").glob("*.yaml"))
    return [load_scenario(p) for p in paths]


def source_fact_map(spec: dict) -> dict[str, dict]:
    """local_id -> {semantic_unit, text} for every poisoned/benign source fact."""
    out = {}
    for f in spec["source_facts"].get("poisoned", []):
        out[f["id"]] = f
    for f in spec["source_facts"].get("benign", []):
        out[f["id"]] = f
    return out
