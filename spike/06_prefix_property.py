"""Spike: does the prefix property hold for the generation/analysis split?

configs/experiment_grid.yaml's whole cost optimization (1,728 generated
traces instead of 41,472) depends on one claim: generating a trajectory to
max_depth=5 and reading back its depth-d prefix is equivalent to having
generated a trajectory with max_depth=d directly, for every d in 0..4.
This script tests that claim directly, per the review that flagged it.

Deliberately does NOT call a live LLM or compare two live generations
text-for-text -- that would confound harness/bookkeeping correctness with
model nondeterminism. Instead it uses a deterministic mock derivation
function and tests the HARNESS property: does state at depth d, as
recorded by a max_depth=5 run, match state at depth d from a max_depth=d
run, across every field the analysis layer depends on. A live-LLM version
of this same equivalence check should be re-run once the real harness
exists (eval/), since a real implementation could still violate the
property (e.g. non-deterministic ordering, or an update-in-place bug) even
if this mock's *design* doesn't.

Includes a negative control: a deliberately broken harness variant that
mutates earlier-depth state at a later depth (the specific failure case
flagged in review -- "depth 4 operation merges/updates M3 written at depth
2"). If the equivalence check can't detect that break, the check itself is
too weak to trust, regardless of whether the real harness passes it.
"""
import copy
import hashlib
import json
from dataclasses import asdict, dataclass, field


@dataclass
class Memory:
    id: str
    depth: int
    content: str
    content_label: str  # CARRIES / REFERENCES / CLEAN placeholder


@dataclass
class RetrievalEvent:
    run_id: str
    depth: int
    query: str
    retrieved_ids: list


@dataclass
class WriteEvent:
    run_id: str
    depth: int
    context_ids: list  # everything retrieved into context for this write
    child_id: str


@dataclass
class OracleEdge:
    parent_id: str
    child_id: str
    depth: int
    role: str  # STRUCTURAL_PARENT / CO_RETRIEVED


@dataclass
class Trace:
    memories: dict
    retrievals: list
    writes: list
    oracle_edges: list
    prompts: list  # (depth, prompt_text) -- checked for max_depth leakage


ROOT_ID = "M0_root"
DISTRACTOR_POOL = ["D1", "D2", "D3"]


def deterministic_child_content(context_ids: list, depth: int) -> str:
    """Stand-in for an LLM derive call: a pure function of (context, depth),
    so re-running never introduces nondeterminism into this check."""
    h = hashlib.sha256(("|".join(sorted(context_ids)) + f"@{depth}").encode()).hexdigest()[:12]
    return f"derived-content-{h}"


def run_harness(max_depth: int, *, mutate_bug: bool = False) -> Trace:
    """Deterministic mock harness. Append-only by construction: once a
    depth's Memory/RetrievalEvent/WriteEvent/OracleEdge is recorded, later
    iterations never touch it again -- which is the exact property under
    test. `mutate_bug=True` deliberately violates that (negative control).
    """
    memories = {ROOT_ID: Memory(ROOT_ID, 0, "root content", "CLEAN")}
    retrievals: list = []
    writes: list = []
    oracle_edges: list = []
    prompts: list = []

    current_parent = ROOT_ID
    for d in range(1, max_depth + 1):
        run_id = f"run_d{d}"
        # Note: query text is a function of the current parent and depth
        # counter d, NOT of max_depth -- max_depth must never leak into
        # anything the agent/model would see.
        query = f"find context related to {current_parent} at step {d}"
        context_ids = [current_parent] + DISTRACTOR_POOL[: (d % len(DISTRACTOR_POOL)) + 1]
        retrievals.append(RetrievalEvent(run_id, d, query, list(context_ids)))

        child_id = f"M{d}"
        content = deterministic_child_content(context_ids, d)
        prompt = f"Derive a memory from context: {context_ids}"
        prompts.append((d, prompt))

        memories[child_id] = Memory(child_id, d, content, "REFERENCES" if d % 2 else "CLEAN")
        writes.append(WriteEvent(run_id, d, list(context_ids), child_id))

        for pid in context_ids:
            role = "STRUCTURAL_PARENT" if pid == current_parent else "CO_RETRIEVED"
            oracle_edges.append(OracleEdge(pid, child_id, d, role))

        current_parent = child_id

    if mutate_bug and max_depth >= 4 and "M2" in memories:
        # THE SUBTLE FAILURE CASE FROM REVIEW: a later-depth operation
        # reaches back and mutates a memory written at an earlier depth.
        # A naive "filter final table by created_depth <= d" prefix
        # extraction would NOT catch this, because M2 still shows
        # created_depth=2 even though its content changed at depth 4.
        memories["M2"] = Memory("M2", 2, "MUTATED-BY-DEPTH-4-MERGE", "CARRIES")

    return Trace(memories, retrievals, writes, oracle_edges, prompts)


