#!/usr/bin/env python3
"""seam_concat.py — 按 storyboard 每个接缝的转场类型自动拼接（接缝自动化引擎）。

替代 compose.sh 里一律 `concat -c copy` 的裸拼：读 `storyboard.json` 每个接缝的
`clips[].continuity.transition`，逐接缝判定接法——

  - 硬切（默认/有意硬切）          → 直接拼，不加转场
  - 微溶解（跳变/视觉跳变/未焊住）  → 局部 xfade 交叉溶解（0.1–0.3s）
  - 缺空镜（需要空镜但没补）        → 报警（不静默裸切，也不自造素材）

实现策略（重编码最小化）：把被硬切/报警接缝相连的连续 clip 归为一个 run，run 内
`concat -c copy`（compose 工作缓存里的 clip 已统一规格、无音轨，零重编码；`出视频/` 原片不改写）；只在**溶解接缝**之间做 xfade。
任何 ffmpeg 失败 → 回退整体 `concat -c copy`，绝不让合成中断。

纯逻辑（分类/分段/xfade offset/滤镜串）可单测；ffmpeg 调用是薄执行层。
clip 在 compose.sh 的 list.txt 阶段已统一到同分辨率/fps/yuv420p 且缓存内 `-an`，故只做视频
xfade，无需 acrossfade（音轨在下游单独按 `视频原生音轨` 策略处理）。

用法：
  python3 seam_concat.py --list <list.txt> --out <concat.mp4> \
      [--storyboard 脚本/第N集/storyboard.json] [--fallback 硬切|微溶解|报警] \
      [--dissolve-sec 0.25] [--report 接缝报告.md] [--plan-only]
缺 storyboard / clip 数对不上 / 无溶解接缝 → 等价于今天的 `concat -c copy`。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

DISSOLVE_WORDS = ("微溶解", "溶解", "叠化", "渐变", "淡入淡出", "交叉溶解", "dissolve", "crossfade", "cross fade", "cross-fade")
WARN_WORDS = ("缺空镜", "需要空镜", "空镜缺", "需补空镜", "补空镜", "missing establishing", "insert needed", "需插入空镜")
JUMP_WORDS = ("跳变", "视觉跳变", "未焊", "没焊", "jump", "硬跳")
HARD_WORDS = ("硬切", "直切", "跳切", "hard_cut", "hard cut", "action_cut", "action cut", "match cut", "matchcut", "eyeline", "cut")
# 有意冲击点：不要在这种接缝加溶解（会泄掉冲击），除非作者显式写了溶解。
INTENDED_HARD_CTX = ("爽点", "反转", "高潮", "炸点", "punch", "climax", "reveal", "硬切")

FALLBACK_MAP = {"硬切": "cut", "微溶解": "dissolve", "报警": "warn", "cut": "cut", "dissolve": "dissolve", "warn": "warn"}
DEFAULT_DISSOLVE_SEC = 0.25


def _has(text: str, words) -> bool:
    t = (text or "").lower()
    return any(w.lower() in t for w in words)


def classify_seam(transition: str, ctx: str = "", fallback: str = "cut") -> Tuple[str, str]:
    """返回 (decision, reason)，decision ∈ {cut, dissolve, warn}。
    优先级：缺空镜报警 > 显式溶解 > 显式硬切 > 跳变(→溶解，除非有意冲击) > 兜底。"""
    t = transition or ""
    if _has(t, WARN_WORDS):
        return "warn", f"转场标注缺空镜：{t.strip()}"
    if _has(t, DISSOLVE_WORDS):
        return "dissolve", f"转场显式溶解：{t.strip()}"
    if _has(t, HARD_WORDS):
        return "cut", f"转场显式硬切：{t.strip()}"
    if _has(t, JUMP_WORDS):
        if _has(ctx, INTENDED_HARD_CTX):
            return "cut", "跳变但属有意冲击点(爽点/反转)，硬切保冲击"
        return "dissolve", f"视觉跳变未焊住 → 微溶解兜底：{t.strip()}"
    # 未定/未知：走兜底；但有意冲击点永不自动溶解
    fb = FALLBACK_MAP.get(str(fallback).strip(), "cut")
    if fb == "dissolve" and _has(ctx, INTENDED_HARD_CTX):
        return "cut", "兜底=微溶解，但本接缝是有意冲击点 → 硬切"
    reason = {"cut": "转场未定，兜底硬切", "dissolve": "转场未定，兜底微溶解", "warn": "转场未定，兜底报警"}[fb]
    return fb, reason


def parse_list_file(list_txt: str) -> List[str]:
    """解析 ffmpeg concat list（`file '...'` 行）→ 文件路径列表。"""
    files: List[str] = []
    with open(list_txt, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"\s*file\s+'(.+)'\s*$", line.strip()) or re.match(r'\s*file\s+"(.+)"\s*$', line.strip())
            if m:
                files.append(m.group(1))
            elif line.strip().startswith("file "):
                files.append(line.strip()[5:].strip().strip("'\""))
    return files


def load_storyboard_seams(storyboard_path: str) -> Tuple[List[str], List[str]]:
    """返回 (transitions, ctxs)，逐 clip 一项；transition 取 clips[i].continuity.transition，
    ctx 取该 clip 的 label/rhythm（用于有意冲击点判定）。读不到返回 ([],[])。"""
    if not storyboard_path or not os.path.isfile(storyboard_path):
        return [], []
    try:
        data = json.load(open(storyboard_path, encoding="utf-8"))
    except (ValueError, OSError):
        return [], []
    clips = data.get("clips") if isinstance(data, dict) else None
    if not isinstance(clips, list):
        return [], []
    transitions, ctxs = [], []
    for c in clips:
        c = c if isinstance(c, dict) else {}
        cont = c.get("continuity") if isinstance(c.get("continuity"), dict) else {}
        transitions.append(str(cont.get("transition") or ""))
        ctxs.append(" ".join(str(c.get(k) or "") for k in ("label", "rhythm", "id", "节奏")))
    return transitions, ctxs


def _logical_cid(path: str) -> str:
    """从文件名提取逻辑 ID（如 Clip_01_part1 -> Clip_01）。"""
    name = os.path.basename(path)
    # 匹配 Clip_NN 或类似的 ID，忽略 _partN 后缀
    match = re.search(r"(Clip[_\s-]*\d+)", name, re.IGNORECASE)
    return match.group(1).lower() if match else name


def build_plan(files: List[str], transitions: List[str], ctxs: List[str], fallback: str = "cut") -> Dict[str, Any]:
    """逐接缝判定。支持 _partN 拆段：子段间强制硬切，跨逻辑镜接缝查 storyboard。"""
    n_files = len(files)
    warnings: List[str] = []
    seams: List[Dict[str, Any]] = []
    
    # 建立逻辑 ID 序列
    logical_ids = [_logical_cid(f) for f in files]
    # 唯一逻辑 ID 序列（去重并保持顺序）
    unique_logical = []
    for lid in logical_ids:
        if not unique_logical or lid != unique_logical[-1]:
            unique_logical.append(lid)
    
    n_logical = len(unique_logical)
    n_sb = len(transitions)
    use_sb = bool(transitions) and n_logical == n_sb
    
    if transitions and not use_sb:
        warnings.append(f"逻辑镜数({n_logical}) 与 storyboard clips({n_sb}) 不一致 → 全部硬切兜底")

    for i in range(max(0, n_files - 1)):
        cid_a = logical_ids[i]
        cid_b = logical_ids[i+1]
        
        if cid_a == cid_b:
            # 同一逻辑镜内部拆段（Split Relay）——强制硬切（无缝接力）
            decision, reason = "cut", f"内部拆段接力({cid_a})"
        elif use_sb:
            # 跨逻辑镜接缝，查 storyboard
            try:
                logical_idx = unique_logical.index(cid_a)
                decision, reason = classify_seam(transitions[logical_idx], 
                                                 ctxs[logical_idx] if logical_idx < len(ctxs) else "", 
                                                 fallback)
            except ValueError:
                decision, reason = "cut", "逻辑 ID 匹配失败，硬切"
        else:
            decision, reason = ("cut", "无 storyboard 或镜数不符，硬切")
            
        seam = {"seam": i, "between": [i, i + 1], "decision": decision, "reason": reason}
        seams.append(seam)
        if decision == "warn":
            warnings.append(f"接缝 {i}→{i+1}：{reason}；建议补缓冲 clip")
            
    return {
        "n_clips": n_files,
        "n_logical": n_logical,
        "seams": seams,
        "warnings": warnings,
        "dissolve_count": sum(1 for s in seams if s["decision"] == "dissolve"),
        "warn_count": sum(1 for s in seams if s["decision"] == "warn"),
        "used_storyboard": use_sb,
    }


def group_runs(seams: List[Dict[str, Any]], n_clips: int) -> List[List[int]]:
    """按溶解接缝切分 run：溶解接缝两侧拆成不同 run；硬切/报警接缝留在同 run（裸拼）。
    返回 [[clip_idx,...], ...]。"""
    if n_clips <= 0:
        return []
    runs: List[List[int]] = [[0]]
    for s in seams:
        i = s["seam"]
        if s["decision"] == "dissolve":
            runs.append([i + 1])
        else:
            runs[-1].append(i + 1)
    return runs


def xfade_offsets(seg_durations: List[float], dissolve_sec: float) -> List[float]:
    """xfade 链各步 offset：offset_k = sum(s_0..s_{k-1}) - k*D（k 从 1 计）。"""
    offsets: List[float] = []
    cum = 0.0
    for k in range(1, len(seg_durations)):
        cum += seg_durations[k - 1]
        offsets.append(round(cum - k * dissolve_sec, 4))
    return offsets


def build_xfade_filter(seg_durations: List[float], dissolve_sec: float, transition: str = "fade") -> Tuple[str, str]:
    """生成 N 段 xfade 链 filter_complex（视频）。返回 (filter_complex, 末端label)。"""
    n = len(seg_durations)
    if n == 0:
        return "", ""
    if n == 1:
        return "", "0:v"
    offsets = xfade_offsets(seg_durations, dissolve_sec)
    parts: List[str] = []
    prev = "0:v"
    for k in range(1, n):
        out = f"vx{k}" if k < n - 1 else "vout"
        parts.append(
            f"[{prev}][{k}:v]xfade=transition={transition}:duration={dissolve_sec}:offset={offsets[k-1]}[{out}]"
        )
        prev = out
    return ";".join(parts), "vout"


# ── 执行层（薄；任何失败回退 -c copy）────────────────────────────────────

def _ffprobe_duration(path: str) -> Optional[float]:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=30,
        ).stdout.strip()
        return float(out) if out else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _concat_copy(files: List[str], out: str, work: str) -> bool:
    list_path = os.path.join(work, "_seam_concat_list.txt")
    with open(list_path, "w", encoding="utf-8") as fh:
        for f in files:
            fh.write(f"file '{os.path.abspath(f)}'\n")
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", list_path, "-c", "copy", out], check=True, timeout=600)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def render_report(plan: Dict[str, Any], dissolve_sec: float) -> str:
    lines = ["# 接缝处理报告", "",
             f"- clip 数: {plan['n_clips']}",
             f"- 用 storyboard 转场: {plan['used_storyboard']}",
             f"- 微溶解接缝: {plan['dissolve_count']}（每处 {dissolve_sec}s xfade）",
             f"- 缺空镜报警: {plan['warn_count']}", ""]
    if plan["warnings"]:
        lines += ["## ⚠️ 报警", ""]
        lines += [f"- {w}" for w in plan["warnings"]]
        lines.append("")
    lines += ["## 逐接缝", "", "| 接缝 | 接法 | 理由 |", "|---|---|---|"]
    icon = {"cut": "✂️ 硬切", "dissolve": "🌫️ 微溶解", "warn": "🚨 缺空镜"}
    for s in plan["seams"]:
        lines.append(f"| {s['between'][0]}→{s['between'][1]} | {icon.get(s['decision'], s['decision'])} | {s['reason']} |")
    return "\n".join(lines) + "\n"


def run(list_txt: str, out: str, *, storyboard: str = "", fallback: str = "cut",
        dissolve_sec: float = DEFAULT_DISSOLVE_SEC, report: str = "", plan_only: bool = False) -> int:
    files = parse_list_file(list_txt)
    transitions, ctxs = load_storyboard_seams(storyboard)
    plan = build_plan(files, transitions, ctxs, fallback)
    work = os.path.dirname(os.path.abspath(out)) or "."

    if report:
        os.makedirs(os.path.dirname(os.path.abspath(report)) or ".", exist_ok=True)
        with open(report, "w", encoding="utf-8") as fh:
            fh.write(render_report(plan, dissolve_sec))
    for w in plan["warnings"]:
        print(f"[seam][warn] {w}", file=sys.stderr)

    runs = group_runs(plan["seams"], len(files))

    if plan_only:
        seg_filter = ""
        if len(runs) > 1:
            seg_filter, _ = build_xfade_filter([0.0] * len(runs), dissolve_sec)  # 形状预览（duration 占位）
        print(json.dumps({"plan": plan, "runs": runs, "mode": "xfade" if len(runs) > 1 else "concat_copy",
                          "filter_preview": seg_filter}, ensure_ascii=False, indent=2))
        return 0

    if not files:
        print("[seam] 空 clip 列表，无可拼接", file=sys.stderr)
        return 2

    # 无溶解接缝（或单 run）→ 等价今天的快路径
    if len(runs) <= 1:
        ok = _concat_copy(files, out, work)
        print(f"[seam] {'concat -c copy' if ok else 'concat 失败'}（无微溶解接缝）", file=sys.stderr)
        return 0 if ok else 1

    # 有溶解接缝：每个 run 先 -c copy 成 seg，再 xfade 链
    try:
        seg_files: List[str] = []
        for ri, run_idxs in enumerate(runs):
            run_files = [files[i] for i in run_idxs]
            if len(run_files) == 1:
                seg_files.append(run_files[0])
            else:
                seg = os.path.join(work, f"_seam_seg_{ri:02d}.mp4")
                if not _concat_copy(run_files, seg, work):
                    raise RuntimeError(f"run {ri} 段内拼接失败")
                seg_files.append(seg)
        durations = [_ffprobe_duration(s) for s in seg_files]
        if any(d is None for d in durations):
            raise RuntimeError("ffprobe 取段时长失败")
        filt, final = build_xfade_filter(durations, dissolve_sec)
        cmd = ["ffmpeg", "-y", "-loglevel", "error"]
        for s in seg_files:
            cmd += ["-i", s]
        cmd += ["-filter_complex", filt, "-map", f"[{final}]",
                "-c:v", "libx264", "-preset", os.environ.get("VIDEO_PRESET", "medium"),
                "-crf", os.environ.get("VIDEO_CRF", "20"), "-an", out]
        subprocess.run(cmd, check=True, timeout=1800)
        print(f"[seam] xfade 链合成完成：{plan['dissolve_count']} 处微溶解 / {len(runs)} 段", file=sys.stderr)
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"[seam][warn] xfade 失败({exc}) → 回退 concat -c copy（接缝降级为硬切，不中断合成）", file=sys.stderr)
        return 0 if _concat_copy(files, out, work) else 1


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="按 storyboard 转场自动拼接（硬切/微溶解/缺空镜报警）")
    ap.add_argument("--list", required=True, help="ffmpeg concat list（compose.sh 的 list.txt）")
    ap.add_argument("--out", required=True, help="输出 concat.mp4")
    ap.add_argument("--storyboard", default="", help="脚本/第N集/storyboard.json（缺则全硬切=今天行为）")
    ap.add_argument("--fallback", default="cut", help="转场未定时兜底：硬切|微溶解|报警（默认 硬切）")
    ap.add_argument("--dissolve-sec", type=float, default=DEFAULT_DISSOLVE_SEC)
    ap.add_argument("--report", default="", help="接缝报告 md 输出路径")
    ap.add_argument("--plan-only", action="store_true", help="只出计划不跑 ffmpeg（干跑/测试）")
    ns = ap.parse_args(argv)
    return run(ns.list, ns.out, storyboard=ns.storyboard, fallback=ns.fallback,
               dissolve_sec=ns.dissolve_sec, report=ns.report, plan_only=ns.plan_only)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
