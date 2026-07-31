#!/usr/bin/env python3
"""Audit raw episode boundaries before n2d-script stage-1 refinement.

Usage:
  python3 skills/n2d/n2d-script/scripts/boundary_audit.py <作品根> [start-end] [--strict] [--json]

This is a deterministic pre-check. It does not decide story quality by itself;
it flags episodes that need human/LLM boundary review before writing voiceover.

两层输出：
  ① 逐集体检表（粗胚右边界风险：软断/章内续切/弱钩/无闭环）。
  ② 剧级追更骨架（Gap1）：跨集断点强度分布 + 连续弱钩集群 + 开篇集群钩子梯度 +
     按 `变现模式`(免费/付费/海外) 的付费/AD 卡点集定位。题材词典按 `题材` 选择点切换(Gap3)。
     **显式付费墙强度入闸**：仅项目配置/平台合同声明的付费或解锁卡点，断点不够强时进 strict 闸；
     未配置时保持 advisory，不猜第 8/10 集。免费档恒不触发单点付费墙。
     另含**视觉奇观放置初筛**（report-only·北极星看点④）：奇观被切点劈半 / 奇观集断点弱
     （疑埋中段未当锚点）。纯报告，不进 strict 闸。
完整方法论见 references/追更骨架.md。
"""
import json
import hashlib
import os
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

from n2d_const import boundary_buckets, boundary_lexicon  # noqa: E402
from n2d_settings import get_setting  # noqa: E402

CHAPTER_HEAD = re.compile(r"^第[一二三四五六七八九十百千万0-9]+章")
# 悬念收尾标点（强断点的"硬断"信号，与词钩叠加判强度）。
SUSPENSE_PUNCT = ("？", "！", "…", "——", "?", "!")
COLD_OPEN_RE = re.compile(
    r"(突然|不好了|出事|杀|逃|追|血|门外|推门|系统提示|提示|真相|原来|竟|"
    r"不可能|为什么|是谁|危险|危机|反击|打脸|逆袭)"
)
SLOW_OPEN_RE = re.compile(r"^\s*(?:第[一二三四五六七八九十百千万0-9]+章\s*)?(翌日|次日|三日后|与此同时|另一边|话说|回忆|从前)")
# 视觉奇观词面（report-only·北极星看点④）：只有 AI 能低成本突破实景的画面高潮。
# 用于初筛"奇观被切点劈半 / 奇观集断点弱（疑埋中段未当锚点）"，不进 strict 闸。
SPECTACLE_RE = re.compile(
    r"(渡劫|天劫|雷劫|境界突破|突破到|晋升|觉醒|法宝出世|出世|飞升|御剑|腾空而起|"
    r"大阵|法阵|阵法|对轰|斗法|万人|千军|大军|决战|大战|血战|异象|天地异象|天地变色|"
    r"末日|海啸|崩塌|陨落|巨龙|神兽|封印|结界|祭天|登基大典|血月|爆发)"
)
MAIN_NODE_SOURCE_KINDS = {"main_nodes_txt", "main_nodes", "novel_review_main_nodes"}


def source_kind(root):
    """Return n2d source kind from 小说/_源指纹.json, if present."""
    path = Path(root) / "小说" / "_源指纹.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    return str(data.get("source_kind") or "").strip()


def is_main_node_project(root):
    return source_kind(root) in MAIN_NODE_SOURCE_KINDS


