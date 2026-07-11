#!/usr/bin/env python3
"""一致性不变量 Charter —— enforcement(强制力)维度的单一持久意图源。

背景（2026-06-27 审计）：为高质量出图/出视频建的一致性硬闸，会在后续"优化"里被
**悄悄降级**——改成 profile-only / opt-in / advisory / 孤儿——而**没有任何测试因此变红**，
diff 看着人畜无害（实例：c9d37df5 把 check_long_running_weak_backend 从无条件 BLOCK 改成
production-only，提交信息只说"措辞优化"）。根因：这些不变量以分散代码分支存在，没有任何
"它必须保持硬闸"的可执行记录。

本 charter 就是那份可执行记录：每个 load-bearing 闸一行，声明它**必须保持的强制力**。配套
`test_consistency_charter.py` introspect gate.py 源码，断言每个 locked 闸在默认 profile 下仍
无条件 BLOCK（severity 没被偷偷塞进 `if profile==production` 后面）。**想降级一个 locked 闸，
必须先改这里的一行**——一个可见、被 review、带日期的动作。这就把"静默降级"变成"显式审计决定"。

字段：
  required_severity   该闸缺料时必须达到的严重度（当前都是 "block"）。
  may_be_profile_gated 允不允许"仅 production 才 BLOCK，demo 降 WARN"。False=守护测试强制其源码
                       不得调用 consistency_release_profile / *_severity 决定 severity。
  may_be_opt_in       允不允许"默认关、要显式 env/flag 才生效"。
  review_status        stable / disputed_downgrade（被未披露降级·待裁决）/ opt_in_default_off /
                       mixed（结构检查硬·子检查 profile 门控）。
  rationale / decided  人话理由 + 决定日期（裁决留痕）。

新增 load-bearing 闸时**必须**在此登记 enforcement，否则守护测试会因"未声明"而提示——这正是
我们要的摩擦：强制力是一等公民，不能默认漂移。本 charter 是增量的，v1 先收最核心的一批。
"""

from __future__ import annotations

import glob
import os
import re
from typing import Any, Dict, List, Mapping

CHARTER_KIND = "n2d_consistency_charter"
CHARTER_VERSION = 1

