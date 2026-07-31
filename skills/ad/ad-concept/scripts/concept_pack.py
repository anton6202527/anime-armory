#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""创意包机器真值（创意/concept.json）的定义与校验 —— ad 线编剧轴 P0 enabler。

为什么存在：
    ad-concept 此前**只产 markdown**（`创意/concept.md` + `创意/创意脚本.md`），全线没有一份
    结构化的创意真值。后果有三层，都是实证空档不是假想：
      ① 唯一的验收（`ad-craft/stage_acceptance.accept_concept`）是「5 个关键词在 concept.md +
         创意脚本.md 拼接全文里出现过就算通过」，别名甚至含「为什么」——中文创意稿几乎必然命中，
         等于形同虚设；
      ② `ad-craft/producer_pack.build_pack` 只能用正则 `_extract_section(concept, "Big Idea")`
         把 Big Idea 段落**抄进 pack**，标题一改就抠空；
      ③ 下游（分镜/出图/评分）想问「这一镜兑现了哪个卖点」时无处可问——没有 id 可绑。
    本脚本定义 concept.json 这个真值，并做**校验**，让 `ad-script/scripts/idea_payoff_ledger.py`
    能拿 id 对账「创意承诺 → 分镜兑现」。

治什么根因：
    「big idea / key message 定完就没人管」——主张没有机器可读的身份（id），就没有任何东西能
    回头核对它有没有被兑现、有没有被临时加戏顶掉。先有真值，才谈得上对账。

设计取舍（与本线既有纪律一致）：
    concept.json **由 AI 写、本脚本只校验**。ad-concept 已经在用「AI 问人话 → 自己落 JSON」的
    模式写 `需求/brief.json`（见 SKILL.md 第0步 + 常见错误表「让用户自己填 brief.json」），
    创意包沿用同一模式。**刻意不写正则从 concept.md 抠字段**——`producer_pack._extract_section`
    那套已经被证明脆弱（依赖 `## Big Idea` 标题字面），再造一份只是把脆弱复制一遍。

诚实边界：
    - 缺 `创意/concept.json` → `available=false` + warn（建议 ad-concept 落 concept.json），
      **不崩、不臆造通过**。ad-concept 尚未落这份档的存量项目不该被本脚本打死。
    - 结构性判据（必填缺失/占位/usps 空）是确定性的 → block；
      语义性判据（objective 与 brief 不一致、SMP 稀释、秒数合计对不上）交人判 → warn/info。
    - 阈值全是**内部启发式**（`provenance: internal-heuristic·confidence=low`），env 可标定，
      不冒充行业标准数值。
    - 默认 exit 0（本脚本是「审」不是「门」）；`--strict` 且 block>0 才 exit 1。

单一主张聚焦（SMP）判据的依据 —— 为什么不是「卖点多就报」：
    广告 doctrine「Single-Minded Proposition」：一条广告只讲一个主张，塞满 feature 会稀释记忆。
    但可查的量化证据（healthcare 领域 1059 个产品的研究）指向一个更精确的结论：多个**相关**卖点
    → 销量 +42%；多个**不相关**卖点 → 订单量 **-66%**（vs 单卖点）。**该拦的不是「卖点多」，
    是「卖点与主张不相关」**。所以判据落在 `supports_key_message=false` 的条目数上，而不是
    `len(usps)` 上。上述数字是**领域研究结论、不是本仓阈值**——本脚本的阈值（2 / 4）是据此
    方向性设定的内部启发式，confidence=low，只 warn 不 block。

用法：
    cd skills/ad/ad-concept/scripts
    python3 concept_pack.py <作品根> [--write] [--json] [--strict]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

VERSION = 1
KIND = "ad_concept_pack_check"
PACK_KIND = "ad_concept_pack"
PACK_REL = os.path.join("创意", "concept.json")
REPORT_REL = os.path.join("生产数据", "ad_concept_pack_check.json")

# 本线自包含：读 _设置.md 走 ad 线 vendored 的 settings 助手（与 ad-craft/gate.py 同法）。
_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB_DIR = os.path.abspath(os.path.join(_HERE, "..", "..", "_lib"))
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)
try:
    import settings as _settings  # noqa: E402
