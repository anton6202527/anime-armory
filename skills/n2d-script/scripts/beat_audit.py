#!/usr/bin/env python3
"""beat_audit.py — 集内留存节拍机检（Gap4/5）。

为什么存在：`导演节奏.md` 要求"先列节拍点表(开场钩/钩子/爽点/集尾钩)再写词"，voiceover 也有
⚡/💥/🪝 标记，但**没有任何机检**——没人量"是否每 15-20s 一个钩子、是否 ≥1 反转、集尾是否硬断、
爽点是否只有情绪没有信息增量"。2026 爆款关键是"信息回报+情绪回报叠加"，且要反同质化。

本脚本读 voiceover.txt（钩子标记 + 情绪）+ 可选 镜头时长.json（真实秒）→ 出：
  ① 集内节拍体检：开场冷启 / 钩子间隔 / ≥1 反转 / 集尾 cliffhanger / 镜头时长曲线。
  ② 情绪回报 vs 信息回报（Gap4）：爽点是否只有情绪宣泄、缺信息增量。
  ③ --series：跨集套路同质化（桥段指纹 Jaccard），治"AI 模板复印、观众疲劳"；
     + 跨集冷开场链（P2）+ 叙事一致性审计优先级（G-S1）+ **看点高潮位复核**（北极星看点④·
     用真实 镜头时长.json 量"最强看点落在时间轴哪个百分位"，治集内虎头蛇尾 / 平庸无看点集）。

report-only（默认 exit 0）；--strict 时 must 级问题 exit 1。**不替代 validate_timings 闸门**，是其旁路的留存建议。

用法:
    python3 beat_audit.py <作品根> 第N集 [--strict] [--json]
    python3 beat_audit.py <作品根> --series [--json]
"""
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
try:
    from n2d_thresholds import load_benchmark  # noqa: E402
except Exception:  # pragma: no cover - beat_audit must remain usable in partial checkouts
    load_benchmark = None

LINE_RE = re.compile(r"^\[镜头(\d+)·([^·\]]+)·([^·\]]+?)(?:·([^·\]]+))?\]\s*(.*)$")
HOOK_NORMAL = "⚡"
HOOK_PAYOFF = "💥"
HOOK_ENDING = "🪝"

# 信息回报：揭示信息增量（真相/身世/系统/线索/数值/命名）。
INFO_RE = re.compile(r"(原来|竟是|竟然|其实|真相|身世|来历|名字|是.{0,6}的人|系统|面板|提示|【|"
                     r"等级|经验|线索|证据|因为|原来是|揭|暴露|发现|秘密|内幕)")
# 情绪回报：情绪宣泄/解气（反击/打脸/解气/胜负/生死/护宠）。
EMO_RE = re.compile(r"(反击|还手|打脸|解气|爽|痛快|怒|恨|哭|跪|斩|杀|赢|胜|夺回|护|宠|碾压|"
                    r"震住|压住|逆袭|翻盘|报仇|雪恨)")
# 反转信号（≥1 反转要求）。
REVERSAL_RE = re.compile(r"(原来|竟|反转|没想到|不料|岂料|居然|反而|却|逆转|翻盘)")
# 钩子内容信号（治"钩子检测只认 ⚡💥🪝 标记、作者漏标就误报"）：从台词内容推断这里其实是个钩子，
# 用来补回作者漏标的钩子，避免 hook_gap/cold_open/集尾钩 误判（只用于消除误报，不凭空加 must）。
HOOK_CONTENT_RE = re.compile(r"(危机|来了|出事|不好了|危险|追来|杀|逃|爆|突然|悬|未完|待续|下一[集章]|"
                             r"怎么会|不可能|是谁|到底|为什么|揭|真相|秘密|发现|生死|绝境|反杀|打脸|逆袭)")
CALM_EMO = ("低沉", "平静", "茫然", "悲伤", "淡漠", "疲惫")
# 高能/峰值情绪（用于情绪弧起伏判定：缺峰值=情绪扁平）。
PEAK_EMO = ("愤怒", "怒", "暴怒", "狂喜", "痛快", "震惊", "惊恐", "崩溃", "亢奋", "癫狂", "杀意", "决绝", "爆发")

# 实体抽取（用于集间「钩子接力」连贯性）：上一集集尾钩抛出的人/物，下一集冷开场是否接住同一根线。
# 实体 = 出场角色（非旁白）∪ 称谓 ∪ 【…】《…》专名标记。保守取词，宁缺毋滥（漏报好过误拦流水线）。
_TITLE_RE = re.compile(r"[一-鿿]{0,4}(?:娘娘|王爷|师尊|陛下|公主|太子|小姐|少爷|夫人|长老|"
                       r"师兄|师姐|宗主|皇后|贵妃|将军|侍卫|掌门|大人|阁下|城主|帝君|魔尊)")
_BRACKET_RE = re.compile(r"【([^】]{1,20})】|《([^》]{1,20})》")


def region_entities(beats):
    """一段 beats（开场/集尾窗口）里的具名实体集合：角色名 + 称谓 + 专名标记。"""
    ents = set()
    for b in beats:
        role = (b.get("role") or "").strip()
        if role and role != "旁白":
            ents.add(role)
        txt = b.get("text") or ""
        for grp in _BRACKET_RE.findall(txt):
            for g in grp:
                if g.strip():
                    ents.add(g.strip())
        for m in _TITLE_RE.findall(txt):
            ents.add(m)
    return ents


def _inferred_hook(beat) -> bool:
    """这一拍是否（按内容）算一个钩子——补回作者漏标的 ⚡💥🪝。"""
    return bool(beat["hooks"]) or bool(REVERSAL_RE.search(beat["text"])) or bool(HOOK_CONTENT_RE.search(beat["text"]))

HOOK_GAP_SEC = 20.0   # 中段钩子间隔上限（导演节奏 §二：每 15-20s 一个钩子）
HOOK_GAP_SHOTS = 4    # 无真实时长时：相邻钩子最多隔几镜
LINK_WINDOW = 3       # 集尾钩 / 下集冷开场 的窗口拍数（取首/尾各 N 拍算实体重合）

VISUAL_HOOK_RE = re.compile(r"(画面|视觉|特写|近景|大特写|冲突|动作|打斗|掌掴|血|脸|表情|追|逃|刀|剑|火|爆|"
                            r"系统面板|光幕|标题卡|字幕|烧屏|大字|caption|title|text|cold open|冷开场|倒叙)")
PROMISE_DUE_KEYS = ("payoff_due", "payoff_episode", "payoff_ep", "payoff_clip", "payoff_at",
                    "delayed_payoff_ep", "due_episode", "due_clip")
