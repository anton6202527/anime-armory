#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广告**叙事结构 / 节拍工艺**机检（advisory·出图前·编剧/分镜轴）。

ad 线已有的编剧轴机检各管一段：shot_variety 管"画面不重复"、copy_quality 管"文案不注水"、
idea_payoff 管"创意承诺落镜"。没有任何东西查**传统广告片的结构纪律**——钩子是否落在黄金 3 秒、
品牌/产品是否 5 秒内进场（skippable 工艺：5s 内见品牌 VTR 显著更高）、CTA 是否存在且收在片尾、
电商片是否守"黄金3秒→痛点→方案→行动指令"四段式、花字停留时长是否够读（Clearcast supers 公式）、
6s bumper 是否只讲一件事、静音可看（85% 信息流静音播放）。本脚本把这些**可机检的传统手法**
做成广告线自己的结构机检，并附 Google ABCD（Attention/Branding/Connection/Direction）四轴数据。

**广告口径必须收着报**：
  ① **有意重复是常态**：CTA/endcard/slogan 板反复出现是提升 recall 的正当手法——只查"缺失/错位"，
     绝不报"重复"（对齐 shot_variety/copy_quality 的品牌重复豁免）。
  ② 单场景/慢节奏广告合法（品牌情绪片 ASL 可以很长）——ASL 出带、节奏后重只 info、不 warn。
  ③ 全部是**关键词初筛 confidence=low**：结构位齐不齐可机判，好不好看仍需人判。

全 advisory：`summary.block` 恒 0（Creative heuristics stay advisory，见 ad-craft/gate.py），
gate 只把它当 warn/info 抬进报告，永不硬挡付费。

用法：
    python3 beat_structure_audit.py <作品根> [--write] [--json] [--strict]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

VERSION = 1
KIND = "ad_beat_structure_audit"
REPORT_REL = os.path.join("生产数据", "ad_beat_structure_audit.json")
STORYBOARD_REL = os.path.join("脚本", "storyboard.json")
BRIEF_REL = os.path.join("需求", "brief.json")
CONCEPT_REL = os.path.join("创意", "concept.json")

# ── 阈值（内部启发式·env 可标定·confidence=low） ───────────────────────────────
# 黄金 3 秒：短视频/信息流工艺，第一个钩子节拍必须在 3s 内开始。
HOOK_WINDOW = float(os.environ.get("AD_BEAT_HOOK_WINDOW", "3.0"))
# skippable 工艺：品牌/产品 5s 内进场（YouTube ABCD：早品牌 VTR ↑~40%）。
BRAND_ENTRY_MAX = float(os.environ.get("AD_BEAT_BRAND_ENTRY_MAX", "5.0"))
# CTA 收尾窗口：行动指令应落在片尾最后 N 秒（或 endcard/末镜）。
CTA_TAIL = float(os.environ.get("AD_BEAT_CTA_TAIL", "5.0"))
# 广告 ASL 带（实测口径：商业广告 ~1.4–2.5s/镜 vs 电视节目 4.7–4.9s；放宽为 0.8–4.0 容纳品牌片）。
ASL_MIN = float(os.environ.get("AD_BEAT_ASL_MIN", "0.8"))
ASL_MAX = float(os.environ.get("AD_BEAT_ASL_MAX", "4.0"))
# 花字/supers 停留公式（Clearcast 口径：0.2s/词 + 2s 识别；中文按 0.15s/字折算）。
SUPERS_PER_CHAR = float(os.environ.get("AD_BEAT_SUPERS_PER_CHAR", "0.15"))
SUPERS_PER_WORD = float(os.environ.get("AD_BEAT_SUPERS_PER_WORD", "0.2"))
SUPERS_BASE = float(os.environ.get("AD_BEAT_SUPERS_BASE", "2.0"))
# 6s bumper：只讲一件事（Think with Google：6s 不是 30s 的压缩版）。
SIX_SEC_MAX = float(os.environ.get("AD_BEAT_SIX_SEC_MAX", "6.5"))
SIX_SEC_MAX_SHOTS = int(os.environ.get("AD_BEAT_SIX_SEC_MAX_SHOTS", "3"))
# 节奏前紧后松判定的最小镜数与容差（信息流留存工艺：开头密度最高）。
MIN_SHOTS_FOR_PACING = int(os.environ.get("AD_BEAT_MIN_SHOTS_PACING", "6"))
PACING_TOLERANCE = float(os.environ.get("AD_BEAT_PACING_TOLERANCE", "1.1"))
# 品牌脉冲露出（Teixeira et al. Marketing Science 2010：总曝光恒定时短脉冲多频次显著降低
# 回避，单次长时间压 logo 反而触发跳出；Kantar LINK branding 诊断同以"出现时点/时长"为口径）。
BRAND_GAP_MAX = float(os.environ.get("AD_BEAT_BRAND_GAP_MAX", "12.0"))    # 进场后最长无品牌区间
BRAND_RUN_MAX = float(os.environ.get("AD_BEAT_BRAND_RUN_MAX", "6.0"))     # 单段连续压品牌上限
BRAND_RATIO_EXEMPT = float(os.environ.get("AD_BEAT_BRAND_RATIO_EXEMPT", "0.7"))  # 产品即品牌豁免线
BRAND_PULSE_MIN_TOTAL = float(os.environ.get("AD_BEAT_BRAND_PULSE_MIN_TOTAL", "15.0"))
SOUND_MIN_TOTAL = float(os.environ.get("AD_BEAT_SOUND_MIN_TOTAL", "15.0"))  # 短于此不判声音设计
PROVENANCE = "internal-heuristic·confidence=low"

