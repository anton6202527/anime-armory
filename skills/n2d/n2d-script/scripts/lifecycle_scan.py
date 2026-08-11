#!/usr/bin/env python3
"""lifecycle_scan.py — 跨集角色形象生命周期预扫（Gap2）。

为什么存在：n2d 的角色卡是"逐集建/首现补"+ visual_contract 的"集内状态演进"，但**跨集**的
造型/年龄/服装/形态里程碑（第3集换嫁衣、第20集年龄跳、第40集黑化造型）没有一个**全局产物**——
等到第 N 集才发现"该变造型但定妆库已锁死"=返工。对标字节小云雀短剧 Agent 的"全局角色管理·
全生命周期形象变化(年龄/服饰/面部)自动扫描"。

本脚本确定性预扫 脚本/第N集/raw.txt（缺则退回 小说/<剧>.txt 不分集），扫"时间跳跃/年龄、
换装/造型、形态变体/状态"三类里程碑信号，产出 设定库/characters/_生命周期.md（集号→里程碑→
涉及角色→形象变化→定妆动作）。仅启发式：检测=候选，人确认后才落角色卡『形态变体』与建/换定妆。

用法:
    python3 lifecycle_scan.py <作品根>            # dry-run：打印候选里程碑
    python3 lifecycle_scan.py <作品根> --write    # 写/刷新 设定库/characters/_生命周期.md
    python3 lifecycle_scan.py <作品根> --json
"""
import json
import os
import re
import sys
from pathlib import Path

# 里程碑信号词典（题材无关·跨集形象演进）。命中=候选，最终由人判。
MILESTONE_SIGNALS = (
    ("时间/年龄", re.compile(
        r"(年后|多年后|数年后|十年后|转眼|及笄|加冠|成年|长大成人|长大了|岁那年|"
        r"光阴荏苒|时光荏苒|物是人非|白驹过隙|又过了|一晃|翌年|来年|垂垂老矣|苍老)")),
    ("换装/造型", re.compile(
        r"(换上|披上|卸下|脱下|换了身|重新梳妆|改换装束|嫁衣|喜服|战甲|铠甲|丧服|孝衣|"
        r"龙袍|凤冠|华服|盛装|素衣|布衣|剪短|剃发|盘发|束发|易容|改妆|卸妆|换上夜行衣|戎装)")),
    ("形态/状态", re.compile(
        r"(觉醒|黑化|重伤|毁容|破相|疤痕|留疤|断臂|断腿|失明|瞎了|白发|白头|华发|"
        r"中毒|面具|蒙面|银发|金瞳|赤瞳|变身|化形|现出原形|解除伪装|恢复真容|返老还童|苍老十岁)")),
)

CHAPTER_HEAD = re.compile(r"^\s*(?:\[编辑\]\s*)?第\s*[零〇一二三四五六七八九十百千万两0-9]+\s*[章回囬囘廻节節卷]")
AUTO_MARKER = "<!-- AUTO:lifecycle_scan 以下为每次扫描重生成，勿手改；人工确认请写到上方「人工确认时间线」 -->"


def ep_num(path):
    m = re.search(r"第(\d+)集", path.name)
    return int(m.group(1)) if m else -1


def known_characters(root):
    """从 设定库/characters/*.md 卡名取已建卡角色名（排除总表/生命周期）。"""
    cdir = Path(root) / "设定库" / "characters"
    names = []
    if cdir.is_dir():
        for f in cdir.glob("*.md"):
            stem = f.stem
            if stem.startswith("_"):
                continue
            names.append(stem)
    return names


def load_units(root):
    """返回 [(标签, 文本)]：优先逐集 raw；缺则退回整本小说（不分集，标签=全本）。"""
    sdir = Path(root) / "脚本"
    units = []
    if sdir.is_dir():
        for d in sorted(sdir.glob("第*集"), key=ep_num):
            raw = d / "raw.txt"
            if raw.exists():
                units.append((f"第{ep_num(d)}集", raw.read_text(encoding="utf-8")))
    if units:
        return units
    novel = Path(root) / "小说"
    if novel.is_dir():
        for f in sorted(novel.glob("*.txt")):
            return [("全本", f.read_text(encoding="utf-8", errors="replace"))]
    return units