FIRST_SCREEN_REQUIRED_FIELDS = {
    "visual_conflict": ("visual_conflict",),
    "content_proposition": ("content_proposition",),
    "onscreen_text": ("onscreen_text",),
    "muted_safe_proof": ("muted_safe_proof",),
    "expected_metric": ("expected_metric",),
}
PROMISE_PAYOFF_STATUS_PAID = {
    "paid", "paid_off", "resolved", "closed", "done", "fulfilled", "payoff",
    "本集兑现", "已兑现", "兑现", "完成",
}
PROMISE_PAYOFF_STATUS_OPEN = {"", "open", "pending", "planned", "ongoing", "待兑现", "未兑现", "延迟"}
CREATIVE_PRIORS_FILENAME = "creative_priors.json"
APPLIED_CREATIVE_PRIORS_FILENAME = "applied_creative_priors.json"
ALLOWED_FIRST_SCREEN_METRICS = {"retention_3s", "retention_6s"}
DEFAULT_RETENTION_HOOK_FLOOR = 0.80
DEFAULT_CAPTION_WORDS_PER_SEC_BAND = (5.0, 10.0)
DEFAULT_FIRST_SCREEN_WINDOW_SEC = 3.0
DEFAULT_FIRST_6S_HOOK_REQUIRED = True
CJK_RE = re.compile(r"[\u3400-\u9fff]")
LATIN_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?")


def _storyboard_path(root, ep):
    return Path(root) / "脚本" / ep / "storyboard.json"


def load_storyboard(root, ep):
    p = _storyboard_path(root, ep)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _nonempty(value) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set)):
        return any(_nonempty(v) for v in value)
    if isinstance(value, dict):
        return any(_nonempty(v) for v in value.values())
    return value not in (None, "", False)


def _first_clip(sb):
    clips = sb.get("clips") if isinstance(sb, dict) else None
    if isinstance(clips, list):
        for clip in clips:
            if isinstance(clip, dict):
                return clip
    return {}


def _candidate_first_screen_contracts(sb):
    """首屏留存契约候选：顶层优先，兼容前两个 clip/continuity/retention 子块。"""
    if not isinstance(sb, dict):
        return []
    out = []
    for key in ("first_3s_visual_hook", "first_screen_hook", "muted_first_screen", "opening_hook"):
        out.append(sb.get(key))
    first = _first_clip(sb)
    for container in (first, first.get("retention") if isinstance(first, dict) else None,
                      first.get("continuity") if isinstance(first, dict) else None):
        if not isinstance(container, dict):
            continue
        for key in ("first_3s_visual_hook", "first_screen_hook", "muted_first_screen", "opening_hook"):
            out.append(container.get(key))
    return [x for x in out if _nonempty(x)]


def _contract_text(contract) -> str:
    if isinstance(contract, str):
        return contract
    if isinstance(contract, dict):
        keys = ("visual", "visual_hook", "画面", "onscreen_text", "onscreen_text_hook", "text",
                "caption", "title", "muted_safe_proof", "proof", "proposition", "description")
        return " ".join(str(contract.get(k) or "") for k in keys)
    return str(contract or "")


def _contract_field(contract, field):
    if not isinstance(contract, dict):
        return None
    for key in FIRST_SCREEN_REQUIRED_FIELDS.get(field, (field,)):
        value = contract.get(key)
        if _nonempty(value):
            return value
    return None


def _first_screen_schema_missing(contract):
    if not isinstance(contract, dict):
        return list(FIRST_SCREEN_REQUIRED_FIELDS)
    return [field for field in FIRST_SCREEN_REQUIRED_FIELDS if not _nonempty(_contract_field(contract, field))]


def _contract_muted_safe(contract) -> bool:
    if isinstance(contract, dict):
        explicit = contract.get("muted_safe")
        if explicit is True:
            return True
        if isinstance(explicit, str) and explicit.strip().lower() in {"true", "yes", "y", "1", "是", "已证明", "安全"}:
            return True
        if _nonempty(contract.get("muted_safe_proof")) or _nonempty(contract.get("onscreen_text")):
            return True
    return bool(VISUAL_HOOK_RE.search(_contract_text(contract)))


def audit_first_screen_contract(root, ep, beats):
    """0-3s 首屏留存契约：必须证明关声也能看懂钩子。"""
    sb = load_storyboard(root, ep)
    if sb is None:
        return []
    findings = []
    contracts = _candidate_first_screen_contracts(sb)
    if not contracts:
        findings.append(("must", "missing_first_3s_visual_hook",
                         "storyboard.json 缺 first_3s_visual_hook：正式出图前必须写结构化首屏契约 visual_conflict/content_proposition/onscreen_text/muted_safe_proof/expected_metric，不能只靠旁白抓人"))
        return findings
    missing_sets = [_first_screen_schema_missing(c) for c in contracts]
    if not any(not missing for missing in missing_sets):
        best_missing = min(missing_sets, key=len)
        findings.append(("must", "incomplete_first_3s_visual_hook",
                         "first_3s_visual_hook 不是严格结构：缺 %s；正式出图前必须把首屏视觉冲突、内容承诺、烧屏文字、静音证明和目标指标写成可审计字段" %
                         ",".join(best_missing)))
    if not any(_contract_muted_safe(c) for c in contracts):
        findings.append(("must", "first_3s_not_muted_safe",
                         "首屏钩子没有证明静音可读：补 visual_hook / onscreen_text_hook / muted_safe_proof，确保关声也能理解危机或悬念"))
    head = beats[:2]
    if head and not any(_inferred_hook(b) for b in head):
        findings.append(("warn", "first_3s_contract_without_beat_hook",
                         "storyboard 写了首屏契约，但 voiceover 前2拍没有钩子信号：让台词/画面节拍与 first_3s_visual_hook 对齐"))
    return findings


def _retention_ledger(sb):
    if not isinstance(sb, dict):
        return []
    for key in ("retention_promise_ledger", "retention_promises", "hook_promise_ledger"):
        value = sb.get(key)
        if isinstance(value, list):
            return [v for v in value if isinstance(v, dict)]
        if isinstance(value, dict):
            items = value.get("promises") or value.get("items") or value.get("ledger")
            if isinstance(items, list):
                return [v for v in items if isinstance(v, dict)]
            return [dict({"hook_id": k}, **v) for k, v in value.items() if isinstance(v, dict)]
    out = []
    for clip in sb.get("clips") or []:
        if not isinstance(clip, dict):
            continue
        ret = clip.get("retention") or {}
        if isinstance(ret, dict):
            promise = ret.get("promise") or ret.get("retention_promise")
            if isinstance(promise, dict):
                out.append(promise)
            promises = ret.get("promises")
            if isinstance(promises, list):
                out.extend(v for v in promises if isinstance(v, dict))
    return out


def _promise_has_due(promise):
    return any(_nonempty(promise.get(k)) for k in PROMISE_DUE_KEYS) or str(promise.get("payoff_status") or "").strip() in {"paid", "paid_off", "resolved", "closed", "本集兑现", "已兑现"}


def _promise_status(promise):
    return str(promise.get("payoff_status") or promise.get("status") or "").strip().lower()


