"""特效窜色机检单测（cd skills/n2d-review/scripts && python -m pytest test_vfx_color_consistency.py）。

纯环形色相数学 + 一个端到端合成项目（生成不同色相的 PNG，验证跨镜窜色被 flag）。
"""
import colorsys
import importlib.util
import json
import sys
from pathlib import Path


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


vc = _load("vfx_color_consistency")


def test_hue_distance_handles_red_wraparound():
    assert abs(vc.hue_dist_deg(vc.hue_to_turn(350), vc.hue_to_turn(10)) - 20.0) < 1e-6
    assert abs(vc.hue_dist_deg(vc.hue_to_turn(42), vc.hue_to_turn(222)) - 180.0) < 1e-6


def test_circular_mean_near_zero():
    m = vc.circular_mean_turn([vc.hue_to_turn(355), vc.hue_to_turn(5)])
    assert vc.hue_dist_deg(m, 0.0) < 1.0


def test_window_centroid_ignores_gray_and_out_of_window():
    target = vc.hue_to_turn(42)
    samples = [
        (vc.hue_to_turn(44), 0.7, 0.8),   # 命中
        (vc.hue_to_turn(40), 0.6, 0.7),   # 命中
        (0.5, 0.02, 0.9),                 # 灰，忽略
        (vc.hue_to_turn(210), 0.8, 0.8),  # 窗口外，忽略
    ]
    cen, cov = vc.window_centroid(samples, target, half_width_turns=55 / 360, sat_floor=0.35, val_floor=0.28)
    assert vc.hue_dist_deg(cen, target) < 5 and abs(cov - 0.5) < 1e-6


def _solid_png(path: Path, hue_deg: float) -> None:
    from PIL import Image
    r, g, b = colorsys.hsv_to_rgb((hue_deg % 360) / 360.0, 0.85, 0.85)
    Image.new("RGB", (48, 48), (int(r * 255), int(g * 255), int(b * 255))).save(path)


def test_analyze_flags_cross_shot_hue_drift(tmp_path: Path):
    from PIL import Image  # noqa: F401  (skip cleanly if Pillow absent)
    shared = tmp_path / "出图" / "共享"
    (shared / "图片").mkdir(parents=True)
    (shared / "asset_registry.json").write_text(json.dumps({
        "assets": [{
            "id": "VFX_07", "type": "vfx", "name": "剑气",
            "vfx_params": {"color_target": {"h": 42, "s": 0.7, "v": 0.85}, "trail": "短"},
        }]
    }, ensure_ascii=False), encoding="utf-8")
    img = tmp_path / "出图" / "第1集" / "图片"
    img.mkdir(parents=True)
    # 三镜：两镜贴近登记金色(40/44°)，一镜窜到偏橙红(18°)→ 偏离基线 >20° 应 warn。
    _solid_png(img / "Clip_01.png", 40)
    _solid_png(img / "Clip_02.png", 44)
    _solid_png(img / "Clip_03.png", 18)
    prompt = tmp_path / "出图" / "第1集" / "prompt"
    prompt.mkdir(parents=True)
    body = "\n".join(
        f"## 镜头{i}\n**目标存档**：`出图/第1集/图片/Clip_0{i}.png`\n剑气 `VFX_07` 一闪。"
        for i in (1, 2, 3))
    (prompt / "01_分镜出图.md").write_text(body, encoding="utf-8")

    res = vc.analyze(str(tmp_path), "第1集")
    assert res["available"] is True
    assert "VFX_07" in res["groups"] and res["groups"]["VFX_07"]["measured"] == 3
    warns = [s for s in res["shots"] if s["verdict"] == "warn"]
    assert len(warns) == 1 and warns[0]["png"] == "Clip_03.png"
