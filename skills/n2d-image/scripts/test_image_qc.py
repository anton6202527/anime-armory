"""image_qc 单测——纯函数 + lint + registry 合法性 + 汇总。

从本目录跑：
  cd skills/n2d-image/scripts && python3 -m pytest test_image_qc.py
"""
from __future__ import annotations

import contextlib
import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).with_name("image_qc.py")
spec = importlib.util.spec_from_file_location("image_qc", SCRIPT)
image_qc = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(image_qc)


def test_worst_verdict_severity_order() -> None:
    assert image_qc.worst_verdict([]) == "ok"
    assert image_qc.worst_verdict(["ok", "warn", "ok"]) == "warn"
    assert image_qc.worst_verdict(["warn", "block"]) == "block"
    assert image_qc.worst_verdict(["ok", "noface"]) == "noface"   # noface 重于 ok 轻于 warn
    assert image_qc.worst_verdict(["noface", "warn"]) == "warn"


def test_count_verdicts_tallies_by_field() -> None:
    rows = [{"verdict": "block"}, {"verdict": "warn"}, {"verdict": "warn"},
            {"verdict": "ok"}, {"verdict": "noface"}, {"no_verdict": 1}]
    assert image_qc.count_verdicts(rows) == {"block": 1, "warn": 2, "noface": 1, "ok": 1}
    assert image_qc.count_verdicts([]) == {"block": 0, "warn": 0, "noface": 0, "ok": 0}


def test_split_shot_blocks() -> None:
    md = "前言\n## Clip 01 起\n参考图\n## Clip 02 承\n身份\n尾"
    blocks = image_qc.split_shot_blocks(md)
    assert [b["label"] for b in blocks] == ["Clip 01 起", "Clip 02 承"]
    assert "参考图" in blocks[0]["body"]
    assert "前言" not in blocks[0]["body"]   # 标题前的内容不计入任何镜块


def test_load_registry_ids(tmp_path: Path) -> None:
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "identity_registry.json").write_text(json.dumps({
        "characters": [
            {"id": "CHAR_01", "forms": [{"form": "常态"}, {"form": "觉醒态"}]},
            {"id": "CHAR_03", "forms": [{"form": "人皮态"}]},
            {"id": "CHAR_SHEN", "forms": [{"form": "受难"}]},
        ]
    }, ensure_ascii=False), encoding="utf-8")
    ids = image_qc.load_registry_ids(tmp_path)
    assert ids == {
        "CHAR_01", "CHAR_01/常态", "CHAR_01/觉醒态",
        "CHAR_03", "CHAR_03/人皮态",
        "CHAR_SHEN", "CHAR_SHEN/受难",
    }
    # 缺 registry → None（lint 跳过合法性，不误报）
    assert image_qc.load_registry_ids(tmp_path / "nope") is None


def test_load_registry_forms_does_not_turn_reference_metadata_into_aliases(tmp_path: Path) -> None:
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "identity_registry.json").write_text(json.dumps({
        "characters": [{
            "id": "CHAR_04",
            "name": "姜月初",
            "forms": [{
                "form": "常态",
                "asset_key": "姜月初_常态",
                "reference_group": {
                    "expression": {
                        "path": "出图/共享/图片/定妆_CHAR_04__常态_表情_克制.png",
                        "status": "planned",
                        "emotion": "克制",
                        "layout": "two_by_three_expression_sheet_v1",
                        "derivation": {
                            "method": "controlled_multiref_generation",
                            "source_path": "出图/共享/图片/定妆_CHAR_04__常态_正面.png",
                        },
                    },
                },
            }],
        }],
    }, ensure_ascii=False), encoding="utf-8")

    forms = image_qc.load_registry_forms(tmp_path)

    assert forms and len(forms) == 1
    aliases = forms[0]["strong_aliases"]
    assert "定妆_CHAR_04__常态_表情_克制" in aliases
    assert "克制" not in aliases
    assert "planned" not in aliases
    assert "controlled_multiref_generation" not in aliases


def test_asset_must_not_have_must_be_propagated_to_prompt(tmp_path: Path) -> None:
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "asset_registry.json").write_text(json.dumps({
        "kind": "n2d_asset_reference_registry",
        "assets": [{
            "id": "PROP_01",
            "type": "prop",
            "name": "毒酒瓷瓶",
            "reference_group": {"primary": "出图/共享/图片/定妆_毒酒瓷瓶.png"},
            "constraints": {"structure": "短颈圆口白瓷酒瓶", "must_not_have": ["壶嘴", "喷口"]},
            "drift_forbidden": ["壶嘴", "喷口"],
        }],
    }, ensure_ascii=False), encoding="utf-8")
    asset_index = image_qc.load_asset_index(tmp_path)
    bad = {"label": "Clip 01 毒酒抵唇", "body": "**资产引用注册层**：`PROP_01`。\n白瓷酒瓶抵近嘴唇。"}
    codes = {f["code"]: f["level"] for f in image_qc.lint_shot_block(bad, None, asset_index=asset_index)}
    assert codes.get("asset_must_not_have_not_propagated") == "block"

    good = {
        "label": "Clip 01 毒酒抵唇",
        "body": "**资产引用注册层**：`PROP_01`。\n白瓷酒瓶抵近嘴唇；结构负向：无壶嘴、无喷口。",
    }
    assert not any(
        f["code"] == "asset_must_not_have_not_propagated"
        for f in image_qc.lint_shot_block(good, None, asset_index=asset_index)
    )


def test_chinese_asset_id_binding_counts_as_bound(tmp_path: Path) -> None:
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "asset_registry.json").write_text(json.dumps({
        "kind": "n2d_asset_reference_registry",
        "assets": [{
            "id": "PROP_急报卷轴",
            "type": "prop",
            "name": "急报卷轴",
            "reference_group": {"primary": "出图/共享/图片/定妆_急报卷轴.png"},
            "constraints": {"must_not_have": ["二维码"]},
        }],
    }, ensure_ascii=False), encoding="utf-8")
    asset_index = image_qc.load_asset_index(tmp_path)
    block = {
        "label": "Clip 05 急报压堂",
        "body": (
            "**参考图入参清单**：`出图/共享/图片/定妆_急报卷轴.png`\n"
            "**资产引用注册层**：`PROP_急报卷轴`；禁形：二维码。\n"
        ),
    }

    codes = {f["code"] for f in image_qc.lint_shot_block(block, None, asset_index=asset_index)}

    assert "asset_ref_without_id" not in codes
    assert "asset_must_not_have_not_propagated" not in codes


def test_asset_primary_map_accepts_legacy_list_reference_group(tmp_path: Path) -> None:
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "asset_registry.json").write_text(json.dumps({
        "assets": [{
            "id": "LOC_01",
            "type": "location",
            "name": "长街废墟",
            "reference_group": [
                {"path": "出图/共享/图片/LOC_01_主参考.png", "status": "ready"}
            ],
        }],
    }, ensure_ascii=False), encoding="utf-8")
    pm = image_qc._asset_primary_map(tmp_path)
    assert pm["LOC_01"] == "出图/共享/图片/LOC_01_主参考.png"
    assert pm["长街废墟"] == "出图/共享/图片/LOC_01_主参考.png"


def test_prop_shape_review_targets_unconfirmed_high_risk_prop_png(tmp_path: Path) -> None:
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "asset_registry.json").write_text(json.dumps({
        "assets": [{
            "id": "PROP_01",
            "type": "prop",
            "name": "毒酒瓷瓶",
            "reference_group": {"primary": "出图/共享/图片/定妆_毒酒瓷瓶.png"},
            "constraints": {"must_not_have": ["壶嘴", "喷口"], "scale": "掌心小瓷瓶"},
        }],
    }, ensure_ascii=False), encoding="utf-8")
    pr = tmp_path / "出图" / "第1集" / "prompt"
    pr.mkdir(parents=True)
    (pr / "01_分镜出图.md").write_text(
        "## 镜头 1（EP01_CLIP01 毒酒抵唇）\n"
        "**资产引用注册层**：`PROP_01`；禁形：壶嘴、喷口。\n",
        encoding="utf-8",
    )
    img = tmp_path / "出图" / "第1集" / "图片"
    img.mkdir(parents=True)
    (img / "Clip_01_毒酒抵唇.png").write_bytes(b"not-a-real-png")

    targets = image_qc.prop_shape_review_targets(tmp_path, "第1集")
    assert len(targets) == 1
    assert targets[0]["asset"] == "PROP_01"
    assert targets[0]["png"] == "图片/Clip_01_毒酒抵唇.png"
    assert targets[0]["scale"] == "掌心小瓷瓶"
    assert targets[0]["confirmed"] is False


def test_asset_shape_review_covers_weapon_and_clip_without_underscore(tmp_path: Path) -> None:
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "asset_registry.json").write_text(json.dumps({
        "assets": [{
            "id": "WEAPON_01",
            "type": "weapon",
            "name": "横刀",
            "reference_group": {"primary": "出图/共享/图片/定妆_武器_横刀.png"},
            "constraints": {
                "structure": "一柄一刃单刃横刀，刀背非刃",
                "must_not_have": ["双刃", "多刃", "双向开刃", "第二把刀刃"],
            },
        }],
    }, ensure_ascii=False), encoding="utf-8")
    pr = tmp_path / "出图" / "第5集" / "prompt"
    pr.mkdir(parents=True)
    (pr / "01_分镜出图.md").write_text(
        "## 镜头 1（EP05_CLIP01 横刀出鞘）\n"
        "**资产引用注册层**：`WEAPON_01`；禁形：双刃、多刃、双向开刃、第二把刀刃。\n",
        encoding="utf-8",
    )
    img = tmp_path / "出图" / "第5集" / "图片"
    img.mkdir(parents=True)
    (img / "Clip01_first.png").write_bytes(b"not-a-real-png")

    targets = image_qc.prop_shape_review_targets(tmp_path, "第5集")

    assert len(targets) == 1
    assert targets[0]["asset"] == "WEAPON_01"
    assert targets[0]["asset_type"] == "weapon"
    assert targets[0]["png"] == "图片/Clip01_first.png"
    assert targets[0]["confirmed"] is False


def test_prop_shape_review_requires_shared_high_risk_primary_confirmation(tmp_path: Path) -> None:
    reg = tmp_path / "出图" / "共享"
    img = reg / "图片"
    img.mkdir(parents=True)
    primary = img / "定妆_武器_横刀.png"
    primary.write_bytes(b"single-edge-candidate")
    (reg / "asset_registry.json").write_text(json.dumps({
        "assets": [
            {
                "id": "WEAPON_01",
                "type": "weapon",
                "name": "横刀",
                "reference_group": {
                    "primary": {"path": "出图/共享/图片/定妆_武器_横刀.png", "status": "ready"},
                },
                "constraints": {
                    "blade_topology": "single_blade=1；cutting_edge_count=1；一侧厚钝刀背，一侧唯一锋刃",
                    "must_not_have": ["双刃", "第二把刀刃"],
                    "scale": "约成人臂展的三分之二",
                },
            },
            {
                "id": "PROP_横刀",
                "type": "prop",
                "name": "横刀别名",
                "alias_of": "WEAPON_01",
                "reference_group": {
                    "primary": {"path": "出图/共享/图片/定妆_武器_横刀.png", "status": "ready"},
                },
                "constraints": {"must_not_have": ["双刃"]},
            },
        ],
    }, ensure_ascii=False), encoding="utf-8")

    targets = image_qc.prop_shape_review_targets(tmp_path, "第1集")

    assert len(targets) == 1
    assert targets[0]["asset"] == "WEAPON_01"
    assert targets[0]["png"] == "出图/共享/图片/定妆_武器_横刀.png"
    assert targets[0]["shot"] == "shared_primary"
    assert targets[0]["scope"] == "shared_primary"
    assert targets[0]["shape_contract"] == [
        "single_blade=1",
        "cutting_edge_count=1",
        "一侧厚钝刀背",
        "一侧唯一锋刃",
        "约成人臂展的三分之二",
    ]
    assert targets[0]["confirmed"] is False

    image_qc.confirm_prop_shape_targets(
        tmp_path,
        "第1集",
        "all",
        reviewer="道具美术复核员",
        reason="原像素确认单刃厚背，无双刃或第二把刀刃",
        review_kind="human",
    )
    targets = image_qc.prop_shape_review_targets(tmp_path, "第1集")
    assert targets[0]["confirmed"] is True

    primary.write_bytes(b"changed-pixels")
    targets = image_qc.prop_shape_review_targets(tmp_path, "第1集")
    assert targets[0]["confirmed"] is False


def test_prop_shape_review_ignores_future_asset_guard_ids(tmp_path: Path) -> None:
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "asset_registry.json").write_text(json.dumps({
        "assets": [
            {
                "id": "WEAPON_01",
                "type": "weapon",
                "name": "横刀",
                "constraints": {"must_not_have": ["第二把刀刃"]},
            },
            {
                "id": "VFX_虎山神摹影",
                "type": "vfx",
                "name": "虎山神摹影黑血妖气",
                "constraints": {"must_not_have": ["过度血腥猎奇"]},
            },
        ],
    }, ensure_ascii=False), encoding="utf-8")
    pr = tmp_path / "出图" / "第5集" / "prompt"
    pr.mkdir(parents=True)
    (pr / "01_分镜出图.md").write_text(
        "## 镜头 2（EP05_CLIP02 猛虎快刀）\n"
        "**资产引用注册层**：`WEAPON_01`；禁形：第二把刀刃。\n"
        "**资产显现时机防呆**：Clip02 禁用 `VFX_虎山神摹影`，直到 Clip06 才允许显现；"
        "资产禁项：过度血腥猎奇。\n",
        encoding="utf-8",
    )
    img = tmp_path / "出图" / "第5集" / "图片"
    img.mkdir(parents=True)
    (img / "Clip02_first.png").write_bytes(b"not-a-real-png")

    targets = image_qc.prop_shape_review_targets(tmp_path, "第5集")

    assert [t["asset"] for t in targets] == ["WEAPON_01"]
    assert targets[0]["png"] == "图片/Clip02_first.png"


def test_prop_shape_review_skips_declared_target_until_png_exists(tmp_path: Path) -> None:
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "asset_registry.json").write_text(json.dumps({
        "assets": [{
            "id": "PROP_01",
            "type": "prop",
            "name": "毒酒瓷瓶",
            "constraints": {"must_not_have": ["壶嘴", "喷口"]},
        }],
    }, ensure_ascii=False), encoding="utf-8")
    pr = tmp_path / "出图" / "第1集" / "prompt"
    pr.mkdir(parents=True)
    (pr / "01_分镜出图.md").write_text(
        "## 镜头 1（EP01_CLIP01 毒酒抵唇）\n"
        "**目标**：`出图/第1集/图片/Clip01_first.png`\n"
        "**资产引用注册层**：`PROP_01`；禁形：壶嘴、喷口。\n",
        encoding="utf-8",
    )

    assert image_qc.prop_shape_review_targets(tmp_path, "第1集") == []

    img = tmp_path / "出图" / "第1集" / "图片"
    img.mkdir(parents=True)
    (img / "Clip01_first.png").write_bytes(b"not-a-real-png")

    targets = image_qc.prop_shape_review_targets(tmp_path, "第1集")
    assert len(targets) == 1
    assert targets[0]["png"] == "图片/Clip01_first.png"


def test_shared_asset_pngs_are_not_treated_as_shot_targets(tmp_path: Path) -> None:
    body = (
        "**参考图**：`出图/共享/图片/CHAR_01_常态_脸部特写.png`\n"
        "**正向 prompt（中文）**：引用 `CHAR_01_常态_脸部特写.png` 锁脸，目标镜头尚未落档。"
    )
    assert image_qc._extract_target_pngs(body) == []

    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "asset_registry.json").write_text(json.dumps({
        "assets": [{
            "id": "PROP_01",
            "type": "prop",
            "name": "毒酒瓷瓶",
            "constraints": {"must_not_have": ["壶嘴", "喷口"]},
        }],
    }, ensure_ascii=False), encoding="utf-8")
    pr = tmp_path / "出图" / "第1集" / "prompt"
    pr.mkdir(parents=True)
    (pr / "01_分镜出图.md").write_text(
        "## Clip 05\n"
        "`PROP_01` 禁形：壶嘴、喷口。\n"
        "`出图/共享/图片/CHAR_01_常态_侧.png`\n",
        encoding="utf-8",
    )
    assert image_qc.prop_shape_review_targets(tmp_path, "第1集") == []


def test_artifact_namespace_flags_live_png_not_declared_by_current_prompt(tmp_path: Path) -> None:
    prompt = tmp_path / "出图" / "第1集" / "prompt"
    prompt.mkdir(parents=True)
    (prompt / "01_分镜出图.md").write_text(
        "## 镜头 1\n"
        "**目标**：`出图/第1集/图片/Clip01_first.png` "
        "`出图/第1集/图片/Clip01_mid.png` "
        "`出图/第1集/图片/Clip01_end.png`\n",
        encoding="utf-8",
    )
    image_dir = tmp_path / "出图" / "第1集" / "图片"
    image_dir.mkdir(parents=True)
    (image_dir / "Clip01_first.png").write_bytes(b"x")
    (image_dir / "Clip01_黑殿审问.png").write_bytes(b"x")

    audit = image_qc.audit_artifact_namespace(tmp_path, "第1集")

    assert audit["declared_targets"] == 3
    assert audit["stale"] == [{
        "path": "出图/第1集/图片/Clip01_黑殿审问.png",
        "reason": "live 图片目录中的 Clip PNG 未被当前 01_分镜出图.md 目标集声明",
    }]


def test_artifact_namespace_blocks_summary_and_findings() -> None:
    payload = {
        "checks": {},
        "lint": {"findings": []},
        "artifact_namespace": {
            "stale": [{"path": "出图/第1集/图片/Clip01_黑殿审问.png"}],
        },
    }

    summary = image_qc.summarize(payload)
    findings = image_qc.to_findings({
        **payload,
        "summary": summary,
        "qc_environment": {"precision_level": "full"},
    })

    assert summary["hard_blocks"] == 1
    assert summary["by_check"]["artifact_namespace"]["block"] == 1
    assert any(
        f["sev"] == "block"
        and f["dim"] == "image_artifact_namespace"
        and f["loc"] == "出图/第1集/图片/Clip01_黑殿审问.png"
        for f in findings
    )


def test_prop_shape_review_confirmations_require_current_png_hash(tmp_path: Path) -> None:
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "asset_registry.json").write_text(json.dumps({
        "assets": [{
            "id": "PROP_01",
            "type": "prop",
            "name": "毒酒瓷瓶",
            "constraints": {"must_not_have": ["壶嘴"]},
        }],
    }, ensure_ascii=False), encoding="utf-8")
    pr = tmp_path / "出图" / "第1集" / "prompt"
    pr.mkdir(parents=True)
    (pr / "01_分镜出图.md").write_text("## Clip 01\n`PROP_01` 无壶嘴。\n", encoding="utf-8")
    img = tmp_path / "出图" / "第1集" / "图片"
    img.mkdir(parents=True)
    (img / "Clip_01.png").write_bytes(b"x")
    confirm = tmp_path / "生产数据" / "image_qc" / "第1集"
    confirm.mkdir(parents=True)
    (confirm / "prop_shape_confirmations.json").write_text(json.dumps({
        "confirmations": [{"asset": "PROP_01", "png": "图片/Clip_01.png", "verdict": "ok"}]
    }, ensure_ascii=False), encoding="utf-8")

    targets = image_qc.prop_shape_review_targets(tmp_path, "第1集")
    assert targets and targets[0]["confirmed"] is False

    image_qc.confirm_prop_shape_targets(tmp_path, "第1集", "all")
    targets = image_qc.prop_shape_review_targets(tmp_path, "第1集")
    assert targets and targets[0]["confirmed"] is True

    (img / "Clip_01.png").write_bytes(b"new-image")
    targets = image_qc.prop_shape_review_targets(tmp_path, "第1集")
    assert targets and targets[0]["confirmed"] is False


def test_prop_shape_review_confirmation_invalidates_when_contract_changes(tmp_path: Path) -> None:
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    registry_path = reg / "asset_registry.json"
    registry = {
        "assets": [{
            "id": "PROP_01",
            "type": "prop",
            "name": "双轮木车",
            "constraints": {
                "must_not_have": ["第三轮"],
                "structure": "总轮数恰好两只",
            },
        }],
    }
    registry_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    pr = tmp_path / "出图" / "第1集" / "prompt"
    pr.mkdir(parents=True)
    (pr / "01_分镜出图.md").write_text("## Clip 01\n`PROP_01` 双轮木车。\n", encoding="utf-8")
    img = tmp_path / "出图" / "第1集" / "图片"
    img.mkdir(parents=True)
    (img / "Clip_01.png").write_bytes(b"same-current-pixels")

    image_qc.confirm_prop_shape_targets(tmp_path, "第1集", "all", reviewer="qa")
    assert image_qc.prop_shape_review_targets(tmp_path, "第1集")[0]["confirmed"] is True

    registry["assets"][0]["constraints"]["structure"] = "总轮数恰好两只；只允许一根横轴"
    registry_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")

    target = image_qc.prop_shape_review_targets(tmp_path, "第1集")[0]
    assert target["confirmed"] is False


def test_face_confirmations_require_current_png_hash_and_convert_rows(tmp_path: Path) -> None:
    img = tmp_path / "出图" / "第1集" / "图片"
    img.mkdir(parents=True)
    (img / "Clip01_end.png").write_bytes(b"image-v1")
    qc_dir = tmp_path / "生产数据" / "image_qc" / "第1集"
    qc_dir.mkdir(parents=True)
    (qc_dir / "image_qc_第1集.json").write_text(json.dumps({
        "checks": {
            "face": {
                "available": True,
                "mode": "insightface",
                "precision_level": "full",
                "shots": [{
                    "char": "贺平生",
                    "png": "图片/Clip01_end.png",
                    "score": 0.36,
                    "floor": 0.38,
                    "verdict": "warn",
                }],
            }
        }
    }, ensure_ascii=False), encoding="utf-8")
    (qc_dir / "face_confirmations.json").write_text(json.dumps({
        "confirmations": [{
            "char": "贺平生",
            "png": "图片/Clip01_end.png",
            "verdict": "ok",
            "png_sha256": "stale",
        }]
    }, ensure_ascii=False), encoding="utf-8")

    payload = {
        "checks": {"face": {"shots": [{"char": "贺平生", "png": "图片/Clip01_end.png", "verdict": "warn"}]}},
    }
    image_qc.apply_face_confirmations(payload, tmp_path, "第1集")
    assert payload["checks"]["face"]["shots"][0]["verdict"] == "warn"
    assert payload["face_manual_confirmations"]["applied"] == 0

    res = image_qc.confirm_face_targets(tmp_path, "第1集", "all", reviewer="qa")
    assert res["selected"] == 1
    payload = {
        "checks": {"face": {"shots": [{"char": "贺平生", "png": "图片/Clip01_end.png", "verdict": "warn"}]}},
    }
    image_qc.apply_face_confirmations(payload, tmp_path, "第1集")
    row = payload["checks"]["face"]["shots"][0]
    assert row["verdict"] == "ok"
    assert row["manual_original_verdict"] == "warn"
    assert row["manual_reviewer"] == "qa"
    data = json.loads((qc_dir / "face_confirmations.json").read_text(encoding="utf-8"))
    assert data["confirmations"][0]["png_sha256"] == image_qc._sha256_file(img / "Clip01_end.png")

    (img / "Clip01_end.png").write_bytes(b"image-v2")
    payload = {
        "checks": {"face": {"shots": [{"char": "贺平生", "png": "图片/Clip01_end.png", "verdict": "warn"}]}},
    }
    image_qc.apply_face_confirmations(payload, tmp_path, "第1集")
    assert payload["checks"]["face"]["shots"][0]["verdict"] == "warn"


