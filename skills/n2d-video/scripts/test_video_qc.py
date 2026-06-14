from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("video_qc.py")
spec = importlib.util.spec_from_file_location("video_qc", SCRIPT)
video_qc = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(video_qc)


def test_parse_clip_range_and_batch_label() -> None:
    assert video_qc.parse_clip_range("01-05") == (1, 5)
    assert video_qc.parse_clip_range("6_10") == (6, 10)
    assert video_qc.batch_label(6, 10) == "06_10"


def test_discover_clips_filters_by_range(tmp_path: Path) -> None:
    video_dir = tmp_path / "出视频" / "第1集" / "视频"
    video_dir.mkdir(parents=True)
    for name in ["Clip_01_A.mp4", "Clip_02_B.mp4", "Clip_10_C.mp4", "not_a_clip.mp4"]:
        (video_dir / name).write_bytes(b"")

    found = video_qc.discover_clips(tmp_path, "第1集", 2, 10)

    assert [p.name for p in found] == ["Clip_02_B.mp4", "Clip_10_C.mp4"]


def test_sample_times_uses_start_mid_end() -> None:
    assert video_qc.sample_times(5.0) == [("start", 0.0), ("mid", 2.5), ("end", 4.8)]


def test_seam_pairs_only_adjacent_present() -> None:
    assert video_qc.seam_pairs([1, 2, 3]) == [(1, 2), (2, 3)]
    assert video_qc.seam_pairs([1, 3]) == []          # 缺中间镜不硬凑
    assert video_qc.seam_pairs([2]) == []
    assert video_qc.seam_pairs([]) == []


def _make_frame(tmp_path: Path, name: str, rgb) -> str:
    from PIL import Image

    p = tmp_path / name
    Image.new("RGB", (64, 64), rgb).save(p)
    return str(p)


def test_machine_check_flags_color_jump_seam(tmp_path: Path) -> None:
    import pytest

    pytest.importorskip("PIL")
    red_end = _make_frame(tmp_path, "Clip_01_03_end.jpg", (200, 30, 30))
    blue_start = _make_frame(tmp_path, "Clip_02_01_start.jpg", (30, 30, 200))
    payload = {
        "clips": [
            {"file": "Clip_01_x.mp4", "frames": [{"label": "end", "path": red_end}]},
            {"file": "Clip_02_y.mp4", "frames": [{"label": "start", "path": blue_start}]},
        ],
    }
    video_qc.machine_check(payload)
    summary = payload["machine_summary"]
    assert summary["seams_checked"] == 1
    assert summary["seam_blocks"] + summary["seam_warns"] == 1  # 红→蓝剪辑点闪光必被抓
    assert payload["seams"][0]["from_clip"] == "Clip_01"


def test_machine_check_uses_context_frames(tmp_path: Path) -> None:
    import pytest

    pytest.importorskip("PIL")
    # 批次里只有 Clip_02；Clip_01 的 end 帧由调用方（盘上相邻镜）补入 → 仍能查 01→02 接缝
    a = _make_frame(tmp_path, "ctx_end.jpg", (50, 120, 50))
    b = _make_frame(tmp_path, "Clip_02_01_start.jpg", (50, 120, 50))
    payload = {"clips": [{"file": "Clip_02_y.mp4", "frames": [{"label": "start", "path": b}]}]}
    video_qc.machine_check(payload, context_frames={1: {"end": a}})
    assert payload["machine_summary"]["seams_checked"] == 1
    assert payload["seams"][0]["verdict"] == "ok"  # 同色同构图 → 接力正常


def test_seam_strictness_respects_storyboard_intent() -> None:
    assert video_qc.seam_strictness(None) == "strict"                       # 无意图 → 宁可误报
    assert video_qc.seam_strictness({"transition": "match_cut"}) == "info"  # 设计切镜 → 只记录
    assert video_qc.seam_strictness({"transition": "hard_cut"}) == "info"
    assert video_qc.seam_strictness({"transition": "relay"}) == "strict"    # 声明接力 → 铁律
    assert video_qc.seam_strictness({"transition": "match_cut", "relay": True}) == "strict"
    assert video_qc.seam_strictness({"transition": ""}) == "strict"


def test_load_seam_intents_does_not_treat_hard_cut_endframe_as_relay(tmp_path: Path) -> None:
    import json

    sb = tmp_path / "脚本" / "第1集"
    sb.mkdir(parents=True)
    (sb / "storyboard.json").write_text(json.dumps({"clips": [
        {"id": "EP01_CLIP01", "continuity": {"transition": "hard_cut", "need_endframe": True}},
        {"id": "EP01_CLIP02", "need_end_frame": True, "continuity": {"transition": "接力"}},
        {"id": "EP01_CLIP03", "continuity": {"need_endframe": True}},
    ]}, ensure_ascii=False), encoding="utf-8")

    intents = video_qc.load_seam_intents(tmp_path, "第1集")

    assert intents[1]["transition"] == "hard_cut" and intents[1]["relay"] is False
    assert intents[2]["relay"] is True
    assert intents[3]["transition"] is None and intents[3]["relay"] is True


def test_is_closeup_lens_markers() -> None:
    assert video_qc.is_closeup_lens("CU 50mm 缓推")
    assert video_qc.is_closeup_lens("ECU")
    assert video_qc.is_closeup_lens("MCU到物件CU")
    assert video_qc.is_closeup_lens("MS到CU")          # 推到近景 → 近景
    assert video_qc.is_closeup_lens("CU反打")
    assert video_qc.is_closeup_lens("过肩反打")
    assert not video_qc.is_closeup_lens("LS 35mm 慢推")  # 远景不入列
    assert not video_qc.is_closeup_lens("MS")            # 中景不入列
    assert not video_qc.is_closeup_lens("")


