#!/usr/bin/env python3
"""Shared per-project settings helpers.

The user-facing convention lives in `skills/n2d/references/选择点与偏好.md`. This module only
implements deterministic read/write helpers for `_设置.md`; it does not ask
questions or infer preferences.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import contextlib
import glob
import os
import re
import threading
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None

try:  # Optional here; most n2d scripts have common/ on sys.path already.
    from n2d_platform_profiles import VIDEO_BACKEND_ALIASES, normalize_video_backend
except Exception:  # pragma: no cover - keep generic settings usable outside n2d.
    VIDEO_BACKEND_ALIASES = {}

    def normalize_video_backend(value: Optional[str], default: str = "dreamina") -> str:
        return (value or default or "").strip().lower()

try:  # `制作模式` 取值的单一真值在 n2d_contract.PRODUCTION_MODES；此处只引用，不另写三元组。
    from n2d_contract import PRODUCTION_MODE_DEFAULT as _PRODUCTION_MODE_DEFAULT
    from n2d_contract import production_mode_keys as _production_mode_keys
    _PRODUCTION_MODE_KEYS = _production_mode_keys()
except Exception:  # pragma: no cover - keep generic settings usable outside n2d.
    _PRODUCTION_MODE_DEFAULT = "混合自动路由"  # 真值在 n2d_const.PRODUCTION_MODE_DEFAULT；此处仅为导入失败时的兜底
    _PRODUCTION_MODE_KEYS = ("混合自动路由", "配音先行", "原生音画", "先出视频后配音")


DEFAULTS = {
    "制作模式": _PRODUCTION_MODE_DEFAULT,
    "基础视觉风格": "冷灰写实3D国风漫剧",
    "拆集节奏": "前长后短",
    # 生成轴=具体模型（设计宪法 C5：指代必须落到模型，不写 agent/渠道）。`生图AI` 退化为访问入口/渠道。
    "生图模型": "GPT Image 2",
    "生图AI": "Codex",
    "生视频模型": "Seedance 2.0",
    "生视频渠道": "即梦/Dreamina",
    # Legacy combined key. New projects should write `生视频模型` + `生视频渠道`.
    "生视频AI": "即梦",
    "视频模型路由": "自动按镜头路由",
    "视频备用后端": "",
    "中段锚帧默认": "关闭",
    "重抽预算策略": "预算充足",
    "出视频规格": "预算充足",
    "视频分辨率": "720p",
    "视频生成音频策略": "无声视频流",
    "后端Smoke硬闸": "否",
    "合成阶段": "跳过",
    "视频原生音轨": "丢弃",
    "对口型": "关闭",
    "后期拟音策略": "自动",
    "字幕字号": "小",
    "AI显式角标": "仅元数据",
    "字幕语言": "中文",
    "变现模式": "免费",
    "合规用途": "internal_only",
}


FAMILY_ROOTS = {
    "制漫剧": "n2d",
}

N2D_PROJECT_MARKERS = (
    "小说",
    "脚本",
    "分镜",
    "设定库",
    "出图",
    "出视频",
    "配音",
    "合成",
    "生产数据",
)


@dataclass(frozen=True)
class SettingSpec:
    """Machine-readable preference contract for settings management.

    The prose source of truth remains `skills/n2d/references/选择点与偏好.md`; this compact schema
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

BASE_VISUAL_STYLE_CHOICES = (
    "冷灰写实3D国风漫剧",
    "真实3D人物质感 + 电影叙事镜头感",
    "写实电影感",
    "国漫写实角色审美 + 电影级布光与镜头语言",
    "国漫写实",
    "二次元赛璐璐",
    "二次元",
    "水墨国风",
    "厚涂幻想",
    "赛博霓虹",
    "Q版轻喜",
    "韩漫精致清透",
    "日漫剧场版光影",
    "3D卡通电影感",
    "动态漫画条漫风",
    "暗黑悬疑写实",
    "古风乙女清雅",
    "热血少年战斗番",
    "美漫硬线阴影",
    "低多边形玩具感",
    "纸片剪影 / 定格动画",
    "纸片剪影",
    "定格动画",
    "CG质感",
    "国风写意",
    "自定义",
)


