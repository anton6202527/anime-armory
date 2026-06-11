#!/usr/bin/env python3
"""Tests for the n2d progress-table parser/router.

Run from this directory:
    cd skills/common && python -m pytest test_n2d_route.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from n2d_route import (  # noqa: E402
    cell_state, is_done, is_started, _cn_to_int, episode_number, normalize_episode,
    parse_progress, stage_of, voice_is_placeholder, manifest_path, is_flow_complete,
    is_progress_satisfied, voiceover_fingerprint,
)


# ── voiceover_fingerprint：抓"配音后又改 voiceover.txt"的失配 ──
def test_voiceover_fingerprint_detects_content_change(tmp_path):
    p = tmp_path / "voiceover.txt"
    p.write_text("[镜头1·沈念·冷] 你来了。\n[镜头2·柳娘子·惊] 娘娘息怒。\n", encoding="utf-8")
    fp1 = voiceover_fingerprint(str(p))
    # 排版改动（空行 / 行尾空白）不该改指纹
    p.write_text("[镜头1·沈念·冷] 你来了。  \n\n[镜头2·柳娘子·惊] 娘娘息怒。\n", encoding="utf-8")
    assert voiceover_fingerprint(str(p)) == fp1
    # 改台词 / 插句 → 指纹变
    p.write_text("[镜头1·沈念·冷] 你终于来了。\n[镜头2·柳娘子·惊] 娘娘息怒。\n", encoding="utf-8")
    assert voiceover_fingerprint(str(p)) != fp1


def test_voiceover_fingerprint_missing_file_is_empty(tmp_path):
    assert voiceover_fingerprint(str(tmp_path / "nope.txt")) == ""
    assert voiceover_fingerprint("") == ""


# ── cell_state / is_done：na（不适用）算已满足 ──
def test_cell_state_basic():
    assert cell_state("✅") == "done"
    assert cell_state("") == "todo"
    assert cell_state("⬜") == "todo"
    assert cell_state("⏳rough") == "rough"
    assert is_started("⏳rough") is True
    assert is_done("⏳rough") is False
    assert cell_state("3/5") == "partial"
    assert cell_state("5/5") == "done"
    assert cell_state("0/5") == "todo"


def test_cell_state_na_counts_as_satisfied():
    for v in ("—", "-", "N/A", "无", "×"):
        assert cell_state(v) == "na"
        assert is_done(v) is True       # na 不挡完成
        assert is_started(v) is False   # 但不算"已开工"
    assert is_done("") is False
    assert is_done("⬜") is False


# ── 集号解析：ASCII / 全角 / 中文数字 ──
def test_cn_to_int():
    assert _cn_to_int("12") == 12
    assert _cn_to_int("１２") == 12       # 全角
    assert _cn_to_int("十二") == 12
    assert _cn_to_int("二十") == 20
    assert _cn_to_int("二十三") == 23
    assert _cn_to_int("三") == 3
    assert _cn_to_int("abc") is None


def test_episode_number_normalization():
    assert episode_number("第１２集") == 12
    assert episode_number("第十二集") == 12
    assert episode_number("十二") == 12
    assert episode_number("abc") is None
    assert normalize_episode("第三集") == "第3集"
    assert normalize_episode("第２集") == "第2集"


PROG_HEADER = "| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 |"
PROG_SEP = "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"


def _write_progress(tmp_path, rows):
    p = os.path.join(tmp_path, "_进度.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(PROG_HEADER + "\n" + PROG_SEP + "\n" + "\n".join(rows) + "\n")
    return str(tmp_path)


def test_parse_mixed_episode_numerals(tmp_path):
    rows = [
        "| 第1集 | 800 | … | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ |",
        "| 第２集 | 800 | … | ✅ | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |",
        "| 第三集 | 800 | … | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |",
    ]
    root = _write_progress(tmp_path, rows)
    header, parsed = parse_progress(root)
    assert len(parsed) == 3                       # 全角/中文集号都没被丢
    assert [r["_num"] for r in parsed] == [1, 2, 3]


def test_no_empty_frontier_on_secondary_column(tmp_path):
    # 第1集：除 素材清单 外全 ✅（字幕英=— 不适用）→ 应路由到 n2d-script，而非空前沿
    rows = [
        "| 第1集 | 800 | … | ✅ | ✅ | ✅ | ✅ | ✅ | ⬜ | ✅ | — | ✅ | ✅ | ✅ | ✅ | ⬜ |",
    ]
    root = _write_progress(tmp_path, rows)
    header, parsed = parse_progress(root)
    route = stage_of(root, parsed[0], header)
    assert route["col"] == "素材清单"
    assert route["skill"] == "n2d-script"


def test_zh_only_episode_can_complete(tmp_path):
    # 字幕英=— 的纯中文集，全流程 ✅ → 不应卡在不适用列上
    rows = [
        "| 第1集 | 800 | … | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ |",
    ]
    root = _write_progress(tmp_path, rows)
    header, parsed = parse_progress(root)
    route = stage_of(root, parsed[0], header)
    assert route["col"] is None        # 已成片
    assert route["skill"] is None


# ── manifest_path / voice_is_placeholder：合成/ 与 出视频/ 双探 ──
def _put_manifest(base_dir, placeholder):
    os.makedirs(base_dir, exist_ok=True)
    data = [{"idx": 0, "文本": "x", "时长": 1.0, **({"占位": True} if placeholder else {})}]
    json.dump(data, open(os.path.join(base_dir, "时长清单.json"), "w", encoding="utf-8"),
              ensure_ascii=False)


def test_manifest_path_probes_both_bases(tmp_path):
    root = str(tmp_path)
    assert manifest_path(root, "第1集") is None
    # 只在 出视频/ 下（先出视频后配音）
    _put_manifest(os.path.join(root, "出视频", "第1集", "配音"), placeholder=True)
    p = manifest_path(root, "第1集")
    assert p and "出视频" in p
    assert voice_is_placeholder(root, "第1集") is True


def test_manifest_path_prefers_compose_dir(tmp_path):
    root = str(tmp_path)
    _put_manifest(os.path.join(root, "出视频", "第2集", "配音"), placeholder=True)
    _put_manifest(os.path.join(root, "合成", "第2集", "配音"), placeholder=False)
    p = manifest_path(root, "第2集")
    assert "合成" in p                              # 合成/ 优先
    assert voice_is_placeholder(root, "第2集") is False


# ── ④ 制作模式：原生音画下 配音 不卡路由（治误推 n2d-voice）──────────────────
def _set_mode(root, mode):
    open(os.path.join(root, "_设置.md"), "w", encoding="utf-8").write(f"- 制作模式: {mode}\n")


def test_voice_first_routes_to_voice_when_unvoiced(tmp_path):
    # 配音先行：剧本改编 ✅ 但配音 ⬜ → 前沿就是 n2d-voice
    rows = ["| 第1集 | 800 | … | ✅ | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |"]
    root = _write_progress(tmp_path, rows)
    _set_mode(root, "配音先行")
    header, parsed = parse_progress(root)
    route = stage_of(root, parsed[0], header)
    assert route["skill"] == "n2d-voice"
    assert route["col"] == "配音"


def test_voice_first_rough_voice_still_routes_to_voice(tmp_path):
    # 配音先行：⏳rough 只代表占位时长，不能算真实配音完成
    rows = ["| 第1集 | 800 | … | ✅ | ✅ | ✅ | ⏳rough | ⬜ | ⬜ | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |"]
    root = _write_progress(tmp_path, rows)
    _set_mode(root, "配音先行")
    header, parsed = parse_progress(root)
    route = stage_of(root, parsed[0], header)
    assert route["skill"] == "n2d-voice"
    assert route["col"] == "配音"
    assert is_progress_satisfied(root, parsed[0], "配音") is False


def test_video_first_rough_voice_can_drive_storyboard(tmp_path):
    # 先出视频后配音：⏳rough 可作时间脚手架推进到分镜/出图，但不是最终成片音轨
    rows = ["| 第1集 | 800 | … | ✅ | ✅ | ✅ | ⏳rough | ⬜ | ⬜ | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |"]
    root = _write_progress(tmp_path, rows)
    _set_mode(root, "先出视频后配音")
    header, parsed = parse_progress(root)
    route = stage_of(root, parsed[0], header)
    assert route["skill"] == "n2d-script"
    assert route["col"] == "分镜设计"
    assert is_progress_satisfied(root, parsed[0], "配音") is True


def test_native_av_skips_voice_column(tmp_path):
    # 原生音画：配音 ⬜ 不该误推 n2d-voice，应直接推进到 分镜设计（说话镜走 native 同步音画）
    rows = ["| 第1集 | 800 | … | ✅ | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |"]
    root = _write_progress(tmp_path, rows)
    _set_mode(root, "原生音画")
    header, parsed = parse_progress(root)
    route = stage_of(root, parsed[0], header)
    assert route["skill"] == "n2d-script"
    assert route["col"] == "分镜设计"


def test_native_av_requires_let_image_proceed_without_voice(tmp_path):
    # 原生音画：配音 ⬜ 但分镜设计 ✅ → 出图prompt 的 requires 含「配音」，不能因此卡住
    rows = ["| 第1集 | 800 | … | ✅ | ✅ | ✅ | ⬜ | ✅ | ✅ | ✅ | — | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |"]
    root = _write_progress(tmp_path, rows)
    _set_mode(root, "原生音画")
    header, parsed = parse_progress(root)
    route = stage_of(root, parsed[0], header)
    assert route["col"] == "出图prompt"
    assert route["skill"] == "n2d-image"


def test_native_av_flow_completion_treats_voice_as_satisfied(tmp_path):
    rows = ["| 第1集 | 800 | … | ✅ | ✅ | ✅ | ⬜ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ |"]
    root = _write_progress(tmp_path, rows)
    _set_mode(root, "原生音画")
    header, parsed = parse_progress(root)
    flow = [h for h in header if h not in {"集", "字数", "raw"}]
    assert is_flow_complete(root, parsed[0], flow) is True


def test_video_first_compose_requires_confirmed_real_voice_manifest(tmp_path):
    rows = ["| 第1集 | 800 | … | ✅ | ✅ | ✅ | ⏳rough | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | ⬜ |"]
    root = _write_progress(tmp_path, rows)
    _set_mode(root, "先出视频后配音")
    header, parsed = parse_progress(root)

    route = stage_of(root, parsed[0], header)

    assert route["skill"] == "n2d-voice"
    assert route["label"] == "补真实配音"
