#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""product_qc 单测。从本目录跑：
    cd skills/ad/ad-image/scripts && python3 -m pytest test_product_qc.py
覆盖：prompt-lint block（产品镜缺参考块）/ prompt-lint pass / 品牌色 ΔE block vs pass /
summary.block → 退出码 / 降级模式（无 Pillow）仍跑 prompt-lint。
PIL 相关用例用 pytest.importorskip。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import product_qc as pq  # noqa: E402


# ── 测试夹具：搭一个最小广告项目 ─────────────────────────────────────────────────

GOOD_PROMPT = """镜头1 | 中景 | 平视 | 手持产品 | 室内 | 顺光 | 自信 | 终稿
资产引用：PROD_main（产品定妆参考组 定妆_产品.png）
品牌色：#e60012（主色出现在瓶身）
身份锁定句：与产品参考图①同一款包装、同一 logo、同一品牌色
负向：不要偏色 / 不要改包装文字 / 不要变形 logo
"""

# 缺参考块 + 缺身份锁定 + 缺负向 → 应多条 block
BAD_PROMPT = """镜头2 | 特写 | 平视 | 产品摆台 | 室内 | 顺光 | 自信 | 终稿
就是一瓶很好的产品，红色包装，背景虚化。
"""


def _make_project(tmp_path, prompts, storyboard=None, overview=None):
    root = tmp_path / "拍广告" / "项目X"
    stage = root / "出图" / "分镜"
    pdir = stage / "prompt"
    pdir.mkdir(parents=True)
    (root / "脚本").mkdir(parents=True)
    sb = storyboard if storyboard is not None else {
        "visual_contract": {"品牌色": "#E60012"},
        "shots": [
            {"shot_id": "镜头1", "assets": {"PROD_main": True}},
            {"shot_id": "镜头2", "assets": {"PROD_main": True}},
        ],
    }
    (root / "脚本" / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
    if overview is not None:
        (pdir / "00_总览.md").write_text(overview, encoding="utf-8")
    for name, text in prompts.items():
        (pdir / name).write_text(text, encoding="utf-8")
    return root, stage


# ── 纯函数：product_shots / brand_color / lint ───────────────────────────────────

def test_product_shots_detects_prod_asset():
    sb = {"shots": [
        {"shot_id": "镜头1", "assets": {"PROD_main": True}},
        {"shot_id": "镜头2", "assets": {"CHAR_a": True}},
        {"shot_id": "镜头3", "assets": {"PROD_hero": False}},
        {"shot_id": "镜头4", "product_lock": "手机屏幕显示 App 界面"},
    ]}
    assert pq.product_shots(sb) == ["镜头1", "镜头4"]


def test_brand_color_from_contract_and_overview():
    assert pq.brand_color_hex({"visual_contract": {"品牌色": "#E60012"}}) == "#e60012"
    assert pq.brand_color_hex({}, overview_text="主色 #00aaff 出现在...") == "#00aaff"
    assert pq.brand_color_hex({}) is None


def test_lint_pass_no_findings():
    assert pq.lint_product_prompt("镜头1", GOOD_PROMPT) == []


def test_lint_block_missing_reference_identity_negatives():
    f = pq.lint_product_prompt("镜头2", BAD_PROMPT)
    assert all(x["severity"] == "block" for x in f)
    codes = {x["detail"].get("missing") for x in f}
    assert "reference_block" in codes
    assert "identity_lock" in codes
    assert "product_asset_id" in codes
    # 负向缺失 finding
    assert any(x["detail"].get("missing_negatives") for x in f)


def test_lint_missing_prompt_file_blocks():
    f = pq.lint_product_prompt("镜头9", None)
    assert len(f) == 1 and f[0]["severity"] == "block"
    assert f[0]["detail"].get("missing_prompt") is True


def test_delta_e_identical_zero_and_far_large():
    assert pq.delta_e_cie76((230, 0, 18), (230, 0, 18)) == pytest.approx(0.0, abs=1e-6)
    # 红 vs 蓝 ΔE 应很大
    assert pq.delta_e_cie76((230, 0, 18), (0, 0, 255)) > 50


# ── prompt-lint 端到端：block 路径 + 退出码 ──────────────────────────────────────

def test_run_qc_writes_authoritative_json_and_block_exit(tmp_path):
    root, stage = _make_project(tmp_path, {"镜头1.md": GOOD_PROMPT, "镜头2.md": BAD_PROMPT})
    rc = pq.main([str(stage)])
    assert rc == 1  # 镜头2 多条 prompt block → 退出非零
    out = root / "出图" / "分镜" / "product_qc.json"
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert set(payload.keys()) == {"kind", "version", "summary", "findings", "qc_environment"}
    assert payload["kind"] == "ad_product_qc"
    assert set(payload["summary"].keys()) == {"block", "warn", "info"}
    assert payload["summary"]["block"] >= 1
    # 每条 finding 符合权威 schema
    for f in payload["findings"]:
        assert set(["severity", "shot", "check", "reason", "detail"]).issubset(f.keys())
        assert f["severity"] in ("block", "warn", "info")
        assert f["check"] in (
            "brand_color", "product_dhash", "logo", "prompt_lint", "local_patch_prohibited",
            "asset_binding", "text_legibility", "safe_area",
        )


def test_run_qc_all_good_prompts_no_prompt_block(tmp_path):
    # 两镜都合规 + 无图（像素检降级 info / pending）→ 不应有 prompt_lint block
    root, stage = _make_project(tmp_path, {"镜头1.md": GOOD_PROMPT, "镜头2.md": GOOD_PROMPT.replace("镜头1", "镜头2")})
    rc = pq.main([str(stage)])
    payload = json.loads((root / "出图" / "分镜" / "product_qc.json").read_text(encoding="utf-8"))
    prompt_blocks = [f for f in payload["findings"] if f["check"] == "prompt_lint" and f["severity"] == "block"]
    assert prompt_blocks == []
    assert rc == 0  # 无 block


# ── 降级模式（无 Pillow）仍跑 prompt-lint ────────────────────────────────────────

def test_degraded_no_pillow_still_lints(tmp_path, monkeypatch):
    monkeypatch.setattr(pq, "_load_imaging", lambda: (None, None))
    root, stage = _make_project(tmp_path, {"镜头1.md": GOOD_PROMPT, "镜头2.md": BAD_PROMPT})
    payload = pq.run_qc(stage)
    # 降级声明 info 存在
    assert any(f["detail"].get("degraded") == "no_pillow" for f in payload["findings"])
    # prompt-lint 仍然抓到镜头2 的 block
    assert any(f["check"] == "prompt_lint" and f["severity"] == "block" and f["shot"] == "镜头2"
               for f in payload["findings"])
    assert payload["qc_environment"]["precision_level"] == "degraded"


def test_local_product_patch_event_blocks(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    pytest.importorskip("numpy")
    root, stage = _make_project(tmp_path, {"镜头1.md": GOOD_PROMPT})
    imgdir = stage / "图片"
    imgdir.mkdir()
    Image.new("RGB", (64, 64), (0xE6, 0x00, 0x12)).save(str(imgdir / "镜头1.png"))
    event_dir = root / "生产数据"
    event_dir.mkdir()
    (event_dir / "production_events.jsonl").write_text(
        json.dumps({
            "stage": "image",
            "event": "generation",
            "generation": {"asset": "出图/分镜/图片/镜头1.png", "method": "local_product_patch"},
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    payload = pq.run_qc(stage)
    assert payload["summary"]["block"] >= 1
    assert any(f["check"] == "local_patch_prohibited" and f["severity"] == "block"
               for f in payload["findings"])


# ── 品牌色 ΔE：block vs pass（需 Pillow） ────────────────────────────────────────

def test_brand_color_block_vs_pass(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    np = pytest.importorskip("numpy")

    root, stage = _make_project(tmp_path, {"镜头1.md": GOOD_PROMPT, "镜头2.md": GOOD_PROMPT.replace("镜头1", "镜头2")})
    imgdir = stage / "图片"
    imgdir.mkdir()
    # 镜头1：纯品牌红 #E60012 → ΔE≈0；镜头2：纯蓝 → 启发式 WARN，不以全图颜色硬挡。
    Image.new("RGB", (64, 64), (0xE6, 0x00, 0x12)).save(str(imgdir / "镜头1.png"))
    Image.new("RGB", (64, 64), (0, 0, 255)).save(str(imgdir / "镜头2.png"))

    payload = pq.run_qc(stage)
    bc = {f["shot"]: f for f in payload["findings"] if f["check"] == "brand_color"}
    assert "镜头2" in bc and bc["镜头2"]["severity"] == "warn"
    # 镜头1 红色：whole-image 降级，ΔE 在阈内 → 应是 warn（降级判定），不是 block
    assert "镜头1" in bc and bc["镜头1"]["severity"] != "block"
    assert payload["summary"]["block"] == 0
    assert payload["summary"]["warn"] >= 1


def test_brand_color_presence_prevents_full_frame_false_block(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    pytest.importorskip("numpy")

    root, stage = _make_project(tmp_path, {"镜头1.md": GOOD_PROMPT})
    imgdir = stage / "图片"
    imgdir.mkdir()
    im = Image.new("RGB", (128, 128), (80, 48, 24))
    for y in range(40, 88):
        for x in range(40, 88):
            im.putpixel((x, y), (0xE6, 0x00, 0x12))
    im.save(str(imgdir / "镜头1.png"))

    payload = pq.run_qc(stage)
    brand_findings = [f for f in payload["findings"] if f["check"] == "brand_color"]
    assert brand_findings
    assert all(f["severity"] != "block" for f in brand_findings)
    assert brand_findings[0]["detail"]["presence"]["ratio_delta_e12"] > 0


def test_dhash_outlier_block(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    pytest.importorskip("numpy")
    # 三镜产品组：两张相同噪声图 + 一张纯白离群
    sb = {"visual_contract": {"品牌色": "#E60012"},
          "shots": [{"shot_id": f"镜头{i}", "assets": {"PROD_main": True}} for i in (1, 2, 3)]}
    root, stage = _make_project(
        tmp_path,
        {f"镜头{i}.md": GOOD_PROMPT.replace("镜头1", f"镜头{i}") for i in (1, 2, 3)},
        storyboard=sb,
    )
    imgdir = stage / "图片"
    imgdir.mkdir()
    import numpy as np
    # 镜头1/2 同款：左暗右亮的横向渐变（行向 dHash 几乎全 0）。
    grad = np.tile(np.linspace(0, 255, 32, dtype="uint8"), (32, 1))
    Image.fromarray(grad, "L").convert("RGB").save(str(imgdir / "镜头1.png"))
    Image.fromarray(grad, "L").convert("RGB").save(str(imgdir / "镜头2.png"))
    # 镜头3：高频竖条纹（行向相邻像素剧烈反转）→ dHash 与渐变图差异巨大 → 离群。
    stripes = np.tile(np.array([0, 255] * 16, dtype="uint8"), (32, 1))
    Image.fromarray(stripes, "L").convert("RGB").save(str(imgdir / "镜头3.png"))
    payload = pq.run_qc(stage)
    dh = [f for f in payload["findings"] if f["check"] == "product_dhash" and f["severity"] in ("warn", "block")]
    assert dh, "转置图应触发 dHash 离群"


def test_no_product_shots_emits_info_and_zero_exit(tmp_path):
    sb = {"visual_contract": {"品牌色": "#E60012"},
          "shots": [{"shot_id": "镜头1", "assets": {"CHAR_a": True}}]}
    root, stage = _make_project(tmp_path, {"镜头1.md": GOOD_PROMPT}, storyboard=sb)
    rc = pq.main([str(stage)])
    assert rc == 0
    payload = json.loads((root / "出图" / "分镜" / "product_qc.json").read_text(encoding="utf-8"))
    assert payload["summary"]["block"] == 0
    assert any("无产品镜" in f["reason"] for f in payload["findings"])


def test_semantic_product_shot_without_prod_id_blocks(tmp_path):
    sb = {"visual_contract": {"品牌色": "#E60012"},
          "shots": [{"shot_id": "镜头1", "product_lock": "手机屏幕显示星盒 App 界面"}]}
    root, stage = _make_project(tmp_path, {"镜头1.md": GOOD_PROMPT.replace("PROD_main", "CHAR_user")}, storyboard=sb)
    payload = pq.run_qc(stage)
    assert any(f["check"] == "asset_binding" and f["severity"] == "block" and f["detail"].get("missing") == "PROD_*"
               for f in payload["findings"])


def test_asset_registry_known_product_avoids_registry_degraded_warn(tmp_path):
    sb = {"visual_contract": {"品牌色": "#E60012"},
          "shots": [{"shot_id": "镜头1", "assets": {"PROD_STARBOX_APP": True, "BRAND_STARBOX": True},
                     "product_lock": "手机屏幕显示星盒 App 界面",
                     "safe_area": {"core_in_center_4x4": True}}]}
    prompt = GOOD_PROMPT.replace("PROD_main", "PROD_STARBOX_APP")
    root, stage = _make_project(tmp_path, {"镜头1.md": prompt}, storyboard=sb)
    reg = root / "出图" / "共享" / "asset_registry.json"
    reg.parent.mkdir(parents=True)
    reg.write_text(json.dumps({"assets": [{"id": "PROD_STARBOX_APP"}, {"id": "BRAND_STARBOX"}]}, ensure_ascii=False),
                   encoding="utf-8")
    payload = pq.run_qc(stage)
    assert not [f for f in payload["findings"] if f["check"] == "asset_binding" and f["severity"] == "block"]
    assert not [f for f in payload["findings"] if f["detail"].get("degraded") == "no_asset_registry"]


def test_center_grid_false_warns_but_does_not_fake_platform_verdict(tmp_path):
    sb = {"visual_contract": {"品牌色": "#E60012"},
          "shots": [{"shot_id": "镜头1", "assets": {"PROD_main": True},
                     "product_lock": "产品 logo 和 CTA",
                     "safe_area": {"core_in_center_4x4": False}}]}
    root, stage = _make_project(tmp_path, {"镜头1.md": GOOD_PROMPT}, storyboard=sb)
    payload = pq.run_qc(stage)
    assert any(f["check"] == "safe_area" and f["severity"] == "warn" for f in payload["findings"])


def test_asset_id_regex_does_not_match_plain_product_or_brand_words():
    shot = {"prompt": "product shot with brand color, but no structured asset id"}

    assert pq.product_asset_ids(shot) == []
    assert pq.brand_asset_ids(shot) == []


def test_brand_color_reports_no_image_before_no_pillow():
    findings = pq.check_brand_color("镜头1", None, "#E60012", None, None)

    assert findings[0]["check"] == "brand_color"
    assert findings[0]["detail"]["degraded"] == "no_image"


def test_logo_reports_no_image_before_no_pillow(tmp_path):
    findings = pq.check_logo("镜头1", None, tmp_path / "logo.png", None, None)

    assert findings[0]["check"] == "logo"
    assert findings[0]["detail"]["degraded"] == "no_image"


# ── 产品 ROI 定位 + ROI 口径像素检 + VLM 裁决接线 ────────────────────────────────

def _imaging():
    Image = pytest.importorskip("PIL.Image")
    np = pytest.importorskip("numpy")
    return Image, np


def _paste_patch(Image, size, patch_color, patch_box, bg=(240, 240, 240)):
    im = Image.new("RGB", size, bg)
    from PIL import ImageDraw
    ImageDraw.Draw(im).rectangle(patch_box, fill=patch_color)
    return im


def test_locate_product_roi_finds_known_patch(tmp_path):
    Image, np = _imaging()
    # 模板 = 带内部结构的"包装"；帧 = 同一结构贴在右下角
    tmpl = _paste_patch(Image, (80, 120), (230, 0, 18), (10, 10, 70, 110))
    from PIL import ImageDraw
    ImageDraw.Draw(tmpl).rectangle((20, 30, 60, 60), fill=(255, 255, 255))
    tmpl_path = tmp_path / "定妆_产品.png"
    tmpl.save(tmpl_path)
    frame = Image.new("RGB", (640, 360), (200, 210, 220))
    frame.paste(tmpl, (500, 200))
    frame_path = tmp_path / "镜头1.png"
    frame.save(frame_path)
    roi = pq.locate_product_roi(frame_path, [tmpl_path], Image, np)
    assert roi is not None
    left, top, right, bottom = roi["bbox"]
    # bbox 应盖住贴入位置（允许粗步长+外扩偏差）
    assert left <= 520 and right >= 540 and top <= 230 and bottom >= 250
    assert roi["confidence"] == "heuristic"


def test_locate_product_roi_refuses_low_confidence(tmp_path):
    Image, np = _imaging()
    tmpl = _paste_patch(Image, (80, 120), (230, 0, 18), (10, 10, 70, 110))
    tmpl_path = tmp_path / "定妆_产品.png"
    tmpl.save(tmpl_path)
    # 帧里根本没有产品——纯噪声梯度
    frame = Image.new("RGB", (320, 180))
    px = frame.load()
    for y in range(180):
        for x in range(320):
            px[x, y] = (x % 256, y % 256, (x * y) % 256)
    frame_path = tmp_path / "镜头1.png"
    frame.save(frame_path)
    assert pq.locate_product_roi(frame_path, [tmpl_path], Image, np) is None


def test_brand_color_block_reachable_with_bbox(tmp_path):
    Image, np = _imaging()
    # bbox 区域是纯蓝，品牌色是红 → ΔE 远超 block 阈，必须硬挡
    im = _paste_patch(Image, (200, 200), (0, 0, 255), (50, 50, 150, 150))
    p = tmp_path / "镜头1.png"
    im.save(p)
    findings = pq.check_brand_color("镜头1", p, "#E60012", Image, np, bbox=(50, 50, 150, 150))
    assert any(f["severity"] == "block" for f in findings)
    assert findings[0]["detail"]["region"] == "bbox"


def test_dhash_group_uses_bbox_map_only_when_complete(tmp_path):
    Image, np = _imaging()
    paths = []
    for i in range(3):
        im = _paste_patch(Image, (160, 160), (230, 0, 18), (40, 40, 120, 120))
        p = tmp_path / f"镜头{i+1}.png"
        im.save(p)
        paths.append((f"镜头{i+1}", p))
    full = {lb: (40, 40, 120, 120) for lb, _ in paths}
    res_full = pq.check_dhash_group(paths, Image, bbox_map=full)
    for f in res_full:
        assert f["detail"].get("region") in (None, "product_bbox")
    partial = {"镜头1": (40, 40, 120, 120)}
    res_partial = pq.check_dhash_group(paths, Image, bbox_map=partial)
    for f in res_partial:
        assert f["detail"].get("region") in (None, "whole_image")


def test_check_logo_multiscale_finds_scaled_logo(tmp_path):
    Image, np = _imaging()
    logo = _paste_patch(Image, (64, 64), (0, 0, 0), (8, 8, 56, 56), bg=(255, 255, 255))
    from PIL import ImageDraw
    ImageDraw.Draw(logo).rectangle((24, 24, 40, 40), fill=(255, 255, 255))
    logo_path = tmp_path / "logo.png"
    logo.save(logo_path)
    frame = Image.new("RGB", (400, 300), (255, 255, 255))
    frame.paste(logo.resize((96, 96)), (150, 100))  # 1.5 倍尺度
    frame_path = tmp_path / "镜头1.png"
    frame.save(frame_path)
    findings = pq.check_logo("镜头1", frame_path, logo_path, Image, np)
    assert findings == []  # 多尺度峰值应达标；单尺度旧实现会漏
    # 无 logo 的帧应给 warn
    blank = Image.new("RGB", (400, 300), (128, 128, 128))
    blank_path = tmp_path / "镜头2.png"
    blank.save(blank_path)
    findings2 = pq.check_logo("镜头2", blank_path, logo_path, Image, np)
    assert findings2 and findings2[0]["severity"] == "warn"


def _project_with_registry_and_frame(tmp_path, Image):
    root, stage = _make_project(tmp_path, {"镜头1.md": GOOD_PROMPT, "镜头2.md": GOOD_PROMPT})
    ref_dir = root / "出图" / "共享" / "定妆库" / "产品"
    ref_dir.mkdir(parents=True)
    ref = _paste_patch(Image, (80, 120), (230, 0, 18), (10, 10, 70, 110))
    ref_path = ref_dir / "定妆_产品.png"
    ref.save(ref_path)
    reg = {"products": [{"id": "PROD_main",
                         "reference_images": ["出图/共享/定妆库/产品/定妆_产品.png"]}]}
    (root / "出图" / "共享" / "asset_registry.json").write_text(
        json.dumps(reg, ensure_ascii=False), encoding="utf-8")
    for label in ("镜头1", "镜头2"):
        frame = Image.new("RGB", (320, 240), (240, 240, 240))
        frame.paste(ref, (100, 60))
        frame.save(stage / f"{label}.png")
    return root, stage


def test_run_qc_vlm_wiring_reports_unadjudicated_then_consumes_verdict(tmp_path):
    Image, np = _imaging()
    root, stage = _project_with_registry_and_frame(tmp_path, Image)
    payload = pq.run_qc(stage)
    checks = [f["check"] for f in payload["findings"]]
    assert "vlm_product_unadjudicated" in checks  # 任务包已生成但 0 裁决 → 机检空转要可见
    tasks = json.loads((root / "生产数据" / "ad_vlm_judge_tasks.json").read_text(encoding="utf-8"))
    assert tasks["task_count"] >= 2
    # 回填一条 suspect 裁决（合同要求原样复制 sha）→ 消费为 vlm_product_identity warn
    task = tasks["tasks"][0]
    verdict = {"verdicts": [{
        "task_id": task["task_id"],
        "image_sha256": task["image"]["sha256"],
        "task_sha256": task["task_sha256"],
        "references_sha256": task["references_sha256"],
        "evaluator": {"model": "test-vlm", "version": "2026-07", "reviewed_at": "2026-07-20T00:00:00"},
        "scores": {"presence": 5, "structure": 2, "relation": 4},
        "verdict": "suspect",
        "notes": "包装文字漂了",
    }]}
    (root / "生产数据" / "ad_vlm_judge_verdicts.json").write_text(
        json.dumps(verdict, ensure_ascii=False), encoding="utf-8")
    payload2 = pq.run_qc(stage)
    checks2 = [f["check"] for f in payload2["findings"]]
    assert "vlm_product_identity" in checks2
    assert "vlm_product_partial_coverage" in checks2  # 2 任务只裁了 1 条


def test_run_qc_no_vlm_flag_skips_task_refresh(tmp_path):
    Image, np = _imaging()
    root, stage = _project_with_registry_and_frame(tmp_path, Image)
    pq.run_qc(stage, refresh_vlm_tasks=False)
    assert not (root / "生产数据" / "ad_vlm_judge_tasks.json").exists()
