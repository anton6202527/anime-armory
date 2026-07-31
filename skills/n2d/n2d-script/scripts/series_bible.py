#!/usr/bin/env python3
"""series_bible.py — n2d 剧级 Show Bible / Narrative Graph 汇总器。

目标：把分散在 storyboard、identity_registry、asset_registry、术语表、音乐/UI/包装/生产配方中的
“剧级真值”收束成 `设定库/series_bible.json/md`。它不改写下游素材，只生成一个可读、可审的总入口，
让后续拆集、出图、出视频和审片都能知道：这个项目到底锁了哪些叙事线、人物、地点、资产、风格和生产配方。

用法：
  python3 skills/n2d/n2d-script/scripts/series_bible.py <作品根> --write
  python3 skills/n2d/n2d-script/scripts/series_bible.py <作品根> --json
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

KIND = "n2d_series_bible"
VERSION = 1

HOOK_RE = re.compile(r"(🪝|⚡|💥|钩子|爽点|反转|真相|危机|突然|系统|升级|身份|秘密|悬念)")
THREAD_RE = re.compile(r"(到底是谁|为什么|真相|秘密|身世|系统|任务|证据|伏笔|账册|令牌|法宝)")
CORE_RE = re.compile(r"全篇|全程|长线|核心|主角|女主|男主|主反派|常驻")
ASSET_RE = re.compile(r"\b(?:LOC|PROP|WEAPON|OUTFIT|VFX)_[A-Za-z0-9_\-\u4e00-\u9fff]+\b")
CHAR_RE = re.compile(r"\bCHAR_[A-Za-z0-9_\-\u4e00-\u9fff]+\b")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def ep_num(value: str) -> int:
    m = re.search(r"\d+", str(value or ""))
    return int(m.group(0)) if m else 10**9


def normalize_ep(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("第") and text.endswith("集"):
        return text
    m = re.search(r"\d+", text)
    return f"第{m.group(0)}集" if m else text


def discover_episodes(root: Path) -> List[str]:
    eps = [Path(p).parent.name for p in glob.glob(str(root / "脚本" / "第*集" / "*"))]
    return sorted(set(eps), key=ep_num)


def episode_text(root: Path, ep: str) -> str:
    base = root / "脚本" / ep
    parts = []
    for name in ("raw.txt", "voiceover.txt", "分镜剧本.md", "故事板.md", "storyboard.json"):
        parts.append(read_text(base / name))
    return "\n".join(parts)


def storyboard(root: Path, ep: str) -> Tuple[Optional[dict], List[dict]]:
    data = load_json(root / "脚本" / ep / "storyboard.json")
    if not isinstance(data, dict):
        return None, []
    clips = data.get("clips") or data.get("shots") or []
    return data, [c for c in clips if isinstance(c, dict)]


def flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return " ".join(flatten_text(v) for v in value)
    if isinstance(value, dict):
        return " ".join([str(k) + " " + flatten_text(v) for k, v in value.items()])
    return str(value)


def unique(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def extract_hooks(text: str, limit: int = 6) -> List[str]:
    hooks = []
    for line in text.splitlines():
        if HOOK_RE.search(line):
            hooks.append(line.strip()[:120])
        if len(hooks) >= limit:
            break
    return hooks


def extract_threads(text: str) -> List[str]:
    hits = []
    for m in THREAD_RE.finditer(text or ""):
        start = max(0, m.start() - 18)
        end = min(len(text), m.end() + 28)
        hits.append(re.sub(r"\s+", " ", text[start:end]).strip())
    return unique(hits)[:8]


def episode_node(root: Path, ep: str) -> Dict[str, Any]:
    data, clips = storyboard(root, ep)
    text = episode_text(root, ep)
    clip_rows = []
    for i, clip in enumerate(clips, 1):
        blob = flatten_text(clip)
        clip_rows.append({
            "id": str(clip.get("id") or clip.get("clip_id") or clip.get("label") or f"Clip_{i:02d}"),
            "characters": unique(clip.get("character_ids") or CHAR_RE.findall(blob)),
            "assets": unique(ASSET_RE.findall(blob)),
            "hook_signal": bool(HOOK_RE.search(blob)),
        })
    return {
        "episode": ep,
        "has_storyboard": data is not None,
        "clip_count": len(clips),
        "hooks": extract_hooks(text),
        "threads": extract_threads(text),
        "characters": unique(x for row in clip_rows for x in row["characters"]),
        "assets": unique(x for row in clip_rows for x in row["assets"]),
        "clips": clip_rows,
    }


def load_identity(root: Path) -> Tuple[List[dict], List[dict]]:
    data = load_json(root / "出图" / "共享" / "identity_registry.json")
    findings: List[dict] = []
    if not isinstance(data, dict):
        findings.append({"severity": "warn", "code": "missing_identity_registry", "message": "缺 identity_registry.json，series_bible 只能建立叙事层，无法汇总角色 DNA。"})
        return [], findings
    chars = [c for c in data.get("characters") or [] if isinstance(c, dict)]
    for char in chars:
        cid = str(char.get("id") or "")
        core = bool(CORE_RE.search(flatten_text({k: char.get(k) for k in ("scope", "tier", "role", "name")})))
        for form in char.get("forms") or []:
            if not isinstance(form, dict):
                continue
            sig = form.get("performance_signature") or char.get("performance_signature")
            if core and not sig:
                findings.append({
                    "severity": "warn",
                    "code": "core_character_missing_performance_signature",
                    "message": f"核心/长线角色 {cid}/{form.get('form') or '常态'} 缺 performance_signature。",
                    "character_id": cid,
                })
    return chars, findings


def load_assets(root: Path) -> Tuple[List[dict], List[dict]]:
    data = load_json(root / "出图" / "共享" / "asset_registry.json")
    if not isinstance(data, dict):
        return [], [{"severity": "info", "code": "missing_asset_registry", "message": "缺 asset_registry.json；若尚未进入出图阶段可接受，出图前需补。"}]
    assets = data.get("assets") or data.get("items") or []
    if isinstance(assets, dict):
        assets = [{**(v if isinstance(v, dict) else {}), "id": k} for k, v in assets.items()]
    return [a for a in assets if isinstance(a, dict)], []


def existing_rel(root: Path, rel: str) -> Optional[str]:
    return rel if (root / rel).exists() else None


def build_series_bible(root: Path, episodes: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    eps = [normalize_ep(e) for e in episodes] if episodes else discover_episodes(root)
    nodes = [episode_node(root, ep) for ep in eps]
    chars, char_findings = load_identity(root)
    assets, asset_findings = load_assets(root)
    findings: List[dict] = []
    findings.extend(char_findings)
    findings.extend(asset_findings)
    if not nodes:
        findings.append({"severity": "warn", "code": "no_episode_nodes", "message": "未发现脚本/第N集产物，series_bible 只会生成空剧级骨架。"})
    if any(not n["has_storyboard"] for n in nodes):
        missing = [n["episode"] for n in nodes if not n["has_storyboard"]]
        findings.append({"severity": "info", "code": "episode_missing_storyboard", "message": "部分集缺 storyboard.json：" + "、".join(missing[:8])})
    roots = {
        "global_style": existing_rel(root, "设定库/global_style.md"),
        "角色圣经": existing_rel(root, "设定库/角色圣经.md"),
        "setup_payoff_ledger": existing_rel(root, "设定库/setup_payoff_ledger.json"),
        "narrative_state_ledger": existing_rel(root, "设定库/narrative_state_ledger.json"),
        "story_integrity_ledger": existing_rel(root, "设定库/story_integrity_ledger.json"),
        "thread_scheduler": existing_rel(root, "设定库/thread_scheduler.json"),
        "leitmotif_registry": existing_rel(root, "设定库/leitmotif_registry.json"),
        "ambient_map": existing_rel(root, "设定库/ambient_map.json"),
        "ui_asset_registry": existing_rel(root, "设定库/ui_asset_registry.json"),
        "translation_glossary": existing_rel(root, "设定库/translation_glossary.json"),
        "series_packaging": existing_rel(root, "设定库/series_packaging.json"),
        "location_spatial_memory": existing_rel(root, "设定库/location_spatial_memory.json"),
        "scene_floorplan": existing_rel(root, "设定库/scene_floorplan.json"),
    }
    missing_optional = [k for k, v in roots.items() if v is None and k not in {"角色圣经"}]
    if missing_optional:
        findings.append({"severity": "info", "code": "series_layers_not_registered", "message": "以下剧级层尚未登记：" + "、".join(missing_optional[:12])})
    return {
        "kind": KIND,
        "version": VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "root": str(root),
        "episodes": eps,
        "truth_sources": roots,
        "narrative_graph": {
            "episode_nodes": nodes,
            "thread_count": sum(len(n.get("threads") or []) for n in nodes),
            "hook_count": sum(len(n.get("hooks") or []) for n in nodes),
        },
        "characters": [{
            "id": c.get("id"),
            "name": c.get("name"),
            "scope": c.get("scope"),
            "forms": [{
                "form": f.get("form"),
                "asset_key": f.get("asset_key"),
                "has_performance_signature": bool(f.get("performance_signature") or c.get("performance_signature")),
                "signature_equipment": f.get("signature_equipment") or c.get("signature_equipment"),
            } for f in (c.get("forms") or []) if isinstance(f, dict)],
        } for c in chars],
        "assets": [{
            "id": a.get("id") or a.get("asset_id"),
            "name": a.get("name"),
            "type": a.get("type"),
            "has_reference_group": isinstance(a.get("reference_group"), dict),
            "has_drift_forbidden": bool(a.get("drift_forbidden")),
        } for a in assets],
        "findings": findings,
    }


def render_md(bible: Mapping[str, Any]) -> str:
    ng = bible.get("narrative_graph") if isinstance(bible.get("narrative_graph"), Mapping) else {}
    lines = [
        "# n2d Series Bible",
        "",
        f"- kind: {bible.get('kind')}",
        f"- episodes: {len(bible.get('episodes') or [])}",
        f"- hooks: {ng.get('hook_count', 0)}",
        f"- threads: {ng.get('thread_count', 0)}",
        "",
        "## 真值源",
    ]
    sources = bible.get("truth_sources") if isinstance(bible.get("truth_sources"), Mapping) else {}
    for key, value in sources.items():
        lines.append(f"- {key}: {value or '未登记'}")
    lines += ["", "## 每集叙事图", "", "| 集 | Clips | 角色 | 资产 | 钩子 | 线程 |", "|---|---:|---|---|---|---|"]
    for node in ng.get("episode_nodes") or []:
        lines.append(
            f"| {node.get('episode')} | {node.get('clip_count', 0)} | "
            f"{'、'.join(node.get('characters') or []) or '-'} | "
            f"{'、'.join(node.get('assets') or []) or '-'} | "
            f"{len(node.get('hooks') or [])} | {len(node.get('threads') or [])} |"
        )
    lines += ["", "## 角色表演签名", "", "| 角色 | 形态 | performance_signature | signature_equipment |", "|---|---|---|---|"]
    for char in bible.get("characters") or []:
        for form in char.get("forms") or []:
            lines.append(
                f"| {char.get('id')} {char.get('name') or ''} | {form.get('form') or '常态'} | "
                f"{'ready' if form.get('has_performance_signature') else 'missing'} | {form.get('signature_equipment') or '-'} |"
            )
    findings = bible.get("findings") or []
    if findings:
        lines += ["", "## Findings"]
        for f in findings:
            lines.append(f"- {str(f.get('severity') or 'info').upper()} [{f.get('code')}] {f.get('message')}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, bible: Mapping[str, Any]) -> Tuple[Path, Path]:
    jp = root / "设定库" / "series_bible.json"
    mp = root / "设定库" / "series_bible.md"
    write_json_atomic(jp, bible)
    write_text_atomic(mp, render_md(bible))
    return jp, mp


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d 剧级 Show Bible / Narrative Graph 汇总器")
    ap.add_argument("root")
    ap.add_argument("--episodes", nargs="*", help="只汇总指定集，如 第1集 第2集")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="warn 退出码也置 1（默认仅 block 失败）")
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()
    bible = build_series_bible(root, ns.episodes)
    if ns.write:
        jp, mp = write_outputs(root, bible)
        bible["outputs"] = {"json": str(jp), "md": str(mp)}
    if ns.json:
        print(json.dumps(bible, ensure_ascii=False, indent=2))
    else:
        print(render_md(bible))
    severities = {str(f.get("severity") or "") for f in bible.get("findings", [])}
    if "block" in severities:
        return 1
    if ns.strict and "warn" in severities:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
