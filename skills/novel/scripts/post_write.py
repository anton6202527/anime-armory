#!/usr/bin/env python3
"""post_write.py — novel 管线“写完一章”后的自动化 Hook。

执行以下操作：
1. 更新 _进度.md：将该章的“正文初稿”标记为 ✅。
2. 增量更新百科：扫描该章并提取新事实。
3. 运行逻辑哨兵：检查是否有硬性冲突。

用法：
  python3 post_write.py <作品根> --chapter <章号>
"""
import os
import sys
import argparse
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.abspath(os.path.join(_HERE, "..", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from novel_route import normalize_episode

def main():
    p = argparse.ArgumentParser(description="novel 写后自动化 Hook")
    p.add_argument("root")
    p.add_argument("--chapter", required=True, help="刚刚写完的章号")
    args = p.parse_args()

    root = os.path.abspath(args.root)
    ch = args.chapter # e.g. "第01章"
    
    # 1. 更新进度
    print(f"🔄 正在更新进度：{ch} 正文初稿 ✅")
    prog_script = os.path.join(_HERE, "..", "progress.py")
    subprocess.run([sys.executable, prog_script, "set", root, ch, "正文初稿", "✅"], check=True)

    # 2. 增量更新百科
    print(f"🔄 正在提取百科事实...")
    wiki_script = os.path.join(_HERE, "..", "..", "novel-wiki", "scripts", "wiki_builder.py")
    # Extract number from chapter string
    import re
    ch_num = re.search(r"(\d+)", ch).group(1)
    subprocess.run([sys.executable, wiki_script, root, "--chapter", ch_num], check=True)

    # 3. 逻辑哨兵
    print(f"🔄 正在运行逻辑哨兵...")
    sentry_script = os.path.join(_HERE, "..", "..", "novel-wiki", "scripts", "logic_sentry.py")
    subprocess.run([sys.executable, sentry_script, root, "--chapter", ch_num], check=True)

    print(f"✅ 任务完成！第 {ch_num} 章已准备好进入 Review 阶段。")

if __name__ == "__main__":
    main()
