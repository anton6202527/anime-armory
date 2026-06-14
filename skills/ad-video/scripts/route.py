#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拍广告 出视频·模型路由（工程化镜型→后端）。

把 SKILL.md / references/platforms.md 里的「镜头类型→模型」prose 表落成可机检的路由产物：
读 `storyboard.json` 的镜型（产品展示/情绪/demo手持/痛点/空镜/endcard…），**按能力分类**
（主体一致性强 / 电影感 / 真实运动 / 通用 / 静帧）路由 primary/fallback，
而**不是**对后端品牌字串做分支判断——后端按能力档登记，换厂只改能力档表，不改判型逻辑。

产物：`出视频/分镜/prompt/video_model_routes.json`，逐镜 {primary, fallback, reason}
+ 单 Clip 时长上限校验（chosen primary 的 per-backend 时长上限按 platforms.md 文档化，
镜头时长超 primary 上限 → block；接近上限 → warn）。

镜像 n2d-model-router 的精神（能力驱动、稳定可 gate），但自包含纯标准库，
不 import n2d-* / mv-* / ad-craft。

用法：
    python3 route.py <作品根> [--json 出视频/分镜/prompt/video_model_routes.json]
"""
import argparse
import json
import os
import re
import sys

VIDEO_MODEL_ROUTES_KIND = "ad_video_model_routes"

# ── 能力档（单一真值源·与 platforms.md 同步） ─────────────────────────────────
# 后端按「能力 + 单 Clip 时长上限(秒)」登记，路由按能力选后端，不对品牌字串分支。
# 时长上限源：references/platforms.md「单 Clip 时长上限按后端」（即梦≤8 / Seedance≤15 / 可灵≈10 / Veo≈8）。
CAP_SUBJECT_LOCK = "subject_consistency"   # 主体一致性强（产品/logo 不抖花、代言人脸稳）
CAP_CINEMATIC = "cinematic"                # 电影感（表演/质感）
CAP_REALISTIC_MOTION = "realistic_motion"  # 真实运动（拟真手持、自然动态）
CAP_GENERAL = "general"                    # 通用叙事
CAP_STILL = "still"                        # 静帧 / 极慢运镜（文字/logo 要稳）

BACKEND_PROFILES = {
    "seedance": {"label": "Seedance", "max_seconds": 15.0,
                 "caps": [CAP_SUBJECT_LOCK, CAP_REALISTIC_MOTION, CAP_GENERAL, CAP_STILL]},
    "kling":    {"label": "可灵Kling", "max_seconds": 10.0,
                 "caps": [CAP_SUBJECT_LOCK, CAP_CINEMATIC, CAP_GENERAL, CAP_STILL]},
    "veo":      {"label": "Veo", "max_seconds": 8.0,
                 "caps": [CAP_CINEMATIC, CAP_GENERAL, CAP_STILL]},
    "dreamina": {"label": "即梦", "max_seconds": 8.0,
                 "caps": [CAP_GENERAL, CAP_REALISTIC_MOTION, CAP_STILL]},
}
DEFAULT_GENERAL_BACKEND = "dreamina"  # 普通镜/兜底默认（platforms.md：模型只作默认/普通镜兜底）

# 后端名归一（中英别名 → key），换厂只改这里 + BACKEND_PROFILES。
_BACKEND_ALIASES = {
    "seedance": "seedance", "即梦seedance": "seedance", "豆包seedance": "seedance",
    "kling": "kling", "可灵": "kling", "快手可灵": "kling",
    "veo": "veo", "google veo": "veo", "gemini": "veo",
    "dreamina": "dreamina", "即梦": "dreamina", "jimeng": "dreamina",
}


def normalize_backend(value, default=DEFAULT_GENERAL_BACKEND):
    key = re.sub(r"[\s/_.-]+", "", str(value or "")).lower()
    if not key:
        return default
    return _BACKEND_ALIASES.get(key, default)


def backend_max_seconds(backend):
    return BACKEND_PROFILES.get(normalize_backend(backend), {}).get("max_seconds", 0.0)


def backends_with_cap(cap):
    """有该能力的后端 key 列表（稳定顺序：按 BACKEND_PROFILES 声明序）。"""
    return [b for b, p in BACKEND_PROFILES.items() if cap in p["caps"]]


# ── 镜型分类（按 storyboard 文本/section/assets，能力优先） ─────────────────────
# 镜型 → 需要的主能力 + reason；判型用关键词，但路由的是能力不是品牌。
SHOT_TYPE_KEYWORDS = [
    ("endcard", ("end card", "endcard", "片尾", "包装定格", "logo+slogan", "logo + slogan", "cta")),
    ("product_hero", ("产品展示", "hero", "环绕", "包装正面", "产品特写", "卖点特写", "product")),
    ("emotion_closeup", ("情绪", "人物特写", "代言人", "表情", "近景特写", "closeup", "close-up")),
    ("demo_handheld", ("demo", "手持", "实拍", "拟真", "开箱", "试用", "handheld")),
    ("empty_transition", ("空镜", "转场", "氛围", "establishing", "transition")),
    ("painpoint_narrative", ("痛点", "情境", "叙事", "钩子", "故事")),
]
SHOT_TYPE_CAP = {
    "product_hero": CAP_SUBJECT_LOCK,
    "emotion_closeup": CAP_CINEMATIC,
    "demo_handheld": CAP_REALISTIC_MOTION,
    "empty_transition": CAP_GENERAL,
    "painpoint_narrative": CAP_GENERAL,
    "endcard": CAP_STILL,
    "general_motion": CAP_GENERAL,
}
SHOT_TYPE_REASON = {
    "product_hero": "产品/包装/logo 不能抖花——路由主体一致性最强后端，首尾双帧锁形态。",
    "emotion_closeup": "情绪/人物特写吃表演与质感——路由电影感后端。",
    "demo_handheld": "demo 实拍/手持要拟真自然动态——路由真实运动后端。",
    "empty_transition": "空镜/转场低身份风险——通用后端即可。",
    "painpoint_narrative": "痛点/叙事普通镜——通用后端即可。",
    "endcard": "end card 文字/logo 要稳——静帧或极慢运镜，必要时 ad-compose 合成。",
    "general_motion": "普通运动镜——用项目默认/通用后端。",
}


def _shot_text(shot):
    parts = []
    for k in ("section", "frame", "label", "title", "shot_id", "desc", "description", "camera", "镜头"):
        v = shot.get(k) if isinstance(shot, dict) else None
        if isinstance(v, str):
            parts.append(v)
    return " ".join(parts)


def classify_shot(shot):
    """storyboard shot → 镜型字符串。endcard 优先（CTA/包装定格命中即定）。纯函数·可测。"""
    text = _shot_text(shot).lower()
    for shot_type, keywords in SHOT_TYPE_KEYWORDS:
        if any(k.lower() in text for k in keywords):
            return shot_type
    return "general_motion"


def shot_prod_ids(shot):
    assets = shot.get("assets") if isinstance(shot, dict) else None
    if not isinstance(assets, dict):
        return set()
    return {k for k, v in assets.items() if k.startswith("PROD_") and v}


def shot_duration(shot):
    for key in ("duration", "时长", "duration_sec", "seconds"):
        raw = shot.get(key) if isinstance(shot, dict) else None
        if raw is None:
            continue
        m = re.search(r"\d+(?:\.\d+)?", str(raw))
        if m:
            return float(m.group(0))
    return 0.0


def choose_route(shot, default_backend=DEFAULT_GENERAL_BACKEND):
    """镜型 → {primary, fallback, reason, capability}。能力优先；产品镜强制主体一致后端。纯函数·可测。

    - 产品镜（product_hero 或绑定 PROD_xx）：必须主体一致后端；
    - 其余：按 SHOT_TYPE_CAP 选有该能力的后端，default_backend 若具备该能力则优先用它。
    - fallback：兜底回退到通用后端 + 即梦，去重去 primary。
    """
    shot_type = classify_shot(shot)
    is_product = shot_type == "product_hero" or bool(shot_prod_ids(shot))
    if is_product:
        cap = CAP_SUBJECT_LOCK
        if shot_type != "product_hero":
            shot_type = "product_hero"
    else:
        cap = SHOT_TYPE_CAP.get(shot_type, CAP_GENERAL)

    candidates = backends_with_cap(cap)
    default_norm = normalize_backend(default_backend)
    # 通用类镜：default 后端若具备该能力则优先（platforms.md：普通镜用项目默认）。
    if cap in (CAP_GENERAL,) and default_norm in candidates:
        primary = default_norm
    elif candidates:
        primary = candidates[0]
    else:
        primary = default_norm

    fallback = []
    for b in candidates + [default_norm, "dreamina"]:
        b = normalize_backend(b)
        if b != primary and b not in fallback:
            fallback.append(b)
    fallback = fallback[:2]
    return {"shot_type": shot_type, "capability": cap, "primary": primary,
            "fallback": fallback, "reason": SHOT_TYPE_REASON.get(shot_type, "")}


def clip_length_cap_check(primary, duration):
    """单 Clip 时长上限校验。duration 超 primary 上限 → block；≥90% 上限 → warn；否则 None。纯函数·可测。"""
    cap = backend_max_seconds(primary)
    if not duration or not cap:
        return None
    label = BACKEND_PROFILES.get(normalize_backend(primary), {}).get("label", primary)
    if duration > cap + 1e-6:
        return {"severity": "block", "code": "clip_too_long_for_backend",
                "msg": f"镜头时长 {duration:.1f}s 超 {label} 单 Clip 上限 {cap:.0f}s——该后端拍不下，"
                       f"改用更长后端(Seedance≤15s)或拆镜/缩时长。"}
    if duration >= cap * 0.9:
        return {"severity": "warn", "code": "clip_near_backend_limit",
                "msg": f"镜头时长 {duration:.1f}s 接近 {label} 上限 {cap:.0f}s——留余量或备拆镜方案。"}
    return None


def _shot_id(shot, index):
    raw = str((shot.get("shot_id") or shot.get("clip_id") or "") if isinstance(shot, dict) else "").strip()
    m = re.search(r"(\d+)", raw)
    if m:
        return f"镜头{int(m.group(1)):02d}"
    return f"镜头{index:02d}"


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _project_default_backend(root):
    """从 _设置.md 读 生视频模型/生视频渠道/生视频AI 当默认；缺则 DEFAULT_GENERAL_BACKEND。纯文本扫描，自包含。"""
    path = os.path.join(root, "_设置.md")
    text = ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    for key in ("生视频模型", "生视频渠道", "生视频AI"):
        m = re.search(rf"{key}\s*[:：]\s*(.+)", text)
        if m:
            val = m.group(1).strip().strip("`*")
            nb = normalize_backend(val, default="")
            if nb:
                return nb
    return DEFAULT_GENERAL_BACKEND


def build_routes(storyboard, default_backend=DEFAULT_GENERAL_BACKEND):
    """storyboard dict → routes 列表 + summary。纯函数·可测。"""
    shots = storyboard.get("shots") or storyboard.get("clips") or []
    routes = []
    for i, shot in enumerate(shots, 1):
        r = choose_route(shot, default_backend)
        duration = shot_duration(shot)
        clip_id = _shot_id(shot, i)
        findings = []
        cap_check = clip_length_cap_check(r["primary"], duration)
        if cap_check:
            cap_check = dict(cap_check, clip=clip_id)
            findings.append(cap_check)
        routes.append({
            "clip": clip_id,
            "shot_type": r["shot_type"],
            "capability": r["capability"],
            "primary": r["primary"],
            "fallback": r["fallback"],
            "max_clip_seconds": backend_max_seconds(r["primary"]),
            "duration": duration,
            "reason": r["reason"],
            "prod_assets": sorted(shot_prod_ids(shot)),
            "findings": findings,
        })
    block = sum(1 for r in routes for f in r["findings"] if f["severity"] == "block")
    warn = sum(1 for r in routes for f in r["findings"] if f["severity"] == "warn")
    return routes, {"block": block, "warn": warn}


def run(root, out_json=None):
    root = os.path.abspath(root)
    sb = load_json(os.path.join(root, "脚本", "storyboard.json"), {}) or {}
    default_backend = _project_default_backend(root)
    routes, summary = build_routes(sb, default_backend)
    payload = {"schema_version": 1, "kind": VIDEO_MODEL_ROUTES_KIND,
               "default_backend": default_backend, "routes": routes, "summary": summary}
    if out_json is None:
        out_json = os.path.join(root, "出视频", "分镜", "prompt", "video_model_routes.json")
    os.makedirs(os.path.dirname(os.path.abspath(out_json)), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    payload["_out_json"] = out_json
    return payload


def main(argv=None):
    ap = argparse.ArgumentParser(description="拍广告出视频·镜型→模型路由（能力驱动）")
    ap.add_argument("project_root")
    ap.add_argument("--json", default=None,
                    help="路由产物路径（默认 出视频/分镜/prompt/video_model_routes.json）")
    args = ap.parse_args(argv)

    payload = run(args.project_root, args.json)
    b, w = payload["summary"]["block"], payload["summary"]["warn"]
    print(f"# 模型路由  默认后端={payload['default_backend']}  clips={len(payload['routes'])}  block={b}  warn={w}")
    for r in payload["routes"]:
        print(f"[{r['clip']}] {r['shot_type']} → primary={r['primary']} "
              f"fallback={','.join(r['fallback']) or '-'}  ({r['reason']})")
        for f in r["findings"]:
            print(("  🔴" if f["severity"] == "block" else "  🟡") + f" {f['msg']}")
    if b == 0:
        print("✅ 路由完成，无时长超限")
    sys.exit(1 if b > 0 else 0)


if __name__ == "__main__":
    main()