def test_face_confirmation_executor_visual_is_explicit_and_authorized(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text(
        "- 图片验收模式: 逐张机器QC+执行者实际像素目视后再继续  # source=explicit_user；用户明确要求\n",
        encoding="utf-8",
    )
    img = tmp_path / "出图" / "第1集" / "图片"
    img.mkdir(parents=True)
    (img / "Clip01.png").write_bytes(b"image-v1")
    qc_dir = tmp_path / "生产数据" / "image_qc" / "第1集"
    qc_dir.mkdir(parents=True)
    (qc_dir / "image_qc_第1集.json").write_text(json.dumps({
        "checks": {"face": {"shots": [{
            "char": "CHAR_01",
            "png": "图片/Clip01.png",
            "verdict": "warn",
        }]}}
    }, ensure_ascii=False), encoding="utf-8")

    res = image_qc.confirm_face_targets(
        tmp_path,
        "第1集",
        "all",
        reviewer="executor:codex",
        review_kind="executor_visual",
        reason="实际查看当前像素并与定妆并排核对",
    )

    assert res["ok"] is True
    data = json.loads((qc_dir / "face_confirmations.json").read_text(encoding="utf-8"))
    receipt = data["confirmations"][0]
    assert receipt["review_kind"] == "executor_visual"
    assert receipt["reviewer_role"] == "ai_visual_executor"
    assert receipt["human_signoff"] is False


def test_face_confirmation_allows_face_reference_coverage(tmp_path: Path) -> None:
    img = tmp_path / "出图" / "第1集" / "图片"
    img.mkdir(parents=True)
    (img / "Clip01_end.png").write_bytes(b"image-v1")
    sha = image_qc._sha256_file(img / "Clip01_end.png")
    qc_dir = tmp_path / "生产数据" / "image_qc" / "第1集"
    qc_dir.mkdir(parents=True)
    (qc_dir / "face_confirmations.json").write_text(json.dumps({
        "confirmations": [{
            "char": "贺平生",
            "png": "图片/Clip01_end.png",
            "verdict": "ok",
            "png_sha256": sha,
            "reason": "暗光侧脸目检通过",
        }]
    }, ensure_ascii=False), encoding="utf-8")

    payload = {
        "lint": {
            "available": True,
            "character_shots": [{
                "label": "Clip 01",
                "shot": "Clip01",
                "png": "图片/Clip01_end.png",
                "identity_refs": ["CHAR_01/常态"],
            }],
        },
        "checks": {
            "face": {
                "available": True,
                "mode": "insightface",
                "precision_level": "full",
                "shots": [{
                    "char": "贺平生",
                    "png": "图片/Clip01_end.png",
                    "score": 0.36,
                    "floor": 0.38,
                    "verdict": "warn",
                }],
            },
        },
    }
    image_qc.apply_face_confirmations(payload, tmp_path, "第1集")
    coverage = image_qc.face_reference_coverage(payload, tmp_path, "第1集")

    assert coverage["verdict"] == "ok"
    assert coverage["covered"] == 1
    assert coverage["missing"] == []


def test_human_image_review_reject_requires_current_png_hash_and_blocks(tmp_path: Path) -> None:
    img = tmp_path / "出图" / "第1集" / "图片"
    img.mkdir(parents=True)
    png = img / "Clip03_first.png"
    png.write_bytes(b"image-v1")
    stale_sha = "stale"
    qc_dir = tmp_path / "生产数据" / "image_qc" / "第1集"
    qc_dir.mkdir(parents=True)
    (qc_dir / "human_image_review.json").write_text(json.dumps({
        "kind": "n2d_human_image_review",
        "version": 1,
        "rejects": [{
            "png": "图片/Clip03_first.png",
            "verdict": "reject",
            "png_sha256": stale_sha,
            "dimension": "style_consistency",
            "reason": "照片感过强",
        }],
    }, ensure_ascii=False), encoding="utf-8")

    payload = {"checks": {}, "lint": {"findings": []}}
    image_qc.apply_human_image_review(payload, tmp_path, "第1集")
    assert payload["human_image_review"]["active_rejects"] == 0

    current_sha = image_qc._sha256_file(png)
    data = json.loads((qc_dir / "human_image_review.json").read_text(encoding="utf-8"))
    data["rejects"][0]["png_sha256"] = current_sha
    (qc_dir / "human_image_review.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    payload = {"checks": {}, "lint": {"findings": []}}
    image_qc.apply_human_image_review(payload, tmp_path, "第1集")
    summary = image_qc.summarize(payload)
    findings = image_qc.to_findings(payload)
    regen = image_qc.to_regen_list(payload)

    assert summary["verdict"] == "block"
    assert summary["by_check"]["human_image_review"]["block"] == 1
    assert any(f["sev"] == "block" and f["dim"] == "style_consistency" and f["loc"] == "图片/Clip03_first.png"
               for f in findings)
    assert regen == [{"shot": "Clip_03", "png": "图片/Clip03_first.png", "reasons": ["人工拒收:style_consistency"]}]


def test_write_prop_shape_skeleton_does_not_confirm(tmp_path: Path) -> None:
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "asset_registry.json").write_text(json.dumps({
        "assets": [{"id": "PROP_01", "type": "prop", "name": "毒酒瓷瓶", "constraints": {"must_not_have": ["壶嘴"]}}],
    }, ensure_ascii=False), encoding="utf-8")
    pr = tmp_path / "出图" / "第1集" / "prompt"
    pr.mkdir(parents=True)
    (pr / "01_分镜出图.md").write_text("## Clip 01\n`PROP_01` 无壶嘴。\n", encoding="utf-8")
    img = tmp_path / "出图" / "第1集" / "图片"
    img.mkdir(parents=True)
    (img / "Clip_01.png").write_bytes(b"x")

    res = image_qc.write_prop_shape_skeleton(tmp_path, "第1集")
    assert res["changed"] == 1
    targets = image_qc.prop_shape_review_targets(tmp_path, "第1集")
    assert targets and targets[0]["confirmed"] is False


def test_confirm_prop_shape_targets_marks_pending_ok(tmp_path: Path) -> None:
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "asset_registry.json").write_text(json.dumps({
        "assets": [{"id": "PROP_01", "type": "prop", "name": "毒酒瓷瓶", "constraints": {"must_not_have": ["壶嘴"]}}],
    }, ensure_ascii=False), encoding="utf-8")
    pr = tmp_path / "出图" / "第1集" / "prompt"
    pr.mkdir(parents=True)
    (pr / "01_分镜出图.md").write_text("## Clip 01\n`PROP_01` 无壶嘴。\n", encoding="utf-8")
    img = tmp_path / "出图" / "第1集" / "图片"
    img.mkdir(parents=True)
    (img / "Clip_01.png").write_bytes(b"x")

    res = image_qc.confirm_prop_shape_targets(tmp_path, "第1集", "all", reviewer="qa")
    assert res["selected"] == 1
    targets = image_qc.prop_shape_review_targets(tmp_path, "第1集")
    assert targets and targets[0]["confirmed"] is True
    data = json.loads((tmp_path / "生产数据" / "image_qc" / "第1集" / "prop_shape_confirmations.json").read_text(encoding="utf-8"))
    assert data["confirmations"][0]["reviewer"] == "qa"
    assert data["confirmations"][0]["png_sha256"] == image_qc._sha256_file(img / "Clip_01.png")


def test_confirm_prop_shape_executor_visual_does_not_impersonate_human(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text(
        "- 图片验收模式: 逐张机器QC+执行者实际像素目视后再继续  # source=explicit_user；用户明确要求\n",
        encoding="utf-8",
    )
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "asset_registry.json").write_text(json.dumps({
        "assets": [{"id": "PROP_01", "type": "prop", "name": "木牌", "constraints": {"must_not_have": ["结构漂移"]}}],
    }, ensure_ascii=False), encoding="utf-8")
    pr = tmp_path / "出图" / "第1集" / "prompt"
    pr.mkdir(parents=True)
    (pr / "01_分镜出图.md").write_text("## Clip 01\n`PROP_01` 木牌。\n", encoding="utf-8")
    img = tmp_path / "出图" / "第1集" / "图片"
    img.mkdir(parents=True)
    (img / "Clip_01.png").write_bytes(b"x")

    res = image_qc.confirm_prop_shape_targets(
        tmp_path,
        "第1集",
        "all",
        reviewer="executor:codex",
        review_kind="executor_visual",
        reason="实际查看当前像素并与道具主参考并排核对",
    )

    assert res["ok"] is True
    data = json.loads((tmp_path / "生产数据" / "image_qc" / "第1集" / "prop_shape_confirmations.json").read_text(encoding="utf-8"))
    receipt = data["confirmations"][0]
    assert receipt["review_kind"] == "executor_visual"
    assert receipt["reviewer_role"] == "ai_visual_executor"
    assert receipt["human_signoff"] is False


def test_vlm_confirm_prop_shape_targets_writes_only_high_confidence_ok(tmp_path: Path, monkeypatch) -> None:
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "asset_registry.json").write_text(json.dumps({
        "assets": [{"id": "PROP_01", "type": "prop", "name": "毒酒瓷瓶", "constraints": {"must_not_have": ["壶嘴"]}}],
    }, ensure_ascii=False), encoding="utf-8")
    pr = tmp_path / "出图" / "第1集" / "prompt"
    pr.mkdir(parents=True)
    (pr / "01_分镜出图.md").write_text("## Clip 01\n`PROP_01` 无壶嘴。\n", encoding="utf-8")
    img = tmp_path / "出图" / "第1集" / "图片"
    img.mkdir(parents=True)
    (img / "Clip_01.png").write_bytes(b"x")

    class FakeVLM:
        @staticmethod
        def load_judge():
            return lambda image, prompt, kind: {"match": True, "confidence": 0.9, "mismatches": [], "reason": "ok"}

        @staticmethod
        def parse_verdict(raw):
            return raw

    monkeypatch.setattr(image_qc, "_load_sibling", lambda name: FakeVLM if name == "vlm_verify" else None)
    res = image_qc.vlm_confirm_prop_shape_targets(tmp_path, "第1集", block_floor=0.6)
    assert res["confirmed"] == 1
    assert image_qc.prop_shape_review_targets(tmp_path, "第1集")[0]["confirmed"] is True
    data = json.loads((tmp_path / "生产数据" / "image_qc" / "第1集" / "prop_shape_confirmations.json").read_text(encoding="utf-8"))
    assert data["confirmations"][0]["png_sha256"] == image_qc._sha256_file(img / "Clip_01.png")


def test_prop_shape_review_is_hard_block_and_finding() -> None:
    payload = {
        "checks": {},
        "lint": {"findings": []},
        "prop_shape_review": {
            "targets": [{
                "asset": "PROP_01",
                "asset_name": "毒酒瓷瓶",
                "label": "Clip 01",
                "png": "图片/Clip_01.png",
                "must_not_have": ["壶嘴", "喷口"],
                "scale": "掌心小瓷瓶",
                "confirmed": False,
                "confirmation_path": "生产数据/image_qc/第1集/prop_shape_confirmations.json",
            }]
        },
    }
    summary = image_qc.summarize(payload)
    assert summary["verdict"] == "block"
    findings = image_qc.to_findings(payload)
    assert any(f["sev"] == "block" and f["dim"] == "multimodal_continuity" and "高风险道具禁形/尺寸" in f["msg"]
               and "掌心小瓷瓶" in f["msg"]
               for f in findings)


def test_qc_inputs_fingerprint_tracks_prop_shape_confirmations(tmp_path: Path) -> None:
    payload = {
        "checks": {},
        "lint": {"findings": []},
        "prop_shape_review": {"targets": [{"asset": "PROP_01", "png": "图片/Clip_01.png"}]},
        "style_attribution": {"intent": {"anchors": ["出图/共享/图片/风格锚_国漫写实.png"]}},
    }

    fingerprint = image_qc._qc_inputs_fingerprint(tmp_path, "第1集", payload)

    assert fingerprint is not None
    assert "生产数据/image_qc/第1集/prop_shape_confirmations.json" in fingerprint["files"]
    assert "生产数据/image_qc/第1集/human_image_review.json" in fingerprint["files"]
    assert "出图/共享/style_anchor_registry.json" in fingerprint["files"]
    assert "出图/共享/图片/风格锚_国漫写实.png" in fingerprint["files"]


def test_qc_inputs_fingerprint_skips_unlanded_face_pending_pngs(tmp_path: Path) -> None:
    payload = {
        "checks": {},
        "lint": {"findings": []},
        "face_reference_coverage": {
            "pending": [
                {"png": "出图/第1集/图片/Clip03_first.png", "shot": "Clip_03"},
            ],
            "missing": [],
        },
    }

    fingerprint = image_qc._qc_inputs_fingerprint(tmp_path, "第1集", payload)

    assert fingerprint is not None
    assert "出图/第1集/图片/Clip03_first.png" not in fingerprint["files"]


def test_qc_inputs_fingerprint_normalizes_episode_picture_relpaths(tmp_path: Path) -> None:
    png = tmp_path / "出图" / "第1集" / "图片" / "Clip01_first.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    payload = {
        "checks": {"face": {"shots": [{"png": "图片/Clip01_first.png", "verdict": "noface"}]}},
        "lint": {"findings": []},
    }

    fingerprint = image_qc._qc_inputs_fingerprint(tmp_path, "第1集", payload)

    assert fingerprint is not None
    assert fingerprint["files"]["出图/第1集/图片/Clip01_first.png"]
    assert "图片/Clip01_first.png" not in fingerprint["files"]


def _char_block(label: str, *, ref=True, eyeline=True, anchor=True, lock=True, char_id="CHAR_01/常态") -> dict:
    body = []
    if ref:
        body.append("**参考图**（多图参考派生铁律）:\n- `出图/共享/图片/定妆_沈念_常态.png`（强度 0.8）")
    if eyeline:
        body.append("**视线方向**：画左看画右")
    body.append(f"**资产身份注册层**：`{char_id}`；从 identity_registry 继承 reference_group。")
    body.append("**人体完整性**：可见身体范围=半身；画幅自然裁切未入画手脚；不得额外手、第三只手、多肢、六指、断手、缺肢、身体埋入、穿模或融合。")
    if anchor:
        body.append("锚点句：沈念：凤眼薄唇")
    if lock:
        body.append("身份锁定句：保持与参考图①的人脸一致。")
    return {"label": label, "body": "\n".join(body)}


def _registry_forms_for_tail_handoff() -> list:
    return [
        {
            "id": "CHAR_01",
            "form": "常态",
            "key": "CHAR_01/常态",
            "asset_key": "沈念_常态",
            "display": "沈念_常态",
            "strong_aliases": {"CHAR_01", "CHAR_01/常态", "沈念_常态", "定妆_沈念_常态"},
            "weak_aliases": {"沈念", "林婉儿"},
        },
        {
            "id": "CHAR_03",
            "form": "人皮态",
            "key": "CHAR_03/人皮态",
            "asset_key": "柳娘子_人皮态",
            "display": "柳娘子_人皮态",
            "strong_aliases": {
                "CHAR_03",
                "CHAR_03/人皮态",
                "柳娘子_人皮态",
                "定妆_柳娘子_人皮态",
                "定妆_柳娘子_人皮态_脸部特写",
            },
            "weak_aliases": {"柳娘子"},
        },
    ]


def _tail_handoff_block(tail_lock: str = "") -> dict:
    blk = _char_block("Clip 12 轻笑与失控")
    blk["body"] += "\n".join([
        "",
        "**专项镜头模板**：dialogue_shot_reverse；柳娘子笑意失控作为下一镜入点。",
        "**近景/反打身份锁定**：尾帧出现柳娘子近景反应时，必须锁中年圆润脸。",
        "**尾帧接力生成方式**：以 `Clip_12_沈念轻笑.png` 为母图，只改柳娘子反应。",
        tail_lock,
    ])
    return blk


def test_lint_flags_unknown_char_id() -> None:
    valid = {"CHAR_01", "CHAR_01/常态"}
    blk = _char_block("Clip 05", char_id="CHAR_99/常态")
    findings = image_qc.lint_shot_block(blk, valid)
    codes = {f["code"] for f in findings}
    assert "unknown_char_id" in codes
    assert any(f["level"] == "block" for f in findings if f["code"] == "unknown_char_id")


def test_lint_passes_clean_char_block() -> None:
    valid = {"CHAR_01", "CHAR_01/常态"}
    findings = image_qc.lint_shot_block(_char_block("Clip 02"), valid)
    assert findings == []   # 参考图/视线/锚点句/身份锁定句/合法ID 齐 → 无 finding


def test_character_shot_manifest_extracts_target_png() -> None:
    blk = _char_block("Clip 02 冷开场")
    blk["body"] = "**目标存档**：`出图/第1集/图片/Clip_02_冷开场.png`\n" + blk["body"]
    manifest = image_qc.character_shot_manifest(blk)
    assert manifest["shot"] == "Clip_02"
    assert manifest["png"] == "出图/第1集/图片/Clip_02_冷开场.png"
    assert manifest["identity_refs"] == ["CHAR_01/常态"]


def test_character_shot_manifests_include_mid_and_end_targets() -> None:
    blk = _char_block("Clip 02 冷开场")
    blk["body"] = (
        "**目标落档**：`出图/第1集/图片/Clip_02_冷开场.png` "
        "`出图/第1集/图片/Clip_02_冷开场_mid.png` "
        "`出图/第1集/图片/Clip_02_冷开场_end.png`\n"
        + blk["body"]
    )
    manifests = image_qc.character_shot_manifests(blk)
    assert [m["png"] for m in manifests] == [
        "出图/第1集/图片/Clip_02_冷开场.png",
        "出图/第1集/图片/Clip_02_冷开场_mid.png",
        "出图/第1集/图片/Clip_02_冷开场_end.png",
    ]


def test_character_shot_manifests_support_per_target_faceless_reaction_anchor() -> None:
    blk = _char_block("Clip 06 反应锚")
    blk["body"] = (
        "**目标落档**：`出图/第1集/图片/Clip06_first.png` "
        "`出图/第1集/图片/Clip06_mid_reaction.png` "
        "`出图/第1集/图片/Clip06_end.png`\n"
        "**逐目标脸检策略**：`出图/第1集/图片/Clip06_mid_reaction.png` "
        "face_check_policy=faceless_reaction_anchor；OTS/侧脸/手部/物件反应锚，不要求正脸比对。\n"
        + blk["body"]
    )

    manifests = image_qc.character_shot_manifests(blk)

    assert [m["face_coverage_required"] for m in manifests] == [True, False, True]
    assert manifests[1]["face_check_policy"] == "faceless_reaction_anchor"


def test_character_shot_manifest_skips_non_human_primary_anchor() -> None:
    blk = {
        "label": "Clip 05 狼首正主",
        "body": "\n".join([
            "**目标落档**：`出图/第1集/图片/Clip05_first.png`",
            "**资产身份注册层**：`CHAR_05/常态`, `CHAR_01/常态`；二人都登记。",
            "**多人同框身份槽位**：SLOT_1: `CHAR_05/常态` -> 画右前景，primary 星标；"
            "SLOT_2: `CHAR_01/常态` -> 画左反应。",
            "**本镜状态锁**：`CHAR_05`: 青面郎君从青衫狼首常态伏地爆冲，妖物视觉特征必须保留。",
        ]),
    }

    manifest = image_qc.character_shot_manifest(blk)

    assert manifest["identity_refs"] == ["CHAR_05/常态"]
    assert manifest["face_coverage_required"] is False
    assert manifest["face_check_policy"] == "non_human_anchor_policy"


def test_character_shot_manifest_keeps_human_primary_face_required_with_creature_in_scene() -> None:
    blk = {
        "label": "Clip 06 人类主检",
        "body": "\n".join([
            "**目标落档**：`出图/第1集/图片/Clip06_first.png`",
            "**资产身份注册层**：`CHAR_01/常态`, `CHAR_05/常态`；二人都登记。",
            "**多人同框身份槽位**：SLOT_1: `CHAR_01/常态` -> 画左前景，primary 星标；"
            "SLOT_2: `CHAR_05/常态` -> 画右冲刺。",
            "**本镜状态锁**：`CHAR_05`: 青面郎君从青衫狼首常态伏地爆冲，妖物视觉特征必须保留。",
        ]),
    }

    manifest = image_qc.character_shot_manifest(blk)

    assert manifest["identity_refs"] == ["CHAR_01/常态"]
    assert manifest["face_coverage_required"] is True
    assert "face_check_policy" not in manifest


def test_character_shot_manifest_uses_primary_slot_identity_refs() -> None:
    blk = {
        "label": "Clip 02 反打",
        "body": "\n".join([
            "**目标存档**：`出图/第1集/图片/Clip02_first.png`",
            "**参考图**：`出图/共享/图片/定妆_张老大.png` `出图/共享/图片/定妆_沈念.png`",
            "**资产身份注册层**：`CHAR_02/常态`, `CHAR_01/常态`；二人都登记。",
            "**多人同框身份槽位**：SLOT_1: `CHAR_02/常态` -> 画右前景，primary 星标；"
            "SLOT_2: `CHAR_01/常态` -> 画左低位反应。",
        ]),
    }

    manifest = image_qc.character_shot_manifest(blk)

    assert manifest["identity_refs"] == ["CHAR_02/常态"]


def test_character_shot_manifest_ignores_offscreen_continuity_char_refs() -> None:
    blk = {
        "label": "Clip 10 尾钩",
        "body": "\n".join([
            "**目标落档**：`出图/第2集/图片/Clip10_first.png` `出图/第2集/图片/Clip10_mid.png` `出图/第2集/图片/Clip10_end.png`",
            "**参考图**：`出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png`",
            "**资产身份注册层**：`CHAR_01/囚犯初醒态`；本镜只主检姜月初。",
            "**专项镜头模板**：continuity_must=[\"CHAR_02 可画外保留\", \"WEAPON_01 横刀也可画外保留\"]。",
        ]),
    }

    manifests = image_qc.character_shot_manifests(blk)

    assert [m["identity_refs"] for m in manifests] == [
        ["CHAR_01/囚犯初醒态"],
        ["CHAR_01/囚犯初醒态"],
        ["CHAR_01/囚犯初醒态"],
    ]


def test_character_shot_manifest_explicit_star_overrides_primary_slot_text() -> None:
    blk = {
        "label": "Clip 08 系统规则",
        "body": "\n".join([
            "**目标存档**：`出图/第1集/图片/Clip08_first.png`",
            "**参考图**：`出图/共享/图片/定妆_姜月初.png` `出图/共享/图片/定妆_裴长青.png`",
            "**资产身份注册层**：`CHAR_01/囚犯初醒态`, `CHAR_02/濒死战损态`；二人都登记。",
            "**主检脸星标**：`CHAR_02/濒死战损态*`；`CHAR_01/囚犯初醒态` 只作 OTS/手部。",
            "**多人同框身份槽位**：SLOT_1: `CHAR_01/囚犯初醒态` -> 画左前景，primary 星标；"
            "SLOT_2: `CHAR_02/濒死战损态` -> 画右下近景。",
        ]),
    }

    manifest = image_qc.character_shot_manifest(blk)

    assert manifest["identity_refs"] == ["CHAR_02/濒死战损态"]


def test_identity_ref_regex_ignores_char_file_stems() -> None:
    text = "`出图/共享/图片/CHAR_SHENNIAN_常态.png` `CHAR_SHENNIAN/常态`"
    assert image_qc.IDENTITY_REF_RE.findall(text) == ["CHAR_SHENNIAN/常态"]


def test_character_shot_manifest_skips_no_face_asset_only_shot() -> None:
    blk = {
        "label": "Clip 16 毒酒碎裂",
        "body": (
            "**目标**：`出图/第1集/图片/Clip_16_毒酒碎裂.png`\n"
            "**参考图**：`出图/共享/图片/定妆_冷宫寝殿.png`；"
            "`出图/共享/图片/定妆_毒酒碎瓷.png`\n"
            "**资产身份注册层**：从 `出图/共享/identity_registry.json` 继承；"
            "无人物或人物不露脸：以场景/道具锚为主。\n"
            "**资产引用注册层**：`LOC_01`；`PROP_03`。"
        ),
    }
    assert image_qc.character_shot_manifest(blk) is None


def test_character_shot_manifest_skips_explicit_no_face_coverage_shot() -> None:
    blk = _char_block("Clip 14 左腕特写", char_id="CHAR_01/觉醒态")
    blk["body"] += "\n**脸部覆盖豁免**：本镜是手腕特写，无可比对人脸；身份由袖口和相邻镜头连续性锁定。"
    assert image_qc.character_shot_manifest(blk) is None


def test_lint_accepts_semantic_char_ids_and_primary_marker() -> None:
    valid = {"CHAR_SHEN", "CHAR_SHEN/受难", "CHAR_LIU"}
    assert image_qc.lint_shot_block(_char_block("Clip 02", char_id="CHAR_SHEN/受难"), valid) == []
    assert image_qc.lint_shot_block(_char_block("Clip 03", char_id="CHAR_SHEN/受难*"), valid) == []
    assert image_qc.lint_shot_block(_char_block("Clip 03b", char_id="CHAR_SHEN*/受难"), valid) == []
    assert image_qc.lint_shot_block(_char_block("Clip 04", char_id="CHAR_LIU*"), valid) == []


def test_lint_flags_unknown_semantic_char_id() -> None:
    valid = {"CHAR_SHEN", "CHAR_SHEN/受难"}
    blk = _char_block("Clip 05", char_id="CHAR_WANG/常态")
    findings = image_qc.lint_shot_block(blk, valid)
    assert any(f["code"] == "unknown_char_id" and "CHAR_WANG" in f["msg"] for f in findings)


def test_lint_flags_missing_reference_block() -> None:
    valid = {"CHAR_01", "CHAR_01/常态"}
    blk = _char_block("Clip 07", ref=False)
    findings = image_qc.lint_shot_block(blk, valid)
    assert any(f["code"] == "no_reference_block" and f["level"] == "block" for f in findings)


def test_lint_warns_missing_fields() -> None:
    valid = {"CHAR_01", "CHAR_01/常态"}
    blk = _char_block("Clip 09", eyeline=False, anchor=False, lock=False)
    codes = {f["code"]: f["level"] for f in image_qc.lint_shot_block(blk, valid)}
    assert codes.get("no_eyeline") == "warn"
    assert codes.get("no_anchor_phrase") == "warn"
    assert codes.get("no_identity_lock_phrase") == "warn"


