#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cover_pack.py — 制MV 作品卡片封面：竖版 key visual 的 prompt/job 包 + 回填 helper。

作品列表卡片要一张竖版封面（约 9:16）。本脚本是 mv 本线自包含步骤，
不调用任何后端、不伪装云端自动化（B4/C4）：

  pack       读 `_meta.json` + `视觉蓝图.md`，产出稳定的封面 prompt + job 包
             （`出图/封面/prompt/cover_prompt.md`、`出图/封面/cover_job.json`）
             + 合规留痕；`_meta.cover` 保持 null。纯净机（断网/无凭证/无重依赖）
             上也能一路产出 job 包。
  set-cover  真正渲染出竖版 PNG 后，用确定性方式把 `_meta.cover` 回填为
             作品根相对路径，并回写 `_进度.md` 封面行。

「由什么生成这张封面」落到具体模型名（含版本，如 GPT Image 2），渠道/CLI
作为访问入口分列（C5）。

用法:
    python3 cover_pack.py pack <作品根> [--force]
    python3 cover_pack.py set-cover <作品根> [--png 出图/封面/图片/cover.png] [--force]
"""
import argparse
import json
import os
import re
import sys
from datetime import date

COVER_DIR = os.path.join("出图", "封面")
PROMPT_REL = os.path.join(COVER_DIR, "prompt", "cover_prompt.md")
JOB_REL = os.path.join(COVER_DIR, "cover_job.json")
DEFAULT_PNG_REL = os.path.join(COVER_DIR, "图片", "cover.png")
# 竖版封面画幅：作品卡片缩略图约 9:16 / 5:7，固定竖版，不跟随成片横竖屏。
COVER_ASPECT = "9:16"


def load_meta(root):
    path = os.path.join(root, "_meta.json")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"找不到 _meta.json：{path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_meta(root, meta):
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def rel_within_root(root, value):
    """规范化为作品根相对路径；越界即拒。"""
    abs_path = value if os.path.isabs(value) else os.path.join(root, value)
    abs_path = os.path.abspath(abs_path)
    rel = os.path.relpath(abs_path, os.path.abspath(root)).replace(os.sep, "/")
    if rel == ".." or rel.startswith("../"):
        raise ValueError(f"路径必须在作品根内：{value}")
    return abs_path, rel


def _blueprint_concept(root):
    """从 视觉蓝图.md 抽 MV 视觉概念开头几行作封面 brief（缺则空）。"""
    path = os.path.join(root, "视觉蓝图.md")
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    grab = []
    in_concept = False
    for line in lines:
        if line.startswith("## MV 视觉概念"):
            in_concept = True
            continue
        if in_concept:
            if line.startswith("## "):
                break
            grab.append(line.rstrip())
    return "\n".join(l for l in grab if l.strip())


def build_cover_prompt(meta, concept):
    title = meta.get("title", "未命名")
    model = (meta.get("image_model") or "GPT Image 2").strip()
    channel = (meta.get("image_channel") or meta.get("image_backend") or "Codex").strip()
    style = (meta.get("visual_style") or "").strip()
    use = (meta.get("use_case") or "").strip()
    synopsis = (meta.get("synopsis") or "").strip()
    concept_block = concept.strip() or "（视觉蓝图未填 MV 视觉概念；先补主角/场景/画风再刷新本封面 prompt）"
    return f"""# 作品封面 prompt — MV《{title}》（竖版 key visual）

> 作品列表卡片封面。**竖版单图**（画幅 {COVER_ASPECT}，约 5:7~9:16），一眼读懂这支 MV 是什么。
> 生成者（C5）：**{model}**（生成模型，含版本）；访问入口：**{channel}**（渠道/CLI，分列，不当生成者）。
> 本文件只是 prompt 包，不调用后端；渲染出 PNG 后跑 `cover_pack.py set-cover` 回填 `_meta.cover`。

## 封面意图
- 简介锚：{synopsis or '（_meta.synopsis 待补）'}
- 用途 / 风格：{use or '（用途待补）'} · {style or '（风格待补）'}

## 视觉概念（继承视觉蓝图，不另起风格）
{concept_block}

## 导演视角封面装配（竖版 · 一张顶全曲气质）
[主视觉竖构图 {COVER_ASPECT}][能量机位：主角高光/副歌气质，非正面平视证件照]，
[主角·锚点句·主妆造] 处于本曲最具代表性的一瞬，
置身 [代表性场景+环境氛围]，[演出光+色胶+调性，非均匀平光]，
[{style or '本曲画风'} + 渲染 + 竖版画幅]，
留出上/下安全边（卡片缩略图不被裁掉主体），画面内**不压字幕/歌名/logo**（卡片外层另render）。

## 一致性锚（与共享定妆同源，封面不得换脸换画风）
- 主角身份锚点句：<拼 设定/characters/<主角>.md 锚点句>
- global_style / palette_anchor：<继承 视觉蓝图 单曲一致性包>
- 参考图 / 主体ID / LoRA（若已启用 MV一致性增强）：<按 references/prompt_format.md 登记后再喂>

