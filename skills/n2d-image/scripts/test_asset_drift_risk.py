"""asset_drift_risk 单测——评分纯函数 + 端到端 analyze。

cd skills/n2d-image/scripts && python3 -m pytest test_asset_drift_risk.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).with_name("asset_drift_risk.py")
spec = importlib.util.spec_from_file_location("asset_drift_risk", SCRIPT)
adr = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(adr)


def test_reuse_base() -> None:
    assert adr.reuse_base("第1集起复用") == adr.WEIGHTS["reuse_high"]
    assert adr.reuse_base("全篇贯穿") == adr.WEIGHTS["reuse_high"]
    assert adr.reuse_base("第1集核心道具") == adr.WEIGHTS["reuse_single"]   # 无复用词 → 单集底分
    assert adr.reuse_base("") == adr.WEIGHTS["reuse_single"]


def test_score_high_reuse_multiform_is_high() -> None:
    s = adr.score_asset({"reuse_base": 25, "appear": 6, "drift_forbidden": 5,
                         "has_structure": True, "has_color": True, "has_multiform": True})
    assert s["band"] == "high"
    assert s["score"] >= adr.BAND_HIGH
    assert s["drivers"][0]["points"] >= s["drivers"][-1]["points"]   # 按贡献降序


def test_score_single_use_low() -> None:
    s = adr.score_asset({"reuse_base": 6, "appear": 1, "drift_forbidden": 1,
                         "has_structure": False, "has_color": False, "has_multiform": False})
    assert s["band"] == "low"


def test_suggestions_color_and_multiform() -> None:
    scored = {"band": "high"}
    sig = {"scope": "第3集起复用", "appear": 4, "has_structure": True, "has_color": True, "has_multiform": True}
    sug = adr.suggestions_for("vfx", scored, sig)
    joined = " ".join(sug)
    assert "颜色" in joined and "多形态" in joined
    assert any("共享定妆库" in s for s in sug)   # 高复用提示进共享库


def _make_project(tmp_path: Path) -> Path:
    root = tmp_path / "剧"
    reg = root / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "asset_registry.json").write_text(json.dumps({"assets": [
        {"id": "LOC_01", "type": "scene", "name": "冷宫寝殿", "scope": "第1集起复用",
         "constraints": {"layout": "...", "axis": "...", "light_anchor": "..."},
         "drift_forbidden": ["layout", "axis", "light_direction", "era_style", "structure"]},
        {"id": "VFX_01", "type": "vfx", "name": "暗金妖力脉冲", "scope": "第3集起妖力视觉",
         "constraints": {"structure": "...", "color": "..."},
         "drift_forbidden": ["color", "trail", "glow"], "forms": [{"id": "lv1"}, {"id": "lv2"}]},
        {"id": "PROP_09", "type": "prop", "name": "一次性信物", "scope": "第1集单镜",
         "constraints": {"structure": "..."}, "drift_forbidden": ["shape"]},
    ]}, ensure_ascii=False), encoding="utf-8")
    sb = root / "脚本" / "第1集"
    sb.mkdir(parents=True)
    (sb / "storyboard.json").write_text(json.dumps({"clips": [
        {"label": "冷宫寝殿建制", "scene": "冷宫寝殿/夜",
         "shots": [{"desc": "冷宫寝殿内，暗金妖力脉冲乍现"}]},
        {"label": "对峙", "scene": "冷宫寝殿",
         "shots": [{"desc": "冷宫寝殿，暗金妖力脉冲扩散"}]},
        {"label": "信物", "scene": "庭院", "shots": [{"desc": "一次性信物递出"}]},
    ]}, ensure_ascii=False), encoding="utf-8")
    return root


def test_analyze_end_to_end(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    rep = adr.analyze(root, "第1集")
    by = {r["id"]: r for r in rep["assets"]}
    # LOC_01 高复用 + 高频 + 5禁漂 → high
    assert by["LOC_01"]["band"] == "high"
    assert by["LOC_01"]["signals"]["appear"] == 2
    # VFX_01 多形态 + 颜色锁 → high
    assert by["VFX_01"]["band"] == "high"
    assert by["VFX_01"]["signals"]["has_multiform"] is True
    # PROP_09 单镜单用 → low
    assert by["PROP_09"]["band"] == "low"
    # 排序：分高在前
    assert rep["assets"][0]["score"] >= rep["assets"][-1]["score"]


def test_run_writes_reports(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    rep = adr.run(root, "第1集")
    assert Path(rep["json_path"]).is_file()
    assert "物料漂移风险" in Path(rep["markdown_path"]).read_text(encoding="utf-8")
