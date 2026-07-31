#!/usr/bin/env python3
"""cover_pack.py — n2d 作品级封面（作品卡片封面）prompt/job 生产包。

作品卡片要展示一张竖版封面，路径固化在作品根 `_meta.json` 的 `cover` 字段。
本步骤是**无成本 writer**：它只产出稳定的封面 prompt 包 + 机器可执行 job 包 +
合规留痕；**不生成 PNG、不调用任何生图后端**。真正渲染出竖版 PNG 后，用
`--backfill-cover` 确定性把 `_meta.json` 的 `cover` 回填为作品根相对路径。

设计遵守：
- C4/B4 优雅降级：纯净机（断网、无凭证、无重依赖）上仍产 prompt/job 包 + 留痕，
  `cover` 保持 null，绝不硬阻断主流程。
- C5 生成者落到具体模型：job 里 `生图模型` 写具体模型名（含版本），`生图渠道` /
  `访问入口` 作为 access path 分列，不把渠道壳当生成者。
- B7/B9 身份锚：封面若含具名角色，必须绑定 `identity_registry` 的
  `CHAR_xx/形态` + `reference_group` 同源锚；脸锚未 ready 时只标 render 前置缺口
  （交由既有出图 runner 在真正生成前强制补齐），本 writer 不硬阻断。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)

from image_backend_adapter import current_image_backend_selection  # noqa: E402
from work_card_meta import (  # noqa: E402
    DEFAULT_COVER_REL,
    backfill_cover,
    load_meta,
    read_synopsis_candidate,
)

KIND = "n2d_work_cover_job_pack"
VERSION = 1
COVER_DIR_REL = "出图/封面"
IDENTITY_REGISTRY_REL = "出图/共享/identity_registry.json"
STYLE_CONTRACT_REL = "设定库/global_style.md"

# 竖版比例：卡片封面契约要求 9:16 / 约 5:7 竖图。
COVER_ASPECT = "9:16"
COVER_ASPECT_ALT = "5:7"


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def recipe_hash(payload: Mapping[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]


def _anchor_is_ready(node: Any, root: Path) -> Tuple[bool, str, str]:
    """判断 reference_group.front 是否为可注入的 ready 脸锚（状态 ready + PNG 真实存在）。"""
    if not isinstance(node, Mapping):
        return False, "", ""
    path = str(node.get("path") or "").strip()
    status = str(node.get("status") or "").strip().lower()
    sha = str(node.get("sha256") or "")
    ready = status in {"", "ready", "registered", "pass", "ok", "accepted"}
    exists = bool(path) and (root / path).is_file() if path else False
    return (ready and exists), path, sha


def pick_cover_subject(root: Path) -> Dict[str, Any]:
    """选封面主角：优先 core_full / 核心长线角色的主形态；绑定同源脸锚（B7/B9）。

    返回一个 identity binding；无 identity_registry 或无角色时返回空 dict（纯风景/
    标题式封面，合法降级）。
    """
    data = load_json(root / IDENTITY_REGISTRY_REL)
    chars = data.get("characters") if isinstance(data, Mapping) else None
    if not isinstance(chars, list):
        return {}

    def rank(ch: Mapping[str, Any]) -> Tuple[int, int]:
        tier = str(ch.get("library_tier") or "")
        scope = str(ch.get("tier") or "") + str(ch.get("scope") or "")
        core = 0 if tier == "core_full" or "核心" in scope or "主角" in scope else 1
        planned = -int(ch.get("planned_episode_count") or 0)
        return core, planned

    ordered = sorted(
        [c for c in chars if isinstance(c, Mapping) and c.get("id")],
        key=rank,
    )
    if not ordered:
        return {}
    ch = ordered[0]
    forms = ch.get("forms") if isinstance(ch.get("forms"), list) else []
    form = forms[0] if forms and isinstance(forms[0], Mapping) else {}
    rg = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
    front = rg.get("front") if isinstance(rg, Mapping) else {}
    ready, anchor_path, anchor_sha = _anchor_is_ready(front, root)
    form_name = str(form.get("form") or "常态")
    return {
        "character_id": str(ch.get("id")),
        "form": form_name,
        "carries_identity": f"{ch.get('id')}/{form_name}",
        "name": str(ch.get("name") or ""),
        "anchor_phrase": str(form.get("anchor_phrase") or ""),
        "reference_group_ref": f"{IDENTITY_REGISTRY_REL}#characters[{ch.get('id')}]/forms/{form_name}/reference_group",
        "face_anchor_path": anchor_path,
        "face_anchor_sha256": anchor_sha,
        "face_anchor_ready": bool(ready),
        "drift_forbidden": form.get("drift_forbidden") or [],
    }


def _first_episode_cover_ref(root: Path) -> str:
    """复用已有的 `脚本/第N集/封面.md` 封面策略作为文案基底（取首个存在的）。"""
    script_dir = root / "脚本"
    if not script_dir.is_dir():
        return ""
    for ep in sorted(p.name for p in script_dir.iterdir() if p.is_dir()):
        cover_md = script_dir / ep / "封面.md"
        if cover_md.is_file():
            return f"脚本/{ep}/封面.md"
    return ""


def build_prompt(root: Path, meta: Mapping[str, Any], subject: Mapping[str, Any],
                 selection: Mapping[str, Any]) -> Dict[str, str]:
    title = str(meta.get("title") or root.name)
    synopsis = str(meta.get("synopsis") or "").strip() or read_synopsis_candidate(root)
    hook = synopsis or "本剧最大爽点/钩子"
    face_zh = ""
    face_en = ""
    if subject:
        anchor = subject.get("anchor_phrase") or subject.get("name")
        face_zh = f"主角 {subject.get('name') or subject.get('character_id')}（{subject.get('carries_identity')}）清晰正脸、强情绪，脸型/眼距/发型/服装配色严格同源锚：{anchor}。"
        face_en = "Protagonist clear frontal face, strong emotion, identity locked to the registered face anchor (same face/hair/wardrobe)."
    zh = (
        f"竖版作品封面（{COVER_ASPECT}，可接受 {COVER_ASPECT_ALT}），高点击率短剧封面。"
        f"{face_zh}"
        f"画面承载本剧核心卖点：{hook}。"
        "构图为标题预留上/下安全留白，主体不顶格；电影级布光、强对比、情绪张力拉满。"
        "严禁任何文字、字幕、水印、Logo、平台角标（标题由排版层后叠）。"
        "继承本剧 style_contract / identity_registry / asset_registry 视觉锚，不得漂移。"
    )
    en = (
        f"Vertical key-visual cover ({COVER_ASPECT}, {COVER_ASPECT_ALT} acceptable), high-CTR short-drama poster. "
        f"{face_en}"
        f"Carries the show's core hook: {hook}. "
        "Leave title-safe margins top/bottom, cinematic lighting, high contrast, strong emotion. "
        "No text, no subtitles, no watermark, no logo, no platform badge. "
        "Inherit the show's style_contract / identity anchors; no drift."
    )
    return {"zh": zh, "en": en}


def build_pack(root: Path) -> Dict[str, Any]:
    meta = load_meta(root)
    subject = pick_cover_subject(root)
    selection = current_image_backend_selection(root)
    prompt = build_prompt(root, meta, subject, selection)

    identity_bindings: List[Dict[str, Any]] = []
    render_blocking: List[str] = []
    if subject:
        identity_bindings.append(subject)
        # B9：脸锚未 ready 时，真正渲染前必须先补共享脸锚；这里只标缺口，不硬阻断本 writer。
        if not subject.get("face_anchor_ready"):
            render_blocking.append("missing_ready_face_anchor")

    model = str(selection.get("image_model") or selection.get("adapter_model") or "").strip()
    recipe = {
        "prompt": prompt,
        "subject": subject.get("carries_identity") if subject else None,
        "model": model,
        "channel": selection.get("channel"),
    }
    pack: Dict[str, Any] = {
        "kind": KIND,
        "version": VERSION,
        "title": str(meta.get("title") or root.name),
        "orientation": "portrait",
        "aspect_ratio": COVER_ASPECT,
        "aspect_ratio_alt": COVER_ASPECT_ALT,
        # C5：生成者=具体模型；渠道/访问入口作为 access path 分列。
        "生图模型": model,
        "生图渠道": str(selection.get("channel") or ""),
        "访问入口": str(selection.get("access") or ""),
        "backend": str(selection.get("backend") or ""),
        "persistent_subject": bool(selection.get("persistent_subject")),
        "prompt": prompt,
        "negative": "文字/字幕/水印/Logo/角标/多余肢体/崩脸/串脸/风格漂移",
        "identity_bindings": identity_bindings,
        "cover_strategy_ref": _first_episode_cover_ref(root),
        "style_contract_ref": STYLE_CONTRACT_REL,
        "qc_required": [
            "portrait_9_16",
            "protagonist_face_clear",
            "identity_match",
            "no_text_no_logo",
            "title_safe_area",
        ],
        "output_path": f"{COVER_DIR_REL}/cover.png",
        "cover_meta_field": meta.get("cover"),
        "render_blocking": render_blocking,
        "compliance": {
            "degraded_no_backend_call": True,
            "note": (
                "无成本 writer：本包只产 prompt/job + 留痕，未生成 PNG、未调后端。"
                "在装好生图后端/凭证的机器上，用既有 n2d 出图 runner 按本包 prompt 渲染竖版封面；"
                "渲染并人审通过后跑 `cover_pack.py <root> --backfill-cover` 回填 _meta.json 的 cover。"
                "_meta.json 的 cover 在真正渲染出 PNG 前保持 null（C4/B4）。"
            ),
            "ai_labeling": "封面 AI 标识为非阻断发布待办（D3），不在此阻断。",
        },
    }
    pack["recipe_hash"] = recipe_hash(recipe)
    return pack


def render_md(pack: Mapping[str, Any]) -> str:
    p = pack.get("prompt") or {}
    subject = (pack.get("identity_bindings") or [{}])[0] if pack.get("identity_bindings") else {}
    lines = [
        f"# 作品封面 prompt 包 — {pack.get('title')}",
        "",
        f"- 竖版比例：{pack.get('aspect_ratio')}（可接受 {pack.get('aspect_ratio_alt')}）",
        f"- 生图模型（C5 生成者）：{pack.get('生图模型') or '（未登记具体模型）'}",
        f"- 生图渠道 / 访问入口（access path）：{pack.get('生图渠道') or '-'} / {pack.get('访问入口') or '-'}",
        f"- 输出路径：{pack.get('output_path')}",
        f"- 当前 _meta.cover：{pack.get('cover_meta_field')}",
        "",
        "## 身份锚（B7/B9）",
        "",
    ]
    if subject:
        lines += [
            f"- 承载角色：{subject.get('carries_identity')}（{subject.get('name')}）",
            f"- 同源脸锚：`{subject.get('face_anchor_path') or '（未 ready）'}` · ready={subject.get('face_anchor_ready')}",
            f"- reference_group：`{subject.get('reference_group_ref')}`",
        ]
        if pack.get("render_blocking"):
            lines.append(f"- ⚠ render 前置缺口：{'、'.join(pack.get('render_blocking'))}（渲染前须由出图 runner 先补 ready 脸锚）")
    else:
        lines.append("- 无具名角色（纯 key visual / 标题式封面，合法降级）")
    lines += [
        "",
        "## Prompt（中文）",
        "",
        str(p.get("zh") or ""),
        "",
        "## Prompt（English）",
        "",
        str(p.get("en") or ""),
        "",
        "## 负向",
        "",
        str(pack.get("negative") or ""),
        "",
        "## 合规 / 降级留痕",
        "",
        str((pack.get("compliance") or {}).get("note") or ""),
        "",
    ]
    return "\n".join(lines)


def write_outputs(root: Path, pack: Mapping[str, Any]) -> Tuple[Path, Path]:
    out = root / COVER_DIR_REL
    jp = out / "cover_job.json"
    mp = out / "cover_prompt.md"
    write_atomic(jp, json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_atomic(mp, render_md(pack))
    return jp, mp


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d 作品级封面 prompt/job 生产包")
    ap.add_argument("root")
    ap.add_argument("--write", action="store_true", help="写出 cover_prompt.md / cover_job.json")
    ap.add_argument("--json", action="store_true")
    ap.add_argument(
        "--backfill-cover",
        nargs="?",
        const=DEFAULT_COVER_REL,
        metavar="PNG_REL",
        help="真正渲染出竖版 PNG 后确定性回填 _meta.json 的 cover（默认 出图/封面/cover.png）",
    )
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()

    if ns.backfill_cover is not None:
        wrote, cover, reason = backfill_cover(root, ns.backfill_cover)
        result = {"backfilled": wrote, "cover": cover, "reason": reason}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        # 回填失败（PNG 未就绪等）不硬阻断：cover 保持原值，返回 0 供流水线续跑。
        return 0

    pack = build_pack(root)
    if ns.write:
        jp, mp = write_outputs(root, pack)
        pack["outputs"] = {"json": str(jp), "md": str(mp)}
    if ns.json:
        print(json.dumps(pack, ensure_ascii=False, indent=2))
    else:
        print(render_md(pack))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
