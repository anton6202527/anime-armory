#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拍广告作品**封面** prompt / job 包（付费出封面前的可复跑计划）。

作品卡片需要一张**竖版（9:16 / 5:7）** key visual / endcard 作封面，落 `_meta.json.cover`。
本步骤只产出稳定的封面 prompt + 封面 job manifest + 合规留痕（生产事件），**不渲染 PNG、不伪造产物、
不写 _meta.json.cover**（保持 null）——遵 C4/B4 优雅降级：纯净机（断网/无凭证/无重依赖）也能一路
产出封面 job 包并讲清「该由哪个具体模型、走哪个渠道生成、缺什么」。

真正渲染出竖版 PNG 后，用确定性 helper 回填：
    python3 skills/ad/ad-craft/scripts/meta_card.py cover "<作品根>" --png 出图/封面/cover.png

封面复用三层定妆库的品牌 / hero product 身份锁（品牌色 HEX / logo / 包装文字），与分镜同源、零漂移。
封面「由什么生成」落到具体生图**模型名**（如 GPT Image 2），渠道 / CLI 作为访问入口**分列**（遵 C5）；
逆向 / 未授权出图路径与分镜同禁（遵 ad-image 生图后端治理）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import plan_prompts as pp  # noqa: E402  (同线复用 registry / brand helpers)

_AD_LIB = _HERE.resolve().parents[2] / "_lib"
if str(_AD_LIB) not in sys.path:
    sys.path.insert(0, str(_AD_LIB))
import settings as ad_settings  # noqa: E402


KIND = "ad_cover_prompt_plan"
COVER_DIR = Path("出图") / "封面"
COVER_PROMPT_REL = COVER_DIR / "封面_prompt.md"
COVER_PNG_REL = COVER_DIR / "cover.png"
COVER_JOB_REL = COVER_DIR / "cover_job.json"
COVER_ASPECT = "9:16"  # 竖版；作品卡片按竖版缩略图裁切


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _first_filled(*values: Any) -> str:
    for value in values:
        text = _clean(value)
        if text and text.lower() not in {"待补", "tbd"}:
            return text
    return ""


def load_brief(root: Path) -> Mapping[str, Any]:
    data = pp.load_json(root / "需求" / "brief.json", {})
    return data if isinstance(data, Mapping) else {}


def load_meta(root: Path) -> Mapping[str, Any]:
    data = pp.load_json(root / "_meta.json", {})
    return data if isinstance(data, Mapping) else {}


def cover_concept(root: Path, brief: Mapping[str, Any], meta: Mapping[str, Any]) -> str:
    """封面主张锚：brief.key_message / synopsis / campaign_objective 里第一条有内容的。"""
    return _first_filled(
        brief.get("key_message"),
        meta.get("synopsis"),
        brief.get("campaign_objective"),
    )


def _usp_lines(brief: Mapping[str, Any]) -> str:
    usp = brief.get("usp")
    items = [str(x) for x in usp if _clean(str(x))] if isinstance(usp, (list, tuple)) else []
    return "\n".join(f"- {x}" for x in items) if items else "- （未登记卖点，按 concept KV 收敛）"


def build_cover_prompt(root: Path, brief: Mapping[str, Any], meta: Mapping[str, Any],
                       registry: Mapping[str, Any], model: str, channel: str) -> str:
    brand = pp.brand_entry(registry)
    mandatories = brief.get("mandatories") if isinstance(brief.get("mandatories"), Mapping) else {}
    product_ids = sorted(x for x in pp.flatten_registry_ids(registry) if x.startswith("PROD_"))
    brand_id = str(brand.get("id") or "BRAND_UNKNOWN")
    entries = pp.registry_entry_map(registry)
    refs: List[str] = []
    for aid in ([brand_id] if brand.get("id") else []) + product_ids:
        refs.extend(pp.reference_paths(entries.get(aid, {})))
    refs = list(dict.fromkeys(refs))
    hexes = pp.brand_hexes(registry) or ([brand.get("primary_hex")] if brand.get("primary_hex") else [])
    concept = cover_concept(root, brief, meta)
    endcard_cta = _clean(mandatories.get("endcard_cta")) or _clean(brief.get("offer"))
    slogan = _clean(mandatories.get("slogan")) or _clean(brand.get("slogan"))
    return f"""# 作品封面 出图 prompt（竖版 key visual / endcard）

## 用途
作品卡片封面：一张**竖版 {COVER_ASPECT}**（约 5:7~9:16）静帧 key visual / endcard，落 `_meta.json.cover`。
封面是「一图讲清这条广告在卖什么」的门面，不是分镜首帧；构图为竖版缩略图优化，主体居中偏上，
底部留 CTA / slogan 余量。

## 生成路由（C5：指代落到具体模型）
- 生图模型：{model}
- 生图渠道（访问入口）：{channel}
- 逆向 / 未授权出图路径禁用；非默认官方模型需 `合规/image_backend_override.json` 签核（与分镜同治理）。

## 概念锚（卖点主张）
{concept or '（brief 未填 key_message；封面主张待 concept/brief 补齐后刷新本包）'}

## 卖点
{_usp_lines(brief)}

## 品牌 / 产品身份锁（复用三层定妆库，零漂移）
- 品牌资产：{brand_id} / {_clean(brand.get('name'))}
- 产品资产：{', '.join(product_ids) or '（纯品牌片可无产品资产）'}
- 品牌色严格保持 {', '.join(str(h) for h in hexes if h) or '（登记品牌 HEX）'}；文字标识“{_clean(brand.get('text_logo'))}”清晰可读，不乱码、不变形 logo、不镜像。
- 参考图 / 资产引用：{'; '.join(refs) or '无；有产品/品牌资产时封面必须 image2image 引用真实定妆图，不纯文生图'}
- image2image / 多参考：有 PROD_/BRAND_ 资产时把以上真实图片作为模型图片输入，不能只在 prompt 里声称引用。

## 封面版式
- 画幅：竖版 {COVER_ASPECT}，主体（hero product / 代言人 / KV 主视觉）居中偏上。
- Endcard 元素：slogan「{slogan or '（可选）'}」、CTA「{endcard_cta or '（可选）'}」、logo 最小留白不贴边。
- 关键文字（slogan / CTA / 法律声明）先留竖版中心构图余量，最终位置与合规文案可在 ad-compose 后期叠加锁定。

## 负向
不要改包装文字；不要变形 logo；不要改 logo；不要改品牌色；不要乱码；不要出现第三方真实品牌 / App UI；
不要明星脸；不要医疗 / 心理疗效暗示；不要把 CTA 或 logo 贴边；不要横版构图。
"""


