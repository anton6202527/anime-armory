from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("gate_policy_coverage.py")
spec = importlib.util.spec_from_file_location("gate_policy_coverage", SCRIPT)
gate_policy_coverage = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(gate_policy_coverage)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _release_evidence(root: Path, episode: str) -> None:
    (root / "_进度.md").write_text("| 集 | 验收 |\n|---|---|\n| 第1集 | ✅ |\n", encoding="utf-8")
    _write_json(root / "合规" / "compliance_manifest.json", {"kind": "n2d_compliance_manifest", "version": 1})
    _write_json(root / "脚本" / episode / "storyboard.json", {"kind": "storyboard", "clips": []})
    _write_json(root / "生产数据" / f"story_economy_audit_{episode}.json", {"kind": "n2d_story_economy_audit", "version": 1, "ok": True, "summary": {"blocks": 0}})
    _write_json(root / "脚本" / episode / "production_handoff_pack.json", {"kind": "n2d_production_handoff_pack", "version": 1, "status": "confirmed"})
    _write_json(root / "脚本" / episode / "continuity_chain.json", {"kind": "n2d_continuity_chain", "version": 1, "status": "confirmed", "summary": {"block": 0}})
    _write_json(root / "脚本" / episode / "continuity_bible.json", {"kind": "n2d_continuity_bible", "version": 1, "status": "confirmed"})
    _write_json(root / "脚本" / episode / "ai_shooting_schedule.json", {"kind": "n2d_ai_shooting_schedule", "version": 1, "status": "confirmed"})
    (root / "脚本" / episode / "ai_call_sheet.md").write_text("status: confirmed\n# call sheet\n", encoding="utf-8")
    _write_json(root / "生产数据" / f"production_locks_{episode}.json", {"kind": "n2d_production_locks", "version": 1, "status": "confirmed", "locks": []})
    _write_json(root / "出图" / "共享" / "identity_registry.json", {"kind": "n2d_identity_registry", "version": 1})
    _write_json(root / "出图" / "共享" / "asset_registry.json", {"kind": "n2d_asset_reference_registry", "version": 1})
    _write_json(root / "生产数据" / f"budget_{episode}.json", {"status": "pass"})
    _write_json(root / "生产数据" / "image_backend_capabilities" / "test.json", {"status": "fresh"})
    _write_json(root / "生产数据" / "image_qc" / episode / f"image_qc_{episode}.json", {"kind": "n2d_image_qc", "version": 1, "status": "pass"})
    _write_json(root / "生产数据" / "consistency_ledger_第1集.json", {"kind": "n2d_consistency_ledger", "version": 1, "status": "pass"})
    _write_json(root / "生产数据" / f"generation_recipe_manifest_{episode}.json", {"kind": "n2d_generation_recipe_manifest", "version": 1, "status": "pass", "records": [], "summary": {}, "root": str(root), "episode": episode})
    _write_json(root / "生产数据" / f"contract_inheritance_{episode}.json", {"kind": "n2d_contract_inheritance", "version": 1, "status": "pass"})
    _write_json(root / "出视频" / episode / "prompt" / "video_model_routes.json", {"kind": "n2d_video_model_routes", "version": 1, "routes": []})
    video = root / "出视频" / episode / "视频" / "Clip_01.mp4"
    video.parent.mkdir(parents=True, exist_ok=True)
    video.write_bytes(b"mp4")
    master = root / "合成" / episode / f"成片_{episode}_zh.mp4"
    master.parent.mkdir(parents=True, exist_ok=True)
    master.write_bytes(b"master")
    (root / "脚本" / episode / "字幕_中文.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\n对白\n", encoding="utf-8")
    _write_json(root / "生产数据" / f"score_{episode}.json", {"kind": "n2d_episode_review_score", "version": 1, "status": "pass"})
    _write_json(root / "生产数据" / f"review_ui_{episode}.json", {"kind": "n2d_review_ui", "version": 1, "status": "pass"})
    _write_json(root / "生产数据" / f"review_ui_findings_{episode}.json", {"kind": "n2d_consistency_findings", "version": 1, "episode": episode, "findings": []})
    _write_json(root / "生产数据" / f"review_signoff_{episode}.json", {"status": "approved"})
    _write_json(root / "生产数据" / f"identity_voice_print_{episode}.json", {"kind": "n2d_identity_voice_print", "version": 1, "available": False, "mode": "no_audio"})
    _write_json(root / "生产数据" / f"release_verdict_{episode}.json", {"kind": "n2d_release_verdict", "version": 1, "status": "internal-only"})


def test_gate_policy_coverage_fails_missing_release_evidence(tmp_path: Path) -> None:
    payload = gate_policy_coverage.build_coverage(tmp_path, "第1集")

    assert payload["status"] == "fail"
    completion_rows = {
        row["group"]: row for row in payload["groups"]
        if row["group"] in {"human_review", "release_verdict"}
    }
    assert all(row["completion_output"] for row in completion_rows.values())
    assert all("release_evidence" not in row["missing"] for row in completion_rows.values())


