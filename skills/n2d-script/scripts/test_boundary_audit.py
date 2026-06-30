#!/usr/bin/env python3
"""Tests for boundary_audit.py series-arc + genre-aware lexicon.

Run from this script's own directory:
    cd skills/n2d-script/scripts && python -m pytest test_boundary_audit.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "boundary_audit.py")
COMMON = os.path.abspath(os.path.join(HERE, "..", "..", "n2d", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

import n2d_const as C  # noqa: E402


def _mk_work(eps, settings=""):
    d = tempfile.mkdtemp()
    for i, body in enumerate(eps, 1):
        ep = Path(d) / "脚本" / f"第{i}集"
        ep.mkdir(parents=True)
        (ep / "raw.txt").write_text(body, encoding="utf-8")
    if settings:
        (Path(d) / "_设置.md").write_text(settings, encoding="utf-8")
    return d


def _mark_main_nodes_source(root):
    src = Path(root) / "小说"
    src.mkdir(parents=True, exist_ok=True)
    (src / "_源指纹.json").write_text(
        json.dumps({"kind": "n2d_source_fingerprint", "version": 1, "source_kind": "main_nodes_txt"}, ensure_ascii=False),
        encoding="utf-8",
    )


def _run_json(root, *extra):
    out = subprocess.run([sys.executable, SCRIPT, root, "--json", *extra],
                         capture_output=True, text=True)
    return json.loads(out.stdout)


# ── 题材词典（Gap3）─────────────────────────────────────────────
def test_lexicon_default_backward_compatible():
    s, c, p = C.boundary_lexicon(None)
    assert "刀" in c and "突破" in p          # 历史古装覆盖保留
    assert "心动" not in p and "真凶" not in p  # 默认不含女频/悬疑


def test_lexicon_female_genre_adds_emotion_words():
    _, c, p = C.boundary_lexicon("自定义:甜宠言情")
    assert "误会" in c and "吃醋" in c
    assert "告白" in p and "心动" in p


def test_lexicon_suspense_adds_clue_words():
    _, c, p = C.boundary_lexicon("悬疑推理")
    assert "凶手" in c and "真凶" in p


# ── 剧级追更骨架（Gap1）─────────────────────────────────────────
def test_weak_cluster_and_no_loop_detected():
    eps = [
        "第一章\n沈念睁眼穿越，门外脚步逼近，竟是死去的兄长归来！",     # 强 + 闭环
        "第二章\n她走进大殿，环顾四周，缓缓坐下，端起茶，",            # 软断·弱钩·无闭环
        "第三章\n夜深了，她在灯下回忆往事，叹气，风声呜咽，",          # 软断·弱钩·无闭环
    ]
    root = _mk_work(eps, "题材: 宫斗\n变现模式: 免费\n")
    data = _run_json(root)
    arc = data["series_arc"]
    assert [2, 3] in arc["weak_clusters"]  # JSON tuples → lists
    assert 2 in arc["no_closed_loop"] and 3 in arc["no_closed_loop"]
    assert arc["strength_dist"]["弱"] == 2


def test_paid_mode_flags_weak_payment_wall():
    # 10 集，第 8/10 集弱钩 → 付费模式应把它们标为卡点偏弱
    eps = ["第%d章\n冲突逼问，她反击震住全场，原来另有隐情！" % i for i in range(1, 11)]
    eps[7] = "第8章\n他们坐下喝茶聊天，气氛缓和，散去，"   # 第8集软断弱钩
    eps[9] = "第10章\n众人散场，各自回房休息，夜色沉沉，"  # 第10集软断弱钩
    root = _mk_work(eps, "题材: 宫斗\n变现模式: 付费\n")
    data = _run_json(root)
    arc = data["series_arc"]
    assert 8 in arc["cliffhanger_targets"] and 10 in arc["cliffhanger_targets"]
    assert any("卡点集" in i for i in arc["issues"])


def test_free_mode_sets_no_payment_wall():
    eps = ["第%d章\n冲突逼问反击震住，反转！" % i for i in range(1, 11)]
    root = _mk_work(eps, "变现模式: 免费\n")
    data = _run_json(root)
    assert data["series_arc"]["cliffhanger_targets"] == []


def test_two_sided_boundary_pair_flags_slow_next_opening():
    eps = [
        "第一章\n沈念发现真相，拔剑反击柳娘子！",
        "第二章\n翌日，她坐在窗边回忆往事，慢慢喝茶，风声很轻。",
    ]
    root = _mk_work(eps, "题材: 宫斗\n变现模式: 免费\n")
    data = _run_json(root)
    pairs = data["series_arc"]["boundary_pairs"]
    assert pairs[0]["from"] == 1 and pairs[0]["to"] == 2
    assert pairs[0]["risk"]
    assert "下集开场弱" in pairs[0]["weakness"]


# ── 视觉奇观放置初筛（report-only·北极星看点④）──────────────────
def test_spectacle_split_boundary_detected():
    eps = [
        "第一章\n沈念催动法诀，天劫雷云压顶，第一道天雷轰然劈下，渡劫开始！",  # 尾含奇观
        "第二章\n天劫继续，九道神雷接连轰落，她浴雷而立，终于渡劫成功飞升！",  # 头含奇观
    ]
    root = _mk_work(eps, "题材: 修仙\n变现模式: 免费\n")
    sp = _run_json(root)["series_arc"]["spectacle"]
    assert [1, 2] in sp["split_boundary"]
    assert any("劈成两半" in i for i in sp["issues"])


def test_spectacle_weak_anchor_flagged_on_soft_end():
    eps = [
        "第一章\n万人观礼，大军压境决战在即，她一剑斩敌震慑全场，原来早有埋伏！",  # 强尾·奇观集
        "第二章\n登基大典之上众臣朝拜，她缓缓走向龙椅，回望群臣，端起酒杯，",        # 软断弱钩·奇观集
    ]
    root = _mk_work(eps, "题材: 修仙\n变现模式: 免费\n")
    sp = _run_json(root)["series_arc"]["spectacle"]
    assert 2 in sp["weak_anchor"] and 1 not in sp["weak_anchor"]
    assert any("断点偏弱" in i for i in sp["issues"])


def test_no_spectacle_no_issue():
    eps = ["第%d章\n她冷笑反击，逼问对方，对方哑口无言，原来如此！" % i for i in range(1, 4)]
    root = _mk_work(eps, "变现模式: 免费\n")
    sp = _run_json(root)["series_arc"]["spectacle"]
    assert sp["spectacle_eps"] == [] and sp["issues"] == []


def test_main_node_source_uses_explicit_hook_and_beats_as_boundary_evidence():
    eps = [
        "# 第1集 冷宫赐死，妖血觉醒\n\n"
        "源章：01-03\n\n"
        "沈念醒来发现自己顶着林婉儿的脸，被赐毒酒，又被冷宫妖物柳娘子逼到死角。\n\n"
        "必保节点：错脸醒来；毒酒赐死；柳娘子逼杀；吞妖觉醒。\n\n"
        "结尾钩子：冷宫有妖，本宫最大。\n\n"
        "n2d 要点：先锁身份定妆。",
        "# 第2集 冷宫立规矩\n\n"
        "源章：04-08\n\n"
        "沈念把收租妖物和御膳房妖油串成证据链。\n\n"
        "必保节点：收租妖物；冷宫规矩；半份证据送御前。\n\n"
        "结尾钩子：皇帝收到证据，猎局反向开启。\n\n"
        "n2d 要点：冷宫空间复用。",
    ]
    root = _mk_work(eps, "变现模式: 免费\n")
    _mark_main_nodes_source(root)
    data = _run_json(root)
    rows = data["episodes"]
    assert rows[0]["structured_main_node"] is True
    assert rows[0]["strength"] == 2
    assert rows[0]["closed_loop"] is True
    assert rows[0]["risk"] is False


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-q"]))


# ── G3·付费墙断点强度入闸（仅付费/海外档）─────────────────────────
def _run(root, *extra):
    """Return (data_or_None, returncode). JSON parsed when --json present."""
    cp = subprocess.run([sys.executable, SCRIPT, root, *extra], capture_output=True, text=True)
    data = json.loads(cp.stdout) if "--json" in extra and cp.stdout.strip() else None
    return data, cp.returncode


# 10 集，1-7/9/10 强尾(！=strength2·闭环·章头)，第8集弱卡点(钩词但无标点=strength1·非逐集risk)
def _paid_eps_weak_wall8():
    eps = ["第%d章\n他逼问背叛，她反击夺回主导，竟是另有隐情！" % i for i in range(1, 11)]
    # 第8集：付费墙位，钩词收尾但无悬念标点 → strength 1（中），不触发逐集 risk，但付费墙应最强
    eps[7] = "第8章\n他逼问背叛，她反击夺回主导，门外站着的人究竟是谁"
    return eps


def test_paid_weak_paywall_enters_strict_gate():
    root = _mk_work(_paid_eps_weak_wall8(), "题材: 宫斗\n变现模式: 付费\n")
    data, _ = _run(root, "--json")
    arc = data["series_arc"]
    assert 8 in arc["cliffhanger_targets"]
    assert arc["weak_paywalls"] == [8]          # 付费墙断点偏弱进闸列
    assert data["has_risk"] is False            # 第8集本身不是逐集高风险（strength=1·闭环·章头）
    assert data["strict_block"] is True         # G3·净增覆盖：靠付费墙弱触发


def test_paid_weak_paywall_strict_exits_1():
    root = _mk_work(_paid_eps_weak_wall8(), "题材: 宫斗\n变现模式: 付费\n")
    _, rc_plain = _run(root)                     # 无 --strict → report-only
    _, rc_strict = _run(root, "--strict")
    assert rc_plain == 0 and rc_strict == 1


def test_paid_strong_walls_pass_strict():
    # 所有付费墙都以悬念标点收尾(strength2) → 无弱卡点 → strict 放行
    eps = ["第%d章\n他逼问背叛，她反击夺回主导，竟是另有隐情！" % i for i in range(1, 11)]
    root = _mk_work(eps, "题材: 宫斗\n变现模式: 付费\n")
    data, rc = _run(root, "--strict", "--json")
    assert data["series_arc"]["weak_paywalls"] == []
    assert data["strict_block"] is False and rc == 0


def test_free_mode_weak_wall_not_gated():
    # 同样的弱卡点，免费档 weak_paywalls 恒空（不设硬付费墙）→ 不因此阻断
    root = _mk_work(_paid_eps_weak_wall8(), "题材: 宫斗\n变现模式: 免费\n")
    data, rc = _run(root, "--strict", "--json")
    assert data["series_arc"]["weak_paywalls"] == []
    assert data["series_arc"]["cliffhanger_targets"] == []
