#!/usr/bin/env python3
"""Recoverable n2d video batch runner.

The runner keeps a stable manifest in `生产数据/video_batch_<episode>_<range>.json`
and drives the expensive image2video step from that manifest. It is deliberately
small: stage-specific creative decisions still live in n2d-video prompts and
gates; this script handles state, subprocess calls, downloads, QC, telemetry,
and progress updates. The costly submit command runs video_preflight by default
immediately before invoking the backend.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
SKILLS_DIR = SCRIPT_DIR.parents[1]
REPO_ROOT = SKILLS_DIR.parent
COMMON_DIR = SKILLS_DIR / "n2d" / "_lib"
DASHBOARD_PY = SKILLS_DIR / "n2d-dashboard" / "scripts" / "dashboard.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from n2d_const import PRODUCTION_MODE_DEFAULT

try:
    from n2d_route import normalize_episode, parse_progress
except Exception:  # pragma: no cover
    normalize_episode = lambda value: str(value).strip()  # type: ignore[assignment]
    parse_progress = None  # type: ignore[assignment]

from n2d_handoff import check_identity_handoff
from video_prompt_compiler import (
    compile_video_prompt,
    normalize_backend as normalize_prompt_backend,
    parse_compiled_markdown,
)
import video_execution_adapter as execution_adapter_v2
import native_av_sidecar
import video_qc

try:
    from flow_telemetry import record_milestone as _record_flow_milestone_impl
except Exception:  # pragma: no cover - observability never blocks production
    _record_flow_milestone_impl = None


def _record_flow_milestone(root: Path, episode: str, milestone: str, **extra: Any) -> None:
    if _record_flow_milestone_impl is None:
        return
    try:
        _record_flow_milestone_impl(root, milestone, episode=episode, stage="video", extra=extra)
    except Exception:
        pass

try:
    from n2d_platform_profiles import (
        anchor_consumption_plan,
        quantize_video_duration,
        select_video_frame_strategy,
        video_backend_frame_control,
    )
except ImportError:
    anchor_consumption_plan = lambda m, c, **kw: {}  # type: ignore
    quantize_video_duration = lambda d, m, c=None, **kw: {  # type: ignore
        "edit_target_sec": float(d or 0), "backend_request_sec": submit_duration(d),
        "backend_surplus_sec": max(0.0, float(submit_duration(d)) - float(d or 0)),
        "trim_mode": "trim_tail", "requires_split": False,
    }
    select_video_frame_strategy = lambda m, c=None, **kw: {"strategy": "first_only"}  # type: ignore
    video_backend_frame_control = lambda m, c: {}  # type: ignore


def aspect_ratio(root: Path) -> str:
    """画幅 选择点（绝不写死，对齐 选择点与偏好.md「画幅」与 compose.sh / 图侧 runner）：
    env N2D_ASPECT/ASPECT(9:16|16:9) > _设置.md「画幅」> 默认 9:16 竖屏。缺 _lib 时降级正则扫 _设置.md。"""
    env = (os.environ.get("N2D_ASPECT") or os.environ.get("ASPECT") or "").strip()
    if env in {"9:16", "16:9"}:
        return env
    try:
        import settings as _settings  # type: ignore
        val = (_settings.get_setting(str(root), "画幅", "") or "").replace(" ", "")
        if "16:9" in val:
            return "16:9"
        if "9:16" in val:
            return "9:16"
    except Exception:
        pass
    try:
        p = root / "_设置.md"
        text = p.read_text(encoding="utf-8") if p.is_file() else ""
    except Exception:
        text = ""
    if re.search(r"画幅\s*[:：]\s*16\s*[:：]?\s*9", text):
        return "16:9"
    return "9:16"

CLIP_HEADING_RE = re.compile(r"^##\s*Clip[_\s]*(\d+)(?:（([^）]+)）)?", re.MULTILINE)
FIRST_FRAME_RE = re.compile(r"\*\*首帧\*\*[^`]*`([^`]+\.png)`")
END_FRAME_RE = re.compile(r"\*\*尾帧\*\*[^`]*`([^`]+\.png)`")
ZH_PROMPT_RE = re.compile(r"###\s*视频 prompt（中文[^`]*```(?:\w+)?\s*(.*?)```", re.DOTALL)
FENCE_RE = re.compile(r"```(?:\w+)?\s*(.*?)```", re.DOTALL)
DURATION_RE = re.compile(r"时长\s*([0-9]+(?:\.[0-9]+)?)\s*s", re.IGNORECASE)
FILENAME_UNSAFE_RE = re.compile(r"[\\/:*?\"<>|\r\n\t]+")
VIDEO_SHOT_PLAN_THRESHOLD_SEC = 12.0
VIDEO_SHOT_HARD_MAX_SEC = 15.0
VIDEO_SHOT_TARGET_SEC = 6.0


def production_dir(root: Path) -> Path:
    return root / "生产数据"


def formal_video_dir(root: Path, episode: str) -> Path:
    return root / "出视频" / episode / "视频"


def prompt_pack_path(root: Path, episode: str) -> Path:
    return root / "出视频" / episode / "prompt" / "01_clips.md"


def batch_id(start: int, end: int) -> str:
    return f"{start:02d}_{end:02d}"


def manifest_path(root: Path, episode: str, start: int, end: int) -> Path:
    return production_dir(root) / f"video_batch_{episode}_{batch_id(start, end)}.json"


def stable_prompt_dir(root: Path, episode: str, start: int, end: int) -> Path:
    return production_dir(root) / "video_batches" / episode / batch_id(start, end) / "prompts"


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dialogue_fact_contract_path(root: Path, episode: str) -> Path:
    return production_dir(root) / f"dialogue_fact_contract_{episode}.json"


def _base_clip_id(value: Any) -> str:
    match = re.search(r"Clip[_\s-]?(\d+)", str(value or ""), re.IGNORECASE)
    return f"Clip_{int(match.group(1)):02d}" if match else str(value or "").strip()


def _manifest_root(manifest: Dict[str, Any]) -> Optional[Path]:
    raw = manifest.get("_root") or manifest.get("root")
    return Path(str(raw)).resolve() if raw else None


DIALOGUE_FACT_REQUIRED_TOKENS = (
    "native_speech",
    "native_av",
    "原生音画",
    "画内角色对白",
    "台词+口型",
    "三轨音频",
    "三轨修补",
)


def _requires_dialogue_fact_contract(prompt: str) -> bool:
    return any(token in prompt for token in DIALOGUE_FACT_REQUIRED_TOKENS)


def _dialogue_fact_contract_row(root: Path, episode: str, clip: str) -> Optional[Dict[str, Any]]:
    path = dialogue_fact_contract_path(root, episode)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("kind") != "n2d_dialogue_fact_contract":
        return None
    wanted = _base_clip_id(clip)
    rows = data.get("clips") if isinstance(data.get("clips"), list) else []
    return next((r for r in rows if isinstance(r, dict) and _base_clip_id(r.get("clip")) == wanted), None)


def _has_character_dialogue(row: Optional[Dict[str, Any]]) -> bool:
    if not row:
        return False
    indices = row.get("allowed_character_dialogue_indices")
    if isinstance(indices, list) and any(str(v).strip() for v in indices):
        return True
    for key in ("allowed_character_dialogue", "allowed_dialogue"):
        values = row.get(key)
        if not isinstance(values, list):
            continue
        for entry in values:
            if isinstance(entry, dict) and str(entry.get("text") or "").strip():
                return True
    return False


def _requests_native_speech(prompt: str) -> bool:
    text = prompt or ""
    native_line = re.compile(
        r"(?:native_audio_policy|speech_policy|audio_intent)\s*=\s*native_speech\b|"
        r"\bmode\s*=\s*native_av\b|"
        r"(?<!no_)\bnative_speech\b|"
        r"台词[+、]口型由原生音画后端生成",
        re.IGNORECASE,
    )
    conditional_tokens = (
        "若 route.",
        "若route.",
        "若 ",
        "如果",
        "非 native_speech",
        "非native_speech",
        "native_speech 镜",
        "native_speech镜",
    )
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or not native_line.search(line):
            continue
        if any(token in line for token in conditional_tokens):
            continue
        return True
    return False


MULTIMODAL_MODEL_VERSIONS = {
    "seedance2.0",
    "seedance2.0fast",
    "seedance2.0_vip",
    "seedance2.0fast_vip",
}
DEFAULT_DREAMINA_MODEL_VERSION = "seedance2.0fast"
HIGH_QUALITY_DREAMINA_MODEL_VERSION = "seedance2.0_vip"
AUTO_MODEL_VERSION_VALUES = {"", "auto", "default", "按预算", "预算自动"}
AUTO_RESOLUTION_VALUES = {"", "auto", "default", "按预算", "预算自动"}


def _project_setting(root: Path, key: str, default: str = "") -> str:
    try:
        import settings as _settings  # type: ignore
        return str(_settings.get_setting(str(root), key, default) or default).strip()
    except Exception:
        pass
    try:
        text = (root / "_设置.md").read_text(encoding="utf-8")
    except Exception:
        return default
    pattern = re.compile(rf"^\s*-?\s*{re.escape(key)}\s*[:：]\s*([^#\n]+)", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip() if match else default


def video_budget_tier(root: Path) -> str:
    value = _project_setting(root, "出视频规格", "预算充足")
    if "充足" in value:
        return "预算充足"
    if "不够" in value or "不足" in value:
        return "预算不够"
    return "预算一般"


def resolve_video_resolution(root: Path, requested: Optional[str], budget_tier: str) -> str:
    value = str(requested or "").strip()
    if value and value.lower() not in AUTO_RESOLUTION_VALUES:
        return value
    explicit = _project_setting(root, "视频分辨率", "")
    if explicit:
        return explicit
    return "720p"


def resolve_base_dreamina_model_version(root: Path, requested: Optional[str], budget_tier: str) -> str:
    value = str(requested or "").strip()
    if value and value.lower() not in AUTO_MODEL_VERSION_VALUES:
        return value
    return HIGH_QUALITY_DREAMINA_MODEL_VERSION if budget_tier == "预算充足" else DEFAULT_DREAMINA_MODEL_VERSION


def _is_high_value_clip(item: Mapping[str, Any], prompt: str) -> bool:
    text = "\n".join(
        str(v or "")
        for v in (
            item.get("clip"),
            item.get("heading"),
            item.get("target"),
            prompt,
        )
    )
    if re.search(r"quality[_\s-]*tier\s*[:=]\s*(?:high|release|pro)\b", text, re.IGNORECASE):
        return True
    if re.search(r"(?:hero[_\s-]*multi|signature[_\s-]*scene|keyshot|final[_\s-]*shot)", text, re.IGNORECASE):
        return True
    return any(
        token in text
        for token in (
            "🔑",
            "关键镜",
            "英雄镜",
            "名场面",
            "高光",
            "爽点",
            "反转",
            "钩子",
            "封面候选",
            "开场钩",
            "高潮",
            "真相揭示",
            "公开对质",
            "关系转折",
            "动作高潮",
            "人脸特写",
        )
    )


def select_dreamina_model_version(base_model: str, budget_tier: str, item: Mapping[str, Any],
                                  prompt: str) -> str:
    base = str(base_model or DEFAULT_DREAMINA_MODEL_VERSION).strip()
    if budget_tier == "预算充足":
        return HIGH_QUALITY_DREAMINA_MODEL_VERSION
    if _is_high_value_clip(item, prompt) and base in {
        DEFAULT_DREAMINA_MODEL_VERSION,
        "seedance2.0",
        "seedance2.0fast_vip",
        *AUTO_MODEL_VERSION_VALUES,
    }:
        return HIGH_QUALITY_DREAMINA_MODEL_VERSION
    return base


def _effective_dreamina_model_version(item: Mapping[str, Any], manifest: Mapping[str, Any],
                                      prompt: str = "") -> str:
    budget = str(item.get("video_budget_tier") or manifest.get("video_budget_tier") or "").strip()
    root = _manifest_root(dict(manifest)) if not budget else None
    if not budget and root:
        budget = video_budget_tier(root)
    if not budget:
        budget = "预算充足"
    base = str(item.get("model_version") or manifest.get("model_version") or DEFAULT_DREAMINA_MODEL_VERSION).strip()
    return select_dreamina_model_version(base, budget, item, prompt)


def _multimodal_model_version(manifest: Mapping[str, Any], item: Optional[Mapping[str, Any]] = None,
                              prompt: str = "") -> str:
    """Return a Dreamina multimodal2video-compatible model version."""
    value = _effective_dreamina_model_version(item or {}, manifest, prompt)
    return value if value in MULTIMODAL_MODEL_VERSIONS else HIGH_QUALITY_DREAMINA_MODEL_VERSION


def _guard_native_speech_contract(prompt: str, item: Dict[str, Any], manifest: Dict[str, Any]) -> None:
    root = _manifest_root(manifest)
    episode = str(manifest.get("episode") or "")
    if not root or not episode or not _requests_native_speech(prompt):
        return
    clip = str(item.get("clip") or "")
    row = _dialogue_fact_contract_row(root, episode, clip)
    if row is None:
        return
    if _has_character_dialogue(row):
        return
    raise RuntimeError(
        "native_speech route has no allowed character dialogue before paid video submit: "
        f"{episode} {clip}. This clip is narration/screen-text only, so narration belongs to compose. "
        "Rerun n2d-model-router/video prompt with native_audio_policy=none/no_native_speech or ambience-only "
        "before spending credits."
    )


def _dialogue_fact_prompt_suffix(root: Path, episode: str, clip: str) -> str:
    row = _dialogue_fact_contract_row(root, episode, clip)
    if not row:
        return ""
    wanted = _base_clip_id(clip)
    path = dialogue_fact_contract_path(root, episode)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    character_allowed = row.get("allowed_character_dialogue")
    if not isinstance(character_allowed, list):
        character_allowed = row.get("allowed_dialogue") if isinstance(row.get("allowed_dialogue"), list) else []
    dialogue_lines = []
    for entry in character_allowed:
        if not isinstance(entry, dict):
            continue
        dialogue_lines.append(f"{entry.get('index')}. {entry.get('role')}: {entry.get('text')}")
    narration_lines = []
    for entry in row.get("allowed_narration") or []:
        if not isinstance(entry, dict):
            continue
        narration_lines.append(f"{entry.get('index')}. 旁白: {entry.get('text')}")
    screen_text_lines = []
    for entry in row.get("screen_text_lines") or []:
        if not isinstance(entry, dict):
            continue
        text = entry.get("text") or ""
        render_policy = entry.get("render_policy") or "compose_overlay_only"
        purpose = entry.get("purpose") or ""
        if text:
            screen_text_lines.append(f"{text}（{render_policy}; {purpose}）")
    facts = []
    forbidden = []
    for fact in data.get("facts") or []:
        if not isinstance(fact, dict):
            continue
        key = str(fact.get("key") or "")
        character = str(fact.get("character") or "")
        canonical = str(fact.get("canonical") or "")
        if (
            key in {"age", "height", "spiritual_root", "daily_water_trips", "night_water_trip"}
            and canonical
            and (character == "贺平生" or character == "剧情账本")
        ):
            facts.append(f"{character}.{key}={canonical}")
        forbidden.extend(str(v) for v in fact.get("forbidden_values") or [] if str(v))
    return "\n".join([
        "对白事实锁 / Dialogue-Fact Contract:",
        f"- clip: {wanted}; allowed_voiceover_indices={row.get('allowed_voiceover_indices')}",
        f"- allowed_narration_indices={row.get('allowed_narration_indices')}; allowed_character_dialogue_indices={row.get('allowed_character_dialogue_indices')}",
        "- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。",
        "- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。",
        *[f"- dialogue: {line}" for line in dialogue_lines],
        *[f"- narration_for_compose_only: {line}" for line in narration_lines],
        "- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.",
        "- screen_text_overlay: " + (" | ".join(screen_text_lines) if screen_text_lines else "none; 不要让视频模型生成文字"),
        "- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。",
        "- canonical_facts: " + ("; ".join(facts) if facts else "see character cards"),
        "- forbidden_fact_values: " + (", ".join(sorted(set(forbidden))) if forbidden else "none"),
        "- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。",
    ]).strip()


def _append_dialogue_fact_contract(prompt: str, item: Dict[str, Any], manifest: Dict[str, Any], *,
                                  enforce_submit_guard: bool = True) -> str:
    root = _manifest_root(manifest)
    episode = str(manifest.get("episode") or "")
    if not root or not episode:
        return prompt
    if enforce_submit_guard:
        _guard_native_speech_contract(prompt, item, manifest)
    clip = str(item.get("clip") or "")
    if "Dialogue-Fact Contract" in prompt or "对白事实锁" in prompt:
        return prompt
    suffix = _dialogue_fact_prompt_suffix(root, episode, clip)
    if not suffix:
        if _requires_dialogue_fact_contract(prompt):
            raise RuntimeError(
                "dialogue fact contract missing before paid video submit: "
                f"{episode} {clip}. Run `python3 skills/n2d-review/scripts/dialogue_fact_guard.py "
                f"{root} {episode} --write` and regenerate video prompts before spending credits."
            )
        return prompt
    return f"{prompt.rstrip()}\n\n{suffix}"


def append_jsonl(path: Path, item: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def clip_key(number: int) -> str:
    return f"Clip_{number:02d}"


def _filename_part(text: str, *, fallback: str = "clip") -> str:
    value = FILENAME_UNSAFE_RE.sub("_", str(text or "")).strip(" ._-")
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"_+", "_", value).strip(" ._-")
    return (value or fallback)[:80]


def _title_from_heading(heading: str) -> str:
    match = re.search(r"（([^）]+)）", heading or "")
    body = match.group(1) if match else heading
    parts = [p.strip() for p in re.split(r"[·|]", body) if p.strip()]
    useful: List[str] = []
    for part in parts:
        if re.search(r"时长\s*[0-9]", part, re.IGNORECASE):
            continue
        if re.search(r"\bEP\d+[_-]?CLIP\d+\b", part, re.IGNORECASE):
            continue
        if re.fullmatch(r"镜头\s*", part):
            continue
        useful.append(part)
    return useful[-1] if useful else ""


def _title_from_image_rel(image_rel: str) -> str:
    stem = Path(str(image_rel or "")).stem
    stem = re.sub(r"^Clip[_\s-]?\d+[_\s-]*", "", stem, flags=re.IGNORECASE)
    return stem


def video_target_name(number: int, heading: str, image_rel: str) -> str:
    """Formal MP4 targets use the physical manifest clip id, not the source PNG id."""
    title = _title_from_heading(heading) or _title_from_image_rel(image_rel)
    return f"{clip_key(number)}_{_filename_part(title)}.mp4"


def _duration_from_heading(text: str) -> Optional[float]:
    match = DURATION_RE.search(text or "")
    return float(match.group(1)) if match else None


def submit_duration(story_duration: Optional[float], minimum: int = 4, maximum: int = 15) -> int:
    """Legacy Dreamina integer-duration wrapper for v1 prompt packs.

    v2 manifests use `quantize_video_duration` with the actual backend/model.
    Keeping this helper avoids silently changing resumable v1 batches.
    """
    if story_duration is None:
        return minimum
    return max(minimum, min(maximum, int(math.ceil(story_duration))))


def backend_duration_plan(
    edit_target: Optional[float],
    backend: str,
    *,
    model_version: Optional[str] = None,
    frame_strategy: Optional[str] = None,
) -> Dict[str, Any]:
    return dict(quantize_video_duration(
        edit_target,
        backend,
        "",
        model_version=model_version,
        mode=frame_strategy,
    ))


def _story_duration(item: Mapping[str, Any]) -> Optional[float]:
    value = item.get("story_duration")
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"\d+(?:\.\d+)?", value)
        if match:
            return float(match.group(0))
    return None


def needs_physical_video_shot_split(item: Mapping[str, Any]) -> bool:
    duration = _story_duration(item)
    return duration is not None and duration > VIDEO_SHOT_PLAN_THRESHOLD_SEC


def direct_submit_forbidden(item: Mapping[str, Any]) -> bool:
    duration = _story_duration(item)
    if duration is None or duration <= VIDEO_SHOT_HARD_MAX_SEC:
        return False
    # Split relay / physical video-shot parts are already safe because each part
    # carries its own short story_duration and a parent pointer.
    if item.get("relay_parent") or item.get("split_relay_prompt_guard") or item.get("video_shot_segment"):
        return False
    return True


def video_shot_split_plan(item: Mapping[str, Any]) -> Dict[str, Any]:
    duration = _story_duration(item)
    if duration is None:
        return {
            "required": False,
            "reason": "missing_story_duration",
            "threshold_sec": VIDEO_SHOT_PLAN_THRESHOLD_SEC,
            "hard_max_sec": VIDEO_SHOT_HARD_MAX_SEC,
        }
    count = max(2, int(math.ceil(duration / VIDEO_SHOT_TARGET_SEC))) if duration > VIDEO_SHOT_PLAN_THRESHOLD_SEC else 1
    return {
        "required": duration > VIDEO_SHOT_PLAN_THRESHOLD_SEC,
        "story_duration_sec": round(duration, 3),
        "threshold_sec": VIDEO_SHOT_PLAN_THRESHOLD_SEC,
        "hard_max_sec": VIDEO_SHOT_HARD_MAX_SEC,
        "target_video_shot_sec": VIDEO_SHOT_TARGET_SEC,
        "recommended_parts": count,
        "direct_submit_allowed": duration <= VIDEO_SHOT_HARD_MAX_SEC,
        "policy": "split editorial camera changes first; then keep each continuous generation take within the selected backend window",
    }


def _extract_prompt(block: str) -> str:
    compiled = parse_compiled_markdown(block)
    if compiled:
        prompt = str(compiled.get("prompt") or "").strip()
        if not prompt:
            raise ValueError("compiled video submit prompt is empty")
        return prompt
    match = ZH_PROMPT_RE.search(block)
    if match:
        return match.group(1).strip()
    fallback = FENCE_RE.search(block)
    if fallback:
        return fallback.group(1).strip()
    raise ValueError("clip block has no fenced video prompt")


def split_clip_blocks(text: str) -> List[Tuple[int, str, str]]:
    matches = list(CLIP_HEADING_RE.finditer(text))
    blocks: List[Tuple[int, str, str]] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        number = int(match.group(1))
        heading = match.group(0).strip()
        blocks.append((number, heading, text[start:end]))
    return blocks


def parse_prompt_pack(root: Path, episode: str, start: int, end: int) -> List[Dict[str, Any]]:
    text = prompt_pack_path(root, episode).read_text(encoding="utf-8")
    out: List[Dict[str, Any]] = []
    for number, heading, block in split_clip_blocks(text):
        if number < start or number > end:
            continue
        first = FIRST_FRAME_RE.search(block)
        if not first:
            raise ValueError(f"{clip_key(number)} missing **首帧** PNG path")
        image_rel = first.group(1).strip()
        image = (root / image_rel).resolve() if not Path(image_rel).is_absolute() else Path(image_rel)
        
        last = END_FRAME_RE.search(block)
        end_image_rel = last.group(1).strip() if last else None
        end_image = (root / end_image_rel).resolve() if end_image_rel and not Path(end_image_rel).is_absolute() else (Path(end_image_rel) if end_image_rel else None)

        compiled = parse_compiled_markdown(block)
        prompt = _extract_prompt(block)
        target = video_target_name(number, heading, image_rel)
        story_duration = _duration_from_heading(heading) or _duration_from_heading(block)
        compiled_duration = (
            dict(compiled.get("duration_plan") or {})
            if isinstance(compiled, Mapping) and isinstance(compiled.get("duration_plan"), Mapping)
            else {}
        )
        edit_target = compiled_duration.get("edit_target_sec") or story_duration
        backend_request = compiled_duration.get("backend_request_sec")
        frame_strategy = str((compiled or {}).get("frame_strategy") or "legacy_auto").strip().lower()
        if not backend_request and compiled:
            # compiled pack 缺 duration_plan 但已知后端：按该后端真实档位量化，
            # 不再落到后端无关的 [4,15] clamp——对即梦 image2video(≤5s)/Veo(≤8s)
            # 那个 clamp 可请求到 15s，是真实越界隐患。纯 v1 legacy pack（无 compiled）
            # 保持原兜底，避免悄悄改变可续跑的旧批次。
            compiled_backend = str(compiled.get("backend") or "").strip()
            if compiled_backend and edit_target is not None:
                compiled_duration = backend_duration_plan(
                    edit_target,
                    compiled_backend,
                    frame_strategy=str(compiled.get("mode") or "") or None,
                )
                backend_request = compiled_duration.get("backend_request_sec")
        out.append({
            "clip": clip_key(number),
            "heading": heading,
            "image": str(image),
            "image_rel": image_rel,
            "end_image": str(end_image) if end_image else None,
            "end_image_rel": end_image_rel,
            "target": target,
            "story_duration": story_duration,
            "edit_target_duration": edit_target,
            "duration_plan": compiled_duration,
            "submit_duration": backend_request or submit_duration(story_duration),
            "speed_mode": "trim",
            "frame_strategy": frame_strategy,
            "prompt_text": prompt,
            "prompt_source_kind": "compiled_submit_prompt" if compiled else "legacy_zh_prompt",
            "prompt_compiler": {
                key: compiled.get(key)
                for key in (
                    "kind", "version", "profile_version", "profile", "backend", "mode",
                    "language", "native_audio_policy", "source_contract_sha256", "frame_strategy",
                )
            } if compiled else None,
            "negative_prompt": str(compiled.get("negative_prompt") or "") if compiled else "",
            "status": "prepared",
        })
    expected = set(range(start, end + 1))
    got = {int(item["clip"].split("_")[1]) for item in out}
    missing = sorted(expected - got)
    if missing:
        raise ValueError("missing clip prompt blocks: " + ", ".join(clip_key(n) for n in missing))
    return out


def _clip_number(item: Dict[str, Any]) -> Optional[int]:
    m = re.search(r"(\d+)", str(item.get("clip") or ""))
    return int(m.group(1)) if m else None


def _base_clip_id(value: Any) -> str:
    m = re.search(r"Clip[_-]?(\d+)", str(value or ""), re.IGNORECASE)
    if m:
        return clip_key(int(m.group(1)))
    m = re.search(r"(\d+)", str(value or ""))
    return clip_key(int(m.group(1))) if m else str(value or "")


def attach_multiframe(root: Path, item: Dict[str, Any], prompt_text: str,
                      anchors_by_clip: Dict[int, Dict[str, Any]]) -> bool:
    """If the clip has valid in-range mid-anchors, attach multiframe2video fields to the item.
    Returns True if attached, False if skipped or failed (needs fallback)."""
    num = _clip_number(item)
    info = anchors_by_clip.get(num) if num is not None else None
    if not info:
        return False
    split = _consumable_anchor_rows(info)
    if not split:
        return False
    end_rel = item.get("end_image_rel")
    if not (end_rel and item.get("end_image") and Path(item["end_image"]).is_file()):
        item["multiframe_skip"] = "no end frame; multiframe chain needs a terminal keyframe"
        return False
    duration = item.get("story_duration") or info.get("duration")
    if not isinstance(duration, (int, float)):
        item["multiframe_skip"] = "no clip duration to derive segment timing"
        return False
    split.sort(key=lambda x: float(x[0]))
    anchor_times = [float(t) for t, _, _ in split]
    try:
        seg_durs = multiframe_segments(float(duration), anchor_times)
    except ValueError as exc:
        item["multiframe_skip"] = str(exc)
        return False
    images_rel = [item["image_rel"]] + [png for _, png, _ in split] + [end_rel]
    images_abs = [str((root / r).resolve()) if not Path(r).is_absolute() else r for r in images_rel]
    missing = [r for r, a in zip(images_rel, images_abs) if not Path(a).is_file()]
    if missing:
        item["multiframe_skip"] = "anchor/keyframe PNG not yet generated: " + ", ".join(missing)
        return False
    head = prompt_text.splitlines()[0].strip() if prompt_text.strip() else ""
    last_dest = (info.get("end_state") or "").strip() or "承接进行中的动作，停在尾帧落幅"
    seg_prompts = []
    dests = [h for _, _, h in split] + [last_dest]
    for hint in dests:
        seg_prompts.append((hint or head or "continue the motion smoothly").strip()[:200])
    item["mode_backend"] = "multiframe2video"
    item["anchor_consumption_mode"] = "native_multiframe"
    item["multiframe_images"] = images_abs
    item["multiframe_images_rel"] = images_rel
    item["multiframe_segment_durations"] = seg_durs
    item["multiframe_segment_prompts"] = seg_prompts
    # multiframe2video uses per-transition durations instead of the generic
    # image2video --duration cap. Keep audit/log duration aligned with the
    # native timeline we actually submit.
    item["submit_duration"] = round(sum(seg_durs), 3)
    duration_plan = dict(item.get("duration_plan") or {})
    duration_plan.update({
        "backend_request_sec": item["submit_duration"],
        "backend_surplus_sec": round(max(0.0, item["submit_duration"] - float(item.get("edit_target_duration") or item["submit_duration"])), 3),
        "trim_mode": "trim_tail" if item["submit_duration"] > float(item.get("edit_target_duration") or item["submit_duration"]) + 0.05 else "none",
        "requires_split": False,
        "duration_control_kind": "native_transition_segments",
    })
    item["duration_plan"] = duration_plan
    return True


def split_relay_prompt_text(parent_prompt: str, parent_clip: str, part_clip: str, *,
                            part_index: int, part_total: int, start_rel: str, end_rel: str,
                            start_sec: float, end_sec: float, end_hint: str = "",
                            shot_description: str = "", compiled_segment_prompt: str = "") -> str:
    """Wrap a parent clip prompt with a hard segment contract for split relay.

    Split relay feeds one physical first/end pair per paid submit.  The parent
    prompt still carries useful style/subject context, but it may also describe
    the full clip end_state; the segment contract must be first so early parts
    do not drift to the final beat.
    """
    if part_index < part_total:
        boundary = "本段只到中间锚帧；不得提前进入下一段，不得抵达父镜头最终 end_state。"
    else:
        boundary = "本段为最后一段；可以抵达父镜头最终 end_state，但必须以本段尾帧为唯一落幅。"
    hint_line = f"段落目标：{end_hint.strip()}" if end_hint and end_hint.strip() else "段落目标：以尾帧构图、主体姿态、道具/面板位置为准。"
    shot_line = f"本段镜位/动作：{shot_description.strip()}" if shot_description and shot_description.strip() else ""
    guard = "\n".join([
        "【Split Relay Segment Contract】",
        f"父镜头：{parent_clip}",
        f"当前子段：{part_clip} ({part_index}/{part_total})",
        f"时间范围：{start_sec:.3f}s -> {end_sec:.3f}s",
        f"首帧：`{start_rel}`",
        f"尾帧：`{end_rel}`",
        shot_line,
        hint_line,
        boundary,
        "执行要求：从首帧状态开始，运动连续自然，在尾帧附近稳定结束；父镜头参考提示词只用于风格、主体和镜头语气，不得覆盖本段首尾帧约束。",
    ]).replace("\n\n", "\n")
    if compiled_segment_prompt.strip():
        return f"{guard}\n\n【Compiled Segment Submit Prompt】\n{compiled_segment_prompt.strip()}".rstrip()
    parent = parent_prompt.strip()
    return f"{guard}\n\n【Parent Clip Reference Prompt】\n{parent}".rstrip()


def compile_relay_segment_prompt(
    *,
    backend: str,
    parent_item: Mapping[str, Any],
    part_clip: str,
    duration_sec: float,
    start_rel: str,
    end_rel: str,
    end_hint: str,
    shot_description: str,
) -> Dict[str, Any]:
    """Recompile one physical take instead of copying the full parent prompt.

    Editorial cuts are distinct camera/action contracts.  Reusing the parent
    prompt makes every child try to perform the whole story clip, which is the
    exact failure split relay is intended to prevent.
    """
    action = shot_description.strip() or end_hint.strip() or "从首帧状态连续完成本段动作并在尾帧姿态停稳"
    camera = shot_description.strip() or "保持本段单一连续机位，运动克制，尾端固定"
    contract = {
        "clip_id": part_clip,
        "backend": backend,
        "mode": "frames2video",
        "native_audio_policy": str((parent_item.get("prompt_compiler") or {}).get("native_audio_policy") or "none"),
        "story_span_sec": float(duration_sec),
        "edit_target_sec": float(duration_sec),
        "frame_strategy": "first_last",
        "primary_action": action,
        "camera_motion": camera,
        "environment_motion": "环境只响应本段主动作，不引入下一段事件",
        "rhythm": "本段动作完整，尾端保留稳定落幅",
        "end_state": end_hint.strip() or "与提交尾帧完全对齐并保持",
        "must_avoid": ["提前演到下一段", "新增人物", "身份漂移", "文字", "水印"],
        "frame_inputs": [start_rel, end_rel],
        "reference_inputs": list(parent_item.get("reference_inputs") or []),
        "control_inputs": list(parent_item.get("control_inputs") or []),
        "audio_inputs": list(parent_item.get("audio_inputs") or []),
    }
    return compile_video_prompt(contract, backend)


def prepare_manifest(root: Path, episode: str, start: int, end: int, *, backend: str, resolution: Optional[str],
                     model_version: Optional[str], force: bool = False) -> Dict[str, Any]:
    episode = normalize_episode(episode)
    path = manifest_path(root, episode, start, end)
    if path.exists() and not force:
        return load_json(path)
    prompts_dir = stable_prompt_dir(root, episode, start, end)
    prompts_dir.mkdir(parents=True, exist_ok=True)
    anchors_by_clip = clip_anchor_index(root, episode)
    budget_tier = video_budget_tier(root)
    resolved_resolution = resolve_video_resolution(root, resolution, budget_tier)
    resolved_model_version = resolve_base_dreamina_model_version(root, model_version, budget_tier)
    
    # 获取后端能力档案；不要用 mode 字符串猜命令名，统一读能力字段。
    capability = video_backend_frame_control(backend, "")  # 渠道暂空
    supports_mf = bool(capability.get("supports_native_mid_anchors"))
    supports_last = bool(capability.get("supports_last_frame"))

    items = []
    for item in parse_prompt_pack(root, episode, start, end):
        prompt_text = item.pop("prompt_text")
        compiler_backend = normalize_prompt_backend((item.get("prompt_compiler") or {}).get("backend"))
        requested_backend = normalize_prompt_backend(backend)
        if item.get("prompt_source_kind") == "compiled_submit_prompt" and compiler_backend != requested_backend:
            raise ValueError(
                f"{item['clip']} compiled prompt backend={compiler_backend} but prepare requested backend={requested_backend}. "
                "Update video_model_routes.json and rerun n2d-video prompt_pack.py; do not submit a primary-backend prompt to a different backend."
            )
        if _requests_native_speech(prompt_text):
            item["require_audio"] = True
            item["force_multimodal"] = True
        item["video_budget_tier"] = budget_tier
        item["model_version"] = select_dreamina_model_version(resolved_model_version, budget_tier, item, prompt_text)
        if item["model_version"] != resolved_model_version:
            item["model_version_reason"] = "high_value_clip_uses_vip"
        requested_strategy = str(item.get("frame_strategy") or "legacy_auto").strip().lower()
        edit_target = item.get("edit_target_duration") or item.get("story_duration")
        actual_duration_plan = backend_duration_plan(
            edit_target,
            backend,
            model_version=item.get("model_version"),
            frame_strategy=requested_strategy,
        )
        actual_duration_plan["story_span_sec"] = item.get("story_duration")
        item["duration_plan"] = actual_duration_plan
        item["edit_target_duration"] = actual_duration_plan.get("edit_target_sec")
        item["submit_duration"] = actual_duration_plan.get("backend_request_sec")
        item["speed_mode"] = "trim"
        prompt_file = prompts_dir / f"{item['target'][:-4]}.prompt.txt"
        prompt_file.write_text(prompt_text + "\n", encoding="utf-8")
        item["prompt_file"] = str(prompt_file)
        item["prepared_prompt_sha256"] = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
        item["prepared_prompt_chars"] = len(prompt_text)

        num = _clip_number(item)
        anchors_info = anchors_by_clip.get(num) if num is not None else None
        consumable_anchors = _consumable_anchor_rows(anchors_info or {})
        anchor_times = [row[0] for row in consumable_anchors]
        shots = list((anchors_info or {}).get("shots") or [])
        editorial_shot_count = len([
            row for row in shots if str(row.get("lens") or "").strip()
        ])
        if requested_strategy == "legacy_auto":
            requested_strategy = str(select_video_frame_strategy(
                backend,
                "",
                shot_count=max(1, editorial_shot_count),
                anchor_count=len(anchor_times),
                need_end=bool(item.get("end_image_rel")),
                requires_mid_anchors=bool(anchor_times and not shots),
            ).get("strategy") or "first_only")
            item["frame_strategy"] = requested_strategy
        frame_plan = anchor_consumption_plan(
            backend,
            "",
            anchor_count=len(anchor_times),
            need_end=bool(item.get("end_image_rel")),
            frame_strategy=requested_strategy,
        )
        item["frame_control_mode"] = capability.get("mode")
        item["anchor_consumption"] = frame_plan
        item["anchor_consumption_mode"] = frame_plan.get("consumption_mode")
        item["video_shot_split_plan"] = video_shot_split_plan(item)
        force_physical_split = requested_strategy == "edit_cut" or bool(item["video_shot_split_plan"].get("required"))

        # 尝试接入原生多帧
        attached_mf = False
        if requested_strategy == "native_multiframe" and supports_mf and anchor_times and not force_physical_split:
            attached_mf = attach_multiframe(root, item, prompt_text, anchors_by_clip)
        elif requested_strategy == "native_multiframe" and supports_mf and anchor_times and force_physical_split:
            item["native_multiframe_skip"] = (
                f"story_clip duration {item['video_shot_split_plan'].get('story_duration_sec')}s "
                f"> {VIDEO_SHOT_PLAN_THRESHOLD_SEC:g}s; use physical video_shot split instead of one long native multiframe clip"
            )
        
        # 如果不支持原生多帧，或者 attach 失败，但有中锚 -> 自动化拆段接力 (Split Relay)
        relay_requested = force_physical_split or requested_strategy in {"split_relay", "edit_cut"} or (
            str((item.get("prompt_compiler") or {}).get("version") or "") == "1" and bool(anchor_times)
        )
        if not attached_mf and relay_requested and anchor_times:
            # 执行自动化拆段 (仅当有 end_frame 且后端支持首尾帧或明确要求拆段时)
            if supports_last and item.get("end_image") and Path(item["end_image"]).is_file():
                # 构造子段列表
                relay_anchors = list(consumable_anchors)
                if requested_strategy == "edit_cut" and shots:
                    boundaries = [float(row["start_sec"]) for row in shots[1:]]
                    selected: List[Tuple[float, str, str]] = []
                    missing_boundaries: List[float] = []
                    for boundary in boundaries:
                        nearest = min(relay_anchors, key=lambda row: abs(row[0] - boundary), default=None)
                        if nearest is None or abs(nearest[0] - boundary) > 0.35:
                            missing_boundaries.append(boundary)
                        else:
                            selected.append((boundary, nearest[1], nearest[2]))
                    if missing_boundaries:
                        item["frame_strategy_issue"] = (
                            "edit_cut boundary images missing at "
                            + ", ".join(f"{value:g}s" for value in missing_boundaries)
                        )
                        refresh_item_recipe_evidence(root, episode, item)
                        items.append(item)
                        continue
                    relay_anchors = selected
                t_list = [0.0] + [t for t, _, _ in relay_anchors] + [float(item["story_duration"])]
                png_list = [item["image_rel"]] + [png for _, png, _ in relay_anchors] + [item["end_image_rel"]]
                segment_end_hints = [hint for _, _, hint in relay_anchors] + [str(anchors_info.get("end_state") or "")]
                missing = []
                for png in png_list:
                    if not png:
                        missing.append(str(png))
                        continue
                    abs_png = Path(png) if Path(png).is_absolute() else root / png
                    if not abs_png.is_file():
                        missing.append(str(png))
                if missing:
                    item["anchor_consumption_issue"] = "split relay keyframe PNG missing: " + ", ".join(missing)
                    refresh_item_recipe_evidence(root, episode, item)
                    items.append(item)
                    continue
                
                parts = []
                for p_idx in range(len(t_list) - 1):
                    seg_dur = t_list[p_idx+1] - t_list[p_idx]
                    part_item = item.copy()
                    for stale_key in (
                        "multiframe_skip",
                        "multiframe_images",
                        "multiframe_images_rel",
                        "multiframe_segment_durations",
                        "multiframe_segment_prompts",
                        "mode_backend",
                    ):
                        part_item.pop(stale_key, None)
                    part_item["clip"] = f"{item['clip']}_part{p_idx+1}"
                    part_item["target"] = f"{item['target'][:-4]}_part{p_idx+1}.mp4"
                    part_item["image_rel"] = png_list[p_idx]
                    part_item["image"] = str((root / png_list[p_idx]).resolve()) if not Path(png_list[p_idx]).is_absolute() else png_list[p_idx]
                    part_item["end_image_rel"] = png_list[p_idx+1]
                    part_item["end_image"] = str((root / png_list[p_idx+1]).resolve()) if not Path(png_list[p_idx+1]).is_absolute() else png_list[p_idx+1]
                    part_item["story_duration"] = seg_dur
                    part_item["edit_target_duration"] = round(seg_dur, 3)
                    part_item["duration_plan"] = backend_duration_plan(
                        seg_dur,
                        backend,
                        model_version=part_item.get("model_version"),
                        frame_strategy="first_last",
                    )
                    part_item["duration_plan"]["story_span_sec"] = round(seg_dur, 3)
                    part_item["submit_duration"] = part_item["duration_plan"].get("backend_request_sec")
                    part_item["speed_mode"] = "trim"
                    part_item["relay_parent"] = item["clip"]
                    part_item["story_clip"] = item["clip"]
                    part_item["video_shot_segment"] = {
                        "version": 1,
                        "parent_story_clip": item["clip"],
                        "video_shot_id": part_item["clip"],
                        "part_index": p_idx + 1,
                        "part_total": len(t_list) - 1,
                        "target_video_shot_sec": VIDEO_SHOT_TARGET_SEC,
                        "parent_story_duration_sec": item["video_shot_split_plan"].get("story_duration_sec"),
                        "edit_target_sec": round(seg_dur, 3),
                        "reason": (
                            "storyboard_editorial_cut" if requested_strategy == "edit_cut"
                            else "story_clip_longer_than_video_shot_threshold" if force_physical_split
                            else "backend_requires_split_relay"
                        ),
                    }
                    part_item["frame_strategy"] = "edit_cut_part" if requested_strategy == "edit_cut" else "split_relay_part"
                    part_item["anchor_consumption_mode"] = part_item["frame_strategy"]
                    part_item["anchor_consumption_parent_mode"] = frame_plan.get("consumption_mode")
                    segment_shot_description = (
                        "；".join(filter(None, (
                            str(shots[p_idx].get("lens") or "") if p_idx < len(shots) else "",
                            str(shots[p_idx].get("description") or "") if p_idx < len(shots) else "",
                        )))
                        if requested_strategy == "edit_cut" else ""
                    )
                    compiled_segment = compile_relay_segment_prompt(
                        backend=backend,
                        parent_item=item,
                        part_clip=part_item["clip"],
                        duration_sec=seg_dur,
                        start_rel=part_item["image_rel"],
                        end_rel=part_item["end_image_rel"],
                        end_hint=segment_end_hints[p_idx] if p_idx < len(segment_end_hints) else "",
                        shot_description=segment_shot_description,
                    )
                    part_prompt = split_relay_prompt_text(
                        prompt_text,
                        item["clip"],
                        part_item["clip"],
                        part_index=p_idx + 1,
                        part_total=len(t_list) - 1,
                        start_rel=part_item["image_rel"],
                        end_rel=part_item["end_image_rel"],
                        start_sec=float(t_list[p_idx]),
                        end_sec=float(t_list[p_idx + 1]),
                        end_hint=segment_end_hints[p_idx] if p_idx < len(segment_end_hints) else "",
                        shot_description=segment_shot_description,
                        compiled_segment_prompt=str(compiled_segment.get("prompt") or ""),
                    )
                    part_prompt_file = prompts_dir / f"{part_item['target'][:-4]}.prompt.txt"
                    part_prompt_file.write_text(part_prompt + "\n", encoding="utf-8")
                    part_item["prompt_file"] = str(part_prompt_file)
                    part_item["prompt_source_kind"] = "compiled_segment_submit_prompt"
                    part_item["prompt_compiler"] = {
                        key: compiled_segment.get(key)
                        for key in (
                            "kind", "version", "profile_version", "profile", "backend", "mode",
                            "language", "native_audio_policy", "source_contract_sha256", "frame_strategy",
                        )
                    }
                    part_item["negative_prompt"] = str(compiled_segment.get("negative_prompt") or "")
                    part_item["prepared_prompt_sha256"] = hashlib.sha256(part_prompt.encode("utf-8")).hexdigest()
                    part_item["prepared_prompt_chars"] = len(part_prompt)
                    part_item["split_relay_prompt_guard"] = {
                        "version": 1,
                        "parent_clip": item["clip"],
                        "part_index": p_idx + 1,
                        "part_total": len(t_list) - 1,
                        "start_sec": float(t_list[p_idx]),
                        "end_sec": float(t_list[p_idx + 1]),
                        "start_image_rel": part_item["image_rel"],
                        "end_image_rel": part_item["end_image_rel"],
                        "strategy": requested_strategy,
                        "edit_target_sec": round(seg_dur, 3),
                    }
                    refresh_item_recipe_evidence(root, episode, part_item)
                    parts.append(part_item)
                
                items.extend(parts)
                continue # 已拆段，跳过原 item
            item["anchor_consumption_issue"] = (
                "mid anchors declared but backend cannot consume native mid anchors"
                if not supports_last else "mid anchors declared but end frame is missing for split relay"
            )
        if requested_strategy == "edit_cut_pending_assets":
            item["frame_strategy_issue"] = (
                "multiple storyboard shots require edit-cut boundary images and an end frame before paid generation"
            )
        elif requested_strategy == "reroute_required":
            item["frame_strategy_issue"] = (
                "high-risk continuous shot needs mid-frame control but the selected backend cannot consume it"
            )
        if force_physical_split and not anchor_times:
            item["duration_segment_issue"] = (
                f"story_clip duration {item.get('story_duration')}s requires physical edit/generation parts "
                "but storyboard has no consumable continuity.anchors[] at cut boundaries; "
                "run n2d-script shot_split_decision + anchor_planner before paid video generation"
            )
        if bool((item.get("duration_plan") or {}).get("requires_split")) and not item.get("video_shot_segment"):
            item["duration_segment_issue"] = (
                f"edit target {item.get('edit_target_duration')}s exceeds the selected backend request ceiling; "
                "prepare explicit physical parts before paid submission"
            )
        refresh_item_recipe_evidence(root, episode, item)
        items.append(item)
    
    payload = {
        "kind": "n2d_video_batch",
        "version": 2,
        "episode": episode,
        "batch": f"{start:02d}-{end:02d}",
        "batch_id": batch_id(start, end),
        "backend": backend,
        "model_version": resolved_model_version,
        "requested_model_version": str(model_version or "auto"),
        "video_budget_tier": budget_tier,
        "video_resolution": resolved_resolution,
        "requested_video_resolution": str(resolution or "auto"),
        "ratio": aspect_ratio(root),
        "execution_adapter": execution_adapter_v2.execution_status(root, backend, ""),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "items": items,
    }
    atomic_write_json(path, payload)
    return payload




def find_item(manifest: Dict[str, Any], clip: str) -> Dict[str, Any]:
    for item in manifest.get("items", []):
        if item.get("clip") == clip:
            return item
    target = clip if clip.startswith("Clip_") else clip_key(int(clip))
    for item in manifest.get("items", []):
        if item.get("clip") == target:
            return item
    raise KeyError(f"clip not in manifest: {target}")


def update_manifest(path: Path, manifest: Dict[str, Any]) -> None:
    manifest["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    atomic_write_json(path, manifest)


# ── multiframe2video (即梦 智能多帧) — native multi-keyframe → one continuous clip ──
# Replaces the split-into-segments + ffmpeg-concat relay for backends that take N keyframes
# natively. CLI contract (verified via probe_cli.py, snapshot in references/cli_snapshots/):
#   dreamina multiframe2video --images a.png,b.png[,c.png...]
#     2 images : --prompt P --duration D
#     3+ images: --transition-prompt × (N-1)  --transition-duration × (N-1)
#   each segment ∈ [0.5, 8]s; total ≥ 2s; ratio inferred from first image;
#   model_version / video_resolution NOT supported by this command.
MULTIFRAME_SEG_MIN = 0.5
MULTIFRAME_SEG_MAX = 8.0
MULTIFRAME_TOTAL_MIN = 2.0


def multiframe_segments(clip_duration: float, anchor_times: Sequence[float], *,
                        seg_min: float = MULTIFRAME_SEG_MIN, seg_max: float = MULTIFRAME_SEG_MAX,
                        total_min: float = MULTIFRAME_TOTAL_MIN) -> List[float]:
    """Keyframe times [0, *anchor_times, clip_duration] → consecutive segment durations.

    Validates the CLI contract: each segment in [seg_min, seg_max], total ≥ total_min,
    strictly increasing. Raises ValueError (with a fix hint) so the caller can fall back
    to image2video/frames2video instead of submitting an invalid task."""
    times = [0.0] + sorted(float(t) for t in anchor_times) + [float(clip_duration)]
    segs = [round(times[i + 1] - times[i], 3) for i in range(len(times) - 1)]
    if any(s <= 0 for s in segs):
        raise ValueError(f"multiframe: non-increasing keyframe times {times}")
    bad = [s for s in segs if s < seg_min or s > seg_max]
    if bad:
        raise ValueError(
            f"multiframe: segment(s) {bad} outside [{seg_min},{seg_max}]s (all={segs}); "
            "re-plan anchors (anchor_planner) so each gap fits — too long→add anchor, too short→drop one")
    if round(sum(segs), 3) < total_min:
        raise ValueError(f"multiframe: total {sum(segs):.3f}s < {total_min}s; clip too short for multiframe2video")
    return segs


def _dreamina_multiframe_args(images: Sequence[str], segment_durations: Sequence[float],
                              segment_prompts: Sequence[str], *, poll: int = 0) -> List[str]:
    """Build the `dreamina multiframe2video` argv. N images → N-1 segments."""
    n = len(images)
    if not (2 <= n <= 20):
        raise ValueError(f"multiframe2video needs 2-20 images, got {n}")
    if len(segment_durations) != n - 1:
        raise ValueError(f"{n} images need {n - 1} segment durations, got {len(segment_durations)}")
    args = ["dreamina", "multiframe2video", "--images", ",".join(images)]
    if n == 2:
        prompt = (list(segment_prompts) or [""])[0]
        args += ["--prompt", prompt, "--duration", str(segment_durations[0])]
    else:
        if len(segment_prompts) != n - 1:
            raise ValueError(f"{n} images need {n - 1} transition prompts, got {len(segment_prompts)}")
        for p in segment_prompts:
            args += ["--transition-prompt", p]
        for d in segment_durations:
            args += ["--transition-duration", str(d)]
    if poll:
        args += ["--poll", str(poll)]
    return args


# Required flags per dreamina command, asserted live before each paid submit (CLI-drift guard).
_CLI_REQUIRED_FLAGS = {
    "multiframe2video": ["images", "prompt", "duration", "transition-prompt", "transition-duration"],
    "frames2video": ["first", "last", "prompt", "duration"],
    "image2video": ["image", "prompt"],
    "multimodal2video": ["image", "prompt", "duration"],
}


def verify_cli_contract(cli: str, command: str) -> None:
    """Run `<cli> <command> --help` and assert the flags the arg builder uses still exist.
    Raises RuntimeError on drift so we don't burn credits on a stale invocation. Silently
    skips if probe_cli or the CLI isn't importable/available (don't block on the guard itself)."""
    requires = _CLI_REQUIRED_FLAGS.get(command)
    if not requires:
        return
    try:
        import probe_cli
        binary = probe_cli.resolve_bin(cli, None)
        if not binary:
            return  # CLI not found here (e.g. manual/headless env) — submit path handles that
        ok, msg = probe_cli.verify(cli, binary, command, requires)
    except Exception:
        return  # probe unavailable → don't block; this is a guard, not a gate
    if not ok:
        raise RuntimeError(
            f"CLI contract drift before paid submit: {msg}. "
            f"Re-run `python3 skills/n2d-video/scripts/probe_cli.py probe` to refresh snapshots "
            f"and update the arg builder before spending credits.")


def storyboard_path(root: Path, episode: str) -> Path:
    return root / "脚本" / normalize_episode(episode) / "storyboard.json"


def beat_hint_at(clip: Dict[str, Any], at_sec: Optional[float]) -> str:
    """表演节拍中 at_sec 时刻"到达的那一拍"，取自 template_contract.beats。

    用作 multiframe2video 的**转场 prompt** —— 让每段描述真实运动（起手→命中），而不是规划器
    的元数据 reason（"auto: R1 高运动模板…"，那是给人读报告的、绝不能当运动描述喂模型）。
    缺 beats 时返回 ""（attach_multiframe 会回退到 Clip 主 prompt 头）。"""
    tc = clip.get("template_contract")
    beats = tc.get("beats") if isinstance(tc, dict) else None
    if not (isinstance(beats, list) and beats):
        return ""
    duration = clip.get("duration")
    if not isinstance(at_sec, (int, float)) or not isinstance(duration, (int, float)) or duration <= 0:
        return str(beats[len(beats) // 2])  # 无可用时间 → 取中间拍
    idx = int(float(at_sec) / float(duration) * len(beats))
    return str(beats[max(0, min(len(beats) - 1, idx))])


def _shot_time_range(value: Any) -> Optional[Tuple[float, float]]:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            return float(value[0]), float(value[1])
        except (TypeError, ValueError):
            return None
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:s|秒)?\s*[-~—–至]\s*([0-9]+(?:\.[0-9]+)?)", str(value or ""))
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def _storyboard_shots(clip: Mapping[str, Any], duration: Any) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for idx, shot in enumerate(clip.get("shots") or [], 1):
        if not isinstance(shot, Mapping):
            continue
        timing = _shot_time_range(shot.get("t") or shot.get("time") or shot.get("range"))
        if timing is None:
            continue
        start, end = timing
        if start < 0 or end <= start:
            continue
        rows.append({
            "index": idx,
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "description": str(shot.get("description") or shot.get("visual") or shot.get("action") or ""),
            "lens": str(shot.get("lens") or shot.get("shot_size") or shot.get("camera") or ""),
        })
    rows.sort(key=lambda row: float(row["start_sec"]))
    if rows and isinstance(duration, (int, float)):
        rows[-1]["end_sec"] = round(float(duration), 3)
    return rows


def _consumable_anchor_rows(info: Mapping[str, Any]) -> List[Tuple[float, str, str]]:
    rows: List[Tuple[float, str, str]] = []
    for t, png, use, hint in zip(
        info.get("times") or [], info.get("images") or [],
        info.get("uses") or [], info.get("hints") or [],
    ):
        use_key = str(use or "split").strip().lower()
        if use_key in {"qc", "reference", "reference_qc", "review"}:
            continue
        if t is None or not png:
            continue
        try:
            rows.append((float(t), str(png), str(hint or "")))
        except (TypeError, ValueError):
            continue
    return sorted(rows, key=lambda row: row[0])


def clip_anchor_index(root: Path, episode: str) -> Dict[int, Dict[str, Any]]:
    """{clip_number: {"times": [at_sec...], "images": [rel png...], "hints": [beat...], "duration"}}
    from storyboard.json. 读 continuity.anchors（N 锚链）或 continuity.midframe（单锚）。

    `hints` 是各锚帧的**运动转场提示**，按 at_sec 从 template_contract.beats 取真值（见 beat_hint_at），
    不再把规划器 reason 当 prompt。capability-driven：所有有 at_sec+png 的锚帧都返回，use 字段仅作
    advisory（multiframe2video 段只需 ≥0.5s，旧 use=qc 标签不再拦）。storyboard 缺失时返回 {}。"""
    path = storyboard_path(root, episode)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: Dict[int, Dict[str, Any]] = {}
    for i, clip in enumerate(data.get("clips") or [], 1):
        if not isinstance(clip, dict):
            continue
        cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
        anchors = cont.get("anchors")
        if anchors is None and isinstance(cont.get("midframe"), dict):
            mid = cont["midframe"]
            anchors = [{"anchor_png": mid.get("midframe_png"), "at_sec": mid.get("split_at_sec"),
                        "use": "split"}]
        if not isinstance(anchors, list):
            anchors = []
        times, images, uses, hints = [], [], [], []
        for a in anchors:
            if not isinstance(a, dict):
                continue
            times.append(a.get("at_sec"))
            images.append(a.get("anchor_png"))
            uses.append(a.get("use", "split"))
            # 转场 prompt 用真运动（按 at_sec 取拍），不用规划器 reason 元数据
            hints.append(beat_hint_at(clip, a.get("at_sec")))
        out[i] = {"times": times, "images": images, "uses": uses, "hints": hints,
                  "duration": clip.get("duration"),
                  "shots": _storyboard_shots(clip, clip.get("duration")),
                  "end_state": str(cont.get("end_state") or "")}  # 末段转场 prompt 用它，比泛化句具体
    return out


def _dreamina_args(item: Dict[str, Any], manifest: Dict[str, Any]) -> List[str]:
    prompt = Path(item["prompt_file"]).read_text(encoding="utf-8").strip()
    prompt = _append_dialogue_fact_contract(prompt, item, manifest)
    model_version = _effective_dreamina_model_version(item, manifest, prompt)

    # Audio/native-AV batches must not silently fall into multiframe2video: that path is
    # image-keyframe accurate, but Dreamina currently returns video-only MP4s there.
    # Use the stronger all-around reference mode and pass the same keyframes as images.
    force_multimodal = bool(
        manifest.get("force_multimodal")
        or manifest.get("require_audio")
        or item.get("force_multimodal")
        or item.get("require_audio")
        or _requests_native_speech(prompt)
    )
    if force_multimodal:
        images = item.get("multimodal_images") or item.get("multiframe_images")
        if not images:
            images = [item["image"]]
            if item.get("end_image") and Path(item["end_image"]).is_file():
                images.append(item["end_image"])
        args = ["dreamina", "multimodal2video"]
        for image in images:
            args += ["--image", str(image)]
        args += [
            "--prompt", prompt,
            "--duration", str(item["submit_duration"]),
            "--ratio", manifest.get("ratio") or "9:16",
            "--video_resolution", manifest.get("video_resolution") or "720p",
            "--model_version", _multimodal_model_version(manifest, item, prompt),
        ]
        return args

    # Native multi-keyframe path (即梦 智能多帧): first + mid-anchors + end → one continuous clip.
    # Prepared by prepare_manifest when storyboard has valid in-range anchors; falls back below
    # if the segment contract can't be met (recorded as item["multiframe_skip"]).
    mf_images = item.get("multiframe_images")
    if mf_images and len(mf_images) >= 2 and item.get("multiframe_segment_durations"):
        seg_prompts = item.get("multiframe_segment_prompts") or (
            [prompt] if len(mf_images) == 2 else [prompt] * (len(mf_images) - 1))
        if "对白事实锁" in prompt:
            seg_prompts = [
                p if "对白事实锁" in str(p) else f"{str(p).rstrip()}\n\n{prompt[prompt.index('对白事实锁'):]}"
                for p in seg_prompts
            ]
        return _dreamina_multiframe_args(
            mf_images, item["multiframe_segment_durations"], seg_prompts,
            poll=int(manifest.get("poll") or 0))

    # Two-frame (首帧 + 尾帧) clip without mid-anchors → multimodal2video with both frames.
    has_end_image = item.get("end_image") and Path(item["end_image"]).is_file()
    if has_end_image:
        return [
            "dreamina", "multimodal2video",
            "--image", item["image"],
            "--image", item["end_image"],
            "--prompt", prompt,
            "--duration", str(item["submit_duration"]),
            "--ratio", manifest.get("ratio") or "9:16",
            "--video_resolution", manifest.get("video_resolution") or "720p",
            "--model_version", _multimodal_model_version(manifest, item, prompt),
        ]

    # Fallback to standard image2video for single-frame sources
    return [
        "dreamina",
        "image2video",
        "--image",
        item["image"],
        "--prompt",
        prompt,
        "--duration",
        str(item["submit_duration"]),
        "--video_resolution",
        manifest.get("video_resolution") or "720p",
        "--model_version",
        model_version,
    ]


def _dreamina_query_args(submit_id: str, download_dir: Path) -> List[str]:
    return ["dreamina", "query_result", f"--submit_id={submit_id}", f"--download_dir={download_dir}"]


# ── 后端适配层（C2：适配不了就停下报缺口，不偷偷换路）──────────────────────────
# 本 runner 只内置了即梦/Dreamina CLI 的自动化契约（命令/旗标见上方探针快照 + _CLI_REQUIRED_FLAGS）。
# n2d-model-router 会把镜头路由到 Kling/Veo/Seedance 等后端，但本机若没有对应 CLI 自动化契约，
# 绝不静默改用即梦顶替（那是 C2 禁的「偷偷换路」，也会按即梦计费记错账）——而是停下报缺口，
# 指引走 manual 出视频后用 `accept` 登记。新增一个自动化后端 = 在此注册一个 adapter
# （submit_args/query_args/provider），submit/query 调用点不动。
VIDEO_BACKEND_ADAPTERS: Dict[str, Dict[str, Any]] = {
    "dreamina": {
        "kind": execution_adapter_v2.ADAPTER_KIND,
        "version": execution_adapter_v2.ADAPTER_VERSION,
        "adapter_id": "dreamina_cli_v2",
        "execution_backend": "dreamina",
        "provider": "dreamina",
        "implementation": "embedded",
        "command": ["dreamina"],
        "operations": ["submit", "query"],
        "capabilities": {
            "idempotency": "runner_guarded",
            "async_query": True,
            "cancel": False,
            "multishot": False,
        },
        "submit_args": _dreamina_args,
        "query_args": _dreamina_query_args,
    },
}
# 走人工出视频的 backend 取值（prepare 仍产 prompt 包，但 submit/query 不适用于人工后端）。
_MANUAL_BACKENDS = {"manual", "手动", "手工", "人工"}
_BACKEND_ALIASES = {"即梦": "dreamina", "jimeng": "dreamina", "dreamina": "dreamina",
                    "即梦/dreamina": "dreamina", "dreamina/即梦": "dreamina"}


def resolve_video_backend(manifest: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """manifest backend → executable adapter v2; never silently switch providers."""
    raw = str(manifest.get("backend") or "dreamina").strip()
    low = raw.lower()
    if low in _MANUAL_BACKENDS:
        raise RuntimeError(
            f"backend={raw}：本批次走人工出视频。把生成好的 clip 放进 出视频/<集>/视频/，"
            "再用 `accept` 登记验收；submit/query 不适用于人工后端。")
    key = _BACKEND_ALIASES.get(low, low)
    adapter = VIDEO_BACKEND_ADAPTERS.get(key)
    if not adapter:
        root = manifest.get("_root")
        channel = manifest.get("channel") or ""
        project_adapter = execution_adapter_v2.adapter_for(root, raw, channel) if root else None
        if project_adapter:
            key = str(project_adapter.get("execution_backend") or key)
            adapter = project_adapter
    if not adapter:
        supported = ", ".join(sorted(VIDEO_BACKEND_ADAPTERS))
        raise RuntimeError(
            f"后端 '{raw}' 没有内置自动化 runner（当前仅 {supported} 有 CLI 契约）。"
            "不会静默改用其它后端顶替（C2：适配不了就停下报缺口，不偷偷换路）。"
            "→ 改用 manual 出视频后用 `accept` 登记，或在 "
            "生产数据/video_execution_adapters.json 注册 adapter v2 wrapper。")
    return key, adapter


def append_submission_log(root: Path, episode: str, row: Dict[str, Any]) -> None:
    append_jsonl(production_dir(root) / f"video_submissions_{episode}.jsonl", row)


def run_preflight_gate(root: Path, episode: str, stage: str = "video_preflight") -> None:
    proc = subprocess.run(
        [sys.executable, str(DASHBOARD_PY), "gate", str(root), episode, "--stage", stage],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        detail = "\n".join(part for part in (proc.stdout.strip(), proc.stderr.strip()) if part)
        raise RuntimeError(f"{stage} gate blocked video backend submission.\n{detail}")


def record_waiver(root: Path, episode: str, stage: str, waiver: str, reason: str) -> None:
    """H2：把跳过付费前闸记成 dashboard waiver 事件（执行时松动留痕，与 n2d-image 对齐）。

    此前 video 的 `--skip-preflight` 静默旁路 video_preflight 一致性闸、无任何留痕（image runner 会
    record_waiver，video 不会，是不对称的无痕旁路）。best-effort：留痕失败绝不中断生成——点在于
    "松一道闸"在 dashboard 可审计、不静默，而非给 bookkeeping 一票否决生成的权力。"""
    cmd = [
        sys.executable, str(DASHBOARD_PY), "waiver", str(root),
        "--episode", episode, "--stage", stage, "--waiver", waiver,
        "--reason", reason, "--source", "n2d-video/scripts/video_runner.py", "--no-build",
    ]
    try:
        subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception:
        pass


def run_identity_handoff_guard(root: Path, episode: str) -> None:
    """Hard guard for paid submits: same-character keyframes must share identity anchors.

    `--skip-preflight` is useful for debugging full dashboard gates, but it must not
    bypass the face-lock contract.  Missing route/prompt files are blockers here
    because this function only runs at the paid submit boundary.
    """
    res = check_identity_handoff(str(root), episode)
    if not res.get("available"):
        notes = "; ".join(str(n) for n in res.get("notes", [])) or "identity handoff check unavailable"
        raise RuntimeError(
            "identity handoff guard unavailable before paid video submission. "
            f"{notes} Run n2d-model-router and regenerate n2d-video prompts first."
        )
    blocks = [f for f in res.get("findings", []) if f.get("severity") == "block"]
    if blocks:
        detail = "\n".join(
            f"- {f.get('clip_id', '?')} [{f.get('code', '?')}]: {f.get('note', '')}"
            for f in blocks
        )
        raise RuntimeError(
            "identity handoff guard blocked paid video submission. "
            "Same-character first/mid/end anchors must come from one identity_registry/reference_group, "
            "and big-expression closeups must use same-source expressions with 锁脸不锁情.\n"
            f"{detail}"
        )


def _adapter_invocation(
    root: Path,
    manifest: Dict[str, Any],
    item: Dict[str, Any],
    adapter: Mapping[str, Any],
    operation: str,
) -> Tuple[List[str], Optional[Path]]:
    """Build an embedded or wrapper-command adapter invocation.

    Wrapper adapters receive only a stable request JSON path on argv; prompts,
    credentials and vendor-specific fields stay outside shell interpolation.
    """
    implementation = str(adapter.get("implementation") or "embedded")
    if implementation == "embedded":
        builder_key = "submit_args" if operation == "submit" else "query_args"
        builder = adapter.get(builder_key)
        if not callable(builder):
            raise RuntimeError(f"adapter {adapter.get('adapter_id') or adapter.get('provider')} missing {builder_key}")
        if operation == "submit":
            return list(builder(item, {**manifest, "_root": str(root)})), None
        download_dir = formal_video_dir(root, str(manifest.get("episode") or "")) / "_downloads"
        return list(builder(str(item.get("submit_id") or ""), download_dir)), None

    request = execution_adapter_v2.build_request(
        operation=operation,
        root=root,
        manifest=manifest,
        item=item,
        adapter=adapter,
    )
    request_path = execution_adapter_v2.write_request(
        root,
        str(manifest.get("episode") or ""),
        request,
    )
    item["execution_request"] = {
        "path": str(request_path),
        "sha256": request.get("request_sha256"),
        "idempotency_key": request.get("idempotency_key"),
        "operation": operation,
        "adapter_id": adapter.get("adapter_id"),
    }
    item["idempotency_key"] = request.get("idempotency_key")
    return execution_adapter_v2.wrapper_args(adapter, operation, request_path), request_path


def _normalized_adapter_result(adapter: Mapping[str, Any], stdout: str, stderr: str) -> Dict[str, Any]:
    raw = execution_adapter_v2.parse_result(stdout, stderr)
    if str(adapter.get("implementation") or "embedded") == "embedded":
        return {
            "submit_id": raw.get("submit_id") or "",
            "status": raw.get("gen_status") or raw.get("status") or "",
            "output_path": raw.get("output_path") or "",
            "error": raw.get("fail_reason") or raw.get("error") or "",
            "raw": raw,
        }
    return execution_adapter_v2.normalize_result(adapter, raw)


def _ensure_adapter_command_ready(adapter: Mapping[str, Any], args: Sequence[str]) -> None:
    if str(adapter.get("implementation") or "embedded") == "embedded":
        return  # embedded adapters retain their own live CLI-contract probe
    if not args:
        raise RuntimeError(f"adapter {adapter.get('adapter_id')} produced an empty command")
    binary = str(args[0])
    ready = (
        Path(binary).is_file() and os.access(binary, os.X_OK)
        if os.path.isabs(binary) or "/" in binary
        else shutil.which(binary) is not None
    )
    if not ready:
        raise RuntimeError(
            f"adapter v2 {adapter.get('adapter_id') or adapter.get('provider')} is registered but command "
            f"'{binary}' is unavailable; install/configure the wrapper or use manual delivery"
        )


GENERATED_NOT_ACCEPTED_STATUSES = {
    "submitting",
    "submitted",
    "queried",
    "query_failed",
    "cancel_unknown",
    "downloaded",
    "downloaded_existing_target",
    "qc_blocked",
}


def _resolved_evidence_path(root: Path, raw: Any) -> Optional[Path]:
    text = str(raw or "").strip()
    if not text:
        return None
    path = Path(text).expanduser()
    return path if path.is_absolute() else root / path


def accepted_video_receipt_issues(root: Path, episode: str, item: Mapping[str, Any]) -> List[str]:
    """Validate that an accepted physical clip has machine QC and current-pixel visual review."""
    issues: List[str] = []
    if str(item.get("status") or "").strip().lower() != "accepted":
        return ["status_not_accepted"]
    if not str(item.get("accepted_at") or "").strip():
        issues.append("accepted_at_missing")
    target = _item_target_path(root, episode, dict(item))
    if not target.is_file():
        issues.append("accepted_target_missing")
        current_sha = ""
    else:
        current_sha = _sha256_file(target)
    machine = item.get("qc_machine") if isinstance(item.get("qc_machine"), Mapping) else {}
    if not machine:
        issues.append("machine_qc_receipt_missing")
    for key in ("qc_json", "qc_markdown"):
        evidence = _resolved_evidence_path(root, item.get(key))
        if evidence is None or not evidence.is_file():
            issues.append(f"{key}_missing")
    review = item.get("visual_review") if isinstance(item.get("visual_review"), Mapping) else {}
    if str(review.get("verdict") or "").strip().lower() != "pass":
        issues.append("visual_review_not_pass")
    if not str(review.get("reviewer") or "").strip():
        issues.append("visual_reviewer_missing")
    if not str(review.get("reviewed_at") or "").strip():
        issues.append("visual_reviewed_at_missing")
    if review.get("explicit_current_pixels_confirmation") is not True:
        issues.append("current_pixels_confirmation_missing")
    if len(str(review.get("notes") or "").strip()) < 4:
        issues.append("visual_review_notes_missing")
    receipt_sha = str(review.get("artifact_sha256") or "").strip()
    if not receipt_sha:
        issues.append("visual_review_sha256_missing")
    elif current_sha and receipt_sha != current_sha:
        issues.append("visual_review_sha256_stale")
    item_sha = str(item.get("artifact_sha256") or "").strip()
    if item_sha and current_sha and item_sha != current_sha:
        issues.append("accepted_artifact_sha256_stale")
    return issues


def sequential_qc_blockers(
    root: Path,
    manifest_file: Path,
    manifest: Mapping[str, Any],
    current_item: Mapping[str, Any],
) -> List[str]:
    """Return episode-wide physical clips that forbid another paid submission.

    Prepared/failed/cancelled rows have no delivered video to inspect. Any paid job
    still in flight, downloaded-but-unaccepted video, or legacy ``accepted`` row
    without a current-pixel visual receipt blocks the next distinct physical clip.
    """
    episode = str(manifest.get("episode") or "")
    current_clip = str(current_item.get("clip") or "")
    manifests: List[Tuple[Path, Mapping[str, Any]]] = [(manifest_file, manifest)]
    seen_paths = {manifest_file.expanduser().resolve()}
    for path in sorted(production_dir(root).glob(f"video_batch_{episode}_*.json")):
        resolved = path.resolve()
        if resolved in seen_paths:
            continue
        seen_paths.add(resolved)
        data = load_json(path)
        if isinstance(data, Mapping):
            manifests.append((path, data))
    blockers: List[str] = []
    seen_rows: Set[Tuple[str, str, str]] = set()
    for path, data in manifests:
        for row in data.get("items") or []:
            if not isinstance(row, Mapping):
                continue
            row_clip = str(row.get("clip") or "")
            if not row_clip or row_clip == current_clip:
                continue
            row_key = (row_clip, str(row.get("target") or ""), str(row.get("submit_id") or ""))
            if row_key in seen_rows:
                continue
            seen_rows.add(row_key)
            status = str(row.get("status") or "").strip().lower()
            label = f"{row_clip}@{path.name}"
            if status in GENERATED_NOT_ACCEPTED_STATUSES:
                blockers.append(f"{label}: status={status}，上一物理视频尚未严格 QC/实际查看并 accept")
            elif status == "accepted":
                issues = accepted_video_receipt_issues(root, episode, row)
                if issues:
                    blockers.append(f"{label}: accepted 收据无效（{','.join(issues)}）")
    return blockers


def enforce_sequential_qc_interlock(
    root: Path,
    manifest_file: Path,
    manifest: Mapping[str, Any],
    current_item: Mapping[str, Any],
) -> None:
    blockers = sequential_qc_blockers(root, manifest_file, manifest, current_item)
    if blockers:
        raise RuntimeError(
            "sequential video QC interlock blocked paid submission: 每出一个物理视频，必须先完成机器 QC、"
            "实际查看并写入当前像素 visual_review=pass，才能生成下一个。\n- " + "\n- ".join(blockers[:12])
        )


def submit_clip(root: Path, manifest_file: Path, clip: str, *, dry_run: bool = False,
                skip_preflight: bool = False) -> Dict[str, Any]:
    manifest = load_json(manifest_file)
    episode = manifest["episode"]
    item = find_item(manifest, clip)
    if item.get("submit_id") and item.get("status") not in {"failed", "rejected"}:
        raise RuntimeError(f"{item['clip']} already has submit_id={item['submit_id']}; query or reject before resubmitting")
    unresolved = item.get("frame_strategy_issue") or item.get("duration_segment_issue") or item.get("anchor_consumption_issue")
    if unresolved:
        raise RuntimeError(f"{item['clip']} paid submission blocked by unresolved execution contract: {unresolved}")
    if str(item.get("frame_strategy") or "").lower() in {"edit_cut_pending_assets", "reroute_required"}:
        raise RuntimeError(
            f"{item['clip']} frame_strategy={item.get('frame_strategy')} is not directly submit-able; "
            "complete boundary assets or change the backend route, then prepare again."
        )
    if bool((item.get("duration_plan") or {}).get("requires_split")) and not item.get("video_shot_segment"):
        raise RuntimeError(
            f"{item['clip']} edit target exceeds the backend duration ceiling; submit prepared physical parts, not the parent clip."
        )
    if direct_submit_forbidden(item):
        duration = _story_duration(item)
        plan = video_shot_split_plan(item)
        raise RuntimeError(
            f"{item['clip']} story_duration={duration:g}s exceeds hard single video_shot cap "
            f"{VIDEO_SHOT_HARD_MAX_SEC:g}s. Do not submit a long story_clip directly. "
            "Run n2d-script shot_split_decision/anchor_planner and video_runner prepare again so it expands "
            f"into ~{plan.get('recommended_parts')} explicit physical takes within the backend window, then submit those part clips."
        )
    if not dry_run:
        enforce_sequential_qc_interlock(root, manifest_file, manifest, item)
    backend_key, adapter = resolve_video_backend({**manifest, "_root": str(root)})
    item["cost_provider"] = adapter["provider"]
    args, request_path = _adapter_invocation(root, manifest, item, adapter, "submit")
    command = args[1] if len(args) > 1 else "submit"
    safe_args = (
        [args[0], command, "--request", str(request_path)]
        if request_path else [args[0], command, "…(args elided)…"]
    )
    if dry_run:
        return {"dry_run": True, "cmd_argv": safe_args, "clip": item["clip"],
                "backend": backend_key, "backend_command": command,
                "adapter_id": adapter.get("adapter_id"), "adapter_version": adapter.get("version", 2),
                "execution_request": str(request_path) if request_path else "embedded"}
    _ensure_adapter_command_ready(adapter, args)
    # "每次都跑一遍": cheap live --help check before spending credits — fail fast if the CLI
    # contract drifted out from under the arg builder (no-op/skip if probe unavailable).
    if str(adapter.get("implementation") or "embedded") == "embedded":
        verify_cli_contract(args[0], command)
    run_identity_handoff_guard(root, episode)
    if not skip_preflight:
        run_preflight_gate(root, episode)
    else:
        # H2：--skip-preflight 不再静默旁路付费前 video_preflight 一致性闸——记 dashboard waiver 留痕欠债
        # （face-lock guard 上面已硬跑不可跳；此处仅放行更广的 preflight，且让这次松动可审计）。
        record_waiver(root, episode, "video_preflight", "skip-preflight",
                      "submit_clip --skip-preflight bypassed video_preflight consistency gate")
    item.update({"status": "submitting", "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    item.pop("fail_reason", None)
    update_manifest(manifest_file, manifest)
    started = time.time()
    proc = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    elapsed = time.time() - started
    normalized = _normalized_adapter_result(adapter, proc.stdout or "", proc.stderr or "")
    parsed = normalized.get("raw") if isinstance(normalized.get("raw"), dict) else {}
    failure = execution_adapter_v2.classify_failure(proc.returncode, normalized, proc.stderr or "")
    row = {
        "clip": item["clip"],
        "cmd_argv": safe_args,
        "image": item["image"],
        "duration": item["submit_duration"],
        "returncode": proc.returncode,
        "elapsed_sec": elapsed,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "adapter_id": adapter.get("adapter_id"),
        "adapter_version": adapter.get("version", 2),
        "request_path": str(request_path) if request_path else "",
        "failure": failure,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    append_submission_log(root, episode, row)
    item["last_submit_returncode"] = proc.returncode
    item["last_submit_elapsed_sec"] = elapsed
    item["last_submit_failure"] = failure
    item["last_submit_stdout_path"] = str(production_dir(root) / f"video_submissions_{episode}.jsonl")
    if proc.returncode != 0:
        item["status"] = "submit_failed"
        item["fail_reason"] = proc.stderr.strip() or f"exit {proc.returncode}"
    else:
        item["submit_id"] = normalized.get("submit_id") or item.get("submit_id")
        item["gen_status"] = normalized.get("status") or parsed.get("gen_status")
        item["credit_count"] = parsed.get("credit_count")
        item["logid"] = parsed.get("logid")
        if str(normalized.get("status") or "").lower() in {"fail", "failed", "error", "rejected"}:
            item["status"] = "failed"
            item["fail_reason"] = normalized.get("error") or parsed.get("fail_reason") or "generation failed"
        else:
            item["status"] = "submitted" if item.get("submit_id") else "submitted_unknown_id"
            item.pop("fail_reason", None)
    update_manifest(manifest_file, manifest)
    _record_flow_milestone(
        root, episode,
        "video_submitted" if item.get("status") in {"submitted", "submitted_unknown_id"} else "video_submit_failed",
        clip=item.get("clip"), adapter_id=adapter.get("adapter_id"), provider=adapter.get("provider"),
        status=item.get("status"), returncode=proc.returncode, elapsed_sec=elapsed,
        failure_class=failure.get("class"), retryable=failure.get("retryable"),
        paid_state_uncertain=failure.get("paid_state_uncertain"),
    )
    return item


def _mp4_set(directory: Path) -> set[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    return {p.resolve() for p in directory.glob("*.mp4")}


def _newest_mp4(directory: Path, before: set[Path], *, submit_id: str = "", since: float = 0.0) -> Optional[Path]:
    candidates = [p for p in directory.glob("*.mp4") if p.resolve() not in before]
    if submit_id:
        for path in directory.glob(f"{submit_id}*.mp4"):
            try:
                if path.stat().st_mtime + 0.001 >= since and path not in candidates:
                    candidates.append(path)
            except OSError:
                continue
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def _preserve_existing_target(target: Path, item: Dict[str, Any], *, force: bool = False) -> bool:
    if force or not target.exists():
        return False
    try:
        if target.stat().st_size < 4096:
            return False
    except OSError:
        return False
    return item.get("status") in {"downloaded", "downloaded_existing_target", "accepted"}


def _valid_downloaded_mp4(path: Path) -> bool:
    try:
        if path.stat().st_size < 4096:
            return False
    except OSError:
        return False
    try:
        proc = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return True
    if proc.returncode != 0 or not proc.stdout.strip():
        return False
    try:
        decode = subprocess.run(
            ["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-map", "0:v:0", "-f", "null", "-"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=90,
            check=False,
        )
    except FileNotFoundError:
        return True
    except subprocess.TimeoutExpired:
        return False
    return decode.returncode == 0


def _setting_value(root: Path, key: str, default: str = "") -> str:
    try:
        import settings as _settings  # type: ignore
        return str(_settings.get_setting(str(root), key, default) or default).strip()
    except Exception:
        pass
    try:
        text = (root / "_设置.md").read_text(encoding="utf-8")
    except Exception:
        return default
    match = re.search(rf"^\s*[-*]?\s*{re.escape(key)}\s*[:：]\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else default


def _prompt_text_for_item(item: Mapping[str, Any]) -> str:
    path = Path(str(item.get("prompt_file") or ""))
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _expects_silent_video_stream(root: Path, item: Mapping[str, Any],
                                 manifest: Optional[Mapping[str, Any]] = None) -> bool:
    manifest = manifest or {}
    if manifest.get("require_audio") or item.get("require_audio"):
        return False
    prompt = _prompt_text_for_item(item)
    if _requests_native_speech(prompt):
        return False
    mode = _setting_value(root, "制作模式", PRODUCTION_MODE_DEFAULT)
    policy = _setting_value(root, "视频生成音频策略", "无声视频流")
    if "原生音画" in mode or "原生音画" in policy:
        return False
    return (
        "无声" in policy
        or "silent" in policy.lower()
        or "no_native_speech" in prompt
        or "do_not_use_audio_inputs=true" in prompt
    )


def _video_has_audio_stream(path: Path) -> bool:
    if shutil.which("ffprobe") is None:
        return False
    try:
        proc = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "a",
                "-show_entries", "stream=index",
                "-of", "csv=p=0",
                str(path),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0 and bool(proc.stdout.strip())


def _enforce_silent_video_stream(root: Path, episode: str, target: Path, item: Dict[str, Any],
                                 manifest: Optional[Mapping[str, Any]]) -> bool:
    """For non-native A/V projects, keep formal video files video-only.

    Dreamina's multimodal2video currently has no no-audio flag and may return an
    AAC track even when no audio input was provided.  The raw file is preserved
    outside the formal video directory for audit, while the accepted asset stays
    aligned with `视频生成音频策略=无声视频流`.
    """
    if not target.is_file() or not _expects_silent_video_stream(root, item, manifest):
        return False
    if not _video_has_audio_stream(target):
        item.setdefault("audio_policy_enforced", "already_silent")
        return False
    if shutil.which("ffmpeg") is None:
        item["audio_policy_enforced"] = "audio_present_ffmpeg_missing"
        return False

    raw_dir = production_dir(root) / "video_raw_with_audio" / episode
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_backup = raw_dir / target.name
    if not raw_backup.exists():
        shutil.copy2(target, raw_backup)

    tmp = target.with_name(f".{target.stem}.silent.{os.getpid()}.mp4")
    proc = subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-xerror",
            "-i", str(target),
            "-map", "0:v:0",
            "-c:v", "copy",
            "-an",
            "-movflags", "+faststart",
            str(tmp),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    if proc.returncode != 0 or not _valid_downloaded_mp4(tmp) or _video_has_audio_stream(tmp):
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        item["audio_policy_enforced"] = "strip_failed"
        item["audio_policy_error"] = proc.stderr.strip() or f"ffmpeg exit {proc.returncode}"
        item["raw_with_audio_backup"] = _rel_path(root, raw_backup)
        return False

    os.replace(tmp, target)
    item["audio_policy_enforced"] = "stripped_to_silent_stream"
    item["raw_with_audio_backup"] = _rel_path(root, raw_backup)
    item.pop("audio_policy_error", None)
    return True


def _record_downloaded_file(root: Path, episode: str, item: Dict[str, Any], found: Path, *,
                            force: bool = False) -> bool:
    if not _valid_downloaded_mp4(found):
        return False
    target = formal_video_dir(root, episode) / item["target"]
    if found.resolve() == target.resolve():
        item["status"] = "downloaded_existing_target"
        item["downloaded_path"] = str(found)
        item["target_path"] = str(target)
        return True
    if _preserve_existing_target(target, item, force=force):
        item["status"] = "downloaded_existing_target"
        item["downloaded_path"] = str(found)
        item["target_path"] = str(target)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target.unlink()
        shutil.move(str(found), str(target))
        item["status"] = "downloaded"
        item["target_path"] = str(target)
    _enforce_silent_video_stream(root, episode, target, item, None)
    return True


def _record_existing_target_if_valid(root: Path, episode: str, item: Dict[str, Any]) -> bool:
    target = formal_video_dir(root, episode) / item["target"]
    if not target.is_file() or not _valid_downloaded_mp4(target):
        return False
    item["status"] = "downloaded_existing_target"
    item["downloaded_path"] = str(target)
    item["target_path"] = str(target)
    _enforce_silent_video_stream(root, episode, target, item, None)
    return True


def query_clip(root: Path, manifest_file: Path, clip: str, *, download: bool = True, force: bool = False) -> Dict[str, Any]:
    manifest = load_json(manifest_file)
    episode = manifest["episode"]
    item = find_item(manifest, clip)
    submit_id = item.get("submit_id")
    if not submit_id:
        raise RuntimeError(f"{item['clip']} has no submit_id")
    _backend_key, adapter = resolve_video_backend({**manifest, "_root": str(root)})
    download_dir = formal_video_dir(root, episode) / "_downloads"
    before = _mp4_set(download_dir)
    args, request_path = _adapter_invocation(root, manifest, item, adapter, "query")
    _ensure_adapter_command_ready(adapter, args)
    query_started_at = time.time()
    proc = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    normalized = _normalized_adapter_result(adapter, proc.stdout or "", proc.stderr or "")
    item["last_query_returncode"] = proc.returncode
    item["last_query_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    item["last_query"] = normalized.get("raw") or {"raw_stdout": proc.stdout}
    item["last_query_adapter"] = {
        "adapter_id": adapter.get("adapter_id"),
        "version": adapter.get("version", 2),
        "request_path": str(request_path) if request_path else "",
        "failure": execution_adapter_v2.classify_failure(proc.returncode, normalized, proc.stderr or ""),
    }
    if proc.returncode != 0:
        found = _newest_mp4(download_dir, before, submit_id=str(submit_id), since=query_started_at) if download else None
        if found and _record_downloaded_file(root, episode, item, found, force=force):
            item["query_warning"] = proc.stderr.strip() or f"query_result exit {proc.returncode}"
            item.pop("fail_reason", None)
            update_manifest(manifest_file, manifest)
            _record_flow_milestone(root, episode, "video_downloaded", clip=item.get("clip"),
                                   adapter_id=adapter.get("adapter_id"), status=item.get("status"))
            return item
        item["status"] = "query_failed"
        item["fail_reason"] = proc.stderr.strip() or f"query_result exit {proc.returncode}"
        update_manifest(manifest_file, manifest)
        _record_flow_milestone(root, episode, "video_query_failed", clip=item.get("clip"),
                               adapter_id=adapter.get("adapter_id"), status=item.get("status"),
                               returncode=proc.returncode,
                               failure_class=(item.get("last_query_adapter") or {}).get("failure", {}).get("class"))
        return item
    item.pop("fail_reason", None)
    query_status = str(normalized.get("status") or (item.get("last_query") or {}).get("gen_status") or "").lower()
    success_statuses = {"success", "succeeded", "completed", "done", "ready"}
    if query_status in success_statuses:
        item.pop("query_warning", None)
    wrapper_output = Path(str(normalized.get("output_path") or ""))
    if download and wrapper_output.is_file() and wrapper_output.suffix.lower() == ".mp4":
        found = wrapper_output
    else:
        found = (
            _newest_mp4(download_dir, before, submit_id=str(submit_id), since=query_started_at)
            if download and query_status in success_statuses else None
        )
    if found:
        if not _record_downloaded_file(root, episode, item, found, force=force):
            item["status"] = "query_failed"
            item["fail_reason"] = f"downloaded mp4 is invalid or incomplete: {found}"
    elif download and query_status in success_statuses and _record_existing_target_if_valid(root, episode, item):
        item.pop("fail_reason", None)
    else:
        item["status"] = "queried"
    update_manifest(manifest_file, manifest)
    _record_flow_milestone(
        root, episode,
        "video_downloaded" if item.get("status") in {"downloaded", "downloaded_existing_target"} else "video_queried",
        clip=item.get("clip"), adapter_id=adapter.get("adapter_id"), status=item.get("status"),
        returncode=proc.returncode,
    )
    return item


def cancel_clip(root: Path, manifest_file: Path, clip: str, *, dry_run: bool = False) -> Dict[str, Any]:
    """Cancel a submitted job when the selected adapter v2 exposes cancel.

    Cancellation is never emulated: if the provider wrapper does not expose it,
    the runner reports the missing operation and leaves paid state untouched.
    """
    manifest = load_json(manifest_file)
    item = find_item(manifest, clip)
    if not item.get("submit_id"):
        raise RuntimeError(f"{item.get('clip')} has no submit_id to cancel")
    _backend_key, adapter = resolve_video_backend({**manifest, "_root": str(root)})
    if "cancel" not in set(adapter.get("operations") or []):
        raise RuntimeError(
            f"adapter {adapter.get('adapter_id') or adapter.get('provider')} does not expose cancel; "
            "do not mark the paid task cancelled until the provider state is verified manually"
        )
    args, request_path = _adapter_invocation(root, manifest, item, adapter, "cancel")
    if dry_run:
        return {
            "dry_run": True,
            "clip": item.get("clip"),
            "adapter_id": adapter.get("adapter_id"),
            "request_path": str(request_path) if request_path else "",
            "cmd_argv": [args[0], "cancel", "--request", str(request_path or "embedded")],
        }
    _ensure_adapter_command_ready(adapter, args)
    proc = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    normalized = _normalized_adapter_result(adapter, proc.stdout or "", proc.stderr or "")
    item["last_cancel_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    item["last_cancel_returncode"] = proc.returncode
    item["last_cancel"] = normalized
    if proc.returncode == 0 and str(normalized.get("status") or "").lower() in {
        "cancelled", "canceled", "success", "done",
    }:
        item["status"] = "cancelled"
        item.pop("fail_reason", None)
    else:
        item["status"] = "cancel_unknown"
        item["fail_reason"] = str(normalized.get("error") or proc.stderr or "provider cancellation state is unknown").strip()
    update_manifest(manifest_file, manifest)
    _record_flow_milestone(
        root, str(manifest.get("episode") or ""),
        "video_cancelled" if item.get("status") == "cancelled" else "video_cancel_unknown",
        clip=item.get("clip"), adapter_id=adapter.get("adapter_id"), status=item.get("status"),
        returncode=proc.returncode,
    )
    return item


def _load_dashboard_module():
    path = SKILLS_DIR / "n2d-dashboard" / "scripts" / "dashboard.py"
    spec = importlib.util.spec_from_file_location("n2d_dashboard", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def qc_override_payload(clip: str, machine: Dict[str, Any]) -> Dict[str, Any]:
    """人工 --allow-qc-block 放行 seam block = 一条机检误报样本（纯函数·可测）。

    回灌 dashboard 事件流，给接缝阈值（SEAM_WARN/BLOCK·色距·跨集风格）攒校准数据：
    override 多的阈值段该放宽，从未 override 的 block 段说明阈值可信。
    """
    return {
        "qa": {
            "check": "seam_machine",
            "outcome": "human_override_false_positive",
            "seam_blocks": machine.get("seam_blocks", 0),
            "seam_warns": machine.get("seam_warns", 0),
            "intra_blocks": machine.get("intra_blocks", 0),
            "anchor_blocks": machine.get("anchor_blocks", 0),
        },
        "meta": {"clip": clip, "note": "接缝/近景片内身份机检 block 被人工放行——误报样本，供阈值校准"},
    }


def qc_block_payload(item: Dict[str, Any]) -> Dict[str, Any]:
    machine = item.get("qc_machine") if isinstance(item.get("qc_machine"), dict) else {}
    clip = str(item.get("clip") or "?")
    reason = str(item.get("fail_reason") or "video QC blocked")
    return {
        "qa": {
            "severity": "block",
            "dim": "成片身份回验",
            "loc": clip,
            "msg": reason,
            "check": "post_video_qc",
            "outcome": "qc_blocked",
            "seam_blocks": machine.get("seam_blocks", 0),
            "intra_blocks": machine.get("intra_blocks", 0),
            "intra_warns": machine.get("intra_warns", 0),
            "anchor_blocks": machine.get("anchor_blocks", 0),
            "anchor_warns": machine.get("anchor_warns", 0),
        },
        "meta": {
            "clip": clip,
            "target": item.get("target") or "",
            "qc_json": item.get("qc_json") or "",
            "qc_markdown": item.get("qc_markdown") or "",
            "post_video_qc": item.get("post_video_qc") if isinstance(item.get("post_video_qc"), dict) else {},
            "return_to_stage": "video",
        },
    }


def _ensure_dense_face_watch_packet(root: Path, episode: str, item: Dict[str, Any],
                                    target: Path) -> None:
    policy = item.get("post_video_qc") if isinstance(item.get("post_video_qc"), dict) else {}
    if policy.get("dense_face_watch_required") is not True:
        return
    if os.environ.get("N2D_SKIP_DENSE_FACE_WATCH") == "1":
        item["video_face_drift_watch"] = {"status": "skipped_by_env"}
        return
    script = SKILLS_DIR / "n2d-review" / "scripts" / "video_face_drift_watch.py"
    if not script.is_file():
        item["video_face_drift_watch"] = {"status": "missing_script", "script": str(script)}
        return
    cmd = [
        sys.executable,
        str(script),
        str(root),
        episode,
        "--video",
        str(target),
        "--clip",
        str(item.get("clip") or ""),
        "--interval",
        "0.5",
        "--max-frames",
        "80",
        "--write",
        "--json",
    ]
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=180)
    except Exception as exc:  # pragma: no cover - defensive around local ffmpeg/process state
        item["video_face_drift_watch"] = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
        return
    payload: Dict[str, Any] = {"status": "error", "returncode": proc.returncode}
    try:
        payload = json.loads(proc.stdout[proc.stdout.find("{"):])
    except Exception:
        payload["stdout_tail"] = proc.stdout[-500:]
        payload["stderr_tail"] = proc.stderr[-500:]
    item["video_face_drift_watch"] = {
        "status": payload.get("status") or ("ok" if proc.returncode == 0 else "error"),
        "json_path": payload.get("json_path") or "",
        "markdown_path": payload.get("markdown_path") or "",
        "contact_sheet": payload.get("contact_sheet") or "",
        "frames": len(payload.get("frames") or []) if isinstance(payload.get("frames"), list) else 0,
        "returncode": proc.returncode,
    }


def record_qc_override(root: Path, episode: str, item: Dict[str, Any]) -> None:
    dashboard = _load_dashboard_module()
    payload = qc_override_payload(item.get("clip", "?"), item.get("qc_machine") or {})
    event = dashboard.make_event(episode, "video", "qa", source="n2d-video/video_runner.py", **payload)
    dashboard.append_events(str(root), [event])


def record_qc_block(root: Path, episode: str, item: Dict[str, Any]) -> None:
    dashboard = _load_dashboard_module()
    payload = qc_block_payload(item)
    event = dashboard.make_event(episode, "video", "qa", source="n2d-video/video_runner.py", **payload)
    dashboard.append_events(str(root), [event])


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_path_for_root(root: Path, path: Any) -> Path:
    raw = str(path or "").strip()
    if not raw:
        return Path()
    p = Path(raw)
    if p.is_absolute():
        return p
    root_abs = root.resolve()
    try:
        cwd_path = p.resolve(strict=False)
        if p.exists() and cwd_path.is_relative_to(root_abs):
            return cwd_path
    except Exception:
        pass
    parts = p.parts
    if root.name in parts:
        for idx in range(len(parts) - 1, -1, -1):
            if parts[idx] != root.name:
                continue
            suffix_parts = parts[idx + 1:]
            if suffix_parts:
                return root.joinpath(*suffix_parts)
    return root / p


def _rel_path(root: Path, path: Any) -> str:
    if not str(path or "").strip():
        return ""
    try:
        return str(_resolve_path_for_root(root, path).resolve(strict=False).relative_to(root.resolve()))
    except Exception:
        return str(path or "")


def _existing_file_digest(root: Path, path: Any) -> str:
    p = _resolve_path_for_root(root, path)
    if p.is_file():
        return f"{_rel_path(root, p)}:{_sha256_file(p)}"
    return f"{_rel_path(root, p)}:missing"


def _raw_image_inputs(item: Dict[str, Any]) -> List[str]:
    multiframe = [str(value) for value in item.get("multiframe_images") or [] if value]
    if multiframe:
        return multiframe
    images: List[str] = []
    for key in ("image", "end_image"):
        value = item.get(key)
        if value:
            images.append(str(value))
    return images


def _actual_image_inputs(item: Dict[str, Any]) -> List[str]:
    explicit = item.get("actual_image_inputs")
    if isinstance(explicit, list) and explicit:
        return [str(value) for value in explicit if str(value or "").strip()]
    return _raw_image_inputs(item)


def _capability_evidence_id(root: Path) -> str:
    cap_dir = production_dir(root) / "video_backend_capabilities"
    files = sorted(p for p in cap_dir.glob("*.json") if p.is_file())
    return _rel_path(root, files[0]) if files else "video_backend_capabilities/not_recorded"


def _route_hash(root: Path, episode: str) -> str:
    path = root / "出视频" / episode / "prompt" / "video_model_routes.json"
    return _sha256_file(path) if path.is_file() else "video_model_routes_missing"


def _file_sha_or_empty(root: Path, rel: str) -> str:
    path = root / rel
    return _sha256_file(path) if path.is_file() else ""


def _artifact_sha(root: Path, path_value: Any) -> str:
    path = _resolve_path_for_root(root, path_value)
    return _sha256_file(path) if path.is_file() else ""


def _item_target_path(root: Path, episode: str, item: Dict[str, Any]) -> Path:
    if item.get("target_path"):
        return _resolve_path_for_root(root, item.get("target_path"))
    if item.get("target"):
        return formal_video_dir(root, episode) / str(item["target"])
    return Path()


def _route_for_clip(root: Path, episode: str, clip_id: str) -> Dict[str, Any]:
    wanted = _base_clip_id(clip_id)
    path = root / "出视频" / episode / "prompt" / "video_model_routes.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    routes = data.get("routes") if isinstance(data, dict) else None
    if isinstance(routes, dict):
        route = routes.get(clip_id)
        return dict(route) if isinstance(route, dict) else {}
    if isinstance(routes, list):
        for route in routes:
            if not isinstance(route, dict):
                continue
            route_clip = str(route.get("clip_id") or route.get("clip") or route.get("id") or "")
            if route_clip == clip_id or _base_clip_id(route_clip) == wanted:
                return dict(route)
    return {}


def _post_video_qc_for_item(root: Path, episode: str, item: Dict[str, Any],
                            route: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    route_data = dict(route) if isinstance(route, Mapping) else _route_for_clip(root, episode, _base_clip_id(item.get("clip")))
    recipe = route_data.get("execution_recipe") if isinstance(route_data.get("execution_recipe"), Mapping) else {}
    policy = recipe.get("post_video_qc") if isinstance(recipe.get("post_video_qc"), Mapping) else route_data.get("post_video_qc")
    if isinstance(policy, Mapping) and policy:
        return dict(policy)
    item_policy = item.get("post_video_qc")
    if isinstance(item_policy, Mapping) and item_policy:
        return dict(item_policy)
    return {}


def refresh_item_recipe_evidence(root: Path, episode: str, item: Dict[str, Any],
                                 manifest: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    route = _route_for_clip(root, episode, _base_clip_id(item.get("clip")))
    item["route_clip_id"] = _base_clip_id(item.get("clip"))
    item["route_hash"] = _route_hash(root, episode)
    if route:
        item["route_primary_backend"] = route.get("primary_backend") or ""
        item["route_mode"] = route.get("mode") or ""
        recipe = route.get("execution_recipe")
        if isinstance(recipe, Mapping):
            item["route_execution_recipe_hash"] = _sha256_text(json.dumps(recipe, ensure_ascii=False, sort_keys=True))
        policy = _post_video_qc_for_item(root, episode, item, route)
        if policy:
            item["post_video_qc"] = policy
    images = _raw_image_inputs(item)
    item["actual_image_inputs"] = [_rel_path(root, p) for p in images]
    item["reference_bundle_sha256"] = _sha256_text("\n".join(_existing_file_digest(root, p) for p in images))
    if manifest is not None:
        item["manifest_backend"] = str(manifest.get("backend") or "")
        item["manifest_model_version"] = str(manifest.get("model_version") or "")
    return item


def acceptance_recipe_meta(root: Path, episode: str, item: Dict[str, Any], manifest: Dict[str, Any]) -> Dict[str, Any]:
    backend = str(manifest.get("backend") or item.get("cost_provider") or "dreamina")
    model_version = str(item.get("model_version") or manifest.get("model_version") or "unknown")
    video_resolution = str(manifest.get("video_resolution") or "unknown")
    route = _route_for_clip(root, episode, str(item.get("clip") or ""))
    post_qc = _post_video_qc_for_item(root, episode, item, route)
    prompt_path = Path(str(item.get("prompt_file") or ""))
    prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else ""
    prompt = _append_dialogue_fact_contract(
        prompt,
        item,
        {**manifest, "_root": str(root)},
        enforce_submit_guard=False,
    )
    images = _actual_image_inputs(item)
    image_rels = [_rel_path(root, p) for p in images]
    reference_bundle_sha256 = _sha256_text("\n".join(_existing_file_digest(root, p) for p in images))
    settings_sha256 = _file_sha_or_empty(root, "_设置.md")
    identity_registry_sha256 = _file_sha_or_empty(root, "出图/共享/identity_registry.json")
    asset_registry_sha256 = _file_sha_or_empty(root, "出图/共享/asset_registry.json")
    route_hash = _route_hash(root, episode)
    recipe = route.get("execution_recipe") if isinstance(route.get("execution_recipe"), Mapping) else {}
    target_path = _item_target_path(root, episode, item)
    artifact_sha256 = _artifact_sha(root, target_path)
    mode = str(route.get("mode") or item.get("mode_backend") or item.get("mode") or "accepted_existing_video")
    meta = {
        "provider": item.get("cost_provider") or backend,
        "model": f"{backend}:{model_version}",
        "mode": mode,
        "channel": backend,
        "route_hash": route_hash,
        "capability_evidence_id": _capability_evidence_id(root),
        "prompt_sha256": _sha256_text(prompt),
        "reference_bundle_sha256": reference_bundle_sha256,
        "backend_version": model_version,
        "quality_tier": video_resolution,
        "actual_image_inputs": image_rels,
        "settings_sha256": settings_sha256,
        "identity_registry_sha256": identity_registry_sha256,
        "asset_registry_sha256": asset_registry_sha256,
        "artifact_sha256": artifact_sha256,
        "route_execution_recipe_hash": _sha256_text(json.dumps(recipe, ensure_ascii=False, sort_keys=True)) if recipe else "",
        "post_video_qc": post_qc,
        "adapter_version": "n2d-video.video_runner.acceptance_recipe.v2",
        "qc_version": "n2d-video.video_qc.v1",
        "seed_effective": False,
        "effective_seed": "none",
        "seed_support": "unsupported_or_unknown",
        "frame_control_mode": item.get("frame_control_mode") or "",
        "anchor_consumption_mode": item.get("anchor_consumption_mode") or "",
        "submit_id": item.get("submit_id") or "",
    }
    fingerprint_payload = {
        "asset": _rel_path(root, target_path),
        "mode": mode,
        "route_hash": route_hash,
        "prompt_sha256": meta["prompt_sha256"],
        "reference_bundle_sha256": reference_bundle_sha256,
        "settings_sha256": settings_sha256,
        "identity_registry_sha256": identity_registry_sha256,
        "asset_registry_sha256": asset_registry_sha256,
        "artifact_sha256": artifact_sha256,
    }
    meta["input_fingerprint"] = _sha256_text(json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True))
    recipe_payload = {
        "provider": meta["provider"],
        "model": meta["model"],
        "mode": meta["mode"],
        "channel": meta["channel"],
        "route_hash": meta["route_hash"],
        "prompt_sha256": meta["prompt_sha256"],
        "reference_bundle_sha256": meta["reference_bundle_sha256"],
        "backend_version": meta["backend_version"],
        "quality_tier": meta["quality_tier"],
        "actual_image_inputs": meta["actual_image_inputs"],
        "settings_sha256": settings_sha256,
        "identity_registry_sha256": identity_registry_sha256,
        "asset_registry_sha256": asset_registry_sha256,
        "artifact_sha256": artifact_sha256,
        "route_execution_recipe_hash": meta["route_execution_recipe_hash"],
        "post_video_qc": post_qc,
        "input_fingerprint": meta["input_fingerprint"],
        "submit_id": meta["submit_id"],
    }
    meta["recipe_hash"] = _sha256_text(json.dumps(recipe_payload, ensure_ascii=False, sort_keys=True))
    return meta


def record_acceptance(root: Path, episode: str, item: Dict[str, Any], qc_clip: Optional[Dict[str, Any]],
                      manifest: Optional[Dict[str, Any]] = None) -> None:
    dashboard = _load_dashboard_module()
    asset_rel = _rel_path(root, _item_target_path(root, episode, item))
    cost = None
    if item.get("credit_count") is not None:
        cost = {
            "amount": item.get("credit_count"),
            "currency": "credits",
            "unit": "credits",
            "provider": item.get("cost_provider") or "dreamina",
        }
    duration = item.get("last_submit_elapsed_sec")
    meta = acceptance_recipe_meta(root, episode, item, manifest or {"episode": episode})
    meta["native_audio"] = "unknown"
    if qc_clip and qc_clip.get("has_audio") is not None:
        meta["native_audio"] = "yes" if qc_clip.get("has_audio") else "no"
    machine = item.get("qc_machine") or {}
    if machine.get("seams_checked"):
        meta["seam_check"] = "block" if machine.get("seam_blocks") else ("warn" if machine.get("seam_warns") else "pass")
    if machine.get("intra_checked"):
        meta["intra_identity_check"] = "block" if machine.get("intra_blocks") else ("warn" if machine.get("intra_warns") else "pass")
    if machine.get("anchor_checked"):
        meta["anchor_adherence_check"] = "block" if machine.get("anchor_blocks") else ("warn" if machine.get("anchor_warns") else "pass")
    event = dashboard.make_event(
        episode,
        "video",
        "generation",
        source="n2d-video/video_runner.py",
        cost=cost,
        duration_sec=duration,
        generation={"asset": asset_rel, "status": "pass"},
        meta=meta,
    )
    submit_id = str(item.get("submit_id") or "")

    def same_generation(existing: Dict[str, Any]) -> bool:
        generation = existing.get("generation") if isinstance(existing.get("generation"), dict) else {}
        existing_meta = existing.get("meta") if isinstance(existing.get("meta"), dict) else {}
        return (
            existing.get("episode") == episode
            and existing.get("stage") == "video"
            and existing.get("event") == "generation"
            and generation.get("asset") == asset_rel
            and str(existing_meta.get("submit_id") or "") == submit_id
        )

    dashboard.replace_events(str(root), same_generation, [event])
    dashboard.build(str(root), write=True)


def count_formal_clips(root: Path, episode: str) -> int:
    logical_clips = set()
    for path in formal_video_dir(root, episode).glob("Clip*.mp4"):
        if ".noaudio" in path.name or "_noaudio" in path.name:
            continue
        match = re.match(r"Clip[_-]?(\d+)", path.name, re.IGNORECASE)
        logical_clips.add(f"Clip_{int(match.group(1)):02d}" if match else path.stem)
    return len(logical_clips)


def count_accepted_clips(root: Path, episode: str) -> int:
    """Count accepted logical clips; MP4 presence alone only proves download."""
    logical_clips = set()
    for path in (root / "生产数据").glob(f"video_batch_{episode}_*.json"):
        data = load_json(path)
        for item in data.get("items") or []:
            if not isinstance(item, dict) or str(item.get("status") or "").lower() != "accepted":
                continue
            raw = str(item.get("story_clip") or item.get("relay_parent") or item.get("clip") or "")
            match = re.search(r"Clip[_-]?(\d+)", raw, re.IGNORECASE)
            if match:
                logical_clips.add(f"Clip_{int(match.group(1)):02d}")
    return len(logical_clips)


def progress_denominator(root: Path, episode: str) -> int:
    if parse_progress is not None:
        try:
            header, rows = parse_progress(str(root))
            for row in rows:
                if row.get("_ep") == episode:
                    cell = str(row.get("视频") or "")
                    match = re.search(r"/\s*(\d+)", cell)
                    if match:
                        return int(match.group(1))
        except Exception:
            pass
    try:
        return len(split_clip_blocks(prompt_pack_path(root, episode).read_text(encoding="utf-8")))
    except Exception:
        return 0


def update_progress(root: Path, episode: str) -> None:
    total = progress_denominator(root, episode)
    if total <= 0:
        return
    count = count_accepted_clips(root, episode)
    progress_py = SKILLS_DIR / "n2d" / "progress.py"
    subprocess.run([sys.executable, str(progress_py), "set", str(root), episode, "视频", f"{count}/{total}"], check=False)


def maybe_build_post_video_proxy(root: Path, episode: str) -> Dict[str, Any]:
    """Refresh OTIO/assembly after every accepted clip; render once complete.

    Best-effort by design: clip delivery remains valid on a clean machine without
    ffmpeg, while the proxy script records a resumable ``planned_ffmpeg_missing``
    state instead of fabricating a playable asset.
    """
    total = progress_denominator(root, episode)
    count = count_accepted_clips(root, episode)
    script = SKILLS_DIR / "n2d-compose" / "scripts" / "post_video_proxy.py"
    if not script.is_file():
        return {"status": "script_missing", "path": str(script)}
    args = [sys.executable, str(script), str(root), episode]
    if total > 0 and count >= total:
        args.append("--render")
    args.append("--json")
    proc = subprocess.run(
        args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        payload = {"status": "error", "stdout": proc.stdout}
    if not isinstance(payload, dict):
        payload = {"status": "error", "stdout": proc.stdout}
    payload["returncode"] = proc.returncode
    if proc.stderr.strip():
        payload["stderr"] = proc.stderr.strip()[-800:]
    return payload


def _post_video_qc_block_reasons(policy: Mapping[str, Any], machine: Mapping[str, Any]) -> List[str]:
    if not policy or policy.get("identity_qc_required") is not True:
        return []
    dense = policy.get("dense_face_watch_required") is True
    if not dense:
        return []
    reasons: List[str] = []
    if int(machine.get("intra_checked") or 0) <= 0:
        reasons.append(
            "成片身份回验 block：本镜要求 dense_face_watch，但 video_qc 没有覆盖片内近脸身份采样；"
            "请补 temporal_consistency/video_face_drift_watch 证据或回退低风险构图后重出"
        )
    if int(machine.get("intra_warns") or 0) > 0:
        reasons.append(
            f"成片身份回验 block：dense_face_watch 镜出现片内身份 warn×{machine.get('intra_warns')}；"
            "warn=粗筛交人判，不能静默 accept"
        )
    return reasons


def stamp_acceptance_recipe_meta(root: Path, episode: str, item: Dict[str, Any],
                                 manifest: Mapping[str, Any]) -> Dict[str, Any]:
    refresh_item_recipe_evidence(root, episode, item, manifest)
    meta = acceptance_recipe_meta(root, episode, item, dict(manifest))
    for key in (
        "recipe_hash",
        "prompt_sha256",
        "reference_bundle_sha256",
        "backend_version",
        "quality_tier",
        "actual_image_inputs",
        "route_hash",
        "route_execution_recipe_hash",
        "input_fingerprint",
        "artifact_sha256",
        "post_video_qc",
        "seed_effective",
        "effective_seed",
        "seed_support",
    ):
        if key in meta:
            item[key] = meta[key]
    return meta


def accept_clip(root: Path, manifest_file: Path, clip: str, *, no_record: bool = False, no_progress: bool = False,
                allow_qc_block: bool = False, visual_reviewer: str = "", visual_notes: str = "",
                visual_current_pixels_confirmed: bool = False) -> Dict[str, Any]:
    manifest = load_json(manifest_file)
    episode = manifest["episode"]
    item = find_item(manifest, clip)
    target = _item_target_path(root, episode, item)
    if not target.exists():
        raise FileNotFoundError(target)
    reviewer = str(visual_reviewer or "").strip()
    notes = str(visual_notes or "").strip()
    if not reviewer or len(notes) < 4 or visual_current_pixels_confirmed is not True:
        raise RuntimeError(
            f"{item['clip']} accept requires actual visual inspection of the current MP4: "
            "provide --visual-reviewer, --visual-notes and --confirm-current-pixels. "
            "Do not claim a human reviewer unless a human actually reviewed it."
        )
    if _enforce_silent_video_stream(root, episode, target, item, manifest):
        update_manifest(manifest_file, manifest)
    qc_range = f"{item['clip'].split('_')[1]}_{item['clip'].split('_')[1]}"
    qc = video_qc.run_qc(root, episode, [target], qc_range, clip_keys=[item.get("clip")])
    qc_clip = qc["clips"][0] if qc.get("clips") else None
    machine = qc.get("machine_summary") or {}
    item["qc_machine"] = machine
    post_qc_policy = _post_video_qc_for_item(root, episode, item)
    if post_qc_policy:
        item["post_video_qc"] = post_qc_policy
    post_qc_reasons = _post_video_qc_block_reasons(post_qc_policy, machine)
    anchor_blocks = int(machine.get("anchor_blocks") or 0)
    native_anchor_expected = item.get("anchor_consumption_mode") == "native_multiframe"
    qc_blocks = (
        int(machine.get("seam_blocks") or 0)
        + int(machine.get("intra_blocks") or 0)
        + (anchor_blocks if native_anchor_expected else 0)
        + len(post_qc_reasons)
    )
    if qc_blocks and not allow_qc_block:
        reasons = []
        if machine.get("seam_blocks"):
            reasons.append(f"接缝机检 block×{machine['seam_blocks']}（continuous_take_relay 边界帧未接上）")
        if machine.get("intra_blocks"):
            reasons.append(f"近景片内身份 block×{machine['intra_blocks']}（脸被表情带着重画，非双帧接力镜）")
        if native_anchor_expected and machine.get("anchor_blocks"):
            reasons.append(f"中段锚帧对账 block×{machine['anchor_blocks']}（声明原生消费中锚，但生成视频中段明显偏离锚帧）")
        reasons.extend(post_qc_reasons)
        item["status"] = "qc_blocked"
        item["target_path"] = str(target)
        item["qc_json"] = qc.get("json_path")
        item["qc_markdown"] = qc.get("markdown_path")
        item["fail_reason"] = "；".join(reasons) + "。重出本镜或确认误报后 --allow-qc-block 强制验收"
        stamp_acceptance_recipe_meta(root, episode, item, manifest)
        update_manifest(manifest_file, manifest)
        if not no_record:
            record_qc_block(root, episode, item)
        _record_flow_milestone(root, episode, "video_qc_blocked", clip=item.get("clip"),
                               status=item.get("status"), artifact=str(target))
        raise RuntimeError(f"{item['clip']} {item['fail_reason']}（详见 {qc.get('markdown_path')}）")
    overridden = bool(qc_blocks) and allow_qc_block
    item["status"] = "accepted"
    item["qc_overridden"] = overridden
    item["target_path"] = str(target)
    item["qc_json"] = qc.get("json_path")
    item["qc_markdown"] = qc.get("markdown_path")
    item["accepted_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    stamp_acceptance_recipe_meta(root, episode, item, manifest)
    item["visual_review"] = {
        "kind": "n2d_video_visual_review",
        "version": 1,
        "verdict": "pass",
        "reviewer": reviewer,
        "reviewed_at": item["accepted_at"],
        "artifact_path": str(target),
        "artifact_sha256": _sha256_file(target),
        "explicit_current_pixels_confirmation": True,
        "criteria": [
            "角色身份/五官/发型/服装一致",
            "人体/手部/持物/接触/穿模",
            "动作物理/镜头意图/构图",
            "接缝/时序/闪烁/画面完整性",
            "音轨策略/字幕安全区（如适用）",
        ],
        "notes": notes,
    }
    try:
        item["native_av_sidecar"] = native_av_sidecar.update_sidecars(root, episode, item, target, qc_clip)
    except Exception as exc:
        item["native_av_sidecar"] = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
    _ensure_dense_face_watch_packet(root, episode, item, target)
    update_manifest(manifest_file, manifest)
    if not no_record:
        if overridden:
            record_qc_override(root, episode, item)
        record_acceptance(root, episode, item, qc_clip, manifest)
    if not no_progress:
        update_progress(root, episode)
    item["post_video_proxy"] = maybe_build_post_video_proxy(root, episode)
    update_manifest(manifest_file, manifest)
    _record_flow_milestone(
        root, episode, "video_accepted", clip=item.get("clip"), status=item.get("status"),
        provider=item.get("cost_provider"), artifact=str(target),
        artifact_sha256=item.get("artifact_sha256"),
    )
    return item


def run_batch_qc(root: Path, manifest_file: Path) -> Dict[str, Any]:
    manifest = load_json(manifest_file)
    episode = manifest["episode"]
    clips = []
    clip_keys = []
    for item in manifest.get("items", []):
        target = _item_target_path(root, episode, item)
        if target.exists():
            clips.append(target)
            clip_keys.append(item.get("clip"))
    if not clips:
        raise RuntimeError("no downloaded target clips in manifest")
    return video_qc.run_qc(root, episode, clips, manifest.get("batch_id") or manifest.get("batch", "batch").replace("-", "_"),
                           clip_keys=clip_keys)


def status_summary(manifest: Dict[str, Any]) -> str:
    counts: Dict[str, int] = {}
    for item in manifest.get("items", []):
        counts[item.get("status", "unknown")] = counts.get(item.get("status", "unknown"), 0) + 1
    lines = [f"{manifest.get('episode')} {manifest.get('batch')} {counts}"]
    for item in manifest.get("items", []):
        sid = f" submit_id={item.get('submit_id')}" if item.get("submit_id") else ""
        lines.append(f"- {item.get('clip')} {item.get('status')}{sid} target={item.get('target')}")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prepare")
    p.add_argument("root")
    p.add_argument("episode")
    p.add_argument("--range", required=True)
    p.add_argument("--backend", default="dreamina")
    p.add_argument("--resolution", default="auto", help="auto reads _设置.md 视频分辨率; default 720p")
    p.add_argument("--model-version", default="auto",
                   help="auto reads _设置.md: ordinary=seedance2.0fast, high/budget-sufficient=seedance2.0_vip")
    p.add_argument("--force", action="store_true")

    for name in ("submit", "query", "cancel", "accept"):
        p = sub.add_parser(name)
        p.add_argument("root")
        p.add_argument("manifest")
        p.add_argument("--clip", required=True)
        if name == "submit":
            p.add_argument("--dry-run", action="store_true")
            p.add_argument("--skip-preflight", action="store_true",
                           help="skip default video_preflight gate before backend submission")
        if name == "query":
            p.add_argument("--no-download", action="store_true")
            p.add_argument("--force", action="store_true")
        if name == "cancel":
            p.add_argument("--dry-run", action="store_true")
        if name == "accept":
            p.add_argument("--no-record", action="store_true")
            p.add_argument("--no-progress", action="store_true")
            p.add_argument("--allow-qc-block", action="store_true",
                           help="接缝机检 block 时仍强制验收（确认是误报/有意跳切再用）")
            p.add_argument("--visual-reviewer", default="",
                           help="实际查看当前 MP4 的执行者；不要伪造真人身份")
            p.add_argument("--visual-notes", default="",
                           help="实际查看结论，至少说明身份/人体/动作/接缝等检查结果")
            p.add_argument("--confirm-current-pixels", action="store_true",
                           help="确认查看的是当前磁盘 MP4，而非旧预览/缩略图")

    p = sub.add_parser("qc")
    p.add_argument("root")
    p.add_argument("manifest")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("status")
    p.add_argument("manifest")

    ns = ap.parse_args(argv)
    if ns.cmd == "prepare":
        start, end = video_qc.parse_clip_range(ns.range)
        payload = prepare_manifest(
            Path(ns.root).expanduser().resolve(),
            ns.episode,
            start,
            end,
            backend=ns.backend,
            resolution=ns.resolution,
            model_version=ns.model_version,
            force=ns.force,
        )
        print(manifest_path(Path(ns.root).expanduser().resolve(), normalize_episode(ns.episode), start, end))
        print(status_summary(payload))
        return 0
    if ns.cmd == "status":
        print(status_summary(load_json(Path(ns.manifest))))
        return 0
    root = Path(ns.root).expanduser().resolve()
    manifest_file = Path(ns.manifest).expanduser().resolve()
    if ns.cmd == "submit":
        print(json.dumps(submit_clip(root, manifest_file, ns.clip, dry_run=ns.dry_run,
                                     skip_preflight=ns.skip_preflight), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if ns.cmd == "query":
        print(json.dumps(query_clip(root, manifest_file, ns.clip, download=not ns.no_download, force=ns.force), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if ns.cmd == "cancel":
        print(json.dumps(cancel_clip(root, manifest_file, ns.clip, dry_run=ns.dry_run), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if ns.cmd == "accept":
        print(json.dumps(accept_clip(root, manifest_file, ns.clip, no_record=ns.no_record, no_progress=ns.no_progress,
                                     allow_qc_block=ns.allow_qc_block,
                                     visual_reviewer=ns.visual_reviewer,
                                     visual_notes=ns.visual_notes,
                                     visual_current_pixels_confirmed=ns.confirm_current_pixels),
                         ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if ns.cmd == "qc":
        payload = run_batch_qc(root, manifest_file)
        if ns.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(payload["markdown_path"])
        summary = payload.get("machine_summary") or {}
        return 1 if (summary.get("seam_blocks") or summary.get("anchor_blocks")) else 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
