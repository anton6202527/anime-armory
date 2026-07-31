#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mv-review 传统 MV 手法机检（craft audit · report-only · 出图前跑）。

shot_variety_audit 管"视觉不重复"，本脚本管**传统 MV 导演/剪辑手艺里可机检的结构律**——
这些是真人 MV 片场几十年沉淀的工艺，AI 产线不该因为"没有片场"就丢掉：

  chorus_escalation   副歌复现升级律：每次副歌回归都要加码（换机位/加场景/提运镜能量/上母题
                      变体），末副歌给全曲最大 payoff——"first chorus 是第一视觉峰值，最终
                      chorus 是最大 payoff" 是行业标准结构。
  dynamics_contrast   动静对比律：副歌运镜能量必须高于主歌（没有对比就没有冲击）；主歌就把
                      运镜拉满 = 副歌没有升级空间（headroom 耗尽）。
  hook_visibility     hook 上脸律：副歌 hook 至少一次对镜头演唱（近景）——表演线是 MV 三线
                      （performance/narrative/b-roll）之锚；纯叙事 MV 自检后可忽略。
  opening_hook        冷开场律：竖屏平台前 3 秒定生死；开场在出现任何钩信号（key 镜/副歌/
                      动作峰值/近景）之前拖太久 → 流失。
  key_clip_coverage   关键镜候选律（shoot options for the edit）：片场给关键 setup 拍保险
                      take，AI 等价物 = 副歌/key 镜出 2-3 张首帧候选再挑，不许单张裸奔。
  bridge_look_shift   bridge 换气律：bridge 是音乐转折，画面应同步转折（换场景/换色调/换
                      能量）——传统导演最容易忽视的一拍。
  lyric_visual_echo   词画呼应（弱信号 info）：全曲画面描述与歌词意象零重合时提示自检——
                      语义呼应机器判不准，只提示不定罪。