# gate_function 名 → enforcement 不变量。键必须是 gate.py 里真实的顶层 def 名。
CHARTER: Dict[str, Dict[str, Any]] = {
    # ── 锁定·无条件 BLOCK（守护测试强制其源码不得 profile 门控 severity）──────────
    "check_input_frame_qc": {
        "dim": "出图落档QC", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "崩脸/接缝断/降级精度近景/非法CHAR 缺即挡，进 video 前唯一像素级落档闸，不分 profile",
        "decided": "2026-06-27",
    },
    "check_expression_span_frame_contract": {
        "dim": "跨情绪近景首尾双帧", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "expression_span=大 的近景缺尾帧=BLOCK，治大表情跳变",
        "decided": "2026-06-27",
    },
    "check_core_expression_anchor_coverage": {
        "dim": "核心表情锚覆盖", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "carries_identity 花钱前核心表情锚必须覆盖，治面瘫/表情漂",
        "decided": "2026-06-27",
    },
    "check_contract_inheritance": {
        "dim": "视觉契约继承", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "出图→出视频 光位锚/轴线/角色状态演进漂移=BLOCK（n2d_contract_diff.BLOCK_ON_DRIFT）",
        "decided": "2026-06-27",
    },
    "check_identity_handoff_inheritance": {
        "dim": "逐镜身份交接", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "命名角色镜未锁 CHAR/face_lock 即 BLOCK，治跨镜换脸",
        "decided": "2026-06-27",
    },
    "check_storyboard_style_contract": {
        "dim": "风格一致性", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "4 个真 gate detector 之一（能让 gate 退非0），global_style 契约破坏即挡",
        "decided": "2026-06-27",
    },
    "check_semantic_lineage": {
        "dim": "语义谱系一致性", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "4 个真 gate detector 之一，语义谱系 Diff 破坏即挡",
        "decided": "2026-06-27",
    },
    "check_state_continuity": {
        "dim": "状态百科一致性", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "4 个真 gate detector 之一，动态状态哨兵破坏即挡",
        "decided": "2026-06-27",
    },
    "check_multimodal_continuity": {
        "dim": "多模态一致性", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "4 个真 gate detector 之一，视觉语义/道具 embedding 离群即挡",
        "decided": "2026-06-27",
    },
    "check_progress_receipt_reconcile": {
        "dim": "进度凭据对账", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "H3 交付侧从凭据重新推导真相：受闸列 ✅ 无 fresh+green 凭据即 BLOCK，"
                     "抓绕过 progress.do_set 的手写/带外 ✅（凭据耦合的第二/三防线·不可降级）",
        "decided": "2026-06-28",
    },

    # ── 已恢复硬化（2026-06-27 用户裁决"不准降级·demo 不降标准·写成铁律"）──────────────
    # 这三个此前被悄悄降级/默认关，现已在 gate.py 恢复无条件 BLOCK，并 locked·守护测试强制不得再降。
    "check_long_running_weak_backend": {
        "dim": "生图AI一致性", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "跨集脸漂总闸。c9d37df5 曾把它降成 production-only WARN（提交信息只说'措辞优化'）；"
                     "2026-06-27 用户裁决恢复无条件 BLOCK，demo 与 production 同标准。",
        "decided": "2026-06-27",
    },
    "check_reference_plan_applied": {
        "dim": "参考规划落实", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "逐镜参考规划未落实即挡。8f2e4c3f/c9d37df5 曾降成 production-only；2026-06-27 恢复"
                     "无条件 BLOCK（核心长线角色缺 plan=BLOCK·普通角色镜=WARN 是内容档非 profile 档）。",
        "decided": "2026-06-27",
    },
    "check_core_anchor_pinning": {
        "dim": "锚点钉死", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "治脸漂根因：本集引用到的核心长线角色一个 form 都没登记 anchor_sha=BLOCK，必须 "
                     "image_qc --pin-anchor 钉死后再付费出图。2026-06-27 用户裁决从 WARN 升 BLOCK·默认开。",
        "decided": "2026-06-27",
    },
    "check_anchor_fingerprints": {
        "dim": "脸锚sha钉死", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": True, "review_status": "stable",
        "rationale": "已登记 anchor_sha 的 form：磁盘 front 定妆图 sha 漂移/丢失=无条件 BLOCK（跨集换脸根因）。"
                     "未登记的非核心 form 仍跳过，但核心长线角色的'该钉没钉'由 check_core_anchor_pinning 强制。",
        "decided": "2026-06-27",
    },
    "check_identity_registry": {
        "dim": "身份注册表", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "结构校验(缺/kind错/空/重复)+ 核心角色 performance_signature + 标志配饰 signature_equipment "
                     "全部无条件 BLOCK（2026-06-27 用户裁决：performance_signature/signature_equipment 从 production-only "
                     "拉平到 demo·B11）。2026-07-10 用户裁决把角色资产生产深度改为 tier-aware：core_full 保留完整视角硬闸，"
                     "recurring_standard/named_minimal 只对本档与本镜实际需要的 ready 参考硬闸；这不是按 demo/profile 降级，"
                     "而是显式内容档位，所有档位仍无条件 BLOCK 缺失的本档必需项。",
        "decided": "2026-07-10",
    },

    # ── 第二批拉平（2026-06-27 用户裁决"默认全 False·demo 也挡·C4 豁免也堵死"）──────────────
    # charter 落地后增量扫描发现的、仍被 profile 门控且漏网的一致性闸，全部恢复无条件 BLOCK。
    "check_asset_reference_registry": {
        "dim": "资产引用注册层", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "场景/道具/武器/服饰共享资产：武器型道具 weapon_profile + 核心场景空间发布字段 demo 也必需"
                     "（识 identity_registry 的姊妹闸，正是'武器/服饰共享图'那一半，曾 production-only）。",
        "decided": "2026-06-27",
    },
    "_check_fidelity_gate_active": {
        "dim": "fidelity-gate", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": True, "review_status": "stable",
        "rationale": "compose/review 终验像素 VLM 脸验证 demo 也 BLOCK；缺 VLM 后端不再 demo 静默 WARN 免单，"
                     "唯一出口显式留痕 N2D_ALLOW_DEGRADED_QC=1（C4 豁免堵死=缺依赖必须显式自负其责）。",
        "decided": "2026-06-27",
    },
    "check_consistency_audit_gate": {
        "dim": "一致性总审", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": True, "review_status": "stable",
        "rationale": "降级精度(缺 insightface=脸/像素没真验)四个阶段都不放行(曾 demo image/video 只 WARN)；"
                     "子进程一律按 production 严格度跑。逃生口同 fidelity-gate 的显式 N2D_ALLOW_DEGRADED_QC。",
        "decided": "2026-06-27",
    },
    "_strict_advisory_should_block": {
        "dim": "strict-advisory升级", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "strict-advisory 维度升 BLOCK 的实质条件(重复≥2/关键场/交付边界/对白近景口型/视频证据缺失)"
                     "demo 也适用，去掉 profile==production 免单。真·脆弱启发式仍由 add() 的 B10 守卫降回 WARN。",
        "decided": "2026-06-27",
    },
    "check_action_beat_budget": {
        "dim": "动作节拍预算", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "一镜塞完整攻防回合(跨≥3 互斥节拍类别)demo 也 BLOCK——模型物理易乱、命中帧读不出。",
        "decided": "2026-06-27",
    },
    "check_generation_recipe_evidence": {
        "dim": "生成配方留痕", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "每张终图/终视频的发布级生成配方证据 demo 也 BLOCK(可复算/可追溯)。",
        "decided": "2026-06-27",
    },
    "_styleid_release_gate_required": {
        "dim": "StyleID发布闸", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "风格化项目脸一致性发布闸 demo 也要求(调用方已 early-return 非风格化项目)。",
        "decided": "2026-06-27",
    },
    "native_voice_identity_required": {
        "dim": "原生音画身份", "required_severity": "block",
        "may_be_profile_gated": False, "may_be_opt_in": False, "review_status": "stable",
        "rationale": "原生音画项目的原生音画身份段 demo 也强制(曾 review/付费/production 才要)。",
        "decided": "2026-06-27",
    },

    # ── production 强一致性默认硬闸（2026-06-29 用户裁决）──────────────────────
    # 这些闸把此前"建议/默认 WARN"升级为 production BLOCK；demo/rough 仍可快速打样，但不能伪装成正式片。
    "check_placeholder_policy": {
        "dim": "production配音占位", "required_severity": "block",
        "may_be_profile_gated": True, "may_be_opt_in": False, "review_status": "production_consistency_default",
        "rationale": "production 正式片不得使用占位声音；混合模式可用无 WAV 时间基准推进，但交付前必须补齐逐镜 final voice、原生音画或后期口型证据。",
        "decided": "2026-06-29",
    },
    "check_image_backend_baseline": {
        "dim": "生图后端基线", "required_severity": "block",
        "may_be_profile_gated": True, "may_be_opt_in": False, "review_status": "production_consistency_default",
        "rationale": "每部剧锁一个生图后端基线；production 缺 baseline 或换后端未做重制计划即 BLOCK。",
        "decided": "2026-06-29",
    },
    "check_keyshot_candidate_plan": {
        "dim": "关键镜best-of-N", "required_severity": "block",
        "may_be_profile_gated": True, "may_be_opt_in": False, "review_status": "production_consistency_default",
        "rationale": "production 关键镜默认 K>=3 并要求 candidate_select 选优闭环；demo 可先 WARN。",
        "decided": "2026-06-29",
    },
    "check_production_core_identity_lock": {
        "dim": "核心角色身份锁", "required_severity": "block",
        "may_be_profile_gated": True, "may_be_opt_in": False, "review_status": "production_consistency_default",
        "rationale": "核心长线角色 production 必须 reference_group + 表情库 + native subject/face_embedding/LoRA 三选一。",
        "decided": "2026-06-29",
    },
    "check_video_prompt_frames": {
        "dim": "视频帧提交", "required_severity": "block",
        "may_be_profile_gated": True, "may_be_opt_in": False, "review_status": "production_consistency_default",
        "rationale": "production 视频 prompt 丢首尾帧/中段锚帧引用即 BLOCK；demo 保留 WARN 便于 rough preview。",
        "decided": "2026-06-29",
    },
    "check_route_frame_capability": {
        "dim": "视频后端帧能力", "required_severity": "block",
        "may_be_profile_gated": True, "may_be_opt_in": False, "review_status": "production_consistency_default",
        "rationale": "production 优先使用支持 first-last / multiframe / ingredients 的后端；帧消费能力不匹配不再普通放行。",
        "decided": "2026-06-29",
    },
    "check_storyboard_contract": {
        "dim": "动作镜中段锚帧", "required_severity": "block",
        "may_be_profile_gated": True, "may_be_opt_in": False, "review_status": "production_consistency_default",
        "rationale": "production 高运动镜缺中段锚帧/锚点即 BLOCK；普通 first-frame-only demo 仍按成本 WARN。",
        "decided": "2026-06-29",
    },
    "_check_storyboard_adjacent_clip_distinctness": {
        "dim": "Clip 去重", "required_severity": "block",
        "may_be_profile_gated": True, "may_be_opt_in": False, "review_status": "production_consistency_default",
        "rationale": "相邻 Clip 高相似且未写 intentional_repeat/拆段接力理由时，production 视频前必须 BLOCK；"
                     "demo 可先 WARN 便于快速预览，但这是一条显式登记的 profile 分级，不能静默漂移。",
        "decided": "2026-07-07",
    },

    # ── 显式登记·profile 门控保留（留存/叙事议题·非出图出视频一致性范围）──────────────────
    # 完整性守护要求"任何 profile 门控 BLOCK 都必须登记裁决"；这 3 个是节奏/留存闸，用户明确划在
    # 一致性范围外，故 may_be_profile_gated=True 是**显式留痕的决定**而非静默降级。要拉平另立议题。
    "check_series_retention_gate": {
        "dim": "系列留存", "required_severity": "block",
        "may_be_profile_gated": True, "may_be_opt_in": False, "review_status": "out_of_scope_retention",
        "rationale": "系列冷开场链/pilot 弧留存闸，节奏/留存议题非出图出视频一致性；profile 门控保留待单独裁决。",
        "decided": "2026-06-27",
    },
    "check_episode_narrative_floor": {
        "dim": "系列留存", "required_severity": "block",
        "may_be_profile_gated": True, "may_be_opt_in": False, "review_status": "out_of_scope_retention",
        "rationale": "逐集首屏钩子/留存承诺账本，留存议题非一致性；profile 门控保留待单独裁决。",
        "decided": "2026-06-27",
    },
    "check_pilot_arc_contract_gate": {
        "dim": "系列留存", "required_severity": "block",
        "may_be_profile_gated": True, "may_be_opt_in": False, "review_status": "out_of_scope_retention",
        "rationale": "pilot 弧契约留存闸，留存议题非一致性；profile 门控保留待单独裁决。",
        "decided": "2026-06-27",
    },
}

