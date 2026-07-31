#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Estimate prompt-cache readiness for novel task packets.

This does not call any model API. It scans writing packets and semantic jobs for
static context blocks/cache_control markers so long-running projects can track
whether reusable context is actually separated from per-chapter instructions.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime
from typing import Any

try:
    from provenance import append_event
except Exception:  # pragma: no cover - provenance is additive
    append_event = None


METRICS_KIND = "novel_prompt_cache_metrics"
STATIC_RE = re.compile(r"<static_context\b[^>]*>(.*?)</static_context>", re.S)
# 逐章/逐时点内容若漏进 static_context，会让缓存前缀逐包不同、跨章命中静默归零。
# 这些 pattern 只在 static 前缀已不一致时用于定位泄漏来源（非硬失败）。
VOLATILE_RE = re.compile(r"第\s*\d+\s*[章集卷]|\d{4}-\d{2}-\d{2}|本章|本集")


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def rel(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def approx_tokens(chars: int) -> int:
    return int(math.ceil(max(0, chars) / 4))


def packet_metrics(root: str, path: str, text: str) -> dict[str, Any]:
    static_blocks = STATIC_RE.findall(text)
    static_chars = sum(len(block) for block in static_blocks)
    total_chars = len(text)
    static_text = "".join(static_blocks)
    # 缓存按字节前缀匹配：同一项目多个包能否共享缓存，取决于 static 块是否字节一致。
    static_hash = hashlib.sha256(static_text.encode("utf-8")).hexdigest()[:16] if static_text else ""
    volatile_hits = sorted(set(VOLATILE_RE.findall(static_text)))
    return {
        "path": rel(root, path),
        "total_chars": total_chars,
        "static_context_chars": static_chars,
        "dynamic_context_chars": max(0, total_chars - static_chars),
        "static_context_blocks": len(static_blocks),
        "static_context_hash": static_hash,
        "static_volatile_hits": volatile_hits,
        "has_cache_control": "cache_control=" in text or "cache_control" in text,
        "estimated_static_tokens": approx_tokens(static_chars),
        "estimated_total_tokens": approx_tokens(total_chars),
    }


def semantic_job_prompt_text(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    parts = []
    for key in ("prompt", "prompt_text", "instructions", "request"):
        if payload.get(key):
            parts.append(str(payload[key]))
    for message in payload.get("messages") or []:
        if isinstance(message, dict) and message.get("content"):
            parts.append(str(message["content"]))
    return "\n".join(parts)


def nested_number(payload: Any, paths: list[list[str]]) -> int:
    for path in paths:
        cur = payload
        for key in path:
            if not isinstance(cur, dict):
                cur = None
                break
            cur = cur.get(key)
        if isinstance(cur, (int, float)):
            return int(cur)
    return 0


def usage_from_payload(payload: Any, source: str) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else payload
    input_tokens = nested_number(usage, [
        ["input_tokens"],
        ["prompt_tokens"],
        ["total_input_tokens"],
    ])
    cached_tokens = nested_number(usage, [
        ["cached_input_tokens"],
        ["cached_tokens"],
        ["input_token_details", "cached_tokens"],
        ["input_token_details", "cache_read"],
        ["prompt_tokens_details", "cached_tokens"],
        ["prompt_token_details", "cached_tokens"],
    ])
    if not input_tokens and not cached_tokens:
        return None
    return {
        "source": source,
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_tokens,
        "cache_hit_ratio": cached_tokens / input_tokens if input_tokens else 0.0,
    }


def iter_jsonl(path: str):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def collect_usage_records(root: str, usage_files: list[str] | None = None) -> dict[str, Any]:
    candidates = []
    if usage_files:
        candidates.extend(os.path.abspath(path) if os.path.isabs(path) else os.path.join(root, path) for path in usage_files)
    else:
        for name in (
            "prompt_usage.jsonl",
            "prompt_cache_usage.jsonl",
            "model_usage.jsonl",
            "llm_usage.jsonl",
        ):
            candidates.append(os.path.join(root, "生产数据", name))
    records: list[dict[str, Any]] = []
    for path in candidates:
        if not os.path.exists(path):
            continue
        if path.endswith(".jsonl"):
            payloads = iter_jsonl(path)
        else:
            loaded = load_json(path, {}) or {}
            payloads = loaded if isinstance(loaded, list) else [loaded]
        for payload in payloads:
            record = usage_from_payload(payload, rel(root, path))
            if record:
                records.append(record)
    for path in sorted(glob.glob(os.path.join(root, "语义任务", "**", "*.json"), recursive=True)):
        payload = load_json(path, {}) or {}
        record = usage_from_payload(payload, rel(root, path))
        if record:
            records.append(record)
    input_tokens = sum(int(record.get("input_tokens") or 0) for record in records)
    cached_tokens = sum(int(record.get("cached_input_tokens") or 0) for record in records)
    return {
        "record_count": len(records),
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_tokens,
        "cache_hit_ratio": cached_tokens / input_tokens if input_tokens else 0.0,
        "sources": records[:100],
    }


def record_usage(
    root: str,
    usage_payload: dict[str, Any],
    *,
    source: str = "manual",
    output_name: str = "model_usage.jsonl",
) -> tuple[str, dict[str, Any]]:
    root = os.path.abspath(root)
    normalized = usage_from_payload(usage_payload, source)
    if not normalized:
        raise ValueError("usage payload must include input_tokens/prompt_tokens or cached token fields")
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, output_name)
    raw_usage = usage_payload.get("usage") if isinstance(usage_payload.get("usage"), dict) else usage_payload
    record = {
        "schema_version": 1,
        "kind": "novel_model_usage",
        "recorded_at": now(),
        "source": source,
        "input_tokens": normalized["input_tokens"],
        "cached_input_tokens": normalized["cached_input_tokens"],
        "cache_hit_ratio": normalized["cache_hit_ratio"],
        "usage": raw_usage,
    }
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    if append_event:
        append_event(
            root,
            event_type="prompt_cache_usage_recorded",
            tool="novel-craft/scripts/prompt_cache_metrics.py",
            outputs=[out_path],
            metadata={
                "source": source,
                "input_tokens": record["input_tokens"],
                "cached_input_tokens": record["cached_input_tokens"],
                "cache_hit_ratio": record["cache_hit_ratio"],
            },
        )
    return out_path, record


def collect_metrics(root: str, *, usage_files: list[str] | None = None) -> dict[str, Any]:
    root = os.path.abspath(root)
    packets = []
    for path in sorted(glob.glob(os.path.join(root, "写作任务", "**", "*.md"), recursive=True)):
        packets.append(packet_metrics(root, path, read_text(path)))
    semantic_jobs = []
    for path in sorted(glob.glob(os.path.join(root, "语义任务", "**", "*.json"), recursive=True)):
        payload = load_json(path, {}) or {}
        text = semantic_job_prompt_text(payload)
        if text:
            semantic_jobs.append(packet_metrics(root, path, text))
    all_items = packets + semantic_jobs
    total_chars = sum(item["total_chars"] for item in all_items)
    static_chars = sum(item["static_context_chars"] for item in all_items)
    cache_control_count = sum(1 for item in all_items if item["has_cache_control"])
    # 跨包 static 前缀一致性：缓存只在 static 块跨请求字节一致时才共享。统计 写作任务 包里
    # 非空 static 块的去重 hash 数；>1 说明缓存前缀逐章漂移、跨章命中将为 0（draft_packets 应把
    # 逐章/逐 step 内容移出 static_context，只保留整部不变的设定/风格/契约）。
    writing_static_hashes = [p["static_context_hash"] for p in packets if p.get("static_context_hash")]
    static_prefix_variants = len(set(writing_static_hashes))
    shared_static_prefix = static_prefix_variants <= 1
    recommendations = []
    if all_items and cache_control_count < len(all_items):
        recommendations.append("add explicit static_context/cache_control markers to packets without reusable context separation")
    if total_chars and static_chars / total_chars < 0.2:
        recommendations.append("static context ratio is low; move stable bible/style/source lists out of dynamic chapter instructions")
    if len(writing_static_hashes) > 1 and not shared_static_prefix:
        recommendations.append(
            f"写作任务 static_context 前缀不一致：{len(writing_static_hashes)} 个包出现 {static_prefix_variants} 种 static 块；"
            "缓存按字节前缀匹配，跨章命中将为 0。把逐章/逐 step 变化的内容移出 static_context，只保留整部不变的设定/风格/契约。"
        )
        leak = sorted({h for p in packets for h in (p.get("static_volatile_hits") or [])})
        if leak:
            recommendations.append(
                f"static_context 内疑似逐章/逐时点内容（应移回 dynamic_context）：{', '.join(leak)}"
            )
    actual_usage = collect_usage_records(root, usage_files)
    if actual_usage["record_count"] == 0:
        recommendations.append("no API usage records found; cache benefit is estimated readiness only")
    return {
        "schema_version": 1,
        "kind": METRICS_KIND,
        "generated_at": now(),
        "project_root": root,
        "metric_semantics": {
            "cache_readiness_ratio": "static-context estimate from local packets, not provider billing",
            "actual_cache_hit_ratio": "observed cached input tokens divided by input tokens from usage records when present",
        },
        "packet_count": len(packets),
        "semantic_job_count": len(semantic_jobs),
        "item_count": len(all_items),
        "cache_control_count": cache_control_count,
        "cache_control_coverage": cache_control_count / len(all_items) if all_items else 0.0,
        "shared_static_prefix": shared_static_prefix,
        "static_prefix_variants": static_prefix_variants,
        "static_prefix_packets": len(writing_static_hashes),
        "total_chars": total_chars,
        "static_context_chars": static_chars,
        "dynamic_context_chars": max(0, total_chars - static_chars),
        "static_context_ratio": static_chars / total_chars if total_chars else 0.0,
        "cache_readiness_ratio": static_chars / total_chars if total_chars else 0.0,
        "estimated_static_tokens": approx_tokens(static_chars),
        "estimated_total_tokens": approx_tokens(total_chars),
        "estimated_reusable_token_ratio": static_chars / total_chars if total_chars else 0.0,
        "actual_usage": actual_usage,
        "actual_cache_hit_ratio": actual_usage["cache_hit_ratio"],
        "recommendations": recommendations,
        "items": all_items,
    }


def render_markdown(metrics: dict[str, Any]) -> str:
    lines = [
        "# Prompt Cache Metrics",
        "",
        f"- generated_at: {metrics.get('generated_at')}",
        f"- packets: {metrics.get('packet_count', 0)}",
        f"- semantic_jobs: {metrics.get('semantic_job_count', 0)}",
        f"- cache_control_coverage: {metrics.get('cache_control_coverage', 0):.2f}",
        f"- shared_static_prefix: {metrics.get('shared_static_prefix')} "
        f"(variants={metrics.get('static_prefix_variants', 0)} / packets={metrics.get('static_prefix_packets', 0)})",
        f"- cache_readiness_ratio: {metrics.get('cache_readiness_ratio', metrics.get('static_context_ratio', 0)):.2f}",
        f"- actual_cache_hit_ratio: {metrics.get('actual_cache_hit_ratio', 0):.2f}",
        f"- actual_usage_records: {(metrics.get('actual_usage') or {}).get('record_count', 0)}",
        f"- estimated_static_tokens: {metrics.get('estimated_static_tokens', 0)}",
        "",
        "## Semantics",
        "",
        "- cache_readiness_ratio is a static local estimate, not a billing metric.",
        "- actual_cache_hit_ratio is based on usage records when available.",
        "",
        "## Recommendations",
        "",
    ]
    recs = metrics.get("recommendations") or []
    lines.extend(f"- {item}" for item in recs) if recs else lines.append("- none")
    lines.extend(["", "## Items", "", "| path | static_ratio | cache_control |", "|---|---:|---|"])
    for item in metrics.get("items") or []:
        ratio = item.get("static_context_chars", 0) / item.get("total_chars", 1) if item.get("total_chars") else 0
        lines.append(f"| {item.get('path')} | {ratio:.2f} | {item.get('has_cache_control')} |")
    return "\n".join(lines) + "\n"


def write_metrics(root: str, metrics: dict[str, Any] | None = None) -> tuple[str, str, dict[str, Any]]:
    root = os.path.abspath(root)
    metrics = metrics or collect_metrics(root)
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "prompt_cache_metrics.json")
    md_path = os.path.join(out_dir, "prompt_cache_metrics.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(metrics))
    if append_event:
        append_event(
            root,
            event_type="prompt_cache_metrics_written",
            tool="novel-craft/scripts/prompt_cache_metrics.py",
            outputs=[json_path, md_path],
            metadata={
                "item_count": metrics.get("item_count"),
                "cache_control_coverage": metrics.get("cache_control_coverage"),
                "static_context_ratio": metrics.get("static_context_ratio"),
                "shared_static_prefix": metrics.get("shared_static_prefix"),
            },
        )
    return json_path, md_path, metrics


def _load_usage_arg(args: argparse.Namespace) -> dict[str, Any]:
    if args.usage_json:
        return json.loads(args.usage_json)
    if args.usage_file:
        with open(args.usage_file, encoding="utf-8") as f:
            return json.load(f)
    raise ValueError("provide --usage-json or --usage-file")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "record-usage":
        parser = argparse.ArgumentParser(description="append real model usage to 生产数据/model_usage.jsonl")
        parser.add_argument("cmd")
        parser.add_argument("project_root")
        parser.add_argument("--usage-json", default="", help="usage JSON string or full API response JSON")
        parser.add_argument("--usage-file", default="", help="JSON file containing usage or full API response")
        parser.add_argument("--source", default="manual")
        parser.add_argument("--output-name", default="model_usage.jsonl")
        parser.add_argument("--json", action="store_true")
        args = parser.parse_args(argv)
        root = os.path.abspath(args.project_root)
        if not os.path.isdir(root):
            print(f"[err] 找不到作品根：{root}", file=sys.stderr)
            return 2
        try:
            payload = _load_usage_arg(args)
            path, record = record_usage(root, payload, source=args.source, output_name=args.output_name)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"[err] {exc}", file=sys.stderr)
            return 2
        result = {"usage_path": path, "record": record}
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"[ok] usage → {path}")
        return 0

    parser = argparse.ArgumentParser(description="estimate novel prompt cache metrics")
    parser.add_argument("project_root")
    parser.add_argument("--usage-file", action="append", help="JSON/JSONL usage file with input/cached token fields; repeatable")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    metrics = collect_metrics(root, usage_files=args.usage_file)
    if args.write:
        json_path, md_path, _metrics = write_metrics(root, metrics)
        if not args.json:
            print(f"[ok] prompt cache metrics JSON → {json_path}")
            print(f"[ok] prompt cache metrics MD   → {md_path}")
    print(json.dumps(metrics, ensure_ascii=False, indent=2) if args.json else render_markdown(metrics))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
