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
try:
    from n2d_settings import get_setting  # noqa: E402
except Exception:  # pragma: no cover - beat_audit must remain usable in partial checkouts
    get_setting = None

LINE_RE = re.compile(r"^\[镜头(\d+)·([^·\]]+)·([^·\]]+?)(?:·([^·\]]+))?\]\s*(.*)$")
HOOK_NORMAL = "⚡"
HOOK_PAYOFF = "💥"
HOOK_ENDING = "🪝"

# 信息回报：揭示信息增量（真相/身世/系统/线索/数值/命名）。
INFO_RE = re.compile(r"(原来|竟是|竟然|其实|真相|身世|来历|名字|是.{0,6}的人|系统|面板|提示|【|"
                     r"等级|经验|线索|证据|因为|原来是|揭|暴露|发现|秘密|内幕|得到|获得|"
                     r"血脉|权限|能力|规则|反噬|代价|伪人皮|潜行)")
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

# 语速标注归一（D2·此前 (语速) 只解析不消费）。可选字段·快/慢/常速及别名。
SLOW_SPEED = ("慢", "缓", "放慢", "慢速")
FAST_SPEED = ("快", "急", "加快", "快速", "提速")
SPEED_MIN_ANNOTATED = 6   # 判"全程同速"所需最少标注样本（不足→信号不够·跳过，绝不臆造）

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

HOOK_GAP_SEC = 20.0   # 中段钩子间隔上限·国内默认（导演节奏 §二：每 15-20s 一个钩子）
DEFAULT_OVERSEAS_HOOK_GAP_SEC = 10.0  # G2·海外档：ReelShort/TikTok 出海素材更碎更狠（每~10s 一反转）
HOOK_GAP_SHOTS = 4    # 无真实时长时：相邻钩子最多隔几镜
LINK_WINDOW = 3       # 集尾钩 / 下集冷开场 的窗口拍数（取首/尾各 N 拍算实体重合）
# G1·开场拉力地板：开场只「有钩」不够，要够深（conflict/suspense/reversal 至少一条强层）。
# 2026 Sensor Tower：下一集解锁率与本集**开场钩子强度**相关性高于集尾悬念——开场是最高杠杆留存信号。
DEFAULT_COLD_OPEN_PULL_FLOOR = 0.3
# 开场拉力四层正则（与 cold_open_quality_score 共用·提到模块级，G1 逐集与 --series 同源单一真值）。
COLD_OPEN_CONFLICT_RE = re.compile(r"(冲突|矛盾|对抗|危机|危险|威胁|追杀|逃|战|敌|恨|怒|杀|死|仇|争|斗|围审|审问|逼问|压迫|羞辱|嘲笑|围住|受审|俯视)")
COLD_OPEN_SUSPENSE_RE = re.compile(r"(谁|什么|为什么|怎么|哪里|何时|秘密|真相|隐瞒|神秘|未知|谜|疑|奇怪|不对劲)")
COLD_OPEN_INFO_RE = re.compile(r"(发现|揭露|原来|其实|真相|证据|线索|秘密|第一次|首次|竟然|没想到)")

VISUAL_HOOK_RE = re.compile(r"(画面|视觉|特写|近景|大特写|冲突|动作|打斗|掌掴|血|脸|表情|追|逃|刀|剑|火|爆|"
                            r"系统面板|光幕|标题卡|字幕|烧屏|大字|caption|title|text|cold open|冷开场|倒叙)")
PROMISE_DUE_KEYS = ("payoff_due", "payoff_episode", "payoff_ep", "payoff_clip", "payoff_at",
                    "delayed_payoff_ep", "due_episode", "due_clip")