def _field_value(text, label):
    match = re.search(rf"^{re.escape(label)}\s*[:：]\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def build_res(genre_text):
    """题材感知：强钩收尾 + 冲突 + 爽点/反转 三正则（与 split_novel 同源，避免漂移）。"""
    strong, conflict, payoff = boundary_lexicon(genre_text)
    # Punctuation is an independent signal in end_strength; remove punctuation-
    # only tokens here so it cannot be counted again as a semantic hook.
    semantic_strong = [t for t in strong if re.search(r"[\w㐀-鿿]", t)]
    strong_re = re.compile(r"(" + "|".join(re.escape(t) for t in semantic_strong) + r")")
    conflict_re = re.compile(r"(" + "|".join(re.escape(t) for t in conflict) + r")")
    payoff_re = re.compile(r"(" + "|".join(re.escape(t) for t in payoff) + r")")
    return strong_re, conflict_re, payoff_re


def cjk_len(text):
    return len(re.findall(r"[㐀-鿿]", text))


def ep_num(path):
    m = re.search(r"第(\d+)集", path.name)
    return int(m.group(1)) if m else -1


def end_strength(text, soft_end, strong_re):
    """集尾断点强度：强(2)=悬念标点+语义词钩齐 / 中(1)=其一 / 弱(0)=无。

    `boundary_lexicon` 为了粗切候选兼容，仍含 ``！/？/…`` 这些标点 token。
    审计时必须先剥掉尾部标点再匹配词钩，否则一个 ``！`` 会同时命中
    ``punct`` 和 ``word``，把普通感叹句重复计成强钩。
    """
    if soft_end:
        return 0
    tail = text[-160:]
    punct = bool(text and text.rstrip()[-1:] in "？！…—?!")
    semantic_tail = re.sub(r"[？！…—?!\s]+$", "", tail)
    word = bool(semantic_tail and strong_re.search(semantic_tail))
    return 2 if (punct and word) else (1 if (punct or word) else 0)


def start_strength(text, conflict_re, payoff_re):
    """集首承接强度：下集开场也要能接住上集断点，避免强尾后慢启动。"""
    head = text[:180]
    word = bool(COLD_OPEN_RE.search(head) or conflict_re.search(head) or payoff_re.search(head))
    slow = bool(SLOW_OPEN_RE.search(head))
    if word and not slow:
        return 2
    return 1 if word else 0


STRENGTH_LABEL = {2: "强", 1: "中", 0: "弱"}
PAIR_STRENGTH_LABEL = {4: "强", 3: "强", 2: "中", 1: "弱", 0: "弱"}


def load_rows(root, strong_re, conflict_re, payoff_re):
    script_root = Path(root) / "脚本"
    main_node = is_main_node_project(root)
    rows = []
    for d in sorted(script_root.glob("第*集"), key=ep_num):
        raw = d / "raw.txt"
        if not raw.exists():
            continue
        text = raw.read_text(encoding="utf-8").strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        hook_text = _field_value(text, "结尾钩子")
        beats_text = _field_value(text, "必保节点")
        soft_end = bool(text and text[-1] in "，、；：")
        tail_for_strength = hook_text or text[-160:]
        explicit_hook = main_node and bool(hook_text)
        structured_main_node = main_node and bool(beats_text and hook_text)
        measured_strength = end_strength(tail_for_strength, False if explicit_hook else soft_end, strong_re)
        rows.append({
            "ep": ep_num(d),
            "chars": cjk_len(text),
            "chapter": bool(CHAPTER_HEAD.search(text)) or structured_main_node,
            "start": "".join(lines[:2])[:90] if lines else "",
            "end": "".join(lines[-3:])[-140:] if lines else "",
            "raw_rel": str(raw.relative_to(Path(root))),
            "raw_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "soft_end": soft_end and not explicit_hook,
            "strong_end": measured_strength >= 2,
            "strength": measured_strength,
            "start_strength": start_strength(text, conflict_re, payoff_re),
            "has_conflict": bool(conflict_re.search(beats_text or text)),
            "has_payoff": bool(payoff_re.search(beats_text or text)),
            "spectacle": bool(SPECTACLE_RE.search(text)),
            "spectacle_head": bool(SPECTACLE_RE.search(text[:180])),
            "spectacle_tail": bool(SPECTACLE_RE.search(tail_for_strength)),
            "source_kind": source_kind(root) if main_node else "",
            "structured_main_node": structured_main_node,
            "explicit_hook": explicit_hook,
        })
    for r in rows:
        r["closed_loop"] = r["has_conflict"] and r["has_payoff"]
    return rows


def enrich_episode_rows(rows):
    """Attach deterministic per-episode risk flags/advice.

    Shared by the CLI and boundary_review.py so the structured signoff tracks
    exactly the same risk model as boundary_audit strict mode.
    """
    has_risk = False
    per_ep = []
    for r in rows:
        flags_e, advice, risk_codes = [], [], []
        risk = False
        if r["chars"] < 650:
            flags_e.append("短(提示)")
            advice.append("可保留短集，核闭环完整")
        if r["chars"] > 1100:
            flags_e.append("长(提示)")
            advice.append("可保留长集，核中段钩子密度")
        if r["soft_end"]:
            flags_e.append("软断")
            advice.append("右边界后移到完整钩子")
            risk_codes.append("soft_end")
            risk = True
        if not r["chapter"]:
            flags_e.append("章内续切")
            risk_codes.append("chapter_inside_continuation")
            risk = True
        if r["strength"] <= 0:
            flags_e.append("弱钩待判")
            advice.append("精修时补强集尾钩")
            risk_codes.append("weak_episode_end")
            risk = True
        if not r["closed_loop"]:
            miss = "缺冲突" if not r["has_conflict"] else "缺爽点/反转"
            flags_e.append(f"无闭环({miss})")
            advice.append("复核并入相邻集或补闭环(P1)")
            risk_codes.append("no_closed_loop")
            risk = True
        if risk:
            has_risk = True
        per_ep.append({**r, "risk": risk, "risk_codes": risk_codes, "flags": flags_e, "advice": advice})
    return per_ep, has_risk


def _boundary_contract(rows: Sequence[Dict[str, Any]], from_ep: int, to_ep: Optional[int]) -> Dict[str, Any]:
    """Bind a boundary finding to both adjacent raw files, not only one episode."""
    by_ep = {int(r["ep"]): r for r in rows}
    left = by_ep.get(int(from_ep)) or {}
    right = by_ep.get(int(to_ep)) if to_ep is not None else {}
    boundary_id = f"E{int(from_ep):04d}-" + (f"E{int(to_ep):04d}" if to_ep is not None else "END")
    left_sha = str(left.get("raw_sha256") or "")
    right_sha = str((right or {}).get("raw_sha256") or "")
    digest = hashlib.sha256(f"{boundary_id}\0{left_sha}\0{right_sha}".encode("utf-8")).hexdigest()
    return {
        "boundary_id": boundary_id,
        "from_episode": int(from_ep),
        "to_episode": int(to_ep) if to_ep is not None else None,
        "left_raw_rel": left.get("raw_rel"),
        "right_raw_rel": (right or {}).get("raw_rel"),
        "left_raw_sha256": left_sha,
        "right_raw_sha256": right_sha,
        "contract_sha256": digest,
    }


def _blocker(code: str, message: str, contract: Dict[str, Any], **extra: Any) -> Dict[str, Any]:
    return {
        "severity": "block",
        "code": code,
        "blocker_id": f"{contract['boundary_id']}:{code}",
        "message": message,
        "boundary_contract": contract,
        **extra,
    }


def build_blockers(
    all_rows: Sequence[Dict[str, Any]],
    per_ep: Sequence[Dict[str, Any]],
    arc: Dict[str, Any],
    *,
    scope_eps: Optional[Iterable[int]] = None,
) -> List[Dict[str, Any]]:
    """Return deterministic, code-addressable strict blockers.

    The series curve is always computed from ``all_rows``. ``scope_eps`` only
    limits which boundary contracts the caller wants to sign off in this run.
    """
    scope = {int(v) for v in scope_eps} if scope_eps is not None else None
    ordered_eps = [int(r["ep"]) for r in all_rows]
    next_by_ep = {ep: (ordered_eps[i + 1] if i + 1 < len(ordered_eps) else None)
                  for i, ep in enumerate(ordered_eps)}

    def in_scope(a: int, b: Optional[int]) -> bool:
        return scope is None or a in scope or (b is not None and b in scope)

    messages = {
        "soft_end": "右边界停在逗号/分号等软断，需移动到完整戏剧断点。",
        "chapter_inside_continuation": "机器粗胚在章内续切，需复核场景/事件是否被切断。",
        "weak_episode_end": "上集收口无可验证的语义钩或悬念断点。",
        "no_closed_loop": "本集缺冲突→兑现/反转闭环，疑似纯铺垫集。",
    }
    blockers: List[Dict[str, Any]] = []
    for row in per_ep:
        ep = int(row["ep"])
        nxt = next_by_ep.get(ep)
        if not in_scope(ep, nxt):
            continue
        contract = _boundary_contract(all_rows, ep, nxt)
        for code in row.get("risk_codes") or []:
            blockers.append(_blocker(code, messages[code], contract, episode=f"第{ep}集"))

    # P2 is co-equal with the previous ending: a weak next opening is a strict
    # boundary blocker even if both standalone episode rows otherwise look fine.
    for pair in arc.get("boundary_pairs") or []:
        a, b = int(pair["from"]), int(pair["to"])
        if int(pair.get("next_start_strength") or 0) > 0 or not in_scope(a, b):
            continue
        contract = _boundary_contract(all_rows, a, b)
        blockers.append(_blocker(
            "weak_next_opening",
            "下集 0-3 秒开场无冲突/悬念/兑现承接，双侧边界不成立。",
            contract,
            episode=f"第{b}集",
        ))

    for ep in arc.get("weak_paywalls") or []:
        ep = int(ep)
        nxt = next_by_ep.get(ep)
        if not in_scope(ep, nxt):
            continue
        contract = _boundary_contract(all_rows, ep, nxt)
        blockers.append(_blocker(
            "weak_configured_paywall",
            "项目显式配置的付费/解锁卡点断点强度不足。",
            contract,
            episode=f"第{ep}集",
            policy_source=(arc.get("paywall_policy") or {}).get("source"),
        ))
    return sorted(blockers, key=lambda b: (b["boundary_contract"]["from_episode"], b["code"]))


def weak_clusters(rows, threshold=0):
    """相邻弱钩(strength<=threshold)集群：≥2 连为流失高风险段。"""
    clusters, cur = [], []
    for r in rows:
        if r["strength"] <= threshold:
            cur.append(r["ep"])
        else:
            if len(cur) >= 2:
                clusters.append((cur[0], cur[-1]))
            cur = []
    if len(cur) >= 2:
        clusters.append((cur[0], cur[-1]))
    return clusters


def _parse_episode_numbers(value: Any) -> List[int]:
    if isinstance(value, list):
        values = value
    else:
        values = re.findall(r"\d+", str(value or ""))
    out = []
    for item in values:
        m = re.search(r"\d+", str(item))
        if m and int(m.group()) > 0 and int(m.group()) not in out:
            out.append(int(m.group()))
    return sorted(out)


def load_paywall_policy(root: str, monet: str) -> Dict[str, Any]:
    """Read explicit project paywall/unlock points.

    There is no universal episode 8/10 wall. A paid/overseas project only gets
    hard paywall blockers when its platform/contract/first-party policy names
    concrete episodes. Unknown policy stays advisory.
    """
    if monet == "免费":
        return {"status": "not_applicable", "episodes": [], "source": "monetization=免费"}

    json_path = Path(root) / "脚本" / "paywall_policy.json"
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        eps = _parse_episode_numbers(
            data.get("paywall_after_episode") or data.get("paywall_episodes") or data.get("unlock_points")
        )
        if eps:
            return {
                "status": "configured",
                "episodes": eps,
                "source": str(json_path.relative_to(Path(root))),
                "evidence_ref": data.get("evidence_ref") or data.get("platform_contract_ref") or "",
            }

    settings_path = Path(root) / "_设置.md"
    if settings_path.exists():
        text = settings_path.read_text(encoding="utf-8", errors="replace")
        for key in ("付费卡点集", "付费墙集", "解锁卡点集", "paywall_after_episode", "paywall_episodes"):
            match = re.search(rf"^\s*[-*]?\s*{re.escape(key)}\s*[:：]\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
            if not match:
                match = re.search(
                    rf"^\s*\|\s*{re.escape(key)}\s*\|\s*([^|]+)\|",
                    text,
                    re.MULTILINE | re.IGNORECASE,
                )
            eps = _parse_episode_numbers(match.group(1)) if match else []
            if eps:
                return {"status": "configured", "episodes": eps, "source": f"_设置.md:{key}", "evidence_ref": ""}
    return {
        "status": "unknown",
        "episodes": [],
        "source": "",
        "advisory": "付费/海外项目尚未配置平台或发行合同给出的付费/解锁卡点；不猜第8/10集，不作硬门。",
    }


def cliffhanger_positions(rows, monet, configured_targets=None):
    """Return explicit project paywall targets; never invent universal positions."""
    eps = [r["ep"] for r in rows]
    if not eps:
        return []
    if monet == "免费":
        return []
    available = set(eps)
    return [n for n in _parse_episode_numbers(configured_targets) if n in available]


def weak_paywalls(rows, monet, configured_targets=None):
    """Configured paid/unlock points whose ending evidence is below strong.

    Free mode and unknown paid policies return an empty list. Only explicit
    project targets may become strict blockers.
    """
    if monet == "免费":
        return []
    by_ep = {r["ep"]: r for r in rows}
    return [w for w in cliffhanger_positions(rows, monet, configured_targets)
            if w in by_ep and by_ep[w]["strength"] < 2]


def boundary_pairs(rows):
    """相邻两集双侧边界评分：上集收尾强度 + 下集开场承接力。"""
    pairs = []
    for prev, nxt in zip(rows, rows[1:]):
        weakness = []
        if prev["strength"] <= 0:
            weakness.append("上集收口弱")
        if nxt["start_strength"] <= 0:
            weakness.append("下集开场弱")
        score = prev["strength"] + nxt["start_strength"]
        pairs.append({
            "from": prev["ep"],
            "to": nxt["ep"],
            "end_strength": prev["strength"],
            "next_start_strength": nxt["start_strength"],
            "score": score,
            "label": PAIR_STRENGTH_LABEL.get(score, "弱"),
            "risk": bool(weakness),
            "weakness": weakness,
        })
    return pairs


def spectacle_placement(rows):
    """视觉奇观放置初筛（report-only·北极星看点④）。

    只 flag 两种确定性模式，不替代人判、不进 strict 闸：
      ① 奇观跨集劈半——上集尾 + 下集头同含奇观词（同一场面横跨切点）。
      ② 奇观集断点弱——含奇观但集尾断点强度 < 强（奇观没收在集尾高潮位，疑埋中段未当锚点）。
    仅"含奇观词"本身不报（避免噪声）；只有出现上述放置问题才提示。
    """
    out = {"spectacle_eps": [], "split_boundary": [], "weak_anchor": [], "issues": []}
    out["spectacle_eps"] = [r["ep"] for r in rows if r["spectacle"]]
    for prev, nxt in zip(rows, rows[1:]):
        if prev["spectacle_tail"] and nxt["spectacle_head"]:
            out["split_boundary"].append((prev["ep"], nxt["ep"]))
    out["weak_anchor"] = [r["ep"] for r in rows if r["spectacle"] and r["strength"] < 2]
    if out["split_boundary"]:
        brief = "、".join(f"第{a}→{b}集" for a, b in out["split_boundary"][:8])
        out["issues"].append(
            f"视觉奇观疑似被切点劈成两半：{brief}。确认是否有意跨集（上集'憋'+下集'放'）；"
            "若非有意，把整场奇观收进一集或切在奇观前/后，别把一个高潮场面劈散（P1）")
    if out["weak_anchor"]:
        eps = "、".join(f"第{e}集" for e in out["weak_anchor"][:12])
        out["issues"].append(
            f"奇观集断点偏弱：{eps}{'…' if len(out['weak_anchor']) > 12 else ''}。"
            "含大战/渡劫/觉醒/万人场等视觉高潮却没收在集尾高潮位——奇观是 AI 漫剧差异点，"
            "建议放到集尾当整集锚点、别埋在中段（北极星看点④）")
    return out


def series_arc(rows, monet, paywall_policy=None):
    """剧级追更骨架体检（Gap1）。返回结构化 dict + 人读建议行。"""
    out = {"monetization": monet, "issues": [], "notes": []}
    if not rows:
        return out
    out["spectacle"] = spectacle_placement(rows)  # report-only·北极星看点④
    dist = {2: 0, 1: 0, 0: 0}
    for r in rows:
        dist[r["strength"]] += 1
    out["strength_dist"] = {STRENGTH_LABEL[k]: v for k, v in dist.items()}

    pairs = boundary_pairs(rows)
    out["boundary_pairs"] = pairs
    risky_pairs = [p for p in pairs if p["risk"]]
    if risky_pairs:
        brief = "；".join(
            f"第{p['from']}→{p['to']}集({'+'.join(p['weakness'])})" for p in risky_pairs[:8]
        )
        out["issues"].append(
            f"双侧边界偏弱：{brief}{'…' if len(risky_pairs) > 8 else ''}。"
            "拆集不只看上集结尾，也要看下集 0-3 秒能否接住同一根戏剧线。"
        )

    # 连续弱钩集群（断点流失高风险）
    clusters = weak_clusters(rows)
    out["weak_clusters"] = clusters
    for a, b in clusters:
        out["issues"].append(f"连续弱钩集群 第{a}-{b}集：断点平→观众易划走，并入相邻强断点集或补强集尾钩")

    # 无闭环集（P1·纯铺垫嫌疑）
    no_loop = [r["ep"] for r in rows if not r["closed_loop"]]
    out["no_closed_loop"] = no_loop
    if no_loop:
        out["issues"].append(
            f"疑似无闭环/纯铺垫集 第{'、'.join(map(str, no_loop[:12]))}集"
            f"{'…' if len(no_loop) > 12 else ''}：缺冲突或缺爽点/反转，复核是否并入相邻集（P1）")

    # 开篇集群钩子梯度（首 N 集留存投资）
    head_n = min(4, len(rows))
    head = rows[:head_n]
    weak_head = [r["ep"] for r in head if r["strength"] <= 0]
    out["opening_cluster"] = [r["ep"] for r in head]
    if weak_head:
        out["issues"].append(
            f"开篇集群第{'、'.join(map(str, weak_head))}集弱钩：前{head_n}集是留存投资最高区，"
            f"应世界观+主角欲望+系列总钩立稳；实际阈值按项目反馈校准（P6）")
    out["notes"].append(f"开篇集群=前{head_n}集（首集须扛 世界观+主角欲望+系列总钩，最该加权）")

    # 变现卡点只消费项目显式策略，不从模式名称推断集号。
    paywall_policy = paywall_policy or {
        "status": "unknown" if monet != "免费" else "not_applicable",
        "episodes": [],
        "source": "",
    }
    out["paywall_policy"] = paywall_policy
    walls = cliffhanger_positions(rows, monet, paywall_policy.get("episodes"))
    out["cliffhanger_targets"] = walls
    weak_walls = weak_paywalls(rows, monet, paywall_policy.get("episodes"))
    out["weak_paywalls"] = weak_walls  # G3·付费/海外档进 strict 闸（免费档恒空）
    if monet == "免费":
        out["notes"].append("变现=免费：完播率导向，要全剧延续性、断点平均强；不设单点付费墙，重点消灭连续弱钩集群")
    else:
        if paywall_policy.get("status") != "configured":
            out["notes"].append(str(paywall_policy.get("advisory") or "未配置付费/解锁卡点；保持建议态，不作硬门"))
        if weak_walls:
            out["issues"].append(
                f"变现={monet} 卡点集第{'、'.join(map(str, weak_walls))}集断点不够强（付费墙/续费点应是最强 cliffhanger）")
        if walls:
            out["notes"].append(
                f"变现={monet}：项目配置的付费/解锁卡点（{'、'.join(map(str, walls))}）须最强断点；"
                f"来源={paywall_policy.get('source') or '未记录'}")
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    strict = "--strict" in flags
    as_json = "--json" in flags
    if not args:
        print("用法: boundary_audit.py <作品根> [start-end] [--strict] [--json]")
        sys.exit(2)
    root = args[0]
    genre = get_setting(root, "题材", "")
    monet = get_setting(root, "变现模式", "免费") or "免费"
    buckets = boundary_buckets(genre)
    strong_re, conflict_re, payoff_re = build_res(genre)

    all_rows = load_rows(root, strong_re, conflict_re, payoff_re)
    if not all_rows:
        print("未找到 脚本/第N集/raw.txt")
        sys.exit(1)
    rows = list(all_rows)
    if len(args) >= 2:
        m = re.match(r"(\d+)-(\d+)$", args[1])
        if not m:
            print("范围格式应为 start-end，例如 2-10")
            sys.exit(2)
        a, b = map(int, m.groups())
        rows = [r for r in rows if a <= r["ep"] <= b]

    # 剧级曲线永远看全局 rows；命令范围只限制本轮逐集/边界签收，避免
    # `2-10` 把第2集误当开篇、也避免局部窗口扭曲全剧弱钩分布。
    paywall_policy = load_paywall_policy(root, monet)
    arc = series_arc(all_rows, monet, paywall_policy)
    per_ep, episode_has_risk = enrich_episode_rows(rows)
    blockers = build_blockers(all_rows, per_ep, arc, scope_eps=[r["ep"] for r in rows])
    weak_pw = sorted({b["boundary_contract"]["from_episode"] for b in blockers
                      if b["code"] == "weak_configured_paywall"})
    strict_block = bool(blockers)
    has_risk = strict_block

    if as_json:
        print(json.dumps({"genre": genre, "buckets": buckets, "series_arc": arc,
                          "episodes": per_ep, "has_risk": has_risk,
                          "episode_heuristic_risk": episode_has_risk,
                          "series_arc_scope": "global", "scope_episodes": [r["ep"] for r in rows],
                          "blockers": blockers, "weak_paywalls": weak_pw,
                          "strict_block": strict_block},
                         ensure_ascii=False, indent=2))
        sys.exit(1 if (strict and strict_block) else 0)

    chars = [r["chars"] for r in rows]
    print(f"题材词典：{(genre or '未设')}→{'/'.join(buckets)}　变现模式：{monet}")
    print(f"episodes={len(rows)} chars_min={min(chars)} chars_max={max(chars)} "
          f"chars_avg={statistics.mean(chars):.1f} chars_median={statistics.median(chars):.0f}")
    print()
    print("| 集 | 字数 | 章头 | 断点 | 标记 | 处理建议 |")
    print("|---|---:|---|:--:|---|---|")
    for r in per_ep:
        print(f"| 第{r['ep']}集 | {r['chars']} | {'是' if r['chapter'] else '否'} | "
              f"{STRENGTH_LABEL[r['strength']]} | {'、'.join(r['flags']) or 'OK'} | "
              f"{'；'.join(r['advice']) or '保留'} |")

    print()
    print("## 剧级追更骨架（Gap1·跨集留存体检）")
    d = arc["strength_dist"]
    print(f"- 断点强度分布：强 {d['强']} / 中 {d['中']} / 弱 {d['弱']}")
    pairs = arc.get("boundary_pairs") or []
    if pairs:
        pd = {"强": 0, "中": 0, "弱": 0}
        for p in pairs:
            pd[p.get("label", "弱")] = pd.get(p.get("label", "弱"), 0) + 1
        print(f"- 双侧边界评分：强 {pd['强']} / 中 {pd['中']} / 弱 {pd['弱']}（上集收尾 + 下集开场）")
    if arc["issues"]:
        for it in arc["issues"]:
            print(f"- ⚠️ {it}")
    else:
        print("- ✅ 未发现连续弱钩集群 / 无闭环集 / 卡点偏弱")
    sp = arc.get("spectacle") or {}
    if sp.get("issues"):
        for it in sp["issues"]:
            print(f"- 🎬 {it}")
    elif sp.get("spectacle_eps"):
        print(f"- 🎬 视觉奇观集：第{'、'.join(map(str, sp['spectacle_eps']))}集"
              "（已作集锚点，未见劈半/弱锚点 · 北极星看点④）")
    for note in arc["notes"]:
        print(f"- ℹ️ {note}")
    print("> 方法论见 references/追更骨架.md；逐集集内留存见 n2d/references/导演节奏.md。")

    if strict and strict_block:
        if weak_pw:
            print(f"\n⛔ boundary_audit strict: 变现={monet} 付费墙/续费卡点集第{'、'.join(map(str, weak_pw))}集断点不够强"
                  "（付费墙须全剧最强 cliffhanger）；精修这些集的集尾断点（危机悬置/反转预告）再继续。")
        if blockers:
            print("\n⛔ boundary_audit strict: 存在高风险粗胚边界；先做 5-10 集窗口复核并写 脚本/_拆集复核.md。")
        sys.exit(1)


if __name__ == "__main__":
    main()
