#!/usr/bin/env python3
"""B1 景别进程机检（镜头语法·分镜导演审美） — 2026-06-24 流程自审落地。

`分镜语法.md` 写了"有进有出 / 相邻镜不撞同景别 / 每集≥1 定场 / 情绪爆点用 CU"，但此前**没有脚本验证**——
gate 只拦缺 `shot_size` 字段，不拦"景别没进程、连撞同景别、爆点没给近景"这类业余分镜。本检读
`storyboard.json` 的逐镜 `continuity.shot_size` + `rhythm`，做纯确定性景别进程机检：

  ① 连续 ≥3 镜同景别 → PPT感/无对比（业余头号信号）；
  ② 全集无定场镜（LS/ELS/全景）→ 观众失去空间地理；
  ③ 爽点/情绪爆点镜（rhythm=爽点·CU硬切）景别不是近景档（CU/ECU/特写）→ 情绪没怼近；
  ④ 全集景别极差太小（几乎不变）→ 没有景别对比、像 slideshow；
  ⑤ 30°法则代理：相邻镜同景别且同机位角度 → 跳切风险。

report-only（导演审美建议）；`--strict` 时有 warn 即退出 1，可作阶段2 闸门。纯 stdlib·纯函数可测。
用法：python3 shot_grammar_audit.py <作品根> 第N集 [--strict] [--json]
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# 景别梯度：rank 越大画面越宽。归一到 7 档（含中英别名）。
# 顺序按**特异性**排（长/含子串的码先匹配），避免 "ELS" 被 "LS"、"MCU" 被 "CU" 子串先吞。
SCALE_RANKS = (
    (("ECU", "大特写", "极特写", "extreme close"), 1),
    (("ELS", "大远景", "大全景", "extreme long", "establishing", "定场"), 7),
    (("MLS", "中全景", "medium long"), 5),
    (("BCU", "MCU", "中近景", "medium close"), 3),
    (("LS", "全景", "远景", "long shot", "wide"), 6),
    (("MS", "中景", "medium"), 4),
    (("CU", "特写", "近景", "close"), 2),
)
ESTABLISHING_MIN_RANK = 6   # LS/ELS/全景 起算定场
CLOSEUP_MAX_RANK = 2        # CU/ECU/特写/近景 算近景档
PEAK_RHYTHM_MARKERS = ("爽点", "爆点", "高潮", "CU硬切")
# 机位角度词（30°法则代理用）。
ANGLE_TOKENS = ("仰拍", "俯拍", "平视", "过肩", "OTS", "正面", "侧面", "背面", "反打", "顶拍", "低角度", "高角度")
# B2 转场类型：有表现力的变化型转场 vs 机械硬切。
EXPRESSIVE_TRANSITIONS = ("match_cut", "eyeline", "action_cut", "j_cut", "l_cut", "empty_buffer",
                          "graphic_match", "match cut", "j-cut", "l-cut")
HARD_TRANSITIONS = ("hard_cut", "hard cut", "硬切", "cut", "")


def scale_rank(shot_size: str) -> Optional[int]:
    """shot_size 文本 → 景别 rank(1 最近~7 最宽)；认不出返回 None。纯函数·可测。"""
    s = str(shot_size or "")
    if not s.strip():
        return None
    up = s.upper()
    for aliases, rank in SCALE_RANKS:
        for a in aliases:
            if a.upper() in up:
                return rank
    return None


def angle_tokens(shot_size: str, extra: str = "") -> frozenset:
    """从 shot_size + 补充文本抽机位角度词集合（30°法则代理）。纯函数·可测。"""
    blob = f"{shot_size or ''} {extra or ''}"
    return frozenset(t for t in ANGLE_TOKENS if t in blob)


def consecutive_same_scale_runs(ranks: List[Optional[int]], min_run: int = 3) -> List[Tuple[int, int, int]]:
    """连续同景别段（长度≥min_run）→ [(起index, 止index, rank)]。None 断开连续。纯函数·可测。"""
    runs = []
    i = 0
    n = len(ranks)
    while i < n:
        if ranks[i] is None:
            i += 1
            continue
        j = i
        while j + 1 < n and ranks[j + 1] == ranks[i]:
            j += 1
        if j - i + 1 >= min_run:
            runs.append((i, j, ranks[i]))
        i = j + 1
    return runs


def has_establishing(ranks: List[Optional[int]]) -> bool:
    """全集是否有定场镜（rank≥ESTABLISHING_MIN_RANK）。纯函数·可测。"""
    return any(r is not None and r >= ESTABLISHING_MIN_RANK for r in ranks)


def scale_spread(ranks: List[Optional[int]]) -> int:
    """景别极差（max-min）。无有效景别返回 0。纯函数·可测。"""
    vals = [r for r in ranks if r is not None]
    return (max(vals) - min(vals)) if vals else 0


def _clip_shot_size(clip: Dict[str, Any]) -> str:
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
    return str(cont.get("shot_size") or clip.get("shot_size") or "")


def _clip_rhythm(clip: Dict[str, Any]) -> str:
    return str(clip.get("rhythm") or "")


def _clip_transition(clip: Dict[str, Any]) -> str:
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
    return str(cont.get("transition") or clip.get("transition") or "").strip().lower()


def has_expressive_transition(transitions: List[str]) -> bool:
    """转场序列里是否有任一变化型转场（match/eyeline/J/L-cut…）。纯函数·可测。"""
    for t in transitions:
        if any(e in t for e in EXPRESSIVE_TRANSITIONS):
            return True
    return False


def _is_peak(clip: Dict[str, Any]) -> bool:
    r = _clip_rhythm(clip)
    return any(m in r for m in PEAK_RHYTHM_MARKERS)


def audit_clips(clips: List[Dict[str, Any]]) -> List[Tuple[str, str, str]]:
    """逐镜景别进程机检 → [(severity, code, msg)]。纯函数·可测（不碰 IO）。"""
    findings: List[Tuple[str, str, str]] = []
    ranks = [scale_rank(_clip_shot_size(c)) for c in clips]
    known = [r for r in ranks if r is not None]
    if len(known) < 2:
        findings.append(("info", "shot_size_missing",
                         f"仅 {len(known)}/{len(clips)} 镜可解析 shot_size——景别进程无法机检，先补 continuity.shot_size"))
        return findings

    # ① 连续 ≥3 同景别
    for i, j, rank in consecutive_same_scale_runs(ranks, 3):
        findings.append(("warn", "same_scale_run",
                         f"镜{i+1}-{j+1} 连续 {j-i+1} 个同景别（rank {rank}）：撞景别像 PPT，相邻镜应有进有出（远→近或近→远）"))

    # ② 无定场
    if not has_establishing(ranks):
        findings.append(("warn", "no_establishing",
                         "全集无定场镜（LS/ELS/全景）：观众失去空间地理，每场开头给 ≥1 个 establishing 远景定场"))

    # ③ 爆点景别不够近
    for idx, c in enumerate(clips):
        if _is_peak(c):
            r = ranks[idx]
            if r is not None and r > CLOSEUP_MAX_RANK:
                findings.append(("warn", "peak_not_closeup",
                                 f"镜{idx+1} 标爽点/爆点（rhythm={_clip_rhythm(c)}）但景别 rank {r} 不是近景档：情绪爆点应怼 CU/ECU 硬切"))

    # ④ 景别极差太小
    if scale_spread(ranks) <= 1:
        findings.append(("warn", "flat_scale",
                         f"全集景别极差仅 {scale_spread(ranks)}：几乎不变景别像 slideshow，缺远近对比（紧凑感来自景别反差）"))

    # ⑥ B2 转场单调 / J-L cut 缺位（紧凑·导演审美）：≥4 接缝全硬切、零变化型转场
    if len(clips) >= 5:
        transitions = [_clip_transition(c) for c in clips[:-1]]   # 末镜无下接缝
        if transitions and not has_expressive_transition(transitions):
            findings.append(("warn", "monotone_hard_cuts",
                             "全集接缝几乎全硬切、零变化型转场（match cut/动作连切/J·L-cut）：剪辑机械。"
                             "配音先行尤其该用音频叠化——J-cut（下句先入引下场）/L-cut（上句盖到反应镜），让对白流动不每句硬切"))

    # ⑤ 30°法则代理：相邻镜同景别 + 同机位角度
    for idx in range(1, len(clips)):
        if ranks[idx] is None or ranks[idx] != ranks[idx - 1]:
            continue
        a_prev = angle_tokens(_clip_shot_size(clips[idx - 1]))
        a_cur = angle_tokens(_clip_shot_size(clips[idx]))
        if a_prev and a_cur and a_prev == a_cur:
            findings.append(("warn", "thirty_degree_risk",
                             f"镜{idx}-{idx+1} 同景别同机位（{'/'.join(sorted(a_cur))}）：违 30°法则易成跳切，换机位差≥30° 或换景别"))
    return findings


def storyboard_path(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", ep, "storyboard.json")


def load_clips(root: str, ep: str) -> Optional[List[Dict[str, Any]]]:
    path = storyboard_path(root, ep)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    clips = data.get("clips") if isinstance(data, dict) else None
    return clips if isinstance(clips, list) else None


def print_findings(findings: List[Tuple[str, str, str]]) -> None:
    icon = {"warn": "⚠️", "info": "ℹ️"}
    if not findings:
        print("- ✅ 景别进程机检通过（有进有出·有定场·爆点怼近·有反差）")
        return
    for sev, code, msg in findings:
        print(f"- {icon.get(sev, '·')} [{code}] {msg}")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if len(args) < 2:
        print("用法: shot_grammar_audit.py <作品根> 第N集 [--strict] [--json]")
        sys.exit(2)
    root, ep = args[0], (args[1] if args[1].startswith("第") else f"第{args[1]}集")
    clips = load_clips(root, ep)
    if clips is None:
        print(f"⛔ 缺/坏 {storyboard_path(root, ep)}——先跑 n2d-script 阶段2 出分镜", file=sys.stderr)
        sys.exit(2)
    findings = audit_clips(clips)
    if "--json" in flags:
        print(json.dumps({"episode": ep, "clips": len(clips),
                          "findings": [{"severity": s, "code": c, "msg": m} for s, c, m in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print(f"# 景别进程机检（B1·导演审美·report-only） — {ep}（{len(clips)} 镜）")
        print_findings(findings)
        print("> 正向标准见 references/分镜语法.md；本检只查确定性景别进程，构图/运镜审美仍需人判。")
    warn_n = sum(1 for s, _, _ in findings if s == "warn")
    if "--strict" in flags and warn_n:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
