#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多时长 cutdown 重剪规划：从主片 storyboard 选镜，剪成更短交付件（30s→15s→6s）。

广告 cutdown 不是机械截断，而是按镜头优先级保留"钩子 + 产品 + CTA"骨架，砍铺垫。
本脚本按每镜 `cutdown_priority`（或 section 默认权重）贪心选镜，凑到目标时长 ±容差，
出 cutdown 计划 JSON（哪些镜留、预计时长）。自包含纯标准库 + 单测。

用法：
    python3 cutdown.py <作品根> --target 15s --json 合成/cutdown/plan_15s.json
"""
import argparse
import json
import os
import sys

# section 默认保留优先级（数字越大越先保留）。CTA/产品/钩子是 cutdown 骨架。
SECTION_PRIORITY = {
    "CTA": 100, "品牌包装": 100, "endcard": 100,
    "产品": 90, "方案": 88, "hero": 90,
    "钩子": 85,
    "证据": 60, "记忆点": 60,
    "痛点": 40, "情境": 38,
}


def shot_priority(shot):
    if "cutdown_priority" in shot:
        return float(shot["cutdown_priority"])
    section = str(shot.get("section", ""))
    for key, pri in SECTION_PRIORITY.items():
        if key in section:
            return pri
    return 50.0


def parse_seconds(label):
    s = str(label).strip().lower().replace("s", "")
    if ":" in s:
        m, sec = s.split(":", 1)
        return int(m) * 60 + float(sec)
    return float(s)


def plan_cutdown(shots, target_seconds, tol=0.6):
    """贪心：按优先级降序累加镜头直到≈目标时长。返回 (kept, total, findings)。
    保序输出（按原 storyboard 顺序），但选择按优先级。"""
    indexed = list(enumerate(shots))
    # 必保镜（priority>=85：钩子/产品/CTA）先入，其余按优先级补到目标
    ranked = sorted(indexed, key=lambda x: (-shot_priority(x[1]), x[0]))
    chosen, total = set(), 0.0
    for i, sh in ranked:
        dur = float(sh.get("duration", sh.get("时长", 0)) or 0)
        if total + dur <= target_seconds + tol:
            chosen.add(i)
            total += dur
        if total >= target_seconds - tol:
            # 已够；但仍要确保必保镜在内
            pass
    # 强制纳入必保镜（即便超一点点也比丢钩子/CTA好），随后报溢出
    for i, sh in indexed:
        if shot_priority(sh) >= 85 and i not in chosen:
            chosen.add(i)
            total += float(sh.get("duration", sh.get("时长", 0)) or 0)

    kept = [shots[i] for i in sorted(chosen)]
    findings = []
    if total > target_seconds + tol:
        findings.append({"severity": "warn", "kind": "cutdown_overflow",
                         "msg": f"必保镜后 {total:.2f}s 超目标 {target_seconds:.0f}s，需再压镜或缩单镜时长"})
    if total < target_seconds - tol:
        findings.append({"severity": "warn", "kind": "cutdown_underflow",
                         "msg": f"只凑到 {total:.2f}s < 目标 {target_seconds:.0f}s，可加镜或放慢节奏"})
    return kept, round(total, 3), findings


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description="多时长 cutdown 重剪规划")
    ap.add_argument("project_root")
    ap.add_argument("--target", required=True, help="目标时长，如 15s / 6s")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    sb = load_json(os.path.join(root, "脚本", "storyboard.json"), {}) or {}
    shots = sb.get("shots") or sb.get("clips") or []
    target = parse_seconds(args.target)
    kept, total, findings = plan_cutdown(shots, target)

    payload = {"schema_version": 1, "kind": "ad_cutdown_plan", "target_seconds": target,
               "total_seconds": total,
               "kept_shots": [s.get("shot_id") or s.get("clip_id") for s in kept],
               "findings": findings}
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"# cutdown {args.target}  保留 {len(kept)} 镜  预计 {total:.2f}s")
    print("  保留：" + ", ".join(str(x) for x in payload["kept_shots"]))
    for fnd in findings:
        print("🟡 " + fnd["msg"])
    sys.exit(0)


if __name__ == "__main__":
    main()