SETTING_SPECS: Tuple[SettingSpec, ...] = (
    SettingSpec("制作模式", ("n2d",), _PRODUCTION_MODE_KEYS, sensitive=True),
    # 题材：弱选择点——split/分镜阶段 motif_detector 自动检测预填建议值，用户可覆盖。驱动母题增强
    # （系统面板等复现桥段的镜头/台词/出图/overlay）。取值与 n2d_const.GENRE_KEYWORDS 的题材键对齐。
    SettingSpec("题材", ("n2d",), ("系统流", "穿越", "修仙", "都市", "宫斗", "赘婿", "战神", "自定义"), parameterized=True),
    # 母题增强：是否对检测到的复现母题桥段套用增强模板（默认建议待确认，注入下游前人确认）。
    SettingSpec("母题增强", ("n2d",), ("开启", "关闭", "仅建议")),
    SettingSpec("基础视觉风格", ("n2d",), BASE_VISUAL_STYLE_CHOICES, parameterized=True),
    SettingSpec("拆集节奏", ("n2d",), ("前长后短", "均衡", "快节奏", "长集", "自定义"),
                key_aliases=("单集时长", "单集节奏偏好"), parameterized=True, syncable=False),
    # 变现模式：拆集结构的商业轴（软默认/高级覆盖，不列首跑必问）。免费(红果/番茄·完播率导向·
    # 全剧延续性·断点平均强)/付费(小程序剧·前十集卡点峰值+付费墙集)/海外(ReelShort/TikTok·更碎更狠)。
    # 驱动 boundary_audit 的剧级追更骨架与卡点定位。取值与 n2d-script/references/追更骨架.md 对齐。
    SettingSpec("变现模式", ("n2d",), ("免费", "付费", "海外"), parameterized=True, syncable=False),
    SettingSpec("项目规模", ("n2d",), ("短 demo", "单集", "多集长线", "长篇量产", "自定义"), parameterized=True, syncable=False),
    SettingSpec("首切范围", ("n2d",), ("部分先切", "全篇粗切"), parameterized=True),
    SettingSpec("脚本批次", ("n2d",), ("逐集", "小批", "整批"), parameterized=True),
    SettingSpec("中段锚帧默认", ("n2d",), ("关闭", "开启")),
    # C5 生成轴=具体模型（默认 GPT Image 2）。`生图AI` 保留为访问入口/渠道（壳）。
    SettingSpec("生图模型", ("n2d",), ("GPT Image 2", "Seedream 5.0", "Seedream 4.5", "Nano Banana Pro", "Gemini 3 Pro Image", "Flux 2 Pro", "可灵主体库模型", "自定义"), key_aliases=("生图model", "image_model"), parameterized=True),
    SettingSpec("生图AI", ("n2d",), ("Codex", "OpenAI", "Seedream", "可灵主体库", "Nano Banana", "Sora Cameo", "自定义官方后端", "自定义"), key_aliases=("生图渠道", "生图入口"), parameterized=True),
    SettingSpec("生视频模型", ("n2d",), VIDEO_MODEL_CHOICES, key_aliases=("视频模型", "目标视频模型"), parameterized=True),
    SettingSpec("生视频渠道", ("n2d",), VIDEO_CHANNEL_CHOICES, key_aliases=("视频渠道", "目标视频渠道"), parameterized=True),
    # Legacy combined key kept for existing projects and old CLI flags.
    SettingSpec("生视频AI", ("n2d",), ("即梦", "dreamina", "可灵", "kling", "Seedance", "Veo", "Sora", "Runway", "manual"), aliases=VIDEO_BACKEND_SETTING_ALIASES, parameterized=True),
    SettingSpec("视频模型路由", ("n2d",), ("自动按镜头路由", "固定生视频模型", "固定生视频AI")),
    SettingSpec("投放时效", ("n2d",), ("实时", "隔夜批量"), key_aliases=("时效档", "urgency")),
    SettingSpec("视频备用后端", ("n2d",), ("无", "即梦", "dreamina", "可灵", "kling", "Seedance", "Veo", "Sora", "Runway", "manual"), aliases=VIDEO_BACKEND_SETTING_ALIASES, parameterized=True),
    SettingSpec("出视频规格", ("n2d",), ("预算充足", "预算一般", "预算不够")),
    # 跨后端英雄镜多版（costly·默认关闭·花钱前确认）：开启后英雄镜（名场面/开场钩/高潮）同时跑
    # primary+secondary 两个后端各出一版、pooled 进候选 video_qc 选优。
    SettingSpec("英雄镜多版", ("n2d",), ("关闭", "开启")),
    SettingSpec("视频分辨率", ("n2d",), ("720p", "1080p", "4K")),
    SettingSpec("画幅", ("n2d",), ("9:16", "16:9"), key_aliases=("漫剧画幅",)),
    SettingSpec("对口型", ("n2d",), ("对话近景", "关闭", "配音对齐", "后期pass", "平台原生")),
    SettingSpec("视频生成音频策略", ("n2d",), ("无声视频流", "配音对齐口型", "低风险环境声", "低风险环境声/音效", "原生音画", "自定义"), parameterized=True),
    SettingSpec("后端Smoke硬闸", ("n2d",), ("否", "是"),
                aliases={"开启": "是", "强制": "是", "硬闸": "是", "关闭": "否", "不强制": "否"},
                key_aliases=("backend_smoke_required", "后端 smoke 硬闸")),
    SettingSpec("合成阶段", ("n2d",), ("跳过", "启用"),
                aliases={"不选": "跳过", "默认不选": "跳过", "关闭": "跳过", "关闭合成": "跳过",
                         "开启": "启用", "需要": "启用", "合成": "启用", "合成成片": "启用"},
                key_aliases=("成片合成", "后期合成", "compose阶段", "compose_stage")),
    SettingSpec("合成缓存保留", ("n2d",), ("手动清理", "成片后清理", "保留7天"),
                key_aliases=("缓存保留", "compose_cache_retention"), syncable=False),
    SettingSpec("配音后端", ("n2d",), ("CosyVoice", "GPT-SoVITS", "MiniMax", "火山", "say冒烟", "自定义"),
                aliases={"say占位": "say冒烟", "macOS say": "say冒烟"}, parameterized=True),
    SettingSpec("字幕语言", ("n2d",), ("中文", "中英双语", "仅英文", "无字幕")),
    SettingSpec("字幕字号", ("n2d",), ("小", "中", "大", "自定义"), parameterized=True),
    SettingSpec("AI显式角标", ("n2d",), ("开启", "仅元数据", "关闭")),
    SettingSpec("视频原生音轨", ("n2d",), ("丢弃", "低音量混入环境声", "保留原片音轨")),
    SettingSpec("后期拟音策略", ("n2d",), ("自动", "强制叠加", "关闭")),
    SettingSpec("生成粒度", ("n2d",), ("逐个", "小批", "按场景分批", "整集", "自定义"), parameterized=True, composite=True),
    SettingSpec("图片验收模式", ("n2d",), ("逐张机器QC+实际目视", "按生成粒度验收")),
    SettingSpec("生成优先序", ("n2d",), ("关键镜优先", "分镜顺序", "先易后难")),
    SettingSpec(
        "一致性增强",
        ("n2d",),
        ("锚点+参考图", "指定参考图", "+LoRA", "image2image_reference_chain", "本机慢速不等待，优先 image2image/多图参考链"),
        key_aliases=("一致性增强(LoRA)",),
        parameterized=True,
    ),
    SettingSpec("本机LoRA慢速策略", ("n2d",), parameterized=True, syncable=False),
    SettingSpec("一致性严格度", ("n2d",), ("demo", "standard", "production", "production_no_cost_image"),
                key_aliases=("一致性发布档", "一致性落地档", "一致性验收档", "制作质量档")),
    SettingSpec("重抽预算策略", ("n2d",), ("预算充足", "预算一般")),
    SettingSpec("脸一致性机检后端", ("n2d",), ("arcface", "styleid", "自动按画风"), key_aliases=("脸encoder", "face_encoder")),
    SettingSpec("N2D_STYLEID_MODEL", ("n2d",), ("kwanY/styleid", "自定义"), key_aliases=("StyleID模型", "StyleID model"), parameterized=True, syncable=False),
    SettingSpec("妖类脸部规则", ("n2d",), parameterized=True),
    SettingSpec("更新重制策略", ("n2d",), ("最小", "严审刷新")),
    SettingSpec("BGM来源", ("n2d",), ("占位", "文件", "Suno"), parameterized=True),
    SettingSpec("接缝兜底", ("n2d",), ("硬切", "微溶解", "报警"), parameterized=True),
    SettingSpec("目标平台", ("n2d",), ("抖音", "快手", "B站", "小红书", "红果", "YouTube", "TikTok", "ReelShort", "视频号", "跨平台", "未定"), parameterized=True, sensitive=True),
    SettingSpec("发行地区", ("n2d",), ("中国大陆", "港澳台", "北美", "东南亚", "全球", "自定义"), parameterized=True, sensitive=True),
    SettingSpec(
        "合规用途",
        ("n2d",),
        ("internal_only", "publish_candidate", "paid_distribution"),
        aliases={
            "demo": "internal_only",
            "demo_only": "internal_only",
            "内部demo": "internal_only",
            "内部 demo": "internal_only",
            "内部预览": "internal_only",
            "内部学习": "internal_only",
            "学习demo": "internal_only",
            "学习 demo": "internal_only",
            "demo学习": "internal_only",
            "学习使用": "internal_only",
            "demo学习使用": "internal_only",
            "做demo学习使用": "internal_only",
            "自用demo": "internal_only",
            "不发布": "internal_only",
            "不公开发布": "internal_only",
            "发布候选": "publish_candidate",
            "公开发布候选": "publish_candidate",
            "付费投放": "paid_distribution",
            "商业投放": "paid_distribution",
        },
        sensitive=True,
    ),

    # shared physical tools.
    SettingSpec("换脸后端", ("all",), ("FaceFusion",), syncable=False),
    SettingSpec("swap模型", ("all",), ("inswapper_128_fp16", "hyperswap_256"), syncable=False),
    SettingSpec("增强模型", ("all",), ("gfpgan_1.4", "codeformer"), syncable=False),
    SettingSpec("源脸合法性", ("all",), ("本人", "授权", "合成"), syncable=False, sensitive=True),

    SettingSpec("生图AI-切换记录", ("n2d",), metadata=True, syncable=False),
)


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def detect_family(work_root: str) -> str:
    root = os.path.abspath(work_root)
    parts = root.split(os.sep)
    for part in reversed(parts):
        if part in FAMILY_ROOTS:
            return FAMILY_ROOTS[part]
    if os.path.isfile(os.path.join(root, "_进度.md")) and any(
        os.path.exists(os.path.join(root, marker)) for marker in N2D_PROJECT_MARKERS
    ):
        return "n2d"
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
SETTING_SOURCE_RE = re.compile(r"(?:^|\s)source=([A-Za-z0-9_-]+)\b")


