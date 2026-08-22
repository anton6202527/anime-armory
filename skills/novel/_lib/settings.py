#!/usr/bin/env python3
"""Per-project settings helpers for the novel family.

The user-facing convention lives in `skills/novel/novel-craft/references/选择点与偏好.md`.
This module is the novel line's deterministic helper for `_设置.md`, audit,
patching, reset, and private global default sync.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from craft_profile import (
    CRAFT_PROFILE_KEY,
    CRAFT_PROFILE_VALUES,
    DEFAULT_CRAFT_PROFILE,
    normalize_craft_profile,
)


DEFAULTS = {
    "小说用途": "未定",
    "目标平台": "未定",
    CRAFT_PROFILE_KEY: DEFAULT_CRAFT_PROFILE,
    "权利来源": "未声明",
    "输出格式": "txt+docx",
    "篇幅档": "medium",
    "小说生成模式": "稳妥初稿",
    "小说生成工作流": "默认单步",
    "小批回扫间隔": "5章",
    "章节生成粒度": "逐章",
    # 普通、可逆的蓝图/设定/Demo 审阅交给独立 specialist reviewer；审批记录
    # 明示 delegated_autonomy，不伪装成人审。高风险边界仍停下。
    "审阅策略": "用户授权制作代理",
    "发行地区": "未定",
    "文本主创模式": "AI辅助",
    "AI使用披露": "AI-assisted",
    "力量体系自检": "开启",
}

GLOBAL_SETTINGS_CANDIDATES = (
    "创作偏好-默认.md",
    os.path.join(".agents", "创作偏好-默认.md"),
    os.path.join(".codex", "创作偏好-默认.md"),
    os.path.join(".claude", "创作偏好-默认.md"),
)

FAMILY_ROOTS = {
    "写小说": "novel",
}

FAMILY_MARKERS = {
    "novel": (("小说",), ("原作.txt",), ("创作蓝图.md",), ("设定",)),
}


@dataclass(frozen=True)
class SettingSpec:
    """Executable subset of the novel choice-point contract.

    The prose source of truth remains
    `skills/novel/novel-craft/references/选择点与偏好.md`. This compact schema is only
    for deterministic patching, audit, and private global-default sync.
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


SETTING_SPECS: Tuple[SettingSpec, ...] = (
    SettingSpec(
        "小说用途",
        ("novel",),
        ("传统小说", "漫剧源书", "微短剧源书", "短读/短篇", "出海译制底稿", "自定义"),
        key_aliases=("目标用途",),
        parameterized=True,
        sensitive=True,
    ),
    SettingSpec(
        "目标平台",
        ("novel",),
        ("起点", "番茄", "晋江", "抖音漫剧", "红果", "历史向", "跨平台", "未定", "自定义"),
        parameterized=True,
        sensitive=True,
    ),
    SettingSpec(CRAFT_PROFILE_KEY, ("novel",), CRAFT_PROFILE_VALUES),
    SettingSpec("权利来源", ("novel",), ("未声明", "原创", "公版", "自有", "授权"), sensitive=True),
    SettingSpec("权利辖区", ("novel",), ("US", "CN", "GLOBAL", "user-declared", "自定义"), parameterized=True, sensitive=True),
    SettingSpec("发行地区", ("novel",), ("CN", "US", "GLOBAL", "未定", "自定义"), parameterized=True, sensitive=True),
    SettingSpec("输出格式", ("novel",), ("txt", "docx", "outline", "txt+docx"), composite=True, parameterized=True),
    SettingSpec("篇幅档", ("novel",), ("short", "medium", "long", "微短剧", "漫剧"), parameterized=True),
    SettingSpec("小说生成模式", ("novel",), ("极速初稿", "稳妥初稿", "商业连载")),
    SettingSpec("小说生成工作流", ("novel",), ("默认单步", "三步迭代", "边写边自检")),
    SettingSpec("小批回扫间隔", ("novel",), ("3章", "5章", "关闭", "自定义"), parameterized=True),
    SettingSpec("章节生成粒度", ("novel",), ("逐章", "小批", "全书草稿"), parameterized=True),
    SettingSpec(
        "审阅策略",
        ("novel",),
        ("用户授权制作代理", "逐阶段用户确认", "自定义"),
        parameterized=True,
        sensitive=True,
    ),
    SettingSpec("文本主创模式", ("novel",), ("人类主创", "AI辅助", "AI生成"), sensitive=True),
    SettingSpec("AI使用披露", ("novel",), ("AI-generated", "AI-assisted", "未使用AI文本"), sensitive=True),
    SettingSpec("目标语言", ("novel",), ("en", "id", "th", "es", "pt", "ja", "自定义"), composite=True, parameterized=True),
    SettingSpec("翻译后端", ("novel",), ("LLM代理", "专业MT", "人工", "混合"), parameterized=True),
    SettingSpec("出海目标平台", ("novel",), ("YouTube", "TikTok", "海外阅读平台", "通用", "自定义"), parameterized=True, sensitive=True),
    SettingSpec("力量体系自检", ("novel",), ("开启", "关闭")),
)

