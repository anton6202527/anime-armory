#!/usr/bin/env python3
"""Create evaluator-optimizer packets for n2d creative stages."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from n2d_action_registry import creative_loop_relpath, stage_action_spec  # noqa: E402


KIND = "n2d_creative_loop_packet"
VERSION = 1

RUBRICS = {
    "script_stage1": [
        "P-1 开发包五件套是否已 confirmed，并且卖点/受众/前3-5集追更弧/打样绿灯能支撑本集改编",
        "集边界是否完成冲突→爽点/反转→钩子闭环",
        "人物动机、前情承接、伏笔与系统/题材母题是否落账",
        "voiceover 是否适合短剧听感：短句、强动作、少解释腔",
    ],
    "script_stage2": [
        "P-2 导演排戏包是否已 confirmed，并且 beat/轴线调度/景别进程/转场/竖屏构图/剪辑节奏可直接指导 storyboard",
        "storyboard 是否把台词/动作/镜头时长拆到可执行 Clip",
        "高风险镜头是否套专项模板和 template_contract",
        "镜头是否有景别阶梯、轴线、状态转场和素材清单闭环",
    ],
    "image_prompt": [
        "每镜是否绑定 CHAR/LOC/PROP/VFX 资产 ID 和参考图",
        "多人/表情/坐骑/载具/奇观是否使用保真实现拆法",
        "图中文字、系统面板、测灵等级是否走 overlay 而非烤字",
    ],
    "video_prompt": [
        "是否继承 storyboard.template_contract 的专属字段",
        "模型路由、首中尾帧、motion control/degrade plan 是否一致",
        "身份/资产/屏幕方向/接缝是否有明确锁定句和负向约束",
    ],
}


def build_packet(root: str, ep: str, stage_key: str) -> Dict[str, Any]:
    action = stage_action_spec(stage_key)
    rubrics = RUBRICS.get(stage_key, ["按本阶段 action_contract 和 gate findings 做一致性、可执行性、成本风险评估"])
    return {
        "kind": KIND,
        "version": VERSION,
        "root": root,
        "episode": ep,
        "stage_key": stage_key,
        "action_contract": action,
        "loop": [
            {
                "step": "generate",
                "owner": action.get("specialist"),
                "instruction": "使用 context_pack 生成本阶段候选产物；不得越过花钱/合规/进度回写边界。",
            },
            {
                "step": "evaluate",
                "owner": action.get("specialist"),
                "rubric": rubrics,
                "output": "列 block/warn/info；block 必须给 return_to_stage 和最小修复范围。",
            },
            {
                "step": "optimize",
                "owner": action.get("specialist"),
                "instruction": "只修本阶段产物和直接依赖，不重写无关集/无关资产；保留可追溯 diff 摘要。",
            },
            {
                "step": "finalize",
                "owner": "n2d-supervisor",
                "instruction": "通过 gate 后再交给用户确认；进度回写仍走对应 stage skill/contract。",
            },
        ],
        "max_iterations": 2,
        "stop_conditions": [
            "gate/prework block",
            "requires human approval",
            "paid_or_irreversible action",
            "no material improvement after 2 iterations",
        ],
    }


def render_markdown(packet: Dict[str, Any]) -> str:
    lines = [
        "# n2d Creative Loop",
        "",
        f"- 集：{packet.get('episode')}",
        f"- 阶段：{packet.get('stage_key')}",
        f"- specialist：{(packet.get('action_contract') or {}).get('specialist')}",
        f"- max iterations：{packet.get('max_iterations')}",
        "",
    ]
    for item in packet.get("loop") or []:
        lines.append(f"## {item.get('step')}")
        if item.get("instruction"):
            lines.append(str(item["instruction"]))
        if item.get("rubric"):
            lines.extend(f"- {r}" for r in item["rubric"])
        lines.append("")
    return "\n".join(lines)


def write_packet(packet: Dict[str, Any]) -> Dict[str, str]:
    root = Path(str(packet["root"]))
    rel_json = creative_loop_relpath(str(packet["episode"]), str(packet["stage_key"]))
    path_json = root / rel_json
    path_md = root / "生产数据" / "views" / "creative_loops" / path_json.with_suffix(".md").name
    path_json.parent.mkdir(parents=True, exist_ok=True)
    path_md.parent.mkdir(parents=True, exist_ok=True)
    path_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path_md.write_text(render_markdown(packet), encoding="utf-8")
    return {
        "json": str(path_json),
        "markdown": str(path_md),
        "rel_json": rel_json,
        "rel_markdown": path_md.relative_to(root).as_posix(),
        "markdown_role": "derived_view",
    }


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="build an n2d creative evaluator-optimizer packet")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("stage_key")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    packet = build_packet(ns.root, ns.episode, ns.stage_key)
    if ns.write:
        packet["outputs"] = write_packet(packet)
    if ns.json:
        print(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_markdown(packet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