_NOISE_RE = re.compile(r"[\s，。！？、；：…—\-\|,.!?;:\"'“”‘’()（）\[\]【】]+")
# 豁免镜（有意重复/hold 的结构位）：与 shot_variety 同口径（本线自包含，不跨文件 import）。
_EXEMPT_RE = re.compile(
    r"片尾|尾板|end.?card|endcard|收尾|logo|CTA|slogan|口号|品牌板|"
    r"产品特写|产品展示|产品beauty|beauty.?shot|hero.?shot|包装展示|卖点板|价格板|二维码|下单",
    re.IGNORECASE)
# 钩子节拍（与 shot_variety 的再钩词族同源 + 黄金3秒/悬念类，本线自包含）。
_HOOK_RE = re.compile(
    r"钩子|hook|悬念|冲突|痛点|反转|转折|提问|对比|反差|揭晓|揭秘|真相|结果|竟然|居然|"
    r"挑战|测试|实测|before|after|证言|见证|数字冲击|倒计时|黄金3秒|黄金三秒",
    re.IGNORECASE)
# CTA/行动指令词族（电商四段式的"行动"位）。
_CTA_RE = re.compile(
    r"CTA|行动指令|点击|购买|下单|抢购|领取|领券|搜索|关注|立即|马上|扫码|咨询|预约|进店|链接|拍下",
    re.IGNORECASE)
# 电商四段式的"痛点"与"方案"位。
_PAIN_RE = re.compile(r"痛点|困扰|烦恼|难题|头疼|苦恼|problem|pain", re.IGNORECASE)
_SOLUTION_RE = re.compile(r"解决|方案|solution|使用后|用它|效果|一键|轻松搞定", re.IGNORECASE)
# ABCD·Connection：画面里有人（脸/表情/情绪）——广告工艺：人脸+情绪显著提升连接。
_PERSON_RE = re.compile(
    r"人物|女主|男主|表情|微笑|大笑|情绪|人脸|面部|达人|模特|用户|妈妈|爸爸|孩子|老人|情侣|face|smile",
    re.IGNORECASE)
