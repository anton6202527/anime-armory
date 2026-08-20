#!/usr/bin/env python3
"""Append an auditable image-generation event for an MV frame.

This does not call a provider.  It records the actual model, access channel,
prompt and reference files used by a web/API/local generation so image_qc can
prove uniformity and detect stale or silently replaced assets.  B14 requires a
successful per-asset ``image_receipts.py preflight`` first; this command then
freezes the provider's *actual* submitted inputs and rejects planned/actual
reference drift before appending the production event.  Provider-backed routes
must bind a project-local schema-v2 manifest plus an independent, hash-verified
API response or trusted-origin HAR capture; a bare job ID is never evidence.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from image_receipts import ReceiptError, record_submission  # noqa: E402


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


def main(argv: Optional[Sequence[str]] = None):
    parser = argparse.ArgumentParser(description="记录 MV 出图模型/渠道/prompt/reference 收据")
    parser.add_argument("project_root")
    parser.add_argument("--asset", required=True, help="已生成的 PNG/JPG（作品根相对路径或绝对路径）")
    parser.add_argument("--model", required=True, help="具体模型与版本，如 GPT Image 2")
    parser.add_argument("--channel", required=True, help="访问入口，如 Codex / OpenAI API")
    parser.add_argument("--prompt", required=True, help="实际来源 prompt 文件")
    parser.add_argument("--reference", action="append", default=[], help="真实提交的参考图，可多次")
    parser.add_argument("--subject-id", action="append", default=[], help="真实提交的后端主体/角色 ID，可多次")
    parser.add_argument("--method", default="generation")
    parser.add_argument("--provider-job-id", default="",
                        help="provider 返回的 job/request/task id；正式 provider 路由必填")
    parser.add_argument("--provider-evidence", default="",
                        help="作品根内 mv_image_provider_evidence schema v2 manifest；正式 provider 路由必填")
    parser.add_argument("--seed", default="", help="后端返回/提交的随机种子；有则必记（复现与微调用）")
    parser.add_argument("--param", action="append", default=[], metavar="K=V",
                        help="其它生成参数留痕（cfg=7.5 / size=2048x1152…，可重复）")
    parser.add_argument("--notes", default="")
    args = parser.parse_args(argv)

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

    params = {}
    for pair in args.param:
        if "=" not in pair:
            print(f"[err] --param 格式应为 K=V，收到：{pair}", file=sys.stderr)
            return 2
        key, value = pair.split("=", 1)
        params[key.strip()] = value.strip()

    try:
        b14 = record_submission(
            Path(root), asset=asset_rel, model=args.model, channel=args.channel,
            prompt=prompt_rel, references=[row["path"] for row in ref_rows],
            subject_ids=args.subject_id, provider_job_id=args.provider_job_id,
            provider_evidence=args.provider_evidence,
        )
    except ReceiptError as exc:
        print(f"[block] B14 actual-submit 对账失败：{exc}", file=sys.stderr)
        return 1

    # Use the authoritative B14 actual rows so owner/use/decodability metadata
    # cannot diverge between the acceptance ledger and the event log.
    submitted = b14["submission"]
    event = {
        "schema_version": 2,
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
            "reference_inputs": submitted["actual_references"],
            "subject_inputs": submitted["actual_subject_ids"],
            "provider_job_id": submitted["provider_job_id"],
            "provider_evidence": submitted["provider_evidence"],
            # 可复现性留痕：seed/参数是登记时已知的事实，能记必记（缺省不阻断——很多网页入口拿不到）。
            "seed": args.seed.strip(),
            "generation_params": params,
            "b14_attempt_id": b14["attempt_id"],
            "b14_preflight_sha256": b14["preflight_sha256"],
            "b14_submission_sha256": submitted["receipt_sha256"],
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
