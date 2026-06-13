#!/usr/bin/env python3
"""n2d-progress/scan.py — 制漫剧(n2d)进度扫描器（只读）。

只扫描 `制漫剧/<剧名>/_进度.md`，解析其中的逐集流程矩阵表，压缩输出：
每阶段完成数 + 生产前沿(下一步该跑哪个 n2d skill) + 次要缺口。
**绝不把上百行的大表灌进上下文，绝不修改任何文件。**

进度表布局（n2d）：行=集，列含 raw + 多个流程列（剧本改编…成片），
单元格 ✅=完成 / N/M=按比例(N=M 才算完成) / ⬜=未开工。
raw=源文本，展示但不计入流程完成判定。

纯标准库，系统 Python 即可。

用法：
  python3 scan.py                 # 扫描 制漫剧/ 下所有剧
  python3 scan.py <剧根> [...]     # 只看指定剧（含 _进度.md 的目录）
  python3 scan.py --root <仓库根>  # 指定仓库根（默认=自动向上找）
"""
import glob
import json
import os
import re
import sys

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'n2d', '_lib'))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from n2d_route import flow_columns, is_done, is_flow_complete, is_progress_satisfied, is_started, parse_progress, stage_of
from n2d_settings import is_native_av, is_video_first
try:
    from n2d_contract import cross_cutting, cross_cutting_tools, COSTLY_HINTS
except Exception:  # pragma: no cover - 横切检查可选，缺契约也不影响主流程扫描
    cross_cutting = None
    cross_cutting_tools = None
    COSTLY_HINTS = None

LINE_DIR = "制漫剧"  # 只管 n2d 这一条线

DISPATCHER = "n2d"  # 认不出列名时兜底

# 花钱/不可逆/合规的前沿列 → 提醒先确认。基准取 n2d_contract.COSTLY_HINTS（单一真值源），
# 仅补 progress 看板特有的「分镜 PNG 前共享定妆库须全 ✅」；缺契约时回退本地精简版。
COSTLY_HINT = dict(COSTLY_HINTS) if COSTLY_HINTS else {
    "配音": "声音克隆需肖像/音色授权（合规闸门）",
    "出图": "会真出图·消耗额度 → 开跑前确认生图后端 + 重抽预算档位",
    "视频": "会真出视频·消耗额度 → 开跑前确认生视频后端",
    "成片": "合成成片（混音+烧字幕），相对便宜但耗时",
}
COSTLY_HINT["出图"] = COSTLY_HINT.get("出图", "") + " 分镜 PNG 前共享定妆库 出图/共享/ 必须全 ✅。"

LOW_COST_PARALLEL_SKILLS = {"n2d-script", "n2d-progress", "n2d-update"}


def _num(row):
    try:
        return int(row.get("_num", 10**9))
    except (TypeError, ValueError):
        return 10**9


def _parallel_tail(col, skill):
    if col in COSTLY_HINT:
        return "（也属于花钱/不可逆/合规点，开跑前仍需单独确认）"
    if skill in LOW_COST_PARALLEL_SKILLS:
        return "（低成本前期，可和当前阶段并行）"
    return "（可并行，但需按对应 stage gate/依赖检查）"


def format_parallel(lbl, col, val, skill, note):
    vt = f"（当前 {val}）" if val and val != "⬜" else ""
    tail = "（补真音后再合成）" if note else ""
    return f"可并行: {lbl}「{col}」{vt} → {skill}{tail} {_parallel_tail(col, skill)}"