# GAP-2：首屏钩子内容字段从「只认 visual_conflict」泛化为 `visual_hook`——导演节奏 §二有五类钩
# （悬念/欲望/反差/信息/危机），2026 市场更在反套路、去掉"冲突shock开场"独尊。硬门只要求"有一个
# 静音可读的视觉钩"，不强迫每个开场都填"冲突"。`visual_conflict` 保留为向后兼容别名（老项目不报错）。
FIRST_SCREEN_REQUIRED_FIELDS = {
    "visual_hook": ("visual_hook", "visual_conflict"),
    "content_proposition": ("content_proposition", "content_promise"),
    "onscreen_text": ("onscreen_text",),
    "muted_safe_proof": ("muted_safe_proof", "muted_readable", "muted_safe"),
    "expected_metric": ("expected_metric",),
}
# 钩子类型分类（导演节奏 §二的五类 + 情绪冲突；中英双写）。可选字段 `hook_type`：写了就校验是否在表内，
# 不写不罚——目的是让"悬念/欲望/情绪型冷开场"光明正大成立，而非被迫硬填一个"conflict"。
FIRST_SCREEN_HOOK_TYPES = {
    "悬念", "欲望", "反差", "信息", "信息增量", "危机", "情绪", "情绪冲突", "冲突",
    "suspense", "desire", "contrast", "info", "information", "crisis", "emotion", "conflict",
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
                "caption", "title", "muted_safe_proof", "content_promise", "muted_readable",
                "proof", "proposition", "description")
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


def _retention_benchmark(root):
    if load_benchmark is None:
        return {}
    try:
        data = load_benchmark(root)
    except Exception:
        return {}
    rb = data.get("retention_benchmarks") if isinstance(data, dict) else None
    return rb if isinstance(rb, dict) else {}


def _first_screen_thresholds(root):
    rb = _retention_benchmark(root)
    creative = rb.get("creative_attention") if isinstance(rb, dict) else {}
    proxy = rb.get("proxy_thresholds") if isinstance(rb, dict) else {}
    try:
        floor = float(proxy.get("retention_hook_floor"))
    except Exception:
        floor = DEFAULT_RETENTION_HOOK_FLOOR
    band = creative.get("caption_words_per_sec_band") if isinstance(creative, dict) else None
    if not (isinstance(band, list) and len(band) >= 2):
        band = DEFAULT_CAPTION_WORDS_PER_SEC_BAND
    try:
        caption_band = (float(band[0]), float(band[1]))
    except Exception:
        caption_band = DEFAULT_CAPTION_WORDS_PER_SEC_BAND
    first_6s_required = bool(creative.get("first_6s_hook_required", DEFAULT_FIRST_6S_HOOK_REQUIRED)) if isinstance(creative, dict) else DEFAULT_FIRST_6S_HOOK_REQUIRED
    return {
        "retention_hook_floor": floor,
        "caption_words_per_sec_band": caption_band,
        "first_6s_hook_required": first_6s_required,
    }


def _as_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _proxy_thresholds(root):
    rb = _retention_benchmark(root)
    proxy = rb.get("proxy_thresholds") if isinstance(rb, dict) else None
    return proxy if isinstance(proxy, dict) else {}


# 海外档信号词：取自 `发行地区` 枚举（北美/东南亚/全球）+ `变现模式=海外` + 平台名。读的是 _设置.md 的
# canonical 选择点值（非菜单文案），符合 choice-point 适配器原则——不在此 if 扫菜单文本做后端分支。
_OVERSEAS_REGION_TOKENS = ("北美", "东南亚", "全球", "海外", "overseas", "tiktok", "reelshort", "海外短剧")


def pacing_region(root):
    """从 _设置.md 的 变现模式/发行地区 推断节奏档：'overseas' vs 'domestic'。

    海外（ReelShort/TikTok）出海素材节奏更碎更狠（每~10s 一反转）；国内保持~20s（导演节奏 §二）。
    任何读取失败 → 'domestic'（保守：不因缺设置而误收紧、误拦国内项目）。"""
    if get_setting is None:
        return "domestic"
    try:
        monet = (get_setting(root, "变现模式", "") or "").strip()
        region = (get_setting(root, "发行地区", "") or "").strip()
    except Exception:
        return "domestic"
    if "海外" in monet:
        return "overseas"
    if any(tok in region for tok in _OVERSEAS_REGION_TOKENS):
        return "overseas"
    return "domestic"


