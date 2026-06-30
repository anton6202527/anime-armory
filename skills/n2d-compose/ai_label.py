#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 生成合成内容标识 —— n2d-compose 导出环节执行（《标识办法》2025-09 第4/5条 + 强制国标 GB 45438-2025）。

为什么在这里：导出成片后顺手做一次 best-effort 标识后处理，减少发布前遗漏。
但 AI 标识/披露/水印在 n2d 中是**非阻断发布待办**：不得因为未配置、未落标或后处理失败而阻断合成、
进度回写或 dashboard 记账。数字水印、平台侧披露与严格 GB 45438 字节级封装均可在工具外补。

做什么：对已产出的成片 MP4 做一道 post-pass——
  1. Pillow 渲染「AI生成」角标 PNG（ffmpeg 无 libass，沿用 render_subs 的 Pillow→overlay 套路）；
  2. ffmpeg overlay 角标 + 写入 GB 45438 元数据字段；
  3. 回写 `合规/compliance_manifest.json` 的 `ai_labeling.explicit_label.status=done` /
     `implicit_metadata.applied=true`，供发布检查参考。

诚实边界：GB 45438 规定的是具体元数据扩展结构；本模块用 ffmpeg 通用 `-metadata` 写入语义字段
（service_provider_code / content_id / 生成合成标签），承载法定信息，但**未必逐字节等于 GB 45438 的
扩展盒格式**——严格字节级合规需专用编码器，属 follow-up。显式角标与语义元数据字段已落地、可机检。

纯函数（build_ai_metadata / label_overlay_spec / labeling_applicable）无依赖、有 pytest；
Pillow/ffmpeg 重活 best-effort，缺则透明跳过并返回未落标（不静默假装已标）。

用法：
  python3 ai_label.py <作品根> <第N集> <成片.mp4> [--position bottom-right] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ZH_FONT_PATHS = ["/System/Library/Fonts/STHeiti Medium.ttc",
                 "/System/Library/Fonts/PingFang.ttc"]
DEFAULT_LABEL_TEXT = "AI生成"
GB_SPEC = "GB45438-2025"
MARGIN_RATIO = 0.025          # 角标距边 = 短边 × 2.5%
FONT_RATIO = 0.030            # 角标字号 = 短边 × 3%


# ---------- 纯函数（可测） ----------

def labeling_applicable(ai_labeling: Optional[Dict[str, Any]]) -> bool:
    """是否需要落标。默认需要；仅 applicable is False 关闭（与 compliance.ai_labeling_required 同源）。"""
    if isinstance(ai_labeling, dict) and ai_labeling.get("applicable") is False:
        return False
    return True


