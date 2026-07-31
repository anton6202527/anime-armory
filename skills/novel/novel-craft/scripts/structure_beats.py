#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""structure_beats.py — 全书结构节拍表 scaffold + 符合度机检（advisory·纯标准库）。

为什么：`references/story-structures.md` 的结构模型库（七点/Save the Cat/三幕/Story Circle）
此前是**纯文档**——选了骨架没有任何机器对象承载"中点反转计划落在第几章"，arc 工具又只看
3-5 章窗口，于是传统写作最经典的结构病 **sagging middle（中段疲软）** 在计划期完全不可见：
Q10 已证明"从正文自动识别节拍"是学术空白（别做语义检测器）；本脚本走可行的另一半——
**作者声明节拍计划（curated 台账），机器当会计对账**，与 foreshadow_ledger 同一哲学。

工件：`设定/结构节拍表.json`（kind=novel_structure_beats）
  {model, target_chapters, beats: [{beat, label, planned_chapter, note}]}

四个信号（全部 advisory·blocking 恒 0——结构是护栏不是镣铐，见 story-structures.md 反模式）：
  ① beat_missing          所选模型的关键节拍未声明（如七点缺 midpoint）→ 建议级
  ② beat_position_drift   节拍计划位置偏出经典区间（中点不在 40-60% 等）→ 建议级
  ③ sagging_middle_gap    25%-80% 中段区两个相邻节拍间隔超上限——中段无结构锚，
                          正是"写着写着塌了"的高发形态 → 建议级
  ④ beat_order_violation  节拍章号违反模型先后序（pinch_2 排在 midpoint 前）→ 建议级

口径纪律：
  - 位置区间来自传统结构学通说（七点/StC 的百分比锚），是**经验护栏非铁律**——全部
    advisory，且 note 里写明"有意打破即豁免"；起承转结/单元剧是章级循环结构，无全书
    百分比锚，声明该模型时本检自动跳过（不硬套，见 story-structures.md 反模式③）。
  - 只读作者 curated 的节拍表整数章号，不扫正文（B10：无正文启发式）。

用法：
    python3 structure_beats.py scaffold <作品根> --model 七点结构 [--target-chapters 120]
    python3 structure_beats.py check <作品根> [--json]
