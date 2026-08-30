from eval_those_models.cli import build_parser


def test_dataset_validate_command_is_available() -> None:
    args = build_parser().parse_args(["dataset", "validate"])

    assert args.command == "dataset"
    assert args.dataset_command == "validate"
    assert not hasattr(args, "validate_only")