# 转化类投放目标（只有电商/转化目标才判四段式，品牌片不套这个模板）。
_CONVERSION_RE = re.compile(r"转化|带货|电商|下单|销量|conversion|sales|performance", re.IGNORECASE)
# 钩子类型标签（性能广告工艺：给 hook 打分类标签，才能按类型统计胜率/做批次多样性）。
_HOOK_TYPE_KEYS = ("hook_type", "钩子类型", "hook_taxonomy")
NGRAM = 2


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def finding(severity: str, code: str, msg: str, shots: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """ad gate 消费 `msg` 键（见 ad-craft/gate.py:52）。附 shots 便于定位，不影响 gate。"""
    out: Dict[str, Any] = {"severity": severity, "code": code, "msg": msg}
    if shots:
        out["shots"] = list(shots)
    return out


def clean(text: str) -> str:
    return _NOISE_RE.sub("", str(text or ""))


def shingles(text: str, n: int = NGRAM) -> Set[str]:
    c = clean(text)
    if len(c) < n:
        return {c} if c else set()
    return {c[i:i + n] for i in range(len(c) - n + 1)}


def _norm(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def load_json(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


# ── storyboard 解析（字段容忍：广告 storyboard schema 较薄；与 shot_variety 同法） ──

def iter_shots(storyboard: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows = storyboard.get("shots") or storyboard.get("clips") or storyboard.get("镜头") or []
    return [r for r in rows if isinstance(r, dict)]


def shot_id(shot: Mapping[str, Any], idx: int) -> str:
    return str(shot.get("shot_id") or shot.get("clip_id") or shot.get("id") or f"镜头{idx + 1}")


def _shot_seconds(shot: Mapping[str, Any]) -> Optional[float]:
    for key in ("duration", "时长", "duration_sec", "seconds"):
        if shot.get(key) is not None:
            try:
                return float(re.sub(r"[^\d.]", "", str(shot.get(key))) or 0) or None
            except ValueError:
                return None
    return None


def shot_supers(shot: Mapping[str, Any]) -> str:
    """镜内屏字（花字/字幕/supers）——Clearcast 停留公式与静音可看都以它为准。"""
    for key in ("字幕", "花字", "超字", "supers", "subtitle", "screen_text", "overlay_text", "text"):
        val = shot.get(key)
        if val:
            return str(val)
    return ""


def shot_vo(shot: Mapping[str, Any]) -> str:
    for key in ("vo", "voiceover", "台词", "旁白"):
        val = shot.get(key)
        if val:
            return str(val)
    return ""


def shot_text(shot: Mapping[str, Any]) -> str:
    """全文本拼块（画面+VO+屏字+结构位标签），供关键词初筛。"""
    keys = ("shot", "frame", "画面", "主体动作", "description", "desc", "visual",
            "section", "role", "purpose", "vo", "voiceover", "台词", "旁白",
            "字幕", "花字", "supers", "subtitle", "screen_text", "overlay_text")
    return " ".join(str(shot.get(k) or "") for k in keys)


def is_exempt(shot: Mapping[str, Any]) -> bool:
    """有意重复/结构位镜（片尾/logo/CTA/产品 beauty/价格板…）。"""
    blob = " ".join(str(shot.get(k) or "") for k in
                    ("shot_type", "scene", "场景", "shot", "frame", "画面", "section", "role", "purpose"))
    if shot.get("endcard") or shot.get("is_endcard") or shot.get("is_hero") or shot.get("hero_product"):
        return True
    return bool(_EXEMPT_RE.search(blob))


def build_timeline(shots: List[Tuple[str, Dict[str, Any]]]):
    """[(sid, shot, start, dur)]、总时长、时间轴是否可信（时长已知过半才判时间类信号）。"""
    timed = []
    elapsed = 0.0
    known = 0
    for sid, shot in shots:
        dur = _shot_seconds(shot)
        timed.append((sid, shot, elapsed, dur))
        if dur:
            known += 1
            elapsed += dur
    timeline_ok = known >= max(1, len(shots) // 2 + 1)
    return timed, elapsed, timeline_ok


# ── brief / concept 上下文 ────────────────────────────────────────────────────

def _string_of(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or value.get("名称") or "")
    return str(value or "")


def brand_tokens_of(brief: Optional[Mapping[str, Any]]) -> List[str]:
    tokens: List[str] = []
    for key in ("品牌", "brand", "brand_name", "产品", "product", "product_name", "产品名"):
        val = _string_of((brief or {}).get(key)).strip()
        if len(val) >= 2:
            tokens.append(val)
    return tokens


def objective_of(brief: Optional[Mapping[str, Any]]) -> str:
    for key in ("campaign_objective", "objective", "目标", "投放目标"):
        val = _string_of((brief or {}).get(key)).strip()
        if val:
            return val
    return ""


def benefit_text_of(concept: Optional[Mapping[str, Any]]) -> str:
    return " ".join(_string_of((concept or {}).get(k)) for k in ("key_message", "big_idea", "主张", "核心信息"))


def _mentions_brand(blob: str, brand_tokens: Sequence[str]) -> bool:
    if brand_tokens:
        return any(tok in blob for tok in brand_tokens)
    # 没有 brief 品名 → 退化为品类关键词（产品/品牌/logo/包装）。
    return bool(re.search(r"产品|品牌|logo|包装", blob, re.IGNORECASE))


# ── 信号 ─────────────────────────────────────────────────────────────────────

def audit_hook_window(timed, timeline_ok: bool, findings) -> Optional[float]:
    """黄金 3 秒：第一个钩子节拍须在 HOOK_WINDOW 内开始（短视频/信息流开场工艺）。
    时长缺失过半不判（insufficient data，不臆造节奏问题）。返回首钩开始秒（供 ABCD）。"""
    first_hook_at = None
    for _sid, shot, start, _dur in timed:
        if _HOOK_RE.search(shot_text(shot)):
            first_hook_at = start
            break
    if not timeline_ok:
        return first_hook_at
    if first_hook_at is None:
        findings.append(finding("warn", "hook_late",
                                "全片没有任何钩子节拍（悬念/提问/痛点/对比/揭晓…）——黄金 3 秒没有给观众"
                                "停下来的理由，信息流里会被直接划走（关键词初筛，若开场钩是纯画面冲击请在"
                                "分镜文本里写明）"))
    elif first_hook_at > HOOK_WINDOW:
        findings.append(finding("warn", "hook_late",
                                f"第一个钩子节拍在 {first_hook_at:.1f}s 才出现（工艺口径 ≤{HOOK_WINDOW:.0f}s）——"
                                "黄金 3 秒内没有钩子，前排镜头建议前置悬念/痛点/反差"))
    return first_hook_at


def audit_brand_entry(timed, timeline_ok: bool, brand_tokens, findings) -> Optional[float]:
    """品牌 5 秒进场（YouTube skippable 工艺：5s 内见品牌/产品，可跳过环境下 VTR ↑~40%）。"""
    first_at = None
    for _sid, shot, start, _dur in timed:
        if _mentions_brand(shot_text(shot), brand_tokens):
            first_at = start
            break
    if first_at is None:
        findings.append(finding("info", "brand_entry_unknown",
                                "分镜文本里找不到品牌/产品提及——无法判断品牌是否 5s 内进场；"
                                "若品牌露出是纯视觉（logo 贴片）请在分镜写明，或核对 brief 品名"))
        return None
    if timeline_ok and first_at > BRAND_ENTRY_MAX:
        findings.append(finding("warn", "brand_entry_late",
                                f"品牌/产品首次露出在 {first_at:.1f}s（工艺口径 ≤{BRAND_ENTRY_MAX:.0f}s）——"
                                "可跳过/可划走环境下，晚品牌意味着大量曝光根本没带到品牌"))
    return first_at


def audit_cta(timed, total: float, timeline_ok: bool, findings) -> bool:
    """CTA 存在 + 收尾（电商四段式的"行动指令"位；重复 CTA 是合法手法，只查缺失/错位）。"""
    cta_rows = [(sid, shot, start, dur) for sid, shot, start, dur in timed
                if _CTA_RE.search(shot_text(shot))]
    if not cta_rows:
        findings.append(finding("warn", "cta_missing",
                                "全片没有任何 CTA/行动指令节拍（点击/购买/搜索/扫码…）——广告没有出口，"
                                "流量再好也接不住；至少片尾要有一个明确动作指令"))
        return False
    sid, shot, start, dur = cta_rows[-1]
    is_last = sid == timed[-1][0]
    if is_last or is_exempt(shot):
        return True
    if timeline_ok:
        end = start + (dur or 0.0)
        if end + 1e-6 < total - CTA_TAIL:
            findings.append(finding("info", "cta_not_final",
                                    f"最后一个 CTA 节拍（{sid}）在 {end:.1f}s 就结束了（全片 {total:.0f}s）——"
                                    f"行动指令通常收在片尾最后 {CTA_TAIL:.0f}s/endcard，避免看完忘了行动",
                                    [sid]))
    return True


def audit_pain_solution_order(timed, objective: str, findings) -> None:
    """电商四段式：黄金3秒→痛点→方案→行动。只对转化/带货目标判；方案先于痛点 = 说服链倒置。"""
    if not _CONVERSION_RE.search(objective or ""):
        return
    pain_idx = solution_idx = None
    for idx, (_sid, shot, _start, _dur) in enumerate(timed):
        blob = shot_text(shot)
        if pain_idx is None and _PAIN_RE.search(blob):
            pain_idx = idx
        if solution_idx is None and _SOLUTION_RE.search(blob):
            solution_idx = idx
    if pain_idx is not None and solution_idx is not None and solution_idx < pain_idx:
        findings.append(finding("warn", "pain_solution_inverted",
                                f"转化目标广告里，方案/效果节拍（{timed[solution_idx][0]}）先于痛点节拍"
                                f"（{timed[pain_idx][0]}）出现——电商四段式是 痛点→方案→行动：观众先认问题"
                                "才会认解法，倒过来说服链断裂",
                                [timed[solution_idx][0], timed[pain_idx][0]]))


def audit_asl_band(timed, timeline_ok: bool, findings) -> None:
    """广告 ASL 带（实测：商业广告 ~1.4–2.5s/镜，电视节目 4.7–4.9s）。类型相关 → 只 info。"""
    known = [dur for _sid, _shot, _start, dur in timed if dur]
    if not timeline_ok or not known:
        return
    asl = sum(known) / len(known)
    if asl < ASL_MIN or asl > ASL_MAX:
        direction = "碎" if asl < ASL_MIN else "慢"
        findings.append(finding("info", "asl_out_of_band",
                                f"平均镜长 {asl:.1f}s 出了广告惯例带（{ASL_MIN}–{ASL_MAX}s）——节奏偏{direction}；"
                                "品牌情绪片可以慢、快剪混剪可以碎，若是刻意的忽略本条（advisory）"))


def audit_pacing_front_loaded(timed, findings) -> None:
    """留存剪辑工艺：切换密度开头最高（前 1/4 平均镜长应 ≤ 全片均值）。只 info。"""
    known = [(sid, dur) for sid, _shot, _start, dur in timed if dur]
    if len(known) < MIN_SHOTS_FOR_PACING:
        return
    q = max(1, len(known) // 4)
    front = [dur for _sid, dur in known[:q]]
    mean_all = sum(d for _sid, d in known) / len(known)
    mean_front = sum(front) / len(front)
    if mean_front > mean_all * PACING_TOLERANCE:
        findings.append(finding("info", "pacing_back_loaded",
                                f"开场前 1/4 的平均镜长 {mean_front:.1f}s 比全片均值 {mean_all:.1f}s 还慢——"
                                "留存工艺是前紧后松（开头切换密度最高，钩住再放缓）；若是刻意慢热请忽略"))


def _supers_min_hold(text: str) -> float:
    """Clearcast supers 停留公式：0.2s/词 + 2s 识别；中文按 0.15s/字折算。"""
    cjk = len(re.findall(r"[一-鿿]", text))
    words = len(re.findall(r"[A-Za-z0-9]+", text))
    return SUPERS_BASE + cjk * SUPERS_PER_CHAR + words * SUPERS_PER_WORD


def audit_supers_hold(timed, findings) -> None:
    """花字停留：字数算出的最短可读时长 > 镜长 = 观众读不完（Clearcast 口径）。"""
    bad: List[str] = []
    for sid, shot, _start, dur in timed:
        text = shot_supers(shot)
        if not text or not dur:
            continue
        need = _supers_min_hold(text)
        if dur + 1e-6 < need:
            bad.append(f"{sid}（{len(clean(text))}字需≈{need:.1f}s，镜长 {dur:.1f}s）")
    if bad:
        findings.append(finding("warn", "supers_hold_short",
                                "屏字停留不够读：" + "；".join(bad) +
                                "——按 Clearcast 口径（0.2s/词+2s，中文 0.15s/字折算）删字或加镜长",
                                [b.split("（")[0] for b in bad]))


def audit_mute_pass(storyboard, timed, findings) -> None:
    """静音可看（85% 信息流静音播放）：有 VO 的镜必须有屏字兜底。
    字幕若由 compose render_subs 统一渲染，在 storyboard 顶层标 `字幕:"统一渲染"` 即可豁免。"""
    if storyboard.get("字幕") or storyboard.get("subtitles"):
        return
    vo_rows = [(sid, shot) for sid, shot, _start, _dur in timed if shot_vo(shot)]
    if not vo_rows:
        return
    uncovered = [sid for sid, shot in vo_rows if not shot_supers(shot)]
    if uncovered:
        findings.append(finding("warn", "mute_pass_gap",
                                f"{len(vo_rows)} 个 VO 镜里 {len(uncovered)} 个没有字幕/花字兜底"
                                f"（{'、'.join(uncovered[:6])}…）——85% 信息流静音播放，关掉声音这些镜等于空播；"
                                "若字幕由合成期统一渲染，请在 storyboard 顶层标 字幕 字段留痕",
                                uncovered))


def audit_open_self_contained(timed, timeline_ok: bool, brand_tokens, benefit_text, findings) -> None:
    """自足开场（skippable 工艺：前 5s 单独看也要知道 给谁/什么好处/什么产品）。只 info。"""
    if not timeline_ok:
        return
    open_blob = " ".join(shot_text(shot) for _sid, shot, start, _dur in timed if start <= BRAND_ENTRY_MAX)
    brand_hit = _mentions_brand(open_blob, brand_tokens)
    benefit_hit = len(shingles(benefit_text) & shingles(open_blob)) >= 2 if clean(benefit_text) else False
    if not brand_hit and not benefit_hit:
        findings.append(finding("info", "open_not_self_contained",
                                f"前 {BRAND_ENTRY_MAX:.0f}s 既没出现品牌/产品、也没带到核心主张——被跳过/划走的"
                                "观众什么都没收到；自足开场是 skippable 环境的保底工艺（advisory）"))


def audit_six_second(timed, total: float, timeline_ok: bool, findings) -> None:
    """6s bumper 只讲一件事（Think with Google：6s 不是 30s 的压缩，镜头和故事弧都翻不了页）。"""
    if not timeline_ok or total > SIX_SEC_MAX:
        return
    non_exempt = [sid for sid, shot, _start, _dur in timed if not is_exempt(shot)]
    blob = " ".join(shot_text(shot) for _sid, shot, _start, _dur in timed)
    four_act = bool(_PAIN_RE.search(blob) and _SOLUTION_RE.search(blob) and _CTA_RE.search(blob))
    if len(non_exempt) > SIX_SEC_MAX_SHOTS or four_act:
        why = (f"非豁免镜 {len(non_exempt)} 个（>{SIX_SEC_MAX_SHOTS}）" if len(non_exempt) > SIX_SEC_MAX_SHOTS
               else "痛点+方案+CTA 四段式俱全")
        findings.append(finding("warn", "six_second_overstuffed",
                                f"{total:.0f}s 短版里塞了{why}——6s bumper 要围绕**一个**点子重新构作，"
                                "不是 30s 的压缩版；砍到一个画面一件事", non_exempt))


def audit_hook_taxonomy(storyboard, concept, findings) -> None:
    """钩子类型标签（性能广告工艺：hook 打分类标签才能按类型统计胜率、做批次多样性）。只 info。"""
    for source in (concept or {}, storyboard or {}):
        for key in _HOOK_TYPE_KEYS:
            if _norm(source.get(key)):
                return
    findings.append(finding("info", "hook_taxonomy_missing",
                            "concept/storyboard 没有声明钩子类型（提问/数据/反差/before-after/痛点先行/"
                            "结果先行/好奇/创始人/开箱/证言…）——打上标签才能跨条目统计哪类钩子赢、"
                            "并在变体批次里保证钩子多样性（advisory）"))


def audit_brand_pulse(timed, total: float, timeline_ok: bool, brand_tokens, findings) -> None:
    """品牌脉冲露出（2026-07 第七轮·Teixeira pulsing 工艺）：品牌该"短脉冲、多频次"地出现。

    两信号（都要 timeline 可信且总时长 ≥BRAND_PULSE_MIN_TOTAL 才判）：
      · brand_pulse_gap    品牌进场后出现超长"品牌黑洞"（连续 >BRAND_GAP_MAX 秒无一镜提及
        品牌/产品）——中段大段裸奔，划走的观众全程没带走品牌记忆。
      · branding_monolithic 单段连续压品牌 >BRAND_RUN_MAX 秒——一坨式露出触发回避，
        拆成多次短脉冲更抗跳出。
    产品即品牌品类（品牌镜占比 ≥BRAND_RATIO_EXEMPT，包装全程在画）两信号都豁免。"""
    if not timeline_ok or total < BRAND_PULSE_MIN_TOTAL:
        return

    # 品牌可见 = 品牌词命中 ∪ 产品在画词（机身/瓶身/包装…）——分镜常写"机身细节滑过"
    # 而不点品名，产品在画就是品牌露出，只认品牌词会把演示段误判成黑洞。
    def _visible(blob: str) -> bool:
        return _mentions_brand(blob, brand_tokens) or bool(
            re.search(r"产品|机身|瓶身|包装|logo|界面|UI|app|图标|二维码", blob, re.IGNORECASE))

    marks = [(start, dur, _visible(shot_text(shot)))
             for _sid, shot, start, dur in timed if dur]
    branded = [(s, d) for s, d, hit in marks if hit]
    if not branded:
        return  # brand_entry_unknown 已报，不重复
    branded_secs = sum(d for _s, d in branded)
    if total and branded_secs / total >= BRAND_RATIO_EXEMPT:
        return  # 产品即品牌：全程在画合法
    # 最长无品牌区间（从品牌首次进场起算到片尾）。
    entry = branded[0][0]
    gap = 0.0
    worst_gap = 0.0
    for s, d, hit in marks:
        if s + d <= entry:
            continue
        if hit:
            worst_gap = max(worst_gap, gap)
            gap = 0.0
        else:
            gap += d
    worst_gap = max(worst_gap, gap)
    if worst_gap > BRAND_GAP_MAX:
        findings.append(finding("warn", "brand_pulse_gap",
                                f"品牌进场后有连续 {worst_gap:.1f}s 无任何品牌/产品露出"
                                f"（>{BRAND_GAP_MAX:.0f}s）——脉冲工艺：品牌该短脉冲多频次地回来，"
                                "中段黑洞里划走的观众没带走任何品牌记忆；在中段补一次轻露出"
                                "（产品入画/角标/口播带品名均可）"))
    run = 0.0
    worst_run = 0.0
    for _s, d, hit in marks:
        run = run + d if hit else 0.0
        worst_run = max(worst_run, run)
    if worst_run > BRAND_RUN_MAX:
        findings.append(finding("info", "branding_monolithic",
                                f"单段连续压品牌 {worst_run:.1f}s（>{BRAND_RUN_MAX:.0f}s）——"
                                "实证口径：总曝光相同时，一坨式露出比短脉冲更触发回避；"
                                "拆成多次短露出（脉冲）更抗跳出"))


_SOUND_RE = re.compile(r"音乐|BGM|配乐|音效|SFX|soundtrack|jingle|声音设计|sonic", re.IGNORECASE)
_NO_MUSIC_RE = re.compile(r"无音乐|不使用音乐|不用音乐|无BGM|纯人声|无配乐", re.IGNORECASE)


def audit_sound_design(storyboard, brief, total: float, findings) -> None:
    """声音设计缺失（2026-07 第七轮·生产实锤盲区：星盒 30s 竖版零 SFX/BGM 规划）。

    总时长 ≥SOUND_MIN_TOTAL 而 storyboard/brief 全文找不到任何 音乐/BGM/音效 声明、
    也没有"无音乐"的显式决定 → info。诚实声明"本轮无音乐"即豁免（决定归人，
    但不许没想过这件事）。"""
    if total < SOUND_MIN_TOTAL:
        return
    blob = json.dumps(storyboard or {}, ensure_ascii=False) + json.dumps(brief or {}, ensure_ascii=False)
    if _NO_MUSIC_RE.search(blob):
        return
    if not _SOUND_RE.search(blob):
        findings.append(finding("info", "sound_design_missing",
                                f"全片 {total:.0f}s 但 storyboard/brief 里没有任何音乐/音效/BGM 规划，"
                                "也没有『本轮不使用音乐』的显式决定——竖版信息流成片零声音设计"
                                "会明显拉低完成度；补 BGM/SFX 计划，或在 brief 显式声明无音乐"))


def build_abcd(timed, timeline_ok: bool, first_hook_at, first_brand_at, cta_found: bool) -> Dict[str, Any]:
    """Google ABCD 四轴（1.7 万+ 条广告验证：合规条目短期销量 ↑~30%）。纯数据，不产 finding。"""
    attention = (first_hook_at is not None and first_hook_at <= HOOK_WINDOW) if timeline_ok else None
    branding = (first_brand_at is not None and first_brand_at <= BRAND_ENTRY_MAX) if timeline_ok else None
    connection = any(_PERSON_RE.search(shot_text(shot)) for _sid, shot, _start, _dur in timed) or None
    if connection is None:
        connection = False
    direction = bool(cta_found)
    score = sum(1 for v in (attention, branding, connection, direction) if v is True)
    return {"attention": attention, "branding": branding, "connection": connection,
            "direction": direction, "score": score,
            "note": "A=钩子≤3s B=品牌≤5s C=有人脸/情绪 D=有CTA；时长缺失时 A/B 为 null"}


def build(root: Path) -> Dict[str, Any]:
    """契约形状（findings 用 `msg` 键，ad gate 可直接消费）：

        {"schema_version":1,"kind":"ad_beat_structure_audit","available":bool,
         "summary":{"block":0,"warn","info"},"findings":[{"severity","code","msg"}],"abcd":{...}}

    `summary.block` 恒为 0——advisory 纪律。"""
    root = Path(root)
    storyboard = load_json(root / STORYBOARD_REL)
    brief = load_json(root / BRIEF_REL)
    concept = load_json(root / CONCEPT_REL)
    findings: List[Dict[str, Any]] = []
    available = isinstance(storyboard, dict)
    shots: List[Tuple[str, Dict[str, Any]]] = []
    abcd: Dict[str, Any] = {}
    total = 0.0
    timeline_ok = False

    if not available:
        findings.append(finding("warn", "storyboard_missing",
                                "缺 脚本/storyboard.json——没有分镜可审结构节拍（insufficient_data，"
                                "不代表结构没问题）。配音后跑 ad-script 分镜 pass 产出 storyboard.json。"))
    else:
        raw = iter_shots(storyboard)
        shots = [(shot_id(s, i), s) for i, s in enumerate(raw)]
        if not shots:
            findings.append(finding("warn", "storyboard_empty",
                                    "storyboard.json 存在但没有 shots——分镜还没落档。"))
        else:
            timed, total, timeline_ok = build_timeline(shots)
            brand_tokens = brand_tokens_of(brief)
            first_hook_at = audit_hook_window(timed, timeline_ok, findings)
            first_brand_at = audit_brand_entry(timed, timeline_ok, brand_tokens, findings)
            cta_found = audit_cta(timed, total, timeline_ok, findings)
            audit_pain_solution_order(timed, objective_of(brief), findings)
            audit_asl_band(timed, timeline_ok, findings)
            audit_pacing_front_loaded(timed, findings)
            audit_supers_hold(timed, findings)
            audit_mute_pass(storyboard, timed, findings)
            audit_open_self_contained(timed, timeline_ok, brand_tokens, benefit_text_of(concept), findings)
            audit_six_second(timed, total, timeline_ok, findings)
            audit_hook_taxonomy(storyboard, concept, findings)
            audit_brand_pulse(timed, total, timeline_ok, brand_tokens, findings)
            audit_sound_design(storyboard, brief, total, findings)
            abcd = build_abcd(timed, timeline_ok, first_hook_at, first_brand_at, cta_found)

    return {
        "schema_version": VERSION,
        "kind": KIND,
        "available": available,
        "project_root": str(root),
        "generated_at": now_iso(),
        "thresholds": {
            "hook_window": HOOK_WINDOW, "brand_entry_max": BRAND_ENTRY_MAX, "cta_tail": CTA_TAIL,
            "asl_min": ASL_MIN, "asl_max": ASL_MAX,
            "supers_per_char": SUPERS_PER_CHAR, "supers_per_word": SUPERS_PER_WORD,
            "supers_base": SUPERS_BASE, "six_sec_max": SIX_SEC_MAX,
            "six_sec_max_shots": SIX_SEC_MAX_SHOTS, "pacing_tolerance": PACING_TOLERANCE,
            "brand_gap_max": BRAND_GAP_MAX, "brand_run_max": BRAND_RUN_MAX,
            "brand_ratio_exempt": BRAND_RATIO_EXEMPT, "sound_min_total": SOUND_MIN_TOTAL,
            "provenance": PROVENANCE,
            "note": "advisory：本检永不产 block。CTA/endcard 有意重复豁免；单场景/慢节奏广告合法"
                    "（ASL/节奏只 info）；关键词初筛，好不好看仍需人判。",
        },
        "inputs": {
            "shots": len(shots),
            "exempt_shots": sum(1 for _sid, s in shots if is_exempt(s)),
            "total_seconds": round(total, 2),
            "timeline_known": timeline_ok,
            "brief_present": brief is not None,
            "concept_present": concept is not None,
        },
        "abcd": abcd,
        "summary": {
            "block": 0,  # advisory：恒 0，不是「这次刚好没有」
            "warn": sum(1 for f in findings if f["severity"] == "warn"),
            "info": sum(1 for f in findings if f["severity"] == "info"),
        },
        "findings": findings,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    i = report.get("inputs") or {}
    abcd = report.get("abcd") or {}
    lines = ["# 广告叙事结构/节拍工艺机检", ""]
    if not report.get("available"):
        lines += ["- ⚠️ 未找到 `脚本/storyboard.json`（available=false·降级为建议，不阻断）", ""]
    lines += [f"- 分镜 {i.get('shots')} 镜 · 总长 ≈{i.get('total_seconds')}s · "
              f"豁免（片尾/CTA/产品beauty…）{i.get('exempt_shots')} 镜",
              f"- warn {s.get('warn')} · info {s.get('info')}（advisory：本检不产 block）"]
    if abcd:
        def _mark(v):
            return "✅" if v is True else ("—" if v is None else "❌")
        lines.append(f"- ABCD：A注意 {_mark(abcd.get('attention'))} · B品牌 {_mark(abcd.get('branding'))} · "
                     f"C连接 {_mark(abcd.get('connection'))} · D指令 {_mark(abcd.get('direction'))} "
                     f"（{abcd.get('score')}/4）")
    lines.append("")
    icon = {"block": "⛔", "warn": "⚠️", "info": "ℹ️"}
    for f in report.get("findings") or []:
        lines.append(f"- {icon.get(f['severity'], '·')} `{f['code']}` {f['msg']}")
    if not report.get("findings"):
        lines.append("- ✅ 结构位齐整：钩子/品牌进场/CTA/节奏/屏字停留未见缺位（好不好看仍需人判）")
    return "\n".join(lines) + "\n"


def write_report(root: Path, report: Mapping[str, Any]) -> None:
    """原子写（tmp + os.replace）：报告被 gate/review 并发读时不会读到半截 JSON。"""
    path = root / REPORT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    for target, payload in ((path, json.dumps(report, ensure_ascii=False, indent=2) + "\n"),
                            (path.with_suffix(".md"), render_markdown(report))):
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, target)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", help="作品根")
    ap.add_argument("--write", action="store_true", help=f"落盘 {REPORT_REL}（+ 同名 .md·原子写）")
    ap.add_argument("--json", action="store_true", help="打印 JSON 而非 markdown")
    ap.add_argument("--strict", action="store_true",
                    help="warn>0 时 exit 1（本检 advisory·恒无 block，--strict 只影响退出码）")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    report = build(root)
    if ns.write:
        write_report(root, report)
    print(json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report))
    return 1 if (ns.strict and report["summary"]["warn"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
