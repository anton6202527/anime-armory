#!/usr/bin/env python3
"""story_quality_pack.py — 文本期剧情可看性增强包。

P1 目标：在不触发图片/视频成本前，把“观众想追什么、上下集怎么接、角色怎么演”
变成机器可读侧车，供出图 prompt / 出视频 prompt 继承。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

KIND = "n2d_story_quality_pack"
QUESTION_RE = re.compile(r"(真相|秘密|到底是谁|为什么|为何|身世|系统|任务|线索|证据|背叛|怀疑)")
PAYOFF_RE = re.compile(r"(揭穿|发现|终于|因此|于是|反杀|打脸|兑现|证明|救出|夺回|升级|突破)")
HOOK_RE = re.compile(r"(🪝|集尾|突然|真相|危机|来了|不可能|怎么会|门外|脚步)")
CHAR_RE = re.compile(r"\bCHAR_[A-Za-z0-9_\-\u4e00-\u9fff]+\b")


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def ep_label(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("第") and text.endswith("集"):
        return text
    m = re.search(r"\d+", text)
    return f"第{m.group(0)}集" if m else text


def ep_num(value: str) -> int:
    m = re.search(r"\d+", str(value or ""))
    return int(m.group(0)) if m else 0


def prior_ep(ep: str) -> Optional[str]:
    n = ep_num(ep)
    return f"第{n - 1}集" if n > 1 else None


def flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    if isinstance(value, dict):
        return " ".join(str(k) + " " + flatten(v) for k, v in value.items())
    return str(value or "")


def text_for_episode(root: Path, ep: str) -> str:
    base = root / "脚本" / ep
    return "\n".join(read(base / name) for name in ("voiceover.txt", "分镜剧本.md", "故事板.md", "storyboard.json"))


def storyboard(root: Path, ep: str) -> List[dict]:
    data = load_json(root / "脚本" / ep / "storyboard.json")
    clips = data.get("clips") if isinstance(data, dict) else []
    return [c for c in clips or [] if isinstance(c, dict)]


def clip_id(clip: Mapping[str, Any], idx: int) -> str:
    return str(clip.get("id") or clip.get("clip_id") or clip.get("label") or f"Clip_{idx:02d}")


def _context(text: str, match: re.Match[str], pad: int = 28) -> str:
    start = max(0, match.start() - pad)
    end = min(len(text), match.end() + pad)
    return re.sub(r"\s+", " ", text[start:end]).strip()


def audience_question_ledger(root: Path, ep: str) -> Dict[str, Any]:
    text = text_for_episode(root, ep)
    rows: List[Dict[str, Any]] = []
    payoff_hits = [_context(text, m) for m in PAYOFF_RE.finditer(text)]
    for idx, m in enumerate(QUESTION_RE.finditer(text), 1):
        q = _context(text, m)
        rows.append({
            "question_id": f"Q{idx:02d}",
            "signal": m.group(0),
            "question_context": q,
            "status": "paid_or_progressed" if payoff_hits else "open",
            "expected_next_handling": "本集兑现/推进" if payoff_hits else "下一集冷开场或集尾钩必须接住",
        })
    ending_hook = bool(HOOK_RE.search(" ".join(text.splitlines()[-8:])))
    findings: List[Dict[str, Any]] = []
    if rows and not ending_hook and not payoff_hits:
        findings.append({"severity": "warn", "code": "open_questions_without_hook", "message": "本集留下观众问题，但集尾缺钩子或兑现进展。"})
    return {"questions": rows, "payoff_contexts": payoff_hits[:8], "ending_hook": ending_hook, "findings": findings}


def _keywords(text: str) -> set:
    words = set()
    for pat in (QUESTION_RE, HOOK_RE, PAYOFF_RE, CHAR_RE):
        words.update(m.group(0) for m in pat.finditer(text or ""))
    return words


def boundary_continuation(root: Path, ep: str) -> Dict[str, Any]:
    prev = prior_ep(ep)
    if not prev:
        return {"available": False, "reason": "第1集无上集边界", "status": "n/a"}
    prev_text = text_for_episode(root, prev)
    cur_text = text_for_episode(root, ep)
    prev_tail = "\n".join(prev_text.splitlines()[-10:])
    cur_head = "\n".join(cur_text.splitlines()[:10])
    overlap = sorted(_keywords(prev_tail) & _keywords(cur_head))
    status = "pass" if overlap else "warn"
    return {
        "available": bool(prev_text and cur_text),
        "previous_episode": prev,
        "previous_tail": prev_tail[:500],
        "current_head": cur_head[:500],
        "shared_signals": overlap,
        "status": status,
        "finding": None if overlap else "上集尾钩和本集冷开场缺共享信号；检查是否断承接。",
    }


def load_signatures(root: Path) -> Dict[str, Mapping[str, Any]]:
    data = load_json(root / "出图" / "共享" / "identity_registry.json")
    out: Dict[str, Mapping[str, Any]] = {}
    if not isinstance(data, dict):
        return out
    for char in data.get("characters") or []:
        if not isinstance(char, Mapping):
            continue
        cid = str(char.get("id") or "")
        char_sig = char.get("performance_signature")
        for form in char.get("forms") or []:
            if not isinstance(form, Mapping):
                continue
            key = f"{cid}/{form.get('form') or '常态'}"
            sig = form.get("performance_signature") or char_sig
            if isinstance(sig, Mapping):
                out[key] = sig
            elif sig:
                out[key] = {"freeform": sig}
    return out


def signature_text(sig: Mapping[str, Any]) -> str:
    parts = []
    for key in ("micro_expression", "gaze", "stance", "habitual_gesture", "speech_rhythm", "action_style", "freeform"):
        val = sig.get(key)
        if val:
            parts.append(f"{key}={val}")
    return "；".join(parts)


def _id_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [x.strip() for x in re.split(r"[,，、\s]+", value) if x.strip()]
    return []


def clip_character_ids(clip: Mapping[str, Any]) -> List[str]:
    # `character_ids: []` is an explicit object/location-only shot.  Do not
    # fall back to scanning the whole clip, because side-car fields such as
    # forbidden_presence may intentionally contain CHAR_* IDs that must not be
    # injected into downstream performance prompts.
    if "character_ids" in clip:
        return list(dict.fromkeys(_id_list(clip.get("character_ids"))))

    ent = clip.get("entity_schedule")
    if isinstance(ent, Mapping):
        scheduled = _id_list(ent.get("characters"))
        if scheduled:
            return list(dict.fromkeys(scheduled))

    ignored = {"entity_schedule", "forbidden_presence", "offscreen_presence", "forbidden_characters"}
    blob = flatten({k: v for k, v in clip.items() if k not in ignored})
    forbidden: set[str] = set()
    if isinstance(ent, Mapping):
        forbidden.update(_id_list(ent.get("forbidden_presence")))
        forbidden.update(_id_list(ent.get("offscreen_presence")))
    chars = [x for x in CHAR_RE.findall(blob) if x not in forbidden]
    return list(dict.fromkeys(chars))


def performance_prompt_cues(root: Path, ep: str) -> List[Dict[str, Any]]:
    sigs = load_signatures(root)
    cues: List[Dict[str, Any]] = []
    for idx, clip in enumerate(storyboard(root, ep), 1):
        cid = clip_id(clip, idx)
        chars = clip_character_ids(clip)
        rows = []
        for char_id in chars:
            matches = [(key, val) for key, val in sigs.items() if key.startswith(f"{char_id}/")]
            for key, sig in matches[:2]:
                rows.append({"character_form": key, "prompt_cue": signature_text(sig)})
        if rows:
            cues.append({
                "clip": cid,
                "performance_signature_prompt": rows,
                "inject_into": ["image_prompt.performance", "video_prompt.performance", "voice_or_native_av.direction"],
            })
    return cues


def digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def build_pack(root: Path, ep: str) -> Dict[str, Any]:
    ep = ep_label(ep)
    questions = audience_question_ledger(root, ep)
    boundary = boundary_continuation(root, ep)
    cues = performance_prompt_cues(root, ep)
    pack = {
        "kind": KIND,
        "version": 1,
        "episode": ep,
        "audience_question_ledger": questions,
        "boundary_continuation": boundary,
        "performance_prompt_cues": cues,
        "summary": {
            "open_questions": sum(1 for q in questions.get("questions") or [] if q.get("status") == "open"),
            "performance_cue_clips": len(cues),
            "boundary_status": boundary.get("status"),
        },
        "notes": ["文本期 report-only；不把时长升成硬门，只加强剧情可看性和下游 prompt 继承。"],
    }
    pack["pack_hash"] = digest(pack)
    return pack


def render_md(pack: Mapping[str, Any]) -> str:
    s = pack.get("summary") or {}
    lines = [
        "# 剧情质量生产包",
        "",
        f"- episode: {pack.get('episode')}",
        f"- open_questions: {s.get('open_questions')}",
        f"- boundary_status: {s.get('boundary_status')}",
        f"- performance_cue_clips: {s.get('performance_cue_clips')}",
        "",
        "## 观众问题账本",
        "",
        "| ID | Signal | Status | Handling |",
        "|---|---|---|---|",
    ]
    ql = (pack.get("audience_question_ledger") or {}).get("questions") or []
    for q in ql:
        lines.append(f"| {q.get('question_id')} | {q.get('signal')} | {q.get('status')} | {q.get('expected_next_handling')} |")
    b = pack.get("boundary_continuation") or {}
    lines += ["", "## 集间承接", "", f"- status: {b.get('status')}", f"- shared_signals: {'、'.join(b.get('shared_signals') or []) or '-'}", ""]
    lines += ["## 表演签名 Prompt Cues", "", "| Clip | Cues |", "|---|---|"]
    for cue in pack.get("performance_prompt_cues") or []:
        txt = "<br>".join(f"{r.get('character_form')}: {r.get('prompt_cue')}" for r in cue.get("performance_signature_prompt") or [])
        lines.append(f"| {cue.get('clip')} | {txt or '-'} |")
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, ep: str, pack: Mapping[str, Any]) -> Tuple[Path, Path]:
    out = root / "生产数据"
    jp = out / f"story_quality_pack_{ep}.json"
    mp = out / f"story_quality_pack_{ep}.md"
    write_atomic(jp, json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_atomic(mp, render_md(pack))
    return jp, mp


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d 文本期剧情质量增强包")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()
    ep = ep_label(ns.episode)
    pack = build_pack(root, ep)
    if ns.write:
        jp, mp = write_outputs(root, ep, pack)
        pack["outputs"] = {"json": str(jp), "md": str(mp)}
    if ns.json:
        print(json.dumps(pack, ensure_ascii=False, indent=2))
    else:
        print(render_md(pack))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
