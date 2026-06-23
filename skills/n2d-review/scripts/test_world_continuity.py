#!/usr/bin/env python3
"""world_continuity 纯数学核心测试（无 Pillow 依赖）。

跑：cd skills/n2d-review/scripts && python -m pytest test_world_continuity.py
"""
from __future__ import annotations

import world_continuity as wc


# ---------- daypart ----------

def test_daypart_clear_night():
    # 低明度（不管暖度）→ 夜
    assert wc.daypart(luma=30.0, warmth=0.0) == "night"
    assert wc.daypart(luma=30.0, warmth=0.5) == "night"   # 暖也算夜（明度压顶）


def test_daypart_clear_day():
    # 高明度 → 白天
    assert wc.daypart(luma=200.0, warmth=0.0) == "day"
    assert wc.daypart(luma=200.0, warmth=0.3) == "day"


def test_daypart_dusk_needs_mid_luma_and_warmth():
    # 中明度 + 暖 → 黄昏
    assert wc.daypart(luma=110.0, warmth=0.20) == "dusk"
    # 中明度但冷调 → 不算黄昏，归白天
    assert wc.daypart(luma=110.0, warmth=0.0) == "day"


def test_daypart_thresholds_tweakable():
    # 默认 110 暖 → dusk；把 day_luma 降到 100 后同输入直接判 day
    assert wc.daypart(110.0, 0.20) == "dusk"
    assert wc.daypart(110.0, 0.20, day_luma=100.0) == "day"
    # night_luma 下调能把中暗镜从 night 拉回 dusk
    assert wc.daypart(60.0, 0.20) == "night"           # 默认 night_luma=70 → 60 判夜
    assert wc.daypart(60.0, 0.20, night_luma=50.0) == "dusk"


# ---------- daypart_rank ----------

def test_daypart_rank_ordering():
    assert wc.daypart_rank("night") == 0
    assert wc.daypart_rank("dusk") == 1
    assert wc.daypart_rank("day") == 2
    assert wc.daypart_rank("night") < wc.daypart_rank("dusk") < wc.daypart_rank("day")


def test_daypart_rank_unknown_is_neutral():
    assert wc.daypart_rank("???") == 1


# ---------- continuity_band ----------

def test_band_same_is_ok():
    assert wc.continuity_band("day", "day") == "ok"
    assert wc.continuity_band("night", "night") == "ok"


def test_band_one_rank_jump_is_warn():
    assert wc.continuity_band("day", "dusk") == "warn"
    assert wc.continuity_band("dusk", "night") == "warn"
    assert wc.continuity_band("night", "dusk") == "warn"


def test_band_two_rank_day_night_is_block():
    assert wc.continuity_band("day", "night") == "block"
    assert wc.continuity_band("night", "day") == "block"


def test_band_locked_contradiction_is_block():
    # 相邻同级(ok)，但与锁定值差 2 级 → block
    assert wc.continuity_band("night", "night", locked_label="day") == "block"
    # 锁定一致则不升级（仍走相邻判定）
    assert wc.continuity_band("day", "day", locked_label="day") == "ok"
    # 锁定差 1 级不触发违锁 block；相邻同级 → ok
    assert wc.continuity_band("day", "day", locked_label="dusk") == "ok"


def test_band_takes_worst_of_jump_and_lock():
    # 相邻 1 级跳(night→dusk=warn) 但本镜 dusk... 用 cur 与 lock 差 2 级才违锁：
    # prev=dusk→cur=day 相邻 1 级(warn)，cur=day 与 lock=night 差 2 级(block) → 取较重 block
    assert wc.continuity_band("dusk", "day", locked_label="night") == "block"


# ---------- light_azimuth（W2·纯数学） ----------

def test_light_azimuth_buckets():
    assert wc.light_azimuth(0.1) == "left"
    assert wc.light_azimuth(0.9) == "right"
    assert wc.light_azimuth(0.5) == "center"        # 正中
    assert wc.light_azimuth(0.55) == "center"       # 死区内仍居中


