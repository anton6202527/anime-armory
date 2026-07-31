#!/usr/bin/env python3
"""Shared per-project settings helpers.

The user-facing convention lives in `skills/song/song-craft/references/选择点与偏好.md`. This module only
implements deterministic read/write helpers for `_设置.md`; it does not ask
questions or infer preferences.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

# 本线自包含：视频后端/制作模式在本文件内提供通用兜底，保持 settings.py 零外部依赖。
VIDEO_BACKEND_ALIASES = {}

def normalize_video_backend(value: Optional[str], default: str = "dreamina") -> str:
    return (value or default or "").strip().lower()

_PRODUCTION_MODE_DEFAULT = "配音先行"
_PRODUCTION_MODE_KEYS = ("配音先行", "先出视频后配音", "原生音画")


DEFAULTS = {
    "制作模式": _PRODUCTION_MODE_DEFAULT,
    "基础视觉风格": "写实电影感",
    "生图AI": "Codex",
    "生视频模型": "Seedance 2.0",
    "生视频渠道": "即梦/Dreamina",
    # Legacy combined key. New projects should write `生视频模型` + `生视频渠道`.
    "生视频AI": "即梦",
    "视频模型路由": "自动按镜头路由",
    "视频备用后端": "",
    "中段锚帧默认": "开启",
    "重抽预算策略": "预算充足",
    "出视频规格": "预算一般",
    "视频原生音轨": "丢弃",
    "水印": "AI合规标识",
    "字幕语言": "中文",
}


FAMILY_ROOTS = {
    "写歌": "song",
}

FAMILY_MARKERS = {
    "song": (("词", "lyrics.md"),),
}


@dataclass(frozen=True)
class SettingSpec:
    """Machine-readable preference contract for settings management.

    The prose source of truth remains `skills/song/song-craft/references/选择点与偏好.md`; this compact schema
    is only the executable subset needed for safe patching, audit, and sync.
    """

    key: str
    families: Tuple[str, ...] = ("all",)
    allowed: Tuple[str, ...] = ()
    aliases: Dict[str, str] = field(default_factory=dict)
    key_aliases: Tuple[str, ...] = ()
    parameterized: bool = False
    composite: bool = False
    syncable: bool = True
    metadata: bool = False
    sensitive: bool = False


def _video_aliases() -> Dict[str, str]:
    aliases = {str(k).lower(): str(v) for k, v in VIDEO_BACKEND_ALIASES.items()}
    aliases.update({
        "即梦": "dreamina",
        "dreamina": "dreamina",
        "dreamina/即梦": "dreamina",
        "dreamina/即梦官方 cli": "dreamina",
        "可灵": "kling",
        "kling": "kling",
        "seedance": "seedance",
        "veo": "veo",
        "sora": "sora",
        "runway": "runway",
        "manual": "manual",
    })
    return aliases


VIDEO_BACKEND_SETTING_ALIASES = _video_aliases()

VIDEO_MODEL_CHOICES = (
    "Seedance 2.0", "Seedance",
    "Veo 3.1", "Veo",
    "Kling 3.0", "Kling",
    "Hailuo 02", "Hailuo 2.3", "Hailuo",
    "Runway Gen-4", "Runway",
    "Luma Ray3.2", "Luma",
    "Pika 2.5", "Pika",
    "HunyuanVideo 1.5", "HunyuanVideo",
    "Wan 2.2", "Wan 2.x", "Wan",
    "LTX-2.3", "LTX",
    "Sora",
    "manual",
)

VIDEO_CHANNEL_CHOICES = (
    "即梦/Dreamina", "即梦", "Dreamina",
    "豆包",
    "海螺AI", "Hailuo",
    "可灵/Kling", "可灵", "Kling",
    "Google Gemini API",
    "Runway API", "Runway",
    "Luma Dream Machine", "Luma",
    "Pika",
    "本地/开源",
    "manual",
)


SETTING_SPECS: Tuple[SettingSpec, ...] = (
    SettingSpec("歌曲用途", ("song",), ("短视频Hook", "完整Demo", "发行母带前草稿", "自定义"), parameterized=True),
    SettingSpec("目标时长", ("song",), ("30s", "45s", "60s", "90s", "120s", "180s", "自定义"), parameterized=True),
    SettingSpec("语言", ("song",), ("中文", "英文", "中英双语", "其他"), parameterized=True),
    SettingSpec("BPM/速度", ("song",), ("慢速", "中速", "快速", "自定义BPM"), parameterized=True),
    SettingSpec("调性", ("song",), ("未定", "C", "D", "E", "F", "G", "A", "B", "Am", "Dm", "Em", "自定义"), parameterized=True),
    SettingSpec("作曲后端", ("song",), ("Suno", "Udio", "ACE-Step", "DiffRhythm", "manual"), parameterized=True),
    SettingSpec("生成版数", ("song",), ("1", "2", "4", "6", "8")),
    SettingSpec("挑版策略", ("song",), ("最佳hook", "最佳人声", "最贴蓝图", "最贴成品用途", "人工挑版")),
    SettingSpec("翻唱后端", ("song",), ("RVC", "so-vits-svc")),
    SettingSpec("演唱音色", ("song",), ("自有嗓", "授权音色", "合成音色"), key_aliases=("演唱音色(合规·需声明)",), sensitive=True),
    SettingSpec("AI音频使用披露", ("song",), ("AI-generated", "AI-assisted", "未使用AI音频"), sensitive=True),
)


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def detect_family(work_root: str) -> str:
    root = os.path.abspath(work_root)
    parts = root.split(os.sep)
    for part in reversed(parts):
        if part in FAMILY_ROOTS:
            return FAMILY_ROOTS[part]
    for family, markers in FAMILY_MARKERS.items():
        for marker in markers:
            if os.path.exists(os.path.join(root, *marker)):
                return family
    return "all"


def setting_specs(family: Optional[str] = None) -> List[SettingSpec]:
    family = family or "all"
    return [
        spec for spec in SETTING_SPECS
        if "all" in spec.families or family == "all" or family in spec.families
    ]


def get_setting_spec(key: str, family: Optional[str] = None) -> Optional[SettingSpec]:
    family = family or "all"
    # Prefer family-local definitions if a key appears in multiple production lines.
    candidates = setting_specs(family)
    for spec in candidates:
        if key == spec.key or key in spec.key_aliases:
            return spec
    for spec in SETTING_SPECS:
        if key == spec.key or key in spec.key_aliases:
            return spec
    return None


def canonical_setting_key(key: str, family: Optional[str] = None) -> str:
    spec = get_setting_spec(key, family)
    return spec.key if spec else key


def repo_root_from(path: str) -> str:
    """Walk upward until the repository root is found."""
    d = os.path.abspath(path)
    if os.path.isfile(d):
        d = os.path.dirname(d)
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, "skills")):
            return d
        d = os.path.dirname(d)
    return os.path.abspath(path)


def _read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _extract_setting(text: str, key: str) -> Optional[str]:
    """Return a setting value from common markdown forms."""
    key_pattern = rf"(?:\*\*)?{re.escape(key)}(?:\*\*)?"
    pat = re.compile(rf"^\s*(?:[-*]\s*)?{key_pattern}\s*[:：]\s*(.+?)\s*$", re.M)
    for line in _settings_region_lines(text):
        m = pat.match(line)
        if m:
            val = re.split(r"\s+#", m.group(1), maxsplit=1)[0].strip()
            return val or None
    return None


def _looks_like_record_line(line: str) -> bool:
    stripped = line.strip()
    stripped = re.sub(r"^[-*]\s*", "", stripped)
    return bool(re.match(r"\d{4}-\d{2}-\d{2}\b", stripped))


def _settings_region_lines(text: str) -> List[str]:
    lines: List[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if re.match(r"^##+\s*记录\b", stripped):
            break
        if not stripped or stripped.startswith(">") or stripped.startswith("#"):
            continue
        if _looks_like_record_line(stripped):
            continue
        lines.append(raw)
    return lines


SETTING_LINE_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*\*)?([^\n:：#]+?)(?:\*\*)?\s*[:：]\s*(.+?)\s*$"
)


def load_settings(work_root: str) -> Dict[str, str]:
    """Parse `<作品根>/_设置.md` into `{key: value}` without global defaults."""
    text = _read_text(os.path.join(work_root.rstrip("/"), "_设置.md"))
    out: Dict[str, str] = {}
    for line in _settings_region_lines(text):
        m = SETTING_LINE_RE.match(line)
        if not m:
            continue
        key = m.group(1).strip()
        val = re.split(r"\s+#", m.group(2), maxsplit=1)[0].strip()
        if key and key not in out:
            out[key] = val
    return out


def write_settings(work_root: str, fields: Dict[str, str], *, note: Optional[str] = None, bold_keys: bool = False):
    """Write `<作品根>/_设置.md` for per-work private choices."""
    lines = ["# 设置 — 本作私有选择点（skills/song/song-craft/references/选择点与偏好.md）", ""]
    if note:
        lines += [f"> {note}", ""]

    for k, v in fields.items():
        shown = v if v not in (None, "", []) else "（未定）"
        key_str = f"**{k}**" if bold_keys else k
        lines.append(f"- {key_str}：{shown}")

    lines += [
        "",
        "> 这些值由 init 按 CLI 参数/全局默认落定；同项目后续**沉默沿用**，"
        "改了在此更新。合规/不可逆/花钱多的点每次仍向用户确认。",
    ]

    path = os.path.join(work_root.rstrip("/"), "_设置.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    
    # Automatically log initialization
    append_record(work_root, "项目设置初始化（继承自 CLI/全局默认）")


def _setting_line_match(line: str, key: str, family: Optional[str] = None) -> Optional[re.Match[str]]:
    spec = get_setting_spec(key, family)
    keys = [key]
    if spec:
        keys = [spec.key, *spec.key_aliases]
    key_pattern = "|".join(re.escape(k) for k in keys)
    return re.match(rf"^(\s*(?:[-*]\s*)?(?:\*\*)?(?:{key_pattern})(?:\*\*)?\s*[:：]\s*)(.*?)(\s*)$", line)


def _record_index(lines: List[str]) -> Optional[int]:
    for i, line in enumerate(lines):
        if re.match(r"^##+\s*记录\b", line.strip()):
            return i
    return None


def _last_setting_line_index(lines: List[str]) -> Optional[int]:
    stop = _record_index(lines)
    scan = lines if stop is None else lines[:stop]
    last = None
    for i, line in enumerate(scan):
        if _looks_like_record_line(line) or line.strip().startswith(">"):
            continue
        if SETTING_LINE_RE.match(line):
            last = i
    return last


def append_record(work_root: str, message: str, *, date: Optional[str] = None) -> None:
    path = os.path.join(work_root.rstrip("/"), "_设置.md")
    content = _read_text(path)
    if not content:
        content = "# 设置 — 本作私有选择点（skills/song/song-craft/references/选择点与偏好.md）\n"
    lines = content.splitlines()
    entry = f"- {date or time.strftime('%Y-%m-%d')} {message}"
    idx = _record_index(lines)
    if idx is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(["## 记录", entry])
    else:
        lines.insert(idx + 1, entry)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")


def _format_validation_error(result: Dict[str, Any]) -> str:
    msg = f"{result.get('key')}: {result.get('message', 'invalid setting')}"
    expected = result.get("expected")
    if expected:
        msg += "；可选值：" + " / ".join(str(x) for x in expected)
    return msg


def validate_project_setting(work_root: str, key: str, value: str) -> Dict[str, Any]:
    """Validate one setting using the family inferred from the project root."""
    return validate_setting(key, value, family=detect_family(work_root))


def set_project_setting(
    work_root: str,
    key: str,
    value: str,
    *,
    record: bool = True,
    message: Optional[str] = None,
    validate: bool = True,
) -> Tuple[Optional[str], str]:
    """Patch one setting line in place, preserving notes and records."""
    work_root = work_root.rstrip("/")
    family = detect_family(work_root)
    if validate:
        check = validate_setting(key, value, family=family)
        if check["level"] in ("warn", "error"):
            raise ValueError(_format_validation_error(check))
    canonical = canonical_setting_key(key, family)
    path = os.path.join(work_root, "_设置.md")
    content = _read_text(path)
    if not content:
        content = "# 设置 — 本作私有选择点（skills/song/song-craft/references/选择点与偏好.md）\n\n"
    lines = content.splitlines()
    old_val: Optional[str] = None
    stop = _record_index(lines)
    scan_end = len(lines) if stop is None else stop
    updated = False
    for i in range(scan_end):
        if _looks_like_record_line(lines[i]):
            continue
        m = _setting_line_match(lines[i], key, family) or _setting_line_match(lines[i], canonical, family)
        if not m:
            continue
        old_val = re.split(r"\s+#", m.group(2), maxsplit=1)[0].strip()
        lines[i] = f"{m.group(1)}{value}{m.group(3)}"
        updated = True
        break

    if not updated:
        insert_after = _last_setting_line_index(lines)
        new_line = f"- {canonical}：{value}"
        if insert_after is None:
            insert_at = 2 if len(lines) >= 2 else len(lines)
            lines.insert(insert_at, new_line)
        else:
            lines.insert(insert_after + 1, new_line)

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    if record:
        append_record(work_root, message or f"设置 {canonical} = {value} (原值: {old_val})")
    return old_val, value


def reset_project_setting(work_root: str, key: str, *, record: bool = True) -> Optional[str]:
    work_root = work_root.rstrip("/")
    family = detect_family(work_root)
    canonical = canonical_setting_key(key, family)
    path = os.path.join(work_root, "_设置.md")
    content = _read_text(path)
    if not content:
        return None
    lines = content.splitlines()
    stop = _record_index(lines)
    scan_end = len(lines) if stop is None else stop
    old_val = None
    kept: List[str] = []
    removed = False
    for i, line in enumerate(lines):
        if i < scan_end:
            m = _setting_line_match(line, key, family) or _setting_line_match(line, canonical, family)
            if m:
                old_val = re.split(r"\s+#", m.group(2), maxsplit=1)[0].strip()
                removed = True
                continue
        kept.append(line)
    if not removed:
        return None
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(kept).rstrip() + "\n")
    if record:
        append_record(work_root, f"重置选项 {canonical} (原值: {old_val})")
    return old_val


def reset_all_project_settings(work_root: str, *, record: bool = True) -> List[str]:
    work_root = work_root.rstrip("/")
    settings = load_settings(work_root)
    path = os.path.join(work_root, "_设置.md")
    content = _read_text(path)
    lines = content.splitlines()
    stop = _record_index(lines)
    scan_end = len(lines) if stop is None else stop
    kept: List[str] = []
    for i, line in enumerate(lines):
        if i < scan_end and not _looks_like_record_line(line) and SETTING_LINE_RE.match(line):
            continue
        kept.append(line)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(kept).rstrip() + "\n")
    if record:
        append_record(work_root, f"重置所有选项 (原含: {', '.join(settings.keys())})")
    return list(settings.keys())


def _matches_allowed(value: str, allowed: Iterable[str], *, parameterized: bool) -> bool:
    raw = str(value or "").strip()
    raw_norm = _norm(raw)
    for item in allowed:
        item_norm = _norm(item)
        if raw_norm == item_norm:
            return True
        if parameterized and (raw.startswith(f"{item}(") or raw.startswith(f"{item}（") or raw_norm.startswith(item_norm + " ")):
            return True
    return False


def _validate_video_backend_list(value: str, spec: SettingSpec) -> bool:
    raw = str(value or "").strip()
    if _matches_allowed(raw, ("无", "关闭", "不使用"), parameterized=False):
        return True
    if _norm(raw) in spec.aliases:
        return True
    parts = [p.strip() for p in re.split(r"[,，、/\s]+", raw) if p.strip()]
    if not parts:
        return True
    for part in parts:
        if _norm(part) in spec.aliases:
            continue
        normalized = normalize_video_backend(part, default="")
        if not normalized:
            return False
    return True


def validate_setting(key: str, value: str, *, family: Optional[str] = None) -> Dict[str, Any]:
    family = family or "all"
    spec = get_setting_spec(key, family)
    if not spec:
        return {"level": "warn", "key": key, "value": value, "message": "unknown setting key"}
    value = normalize_setting_value(spec.key, value)
    if spec.metadata:
        return {"level": "info", "key": key, "canonical_key": spec.key, "value": value, "message": "project metadata"}
    if spec.key == "生视频AI":
        if _validate_video_backend_list(value, spec):
            return {"level": "ok", "key": key, "canonical_key": spec.key, "value": value, "message": "ok"}
        return {"level": "error", "key": key, "canonical_key": spec.key, "value": value, "message": "invalid video backend"}
    if spec.key == "视频备用后端":
        if _validate_video_backend_list(value, spec):
            return {"level": "ok", "key": key, "canonical_key": spec.key, "value": value, "message": "ok"}
        return {"level": "error", "key": key, "canonical_key": spec.key, "value": value, "message": "invalid fallback video backend"}
    if not spec.allowed:
        return {"level": "ok", "key": key, "canonical_key": spec.key, "value": value, "message": "ok"}
    values = [value]
    if spec.composite:
        values = []
        for part in re.split(r"[;；]", value):
            part = part.strip()
            if not part:
                continue
            values.append(part.split("=", 1)[1].strip() if "=" in part else part)
    invalid = [v for v in values if not _matches_allowed(v, spec.allowed, parameterized=spec.parameterized)]
    if invalid:
        return {
            "level": "error",
            "key": key,
            "canonical_key": spec.key,
            "value": value,
            "message": "invalid value: " + ", ".join(invalid),
            "expected": list(spec.allowed),
        }
    return {"level": "ok", "key": key, "canonical_key": spec.key, "value": value, "message": "ok"}


def audit_settings(work_root: str) -> Dict[str, Any]:
    family = detect_family(work_root)
    settings = load_settings(work_root)
    rows = [validate_setting(k, v, family=family) for k, v in settings.items()]
    return {
        "family": family,
        "settings": settings,
        "rows": rows,
        "errors": sum(1 for r in rows if r["level"] == "error"),
        "warnings": sum(1 for r in rows if r["level"] == "warn"),
        "infos": sum(1 for r in rows if r["level"] == "info"),
    }


def syncable_project_settings(work_root: str) -> Dict[str, str]:
    family = detect_family(work_root)
    out: Dict[str, str] = {}
    for key, value in load_settings(work_root).items():
        spec = get_setting_spec(key, family)
        if not spec or spec.metadata or not spec.syncable:
            continue
        out[spec.key] = value
    return out


def sync_global_settings(work_root: str, fields: Dict[str, str]) -> str:
    repo_root = repo_root_from(work_root)
    global_path = global_settings_path(repo_root)
    os.makedirs(os.path.dirname(global_path) or ".", exist_ok=True)
    content = _read_text(global_path)
    lines = content.splitlines()
    for key, value in fields.items():
        pattern = re.compile(rf"^(\s*[-*]\s*(?:\*\*)?{re.escape(key)}(?:\*\*)?\s*[:：]\s*)(.+)$")
        replaced = False
        for i, line in enumerate(lines):
            m = pattern.match(line)
            if m:
                lines[i] = f"{m.group(1)}{value}"
                replaced = True
                break
        if not replaced:
            if lines and lines[-1].strip():
                lines.append("")
            lines.append(f"- {key}: {value}")
    with open(global_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    return global_path


GLOBAL_SETTINGS_CANDIDATES = (
    "创作偏好-默认.md",
    os.path.join(".agents", "创作偏好-默认.md"),
    os.path.join(".codex", "创作偏好-默认.md"),
    os.path.join(".claude", "创作偏好-默认.md"),
)


def global_settings_paths(repo_root: str) -> List[str]:
    return [os.path.join(repo_root, rel) for rel in GLOBAL_SETTINGS_CANDIDATES]


def global_settings_path(repo_root: str) -> str:
    for path in global_settings_paths(repo_root):
        if os.path.exists(path):
            return path
    return global_settings_paths(repo_root)[0]


def normalize_setting_value(key: str, value: str) -> str:
    """Normalize historical setting aliases that should not leak into execution."""
    normalized = (value or "").strip()
    if key == "重抽预算策略" and normalized in {"预算不足", "预算不够"}:
        return "预算一般"
    return normalized


def get_setting(work_root: str, key: str, default: Optional[str] = None) -> str:
    """Read a setting from `<作品根>/_设置.md`, then global defaults, then fallback."""
    work_root = work_root.rstrip("/")
    project = _extract_setting(_read_text(os.path.join(work_root, "_设置.md")), key)
    if project:
        return normalize_setting_value(key, project)
    repo = repo_root_from(work_root)
    for path in global_settings_paths(repo):
        global_val = _extract_setting(_read_text(path), key)
        if global_val:
            return normalize_setting_value(key, global_val)
    if default is not None:
        return normalize_setting_value(key, default)
    return normalize_setting_value(key, DEFAULTS.get(key, ""))


def production_mode(work_root: str) -> str:
    mode = get_setting(work_root, "制作模式", DEFAULTS["制作模式"])
    return mode or DEFAULTS["制作模式"]


def is_video_first(work_root: str) -> bool:
    return "先出视频" in production_mode(work_root)


def is_native_av(work_root: str) -> bool:
    """`制作模式=原生音画`: speaking shots use native synchronized A/V."""
    mode = production_mode(work_root)
    return "原生音画" in mode or "native_av" in mode.lower()


def watermark_setting(work_root: str) -> str:
    return get_setting(work_root, "水印", DEFAULTS["水印"])