def _promise_has_payoff_evidence(promise):
    return any(_nonempty(promise.get(k)) for k in (
        "payoff_evidence", "evidence", "payoff_clip", "paid_by_episode", "payoff_asset", "payoff_frame"
    ))


def _promise_due_this_episode(promise, ep):
    ep_text = str(ep or "")
    for key in ("payoff_episode", "payoff_ep", "delayed_payoff_ep", "due_episode", "paid_by_episode"):
        value = str(promise.get(key) or "").strip()
        if value and (value == ep_text or _ep_num(value) == _ep_num(ep_text)):
            return True
    for key in ("payoff_due", "due", "payoff_at"):
        value = str(promise.get(key) or "").strip()
        if value and (ep_text in value or _ep_num(value) == _ep_num(ep_text)):
            return True
    return any(_nonempty(promise.get(k)) for k in ("payoff_clip", "due_clip"))


def audit_retention_promise_ledger(root, ep, beats):
    """钩子承诺-兑现账本：每个强钩子至少要有可追踪的承诺与兑现期限。"""
    sb = load_storyboard(root, ep)
    if sb is None:
        return []
    findings = []
    ledger = _retention_ledger(sb)
    has_hooks = any(_inferred_hook(b) for b in beats)
    if has_hooks and not ledger:
        findings.append(("must", "missing_retention_promise_ledger",
                         "storyboard.json 缺 retention_promise_ledger：正式出图前必须登记 opening/cliffhanger 的 hook_id、promise_type、opened_at、payoff_due，避免假悬念/爽点不兑现"))
        return findings
    for i, item in enumerate(ledger, 1):
        missing = []
        if not _nonempty(item.get("hook_id")):
            missing.append("hook_id")
        if not _nonempty(item.get("promise_type")):
            missing.append("promise_type")
        if not _nonempty(item.get("opened_at")):
            missing.append("opened_at")
        if not _nonempty(item.get("promise")):
            missing.append("promise")
        if not _promise_has_due(item):
            missing.append("payoff_due")
        if missing:
            findings.append(("must", "incomplete_retention_promise",
                             f"retention_promise_ledger 第{i}条缺 {','.join(missing)}：每个钩子承诺必须能追踪到何时兑现/是否延迟"))
        status = _promise_status(item)
        if status in PROMISE_PAYOFF_STATUS_PAID and not _promise_has_payoff_evidence(item):
            findings.append(("must", "paid_promise_without_evidence",
                             f"retention_promise_ledger 第{i}条标记已兑现，但缺 payoff_clip/payoff_evidence/paid_by_episode：承诺兑现必须能回看证据"))
        if _promise_due_this_episode(item, ep) and status in PROMISE_PAYOFF_STATUS_OPEN and not _promise_has_payoff_evidence(item):
            findings.append(("must", "due_promise_without_payoff_evidence",
                             f"retention_promise_ledger 第{i}条本集到期，但没有 payoff_status=paid/resolved 或 payoff_evidence：不能把到期钩子带进贵工位"))
    if any(HOOK_ENDING in b["hooks"] or _inferred_hook(b) for b in beats[-2:]):
        tail_promises = [p for p in ledger if re.search(r"(cliff|ending|tail|next|追更|集尾|尾钩|断点)", str(p.get("promise_type") or p.get("hook_id") or ""), re.I)]
        if not tail_promises:
            findings.append(("must", "missing_tail_promise",
                             "集尾有 cliffhanger，但 retention_promise_ledger 没有集尾/追更承诺条目：补 promise_type=cliffhanger/tail_hook 与 payoff_due/delayed_payoff_ep"))
    return findings


def _load_json_file(path):
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _load_creative_priors(root):
    data = _load_json_file(Path(root) / "生产数据" / CREATIVE_PRIORS_FILENAME)
    if not isinstance(data, dict) or data.get("kind") != "n2d_creative_priors":
        return None
    priors = data.get("priors")
    return data if isinstance(priors, dict) and priors else None


def _creative_prior_decisions(root, ep, sb):
    decisions = {}
    applied_path = Path(root) / "脚本" / ep / APPLIED_CREATIVE_PRIORS_FILENAME
    applied = _load_json_file(applied_path)
    if isinstance(applied, dict):
        explicit = applied.get("decisions")
        if isinstance(explicit, dict):
            decisions.update({str(k): v for k, v in explicit.items()})
        legacy_applied = applied.get("applied_creative_priors")
        if isinstance(legacy_applied, dict):
            for key in legacy_applied:
                decisions.setdefault(str(key), {"status": "applied", "source": APPLIED_CREATIVE_PRIORS_FILENAME})
    if isinstance(sb, dict):
        for key in ("creative_prior_decisions", "creative_priors_decisions", "retention_prior_decisions"):
            value = sb.get(key)
            if isinstance(value, dict):
                decisions.update({str(k): v for k, v in value.items()})
    rejected = _load_json_file(Path(root) / "脚本" / ep / "rejected_creative_priors.json")
    if isinstance(rejected, dict):
        value = rejected.get("decisions") or rejected.get("rejected_creative_priors")
        if isinstance(value, dict):
            decisions.update({str(k): v for k, v in value.items()})
    return decisions


def _decision_status(decision):
    if isinstance(decision, dict):
        return str(decision.get("status") or decision.get("decision") or "").strip().lower()
    return str(decision or "").strip().lower()


def _decision_reject_reason(decision):
    if not isinstance(decision, dict):
        return ""
    return str(decision.get("rejected_reason") or decision.get("reason") or decision.get("why") or "").strip()


def audit_creative_priors_application(root, ep):
    priors = _load_creative_priors(root)
    if not priors:
        return []
    sb = load_storyboard(root, ep) or {}
    decisions = _creative_prior_decisions(root, ep, sb)
    findings = []
    for field in sorted((priors.get("priors") or {}).keys()):
        decision = decisions.get(field)
        status = _decision_status(decision)
        if status in {"applied", "apply", "accepted", "used", "adopted", "已应用", "采用"}:
            continue
        if status in {"rejected", "reject", "skip", "skipped", "ignored", "not_applied", "拒绝", "不采用"}:
            if not _decision_reject_reason(decision):
                findings.append(("must", "creative_prior_rejected_without_reason",
                                 f"creative_priors.json 中 {field} 被拒绝/跳过，但缺 rejected_reason：投放回灌先验必须可解释地应用或拒绝"))
            continue
        findings.append(("must", "creative_prior_not_acknowledged",
                         f"creative_priors.json 中 {field} 有第一方投放胜出先验，但本集缺 applied_creative_priors.json 或 creative_prior_decisions 决策证据"))
    return findings


def _env_sec(name, default):
    """env 覆盖节奏阈值（缺/坏→默认）——平台/题材不同，基准可调不写死。"""
    try:
        v = os.environ.get(name)
        return float(v) if v not in (None, "") else default
    except Exception:
        return default


