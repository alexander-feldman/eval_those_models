"""Command-line interface for the evaluation harness."""

from __future__ import annotations

import argparse

from eval_those_models import __version__
from eval_those_models.dataset import importer


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
    return parser


def _run_dataset_build(args: argparse.Namespace) -> int:
    args.validate_only = False
    return importer.run(args)


def _run_dataset_validate(args: argparse.Namespace) -> int:
    args.validate_only = True
    return importer.run(args)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)