def test_gate_policy_coverage_write_check_passes_complete_fixture(tmp_path: Path) -> None:
    episode = "第1集"
    _release_evidence(tmp_path, episode)

    payload = gate_policy_coverage.build_coverage(tmp_path, episode)
    gate_policy_coverage.write_coverage(tmp_path, episode, payload)

    assert payload["status"] == "pass"
    assert gate_policy_coverage.check_coverage(tmp_path, episode)["status"] == "pass"
    assert (tmp_path / "生产数据" / f"gate_policy_coverage_{episode}.json").is_file()
    assert (tmp_path / "生产数据" / "gate_policy_coverage.json").is_file()


def test_gate_check_binding_all_groups_healthy_and_detects_drift():
    # P0-5：政策↔gate 代码绑定——10 个映射组的 check 函数当前在 gate.py 既定义又被调用。
    healthy = {g: gate_policy_coverage.gate_check_gaps(g) for g in gate_policy_coverage.GROUP_GATE_CHECKS}
    assert all(v == [] for v in healthy.values()), {g: v for g, v in healthy.items() if v}
    # 删除函数 → gate_check_missing；仅定义无调用 → gate_check_unwired
    saved = gate_policy_coverage._gate_src_cache
    try:
        gate_policy_coverage._gate_src_cache = "def unrelated():\n    pass\n"
        assert gate_policy_coverage.gate_check_gaps("compliance") == ["gate_check_missing:check_compliance_manifest"]
        gate_policy_coverage._gate_src_cache = "def check_compliance_manifest(r, e, s):\n    pass\n"
        assert gate_policy_coverage.gate_check_gaps("compliance") == ["gate_check_unwired:check_compliance_manifest"]
        # AST：函数名只在字符串里出现（旧正则会误判 wired）→ 仍 unwired
        gate_policy_coverage._gate_src_cache = (
            'def run(r, e, s):\n    x = "check_compliance_manifest()"\n'
            "def check_compliance_manifest(r, e, s):\n    pass\n"
        )
        assert gate_policy_coverage.gate_check_gaps("compliance") == ["gate_check_unwired:check_compliance_manifest"]
        # AST：调用只在不可达的死代码里（run 不调用它）→ unwired
        gate_policy_coverage._gate_src_cache = (
            "def dead(r, e, s):\n    check_compliance_manifest(r, e, s)\n"
            "def check_compliance_manifest(r, e, s):\n    pass\n"
            "def run(r, e, s):\n    pass\n"
        )
        assert gate_policy_coverage.gate_check_gaps("compliance") == ["gate_check_unwired:check_compliance_manifest"]
        # AST：从 run 真正可达地调用 → 健全
        gate_policy_coverage._gate_src_cache = (
            "def run(r, e, s):\n    check_compliance_manifest(r, e, s)\n"
            "def check_compliance_manifest(r, e, s):\n    pass\n"
        )
        assert gate_policy_coverage.gate_check_gaps("compliance") == []
    finally:
        gate_policy_coverage._gate_src_cache = saved


def test_evidence_rejects_empty_and_invalid_json(tmp_path: Path) -> None:
    ep = "第1集"
    pdir = tmp_path / "生产数据"
    pdir.mkdir(parents=True)
    pattern = ["生产数据/budget_{ep}.json"]
    # 有效 json → 计入
    (pdir / f"budget_{ep}.json").write_text('{"status":"pass"}', encoding="utf-8")
    assert gate_policy_coverage.evidence_matches(tmp_path, ep, pattern)
    # 空文件 → 不计入
    (pdir / f"budget_{ep}.json").write_text("", encoding="utf-8")
    assert gate_policy_coverage.evidence_matches(tmp_path, ep, pattern) == []
    # 坏 json → 不计入
    (pdir / f"budget_{ep}.json").write_text("{not json", encoding="utf-8")
    assert gate_policy_coverage.evidence_matches(tmp_path, ep, pattern) == []


def test_gate_inventory_real_gate_all_reachable() -> None:
    # 真 gate.py：每个 check_* 都应从 run() 可达，0 死闸（回归基线）。
    inv = gate_policy_coverage.gate_inventory()
    assert inv["status"] == "pass", inv.get("dead")
    assert inv["total"] >= 90  # 当前 94，给冗余防误改
    assert inv["dead"] == []
    assert inv["reachable"] == inv["total"]


def test_gate_inventory_detects_dead_gate() -> None:
    # 定义了 check_* 但 run() 不调用 → 死闸 → fail。
    saved = gate_policy_coverage._gate_src_cache
    try:
        gate_policy_coverage._gate_src_cache = (
            "def run(r, e, s):\n    check_alive(r, e, s)\n"
            "def check_alive(r, e, s):\n    pass\n"
            "def check_dead(r, e, s):\n    pass\n"  # 定义在但 run 不调用
        )
        inv = gate_policy_coverage.gate_inventory()
        assert inv["status"] == "fail"
        assert inv["dead"] == ["check_dead"]
        assert inv["reachable"] == 1 and inv["total"] == 2
    finally:
        gate_policy_coverage._gate_src_cache = saved
