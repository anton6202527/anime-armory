#!/usr/bin/env python3
"""Generate n2d episode images through Codex's image_generation feature.

This is the Codex backend adapter used by N2D_IMAGE_COMMAND.  It keeps the
batch wrapper backend-agnostic while giving Codex a real PNG-producing path:

1. Parse the episode prompt pack.
2. Ask ``codex exec --image ... --json --enable image_generation`` to generate one target image.
3. Decode the ``image_generation_end`` event payload into a temporary PNG.
4. Archive the old target, move the new PNG into place, and record dashboard
   telemetry including the seed downgrade status.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

try:
    from PIL import Image, ImageFilter, ImageOps
except Exception:  # pragma: no cover - Pillow-less runner falls back to raw refs.
    Image = None  # type: ignore[assignment]
    ImageFilter = None  # type: ignore[assignment]
    ImageOps = None  # type: ignore[assignment]

N2D_LIB = Path(__file__).resolve().parents[2] / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))

from image_backend_adapter import current_image_backend_selection  # noqa: E402
from settings import get_setting  # noqa: E402
from image_prompt_compiler import (  # noqa: E402
    COMPILED_HEADING,
    compile_image_prompt,
    contract_from_section,
    infer_task_type as infer_image_task_type,
    lint_compiled_prompt as lint_compiled_image_prompt,
    normalize_exclusions,
)
from n2d_contract import (  # noqa: E402
    CHARACTER_LIBRARY_TIER_CORE,
    CHARACTER_LIBRARY_TIER_MINIMAL,
    CHARACTER_LIBRARY_TIER_PARTIAL,
    CHARACTER_LIBRARY_TIER_STANDARD,
    IDENTITY_REVIEW_BINDING_FINGERPRINT_KIND,
    character_library_tier_for_record,
    identity_review_binding_fingerprint,
    identity_review_contract_for_view,
    identity_review_required_criteria,
    identity_reviewed_at_errors,
    identity_reviewer_appears_automated,
    required_character_reference_group_fields,
)

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
from visual_reference_policy import (  # noqa: E402
    IDENTITY_GENERATION_POLICIES,
    STYLE_GENERATION_POLICIES,
    evaluate_generation_reference,
    reference_manifest_generation_issues,
)


PROMPT_REL = Path("出图") / "{episode}" / "prompt" / "01_分镜出图.md"
DASHBOARD = Path("skills") / "n2d" / "n2d-dashboard" / "scripts" / "dashboard.py"
IMAGE_QC = Path("skills") / "n2d" / "n2d-image" / "scripts" / "image_qc.py"
COMPLIANCE = Path("skills") / "n2d" / "n2d-compliance" / "scripts" / "compliance.py"
PROGRESS = Path("skills") / "n2d" / "progress.py"
SOURCE = "skills/n2d/n2d-image/scripts/codex_image_runner.py"
STYLE_ANCHOR_REGISTRY = Path("出图") / "共享" / "style_anchor_registry.json"
MAX_CODEX_REFERENCE_IMAGES = int(os.environ.get("N2D_CODEX_MAX_REFERENCE_IMAGES", "5"))
MAX_CODEX_CHARACTER_REFERENCES_PER_OWNER = int(os.environ.get("N2D_CODEX_MAX_CHARACTER_REFERENCES_PER_OWNER", "4"))
IMAGE_QC_PYTHON_ENV = "N2D_IMAGE_QC_PYTHON"
REFERENCE_ENHANCE_MIN_SHORT_EDGE = int(os.environ.get("N2D_REFERENCE_ENHANCE_MIN_SHORT_EDGE", "1024"))
REFERENCE_ENHANCE_MAX_LONG_EDGE = int(os.environ.get("N2D_REFERENCE_ENHANCE_MAX_LONG_EDGE", "2048"))
REFERENCE_ENHANCE_ENABLED = os.environ.get("N2D_REFERENCE_ENHANCE", "1").strip().lower() not in {
    "0", "false", "no", "off"
}
IMAGE_QC_PYTHON_CANDIDATES = (
    "/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python",
    "~/miniforge3/envs/facefusion/bin/python",
    "~/mambaforge/envs/facefusion/bin/python",
    "~/anaconda3/envs/facefusion/bin/python",
)
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
SHARED_ASSET_ID_PREFIXES = ("CHAR_", "BEAST_", "GROUP_", "LOC_", "PROP_", "MOUNT_", "WEAPON_", "OUTFIT_", "VFX_")
EPISODE_CLIP_IMAGE_RE = re.compile(r"^Clip_?\d{2}_.+\.(?:png|jpg|jpeg|webp)$", re.I)
CROSS_EPISODE_SOURCE_FRAME_LINE_RE = re.compile(
    r"(?:跨集接力源帧|上一集尾帧|前集尾帧|prev_tail_frame|cross_episode_handoff)",
    re.I,
)
FAILED_SHARED_REF_STATUSES = {"review_failed", "failed", "fail", "rejected", "needs_regen", "blocked"}
STYLE_ANCHOR_READY_STATUSES = {"ready", "approved", "selected", "selected_anchor", "style_anchor", "pass", "ok"}
STRICT_IMAGE_REVIEW_MODE = "逐张机器QC+实际目视"
CHARACTER_SHARED_CORE_FIELDS = required_character_reference_group_fields(CHARACTER_LIBRARY_TIER_CORE)
CHARACTER_SHARED_STANDARD_FIELDS = required_character_reference_group_fields(CHARACTER_LIBRARY_TIER_STANDARD)
CHARACTER_SHARED_MINIMAL_FIELDS = required_character_reference_group_fields(CHARACTER_LIBRARY_TIER_MINIMAL)
CHARACTER_SHARED_BODY_FIELDS = ("half_body", "full_body", "outfit")
CHARACTER_SHARED_FACE_FIELDS = ("face_anchor_refs", "expressions")
REALISTIC_RENDERING_STYLE_GUIDANCE = (
    "项目基础视觉风格只由 _设置.md、storyboard.style_contract 与 style_anchor 决定。"
    "严格继承其线条或材质语言、色彩分级、镜头语言和完成度，不得擅自替换成写实、3D、赛璐璐、水墨、Q版或其它未选择风格；"
    "单张人物参考图只锁身份、服装和道具结构，不覆盖项目风格。"
)
EXTERNAL_CHARACTER_REFERENCE_GUIDANCE = (
    "用户提供的人物/主角参考图默认只作身份与身形锚：只提取基础身高、体型/身材比例、体态、脸型、五官比例、"
    "眼神气质、肤质、年龄感等身份信息。不得继承参考图里的画风、照片/摄影风格、渲染风格、滤镜、色彩分级、"
    "光影方案、景深、清晰度质感、构图/镜头语言、背景、服装、裸露程度、发型/发饰、表情、姿态、配饰、"
    "场景、IP/水印或原图剧情状态；外部参考图的风格权重视为 0。项目风格必须以 _设置.md 的基础视觉风格、"
    "本集 style_contract/基础视觉风格契约和角色/资产 registry 为唯一真值，统一转译到项目风格。"
)
NON_CHARACTER_FACE_POLICY_GUIDANCE = (
    "非角色资产/VFX/道具/武器/场景若未在 registry 显式声明 owner/carries_identity 且 face_policy=face_locked，"
    "不得生成清晰可辨的人物脸、角色立绘或替任何角色定妆；只能画纯资产/纯特效/环境，或下巴以下、背身、侧后剪影、无脸人台等尺度参考。"
    "一旦画到具名角色脸，必须绑定对应 CHAR_xx/形态并引用同源定妆组，否则视为脸漂失败。"
)
FULL_BODY_SHOES_GUIDANCE = (
    "人物全身、标准立绘、正面/前45°/侧面/后45°/背面、五角 turnaround、全身动作参考必须头到脚完整入画，鞋靴/脚部清楚可见；"
    "不得裁掉脚、被衣摆/烟雾完全遮住鞋、或用半身构图冒充全身。半身/脸部特写目标按其命名豁免。"
)
STYLE_ONLY_REFERENCE_GUIDANCE = (
    "项目统一风格锚只用于学习当前 style_contract 的线条/材质/渲染语言、色彩分级、镜头焦段和完成度；"
    "不得继承风格锚里的具体人物身份、五官、服装、动作、剧情状态、背景场景或构图。"
)
SHARED_MAKEUP_BOARD_GUIDANCE = (
    "共享角色定妆必须是统一规格的定妆参考板，不是剧情剧照：统一中性灰白/18%灰棚拍背景，"
    "背景干净无窗、无房间、无家具、无剧情道具、无环境叙事；同一胸口高度机位、"
    "同一 70mm 左右等效镜头、同一柔和均匀棚拍光，并继承项目已选 style_contract；"
    "不得擅自切换风格，不要剧情动作、台词表演、复杂场面调度。"
)
RESTRICTED_PARTIAL_BOARD_GUIDANCE = (
    "restricted_partial 局部角色只出手部、肩背、布料或侧后剪影参考板；不建立完整正脸，不生成可识别主角脸，"
    "不画跪哭/递笔录等剧情剧照；统一中性灰白/18%灰棚拍背景，无窗、无房间、无剧情道具。"
)
REFERENCE_ATTACHMENT_PRIORITY_GUIDANCE = (
    "本次通过 `codex exec --image` 附加的参考图是真实视觉证据，身份/服装/道具结构优先级高于文字描述。"
    "每个 `character` 附件必须按 owner 绑定到对应角色，禁止把 A 的脸、发型、衣服或配饰套给 B，"
    "禁止把多人合成一张新脸，禁止新造未登记主角脸。人物近景/对白/主检镜必须让眼鼻嘴三角区可比对，"
    "不得用过暗、过小、头发遮脸、背影或无脸来逃避身份一致性；动作镜可用 45°/侧脸/过肩露脸，"
    "但仍要保留可核验的脸型、发际线、眉眼、鼻口比例、发型轮廓、服装剪影、色卡和标志配饰。"
    "若文字 prompt 与附件/registry 冲突：身份、发型、服装、道具外形以附件和 registry 为准，"
    "文字只控制本镜动作、构图、情绪、光线和场景调度。"
)
REFERENCE_QUALITY_GUIDANCE = (
    "若用户参考图或外部参考图分辨率低、压缩重、来自截图或带播放器/搜索框/字幕/UI，参考图只提供身份、兽脸结构、"
    "体态、服装轮廓或道具拓扑信息；不得继承低清、像素化、模糊、压缩块、屏幕截图质感、播放按钮、平台 UI、字幕、"
    "水印或原图画幅。runner 会优先把短边低于 1024px 的参考图升采样为增强入参；最终输出仍必须按项目质量生成"
    "清晰、干净、高分辨率的正式 PNG，而不是复制参考图的低分辨率质感。"
)


@dataclass
class ClipSection:
    clip: str
    title: str
    body: str
    target_line: str


@dataclass
class Target:
    shot: str
    clip: str
    mode: str
    rel_path: str
    section: ClipSection
    variant_note: str = ""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def executable_python(path: str) -> Optional[str]:
    expanded = os.path.expanduser(str(path or "").strip())
    if not expanded:
        return None
    if os.path.isfile(expanded) and os.access(expanded, os.X_OK):
        return expanded
    return None


def image_qc_python() -> str:
    """Interpreter for full image_qc.

    The generator may run under Homebrew/system Python 3.14, but image_qc's
    full face stack is expected in the visual QC conda env.  Falling back to
    sys.executable is allowed only when no configured/full candidate exists.
    """
    configured = executable_python(os.environ.get(IMAGE_QC_PYTHON_ENV, ""))
    if configured:
        return configured
    for candidate in IMAGE_QC_PYTHON_CANDIDATES:
        found = executable_python(candidate)
        if found:
            return found
    return sys.executable


def normalize_episode(value: str) -> str:
    text = str(value).strip()
    if re.fullmatch(r"\d+", text):
        return f"第{text}集"
    return text


def split_csv(value: str) -> List[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def rel_to_root(path: str, episode: str) -> str:
    text = path.strip().strip("`")
    if not text:
        return text
    if text.startswith("出图/"):
        return text
    if "/" in text:
        return text
    return str(Path("出图") / episode / "图片" / text)


def first_backticked(text: str) -> Optional[str]:
    match = re.search(r"`([^`]+)`", text)
    return match.group(1) if match else None


def backticked(text: str) -> List[str]:
    return re.findall(r"`([^`]+)`", text)


def cross_episode_source_frame_paths(text: str) -> List[str]:
    paths: List[str] = []
    seen: Set[str] = set()
    for line in str(text or "").splitlines():
        if not CROSS_EPISODE_SOURCE_FRAME_LINE_RE.search(line):
            continue
        candidates = backticked(line)
        candidates.extend(
            match.group(0)
            for match in re.finditer(r"[\w./\-\u4e00-\u9fff]+?\.(?:png|jpg|jpeg|webp)", line, re.I)
        )
        for raw in candidates:
            rel = str(raw or "").strip()
            if Path(rel).suffix.lower() not in IMAGE_SUFFIXES or rel in seen:
                continue
            seen.add(rel)
            paths.append(rel)
    return paths


def load_sections(root: Path, episode: str) -> List[ClipSection]:
    prompt_path = root / str(PROMPT_REL).format(episode=episode)
    if not prompt_path.is_file():
        raise FileNotFoundError(f"prompt pack not found: {prompt_path}")
    storyboard_targets = load_storyboard_target_lines(root, episode)
    text = prompt_path.read_text(encoding="utf-8")
    headers = list(re.finditer(r"^##\s+(?:(Clip)[_\s-]*([0-9０-９]+)|(镜头)\s*([0-9０-９]+))[^\n]*$", text, re.M))
    sections: List[ClipSection] = []
    for index, header in enumerate(headers):
        start = header.start()
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        body = text[start:end].strip()
        compiled_marker = re.search(rf"(?m)^\s*{re.escape(COMPILED_HEADING)}\s*$", body)
        if compiled_marker:
            body = body[: compiled_marker.start()].rstrip()
        title = header.group(0).strip()
        raw_num = header.group(2) or header.group(4)
        if not raw_num:
            continue
        raw_num = raw_num.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
        clip = f"Clip_{int(raw_num):02d}"
        target_match = re.search(r"^\*\*(?:目标|目标落档|本镜出图张数)\*\*：([^\n]+)$", body, re.M)
        target_line = target_match.group(1).strip() if target_match else storyboard_targets.get(clip, "")
        sections.append(ClipSection(clip=clip, title=title, body=body, target_line=target_line))
    return sections


def load_storyboard_target_lines(root: Path, episode: str) -> dict[str, str]:
    """Build target lines from storyboard frame paths when prompt omits them."""
    path = root / "脚本" / episode / "storyboard.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    targets: dict[str, str] = {}
    for index, clip_data in enumerate(data.get("clips") or [], start=1):
        if not isinstance(clip_data, dict):
            continue
        clip = storyboard_clip_key(clip_data, index)
        paths: list[str] = []
        first = clip_data.get("firstframe_png")
        if isinstance(first, str) and first.strip():
            paths.append(first.strip())
        continuity = clip_data.get("continuity") or {}
        if isinstance(continuity, dict):
            midframe = continuity.get("midframe") or {}
            if isinstance(midframe, dict):
                anchor = midframe.get("anchor_png") or midframe.get("midframe_png")
                if isinstance(anchor, str) and anchor.strip():
                    paths.append(anchor.strip())
            for anchor_data in continuity.get("anchors") or []:
                if not isinstance(anchor_data, dict):
                    continue
                anchor = anchor_data.get("anchor_png")
                if isinstance(anchor, str) and anchor.strip():
                    paths.append(anchor.strip())
            endframe = continuity.get("endframe_png")
            if isinstance(endframe, str) and endframe.strip():
                paths.append(endframe.strip())
        if paths:
            deduped = list(dict.fromkeys(paths))
            targets[clip] = " ".join(f"`{item}`" for item in deduped)
    return targets


def current_episode_target_paths(root: Path, episode: str) -> Set[str]:
    """Return the live episode image namespace declared by the current prompt."""
    paths: Set[str] = set()
    try:
        sections = load_sections(root, episode)
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        return paths
    prefix = f"出图/{episode}/图片/"
    for section in sections:
        for raw in backticked(section.target_line):
            rel = rel_to_root(raw, episode)
            if rel.startswith(prefix) and Path(rel).suffix.lower() in IMAGE_SUFFIXES:
                paths.add(rel)
    return paths


def stale_episode_image_artifacts(root: Path, episode: str) -> List[str]:
    """Find Clip PNGs in the live image dir that the current prompt does not own.

    Keeping an old coarse-cut batch beside a regenerated fine-cut batch makes
    downstream storyboard/video prompts pick stale frames by accident.  The
    current prompt target list is the only live namespace for an episode.
    """
    declared = current_episode_target_paths(root, episode)
    if not declared:
        return []
    image_dir = root / "出图" / episode / "图片"
    if not image_dir.is_dir():
        return []
    stale: List[str] = []
    for path in sorted(image_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if not EPISODE_CLIP_IMAGE_RE.fullmatch(path.name):
            continue
        rel = str(path.relative_to(root))
        if rel not in declared:
            stale.append(rel)
    return stale


def enforce_current_episode_image_namespace(root: Path, episode: str) -> bool:
    stale = stale_episode_image_artifacts(root, episode)
    if not stale:
        return True
    print(
        "[gate] 本集图片目录存在当前 `01_分镜出图.md` 未声明的旧/旁路 Clip PNG。"
        "先移入 `废料/出图/第N集/...` 并同步 storyboard/video prompt，禁止继续生成：",
        file=sys.stderr,
    )
    for rel in stale[:40]:
        print(f"  - {rel}", file=sys.stderr)
    if len(stale) > 40:
        print(f"  ... and {len(stale) - 40} more", file=sys.stderr)
    return False


def storyboard_clip_key(clip_data: dict, fallback_index: int) -> str:
    for key in ("clip", "id"):
        value = clip_data.get(key)
        if value is None:
            continue
        text = str(value)
        match = re.search(r"(?:CLIP|Clip|clip)[_\s-]*([0-9]+)", text)
        if not match:
            match = re.search(r"镜头[_\s-]*([0-9]+)", text)
        if not match:
            match = re.fullmatch(r"\s*([0-9]+)\s*", text)
        if match:
            return f"Clip_{int(match.group(1)):02d}"
    return f"Clip_{fallback_index:02d}"


def load_shared_sections(root: Path) -> List[Target]:
    """Resolve shared makeup/reference prompt sections into generation targets.

    Shared prompt files use a different schema from episode shots.  We only
    generate the primary file listed first in ``目标存档``; derived face/half-body
    references can be generated later as explicit follow-up targets if needed.
    """
    prompt_dir = root / "出图" / "共享" / "prompt"
    files = ["风格锚.md", "角色定妆.md", "场景定妆.md", "道具定妆.md", "法宝定妆.md", "特效定妆.md"]
    targets: List[Target] = []
    section_by_alias: list[tuple[set, ClipSection]] = []
    seen_paths: set[str] = set()

    def add_target(shot: str, rel_path: str, section: ClipSection, aliases: set, variant_note: str = "") -> None:
        rel = rel_to_root(rel_path, "共享")
        if not is_shared_image_path(rel) or rel in seen_paths:
            return
        seen_paths.add(rel)
        target = Target(shot=shot, clip=shot, mode="shared", rel_path=rel, section=section, variant_note=variant_note)
        setattr(target, "aliases", aliases)
        targets.append(target)
    for filename in files:
        path = prompt_dir / filename
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        headers = list(re.finditer(r"^##\s+(.+)$", text, re.M))
        for index, header in enumerate(headers):
            start = header.start()
            end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
            body = text[start:end].strip()
            target_match = re.search(r"\*\*目标存档\*\*：([^\n]+)", body)
            if not target_match:
                continue
            first = first_backticked(target_match.group(1))
            if not first:
                continue
            title = header.group(0).strip()
            aliases = shared_aliases(title, body, first)
            shot = preferred_shared_shot(title, aliases, first)
            section = ClipSection(clip=shot, title=title, body=body, target_line=target_match.group(1).strip())
            section_by_alias.append((aliases, section))
            for rel in shared_image_paths_from_text(body):
                variant_shot = shared_variant_shot(shot, rel)
                add_target(variant_shot, rel, section, aliases, shared_variant_note(rel, section_body=body))
    add_registry_shared_targets(root, section_by_alias, add_target)
    return targets


def is_shared_image_path(path: str) -> bool:
    text = str(path or "").strip().strip("`")
    suffix = Path(text).suffix.lower()
    return text.startswith("出图/共享/图片/") and suffix in {".png", ".jpg", ".jpeg", ".webp"}


def shared_image_paths_from_text(text: str) -> List[str]:
    paths: List[str] = []
    seen: set[str] = set()
    for raw in backticked(text):
        if "<" in raw or ">" in raw:
            continue
        suffix = Path(raw).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        rel = rel_to_root(raw, "共享")
        if is_shared_image_path(rel) and rel not in seen:
            seen.add(rel)
            paths.append(rel)
    return paths


def shared_variant_shot(base: str, rel_path: str) -> str:
    stem = Path(rel_path).stem
    token = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", stem, flags=re.UNICODE).strip("_")
    return f"{base}::{token or stem}"


def shared_variant_note(rel_path: str, *, section_body: str = "") -> str:
    stem = Path(rel_path).stem
    architectural_fixture = bool(re.search(
        r"墙上固定|固定安装|建筑构件|窗框|窗台|门框|楼梯(?:扶栏|栏杆)|扶栏|栏杆",
        str(section_body or ""),
    ))
    installed_furniture = bool(re.search(
        r"长方木桌|餐桌|桌面|桌腿|床榻|长凳|家具",
        str(section_body or ""),
    ))
    small_hand_prop = bool(re.search(
        r"掌心|掌长|掌宽|一掌高|单手(?:完整)?(?:握持|托住|包住)|8\s*(?:至|到|[-~])\s*10\s*厘米|12\s*(?:至|到|[-~])\s*16\s*厘米",
        str(section_body or ""),
    ))
    if "风格锚" in stem or "style_anchor" in stem.lower():
        return (
            "本次目标是抽象分区式视觉语言控制板，不是剧情剧照、环境设定图、海报或道具陈列："
            "只展示色卡、明暗/光比阶梯、线条笔触和近裁材质样本；"
            "不得出现人物、动物/妖物、建筑/城寨、兵器、道具、器皿、家具、卷轴、地图、可读或伪造文字与剧情动作。"
        )
    real_quadruped = bool(re.search(
        r"真实四足|四(?:只|条)?(?:虎)?掌(?:全部)?着地|野生猫科|四足兽类",
        str(section_body or ""),
    ))
    if real_quadruped:
        if "脸部特写" in stem or "表情" in stem:
            return (
                "本次目标是真实四足动物的同源头部近景：保持兽首、圆耳、短吻、眼鼻比例、毛纹与主参考一致；"
                "肩颈以下自然裁切。禁止人脸化、兽人化、类人胸臂、衣装、文字或水印。"
            )
        if any(token in stem for token in ("45度", "三分之二", "_侧", "侧面", "_背", "背面")):
            return (
                "本次目标是真实四足动物的同源角度参考：四只兽掌着地，躯干水平，肩胛、脊背、骨盆、四肢和长尾"
                "符合真实物种解剖；按文件名角度旋转整体身体，不只转头。禁止双足直立、虎头人身/狼头人身、"
                "类人胸肌、手臂手掌、兽人或妖物形态。"
            )
        return (
            "本次目标是真实四足动物的共享主参考图：四只兽掌全部着地，躯干水平，头部正对相机，"
            "肩胛、脊背、骨盆、四肢和长尾符合真实物种解剖；全身从耳尖、四掌到尾尖完整可见。"
            "禁止双足直立、虎头人身/狼头人身、类人胸肌、手臂手掌、兽人、妖物、衣装或剧情伤痕。"
        )
    if "布局图" in stem or "空间图" in stem or "平面图" in stem or "spatial_map" in stem:
        return (
            "本次目标是场景空间布局图，不是电影气氛图：必须用俯视或高位等距视角画清平面关系，"
            "只标出资产登记和场景卡已声明的入口、门窗、家具/常驻物件、人物站位、运动路径、轴线和光源；"
            "不得凭空新增破顶、交战区、高位来源、暗道或其他未登记结构。"
            "只准一张连续的单幅俯视布局，不得添加标题、图例栏、侧栏、立面图、参考小图或多格说明板。"
            "允许最多八个简短中文标签、箭头和区域色块，但不要长句；禁止只生成普通仰拍/平视场景插画。"
        )
    if "手部局部" in stem:
        return (
            "本次目标是功能群体/资产的手部局部参考：只画手、前臂、袖口、握持或牵绳/火把接触点，"
            "中性浅灰背景，手部数量和左右归属清楚；禁止出现清晰人物脸、完整角色立绘、现代物件或剧情动作。"
        )
    if "布料局部" in stem or "材质局部" in stem:
        return (
            "本次目标是服装/布料材质局部参考：只画肩背、袖口、衣襟、布纹、磨损和颜色层级，"
            "不建立新人物身份；禁止出现清晰人物脸、全身立绘、可读文字、现代 logo 或剧情动作。"
        )
    if stem.endswith("反打"):
        return (
            "本次目标是场景主视图的真实反打空间参考：摄影机必须移到主视图的对面或轴线另一端，朝原机位方向拍摄，"
            "需要看到主视图未展示的对侧墙面/入口/家具背面，并让登记地标在画面中的左右关系合理反转。"
            "建筑材质、天气、时间、冷暖光源和常驻物件必须与主视图同源；禁止复制主视图或只做轻微变焦/平移，禁止新增人物、文字、现代物件或改换地点。"
        )
    if stem.endswith("_反面"):
        if "DOORFRAME" in stem.upper() or "定妆_道具_门框" in stem:
            return (
                "本次目标是同一空门框的真实背面结构参考：摄影机移到门框背侧，完整展示两根立柱、双层上横梁、底槛、"
                "背侧榫接、墙体安装面和木构连接；门洞中央必须从上到下保持完全通透，尺寸、净空、木色、磨损与主参考一致。"
                "这是门框资产，不是门扇资产：绝对禁止在门洞内生成门扇、门板、栅板、帘子、横撑、门闩、把手或任何填充物；"
                "禁止镜像或复刻正面、禁止现代合页/金属锁、人物、文字或水印。"
            )
        if architectural_fixture:
            return (
                "本次目标是同一固定建筑构件的真实背面结构参考：摄影机必须移到构件背侧，完整展示主参考不可见的背板、"
                "加固横档、榫接、木轴/安装点及其与门框或墙体的连接；保持主参考的板材数量、外框尺寸、木色、磨损和开合方向。"
                "门类资产不得把正面可见的横木门闩、把手或装饰原样复制到背面，只展示结构上合理的背侧加固与穿榫证据；"
                "禁止镜像或复刻正面、禁止只做轻微变焦、禁止拆离门框、禁止新增现代合页、金属锁、人物、文字或水印。"
            )
        if installed_furniture:
            return (
                "本次目标是同一家具的真实背面/底部结构参考：摄影机移到主参考背侧并降低机位，完整展示背侧框架、"
                "桌板/座板底面、腿足、横撑、榫卯和承重连接；保持主参考的尺寸、板材厚度、腿数、木色与磨损。"
                "禁止镜像或复刻主视图、禁止只做轻微变焦、禁止新增抽屉、现代五金、人物、文字或水印。"
            )
        return (
            "本次目标是同一道具的真实反面结构参考：摄影机移到主参考背侧，完整展示正面不可见的背板、内侧、"
            "加固件、榫接和安装/承重点；保持主参考的数量、轮廓、尺寸、材质、颜色与磨损。"
            "禁止镜像或复刻正面、禁止只做轻微变焦、禁止把正面把手/门闩/装饰原样复制到背面，"
            "禁止新增现代五金、人物、文字或水印。"
        )
    if "握持比例" in stem:
        return (
            "本次目标是武器握持比例参考：以中性浅灰背景展示武器全长、手掌握点、人与武器尺度关系，"
            "画面要能判断长度、重心和刃部方向；人体只作尺度尺或握持手部参考，必须裁到下巴以下、背身、"
            "侧后剪影或无脸中性人台，禁止出现清晰可辨的人物五官/肖像脸，禁止把比例图画成角色立绘；"
            "禁止只画无尺度的武器美术图。"
        )
    if stem.endswith("_比例"):
        if small_hand_prop:
            return (
                "本次目标是小型道具的真实尺度证据图，不是产品独照：同一中性棚拍画面必须出现一只完整成年手掌，"
                "并让道具完整落在掌心内或与手掌同平面紧邻；道具任何边都不得超过登记的掌长/掌宽上限。"
                "完整五指与手腕必须可见且解剖自然，只出现这一只手，裁到前臂；禁止删除尺度参照、禁止放大成盾牌/托盘/大木板，"
                "禁止清晰人物脸、完整人物、文字标尺、水印、多格拼板或单独产品照。"
            )
        return (
            "本次目标是道具尺度/比例参考：必须展示道具完整轮廓、背带/提带/握点、主要结构件和材质，"
            "并加入一个无脸尺度参照（单手/双手/前臂、下巴以下中性人台或背身剪影均可），让观众能判断"
            "道具与手掌/前臂/躯干的真实比例；中性浅灰背景，禁止只复制主道具静物，禁止无尺度参照，"
            "禁止出现清晰可辨人物五官/新角色脸，禁止文字标尺、水印或现代物件。"
        )
    if stem.endswith("_手持"):
        if architectural_fixture:
            return (
                "本次目标是固定建筑构件的真实操作参考，不是把构件拆下来搬运：构件必须完整安装在墙体/门洞/楼梯上，"
                "只出现一名裁到下巴以下或背身的无脸中性成年人，用单手正常推、拉、扶或扣住登记的操作点，"
                "清楚展示手、操作点、固定框与墙体的连接。禁止双手捧着整块窗/门/栏杆，禁止拆离墙体、产品陈列、多格拼板、清晰人脸、文字或水印。"
            )
        if installed_furniture:
            return (
                "本次目标是大件家具的日常交互参考，不是搬运演示：家具必须四腿/底座完整落地并保持正常使用方向，"
                "只出现一名裁到下巴以下或背身的无脸成年人，以坐、俯身、一手扶桌沿/床沿或放置小物的自然姿势展示接触点和高度。"
                "禁止将整张桌、床、凳子抬起、抱在怀里或悬空，禁止多格拼板、多人演示、清晰人脸、文字或水印。"
            )
        if small_hand_prop:
            return (
                "本次目标是小型道具单手持用参考：只出现一只成年人的手和前臂；道具完整落在掌心、由五指包持或托住，"
                "任何边不得超过登记的掌长/掌宽上限。完整五指和手腕连接必须清楚自然，另一只手完全不入画。"
                "禁止双手捧持导致道具放大，禁止产品独照、完整人物、清晰人脸、多格拼板、文字或水印。"
            )
        return (
            "本次目标是道具手持/携行参考：必须出现单手/双手/前臂或下巴以下中性人台，清楚展示手与"
            "提带/背带/握点/包体的接触方式、承重点和携行姿态；道具主体仍要完整可读且结构不漂移。"
            "禁止只画无人静物，禁止清晰人物五官/新角色脸，禁止把道具改成现代背包、武器或不相关器物。"
        )
    if "_动作_持" in stem:
        return (
            "本次目标是同源角色持械动作参考：保持角色身份、服装和武器结构，展示清楚双手/单手握持位置、"
            "武器全长、身体重心和鞋靴落点；全身动作必须头到脚完整入画。这是共享动作库，不是剧情分镜。"
        )
    if "青烟成枪" in stem:
        return (
            "本次目标是武器动态形态参考：青烟凝成庚金长枪的结构必须完整可读，烟雾只包裹轮廓，"
            "枪尖、枪杆、尾端和绿色法术能量层级清楚；禁止画成散雾或无实体光束。"
        )
    if any(token in stem for token in ("后45度", "后3／4", "后四分之三", "侧背")):
        return (
            "本次目标是后3/4参考：同一角色同一服装，中性浅灰背景，头、颈、双肩线、胸腔、腰背、"
            "骨盆、膝盖和双脚作为一个整体，从严格正背面向同一侧旋转约45°；近侧肩胯更大、远侧肩胯"
            "被遮挡，背部平面必须出现明确透视收缩，只露少量侧脸轮廓。全身从头到鞋靴完整可见；禁止"
            "只有头部回转而躯干仍正背对称，禁止后脑正中、双肩等宽、双鞋跟对称的纯背面，禁止前3/4。"
            "若角色锚写苍白干裂病容，只表现为病弱苍白肤色和轻微干唇，不得画成脸颊树枝状黑线、龟裂"
            "纹、妖化纹、疤痕或开放性伤口；可见侧脸必须服从同源脸锚。"
        )
    if "45度" in stem:
        return "本次目标是 45° / 三分之二侧脸参考：同一角色同一服装，中性浅灰背景，脸部转向约 45°，人物全身从头到鞋靴完整可见；不是正脸改名，也不是纯侧脸。"
    if stem.endswith("_侧"):
        return (
            "本次目标是严格90°标准全侧面参考：同一角色同一服装，中性浅灰背景，脸、肩线、胸腔、"
            "骨盆和双脚朝同一个侧向一起旋转到90°；脸部只能看到一只眼、一个耳朵和清晰的鼻梁/嘴唇/"
            "下颌侧影，另一侧眼睛与另一侧耳朵必须完全不可见。保持同身高同景别，人物全身从头到鞋靴"
            "完整可见；禁止前45°、禁止双眼可见、禁止正面胸口、禁止凭空新增疤痕/裂纹/纹身。"
        )
    if stem.endswith("_背"):
        return (
            "本次目标是严格180°正背面参考：同一角色同一服装，中性浅灰背景，后脑、后颈、双肩背线、"
            "腰背、骨盆、双腿和鞋跟都正对镜头；人物全身从头到鞋靴完整可见，重点锁发型背面、布巾尾带、"
            "衣料背部层次、伤臂吊带背侧连接与背影轮廓。脸、双眼、鼻梁、嘴唇、正面胸口和前襟必须完全"
            "不可见；禁止后45°冒充正背面，禁止人物回头，禁止凭空新增背部武器、图案、文字或配件。"
        )
    if "半身" in stem:
        return "本次目标是半身服装参考：人物主体居中，头身中线接近画面中线，左右留白均衡，重点锁服装剪裁、材质和配饰。"
    if "脸部特写" in stem:
        return "本次目标是脸部特写参考：肩颈以上近景，眼鼻嘴三角区清晰，五官与主参考同一张脸，服装/发型边缘可见。"
    if "三视图" in stem:
        return "本次目标是人审 turnaround 拼版（旧文件名兼容）：同一角色同一服装，正面、前3/4、侧面、后3/4、背面五角同框排列，同身高、同比例、头顶线/脚底线/身体中心线/水平视平线对齐，每个全身视图都必须从头到鞋靴完整可见。"
    if "_表情_六联表" in stem:
        return (
            "本次目标是同源六联表情表：以已通过的角色正面脸锚为母图，在 2×3 等分网格中依次呈现"
            "冷静、警觉、震惊、隐忍、将哭、决绝六种肩颈以上表情；六格必须是同一角色、同一年龄、"
            "同一发型妆造、同一脸型与五官比例，只改变 FACS/AU 肌肉组合。统一中性浅灰背景和均匀棚拍光，"
            "每格头部尺寸/视平线一致；不烤入文字标签、不画成六个不同人物、不换衣、不改变镜头角度。"
        )
    if "_表情_" in stem:
        emotion = stem.split("_表情_", 1)[-1]
        return (
            f"本次目标是同源表情脸部近景参考：保持同一角色身份和妆造，只改变表情为「{emotion}」；"
            "画面必须是肩颈以上到胸口以内的近景，脸部占画面 30%-50%，眼鼻嘴三角区清晰，"
            "不得画成全身/远景/多人构图，脸部不可换人。"
        )
    if "定妆_场景_" in stem:
        return (
            "本次目标是生产级场景主母本：优先锁定地标、空间轴线、出入口、常驻物件和主光方向；"
            "只生成一张连续的全画幅单机位场景，不得做上下/左右多格拼板、分镜板，不得同时附送反打、"
            "俯视图或平面图；禁止可读或伪造文字牌匾、对联、标签与水印。"
            "不生成摄影棚、角色立绘或人物全身参考板。若场景合同明确绑定倒地/尸体常驻主体，"
            "仅把该主体作为场景连续性地标，严格继承其身份附件"
        )
    return "本次目标是共享主参考图：中性档案，不带剧情戏剧动作，锁身份/场景/道具/特效基准；人物全身/标准立绘必须头到鞋靴完整可见，半身/脸部特写目标除外。"


def requires_controlled_makeup_derivation(rel_path: str) -> bool:
    """Character split references cannot be safely text-generated one by one."""
    stem = Path(rel_path).stem
    if not stem.startswith(("CHAR_", "定妆_")):
        return False
    if stem.endswith("_三视图"):
        return not stem.endswith("_背影_三视图")
    if "_表情_" in stem:
        return True
    unsafe_suffixes = (
        "_45度",
        "_后45度",
        "_后3／4",
        "_后四分之三",
        "_侧",
        "_背",
        "_侧背",
        "_侧影",
        "_半身",
        "_全身翼展",
        "_全身",
        "_脸部特写",
        "_群像sheet",
        "_sheet",
    )
    return stem.endswith(unsafe_suffixes)


def shared_group_member_variant_guidance(target: Target) -> str:
    """Keep group-character split refs as one representative member, not a sheet."""
    if target.mode != "shared":
        return ""
    stem = Path(target.rel_path).stem
    if "群像sheet" in stem or "多人群像" in stem:
        return ""
    if not requires_controlled_makeup_derivation(target.rel_path):
        return ""
    aliases = " ".join(str(alias) for alias in (getattr(target, "aliases", set()) or set()))
    text = "\n".join([str(target.shot or ""), aliases, str(target.section.body or "")])
    if not any(token in text for token in ("群像", "队伍", "群体", "队员")):
        return ""
    if any(
        token in text
        for token in (
            "restricted_partial",
            "只保留低头侧后剪影",
            "不建立清晰个人正脸",
            "只手部/剪影/布料局部",
        )
    ):
        return ""
    return (
        "共享群像角色角度资产硬约束：本目标不是群像 sheet，必须从该群像身份中抽取"
        "一名普通代表成员作为样板军士/样板队员来画；前3/4、侧面、后3/4、背面、半身、脸部特写"
        "只能出现这一名代表成员，三视图可以同框排列多个角度但必须是同一名成员的多视图。"
        "不得画成多人队列、三名军士并排、重复复制人、关系图或小队合影；仍保持功能角色/普通队员气质，"
        "不要把他升级成独一无二的主角脸。"
    )


def requires_human_review_before_ready(rel_path: str) -> bool:
    """Text-generated character front/turnaround images are only candidates until human-approved."""
    stem = Path(rel_path).stem
    if not stem.startswith(("CHAR_", "定妆_")):
        return False
    if stem.endswith("_三视图"):
        return True
    if "_表情_" in stem:
        return True
    if requires_controlled_makeup_derivation(rel_path):
        return False
    return True


def has_controlled_makeup_source(rel_path: str, reference_inputs: Sequence[Dict[str, Any]]) -> bool:
    """Allow split makeup refs only when a same-source parent image is attached."""
    if not requires_controlled_makeup_derivation(rel_path):
        return True
    expected = {Path(candidate).stem for candidate in controlled_makeup_parent_candidates(rel_path)}
    for item in reference_inputs or []:
        ref_stem = Path(str(item.get("rel_path") or item.get("abs_path") or "")).stem
        if ref_stem in expected:
            return True
    return False


def controlled_makeup_parent_candidates(rel_path: str) -> List[str]:
    """Return likely same-source parent images for split makeup references."""
    if not requires_controlled_makeup_derivation(rel_path):
        return []
    path = Path(rel_path)
    stem = path.stem
    is_turnaround = stem.endswith("_三视图")
    base = re.sub(r"_(?:表情_.+|后45度|后3／4|后四分之三|45度|侧|背|侧背|侧影|半身|全身翼展|全身|脸部特写|群像sheet|sheet|三视图)$", "", stem)
    parent = path.parent.as_posix()
    if is_turnaround:
        stems = [
            base,
            f"{base}_front",
            f"{base}_正面",
            f"{base}_45度",
            f"{base}_侧",
            f"{base}_后45度",
            f"{base}_背",
            f"{base}_半身",
            f"{base}_全身",
        ]
    else:
        stems = [base, f"{base}_front", f"{base}_正面", f"{base}_三视图"]
    suffixes = [path.suffix or ".png", ".png", ".jpg", ".jpeg", ".webp"]
    out: List[str] = []
    seen: Set[str] = set()
    for candidate_stem in stems:
        for suffix in suffixes:
            rel = f"{parent}/{candidate_stem}{suffix}"
            if rel in seen:
                continue
            seen.add(rel)
            out.append(rel)
    return out


def shared_prop_variant_parent(rel_path: str) -> str:
    """Return the approved primary prop path for scale/in-hand derivatives."""
    path = Path(rel_path)
    stem = path.stem
    base = re.sub(r"_(?:比例|手持|scale|in_hand)$", "", stem, flags=re.IGNORECASE)
    if base == stem:
        return ""
    return f"{path.parent.as_posix()}/{base}{path.suffix or '.png'}"


def add_registry_shared_targets(root: Path, section_by_alias: list[tuple[set, ClipSection]], add_target) -> None:
    identity_path = root / "出图" / "共享" / "identity_registry.json"
    if identity_path.is_file():
        try:
            identity = json.loads(identity_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            identity = {}
        for character in identity.get("characters") or []:
            char_id = str(character.get("id") or "")
            for form in character.get("forms") or []:
                if not isinstance(form, dict):
                    continue
                form_name = str(form.get("form") or "")
                aliases = registry_form_aliases(char_id, form_name)
                section = find_shared_section(section_by_alias, aliases)
                if not section:
                    continue
                for rel in registry_image_paths(form):
                    shot = shared_variant_shot(next(iter(sorted(aliases))) or char_id or "shared", rel)
                    add_target(shot, rel, section, aliases, shared_variant_note(rel, section_body=section.body))

    asset_path = root / "出图" / "共享" / "asset_registry.json"
    if asset_path.is_file():
        try:
            assets = json.loads(asset_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            assets = {}
        for asset in assets.get("assets") or []:
            if not isinstance(asset, dict):
                continue
            asset_id = str(asset.get("id") or "")
            aliases = {asset_id, str(asset.get("name") or "")}
            section = find_shared_section(section_by_alias, aliases)
            if not section:
                continue
            asset_contract = json.dumps(
                {
                    "name": asset.get("name"),
                    "constraints": asset.get("constraints"),
                    "current_state": asset.get("current_state"),
                    "scene_dna": asset.get("scene_dna"),
                },
                ensure_ascii=False,
            )
            for rel in registry_image_paths(asset):
                shot = shared_variant_shot(asset_id or "asset", rel)
                add_target(
                    shot,
                    rel,
                    section,
                    aliases,
                    shared_variant_note(rel, section_body=f"{section.body}\n{asset_contract}"),
                )


def registry_form_aliases(char_id: str, form_name: str) -> set[str]:
    aliases = {char_id, f"{char_id}/{form_name}", form_name}
    if char_id == "CHAR_01" and "常态" in form_name:
        aliases.add("CHAR_01/常态")
    if char_id == "CHAR_01" and "觉醒" in form_name:
        aliases.add("CHAR_01/觉醒态")
    if char_id == "CHAR_02":
        aliases.add("CHAR_02/常态")
    if char_id == "CHAR_03" and "善姑" in form_name:
        aliases.add("CHAR_03/善姑伪装")
    if char_id == "CHAR_03" and "妖形" in form_name:
        aliases.add("CHAR_03/妖形半露")
    if char_id == "CHAR_04":
        aliases.add("CHAR_04/常态")
    return {item for item in aliases if item}


def find_shared_section(section_by_alias: list[tuple[set, ClipSection]], aliases: set[str]) -> Optional[ClipSection]:
    form_aliases = {alias for alias in aliases if "/" in alias}
    if form_aliases:
        for section_aliases, section in section_by_alias:
            if section_aliases.intersection(form_aliases):
                return section
    for section_aliases, section in section_by_alias:
        if section_aliases.intersection(aliases):
            title = section.title
            if any(alias in title for alias in aliases if alias.startswith(SHARED_ASSET_ID_PREFIXES)):
                return section
    for section_aliases, section in section_by_alias:
        if section_aliases.intersection(aliases):
            return section
    return None


def registry_image_paths(value) -> List[str]:
    paths: List[str] = []
    seen: set[str] = set()

    def walk(node) -> None:
        if isinstance(node, dict):
            status = str(node.get("status") or "").lower()
            path = node.get("path")
            if isinstance(path, str) and (not status or status in {"ready", "planned", "pass", "todo", "review_pending"}):
                add(path)
            for key, child in node.items():
                if key in {"source", "source_image"}:
                    continue
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            add(node)

    def add(raw: str) -> None:
        suffix = Path(raw).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
            return
        rel = rel_to_root(raw, "共享")
        if is_shared_image_path(rel) and rel not in seen:
            seen.add(rel)
            paths.append(rel)

    walk(value.get("reference_group") if isinstance(value, dict) else value)
    if isinstance(value, dict):
        walk(value.get("reference_atlas"))
        walk(value.get("scene_atlas"))
    return paths


def shared_aliases(title: str, body: str, rel_path: str) -> set:
    stem = Path(rel_path).stem
    aliases = {stem, Path(rel_path).name}
    title_text = re.sub(r"^##\s*", "", title).strip()
    title_name = re.split(r"[（(]", title_text, maxsplit=1)[0].strip()
    if title_name:
        aliases.add(title_name)
    if "风格锚" in stem or "style_anchor" in stem.lower():
        aliases.update({"风格锚", "STYLE_ANCHOR", "style_anchor"})
    # The section title owns the shared target identity.  Body text may mention
    # related assets, such as VFX_01 in a character form, but those references
    # must not become selectable aliases for this target.
    ids = re.findall(r"`?((?:CHAR|BEAST|GROUP|LOC|PROP|MOUNT|WEAPON|OUTFIT|VFX)_[A-Za-z0-9_\u4e00-\u9fff]+)`?", title)
    aliases.update(ids)
    form_refs = re.findall(r"`?((?:CHAR|BEAST|GROUP)_[A-Za-z0-9_\u4e00-\u9fff]+/[A-Za-z0-9_\u4e00-\u9fff·.-]+)`?", f"{title}\n{body}")
    aliases.update(form_refs)
    if "CHAR_01" in aliases and "常态" in title:
        aliases.add("CHAR_01/常态")
    if "CHAR_01" in aliases and "觉醒态" in title:
        aliases.add("CHAR_01/觉醒态")
    if "CHAR_02" in aliases:
        aliases.add("CHAR_02/常态")
    if "CHAR_03" in aliases and "人皮态" in title:
        aliases.add("CHAR_03/人皮态")
    return {a for a in aliases if a}


def preferred_shared_shot(title: str, aliases: set, rel_path: str) -> str:
    title_ids = re.findall(r"`((?:CHAR|BEAST|LOC|PROP|WEAPON|OUTFIT|VFX)_[A-Za-z0-9_\u4e00-\u9fff]+)`", title)
    for ident in title_ids:
        form_alias = ""
        if ident == "CHAR_01" and "常态" in title:
            form_alias = "CHAR_01/常态"
        elif ident == "CHAR_01" and "觉醒态" in title:
            form_alias = "CHAR_01/觉醒态"
        elif ident == "CHAR_02":
            form_alias = "CHAR_02/常态"
        elif ident == "CHAR_03" and "人皮态" in title:
            form_alias = "CHAR_03/人皮态"
        if form_alias and form_alias in aliases:
            return form_alias
        if ident in aliases:
            return ident
    for prefix in ("CHAR_", "BEAST_", "LOC_", "PROP_", "WEAPON_", "OUTFIT_", "VFX_"):
        candidates = sorted(a for a in aliases if isinstance(a, str) and a.startswith(prefix))
        if candidates:
            return candidates[0]
    return Path(rel_path).stem


def normalize_shot_name(shot: str) -> str:
    text = str(shot).strip()
    text = text.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    match = re.fullmatch(r"(?:镜头|shot|clip)?[_\s-]*([0-9]+)(?:_(mid|end|first|first_mid|a[0-9]+))?", text, re.I)
    if match:
        suffix = f"_{match.group(2)}" if match.group(2) else ""
        return f"Clip_{int(match.group(1)):02d}{suffix}"
    match = re.fullmatch(r"Clip[_\s-]*([0-9]+)(?:_(mid|end|first|first_mid|a[0-9]+))?", text, re.I)
    if match:
        suffix = f"_{match.group(2)}" if match.group(2) else ""
        return f"Clip_{int(match.group(1)):02d}{suffix}"
    return text


def section_for(sections: Sequence[ClipSection], shot: str) -> ClipSection:
    shot = normalize_shot_name(shot)
    match = re.search(r"Clip_(\d+)", shot)
    if not match:
        raise ValueError(f"invalid shot name: {shot}")
    clip = f"Clip_{int(match.group(1)):02d}"
    for section in sections:
        if section.clip == clip:
            return section
    raise ValueError(f"no prompt section found for {shot}")


def declared_target_suffix(section: ClipSection, raw_path: str) -> str:
    """Return the frame selector encoded by a prompt-declared target path.

    Most projects use ``_a1``/``_mid``/``_end``, but production storyboards
    also name timed action anchors ``_anchor01`` or
    ``_anchor_cut_0360``.  The prompt target line is the physical-output
    truth, so the runner must not silently drop a valid PNG merely because its
    suffix is more descriptive than the legacy shorthand.
    """
    stem = Path(raw_path).stem
    clip_match = re.search(r"(\d+)$", str(section.clip or ""))
    if clip_match:
        number = int(clip_match.group(1))
        match = re.match(rf"^(?:EP\d+_)?CLIP0*{number}_(.+)$", stem, re.I)
        if match:
            return match.group(1)
    return stem


def declared_target_mode(section: ClipSection, raw_path: str, first_path: str = "") -> str:
    rel = str(raw_path or "")
    if first_path and rel == first_path:
        return "firstframe"
    suffix = declared_target_suffix(section, rel).lower()
    if suffix == "first":
        return "firstframe"
    if suffix == "end":
        return "tailframe"
    return "midframe"


def target_for_shot(shot: str, section: ClipSection, episode: str) -> Target:
    shot = normalize_shot_name(shot)
    line = section.target_line
    if not line:
        raise ValueError(f"{section.clip}: target line missing")
    paths = backticked(line)

    # Prefer an exact prompt-declared suffix before applying the legacy
    # ``*_end`` shortcut.  A relay clip can legitimately begin from the prior
    # clip's ``..._end.png`` and also declare its own ``ClipNN_end.png``.  The
    # old shortcut selected the first path containing ``_end`` and therefore
    # redrew the relay source instead of the requested tail frame.
    custom_match = re.fullmatch(rf"{re.escape(section.clip)}_(.+)", shot, re.I)
    if custom_match:
        requested_suffix = custom_match.group(1)
        exact_path = next((
            raw for raw in paths
            if declared_target_suffix(section, raw).lower() == requested_suffix.lower()
            or Path(raw).stem.lower() == requested_suffix.lower()
        ), "")
        if exact_path:
            mode = declared_target_mode(section, exact_path, paths[0] if paths else "")
            return Target(
                shot=shot,
                clip=section.clip,
                mode=mode,
                rel_path=rel_to_root(exact_path, episode),
                section=section,
            )

    if shot.endswith("_end"):
        path = next((p for p in paths if "_end" in Path(p).stem), paths[-1] if paths else "")
        if not path:
            raise ValueError(f"{shot}: tail-frame target missing")
        return Target(shot=shot, clip=section.clip, mode="tailframe", rel_path=rel_to_root(path, episode), section=section)

    anchor_suffix = re.search(r"_(mid|first_(?:mid|a\d+)|a\d+)$", shot)
    if anchor_suffix:
        suffix = anchor_suffix.group(1)
        suffix = suffix.replace("first_", "")
        path = next((p for p in paths if Path(p).stem.endswith(f"_{suffix}")), "")
        if not path:
            path = next((p for p in paths if "_mid" in Path(p).stem or re.search(r"_a\d+$", Path(p).stem)), paths[1] if len(paths) > 1 else "")
        if path:
            return Target(shot=shot, clip=section.clip, mode="midframe", rel_path=rel_to_root(path, episode), section=section)
        raise ValueError(f"{shot}: mid/anchor target missing")

    custom_match = re.fullmatch(rf"{re.escape(section.clip)}_(.+)", shot, re.I)
    if custom_match:
        requested_suffix = custom_match.group(1)
        path = next((
            raw for raw in paths
            if declared_target_suffix(section, raw).lower() == requested_suffix.lower()
            or Path(raw).stem.lower() == requested_suffix.lower()
        ), "")
        if not path:
            raise ValueError(f"{shot}: declared frame target missing")
        mode = declared_target_mode(section, path, paths[0] if paths else "")
        return Target(shot=shot, clip=section.clip, mode=mode, rel_path=rel_to_root(path, episode), section=section)

    first = paths[0] if paths else first_backticked(line)
    if not first:
        raise ValueError(f"{shot}: first-frame target missing")
    return Target(shot=shot, clip=section.clip, mode="firstframe", rel_path=rel_to_root(first, episode), section=section)


def expand_shot_targets(shot: str, section: ClipSection, episode: str) -> List[Target]:
    """Resolve a requested Clip into its prompt-declared frame targets.

    A bare ``Clip_01`` means "generate the whole clip frame set" when the
    prompt declares multiple target PNGs.  Explicit frame requests such as
    ``Clip_01_mid`` and ``Clip_01_end`` still resolve to one target.
    """
    normalized = normalize_shot_name(shot)
    if normalized.lower() != section.clip.lower():
        return [target_for_shot(normalized, section, episode)]

    targets = [target_for_shot(normalized, section, episode)]
    paths = [rel_to_root(raw, episode) for raw in backticked(section.target_line)]
    stems = {Path(target.rel_path).stem for target in targets}
    for path in paths:
        stem = Path(path).stem
        if stem in stems:
            continue
        suffix = declared_target_suffix(section, path)
        frame_shot = f"{section.clip}_{suffix}"
        frame_target = target_for_shot(frame_shot, section, episode)
        stems.add(Path(frame_target.rel_path).stem)
        targets.append(frame_target)
    return targets


def logical_seed(root: Path, episode: str, shot: str, rel_path: str) -> str:
    data = f"{root.name}|{episode}|{shot}|{rel_path}".encode("utf-8")
    return str(1000 + int(hashlib.sha1(data).hexdigest()[:8], 16) % 9000)


def frame_role_note(target: Target) -> str:
    """Human-readable role for first/mid/action/end targets.

    Multi-anchor clips reuse the same prompt section, so the backend needs an
    explicit per-target instruction; otherwise mid/end requests can collapse
    back into a nice-looking duplicate of the first frame.
    """
    stem = Path(target.rel_path).stem
    if target.mode == "firstframe":
        return "本次目标是首帧 firstframe：抓动作起幅/情绪起点，预留运镜余量，不要直接画成动作顶点。"
    if target.mode == "tailframe":
        return "本次目标是尾帧 endframe：表现本 Clip 的动作结果/情绪落点，并作为视频接力帧；必须区别于首帧，构图、人物状态和光位要能承接下一镜。"
    if target.mode == "midframe":
        match = re.search(r"_a(\d+)$", stem)
        if match:
            return f"本次目标是动作关键锚帧 a{match.group(1)}：位于首帧与尾帧之间，抓本 Clip 的明确动作节点；不得重复首帧构图。"
        return "本次目标是中段锚帧 midframe：位于首帧与尾帧之间，表现动作推进半程/关系变化；不得重复首帧构图。"
    return ""


def temp_token(value: str) -> str:
    text = re.sub(r"[^\w.-]+", "_", str(value), flags=re.UNICODE).strip("_")
    return text or "target"


def png_valid(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 32:
        return False
    with path.open("rb") as fh:
        return fh.read(8) == b"\x89PNG\r\n\x1a\n"


def raster_valid(path: Path) -> bool:
    """Return true for existing shared raster references we can safely reuse.

    Generated targets are still required to land as PNG bytes, but user-supplied
    shared references may be JPEG/WebP. Treating only PNG as "existing" causes
    the runner to overwrite legitimate reference images during shared bootstrap.
    """
    if png_valid(path):
        return True
    if not path.is_file() or path.stat().st_size < 12:
        return False
    try:
        with path.open("rb") as fh:
            header = fh.read(12)
    except OSError:
        return False
    return (
        header.startswith(b"\xff\xd8\xff")
        or (header[:4] == b"RIFF" and header[8:12] == b"WEBP")
    )


def png_size(path: Path) -> Optional[tuple[int, int]]:
    if not png_valid(path):
        return None
    try:
        with path.open("rb") as fh:
            header = fh.read(24)
        if len(header) < 24 or header[12:16] != b"IHDR":
            return None
        return struct.unpack(">II", header[16:24])
    except OSError:
        return None


def brief_context(path: Path, limit: int = 1800) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    return text[:limit]


def load_json_file(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _reference_relevant_text(body: str) -> str:
    """Only scan positive reference declarations, not negative/prohibition text."""
    lines: List[str] = []
    in_reference_block = False
    for line in str(body or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("**参考图**") or "参考图入参清单" in stripped:
            in_reference_block = True
            lines.append(line)
            continue
        if in_reference_block and stripped.startswith("**") and "参考图" not in stripped:
            in_reference_block = False
        if in_reference_block:
            lines.append(line)
            continue
        if any(marker in line for marker in ("资产身份注册层", "身份注册层", "身份注册", "成长派生", "资产引用注册层", "生成方式", "常驻主体", "常驻角色", "常驻物件")):
            lines.append(line)
    return "\n".join(lines)


_IMAGE_REFERENCE_TOKEN_RE = re.compile(
    r"`?(?:出图/共享/图片/)?定妆_[^`\s，。；;、)）]+?\.(?:png|jpg|jpeg|webp)`?",
    re.I,
)


def _registry_ref_scan_text(body: str) -> str:
    """Text used for registry ID scans, with makeup image filenames removed.

    A prompt may mention `定妆_CHAR_FOO_脸部特写.png` in the reference block.  The
    direct file-ready gate handles that path; the registry scan must not treat
    the filename stem as a CHAR_* identity id.
    """
    return _IMAGE_REFERENCE_TOKEN_RE.sub(" ", _reference_relevant_text(body))


def _shot_character_refs(body: str) -> Set[str]:
    text = _registry_ref_scan_text(body)
    refs = set(re.findall(r"(?:CHAR|BEAST)_[A-Za-z0-9_]+(?:/[A-Za-z0-9_\u4e00-\u9fff·.-]+)?", text))
    refs |= {m.strip("`") for m in re.findall(r"`((?:CHAR|BEAST)_[^`]+)`", text)}
    return {r.strip("` *，,。；;、)）(") for r in refs if r.strip("` *，,。；;、)）(")}


_ASSET_REF_CONSTRAINT_SUFFIX_RE = re.compile(
    r"^(?:结构|颜色|尺寸|数量|材质|比例|状态|禁漂|漂移|参考|约束|锁定|唯一性|保持|固定|归属|稳定|不变)"
)


def _shot_asset_refs(body: str, known_asset_ids: Iterable[str] = ()) -> Set[str]:
    text = _registry_ref_scan_text(body)
    raw_refs: Set[str] = set()
    for prefix in ("LOC", "PROP", "WEAPON", "OUTFIT", "VFX"):
        raw_refs |= set(re.findall(rf"{prefix}_[A-Za-z0-9_\u4e00-\u9fff]+", text))
    known = sorted(
        {str(item).strip() for item in known_asset_ids if str(item).strip()},
        key=len,
        reverse=True,
    )
    if not known:
        return raw_refs
    refs: Set[str] = set()
    for ref in raw_refs:
        if ref in known:
            refs.add(ref)
            continue
        # Chinese prompt prose often concatenates a stable id and a constraint,
        # e.g. ``PROP_水桶结构/颜色/尺寸漂移``.  The greedy CJK token scan must
        # resolve that phrase back to the registered id rather than inventing a
        # pseudo asset named ``PROP_水桶结构``.
        normalized = next(
            (
                aid for aid in known
                if ref.startswith(aid)
                and _ASSET_REF_CONSTRAINT_SUFFIX_RE.match(ref[len(aid):])
            ),
            "",
        )
        refs.add(normalized or ref)
    return refs


# Asset types whose plate renders a person, so a missing face anchor = a new face.
_IDENTITY_BEARING_ASSET_TYPES = {
    "vfx", "poster", "key_visual", "kv", "relation", "relationship",
    "cover", "群像", "海报", "封面", "关系图",
}
# 固有"画面里就是人脸"的类型（海报/关系图/封面/群像）——必 face_locked。
# vfx 不在此列：纯能量特效(青烟/白气/龙珠)无脸，只有渲染在人身上(有人物上下文)才 face_locked。
_PERSON_SHOWING_ASSET_TYPES = {
    "poster", "key_visual", "kv", "relation", "relationship",
    "cover", "群像", "海报", "封面", "关系图",
}

_CHAR_REF_RE = re.compile(r"(?:CHAR|BEAST)_[A-Za-z0-9_]+(?:/[A-Za-z0-9_一-鿿·.-]+)?")

# Explicit "a person is in frame" signal, used to infer carried identity even when
# the asset's `type` is blank/custom (so it falls outside _IDENTITY_BEARING_ASSET_TYPES).
# Kept narrow: room/prop plates that merely name a character's belonging (e.g.
# "CHAR_01 的寝宫，空镜") have no person keyword and must NOT pull a face in.
_PERSON_CONTEXT_RE = re.compile(
    r"脸|面容|面颊|五官|眉眼|眼底|发|妆|人物|角色|肖像|半身|全身|持|握|站立|端坐|怀抱"
    r"|portrait|face|holds?|holding|standing|seated"
)
# 明确"画面主体就是某角色的脸/立绘"的窄信号（用于 face_policy 推断·不含 scene/effect 描述里顺带提到的"角色/人物"）。
_PORTRAIT_CONTEXT_RE = re.compile(r"脸|面容|面颊|五官|眉眼|肖像|立绘|portrait|headshot|character\s*sheet")

# 人物脸一致性铁律（A·face_policy）：任何**会出现具名角色脸**的资产定妆，必须显式声明脸策略——
#   faceless    人只作尺度尺/握持手/背身剪影，禁止清晰五官（武器握持比例/scale 参考）→ 出图后像素核验 0 清晰脸；
#   face_locked 必须保持承载角色身份（持械动作/VFX 上身/海报/关系图/角色镜）→ 必须折入 owner/承载角色脸锚 + 脸核验。
# 绝不允许"含人脸资产镜自由生成脸"（武器握持比例脸漂的结构性真因）。
_FACELESS_STEM_RE = re.compile(r"握持比例|比例尺|尺度|scale|grip|proportion", re.IGNORECASE)
_FACE_LOCKED_STEM_RE = re.compile(r"动作_持|持械|wielding|wield|半身|全身|脸部特写|45度|_侧|_背|肖像|portrait",
                                  re.IGNORECASE)
FACE_POLICY_CHOICES = ("faceless", "face_locked", "none")
FACE_MOOD_ONLY_POLICIES = {"face_mood_only", "face_only", "identity_mood_only", "mood_only"}


def _form_reference_use_policy(form: Dict[str, Any]) -> str:
    reference_group = form.get("reference_group") if isinstance(form.get("reference_group"), dict) else {}
    reference_atlas = form.get("reference_atlas") if isinstance(form.get("reference_atlas"), dict) else {}
    for value in (
        form.get("reference_use_policy"),
        form.get("reference_policy"),
        reference_group.get("reference_use_policy"),
        reference_atlas.get("reference_use_policy"),
    ):
        text = str(value or "").strip().lower()
        if text:
            return text
    return ""


def _asset_owner_refs(asset: Dict[str, Any]) -> List[str]:
    """asset 的 owner / 承载角色（owner / owner_character / signature_owner）→ CHAR ref 列表。

    owner 此前是脸锚推断的盲区：武器 owner=CHAR_xx 只写在 owner 字段，name/constraints 里没有 → 旧逻辑
    捞不到 → 持械镜不折脸锚 → 后端自画新脸（大荒碎星戟握持镜脸漂真因）。"""
    out: List[str] = []
    for key in ("owner", "owner_character", "signature_owner", "carried_by"):
        v = asset.get(key)
        for item in (v if isinstance(v, list) else [v]):
            text = str(item or "").strip().strip("`")
            if _CHAR_REF_RE.fullmatch(text) and text not in out:
                out.append(text)
    return out


def resolve_face_policy(asset: Dict[str, Any], rel_path: str = "") -> str:
    """资产定妆的脸策略（单一真值源）：faceless | face_locked | none。纯函数·可测。

    显式 asset['face_policy'] 优先；否则按 stem/类型/人物上下文/owner 推断：
      - 比例/scale/握持 stem → faceless（人只作尺度参考·禁清晰脸）。
      - 持械动作/半身/特写/肖像 stem、身份承载类型(vfx/海报/关系图)、或人物上下文 + owner → face_locked。
      - 无人物迹象（纯武器美术/空镜/道具）→ none。"""
    explicit = str(asset.get("face_policy") or "").strip().lower()
    if explicit in FACE_POLICY_CHOICES:
        return explicit
    blob = " ".join([
        str(asset.get("name") or ""), str(asset.get("scope") or ""), rel_path,
        json.dumps(asset.get("constraints") or {}, ensure_ascii=False),
        json.dumps(asset.get("forms") or [], ensure_ascii=False),
        json.dumps(asset.get("reference_group") or {}, ensure_ascii=False),
    ])
    stem = Path(rel_path).stem if rel_path else ""
    if _FACELESS_STEM_RE.search(stem) or _FACELESS_STEM_RE.search(blob):
        return "faceless"
    atype = str(asset.get("type") or "").strip().lower()
    # 显式 carries_identity / subject_characters = 作者声明此图承载某角色脸 → face_locked。
    declared_carry = bool(asset.get("carries_identity") or asset.get("subject_characters"))
    # 固有出脸的类型（海报/关系图/封面/群像）或显式声明承载角色 → face_locked。
    if atype in _PERSON_SHOWING_ASSET_TYPES or declared_carry:
        return "face_locked"
    # VFX/effect 特效图：脸只能靠**显式 carries_identity** 声明（上面已判），不从 effect 描述里顺带的
    # "不遮主角脸""环绕角色"等 incidental 文本误推 face_locked（纯能量特效图本就无脸）→ none。
    if atype in ("vfx", "effect", "特效"):
        return "none"
    # 角色/武器/道具图：持械动作/半身/特写/肖像/45度/侧/背 stem，或画面主体就是脸/立绘的窄上下文 → face_locked。
    # **保守**：只认明确的角色立绘信号，不把 scene/prop 描述里顺带的"角色/人物"当出脸（避免误锁场景）。
    if _FACE_LOCKED_STEM_RE.search(stem) or _FACE_LOCKED_STEM_RE.search(blob) or _PORTRAIT_CONTEXT_RE.search(blob):
        return "face_locked"
    return "none"


def _asset_carried_identities(asset: Dict[str, Any]) -> List[str]:
    """CHAR ids/forms whose locked face this asset depicts and must inherit.

    A 定妆/分镜 asset that renders a character's face (VFX on a body, a poster, a
    relationship plate) is NOT identity-neutral: with no face anchor fed, the
    backend invents a brand-new face and the asset drifts at the 定妆 stage — the
    万妖血脉 VFX plate vs the 沈念 base pack was exactly this failure. The asset's
    own ``reference_group`` only self-references its not-yet-existing output, so
    the face has to come from the carried character.

    ``carries_identity`` / ``subject_characters`` (str or list; bare ``CHAR_xx`` or
    form-qualified ``CHAR_xx/形态``) is authoritative. When absent, fall back to
    inferring CHAR ids from an identity-bearing asset's name/constraints/structure
    text, so a legacy registry degrades safely instead of silently drifting.
    """
    out: List[str] = []
    seen: Set[str] = set()

    def add(value: Any) -> None:
        text = str(value or "").strip().strip("`")
        if _CHAR_REF_RE.fullmatch(text) and text not in seen:
            seen.add(text)
            out.append(text)

    explicit = asset.get("carries_identity")
    if explicit is None:
        explicit = asset.get("subject_characters")
    if isinstance(explicit, str):
        explicit = [explicit]
    for value in explicit or []:
        add(value)
    if out:
        return out

    if _shared_asset_suppresses_character_refs(asset, ""):
        return out

    # owner-aware：face_locked 资产无显式 carries_identity 时，承载角色取 owner（治 owner 盲区脸漂——
    # 大荒碎星戟 owner=CHAR_JIANG_YUECHU 只在 owner 字段，旧逻辑捞不到→持械镜不折脸锚→自画新脸）。
    # faceless / none 资产**不**折脸锚（握持比例镜本就该无清晰脸）。
    if resolve_face_policy(asset) == "face_locked":
        for ref in _asset_owner_refs(asset):
            add(ref)
        if out:
            return out

    blob = " ".join([
        str(asset.get("name") or ""),
        str(asset.get("scope") or ""),
        json.dumps(asset.get("constraints") or {}, ensure_ascii=False),
        json.dumps(asset.get("forms") or [], ensure_ascii=False),
    ])
    if not _CHAR_REF_RE.search(blob):
        return out
    # Fire inference when the type is a known person-bearing kind, OR a character is
    # named alongside explicit person/face context — the latter catches plates whose
    # `type` is blank/custom yet clearly render a face (the type-whitelist hole).
    type_bearing = str(asset.get("type") or "").strip().lower() in _IDENTITY_BEARING_ASSET_TYPES
    if not (type_bearing or _PERSON_CONTEXT_RE.search(blob)):
        return out
    for match in _CHAR_REF_RE.findall(blob):
        add(match)
    return out


def _shared_target_assets_for_policy(assets: Dict[str, Any], target: Target) -> List[Dict[str, Any]]:
    if target.mode != "shared":
        return []
    aliases = {str(item).strip() for item in (getattr(target, "aliases", set()) or set()) if str(item).strip()}
    out: List[Dict[str, Any]] = []
    for asset in assets.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        aid = str(asset.get("id") or "").strip()
        if aid and aid in aliases:
            out.append(asset)
            continue
        if target.rel_path in registry_image_paths(asset):
            out.append(asset)
    return out


def _shared_asset_suppresses_character_refs(asset: Dict[str, Any], rel_path: str) -> bool:
    face_policy = resolve_face_policy(asset, rel_path)
    human_presence = str(asset.get("human_presence") or "").strip().lower()
    return face_policy == "faceless" or human_presence.startswith("no_person")


def _status_ready(node: Dict[str, Any], *, allow_pending_user_reference: bool = False) -> bool:
    # Kept as a keyword for compatibility with older callers, but pending rights
    # are never generation-ready.  External rows additionally pass the strict
    # rights/SHA/watermark policy before reaching `_add_ready_image_path`.
    del allow_pending_user_reference
    status = str(node.get("status") or "").strip().lower()
    return not status or status in {"ready", "registered", "pass", "ok", "accepted"}


def _collect_ready_image_paths(
    node: Any,
    root: Path,
    out: List[str],
    seen: Set[str],
    *,
    allow_non_shared: bool = False,
    allow_pending_user_reference: bool = False,
) -> None:
    lineage_keys = {
        "path",
        "source",
        "source_image",
        "source_refs",
        "source_path",
        "source_sha256",
        "derivation",
        "reference_inputs",
        "generated_by",
        "generated_at",
        "human_review",
        "review_reason",
    }
    if isinstance(node, dict):
        path = node.get("path")
        if isinstance(path, str) and _status_ready(node, allow_pending_user_reference=allow_pending_user_reference):
            _add_ready_image_path(path, root, out, seen, allow_non_shared=allow_non_shared)
        for key, value in node.items():
            if key in lineage_keys:
                continue
            _collect_ready_image_paths(
                value,
                root,
                out,
                seen,
                allow_non_shared=allow_non_shared,
                allow_pending_user_reference=allow_pending_user_reference,
            )
    elif isinstance(node, list):
        for item in node:
            _collect_ready_image_paths(
                item,
                root,
                out,
                seen,
                allow_non_shared=allow_non_shared,
                allow_pending_user_reference=allow_pending_user_reference,
            )
    elif isinstance(node, str):
        _add_ready_image_path(node, root, out, seen, allow_non_shared=allow_non_shared)


def _collect_eligible_external_image_paths(
    node: Any,
    root: Path,
    out: List[str],
    seen: Set[str],
    *,
    allowed_policies: Sequence[str],
) -> None:
    """Collect external inputs only after rights, SHA and watermark approval."""
    if isinstance(node, Mapping):
        if "path" in node:
            result = evaluate_generation_reference(
                root,
                node,
                allowed_policies=allowed_policies,
            )
            rel = str(result.get("path") or "").strip()
            if result.get("eligible") and rel:
                _add_ready_image_path(rel, root, out, seen, allow_non_shared=True)
            return
        for value in node.values():
            _collect_eligible_external_image_paths(
                value,
                root,
                out,
                seen,
                allowed_policies=allowed_policies,
            )
    elif isinstance(node, list):
        for item in node:
            _collect_eligible_external_image_paths(
                item,
                root,
                out,
                seen,
                allowed_policies=allowed_policies,
            )


def _resolve_registry_image_path(root: Path, value: str) -> tuple[str, Path, List[str]]:
    """Resolve a load-bearing registry image without path aliases or escapes."""
    raw = str(value or "").strip()
    if not raw:
        return "", Path(), ["path_missing"]
    if "\x00" in raw:
        return "", Path(), ["path_invalid_nul"]
    if (
        os.path.isabs(raw)
        or (len(raw) >= 3 and raw[1] == ":" and raw[2] in {"/", "\\"})
        or raw.startswith("\\\\")
    ):
        return "", Path(), ["absolute_registry_evidence_path_not_allowed"]
    root_real = root.expanduser().resolve()
    resolved = (root_real / raw).resolve(strict=False)
    try:
        if os.path.commonpath((str(root_real), str(resolved))) != str(root_real):
            return "", Path(), ["registry_evidence_path_outside_project_root"]
        canonical = resolved.relative_to(root_real).as_posix()
    except (ValueError, OSError):
        return "", Path(), ["registry_evidence_path_outside_project_root"]
    if raw.replace("\\", "/") != canonical:
        return canonical, resolved, ["registry_evidence_path_not_canonical_project_relative"]
    return canonical, resolved, []


def _add_ready_image_path(raw: str, root: Path, out: List[str], seen: Set[str], *, allow_non_shared: bool = False) -> None:
    if Path(raw).suffix.lower() not in IMAGE_SUFFIXES:
        return
    rel = raw if str(raw).startswith("出图/") else rel_to_root(str(raw), "共享")
    canonical, resolved, path_errors = _resolve_registry_image_path(root, rel)
    if path_errors:
        return
    if (not allow_non_shared and not is_shared_image_path(canonical)) or canonical in seen:
        return
    # A reference bundle is for actual backend image inputs; planned/missing paths
    # belong in gate findings, not in a generation request.
    if not resolved.is_file():
        return
    seen.add(canonical)
    out.append(canonical)


def _style_anchor_status_ready(value: Any) -> bool:
    status = str(value or "").strip().lower()
    return not status or status in STYLE_ANCHOR_READY_STATUSES


def load_style_anchor_paths(root: Path) -> List[str]:
    """Return project-level style-only anchors from ``style_anchor_registry``.

    The runner needs an image input it can actually pass to Codex.  This sidecar
    lets an operator select a style probe as the temporary style carrier without
    editing the upstream storyboard contract first.
    """
    data = load_json_file(root / STYLE_ANCHOR_REGISTRY)
    if not data:
        return []
    anchors: List[str] = []
    seen: Set[str] = set()

    def add(raw: Any, status: Any = "") -> None:
        text = str(raw or "").strip()
        if not text or Path(text).suffix.lower() not in IMAGE_SUFFIXES:
            return
        if not _style_anchor_status_ready(status):
            return
        rel = text if text.startswith("出图/") else str(Path("出图") / "共享" / "图片" / text)
        canonical, resolved, path_errors = _resolve_registry_image_path(root, rel)
        if path_errors or canonical in seen or not resolved.is_file():
            return
        seen.add(canonical)
        anchors.append(canonical)

    def scan(node: Any) -> None:
        if isinstance(node, dict):
            if "path" in node:
                add(node.get("path"), node.get("status"))
                return
            for value in node.values():
                scan(value)
        elif isinstance(node, list):
            for item in node:
                scan(item)
        elif isinstance(node, str):
            add(node)

    scan(data.get("selected_anchor") or data.get("style_anchor"))
    if anchors:
        return anchors
    scan(data.get("anchors"))
    return anchors


def load_style_source_paths(root: Path) -> List[str]:
    """Raw user style observations, usable only to synthesize the clean style anchor."""
    data = load_json_file(root / STYLE_ANCHOR_REGISTRY)
    if not data:
        return []
    paths: List[str] = []
    seen: Set[str] = set()
    _collect_eligible_external_image_paths(
        data.get("source_style_references"),
        root,
        paths,
        seen,
        allowed_policies=tuple(STYLE_GENERATION_POLICIES),
    )
    return paths


def reference_bundle_for_target(root: Path, episode: str, target: Target) -> Dict[str, Any]:
    """Resolve per-shot character/asset references into a backend-friendly bundle."""
    body = target.section.body
    char_refs = _shot_character_refs(body)
    asset_refs: Set[str] = set()
    if target.mode == "shared":
        for alias in getattr(target, "aliases", set()) or set():
            text = str(alias).strip()
            if re.fullmatch(r"(?:CHAR|BEAST)_[A-Za-z0-9_]+(?:/[A-Za-z0-9_\u4e00-\u9fff·.-]+)?", text):
                char_refs.add(text)
            elif re.fullmatch(r"(?:LOC|PROP|WEAPON|OUTFIT|VFX)_[A-Za-z0-9_\u4e00-\u9fff]+", text):
                asset_refs.add(text)
    identity = load_json_file(root / "出图" / "共享" / "identity_registry.json")
    assets = load_json_file(root / "出图" / "共享" / "asset_registry.json")
    known_asset_ids = {
        str(asset.get("id") or "").strip()
        for asset in assets.get("assets") or []
        if isinstance(asset, dict) and str(asset.get("id") or "").strip()
    }
    asset_refs |= _shot_asset_refs(body, known_asset_ids)
    target_aliases = {str(item).strip() for item in (getattr(target, "aliases", set()) or set())}
    resident_scene_identity = bool(
        target.mode == "shared"
        and char_refs
        and any(value.startswith("LOC_") for value in {str(target.shot or ""), str(target.clip or ""), *target_aliases})
        and any(marker in body for marker in ("常驻主体", "常驻角色", "常驻物件"))
    )
    if target.mode == "shared" and not resident_scene_identity and any(
        _shared_asset_suppresses_character_refs(asset, target.rel_path)
        for asset in _shared_target_assets_for_policy(assets, target)
    ):
        char_refs.clear()
    items: List[Dict[str, Any]] = []
    missing: List[str] = []
    style_anchor_paths = load_style_anchor_paths(root)
    if style_anchor_paths:
        items.append({
            "kind": "style",
            "id": "STYLE_ANCHOR",
            "paths": style_anchor_paths,
            "use_policy": "style_only",
        })
    if target.mode == "shared" and is_style_anchor_path(target.rel_path):
        style_source_paths = load_style_source_paths(root)
        if style_source_paths:
            items.append({
                "kind": "style",
                "id": "STYLE_SOURCE_REFERENCES",
                "paths": style_source_paths,
                "use_policy": "style_source_only_for_clean_anchor_synthesis",
            })
    cross_episode_sources = cross_episode_source_frame_paths(body)
    if cross_episode_sources:
        items.append({
            "kind": "source_frame",
            "id": "CROSS_EPISODE_HANDOFF",
            "paths": cross_episode_sources,
            "use_policy": "cross_episode_geometry_handoff",
        })

    # An asset that depicts a character must inherit that character's locked face
    # anchor; its own reference_group only self-references the not-yet-existing
    # output. Fold the carried identity into char_refs so the character branch
    # below resolves real face anchors — otherwise a full face renders unanchored
    # and drifts at the 定妆 stage.
    carried_identity: List[str] = []
    for asset in assets.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        aid = str(asset.get("id") or "").strip()
        if not aid or aid not in asset_refs:
            continue
        for ref in _asset_carried_identities(asset):
            char_refs.add(ref)
            if ref not in carried_identity:
                carried_identity.append(ref)

    form_refs_by_character: Dict[str, Set[str]] = {}
    bare_character_refs: Set[str] = set()
    for ref in char_refs:
        cid, sep, form_name = str(ref).strip().partition("/")
        if not cid:
            continue
        if sep and form_name:
            form_refs_by_character.setdefault(cid, set()).add(form_name)
        else:
            bare_character_refs.add(cid)

    for ch in identity.get("characters") or []:
        if not isinstance(ch, dict):
            continue
        cid = str(ch.get("id") or "").strip()
        if not cid or (cid not in bare_character_refs and cid not in form_refs_by_character):
            continue
        requested_forms = form_refs_by_character.get(cid)
        for form in ch.get("forms") or []:
            if not isinstance(form, dict):
                continue
            fname = str(form.get("form") or "常态").strip()
            if requested_forms is not None:
                if fname not in requested_forms:
                    continue
            elif cid not in bare_character_refs:
                continue
            paths: List[str] = []
            seen: Set[str] = set()
            reference_policy = _form_reference_use_policy(form)
            if reference_policy in FACE_MOOD_ONLY_POLICIES:
                reference_group = form.get("reference_group") if isinstance(form.get("reference_group"), dict) else {}
                reference_atlas = form.get("reference_atlas") if isinstance(form.get("reference_atlas"), dict) else {}
                for key in CHARACTER_SHARED_FACE_FIELDS:
                    _collect_ready_image_paths(reference_group.get(key), root, paths, seen)
                    _collect_ready_image_paths(reference_atlas.get(key), root, paths, seen)
            else:
                _collect_eligible_external_image_paths(
                    ch.get("external_visual_references"),
                    root,
                    paths,
                    seen,
                    allowed_policies=tuple(IDENTITY_GENERATION_POLICIES),
                )
                _collect_ready_image_paths(form.get("reference_group"), root, paths, seen)
                _collect_ready_image_paths(form.get("reference_atlas"), root, paths, seen)
            if paths:
                items.append({"kind": "character", "id": cid, "form": fname, "paths": paths})
            else:
                missing.append(f"{cid}/{fname}")

    for asset in assets.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        aid = str(asset.get("id") or "").strip()
        if not aid or aid not in asset_refs:
            continue
        paths = []
        seen = set()
        _collect_ready_image_paths(asset.get("reference_group"), root, paths, seen)
        _collect_ready_image_paths(asset.get("reference_atlas"), root, paths, seen)
        if paths:
            items.append({"kind": "asset", "id": aid, "type": asset.get("type") or "", "paths": paths})
        else:
            missing.append(aid)

    return {
        "kind": "n2d_codex_reference_bundle",
        "version": 2,
        "episode": episode,
        "shot": target.shot,
        "target": target.rel_path,
        "backend": "codex",
        "true_image_reference_support": True,
        "reference_input_mode": "codex_exec_image_flags",
        "persistent_subject_support": False,
        "items": items,
        "carried_identity": carried_identity,
        "missing_ready_refs": missing,
    }


def shared_image_ready(root: Path, rel_path: str) -> bool:
    rel = str(rel_path or "").strip()
    canonical, path, path_errors = _resolve_registry_image_path(root, rel)
    if path_errors or not is_shared_image_path(canonical):
        return False
    if not path.is_file():
        return False
    if path.suffix.lower() == ".png":
        return png_valid(path)
    try:
        return path.stat().st_size > 32
    except OSError:
        return False


def _ready_shared_paths_for_node(root: Path, node: Any) -> List[str]:
    paths: List[str] = []
    seen: Set[str] = set()
    _collect_ready_image_paths(node, root, paths, seen)
    return [rel for rel in paths if shared_image_ready(root, rel)]


def _failed_shared_refs_for_node(node: Any, prefix: str = "") -> List[str]:
    failures: List[str] = []
    if isinstance(node, dict):
        status = str(node.get("status") or "").strip().lower()
        path = node.get("path")
        if isinstance(path, str) and status in FAILED_SHARED_REF_STATUSES:
            label = prefix or Path(path).name
            failures.append(f"{label}={status} `{path}`")
        for key, value in node.items():
            if key in {"path", "source", "source_image", "source_refs"}:
                continue
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            failures.extend(_failed_shared_refs_for_node(value, child_prefix))
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            child_prefix = f"{prefix}[{idx}]" if prefix else f"[{idx}]"
            failures.extend(_failed_shared_refs_for_node(value, child_prefix))
    return failures


def _form_is_restricted_partial(form: Dict[str, Any]) -> bool:
    record = dict(form)
    atlas = form.get("reference_atlas") if isinstance(form.get("reference_atlas"), Mapping) else {}
    group = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
    if "library_tier" not in record and atlas.get("build_tier"):
        record["library_tier"] = atlas.get("build_tier")
    if group.get("restricted_partial") is True:
        record["restricted_partial"] = True
    return character_library_tier_for_record(record) == CHARACTER_LIBRARY_TIER_PARTIAL


def _character_forms_for_ref(identity: Dict[str, Any], char_ref: str) -> tuple[List[tuple[str, Dict[str, Any]]], bool]:
    text = str(char_ref or "").strip().strip("`")
    cid, _, requested_form = text.partition("/")
    for ch in identity.get("characters") or []:
        if not isinstance(ch, dict) or str(ch.get("id") or "").strip() != cid:
            continue
        forms = []
        for form in ch.get("forms") or []:
            if not isinstance(form, dict):
                continue
            enriched = dict(form)
            for key in (
                "id", "character_id",
                "scope", "narrative_tier", "library_tier", "tier", "core", "long_line",
                "planned_episode_count", "episode_count", "face_policy",
                "restricted_partial", "restricted_partial_contract",
            ):
                if key not in enriched and key in ch:
                    enriched[key] = ch.get(key)
            atlas = enriched.get("reference_atlas") if isinstance(enriched.get("reference_atlas"), Mapping) else {}
            if "library_tier" not in enriched and atlas.get("build_tier"):
                enriched["library_tier"] = atlas.get("build_tier")
            forms.append(enriched)
        if requested_form:
            matched = [
                (cid, form)
                for form in forms
                if str(form.get("form") or "常态").strip() == requested_form
            ]
            return matched, True
        return [(cid, form) for form in forms], True
    return [], False


def _character_library_tier(form: Mapping[str, Any]) -> str:
    record = dict(form)
    atlas = form.get("reference_atlas") if isinstance(form.get("reference_atlas"), Mapping) else {}
    if "library_tier" not in record and atlas.get("build_tier"):
        record["library_tier"] = atlas.get("build_tier")
    return character_library_tier_for_record(record)


CORE_REVIEW_PASS = {"pass", "passed", "ok", "accepted", "approved", "ready"}


def _core_review_item_path(item: Any) -> str:
    if isinstance(item, Mapping):
        return str(item.get("path") or item.get("ref") or item.get("file") or "").strip()
    return str(item or "").strip()


def _core_review_view_item(form: Mapping[str, Any], view: str) -> Any:
    rg = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
    if view in rg:
        return rg.get(view)
    atlas = form.get("reference_atlas") if isinstance(form.get("reference_atlas"), Mapping) else {}
    base = atlas.get("base_views") if isinstance(atlas.get("base_views"), Mapping) else {}
    return base.get(view)


def _core_expression_review_items(form: Mapping[str, Any]) -> List[Any]:
    rg = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
    atlas = form.get("reference_atlas") if isinstance(form.get("reference_atlas"), Mapping) else {}
    out: List[Any] = []
    for node in (
        rg.get("expressions"), rg.get("face_anchor_refs"),
        atlas.get("expression_refs"), atlas.get("face_anchor_refs"),
    ):
        if isinstance(node, list):
            out.extend(node)
        elif isinstance(node, Mapping) and any(key in node for key in ("path", "ref", "file")):
            out.append(node)
        elif isinstance(node, Mapping):
            out.extend(value for value in node.values() if isinstance(value, (str, Mapping)))
        elif isinstance(node, str):
            out.append(node)
    return out


def core_review_binding_fingerprint(
    character_id: str,
    form_name: str,
    library_tier: str,
    view: str,
    path: str,
    png_sha256: str,
) -> str:
    """Canonical binding shared with image_qc's per-view receipt contract."""
    return identity_review_binding_fingerprint(
        character_id=character_id,
        form=form_name,
        library_tier=library_tier,
        view=view,
        path=path,
        png_sha256=png_sha256,
    )