def _split_value_comment(raw: str) -> Tuple[str, str]:
    """Split a setting value from a trailing markdown comment."""
    value, sep, comment = str(raw or "").partition("#")
    return value.strip(), (comment.strip() if sep else "")


def _setting_source_from_comment(comment: str) -> str:
    m = SETTING_SOURCE_RE.search(comment or "")
    return m.group(1).strip() if m else ""


def _format_setting_value(value: str, source: Optional[str]) -> str:
    value = str(value or "").strip()
    source = str(source or "").strip()
    return f"{value}  # source={source}" if source else value


def load_settings(work_root: str) -> Dict[str, str]:
    """Parse `<作品根>/_设置.md` into `{key: value}` without global defaults."""
    return {key: meta["value"] for key, meta in load_settings_meta(work_root).items()}


def load_settings_meta(work_root: str) -> Dict[str, Dict[str, str]]:
    """Parse project settings with lightweight provenance metadata.

    Provenance is encoded as a trailing markdown comment, e.g.
    `- 制作模式：原生音画  # source=explicit_user`.
    Older lines without a source remain valid and get `source=""`.
    """
    text = _read_text(os.path.join(work_root.rstrip("/"), "_设置.md"))
    out: Dict[str, Dict[str, str]] = {}
    for line in _settings_region_lines(text):
        m = SETTING_LINE_RE.match(line)
        if not m:
            continue
        key = m.group(1).strip()
        val, comment = _split_value_comment(m.group(2))
        if key and key not in out:
            out[key] = {"value": val, "source": _setting_source_from_comment(comment), "line": line}
    return out


