from types import SimpleNamespace

import pytest

from eval_those_models import cli
from eval_those_models.cli import build_parser
from eval_those_models.runner import RunError


def test_dataset_validate_command_is_available() -> None:
    args = build_parser().parse_args(["dataset", "validate"])

    assert args.command == "dataset"
    assert args.dataset_command == "validate"
    assert not hasattr(args, "validate_only")


def test_dataset_grading_audit_command_is_available() -> None:
    args = build_parser().parse_args(["dataset", "audit-grading"])

    assert args.command == "dataset"
    assert args.dataset_command == "audit-grading"


def test_plan_command_is_available() -> None:
    args = build_parser().parse_args(["plan", "configs/experiments/smoke-test.yaml"])

    assert args.command == "plan"
    assert args.json is False


def test_run_execute_acknowledgement_defaults_off() -> None:
    args = build_parser().parse_args(["run", "configs/experiments/smoke-test.yaml"])

    assert args.command == "run"
    assert args.execute is False


def test_dirty_checkout_cannot_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=" M changed.py\n"),
    )

    with pytest.raises(RunError, match="clean Git checkout"):
        cli._require_reproducible_checkout()