def test_lint_blocks_action_shot_looking_at_camera() -> None:
    valid = {"CHAR_01", "CHAR_01/常态"}
    blk = _char_block("Clip 07 破虚斜劈")
    blk["body"] += (
        "\n**专项镜头模板**：fight_exchange；attack_path=爆冲斜劈。"
        "\n**正向 prompt（英文）**：action keyframe, Jiang slashes forward while looking at viewer, clear frontal face."
    )
    codes = {f["code"]: f["level"] for f in image_qc.lint_shot_block(blk, valid)}
    assert codes.get("combat_camera_eye_contact") == "block"
    assert codes.get("combat_frontal_portrait_bias") == "block"
    assert "combat_camera_eye_contact" in image_qc.HARD_LINT_CODES


def test_lint_does_not_treat_compiled_inline_camera_constraint_as_positive_gaze() -> None:
    valid = {"CHAR_01", "CHAR_01/常态"}
    blk = _char_block("Clip 07 破虚斜劈")
    blk["body"] += (
        "\n**专项镜头模板**：fight_exchange；attack_path=爆冲斜劈。"
        "\n### 负向 prompt\n不要直视镜头/looking at viewer。"
        "\n### 后端编译提交 image prompt\n```text\n"
        "动作瞬间：持刀斜劈；角色视线锁对手；非 POV 镜不看镜头；"
        "限制：直视镜头/looking at viewer；正面肖像摆拍。\n```"
    )

    codes = {f["code"] for f in image_qc.lint_shot_block(blk, valid)}
    assert "combat_camera_eye_contact" not in codes
    assert "combat_frontal_portrait_bias" not in codes


def test_lint_strips_inline_constraint_after_aspect_ratio_space() -> None:
    valid = {"CHAR_01", "CHAR_01/常态"}
    blk = _char_block("Clip 08 斜劈")
    blk["body"] += (
        "\n**专项镜头模板**：fight_exchange；attack_path=持刀斜劈。"
        "\n### 后端编译提交 image prompt\n```text\n"
        "动作瞬间：持刀斜劈；角色视线锁对手；非 POV 镜不看镜头；"
        "画幅：9:16 限制：换脸；直视镜头/looking at viewer；正面肖像摆拍。\n```"
    )

    codes = {f["code"] for f in image_qc.lint_shot_block(blk, valid)}
    assert "combat_camera_eye_contact" not in codes
    assert "combat_frontal_portrait_bias" not in codes


def test_lint_validates_identity_bindings_not_episode_state_prose() -> None:
    valid = {"CHAR_01", "CHAR_01/常态"}
    blk = _char_block("Clip 03", char_id="CHAR_01/常态")
    blk["body"] += (
        "\n**专项镜头模板**：blocking=CHAR_01/囚途残损态 向画右后撤。"
        "\n**本镜状态锁**：CHAR_01/囚途残损态 保持面颊无血。"
    )

    findings = image_qc.lint_shot_block(blk, valid)
    assert not any(f["code"] == "unknown_char_id" for f in findings)


def test_lint_validates_compiled_subject_layout_not_later_camera_state() -> None:
    valid = {"CHAR_01", "CHAR_01/常态", "CHAR_02", "CHAR_02/常态"}
    blk = _char_block("Clip 08", char_id="CHAR_01/常态")
    blk["body"] += (
        "\n### 后端编译提交 image prompt\n```text\n"
        "生成剧情关键帧 主体布局：SLOT_1: CHAR_01/常态 -> LEFT_SLOT；"
        "SLOT_2: CHAR_02/常态 -> RIGHT_SLOT "
        "动作瞬间：递刀。 构图：screen_position=CHAR_01/囚途残损态 画左；"
        "CHAR_02/濒死至死亡态 画右。\n```"
    )

    findings = image_qc.lint_shot_block(blk, valid)
    assert not any(f["code"] == "unknown_char_id" for f in findings)


def test_lint_warns_action_shot_missing_camera_observer_guard() -> None:
    valid = {"CHAR_01", "CHAR_01/常态"}
    blk = _char_block("Clip 08 命中帧", eyeline=False)
    blk["body"] += (
        "\n**视线方向**：保持轴线。"
        "\n**专项镜头模板**：fight_exchange；impact_frame=肩甲命中。"
        "\n**正向 prompt（中文）**：动作命中帧，长枪刺入肩甲，火星飞溅。"
    )
    codes = {f["code"]: f["level"] for f in image_qc.lint_shot_block(blk, valid)}
    assert codes.get("combat_eyeline_guard_missing") == "warn"


def test_lint_accepts_action_shot_with_opponent_eyeline_guard() -> None:
    valid = {"CHAR_01", "CHAR_01/常态"}
    blk = _char_block("Clip 08 命中帧")
    blk["body"] += (
        "\n**专项镜头模板**：fight_exchange；impact_frame=肩甲命中。"
        "\n**正向 prompt（中文）**：动作命中帧，镜头是旁观者，角色不看镜头，视线锁定右后对手和枪线命中点。"
    )
    assert not any(f["code"].startswith("combat_") for f in image_qc.lint_shot_block(blk, valid))


def test_lint_warns_missing_human_anatomy_contract() -> None:
    valid = {"CHAR_01", "CHAR_01/常态"}
    blk = {
        "label": "Clip 02",
        "body": "\n".join([
            "**参考图**：`出图/共享/图片/定妆_沈念_常态.png`",
            "**视线方向**：画左看画右",
            "**资产身份注册层**：`CHAR_01/常态`；从 identity_registry 继承 reference_group。",
            "锚点句：沈念：凤眼薄唇",
            "身份锁定句：保持与参考图①的人脸一致。",
        ]),
    }
    codes = {f["code"]: f["level"] for f in image_qc.lint_shot_block(blk, valid)}
    assert codes.get("anatomy_contract_missing") == "warn"


def test_lint_blocks_hand_action_without_ownership_contract() -> None:
    valid = {"CHAR_01", "CHAR_01/常态"}
    blk = _char_block("Clip 10 抽剑")
    blk["body"] += "\n**正向 prompt（中文）**：沈念右手握住长剑向前递出，剑锋抵住卷轴。"
    codes = {f["code"]: f["level"] for f in image_qc.lint_shot_block(blk, valid)}
    assert codes.get("hand_ownership_contract_missing") == "block"
    assert "hand_ownership_contract_missing" in image_qc.HARD_LINT_CODES


def test_lint_blocks_ground_contact_without_anti_fusion_contract() -> None:
    valid = {"CHAR_01", "CHAR_01/常态"}
    blk = _char_block("Clip 11 废墟站立")
    blk["body"] += "\n**正向 prompt（中文）**：沈念站立于泥土废墟中央，衣摆垂落到地面。"
    codes = {f["code"]: f["level"] for f in image_qc.lint_shot_block(blk, valid)}
    assert codes.get("body_grounding_contract_missing") == "block"


def test_lint_blocks_full_body_without_head_to_toe_contract() -> None:
    valid = {"CHAR_01", "CHAR_01/常态"}
    blk = _char_block("Clip 12 全身立绘")
    blk["body"] += "\n**正向 prompt（中文）**：全身标准立绘，沈念站立展示破旧宫装。"
    codes = {f["code"]: f["level"] for f in image_qc.lint_shot_block(blk, valid)}
    assert codes.get("full_body_integrity_contract_missing") == "block"


def test_human_anatomy_block_enters_summary_findings_and_regen() -> None:
    payload = {
        "checks": {
            "human_anatomy": {
                "available": True,
                "locator": "mediapipe",
                "shots": [{
                    "png": "图片/Clip01_first.png",
                    "max_fingertips": 7,
                    "hands": 1,
                    "verdict": "block",
                }],
            }
        },
        "lint": {"findings": []},
    }

    summary = image_qc.summarize(payload)
    findings = image_qc.to_findings({
        **payload,
        "summary": summary,
        "qc_environment": {"precision_level": "full"},
    })
    regen = image_qc.to_regen_list(payload)

    assert summary["verdict"] == "block"
    assert summary["by_check"]["human_anatomy"]["block"] == 1
    assert any(f["sev"] == "block" and f["dim"] == "human_anatomy_continuity" for f in findings)
    assert regen and "人体解剖 N5" in regen[0]["reasons"]


def test_lint_skips_non_character_shot() -> None:
    # 纯空镜：无身份注册层、无定妆引用 → 不强求身份字段
    blk = {"label": "Clip 11 空镜", "body": "**视线方向**：无人物；画面重心按横轴。\n纯风/雾/残烛空镜。"}
    assert image_qc.lint_shot_block(blk, {"CHAR_01"}) == []


def test_lint_id_check_skipped_when_registry_missing() -> None:
    # valid_ids=None（registry 缺）→ 不做 ID 合法性，但其它字段照查
    blk = _char_block("Clip 03", char_id="CHAR_99/常态")
    codes = {f["code"] for f in image_qc.lint_shot_block(blk, None)}
    assert "unknown_char_id" not in codes


def test_lint_blocks_tail_identity_handoff_without_tail_prompt() -> None:
    valid = {"CHAR_01", "CHAR_01/常态", "CHAR_03", "CHAR_03/人皮态"}
    findings = image_qc.lint_shot_block(_tail_handoff_block(), valid, _registry_forms_for_tail_handoff())
    codes = {f["code"]: f["level"] for f in findings}
    assert codes.get("tail_identity_handoff_missing_prompt") == "block"


def test_lint_blocks_tail_identity_handoff_without_target_reference() -> None:
    valid = {"CHAR_01", "CHAR_01/常态", "CHAR_03", "CHAR_03/人皮态"}
    blk = _tail_handoff_block("**尾帧专用重抽提示**：锁柳娘子身份，不要美化成通用古装脸。")
    findings = image_qc.lint_shot_block(blk, valid, _registry_forms_for_tail_handoff())
    codes = {f["code"]: f["level"] for f in findings}
    assert codes.get("tail_identity_handoff_unlocked") == "block"


def test_lint_passes_tail_identity_handoff_with_target_reference() -> None:
    valid = {"CHAR_01", "CHAR_01/常态", "CHAR_03", "CHAR_03/人皮态"}
    blk = _tail_handoff_block(
        "**尾帧专用重抽提示（2026-06-13）**：`Clip_12_end.png` 是柳娘子失控入点；"
        "以 `CHAR_03/人皮态`、`定妆_柳娘子_人皮态_脸部特写.png` 锁目标身份。"
    )
    findings = image_qc.lint_shot_block(blk, valid, _registry_forms_for_tail_handoff())
    assert not any(f["code"].startswith("tail_identity_handoff_") for f in findings)


def test_lint_tail_identity_handoff_ignores_vfx_weak_alias() -> None:
    valid = {"CHAR_01", "CHAR_01/常态", "CHAR_03", "CHAR_03/诈死复苏态"}
    forms = _registry_forms_for_tail_handoff() + [{
        "id": "CHAR_03",
        "form": "诈死复苏态",
        "key": "CHAR_03/诈死复苏态",
        "asset_key": "CHAR_03__诈死复苏态",
        "display": "CHAR_03__诈死复苏态",
        "strong_aliases": {"CHAR_03", "CHAR_03/诈死复苏态", "CHAR_03__诈死复苏态"},
        "weak_aliases": {"虎山神", "虎妖"},
    }]
    blk = _char_block("Clip 01 接力", char_id="CHAR_01/常态")
    blk["body"] += "\n".join([
        "",
        "**尾帧接力生成方式**：尾帧以本镜首帧 image2image 派生，VFX_虎山神摹影只作后段气息。",
        "**尾帧专用重抽提示**：尾帧身份交接=`CHAR_01/常态` asset_key=`沈念_常态`。",
    ])

    findings = image_qc.lint_shot_block(blk, valid, forms)

    assert not any(f["code"].startswith("tail_identity_handoff_") for f in findings)


def test_lint_skips_tail_identity_handoff_for_final_no_tail_frame() -> None:
    valid = {"CHAR_01", "CHAR_01/觉醒态", "CHAR_03", "CHAR_03/人皮态", "CHAR_03/真容态"}
    blk = _char_block("Clip 15 集尾", char_id="CHAR_01/觉醒态")
    blk["body"] += (
        "\n**剧本描述**：沈念看着地上空宫装与污水，意识到柳娘子是妖。"
        "\n**尾帧接力生成方式**：无（最终镜，无尾帧）"
        "\n**尾帧专用重抽提示**：无"
    )
    findings = image_qc.lint_shot_block(blk, valid, _registry_forms_for_tail_handoff())
    assert not any(f["code"].startswith("tail_identity_handoff_") for f in findings)


def test_lint_blocks_outfit_form_mismatch_for_single_character_shot() -> None:
    valid = {"CHAR_01", "CHAR_01/觉醒态", "CHAR_01/红衣觉醒态"}
    forms = [
        {
            "id": "CHAR_01",
            "form": "觉醒态",
            "key": "CHAR_01/觉醒态",
            "asset_key": "沈念_觉醒态",
            "display": "沈念_觉醒态",
            "reference_stems": {"定妆_沈念_觉醒态"},
            "strong_aliases": {"CHAR_01", "CHAR_01/觉醒态", "沈念_觉醒态", "定妆_沈念_觉醒态"},
            "weak_aliases": {"沈念"},
        }
    ]
    blk = _char_block("Clip 08 红衣近景", char_id="CHAR_01/觉醒态")
    blk["body"] += "\n**正向 prompt（中文）**：沈念穿红色破旧宫装，金瞳痛感觉醒，CU 近景。"
    findings = image_qc.lint_shot_block(blk, valid, forms)
    assert any(f["code"] == "outfit_form_mismatch" and f["level"] == "block" for f in findings)
    assert "outfit_form_mismatch" in image_qc.HARD_LINT_CODES


def test_lint_allows_matching_outfit_form() -> None:
    valid = {"CHAR_01", "CHAR_01/红衣觉醒态"}
    forms = [
        {
            "id": "CHAR_01",
            "form": "红衣觉醒态",
            "key": "CHAR_01/红衣觉醒态",
            "asset_key": "沈念_红衣觉醒态",
            "display": "沈念_红衣觉醒态",
            "reference_stems": {"定妆_沈念_红衣觉醒态"},
            "strong_aliases": {"CHAR_01", "CHAR_01/红衣觉醒态", "沈念_红衣觉醒态", "定妆_沈念_红衣觉醒态"},
            "weak_aliases": {"沈念"},
        }
    ]
    blk = _char_block("Clip 08 红衣近景", char_id="CHAR_01/红衣觉醒态")
    blk["body"] += "\n**正向 prompt（中文）**：沈念穿红色破旧宫装，金瞳痛感觉醒，CU 近景。"
    findings = image_qc.lint_shot_block(blk, valid, forms)
    assert not any(f["code"] == "outfit_form_mismatch" for f in findings)


def test_lint_allows_outfit_group_declared_in_anchor_phrase() -> None:
    valid = {"CHAR_01", "CHAR_01/觉醒态"}
    forms = [
        {
            "id": "CHAR_01",
            "form": "觉醒态",
            "key": "CHAR_01/觉醒态",
            "asset_key": "沈念_觉醒态",
            "anchor_phrase": "凤眼薄唇·乌黑半披发带·月白粗布·左腕淡疤",
            "display": "沈念_觉醒态",
            "reference_stems": {"定妆_沈念_觉醒态"},
            "strong_aliases": {"CHAR_01", "CHAR_01/觉醒态", "沈念_觉醒态", "定妆_沈念_觉醒态"},
            "weak_aliases": {"沈念"},
        }
    ]
    blk = _char_block("Clip 12 月白旧宫装近景", char_id="CHAR_01/觉醒态")
    blk["body"] += "\n**正向 prompt（中文）**：沈念月白旧宫装，金瞳觉醒态残留，CU 近景。"
    findings = image_qc.lint_shot_block(blk, valid, forms)
    assert not any(f["code"] == "outfit_form_mismatch" for f in findings)


def test_lint_allows_outfit_group_declared_in_character_dna() -> None:
    valid = {"CHAR_01", "CHAR_01/觉醒态"}
    forms = [
        {
            "id": "CHAR_01",
            "form": "觉醒态",
            "key": "CHAR_01/觉醒态",
            "asset_key": "沈念_觉醒态",
            "character_dna_text": "同一红色旧宫装，衣领袖型和暗纹延续常态",
            "display": "沈念_觉醒态",
            "reference_stems": {"定妆_沈念_觉醒态"},
            "strong_aliases": {"CHAR_01", "CHAR_01/觉醒态", "沈念_觉醒态", "定妆_沈念_觉醒态"},
            "weak_aliases": {"沈念"},
        }
    ]
    blk = _char_block("Clip 12 红衣觉醒近景", char_id="CHAR_01/觉醒态")
    blk["body"] += "\n**正向 prompt（中文）**：沈念穿红色旧宫装，金瞳觉醒态残留，CU 近景。"
    findings = image_qc.lint_shot_block(blk, valid, forms)
    assert not any(f["code"] == "outfit_form_mismatch" for f in findings)


def test_lint_blocks_registry_driven_outfit_form_mismatch() -> None:
    valid = {"CHAR_01", "CHAR_01/月白寝衣", "CHAR_01/玄青官袍"}
    forms = [
        {
            "id": "CHAR_01",
            "form": "月白寝衣",
            "key": "CHAR_01/月白寝衣",
            "asset_key": "沈念_月白寝衣",
            "character_dna_text": "月白交领寝衣，宽袖，素布腰带",
            "wardrobe_profile": {
                "silhouette": "柔软寝衣，宽袖",
                "collar": "月白交领",
                "aliases": ["月白寝衣", "月白交领寝衣"],
            },
            "display": "沈念_月白寝衣",
            "reference_stems": {"定妆_沈念_月白寝衣"},
            "strong_aliases": {"CHAR_01", "CHAR_01/月白寝衣", "沈念_月白寝衣"},
            "weak_aliases": {"沈念"},
        },
        {
            "id": "CHAR_01",
            "form": "玄青官袍",
            "key": "CHAR_01/玄青官袍",
            "asset_key": "沈念_玄青官袍",
            "character_dna_text": "玄青窄袖官袍，暗银云纹腰封，低反光织物",
            "wardrobe_profile": {
                "silhouette": "直身窄袖官袍",
                "collar": "交领",
                "sleeve": "窄袖",
                "waist": "暗银云纹腰封",
                "aliases": ["玄青窄袖官袍", "暗银云纹腰封"],
            },
            "display": "沈念_玄青官袍",
            "reference_stems": {"定妆_沈念_玄青官袍"},
            "strong_aliases": {"CHAR_01/玄青官袍", "沈念_玄青官袍"},
            "weak_aliases": {"沈念"},
        },
    ]
    blk = _char_block("Clip 18 换官袍", char_id="CHAR_01/月白寝衣")
    blk["body"] += "\n**正向 prompt（中文）**：沈念改穿玄青窄袖官袍，暗银云纹腰封，站在殿门前。"
    findings = image_qc.lint_shot_block(blk, valid, forms)
    assert any(
        f["code"] == "outfit_form_mismatch" and "玄青窄袖官袍" in f["msg"]
        for f in findings
    )


def test_lint_ignores_outfit_terms_inside_taboo_and_topology_bans() -> None:
    valid = {"CHAR_01", "CHAR_01/常态"}
    forms = [
        {
            "id": "CHAR_01",
            "form": "常态",
            "key": "CHAR_01/常态",
            "asset_key": "姜月初_常态",
            "character_dna_text": "玄黑窄袖交领劲装",
            "wardrobe_profile": {"silhouette": "玄黑窄袖交领劲装", "sleeve": "窄袖"},
            "display": "姜月初_常态",
            "reference_stems": {"定妆_姜月初_常态"},
            "strong_aliases": {"CHAR_01", "CHAR_01/常态", "姜月初_常态"},
            "weak_aliases": {"姜月初"},
        }
    ]
    blk = _char_block("Clip 12", char_id="CHAR_01/常态")
    blk["body"] += (
        "\n**正向 prompt（中文）**：姜月初穿玄黑窄袖交领劲装，MCU 近景。"
        "\n**画风规格**：风格禁忌：白衣仙女、月白旧宫装。"
        "\n**资产拓扑锁**：刀鞘/袖口/腰带不得画成刀刃。"
    )

    findings = image_qc.lint_shot_block(blk, valid, forms)
    assert not any(f["code"] == "outfit_form_mismatch" for f in findings)


def test_lint_allows_registry_driven_outfit_form_match() -> None:
    valid = {"CHAR_01", "CHAR_01/玄青官袍"}
    forms = [
        {
            "id": "CHAR_01",
            "form": "玄青官袍",
            "key": "CHAR_01/玄青官袍",
            "asset_key": "沈念_玄青官袍",
            "character_dna_text": "玄青窄袖官袍，暗银云纹腰封，低反光织物",
            "wardrobe_profile": {
                "silhouette": "直身窄袖官袍",
                "collar": "交领",
                "sleeve": "窄袖",
                "waist": "暗银云纹腰封",
                "aliases": ["玄青窄袖官袍", "暗银云纹腰封"],
            },
            "display": "沈念_玄青官袍",
            "reference_stems": {"定妆_沈念_玄青官袍"},
            "strong_aliases": {"CHAR_01", "CHAR_01/玄青官袍", "沈念_玄青官袍"},
            "weak_aliases": {"沈念"},
        }
    ]
    blk = _char_block("Clip 18 官袍近景", char_id="CHAR_01/玄青官袍")
    blk["body"] += "\n**正向 prompt（中文）**：沈念穿玄青窄袖官袍，暗银云纹腰封，MCU 近景。"
    findings = image_qc.lint_shot_block(blk, valid, forms)
    assert not any(f["code"] == "outfit_form_mismatch" for f in findings)


def test_lint_blocks_tail_without_image2image_relay() -> None:
    # 同角色尾帧：声明了接力尾帧素材，但没写 image2image 锁脸 → 纯文生图兜底脸漂 → hard block
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 30 转身")
    blk["body"] += "\n**目标**：`出图/第1集/图片/Clip_30.png` + 接力尾帧 `Clip_30_end.png`"
    codes = {f["code"]: f["level"] for f in image_qc.lint_shot_block(blk, valid)}
    assert codes.get("tail_relay_not_image2image") == "block"


def test_lint_passes_tail_with_image2image_relay() -> None:
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 31 转身")
    blk["body"] += ("\n**尾帧接力生成方式**：以 `Clip_31.png` 图生图为母图，只改表情。"
                    "接力尾帧 `Clip_31_end.png`")
    findings = image_qc.lint_shot_block(blk, valid)
    assert not any(f["code"] == "tail_relay_not_image2image" for f in findings)


def test_lint_tail_relay_allows_negated_text2image_phrase() -> None:
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 31 转身")
    blk["body"] += (
        "\n**参考图**（多图参考派生铁律：禁纯文生图）"
        "\n**尾帧接力生成方式**：以 `Clip_31.png` 图生图为母图，只改表情，"
        "不得纯文生图。接力尾帧 `Clip_31_end.png`"
    )
    findings = image_qc.lint_shot_block(blk, valid)
    assert not any(f["code"] == "tail_relay_not_image2image" for f in findings)


def test_lint_tail_relay_blocks_unnegated_text2image_fallback() -> None:
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 31 转身")
    blk["body"] += (
        "\n**尾帧接力生成方式**：以 `Clip_31.png` 图生图为母图，只改表情，"
        "失败时纯文生图兜底。接力尾帧 `Clip_31_end.png`"
    )
    codes = {f["code"]: f["level"] for f in image_qc.lint_shot_block(blk, valid)}
    assert codes.get("tail_relay_not_image2image") == "block"


def test_lint_no_tail_relay_finding_when_shot_has_no_tail() -> None:
    # 没有尾帧的普通角色镜不应被尾帧锁脸铁律误伤
    valid = {"CHAR_01/常态"}
    findings = image_qc.lint_shot_block(_char_block("Clip 32"), valid)
    assert not any(f["code"] == "tail_relay_not_image2image" for f in findings)


def test_lint_skips_tail_identity_handoff_when_tail_declared_none() -> None:
    valid = {"CHAR_01", "CHAR_01/常态", "CHAR_03", "CHAR_03/人皮态"}
    blk = _char_block("Clip 20 集尾", char_id="CHAR_01/觉醒态")
    blk["body"] += "\n".join([
        "",
        "**目标**：`出图/第1集/图片/Clip_20.png`；尾帧：`无`",
        "**近景/反打身份锁定**：本镜沈念为主，柳娘子在右后景反应仍需引用 `定妆_柳娘子_人皮态_脸部特写.png`。",
        "**尾帧接力生成方式**：本镜若生成柳娘子反应尾帧/变体，只改后景反应，不重画柳娘子脸。",
    ])
    findings = image_qc.lint_shot_block(blk, valid, _registry_forms_for_tail_handoff())
    assert not any(f["code"].startswith("tail_identity_handoff_") for f in findings)


def test_lint_warns_closeup_strong_emotion_without_expression_lib() -> None:
    # 近景 + 强情绪角色镜，未引表情库/脸部特写 → block（表情镜脸漂风险）
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 40 痛哭")
    blk["body"] += "\n**景别**：ECU 面部特写\n**情绪**：崩溃落泪、面部扭曲"
    codes = {f["code"]: f["level"] for f in image_qc.lint_shot_block(blk, valid)}
    assert codes.get("no_expression_lib_ref") == "block"


def test_lint_passes_closeup_emotion_with_expression_lib_ref() -> None:
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 41 痛哭")
    blk["body"] += ("\n**景别**：ECU 面部特写\n**情绪**：崩溃落泪"
                    "\n表情库：引用 `定妆_沈念_常态_脸部特写.png` 同源表情，首尾双帧只插值。")
    findings = image_qc.lint_shot_block(blk, valid)
    assert not any(f["code"] == "no_expression_lib_ref" for f in findings)