## 落档
- 渲染 → `{DEFAULT_PNG_REL}`（竖版 PNG）
- 跑 `record_generation.py <作品根> --asset {DEFAULT_PNG_REL} --model "{model}" --channel "{channel}" --prompt {PROMPT_REL}` 留生成收据
- 跑 `cover_pack.py set-cover <作品根>` 回填 `_meta.cover` + `_进度.md`
"""


def build_job(meta):
    model = (meta.get("image_model") or "GPT Image 2").strip()
    channel = (meta.get("image_channel") or meta.get("image_backend") or "Codex").strip()
    return {
        "schema_version": 1,
        "kind": "mv_cover_job",
        "status": "prompt_ready",
        "generated_at": date.today().isoformat(),
        "note": "纯 prompt/job 包，不调用后端；断网/无凭证的纯净机也能产出。渲染由用户在对应渠道完成后回填。",
        "cover": {
            "role": "work_card_cover",
            "orientation": "portrait",
            "aspect": COVER_ASPECT,
            "target_png_rel": DEFAULT_PNG_REL.replace(os.sep, "/"),
            "source_prompt_rel": PROMPT_REL.replace(os.sep, "/"),
        },
        # C5：生成者=具体模型（含版本）；渠道/CLI 作为访问入口分列，不当生成者。
        "generation": {
            "model": model,
            "channel": channel,
            "provider_called": False,
        },
        "compliance": {
            "ai_visual_usage": meta.get("ai_visual_usage"),
            "song_rights_status": meta.get("song_rights_status"),
            "meta_cover_state": "null_until_rendered",
        },
    }


def _flip_progress_cover_rows(root):
    """确定性回写 _进度.md：把封面两行勾上（B5）。找不到就静默跳过。"""
    path = os.path.join(root, "_进度.md")
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        text = f.read()
    new = re.sub(r"- \[ \](?=[^\n]*封面 prompt/job 包)", "- [x]", text)
    new = re.sub(r"- \[ \](?=[^\n]*封面已渲染并回填)", "- [x]", new)
    if new != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)


def _flip_progress_pack_row(root):
    """pack 完成后只勾第一行（job 包已产），不勾"已渲染"行。"""
    path = os.path.join(root, "_进度.md")
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        text = f.read()
    new = re.sub(r"- \[ \](?=[^\n]*封面 prompt/job 包)", "- [x]", text)
    if new != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)


def cmd_pack(root, force):
    meta = load_meta(root)
    prompt_path = os.path.join(root, PROMPT_REL)
    job_path = os.path.join(root, JOB_REL)
    if os.path.exists(prompt_path) and not force:
        print(f"[skip] 封面 prompt 已存在（--force 覆盖刷新）：{PROMPT_REL}")
    else:
        os.makedirs(os.path.dirname(prompt_path), exist_ok=True)
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(build_cover_prompt(meta, _blueprint_concept(root)))
        print(f"[ok] 封面 prompt → {PROMPT_REL}")
    os.makedirs(os.path.dirname(job_path), exist_ok=True)
    with open(job_path, "w", encoding="utf-8") as f:
        json.dump(build_job(meta), f, ensure_ascii=False, indent=2)
    print(f"[ok] 封面 job 包 → {JOB_REL}（provider_called=false，_meta.cover 保持 null）")
    _flip_progress_pack_row(root)
    job = build_job(meta)
    print(f"[C5] 生成者={job['generation']['model']}（模型）· 访问入口={job['generation']['channel']}（渠道）")
    print(f"[next] 渲染竖版 PNG → {DEFAULT_PNG_REL} → record_generation.py 留收据 → "
          f"cover_pack.py set-cover 回填 _meta.cover")
    return 0


def cmd_set_cover(root, png, force):
    meta = load_meta(root)
    try:
        abs_png, rel_png = rel_within_root(root, png or DEFAULT_PNG_REL)
    except ValueError as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 2
    if not os.path.isfile(abs_png):
        print(f"[err] 竖版封面 PNG 不存在，先渲染再回填：{rel_png}", file=sys.stderr)
        print("       纯净机上封面步骤只到 job 包为止，_meta.cover 应保持 null。", file=sys.stderr)
        return 2
    if rel_png.lower().rsplit(".", 1)[-1] not in ("png",):
        print(f"[err] 封面必须是 PNG：{rel_png}", file=sys.stderr)
        return 2
    # write_if_absent 语义：不覆盖用户已设的封面（除非 --force）。
    existing = meta.get("cover")
    if isinstance(existing, str) and existing.strip() and existing.strip() != rel_png and not force:
        print(f"[skip] _meta.cover 已由用户/前次设为 {existing}；--force 才覆盖为 {rel_png}")
        return 0
    meta["cover"] = rel_png
    save_meta(root, meta)
    _flip_progress_cover_rows(root)
    print(f"[ok] _meta.cover → {rel_png}（作品根相对路径，桌面卡片可用）")
    print("[note] 记得已用 record_generation.py 留下该封面的 model/channel/prompt/asset 收据。")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="制MV 作品卡片封面 prompt/job 包 + 回填")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_pack = sub.add_parser("pack", help="产出封面 prompt/job 包（不调用后端）")
    p_pack.add_argument("root")
    p_pack.add_argument("--force", action="store_true", help="覆盖刷新已存在的封面 prompt")
    p_set = sub.add_parser("set-cover", help="渲染出竖版 PNG 后回填 _meta.cover")
    p_set.add_argument("root")
    p_set.add_argument("--png", default=None, help=f"竖版封面 PNG（默认 {DEFAULT_PNG_REL}）")
    p_set.add_argument("--force", action="store_true", help="覆盖用户已设的 _meta.cover")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    try:
        if args.cmd == "pack":
            return cmd_pack(root, args.force)
        return cmd_set_cover(root, args.png, args.force)
    except FileNotFoundError as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