def effective_hook_gap_sec(root):
    """G2·有效中段钩子间隔上限：benchmark proxy_thresholds.hook_gap_sec（默认 20s）+ 区域档覆盖。

    海外档优先取 proxy_thresholds.overseas_hook_gap_sec（默认 10s）。阈值单一真值在
    industry_benchmark.json，可被项目 生产数据/industry_benchmark.json 覆盖（走 v2 provenance schema）。"""
    proxy = _proxy_thresholds(root)
    base = _as_float(proxy.get("hook_gap_sec"), HOOK_GAP_SEC)
    if pacing_region(root) == "overseas":
        return _as_float(proxy.get("overseas_hook_gap_sec"), DEFAULT_OVERSEAS_HOOK_GAP_SEC)
    return base


def cold_open_pull_layers(head_beats):
    """G1·开场拉力四层评分（纯函数·可测）：conflict/suspense/reversal/info 加权 → 0-1 分 + 各层命中。

    与 cold_open_quality_score 共用同一套权重/正则，确保「逐集 audit_episode」与「--series 链」对开场强度
    口径一致（单一真值，避免两处漂离）。"""
    head_text = " ".join(b["text"] for b in head_beats)
    conflict_layer = 1.0 if COLD_OPEN_CONFLICT_RE.search(head_text) else 0.0
    suspense_layer = 1.0 if COLD_OPEN_SUSPENSE_RE.search(head_text) else 0.0
    reversal_layer = 1.0 if any(REVERSAL_RE.search(b["text"]) for b in head_beats) else 0.0
    info_layer = 1.0 if COLD_OPEN_INFO_RE.search(head_text) else 0.0
    score = (conflict_layer * 0.3 + suspense_layer * 0.3 +
             reversal_layer * 0.25 + info_layer * 0.15)
    layers = {"conflict": conflict_layer, "suspense": suspense_layer,
              "reversal": reversal_layer, "info": info_layer}
    return round(score, 3), layers


def _cold_open_pull_floor(root):
    return _as_float(_proxy_thresholds(root).get("cold_open_pull_floor"), DEFAULT_COLD_OPEN_PULL_FLOOR)


def audit_cold_open_pull_strength(root, ep, beats):
    """G1·开场拉力（独立留存杠杆）。

    Sensor Tower 2026：第2集解锁率 ≈ 上一集**开场钩子强度**，相关性高于集尾悬念。此前 n2d 把开场强度
    只当 --series 连续性（接没接住上集的钩）来查，且 cold_open 检查只问「有没有钩」(二值)；本检查把「开场够不够深」
    提为逐集留存信号——开场只有单薄 info 层 / 零强层 = 拉力不足，正式出图前补强（改开场比改成片便宜）。

    score < floor → warn（开场缺 conflict/suspense/reversal 任一强层）；nonzero 但仍偏薄 → info 提示加深。
    报告产物：voiceover.txt 开场窗（前2拍，与 cold_open/cold_open_quality_score 同窗）。"""
    head = beats[:2]
    if not head:
        return []
    score, layers = cold_open_pull_layers(head)
    floor = _cold_open_pull_floor(root)
    present = [k for k, v in layers.items() if v]
    if score < floor:
        shown = "/".join(present) if present else "无强层"
        return [("warn", "cold_open_pull_weak",
                 f"开场拉力 {score:.2f} < 地板 {floor:.2f}（命中层：{shown}）——开场只『有钩』不够深："
                 "2026 数据显示下一集解锁率与本集**开场钩子强度**相关性高于集尾悬念，"
                 "开场补到至少一条强层（直给冲突/抛悬念/反转直入），别把最强信息留到中段")]
    if score < 0.6:
        return [("info", "cold_open_pull_thin",
                 f"开场拉力 {score:.2f}（命中层：{'/'.join(present)}）达地板但偏单薄——"
                 "叠加第二条强层（冲突+悬念/反转）可进一步拉高下一集解锁率，留存最高杠杆在开场")]
    return []