def test_load_shot_types_reads_lens(tmp_path: Path) -> None:
    import json
    sb = tmp_path / "脚本" / "第1集"
    sb.mkdir(parents=True)
    (sb / "storyboard.json").write_text(json.dumps({"clips": [
        {"id": "Clip_01", "shots": [{"lens": "LS 35mm 慢推"}]},
        {"id": "Clip_02", "shots": [{"lens": "CU 50mm"}, {"lens": "MS"}]},
    ]}, ensure_ascii=False), encoding="utf-8")
    types = video_qc.load_shot_types(tmp_path, "第1集")
    assert types[1]["closeup"] is False
    assert types[2]["closeup"] is True  # 含一个 CU 分镜即近景


def _make_gradient_frame(tmp_path: Path, name: str, reverse: bool) -> str:
    """水平亮度梯度帧；reverse 时方向翻转，使每列水平梯度全反号 → dHash 距拉满（模拟脸被重画的结构突变）。
    dHash 抓梯度不抓绝对色，所以用方向相反的梯度而非纯色块。"""
    from PIL import Image
    p = tmp_path / name
    img = Image.new("RGB", (64, 64))
    for x in range(64):
        v = min(255, (63 - x) * 4 if reverse else x * 4)
        for y in range(64):
            img.putpixel((x, y), (v, v, v))
    img.save(p)
    return str(p)


def test_intra_clip_check_flags_gross_face_jump(tmp_path: Path) -> None:
    import pytest
    pytest.importorskip("PIL")
    # 近景 clip 的 start/end 帧结构剧变（水平梯度方向全反）→ 远超重画阈值 → block
    start = _make_gradient_frame(tmp_path, "Clip_03_01_start.jpg", reverse=False)
    end = _make_gradient_frame(tmp_path, "Clip_03_03_end.jpg", reverse=True)
    payload = {"clips": [{"file": "Clip_03_face.mp4",
                          "frames": [{"label": "start", "path": start},
                                     {"label": "end", "path": end}]}]}
    video_qc.intra_clip_check(payload, shot_types={3: {"closeup": True, "lens": "CU 50mm"}})
    assert payload["machine_summary"]["intra_checked"] == 1
    assert payload["machine_summary"]["intra_blocks"] == 1
    assert payload["intra_clips"][0]["clip"] == "Clip_03"
    assert payload["intra_clips"][0]["verdict"] == "block"


def test_intra_clip_check_skips_non_closeup(tmp_path: Path) -> None:
    import pytest
    pytest.importorskip("PIL")
    start = _make_frame(tmp_path, "Clip_04_01_start.jpg", (0, 0, 0))
    end = _make_frame(tmp_path, "Clip_04_03_end.jpg", (255, 255, 255))
    payload = {"clips": [{"file": "Clip_04_wide.mp4",
                          "frames": [{"label": "start", "path": start},
                                     {"label": "end", "path": end}]}]}
    # 有景别表且为远景 → 跳过，不抽样
    video_qc.intra_clip_check(payload, shot_types={4: {"closeup": False, "lens": "LS"}})
    assert "intra_checked" not in payload.get("machine_summary", {})


def test_machine_check_downgrades_declared_cut_to_info(tmp_path: Path) -> None:
    import pytest

    pytest.importorskip("PIL")
    red_end = _make_frame(tmp_path, "Clip_01_03_end.jpg", (200, 30, 30))
    blue_start = _make_frame(tmp_path, "Clip_02_01_start.jpg", (30, 30, 200))
    payload = {
        "clips": [
            {"file": "Clip_01_x.mp4", "frames": [{"label": "end", "path": red_end}]},
            {"file": "Clip_02_y.mp4", "frames": [{"label": "start", "path": blue_start}]},
        ],
    }
    video_qc.machine_check(payload, seam_intents={1: {"transition": "match_cut", "relay": False}})
    s = payload["machine_summary"]
    assert s["seam_blocks"] == 0 and s["seam_info"] == 1          # 设计切镜不拦验收
    assert payload["seams"][0]["verdict"] == "info"
    assert payload["seams"][0]["verdict_if_relay"] in ("warn", "block")  # 原始距离仍留痕


def test_intra_verdict_blocks_only_closeup_nondoubleframe_redraw() -> None:
    g = 29  # SEAM_BLOCK
    rb = video_qc.INTRA_REDRAW_BLOCK  # 44
    # 正常表演/运镜：<=gross → ok
    assert video_qc.intra_verdict(20, g, have_types=True, double_frame=False) == "ok"
    # gross<worst<=redraw：粗筛 warn（即便近景非双帧，未到重画阈值不误杀）
    assert video_qc.intra_verdict(35, g, have_types=True, double_frame=False) == "warn"
    # 近景 + 非双帧 + 远超重画阈值 → block
    assert video_qc.intra_verdict(50, g, have_types=True, double_frame=False) == "block"
    # 双帧接力镜豁免（端点已锚同人，大表情弧线天然大距离）→ warn
    assert video_qc.intra_verdict(50, g, have_types=True, double_frame=True) == "warn"
    # 景别未知（无 storyboard）→ 绝不 block（不误杀非近景）→ warn
    assert video_qc.intra_verdict(50, g, have_types=False, double_frame=False) == "warn"
