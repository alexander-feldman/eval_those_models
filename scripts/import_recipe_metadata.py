#!/usr/bin/env python3
"""Compatibility wrapper for the packaged dataset importer."""

from __future__ import annotations

from pathlib import Path

from eval_those_models.dataset.importer import main

if __name__ == "__main__":
    raise SystemExit(main(project_root=Path(__file__).resolve().parents[1]))
