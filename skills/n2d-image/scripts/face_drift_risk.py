#!/usr/bin/env python3
"""出图前·脸漂风险分（③ 把 LoRA/加强参考的判断从「事后升档」前移到「事前预测」）。

现状链路里，脸漂只有**事后**才被处理：跨集出现 ≥2 集 warn/block 才由 n2d-identity 建议升 LoRA
（identity.py lora_upgrade_candidates）——意味着前两集已经漂了才反应。本脚本在**出图之前**，用
分镜本身的高危信号预测哪些角色本集容易脸漂，提前提示加强参考 / 建表情库 / 上 LoRA。

风险信号（全部来自 storyboard.json + identity_registry.json，不读像素、不花钱）：
  - 近景占比   ：该角色出现的镜里 CU/ECU/MCU/OTS/特写/反打 的比例（近景脸放大，漂移最刺眼）；
  - 大表情数   ：desc 命中强情绪（哭/怒/狂喜/崩溃…）的镜（大表情让 AI 重画整张脸）；
  - 多人同框   ：与其它命名角色同框的镜（单图参考后端难分别控脸，易串脸）；
  - 极端角度   ：lens/desc 命中该角色 angle_policy.risky（俯仰/远景/逆光暗部）的镜；
  - 锁脸档位   ：默认后端是否有原生锁脸——Codex/即梦只有 reference_group（底色更高危），
                 可灵/Seedream/Sora 原生主体库更稳，LoRA 最稳。

输出 生产数据/face_drift_risk_<ep>.json + .md，按风险排序，对 high/medium 角色给出可执行建议
（与 image_qc 的 no_expression_lib_ref gate、n2d-lora init 对齐）。**只提示不阻断**——出图前的预案，
不是落档闸门（落档由 image_qc 管）。

用法：python3 face_drift_risk.py <作品根> <第N集> [--json]
纯 stdlib；评分纯函数有 pytest 覆盖。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

# 近景景别（与 image_qc.CLOSEUP_MARKERS / video_qc 同义；本 skill 自留一份，不跨 import）。
CLOSEUP_MARKERS = ("ECU", "MCU", "BCU", "CU", "OTS", "反打", "特写", "近景", "过肩", "脸部")
# 强情绪（与 image_qc.STRONG_EMOTION_MARKERS 对齐：表情镜脸漂的触发词）。
STRONG_EMOTION_MARKERS = (
    "哭", "泣", "落泪", "含泪", "泪", "怒", "愤", "暴怒", "狂怒", "震惊", "惊恐", "恐惧",
    "狂喜", "大笑", "狂笑", "嘶吼", "咆哮", "嚎", "痛苦", "崩溃", "狰狞", "扭曲", "癫狂",
    "失控", "绝望", "悲恸", "惊愕",
)
# 默认后端有原生锁脸能力的（image 阶段主体库/Cameo）；其余（codex/openai/dreamina）只有 reference_group。
NATIVE_LOCK_BACKENDS = {"kling", "seedream", "sora"}
READY_STATUSES = {"registered", "ready"}

WEIGHTS = {"base_reference_group": 25, "base_native": 8, "base_lora": 0,
           "closeup": 30, "emotion_each": 8, "emotion_cap": 24,
           "multi": 20, "angle_each": 6, "angle_cap": 24}
BAND_HIGH, BAND_MEDIUM = 55, 30


# ── 纯函数（无依赖·可测） ──────────────────────────────────────────────────────

def is_closeup(lens_or_desc: str) -> bool:
    s = str(lens_or_desc or "").upper()
    return any(m.upper() in s for m in CLOSEUP_MARKERS)


def has_strong_emotion(text: str) -> bool:
    t = str(text or "")
    return any(m in t for m in STRONG_EMOTION_MARKERS)


def extreme_angle_tokens(lens: str, desc: str, risky: Sequence[str]) -> List[str]:
    """命中该角色 angle_policy.risky 的高危项（lens/desc 文字 → risky token）。纯函数·可测。"""
    text = f"{lens or ''} {desc or ''}"
    hit: List[str] = []
    risky_set = set(risky or [])
    if ("extreme_top" in risky_set) and re.search(r"俯|顶光|顶视|鸟瞰|top", text, re.I):
        hit.append("extreme_top")
    if ("extreme_low" in risky_set) and re.search(r"仰|low\b|脚下", text, re.I):
        hit.append("extreme_low")
    if ("face_too_small" in risky_set) and re.search(r"\bELS\b|\bLS\b|远景|全景|大全|群像", text, re.I):
        hit.append("face_too_small")
    if ("deep_shadow" in risky_set) and re.search(r"逆光|暗部|阴影|剪影|暗光|背光|silhouet", text, re.I):
        hit.append("deep_shadow")
    return hit


def lock_tier(default_backend: str, image_adapters: Mapping[str, Any], lora: Mapping[str, Any]) -> str:
    """该角色当前锁脸档位：'lora'（最稳）/ 'native'（后端原生主体库）/ 'reference_group'（仅参考图，最高危底色）。纯函数·可测。"""
    if str((lora or {}).get("status") or "").strip() in {"ready", "training"}:
        return "lora"
    be = str(default_backend or "").strip().lower()
    ad = (image_adapters or {}).get(be) or {}
    if be in NATIVE_LOCK_BACKENDS and str(ad.get("status") or "").strip() in READY_STATUSES:
        return "native"
    return "reference_group"


def score_character(signals: Mapping[str, Any], tier: str) -> Dict[str, Any]:
    """风险分 + 档位 + 驱动因子（纯函数·可测）。

    signals: {appear, closeup, emotion, multi, angle}（计数）。score 0–100，band high/medium/low。
    """
    appear = max(int(signals.get("appear", 0)), 0)
    base = {"reference_group": WEIGHTS["base_reference_group"], "native": WEIGHTS["base_native"],
            "lora": WEIGHTS["base_lora"]}.get(tier, WEIGHTS["base_reference_group"])
    drivers: List[Dict[str, Any]] = [{"factor": f"锁脸档位={tier}", "points": base}]
    closeup_ratio = (signals.get("closeup", 0) / appear) if appear else 0.0
    multi_ratio = (signals.get("multi", 0) / appear) if appear else 0.0
    cu = round(closeup_ratio * WEIGHTS["closeup"], 1)
    emo = min(int(signals.get("emotion", 0)) * WEIGHTS["emotion_each"], WEIGHTS["emotion_cap"])
    mp = round(multi_ratio * WEIGHTS["multi"], 1)
    ang = min(int(signals.get("angle", 0)) * WEIGHTS["angle_each"], WEIGHTS["angle_cap"])
    if cu:
        drivers.append({"factor": f"近景占比 {signals.get('closeup',0)}/{appear}", "points": cu})
    if emo:
        drivers.append({"factor": f"大表情 {signals.get('emotion',0)} 镜", "points": emo})
    if mp:
        drivers.append({"factor": f"多人同框 {signals.get('multi',0)}/{appear}", "points": mp})
    if ang:
        drivers.append({"factor": f"极端角度 {signals.get('angle',0)} 镜", "points": ang})
    score = min(round(base + cu + emo + mp + ang, 1), 100.0)
    band = "high" if score >= BAND_HIGH else ("medium" if score >= BAND_MEDIUM else "low")
    drivers.sort(key=lambda d: d["points"], reverse=True)
    return {"score": score, "band": band, "tier": tier, "drivers": drivers}


def suggestions_for(name: str, scored: Mapping[str, Any], signals: Mapping[str, Any],
                    char_id: str, form: str, root_hint: str = "<作品根>") -> List[str]:
    """按驱动因子 + 档位给可执行建议（与 image_qc 表情库 gate、n2d-lora init 对齐）。纯函数·可测。"""
    out: List[str] = []
    tier = scored.get("tier")
    appear = max(int(signals.get("appear", 0)), 1)
    # 阈值化：只在某高危信号**材料性出现**时给对应建议，避免每个角色都堆同一套样板话。
    if tier == "reference_group":
        out.append("默认后端无原生锁脸（Codex/即梦仅 reference_group）——跨镜全靠参考图，是脸漂高危底色。")
    if int(signals.get("emotion", 0)) >= 2:
        out.append("大表情镜多：必建表情库 expressions + 脸部特写参考，首尾双帧只插值（对齐 image_qc no_expression_lib_ref）。")
    if int(signals.get("closeup", 0)) / appear >= 0.4:
        out.append("近景占比高：补脸部特写主参考，近景镜锁脸型/五官比例/发型发饰。")
    if int(signals.get("multi", 0)) >= 2:
        out.append("多人同框多：用多参考后端（Seedream/可灵主体库）或把同框拆成正反打分别出，避免单图参考串脸。")
    if int(signals.get("angle", 0)) >= 1:
        out.append("极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。")
    if scored.get("band") == "high" and tier != "lora":
        out.append(f"风险 high 且未上 LoRA：考虑 python3 skills/n2d-lora/scripts/lora.py init '{root_hint}' "
                   f"--character-id {char_id} --form '{form}'（事前升档，别等跨集漂了再补）。")
    return out


# ── 数据装载 + 推断（best-effort I/O） ──────────────────────────────────────────

def project_default_backend(root: Path) -> str:
    """_设置.md 的『生图AI：X』→ 后端规范名（小写）；读不到 → codex（与全局默认一致）。"""
    raw = ""
    try:
        text = (root / "_设置.md").read_text(encoding="utf-8")
        m = re.search(r"生图AI[：:]\s*([^\n（(]+)", text)
        if m:
            raw = m.group(1).strip()
    except Exception:
        pass
    low = raw.lower()
    alias = {"codex": "codex", "openai": "openai", "即梦": "dreamina", "dreamina": "dreamina",
             "可灵": "kling", "kling": "kling", "seedream": "seedream", "即梦seedream": "seedream",
             "sora": "sora", "nano": "seedream"}
    for k, v in alias.items():
        if k in low:
            return v
    return "codex"


def _split_aliases(*texts: str) -> Set[str]:
    out: Set[str] = set()
    for t in texts:
        for part in re.split(r"[/／、,，|\s]+", str(t or "")):
            p = part.strip()
            if len(p) >= 2:
                out.add(p)
    return out


def load_characters(root: Path) -> List[Dict[str, Any]]:
    """identity_registry.json → 每角色 {id, name, aliases, form, angle_policy, image_adapters, lora}。
    多形态取第 1 形态做策略锚（多数角色单形态），lora 取任一 ready。"""
    path = root / "出图" / "共享" / "identity_registry.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    chars: List[Dict[str, Any]] = []
    for ch in data.get("characters") or []:
        cid = str(ch.get("id") or "").strip()
        forms = [f for f in (ch.get("forms") or []) if isinstance(f, dict)]
        if not cid or not forms:
            continue
        aliases = _split_aliases(ch.get("name") or "")
        for f in forms:
            aliases |= _split_aliases(f.get("asset_key") or "")
        f0 = forms[0]
        adapters = f0.get("identity_adapters") or {}
        # lora ready on ANY form 算已上档
        lora = {"status": "not_ready"}
        for f in forms:
            ls = str(((f.get("identity_adapters") or {}).get("lora") or {}).get("status") or "")
            if ls in {"ready", "training"}:
                lora = {"status": ls}
                break
        chars.append({
            "id": cid,
            "name": str(ch.get("name") or cid),
            "aliases": aliases,
            "form": str(f0.get("form") or "常态"),
            "angle_policy": f0.get("angle_policy") or {},
            "image_adapters": adapters.get("image") or {},
            "lora": lora,
        })
    return chars


def load_clips(root: Path, ep: str) -> List[Dict[str, Any]]:
    try:
        data = json.loads((root / "脚本" / ep / "storyboard.json").read_text(encoding="utf-8"))
    except Exception:
        return []
    return data.get("clips") or data.get("shots") or []


def clip_text(clip: Mapping[str, Any]) -> Tuple[str, str]:
    """(全文本, lens 串)——全文本含 label/scene/desc/continuity，用于角色匹配 + 情绪/角度判定。"""
    parts: List[str] = [str(clip.get("label") or ""), str(clip.get("scene") or "")]
    cont = clip.get("continuity") or {}
    parts += [str(cont.get("start_state") or ""), str(cont.get("end_state") or "")]
    lenses: List[str] = []
    for s in (clip.get("shots") or []):
        if isinstance(s, dict):
            parts.append(str(s.get("desc") or ""))
            lenses.append(str(s.get("lens") or ""))
    return " ".join(parts), " ".join(lenses)


def present_characters(text: str, chars: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    return [c for c in chars if any(a in text for a in c.get("aliases") or set())]


def analyze(root: Path, ep: str) -> Dict[str, Any]:
    chars = load_characters(root)
    clips = load_clips(root, ep)
    default_backend = project_default_backend(root)
    by_id: Dict[str, Dict[str, Any]] = {
        c["id"]: {"char": c, "appear": 0, "closeup": 0, "emotion": 0, "multi": 0, "angle": 0,
                  "angle_tokens": set(), "clips": []}
        for c in chars
    }
    notes: List[str] = []
    if not chars:
        notes.append("identity_registry.json 缺失/无角色——无法算风险分。")
    if not clips:
        notes.append("storyboard.json 缺失/无 clips——先跑 n2d-script 分镜设计再算风险。")
    for clip in clips:
        text, lens = clip_text(clip)
        present = present_characters(text, chars)
        multi = len({c["id"] for c in present}) >= 2
        for c in present:
            agg = by_id[c["id"]]
            agg["appear"] += 1
            agg["clips"].append(str(clip.get("id") or clip.get("label") or ""))
            if is_closeup(lens) or is_closeup(text):
                agg["closeup"] += 1
            if has_strong_emotion(text):
                agg["emotion"] += 1
            if multi:
                agg["multi"] += 1
            toks = extreme_angle_tokens(lens, text, (c.get("angle_policy") or {}).get("risky") or [])
            if toks:
                agg["angle"] += 1
                agg["angle_tokens"].update(toks)
    results: List[Dict[str, Any]] = []
    for cid, agg in by_id.items():
        if agg["appear"] == 0:
            continue
        c = agg["char"]
        tier = lock_tier(default_backend, c.get("image_adapters") or {}, c.get("lora") or {})
        signals = {k: agg[k] for k in ("appear", "closeup", "emotion", "multi", "angle")}
        scored = score_character(signals, tier)
        sug = suggestions_for(c["name"], scored, signals, cid, c["form"], str(root))
        results.append({
            "character_id": cid, "name": c["name"], "form": c["form"],
            "signals": signals, "angle_tokens": sorted(agg["angle_tokens"]),
            "appears_in": agg["clips"], **scored, "suggestions": sug,
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    return {
        "kind": "n2d_face_drift_risk", "version": 1, "root": str(root), "episode": ep,
        "default_backend": default_backend,
        "high": sum(1 for r in results if r["band"] == "high"),
        "medium": sum(1 for r in results if r["band"] == "medium"),
        "characters": results, "notes": notes,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    lines = [
        "# 出图前·脸漂风险分（事前预测·只提示不阻断）",
        "",
        f"- episode: {report.get('episode')} · 默认后端: {report.get('default_backend')}",
        f"- 高危角色 🔴 {report.get('high', 0)} · 中危 🟡 {report.get('medium', 0)}",
        "",
        "| 角色 | 风险 | 分 | 锁脸档 | 主驱动 |",
        "|---|---|---|---|---|",
    ]
    for r in report.get("characters", []):
        drv = "；".join(f"{d['factor']}(+{d['points']})" for d in r.get("drivers", [])[:3])
        lines.append(f"| {r['name']}（{r['character_id']}/{r['form']}） | {icon.get(r['band'],'?')} {r['band']} "
                     f"| {r['score']} | {r['tier']} | {drv} |")
    lines.append("")
    for r in report.get("characters", []):
        if r["band"] == "low" or not r.get("suggestions"):
            continue
        lines.append(f"## {icon.get(r['band'])} {r['name']}（{r['character_id']}/{r['form']}）· 分 {r['score']}")
        for s in r["suggestions"]:
            lines.append(f"- {s}")
        lines.append("")
    for n in report.get("notes", []):
        lines.append(f"- note: {n}")
    lines.append("")
    lines.append("说明：本表是**出图前**的脸漂预案——high/medium 角色按建议提前加强参考/建表情库/上 LoRA，"
                 "比等跨集漂了再由 n2d-identity 事后升档省一大截返工。不阻断出图（落档闸门是 image_qc）。")
    return "\n".join(lines) + "\n"


def run(root: Path, ep: str) -> Dict[str, Any]:
    report = analyze(root, ep)
    out_dir = root / "生产数据"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"face_drift_risk_{ep}.json"
    md_path = out_dir / f"face_drift_risk_{ep}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    report["json_path"] = str(json_path)
    report["markdown_path"] = str(md_path)
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true", help="打印机器可读 report")
    ns = ap.parse_args(argv)
    report = run(Path(ns.root).expanduser().resolve(), ns.episode)
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    print(f"出图前脸漂风险（{ns.episode}·后端 {report['default_backend']}）：🔴 {report['high']} · 🟡 {report['medium']}")
    for r in report["characters"]:
        if r["band"] == "low":
            continue
        print(f"  {icon.get(r['band'])} {r['name']}（{r['character_id']}/{r['form']}）分 {r['score']}·{r['tier']}")
        for s in r["suggestions"]:
            print(f"     - {s}")
    for n in report["notes"]:
        print("ℹ️ " + n)
    print(f"→ {report['markdown_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
