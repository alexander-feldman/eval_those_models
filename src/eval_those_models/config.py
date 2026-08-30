"""Strict, versioned experiment configuration loading."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when an experiment configuration is invalid."""


@dataclass(frozen=True)
class PromptConfig:
    prompt_id: str
    version: str
    context_group: str
    template: str
    tool_profile_id: str | None = None


@dataclass(frozen=True)
class RoutingConfig:
    only: tuple[str, ...]
    allow_fallbacks: bool
    data_collection: str
    zdr: bool


@dataclass(frozen=True)
class PricingCeiling:
    input_per_million: Decimal
    output_per_million: Decimal
    web_search_per_request: Decimal = Decimal()


@dataclass(frozen=True)
class WebSearchConfig:
    engine: str
    max_uses: int
    max_results: int
    max_total_results: int
    max_characters: int
    estimated_input_tokens_per_use: int
    max_cost_usd: Decimal | None = None


@dataclass(frozen=True)
class ToolProfileConfig:
    profile_id: str
    web_search: WebSearchConfig | None


@dataclass(frozen=True)
class ModelConfig:
    model_id: str
    routing: RoutingConfig
    max_output_tokens: int
    temperature: float | None
    seed: int | None
    reasoning_enabled: bool | None
    pricing_ceiling: PricingCeiling


@dataclass(frozen=True)
class ExperimentConfig:
    schema_version: int
    experiment_id: str
    recipe_ids: tuple[str, ...]
    prompts: tuple[PromptConfig, ...]
    models: tuple[ModelConfig, ...]
    repetitions: int
    max_budget_usd: Decimal
    concurrency: int
    max_retries: int
    tool_profiles: tuple[ToolProfileConfig, ...] = (ToolProfileConfig("no-tools", None),)