def _parse_expected_metric(value):
    if not isinstance(value, dict):
        return None, None, "expected_metric 必须是 {primary,target} 对象"
    primary = str(value.get("primary") or value.get("metric") or "").strip()
    target_raw = value.get("target")
    try:
        target = float(target_raw)
    except (TypeError, ValueError):
        return primary, None, "expected_metric.target 必须是 0-1 数值"
    return primary, target, ""


def _caption_units(text: str) -> int:
    text = str(text or "")
    cjk = len(CJK_RE.findall(text))
    latin = len(LATIN_WORD_RE.findall(text))
    return cjk + latin


def _caption_duration(contract) -> float:
    if not isinstance(contract, dict):
        return DEFAULT_FIRST_SCREEN_WINDOW_SEC
    for key in ("onscreen_text_duration_sec", "caption_duration_sec", "window_sec", "duration_sec"):
        try:
            value = float(contract.get(key))
            if value > 0:
                return value
        except (TypeError, ValueError):
            continue
    return DEFAULT_FIRST_SCREEN_WINDOW_SEC


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
        readable = contract.get("muted_readable")
        if readable is True:
            return True
        if isinstance(readable, str) and readable.strip().lower() in {"true", "yes", "y", "1", "是", "已证明", "安全"}:
            return True
        proof_text = " ".join(str(contract.get(k) or "") for k in ("muted_safe_proof", "visual_hook", "visual_conflict", "onscreen_text"))
        if _nonempty(contract.get("muted_safe_proof")) and VISUAL_HOOK_RE.search(proof_text):
            return True
    return bool(VISUAL_HOOK_RE.search(_contract_text(contract)))


def _storyboard_first_6s_visual_hook(sb) -> bool:
    """A cold open may be carried by image/blocking rather than spoken text."""
    if not isinstance(sb, dict):
        return False
    contract_texts = []
    for contract in _candidate_first_screen_contracts(sb):
        contract_texts.append(_contract_text(contract))
    first = _first_clip(sb)
    if not isinstance(first, dict):
        return False
    first_blob = " ".join(str(first.get(key) or "") for key in ("label", "pacing_role", "dramatic_function", "audience_effect", "description"))
    blob = " ".join([first_blob, *contract_texts])
    return bool(
        first_blob.strip()
        and (
            COLD_OPEN_CONFLICT_RE.search(first_blob)
            or COLD_OPEN_SUSPENSE_RE.search(first_blob)
            or COLD_OPEN_INFO_RE.search(first_blob)
            or HOOK_CONTENT_RE.search(first_blob)
            or (VISUAL_HOOK_RE.search(first_blob) and (COLD_OPEN_SUSPENSE_RE.search(blob) or COLD_OPEN_CONFLICT_RE.search(blob)))
        )
    )


