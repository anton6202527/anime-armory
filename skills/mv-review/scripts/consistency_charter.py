#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MV 一致性不变量 Charter —— enforcement（强制力）维度的单一持久意图源。

背景（参照 n2d consistency_charter 的教训）：为一致性建的硬闸，最容易在后续"优化"里被
**悄悄降级**——err 挪成 warn、新增一个 `is_demo` 豁免分支、检查整段被删——而没有任何测试
因此变红，diff 看着人畜无害。mv 线 2026-07-16/17 两轮刚补了一批 load-bearing 闸
（脸崩 hard block、定妆 readiness、降级具名放行、版权闸、picture_lock hash 链…），
正是未来最可能被静默削弱的面。

本 charter 是那份可执行记录，对每个 gate 闸声明两件事：
  guard_tokens      该闸源码必须仍包含的关键片段（防检查被删/改名后静默失效）；
  max_is_demo_refs  该闸函数体内 `is_demo` 出现次数的**冻结基线**——mv 没有 profile 系统，
                    demo 豁免（`meta.get("is_demo")` 短路正式闸）就是 mv 的静默降级向量。
                    新增一个 demo 豁免分支 → 计数超基线 → 守护测试红 → 必须先来这里
                    显式改一行（可见、被 review、带日期）。

另有 HARD_QC_INVARIANTS：gate 之外的 QC 硬闸片段（image_qc 脸崩 HARD、禁用本地贴脸、
video_qc HDR/缺片 block、delivery_qc 响度 block），同样以"源码必须包含"守护。