def _core_review_png_valid(path: Path) -> bool:
    """Spending-side current-pixel check; fail closed when Pillow is absent."""
    if Image is None or not path.is_file():
        return False
    try:
        with Image.open(path) as opened:
            if opened.format != "PNG" or min(opened.size) < 512:
                return False
            opened.verify()
        with Image.open(path) as decoded:
            decoded.load()
        return True
    except Exception:
        return False


def _executor_visual_review_authorized(root: Path) -> bool:
    path = root / "_设置.md"
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return (
        "执行者实际像素目视" in text
        and ("用户明确" in text or "source=explicit_user" in text)
    )


def _core_review_receipt_valid(
    root: Path,
    item: Any,
    *,
    character_id: str,
    form_name: str,
    view: str,
) -> bool:
    if not isinstance(item, Mapping):
        return False
    raw_rel = _core_review_item_path(item)
    rel, path, path_errors = _resolve_registry_image_path(root, raw_rel)
    if path_errors:
        return False
    sha = optional_file_sha256(path) if rel else ""
    candidates: List[tuple[int, str, Mapping[str, Any]]] = []
    for fallback_kind, key in (("human", "human_review"), ("executor_visual", "visual_review")):
        candidate = item.get(key) if isinstance(item.get(key), Mapping) else {}
        if not candidate:
            continue
        candidate_sha = str(
            candidate.get("png_sha256") or candidate.get("artifact_sha256") or candidate.get("sha256") or ""
        ).strip().lower()
        score = 0
        if sha and candidate_sha == sha.lower():
            score += 8
        if str(candidate.get("verdict") or candidate.get("status") or "").strip().lower() in CORE_REVIEW_PASS:
            score += 4
        if str(candidate.get("reviewer") or candidate.get("reviewed_by") or "").strip():
            score += 2
        if fallback_kind == "human":
            score += 1
        candidates.append((score, fallback_kind, candidate))
    if candidates:
        _score, fallback_review_kind, review = max(candidates, key=lambda row: row[0])
    else:
        fallback_review_kind, review = "", {}
    review_kind = str(review.get("review_kind") or fallback_review_kind).strip().lower()
    verdict = str(review.get("verdict") or review.get("status") or "").strip().lower()
    reviewer = str(review.get("reviewer") or review.get("reviewed_by") or "").strip()
    reviewed_at = str(review.get("reviewed_at") or review.get("timestamp") or "").strip()
    criteria = {str(value) for value in (review.get("criteria") or []) if str(value)}
    confirmation = review.get("confirmation") if isinstance(review.get("confirmation"), Mapping) else {}
    expected = core_review_binding_fingerprint(
        character_id,
        form_name,
        "core_full",
        view,
        rel,
        sha,
    ) if rel and sha else ""
    return bool(
        str(item.get("status") or "").strip().lower() in {"ready", "registered"}
        and _core_review_png_valid(path)
        and verdict in CORE_REVIEW_PASS
        and str(review.get("status") or "").strip().lower() == "accepted"
        and reviewer
        and review_kind in {"human", "executor_visual"}
        and (
            (review_kind == "human" and not identity_reviewer_appears_automated(reviewer))
            or (
                review_kind == "executor_visual"
                and str(review.get("reviewer_role") or "") == "ai_visual_executor"
                and review.get("human_signoff") is False
                and _executor_visual_review_authorized(root)
            )
        )
        and not identity_reviewed_at_errors(reviewed_at)
        and str(review.get("character_id") or "") == character_id
        and str(review.get("form") or "") == form_name
        and str(review.get("library_tier") or "") == "core_full"
        and str(review.get("view") or "") == view
        and str(review.get("path") or "") == rel
        and str(review.get("review_contract") or "") == identity_review_contract_for_view(view)
        and str(review.get("registry_binding_fingerprint_kind") or "")
        == IDENTITY_REVIEW_BINDING_FINGERPRINT_KIND
        and set(identity_review_required_criteria(view)).issubset(criteria)
        and confirmation.get("kind") == "explicit_current_pixels_acceptance"
        and confirmation.get("accepted_current_pixels") is True
        and str(review.get("png_sha256") or review.get("artifact_sha256") or review.get("sha256") or "").strip().lower() == sha.lower()
        and expected
        and str(review.get("registry_binding_fingerprint") or "").strip().lower() == expected
    )


