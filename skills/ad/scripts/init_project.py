#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拍广告 立项脚手架：在 创作区/拍广告/<项目名>/ 下建目录骨架 + _设置.md + _进度.md + _meta.json
+ 需求/brief.json 模板。不拆集（一条主片是整体）；cutdown/多比例交付件登记在 _进度.md。

用法：
    python3 skills/ad/scripts/init_project.py "创作区/拍广告/某品牌618" --title 某品牌618秒杀 --brand 某品牌
契约（阶段表/选择点/交付件）来自 ad-craft；本脚本只摆骨架，不写死偏好。
"""
import argparse
import json
import os
import sys
import uuid
from datetime import date
from pathlib import Path

_CRAFT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ad-craft", "scripts"))
if _CRAFT not in sys.path:
    sys.path.insert(0, _CRAFT)
import contract  # noqa: E402
import locale_matrix  # noqa: E402
import meta_card  # noqa: E402

SUBDIRS = [
    "需求", "创意", "脚本", "设定库", "配音",
    "出图/共享", "出图/分镜", "出视频/分镜",
    "合成", "合规", "生产数据", "投放反馈", "废料",
]

BRIEF_TEMPLATE = {
    "schema_version": 2,
    "kind": "ad_brief",
    "brand": "",
    "product": "",
    "usp": [],
    "audience": "",
    "campaign_objective": "",
    "funnel_stage": "",
    "offer": "",
    "landing_page": "",
    "tone": "",
    "key_message": "",
    "mandatories": {"logo": "", "slogan": "", "legal_lines": [], "endcard_cta": ""},
    "claims": [],
    "must_avoid": [],
    "deliverables": {"master_duration": "", "aspect": "", "cutdowns": []},
    "platforms": [],
    "placements": [],
    "platform_specs": {},
    "placement_specs": {},
    "platform_safe_zone_evidence": {},
    "deliverable_placements": {},
    "release_regions": [],
    "legal_reviews": [],
    "default_locale": "",
    "ai_label_receipts": [],
    "provenance_receipts": [],
    "accessibility": {
        "target_level": "",
        "meaningful_non_speech_audio": False,
        "meaningful_non_speech_events": [],
        "non_speech_captioning_required": False,
        "audio_description_required": False,
        "audio_description": {},
        "media_alternative_required": False,
        "media_alternative": {},
        "caption_exception": {},
    },
    "color_management": {"mode": "sdr_bt709", "conversion_evidence": ""},
    "deadline": "",
    "rights": {
        "talent": {"status": "", "territory": "", "media_scope": "", "approved_by": ""},
        "music": {"status": "", "evidence_file": "", "territory": "", "media_scope": "", "validity": "", "approved_by": ""},
        "fonts": {"status": "", "evidence_file": "", "territory": "", "media_scope": "", "validity": "", "approved_by": ""},
        "assets": {"status": "", "evidence_file": "", "territory": "", "media_scope": "", "validity": "", "approved_by": ""},
    },
    "measurement": {
        "primary_kpi": "",
        "conversion_event": "",
        "attribution_window": "",
        "media_budget": "",
    },
}


def main():
    ap = argparse.ArgumentParser(description="拍广告项目立项脚手架")
    ap.add_argument("project_root", help="如 创作区/拍广告/某品牌618")
    ap.add_argument("--title", default=None)
    ap.add_argument("--brand", default="")
    ap.add_argument("--master-duration", default=None, help="覆盖默认主片时长")
    ap.add_argument("--aspect", default=None, help="覆盖默认交付比例")
    ap.add_argument("--cutdown-plan", default=None, help="覆盖默认 cutdown 方案")
    # 选择点 = 候选菜单，不是封闭枚举：不绑 argparse choices，保留手输兜底（新后端/别名不被拒）。
    ap.add_argument("--video-model", default=None,
                    metavar="MODEL",
                    help="可选：固定/覆盖生视频模型（菜单：%s …；可手输其它）；默认不在立项时强问"
                         % " / ".join(contract.VIDEO_MODELS[:4]))
    ap.add_argument("--video-channel", default=None,
                    metavar="CHANNEL",
                    help="可选：固定/覆盖生视频渠道（菜单：%s …；可手输其它）；默认由路由/探测决定"
                         % " / ".join(contract.VIDEO_CHANNELS_MENU[:4]))
    ap.add_argument("--video-backend", default=None,
                    metavar="CHANNEL",
                    help="兼容旧参数：等同于 --video-channel")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    title = args.title or os.path.basename(root)
    os.makedirs(root, exist_ok=True)
    for d in SUBDIRS:
        os.makedirs(os.path.join(root, d), exist_ok=True)

    md = args.master_duration or contract.DEFAULT_SETTINGS["主片时长"]
    aspect = args.aspect or contract.DEFAULT_SETTINGS["交付比例"]
    plan = args.cutdown_plan or contract.DEFAULT_SETTINGS["cutdown版本"]
    video_model = args.video_model or contract.DEFAULT_SETTINGS["生视频模型"]
    video_channel = args.video_channel or args.video_backend or contract.DEFAULT_SETTINGS["生视频渠道"]
    deliverables = contract.default_deliverables(md, aspect, plan)

    def write_if_absent(rel, content):
        path = os.path.join(root, rel)
        if os.path.exists(path):
            print(f"[skip] 已存在：{rel}")
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[ok] {rel}")

    setting_overrides = {
        "主片时长": md,
        "交付比例": aspect,
        "cutdown版本": plan,
        "生图模型": contract.DEFAULT_SETTINGS["生图模型"],
        "生图渠道": contract.DEFAULT_SETTINGS["生图渠道"],
        "生视频模型": video_model,
        "生视频渠道": video_channel,
        "广告目标": contract.DEFAULT_SETTINGS["广告目标"],
        "漏斗阶段": contract.DEFAULT_SETTINGS["漏斗阶段"],
    }
    write_if_absent("_设置.md", contract.settings_markdown(title, setting_overrides))
    write_if_absent("_进度.md", contract.progress_markdown(title, deliverables))

    meta = {
        "schema_version": 1, "kind": "ad_project", "project_id": f"ad_{uuid.uuid4().hex[:16]}",
        "line": "ad", "title": title, "brand": args.brand,
        # 作品卡片字段：synopsis 立项先用默认广告目标占位，brief 产出后由
        # meta_card.backfill_synopsis 确定性回填 key_message；cover 出封面 PNG 前保持 null。
        "synopsis": meta_card.initial_synopsis(contract.DEFAULT_SETTINGS["广告目标"]),
        "cover": None,
        "image_model": contract.DEFAULT_SETTINGS["生图模型"],
        "image_channel": contract.DEFAULT_SETTINGS["生图渠道"],
        "video_model": video_model,
        "video_channel": video_channel,
        "video_backend": video_channel,
        "adlaw_region": contract.DEFAULT_SETTINGS["广告法地区"],
        "deliverables": deliverables,
    }
    meta_path = os.path.join(root, "_meta.json")
    if not os.path.exists(meta_path):
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print("[ok] _meta.json")
    else:
        try:
            with open(meta_path, encoding="utf-8") as f:
                existing_meta = json.load(f)
            if isinstance(existing_meta, dict):
                meta = existing_meta
        except (OSError, json.JSONDecodeError):
            pass

    catalog_path = os.path.join(root, "生产数据", "artifact_catalog.json")
    if not os.path.exists(catalog_path) and meta.get("project_id") and meta.get("line") == "ad":
        with open(catalog_path, "w", encoding="utf-8") as f:
            json.dump({
                "schema_version": 1, "kind": "artifact_catalog", "status": "bootstrap",
                "generated_at": date.today().isoformat(),
                "project": {"project_id": meta["project_id"], "line": "ad", "title": title, "root_rel": "."},
                "summary": {"artifact_count": 0, "total_bytes": 0, "disposable_bytes": 0, "invalid_count": 0},
                "event_sources": [], "view_sources": [], "artifacts": [], "duplicates": [],
            }, f, ensure_ascii=False, indent=2)
        print("[ok] 生产数据/artifact_catalog.json（bootstrap，可重建）")
    elif not os.path.exists(catalog_path):
        print("[skip] 旧项目缺 project_id/line；先用 tools/artifact-catalog migrate 补身份与 catalog")

    brief = dict(BRIEF_TEMPLATE)
    brief["brand"] = args.brand
    brief["campaign_objective"] = contract.DEFAULT_SETTINGS["广告目标"]
    brief["funnel_stage"] = contract.DEFAULT_SETTINGS["漏斗阶段"]
    brief["deliverables"] = {"master_duration": md, "aspect": aspect,
                             "cutdowns": [d["duration"] for d in deliverables if d["kind"] == "cutdown"]}
    if not os.path.exists(os.path.join(root, "需求", "brief.json")):
        with open(os.path.join(root, "需求", "brief.json"), "w", encoding="utf-8") as f:
            json.dump(brief, f, ensure_ascii=False, indent=2)
        print("[ok] 需求/brief.json（模板，待 AI 据客户需求填充）")

    locale_path = os.path.join(root, "合规", "locale_matrix.json")
    if not os.path.exists(locale_path):
        locale_payload = locale_matrix.template(
            Path(root), [row["deliverable_id"] for row in deliverables])
        with open(locale_path, "w", encoding="utf-8") as f:
            json.dump(locale_payload, f, ensure_ascii=False, indent=2)
        print("[ok] 合规/locale_matrix.json（pending 模板，发布前补具名语言/排版复核）")

    print(f"\n[done] 立项完成：{root}")
    print("下一步：ad-concept 创意策划。brief 缺的信息由 AI 在其第0步**访谈式补齐**——"
          "必问只有最小集（品牌/产品/卖点/人群），其余推断后请用户确认、合规项可延后；"
          "**不要让用户自己填 brief.json**。")


if __name__ == "__main__":
    main()