# Context-pack consumers need the current settings, but must not receive the
# whole append-only audit trail as if every historical sentence were still a
# current project fact.  Keep this projection in the settings helper so the
# authoritative region boundary stays identical to ``load_settings_meta``.
SETTINGS_CONTEXT_CORRECTION_LIMIT = 3
SETTINGS_CONTEXT_RECORD_MAX_CHARS = 600
_CORRECTION_RECORD_MARKERS = (
    "数据校正",
    "事实校正",
    "口径校正",
    "更正",
    "纠正",
    "订正",
    "修正",
    "作废",
    "不再作为",
    "以此为准",
    "以最新为准",
)


def _settings_record_candidates(text: str) -> Tuple[List[str], str]:
    """Return audit-record candidates in newest-first helper order.

    Current files have a ``## 记录`` region and ``append_record`` prepends new
    entries there.  Very old files sometimes placed dated bullets directly in
    the document; those remain readable without ever becoming setting lines.
    """
    lines = text.splitlines()
    idx = _record_index(lines)
    if idx is not None:
        candidates = [line for line in lines[idx + 1:] if _looks_like_record_line(line)]
        return candidates, "record_section"
    legacy = [line for line in lines if _looks_like_record_line(line)]
    # Legacy writers were not consistent about prepend vs append.  ISO dates
    # let us recover newest-first ordering without changing same-day order.
    legacy.sort(
        key=lambda line: (
            re.search(r"\d{4}-\d{2}-\d{2}", line).group(0)
            if re.search(r"\d{4}-\d{2}-\d{2}", line)
            else ""
        ),
        reverse=True,
    )
    return legacy, ("legacy_dated_lines" if legacy else "none")


def _compact_record_line(line: str) -> str:
    value = re.sub(r"^\s*[-*]\s*", "", str(line or "").strip())
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) > SETTINGS_CONTEXT_RECORD_MAX_CHARS:
        value = value[:SETTINGS_CONTEXT_RECORD_MAX_CHARS].rstrip() + "…"
    return value