# ── 强制力决策日志（ENFORCEMENT_DECISIONS）─────────────────────────────────────
# CHARTER 收"无条件 BLOCK 锁"；本表收**刻意的、非无条件 BLOCK** 的 severity 设计（能力门控/
# 分级等），让它们也成为带日期、可被守护测试盯住的一等记录——防止像 `44af5704`（"force three-frame
# contract for all backends"）那样**悄悄反转一条既定能力门控**却只留 commit message。守护测试
# `test_enforcement_decisions_well_formed` 会断言每条决策的 `guard_token` 仍出现在对应 gate 函数源码里：
# 谁要把分级设计改回"一刀切"，guard_token 一旦消失测试即红 → 逼出一次显式、被 review 的 charter 更新。
ENFORCEMENT_DECISIONS: List[Dict[str, Any]] = [
    {
        "id": "three_frame_graduated_severity",
        "gate_function": "check_storyboard_contract",
        "dim": "中段锚帧",
        "design": "risk_only_with_explicit_native_opt_in",
        "guard_token": "backend_supports_three_plus_frames",
        "rule": "普通镜不设至少三帧要求。只有 policy.midframe_default_mode=explicit_opt_in 且"
                "backend_supports_three_plus_frames=True 时强制普通 D0 中锚；production 高运动镜、"
                "E1 编辑切点及已声明 anchors 继续按执行合同硬检。首尾 split relay 不冒充原生三帧；"
                "use=qc/reference 不进入时间轴。",
        "supersedes": "2026-06-27 three_frame capability-gated default-image policy",
        "rationale": "多家主流视频 API 的稳定公约数是首帧或首尾帧，不存在跨厂商普通镜三帧最低标准。"
                     "帧数应由剪辑语法和连续动作风险决定；低风险镜无条件补中帧浪费出图，且旧 runner "
                     "会误消费 QC 图。风险/显式 opt-in 保留真正需要的控制力。",
        "decided": "2026-07-10",
    },
]

