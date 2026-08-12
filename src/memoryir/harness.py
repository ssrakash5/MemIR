"""Trace generation for the eval/ harness.

Implements the frozen rules from configs/experiment_grid.yaml:
  - shared retrieval per run (one retrieval feeds all write_fanout children)
  - true-parents-rank-first + distractor fill
  - depth-continuation rule (child_1 lineage continues; child_2-style
    siblings are fresh each depth)

One implementation decision made here that wasn't fully pinned down in
the frozen design docs, flagged explicitly rather than silently decided:
at depth_1, ALL of a scenario's source_facts (not just child_1's
true_parents) are part of the shared retrieved context, because child_2
needs its own true parent (e.g. B2) to also be retrievable in the same
run. Distractor fill count is therefore
`max(0, top_k - len(all_source_facts))` at depth_1, and
`max(0, top_k - 2)` at continuation depths (previous child_1 + one
distractor-derived seed for child_2). See eval/README.md.
"""
from dataclasses import dataclass

from . import db
from .embeddings import Embedder
from .llm import LLMClient
from .scenarios import source_fact_map


@dataclass
class TraceConfig:
    top_k: int
    write_fanout: int  # only 1 or 2 supported by this harness version
    derivation_transform: str
    seed: int
    max_depth: int


def generate_trace(
    spec: dict,
    config: TraceConfig,
    conn,
    llm: LLMClient,
    embedder: Embedder,
) -> str:
    scenario_id = spec["scenario_id"]
    prompt_style = spec["prompt_style"]
    trace_id = f"{scenario_id}__{config.derivation_transform}__seed{config.seed}"

    facts = source_fact_map(spec)
    distractors = spec["distractor_pool"]

    # --- depth 0: insert every source fact and every distractor as a memory ---
    local_id_to_memory_id: dict[str, int] = {}
    local_id_to_text: dict[str, str] = {}
    for local_id, fact in facts.items():
        text = fact["text"].strip()
        mid = db.insert_memory(
            conn,
            scenario_id=scenario_id,
            trace_id=trace_id,
            depth=0,
            branch="source_fact",
            local_id=local_id,
            content=text,
            embedding=embedder.embed(text),
        )
        local_id_to_memory_id[local_id] = mid
        local_id_to_text[local_id] = text
    for d in distractors:
        text = d["text"].strip()
        mid = db.insert_memory(
            conn,
            scenario_id=scenario_id,
            trace_id=trace_id,
            depth=0,
            branch="distractor",
            local_id=d["id"],
            content=text,
            embedding=embedder.embed(text),
        )
        local_id_to_memory_id[d["id"]] = mid
        local_id_to_text[d["id"]] = text

    def fill_distractors(exclude: set[str], n: int) -> list[str]:
        """Distractor local_ids in fixed listed order, skipping any in `exclude`."""
        out = []
        for d in distractors:
            if d["id"] in exclude:
                continue
            out.append(d["id"])
            if len(out) == n:
                break
        return out

    def derive_and_store(
        *,
        depth: int,
        branch: str,
        context_local_ids: list[str],
        structural_parent_local_ids: list[str],
    ) -> str:
        focus_texts = [local_id_to_text[lid] for lid in structural_parent_local_ids]
        background_texts = [
            local_id_to_text[lid]
            for lid in context_local_ids
            if lid not in structural_parent_local_ids
        ]
        text = llm.derive(
            focus_texts=focus_texts,
            background_texts=background_texts,
            derivation_transform=config.derivation_transform,
            prompt_style=prompt_style,
        )
        mid = db.insert_memory(
            conn,
            scenario_id=scenario_id,
            trace_id=trace_id,
            depth=depth,
            branch=branch,
            local_id=None,
            content=text,
            embedding=embedder.embed(text),
            derivation_transform=config.derivation_transform,
            prompt_style=prompt_style,
        )
        structural_ids = [local_id_to_memory_id[lid] for lid in structural_parent_local_ids]
        co_retrieved_ids = [
            local_id_to_memory_id[lid]
            for lid in context_local_ids
            if lid not in structural_parent_local_ids
        ]
        db.insert_influence_edges(
            conn,
            trace_id=trace_id,
            child_memory_id=mid,
            depth=depth,
            structural_parent_ids=structural_ids,
            co_retrieved_ids=co_retrieved_ids,
        )
        local_id_to_memory_id[f"__memid_{mid}"] = mid  # not used as a lookup key elsewhere
        return text

    # --- depth 1: explicit scenario spec, shared retrieval across children ---
    depth1 = spec["derivation_plan"]["depth_1"]
    child1_true_parents = depth1["child_1"]["true_parents"]
    child2_true_parents = depth1["child_2"]["true_parents"]

    all_source_local_ids = list(facts.keys())
    n_distractors_needed = max(0, config.top_k - len(all_source_local_ids))
    distractor_fill = fill_distractors(exclude=set(), n=n_distractors_needed)
    shared_context_ids = all_source_local_ids + distractor_fill

    derive_and_store(
        depth=1,
        branch="child_1",
        context_local_ids=shared_context_ids,
        structural_parent_local_ids=child1_true_parents,
    )
    prev_child1_local_id = None  # depth>=2 continuation uses memory ids directly, tracked below
    prev_child1_memory_id = None
    # re-fetch child_1's memory id (last inserted for branch child_1 at depth 1)
    prev_child1_memory_id = conn.execute(
        "SELECT id FROM memories WHERE trace_id=%s AND depth=1 AND branch='child_1' ORDER BY id DESC LIMIT 1",
        (trace_id,),
    ).fetchone()[0]
    # register it under a synthetic local_id so derive_and_store's lookup machinery works uniformly
    local_id_to_memory_id["__prev_child1__"] = prev_child1_memory_id
    local_id_to_text["__prev_child1__"] = conn.execute(
        "SELECT content FROM memories WHERE id=%s", (prev_child1_memory_id,)
    ).fetchone()[0]

    if config.write_fanout >= 2:
        derive_and_store(
            depth=1,
            branch="child_2",
            context_local_ids=shared_context_ids,
            structural_parent_local_ids=child2_true_parents,
        )

    # --- depths 2..max_depth: continuation rule ---
    for depth in range(2, config.max_depth + 1):
        seed_distractor_id = distractors[(depth - 2) % len(distractors)]["id"]
        n_fill = max(0, config.top_k - 2)
        fill = fill_distractors(exclude={seed_distractor_id}, n=n_fill)
        context_ids = ["__prev_child1__", seed_distractor_id] + fill

        derive_and_store(
            depth=depth,
            branch="child_1",
            context_local_ids=context_ids,
            structural_parent_local_ids=["__prev_child1__"],
        )
        new_child1_memory_id = conn.execute(
            "SELECT id FROM memories WHERE trace_id=%s AND depth=%s AND branch='child_1' ORDER BY id DESC LIMIT 1",
            (trace_id, depth),
        ).fetchone()[0]
        local_id_to_memory_id["__prev_child1__"] = new_child1_memory_id
        local_id_to_text["__prev_child1__"] = conn.execute(
            "SELECT content FROM memories WHERE id=%s", (new_child1_memory_id,)
        ).fetchone()[0]

        if config.write_fanout >= 2:
            derive_and_store(
                depth=depth,
                branch="child_2",
                context_local_ids=context_ids,
                structural_parent_local_ids=[seed_distractor_id],
            )

    return trace_id
