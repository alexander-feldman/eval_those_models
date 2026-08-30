from eval_those_models.cli import build_parser


def test_dataset_validate_command_is_available() -> None:
    args = build_parser().parse_args(["dataset", "validate"])

    assert args.command == "dataset"
    assert args.dataset_command == "validate"
    assert not hasattr(args, "validate_only")


def test_plan_command_is_available() -> None:
    args = build_parser().parse_args(["plan", "configs/experiments/smoke-test.yaml"])

    assert args.command == "plan"
    assert args.json is False


def test_run_execute_acknowledgement_defaults_off() -> None:
    args = build_parser().parse_args(["run", "configs/experiments/smoke-test.yaml"])

    assert args.command == "run"
    assert args.execute is False
