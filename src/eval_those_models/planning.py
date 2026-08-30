"""Deterministic experiment expansion, leakage checks, and cost planning."""

from __future__ import annotations

import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from eval_those_models.cases import case_id
from eval_those_models.config import ExperimentConfig, ModelConfig, ToolProfileConfig
from eval_those_models.references import Reference


class PlanningError(ValueError):
    """Raised when an experiment cannot be planned safely."""


AUTO_SEARCH_INPUT_TOKEN_FLOOR = 16_000


@dataclass(frozen=True)
class PlannedCase:
    case_id: str
    experiment_id: str
    recipe_id: str
    rights_context: str
    prompt_template_id: str
    prompt_template_version: str
    rendered_prompt: str
    model_requested: str
    provider_policy: dict[str, Any]
    parameters: dict[str, Any]
    repetition: int
    harness_git_commit: str
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost_usd: Decimal
    tool_profile_id: str = "no-tools"

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "experiment_id": self.experiment_id,
            "recipe_id": self.recipe_id,
            "rights_context": self.rights_context,
            "prompt_template_id": self.prompt_template_id,
            "prompt_template_version": self.prompt_template_version,
            "rendered_prompt": self.rendered_prompt,
            "model_requested": self.model_requested,
            "tool_profile_id": self.tool_profile_id,
            "provider_policy": self.provider_policy,
            "parameters": self.parameters,
            "repetition": self.repetition,
            "harness_git_commit": self.harness_git_commit,
            "estimated_input_tokens": self.estimated_input_tokens,
            "estimated_output_tokens": self.estimated_output_tokens,
            "estimated_cost_usd": str(self.estimated_cost_usd),
        }


@dataclass(frozen=True)
class ExperimentPlan:
    experiment_id: str
    cases: tuple[PlannedCase, ...]
    excluded_incomplete_recipe_ids: tuple[str, ...]
    max_budget_usd: Decimal
    max_retries: int = 0

    @property
    def estimated_cost_usd(self) -> Decimal:
        return sum((case.estimated_cost_usd for case in self.cases), Decimal())

    @property
    def estimated_input_tokens(self) -> int:
        return sum(case.estimated_input_tokens for case in self.cases)

    @property
    def estimated_output_tokens(self) -> int:
        return sum(case.estimated_output_tokens for case in self.cases)

    @property
    def maximum_attempts(self) -> int:
        return len(self.cases) * (self.max_retries + 1)

    @property
    def maximum_cost_with_retries_usd(self) -> Decimal:
        return self.estimated_cost_usd * (self.max_retries + 1)

    def cost_by_model(self) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = defaultdict(Decimal)
        for case in self.cases:
            totals[case.model_requested] += case.estimated_cost_usd
        return dict(totals)

    def as_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "total_cases": len(self.cases),
            "maximum_attempts": self.maximum_attempts,
            "excluded_incomplete_recipe_ids": list(self.excluded_incomplete_recipe_ids),
            "estimated_input_tokens": self.estimated_input_tokens,
            "estimated_output_tokens": self.estimated_output_tokens,
            "estimated_cost_usd": str(self.estimated_cost_usd),
            "maximum_cost_with_retries_usd": str(self.maximum_cost_with_retries_usd),
            "estimated_cost_by_model_usd": {
                model: str(cost) for model, cost in sorted(self.cost_by_model().items())
            },
            "max_budget_usd": str(self.max_budget_usd),
            "cases": [case.as_dict() for case in self.cases],
        }


def build_plan(
    config: ExperimentConfig,
    references: dict[str, Reference],
    harness_git_commit: str,
) -> ExperimentPlan:
    """Expand an experiment deterministically and enforce local safety checks."""
    cases: list[PlannedCase] = []
    excluded: list[str] = []
    for recipe_id in config.recipe_ids:
        reference = references[recipe_id]
        if not reference.ingredient_list_complete:
            excluded.append(recipe_id)
            continue
        for prompt in config.prompts:
            rendered = prompt.template.format(
                recipe_name=reference.recipe_name,
                cookbook_title=reference.cookbook_title,
            )
            if prompt.context_group == "modern_title_only":
                assert_no_reference_leakage(rendered, reference)
            selected_profiles = (
                tuple(
                    profile
                    for profile in config.tool_profiles
                    if profile.profile_id == prompt.tool_profile_id
                )
                if prompt.tool_profile_id is not None
                else config.tool_profiles
            )
            for model in config.models:
                for tool_profile in selected_profiles:
                    for repetition in range(1, config.repetitions + 1):
                        cases.append(
                            _make_case(
                                config,
                                reference,
                                prompt.prompt_id,
                                prompt.version,
                                prompt.context_group,
                                rendered,
                                model,
                                tool_profile,
                                repetition,
                                harness_git_commit,
                            )
                        )
    plan = ExperimentPlan(
        experiment_id=config.experiment_id,
        cases=tuple(cases),
        excluded_incomplete_recipe_ids=tuple(excluded),
        max_budget_usd=config.max_budget_usd,
        max_retries=config.max_retries,
    )
    if not plan.cases:
        raise PlanningError("experiment has no runnable cases")
    if plan.maximum_cost_with_retries_usd > plan.max_budget_usd:
        raise PlanningError(
            f"maximum cost with retries ${plan.maximum_cost_with_retries_usd} exceeds "
            f"configured budget ${plan.max_budget_usd}"
        )
    return plan