def test_light_azimuth_deadzone_tweakable():
    # 缩小死区 → 0.55 判 right
    assert wc.light_azimuth(0.55, deadzone=0.02) == "right"


# ---------- light_dir_band（W2·只抓左右硬翻转·advisory） ----------

def test_light_dir_band_flip_is_warn():
    assert wc.light_dir_band("left", "right") == "warn"
    assert wc.light_dir_band("right", "left") == "warn"


def test_light_dir_band_center_transition_ok():
    assert wc.light_dir_band("left", "center") == "ok"
    assert wc.light_dir_band("center", "right") == "ok"
    assert wc.light_dir_band("left", "left") == "ok"


def test_episode_png_paths_reads_canonical_image_dir(tmp_path):
    ep = "第1集"
    img = tmp_path / "出图" / ep / "图片"
    flat = tmp_path / "出图" / ep
    img.mkdir(parents=True)
    (img / "Clip_01.png").write_bytes(b"x")
    (flat / "legacy.png").write_bytes(b"x")

    names = [p.rsplit("/", 1)[-1] for p in wc.episode_png_paths(str(tmp_path), ep)]

    assert names == ["Clip_01.png", "legacy.png"]


# ---------- W3 光照物理（俯仰 + 光位锚自洽·A3） ----------

def test_light_elevation_bands():
    assert wc.light_elevation(0.1) == "top"
    assert wc.light_elevation(0.9) == "bottom"
    assert wc.light_elevation(0.5) == "center"


def test_light_elev_band_only_top_bottom_flip_warns():
    assert wc.light_elev_band("top", "bottom") == "warn"
    assert wc.light_elev_band("bottom", "top") == "warn"
    assert wc.light_elev_band("top", "center") == "ok"
    assert wc.light_elev_band("top", "top") == "ok"


def test_declared_light_dir_parses_h_and_v():
    assert wc.declared_light_dir("继承 LOC_01，画左破窗冷月主光") == {"h": "left", "v": None}
    assert wc.declared_light_dir("右侧顶光，硬光") == {"h": "right", "v": "top"}
    assert wc.declared_light_dir("自下而上的鬼影光") == {"h": None, "v": "bottom"}
    assert wc.declared_light_dir("逆光剪影") == {"h": None, "v": None}   # 含糊词不判


def test_anchor_contradiction_h_and_v():
    assert wc.anchor_contradiction({"h": "left", "v": None}, "right", None)  # 声明左实测右
    assert wc.anchor_contradiction({"h": "left", "v": None}, "left", None) is None
    assert wc.anchor_contradiction({"h": None, "v": "top"}, None, "bottom")  # 声明顶实测底
    # 同轴缺测/缺声明 → 不判矛盾
    assert wc.anchor_contradiction({"h": "left", "v": None}, None, None) is None
    assert wc.anchor_contradiction({"h": None, "v": None}, "right", "bottom") is None


def test_analyze_emits_light_elevation_flip(tmp_path, monkeypatch):
    try:
        from PIL import Image
    except Exception:
        return
    root = tmp_path / "剧"
    imgdir = root / "出图" / "第1集"
    imgdir.mkdir(parents=True)

    def _save(name, lit_top):
        im = Image.new("L", (48, 48), 20)  # 暗底
        px = im.load()
        ys = range(0, 12) if lit_top else range(36, 48)  # 顶亮 vs 底亮
        for y in ys:
            for x in range(48):
                px[x, y] = 255
        im.save(imgdir / name)

    _save("EP01_CLIP01.png", lit_top=True)    # 顶光
    _save("EP01_CLIP02.png", lit_top=False)   # 底光 → 与上镜俯仰翻转
    monkeypatch.setattr(wc, "_scene_of_shot", lambda r, e: {
        "EP01_CLIP01.png": "冷宫", "EP01_CLIP02.png": "冷宫"})
    res = wc.analyze(str(root), "第1集")
    assert res["available"] is True
    elev = [s for s in res["shots"] if s.get("metric") == "light_elevation" and s["verdict"] == "warn"]
    assert any(s["png"] == "EP01_CLIP02.png" for s in elev)
