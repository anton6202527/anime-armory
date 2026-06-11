"""inherit_contract.py 回归测试——出图→出视频 视觉契约继承 Diff。

cd skills/n2d-video/scripts && python3 -m pytest test_inherit_contract.py
构造临时项目验证：一致→pass；轴线被改→block；视频缺字段→block；视频细化超集→pass；
色调漂移→warn 不拦；出图侧缺字段→提示不拦。格式按 demo
（制漫剧/本宫才是这皇宫最大的妖/出图/第1集/prompt/00_总览.md）的短标签 bullet 校准。
"""
import json
import os

import inherit_contract as ic

EP = "第1集"

# 出图侧契约（短标签，与 demo / gate.py --stage image 一致）
IMG_CONTRACT = """# 第1集 — 出图总览

## 本集视觉一致性契约
- 色调基线：冷青灰压暗；残烛暖金只照脸。
- 光位锚：冷宫寝殿=画左前 3000K 残烛暖主光；画右后冷月背光。
- 轴线：守床榻到门口横轴；沈念画左看画右，柳娘子画右看画左。
- 状态演进：沈念 Clip01-13 黑瞳常态；Clip14 起左腕疤裂暗金。
- 景别阶梯：LS建制 -> CU铜镜 -> MCU对峙 -> ECU金瞳。

## 其它段
- 无关内容
"""

# 视频侧逐字誊抄（长标签写法也应被认出）
VID_VERBATIM = """# 第1集 — 出视频总览

## 本集导演一致性契约
- 主色调：冷青灰压暗。
- 镜头语法：铺垫慢推。
- 轴线：守床榻到门口横轴。
- 剧情状态锁：金瞳不得提前。
- 场景状态：残烛常亮。

## 本集视觉一致性契约
- 色调基线：冷青灰压暗；残烛暖金只照脸。
- 场景光位锚：冷宫寝殿=画左前 3000K 残烛暖主光；画右后冷月背光。
- 场景轴线视线：守床榻到门口横轴；沈念画左看画右，柳娘子画右看画左。
- 角色状态演进：沈念 Clip01-13 黑瞳常态；Clip14 起左腕疤裂暗金。
- 景别阶梯：LS建制 → CU铜镜 → MCU对峙 → ECU金瞳。
"""


def _write_project(tmp_path, img_text, vid_text):
    root = tmp_path / "剧"
    for sub, text in (("出图", img_text), ("出视频", vid_text)):
        d = root / sub / EP / "prompt"
        d.mkdir(parents=True, exist_ok=True)
        (d / "00_总览.md").write_text(text, encoding="utf-8")
    return str(root)


def _report(root):
    p = os.path.join(root, "生产数据", f"contract_inheritance_{EP}.json")
    assert os.path.isfile(p), "必须落 JSON 报告"
    assert os.path.isfile(p[:-5] + ".md"), "必须落 MD 报告"
    return json.load(open(p, encoding="utf-8"))


def test_identical_contract_passes(tmp_path):
    # 逐字一致（标点/箭头/标签长短写差异归一化后不算漂移）→ exit 0 全 pass
    root = _write_project(tmp_path, IMG_CONTRACT, VID_VERBATIM)
    assert ic.run(root, EP) == 0
    rep = _report(root)
    assert rep["verdict"] == "pass"
    assert rep["summary"]["block"] == 0 and rep["summary"]["warn"] == 0
    assert {r["field"] for r in rep["fields"]} == set(ic.VISUAL_CONTRACT_FIELDS)


def test_axis_rewritten_blocks(tmp_path):
    # 轴线被誊抄改错（左右互换）→ block, exit 1
    vid = VID_VERBATIM.replace(
        "- 场景轴线视线：守床榻到门口横轴；沈念画左看画右，柳娘子画右看画左。",
        "- 场景轴线视线：守床榻到门口横轴；沈念画右看画左，柳娘子画左看画右。")
    root = _write_project(tmp_path, IMG_CONTRACT, vid)
    assert ic.run(root, EP) == 1
    rep = _report(root)
    assert rep["verdict"] == "block"
    axis = next(r for r in rep["fields"] if r["field"] == "场景轴线视线")
    assert axis["status"] == "block_drift" and axis["severity"] == "block"


