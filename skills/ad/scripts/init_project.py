#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拍广告 立项脚手架：在 拍广告/<项目名>/ 下建目录骨架 + _设置.md + _进度.md + _meta.json
+ 需求/brief.json 模板。不拆集（一条主片是整体）；cutdown/多比例交付件登记在 _进度.md。

用法：
    python3 skills/ad/scripts/init_project.py "拍广告/某品牌618" --title 某品牌618秒杀 --brand 某品牌
契约（阶段表/选择点/交付件）来自 ad-craft；本脚本只摆骨架，不写死偏好。
"""
import argparse
import json
import os
import sys

_CRAFT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ad-craft", "scripts"))
if _CRAFT not in sys.path:
    sys.path.insert(0, _CRAFT)
import contract  # noqa: E402

SUBDIRS = [
    "需求", "创意", "脚本", "设定库", "配音",
    "出图/共享", "出图/分镜", "出视频/分镜",
    "合成", "合规", "废料",
]

BRIEF_TEMPLATE = {
    "schema_version": 1,
    "kind": "ad_brief",
    "brand": "",
    "product": "",
    "usp": [],
    "audience": "",
    "tone": "",
    "key_message": "",
    "mandatories": {"logo": "", "slogan": "", "legal_lines": [], "endcard_cta": ""},
    "claims": [],
    "must_avoid": [],
    "deliverables": {"master_duration": "", "aspect": "", "cutdowns": []},
    "platforms": [],
    "deadline": "",
    "rights": {"talent": "", "music": "", "fonts": "", "assets": ""},
}


def main():
    ap = argparse.ArgumentParser(description="拍广告项目立项脚手架")
    ap.add_argument("project_root", help="如 拍广告/某品牌618")
    ap.add_argument("--title", default=None)
    ap.add_argument("--brand", default="")
    ap.add_argument("--master-duration", default=None, help="覆盖默认主片时长")
    ap.add_argument("--aspect", default=None, help="覆盖默认交付比例")
    ap.add_argument("--cutdown-plan", default=None, help="覆盖默认 cutdown 方案")
    # 选择点 = 候选菜单，不是封闭枚举：不绑 argparse choices，保留手输兜底（新后端/别名不被拒）。
    ap.add_argument("--video-model", default=None,
                    metavar="MODEL",
                    help="首跑生视频模型（菜单：%s …；可手输其它）；应由 agent 先问用户再传入"
                         % " / ".join(contract.VIDEO_MODELS[:4]))
    ap.add_argument("--video-channel", default=None,
                    metavar="CHANNEL",
                    help="首跑生视频渠道（菜单：%s …；可手输其它）；应由 agent 先问用户再传入"
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
        "生视频模型": video_model,
        "生视频渠道": video_channel,
    }
    write_if_absent("_设置.md", contract.settings_markdown(title, setting_overrides))
    write_if_absent("_进度.md", contract.progress_markdown(title, deliverables))

    meta = {
        "schema_version": 1, "kind": "ad_project", "title": title, "brand": args.brand,
        "image_backend": contract.DEFAULT_SETTINGS["生图AI"],
        "video_model": video_model,
        "video_channel": video_channel,
        "video_backend": video_channel,
        "adlaw_region": contract.DEFAULT_SETTINGS["广告法地区"],
        "deliverables": deliverables,
    }
    if not os.path.exists(os.path.join(root, "_meta.json")):
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print("[ok] _meta.json")

    brief = dict(BRIEF_TEMPLATE)
    brief["brand"] = args.brand
    brief["deliverables"] = {"master_duration": md, "aspect": aspect,
                             "cutdowns": [d["duration"] for d in deliverables if d["kind"] == "cutdown"]}
    if not os.path.exists(os.path.join(root, "需求", "brief.json")):
        with open(os.path.join(root, "需求", "brief.json"), "w", encoding="utf-8") as f:
            json.dump(brief, f, ensure_ascii=False, indent=2)
        print("[ok] 需求/brief.json（模板，待 AI 据客户需求填充）")

    print(f"\n[done] 立项完成：{root}")
    print("下一步：ad-concept 创意策划。brief 缺的信息由 AI 在其第0步**访谈式补齐**——"
          "必问只有最小集（品牌/产品/卖点/人群），其余推断后请用户确认、合规项可延后；"
          "**不要让用户自己填 brief.json**。")


if __name__ == "__main__":
    main()
