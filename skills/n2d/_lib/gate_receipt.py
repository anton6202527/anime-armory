#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gate-receipt verification — couple `_进度.md` advancement to *verified, fresh* evidence.

The architectural linchpin against "闸验声明不验现实"（gate certifies claims, not reality）：
`progress.py set <gated-col> ✅` must not be a free-text write. Before a paid/consequential
production column is marked done, there must be a gate **receipt** that proves three things:

  1. the gate actually ran for this (episode, stage)              → 凭据存在
  2. it passed (0 block-severity findings)                        → 闸门真绿
  3. it still describes the CURRENT artifacts on disk             → 内容指纹新鲜

This module reuses what the pipeline already writes — `dashboard.py gate --stage X` persists
`生产数据/gate_findings_{stage}_{ep}.json` carrying `summary.severity` + `inputs_fingerprint`
(`gate_findings_payload`), and `skill_snapshot.fingerprint_is_fresh` recomputes the content
fingerprint. We add the missing coupling: advancement consults the receipt.

Fail-closed by design (design law: missing evidence = inconclusive = BLOCK, never silent pass):
no receipt / stale receipt / fingerprint-less receipt all REFUSE the ✅. The single, loud,
audited escape hatch is `N2D_PROGRESS_ALLOW_UNVERIFIED=1`, which records a waiver (accruing
debt) instead of silently passing.

Pure stdlib + same-`_lib` imports only (no cross-skill import) so it runs on the user's
machine with no VCS and Chinese paths, exactly like the rest of n2d/_lib.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from typing import Any, Dict, NamedTuple, Optional

from n2d_route import cell_state, normalize_episode

try:
    from skill_snapshot import fingerprint_is_fresh
except Exception:  # pragma: no cover - snapshot helper should always be present
    fingerprint_is_fresh = None  # type: ignore[assignment]

# 生产数据目录 + gate findings 命名，与 n2d-dashboard 的 production_dir / GATE_FINDINGS_PREFIX
# 保持一致（跨线不 import，故在此复刻这两个稳定常量）。
PRODUCTION_DIRNAME = "生产数据"
GATE_FINDINGS_PREFIX = "gate_findings"

# 受闸列 → gate_stage。**只挂花钱/不可逆/交付的后果性列**（出图/出视频/合成/验收）；
# 廉价的纯文本 prompt 列（出图prompt/视频prompt）不在此——它们的 preflight 闸在 runner 里
# 付费前已跑，无需用进度耦合再挡一道，且更易误报。判据=「这一步是否真烧素材/产出交付物」。
ENFORCED_COLUMN_GATE_STAGE: Dict[str, str] = {
    "出图": "image",
    "视频": "video",
    "成片": "compose",
    "验收": "review",
}

WAIVER_LEDGER = "progress_unverified_waivers.jsonl"
ALLOW_ENV = "N2D_PROGRESS_ALLOW_UNVERIFIED"


class ReceiptVerdict(NamedTuple):
    ok: bool          # True = 允许写 ✅（已验证 / 非受闸 / 非完成态）
    enforced: bool    # True = 这是一次受闸的完成态写入，真正过了凭据校验
    code: str         # verified / not_gated / not_complete / no_receipt / gate_failed / stale / unverifiable / no_fingerprint_tool
    stage: str        # 对应 gate_stage（非受闸为 ""）
    message: str      # 人读说明（含可执行修复指令）

    @property
    def needs_evidence(self) -> bool:
        return self.enforced and not self.ok


def gate_findings_path(root: str, ep: str, stage: str) -> str:
    return os.path.join(
        root, PRODUCTION_DIRNAME, f"{GATE_FINDINGS_PREFIX}_{stage}_{normalize_episode(ep)}.json"
    )


