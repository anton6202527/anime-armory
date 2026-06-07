#!/usr/bin/env python3
"""Audit raw episode boundaries before n2d-script stage-1 refinement.

Usage:
  python3 skills/n2d-script/scripts/boundary_audit.py <作品根> [start-end]

This is a deterministic pre-check. It does not decide story quality by itself;
it flags episodes that need human/LLM boundary review before writing voiceover.
"""
import os
import re
import statistics
import sys
from pathlib import Path


# 集尾强钩信号（通用·不绑具体作品）：悬念标点 + 反转/突变/疑问/紧迫类词。
# 仅启发式——最终钩力由人/LLM 精修判；命中=暂判有钩，未命中=「弱钩待判」提示补强。
STRONG_END = re.compile(
    r"(？|！|…|——|\?|!"                           # 悬念/惊叹/省略/破折号收尾
    r"|竟然?|居然|原来|没想到|不料|岂料"             # 反转揭示
    r"|突然|猛地?|骤然|霎时|忽然"                    # 突变
    r"|难道|莫非|是谁|什么|为什么|怎么|凭什么"        # 疑问钩
    r"|来了|出事|不好了|糟了|完了)"                  # 紧迫
    r"\s*$"
)
CHAPTER_HEAD = re.compile(r"^第[一二三四五六七八九十百千万0-9]+章")


def cjk_len(text):
    return len(re.findall(r"[\u3400-\u9fff]", text))


def ep_num(path):
    m = re.search(r"第(\d+)集", path.name)
    return int(m.group(1)) if m else -1


def load_rows(root):
    script_root = Path(root) / "脚本"
    rows = []
    for d in sorted(script_root.glob("第*集"), key=ep_num):
        raw = d / "raw.txt"
        if not raw.exists():
            continue
        text = raw.read_text(encoding="utf-8").strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        rows.append({
            "ep": ep_num(d),
            "chars": cjk_len(text),
            "chapter": bool(CHAPTER_HEAD.search(text)),
            "start": "".join(lines[:2])[:90] if lines else "",
            "end": "".join(lines[-3:])[-140:] if lines else "",
            "soft_end": bool(text and text[-1] in "，、；："),
            "strong_end": bool(STRONG_END.search(text[-160:])),
        })
    return rows


def main():
    if len(sys.argv) < 2:
        print("用法: boundary_audit.py <作品根> [start-end]")
        sys.exit(2)
    root = sys.argv[1]
    rows = load_rows(root)
    if not rows:
        print("未找到 脚本/第N集/raw.txt")
        sys.exit(1)
    if len(sys.argv) >= 3:
        m = re.match(r"(\d+)-(\d+)$", sys.argv[2])
        if not m:
            print("范围格式应为 start-end，例如 2-10")
            sys.exit(2)
        a, b = map(int, m.groups())
        rows = [r for r in rows if a <= r["ep"] <= b]

    chars = [r["chars"] for r in rows]
    print(f"episodes={len(rows)} chars_min={min(chars)} chars_max={max(chars)} "
          f"chars_avg={statistics.mean(chars):.1f} chars_median={statistics.median(chars):.0f}")
    print()
    print("| 集 | 字数 | 章头 | 标记 | 处理建议 |")
    print("|---|---:|---|---|---|")
    for r in rows:
        flags = []
        advice = []
        if r["chars"] < 650:
            flags.append("短")
            advice.append("核是否并入相邻集")
        if r["chars"] > 1100:
            flags.append("长")
            advice.append("配音后核是否拆镜/拆集")
        if r["soft_end"]:
            flags.append("软断")
            advice.append("右边界后移到完整钩子")
        if not r["chapter"]:
            flags.append("章内续切")
        if not r["strong_end"]:
            flags.append("弱钩待判")
            advice.append("精修时补强集尾钩")
        print(f"| 第{r['ep']}集 | {r['chars']} | {'是' if r['chapter'] else '否'} | "
              f"{'、'.join(flags) or 'OK'} | {'；'.join(advice) or '保留'} |")


if __name__ == "__main__":
    main()
