from decimal import Decimal
from pathlib import Path

import pytest

from eval_those_models.config import ConfigError, load_experiment

VALID_CONFIG = """
schema_version: 1
experiment_id: smoke-v1
max_budget_usd: "1.00"
repetitions: 2
recipes: [recipe-one]
prompts:
  - id: recall
    version: "1"
    context_group: modern_title_only
    template: 'What is in {recipe_name} from {cookbook_title}?'
models:
  - id: example/model
    routing:
      only: [Example]
      allow_fallbacks: false
      data_collection: deny
    max_output_tokens: 100
    temperature: 0
    seed: 0
    pricing_ceiling:
      input_per_million: "1.00"
      output_per_million: "2.00"
"""


def _write(tmp_path: Path, contents: str) -> Path:
    path = tmp_path / "experiment.yaml"
    path.write_text(contents, encoding="utf-8")
    return path


def test_load_experiment_parses_strict_typed_config(tmp_path: Path) -> None:
    config = load_experiment(_write(tmp_path, VALID_CONFIG))

    assert config.experiment_id == "smoke-v1"
    assert config.repetitions == 2
    assert config.concurrency == 3
    assert config.models[0].routing.only == ("Example",)
    assert str(config.models[0].pricing_ceiling.output_per_million) == "2.00"


def test_load_experiment_rejects_unknown_fields(tmp_path: Path) -> None:
    invalid = VALID_CONFIG.replace("repetitions: 2", "repetitions: 2\nextra: nope")

    with pytest.raises(ConfigError, match="unknown fields"):
        load_experiment(_write(tmp_path, invalid))


def test_load_experiment_rejects_unknown_prompt_variables(tmp_path: Path) -> None:
    invalid = VALID_CONFIG.replace("{recipe_name}", "{reference_text_exact}")

    with pytest.raises(ConfigError, match="unsupported fields"):
        load_experiment(_write(tmp_path, invalid))


def test_load_experiment_parses_auto_web_search_profile(tmp_path: Path) -> None:
    configured = VALID_CONFIG.replace(
        "repetitions: 2",
        """repetitions: 2
tool_profiles:
  - id: web-auto
    web_search:
      engine: auto
      max_uses: 1
      max_results: 3
      max_total_results: 3
      max_characters: 1500
      estimated_input_tokens_per_use: 5000""",
    ).replace(
        'output_per_million: "2.00"',
        'output_per_million: "2.00"\n      web_search_per_request: "0.01"',
    )

    config = load_experiment(_write(tmp_path, configured))

    profile = config.tool_profiles[0]
    assert profile.profile_id == "web-auto"
    assert profile.web_search is not None
    assert profile.web_search.engine == "auto"
    assert profile.web_search.max_uses == 1
    assert config.models[0].pricing_ceiling.web_search_per_request == Decimal("0.01")


def test_load_experiment_rejects_invalid_web_search_engine(tmp_path: Path) -> None:
    configured = VALID_CONFIG.replace(
        "repetitions: 2",
        """repetitions: 2
tool_profiles:
  - id: web-auto
    web_search:
      engine: mystery
      max_uses: 1
      max_results: 3
      max_total_results: 3
      max_characters: 1500
      estimated_input_tokens_per_use: 5000""",
    )

    with pytest.raises(ConfigError, match="engine is not supported"):
        load_experiment(_write(tmp_path, configured))


def test_tracked_smoke_configuration_has_24_calls() -> None:
    config = load_experiment(Path("configs/experiments/smoke-test.yaml"))

    assert (
        len(config.recipe_ids) * len(config.prompts) * len(config.models) * config.repetitions == 24
    )