def test_lint_no_expression_gate_when_not_closeup() -> None:
    # 远景大表情：景别不近 → 不触发表情库 gate
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 42 远景")
    blk["body"] += "\n**景别**：远景 LS 全身\n**情绪**：崩溃落泪"
    assert not any(f["code"] == "no_expression_lib_ref" for f in image_qc.lint_shot_block(blk, valid))


def test_lint_no_expression_gate_when_neutral_closeup() -> None:
    # 近景但中性表情 → 不强求表情库
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 43 近景中性")
    blk["body"] += "\n**景别**：CU 近景\n**情绪**：平静、无明显表情"
    assert not any(f["code"] == "no_expression_lib_ref" for f in image_qc.lint_shot_block(blk, valid))


def test_lint_expression_gate_skips_non_character_shot() -> None:
    # 空镜即便写了近景+情绪词也不触发（非角色镜先被 is_char_shot 挡掉）
    blk = {"label": "Clip 44 空镜", "body": "**景别**：ECU 特写，135mm\n残烛痛苦地摇曳，无人物。"}
    assert image_qc.lint_shot_block(blk, {"CHAR_01"}) == []


# ── ④ 所有人物近景大表情无表情库 = block ──────────────────────────────
def test_core_char_ids():
    forms = [{"id": "CHAR_01", "scope": "全篇"}, {"id": "CHAR_02", "scope": "第1集起复用"},
             {"id": "CHAR_03", "scope": "核心"}, {"id": "CHAR_04", "scope": ""}]
    assert image_qc.core_char_ids(forms) == {"CHAR_01", "CHAR_03"}


def test_lint_closeup_core_strong_emotion_blocks():
    # 核心角（core_ids 命中）近景大表情无表情库 → block
    out = image_qc._lint_closeup_expression_lib(
        "Clip 50", "ECU 面部特写，沈念崩溃落泪 CHAR_01/常态",
        id_refs=["CHAR_01/常态"], core_ids={"CHAR_01"})
    assert out and out[0]["level"] == "block" and out[0]["code"] == "no_expression_lib_ref"
    assert "no_expression_lib_ref" in image_qc.HARD_LINT_CODES


def test_lint_closeup_noncore_also_blocks():
    # 同样的镜但角色非核心（core_ids 不含）→ 仍然 block；基础表情参考不按主配角放松。
    out = image_qc._lint_closeup_expression_lib(
        "Clip 51", "ECU 面部特写，路人崩溃落泪 CHAR_09/常态",
        id_refs=["CHAR_09/常态"], core_ids={"CHAR_01"})
    assert out and out[0]["level"] == "block" and out[0]["code"] == "no_expression_lib_ref"


def test_lint_closeup_core_with_expression_lib_passes():
    out = image_qc._lint_closeup_expression_lib(
        "Clip 52", "ECU 面部特写，崩溃落泪 CHAR_01/常态，表情库 expressions 首尾双帧只插值",
        id_refs=["CHAR_01/常态"], core_ids={"CHAR_01"})
    assert out == []


def test_lint_closeup_core_with_face_anchor_refs_passes():
    out = image_qc._lint_closeup_expression_lib(
        "Clip 52", "ECU 面部特写，崩溃落泪 CHAR_01/常态，引用 face_anchor_refs 基础脸锚和脸部特写，首尾双帧只插值",
        id_refs=["CHAR_01/常态"], core_ids={"CHAR_01"})
    assert out == []


def test_lint_closeup_strong_emotion_only_in_negative_does_not_block():
    # Fix3：负向 prompt 里 ban 哭/崩溃，正向段是平静镜——不该误判大表情硬拦。
    body = ("ECU 面部特写，CHAR_01/常态 平静凝视\n"
            "**负向 prompt**：崩溃, 哭, 落泪, 狰狞")
    out = image_qc._lint_closeup_expression_lib(
        body and "Clip 53", body, id_refs=["CHAR_01/常态"], core_ids={"CHAR_01"})
    assert out == []
    # 同一强情绪词出现在正向段则照常 block（确认没把整条检查关掉）。
    pos = "ECU 面部特写，CHAR_01/常态 崩溃落泪\n**负向 prompt**：模糊"
    out2 = image_qc._lint_closeup_expression_lib(
        "Clip 53b", pos, id_refs=["CHAR_01/常态"], core_ids={"CHAR_01"})
    assert out2 and out2[0]["code"] == "no_expression_lib_ref"


def test_lint_shot_block_core_expression_block_integration():
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 53 痛哭")
    blk["body"] += "\n**景别**：ECU 面部特写\n**情绪**：崩溃落泪、面部扭曲"
    forms = [{"id": "CHAR_01", "scope": "全篇"}]
    codes = {f["code"]: f["level"] for f in image_qc.lint_shot_block(blk, valid, forms)}
    assert codes.get("no_expression_lib_ref") == "block"
    assert "closeup_core_no_expression_lib" not in codes


# ── A 资产 id lint 对称化 ───────────────────────────────────────────────────────

def _asset_index() -> dict:
    return {
        "ids": {"LOC_01", "PROP_01", "WEAPON_01", "VFX_01"},
        "name_to_id": {
            "冷宫寝殿": "LOC_01",
            "斑驳铜镜": "PROP_01",
            "霜纹长剑": "WEAPON_01",
            "暗金妖力脉冲": "VFX_01",
        },
        "prefix_of": {"LOC_01": "LOC_", "PROP_01": "PROP_", "WEAPON_01": "WEAPON_", "VFX_01": "VFX_"},
    }


def test_load_asset_index(tmp_path: Path) -> None:
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "asset_registry.json").write_text(json.dumps({"assets": [
        {"id": "LOC_01", "type": "scene", "name": "冷宫寝殿",
         "reference_group": {"primary": "出图/共享/图片/定妆_冷宫寝殿.png"}},
        {"id": "PROP_01", "type": "prop", "name": "斑驳铜镜",
         "reference_group": {"primary": "出图/共享/图片/定妆_斑驳铜镜.png"}},
        {"id": "WEAPON_01", "type": "weapon", "name": "霜纹长剑",
         "reference_group": {"primary": "出图/共享/图片/定妆_霜纹长剑.png"}},
    ]}, ensure_ascii=False), encoding="utf-8")
    idx = image_qc.load_asset_index(tmp_path)
    assert idx["ids"] == {"LOC_01", "PROP_01", "WEAPON_01"}
    assert idx["name_to_id"]["冷宫寝殿"] == "LOC_01"
    assert idx["name_to_id"]["斑驳铜镜"] == "PROP_01"   # 由 name 与 reference_group stem 双路映射
    assert idx["name_to_id"]["霜纹长剑"] == "WEAPON_01"
    assert idx["prefix_of"]["PROP_01"] == "PROP_"
    assert idx["prefix_of"]["WEAPON_01"] == "WEAPON_"
    assert image_qc.load_asset_index(tmp_path / "nope") is None


def test_lint_flags_unknown_asset_id() -> None:
    blk = {"label": "Clip 05 道具", "body": "**资产引用注册层**：`WEAPON_99`；从 asset_registry 取参考。"}
    findings = image_qc.lint_shot_block(blk, None, None, _asset_index())
    codes = {f["code"]: f["level"] for f in findings}
    assert codes.get("unknown_asset_id") == "block"


def test_lint_ignores_axis_embedded_asset_id_and_resolves_descriptor_suffix() -> None:
    blk = {
        "label": "Clip 05 轴线",
        "body": (
            "**正反打合同**：axis_id=AXIS_LOC_01_CHAR_01_VS_CHAR_02；"
            "**光位锚**：LOC_01光位从画左后侧进入。"
        ),
    }

    findings = image_qc.lint_shot_block(blk, None, None, _asset_index())
    assert not any(f["code"] == "unknown_asset_id" for f in findings)


def test_lint_warns_asset_ref_without_id() -> None:
    # 用了 定妆_斑驳铜镜（已登记 PROP_01）却没绑 PROP_01 → warn
    blk = {"label": "Clip 06 铜镜", "body": "**参考图**：`出图/共享/图片/定妆_斑驳铜镜.png`（道具定妆）"}
    findings = image_qc.lint_shot_block(blk, None, None, _asset_index())
    codes = {f["code"]: f["level"] for f in findings}
    assert codes.get("asset_ref_without_id") == "warn"


def test_lint_asset_binding_clean_when_id_present() -> None:
    blk = {"label": "Clip 07", "body": "**参考图**：`定妆_霜纹长剑.png`；资产引用注册层：`WEAPON_01`。"}
    findings = image_qc.lint_shot_block(blk, None, None, _asset_index())
    assert not any(f["code"] in ("unknown_asset_id", "asset_ref_without_id") for f in findings)


def test_lint_asset_runs_on_pure_scene_shot() -> None:
    # 纯场景镜（非角色镜）也要跑资产 lint，不被 is_char_shot 早返回挡掉
    blk = {"label": "Clip 08 空镜", "body": "纯场景空镜，用了 `定妆_冷宫寝殿.png` 但没写 LOC 绑定。"}
    findings = image_qc.lint_shot_block(blk, {"CHAR_01"}, None, _asset_index())
    assert any(f["code"] == "asset_ref_without_id" for f in findings)


def test_lint_asset_skipped_when_no_registry() -> None:
    blk = {"label": "Clip 09", "body": "`PROP_99` 与 `定妆_斑驳铜镜.png`"}
    assert image_qc.lint_shot_block(blk, None, None, None) == []   # asset_index=None → 跳过


def test_unknown_asset_id_is_hard_lint() -> None:
    assert "unknown_asset_id" in image_qc.HARD_LINT_CODES


# ── B 道具/特效漂移进落档 ──────────────────────────────────────────────────────

def test_summarize_multimodal_is_advisory() -> None:
    payload = {"checks": {"multimodal": {"available": True, "shots": [
        {"verdict": "block"}, {"verdict": "warn"}]}}, "lint": {"available": True, "findings": []}}
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 0          # 道具/特效初筛即便 block 也只算人判
    assert s["advisory"] == 2
    assert s["verdict"] == "review"


def test_to_findings_emits_multimodal_warn() -> None:
    # sidecar 标 available（隔离 semantic_embedding_required 的缺席升级，专测 palette 初筛 warn 渲染）。
    payload = {"checks": {"multimodal": {"shots": [
        {"png": "图片/Clip_05.png", "verdict": "block", "asset": "PROP_01"}]}},
        "semantic_drift": {"available": True, "findings": []},
        "lint": {"findings": []}}
    fnds = image_qc.to_findings(payload)
    mm = [f for f in fnds if f["dim"] == "multimodal_continuity"]
    assert len(mm) == 1 and mm[0]["sev"] == "warn" and "PROP_01" in mm[0]["msg"]


# ── D 场景/道具/特效漂移人审拼图 ───────────────────────────────────────────────

def test_asset_review_targets_scene_and_multimodal() -> None:
    payload = {"checks": {
        "scene": {"shots": [{"png": "图片/Clip_03.png", "scene": "冷宫寝殿.png", "verdict": "warn"},
                            {"png": "图片/Clip_04.png", "scene": "冷宫寝殿.png", "verdict": "ok"}]},
        "multimodal": {"shots": [{"png": "图片/Clip_07.png", "asset": "PROP_01", "verdict": "block"}]},
    }}
    pm = {"冷宫寝殿": "出图/共享/图片/定妆_冷宫寝殿.png", "PROP_01": "出图/共享/图片/定妆_斑驳铜镜.png"}
    targets = image_qc.asset_review_targets(payload, Path("/r/剧"), "第1集", pm)
    kinds = {(t["kind"], t["shot"]) for t in targets}
    assert ("scene", "Clip_03") in kinds        # warn 进队列
    assert ("asset", "Clip_07") in kinds        # multimodal block 进队列
    assert not any(t["shot"] == "Clip_04" for t in targets)   # ok 不进
    scene_t = next(t for t in targets if t["kind"] == "scene")
    assert scene_t["ref"] == "出图/共享/图片/定妆_冷宫寝殿.png"
    assert scene_t["png_abs"] == "/r/剧/出图/第1集/图片/Clip_03.png"
    assert scene_t["stitch"].endswith("生产数据/image_qc/第1集/asset_review/scene_Clip_03_compare.png")


def test_asset_review_targets_empty_when_clean() -> None:
    payload = {"checks": {"scene": {"shots": [{"png": "a.png", "scene": "x.png", "verdict": "ok"}]},
                          "multimodal": {"shots": []}}}
    assert image_qc.asset_review_targets(payload, Path("/r"), "第1集", {}) == []


def test_resolve_asset_ref_falls_back(tmp_path: Path) -> None:
    # primary_map 命中优先
    pm = {"斑驳铜镜": "出图/共享/图片/定妆_斑驳铜镜.png"}
    assert image_qc._resolve_asset_ref(tmp_path, pm, "斑驳铜镜.png") == "出图/共享/图片/定妆_斑驳铜镜.png"
    # 不命中且无文件 → None
    assert image_qc._resolve_asset_ref(tmp_path, {}, "不存在的资产") is None


def test_lifecycle_regression_is_hard_lint() -> None:
    # F：资产状态回退作为 lint 硬码项，summarize 当 hard
    payload = {"checks": {}, "lint": {"available": True, "findings": [
        {"level": "block", "code": "lifecycle_regression", "msg": "PROP_03：状态回退"}]}}
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 1
    assert s["verdict"] == "block"
    assert "lifecycle_regression" in image_qc.HARD_LINT_CODES


def test_summarize_hard_vs_advisory() -> None:
    payload = {
        "checks": {
            "face": {"available": True, "shots": [{"verdict": "block"}, {"verdict": "ok"}]},   # hard 1
            "outfit": {"available": True, "shots": [{"verdict": "block"}, {"verdict": "warn"}]},  # advisory 2（初筛）
            "scene": {"available": True, "shots": []},
            "seam": {"available": True, "seams": [{"verdict": "warn"}]},                         # advisory 1
            "anchors": {"available": True, "anchors": [{"char": "x", "verdict": "block"}]},      # advisory 1
        },
        "lint": {"available": True, "findings": [
            {"level": "block", "code": "unknown_char_id"},   # hard 1
            {"level": "warn", "code": "no_eyeline"},          # advisory 1
        ]},
    }
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 2    # face block + lint unknown_char_id
    assert s["advisory"] == 5       # outfit block+warn + seam warn + anchors block + lint warn
    assert s["verdict"] == "block"


def test_summarize_outfit_block_alone_is_review_not_block() -> None:
    # 服装/场景初筛即便报 block，也只算 review（人判），不强制重抽
    payload = {"checks": {"outfit": {"available": True, "shots": [{"verdict": "block"}]}},
               "lint": {"available": True, "findings": []}}
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 0
    assert s["verdict"] == "review"


def test_summarize_clean_is_ok() -> None:
    payload = {"checks": {"face": {"available": True, "shots": [{"verdict": "ok"}]}},
               "lint": {"available": True, "findings": []}}
    assert image_qc.summarize(payload)["verdict"] == "ok"


def test_summarize_pillow_fallback_degrades_to_review() -> None:
    payload = {"checks": {"face": {"available": True, "mode": "pillow_fallback",
                                   "shots": [{"verdict": "ok", "degraded_face": True, "closeup": False}]}},
               "lint": {"available": True, "findings": []}}
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 0
    assert s["degraded"] is True
    assert s["verdict"] == "review"


def test_missing_image_target_is_hard_but_not_counted_as_face_failure() -> None:
    payload = {
        "checks": {
            "face": {
                "available": True,
                "mode": "pillow_fallback",
                "shots": [{
                    "png": "图片/Clip_01.png",
                    "verdict": "missing",
                    "degraded_face": True,
                    "closeup": True,
                }],
            }
        },
        "lint": {"available": True, "findings": []},
    }
    summary = image_qc.summarize(payload)
    assert summary["hard_blocks"] == 1
    assert summary["by_check"]["face"]["block"] == 0
    assert summary["by_check"]["image_targets_missing"]["block"] == 1
    assert "face_degraded_closeup" not in summary["by_check"]

    findings = image_qc.to_findings(payload)
    missing = [f for f in findings if f["dim"] == "image_artifact_presence"]
    assert len(missing) == 1
    assert missing[0]["sev"] == "block"
    assert "不是崩脸判定" in missing[0]["msg"]
    assert not any("崩脸 G1 block" in f["msg"] for f in findings)


def test_summarize_unavailable_visual_checks_degrades_to_review() -> None:
    payload = {
        "checks": {
            "face": {"available": False, "notes": ["缺 Pillow/insightface"]},
            "outfit": {"available": False, "notes": ["缺 Pillow"]},
            "seam": {"notes": ["未装 Pillow——接缝机检跳过"]},
        },
        "lint": {"available": True, "findings": []},
    }
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 0
    assert s["advisory"] == 0
    assert s["verdict"] == "review"
    assert s["degraded"] is True
    assert s["unavailable_visual_checks"] == ["face", "outfit", "seam"]


def test_qc_environment_reports_precision_and_stage_jump() -> None:
    full = {
        "checks": {"face": {"available": True, "mode": "insightface", "shots": []},
                   "outfit": {"available": True, "shots": []},
                   "scene": {"available": True, "shots": []},
                   "seam": {"available": True, "seams": []}},
        "summary": {"verdict": "ok"},
    }
    env = image_qc.qc_environment(full)
    assert env["precision_level"] == "full"
    assert env["jump_to_stage"] == "video"
    assert env["recommended_install"] == ""

    full_review = {
        "checks": {"face": {"available": True, "mode": "insightface", "shots": []},
                   "outfit": {"available": True, "shots": [{"verdict": "warn"}]},
                   "scene": {"available": True, "shots": []},
                   "seam": {"available": True, "seams": []}},
        "summary": {"verdict": "review", "hard_blocks": 0, "advisory": 1},
    }
    env = image_qc.qc_environment(full_review)
    assert env["precision_level"] == "full"
    assert env["jump_to_stage"] == "video"
    assert "非阻断初筛" in env["jump_reason"]

    degraded = {
        "checks": {"face": {"available": True, "mode": "pillow_fallback", "shots": []}},
        "summary": {"verdict": "ok"},
    }
    env = image_qc.qc_environment(degraded)
    assert env["precision_level"] == "degraded"
    assert env["jump_to_stage"] == "image"
    assert "insightface" in " ".join(env["missing_or_degraded"])
    assert "facefusion" in env["recommended_install"]

    none = {
        "checks": {
            "face": {"available": False, "notes": ["缺 Pillow"]},
            "outfit": {"available": False, "notes": ["缺 Pillow"]},
            "scene": {"available": False, "notes": ["缺 Pillow"]},
            "seam": {"available": False, "notes": ["缺 Pillow"]},
        },
        "summary": {"verdict": "review"},
    }
    env = image_qc.qc_environment(none)
    assert env["precision_level"] == "none"
    assert env["jump_to_stage"] == "image_qc_setup"


def test_summarize_seam_block_is_hard() -> None:
    # 接缝接力 block = 真接力断（seam_analyze 已对设计切镜降 info）→ 与崩脸同级 hard，gate 硬拦
    payload = {"checks": {"seam": {"available": True, "seams": [{"verdict": "block"}, {"verdict": "warn"}]}},
               "lint": {"available": True, "findings": []}}
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 1   # seam block
    assert s["advisory"] == 1      # seam warn
    assert s["verdict"] == "block"


def test_to_findings_emits_seam_block_as_block() -> None:
    payload = {"checks": {"seam": {"available": True, "seams": [
        {"verdict": "block", "tail": "镜头05_end.png", "next_first": "镜头06.png", "dist": 33}]}},
        "lint": {"findings": []}}
    findings = image_qc.to_findings(payload)
    seam_f = [f for f in findings if "接缝" in f["msg"]]
    assert seam_f and seam_f[0]["sev"] == "block"


def test_normalize_seam_availability_marks_absent_dir_unverified(tmp_path) -> None:
    # Fix1：seam_analyze 在缺/空 图片目录回 {"seams":[], "notes":[...]} 无 available 键。
    # 缺目录 → available False（未验，不是 ok）。
    res = image_qc._normalize_seam_availability(
        {"seams": [], "notes": ["无 …图片——出图后再跑接缝机检。"]}, str(tmp_path), "第1集")
    assert res["available"] is False
    assert res["availability_reason"] == "no_episode_images"
    # 空目录（存在但无 PNG）同样 available False——这是最隐蔽的零覆盖。
    (tmp_path / "出图" / "第1集" / "图片").mkdir(parents=True)
    res2 = image_qc._normalize_seam_availability({"seams": [], "notes": []}, str(tmp_path), "第1集")
    assert res2["available"] is False
    # 有真实 PNG → available True。
    (tmp_path / "出图" / "第1集" / "图片" / "Clip_01.png").write_bytes(b"x")
    res3 = image_qc._normalize_seam_availability({"seams": [], "notes": []}, str(tmp_path), "第1集")
    assert res3["available"] is True
    assert res3["availability_reason"] == "ready"
    # seam_analyze 自置 available（失败/缺依赖）时不被覆盖。
    res4 = image_qc._normalize_seam_availability(
        {"available": False, "notes": ["未装 Pillow"]}, str(tmp_path), "第1集")
    assert res4["available"] is False


def test_seam_unverified_degrades_to_review_like_face() -> None:
    # Fix1：seam available False 与 face 一致——经 unavailable_visual_checks 走 degraded→review，
    # 不再因 seams 为空被当成干净 ok（零接缝覆盖却放行）。
    payload = {"checks": {"face": {"available": True, "mode": "insightface", "shots": [{"verdict": "ok"}]},
                          "seam": {"available": False, "seams": [], "notes": ["无 …图片"]}},
               "lint": {"available": True, "findings": []}}
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 0
    assert "seam" in s["unavailable_visual_checks"]
    assert s["degraded"] is True
    assert s["verdict"] == "review"


def test_no_episode_images_does_not_downgrade_installed_qc_environment() -> None:
    payload = {
        "checks": {
            "face": {"available": True, "mode": "insightface", "shots": []},
            "outfit": {"available": True, "shots": []},
            "scene": {"available": True, "shots": []},
            "seam": {
                "available": False,
                "availability_reason": "no_episode_images",
                "seams": [],
                "notes": ["本集尚无 PNG"],
            },
        },
        "summary": {"verdict": "block", "hard_blocks": 1},
    }
    env = image_qc.qc_environment(payload)
    assert env["precision_level"] == "full"
    assert env["missing_or_degraded"] == []
    assert env["jump_to_stage"] == "image"


def test_summarize_strict_pixel_promotes_outfit_block_to_hard() -> None:
    # Fix2：默认 off 时 outfit/scene block 仍是 advisory（review）；--strict-pixel 升 hard（block）。
    payload = {"checks": {"outfit": {"available": True, "shots": [{"verdict": "block"}]},
                          "scene": {"available": True, "shots": [{"verdict": "block"}, {"verdict": "warn"}]}},
               "lint": {"available": True, "findings": []}}
    lax = image_qc.summarize(payload)
    assert lax["hard_blocks"] == 0 and lax["verdict"] == "review"
    strict = image_qc.summarize(payload, strict_pixel=True)
    assert strict["hard_blocks"] == 2   # outfit block + scene block
    assert strict["verdict"] == "block"
    # warn 不升 hard，仍计 advisory。
    assert strict["advisory"] == 1


def test_degraded_closeup_face_is_hard_block_but_non_closeup_is_review() -> None:
    # 降级精度（pillow_fallback）：近景脸无法验同人 → hard block；远景脸仍只 review
    payload = {
        "checks": {"face": {"available": True, "mode": "pillow_fallback", "shots": [
            {"png": "镜头03.png", "verdict": "ok", "degraded_face": True, "closeup": True},
            {"png": "镜头08.png", "verdict": "ok", "degraded_face": True, "closeup": False},
        ]}},
        "lint": {"findings": []},
    }
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 1   # only the closeup shot
    assert s["verdict"] == "block"
    findings = image_qc.to_findings(payload)
    deg = [f for f in findings if "降级精度近景" in f["msg"]]
    assert len(deg) == 1 and deg[0]["sev"] == "block" and "镜头03" in deg[0]["loc"]


def test_face_review_targets_for_degraded_closeup() -> None:
    # 降级近景脸 → 人审拼图目标：ref=定妆主参考，stitch 落 生产数据/image_qc/<ep>/face_review。
    payload = {
        "checks": {"face": {"available": True, "mode": "pillow_fallback", "shots": [
            {"png": "图片/Clip_12_脸.png", "chars": ["沈念_常态"], "verdict": "ok",
             "degraded_face": True, "closeup": True},
            {"png": "图片/Clip_08.png", "chars": ["沈念_常态"], "verdict": "ok",
             "degraded_face": True, "closeup": False},   # 远景 → 不进队列
        ]}},
    }
    targets = image_qc.face_review_targets(payload, Path("/r/剧"), "第1集")
    assert len(targets) == 1
    t = targets[0]
    assert t["shot"] == "Clip_12"
    assert t["char"] == "沈念_常态"
    assert t["ref"] == "出图/共享/图片/定妆_沈念_常态.png"
    assert t["png_abs"] == "/r/剧/出图/第1集/图片/Clip_12_脸.png"
    assert t["stitch"].endswith("生产数据/image_qc/第1集/face_review/Clip_12_compare.png")


