"""Spike: one structured model call, full request metadata captured.

Uses the Azure OpenAI credentials in ../creds.env (one directory above this
repo, NOT inside it, and gitignored regardless -- requests/responses are
logged with keys redacted). This spike proves: (1) a
structured/JSON-schema call works against the deployment we'll actually use,
and (2) we can log full request/response metadata with the key redacted,
which every real eval run will need to do for reproducibility.
"""
import json
import os
import time
from pathlib import Path

import truststore

truststore.inject_into_ssl()  # use Windows system cert store; corp TLS-inspection
# root CA is trusted by Windows but not by Python's bundled certifi store.

from dotenv import load_dotenv
from openai import AzureOpenAI

REPO_ROOT = Path(__file__).resolve().parent.parent
CREDS_PATH = REPO_ROOT.parent / "creds.env"
RESULTS_DIR = REPO_ROOT / "results"

RUBRIC_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "carries_label",
        "schema": {
            "type": "object",
            "properties": {
                "label": {"type": "string", "enum": ["CARRIES", "REFERENCES", "CLEAN"]},
                "reasoning": {"type": "string"},
            },
            "required": ["label", "reasoning"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}


def redact(value: str) -> str:
    if not value:
        return ""
    return value[:4] + "..." + f"[len={len(value)}]"


def main() -> None:
    load_dotenv(CREDS_PATH)

    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    api_key = os.environ["AZURE_OPENAI_API_KEY"]
    deployment = os.environ["AZURE_OPENAI_MINI_DEPLOYMENT_NAME"]
    api_version = os.environ["AZURE_OPENAI_MINI_API_VERSION"]

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )

    # This is a placeholder rubric call, NOT the real labeling rubric — the
    # real one belongs in a version-controlled file per
    # docs/labeling_protocol.md, not embedded in code. This just proves
    # structured JSON output + logging works against this deployment.
    system_prompt = (
        "You label whether a derived memory CARRIES a false claim, only "
        "REFERENCES the topic, or is CLEAN of it. Respond via the given schema."
    )
    user_prompt = (
        'Injected false claim: "The Eiffel Tower is in Berlin."\n'
        'Derived memory: "European landmarks include famous towers such as '
        'the Eiffel Tower, located in a major capital city."\n'
        "Label this derived memory."
    )

    request_payload = {
        "model": deployment,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "response_format": RUBRIC_SCHEMA,
    }

    t0 = time.time()
    response = client.chat.completions.create(**request_payload)
    latency_s = time.time() - t0

    raw_content = response.choices[0].message.content
    parsed = json.loads(raw_content)
    assert parsed["label"] in {"CARRIES", "REFERENCES", "CLEAN"}, f"bad label: {parsed}"
    assert isinstance(parsed["reasoning"], str) and parsed["reasoning"], "empty reasoning"

    RESULTS_DIR.mkdir(exist_ok=True)
    log_path = RESULTS_DIR / "spike_04_llm_call.json"
    log_entry = {
        "request": {**request_payload, "_note": "api_key not included; auth via AzureOpenAI client, not request body"},
        "endpoint_redacted": redact(endpoint),
        "response": {
            "id": response.id,
            "model": response.model,
            "usage": response.usage.model_dump() if response.usage else None,
            "content": raw_content,
        },
        "latency_s": latency_s,
    }
    log_path.write_text(json.dumps(log_entry, indent=2))

    print(f"GREEN: structured call to deployment={deployment} succeeded in {latency_s:.2f}s.")
    print(f"  label={parsed['label']!r} reasoning={parsed['reasoning'][:80]!r}...")
    print(f"  full request/response logged to {log_path.relative_to(REPO_ROOT)} (key redacted)")


if __name__ == "__main__":
    main()