测试：cd skills/novel/novel-craft/scripts && python3 -m pytest test_structure_beats.py
"""
import argparse
import json
import os
import sys
from datetime import date

KIND = "novel_structure_beats"
BEATS_REL = os.path.join("设定", "结构节拍表.json")
PROVENANCE = "curated-plan·advisory"

# ── 模型库（与 references/story-structures.md 一一对应）──────────────────────
# 每拍：(beat_id, 中文名, 位置区间 lo-hi 占全书比例)。区间=传统结构学经验护栏。
MODELS = {
    "七点结构": [
        ("hook", "钩子/起点状态", 0.00, 0.10),
        ("plot_turn_1", "第一转折点（进入主线）", 0.15, 0.30),
        ("pinch_1", "第一夹点（反面力量施压）", 0.30, 0.45),
        ("midpoint", "中点（被动→主动翻转）", 0.40, 0.60),
        ("pinch_2", "第二夹点（看似最糟）", 0.55, 0.80),
        ("plot_turn_2", "第二转折点（最后一块拼图）", 0.75, 0.90),
        ("resolution", "结局兑现", 0.90, 1.00),
    ],
    "save_the_cat": [
        ("catalyst", "催化剂（打破日常）", 0.05, 0.15),
        ("midpoint", "中点（假胜/假败）", 0.40, 0.60),
        ("all_is_lost", "至暗时刻（全书最低点）", 0.65, 0.85),
        ("finale", "终局", 0.85, 1.00),
    ],
    "三幕": [
        ("inciting", "激励事件", 0.05, 0.15),
        ("plot_point_1", "一幕转折", 0.20, 0.30),
        ("midpoint", "中点反转", 0.40, 0.60),
        ("plot_point_2", "二幕转折（至暗后破局）", 0.70, 0.85),
        ("climax", "高潮", 0.85, 1.00),
    ],
    "story_circle": [
        ("you", "安于日常", 0.00, 0.10),
        ("need", "意识到缺失", 0.05, 0.18),
        ("go", "跨过门槛", 0.15, 0.30),
        ("search", "适应试错付代价", 0.25, 0.50),
        ("find", "得到想要的", 0.45, 0.62),
        ("take", "付出沉重代价", 0.55, 0.78),
        ("return", "带着改变回归", 0.75, 0.92),
        ("change", "今非昔比", 0.90, 1.00),
    ],
}
# 章级循环模型：无全书百分比锚，声明即跳过（不硬套，story-structures.md 反模式③）。
UNIT_MODELS = ("起承转结", "kishotenketsu", "单元剧")

# 中段疲软：25%-80% 区间内相邻节拍最大间隔超过全书的 SAG_GAP_FRAC → 预警。
SAG_ZONE = (0.25, 0.80)
SAG_GAP_FRAC = float(os.environ.get("NOVEL_STRUCT_SAG_GAP_FRAC", "0.22"))
SAG_GAP_MIN_CH = int(os.environ.get("NOVEL_STRUCT_SAG_GAP_MIN_CH", "5"))  # 短篇不误报
POSITION_TOLERANCE = float(os.environ.get("NOVEL_STRUCT_POS_TOL", "0.05"))  # 区间外再宽容 5%


def beats_path(root):
    return os.path.join(root, BEATS_REL)


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def _target_chapters(root, plan=None):
    """全书目标章数：节拍表自带 > _meta.json.target_chapters > 章纲/正文最大章号。取不到→None。"""
    if plan and plan.get("target_chapters"):
        try:
            n = int(plan["target_chapters"])
            if n > 0:
                return n
        except (TypeError, ValueError):
            pass
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    try:
        n = int(meta.get("target_chapters") or 0)
        if n > 0:
            return n
    except (TypeError, ValueError):
        pass
    import glob
    import re
    mx = 0
    outline = os.path.join(root, "设定", "章纲.md")
    if os.path.exists(outline):
        with open(outline, encoding="utf-8", errors="replace") as f:
            for m in re.finditer(r"第\s*0*(\d+)\s*章", f.read()):
                mx = max(mx, int(m.group(1)))
    for p in glob.glob(os.path.join(root, "章节", "第*.md")):
        m = re.search(r"第0*(\d+)章", os.path.basename(p))
        if m:
            mx = max(mx, int(m.group(1)))
    return mx or None


def normalize_model(name):
    """模型名归一：容错常见别名/大小写。未知返回原样（check 会给 unknown_model 提示）。"""
    s = str(name or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "seven_point": "七点结构", "七点": "七点结构", "7点": "七点结构",
        "save_the_cat": "save_the_cat", "stc": "save_the_cat", "救猫咪": "save_the_cat",
        "three_act": "三幕", "三幕结构": "三幕",
        "story_circle": "story_circle", "八步环": "story_circle", "故事圈": "story_circle",
        "起承转结": "起承转结", "kishotenketsu": "起承转结", "单元剧": "单元剧",
    }
    return aliases.get(s, aliases.get(str(name or "").strip(), str(name or "").strip()))


def scaffold(root, model, target_chapters=None):
    """按模型生成节拍表模板：planned_chapter 取区间中点×目标章数，作者再手调。"""
    model = normalize_model(model)
    if model in UNIT_MODELS:
        raise SystemExit(f"「{model}」是章级循环结构，无全书节拍锚——无需节拍表（见 story-structures.md）")
    if model not in MODELS:
        raise SystemExit(f"未知模型「{model}」；可选：{'、'.join(MODELS)}（章级循环：{'、'.join(UNIT_MODELS)} 不建表）")
    target = target_chapters or _target_chapters(root) or 100
    beats = []
    for beat_id, label, lo, hi in MODELS[model]:
        mid = (lo + hi) / 2
        beats.append({
            "beat": beat_id, "label": label,
            "planned_chapter": max(1, round(mid * target)),
            "note": "（模板默认位=区间中点，按实际章纲手调；有意打破经典位请在 note 说明）",
        })
    payload = {
        "schema_version": 1, "kind": KIND, "updated_at": date.today().isoformat(),
        "model": model, "target_chapters": target, "beats": beats,
    }
    path = beats_path(root)
    write_json(path, payload)
    return path, payload


def check_plan(plan, target):
    """纯函数：节拍表 → alerts。全部 advisory；模型未知/章级循环各给一条 info 说明后返回。"""
    alerts = []
    model = normalize_model(plan.get("model"))
    if model in UNIT_MODELS:
        return [{"type": "unit_model_skipped", "severity": "info", "auto": True,
                 "note": f"「{model}」是章级循环结构，无全书百分比锚——节拍符合度检查不适用（章级工艺走章纲/hook 检测）"}]
    spec = MODELS.get(model)
    if not spec:
        return [{"type": "unknown_model", "severity": "info", "auto": True,
                 "note": f"节拍表模型「{plan.get('model')}」不在模型库（{'、'.join(MODELS)}）——无法对账；"
                         f"改名或在 story-structures.md 补模型定义"}]
    declared = {}
    for b in plan.get("beats") or []:
        if not isinstance(b, dict):
            continue
        try:
            ch = int(b.get("planned_chapter") or 0)
        except (TypeError, ValueError):
            continue
        if b.get("beat") and ch > 0:
            declared[str(b["beat"])] = ch

    # ① 关键节拍未声明
    for beat_id, label, _lo, _hi in spec:
        if beat_id not in declared:
            alerts.append({"type": "beat_missing", "severity": "建议级", "auto": True,
                           "note": (f"「{model}」的关键节拍 {beat_id}（{label}）未声明计划章——"
                                    f"缺中点/夹点锚是中段疲软（sagging middle）的头号成因；"
                                    f"补进 设定/结构节拍表.json（{PROVENANCE}）")})

    if not target or target <= 0:
        alerts.append({"type": "target_unknown", "severity": "info", "auto": True,
                       "note": "无法确定全书目标章数（节拍表/_meta.json/章纲均无）——位置类检查跳过"})
        return alerts

    # ② 位置偏出经典区间（±POSITION_TOLERANCE 宽容）
    for beat_id, label, lo, hi in spec:
        if beat_id not in declared:
            continue
        frac = declared[beat_id] / target
        if frac < lo - POSITION_TOLERANCE or frac > hi + POSITION_TOLERANCE:
            alerts.append({"type": "beat_position_drift", "severity": "建议级", "auto": True,
                           "chapter": declared[beat_id],
                           "note": (f"{beat_id}（{label}）计划在第{declared[beat_id]}章 = 全书 {frac:.0%}，"
                                    f"偏出经典区间 {lo:.0%}–{hi:.0%}——经验护栏非铁律，有意打破请在节拍表"
                                    f" note 说明；无意的偏移常见于中点拖后=前松后赶（{PROVENANCE}）")})

    # ③ 中段疲软：SAG_ZONE 内相邻锚点最大间隔
    zone_lo, zone_hi = int(SAG_ZONE[0] * target), int(SAG_ZONE[1] * target)
    anchors = sorted(set([zone_lo] + [c for c in declared.values() if zone_lo <= c <= zone_hi] + [zone_hi]))
    gap_limit = max(SAG_GAP_MIN_CH, int(SAG_GAP_FRAC * target))
    for a, b in zip(anchors, anchors[1:]):
        if b - a > gap_limit:
            alerts.append({"type": "sagging_middle_gap", "severity": "建议级", "auto": True,
                           "chapter": a,
                           "note": (f"中段区（{SAG_ZONE[0]:.0%}–{SAG_ZONE[1]:.0%}）第{a}–{b}章之间 "
                                    f"{b - a} 章无任何结构节拍锚（上限 {gap_limit}）——正是 sagging middle "
                                    f"高发带；传统修法：在此加夹点/小反转/子目标，或把中点反转前移"
                                    f"（{PROVENANCE}·对齐 sweep_schedule 的 40-60% 加密回扫带）")})

    # ④ 节拍先后序违例
    order = [beat_id for beat_id, *_ in spec]
    seq = [(order.index(k), k, v) for k, v in declared.items() if k in order]
    seq.sort(key=lambda t: t[0])
    for (i1, k1, c1), (i2, k2, c2) in zip(seq, seq[1:]):
        if c2 < c1:
            alerts.append({"type": "beat_order_violation", "severity": "建议级", "auto": True,
                           "chapter": c2,
                           "note": (f"{k2}（第{c2}章）计划在 {k1}（第{c1}章）之前，违反「{model}」的"
                                    f"节拍先后序——若是多线/倒叙的有意安排请在 note 说明（{PROVENANCE}）")})
    return alerts


def analyze(root):
    """consistency_audit 子检测器契约：{ran, alerts, total, blocking(=0)}。无节拍表优雅跳过。"""
    plan = load_json(beats_path(root))
    if not isinstance(plan, dict) or plan.get("kind") != KIND:
        return {"ran": False,
                "skipped": ("无 设定/结构节拍表.json——长篇建议声明结构骨架后跑符合度检查："
                            "python3 novel-craft/scripts/structure_beats.py scaffold <root> --model 七点结构")}
    target = _target_chapters(root, plan)
    alerts = check_plan(plan, target)
    return {"ran": True, "model": normalize_model(plan.get("model")),
            "target_chapters": target,
            "thresholds": {"sag_gap_frac": SAG_GAP_FRAC, "sag_gap_min_ch": SAG_GAP_MIN_CH,
                           "position_tolerance": POSITION_TOLERANCE, "provenance": PROVENANCE,
                           "note": "advisory：结构护栏永不阻断；有意打破经典位在节拍表 note 说明即可。"},
            "alerts": alerts, "total": len(alerts), "blocking": 0}


def main(argv=None):
    ap = argparse.ArgumentParser(description="全书结构节拍表 scaffold/符合度机检（advisory）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scaffold")
    sc.add_argument("project_root")
    sc.add_argument("--model", required=True, help="七点结构 | save_the_cat | 三幕 | story_circle")
    sc.add_argument("--target-chapters", type=int, default=None)
    ck = sub.add_parser("check")
    ck.add_argument("project_root")
    ck.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if args.cmd == "scaffold":
        path, payload = scaffold(root, args.model, args.target_chapters)
        print(f"[ok] 结构节拍表 → {path}（{payload['model']}·目标 {payload['target_chapters']} 章·"
              f"{len(payload['beats'])} 拍模板，请按章纲手调 planned_chapter）")
        return 0
    res = analyze(root)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    if not res.get("ran"):
        print("ℹ️ " + res.get("skipped", "skipped"))
        return 0
    out = os.path.join(root, "审稿", "structure_beat_findings.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    icon = "⚠️" if res["total"] else "✅"
    print(f"{icon} 结构节拍符合度：模型 {res['model']}，{res['total']} 条提示 → {out}")
    for a in res["alerts"]:
        print(f"  - [{a['severity']}] {a['type']}: {a['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
