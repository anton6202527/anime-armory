#!/usr/bin/env python3
"""Tests for midstart_context.py.

Run from this script's own directory:
    cd skills/n2d/n2d-script/scripts && python -m pytest test_midstart_context.py
"""
import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import midstart_context as M  # noqa: E402


def _root():
    return Path(tempfile.mkdtemp())


def test_scaffold_creates_pack_and_blocks_placeholders():
    root = _root()
    path = M.scaffold(root, "第48章", "第45-52章", "", force=False)
    assert path.exists()
    assert "目标起点：第48章" in path.read_text(encoding="utf-8")
    report = M.check(root)
    assert report["verdict"] == "block"
    assert any(f["code"] == "unfilled_field" for f in report["findings"])


def test_completed_pack_passes_with_no_character_warn_after_card_exists():
    root = _root()
    M.scaffold(root, "第48章", "第45-52章", "", force=False)
    path = M.pack_path(root)
    text = path.read_text(encoding="utf-8")
    replacements = {
        "【待补：为什么从这里开始做，是否用于打样/爆点/投放测试】": "从第48章大反转做爆点打样",
        "【待补：常态年龄、脸型五官、发型、服装、配色、身份阶层；不得混入当前章节临时伤/泪/觉醒态】": "沈念常态，十八岁，凤眼薄唇，乌黑半披发，月白旧宫装",
        "【待补：本窗口开始时主角身上已有的伤、服装、觉醒态、战损、境界外显等；无则写无】": "左颊新伤，未觉醒金瞳",
        "【待补：3-5 个绝不能漂的识别锚点，如凤眼薄唇/半披黑发/月白旧宫装/左腕淡疤】": "凤眼薄唇；半披黑发；月白旧宫装；左腕淡疤",
        "【待补：等级、系统数值、武器/法宝、能力限制；无体系则写无】": "筑基初期，系统积分 120，禁用高阶法术",
        "【待补：与男主/反派/同伴/家族/宗门/系统的关系温度与敌友状态】": "与王敦敌对；与系统互相试探",
        "【待补：按 章节/集 -> 角色 -> 变化 -> 定妆动作 列出；无则写无】": "第30章沈念入冷宫，常态定妆沿用",
        "【待补：哪些角色会换装、觉醒、受伤、变体、年龄跳；无则写无】": "第50章金瞳觉醒，需新建觉醒态",
        "【待补：哪些形态要先建常态定妆，哪些要建当前形态/变体定妆】": "先建常态与觉醒态两个形态",
        "【待补：压缩到 300-800 字，说明到目标起点前主角经历、关键选择、当前处境】": "沈念被废后入冷宫，发现系统只在危机时响应。她已确认王敦篡改宫册，但尚无证据。",
        "【待补：目标起点这一段主角想要什么】": "拿到宫册原件并活过夜审",
        "【待补：目标起点这一段谁阻拦/什么危机/什么误会或谜团】": "王敦派人逼供，系统规则半露",
        "【待补：观众需要知道但本窗口不能提前泄露的伏笔、真相、系统规则；无则写无】": "系统真实宿主不能提前泄露",
        "【待补：列出本窗口会出现的具名角色，说明已建卡路径或待建卡摘要】": "沈念、王敦、柳娘子；角色卡见 characters/",
        "【待补：列出本窗口会出现的主场景，说明已建卡路径或待建卡摘要】": "冷宫寝殿、夜审大殿",
        "【待补：列出武器、法宝、证物、系统面板、特效 VFX；无则写无】": "宫册原件、VFX_系统面板",
        "【待补：目标起点前一幕停在哪里，人物姿态/情绪/信息状态是什么】": "沈念听见门锁响，仍不知道王敦亲临",
        "【待补：0-3 秒能抓人的画面/台词/危机；不是过渡交代】": "门锁断裂，王敦一句“她还活着？”",
        "【待补：本次制作窗口末端准备断在哪里，下一集怎么起】": "断在金瞳亮起前一瞬，下一集冷开场觉醒",
        "【待补：保留 / 并入前集 / 并入后集 / 前后挪段；写原因】": "保留第48章开头，后挪半段到第49章，保证冷开场",
        "【待补：可以从该起点开工 / 先补第X章前情 / 先建定妆变体 / 先调整边界】": "可以从该起点开工，先建常态与觉醒态定妆",
        "【待补：例如主角当前形态易污染常态定妆、关系反转不能提前剧透、战力状态需锁等；无则写无】": "当前伤痕是剧情状态，不写入常态定妆",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    cdir = root / "设定库" / "characters"
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / "沈念.md").write_text("# 角色卡 — 沈念\n- 锚点句：凤眼薄唇\n", encoding="utf-8")
    (cdir / "_生命周期.md").write_text("# 生命周期\n| 集 | 角色 | 形象变化 | 定妆动作 |\n", encoding="utf-8")
    report = M.check(root)
    assert report["verdict"] == "pass"
    assert report["findings"] == []


def test_missing_pack_is_block():
    report = M.check(_root())
    assert report["verdict"] == "block"
    assert report["findings"][0]["code"] == "missing_midstart_pack"


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-q"]))
