import json
from pathlib import Path

import pytest

import placement_adaptation as pa


def _progress(rows):
    body = [
        "# Ad", "", "## 交付版本矩阵", "",
        "| 交付件 | 时长 | 比例 | 类型 | 交付规格 | 状态 | 成片路径 |",
        "|---|---|---|---|---|---|---|",
    ]
    body.extend(f"| {label} | {duration} | {aspect} | {kind} | 平台默认 | ⬜ | |"
                for label, duration, aspect, kind in rows)
    return "\n".join(body) + "\n"


def _root(tmp_path: Path, *, multi=False):
    root = tmp_path / "ad"
    (root / "需求").mkdir(parents=True)
    rows = [("主片", "30s", "16:9", "master")]
    if multi:
        rows.append(("reframe 9:16", "30s", "9:16", "reframe"))
    (root / "_进度.md").write_text(_progress(rows), encoding="utf-8")
    (root / "需求" / "brief.json").write_text("{}", encoding="utf-8")
    return root


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _platform_brief(root: Path, config=None):
    safe = root / "证据" / "tiktok-safe.png"
    safe.parent.mkdir(parents=True, exist_ok=True)
    safe.write_bytes(b"safe-template")
    brief = {
        "platforms": ["TikTok"],
        "placements": ["TikTok:auction_in_feed"],
        "platform_safe_zone_evidence": {"TikTok:auction_in_feed": "证据/tiktok-safe.png"},
        "deliverable_placements": {
            "master": ["TikTok:auction_in_feed"],
            "reframe_9x16": ["TikTok:auction_in_feed"],
        },
        "placement_adaptation_modes": config or {},
    }
    _write_json(root / "需求" / "brief.json", brief)
    return brief


def test_original_master_is_native_and_auto_approved(tmp_path):
    root = _root(tmp_path)
    report = pa.evaluate(root)

    assert report["summary"]["approved"] is True
    assert report["items"][0]["selected_mode"] == "native_master"
    assert report["plan_sha256"] == pa.plan_sha(report)


def test_plan_digest_is_stable_but_changes_with_bound_brief_bytes(tmp_path):
    root = _root(tmp_path)
    first = pa.evaluate(root)
    second = pa.evaluate(root)
    assert first["plan_sha256"] == second["plan_sha256"]

    (root / "需求" / "brief.json").write_text('{"campaign_mode":"formal"}', encoding="utf-8")
    changed = pa.evaluate(root)
    assert changed["plan_sha256"] != first["plan_sha256"]


def test_multi_aspect_never_defaults_to_mechanical_crop(tmp_path):
    root = _root(tmp_path, multi=True)
    _platform_brief(root)
    report = pa.evaluate(root)
    row = next(item for item in report["items"] if item["deliverable_id"] == "reframe_9x16")

    assert row["selected_mode"] is None
    assert row["status"] == "blocked"
    assert any(f["code"] == "adaptation_mode_missing" for f in row["findings"])


def test_mechanical_reframe_requires_focus_approval_and_safe_zone_evidence(tmp_path):
    root = _root(tmp_path, multi=True)
    _platform_brief(root, {"reframe_9x16": {"mode": "mechanical_reframe"}})
    report = pa.evaluate(root)

    codes = {f["code"] for f in report["findings"]}
    assert "adaptation_approval_missing" in codes
    assert "adaptation_focus_plan_missing" in codes
    assert "adaptation_approval_evidence_missing" in codes


def test_mechanical_reframe_passes_only_with_bound_current_evidence(tmp_path):
    root = _root(tmp_path, multi=True)
    (root / "证据").mkdir(parents=True, exist_ok=True)
    (root / "证据" / "approval.md").write_text("制片与创意批准逐镜焦点裁切", encoding="utf-8")
    _write_json(root / "证据" / "focus.json", {"shots": [
        {"shot_id": "S1", "start": 0, "end": 3, "x": 0.45, "y": 0.5},
    ]})
    _platform_brief(root, {"reframe_9x16": {
        "mode": "mechanical_reframe", "approved_by": "创意甲",
        "evidence_file": "证据/approval.md", "focus_plan_file": "证据/focus.json",
    }})
    report = pa.evaluate(root)
    row = next(item for item in report["items"] if item["deliverable_id"] == "reframe_9x16")

    assert row["status"] == "approved", row["findings"]
    assert row["evidence"]["focus_plan"]["sha256"]
    assert row["evidence"]["safe_zones"]["TikTok:auction_in_feed"]["sha256"]


