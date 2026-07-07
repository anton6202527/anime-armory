#!/usr/bin/env python3
"""Per-project settings helpers for the comic family.

The user-facing convention lives in `skills/comic/references/选择点与偏好.md`.
This module only implements deterministic helpers for `_设置.md`; it does not
ask questions or infer preferences.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple


DEFAULTS = {
    "输入模式": "原创漫画",
    "漫画形态": "条漫",
    "阅读方向": "从上到下",
    "目标平台": "通用",
    "页面尺寸": "1440xauto",
    "单话分段高度": "0",
    "基础视觉风格": "彩色国漫条漫",
    "生图模型": "GPT Image 2",
    "生图渠道": "Codex CLI",
    "生图AI": "Codex",
    "参考一致性策略": "共享参考图",
    "定妆级别": "长线专门定妆",
    "文字语言": "中文",
    "嵌字方式": "后期嵌字",
    "导出格式": "webp+png",
    "发行地区": "未指定",
    "合规用途": "demo学习",
}

VISUAL_STYLE_PRESETS = (
    "彩色国漫条漫",
    "黑白页漫",
    "日漫赛璐璐",
    "韩漫清透",
    "美漫硬线",
    "水墨国风",
    "Q版轻喜",
    "写实电影感",
    "国风厚涂条漫",
    "新国风水墨彩漫",
    "黑白日漫页漫",
    "日漫网点热血",
    "少女漫画清透",
    "青年漫画写实",
    "韩漫清透条漫",
    "韩漫恋爱柔光",
    "韩漫奇幻厚涂",
    "美漫硬线超级英雄",
    "美漫复古半调",
    "美漫暗黑写实",
    "欧漫清线",
    "欧漫绘本水彩",
    "法式写实冒险",
    "水彩治愈",
    "扁平矢量漫画",
    "儿童绘本漫画",
    "Q版四格轻喜",
    "黑色电影高反差",
    "赛博朋克霓虹",
    "蒸汽朋克复古",
    "暗黑怪谈厚涂",
    "像素漫画",
    "铅笔草稿分镜",
    "灰稿分镜",
    "自定义",
)

FAMILY_ROOTS = {
    "画漫画": "comic",
}

FAMILY_MARKERS = {
    "comic": (
        ("脚本", "第1话", "panel_script.json"),
        ("排版", "第1话", "layout.json"),
        ("设定库", "story_bible.md"),
    ),
}

GLOBAL_SETTINGS_CANDIDATES = (
    "创作偏好-默认.md",
    os.path.join(".agents", "创作偏好-默认.md"),
    os.path.join(".codex", "创作偏好-默认.md"),
    os.path.join(".claude", "创作偏好-默认.md"),
)


@dataclass(frozen=True)
class SettingSpec:
    """Executable subset of the comic choice-point contract."""

    key: str
    families: Tuple[str, ...] = ("all",)
    allowed: Tuple[str, ...] = ()
    aliases: Dict[str, str] = field(default_factory=dict)
    key_aliases: Tuple[str, ...] = ()
    parameterized: bool = False
    composite: bool = False
    freeform: bool = False
    syncable: bool = True
    metadata: bool = False
    sensitive: bool = False


SETTING_SPECS: Tuple[SettingSpec, ...] = (
    SettingSpec("输入模式", ("comic",), ("原创漫画", "源本改漫画", "脚本改漫画"), sensitive=True),
    SettingSpec("漫画形态", ("comic",), ("条漫", "页漫", "四格", "分镜稿")),
    SettingSpec("阅读方向", ("comic",), ("从上到下", "从左到右", "从右到左")),
    SettingSpec(
        "目标平台",
        ("comic",),
        ("通用", "快看", "腾讯动漫", "B站漫画", "小红书", "WEBTOON", "Tapas", "自定义"),
        parameterized=True,
        sensitive=True,
    ),
    SettingSpec("页面尺寸", ("comic",), ("1440xauto", "1080xauto", "A4", "B5", "自定义"), parameterized=True),
    SettingSpec("单话分段高度", ("comic",), parameterized=True),
    SettingSpec(
        "基础视觉风格",
        ("comic",),
        VISUAL_STYLE_PRESETS,
        parameterized=True,
        freeform=True,
    ),
    SettingSpec("风格锚", ("comic",), parameterized=True, freeform=True),
    SettingSpec(
        "生图模型",
        ("comic",),
        ("GPT Image 2", "Seedream 5.0", "Seedream 4.5", "Nano Banana Pro", "Gemini 3 Pro Image", "Flux 2 Pro", "自定义"),
        key_aliases=("image_model",),
        parameterized=True,
    ),
    SettingSpec(
        "生图渠道",
        ("comic",),
        ("Codex CLI", "OpenAI API", "Dreamina/即梦官方 CLI", "Seedream", "可灵主体库", "Nano Banana", "manual", "自定义"),
        key_aliases=("生图入口", "image_channel"),
        parameterized=True,
    ),
    SettingSpec(
        "生图AI",
        ("comic",),
        ("Codex", "OpenAI", "Dreamina", "即梦", "Seedream", "可灵主体库", "Nano Banana", "manual", "自定义"),
        key_aliases=("生图后端",),
        parameterized=True,
    ),
    SettingSpec("参考一致性策略", ("comic",), ("共享参考图", "主体库", "LoRA", "手工校对"), parameterized=True),
    SettingSpec(
        "定妆级别",
        ("comic",),
        ("长线专门定妆", "短 demo 锚点", "锚点过渡", "手工校对"),
        key_aliases=("角色定妆级别", "角色定妆策略"),
        parameterized=True,
    ),
    SettingSpec("年龄形态继承", ("comic",), ("开启", "关闭"), key_aliases=("形态继承", "年龄继承")),
    SettingSpec("角色一致性硬闸", ("comic",), ("开启", "关闭"), key_aliases=("一致性硬闸", "角色硬闸")),
    SettingSpec(
        "文字语言",
        ("comic",),
        ("中文", "英文", "中上英下", "英上中下", "自定义语言"),
        key_aliases=("嵌字语言", "漫画文字语言", "prompt文字语言"),
        parameterized=True,
    ),
    SettingSpec("嵌字方式", ("comic",), ("后期嵌字", "手工嵌字", "图像内文字"), sensitive=True),
    SettingSpec("导出格式", ("comic",), ("webp+png", "png", "webp", "jpg", "pdf", "自定义"), parameterized=True),
    SettingSpec("发行地区", ("comic",), ("未指定", "中国大陆", "港澳台", "北美", "全球", "自定义"), parameterized=True, sensitive=True),
    SettingSpec("合规用途", ("comic",), ("demo学习", "自用草稿", "发布候选", "商用", "授权交付", "自定义"), parameterized=True, sensitive=True),
)

SETTING_LINE_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*\*)?([^\n:：#]+?)(?:\*\*)?\s*[:：]\s*(.+?)\s*$"
)


def repo_root_from(path: str) -> str:
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
    pattern = re.compile(rf"^\s*(?:[-*]\s*)?{key_pattern}\s*[:：]\s*(.+?)\s*$", re.M)
    for line in _settings_region_lines(text):
        match = pattern.match(line)
        if match:
            value = re.split(r"\s+#", match.group(1), maxsplit=1)[0].strip()
            return value or None
    return None


def load_settings(work_root: str) -> Dict[str, str]:
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


def write_settings(
    work_root: str,
    fields: Dict[str, str],
    *,
    note: Optional[str] = None,
    bold_keys: bool = False,
) -> None:
    lines = ["# 设置 — 本作私有选择点（skills/comic/references/选择点与偏好.md）", ""]
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
        content = "# 设置 — 本作私有选择点（skills/comic/references/选择点与偏好.md）\n"
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


def _setting_line_match(line: str, key: str, family: Optional[str] = None) -> Optional[re.Match[str]]:
    spec = get_setting_spec(key, family)
    keys = [key]
    if spec:
        keys = [spec.key, *spec.key_aliases]
    key_pattern = "|".join(re.escape(k) for k in keys)
    return re.match(rf"^(\s*(?:[-*]\s*)?(?:\*\*)?(?:{key_pattern})(?:\*\*)?\s*[:：]\s*)(.*?)(\s*)$", line)


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
        values = [part.strip() for part in re.split(r"[;；,+、/]+", value) if part.strip()]
    invalid = [v for v in values if not _matches_allowed(v, spec.allowed, parameterized=spec.parameterized)]
    if invalid:
        if spec.freeform and value.strip():
            return {
                "level": "ok",
                "key": key,
                "canonical_key": spec.key,
                "value": value,
                "message": "custom value",
            }
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
        content = "# 设置 — 本作私有选择点（skills/comic/references/选择点与偏好.md）\n\n"
    lines = content.splitlines()
    old_value: Optional[str] = None
    stop = _record_index(lines)
    scan_end = len(lines) if stop is None else stop
    updated = False
    for i in range(scan_end):
        if _looks_like_record_line(lines[i]):
            continue
        match = _setting_line_match(lines[i], key, family) or _setting_line_match(lines[i], canonical, family)
        if not match:
            continue
        old_value = re.split(r"\s+#", match.group(2), maxsplit=1)[0].strip()
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
        append_record(work_root, message or f"设置 {canonical} = {normalized_value} (原值: {old_value})")
    return old_value, normalized_value


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
    old_value = None
    kept: List[str] = []
    removed = False
    for i, line in enumerate(lines):
        if i < scan_end:
            match = _setting_line_match(line, key, family) or _setting_line_match(line, canonical, family)
            if match:
                old_value = re.split(r"\s+#", match.group(2), maxsplit=1)[0].strip()
                removed = True
                continue
        kept.append(line)
    if not removed:
        return None
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(kept).rstrip() + "\n")
    if record:
        append_record(work_root, f"重置选项 {canonical} (原值: {old_value})")
    return old_value


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
        normalized_value = normalize_setting_value(canonical, value)
        pattern = re.compile(rf"^(\s*[-*]\s*(?:\*\*)?{re.escape(canonical)}(?:\*\*)?\s*[:：]\s*)(.+)$")
        replaced = False
        kept: List[str] = []
        for line in lines:
            match = pattern.match(line)
            if match:
                if not replaced:
                    kept.append(f"{match.group(1)}{normalized_value}")
                    replaced = True
                continue
            kept.append(line)
        lines = kept
        if not replaced:
            if lines and lines[-1].strip():
                lines.append("")
            lines.append(f"- {canonical}: {normalized_value}")
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
    normalized = (value or "").strip()
    if key == "生图模型" and normalized == "OpenAI image_generation（Codex 内置）":
        return "GPT Image 2"
    if key == "单话分段高度" and normalized.isdigit():
        return normalized
    if key == "文字语言":
        lowered = _norm(normalized)
        aliases = {
            "zh": "中文",
            "chinese": "中文",
            "cn": "中文",
            "中文": "中文",
            "en": "英文",
            "english": "英文",
            "英文": "英文",
            "zh_en": "中上英下",
            "zh-en": "中上英下",
            "中英": "中上英下",
            "中上英下": "中上英下",
            "中文上英文下": "中上英下",
            "en_zh": "英上中下",
            "en-zh": "英上中下",
            "英中": "英上中下",
            "英上中下": "英上中下",
            "英文上中文下": "英上中下",
        }
        if lowered in aliases:
            return aliases[lowered]
    if key == "合规用途":
        lowered = _norm(normalized)
        aliases = {
            "demo": "demo学习",
            "demo学习": "demo学习",
            "学习demo": "demo学习",
            "做demo学习使用": "demo学习",
            "学习使用": "demo学习",
            "内部demo": "demo学习",
            "internal_only": "demo学习",
            "internal only": "demo学习",
            "draft": "demo学习",
            "preview": "demo学习",
            "test": "demo学习",
            "自用": "自用草稿",
            "自用草稿": "自用草稿",
        }
        if lowered in aliases:
            return aliases[lowered]
    return normalized


def get_setting(work_root: str, key: str, default: Optional[str] = None) -> str:
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