def test_face_review_targets_empty_when_full_precision() -> None:
    # full（insightface）模式无 degraded_face → 队列为空
    payload = {"checks": {"face": {"mode": "insightface", "shots": [
        {"png": "图片/Clip_03.png", "chars": ["沈念"], "verdict": "ok"}]}}}
    assert image_qc.face_review_targets(payload, Path("/r"), "第1集") == []


def test_stitch_for_png_lookup() -> None:
    payload = {"face_human_review": [
        {"png": "图片/Clip_12_脸.png", "stitch": "/r/生产数据/.../Clip_12_compare.png", "stitched": True},
        {"png": "图片/Clip_13.png", "stitch": "/r/.../Clip_13_compare.png", "stitched": False},
    ]}
    assert image_qc._stitch_for_png(payload, "图片/Clip_12_脸.png").endswith("Clip_12_compare.png")
    assert image_qc._stitch_for_png(payload, "图片/Clip_13.png") is None   # 未成功生成 → None
    assert image_qc._stitch_for_png(payload, "图片/none.png") is None


def test_to_findings_degraded_closeup_appends_stitch_path() -> None:
    payload = {
        "checks": {"face": {"available": True, "mode": "pillow_fallback", "shots": [
            {"png": "图片/Clip_12_脸.png", "verdict": "ok", "degraded_face": True, "closeup": True}]}},
        "lint": {"findings": []},
        "face_human_review": [
            {"png": "图片/Clip_12_脸.png", "stitch": "生产数据/image_qc/第1集/face_review/Clip_12_compare.png",
             "stitched": True}],
    }
    findings = image_qc.to_findings(payload)
    deg = [f for f in findings if "降级精度近景" in f["msg"]]
    assert len(deg) == 1
    assert "人审并排图" in deg[0]["msg"] and "Clip_12_compare.png" in deg[0]["msg"]


def _coverage_payload(verdict: str = "ok") -> dict:
    return {
        "checks": {"face": {"available": True, "mode": "insightface", "shots": [
            {"png": "图片/Clip_02_冷开场.png", "verdict": verdict, "chars": ["沈念"]},
        ]}},
        "lint": {"available": True, "findings": [], "character_shots": [
            {"label": "Clip 02 冷开场", "shot": "Clip_02",
             "png": "出图/第1集/图片/Clip_02_冷开场.png", "identity_refs": ["CHAR_01/常态"]},
        ]},
    }


def test_face_reference_coverage_requires_full_face_row_for_landed_character_png(tmp_path: Path) -> None:
    png = tmp_path / "出图" / "第1集" / "图片" / "Clip_02_冷开场.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"x")
    payload = _coverage_payload()
    payload["checks"]["face"]["shots"] = []
    coverage = image_qc.face_reference_coverage(payload, tmp_path, "第1集")
    assert coverage["verdict"] == "block"
    assert coverage["missing"][0]["reason"] == "no_face_comparison"

    payload["face_reference_coverage"] = coverage
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 1
    assert s["verdict"] == "block"


def test_face_reference_coverage_blocks_warn_face_match(tmp_path: Path) -> None:
    png = tmp_path / "出图" / "第1集" / "图片" / "Clip_02_冷开场.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"x")
    payload = _coverage_payload("warn")
    coverage = image_qc.face_reference_coverage(payload, tmp_path, "第1集")
    assert coverage["verdict"] == "block"
    assert coverage["missing"][0]["reason"] == "face_verdict_warn"

    payload["face_reference_coverage"] = coverage
    findings = image_qc.to_findings(payload)
    strict = [f for f in findings if "角色脸定妆比对覆盖缺口" in f["msg"]]
    assert len(strict) == 1 and strict[0]["sev"] == "block"


def test_face_reference_coverage_passes_full_ok_match(tmp_path: Path) -> None:
    png = tmp_path / "出图" / "第1集" / "图片" / "Clip_02_冷开场.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"x")
    coverage = image_qc.face_reference_coverage(_coverage_payload("ok"), tmp_path, "第1集")
    assert coverage["verdict"] == "ok"
    assert coverage["required"] == 1
    assert coverage["covered"] == 1
    assert coverage["missing"] == []


def test_face_reference_coverage_skips_per_target_faceless_reaction_anchor(tmp_path: Path) -> None:
    png = tmp_path / "出图" / "第1集" / "图片" / "Clip06_mid_reaction.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"x")
    payload = {
        "checks": {"face": {"available": True, "mode": "insightface", "shots": [
            {"png": "图片/Clip06_mid_reaction.png", "verdict": "noface"},
        ]}},
        "lint": {"available": True, "findings": [], "character_shots": [
            {"label": "Clip 06", "shot": "Clip_06",
             "png": "出图/第1集/图片/Clip06_mid_reaction.png",
             "identity_refs": ["CHAR_01/常态"],
             "face_coverage_required": False,
             "face_check_policy": "faceless_reaction_anchor"},
        ]},
    }

    coverage = image_qc.face_reference_coverage(payload, tmp_path, "第1集")

    assert coverage["verdict"] == "ok"
    assert coverage["required"] == 0
    assert coverage["missing"] == []
    assert coverage["skipped"][0]["reason"] == "faceless_reaction_anchor"


def test_storyboard_anchor_focus_refs_exempts_basin_detail_insert(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    storyboard = root / "脚本" / ep / "storyboard.json"
    storyboard.parent.mkdir(parents=True)
    storyboard.write_text(json.dumps({"clips": [{
        "id": "EP01_CLIP07",
        "continuity": {"anchors": [{
            "anchor_png": "出图/第1集/图片/EP01_CLIP07_a1.png",
            "at_sec": 2.4,
        }]},
        "shots": [{
            "t": "2.4-3.9s",
            "lens": "ECU insert·固定慢推",
            "desc": "水滴滑过破损盆底，一缕青金幽光从细纹中亮起",
        }],
    }]}, ensure_ascii=False), encoding="utf-8")
    registry = root / "出图" / "共享" / "identity_registry.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"characters": [
        {"id": "CHAR_01", "name": "贺平生"},
    ]}, ensure_ascii=False), encoding="utf-8")

    refs = image_qc._storyboard_anchor_focus_refs(
        root, ep, "出图/第1集/图片/EP01_CLIP07_a1.png", ["CHAR_01/常态"]
    )

    assert refs == ["__STORYBOARD_FACE_EXEMPT_DETAIL__"]


def test_face_reference_coverage_prefers_exact_png_over_clip_worst(tmp_path: Path) -> None:
    png = tmp_path / "出图" / "第1集" / "图片" / "Clip_02_冷开场_mid.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"x")
    payload = {
        "checks": {"face": {"available": True, "mode": "insightface", "shots": [
            {"png": "图片/Clip_02_冷开场.png", "verdict": "warn", "chars": ["沈念"]},
            {"png": "图片/Clip_02_冷开场_mid.png", "verdict": "ok", "chars": ["沈念"]},
        ]}},
        "lint": {"available": True, "findings": [], "character_shots": [
            {"label": "Clip 02 冷开场", "shot": "Clip_02",
             "png": "Clip_02_冷开场_mid.png", "identity_refs": ["CHAR_01/常态"]},
        ]},
    }

    coverage = image_qc.face_reference_coverage(payload, tmp_path, "第1集")
    assert coverage["verdict"] == "ok"
    assert coverage["covered"] == 1
    assert coverage["missing"] == []


def test_face_reference_coverage_does_not_block_prompt_before_png(tmp_path: Path) -> None:
    coverage = image_qc.face_reference_coverage(_coverage_payload("ok"), tmp_path, "第1集")
    assert coverage["verdict"] == "ok"
    assert coverage["required"] == 0
    assert len(coverage["pending"]) == 1


def test_face_reference_coverage_does_not_treat_endframe_as_firstframe(tmp_path: Path) -> None:
    png = tmp_path / "出图" / "第1集" / "图片" / "Clip_02_end.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"x")
    coverage = image_qc.face_reference_coverage(_coverage_payload("ok"), tmp_path, "第1集")
    assert coverage["verdict"] == "ok"
    assert coverage["required"] == 0
    assert len(coverage["pending"]) == 1


def test_to_regen_list_includes_face_reference_coverage_missing() -> None:
    payload = {
        "checks": {},
        "lint": {"findings": []},
        "face_reference_coverage": {"missing": [
            {"label": "Clip 02 冷开场", "shot": "Clip_02", "png": "图片/Clip_02_冷开场.png",
             "reason": "no_face_comparison"}
        ]},
    }
    regen = image_qc.to_regen_list(payload)
    assert len(regen) == 1
    assert regen[0]["shot"] == "Clip_02"
    assert "脸部定妆比对覆盖:no_face_comparison" in regen[0]["reasons"]