def audit_first_screen_contract(root, ep, beats):
    """0-3s 首屏留存契约：必须证明关声也能看懂钩子。"""
    sb = load_storyboard(root, ep)
    if sb is None:
        return []
    findings = []
    thresholds = _first_screen_thresholds(root)
    contracts = _candidate_first_screen_contracts(sb)
    if not contracts:
        findings.append(("must", "missing_first_3s_visual_hook",
                         "storyboard.json 缺 first_3s_visual_hook：正式出图前必须写结构化首屏契约 visual_hook(或兼容 visual_conflict)/content_proposition/onscreen_text/muted_safe_proof/expected_metric，不能只靠旁白抓人"))
        return findings
    missing_sets = [_first_screen_schema_missing(c) for c in contracts]
    if not any(not missing for missing in missing_sets):
        best_missing = min(missing_sets, key=len)
        findings.append(("must", "incomplete_first_3s_visual_hook",
                         "first_3s_visual_hook 不是严格结构：缺 %s；正式出图前必须把首屏视觉钩(visual_hook，冲突/悬念/欲望/反差/信息/危机皆可)、内容承诺、烧屏文字、静音证明和目标指标写成可审计字段" %
                         ",".join(best_missing)))
    # GAP-2：可选 hook_type 校验（写了才查；不写不罚）——让悬念/欲望/情绪型开场名正言顺，不被迫填"冲突"。
    for contract in contracts:
        if not isinstance(contract, dict):
            continue
        ht = str(contract.get("hook_type") or "").strip()
        if ht and not all(part.strip() in FIRST_SCREEN_HOOK_TYPES for part in re.split(r"[、,/|]+", ht) if part.strip()):
            findings.append(("warn", "first_3s_unknown_hook_type",
                             f"first_3s_visual_hook.hook_type=『{ht}』不在钩子类型表（悬念/欲望/反差/信息/危机/情绪冲突）：确认是有意自定义还是误填；hook_type 仅约束分类、不要求一定是冲突型"))
            break
    valid_metric = False
    metric_errors = []
    floor = float(thresholds["retention_hook_floor"])
    for contract in contracts:
        if not isinstance(contract, dict):
            metric_errors.append("expected_metric 缺结构化对象")
            continue
        primary, target, error = _parse_expected_metric(_contract_field(contract, "expected_metric"))
        if error:
            metric_errors.append(error)
            continue
        if primary not in ALLOWED_FIRST_SCREEN_METRICS:
            metric_errors.append(f"expected_metric.primary={primary or 'missing'} 不在 retention_3s/retention_6s")
            continue
        if target is None or target < floor:
            metric_errors.append(f"expected_metric.target={target if target is not None else 'missing'} 低于留存钩子目标线 {floor:.0%}")
            continue
        valid_metric = True
        break
    if not valid_metric:
        detail = metric_errors[0] if metric_errors else "expected_metric 无法校验"
        findings.append(("must", "invalid_first_3s_expected_metric",
                         f"first_3s_visual_hook 目标指标不可审计：{detail}；必须写 primary=retention_3s/retention_6s 且 target ≥ 当前 retention_hook_floor"))
    if not any(_contract_muted_safe(c) for c in contracts):
        findings.append(("must", "first_3s_not_muted_safe",
                         "首屏钩子没有证明静音可读：补 visual_hook / onscreen_text_hook / muted_safe_proof，确保关声也能理解危机或悬念"))
    caption_min, caption_max = thresholds["caption_words_per_sec_band"]
    for contract in contracts:
        text = _contract_field(contract, "onscreen_text")
        if not _nonempty(text):
            continue
        units = _caption_units(str(text))
        duration = _caption_duration(contract)
        density = units / duration if duration > 0 else 0.0
        if density > caption_max:
            findings.append(("must", "first_3s_caption_too_dense",
                             f"首屏烧屏文字过载：{units} units/{duration:.1f}s = {density:.1f}/s，高于基准 {caption_min:g}-{caption_max:g}/s；短剧首屏文字要可读"))
        elif density < caption_min:
            findings.append(("warn", "first_3s_caption_too_sparse",
                             f"首屏烧屏文字偏少：{units} units/{duration:.1f}s = {density:.1f}/s，低于参考 {caption_min:g}-{caption_max:g}/s；确认画面钩足够强"))
        break
    head = beats[:2]
    if head and not any(_inferred_hook(b) for b in head) and not _storyboard_first_6s_visual_hook(sb):
        severity = "must" if thresholds["first_6s_hook_required"] else "warn"
        findings.append((severity, "missing_first_6s_beat_hook",
                         "storyboard 写了首屏契约，但 voiceover 前2拍/约前6秒没有钩子信号：让台词/画面节拍与 first_3s_visual_hook 对齐"))
    else:
        # 黄金3秒时间量化档：宣称的是 0-3s，上面的节拍启发式只能验到「约前6秒」。
        # 有真实 镜头时长.json 时把窗口收紧到 3.0s 复核；无时长数据维持原口径不加噪。
        shot_secs = load_shot_seconds(root, ep)
        if shot_secs and beats:
            starts, _total = cumulative_starts(shot_secs)
            hook_times = sorted(starts[b["shot"]] for b in beats
                                if _inferred_hook(b) and b["shot"] in starts)
            if hook_times and hook_times[0] > 3.0:
                findings.append(("warn", "first_hook_after_golden_3s",
                                 f"首个钩子节拍落在 {hook_times[0]:.1f}s（超出 0-3s 黄金开场窗）：前6秒有钩，但 0-3s 只能靠 first_3s_visual_hook 的画面钩/烧屏文字自证，确认冷开场画面扛得住前 3 秒"))
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


