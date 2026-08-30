from dataclasses import replace
from decimal import Decimal

import pytest

from eval_those_models.config import (
    ExperimentConfig,
    ModelConfig,
    PricingCeiling,
    PromptConfig,
    RoutingConfig,
    ToolProfileConfig,
    WebSearchConfig,
)
from eval_those_models.planning import PlanningError, build_plan
from eval_those_models.references import Reference


def _model(model_id: str = "example/model") -> ModelConfig:
    return ModelConfig(
        model_id=model_id,
        routing=RoutingConfig(("Example",), False, "deny", False),
        max_output_tokens=100,
        temperature=0,
        seed=0,
        reasoning_enabled=False,
        pricing_ceiling=PricingCeiling(Decimal("1"), Decimal("2")),
    )


def _config() -> ExperimentConfig:
    return ExperimentConfig(
        schema_version=1,
        experiment_id="smoke",
        recipe_ids=("complete", "incomplete"),
        prompts=(
            PromptConfig(
                "recall",
                "1",
                "modern_title_only",
                "What is in {recipe_name} from {cookbook_title}?",
            ),
        ),
        models=(_model(),),
        repetitions=2,
        max_budget_usd=Decimal("1"),
        concurrency=1,
        max_retries=2,
    )


def _reference(recipe_id: str, complete: bool = True) -> Reference:
    return Reference(
        recipe_id=recipe_id,
        recipe_name=f"Recipe {recipe_id}",
        cookbook_title="A Cookbook",
        rights_context="modern_copyrighted",
        ingredient_list_complete=complete,
        reference_text_exact="1 cup secret\n2 tsp hidden",
        ingredient_lines=("1 cup secret", "2 tsp hidden"),
    )


def test_plan_is_deterministic_and_excludes_incomplete_references() -> None:
    config = _config()
    references = {
        "complete": _reference("complete"),
        "incomplete": _reference("incomplete", False),
    }

    first = build_plan(config, references, "abc123")
    second = build_plan(config, references, "abc123")

    assert [case.case_id for case in first.cases] == [case.case_id for case in second.cases]
    assert len(first.cases) == 2
    assert first.excluded_incomplete_recipe_ids == ("incomplete",)
    assert first.cases[0].case_id != first.cases[1].case_id
    assert "secret" not in str(first.as_dict())


def test_plan_rejects_ground_truth_in_a_title_only_prompt() -> None:
    config = replace(
        _config(),
        recipe_ids=("complete",),
        prompts=(
            PromptConfig(
                "leaky",
                "1",
                "modern_title_only",
                "Please reproduce {cookbook_title} for {recipe_name}",
            ),
        ),
    )
    reference = replace(_reference("complete"), cookbook_title="1 cup secret")

    with pytest.raises(PlanningError, match="protected reference text"):
        build_plan(config, {"complete": reference}, "abc123")


def test_plan_rejects_worst_case_cost_above_budget() -> None:
    config = replace(
        _config(),
        recipe_ids=("complete",),
        max_budget_usd=Decimal("0.000001"),
    )

    with pytest.raises(PlanningError, match="exceeds.*configured budget"):
        build_plan(config, {"complete": _reference("complete")}, "abc123")


def test_case_id_changes_with_harness_commit() -> None:
    config = replace(_config(), recipe_ids=("complete",), repetitions=1)
    references = {"complete": _reference("complete")}

    first = build_plan(config, references, "abc123")
    second = build_plan(config, references, "def456")

    assert first.cases[0].case_id != second.cases[0].case_id


def test_plan_adds_web_search_to_request_and_budget() -> None:
    model = replace(
        _model(),
        pricing_ceiling=PricingCeiling(Decimal("1"), Decimal("2"), Decimal("0.01")),
    )
    config = replace(
        _config(),
        recipe_ids=("complete",),
        repetitions=1,
        models=(model,),
        tool_profiles=(
            ToolProfileConfig(
                "web-auto",
                WebSearchConfig("auto", 1, 3, 3, 1500, 5000),
            ),
        ),
    )

    plan = build_plan(config, {"complete": _reference("complete")}, "abc123")

    case = plan.cases[0]
    assert case.tool_profile_id == "web-auto"
    assert case.parameters["tools"] == [
        {
            "type": "openrouter:web_search",
            "parameters": {
                "engine": "auto",
                "max_uses": 1,
                "max_results": 3,
                "max_total_results": 3,
                "max_characters": 1500,
            },
        }
    ]
    assert case.parameters["max_tool_calls"] == 1
    assert case.estimated_input_tokens >= 5000
    assert case.estimated_cost_usd > Decimal("0.01")


def test_plan_requires_search_cost_ceiling_when_search_is_enabled() -> None:
    config = replace(
        _config(),
        recipe_ids=("complete",),
        repetitions=1,
        tool_profiles=(
            ToolProfileConfig(
                "web-auto",
                WebSearchConfig("auto", 1, 3, 3, 1500, 5000),
            ),
        ),
    )

    with pytest.raises(PlanningError, match="search cost ceiling"):
        build_plan(config, {"complete": _reference("complete")}, "abc123")
