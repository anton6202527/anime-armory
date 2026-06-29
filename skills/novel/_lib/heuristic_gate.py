# -*- coding: utf-8 -*-
"""heuristic_gate.py — 跨线宪法 B10 在 novel 线哨兵层的落地：脆弱启发式不得硬阻断。

docs/skill-design-principles.md **B10**：关键词命中 / 任意数值阈值 / 小样本回归这类
**脆弱启发式只能 ≤建议级**；要做 BLOCK 级（阻断级·能硬挡 post_write）必须有证据支撑——
对小说文本而言，证据=**只比较作者 curated 台账的结构化字段（整数/枚举/日期）即可复算的事实**，
trigger 里**不含任何对正文的子串/关键词/邻近扫描**。

为什么 novel 线要单独有这个模块：各创作线**互相独立、无共享层**（见 CLAUDE.md「全独立」+
independence-audit），所以跨线宪法 B10 在 novel 线必须有自己的 chokepoint，不依赖别线代码。
本模块实现 B10 的降级守卫（`confidence=="heuristic" and sev==阻断级 -> 建议级`），是 novel 哨兵的
单一收口点：**任何 confidence="heuristic" 却声明 severity="阻断级" 的 finding，统一自动降为 建议级。**

一处针对本线的**调参**（因层制宜）：B10 的参考实现默认「未标 confidence = 确定性闸 = 不受影响」，
因为发布闸层多数本就是像素/embedding 证据闸；而 novel 哨兵**天生几乎全是正文关键词/子串启发式**，
所以这里默认相反——**block 权要靠 `DETERMINISTIC_TYPES` 显式挣得**（证明自己只比结构化字段、
不扫正文），未登记的一律按 heuristic 处理，新增哨兵不会因为忘记标记就意外获得硬挡发布的权力。

纯标准库·纯函数·可测：cd skills/novel/_lib && python3 -m pytest test_heuristic_gate.py
"""

BLOCKING = "阻断级"
ADVISORY = "建议级"
HEURISTIC = "heuristic"
DETERMINISTIC = "deterministic"

# 仅这些 finding type 允许保留 阻断级（硬挡 post_write）——它们只比较作者 curated 台账的
# 结构化字段（整数序/章号），trigger 里没有对正文的任何子串/关键词/邻近扫描：
#   - timeline_event_disorder：timeline.json 的 order vs 成章 chapter 的整数序比较（timeline_check）
#   - foreshadowing_overdue   ：伏笔台账 expected_payoff_chapter vs through_chapter 的整数比较
#                               （台账条目是人工 curated，超期判定是纯整数运算·无正文扫描）
DETERMINISTIC_TYPES = frozenset({
    "timeline_event_disorder",
    "foreshadowing_overdue",
    # 结构化原子事实闸（FACTTRACK 式·只比作者 curated 台账的枚举/章号/区间，trigger 不扫正文）：
    #   - deceased_ledger_reactivation：state_ledger 结构化生命周期事件——已故/退场角色在死亡章之后
    #                                   发生非复活类**结构化** event（枚举×章号比较，不扫正文）。
    #   - world_fact_interval_conflict：world_state_ledger 同一 key 的两条原子事实有效区间重叠却值不同
    #                                   （[established_at,invalidated_at) 区间重叠 + value 不等·纯区间运算）。
    "deceased_ledger_reactivation",
    "world_fact_interval_conflict",
    # 力量体系结构化闸（power_system·只比作者 curated progression 快照的枚举/数值/章号，trigger 不扫正文）：
    #   - power_unknown_tier：境界名不在 registry.tiers.sequence（枚举集合判定）。
    #   - power_tier_regress / power_level_regress / power_combat_regress：境界/等级/战力跨章退档
    #     （数值×章号比较；快照写 regress_reason 命中豁免词才放行）。系统流/修仙战力崩坏=确定性硬伤。
    "power_unknown_tier",
    "power_tier_regress",
    "power_level_regress",
    "power_combat_regress",
})

_DOWNGRADE_NOTE = "（启发式低置信·按 B10 自动降为建议级·不硬阻断 post_write）"


def classify_confidence(alert_type, deterministic_types=DETERMINISTIC_TYPES):
    """finding type → 'deterministic' | 'heuristic'。纯函数·可测。"""
    return DETERMINISTIC if alert_type in deterministic_types else HEURISTIC


def annotate_confidence(alerts, deterministic_types=DETERMINISTIC_TYPES):
    """就地按 type 给每条 finding 标 confidence（已显式带 confidence 的不覆盖，detector 可自裁）。

    confidence 是 finding 的**内在证据等级**（单一真值，随 finding 走），与「是否降级」分离。
    返回 alerts（同一对象，便于链式）。"""
    for a in alerts:
        if isinstance(a, dict) and "confidence" not in a:
            a["confidence"] = classify_confidence(a.get("type"), deterministic_types)
    return alerts


def apply_confidence_policy(alerts):
    """B10 降级策略（就地）：confidence=="heuristic" 且 severity=="阻断级" → "建议级"。

    幂等（已降级的再调一次是 no-op）。未标 confidence 的保守按 heuristic 处理
    （= 未登记 DETERMINISTIC_TYPES 的一律不许硬阻断）。
    返回 (alerts, downgrades)；downgrades 是结构化降级账，供报告可见化（不静默吞掉）。"""
    downgrades = []
    for a in alerts:
        if not isinstance(a, dict):
            continue
        conf = a.get("confidence", HEURISTIC)
        if conf == HEURISTIC and a.get("severity") == BLOCKING:
            a["severity"] = ADVISORY
            a["downgraded_from"] = BLOCKING
            note = a.get("note", "")
            if _DOWNGRADE_NOTE not in note:
                a["note"] = f"{note}{_DOWNGRADE_NOTE}"
            downgrades.append({
                "type": a.get("type"), "entity": a.get("entity"),
                "chapter": a.get("chapter"), "from": BLOCKING, "to": ADVISORY,
            })
    return alerts, downgrades


def enforce(alerts, deterministic_types=DETERMINISTIC_TYPES):
    """哨兵收口便捷入口：先 annotate_confidence 再 apply_confidence_policy。

    哨兵 main()/consistency_audit 在算 blocking 前调一次即可，保证所有消费端看到的
    severity 都是 B10 策略生效后的最终值（没有任何消费端会看到 heuristic 阻断级）。
    返回 (alerts, downgrades)。"""
    annotate_confidence(alerts, deterministic_types)
    return apply_confidence_policy(alerts)


def count_blocking(alerts):
    """策略生效后真实阻断数（只数确定性证据闸留下的 阻断级）。纯函数·可测。"""
    return sum(1 for a in alerts if isinstance(a, dict) and a.get("severity") == BLOCKING)
