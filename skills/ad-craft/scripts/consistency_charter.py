#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ad 线一致性/合规硬闸【防降级宪章】（n2d consistency_charter 同哲学）。

为什么存在：硬闸最常见的死法不是被删掉，而是在某次「优化」提交里被静默降档——
block 变 warn、无条件变带条件、gate 读报告变「报告缺失也放行」——而没有任何测试变红。
n2d 线为此立了 charter：**每一条承重闸门在这里占一行，声明它必须保持的最低严重度**；
配套守卫测试直接内省 gate.py 源码 + 功能验证，降档必须来这里改一行**可见、带日期、
带理由**的记录，把静默降级变成显式审计决策。

本文件是 ad 线的执法意图唯一持久化来源（single source of enforcement intent）：
  · LOCKED_BLOCK_CODES —— gate.py 中必须存在且保持 block 严重度的 finding code。
  · INVARIANTS —— 不落在单一 code 上的结构性纪律（advisory 降档规则、新鲜度规则、
    占位 VO 分阶段规则），由守卫测试功能性锁定。

改动流程：要降档/移除任何一行，先在这里改（附 decided 日期与 rationale），
让守卫测试的红灯变成一次显式决策，而不是 code review 里没人注意的一行 diff。

用法：python3 consistency_charter.py  # 打印宪章表（只读，无副作用）
"""
from __future__ import annotations

import json
import sys

SCHEMA_VERSION = 1
KIND = "ad_consistency_charter"

# ── 承重 block code 台账 ─────────────────────────────────────────────────────
# 每行：code（gate.py finding code）/ where（哪个 findings 函数）/ rationale / decided。
# required_severity 一律 block；may_be_conditional 标注「允许的条件化」（超出即降级）。
LOCKED_BLOCK_CODES = [
    # —— brief / 合规前置 ——
    {"code": "brief_missing", "where": "brief_findings",
     "rationale": "没有 brief 就花钱＝无的放矢；投放目标/合规底线全悬空", "decided": "2026-07-23"},
    {"code": "brief_required_missing", "where": "brief_findings",
     "rationale": "brief 最小必填集是所有下游机检的输入", "decided": "2026-07-23"},
    {"code": "brief_deferred_missing", "where": "brief_findings",
     "rationale": "claim 依据/授权等花钱 gate 前合规项，缺了成片即废", "decided": "2026-07-23"},
    {"code": "ad_law_report_missing", "where": "ad_law_findings",
     "rationale": "广告法机检是唯一能 BLOCK 的文案闸（score_findings 立的规矩）", "decided": "2026-07-23"},
    {"code": "ad_law_block", "where": "ad_law_findings",
     "rationale": "绝对化用语等统法条 block 不允许任何理由放行", "decided": "2026-07-23"},
    {"code": "producer_pack_block", "where": "producer_pack_findings",
     "rationale": "claim 依据/授权/法律声明/资产绑定未闭合不得开机", "decided": "2026-07-23"},
    # —— 确定性生产闸 ——
    {"code": "storyboard_missing", "where": "storyboard_findings",
     "rationale": "无分镜出图＝无契约生产", "decided": "2026-07-23"},
    {"code": "voice_manifest_missing", "where": "voice_findings",
     "rationale": "无实测 VO 时长，镜头时长全是猜的", "decided": "2026-07-23"},
    {"code": "asset_registry_snapshot_stale", "where": "registry_snapshot_findings",
     "rationale": "照过期定妆快照出图本身就是漂移源（干净但过期的证据不是证据）", "decided": "2026-07-23"},
    # —— 生图路由治理 ——
    {"code": "image_route_incomplete", "where": "image_backend_findings",
     "rationale": "生图必须分列具体模型+渠道，厂商壳不能作为生成者", "decided": "2026-07-23"},
    {"code": "image_backend_forbidden", "where": "image_backend_findings",
     "rationale": "逆向/未授权渠道不得用于广告出图", "decided": "2026-07-23"},
    {"code": "image_model_unknown", "where": "image_backend_findings",
     "rationale": "未核验模型名不得花钱", "decided": "2026-07-23"},
    {"code": "image_channel_unknown", "where": "image_backend_findings",
     "rationale": "未登记渠道不得花钱", "decided": "2026-07-23"},
    {"code": "image_backend_non_codex_requires_signoff", "where": "image_backend_findings",
     "rationale": "非默认路线必须用户显式签核，适配层不得偷换模型", "decided": "2026-07-23"},
    {"code": "image_backend_mixed", "where": "image_backend_findings",
     "rationale": "项目内混用生图路由＝跨镜风格漂移的确定来源", "decided": "2026-07-23"},
    {"code": "image_output_backend_mixed", "where": "image_output_backend_findings",
     "rationale": "已落图 provenance 混后端，成片风格必然割裂", "decided": "2026-07-23"},
    {"code": "image_output_reference_inputs_missing", "where": "image_output_backend_findings",
     "rationale": "产品镜 prompt 声称引用不等于真实图片输入（文生图产品＝伪造产品）", "decided": "2026-07-23"},
    # —— 一致性机检（ad 线的「脸」）——
    {"code": "product_qc_missing", "where": "product_qc_findings",
     "rationale": "产品/logo/品牌色一致性是 ad 线的崩脸检查，缺报告不得出视频", "decided": "2026-07-23"},
    {"code": "product_qc_block", "where": "product_qc_findings",
     "rationale": "产品漂移带病续做，后面每一步都是废片钱", "decided": "2026-07-23"},
    {"code": "product_qc_precision_not_full", "where": "product_qc_findings",
     "rationale": "降级精度的机检不算检过；唯一出口是报告内人工留痕放行（manual_review_accepted）",
     "may_be_conditional": "manual_review_accepted 留痕时降 warn", "decided": "2026-07-23"},
    {"code": "product_qc_pending_images", "where": "product_qc_findings",
     "rationale": "no_image pending＝机检空转，报告存在≠真检过", "decided": "2026-07-23"},
    {"code": "video_contract_missing", "where": "video_contract_findings",
     "rationale": "图→视频契约继承不核验，出视频 prompt 会丢定妆约束", "decided": "2026-07-23"},
    {"code": "video_contract_block", "where": "video_contract_findings",
     "rationale": "契约继承 block＝视频 prompt 已背离定妆", "decided": "2026-07-23"},
    {"code": "video_qc_missing", "where": "video_qc_findings",
     "rationale": "clip 落档不 QC 就合成，废 clip 会焊进成片", "decided": "2026-07-23"},
    {"code": "video_qc_block", "where": "video_qc_findings",
     "rationale": "视频 QC block 未清不得合成", "decided": "2026-07-23"},
    {"code": "video_qc_precision_not_full", "where": "video_qc_findings",
     "rationale": "同 product_qc_precision_not_full；唯一出口是留痕人工放行",
     "may_be_conditional": "manual_review_accepted 留痕时不阻断", "decided": "2026-07-23"},
    {"code": "video_clips_missing", "where": "video_clip_findings",
     "rationale": "无 clip 不能进合成", "decided": "2026-07-23"},
    # —— 覆盖账本（2026-07 新增，n2d consistency_coverage 对位）——
    {"code": "verifier_coverage_block", "where": "verifier_coverage_findings",
     "rationale": "适用 × 休眠 → 交付前阻断：机检空转（报告存在但 0 真实对象被检）不算检过；"
                  "唯一出口是 合规/degraded_qc_waiver.json 签核留痕",
     "may_be_conditional": "有效 waiver 时降 warn（verifier_coverage.py 内部降档，留痕）",
     "decided": "2026-07-23"},
    {"code": "verifier_coverage_missing", "where": "verifier_coverage_findings",
     "rationale": "compose（交付点）fail-closed：没有覆盖账本＝无法证明该跑的机检都真跑了",
     "may_be_conditional": "仅 compose 阶段 block；video 阶段 warn", "decided": "2026-07-23"},
]

# ── 结构性纪律（功能性锁定，不落在单一 code 上）───────────────────────────────
INVARIANTS = [
    {"id": "advisory_never_blocks",
     "statement": "创意/启发式侧车（_advisory_report_findings 消费的一切）无论自身报什么，"
                  "并入 gate 后最高只能是 warn；报告缺失只能是 info。只有广告法与确定性闸门能 BLOCK。",
     "origin": "score_findings 2026-06 立规", "decided": "2026-07-23"},
    {"id": "freshness_blocks_hard_reports",
     "statement": "硬闸报告早于其输入产物必须 block（{code}_stale）：干净但过期的报告不是证据。",
     "origin": "report_freshness_findings", "decided": "2026-07-23"},
    {"id": "voice_placeholder_stage_rule",
     "statement": "占位 VO：image 阶段 warn（定妆/首帧不依赖精确时长）；video/compose 阶段 block"
                  "（占位时长会被焊进帧/成片），仅 --allow-placeholder 显式放行 demo。",
     "origin": "voice_findings", "decided": "2026-07-23"},
    {"id": "gate_reads_sidecars_not_subprocess",
     "statement": "gate 读侧车报告文件（load_json），不在 gate 内 subprocess 重跑检测器；"
                  "重跑归各 runner，gate 只消费证据（producer/platform pack 为进程内构建例外）。",
     "origin": "n2d gate 同构", "decided": "2026-07-23"},
]


def build() -> dict:
    return {"schema_version": SCHEMA_VERSION, "kind": KIND,
            "locked_block_codes": LOCKED_BLOCK_CODES, "invariants": INVARIANTS}


def main() -> int:
    doc = build()
    print(f"# ad 一致性防降级宪章  locked_block_codes={len(LOCKED_BLOCK_CODES)}  invariants={len(INVARIANTS)}")
    print(json.dumps(doc, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