def _load_findings(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _block_count(payload: Dict[str, Any]) -> int:
    """block-severity 计数：优先 summary.severity.block，缺则从 findings 现场数（口径冗余防漂移）。"""
    summary = payload.get("summary")
    if isinstance(summary, dict):
        sev = summary.get("severity")
        if isinstance(sev, dict) and "block" in sev:
            try:
                return int(sev.get("block") or 0)
            except (TypeError, ValueError):
                pass
    findings = payload.get("findings")
    if isinstance(findings, list):
        counts = Counter(
            str(f.get("sev") or "").lower() for f in findings if isinstance(f, dict)
        )
        return counts.get("block", 0)
    return 0


def _gate_cmd(root: str, ep: str, stage: str) -> str:
    return (
        f'python3 skills/n2d-dashboard/scripts/dashboard.py gate "{root}" {normalize_episode(ep)} '
        f"--stage {stage}"
    )


def verify_receipt(root: str, ep: str, stage: str) -> ReceiptVerdict:
    """Core: does a *fresh, passing* gate receipt exist for (ep, stage)?

    Decoupled from any progress column so other consumers (dashboard waiver-debt
    rollup, series ledger) can ask the same question and tell whether an earlier
    unverified ✅ has since been销账（销债=对当前产物重跑闸门并通过）。
    """
    path = gate_findings_path(root, ep, stage)
    payload = _load_findings(path)
    if payload is None:
        return ReceiptVerdict(
            False, True, "no_receipt", stage,
            f"缺闸门凭据：未找到 {os.path.relpath(path, root) if path.startswith(root) else path}。"
            f"先真跑闸门再回写 ✅ → {_gate_cmd(root, ep, stage)}",
        )

    blocks = _block_count(payload)
    if blocks > 0:
        return ReceiptVerdict(
            False, True, "gate_failed", stage,
            f"闸门未过：{stage} 仍有 {blocks} 个 block 级问题（见 {os.path.basename(path)}）。"
            f"修掉 block 后重跑 → {_gate_cmd(root, ep, stage)}",
        )

    if fingerprint_is_fresh is None:
        return ReceiptVerdict(
            False, True, "no_fingerprint_tool", stage,
            "无法加载 skill_snapshot.fingerprint_is_fresh，不能证明凭据对应当前产物；fail-closed 拒绝。",
        )

    fresh = fingerprint_is_fresh(payload.get("inputs_fingerprint"), root)
    if fresh is None:
        return ReceiptVerdict(
            False, True, "unverifiable", stage,
            f"闸门凭据缺 `inputs_fingerprint`，无法证明它对应当前产物（产物可能在闸门后被重出）。"
            f"重跑闸门以盖新鲜指纹 → {_gate_cmd(root, ep, stage)}",
        )
    if fresh is False:
        return ReceiptVerdict(
            False, True, "stale", stage,
            f"闸门凭据已陈旧：{stage} 跑过后产物又变了（图/契约/storyboard 被改），旧绿不算数。"
            f"对当前产物重跑闸门 → {_gate_cmd(root, ep, stage)}",
        )
    return ReceiptVerdict(True, True, "verified", stage, f"闸门凭据已验证（{stage} 绿且指纹新鲜）。")


def is_receipt_valid(root: str, ep: str, stage: str) -> bool:
    """True iff a fresh, passing receipt exists for (ep, stage) — used to销账 old waivers."""
    return verify_receipt(root, ep, stage).ok


def reconcile_progress(root: str, ep: str) -> list:
    """H3 交付侧对账：扫该集 `_进度.md` 里所有受闸列标 ✅(done) 的列，凡无 fresh+green 凭据即一条
    violation。把 ✅ 从「可写真值」降级成「待背书声明」——抓住绕过 `progress.do_set` 的手写/带外 ✅
    （凭据耦合只活在 do_set，sed/编辑器/别的写路径都是构造性旁路·H3）。返回 [] = 全部背书。

    供 compose/review 闸在交付前**重新从凭据推导真相**，与 do_set 写时校验互为第二/第三防线。"""
    try:
        from n2d_route import parse_progress
    except Exception:  # pragma: no cover
        return []
    try:
        _header, rows = parse_progress(root)
    except (FileNotFoundError, ValueError, OSError):
        return []  # 无进度表 → 无可对账（缺表本身由别的闸/路由处理）
    target = normalize_episode(ep)
    violations: list = []
    for row in rows:
        if normalize_episode(row.get("_ep") or row.get("集") or "") != target:
            continue
        for col, stage in ENFORCED_COLUMN_GATE_STAGE.items():
            if cell_state(row.get(col, "")) != "done":
                continue  # 只查标完成(✅)的受闸列
            verdict = verify_receipt(root, ep, stage)
            if not verdict.ok:
                violations.append({
                    "column": col, "gate_stage": stage,
                    "code": verdict.code, "message": verdict.message,
                })
        break
    return violations


def check_advance(root: str, ep: str, col: str, val: str) -> ReceiptVerdict:
    """Decide whether `progress.py set` may write `val` into `col` for `ep`.

    Only the *done* transition on a受闸列 is enforced; rough/partial/todo/na/数字未满 都放行
    （它们本就不是「这一步已交付」的声明）。
    """
    stage = ENFORCED_COLUMN_GATE_STAGE.get(col)
    if stage is None:
        return ReceiptVerdict(True, False, "not_gated", "", f"「{col}」非受闸列，按声明回写。")
    if cell_state(val) != "done":
        return ReceiptVerdict(True, False, "not_complete", stage, f"「{col}」= {val} 非完成态，无需凭据。")
    return verify_receipt(root, ep, stage)


def unresolved_waivers(root: str) -> list:
    """Read the waiver ledger and drop lines whose (episode, stage) now has a valid receipt.

    Append-only ledger means销账后旧行仍在；按 (episode, gate_stage) 去重取最近一条，
    再剔除「现已有新鲜凭据」的，剩下的才是真欠债，供 dashboard/series 计债不误报。
    """
    path = os.path.join(root, PRODUCTION_DIRNAME, WAIVER_LEDGER)
    latest: Dict[tuple, Dict[str, Any]] = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                key = (rec.get("episode"), rec.get("gate_stage"))
                latest[key] = rec  # 后写覆盖：保留该 (集,阶段) 最近一次 waiver
    except OSError:
        return []
    out = []
    for (ep, stage), rec in latest.items():
        if ep and stage and is_receipt_valid(root, ep, stage):
            continue  # 已销账
        out.append(rec)
    return out


def allow_override() -> bool:
    return os.environ.get(ALLOW_ENV, "").strip() not in ("", "0", "false", "False")


def record_waiver(root: str, ep: str, col: str, verdict: ReceiptVerdict, *, reason: str = "") -> str:
    """Append a loud, accruing waiver line so an unverified ✅ is never silent debt."""
    from datetime import datetime, timezone

    path = os.path.join(root, PRODUCTION_DIRNAME, WAIVER_LEDGER)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    line = {
        "kind": "n2d_progress_unverified_waiver",
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "episode": normalize_episode(ep),
        "column": col,
        "gate_stage": verdict.stage,
        "code": verdict.code,
        "reason": reason or os.environ.get("N2D_WAIVER_REASON", ""),
        "message": verdict.message,
    }
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    return path
