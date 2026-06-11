#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smart Update Dispatcher.

Automatically detects the current production line based on directory
structure and routes the update/snapshot check to the appropriate script.
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
    ap = argparse.ArgumentParser(description="智能更新分发：自动探测并调用各产线自己的 update")
    ap.add_argument("cmd", choices=["check", "record"], help="执行的操作")
    ap.add_argument("project_root", nargs="?", default=".", help="作品根目录，默认当前目录")
    ap.add_argument("cmd_args", nargs=argparse.REMAINDER, help="传递给底层 update 脚本的附加参数")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    
    script_to_call = None
    line_name = "unknown"
    
    # 启发式探测产线
    if "/写歌/" in root or os.path.exists(os.path.join(root, "词", "lyrics.md")):
        line_name = "song"
    elif "/制MV/" in root or os.path.exists(os.path.join(root, "视觉蓝图.md")):
        line_name = "mv"
    elif "/制漫剧/" in root or os.path.exists(os.path.join(root, "出图")):
        script_to_call = find_script("skills/n2d-update/scripts/update_plan.py")
        line_name = "n2d"
    elif "/写小说/" in root or os.path.exists(os.path.join(root, "章节")):
        line_name = "novel"
    
    if not script_to_call or not os.path.exists(script_to_call):
        print(f"[提示] 检测到 {line_name} 产线上下文。")
        if line_name == "novel":
            print("当前小说系列依赖 novel-review/self_audit.py 做审计，尚未接入自动化快照与重制计划。")
        else:
            print(f"该产线 ({line_name}) 目前暂未实现独立的自动化更新嗅探脚本。")
        sys.exit(0)
        
    print(f"[dispatch] 检测到 {line_name} 产线上下文，正在路由至专属工具...\n")
    
    cmd = [sys.executable, script_to_call, args.cmd, root] + args.cmd_args
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)

if __name__ == "__main__":
    main()