# 守护测试用：locked 闸源码里**调用**这些函数 = severity 被 profile 门控 = 违反 charter。
# 带 `(` 只匹配真实调用，不误伤注释/文档里提及函数名（如"不随 consistency_release_profile 降级"）。
PROFILE_GATING_TOKENS = (
    "consistency_release_profile(",
    "_production_profile_inferred(",
)
# 跟一层 helper：闸把 severity 委托给名字含这些片段的 helper（如 _long_running_subjectless_severity）。
_SEVERITY_HELPER_HINTS = ("severity", "_sev", "_subjectless")


def charter_entries() -> Dict[str, Dict[str, Any]]:
    return CHARTER


def locked_gates() -> List[str]:
    return [name for name, e in CHARTER.items() if not e.get("may_be_profile_gated")]


def disputed_entries() -> Dict[str, Dict[str, Any]]:
    return {n: e for n, e in CHARTER.items()
            if e.get("review_status") in ("disputed_downgrade", "opt_in_default_off")}


def gate_source_text(scripts_dir) -> str:
    """gate 闸源码全集 = `gate.py` + `gates/*.py`（按证据族拆分后，locked 闸可分散到 gates/ 子包）。

    charter 的源码核对（audit_source / find_unregistered_profile_gates / top_level_bodies）只认它拿到的
    `source` 字符串里有哪些顶层 def——所以一旦把某个 locked check_ 迁出 gate.py 到 gates/<family>.py，
    源码核对的**调用方**必须喂全集，否则会把迁出的 locked 闸误报成 missing_gate。本函数是那份"全集"的
    单一真值：gate.py 在前 + 所有 gates/*.py（跳过 __init__ / test_）按名排序拼接，跨文件顶层 def
    仍 0 缩进、能被 top_level_bodies 正确切分。gates/ 不存在时退化为只读 gate.py（行为不变）。"""
    scripts_dir = str(scripts_dir)
    parts: List[str] = []
    # gate.py + gate_core.py（共享基座·增量2 拆出的常量/findings/add/无状态助手，含若干 locked 非 check_ 闸
    # 如 _check_fidelity_gate_active）+ gates/*.py（按证据族迁出的 check_）。三者合起来才是完整闸逻辑。
    for fname in ("gate.py", "gate_core.py"):
        fpath = os.path.join(scripts_dir, fname)
        if os.path.isfile(fpath):
            with open(fpath, encoding="utf-8") as f:
                parts.append(f.read())
    for path in sorted(glob.glob(os.path.join(scripts_dir, "gates", "*.py"))):
        base = os.path.basename(path)
        if base == "__init__.py" or base.startswith("test_"):
            continue
        with open(path, encoding="utf-8") as f:
            parts.append(f.read())
    return "\n".join(parts)


