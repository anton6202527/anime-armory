import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import platform_pack as pp  # noqa: E402


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "广告项目"
    (root / "需求").mkdir(parents=True)
    (root / "需求" / "brief.json").write_text(json.dumps({
        "platforms": ["抖音", "小红书"],
        "deliverables": {"master_duration": "30s", "aspect": "9:16", "cutdowns": ["15s", "6s"]},
    }, ensure_ascii=False), encoding="utf-8")
    (root / "_设置.md").write_text("- 目标平台: 跨平台\n- 主片时长: 30s\n", encoding="utf-8")
    return root


def test_build_pack_includes_platform_specs_and_deliverables(tmp_path):
    root = _project(tmp_path)
    pack = pp.build_pack(root)

    assert pack["summary"]["platform_count"] == 2
    assert pack["summary"]["deliverable_count"] == 3
    assert pack["specs"]["抖音"]["safe_area"] == "placement_overlay_aware"
    assert [row["deliverable_id"] for row in pack["deliverables"]] == ["master", "cut_15s", "cut_6s"]
    assert any(f["code"] == "placement_missing" for f in pack["findings"])


def test_write_pack_outputs_json(tmp_path):
    root = _project(tmp_path)
    pack = pp.write_pack(root)

    path = Path(pack["_json_path"])
    assert path.is_file()
    disk = json.loads(path.read_text(encoding="utf-8"))
    assert disk["kind"] == pp.KIND


def test_unknown_platform_blocks_until_current_spec_is_bound(tmp_path):
    root = tmp_path / "广告项目"
    (root / "需求").mkdir(parents=True)
    (root / "需求" / "brief.json").write_text(json.dumps({"platforms": ["新平台"]}, ensure_ascii=False), encoding="utf-8")

    pack = pp.build_pack(root)

    assert pack["summary"]["block"] >= 1
    assert pack["specs"]["新平台"]["platform_key"] == "manual"


def test_safe_zone_evidence_closes_known_platform_release_warning(tmp_path):
    root = _project(tmp_path)
    brief_path = root / "需求" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["platform_safe_zone_evidence"] = {"抖音": "合规/douyin-safe.png", "小红书": "合规/xhs-safe.png"}
    brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    (root / "合规").mkdir()
    (root / "合规" / "douyin-safe.png").write_bytes(b"template")
    (root / "合规" / "xhs-safe.png").write_bytes(b"template")

    pack = pp.build_pack(root)

    assert not any(f["code"] == "safe_zone_asset_pending" for f in pack["findings"])
    assert not any(f["code"] == "safe_zone_evidence_missing" for f in pack["findings"])


def test_declared_safe_zone_file_must_exist(tmp_path):
    root = _project(tmp_path)
    brief_path = root / "需求" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["platform_safe_zone_evidence"] = {"抖音": "合规/missing.png"}
    brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    pack = pp.build_pack(root)
    assert any(f["code"] == "safe_zone_evidence_missing" for f in pack["findings"])


def test_current_official_tiktok_youtube_meta_specs_are_provenanced(tmp_path):
    for name in ("TikTok", "YouTube", "Instagram Reels", "Facebook Reels"):
        spec = pp.spec_for(name)
        assert spec["authority"].startswith("official_platform")
        assert spec["checked_at"] == "2026-08-20"
        assert str(spec["source"]).startswith("https://")
        assert spec["safe_zone_asset"] == "download_current_official_template"
    assert pp.spec_for("TikTok")["min_resolution"] == "540x960"
    assert pp.spec_for("TikTok")["min_bitrate_bps"] == 516000


def test_custom_platform_spec_requires_provenance(tmp_path):
    root = tmp_path / "广告项目"
    (root / "需求").mkdir(parents=True)
    (root / "需求" / "brief.json").write_text(json.dumps({
        "platforms": ["客户私域"],
        "platform_specs": {"客户私域": {"aspect": "9:16", "safe_area": "client_template"}},
    }, ensure_ascii=False), encoding="utf-8")

    pack = pp.build_pack(root)

    assert pack["summary"]["block"] >= 1
    assert any(f["code"] == "custom_platform_provenance_missing" for f in pack["findings"])


def test_platform_spec_age_is_machine_checkable():
    assert pp.spec_age_days("2026-07-01", date(2026, 7, 11)) == 10
    assert pp.spec_age_days("not-a-date", date(2026, 7, 11)) is None


def test_placement_is_first_class_and_uses_exact_safe_zone_evidence(tmp_path):
    root = tmp_path / "广告项目"
    (root / "需求").mkdir(parents=True)
    (root / "合规").mkdir()
    (root / "合规" / "tt-feed.png").write_bytes(b"template")
    (root / "需求" / "brief.json").write_text(json.dumps({
        "platforms": ["TikTok"],
        "placements": ["TikTok:auction_in_feed"],
        "platform_safe_zone_evidence": {"TikTok:auction_in_feed": "合规/tt-feed.png"},
    }, ensure_ascii=False), encoding="utf-8")
    pack = pp.build_pack(root)
    assert pack["summary"]["placement_count"] == 1
    spec = pack["placement_specs"]["TikTok:auction_in_feed"]
    assert spec["safe_zone_evidence_scope"] == "placement"
    assert not any(f["code"] in {"placement_missing", "safe_zone_asset_pending"} for f in pack["findings"])


def test_unknown_placement_blocks_until_custom_provenance_is_bound(tmp_path):
    root = tmp_path / "广告项目"
    (root / "需求").mkdir(parents=True)
    (root / "需求" / "brief.json").write_text(json.dumps({
        "platforms": ["YouTube"], "placements": ["YouTube:new_surface"],
    }), encoding="utf-8")
    pack = pp.build_pack(root)
    assert any(f["code"] == "placement_spec_missing" and f["severity"] == "block" for f in pack["findings"])


def test_current_demand_gen_profile_includes_4x5_and_duration_eligibility():
    spec = pp.spec_for_placement("YouTube", "demand_gen")
    assert "4:5" in spec["allowed_aspects"]
    assert spec["min_duration_seconds"] == 5
    assert spec["in_stream_eligible_min_duration_seconds"] == 10


def test_multiple_placements_require_deliverable_mapping(tmp_path):
    root = tmp_path / "广告项目"
    (root / "需求").mkdir(parents=True)
    (root / "需求" / "brief.json").write_text(json.dumps({
        "platforms": ["TikTok", "YouTube"],
        "placements": ["TikTok:auction_in_feed", "YouTube:in_stream"],
    }), encoding="utf-8")
    pack = pp.build_pack(root)
    assert any(f["code"] == "deliverable_placement_mapping_missing" and f["severity"] == "block"
               for f in pack["findings"])