def _write_image_event(root: Path, ep: str, asset: str, *, provider: str = "Codex",
                       method: str = "image2image", event: str = "generation") -> None:
    prod = root / "生产数据"
    prod.mkdir(parents=True, exist_ok=True)
    payload = {
        "kind": "n2d_production_event",
        "version": 1,
        "episode": ep,
        "stage": "image",
        "event": event,
        "source": provider,
        "generation": {"asset": asset, "status": "pass", "method": method},
        "cost": {"provider": provider},
        "meta": {"method": method},
    }
    with open(prod / "production_events.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def test_prohibited_face_patch_outputs_block_summary_and_regen(tmp_path: Path) -> None:
    _write_image_event(
        tmp_path,
        "第1集",
        "出图/第1集/图片/Clip_02_冷开场.png",
        provider="local_face_patch",
        method="crop_resize_color_match_alpha_blend",
        event="redraw",
    )
    report = image_qc.prohibited_face_patch_outputs(tmp_path, "第1集")
    assert report["verdict"] == "block"
    assert report["outputs"][0]["shot"] == "Clip_02"

    payload = {"checks": {}, "lint": {"findings": []}, "prohibited_face_patch": report}
    summary = image_qc.summarize(payload)
    assert summary["hard_blocks"] == 1
    assert summary["verdict"] == "block"
    assert summary["by_check"]["prohibited_face_patch"]["block"] == 1

    findings = image_qc.to_findings(payload)
    assert len(findings) == 1
    assert findings[0]["sev"] == "block"
    assert "embedding 分数不是合格目标" in findings[0]["msg"]

    regen = image_qc.to_regen_list(payload)
    assert regen[0]["shot"] == "Clip_02"
    assert "本地贴脸修复产物禁用" in regen[0]["reasons"]


def test_prohibited_face_patch_outputs_cleared_by_later_real_generation(tmp_path: Path) -> None:
    asset = "出图/第1集/图片/Clip_02_冷开场.png"
    _write_image_event(tmp_path, "第1集", asset, provider="local_face_patch",
                       method="crop_resize_color_match_alpha_blend", event="redraw")
    _write_image_event(tmp_path, "第1集", asset, provider="Codex",
                       method="image2image", event="generation")

    report = image_qc.prohibited_face_patch_outputs(tmp_path, "第1集")
    assert report["verdict"] == "ok"
    assert report["outputs"] == []


def test_to_findings_maps_severity_and_dims() -> None:
    payload = {
        "checks": {
            "face": {"shots": [{"png": "镜头3.png", "verdict": "block"}, {"png": "镜头4.png", "verdict": "ok"}]},
            "outfit": {"shots": [{"png": "镜头5.png", "verdict": "block"}]},   # 初筛 → warn
            "scene": {"shots": [{"png": "镜头6.png", "verdict": "warn", "kind": "光色"}]},
            "seam": {"seams": [{"tail": "镜头7_end.png", "next_first": "镜头8.png", "dist": 40, "verdict": "warn"}]},
            "anchors": {"anchors": [{"char": "沈念", "verdict": "block"}]},     # 初筛 → warn
        },
        "lint": {"findings": [
            {"level": "block", "code": "unknown_char_id", "msg": "Clip 9：非法 CHAR_99"},
            {"level": "warn", "code": "no_eyeline", "msg": "Clip 9：缺视线"},
        ]},
    }
    fnds = image_qc.to_findings(payload)
    by_sev = {(f["dim"], f["sev"]) for f in fnds}
    assert ("character_consistency", "block") in by_sev      # 崩脸 hard
    assert ("outfit_consistency", "warn") in by_sev          # 服装初筛降 warn
    assert ("scene_consistency", "warn") in by_sev           # 场景/接缝初筛
    assert ("image_prompt_lint", "block") in by_sev          # 非法 ID hard
    assert ("image_prompt_lint", "warn") in by_sev           # 漏视线 warn
    # face 的 ok 行不进 findings；服装 block 不会变成 block sev
    assert not any(f["dim"] == "outfit_consistency" and f["sev"] == "block" for f in fnds)
    assert all(f["return_to_stage"] == "image" for f in fnds)


def test_to_findings_reports_unavailable_visual_checks() -> None:
    payload = {
        "checks": {
            "face": {"available": False, "notes": ["face_consistency 不可用"]},
            "scene": {"available": False, "notes": ["scene_consistency 不可用"]},
        },
        "lint": {"findings": []},
    }
    fnds = image_qc.to_findings(payload)
    assert len(fnds) == 2
    assert all(f["sev"] == "warn" for f in fnds)
    assert any(f["dim"] == "character_consistency" and "未执行" in f["msg"] for f in fnds)
    assert any(f["dim"] == "scene_consistency" and "未执行" in f["msg"] for f in fnds)


def test_to_findings_blocks_precision_none() -> None:
    payload = {
        "qc_environment": {"precision_level": "none"},
        "checks": {},
        "lint": {"findings": []},
    }
    fnds = image_qc.to_findings(payload)
    assert any(f["sev"] == "block" and f["dim"] == "image_qc_precision" for f in fnds)


def test_to_findings_warns_precision_degraded() -> None:
    payload = {
        "qc_environment": {"precision_level": "degraded"},
        "checks": {},
        "lint": {"findings": []},
    }
    fnds = image_qc.to_findings(payload)
    assert any(f["sev"] == "warn" and f["dim"] == "image_qc_precision" for f in fnds)


def test_to_findings_blocks_semantic_embedding_missing_for_registered_assets() -> None:
    payload = {
        "semantic_drift": {"available": False, "notes": ["missing"], "findings": []},
        "checks": {"multimodal": {"shots": [
            {"png": "图片/Clip_01.png", "asset": "PROP_01", "verdict": "ok"},
        ]}},
        "lint": {"findings": []},
    }
    fnds = image_qc.to_findings(payload)
    assert any(f["sev"] == "block" and f["dim"] == "multimodal_continuity" for f in fnds)
    assert image_qc.summarize(payload)["verdict"] == "block"


def test_semantic_embedding_required_fires_when_sidecar_absent() -> None:
    # 堵静默消失洞：semantic_drift sidecar 整段缺席（模块加载/执行异常被吞），payload 无 "semantic_drift" 键，
    # 但有已登记关键资产 → 仍须升 hard block（否则一次模块加载失败就让非脸兜底无声蒸发）。
    payload = {
        "checks": {"scene": {"shots": [
            {"png": "图片/Clip_01.png", "scene": "LOC_01", "verdict": "ok"},
        ]}},
        "lint": {"findings": []},
    }
    assert image_qc.semantic_embedding_required(payload)        # 缺席 == unavailable
    assert image_qc.summarize(payload)["verdict"] == "block"


def test_semantic_embedding_not_required_when_sidecar_ran_ok() -> None:
    # 对照：sidecar 跑通(available True) → 不在此升 hard（改由 findings 表达），避免重复阻断。
    payload = {
        "semantic_drift": {"available": True, "findings": []},
        "checks": {"scene": {"shots": [
            {"png": "图片/Clip_01.png", "scene": "LOC_01", "verdict": "ok"},
        ]}},
        "lint": {"findings": []},
    }
    assert image_qc.semantic_embedding_required(payload) == []


def test_semantic_drift_findings_enter_summary_and_gate_findings() -> None:
    payload = {
        "semantic_drift": {"available": True, "findings": [
            {"level": "warn", "code": "semantic_drift_low", "msg": "PROP_01 语义漂移疑似"},
            {"level": "info", "code": "semantic_drift_lighting", "msg": "LOC_01 只是灯光差异"},
        ]},
        "checks": {},
        "lint": {"findings": []},
    }

    summary = image_qc.summarize(payload)
    findings = image_qc.to_findings(payload)

    assert summary["by_check"]["semantic_drift"]["warn"] == 1
    assert summary["advisory"] == 1
    assert any(f["sev"] == "warn" and f["dim"] == "multimodal_continuity" and "PROP_01" in f["msg"]
               for f in findings)
    assert any(f["sev"] == "info" and f["dim"] == "multimodal_continuity" and "LOC_01" in f["msg"]
               for f in findings)


def test_tone_light_contract_findings_enter_summary_and_gate_findings() -> None:
    # 契约像素兜底（色调/光位）的 warn findings 进 summary.advisory + to_findings(style_consistency)。
    payload = {
        "tone_light_contract": {"available": True, "checked": 8, "findings": [
            {"level": "warn", "code": "tone_warmth_contradiction", "msg": "色调像素兜底：契约冷 vs 渲染暖"},
        ]},
        "checks": {},
        "lint": {"findings": []},
    }
    summary = image_qc.summarize(payload)
    findings = image_qc.to_findings(payload)
    assert summary["by_check"]["tone_light_contract"]["warn"] == 1
    assert summary["advisory"] == 1
    assert any(f["sev"] == "warn" and f["dim"] == "style_consistency" and "色调像素兜底" in f["msg"]
               for f in findings)


def test_shot_scale_contract_findings_enter_summary_and_gate_findings() -> None:
    # 契约像素兜底（景别）的 warn findings 进 summary.advisory + to_findings(style_consistency)。
    payload = {
        "shot_scale_contract": {"available": True, "checked": 4, "findings": [
            {"level": "warn", "code": "shot_scale_closeup_tiny_face", "msg": "景别像素兜底：镜1 声明 CU 但脸很小"},
        ]},
        "checks": {},
        "lint": {"findings": []},
    }
    summary = image_qc.summarize(payload)
    findings = image_qc.to_findings(payload)
    assert summary["by_check"]["shot_scale_contract"]["warn"] == 1
    assert summary["advisory"] == 1
    assert any(f["sev"] == "warn" and f["dim"] == "style_consistency" and "景别像素兜底" in f["msg"]
               for f in findings)


def test_style_attribution_block_enters_summary_and_gate_findings() -> None:
    payload = {
        "style_attribution": {"available": True, "checked": 0, "findings": [
            {"level": "block", "code": "style_anchor_missing", "msg": "缺 style_anchor"},
        ]},
        "checks": {},
        "lint": {"findings": []},
    }

    summary = image_qc.summarize(payload)
    findings = image_qc.to_findings(payload)

    assert summary["verdict"] == "block"
    assert summary["by_check"]["style_attribution"]["block"] == 1
    assert any(f["sev"] == "block" and f["dim"] == "style_consistency" and "style_anchor" in f["msg"]
               for f in findings)


def test_to_findings_blocks_high_cross_episode_face_drift() -> None:
    payload = {
        "cross_episode_face_drift": {"entries": [
            {"char": "CHAR_01", "episode_from": "第1集", "episode_to": "第3集",
             "from_mean": 0.82, "to_mean": 0.60, "drop": 0.22, "severity": "high"},
        ]},
        "checks": {},
        "lint": {"findings": []},
    }
    fnds = image_qc.to_findings(payload)
    assert any(f["sev"] == "block" and f["dim"] == "character_consistency" for f in fnds)
    assert image_qc.summarize(payload)["verdict"] == "block"


def test_to_findings_empty_when_clean() -> None:
    payload = {"checks": {"face": {"shots": [{"png": "a.png", "verdict": "ok"}]}},
               "lint": {"findings": []}}
    assert image_qc.to_findings(payload) == []


def test_shot_key_extracts_clip_number() -> None:
    assert image_qc._shot_key("图片/Clip_18_铜镜金瞳.png") == "Clip_18"
    assert image_qc._shot_key("Clip 09：角色镜缺参考图") == "Clip_09"
    assert image_qc._shot_key("镜头7_end.png") == "Clip_07"
    assert image_qc._shot_key(None) is None
    assert image_qc._shot_key("空镜.png") == "空镜.png"   # 提不出镜号 → 退回文件名


def test_affected_shot_args_only_emits_executable_clip_ids() -> None:
    regen = [
        {"shot": "Clip_01"},
        {"shot": "Clip_01"},
        {"shot": "1.4）。建议补充物理镜头参数"},
        {"shot": "Clip_27"},
        {"shot": "cv2——faceless 像素核验跳过"},
    ]

    assert image_qc.affected_shot_args(regen) == ["Clip_01", "Clip_27"]


def test_to_regen_list_only_unusable_shots() -> None:
    payload = {
        "checks": {
            "face": {"shots": [{"png": "图片/Clip_03_脸.png", "verdict": "block"},   # 崩脸 → 重生成
                               {"png": "图片/Clip_04_脸.png", "verdict": "ok"}]},
            "outfit": {"shots": [{"png": "图片/Clip_18_金瞳.png", "verdict": "block"},  # 校准后服装漂 → 重生成
                                 {"png": "图片/Clip_02_旧疤.png", "verdict": "warn"}]},  # warn → 能用，保留
            "scene": {"shots": [{"png": "图片/Clip_05.png", "verdict": "warn"}]},        # 场景初筛 warn → 保留
            "seam": {"seams": [{"tail": "图片/Clip_07_end.png", "verdict": "block"}]},   # 接缝断 → 重生成
        },
        "lint": {"findings": [
            {"level": "block", "code": "unknown_char_id", "msg": "Clip 09：非法 CHAR_99"},  # 硬伤 → 重生成
            {"level": "block", "code": "no_eyeline", "msg": "Clip 11：缺视线"},             # 非硬码 → 不进
            {"level": "warn", "code": "no_anchor_phrase", "msg": "Clip 12：缺锚点"},
        ]},
    }
    regen = image_qc.to_regen_list(payload)
    shots = {r["shot"] for r in regen}
    assert shots == {"Clip_03", "Clip_18", "Clip_07", "Clip_09"}  # 崩脸/服装漂/接缝断/非法ID
    assert "Clip_04" not in shots and "Clip_02" not in shots      # ok/warn 能用就用，不重生成
    assert "Clip_05" not in shots and "Clip_11" not in shots
    # reasons 留痕
    c18 = next(r for r in regen if r["shot"] == "Clip_18")
    assert "服装漂 N1(校准后)" in c18["reasons"]
    assert c18["png"] == "图片/Clip_18_金瞳.png"


def test_to_strict_regen_list_includes_review_findings() -> None:
    payload = {
        "checks": {
            "face": {"shots": [{"png": "图片/Clip_03_脸.png", "verdict": "warn"}]},
            "outfit": {"shots": [{"png": "图片/Clip_18_金瞳.png", "verdict": "warn"}]},
            "scene": {"shots": [{"png": "图片/Clip_05.png", "verdict": "warn"}]},
            "seam": {"seams": [{"tail": "图片/Clip_07_end.png", "verdict": "warn"}]},
        },
        "lint": {"findings": [
            {"level": "warn", "code": "no_eyeline", "msg": "Clip 11：缺视线"},
            {"level": "warn", "code": "no_anchor_phrase", "msg": "Clip 12：缺锚点"},
        ]},
    }
    regen = image_qc.to_strict_regen_list(payload)
    shots = {r["shot"] for r in regen}
    assert shots == {"Clip_03", "Clip_18", "Clip_05", "Clip_07", "Clip_11", "Clip_12"}
    assert any("strict:prompt:no_eyeline" in r["reasons"] for r in regen if r["shot"] == "Clip_11")


def test_to_regen_list_empty_when_only_advisory() -> None:
    payload = {"checks": {"outfit": {"shots": [{"png": "a.png", "verdict": "warn"}]},
                          "scene": {"shots": [{"png": "b.png", "verdict": "warn"}]}},
               "lint": {"findings": [{"level": "warn", "code": "no_eyeline", "msg": "Clip 1"}]}}
    assert image_qc.to_regen_list(payload) == []   # 全是能用项 → 不重生成任何镜


# --- P2-A：disk-scoped 兜底——lint 漏分类的有脸镜列为 advisory，不静默漏检 ---
def test_coverage_flags_unclassified_face_shot(tmp_path: Path) -> None:
    # character_shots 空（lint 漏判），但 face 在某 PNG 检出人脸 → 应列 unclassified（非阻断）
    payload = {
        "lint": {"available": True, "character_shots": []},
        "checks": {"face": {"available": True, "mode": "insightface",
                            "shots": [{"png": "图片/Clip_05.png", "verdict": "ok"}]}},
    }
    cov = image_qc.face_reference_coverage(payload, tmp_path, "第1集")
    assert cov["required"] == 0
    assert cov["verdict"] == "ok"  # 无硬缺口
    uncl = cov["unclassified"]
    assert len(uncl) == 1
    assert uncl[0]["reason"] == "unclassified_face_shot"
    # summarize：advisory，不进 hard_blocks
    payload["face_reference_coverage"] = cov
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 0
    assert s["advisory"] >= 1


def test_coverage_ignores_noface_and_degraded(tmp_path: Path) -> None:
    # noface（场景/无脸镜）不应被当作漏分类角色镜
    payload = {
        "lint": {"available": True, "character_shots": []},
        "checks": {"face": {"available": True, "mode": "insightface",
                            "shots": [{"png": "图片/bg_01.png", "verdict": "noface"}]}},
    }
    cov = image_qc.face_reference_coverage(payload, tmp_path, "第1集")
    assert cov["unclassified"] == []
    # 降级精度（pillow_fallback）下不信任「检出人脸」，不产 unclassified（避免误报）
    payload_deg = {
        "lint": {"available": True, "character_shots": []},
        "checks": {"face": {"available": True, "mode": "pillow_fallback",
                            "shots": [{"png": "图片/Clip_05.png", "verdict": "ok"}]}},
    }
    cov_deg = image_qc.face_reference_coverage(payload_deg, tmp_path, "第1集")
    assert cov_deg["unclassified"] == []


# ── C3 多主体空间绑定 ──────────────────────────────────────────────────────
def test_multi_subject_spatial_binding_blocks_without_binding_or_strategy():
    # 2026-06：无空间绑定/无执行策略 → block（与 review 同框 gate、script must 同口径）
    body = "**资产身份注册层**：`CHAR_01/常态` 与 `CHAR_03/常态` 同框对峙。"
    out = image_qc._lint_multi_subject_spatial_binding("镜头5", body, ["CHAR_01/常态", "CHAR_03/常态"])
    assert len(out) == 1 and out[0]["code"] == "multi_person_no_spatial_binding" and out[0]["level"] == "block"


def test_multi_subject_spatial_binding_ok_with_blocking_or_positions():
    refs = ["CHAR_01", "CHAR_03"]
    assert image_qc._lint_multi_subject_spatial_binding("镜头5", "blocking=沈念画左，柳娘子画右", refs) == []
    assert image_qc._lint_multi_subject_spatial_binding("镜头5", "沈念在画左，柳娘子在画右对峙", refs) == []
    # 登记分层合成/原生主体执行策略也放行（block ⊆ review 同框 block，不误挡 review 会放行的镜）
    assert image_qc._lint_multi_subject_spatial_binding("镜头5", "本镜登记 分别出图+合成，逐主体单人分层出图后合成", refs) == []
    assert image_qc._lint_multi_subject_spatial_binding("镜头5", "shot_reverse_shot 拆成单人镜反打", refs) == []
    # 单人镜不触发
    assert image_qc._lint_multi_subject_spatial_binding("镜头1", "CHAR_01 独自", ["CHAR_01/常态"]) == []


# ── C4 多角度参考喂养 ──────────────────────────────────────────────────────
def test_native_multiref_underfed_info_when_group_underused():
    body = "**参考图**：\n- `定妆_沈念.png`（正脸主参考）"
    out = image_qc._lint_native_multiref_coverage("镜头1", body, ["CHAR_01/常态"], {"CHAR_01": 4})
    assert len(out) == 1 and out[0]["code"] == "native_multiref_underfed" and out[0]["level"] == "info"


def test_native_multiref_ok_when_enough_or_no_group():
    body3 = "`定妆_沈念.png` `定妆_沈念_侧.png` `定妆_沈念_背.png`"
    assert image_qc._lint_native_multiref_coverage("镜头1", body3, ["CHAR_01"], {"CHAR_01": 4}) == []
    char_named = (
        "`出图/共享/图片/CHAR_01_常态.png` "
        "`出图/共享/图片/CHAR_01_常态_侧.png` "
        "`出图/共享/图片/CHAR_01_常态_背.png`"
    )
    assert image_qc._lint_native_multiref_coverage("镜头1", char_named, ["CHAR_01"], {"CHAR_01": 4}) == []
    # 没有多角度组（avail<3）→ 不提
    assert image_qc._lint_native_multiref_coverage("镜头1", "`定妆_沈念.png`", ["CHAR_01"], {"CHAR_01": 1}) == []
    # 无 form_ref_counts → 不提
    assert image_qc._lint_native_multiref_coverage("镜头1", "`定妆_沈念.png`", ["CHAR_01"], None) == []


def test_weak_face_anchor_reason_thresholds():
    # 脸太小 + 低分辨率 → 两条原因
    r = image_qc.weak_face_anchor_reason(0.05, 512)
    assert r and "脸占画面" in r and "裁切短边" in r
    # 脸占比够、分辨率够 → None
    assert image_qc.weak_face_anchor_reason(0.4, 1024) is None
    # 检测器漏检（ratio=None）→ 只按分辨率判
    assert "裁切短边" in (image_qc.weak_face_anchor_reason(None, 600) or "")
    assert image_qc.weak_face_anchor_reason(None, 1200) is None
    # 两者皆 None → 不报
    assert image_qc.weak_face_anchor_reason(None, None) is None


def test_face_anchor_ref_items_collects_only_tight_crops():
    form = {
        "reference_group": {
            "front": "出图/共享/图片/定妆_沈念.png",          # 宽身位主参考——不该被收
            "face_anchor_refs": ["出图/共享/图片/定妆_沈念_脸部特写.png"],
        },
        "reference_atlas": {
            "base_views": {"front": {"path": "出图/共享/图片/定妆_沈念.png"}},
            "expression_refs": [
                {"emotion": "基础", "path": "出图/共享/图片/定妆_沈念.png"},
                {"emotion": "怒", "path": "出图/共享/图片/表情_沈念_怒.png"},
            ],
        },
    }
    items = image_qc._face_anchor_ref_items(form)
    paths = {p for _, p in items}
    assert "出图/共享/图片/定妆_沈念_脸部特写.png" in paths
    assert "出图/共享/图片/表情_沈念_怒.png" in paths
    assert "出图/共享/图片/定妆_沈念.png" not in paths  # 宽身位主参考不收


def test_audit_face_anchor_quality_ignores_base_expression_alias_to_front(tmp_path):
    import pytest
    Image = pytest.importorskip("PIL.Image", reason="Pillow 装在 facefusion conda env，系统 Python 无")
    root = tmp_path / "剧"
    img_dir = root / "出图" / "共享" / "图片"
    img_dir.mkdir(parents=True)
    # 正面全身/宽身位参考脸占比可很小；紧裁脸锚才进入本门。
    Image.new("RGB", (320, 960), (128, 128, 128)).save(img_dir / "定妆_沈念.png")
    Image.new("RGB", (1024, 1024), (128, 128, 128)).save(img_dir / "定妆_沈念_脸部特写.png")
    (root / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({
        "characters": [{"id": "CHAR_01", "name": "沈念", "scope": "核心长线女主", "forms": [{
            "form": "常态",
            "reference_group": {
                "front": {"path": "出图/共享/图片/定妆_沈念.png"},
                "face_anchor_refs": ["出图/共享/图片/定妆_沈念_脸部特写.png"],
            },
            "reference_atlas": {
                "base_views": {"front": {"path": "出图/共享/图片/定妆_沈念.png"}},
                "face_anchor_refs": ["出图/共享/图片/定妆_沈念_脸部特写.png"],
                "expression_refs": [{"emotion": "基础", "path": "出图/共享/图片/定妆_沈念.png"}],
            },
        }]}]
    }, ensure_ascii=False), encoding="utf-8")
    res = image_qc.audit_face_anchor_quality(root, "第1集")
    assert res["available"]
    # reference_group / reference_atlas 对同一紧裁脸锚的重复登记只应检查一次。
    assert res["checked"] == 1
    assert not [f for f in res["findings"] if "定妆_沈念.png" in f["msg"]]


def test_face_anchor_quality_audits_expression_contact_sheet_instead_of_skipping_it(tmp_path, monkeypatch):
    import pytest
    Image = pytest.importorskip("PIL.Image", reason="Pillow 装在 facefusion conda env，系统 Python 无")
    root = tmp_path / "剧"
    tight_rel = "出图/共享/图片/定妆_少年_脸部特写.png"
    sheet_rel = "出图/共享/图片/定妆_少年_表情_六联表.png"
    (root / "出图" / "共享" / "图片").mkdir(parents=True)
    Image.new("RGB", (1024, 1024), (128, 128, 128)).save(root / tight_rel)
    Image.new("RGB", (1672, 941), (128, 128, 128)).save(root / sheet_rel)

    class FakeFaceModule:
        @staticmethod
        def cv2_face_boxes(path):
            if str(path).endswith("六联表.png"):
                return [(0, 0, 120, 120)]
            return [(100, 100, 700, 700)]

    monkeypatch.setattr(image_qc, "_load_review_module", lambda _name: FakeFaceModule)
    (root / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({
        "characters": [{"id": "CHAR_01", "name": "少年", "scope": "核心长线主角", "forms": [{
            "form": "常态",
            "reference_group": {"face_anchor_refs": [{"path": tight_rel}]},
            "reference_atlas": {
                "face_anchor_refs": [{"path": tight_rel}],
                "expression_refs": [{
                    "emotion": "六联表",
                    "path": sheet_rel,
                    "layout": "two_by_three_expression_sheet_v1",
                }],
            },
        }]}],
    }, ensure_ascii=False), encoding="utf-8")

    res = image_qc.audit_face_anchor_quality(root, "第1集")

    assert res["checked"] == 2
    assert any(
        finding["level"] == "block" and finding["code"] == "expression_sheet_face_count"
        for finding in res["findings"]
    )


def test_audit_face_anchor_quality_flags_low_res(tmp_path):
    import pytest
    Image = pytest.importorskip("PIL.Image", reason="Pillow 装在 facefusion conda env，系统 Python 无")
    root = tmp_path / "剧"
    img_dir = root / "出图" / "共享" / "图片"
    img_dir.mkdir(parents=True)
    # 故意低分辨率（短边 320 < 768）的脸部特写
    Image.new("RGB", (320, 480), (128, 128, 128)).save(img_dir / "定妆_沈念_脸部特写.png")
    (root / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({
        "characters": [{"id": "CHAR_01", "name": "沈念", "forms": [{
            "form": "常态",
            "reference_group": {"face_anchor_refs": ["出图/共享/图片/定妆_沈念_脸部特写.png"]},
        }]}]
    }, ensure_ascii=False), encoding="utf-8")
    res = image_qc.audit_face_anchor_quality(root, "第1集")
    assert res["available"] and res["checked"] == 1
    codes = {f["code"] for f in res["findings"]}
    assert "weak_face_anchor" in codes
    assert any("裁切短边" in f["msg"] for f in res["findings"])


def test_audit_face_anchor_quality_ignores_human_bbox_ratio_for_nonhuman_and_dedupes(tmp_path, monkeypatch):
    import pytest
    Image = pytest.importorskip("PIL.Image", reason="Pillow 装在 facefusion conda env，系统 Python 无")
    root = tmp_path / "剧"
    img_dir = root / "出图" / "共享" / "图片"
    img_dir.mkdir(parents=True)
    rel = "出图/共享/图片/定妆_虎妖_脸部特写.png"
    Image.new("RGB", (1024, 1024), (128, 128, 128)).save(root / rel)

    class FakeFaceModule:
        @staticmethod
        def cv2_face_boxes(_path):
            return [(0, 0, 160, 160)]  # human detector false positive: 2.4%

    monkeypatch.setattr(image_qc, "_load_review_module", lambda _name: FakeFaceModule)
    (root / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({
        "characters": [{
            "id": "CHAR_TIGER", "name": "虎山神", "scope": "复现虎妖",
            "forms": [{
                "form": "常态", "anchor_phrase": "非人虎妖真身，吊睛白额虎首",
                "character_dna": {"face": "虎头人身妖物，不得洗成人脸"},
                "reference_group": {"face_anchor_refs": [{"path": rel}]},
                "reference_atlas": {"face_anchor_refs": [{"path": rel}]},
            }],
        }],
    }, ensure_ascii=False), encoding="utf-8")

    res = image_qc.audit_face_anchor_quality(root, "第1集")

    assert res["checked"] == 1
    assert res["findings"] == []


def test_audit_face_anchor_quality_blocks_core_low_res(tmp_path):
    import pytest
    Image = pytest.importorskip("PIL.Image", reason="Pillow 装在 facefusion conda env，系统 Python 无")
    root = tmp_path / "剧"
    img_dir = root / "出图" / "共享" / "图片"
    img_dir.mkdir(parents=True)
    Image.new("RGB", (320, 480), (128, 128, 128)).save(img_dir / "定妆_沈念_脸部特写.png")
    (root / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({
        "characters": [{"id": "CHAR_01", "name": "沈念", "scope": "长线女主·全篇", "forms": [{
            "form": "常态",
            "reference_group": {"face_anchor_refs": ["出图/共享/图片/定妆_沈念_脸部特写.png"]},
        }]}]
    }, ensure_ascii=False), encoding="utf-8")
    res = image_qc.audit_face_anchor_quality(root, "第1集")
    assert any(f["level"] == "block" and f["code"] == "weak_face_anchor_core" for f in res["findings"])
    payload = {"checks": {}, "lint": {"findings": res["findings"]}}
    assert image_qc.summarize(payload)["verdict"] == "block"


def test_audit_face_anchor_quality_normalizes_six_panel_expression_sheet(tmp_path, monkeypatch):
    import pytest
    Image = pytest.importorskip("PIL.Image", reason="Pillow 装在 facefusion conda env，系统 Python 无")
    root = tmp_path / "剧"
    rel = "出图/共享/图片/定妆_沈念_表情_六联表.png"
    (root / rel).parent.mkdir(parents=True)
    Image.new("RGB", (1200, 1800), (128, 128, 128)).save(root / rel)

    class FakeFaceModule:
        @staticmethod
        def cv2_face_boxes(_path):
            # Each face is only 3% of the complete sheet, but 18% of one 2x3 panel.
            return [(0, 0, 180, 360)] * 6

    monkeypatch.setattr(image_qc, "_load_review_module", lambda _name: FakeFaceModule)
    (root / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({
        "characters": [{"id": "CHAR_01", "name": "沈念", "scope": "长线女主·全篇", "forms": [{
            "form": "常态",
            "reference_group": {"expressions": [{"emotion": "六联表", "path": rel}]},
            "reference_atlas": {"expression_refs": [{"emotion": "六联表", "path": rel}]},
        }]}],
    }, ensure_ascii=False), encoding="utf-8")

    res = image_qc.audit_face_anchor_quality(root, "第1集")

    assert res["checked"] == 1
    assert not [f for f in res["findings"] if f["code"] == "weak_face_anchor_core"]
    assert not [f for f in res["findings"] if f["code"] == "expression_sheet_face_count"]


def test_audit_face_anchor_quality_blocks_incomplete_six_panel_expression_sheet(tmp_path, monkeypatch):
    import pytest
    Image = pytest.importorskip("PIL.Image", reason="Pillow 装在 facefusion conda env，系统 Python 无")
    root = tmp_path / "剧"
    rel = "出图/共享/图片/定妆_沈念_表情_六联表.png"
    (root / rel).parent.mkdir(parents=True)
    Image.new("RGB", (1200, 1800), (128, 128, 128)).save(root / rel)

    class FakeFaceModule:
        @staticmethod
        def cv2_face_boxes(_path):
            return [(0, 0, 180, 360)] * 5

    monkeypatch.setattr(image_qc, "_load_review_module", lambda _name: FakeFaceModule)
    (root / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({
        "characters": [{"id": "CHAR_01", "name": "沈念", "scope": "长线女主·全篇", "forms": [{
            "form": "常态",
            "reference_atlas": {"expression_refs": [{"emotion": "六联表", "path": rel}]},
        }]}],
    }, ensure_ascii=False), encoding="utf-8")

    res = image_qc.audit_face_anchor_quality(root, "第1集")

    assert any(
        finding["level"] == "block" and finding["code"] == "expression_sheet_face_count"
        for finding in res["findings"]
    )


def test_native_multiref_tiers_by_persistent_subject():
    # ④ 持久主体后端（Seedream/可灵/Sora）：把「喂全组」换成「ID+单强锚」口径，不再误导堆图
    body = "**参考图**：\n- `定妆_沈念.png`（正脸主参考）"
    out = image_qc._lint_native_multiref_coverage("镜头1", body, ["CHAR_01/常态"], {"CHAR_01": 4},
                                                  persistent_subject=True)
    assert len(out) == 1 and out[0]["code"] == "native_subject_anchor_ok" and out[0]["level"] == "info"
    assert "单强锚" in out[0]["msg"]
    # 多参考后端（persistent_subject=False/未知）→ 仍是喂全组的旧 nudge
    out2 = image_qc._lint_native_multiref_coverage("镜头1", body, ["CHAR_01/常态"], {"CHAR_01": 4},
                                                   persistent_subject=False)
    assert out2[0]["code"] == "native_multiref_underfed"


def test_registry_ref_counts_takes_max_per_char():
    forms = [{"id": "CHAR_01", "ref_count": 2}, {"id": "CHAR_01", "ref_count": 4}, {"id": "CHAR_02", "ref_count": 1}]
    assert image_qc.registry_ref_counts(forms) == {"CHAR_01": 4, "CHAR_02": 1}


def _state_ledger_work(tmp_path: Path, sb_state: str, prompt_text: str = "", with_ledger: bool = False) -> Path:
    (tmp_path / "脚本" / "第1集").mkdir(parents=True)
    (tmp_path / "脚本" / "第1集" / "storyboard.json").write_text(
        json.dumps({"visual_contract": {"角色状态演进": sb_state}}), encoding="utf-8")
    (tmp_path / "出图" / "第1集" / "prompt").mkdir(parents=True)
    (tmp_path / "出图" / "第1集" / "prompt" / "01_分镜出图.md").write_text(prompt_text, encoding="utf-8")
    if with_ledger:
        (tmp_path / "出图" / "共享").mkdir(parents=True, exist_ok=True)
        (tmp_path / "出图" / "共享" / "visual_state_ledger.json").write_text("{}", encoding="utf-8")
    return tmp_path


def test_reference_layer_classifies_identity_vs_atmosphere() -> None:
    rl = image_qc.reference_layer
    assert rl({"path": "出图/共享/图片/定妆_沈念_脸部特写.png"}) == ""          # 中性命名 → 未知(默认按身份用)
    assert rl({"path": "定妆_沈念_烛光氛围.png"}) == "atmosphere"             # 戏剧光命名
    assert rl("定妆_暗调逆光.png") == "atmosphere"
    assert rl({"layer": "atmosphere", "path": "x.png"}) == "atmosphere"     # 显式标签
    assert rl({"lighting": "neutral", "path": "定妆_烛光.png"}) == "identity"  # 显式中性盖过命名


def test_face_anchor_lighting_audit_flags_dramatic_anchor(tmp_path: Path) -> None:
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "identity_registry.json").write_text(json.dumps({
        "characters": [{
            "id": "CHAR_01",
            "forms": [{
                "form": "冷宫废妃常态",
                "reference_group": {"face_anchor_refs": [
                    {"path": "出图/共享/图片/定妆_沈念_脸部特写.png", "status": "ready"},
                    {"path": "出图/共享/图片/定妆_沈念_烛光氛围.png", "status": "ready"},
                ]},
            }],
        }]
    }, ensure_ascii=False), encoding="utf-8")
    res = image_qc.face_anchor_lighting_audit(tmp_path, "第1集")
    assert res["available"] is True
    flagged = {Path(f["path"]).name for f in res["flagged"]}
    assert flagged == {"定妆_沈念_烛光氛围.png"}  # 只 flag 戏剧光板，中性脸锚不报


def test_state_ledger_advises_when_cumulative_state_and_no_ledger(tmp_path: Path) -> None:
    r = image_qc.audit_state_ledger(_state_ledger_work(tmp_path, "镜6 被刺流血→镜7 包扎"), "第1集")
    assert r["advise"] is True
    assert "流血" in r["markers"] and "包扎" in r["markers"]


def test_state_ledger_silent_when_ledger_present_and_state_injected(tmp_path: Path) -> None:
    # ledger 建了 AND 累积状态确实注入了出图 prompt → 真静默。
    work = _state_ledger_work(tmp_path, "镜6 被刺流血",
                              prompt_text="本镜沈念左臂流血、绷带可见", with_ledger=True)
    r = image_qc.audit_state_ledger(work, "第1集")
    assert r["advise"] is False and r["ledger_present"] is True
    assert r["not_injected_markers"] == []


def test_state_ledger_advises_when_state_declared_but_not_injected(tmp_path: Path) -> None:
    # A5b：状态演进声明了累积状态，但出图 prompt 没注入（runner 会照画干净衣服）——即便建了 ledger 也要 advise。
    work = _state_ledger_work(tmp_path, "镜6 被刺流血", prompt_text="沈念立于窗前", with_ledger=True)
    r = image_qc.audit_state_ledger(work, "第1集")
    assert r["advise"] is True
    assert "流血" in r["not_injected_markers"]


def test_state_ledger_no_false_positive_on_emotion_words(tmp_path: Path) -> None:
    # 悲伤/热血 是情绪词，不是累积视觉状态——裸「伤/血」已从关键词表剔除，不应误报
    r = image_qc.audit_state_ledger(_state_ledger_work(tmp_path, "女主悲伤落座，男主热血宣言"), "第1集")
    assert r["advise"] is False and r["markers"] == []


def test_state_ledger_unavailable_when_no_source(tmp_path: Path) -> None:
    r = image_qc.audit_state_ledger(tmp_path / "nope", "第99集")
    assert r["available"] is False and r["advise"] is False


def test_state_ledger_finding_is_info_never_blocks(tmp_path: Path) -> None:
    payload = {"state_ledger": {"advise": True, "markers": ["流血"]}}
    findings = image_qc.to_findings(payload)
    sl = [f for f in findings if f["dim"] == "state_continuity"]
    assert len(sl) == 1 and sl[0]["sev"] == "info"


def _registry_with_form(tmp_path: Path, forms: list) -> Path:
    (tmp_path / "出图" / "共享").mkdir(parents=True)
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps({"characters": [{"id": "CHAR_01", "name": "沈念", "forms": forms}]}), encoding="utf-8")
    return tmp_path


def test_mark_finalized_sets_single_form(tmp_path: Path) -> None:
    root = _registry_with_form(tmp_path, [{"form": "常态", "asset_key": "x"}])
    r = image_qc.mark_finalized(root, "CHAR_01")
    assert r["ok"] is True
    reg = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))
    assert reg["characters"][0]["forms"][0]["self_check_passed"] is True


def test_mark_finalized_requires_form_when_ambiguous(tmp_path: Path) -> None:
    root = _registry_with_form(tmp_path, [{"form": "常态"}, {"form": "觉醒态"}])
    assert image_qc.mark_finalized(root, "CHAR_01")["ok"] is False
    assert image_qc.mark_finalized(root, "CHAR_01/觉醒态")["ok"] is True


def test_mark_finalized_unfinalize_sets_false(tmp_path: Path) -> None:
    root = _registry_with_form(tmp_path, [{"form": "常态"}])
    image_qc.mark_finalized(root, "CHAR_01/常态", value=False)
    reg = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))
    assert reg["characters"][0]["forms"][0]["self_check_passed"] is False


def test_mark_finalized_asset(tmp_path: Path) -> None:
    (tmp_path / "出图" / "共享").mkdir(parents=True)
    img = tmp_path / "出图" / "共享" / "图片"
    img.mkdir(parents=True)
    (img / "定妆_毒酒壶.png").write_bytes(b"\x89PNG-prop-bytes")
    (img / "定妆_马队.png").write_bytes(b"\x89PNG-mount-bytes")
    prop_rel = "出图/共享/图片/定妆_毒酒壶.png"
    mount_rel = "出图/共享/图片/定妆_马队.png"
    (tmp_path / "出图" / "共享" / "asset_registry.json").write_text(
        json.dumps({
            "assets": [
                {
                    "id": "PROP_01",
                    "name": "毒酒壶",
                    "reference_group": {"primary": {"path": prop_rel, "status": "review_pending"}},
                },
                {
                    "id": "MOUNT_GROUP_01",
                    "name": "马队",
                    "reference_group": {
                        "primary": {"path": mount_rel, "status": "review_pending", "human_review": {"status": "pending"}}
                    },
                },
            ]
        }), encoding="utf-8")
    assert image_qc.mark_finalized(tmp_path, "PROP_01")["ok"] is True
    assert image_qc.mark_finalized(tmp_path, "MOUNT_GROUP_01")["ok"] is True
    reg = json.loads((tmp_path / "出图" / "共享" / "asset_registry.json").read_text(encoding="utf-8"))
    assert reg["assets"][0]["self_check_passed"] is True
    assert reg["assets"][1]["self_check_passed"] is True
    assert reg["assets"][1]["reference_group"]["primary"]["status"] == "ready"
    assert reg["assets"][1]["reference_group"]["primary"]["human_review"]["status"] == "accepted"


def test_mark_finalized_asset_uses_project_write_lock(tmp_path: Path) -> None:
    (tmp_path / "出图" / "共享").mkdir(parents=True)
    rel = "出图/共享/图片/定妆_断碑.png"
    (tmp_path / rel).parent.mkdir(parents=True)
    (tmp_path / rel).write_bytes(b"\x89PNG-prop-bytes")
    (tmp_path / "出图" / "共享" / "asset_registry.json").write_text(
        json.dumps({"assets": [{
            "id": "PROP_01",
            "name": "断碑",
            "reference_group": {"primary": {"path": rel, "status": "review_pending"}},
        }]}), encoding="utf-8")
    entered = []

    @contextlib.contextmanager
    def fake_lock(root: Path):
        entered.append(root)
        yield

    original = image_qc._project_write_lock
    image_qc._project_write_lock = fake_lock
    try:
        assert image_qc.mark_finalized(tmp_path, "PROP_01")["ok"] is True
    finally:
        image_qc._project_write_lock = original

    assert entered == [tmp_path]
    reg = json.loads((tmp_path / "出图" / "共享" / "asset_registry.json").read_text(encoding="utf-8"))
    assert reg["assets"][0]["self_check_passed"] is True