def scan(root):
    names = known_characters(root)
    milestones = []
    for label, text in load_units(root):
        chars_here = [n for n in names if n in text]
        for cat, rx in MILESTONE_SIGNALS:
            for m in rx.finditer(text):
                s = max(0, m.start() - 14)
                e = min(len(text), m.end() + 14)
                snippet = re.sub(r"\s+", "", text[s:e])
                milestones.append({
                    "unit": label,
                    "category": cat,
                    "signal": m.group(0),
                    "snippet": snippet,
                    "characters": chars_here,
                })
    # 同 unit+category+signal 去重（取首个片段）
    seen, dedup = set(), []
    for ms in milestones:
        k = (ms["unit"], ms["category"], ms["signal"])
        if k in seen:
            continue
        seen.add(k)
        dedup.append(ms)
    return dedup, names


def render_md(root, milestones, names):
    lines = ["# 角色形象生命周期时间线（跨集·全局产物）", ""]
    lines.append("> 拆集/建卡阶段预规划：每个里程碑=某角色在某集的**造型/年龄/服装/标志变化**。")
    lines.append("> 用途：① 提前规划定妆库何时该派生新『形态变体』，避免锁死后到第N集才发现要变；")
    lines.append("> ② n2d-identity 跨集漂移报表的**预期变化基线**——里程碑解释的形象变化=合法演进，")
    lines.append("> 里程碑之外的形象变化=漂移(崩脸/服装漂)。人确认后把变体写回对应角色卡『形态变体』并建/换定妆。")
    lines.append("")
    lines.append("## 人工确认时间线")
    lines.append("（人工把下方自动候选确认/合并/补全到这里：集号 → 角色 → 形象变化 → 定妆动作）")
    lines.append("")
    lines.append("| 集 | 角色 | 形象变化 | 定妆动作（新建变体/换卡/沿用） |")
    lines.append("|---|---|---|---|")
    lines.append("| | | | |")
    lines.append("")
    lines.append(AUTO_MARKER)
    lines.append("")
    lines.append(f"## 自动检测里程碑候选（已建卡角色：{('、'.join(names)) or '（暂无角色卡，先建卡再扫描可归属角色）'}）")
    if not milestones:
        lines.append("")
        lines.append("（未检测到跨集形象里程碑信号——题材可能无明显年龄跳/换装/形态变体；仍按剧情人工核。）")
        return "\n".join(lines) + "\n"
    lines.append("")
    lines.append("| 集 | 信号类别 | 触发词 | 片段 | 疑似涉及角色 | 待人确认 |")
    lines.append("|---|---|---|---|---|---|")
    for ms in milestones:
        chars = "、".join(ms["characters"]) or "（待填）"
        lines.append(f"| {ms['unit']} | {ms['category']} | {ms['signal']} | …{ms['snippet']}… | {chars} | 形象变化?/需新变体? |")
    return "\n".join(lines) + "\n"


def write_md(root, content):
    out = Path(root) / "设定库" / "characters" / "_生命周期.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    # 保留人工区：若已存在且含 AUTO_MARKER，保留 marker 之前的人工内容，只重生成自动段。
    if out.exists():
        old = out.read_text(encoding="utf-8")
        if AUTO_MARKER in old:
            human = old.split(AUTO_MARKER)[0].rstrip()
            auto = content.split(AUTO_MARKER, 1)[1]
            content = human + "\n\n" + AUTO_MARKER + auto
    out.write_text(content, encoding="utf-8")
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        print("用法: lifecycle_scan.py <作品根> [--write] [--json]")
        sys.exit(2)
    root = args[0]
    milestones, names = scan(root)
    if "--json" in flags:
        print(json.dumps({"characters": names, "milestones": milestones},
                         ensure_ascii=False, indent=2))
        return
    content = render_md(root, milestones, names)
    if "--write" in flags:
        out = write_md(root, content)
        print(f"已写 {out}（保留人工确认区）。检测到 {len(milestones)} 个里程碑候选；"
              f"已建卡角色 {len(names)} 个。人确认后落角色卡『形态变体』。")
    else:
        print(content)
        print(f"\n[dry-run] {len(milestones)} 个里程碑候选。--write 落 设定库/characters/_生命周期.md。")


if __name__ == "__main__":
    main()