def snapshot_at_depth(full_trace: Trace, d: int) -> Trace:
    """The 'prefix by filtering the final table' extraction the real
    harness would need to do -- filters by recorded depth, does NOT
    re-derive state as it stood the moment depth d completed. If
    mutate_bug introduced a later write-back, this filter will silently
    return the MUTATED version, which is exactly the failure mode this
    spike needs to catch."""
    mem = {k: v for k, v in full_trace.memories.items() if v.depth <= d}
    retr = [r for r in full_trace.retrievals if r.depth <= d]
    wr = [w for w in full_trace.writes if w.depth <= d]
    edges = [e for e in full_trace.oracle_edges if e.depth <= d]
    prompts = [p for p in full_trace.prompts if p[0] <= d]
    return Trace(mem, retr, wr, edges, prompts)


def canonical(trace: Trace) -> str:
    """Order-independent, deterministic serialization for equality checks."""
    d = {
        "memories": sorted((asdict(m) for m in trace.memories.values()), key=lambda x: x["id"]),
        "retrievals": sorted((asdict(r) for r in trace.retrievals), key=lambda x: x["run_id"]),
        "writes": sorted((asdict(w) for w in trace.writes), key=lambda x: x["run_id"]),
        "oracle_edges": sorted(
            (asdict(e) for e in trace.oracle_edges), key=lambda x: (x["parent_id"], x["child_id"])
        ),
        "prompts": sorted(trace.prompts),
    }
    return json.dumps(d, sort_keys=True)


def check_no_max_depth_leakage(*, mutate_bug: bool) -> bool:
    """A substring search for the numeral max_depth is unreliable: the
    per-step depth counter d coincidentally equals max_depth on the final
    step (e.g. 'step 5' when max_depth=5 and d reaches 5), which is not a
    leak. The actual invariant to test is: prompt/query text for a given
    depth d must be IDENTICAL regardless of what max_depth was set to --
    if it isn't, something is threading max_depth into content the
    agent/model would see. Test this differentially with two different
    max_depth values sharing a common prefix depth range."""
    trace_5 = run_harness(max_depth=5, mutate_bug=mutate_bug)
    trace_8 = run_harness(max_depth=8, mutate_bug=mutate_bug)

    prompts_5 = {d: text for d, text in trace_5.prompts}
    prompts_8 = {d: text for d, text in trace_8.prompts}
    for d in range(1, 6):  # depths present in both traces
        if prompts_5[d] != prompts_8[d]:
            print(f"    leak at depth {d}: {prompts_5[d]!r} != {prompts_8[d]!r}")
            return False

    queries_5 = {r.depth: r.query for r in trace_5.retrievals}
    queries_8 = {r.depth: r.query for r in trace_8.retrievals}
    for d in range(1, 6):
        if queries_5[d] != queries_8[d]:
            print(f"    leak at depth {d}: {queries_5[d]!r} != {queries_8[d]!r}")
            return False

    return True


def run_property_check(*, mutate_bug: bool, label: str) -> bool:
    print(f"\n=== {label} (mutate_bug={mutate_bug}) ===")
    full = run_harness(max_depth=5, mutate_bug=mutate_bug)

    all_pass = True
    for d in range(0, 5):
        a_prefix = canonical(snapshot_at_depth(full, d))
        b_direct = canonical(run_harness(max_depth=d, mutate_bug=mutate_bug))
        ok = a_prefix == b_direct
        all_pass &= ok
        print(f"  d={d}  {'PASS' if ok else 'FAIL'}")

    leak_ok = check_no_max_depth_leakage(mutate_bug=mutate_bug)
    print(f"  max_depth leakage check   {'PASS (not leaked)' if leak_ok else 'FAIL (leaked!)'}")
    all_pass &= leak_ok

    print(f"  RESULT: {'PREFIX_SAFE' if all_pass else 'PREFIX_VIOLATED'}")
    return all_pass


def main() -> None:
    honest_result = run_property_check(mutate_bug=False, label="Honest (append-only) harness design")
    assert honest_result, (
        "Prefix property FAILED on the append-only harness design. "
        "This means configs/experiment_grid.yaml's generation/analysis "
        "split is invalid as specified -- depth would need to go back to "
        "being a generation factor, not an analysis factor."
    )

    buggy_result = run_property_check(
        mutate_bug=True, label="Negative control: harness with a later-depth mutation bug"
    )
    assert not buggy_result, (
        "Negative control did NOT fail -- the equivalence check is too "
        "weak to trust (it can't detect a real prefix-property violation), "
        "so the PASS above on the honest harness is not meaningful evidence."
    )

    print(
        "\nGREEN: prefix property holds for this harness design (all d=0..4 "
        "PASS, no max_depth leakage), AND the check is proven capable of "
        "catching a real violation (negative control correctly FAILED).\n"
        "Caveat: this validates the DESIGN using deterministic mock "
        "derivation. The real eval/ harness, once built, needs its own run "
        "of an equivalent check -- a real implementation could still "
        "violate this property (e.g. non-deterministic write ordering, an "
        "update-in-place bug) even though this mock's append-only design "
        "doesn't."
    )


if __name__ == "__main__":
    main()
