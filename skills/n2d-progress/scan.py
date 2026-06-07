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
import json
import os
import re
import sys

LINE_DIR = "制漫剧"  # 只管 n2d 这一条线

# 列名关键词 → n2d stage skill（命中第一个关键词即用）。
STAGE_RULES = [
    (("配音",), "n2d-voice"),
    (("出图", "定妆"), "n2d-image"),
    (("视频",), "n2d-video"),
    (("成片", "合成"), "n2d-compose"),
    (("改编", "bgm", "封面", "分镜", "素材", "字幕"), "n2d-script"),
]
DISPATCHER = "novel2drama"  # 认不出列名时兜底

# 花钱/不可逆/合规的前沿列 → 提醒先确认。
COSTLY_HINT = {
    "出图": "会真出图·消耗额度 → 开跑前确认生图后端 + 重抽预算档位；分镜 PNG 前共享定妆库 出图/common/ 必须全 ✅",
    "视频": "会真出视频·消耗额度 → 开跑前确认生视频后端",
    "成片": "合成成片（混音+烧字幕），相对便宜但耗时",
    "配音": "声音克隆需肖像/音色授权（合规闸门）",
}

META_COLS = {"集", "字数", "序号", "#"}  # 索引/计量列，不算阶段


def is_done(cell):
    c = cell.strip()
    if c == "✅":
        return True
    m = re.match(r"^(\d+)\s*/\s*(\d+)$", c)
    return bool(m) and int(m.group(2)) > 0 and int(m.group(1)) == int(m.group(2))


def is_started(cell):
    c = cell.strip()
    if c == "✅":
        return True
    m = re.match(r"^(\d+)\s*/\s*(\d+)$", c)
    return bool(m) and int(m.group(1)) > 0


def parse_table(text):
    """提取第一张 markdown 管道表。返回 (header, rows) 或 (None, None)。"""
    lines = [ln for ln in text.splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return None, None
    cells = lambda ln: [p.strip() for p in ln.strip().strip("|").split("|")]
    header = cells(lines[0])
    rows = []
    for ln in lines[1:]:
        if re.match(r"^\s*\|[\s:|-]+\|\s*$", ln):  # 分隔行 |---|
            continue
        c = cells(ln)
        if len(c) == len(header):
            rows.append(c)
    return header, rows


def next_skill(col):
    for keys, skill in STAGE_RULES:
        if any(k.lower() in col.lower() for k in keys):
            return skill
    return DISPATCHER


def read_mode(root):
    """读 _设置.md 的 `制作模式`（缺则默认 配音先行）。"""
    p = os.path.join(root, "_设置.md")
    if not os.path.isfile(p):
        return "配音先行"
    try:
        with open(p, encoding="utf-8") as f:
            txt = f.read()
    except OSError:
        return "配音先行"
    m = re.search(r"制作模式\s*[:：]\s*([^\s#]+)", txt)
    return m.group(1) if m else "配音先行"


def voice_is_placeholder(root, ep):
    """该集真实配音是否还没补（时长清单仍含占位句）。
    返回 True=仍占位 / False=已是真音 / None=无清单可判。"""
    p = os.path.join(root, "出视频", ep, "配音", "时长清单.json")
    if not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if isinstance(data, list):
        return any(isinstance(x, dict) and x.get("占位") for x in data)
    return None


def report(root, out):
    with open(os.path.join(root, "_进度.md"), encoding="utf-8") as f:
        header, rows = parse_table(f.read())
    if not header or not rows:
        out.append("（_进度.md 无可解析的进度表）")
        return

    label_i = 0
    disp_idx = [i for i, h in enumerate(header)
                if h not in META_COLS and i != label_i]
    flow_idx = [i for i in disp_idx if header[i] != "raw"]  # 流程列(排除源文本)

    mode = read_mode(root)
    alt = "先出视频" in mode  # 制作模式=先出视频后配音（快速 demo·不推荐）
    if alt:
        out.append("制作模式: 先出视频后配音 ⚠️(快速 demo·不推荐：占位时长锁镜头→后期补真音对不上)")

    full = sum(1 for r in rows if all(is_done(r[i]) for i in flow_idx))
    out.append(f"行数: {len(rows)} | 全流程完成: {full}/{len(rows)}")
    out.append("各阶段完成: " + " | ".join(   # 只列流程列；raw 是源文本展示位，不计入完成度
        f"{header[i]} {sum(1 for r in rows if is_done(r[i]))}/{len(rows)}"
        for i in flow_idx))

    gaps = []  # (集, 列, 值, skill, note)
    for r in rows:
        started = any(is_started(r[i]) for i in flow_idx)
        if started and not all(is_done(r[i]) for i in flow_idx):
            for i in flow_idx:
                if not is_done(r[i]):
                    col, val = header[i], r[i].strip()
                    skill, note = next_skill(col), ""
                    # 先出视频后配音模式：视频已出、只差成片时，progress.py 的线性
                    # 路由会直接指向 n2d-compose——但此模式下「配音 ✅」很可能仍是占位，
                    # 合成前必须先补真实配音。这里在前沿层把它拦回 n2d-voice。
                    if alt and skill == "n2d-compose" \
                            and voice_is_placeholder(root, r[label_i].strip()):
                        skill = "n2d-voice"
                        note = ("⚠️先出视频后配音模式：当前配音仍是占位，合成前"
                                "必须先 /n2d-voice 补真实配音，再 /n2d-compose 把"
                                "真音拟合到已成片镜头长（见 n2d-compose「先出视频后配音」节）")
                    gaps.append((r[label_i], col, val, skill, note))
                    break

    if not gaps:
        if full == len(rows):
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
