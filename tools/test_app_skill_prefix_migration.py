#!/usr/bin/env python3
"""Compatibility checks for the Web/canvas app-* skill prefix migration."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize(
    ("script", "schema", "skill", "legacy_names"),
    (
        (
            "skills/app/app-script-workbench/scripts/workbench.py",
            "app-script-workbench/v1",
            "app-script-workbench",
            (("n2d-script-workbench/v1", "n2d-script-workbench"), ("app-n2d-script-workbench/v1", "app-n2d-script-workbench")),
        ),
        (
            "skills/app/app-character-turnaround/scripts/turnaround.py",
            "app-character-turnaround/v1",
            "app-character-turnaround",
            (("n2d-character-turnaround/v1", "n2d-character-turnaround"), ("app-n2d-character-turnaround/v1", "app-n2d-character-turnaround")),
        ),
        (
            "skills/app/app-first-frame-video/scripts/first_frame_video.py",
            "app-first-frame-video/v1",
            "app-first-frame-video",
            (("n2d-first-frame-video/v1", "n2d-first-frame-video"), ("app-n2d-first-frame-video/v1", "app-n2d-first-frame-video")),
        ),
        (
            "skills/app/app-audio-video/scripts/audio_video.py",
            "app-audio-video/v1",
            "app-audio-video",
            (("n2d-audio-video/v1", "n2d-audio-video"), ("app-n2d-audio-video/v1", "app-n2d-audio-video")),
        ),
    ),
)
def test_legacy_json_is_normalized_and_rewritten(
    tmp_path: Path,
    script: str,
    schema: str,
    skill: str,
    legacy_names: tuple[tuple[str, str], ...],
) -> None:
    module_path = REPO / script
    spec = importlib.util.spec_from_file_location(f"migration_{module_path.stem}_{skill}", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for index, (legacy_schema, legacy_skill) in enumerate(legacy_names):
        payload_path = tmp_path / f"legacy-{index}.json"
        payload_path.write_text(
            json.dumps({"schema": legacy_schema, "skill": legacy_skill}),
            encoding="utf-8",
        )

        payload = module.read_json(payload_path)
        assert payload["schema"] == schema
        assert payload["skill"] == skill

        module.write_json(payload_path, payload)
        persisted = json.loads(payload_path.read_text(encoding="utf-8"))
        assert persisted["schema"] == schema
        assert persisted["skill"] == skill