# A1 多层节奏间距栅格（导演节奏 §二 + 2026 短剧基准）：钩子层(②·≤20s)之外补两层。
#   · 爆点/反转 ≤30s（warn）：每 ~30s 一个剧情爆点；有钩子撑着但久无真反转/爽点 = 张力空转。
#   · 情绪峰   ≤180s（info）：每 ~3min 一个情绪峰值——主要约束长剪/多分钟集；漫剧短集天然不触发=无误报。
# 都只查「相邻两个该层拍之间」的间距（≥2 拍才有间距）：首拍前由 cold_open/钩子层覆盖、
# 0-1 拍由 ③no_reversal/⑦flat_emotion_arc 覆盖、末拍后留给集尾 cliffhanger（不该有近 payoff）——故不重复。
CADENCE_BLAST_SEC = _env_sec("N2D_BEAT_BLAST_GAP_SEC", 30.0)
CADENCE_PEAK_SEC = _env_sec("N2D_BEAT_PEAK_GAP_SEC", 180.0)


def _is_blast(beat) -> bool:
    """爆点/反转拍 = 💥爽点 ∪ 反转词（与 effective_hooked 的"钩子"区分：这是真兑现，不含内容推断钩）。"""
    return (HOOK_PAYOFF in beat["hooks"]) or bool(REVERSAL_RE.search(beat["text"]))


def _is_peak(beat) -> bool:
    """情绪峰拍 = 高能峰值情绪标注（愤怒/痛快/震惊/崩溃…）。"""
    return any(p in beat["emotion"] for p in PEAK_EMO)


def worst_cadence_gap(beats, starts, predicate, threshold):
    """该层拍（predicate 命中）相邻两拍间的最大超阈间距 (prev_sec, cur_sec, gap) 或 None。

    只看「相邻该层拍之间」——<2 拍返回 None（间距对 0-1 拍无意义，由别的检查兜）；
    不含首拍前（cold_open/钩子层管）与末拍后（留给集尾 cliffhanger）。纯函数·可测。"""
    times = sorted(starts.get(b["shot"], 0.0) for b in beats if predicate(b))
    if len(times) < 2:
        return None
    worst = None
    for a, b in zip(times, times[1:]):
        gap = b - a
        if gap > threshold and (worst is None or gap > worst[2]):
            worst = (a, b, gap)
    return worst


def _ep_num(ep):
    m = re.search(r"\d+", str(ep or ""))
    return int(m.group()) if m else None


def hook_link(prev_beats, beats):
    """判定「上一集集尾钩 → 本集冷开场」是否接住同一根因果线（实体重合）。

    返回 dict：prev_end_entities / open_entities / overlap / linked / has_signal。
    has_signal=False 表示证据不足（任一侧无具名实体）——不做判定，避免误拦。"""
    prev_end = region_entities(prev_beats[-LINK_WINDOW:]) if prev_beats else set()
    cur_open = region_entities(beats[:LINK_WINDOW]) if beats else set()
    overlap = prev_end & cur_open
    has_signal = bool(prev_end) and bool(cur_open)
    return {"prev_end_entities": sorted(prev_end), "open_entities": sorted(cur_open),
            "overlap": sorted(overlap), "linked": bool(overlap), "has_signal": has_signal}


def _valid_hook_bridge(bridge, prev_ep, ep):
    """显式跨集桥接声明：用于合法 thread-switch / delayed payoff，不强迫实体重合。"""
    if not isinstance(bridge, dict):
        return None
    src = str(bridge.get("from_episode") or bridge.get("prev_episode") or "").strip()
    if src and src not in {prev_ep, str(prev_ep).replace("第", "").replace("集", "")} and _ep_num(src) != _ep_num(prev_ep):
        return None
    if bridge.get("answers_prev_hook") is True:
        return bridge
    if str(bridge.get("thread_id") or "").strip() and (
        str(bridge.get("bridge_text") or bridge.get("summary") or bridge.get("reason") or "").strip()
        or str(bridge.get("delayed_payoff_ep") or bridge.get("delayed_to_episode") or "").strip()
    ):
        return bridge
    if str(bridge.get("delayed_payoff_ep") or bridge.get("delayed_to_episode") or "").strip():
        return bridge
    return None


def explicit_hook_bridge(root, ep, prev_ep=None):
    """读取 storyboard.json 里的 hook_bridge/cross_episode_bridge 声明。

    支持顶层或前两个 clip 的：
      hook_bridge / cross_episode_hook_bridge / narrative_bridge
      continuity.hook_bridge
    """
    prev_ep = prev_ep or ""
    p = Path(root) / "脚本" / ep / "storyboard.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    candidates = []
    for key in ("hook_bridge", "cross_episode_hook_bridge", "narrative_bridge"):
        candidates.append(data.get(key))
    clips = data.get("clips")
    if isinstance(clips, list):
        for clip in clips[:2]:
            if not isinstance(clip, dict):
                continue
            for key in ("hook_bridge", "cross_episode_hook_bridge", "narrative_bridge"):
                candidates.append(clip.get(key))
            cont = clip.get("continuity")
            if isinstance(cont, dict):
                candidates.append(cont.get("hook_bridge"))
    for cand in candidates:
        valid = _valid_hook_bridge(cand, prev_ep, ep)
        if valid:
            return valid
    return None


def incoming_link_findings(root, ep, beats):
    """本集 vs 上一集的因果钩子闭合检查（per-ep·可进 run.py strict 闸）。

    只有当①上一集存在且以 cliffhanger 收尾、②两侧都拿得到具名实体、③零重合 时才报 warn——
    即「上一集的钩子抛出的人/物，本集冷开场一个都没接住」，这是观众断片的硬伤。
    保守：证据不足或确有重合一律放过。strict 下 warn→block。"""
    n = _ep_num(ep)
    if n is None:
        return []
    prev_ep = f"第{n - 1}集"
    prev_state = _episode_open_close(root, prev_ep)
    if not prev_state or not prev_state.get("ends_cliff"):
        return []  # 上集没集尾钩 → 钩子闭合无从谈起（由 p2_resolved_ending/集尾钩检查覆盖）
    prev_vpath = Path(root) / "脚本" / prev_ep / "voiceover.txt"
    if not prev_vpath.exists():
        return []
    prev_beats = parse_voiceover(prev_vpath)
    link = hook_link(prev_beats, beats)
    if link["has_signal"] and not link["linked"]:
        bridge = explicit_hook_bridge(root, ep, prev_ep)
        if bridge:
            return []
        return [("warn", "cross_ep_hook_break",
                 f"{prev_ep}集尾钩抛出的 [{'/'.join(link['prev_end_entities'][:4])}] 在本集冷开场"
                 f"（[{'/'.join(link['open_entities'][:4])}]）一个都没接住——钩子接力断线，观众看不懂前因。"
                 f"本集前 {LINK_WINDOW} 拍直入上集悬置的那条线，或在 storyboard.json 写 hook_bridge"
                 f"（thread_id / answers_prev_hook / delayed_payoff_ep）声明合法桥接")]
    return []


