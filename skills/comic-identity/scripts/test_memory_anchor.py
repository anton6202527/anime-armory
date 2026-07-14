"""memory_anchor 单测。运行：cd skills/comic-identity/scripts && python -m pytest test_memory_anchor.py"""
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).with_name("memory_anchor.py")
spec = importlib.util.spec_from_file_location("comic_memory_anchor", SCRIPT)
ma = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(ma)


REGISTRY = {"assets": {"CHAR_A": {"views": {"front": "出图/共享/图片/CHAR_A__front.png",
                                            "face": "出图/共享/图片/CHAR_A__face.png"}},
                       "CHAR_B": {"views": {}}}}


def test_gap_reappearance_triggers_pin():
    history = {"CHAR_A": [1, 5], "CHAR_C": [4, 5]}
    rows = ma.plan_rows(history, REGISTRY, target=5)
    a = next(r for r in rows if r["character_id"] == "CHAR_A")
    assert a["status"] == "ready" and len(a["pinned_refs"]) == 2
    assert any("复现间隔 4" in r for r in a["reasons"])
    # 相邻话连续出场（gap=1）不触发
    assert not any(r["character_id"] == "CHAR_C" for r in rows)


def test_missing_views_marked():
    rows = ma.plan_rows({"CHAR_B": [1, 6]}, REGISTRY, target=6)
    assert rows and rows[0]["status"] == "missing_canonical_views"


def test_first_appearance_not_flagged():
    assert ma.plan_rows({"CHAR_A": [3]}, REGISTRY, target=3) == []


def test_build_plan_and_consumption(tmp_path):
    # 端到端：写计划 → build_panel_jobs.load_memory_anchor_pins 读回
    (tmp_path / "脚本" / "第1话").mkdir(parents=True)
    (tmp_path / "脚本" / "第4话").mkdir(parents=True)
    for ch, chars in (("第1话", ["CHAR_A"]), ("第4话", ["CHAR_A"])):
        (tmp_path / "脚本" / ch / "panel_script.json").write_text(json.dumps({
            "panels": [{"panel_id": "P1", "characters": chars}]}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "出图" / "共享").mkdir(parents=True)
    (tmp_path / "出图" / "共享" / "图片").mkdir(parents=True)
    (tmp_path / "出图" / "共享" / "图片" / "CHAR_A__front.png").write_bytes(b"front")
    (tmp_path / "出图" / "共享" / "图片" / "CHAR_A__face.png").write_bytes(b"face")
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps(REGISTRY, ensure_ascii=False), encoding="utf-8")
    plan = ma.build_plan(tmp_path, "第4话")
    assert plan["summary"]["ready"] == 1
    assert plan["inputs_fingerprint"]
    assert plan["characters"][0]["pinned_refs"][0]["sha256"]
    out = ma.plan_path(tmp_path, "第4话")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

    bpj_path = Path(__file__).resolve().parents[2] / "comic-image" / "scripts" / "build_panel_jobs.py"
    spec2 = importlib.util.spec_from_file_location("bpj", bpj_path)
    bpj = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(bpj)
    pins = bpj.load_memory_anchor_pins(tmp_path, "第4话")
    assert "CHAR_A" in pins and pins["CHAR_A"][0]["role"] == "memory_anchor"