def load_experiment(path: Path) -> ExperimentConfig:
    """Load a YAML experiment file and reject unknown or malformed fields."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"could not read configuration {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from exc
    root = _mapping(raw, "configuration")
    _keys(
        root,
        required={
            "schema_version",
            "experiment_id",
            "recipes",
            "prompts",
            "models",
            "repetitions",
            "max_budget_usd",
        },
        optional={"concurrency", "max_retries", "tool_profiles"},
        where="configuration",
    )
    schema_version = _positive_int(root["schema_version"], "schema_version")
    if schema_version != 1:
        raise ConfigError(f"unsupported schema_version {schema_version}; expected 1")

    recipe_ids = tuple(
        _nonempty_string(value, f"recipes[{index}]")
        for index, value in enumerate(_list(root["recipes"], "recipes"))
    )
    if len(set(recipe_ids)) != len(recipe_ids):
        raise ConfigError("recipes contains duplicate IDs")

    prompts = tuple(
        _parse_prompt(value, index) for index, value in enumerate(_list(root["prompts"], "prompts"))
    )
    models = tuple(
        _parse_model(value, index) for index, value in enumerate(_list(root["models"], "models"))
    )
    tool_profiles = tuple(
        _parse_tool_profile(value, index)
        for index, value in enumerate(_list(root.get("tool_profiles", []), "tool_profiles"))
    ) or (ToolProfileConfig("no-tools", None),)
    if not recipe_ids or not prompts or not models:
        raise ConfigError("recipes, prompts, and models must each contain at least one item")
    if len({(prompt.prompt_id, prompt.version) for prompt in prompts}) != len(prompts):
        raise ConfigError("prompts contains duplicate ID/version pairs")
    if len({model.model_id for model in models}) != len(models):
        raise ConfigError("models contains duplicate model IDs")
    if len({profile.profile_id for profile in tool_profiles}) != len(tool_profiles):
        raise ConfigError("tool_profiles contains duplicate IDs")
    profile_ids = {profile.profile_id for profile in tool_profiles}
    for prompt in prompts:
        if prompt.tool_profile_id is not None and prompt.tool_profile_id not in profile_ids:
            raise ConfigError(
                f"prompt {prompt.prompt_id!r} references unknown tool profile "
                f"{prompt.tool_profile_id!r}"
            )

    budget = _decimal(root["max_budget_usd"], "max_budget_usd")
    if budget <= 0:
        raise ConfigError("max_budget_usd must be greater than zero")
    max_retries = _nonnegative_int(root.get("max_retries", 2), "max_retries")
    return ExperimentConfig(
        schema_version=schema_version,
        experiment_id=_identifier(root["experiment_id"], "experiment_id"),
        recipe_ids=recipe_ids,
        prompts=prompts,
        models=models,
        tool_profiles=tool_profiles,
        repetitions=_positive_int(root["repetitions"], "repetitions"),
        max_budget_usd=budget,
        concurrency=_bounded_int(root.get("concurrency", 3), "concurrency", 1, 10),
        max_retries=max_retries,
    )


def _parse_prompt(value: Any, index: int) -> PromptConfig:
    where = f"prompts[{index}]"
    item = _mapping(value, where)
    _keys(
        item,
        {"id", "version", "context_group", "template"},
        {"tool_profile"},
        where,
    )
    template = _nonempty_string(item["template"], f"{where}.template")
    allowed_fields = {"recipe_name", "cookbook_title"}
    fields = {
        part.split("!", 1)[0].split(":", 1)[0] for part in template.split("{")[1:] if "}" in part
    }
    fields = {field.split("}", 1)[0] for field in fields}
    unknown_fields = fields - allowed_fields
    if unknown_fields:
        raise ConfigError(f"{where}.template has unsupported fields: {sorted(unknown_fields)}")
    if not fields:
        raise ConfigError(f"{where}.template must contain at least one template field")
    try:
        template.format(recipe_name="recipe", cookbook_title="cookbook")
    except (KeyError, ValueError) as exc:
        raise ConfigError(f"{where}.template is invalid: {exc}") from exc
    return PromptConfig(
        prompt_id=_identifier(item["id"], f"{where}.id"),
        version=_nonempty_string(item["version"], f"{where}.version"),
        context_group=_identifier(item["context_group"], f"{where}.context_group"),
        template=template,
        tool_profile_id=(
            _identifier(item["tool_profile"], f"{where}.tool_profile")
            if "tool_profile" in item
            else None
        ),
    )


def _parse_tool_profile(value: Any, index: int) -> ToolProfileConfig:
    where = f"tool_profiles[{index}]"
    item = _mapping(value, where)
    _keys(item, {"id", "web_search"}, set(), where)
    raw_search = item["web_search"]
    if raw_search is None:
        return ToolProfileConfig(_identifier(item["id"], f"{where}.id"), None)
    search = _mapping(raw_search, f"{where}.web_search")
    _keys(
        search,
        {
            "engine",
            "max_uses",
            "max_results",
            "max_total_results",
            "max_characters",
            "estimated_input_tokens_per_use",
        },
        {"max_cost_usd"},
        f"{where}.web_search",
    )
    engine = _nonempty_string(search["engine"], f"{where}.web_search.engine")
    if engine not in {"auto", "native", "exa", "firecrawl", "parallel", "perplexity"}:
        raise ConfigError(f"{where}.web_search.engine is not supported")
    max_results = _bounded_int(search["max_results"], f"{where}.web_search.max_results", 1, 25)
    max_total_results = _bounded_int(
        search["max_total_results"], f"{where}.web_search.max_total_results", 1, 750
    )
    if max_total_results < max_results:
        raise ConfigError(f"{where}.web_search.max_total_results must be at least max_results")
    max_cost = (
        _decimal(search["max_cost_usd"], f"{where}.web_search.max_cost_usd")
        if "max_cost_usd" in search
        else None
    )
    if max_cost is not None and max_cost <= 0:
        raise ConfigError(f"{where}.web_search.max_cost_usd must be greater than zero")
    return ToolProfileConfig(
        profile_id=_identifier(item["id"], f"{where}.id"),
        web_search=WebSearchConfig(
            engine=engine,
            max_uses=_bounded_int(search["max_uses"], f"{where}.web_search.max_uses", 1, 30),
            max_results=max_results,
            max_total_results=max_total_results,
            max_characters=_bounded_int(
                search["max_characters"], f"{where}.web_search.max_characters", 1, 100_000
            ),
            estimated_input_tokens_per_use=_positive_int(
                search["estimated_input_tokens_per_use"],
                f"{where}.web_search.estimated_input_tokens_per_use",
            ),
            max_cost_usd=max_cost,
        ),
    )


def _parse_model(value: Any, index: int) -> ModelConfig:
    where = f"models[{index}]"
    item = _mapping(value, where)
    _keys(
        item,
        {"id", "routing", "max_output_tokens", "pricing_ceiling"},
        {"temperature", "seed", "reasoning_enabled"},
        where,
    )
    routing_raw = _mapping(item["routing"], f"{where}.routing")
    _keys(
        routing_raw,
        {"only", "allow_fallbacks", "data_collection"},
        {"zdr"},
        f"{where}.routing",
    )
    only = tuple(
        _nonempty_string(provider, f"{where}.routing.only[{provider_index}]")
        for provider_index, provider in enumerate(
            _list(routing_raw["only"], f"{where}.routing.only")
        )
    )
    if not only:
        raise ConfigError(f"{where}.routing.only must name at least one provider")
    data_collection = _nonempty_string(
        routing_raw["data_collection"], f"{where}.routing.data_collection"
    )
    if data_collection not in {"allow", "deny"}:
        raise ConfigError(f"{where}.routing.data_collection must be 'allow' or 'deny'")

    pricing_raw = _mapping(item["pricing_ceiling"], f"{where}.pricing_ceiling")
    _keys(
        pricing_raw,
        {"input_per_million", "output_per_million"},
        {"web_search_per_request"},
        f"{where}.pricing_ceiling",
    )
    pricing = PricingCeiling(
        input_per_million=_decimal(
            pricing_raw["input_per_million"], f"{where}.pricing_ceiling.input_per_million"
        ),
        output_per_million=_decimal(
            pricing_raw["output_per_million"], f"{where}.pricing_ceiling.output_per_million"
        ),
        web_search_per_request=_decimal(
            pricing_raw.get("web_search_per_request", 0),
            f"{where}.pricing_ceiling.web_search_per_request",
        ),
    )
    if (
        pricing.input_per_million < 0
        or pricing.output_per_million < 0
        or pricing.web_search_per_request < 0
    ):
        raise ConfigError(f"{where}.pricing_ceiling values cannot be negative")

    temperature_raw = item.get("temperature")
    if temperature_raw is not None and (
        isinstance(temperature_raw, bool) or not isinstance(temperature_raw, (int, float))
    ):
        raise ConfigError(f"{where}.temperature must be a number or null")
    seed_raw = item.get("seed")
    if seed_raw is not None and (isinstance(seed_raw, bool) or not isinstance(seed_raw, int)):
        raise ConfigError(f"{where}.seed must be an integer or null")
    return ModelConfig(
        model_id=_nonempty_string(item["id"], f"{where}.id"),
        routing=RoutingConfig(
            only=only,
            allow_fallbacks=_boolean(
                routing_raw["allow_fallbacks"], f"{where}.routing.allow_fallbacks"
            ),
            data_collection=data_collection,
            zdr=_boolean(routing_raw.get("zdr", False), f"{where}.routing.zdr"),
        ),
        max_output_tokens=_positive_int(item["max_output_tokens"], f"{where}.max_output_tokens"),
        temperature=float(temperature_raw) if temperature_raw is not None else None,
        seed=seed_raw,
        reasoning_enabled=(
            _boolean(item["reasoning_enabled"], f"{where}.reasoning_enabled")
            if "reasoning_enabled" in item
            else None
        ),
        pricing_ceiling=pricing,
    )


def _keys(value: dict[str, Any], required: set[str], optional: set[str], where: str) -> None:
    missing = required - value.keys()
    unknown = value.keys() - required - optional
    if missing:
        raise ConfigError(f"{where} is missing required fields: {sorted(missing)}")
    if unknown:
        raise ConfigError(f"{where} has unknown fields: {sorted(unknown)}")


def _mapping(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ConfigError(f"{where} must be a mapping")
    return value


def _list(value: Any, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise ConfigError(f"{where} must be a list")
    return value


def _nonempty_string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{where} must be a non-empty string")
    return value.strip()


def _identifier(value: Any, where: str) -> str:
    result = _nonempty_string(value, where)
    if not all(character.isalnum() or character in "-_." for character in result):
        raise ConfigError(f"{where} may contain only letters, numbers, '-', '_', and '.'")
    return result


def _boolean(value: Any, where: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{where} must be true or false")
    return value


def _positive_int(value: Any, where: str) -> int:
    return _bounded_int(value, where, 1, 2**31 - 1)


def _nonnegative_int(value: Any, where: str) -> int:
    return _bounded_int(value, where, 0, 10)


def _bounded_int(value: Any, where: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ConfigError(f"{where} must be an integer between {minimum} and {maximum}")
    return value


def _decimal(value: Any, where: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ConfigError(f"{where} must be a decimal number")
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ConfigError(f"{where} must be a decimal number") from exc
