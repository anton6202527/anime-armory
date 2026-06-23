"""色温/调色一致机检单测（cd skills/n2d-review/scripts && python -m pytest test_color_grade_consistency.py）。"""
import importlib.util
import math
import sys
from pathlib import Path


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


cg = _load("color_grade_consistency")


def test_grade_proxy_warm_cold_sign():
    warm, _ = cg.grade_proxy(200, 150, 80)   # R>B → 暖 → warmth>0
    cold, _ = cg.grade_proxy(80, 150, 200)   # B>R → 冷 → warmth<0
    assert warm > 0 and cold < 0
    _, green = cg.grade_proxy(120, 200, 120)  # G 高 → 偏绿 → tint>0
    assert green > 0


def test_grade_proxy_neutral_near_zero():
    w, t = cg.grade_proxy(128, 128, 128)
    assert abs(w) < 1e-6 and abs(t) < 1e-6


def test_analyze_flags_warm_cold_whiplash(tmp_path: Path):
    try:
        from PIL import Image
    except Exception:
        import pytest
        pytest.skip("Pillow absent")
    img = tmp_path / "出图" / "第1集" / "图片"
    img.mkdir(parents=True)

    def solid(name, rgb):
        Image.new("RGB", (40, 40), rgb).save(img / name)

    # 同一场景三镜：两镜中性，一镜强暖橙 → 暖冷代理离群应 warn。
    solid("S1_01.png", (130, 128, 126))
    solid("S1_02.png", (126, 128, 130))
    solid("S1_03.png", (210, 150, 70))
    prompt = tmp_path / "出图" / "第1集" / "prompt"
    prompt.mkdir(parents=True)
    body = "\n".join(
        f"## 镜头{i}\n**目标存档**：`出图/第1集/图片/S1_0{i}.png`\n**参考图**：场景 `定妆_冷宫寝屋`"
        for i in (1, 2, 3))
    (prompt / "01_分镜出图.md").write_text(body, encoding="utf-8")

    res = cg.analyze(str(tmp_path), "第1集")
    if not res["available"]:
        import pytest
        pytest.skip("Pillow probe false")
    warns = [s for s in res["shots"] if s["verdict"] == "warn"]
    assert any(s["png"].endswith("S1_03.png") for s in warns)
    assert all(not s["png"].endswith("S1_01.png") for s in warns)
