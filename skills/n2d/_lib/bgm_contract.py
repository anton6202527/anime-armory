#!/usr/bin/env python3
"""Structured BGM contract for n2d compose/release gates."""
from __future__ import annotations

import json
import hashlib
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping

KIND = "n2d_bgm_contract"
VERSION = 1
STRATEGIES = {"none", "licensed_file", "generated", "placeholder"}


def sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def contract_path(root: str | Path, episode: str) -> Path:
    return Path(root) / "合成" / episode / "bgm_contract.json"


def _read_bgm_lines(root: Path, episode: str) -> List[str]:
    path = root / "脚本" / episode / "bgm.txt"
    try:
        return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")]
    except OSError:
        return []


def _setting(root: Path, key: str) -> str:
    try:
        text = (root / "_设置.md").read_text(encoding="utf-8")
    except OSError:
        return ""
    m = re.search(rf"(?:^|\n)\s*[-*]?\s*{re.escape(key)}\s*[:：]\s*([^\n#]+)", text)
    return m.group(1).strip() if m else ""


def scaffold(root: str | Path, episode: str) -> Dict[str, Any]:
    root_path = Path(root)
    source = _setting(root_path, "BGM来源")
    strategy = "placeholder"
    if any(token in source.lower() for token in ("无", "none", "不要")):
        strategy = "none"
    elif any(token in source.lower() for token in ("本地", "素材", "授权", "licensed")):
        strategy = "licensed_file"
    elif any(token in source.lower() for token in ("生成", "suno", "udio", "ai")):
        strategy = "generated"
    return {
        "kind": KIND,
        "version": VERSION,
        "episode": episode,
        # 明确选择 none 不需要版权或生成来源，可作为安全、可逆的
        # one-click 交付默认。其他策略仍保持 draft，等待真实文件/来源证据。
        "status": "confirmed" if strategy == "none" else "draft",
        "strategy": strategy,
        "source": {
            "file": "",
            "model": "",
            "channel": "",
            "license_or_rights_ref": "",
        },
        "cues": [{"id": f"BGM_{i:02d}", "intent": line, "start_sec": None, "end_sec": None}
                 for i, line in enumerate(_read_bgm_lines(root_path, episode), 1)],
        "mix": {"ducking": True, "tension_envelope": True, "target_gain_db": -12.0},
        "placeholder_approval": {"approved": False, "approved_by": "", "scope": "internal_rough_only"},
        "note": "status=confirmed 后才可进正式 compose；placeholder 必须显式批准且只用于 internal rough。",
    }


def load(root: str | Path, episode: str) -> Dict[str, Any]:
    try:
        value = json.loads(contract_path(root, episode).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def validate(
    root: str | Path,
    episode: str,
    payload: Mapping[str, Any] | None = None,
    *,
    allow_placeholder: bool = True,
) -> List[Dict[str, str]]:
    root_path = Path(root)
    data = dict(payload or load(root_path, episode))
    issues: List[Dict[str, str]] = []

    def issue(code: str, message: str) -> None:
        issues.append({"code": code, "severity": "block", "message": message})

    if data.get("kind") != KIND or int(data.get("version") or 0) < VERSION:
        issue("bgm_contract_missing_or_invalid", "缺有效 bgm_contract.json；先生成并确认 BGM 机器合同。")
        return issues
    if str(data.get("episode") or "") != episode:
        issue("bgm_episode_mismatch", "bgm_contract.episode 与当前集不一致。")
    if str(data.get("status") or "").lower() not in {"confirmed", "approved", "ready"}:
        issue("bgm_contract_unconfirmed", "BGM 合同尚未 confirmed；不得把默认占位静默混入母版。")
    strategy = str(data.get("strategy") or "")
    if strategy not in STRATEGIES:
        issue("bgm_strategy_invalid", f"BGM strategy 必须是 {sorted(STRATEGIES)}。")
        return issues
    cues = data.get("cues") if isinstance(data.get("cues"), list) else []
    if strategy != "none" and not any(isinstance(row, Mapping) and str(row.get("intent") or "").strip() for row in cues):
        issue("bgm_cues_missing", "启用 BGM 但 cues 为空；bgm.txt 的情绪/卡点意图没有进入机器合同。")
    source = data.get("source") if isinstance(data.get("source"), Mapping) else {}
    if strategy == "licensed_file":
        raw = str(source.get("file") or "")
        path = Path(raw) if Path(raw).is_absolute() else root_path / raw
        if not raw or not path.is_file():
            issue("bgm_file_missing", "licensed_file 缺可读取的 BGM 文件。")
        if not str(source.get("license_or_rights_ref") or "").strip():
            issue("bgm_rights_missing", "licensed_file 缺授权/版权来源引用。")
    elif strategy == "generated":
        if not str(source.get("model") or "").strip() or not str(source.get("channel") or "").strip():
            issue("bgm_generation_provenance_missing", "生成式 BGM 必须分列具体 model 与 channel。")
        raw = str(source.get("file") or "")
        path = Path(raw) if Path(raw).is_absolute() else root_path / raw
        if not raw or not path.is_file():
            issue("bgm_generated_file_missing", "生成式 BGM 尚未落真实音频文件。")
        receipt_path = contract_path(root_path, episode).with_name("bgm_generation_receipt.json")
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except Exception:
            receipt = {}
        if receipt.get("kind") != "n2d_bgm_generation_receipt" or receipt.get("status") != "pass":
            issue("bgm_generation_receipt_missing", "生成式 BGM 缺 pass 生成/登记收据；运行 gen_bgm.py --run 或 --register-existing。")
        elif path.is_file() and receipt.get("output_sha256") != sha256_file(path):
            issue("bgm_generation_receipt_stale", "BGM 文件已变化，生成收据哈希过期。")
        elif receipt.get("contract_sha256") != sha256_file(contract_path(root_path, episode)):
            issue("bgm_generation_contract_stale", "BGM 合同已变化，生成收据未重签。")
    elif strategy == "placeholder":
        approval = data.get("placeholder_approval") if isinstance(data.get("placeholder_approval"), Mapping) else {}
        if approval.get("approved") is not True or not str(approval.get("approved_by") or "").strip():
            issue("bgm_placeholder_unapproved", "程序化占位 BGM 只可用于 internal rough，且必须显式填写 approved/approved_by。")
        if str(approval.get("scope") or "") != "internal_rough_only":
            issue("bgm_placeholder_scope_invalid", "占位 BGM scope 必须是 internal_rough_only，不能冒充发布母版配乐。")
        if not allow_placeholder:
            issue("bgm_placeholder_not_deliverable", "占位 BGM 只允许内部粗剪；review/发布母版必须换成真实授权/生成配乐，或明确选择 strategy=none。")
    return issues


def write_missing(root: str | Path, episode: str) -> Path:
    path = contract_path(root, episode)
    if path.is_file():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(scaffold(root, episode), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


__all__ = ["KIND", "VERSION", "STRATEGIES", "contract_path", "load", "scaffold", "sha256_file", "validate", "write_missing"]
