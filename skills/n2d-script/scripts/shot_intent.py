#!/usr/bin/env python3
"""shot_intent.py — 写逐镜创作意图黑板 `脚本/<集>/shot_intent.json`（派生投影 + 演进 override）。

分镜定稿后由 script 阶段调用：把逐镜意图（expression_span/need_endframe/motion_intensity/景别/
action_beat/identity_requirement）投影到黑板，并保留 allowed_evolution（允许的演进白名单）。
派生字段仍以 storyboard.json 为权威；手改本文件不会覆盖 gate 或生成侧行为。唯一作者 override
通道是 allowed_evolution，用来声明某镜某角色的脸/发/服装/道具演进，补关键词漏检。

核心逻辑在 n2d/_lib/n2d_intent.py（纯函数·可测）；本脚本只是 script 侧入口。
重建时**保留作者已声明**（source="author"）的 allowed_evolution 条目，不覆盖人工意图。

用法：
  python3 shot_intent.py <作品根> 第N集            # 构建并落盘（dry-run 见 --json）
  python3 shot_intent.py <作品根> 第N集 --json      # 只打印将写入的对象，不落盘
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "n2d", "_lib"))
import n2d_intent  # noqa: E402  逐镜意图黑板 builder/writer 单一真值源


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="写逐镜创作意图黑板 shot_intent.json")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true", help="只打印对象不落盘")
    ns = ap.parse_args(argv)
    root = ns.root.rstrip("/")
    if ns.json:
        prior = n2d_intent._load_json(n2d_intent.shot_intent_path(root, ns.episode))
        obj = n2d_intent.build_shot_intent(root, ns.episode, prior=prior)
        print(json.dumps(obj, ensure_ascii=False, indent=2))
        return 0
    path = n2d_intent.write_shot_intent(root, ns.episode)
    obj = n2d_intent.load_shot_intent(root, ns.episode) or {}
    n_shots = len(obj.get("shots") or [])
    n_evo = len(obj.get("allowed_evolution") or [])
    print(f"✅ 逐镜意图黑板已写：{path}（{n_shots} 镜意图 + {n_evo} 条 allowed_evolution 脚手架）")
    print("   派生字段以 storyboard.json 为权威；state_continuity 的 face/hair/costume 锁消费 allowed_evolution 的作者声明；"
          "把条目 field 标成 costume/face/hair/prop、填 from_shot/to_shot、置 source=\"author\" 即生效。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