def test_structural_text_risk_recommends_native_reedit(tmp_path):
    root = _root(tmp_path, multi=True)
    _write_json(root / "脚本" / "storyboard.json", {"shots": [{
        "shot_id": "S1", "subtitle": "立即购买", "claim_ids": ["C1"],
    }]})
    (root / "证据").mkdir(parents=True, exist_ok=True)
    (root / "证据" / "approval.md").write_text("批准原生重编", encoding="utf-8")
    native_source = root / "出视频" / "分镜" / "视频" / "竖版镜头01.mp4"
    native_source.parent.mkdir(parents=True)
    native_source.write_bytes(b"native-shot")
    _write_json(root / "证据" / "vertical-shots.json", {"shots": [
        {"shot_id": "S1", "composition": "竖版重构，CTA 避开底部与右侧 UI",
         "source_path": "出视频/分镜/视频/竖版镜头01.mp4"},
    ]})
    _platform_brief(root, {"reframe_9x16": {
        "mode": "native_reedit", "approved_by": "创意甲",
        "evidence_file": "证据/approval.md", "shot_plan_file": "证据/vertical-shots.json",
    }})
    report = pa.evaluate(root)
    row = next(item for item in report["items"] if item["deliverable_id"] == "reframe_9x16")

    assert row["recommended_mode"] == "native_reedit"
    assert row["status"] == "approved", row["findings"]
    assert row["evidence"]["native_sources"][0]["sha256"] == pa.sha256_file(native_source)


def test_native_execution_requires_every_shot_plan_source(tmp_path, monkeypatch):
    root = _root(tmp_path, multi=True)
    (root / "证据").mkdir(parents=True, exist_ok=True)
    (root / "证据" / "approval.md").write_text("批准原生重编", encoding="utf-8")
    source = root / "出视频" / "分镜" / "视频" / "竖版镜头01.mp4"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"native-shot")
    _write_json(root / "证据" / "vertical-shots.json", {"shots": [{
        "shot_id": "S1", "composition": "竖版重构",
        "source_path": "出视频/分镜/视频/竖版镜头01.mp4",
    }]})
    _platform_brief(root, {"reframe_9x16": {
        "mode": "native_reedit", "approved_by": "创意甲",
        "evidence_file": "证据/approval.md", "shot_plan_file": "证据/vertical-shots.json",
    }})
    master = root / "合成" / "成片_主片.mp4"
    output = root / "合成" / "多比例" / "成片_9x16.mp4"
    master.parent.mkdir(parents=True)
    output.parent.mkdir(parents=True)
    master.write_bytes(b"master")
    output.write_bytes(b"vertical")
    monkeypatch.setattr(pa.render_profile, "compile_profile", lambda _root: {
        "profile_sha256": "profile-current", "summary": {"block": 0},
    })

    with pytest.raises(ValueError, match="未消费"):
        pa.record_execution(
            root, "reframe_9x16", "native_reedit", ["合成/成片_主片.mp4"],
            "合成/多比例/成片_9x16.mp4", "剪辑甲",
        )
    receipt = pa.record_execution(
        root, "reframe_9x16", "native_reedit", ["出视频/分镜/视频/竖版镜头01.mp4"],
        "合成/多比例/成片_9x16.mp4", "剪辑甲",
    )
    assert receipt["inputs"][0]["path"] == "出视频/分镜/视频/竖版镜头01.mp4"


def test_record_execution_binds_actual_mode_inputs_output_plan_and_profile(tmp_path, monkeypatch):
    root = _root(tmp_path, multi=True)
    (root / "证据").mkdir(parents=True, exist_ok=True)
    (root / "证据" / "approval.md").write_text("批准机械适配", encoding="utf-8")
    _write_json(root / "证据" / "focus.json", {"shots": [
        {"shot_id": "S1", "start": 0, "end": 3, "x": 0.5, "y": 0.5},
    ]})
    _platform_brief(root, {"reframe_9x16": {
        "mode": "mechanical_reframe", "approved_by": "创意甲",
        "evidence_file": "证据/approval.md", "focus_plan_file": "证据/focus.json",
    }})
    source = root / "合成" / "成片_主片.mp4"
    output = root / "合成" / "多比例" / "成片_9x16.mp4"
    source.parent.mkdir(parents=True)
    output.parent.mkdir(parents=True)
    source.write_bytes(b"master")
    output.write_bytes(b"vertical")
    monkeypatch.setattr(pa.render_profile, "compile_profile", lambda _root: {
        "profile_sha256": "profile-current", "summary": {"block": 0},
    })

    receipt = pa.record_execution(
        root, "reframe_9x16", "mechanical_reframe",
        ["合成/成片_主片.mp4"], "合成/多比例/成片_9x16.mp4", "剪辑甲",
    )

    assert receipt["actual_mode"] == "mechanical_reframe"
    assert receipt["output"]["sha256"] == pa.sha256_file(output)
    assert receipt["adaptation_plan_sha256"]
    assert receipt["adaptation_item_sha256"]
    assert receipt["render_profile_sha256"] == "profile-current"
    assert receipt["receipt_sha256"]

    with pytest.raises(ValueError, match="不一致"):
        pa.record_execution(
            root, "reframe_9x16", "native_reedit",
            ["合成/成片_主片.mp4"], "合成/多比例/成片_9x16.mp4", "剪辑甲",
        )
