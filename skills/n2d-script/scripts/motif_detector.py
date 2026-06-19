#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""题材 + 母题(motif)检测器 — 识别穿越/系统流等爽文的题材与高频复现母题桥段。

母题=相对固定的复现场景模板 + 每次出现带成长属性（系统面板出现/升级/签到/抽奖/爆装备…）。
本检测器照 anchor_planner.py 的范式：规则确定性、逐条可解释、默认 dry-run 出建议、人确认 --write 注回。

检测两层（关键词单一真值源在 n2d_const，split/分镜检测器与 gate 共用）：
  · 题材 detect_genre：扫正文/storyboard，按 GENRE_KEYWORDS 命中数判定（≥GENRE_MIN_HITS），多题材取最多者。
  · 母题 detect_motif_clips：扫每个 Clip 文本，按 MOTIF_TYPE_KEYWORDS 识别母题桥段（系统面板等）。

默认 dry-run：只写 生产数据/motif_plan_第N集.{json,md}（题材判定 + 母题桥段 + 增强建议），给人确认。
--write 才：① 把 template/ motif_id 注回 storyboard.json 对应 Clip 的 template_contract；
          ② 初始化/追加 出图/共享/motif_registry.json（含成长 progression 骨架，等级占位待人填）。

混合渲染：系统面板的等级/属性是 overlay 文字层（n2d-compose render_panel），AI 只出锁色锁形空光幕底框，
所以 progression 的 level/attrs 是给 overlay 用的数值真值——本检测器只排骨架，具体数值由人按剧情填。

用法:
  python3 motif_detector.py <作品根> <第N集> [--write] [--genre 系统流]