HOOK_TYPE_MONOTONE_RUN = 3  # 连续同类型钩子 ≥ 此 → 单调（钩子类型该像波浪轮换）


def _hook_type_token(promise):
    """钩子类型 token：优先显式 hook_type，退回 promise_type；空→''（断开 run，不计单调）。"""
    for k in ("hook_type", "promise_type"):
        v = str(promise.get(k) or "").strip().lower()
        if v:
            return v
    return ""


def audit_hook_type_rotation(root, ep, beats):
    """GAP-4：集内相邻钩子类型轮换——同一 hook_type/promise_type 连续 ≥N 个 = 单调，观众疲劳。
    advisory(warn)，不阻断；ledger 不足或类型缺失优雅跳过（绝不臆造）。"""
    sb = load_storyboard(root, ep)
    if sb is None:
        return []
    seq = [_hook_type_token(p) for p in _retention_ledger(sb)]
    findings = []
    run_type, run_len = None, 0
    worst = None
    for token in seq:
        if token and token == run_type:
            run_len += 1
        else:
            run_type, run_len = token, (1 if token else 0)
        if token and run_len >= HOOK_TYPE_MONOTONE_RUN and (worst is None or run_len > worst[1]):
            worst = (run_type, run_len)
    if worst:
        findings.append(("warn", "monotone_hook_type",
                         f"retention_promise_ledger 连续 {worst[1]} 个钩子同类型『{worst[0]}』：钩子类型要像波浪轮换"
                         "（悬念/欲望/反差/信息/危机交替），同型连甩=观众疲劳——换一两个钩的角度或类型"))
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