def _core_review_receipt_issues(root: Path, character_id: str, form: Mapping[str, Any]) -> List[str]:
    """Independent spending-side validation of core current-hash receipts."""
    if _character_library_tier(form) != "core_full":
        return []
    form_name = str(form.get("form") or "常态").strip()
    missing: List[str] = []
    evidence_entries: List[tuple[str, Any]] = [
        (view, _core_review_view_item(form, view)) for view in CHARACTER_SHARED_CORE_FIELDS
    ]
    evidence_entries.extend(("expression", item) for item in _core_expression_review_items(form))
    realpath_groups: Dict[str, Set[str]] = {}
    sha_groups: Dict[str, Set[str]] = {}
    for evidence_view, evidence_item in evidence_entries:
        raw_rel = _core_review_item_path(evidence_item)
        if not raw_rel:
            continue
        _rel, resolved, path_errors = _resolve_registry_image_path(root, raw_rel)
        if path_errors:
            missing.append(f"path_safety:{evidence_view}:{'/'.join(path_errors)}")
            continue
        realpath_groups.setdefault(str(resolved), set()).add(evidence_view)
        current_sha = optional_file_sha256(resolved) if resolved.is_file() else ""
        if current_sha:
            sha_groups.setdefault(current_sha, set()).add(evidence_view)
    for views in realpath_groups.values():
        if len(views) > 1:
            missing.append("duplicate_canonical_realpath:" + "/".join(sorted(views)))
    for views in sha_groups.values():
        if len(views) > 1:
            missing.append("duplicate_png_sha:" + "/".join(sorted(views)))
    for view in CHARACTER_SHARED_CORE_FIELDS:
        if not _core_review_receipt_valid(
            root,
            _core_review_view_item(form, view),
            character_id=character_id,
            form_name=form_name,
            view=view,
        ):
            missing.append(view)
    expression_ok = any(
        _core_review_receipt_valid(
            root,
            item,
            character_id=character_id,
            form_name=form_name,
            view="expression",
        )
        for item in _core_expression_review_items(form)
    )
    if not expression_ok:
        missing.append("expression")
    return missing


def _character_required_fields_for_shot(form: Mapping[str, Any], shot_text: str = "") -> Tuple[str, ...]:
    tier = _character_library_tier(form)
    if tier == "core_full":
        required = list(CHARACTER_SHARED_CORE_FIELDS)
    elif tier == "recurring_standard":
        required = list(CHARACTER_SHARED_STANDARD_FIELDS)
    elif tier == "named_minimal":
        required = list(CHARACTER_SHARED_MINIMAL_FIELDS)
    else:
        return ()
    text = str(shot_text or "")
    if tier == "named_minimal" and re.search(r"CU|MCU|ECU|近景|特写|反打|过肩|转头|回头|打斗|动作|挥|劈|斩|刺", text, re.I):
        required.append("three_quarter")
    if re.search(r"侧面|侧脸|全侧|profile|side view", text, re.I):
        required.append("side")
    if re.search(r"后\s*(?:3/4|45|四分之三)|后侧45|侧背|rear[- ]?(?:three[- ]?quarter|3/4|45)", text, re.I):
        required.append("rear_three_quarter")
    elif re.search(r"背面|背影|背身|背对|back view|rear view", text, re.I):
        required.append("back")
    return tuple(dict.fromkeys(required))


def _character_basic_pack_issues(
    root: Path,
    char_ref: str,
    form: Dict[str, Any],
    shot_text: str = "",
) -> List[str]:
    if _form_is_restricted_partial(form):
        return []
    form_name = str(form.get("form") or "常态").strip()
    library_tier = _character_library_tier(form)
    issues: List[str] = []
    if form.get("self_check_passed") is False:
        return [f"{char_ref}/{form_name}: 共享定妆 self_check_passed=false，先复核/重出共享库"]
    if library_tier == "core_full" and form.get("self_check_passed") is not True:
        issues.append(
            f"{char_ref}/{form_name}: core_full 共享定妆尚未 finalize；必须五角 + turnaround + "
            "至少一张 expression/face anchor 逐图签当前 hash 收据，禁止生成 Clip 分镜图"
        )
    reference_group = form.get("reference_group")
    if not isinstance(reference_group, dict):
        issues.append(f"{char_ref}/{form_name}: reference_group 缺失，不能进入 Clip 分镜图生成")
        return issues

    missing: List[str] = []
    for key in _character_required_fields_for_shot(form, shot_text):
        if not _ready_shared_paths_for_node(root, reference_group.get(key)):
            missing.append(key)
    if not any(_ready_shared_paths_for_node(root, reference_group.get(key)) for key in CHARACTER_SHARED_BODY_FIELDS):
        missing.append("half_body_or_full_body")
    if not any(_ready_shared_paths_for_node(root, reference_group.get(key)) for key in CHARACTER_SHARED_FACE_FIELDS):
        missing.append("face_anchor_or_expression")
    if library_tier == "core_full":
        receipt_issues = _core_review_receipt_issues(root, char_ref, form)
        if receipt_issues:
            missing.append("current_hash_review_receipts:" + "/".join(receipt_issues))
    if missing:
        issues.append(
            f"{char_ref}/{form_name}: 共享定妆分档基础包未齐（library_tier={library_tier}，缺 {', '.join(missing)}），"
            "先补共享库并过自检，禁止生成 Clip 分镜图"
        )
    return issues


