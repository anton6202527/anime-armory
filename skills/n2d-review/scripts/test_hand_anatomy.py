#!/usr/bin/env python3
"""hand_anatomy 纯几何单测（无 cv2/mediapipe 依赖）。
cd skills/n2d-review/scripts && python -m pytest test_hand_anatomy.py
"""
import hand_anatomy as ha


def test_count_fingertips_open_hand():
    # 张开手：4 道深指缝（拇-食-中-无名-小之间）→ 5 指尖
    depths = [30, 28, 26, 25]
    assert ha.count_fingertips(depths, scale=100.0, min_frac=0.22) == 5


def test_count_fingertips_extra_finger():
    # 六指：5 道深指缝 → 6 指尖
    depths = [30, 29, 28, 27, 26]
    assert ha.count_fingertips(depths, scale=100.0) == 6


def test_count_fingertips_shallow_noise_ignored():
    # 全是浅毛刺（< scale*min_frac）→ 不算指缝 → 0（不误判握拳为多指）
    assert ha.count_fingertips([5, 4, 3, 2], scale=100.0, min_frac=0.22) == 0


def test_count_fingertips_no_scale():
    assert ha.count_fingertips([30, 28], scale=0.0) == 0


def test_anatomy_band_extra_is_block():
    assert ha.anatomy_band(6) == "block"
    assert ha.anatomy_band(7) == "block"


def test_anatomy_band_normal_is_ok():
    # 正常 5 指 / 握拳 0-1 指尖 一律 ok，不误杀
    for ft in (0, 1, 2, 3, 4, 5):
        assert ha.anatomy_band(ft) == "ok"


def test_anatomy_band_custom_threshold():
    assert ha.anatomy_band(5, extra_threshold=5) == "block"
    assert ha.anatomy_band(4, extra_threshold=5) == "ok"


def test_worst_band():
    assert ha.worst_band(["ok", "ok"]) == "ok"
    assert ha.worst_band(["ok", "warn"]) == "warn"
    assert ha.worst_band(["ok", "warn", "block"]) == "block"
    assert ha.worst_band([]) == "ok"


def test_episode_png_paths_reads_canonical_image_dir(tmp_path):
    ep = "第1集"
    img = tmp_path / "出图" / ep / "图片"
    flat = tmp_path / "出图" / ep
    img.mkdir(parents=True)
    (img / "Clip_01.png").write_bytes(b"x")
    (flat / "legacy.png").write_bytes(b"x")

    names = [p.rsplit("/", 1)[-1] for p in ha.episode_png_paths(str(tmp_path), ep)]

    assert names == ["Clip_01.png", "legacy.png"]
