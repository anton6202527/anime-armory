#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""源同步守望 —— Stop hook 用。扫所有有源指纹的漫剧，写小说成品一改就提示。

每次 Claude 回完话由 Stop hook 调用：遍历 `制漫剧/*/小说/_源指纹.json`，
对比当前真源（同名 写小说/<剧>/章节）与基线指纹，**只在发现漂移时**打一行提醒
（clean/无基线/出错全静默，零噪声）。永远 exit 0，不打断。

手动也可跑：python3 source_watch.py [仓库根]   （默认 CWD = 项目根，hook 即如此）
"""
import os, sys, glob, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import source_check as sc
except Exception:
    sys.exit(0)


def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    drifts = []
    for fp in glob.glob(os.path.join(repo, "制漫剧", "*", "小说", "_源指纹.json")):
        root = os.path.dirname(os.path.dirname(fp))
        try:
            cur, _label, _kind = sc.resolve_source(root, None)
            base = json.load(open(fp, encoding="utf-8"))
            old = {int(k): v for k, v in base.get("chapter_hashes", {}).items()}
            changed = sorted(ch for ch in cur if ch in old and cur[ch] != old[ch])
            added = sorted(set(cur) - set(old))
            removed = sorted(set(old) - set(cur))
            if not (changed or added or removed):
                continue
            chap_to_eps = sc.map_chapter_to_eps(root)
            prog = sc.ep_progress(root)
            risky = [ch for ch in changed + added
                     if any(prog.get(e) for e in chap_to_eps.get(ch, []))]
            drifts.append((os.path.basename(root), changed, added, removed, risky))
        except Exception:
            continue  # 守望不能因单个作品出错而打断 Stop

    if drifts:
        print("⚠️ 源同步提醒：写小说成品已变动，对应漫剧源过期——")
        for name, ch, ad, rm, risky in drifts:
            line = f"  · 《{name}》变动章 {ch}"
            if ad: line += f" 新增 {ad}"
            if rm: line += f" 删除 {rm}"
            if risky: line += f"  ⚠️其中触及【已生产集】的章：{risky}（重切/重配前逐集确认）"
            print(line)
        print("  → 看落集+处置：`python3 skills/novel2drama/source_check.py <漫剧作品根>`；"
              "处理完用 `--record` 更新基线。")
    sys.exit(0)


if __name__ == "__main__":
    main()
