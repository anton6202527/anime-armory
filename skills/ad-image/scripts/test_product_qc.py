#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""product_qc 单测。从本目录跑：
    cd skills/ad-image/scripts && python3 -m pytest test_product_qc.py
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
    ]}
    assert pq.product_shots(sb) == ["镜头1"]


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
    assert set(payload.keys()) == {"summary", "findings"}
    assert set(payload["summary"].keys()) == {"block", "warn", "info"}
    assert payload["summary"]["block"] >= 1
    # 每条 finding 符合权威 schema
    for f in payload["findings"]:
        assert set(["severity", "shot", "check", "reason", "detail"]).issubset(f.keys())
        assert f["severity"] in ("block", "warn", "info")
        assert f["check"] in ("brand_color", "product_dhash", "logo", "prompt_lint")


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


# ── 品牌色 ΔE：block vs pass（需 Pillow） ────────────────────────────────────────

def test_brand_color_block_vs_pass(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    np = pytest.importorskip("numpy")

    root, stage = _make_project(tmp_path, {"镜头1.md": GOOD_PROMPT, "镜头2.md": GOOD_PROMPT.replace("镜头1", "镜头2")})
    imgdir = stage / "图片"
    imgdir.mkdir()
    # 镜头1：纯品牌红 #E60012 → ΔE≈0 pass；镜头2：纯蓝 → ΔE 巨大 block
    Image.new("RGB", (64, 64), (0xE6, 0x00, 0x12)).save(str(imgdir / "镜头1.png"))
    Image.new("RGB", (64, 64), (0, 0, 255)).save(str(imgdir / "镜头2.png"))

    payload = pq.run_qc(stage)
    bc = {f["shot"]: f for f in payload["findings"] if f["check"] == "brand_color"}
    # 镜头2 蓝色应 block
    assert "镜头2" in bc and bc["镜头2"]["severity"] == "block"
    # 镜头1 红色：whole-image 降级，ΔE 在阈内 → 应是 warn（降级判定），不是 block
    assert "镜头1" in bc and bc["镜头1"]["severity"] != "block"
    assert payload["summary"]["block"] >= 1


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
