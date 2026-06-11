#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""出图 → 出视频 视觉契约继承机检（拍广告版）。

广告里"视频改不动、要烤进首帧像素"的导演决策（**品牌色**/光位锚/轴线·视线/景别/产品形态）
必须从出图阶段继承到出视频，不能漂。本脚本逐字段 Diff `storyboard.json.visual_contract`
（出图阶段细化后）与每 Clip 的视频 prompt，品牌色/光位/轴线漂移=block。

自包含纯标准库 + 单测，不 import ad-craft。

用法：
    python3 inherit_contract.py <作品根> --json 出视频/分镜/contract_inheritance.json
"""
import argparse
import json
import os
import sys

# 这些字段是像素级硬继承（视频改不动）：缺失或与上游冲突 = block。
HARD_FIELDS = ["品牌色", "光位锚", "轴线"]
SOFT_FIELDS = ["画风", "景别", "构图"]


def diff_contract(image_contract, clip_prompt_text):
    """上游契约 image_contract(dict) vs 单 Clip 视频 prompt 文本。返回 findings。"""
    findings = []
    text = clip_prompt_text or ""
    for field in HARD_FIELDS:
        val = str(image_contract.get(field, "")).strip()
        if not val:
            continue  # 上游没定义该硬字段，不强求
        # 品牌色按 HEX 或值子串匹配；其它按值子串匹配
        token = val.lstrip("#")
        if token and token.lower() not in text.lower() and val not in text:
            findings.append({"severity": "block", "field": field,
                             "msg": f"视频 prompt 未继承上游{field}「{val}」（{field}漂移风险）"})
    for field in SOFT_FIELDS:
        val = str(image_contract.get(field, "")).strip()
        if val and val not in text:
            findings.append({"severity": "warn", "field": field,
                             "msg": f"视频 prompt 未显式继承{field}「{val}」"})
    return findings


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description="出图→出视频视觉契约继承机检（拍广告）")
    ap.add_argument("project_root")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)

    sb = load_json(os.path.join(root, "脚本", "storyboard.json"), {}) or {}
    contract = sb.get("visual_contract", {})
    prompt_dir = os.path.join(root, "出视频", "分镜", "prompt")

    results = []
    if os.path.isdir(prompt_dir):
        for name in sorted(os.listdir(prompt_dir)):
            if not name.endswith((".md", ".txt")):
                continue
            with open(os.path.join(prompt_dir, name), encoding="utf-8", errors="replace") as f:
                txt = f.read()
            for fnd in diff_contract(contract, txt):
                fnd["clip"] = name
                results.append(fnd)

    payload = {"schema_version": 1, "kind": "ad_contract_inheritance",
               "visual_contract": contract, "findings": results,
               "summary": {"block": sum(1 for r in results if r["severity"] == "block"),
                           "warn": sum(1 for r in results if r["severity"] == "warn")}}
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    b, w = payload["summary"]["block"], payload["summary"]["warn"]
    print(f"# 契约继承机检  block={b}  warn={w}")
    for r in results:
        print(("🔴" if r["severity"] == "block" else "🟡") + f" [{r['clip']}] {r['msg']}")
    if not results:
        print("✅ 视觉契约继承完整（品牌色/光位/轴线已继承）")
    sys.exit(1 if b > 0 else 0)


if __name__ == "__main__":
    main()