def _norm_speed(s: str) -> str:
    """语速文本 → 'slow'/'fast'/'normal'/''(未标)。纯函数·可测。"""
    s = (s or "").strip()
    if not s:
        return ""
    if any(w in s for w in SLOW_SPEED):
        return "slow"
    if any(w in s for w in FAST_SPEED):
        return "fast"
    return "normal"


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
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        out = {}
        for k, v in data.items():
            m = re.search(r"镜头\s*(\d+)", str(k))
            if not m:
                m = re.search(r"(?:^|[_\s-])shot[_\s-]*0*(\d+)", str(k), re.I)
            if m:
                out[int(m.group(1))] = float(v)
        if out:
            return out
    sb_path = Path(root) / "脚本" / ep / "storyboard.json"
    if sb_path.exists():
        try:
            sb = json.loads(sb_path.read_text(encoding="utf-8"))
        except Exception:
            sb = None
        out = {}
        if isinstance(sb, dict) and isinstance(sb.get("clips"), list):
            for clip in sb["clips"]:
                if not isinstance(clip, dict):
                    continue
                try:
                    dur = float(clip.get("duration"))
                except (TypeError, ValueError):
                    continue
                indices = clip.get("voiceover_indices") or clip.get("source_shots") or clip.get("shot_indices")
                if not isinstance(indices, list) or not indices:
                    continue
                nums = []
                for item in indices:
                    if isinstance(item, bool):
                        continue
                    if isinstance(item, int):
                        nums.append(item)
                        continue
                    m = re.search(r"\d+", str(item))
                    if m:
                        nums.append(int(m.group()))
                nums = [n for n in nums if n > 0]
                if not nums:
                    continue
                share = dur / len(nums)
                for n in nums:
                    out[n] = out.get(n, 0.0) + share
        if out:
            return {k: round(v, 3) for k, v in out.items()}
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    out = {}
    for k, v in data.items():
        m = re.search(r"镜头\s*(\d+)", str(k))
        if not m:
            m = re.search(r"(?:^|[_\s-])shot[_\s-]*0*(\d+)", str(k), re.I)
        if not m:
            m = re.search(r"(?:^|[_\s-])clip[_\s-]*0*(\d+)", str(k), re.I)
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

    # ①e 钩子类型轮换（GAP-4）：集内同型钩子连甩 = 观众疲劳，advisory 提示换角度。
    findings.extend(audit_hook_type_rotation(root, ep, beats))

    # ①f 开场拉力（G1·最高杠杆留存信号）：开场只「有钩」不够，要够深——下一集解锁率与开场强度相关性 > 集尾悬念。
    findings.extend(audit_cold_open_pull_strength(root, ep, beats))

    # ② 钩子间隔（导演节奏 §二）·用 marker∪content 钩子算间隔（漏标记不再误判 hook_gap）
    # G2·间隔上限按区域档取（国内~20s / 海外~10s），单一真值在 industry_benchmark.json。
    gap_sec = effective_hook_gap_sec(root)
    if shot_secs:
        starts, total = cumulative_starts(shot_secs)
        hook_times = sorted(starts.get(b["shot"], 0.0) for b in effective_hooked)
        prev = 0.0
        for t in hook_times:
            if t - prev > gap_sec:
                findings.append(("warn", "hook_gap",
                                 f"{prev:.0f}s–{t:.0f}s 间隔 {t-prev:.0f}s 无钩子（>{gap_sec:.0f}s）：中段易划走，补悬念/信息/反差/危机"))
            prev = t
        if total - prev > gap_sec and hook_times:
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

    # ⑥b Clip 物理切镜密度（2026-07 实跑痛点回修·granularity 修正）：本审计的"镜"是台词行粒度
    #    （EP1 实测 14 行/分钟看似健康），但观众看到的切镜是 storyboard 的物理 Clip——EP1/EP2 实际
    #    只有 5.3-5.5 Clip/分钟且多为 10s+ 长镜，这才是"PPT 感"的镜头层来源。漫剧图生视频流的
    #    行业常态是 5-8 镜/分钟（真人短剧 12-24，载体不同勿混用），地板取 5（env 可调）：低于它
    #    = 比漫剧常态还慢，长镜必须靠镜内运动/多 sub-shot 撑住，否则回分镜拆镜。
    clip_density_floor = float(os.environ.get("N2D_CLIP_DENSITY_SLOW", "5.0"))
    sb_for_density = load_storyboard(root, ep)
    if isinstance(sb_for_density, dict):
        _clips = [c for c in (sb_for_density.get("clips") or []) if isinstance(c, dict)]
        _total = 0.0
        for c in _clips:
            try:
                _total += float(c.get("duration") or 0)
            except (TypeError, ValueError):
                pass
        if len(_clips) >= 4 and _total > 30:
            density = len(_clips) / (_total / 60.0)
            if density < clip_density_floor:
                findings.append(("warn", "clip_density_ppt_slow",
                                 f"物理切镜密度 {density:.1f} Clip/分钟（{len(_clips)} Clip / {_total:.0f}s）"
                                 f"低于漫剧地板 {clip_density_floor:g}/min——台词行密度再高，观众看到的仍是长镜堆叠"
                                 "（PPT 感镜头层来源）。拆长 Clip 成多物理镜，或确保每个长镜有真实镜内运动/景别推进"))

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

    # ⑨ 语速呼吸（D2·把此前只解析不消费的 (语速) 标注接进节奏审计·与 ⑥镜长/⑦情绪弧 三轴互补）。
    #    语速是可选标注：覆盖低→信号不足，按注释覆盖率优雅跳过、绝不臆造。全 info（软提示·不阻断 --strict）。
    speeds = [_norm_speed(b["speed"]) for b in beats]
    # A. 开场拖速：黄金3秒忌冗长铺垫——首2镜显式标 slow（与 ① cold_open 的"旁白+平缓"判据互补·不同源）。
    if any(s == "slow" for s in speeds[:2]):
        findings.append(("info", "slow_cold_open_speed",
                         "开场首镜标注慢语速：黄金3秒忌拖沓铺垫，开场提速或把慢拍后移（与冷开场情绪判据互补）"))
    # B. 全程同速：标注足够多却零快慢变化——节奏第三呼吸轴缺失（标注不足则跳过，不臆造）。
    annotated = [s for s in speeds if s]
    if len(annotated) >= SPEED_MIN_ANNOTATED and len(set(annotated)) == 1:
        findings.append(("info", "flat_speed",
                         f"已标语速 {len(annotated)}/{len(beats)} 镜均为同一档、无快慢变化："
                         "节奏第三呼吸轴——临近爽点提速碎切、铺垫/留白放缓，与镜长曲线/情绪弧一起做起伏"))

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


