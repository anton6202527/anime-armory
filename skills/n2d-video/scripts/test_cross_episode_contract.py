"""跨集视觉契约一致性测试（⑦）。

跑法：cd skills/n2d-video/scripts && python3 -m pytest test_cross_episode_contract.py
"""
import json
import os

import cross_episode_contract as ce  # 设置 _lib sys.path
import n2d_cross_episode as cx


# ── 纯函数 ───────────────────────────────────────────────────────
def test_light_side():
    assert cx.light_side("冷宫寝殿=左侧光，强对比") == "L"
    assert cx.light_side("冷宫寝殿=右侧光") == "R"
    assert cx.light_side("强对比冷月光，无环境散光") is None      # 无左右 → 不猜
    assert cx.light_side("左侧光与右侧光并存") is None            # 同现冲突 → 不猜


def test_axis_dir():
    assert cx.axis_dir("冷宫寝殿沿地面 画左 -> 画右 侧身移动") == ("左", "右")
    assert cx.axis_dir("画右→画左") == ("右", "左")
    assert cx.axis_dir("人物居中正面，无横移") is None


def test_detect_light_inversion_only_same_scene():
    scenes = ["冷宫寝殿", "御花园"]
    prev = "冷宫寝殿=左侧光；御花园=右侧光"
    cur = "冷宫寝殿=右侧光；御花园=右侧光"
    w = cx.detect_inversions(prev, cur, scenes, "light")
    # 冷宫寝殿 L→R 反转命中；御花园 R→R 不报
    assert len(w) == 1 and w[0]["scene"] == "冷宫寝殿"


def test_detect_no_false_positive_across_different_scenes():
    # 第1集冷宫画左、第2集御花园画右 = 不同地点，不该误报
    scenes = ["冷宫寝殿", "御花园"]
    assert cx.detect_inversions("冷宫寝殿=左侧光", "御花园=右侧光", scenes, "light") == []


def test_detect_axis_inversion():
    scenes = ["冷宫寝殿"]
    w = cx.detect_inversions("冷宫寝殿 画左 -> 画右", "冷宫寝殿 画右 -> 画左", scenes, "axis")
    assert len(w) == 1 and w[0]["kind"] == "axis"


def test_field_similarity():
    assert cx.field_similarity("冷青灰压暗", "冷青灰压暗") == 1.0
    assert cx.field_similarity("冷青灰", "暖金亮") < 0.3
    assert cx.field_similarity("", "") == 1.0


def test_cross_episode_diff_warns_only_on_inversion():
    prev = "## 本集视觉一致性契约\n- 光位锚：冷宫寝殿=左侧光\n- 轴线：冷宫寝殿 画左 -> 画右\n"
    cur = "## 本集视觉一致性契约\n- 光位锚：冷宫寝殿=右侧光\n- 轴线：冷宫寝殿 画左 -> 画右\n"
    d = cx.cross_episode_diff(prev, cur, ["冷宫寝殿"], "第1集", "第2集")
    assert d["summary"]["light_inversions"] == 1
    assert d["summary"]["axis_inversions"] == 0
    assert len(d["fields"]) == 5


# ── CLI ───────────────────────────────────────────────────────────
SECTION = ("## 本集视觉一致性契约\n- 色调基线：冷青灰压暗\n- 光位锚：冷宫寝殿={light}\n"
           "- 轴线：冷宫寝殿 画左 -> 画右\n- 状态演进：沈念常态\n- 景别阶梯：CU->MCU\n")


def _write_overview(root, ep, light):
    d = os.path.join(root, "出图", ep, "prompt")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "00_总览.md"), "w", encoding="utf-8").write(SECTION.format(light=light))


def _write_assets(root):
    d = os.path.join(root, "出图", "共享")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "asset_registry.json"), "w", encoding="utf-8").write(
        json.dumps({"assets": [{"id": "LOC_01", "name": "冷宫寝殿"}]}, ensure_ascii=False))


def test_cli_flags_cross_episode_light_inversion(tmp_path):
    root = str(tmp_path / "剧")
    _write_overview(root, "第1集", "左侧光")
    _write_overview(root, "第2集", "右侧光")
    _write_assets(root)

    rc = ce.run(root, "第2集")
    assert rc == 0  # advisory：不退非零
    rep = json.load(open(os.path.join(root, "生产数据", "cross_episode_contract_第2集.json"), encoding="utf-8"))
    assert rep["prev_episode"] == "第1集"
    assert rep["summary"]["light_inversions"] == 1
    assert os.path.isfile(os.path.join(root, "生产数据", "cross_episode_contract_第2集.md"))


def test_cli_first_episode_skips(tmp_path):
    root = str(tmp_path / "剧")
    _write_overview(root, "第1集", "左侧光")
    _write_assets(root)

    assert ce.run(root, "第1集") == 0
    rep = json.load(open(os.path.join(root, "生产数据", "cross_episode_contract_第1集.json"), encoding="utf-8"))
    assert rep["prev_episode"] == "" and rep["summary"]["warnings"] == 0


def test_cli_missing_overview_errors(tmp_path):
    root = str(tmp_path / "剧")
    assert ce.run(root, "第2集") == 2