# ── 锚点指纹钉死（P0-b）─────────────────────────────────────────────
def _registry_with_anchor(tmp_path: Path) -> Path:
    img = tmp_path / "出图" / "共享" / "图片"
    img.mkdir(parents=True)
    (img / "定妆_沈念_常态.png").write_bytes(b"\x89PNG-anchor-bytes-v1")
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({
        "characters": [{"id": "CHAR_01", "name": "沈念", "forms": [
            {"form": "常态", "reference_group": {"front": "出图/共享/图片/定妆_沈念_常态.png"}},
        ]}]
    }, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def _registry_with_anchor_object(tmp_path: Path) -> Path:
    root = _registry_with_anchor(tmp_path)
    p = root / "出图" / "共享" / "identity_registry.json"
    reg = json.loads(p.read_text(encoding="utf-8"))
    reg["characters"][0]["forms"][0]["reference_group"]["front"] = {
        "path": "出图/共享/图片/定妆_沈念_常态.png",
        "status": "ready",
    }
    p.write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")
    return root


def test_pin_anchor_writes_sha(tmp_path: Path) -> None:
    root = _registry_with_anchor(tmp_path)
    r = image_qc.pin_anchor(root, "CHAR_01/常态")
    assert r["ok"] is True
    reg = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))
    sha = reg["characters"][0]["forms"][0]["anchor_sha"]
    assert sha and len(sha) == 64


def test_pin_anchor_missing_front_image_fails(tmp_path: Path) -> None:
    root = _registry_with_anchor(tmp_path)
    (root / "出图" / "共享" / "图片" / "定妆_沈念_常态.png").unlink()
    assert image_qc.pin_anchor(root, "CHAR_01/常态")["ok"] is False


def test_unpin_anchor_removes_sha(tmp_path: Path) -> None:
    root = _registry_with_anchor(tmp_path)
    image_qc.pin_anchor(root, "CHAR_01/常态")
    image_qc.pin_anchor(root, "CHAR_01/常态", unpin=True)
    reg = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))
    assert "anchor_sha" not in reg["characters"][0]["forms"][0]


# ── ①a 落档自检自动钉死 anchor_sha ─────────────────────────────────
def test_mark_finalized_auto_pins_anchor(tmp_path: Path) -> None:
    root = _registry_with_anchor(tmp_path)
    r = image_qc.mark_finalized(root, "CHAR_01/常态")
    assert r["ok"] is True and r["auto_pinned"] is True
    fm = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))["characters"][0]["forms"][0]
    assert fm["self_check_passed"] is True
    # 自动钉死的 sha 必须等于手动 pin 的结果（同一母图同一指纹）
    assert fm["anchor_sha"] == image_qc._sha256_file(root / "出图" / "共享" / "图片" / "定妆_沈念_常态.png")


def test_mark_finalized_auto_pins_anchor_from_front_object(tmp_path: Path) -> None:
    root = _registry_with_anchor_object(tmp_path)
    r = image_qc.mark_finalized(root, "CHAR_01/常态")
    assert r["ok"] is True and r["auto_pinned"] is True
    fm = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))["characters"][0]["forms"][0]
    assert fm["anchor_sha"] == image_qc._sha256_file(root / "出图" / "共享" / "图片" / "定妆_沈念_常态.png")


def test_mark_finalized_promotes_review_pending_front_to_ready(tmp_path: Path) -> None:
    root = _registry_with_anchor_object(tmp_path)
    p = root / "出图" / "共享" / "identity_registry.json"
    reg = json.loads(p.read_text(encoding="utf-8"))
    form = reg["characters"][0]["forms"][0]
    form["reference_group"]["front"]["status"] = "review_pending"
    form["reference_group"]["front"]["human_review"] = {"status": "pending"}
    form["reference_atlas"] = {
        "base_views": {
            "front": {
                "path": "出图/共享/图片/定妆_沈念_常态.png",
                "status": "review_pending",
                "human_review": {"status": "pending"},
            }
        }
    }
    p.write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")

    r = image_qc.mark_finalized(root, "CHAR_01/常态")
    assert r["ok"] is True
    fm = json.loads(p.read_text(encoding="utf-8"))["characters"][0]["forms"][0]
    assert fm["reference_group"]["front"]["status"] == "ready"
    assert fm["reference_group"]["front"]["human_review"]["status"] == "accepted"
    assert fm["reference_atlas"]["base_views"]["front"]["status"] == "ready"


def test_mark_finalized_promotes_review_pending_side_to_ready(tmp_path: Path) -> None:
    root = _registry_with_anchor_object(tmp_path)
    img = root / "出图" / "共享" / "图片"
    (img / "定妆_沈念_常态_侧面.png").write_bytes(b"\x89PNG-side-bytes-v1")
    side_rel = "出图/共享/图片/定妆_沈念_常态_侧面.png"
    p = root / "出图" / "共享" / "identity_registry.json"
    reg = json.loads(p.read_text(encoding="utf-8"))
    form = reg["characters"][0]["forms"][0]
    form["reference_group"]["side"] = {
        "path": side_rel,
        "status": "review_pending",
        "human_review": {"status": "pending"},
    }
    form["reference_atlas"] = {
        "base_views": {
            "side": {
                "path": side_rel,
                "status": "review_pending",
                "human_review": {"status": "pending"},
            }
        }
    }
    p.write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")

    r = image_qc.mark_finalized(root, "CHAR_01/常态")
    assert r["ok"] is True
    fm = json.loads(p.read_text(encoding="utf-8"))["characters"][0]["forms"][0]
    assert fm["reference_group"]["side"]["status"] == "ready"
    assert fm["reference_group"]["side"]["human_review"]["status"] == "accepted"
    assert fm["reference_atlas"]["base_views"]["side"]["status"] == "ready"
    assert fm["reference_atlas"]["base_views"]["side"]["human_review"]["status"] == "accepted"


def test_mark_finalized_promotes_review_pending_turnaround_to_ready(tmp_path: Path) -> None:
    root = _registry_with_anchor_object(tmp_path)
    img = root / "出图" / "共享" / "图片"
    (img / "定妆_沈念_常态_三视图.png").write_bytes(b"\x89PNG-turnaround-bytes-v1")
    turnaround_rel = "出图/共享/图片/定妆_沈念_常态_三视图.png"
    p = root / "出图" / "共享" / "identity_registry.json"
    reg = json.loads(p.read_text(encoding="utf-8"))
    form = reg["characters"][0]["forms"][0]
    form["reference_group"]["turnaround"] = {
        "path": turnaround_rel,
        "status": "review_pending",
        "human_review": {"status": "pending"},
    }
    p.write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")

    r = image_qc.mark_finalized(root, "CHAR_01/常态")
    assert r["ok"] is True
    fm = json.loads(p.read_text(encoding="utf-8"))["characters"][0]["forms"][0]
    assert fm["reference_group"]["turnaround"]["status"] == "ready"
    assert fm["reference_group"]["turnaround"]["human_review"]["status"] == "accepted"


def test_mark_finalized_promotes_face_expression_and_partial_refs(tmp_path: Path) -> None:
    root = _registry_with_anchor_object(tmp_path)
    img = root / "出图" / "共享" / "图片"
    face_rel = "出图/共享/图片/定妆_沈念_常态_脸锚.png"
    hand_rel = "出图/共享/图片/定妆_群体_手部局部.png"
    (img / "定妆_沈念_常态_脸锚.png").write_bytes(b"\x89PNG-face-bytes")
    (img / "定妆_群体_手部局部.png").write_bytes(b"\x89PNG-hand-bytes")
    p = root / "出图" / "共享" / "identity_registry.json"
    reg = json.loads(p.read_text(encoding="utf-8"))
    form = reg["characters"][0]["forms"][0]
    form["reference_group"]["face_anchor_refs"] = [{"path": face_rel, "status": "review_pending"}]
    form["reference_group"]["expressions"] = [{"path": face_rel, "status": "review_pending", "emotion": "基础"}]
    form["reference_atlas"] = {
        "face_anchor_refs": [{"path": face_rel, "status": "review_pending"}],
        "expression_refs": [{"path": face_rel, "status": "review_pending", "emotion": "基础"}],
        "partial_refs": {"hand": {"path": hand_rel, "status": "review_pending"}},
    }
    p.write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")

    r = image_qc.mark_finalized(root, "CHAR_01/常态")
    assert r["ok"] is True
    fm = json.loads(p.read_text(encoding="utf-8"))["characters"][0]["forms"][0]
    assert fm["reference_group"]["face_anchor_refs"][0]["status"] == "ready"
    assert fm["reference_group"]["face_anchor_refs"][0]["path"] == face_rel
    assert fm["reference_group"]["expressions"][0]["status"] == "ready"
    assert fm["reference_atlas"]["face_anchor_refs"][0]["status"] == "ready"
    assert fm["reference_atlas"]["expression_refs"][0]["status"] == "ready"
    assert fm["reference_atlas"]["partial_refs"]["hand"]["status"] == "ready"
    assert fm["reference_atlas"]["partial_refs"]["hand"]["path"] == hand_rel


def test_mark_finalized_no_auto_pin_flag_keeps_optin(tmp_path: Path) -> None:
    root = _registry_with_anchor(tmp_path)
    r = image_qc.mark_finalized(root, "CHAR_01/常态", auto_pin=False)
    assert r["ok"] is True and r["auto_pinned"] is False
    fm = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))["characters"][0]["forms"][0]
    assert fm["self_check_passed"] is True and "anchor_sha" not in fm


def test_mark_finalized_unfinalize_does_not_pin(tmp_path: Path) -> None:
    root = _registry_with_anchor(tmp_path)
    image_qc.mark_finalized(root, "CHAR_01/常态", value=False)
    fm = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))["characters"][0]["forms"][0]
    assert fm["self_check_passed"] is False and "anchor_sha" not in fm


def test_mark_finalized_auto_pin_graceful_when_front_missing(tmp_path: Path) -> None:
    # form 无 reference_group front（不可钉）→ 落档仍成功，只是不自动钉死，不抛错
    root = _registry_with_form(tmp_path, [{"form": "常态", "asset_key": "x"}])
    r = image_qc.mark_finalized(root, "CHAR_01")
    assert r["ok"] is True and r["auto_pinned"] is False
    fm = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))["characters"][0]["forms"][0]
    assert fm["self_check_passed"] is True and "anchor_sha" not in fm


# ── 表情库跨集共享锁定（P1-b）─────────────────────────────────────
def _registry_with_expr(tmp_path: Path, make_file: bool = True) -> Path:
    img = tmp_path / "出图" / "共享" / "图片"
    img.mkdir(parents=True)
    if make_file:
        (img / "定妆_沈念_常态_表情_怒.png").write_bytes(b"\x89PNG-expr-v1")
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({
        "characters": [{"id": "CHAR_01", "name": "沈念", "forms": [
            {"form": "常态", "expression_anchors": [
                {"emotion": "怒", "path": "出图/共享/图片/定妆_沈念_常态_表情_怒.png"},
            ]},
        ]}]
    }, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_finalize_expression_sets_passed_and_sha(tmp_path: Path) -> None:
    root = _registry_with_expr(tmp_path)
    r = image_qc.finalize_expression(root, "CHAR_01/常态/怒")
    assert r["ok"] is True
    a = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))["characters"][0]["forms"][0]["expression_anchors"][0]
    assert a["self_check_passed"] is True and len(a["anchor_sha"]) == 64


def test_finalize_expression_syncs_reference_atlas_expression_refs(tmp_path: Path) -> None:
    root = _registry_with_expr(tmp_path)
    p = root / "出图" / "共享" / "identity_registry.json"
    reg = json.loads(p.read_text(encoding="utf-8"))
    form = reg["characters"][0]["forms"][0]
    expr = {"emotion": "怒", "path": "出图/共享/图片/定妆_沈念_常态_表情_怒.png", "status": "review_pending"}
    form["reference_group"] = {"expressions": [dict(expr)]}
    form["reference_atlas"] = {"expression_refs": [dict(expr)]}
    p.write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")

    r = image_qc.finalize_expression(root, "CHAR_01/常态/怒")
    assert r["ok"] is True
    form = json.loads(p.read_text(encoding="utf-8"))["characters"][0]["forms"][0]
    assert form["expression_anchors"][0]["status"] == "ready"
    assert form["reference_group"]["expressions"][0]["status"] == "ready"
    assert form["reference_atlas"]["expression_refs"][0]["status"] == "ready"
    assert form["reference_atlas"]["expression_refs"][0]["self_check_passed"] is True
    assert len(form["reference_atlas"]["expression_refs"][0]["anchor_sha"]) == 64


def test_finalize_expression_unfinalize_clears_sha(tmp_path: Path) -> None:
    root = _registry_with_expr(tmp_path)
    image_qc.finalize_expression(root, "CHAR_01/常态/怒")
    image_qc.finalize_expression(root, "CHAR_01/常态/怒", value=False)
    a = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))["characters"][0]["forms"][0]["expression_anchors"][0]
    assert a["self_check_passed"] is False and "anchor_sha" not in a


def test_finalize_expression_unknown_emotion_fails(tmp_path: Path) -> None:
    root = _registry_with_expr(tmp_path)
    assert image_qc.finalize_expression(root, "CHAR_01/常态/惊")["ok"] is False


def test_finalize_expression_missing_image_fails(tmp_path: Path) -> None:
    root = _registry_with_expr(tmp_path, make_file=False)
    assert image_qc.finalize_expression(root, "CHAR_01/常态/怒")["ok"] is False


# ── B 跨集脸漂移趋势 ─────────────────────────────────────────────────────────────

def _drift_payload(mean: float, mode: str = "insightface") -> dict:
    return {"checks": {"face": {"mode": mode, "characters": {
        "CHAR_01": {"ep_mean_score": mean, "ep_n_shots": 3}}}}}


def _drift_payload_chars(chars: dict, mode: str = "insightface") -> dict:
    return {"checks": {"face": {"mode": mode, "characters": chars}}}


