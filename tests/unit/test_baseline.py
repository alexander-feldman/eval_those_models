import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from eval_those_models.baseline import BaselineMatchError, match_baseline
from eval_those_models.config import (
    ExperimentConfig,
    ModelConfig,
    PricingCeiling,
    PromptConfig,
    RoutingConfig,
)


def _config() -> ExperimentConfig:
    return ExperimentConfig(
        schema_version=1,
        experiment_id="baseline",
        recipe_ids=("recipe",),
        prompts=(
            PromptConfig(
                "neutral-recall",
                "1",
                "modern_title_only",
                "What is in {recipe_name} from {cookbook_title}?",
            ),
        ),
        models=(
            ModelConfig(
                "example/model",
                RoutingConfig(("Example",), False, "deny", False),
                400,
                0,
                0,
                False,
                PricingCeiling(Decimal("1"), Decimal("2")),
            ),
        ),
        repetitions=1,
        max_budget_usd=Decimal("1"),
        concurrency=1,
        max_retries=0,
    )


def _events(path: Path, finish_reason: str = "stop") -> Path:
    config = _config()
    model = config.models[0]
    rows = [
        {"event": "run_started", "run_id": "run_1"},
        {
            "event": "attempt_started",
            "attempt_id": "attempt_1",
            "case": {
                "recipe_id": "recipe",
                "model_requested": "example/model",
                "prompt_template_id": "neutral-recall",
                "prompt_template_version": "1",
                "provider_policy": {
                    "only": ["Example"],
                    "allow_fallbacks": False,
                    "data_collection": "deny",
                    "zdr": False,
                },
                "parameters": {
                    "max_tokens": model.max_output_tokens,
                    "reasoning": {"enabled": False},
                    "temperature": 0,
                    "seed": 0,
                },
            },
        },
        {
            "event": "attempt_succeeded",
            "attempt_id": "attempt_1",
            "provider_actual": "Example",
            "finish_reason": finish_reason,
        },
        {"event": "run_completed", "run_id": "run_1"},
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def test_match_baseline_accepts_exact_terminal_attempt(tmp_path: Path) -> None:
    matches = match_baseline(
        _config(),
        _events(tmp_path / "attempts.jsonl"),
        recipe_ids=("recipe",),
        model_ids=("example/model",),
    )

    assert matches[0].attempt_id == "attempt_1"
    assert matches[0].eligibility == "eligible"


def test_match_baseline_rejects_truncated_attempt_from_primary_match(tmp_path: Path) -> None:
    matches = match_baseline(
        _config(),
        _events(tmp_path / "attempts.jsonl", "length"),
        recipe_ids=("recipe",),
        model_ids=("example/model",),
    )

    assert matches[0].eligibility == "ineligible_finish_reason"


def test_match_baseline_detects_parameter_drift(tmp_path: Path) -> None:
    config = replace(_config(), models=(replace(_config().models[0], max_output_tokens=500),))

    matches = match_baseline(
        config,
        _events(tmp_path / "attempts.jsonl"),
        recipe_ids=("recipe",),
        model_ids=("example/model",),
    )

    assert matches[0].eligibility == "parameter_mismatch"


def test_match_baseline_requires_completed_run(tmp_path: Path) -> None:
    path = _events(tmp_path / "attempts.jsonl")
    rows = path.read_text(encoding="utf-8").splitlines()[:-1]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    with pytest.raises(BaselineMatchError, match="run_completed"):
        match_baseline(_config(), path, recipe_ids=("recipe",), model_ids=("example/model",))