def top_level_bodies(source: str) -> Dict[str, str]:
    """gate 闸源码全集 → {顶层 def 名: 函数体文本}。函数都在 0 缩进，按下一个顶层 def 切分。

    source 应由 gate_source_text() 产出（gate.py + gates/*.py 拼接），不要直接只喂单个 gate.py，
    否则按证据族拆分后迁出的 locked 闸会被漏看。"""
    bodies: Dict[str, str] = {}
    pattern = re.compile(r"^def\s+([A-Za-z_]\w*)\s*\(", re.M)
    marks = [(m.group(1), m.start()) for m in pattern.finditer(source)]
    for i, (name, start) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(source)
        bodies[name] = source[start:end]
    return bodies


def _gathered_body(name: str, bodies: Mapping[str, str]) -> str:
    """函数体 + 它调用的 severity helper 的体（跟一层，覆盖 _*_severity 间接 profile 门控）。"""
    body = bodies.get(name, "")
    if not body:
        return ""
    extra = []
    for helper, hbody in bodies.items():
        if helper == name:
            continue
        if any(hint in helper for hint in _SEVERITY_HELPER_HINTS) and (helper + "(") in body:
            extra.append(hbody)
    return body + "\n" + "\n".join(extra)


_PROFILE_SEVERITY_PATTERN = re.compile(
    r'== "production"|!= "production"|BLOCK if .*production|production and|and .*production'
)
# profile 机制本身/工具函数：调用或定义 profile 但不是"按 profile 决定一致性 BLOCK"，豁免登记。
_COMPLETENESS_EXEMPT = {
    "consistency_release_profile", "_production_profile_inferred", "_contains_profile_marker",
    "_profile_values", "_production_profile_values",
}