def test_video_missing_field_blocks(tmp_path):
    # 视频侧契约丢了景别阶梯 → block, exit 1
    vid = "\n".join(ln for ln in VID_VERBATIM.splitlines() if not ln.startswith("- 景别阶梯"))
    root = _write_project(tmp_path, IMG_CONTRACT, vid)
    assert ic.run(root, EP) == 1
    rep = _report(root)
    ladder = next(r for r in rep["fields"] if r["field"] == "景别阶梯")
    assert ladder["status"] == "block_missing_in_video"


def test_video_missing_section_blocks(tmp_path):
    # 视频侧整节没誊抄（只有导演一致性契约，不可替代）→ 五字段全 block
    vid = VID_VERBATIM.split("## 本集视觉一致性契约")[0]
    root = _write_project(tmp_path, IMG_CONTRACT, vid)
    assert ic.run(root, EP) == 1
    rep = _report(root)
    assert all(r["severity"] == "block" for r in rep["fields"])


def test_video_refined_superset_passes(tmp_path):
    # 视频侧有意收紧/细化（包含出图侧原文 + 追加运动落地约束）→ pass_superset, exit 0
    vid = VID_VERBATIM.replace(
        "- 场景光位锚：冷宫寝殿=画左前 3000K 残烛暖主光；画右后冷月背光。",
        "- 场景光位锚：冷宫寝殿=画左前 3000K 残烛暖主光；画右后冷月背光。运镜中烛光只许摇曳不许改向，Clip14 后允许暗金补光。")
    root = _write_project(tmp_path, IMG_CONTRACT, vid)
    assert ic.run(root, EP) == 0
    rep = _report(root)
    anchor = next(r for r in rep["fields"] if r["field"] == "场景光位锚")
    assert anchor["status"] == "pass_superset" and rep["verdict"] == "pass"


def test_tone_drift_warns_not_blocks(tmp_path):
    # 色调基线改写（非光位/轴线）→ warn，exit 0 不拦
    vid = VID_VERBATIM.replace(
        "- 色调基线：冷青灰压暗；残烛暖金只照脸。",
        "- 色调基线：暖橙明亮基调，全程高调打光。")
    root = _write_project(tmp_path, IMG_CONTRACT, vid)
    assert ic.run(root, EP) == 0
    rep = _report(root)
    tone = next(r for r in rep["fields"] if r["field"] == "色调基线")
    assert tone["status"] == "warn_drift" and rep["verdict"] == "warn"


def test_upstream_missing_field_warns_not_blocks(tmp_path):
    # 出图侧本来就缺状态演进 → 提示但不拦（上游问题）；视频侧多写不构成 block
    img = "\n".join(ln for ln in IMG_CONTRACT.splitlines() if not ln.startswith("- 状态演进"))
    root = _write_project(tmp_path, img, VID_VERBATIM)
    assert ic.run(root, EP) == 0
    rep = _report(root)
    state = next(r for r in rep["fields"] if r["field"] == "角色状态演进")
    assert state["status"] == "upstream_missing" and state["severity"] == "warn"


def test_missing_files_precondition(tmp_path):
    # 任一侧 00_总览 不存在 → exit 2（前置缺失，区别于契约漂移）
    root = str(tmp_path / "空剧")
    os.makedirs(os.path.join(root, "出图", EP, "prompt"), exist_ok=True)
    assert ic.run(root, EP) == 2  # 两侧都缺（出图文件没写）
    open(os.path.join(root, "出图", EP, "prompt", "00_总览.md"), "w", encoding="utf-8").write(IMG_CONTRACT)
    assert ic.run(root, EP) == 2  # 只缺视频侧