def build_ai_metadata(ai_labeling: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """构造写入成片的 ffmpeg 元数据隐式标识字段（GB 45438 语义字段）。纯函数·可测。
    缺编码/编号时仍写「生成合成标签」与 spec（标识本身不能因编码缺失而不写），编码/编号留空由 gate 另行拦。"""
    meta = (ai_labeling or {}).get("implicit_metadata") if isinstance(ai_labeling, dict) else {}
    meta = meta if isinstance(meta, dict) else {}
    spc = str(meta.get("service_provider_code") or "").strip()
    cid = str(meta.get("content_id") or "").strip()
    label = (ai_labeling or {}).get("explicit_label") if isinstance(ai_labeling, dict) else {}
    text = str((label or {}).get("text") or DEFAULT_LABEL_TEXT).strip() or DEFAULT_LABEL_TEXT
    fields = {
        "ai_generated": "true",
        "synthetic_label": "AIGC",                 # 生成合成标签
        "generative_label_spec": str(meta.get("spec") or GB_SPEC),
        "service_provider_code": spc,
        "content_production_id": cid,
        "comment": (f"本内容由人工智能生成合成 / AI-generated synthetic content; "
                    f"label={text}; spec={meta.get('spec') or GB_SPEC}"
                    + (f"; service_provider={spc}" if spc else "")
                    + (f"; content_id={cid}" if cid else "")),
    }
    return fields


def label_overlay_spec(ai_labeling: Optional[Dict[str, Any]], w: int, h: int) -> Dict[str, Any]:
    """显式角标的渲染规格（文案/字号/位置）。纯函数·可测。position ∈ 四角；默认 bottom-right。"""
    label = (ai_labeling or {}).get("explicit_label") if isinstance(ai_labeling, dict) else {}
    label = label if isinstance(label, dict) else {}
    text = str(label.get("text") or DEFAULT_LABEL_TEXT).strip() or DEFAULT_LABEL_TEXT
    position = str(label.get("position") or "bottom-right").strip().lower()
    short = max(1, min(int(w), int(h)))
    font_size = max(18, int(short * FONT_RATIO))
    margin = max(8, int(short * MARGIN_RATIO))
    return {"text": text, "position": position, "font_size": font_size, "margin": margin}


def overlay_xy_expr(position: str, margin: int) -> str:
    """position → ffmpeg overlay 坐标表达式（W/H=主画面，w/h=角标）。纯函数·可测。"""
    m = int(margin)
    return {
        "top-left": f"{m}:{m}",
        "top-right": f"W-w-{m}:{m}",
        "bottom-left": f"{m}:H-h-{m}",
        "bottom-right": f"W-w-{m}:H-h-{m}",
    }.get((position or "bottom-right"), f"W-w-{m}:H-h-{m}")


# ---------- best-effort 渲染 / 落标 ----------

def manifest_path(root: str) -> Path:
    return Path(root) / "合规" / "compliance_manifest.json"


def load_manifest(root: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(manifest_path(root).read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_font(size: int):
    try:
        from PIL import ImageFont  # type: ignore
    except Exception:
        return None
    for p in ZH_FONT_PATHS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def render_label_png(spec: Dict[str, Any], out_path: str) -> bool:
    """渲染角标透明 PNG（描边保证深浅底都可读）。Pillow 缺/失败 → False（不静默成功）。"""
    try:
        from PIL import Image, ImageDraw  # type: ignore
    except Exception:
        return False
    try:
        text = spec["text"]
        fs = int(spec["font_size"])
        font = _load_font(fs)
        pad = max(6, fs // 4)
        # 量文字尺寸
        tmp = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        d0 = ImageDraw.Draw(tmp)
        try:
            l, t, r, b = d0.textbbox((0, 0), text, font=font)
            tw, th = r - l, b - t
        except Exception:
            tw, th = fs * len(text), fs
        img = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 110))  # 半透明底衬
        d = ImageDraw.Draw(img)
        d.text((pad, pad), text, font=font, fill=(255, 255, 255, 235),
               stroke_width=max(1, fs // 16), stroke_fill=(0, 0, 0, 235))
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path)
        return True
    except Exception:
        return False


def _probe_size(mp4: str) -> Optional[Tuple[int, int]]:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", mp4],
            capture_output=True, text=True, timeout=60)
        if out.returncode != 0:
            return None
        w, h = out.stdout.strip().split("x")
        return int(w), int(h)
    except Exception:
        return None


def apply_label_and_metadata(mp4: str, label_png: str, xy: str, metadata: Dict[str, str]) -> bool:
    """ffmpeg post-pass：overlay 角标 + 写元数据，原位替换成片。ffmpeg 缺/失败 → False。"""
    src = Path(mp4)
    if not src.exists():
        return False
    tmp = str(src.with_suffix(".labeled.mp4"))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-i", label_png,
           "-filter_complex", f"[0:v][1:v]overlay={xy}",
           "-c:a", "copy", "-movflags", "+faststart"]
    for k, v in metadata.items():
        cmd += ["-metadata", f"{k}={v}"]
    cmd.append(tmp)
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if res.returncode != 0 or not os.path.exists(tmp):
            return False
        os.replace(tmp, mp4)
        return True
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return False


def mark_manifest_applied(root: str) -> bool:
    """回写 manifest：explicit_label.status=done + implicit_metadata.applied=true（供发布检查参考）。"""
    data = load_manifest(root)
    if not isinstance(data, dict):
        return False
    ai = data.setdefault("ai_labeling", {})
    if not isinstance(ai, dict):
        return False
    label = ai.setdefault("explicit_label", {})
    meta = ai.setdefault("implicit_metadata", {})
    if isinstance(label, dict):
        label["status"] = "done"
    if isinstance(meta, dict):
        meta["applied"] = True
    try:
        manifest_path(root).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return True
    except Exception:
        return False


def apply(root: str, ep: str, mp4: str, position: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
    """对成片落 AI 标识（显式角标 + 元数据隐式标识）并回写 manifest。返回结果字典。"""
    result: Dict[str, Any] = {"applied": False, "notes": []}
    data = load_manifest(root)
    if not isinstance(data, dict):
        result["notes"].append("缺 compliance_manifest.json——AI 标识无法自动落；不阻断合成，发布前按目标地区/平台补齐")
        return result
    ai = data.get("ai_labeling") if isinstance(data.get("ai_labeling"), dict) else None
    if not labeling_applicable(ai):
        result["applied"] = False
        result["skipped"] = "applicable=false"
        result["notes"].append("ai_labeling.applicable=false——按声明跳过落标（纯海外/特殊场景，理由见 manifest.notes）")
        return result
    if position:
        ai = dict(ai or {})
        lab = dict(ai.get("explicit_label") or {})
        lab["position"] = position
        ai["explicit_label"] = lab
    size = _probe_size(mp4) or (1080, 1920)
    spec = label_overlay_spec(ai, size[0], size[1])
    metadata = build_ai_metadata(ai)
    xy = overlay_xy_expr(spec["position"], spec["margin"])
    result["spec"] = spec
    result["metadata"] = metadata
    if dry_run:
        result["notes"].append("dry-run：仅计算 spec/metadata，不改成片、不回写 manifest")
        return result
    work = Path(root) / "合成" / ep / "_work"
    label_png = str(work / "ai_label.png")
    if not render_label_png(spec, label_png):
        result["notes"].append("⚠️ 角标 PNG 渲染失败（缺 Pillow？）——AI 标识未落；不阻断合成，发布前补齐")
        return result
    if not apply_label_and_metadata(mp4, label_png, xy, metadata):
        result["notes"].append("⚠️ ffmpeg overlay/元数据写入失败——AI 标识未落；不阻断合成，发布前补齐")
        return result
    marked = mark_manifest_applied(root)
    result["applied"] = True
    result["manifest_updated"] = marked
    result["notes"].append(f"✓ 已落 AI 标识：角标「{spec['text']}」@{spec['position']} + GB45438 元数据；manifest 回写={'ok' if marked else '失败'}")
    return result


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("mp4")
    ap.add_argument("--position", default=None, choices=["top-left", "top-right", "bottom-left", "bottom-right"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = apply(ns.root, ns.episode, ns.mp4, position=ns.position, dry_run=ns.dry_run)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        for n in res.get("notes", []):
            print(n)
    return 0  # advisory：AI 标识不得阻断 compose / progress / dashboard


if __name__ == "__main__":
    raise SystemExit(main())