测试: cd skills/n2d-script/scripts && python -m pytest test_motif_detector.py
"""
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
try:
    from n2d_const import (
        GENRE_KEYWORDS, GENRE_MIN_HITS, MOTIF_TYPE_KEYWORDS, MOTIF_TYPE_MIN_HITS,
        MOTIF_ID_PREFIX, MOTIF_REGISTRY_KIND, MOTIF_PLAN_KIND,
        MOTIF_MONOTONIC_FIELDS_DEFAULT, SYSTEM_PANEL_TEMPLATE_ID,
        SYSTEM_PANEL_MOTIF_ID, SYSTEM_PANEL_VFX_ID, SYSTEM_PANEL_OVERLAY_FIELDS,
    )
except Exception:  # 退化：常量不可用时本地兜底，保持与 n2d_const 同步（仅供独立跑/测试桩）
    GENRE_KEYWORDS = (("系统流", ("系统", "面板", "宿主", "升级")),)
    GENRE_MIN_HITS = 2
    MOTIF_TYPE_KEYWORDS = (("system_panel", ("系统面板", "面板", "等级")),)
    MOTIF_TYPE_MIN_HITS = 1
    MOTIF_ID_PREFIX = "MOTIF_"
    MOTIF_REGISTRY_KIND = "n2d_motif_registry"
    MOTIF_PLAN_KIND = "n2d_motif_plan"
    MOTIF_MONOTONIC_FIELDS_DEFAULT = ("level", "panel_tier")
    SYSTEM_PANEL_TEMPLATE_ID = "system_panel"
    SYSTEM_PANEL_MOTIF_ID = "MOTIF_系统面板"
    SYSTEM_PANEL_VFX_ID = "VFX_系统面板"
    SYSTEM_PANEL_OVERLAY_FIELDS = ("title", "level", "attrs")

# 哪些母题类型呈现为"系统面板"形态（套 system_panel 镜头模板 + VFX_系统面板 + overlay）。
# 其余（loot/cheat 等）暂不绑面板模板，只在 motif_plan 报告里列出，待后续加专属模板。
PANEL_FAMILY_MOTIF_TYPES = ("system_panel", "level_up", "system_refresh", "signin", "gacha")


# ── 题材检测（纯函数·可测） ──────────────────────────────────────────────────

def detect_genre(text: str, *, min_hits: int = GENRE_MIN_HITS) -> Dict[str, Any]:
    """按 GENRE_KEYWORDS 命中数判定题材。返回 {genre, confidence, hits, matched, by_genre}。

    genre=None 表示无题材达到 min_hits。by_genre 列全部题材命中明细（便于人复核）。"""
    by_genre: List[Dict[str, Any]] = []
    for genre, keywords in GENRE_KEYWORDS:
        matched = sorted({kw for kw in keywords if kw in text})
        by_genre.append({"genre": genre, "hits": len(matched), "matched": matched})
    by_genre.sort(key=lambda r: r["hits"], reverse=True)
    top = by_genre[0] if by_genre else {"genre": None, "hits": 0, "matched": []}
    if top["hits"] < min_hits:
        return {"genre": None, "confidence": 0.0, "hits": top["hits"],
                "matched": top["matched"], "by_genre": by_genre}
    # 置信度：top 命中数 / (top + 第二名)，区分"明显单一题材"与"两题材纠缠"。
    second = by_genre[1]["hits"] if len(by_genre) > 1 else 0
    confidence = round(top["hits"] / (top["hits"] + second), 2) if (top["hits"] + second) else 1.0
    return {"genre": top["genre"], "confidence": confidence, "hits": top["hits"],
            "matched": top["matched"], "by_genre": by_genre}


# ── 母题桥段检测（纯函数·可测） ───────────────────────────────────────────────

def clip_text(clip: Dict[str, Any]) -> str:
    """聚合 Clip 的可读文本（label/scene/台词/分镜描述/状态），用于母题关键词匹配。纯函数·可测。"""
    parts: List[str] = [str(clip.get("label") or ""), str(clip.get("scene") or ""),
                        str(clip.get("voiceover") or clip.get("台词") or "")]
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
    parts += [str(cont.get("start_state") or ""), str(cont.get("end_state") or "")]
    for s in clip.get("shots") or []:
        if isinstance(s, dict):
            parts.append(str(s.get("desc") or ""))
            parts.append(str(s.get("台词") or s.get("line") or ""))
    return " ".join(parts)


def classify_motif(clip: Dict[str, Any], *, min_hits: int = MOTIF_TYPE_MIN_HITS) -> Optional[Dict[str, Any]]:
    """识别 Clip 命中的母题类型（取命中最多者）。不命中返回 None。返回 {motif_type, hits, matched, rule}。"""
    text = clip_text(clip)
    best: Optional[Dict[str, Any]] = None
    for motif_type, keywords in MOTIF_TYPE_KEYWORDS:
        matched = sorted({kw for kw in keywords if kw in text})
        if len(matched) >= min_hits and (best is None or len(matched) > best["hits"]):
            best = {"motif_type": motif_type, "hits": len(matched), "matched": matched}
    if best is None:
        return None
    best["rule"] = f"命中 {best['motif_type']}（{best['hits']} 词：{'/'.join(best['matched'])}）"
    return best


def motif_template_id(motif_type: str) -> str:
    """母题类型 → 镜头模板 id。面板家族套 system_panel；其余暂无专属模板返回空串。"""
    return SYSTEM_PANEL_TEMPLATE_ID if motif_type in PANEL_FAMILY_MOTIF_TYPES else ""


def motif_id_for(motif_type: str) -> str:
    """母题类型 → motif_id。面板家族统一归到 MOTIF_系统面板（共享一套面板定妆/成长）。"""
    if motif_type in PANEL_FAMILY_MOTIF_TYPES:
        return SYSTEM_PANEL_MOTIF_ID
    return MOTIF_ID_PREFIX + motif_type


def clip_id_of(clip: Dict[str, Any], ep: str, index: int) -> str:
    cid = clip.get("id")
    return str(cid) if cid else f"{ep}_CLIP{index:02d}"


def detect_motif_clips(clips: List[Dict[str, Any]], ep: str,
                       *, min_hits: int = MOTIF_TYPE_MIN_HITS) -> List[Dict[str, Any]]:
    """扫 Clip 列表识别母题桥段。返回每个命中 Clip 的建议条目（含 motif_id/template/成长档建议）。"""
    out: List[Dict[str, Any]] = []
    panel_seq = 0
    for i, clip in enumerate(clips, 1):
        if not isinstance(clip, dict):
            continue
        hit = classify_motif(clip, min_hits=min_hits)
        if not hit:
            continue
        mt = hit["motif_type"]
        is_panel = mt in PANEL_FAMILY_MOTIF_TYPES
        if is_panel:
            panel_seq += 1
        out.append({
            "clip_index": i,
            "clip_id": clip_id_of(clip, ep, i),
            "motif_type": mt,
            "motif_id": motif_id_for(mt),
            "template": motif_template_id(mt),
            "hits": hit["hits"],
            "matched": hit["matched"],
            "rule": hit["rule"],
            # 成长档建议骨架：面板家族按出现序给递增等级占位（人按剧情改实际数值）。
            "growth_suggestion": ({"level": panel_seq, "panel_tier": f"v{panel_seq}"} if is_panel else {}),
        })
    return out


# ── 成长状态机单调校验（纯函数·可测） ──────────────────────────────────────────

def validate_progression_monotonic(progression: List[Dict[str, Any]],
                                    monotonic_fields: Tuple[str, ...] = MOTIF_MONOTONIC_FIELDS_DEFAULT
                                    ) -> Dict[str, Any]:
    """校验成长 progression 的单调字段只增不减（退级=违例）。返回 {ok, violations}。

    panel_tier 形如 "v1"/"v2_流光"——取其中首个整数作序比较；level 直接数值比较。
    无法解析为序的值跳过（不判违例，只判可比较项）。纯函数·可测。"""
    import re as _re
    violations: List[Dict[str, Any]] = []

    def as_rank(field: str, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        m = _re.search(r"\d+(?:\.\d+)?", str(value))
        return float(m.group()) if m else None

    last: Dict[str, float] = {}
    for idx, snap in enumerate(progression):
        if not isinstance(snap, dict):
            continue
        for field in monotonic_fields:
            rank = as_rank(field, snap.get(field))
            if rank is None:
                continue
            if field in last and rank < last[field]:
                violations.append({
                    "at_index": idx,
                    "at_clip": snap.get("at_clip"),
                    "field": field,
                    "value": snap.get(field),
                    "prev": last[field],
                    "message": f"{field} 退级：{snap.get(field)} < 上一档 {last[field]}（母题成长只进不退）",
                })
            else:
                last[field] = rank
    return {"ok": not violations, "violations": violations}


# ── 路径/IO ──────────────────────────────────────────────────────────────────

def storyboard_path(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", ep, "storyboard.json")


def raw_path(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", ep, "raw.txt")


def motif_registry_path(root: str) -> str:
    return os.path.join(root, "出图", "共享", "motif_registry.json")


def load_json(path: str) -> Optional[Any]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def gather_text(root: str, ep: str, sb: Optional[Dict[str, Any]]) -> str:
    """题材判定的语料：raw 正文 + storyboard 各 Clip 文本（任一缺失则只用可得部分）。"""
    parts: List[str] = []
    raw = None
    try:
        with open(raw_path(root, ep), encoding="utf-8") as f:
            raw = f.read()
    except OSError:
        raw = None
    if raw:
        parts.append(raw)
    if isinstance(sb, dict):
        parts.append(str(sb.get("global_style") or ""))
        for clip in sb.get("clips") or []:
            if isinstance(clip, dict):
                parts.append(clip_text(clip))
    return "\n".join(parts)


# ── 计划/报告 ─────────────────────────────────────────────────────────────────

def plan_episode(root: str, ep: str, *, genre_override: Optional[str] = None) -> Dict[str, Any]:
    sb = load_json(storyboard_path(root, ep))
    clips = sb.get("clips") if isinstance(sb, dict) else None
    text = gather_text(root, ep, sb if isinstance(sb, dict) else None)
    genre_result = detect_genre(text)
    if genre_override:
        genre_result = {**genre_result, "genre": genre_override, "override": True}
    motif_clips = detect_motif_clips(clips, ep) if isinstance(clips, list) else []
    panel_clips = [m for m in motif_clips if m["motif_id"] == SYSTEM_PANEL_MOTIF_ID]
    return {
        "schema_version": 1,
        "kind": MOTIF_PLAN_KIND,
        "episode": ep,
        "genre": genre_result,
        "motif_clips": motif_clips,
        "summary": {
            "genre": genre_result.get("genre"),
            "motif_clips": len(motif_clips),
            "panel_clips": len(panel_clips),
            "storyboard_present": isinstance(clips, list),
        },
    }


def render_md(plan: Dict[str, Any]) -> str:
    g = plan["genre"]
    lines = [f"# 题材母题检测 — {plan['episode']}", ""]
    if g.get("genre"):
        tag = "（用户指定）" if g.get("override") else f"（置信度 {g.get('confidence')}，命中 {g.get('hits')} 词）"
        lines.append(f"- **题材判定：{g['genre']}**{tag}　命中：{'/'.join(g.get('matched') or []) or '—'}")
    else:
        lines.append("- 题材判定：未达阈值（无明显题材）。如需启用母题增强可 `--genre 系统流` 指定。")
    lines.append(f"- 母题桥段：{plan['summary']['motif_clips']} 处（系统面板家族 {plan['summary']['panel_clips']} 处）")
    lines.append("")
    if not plan["summary"]["storyboard_present"]:
        lines.append("> ⚠️ 未找到 storyboard.json：题材按 raw 正文判定，母题桥段需分镜后再扫。")
        lines.append("")
    if plan["motif_clips"]:
        lines.append("## 母题增强建议（人确认后 `--write` 注回）")
        lines.append("")
        for m in plan["motif_clips"]:
            tpl = f"套模板 `{m['template']}`" if m["template"] else "（暂无专属模板）"
            lines.append(f"### {m['clip_id']}　{m['rule']}")
            lines.append(f"- 母题：`{m['motif_id']}`（{m['motif_type']}）{tpl}")
            if m["growth_suggestion"]:
                gs = m["growth_suggestion"]
                lines.append(f"- 成长档建议：level={gs.get('level')} / panel_tier={gs.get('panel_tier')}（占位·按剧情改实际数值/属性）")
            lines.append("- 增强落点：")
            lines.append("  - **场景/道具**：AI 出锁色锁形发光光幕底框（`%s`，禁烤文字/数字）" % SYSTEM_PANEL_VFX_ID)
            lines.append("  - **台词**：系统音腔（机械/简短，`narrator_role=系统`→字幕灰小字）；主角反应=爽点")
            lines.append("  - **overlay 数值层**：合成期叠清晰 %s（n2d-compose render_panel）" % "/".join(SYSTEM_PANEL_OVERLAY_FIELDS))
            lines.append("")
    else:
        lines.append("> 未检测到母题桥段。")
        lines.append("")
    lines.append("---")
    lines.append("确认后：`python3 motif_detector.py <作品根> %s --write` 注回 storyboard + 写 motif_registry.json。" % plan["episode"])
    lines.append("详见 `n2d-script/references/题材母题框架.md`。")
    return "\n".join(lines) + "\n"


# ── 注回（--write） ──────────────────────────────────────────────────────────

def inject_storyboard(root: str, ep: str, motif_clips: List[Dict[str, Any]]) -> int:
    """把 template/motif_id 注回 storyboard.json 对应 Clip 的 template_contract（原子写）。
    已手动声明 template 的 Clip 跳过（人工优先）。返回写入 Clip 数。"""
    path = storyboard_path(root, ep)
    sb = load_json(path)
    if not isinstance(sb, dict) or not isinstance(sb.get("clips"), list):
        return 0
    by_index = {m["clip_index"]: m for m in motif_clips if m["template"]}
    written = 0
    for i, clip in enumerate(sb["clips"], 1):
        if not isinstance(clip, dict):
            continue
        m = by_index.get(i)
        if not m:
            continue
        if clip.get("template") and clip.get("template") != m["template"]:
            continue  # 人工已声明别的模板，优先
        clip["template"] = m["template"]
        tc = clip.setdefault("template_contract", {})
        if not tc.get("motif_id"):
            tc["motif_id"] = m["motif_id"]
            tc.setdefault("vfx_asset", SYSTEM_PANEL_VFX_ID)
            tc.setdefault("text_layer", "overlay")
        written += 1
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sb, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return written


def upsert_motif_registry(root: str, motif_clips: List[Dict[str, Any]]) -> Dict[str, Any]:
    """初始化/追加 出图/共享/motif_registry.json（原子写）。为面板家族建/补 MOTIF_系统面板，
    把检测到的 Clip 追加进 progression 骨架（等级占位，去重 at_clip）。返回 {created, appended}。"""
    path = motif_registry_path(root)
    reg = load_json(path)
    if not isinstance(reg, dict) or reg.get("kind") != MOTIF_REGISTRY_KIND:
        reg = {"kind": MOTIF_REGISTRY_KIND, "version": 1, "motifs": []}
    motifs: List[Dict[str, Any]] = reg.setdefault("motifs", [])
    by_id = {m.get("motif_id"): m for m in motifs if isinstance(m, dict)}
    created, appended = 0, 0
    for m in motif_clips:
        if m["motif_id"] != SYSTEM_PANEL_MOTIF_ID:
            continue  # MVP 只为面板家族落 registry
        entry = by_id.get(SYSTEM_PANEL_MOTIF_ID)
        if entry is None:
            entry = {
                "motif_id": SYSTEM_PANEL_MOTIF_ID,
                "motif_type": "system_panel",
                "scope": "复用",
                "growth_state_machine": {
                    "bound_vfx": SYSTEM_PANEL_VFX_ID,
                    "monotonic_fields": list(MOTIF_MONOTONIC_FIELDS_DEFAULT),
                    "progression": [],
                },
                "shot_template_id": SYSTEM_PANEL_TEMPLATE_ID,
                "dialogue_patterns": {
                    "trigger_lines": ["叮——检测到宿主", "系统绑定成功"],
                    "narrator_role": "系统",
                    "tone": "机械音/无情感/简短",
                },
                "overlay_spec": {
                    "anchor": "panel_center",
                    "fields": list(SYSTEM_PANEL_OVERLAY_FIELDS),
                    "color": [180, 230, 255],
                    "lock_to_clip_range": True,
                },
            }
            motifs.append(entry)
            by_id[SYSTEM_PANEL_MOTIF_ID] = entry
            created += 1
        prog = entry["growth_state_machine"]["progression"]
        existing_clips = {p.get("at_clip") for p in prog if isinstance(p, dict)}
        if m["clip_id"] in existing_clips:
            continue
        gs = m.get("growth_suggestion") or {}
        prog.append({
            "at_clip": m["clip_id"],
            "level": gs.get("level"),
            "panel_tier": gs.get("panel_tier"),
            "title": "系统",
            "attrs": {},
            "_note": "占位·按剧情填实际等级/属性数值（overlay 文字层据此渲染）",
        })
        appended += 1
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return {"created": created, "appended": appended, "path": path}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="题材 + 母题(motif)检测器")
    ap.add_argument("project_root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true",
                    help="把 template/motif_id 注回 storyboard.json 并写 motif_registry.json（默认只出报告）")
    ap.add_argument("--genre", default=None, help="人工指定题材（覆盖自动判定）")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.project_root)
    plan = plan_episode(root, args.episode, genre_override=args.genre)
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, f"motif_plan_{args.episode}.json")
    md_path = os.path.join(out_dir, f"motif_plan_{args.episode}.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_md(plan))
    print(f"[ok] 母题检测 → {json_path}")
    print(f"[ok] 人读报告 → {md_path}")
    s = plan["summary"]
    print(f"     题材={s['genre'] or '未判定'} / 母题桥段 {s['motif_clips']} 处（面板家族 {s['panel_clips']} 处）")
    if args.write:
        n = inject_storyboard(root, args.episode, plan["motif_clips"])
        reg = upsert_motif_registry(root, plan["motif_clips"])
        print(f"[ok] 注回 storyboard.json：{n} 个 Clip 的 template/motif_id")
        print(f"[ok] motif_registry.json：新建 {reg['created']} 母题 / 追加 {reg['appended']} 成长档 → {reg['path']}")
        print("     ⚠️ progression 等级/属性是占位骨架，请按剧情填实际数值（overlay 文字层据此渲染）")
    elif plan["motif_clips"]:
        print("     （dry-run：确认后加 --write 注回 storyboard + 写 motif_registry.json）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
