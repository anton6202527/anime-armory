# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_profile as rp  # noqa: E402


def _project(tmp_path: Path, settings: str, brief=None) -> Path:
    root = tmp_path / "广告项目"
    (root / "需求").mkdir(parents=True)
    (root / "_设置.md").write_text(settings, encoding="utf-8")
    (root / "需求" / "brief.json").write_text(
        json.dumps(brief or {}, ensure_ascii=False), encoding="utf-8")
    return root


def test_default_source_passes_through_without_fake_1080_upscale(tmp_path):
    root = _project(tmp_path, "- 出视频规格: 预算一般\n- 视频分辨率: 720p\n- 交付比例: 16:9\n")

    profile = rp.compile_profile(root)

    assert profile["source_generation"]["resolution"] == "1280x720"
    assert profile["source_generation"]["fps"] == 24
    assert profile["master_render"]["resolution"] == "1280x720"
    assert profile["master_render"]["fps"] == 24
    assert profile["upscale"]["required"] is False
    assert profile["authority"]["precedence"][0] == "brief.render_profile"
    assert profile["summary"]["block"] == 0


def test_1080_and_4k_choices_are_oriented_to_project_aspect(tmp_path):
    portrait = _project(tmp_path / "portrait", "- 出视频规格: 预算充足\n- 视频分辨率: 1080p\n- 交付比例: 9:16\n")
    p = rp.compile_profile(portrait)
    assert (p["source_generation"]["width"], p["source_generation"]["height"]) == (1080, 1920)
    assert p["source_generation"]["fps"] == 30

    uhd = _project(tmp_path / "uhd", "- 出视频规格: 预算充足\n- 视频分辨率: 4K\n- 交付比例: 16:9\n")
    p4k = rp.compile_profile(uhd)
    assert p4k["source_generation"]["resolution"] == "3840x2160"
    assert p4k["source_generation"]["backend_request_resolution"] == "4K"

    four_five = rp.parse_resolution("1080p", "4:5")
    square = rp.parse_resolution("1080p", "1:1")
    assert (four_five["width"], four_five["height"]) == (1080, 1350)
    assert (square["width"], square["height"]) == (1080, 1080)


def test_shorts_recommendation_is_explicit_container_upscale_not_native_claim(tmp_path):
    root = _project(
        tmp_path,
        "- 出视频规格: 预算一般\n- 视频分辨率: 720p\n- 交付比例: 9:16\n",
        {
            "deliverables": {"aspect": "9:16", "master_duration": "15s"},
            "platforms": ["YouTube"],
            "placements": ["YouTube:shorts"],
        },
    )

    profile = rp.compile_profile(root)

    assert profile["master_render"]["resolution"] == "1080x1920"
    assert profile["upscale"]["effective_source_resolution"] == "720x1280"
    assert profile["upscale"]["quality_claim"] == "container_upscale_only"
    finding = next(row for row in profile["findings"] if row["code"] == "container_upscale_only")
    assert finding["severity"] == "warn"
    assert profile["summary"]["block"] == 0
    assert profile["master_render"]["authority"][0]["source"].startswith("https://support.google.com/")


def test_evidenced_custom_master_may_stay_below_platform_recommendation(tmp_path):
    root = _project(
        tmp_path,
        "- 出视频规格: 预算一般\n- 视频分辨率: 720p\n- 交付比例: 9:16\n",
        {
            "deliverables": {"aspect": "9:16"},
            "platforms": ["YouTube"], "placements": ["YouTube:shorts"],
            "render_profile": {
                "source_generation": {"resolution": "720p", "fps": 24},
                "master_render": {"resolution": "720x1280", "fps": 24},
                "source": "客户批准的投放规格.pdf", "approved_by": "客户制片人",
            },
        },
    )
    profile = rp.compile_profile(root)
    assert profile["master_render"]["resolution"] == "720x1280"
    assert profile["summary"]["block"] == 0
    assert any(row["code"] == "custom_master_below_delivery_recommendation"
               and row["severity"] == "warn" for row in profile["findings"])


