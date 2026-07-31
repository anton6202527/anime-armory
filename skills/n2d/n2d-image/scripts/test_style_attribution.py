"""style_attribution 单测——style_contract 解析 + 风格指纹距离 + 归属 findings + 端到端降级。
cd skills/n2d/n2d-image/scripts && python3 -m pytest test_style_attribution.py
"""
import json
from pathlib import Path

import style_attribution as sa


# ── 纯函数：style_contract 解析 ────────────────────────────────────────────────

def test_parse_intent_list_taboo_and_list_anchor():
    sc = {
        "风格名": "国漫写实角色审美 + 电影级布光",
        "风格禁忌": ["欧美脸漂移", "插画化", "页游塑料盔甲"],
        "style_anchor": ["出图/共享/图片/定妆_风格锚_1.png", "出图/共享/图片/定妆_风格锚_2.png"],
    }
    intent = sa.parse_style_intent(sc)
    assert intent["style_name"].startswith("国漫写实")
    assert intent["taboos"] == ["欧美脸漂移", "插画化", "页游塑料盔甲"]
    assert len(intent["anchors"]) == 2


def test_parse_intent_string_taboo_and_string_anchor():
    sc = {"风格名": "二次元赛璐璐", "风格禁忌": "欧美脸、塑料感；过度磨皮", "style_anchor": "出图/共享/图片/锚.png"}
    intent = sa.parse_style_intent(sc)
    assert intent["taboos"] == ["欧美脸", "塑料感", "过度磨皮"]
    assert intent["anchors"] == ["出图/共享/图片/锚.png"]


def test_parse_intent_empty_when_no_style_name():
    assert sa.parse_style_intent({})["style_name"] == ""


# ── 纯函数：指纹距离（max 维归一） ──────────────────────────────────────────────

def test_fingerprint_distance_max_dim_normalized():
    a = {"sat": 100.0, "contrast": 120.0, "edge": 30.0}
    b = {"sat": 100.0, "contrast": 120.0, "edge": 30.0}
    assert sa.fingerprint_distance(a, b) == 0.0
    # 仅边缘维偏离一个 EDGE_SCALE → 距离≈1.0（取 max）
    c = dict(a); c["edge"] = 30.0 + sa.EDGE_SCALE
    assert abs(sa.fingerprint_distance(c, a) - 1.0) < 1e-6


def test_fingerprint_distance_none_when_missing():
    assert sa.fingerprint_distance(None, {"sat": 1, "contrast": 1, "edge": 1}) is None


def test_median_fingerprint():
    fps = [{"sat": 10, "contrast": 20, "edge": 5}, {"sat": 30, "contrast": 40, "edge": 15},
           {"sat": 20, "contrast": 30, "edge": 10}]
    assert sa.median_fingerprint(fps) == {"sat": 20.0, "contrast": 30.0, "edge": 10.0}


# ── 纯函数：findings 判定 ──────────────────────────────────────────────────────

def test_findings_anchor_missing_degrades_to_human_checklist():
    intent = {"style_name": "国漫写实", "taboos": ["欧美脸漂移", "插画化"], "anchors": []}
    fs = sa.style_findings(intent, None, None, 0, "missing")
    assert len(fs) == 1 and fs[0]["code"] == "style_anchor_missing" and fs[0]["level"] == "block"
    assert "欧美脸漂移" in fs[0]["msg"]  # 人判清单列出禁忌


def test_findings_no_style_name_stays_silent():
    # 无风格名 → 存在性归 preflight gate，这里不双报
    assert sa.style_findings({"style_name": ""}, {"sat": 1, "contrast": 1, "edge": 1},
                             {"sat": 99, "contrast": 99, "edge": 99}, 5, "ok") == []


def test_findings_episode_drift_flags_warn():
    intent = {"style_name": "国漫写实", "taboos": ["插画化"], "anchors": ["a.png"]}
    anchor = {"sat": 90.0, "contrast": 130.0, "edge": 28.0}
    # 本集饱和度爆高一个多 SAT_SCALE → 偏离 ≥ 阈值
    episode = {"sat": 90.0 + sa.SAT_SCALE + 5, "contrast": 130.0, "edge": 28.0}
    fs = sa.style_findings(intent, anchor, episode, 12, "ok")
    assert len(fs) == 1 and fs[0]["code"] == "style_attribution_drift" and fs[0]["level"] == "warn"
    assert "饱和度" in fs[0]["msg"]