def parse_voiceover(path):
    beats = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = LINE_RE.match(line)
        if not m:
            continue
        shot, role, emo, speed, text = m.groups()
        hooks = set(h for h in (HOOK_NORMAL, HOOK_PAYOFF, HOOK_ENDING) if h in line)
        beats.append({
            "shot": int(shot), "role": role.strip(), "emotion": emo.strip(),
            "speed": (speed or "").strip(), "text": text.strip(), "hooks": hooks,
        })
    return beats


def load_shot_seconds(root, ep):
    p = Path(root) / "脚本" / ep / "镜头时长.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    out = {}
    for k, v in data.items():
        m = re.search(r"(\d+)", str(k))
        if m:
            out[int(m.group(1))] = float(v)
    return out or None


def cumulative_starts(shot_secs):
    """镜号→该镜起始累计秒。"""
    starts, t = {}, 0.0
    for sn in sorted(shot_secs):
        starts[sn] = t
        t += shot_secs[sn]
    return starts, t


def audit_episode(root, ep):
    vpath = Path(root) / "脚本" / ep / "voiceover.txt"
    findings = []  # (severity, code, msg)  severity: must|warn|info
    if not vpath.exists():
        return [("must", "no_voiceover", f"缺 {ep}/voiceover.txt，先做阶段1 剧本改编")], {}
    beats = parse_voiceover(vpath)
    if not beats:
        return [("warn", "empty", "voiceover.txt 无可解析台词行（格式 [镜头N·角色·情绪·(语速)] 台词）")], {}

    shot_secs = load_shot_seconds(root, ep)
    hooked = [b for b in beats if b["hooks"]]
    payoffs = [b for b in beats if HOOK_PAYOFF in b["hooks"]]
    # 内容推断钩子（marker ∪ content）——只用于消除"漏标记"导致的 cold_open/hook_gap 误报，不新增 must。
    effective_hooked = [b for b in beats if _inferred_hook(b)]

    # ① 开场冷启：前 2 镜应有钩（标记或内容）或非慢旁白起
    head = beats[:2]
    head_hooked = any(b in effective_hooked for b in head)
    if not head_hooked and head and head[0]["role"] == "旁白" and head[0]["emotion"] in CALM_EMO:
        findings.append(("warn", "cold_open",
                         "开场疑似慢旁白起（旁白+平缓情绪、前2镜无钩）：改 0-3s 冷开场/倒叙钩，最炸的画面/台词放最前"))
    elif not head_hooked:
        findings.append(("info", "cold_open", "前2镜无钩子标记，确认是否 0-3s 冷开场抓人"))

    # ①b 0-3s 首屏视觉钩（storyboard 契约）：正式出图前必须证明静音可读。
    findings.extend(audit_first_screen_contract(root, ep, beats))

    # ①c 钩子承诺-兑现账本：把 opening/tail hook 从“感觉有钩”升级为可追踪承诺。
    findings.extend(audit_retention_promise_ledger(root, ep, beats))

    # ①d 投放回灌先验：有第一方 A/B 胜出先验时，必须明确应用或带理由拒绝。
    findings.extend(audit_creative_priors_application(root, ep))

    # ② 钩子间隔（导演节奏 §二）·用 marker∪content 钩子算间隔（漏标记不再误判 hook_gap）
    if shot_secs:
        starts, total = cumulative_starts(shot_secs)
        hook_times = sorted(starts.get(b["shot"], 0.0) for b in effective_hooked)
        prev = 0.0
        for t in hook_times:
            if t - prev > HOOK_GAP_SEC:
                findings.append(("warn", "hook_gap",
                                 f"{prev:.0f}s–{t:.0f}s 间隔 {t-prev:.0f}s 无钩子（>{HOOK_GAP_SEC:.0f}s）：中段易划走，补悬念/信息/反差/危机"))
            prev = t
        if total - prev > HOOK_GAP_SEC and hook_times:
            findings.append(("info", "hook_gap_tail", f"末钩到结尾 {total-prev:.0f}s 无新钩，确认集尾张力"))
        # ②b A1 多层节奏栅格：爆点/反转(≤30s·warn) + 情绪峰(≤180s·info·主要约束长剪)。
        #     只在该层 ≥2 拍且相邻间距超阈时报（dead stretch between detonations/peaks）。
        for code, label, pred, gap_sec, sev in (
            ("cadence_blast", "爆点/反转", _is_blast, CADENCE_BLAST_SEC, "warn"),
            ("cadence_peak", "情绪峰", _is_peak, CADENCE_PEAK_SEC, "info"),
        ):
            worst = worst_cadence_gap(beats, starts, pred, gap_sec)
            if worst:
                findings.append((sev, code,
                    f"{worst[0]:.0f}s–{worst[1]:.0f}s 间隔 {worst[2]:.0f}s 无{label}（>{gap_sec:.0f}s）："
                    f"有钩子撑着但久无{label}，张力空转易掉留存——中间补一个{label}"
                    f"（2026 短剧基准：{label}约每 {gap_sec:.0f}s 一次）"))
    else:
        idxs = sorted(b["shot"] for b in effective_hooked)
        for a, b in zip(idxs, idxs[1:]):
            if b - a > HOOK_GAP_SHOTS:
                findings.append(("info", "hook_gap_shots",
                                 f"镜{a}→镜{b} 隔 {b-a} 镜无钩（无镜头时长.json，按镜数估）：定稿后用真实秒复核"))

    # ③ ≥1 反转
    has_rev = bool(payoffs) or any(REVERSAL_RE.search(b["text"]) for b in beats)
    if not has_rev:
        findings.append(("warn", "no_reversal", "本集无 💥爽点 也无反转词：导演节奏要求每集 ≥1 次反转，补一个"))

    # ④ 集尾 cliffhanger（缺 🪝 标记时，先看末 2 拍内容是否其实已有 cliffhanger，避免漏标误判为"把戏讲完"）
    if not any(HOOK_ENDING in b["hooks"] for b in beats):
        tail = beats[-2:]
        if any(_inferred_hook(b) for b in tail):
            findings.append(("info", "ending_hook_unmarked",
                             "集尾疑已有 cliffhanger 内容但缺 🪝 标记：补标记便于机检/卡点对账（不影响留存，只为可追踪）"))
        else:
            findings.append(("warn", "no_ending_hook", "缺集尾 cliffhanger（标记与内容都没有）：集尾须硬断（危机悬置/真相半露/反转预告），别把戏讲完"))

    # ⑤ 情绪回报 vs 信息回报（Gap4）
    info_hooks, emo_hooks = [], []
    for b in hooked:
        if INFO_RE.search(b["text"]):
            info_hooks.append(b["shot"])
        if EMO_RE.search(b["text"]):
            emo_hooks.append(b["shot"])
    if hooked and not info_hooks:
        findings.append(("warn", "no_info_payoff",
                         "本集钩子/爽点全为情绪宣泄、零信息增量：2026 爆款要『信息回报+情绪回报』叠加，"
                         "至少一个钩子给观众新信息（真相/身世/线索/系统数值）"))
    elif hooked and not emo_hooks:
        findings.append(("info", "no_emo_payoff", "钩子偏信息、缺情绪释放，确认爽感是否足够"))

    # ⑥ 镜头时长曲线（导演节奏 §四/§五）
    if shot_secs and len(shot_secs) >= 4:
        vals = list(shot_secs.values())
        mean = sum(vals) / len(vals)
        if mean > 0:
            var = sum((v - mean) ** 2 for v in vals) / len(vals)
            cov = (var ** 0.5) / mean
            if cov < 0.18:
                findings.append(("info", "flat_rhythm",
                                 f"镜头近等长（变异系数 {cov:.2f}<0.18）像 PPT：走曲线——铺垫长镜+临近爽点碎切+爽点后留白"))

    # ⑦ 情绪节奏弧（语义·从 [情绪] 标注建设计态情绪曲线，治"emotion_flow 只有声学能量、没有语义情绪弧"）
    #    与 n2d-voice 的声学能量曲线互补：本检查的是"设计的情绪有没有起伏与峰值"，纯文本、定稿前可跑。
    if len(beats) >= 6:
        emotions = [b["emotion"] for b in beats]
        distinct = {e for e in emotions if e}
        calm_n = sum(1 for e in emotions if any(c in e for c in CALM_EMO))
        peak_n = sum(1 for e in emotions if any(p in e for p in PEAK_EMO))
        calm_ratio = calm_n / len(emotions)
        if len(distinct) <= 2:
            findings.append(("warn", "flat_emotion_arc",
                             f"整集情绪只有 {len(distinct)} 档（{'/'.join(sorted(distinct)) or '空'}），情绪节奏扁平："
                             "留存靠'憋—放'曲线（铺垫压抑→爆发释放），按导演节奏 §六给情绪起伏，别一条道走到黑"))
        elif calm_ratio >= 0.7:
            findings.append(("warn", "flat_emotion_arc",
                             f"整集 {calm_ratio:.0%} 是平缓/低沉情绪、缺高能峰值（peak {peak_n} 拍）："
                             "至少在爽点/反转拍给一个强情绪峰（愤怒/痛快/震惊/决绝），否则全程温吞易划走"))
        elif peak_n == 0:
            findings.append(("info", "no_emotion_peak",
                             "全集无高能峰值情绪（愤怒/痛快/震惊/崩溃…）：确认爽点拍的情绪强度是否够顶"))

    # ⑧ 集间因果钩子闭合（与上一集的接力·Gap：钩子接错根/接不上）
    findings.extend(incoming_link_findings(root, ep, beats))

    stats = {
        "shots": len(beats), "hooks": len(hooked), "payoffs": len(payoffs),
        "info_payoff_shots": info_hooks, "emo_payoff_shots": emo_hooks,
        "has_reversal": has_rev, "has_ending_hook": any(HOOK_ENDING in b["hooks"] for b in beats),
        "has_timings": bool(shot_secs),
        "has_storyboard": load_storyboard(root, ep) is not None,
    }
    return findings, stats