def settings_context_snapshot(
    work_root: str,
    *,
    correction_limit: int = SETTINGS_CONTEXT_CORRECTION_LIMIT,
) -> Dict[str, Any]:
    """Build a bounded, history-safe settings view for downstream agents.

    ``effective_settings`` is derived exclusively from
    :func:`load_settings_meta`, which stops at the first ``## 记录`` heading
    and ignores legacy dated audit lines.  Audit records are non-authoritative
    provenance: only explicitly corrective entries are included, with a hard
    cap.  Parsing failure fails closed to an empty snapshot; callers must never
    fall back to previewing the entire file.
    """
    path = os.path.join(work_root.rstrip("/"), "_设置.md")
    exists = os.path.isfile(path)
    try:
        limit = max(0, min(int(correction_limit), SETTINGS_CONTEXT_CORRECTION_LIMIT))
    except (TypeError, ValueError):
        limit = SETTINGS_CONTEXT_CORRECTION_LIMIT

    base: Dict[str, Any] = {
        "kind": "n2d_settings_context",
        "version": 1,
        "status": "missing" if not exists else "empty",
        "source_path": "_设置.md",
        "authority": {
            "effective_settings": "settings.load_settings_meta:settings_region_before_record_section",
            "audit_records": "provenance_only_non_authoritative",
            "records_can_override_effective_settings": False,
        },
        "effective_settings": {},
        "recent_corrections": [],
        "record_summary": {
            "format": "none",
            "records_seen": 0,
            "corrections_seen": 0,
            "corrections_included": 0,
            "limit": limit,
            "full_history_omitted": True,
        },
    }
    if not exists:
        return base

    try:
        meta = load_settings_meta(work_root)
        # Do not expose raw source lines: a source comment is the only
        # provenance needed by a stage consumer, and raw lines may carry
        # unrelated legacy prose.
        effective: Dict[str, Dict[str, str]] = {}
        for key, item in meta.items():
            effective[str(key)] = {
                "value": str(item.get("value") or ""),
                "source": str(item.get("source") or ""),
            }

        text = _read_text(path)
        candidates, record_format = _settings_record_candidates(text)
        corrections = [
            compact
            for line in candidates
            for compact in [_compact_record_line(line)]
            if compact and any(marker in compact for marker in _CORRECTION_RECORD_MARKERS)
        ]
        included = corrections[:limit]
        base["effective_settings"] = effective
        base["recent_corrections"] = [
            {
                "text": text,
                "authority": "provenance_only_non_authoritative",
            }
            for text in included
        ]
        base["record_summary"] = {
            "format": record_format,
            "records_seen": len(candidates),
            "corrections_seen": len(corrections),
            "corrections_included": len(included),
            "limit": limit,
            "full_history_omitted": True,
        }
        base["status"] = "ok" if effective else "empty"
        return base
    except Exception:
        # Fail closed: an unreadable/malformed settings file must not make the
        # context builder leak the raw append-only audit trail as a fallback.
        base["status"] = "parse_error"
        base["issues"] = [
            "settings helper could not build a current-settings projection; raw _设置.md history was intentionally omitted"
        ]
        return base


# ── _设置.md 并发安全：flock + 原子写（与 progress.py 对称；并行 batch agent 抢写不再撕裂）──
_settings_lock_state = threading.local()


@contextlib.contextmanager
def _settings_lock(lock_root: str, *, lockname: str = "_设置.lock",
                   timeout: float = 30.0, poll: float = 0.1):
    """串行化 `_设置.md` 的 read-modify-write（单机多 worker / 并行 batch）。

    按 lock-path **可重入**：同线程已持同一把锁时嵌套获取是 no-op（set_project_setting 内部还会
    调 append_record，二者同锁；work_root 与 global 是不同文件、不同锁，互不误共享）。"""
    lock_root = str(lock_root).rstrip("/") or "."
    os.makedirs(lock_root, exist_ok=True)
    path = os.path.join(lock_root, lockname)
    held = getattr(_settings_lock_state, "held", None)
    if held is None:
        held = {}
        _settings_lock_state.held = held
    if held.get(path, 0) > 0:  # 本线程已持该锁 → 可重入 no-op
        held[path] += 1
        try:
            yield path
        finally:
            held[path] -= 1
        return
    start = time.time()
    if fcntl is not None:
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
        try:
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.time() - start > timeout:
                        raise TimeoutError(f"settings lock timeout ({timeout}s): {path}")
                    time.sleep(poll)
            held[path] = 1
            try:
                yield path
            finally:
                held[path] = 0
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
    else:  # pragma: no cover - non-POSIX 目录锁兜底
        lock_dir = path + ".d"
        acquired = False
        try:
            while True:
                try:
                    os.mkdir(lock_dir)
                    acquired = True
                    break
                except FileExistsError:
                    if time.time() - start > timeout:
                        raise TimeoutError(f"settings lock timeout ({timeout}s): {path}")
                    time.sleep(poll)
            held[path] = 1
            try:
                yield path
            finally:
                held[path] = 0
        finally:
            if acquired:
                with contextlib.suppress(OSError):
                    os.rmdir(lock_dir)


