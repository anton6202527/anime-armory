#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write publishing-facing AI usage metadata for a song project.

写盘/骨架统一走本线 song/_lib/disclosure.py（vendored，本线自包含）；本线只保留专属字段与文案。
"""
import argparse
import os
import sys

_COMMON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "song", "_lib"))
if _COMMON_DIR not in sys.path:
    sys.path.insert(0, _COMMON_DIR)
import disclosure  # noqa: E402

from contract import AI_AUDIO_USAGE_MODES, AI_LYRICS_USAGE_MODES  # noqa: E402

NOTES = [
    "- 若歌曲音频由 AI 音乐模型直接生成，通常按 AI-generated 留痕。",
    "- 若人类完成作词作曲录唱，AI 只用于润色、检查、分离或混音辅助，可记录为 AI-assisted。",
    "- 克隆或模仿真实歌手嗓音需明确授权；未授权真人嗓不得使用。",
    "- 发布前按目标平台最新规则复核；本文件只做项目留痕，不替代法律意见。",
]


def main():
    ap = argparse.ArgumentParser(description="写入 song 项目的 AI 音频使用披露元数据")
    ap.add_argument("project_root")
    ap.add_argument("--audio-mode", required=True, choices=AI_AUDIO_USAGE_MODES)
    ap.add_argument("--lyrics-mode", default="AI-generated", choices=AI_LYRICS_USAGE_MODES)
    ap.add_argument("--publish-target", default="未定")
    ap.add_argument("--human-contribution", default="")
    args = ap.parse_args()

    root = disclosure.resolve_root_or_exit(args.project_root)
    meta = disclosure.load_meta(root)
    payload = disclosure.base_payload(
        root, "song_ai_usage", meta,
        publish_target=args.publish_target,
        human_contribution=args.human_contribution,
    )
    payload.update({
        "rights_status": meta.get("rights_status", "unknown"),
        "vocal_source": meta.get("vocal_source") or "未记录",
        "compose_backend": meta.get("song_backend") or meta.get("compose_backend") or "未记录",
        "lyrics_mode": args.lyrics_mode,
        "audio_mode": args.audio_mode,
    })
    field_lines = [
        f"- 歌词使用类型：{payload['lyrics_mode']}",
        f"- 音频/演唱使用类型：{payload['audio_mode']}",
        f"- 作曲后端：{payload['compose_backend']}",
        f"- 演唱音色来源：{payload['vocal_source']}",
        f"- 词曲权利状态：{payload['rights_status']}",
        f"- 发布平台/用途：{payload['publish_target']}",
    ]
    _, md_path = disclosure.write(
        root, payload,
        md_title=f"AI 使用说明 — {payload['title']}",
        field_lines=field_lines,
        notes=NOTES,
        contribution_placeholder="（待填写：主题、蓝图、歌词修改、挑版、混音/母带、人工审听等）",
    )
    print(f"[ok] AI 使用披露：{md_path}")


if __name__ == "__main__":
    main()
