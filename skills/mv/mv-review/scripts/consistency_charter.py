#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MV 一致性不变量 Charter —— enforcement（强制力）维度的单一持久意图源。

背景（参照兄弟线 consistency_charter 的教训）：为一致性建的硬闸，最容易在后续"优化"里被
**悄悄降级**——err 挪成 warn、新增一个 `is_demo` 豁免分支、检查整段被删——而没有任何测试
因此变红，diff 看着人畜无害。mv 线 2026-08-20 复核并补齐了一批 load-bearing 闸
（脸崩 hard block、B14 双闸、定妆 readiness、歌词声学证据、版权闸、picture_lock hash 链…），
正是未来最可能被静默削弱的面。

本 charter 是那份可执行记录，对每个 gate 闸声明两件事：
  guard_tokens      该闸源码必须仍包含的关键片段（防检查被删/改名后静默失效）；
  max_is_demo_refs  该闸函数体内 `is_demo` 出现次数的**冻结基线**——mv 没有 profile 系统，
                    demo 豁免（`meta.get("is_demo")` 短路正式闸）就是 mv 的静默降级向量。
                    新增一个 demo 豁免分支 → 计数超基线 → 守护测试红 → 必须先来这里
                    显式改一行（可见、被 review、带日期）。

另有 HARD_QC_INVARIANTS：gate 之外的 QC 硬闸片段（image_qc 脸崩 HARD、禁用本地贴脸、
video_qc HDR/缺片 block、delivery_qc 响度 block），以 ``tokens`` 守护必须存在的实现，
并以 ``forbidden_tokens`` 守护已废弃、会削弱证据或可移植性的实现不得回流。

