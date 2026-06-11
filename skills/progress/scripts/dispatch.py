#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smart Progress Dispatcher.

Automatically detects the current production line based on directory
structure and routes the progress check to the appropriate script.
"""

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

def find_script(relative_path: str) -> str:
    return os.path.join(REPO, relative_path)

def main():
    ap = argparse.ArgumentParser(description="智能进度分发：自动探测并调用各产线自己的 progress")
    ap.add_argument("project_root", nargs="?", default=".", help="作品根目录，默认当前目录")
    ap.add_argument("cmd_args", nargs=argparse.REMAINDER, help="传递给底层 progress 脚本的附加参数")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    
    script_to_call = None
    line_name = "unknown"
    
    # 启发式探测产线
    if "/写歌/" in root or os.path.exists(os.path.join(root, "词", "lyrics.md")):
        # 假设写歌线也有类似的 progress.py，如果没有则退回提示
        script_to_call = find_script("skills/song-craft/scripts/progress.py")
        line_name = "song"
    elif "/制MV/" in root or os.path.exists(os.path.join(root, "视觉蓝图.md")):
        script_to_call = find_script("skills/mv-craft/scripts/progress.py")
        line_name = "mv"
    elif "/制漫剧/" in root or os.path.exists(os.path.join(root, "出图")):
        script_to_call = find_script("skills/n2d-progress/scan.py")
        line_name = "n2d"
    elif "/写小说/" in root or os.path.exists(os.path.join(root, "章节")):
        script_to_call = find_script("skills/novel-craft/scripts/progress.py")
        line_name = "novel"
    
    if not script_to_call or not os.path.exists(script_to_call):
        print(f"[err] 无法识别产线上下文，或对应产线的进度脚本 ({script_to_call}) 不存在。")
        print("请提供准确的作品根目录，例如：python3 dispatch.py 写小说/某书")
        sys.exit(1)
        
    print(f"[dispatch] 检测到 {line_name} 产线上下文，正在路由至专属工具...\n")
    
    cmd = [sys.executable, script_to_call, root] + args.cmd_args
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)

if __name__ == "__main__":
    main()
