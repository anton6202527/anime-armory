from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("release_manifest.py")
spec = importlib.util.spec_from_file_location("release_manifest", SCRIPT)
release_manifest = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(release_manifest)

compliance = release_manifest.compliance


def _write_internal_compliance(root: Path, episode: str) -> None:
    data = compliance.default_manifest(root, episode)
    data["distribution_intent"] = "internal_only"
    path = compliance.manifest_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_release_evidence(root: Path, episode: str) -> None:
    (root / "_设置.md").write_text("- 制作模式: 配音先行\n", encoding="utf-8")
    (root / "_进度.md").write_text("| 集 | 成片 | 验收 |\n|---|---|---|\n| 第1集 | ✅ | ✅ |\n", encoding="utf-8")
    script_dir = root / "脚本" / episode
    script_dir.mkdir(parents=True, exist_ok=True)
    (script_dir / "storyboard.json").write_text('{"kind":"storyboard","clips":[]}', encoding="utf-8")
    pdir = root / "生产数据"
    pdir.mkdir(exist_ok=True)
    (pdir / "production_events_audit.json").write_text(
        json.dumps({"status": "pass", "event_count": 1, "hash_chain_head": "abc", "strict_trace": True}, ensure_ascii=False),
        encoding="utf-8",
    )
    (pdir / "artifact_validation.json").write_text(
        json.dumps({"kind": "n2d_artifact_validation", "version": 1, "root": str(root), "summary": {}, "checked": [], "issues": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    (pdir / f"generation_recipe_manifest_{episode}.json").write_text(
        json.dumps({"kind": "n2d_generation_recipe_manifest", "version": 1, "root": str(root), "episode": episode, "records": [], "summary": {}, "status": "pass"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (pdir / f"gate_policy_coverage_{episode}.json").write_text(
        json.dumps({"kind": "n2d_gate_policy_coverage", "version": 1, "root": str(root), "episode": episode, "matrix": {}, "groups": [], "summary": {}, "status": "pass"}, ensure_ascii=False),
        encoding="utf-8",
    )


def test_build_release_manifest_ready_with_asset_and_signoff(tmp_path: Path) -> None:
    episode = "第1集"
    _write_internal_compliance(tmp_path, episode)
    _write_release_evidence(tmp_path, episode)
    asset = tmp_path / "合成" / episode / f"成片_{episode}_zh.mp4"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"mp4-master")
    pdir = tmp_path / "生产数据"
    pdir.mkdir(exist_ok=True)
    (pdir / f"review_signoff_{episode}.json").write_text(
        json.dumps({"status": "approved", "reviewer": "human"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (pdir / f"score_{episode}.json").write_text(
        json.dumps({"status": "pass", "score": 91, "threshold": 85}, ensure_ascii=False),
        encoding="utf-8",
    )

    payload = release_manifest.build_manifest(tmp_path, episode)
    path = release_manifest.write_manifest(tmp_path, episode, payload)

    assert payload["readiness"]["status"] == "ready"
    assert payload["asset"]["sha256"]
    assert payload["review"]["signoff"]["available"] is True
    assert payload["provenance"]["artifact_lineage"]["path"]
    assert payload["transparency"]["strict"] is False
    assert payload["transparency"]["machine_readable_present"] is False
    assert payload["readiness"]["status"] == "ready"  # internal_only: transparency gaps are publish todos
    assert path.is_file()
    assert (tmp_path / "生产数据" / f"artifact_lineage_{episode}.json").is_file()
    assert release_manifest.check_manifest(tmp_path, episode)["status"] == "pass"


def test_release_manifest_check_detects_asset_hash_mismatch(tmp_path: Path) -> None:
    episode = "第1集"
    _write_internal_compliance(tmp_path, episode)
    _write_release_evidence(tmp_path, episode)
    asset = tmp_path / "合成" / episode / f"成片_{episode}_zh.mp4"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"v1")
    pdir = tmp_path / "生产数据"
    pdir.mkdir(exist_ok=True)
    (pdir / f"review_signoff_{episode}.json").write_text('{"status":"approved","reviewer":"human"}', encoding="utf-8")
    payload = release_manifest.build_manifest(tmp_path, episode)
    release_manifest.write_manifest(tmp_path, episode, payload)

    asset.write_bytes(b"v2")
    result = release_manifest.check_manifest(tmp_path, episode)

    assert result["status"] == "fail"
    assert "asset sha256 mismatch" in result["issues"]


def test_release_manifest_blocks_gate_findings_and_missing_signoff(tmp_path: Path) -> None:
    episode = "第1集"
    _write_internal_compliance(tmp_path, episode)
    _write_release_evidence(tmp_path, episode)
    asset = tmp_path / "合成" / episode / f"成片_{episode}_zh.mp4"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"mp4-master")
    pdir = tmp_path / "生产数据"
    pdir.mkdir(exist_ok=True)
    (pdir / f"gate_findings_review_{episode}.json").write_text(
        json.dumps({
            "kind": "n2d_consistency_findings",
            "findings": [{"severity": "block", "dimension": "角色一致性", "message": "脸漂"}],
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    payload = release_manifest.build_manifest(tmp_path, episode)

    assert payload["readiness"]["status"] == "blocked"
    assert any("missing human review signoff" in item for item in payload["readiness"]["blocks"])
    assert any("gate block" in item for item in payload["readiness"]["blocks"])


def test_transparency_blocks_paid_release_without_labels(tmp_path: Path) -> None:
    episode = "第1集"
    data = compliance.default_manifest(tmp_path, episode)
    data["distribution_intent"] = "paid_distribution"

    summary = release_manifest.transparency_summary(tmp_path, episode, data, stage="release")

    assert summary["strict"] is True
    assert any("显式标识" in item for item in summary["blocks"])
    assert any("机器可读" in item for item in summary["blocks"])


def test_transparency_accepts_label_and_c2pa_manifest(tmp_path: Path) -> None:
    episode = "第1集"
    data = compliance.default_manifest(tmp_path, episode)
    data["distribution_intent"] = "paid_distribution"
    data["ai_labeling"]["explicit_label"]["status"] = "done"
    data["ai_labeling"]["implicit_metadata"]["applied"] = False
    c2pa = tmp_path / "合规" / "c2pa_manifest.json"
    c2pa.parent.mkdir(parents=True)
    c2pa.write_text('{"kind":"c2pa"}', encoding="utf-8")
    data["ai_labeling"]["implicit_metadata"]["c2pa_manifest"] = "合规/c2pa_manifest.json"

    summary = release_manifest.transparency_summary(tmp_path, episode, data, stage="release")

    assert summary["machine_readable_present"] is True
    assert summary["content_credentials"]["status"] == "present"
    assert summary["blocks"] == []


def test_platform_checklist_blocks_paid_target_missing_delivery_assets(tmp_path: Path) -> None:
    episode = "第1集"
    data = compliance.default_manifest(tmp_path, episode)
    data["distribution_intent"] = "paid_distribution"
    data["platform_review"]["targets"] = [{"platform": "TikTok", "region": "US", "language": "en"}]
    data["ai_labeling"]["explicit_label"]["status"] = "done"
    data["ai_labeling"]["implicit_metadata"]["applied"] = True
    data["ai_labeling"]["platform_disclosure"] = {"status": "done"}
    transparency = release_manifest.transparency_summary(tmp_path, episode, data, stage="release")

    checklist = release_manifest.platform_release_checklist(
        tmp_path,
        episode,
        data,
        transparency,
        [],
        stage="release",
    )

    assert checklist["strict"] is True
    assert checklist["targets"][0]["platform"] == "tiktok"
    assert {"subtitle", "cover"} <= set(checklist["targets"][0]["missing"])
    assert any("platform checklist tiktok missing" in item for item in checklist["blocks"])


def test_platform_checklist_accepts_required_delivery_evidence(tmp_path: Path) -> None:
    episode = "第1集"
    (tmp_path / "脚本" / episode).mkdir(parents=True)
    (tmp_path / "脚本" / episode / "字幕_中文.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\n字幕\n", encoding="utf-8")
    (tmp_path / "合成" / episode).mkdir(parents=True)
    (tmp_path / "合成" / episode / "cover.jpg").write_bytes(b"jpg")
    data = compliance.default_manifest(tmp_path, episode)
    data["distribution_intent"] = "paid_distribution"
    data["platform_review"]["targets"] = [{"platform": "YouTube", "region": "US", "language": "en"}]
    data["ai_labeling"]["explicit_label"]["status"] = "done"
    data["ai_labeling"]["implicit_metadata"]["applied"] = True
    data["ai_labeling"]["platform_disclosure"] = {"status": "done"}
    transparency = release_manifest.transparency_summary(tmp_path, episode, data, stage="release")

    checklist = release_manifest.platform_release_checklist(
        tmp_path,
        episode,
        data,
        transparency,
        [],
        stage="release",
    )

    assert checklist["targets"][0]["platform"] == "youtube"
    assert checklist["targets"][0]["missing"] == []
    assert checklist["blocks"] == []


def test_release_manifest_rejects_rubber_stamp_signoff(tmp_path: Path) -> None:
    """空签收/无 reviewer 的橡皮图章不得清掉人审 block（证声明不证现实）。"""
    episode = "第1集"
    _write_internal_compliance(tmp_path, episode)
    _write_release_evidence(tmp_path, episode)
    asset = tmp_path / "合成" / episode / f"成片_{episode}_zh.mp4"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"mp4-master")
    pdir = tmp_path / "生产数据"
    pdir.mkdir(exist_ok=True)
    # 文件存在但缺 reviewer + 缺真实结论
    (pdir / f"review_signoff_{episode}.json").write_text("{}", encoding="utf-8")

    payload = release_manifest.build_manifest(tmp_path, episode)

    assert payload["readiness"]["status"] == "blocked"
    assert payload["review"]["signoff"]["available"] is True
    assert payload["review"]["signoff"]["valid"] is False
    assert any("signoff invalid" in item for item in payload["readiness"]["blocks"])


def test_release_manifest_accepts_signoff_with_reviewer_and_decision(tmp_path: Path) -> None:
    episode = "第1集"
    _write_internal_compliance(tmp_path, episode)
    _write_release_evidence(tmp_path, episode)
    asset = tmp_path / "合成" / episode / f"成片_{episode}_zh.mp4"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"mp4-master")
    pdir = tmp_path / "生产数据"
    pdir.mkdir(exist_ok=True)
    (pdir / f"review_signoff_{episode}.json").write_text(
        json.dumps({"reviewer": "张三", "decision": "approved"}, ensure_ascii=False), encoding="utf-8"
    )

    signoff = release_manifest.review_signoff(tmp_path, episode)
    assert signoff["valid"] is True
    assert signoff["reviewer"] == "张三"


def test_release_manifest_blocks_stale_gate_findings(tmp_path: Path) -> None:
    """带输入指纹的 gate_findings，若产物在 gate 之后被改，则缓存判定失效 → 阻断。"""
    import importlib.util as _ilu

    dashboard_path = (
        Path(release_manifest.__file__).resolve().parent.parent
        / "n2d-dashboard" / "scripts" / "dashboard.py"
    )
    _spec = _ilu.spec_from_file_location("n2d_dashboard_for_test", dashboard_path)
    dashboard = _ilu.module_from_spec(_spec)
    assert _spec.loader is not None
    _spec.loader.exec_module(dashboard)

    episode = "第1集"
    _write_internal_compliance(tmp_path, episode)
    _write_release_evidence(tmp_path, episode)
    asset = tmp_path / "合成" / episode / f"成片_{episode}_zh.mp4"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"mp4-master")
    pdir = tmp_path / "生产数据"
    pdir.mkdir(exist_ok=True)
    (pdir / f"review_signoff_{episode}.json").write_text(
        json.dumps({"reviewer": "张三", "decision": "approved"}, ensure_ascii=False), encoding="utf-8"
    )

    # 写一份带输入指纹的 clean gate findings（覆盖 storyboard.json）
    dashboard.write_gate_findings(str(tmp_path), episode, "review", [])
    fresh = release_manifest.gate_findings_freshness(tmp_path, episode)
    assert fresh["stale"] == []

    # 改 storyboard → 指纹失配 → stale
    (tmp_path / "脚本" / episode / "storyboard.json").write_text(
        '{"kind":"storyboard","clips":[{"id":"C1"}]}', encoding="utf-8"
    )
    fresh2 = release_manifest.gate_findings_freshness(tmp_path, episode)
    assert fresh2["stale"], "storyboard 改动后 gate findings 应判为 stale"

    payload = release_manifest.build_manifest(tmp_path, episode)
    assert payload["readiness"]["status"] == "blocked"
    assert any("gate findings stale" in item for item in payload["readiness"]["blocks"])
