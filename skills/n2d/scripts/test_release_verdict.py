from __future__ import annotations

import importlib.util
import json
import os
import time
from pathlib import Path


SCRIPT = Path(__file__).with_name("release_verdict.py")
spec = importlib.util.spec_from_file_location("release_verdict", SCRIPT)
release_verdict = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(release_verdict)

from skill_snapshot import artifact_fingerprint  # noqa: E402


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _write_bytes(path: Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return release_verdict.sha256_file(path)


def _release_ready_project(root: Path, episode: str = "第1集") -> None:
    (root / "_设置.md").write_text("- 制作模式: 配音先行\n", encoding="utf-8")
    (root / "_进度.md").write_text(f"""# demo

| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 奇观连续性 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 | 验收 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| {episode} | 100 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
""", encoding="utf-8")
    master = root / "合成" / episode / f"成片_{episode}_zh.mp4"
    _write_bytes(master, b"final master")
    past = time.time() - 10
    os.utime(master, (past, past))

    comp = release_verdict.compliance_mod.default_manifest(root, episode)
    comp["distribution_intent"] = "internal_only"
    comp["platform_review"]["targets"][0].update({
        "platform": "内部预览",
        "region": "CN",
        "language": "zh",
        "policy_profile": "internal_preview_2026-07-03",
        "profile_checked_at": "2026-07-03",
        "copyright_review": "not_applicable",
        "content_rating_review": "not_applicable",
    })
    comp["regulatory_filing"]["applicable"] = False
    comp["regulatory_filing"]["notes"] = "内部预览不公开投放"
    comp["ai_labeling"]["explicit_label"]["status"] = "done"
    comp["ai_labeling"]["explicit_label"]["prominent_label_spec"] = "前5s出现/≥3s持续/显著位/裁剪后存活 已确认"
    comp["ai_labeling"]["implicit_metadata"]["service_provider_code"] = "SP-INTERNAL"
    comp["ai_labeling"]["implicit_metadata"]["content_id"] = "CID-001"
    comp["ai_labeling"]["implicit_metadata"]["applied"] = True
    _write_json(root / "合规" / "compliance_manifest.json", comp)
    _write_json(root / "生产数据" / f"gate_findings_review_{episode}.json", {"kind": "n2d_gate_findings", "version": 1, "findings": [], "summary": {"severity": {"block": 0, "warn": 0}}})
    _write_json(root / "生产数据" / f"score_{episode}.json", {"kind": "n2d_episode_review_score", "version": 1, "status": "pass", "score": 91, "threshold": 80})
    _write_json(root / "生产数据" / f"consistency_ledger_{episode}.json", {"kind": "n2d_consistency_ledger", "version": 1, "status": "pass", "delivery_surface": {"status": "pass"}, "counts": {"block": 0, "high": 0}})
    _write_json(root / "生产数据" / f"review_ui_{episode}.json", {"kind": "n2d_review_ui", "version": 1, "status": "pass"})
    _write_json(root / "生产数据" / f"review_ui_findings_{episode}.json", {"kind": "n2d_consistency_findings", "version": 1, "episode": episode, "findings": []})
    _write_json(root / "生产数据" / f"generation_recipe_manifest_{episode}.json", {"kind": "n2d_generation_recipe_manifest", "version": 1, "status": "pass", "records": [], "summary": {}, "root": str(root), "episode": episode})
    _write_json(root / "脚本" / episode / "production_breakdown.json", {"kind": "n2d_production_breakdown", "version": 1, "episode": episode, "status": "confirmed", "scene_breakdowns": []})
    _write_json(root / "脚本" / episode / "continuity_breakdown.json", {"kind": "n2d_continuity_breakdown", "version": 1, "episode": episode, "status": "confirmed", "rows": []})
    call_sheet = root / "脚本" / episode / "ai_call_sheet.md"
    call_sheet.parent.mkdir(parents=True, exist_ok=True)
    call_sheet.write_text("---\nkind: n2d_ai_call_sheet\nstatus: confirmed\n---\n# call sheet\n", encoding="utf-8")
    clip1_hash = _write_bytes(root / "出视频" / episode / "Clip01.mp4", b"pilot clip 1")
    clip2_hash = _write_bytes(root / "出视频" / episode / "Clip02.mp4", b"pilot clip 2")
    _write_json(root / "生产数据" / "pilot_qc_Clip01.json", {"status": "pass"})
    _write_json(root / "生产数据" / "pilot_qc_Clip02.json", {"status": "pass"})
    _write_json(root / "生产数据" / f"pilot_acceptance_{episode}.json", {
        "kind": "n2d_pilot_acceptance",
        "version": 1,
        "episode": episode,
        "status": "accepted",
        "reviewer": "human-qc",
        "risk_selection": {"method": "代表镜头风险排序", "risk_factors": ["face", "scene", "action", "lipsync", "seam", "routing"]},
        "clips": [
            {"clip_id": "Clip_01", "artifact_path": f"出视频/{episode}/Clip01.mp4", "artifact_sha256": clip1_hash, "qc_report": "生产数据/pilot_qc_Clip01.json"},
            {"clip_id": "Clip_02", "artifact_path": f"出视频/{episode}/Clip02.mp4", "artifact_sha256": clip2_hash, "qc_report": "生产数据/pilot_qc_Clip02.json"},
        ],
        "coverage": ["face", "scene", "action", "lipsync", "seam", "routing"],
        "checks": {"face": "pass", "scene": "pass", "action": "pass", "lipsync": "pass", "seam": "pass", "routing": "pass"},
    })
    image_rel = f"出图/{episode}/图片/Clip01.png"
    image = root / image_rel
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(b"png")
    fp = artifact_fingerprint(str(root), [image_rel])
    _write_json(root / "生产数据" / "image_qc" / episode / f"image_qc_{episode}.json", {
        "kind": "n2d_image_qc",
        "version": 1,
        "status": "pass",
        "qc_environment": {"precision_level": "full"},
        "summary": {"hard_blocks": 0, "verdict": "pass"},
        "inputs_fingerprint": fp,
    })


def test_release_verdict_internal_only_when_all_components_pass(tmp_path: Path) -> None:
    _release_ready_project(tmp_path)

    payload = release_verdict.build_verdict(tmp_path, "第1集")

    assert payload["status"] == "internal-only"
    assert payload["summary"]["block"] == 0
    assert {c["name"]: c["status"] for c in payload["components"]}["image_qc"] == "pass"
    assert {c["name"]: c["status"] for c in payload["components"]}["pilot_release_gate"] == "pass"


def test_release_verdict_blocks_stale_image_qc(tmp_path: Path) -> None:
    _release_ready_project(tmp_path)
    (tmp_path / "出图" / "第1集" / "图片" / "Clip01.png").write_bytes(b"changed")

    payload = release_verdict.build_verdict(tmp_path, "第1集")

    assert payload["status"] == "blocked"
    image_qc = next(c for c in payload["components"] if c["name"] == "image_qc")
    assert image_qc["status"] == "block"
    assert "stale" in image_qc["message"]


def test_release_verdict_blocks_missing_production_handoff(tmp_path: Path) -> None:
    _release_ready_project(tmp_path)
    (tmp_path / "脚本" / "第1集" / "production_breakdown.json").unlink()

    payload = release_verdict.build_verdict(tmp_path, "第1集")

    assert payload["status"] == "blocked"
    handoff = next(c for c in payload["components"] if c["name"] == "production_handoff")
    assert handoff["status"] == "block"
    assert "P-3" in handoff["message"]


def test_release_verdict_blocks_missing_pilot_acceptance(tmp_path: Path) -> None:
    _release_ready_project(tmp_path)
    (tmp_path / "生产数据" / "pilot_acceptance_第1集.json").unlink()

    payload = release_verdict.build_verdict(tmp_path, "第1集")

    assert payload["status"] == "blocked"
    pilot = next(c for c in payload["components"] if c["name"] == "pilot_release_gate")
    assert pilot["status"] == "block"
    assert "pilot_acceptance" in pilot["message"]


def test_release_verdict_blocks_release_evidence_older_than_master(tmp_path: Path) -> None:
    _release_ready_project(tmp_path)
    master = tmp_path / "合成" / "第1集" / "成片_第1集_zh.mp4"
    master.parent.mkdir(parents=True, exist_ok=True)
    master.write_bytes(b"new master")
    future = time.time() + 5
    os.utime(master, (future, future))

    payload = release_verdict.build_verdict(tmp_path, "第1集")

    assert payload["status"] == "blocked"
    freshness = next(c for c in payload["components"] if c["name"] == "release_evidence_freshness")
    assert freshness["status"] == "block"
    assert "母版" in freshness["message"]


def test_release_verdict_blocks_missing_final_master(tmp_path: Path) -> None:
    _release_ready_project(tmp_path)
    for path in (tmp_path / "合成" / "第1集").glob("*.mp4"):
        path.unlink()

    payload = release_verdict.build_verdict(tmp_path, "第1集")

    assert payload["status"] == "blocked"
    master = next(c for c in payload["components"] if c["name"] == "final_master")
    assert master["status"] == "block"


def test_release_verdict_blocks_incomplete_pilot_evidence(tmp_path: Path) -> None:
    _release_ready_project(tmp_path)
    path = tmp_path / "生产数据" / "pilot_acceptance_第1集.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["clips"][0].pop("artifact_sha256")
    _write_json(path, data)

    payload = release_verdict.build_verdict(tmp_path, "第1集")

    pilot = next(c for c in payload["components"] if c["name"] == "pilot_release_gate")
    assert pilot["status"] == "block"
    assert "evidence_issues" in pilot["message"]
