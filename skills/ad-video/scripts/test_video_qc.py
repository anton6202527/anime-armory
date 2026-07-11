import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_qc as vq  # noqa: E402


def _project(tmp_path: Path, *, route_cap="subject_consistency", prompt=True, video=True) -> Path:
    root = tmp_path / "广告项目"
    (root / "脚本").mkdir(parents=True)
    (root / "出视频" / "分镜" / "prompt").mkdir(parents=True)
    (root / "出视频" / "分镜" / "视频").mkdir(parents=True)
    (root / "脚本" / "storyboard.json").write_text(json.dumps({
        "clips": [
            {"id": "C01", "duration": 4, "scene": "产品 hero", "shot": "产品界面特写",
             "assets": {"PROD_STARBOX_APP": True, "BRAND_STARBOX": True},
             "safe_area": {"core_in_center_4x4": True}},
            {"id": "C02", "duration": 3, "scene": "片尾", "shot": "CTA end card",
             "assets": {"BRAND_STARBOX": True}, "safe_area": {"core_in_center_4x4": True}},
        ]
    }, ensure_ascii=False), encoding="utf-8")
    routes = {
        "kind": "ad_video_model_routes",
        "routes": [
            {"clip": "镜头01", "capability": route_cap, "primary": "seedance", "prod_assets": ["PROD_STARBOX_APP"]},
            {"clip": "镜头02", "capability": "still", "primary": "seedance", "prod_assets": []},
        ],
        "summary": {"block": 0, "warn": 0},
    }
    (root / "出视频" / "分镜" / "prompt" / "video_model_routes.json").write_text(
        json.dumps(routes, ensure_ascii=False), encoding="utf-8")
    if prompt:
        (root / "出视频" / "分镜" / "prompt" / "镜头01.md").write_text(
            "资产引用：PROD_STARBOX_APP；与产品参考图①同一包装、同一 logo、同一品牌色；文字清晰可读。",
            encoding="utf-8")
        (root / "出视频" / "分镜" / "prompt" / "镜头02.md").write_text(
            "片尾 end card，BRAND_STARBOX，CTA 立即预约内测，文字清晰可读。",
            encoding="utf-8")
    if video:
        (root / "出视频" / "分镜" / "视频" / "镜头01.mp4").write_bytes(b"fake-video")
        (root / "出视频" / "分镜" / "视频" / "镜头02.mp4").write_bytes(b"fake-video")
    (root / "出视频" / "分镜" / "contract_inheritance.json").write_text(
        json.dumps({"summary": {"block": 0, "warn": 0}}, ensure_ascii=False), encoding="utf-8")
    return root


def test_video_qc_passes_measured_product_clip(tmp_path, monkeypatch):
    root = _project(tmp_path)
    monkeypatch.setattr(vq, "_probe", lambda path: {
        "streams": [{"codec_type": "video", "width": 1280, "height": 720}],
        "format": {"duration": "4" if "01" in path.stem else "3"},
    })

    def fake_extract(video, at, out):
        Image, _ = vq._load_imaging()
        if Image is None:
            return False
        out.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (32, 18), (20, 20, 20)).save(out)
        return True

    monkeypatch.setattr(vq, "_extract_frame", fake_extract)
    payload = vq.run_qc(root)

    assert payload["kind"] == vq.KIND
    assert payload["summary"]["block"] == 0
    assert Path(root / "出视频" / "分镜" / "video_qc.json").is_file()


def test_video_qc_blocks_missing_clip(tmp_path):
    root = _project(tmp_path, video=False)
    payload = vq.run_qc(root)

    assert payload["summary"]["block"] >= 1
    assert any(f["check"] == "clip_presence" for f in payload["findings"])


def test_video_qc_reports_pending_submit_id_for_missing_clip(tmp_path):
    root = _project(tmp_path, video=False)
    (root / "出视频" / "分镜" / "video_jobs_manifest.json").write_text(json.dumps({
        "jobs": [{
            "clip": "镜头01",
            "status": "submitted",
            "pending_status": "querying",
            "submit_id": "sub_123",
            "expected_output": "出视频/分镜/视频/镜头01.mp4",
        }]
    }, ensure_ascii=False), encoding="utf-8")
    payload = vq.run_qc(root)

    pending = [f for f in payload["findings"] if f["clip"] == "镜头01" and f["check"] == "clip_presence"]
    assert pending
    assert pending[0]["detail"]["submit_id"] == "sub_123"


def test_video_qc_blocks_product_route_without_subject_lock(tmp_path):
    root = _project(tmp_path, route_cap="general")
    payload = vq.run_qc(root)

    assert any(f["check"] == "route_subject_lock" and f["severity"] == "block" for f in payload["findings"])


def test_video_qc_blocks_product_prompt_without_lock(tmp_path):
    root = _project(tmp_path)
    (root / "出视频" / "分镜" / "prompt" / "镜头01.md").write_text("环绕推近，暖光。", encoding="utf-8")
    payload = vq.run_qc(root)

    assert any(f["check"] == "prompt_product_lock" and f["severity"] == "block" for f in payload["findings"])


def test_asset_regex_does_not_match_plain_product_or_brand_words():
    shot = {"prompt": "product interface with brand color but no structured IDs"}

    assert vq.prod_assets(shot) == set()
    assert vq.brand_assets(shot) == set()
