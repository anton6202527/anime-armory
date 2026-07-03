from __future__ import annotations

import importlib.util
import json
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


def _release_ready_project(root: Path, episode: str = "第1集") -> None:
    (root / "_设置.md").write_text("- 制作模式: 配音先行\n", encoding="utf-8")
    (root / "_进度.md").write_text(f"""# demo

| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 奇观连续性 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 | 验收 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| {episode} | 100 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
""", encoding="utf-8")
    _write_json(root / "合规" / "compliance_manifest.json", {"kind": "n2d_compliance_manifest", "version": 1, "distribution_intent": "internal_only"})
    _write_json(root / "生产数据" / f"gate_findings_review_{episode}.json", {"kind": "n2d_gate_findings", "version": 1, "findings": [], "summary": {"severity": {"block": 0, "warn": 0}}})
    _write_json(root / "生产数据" / f"score_{episode}.json", {"kind": "n2d_episode_review_score", "version": 1, "status": "pass", "score": 91, "threshold": 80})
    _write_json(root / "生产数据" / f"consistency_ledger_{episode}.json", {"kind": "n2d_consistency_ledger", "version": 1, "status": "pass", "delivery_surface": {"status": "pass"}, "counts": {"block": 0, "high": 0}})
    _write_json(root / "生产数据" / f"review_ui_{episode}.json", {"kind": "n2d_review_ui", "version": 1, "status": "pass"})
    _write_json(root / "生产数据" / f"review_ui_findings_{episode}.json", {"kind": "n2d_consistency_findings", "version": 1, "episode": episode, "findings": []})
    _write_json(root / "生产数据" / f"generation_recipe_manifest_{episode}.json", {"kind": "n2d_generation_recipe_manifest", "version": 1, "status": "pass", "records": [], "summary": {}, "root": str(root), "episode": episode})
    _write_json(root / "生产数据" / f"pilot_acceptance_{episode}.json", {
        "kind": "n2d_pilot_acceptance",
        "version": 1,
        "episode": episode,
        "status": "accepted",
        "clips": [{"clip": "EP01_CLIP01"}, {"clip": "EP01_CLIP02"}],
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


def test_release_verdict_blocks_stale_image_qc(tmp_path: Path) -> None:
    _release_ready_project(tmp_path)
    (tmp_path / "出图" / "第1集" / "图片" / "Clip01.png").write_bytes(b"changed")

    payload = release_verdict.build_verdict(tmp_path, "第1集")

    assert payload["status"] == "blocked"
    image_qc = next(c for c in payload["components"] if c["name"] == "image_qc")
    assert image_qc["status"] == "block"
    assert "stale" in image_qc["message"]
