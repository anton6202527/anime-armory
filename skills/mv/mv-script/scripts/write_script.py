#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
write_script.py — MV 剧本创作脚本（听歌识影）。

从歌词 + 节拍分析 (beatgrid) 创作 MV 的【视觉蓝图】与角色/场景设定。
"""
import argparse
import hashlib
import json
import os
import re
import sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
MV_UTILS_PATH = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "mv_utils.py")


def load_mv_utils():
    spec = importlib.util.spec_from_file_location("mv_utils", MV_UTILS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mv_utils = load_mv_utils()


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_text(path, default=""):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _settings_digest(settings):
    """Hash only choices that can change the visual blueprint."""
    keys = ("MV用途", "MV视觉风格", "合成画幅", "发行目标平台", "演唱口型", "字幕语言")
    payload = {key: settings.get(key) for key in keys if settings.get(key) is not None}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _section_names(beatgrid, meta):
    rows = (beatgrid or {}).get("sections") or []
    names = [str(row.get("section") or row.get("name") or row.get("label") or "").strip()
             for row in rows if isinstance(row, dict)]
    names = [name for name in names if name]
    # A measured beatgrid is the timing truth.  _meta.structure remains only a
    # rough-project fallback and must not silently override reviewed sections.
    if names:
        return names
    return [str(value) for value in (meta.get("structure") or []) if str(value).strip()]


def build_script_prompt(root, lyrics, beatgrid, meta, settings):
    sections = _section_names(beatgrid, meta)
    
    section_str = ", ".join(sections)
    
    return f"""# MV 视觉剧本创作任务

请作为资深 MV 导演，为以下歌曲创作详细的视觉剧本（视觉蓝图）。

## 1. 歌曲信息
- 歌曲名称：{meta.get('title', '未知')}
- 视觉风格：{settings.get('MV视觉风格', '电影叙事')}
- 目标平台：{meta.get('target_platform', '跨平台')}
- 画幅：{meta.get('aspect', '16:9')}
- 歌曲结构：{section_str}

## 2. 歌词参考
{lyrics}

## 3. 节奏与能量参考 (beatgrid)
{json.dumps(beatgrid, ensure_ascii=False, indent=2) if beatgrid else "尚未进行节拍分析"}

## 任务要求
请基于以上信息，产出以下内容：

### A. 核心视觉概念
- **叙事模式**：(如：循环往复的叙事、双时空交错、纯意识流隐喻等)
- **视觉母题 (Motif)**：(贯穿全片的视觉符号，如：不断凋谢的花、流动的霓虹灯、飞鸟、碎裂的镜子)
- **色彩剧本 (Color Script)**：(请为每个大段落 [Intro, Verse, Chorus, Bridge, Outro] 分别定义主灯光色、对比色和视觉氛围。例如：Verse-冷白孤寂，Chorus-红蓝双色霓虹高能)

### B. 视觉蓝图 (段落 ↔ 画面映射)
请为每个段落 ({section_str}) 设计具体的画面意图。格式如下：
- [段落名] → 画面：(详细描述画面内容、情绪、主角状态、运镜意图。副歌要高能，verse要铺垫)
- [段落名] → 动作强度/风格：(参考 dance_choreography.md 定下力量等级 Level 1-10 和动作取向)
- [段落名] → 灯光/色彩：(从色彩剧本中派生，描述具体的灯光方向和色调)

### C. 角色设定 (主要主角)
- **身份描述**：
- **妆造定妆词**：(包含发型、五官特征、主要服装风格、配色，确保可用于生图)
- **运动/舞蹈特征**：(角色擅长的动作风格，如：柔弱、爆发力强、优雅等)
- **演唱特征 (Vocal Traits)**：(描述主角唱歌时的神态。如：闭眼深情、对着麦克风嘶吼、轻声呢喃时的嘴型特征)

### D. 场景设定
- **主场景描述**：

---
请直接输出 Markdown 格式的【视觉蓝图.md】内容，以及对应的角色卡文本。
"""


def main():
    ap = argparse.ArgumentParser(description="MV 剧本创作引擎")
    ap.add_argument("project_root")
    ap.add_argument("--save", action="store_true", help="保存本次剧本创作 prompt 到 设定/mv_script_prompt.md")
    ap.add_argument("--content-file", help="把 LLM 生成的视觉蓝图 Markdown 写入 视觉蓝图.md，并回写对应进度")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)

    meta = load_json(os.path.join(root, "_meta.json"), {})
    # 统一走本线 settings loader（正确处理 **加粗** key、跳过 `## 记录` 区），不再手写解析——
    # 旧的内联解析会误读加粗键、且会吃进 ## 记录 块的行。
    settings = mv_utils.parse_settings(root)

    lyrics = read_text(os.path.join(root, "词", "lyrics.md"))
    beatgrid = load_json(os.path.join(root, "节拍", "beatgrid.json"))

    prompt = build_script_prompt(root, lyrics, beatgrid, meta, settings)
    prompt_path = os.path.join(root, "设定", "mv_script_prompt.md")
    if args.save:
        write_text(prompt_path, prompt)
    
    print("--- MV SCRIPT COMPOSER PROMPT ---")
    print(prompt)
    print("--- END PROMPT ---")

    if args.content_file:
        if not os.path.exists(args.content_file):
            print(f"[err] 找不到 --content-file：{args.content_file}", file=sys.stderr)
            sys.exit(2)
        content = read_text(args.content_file)
        if not content.strip():
            print("[err] --content-file 为空", file=sys.stderr)
            sys.exit(2)
        blueprint_path = os.path.join(root, "视觉蓝图.md")
        write_text(blueprint_path, content)
        song_path = mv_utils.find_song(root)
        state = {
            "schema_version": 2,
            "kind": "mv_script_state",
            "source": {
                "original_name": os.path.basename(args.content_file),
                "sha256": mv_utils.content_hash(args.content_file),
            },
            "song_timing": settings.get("歌曲输入时序") or meta.get("song_timing") or "先传音乐",
            "has_song": song_path is not None,
            "has_beatgrid": beatgrid is not None,
            "sections_verified": bool((beatgrid or {}).get("sections_verified")),
            "sections_complete": bool((beatgrid or {}).get("sections_complete")),
            "section_names": _section_names(beatgrid, meta),
            "inputs_sha256": {
                "song": mv_utils.content_hash(song_path),
                "beatgrid": mv_utils.content_hash(os.path.join(root, "节拍", "beatgrid.json")),
                "lyrics": mv_utils.content_hash(os.path.join(root, "词", "lyrics.md")),
                "settings_script": _settings_digest(settings),
            },
            "output_sha256": mv_utils.content_hash(blueprint_path),
        }
        write_text(os.path.join(root, "设定", "mv_script_state.json"), json.dumps(state, ensure_ascii=False, indent=2) + "\n")
        stage_key = "script_review" if (
            state["has_song"] and state["has_beatgrid"]
            and state["sections_verified"] and state["sections_complete"]
        ) else "script"
        mv_utils.update_progress_stage(root, stage_key)
        print(f"[ok] 视觉蓝图.md 已写入；_进度.md 标记 {stage_key}")
    
    print(f"\n[info] 作品根：{root}")
    if args.save:
        print(f"[info] prompt 已保存：{prompt_path}")
    print("[next] 请根据上述 prompt 生成剧本内容；可用 --content-file 写回 视觉蓝图.md。")


if __name__ == "__main__":
    main()