except Exception:  # pragma: no cover - settings 助手缺失时回退正则
    _settings = None

# 占位口径与 ad-craft/gate.py:32 `_PENDING_TOKENS` 同源（本线自包含·复制不 import）。
PENDING_TOKENS = {"", "未记录", "待补", "待填", "待填写", "tbd", "todo", "未填", "未定", "n/a"}
_PLACEHOLDER_RE = re.compile(r"待补|待填|TODO|TBD|^<.*>$|^__", re.IGNORECASE)

# 必填字段：缺一，下游就有一整类问题无从对账。
REQUIRED_FIELDS = ("big_idea", "key_message", "creative_route", "objective", "hypothesis", "kv_direction")

# ── 阈值（内部启发式·env 可标定·confidence=low） ───────────────────────────────
# 不相关卖点条目数达到这个数 → 稀释告警（SMP：见 docstring 的依据说明）。
UNRELATED_USP_WARN = int(os.environ.get("AD_CONCEPT_UNRELATED_USP_WARN", "2"))
# 卖点总数超过这个数 **且**存在不相关条目 → 升告警（多而杂 > 多而相关）。
USP_TOTAL_WARN = int(os.environ.get("AD_CONCEPT_USP_TOTAL_WARN", "4"))
# storyline 秒数合计 vs 主片时长的相对容差（广告总时长是硬约束，但创意期只是段落级预算 → warn）。
STORYLINE_TOLERANCE_RATIO = float(os.environ.get("AD_CONCEPT_STORYLINE_TOL", "0.2"))

PROVENANCE = "internal-heuristic·confidence=low"


# ── 纯函数（无 IO·可测） ──────────────────────────────────────────────────────

def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def finding(severity: str, code: str, msg: str) -> Dict[str, str]:
    """ad gate 消费的是 `msg` 键（见 ad-craft/gate.py:52 `finding()`），不是 `message`。"""
    return {"severity": severity, "code": code, "msg": msg}


def is_pending(value: Any) -> bool:
    """空 / 占位（待补·TBD·<...>）判定。纯函数·可测。"""
    if value is None:
        return True
    if isinstance(value, str):
        raw = value.strip()
        if raw.lower() in PENDING_TOKENS:
            return True
        return bool(_PLACEHOLDER_RE.search(raw))
    if isinstance(value, (list, tuple, dict)):
        return not value
    return False


def normalize_objective(value: str) -> str:
    """目标口径归一化：去空白 + 小写，用于 concept↔brief 比对。纯函数·可测。"""
    return re.sub(r"\s+", "", str(value or "")).lower()


