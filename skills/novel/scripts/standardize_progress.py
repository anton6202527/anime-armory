#!/usr/bin/env python3
"""standardize_progress.py — 将旧版 novel 进度表转换为标准矩阵格式。

支持从以下形态提取：
1. 自由格式 Checklist (- [x] 第N章 ...)
2. 旧版 4 列 Table (| 章 | 标题 | 字数 | 状态 |)
3. 纯文本行

用法：
  python3 standardize_progress.py <作品根> [--dry-run]
"""
import os
import sys
import re
import json

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.abspath(os.path.join(_HERE, "..", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from novel_contract import build_progress_markdown, routing_stages, PROGRESS_DONE, PROGRESS_TODO
from novel_route import chapter_number, progress_path

def extract_chapter_states(content):
    """从旧内容中尽可能提取各章的'完成'状态。"""
    states = {} # {num: is_done}
    
    # 1. Checklist 形态: - [x] 第12章
    checklist_re = re.compile(r"^\s*-\s*\[([xX ])\]\s*(.+)$", re.MULTILINE)
    for m in checklist_re.finditer(content):
        done = m.group(1).lower() == 'x'
        num = chapter_number(m.group(2))
        if num:
            states[num] = states.get(num, False) or done

    # 2. 表格形态: | 12 | ... | ✅ |
    # 简单寻找包含 ✅ 的行
    for line in content.splitlines():
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                num = chapter_number(parts[1])
                if num:
                    # 只要列中包含 ✅ 或 [x] 就认为完成
                    is_done = any("✅" in p or "[x]" in p.lower() for p in parts[2:])
                    states[num] = states.get(num, False) or is_done
                    
    return states

def main():
    if len(sys.argv) < 2:
        print("用法: standardize_progress.py <作品根> [--dry-run]")
        sys.exit(1)
        
    root = os.path.abspath(sys.argv[1])
    dry_run = "--dry-run" in sys.argv
    
    p_path = progress_path(root)
    if not os.path.exists(p_path):
        print(f"找不到进度文件: {p_path}")
        sys.exit(1)
        
    content = open(p_path, encoding="utf-8").read()
    
    # 如果已经是新版（含 novel-progress-schema），跳过
    if "novel-progress-schema" in content:
        print("✅ 已经是标准格式。")
        return

    # 提取状态
    states = extract_chapter_states(content)
    if not states:
        print("⚠️ 未能提取到任何章节状态。")
        max_ch = 10 # 默认
    else:
        max_ch = max(states.keys())
        print(f"找到 {len(states)} 个章节状态，最高第 {max_ch} 章。")

    # 获取元数据
    meta_path = os.path.join(root, "_meta.json")
    title = os.path.basename(root)
    kind = "unknown"
    if os.path.exists(meta_path):
        meta = json.load(open(meta_path, encoding="utf-8"))
        title = meta.get("title") or title
        kind = meta.get("kind", "unknown")
        max_ch = meta.get("target_chapters", max_ch)

    # 生成新进度
    new_md = build_progress_markdown(title, kind, max_ch)
    
    # 填入已完成的状态 (假设已完成的章节 '正文初稿' 为 ✅)
    # 对于小说管线，如果旧进度说'完成'，我们保守地认为 '大纲'/'细纲'/'正文初稿' 都完成了。
    lines = new_md.splitlines()
    out_lines = []
    header = None
    for line in lines:
        if line.startswith("| 第"):
            parts = [p.strip() for p in line.split("|")]
            num = chapter_number(parts[1])
            if num in states and states[num]:
                # 找到 '正文初稿' 列下标
                if not header:
                    # 向上找表头
                    for prev in reversed(out_lines):
                        if prev.startswith("| 章节"):
                            header = [h.strip() for h in prev.split("|")[1:-1]]
                            break
                
                if header:
                    # 标记 大纲, 细纲, 正文初稿 为完成
                    for stage in ["大纲", "细纲", "正文初稿"]:
                        if stage in header:
                            idx = header.index(stage) + 1 # +1 because of 章节/标题/字数 prefix and | index
                            # Wait, parts[1] is 章节, parts[2] is 标题, parts[3] is 字数. 
                            # header[0] is 章节. So idx is exactly the part index.
                            if idx < len(parts):
                                parts[idx] = PROGRESS_DONE
            line = "| " + " | ".join(parts[1:-1]) + " |"
        out_lines.append(line)

    final_md = "\n".join(out_lines) + "\n\n## 历史记录 (迁移自旧版)\n" + content

    if dry_run:
        print("--- NEW PROGRESS.MD (PREVIEW) ---")
        print(final_md[:1000] + "...")
    else:
        # 备份旧文件
        os.rename(p_path, p_path + ".bak")
        with open(p_path, "w", encoding="utf-8") as f:
            f.write(final_md)
        print(f"✅ 进度表已标准化：{p_path}")

if __name__ == "__main__":
    main()
