"""tone_light_contract 单测——契约暖冷·明暗意图解析 + 像素中位数矛盾判定 + 端到端。
cd skills/n2d-image/scripts && python3 -m pytest test_tone_light_contract.py
"""
import pytest

import tone_light_contract as tl


# ── 纯函数：意图解析 ──────────────────────────────────────────────────────────

def test_parse_intent_leading_token_wins_cool_then_warm_accent():
    # 「冷青灰压暗；残烛暖金只照脸」：冷在前=基调冷（暖金是点缀，不夺基调），压暗=dark
    intent = tl.parse_tone_intent("冷青灰压暗；残烛暖金只照脸")
    assert intent["warmth"] == "cool" and intent["brightness"] == "dark"


def test_parse_intent_warm_bright():
    intent = tl.parse_tone_intent("暖橙明亮基调，全程高调打光")
    assert intent["warmth"] == "warm" and intent["brightness"] == "bright"


def test_parse_intent_kelvin_fallback_from_light_anchor():
    # 色调基线无暖冷词 → 退到光位锚色温：3000K=暖
    intent = tl.parse_tone_intent("中性灰", "画左前 3000K 残烛暖主光")
    assert intent["warmth"] == "warm"
    # 5600K=冷
    assert tl.parse_tone_intent("中性灰", "5600K 日光")["warmth"] == "cool"


def test_parse_intent_none_when_no_signal():
    intent = tl.parse_tone_intent("某种风格", "")
    assert intent["warmth"] is None and intent["brightness"] is None


# ── 纯函数：度量 + 中位数 ─────────────────────────────────────────────────────

def test_frame_metrics_warmth_and_luma():
    m = tl.frame_metrics(200, 100, 50)
    assert m["warmth"] == 150.0                       # R−B
    assert round(m["luma"], 1) == round(0.299 * 200 + 0.587 * 100 + 0.114 * 50, 1)


def test_median():
    assert tl._median([1, 2, 3]) == 2
    assert tl._median([1, 2, 3, 4]) == 2.5
    assert tl._median([]) is None


# ── 纯函数：矛盾判定 ──────────────────────────────────────────────────────────

def test_tone_findings_cool_contract_warm_render_flags():
    intent = {"warmth": "cool", "brightness": None, "evidence": "冷青灰"}
    out = tl.tone_findings(intent, warmth_median=40.0, luma_median=120.0, n_frames=8)
    assert len(out) == 1 and out[0]["code"] == "tone_warmth_contradiction" and out[0]["level"] == "warn"


def test_tone_findings_dark_contract_bright_render_flags():
    intent = {"warmth": None, "brightness": "dark", "evidence": "压暗"}
    out = tl.tone_findings(intent, warmth_median=0.0, luma_median=180.0, n_frames=8)
    assert len(out) == 1 and out[0]["code"] == "tone_brightness_contradiction"


def test_tone_findings_silent_when_consistent_or_neutral():
    # 契约冷、渲染也冷（R−B 很负）→ 不报
    intent = {"warmth": "cool", "brightness": "dark", "evidence": "冷青灰压暗"}
    assert tl.tone_findings(intent, warmth_median=-30.0, luma_median=60.0, n_frames=8) == []
    # 中性（|R−B| 在边距内）→ 不报（宁可漏不可误杀）
    assert tl.tone_findings(intent, warmth_median=-5.0, luma_median=92.0, n_frames=8) == []


def test_tone_findings_empty_when_no_frames_or_no_median():
    intent = {"warmth": "cool", "brightness": "dark", "evidence": "x"}
    assert tl.tone_findings(intent, None, None, 0) == []
    assert tl.tone_findings(intent, 40.0, 180.0, 0) == []


# ── Pillow I/O + 端到端（缺 PIL 优雅跳过） ────────────────────────────────────

def _has_pil():
    try:
        import PIL  # noqa: F401
        return True
    except Exception:
        return False


pil = pytest.mark.skipif(not _has_pil(), reason="Pillow 不可用")


@pil
def test_measure_frame_solid_color(tmp_path):
    from PIL import Image
    p = tmp_path / "warm.png"
    Image.new("RGB", (32, 32), (210, 120, 40)).save(p)
    rgb = tl.measure_frame(str(p))
    assert rgb is not None
    r, g, b = rgb
    assert abs(r - 210) < 2 and abs(b - 40) < 2          # 纯色帧均值≈像素值


@pil
def test_analyze_flags_cool_dark_contract_against_warm_bright_frames(tmp_path):
    from PIL import Image
    root = tmp_path / "剧"
    pd = root / "出图" / "第1集" / "prompt"
    pd.mkdir(parents=True)
    (pd / "00_总览.md").write_text(
        "# 第1集\n## 本集视觉一致性契约\n- 色调基线：冷青灰压暗；残烛暖金只照脸。\n", encoding="utf-8")
    img = root / "出图" / "第1集" / "图片"
    img.mkdir(parents=True)
    for i in range(4):
        Image.new("RGB", (32, 32), (230, 180, 60)).save(img / f"Clip_{i:02d}.png")   # 暖且亮
    res = tl.analyze(root, "第1集")
    assert res["available"] and res["checked"] == 4
    codes = {f["code"] for f in res["findings"]}
    assert "tone_warmth_contradiction" in codes          # 契约冷 vs 渲染暖
    assert "tone_brightness_contradiction" in codes      # 契约压暗 vs 渲染亮


@pil
def test_analyze_silent_when_render_matches_contract(tmp_path):
    from PIL import Image
    root = tmp_path / "剧"
    pd = root / "出图" / "第1集" / "prompt"
    pd.mkdir(parents=True)
    (pd / "00_总览.md").write_text(
        "# 第1集\n## 本集视觉一致性契约\n- 色调基线：冷青灰压暗。\n", encoding="utf-8")
    img = root / "出图" / "第1集" / "图片"
    img.mkdir(parents=True)
    for i in range(4):
        Image.new("RGB", (32, 32), (40, 60, 90)).save(img / f"Clip_{i:02d}.png")     # 冷且暗
    res = tl.analyze(root, "第1集")
    assert res["available"] and res["findings"] == []


def test_analyze_available_true_no_intent_when_contract_has_no_tone(tmp_path):
    root = tmp_path / "剧"
    pd = root / "出图" / "第1集" / "prompt"
    pd.mkdir(parents=True)
    (pd / "00_总览.md").write_text(
        "# 第1集\n## 本集视觉一致性契约\n- 色调基线：某种说不清的风格。\n", encoding="utf-8")
    res = tl.analyze(root, "第1集")
    assert res["available"] and res["checked"] == 0 and res["findings"] == []
