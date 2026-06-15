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
import json

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILLS = os.path.abspath(os.path.join(_HERE, "..", ".."))
_LIB = os.path.abspath(os.path.join(_HERE, "..", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from project_io import load_project_settings

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def is_n2d_bound(root, meta, settings):
    if meta.get("scale") == "漫剧" or meta.get("kind") == "漫剧源书":
        return True
    platform = str(settings.get("目标平台", "")).lower()
    if any(k in platform for k in ["漫剧", "短剧", "n2d"]):
        return True
    return False

def main():
    p = argparse.ArgumentParser(description="novel 写后自动化 Hook")
    p.add_argument("root")
    p.add_argument("--chapter", required=True, help="刚刚写完的章号")
    args = p.parse_args()

    root = os.path.abspath(args.root)
    ch = args.chapter # e.g. "第01章"
    
    # Extract number from chapter string
    import re
    m = re.search(r"(\d+)", ch)
    if not m:
        print(f"[err] 无法从章号识别数字: {ch}", file=sys.stderr)
        sys.exit(1)
    ch_num = int(m.group(1))
    ch_padded = f"第{ch_num:02d}章"

    meta = load_json(os.path.join(root, "_meta.json"))
    settings = load_project_settings(root)
    
    # 1. 更新进度
    print(f"🔄 正在更新进度：{ch_padded} 正文初稿 ✅")
    prog_script = os.path.join(_HERE, "..", "progress.py")
    subprocess.run([sys.executable, prog_script, "set", root, ch_padded, "正文初稿", "✅"], check=True)

    # 2. 状态账本对账 (Audit)
    delta_path = os.path.join(root, "审稿", f"state_delta_{ch_padded}.json")
    if os.path.exists(delta_path):
        print(f"🔄 正在运行状态账本对账 (Audit)...")
        reconcile_script = os.path.join(_HERE, "..", "..", "novel-craft", "scripts", "reconcile_ledger.py")
        subprocess.run([sys.executable, reconcile_script, root, "--chapter", str(ch_num), "--audit"], check=True)
    else:
        print(f"⚠️ 缺失状态增量文件：{delta_path}")
        print(f"  [建议] 请先提取本章状态变动并写入该 JSON，再重跑 post_write。")

    # 3. 增量更新百科
    print(f"🔄 正在提取百科事实...")
    wiki_script = os.path.join(_HERE, "..", "..", "novel-wiki", "scripts", "wiki_builder.py")
    subprocess.run([sys.executable, wiki_script, root, "--chapter", str(ch_num)], check=True)

    # 4. 逻辑哨兵
    print(f"🔄 正在运行逻辑哨兵...")
    sentry_script = os.path.join(_HERE, "..", "..", "novel-wiki", "scripts", "logic_sentry.py")
    subprocess.run([sys.executable, sentry_script, root, "--chapter", str(ch_num)], check=True)

    # 5. N2D 就绪检查 (如果是漫剧项目)
    if is_n2d_bound(root, meta, settings):
        print(f"🔄 检测到漫剧/短剧项目，正在运行 N2D 就绪机检...")
        n2d_script = os.path.join(_HERE, "..", "..", "novel-review", "scripts", "n2d_readiness_check.py")
        subprocess.run([sys.executable, n2d_script, root, "--range", str(ch_num)], check=True)

    print(f"\n✅ 任务完成！{ch_padded} 已准备好进入 Review 阶段。")
    print(f"  [下一步] 请核对对账 Prompt，保存核对结论 JSON 后合并账本：")
    print(f"  python3 skills/novel-craft/scripts/reconcile_ledger.py \"{root}\" --chapter {ch_num} --merge --verified <结论.json>")

if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
