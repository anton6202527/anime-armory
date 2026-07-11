#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plan strict ad-video contracts and concise backend submission prompts.

Outputs:
  - 出视频/分镜/prompt/镜头NN.md
  - 出视频/分镜/video_jobs_manifest.json

Each Markdown file keeps the complete product/brand/legal contract for gates and
provenance.  Only its compiler block is model-facing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import inherit_contract
import route

AD_LIB = Path(__file__).resolve().parents[2] / "ad" / "_lib"
if str(AD_LIB) not in sys.path:
    sys.path.insert(0, str(AD_LIB))
from ad_video_prompt_compiler import compile_prompt, render_markdown  # noqa: E402

CAMERA_MANIFEST_REL = "skills/ad/references/运镜/manifest.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _shot_label(shot: Mapping[str, Any], index: int) -> str:
    raw = str(shot.get("shot_id") or shot.get("clip_id") or shot.get("id") or "")
    m = re.search(r"(\d+)", raw)
    if m:
        return f"镜头{int(m.group(1)):02d}"
    return f"镜头{index:02d}"


def _shots(storyboard: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    raw = storyboard.get("shots") or storyboard.get("clips") or []
    return [s for s in raw if isinstance(s, Mapping)]


def _duration(shot: Mapping[str, Any], fallback: float = 4.0) -> float:
    for key in ("duration", "duration_sec", "seconds", "时长"):
        raw = shot.get(key)
        if raw is None:
            continue
        m = re.search(r"\d+(?:\.\d+)?", str(raw))
        if m:
            return float(m.group(0))
    return fallback


def _assets(shot: Mapping[str, Any], prefix: str) -> List[str]:
    assets = shot.get("assets")
    if not isinstance(assets, Mapping):
        return []
    return sorted(str(k) for k, v in assets.items() if str(k).startswith(prefix) and bool(v))


def _image_paths(root: Path, label: str) -> Tuple[Path, Optional[Path], str]:
    first = root / "出图" / "分镜" / "图片" / f"{label}.png"
    end = root / "出图" / "分镜" / "图片" / f"{label}_end.png"
    if end.exists():
        return first, end, "frames2video"
    return first, None, "image2video"


def _route_by_clip(root: Path) -> Dict[str, Dict[str, Any]]:
    route_path = root / "出视频" / "分镜" / "prompt" / "video_model_routes.json"
    data = load_json(route_path)
    if not isinstance(data, dict) or not isinstance(data.get("routes"), list):
        data = route.run(str(root))
    return {
        str(item.get("clip")): item
        for item in data.get("routes", [])
        if isinstance(item, dict) and item.get("clip")
    }


def _contract_lines(contract: Mapping[str, Any]) -> List[str]:
    lines = []
    for key in ("品牌色", "光位锚", "轴线", "画风", "景别", "构图"):
        val = str(contract.get(key) or "").strip()
        if val:
            lines.append(f"- {key}：{val}")
    if not lines:
        lines.append("- 品牌色：继承出图 00_总览.md / storyboard visual_contract")
    return lines


def motion_instruction(shot: Mapping[str, Any], route_item: Mapping[str, Any]) -> str:
    shot_type = str(route_item.get("shot_type") or "")
    scene = str(shot.get("scene") or "")
    shot_text = str(shot.get("shot") or shot.get("frame") or "")
    if shot_type == "endcard" or "片尾" in scene or "end card" in shot_text.lower():
        return "镜头运动：固定机位或极慢推镜头；速度=轻微；方向=无或沿产品轴线轻推；起止=保持 logo、CTA、slogan、法律声明清晰可读，只允许轻微呼吸视差。"
    if "界面" in scene or "UI" in shot_text.upper() or "手机" in shot_text:
        return "镜头运动：缓慢推镜头；速度=缓慢；方向=沿手机/UI 正面轻推；起止=UI 保持 center 4x4，卡片轻微视差，不变形、不乱码。"
    if "主角" in shot_text or "人物" in scene or "情绪" in scene:
        return "镜头运动：手持晃动或稳定器跟拍；速度=轻微；方向=随人物微动；起止=人物表演自然，手机/UI 保持可读并留在中心安全区。"
    return "镜头运动：稳定器跟拍或移镜头；速度=匀速；方向=顺主体动线；起止=保持首帧构图和 action-safe 边距，不使用快速甩镜。"


def camera_motion_value(shot: Mapping[str, Any], route_item: Mapping[str, Any]) -> str:
    """Keep only the affirmative camera instruction for the provider prompt."""
    text = motion_instruction(shot, route_item)
    text = re.sub(r"^镜头运动[：:]", "", text).strip()
    return text.split("；起止=", 1)[0].strip("。； ")


def build_prompt(
    root: Path,
    shot: Mapping[str, Any],
    index: int,
    contract: Mapping[str, Any],
    route_item: Mapping[str, Any],
) -> Tuple[str, Dict[str, Any]]:
    label = _shot_label(shot, index)
    first, end, mode = _image_paths(root, label)
    prod_assets = _assets(shot, "PROD_")
    brand_assets = _assets(shot, "BRAND_")
    duration = _duration(shot, float(route_item.get("duration") or 4.0))
    expected = root / "出视频" / "分镜" / "视频" / f"{label}.mp4"
    contract_text = "\n".join(_contract_lines(contract))
    prod_line = "、".join(prod_assets) if prod_assets else "无"
    brand_line = "、".join(brand_assets) if brand_assets else "无"
    shot_text = str(shot.get("shot") or shot.get("frame") or "").strip()
    action = str(shot.get("action") or shot.get("product_action") or shot_text).strip()
    environment_motion = str(
        shot.get("environment_motion")
        or shot.get("environment_interaction")
        or shot.get("dynamic_detail")
        or ""
    ).strip()
    continuity = shot.get("continuity") if isinstance(shot.get("continuity"), Mapping) else {}
    end_state = str(shot.get("end_state") or continuity.get("end_state") or "").strip()
    if not end_state:
        end_state = "尾帧构图与下一镜切点" if end else "产品、Logo 与主视觉稳定落幅"
    product_hold = (
        "同一包装结构、产品比例、Logo 位置与品牌色；继承首帧已有 UI 像素"
        if prod_assets else
        "同一品牌色、Logo 位置与版式层级；继承首帧已有品牌像素"
    )
    compiler_source = {
        "clip_id": label,
        "backend": route_item.get("primary") or "generic",
        "mode": mode,
        "product_action": action,
        "camera_motion": camera_motion_value(shot, route_item),
        "environment_motion": environment_motion,
        "end_state": end_state,
        "product_hold": product_hold,
        "text_strategy": "保持首帧已有包装、UI 与文字像素稳定；CTA、slogan、法律声明由后期可控叠加",
        "negative_elements": [
            "包装文字或 Logo 变形",
            "品牌色漂移",
            "新增乱码或第三方 App UI",
            "人物身份漂移",
            "医疗或心理疗效暗示",
            "CTA 或法律声明贴边",
            "快速运镜造成产品、UI 或文字抖花",
        ],
    }
    compiled = compile_prompt(compiler_source)
    if compiled["lint"]["errors"]:
        raise ValueError(f"{label} prompt compiler blocked: {compiled['lint']['errors']}")
    brand_registry = load_json(root / "出图" / "共享" / "asset_registry.json", {}) or {}
    brand = brand_registry.get("brand") if isinstance(brand_registry.get("brand"), Mapping) else {}
    brand_name = str(brand.get("name") or brand.get("text_logo") or "登记品牌")
    locked_texts = []
    for key in ("text_logo", "slogan"):
        if brand.get(key):
            locked_texts.append(str(brand[key]))
    text = f"""# {label} 图生视频 prompt

## 输入帧
- 首帧：{first.relative_to(root).as_posix()}
- 尾帧：{end.relative_to(root).as_posix() if end else "无；本镜使用首帧图生视频"}
- 模式：{mode}
- 目标时长：{duration:.1f}s

## 上游视觉契约
{contract_text}

## 模型路由
- primary：{route_item.get("primary", "未定")}
- fallback：{", ".join(route_item.get("fallback") or []) or "无"}
- quality_tier：{route_item.get("quality_tier", "n/a")}
- route_reason：{route_item.get("reason", "")}

## 画面连续性
- 场景：{shot.get("scene", "")}
- 镜头：{shot.get("shot") or shot.get("frame") or ""}
- 首帧内容：严格继承 `出图/分镜/图片/{label}.png` 的构图、品牌色、光位、轴线、产品/UI位置。
- 尾帧接力：{"结尾必须贴近尾帧 `" + end.relative_to(root).as_posix() + "`，作为下一镜切点。" if end else "片尾/收束镜头，保持静态可读。"}

## 运镜与动作
运镜参考：{CAMERA_MANIFEST_REL}
{motion_instruction(shot, route_item)}
动作只服务 VO 节奏：起幅稳，1/3 处进入主动作，结尾留 8-12 帧稳定画面用于剪辑接缝。

## 产品/品牌身份锁定
- 资产引用：{prod_line} / {brand_line}
- 身份锁定句：与首帧、尾帧和定妆包同一产品结构、同一 logo、同一品牌色；同一品牌“{brand_name}”；登记文案清晰可读，不乱码。
- 产品锁：{shot.get("product_lock", "")}

## 文字与安全区
文字清晰可读，准确显示并保留登记原文：{('、'.join(locked_texts) or '按 brief/asset_registry') }。
产品、Logo、CTA 和法律声明遵守目标 placement 的官方 safe-zone 模板；不以通用中心网格代替平台遮挡区。

## 负向
不要改包装文字；不要变形 logo；不要改 logo；不要改品牌色；不要乱码；不要出现第三方真实 App UI；不要明星脸；不要医疗/心理疗效暗示；不要让 CTA 或法律声明贴边；不要过快运镜导致 UI/文字抖花。

## 模型提交边界
以上内容是完整生产合同，供继承闸门、广告合规审查、人工复核与溯源使用；不得整段提交给视频模型。视频后端只接收下方编译块的主 prompt，并按后端能力单独接收负向字段。精确 CTA、slogan、价格、法律声明与 UI 文案由后期可控叠加，视频模型只保持首帧已有文字像素稳定。

{render_markdown(compiled)}
"""
    submit_prompt = str(compiled["prompt"])
    job = {
        "job_id": label,
        "clip": label,
        "prompt": f"出视频/分镜/prompt/{label}.md",
        "first_frame": first.relative_to(root).as_posix(),
        "end_frame": end.relative_to(root).as_posix() if end else None,
        "mode": mode,
        "duration": duration,
        "expected_output": expected.relative_to(root).as_posix(),
        "route": {
            "primary": route_item.get("primary"),
            "fallback": route_item.get("fallback") or [],
            "quality_tier": route_item.get("quality_tier"),
        },
        "camera_manifest": CAMERA_MANIFEST_REL,
        "prompt_source_kind": "compiled_submit_prompt",
        "prompt_compiler": {
            key: compiled[key]
            for key in ("kind", "version", "profile_version", "profile", "backend", "mode", "language")
        },
        "submit_prompt": submit_prompt,
        "negative_prompt": compiled["negative_prompt"],
        "source_contract_sha256": compiled["source_contract_sha256"],
        "compiler_source_contract": compiler_source,
        "submit_prompt_sha256": hashlib.sha256(submit_prompt.encode("utf-8")).hexdigest(),
        "submit_prompt_chars": len(submit_prompt),
        "input_frame_sha256": {
            "first": hashlib.sha256(first.read_bytes()).hexdigest() if first.is_file() else None,
            "end": hashlib.sha256(end.read_bytes()).hexdigest() if end and end.is_file() else None,
        },
        "status": "planned",
    }
    return text, job


def plan(root: Path) -> Dict[str, Any]:
    root = root.resolve()
    storyboard = load_json(root / "脚本" / "storyboard.json", {}) or {}
    contract, source = inherit_contract.load_contract(str(root))
    routes = _route_by_clip(root)
    prompt_dir = root / "出视频" / "分镜" / "prompt"
    jobs: List[Dict[str, Any]] = []
    for index, shot in enumerate(_shots(storyboard), 1):
        label = _shot_label(shot, index)
        route_item = routes.get(label, {})
        prompt, job = build_prompt(root, shot, index, contract, route_item)
        prompt_path = prompt_dir / f"{label}.md"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8")
        jobs.append(job)
    manifest = {
        "schema_version": 2,
        "kind": "ad_video_prompt_plan",
        "project_root": str(root),
        "generated_at": now_iso(),
        "contract_source": source,
        "jobs": jobs,
        "summary": {
            "clips": len(jobs),
            "frames2video": sum(1 for j in jobs if j["mode"] == "frames2video"),
            "image2video": sum(1 for j in jobs if j["mode"] == "image2video"),
        },
    }
    write_json(root / "出视频" / "分镜" / "video_jobs_manifest.json", manifest)
    return manifest


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="拍广告出视频 prompt 规划")
    ap.add_argument("project_root")
    ns = ap.parse_args(argv)
    manifest = plan(Path(ns.project_root))
    s = manifest["summary"]
    print(f"# video prompt plan clips={s['clips']} frames2video={s['frames2video']} image2video={s['image2video']}")
    print("  manifest: 出视频/分镜/video_jobs_manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
