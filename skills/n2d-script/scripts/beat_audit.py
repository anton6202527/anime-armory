#!/usr/bin/env python3
"""beat_audit.py — 集内留存节拍机检（Gap4/5）。

为什么存在：`导演节奏.md` 要求"先列节拍点表(开场钩/钩子/爽点/集尾钩)再写词"，voiceover 也有
⚡/💥/🪝 标记，但**没有任何机检**——没人量"是否每 15-20s 一个钩子、是否 ≥1 反转、集尾是否硬断、
爽点是否只有情绪没有信息增量"。2026 爆款关键是"信息回报+情绪回报叠加"，且要反同质化。

本脚本读 voiceover.txt（钩子标记 + 情绪）+ 可选 镜头时长.json（真实秒）→ 出：
  ① 集内节拍体检：开场冷启 / 钩子间隔 / ≥1 反转 / 集尾 cliffhanger / 镜头时长曲线。
  ② 情绪回报 vs 信息回报（Gap4）：爽点是否只有情绪宣泄、缺信息增量。
  ③ --series：跨集套路同质化（桥段指纹 Jaccard），治"AI 模板复印、观众疲劳"。

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
        if "--json" in flags:
            print(json.dumps({"episodes": eps, "duplicates": dups,
                              "cold_open_chain_rate": chain_rate,
                              "cold_open_chain_findings": [{"severity": s, "code": c, "msg": m}
                                                          for s, c, m in chain_findings],
                              "narrative_risk_profile": risk_ranked,
                              "narrative_audit_priority": [{"severity": s, "code": c, "msg": m}
                                                           for s, c, m in risk_findings]},
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
