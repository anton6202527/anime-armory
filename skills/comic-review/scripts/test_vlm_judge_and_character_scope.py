#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VLM 三轴任务包 + 角色一致性覆盖扩展（MON_/裸名字）+ 签收 sha 绑定。

运行：cd skills/comic-review/scripts && python3 -m pytest test_vlm_judge_and_character_scope.py
"""
from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import character_consistency
import vlm_judge

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def make_project(root: Path) -> None:
    chapter = "第1话"
    (root / "脚本" / chapter).mkdir(parents=True)
    (root / "出图" / chapter / "panels").mkdir(parents=True)
    (root / "出图" / "共享" / "图片").mkdir(parents=True)
    (root / "生产数据").mkdir(parents=True)
    script = {
        "panels": [
            {
                "panel_id": "P001",
                "description": "妖物扑向少年。",
                "characters": ["MON_TIGER", "阿福"],
                "references": ["MON_TIGER", "PROP_SWORD"],
                "scene_anchor_id": "LOC_FOREST",
            },
            {
                "panel_id": "P002",
                "description": "少年退到树后。",
                "characters": ["阿福"],
                "references": [],
                "scene_anchor_id": "LOC_FOREST",
            },
        ]
    }
    (root / "脚本" / chapter / "panel_script.json").write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")
    (root / "出图" / chapter / "panels" / "P001.png").write_bytes(PNG_1X1)
    (root / "出图" / chapter / "panels" / "P002.png").write_bytes(PNG_1X1 + b"x")
    (root / "出图" / "共享" / "图片" / "MON_TIGER__anchor.png").write_bytes(PNG_1X1)
    (root / "出图" / "共享" / "图片" / "PROP_SWORD__anchor.png").write_bytes(PNG_1X1)
    registry = {"assets": {"MON_TIGER": {"id": "MON_TIGER", "type": "monster"}, "PROP_SWORD": {"id": "PROP_SWORD", "type": "prop"}}}
    (root / "出图" / "共享" / "identity_registry.json").write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")


def test_vlm_tasks_cover_three_axes_and_stale_verdicts_drop(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    make_project(root)
    chapter = "第1话"

    payload = vlm_judge.build_tasks(root, chapter)
    axes = {task["axis"] for task in payload["tasks"]}
    assert "character_identity" in axes  # MON_ 也进角色轴
    assert "background_continuity" in axes  # 同场景锚相邻格
    assert "prop_identity" in axes

    vlm_judge.write_tasks(root, chapter)
    char_task = next(t for t in payload["tasks"] if t["axis"] == "character_identity")
    good_sha = char_task["panel"]["sha256"]
    evidence = {
        "task_sha256": char_task["task_sha256"],
        "references_sha256": char_task["references_sha256"],
        "evaluator": {"model": "Test VLM", "version": "2026-07-14"},
    }
    (root / "生产数据" / f"comic_vlm_judge_verdicts_{chapter}.json").write_text(
        json.dumps(
            {
                "verdicts": [
                    {"task_id": char_task["task_id"], "panel_sha256": good_sha, "scores": {"face": 2}, "verdict": "suspect", **evidence},
                    {"task_id": char_task["task_id"] + "_stale", "panel_sha256": "0" * 64, "scores": {"face": 1}},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    suspects = vlm_judge.suspect_verdicts(root, chapter, "character_identity")
    assert len(suspects) == 1
    assert suspects[0]["low_scores"] == ["face=2"]

    # 重抽该格（内容变化）→ 重建任务包后旧裁决 sha 不匹配，自动作废
    (root / "出图" / chapter / "panels" / "P001.png").write_bytes(PNG_1X1 + b"rerolled")
    vlm_judge.write_tasks(root, chapter)
    assert vlm_judge.suspect_verdicts(root, chapter, "character_identity") == []


def test_vlm_verdict_without_complete_sha_or_evaluator_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    make_project(root)
    chapter = "第1话"
    vlm_judge.write_tasks(root, chapter)
    task = vlm_judge.load_json(vlm_judge.tasks_path(root, chapter), {})["tasks"][0]
    (root / "生产数据" / f"comic_vlm_judge_verdicts_{chapter}.json").write_text(
        json.dumps({"verdicts": [{
            "task_id": task["task_id"],
            "panel_sha256": task["panel"]["sha256"],
            "scores": {"face": 5},
            "verdict": "pass",
        }]}),
        encoding="utf-8",
    )
    assert vlm_judge.load_verdicts(root, chapter) == {}


def test_character_scope_covers_mon_and_flags_unbound_names(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    make_project(root)

    report = character_consistency.analyze(root, "第1话")

    char_ids = {row["character_id"] for row in report["characters"]}
    assert "MON_TIGER" in char_ids
    codes = {f["code"] for f in report["findings"]}
    assert "named_character_without_ref" in codes
    unbound = next(f for f in report["findings"] if f["code"] == "named_character_without_ref")
    assert unbound["character_id"] == "阿福"
    assert "P001" in unbound["reason"] and "P002" in unbound["reason"]


def test_scene_prop_report_builds_groups_and_flags_missing_prop_ref(tmp_path: Path) -> None:
    import scene_prop_consistency

    root = tmp_path / "项目"
    make_project(root)
    # 移除 PROP_SWORD 参考图 → 应报 prop_reference_missing
    (root / "出图" / "共享" / "图片" / "PROP_SWORD__anchor.png").unlink()

    report = scene_prop_consistency.analyze(root, "第1话")

    anchors = {row["scene_anchor_id"] for row in report["scenes"]}
    assert "LOC_FOREST" in anchors
    prop_ids = {row["prop_id"] for row in report["props"]}
    assert "PROP_SWORD" in prop_ids
    codes = {f["code"] for f in report["findings"]}
    assert "prop_reference_missing" in codes
    assert "scene_anchor_reference_missing" in codes  # LOC_FOREST 无锚点参考图


def test_acceptance_requires_matching_sha_and_rejects_block(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    (root / "生产数据").mkdir(parents=True)
    (root / "出图" / "第1话" / "panels").mkdir(parents=True)
    panel = root / "出图" / "第1话" / "panels" / "P001.png"
    panel.write_bytes(PNG_1X1)
    sha = hashlib.sha256(PNG_1X1).hexdigest()
    (root / "生产数据" / "character_consistency_acceptance_第1话.json").write_text(
        json.dumps(
            {
                "accepted_findings": [
                    {"code": "face_fingerprint_low", "panel_id": "P001", "reason": "低机位", "artifact_sha256": sha},
                    {"code": "face_fingerprint_low", "panel_id": "P002", "reason": "旧签收", "artifact_sha256": "f" * 64},
                    {"code": "character_reference_missing", "panel_id": "P003", "reason": "想洗掉结构块"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    findings = [
        {"severity": "warn", "code": "face_fingerprint_low", "panel_id": "P001", "artifact": "出图/第1话/panels/P001.png"},
        {"severity": "warn", "code": "face_fingerprint_low", "panel_id": "P002", "artifact": "出图/第1话/panels/P001.png"},
        {"severity": "block", "code": "character_reference_missing", "panel_id": "P003", "artifact": "出图/共享/identity_registry.json"},
    ]
    notes: list[str] = []

    character_consistency.apply_manual_acceptances(root, "第1话", findings, notes)

    assert findings[0]["severity"] == "info"  # sha 匹配 → 签收生效
    assert findings[1]["severity"] == "warn"  # sha 不匹配 → 签收失效
    assert findings[2]["severity"] == "block"  # block 级不可签收
    joined = "；".join(notes)
    assert "自动失效" in joined
    assert "不可签收" in joined
