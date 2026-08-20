#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读 创作区/拍广告/<项目>/_进度.md 的「阶段进度」表，报告当前前沿 + 下一步该跑哪个 ad-* skill。

只读，不改文件。解析很宽容：只看「阶段进度」段里 `| 阶段 | 状态 | ...` 行的前两列，
按 ad-craft 阶段表把中文阶段标签映射回 stage key，找第一个未 ✅ 的阶段作为前沿。
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import contract  # noqa: E402

# 阶段表解析统一走本线 ad/_lib/progress_md.py（vendored，本线自包含）。
_COMMON_DIR = os.path.abspath(os.path.join(_HERE, "..", "..", "_lib"))
if _COMMON_DIR not in sys.path:
    sys.path.insert(0, _COMMON_DIR)
import progress_md  # noqa: E402

DONE = "✅"


def acceptance_note(root, key):
    """✅ 阶段行 ↔ 生产数据/stage_acceptance/<stage>.json 对账（只读提示，不改状态）。

    手改 _进度.md 可以绕过 progress_set 的护栏；这里把「✅ 无验收凭证 / 凭证仍有 block」
    在只读视图里说出来，真正的硬拦在 ad-review M0。
    """
    if not key:
        return ""
    path = os.path.join(root, "生产数据", "stage_acceptance", f"{key}.json")
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        block = int((payload.get("summary") or {}).get("block") or 0)
    except (OSError, json.JSONDecodeError, TypeError, ValueError, AttributeError):
        return "  ⚠️ ✅ 无验收凭证（缺 stage_acceptance 落档）"
    if block:
        return f"  ⚠️ ✅ 但验收凭证仍有 block={block}"
    return ""


def parse_stage_rows(text):
    """从 _进度.md 抽「阶段进度」段的 (label, status) 列表（2 列表）。"""
    rows = progress_md.parse_stage_rows(
        text, section_keywords=("阶段进度",), min_cols=2, status_col=1,
    )
    return [(r["label"], r["status"]) for r in rows]


def brief_hint(root):
    """读 需求/brief.json 跑 contract.brief_check，缺项给一行提示（只读不改）。"""
    path = os.path.join(root, "需求", "brief.json")
    if not os.path.isfile(path):
        return
    try:
        with open(path, encoding="utf-8") as f:
            check = contract.brief_check(json.load(f))
    except (OSError, json.JSONDecodeError):
        print("[warn] 需求/brief.json 读取失败，请检查 JSON 格式")
        return
    if check["missing_required"]:
        print(f"[brief] 缺必填项：{'、'.join(check['missing_required'])}"
              " —— ad-concept 第0步访谈补齐后才开工创意（别让用户填 JSON）")
    elif check["missing_deferred"]:
        print(f"[brief] 合规项待补：{'、'.join(check['missing_deferred'])}"
              " —— 不阻塞创意/脚本，但进出图/出视频/合成等花钱 gate 前必须补齐")


def main():
    ap = argparse.ArgumentParser(description="拍广告进度路由（只读）")
    ap.add_argument("project_root")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    prog = os.path.join(root, "_进度.md")
    if not os.path.isfile(prog):
        print(f"[err] 没有 _进度.md：{root}\n建议先 skills/ad/scripts/init_project.py 立项。", file=sys.stderr)
        sys.exit(2)

    with open(prog, encoding="utf-8") as f:
        rows = parse_stage_rows(f.read())

    stage_by_label = {s["label"]: s for s in contract.stage_table()}
    frontier = None
    print(f"# {os.path.basename(root)} — 拍广告进度\n")
    for label, status in rows:
        meta = stage_by_label.get(label)
        owner = meta["owner"] if meta else "?"
        note = acceptance_note(root, meta["key"]) if meta and DONE in status else ""
        print(f"- {status} {label}  ·  {owner}{note}")
        if frontier is None and DONE not in status:
            frontier = (label, meta)

    print()
    brief_hint(root)
    if frontier is None:
        print("[done] 生产阶段已完成 ✅ —— 下一步：分别闭合 AI 标识与商业披露收据、campaign_readiness + compliance_manifest 发布证据 → ad-review M0；投放后用 ad-feedback 回灌。")
        return
    label, meta = frontier
    owner = meta["owner"] if meta else "?"
    key = meta["key"] if meta else "?"
    gate = " ⚠️ 高风险（花钱/不可逆）阶段，正式生产前确认" if key in contract.GATE_STAGES else ""
    print(f"[前沿] 下一步：**{label}** → 跑 `{owner}`{gate}")


if __name__ == "__main__":
    main()