def episode_signature(root, ep):
    """桥段指纹：本集 payoff/conflict 关键词集合 + 钩子类型序列（用于同质化对比）。"""
    vpath = Path(root) / "脚本" / ep / "voiceover.txt"
    if not vpath.exists():
        return None
    beats = parse_voiceover(vpath)
    kws = set()
    for b in beats:
        for rx in (EMO_RE, INFO_RE, REVERSAL_RE):
            kws.update(rx.findall(b["text"]))
    emos = tuple(b["emotion"] for b in beats)
    return {"keywords": kws, "emotions": emos}


def jaccard(a, b):
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b) if (a | b) else 0.0


# ── 叙事一致性审计优先级（G-S1·2026-06-24 流程自审落地·ConStory-Bench arXiv 2603.05890） ──
# 长篇 LLM 一致性 bug 经验上**聚集在叙事中段 + 高 token 熵段**（事实/时序维度尤甚）。一致性审计
# 此前对所有集均匀施力；这里给一个 report-only 的风险加权，告诉操作者**哪些集该优先深审 + 加密抽帧/人审**。
def mid_arc_weight(index: int, total: int) -> float:
    """剧中段权重：位置 p=index/(total-1)∈[0,1]，权重 = 1−2|p−0.5| → 正中=1、两端=0。纯函数·可测。"""
    if total <= 1:
        return 0.0
    p = index / (total - 1)
    return round(1.0 - 2.0 * abs(p - 0.5), 4)


def token_entropy(text: str) -> float:
    """文本字符分布 Shannon 熵(bits)——高熵=信息密度高=漂移高发段。纯函数·可测。"""
    chars = [c for c in str(text or "") if not c.isspace()]
    if not chars:
        return 0.0
    n = len(chars)
    counts = Counter(chars)
    return round(-sum((c / n) * math.log2(c / n) for c in counts.values()), 4)


def narrative_risk_score(mid_w: float, entropy: float, ent_max: float) -> float:
    """叙事一致性审计风险分 = √(中段权重 × 相对熵)。几何均值→两者都高才高分。纯函数·可测。"""
    ent_norm = (entropy / ent_max) if ent_max > 0 else 0.0
    return round((max(mid_w, 0.0) * max(ent_norm, 0.0)) ** 0.5, 4)