配套 `test_consistency_charter.py` introspect 真实源码断言全部成立；
CLI：python3 consistency_charter.py（退出非 0 = 有违规，供自查/CI）。
新增 load-bearing 闸时**必须**在此登记（完整性扫描会揪出用了 is_demo 却未登记的 gate 函数）。
"""
from __future__ import annotations

import os
import re
from typing import Any

CHARTER_KIND = "mv_consistency_charter"
CHARTER_VERSION = 1

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))
GATE_PATH = os.path.join(SKILLS_DIR, "mv-craft", "scripts", "gate.py")

# gate.py 顶层函数名 → enforcement 不变量。键必须是 gate.py 里真实的顶层 def 名。
# max_is_demo_refs = 2026-07-17 落 charter 时的实测基线（想加 demo 豁免先改这里并留痕）。
CHARTER: dict[str, dict[str, Any]] = {
    "_rights_errors": {
        "dim": "版权闸", "guard_tokens": ["_UNRESOLVED_RIGHTS", "song_rights_status"],
        "max_is_demo_refs": 1,
        "rationale": "歌曲版权 unknown 时无条件拦付费阶段（song_rights_status 检查 demo 也适用；"
                     "rights_manifest 六断言仅正式项目要求是显式决定）。",
        "decided": "2026-07-17",
    },
    "_staleness_errors": {
        "dim": "输入新鲜度", "guard_tokens": ["inputs_sha256"], "max_is_demo_refs": 1,
        "rationale": "旧分镜不得消费新输入：clip_plan 全输入收据 hash 必须与当前一致。",
        "decided": "2026-07-17",
    },
    "_beatgrid_contract": {
        "dim": "音乐时序真值", "guard_tokens": ["source_audio_sha256", "downbeats_verified"],
        "max_is_demo_refs": 3,
        "rationale": "beatgrid 必须来自当前歌曲且正式项目需具名确认相位/段落；卡点是 MV 命门。",
        "decided": "2026-07-17",
    },
    "_timeline_contract_errors": {
        "dim": "时间线对账", "guard_tokens": ["source_clip_plan_sha256"], "max_is_demo_refs": 1,
        "rationale": "timeline 与 clip_plan 的 clip 集合/时长必须一致并 hash 绑定。",
        "decided": "2026-07-17",
    },
    "_otio_contract_errors": {
        "dim": "OTIO 编辑合同", "guard_tokens": ["otio_sha256"], "max_is_demo_refs": 1,
        "rationale": "正式项目 OTIO + receipt hash 链必须新鲜。",
        "decided": "2026-07-17",
    },
    "_pacing_receipt_errors": {
        "dim": "节奏预检收据", "guard_tokens": ["blocked"], "max_is_demo_refs": 1,
        "rationale": "正式付费生产前 pacing_prescore 必须存在、新鲜；显式阈值判 blocked 即拦。",
        "decided": "2026-07-17",
    },
    "_alignment_contract_errors": {
        "dim": "歌词时间轴", "guard_tokens": ["character_coverage_ratio"], "max_is_demo_refs": 1,
        "rationale": "口型/字幕前歌词强制对齐需完整行+90% 字符覆盖或具名逐行听审。",
        "decided": "2026-07-17",
    },
    "_semantic_prompt_errors": {
        "dim": "语义分镜收据", "guard_tokens": ["result_clip_plan_sha256"], "max_is_demo_refs": 1,
        "rationale": "正式出图前语义分镜必须覆盖全部 clip 并绑定当前 clip_plan。",
        "decided": "2026-07-17",
    },
    "_image_qc_errors_warnings": {
        "dim": "出图落档QC消费", "guard_tokens": ["hard_blocks", 'precision != "full"', "bound_report_sha256"],
        "max_is_demo_refs": 1,
        "rationale": "image_qc hard block=0、精度 full 或具名+hash 绑定放行才准进 mv-video；"
                     "旧式裸布尔 manual_review_accepted 不再放行（2026-07-16 第二轮裁决）。",
        "decided": "2026-07-17",
    },
    "_identity_readiness": {
        "dim": "主角定妆包readiness", "guard_tokens": ["len(existing) >= 3"], "max_is_demo_refs": 1,
        "rationale": "正式 video_jobs 前主角定妆包必须 ready≥3 张——定妆不全时脸检 floor 无法自标定"
                     "（2026-07-16 第二轮从 mv-review warn 升进付费闸）。",
        "decided": "2026-07-17",
    },
    "_demo_flag_warnings": {
        "dim": "demo自证护栏", "guard_tokens": ["formal_readiness"], "max_is_demo_refs": 4,
        "rationale": "is_demo=true 但有正式生产痕迹时提醒复核标记（本函数职责就是查 demo，基线高是正常）。",
        "decided": "2026-07-17",
    },
    "_shot_variety_warnings": {
        "dim": "视觉多样性advisory", "guard_tokens": ["shot_variety"], "max_is_demo_refs": 0,
        "rationale": "advisory 惯例样板：只进 warnings、永不 block、不分 demo。",
        "decided": "2026-07-17",
    },
    "_drift_risk_warnings": {
        "dim": "漂移风险advisory", "guard_tokens": ["drift_risk"], "max_is_demo_refs": 0,
        "rationale": "出图前漂移风险预测消费（2026-07-17 第三轮新增）；advisory、不分 demo。",
        "decided": "2026-07-17",
    },
    "_craft_audit_warnings": {
        "dim": "传统手法advisory", "guard_tokens": ["craft_audit"], "max_is_demo_refs": 0,
        "rationale": "传统 MV 手法机检消费（2026-07-17 第四轮新增：副歌升级/动静对比/hook 上脸/冷开场/"
                     "关键镜候选/bridge 换气）；advisory、不分 demo。",
        "decided": "2026-07-17",
    },
    "_pilot_matrix_warnings": {
        "dim": "打样矩阵advisory", "guard_tokens": ["PILOT_MIN_CLIPS"], "max_is_demo_refs": 1,
        "rationale": "正式大盘全量出图前提示先打样（2026-07-17 第三轮新增）；demo/小盘不打扰是显式决定。",
        "decided": "2026-07-17",
    },
    "_video_report_errors": {
        "dim": "视频报告消费", "guard_tokens": ["semantic_review", "selected_video_sha256"],
        "max_is_demo_refs": 1,
        "rationale": "compose 前 inherit_contract/video_qc 必须存在、新鲜、hard=0，正式项目语义签收绑定视频与接缝合同 hash。",
        "decided": "2026-07-17",
    },
    "_picture_lock_errors": {
        "dim": "picture lock", "guard_tokens": ["editorial_timeline_sha256"], "max_is_demo_refs": 1,
        "rationale": "正式项目付费出视频/合成前必须有具名、全输入 hash 绑定的 picture lock。",
        "decided": "2026-07-17",
    },
    "check": {
        "dim": "挑版对账", "guard_tokens": ["selected_take"], "max_is_demo_refs": 1,
        "rationale": "compose 期 timeline 已存在视频必须有 jobs_manifest 挑版记录（防绕过 --select 手动丢片）。",
        "decided": "2026-07-17",
    },
}

# gate 之外的 QC 硬闸：源码必须仍包含这些片段（相对 skills/ 的文件 → 片段列表）。
HARD_QC_INVARIANTS: list[dict[str, Any]] = [
    {"file": "mv-image/scripts/image_qc.py", "dim": "脸崩HARD",
     "tokens": ['HARD_CHECKS = ("face",)'],
     "rationale": "脸崩是唯一 HARD 视觉检查——HARD_CHECKS 不许被清空或移除 face。"},
    {"file": "mv-image/scripts/image_qc.py", "dim": "禁用本地贴脸",
     "tokens": ["prohibited_local_patch"],
     "rationale": "facefusion/inswapper/roop 等本地换脸产物无条件 hard block。"},
    {"file": "mv-video/scripts/video_qc.py", "dim": "HDR/缺片block",
     "tokens": ['"level": "block", "code": "hdr_input_requires_explicit_tonemap"',
                '"level": "block", "code": "selected_video_missing"'],
     "rationale": "HDR 未显式 tonemap、选中视频缺失必须 block。"},
    {"file": "mv-compose/delivery_qc.py", "dim": "交付响度block",
     "tokens": ['blocks.append("true_peak_above_0dbtp")', 'blocks.append("loudness_scan_unavailable")'],
     "rationale": "true peak>0dBTP、响度扫描不可用必须 block——扫不了≠过（fail-closed）。"},
]


def top_level_bodies(source: str) -> dict[str, str]:
    """源码 → {顶层 def 名: 函数体文本}（0 缩进函数，按下一个顶层 def 切分）。"""
    bodies: dict[str, str] = {}
    pattern = re.compile(r"^def\s+([A-Za-z_]\w*)\s*\(", re.M)
    marks = [(m.group(1), m.start()) for m in pattern.finditer(source)]
    for i, (name, start) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(source)
        bodies[name] = source[start:end]
    return bodies


def audit_gate_source(source: str, charter: dict[str, dict[str, Any]] | None = None) -> list[dict[str, str]]:
    """对照 charter 审 gate.py 源码。返回违规列表 [{gate, kind, problem}]。

    kind=missing_gate            charter 登记的闸在 gate.py 找不到（被改名/删除→静默失效）。
    kind=guard_token_missing     闸还在，但守护片段没了（检查被删/改写→静默失效）。
    kind=demo_gating_increased   函数体 is_demo 次数超冻结基线（新增 demo 豁免=静默降级）。
    """
    charter = charter if charter is not None else CHARTER
    bodies = top_level_bodies(source)
    out: list[dict[str, str]] = []
    for name, entry in charter.items():
        body = bodies.get(name)
        if body is None:
            out.append({"gate": name, "kind": "missing_gate",
                        "problem": f"charter 登记的 gate 函数 `{name}` 在 gate.py 找不到（被改名/删除？）——"
                                   "要么恢复，要么先改 charter 留痕。"})
            continue
        for token in entry.get("guard_tokens") or []:
            if token not in body:
                out.append({"gate": name, "kind": "guard_token_missing",
                            "problem": f"`{name}` 缺守护片段 `{token}`——该检查疑似被删/改写；"
                                       "恢复检查，或先在 charter 改这一行并写明裁决。"})
        baseline = int(entry.get("max_is_demo_refs") or 0)
        actual = body.count("is_demo")
        if actual > baseline:
            out.append({"gate": name, "kind": "demo_gating_increased",
                        "problem": f"`{name}` 的 is_demo 引用 {actual} 处，超过 charter 冻结基线 {baseline}——"
                                   "疑似新增 demo 豁免分支静默降级正式闸；要么去掉豁免，"
                                   "要么先在 charter 抬基线并写明裁决。"})
    return out


def find_unregistered_demo_gates(source: str, charter: dict[str, dict[str, Any]] | None = None) -> list[str]:
    """完整性守护：gate.py 里用了 is_demo（=有 demo 豁免力）却没在 charter 登记的顶层函数。

    以后新增带 demo 豁免的闸不登记即测试红，根除"修了一个漏一个"。"""
    charter = charter if charter is not None else CHARTER
    out = []
    for name, body in top_level_bodies(source).items():
        if name in charter:
            continue
        if "is_demo" in body:
            out.append(name)
    return out


def audit_hard_qc(skills_dir: str | None = None) -> list[dict[str, str]]:
    """QC 硬闸片段核对：文件缺失或片段消失都算违规。"""
    skills_dir = skills_dir or SKILLS_DIR
    out: list[dict[str, str]] = []
    for spec in HARD_QC_INVARIANTS:
        path = os.path.join(skills_dir, spec["file"])
        if not os.path.isfile(path):
            out.append({"gate": spec["file"], "kind": "missing_file",
                        "problem": f"charter 登记的 QC 文件不存在：{spec['file']}"})
            continue
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        for token in spec["tokens"]:
            if token not in source:
                out.append({"gate": spec["file"], "kind": "hard_qc_token_missing",
                            "problem": f"{spec['file']} 缺硬闸片段 `{token}`（{spec['dim']}）——"
                                       "疑似硬闸被静默降级/删除；恢复或先改 charter 留痕。"})
    return out


def audit_all() -> list[dict[str, str]]:
    with open(GATE_PATH, encoding="utf-8") as fh:
        gate_source = fh.read()
    violations = audit_gate_source(gate_source)
    violations += [{"gate": name, "kind": "unregistered_demo_gate",
                    "problem": f"gate 函数 `{name}` 用了 is_demo 但未在 charter 登记 enforcement——"
                               "新增 demo 豁免必须是显式、留痕的决定。"}
                   for name in find_unregistered_demo_gates(gate_source)]
    violations += audit_hard_qc()
    return violations


def main() -> int:
    violations = audit_all()
    if not violations:
        print(f"[ok] mv consistency charter：{len(CHARTER)} 个 gate 闸 + "
              f"{len(HARD_QC_INVARIANTS)} 组 QC 硬闸全部符合声明的强制力。")
        return 0
    for v in violations:
        print(f"[violation] {v['kind']} · {v['gate']}: {v['problem']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