def _atomic_write_text(path: str, text: str) -> None:
    """同目录 temp + os.replace；读者永不见半写状态。"""
    directory = os.path.dirname(path) or "."
    tmp = os.path.join(directory, f".{os.path.basename(path)}.tmp.{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def write_settings(
    work_root: str,
    fields: Dict[str, str],
    *,
    note: Optional[str] = None,
    bold_keys: bool = False,
    source: str = "global_default",
    sources: Optional[Dict[str, str]] = None,
):
    """Write `<作品根>/_设置.md` for per-work private choices."""
    lines = ["# 设置 — 本作私有选择点（skills/n2d/references/选择点与偏好.md）", ""]
    if note:
        lines += [f"> {note}", ""]

    for k, v in fields.items():
        shown = v if v not in (None, "", []) else "（未定）"
        key_str = f"**{k}**" if bold_keys else k
        lines.append(f"- {key_str}：{_format_setting_value(str(shown), (sources or {}).get(k, source))}")

    lines += [
        "",
        "> 这些值由 init 按 CLI 参数/全局默认落定；同项目后续**沉默沿用**，"
        "改了在此更新。合规/不可逆/花钱多的点每次仍向用户确认。",
    ]

    path = os.path.join(work_root.rstrip("/"), "_设置.md")
    with _settings_lock(work_root):
        _atomic_write_text(path, "\n".join(lines) + "\n")
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
    with _settings_lock(work_root):
        content = _read_text(path)
        if not content:
            content = "# 设置 — 本作私有选择点（skills/n2d/references/选择点与偏好.md）\n"
        lines = content.splitlines()
        entry = f"- {date or time.strftime('%Y-%m-%d')} {message}"
        idx = _record_index(lines)
        if idx is None:
            if lines and lines[-1].strip():
                lines.append("")
            lines.extend(["## 记录", entry])
        else:
            lines.insert(idx + 1, entry)
        _atomic_write_text(path, "\n".join(lines).rstrip() + "\n")


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
    source: str = "explicit_user",
) -> Tuple[Optional[str], str]:
    """Patch one setting line in place, preserving notes and records."""
    work_root = work_root.rstrip("/")
    family = detect_family(work_root)
    if validate:
        check = validate_setting(key, value, family=family)
        if check["level"] in ("warn", "error"):
            raise ValueError(_format_validation_error(check))
        value = str(check.get("value", value))
    canonical = canonical_setting_key(key, family)
    path = os.path.join(work_root, "_设置.md")
    with _settings_lock(work_root):
        content = _read_text(path)
        if not content:
            content = "# 设置 — 本作私有选择点（skills/n2d/references/选择点与偏好.md）\n\n"
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
            old_val, _comment = _split_value_comment(m.group(2))
            lines[i] = f"{m.group(1)}{_format_setting_value(value, source)}{m.group(3)}"
            updated = True
            break

        if not updated:
            insert_after = _last_setting_line_index(lines)
            new_line = f"- {canonical}：{_format_setting_value(value, source)}"
            if insert_after is None:
                insert_at = 2 if len(lines) >= 2 else len(lines)
                lines.insert(insert_at, new_line)
            else:
                lines.insert(insert_after + 1, new_line)

        _atomic_write_text(path, "\n".join(lines).rstrip() + "\n")
        if record:
            append_record(work_root, message or f"设置 {canonical} = {value} (source={source}, 原值: {old_val})")
    return old_val, value


def reset_project_setting(work_root: str, key: str, *, record: bool = True) -> Optional[str]:
    work_root = work_root.rstrip("/")
    family = detect_family(work_root)
    canonical = canonical_setting_key(key, family)
    path = os.path.join(work_root, "_设置.md")
    with _settings_lock(work_root):
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
                    old_val, _comment = _split_value_comment(m.group(2))
                    removed = True
                    continue
            kept.append(line)
        if not removed:
            return None
        _atomic_write_text(path, "\n".join(kept).rstrip() + "\n")
        if record:
            append_record(work_root, f"重置选项 {canonical} (原值: {old_val})")
    return old_val


