#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build ad-image shared look package and per-shot prompt pack.

This is the deterministic planning step before paid image generation. It writes
the shared product/brand prompt package, the visual overview, per-shot first
frame prompts, optional end-frame prompts for continuity, and an image job
manifest. It does not call an image model and does not fake PNG outputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

_AD_LIB = Path(__file__).resolve().parents[2] / "ad" / "_lib"
if str(_AD_LIB) not in sys.path:
    sys.path.insert(0, str(_AD_LIB))
import settings as ad_settings  # noqa: E402


KIND = "ad_image_prompt_plan"
PROD_RE = re.compile(r"\bPROD_[A-Za-z0-9_]*\b")
BRAND_RE = re.compile(r"\bBRAND_[A-Za-z0-9_]*\b")


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def shots(storyboard: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    raw = storyboard.get("shots") or storyboard.get("clips") or []
    return [s for s in raw if isinstance(s, Mapping)]


def shot_label(shot: Mapping[str, Any], index: int) -> str:
    raw = str(shot.get("shot_id") or shot.get("clip_id") or shot.get("id") or shot.get("clip") or "").strip()
    m = re.search(r"(\d+)", raw)
    if m:
        return f"镜头{int(m.group(1)):02d}"
    return raw or f"镜头{index:02d}"


def shot_text(shot: Mapping[str, Any]) -> str:
    parts = []
    for key in ("scene", "shot", "frame", "prompt", "description", "desc", "product_lock"):
        value = shot.get(key)
        if isinstance(value, str):
            parts.append(value)
    return "\n".join(parts)


def asset_ids(shot: Mapping[str, Any], regex: re.Pattern[str]) -> List[str]:
    ids = set()
    assets = shot.get("assets")
    if isinstance(assets, Mapping):
        ids.update(str(k) for k, v in assets.items() if v and regex.fullmatch(str(k)))
    elif isinstance(assets, Sequence) and not isinstance(assets, (str, bytes)):
        ids.update(str(v) for v in assets if regex.fullmatch(str(v)))
    ids.update(regex.findall(shot_text(shot)))
    return sorted(ids)


def flatten_registry_ids(registry: Any) -> set[str]:
    ids: set[str] = set()
    if isinstance(registry, Mapping):
        raw_id = str(registry.get("id") or registry.get("asset_id") or "").strip()
        if raw_id:
            ids.add(raw_id)
        for key, value in registry.items():
            if isinstance(key, str) and (key.startswith("PROD_") or key.startswith("BRAND_")):
                ids.add(key)
            ids.update(flatten_registry_ids(value))
    elif isinstance(registry, list):
        for value in registry:
            ids.update(flatten_registry_ids(value))
    return ids


def product_entries(registry: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    raw = registry.get("products") or []
    return [p for p in raw if isinstance(p, Mapping)]


def registry_entry_map(registry: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    out: Dict[str, Mapping[str, Any]] = {}
    brand = brand_entry(registry)
    if brand.get("id"):
        out[str(brand["id"])] = brand
    for product in product_entries(registry):
        if product.get("id"):
            out[str(product["id"])] = product
    for key in ("characters", "locations", "assets"):
        for item in registry.get(key) or []:
            if isinstance(item, Mapping) and item.get("id"):
                out[str(item["id"])] = item
    return out


def reference_paths(entry: Mapping[str, Any]) -> List[str]:
    raw = entry.get("reference_images") or entry.get("references") or entry.get("reference_paths") or []
    if isinstance(raw, str):
        raw = [raw]
    out = []
    for item in raw if isinstance(raw, Sequence) else []:
        value = item.get("path") if isinstance(item, Mapping) else item
        if value and str(value) not in out:
            out.append(str(value))
    return out


def brand_entry(registry: Mapping[str, Any]) -> Mapping[str, Any]:
    raw = registry.get("brand")
    return raw if isinstance(raw, Mapping) else {}


def brand_hexes(registry: Mapping[str, Any]) -> List[str]:
    brand = brand_entry(registry)
    values = [
        brand.get("primary_hex"),
        brand.get("accent_hex"),
        brand.get("background_hex"),
    ]
    for product in product_entries(registry):
        values.extend(product.get("brand_hexes") or [])
    return [str(v) for v in values if isinstance(v, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", v)]


def safe_area_text(safe: Any) -> str:
    if not isinstance(safe, Mapping) or not safe:
        return "8x8 grid; keep product/logo/CTA/legal text inside center 6x6; core product in center 4x4"
    return "; ".join(f"{k}={v}" for k, v in safe.items())


def continuity(shot: Mapping[str, Any]) -> Mapping[str, Any]:
    raw = shot.get("continuity")
    return raw if isinstance(raw, Mapping) else {}


def needs_end_frame(shot: Mapping[str, Any]) -> bool:
    cont = continuity(shot)
    return bool(shot.get("need_end_frame") or shot.get("end_frame") or cont.get("need_end_frame"))


def build_shared_registry(root: Path, registry: Mapping[str, Any]) -> None:
    out = root / "出图" / "共享" / "asset_registry.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_brand_prompt(registry: Mapping[str, Any]) -> str:
    brand = brand_entry(registry)
    return f"""# {brand.get('id', 'BRAND_UNKNOWN')} 品牌定妆 prompt

资产身份注册：{brand.get('id', 'BRAND_UNKNOWN')}
品牌名称：{brand.get('name', '')}
文字标识：{brand.get('text_logo', '')}
Slogan：{brand.get('slogan', '')}
品牌主色：{brand.get('primary_hex', '')}
辅助色：{brand.get('accent_hex', '')}
背景色：{brand.get('background_hex', '')}

视觉要求：
- text logo 必须清晰可读，不乱码，不变形 logo，不镜像。
- color consistency: strict HEX {brand.get('primary_hex', '')}
- Logo 保持最小留白，不贴边，不被反光、手指、通知卡片遮挡。
- 片尾或 CTA 镜先保留中心构图余量；最终位置须按目标 placement 当前官方/客户模板复核。

负向：
- 不要改 logo 字形，不要变形 logo，不要改品牌色，不要乱码，不要出现第三方真实品牌。
"""


def build_product_prompt(product: Mapping[str, Any], brand: Mapping[str, Any]) -> str:
    ui_states = product.get("ui_states") if isinstance(product.get("ui_states"), list) else []
    ui_lines = []
    for state in ui_states:
        if not isinstance(state, Mapping):
            continue
        locked = "、".join(str(x) for x in (state.get("locked_text") or []))
        ui_lines.append(f"- {state.get('state_id')}: {state.get('screen_title')} | locked_text={locked} | {state.get('usage')}")
    locks = product.get("prompt_locks") or []
    return f"""# {product.get('id')} 产品/App 定妆 prompt

资产身份注册：{product.get('id')}
品牌资产：{product.get('brand_id') or brand.get('id')}
产品名称：{product.get('name')}
产品类型：{product.get('type')}
参考图/资产引用：本 prompt 生成的定妆图作为 image2image / 多参考母图，后续所有产品镜必须引用 {product.get('id')}。

Hero surfaces：
{chr(10).join('- ' + str(x) for x in (product.get('hero_surfaces') or []))}

UI states：
{chr(10).join(ui_lines) if ui_lines else '- 未登记 UI state'}

身份锁定句：
- 与产品参考图①同一款 App UI、同一 logo、同一品牌色、同一文字标识“{brand.get('text_logo', '')}”。
- 品牌色严格保持 {brand.get('primary_hex', '')}，辅助色 {brand.get('accent_hex', '')}，文字清晰可读，不乱码。

Prompt locks：
{chr(10).join('- ' + str(x) for x in locks)}

安全框：
- {safe_area_text(product.get('safe_area'))}

负向：
- 不要改包装文字，不要变形 logo，不要改 logo，不要改品牌色，不要乱码，不要出现第三方真实 App UI。
"""


def build_overview(root: Path, registry: Mapping[str, Any], storyboard: Mapping[str, Any]) -> str:
    brand = brand_entry(registry)
    style = read_text(root / "设定库" / "global_style.md")
    deliverables = load_json(root / "生产数据" / "platform_pack.json", {}) or {}
    brand_id = str(brand.get("id") or "BRAND_UNKNOWN")
    product_ids = sorted(x for x in flatten_registry_ids(registry) if x.startswith("PROD_"))
    return f"""# ad-image 视觉一致性契约总览

项目：{root.name}
画幅：{storyboard.get('aspect') or '按项目交付比例'}
品牌资产：{brand.get('id', '')} / {brand.get('name', '')}
品牌色：{', '.join(brand_hexes(registry)) or brand.get('primary_hex', '')}
产品资产：{', '.join(sorted(x for x in flatten_registry_ids(registry) if x.startswith('PROD_')))}
平台规格：{', '.join(deliverables.get('platforms') or []) if isinstance(deliverables, Mapping) else ''}

## 全局风格

{style.strip()}

## 出图硬约束

- 所有产品/App/UI 镜必须引用对应 PROD_*；品牌/片尾镜必须引用 {brand_id}。
- 当前产品资产：{', '.join(product_ids) or '未登记'}。
- 参考图/资产引用必须走共享定妆包，不做纯文生图产品。
- 身份锁定句必须包含：同一款 App UI、同一 logo、同一品牌色。
- 负向必须包含：不要改包装文字、不要变形 logo、不要乱码。
- UI/CTA/法律声明必须文字清晰可读，最终关键文字可在 ad-compose 后期叠加锁定。
- 跨比例构图余量（内部启发式）：8x8 grid，产品重心 center 4x4，文字/CTA/legal center 6x6；不等于平台 placement 安全区。
"""


def frame_prompt(label: str, shot: Mapping[str, Any], registry: Mapping[str, Any], *, end_frame: bool = False) -> str:
    brand = brand_entry(registry)
    product_ids = asset_ids(shot, PROD_RE)
    brand_ids = asset_ids(shot, BRAND_RE)
    if product_ids and not brand_ids and brand.get("id"):
        brand_ids = [str(brand["id"])]
    entries = registry_entry_map(registry)
    refs = []
    for aid in product_ids + brand_ids:
        refs.extend(reference_paths(entries.get(aid, {})))
    refs = list(dict.fromkeys(refs))
    cont = continuity(shot)
    suffix = "尾帧" if end_frame else "首帧"
    end_note = cont.get("transition") or "保持可与下一镜自然接力"
    return f"""# {label} {suffix} 出图 prompt

## 镜头信息
- 场景：{shot.get('scene', '')}
- 镜头：{shot.get('shot') or shot.get('frame') or ''}
- 时长：{shot.get('duration') or shot.get('duration_sec') or ''}s
- 类型：{'end_frame continuity handoff' if end_frame else 'first_frame'}
- 安全框：{safe_area_text(shot.get('safe_area'))}

## 资产身份注册
- 产品资产：{', '.join(product_ids)}
- 品牌资产：{', '.join(brand_ids)}
- 参考图/资产引用：{'; '.join(refs) or '无；产品镜在正式生成前必须补 registry.reference_images'}
- image2image / 多参考：产品镜必须把以上真实图片作为模型图片输入；不能只在 prompt 里声称引用。

## 画面 prompt
{shot.get('prompt') or shot_text(shot)}

## 身份锁定句
与登记产品参考图同一结构、同一 logo、同一品牌色 {brand.get('primary_hex', '')}；同一文字标识“{brand.get('text_logo', '')}”；登记文案清晰可读，不乱码。

## 产品/品牌锁
{shot.get('product_lock') or '保持产品和品牌资产一致。'}

## 文字锁
文字清晰可读，准确显示并保留原文；CTA、slogan、法律声明先留中心构图余量，并按目标 placement 模板避让，不乱码。

## 构图与光位
严格继承 storyboard 的画幅、构图、光位、场景与风格；按目标 placement 的官方安全区模板留出 UI overlay 避让，给图生视频保留运动余量。

## 尾帧接力
need_end_frame：{str(needs_end_frame(shot)).lower()}
transition：{end_note}
{('本尾帧应作为下一镜首帧接力构图，动作不在峰值，保留运镜余量。' if end_frame else '首帧为起幅，不放在动作峰值，为图生视频留运镜余量。')}

## 负向
不要改包装文字；不要变形 logo；不要改 logo；不要改品牌色；不要乱码；不要出现第三方真实 App UI；不要明星脸；不要医疗/心理疗效暗示；不要把 CTA 或法律声明贴边。
"""


def build_jobs(root: Path, storyboard: Mapping[str, Any]) -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []
    registry = load_json(root / "出图" / "共享" / "asset_registry.json", {}) or load_json(root / "设定库" / "asset_registry.json", {}) or {}
    entries = registry_entry_map(registry)
    for index, shot in enumerate(shots(storyboard), start=1):
        label = shot_label(shot, index)
        required = asset_ids(shot, PROD_RE) + asset_ids(shot, BRAND_RE)
        refs = list(dict.fromkeys(path for aid in required for path in reference_paths(entries.get(aid, {}))))
        jobs.append({
            "job_id": f"{label}_first",
            "shot": label,
            "kind": "first_frame",
            "prompt": f"出图/分镜/prompt/{label}.md",
            "expected_output": f"出图/分镜/图片/{label}.png",
            "requires_assets": required,
            "reference_inputs": refs,
            "requires_image_input": bool(asset_ids(shot, PROD_RE)),
            "status": "planned",
        })
        if needs_end_frame(shot):
            jobs.append({
                "job_id": f"{label}_end",
                "shot": label,
                "kind": "end_frame",
                "prompt": f"出图/分镜/prompt/{label}_end.md",
                "expected_output": f"出图/分镜/图片/{label}_end.png",
                "requires_assets": required,
                "reference_inputs": refs,
                "requires_image_input": bool(asset_ids(shot, PROD_RE)),
                "status": "planned",
            })
    return jobs


def append_event(root: Path, event: Mapping[str, Any]) -> None:
    path = root / "生产数据" / "production_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def run(root: Path) -> Dict[str, Any]:
    root = root.resolve()
    storyboard = load_json(root / "脚本" / "storyboard.json", {}) or {}
    registry = load_json(root / "设定库" / "asset_registry.json", {}) or {}
    if not registry:
        registry = load_json(root / "出图" / "共享" / "asset_registry.json", {}) or {}
    if not storyboard:
        raise SystemExit("缺 脚本/storyboard.json")
    if not registry:
        raise SystemExit("缺 设定库/asset_registry.json 或 出图/共享/asset_registry.json")

    shared_prompt_dir = root / "出图" / "共享" / "prompt"
    shot_prompt_dir = root / "出图" / "分镜" / "prompt"
    image_dir = root / "出图" / "分镜" / "图片"
    image_dir.mkdir(parents=True, exist_ok=True)
    build_shared_registry(root, registry)

    brand = brand_entry(registry)
    write_text(shared_prompt_dir / f"品牌_{brand.get('id', 'BRAND')}.md", build_brand_prompt(registry))
    for product in product_entries(registry):
        write_text(shared_prompt_dir / f"产品_{product.get('id', 'PROD')}.md", build_product_prompt(product, brand))
    write_text(shot_prompt_dir / "00_总览.md", build_overview(root, registry, storyboard))

    for index, shot in enumerate(shots(storyboard), start=1):
        label = shot_label(shot, index)
        write_text(shot_prompt_dir / f"{label}.md", frame_prompt(label, shot, registry, end_frame=False))
        if needs_end_frame(shot):
            write_text(shot_prompt_dir / f"{label}_end.md", frame_prompt(label, shot, registry, end_frame=True))

    jobs = build_jobs(root, storyboard)
    image_model = ad_settings.get_setting(str(root), "生图模型", "GPT Image 2")
    image_channel = ad_settings.get_setting(str(root), "生图渠道", "Codex CLI")
    for job in jobs:
        job["planned_model"] = image_model
        job["planned_channel"] = image_channel
        prompt_path = root / str(job["prompt"])
        job["prompt_sha256"] = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    manifest = {
        "schema_version": 1,
        "kind": KIND,
        "project_root": str(root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "shared_prompts": [
            str(p.relative_to(root)) for p in sorted(shared_prompt_dir.glob("*.md"))
        ],
        "overview": "出图/分镜/prompt/00_总览.md",
        "image_route": {"model": image_model, "channel": image_channel},
        "jobs": jobs,
        "summary": {
            "first_frames": sum(1 for j in jobs if j["kind"] == "first_frame"),
            "end_frames": sum(1 for j in jobs if j["kind"] == "end_frame"),
            "planned": len(jobs),
        },
        "note": "This manifest plans paid image generation; PNG files are not faked by this script.",
    }
    out = root / "出图" / "分镜" / "image_jobs_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    append_event(root, {
        "ts": manifest["generated_at"],
        "stage": "image",
        "event": "prompt_plan",
        "provider": "local_planner",
        "asset": "出图/分镜/image_jobs_manifest.json",
        "generation": {"provider": "ad-image plan_prompts", "method": "prompt_plan"},
        "meta": {"jobs": len(jobs), "first_frames": manifest["summary"]["first_frames"], "end_frames": manifest["summary"]["end_frames"]},
    })
    manifest["_json_path"] = str(out)
    return manifest


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="build ad-image prompt package")
    ap.add_argument("project_root")
    args = ap.parse_args(argv)
    payload = run(Path(args.project_root))
    s = payload["summary"]
    print(f"# ad-image prompt plan first={s['first_frames']} end={s['end_frames']} planned={s['planned']}")
    print(f"[ok] {payload['_json_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