def parallel_suggestion(root, rows, header, flow, gaps):
    """Return one safe parallel work suggestion, if there is a useful candidate.

    Prefer already-started secondary gaps; otherwise suggest starting the next
    raw-ready episode from its current first stage.  This keeps the main
    "frontier" single-minded while surfacing useful cross-episode overlap.
    """
    if not gaps:
        return ""

    primary_ep = gaps[0][0]
    for lbl, col, val, skill, note in gaps[1:]:
        if lbl != primary_ep and col:
            return format_parallel(lbl, col, val, skill, note)

    primary_num = next((_num(r) for r in rows if r.get("_ep") == primary_ep), 0)
    for r in sorted(rows, key=_num):
        ep = r.get("_ep", "")
        if not ep or ep == primary_ep:
            continue
        # Do not invent work for episodes whose source/raw row is not ready.
        if not is_started(r.get("raw", "")) and not is_progress_satisfied(root, r, "raw"):
            continue
        # Prefer later episodes; if none exist, the loop below still catches earlier unfinished ones.
        if _num(r) <= primary_num:
            continue
        if any(is_started(r.get(c, "")) for c in flow):
            continue
        route = stage_of(root, r, header)
        col = route.get("col") or ""
        if col:
            val = r.get(col, "").strip()
            return format_parallel(ep, col, val, route.get("skill") or DISPATCHER, route.get("note") or "")

    for r in sorted(rows, key=_num):
        ep = r.get("_ep", "")
        if not ep or ep == primary_ep:
            continue
        if any(is_started(r.get(c, "")) for c in flow):
            continue
        route = stage_of(root, r, header)
        col = route.get("col") or ""
        if col:
            val = r.get(col, "").strip()
            return format_parallel(ep, col, val, route.get("skill") or DISPATCHER, route.get("note") or "")
    return ""


def _finding_counts(data):
    """Return (block, warn) for consistency/gate findings payloads.

    Supports both current `severity/dimension/message` rows and older
    `sev/dim/msg` rows. Files with only info rows are not actionable gaps.
    """
    summary = data.get("summary") if isinstance(data, dict) else None
    if isinstance(summary, dict):
        sev = summary.get("severity")
        if isinstance(sev, dict):
            return int(sev.get("block") or 0), int(sev.get("warn") or 0)
    rows = data.get("findings") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return 0, 0
    block = warn = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        sev = str(row.get("severity") or row.get("sev") or "").lower()
        if row.get("resolved") is True:
            continue
        if sev == "block":
            block += 1
        elif sev == "warn":
            warn += 1
    return block, warn


