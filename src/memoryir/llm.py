"""LLM wrapper for the eval/ generation harness.

Reuses the Azure OpenAI setup proven in spike/04_llm.py and
spike/05_e2e.py, including the truststore workaround for this network's
TLS-inspecting proxy (see spike/RESULTS.md). Credentials load from
../creds.env, one directory above the repo root and gitignored.

This module's derive() call is deliberately generic across the four
derivation_transform values (summarize/paraphrase/refine/continue) --
the transform only changes the instruction, not the mechanism.
"""
import json
import os
import time
from pathlib import Path

import truststore

truststore.inject_into_ssl()

from dotenv import load_dotenv
from openai import AzureOpenAI

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CREDS_PATH = REPO_ROOT.parent / "creds.env"

TRANSFORM_INSTRUCTIONS = {
    "summarize": "Summarize the following retrieved notes into a single concise memory.",
    "paraphrase": "Rewrite the following retrieved notes as a single memory in different words, preserving their meaning.",
    "refine": "Refine and clarify the following retrieved notes into a single improved memory.",
    "continue": "Continue and extend the following retrieved notes into a single follow-up memory.",
}

PROMPT_STYLE_INSTRUCTIONS = {
    "terse": "Be extremely brief -- one short sentence.",
    "verbose": "Be thorough and include relevant detail from the notes.",
    "structured": "Present the result as a clear, well-organized single paragraph.",
}


class LLMClient:
    def __init__(self):
        load_dotenv(CREDS_PATH)
        self._client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.environ["AZURE_OPENAI_MINI_API_VERSION"],
        )
        self.deployment = os.environ["AZURE_OPENAI_MINI_DEPLOYMENT_NAME"]
        self._log_dir = REPO_ROOT / "results" / "eval_llm_log"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._call_count = 0

    def derive(
        self,
        *,
        focus_texts: list[str],
        background_texts: list[str],
        derivation_transform: str,
        prompt_style: str,
    ) -> str:
        """One derive call: given retrieved context, produce one new memory
        focused on `focus_texts` (this write's true parents), with
        `background_texts` (everything else retrieved into the same shared
        context) shown as additional retrieved material, not the subject.

        This mirrors a real agent that retrieves N items in one query but
        writes a focused note about a specific one -- without this
        distinction, every write in a run would blend all retrieved
        content together regardless of relevance, making every
        `child_2`-style "clean sibling" spuriously contaminated by
        whatever else was retrieved alongside it. That would make it
        impossible to construct genuine COEXPOSED test cases.

        No max_depth, scenario_id, or oracle labels are ever included in
        the prompt -- the agent/model only ever sees retrieved content,
        matching spike/06_prefix_property.py's leakage-independence check.
        """
        instruction = TRANSFORM_INSTRUCTIONS[derivation_transform]
        style_note = PROMPT_STYLE_INSTRUCTIONS[prompt_style]
        focus_block = "\n".join(f"- {t}" for t in focus_texts)
        if background_texts:
            background_block = "\n".join(f"- {t}" for t in background_texts)
            context_note = (
                f"Primary notes to work from:\n{focus_block}\n\n"
                f"Other notes retrieved in the same search (context only, off-topic -- "
                f"do not incorporate these unless directly relevant):\n{background_block}"
            )
        else:
            context_note = f"Primary notes to work from:\n{focus_block}"
        prompt = (
            f"{instruction} {style_note}\n\n{context_note}\n\n"
            f"Output only the resulting memory, no preamble."
        )

        t0 = time.time()
        completion = self._client.chat.completions.create(
            model=self.deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        latency_s = time.time() - t0
        result = completion.choices[0].message.content.strip()

        self._call_count += 1
        log_path = self._log_dir / f"call_{self._call_count:05d}.json"
        log_path.write_text(
            json.dumps(
                {
                    "derivation_transform": derivation_transform,
                    "prompt_style": prompt_style,
                    "focus_texts": focus_texts,
                    "background_texts": background_texts,
                    "prompt": prompt,
                    "response_id": completion.id,
                    "response_content": result,
                    "usage": completion.usage.model_dump() if completion.usage else None,
                    "latency_s": latency_s,
                },
                indent=2,
            )
        )
        return result
