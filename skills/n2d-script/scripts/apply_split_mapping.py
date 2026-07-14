#!/usr/bin/env python3
"""Apply a human-approved source-unit split window without corrupting downstream work.

The command replaces one materialized raw-only prefix/window, splices the untouched
machine suffix at ``next_source_unit_id``, refreshes the compact plan/index/progress,
and writes a rollback backup plus an immutable SHA receipt.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
import re
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import split_novel as SN  # noqa: E402

KIND = "n2d_approved_split_mapping"
RECEIPT_KIND = "n2d_split_mapping_application_receipt"
VERSION = 1
EMPTY_DOWNSTREAM = {"", "⬜", "—", "-", "na", "n/a"}


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_sha(data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha_bytes(payload)


def _unit_index(value: Any) -> int:
    match = re.fullmatch(r"U(\d{6})", str(value or "").strip())
    if not match:
        raise ValueError(f"非法 source unit ID: {value!r}；应为 U000001")
    return int(match.group(1))


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} 顶层必须是对象")
    return data


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp, path)
    except Exception:
        try:
            os.unlink(temp)
        except FileNotFoundError:
            pass
        raise


def _normalize_source(root: Path, plan: dict[str, Any]) -> tuple[Path, list[str]]:
    source_rel = str(plan.get("source_text") or "")
    source = (root / source_rel).resolve()
    if not source.is_file() or root.resolve() not in source.parents:
        raise ValueError("split_plan.source_text 缺失或越出作品根")
    text = SN.read_text(str(source))
    # write_split_plan hashes through text-mode open(), whose universal-newline
    # contract turns CRLF/CR into LF. Match that contract before deciding that
    # a source changed; the source-unit hash below independently validates body
    # semantics after paragraph normalization.
    text_mode_view = text.replace("\r\n", "\n").replace("\r", "\n")
    actual_source_sha = SN.sha256_text(text_mode_view.rstrip())
    if actual_source_sha != str(plan.get("source_text_sha256") or ""):
        raise ValueError("规范源文本 SHA 已漂移；先重建/迁移 split_plan，不得套用旧批准映射")
    paras = SN.strip_frontmatter(SN.normalize_paragraphs(text))
    units = plan.get("source_units") or {}
    if isinstance(units, dict):
        if len(paras) != int(units.get("count") or 0):
            raise ValueError("规范化段落数与 split_plan source_units.count 不一致")
        if SN.sha256_text("\n".join(paras)) != str(units.get("normalized_text_sha256") or ""):
            raise ValueError("规范化 source-unit SHA 已漂移")
    else:
        # iter_source_units validates verbose v2 rows against the same source axis.
        hydrated = list(SN.iter_source_units(plan, paras))
        if len(hydrated) != len(paras):
            raise ValueError("verbose source-unit 轴不完整")
    return source, paras


def _validate_mapping(mapping: dict[str, Any], source_count: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if mapping.get("kind") != KIND or int(mapping.get("schema_version") or 0) != VERSION:
        raise ValueError(f"映射必须是 {KIND} schema v{VERSION}")
    approval = mapping.get("approval") or {}
    if not str(approval.get("reviewer") or "").strip():
        raise ValueError("approval.reviewer 不能为空")
    roles = {str(role).strip() for role in (approval.get("roles") or [])}
    if not roles.intersection({"director", "showrunner", "head_writer"}):
        raise ValueError("批准映射至少需要 director/showrunner/head_writer 之一")
    window = mapping.get("window") or {}
    start_ep, end_ep = int(window.get("start_episode") or 0), int(window.get("end_episode") or 0)
    rows = list(mapping.get("episodes") or [])
    if start_ep < 1 or end_ep < start_ep or len(rows) != end_ep - start_ep + 1:
        raise ValueError("window 集号与 episodes 数量不一致")
    expected_ep = start_ep
    previous_end = None
    for row in rows:
        episode = int(row.get("episode") or 0)
        start = _unit_index(row.get("start_source_unit_id"))
        end = _unit_index(row.get("end_source_unit_id"))
        if episode != expected_ep or start > end or end > source_count:
            raise ValueError(f"第{expected_ep}集映射无效")
        if previous_end is not None and start != previous_end + 1:
            raise ValueError("批准窗口 source-unit 必须连续、无空洞、无重叠")
        previous_end = end
        expected_ep += 1
    if _unit_index(window.get("start_source_unit_id")) != _unit_index(rows[0]["start_source_unit_id"]):
        raise ValueError("window.start_source_unit_id 与首集不一致")
    if _unit_index(window.get("end_source_unit_id")) != _unit_index(rows[-1]["end_source_unit_id"]):
        raise ValueError("window.end_source_unit_id 与末集不一致")
    next_idx = _unit_index(window.get("next_source_unit_id"))
    if next_idx != previous_end + 1 or next_idx > source_count:
        raise ValueError("next_source_unit_id 必须紧接批准窗口末尾")
    return window, rows


def _progress_preflight(progress_path: Path, start_ep: int, end_ep: int) -> list[str]:
    lines = progress_path.read_text(encoding="utf-8").splitlines()
    seen: set[int] = set()
    for line in lines:
        match = re.match(r"\|\s*第(\d+)集\s*\|", line)
        if not match:
            continue
        ep = int(match.group(1))
        if not start_ep <= ep <= end_ep:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[2] != "✅":
            raise ValueError(f"第{ep}集不是已落 raw 状态")
        dirty = [value for value in cells[3:] if value.lower() not in EMPTY_DOWNSTREAM]
        if dirty:
            raise ValueError(f"第{ep}集已有下游进度 {dirty}，拒绝覆盖 raw")
        seen.add(ep)
    expected = set(range(start_ep, end_ep + 1))
    if seen != expected:
        raise ValueError(f"_进度.md 缺窗口集行: {sorted(expected - seen)}")
    return lines


def _replace_progress_lengths(lines: list[str], lengths: dict[int, int]) -> bytes:
    out = []
    for line in lines:
        match = re.match(r"(\|\s*第(\d+)集\s*\|\s*)(\d+)(\s*\|.*)", line)
        if match and int(match.group(2)) in lengths:
            line = f"{match.group(1)}{lengths[int(match.group(2))]}{match.group(4)}"
        out.append(line)
    return ("\n".join(out).rstrip() + "\n").encode("utf-8")


def _episode_row(root: Path, row: dict[str, Any], paras: list[str], reviewer: str) -> tuple[dict[str, Any], bytes]:
    ep = int(row["episode"])
    start = _unit_index(row["start_source_unit_id"])
    end = _unit_index(row["end_source_unit_id"])
    raw_text = "\n".join(paras[start - 1:end]).rstrip() + "\n"
    raw_rel = f"脚本/第{ep}集/raw.txt"
    item = {
        "episode": ep,
        "episode_label": f"第{ep}集",
        "source_chars": len(raw_text.replace("\n", "")),
        "opening_preview": SN.summarize_text(raw_text[:400]),
        "ending_preview": SN.summarize_text(raw_text[-400:]),
        "raw_rel": raw_rel,
        "raw_sha256": SN.sha256_text(raw_text.rstrip()),
        "machine_source_sha256": SN.sha256_text(raw_text.rstrip()),
        "materialized": True,
        "source_unit_span": {
            "episode": ep,
            "start_source_unit_id": f"U{start:06d}",
            "end_source_unit_id": f"U{end:06d}",
            "start_index": start,
            "end_index": end,
            "mapping_exact": True,
        },
        "boundary_status": "human_approved_applied",
        "human_approval": {
            "reviewer": reviewer,
            "source_chapters": row.get("source_chapters") or "",
            "core_scene": row.get("core_scene") or "",
            "end_hook": row.get("end_hook") or "",
        },
        "adaptation_policy": "raw 是获批取材窗口；阶段1仍须按漫剧节奏重写并保留冲突、选择、反转与集尾钩。",
    }
    return item, raw_text.encode("utf-8")


def _backup(root: Path, paths: list[Path], target: Path) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(target, "w:gz") as archive:
        for path in paths:
            if path.exists():
                archive.add(path, arcname=path.relative_to(root).as_posix(), recursive=False)
    payload = target.read_bytes()
    return {"path": target.relative_to(root).as_posix(), "sha256": _sha_bytes(payload), "bytes": len(payload)}


def apply_mapping(root: str | Path, mapping_path: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    mapping_path = Path(mapping_path).resolve()
    plan_path = root / "脚本" / "split_plan.json"
    index_path = root / "脚本" / "_拆集机器索引.md"
    progress_path = root / "_进度.md"
    plan = _read_json(plan_path)
    mapping = _read_json(mapping_path)
    source_path, paras = _normalize_source(root, plan)
    window, mapping_rows = _validate_mapping(mapping, len(paras))
    start_ep, end_ep = int(window["start_episode"]), int(window["end_episode"])
    progress_lines = _progress_preflight(progress_path, start_ep, end_ep)

    plan_episodes = list(plan.get("episodes") or [])
    next_idx = _unit_index(window["next_source_unit_id"])
    suffix_pos = None
    for index, row in enumerate(plan_episodes):
        span = row.get("source_unit_span") or {}
        if int(span.get("start_index") or 0) == next_idx:
            suffix_pos = index
            break
    if suffix_pos is None:
        raise ValueError("旧计划中找不到 next_source_unit_id 对应的安全后缀")
    affected_old = plan_episodes[start_ep - 1:suffix_pos]
    if any(bool(row.get("materialized")) for row in affected_old[end_ep - start_ep + 1:]):
        raise ValueError("被吸收的旧集已有 materialized 产物，拒绝平移")
    suffix = copy.deepcopy(plan_episodes[suffix_pos:])
    if any(bool(row.get("materialized")) for row in suffix):
        raise ValueError("未落地后缀中出现 materialized 集，需先做专项迁移计划")

    reviewer = str((mapping.get("approval") or {}).get("reviewer") or "").strip()
    new_rows: list[dict[str, Any]] = []
    raw_payloads: dict[Path, bytes] = {}
    for row in mapping_rows:
        item, payload = _episode_row(root, row, paras, reviewer)
        new_rows.append(item)
        raw_payloads[root / item["raw_rel"]] = payload
    for offset, row in enumerate(suffix, end_ep + 1):
        row["episode"] = offset
        row["episode_label"] = f"第{offset}集"
        row["raw_rel"] = f"脚本/第{offset}集/raw.txt"
        span = row.get("source_unit_span") or {}
        span["episode"] = offset
        row["source_unit_span"] = span
        new_rows.append(row)
    plan["episodes"] = plan_episodes[:start_ep - 1] + new_rows
    plan["estimated_total_episode_count"] = len(plan["episodes"])
    plan["target_episode_count"] = max(int(plan.get("target_episode_count") or 0), end_ep)
    plan["split_mode"] = f"{plan.get('split_mode', 'machine')} + 人工批准窗口实施"
    spans = [row.get("source_unit_span") or {} for row in plan["episodes"]]
    plan["boundary_candidates"] = SN.build_boundary_candidates(paras, spans)
    plan["boundary_optimization"] = {
        "method": "full_book_beam_search_v1",
        "enforcement": "advisory_needs_semantic_review",
        "dictionary_hard_veto": False,
        "development_arc_constraints_applied": False,
        "development_arc_unmapped_note": "人工批准窗口已成为硬事实；其余边界仍为机器建议。",
        "top_paths": SN.optimize_boundary_paths(paras, len(plan["episodes"]), top_k=3),
    }

    now = datetime.now(timezone.utc).replace(microsecond=0)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    receipt_rel = f"生产数据/边界收据/split_mapping_applied_{stamp}.json"
    receipt_path = root / receipt_rel
    approved = {
        "start_episode": start_ep,
        "end_episode": end_ep,
        "start_source_unit_id": window["start_source_unit_id"],
        "end_source_unit_id": window["end_source_unit_id"],
        "next_source_unit_id": window["next_source_unit_id"],
        "reviewer": reviewer,
        "roles": (mapping.get("approval") or {}).get("roles") or [],
        "approved_at": (mapping.get("approval") or {}).get("approved_at") or "",
        "applied_at": now.isoformat(),
        "mapping": mapping_path.relative_to(root).as_posix() if root in mapping_path.parents else str(mapping_path),
        "receipt": receipt_rel,
    }
    plan.setdefault("human_approved_windows", []).append(approved)
    plan["generated_at"] = now.isoformat()

    plan_payload = (json.dumps(plan, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    index_payload = SN.render_machine_split_review(plan).encode("utf-8")
    lengths = {int(row["episode"]): int(new_rows[int(row["episode"]) - start_ep]["source_chars"]) for row in mapping_rows}
    progress_payload = _replace_progress_lengths(progress_lines, lengths)
    mutable = [plan_path, index_path, progress_path, *raw_payloads.keys()]
    old_bytes = {path: path.read_bytes() for path in mutable if path.exists()}
    backup_path = root / "生产数据" / "边界收据" / f"split_mapping_before_{stamp}.tar.gz"
    backup = _backup(root, mutable, backup_path)

    before = {path.relative_to(root).as_posix(): _sha_bytes(data) for path, data in old_bytes.items()}
    try:
        for path, payload in raw_payloads.items():
            _atomic_write(path, payload)
        _atomic_write(plan_path, plan_payload)
        _atomic_write(index_path, index_payload)
        _atomic_write(progress_path, progress_payload)
        after = {
            path.relative_to(root).as_posix(): _sha_bytes(path.read_bytes())
            for path in mutable
        }
        receipt = {
            "schema_version": 1,
            "kind": RECEIPT_KIND,
            "status": "applied",
            "applied_at": now.isoformat(),
            "project_root": str(root),
            "source": {"path": source_path.relative_to(root).as_posix(), "sha256": plan["source_text_sha256"]},
            "approval": mapping.get("approval") or {},
            "mapping": {"path": approved["mapping"], "sha256": _canonical_sha(mapping), "window": window},
            "splice": {
                "old_episode_count": len(plan_episodes),
                "new_episode_count": len(plan["episodes"]),
                "suffix_old_episode": suffix_pos + 1,
                "suffix_new_episode": end_ep + 1,
                "suffix_start_source_unit_id": window["next_source_unit_id"],
            },
            "backup": backup,
            "before_sha256": before,
            "after_sha256": after,
            "checks": {
                "source_snapshot_matched": True,
                "mapping_contiguous": True,
                "window_raw_only": True,
                "suffix_unmaterialized": True,
                "plan_raw_progress_refreshed": True,
            },
        }
        _atomic_write(receipt_path, (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    except Exception:
        for path in mutable:
            if path in old_bytes:
                _atomic_write(path, old_bytes[path])
            elif path.exists():
                path.unlink()
        raise
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="实施人工批准的 n2d 拆集 source-unit 映射")
    parser.add_argument("root", help="作品根")
    parser.add_argument("mapping", help="n2d_approved_split_mapping JSON")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = apply_mapping(args.root, args.mapping)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(2, f"拆集映射实施失败：{exc}\n")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"已实施：{result['mapping']['window']}")
        print(f"回滚备份：{result['backup']['path']}")


if __name__ == "__main__":
    main()
