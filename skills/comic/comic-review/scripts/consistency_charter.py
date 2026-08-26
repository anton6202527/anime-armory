#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""漫画线一致性不变量 Charter —— 强制力（enforcement）维度的单一持久意图源。

背景：设计宪法 B11 要求 load-bearing 闸不得被后续"优化"静默降级（改 opt-in /
advisory / 设置门控而没有任何测试变红）。同仓成熟视频线已有等价 charter；
漫画线此前没有——这是保护空缺（2026-07-20 标准审计）。本文件是漫画线的
可执行登记表：每个承重闸一行，声明它必须保持的强制力。配套
`test_consistency_charter.py` introspect gate.py 源码：

- charter 键必须是 gate.py 真实的顶层 def；
- `may_be_setting_gated=False` 的闸，其源码不得用 read_setting 决定 severity；
- gate.py 中任何新的能产 block 的顶层函数必须在此登记（或列入豁免名单），
  否则守护测试红——强制力是一等公民，不能默认漂移。

**想降级一个 locked 闸，必须先改这里的一行**——可见、被 review、带日期。

本线自包含：不 import 任何别线实现（宪法 A1）。
"""
from __future__ import annotations

from typing import Any, Dict

CHARTER_KIND = "comic_consistency_charter"
CHARTER_VERSION = 1

# gate_function 名 → enforcement 不变量。键必须是 gate.py 里真实的顶层 def 名。
CHARTER: Dict[str, Dict[str, Any]] = {
    # ── 锁定·无条件 BLOCK（源码不得用设置门控 severity）─────────────────────
    "check_prompt_compiler": {
        "dim": "合同/提交prompt单向边界(B13)", "required_severity": "block",
        "may_be_setting_gated": False, "review_status": "stable",
        "rationale": "submit_prompt 必须出自登记的 compiler 且 SHA 一致；边界破了内部合同会泄进付费 prompt",
        "decided": "2026-07-20",
    },
    "check_panel_jobs_stale": {
        "dim": "出图包陈旧契约", "required_severity": "block",
        "may_be_setting_gated": False, "review_status": "stable",
        "rationale": "上游合同变更后旧 job 冒充现行契约=一致性根基失效，不分档位",
        "decided": "2026-07-20",
    },
    "check_panel_jobs_ready": {
        "dim": "成图状态/旧契约成图/postQC", "required_severity": "block",
        "may_be_setting_gated": False, "review_status": "stable",
        "rationale": "旧契约成图冒 ready、post_qc=block 进合成必须无条件拦",
        "decided": "2026-07-20",
    },
    "check_style_contract": {
        "dim": "风格锚存在性", "required_severity": "block",
        "may_be_setting_gated": False, "review_status": "stable",
        "rationale": "无风格锚批量出图=整话画风裸奔，出图前必须有锚",
        "decided": "2026-07-20",
    },
    "check_backend": {
        "dim": "生成配方混用", "required_severity": "block",
        "may_be_setting_gated": False, "review_status": "stable",
        "rationale": "同话混用模型/渠道整话质感断裂，generation_recipe_mixed 无条件拦",
        "decided": "2026-07-20",
    },
    "check_panel_visual_contract": {
        "dim": "格内视觉合同(场景锚/眼神/多人staging)", "required_severity": "block",
        "may_be_setting_gated": False, "review_status": "stable",
        "rationale": "无理由看镜头/多人缺 staging 是确定性合同缺失，出图前拦",
        "decided": "2026-07-20",
    },
    "check_identity_execution_contracts": {
        "dim": "逐主体DNA/形态/服装/表情/状态/变体与精确参考执行合同",
        "required_severity": "block",
        "may_be_setting_gated": False,
        "review_status": "stable",
        "rationale": "付费出图前必须把每个主体的当前身份状态、定位证据与精确参考SHA固化进 execution_input；缺项或陈旧不得继续",
        "decided": "2026-08-26",
    },
    "run_continuity_contract_audit": {
        "dim": "跨话状态链(exit→entry)", "required_severity": "block",
        "may_be_setting_gated": False, "review_status": "stable",
        "rationale": "上一话 exit 与本话 entry 不一致=硬穿帮，可计算必拦",
        "decided": "2026-07-20",
    },
    "run_lettering_geometry_qc": {
        "dim": "嵌字几何(槽位越界)", "required_severity": "block",
        "may_be_setting_gated": False, "review_status": "stable",
        "rationale": "lettering_out_of_canvas 渲染必然裁字，坐标事实无条件拦；其余几何仅 warn",
        "decided": "2026-07-20",
    },
    "run_lettering_contract_check": {
        "dim": "嵌字版本血统(脚本/翻译/人工改写)", "required_severity": "block",
        "may_be_setting_gated": False, "review_status": "stable",
        "rationale": "旧脚本文字、失效翻译或无 SHA 收据的静默改写进入成品是可复算的派生合同断裂，compose/review 必须无条件拦",
        "decided": "2026-08-20",
    },
    # ── 锁定·BLOCK 但允许被「角色一致性硬闸」设置门控 ───────────────────────
    "check_identity": {
        "dim": "身份报告/缺参考/重抽目标/换装缺口", "required_severity": "block",
        "may_be_setting_gated": True, "review_status": "stable",
        "rationale": "缺共享参考、rerun_targets 未清是无条件 block；outfit_gaps 按硬闸设置升降（故意）",
        "decided": "2026-07-20",
    },
    "check_reference_execution": {
        "dim": "参考执行保真(风格锚/主体锚真实进通道)", "required_severity": "block",
        "may_be_setting_gated": True, "review_status": "stable",
        "rationale": "声明锚被附件上限静默省略是漂移根因；硬闸开=block、关=warn（故意）",
        "decided": "2026-07-20",
    },
    "check_machine_audit_liveness": {
        "dim": "机检活性(CCIP/VLM空转显式化)", "required_severity": "block",
        "may_be_setting_gated": True, "review_status": "stable",
        "rationale": "硬闸开+CCIP 不可用+0 裁决=身份轴完全无机检，升 block；其余组合 warn（故意）",
        "decided": "2026-07-20",
    },
    "run_script_advisory_audits": {
        "dim": "编剧层机检(显式entity_schedule例外)", "required_severity": "block",
        "may_be_setting_gated": False, "review_status": "mixed",
        "rationale": "advisory 整体 must→warn 不阻断（故意）；唯显式 entity_schedule 违约按确定性契约 block",
        "decided": "2026-07-20",
    },
}

# gate.py 中允许产 block 但不需要单独登记的函数（基础设施/分发器/汇总器）。
ALLOW_UNREGISTERED = {
    "add",                    # findings 构造器（B10 降级守卫本体）
    "run_contract_command",   # 子脚本 --check 桥（严重度来自子脚本合同）
    "check_production_profile",  # 档位自洽合同
    "refresh_identity_report",   # 刷新失败按缺料 block（基础设施）
    "check_required",         # 必需产物存在性（artifact_presence）
    "check_source_semantics",  # source trace 合同（comic-script 合同桥）
    "check_format_geometry",  # 排版几何合同
    "check_manifest_profile",  # 平台交付 profile（publish-like 升 block 是 platform_profiles 合同）
    "merge_consistency_report",  # 汇总器（severity 来自 finding_confidence 分级）
    "run_reference_plan_advisory",  # advisory（同源校验 stale 例外走 check_panel_jobs_stale）
    "run_image", "run_compose", "run_review",  # stage 分发器
    "make_report", "write_outputs", "main",   # 基础设施
}
