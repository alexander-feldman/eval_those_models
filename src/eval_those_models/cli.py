"""Command-line interface for the evaluation harness."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from eval_those_models import __version__
from eval_those_models.config import ConfigError, ExperimentConfig, load_experiment
from eval_those_models.dataset import importer
from eval_those_models.planning import ExperimentPlan, PlanningError, build_plan
from eval_those_models.providers.openrouter import OpenRouterClient, OpenRouterError
from eval_those_models.references import ReferenceError, load_references
from eval_those_models.runner import RunError, run_experiment


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eval-those-models")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    dataset = commands.add_parser("dataset", help="build or validate private reference data")
    operation = dataset.add_subparsers(dest="dataset_command", required=True)

    dataset_options = importer.build_parser(include_operation=False)
    build = operation.add_parser("build", parents=[dataset_options], add_help=False)
    build.set_defaults(handler=_run_dataset_build)

    validate = operation.add_parser("validate", parents=[dataset_options], add_help=False)
    validate.set_defaults(handler=_run_dataset_validate)

    plan = commands.add_parser("plan", help="expand and validate an experiment without dispatching")
    _add_experiment_arguments(plan)
    plan.add_argument("--json", action="store_true", help="print the complete plan as JSON")
    plan.set_defaults(handler=_run_plan)

    run = commands.add_parser("run", help="execute a budgeted experiment through OpenRouter")
    _add_experiment_arguments(run)
    run.add_argument(
        "--artifacts-dir",
        type=Path,
        default=Path("artifacts/runs"),
        help="private output directory (default: artifacts/runs)",
    )
    run.add_argument(
        "--execute",
        action="store_true",
        help="required acknowledgement that this command makes paid API requests",
    )
    run.set_defaults(handler=_run_experiment)
    return parser


def _run_dataset_build(args: argparse.Namespace) -> int:
    args.validate_only = False
    return importer.run(args)


def _run_dataset_validate(args: argparse.Namespace) -> int:
    args.validate_only = True
    return importer.run(args)


def _add_experiment_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("config", type=Path, help="versioned experiment YAML")
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/private/cookbook_eval.sqlite"),
        help="private reference SQLite database",
    )


def _load_plan(args: argparse.Namespace) -> tuple[ExperimentConfig, ExperimentPlan]:
    config = load_experiment(args.config)
    references = load_references(args.database, config.recipe_ids)
    return config, build_plan(config, references, _git_commit())


def _run_plan(args: argparse.Namespace) -> int:
    _, plan = _load_plan(args)
    if args.json:
        print(json.dumps(plan.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"Experiment: {plan.experiment_id}")
        print(f"Cases: {len(plan.cases)}")
        print(f"Maximum attempts including retries: {plan.maximum_attempts}")
        print(f"Excluded incomplete references: {len(plan.excluded_incomplete_recipe_ids)}")
        print(
            f"Estimated tokens: {plan.estimated_input_tokens} input, "
            f"{plan.estimated_output_tokens} output"
        )
        for model, cost in sorted(plan.cost_by_model().items()):
            print(f"Estimated cost ({model}): ${cost}")
        print(f"Estimated total cost: ${plan.estimated_cost_usd}")
        print(f"Maximum cost including retries: ${plan.maximum_cost_with_retries_usd}")
        print(f"Maximum authorized spend: ${plan.max_budget_usd}")
        policies = {json.dumps(case.provider_policy, sort_keys=True) for case in plan.cases}
        print("Provider policies:")
        for policy in sorted(policies):
            print(f"  {policy}")
    return 0


def _run_experiment(args: argparse.Namespace) -> int:
    if not args.execute:
        raise RunError("refusing paid API requests without --execute")
    _require_reproducible_checkout()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RunError("OPENROUTER_API_KEY is not set")
    config, plan = _load_plan(args)
    summary = run_experiment(
        config,
        plan,
        OpenRouterClient(api_key),
        args.artifacts_dir,
    )
    print(f"Run: {summary.run_id}")
    print(f"Artifacts: {summary.run_directory}")
    print(f"Cases: {summary.succeeded} succeeded, {summary.failed} failed")
    print(f"Attempts: {summary.attempts}")
    print(f"Reported cost: ${summary.reported_cost_usd}")
    return 1 if summary.failed else 0


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    commit = result.stdout.strip()
    return commit if result.returncode == 0 and commit else "unknown"


def _require_reproducible_checkout() -> None:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        check=False,
        capture_output=True,
        text=True,
    )
    if status.returncode != 0:
        raise RunError("run must execute from a Git checkout")
    if status.stdout.strip():
        raise RunError("run requires a clean Git checkout so case IDs identify the exact harness")


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return args.handler(args)
    except (ConfigError, OpenRouterError, PlanningError, ReferenceError, RunError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