SETTING_LINE_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*\*)?([^\n:：#]+?)(?:\*\*)?\s*[:：]\s*(.+?)\s*$"
)


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


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def _read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _looks_like_record_line(line: str) -> bool:
    stripped = re.sub(r"^[-*]\s*", "", line.strip())
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


def _extract_setting(text: str, key: str) -> Optional[str]:
    key_pattern = rf"(?:\*\*)?{re.escape(key)}(?:\*\*)?"
    pat = re.compile(rf"^\s*(?:[-*]\s*)?{key_pattern}\s*[:：]\s*(.+?)\s*$", re.M)
    for line in _settings_region_lines(text):
        match = pat.match(line)
        if match:
            value = re.split(r"\s+#", match.group(1), maxsplit=1)[0].strip()
            return value or None
    return None


def load_settings(work_root: str) -> Dict[str, str]:
    """Parse `<作品根>/_设置.md` into `{key: value}` without defaults."""
    text = _read_text(os.path.join(work_root.rstrip("/"), "_设置.md"))
    out: Dict[str, str] = {}
    for line in _settings_region_lines(text):
        match = SETTING_LINE_RE.match(line)
        if not match:
            continue
        key = match.group(1).strip()
        value = re.split(r"\s+#", match.group(2), maxsplit=1)[0].strip()
        if key and key not in out:
            out[key] = normalize_setting_value(key, value)
    return out


def append_record(work_root: str, message: str, *, date: Optional[str] = None) -> None:
    """Append a human-readable change record to `<作品根>/_设置.md`."""
    path = os.path.join(work_root.rstrip("/"), "_设置.md")
    content = _read_text(path)
    if not content:
        content = "# 设置 — 本作私有选择点（skills/novel/novel-craft/references/选择点与偏好.md）\n"
    lines = content.splitlines()
    entry = f"- {date or time.strftime('%Y-%m-%d')} {message}"
    for idx, line in enumerate(lines):
        if re.match(r"^##+\s*记录\b", line.strip()):
            lines.insert(idx + 1, entry)
            break
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(["## 记录", entry])
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")


def write_settings(
    work_root: str,
    fields: Dict[str, str],
    *,
    note: Optional[str] = None,
    bold_keys: bool = False,
) -> None:
    """Rewrite `<作品根>/_设置.md` for per-work private choices."""
    # New projects record the craft contract explicitly.  Private global
    # defaults win; projects created before this choice point remain compatible
    # because every runtime resolver falls back to `genre_novel`.
    fields = dict(fields)
    fields.setdefault(
        CRAFT_PROFILE_KEY,
        get_setting(work_root, CRAFT_PROFILE_KEY, DEFAULT_CRAFT_PROFILE),
    )
    fields.setdefault(
        "审阅策略",
        get_setting(work_root, "审阅策略", DEFAULTS["审阅策略"]),
    )
    lines = ["# 设置 — 本作私有选择点（skills/novel/novel-craft/references/选择点与偏好.md）", ""]
    if note:
        lines += [f"> {note}", ""]

    for key, value in fields.items():
        shown = value if value not in (None, "", []) else "（未定）"
        key_text = f"**{key}**" if bold_keys else key
        lines.append(f"- {key_text}：{shown}")

    lines += [
        "",
        "> 这些值由 init 按 CLI 参数/全局默认落定；同项目后续**沉默沿用**，"
        "改了在此更新。合规/不可逆/花钱多的点每次仍向用户确认。",
    ]

    os.makedirs(work_root.rstrip("/"), exist_ok=True)
    path = os.path.join(work_root.rstrip("/"), "_设置.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
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


def _format_validation_error(result: Dict[str, Any]) -> str:
    msg = f"{result.get('key')}: {result.get('message', 'invalid setting')}"
    expected = result.get("expected")
    if expected:
        msg += "；可选值：" + " / ".join(str(x) for x in expected)
    return msg


def _matches_allowed(value: str, allowed: Iterable[str], *, parameterized: bool) -> bool:
    raw = str(value or "").strip()
    raw_norm = _norm(raw)
    for item in allowed:
        item_norm = _norm(item)
        if raw_norm == item_norm:
            return True
        if parameterized and (
            raw.startswith(f"{item}(")
            or raw.startswith(f"{item}（")
            or raw_norm.startswith(item_norm + " ")
        ):
            return True
    return False


def validate_setting(key: str, value: str, *, family: Optional[str] = None) -> Dict[str, Any]:
    family = family or "all"
    spec = get_setting_spec(key, family)
    if not spec:
        return {"level": "warn", "key": key, "value": value, "message": "unknown setting key"}
    value = normalize_setting_value(spec.key, value)
    if spec.metadata:
        return {"level": "info", "key": key, "canonical_key": spec.key, "value": value, "message": "project metadata"}
    if not spec.allowed:
        return {"level": "ok", "key": key, "canonical_key": spec.key, "value": value, "message": "ok"}
    values = [value]
    if spec.composite:
        values = []
        for part in re.split(r"[;；,+、/]+", value):
            part = part.strip()
            if part:
                values.append(part)
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


def validate_project_setting(work_root: str, key: str, value: str) -> Dict[str, Any]:
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
    normalized_value = normalize_setting_value(canonical, value)
    path = os.path.join(work_root, "_设置.md")
    content = _read_text(path)
    if not content:
        content = "# 设置 — 本作私有选择点（skills/novel/novel-craft/references/选择点与偏好.md）\n\n"
    lines = content.splitlines()
    old_val: Optional[str] = None
    stop = _record_index(lines)
    scan_end = len(lines) if stop is None else stop
    updated = False
    for i in range(scan_end):
        if _looks_like_record_line(lines[i]):
            continue
        match = _setting_line_match(lines[i], key, family) or _setting_line_match(lines[i], canonical, family)
        if not match:
            continue
        old_val = re.split(r"\s+#", match.group(2), maxsplit=1)[0].strip()
        lines[i] = f"{match.group(1)}{normalized_value}{match.group(3)}"
        updated = True
        break

    if not updated:
        insert_after = _last_setting_line_index(lines)
        new_line = f"- {canonical}：{normalized_value}"
        if insert_after is None:
            insert_at = 2 if len(lines) >= 2 else len(lines)
            lines.insert(insert_at, new_line)
        else:
            lines.insert(insert_after + 1, new_line)

    os.makedirs(work_root, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    if record:
        append_record(work_root, message or f"设置 {canonical} = {normalized_value} (原值: {old_val})")
    return old_val, normalized_value


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
            match = _setting_line_match(line, key, family) or _setting_line_match(line, canonical, family)
            if match:
                old_val = re.split(r"\s+#", match.group(2), maxsplit=1)[0].strip()
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


def audit_settings(work_root: str) -> Dict[str, Any]:
    family = detect_family(work_root)
    settings = load_settings(work_root)
    rows = [validate_setting(key, value, family=family) for key, value in settings.items()]
    return {
        "family": family,
        "settings": settings,
        "rows": rows,
        "errors": sum(1 for row in rows if row["level"] == "error"),
        "warnings": sum(1 for row in rows if row["level"] == "warn"),
        "infos": sum(1 for row in rows if row["level"] == "info"),
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
        canonical = canonical_setting_key(key, detect_family(work_root))
        pattern = re.compile(rf"^(\s*[-*]\s*(?:\*\*)?{re.escape(canonical)}(?:\*\*)?\s*[:：]\s*)(.+)$")
        replaced = False
        for i, line in enumerate(lines):
            match = pattern.match(line)
            if match:
                lines[i] = f"{match.group(1)}{value}"
                replaced = True
                break
        if not replaced:
            if lines and lines[-1].strip():
                lines.append("")
            lines.append(f"- {canonical}: {value}")
    with open(global_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    return global_path


def global_settings_paths(repo_root: str) -> List[str]:
    return [os.path.join(repo_root, rel) for rel in GLOBAL_SETTINGS_CANDIDATES]


def global_settings_path(repo_root: str) -> str:
    for path in global_settings_paths(repo_root):
        if os.path.exists(path):
            return path
    return global_settings_paths(repo_root)[0]


def normalize_setting_value(key: str, value: str) -> str:
    """Normalize historical aliases that should not leak into novel execution."""
    normalized = (value or "").strip()
    if key == CRAFT_PROFILE_KEY:
        return normalize_craft_profile(normalized)
    if key == "小说用途":
        aliases = {
            "红果": "漫剧源书",
            "红果短剧": "漫剧源书",
            "红果漫剧": "漫剧源书",
            "红果漫剧源书": "漫剧源书",
            "抖音": "漫剧源书",
            "抖音短剧": "漫剧源书",
            "抖音漫剧": "漫剧源书",
            "抖音漫剧源书": "漫剧源书",
            "短剧": "微短剧源书",
            "微短剧": "微短剧源书",
            "漫剧": "漫剧源书",
            "传统": "传统小说",
            "传统网文": "传统小说",
            "传统连载": "传统小说",
            "网文": "传统小说",
            "长篇": "传统小说",
            "短篇": "短读/短篇",
            "短读": "短读/短篇",
        }
        return aliases.get(normalized, normalized)
    if key == "篇幅档" and normalized in {"抖音漫剧", "红果短剧"}:
        return "漫剧"
    if key == "小说生成工作流" and normalized in {"三段式", "Trio", "trio"}:
        return "三步迭代"
    if key == "小说生成工作流" and normalized in {
        "边写边检",
        "边写边审",
        "写后自检",
        "实时自检",
        "write-check",
        "write_check",
        "live-check",
        "live_check",
    }:
        return "边写边自检"
    if key == "小批回扫间隔" and normalized in {"off", "none", "0", "0章", "不回扫"}:
        return "关闭"
    if key == "小批回扫间隔" and normalized.isdigit():
        return f"{normalized}章"
    return normalized


def get_setting(work_root: str, key: str, default: Optional[str] = None) -> str:
    """Read project setting, then private global defaults, then fallback."""
    work_root = work_root.rstrip("/")
    project = _extract_setting(_read_text(os.path.join(work_root, "_设置.md")), key)
    if project:
        return normalize_setting_value(key, project)
    repo = repo_root_from(work_root)
    for path in global_settings_paths(repo):
        global_value = _extract_setting(_read_text(path), key)
        if global_value:
            return normalize_setting_value(key, global_value)
    if default is not None:
        return normalize_setting_value(key, default)
    return normalize_setting_value(key, DEFAULTS.get(key, ""))