def test_findings_within_threshold_silent():
    intent = {"style_name": "国漫写实", "taboos": [], "anchors": ["a.png"]}
    anchor = {"sat": 90.0, "contrast": 130.0, "edge": 28.0}
    episode = {"sat": 95.0, "contrast": 135.0, "edge": 29.0}  # 各维都在尺度内
    assert sa.style_findings(intent, anchor, episode, 12, "ok") == []


# ── 端到端：无 storyboard / 无锚 降级 ──────────────────────────────────────────

def _write_storyboard(root: Path, style_contract):
    p = root / "脚本" / "第1集" / "storyboard.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"style_contract": style_contract}, ensure_ascii=False), encoding="utf-8")


def test_analyze_no_style_name_available_but_silent(tmp_path):
    _write_storyboard(tmp_path, {})  # 无风格名
    res = sa.analyze(tmp_path, "第1集")
    assert res["available"] is True and res["findings"] == []


def test_analyze_anchor_missing_emits_human_checklist(tmp_path):
    _write_storyboard(tmp_path, {"风格名": "国漫写实", "风格禁忌": ["插画化"]})  # 有风格名无锚
    res = sa.analyze(tmp_path, "第1集")
    assert res["available"] is True
    assert res["anchor_status"] == "missing"
    assert res["findings"][0]["code"] == "style_anchor_missing"


def test_analyze_uses_style_anchor_registry_fallback(tmp_path):
    anchor_rel = "出图/共享/图片/风格锚_冷灰写实3D国风漫剧.png"
    _solid_png(tmp_path / anchor_rel, (90, 90, 95))
    _write_storyboard(tmp_path, {"风格名": "国漫写实", "风格禁忌": ["插画化"]})
    reg = tmp_path / "出图" / "共享" / "style_anchor_registry.json"
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(json.dumps({
        "kind": "n2d_style_anchor_registry",
        "selected_anchor": {"path": anchor_rel, "status": "ready"},
    }, ensure_ascii=False), encoding="utf-8")

    res = sa.analyze(tmp_path, "第1集")

    assert res["anchor_status"] == "ok"
    assert res["intent"]["anchors"] == [anchor_rel]
    assert res["intent"]["anchor_source"] == str(sa.STYLE_ANCHOR_REGISTRY)


def test_analyze_anchor_registered_but_file_absent(tmp_path):
    _write_storyboard(tmp_path, {"风格名": "国漫写实", "style_anchor": ["出图/共享/图片/缺.png"]})
    res = sa.analyze(tmp_path, "第1集")
    assert res["anchor_status"] == "files_missing"
    assert res["findings"][0]["code"] == "style_anchor_file_missing"
    assert res["findings"][0]["level"] == "block"


def _solid_png(path: Path, rgb):
    pytest = __import__("pytest")
    Image = pytest.importorskip("PIL.Image", reason="Pillow not installed")
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (96, 96), rgb).save(path)


def test_measure_fingerprint_real_pixels(tmp_path):
    p = tmp_path / "x.png"
    _solid_png(p, (200, 40, 40))  # 高饱和红
    fp = sa.measure_fingerprint(str(p))
    assert fp is not None and set(fp) == {"sat", "contrast", "edge"}
    assert fp["sat"] > 150  # 鲜红 → 高饱和


def test_analyze_end_to_end_flags_drift_on_real_images(tmp_path):
    # 锚=高饱和；本集帧=近灰（低饱和）→ 整集饱和度指纹远离锚 → warn drift
    anchor_rel = "出图/共享/图片/定妆_风格锚_1.png"
    _solid_png(tmp_path / anchor_rel, (210, 30, 30))
    _write_storyboard(tmp_path, {"风格名": "二次元赛璐璐", "风格禁忌": ["写实粗粝"],
                                 "style_anchor": [anchor_rel]})
    for i in range(3):
        _solid_png(tmp_path / "出图" / "第1集" / "图片" / f"镜头{i}.png", (128, 126, 130))  # 近灰
    res = sa.analyze(tmp_path, "第1集")
    assert res["available"] is True and res["checked"] == 3
    assert res["anchor_status"] == "ok"
    codes = [f["code"] for f in res["findings"]]
    assert "style_attribution_drift" in codes