def findings_status(root, ep):
    """Summarize active/stale findings for one episode.

    A findings file older than `_进度.md` may describe a previous production
    state. Report it as stale instead of "unresolved" so progress does not keep
    sending the user into already-superseded return tasks.
    """
    # 用「本集」的 manifest mtime 当陈旧基准，而非整份 _进度.md：给别的集设一列也会 touch
    # _进度.md，会把本集仍未解决的 block 误降级成「已过期」。本集 manifest 只在本集 set 时刷新。
    ep_manifest = os.path.join(root, "脚本", ep, "manifest.json")
    progress_file = os.path.join(root, "_进度.md")
    ref_path = ep_manifest if os.path.exists(ep_manifest) else progress_file
    progress_mtime = os.path.getmtime(ref_path) if os.path.exists(ref_path) else 0
    active = {"block": 0, "warn": 0, "files": 0}
    stale = {"block": 0, "warn": 0, "files": 0}
    for path in glob.glob(os.path.join(root, "生产数据", f"*findings*{ep}.json")):
        try:
            data = json.load(open(path, encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        block, warn = _finding_counts(data)
        if block <= 0 and warn <= 0:
            continue
        bucket = stale if os.path.getmtime(path) < progress_mtime else active
        bucket["block"] += block
        bucket["warn"] += warn
        bucket["files"] += 1
    return active, stale


def report(root, out):
    try:
        header, dict_rows = parse_progress(root)
    except (OSError, ValueError):
        out.append("（_进度.md 无可解析的进度表）")
        return

    flow = flow_columns(header)
    if is_video_first(root):
        out.append("制作模式: 先出视频后配音 ⚠️(快速 demo·不推荐：占位时长锁镜头→后期补真音对不上)")
    elif is_native_av(root):
        out.append("制作模式: 原生音画(native AV)·说话镜由视频后端一次出同步音画；配音=可选旁白层，不卡路由")

    full = sum(1 for r in dict_rows if is_flow_complete(root, r, flow))
    out.append(f"行数: {len(dict_rows)} | 全流程完成: {full}/{len(dict_rows)}")
    out.append("各阶段完成: " + " | ".join(   # 只列流程列；raw 是源文本展示位，不计入完成度
        f"{c} {sum(1 for r in dict_rows if is_progress_satisfied(root, r, c) )}/{len(dict_rows)}"
        for c in flow))

    episodes = [r.get("_ep", "") for r in dict_rows if r.get("_ep")]
    cross_cutting_check(root, out, episodes)  # 横切就绪（合规/身份/LoRA/仪表盘/回灌）+ 观察工具（评分/UI/更新）——不在流程表里但要可见

    findings_gaps = []
    for ep in episodes:
        active, stale = findings_status(root, ep)
        if active["block"] or active["warn"]:
            findings_gaps.append(
                f"  - {ep} 当前 findings: block {active['block']} / warn {active['warn']} "
                f"（{active['files']} 个文件，建议调 n2d-batch 修复或重跑对应 gate）"
            )
        elif stale["block"] or stale["warn"]:
            findings_gaps.append(
                f"  - {ep} 有过期 findings: block {stale['block']} / warn {stale['warn']} "
                "（进度已更新，建议重跑 score/review/gate 刷新，不按旧结果直接返工）"
            )

    gaps = []  # (集, 列, 值, skill, note)
    for r in dict_rows:
        started = any(is_started(r.get(c, "")) for c in flow)
        if started and not is_flow_complete(root, r, flow):
            route = stage_of(root, r, header)
            col = route.get("col") or ""
            val = r.get(col, "").strip() if col else ""
            gaps.append((r.get("_ep", ""), col, val, route.get("skill") or DISPATCHER, route.get("note") or ""))

    if not gaps:
        if full == len(dict_rows):
            out.append("✅ 全部完成。")
        else:
            out.append(f"尚无已开工的集（仅源文本就绪）→ 从第1集起跑：{DISPATCHER}")
        return

    lbl, col, val, skill, note = gaps[0]
    vt = f"（当前 {val}）" if val and val != "⬜" else ""
    out.append(f"前沿: {lbl} → 下一步列「{col}」{vt} → skill: {skill}")
    if note:
        out.append(f"  {note}")
    elif col in COSTLY_HINT:
        out.append(f"  ⚠️ {COSTLY_HINT[col]}")
    parallel = parallel_suggestion(root, dict_rows, header, flow, gaps)
    if parallel:
        out.append(parallel)
    if len(gaps) > 1 or findings_gaps:
        out.append("次要缺口/待办:")
        out.extend(findings_gaps[:3])
        if len(findings_gaps) > 3:
            out.append(f"  - …另有 {len(findings_gaps)-3} 集存在 findings")
        for lbl, col, val, skill, note in gaps[1:6]:
            vt = f"（{val}）" if val and val != "⬜" else "⬜"
            tail = "（补真音后再合成）" if note else ""
            out.append(f"  - {lbl}「{col}」{vt} → {skill}{tail}")
        if len(gaps) > 6:
            out.append(f"  - …另有 {len(gaps)-6} 集已开工待补")


def episode_coverage(root, artifact, episodes):
    """Per-episode artifact coverage for glob patterns such as score_*.json."""
    total = len(episodes)
    if total <= 0:
        return 0, 0
    done = 0
    for ep in episodes:
        pattern = artifact.replace("*", ep)
        if glob.glob(os.path.join(root, pattern)):
            done += 1
    return done, total


def coverage_status(root, item, episodes):
    """Return display mark for a CROSS_CUTTING_READINESS entry.

    Work-level artifacts stay boolean.  Per-episode glob artifacts report N/M,
    preventing one generated score/review UI from looking like whole-work ready.
    """
    art = item.get("artifact")
    required = bool(item.get("required_before"))
    if not art:
        return None
    if "*" in art:
        done, total = episode_coverage(root, art, episodes)
        if total <= 0:
            return "○0/0"
        if done == total:
            return f"✅{done}/{total}"
        if done:
            return f"◐{done}/{total}"
        return f"⚠️0/{total}" if required else f"○0/{total}"
    hit = bool(glob.glob(os.path.join(root, art)))
    if hit:
        return "✅"
    if required:
        return "⚠️缺"
    return "○未跑"


def cross_cutting_check(root, out, episodes=None):
    """横切就绪检查：按契约 CROSS_CUTTING_READINESS 注册表，列各横切 readiness 标志是否在位。
    只读、只提示——合规缺失给 ⚠️（付费硬前置），其余给 ○（按需，未跑不算错）。"""
    if cross_cutting is None:
        return
    episodes = episodes or []
    rows = []
    for item in cross_cutting():
        skill = item.get("skill")
        label = item.get("label")
        mark = coverage_status(root, item, episodes)
        if mark is None:  # 仓库级/无 per-work 标志（如资产库）
            continue
        rows.append(f"{label}({skill}) {mark}")
    if rows:
        out.append("横切就绪: " + " | ".join(rows))
        if any("⚠️缺" in r for r in rows):
            out.append("  ⚠️ 合规包缺失：image 起的付费阶段 gate 会阻断，先跑 n2d-compliance --init")
    # 观察/计划类工具（score/review_ui/update）：有 per-work 产物但只是可选观察输出，
    # 单列「非前置」与「就绪」分开，避免把可选 QA/计划产物误当生产必经步骤。
    tool_rows = []
    if cross_cutting_tools is not None:
        for item in cross_cutting_tools():
            if not item.get("artifact"):
                continue
            mark = coverage_status(root, item, episodes)
            if mark is None:
                continue
            tool_rows.append(f"{item.get('label')}({item.get('skill')}) {mark}")
    if tool_rows:
        out.append("横切观察(可选·非前置): " + " | ".join(tool_rows))


def find_repo_root(start):
    d = os.path.abspath(start)
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, "skills")) and (
            os.path.isfile(os.path.join(d, "AGENTS.md"))
            or os.path.isfile(os.path.join(d, "CLAUDE.md"))
        ):
            return d
        d = os.path.dirname(d)
    return os.path.abspath(start)