def reset_all_project_settings(work_root: str, *, record: bool = True) -> List[str]:
    work_root = work_root.rstrip("/")
    path = os.path.join(work_root, "_设置.md")
    with _settings_lock(work_root):
        settings = load_settings(work_root)
        content = _read_text(path)
        lines = content.splitlines()
        stop = _record_index(lines)
        scan_end = len(lines) if stop is None else stop
        kept: List[str] = []
        for i, line in enumerate(lines):
            if i < scan_end and not _looks_like_record_line(line) and SETTING_LINE_RE.match(line):
                continue
            kept.append(line)
        _atomic_write_text(path, "\n".join(kept).rstrip() + "\n")
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
    alias_value = spec.aliases.get(_norm(value)) if spec.aliases else None
    if alias_value:
        value = normalize_setting_value(spec.key, alias_value)
    if spec.metadata:
        return {"level": "info", "key": key, "canonical_key": spec.key, "value": value, "message": "project metadata"}
    if spec.key == "生视频AI":
        if _validate_video_backend_list(value, spec):
            return {
                "level": "warn",
                "key": key,
                "canonical_key": spec.key,
                "value": value,
                "message": "legacy combined field; prefer 生视频模型 + 生视频渠道, and use this only for old-project fallback",
            }
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


IMAGE_MODEL_TOKENS = (
    "gpt image", "gpt-image", "seedream", "nano banana", "gemini", "flux", "可灵主体库模型",
)
IMAGE_CHANNEL_TOKENS = (
    "codex", "openai", "dreamina", "即梦", "seedream", "可灵", "kling", "nano banana", "sora", "cli", "api",
)
IMAGE_NATIVE_SUBJECT_CHANNEL_TOKENS = ("seedream", "可灵", "kling", "主体库", "character id", "face lock", "sora cameo")
IMAGE_NO_NATIVE_SUBJECT_CHANNEL_TOKENS = ("codex", "openai", "dreamina", "即梦", "nano banana")
LONG_PROJECT_MARKERS = ("多集", "长线", "长篇", "量产", "series", "long")


def _n2d_episode_count(work_root: str) -> int:
    try:
        pattern = os.path.join(work_root.rstrip("/"), "脚本", "*", "storyboard.json")
        return len({os.path.basename(os.path.dirname(p)) for p in glob.glob(pattern)})
    except Exception:
        return 0


def _contains_any(value: str, tokens: Iterable[str]) -> bool:
    norm = _norm(value)
    return any(_norm(token) in norm for token in tokens)