def build_manifest(root: Path, model: str, channel: str, registry: Mapping[str, Any],
                   prompt_sha: str) -> Dict[str, Any]:
    product_ids = sorted(x for x in pp.flatten_registry_ids(registry) if x.startswith("PROD_"))
    brand = pp.brand_entry(registry)
    entries = pp.registry_entry_map(registry)
    brand_id = str(brand.get("id") or "")
    refs: List[str] = []
    for aid in ([brand_id] if brand_id else []) + product_ids:
        refs.extend(pp.reference_paths(entries.get(aid, {})))
    refs = list(dict.fromkeys(refs))
    job = {
        "job_id": "cover",
        "kind": "cover_key_visual",
        "aspect": COVER_ASPECT,
        "orientation": "portrait",
        "prompt": COVER_PROMPT_REL.as_posix(),
        "expected_output": COVER_PNG_REL.as_posix(),
        "requires_assets": ([brand_id] if brand_id else []) + product_ids,
        "reference_inputs": refs,
        "requires_image_input": bool(product_ids),
        "planned_model": model,
        "planned_channel": channel,
        "prompt_sha256": prompt_sha,
        "status": "planned",
    }
    return {
        "schema_version": 1,
        "kind": KIND,
        "project_root": str(root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "image_route": {"model": model, "channel": channel},
        "cover_field": None,
        "job": job,
        "backfill": {
            "helper": "skills/ad/ad-craft/scripts/meta_card.py",
            "command": f'python3 skills/ad/ad-craft/scripts/meta_card.py cover "<作品根>" --png {COVER_PNG_REL.as_posix()}',
            "note": "渲染出竖版 PNG 后运行；helper 确定性回填 _meta.json.cover 为作品根相对路径。",
        },
        "note": "This manifest plans a paid cover render; PNG is not faked and _meta.json.cover stays null until backfill.",
    }


def append_event(root: Path, event: Mapping[str, Any]) -> None:
    path = root / "生产数据" / "production_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def run(root: Path) -> Dict[str, Any]:
    root = root.resolve()
    registry = pp.load_json(root / "设定库" / "asset_registry.json", {}) or {}
    if not registry:
        registry = pp.load_json(root / "出图" / "共享" / "asset_registry.json", {}) or {}
    registry = registry if isinstance(registry, Mapping) else {}
    brief = load_brief(root)
    meta = load_meta(root)

    model = ad_settings.get_setting(str(root), "生图模型", "GPT Image 2")
    channel = ad_settings.get_setting(str(root), "生图渠道", "Codex CLI")

    prompt_path = root / COVER_PROMPT_REL
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_text = build_cover_prompt(root, brief, meta, registry, model, channel)
    prompt_path.write_text(prompt_text.rstrip() + "\n", encoding="utf-8")
    prompt_sha = hashlib.sha256(prompt_path.read_bytes()).hexdigest()

    manifest = build_manifest(root, model, channel, registry, prompt_sha)
    (root / COVER_JOB_REL).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    append_event(root, {
        "ts": manifest["generated_at"],
        "stage": "image",
        "event": "cover_prompt_plan",
        "provider": "local_planner",
        "asset": COVER_JOB_REL.as_posix(),
        "generation": {"provider": "ad-image plan_cover", "method": "prompt_plan",
                       "planned_model": model, "planned_channel": channel},
        "meta": {"aspect": COVER_ASPECT, "requires_image_input": manifest["job"]["requires_image_input"]},
    })
    manifest["_json_path"] = str(root / COVER_JOB_REL)
    return manifest


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="build ad-image cover prompt/job package (portrait key visual)")
    ap.add_argument("project_root")
    args = ap.parse_args(argv)
    payload = run(Path(args.project_root))
    job = payload["job"]
    print(f"# ad-image cover plan model={job['planned_model']} channel={job['planned_channel']} "
          f"aspect={job['aspect']} requires_image_input={job['requires_image_input']}")
    print(f"[ok] {payload['_json_path']}")
    print(f"[next] 渲染竖版 PNG → {COVER_PNG_REL.as_posix()}，再跑："
          f' meta_card.py cover "<作品根>" --png {COVER_PNG_REL.as_posix()} 回填 _meta.json.cover')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
