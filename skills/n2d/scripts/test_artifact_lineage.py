from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("artifact_lineage.py")
spec = importlib.util.spec_from_file_location("artifact_lineage", SCRIPT)
artifact_lineage = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(artifact_lineage)


def _evidence(root: Path, episode: str) -> Path:
    (root / "_设置.md").write_text("- 制作模式: 配音先行\n", encoding="utf-8")
    (root / "_进度.md").write_text("| 集 | 成片 |\n|---|---|\n| 第1集 | ✅ |\n", encoding="utf-8")
    script_dir = root / "脚本" / episode
    script_dir.mkdir(parents=True)
    (script_dir / "storyboard.json").write_text('{"clips":[]}', encoding="utf-8")
    comp = root / "合规"
    comp.mkdir()
    (comp / "compliance_manifest.json").write_text('{"kind":"n2d_compliance_manifest","version":1}', encoding="utf-8")
    prod = root / "生产数据"
    prod.mkdir()
    (prod / "production_events_audit.json").write_text('{"status":"pass","hash_chain_head":"abc"}', encoding="utf-8")
    (prod / "artifact_validation.json").write_text(
        json.dumps({"kind": "n2d_artifact_validation", "version": 1, "root": str(root), "summary": {}, "checked": [], "issues": []}),
        encoding="utf-8",
    )
    (prod / f"generation_recipe_manifest_{episode}.json").write_text(
        json.dumps({"kind": "n2d_generation_recipe_manifest", "version": 1, "root": str(root), "episode": episode, "records": [], "summary": {}, "status": "pass"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (prod / f"gate_policy_coverage_{episode}.json").write_text(
        json.dumps({"kind": "n2d_gate_policy_coverage", "version": 1, "root": str(root), "episode": episode, "matrix": {}, "groups": [], "summary": {}, "status": "pass"}, ensure_ascii=False),
        encoding="utf-8",
    )
    asset = root / "合成" / episode / f"成片_{episode}_zh.mp4"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"mp4")
    return asset


def test_artifact_lineage_build_write_check(tmp_path: Path) -> None:
    episode = "第1集"
    _evidence(tmp_path, episode)

    payload = artifact_lineage.build_lineage(tmp_path, episode)
    path = artifact_lineage.write_lineage(tmp_path, episode, payload)

    assert payload["status"] == "pass"
    assert payload["lineage_id"]
    assert path.is_file()
    assert artifact_lineage.check_lineage(tmp_path, episode)["status"] == "pass"


def test_artifact_lineage_check_detects_hash_mismatch(tmp_path: Path) -> None:
    episode = "第1集"
    asset = _evidence(tmp_path, episode)
    payload = artifact_lineage.build_lineage(tmp_path, episode)
    artifact_lineage.write_lineage(tmp_path, episode, payload)

    asset.write_bytes(b"changed")

    result = artifact_lineage.check_lineage(tmp_path, episode)
    assert result["status"] == "fail"
    assert any("sha256 mismatch" in item for item in result["issues"])
