#!/usr/bin/env python3
"""Append an auditable image-generation event for an MV frame.

This does not call a provider.  It records the actual model, access channel,
prompt and reference files used by a web/API/local generation so image_qc can
prove uniformity and detect stale or silently replaced assets.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve(root, value):
    path = value if os.path.isabs(value) else os.path.join(root, value)
    return os.path.abspath(path)


def relative(root, path):
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    if rel == ".." or rel.startswith("../"):
        raise ValueError(f"路径必须在作品根内：{path}")
    return rel


def main():
    parser = argparse.ArgumentParser(description="记录 MV 出图模型/渠道/prompt/reference 收据")
    parser.add_argument("project_root")
    parser.add_argument("--asset", required=True, help="已生成的 PNG/JPG（作品根相对路径或绝对路径）")
    parser.add_argument("--model", required=True, help="具体模型与版本，如 GPT Image 2")
    parser.add_argument("--channel", required=True, help="访问入口，如 Codex / OpenAI API")
    parser.add_argument("--prompt", required=True, help="实际来源 prompt 文件")
    parser.add_argument("--reference", action="append", default=[], help="真实提交的参考图，可多次")
    parser.add_argument("--subject-id", action="append", default=[], help="真实提交的后端主体/角色 ID，可多次")
    parser.add_argument("--method", default="generation")
    parser.add_argument("--provider-job-id", default="")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    try:
        asset = resolve(root, args.asset)
        prompt = resolve(root, args.prompt)
        refs = [resolve(root, value) for value in args.reference]
        missing = [path for path in (asset, prompt, *refs) if not os.path.isfile(path)]
        if missing:
            raise ValueError(f"文件不存在：{missing[0]}")
        asset_rel = relative(root, asset)
        prompt_rel = relative(root, prompt)
        ref_rows = [
            {"path": relative(root, path), "sha256": sha256(path)} for path in refs
        ]
    except ValueError as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 2

    event = {
        "schema_version": 1,
        "stage": "image",
        "event": "generation",
        "recorded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "generation": {
            "asset": asset_rel,
            "asset_sha256": sha256(asset),
            "model": args.model.strip(),
            "channel": args.channel.strip(),
            "method": args.method.strip(),
            "source_prompt": prompt_rel,
            "source_prompt_sha256": sha256(prompt),
            "reference_inputs": ref_rows,
            "subject_inputs": [value.strip() for value in args.subject_id if value.strip()],
            "provider_job_id": args.provider_job_id.strip(),
        },
        "notes": args.notes,
    }
    path = os.path.join(root, "生产数据", "production_events.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"[ok] image generation receipt → {path} · {asset_rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
