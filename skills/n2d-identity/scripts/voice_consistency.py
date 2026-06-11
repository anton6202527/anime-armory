#!/usr/bin/env python3
"""音色跨集漂移检测（n2d-identity 横切层）。

「一角一色、跨集持久」是 n2d 配音的身份不变量。本脚本读各集
`合成/第N集/配音/时长清单.json`（n2d-voice 产物，逐句条目），做两类对账：

1. 跨集漂移：同一角色在相邻（按集序）可检集之间 voice_key 变了 → drift；
   同一集内同角色出现多个 voice_key 也算 drift（episode_from == episode_to）。
2. voicemap 对账：manifest 实际使用的 voice_key 与 `设定库/voicemap.json`
   （角色→音色注册表，n2d-voice 写）登记的 key 不符 → voicemap_mismatch。

逐句条目若没有音色键字段（契约 `voice_key`，或 n2d-voice 现行的中文字段
`音色键`）则整集标 `insufficient_data`，跳过比对——宁可不报也不报假漂移。

输出（--write，或由 identity.py --write 顺带触发）：
  生产数据/identity_voice_drift_report.json（kind=n2d_identity_voice_drift_report）
  生产数据/identity_voice_drift_report.md

每条 drift / mismatch 都带 batch 回流建议字段（return_to_stage="voice"、
affected_shots、scope），供 n2d-batch 只重配受影响角色/集。纯 stdlib。
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "common"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import (  # noqa: E402  音色一致性契约（单一真值源）
    IDENTITY_VOICE_DRIFT_REPORT_KIND,
    VOICE_KEY_FIELD,
    VOICE_KEY_LEGACY_FIELD,
    VOICE_KEY_PLACEHOLDER_SUFFIX,
    voicemap_path,
)
from n2d_route import episode_number as route_episode_number  # noqa: E402


REPORT_KIND = IDENTITY_VOICE_DRIFT_REPORT_KIND
VERSION = 1

# n2d-voice render_voice.py 现行写的是中文字段「音色键」；契约的标准字段是 voice_key。
# 两个都认（voice_key 优先）。
LEGACY_VOICE_KEY_FIELD = VOICE_KEY_LEGACY_FIELD
# 占位后端（macOS say 应急轨）voice_key 后缀：显式声明「不是 voicemap 注册音色，需重配」——
# 不参与漂移/对账比对（避免假漂移），单独记入 placeholder_revoice 待重配清单。
PLACEHOLDER_SUFFIX = VOICE_KEY_PLACEHOLDER_SUFFIX
# 逐句条目的角色字段（n2d-voice 写中文「角色」；保底也认 char）
CHARACTER_FIELDS = ("角色", "char", "character")
# 镜头定位字段（用于 affected_shots）
SHOT_FIELDS = ("镜头", "shot")

MANIFEST_RELPATH = os.path.join("配音", "时长清单.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def episode_sort_key(ep: str) -> Tuple[int, str]:
    n = route_episode_number(ep)
    return (n if n is not None else 10**9, ep)


def manifest_path(root: Path, ep: str) -> Path:
    return root / "合成" / ep / MANIFEST_RELPATH


def discover_episodes(root: Path) -> List[str]:
    """有配音时长清单的集（按集序排）。"""
    eps = {Path(p).parent.parent.name for p in glob.glob(str(Path(root) / "合成" / "第*集" / MANIFEST_RELPATH))}
    return sorted(eps, key=episode_sort_key)


def _entry_character(entry: Mapping[str, Any]) -> str:
    for field in CHARACTER_FIELDS:
        value = str(entry.get(field, "") or "").strip()
        if value:
            return value
    return ""


def _entry_voice_key(entry: Mapping[str, Any]) -> str:
    for field in (VOICE_KEY_FIELD, LEGACY_VOICE_KEY_FIELD):
        value = str(entry.get(field, "") or "").strip()
        if value:
            return value
    return ""


def _entry_shot(entry: Mapping[str, Any]) -> str:
    for field in SHOT_FIELDS:
        value = str(entry.get(field, "") or "").strip()
        if value:
            return value
    return ""


def parse_episode(root: Path, ep: str) -> Dict[str, Any]:
    """解析一集时长清单 → 逐角色音色使用情况。

    返回：{
      "episode", "manifest", "status": ok|insufficient_data|invalid,
      "lines": 总句数,
      "characters": { 角色: [ {"voice_key", "first_idx", "lines", "shots"} ... 按出现顺序 ] }
    }
    任何带角色的条目缺音色键字段 → 整集 insufficient_data（不报假漂移）。
    """
    path = manifest_path(root, ep)
    rel = str(path.relative_to(root)) if path.is_absolute() else str(path)
    data = load_json(path)
    out: Dict[str, Any] = {"episode": ep, "manifest": rel, "status": "ok", "lines": 0, "characters": {}}
    if not isinstance(data, list):
        out["status"] = "invalid"
        return out
    characters: Dict[str, List[Dict[str, Any]]] = {}
    missing_key = 0
    lines = 0
    for i, entry in enumerate(data):
        if not isinstance(entry, Mapping):
            continue
        char = _entry_character(entry)
        if not char:
            continue
        lines += 1
        key = _entry_voice_key(entry)
        idx = entry.get("idx", i)
        shot = _entry_shot(entry)
        if not key:
            missing_key += 1
            continue
        spans = characters.setdefault(char, [])
        if spans and spans[-1]["voice_key"] == key:
            spans[-1]["lines"] += 1
            if shot and shot not in spans[-1]["shots"]:
                spans[-1]["shots"].append(shot)
        else:
            characters.setdefault(char, spans).append(
                {"voice_key": key, "first_idx": idx, "lines": 1, "shots": [shot] if shot else []}
            )
    out["lines"] = lines
    out["characters"] = characters
    if lines == 0:
        out["status"] = "insufficient_data"
    elif missing_key:
        out["status"] = "insufficient_data"
        out["lines_missing_voice_key"] = missing_key
    return out


def load_voicemap(root: Path) -> Optional[Dict[str, str]]:
    """voicemap.json → {角色: 注册音色键}。文件缺失/不可解析返回 None（跳过对账）。"""
    data = load_json(Path(voicemap_path(str(root))))
    if not isinstance(data, Mapping):
        return None
    out: Dict[str, str] = {}
    for char, cfg in data.items():
        if isinstance(cfg, Mapping):
            key = str(cfg.get("key", "") or "").strip()
        else:
            key = str(cfg or "").strip()
        if key:
            out[str(char).strip()] = key
    return out


def _char_episode_shots(spans: List[Dict[str, Any]]) -> List[str]:
    shots: List[str] = []
    for span in spans:
        for shot in span.get("shots", []):
            if shot not in shots:
                shots.append(shot)
    return shots


def _drift_entry(
    *,
    character: str,
    episode_from: str,
    episode_to: str,
    voice_from: str,
    voice_to: str,
    first_idx: Any,
    spans_to: List[Dict[str, Any]],
) -> Dict[str, Any]:
    affected = _char_episode_shots(spans_to)
    total_lines = sum(int(s.get("lines", 0) or 0) for s in spans_to)
    return {
        "character": character,
        "episode_from": episode_from,
        "episode_to": episode_to,
        "voice_from": voice_from,
        "voice_to": voice_to,
        "first_affected_line_idx": first_idx,
        # batch 回流建议：回 voice 阶段重配该角色整集台词（时长清单变 → 分镜时长也要复核）
        "return_to_stage": "voice",
        "affected_shots": affected,
        "scope": (
            f"{episode_to} 角色「{character}」音色由 {voice_from} 漂为 {voice_to}：该集此角色共 {total_lines} 句"
            f"需按注册音色重配（n2d-voice），重配后时长清单变化需复核分镜时长（n2d-script 阶段2）"
        ),
    }


def build_report(root: Path, generated_at: Optional[str] = None) -> Dict[str, Any]:
    root = Path(root)
    episodes = discover_episodes(root)
    parsed = [parse_episode(root, ep) for ep in episodes]
    notes: List[str] = []
    drifts: List[Dict[str, Any]] = []
    mismatches: List[Dict[str, Any]] = []
    voicemap = load_voicemap(root)
    if voicemap is None:
        notes.append("voicemap.json 缺失或不可解析，跳过 voicemap 对账（n2d-voice 写 设定库/voicemap.json 后启用）")
    unregistered: set = set()

    placeholders: List[Dict[str, Any]] = []
    last_seen: Dict[str, Dict[str, Any]] = {}  # 角色 → {"episode", "voice_key"}
    for ep_info in parsed:
        ep = ep_info["episode"]
        if ep_info["status"] != "ok":
            continue  # insufficient_data / invalid：宁缺勿假，跳过比对
        for char, spans in sorted(ep_info["characters"].items()):
            # 占位应急轨（say:<声音名>#placeholder）单列：声明性"未配真音色"，不进漂移/对账比对
            real_spans = [s for s in spans if not s["voice_key"].endswith(PLACEHOLDER_SUFFIX)]
            placeholder_spans = [s for s in spans if s["voice_key"].endswith(PLACEHOLDER_SUFFIX)]
            if placeholder_spans:
                placeholders.append({
                    "character": char,
                    "episode": ep,
                    "voice_key_used": placeholder_spans[0]["voice_key"],
                    "lines": sum(int(s.get("lines", 0) or 0) for s in placeholder_spans),
                    "first_affected_line_idx": placeholder_spans[0]["first_idx"],
                    "return_to_stage": "voice",
                    "affected_shots": _char_episode_shots(placeholder_spans),
                    "scope": f"{ep} 角色「{char}」为占位应急轨（{placeholder_spans[0]['voice_key']}），需用注册音色重配（n2d-voice）后再出图/合成",
                })
            # ① 同集内多音色（同角色换键，仅真音色键之间比）
            for prev_span, span in zip(real_spans, real_spans[1:]):
                drifts.append(_drift_entry(
                    character=char, episode_from=ep, episode_to=ep,
                    voice_from=prev_span["voice_key"], voice_to=span["voice_key"],
                    first_idx=span["first_idx"], spans_to=real_spans,
                ))
            # ② 跨集换键（与上一可检集对比）
            prev = last_seen.get(char)
            if prev and real_spans and prev["voice_key"] != real_spans[0]["voice_key"]:
                drifts.append(_drift_entry(
                    character=char, episode_from=prev["episode"], episode_to=ep,
                    voice_from=prev["voice_key"], voice_to=real_spans[0]["voice_key"],
                    first_idx=real_spans[0]["first_idx"], spans_to=real_spans,
                ))
            if real_spans:
                last_seen[char] = {"episode": ep, "voice_key": real_spans[-1]["voice_key"]}
            # ③ voicemap 对账：实际用键 vs 注册键（占位键已单列，不算 mismatch）
            if voicemap is not None and real_spans:
                registered = voicemap.get(char, "")
                if not registered:
                    unregistered.add(char)
                else:
                    for span in real_spans:
                        if span["voice_key"] == registered:
                            continue
                        mismatches.append({
                            "character": char,
                            "episode": ep,
                            "voice_key_used": span["voice_key"],
                            "voice_key_registered": registered,
                            "first_affected_line_idx": span["first_idx"],
                            "return_to_stage": "voice",
                            "affected_shots": span.get("shots", []),
                            "scope": (
                                f"{ep} 角色「{char}」实际使用音色 {span['voice_key']} 与 voicemap 注册的"
                                f" {registered} 不符：共 {span.get('lines', 0)} 句需按注册音色重配（n2d-voice）"
                            ),
                        })
    for char in sorted(unregistered):
        notes.append(f"voicemap_unregistered:{char}（角色未在 voicemap 登记，无法对账——建议补登记）")

    episodes_out = [
        {k: v for k, v in info.items() if k != "characters"} | {
            # 报表里每集只留「角色→使用过的音色键序列」摘要，逐句细节留在源 manifest
            "characters": {c: [s["voice_key"] for s in spans] for c, spans in info.get("characters", {}).items()}
        }
        for info in parsed
    ]
    return {
        "kind": REPORT_KIND,
        "version": VERSION,
        "root": str(root),
        "generated_at": generated_at or now_iso(),
        "episodes": episodes_out,
        "drifts": drifts,
        "voicemap_mismatches": mismatches,
        "placeholder_revoice": placeholders,
        "summary": {
            "episodes_total": len(parsed),
            "episodes_checked": sum(1 for e in parsed if e["status"] == "ok"),
            "episodes_insufficient": sum(1 for e in parsed if e["status"] != "ok"),
            "drifts": len(drifts),
            "voicemap_mismatches": len(mismatches),
            "placeholder_revoice": len(placeholders),
        },
        "notes": notes,
    }


def render_md(report: Mapping[str, Any]) -> str:
    s = report.get("summary", {})
    lines = [
        "# 音色跨集漂移报表",
        "",
        f"- root: {report.get('root')}",
        f"- generated_at: {report.get('generated_at')}",
        f"- 可检集: {s.get('episodes_checked', 0)}/{s.get('episodes_total', 0)}（数据不足 {s.get('episodes_insufficient', 0)} 集）",
        f"- 跨集/集内漂移: {s.get('drifts', 0)}；voicemap 不符: {s.get('voicemap_mismatches', 0)}；占位待重配: {s.get('placeholder_revoice', 0)}",
        "",
    ]
    for note in report.get("notes", []):
        lines.append(f"- note: {note}")
    lines.extend(["", "## 各集状态", "", "| 集 | 状态 | 台词句数 | 角色→音色键 |", "|---|---|---|---|"])
    for ep in report.get("episodes", []):
        chars = "; ".join(f"{c}:{'→'.join(keys)}" for c, keys in (ep.get("characters") or {}).items()) or "-"
        lines.append(f"| {ep.get('episode')} | {ep.get('status')} | {ep.get('lines', 0)} | {chars} |")
    drifts = report.get("drifts") or []
    lines.extend(["", "## 漂移明细", ""])
    if not drifts:
        lines.append("- 无（可检范围内同角色音色跨集稳定）")
    for d in drifts:
        lines.append(
            f"- 「{d.get('character')}」{d.get('episode_from')}→{d.get('episode_to')}：{d.get('voice_from')} → {d.get('voice_to')}"
            f"（首个受影响句 idx={d.get('first_affected_line_idx')}）"
        )
        lines.append(f"  - 回流：return_to_stage={d.get('return_to_stage')}；{d.get('scope')}")
    mismatches = report.get("voicemap_mismatches") or []
    lines.extend(["", "## voicemap 对账", ""])
    if not mismatches:
        lines.append("- 无不符（或 voicemap 缺失已在 note 提示）")
    for m in mismatches:
        lines.append(
            f"- 「{m.get('character')}」{m.get('episode')}：实际用 {m.get('voice_key_used')}，注册为 {m.get('voice_key_registered')}"
            f"（首个受影响句 idx={m.get('first_affected_line_idx')}）"
        )
        lines.append(f"  - 回流：return_to_stage={m.get('return_to_stage')}；{m.get('scope')}")
    placeholders = report.get("placeholder_revoice") or []
    if placeholders:
        lines.extend(["", "## 占位应急轨待重配", ""])
        for p in placeholders:
            lines.append(f"- 「{p.get('character')}」{p.get('episode')}：{p.get('voice_key_used')}（{p.get('lines', 0)} 句）")
            lines.append(f"  - 回流：return_to_stage={p.get('return_to_stage')}；{p.get('scope')}")
    return "\n".join(lines)


def write_outputs(root: Path, report: Mapping[str, Any]) -> Dict[str, Path]:
    out_dir = Path(root) / "生产数据"
    paths = {
        "json": out_dir / "identity_voice_drift_report.json",
        "md": out_dir / "identity_voice_drift_report.md",
    }
    atomic_write_text(paths["json"], json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["md"], render_md(report) + "\n")
    return paths


def main() -> int:
    ap = argparse.ArgumentParser(description="n2d 音色跨集漂移检测（时长清单 voice_key × voicemap 对账）")
    ap.add_argument("root")
    ap.add_argument("--write", action="store_true", help="写 生产数据/identity_voice_drift_report.{json,md}")
    ap.add_argument("--json", action="store_true", help="打印 JSON 报表")
    ns = ap.parse_args()
    root = Path(ns.root)
    report = build_report(root)
    if ns.write:
        for p in write_outputs(root, report).values():
            print(f"wrote {p}")
    elif ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_md(report))
    s = report.get("summary", {})
    return 1 if s.get("drifts", 0) or s.get("voicemap_mismatches", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
