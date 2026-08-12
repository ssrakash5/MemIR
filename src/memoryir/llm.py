"""LLM wrapper(s) for the eval/ generation harness.

Reuses the Azure OpenAI setup proven in spike/04_llm.py and
spike/05_e2e.py, including the truststore workaround for this network's
TLS-inspecting proxy (see spike/RESULTS.md). Credentials load from
../creds.env, one directory above the repo root and gitignored.

Every client class here exposes the SAME derive() interface (focus_texts,
background_texts, derivation_transform, prompt_style) -> str, so
harness.generate_trace() is agnostic to which model produced a trace --
this is what makes the 3-model cross-model extension (2026-08-12, see
docs/preregistration.md's dated addendum) a drop-in swap, not a harness
rewrite.

This module's derive() call is deliberately generic across the four
derivation_transform values (summarize/paraphrase/refine/continue) --
the transform only changes the instruction, not the mechanism.
"""
import json
import os
import time
from pathlib import Path

import requests
import truststore

truststore.inject_into_ssl()

from dotenv import load_dotenv
from openai import AzureOpenAI

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CREDS_PATH = REPO_ROOT.parent / "creds.env"

# model name -> (deployment env var, api-version env var). Both are
# OpenAI-compatible chat completions deployments on the same Azure
# OpenAI resource, so they share the LLMClient implementation below --
# only the deployment/model string differs.
_OPENAI_MODEL_ENV = {
    "gpt-4o-mini": ("AZURE_OPENAI_MINI_DEPLOYMENT_NAME", "AZURE_OPENAI_MINI_API_VERSION"),
    "gpt-4o": ("AZURE_OPENAI_DEPLOYMENT_NAME", "AZURE_OPENAI_API_VERSION"),
}

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


def _build_prompt(
    *, focus_texts: list[str], background_texts: list[str],
    derivation_transform: str, prompt_style: str,
) -> str:
    """Shared prompt construction -- identical across every model backend,
    so the model is the only thing that varies (no per-model prompt
    tuning), and cross-model comparisons stay apples-to-apples. No
    max_depth, scenario_id, or oracle labels are ever included -- the
    agent/model only ever sees retrieved content, matching
    spike/06_prefix_property.py's leakage-independence check."""
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
    return (
        f"{instruction} {style_note}\n\n{context_note}\n\n"
        f"Output only the resulting memory, no preamble."
    )


class LLMClient:
    """OpenAI-compatible chat-completions backend -- covers gpt-4o-mini
    (default, unchanged from the original single-model harness) and
    gpt-4o (2026-08-12 cross-model extension), which share one Azure
    OpenAI resource and API shape."""

    def __init__(self, *, model: str = "gpt-4o-mini", log_dir: Path | None = None):
        load_dotenv(CREDS_PATH)
        deployment_var, api_version_var = _OPENAI_MODEL_ENV[model]
        self._client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.environ[api_version_var],
        )
        self.deployment = os.environ[deployment_var]
        self.model_name = model
        # log_dir override lets concurrent full-sweep workers each get
        # their own subdirectory (avoids call_00001.json filename
        # collisions across LLMClient instances sharing one directory).
        self._log_dir = log_dir or (REPO_ROOT / "results" / "eval_llm_log")
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
        """
        prompt = _build_prompt(
            focus_texts=focus_texts, background_texts=background_texts,
            derivation_transform=derivation_transform, prompt_style=prompt_style,
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
                    "model": self.model_name,
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


class LlamaClient:
    """Llama-3.3-70B-Instruct via Azure AI Foundry's Models-as-a-Service
    REST endpoint -- a different API shape from the AzureOpenAI SDK
    (POST {endpoint}/models/chat/completions?api-version=..., Bearer
    auth), confirmed working 2026-08-12. Same derive() interface as
    LLMClient so harness.py doesn't need to know which backend it's
    calling."""

    def __init__(self, *, log_dir: Path | None = None):
        load_dotenv(CREDS_PATH)
        self._endpoint = os.environ["AZURE_LLAMA_ENDPOINT"]
        self._key = os.environ["AZURE_LLAMA_API_KEY"]
        self.deployment = os.environ["AZURE_LLAMA_DEPLOYMENT_NAME"]
        self._api_version = os.environ["AZURE_LLAMA_API_VERSION"]
        self.model_name = "llama-3.3-70b"
        self._log_dir = log_dir or (REPO_ROOT / "results" / "eval_llm_log_llama")
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
        prompt = _build_prompt(
            focus_texts=focus_texts, background_texts=background_texts,
            derivation_transform=derivation_transform, prompt_style=prompt_style,
        )
        url = f"{self._endpoint}/models/chat/completions?api-version={self._api_version}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._key}",
            "azureml-model-deployment": self.deployment,
        }
        body = {
            "messages": [{"role": "user", "content": prompt}],
            "model": self.deployment,
            "temperature": 0,
        }

        t0 = time.time()
        resp = requests.post(url, headers=headers, json=body, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        latency_s = time.time() - t0
        result = data["choices"][0]["message"]["content"].strip()

        self._call_count += 1
        log_path = self._log_dir / f"call_{self._call_count:05d}.json"
        log_path.write_text(
            json.dumps(
                {
                    "model": self.model_name,
                    "derivation_transform": derivation_transform,
                    "prompt_style": prompt_style,
                    "focus_texts": focus_texts,
                    "background_texts": background_texts,
                    "prompt": prompt,
                    "response_id": data.get("id"),
                    "response_content": result,
                    "usage": data.get("usage"),
                    "latency_s": latency_s,
                },
                indent=2,
            )
        )
        return result


def make_llm_client(model: str, *, log_dir: Path | None = None):
    """Factory: model name -> the right client. Single place that maps
    the 3-model roster to backend classes, so callers (harness/runners)
    never branch on model name themselves."""
    if model in _OPENAI_MODEL_ENV:
        return LLMClient(model=model, log_dir=log_dir)
    if model == "llama-3.3-70b":
        return LlamaClient(log_dir=log_dir)
    raise ValueError(f"Unknown model: {model!r}")
