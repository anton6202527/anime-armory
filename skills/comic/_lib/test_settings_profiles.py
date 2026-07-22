#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from settings import (  # noqa: E402
    PRODUCTION_PROFILE_PRESETS,
    get_setting,
    set_project_setting,
    validate_setting,
)


def test_all_profile_expansions_are_schema_valid() -> None:
    for profile, fields in PRODUCTION_PROFILE_PRESETS.items():
        assert validate_setting("生产档位", profile, family="comic")["level"] == "ok"
        assert fields
        for key, value in fields.items():
            assert validate_setting(key, value, family="comic")["level"] == "ok"


def test_setting_profile_updates_linked_consistency_floor(tmp_path: Path) -> None:
    root = tmp_path / "画漫" / "作品"
    root.mkdir(parents=True)
    (root / "_settings-marker").write_text("comic", encoding="utf-8")

    set_project_setting(str(root), "生产档位", "连载高一致性")

    assert get_setting(str(root), "生产档位") == "连载高一致性"
    assert get_setting(str(root), "定妆级别") == "长线专门定妆+高一致性"
    assert get_setting(str(root), "年龄形态继承") == "开启"
    assert get_setting(str(root), "角色一致性硬闸") == "开启"
    text = (root / "_设置.md").read_text(encoding="utf-8")
    assert "已应用 5 项联动设置" in text


def test_default_profile_is_serial_and_consistency_gate_is_on(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    assert get_setting(str(root), "生产档位") == "连载标准"
    assert get_setting(str(root), "年龄形态继承") == "开启"
    assert get_setting(str(root), "角色一致性硬闸") == "开启"
    assert get_setting(str(root), "生图分辨率策略") == "后端最高可达"


def test_builtin_imagegen_channel_is_a_valid_explicit_choice() -> None:
    assert validate_setting("生图渠道", "内置 imagegen", family="comic")["level"] == "ok"
    assert validate_setting("生图AI", "Codex内置imagegen", family="comic")["level"] == "ok"