def assert_no_reference_leakage(rendered_prompt: str, reference: Reference) -> None:
    """Reject title-only prompts containing exact protected reference material."""
    prompt = _normalize(rendered_prompt)
    protected = [reference.reference_text_exact, *reference.ingredient_lines]
    for value in protected:
        normalized = _normalize(value)
        if normalized and normalized in prompt:
            raise PlanningError(
                f"title-only prompt for {reference.recipe_id!r} contains protected reference text"
            )


def _make_case(
    config: ExperimentConfig,
    reference: Reference,
    prompt_id: str,
    prompt_version: str,
    context_group: str,
    rendered_prompt: str,
    model: ModelConfig,
    tool_profile: ToolProfileConfig,
    repetition: int,
    harness_git_commit: str,
) -> PlannedCase:
    provider_policy = {
        "only": list(model.routing.only),
        "allow_fallbacks": model.routing.allow_fallbacks,
        "data_collection": model.routing.data_collection,
        "zdr": model.routing.zdr,
    }
    parameters: dict[str, Any] = {"max_tokens": model.max_output_tokens}
    if model.reasoning_enabled is not None:
        parameters["reasoning"] = {"enabled": model.reasoning_enabled}
    if model.temperature is not None:
        parameters["temperature"] = model.temperature
    if model.seed is not None:
        parameters["seed"] = model.seed
    search_cost = Decimal()
    search_input_tokens = 0
    if tool_profile.web_search is not None:
        search = tool_profile.web_search
        if model.pricing_ceiling.web_search_per_request <= 0:
            raise PlanningError(
                f"{model.model_id} has web search enabled without a positive search cost ceiling"
            )
        parameters["tools"] = [
            {
                "type": "openrouter:web_search",
                "parameters": {
                    "engine": search.engine,
                    "max_uses": search.max_uses,
                    "max_results": search.max_results,
                    "max_total_results": search.max_total_results,
                    "max_characters": search.max_characters,
                },
            }
        ]
        parameters["max_tool_calls"] = search.max_uses
        search_cost = model.pricing_ceiling.web_search_per_request * search.max_uses
        estimated_tokens_per_use = search.estimated_input_tokens_per_use
        if search.engine in {"auto", "native"}:
            estimated_tokens_per_use = max(
                estimated_tokens_per_use,
                AUTO_SEARCH_INPUT_TOKEN_FLOOR,
            )
        search_input_tokens = estimated_tokens_per_use * search.max_uses
    identity = {
        "experiment_id": config.experiment_id,
        "reference_id": reference.recipe_id,
        "rights_context": reference.rights_context,
        "context_group": context_group,
        "prompt_template_id": prompt_id,
        "prompt_template_version": prompt_version,
        "rendered_prompt": rendered_prompt,
        "model_requested": model.model_id,
        "tool_profile_id": tool_profile.profile_id,
        "provider_policy": provider_policy,
        "parameters": parameters,
        "repetition": repetition,
        "harness_git_commit": harness_git_commit,
    }
    # A token cannot encode less than one UTF-8 byte. Adding fixed chat-message
    # overhead makes this deliberately conservative for budget authorization.
    input_tokens = len(rendered_prompt.encode("utf-8")) + 32 + search_input_tokens
    output_tokens = model.max_output_tokens
    cost = (
        Decimal(input_tokens) * model.pricing_ceiling.input_per_million
        + Decimal(output_tokens) * model.pricing_ceiling.output_per_million
    ) / Decimal(1_000_000) + search_cost
    return PlannedCase(
        case_id=case_id(identity),
        experiment_id=config.experiment_id,
        recipe_id=reference.recipe_id,
        rights_context=reference.rights_context,
        prompt_template_id=prompt_id,
        prompt_template_version=prompt_version,
        rendered_prompt=rendered_prompt,
        model_requested=model.model_id,
        tool_profile_id=tool_profile.profile_id,
        provider_policy=provider_policy,
        parameters=parameters,
        repetition=repetition,
        harness_git_commit=harness_git_commit,
        estimated_input_tokens=input_tokens,
        estimated_output_tokens=output_tokens,
        estimated_cost_usd=cost,
    )


def _normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())