def test_custom_native_placement_blocks_source_below_native_requirement(tmp_path):
    root = _project(
        tmp_path,
        "- 出视频规格: 预算一般\n- 视频分辨率: 720p\n- 交付比例: 16:9\n",
        {
            "deliverables": {"aspect": "16:9"},
            "platforms": ["客户播出系统"],
            "placements": ["客户播出系统:大屏"],
            "placement_specs": {
                "客户播出系统:大屏": {
                    "aspect": "16:9",
                    "required_resolution": "1920x1080",
                    "native_resolution_required": True,
                    "safe_area": "none",
                    "source": "客户交付规范.pdf",
                    "checked_at": "2026-08-20",
                    "authority": "client_written_spec",
                }
            },
        },
    )

    profile = rp.compile_profile(root)

    assert profile["master_render"]["resolution"] == "1920x1080"
    assert profile["upscale"]["native_resolution_required"] is True
    assert any(row["code"] == "native_resolution_source_below_requirement"
               and row["severity"] == "block" for row in profile["findings"])


def test_custom_exact_source_and_master_fps_override_are_supported(tmp_path):
    root = _project(
        tmp_path,
        "- 出视频规格: 自定义 25fps\n- 视频分辨率: 自定义 1536x864\n- 交付比例: 16:9\n",
        {
            "deliverables": {"aspect": "16:9"},
            "render_profile": {
                "source_generation": {"resolution": "1536x864", "fps": 25},
                "master_render": {"resolution": "1536x864", "fps": 25},
                "upscale_policy": "allow",
                "source": "客户邮件 2026-08-20",
                "approved_by": "客户制片人",
            },
        },
    )

    profile = rp.write_profile(root)

    assert profile["source_generation"]["backend_request_resolution"] == "1536x864"
    assert profile["master_render"]["fps"] == 25
    assert profile["upscale"]["policy"] == "allow"
    disk = json.loads((root / rp.PROFILE_REL).read_text(encoding="utf-8"))
    assert disk["profile_sha256"] == profile["profile_sha256"]


def test_bare_custom_resolution_without_dimensions_fails_closed(tmp_path):
    root = _project(tmp_path, "- 出视频规格: 预算一般\n- 视频分辨率: 自定义\n- 交付比例: 16:9\n")
    profile = rp.compile_profile(root)
    assert any(row["code"] == "source_resolution_unadapted" and row["severity"] == "block"
               for row in profile["findings"])


def test_custom_exact_resolution_must_match_render_aspect(tmp_path):
    root = _project(tmp_path, "- 出视频规格: 自定义 25fps\n- 视频分辨率: 1024x768\n- 交付比例: 16:9\n")
    profile = rp.compile_profile(root)
    assert any(row["code"] == "source_resolution_unadapted" for row in profile["findings"])


def test_profile_sha_does_not_depend_on_platform_pack_already_being_materialised(tmp_path):
    root = _project(tmp_path, "- 出视频规格: 预算一般\n- 视频分辨率: 720p\n- 交付比例: 16:9\n")
    pack = rp.platform_pack.build_pack(root)

    first = rp.write_profile(root, pack=pack)
    assert not (root / "生产数据" / "platform_pack.json").exists()
    second = rp.write_profile(root)

    assert (root / "生产数据" / "platform_pack.json").exists()
    assert first["profile_sha256"] == second["profile_sha256"]


def test_unknown_platform_requirement_blocks_profile_instead_of_silent_fallback(tmp_path):
    root = _project(
        tmp_path,
        "- 出视频规格: 预算一般\n- 视频分辨率: 720p\n- 交付比例: 9:16\n",
        {"platforms": ["未知新平台"]},
    )
    profile = rp.compile_profile(root)
    assert any(row["code"] == "platform_spec_missing" and row["severity"] == "block"
               and row["source_component"] == "platform_pack" for row in profile["findings"])
