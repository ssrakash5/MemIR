"""Scenario spec loading for the eval/ generation harness.

Loads and lightly validates the human-approved YAML specs under
configs/scenarios/ -- does not re-derive or second-guess oracle
true_parents assignments, those are the approved ground truth per
configs/scenarios/README.md.
"""
import re
from pathlib import Path

import yaml

# H3 marker-token extraction (added 2026-08-14, DATED DECISION): no
# scenario spec authors an explicit marker_tokens field. Mechanically
# derived instead --
# ID-like tokens (codes, account/routing numbers, emails, amounts) found
# in P1's text, unioned with any `entities` dict value that appears
# verbatim as a substring of P1's text. Verified to give >=1 marker for
# all 24 scenarios (see eval/compute_h3_metrics.py's exploration). If
# this needs to change, it's a rubric-level edit requiring the usual
# dated deviation entry, same as any other frozen-design change.
_MARKER_ID_PATTERN = re.compile(
    r"[A-Z]{1,6}-?\d{2,}|\+?\d[\d\-]{6,}|\d[\d,]{2,}|\b[\w.-]+@[\w.-]+\.\w+\b"
)


def extract_markers(spec: dict) -> set[str]:
    """Distinctive surface-form tokens whose disappearance from a
    descendant's content defines 'laundering' for H3 -- see module
    docstring above."""
    p1_text = source_fact_map(spec)["P1"]["text"]
    markers = set(_MARKER_ID_PATTERN.findall(p1_text))
    for v in spec.get("entities", {}).values():
        v = str(v)
        if v in p1_text:
            markers.add(v)
    return markers

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