def _audit_n2d_cross_settings(work_root: str, settings: Dict[str, str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    # `load_settings()` intentionally contains project-local values only.  A
    # sensitive setting such as compliance usage may therefore come entirely
    # from the repository default and used to escape `settings audit`.  Audit
    # the effective fallback whenever the project has not pinned it locally;
    # known aliases normalize through the same SettingSpec, while unknown
    # values remain an error (and compliance continues to fail closed).
    if "合规用途" not in settings:
        effective_compliance = get_setting(work_root, "合规用途", DEFAULTS["合规用途"])
        compliance_row = validate_setting("合规用途", effective_compliance, family="n2d")
        compliance_row = dict(compliance_row)
        compliance_row["effective"] = True
        compliance_row["message"] = (
            "effective default: " + str(compliance_row.get("message") or "")
        )
        rows.append(compliance_row)
    image_model = settings.get("生图模型", "")
    image_channel = settings.get("生图AI") or settings.get("生图渠道") or ""
    if image_model and _contains_any(image_model, IMAGE_CHANNEL_TOKENS) and not _contains_any(image_model, IMAGE_MODEL_TOKENS):
        rows.append({
            "level": "warn",
            "key": "生图模型",
            "canonical_key": "生图模型",
            "value": image_model,
            "message": "looks like a channel/access path; 生图模型 must name the generator model, while 生图AI/生图渠道 names the channel",
        })
    if image_channel and _contains_any(image_channel, ("gpt image", "gpt-image", "gemini 3 pro image", "flux 2 pro")):
        rows.append({
            "level": "warn",
            "key": "生图AI",
            "canonical_key": "生图AI",
            "value": image_channel,
            "message": "looks like a model name; 生图AI is the channel/access path. Put concrete model names in 生图模型",
        })
    if "生视频AI" in settings and ("生视频模型" not in settings or "生视频渠道" not in settings):
        rows.append({
            "level": "warn",
            "key": "生视频AI",
            "canonical_key": "生视频AI",
            "value": settings.get("生视频AI", ""),
            "message": "legacy field is present without the split 生视频模型 + 生视频渠道 pair; split it before new production",
        })
    scale = settings.get("项目规模", "")
    long_project = _contains_any(scale, LONG_PROJECT_MARKERS) or _n2d_episode_count(work_root) >= 3
    if long_project and image_channel and _contains_any(image_channel, IMAGE_NO_NATIVE_SUBJECT_CHANNEL_TOKENS) and not _contains_any(image_channel, IMAGE_NATIVE_SUBJECT_CHANNEL_TOKENS):
        rows.append({
            "level": "warn",
            "key": "生图AI",
            "canonical_key": "生图AI",
            "value": image_channel,
            "message": "long-running n2d project is using an image channel without persistent subject/character-id evidence; prefer a native subject backend or register face_embedding/LoRA before batch production",
        })
    if long_project and not scale:
        rows.append({
            "level": "warn",
            "key": "项目规模",
            "canonical_key": "项目规模",
            "value": "",
            "message": "multiple storyboards imply a long-running project; record 项目规模=多集长线 or 长篇量产 so first-run backend choices match consistency risk",
        })
    return rows


def audit_settings(work_root: str) -> Dict[str, Any]:
    family = detect_family(work_root)
    settings = load_settings(work_root)
    rows = [validate_setting(k, v, family=family) for k, v in settings.items()]
    if family == "n2d":
        rows.extend(_audit_n2d_cross_settings(work_root, settings))
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
    global_dir = os.path.dirname(global_path) or "."
    os.makedirs(global_dir, exist_ok=True)
    # 全局默认文件可被不同项目的并行 batch agent 同时写 → 独立锁（按 global 文件所在目录）+ 原子写。
    with _settings_lock(global_dir, lockname="_global设置.lock"):
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
        _atomic_write_text(global_path, "\n".join(lines).rstrip() + "\n")
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
    spec = get_setting_spec(key)
    if spec and spec.aliases:
        alias = spec.aliases.get(_norm(normalized))
        if alias:
            normalized = alias
    if key == "重抽预算策略" and normalized in {"预算不足", "预算不够"}:
        return "预算一般"
    if key == "更新重制策略" and normalized == "保图刷新":
        return "严审刷新"
    if key == "合成阶段":
        if normalized in {"不选", "默认不选", "关闭", "关闭合成", "跳过合成", "不合成"}:
            return "跳过"
        if normalized in {"开启", "需要", "合成", "合成成片", "启用合成"}:
            return "启用"
    return normalized


def _setting_lookup_keys(key: str, family: Optional[str] = None) -> List[str]:
    spec = get_setting_spec(key, family)
    keys = [key]
    if spec:
        keys = [spec.key, *spec.key_aliases]
        if key not in keys:
            keys.append(key)
    return keys


def get_setting(work_root: str, key: str, default: Optional[str] = None) -> str:
    """Read a setting from `<作品根>/_设置.md`, then global defaults, then fallback."""
    work_root = work_root.rstrip("/")
    spec = get_setting_spec(key)
    canonical = spec.key if spec else key
    lookup_keys = _setting_lookup_keys(key)
    project_text = _read_text(os.path.join(work_root, "_设置.md"))
    for lookup_key in lookup_keys:
        project = _extract_setting(project_text, lookup_key)
        if project:
            return normalize_setting_value(canonical, project)
    repo = repo_root_from(work_root)
    for path in global_settings_paths(repo):
        global_text = _read_text(path)
        for lookup_key in lookup_keys:
            global_val = _extract_setting(global_text, lookup_key)
            if global_val:
                return normalize_setting_value(canonical, global_val)
    if default is not None:
        return normalize_setting_value(canonical, default)
    return normalize_setting_value(canonical, DEFAULTS.get(canonical, DEFAULTS.get(key, "")))


def project_setting_source(work_root: str, key: str, family: Optional[str] = None) -> str:
    """Return project-local provenance for a setting key; global defaults are not considered."""
    family = family or detect_family(work_root)
    spec = get_setting_spec(key, family)
    lookup_keys = _setting_lookup_keys(key, family)
    meta = load_settings_meta(work_root)
    for lookup_key in lookup_keys:
        if lookup_key in meta:
            return meta[lookup_key].get("source", "")
    if spec and spec.key in meta:
        return meta[spec.key].get("source", "")
    return ""


def production_mode(work_root: str) -> str:
    mode = get_setting(work_root, "制作模式", DEFAULTS["制作模式"])
    return mode or DEFAULTS["制作模式"]


def is_video_first(work_root: str) -> bool:
    return "先出视频" in production_mode(work_root)


def is_hybrid_routing(work_root: str) -> bool:
    """`制作模式=混合自动路由`: timing-first, per-shot sound routing."""
    mode = production_mode(work_root)
    low = mode.lower()
    return "混合自动路由" in mode or "hybrid" in low or "mixed" in low


def is_native_av(work_root: str) -> bool:
    """`制作模式=原生音画`: speaking shots use native synchronized A/V."""
    mode = production_mode(work_root)
    return "原生音画" in mode or "native_av" in mode.lower()
