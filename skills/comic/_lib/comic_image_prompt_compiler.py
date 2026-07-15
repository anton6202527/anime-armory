#!/usr/bin/env python3
"""Comic-owned compiler from panel production contracts to image prompts."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Mapping, Sequence


KIND = "comic_compiled_image_prompt"
VERSION = 1
PROFILE_VERSION = "2026-07-15.1"
_INTERNAL_RE = re.compile(
    r"(?:CHAR_|MON_|LOC_|PROP_|SYS_|FX_|STYLE_|出图/|\.png\b|identity_registry|asset_registry|reference_group)",
    re.I,
)
_INTERNAL_TOKEN_RE = re.compile(r"\b(?:CHAR|MON|LOC|PROP|SYS|FX|STYLE)_[A-Z0-9_]+\b", re.I)
_IMAGE_PATH_RE = re.compile(r"(?:[^\s；;,，。]+[/\\])?[^\s；;,，。]+\.(?:png|jpe?g|webp|avif)\b", re.I)
_TOKEN_LABELS = {
    "CHAR": "已登记角色参考",
    "MON": "已登记角色参考",
    "LOC": "已登记场景锚",
    "PROP": "已登记道具参考",
    "SYS": "已登记效果参考",
    "FX": "已登记效果参考",
    "STYLE": "项目风格锚",
}


_SAFETY_REPLACEMENTS = (
    (
        "超近景冲击格：姜月初双手将横刀刺入裴长青胸口，接触点被深红血色与飞散墨点遮挡，不展示露骨伤口",
        "超近景冲击格：姜月初双手握刀骤然推向裴长青胸前；用暗红布片与飞散墨点完全遮住接触处，只表现双方错愕和冲击，不表现穿刺、伤口或体液",
    ),
    ("囚服尸体和黑衣赤云纹的镇魔卫尸体", "倒卧的囚服无面剪影与黑衣赤云纹无面剪影"),
    ("枯草间尸骸横陈", "枯草间散落着被破布覆盖的静止无面剪影"),
    ("从尸骸间", "从破布覆盖的静止剪影之间"),
    ("尸骸缝隙", "破布与枯草缝隙"),
    ("尸骸", "被破布覆盖的静止无面剪影"),
    ("尸体", "静止无面剪影"),
    ("胸口巨大血窟窿", "仅位于前胸的圆形暗黑能量空洞"),
    ("胸口血窟窿", "仅位于前胸的圆形暗黑能量空洞"),
    ("巨大窟窿涌出黑血", "圆形暗黑能量空洞逸散黑色墨气"),
    ("巨大窟窿仍然流黑血", "圆形暗黑能量空洞仍逸散黑色墨气"),
    ("虎妖黑血", "虎妖周围的黑色墨迹"),
    ("黑色妖血", "黑色妖墨"),
    ("以妖血为墨", "以妖墨为媒"),
    ("黑血", "黑色墨迹"),
    ("妖血", "妖墨"),
    ("血色余晖", "暗红余晖"),
    ("血色轮廓光", "暗红轮廓光"),
    ("深红血色", "深暗红色"),
    ("血痕", "暗色尘泥拖痕"),
    ("血污", "尘泥污迹"),
    ("重伤濒死", "极度虚弱、近乎失去意识"),
    ("濒死", "极度虚弱"),
    ("左臂扭曲", "左臂无力垂落"),
    ("重伤", "虚弱"),
    ("伤口仍在", "前胸暗黑标志仍在"),
    ("伤口", "破损处"),
    ("死亡假象", "倒地静止状态"),
    ("死亡", "倒地静止"),
    ("斩杀生物", "击败妖物"),
    ("斩杀", "击败"),
    ("最后气血", "最后力量"),
    ("斩向虎妖脖颈", "挥向虎妖肩侧"),
    ("刺入", "推向"),
    ("刺进", "推向"),
    ("过度血腥特写", "任何写实伤害细节"),
)


def safety_shape_visual_text(value: Any) -> str:
    """在编译期把高风险视觉措辞改写为非写实、可执行的等价叙事。"""
    shaped = str(value or "")
    for old, new in _SAFETY_REPLACEMENTS:
        shaped = shaped.replace(old, new)
    return shaped


def one_line(value: Any, limit: int = 520) -> str:
    if isinstance(value, Mapping):
        text = "；".join(f"{k}={one_line(v)}" for k, v in value.items() if one_line(v))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        text = "；".join(one_line(v) for v in value if one_line(v))
    else:
        text = str(value or "")
    text = re.sub(r"\s+", " ", text).strip(" ；;,，。")
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit("；", 1)[0].rsplit("。", 1)[0]
    return (cut or text[:limit]).rstrip(" ；;,，。") + "…"


def public_text(value: Any, limit: int = 520) -> str:
    """Convert auditable contract text into model-facing visible language.

    Scene/identity contracts may legitimately mention registry IDs and image
    paths.  They stay in the production contract, while this compiler replaces
    them with semantic labels so internal bookkeeping never reaches the model.
    """
    text = one_line(safety_shape_visual_text(value), limit * 2)

    def replace_token(match: re.Match[str]) -> str:
        prefix = match.group(0).split("_", 1)[0].upper()
        return _TOKEN_LABELS.get(prefix, "已登记参考")

    text = _INTERNAL_TOKEN_RE.sub(replace_token, text)
    text = _IMAGE_PATH_RE.sub("已登记参考图", text)
    text = re.sub(r"(?:出图[/\\]|identity_registry|asset_registry|reference_group)", "已登记参考", text, flags=re.I)
    text = re.sub(r"(已登记[^；;,，。 ]+)(?:\s*\1)+", r"\1", text)
    return one_line(text, limit)


def normalize_backend(value: Any) -> str:
    text = one_line(value).lower()
    for aliases, name in (
        (("gpt image", "gpt-image", "openai", "codex"), "gpt_image"),
        (("gemini", "nano banana"), "gemini"),
        (("seedream",), "seedream"),
        (("kling", "可灵", "主体库"), "kling_subject"),
        (("dreamina", "即梦"), "dreamina"),
        (("flux", "comfyui", "sdxl", "stable diffusion"), "diffusion_pipeline"),
        (("manual", "人工"), "manual"),
    ):
        if any(alias in text for alias in aliases):
            return name
    return text or "generic"


def profile_for(value: Any) -> Dict[str, str]:
    backend = normalize_backend(value)
    if backend == "gpt_image":
        return {"backend": backend, "profile": "gpt_image_comic_natural", "negative": "inline_guard"}
    if backend == "gemini":
        return {"backend": backend, "profile": "gemini_comic_structured", "negative": "inline_guard"}
    if backend in {"seedream", "kling_subject", "dreamina"}:
        return {"backend": backend, "profile": "zh_comic_reference_first", "negative": "inline_guard"}
    if backend == "diffusion_pipeline":
        return {"backend": backend, "profile": "diffusion_comic_tags", "negative": "separate"}
    return {"backend": backend, "profile": "generic_comic_natural", "negative": "inline_guard"}


def _hash(contract: Mapping[str, Any]) -> str:
    raw = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compile_prompt(contract: Mapping[str, Any]) -> Dict[str, Any]:
    profile = profile_for(contract.get("backend"))
    visible = public_text(contract.get("visible_facts"), 420)
    style = public_text(contract.get("style"), 260)
    composition = public_text(contract.get("composition"), 300)
    scene = public_text(contract.get("scene_continuity"), 340)
    identity = public_text(contract.get("identity_hold"), 320)
    finishing = public_text(contract.get("finishing"), 360)
    text_strategy = public_text(contract.get("text_strategy"), 220)
    anatomy = public_text(contract.get("anatomy"), 220)
    negative_elements = [public_text(v, 70) for v in contract.get("negative_elements") or [] if public_text(v, 70)]

    parts = ["生成一张铺满画布的单格无字漫画画面。"]
    parts.append(f"画面事实：{visible}。" if visible else "")
    parts.append(f"构图与表演：{composition}。" if composition else "")
    parts.append(f"画风与稿层：{style}。" if style else "")
    parts.append(f"场景连续性：{scene}。" if scene else "")
    parts.append(f"参考保持：{identity}。" if identity else "")
    parts.append(f"线稿、黑场、网点与效果：{finishing}。" if finishing else "")
    parts.append(f"文字处理：{text_strategy}。" if text_strategy else "")
    parts.append(f"人体与道具：{anatomy}。" if anatomy else "")
    if profile["negative"] == "inline_guard" and negative_elements:
        parts.append("避免：" + "、".join(negative_elements) + "。")
    prompt = " ".join(part for part in parts if part).strip()
    negative_prompt = ", ".join(negative_elements) if profile["negative"] == "separate" else ""
    payload: Dict[str, Any] = {
        "kind": KIND,
        "version": VERSION,
        "profile_version": PROFILE_VERSION,
        "panel_id": one_line(contract.get("panel_id")),
        "backend": profile["backend"],
        "profile": profile["profile"],
        "language": "zh",
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "request_controls": {
            "reference_inputs": list(contract.get("reference_inputs") or []),
            "canvas": dict(contract.get("canvas") or {}),
        },
        "source_contract_sha256": _hash(contract),
    }
    payload["lint"] = lint(payload)
    return payload


def lint(payload: Mapping[str, Any]) -> Dict[str, List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    prompt = one_line(payload.get("prompt"), 100000)
    if not prompt:
        errors.append("empty_submit_prompt")
    if "画面事实：" not in prompt:
        errors.append("missing_visible_facts")
    if "画风与稿层：" not in prompt:
        errors.append("missing_style_or_render_stage")
    if _INTERNAL_RE.search(prompt):
        errors.append("submit_prompt_contains_internal_contract_reference")
    if any(token in prompt for token in ("对白：", "旁白：", "台词：")):
        errors.append("submit_prompt_contains_exact_dialogue")
    if len(prompt) > 1400:
        warnings.append(f"submit_prompt_verbose:{len(prompt)}")
    # Semicolons are the intended compact structure inside scene/finishing
    # contracts.  Count only sentence-ending punctuation here; treating every
    # structured field separator as a new sentence warned on normal jobs.
    if len([p for p in re.split(r"[。.!?]+", prompt) if p.strip()]) > 20:
        warnings.append("submit_prompt_many_clauses")
    return {"errors": errors, "warnings": warnings}