def find_unregistered_profile_gates(source: str, charter: Mapping[str, Dict[str, Any]] = CHARTER) -> List[str]:
    """完整性守护：扫 gate.py 里**按 profile 决定 BLOCK** 却没在 charter 登记的函数。

    返回未登记函数名列表（应为空）。这把"靠人记得 grep 找漏网降级闸"变成"机器强制每个
    profile 门控 BLOCK 都必须在 charter 有显式裁决"——以后新增 profile 门控不登记即测试红，
    根除"修了一个漏一个"。登记 may_be_profile_gated=False=拉平，=True=显式留痕的保留决定。
    """
    out: List[str] = []
    for name, body in top_level_bodies(source).items():
        if name in _COMPLETENESS_EXEMPT or name in charter:
            continue
        if "consistency_release_profile(" not in body and "_production_profile_inferred(" not in body:
            continue
        if "BLOCK" not in body or not _PROFILE_SEVERITY_PATTERN.search(body):
            continue
        out.append(name)
    return out


def audit_source(source: str, charter: Mapping[str, Dict[str, Any]] = CHARTER) -> List[Dict[str, str]]:
    """对照 charter 审 gate.py 源码。返回违规列表 [{gate, kind, problem}]。

    kind=missing_gate   charter 登记的闸在 gate.py 找不到（被改名/删除→静默失效）。
    kind=profile_gated  locked(may_be_profile_gated=False) 闸的源码却按 profile 决定 severity。
    """
    bodies = top_level_bodies(source)
    out: List[Dict[str, str]] = []
    for name, entry in charter.items():
        if name not in bodies:
            out.append({"gate": name, "kind": "missing_gate",
                        "problem": f"charter 登记的 gate_function `{name}` 在 gate.py 找不到（被改名/删除？）"})
            continue
        if entry.get("may_be_profile_gated"):
            continue  # 允许 profile 门控的不查源码
        gathered = _gathered_body(name, bodies)
        hit = next((t for t in PROFILE_GATING_TOKENS if t in gathered), None)
        if hit:
            out.append({"gate": name, "kind": "profile_gated",
                        "problem": f"`{name}` 在 charter 声明为无条件 BLOCK（may_be_profile_gated=False），"
                                   f"但源码出现 `{hit}` 按 profile 决定 severity——疑似被悄悄降级。"
                                   f"要么修回无条件 BLOCK，要么先在 charter 里把它改成 disputed 并留痕。"})
    return out
