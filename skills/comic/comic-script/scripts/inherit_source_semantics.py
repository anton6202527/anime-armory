#!/usr/bin/env python3
"""Reuse reviewed source meanings when serial chapters consume one source slice.

The target chapter must already have been scaffolded by source_semantics_gate.py.
Only linguistic review fields are inherited; the target chapter contract, source
slice, source hashes and receipt metadata stay untouched.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


# Must be a subset of source_semantics_gate.ADAPTATION_DECISIONS (minus the
# non-final 待定): a --decision override the gate later rejects is worse than
# useless.  The old set wrote bare "旁白" (gate wants "成旁白") and lacked
# 成对白/成拟声/保留原文.
FINAL_DECISIONS = {"成画面", "成对白", "成旁白", "成拟声", "并入", "删除", "后文带出", "保留原文"}


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"JSON root must be an object: {path}")
    return data


def segment_number(segment_id: str) -> int:
    value = str(segment_id or "").strip().upper()
    if not value.startswith("S") or not value[1:].isdigit():
        raise SystemExit(f"invalid segment id: {segment_id!r}")
    return int(value[1:])


def decision_overrides(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"--decision must be Sxxx=decision, got {value!r}")
        segment_id, decision = (part.strip() for part in value.split("=", 1))
        segment_number(segment_id)
        if decision not in FINAL_DECISIONS:
            raise SystemExit(f"unsupported decision {decision!r}; choose {sorted(FINAL_DECISIONS)}")
        result[segment_id.upper()] = decision
    return result


def inherit(
    target: dict[str, Any],
    source: dict[str, Any],
    *,
    consume_start: int,
    consume_end: int,
    overrides: dict[str, str],
) -> dict[str, Any]:
    if consume_start > consume_end:
        raise SystemExit("consume start must not exceed consume end")
    source_segments = {
        str(item.get("segment_id") or ""): item
        for item in source.get("segments", [])
        if isinstance(item, dict)
    }
    target_segments = target.get("segments")
    if not isinstance(target_segments, list) or not target_segments:
        raise SystemExit("target source_semantics has no segments")

    consumed: list[str] = []
    for item in target_segments:
        if not isinstance(item, dict):
            raise SystemExit("target contains a non-object segment")
        segment_id = str(item.get("segment_id") or "")
        number = segment_number(segment_id)
        prior = source_segments.get(segment_id)
        if not prior:
            raise SystemExit(f"source chapter lacks {segment_id}")
        if str(prior.get("source_excerpt") or "") != str(item.get("source_excerpt") or ""):
            raise SystemExit(f"source excerpt drift at {segment_id}; refuse semantic inheritance")

        for field in ("meaning_zh", "ambiguities"):
            item[field] = prior.get(field, [] if field == "ambiguities" else "")

        if number < consume_start:
            item["text_target"] = "（本话不嵌字）"
            item["adaptation_decision"] = "删除"
            item["adaptation_note"] = "该段已由前序话次完成改编，本话仅保留语义追溯，不重复消费。"
        elif number > consume_end:
            item["text_target"] = "（本话不嵌字）"
            item["adaptation_decision"] = "后文带出"
            item["adaptation_note"] = "超出本话已签核戏剧边界，留待后续话次消费。"
        else:
            consumed.append(segment_id)
            item["text_target"] = "（本话改编为分格台词／旁白）"
            item["adaptation_decision"] = overrides.get(segment_id, "成画面")
            item["adaptation_note"] = "属于本话已签核源范围，按分格脚本承担可追溯的画面、对白或旁白功能。"

    unknown = sorted(set(overrides) - set(consumed))
    if unknown:
        raise SystemExit(f"decision overrides fall outside consumed range: {', '.join(unknown)}")

    target["proper_noun_glossary"] = source.get("proper_noun_glossary", [])
    target["glossary_reviewed"] = bool(source.get("glossary_reviewed"))
    target["ambiguity_reviewed"] = bool(source.get("ambiguity_reviewed"))
    target["status"] = "review"
    target["semantic_inheritance"] = {
        "source_chapter": source.get("chapter"),
        "mode": "linguistic_fields_only",
        "consume_range": [f"S{consume_start:03d}", f"S{consume_end:03d}"],
        "preserved_target_contract": True,
    }
    return target


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description="继承前话已审源语义，只重置当前话消费决策。")
    parser.add_argument("root", type=Path)
    parser.add_argument("--chapter", required=True)
    parser.add_argument("--from-chapter", required=True)
    parser.add_argument("--consume-start", required=True, type=int)
    parser.add_argument("--consume-end", required=True, type=int)
    parser.add_argument("--decision", action="append", default=[])
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    target_path = args.root / "脚本" / args.chapter / "source_semantics.json"
    source_path = args.root / "脚本" / args.from_chapter / "source_semantics.json"
    target = load_json(target_path)
    source = load_json(source_path)
    result = inherit(
        target,
        source,
        consume_start=args.consume_start,
        consume_end=args.consume_end,
        overrides=decision_overrides(args.decision),
    )
    if args.write:
        atomic_write_json(target_path, result)
    summary = {
        "target": str(target_path),
        "source": str(source_path),
        "consume_range": result["semantic_inheritance"]["consume_range"],
        "segment_count": len(result.get("segments", [])),
        "written": args.write,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2) if args.json else summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