def cold_open_quality_score(root, ep):
    vpath = Path(root) / "脚本" / ep / "voiceover.txt"
    if not vpath.exists():
        return {"score": 0.0, "layers": {}, "depth": "unknown", "note": "voiceover.txt 不存在"}
    beats = parse_voiceover(vpath)
    if not beats:
        return {"score": 0.0, "layers": {}, "depth": "unknown", "note": "无节拍数据"}
    score, layers = cold_open_pull_layers(beats[:2])
    if score >= 0.6:
        depth = "deep"
    elif score >= 0.3:
        depth = "moderate"
    else:
        depth = "shallow"
    return {"score": score, "layers": layers, "depth": depth}


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
        co_quality_rows = []
        co_quality_findings = []
        for ep in _eps2:
            q = cold_open_quality_score(root, ep)
            co_quality_rows.append({"episode": ep, **q})
            if q["depth"] == "shallow" and q["score"] < 0.15:
                co_quality_findings.append(("warn", "shallow_cold_open",
                                             f"{ep} 冷开场质量极浅（score={q['score']:.2f}，depth={q['depth']}）——"
                                             "前 2 拍缺冲突/悬念/反转信号，观众 3s 内无理由留步；补至少 2 层钩子信号"))
            elif q["depth"] == "shallow":
                co_quality_findings.append(("info", "weak_cold_open",
                                             f"{ep} 冷开场偏浅（score={q['score']:.2f}，depth={q['depth']}）——"
                                             "建议补冲突/悬念/反转中的至少一层"))
        _eps3, risk_ranked, risk_findings = narrative_risk_profile(root)
        hl_rows, hl_findings = highlight_climax_profile(root)
        if "--json" in flags:
            print(json.dumps({"episodes": eps, "duplicates": dups,
                              "cold_open_chain_rate": chain_rate,
                              "cold_open_chain_findings": [{"severity": s, "code": c, "msg": m}
                                                           for s, c, m in chain_findings],
                              "cold_open_quality_profile": co_quality_rows,
                              "cold_open_quality_findings": [{"severity": s, "code": c, "msg": m}
                                                             for s, c, m in co_quality_findings],
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
        print(f"\n## 冷开场质量深度（G2·{len(co_quality_rows)} 集）")
        if not co_quality_findings:
            scored_q = [r for r in co_quality_rows if r.get("depth") != "unknown"]
            if scored_q:
                avg_score = sum(r["score"] for r in scored_q) / len(scored_q)
                print(f"- ✅ 各集冷开场质量深度健康（平均 score={avg_score:.2f}）")
            else:
                print("- ℹ️ 无可用冷开场数据")
        else:
            order = {"must": 0, "warn": 1, "info": 2}
            icon = {"must": "⛔", "warn": "⚠️", "info": "ℹ️"}
            for s, c, m in sorted(co_quality_findings, key=lambda f: order[f[0]]):
                print(f"- {icon[s]} [{c}] {m}")
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
    if "--write" in flags:
        # 落盘（2026-07 实跑痛点回修）：此前节拍/密度结论只打印——EP1 密度 5.5 镜/分钟
        # 触发"疑节奏塌"却无档案可查、score/update 无从消费。写 生产数据/beat_audit_<集>.json
        # 供审计追溯与 n2d-update 新鲜度比对；不改判定口径。
        out_dir = Path(root) / "生产数据"
        out_dir.mkdir(parents=True, exist_ok=True)
        import datetime as _dt
        (out_dir / f"beat_audit_{ep}.json").write_text(json.dumps({
            "kind": "n2d_beat_audit", "version": 1, "episode": ep,
            "generated_at": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
            "stats": stats,
            "findings": [{"severity": s, "code": c, "msg": m} for s, c, m in findings],
        }, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
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
