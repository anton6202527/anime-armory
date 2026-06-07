#!/usr/bin/env python3
"""n2d-progress/scan.py — 制漫剧(novel2drama)进度扫描器（只读）。

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
import os
import re
import sys

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'common'))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from n2d_route import flow_columns, is_done, is_started, parse_progress, stage_of
from n2d_settings import is_video_first

LINE_DIR = "制漫剧"  # 只管 n2d 这一条线

DISPATCHER = "novel2drama"  # 认不出列名时兜底

# 花钱/不可逆/合规的前沿列 → 提醒先确认。
COSTLY_HINT = {
    "出图": "会真出图·消耗额度 → 开跑前确认生图后端 + 重抽预算档位；分镜 PNG 前共享定妆库 出图/common/ 必须全 ✅",
    "视频": "会真出视频·消耗额度 → 开跑前确认生视频后端",
    "成片": "合成成片（混音+烧字幕），相对便宜但耗时",
    "配音": "声音克隆需肖像/音色授权（合规闸门）",
}

def report(root, out):
    try:
        header, dict_rows = parse_progress(root)
    except (OSError, ValueError):
        out.append("（_进度.md 无可解析的进度表）")
        return

    flow = flow_columns(header)
    if is_video_first(root):
        out.append("制作模式: 先出视频后配音 ⚠️(快速 demo·不推荐：占位时长锁镜头→后期补真音对不上)")

    full = sum(1 for r in dict_rows if all(is_done(r.get(c, "")) for c in flow))
    out.append(f"行数: {len(dict_rows)} | 全流程完成: {full}/{len(dict_rows)}")
    out.append("各阶段完成: " + " | ".join(   # 只列流程列；raw 是源文本展示位，不计入完成度
        f"{c} {sum(1 for r in dict_rows if is_done(r.get(c, '')) )}/{len(dict_rows)}"
        for c in flow))

    gaps = []  # (集, 列, 值, skill, note)
    for r in dict_rows:
        started = any(is_started(r.get(c, "")) for c in flow)
        if started and not all(is_done(r.get(c, "")) for c in flow):
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
    if len(gaps) > 1:
        out.append("次要缺口:")
        for lbl, col, val, skill, note in gaps[1:6]:
            vt = f"（{val}）" if val and val != "⬜" else "⬜"
            tail = "（补真音后再合成）" if note else ""
            out.append(f"  - {lbl}「{col}」{vt} → {skill}{tail}")
        if len(gaps) > 6:
            out.append(f"  - …另有 {len(gaps)-6} 集已开工待补")


def find_repo_root(start):
    d = os.path.abspath(start)
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, "skills")) and \
           os.path.isfile(os.path.join(d, "CLAUDE.md")):
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