全部读 `分镜/clip_plan.json`（+ `词/lyrics.md`），不读像素、不花钱。产物
`生产数据/craft_audit/craft_audit.{json,md}`，全 advisory（最高 warn 永不 block），退出恒 0。
用法：python3 craft_audit.py <制MV作品根> [--write] [--json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from typing import Any
from datetime import date

VERSION = 1
KIND = "mv_craft_audit"
SEVERITIES = ("block", "warn", "info")


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


# 冷开场：出现首个钩信号前的累计时长超过此秒数 → warn（竖屏短视频口径，可 env 放宽）。
OPEN_HOOK_SECONDS = _float_env("MV_OPEN_HOOK_SECONDS", 8.0)
# 主歌平均运镜能量 ≥ 此值 → 副歌没有升级空间（能量满格 2.0）。
VERSE_ENERGY_CEILING = _float_env("MV_VERSE_ENERGY_CEILING", 1.5)
# 词画呼应：歌词有效意象 bigram 至少这么多才判（太短的词不判）。
LYRIC_ECHO_MIN_BIGRAMS = 8

CHORUS_RE = re.compile(r"chorus|副歌|drop|hook|refrain|高潮|climax", re.IGNORECASE)
VERSE_RE = re.compile(r"verse|主歌", re.IGNORECASE)
BRIDGE_RE = re.compile(r"bridge|桥段|桥\b|间奏|solo", re.IGNORECASE)
CLOSEUP_RE = re.compile(r"大?特写|近景|closeup|close-?up|\bE?CU\b|face|脸部|面部", re.IGNORECASE)
HIGH_CAM_RE = re.compile(r"甩|环绕|旋转|冲|穿越|穿梭|升降|急推|快速推|whip|orbit|crash|zoom|变焦|fly|手持", re.IGNORECASE)
MID_CAM_RE = re.compile(r"推|拉|摇|移|跟拍|环视|dolly|pan|tilt|track|steadicam", re.IGNORECASE)
STATIC_CAM_RE = re.compile(r"固定|静止|锁定|定格|不动|无运镜|static|still|locked|hold", re.IGNORECASE)
CJK_RE = re.compile(r"[一-鿿]")
LYRIC_STOP_CHARS = set("的了你我他她它是在不有和与也都一这那就要将把上下中大小又并却而已"
                       "其之于为呢吗啊哦呀吧个们来去到说想看听让像被从对没很还")


def _sha256(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def finding(severity: str, code: str, message: str, clips: list[str] | None = None) -> dict[str, Any]:
    return {
        "severity": severity if severity in SEVERITIES else "info",
        "code": code,
        "message": message,
        "clips": clips or [],
    }


def _norm(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def _sd(clip: dict[str, Any]) -> dict[str, Any]:
    sd = clip.get("shot_design")
    return sd if isinstance(sd, dict) else {}


def _cid(clip: dict[str, Any]) -> str:
    return str(clip.get("clip_id"))


def _location_key(clip: dict[str, Any]) -> str:
    sd = _sd(clip)
    return _norm(sd.get("location_id") or sd.get("setup_group") or sd.get("location_name") or clip.get("section"))


def _is_chorusish(clip: dict[str, Any]) -> bool:
    if _norm(clip.get("beat_role")) == "key":
        return True
    return bool(CHORUS_RE.search(str(clip.get("section") or "")))


def _is_versish(clip: dict[str, Any]) -> bool:
    return bool(VERSE_RE.search(str(clip.get("section") or "")))


def _is_bridgish(clip: dict[str, Any]) -> bool:
    return bool(BRIDGE_RE.search(str(clip.get("section") or "")))


def camera_energy(clip: dict[str, Any]) -> int | None:
    """运镜能量分：2=高动态（甩/环绕/冲…）、1=常规运动（推/拉/摇/移…）、0=静止；写不清 → None 不臆造。"""
    cam = " ".join(str(_sd(clip).get(k) or "") for k in ("camera_movement", "lens_feel"))
    if not cam.strip():
        return None
    if HIGH_CAM_RE.search(cam):
        return 2
    if STATIC_CAM_RE.search(cam):
        return 0
    if MID_CAM_RE.search(cam):
        return 1
    return None


def _is_performance(clip: dict[str, Any]) -> bool:
    return _norm(clip.get("action_family")) == "performance_vocal" or bool(clip.get("vocal_lyrics"))


def chorus_instances(clips: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """连续 chorusish clip 的 run = 一次副歌复现实例。"""
    instances: list[list[dict[str, Any]]] = []
    run: list[dict[str, Any]] = []
    for clip in clips:
        if _is_chorusish(clip):
            run.append(clip)
        elif run:
            instances.append(run)
            run = []
    if run:
        instances.append(run)
    return instances


def _instance_signature(instance: list[dict[str, Any]]) -> dict[str, Any]:
    energies = [e for e in (camera_energy(c) for c in instance) if e is not None]
    return {
        "locations": {_location_key(c) for c in instance if _location_key(c)},
        "sizes": {_norm(_sd(c).get("shot_size")) for c in instance if _norm(_sd(c).get("shot_size"))},
        "motifs": {_norm(c.get("visual_motif")) for c in instance if _norm(c.get("visual_motif"))},
        "max_energy": max(energies) if energies else None,
        "count": len(instance),
    }


def audit_chorus_escalation(clips: list[dict[str, Any]], findings: list[dict[str, Any]]) -> int:
    """副歌复现升级律：第 k(≥2) 次副歌若无任何新元素（新场景/新景别/新母题/更高运镜能量/更多镜）→ warn。"""
    instances = chorus_instances(clips)
    if len(instances) < 2:
        return 0
    hits = 0
    seen_locations: set[str] = set()
    seen_sizes: set[str] = set()
    seen_motifs: set[str] = set()
    prev_max_energy: int | None = None
    prev_count = 0
    sigs = [_instance_signature(inst) for inst in instances]
    for k, (inst, sig) in enumerate(zip(instances, sigs), start=1):
        if k > 1:
            gained = bool(sig["locations"] - seen_locations) or bool(sig["sizes"] - seen_sizes) \
                or bool(sig["motifs"] - seen_motifs) \
                or (sig["max_energy"] is not None and prev_max_energy is not None and sig["max_energy"] > prev_max_energy) \
                or sig["count"] > prev_count
            if not gained:
                ids = [_cid(c) for c in inst]
                findings.append(finding("warn", "chorus_no_escalation",
                                        f"第 {k} 次副歌（{ids[0]}…{ids[-1]}）相比前面副歌无任何视觉升级"
                                        "（没有新场景/新景别/新母题/更高运镜能量/更多镜头）——传统 MV 每次副歌"
                                        "回归都要加码，末副歌给全曲最大 payoff；回 mv-plan 给这段换机位/加场景/提能量", ids))
                hits += 1
        seen_locations |= sig["locations"]
        seen_sizes |= sig["sizes"]
        seen_motifs |= sig["motifs"]
        if sig["max_energy"] is not None:
            prev_max_energy = sig["max_energy"] if prev_max_energy is None else max(prev_max_energy, sig["max_energy"])
        prev_count = max(prev_count, sig["count"])
    first, last = sigs[0], sigs[-1]
    if (last["count"] < first["count"]
            and last["max_energy"] is not None and first["max_energy"] is not None
            and last["max_energy"] <= first["max_energy"]):
        findings.append(finding("info", "final_chorus_not_maximal",
                                f"末副歌镜头数（{last['count']}）少于首副歌（{first['count']}）且运镜能量未超——"
                                "若非刻意收束（余韵型结尾），考虑把最大 payoff 留给末副歌"))
        hits += 1
    return hits


def audit_dynamics_contrast(clips: list[dict[str, Any]], findings: list[dict[str, Any]]) -> int:
    """动静对比律：副歌平均运镜能量应高于主歌；主歌拉满则没有升级空间。"""
    chorus = [e for e in (camera_energy(c) for c in clips if _is_chorusish(c)) if e is not None]
    verse = [e for e in (camera_energy(c) for c in clips if _is_versish(c) and not _is_chorusish(c)) if e is not None]
    if len(chorus) < 2 or len(verse) < 2:
        return 0
    hits = 0
    chorus_avg = sum(chorus) / len(chorus)
    verse_avg = sum(verse) / len(verse)
    if chorus_avg <= verse_avg:
        findings.append(finding("warn", "no_dynamics_contrast",
                                f"副歌平均运镜能量 {chorus_avg:.2f} 不高于主歌 {verse_avg:.2f}——"
                                "没有对比就没有冲击：主歌收着（缓推/跟拍/留白），副歌放（甩/环绕/冲击变焦），"
                                "把能量差做出来"))
        hits += 1
    elif verse_avg >= VERSE_ENERGY_CEILING:
        findings.append(finding("info", "verse_energy_ceiling",
                                f"主歌平均运镜能量已达 {verse_avg:.2f}（≥{VERSE_ENERGY_CEILING}）——"
                                "主歌就拉满，副歌升无可升；考虑主歌降档，给副歌留 headroom"))
        hits += 1
    return hits


def audit_hook_visibility(clips: list[dict[str, Any]], findings: list[dict[str, Any]]) -> int:
    """hook 上脸律：副歌至少一次对镜头演唱近景；全片无表演线时只 info 自检。"""
    instances = chorus_instances(clips)
    if not instances:
        return 0
    performers = [c for c in clips if _is_performance(c)]
    if not performers:
        findings.append(finding("info", "no_performance_line",
                                "全曲没有任何演唱表演镜（performance_vocal/vocal_lyrics）——纯叙事/纯氛围 MV "
                                "合法，但请自检是刻意选择而非漏排；表演线是传统 MV 三线之锚"))
        return 1
    lacking: list[str] = []
    for inst in instances:
        ok = any(_is_performance(c) and CLOSEUP_RE.search(str(_sd(c).get("shot_size") or "")) for c in inst)
        if not ok:
            lacking.append(f"{_cid(inst[0])}…{_cid(inst[-1])}")
    if lacking:
        findings.append(finding("warn", "hook_not_sung_on_camera",
                                f"{len(lacking)}/{len(instances)} 次副歌没有对镜头演唱的近景（{'；'.join(lacking)}）——"
                                "hook 至少一次上脸唱（传统 MV 铁律）；回 mv-plan 在副歌段排一个 performance_vocal 近景"))
        return 1
    return 0


def audit_opening_hook(clips: list[dict[str, Any]], findings: list[dict[str, Any]]) -> int:
    """冷开场律：首个钩信号（key 镜/副歌/动作峰值/近景）出现前的累计时长 > 阈值 → warn。"""
    elapsed = 0.0
    have_duration = False
    pre_hook: list[str] = []
    for clip in clips:
        hooked = (_is_chorusish(clip) or bool(str(clip.get("action_peak") or "").strip())
                  or CLOSEUP_RE.search(str(_sd(clip).get("shot_size") or "")))
        if hooked:
            break
        pre_hook.append(_cid(clip))
        try:
            elapsed += float(clip.get("duration"))
            have_duration = True
        except (TypeError, ValueError):
            pass
    else:
        if clips:
            findings.append(finding("warn", "no_hook_signal_at_all",
                                    "全曲没有任何钩信号（key 镜/副歌/动作峰值/近景）——分镜还没写实或结构缺爆点",
                                    [_cid(c) for c in clips[:5]]))
            return 1
        return 0
    late = (have_duration and elapsed > OPEN_HOOK_SECONDS) or (not have_duration and len(pre_hook) > 3)
    if late:
        shown = f"{elapsed:.1f}s" if have_duration else f"{len(pre_hook)} 个 clip"
        findings.append(finding("warn", "cold_open_too_long",
                                f"开场 {shown} 内没有任何钩信号（首钩前：{'、'.join(pre_hook[:6])}）——"
                                f"竖屏平台前 3 秒定生死（阈值 {OPEN_HOOK_SECONDS}s 已放宽）；"
                                "开场镜给身份/悬念/冲击其一，或把一个副歌意象前置当 cold open", pre_hook))
        return 1
    return 0


CANDIDATE_KEYS = ("candidate_count", "takes_planned", "image_candidates", "best_of")


def audit_key_clip_coverage(clips: list[dict[str, Any]], findings: list[dict[str, Any]]) -> int:
    """关键镜候选律：副歌/key 镜应计划 ≥2 张首帧候选（shoot options for the edit）。"""
    key_clips = [c for c in clips if _is_chorusish(c)]
    if not key_clips:
        return 0
    has_field = any(any(k in c for k in CANDIDATE_KEYS) for c in clips)
    if not has_field:
        ids = [_cid(c) for c in key_clips]
        findings.append(finding("info", "key_clip_coverage_unplanned",
                                f"{len(ids)} 个副歌/key 镜未见候选计划字段（{'/'.join(CANDIDATE_KEYS)}）——"
                                "片场惯例是给关键 setup 拍保险 take：关键镜出 2-3 张首帧候选再挑，"
                                "别单张裸奔进出视频", ids[:8]))
        return 1
    weak = [_cid(c) for c in key_clips
            if max((int(c.get(k) or 0) for k in CANDIDATE_KEYS if k in c), default=0) < 2]
    if weak:
        findings.append(finding("warn", "key_clip_single_candidate",
                                f"{len(weak)} 个副歌/key 镜候选数 <2：{'、'.join(weak[:8])}——"
                                "关键镜单张裸奔，崩了就是重排期；出 2-3 张候选再挑", weak))
        return 1
    return 0


def audit_bridge_look_shift(clips: list[dict[str, Any]], findings: list[dict[str, Any]]) -> int:
    """bridge 换气律：bridge 段没有引入任何新场景/新母题、能量也不变 → info（最易被忽视的一拍）。"""
    bridge = [c for c in clips if _is_bridgish(c)]
    if not bridge:
        return 0
    others = [c for c in clips if not _is_bridgish(c)]
    seen_loc = {_location_key(c) for c in others if _location_key(c)}
    seen_motif = {_norm(c.get("visual_motif")) for c in others if _norm(c.get("visual_motif"))}
    b_loc = {_location_key(c) for c in bridge if _location_key(c)}
    b_motif = {_norm(c.get("visual_motif")) for c in bridge if _norm(c.get("visual_motif"))}
    b_energy = [e for e in (camera_energy(c) for c in bridge) if e is not None]
    o_energy = [e for e in (camera_energy(c) for c in others) if e is not None]
    energy_shift = bool(b_energy and o_energy) and abs(sum(b_energy) / len(b_energy) - sum(o_energy) / len(o_energy)) >= 0.5
    if not (b_loc - seen_loc) and not (b_motif - seen_motif) and not energy_shift:
        ids = [_cid(c) for c in bridge]
        findings.append(finding("info", "bridge_no_look_shift",
                                f"bridge/间奏段（{ids[0]}…{ids[-1]}）没换场景、没上新母题、能量也没变——"
                                "音乐在转折而画面没跟上；传统手法：bridge 换色调/换空间/换能量至少其一", ids))
        return 1
    return 0


def _lyric_lines(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or re.match(r"^\[[^\]]+\]$", line):
            continue
        out.append(line)
    return out


def _content_bigrams(text: str) -> set[str]:
    chars = [ch for ch in text if CJK_RE.match(ch) and ch not in LYRIC_STOP_CHARS]
    return {a + b for a, b in zip(chars, chars[1:])}


def audit_lyric_visual_echo(clips: list[dict[str, Any]], lyrics_text: str,
                            findings: list[dict[str, Any]]) -> int:
    """词画呼应（弱信号）：歌词意象与画面描述零重合 → info 自检；机器不判语义好坏。"""
    if not lyrics_text.strip():
        return 0
    corpus_parts = []
    for clip in clips:
        for key in ("desc", "description", "visual_motif", "action_peak", "action"):
            corpus_parts.append(str(clip.get(key) or ""))
    corpus = " ".join(corpus_parts)
    if not corpus.strip():
        return 0
    bigrams = set()
    for line in _lyric_lines(lyrics_text):
        bigrams |= _content_bigrams(line)
    if len(bigrams) < LYRIC_ECHO_MIN_BIGRAMS:
        return 0
    matched = [bg for bg in bigrams if bg in corpus]
    if not matched:
        findings.append(finding("info", "lyric_visual_echo_zero",
                                f"歌词 {len(bigrams)} 个意象片段与全部画面描述零重合——"
                                "若非刻意的纯抽象/反差 MV，考虑把 2-3 个核心歌词意象落进对应段落的画面"))
        return 1
    return 0


def summary_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    out = {key: 0 for key in SEVERITIES}
    for item in items:
        sev = item.get("severity")
        if sev in out:
            out[sev] += 1
    return out


def build_report(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    plan_rel = "分镜/clip_plan.json"
    lyrics_rel = "词/lyrics.md"
    plan_path = os.path.join(root, plan_rel)
    lyrics_path = os.path.join(root, lyrics_rel)
    plan = load_json(plan_path)
    findings: list[dict[str, Any]] = []
    notes: list[str] = []
    if not isinstance(plan, dict):
        notes.append("缺 分镜/clip_plan.json——先跑 mv-plan 再做传统手法机检。")
        clips: list[dict[str, Any]] = []
    else:
        clips = [c for c in (plan.get("clips") or []) if isinstance(c, dict)]
        if not clips:
            notes.append("clip_plan 里没有 clips。")
    if clips:
        audit_chorus_escalation(clips, findings)
        audit_dynamics_contrast(clips, findings)
        audit_hook_visibility(clips, findings)
        audit_opening_hook(clips, findings)
        audit_key_clip_coverage(clips, findings)
        audit_bridge_look_shift(clips, findings)
        lyrics_text = ""
        if os.path.isfile(lyrics_path):
            try:
                with open(lyrics_path, encoding="utf-8") as fh:
                    lyrics_text = fh.read()
            except OSError:
                lyrics_text = ""
        audit_lyric_visual_echo(clips, lyrics_text, findings)
    counts = summary_counts(findings)
    return {
        "schema_version": VERSION,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "engine": "mv-review/scripts/craft_audit.py",
        "inputs_sha256": {plan_rel: _sha256(plan_path), lyrics_rel: _sha256(lyrics_path)},
        "thresholds": {
            "open_hook_seconds": OPEN_HOOK_SECONDS,
            "verse_energy_ceiling": VERSE_ENERGY_CEILING,
            "lyric_echo_min_bigrams": LYRIC_ECHO_MIN_BIGRAMS,
        },
        "summary": {
            **counts,
            "block": 0,  # 恒 0：本层永不制造 block
            "clips_checked": len(clips),
            "verdict": "review" if counts["warn"] else "ok",
        },
        "findings": findings,
        "notes": notes,
    }


def render_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# MV 传统手法机检（craft audit · 事前 · advisory）",
        "",
        f"- generated_at: {report.get('generated_at')}",
        f"- clips_checked: {s.get('clips_checked')}",
        f"- verdict: {s.get('verdict')}   warn: {s.get('warn')}   info: {s.get('info')}",
        "",
        "## Findings",
        "",
    ]
    if not report.get("findings"):
        lines.append("- （无违反传统手法结构律的项）")
    for item in report.get("findings") or []:
        clips = f"  · clips: {', '.join(item.get('clips') or [])}" if item.get("clips") else ""
        lines.append(f"- [{item.get('severity')}] {item.get('code')}: {item.get('message')}{clips}")
    for note in report.get("notes") or []:
        lines.append(f"- [note] {note}")
    return "\n".join(lines).rstrip() + "\n"


def write_report(root: str, report: dict[str, Any]) -> tuple[str, str]:
    out_dir = os.path.join(root, "生产数据", "craft_audit")
    json_path = os.path.join(out_dir, "craft_audit.json")
    md_path = os.path.join(out_dir, "craft_audit.md")
    write_json(json_path, report)
    write_text(md_path, render_markdown(report))
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="MV 传统手法机检（report-only）")
    ap.add_argument("project_root")
    ap.add_argument("--write", action="store_true", help="落盘 生产数据/craft_audit/craft_audit.{json,md}")
    ap.add_argument("--json", action="store_true", help="打印机器可读 JSON")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.project_root):
        print(f"[err] 找不到作品根：{args.project_root}")
        return 2
    report = build_report(args.project_root)
    if args.write:
        json_path, md_path = write_report(report["project_root"], report)
        print(f"[ok] craft audit JSON → {json_path}")
        print(f"[ok] craft audit MD   → {md_path}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(report))
    return 0  # report-only：永不因 finding 退非零


if __name__ == "__main__":
    raise SystemExit(main())