def narrative_risk_profile(root):
    """按「剧中段位置 × 信息熵」给每集排一致性审计优先级（report-only·ConStory）。
    返回 (eps, ranked_rows, findings)；findings 只在 ≥4 集时给（太短无"中段"可言）。"""
    sdir = Path(root) / "脚本"
    eps = sorted([d.name for d in sdir.glob("第*集") if (d / "voiceover.txt").exists()],
                 key=lambda n: int(re.search(r"\d+", n).group()))
    rows = []
    for i, ep in enumerate(eps):
        beats = parse_voiceover(sdir / ep / "voiceover.txt")
        text = "".join(b["text"] for b in beats)
        rows.append({"episode": ep, "index": i, "entropy": token_entropy(text), "beats": len(beats)})
    ent_max = max((r["entropy"] for r in rows), default=0.0)
    total = len(rows)
    for r in rows:
        r["mid_arc_weight"] = mid_arc_weight(r["index"], total)
        r["risk_score"] = narrative_risk_score(r["mid_arc_weight"], r["entropy"], ent_max)
    ranked = sorted(rows, key=lambda r: (r["risk_score"], r["entropy"]), reverse=True)
    findings = []
    if total >= 4:
        k = max(1, total // 3)
        for r in ranked[:k]:
            if r["risk_score"] > 0:
                findings.append(("info", "narrative_audit_priority",
                    f"{r['episode']}：叙事一致性审计优先（中段权重 {r['mid_arc_weight']} × 熵 {r['entropy']} → "
                    f"risk={r['risk_score']}）——ConStory 显示长篇一致性 bug 聚集中段高熵段，建议 consistency_audit 深审 + 加密抽帧/人审"))
    return eps, ranked, findings


def audit_series(root):
    sdir = Path(root) / "脚本"
    eps = sorted([d.name for d in sdir.glob("第*集") if (d / "voiceover.txt").exists()],
                 key=lambda n: int(re.search(r"\d+", n).group()))
    sigs = {ep: episode_signature(root, ep) for ep in eps}
    dups = []
    for i, ea in enumerate(eps):
        for eb in eps[i + 1:]:
            sa, sb = sigs[ea], sigs[eb]
            if not sa or not sb:
                continue
            j = jaccard(sa["keywords"], sb["keywords"])
            if j >= 0.8 and len(sa["keywords"]) >= 4:
                dups.append((ea, eb, round(j, 2)))
    return eps, dups


def _episode_open_close(root, ep):
    """一集的开场/收尾态：opens_cold(前2拍有钩且非慢旁白起) + ends_cliff(集尾有 cliffhanger 标记或内容)。"""
    vpath = Path(root) / "脚本" / ep / "voiceover.txt"
    if not vpath.exists():
        return None
    beats = parse_voiceover(vpath)
    if not beats:
        return None
    head = beats[:2]
    tail = beats[-2:]
    slow_recap_open = bool(head and head[0]["role"] == "旁白" and head[0]["emotion"] in CALM_EMO
                          and not any(b["hooks"] for b in head))
    opens_cold = any(_inferred_hook(b) for b in head) and not slow_recap_open
    ends_cliff = (HOOK_ENDING in beats[-1]["hooks"]) or any(_inferred_hook(b) for b in tail)
    return {"opens_cold": opens_cold, "ends_cliff": ends_cliff, "beats": len(beats)}


def cold_open_chain(root):
    """P2 跨集冷开场链：切点要让**下一集**能 0-3s 冷开场（拆集法 P2）。

    逐相邻集对(N,N+1)判：① N 结尾须悬置(cliffhanger)，否则 N+1 无张力可冷开场；
    ② N+1 须真冷开场(前2拍有钩、非慢旁白回顾)。保守——只在明确"收得太干净"或"开篇慢热"时报 warn。
    返回 (eps, states, findings, chain_ok_rate)；chain_ok_rate 供 narrative_kpi 消费（report-only）。"""
    sdir = Path(root) / "脚本"
    eps = sorted([d.name for d in sdir.glob("第*集") if (d / "voiceover.txt").exists()],
                 key=lambda n: int(re.search(r"\d+", n).group()))
    states = {ep: _episode_open_close(root, ep) for ep in eps}
    findings = []
    ok = total = 0
    for a, b in zip(eps, eps[1:]):
        sa, sb = states.get(a), states.get(b)
        if not sa or not sb:
            continue
        total += 1
        if not sa["ends_cliff"]:
            findings.append(("warn", "p2_resolved_ending",
                             f"{a}结尾收得太干净（无 cliffhanger），{b}难以 0-3s 冷开场——把{a}切在悬念断点（危机悬置/真相半露/反转预告）"))
        elif not sb["opens_cold"]:
            findings.append(("warn", "p2_slow_next_open",
                             f"{b}开篇慢热/未接住{a}的钩子做冷开场——{b}前 2 拍给倒叙钩/危机直入，别用旁白慢回顾起"))
        else:
            # 两端都对（上集悬置 + 下集冷开场），再查「接的是不是同一根线」：实体零重合=钩子接错根。
            link = hook_link(parse_voiceover(sdir / a / "voiceover.txt"),
                             parse_voiceover(sdir / b / "voiceover.txt"))
            if link["has_signal"] and not link["linked"] and not explicit_hook_bridge(root, b, a):
                findings.append(("warn", "cross_ep_hook_break",
                                 f"{a}集尾钩 [{'/'.join(link['prev_end_entities'][:4])}] 与 {b}冷开场 "
                                 f"[{'/'.join(link['open_entities'][:4])}] 实体零重合——下集没接住上集那根钩子，因果断线；"
                                 "若是有意切线/延迟回收，在 storyboard.json 写 hook_bridge"))
            else:
                ok += 1
    rate = round(ok / total, 3) if total else None
    return eps, states, findings, rate


# ── 看点高潮位复核（阶段2·北极星看点④的时间轴落点·需真实 镜头时长.json） ──
# boundary_audit 在拆集层只能用词面/集尾强度初筛奇观放置；到了阶段2 有了每镜真实秒，
# 才能量"本集最强看点落在时间轴哪个百分位"——治集内『虎头蛇尾』(看点堆前段、高潮后长尾塌陷)
# 与『平庸无看点集』(北极星：每集须一个核心看点)。无 镜头时长.json 的集静默跳过(拆集层不激活)。
HIGHLIGHT_EARLY_POS = 0.45    # 最强看点早于总时长此比例 + 之后无钩 → 集内前重后轻
HIGHLIGHT_LATE_POS = 0.92     # 看点全部堆到极尾(无铺垫憋放) → 提示确认是否缺爬升


def _highlight_beats(beats):
    """看点拍 = 💥爽点 ∪ 高能峰值情绪 ∪ (信息∩情绪回报叠加)。返回 shot 号列表。"""
    out = []
    for b in beats:
        is_payoff = HOOK_PAYOFF in b["hooks"]
        is_peak = any(p in b["emotion"] for p in PEAK_EMO)
        is_info_emo = bool(INFO_RE.search(b["text"])) and bool(EMO_RE.search(b["text"]))
        if is_payoff or is_peak or is_info_emo:
            out.append(b["shot"])
    return out


def highlight_climax_profile(root):
    """看点高潮位复核（report-only·阶段2）。

    只在同时有 voiceover + 镜头时长.json 的集上算（拆集层无真实秒 → 静默，
    到 storyboard 定稿后才激活，与 boundary_audit 的词面奇观初筛分层互补）。
    每集计算最强看点(最晚的看点拍)的归一化时间位置 climax_pos，flag：
      · no_highlight_beat —— 有时长却零看点拍（北极星：每集须一个核心看点）。
      · highlight_too_early —— climax<45% 且其后无任何钩子撑张力（集内虎头蛇尾）。
    返回 (rows, findings)。"""
    sdir = Path(root) / "脚本"
    eps = sorted([d.name for d in sdir.glob("第*集") if (d / "voiceover.txt").exists()],
                 key=lambda n: int(re.search(r"\d+", n).group()))
    rows, findings = [], []
    for ep in eps:
        beats = parse_voiceover(sdir / ep / "voiceover.txt")
        shot_secs = load_shot_seconds(root, ep)
        if not beats or not shot_secs:
            continue  # 无真实时长不判（阶段2 前静默）
        starts, total = cumulative_starts(shot_secs)
        if total <= 0:
            continue
        hl_shots = _highlight_beats(beats)
        if not hl_shots:
            rows.append({"episode": ep, "total_sec": round(total, 1), "has_highlight": False})
            findings.append(("warn", "no_highlight_beat",
                f"{ep}：全集 {total:.0f}s 无可识别看点拍（爽点💥/峰值情绪/信息+情绪叠加）——"
                "北极星要求每集一个核心看点（爽点·反转·情绪峰·视觉奇观），补一个或并入相邻集"))
            continue
        hl_starts = sorted(starts.get(s, 0.0) for s in hl_shots)
        climax = hl_starts[-1]
        climax_pos = climax / total
        tail_has_hook = any(_inferred_hook(b) for b in beats if starts.get(b["shot"], 0.0) > climax + 0.01)
        row = {"episode": ep, "total_sec": round(total, 1), "has_highlight": True,
               "n_highlight": len(hl_shots), "climax_pos": round(climax_pos, 3),
               "first_highlight_pos": round(hl_starts[0] / total, 3), "tail_has_hook": tail_has_hook}
        rows.append(row)
        if climax_pos < HIGHLIGHT_EARLY_POS and not tail_has_hook:
            findings.append(("warn", "highlight_too_early",
                f"{ep}：最强看点落在 {climax_pos:.0%} 处（{climax:.0f}s/{total:.0f}s），其后再无钩子撑张力——"
                "集内'虎头蛇尾'：把看点/爽点后移到 ~60-85% 高潮位、爽点后留 1-2s 再集尾 cliffhanger（导演节奏 §四/§五）"))
        elif climax_pos > HIGHLIGHT_LATE_POS and len(hl_shots) == 1:
            findings.append(("info", "highlight_no_buildup",
                f"{ep}：唯一看点压在 {climax_pos:.0%} 极尾、前段无看点铺垫——确认是否缺'憋'的爬升（憋放距离不足易突兀）"))
    return rows, findings


def print_findings(title, findings):
    print(f"## {title}")
    order = {"must": 0, "warn": 1, "info": 2}
    icon = {"must": "⛔", "warn": "⚠️", "info": "ℹ️"}
    if not findings:
        print("- ✅ 集内节拍体检通过")
        return
    for sev, code, msg in sorted(findings, key=lambda f: order[f[0]]):
        print(f"- {icon[sev]} [{code}] {msg}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        print("用法: beat_audit.py <作品根> 第N集 [--strict] [--json]  |  <作品根> --series")
        sys.exit(2)
    root = args[0]

    if "--series" in flags:
        eps, dups = audit_series(root)
        _eps2, _states, chain_findings, chain_rate = cold_open_chain(root)
        _eps3, risk_ranked, risk_findings = narrative_risk_profile(root)
        hl_rows, hl_findings = highlight_climax_profile(root)
        if "--json" in flags:
            print(json.dumps({"episodes": eps, "duplicates": dups,
                              "cold_open_chain_rate": chain_rate,
                              "cold_open_chain_findings": [{"severity": s, "code": c, "msg": m}
                                                          for s, c, m in chain_findings],
                              "narrative_risk_profile": risk_ranked,
                              "narrative_audit_priority": [{"severity": s, "code": c, "msg": m}
                                                           for s, c, m in risk_findings],
                              "highlight_climax_profile": hl_rows,
                              "highlight_climax_findings": [{"severity": s, "code": c, "msg": m}
                                                            for s, c, m in hl_findings]},
                             ensure_ascii=False, indent=2))
            return
        print(f"## 跨集套路同质化（Gap4·{len(eps)} 集）")
        if not dups:
            print("- ✅ 未发现高度重复的桥段指纹")
        else:
            for ea, eb, j in dups:
                print(f"- ⚠️ {ea} ↔ {eb} 桥段指纹重合 {j}（套路雷同→观众疲劳，换爽点类型/信息角度/情绪曲线）")
        print(f"\n## 跨集冷开场链（P2·切点让下集能 0-3s 冷开场·达成率 {chain_rate if chain_rate is not None else '—'}）")
        if not chain_findings:
            print("- ✅ 相邻集的「结尾悬置→下集冷开场」链路顺畅")
        else:
            for _s, c, m in chain_findings:
                print(f"- ⚠️ [{c}] {m}")
        print(f"\n## 叙事一致性审计优先级（G-S1·中段×高熵·ConStory·report-only·{len(risk_ranked)} 集）")
        if not risk_findings:
            print("- ℹ️ 集数太少或风险均匀，无优先建议（≥4 集才给）")
        else:
            for _s, c, m in risk_findings:
                print(f"- ℹ️ [{c}] {m}")
        scored = [r for r in hl_rows if r.get("has_highlight")]
        print(f"\n## 看点高潮位复核（北极星看点④·需真实镜头时长·{len(scored)}/{len(hl_rows)} 集有时长）")
        if not hl_rows:
            print("- ℹ️ 暂无任何集产出 镜头时长.json（阶段2 storyboard 定稿后激活），拆集层用 boundary_audit 词面初筛")
        elif not hl_findings:
            poss = "、".join(f"{r['episode']}={r['climax_pos']:.0%}" for r in scored[:8])
            print(f"- ✅ 各集看点高潮位健康（最强看点落点：{poss}{'…' if len(scored) > 8 else ''}）")
        else:
            order = {"must": 0, "warn": 1, "info": 2}
            icon = {"must": "⛔", "warn": "⚠️", "info": "ℹ️"}
            for s, c, m in sorted(hl_findings, key=lambda f: order[f[0]]):
                print(f"- {icon[s]} [{c}] {m}")
        return

    if len(args) < 2:
        print("用法: beat_audit.py <作品根> 第N集 [--strict] [--json]")
        sys.exit(2)
    ep = args[1] if args[1].startswith("第") else f"第{args[1]}集"
    findings, stats = audit_episode(root, ep)
    if "--json" in flags:
        print(json.dumps({"episode": ep, "stats": stats,
                          "findings": [{"severity": s, "code": c, "msg": m} for s, c, m in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print(f"# 集内留存节拍体检 — {ep}")
        print(f"镜数 {stats.get('shots', 0)}　钩子 {stats.get('hooks', 0)}　爽点 {stats.get('payoffs', 0)}　"
              f"反转 {'有' if stats.get('has_reversal') else '无'}　集尾钩 {'有' if stats.get('has_ending_hook') else '无'}　"
              f"真实时长 {'有' if stats.get('has_timings') else '无(按镜数估)'}")
        print()
        print_findings("节拍 findings（report-only·导演节奏建议）", findings)
        print("> 集间留存骨架见 references/追更骨架.md；时长一致性闸门仍是 validate_timings.py（本检不替代它）。")

    must_n = sum(1 for s, _, _ in findings if s == "must")
    warn_n = sum(1 for s, _, _ in findings if s == "warn")
    if "--strict" in flags and (must_n or warn_n):
        sys.exit(1)
    sys.exit(0 if not must_n else 1)


if __name__ == "__main__":
    main()
