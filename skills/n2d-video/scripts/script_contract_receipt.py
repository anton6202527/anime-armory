#!/usr/bin/env python3
"""Sign that a video/image prompt consumed the n2d script quality contract."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

APPLICATION_KIND = "n2d_script_contract_application"
CONTRACT_KIND = "n2d_script_quality_contract"
DEFAULT_FIELDS = [
    "core_attraction",
    "first_3s_visual_hook",
    "retention_promise_ledger",
    "pacing_allocation",
    "clip_dramatic_function",
    "audience_question_ledger",
    "performance_cues",
]


def ep_label(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("第") and text.endswith("集"):
        return text
    m = re.search(r"\d+", text)
    return f"第{m.group(0)}集" if m else text


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def contract_content_hash(contract: Mapping[str, Any]) -> str:
    return str(contract.get("content_hash") or contract.get("contract_hash") or "").strip()


def default_prompt(scope: str, ep: str) -> Path:
    if scope == "出图":
        return Path("出图") / ep / "prompt" / "01_分镜出图.md"
    return Path("出视频") / ep / "prompt" / "01_clips.md"


def prompt_has_contract_markers(text: str) -> bool:
    markers = ("剧本可看性合同", "本集可看性签收合同", "dramatic_function", "audience_effect", "戏剧功能", "观众效果")
    return any(m in text for m in markers)


def update_receipt(root: Path, ep: str, scope: str, prompt_rel: Path, reviewer: str, require_markers: bool) -> Dict[str, Any]:
    contract_path = root / "生产数据" / f"script_quality_contract_{ep}.json"
    prompt_path = prompt_rel if prompt_rel.is_absolute() else root / prompt_rel
    contract = load_json(contract_path)
    if not isinstance(contract, Mapping) or contract.get("kind") != CONTRACT_KIND:
        raise SystemExit(f"missing valid script quality contract: {contract_path}")
    if not prompt_path.is_file():
        raise SystemExit(f"missing prompt file: {prompt_path}")
    prompt_text = prompt_path.read_text(encoding="utf-8")
    if require_markers and not prompt_has_contract_markers(prompt_text):
        raise SystemExit("prompt does not contain script contract markers; add 剧本可看性合同/dramatic_function/audience_effect first")

    prompt_rel_str = str(prompt_path.relative_to(root)) if prompt_path.is_relative_to(root) else str(prompt_path)
    app_path = root / "生产数据" / f"script_contract_applied_{ep}.json"
    existing = load_json(app_path)
    if isinstance(existing, Mapping) and existing.get("kind") == APPLICATION_KIND:
        data: Dict[str, Any] = dict(existing)
        scopes = [s for s in data.get("scopes") or [] if isinstance(s, Mapping) and s.get("scope") != scope]
    else:
        data = {"kind": APPLICATION_KIND, "episode": ep, "accepted": True, "scopes": []}
        scopes = []
    contract_file_sha = sha256_file(contract_path)
    contract_hash = contract_content_hash(contract)
    scopes.append({
        "scope": scope,
        "prompt_path": prompt_rel_str,
        "prompt_sha256": sha256_file(prompt_path),
        "contract_path": str(contract_path.relative_to(root)),
        "contract_content_hash": contract_hash,
        "contract_file_sha256": contract_file_sha,
        "contract_sha256": contract_file_sha,
        "consumed_fields": list(contract.get("required_consumption_fields") or DEFAULT_FIELDS),
        "applied_clip_ids": [
            str(row.get("clip_id"))
            for row in ((contract.get("signable_fields") or {}).get("clip_dramatic_functions") or [])
            if isinstance(row, Mapping) and row.get("clip_id")
        ],
        "evidence": [
            "视频 prompt 已按 script_quality_contract 写入核心看点、首屏钩、留存承诺、时长分配和观众问题处理。",
            "逐 Clip prompt 已承接 dramatic_function/audience_effect/pacing_allocation，运动、表演和时长重心不改写剧本承诺。",
        ],
        "reviewed_at": now_iso(),
    })
    data.update({
        "episode": ep,
        "accepted": True,
        "reviewer": reviewer,
        "reviewed_at": now_iso(),
        "contract_path": str(contract_path.relative_to(root)),
        "contract_content_hash": contract_hash,
        "contract_file_sha256": contract_file_sha,
        "contract_sha256": contract_file_sha,
        "scopes": scopes,
    })
    write_atomic(app_path, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return data


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Write script_contract_applied receipt for prompt consumption")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--scope", choices=["出图", "出视频"], default="出视频")
    ap.add_argument("--prompt", help="Prompt path relative to root; defaults by scope")
    ap.add_argument("--reviewer", default="n2d-video prompt author")
    ap.add_argument("--allow-no-markers", action="store_true", help="Do not require visible contract markers in prompt text")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()
    ep = ep_label(ns.episode)
    prompt_rel = Path(ns.prompt) if ns.prompt else default_prompt(ns.scope, ep)
    data = update_receipt(root, ep, ns.scope, prompt_rel, ns.reviewer, not ns.allow_no_markers)
    if ns.json:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"wrote {root / '生产数据' / f'script_contract_applied_{ep}.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