配套 `test_consistency_charter.py` introspect 真实源码断言全部成立；
CLI：python3 consistency_charter.py（退出非 0 = 有违规，供自查/CI）。
新增 load-bearing 闸时**必须**在此登记（完整性扫描会揪出用了 is_demo 却未登记的 gate 函数）。
"""
from __future__ import annotations

import os
import re
from typing import Any

CHARTER_KIND = "mv_consistency_charter"
CHARTER_VERSION = 5

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
        "dim": "歌词时间轴",
        "guard_tokens": ["character_coverage_ratio", "_alignment_stem_timing_errors",
                         "_alignment_acoustic_valid", "evidence_content_sha256"],
        "max_is_demo_refs": 1,
        "rationale": "文字覆盖率不得冒充声学置信度；正式接受需歌声专用校准证据或具名逐行听审，"
                     "并验证 stem→master offset/drift、当前绑定与证据内容 hash。",
        "decided": "2026-08-20",
    },
    "_alignment_acoustic_valid": {
        "dim": "歌声声学证据",
        "guard_tokens": ["singing_specific", "calibrated", "acceptance_eligible", "covered == set(range(lyric_lines))"],
        "max_is_demo_refs": 0,
        "rationale": "声学路线必须是歌声专用、已校准、明确可验收，并逐行覆盖当前歌词。",
        "decided": "2026-08-20",
    },
    "_alignment_stem_timing_errors": {
        "dim": "stem到master时基",
        "guard_tokens": ["stem_master_timing", "offset_seconds", "drift_seconds", "minimum_correlation"],
        "max_is_demo_refs": 0,
        "rationale": "非 master 对齐音频必须以当前文件绑定复核 offset/drift；自动路线保留三窗口与阈值。",
        "decided": "2026-08-20",
    },
    "_semantic_prompt_errors": {
        "dim": "语义分镜收据",
        "guard_tokens": ["result_clip_plan_sha256", '_strict_int(receipt.get("schema_version")) != 3',
                         'receipt.get("complete") is not True', "prompt_outputs_sha256"],
        "max_is_demo_refs": 1,
        "rationale": "付费/合成前只接受 complete schema v3，须覆盖全部 clip、绑定当前 clip_plan，"
                     "并逐 clip 重算 image/video prompt 输出 hash。",
        "decided": "2026-08-20",
    },
    "_image_qc_errors_warnings": {
        "dim": "出图落档QC消费",
        "guard_tokens": ["hard_blocks", 'precision != "full"', "assets_sha256",
                         "all_current_accepted", "generation_provenance"],
        "max_is_demo_refs": 1,
        "rationale": "B14 承重门只接受 full+ok machine QC、完整生成来源和动态复算后全资产 current+accepted；"
                     "degraded/manual review 永不替代机检。新鲜度只走 assets_sha256，不退回 mtime。",
        "decided": "2026-08-20",
    },
    "_identity_readiness": {
        "dim": "主角定妆包readiness", "guard_tokens": ["len(existing) >= 3"], "max_is_demo_refs": 1,
        "rationale": "正式 video_jobs 前主角定妆包必须 ready≥3 张——定妆不全时脸检 floor 无法自标定"
                     "（2026-07-16 第二轮从 mv-review warn 升进付费闸）。",
        "decided": "2026-07-17",
    },
    "_demo_flag_warnings": {
        "dim": "demo自证护栏", "guard_tokens": ["formal_readiness", "settings-first"], "max_is_demo_refs": 6,
        "rationale": "2026-08-20 改为 settings-first 后，本函数只比较 `_meta.is_demo` 兼容镜像并发 advisory；"
                     "6 次文本引用来自变量/说明/消息，不提供任何硬门豁免。",
        "decided": "2026-08-20",
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
    {"file": "mv-video/scripts/video_qc.py", "dim": "视频重度脸漂block",
     "tokens": ['"level": "block", "code": "video_face_identity_drift_severe"',
                "SEVERE_FACE_DRIFT_MARGIN", "bound_video_sha256"],
     "rationale": "视频帧脸 embedding 跌破重度带（自标定阈值-0.15）＝疑似换人，必须 block；"
                  "唯一出口是具名+绑定当前视频 sha 的 face_drift_waiver（2026-07-20 新增：出图侧 G1 是硬闸，"
                  "视频侧同人底线不得反而只 warn）。轻/中度漂移仍是 warn+人审，不受本条约束。"},
    {"file": "mv-image/scripts/image_qc.py", "dim": "正式身份锚点合同消费hard",
     "tokens": ["FORMAL_HARD_LINT_CODES", '"missing_anchor_identity"'],
     "rationale": "正式项目 prompt 缺身份锚点/禁止漂移块＝身份合同未被下游消费（B12 确定性交接缺口）→ hard；"
                  "demo 与参考/视觉块保持 advisory（2026-07-20 新增）。"},
    {"file": "mv-video/scripts/inherit_contract.py", "dim": "schema4真实提交收据block",
     "tokens": ['"code": "missing_actual_submit_receipt"',
                '"code": "submit_receipt_refs_mismatch"',
                '"code": "submitted_reference_changed"',
                'receipt.get("submitted_refs")', "video_capabilities.SHA256_RE.fullmatch(sha)"],
     "rationale": "只有 provider 实际 submit receipt 才能证明请求绑定；逐 role/path/SHA 的 submitted_refs "
                  "必须与编译 controls 完全相等且仍匹配当前文件。计划首帧或登记时顺手抄入的 SHA 不算证据"
                  "（2026-08-20 schema4 裁决）。"},
    {"file": "mv-video/scripts/video_jobs.py", "dim": "schema4提交边界fail-closed",
     "tokens": ["def validate_submit_receipt", '"receipt_request_controls_mismatch"',
                '"receipt_submitted_refs_do_not_match_compiled_controls"',
                '"manual_receipt_reviewer_missing"', '"provider_job_id"'],
     "rationale": "register 必须核验 job/model/channel/provider、完整 request_controls 与真实 refs；"
                  "manual 渠道必须具名证明，不得用未提交的计划参数补收据。"},
    {"file": "mv-video/scripts/inherit_contract.py", "dim": "controls与新鲜度审计block",
     "tokens": ['"code": "manifest_project_input_changed"',
                '"code": "manifest_compiler_or_capability_changed"',
                '"code": "manifest_compiled_controls_hash_mismatch"',
                '"code": "manifest_planned_controls_hash_mismatch"'],
     "rationale": "设置、compiler/capability、prompt、image QC、引用或 planned/compiled controls 改变后，"
                  "旧任务包不得继续作为当前提交合同。"},
    {"file": "_lib/video_capabilities.py", "dim": "能力图时效性硬门",
     "tokens": ["CAPABILITY_GRAPH_STALE_AFTER_DAYS = 90",
                "def capability_graph_freshness_errors", "capability_graph_reverification_required"],
     "rationale": "模型公开规格会变化；内置执行矩阵采集超过 90 天后必须先复核，不能只因旧 hash 自洽继续付费。"},
    {"file": "mv-video/scripts/video_jobs.py", "dim": "任务包新鲜度完整绑定",
     "tokens": ["def build_freshness_snapshot", '"settings_sha256"', '"compiler_sha256"',
                '"image_qc_sha256"', '"reference_inputs_sha256"',
                '"planned_request_controls_sha256"', '"compiled_request_controls_sha256"'],
     "rationale": "schema4 manifest 必须持久化设置/compiler/prompt/image QC/reference 与完整 controls hash，"
                  "使审计端能 fail-closed 判旧。"},
    {"file": "mv-video/scripts/video_jobs.py", "dim": "多镜头真实切点复核",
     "tokens": ["def validate_cut_map", '"cut_map_source_sha256_mismatch"',
                '"cut_map_reviewer_missing"', '"cut_map_review_method_not_evidentiary"',
                '"actual_boundaries_seconds"'],
     "rationale": "多镜头 sequence 拆分必须由具名、逐帧/时间码实看生成 cut map 并绑定源视频 SHA；"
                  "盲抄计划边界不得通过。"},
    {"file": "mv-video/scripts/inherit_contract.py", "dim": "多镜头收据与cut map审计block",
     "tokens": ['"code": "sequence_submit_receipt_invalid"',
                '"code": "sequence_cut_map_invalid"', '"mv_video_sequence_cut_map"'],
     "rationale": "sequence 已登记时，父提交收据和具名 cut map 任一缺失、篡改或换源都必须 block。"},
    {"file": "mv-video/scripts/video_jobs.py", "dim": "任务包根路径可移植",
     "tokens": ['"root_rel": "."'], "forbidden_tokens": ['"project_root": root'],
     "rationale": "新 jobs manifest 只记录作品内相对根；旧 manifest 的绝对 project_root 仍可由读取端忽略审计，"
                  "但不得继续写入新产物。"},
    {"file": "mv-video/scripts/inherit_contract.py", "dim": "继承报告根路径可移植",
     "tokens": ['"root_rel": "."'], "forbidden_tokens": ['"root": root'],
     "rationale": "继承审计报告可随作品目录搬迁；历史报告的 root 字段不参与证据判定，保持只读兼容。"},
    {"file": "mv-video/scripts/video_qc.py", "dim": "视频QC报告根路径可移植",
     "tokens": ['"root_rel": "."'], "forbidden_tokens": ['"root": root'],
     "rationale": "视频 QC 报告只写 root_rel，避免将本机绝对目录写进可交付证据。"},
    {"file": "mv-review/scripts/consistency_findings.py", "dim": "一致性汇总根路径可移植",
     "tokens": ['"root_rel": "."'], "forbidden_tokens": ['"project_root": root'],
     "rationale": "汇总报告随作品目录移动，不落工作站绝对路径。"},
    {"file": "mv-review/scripts/craft_audit.py", "dim": "传统手法报告根路径可移植",
     "tokens": ['"root_rel": "."'], "forbidden_tokens": ['"project_root": root'],
     "rationale": "审美辅助报告也属于可交付生产数据，不落工作站绝对路径。"},
    {"file": "mv-review/scripts/shot_variety_audit.py", "dim": "镜头多样性报告根路径可移植",
     "tokens": ['"root_rel": "."'], "forbidden_tokens": ['"project_root": root'],
     "rationale": "镜头审计报告只记录作品内相对根。"},
    {"file": "mv-plan/scripts/pilot_matrix.py", "dim": "打样矩阵根路径可移植",
     "tokens": ['"root_rel": "."'], "forbidden_tokens": ['"project_root": root'],
     "rationale": "打样计划不泄漏生成机器目录。"},
    {"file": "mv-score/scripts/score_pacing.py", "dim": "节奏与回流报告根路径可移植",
     "tokens": ['"root_rel": "."'], "forbidden_tokens": ['"project_root": root'],
     "rationale": "节奏收据和回流清单均可随作品根搬迁。"},
    {"file": "mv-update/scripts/update_plan.py", "dim": "更新计划根路径可移植",
     "tokens": ['"root_rel": "."'], "forbidden_tokens": ['"project_root": root'],
     "rationale": "基线、影响计划和命令模板不得持久化工作站绝对路径。"},
    {"file": "mv-image/scripts/image_receipts.py", "dim": "B14逐图动态验收",
     "tokens": ['machine.get("verdict") != "ok"', 'machine.get("precision_level") != "full"',
                '"all_current_accepted": bool(expected) and stale == 0'],
     "rationale": "逐图账本必须动态重算当前像素/引用/生成/QC/具名签收；只有 full+ok 且全集无 stale 才完成。"},
    {"file": "mv-image/scripts/image_receipts.py", "dim": "图片供应商原始证据",
     "tokens": ["PROVIDER_EVIDENCE_SCHEMA_VERSION = 2", "PROVIDER_ADAPTERS",
                "def provider_evidence_required", '"raw_capture"', '"output_selector"',
                '"provider_authenticity": "not_proven_offline"'],
     "rationale": "正式云端出图必须经受信 adapter 重解析独立 raw capture，精确绑定输出字节；"
                  "离线自洽性不得冒充 provider 真实性。"},
    {"file": "mv-image/scripts/image_qc.py", "dim": "图片QC报告根路径可移植",
     "tokens": ['"root_rel": "."', '"event_path": "生产数据/production_events.jsonl"'],
     "forbidden_tokens": ['"root": str(root)', '"event_path": str(_production_events_path(root))'],
     "rationale": "新 image_qc 报告及嵌套事件引用都只写作品相对路径。"},
    {"file": "mv-video/scripts/provider_evidence.py", "dim": "视频供应商证据fail-closed",
     "tokens": ["EVIDENCE_SCHEMA_VERSION = 2", "TRUSTED_API_ADAPTERS = {}",
                "provider_evidence_json_duplicate_key", "provider_evidence_path_not_in_evidence_tree",
                '"named_human_observation"', "provider_evidence_request_controls_mismatch",
                "provider_evidence_selected_asset_sha256_mismatch"],
     "rationale": "原始响应只能由固定 adapter 重解析，UI 只算具名人证，local 必须绑定 controls/refs/output；"
                  "当前公开 Veo/Runway 响应无法完整证明所需字段，API adapter 故意为空并拒绝自述。"},
    {"file": "mv-lyric-sync/scripts/align.py", "dim": "歌声对齐证据与时基",
     "tokens": ['"acceptance_eligible": False', 'evidence.get("acceptance_eligible") is not True',
                '"stem_master_timing": stem_timing', '"evidence_content_sha256"'],
     "rationale": "raw WhisperX 分数不得直接验收；正式声学证据需歌声专用+校准+eligible，且 stem 时基和证据内容均防篡改。"},
    {"file": "mv-craft/scripts/export_otio.py", "dim": "OTIO整数帧与官方往返",
     "tokens": ['"OTIO_SCHEMA": "RationalTime.1"', "def official_roundtrip", '"official_roundtrip"'],
     "rationale": "编辑时间使用整数帧 RationalTime，并以官方 OpenTimelineIO adapter round-trip 证明交换件可读。"},
    {"file": "mv-compose/color_input_manifest.py", "dim": "逐输入BT709显式变换",
     "tokens": ['"declared_bt709_full"', 'scale=in_range=full:out_range=limited',
                '"inputs_sha256"', '"timeline_sha256"'],
     "rationale": "逐输入分类和当前 hash 必须完整；full-range 只能经显式 full→limited 变换进入 SDR 交付。"},
    {"file": "mv-compose/delivery_qc.py", "dim": "交付响度block",
     "tokens": ['blocks.append("true_peak_above_0dbtp")', 'blocks.append("loudness_scan_unavailable")'],
     "rationale": "true peak>0dBTP、响度扫描不可用必须 block——扫不了≠过（fail-closed）。"},
    {"file": "mv-compose/delivery_qc.py", "dim": "最终PCM音轨同一性",
     "tokens": ["decoded_pcm_start_middle_end_correlation", '"drift_ms"', '"min_correlation"'],
     "rationale": "最终解码 PCM 必须在首/中/尾窗口与原歌互相关，并显式报告偏移和漂移。"},
    {"file": "mv-compose/delivery_qc.py", "dim": "交付文件可移植绑定",
     "tokens": ['row["path"] = mv_utils.relpath(root, output_path)',
                'row["sha256"] = mv_utils.content_hash(output_path)'],
     "rationale": "delivery_qc.files 逐项必须以作品相对路径和当前 SHA-256 绑定 final/master，"
                  "不得泄漏本机目录或只信角色名。"},
    {"file": "mv-craft/scripts/provenance.py", "dim": "C2PA信任维度分离",
     "tokens": ['"trust_checked"', '"trusted"', '"timestamp_validated"',
                '"timestamp_trusted"', '"timestamp_exception_allowed"', '"timestamped"',
                '"certificate_profile": "test_untrusted" if test_certificate else "production"'],
     "rationale": "结构/签名/信任/时间戳分别落证；内置测试证书永不冒充 production trusted。"},
    {"file": "mv-craft/scripts/provenance.py", "dim": "来源资产全集",
     "tokens": ['for suffix in ("png", "jpg", "jpeg", "webp")',
                'os.path.join(root, "出视频", "视频", "**", "*.mp4")',
                '"生产数据/provider_evidence/**/*"', '"出视频/provider_evidence/**/*"'],
     "rationale": "provenance 不得漏掉非 PNG 图片、嵌套挑版视频或供应商原始证据。"},
    {"file": "mv-review/scripts/mv_check.py", "dim": "具名总审收据",
     "tokens": ['"kind": "mv_review_receipt"', '"inputs_sha256": inputs', '"human_signoff"'],
     "rationale": "只有本次 0 BLOCK 的全量机检才可写具名 review receipt，并绑定当前交付/披露/来源链。"},
    {"file": "mv-craft/scripts/completion.py", "dim": "完成态收据控制",
     "tokens": ["CONTROLLED_COMPLETION_STAGES = frozenset(OUTPUT_HEALTH_STAGES)",
                '"mv_handoff_receipt"', '"mv_release_decision"', '"合规/release_decision.json"',
                "prompt_outputs_sha256", 'settings.get("演唱口型", "关闭") != "关闭"'],
     "rationale": "所有产物阶段完成态都经权威 health controller；语义 prompt 与口型 alignment 不能靠"
                  "手工进度勾选跳过，发布必须绑定当前 release decision。"},
    {"file": "mv-craft/scripts/completion.py", "dim": "完成态严格前驱链",
     "tokens": ['"beat", "lyric_sync", "plan", "semantic_plan", "pacing_check"',
                "def _predecessor_completion_errors", "if actual_keys != expected_keys",
                "if predecessor in OUTPUT_HEALTH_STAGES"],
     "rationale": "拍点/歌词/规划/节奏/picture-lock 等收据阶段不再能手工打勾；"
                  "完成当前阶段前必须按当前设置阶段表验证全部前驱行及 health。"},
    {"file": "mv-craft/scripts/state_contract.py", "dim": "同步不反向宣告完成",
     "tokens": ["never a", 'progress.state_of(status) == "done"',
                'not completion.stage_health(root, key)["ok"]'],
     "rationale": "sync 只迁移、保留或降级状态，绝不因健康产物把 --no-progress 的证据写入反向晋级。"},
    {"file": "mv-craft/scripts/gate.py", "dim": "规划阶段精确输入合同",
     "tokens": ['expected_inputs["settings_plan"]',
                '"alignment": os.path.join(root, "字幕", "alignment_report.json")',
                "clip_plan.inputs_sha256 含旧/未知输入键"],
     "rationale": "gate 与 completion 必须共用 song/beatgrid/lyrics/blueprint/alignment/settings_plan 精确字典；"
                  "旧整份 settings hash 与额外键不得导致两个权威验证器互相冲突。"},
    {"file": "mv-craft/scripts/release_decision.py", "dim": "真实上传字节与严格发布顺序",
     "tokens": ["UPLOAD_RECEIPT_SCHEMA_VERSION = 3", 'payload.get("uploaded_asset")',
                "provenance.c2pa.output", "def upload_receipt_claim",
                'for stage in ("compose", "disclosure", "provenance", "review")'],
     "rationale": "ready/uploaded 决策前必须复算总审前的全链 health；上传回执必须绑定实际字节，"
                  "C2PA 路线则必须精确上传 provenance 当前签名输出。"},
    {"file": "mv-craft/scripts/formal_readiness.py", "dim": "正式升级计划可移植",
     "tokens": ['project = "<作品根>"', "def _portable_message"],
     "forbidden_tokens": ['f\'python3 skills/mv/mv-craft/run.py "{root}"\''],
     "rationale": "formal readiness 的 JSON/Markdown 命令与诊断不得持久化工作站绝对路径。"},
    {"file": "_lib/disclosure.py", "dim": "AI披露根路径可移植",
     "tokens": ['"project_root": "."'], "forbidden_tokens": ['"project_root": root'],
     "rationale": "基础 disclosure payload 从源头只写相对根，避免其他调用方遗漏覆写时泄漏本机路径。"},
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
    """QC 硬闸核对：文件/必需片段缺失，或废弃片段回流，都算违规。"""
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
        for token in spec.get("forbidden_tokens") or []:
            if token in source:
                out.append({"gate": spec["file"], "kind": "hard_qc_forbidden_token_present",
                            "problem": f"{spec['file']} 出现已禁止片段 `{token}`（{spec['dim']}）——"
                                       "旧实现疑似回流；移除或先改 charter 留痕。"})
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