def main(argv):
    args = list(argv)
    repo_root = None
    if "--root" in args:
        i = args.index("--root")
        repo_root, args = args[i + 1], args[:i] + args[i + 2:]
    if repo_root is None:
        repo_root = find_repo_root(os.path.dirname(__file__))

    works = []  # (root, rel)
    if args:
        for a in args:
            root = os.path.abspath(a)
            rel = os.path.relpath(root, repo_root)
            if os.path.isfile(os.path.join(root, "_进度.md")):
                works.append((root, rel))
            else:
                print(f"（跳过 {rel}：无 _进度.md）")
    else:
        base = os.path.join(repo_root, LINE_DIR)
        if os.path.isdir(base):
            for name in sorted(os.listdir(base)):
                root = os.path.join(base, name)
                if os.path.isfile(os.path.join(root, "_进度.md")):
                    works.append((root, os.path.join(LINE_DIR, name)))

    if not works:
        print(f"未找到任何含 _进度.md 的剧。线根目录：{LINE_DIR}/")
        return 0

    blocks = []
    for root, rel in works:
        out = [f"=== {rel} ==="]
        report(root, out)
        blocks.append("\n".join(out))
    print("\n\n".join(blocks))
    print(f"\n--- 共 {len(works)} 部剧 ---")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