def test_update_face_drift_history_writes_full_precision(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "剧"
    (root / "生产数据").mkdir(parents=True)
    out = image_qc.update_face_drift_history(root, "第1集", _drift_payload(0.82))
    assert out is not None
    assert out["characters"]["CHAR_01"]["第1集"] == 0.82
    assert out["kind"] == image_qc.FACE_DRIFT_HISTORY_KIND


def test_update_face_drift_history_skips_degraded_precision(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "剧"
    (root / "生产数据").mkdir(parents=True)
    # pillow_fallback = 降级精度，均值不可比，不写历史
    assert image_qc.update_face_drift_history(root, "第1集", _drift_payload(0.82, mode="pillow_fallback")) is None
    assert not image_qc._face_drift_history_path(root).exists()


def test_update_face_drift_history_removes_stale_current_episode_chars(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "剧"
    (root / "生产数据").mkdir(parents=True)
    image_qc.update_face_drift_history(
        root,
        "第2集",
        _drift_payload_chars({
            "CHAR_01": {"ep_mean_score": 0.80, "ep_n_shots": 3},
            "CHAR_02": {"ep_mean_score": 0.30, "ep_n_shots": 2},
        }),
    )

    out = image_qc.update_face_drift_history(root, "第2集", _drift_payload(0.82))

    assert out is not None
    assert out["characters"]["CHAR_01"]["第2集"] == 0.82
    assert "CHAR_02" not in out["characters"]


def test_cross_episode_face_drift_flags_systematic_decline(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "剧"
    (root / "生产数据").mkdir(parents=True)
    image_qc.cross_episode_face_drift(root, "第1集", _drift_payload(0.82))
    image_qc.cross_episode_face_drift(root, "第2集", _drift_payload(0.78))
    drift = image_qc.cross_episode_face_drift(root, "第3集", _drift_payload(0.60))  # 基线0.82→0.60 掉0.22≥block
    if not drift.get("available"):
        import pytest
        pytest.skip("face_consistency 模块在测试环境不可用")
    assert any(e["char"] == "CHAR_01" and e["severity"] == "high" for e in drift["entries"])


def test_cross_episode_face_drift_quiet_when_stable(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "剧"
    (root / "生产数据").mkdir(parents=True)
    image_qc.cross_episode_face_drift(root, "第1集", _drift_payload(0.82))
    drift = image_qc.cross_episode_face_drift(root, "第2集", _drift_payload(0.81))
    if not drift.get("available"):
        import pytest
        pytest.skip("face_consistency 模块在测试环境不可用")
    assert drift["entries"] == []


# ── A 降级精度多人同框不放行 ─────────────────────────────────────────────────────

def _degraded_face_payload_with_shots(shots: list) -> dict:
    return {"checks": {"face": {"mode": "pillow_fallback", "shots": shots}}}


def test_multi_person_shot_nums_reads_character_ids(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "剧"
    (root / "脚本" / "第1集").mkdir(parents=True)
    (root / "脚本" / "第1集" / "storyboard.json").write_text(json.dumps({"clips": [
        {"id": "Clip_01", "character_ids": ["CHAR_01"]},
        {"id": "Clip_02", "character_ids": ["CHAR_01", "CHAR_02"]},
    ]}), encoding="utf-8")
    nums = image_qc.multi_person_shot_nums(root, "第1集")
    assert nums == {2}


def test_degraded_multi_person_medium_shot_is_hard_block(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "剧"
    (root / "脚本" / "第1集").mkdir(parents=True)
    (root / "脚本" / "第1集" / "storyboard.json").write_text(json.dumps({"clips": [
        {"id": "Clip_02", "character_ids": ["CHAR_01", "CHAR_02"], "shots": [{"lens": "中景"}]},
    ]}), encoding="utf-8")
    payload = _degraded_face_payload_with_shots([{"png": "Clip_02.png", "verdict": "ok"}])
    image_qc.annotate_degraded_closeups(payload, root, "第1集")
    assert payload["checks"]["face"]["shots"][0]["multi_person"] is True
    assert len(image_qc._degraded_multi_person_face_shots(payload)) == 1
    summary = image_qc.summarize(payload)
    assert summary["by_check"].get("face_degraded_multi_person", {}).get("block") == 1
    assert summary["verdict"] == "block"


def test_degraded_single_person_medium_shot_not_blocked(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "剧"
    (root / "脚本" / "第1集").mkdir(parents=True)
    (root / "脚本" / "第1集" / "storyboard.json").write_text(json.dumps({"clips": [
        {"id": "Clip_01", "character_ids": ["CHAR_01"], "shots": [{"lens": "中景"}]},
    ]}), encoding="utf-8")
    payload = _degraded_face_payload_with_shots([{"png": "Clip_01.png", "verdict": "ok"}])
    image_qc.annotate_degraded_closeups(payload, root, "第1集")
    assert image_qc._degraded_multi_person_face_shots(payload) == []
    # 单人中景在降级下不升 hard（不误杀），仍走 review/降级路径
    assert image_qc.summarize(payload)["by_check"].get("face_degraded_multi_person") is None


# ── 辨识标记（MK1）出图前文本预检 ─────────────────────────────────────────────

def _form_with_marks(marks):
    return {"id": "CHAR_01", "key": "CHAR_01/常态", "display": "沈念_常态", "scope": "全篇",
            "strong_aliases": {"CHAR_01", "CHAR_01/常态", "沈念_常态"},
            "identity_marks": [image_qc._normalize_identity_mark(m) for m in marks]}


_PERM_SCAR = {"mark_id": "MARK_左腕旧疤", "type": "疤痕", "region": "左腕",
              "persistence": "permanent", "plot_load": True, "keywords": ["左腕旧疤"]}
_ACQ_EYE = {"mark_id": "MARK_金瞳", "type": "瞳色", "region": "双眼",
            "persistence": {"acquired_at": "第3集"}, "keywords": ["金瞳"]}


def test_normalize_identity_mark_and_tokens():
    perm = image_qc._normalize_identity_mark(_PERM_SCAR)
    assert perm["persistence"] == "permanent" and perm["acquired_ep"] is None
    toks = image_qc._mark_tokens(perm)
    assert "左腕旧疤" in toks and "左腕疤痕" in toks and "疤痕" in toks
    acq = image_qc._normalize_identity_mark(_ACQ_EYE)
    assert acq["persistence"] == "acquired" and acq["acquired_ep"] == 3
    assert image_qc._normalize_identity_mark({"side": "left"}) is None  # 无任何搜索词


def test_lint_identity_marks_permanent_missing_warns():
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 10")  # body 未提左腕旧疤
    codes = {f["code"]: f["level"]
             for f in image_qc.lint_shot_block(blk, valid, [_form_with_marks([_PERM_SCAR])], ep_num=1)}
    assert codes.get("identity_mark_missing") == "warn"


def test_lint_identity_marks_present_passes():
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 11")
    blk["body"] += "\n**资产身份注册层**补：锁凤眼薄唇、左腕旧疤。"
    codes = {f["code"]
             for f in image_qc.lint_shot_block(blk, valid, [_form_with_marks([_PERM_SCAR])], ep_num=1)}
    assert "identity_mark_missing" not in codes


def test_lint_identity_marks_acquired_anachronism_blocks_then_clears():
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 12")
    blk["body"] += "\n沈念睁开金瞳，金光乍现。"
    # 第1集（获得集第3集之前）写了金瞳 → block 穿帮
    codes1 = {f["code"]: f["level"]
              for f in image_qc.lint_shot_block(blk, valid, [_form_with_marks([_ACQ_EYE])], ep_num=1)}
    assert codes1.get("identity_mark_anachronism") == "block"
    # 第4集（获得后）写了金瞳 → 既不穿帮也不缺失
    codes4 = {f["code"]
              for f in image_qc.lint_shot_block(blk, valid, [_form_with_marks([_ACQ_EYE])], ep_num=4)}
    assert "identity_mark_anachronism" not in codes4 and "identity_mark_missing" not in codes4


def test_lint_identity_marks_skips_absent_character():
    valid = {"CHAR_01/常态", "CHAR_02/常态"}
    blk = _char_block("Clip 13")  # 只在场 CHAR_01
    other = {"id": "CHAR_02", "key": "CHAR_02/常态", "display": "柳娘子", "scope": "",
             "strong_aliases": {"CHAR_02", "CHAR_02/常态"},
             "identity_marks": [image_qc._normalize_identity_mark(_PERM_SCAR)]}
    codes = {f["code"] for f in image_qc.lint_shot_block(blk, valid, [other], ep_num=1)}
    assert "identity_mark_missing" not in codes  # CHAR_02 不在场，不查它的标记


# ── 承载角色脸锚（registry 级·后端无关·治定妆脸漂真因） ───────────────────────────

def _setup_carry(tmp_path: Path, asset: dict, character: dict, *, with_png: bool = False) -> Path:
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "asset_registry.json").write_text(
        json.dumps({"assets": [asset]}, ensure_ascii=False), encoding="utf-8")
    (reg / "identity_registry.json").write_text(
        json.dumps({"characters": [character]} if character else {}, ensure_ascii=False),
        encoding="utf-8")
    if with_png:
        img = reg / "图片"
        img.mkdir(parents=True, exist_ok=True)
        (img / "定妆_沈念.png").write_bytes(b"\x89PNG\r\n")  # 存在性检查只看 is_file()
    return tmp_path


def test_carried_identity_unanchored_blocks_when_no_ready_anchor(tmp_path: Path) -> None:
    # VFX 板承载 CHAR_01 的脸，但 CHAR_01 形态无任何 ready 脸锚 → 必无锚渲染新脸 → block
    tmp = _setup_carry(
        tmp_path,
        {"id": "VFX_血脉", "type": "vfx", "name": "万妖血脉觉醒",
         "carries_identity": ["CHAR_01/常态"]},
        {"id": "CHAR_01", "forms": [{"form": "常态", "reference_group": {}}]},
    )
    res = image_qc.audit_carried_identity_anchors(tmp)
    codes = {f["code"]: f["level"] for f in res["findings"]}
    assert codes.get("unanchored_identity_plate") == "block"


def test_carried_identity_ok_when_ready_anchor_present(tmp_path: Path) -> None:
    tmp = _setup_carry(
        tmp_path,
        {"id": "VFX_血脉", "type": "vfx", "name": "万妖血脉觉醒",
         "carries_identity": ["CHAR_01/常态"]},
        {"id": "CHAR_01", "forms": [{"form": "常态", "reference_group": {
            "正面": {"path": "出图/共享/图片/定妆_沈念.png", "status": "ready"}}}]},
        with_png=True,
    )
    res = image_qc.audit_carried_identity_anchors(tmp)
    assert [f for f in res["findings"] if f["level"] == "block"] == []


def test_carried_identity_unknown_character_blocks(tmp_path: Path) -> None:
    tmp = _setup_carry(
        tmp_path,
        {"id": "VFX_血脉", "type": "vfx", "name": "关系图",
         "carries_identity": ["CHAR_99/常态"]},
        {"id": "CHAR_01", "forms": [{"form": "常态", "reference_group": {}}]},
    )
    res = image_qc.audit_carried_identity_anchors(tmp)
    codes = {f["code"] for f in res["findings"]}
    assert "carried_identity_unknown" in codes


def test_carried_identity_pure_scene_asset_not_flagged(tmp_path: Path) -> None:
    # 纯场景资产不承载角色脸 → 不推断、不报
    tmp = _setup_carry(
        tmp_path,
        {"id": "LOC_01", "type": "location", "name": "冷宫庭院"},
        {"id": "CHAR_01", "forms": [{"form": "常态", "reference_group": {}}]},
    )
    res = image_qc.audit_carried_identity_anchors(tmp)
    assert res["findings"] == []


def test_carried_identity_exempt_env_downgrades_to_warn(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("N2D_ALLOW_UNANCHORED_IDENTITY_PLATE", "1")
    tmp = _setup_carry(
        tmp_path,
        {"id": "VFX_血脉", "type": "vfx", "name": "万妖血脉觉醒",
         "carries_identity": ["CHAR_01/常态"]},
        {"id": "CHAR_01", "forms": [{"form": "常态", "reference_group": {}}]},
    )
    res = image_qc.audit_carried_identity_anchors(tmp)
    levels = {f["level"] for f in res["findings"]}
    assert levels == {"warn"}  # 豁免后只 warn 留痕，不 block


def test_carried_identity_block_codes_are_hard() -> None:
    # 落档机检 → gate hard_blocks 的闭环依赖这两个码在 HARD_LINT_CODES
    assert "unanchored_identity_plate" in image_qc.HARD_LINT_CODES
    assert "carried_identity_unknown" in image_qc.HARD_LINT_CODES


# ── 人物脸一致性铁律：audit_asset_face_policy ──
def test_audit_asset_face_policy_blocks_and_skips(tmp_path):
    import image_qc, json
    from pathlib import Path
    root = Path(tmp_path); (root / "出图" / "共享").mkdir(parents=True)
    reg = {"assets": [
        {"id": "WEAPON_HALBERD", "type": "weapon", "owner": "CHAR_J", "name": "戟",
         "reference_group": {"scale_reference": "图片/定妆_握持比例.png"}},
        {"id": "POSTER_BAD", "type": "poster", "name": "群像海报 人物 站立"},
        {"id": "POSTER_OK", "type": "poster", "owner": "CHAR_J", "name": "海报 人物"},
        {"id": "WEAPON_PLAIN", "type": "weapon", "name": "纯武器美术"},
    ]}
    (root / "出图" / "共享" / "asset_registry.json").write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")
    res = image_qc.audit_asset_face_policy(root)
    assert res["available"] is True
    codes = {(f["level"], f["code"]) for f in res["findings"]}
    assert ("block", "asset_face_locked_no_owner") in codes
    assert all(f["code"] != "asset_faceless_face_detected" for f in res["findings"])
    assert any("WEAPON_HALBERD" in n for n in res["notes"])
    assert "asset_faceless_face_detected" in image_qc.HARD_LINT_CODES
    assert "asset_face_locked_no_owner" in image_qc.HARD_LINT_CODES


# ── faceless 持久机器证据：producer 写回 + consumer 信任新鲜证据（#5） ──
def _png(path, color=(180, 180, 180)):
    from PIL import Image
    Image.new("RGB", (128, 128), color).save(path)


def test_faceless_fresh_record_helper(tmp_path):
    import image_qc
    asset = {"face_consistency": {"source": "machine_pixel", "records": [
        {"png": "图片/x.png", "png_sha256": "abc", "verdict": "ok"}]}}
    assert image_qc._faceless_fresh_record(asset, "图片/x.png", "abc")["verdict"] == "ok"
    assert image_qc._faceless_fresh_record(asset, "图片/x.png", "STALE") is None      # sha 不匹配→陈旧
    hand = {"face_consistency": {"verdict": "pass_no_clear_face"}}                     # 手写·无 machine 源
    assert image_qc._faceless_fresh_record(hand, "图片/x.png", "abc") is None


def test_asset_face_pngs_uses_formal_slots_only_and_dedupes():
    import image_qc
    asset = {
        "reference_group": {
            "primary": {
                "path": "出图/共享/图片/场景.png",
                "derivation": {"source_path": "出图/共享/图片/风格锚.png"},
            },
            "front": {"path": "出图/共享/图片/场景.png"},
            "reverse": {"path": "出图/共享/图片/场景_反打.png"},
        },
        "scene_atlas": {
            "base_views": {
                "front": {"path": "出图/共享/图片/场景.png"},
                "back": {"path": "出图/共享/图片/场景_反打.png"},
            },
        },
    }

    assert image_qc._asset_face_pngs(asset) == [
        "出图/共享/图片/场景.png",
        "出图/共享/图片/场景_反打.png",
    ]


def test_gate_trusts_fresh_machine_block_record(tmp_path):
    import image_qc, json
    from pathlib import Path
    root = Path(tmp_path); img = root / "出图" / "共享" / "图片"; img.mkdir(parents=True)
    _png(img / "握持比例.png")
    sha = image_qc._sha256_file(img / "握持比例.png")
    reg = {"assets": [{"id": "WEAPON_H", "type": "weapon", "owner": "CHAR_J", "name": "戟",
        "reference_group": {"scale_reference": "图片/握持比例.png"},
        "face_consistency": {"source": "machine_pixel", "records": [
            {"png": "图片/握持比例.png", "png_sha256": sha, "verdict": "block", "clear_faces": 1}]}}]}
    (root / "出图" / "共享" / "asset_registry.json").write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")
    res = image_qc.audit_asset_face_policy(root)   # 信任登记的 block 机器证据·不必跑 insightface
    assert any(f["code"] == "asset_faceless_face_detected" for f in res["findings"])


def test_record_faceless_evidence_roundtrip(tmp_path):
    import image_qc, json
    from pathlib import Path
    root = Path(tmp_path); img = root / "出图" / "共享" / "图片"; img.mkdir(parents=True)
    _png(img / "握持比例.png")
    reg = {"assets": [{"id": "WEAPON_H", "type": "weapon", "owner": "CHAR_J", "name": "戟",
        "reference_group": {"scale_reference": "图片/握持比例.png"}}]}
    (root / "出图" / "共享" / "asset_registry.json").write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")
    r = image_qc.record_faceless_evidence(root)
    if not r.get("available"):
        return  # 无 insightface 环境优雅跳过
    reg2 = json.loads((root / "出图" / "共享" / "asset_registry.json").read_text(encoding="utf-8"))
    fcrec = reg2["assets"][0].get("face_consistency")
    assert fcrec and fcrec["source"] == "machine_pixel" and fcrec["records"][0]["png_sha256"]


# ── 镜头不是对视对象铁律·全场景版（_lint_camera_gaze_general） ──
def test_camera_gaze_general_warns_nonaction_look_at_camera():
    import image_qc
    f = image_qc._lint_camera_gaze_general("Clip_X", "正向：少女站在窗前，看向镜头，清晰正脸。负向：水印")
    assert any(x["code"] == "camera_gaze_portrait_bias" and x["level"] == "warn" for x in f)


def test_camera_gaze_general_pov_exempt():
    import image_qc
    f = image_qc._lint_camera_gaze_general("Clip_Y", "正向：主观镜头·镜头=对手，少女直视镜头，对观众压迫感特写")
    assert f == []   # POV/对观众特写 豁免


def test_camera_gaze_general_clean_with_eyeline_guard():
    import image_qc
    # 有反向防呆句（不与镜头对视/视线锁定）→ 不报
    f = image_qc._lint_camera_gaze_general("Clip_Z", "正向：少女侧身，视线锁定门口，不看镜头，三分之二侧脸。")
    assert f == []


def test_camera_gaze_general_skips_action_shots():
    import image_qc
    # 动作镜交给 _lint_action_eyeline(block 路径)，general 不重复报
    assert image_qc._lint_camera_gaze_general("Clip_A", "正向：打斗拆招，看向镜头，清晰正脸") == []


def test_n2d_const_camera_gaze_single_source():
    import sys; sys.path.insert(0, "../../n2d/_lib")
    import n2d_const
    assert "selfie" in n2d_const.CAMERA_GAZE_NEGATIVES
    assert n2d_const.is_camera_gaze_pov_exempt("本镜 opponent pov 直视镜头") is True
    assert n2d_const.is_camera_gaze_pov_exempt("少女站在窗前") is False


def test_turnaround_alignment_reason_thresholds():
    # 视平线齐 + 比例一致 → 不报
    assert image_qc.turnaround_alignment_reason(
        {"front": (0.30, 0.20), "side": (0.32, 0.22)}) is None
    # 视平线差 >6% → 报
    r = image_qc.turnaround_alignment_reason({"front": (0.30, 0.20), "side": (0.40, 0.20)})
    assert r and "视平线不齐" in r
    # 脸高比例差 >1.35 倍 → 报
    r2 = image_qc.turnaround_alignment_reason({"front": (0.30, 0.20), "side": (0.31, 0.30)})
    assert r2 and "比例不一" in r2
    # 单视图/不可测 → 不判
    assert image_qc.turnaround_alignment_reason({"front": (0.30, 0.20)}) is None
    assert image_qc.turnaround_alignment_reason({}) is None


def test_expression_review_items_deduplicate_same_physical_reference_path() -> None:
    shared = {"path": "出图/共享/图片/expr.png", "status": "planned"}
    form = {
        "reference_group": {"expressions": [shared], "face_anchor_refs": [shared]},
        "reference_atlas": {"expression_refs": [dict(shared)], "face_anchor_refs": [dict(shared)]},
    }

    items = image_qc._expression_review_items(form)

    assert len(items) == 1
    assert image_qc._view_item_path(items[0]) == shared["path"]


def test_whole_body_geometry_reports_head_feet_center_and_height(tmp_path: Path) -> None:
    from PIL import Image, ImageDraw
    path = tmp_path / "front.png"
    image = Image.new("RGB", (300, 500), (220, 220, 220))
    draw = ImageDraw.Draw(image)
    draw.ellipse((125, 50, 175, 105), fill=(35, 35, 35))
    draw.rectangle((105, 100, 195, 445), fill=(45, 45, 45))
    image.save(path)

    evidence = image_qc.whole_body_geometry(path)

    assert evidence["measurable"] is True
    assert 0.08 < evidence["head_top"] < 0.13
    assert 0.87 < evidence["foot_bottom"] < 0.92
    assert 0.48 < evidence["centerline"] < 0.52
    assert evidence["subject_height"] > 0.75


def _core_turnaround_registry(tmp_path: Path) -> Path:
    from PIL import Image, ImageDraw
    shared = tmp_path / "出图" / "共享"
    images = shared / "图片"
    images.mkdir(parents=True)
    refs = {}
    for index, key in enumerate((*image_qc.TURNAROUND_VIEW_KEYS, "turnaround")):
        rel = f"出图/共享/图片/{key}.png"
        image = Image.new("RGB", (512, 768), (220, 220, 220))
        draw = ImageDraw.Draw(image)
        draw.ellipse((220, 70, 292, 150), fill=(30 + index, 30, 30))
        draw.rectangle((180, 145, 332, 700), fill=(45 + index, 45, 45))
        image.save(tmp_path / rel)
        refs[key] = {"path": rel, "status": "review_pending"}
    expression_rel = "出图/共享/图片/expression_neutral.png"
    expression = Image.new("RGB", (512, 512), (220, 220, 220))
    expression_draw = ImageDraw.Draw(expression)
    expression_draw.ellipse((128, 55, 384, 440), fill=(40, 40, 40))
    expression.save(tmp_path / expression_rel)
    refs["face_anchor_refs"] = [{"path": expression_rel, "status": "review_pending", "emotion": "neutral"}]
    (shared / "identity_registry.json").write_text(json.dumps({
        "characters": [{
            "id": "CHAR_CORE",
            "library_tier": "core_full",
            "forms": [{
                "form": "常态",
                "reference_group": refs,
                "reference_atlas": {
                    "build_tier": "core_full",
                    "base_views": {key: dict(refs[key]) for key in image_qc.TURNAROUND_VIEW_KEYS},
                },
            }],
        }]
    }, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_core_turnaround_requires_hash_bound_per_view_receipts(tmp_path: Path) -> None:
    root = _core_turnaround_registry(tmp_path)

    before = image_qc.audit_turnaround_alignment(root, "第1集")
    assert len(before["human_review_required"]) == len(image_qc.TURNAROUND_FINALIZE_KEYS)
    assert all(f["level"] == "block" for f in before["findings"] if f["code"] == "turnaround_core_view_review_missing")
    refused = image_qc.mark_finalized(root, "CHAR_CORE/常态")
    assert refused["ok"] is False
    assert {row["view"] for row in refused["required_view_receipts"]} == set(image_qc.TURNAROUND_FINALIZE_KEYS)

    invalid_time = image_qc.review_turnaround_view(
        root,
        "CHAR_CORE/常态",
        "front",
        verdict="pass",
        reviewer="art-director",
        reviewed_at="2026-07-14T12:00:00",
    )
    assert invalid_time["ok"] is False and "时区" in invalid_time["msg"]

    missing_confirmation = image_qc.review_turnaround_view(
        root,
        "CHAR_CORE/常态",
        "front",
        verdict="pass",
        reviewer="art-director",
        reviewed_at="2026-07-14T12:00:00+00:00",
    )
    assert missing_confirmation["ok"] is False and "accept-current-pixels" in missing_confirmation["msg"]

    automated = image_qc.review_turnaround_view(
        root,
        "CHAR_CORE/常态",
        "front",
        verdict="pass",
        reviewer="codex-agent",
        reviewed_at="2026-07-14T12:00:00+00:00",
        accept_current_pixels=True,
    )
    assert automated["ok"] is False and "人工声明标识" in automated["msg"]

    for view in image_qc.TURNAROUND_FINALIZE_KEYS:
        result = image_qc.review_turnaround_view(
            root,
            "CHAR_CORE/常态",
            view,
            verdict="pass",
            reviewer="art-director",
            reviewed_at="2026-07-14T12:00:00+00:00",
            note="identity/costume/body alignment checked",
            accept_current_pixels=True,
        )
        assert result["ok"] is True

    registry = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))
    expression_receipt = registry["characters"][0]["forms"][0]["reference_group"]["face_anchor_refs"][0]["human_review"]
    assert expression_receipt["view"] == "expression"
    assert expression_receipt["character_id"] == "CHAR_CORE"
    assert expression_receipt["png_sha256"]
    assert expression_receipt["registry_binding_fingerprint"]
    assert expression_receipt["review_contract"] == "n2d_expression_review_v1"
    assert expression_receipt["confirmation"]["accepted_current_pixels"] is True

    after = image_qc.audit_turnaround_alignment(root, "第1集")
    assert after["human_review_required"] == []
    finalized = image_qc.mark_finalized(root, "CHAR_CORE/常态")
    assert finalized["ok"] is True

    # Any pixel change invalidates only that view's receipt and prevents a
    # stale form-level self_check from being re-finalized.
    (root / "出图" / "共享" / "图片" / "side.png").write_bytes(b"changed-pixels")
    stale = image_qc.mark_finalized(root, "CHAR_CORE/常态")
    assert stale["ok"] is False
    assert [row["view"] for row in stale["required_view_receipts"]] == ["side"]


def test_executor_visual_receipt_requires_explicit_project_authorization(tmp_path: Path) -> None:
    root = _core_turnaround_registry(tmp_path)
    refused = image_qc.review_turnaround_view(
        root,
        "CHAR_CORE/常态",
        "front",
        verdict="pass",
        reviewer="Codex视觉执行者",
        review_kind="executor_visual",
        accept_current_pixels=True,
    )
    assert refused["ok"] is False
    assert "未在 _设置.md 明确授权" in refused["msg"]

    (root / "_设置.md").write_text(
        "- 图片验收模式：逐张机器QC+实际目视  # source=explicit_user\n"
        "- 用户明确要求每张由执行者实际像素目视后才进入下一张\n",
        encoding="utf-8",
    )
    accepted = image_qc.review_turnaround_view(
        root,
        "CHAR_CORE/常态",
        "front",
        verdict="pass",
        reviewer="Codex视觉执行者",
        review_kind="executor_visual",
        accept_current_pixels=True,
    )
    assert accepted["ok"] is True
    registry = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))
    front = registry["characters"][0]["forms"][0]["reference_group"]["front"]
    assert "human_review" not in front
    assert front["visual_review"]["review_kind"] == "executor_visual"
    assert front["visual_review"]["human_signoff"] is False
    audit = image_qc.audit_turnaround_alignment(root, "第1集")
    pending_front = [row for row in audit["human_review_required"] if row["view"] == "front"]
    assert pending_front == []


def test_style_anchor_executor_visual_review_promotes_matching_entries(tmp_path: Path) -> None:
    from PIL import Image

    image_dir = tmp_path / "出图" / "共享" / "图片"
    image_dir.mkdir(parents=True)
    rel = "出图/共享/图片/风格锚_国漫写实.png"
    Image.new("RGB", (512, 768), (80, 90, 100)).save(tmp_path / rel)
    registry_path = tmp_path / "出图" / "共享" / "style_anchor_registry.json"
    item = {"id": "STYLE_ANCHOR", "path": rel, "status": "review_pending"}
    registry_path.write_text(json.dumps({
        "selected_anchor": dict(item),
        "anchors": [dict(item)],
    }, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "_设置.md").write_text(
        "- 图片验收模式：逐张机器QC+实际目视  # source=explicit_user\n"
        "- 用户明确要求每张由执行者实际像素目视后才进入下一张\n",
        encoding="utf-8",
    )

    result = image_qc.review_style_anchor(
        tmp_path,
        reviewer="Codex视觉执行者",
        review_kind="executor_visual",
        note="style/material/color checked",
        accept_current_pixels=True,
    )

    assert result["ok"] is True
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    selected = registry["selected_anchor"]
    assert selected["status"] == "ready"
    assert selected["sha256"] == result["png_sha256"]
    assert selected["visual_review"]["human_signoff"] is False
    assert registry["anchors"][0]["visual_review"]["png_sha256"] == result["png_sha256"]


@pytest.mark.parametrize("mode", ["absolute", "path_escape", "symlink", "noncanonical"])
def test_legacy_signer_path_escape_symlink_and_noncanonical_are_rejected(
    tmp_path: Path,
    mode: str,
) -> None:
    root = _core_turnaround_registry(tmp_path)
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    front = registry["characters"][0]["forms"][0]["reference_group"]["front"]
    if mode == "absolute":
        front["path"] = str((root / "出图" / "共享" / "图片" / "front.png").resolve())
        expected = "absolute_registry_evidence_path_not_allowed"
    elif mode == "path_escape":
        outside = root.parent / f"{root.name}_outside.png"
        outside.write_bytes((root / "出图" / "共享" / "图片" / "front.png").read_bytes())
        front["path"] = f"../{outside.name}"
        expected = "registry_evidence_path_outside_project_root"
    elif mode == "symlink":
        link = root / "出图" / "共享" / "图片" / "front_link.png"
        link.symlink_to("front.png")
        front["path"] = "出图/共享/图片/front_link.png"
        expected = "registry_evidence_path_not_canonical_project_relative"
    else:
        front["path"] = "出图/共享/图片/../图片/front.png"
        expected = "registry_evidence_path_not_canonical_project_relative"
    registry_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")

    result = image_qc.review_turnaround_view(
        root,
        "CHAR_CORE/常态",
        "front",
        verdict="pass",
        reviewer="art-director",
        reviewed_at="2026-07-14T12:00:00+00:00",
        accept_current_pixels=True,
    )

    assert result["ok"] is False
    assert expected in result["msg"]


def test_legacy_finalize_consumer_duplicate_png_sha_is_independently_blocked(tmp_path: Path) -> None:
    root = _core_turnaround_registry(tmp_path)
    for view in image_qc.TURNAROUND_FINALIZE_KEYS:
        result = image_qc.review_turnaround_view(
            root,
            "CHAR_CORE/常态",
            view,
            verdict="pass",
            reviewer="art-director",
            reviewed_at="2026-07-14T12:00:00+00:00",
            accept_current_pixels=True,
        )
        assert result["ok"] is True

    image_dir = root / "出图" / "共享" / "图片"
    (image_dir / "back.png").write_bytes((image_dir / "side.png").read_bytes())
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    back = registry["characters"][0]["forms"][0]["reference_group"]["back"]
    sha = image_qc._sha256_file(image_dir / "back.png")
    back["sha256"] = sha
    back["human_review"]["png_sha256"] = sha
    back["human_review"]["registry_binding_fingerprint"] = image_qc.identity_review_binding_fingerprint(
        character_id="CHAR_CORE",
        form="常态",
        library_tier="core_full",
        view="back",
        path=back["path"],
        png_sha256=sha,
    )
    registry_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")

    finalized = image_qc.mark_finalized(root, "CHAR_CORE/常态")

    assert finalized["ok"] is False
    assert any(
        "duplicate_png_sha_across_buckets" in row["issues"]
        for row in finalized["required_view_receipts"]
    )


def test_body_alignment_threshold_is_warn_evidence_not_hard_receipt() -> None:
    reason = image_qc.turnaround_body_alignment_reason({
        "front": {"measurable": True, "head_top": 0.10, "foot_bottom": 0.90, "centerline": 0.50, "subject_height": 0.80},
        "back": {"measurable": True, "head_top": 0.20, "foot_bottom": 0.98, "centerline": 0.64, "subject_height": 0.60},
    })
    assert reason and "头顶线不齐" in reason and "脚底线不齐" in reason and "身体中心线不齐" in reason


def test_audit_shot_variety_static_and_duplicate(tmp_path):
    from PIL import Image
    import json as _json
    root = tmp_path
    img_dir = root / "出图" / "第1集" / "图片"
    img_dir.mkdir(parents=True)
    solid = Image.new("RGB", (64, 64), (120, 120, 120))
    grad = Image.new("RGB", (64, 64))
    for x in range(64):
        for y in range(64):
            grad.putpixel((x, y), (x * 4 % 256, y * 4 % 256, (x + y) % 256))
    solid.save(img_dir / "a_first.png"); solid.save(img_dir / "a_end.png")
    solid.save(img_dir / "b_first.png"); grad.save(img_dir / "b_end.png")
    sb_dir = root / "脚本" / "第1集"
    sb_dir.mkdir(parents=True)
    (sb_dir / "storyboard.json").write_text(_json.dumps({"clips": [
        {"id": "C1", "duration": 12.0, "pacing_role": "主看点",
         "firstframe_png": "出图/第1集/图片/a_first.png", "endframe_png": "出图/第1集/图片/a_end.png",
         "location_id": "L1", "shots": [{"lens": "CU 固定"}]},
        {"id": "C2", "duration": 5.0, "pacing_role": "主看点",
         "firstframe_png": "出图/第1集/图片/b_first.png", "endframe_png": "出图/第1集/图片/b_end.png",
         "location_id": "L1", "shots": [{"lens": "LS 固定"}]},
    ]}, ensure_ascii=False), encoding="utf-8")
    res = image_qc.audit_shot_variety(root, "第1集")
    codes = {(f["code"], f["level"]) for f in res["findings"]}
    # C1: first==end 且 12s ≥ block 秒、d=0 ≤ block 阈 → block
    assert ("static_long_take", "block") in codes
    # C1.first 与 C2.first 同图 → 跨 Clip 构图重复 warn
    assert ("duplicate_composition", "warn") in codes


def test_audit_shot_variety_hold_role_exempt(tmp_path):
    from PIL import Image
    import json as _json
    root = tmp_path
    img_dir = root / "出图" / "第1集" / "图片"
    img_dir.mkdir(parents=True)
    solid = Image.new("RGB", (64, 64), (10, 10, 10))
    solid.save(img_dir / "a_first.png"); solid.save(img_dir / "a_end.png")
    sb_dir = root / "脚本" / "第1集"
    sb_dir.mkdir(parents=True)
    (sb_dir / "storyboard.json").write_text(_json.dumps({"clips": [
        {"id": "C1", "duration": 12.0, "pacing_role": "集尾钩子·留白",
         "firstframe_png": "出图/第1集/图片/a_first.png", "endframe_png": "出图/第1集/图片/a_end.png",
         "location_id": "L1", "shots": [{"lens": "CU 固定"}]},
    ]}, ensure_ascii=False), encoding="utf-8")
    res = image_qc.audit_shot_variety(root, "第1集")
    assert not any(f["code"] == "static_long_take" for f in res["findings"])


def test_audit_shot_variety_lens_monotony(tmp_path):
    import json as _json
    root = tmp_path
    (root / "脚本" / "第1集").mkdir(parents=True)
    clips = [{"id": f"C{i}", "duration": 6.0, "location_id": "L1",
              "shots": [{"lens": "CU 固定"}]} for i in range(1, 7)]
    (root / "脚本" / "第1集" / "storyboard.json").write_text(
        _json.dumps({"clips": clips}, ensure_ascii=False), encoding="utf-8")
    res = image_qc.audit_shot_variety(root, "第1集")
    assert any(f["code"] == "lens_variety_low" for f in res["findings"])


def test_lens_classes_reads_storyboard_shot_size_before_physical_lens() -> None:
    clip = {
        "shots": [
            {"shot_size": "ECU→CU", "lens": "85mm"},
            {"shot_size": "MS", "lens": "50mm"},
        ]
    }

    assert image_qc._lens_classes(clip) == {"ECU", "CU", "MS"}
