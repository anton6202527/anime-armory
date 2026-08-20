#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write a current, human-attested AI-use disclosure for an MV project."""
from __future__ import annotations

import argparse
from datetime import datetime
import os
import sys

_COMMON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if _COMMON_DIR not in sys.path:
    sys.path.insert(0, _COMMON_DIR)
import disclosure  # noqa: E402  vendored in this production line

import completion  # noqa: E402
from contract import AI_VISUAL_USAGE_MODES, runtime_state_from_settings  # noqa: E402
import mv_utils  # noqa: E402


MUSIC_MODES = ("human", "AI-assisted", "AI-generated", "unknown")
REALISM_MODES = ("stylized", "photorealistic", "mixed", "unknown")
REAL_PERSON_MODES = ("none", "authorized", "unauthorized", "unknown")
EVIDENCE_RELS = (
    "_设置.md",
    "_meta.json",
    "生产数据/image_acceptance/image_acceptance.json",
    "出视频/jobs_manifest.json",
    "生产数据/video_qc/video_qc.json",
    "合规/rights_manifest.json",
)
PLACEHOLDER_REVIEWERS = {"", "<name>", "待填", "待定", "unknown"}


NOTES = [
    "- 本披露绑定当前设置、生成/验收收据和权利清单；任一绑定输入变化后必须重签。",
    "- C2PA/元数据不替代发布平台的上传声明或法域要求的可见标识。",
    "- 真人肖像、声音或身份必须有可核验授权；unauthorized 会被本脚本拒绝。",
    "- 这是制作与交付证据，不是法律意见；发布决策另跑 release_decision.py。",
]


def _input_bindings(root: str) -> dict[str, str]:
    return {
        rel: mv_utils.content_hash(os.path.join(root, rel))
        for rel in EVIDENCE_RELS
        if mv_utils.content_hash(os.path.join(root, rel))
    }


def _classification(visual_mode: str, video_mode: str, music_mode: str) -> str:
    values = {visual_mode, video_mode, music_mode}
    if values <= {"未使用AI视觉", "human"}:
        return "no_gen_ai"
    if visual_mode == "AI-generated" and video_mode == "AI-generated" and music_mode == "AI-generated":
        return "fully_gen_ai"
    return "partly_gen_ai"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="写入 MV 项目的当前 AI 使用披露与具名签收")
    ap.add_argument("project_root")
    ap.add_argument("--visual-mode", required=True, choices=AI_VISUAL_USAGE_MODES)
    ap.add_argument("--video-mode", required=True, choices=AI_VISUAL_USAGE_MODES)
    ap.add_argument("--publish-target", required=True)
    ap.add_argument("--territory", default="未定", help="例如 CN、EU、US；多法域用逗号分隔")
    ap.add_argument("--realism", default="unknown", choices=REALISM_MODES)
    ap.add_argument("--real-person", default="unknown", choices=REAL_PERSON_MODES)
    ap.add_argument("--music-mode", default="unknown", choices=MUSIC_MODES)
    ap.add_argument("--image-model-version", default="未记录")
    ap.add_argument("--video-model-version", default="未记录")
    ap.add_argument("--human-contribution", required=True)
    ap.add_argument("--reviewer", required=True)
    ap.add_argument("--no-progress", action="store_true",
                    help="显式只写披露证据，不尝试完成 workflow 阶段")
    args = ap.parse_args(argv)

    root = disclosure.resolve_root_or_exit(args.project_root)
    reviewer = str(args.reviewer).strip()
    contribution = str(args.human_contribution).strip()
    if reviewer in PLACEHOLDER_REVIEWERS or not contribution:
        print("[err] disclosure 需要真实 --reviewer 与非空 --human-contribution", file=sys.stderr)
        return 1
    if args.real_person == "unauthorized":
        print("[block] 未授权真人身份/肖像不得进入 MV 发布链", file=sys.stderr)
        return 1

    meta = disclosure.load_meta(root)
    runtime = runtime_state_from_settings(mv_utils.parse_settings(root))
    payload = disclosure.base_payload(
        root, "mv_ai_usage", meta,
        publish_target=args.publish_target,
        human_contribution=contribution,
    )
    # Avoid persisting a workstation-specific absolute path in portable output.
    payload.update({
        "schema_version": 2,
        "project_root": ".",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "complete": True,
        "reviewer": reviewer,
        "territories": [row.strip() for row in args.territory.split(",") if row.strip()],
        "realism": args.realism,
        "real_person_status": args.real_person,
        "music_mode": args.music_mode,
        "gen_ai_classification": _classification(args.visual_mode, args.video_mode, args.music_mode),
        "song_rights_status": meta.get("song_rights_status") or meta.get("rights_status") or "unknown",
        "visual_mode": args.visual_mode,
        "video_mode": args.video_mode,
        "image_model": runtime["image_model"],
        "image_model_version": args.image_model_version,
        "image_channel": runtime["image_channel"],
        "image_backend": runtime["image_backend"],
        "video_model": runtime["video_model"],
        "video_model_version": args.video_model_version,
        "video_channel": runtime["video_channel"],
        "video_backend": runtime["video_backend"],
        "inputs_sha256": _input_bindings(root),
    })
    field_lines = [
        f"- 输入歌权利状态：{payload['song_rights_status']}",
        f"- GenAI 分类：{payload['gen_ai_classification']}",
        f"- 视觉 / 视频：{payload['visual_mode']} / {payload['video_mode']}",
        f"- 音乐：{payload['music_mode']}",
        f"- 真实感 / 真人：{payload['realism']} / {payload['real_person_status']}",
        f"- 生图：{payload['image_model']} @ {payload['image_channel']} ({payload['image_model_version']})",
        f"- 生视频：{payload['video_model']} @ {payload['video_channel']} ({payload['video_model_version']})",
        f"- 发布平台 / 法域：{payload['publish_target']} / {', '.join(payload['territories']) or '未定'}",
        f"- 复核人：{payload['reviewer']}",
    ]
    _, md_path = disclosure.write(
        root, payload,
        md_title=f"AI 使用说明 — MV《{payload['title']}》",
        field_lines=field_lines,
        notes=NOTES,
        contribution_placeholder="（本 schema 不允许空白）",
    )
    health = completion.stage_health(root, "disclosure")
    if not health["ok"]:
        print("[draft] 披露已写入但未达到完成态：" + "；".join(health["errors"]), file=sys.stderr)
        return 1
    if not args.no_progress:
        try:
            completion.mark_stage_complete(root, "disclosure")
        except ValueError as exc:
            print(f"[err] 披露已写入，但完成态未建立：{exc}", file=sys.stderr)
            return 1
    else:
        print("[evidence-only] --no-progress：未声明 disclosure 阶段完成", file=sys.stderr)
    print(f"[ok] AI 使用披露：{md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