def parse_seconds(label: Any) -> Optional[float]:
    """'30s' / '15' / '自定义(45s)' → 45.0；解析不出返回 None。纯函数·可测。"""
    raw = str(label or "").strip()
    if not raw:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", raw)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def usp_rows(pack: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """`usps[]` 归一化成 [{id, text, supports_key_message, claim_id}]。纯函数·可测。

    容错：既接受结构化 dict，也接受历史/手写的纯字符串条目（此时 supports_key_message 未声明
    → 按 None 记，不臆造 true 也不臆造 false）。"""
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(pack.get("usps") or [], 1):
        if isinstance(item, Mapping):
            out.append({
                "id": str(item.get("id") or f"USP_{i:02d}"),
                "text": str(item.get("text") or "").strip(),
                "supports_key_message": item.get("supports_key_message"),
                "claim_id": str(item.get("claim_id") or "").strip(),
            })
        elif str(item or "").strip():
            out.append({"id": f"USP_{i:02d}", "text": str(item).strip(),
                        "supports_key_message": None, "claim_id": ""})
    return out


def unrelated_usps(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """`supports_key_message` **显式为 false** 的条目。纯函数·可测。

    未声明（None）不算不相关——缺料不臆造。缺声明本身另有 warn（见 check_usps）。"""
    return [dict(r) for r in rows if r.get("supports_key_message") is False]


def check_required(pack: Mapping[str, Any]) -> List[Dict[str, str]]:
    """必填字段缺失/为空/仍是占位 → block（结构性判据，确定性）。纯函数·可测。"""
    out: List[Dict[str, str]] = []
    for key in REQUIRED_FIELDS:
        if key not in pack:
            out.append(finding("block", "concept_field_missing",
                               f"concept.json 缺必填字段 `{key}`——下游无法对账该承诺，补齐后复跑。"))
        elif is_pending(pack.get(key)):
            out.append(finding("block", "concept_field_pending",
                               f"concept.json 字段 `{key}` 为空或仍是占位（{str(pack.get(key))[:20]!r}）"
                               "——创意定稿前必须落定，占位会被 producer_pack 原样抄进制片包。"))
    return out


def check_objective(pack: Mapping[str, Any], brief: Optional[Mapping[str, Any]]) -> List[Dict[str, str]]:
    """concept.objective 必须与 brief.campaign_objective 一致。纯函数·可测。

    不一致 → warn（可能是 brief 后改、也可能是创意跑偏，机器分不出，交人判）。
    brief 缺失/未填 → info + insufficient_data（不臆造通过）。"""
    concept_obj = str(pack.get("objective") or "").strip()
    if is_pending(concept_obj):
        return []  # 已由 check_required 报过，不重复
    if brief is None:
        return [finding("info", "objective_brief_unavailable",
                        "缺 需求/brief.json，无法核对 objective 是否与 campaign_objective 一致"
                        "（insufficient_data）。")]
    brief_obj = str(brief.get("campaign_objective") or "").strip()
    if is_pending(brief_obj):
        return [finding("info", "objective_brief_unavailable",
                        "brief.json 的 campaign_objective 未填/占位，无法核对一致性（insufficient_data）。")]
    if normalize_objective(concept_obj) != normalize_objective(brief_obj):
        return [finding("warn", "objective_brief_mismatch",
                        f"concept.objective『{concept_obj}』≠ brief.campaign_objective『{brief_obj}』"
                        "——目标不同则品牌露出/产品演示/CTA 比重都该不同；确认是 brief 后改（同步 concept）"
                        "还是创意跑偏（改回来）。")]
    return []


def check_usps(pack: Mapping[str, Any], brief: Optional[Mapping[str, Any]] = None) -> List[Dict[str, str]]:
    """卖点结构 + 单一主张聚焦(SMP) 稀释检查。纯函数·可测。

    判据依据见模块 docstring：拦的是**不相关卖点**，不是「卖点多」。全部 warn，绝不 block——
    「这个卖点支不支持主张」是创意判断，机器只按 AI 自己登记的 supports_key_message 复述。"""
    rows = usp_rows(pack)
    out: List[Dict[str, str]] = []
    if not rows:
        out.append(finding("block", "usps_empty",
                           "concept.json 的 usps[] 为空——没有登记卖点，下游 idea_payoff_ledger 无从对账"
                           "「哪一镜兑现了哪个卖点」，且分镜里出现的任何卖点都成了无据加戏。"))
        return out

    undeclared = [r for r in rows if r.get("supports_key_message") is None]
    if undeclared:
        out.append(finding("warn", "usp_support_undeclared",
                           f"{len(undeclared)}/{len(rows)} 个卖点未声明 supports_key_message"
                           f"（{'、'.join(r['id'] for r in undeclared[:4])}）——"
                           "无法判断它们服务主张还是稀释主张；逐条标 true/false。"))

    declared = [r for r in rows if r.get("supports_key_message") is not None]
    if declared and not any(r.get("supports_key_message") for r in declared):
        out.append(finding("warn", "usp_none_supports_key_message",
                           "所有已声明的卖点 supports_key_message 全为 false——一句话主张没有任何卖点支撑，"
                           "要么主张选错、要么卖点选错，二者必改其一。"))

    unrelated = unrelated_usps(rows)
    if len(unrelated) >= UNRELATED_USP_WARN:
        out.append(finding("warn", "usp_unrelated_dilution",
                           f"{len(unrelated)} 个卖点声明与主张不相关（{'、'.join(r['id'] for r in unrelated[:4])}）"
                           f"，达到内部阈值 {UNRELATED_USP_WARN}——业界证据方向：多个**相关**卖点提升效果，"
                           "多个**不相关**卖点显著拖累转化（稀释主张）。删掉不相关项，或改写让它们服务主张。"))
    if len(rows) > USP_TOTAL_WARN and unrelated:
        out.append(finding("warn", "usp_overload_with_unrelated",
                           f"卖点共 {len(rows)} 条（超内部阈值 {USP_TOTAL_WARN}）且其中 {len(unrelated)} 条与主张不相关"
                           "——Single-Minded Proposition：一条广告只讲一个主张。先砍不相关项，再考虑合并同类项。"))

    if brief is not None:
        claim_ids = {str((c or {}).get("id") or "").strip()
                     for c in (brief.get("claims") or []) if isinstance(c, Mapping)}
        claim_ids.discard("")
        for r in rows:
            if r.get("claim_id") and claim_ids and r["claim_id"] not in claim_ids:
                out.append(finding("info", "usp_claim_id_unknown",
                                   f"卖点 {r['id']} 的 claim_id『{r['claim_id']}』不在 brief.claims[] 里"
                                   "——功效/数据类宣称需要有依据的 claim 支撑，核对 id 或去 brief 补登记。"))
    return out


def check_storyline(pack: Mapping[str, Any], master_seconds: Optional[float]) -> List[Dict[str, str]]:
    """故事线秒数预算 vs 主片时长。纯函数·可测。

    只 warn：创意期是**段落级**预算（给 ad-script 当时间轴种子），不是定稿镜头时长；
    真正的总时长硬约束在 `ad-script/finalize_storyboard.py` 用实测 VO 时长对账。这里重复硬拦
    只会在创意期误杀。"""
    beats = [b for b in (pack.get("storyline") or []) if isinstance(b, Mapping)]
    out: List[Dict[str, str]] = []
    if not beats:
        out.append(finding("warn", "storyline_empty",
                           "concept.json 的 storyline[] 为空——没有段落级故事线，ad-script 拆镜头时"
                           "没有时间轴种子，钩子/痛点/卖点/CTA 的秒数分配无从继承。"))
        return out
    total = 0.0
    unbudgeted = []
    for i, beat in enumerate(beats, 1):
        sec = beat.get("planned_seconds")
        try:
            total += float(sec or 0)
        except (TypeError, ValueError):
            unbudgeted.append(str(beat.get("section") or f"#{i}"))
            continue
        if not sec:
            unbudgeted.append(str(beat.get("section") or f"#{i}"))
    if unbudgeted:
        out.append(finding("warn", "storyline_seconds_missing",
                           f"故事线段落 {'、'.join(unbudgeted[:5])} 没有 planned_seconds——"
                           "每段给秒数预算才能当 ad-script 的时间轴种子。"))
    if master_seconds is None:
        out.append(finding("info", "master_duration_unavailable",
                           "_设置.md 无「主片时长」，跳过故事线秒数合计对账（insufficient_data）。"))
        return out
    tol = max(1.0, master_seconds * STORYLINE_TOLERANCE_RATIO)
    if abs(total - master_seconds) > tol:
        out.append(finding("warn", "storyline_seconds_mismatch",
                           f"故事线秒数合计 {total:.1f}s 与主片时长 {master_seconds:.0f}s 差 "
                           f"{total - master_seconds:+.1f}s（内部容差 ±{tol:.1f}s）——"
                           "广告总时长是硬约束，创意期就把段落预算调平，别把超时留给分镜期砍戏。"))
    return out


# ── IO（best-effort·缺则 None） ───────────────────────────────────────────────

def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_pack(root: Path) -> Optional[Dict[str, Any]]:
    data = load_json(root / PACK_REL)
    return data if isinstance(data, dict) else None


def load_brief(root: Path) -> Optional[Dict[str, Any]]:
    data = load_json(root / "需求" / "brief.json")
    return data if isinstance(data, dict) else None


def master_seconds(root: Path) -> Optional[float]:
    """读 _设置.md 的「主片时长」。settings 助手优先，缺失时正则兜底。"""
    if _settings is not None:
        try:
            value = _settings.get_setting(str(root), "主片时长", "")
            sec = parse_seconds(value)
            if sec:
                return sec
        except Exception:
            pass
    try:
        text = (root / "_设置.md").read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r"主片时长[^\n]*?(\d+(?:\.\d+)?)\s*s", text)
    return float(m.group(1)) if m else None


def build(root: Path) -> Dict[str, Any]:
    """契约形状（ad gate 可直接消费；findings 用 `msg` 键）：

        {"schema_version":1,"kind":"ad_concept_pack_check","available":bool,
         "summary":{"block","warn","info"},"findings":[{"severity","code","msg"}]}
    """
    root = Path(root)
    pack = load_pack(root)
    brief = load_brief(root)
    findings: List[Dict[str, str]] = []
    available = pack is not None

    if not available:
        findings.append(finding("warn", "concept_pack_missing",
                                f"缺 {PACK_REL}——创意包没有机器真值，big idea/主张定完就无人对账"
                                "（stage_acceptance 的关键词检近乎必然通过，拦不住）。"
                                "建议 ad-concept 访谈完把创意结构化落 concept.json（别让用户自己填）。"))
    else:
        kind = str(pack.get("kind") or "")
        if kind and kind != PACK_KIND:
            findings.append(finding("warn", "concept_pack_kind_unexpected",
                                    f"concept.json 的 kind=『{kind}』，期望『{PACK_KIND}』——确认这是创意包而非别的产物。"))
        findings.extend(check_required(pack))
        findings.extend(check_objective(pack, brief))
        findings.extend(check_usps(pack, brief))
        findings.extend(check_storyline(pack, master_seconds(root)))

    return {
        "schema_version": VERSION,
        "kind": KIND,
        "available": available,
        "project_root": str(root),
        "generated_at": now_iso(),
        "pack_path": PACK_REL,
        "thresholds": {
            "unrelated_usp_warn": UNRELATED_USP_WARN,
            "usp_total_warn": USP_TOTAL_WARN,
            "storyline_tolerance_ratio": STORYLINE_TOLERANCE_RATIO,
            "provenance": PROVENANCE,
            "note": "SMP 稀释判据的方向来自广告 doctrine 与领域研究（相关卖点提升/不相关卖点拖累），"
                    "但这里的具体数值是内部启发式，不是行业标准值。",
        },
        "summary": {
            "block": sum(1 for f in findings if f["severity"] == "block"),
            "warn": sum(1 for f in findings if f["severity"] == "warn"),
            "info": sum(1 for f in findings if f["severity"] == "info"),
        },
        "findings": findings,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    lines = ["# 创意包机检 · concept.json", ""]
    if not report.get("available"):
        lines.append("- ⚠️ 未找到 `创意/concept.json`（available=false·降级为建议，不阻断）")
        lines.append("")
    lines.append(f"- block {s.get('block')} · warn {s.get('warn')} · info {s.get('info')}")
    lines.append("")
    icon = {"block": "⛔", "warn": "⚠️", "info": "ℹ️"}
    for f in report.get("findings") or []:
        lines.append(f"- {icon.get(f['severity'], '·')} `{f['code']}` {f['msg']}")
    if not report.get("findings"):
        lines.append("- ✅ 创意包结构完整、主张聚焦（仍需人审创意本身）")
    return "\n".join(lines) + "\n"


def write_report(root: Path, report: Mapping[str, Any]) -> None:
    path = root / REPORT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    path.with_suffix(".md").write_text(render_markdown(report), encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", help="作品根")
    ap.add_argument("--write", action="store_true", help=f"落盘 {REPORT_REL}（+ 同名 .md）")
    ap.add_argument("--json", action="store_true", help="打印 JSON 而非 markdown")
    ap.add_argument("--strict", action="store_true", help="block>0 时 exit 1（默认 exit 0：本检是审不是门）")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    report = build(root)
    if ns.write:
        write_report(root, report)
    print(json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report))
    return 1 if (ns.strict and report["summary"]["block"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
