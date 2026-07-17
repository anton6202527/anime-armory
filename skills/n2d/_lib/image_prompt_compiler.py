#!/usr/bin/env python3
"""Backend-aware compiler for n2d image submit requests.

The image production contract is intentionally richer than the request sent to
an image model.  This module is the single boundary between those layers.  It
keeps director/identity/asset/QC contracts auditable while emitting only the
pixel-relevant brief, reference roles and provider request parameters.

The compiler is deterministic and provider-SDK free.  Runners may translate
the returned request fields to a CLI/API, but must not append un-hashed creative
instructions after this boundary.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


KIND = "n2d_compiled_image_prompt"
VERSION = 1
PROFILE_VERSION = "2026-07-17.1"
COMPILED_HEADING = "### 后端编译提交 image prompt"

TASK_TYPES = {
    "character_catalog",
    "scene_asset",
    "prop_asset",
    "style_anchor",
    "shot_keyframe",
    "relay_edit",
    "multi_subject",
}

_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_RAW_PATH_RE = re.compile(
    r"(?:identity_registry|asset_registry|visual_state_ledger|角色库/|设定库/|生产数据/|"
    r"出图/(?:共享|第\d+集)/|[A-Za-z0-9_./-]+\.(?:json|md|png))",
    re.I,
)
_FULL_CONTRACT_RE = re.compile(
    r"剧本可看性合同|时长分配合同|重抽预算|检查清单|自检|路由理由|"
    r"script_quality_contract|director_camera_plan|reference_plan",
    re.I,
)
_NEGATIVE_PREFIX_RE = re.compile(
    r"^(?:不要|不得|禁止|避免|不可|别|无|no\s+|not\s+|without\s+|"
    r"do\s+not\s+|don't\s+|avoid\s+|exclude\s+)",
    re.I,
)
_NEGATIVE_COMMAND_RE = re.compile(
    r"\b(?:no|not|never|without|avoid|don't|do not|exclude)\b|不要|不得|禁止|避免|不可|"
    r"(?:^|[\s，。；;：:])别(?=\S)",
    re.I,
)
_ASPECT_RE = re.compile(r"(?<!\d)(1:1|2:3|3:2|3:4|4:3|4:5|5:4|9:16|16:9|21:9)(?!\d)")
_IMAGE_INDEX_RE = re.compile(r"(?:Image|图|参考图)\s*([0-9]+)", re.I)
_CHAR_ID_RE = re.compile(r"\b(?:CHAR|BEAST|CROWD|GROUP)_[A-Za-z0-9_\u4e00-\u9fff-]+(?:/[A-Za-z0-9_\u4e00-\u9fff-]+)?\b")
_ASSET_ID_RE = re.compile(r"\b(?:LOC|PROP|WEAPON|OUTFIT|VFX|STYLE)_[A-Za-z0-9_\u4e00-\u9fff-]+\b")


def _one_line(value: Any) -> str:
    if isinstance(value, str):
        text = value
    elif isinstance(value, Mapping):
        text = "；".join(
            f"{key}={_one_line(item)}" for key, item in value.items() if _one_line(item)
        )
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        text = "；".join(_one_line(item) for item in value if _one_line(item))
    else:
        text = str(value or "")
    return re.sub(r"\s+", " ", text).strip(" ；;,，。")


def _compact(value: Any, limit: int) -> str:
    text = _one_line(value)
    if len(text) <= limit:
        return text
    candidate = text[:limit]
    for separator in ("；", "。", ",", "，"):
        if separator in candidate:
            candidate = candidate.rsplit(separator, 1)[0]
            break
    return (candidate or text[:limit]).rstrip(" ；;,，。") + "…"


def _without_aspect_phrases(value: Any) -> str:
    text = _one_line(value)
    text = _ASPECT_RE.sub("", text)
    text = re.sub(r"(?:竖屏|竖版|横屏|横版|vertical|landscape)\s*(?=[；;,，。 ]|$)", "", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip(" ；;,，。")


def _hash_mapping(value: Mapping[str, Any]) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def normalize_backend(value: Any) -> str:
    raw = _one_line(value).lower()
    aliases = (
        (("codex",), "codex"),
        (("openai", "gpt image", "gpt-image", "chatgpt image"), "openai"),
        (("dreamina", "jimeng", "即梦"), "dreamina"),
        (("seedream", "doubao-seedream"), "seedream"),
        (("nano banana", "gemini", "nano_banana"), "gemini"),
        (("flux", "black forest"), "flux"),
        (("midjourney",), "midjourney"),
        (("imagen", "vertex image"), "imagen"),
        (("stable diffusion", "sdxl", "comfyui", "stability"), "stable_diffusion"),
        (("kling", "可灵"), "kling"),
    )
    for names, canonical in aliases:
        if any(name in raw for name in names):
            return canonical
    return raw or "generic"


def backend_profile(value: Any) -> Dict[str, Any]:
    """Return prompt dialect and request-field capabilities for one backend."""
    backend = normalize_backend(value)
    profiles: Dict[str, Dict[str, Any]] = {
        "codex": {
            "name": "codex_gpt_image_agent_brief",
            "language": "zh",
            "negative_strategy": "inline_constraints",
            "embed_aspect": True,
            "advisory_char_limit": 1500,
            "request_fields": ("aspect_ratio", "quality", "output_format"),
        },
        "openai": {
            "name": "openai_gpt_image_natural_brief",
            "language": "zh",
            "negative_strategy": "inline_constraints",
            "embed_aspect": False,
            "advisory_char_limit": 1400,
            "request_fields": ("size", "quality", "background", "output_format"),
        },
        "dreamina": {
            "name": "seedream_concise_natural_language",
            "language": "zh",
            "negative_strategy": "inline_constraints",
            "embed_aspect": True,
            "advisory_char_limit": 1200,
            "request_fields": (
                "aspect_ratio", "size", "quality", "output_format",
                "model_version", "resolution_type",
            ),
        },
        "seedream": {
            "name": "seedream_concise_natural_language",
            "language": "zh",
            "negative_strategy": "inline_constraints",
            "embed_aspect": False,
            "advisory_char_limit": 1200,
            "request_fields": ("size", "quality", "output_format", "prompt_optimization"),
        },
        "gemini": {
            "name": "gemini_multimodal_reference_roles",
            "language": "zh",
            "negative_strategy": "inline_constraints",
            "embed_aspect": False,
            "advisory_char_limit": 1400,
            "request_fields": ("aspect_ratio", "image_size", "mime_type"),
        },
        "flux": {
            "name": "flux_positive_structured",
            "language": "en",
            "negative_strategy": "positive_only",
            "embed_aspect": False,
            "advisory_char_limit": 1500,
            "request_fields": ("width", "height", "prompt_upsampling", "output_format"),
        },
        "midjourney": {
            "name": "midjourney_compact_snapshot",
            "language": "en",
            "negative_strategy": "parameter_no",
            "embed_aspect": False,
            "advisory_char_limit": 750,
            "request_fields": ("aspect_ratio", "quality", "style_reference", "omni_reference"),
        },
        "imagen": {
            "name": "imagen_prompt_with_negative_elements",
            "language": "en",
            "negative_strategy": "separate_element_list",
            "embed_aspect": False,
            "advisory_char_limit": 1300,
            "request_fields": ("aspect_ratio", "sample_count", "seed", "output_format"),
        },
        "stable_diffusion": {
            "name": "diffusion_positive_negative",
            "language": "en",
            "negative_strategy": "separate_element_list",
            "embed_aspect": False,
            "advisory_char_limit": 1200,
            "request_fields": ("width", "height", "steps", "cfg_scale", "seed"),
        },
        "kling": {
            "name": "kling_subject_bound_brief",
            "language": "zh",
            "negative_strategy": "inline_constraints",
            "embed_aspect": True,
            "advisory_char_limit": 1200,
            "request_fields": ("aspect_ratio", "quality", "output_format", "subject_ids"),
        },
    }
    profile = dict(profiles.get(backend) or {
        "name": "generic_image_brief",
        "language": "zh",
        "negative_strategy": "inline_constraints",
        "embed_aspect": True,
        "advisory_char_limit": 1400,
        "request_fields": ("aspect_ratio", "size", "quality", "output_format"),
    })
    profile["backend"] = backend
    return profile


def task_profile(value: Any) -> Dict[str, Any]:
    task = _one_line(value).lower()
    aliases = {
        "character": "character_catalog",
        "character_board": "character_catalog",
        "turnaround": "character_catalog",
        "scene": "scene_asset",
        "location": "scene_asset",
        "environment": "scene_asset",
        "prop": "prop_asset",
        "asset": "prop_asset",
        "weapon": "prop_asset",
        "vfx": "prop_asset",
        "style": "style_anchor",
        "keyframe": "shot_keyframe",
        "firstframe": "shot_keyframe",
        "shot": "shot_keyframe",
        "midframe": "relay_edit",
        "tailframe": "relay_edit",
        "image_edit": "relay_edit",
        "multi": "multi_subject",
    }
    task = aliases.get(task, task)
    if task not in TASK_TYPES:
        task = "shot_keyframe"
    return {
        "name": task,
        "requires_action": task in {"shot_keyframe", "relay_edit", "multi_subject"},
        "requires_neutral_catalog": task in {"character_catalog", "prop_asset", "style_anchor"},
        "requires_preserve_delta": task == "relay_edit",
    }


def _dedupe(values: Iterable[Any], *, limit: int = 0) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        text = _one_line(value)
        key = re.sub(r"[\s，。；;,:：]+", "", text).lower()
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(text)
        if limit and len(out) >= limit:
            break
    return out


def _semantic_key(value: Any) -> str:
    return re.sub(r"[\s，。；;,:：/|（）()\-]+", "", _one_line(value)).lower()


def _compress_repeated(values: Iterable[Any], *, limit: int = 0) -> List[str]:
    """Drop exact and clearly subsumed clauses while retaining the fuller rule."""
    unique = _dedupe(values)
    kept: List[str] = []
    for index, text in enumerate(unique):
        key = _semantic_key(text)
        if not key:
            continue
        if any(
            key != _semantic_key(other)
            and len(key) >= 8
            and key in _semantic_key(other)
            for other in unique[index + 1:]
        ):
            continue
        replaced = False
        for existing_index, existing in enumerate(kept):
            existing_key = _semantic_key(existing)
            if len(existing_key) >= 8 and existing_key in key:
                kept[existing_index] = text
                replaced = True
                break
        if not replaced:
            kept.append(text)
        if limit and len(kept) >= limit:
            break
    return kept


def resolve_contract_conflicts(
    contract: Mapping[str, Any],
    profile: Mapping[str, Any],
    task: str,
) -> tuple[Dict[str, Any], List[str], Dict[str, int]]:
    """Apply deterministic priority rules before rendering backend text.

    Request parameters beat prose for canvas geometry; the selected style field
    beats legacy style/aspect phrases embedded in composition; neutral catalog
    tasks never inherit story action; longer non-duplicate guards beat shorter
    repeats.  The original contract hash remains unchanged for traceability.
    """
    resolved = dict(contract)
    decisions: List[str] = []
    params = resolved.get("request_params") if isinstance(resolved.get("request_params"), Mapping) else {}
    requested_aspect = _one_line(params.get("aspect_ratio"))
    for key in ("composition", "style"):
        original = _one_line(resolved.get(key))
        cleaned = _without_aspect_phrases(original) if requested_aspect else original
        if cleaned != original:
            decisions.append(f"request_params.aspect_ratio_overrode_{key}")
            resolved[key] = cleaned
    if task in {"character_catalog", "scene_asset", "prop_asset", "style_anchor"} and _one_line(resolved.get("action")):
        resolved["action"] = ""
        decisions.append("neutral_catalog_dropped_story_action")

    # Natural-language image backends can interpret graphic anatomy words in
    # negative constraints as requested content. Keep the production contract
    # untouched for QC, but submit a positive anatomy formulation and soften a
    # small set of clearly non-violent social actions at the provider boundary.
    if str(profile.get("backend") or "") in {"codex", "openai"}:
        action = _one_line(resolved.get("action"))
        if not re.search(r"刀|剑|枪|矛|匕首|武器|流血|伤口|受伤|搏斗|打斗|攻击|杀", action):
            softened = action
            softened = softened.replace("用两指弹回木牌", "用两指点住木牌，再把木牌递回少年胸前")
            softened = softened.replace("承受冲击但不后退", "稳稳站住")
            # Preserve the hierarchy/dialogue beat while avoiding an adult-on-
            # minor coercive-contact reading at the provider boundary. The
            # source script and QC contract remain unchanged.
            softened = softened.replace(
                "粗大右手压在瘦削左肩，粗布轻微凹下",
                "粗大右手撑在少年身侧的木桌边，靠近但不接触身体",
            )
            softened = softened.replace("手掌压到少年肩头", "手掌落在少年身侧的木桌面")
            softened = softened.replace("肩头接触只用手部插入镜", "手掌与桌面接触只用手部插入镜")
            softened = softened.replace("拍肩为张老大右手", "撑桌为张老大右手")
            softened = softened.replace("手掌压肩插入镜", "手掌撑桌插入镜")
            if softened != action:
                resolved["action"] = softened
                decisions.append("nonviolent_social_action_softened_for_provider")

        # A benign adult/minor dialogue can still be misread as coercive when
        # the production contract uses dramatic shorthand such as “俯身压下”
        # or “羞辱”.  Keep those words in the auditable source contract, but at
        # the provider boundary describe the same beat as separated verbal
        # blocking with explicit zero contact.  Apply the rewrite to every
        # pixel-facing field so a preserve/policy sentence cannot reintroduce
        # the unsafe reading after the action field was cleaned.
        provider_blob = _one_line([
            resolved.get("objective"), resolved.get("subject"), resolved.get("action"),
            resolved.get("mood"), resolved.get("preserve"), resolved.get("policy_guards"),
        ])
        adult_minor_dialogue = (
            re.search(r"十四岁|少年|未成年|minor", provider_blob, re.I)
            and re.search(r"成年|成人|管事|张老大|adult|supervisor", provider_blob, re.I)
            and not re.search(r"刀|剑|枪|矛|匕首|武器|流血|伤口|受伤|搏斗|打斗|攻击|杀", provider_blob)
        )
        if adult_minor_dialogue:
            replacements = (
                ("张老大俯身把命令逐字压下", "张老大站在木桌另一侧，严肃口头交代劳役"),
                ("管事俯身", "管事站在木桌另一侧"),
                ("把羞辱变成具体劳役", "把严苛安排落实为具体劳役"),
                ("羞辱", "严苛训话"),
                ("粗大右手撑在少年身侧的木桌边，靠近但不接触身体", "右手撑在木桌远离少年的一侧，两人由木桌明确分隔，零身体接触"),
                ("成人右手只撑在少年身侧桌边，靠近但不接触少年身体", "张老大的右手只撑在木桌远离少年的一侧，两人由木桌明确分隔，零身体接触"),
                ("手掌落在少年身侧的木桌面", "手掌落在木桌远离少年的一侧"),
                ("手掌与桌面接触只用手部插入镜", "手掌只与木桌接触，少年保持完整个人空间"),
            )

            def rewrite_adult_minor(value: Any) -> Any:
                if isinstance(value, str):
                    text = value
                    for old, new in replacements:
                        text = text.replace(old, new)
                    return text
                if isinstance(value, list):
                    return [rewrite_adult_minor(item) for item in value]
                if isinstance(value, tuple):
                    return tuple(rewrite_adult_minor(item) for item in value)
                return value

            changed = False
            for key in ("objective", "action", "mood", "preserve", "policy_guards"):
                before = resolved.get(key)
                after = rewrite_adult_minor(before)
                if after != before:
                    resolved[key] = after
                    changed = True
            if changed:
                decisions.append("adult_minor_dialogue_rewritten_as_separated_verbal_blocking")

        exclusions = normalize_exclusions(resolved.get("exclude") or [])
        graphic_anatomy = re.compile(r"断手|断肢|缺肢|血光|伤口|入体|贯穿")
        if any(graphic_anatomy.search(item) for item in exclusions):
            exclusions = [item for item in exclusions if not graphic_anatomy.search(item)]
            exclusions.append("人体与手部结构自然完整")
            resolved["exclude"] = _dedupe(exclusions, limit=14)
            decisions.append("graphic_negative_anatomy_rewritten_positive")

    before_preserve = len(_dedupe(resolved.get("preserve") or []))
    before_guards = len(_dedupe(resolved.get("policy_guards") or []))
    resolved["preserve"] = _compress_repeated(resolved.get("preserve") or [], limit=5)
    resolved["policy_guards"] = _compress_repeated(resolved.get("policy_guards") or [], limit=12)
    if len(resolved["preserve"]) < before_preserve or len(resolved["policy_guards"]) < before_guards:
        decisions.append("repeated_constraints_compressed")
    stats = {
        "preserve_input": before_preserve,
        "preserve_output": len(resolved["preserve"]),
        "policy_guard_input": before_guards,
        "policy_guard_output": len(resolved["policy_guards"]),
    }
    return resolved, decisions, stats


def normalize_exclusions(value: Any, *, limit: int = 14) -> List[str]:
    """Normalize human prohibitions into short backend-neutral element phrases."""
    if isinstance(value, str):
        raw_values: Iterable[Any] = re.split(r"[\n；;]+", value)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        raw_values = value
    else:
        raw_values = [value]
    parts: List[str] = []
    for raw in raw_values:
        text = _one_line(raw)
        text = re.sub(r"^(?:风格禁忌|身份禁漂|资产禁漂|本镜禁忌|禁止|限制)[：:]\s*", "", text)
        for piece in re.split(r"[、,，]+", text):
            item = _NEGATIVE_PREFIX_RE.sub("", piece.strip())
            item = item.strip(" ；;,，。")
            if not item or item in {"无", "none", "-"}:
                continue
            parts.append(_compact(item, 72))
    return _dedupe(parts, limit=limit)


def normalize_references(values: Any) -> List[Dict[str, Any]]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)):
        values = [values] if values else []
    out: List[Dict[str, Any]] = []
    seen = set()
    for index, value in enumerate(values, 1):
        if isinstance(value, Mapping):
            item = {
                "index": int(value.get("index") or index),
                "role": _one_line(value.get("role")) or "reference",
                "owner": _one_line(value.get("owner") or value.get("id")),
                "path": _one_line(
                    value.get("actual_path") or value.get("prepared_rel_path") or
                    value.get("rel_path") or value.get("path") or value.get("image")
                ),
                "sha256": _one_line(
                    value.get("prepared_sha256") or value.get("sha256") or value.get("source_sha256")
                ),
            }
        else:
            item = {"index": index, "role": "reference", "owner": "", "path": _one_line(value), "sha256": ""}
        key = (item["role"], item["owner"], item["path"], item["sha256"])
        if not item["path"] or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _strip_nonvisual_metadata(value: Any) -> str:
    text = _one_line(value)
    text = re.sub(r"`", "", text)
    text = _RAW_PATH_RE.sub("", text)
    text = re.sub(r"\b(?:sha256|hash|manifest|registry)\s*=\s*[^；;,，。 ]+", "", text, flags=re.I)
    # Administrative headings may be embedded inside an otherwise visual
    # director-intent sentence (for example ``必须服务剧本可看性合同：...``).
    # Keep the pixel-relevant payload after the heading, but never send the
    # production-contract label itself to the image backend or immediately
    # fail our own compiled-prompt lint.
    text = re.sub(
        r"(?:必须服务|继承|来自)?\s*(?:剧本可看性合同|时长分配合同|重抽预算|检查清单|自检|路由理由|"
        r"script_quality_contract|director_camera_plan|reference_plan)\s*[：:=]?\s*",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(r"\s*；\s*；+", "；", text)
    return text.strip(" ；;,，。")


def _field(section: str, label: str) -> str:
    match = re.search(rf"^\*\*{re.escape(label)}\*\*[：:]\s*(.+)$", section or "", re.M)
    return match.group(1).strip() if match else ""


def _prompt_block(section: str, language: str = "中文") -> str:
    match = re.search(
        rf"(?ms)^###\s*正向\s*prompt（{re.escape(language)}[^）]*）\s*\n"
        r"(?:```(?:text)?\s*\n)?(?P<body>.*?)(?:\n```)?(?=^###\s+|^##\s+|\Z)",
        section or "",
    )
    return match.group("body").strip() if match else ""


def _prompt_line(block: str, label: str) -> str:
    match = re.search(rf"^{re.escape(label)}[：:]\s*(.+)$", block or "", re.M)
    return match.group(1).strip() if match else ""


def _negative_block(section: str) -> str:
    match = re.search(
        r"(?ms)^###\s*负向\s*prompt[^\n]*\n(?P<body>.*?)(?=^###\s+|^##\s+|\Z)",
        section or "",
    )
    return match.group("body").strip().strip("`") if match else ""


def _makeup_submission_block(section: str) -> str:
    match = re.search(
        r"(?ms)^###\s*定妆图提交口径[^\n]*\n\s*```(?:text)?\s*\n(?P<body>.*?)\n```",
        section or "",
    )
    return match.group("body").strip() if match else ""


def infer_task_type(section: str, *, mode: str = "", target_path: str = "") -> str:
    mode_low = _one_line(mode).lower()
    if mode_low in {"midframe", "tailframe", "image_edit", "edit", "inpaint", "outpaint"}:
        return "relay_edit"
    blob = f"{section}\n{target_path}"
    heading = re.search(r"(?m)^##\s+([^\n]+)", section or "")
    heading_text = heading.group(1).strip() if heading else ""
    # Shared character/asset contracts legitimately mention STYLE_ANCHOR as a
    # dependency.  Only the current target/title may classify this request as
    # style-anchor synthesis; scanning the whole section misroutes every makeup
    # board that says "inherit STYLE_ANCHOR".
    if re.search(r"(?:风格锚|style[_ -]?anchor)", f"{target_path}\n{heading_text}", re.I):
        return "style_anchor"
    if re.search(r"^##\s*镜头\s*\d+", section or "", re.M):
        ids = set(_CHAR_ID_RE.findall(blob))
        if len({item.split("/", 1)[0] for item in ids}) >= 2 or "多人同框身份槽位" in blob:
            return "multi_subject"
        return "shot_keyframe"
    # A scene plate may explicitly bind resident CHAR_/BEAST_ identities.
    # Classify from the current target/title before scanning dependencies, or
    # the resident identity turns the whole LOC plate into character_catalog.
    if re.search(r"\bLOC_", f"{target_path}\n{heading_text}"):
        return "scene_asset"
    # Shared non-scene assets may legitimately mention a LOC lighting/axis
    # contract in their full human-readable section. Classify the thing being
    # generated from its target/title before scanning those dependencies, or a
    # WEAPON/PROP/VFX card is silently compiled as an environment plate.
    if re.search(r"\b(?:WEAPON|PROP|VFX)_", f"{target_path}\n{heading_text}"):
        return "prop_asset"
    if _CHAR_ID_RE.search(blob):
        return "character_catalog"
    if re.search(r"\bLOC_", blob):
        return "scene_asset"
    return "prop_asset"


def contract_from_section(
    section: str,
    *,
    backend: Any = None,
    model: Any = None,
    channel: Any = None,
    mode: str = "",
    task_type: str = "",
    target_path: str = "",
    style: str = "",
    aspect_ratio: str = "",
    reference_inputs: Any = None,
    request_params: Optional[Mapping[str, Any]] = None,
    policy_guards: Any = None,
    risk_flags: Any = None,
) -> Dict[str, Any]:
    """Extract a compact canonical image contract from a full Markdown block."""
    # Prompt packs append an auditable compiled-request block. It is output,
    # never source. Reading it back recursively makes every retry longer and
    # can resurrect stale or safety-sensitive constraints.
    section = section_without_compiled(section)
    positive = _prompt_block(section, "中文")
    inferred = task_type or infer_task_type(section, mode=mode, target_path=target_path)
    makeup = _makeup_submission_block(section) if inferred == "character_catalog" else ""
    identities = _prompt_line(positive, "锚点句") or _field(section, "锚点句")
    identity_lock = _prompt_line(positive, "身份锁定句") or _field(section, "身份锁定句")
    composition = _prompt_line(positive, "镜头构图") or _field(section, "镜头/机位")
    action = _prompt_line(positive, "动作瞬间") or _field(section, "剧本描述")
    action = re.split(
        r"；(?:人体完整性|解剖完整性|手部归属|身体接地|身体裁切|本镜状态锁)[^：:]*[：:]",
        action,
        maxsplit=1,
    )[0].strip()
    scene_light = _prompt_line(positive, "场景光影") or _field(section, "场景 DNA")
    mood = _prompt_line(positive, "情绪张力") or _field(section, "导演意图")
    style_text = style or _prompt_line(positive, "画风规格")
    exclusions = normalize_exclusions([
        _prompt_line(positive, "禁止"),
        _prompt_line(makeup, "禁止"),
        _negative_block(section),
    ])
    if inferred == "style_anchor":
        # Style boards are control assets.  Project style prose can name the
        # people, locations and props that will eventually use the style, and
        # custom taboo lists may already consume the generic exclusion limit.
        # Put control-asset isolation first so those nouns cannot turn the
        # anchor itself into a story still or environment plate.
        exclusions = normalize_exclusions([
            "人物或清晰人脸",
            "动物或妖物",
            "建筑或城寨或具体环境景观",
            "兵器或道具或器皿或家具或工作台",
            "卷轴或地图或书页或可读文字或伪造文字",
            "剧情动作或海报构图或水印或logo",
            *exclusions,
        ])
    if makeup:
        identities = "；".join(_dedupe([
            _prompt_line(makeup, "角色身份"),
            _prompt_line(makeup, "年龄/年龄档"),
            _prompt_line(makeup, "服装妆造"),
            _prompt_line(makeup, "固定外貌"),
        ], limit=8))
        composition = composition or _prompt_line(makeup, "定妆要求")
        identity_lock = identity_lock or "；".join(_dedupe([
            _prompt_line(makeup, "固定外貌"),
            _prompt_line(makeup, "服装妆造"),
        ], limit=4))
    if inferred == "scene_asset" and not scene_light:
        # Scene makeup sections are commonly authored as one dense visual
        # paragraph rather than shot-style labelled lines.  Dropping that
        # paragraph leaves the model with only the global style and silently
        # loses landmarks, axis, resident assets and lighting continuity.
        scene_light = positive
    if inferred == "prop_asset" and not identities:
        # Prop/weapon/VFX cards are also commonly one dense asset paragraph.
        # Keep it as the generated subject; otherwise the compiler emits only
        # the filename and global style, dropping topology/material/faceless
        # constraints from the actual paid request.
        identities = positive
    preserve = _dedupe([
        identity_lock,
        _field(section, "资产拓扑锁"),
        _field(section, "本镜状态锁"),
        _field(section, "光位锚"),
    ], limit=6)
    objective = (
        _field(section, "导演意图") or _field(section, "剧本描述") or
        _field(section, "定妆图提交口径") or target_path
    )
    if inferred == "style_anchor":
        objective = "抽象分区式视觉语言样板，不是剧情剧照、环境设定图、海报或道具陈列"
        identities = positive
        composition = (
            "中性无叙事背景上的分区样板；只展示色卡、明暗/光比阶梯、线条笔触、"
            "颜料颗粒与近裁材质样本"
        )
    subject_slots = _field(section, "多人同框身份槽位")
    refs = normalize_references(reference_inputs)
    params = dict(request_params or {})
    if aspect_ratio:
        params.setdefault("aspect_ratio", aspect_ratio)
    is_turnaround_catalog = (
        inferred == "character_catalog"
        and bool(re.search(r"三视图|五角|turnaround", f"{target_path}\n{section}", re.I))
    )
    if is_turnaround_catalog:
        # Five full-body columns need a wide technical plate.  Inheriting the
        # episode's portrait aspect makes each body too narrow to inspect and
        # produces unusable split views.
        params["aspect_ratio"] = "16:9"
    raw_policy_guards = [
        _strip_nonvisual_metadata(item)
        for item in (
            policy_guards
            if isinstance(policy_guards, Sequence) and not isinstance(policy_guards, (str, bytes, bytearray))
            else [policy_guards]
        )
        if _strip_nonvisual_metadata(item)
    ]
    if is_turnaround_catalog:
        story_only_markers = (
            "镜头为旁观者视角",
            "武器入体/接触点",
            "入体点硬锁",
            "本镜已指定胸口/胸前",
            "源帧几何连续性",
        )
        raw_policy_guards = [
            item for item in raw_policy_guards
            if not any(marker in item for marker in story_only_markers)
        ]
    contract: Dict[str, Any] = {
        "task_type": inferred,
        "backend": _one_line(backend),
        "model": _one_line(model),
        "channel": _one_line(channel),
        "mode": _one_line(mode) or inferred,
        "target_path": _one_line(target_path),
        "objective": _strip_nonvisual_metadata(objective),
        "subject": _strip_nonvisual_metadata(identities or identity_lock),
        "subject_slots": _strip_nonvisual_metadata(subject_slots),
        "composition": _strip_nonvisual_metadata(composition),
        "action": _strip_nonvisual_metadata(action),
        "scene": _strip_nonvisual_metadata(scene_light),
        "lighting": _strip_nonvisual_metadata(_field(section, "光位锚")),
        "mood": _strip_nonvisual_metadata(mood),
        "style": _strip_nonvisual_metadata(style_text),
        "preserve": [_strip_nonvisual_metadata(item) for item in preserve if _strip_nonvisual_metadata(item)],
        "policy_guards": _dedupe(raw_policy_guards),
        "exclude": exclusions,
        "risk_flags": _dedupe(
            risk_flags
            if isinstance(risk_flags, Sequence) and not isinstance(risk_flags, (str, bytes, bytearray))
            else [risk_flags]
        ),
        "reference_inputs": refs,
        "request_params": params,
        "source_contract_text_sha256": sha256_text(section_without_compiled(section)),
    }
    return contract


def section_without_compiled(section: str) -> str:
    text = str(section or "")
    marker = re.search(rf"(?m)^\s*{re.escape(COMPILED_HEADING)}\s*$", text)
    return text[: marker.start()].rstrip() if marker else text.rstrip()


def _reference_role_sentences(refs: Sequence[Mapping[str, Any]], language: str) -> List[str]:
    lines: List[str] = []
    for index, item in enumerate(refs, 1):
        role = _one_line(item.get("role")) or "reference"
        owner = _one_line(item.get("owner")) or "registered asset"
        if language == "en":
            lines.append(f"Image {index} is the {role} reference for {owner}")
        else:
            lines.append(f"图{index}作为{owner}的{role}参考")
    return lines


def _positive_guard(task: str, language: str) -> str:
    if language == "en":
        if task == "scene_asset":
            return "The environment is empty, spatially coherent and clean, with stable landmarks and lighting."
        if task in {"prop_asset", "style_anchor"}:
            return "The isolated reference remains clean, structurally complete and free of added lettering or branding."
        return "Registered subjects remain anatomically complete and clearly separated; the clean frame contains only intended elements."
    if task == "scene_asset":
        return "保持空场景、空间结构和地标清楚，光位稳定，画面干净。"
    if task in {"prop_asset", "style_anchor"}:
        return "保持参考资产结构完整、背景干净，画面不增加文字或品牌标识。"
    return "仅保留已登记主体，人物结构完整且彼此分离，画面干净，不增加文字或水印。"


def _conditional_guards(contract: Mapping[str, Any], task: str, language: str) -> List[str]:
    blob = " ".join(_one_line(contract.get(key)) for key in (
        "objective", "subject", "subject_slots", "composition", "action", "scene", "preserve"
    ))
    flags = set(_one_line(item).lower() for item in contract.get("risk_flags") or [])
    hands = bool(re.search(
        r"左手|右手|双手|手掌|手腕|手指|握|抓|持|扶|触|接触|刀|剑|枪|"
        r"\bhand(?:s)?\b|\bgrip|\bhold|\btouch",
        blob,
        re.I,
    )) or "hands" in flags
    ground = bool(re.search(r"全身|站立|跪|倒地|落地|脚|鞋|full body|standing|kneel|ground", blob, re.I)) or "grounding" in flags
    closeup = bool(re.search(r"\b(?:CU|MCU|ECU)\b|近景|特写|反打|close-up", blob, re.I)) or "closeup" in flags
    multi = task == "multi_subject" or bool(_one_line(contract.get("subject_slots")))
    if task in {"scene_asset", "prop_asset", "style_anchor"}:
        # Scene contracts often name characters only to describe blocking and
        # axis continuity; isolated asset cards often name a knife/weapon whose
        # noun alone matches the generic hand-risk regex. Neither case should
        # activate character anatomy guards or populate the clean asset plate.
        hands = False
        ground = False
        closeup = False
        multi = False
    guards: List[str] = []
    if language == "en":
        if hands:
            guards.append("Visible hands belong unambiguously to their subjects and connect naturally to the correct arms and contact points; each human subject has two arms and at most two visible hands")
        if ground:
            guards.append("Visible bodies and footwear are complete, naturally cropped and physically grounded")
        if closeup:
            guards.append("The primary face remains identifiable from its own reference in a natural three-quarter, side-facing or over-shoulder performance")
        if multi:
            guards.append("Each named subject stays in its assigned screen slot and uses only its own identity reference")
    else:
        if hands:
            guards.append("可见手部归属清楚并自然连接正确手臂和接触点；单个人形主体最多两条手臂、两只可见手")
        if ground:
            guards.append("可见身体与鞋脚结构完整、裁切自然、接地明确")
        if closeup:
            guards.append("主检脸与自身参考一致且可辨，但不转成直视镜头的肖像摆拍")
        if multi:
            guards.append("每个具名主体守住自己的画面槽位，只使用自己的身份参考")
    return guards


_EN_POLICY_GUARDS = (
    ("用户提供的人物/主角参考图", "Use external character references only for identity, body proportions and age; apply the selected project style, lighting, composition and wardrobe."),
    ("镜头为旁观者视角", "Use an observer camera; subjects look toward the scene target, opponent or contact point in a readable three-quarter, side or over-shoulder performance."),
    ("共享群像角色角度资产", "Show one ordinary representative member only, preserving the same member across all requested views."),
    ("源帧几何连续性", "Preserve the source-frame staging, axis, weapon or prop contact point, wound position, grip and entry angle; advance only the stated local motion delta."),
    ("源帧主体身份连续", "Preserve the same casting, face proportions, hair silhouette, wardrobe construction, footwear and material state from the source frame."),
    ("入体点硬锁", "Keep one weapon, one original entry point and one continuous wound line at the same body location."),
    ("武器入体/接触点", "Show exactly one coherent weapon contact or entry point at the body location specified by the story."),
    ("本镜已指定胸口/胸前", "Keep the weapon entry point on the upper chest."),
    ("脸部机检可核验", "Keep the primary face identifiable with a clear eye-nose-mouth triangle and facial contour, using a readable action angle rather than a posed portrait."),
    ("手部/肢体归属", "Assign every visible hand to the correct subject and arm; each human subject has two arms and at most two visible hands with natural wrist and contact geometry."),
    ("另一只手和武器的归属", "Keep the other hand and weapon ownership unambiguous; naturally occlude an unneeded hand."),
    ("共享角色定妆", "Use a consistent neutral character reference board with clean gray studio background and complete head-to-foot requested views."),
    ("道具尺度派生板", "Use a faceless hand or below-chin scale reference while keeping the prop structure complete and the subject anonymous."),
    ("道具主参考板", "Show the clean isolated prop on a neutral background with complete structure and no narrative action."),
    ("风格附件只提供", "Use the style attachment only for line, material, color grading, camera language and finish; keep character identity and scene content from their own references."),
    ("赛璐璐视觉语法", "Render the action climax with clear cel-shaded contours, graphic impact shapes, directional speed lines and short readable motion accents."),
    ("水墨视觉语法", "Render the action climax with dry-brush and ink-wash energy, tonal depth and controlled negative space along the attack direction."),
    ("经费在燃烧", "Render the action climax with subject-separating volumetric light, atmospheric depth, environmental reaction and short directional motion accents while faces and impact points stay clear."),
    ("每个主体只使用自己的身份参考", "Each subject uses only its own identity reference and remains in its assigned screen slot with unambiguous hand ownership."),
)


def _policy_guard_for_profile(value: Any, profile: Mapping[str, Any]) -> str:
    text = _one_line(value)
    if not text:
        return ""
    language = str(profile.get("language") or "zh")
    strategy = str(profile.get("negative_strategy") or "")
    if language == "en":
        for marker, replacement in _EN_POLICY_GUARDS:
            if marker in text:
                return replacement
    if strategy != "positive_only" or not _NEGATIVE_COMMAND_RE.search(text):
        return text
    positive_clauses = [
        clause.strip()
        for clause in re.split(r"[。；;]+", text)
        if clause.strip() and not _NEGATIVE_COMMAND_RE.search(clause)
    ]
    return "；".join(positive_clauses)


def _compile_parts(contract: Mapping[str, Any], profile: Mapping[str, Any], task: str) -> List[str]:
    language = str(profile.get("language") or "zh")
    english = language == "en"
    objective = _compact(contract.get("objective"), 180)
    subject = _compact(contract.get("subject"), 520 if task == "character_catalog" else 260)
    slots = _compact(contract.get("subject_slots"), 260)
    composition = _compact(_without_aspect_phrases(contract.get("composition")), 230)
    action = _compact(contract.get("action"), 260)
    scene = _compact(contract.get("scene"), 460 if task == "scene_asset" else 220)
    lighting = _compact(contract.get("lighting"), 150)
    mood = _compact(contract.get("mood"), 140)
    style = _compact(_without_aspect_phrases(contract.get("style")), 220)
    preserve = _dedupe(contract.get("preserve") or [], limit=5)
    policy_guards = _dedupe(
        _policy_guard_for_profile(item, profile)
        for item in (contract.get("policy_guards") or [])
        if _policy_guard_for_profile(item, profile)
    )[:12]
    references = normalize_references(contract.get("reference_inputs"))
    parts: List[str] = []

    if english:
        openings = {
            "character_catalog": "Create a neutral production character reference",
            "scene_asset": "Create a production environment reference",
            "prop_asset": "Create an isolated production asset reference",
            "style_anchor": "Create a neutral visual-style reference board",
            "shot_keyframe": "Create one production-ready story keyframe",
            "relay_edit": "Edit the supplied source frame; change only the stated action delta",
            "multi_subject": "Create one production-ready multi-subject story keyframe",
        }
        parts.append(openings[task] + (f": {objective}." if objective else "."))
        if subject:
            parts.append(f"Subject: {subject}.")
        if slots:
            parts.append(f"Subject layout: {slots}.")
        if action and task in {"shot_keyframe", "relay_edit", "multi_subject"}:
            parts.append(f"Frozen moment: {action}.")
        if composition:
            parts.append(f"Composition: {composition}.")
        if scene:
            parts.append(f"Environment: {scene}.")
        if lighting:
            parts.append(f"Lighting: {lighting}.")
        if mood:
            parts.append(f"Emotional focus: {mood}.")
        if style:
            parts.append(f"Visual style: {style}.")
        parts.extend(sentence + "." for sentence in _reference_role_sentences(references, language))
        if preserve:
            label = "Preserve exactly" if task == "relay_edit" else "Keep consistent"
            parts.append(f"{label}: {'; '.join(_compact(item, 130) for item in preserve)}.")
        parts.extend(_compact(item, 260) + "." for item in policy_guards)
    else:
        openings = {
            "character_catalog": "生成中性生产级角色参考图",
            "scene_asset": "生成生产级场景参考图",
            "prop_asset": "生成独立生产级资产参考图",
            "style_anchor": "生成中性视觉风格参考板",
            "shot_keyframe": "生成一张正式剧情关键帧",
            "relay_edit": "编辑已提交源帧，只改变本次动作增量",
            "multi_subject": "生成一张正式多人剧情关键帧",
        }
        parts.append(openings[task] + (f"：{objective}。" if objective else "。"))
        if subject:
            parts.append(f"主体：{subject}。")
        if slots:
            parts.append(f"主体布局：{slots}。")
        if action and task in {"shot_keyframe", "relay_edit", "multi_subject"}:
            parts.append(f"动作瞬间：{action}。")
        if composition:
            parts.append(f"构图：{composition}。")
        if scene:
            parts.append(f"场景：{scene}。")
        if lighting:
            parts.append(f"光影：{lighting}。")
        if mood:
            parts.append(f"情绪焦点：{mood}。")
        if style:
            parts.append(f"视觉风格：{style}。")
        parts.extend(sentence + "。" for sentence in _reference_role_sentences(references, language))
        if preserve:
            label = "必须保持不变" if task == "relay_edit" else "保持一致"
            parts.append(f"{label}：{'；'.join(_compact(item, 130) for item in preserve)}。")
        parts.extend(_compact(item, 260) + "。" for item in policy_guards)

    parts.extend(guard + ("." if english else "。") for guard in _conditional_guards(contract, task, language))
    params = contract.get("request_params") if isinstance(contract.get("request_params"), Mapping) else {}
    aspect = _one_line(params.get("aspect_ratio"))
    if profile.get("embed_aspect") and aspect:
        parts.append((f"Canvas: {aspect}." if english else f"画幅：{aspect}。"))
    return parts


def compile_image_prompt(contract: Mapping[str, Any], backend: Any = None) -> Dict[str, Any]:
    """Compile one canonical image contract into an auditable submit payload."""
    source = dict(contract or {})
    selected_backend = backend or source.get("backend")
    profile = backend_profile(selected_backend)
    task = task_profile(source.get("task_type") or source.get("mode"))["name"]
    source_contract = {
        key: source.get(key)
        for key in (
            "task_type", "objective", "subject", "subject_slots", "composition", "action",
            "scene", "lighting", "mood", "style", "preserve", "policy_guards", "exclude", "risk_flags",
        )
    }
    source_hash = _one_line(source.get("source_contract_sha256")) or _hash_mapping(source_contract)
    resolved, compiler_decisions, compression = resolve_contract_conflicts(source, profile, task)
    references = normalize_references(resolved.get("reference_inputs"))
    params = dict(resolved.get("request_params") or {})
    parts = _compile_parts({**resolved, "reference_inputs": references, "request_params": params}, profile, task)
    exclusions = normalize_exclusions(resolved.get("exclude") or [])
    negative_prompt = ""
    strategy = str(profile.get("negative_strategy") or "inline_constraints")
    if strategy == "inline_constraints" and exclusions:
        if profile.get("language") == "en":
            parts.append("Constraints: " + "; ".join(exclusions) + ".")
        else:
            parts.append("限制：" + "；".join(exclusions) + "。")
    elif strategy in {"separate_element_list", "parameter_no"}:
        negative_prompt = ", ".join(exclusions)
    elif strategy == "positive_only":
        parts.append(_positive_guard(task, str(profile.get("language") or "en")))

    prompt = " ".join(_one_line(part) for part in parts if _one_line(part)).strip()
    language = str(profile.get("language") or "zh")
    if language == "en" and _CJK_RE.search(prompt):
        language = "mixed"

    execution_context = {
        "backend": profile["backend"],
        "model": _one_line(source.get("model")),
        "channel": _one_line(source.get("channel")),
        "mode": _one_line(source.get("mode")) or task,
        "task_type": task,
        "target_path": _one_line(source.get("target_path")),
        "reference_inputs": references,
        "request_params": params,
    }
    payload: Dict[str, Any] = {
        "kind": KIND,
        "version": VERSION,
        "profile_version": PROFILE_VERSION,
        "profile": profile["name"],
        "backend": profile["backend"],
        "model": _one_line(source.get("model")),
        "channel": _one_line(source.get("channel")),
        "mode": execution_context["mode"],
        "task_type": task,
        "language": language,
        "negative_strategy": strategy,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "reference_inputs": references,
        "request_params": params,
        "source_contract_sha256": source_hash,
        "source_contract_text_sha256": _one_line(source.get("source_contract_text_sha256")),
        "execution_context_sha256": _hash_mapping(execution_context),
        "compiler_decisions": compiler_decisions,
    }
    request_to_hash = {
        key: payload.get(key)
        for key in (
            "kind", "version", "profile_version", "profile", "backend", "model", "channel",
            "mode", "task_type", "language", "negative_strategy", "prompt", "negative_prompt",
            "reference_inputs", "request_params", "source_contract_sha256", "execution_context_sha256",
        )
    }
    payload["compiled_request_sha256"] = _hash_mapping(request_to_hash)
    payload["metrics"] = {
        "prompt_chars": len(prompt),
        "negative_chars": len(negative_prompt),
        "clause_count": len([item for item in re.split(r"[。；;.!?]+", prompt) if item.strip()]),
        "reference_count": len(references),
        "estimated_text_tokens": max(1, (len(prompt) + len(negative_prompt) + 3) // 4),
        "constraint_compression": compression,
    }
    payload["lint"] = lint_compiled_prompt(payload)
    return payload


def compiled_request_hash(payload: Mapping[str, Any]) -> str:
    request_to_hash = {
        key: payload.get(key)
        for key in (
            "kind", "version", "profile_version", "profile", "backend", "model", "channel",
            "mode", "task_type", "language", "negative_strategy", "prompt", "negative_prompt",
            "reference_inputs", "request_params", "source_contract_sha256", "execution_context_sha256",
        )
    }
    return _hash_mapping(request_to_hash)


def lint_compiled_prompt(payload: Mapping[str, Any]) -> Dict[str, List[str]]:
    """Return deterministic request errors and advisory compactness warnings."""
    errors: List[str] = []
    warnings: List[str] = []
    prompt = _one_line(payload.get("prompt"))
    backend = normalize_backend(payload.get("backend"))
    profile = backend_profile(backend)
    task = _one_line(payload.get("task_type"))
    strategy = _one_line(payload.get("negative_strategy"))
    negative = _one_line(payload.get("negative_prompt"))
    refs = normalize_references(payload.get("reference_inputs"))
    params = payload.get("request_params") if isinstance(payload.get("request_params"), Mapping) else {}

    if not prompt:
        errors.append("empty_submit_prompt")
    if task not in TASK_TYPES:
        errors.append("missing_or_invalid_task_type")
    if task in {"shot_keyframe", "relay_edit", "multi_subject"} and not re.search(
        r"动作瞬间：|Frozen moment:", prompt
    ):
        errors.append("story_image_missing_single_frozen_moment")
    if task == "relay_edit" and not re.search(r"必须保持不变：|Preserve exactly:", prompt):
        errors.append("relay_edit_missing_preserve_contract")
    if backend == "flux" and (_NEGATIVE_COMMAND_RE.search(prompt) or negative):
        errors.append("flux_requires_positive_only_prompt")
    if strategy in {"inline_constraints", "positive_only"} and negative:
        errors.append("backend_negative_field_must_be_empty")
    if strategy in {"separate_element_list", "parameter_no"} and _NEGATIVE_COMMAND_RE.search(negative):
        errors.append("negative_field_contains_instruction_language")
    if _RAW_PATH_RE.search(prompt):
        errors.append("submit_prompt_leaks_internal_path_or_registry")
    if _FULL_CONTRACT_RE.search(prompt):
        errors.append("submit_prompt_leaks_full_production_contract")
    aspects = set(_ASPECT_RE.findall(prompt))
    requested_aspect = _one_line(params.get("aspect_ratio"))
    if requested_aspect and any(value != requested_aspect for value in aspects):
        errors.append("prompt_aspect_conflicts_with_request_params")
    referenced_indexes = [int(item) for item in _IMAGE_INDEX_RE.findall(prompt)]
    if referenced_indexes and max(referenced_indexes) > len(refs):
        errors.append("prompt_mentions_unattached_reference_index")
    if payload.get("compiled_request_sha256") and _one_line(payload.get("compiled_request_sha256")) != compiled_request_hash(payload):
        errors.append("compiled_request_sha256_mismatch")
    if not re.fullmatch(r"[0-9a-f]{64}", _one_line(payload.get("source_contract_sha256"))):
        errors.append("source_contract_sha256_invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", _one_line(payload.get("execution_context_sha256"))):
        errors.append("execution_context_sha256_invalid")

    if len(prompt) > int(profile.get("advisory_char_limit") or 1400):
        warnings.append(
            f"submit_prompt_verbose:{len(prompt)}>{profile.get('advisory_char_limit')}"
        )
    clauses = len([item for item in re.split(r"[。；;.!?]+", prompt) if item.strip()])
    if clauses > 16:
        warnings.append(f"submit_prompt_many_clauses:{clauses}>16")
    if _one_line(payload.get("language")) == "mixed":
        warnings.append("backend_profile_contains_mixed_language")
    if task in {"character_catalog", "scene_asset", "prop_asset", "style_anchor"} and re.search(
        r"剧情高潮|打斗连招|完整动作链|story climax|action sequence", prompt, re.I
    ):
        warnings.append("catalog_prompt_contains_story_action")
    return {"errors": _dedupe(errors), "warnings": _dedupe(warnings)}


def render_compiled_markdown(payload: Mapping[str, Any]) -> str:
    meta = (
        f"kind={payload.get('kind')}; version={payload.get('version')}; "
        f"profile_version={payload.get('profile_version')}; profile={payload.get('profile')}; "
        f"backend={payload.get('backend')}; model={payload.get('model')}; channel={payload.get('channel')}; "
        f"mode={payload.get('mode')}; task_type={payload.get('task_type')}; "
        f"language={payload.get('language')}; negative_strategy={payload.get('negative_strategy')}; "
        f"source_contract_sha256={payload.get('source_contract_sha256')}; "
        f"source_contract_text_sha256={payload.get('source_contract_text_sha256')}; "
        f"execution_context_sha256={payload.get('execution_context_sha256')}; "
        f"compiled_request_sha256={payload.get('compiled_request_sha256')}"
    )
    params = json.dumps(payload.get("request_params") or {}, ensure_ascii=False, sort_keys=True)
    refs = json.dumps(payload.get("reference_inputs") or [], ensure_ascii=False, sort_keys=True)
    metrics = json.dumps(payload.get("metrics") or {}, ensure_ascii=False, sort_keys=True)
    lines = [
        COMPILED_HEADING,
        f"**编译元数据**：{meta}",
        f"**后端请求参数**：`{params}`",
        f"**参考附件角色**：`{refs}`",
        f"**编译度量**：`{metrics}`",
        "```text",
        str(payload.get("prompt") or "").strip(),
        "```",
    ]
    negative = _one_line(payload.get("negative_prompt"))
    if negative:
        lines += [
            "",
            "### 后端图片负向字段（单独提交，不拼入主 prompt）",
            "```text",
            negative,
            "```",
        ]
    return "\n".join(lines)


_COMPILED_RE = re.compile(
    r"###\s*后端编译提交\s*image\s*prompt\s*\n"
    r"\*\*编译元数据\*\*[：:]\s*([^\n]+)\n"
    r"\*\*后端请求参数\*\*[：:]\s*`([^\n`]*)`\n"
    r"\*\*参考附件角色\*\*[：:]\s*`([^\n`]*)`\n"
    r"\*\*编译度量\*\*[：:]\s*`([^\n`]*)`\n"
    r"```(?:text)?\s*\n?(.*?)```",
    re.I | re.S,
)
_NEGATIVE_RE = re.compile(
    r"###\s*后端图片负向字段[^\n]*\n```(?:text)?\s*\n?(.*?)```",
    re.I | re.S,
)


def parse_compiled_markdown(section: str) -> Optional[Dict[str, Any]]:
    match = _COMPILED_RE.search(section or "")
    if not match:
        return None
    meta: Dict[str, str] = {}
    for piece in match.group(1).split(";"):
        if "=" not in piece:
            continue
        key, value = piece.split("=", 1)
        meta[key.strip()] = value.strip()
    try:
        params = json.loads(match.group(2) or "{}")
    except json.JSONDecodeError:
        params = {}
    try:
        refs = json.loads(match.group(3) or "[]")
    except json.JSONDecodeError:
        refs = []
    try:
        metrics = json.loads(match.group(4) or "{}")
    except json.JSONDecodeError:
        metrics = {}
    negative = _NEGATIVE_RE.search(section or "")
    payload: Dict[str, Any] = {
        **meta,
        "version": int(meta.get("version", "0")) if meta.get("version", "").isdigit() else 0,
        "request_params": params,
        "reference_inputs": refs,
        "metrics": metrics,
        "prompt": match.group(5).strip(),
        "negative_prompt": negative.group(1).strip() if negative else "",
    }
    return payload


def lint_compiled_section(
    section: str,
    *,
    expected_backend: Any = None,
    allowed_tasks: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Validate the compiled block embedded beside a complete image contract."""
    payload = parse_compiled_markdown(section)
    if payload is None:
        return {
            "payload": None,
            "errors": ["missing_compiled_image_request"],
            "warnings": [],
        }
    errors: List[str] = []
    warnings: List[str] = []
    for key in (
        "kind", "version", "profile_version", "profile", "backend", "mode",
        "task_type", "language", "negative_strategy", "source_contract_sha256",
        "source_contract_text_sha256", "execution_context_sha256",
        "compiled_request_sha256",
    ):
        if payload.get(key) in (None, ""):
            errors.append(f"compiled_metadata_missing:{key}")
    if payload.get("kind") != KIND:
        errors.append(f"compiled_kind_invalid:{payload.get('kind')}")
    if payload.get("version") != VERSION:
        errors.append(f"compiled_version_unsupported:{payload.get('version')}")
    actual_backend = normalize_backend(payload.get("backend"))
    wanted_backend = normalize_backend(expected_backend) if _one_line(expected_backend) else ""
    if wanted_backend and actual_backend != wanted_backend:
        errors.append(f"compiled_backend_mismatch:{actual_backend}!={wanted_backend}")
    allowed = {task_profile(item)["name"] for item in (allowed_tasks or [])}
    actual_task = task_profile(payload.get("task_type"))["name"]
    if allowed and actual_task not in allowed:
        errors.append(f"compiled_task_type_mismatch:{actual_task}")
    source_text_hash = _one_line(payload.get("source_contract_text_sha256"))
    if source_text_hash and source_text_hash != sha256_text(section_without_compiled(section)):
        errors.append("compiled_source_contract_stale")
    lint = lint_compiled_prompt(payload)
    errors.extend(lint.get("errors") or [])
    warnings.extend(lint.get("warnings") or [])
    return {
        "payload": payload,
        "errors": _dedupe(errors),
        "warnings": _dedupe(warnings),
    }


def compile_image_section(section: str, **overrides: Any) -> Dict[str, Any]:
    """Compile a full Markdown section for a concrete runner target."""
    contract = contract_from_section(section, **overrides)
    return compile_image_prompt(contract, overrides.get("backend"))


__all__ = [
    "COMPILED_HEADING",
    "KIND",
    "PROFILE_VERSION",
    "TASK_TYPES",
    "VERSION",
    "backend_profile",
    "compile_image_prompt",
    "compile_image_section",
    "compiled_request_hash",
    "contract_from_section",
    "infer_task_type",
    "lint_compiled_prompt",
    "lint_compiled_section",
    "normalize_backend",
    "normalize_exclusions",
    "normalize_references",
    "parse_compiled_markdown",
    "render_compiled_markdown",
    "section_without_compiled",
    "sha256_text",
    "task_profile",
]
