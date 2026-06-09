#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write publishing-facing AI usage metadata for a song project."""
import argparse
import json
import os
import sys
from datetime import date

from contract import AI_AUDIO_USAGE_MODES, AI_LYRICS_USAGE_MODES


def load_meta(root):
    path = os.path.join(root, "_meta.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_markdown(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        f"# AI 使用说明 — {payload['title']}",
        "",
        f"- 生成日期：{payload['generated_at']}",
        f"- 项目：{payload['project_root']}",
        f"- 歌词使用类型：{payload['lyrics_mode']}",
        f"- 音频/演唱使用类型：{payload['audio_mode']}",
        f"- 作曲后端：{payload['compose_backend']}",
        f"- 演唱音色来源：{payload['vocal_source']}",
        f"- 词曲权利状态：{payload['rights_status']}",
        f"- 发布平台/用途：{payload['publish_target']}",
        "",
        "## 人工贡献记录",
        payload["human_contribution"] or "（待填写：主题、蓝图、歌词修改、挑版、混音/母带、人工审听等）",
        "",
        "## 说明",
        "- 若歌曲音频由 AI 音乐模型直接生成，通常按 AI-generated 留痕。",
        "- 若人类完成作词作曲录唱，AI 只用于润色、检查、分离或混音辅助，可记录为 AI-assisted。",
        "- 克隆或模仿真实歌手嗓音需明确授权；未授权真人嗓不得使用。",
        "- 发布前按目标平台最新规则复核；本文件只做项目留痕，不替代法律意见。",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description="写入 song 项目的 AI 音频使用披露元数据")
    ap.add_argument("project_root")
    ap.add_argument("--audio-mode", required=True, choices=AI_AUDIO_USAGE_MODES)
    ap.add_argument("--lyrics-mode", default="AI-generated", choices=AI_LYRICS_USAGE_MODES)
    ap.add_argument("--publish-target", default="未定")
    ap.add_argument("--human-contribution", default="")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)
    meta = load_meta(root)
    payload = {
        "schema_version": 1,
        "kind": "song_ai_usage",
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "title": meta.get("title") or os.path.basename(root),
        "rights_status": meta.get("rights_status", "unknown"),
        "vocal_source": meta.get("vocal_source") or "未记录",
        "compose_backend": meta.get("song_backend") or meta.get("compose_backend") or "未记录",
        "lyrics_mode": args.lyrics_mode,
        "audio_mode": args.audio_mode,
        "publish_target": args.publish_target,
        "human_contribution": args.human_contribution,
    }
    compliance_dir = os.path.join(root, "合规")
    write_json(os.path.join(compliance_dir, "ai_usage.json"), payload)
    write_markdown(os.path.join(compliance_dir, "AI使用说明.md"), payload)
    print(f"[ok] AI 使用披露：{os.path.join(compliance_dir, 'AI使用说明.md')}")


if __name__ == "__main__":
    main()
