#!/usr/bin/env python3
"""跨集视觉契约一致性检查（⑦·advisory）。

集内继承 Diff（inherit_contract.py，出图↔出视频要求逐字一致）解决"同集内誊抄漂移"；本脚本解决
另一类穿帮：**同一地点跨集光位/轴线翻**（第1集冷宫画左光、第4集冷宫右侧光 = 越轴/光跳）。

读 第N集 与其**前一可比集**的 `出图/第N集/prompt/00_总览.md` 视觉契约，输出：
  1. 逐字段 side-by-side + 相似度（信息，给人看两集差在哪，不产告警）；
  2. **同名场景方向反转**告警（只在 asset_registry 的 LOC 地点两集都出现、且光位左右/轴线走向反转时报）。

**advisory·warn-only**：写报告 + 打印，**不阻断**（启发式不当硬闸；地点门控压噪音）。
用法：python3 cross_episode_contract.py <作品根> <第N集>
产出：生产数据/cross_episode_contract_第N集.json + .md
纯 stdlib；方向/相似度核心在 skills/n2d/_lib/n2d_cross_episode.py（纯函数·有 pytest）。
"""
from __future__ import annotations

import json
import os
import sys
import time

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import production_dir  # noqa: E402
# 上集定位 / 地点门控 / 总览路径 的真值源在 _lib，CLI 与 n2d-review gate 共用同一份（防漂）。
from n2d_cross_episode import (  # noqa: E402
    cross_episode_diff,
    overview_rel as _overview_rel,
    prior_episode,
    scene_names,
    core_scene_names,
)

KIND = "n2d_cross_episode_contract"


def render_md(ep: str, prev_ep: str, report: dict) -> str:
    s = report.get("summary", {})
    lines = [
        f"# 跨集视觉契约一致性 · {ep}（vs 前集 {prev_ep or '无'}）",
        "",
        f"- 方向反转告警 {s.get('warnings', 0)}（光位 {s.get('light_inversions', 0)} · 轴线 {s.get('axis_inversions', 0)}）· 核心场景 BLOCK {s.get('blocks', 0)}",
        "- 说明：非核心场景 **advisory·warn-only**；**核心主场景（asset_registry 显式标 core）跨集光位/轴线反转升 BLOCK**（P2b·硬伤，须对齐前集或写明有意换机位）。",
        "",
    ]
    for n in report.get("notes", []):
        lines.append(f"- note: {n}")
    lines.extend(["", "## 同名场景方向反转（actionable）", ""])
    if not report.get("warnings"):
        lines.append("- ✅ 无（两集共现地点的光位左右/轴线走向一致，或无可门控地点）")
    for w in report.get("warnings", []):
        bi = "⛔" if w.get("level") == "block" else "⚠️"
        lines.append(f"- {bi}「{w['scene']}」{w['kind']}：{w['note']}")
    lines.extend(["", "## 逐字段 side-by-side（信息·相似度越低差异越大）", "",
                  "| 字段 | 相似度 | 前集 | 本集 |", "|---|---|---|---|"])
    for f in report.get("fields", []):
        pv = (f.get("prev_text") or "（缺）").replace("|", "/")[:60]
        cv = (f.get("cur_text") or "（缺）").replace("|", "/")[:60]
        lines.append(f"| {f['field']} | {f['similarity']} | {pv} | {cv} |")
    return "\n".join(lines) + "\n"


def run(root: str, ep: str) -> int:
    cur_rel = _overview_rel(ep)
    cur_path = os.path.join(root, cur_rel)
    if not os.path.isfile(cur_path):
        print(f"⛔ 缺 {cur_path} —— 本集出图总览未生成，先 n2d-image。", file=sys.stderr)
        return 2
    prev_ep = prior_episode(root, ep)
    out_dir = production_dir(root)
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, f"cross_episode_contract_{ep}.json")
    md_path = os.path.join(out_dir, f"cross_episode_contract_{ep}.md")
    if prev_ep is None:
        report = {"kind": KIND, "episode": ep, "prev_episode": "", "fields": [], "warnings": [],
                  "notes": ["无前一可比集（首集）——跨集对比跳过。"], "summary": {"warnings": 0, "light_inversions": 0, "axis_inversions": 0},
                  "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
        open(md_path, "w", encoding="utf-8").write(f"# 跨集视觉契约一致性 · {ep}\n\n- 首集，无前集可比。\n")
        print(f"ℹ️ {ep} 是首集，跨集对比跳过 → {json_path}")
        return 0
    scenes = scene_names(root)
    diff = cross_episode_diff(open(os.path.join(root, _overview_rel(prev_ep)), encoding="utf-8").read(),
                              open(cur_path, encoding="utf-8").read(), scenes, prev_ep=prev_ep, cur_ep=ep,
                              core_scenes=core_scene_names(root))
    report = {"kind": KIND, "episode": ep, "prev_episode": prev_ep,
              "scenes_checked": scenes, **diff,
              "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    open(md_path, "w", encoding="utf-8").write(render_md(ep, prev_ep, report))
    n = report["summary"]["warnings"]
    blocks = report["summary"].get("blocks", 0)
    icon = "⛔" if blocks else ("⚠️" if n else "✅")
    print(f"{icon} 跨集契约 {ep} vs {prev_ep}: 方向反转 {n}（核心场景 block {blocks}） → {json_path}")
    for w in report.get("warnings", []):
        bi = "⛔" if w.get("level") == "block" else "⚠️"
        print(f"  - {bi} [{w['kind']}] {w['scene']}: {w['note']}")
    # 核心主场景反转=硬伤 → 非零退出；非核心仍 advisory（启发式不当硬闸）。
    return 2 if blocks else 0


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2:
        print("用法：python3 cross_episode_contract.py <作品根> <第N集>", file=sys.stderr)
        return 2
    return run(args[0], args[1])


if __name__ == "__main__":
    raise SystemExit(main())
