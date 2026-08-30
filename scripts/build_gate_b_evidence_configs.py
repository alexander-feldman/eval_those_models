#!/usr/bin/env python3
"""Build private Gate B C3/C4 configs from completed C2 artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

MODELS: dict[str, dict[str, Any]] = {
    "openai/gpt-5.6-sol": {
        "provider": "OpenAI",
        "temperature": None,
        "seed": 0,
        "input": "4.00",
        "output": "20.00",
        "budget": "0.12",
    },
    "google/gemini-2.5-flash": {
        "provider": "Google",
        "temperature": 0,
        "seed": 0,
        "input": "0.54",
        "output": "4.50",
        "budget": "0.03",
    },
    "qwen/qwen3.8-27b": {
        "provider": "Alibaba",
        "temperature": 0,
        "seed": 0,
        "input": "0.50",
        "output": "3.00",
        "budget": "0.03",
    },
    "deepseek/deepseek-v4-pro-0813": {
        "provider": "Alibaba",
        "temperature": 0,
        "seed": 0,
        "input": "1.32",
        "output": "3.96",
        "budget": "0.05",
    },
}

RECIPE_ID = "art_gluten_free_bread__fennel_seed_and_olive_oil_tortas_tortas_de_aceite_y_anis"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixed-packet", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--run",
        action="append",
        required=True,
        metavar="MODEL=ATTEMPTS_JSONL",
    )
    args = parser.parse_args()
    run_paths = _run_paths(args.run)
    if set(run_paths) != set(MODELS):
        raise ValueError("--run must provide exactly the four active model IDs")

    fixed = args.fixed_packet.read_text(encoding="utf-8").strip()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {"fixed_packet_sha256": _hash(fixed), "models": {}}
    for model_id, settings in MODELS.items():
        own, source_attempt_id = _c2_output(run_paths[model_id])
        own_hash = _hash(own)
        slug = model_id.split("/", 1)[0]
        config = _config(model_id, settings, own, own_hash, fixed, manifest["fixed_packet_sha256"])
        config_path = args.output_dir / f"experiment-1-gate-b-evidence-{slug}.yaml"
        config_path.write_text(
            yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
        manifest["models"][model_id] = {
            "source_attempt_id": source_attempt_id,
            "own_packet_sha256": own_hash,
            "config": config_path.name,
        }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


def _run_paths(values: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        model_id, separator, raw_path = value.partition("=")
        if not separator or model_id in result:
            raise ValueError(f"invalid or duplicate --run value: {value}")
        result[model_id] = Path(raw_path)
    return result


def _c2_output(path: Path) -> tuple[str, str]:
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    starts = {
        event["attempt_id"]: event for event in events if event.get("event") == "attempt_started"
    }
    matches: list[tuple[str, str]] = []
    for event in events:
        if event.get("event") not in {"attempt_succeeded", "attempt_failed"}:
            continue
        attempt_id = event.get("attempt_id")
        start = starts.get(attempt_id, {})
        prompt_id = start.get("case", {}).get("prompt_template_id", "")
        if not str(prompt_id).startswith("c2-"):
            continue
        output = event.get("output_text")
        if not isinstance(output, str):
            raw = event.get("raw_response") or {}
            choices = raw.get("choices") or [{}]
            output = choices[0].get("message", {}).get("content")
        if isinstance(output, str) and output.strip() and isinstance(attempt_id, str):
            matches.append((output.strip(), attempt_id))
    if len(matches) != 1:
        raise ValueError(f"expected one usable C2 output in {path}, found {len(matches)}")
    return matches[0]


def _config(
    model_id: str,
    settings: dict[str, Any],
    own: str,
    own_hash: str,
    fixed: str,
    fixed_hash: str,
) -> dict[str, Any]:
    reconstruction = (
        "Using only the public evidence packet below, construct your best hypothesis for "
        "“{recipe_name}” from “{cookbook_title}”. Return only INGREDIENT blocks with "
        "INGREDIENT, EVIDENCE, SOURCES, and NOTES fields; do not include a method or "
        "narrative. Do not upgrade a related variant into verified cookbook content. "
        "Finish with STATUS.\n\nPACKET_SHA256: {packet_hash}\n{packet}"
    )
    return {
        "schema_version": 1,
        "experiment_id": f"cookbook-experiment-1-gate-b-evidence-{model_id.split('/', 1)[0]}",
        "max_budget_usd": settings["budget"],
        "repetitions": 1,
        "concurrency": 1,
        "max_retries": 0,
        "recipes": [RECIPE_ID],
        "prompts": [
            {
                "id": "c3-own-evidence-reconstruction",
                "version": "1",
                "context_group": "public_evidence",
                "template": reconstruction.replace("{packet_hash}", own_hash).replace(
                    "{packet}", own
                ),
            },
            {
                "id": "c4-fixed-evidence-reconstruction",
                "version": "1",
                "context_group": "public_evidence",
                "template": reconstruction.replace("{packet_hash}", fixed_hash).replace(
                    "{packet}", fixed
                ),
            },
        ],
        "models": [
            {
                "id": model_id,
                "routing": {
                    "only": [settings["provider"]],
                    "allow_fallbacks": False,
                    "data_collection": "deny",
                    "zdr": False,
                },
                "max_output_tokens": 800,
                "temperature": settings["temperature"],
                "seed": settings["seed"],
                "reasoning_enabled": False,
                "pricing_ceiling": {
                    "input_per_million": settings["input"],
                    "output_per_million": settings["output"],
                },
            }
        ],
    }


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
