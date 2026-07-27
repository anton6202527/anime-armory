#!/usr/bin/env python3
"""Clip economy planner: episode-level generation-count budget + merge-first proposals.

治「简单叙事被拆成太多付费视频 clip」：story_economy_audit 管单 Clip 时长预算，
本脚本管**集级生成次数**——统计当前 storyboard 会产生多少次付费生成（含镜位拆分与
长镜拆段），对照 2026 多镜叙事后端现实（单次生成可承载多个镜位：Seedance 2.0 单次
4-15s 一次 3-5 镜、Kling 3.0 multi-shot 单次 15s；采集日期 2026-07-22），给出：

  • 相邻同场景/同实体链的**合并候选组**（merge_or_single_take）：并成一个
    story_clip + `take_policy=single_take_multishot`，镜位切换交 multishot-native
    后端一次生成内部完成；
  • 弱信息微镜（compact/micro/montage 经济类）**并入相邻强戏**候选（fold_into_neighbor）；
  • 当前 vs 合并后的预计生成次数与密度指标。

宪法边界（B10）：全部启发式判定 report-only，findings 只到 warn 且标
`confidence=heuristic`，不做硬阻断；合并是否执行由编剧在阶段2精修时决定（改
storyboard 属签收产物变更，脚本不自动改写）。安全边界：命中高动作模板/已声明
锚链/超单次生成硬上限的 Clip 不进合并候选（与 shot_split_decision 的
single_take_policy_verdict 同口径，安全拆分优先于省次数）。

用法：python3 clip_economy_planner.py <作品根> <第N集> [--write] [--json] [--max-take-sec 15]
产物：生产数据/clip_economy_plan_第N集.json/md
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from shot_split_decision import (  # noqa: E402
    VIDEO_SHOT_HARD_MAX_SEC,
    clip_take_policy,
    duration_of,
    plan_video_shot_segments,
)

try:
    import story_economy_audit as sea  # type: ignore  # noqa: E402
except Exception:  # pragma: no cover - planner degrades to duration-only signals
    sea = None  # type: ignore

# 设置读取属同系列 n2d/_lib，缺失时降级为无设置（advisory），不让主流程崩。
_N2D_LIB = HERE.parent.parent / "n2d" / "_lib"
if str(_N2D_LIB) not in sys.path:
    sys.path.insert(0, str(_N2D_LIB))
try:
    from settings import load_settings  # type: ignore  # noqa: E402
except Exception:  # pragma: no cover
    def load_settings(work_root: str) -> Dict[str, str]:  # type: ignore
        return {}

KIND = "n2d_clip_economy_plan"
VERSION = 1

# 多镜叙事后端现实的快照参考（采集日期 2026-07-22·会过期，仅作报告口径，不做阻断阈值）：
# Seedance 2.0 单次 4-15s 且一次可承载 3-5 个镜头；Kling 3.0 multi-shot 单次 15s；
# Seedance 2.5 基础 30s（可延长）。简单叙事 1 分钟 ≈ 4-6 次生成是可达口径。
CAPABILITY_SNAPSHOT_DATE = "2026-07-22"
DEFAULT_MAX_TAKE_SEC = 15.0
DENSITY_WARN_PER_MIN = 10.0  # 兜底密度上限（复杂度未知/无时长时的旧口径），report-only

# ── 复杂度感知生成预算（治「简单叙事被拆成太多付费 clip」）──
# 简单叙事优先「更少更长的多镜单拍」，复杂/动作戏才配更高的每分钟生成密度。
# 每分钟预计付费生成次数上限，按叙事**广度**分档（heuristic·会随后端能力刷新）。
# 广度=场景数+角色数（简单叙事守在少数地点/人物）；动作密度另作预算加成（打斗合理需要更多镜位），
# 不把「一段打斗拆成几个 clip」误判成叙事复杂。
COMPLEXITY_BUDGET_PER_MIN = {
    "simple": 6.0,
    "standard": 9.0,
    "complex": 12.0,
}
ACTION_BUDGET_ALLOWANCE_PER_CLIP = 0.5  # 每个动作/奇观镜多给的每分钟生成额度
ACTION_BUDGET_ALLOWANCE_CAP = 2.0

# ── 绝对 clip 数预算（治「简单叙事 clip 数太多」的独立轴）──
# 上面的 takes/min 只治「一个 clip 拆几次付费生成」；治不了「本集被作者拆成太多 clip」。
# clip 数是在 storyboard 编排期就定死的（一节拍一 clip），后续省次数工具只并 take、不减 clip。
# 简单叙事应「更少更长的多镜单拍」——用每分钟 clip 数上限（按复杂度分档）单独把这条兜住。
COMPLEXITY_CLIP_BUDGET_PER_MIN = {
    "simple": 6.0,
    "standard": 8.0,
    "complex": 11.0,
}
# 「每个 clip 简短点」轴：clip 时长超单次生成窗口会被拆成多段付费 part。
# 一个 clip 被拆成 ≥ 此段数就点名——建议把该 beat 写短（≤单次窗口一段成）或合并镜位，
# 直接减 part 数（用户诉求「每个独立生成 clip 再简短点」）。
LONG_CLIP_PART_FLAG_THRESHOLD = 3

# 片段经济强度选择点（镜像 主线剪枝 的 advisory/enforce 语义）：
#   保守（默认/未设置）= 仅建议不阻断，兼容老项目；
#   紧凑 = 超复杂度预算且有可采纳的合并/单拍省次数 → --strict 阻断；
#   极简 = 预算再收紧一档（×0.8）后同 紧凑 阻断。
ECONOMY_ENFORCE_MODES = {"紧凑", "极简"}
ECONOMY_TIGHT_MODES = {"极简"}


def economy_mode(root: Path) -> Tuple[str, bool, float]:
    """返回 (mode_label, enforce, budget_scale)。缺省/保守 → advisory。"""
    try:
        settings = load_settings(str(root))
    except Exception:
        settings = {}
    raw = str(settings.get("片段经济") or settings.get("clip经济") or "").strip()
    enforce = raw in ECONOMY_ENFORCE_MODES
    scale = 0.8 if raw in ECONOMY_TIGHT_MODES else 1.0
    label = raw or "未设置(保守)"
    return label, enforce, scale


def classify_complexity(
    clips: Sequence[Mapping[str, Any]],
    economy_rows: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    """从 storyboard 确定性推断本集叙事复杂度（simple/standard/complex）。

    信号：不同场景数、登场核心角色数、动作/奇观镜数、强揭示/反转节拍数。
    纯启发式初筛——只决定「生成次数预算档」，不臆断剧情质量。"""
    locations: set = set()
    characters: set = set()
    action_clips = 0
    premium_beats = 0
    for i, clip in enumerate(clips, 1):
        loc = _location_key(clip)
        if loc:
            locations.add(loc)
        for c in clip.get("character_ids") or []:
            # storyboard 惯例 "CHAR_01/囚服残损态"：斜杠后是状态后缀，不是另一个角色。
            # 不剥后缀会把单角色多状态数成多人、虚抬复杂度档（实证：第3集 4 实体被数成 8）。
            base = str(c).strip().split("/", 1)[0].strip()
            if base:
                characters.add(base)
        if _high_risk(clip):
            action_clips += 1
        cid = clip_id(clip, i)
        if str((economy_rows.get(cid) or {}).get("economy_class") or "") == "premium_detail":
            premium_beats += 1
    n_loc = len(locations)
    n_char = len(characters)
    # 叙事**广度**判据（只看地点/人物这类真复杂度信号，不把打斗镜位数算进来）：
    if n_loc >= 4 or n_char >= 8:
        cls = "complex"
    elif n_loc <= 2 and n_char <= 4:
        cls = "simple"
    else:
        cls = "standard"
    action_allowance = min(action_clips * ACTION_BUDGET_ALLOWANCE_PER_CLIP, ACTION_BUDGET_ALLOWANCE_CAP)
    budget = COMPLEXITY_BUDGET_PER_MIN[cls] + action_allowance
    return {
        "class": cls,
        "distinct_locations": n_loc,
        "distinct_characters": n_char,
        "action_clips": action_clips,
        "premium_beats": premium_beats,
        "action_budget_allowance": round(action_allowance, 2),
        "budget_per_min": round(budget, 2),
    }

# 不进合并候选的高风险信号：高动作模板、显式锚链、奇观镜（安全拆分/锚帧链优先）。
HIGH_RISK_TEMPLATE_RE = re.compile(
    r"(fight|combat|chase|battle|打斗|追逐|法术|武技|渡劫|突破|爆发|magic_burst|spectacle)",
    re.I,
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def ep_label(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("第") and text.endswith("集"):
        return text
    m = re.search(r"\d+", text)
    return f"第{m.group(0)}集" if m else text


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def clip_id(clip: Mapping[str, Any], idx: int) -> str:
    return str(clip.get("id") or clip.get("clip_id") or clip.get("label") or f"Clip_{idx:02d}")


def load_storyboard(root: Path, ep: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    path = root / "脚本" / ep / "storyboard.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return [], f"缺 {path}"
    except json.JSONDecodeError as exc:
        return [], f"storyboard.json 不可解析：{exc}"
    clips = data.get("clips") if isinstance(data, dict) else None
    if not isinstance(clips, list) or not clips:
        return [], "storyboard.json 缺非空 clips[]"
    return [c for c in clips if isinstance(c, dict)], None


def generated_clip_ids(root: Path, ep: str, clips: Sequence[Mapping[str, Any]]) -> set:
    """已有付费视频落盘的 Clip id 集合（沉没成本口径·heuristic）。

    这些 Clip 不再构成「可采纳省次数」：已生成 take 是沉没成本，此刻采纳合并/单拍
    意味着废弃已付费产物并重新生成，省不到次数；enforce 档不得据此阻断（可执行、
    不死锁）。真要返工走 n2d-update 最小重制计划。判定两条：storyboard 回填的
    video_out 指向存在文件；或 出视频/<ep>/视频/ 下有该 Clip 序号前缀的 MP4
    （Clip_NN 前缀，与 video_qc 的解析同口径；_rejected 等子目录不算）。"""
    out: set = set()
    prefix_hits: set = set()
    try:
        for f in (root / "出视频" / ep / "视频").iterdir():
            if f.is_file() and f.suffix.lower() == ".mp4":
                m = re.match(r"(clip_\d+)", f.name, re.I)
                if m:
                    prefix_hits.add(m.group(1).lower())
    except OSError:
        pass
    for i, clip in enumerate(clips, 1):
        cid = clip_id(clip, i)
        video_out = str(clip.get("video_out") or "").strip()
        if video_out and (root / video_out).exists():
            out.add(cid)
            continue
        m = re.search(r"clip[_\s]*0*(\d+)", cid, re.I)
        ordinal = int(m.group(1)) if m else i
        if f"clip_{ordinal:02d}" in prefix_hits:
            out.add(cid)
    return out


def _location_key(clip: Mapping[str, Any]) -> str:
    loc = str(clip.get("location_id") or "").strip()
    if loc:
        return loc
    scene = str(clip.get("scene") or "").strip()
    return scene[:20]


def _entity_set(clip: Mapping[str, Any]) -> frozenset:
    chars = [str(x) for x in clip.get("character_ids") or []]
    entity = clip.get("entity_schedule") if isinstance(clip.get("entity_schedule"), Mapping) else {}
    required = [str(x) for x in entity.get("required_presence") or []]
    return frozenset(chars) | frozenset(required)


def _seam_mode(clip: Mapping[str, Any]) -> str:
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    return str(cont.get("seam_mode") or "").strip().lower()


def _risk_anchor_chain(clip: Mapping[str, Any]) -> bool:
    """锚帧是否代表真风险（R1 高运动/R3 漂移实证/apex 命中帧）。

    锚是**派生物**：E1 edit_cut 边界、R2 普通长镜、D0 显式中锚都会在 anchor_planner
    重跑时按合并后的新 Clip 重新规划，不应把「曾经规划过锚」一刀切当成不可合并。"""
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    anchors = cont.get("anchors") if isinstance(cont.get("anchors"), list) else []
    for a in anchors:
        if not isinstance(a, Mapping):
            continue
        use = str(a.get("use") or "").strip().lower()
        reason = str(a.get("reason") or "")
        if use == "keyframe" or "apex" in reason:
            return True
        if reason.startswith("auto: R1") or reason.startswith("auto: R3"):
            return True
    return False


def _high_risk(clip: Mapping[str, Any]) -> bool:
    template = str(clip.get("template") or "")
    if HIGH_RISK_TEMPLATE_RE.search(template):
        return True
    if _risk_anchor_chain(clip):
        return True
    if clip.get("spectacle_story_function"):
        return True
    return False


def estimate_takes(clip: Mapping[str, Any], idx: int) -> int:
    """当前 storyboard 口径下该 Clip 预计的付费生成次数（复用 shot_split_decision 真值逻辑）。"""
    cid = clip_id(clip, idx)
    duration = duration_of(clip)
    if clip_take_policy(clip) == "single_take_multishot" and duration is not None and duration <= VIDEO_SHOT_HARD_MAX_SEC and not _high_risk(clip):
        return 1
    shots = clip.get("shots") if isinstance(clip.get("shots"), list) else None
    segments = plan_video_shot_segments(cid, duration, shots)
    return max(1, len(segments))


def mergeable(clip: Mapping[str, Any]) -> Tuple[bool, str]:
    """该 Clip 能否进入合并候选组。返回 (可否, 不可原因)。"""
    duration = duration_of(clip)
    if duration is None:
        return False, "缺时长"
    if _high_risk(clip):
        return False, "高动作模板/锚链/奇观镜（安全拆分优先）"
    if str(clip.get("shared_video") or clip.get("reuse_video") or "").strip():
        return False, "共享/复用视频 clip 不合并"
    return True, ""


def find_merge_groups(
    clips: Sequence[Mapping[str, Any]],
    max_take_sec: float,
    generated: frozenset = frozenset(),
) -> List[Dict[str, Any]]:
    """相邻同场景/实体重叠链 → 合并候选组（组内合计 ≤ max_take_sec）。

    已生成视频的 Clip（generated）按沉没成本处理：断链且不进任何候选组。"""
    groups: List[Dict[str, Any]] = []
    chain: List[Tuple[int, Mapping[str, Any]]] = []

    def flush() -> None:
        if len(chain) >= 2:
            members = [clip_id(c, i) for i, c in chain]
            total = sum(float(duration_of(c) or 0.0) for _, c in chain)
            groups.append({
                "group_id": f"MERGE_{len(groups)+1:02d}",
                "members": members,
                "combined_sec": round(total, 3),
                "location": _location_key(chain[0][1]),
                "suggestion": "merge_or_single_take",
                "proposal": (
                    "并成一个 story_clip：各源 Clip 降级为内部 shots[] 镜位行，"
                    "写 take_policy=single_take_multishot 交 multishot-native 后端一次生成；"
                    "或保留分镜但把弱信息成员并入相邻强戏。"
                ),
            })
        chain.clear()

    for i, clip in enumerate(clips, 1):
        ok, _why = mergeable(clip)
        if not ok or clip_id(clip, i) in generated:
            flush()
            continue
        seam = _seam_mode(clip)
        if seam == "intentional_discontinuity":
            flush()
        if chain:
            prev_i, prev = chain[-1]
            same_loc = _location_key(clip) == _location_key(prev) and _location_key(clip) != ""
            overlap = bool(_entity_set(clip) & _entity_set(prev)) or (not _entity_set(clip) or not _entity_set(prev))
            total = sum(float(duration_of(c) or 0.0) for _, c in chain) + float(duration_of(clip) or 0.0)
            if not (same_loc and overlap and total <= max_take_sec + 1e-9):
                flush()
        chain.append((i, clip))
    flush()
    return groups


def find_fold_candidates(
    clips: Sequence[Mapping[str, Any]],
    economy_rows: Mapping[str, Mapping[str, Any]],
    generated: frozenset = frozenset(),
) -> List[Dict[str, Any]]:
    """弱信息微镜（compact/micro/montage）→ 并入相邻强戏候选（不独立成付费 clip）。"""
    out: List[Dict[str, Any]] = []
    for i, clip in enumerate(clips, 1):
        cid = clip_id(clip, i)
        if cid in generated:
            continue
        row = economy_rows.get(cid) or {}
        economy_class = str(row.get("economy_class") or "")
        duration = duration_of(clip)
        if economy_class not in {"compact_story", "micro_reaction", "montage_bridge"}:
            continue
        if duration is None or duration > 4.0:
            continue
        if _high_risk(clip):
            continue
        neighbor = None
        if i - 2 >= 0:
            neighbor = clip_id(clips[i - 2], i - 1)
        elif i < len(clips):
            neighbor = clip_id(clips[i], i + 1)
        out.append({
            "clip": cid,
            "duration_sec": duration,
            "economy_class": economy_class,
            "suggestion": "fold_into_neighbor",
            "neighbor": neighbor,
            "proposal": "短弱信息镜不独立成付费生成：并入相邻强戏做起幅/落幅节拍，或改一句旁白/屏幕文案。",
        })
    return out


def build_plan(root: Path, ep: str, max_take_sec: float = DEFAULT_MAX_TAKE_SEC) -> Dict[str, Any]:
    ep = ep_label(ep)
    clips, err = load_storyboard(root, ep)
    if err:
        return {
            "kind": KIND, "version": VERSION, "episode": ep, "generated_at": now_iso(),
            "ok": False, "summary": {}, "merge_groups": [], "fold_candidates": [],
            "findings": [{"severity": "warn", "code": "missing_storyboard", "message": err,
                          "confidence": "heuristic"}],
        }

    economy_rows: Dict[str, Mapping[str, Any]] = {}
    if sea is not None:
        try:
            report = sea.build_report(root, ep)
            economy_rows = {
                str(row.get("clip")): row
                for row in report.get("clips") or []
                if isinstance(row, Mapping)
            }
        except Exception:
            economy_rows = {}

    per_clip: List[Dict[str, Any]] = []
    total_span = 0.0
    current_takes = 0
    for i, clip in enumerate(clips, 1):
        cid = clip_id(clip, i)
        duration = duration_of(clip)
        takes = estimate_takes(clip, i)
        current_takes += takes
        if duration is not None:
            total_span += duration
        ok, why = mergeable(clip)
        per_clip.append({
            "clip": cid,
            "duration_sec": duration,
            "estimated_takes": takes,
            "take_policy": clip_take_policy(clip),
            "economy_class": str((economy_rows.get(cid) or {}).get("economy_class") or ""),
            "mergeable": ok,
            **({"merge_blocked_reason": why} if why else {}),
        })

    # 沉没成本口径：已有付费视频落盘的 Clip 不进任何省次数候选（合并=废弃重生成，无节省）。
    generated = frozenset(generated_clip_ids(root, ep, clips))
    merge_groups = find_merge_groups(clips, max_take_sec, generated)
    fold_candidates = find_fold_candidates(clips, economy_rows, generated)

    by_id = {row["clip"]: row for row in per_clip}
    member_ids = set()
    for g in merge_groups:
        group_takes = 0
        for m in g["members"]:
            member_ids.add(m)
            group_takes += int((by_id.get(m) or {}).get("estimated_takes") or 1)
        g["current_takes"] = group_takes
    folded_ids = {c["clip"] for c in fold_candidates} - member_ids

    # 单 Clip 补 take_policy 候选：编辑镜位强拆成多 take、但 ≤单次窗口且非高风险的镜，
    # 声明 take_policy=single_take_multishot 后一次生成即可。真实项目主浪费点常在这里：
    # 相邻 clip 往往已够长合不动，省次数靠不拆内部镜位。
    single_take_candidates: List[Dict[str, Any]] = []
    sunk_cost_skipped: List[str] = []
    for i, clip in enumerate(clips, 1):
        cid = clip_id(clip, i)
        if cid in member_ids or cid in folded_ids:
            continue  # 已被合并/并入候选覆盖，不重复计
        if cid in generated:
            takes_now = int((by_id.get(cid) or {}).get("estimated_takes") or 1)
            if takes_now > 1 and clip_take_policy(clip) != "single_take_multishot":
                sunk_cost_skipped.append(cid)  # 本可合并，但视频已生成 → 沉没成本，不计节省
            continue
        duration = duration_of(clip)
        takes = int((by_id.get(cid) or {}).get("estimated_takes") or 1)
        if takes <= 1 or clip_take_policy(clip) == "single_take_multishot":
            continue
        if duration is None or duration > max_take_sec:
            continue
        ok, _why = mergeable(clip)
        if not ok:
            continue
        single_take_candidates.append({
            "clip": cid,
            "duration_sec": duration,
            "current_takes": takes,
            "suggestion": "add_take_policy_single_take_multishot",
            "saving_takes": takes - 1,
            "proposal": "storyboard 该 Clip 写 take_policy=single_take_multishot：内部镜位交 multishot-native 后端一次生成，不再拆独立付费 take。",
        })

    projected_takes = (
        current_takes
        - sum(int((by_id.get(m) or {}).get("estimated_takes") or 1) for m in member_ids)
        + len(merge_groups)
        - len(folded_ids)
        - sum(int(c.get("saving_takes") or 0) for c in single_take_candidates)
    )
    projected_takes = max(len(merge_groups) if clips else 0, projected_takes)

    minutes = total_span / 60.0 if total_span > 0 else 0.0
    takes_per_min = round(current_takes / minutes, 2) if minutes else None
    projected_per_min = round(projected_takes / minutes, 2) if minutes else None

    # 复杂度感知预算：简单叙事配更低的每分钟生成密度。
    complexity = classify_complexity(clips, economy_rows)
    mode_label, enforce, budget_scale = economy_mode(root)
    budget_per_min = round(complexity["budget_per_min"] * budget_scale, 2)
    complexity["applied_budget_per_min"] = budget_per_min
    savings_available = bool(merge_groups or single_take_candidates or fold_candidates)
    over_budget = takes_per_min is not None and takes_per_min > budget_per_min
    # ── 绝对 clip 数轴（治「简单叙事 clip 太多」）──
    clip_budget_per_min = round(COMPLEXITY_CLIP_BUDGET_PER_MIN[complexity["class"]] * budget_scale, 2)
    complexity["clip_budget_per_min"] = clip_budget_per_min
    clips_per_min = round(len(clips) / minutes, 2) if minutes else None
    clips_over_budget = clips_per_min is not None and clips_per_min > clip_budget_per_min
    # ── 「每个 clip 简短点」轴：点名被拆成多段付费 part 的长 clip（沉没成本已生成的不计）──
    long_clips = [
        {"clip": row["clip"], "duration_sec": row["duration_sec"], "estimated_takes": row["estimated_takes"]}
        for row in per_clip
        if int(row.get("estimated_takes") or 0) >= LONG_CLIP_PART_FLAG_THRESHOLD and row["clip"] not in generated
    ]
    # 阻断只在 enforce 档（紧凑/极简）且超预算（生成密度或 clip 数任一）且有可采纳省次数时成立——可执行、不死锁。
    should_block = bool(enforce and (over_budget or clips_over_budget) and savings_available)

    findings: List[Dict[str, Any]] = []
    if over_budget:
        findings.append({
            "severity": "block" if should_block else "warn",
            "code": "generation_density_over_budget",
            "confidence": "heuristic",
            "message": (
                f"本集复杂度={complexity['class']}（{complexity['distinct_locations']}场景/"
                f"{complexity['distinct_characters']}角色/{complexity['action_clips']}动作镜），"
                f"当前每分钟预计生成 {takes_per_min} 次 > 预算 {budget_per_min}/min。"
                f"采纳下方 merge/单拍多镜合并后约 {projected_per_min}/min。"
                + ("片段经济=" + mode_label + " 档：先把生成次数压进预算或改 storyboard 后再进贵工位。"
                   if should_block else "简单叙事优先「更少更长的多镜单拍」，不必逐节拍独立成付费 clip。")
            ),
        })
    elif takes_per_min is not None and takes_per_min > DENSITY_WARN_PER_MIN:
        findings.append({
            "severity": "warn",
            "code": "generation_density_high",
            "confidence": "heuristic",
            "message": (
                f"当前每分钟预计生成 {takes_per_min} 次（> 兜底 {DENSITY_WARN_PER_MIN:g}/min）。"
                f"多镜叙事后端（快照 {CAPABILITY_SNAPSHOT_DATE}）单次可承载多个镜位；"
                f"按下方 merge/fold 候选合并后约 {projected_per_min}/min。"
            ),
        })
    if clips_over_budget:
        # clip 数超预算与 take 密度超预算是两条正交轴：前者治「作者拆了太多 clip」，
        # 后者治「一个 clip 拆几次生成」。二者可各自独立触发。
        clip_should_block = bool(enforce and savings_available)
        findings.append({
            "severity": "block" if clip_should_block else "warn",
            "code": "clip_count_over_budget",
            "confidence": "heuristic",
            "message": (
                f"本集复杂度={complexity['class']}，却有 {len(clips)} 个 clip"
                f"（{clips_per_min}/min > clip 数预算 {clip_budget_per_min}/min）。"
                "简单叙事应把相邻节拍并成「更少更长的多镜单拍」，而不是一节拍一 clip。"
                + ("片段经济=" + mode_label + " 档：先按下方 merge/fold 候选把 clip 数压进预算（改 storyboard）再进贵工位。"
                   if clip_should_block else "考虑合并相邻同景 clip 以减少 clip 总数（沉没成本已生成的不追溯）。")
            ),
        })
    if long_clips:
        preview = ", ".join(f"{c['clip']}({c['duration_sec']}s→{c['estimated_takes']}段)" for c in long_clips[:6])
        findings.append({
            "severity": "warn",
            "code": "long_clips_force_part_split",
            "confidence": "heuristic",
            "message": (
                f"{len(long_clips)} 个 clip 时长超单次生成窗口，被拆成 ≥{LONG_CLIP_PART_FLAG_THRESHOLD} 段付费 part："
                f"{preview}{'…' if len(long_clips) > 6 else ''}。"
                "「每个独立生成 clip 再简短点」：把这些 beat 写短到单次窗口一段成，或合并内部镜位"
                "（take_policy=single_take_multishot），直接减 part 数。时长/节奏改动属阶段2签收变更，本脚本不自动改写。"
            ),
        })
    if sunk_cost_skipped:
        findings.append({
            "severity": "info",
            "code": "sunk_cost_clips_excluded",
            "confidence": "heuristic",
            "message": (
                f"{len(sunk_cost_skipped)} 个多 take Clip（{', '.join(sunk_cost_skipped[:6])}"
                f"{'…' if len(sunk_cost_skipped) > 6 else ''}）已有生成视频落盘，按沉没成本处理：不计入可采纳"
                "省次数、不参与 enforce 阻断（此刻合并=废弃已付费产物重新生成）。确要返工走 n2d-update 最小重制计划；"
                "本口径只约束存量，后续集的 storyboard 仍按预算规划。"
            ),
        })
    if merge_groups or single_take_candidates:
        findings.append({
            "severity": "warn",
            "code": "merge_candidates_available",
            "confidence": "heuristic",
            "message": (
                f"发现 {len(merge_groups)} 组相邻合并候选 + {len(single_take_candidates)} 个单 Clip 补 "
                f"take_policy 候选，采纳后本集预计生成次数 {current_takes} → {projected_takes}。"
                "均属阶段2精修的签收变更，由编剧确认后改 storyboard，本脚本不自动改写。"
            ),
        })

    summary = {
        "clips": len(clips),
        "total_span_sec": round(total_span, 3),
        "current_estimated_takes": current_takes,
        "projected_takes_after_merge": projected_takes,
        "takes_per_minute": takes_per_min,
        "projected_takes_per_minute": projected_per_min,
        "merge_groups": len(merge_groups),
        "fold_candidates": len(fold_candidates),
        "single_take_candidates": len(single_take_candidates),
        "sunk_cost_clips": len(generated),
        "max_take_sec": max_take_sec,
        "capability_snapshot_date": CAPABILITY_SNAPSHOT_DATE,
        "complexity": complexity,
        "economy_mode": mode_label,
        "budget_per_min": budget_per_min,
        "over_budget": over_budget,
        "clips_per_minute": clips_per_min,
        "clip_budget_per_min": clip_budget_per_min,
        "clips_over_budget": clips_over_budget,
        "long_clips_forcing_parts": len(long_clips),
    }
    return {
        "kind": KIND,
        "version": VERSION,
        "episode": ep,
        "generated_at": now_iso(),
        "ok": not should_block,
        "should_block": should_block,
        "summary": summary,
        "clips": per_clip,
        "merge_groups": merge_groups,
        "fold_candidates": fold_candidates,
        "single_take_candidates": single_take_candidates,
        "long_clips": long_clips,
        "findings": findings,
        "rules": [
            "两条正交预算：takes/min（一个 clip 拆几次生成）与 clips/min（本集被拆成几个 clip）。前者靠 merge/单拍省，后者靠合并相邻节拍减 clip 数。",
            "生成次数预算按集看，不只按单 Clip 时长看：简单叙事优先「更少更长的多镜单拍」而不是逐节拍独立 clip。",
            "长 clip（超单次生成窗口、被拆成多段付费 part）会被点名 shorten：把 beat 写短到单次窗口一段成，直接减 part 数（用户诉求「每个独立生成 clip 再简短点」）。",
            "已生成视频的 Clip 是沉没成本：不进省次数候选、不触发 enforce 阻断；进行中的集不追溯返工，返工走 n2d-update 最小重制。",
            "合并候选只提案不执行：改 storyboard 是签收产物变更，须编剧在阶段2精修确认。",
            "高动作模板/锚链/奇观镜不进合并候选：安全拆分与锚帧链优先于省次数（与 shot_split_decision 同口径）。",
            "本报告全部启发式、report-only（宪法 B10）；密度口径带能力快照日期，会过期，执行前按 C2 刷新。",
        ],
    }


def build_merge_draft(
    clips: Sequence[Mapping[str, Any]],
    merge_groups: Sequence[Mapping[str, Any]],
    ep: str,
) -> Dict[str, Any]:
    """合并候选组 → 可审阅的 storyboard 草案片段（status=draft·绝不改写 storyboard.json）。

    每组产一个草案 Clip：各源 Clip 降级为内部 shots[] 镜位行（时间轴按源时长累加），
    写 take_policy=single_take_multishot。voiceover 索引/entity_schedule/continuity 等
    签收字段由编剧手工归并——脚本只搭骨架，不代签。"""
    by_id = {clip_id(c, i): c for i, c in enumerate(clips, 1)}
    draft_clips: List[Dict[str, Any]] = []
    for g in merge_groups:
        members = [m for m in g.get("members") or [] if m in by_id]
        if len(members) < 2:
            continue
        sources = [by_id[m] for m in members]
        cursor = 0.0
        shots: List[Dict[str, Any]] = []
        for m, src in zip(members, sources):
            dur = float(duration_of(src) or 0.0)
            src_shots = [s for s in src.get("shots") or [] if isinstance(s, Mapping)]
            lens = ""
            if src_shots:
                lens = str(src_shots[0].get("lens") or src_shots[0].get("shot_size") or "")
            if not lens:
                cont = src.get("continuity") if isinstance(src.get("continuity"), Mapping) else {}
                lens = str(cont.get("shot_size") or "")
            shots.append({
                "t": [round(cursor, 3), round(cursor + dur, 3)],
                "lens": lens or "承接",
                "desc": str(src.get("label") or src.get("dramatic_function") or m),
                "source_clip": m,
            })
            cursor += dur
        chars: List[str] = []
        for src in sources:
            for c in src.get("character_ids") or []:
                if str(c) not in chars:
                    chars.append(str(c))
        first = sources[0]
        draft_clips.append({
            "draft_id": f"MERGED_{g.get('group_id')}",
            "source_clips": members,
            "duration": round(cursor, 3),
            "take_policy": "single_take_multishot",
            "scene": first.get("scene"),
            "location_id": first.get("location_id"),
            "character_ids": chars,
            "shots": shots,
            "manual_merge_required": [
                "voiceover/dialogue/narration 三轨索引按互斥规则归并",
                "entity_schedule 与 continuity.entry_exit/start_state/end_state 重写为合并后真值",
                "dramatic_function/pacing_role/runtime_priority 重签",
                "合并落 storyboard 后重跑 anchor_planner / validate_timings / 相关 gate",
            ],
        })
    return {
        "kind": "n2d_clip_economy_merge_draft",
        "version": VERSION,
        "episode": ep,
        "generated_at": now_iso(),
        "status": "draft",
        "policy": "review-then-apply：编剧审阅后手工并入 storyboard.json；本文件不是执行真值，不参与 gate。",
        "draft_clips": draft_clips,
    }


def render_md(plan: Mapping[str, Any]) -> str:
    s = plan.get("summary") or {}
    lines = [
        "# Clip 经济性规划（生成次数预算 + 合并候选）",
        "",
        f"- episode: {plan.get('episode')}",
        f"- 当前预计生成次数: {s.get('current_estimated_takes')}（{s.get('takes_per_minute')}/min）",
        f"- 合并后预计: {s.get('projected_takes_after_merge')}（{s.get('projected_takes_per_minute')}/min）",
        f"- 合并候选组: {s.get('merge_groups')} · 并入相邻强戏候选: {s.get('fold_candidates')} · 单Clip补take_policy候选: {s.get('single_take_candidates')}",
        (lambda c: f"- 复杂度: {c.get('class')}（{c.get('distinct_locations')}场景/{c.get('distinct_characters')}角色/"
                   f"{c.get('action_clips')}动作镜）· 预算 {s.get('budget_per_min')}/min · 片段经济档 {s.get('economy_mode')}"
                   f"{'· 超预算' if s.get('over_budget') else ''}")(s.get('complexity') or {}),
        f"- 能力快照: {s.get('capability_snapshot_date')}（单次多镜上限口径 {s.get('max_take_sec')}s·会过期）",
        "",
        "## 合并候选组",
        "",
    ]
    for g in plan.get("merge_groups") or []:
        lines.append(
            f"- **{g.get('group_id')}**（{g.get('location')}·合计 {g.get('combined_sec')}s）："
            f"{' + '.join(g.get('members') or [])} → {g.get('proposal')}"
        )
    if not plan.get("merge_groups"):
        lines.append("- 无（相邻镜要么不同场景，要么高风险/超单次窗口）")
    lines += ["", "## 并入相邻强戏候选", ""]
    for c in plan.get("fold_candidates") or []:
        lines.append(
            f"- {c.get('clip')}（{c.get('duration_sec')}s·{c.get('economy_class')}）→ 并入 {c.get('neighbor')}：{c.get('proposal')}"
        )
    if not plan.get("fold_candidates"):
        lines.append("- 无")
    lines += ["", "## 单 Clip 补 take_policy 候选（内部镜位一次生成）", ""]
    for c in plan.get("single_take_candidates") or []:
        lines.append(
            f"- {c.get('clip')}（{c.get('duration_sec')}s·当前 {c.get('current_takes')} take → 1）：{c.get('proposal')}"
        )
    if not plan.get("single_take_candidates"):
        lines.append("- 无")
    findings = plan.get("findings") or []
    if findings:
        lines += ["", "## Findings（全部 heuristic·report-only）", ""]
        for f in findings:
            lines.append(f"- {str(f.get('severity')).upper()} {f.get('code')}: {f.get('message')}")
    lines += ["", "## Rules", ""]
    for rule in plan.get("rules") or []:
        lines.append(f"- {rule}")
    return "\n".join(lines)


def write_outputs(root: Path, ep: str, plan: Mapping[str, Any]) -> Tuple[Path, Path]:
    out = root / "生产数据"
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"clip_economy_plan_{ep}.json"
    md_path = out / f"clip_economy_plan_{ep}.md"
    write_atomic(json_path, json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_atomic(md_path, render_md(plan) + "\n")
    return json_path, md_path


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d clip economy planner (generation-count budget + merge-first)")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-take-sec", type=float, default=DEFAULT_MAX_TAKE_SEC,
                    help="单次多镜生成的合计时长口径（默认 15s；按所选后端能力档调整）")
    ap.add_argument("--emit-merge-draft", action="store_true",
                    help="把合并候选组落成可审阅的 storyboard 草案片段（status=draft，不改写 storyboard.json）")
    ap.add_argument("--strict", action="store_true",
                    help="片段经济=紧凑/极简 档：超复杂度预算且有可采纳省次数时返回非零（阻断进贵工位）；保守/未设置恒返回 0。")
    ns = ap.parse_args(argv)
    root = Path(ns.root.rstrip("/"))
    ep = ep_label(ns.episode)
    plan = build_plan(root, ep, max_take_sec=float(ns.max_take_sec))
    if ns.write:
        jp, mp = write_outputs(root, ep, plan)
        plan = {**plan, "outputs": {"json": str(jp), "markdown": str(mp)}}
    if ns.emit_merge_draft and plan.get("merge_groups"):
        clips, _err = load_storyboard(root, ep)
        draft = build_merge_draft(clips, plan["merge_groups"], ep)
        draft_path = root / "生产数据" / f"clip_economy_merge_draft_{ep}.json"
        write_atomic(draft_path, json.dumps(draft, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        plan = {**plan, "merge_draft": str(draft_path)}
    if ns.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(render_md(plan))
    # 退出码：仅 --strict 且 enforce 档判定 should_block 才非零；保守/未设置恒 0，老项目不受影响。
    return 1 if (ns.strict and plan.get("should_block")) else 0


if __name__ == "__main__":
    raise SystemExit(main())