def _asset_for_ref(assets: Dict[str, Any], asset_ref: str) -> Optional[Dict[str, Any]]:
    for asset in assets.get("assets") or []:
        if isinstance(asset, dict) and str(asset.get("id") or "").strip() == asset_ref:
            return asset
    return None


def _asset_basic_pack_issues(root: Path, asset_ref: str, asset: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    paths = _ready_shared_paths_for_node(root, asset.get("reference_group"))
    paths.extend(_ready_shared_paths_for_node(root, asset.get("reference_atlas")))
    if not paths:
        issues.append(f"{asset_ref}: 共享资产缺 ready 参考图，禁止生成 Clip 分镜图")
    failed_refs = _failed_shared_refs_for_node(asset.get("reference_group"), "reference_group")
    failed_refs.extend(_failed_shared_refs_for_node(asset.get("reference_atlas"), "reference_atlas"))
    if failed_refs:
        issues.append(f"{asset_ref}: 共享资产存在复核失败参考图（{'; '.join(failed_refs)}），先重出共享库")
    if asset.get("self_check_passed") is False:
        issues.append(f"{asset_ref}: 共享资产 self_check_passed=false，先复核/重出共享库")
    if not isinstance(asset.get("constraints"), dict) or not asset.get("constraints"):
        issues.append(f"{asset_ref}: 共享资产缺 constraints/禁漂约束，先补共享库")
    atype = str(asset.get("type") or "").strip().lower()
    if (asset_ref.startswith("WEAPON_") or atype in {"weapon", "武器"}) and not isinstance(asset.get("weapon_profile"), dict):
        issues.append(f"{asset_ref}: 核心武器缺 weapon_profile，先补共享库")
    return issues


def shared_first_interlock_issues(root: Path, episode: str, targets: Optional[Sequence[Target]] = None) -> List[str]:
    """Shared-first lock before Clip spending.

    By default this scans the whole episode prompt pack.  A P0 vertical slice
    may generate shared assets or dry-run job packs, but it must not spend on
    any ``Clip_*`` PNG until the episode's referenced shared library is complete
    enough to pass as real image inputs.  When a caller passes explicit shot
    targets for a selective redraw, scope the lock to those sections so unrelated
    future/missing shared assets do not block a local repair.
    """
    try:
        if targets:
            sections = []
            seen_clips: Set[str] = set()
            for target in targets:
                if getattr(target, "mode", "") == "shared":
                    continue
                section = getattr(target, "section", None)
                clip = getattr(section, "clip", "")
                if section and clip not in seen_clips:
                    seen_clips.add(clip)
                    sections.append(section)
            if not sections:
                sections = load_sections(root, episode)
        else:
            sections = load_sections(root, episode)
    except Exception as exc:
        return [f"{episode}: 无法读取本集分镜 prompt，不能确认共享库先行顺序：{type(exc).__name__}: {exc}"]

    identity = load_json_file(root / "出图" / "共享" / "identity_registry.json")
    assets = load_json_file(root / "出图" / "共享" / "asset_registry.json")
    known_asset_ids = {
        str(asset.get("id") or "").strip()
        for asset in assets.get("assets") or []
        if isinstance(asset, dict) and str(asset.get("id") or "").strip()
    }
    issues: List[str] = []
    seen: Set[str] = set()

    def add_issue(message: str) -> None:
        if message not in seen:
            seen.add(message)
            issues.append(message)

    if not load_style_anchor_paths(root):
        add_issue(f"{episode}: 缺 ready 风格锚（{STYLE_ANCHOR_REGISTRY} selected_anchor.path 指向的 PNG 不存在或未 ready），先生成/签收共享风格锚，禁止生成 Clip 分镜图")

    for section in sections:
        try:
            target = target_for_shot(section.clip, section, episode)
        except Exception:
            target = Target(
                shot=section.clip,
                clip=section.clip,
                mode="firstframe",
                rel_path=str(Path("出图") / episode / "图片" / f"{section.clip}.png"),
                section=section,
            )
        bundle = reference_bundle_for_target(root, episode, target)
        for missing in bundle.get("missing_ready_refs") or []:
            add_issue(f"{section.clip}: {missing} 缺 ready 共享参考图，先补共享库，禁止生成 Clip 分镜图")

        for char_ref in sorted(_shot_character_refs(section.body)):
            forms, character_known = _character_forms_for_ref(identity, char_ref)
            if not character_known:
                add_issue(f"{section.clip}: {char_ref} 未登记到 identity_registry.json，先补共享库")
                continue
            if not forms:
                add_issue(f"{section.clip}: {char_ref} 未找到对应形态，先补 identity_registry.json")
                continue
            for cid, form in forms:
                for issue in _character_basic_pack_issues(root, cid, form, section.body):
                    add_issue(f"{section.clip}: {issue}")

        for asset_ref in sorted(_shot_asset_refs(section.body, known_asset_ids)):
            asset = _asset_for_ref(assets, asset_ref)
            if not asset:
                add_issue(f"{section.clip}: {asset_ref} 未登记到 asset_registry.json，先补共享库")
                continue
            for issue in _asset_basic_pack_issues(root, asset_ref, asset):
                add_issue(f"{section.clip}: {issue}")

        for rel in shared_image_paths_from_text(section.body):
            if not shared_image_ready(root, rel):
                add_issue(f"{section.clip}: 直接引用的共享图 `{rel}` 不存在或未 ready，先补共享库")

    return issues


def enforce_shared_first_interlock(root: Path, episode: str, targets: Optional[Sequence[Target]] = None) -> bool:
    issues = shared_first_interlock_issues(root, episode, targets=targets)
    if not issues:
        return True
    scope = "本次请求镜头" if targets else "本集"
    print(f"[gate] shared-first interlock blocked — 先生成完并复核{scope}依赖的共享库，再生成 Clip 分镜图；--skip-preflight 不能跳过这条顺序锁。", file=sys.stderr)
    for issue in issues[:30]:
        print(f"[gate] - {issue}", file=sys.stderr)
    if len(issues) > 30:
        print(f"[gate] - ... plus {len(issues) - 30} more shared-first issues", file=sys.stderr)
    return False


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def optional_file_sha256(path: Path) -> str:
    try:
        return file_sha256(path) if path.is_file() else ""
    except Exception:
        return ""


def sha256_text(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


def _rel_from_root(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def _open_image_size(path: Path) -> Optional[tuple[int, int]]:
    if Image is None:
        return None
    try:
        with Image.open(path) as img:
            return img.size
    except Exception:
        return None


def _reference_enhanced_path(root: Path, episode: str, rel_path: str, source_sha: str, width: int, height: int, out_w: int, out_h: int) -> Path:
    stem = temp_token(Path(rel_path).stem)
    name = f"{stem}__{source_sha[:12]}_{width}x{height}_to_{out_w}x{out_h}.png"
    return root / "生产数据" / "reference_enhanced" / episode / name


def _enhance_reference_image(src: Path, dst: Path, size: tuple[int, int]) -> None:
    if Image is None or ImageOps is None:
        raise RuntimeError("Pillow unavailable")
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as opened:
        img = ImageOps.exif_transpose(opened).convert("RGB")
    if img.size != size:
        img = img.resize(size, Image.Resampling.LANCZOS)
    if ImageFilter is not None:
        img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=120, threshold=3))
    img.save(dst, format="PNG", optimize=True)


def prepare_reference_inputs(
    root: Path,
    episode: str,
    inputs: Sequence[Dict[str, Any]],
    *,
    write: bool = True,
) -> List[Dict[str, Any]]:
    """Upscale low-resolution visual references before passing them to Codex.

    The original registry path stays in ``rel_path`` for identity gates.  The
    actual ``codex exec --image`` attachment switches to ``prepared_abs_path``
    when a deterministic enhanced copy is available.
    """
    prepared: List[Dict[str, Any]] = []
    for item in inputs:
        out = dict(item)
        abs_text = str(out.get("abs_path") or "").strip()
        src = Path(abs_text) if abs_text else Path()
        quality: Dict[str, Any] = {
            "policy": "low_res_reference_enhancement",
            "enabled": REFERENCE_ENHANCE_ENABLED,
            "min_short_edge": REFERENCE_ENHANCE_MIN_SHORT_EDGE,
            "max_long_edge": REFERENCE_ENHANCE_MAX_LONG_EDGE,
            "enhanced": False,
        }
        if not REFERENCE_ENHANCE_ENABLED:
            quality["status"] = "disabled"
            out["reference_quality"] = quality
            prepared.append(out)
            continue
        if Image is None:
            quality["status"] = "pillow_unavailable"
            out["reference_quality"] = quality
            prepared.append(out)
            continue
        if not src.is_file():
            quality["status"] = "missing"
            out["reference_quality"] = quality
            prepared.append(out)
            continue

        size = _open_image_size(src)
        if not size:
            quality["status"] = "unreadable_raster"
            out["reference_quality"] = quality
            prepared.append(out)
            continue
        width, height = size
        short_edge = min(width, height)
        long_edge = max(width, height)
        quality.update({
            "original_width": width,
            "original_height": height,
            "original_short_edge": short_edge,
            "original_long_edge": long_edge,
        })
        if short_edge >= REFERENCE_ENHANCE_MIN_SHORT_EDGE:
            quality["status"] = "source_resolution_ok"
            out["reference_quality"] = quality
            prepared.append(out)
            continue

        scale = REFERENCE_ENHANCE_MIN_SHORT_EDGE / max(1, short_edge)
        if long_edge * scale > REFERENCE_ENHANCE_MAX_LONG_EDGE:
            scale = REFERENCE_ENHANCE_MAX_LONG_EDGE / max(1, long_edge)
        scale = max(1.0, scale)
        out_w = max(1, round(width * scale))
        out_h = max(1, round(height * scale))
        quality.update({
            "target_width": out_w,
            "target_height": out_h,
            "method": "lanczos_upscale_unsharp_mask",
        })
        if (out_w, out_h) == (width, height):
            quality["status"] = "max_long_edge_prevented_upscale"
            out["reference_quality"] = quality
            prepared.append(out)
            continue

        source_sha = str(out.get("sha256") or "").strip() or file_sha256(src)
        dst = _reference_enhanced_path(root, episode, str(out.get("rel_path") or src.name), source_sha, width, height, out_w, out_h)
        try:
            if write and not dst.is_file():
                _enhance_reference_image(src, dst, (out_w, out_h))
            if write and dst.is_file():
                out["source_abs_path"] = str(src)
                out["prepared_abs_path"] = str(dst)
                out["prepared_rel_path"] = _rel_from_root(root, dst)
                out["prepared_sha256"] = file_sha256(dst)
                out["prepared_bytes"] = dst.stat().st_size
                quality.update({
                    "status": "enhanced",
                    "enhanced": True,
                    "prepared_width": out_w,
                    "prepared_height": out_h,
                })
            else:
                quality["status"] = "would_enhance"
        except Exception as exc:
            quality["status"] = "enhance_failed"
            quality["error"] = str(exc)[:200]
        out["reference_quality"] = quality
        prepared.append(out)
    return prepared


def reference_input_attachment_path(item: Dict[str, Any]) -> str:
    return str(item.get("prepared_abs_path") or item.get("abs_path") or "").strip()


def reference_input_actual_path(item: Dict[str, Any]) -> str:
    return str(item.get("prepared_rel_path") or item.get("rel_path") or item.get("abs_path") or "").strip()


def selected_relay_source_path(reference_inputs: Sequence[Mapping[str, Any]]) -> str:
    """Return the logical source-frame path actually selected for submission."""
    for item in reference_inputs:
        if str(item.get("role") or "") == "source_frame":
            return str(item.get("rel_path") or "").strip()
    return ""


def codex_backend_version() -> str:
    try:
        proc = subprocess.run(
            ["codex", "--version"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5,
        )
        version = (proc.stdout or proc.stderr or "").strip().splitlines()[0]
        return version or "codex-cli unknown"
    except Exception:
        return "codex-cli unknown"


def reference_bundle_hash(reference_manifest: Optional[Path], reference_inputs: Sequence[Dict[str, Any]]) -> str:
    if reference_manifest and reference_manifest.is_file():
        return file_sha256(reference_manifest)
    payload = json.dumps(list(reference_inputs or []), ensure_ascii=False, sort_keys=True, default=str)
    return sha256_text(payload)


def codex_reference_inputs_for_target(
    root: Path,
    episode: str,
    target: Target,
    bundle: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Materialize the auditable image attachments passed to ``codex exec``."""
    inputs: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    seq = 0

    def priority_for(rel_path: str, role: str) -> int:
        stem = Path(rel_path).stem
        if role == "source_frame":
            return 0
        if role == "character":
            if "脸部特写" in stem or "face" in stem.lower():
                return 10
            if "半身" in stem or "全身" in stem or "outfit" in stem.lower():
                return 20
            if not any(token in stem for token in ("45度", "三视图", "_侧", "_背", "侧", "背")):
                return 30
            if "45度" in stem or "_侧" in stem or stem.endswith("侧"):
                return 40
            if "三视图" in stem:
                return 45
            if "_背" in stem or stem.endswith("背"):
                return 50
            return 55
        if role == "style":
            return 60
        if role == "asset":
            if stem.startswith("PROP_"):
                return 70
            if stem.startswith("LOC_"):
                return 80
            if stem.startswith("VFX_"):
                return 90
            return 100
        if "脸部特写" in stem:
            return 110
        if "半身" in stem or "全身" in stem:
            return 120
        if not any(token in stem for token in ("45度", "三视图", "_侧", "_背", "侧", "背")):
            return 130
        if "45度" in stem or "_侧" in stem or stem.endswith("侧"):
            return 140
        if "三视图" in stem:
            return 150
        if "_背" in stem or stem.endswith("背"):
            return 160
        return 170

    def add(rel: str, *, role: str, owner: str, source: str) -> None:
        nonlocal seq
        text = str(rel or "").strip()
        if not text or Path(text).suffix.lower() not in IMAGE_SUFFIXES:
            return
        rel_path = text if text.startswith("出图/") else rel_to_root(text, episode)
        if rel_path == target.rel_path:
            return
        path = root / rel_path
        if not path.is_file():
            return
        if rel_path in seen:
            if role == "character":
                for item in inputs:
                    if item.get("rel_path") == rel_path and item.get("role") == "style":
                        item["role"] = "character"
                        item["owner"] = owner
                        item["source"] = source
                        item["priority"] = priority_for(rel_path, "character")
                        item["upgraded_from_style_anchor"] = True
                        break
            return
        seen.add(rel_path)
        try:
            size = path.stat().st_size
            sha = file_sha256(path)
        except OSError:
            return
        inputs.append({
            "role": role,
            "owner": owner,
            "source": source,
            "rel_path": rel_path,
            "abs_path": str(path),
            "sha256": sha,
            "bytes": size,
            "priority": priority_for(rel_path, role),
            "sequence": seq,
        })
        seq += 1

    def add_explicit_source_frames() -> None:
        clips: List[str] = []
        seen_clips: Set[str] = set()
        source_lines = [
            line
            for line in target.section.body.splitlines()
            if re.search(r"(母图|同源成图|上一帧|上一张|成图|image2image|image-to-image)", line, re.I)
        ]
        for line in source_lines:
            for match in re.finditer(r"Clip[_\s-]*([0-9０-９]{1,3})", line, re.I):
                raw = match.group(1).translate(str.maketrans("０１２３４５６７８９", "0123456789"))
                clip = f"Clip_{int(raw):02d}"
                if clip == target.clip or clip in seen_clips:
                    continue
                seen_clips.add(clip)
                clips.append(clip)
        if not clips:
            return
        try:
            sections = load_sections(root, episode)
        except Exception:
            return
        for clip in clips:
            try:
                source_section = section_for(sections, clip)
                source_target = target_for_shot(clip, source_section, episode)
                add(source_target.rel_path, role="source_frame", owner=clip, source="explicit_source_clip")
            except Exception:
                continue

    add_explicit_source_frames()

    if target.mode == "shared":
        prop_parent = shared_prop_variant_parent(target.rel_path)
        if prop_parent:
            add(prop_parent, role="asset", owner=target.shot, source="same_prop_primary_parent")

    if target.mode == "shared" and requires_controlled_makeup_derivation(target.rel_path):
        for rel in controlled_makeup_parent_candidates(target.rel_path):
            add(rel, role="source_frame", owner=target.shot, source="same_source_makeup_parent")

    if target.mode not in {"firstframe", "shared"}:
        try:
            source_target = target_for_shot(target.clip, target.section, episode)
            add(source_target.rel_path, role="source_frame", owner=target.clip, source="same_clip_firstframe")
        except Exception:
            pass
        declared_paths = [rel_to_root(raw, episode) for raw in backticked(target.section.target_line)]
        if target.mode == "midframe" and target.rel_path in declared_paths:
            target_index = declared_paths.index(target.rel_path)
            if target_index > 0:
                add(
                    declared_paths[target_index - 1],
                    role="source_frame",
                    owner=target.clip,
                    source="same_clip_previous_frame",
                )
        if target.mode == "tailframe":
            for rel in declared_paths:
                stem = Path(rel).stem
                if rel == target.rel_path:
                    continue
                if declared_target_mode(target.section, rel, declared_paths[0] if declared_paths else "") == "midframe":
                    add(rel, role="source_frame", owner=target.clip, source="same_clip_anchor")

    for item in bundle.get("items") or []:
        if not isinstance(item, dict):
            continue
        owner = str(item.get("id") or "")
        form = str(item.get("form") or "")
        if form:
            owner = f"{owner}/{form}" if owner else form
        for rel in item.get("paths") or []:
            add(str(rel), role=str(item.get("kind") or "reference"), owner=owner, source="reference_bundle")

    def sort_int(item: Dict[str, Any], key: str, default: int) -> int:
        value = item.get(key)
        if value is None or value == "":
            return default
        return int(value)

    inputs.sort(key=lambda item: (sort_int(item, "priority", 999), sort_int(item, "sequence", 0)))
    # A turnaround generated from an already approved character front does not
    # benefit from uploading every redundant crop plus the original style
    # anchor.  The full-body front already carries the approved outfit/style;
    # the tight face anchor supplies high-frequency identity detail.  Keeping
    # exactly those two inputs reduces edit payload size and conflicting pose
    # signals while retaining both body and face truth.  Older projects without
    # a tight face anchor keep the general reference-budget path below.
    target_stem = Path(target.rel_path).stem
    if target.mode == "shared" and target_stem.endswith("_三视图"):
        base_stem = target_stem.removesuffix("_三视图")
        exact_front = next((
            item for item in inputs
            if item.get("role") in {"character", "source_frame"}
            and Path(str(item.get("rel_path") or "")).stem == base_stem
        ), None)
        face_anchor = next((
            item for item in inputs
            if item.get("role") == "character"
            and any(token in Path(str(item.get("rel_path") or "")).stem.lower()
                    for token in ("脸部特写", "face_anchor", "face"))
        ), None)
        if exact_front is not None and face_anchor is not None:
            return [exact_front, face_anchor]
    pruned: List[Dict[str, Any]] = []
    character_counts: Dict[str, int] = {}
    for item in inputs:
        if item.get("role") == "character":
            owner = str(item.get("owner") or item.get("rel_path") or "character")
            count = character_counts.get(owner, 0)
            if count >= MAX_CODEX_CHARACTER_REFERENCES_PER_OWNER:
                continue
            character_counts[owner] = count + 1
        pruned.append(item)
    return select_codex_reference_inputs(target, pruned, MAX_CODEX_REFERENCE_IMAGES)


def select_codex_reference_inputs(
    target: Target,
    inputs: Sequence[Dict[str, Any]],
    limit: int = MAX_CODEX_REFERENCE_IMAGES,
) -> List[Dict[str, Any]]:
    """Fit references to the built-in image generator's hard attachment cap.

    Episode frames reserve context capacity instead of letting one character's
    angle pack consume every slot. Selection is deterministic: source frame,
    balanced character identities, then location/plot asset/style context.
    Shared catalog derivations keep their existing source-priority order.
    """
    rows = list(inputs)
    if limit <= 0:
        return []
    if len(rows) <= limit or target.mode == "shared":
        return rows[:limit]

    source_rows = [row for row in rows if row.get("role") == "source_frame"]

    def source_rank(row: Mapping[str, Any]) -> tuple[int, int]:
        """Prefer the nearest already-approved relay frame under a tight cap.

        Multi-anchor clips used to attach the clip firstframe before the
        immediately preceding anchor.  Because the built-in backend only accepts
        a small reference set, the previous anchor was then truncated and an a2
        redraw silently restarted from the firstframe.  That breaks pose, hair,
        prop-state and VFX continuity even though the full reference manifest is
        technically correct.
        """
        source = str(row.get("source") or "")
        if target.mode == "midframe":
            order = {
                "same_clip_previous_frame": 0,
                "same_clip_firstframe": 1,
                "explicit_source_clip": 2,
            }
        elif target.mode == "tailframe":
            order = {
                "same_clip_anchor": 0,
                "same_clip_firstframe": 1,
                "explicit_source_clip": 2,
            }
        else:
            order = {"explicit_source_clip": 0}
        sequence = int(row.get("sequence") or 0)
        if target.mode == "tailframe" and source == "same_clip_anchor":
            sequence = -sequence
        return (order.get(source, 9), sequence)

    sources = sorted(source_rows, key=source_rank)[:1]
    discarded_source_ids = {id(row) for row in source_rows if row not in sources}
    characters: Dict[str, List[Dict[str, Any]]] = {}
    contexts: List[Dict[str, Any]] = []
    for row in rows:
        if row in sources:
            continue
        if id(row) in discarded_source_ids:
            continue
        if row.get("role") == "character":
            owner = str(row.get("owner") or row.get("rel_path") or "character")
            characters.setdefault(owner, []).append(row)
        else:
            contexts.append(row)

    def context_rank(row: Mapping[str, Any]) -> tuple[int, int, int]:
        owner = str(row.get("owner") or "")
        role = str(row.get("role") or "")
        if owner.startswith("LOC_"):
            kind = 0
        elif owner.startswith(("PROP_", "WEAPON_", "VFX_")) or role == "asset":
            kind = 1
        elif role == "style":
            kind = 2
        else:
            kind = 3
        return (kind, int(row.get("priority") or 999), int(row.get("sequence") or 0))

    contexts.sort(key=context_rank)
    owner_count = len(characters)
    context_reserve = 0
    if contexts:
        body = str(getattr(target.section, "body", "") or "")
        has_interacted_asset = any(
            str(row.get("owner") or "").startswith(("PROP_", "WEAPON_", "VFX_"))
            and str(row.get("owner") or "") in body
            for row in contexts
        )
        context_reserve = 2 if (owner_count <= 1 and not sources) or has_interacted_asset else 1
        context_reserve = min(context_reserve, len(contexts), max(0, limit - len(sources)))
    character_budget = max(0, limit - len(sources) - context_reserve)

    context_groups: Dict[str, List[Dict[str, Any]]] = {}
    for row in contexts:
        owner = str(row.get("owner") or row.get("rel_path") or "context")
        context_groups.setdefault(owner, []).append(row)
    selected_contexts: List[Dict[str, Any]] = []
    context_depth = 0
    context_owners = list(context_groups)
    while len(selected_contexts) < context_reserve:
        added = False
        for owner in context_owners:
            group = context_groups[owner]
            if context_depth < len(group):
                selected_contexts.append(group[context_depth])
                added = True
                if len(selected_contexts) >= context_reserve:
                    break
        if not added:
            break
        context_depth += 1

    selected_chars: List[Dict[str, Any]] = []
    depth = 0
    owners = list(characters)
    while len(selected_chars) < character_budget:
        added = False
        for owner in owners:
            group = characters[owner]
            if depth < len(group):
                selected_chars.append(group[depth])
                added = True
                if len(selected_chars) >= character_budget:
                    break
        if not added:
            break
        depth += 1

    selected = [*sources, *selected_chars, *selected_contexts]
    selected_ids = {id(row) for row in selected}
    for row in rows:
        if len(selected) >= limit:
            break
        if id(row) not in selected_ids and id(row) not in discarded_source_ids:
            selected.append(row)
            selected_ids.add(id(row))
    return selected[:limit]


def bundle_identity_face_paths(bundle: Dict[str, Any]) -> Set[str]:
    """Rel-paths of the carried/declared character face anchors in a bundle.

    Backend-agnostic so every runner enforces the same face-anchor floor: a plate
    that depicts a character (``carried_identity`` non-empty) must actually attach
    one of these, or it renders an unanchored — drifting — new face.
    """
    return {
        str(rel)
        for item in bundle.get("items") or []
        if str(item.get("kind")) == "character"
        for rel in (item.get("paths") or [])
    }


def carried_identity_unanchored(bundle: Dict[str, Any], attached_paths: Iterable[str]) -> bool:
    """True when the bundle declares carried identity but no character face anchor
    is actually attached — the exact unanchored-face-plate drift condition.

    Honored by both the Codex and Dreamina runners as a pre-spend interlock
    (override: ``N2D_ALLOW_UNANCHORED_IDENTITY_PLATE=1``)."""
    if not bundle.get("carried_identity"):
        return False
    face_paths = bundle_identity_face_paths(bundle)
    if not face_paths:
        return True
    attached = {str(p) for p in attached_paths}
    return not (face_paths & attached)


def log_unanchored_friction(root: Path, episode: str, shot: str, carried, backend: str) -> None:
    """自我优化闭环：carries_identity 但 0 脸锚→定妆脸漂的 pre-spend 闸命中时上报一条现场信号。
    两个 backend 共用（Dreamina runner import 本模块为 base）。纯防御、失败静默、绝不拖垮出图。"""
    if root is None:
        return
    try:
        lib = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
        if lib not in sys.path:
            sys.path.insert(0, lib)
        from n2d_friction import log_friction
    except Exception:
        return
    names = "、".join(str(c) for c in (carried or []))
    log_friction(
        str(root), "n2d-image",
        f"承载身份镜 {shot} 缺脸锚被 pre-spend 闸挡下（{backend}）：carries_identity={names} 却喂 0 张脸锚",
        kind="defect", stage=f"出图/{shot}", episode=episode,
        evidence=str(root and os.path.join("生产数据", "codex_reference_bundles", episode, "")),
        proposed="把承载角色的正面/脸特写参考置 ready，或在 asset_registry 给该资产补 carries_identity 派生脸锚后重试",
        severity="warn",
    )


def attach_reference_inputs(bundle: Dict[str, Any], inputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    bundle["cli_image_input_count"] = len(inputs)
    bundle["cli_image_inputs"] = inputs
    bundle["cli_image_input_limit"] = MAX_CODEX_REFERENCE_IMAGES
    if len(inputs) >= MAX_CODEX_REFERENCE_IMAGES:
        bundle["cli_image_input_truncated"] = True
    return bundle


def write_reference_bundle_manifest(root: Path, episode: str, target: Target, bundle: Dict[str, Any]) -> Path:
    out_dir = root / "生产数据" / "codex_reference_bundles" / episode
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{temp_token(target.shot)}.json"
    path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def high_risk_text_only_character_shot(target: Target) -> bool:
    if target.mode == "shared":
        return False
    chars = _shot_character_refs(target.section.body)
    if not chars:
        return False
    body = target.section.body
    markers = (
        "近景", "特写", "脸部", "反打", "过肩", "CU", "MCU", "ECU",
        "大表情", "表情", "哭", "泪", "惊恐", "震惊", "冷笑", "怒",
        "多人", "同框", "对峙", "暗光", "黑烟", "烟雾", "VFX",
    )
    return len({c.split("/", 1)[0] for c in chars}) >= 2 or any(m in body for m in markers)


def reference_bundle_prompt_text(root: Path, bundle: Dict[str, Any], manifest_path: Optional[Path]) -> str:
    lines = [
        "参考图 bundle（结构化 + Codex CLI 真实附件入参；见 true_image_reference_support=true）：",
        f"- manifest: {manifest_path}" if manifest_path else "- manifest: 未写入",
        f"- true_image_reference_support: {bundle.get('true_image_reference_support')}",
        f"- reference_input_mode: {bundle.get('reference_input_mode') or 'codex_exec_image_flags'}",
        f"- cli_image_input_count: {bundle.get('cli_image_input_count', 0)}",
    ]
    for input_item in bundle.get("cli_image_inputs") or []:
        attachment = reference_input_attachment_path(input_item)
        quality = input_item.get("reference_quality") if isinstance(input_item.get("reference_quality"), dict) else {}
        suffix = ""
        if quality.get("enhanced"):
            suffix = (
                f" [enhanced {quality.get('original_width')}x{quality.get('original_height')}"
                f" -> {quality.get('prepared_width')}x{quality.get('prepared_height')}]"
            )
        lines.append(
            "- --image "
            f"{input_item.get('role')} {input_item.get('owner')}: {attachment}{suffix}"
        )
    for item in bundle.get("items") or []:
        label = f"{item.get('kind')} {item.get('id')}"
        if item.get("form"):
            label += f"/{item.get('form')}"
        paths = [str(root / p) for p in (item.get("paths") or [])]
        lines.append(f"- {label}: " + " | ".join(paths[:8]))
    missing = bundle.get("missing_ready_refs") or []
    if missing:
        lines.append("- missing_ready_refs: " + "、".join(str(x) for x in missing))
    return "\n".join(lines)


def _target_has_character_alias(target: Target) -> bool:
    aliases = {str(item).strip() for item in (getattr(target, "aliases", set()) or set())}
    return any(alias.startswith(("CHAR_", "BEAST_")) for alias in aliases)


def _target_has_prop_alias(target: Target) -> bool:
    aliases = {str(item).strip() for item in (getattr(target, "aliases", set()) or set())}
    return any(alias.startswith(("PROP_", "WEAPON_")) for alias in aliases)


def shared_prop_board_guidance(target: Target) -> str:
    if target.mode != "shared" or not _target_has_prop_alias(target):
        return ""
    stem = Path(target.rel_path).stem
    if any(token in stem for token in ("_手持", "_比例", "_in_hand", "_scale")):
        return (
            "- 道具派生参考板：可以出现无脸手部、无脸人台或下巴以下尺度参照，但不得出现清晰人脸、"
            "具名角色身份、随机服装抢戏或身体残片穿过道具结构。"
        )
    return (
        "- 道具主参考板：只画干净物件本体，置于中性棚拍台面或极简同风格地面；禁止人物、手、肩膀、背影、"
        "身体残片、头发、脸、脚、随机比例人、持握动作或剧情动作。比例/手持语义只作为尺寸说明，"
        "不要把“压在少年肩上/体量压过少年”等剧情描述画成人物；手持和比例另由 `_手持` / `_比例` 槽生成。"
    )


def _target_is_restricted_partial(target: Target) -> bool:
    stem = Path(target.rel_path).stem
    text = f"{stem}\n{target.section.body}"
    return any(token in text for token in ("restricted_partial", "局部参考", "剪影局部", "手部局部", "布料局部", "no_full_face"))


def shared_style_guidance(target: Target, reference_bundle: Optional[Dict[str, Any]]) -> str:
    if target.mode != "shared":
        return ""
    lines = [f"- {REALISTIC_RENDERING_STYLE_GUIDANCE}", f"- {SHARED_MAKEUP_BOARD_GUIDANCE}"]
    if _target_is_restricted_partial(target):
        lines.append(f"- {RESTRICTED_PARTIAL_BOARD_GUIDANCE}")
    elif _target_has_character_alias(target):
        lines.append("- 人物主参考板采用中性站姿/中性表情，角色正面或 45° 身份可辨，但不要看镜头式写真感。")
    prop_guidance = shared_prop_board_guidance(target)
    if prop_guidance:
        lines.append(prop_guidance)
    has_style = any(str(item.get("kind") or "") == "style" for item in (reference_bundle or {}).get("items") or [])
    if has_style:
        lines.append(f"- {STYLE_ONLY_REFERENCE_GUIDANCE}")
    else:
        lines.append("- 当前没有 ready 风格锚附件；只能按文字风格契约生成，产出必须先作为风格探针/候选，不得直接钉成最终定妆。")
    return "共享定妆统一风格约束：\n" + "\n".join(lines)


def aspect_ratio(root: Path) -> str:
    """画幅 选择点（绝不写死，对齐 skills/n2d/references/选择点与偏好.md「画幅」与 compose.sh）：
    env N2D_ASPECT/ASPECT(9:16|16:9) > _设置.md「画幅」> 默认 9:16 竖屏。缺 _lib 时降级正则扫 _设置.md。"""
    env = (os.environ.get("N2D_ASPECT") or os.environ.get("ASPECT") or "").strip()
    if env in {"9:16", "16:9"}:
        return env
    try:
        lib = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
        if lib not in sys.path:
            sys.path.insert(0, lib)
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


def aspect_phrase(ratio: str) -> str:
    """画幅短语：喂进生图 prompt 输出规格行的横/竖屏中文措辞。"""
    return "16:9 横版宽银幕" if str(ratio) == "16:9" else "9:16 竖版"


def style_contract_phrase(root: Path, episode: str) -> str:
    """从 storyboard.json 的 style_contract 提取本剧风格意图（风格名/视觉基调/光色策略/镜头构图 + 风格禁忌），
    供生图后端继承——绝不写死某一种风格（宪法 C4「标准不绑后端」）。读不到 → 空串。"""
    try:
        p = root / "脚本" / episode / "storyboard.json"
        sc = json.loads(p.read_text(encoding="utf-8")).get("style_contract") if p.is_file() else None
    except Exception:
        sc = None
    if not isinstance(sc, dict):
        return ""

    def _val(*keys: str) -> str:
        for k in keys:
            v = sc.get(k)
            if isinstance(v, (list, tuple)):
                v = "、".join(str(x).strip() for x in v if str(x).strip())
            v = str(v or "").strip()
            if v:
                return v
        return ""

    pos = [_val("风格名", "style_name"), _val("视觉基调"), _val("光色策略"), _val("镜头与构图")]
    line = "，".join(p for p in pos if p)
    taboo = _val("风格禁忌", "taboos")
    if taboo:
        line = (line + "。风格禁忌：" + taboo) if line else ("风格禁忌：" + taboo)
    return line


def camera_gaze_negatives_for(body: str) -> str:
    """非 POV 镜的「禁止看镜头/肖像摆拍/自拍」负面词（顿号连接），单一真值源 n2d_const。

    POV / 破第四墙 / 对观众压迫特写经 ``is_camera_gaze_pov_exempt`` 豁免，返回空串。
    两个出图后端共用（Codex 指令块 + Dreamina 直出 prompt）——避免「换渠道就丢视线防呆」，
    打斗镜被即梦渲染成正对镜头肖像摆拍。失败静默、绝不拖垮出图。"""
    try:
        _lib = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
        if _lib not in sys.path:
            sys.path.insert(0, _lib)
        from n2d_const import CAMERA_GAZE_NEGATIVES as _CGN, is_camera_gaze_pov_exempt as _pov_exempt
        if not _pov_exempt(str(body or "")):
            return "、".join(_CGN)
    except Exception:
        pass
    return ""


def weapon_clash_compose_for(body: str) -> str:
    """武器/武技对撞镜的「两兵器接触点硬碰硬」构图指引，单一真值源 n2d_const；非对撞镜返回空串。

    与「镜头不是对视对象」铁律协同（接触点为焦点·脸 ¾/侧非主体）。两个出图后端共用。"""
    try:
        _lib = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
        if _lib not in sys.path:
            sys.path.insert(0, _lib)
        from n2d_const import is_weapon_clash_shot as _is_clash, WEAPON_CLASH_COMPOSE_GUIDANCE as _CCG
        if _is_clash(str(body or "")):
            return str(_CCG)
    except Exception:
        pass
    return ""


def combat_spectacle_richness_for(body: str, style: str = "") -> str:
    """打斗/法术/动作高潮镜的「经费在燃烧」视觉盛宴注入（体积光/大气纵深/环境受力/运动能量四层），
    单一真值源 n2d_const；非打斗镜返回空串。两个出图后端共用，与 apex_light 协同、不糊脸不盖受力点。

    ``style`` 传本剧风格名/风格句（style_contract_phrase）：cel/ink/flat 风格自动换成
    赛璐璐速度线/水墨气劲/夸张图形化变体，避免给非写实剧硬塞写实体积光与 motion blur。"""
    try:
        _lib = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
        if _lib not in sys.path:
            sys.path.insert(0, _lib)
        from n2d_const import is_combat_spectacle_shot as _is_spec, combat_spectacle_guidance_for_style as _csg
        if _is_spec(str(body or "")):
            return str(_csg(str(style or "")))
    except Exception:
        pass
    return ""


def source_frame_geometry_guidance(target: Target) -> str:
    body = str(getattr(target.section, "body", "") or "")
    cross_episode = bool(cross_episode_source_frame_paths(body))
    if target.mode not in {"midframe", "tailframe"} and not cross_episode:
        return ""
    if target.mode == "tailframe":
        role = "尾帧"
    elif target.mode == "midframe":
        role = "中段/动作锚帧"
    elif cross_episode:
        role = "跨集首帧"
    else:
        role = "接力帧"
    weapon_body_contact = has_weapon_body_contact(target)
    geometry_lock = (
        "必须保持同一角色站位、同一道具接触点、同一手握位置和同一画面轴线；"
        "动作推进只能在表情、光效、烟尘、身体微姿态和局部镜头距离上变化，不得把道具接触点移到另一处。"
    )
    if weapon_body_contact:
        geometry_lock = (
            "必须保持同一角色站位、同一武器/道具接触点、同一伤口位置、同一手握位置、同一入射角/刀柄角度和同一画面轴线；"
            "动作推进只能在表情、光效、烟尘、身体微姿态和局部镜头距离上变化，不得把接触点或伤口换到身体另一处。"
        )
    lines = [
        "- **源帧几何连续性硬锁**：本次附加的 `source_frame` 是几何底板，不是普通风格参考。"
        + geometry_lock,
        f"- **源帧主体身份连续硬锁**：本次目标是同一 Clip 的{role}，不是重新选角/重新换装。"
        "主检角色必须继承 `source_frame` 与角色定妆附件里的同一张脸、同一脸型比例、同一发际线、同一发髻/发束轮廓、"
        "同一衣领交叠方向、袖口卷边、腰带位置、裙摆/裤摆长度、鞋履形状和脏旧材质；"
        "只允许改变情绪落点、手臂/水桶/道具的微姿态、水滴/灰尘/光位和镜头距离。"
        "禁止把接力帧画成陌生少年/陌生少女、换发型、换衣服、换鞋、换年龄感，禁止为了画面好看重塑五官或服装剪影。",
    ]
    if cross_episode:
        lines.append(
            "- **跨集动作接力硬锁**：本次首帧必须直接承接上一集尾帧的动作几何。"
            "禁止重新建立远景、禁止让上一集已经近身/亮爪/开战的主体退回深景，禁止把群体动作画成重新从远处走来；"
            "只能在上一集尾帧站位、距离、朝向、光位和轴线上推进拔刀、扑杀、闪避等下一拍动作。"
        )
    if weapon_body_contact:
        lines.append(
            "- **入体点硬锁**：若上一帧已有武器插入身体，本帧只能保留同一把武器、同一处入体点和同一条伤口线；"
            "禁止新增第二处伤口，禁止把胸口伤改成腹部/腰部/肩部伤，禁止让同一把刀像插了多刀一样跳位。"
        )
    return "\n".join(lines)


def weapon_body_contact_guidance(target: Target) -> str:
    body = target_story_action_scope(target) or str(getattr(target.section, "body", "") or "")
    if not has_weapon_body_contact(target):
        return ""
    lines = [
        "- **武器入体/接触点铁律**：本镜若表现武器插入/刺入/贯穿身体，画面只能有一个明确入体点或接触点，"
        "且必须落在 prompt 指定的身体部位；禁止让同一把武器像插了多刀，禁止同一镜里出现互相矛盾的伤口位置。",
    ]
    if re.search(r"(胸口|胸膛|胸前|心口)", body):
        lines.append("  本镜已指定胸口/胸前，入体点必须在上胸/胸口区域；不得画成腹部、腰部、肩部或大腿入刀。")
    return "\n".join(lines)


def has_weapon_body_contact(target: Target) -> bool:
    """Detect an actual weapon/body entry beat without matching QC boilerplate.

    A former detector treated the single character ``入`` as an entry verb.
    Harmless phrases such as ``必须入画`` plus ``木牌递回少年胸前`` then
    injected wound/weapon language into a nonviolent relay-edit prompt, which
    could trigger an image-provider safety rejection.  Use only explicit entry
    verb phrases and the story/action slice here.
    """
    body = target_story_action_scope(target) or str(getattr(target.section, "body", "") or "")
    return bool(
        re.search(r"(?:插(?:入|进|在)|刺(?:入|中|穿|在)|贯穿|捅入|扎入|钉入|没入|贯入)", body)
        and re.search(r"(?:刀|剑|枪|矛|匕首|刃|武器)", body)
        and re.search(r"(?:胸口|胸膛|胸前|心口|腹部|腹|腰部|腰|肩部|肩|背部|背|身体|躯干)", body)
    )


def face_qc_visibility_guidance(target: Target) -> str:
    body = str(getattr(target.section, "body", "") or "")
    if not re.search(r"(CHAR_|人物|角色|姜月初|裴长青|虎山神|虎妖|脸|近景|反打|打斗|动作|持刀)", body):
        return ""
    return (
        "- **脸部机检可核验铁律**：只要本镜含具名角色或 `资产身份注册层`，主检角色的脸必须能被落档机检抓到，"
        "至少保留清楚的眼鼻嘴三角区与脸部轮廓；动作镜可用三分之二侧脸、45°侧脸、过肩露脸或侧前脸，"
        "但不得小到不可辨、不得被头发/暗影/火花/刀光完全遮住、不得只剩纯背影或极端全侧剪影。"
        "保持不看镜头和动作优先，但必须让身份比对有真实脸部证据。"
    )


def hand_limb_anatomy_guidance(target: Target) -> str:
    body = str(getattr(target.section, "body", "") or "")
    if not (
        re.search(r"(CHAR_|人物|角色|姜月初|裴长青|虎山神|虎妖|人形|少女|男子|女主|主角)", body)
        and re.search(
            r"(手|掌|指|腕|臂|胳膊|脚|足|鞋|腿|膝|踝|落点|脚尖|脚步|踩|踏|跪|蹲|握|持|扶|按|触|碰|抓|托|撑|拔|挥|劈|斩|刺|刀|剑|卷|古卷|面板|道具|武器|打斗|动作)",
            body,
        )
    ):
        return ""
    return (
        "- **手部/肢体归属铁律**：含人物手部、武器、道具触碰或动作受力时，必须先锁清楚每只可见手属于哪个角色、"
        "哪一侧手臂以及正在接触什么；单个人形角色最多两条手臂两只手，可见手必须自然连接到同侧手腕、前臂、肘部和肩线。"
        "禁止额外手掌、镜像右手/镜像左手、漂浮断手、手从卷轴/刀柄/光效里长出、左右手归属互换、同一只手在两个位置重复出现、"
        "多指/粘连畸形或袖口遮挡下凭空多出一只手。若一只手按住卷轴/面板/道具，另一只手和武器的归属必须明确；"
        "不需要展示的手宁可被身体、袖子、画幅或道具自然遮挡，也不得生成第三只手或第二个同侧手。"
        "含脚尖、脚步、踩踏、跪地、蹲伏、踢、落点或鞋靴时，必须清楚显示脚/鞋/小腿的归属和受力方向；"
        "禁止把脚画成手、用手掌替代脚掌、让脚趾变成手指、让地面支撑点从脚变成手，脚部动作不清时宁可改构图到鞋靴落点特写。"
    )


def target_story_action_scope(target: Target) -> str:
    """Return only story/action prose, excluding generic QC boilerplate.

    Whole prompt-pack sections contain words such as ``穿模`` and
    ``无跨集动作接力``. Feeding the entire section to semantic detectors made
    harmless shots look like weapon-entry or combat scenes.
    """
    body = str(getattr(target.section, "body", "") or "")
    action = re.search(r"(?m)^动作瞬间[：:]\s*(.+)$", body)
    if action:
        text = action.group(1)
        text = re.split(
            r"；(?:人体完整性|解剖完整性|手部归属|身体接地|身体裁切|本镜状态锁)[^：:]*[：:]",
            text,
            maxsplit=1,
        )[0]
        return re.sub(r"\s+", " ", text).strip()
    description = re.search(r"(?m)^\*\*剧本描述\*\*[：:]\s*(.+)$", body)
    return re.sub(r"\s+", " ", description.group(1)).strip() if description else ""


def image_style_brief(root: Path, episode: str) -> str:
    try:
        data = load_json_file(root / "脚本" / episode / "storyboard.json")
        style = data.get("style_contract") if isinstance(data.get("style_contract"), Mapping) else {}
    except Exception:
        style = {}
    parts: List[str] = []
    for key in ("风格名", "style_name", "视觉基调", "光色策略"):
        value = style.get(key) if isinstance(style, Mapping) else None
        text = re.sub(r"\s+", " ", str(value or "")).strip(" ；;,，。")
        if text and text not in parts:
            parts.append(text)
    if parts:
        return "；".join(parts)
    try:
        text = (root / "_设置.md").read_text(encoding="utf-8")
    except Exception:
        text = ""
    match = re.search(r"基础视觉风格\s*[：:]\s*(.+)$", text, re.M)
    return match.group(1).strip() if match else "继承项目基础视觉风格与 style_anchor"


def image_request_params(root: Path) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "aspect_ratio": aspect_ratio(root),
        "output_format": "png",
    }
    try:
        text = (root / "_设置.md").read_text(encoding="utf-8")
    except Exception:
        text = ""
    for label, key in (("生图分辨率", "size"), ("图片分辨率", "size"), ("生图质量", "quality"), ("图片质量", "quality")):
        match = re.search(rf"(?m)^\s*(?:[-*]\s*)?{re.escape(label)}\s*[：:]\s*(.+?)\s*$", text)
        if match and key not in params:
            params[key] = match.group(1).strip().strip("`|")
    return params


def strict_single_image_review_enabled(root: Path) -> bool:
    """The one-image review gate is a project-independent hard floor.

    `_设置.md` still records the user's preferred wording for UI/provenance, but
    no project may weaken the B14 load-bearing pre/post consistency gate.  This
    deliberately returns True even for legacy projects that lack the setting.
    """
    return True


_OPTIONAL_SHARED_IDENTITY_VIEWS = {
    "named_minimal": {"three_quarter", "side", "rear_three_quarter", "back", "turnaround"},
    "recurring_standard": {"side", "rear_three_quarter", "back", "turnaround"},
}


def _is_explicitly_abandoned_optional_shared_image(
    root: Path,
    asset: str,
    artifact_sha: str,
    event: Mapping[str, Any],
) -> bool:
    """Return whether a rejected optional shared view was deliberately retired.

    This is intentionally narrower than a general QA waiver: the exact rejected
    hash must be named, the canonical PNG must already be absent, and the current
    identity registry must classify the matching view as optional for its library
    tier with ``status=review_failed``.  A later shot that truly needs the angle is
    still blocked by the shared-first reference interlock.
    """
    meta = event.get("meta") if isinstance(event.get("meta"), Mapping) else {}
    if (
        str(meta.get("terminal_disposition") or "") != "abandoned_optional"
        or str(meta.get("accepted_current_pixels")).strip().lower() not in {"false", "0", "no"}
        or str(meta.get("artifact_sha256") or "") != artifact_sha
        or (root / asset).exists()
    ):
        return False

    registry_path = root / "出图" / "共享" / "identity_registry.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, TypeError, json.JSONDecodeError):
        return False
    characters = registry.get("characters") if isinstance(registry, Mapping) else None
    if not isinstance(characters, list):
        return False
    for character in characters:
        if not isinstance(character, Mapping):
            continue
        character_tier = str(character.get("library_tier") or "")
        forms = character.get("forms")
        if not isinstance(forms, list):
            continue
        for form in forms:
            if not isinstance(form, Mapping):
                continue
            tier = str(form.get("library_tier") or character_tier)
            optional_views = _OPTIONAL_SHARED_IDENTITY_VIEWS.get(tier, set())
            group = form.get("reference_group")
            if not isinstance(group, Mapping):
                continue
            for view in optional_views:
                slot = group.get(view)
                visual_review = (
                    slot.get("visual_review")
                    if isinstance(slot, Mapping)
                    and isinstance(slot.get("visual_review"), Mapping)
                    else {}
                )
                if (
                    isinstance(slot, Mapping)
                    and str(slot.get("path") or "") == asset
                    and str(slot.get("status") or "") in {"planned", "review_failed"}
                    and str(visual_review.get("status") or "") == "rejected"
                    and str(visual_review.get("png_sha256") or "") == artifact_sha
                ):
                    return True
    return False


def _is_explicitly_archived_stop_loss_shared_image(
    root: Path,
    asset: str,
    artifact_sha: str,
    event: Mapping[str, Any],
) -> bool:
    """Allow production to move on after an exact rejected shared PNG is retired.

    This is not an acceptance or a general QA waiver.  The exact generated hash
    must have a terminal executor/human rejection with ``stop_loss=true`` and
    ``accepted_current_pixels=false``, and the rejected PNG must already have
    been removed from the canonical shared-library path.  Episode frames and
    any rejected image still present in the formal namespace remain blocking.
    """
    meta = event.get("meta") if isinstance(event.get("meta"), Mapping) else {}
    return bool(
        asset.startswith("出图/共享/图片/")
        and str(meta.get("stop_loss") or "").strip().lower() in {"true", "1", "yes"}
        and str(meta.get("accepted_current_pixels", "")).strip().lower() in {"false", "0", "no"}
        and artifact_sha
        and str(meta.get("artifact_sha256") or "") == artifact_sha
        and not (root / asset).exists()
    )


def strict_pending_image_review(root: Path, next_rel_path: str) -> Optional[Dict[str, str]]:
    """Return the latest different image awaiting hash-bound QA acceptance.

    Re-drawing the same target remains allowed so a rejected current unit can
    be improved.  Moving to a different image requires a later dashboard QA
    event with ``status=accepted`` and the exact generated pixel hash, except
    for an exact-hash rejected optional shared identity view that has been
    explicitly retired and removed from its canonical path, or for an exact-hash
    rejected shared-library target explicitly closed by the audited stop-loss
    policy and removed from the canonical namespace.
    """
    path = root / "生产数据" / "production_events.jsonl"
    if not path.is_file():
        return None
    events: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(event, dict):
            events.append(event)
    latest: Optional[Tuple[int, str, str]] = None
    for index, event in enumerate(events):
        generation = event.get("generation") if isinstance(event.get("generation"), Mapping) else {}
        if (
            event.get("stage") == "image"
            and event.get("event") in {"generation", "redraw"}
            and generation.get("status") == "pass"
            and generation.get("asset")
        ):
            meta = event.get("meta") if isinstance(event.get("meta"), Mapping) else {}
            latest = (index, str(generation["asset"]), str(meta.get("artifact_sha256") or ""))
    if latest is None:
        return None
    latest_index, asset, artifact_sha = latest
    if asset == next_rel_path:
        return None
    for event in events[latest_index + 1:]:
        generation = event.get("generation") if isinstance(event.get("generation"), Mapping) else {}
        meta = event.get("meta") if isinstance(event.get("meta"), Mapping) else {}
        if (
            event.get("stage") == "image"
            and event.get("event") == "qa"
            and str(generation.get("asset") or "") == asset
            and artifact_sha
            and str(meta.get("artifact_sha256") or "") == artifact_sha
        ):
            if generation.get("status") == "accepted":
                return None
            if (
                generation.get("status") == "rejected"
                and _is_explicitly_abandoned_optional_shared_image(
                    root, asset, artifact_sha, event
                )
            ):
                return None
            if (
                generation.get("status") == "rejected"
                and _is_explicitly_archived_stop_loss_shared_image(
                    root, asset, artifact_sha, event
                )
            ):
                return None
    return {"asset": asset, "artifact_sha256": artifact_sha}


def image_prompt_experiment_context() -> Dict[str, str]:
    experiment_id = os.environ.get("N2D_IMAGE_PROMPT_EXPERIMENT_ID", "").strip()
    variant = os.environ.get("N2D_IMAGE_PROMPT_VARIANT", "").strip()
    if bool(experiment_id) != bool(variant):
        raise ValueError(
            "image prompt A/B requires both N2D_IMAGE_PROMPT_EXPERIMENT_ID and N2D_IMAGE_PROMPT_VARIANT"
        )
    return {"experiment_id": experiment_id, "variant": variant} if experiment_id else {}


def model_facing_policy_guards(
    target: Target,
    reference_inputs: Sequence[Mapping[str, Any]],
) -> List[str]:
    """Return only pixel-relevant target constraints for the compiled request.

    Operational details such as internal registry paths, preprocessing commands,
    retry budgets and QC routing stay in the complete production contract and
    receipts.  This function preserves the few high-risk visual invariants that
    used to live in the oversized Codex wrapper.
    """
    body = str(getattr(target.section, "body", "") or "")
    guards: List[str] = []

    stem = Path(target.rel_path).stem
    if "风格锚" in stem or "style_anchor" in stem.lower():
        # STYLE_ANCHOR is a control asset, not a character/prop/scene card.
        # Its human-readable contract necessarily names downstream subjects
        # and forbidden story objects; those nouns must never trigger the
        # generic gaze, anatomy, weapon-contact or scene guards below.
        return [
            "风格锚是抽象视觉语言控制板，不是剧情剧照、环境设定图、海报或道具陈列",
            "使用清晰分区的色卡、明暗与光比阶梯、线条笔触、颜料颗粒和近裁材质样本；保持中性无叙事背景",
            "画面不出现人物或脸、动物或妖物、建筑或城寨、兵器、道具、器皿、家具、工作台、卷轴、地图、书页、可读或伪造文字、剧情动作、水印或标志",
        ]
    aliases = {str(item) for item in getattr(target, "aliases", set()) or set()}
    shared_scene_target = target.mode == "shared" and any(
        value.startswith("LOC_")
        for value in {str(target.shot or ""), str(target.clip or ""), *aliases}
    )
    primary_character_makeup = (
        target.mode == "shared"
        and not shared_scene_target
        and _target_has_character_alias(target)
        and not any(token in stem for token in ("45度", "三分之二", "_侧", "侧面", "_背", "背面", "半身", "脸部", "三视图", "表情", "动作"))
    )
    real_quadruped = (
        target.mode == "shared"
        and _target_has_character_alias(target)
        and bool(re.search(r"真实四足|四(?:只|条)?(?:虎)?掌(?:全部)?着地|野生猫科|四足兽类", body))
    )
    gaze_lock = not shared_scene_target and bool(re.search(
        r"CHAR_|人物|角色|少年|少女|男人|女人|男子|女子|主角|对手|打斗|格挡|挥剑|劈砍|出拳|对话",
        body,
    )) and bool(camera_gaze_negatives_for(body))
    if primary_character_makeup and real_quadruped:
        guards.append(
            "真实四足动物正面母本（最高优先级）：四只兽掌全部着地，躯干水平，头部正对相机，"
            "肩胛、脊背、骨盆、四肢和长尾符合真实猫科/犬科解剖；禁止双足直立、虎头人身/狼头人身、"
            "类人胸肌、类人手臂手掌、兽人或妖物形态。全身从耳尖、四掌到尾尖完整可见"
        )
    elif primary_character_makeup:
        guards.append(
            "共享角色正面主母本：身体、肩线和脸严格正对相机，头部偏转不超过 5 度，双眼与五官近似对称可核验；"
            "眼神轻微越过镜头而非写真式盯镜头。不得生成 45°、三分之二侧脸、侧身、背身或多视图拼板"
        )
    elif gaze_lock:
        guards.append(
            "镜头为旁观者视角：角色不看镜头，视线锁定场内对象、对话对象、手中物件或所视之物；"
            "身份可辨使用三分之二、45°、侧脸或过肩露脸，不转成正对镜头肖像摆拍"
        )

    if "刀柄、发抖指节和衣料同轴" in body:
        guards.insert(0, (
            "冷开场首帧必须是85mm ECU/CU叙事插入，不是全身群像或两人并排跪地摆拍："
            "前景清楚看见姜月初发抖的手紧握唯一一把横刀刀柄，暗银单刃刀身横向或斜横穿过画面，"
            "刀尖悬停并明确指向画面右侧半跪的成年男性裴长青胸颈，尚未接触；"
            "姜月初带少量暗红血污的痛苦决绝三分之二侧脸在中近景，二人都看戏内对象而非镜头；"
            "虎山神只在远后景浅景深中形成虎头人身、直立双腿和人形肩背的巨影，绝不是四足普通老虎。"
            "三层必须一眼读成‘刀对准人、妖在后方逼近’的反差"
        ))

    if str(getattr(target, "shot", "") or "") == "Clip_02_first" and "尸场空间一次建立" in body:
        guards[:0] = [
            (
                "十分钟前首帧版式：35mm低机位广角尸场建立镜。姜月初画左从尸堆侧躺撑起，空手摸无血残损囚服；"
                "裴长青在画右相隔至少两个身位独自半跪。禁止贴坐、对跪、搀扶、持刀对人、85mm海报群像和任何角色看镜头"
            ),
            (
                "CHAR_04状态与拓扑：虎山神是远后景水平倒地伪死的虎头人身巨人，具人形胸腹、两条人形手臂手掌和两条人形腿脚；"
                "禁止站立、复活、逼近、四足兽爪、水平长虎身或普通老虎"
            ),
            (
                "道具唯一性：翻覆囚车、官道尸体和残骸建立死局；只出现一截断刀插地封路。"
                "本帧完整横刀尚未入画，禁止完整长刀、第二把刀、双刀、碎片变成多把刀或武器陈列"
            ),
        ]

    if str(getattr(target, "shot", "") or "") == "Clip_04_first":
        guards[:0] = [
            (
                "交易落槌首帧状态：50mm双人中景，姜月初保持画左站立、裴长青保持画右半跪，"
                "两人尚未发生任何肢体接触或搀扶；共同关注戏内逃生方向，不看镜头"
            ),
            (
                "CHAR_04必须只在远后景地面水平倒伏伪死：虎头侧贴地、双眼闭合，具人形肩背、"
                "两条人形手臂手掌、两条人形腿脚和完整卧倒巨躯；禁止直立、坐起、悬浮、睁眼、"
                "直视镜头、四足普通老虎、仅画一颗巨大虎头或半身胸像"
            ),
            (
                "本帧画内只保留姜月初手中的一把完整横刀；PROP_断刀已留在上一空间并保持画外。"
                "禁止地面断刀、第二把刀、刀鞘误画成刀刃、双刀或武器陈列"
            ),
        ]

    if "左臂不自然扭曲" in body or "左臂骨折" in body:
        guards.append(
            "左臂伤势是必须可读的连续性锚点：按角色自身左右计，伤臂位于画面观者右侧；"
            "肘/前臂必须出现清楚的受伤折角并无力下垂，明显无法承重或正常发力；"
            "保持恰好两条手臂两只手，不得增生肢体、错置关节或把未受伤的右臂一起画坏"
        )

    if shared_scene_target and "系统金光仅作局部剧情光" in body:
        guards.append(
            "空场景主母本是无特效的环境底版：本张完全不出现系统金光、金色法术纹、金色能量轨迹、"
            "发光法器、仪式器皿、符阵或魔法烟雾；只保留自然夕阳在尘土、岩石和旧金属上的低饱和反光，"
            "系统特效由后续镜头单独叠加"
        )

    resident_character_refs = sorted(_shot_character_refs(body)) if shared_scene_target else []
    if resident_character_refs:
        guards.append(
            "场景中的常驻具名主体必须继承对应身份附件："
            + "、".join(resident_character_refs)
            + "；尸体/倒地状态只改变姿势和生命状态，不改变物种、人形/四足拓扑、头部结构、毛色、体量或持续伤口；"
            "禁止把虎头人身妖物改成四足普通虎"
        )

    external_character_inputs = any(
        str(item.get("role") or "") == "character"
        and not str(item.get("rel_path") or "").startswith("出图/共享/")
        for item in reference_inputs
        if isinstance(item, Mapping)
    )
    if re.search(r"用户(?:提供的)?(?:人物|主角)?参考图|外部参考图", body) or external_character_inputs:
        guards.extend([
            "用户提供的人物/主角参考图默认只作身份与身形锚：提取基础身高、体型/身材比例、体态、脸型、五官比例和年龄感；"
            "外部参考图的风格权重视为 0，不得继承参考图里的画风、照片/摄影风格、渲染风格、滤镜、光影、构图、衣装或背景",
            "附件是真实视觉证据；每个角色只使用自己的身份附件，禁止把 A 的脸或身形套给 B；脸型、五官比例、年龄感与身形可读附件，发型、服装、配饰和道具结构必须服从本项目角色定妆合同，禁止继承外部参考图衣装",
            "低清或截图参考只锁身份与结构；不得继承低清、像素化、模糊、压缩块、屏幕截图质感、播放按钮、平台 UI、字幕或水印，输出保持清晰干净",
        ])

    group_guard = shared_group_member_variant_guidance(target)
    if group_guard:
        guards.append(
            "共享群像角色角度资产硬约束：本目标只画一名普通代表成员；各角度必须是同一名成员，"
            "不得画成多人队列、三名军士并排、重复复制人、关系图或小队合影"
        )

    if target.mode in {"midframe", "tailframe"} or cross_episode_source_frame_paths(body):
        source_geometry_guard = (
            "源帧几何连续性硬锁：保持同一角色站位、同一道具接触点、同一手握位置和画面轴线；"
            "只推进表情、光效、烟尘、身体微姿态或镜头距离"
        )
        if has_weapon_body_contact(target):
            source_geometry_guard = (
                "源帧几何连续性硬锁：保持同一角色站位、同一武器/道具接触点、同一伤口位置、同一手握位置、"
                "同一入射角/刀柄角度和画面轴线；只推进表情、光效、烟尘、身体微姿态或镜头距离"
            )
        guards.extend([
            source_geometry_guard,
            "源帧主体身份连续硬锁：这是同一 Clip 接力，不是重新选角/重新换装；保持同一脸型比例、同一发际线、同一发髻/发束轮廓，以及同一衣领交叠方向、袖口卷边、腰带位置、衣摆、鞋履和材质",
        ])
        if has_weapon_body_contact(target):
            guards.append(
                "入体点硬锁：保留同一把武器、同一处入体点和同一条伤口线；"
                "禁止新增第二处伤口，禁止把胸口伤改成腹部/腰部/肩部伤"
            )

    if not shared_scene_target and weapon_body_contact_guidance(target):
        guards.append(
            "武器入体/接触点铁律：只能有一个明确入体点或接触点，落在剧情指定身体部位；"
            "禁止同一把武器像插了多刀或出现互相矛盾的伤口位置"
        )
        if re.search(r"(胸口|胸膛|胸前|心口)", body):
            guards.append(
                "本镜已指定胸口/胸前：入体点在上胸/胸口，不得画成腹部、腰部、肩部或大腿入刀"
            )

    if target.mode != "shared" and face_qc_visibility_guidance(target):
        guards.append(
            "脸部机检可核验铁律：主检角色保留清楚的眼鼻嘴三角区与脸部轮廓；动作镜可用三分之二、45°、过肩或侧前脸，"
            "不得被头发/暗影/火花/刀光完全遮住，也不得被其他强烈光效完全遮住；不转成看镜头肖像"
        )
    if target.mode != "shared" and hand_limb_anatomy_guidance(target):
        guards.extend([
            "手部/肢体归属铁律：每只可见手明确归属角色和左右手臂，单个人形角色最多两条手臂两只手；"
            "保持左右手方向正确、手腕连接连续，每只手只出现一次；禁止额外手掌、镜像右手/镜像左手，人体与手部结构自然完整",
            "若一只手接触道具，另一只手和武器的归属必须明确；可自然遮挡不需展示的手，但不生成第三只手",
        ])

    if real_quadruped:
        guards.append(
            "共享真实动物定妆使用中性灰白/18%灰棚拍背景，无窗、无房间、无家具、无剧情道具；"
            "四足全身与尾部完整可见，不套用人物的鞋靴、服装、手部或直立姿态规则"
        )
    elif target.mode == "shared" and not shared_scene_target and _target_has_character_alias(target):
        guards.append(
            "共享角色定妆使用统一规格的定妆参考板：中性灰白/18%灰棚拍背景，无窗、无房间、无家具、无剧情道具；"
            "全身、角度和三视图从头到鞋靴完整可见"
        )
    if target.mode == "shared" and _target_has_prop_alias(target):
        stem = Path(target.rel_path).stem
        if any(token in stem for token in ("_手持", "_比例", "_in_hand", "_scale")):
            guards.append("道具尺度派生板可用无脸手部或下巴以下尺度参照；道具结构完整，不出现清晰人脸或具名角色身份")
        else:
            guards.append("道具主参考板只画干净物件本体和中性背景；不出现人物、手、脸、身体残片、持握动作或剧情动作")

    if any(
        str(item.get("role") or item.get("kind") or "").lower() == "style"
        for item in reference_inputs
        if isinstance(item, Mapping)
    ):
        guards.append(
            "风格附件只提供线条、材质、色彩分级、镜头语言和完成度；不得继承风格锚里的具体人物身份、五官、服装、动作、背景场景或构图"
        )
    return list(dict.fromkeys(item.strip(" ；。") for item in guards if item.strip()))


def section_continuity_must_for_model(
    body: str,
    *,
    soften_adult_minor_contact: bool = True,
) -> List[str]:
    """Extract storyboard ``continuity_must`` clauses from a prompt section.

    The prompt pack already carries the authoritative storyboard contract, but
    the compact compiler previously discarded this field.  That made visible
    props disappear between adjacent episode frames even though the upstream
    plan explicitly required them. Keep clauses compact. Codex/OpenAI may opt
    into the provider-boundary non-contact rewrite; other signed official
    backends retain the storyboard action instead of receiving a contract that
    simultaneously asks for contact and forbids it.
    """
    match = re.search(r"continuity_must\s*=\s*(\[[^\n]*?\])(?=；|;|\n|$)", str(body or ""))
    if not match:
        return []
    try:
        raw = json.loads(match.group(1))
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list):
        return []
    has_minor = bool(re.search(r"(?:十四岁|14岁|少年|未成年)", str(body or ""), re.I))
    clauses: List[str] = []
    for item in raw:
        clause = re.sub(r"\s+", " ", str(item or "")).strip(" ；。")
        if not clause:
            continue
        if soften_adult_minor_contact and has_minor and re.search(r"(?:拍肩|压(?:到|住|在)?[^；。]{0,8}肩|肩头接触)", clause):
            clause = "成人右手只撑在少年身侧桌边，靠近但不接触少年身体"
        clauses.append(clause)
    return list(dict.fromkeys(clauses))


def critical_retry_guard(retry_guidance: str) -> str:
    """Return a compact, compiler-surviving guard for an actual-pixel rerun."""
    text = str(retry_guidance or "").strip()
    if not text:
        return ""
    prefix = "上一次当前像素实际目视拒收原因："
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip(" -")
        if line.startswith(prefix):
            reason = line[len(prefix):].strip()
            if reason:
                return "返工硬约束（最高优先级）：" + reason
    flattened = re.sub(r"\s+", " ", text).strip()
    return "返工硬约束（最高优先级）：" + flattened


_STILL_UNSAFE_VIDEO_EDIT_RE = re.compile(
    r"跳切|分屏|拼贴|三联|四联|多格|蒙太奇|转场|剪切|"
    r"jump\s*cut|split[- ]?screen|triptych|collage|montage|transition",
    re.I,
)


def storyboard_motion_for_still(video_prompt: str) -> str:
    """Keep pose/micro-motion guidance, never edit/layout language, in a still prompt.

    Storyboard ``video_prompt`` is authored for a moving clip. Passing an edit
    direction such as "三个清晰跳切" to an image model makes it render a
    triptych/contact sheet. A physical first/mid/tail frame must remain one
    continuous camera image; the video stage owns cuts and transitions.
    """
    text = re.sub(r"\s+", " ", str(video_prompt or "")).strip()
    if not text or _STILL_UNSAFE_VIDEO_EDIT_RE.search(text):
        return ""
    return text


def storyboard_anchor_beat(root: Path, episode: str, target: Target) -> Dict[str, Any]:
    """Resolve a physical first/anchor frame to its timed storyboard sub-shot.

    One prompt section can own several physical sub-shots. Reusing its merged
    action for the first frame or every ``_aN`` merges adjacent edit beats. At
    an exact edit boundary the anchor belongs to the sub-shot that starts
    there, not the one that just ended.
    """
    if target.mode not in {"firstframe", "midframe"}:
        return {}
    data = load_json_file(root / "脚本" / episode / "storyboard.json")
    target_num = re.search(r"(\d+)$", str(target.clip or ""))
    if not target_num:
        return {}
    clip = next((
        row for row in data.get("clips") or []
        if isinstance(row, dict)
        and re.search(r"(\d+)$", str(row.get("id") or ""))
        and int(re.search(r"(\d+)$", str(row.get("id") or "")).group(1)) == int(target_num.group(1))
    ), None)
    if not isinstance(clip, dict):
        return {}
    if target.mode == "firstframe":
        anchor_index = 0
        at_sec = 0.0
        frame_role = "first"
    else:
        anchors = (clip.get("continuity") or {}).get("anchors") or []
        anchor_index = next((
            index for index, row in enumerate(anchors)
            if isinstance(row, dict)
            and rel_to_root(str(row.get("anchor_png") or ""), episode) == target.rel_path
        ), -1)
        if anchor_index < 0:
            match = re.search(r"_a(\d+)$", str(target.shot or ""), re.I)
            if not match:
                return {}
            anchor_index = int(match.group(1)) - 1
        if anchor_index < 0 or anchor_index >= len(anchors) or not isinstance(anchors[anchor_index], dict):
            return {}
        try:
            at_sec = float(anchors[anchor_index].get("at_sec"))
        except (TypeError, ValueError):
            return {}
        frame_role = f"a{anchor_index + 1}"
    parsed: List[Tuple[float, float, Dict[str, Any]]] = []
    for row in clip.get("shots") or []:
        if not isinstance(row, dict):
            continue
        timing = re.match(r"\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*s?\s*$", str(row.get("t") or ""), re.I)
        if timing:
            parsed.append((float(timing.group(1)), float(timing.group(2)), row))
    if not parsed:
        untimed = [row for row in (clip.get("shots") or []) if isinstance(row, dict)]
        if not untimed:
            return {}
        if target.mode == "firstframe":
            selected_index = 0
        else:
            try:
                duration = float(clip.get("duration") or 0)
            except (TypeError, ValueError):
                duration = 0.0
            if duration <= 0:
                anchors = (clip.get("continuity") or {}).get("anchors") or []
                try:
                    duration = max(float(row.get("source_duration") or 0) for row in anchors if isinstance(row, dict))
                except (TypeError, ValueError):
                    duration = 0.0
            if duration > 0:
                selected_index = min(int(max(0.0, at_sec) / duration * len(untimed)), len(untimed) - 1)
            else:
                selected_index = min(anchor_index + 1, len(untimed) - 1)
        duration = float(clip.get("duration") or len(untimed) or 1)
        segment = duration / max(len(untimed), 1)
        parsed = [
            (index * segment, (index + 1) * segment, row)
            for index, row in enumerate(untimed)
        ]
        selected = parsed[selected_index]
    else:
        exact = next((item for item in parsed if abs(item[0] - at_sec) <= 1e-4), None)
        selected = exact or next((item for item in parsed if item[0] <= at_sec < item[1]), None)
    if not selected:
        return {}
    start, end, row = selected
    desc = re.sub(r"\s+", " ", str(row.get("desc") or "")).strip()
    lens = re.sub(r"\s+", " ", str(row.get("lens") or "")).strip()
    video_prompt = re.sub(r"\s+", " ", str(row.get("video_prompt") or "")).strip()
    names: List[Tuple[str, str]] = []
    identity = load_json_file(root / "出图" / "共享" / "identity_registry.json")
    for character in identity.get("characters") or []:
        if isinstance(character, dict):
            cid = str(character.get("id") or "").strip()
            name = str(character.get("name") or "").strip()
            if cid and name:
                names.append((cid, name))
    focus = [(cid, name) for cid, name in names if name in desc]
    focus_ids = [cid for cid, _name in focus]
    focus_names = [name for _cid, name in focus]
    excluded_names = [name for cid, name in names if cid in (clip.get("character_ids") or []) and cid not in focus_ids]
    is_single_reaction = bool(
        len(focus_names) == 1
        and re.search(r"CU|ECU|特写|近景", lens, re.I)
        and re.search(r"应下|反应|垂眼|点头|呼气|抿唇|沉默", desc)
    )
    is_faceless_insert = bool(
        not focus_names
        and re.search(r"insert|ECU|物件|特写", lens, re.I)
        and re.search(r"不出现[^；。]{0,8}人脸|无人物|无人|空镜", desc)
    )
    is_detail_insert = bool(
        not focus_names
        and not is_faceless_insert
        and re.search(r"insert|ECU|局部|特写", lens, re.I)
        and re.search(r"掌心|手指|手背|手腕|单手|双手|右手|左手|脚|鞋|桶|盆|容器|器具|扁担|道具|物件|伤口|水下", desc)
    )
    knowledge_state = (clip.get("entity_schedule") or {}).get("knowledge_state") or {}
    audience_knowledge = "；".join(
        str(item or "").strip() for item in knowledge_state.get("AUDIENCE") or [] if str(item or "").strip()
    )
    character_knowledge = "；".join(
        str(item or "").strip()
        for key, values in knowledge_state.items()
        if str(key).startswith("CHAR_")
        for item in (values or [])
        if str(item or "").strip()
    )
    audience_only_reveal = bool(
        audience_knowledge
        and re.search(r"不知|未察觉|没发现|不知道", character_knowledge)
    )
    continuity = clip.get("continuity") or {}
    current_state = (
        re.sub(r"\s+", " ", str(continuity.get("start_state") or "")).strip()
        if target.mode == "firstframe"
        else desc
    )
    visibility_text = "；".join(filter(None, (desc, current_state)))
    asset_registry = load_json_file(root / "出图" / "共享" / "asset_registry.json")
    clip_object_ids = {str(value or "").strip() for value in clip.get("object_ids") or []}
    visible_objects: List[str] = []
    excluded_objects: List[str] = []
    excluded_object_aliases: List[str] = []
    prop_nouns = ("扁担", "木牌", "水桶", "桶", "盆", "碗", "瓶", "壶", "灯", "剑", "刀", "枪", "鞋", "包")
    for asset in asset_registry.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        asset_id = str(asset.get("id") or "").strip()
        if asset_id not in clip_object_ids:
            continue
        name = str(asset.get("name") or asset_id).strip()
        aliases = [asset_id, name]
        aliases.extend(noun for noun in prop_nouns if noun in name)
        aliases = list(dict.fromkeys(alias for alias in aliases if alias))
        if any(alias in visibility_text for alias in aliases):
            visible_objects.append(name)
        else:
            excluded_objects.append(name)
            excluded_object_aliases.extend(aliases)
    return {
        "anchor_index": anchor_index + 1,
        "frame_role": frame_role,
        "at_sec": at_sec,
        "start_sec": start,
        "end_sec": end,
        "desc": desc,
        "lens": lens,
        "video_prompt": video_prompt,
        "focus_ids": focus_ids,
        "focus_names": focus_names,
        "excluded_names": excluded_names,
        "single_reaction": is_single_reaction,
        "faceless_insert": is_faceless_insert,
        "detail_insert": is_detail_insert,
        "audience_only_reveal": audience_only_reveal,
        "audience_knowledge": audience_knowledge,
        "character_knowledge": character_knowledge,
        "current_state": current_state,
        "visible_objects": visible_objects,
        "excluded_objects": excluded_objects,
        "excluded_object_aliases": list(dict.fromkeys(excluded_object_aliases)),
    }


def compile_target_image_request(
    root: Path,
    episode: str,
    target: Target,
    reference_inputs: Sequence[Mapping[str, Any]],
    *,
    backend: str = "codex",
    model: str = "",
    channel: str = "",
    retry_guidance: str = "",
    request_params_override: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    selection = current_image_backend_selection(str(root))
    actual_model = model or os.environ.get("N2D_IMAGE_MODEL") or str(selection.get("image_model") or "")
    actual_channel = channel or str(selection.get("channel") or selection.get("access") or "")
    task = infer_image_task_type(target.section.body, mode=target.mode, target_path=target.rel_path)
    params = image_request_params(root)
    params.update(dict(request_params_override or {}))
    body = str(target.section.body or "")
    policy_guards = model_facing_policy_guards(target, reference_inputs)
    anchor_beat = storyboard_anchor_beat(root, episode, target)
    continuity_must = section_continuity_must_for_model(
        body,
        soften_adult_minor_contact=backend in {"codex", "openai"},
    )
    if anchor_beat.get("single_reaction"):
        continuity_must = [
            clause for clause in continuity_must
            if not re.search(r"(?:拍肩|压(?:到|住|在)?[^；。]{0,8}肩|肩头接触)", clause)
        ]
    if continuity_must:
        policy_guards.insert(0, "专项连续性硬约束：" + "；".join(continuity_must))
    retry_guard = critical_retry_guard(retry_guidance)
    if retry_guard and anchor_beat.get("single_reaction"):
        focus = "、".join(anchor_beat.get("focus_names") or []) or "本锚焦点角色"
        excluded = "、".join(anchor_beat.get("excluded_names") or []) or "前一动作人物"
        retry_guard = (
            f"返工硬约束（最高优先级）：本锚只画{focus}的单人反应特写；"
            f"{excluded}及其双手完全出画；不得延续前一子镜头的身体接触动作"
        )
    if retry_guard:
        # Keep the actual-pixel rejection in a dedicated high-priority clause.
        # Appending it to a long objective silently loses it when the compiler
        # compacts objective to 180 characters.
        policy_guards.insert(0, retry_guard)
    story_action = target_story_action_scope(target)
    clash = weapon_clash_compose_for(story_action)
    if clash:
        policy_guards.append(re.sub(r"\s+", " ", clash).strip(" -；。"))
    selected_style = image_style_brief(root, episode)
    spectacle = combat_spectacle_richness_for(story_action, selected_style)
    if spectacle:
        if re.search(r"赛璐璐|二次元|anime|cel(?:[- ]?shad)", selected_style, re.I):
            policy_guards.append(
                "动作高潮按赛璐璐视觉语法呈现：清晰轮廓、分层色块、图形化冲击形、方向明确的速度线和短促残影；"
                "环境同步受力，动作与身份始终清楚，不混入写实体积光或长拖影 motion blur"
            )
        elif re.search(r"水墨|国画|ink wash|sumi", selected_style, re.I):
            policy_guards.append(
                "动作高潮按水墨视觉语法呈现：飞白与泼墨气劲沿攻击方向展开，以浓淡、留白和墨雾建立纵深；"
                "环境同步受力，动作与身份清楚，不混入写实体积光或写实景深"
            )
        else:
            policy_guards.append(
                "动作高潮呈现经费在燃烧的完成度：丁达尔体积光勾勒主体，大气透视分离前中后景，"
                "碎屑、烟尘和衣摆体现环境受力，速度线与短促运动残影强化方向；脸和命中点保持清楚"
            )
    contract = contract_from_section(
        target.section.body,
        backend=backend,
        model=actual_model,
        channel=actual_channel,
        mode=target.mode,
        task_type=task,
        target_path=target.rel_path,
        style=image_style_brief(root, episode),
        aspect_ratio=str(params.get("aspect_ratio") or ""),
        reference_inputs=reference_inputs,
        request_params=params,
        policy_guards=policy_guards,
    )
    if target.shot == "Clip_02_first" and "尸场空间一次建立" in body:
        # The source section describes the whole multi-shot Clip and therefore
        # also contains the later CU, revival and complete-weapon states.  For
        # the physical S02A first frame those merged clauses are contradictory;
        # replace them with the actual ten-minutes-earlier state before provider
        # compilation instead of hoping a late negative prompt wins.
        contract["objective"] = "十分钟前：35mm低机位广角一次建立翻覆囚车、官道尸体、断刀封路与虎妖伪死的荒野死局"
        contract["subject"] = (
            "姜月初无血、空手、刚从尸堆侧躺撑起；裴长青相隔至少两个身位独自半跪；"
            "虎山神以虎头人身巨人形态在远后景水平倒地伪死"
        )
        contract["subject_slots"] = (
            "SLOT_1: CHAR_01/常态 -> 画左中景侧躺撑起，空手摸残损囚服；"
            "SLOT_2: CHAR_02/常态 -> 画右前景远处独自半跪，左臂扭曲重伤；"
            "SLOT_3: CHAR_04/常态 -> 上方远后景虎头人身巨躯水平倒地伪死"
        )
        contract["action"] = "姜月初刚醒并确认囚服；裴长青以一截断刀封住退路；虎山神保持倒地伪死"
        contract["composition"] = (
            "35mm低机位广角尸场建立镜，前中后景分层；姜月初与裴长青相隔至少两个身位，"
            "不贴坐、不对跪、不摆拍，所有角色只看戏内对象"
        )
        forbidden_preserve = re.compile(
            r"WEAPON_01|完整横刀|横刀站姿|面颊血污|被架起|带伤复生|傲慢捕食者姿态"
        )
        contract["preserve"] = [
            item for item in (contract.get("preserve") or [])
            if not forbidden_preserve.search(str(item))
        ] + [
            "状态唯一真值：CHAR_01无血空手刚醒；CHAR_02左臂重伤独自半跪；CHAR_04虎头人身水平倒地伪死",
            "仅一截断刀插地封路；完整横刀尚未入画",
        ]
        contract["exclude"] = list(dict.fromkeys([
            *(contract.get("exclude") or []),
            "完整横刀", "第二把刀", "双刀", "武器陈列",
            "虎山神站立", "虎山神复活", "四足普通老虎",
            "姜月初面颊血污", "姜月初持刀", "两人贴坐", "两人对跪",
        ]))
    if anchor_beat:
        still_motion = storyboard_motion_for_still(str(anchor_beat.get("video_prompt") or ""))
        beat_desc = str(anchor_beat.get("desc") or "")
        if anchor_beat.get("audience_only_reveal") and "盆底" in beat_desc:
            beat_desc = beat_desc.replace("盆底", "盆底外侧下表面", 1)
        beat_action = "；".join(filter(None, (
            beat_desc,
            still_motion,
        )))
        # A multi-sub-shot section carries a merged dramatic objective.  Once
        # this physical anchor is resolved, keeping that merged text leaks
        # actions from adjacent edit beats back into the provider prompt.
        # Replace it rather than append so the timed storyboard beat remains
        # the only action truth for this image.
        contract["objective"] = f"本锚只呈现 storyboard 子镜头：{beat_desc or beat_action}"
        contract["action"] = beat_action
        contract["composition"] = (
            f"本锚专属景别/机位：{anchor_beat.get('lens') or '继承 storyboard'}；"
            "继承同镜轴线、光位和身份，不合并前后子镜头的动作或景别"
        )
        excluded_objects = list(anchor_beat.get("excluded_objects") or [])
        excluded_object_aliases = list(anchor_beat.get("excluded_object_aliases") or [])
        if excluded_object_aliases:
            scene_clauses = [
                clause.strip() for clause in re.split(r"[；;]", str(contract.get("scene") or ""))
                if clause.strip()
            ]
            contract["scene"] = "；".join(
                clause for clause in scene_clauses
                if not any(alias and alias in clause for alias in excluded_object_aliases)
            )
            filtered_preserve: List[str] = []
            for item in contract.get("preserve") or []:
                clauses = [clause.strip() for clause in re.split(r"[；;]", str(item)) if clause.strip()]
                kept = [
                    clause for clause in clauses
                    if not any(alias and alias in clause for alias in excluded_object_aliases)
                ]
                if kept:
                    filtered_preserve.append("；".join(kept))
            contract["preserve"] = filtered_preserve
            contract["exclude"] = list(dict.fromkeys([
                *(contract.get("exclude") or []),
                *[f"{name}在本时点入画" for name in excluded_objects],
            ]))
        guards = list(contract.get("policy_guards") or [])
        if anchor_beat.get("audience_only_reveal"):
            guards.insert(0, (
                "观众独享信息铁律：本帧异常只允许出现在角色当前视线不可达的道具外侧、背面或下表面；"
                "角色不得看见、触发或对异常作知情反应；不得把异常画进角色可见的道具内腔/正面。"
                f"观众获得 `{anchor_beat.get('audience_knowledge')}`，角色仍保持 `{anchor_beat.get('character_knowledge')}`"
            ))
        current_state = str(anchor_beat.get("current_state") or "").strip()
        if current_state:
            guards.insert(0, f"本帧当前状态硬约束：{current_state}；不得使用同 Clip 后续状态替代")
        if excluded_objects:
            visible = "、".join(anchor_beat.get("visible_objects") or []) or "storyboard 当前明确可见实体"
            guards.insert(0, (
                f"定时子镜道具可见性铁律：当前只保留{visible}；"
                f"{ '、'.join(excluded_objects) }在本时点尚未入画，必须完全不出现在像素中"
            ))
        guards.insert(0, (
            "物理关键帧版式铁律：只生成一个连续相机画面；禁止分屏、三联画、多格漫画、拼贴、"
            "接触表或把跳切/蒙太奇的多个时刻同时画进一张图；剪辑变化只由视频阶段完成"
        ))
        guards.insert(0, (
            f"帧动作唯一真值：{anchor_beat.get('frame_role') or ('a' + str(anchor_beat.get('anchor_index')))} "
            f"@ {anchor_beat.get('at_sec')}s "
            f"只表现 `{anchor_beat.get('desc')}`；不得混入同一 Clip 的其它子镜头动作"
        ))
        if anchor_beat.get("faceless_insert"):
            excluded_tokens = [
                *(anchor_beat.get("excluded_names") or []),
                *_shot_character_refs(body),
            ]
            contract["subject"] = str(anchor_beat.get("desc") or "无人物物件插入镜")
            contract["subject_slots"] = ""
            contract["preserve"] = [
                item for item in (contract.get("preserve") or [])
                if not any(token and token in str(item) for token in excluded_tokens)
            ]
            contract["exclude"] = list(dict.fromkeys([
                *(contract.get("exclude") or []),
                "人物", "清晰人脸", "人体残件",
                *[f"{token}入画" for token in excluded_tokens if token],
            ]))
            guards = [
                guard for guard in guards
                if not any(marker in str(guard) for marker in (
                    "镜头为旁观者视角", "脸部机检可核验铁律", "手部/肢体归属铁律",
                    "源帧主体身份连续硬锁",
                ))
            ]
            guards.insert(0, (
                "本帧是无脸物件插入镜：只出现剧本指定旧物、空院与远景；"
                "所有具名人物及其脸、手臂、身体、衣装残件完全不入画"
            ))
        elif anchor_beat.get("detail_insert"):
            contract["subject"] = str(anchor_beat.get("desc") or "人物局部动作特写")
            contract["subject_slots"] = ""
            contract["exclude"] = list(dict.fromkeys([
                *(contract.get("exclude") or []),
                "人物脸部", "完整人物全身", "相邻子镜头动作",
            ]))
            guards = [
                guard for guard in guards
                if not any(marker in str(guard) for marker in (
                    "镜头为旁观者视角", "脸部机检可核验铁律",
                ))
            ]
            guards.insert(0, (
                "本帧是人物局部插入镜：只呈现 storyboard 指定的手/脚/道具接触细节；"
                "角色脸部和完整身体出画，肢体必须可追溯到同一角色且解剖、数量、接触点正确"
            ))
        elif anchor_beat.get("single_reaction"):
            focus = "、".join(anchor_beat.get("focus_names") or []) or "本锚焦点角色"
            excluded = "、".join(anchor_beat.get("excluded_names") or []) or "前一动作人物"
            focus_ids = set(anchor_beat.get("focus_ids") or [])
            excluded_tokens = [
                *(anchor_beat.get("excluded_names") or []),
                *[
                    cid for cid in _shot_character_refs(body)
                    if cid.split("/", 1)[0] not in focus_ids
                ],
            ]
            slot_parts = re.split(r"\s*；(?=SLOT_\d+\s*:)", str(contract.get("subject_slots") or ""))
            focus_slots = [
                part for part in slot_parts
                if any(cid in part for cid in focus_ids)
            ]
            if focus_slots:
                contract["subject_slots"] = "；".join(focus_slots)
                focus_descriptions = [
                    match.group(1).strip()
                    for part in focus_slots
                    if (match := re.search(r"区分锚点[：:]\s*(.+)$", part))
                ]
                contract["subject"] = "；".join(focus_descriptions) or focus
            preserve_focus: List[str] = []
            for item in contract.get("preserve") or []:
                clauses = [clause.strip() for clause in re.split(r"[；;]", str(item)) if clause.strip()]
                kept = [
                    clause for clause in clauses
                    if not any(token and token in clause for token in excluded_tokens)
                ]
                if kept:
                    preserve_focus.append("；".join(kept))
            contract["preserve"] = preserve_focus
            contract["exclude"] = list(dict.fromkeys([
                *(contract.get("exclude") or []),
                *[f"{token}入画" for token in excluded_tokens if token],
            ]))
            guards = [
                guard for guard in guards
                if not str(guard).startswith("源帧几何连续性硬锁：")
            ]
            guards.insert(0, (
                f"本锚是单人反应特写：清晰主体只保留{focus}；{excluded}及其手臂完全出画，"
                "前一子镜头的身体接触动作已结束，不得继续入画"
            ))
        contract["policy_guards"] = guards
    gaze_exclusions = camera_gaze_negatives_for(body) if any(
        "镜头为旁观者视角" in item for item in policy_guards
    ) else ""
    if gaze_exclusions:
        contract["exclude"] = list(dict.fromkeys([
            *(contract.get("exclude") or []),
            *normalize_exclusions(gaze_exclusions),
        ]))
    if target.variant_note:
        contract["objective"] = "；".join(filter(None, (
            str(contract.get("objective") or ""),
            str(target.variant_note),
        )))
    if target.mode in {"midframe", "tailframe"}:
        preserve = list(contract.get("preserve") or [])
        if anchor_beat.get("single_reaction"):
            preserve.append("源帧的角色身份、服装、场景几何、光位与轴线；前一子镜头接触动作不得延续")
        elif anchor_beat:
            preserve.append(
                "源帧的角色身份、服装、场景几何、光位、轴线，以及既有道具的结构、总数量和归属；"
                "只按本锚 storyboard 改变人物姿态、手握点、道具位置与接触状态"
            )
        else:
            preserve.append("源帧的角色身份、服装、站位、场景几何、光位、轴线、手握位置与道具接触点")
        if anchor_beat:
            anchor_guards = list(contract.get("policy_guards") or [])
            anchor_guards.insert(0, (
                "中锚动作状态替换铁律：源帧中的同一人物和同一组道具只改变到本锚新状态；"
                "不得同时保留旧姿态/旧位置又新增一套新姿态/新位置，不得复制人物、肢体或道具；"
                "道具总数量、拓扑与归属严格不变"
            ))
            contract["policy_guards"] = anchor_guards
        if has_weapon_body_contact(target):
            preserve.append("源帧既有武器接触点、伤口位置与入射角")
        contract["preserve"] = preserve
        role = "中段动作增量" if target.mode == "midframe" else "尾态动作/表情增量"
        contract["action"] = "；".join(filter(None, (str(contract.get("action") or ""), role)))
    if retry_guard:
        contract["objective"] = "；".join(filter(None, (
            retry_guard,
            str(contract.get("objective") or ""),
        )))
    payload = compile_image_prompt(contract, backend)
    experiment = image_prompt_experiment_context()
    if experiment:
        payload["experiment"] = experiment
    return payload


def compiled_request_receipt_path(root: Path, episode: str, target: Target) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.\-\u4e00-\u9fff]+", "_", f"{target.shot}_{Path(target.rel_path).stem}").strip("_")
    return root / "生产数据" / "compiled_image_requests" / episode / f"{safe}.json"


def write_compiled_request_receipt(
    root: Path,
    episode: str,
    target: Target,
    compiled: Mapping[str, Any],
    submitted_prompt: str,
) -> Path:
    latest_path = compiled_request_receipt_path(root, episode, target)
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    references = list(compiled.get("reference_inputs") or [])
    params = dict(compiled.get("request_params") or {})
    compiled_sha = str(compiled.get("compiled_request_sha256") or sha256_text(submitted_prompt))
    payload = {
        "kind": "n2d_compiled_image_request_receipt",
        "version": 1,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "episode": episode,
        "shot": target.shot,
        "target": target.rel_path,
        "compiler": dict(compiled),
        "actual_submit_prompt": submitted_prompt,
        "actual_submit_prompt_sha256": sha256_text(submitted_prompt),
        "actual_submit_prompt_chars": len(submitted_prompt),
        "actual_submit_request": {
            "prompt": submitted_prompt,
            "negative_prompt": str(compiled.get("negative_prompt") or ""),
            "request_params": params,
            "reference_inputs": references,
        },
        "request_params_sha256": sha256_text(json.dumps(params, ensure_ascii=False, sort_keys=True, separators=(",", ":"))),
        "reference_inputs_sha256": sha256_text(json.dumps(references, ensure_ascii=False, sort_keys=True, separators=(",", ":"))),
    }
    backend = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(compiled.get("backend") or "image")).strip("_")
    immutable = latest_path.parent / "history" / f"{latest_path.stem}_{backend}_{compiled_sha[:16]}.json"
    immutable.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    for path in (immutable, latest_path):
        tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    return immutable


def build_codex_prompt(
    root: Path,
    episode: str,
    target: Target,
    temp_path: Path,
    seed: str,
    reference_bundle: Optional[Dict[str, Any]] = None,
    reference_manifest: Optional[Path] = None,
    retry_guidance: str = "",
    compiled_request: Optional[Mapping[str, Any]] = None,
) -> str:
    fallback_references: Sequence[Mapping[str, Any]] = list(
        (reference_bundle or {}).get("cli_image_inputs") or
        (reference_bundle or {}).get("items") or []
    )
    compiled = dict(compiled_request or compile_target_image_request(
        root,
        episode,
        target,
        fallback_references,
        backend="codex",
        retry_guidance=retry_guidance,
    ))
    lint = lint_compiled_image_prompt(compiled)
    if lint.get("errors"):
        raise ValueError("compiled image prompt invalid: " + ", ".join(lint["errors"]))
    params = json.dumps(compiled.get("request_params") or {}, ensure_ascii=False, sort_keys=True)
    negative = str(compiled.get("negative_prompt") or "").strip()
    negative_block = f"\n独立负向字段（仅后端支持时提交）：\n{negative}\n" if negative else ""
    return f"""为 N2D 生成且只生成 1 张正式 PNG。必须调用内置 image_generation/image_gen；不得用 Python、SVG、canvas、纯色图或占位图伪造。

执行参数：
- task_type={compiled.get('task_type')}; mode={compiled.get('mode')}; model={compiled.get('model') or '本次已选图片模型'}
- request_params={params}
- 输出由外层 runner 从事件流解码到：{temp_path}
- 本次 `--image` 附件及其顺序就是 compiler 中的图1/图2…，不得交换主体归属。

模型实际执行 prompt：
{compiled.get('prompt') or ''}
{negative_block}
完成后只用一句话说明完成。无法生成真实 PNG 时直接报失败，不搜索文件系统、不创建替代文件。
"""


def build_codex_command(repo: Path, prompt: str, reference_inputs: Sequence[Dict[str, Any]]) -> List[str]:
    cmd = ["codex", "exec"]
    model = os.environ.get("N2D_CODEX_MODEL")
    if model:
        cmd.extend(["-m", model])
    image_paths = [reference_input_attachment_path(item) for item in reference_inputs if reference_input_attachment_path(item)]
    if image_paths:
        cmd.append("--image")
        cmd.extend(image_paths)
    cmd.extend(["--json", "--enable", "image_generation", "-C", str(repo), prompt])
    return cmd


TRANSIENT_CODEX_FAILURE_MARKERS = (
    "tls handshake eof",
    "stream disconnected",
    "failed to connect to websocket",
    "error sending request",
    "http/request failed",
    "transport channel closed",
    "timeout waiting for child process",
)


def transient_codex_transport_failure(proc: subprocess.CompletedProcess[str]) -> bool:
    if proc.returncode == 0:
        return False
    text = f"{proc.stderr or ''}\n{proc.stdout or ''}".lower()
    return any(marker in text for marker in TRANSIENT_CODEX_FAILURE_MARKERS)


def run_codex(
    repo: Path,
    prompt: str,
    timeout_sec: Optional[float],
    reference_inputs: Sequence[Dict[str, Any]],
) -> subprocess.CompletedProcess[str]:
    cmd = build_codex_command(repo, prompt, reference_inputs)
    attempts = max(1, int(os.environ.get("N2D_CODEX_TRANSPORT_RETRIES", "3")))
    delay_sec = max(0.0, float(os.environ.get("N2D_CODEX_TRANSPORT_RETRY_DELAY", "5")))
    proc: subprocess.CompletedProcess[str]
    for attempt in range(1, attempts + 1):
        try:
            proc = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired:
            if attempt >= attempts:
                raise
            print(
                f"[retry] Codex image generation timed out on attempt {attempt}/{attempts}; "
                "retrying same target",
                file=sys.stderr,
            )
            if delay_sec:
                time.sleep(delay_sec * attempt)
            continue
        image_failure = image_generation_failure_detail(proc.stdout or "")
        retryable_image_failure = (
            proc.returncode == 0
            and bool(image_failure)
            and transient_codex_image_failure(image_failure)
        )
        if (
            not transient_codex_transport_failure(proc)
            and not retryable_image_failure
        ) or attempt >= attempts:
            return proc
        if retryable_image_failure:
            print(
                f"[retry] Codex image generation transient failure on attempt {attempt}/{attempts}: "
                f"{image_failure[:300]}; retrying same target",
                file=sys.stderr,
            )
        else:
            print(
                f"[retry] Codex transport failure on attempt {attempt}/{attempts}; retrying",
                file=sys.stderr,
            )
        if delay_sec:
            time.sleep(delay_sec * attempt)
    return proc



def format_codex_failure(proc: subprocess.CompletedProcess[str]) -> str:
    """Keep both stderr and JSONL stdout because Codex often puts API errors in stdout."""
    parts: List[str] = []
    stderr = (proc.stderr or "").strip()
    stdout = (proc.stdout or "").strip()
    if stderr:
        parts.append(f"stderr={stderr[-2000:]}")
    if stdout:
        parts.append(f"stdout={stdout[-4000:]}")
    detail = " | ".join(parts) if parts else "no stdout/stderr"
    return f"codex exit {proc.returncode}: {detail}"


def decode_image_event(stdout: str, out_path: Path) -> bool:
    """Decode Codex CLI's built-in image_generation result from JSONL output.

    The built-in tool returns the PNG as base64 in an ``image_generation_end``
    event. In ``codex exec`` this event is reliably persisted to the session
    JSONL; it may not be mirrored to stdout, so stdout is used first and the
    session file is used as the fallback.
    """
    thread_id = ""
    payload = _image_payload_from_jsonl(stdout)
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started" and isinstance(event.get("thread_id"), str):
            thread_id = event["thread_id"]
            break
    if not payload and thread_id:
        session_path = _codex_session_path(thread_id)
        if session_path:
            payload = _image_payload_from_jsonl(session_path.read_text(encoding="utf-8", errors="ignore"))
    if not payload:
        return False
    return _write_image_payload(payload, out_path)


TRANSIENT_IMAGE_FAILURE_MARKERS = (
    "network error",
    "network failure",
    "connection reset",
    "connection refused",
    "stream disconnected",
    "timed out",
    "timeout",
    "rate limit",
    "temporarily unavailable",
    "internal server error",
    "网络错误",
    "网络异常",
    "连接中断",
    "连接失败",
    "请求超时",
    "服务暂时不可用",
)


def transient_codex_image_failure(detail: str) -> bool:
    text = str(detail or "").lower()
    return (
        any(marker in text for marker in TRANSIENT_IMAGE_FAILURE_MARKERS)
        or ("网络" in text and any(token in text for token in ("失败", "错误", "异常", "超时", "中断")))
        or re.search(r"\b(?:http\s*)?5\d\d\b", text) is not None
    )


def image_generation_failure_detail(stdout: str) -> str:
    """Return a concise failed-image event reason from stdout/session JSONL.

    Codex CLI can exit zero even when the nested image tool ends with
    ``image_generation_end: failed``.  The event itself currently carries no
    error field, while the final agent message records the useful transport
    reason.  Inspect the persisted session as well as stdout so the caller can
    distinguish a retryable backend outage from a missing-result adapter bug.
    """
    texts = [stdout]
    thread_id = _thread_id_from_stdout(stdout)
    if thread_id:
        session_path = _codex_session_path(thread_id)
        if session_path:
            texts.append(session_path.read_text(encoding="utf-8", errors="ignore"))
    best = ""
    for text in texts:
        detail = _image_failure_from_jsonl(text)
        if detail and detail != "image_generation_end status=failed":
            best = detail
        elif detail and not best:
            best = detail
    return best


def _thread_id_from_stdout(stdout: str) -> str:
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started" and isinstance(event.get("thread_id"), str):
            return event["thread_id"]
    return ""


def _image_failure_from_jsonl(text: str) -> str:
    failed = False
    messages: List[str] = []
    final_failures: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = event.get("payload") if isinstance(event, dict) else None
        if not isinstance(payload, dict):
            continue
        if payload.get("type") == "image_generation_end" and payload.get("status") == "failed":
            failed = True
            error = payload.get("error")
            if isinstance(error, str) and error.strip():
                messages.append(error.strip())
        if payload.get("type") == "agent_message":
            message = payload.get("message")
            if isinstance(message, str) and message.strip():
                messages.append(message.strip())
                if payload.get("phase") == "final_answer" and re.search(
                    r"失败|无法|不能|未生成|fail|error|unable|cannot",
                    message,
                    re.I,
                ):
                    final_failures.append(message.strip())
    if not failed:
        return final_failures[-1] if final_failures else ""
    for message in reversed(messages):
        lowered = message.lower()
        if any(token in lowered for token in ("fail", "error", "失败", "错误", "异常", "超时")):
            return message
    return "image_generation_end status=failed"


def _image_payload_from_jsonl(text: str) -> str:
    payload = ""
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        data = event.get("payload") if isinstance(event, dict) else None
        if not isinstance(data, dict) or data.get("type") != "image_generation_end":
            continue
        result = data.get("result")
        if isinstance(result, str) and result.strip():
            payload = result.strip()
    return payload


def _codex_session_path(thread_id: str) -> Optional[Path]:
    sessions_dir = Path.home() / ".codex" / "sessions"
    if not sessions_dir.is_dir():
        return None
    matches = list(sessions_dir.glob(f"**/*{thread_id}.jsonl"))
    if not matches:
        return None
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]


def _write_image_payload(payload: str, out_path: Path) -> bool:
    if not payload:
        return False
    if payload.startswith("data:"):
        payload = payload.split(",", 1)[-1]
    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(raw)
    return png_valid(out_path)


def archive_existing(root: Path, rel_path: str, task_id: str) -> Optional[Path]:
    final = root / rel_path
    if not final.exists():
        return None
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = root / "废料" / "出图" / rel_path.replace("出图/", "").rsplit("/", 1)[0] / f"codex_rerun_{task_id}_{stamp}"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / final.name
    shutil.copy2(final, archive_path)
    return archive_path


def record_event(
    root: Path,
    episode: str,
    target: Target,
    *,
    status: str,
    duration_sec: float,
    task_id: str,
    seed: str,
    temp_path: Path,
    archive_path: Optional[Path] = None,
    reference_manifest: Optional[Path] = None,
    reference_inputs: Optional[Sequence[Dict[str, Any]]] = None,
    submitted_prompt: str = "",
    compiled_request: Optional[Mapping[str, Any]] = None,
    compiled_receipt: Optional[Path] = None,
    error: str = "",
) -> None:
    event = "redraw" if os.environ.get("N2D_REASON") == "rerun" else "generation"
    reason = f"{task_id or 'codex-image'} Codex image_generation 真实重出 {target.shot}，禁止本地贴脸修复"
    category = "face_consistency" if event == "redraw" else ""
    cmd = [
        sys.executable,
        str(repo_root() / DASHBOARD),
        "record",
        str(root),
        "--episode",
        episode,
        "--stage",
        "image",
        "--event",
        event,
        "--asset",
        target.rel_path,
        "--status",
        status,
        "--provider",
        "Codex",
        "--duration-sec",
        f"{duration_sec:.3f}",
        "--unit",
        "credits",
        "--meta",
        f"mode=codex_exec_image_generation_{target.mode}",
        "--meta",
        f"codex_model={os.environ.get('N2D_CODEX_MODEL') or 'default'}",
        "--meta",
        f"task={task_id}",
        "--meta",
        f"shot={target.shot}",
        "--meta",
        f"logical_seed={seed}",
        "--meta",
        "seed_effective=unsupported",
        "--meta",
        "seed_degrade=codex_exec_no_seed_api",
        "--meta",
        f"temp_output={temp_path}",
        "--meta",
        f"source={SOURCE}",
    ]
    reference_inputs = list(reference_inputs or [])
    compiled_request = dict(compiled_request or {})
    experiment = compiled_request.get("experiment") if isinstance(compiled_request.get("experiment"), Mapping) else {}
    image_model = str(compiled_request.get("model") or os.environ.get("N2D_IMAGE_MODEL") or "GPT Image 2")
    channel = str(compiled_request.get("channel") or "Codex CLI")
    prompt_sha = sha256_text(submitted_prompt) if submitted_prompt else sha256_text(str(compiled_request.get("prompt") or ""))
    source_prompt_sha = sha256_text(target.section.body)
    compiled_sha = str(compiled_request.get("compiled_request_sha256") or "")
    ref_sha = reference_bundle_hash(reference_manifest, reference_inputs)
    route_hash = sha256_text(f"codex|{image_model}|{channel}|{target.mode}|{target.shot}|{target.rel_path}")
    settings_sha = optional_file_sha256(root / "_设置.md")
    identity_registry_sha = optional_file_sha256(root / "出图" / "共享" / "identity_registry.json")
    asset_registry_sha = optional_file_sha256(root / "出图" / "共享" / "asset_registry.json")
    artifact_path = root / target.rel_path
    artifact_sha = optional_file_sha256(artifact_path) or optional_file_sha256(temp_path)
    adapter_version = f"codex_image_runner.py@{optional_file_sha256(Path(__file__))[:12]}"
    qc_version = f"image_qc.py@{optional_file_sha256(repo_root() / IMAGE_QC)[:12]}"
    backend_version = codex_backend_version()
    input_fingerprint = sha256_text(json.dumps({
        "asset": target.rel_path,
        "mode": target.mode,
        "prompt_sha256": prompt_sha,
        "source_prompt_section_sha256": source_prompt_sha,
        "compiled_request_sha256": compiled_sha,
        "reference_bundle_sha256": ref_sha,
        "route_hash": route_hash,
        "settings_sha256": settings_sha,
        "identity_registry_sha256": identity_registry_sha,
        "asset_registry_sha256": asset_registry_sha,
        "logical_seed": seed,
    }, ensure_ascii=False, sort_keys=True))
    recipe_hash = sha256_text(json.dumps({
        "input_fingerprint": input_fingerprint,
        "artifact_sha256": artifact_sha,
        "backend_version": backend_version,
        "model_version": image_model,
    }, ensure_ascii=False, sort_keys=True))
    capability_path = root / "生产数据" / "image_backend_capabilities" / "codex.json"
    capability_id = f"{capability_path.relative_to(root)}#{file_sha256(capability_path)[:12]}" if capability_path.is_file() else "codex-refresh-missing"
    actual_inputs = [reference_input_actual_path(item) for item in reference_inputs if reference_input_actual_path(item)]
    cmd.extend([
        "--meta", f"model={image_model}",
        "--meta", f"model_version={image_model}",
        "--meta", f"channel={channel}",
        "--meta", f"route_hash={route_hash}",
        "--meta", f"capability_evidence_id={capability_id}",
        "--meta", f"recipe_hash={recipe_hash}",
        "--meta", f"prompt_sha256={prompt_sha}",
        "--meta", f"actual_submit_prompt_sha256={prompt_sha}",
        "--meta", f"source_prompt_section_sha256={source_prompt_sha}",
        "--meta", f"prompt_compiler_kind={compiled_request.get('kind') or ''}",
        "--meta", f"prompt_compiler_version={compiled_request.get('version') or ''}",
        "--meta", f"prompt_profile_version={compiled_request.get('profile_version') or ''}",
        "--meta", f"prompt_profile={compiled_request.get('profile') or ''}",
        "--meta", f"prompt_task_type={compiled_request.get('task_type') or ''}",
        "--meta", f"negative_strategy={compiled_request.get('negative_strategy') or ''}",
        "--meta", f"source_contract_sha256={compiled_request.get('source_contract_sha256') or ''}",
        "--meta", f"execution_context_sha256={compiled_request.get('execution_context_sha256') or ''}",
        "--meta", f"compiled_request_sha256={compiled_sha}",
        "--meta", f"compiled_prompt_chars={(compiled_request.get('metrics') or {}).get('prompt_chars') or 0}",
        "--meta", f"compiled_estimated_text_tokens={(compiled_request.get('metrics') or {}).get('estimated_text_tokens') or 0}",
        "--meta", f"image_prompt_experiment_id={experiment.get('experiment_id') or ''}",
        "--meta", f"image_prompt_variant={experiment.get('variant') or ''}",
        "--meta", f"reference_bundle_sha256={ref_sha}",
        "--meta", f"backend_version={backend_version}",
        "--meta", f"input_fingerprint={input_fingerprint}",
        "--meta", f"settings_sha256={settings_sha}",
        "--meta", f"identity_registry_sha256={identity_registry_sha}",
        "--meta", f"asset_registry_sha256={asset_registry_sha}",
        "--meta", f"artifact_sha256={artifact_sha}",
        "--meta", f"adapter_version={adapter_version}",
        "--meta", f"qc_version={qc_version}",
        "--meta", "quality_tier=project_default",
        "--meta", f"actual_image_inputs={'|'.join(actual_inputs) if actual_inputs else 'none'}",
        "--meta", "seed_effective=false",
        "--meta", "seed_support=unsupported_no_seed_api",
    ])
    if reference_manifest:
        cmd.extend(["--meta", f"reference_bundle={reference_manifest}"])
        cmd.extend(["--meta", f"reference_manifest={reference_manifest}"])
    if compiled_receipt:
        try:
            receipt_rel = compiled_receipt.relative_to(root)
        except ValueError:
            receipt_rel = compiled_receipt
        cmd.extend(["--meta", f"compiled_request_receipt={receipt_rel}"])
    cmd.extend(["--meta", "reference_input_mode=codex_exec_image_flags"])
    cmd.extend(["--meta", f"reference_input_count={len(reference_inputs)}"])
    if reference_inputs:
        rels = "|".join(reference_input_actual_path(item) for item in reference_inputs if reference_input_actual_path(item))
        cmd.extend(["--meta", f"reference_input_paths={rels}"])
    if event == "redraw":
        cmd.extend(["--redraw-reason", reason, "--redraw-category", category])
    if target.mode == "midframe" and status == "pass":
        source_image = selected_relay_source_path(reference_inputs)
        cmd.extend(["--meta", "self_check=pass", "--meta", "midframe_role=between_first_and_end"])
        if source_image:
            cmd.extend(["--meta", f"source_image={source_image}"])
    if archive_path:
        cmd.extend(["--meta", f"archived_previous={archive_path}"])
    if error:
        cmd.extend(["--meta", f"error={error[:500]}"])
    subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def run_image_gate(root: Path, episode: str, stage: str = "image") -> bool:
    python = image_qc_python() if stage == "image" else sys.executable
    cmd = [
        python,
        str(repo_root() / DASHBOARD),
        "gate",
        str(root),
        episode,
        "--stage",
        stage,
    ]
    proc = subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode == 0:
        print(f"[gate] {stage} gate passed for {episode}")
        return True
    print(proc.stdout, end="", file=sys.stderr)
    print(proc.stderr, end="", file=sys.stderr)
    print(f"[gate] {stage} gate blocked for {episode}", file=sys.stderr)
    return False


def run_shared_asset_preflight(root: Path, episode: str) -> bool:
    """Pre-spend gate for bootstrap shared assets.

    The regular ``image_preflight`` deliberately requires landed core
    multi-view pixels and their current-pixel receipts, so calling it before
    the first turnaround is generated would deadlock bootstrap.  This narrower
    non-waivable gate checks the two prerequisites that must already exist:
    project compliance and every external reference requesting backend use.
    """
    reference_issues = reference_manifest_generation_issues(root)
    if reference_issues:
        print(
            "[gate] shared_asset_preflight blocked — external visual references are not generation-eligible",
            file=sys.stderr,
        )
        for issue in reference_issues[:30]:
            print(f"[gate] - {issue}", file=sys.stderr)
        if len(reference_issues) > 30:
            print(f"[gate] - ... plus {len(reference_issues) - 30} more reference issues", file=sys.stderr)
        return False

    cmd = [
        sys.executable,
        str(repo_root() / COMPLIANCE),
        str(root),
        episode,
        "--check",
        "--stage",
        "image",
        "--json",
    ]
    proc = subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode == 0:
        print(f"[gate] shared_asset_preflight passed for {episode}")
        return True
    print(proc.stdout, end="", file=sys.stderr)
    print(proc.stderr, end="", file=sys.stderr)
    print(
        f"[gate] shared_asset_preflight blocked for {episode} — fix compliance/reference rights before paid shared generation",
        file=sys.stderr,
    )
    return False


def record_waiver(root: Path, episode: str, stage: str, waiver: str, reason: str) -> None:
    """Log an escape-hatch / gate-bypass as a dashboard waiver event (执行时松动留痕).

    Best-effort: never let waiver bookkeeping abort generation. The point is that
    relaxing a gate becomes auditable on the dashboard, not silent.
    """
    cmd = [
        sys.executable,
        str(repo_root() / DASHBOARD),
        "waiver",
        str(root),
        "--episode", episode,
        "--stage", stage,
        "--waiver", waiver,
        "--reason", reason,
        "--source", "n2d-image/scripts/codex_image_runner.py",
        "--no-build",
    ]
    proc = subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        print(f"[waiver] failed to record {waiver} for {episode}: {proc.stderr.strip()}", file=sys.stderr)
    else:
        print(f"[waiver] recorded {waiver} for {episode} (stage={stage})")


def episode_png_key(rel_path: str, episode: str) -> str:
    text = str(rel_path or "").strip().replace("\\", "/")
    prefix = f"出图/{episode}/"
    if text.startswith(prefix):
        return text[len(prefix):]
    marker = "/图片/"
    if marker in text:
        return "图片/" + text.rsplit(marker, 1)[-1]
    if text.startswith("图片/"):
        return text
    if text.endswith(".png") and "/" not in text:
        return "图片/" + text
    return text


def run_target_image_qc(root: Path, episode: str, target: Target) -> bool:
    """Run image_qc after one landed shot and fail only this target on hard evidence gaps."""
    python = image_qc_python()
    if python != sys.executable:
        print(f"[image_qc] using {python}")
    env = os.environ.copy()
    # Per-target QC runs after every generated PNG. Avoid auto-attaching the
    # optional VLM backend for the whole episode on each target; explicit user
    # configuration still wins.
    env.setdefault("N2D_VLM_CMD", "off")
    cmd = [
        python,
        str(repo_root() / IMAGE_QC),
        str(root),
        episode,
    ]
    proc = subprocess.run(
        cmd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    if proc.returncode != 0:
        print(proc.stdout, end="", file=sys.stderr)
        print(proc.stderr, end="", file=sys.stderr)
        print(f"[image_qc] failed to run for {target.shot}", file=sys.stderr)
        return False

    report = root / "生产数据" / "image_qc" / episode / f"image_qc_{episode}.json"
    try:
        payload = json.loads(report.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[image_qc] missing/unreadable report for {target.shot}: {exc}", file=sys.stderr)
        return False

    env = payload.get("qc_environment") or {}
    precision = str(env.get("precision_level") or "")
    target_key = episode_png_key(target.rel_path, episode)
    problems: List[str] = []
    executor_visual_rejection = latest_hash_bound_executor_visual_rejection(root, target)
    if executor_visual_rejection:
        problems.append("executor_visual_rejection")
    if precision != "full":
        problems.append(f"precision={precision or 'unknown'}")

    coverage = payload.get("face_reference_coverage") or {}
    for row in coverage.get("missing") or []:
        if episode_png_key(str(row.get("png") or ""), episode) == target_key:
            problems.append(f"face_reference_coverage:{row.get('reason') or 'missing'}")

    checks = payload.get("checks") or {}
    target_blocks = {
        # Character-shot face coverage is enforced by face_reference_coverage,
        # which knows whether the landed PNG is expected to contain a character.
        # A generic face:noface row is normal for prop/scene inserts and must not
        # stop empty establishing/detail shots.
        # Under B14, WARN/UNVERIFIABLE means "machine cannot sign this image",
        # so the runner pauses before acceptance/next-image advancement.  This
        # is not a claim that a heuristic proved the pixels wrong; it forces the
        # required current-pixel visual adjudication instead of auto-passing.
        "face": {"block", "warn", "unverifiable"},
        "hair": {"block", "warn"},
        "outfit": {"block", "warn"},
    }
    for check_name, blocked_verdicts in target_blocks.items():
        for row in (checks.get(check_name) or {}).get("shots") or []:
            if episode_png_key(str(row.get("png") or ""), episode) != target_key:
                continue
            verdict = str(row.get("verdict") or "")
            if verdict in blocked_verdicts:
                score = row.get("score")
                floor = row.get("floor")
                suffix = f":{verdict}"
                if score is not None and floor is not None:
                    suffix += f"(score={score},floor={floor})"
                problems.append(f"{check_name}{suffix}")

    # Registered high-risk props/VFX have a current-pixel comparison queue.
    # A face-consistent frame can still be narratively wrong (for example one
    # glowing tiger eye where the shot contract requires two).  Do not advance
    # until every target bound to this exact PNG has a current-hash visual
    # confirmation; the confirmation helper invalidates stale rows on redraw.
    prop_review = payload.get("prop_shape_review") or {}
    for row in prop_review.get("targets") or []:
        if episode_png_key(str(row.get("png") or ""), episode) != target_key:
            continue
        if not row.get("confirmed"):
            asset = str(row.get("asset") or row.get("asset_name") or "registered_asset")
            problems.append(f"prop_shape_review:{asset}:unconfirmed_current_pixels")

    clip_display = target.clip.replace("_", " ")
    for finding in (payload.get("lint") or {}).get("findings") or []:
        if str(finding.get("level") or "") != "block":
            continue
        msg = str(finding.get("msg") or "")
        if target.clip in msg or clip_display in msg:
            problems.append(f"prompt:{finding.get('code') or 'block'}")

    if problems:
        print(f"[image_qc] {target.shot} blocked: {', '.join(dict.fromkeys(problems))}", file=sys.stderr)
        return False
    print(f"[image_qc] {target.shot} target gate passed")
    return True


def run_target_repair_preflight(root: Path, episode: str, target: Target) -> bool:
    """Allow one proven-bad current PNG to enter the paid redraw loop.

    The episode-wide ``image_preflight`` deliberately blocks when current
    pixels fail QC.  That is correct for advancing production but circular for
    repairing the exact failed PNG.  This target-scoped preflight is not a
    waiver: it requires a fresh full-precision report, binds the rejected
    current pixel hash and its concrete face/hair/outfit/coverage findings,
    then writes a B14 pre-generation receipt.  Shared/reference and compiled
    request gates still run normally before submission, and post-generation
    target QC remains mandatory.
    """
    report = root / "生产数据" / "image_qc" / episode / f"image_qc_{episode}.json"
    final = root / target.rel_path
    if not png_valid(final):
        print(f"[gate] repair-redraw requires an existing valid PNG: {target.rel_path}", file=sys.stderr)
        return False
    try:
        payload = json.loads(report.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[gate] repair-redraw requires readable image_qc: {exc}", file=sys.stderr)
        return False
    qc_env = payload.get("qc_environment") if isinstance(payload.get("qc_environment"), Mapping) else {}
    if str(qc_env.get("precision_level") or "") != "full":
        print("[gate] repair-redraw requires full-precision image_qc", file=sys.stderr)
        return False

    target_key = episode_png_key(target.rel_path, episode)
    problems: List[str] = []
    executor_visual_rejection = latest_hash_bound_executor_visual_rejection(root, target)
    if executor_visual_rejection:
        problems.append("executor_visual_rejection")
    coverage = payload.get("face_reference_coverage") if isinstance(payload.get("face_reference_coverage"), Mapping) else {}
    for row in coverage.get("missing") or []:
        if episode_png_key(str(row.get("png") or ""), episode) == target_key:
            problems.append(f"face_reference_coverage:{row.get('reason') or 'missing'}")
    checks = payload.get("checks") if isinstance(payload.get("checks"), Mapping) else {}
    for check_name in ("face", "hair", "outfit"):
        check = checks.get(check_name) if isinstance(checks.get(check_name), Mapping) else {}
        for row in check.get("shots") or []:
            if episode_png_key(str(row.get("png") or ""), episode) != target_key:
                continue
            verdict = str(row.get("verdict") or "")
            if verdict in {"block", "warn", "unverifiable"}:
                problems.append(f"{check_name}:{verdict}")
    problems = list(dict.fromkeys(problems))
    if not problems:
        print(
            f"[gate] repair-redraw refused: current full QC/current-pixel review has no repair failure for {target.rel_path}",
            file=sys.stderr,
        )
        return False

    receipt_dir = root / "生产数据" / "image_preflight_receipts" / episode
    receipt_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
    receipt = receipt_dir / f"{Path(target.rel_path).stem}__repair_{stamp}.json"
    receipt.write_text(json.dumps({
        "kind": "n2d_single_image_consistency_preflight",
        "schema_version": 1,
        "created_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "episode": episode,
        "clip": target.clip,
        "target": target.rel_path,
        "mode": "full_qc_targeted_repair",
        "status": "passed_for_single_target_repair",
        "review_contract": "B14_pre_generation_consistency",
        "current_target_sha256": optional_file_sha256(final),
        "image_qc_report": str(report.relative_to(root)),
        "image_qc_report_sha256": optional_file_sha256(report),
        "repair_findings": problems,
        "preflight_checks": {
            "current_target_exists_and_decodes": True,
            "current_target_sha_bound": True,
            "full_precision_qc": True,
            "target_has_concrete_machine_or_current_pixel_failure": True,
            "single_target_only": True,
        },
        "post_generation_required": [
            "full_machine_qc",
            "canonical_face_and_current_output_side_by_side_original_pixel_review",
            "current_output_sha_bound_qa_receipt",
        ],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[gate] B14 targeted repair preflight passed: {receipt}")
    return True


def target_qc_retry_guidance(root: Path, episode: str, target: Target) -> str:
    """Convert a previous per-target QC block into prompt guidance for a force rerun."""
    report = root / "生产数据" / "image_qc" / episode / f"image_qc_{episode}.json"
    try:
        payload = json.loads(report.read_text(encoding="utf-8"))
    except Exception:
        payload = {}

    target_key = episode_png_key(target.rel_path, episode)
    problems: List[str] = []
    executor_visual_rejection = latest_hash_bound_executor_visual_rejection(root, target)
    if executor_visual_rejection:
        problems.append("executor_visual_rejection")

    coverage = payload.get("face_reference_coverage") or {}
    for row in coverage.get("missing") or []:
        if episode_png_key(str(row.get("png") or ""), episode) == target_key:
            reason = str(row.get("reason") or "missing").strip()
            problems.append(f"face_reference_coverage:{reason}")

    prop_targets: List[Dict[str, Any]] = []
    prop_shape = payload.get("prop_shape_review") or {}
    for row in prop_shape.get("targets") or []:
        if not isinstance(row, dict):
            continue
        if row.get("confirmed"):
            continue
        if episode_png_key(str(row.get("png") or ""), episode) != target_key:
            continue
        prop_targets.append(row)
        asset = str(row.get("asset") or row.get("asset_name") or "registered_prop").strip()
        problems.append(f"prop_shape_review:{asset}")

    checks = payload.get("checks") or {}
    for check_name in ("face", "hair", "outfit"):
        for row in (checks.get(check_name) or {}).get("shots") or []:
            if episode_png_key(str(row.get("png") or ""), episode) != target_key:
                continue
            verdict = str(row.get("verdict") or "")
            if verdict != "block" and not (check_name == "face" and verdict == "warn"):
                continue
            score = row.get("score")
            floor = row.get("floor")
            suffix = f"{check_name}:{verdict}"
            if score is not None and floor is not None:
                suffix += f"(score={score},floor={floor})"
            problems.append(suffix)

    clip_display = target.clip.replace("_", " ")
    for finding in (payload.get("lint") or {}).get("findings") or []:
        if str(finding.get("level") or "") != "block":
            continue
        msg = str(finding.get("msg") or "")
        if target.clip in msg or clip_display in msg:
            problems.append(f"prompt:{finding.get('code') or 'block'}")

    problems = list(dict.fromkeys(problems))
    if not problems:
        return ""

    has_face_problem = any(p.startswith("face") for p in problems)
    body = str(getattr(target.section, "body", "") or "")
    has_beast_demon = "CHAR_05" in body or "青面郎君" in body or "狼妖" in body
    lines = [
        "QC 重抽纠偏：",
        "- 本目标上一次生成未通过目标级 QC："
        + "、".join(problems)
        + "。本次是强制重抽，必须优先修复这些失败项。",
    ]
    if executor_visual_rejection:
        lines.append(
            "- 上一次当前像素实际目视拒收原因："
            + re.sub(r"\s+", " ", executor_visual_rejection).strip()[:700]
        )
    if has_face_problem:
        lines.append(
            "- face:block/warn 修复：主检人物必须给出可比对的眼鼻嘴三角区和脸部轮廓，"
            "优先用 45°/三分之二侧脸或清楚过肩回头；不得让头发、暗影、烟雾、背影、极小脸或侧后脑勺规避身份核验。"
        )
        lines.append(
            "- face_verdict_warn 修复：这通常表示脸已可见但不够像或不够大。"
            "主检角色脸部应更接近脸锚参考的脸型、眉眼、鼻口比例和发际线，"
            "脸部在画面中占比略增，改为侧前 45°/三分之二侧脸；不要只给纯侧脸、低头脸或过小脸。"
        )
    if has_beast_demon:
        lines.append(
            "- 妖物身份修复：青面郎君/狼妖脸部必须保持对应野兽狼首结构；"
            "不要画成人类俊脸。若有狼妖群，只保留后景剪影或侧背辅助，不要生成多个与 CHAR_05 竞争的清晰主妖脸。"
        )
    if any(p.startswith("hair") for p in problems):
        lines.append("- hair:block 修复：发型、发髻、发际线和头发轮廓必须回到对应角色脸锚/半身参考。")
    if any(p.startswith("outfit") for p in problems):
        lines.append("- outfit:block 修复：服装剪影、领口、袖口、腰带、纹样、主色和关键配饰必须回到对应角色/道具参考。")
    if prop_targets:
        lines.append(
            "- prop_shape_review 修复：本镜上次登记道具需要人工形状确认；重抽必须让需要出场的登记道具清楚可辨，"
            "外形、材质、数量和时代感以附件/registry 为准，不要用暗影、极远景、半截遮挡或模糊来逃避检查。"
        )
        for row in prop_targets[:6]:
            asset = str(row.get("asset") or "registered_prop").strip()
            name = str(row.get("asset_name") or "").strip()
            ref = str(row.get("ref") or "").strip()
            forbidden = "、".join(str(x) for x in (row.get("must_not_have") or []) if str(x).strip())
            suffix = f"；禁：{forbidden}" if forbidden else ""
            label = f"{asset}（{name}）" if name else asset
            lines.append(f"  - {label}: 按参考 `{ref}` 的结构与旧化材质生成{suffix}。")
    lines.append("- 不要降低画质或缩小主体来逃避 QC；必须清晰、高分辨率、无水印、无字幕、无 UI。")
    return "\n".join(lines)


def latest_hash_bound_executor_visual_rejection(root: Path, target: Target) -> str:
    """Return the latest actual-pixel rejection for the exact current PNG.

    Machine QC can pass while a visual reviewer catches continuity errors such
    as a missing registered prop.  Force-rerunning the same prompt without that
    finding wastes another paid attempt.  Consume only a rejection bound to
    the current artifact SHA and explicitly labelled ``executor_visual``.
    """
    path = root / "生产数据" / "production_events.jsonl"
    final = root / target.rel_path
    current_sha = optional_file_sha256(final) if final.is_file() else ""
    if not current_sha or not path.is_file():
        return ""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for raw in reversed(lines):
        try:
            row = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        generation = row.get("generation") if isinstance(row.get("generation"), Mapping) else {}
        meta = row.get("meta") if isinstance(row.get("meta"), Mapping) else {}
        qa = row.get("qa") if isinstance(row.get("qa"), Mapping) else {}
        if str(row.get("event") or "") != "qa":
            continue
        if str(generation.get("asset") or "") != target.rel_path:
            continue
        if str(generation.get("status") or "").lower() != "rejected":
            continue
        if str(meta.get("artifact_sha256") or "") != current_sha:
            continue
        if str(meta.get("review_kind") or "").lower() != "executor_visual":
            continue
        return str(qa.get("msg") or "").strip()
    return ""


def append_log(root: Path, row: dict) -> None:
    path = root / "生产数据" / "codex_image_runner.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def controlled_multiref_derivation(
    root: Path,
    rel_path: str,
    reference_inputs: Sequence[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not requires_controlled_makeup_derivation(rel_path) or not reference_inputs:
        return None
    stem = Path(rel_path).stem
    prefer_turnaround = any(token in stem for token in ("45度", "_侧", "_背"))
    base = re.sub(r"_(?:表情_.+|45度|侧|背|侧背|侧影|半身|全身翼展|全身|脸部特写|群像sheet|sheet|三视图)$", "", stem)
    front_stems = {base, f"{base}_front", f"{base}_正面"}
    same_source_parent_stems = {Path(candidate).stem for candidate in controlled_makeup_parent_candidates(rel_path)}
    ordered = sorted(reference_inputs, key=lambda item: int(item.get("priority") or 999))

    def is_turnaround(item: Dict[str, Any]) -> bool:
        item_stem = Path(str(item.get("rel_path") or item.get("abs_path") or "")).stem
        return "三视图" in item_stem or item_stem.endswith("_turnaround")

    def is_front(item: Dict[str, Any]) -> bool:
        item_stem = Path(str(item.get("rel_path") or item.get("abs_path") or "")).stem
        return item_stem in front_stems or item_stem.endswith("_front") or item_stem.endswith("_正面")

    def is_same_source_parent(item: Dict[str, Any]) -> bool:
        item_stem = Path(str(item.get("rel_path") or item.get("abs_path") or "")).stem
        return item_stem in same_source_parent_stems

    source = None
    predicates = (is_turnaround, is_front) if prefer_turnaround else (is_front, is_turnaround)
    for predicate in predicates:
        source = next((item for item in ordered if predicate(item)), None)
        if source:
            break
    if source is None:
        source = next((item for item in ordered if is_same_source_parent(item)), None)
    if source is None:
        source = ordered[0]
    source_rel = str(source.get("prepared_rel_path") or source.get("rel_path") or "").strip()
    source_abs = (
        Path(str(source.get("prepared_abs_path") or source.get("abs_path") or ""))
        if (source.get("prepared_abs_path") or source.get("abs_path"))
        else root / source_rel
    )
    size = png_size(source_abs)
    width, height = size if size else (0, 0)
    source_sha = str(source.get("prepared_sha256") or source.get("sha256") or "").strip()
    if not source_sha and source_abs.is_file():
        source_sha = file_sha256(source_abs)
    return {
        "method": "controlled_multiref_generation",
        "source_path": source_rel,
        "source_sha256": source_sha,
        "crop_box": [0, 0, int(width), int(height)],
        "generated_by": SOURCE,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "reference_input_mode": "codex_exec_image_flags",
        "reference_inputs": [
            {
                "rel_path": str(item.get("rel_path") or ""),
                "prepared_rel_path": str(item.get("prepared_rel_path") or ""),
                "sha256": str(item.get("sha256") or ""),
                "prepared_sha256": str(item.get("prepared_sha256") or ""),
                "role": str(item.get("role") or ""),
                "owner": str(item.get("owner") or ""),
                "source": str(item.get("source") or ""),
            }
            for item in reference_inputs
            if item.get("rel_path")
        ],
    }


def is_style_anchor_path(rel_path: str) -> bool:
    stem = Path(str(rel_path or "")).stem.lower()
    return "风格锚" in stem or "style_anchor" in stem


def mark_style_anchor_ready(root: Path, rel_path: str, *, status: str = "ready") -> None:
    path = root / STYLE_ANCHOR_REGISTRY
    data = load_json_file(path)
    if not data:
        data = {"kind": "n2d_style_anchor_registry", "version": 1}
    selected = data.get("selected_anchor") if isinstance(data.get("selected_anchor"), dict) else {}
    selected = dict(selected)
    selected.update({
        "path": rel_path,
        "status": status,
        "role": "style_anchor",
        "use_policy": "style_only",
        "identity_policy": "do_not_clone_face_or_costume",
        "updated_by": SOURCE,
        "updated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    })
    data["selected_anchor"] = selected
    data["updated_at"] = selected["updated_at"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def mark_shared_reference_status(
    root: Path,
    rel_path: str,
    status: str,
    *,
    preserve_ready: bool = False,
    derivation: Optional[Dict[str, Any]] = None,
) -> None:
    """Mark matching shared reference registry entries after a real PNG exists."""
    asset_path = root / rel_path
    pixel_meta: Dict[str, Any] = {}
    if status == "ready" and asset_path.is_file():
        current_sha = optional_file_sha256(asset_path)
        current_size = _open_image_size(asset_path)
        if current_sha:
            pixel_meta["sha256"] = current_sha
        if current_size:
            pixel_meta["width"], pixel_meta["height"] = current_size

    skip_string_keys = {
        "path",
        "rel_path",
        "abs_path",
        "source",
        "source_image",
        "source_refs",
        "source_face_reference",
        "source_path",
        "source_sha256",
        "generated_by",
        "generated_at",
        "review_reason",
    }

    def ready_entry(existing: Any = None) -> Dict[str, Any]:
        entry = dict(existing) if isinstance(existing, dict) else {}
        entry["path"] = rel_path
        entry["status"] = status
        entry.update(pixel_meta)
        if derivation:
            entry["derivation"] = derivation
        return entry

    for registry_rel in (
        Path("出图") / "共享" / "identity_registry.json",
        Path("出图") / "共享" / "asset_registry.json",
    ):
        path = root / registry_rel
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        changed = False

        def walk(node) -> None:
            nonlocal changed
            if isinstance(node, dict):
                if node.get("path") == rel_path:
                    if preserve_ready and node.get("status") == "ready":
                        return
                    if node.get("status") != status:
                        node["status"] = status
                        changed = True
                    for meta_key, meta_value in pixel_meta.items():
                        if node.get(meta_key) != meta_value:
                            node[meta_key] = meta_value
                            changed = True
                    if derivation and node.get("derivation") != derivation:
                        node["derivation"] = derivation
                        changed = True
                    if status == "review_pending":
                        review = node.get("human_review")
                        if not isinstance(review, dict):
                            review = {}
                        review["status"] = "pending"
                        review["reason"] = "Codex text-generated character candidate requires human approval before ready"
                        node["human_review"] = review
                        changed = True
                    elif status == "ready":
                        review = node.get("human_review")
                        if isinstance(review, dict) and review.get("status") == "pending":
                            review = dict(review)
                            review["status"] = "accepted"
                            review["reason"] = "shared reference promoted to ready after reviewed shared generation"
                            review["reviewed_by"] = SOURCE
                            review["reviewed_at"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
                            node["human_review"] = review
                            changed = True
                for key, child in list(node.items()):
                    # Lineage / audit metadata may legitimately contain the same
                    # target path (for example ``derivation.source_refs`` when a
                    # prior candidate is recorded).  Those values are evidence,
                    # not registry reference slots.  Descending into them can
                    # repeatedly expand the target string into ``ready_entry``
                    # objects that themselves contain the same derivation and
                    # eventually hit RecursionError.  The existing key deny-list
                    # already defines metadata-only fields; apply it to nested
                    # containers as well as direct strings.
                    if key in skip_string_keys:
                        continue
                    if isinstance(child, str) and key not in skip_string_keys and child == rel_path:
                        node[key] = ready_entry()
                        changed = True
                        continue
                    walk(child)
            elif isinstance(node, list):
                for idx, child in enumerate(list(node)):
                    if isinstance(child, str) and child == rel_path:
                        node[idx] = ready_entry()
                        changed = True
                        continue
                    walk(child)

        walk(data)
        if changed:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def status_after_shared_generation(rel_path: str, target: Optional[Target] = None) -> str:
    if (
        target is not None
        and target.mode == "shared"
        and os.environ.get("N2D_HUMAN_REVIEWED_SHARED") != "1"
    ):
        return "review_pending"
    return "ready"


def latest_recorded_status(root: Path, task_id: str, rel_path: str) -> str:
    path = root / "生产数据" / "production_events.jsonl"
    if not path.is_file():
        return ""
    status = ""
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("stage") != "image":
                continue
            generation = event.get("generation")
            meta = event.get("meta")
            if not isinstance(generation, dict) or not isinstance(meta, dict):
                continue
            if generation.get("asset") == rel_path and str(meta.get("task") or "") == task_id:
                status = str(generation.get("status") or "")
    return status.lower()


def target_generation_lock(root: Path, rel_path: str) -> Path:
    token = hashlib.sha256(str(rel_path).encode("utf-8")).hexdigest()[:20]
    return root / "生产数据" / ".generation_locks" / f"{token}.lock"


def acquire_target_generation_lock(root: Path, rel_path: str, timeout_sec: Optional[float]) -> Optional[Path]:
    """Atomically prevent duplicate paid submissions for the same target."""
    lock = target_generation_lock(root, rel_path)
    lock.parent.mkdir(parents=True, exist_ok=True)
    stale_after = max(float(timeout_sec or 600.0) + 120.0, 720.0)
    for _ in range(2):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            try:
                age = max(0.0, time.time() - lock.stat().st_mtime)
            except OSError:
                age = 0.0
            if age <= stale_after:
                return None
            try:
                lock.unlink()
            except OSError:
                return None
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"pid": os.getpid(), "target": rel_path, "created_at": time.time()}, fh, ensure_ascii=False)
        return lock
    return None


def release_target_generation_lock(lock: Optional[Path]) -> None:
    if not lock:
        return
    try:
        lock.unlink()
    except FileNotFoundError:
        pass


def process_target(
    root: Path,
    episode: str,
    target: Target,
    *,
    task_id: str,
    timeout_sec: Optional[float],
    dry_run: bool,
    force: bool,
) -> bool:
    seed = logical_seed(root, episode, target.shot, target.rel_path)
    final = root / target.rel_path
    temp_dir = Path(tempfile.gettempdir()) / "n2d_codex_image_runner" / (task_id or "manual")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{episode}_{temp_token(target.shot)}_{Path(target.rel_path).stem}.png"
    if temp_path.exists():
        temp_path.unlink()

    existing_shared_image = target.mode == "shared" and raster_valid(final)
    previous_status = latest_recorded_status(root, task_id, target.rel_path)
    reference_bundle = reference_bundle_for_target(root, episode, target)
    reference_inputs = codex_reference_inputs_for_target(root, episode, target, reference_bundle)
    reference_inputs = prepare_reference_inputs(root, episode, reference_inputs, write=not dry_run)
    attach_reference_inputs(reference_bundle, reference_inputs)
    retry_guidance = target_qc_retry_guidance(root, episode, target) if force and png_valid(final) else ""
    compiled_request = compile_target_image_request(
        root,
        episode,
        target,
        reference_inputs,
        backend="codex",
        retry_guidance=retry_guidance,
    )
    compiler_errors = list((compiled_request.get("lint") or {}).get("errors") or [])
    if compiler_errors:
        print(
            f"[fail] {target.shot}: compiled image request invalid: {', '.join(compiler_errors)}",
            file=sys.stderr,
        )
        return False

    if dry_run:
        print(json.dumps({
            "shot": target.shot,
            "mode": target.mode,
            "target": target.rel_path,
            "temp": str(temp_path),
            "logical_seed": seed,
            "reference_input_mode": "codex_exec_image_flags",
            "reference_input_count": len(reference_inputs),
            "reference_input_paths": [reference_input_actual_path(item) for item in reference_inputs],
            "reference_input_quality": [item.get("reference_quality") for item in reference_inputs],
            "prompt_compiler": {
                key: compiled_request.get(key)
                for key in (
                    "kind", "version", "profile_version", "profile", "backend", "model", "mode",
                    "task_type", "negative_strategy", "source_contract_sha256", "compiled_request_sha256",
                )
            },
            "compiled_prompt_chars": (compiled_request.get("metrics") or {}).get("prompt_chars"),
            "skip_existing_pass": (not force and previous_status == "pass" and png_valid(final)),
            "skip_existing_file": (not force and existing_shared_image),
        }, ensure_ascii=False))
        return True

    if not force and existing_shared_image:
        if is_style_anchor_path(target.rel_path):
            # Existing pixels are not a visual signoff. Keep the registry's
            # review_pending/approved state; a skip must never auto-promote.
            pass
        else:
            mark_shared_reference_status(
                root,
                target.rel_path,
                status_after_shared_generation(target.rel_path, target),
                preserve_ready=True,
            )
        print(f"[skip] {target.shot} existing shared image: {target.rel_path}")
        append_log(root, {
            "ts": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
            "episode": episode,
            "shot": target.shot,
            "mode": target.mode,
            "target": target.rel_path,
            "status": "skip_existing_png",
            "logical_seed": seed,
            "seed_effective": "unsupported",
        })
        return True

    if not force and previous_status == "pass" and png_valid(final):
        print(f"[skip] {target.shot} already has pass record for {task_id}: {target.rel_path}")
        append_log(root, {
            "ts": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
            "episode": episode,
            "shot": target.shot,
            "mode": target.mode,
            "target": target.rel_path,
            "status": "skip_pass_recorded",
            "logical_seed": seed,
            "seed_effective": "unsupported",
        })
        return True

    if (
        target.mode == "shared"
        and requires_controlled_makeup_derivation(target.rel_path)
        and not has_controlled_makeup_source(target.rel_path, reference_inputs)
    ):
        print(
            "[fail] "
            f"{target.shot}: character makeup split refs must be derived from an approved same-source "
            "turnaround/front image or generated by a real image2image/multiref backend; Codex text-only "
            f"generation is blocked for {target.rel_path}",
            file=sys.stderr,
        )
        return False

    reference_manifest = write_reference_bundle_manifest(root, episode, target, reference_bundle)
    if (
        carried_identity_unanchored(
            reference_bundle, [item.get("rel_path") for item in reference_inputs]
        )
    ):
        carried = "、".join(str(c) for c in reference_bundle.get("carried_identity") or [])
        print(
            "[fail] "
            f"{target.shot}: 本图声明承载角色身份（carries_identity={carried}），"
            "但没有任何角色脸锚作为 `codex exec --image` 附件传入——纯文生图会另画一张新脸，"
            f"正是定妆阶段脸漂的成因。参考 manifest 已写入 {reference_manifest}；"
            "请先把承载角色的脸部特写/正面参考置 ready，或设 N2D_ALLOW_UNANCHORED_IDENTITY_PLATE=1 显式豁免。",
            file=sys.stderr,
        )
        log_unanchored_friction(root, episode, target.shot, reference_bundle.get("carried_identity"), "Codex")
        return False
    if (
        high_risk_text_only_character_shot(target)
        and (reference_bundle.get("items") or reference_bundle.get("missing_ready_refs"))
        and not reference_inputs
    ):
        print(
            "[fail] "
            f"{target.shot}: 本镜是高风险角色镜（近景/大表情/多人/暗光/VFX 等），"
            "但 reference_bundle 没有任何可作为 `codex exec --image` 附件传入的 ready 图片。"
            f"参考 manifest 已写入 {reference_manifest}；先补 ready 参考图或切支持主体库的后端。",
            file=sys.stderr,
        )
        return False

    prompt = build_codex_prompt(
        root,
        episode,
        target,
        temp_path,
        seed,
        reference_bundle,
        reference_manifest,
        retry_guidance=retry_guidance,
        compiled_request=compiled_request,
    )
    compiled_receipt = write_compiled_request_receipt(root, episode, target, compiled_request, prompt)
    generation_lock = acquire_target_generation_lock(root, target.rel_path, timeout_sec)
    if generation_lock is None:
        print(
            f"[fail] {target.shot}: target already has an active generation lock; do not resubmit while the prior paid job is running",
            file=sys.stderr,
        )
        return False
    started = time.monotonic()
    error = ""
    archive_path: Optional[Path] = None
    ok = False
    try:
        proc = run_codex(repo_root(), prompt, timeout_sec, reference_inputs)
        if proc.returncode != 0:
            error = format_codex_failure(proc)
        elif not png_valid(temp_path) and not decode_image_event(proc.stdout, temp_path):
            failure_detail = image_generation_failure_detail(proc.stdout or "")
            if failure_detail:
                error = f"codex image_generation failed: {failure_detail}"
            else:
                error = f"codex completed but no valid PNG file or image_generation_end payload was available for {temp_path}"
        else:
            archive_path = archive_existing(root, target.rel_path, task_id)
            final.parent.mkdir(parents=True, exist_ok=True)
            os.replace(temp_path, final)
            ok = png_valid(final)
            if ok and target.mode == "shared":
                if is_style_anchor_path(target.rel_path):
                    mark_style_anchor_ready(root, target.rel_path, status="review_pending")
                else:
                    mark_shared_reference_status(
                        root,
                        target.rel_path,
                        status_after_shared_generation(target.rel_path, target),
                        derivation=controlled_multiref_derivation(root, target.rel_path, reference_inputs),
                    )
            if not ok:
                error = f"moved output is not a valid PNG: {final}"
    except subprocess.TimeoutExpired:
        error = f"codex timed out after {timeout_sec}s"
    except Exception as exc:  # pragma: no cover - defensive batch guard
        error = f"{type(exc).__name__}: {exc}"
    finally:
        release_target_generation_lock(generation_lock)

    duration = time.monotonic() - started
    record_event(
        root,
        episode,
        target,
        status="pass" if ok else "fail",
        duration_sec=duration,
        task_id=task_id,
        seed=seed,
        temp_path=temp_path,
        archive_path=archive_path,
        reference_manifest=reference_manifest,
        reference_inputs=reference_inputs,
        submitted_prompt=prompt,
        compiled_request=compiled_request,
        compiled_receipt=compiled_receipt,
        error=error,
    )
    append_log(root, {
        "ts": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "episode": episode,
        "shot": target.shot,
        "mode": target.mode,
        "target": target.rel_path,
        "status": "pass" if ok else "fail",
        "duration_sec": round(duration, 3),
        "logical_seed": seed,
        "seed_effective": "unsupported",
        "reference_input_mode": "codex_exec_image_flags",
        "reference_input_count": len(reference_inputs),
        "reference_input_paths": [reference_input_actual_path(item) for item in reference_inputs],
        "reference_manifest": str(reference_manifest),
        "compiled_request": str(compiled_receipt),
        "compiled_request_sha256": compiled_request.get("compiled_request_sha256"),
        "prompt_profile_version": compiled_request.get("profile_version"),
        "prompt_profile": compiled_request.get("profile"),
        "prompt_task_type": compiled_request.get("task_type"),
        "compiled_estimated_text_tokens": (compiled_request.get("metrics") or {}).get("estimated_text_tokens"),
        "image_prompt_experiment_id": (compiled_request.get("experiment") or {}).get("experiment_id"),
        "image_prompt_variant": (compiled_request.get("experiment") or {}).get("variant"),
        "actual_submit_prompt_sha256": sha256_text(prompt),
        "archive": str(archive_path) if archive_path else "",
        "error": error[:1000],
    })
    if ok:
        print(f"[pass] {target.shot} -> {target.rel_path}")
    else:
        print(f"[fail] {target.shot}: {error}", file=sys.stderr)
    return ok


def build_targets(root: Path, episode: str, shots: Iterable[str]) -> List[Target]:
    sections = load_sections(root, episode)
    targets: List[Target] = []
    seen = set()
    for shot in shots:
        section = section_for(sections, shot)
        for target in expand_shot_targets(shot, section, episode):
            key = target.rel_path
            if key not in seen:
                seen.add(key)
                targets.append(target)
    return order_targets_for_reference_chain(targets)


def frame_dependency_rank(target: Target) -> tuple[int, int]:
    """Order same-Clip frames so derived tailframes can see earlier anchors."""
    if target.mode == "firstframe":
        return (0, 0)
    if target.mode == "midframe":
        stem = Path(target.rel_path).stem
        if re.search(r"_mid$", stem):
            return (1, 0)
        match = re.search(r"_a(\d+)$", stem)
        if match:
            return (1, int(match.group(1)))
        return (1, 999)
    if target.mode == "tailframe":
        return (2, 0)
    return (1, 999)


def order_targets_for_reference_chain(targets: List[Target]) -> List[Target]:
    """Keep user Clip order, but generate each Clip's anchors before its tailframe."""
    clip_order: Dict[str, int] = {}
    for target in targets:
        clip_order.setdefault(target.clip, len(clip_order))
    return [
        target for _idx, target in sorted(
            enumerate(targets),
            key=lambda item: (
                clip_order.get(item[1].clip, item[0]),
                frame_dependency_rank(item[1]),
                item[0],
            ),
        )
    ]


def all_episode_targets(root: Path, episode: str) -> List[Target]:
    targets: List[Target] = []
    seen: Set[str] = set()
    for section in load_sections(root, episode):
        for target in expand_shot_targets(section.clip, section, episode):
            if target.rel_path not in seen:
                seen.add(target.rel_path)
                targets.append(target)
    return targets


def covers_all_episode_targets(root: Path, episode: str, targets: Sequence[Target]) -> bool:
    """Whether this run generated the whole episode image namespace.

    Partial batch runs intentionally leave future Clip PNGs absent.  Running the
    whole-episode image gate after such a batch turns those expected absences
    into noisy hard blocks, so the runner only performs the final image gate
    when the requested target set covers every declared episode target.
    """
    requested = {target.rel_path for target in targets if target.mode != "shared"}
    if not requested:
        return False
    try:
        declared = {target.rel_path for target in all_episode_targets(root, episode)}
    except Exception:
        return False
    return bool(declared) and declared.issubset(requested)


def image_progress_counts(root: Path, episode: str) -> tuple[int, int]:
    """Count live image-plan targets by real landed files, not by task attempts."""
    targets: List[Target] = []
    seen: Set[str] = set()
    try:
        for target in build_shared_targets(root, ["all"]):
            if target.rel_path not in seen:
                seen.add(target.rel_path)
                targets.append(target)
    except Exception:
        pass
    try:
        for target in all_episode_targets(root, episode):
            if target.rel_path not in seen:
                seen.add(target.rel_path)
                targets.append(target)
    except Exception:
        pass

    done = 0
    for target in targets:
        path = root / target.rel_path
        if target.mode == "shared":
            done += 1 if raster_valid(path) else 0
        else:
            done += 1 if png_valid(path) else 0
    return done, len(targets)


def current_image_progress_total(root: Path, episode: str) -> Optional[int]:
    """Return the already-established 出图 denominator from `_进度.md`."""
    path = root / "_进度.md"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    header: Optional[List[str]] = None
    for line in lines:
        if line.startswith("| 集 |"):
            header = [cell.strip() for cell in line.split("|")[1:-1]]
            continue
        if not header or not re.match(r"^\|\s*" + re.escape(episode) + r"\s*\|", line):
            continue
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(cells) < len(header) or "出图" not in header:
            return None
        value = cells[header.index("出图")]
        match = re.fullmatch(r"\s*\d+\s*/\s*(\d+)\s*", value)
        if match:
            return int(match.group(1))
        return None
    return None


def episode_image_done_count(root: Path, episode: str) -> int:
    """Count only episode Clip PNGs for progress rows with an existing denominator."""
    done = 0
    try:
        targets = all_episode_targets(root, episode)
    except Exception:
        return 0
    seen: Set[str] = set()
    for target in targets:
        if target.rel_path in seen:
            continue
        seen.add(target.rel_path)
        done += 1 if png_valid(root / target.rel_path) else 0
    return done


def episode_image_target_count(root: Path, episode: str) -> int:
    """Count live episode Clip targets declared by the current prompt pack."""
    try:
        targets = all_episode_targets(root, episode)
    except Exception:
        return 0
    return len({target.rel_path for target in targets})


def sync_image_progress(root: Path, episode: str) -> Optional[tuple[int, int]]:
    combined_done, combined_total = image_progress_counts(root, episode)
    episode_done = episode_image_done_count(root, episode)
    episode_total = episode_image_target_count(root, episode)
    has_shared_scope = combined_total > episode_total
    live_done = combined_done if has_shared_scope else episode_done
    live_total = combined_total if has_shared_scope else episode_total

    current_total = current_image_progress_total(root, episode)
    if current_total:
        if episode_total and current_total == episode_total:
            done, total = episode_done, episode_total
        elif combined_total and current_total == combined_total:
            done, total = combined_done, combined_total
        else:
            done = live_done
            total = current_total
        preserve_stale = os.environ.get("N2D_PRESERVE_IMAGE_PROGRESS_TOTAL", "").strip().lower() in {
            "1", "true", "yes", "on",
        }
        if (
            live_total
            and live_total != current_total
            and not preserve_stale
            and not (episode_total and current_total == episode_total)
        ):
            print(
                f"[progress] 出图 denominator {current_total} differs from live image-plan targets {live_total}; "
                f"using {live_total}",
                file=sys.stderr,
            )
            total = live_total
        done = min(done, total)
    else:
        done, total = combined_done, combined_total
    if total <= 0:
        return None
    cmd = [
        sys.executable,
        str(repo_root() / PROGRESS),
        "set",
        str(root),
        episode,
        "出图",
        f"{done}/{total}",
    ]
    proc = subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        print(f"[progress] failed to sync 出图 {done}/{total}: {proc.stderr.strip()}", file=sys.stderr)
        return None
    print(f"[progress] 出图 {done}/{total}")
    return done, total


def build_shared_targets(root: Path, requested: Iterable[str]) -> List[Target]:
    available = load_shared_sections(root)
    requests = list(requested)
    if not requests or requests == ["all"]:
        return available
    targets: List[Target] = []
    seen = set()
    for req in requests:
        req = req.strip()
        found = None
        for target in available:
            aliases = getattr(target, "aliases", set())
            if req == target.shot or req == Path(target.rel_path).stem or req in aliases:
                found = target
                break
        if not found:
            raise ValueError(f"no shared target found for {req}")
        if found.rel_path not in seen:
            seen.add(found.rel_path)
            targets.append(found)
    return targets


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Codex image_generation adapter for n2d image tasks")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--shots", default=os.environ.get("N2D_AFFECTED_SHOTS", ""))
    ap.add_argument("--shared-targets", default="", help="comma-separated shared assets to generate; use 'all' for all primary shared prompt targets")
    ap.add_argument("--shared-offset", type=int, default=0, help="zero-based offset into resolved shared targets")
    ap.add_argument("--max-shared-targets", type=int, help="maximum number of resolved shared targets to process")
    ap.add_argument("--max-shots", type=int)
    ap.add_argument("--timeout-sec", type=float, default=float(os.environ.get("N2D_CODEX_IMAGE_TIMEOUT", "900")))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stop-on-fail", action="store_true")
    ap.add_argument("--force", action="store_true", help="regenerate even when this task already has a pass event for the asset")
    ap.add_argument(
        "--repair-redraw",
        action="store_true",
        help="redraw exactly one current PNG named by a fresh full image_qc failure; writes a B14 target preflight receipt",
    )
    ap.add_argument("--skip-image-qc", action="store_true", help="skip per-target image_qc after each generated episode shot")
    ap.add_argument("--skip-final-gate", action="store_true", help="do not run the whole-episode image gate after shot generation")
    ap.add_argument("--skip-preflight", action="store_true", help="skip the pre-spend image_preflight gate (logs a dashboard waiver)")
    return ap


def main(argv: Sequence[str]) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root).resolve()
    episode = normalize_episode(ns.episode)
    shots = split_csv(ns.shots)
    shared_targets = split_csv(ns.shared_targets)
    if not shots and not shared_targets:
        raise SystemExit("--shots/--shared-targets or N2D_AFFECTED_SHOTS is required")
    if ns.max_shots is not None:
        shots = shots[: ns.max_shots]
    task_id = os.environ.get("N2D_TASK_ID") or f"manual-{episode}"
    targets = []
    if shared_targets:
        resolved_shared = build_shared_targets(root, shared_targets)
        start = max(ns.shared_offset, 0)
        end = start + ns.max_shared_targets if ns.max_shared_targets is not None else None
        targets.extend(resolved_shared[start:end])
    if shots:
        targets.extend(build_targets(root, episode, shots))
    if not targets:
        raise SystemExit("no targets resolved")
    forbidden_consistency_bypasses = [
        flag
        for flag, enabled in (
            ("--skip-preflight", ns.skip_preflight),
            ("--skip-image-qc", ns.skip_image_qc),
            ("--skip-final-gate", ns.skip_final_gate),
        )
        if enabled
    ]
    if forbidden_consistency_bypasses and not ns.dry_run:
        print(
            "[gate] B14 每张图片前后双重一致性硬闸不可绕过："
            + ", ".join(forbidden_consistency_bypasses)
            + "；修复前置合同/QC 环境后重试。",
            file=sys.stderr,
        )
        return 1
    if ns.repair_redraw and not ns.dry_run and (not ns.force or len(targets) != 1):
        print(
            "[gate] --repair-redraw requires --force and exactly one resolved PNG target",
            file=sys.stderr,
        )
        return 1
    strict_single_review = strict_single_image_review_enabled(root)
    if strict_single_review and not ns.dry_run and len(targets) != 1:
        print(
            "[gate] 图片验收模式=逐张机器QC+实际目视：一次正式调用必须且只能解析 1 张图片；"
            "请传单一 --shared-targets，或把 --shots 缩到只产生一个实际 PNG 的目标。",
            file=sys.stderr,
        )
        return 1
    if strict_single_review and not ns.dry_run:
        pending_review = strict_pending_image_review(root, targets[0].rel_path)
        if pending_review:
            print(
                "[gate] 上一张图片尚无与当前像素 SHA 绑定的 qa/accepted 目视验收："
                f"{pending_review['asset']} ({pending_review['artifact_sha256'] or 'sha-missing'})；"
                "只能继续重抽该图，或先完成 full 机器QC、实际像素目视并记录 accepted，再生成下一张。",
                file=sys.stderr,
            )
            return 1

    # Shared style/identity assets are paid generations too.  They cannot use
    # the full image_preflight before their own pixels/MVIEW receipts exist, but
    # compliance and external-reference rights are already knowable and are not
    # waivable via --skip-preflight.
    if shared_targets and not ns.dry_run and not run_shared_asset_preflight(root, episode):
        return 1

    # Non-waivable ordering lock: a Clip run may never spend before the
    # referenced shared library is complete.  Whole-episode runs scan the whole
    # prompt pack; selective redraws scan only the requested Clip sections.
    # --skip-preflight only skips the broader dashboard gate; it cannot bypass shared-first.
    if shots and not ns.dry_run and not enforce_shared_first_interlock(root, episode, targets=targets):
        return 1
    if shots and not ns.dry_run and not enforce_current_episode_image_namespace(root, episode):
        return 1

    # Pre-spend interlock: 出图是 n2d 最贵工位之一，绝不能「烧完积分才发现崩脸/缺参考/契约不全」。
    # 生成前先跑 image_preflight 硬闸门（不需要本集 PNG 已存在）；block 即拒绝生成，不花钱。
    # 逃生口 --skip-preflight 必须留痕成 dashboard waiver（执行时松动可审计）。
    if shots and not ns.dry_run:
        if ns.repair_redraw:
            if not run_target_repair_preflight(root, episode, targets[0]):
                return 1
        elif ns.skip_preflight:
            record_waiver(root, episode, "image_preflight", "skip-preflight",
                          "operator passed --skip-preflight; pre-spend image_preflight gate not run")
        elif not run_image_gate(root, episode, stage="image_preflight"):
            print("[gate] image_preflight blocked — refusing to spend on generation; fix upstream or pass --skip-preflight", file=sys.stderr)
            return 1

    ok_all = True
    for target in targets:
        print(f"[start] {target.shot} -> {target.rel_path}", flush=True)
        ok = process_target(
            root,
            episode,
            target,
            task_id=task_id,
            timeout_sec=ns.timeout_sec,
            dry_run=ns.dry_run,
            force=ns.force,
        )
        if (
            ok
            and not ns.dry_run
            and not ns.skip_image_qc
            and ((shots and target.mode != "shared") or strict_single_review)
        ):
            ok = run_target_image_qc(root, episode, target)
        ok_all = ok_all and ok
        if ok and not ns.dry_run:
            sync_image_progress(root, episode)
        if not ok and ns.stop_on_fail:
            break
    if ns.skip_image_qc and shots and not ns.dry_run:
        record_waiver(root, episode, "image", "skip-image-qc",
                      "operator passed --skip-image-qc; per-target landed-frame QC not run")
    if ok_all and shots and not ns.dry_run:
        if ns.skip_final_gate:
            record_waiver(root, episode, "image", "skip-final-gate",
                          "operator passed --skip-final-gate; whole-episode image gate not run")
        elif not covers_all_episode_targets(root, episode, targets):
            print("[gate] image final gate deferred for partial batch; run the whole-episode image gate after all declared Clip PNGs are present")
        else:
            ok_all = run_image_gate(root, episode)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
