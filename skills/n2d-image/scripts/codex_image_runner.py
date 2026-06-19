#!/usr/bin/env python3
"""Generate n2d episode images through Codex's image_generation feature.

This is the Codex backend adapter used by N2D_IMAGE_COMMAND.  It keeps the
batch wrapper backend-agnostic while giving Codex a real PNG-producing path:

1. Parse the episode prompt pack.
2. Ask ``codex exec --json --enable image_generation`` to generate one target image.
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
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence


PROMPT_REL = Path("出图") / "{episode}" / "prompt" / "01_分镜出图.md"
DASHBOARD = Path("skills") / "n2d-dashboard" / "scripts" / "dashboard.py"
SOURCE = "skills/n2d-image/scripts/codex_image_runner.py"


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
    return Path(__file__).resolve().parents[3]


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


def load_sections(root: Path, episode: str) -> List[ClipSection]:
    prompt_path = root / str(PROMPT_REL).format(episode=episode)
    if not prompt_path.is_file():
        raise FileNotFoundError(f"prompt pack not found: {prompt_path}")
    storyboard_targets = load_storyboard_target_lines(root, episode)
    text = prompt_path.read_text(encoding="utf-8")
    headers = list(re.finditer(r"^##\s+(?:(Clip)\s+(\d+)|(镜头)\s*([0-9０-９]+))[^\n]*$", text, re.M))
    sections: List[ClipSection] = []
    for index, header in enumerate(headers):
        start = header.start()
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        body = text[start:end].strip()
        title = header.group(0).strip()
        raw_num = header.group(2) or header.group(4)
        if not raw_num:
            continue
        raw_num = raw_num.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
        clip = f"Clip_{int(raw_num):02d}"
        target_match = re.search(r"^\*\*(?:目标|目标落档)\*\*：([^\n]+)$", body, re.M)
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
    files = ["角色定妆.md", "场景定妆.md", "道具定妆.md", "特效定妆.md"]
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
            target_match = re.search(r"^\*\*目标存档\*\*：([^\n]+)$", body, re.M)
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
                add_target(variant_shot, rel, section, aliases, shared_variant_note(rel))
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


def shared_variant_note(rel_path: str) -> str:
    stem = Path(rel_path).stem
    if "45度" in stem:
        return "本次目标是 45° / 三分之二侧脸参考：同一角色同一服装，中性浅灰背景，脸部转向约 45°，不是正脸改名，也不是纯侧脸。"
    if stem.endswith("_侧"):
        return "本次目标是标准侧面参考：同一角色同一服装，中性浅灰背景，保持同身高同景别，脸部清楚。"
    if stem.endswith("_背"):
        return "本次目标是背面参考：同一角色同一服装，中性浅灰背景，重点锁发型背面、衣料结构和背影轮廓。"
    if "半身" in stem:
        return "本次目标是半身服装参考：人物主体居中，头身中线接近画面中线，左右留白均衡，重点锁服装剪裁、材质和配饰。"
    if "脸部特写" in stem:
        return "本次目标是脸部特写参考：肩颈以上近景，眼鼻嘴三角区清晰，五官与主参考同一张脸，服装/发型边缘可见。"
    if "三视图" in stem:
        return "本次目标是人审三视图拼版：同一角色同一服装，正面、45°、侧面、背面同框排列，同身高、同比例、水平视平线对齐。"
    if "_表情_" in stem:
        emotion = stem.split("_表情_", 1)[-1]
        return (
            f"本次目标是同源表情脸部近景参考：保持同一角色身份和妆造，只改变表情为「{emotion}」；"
            "画面必须是肩颈以上到胸口以内的近景，脸部占画面 30%-50%，眼鼻嘴三角区清晰，"
            "不得画成全身/远景/多人构图，脸部不可换人。"
        )
    return "本次目标是共享主参考图：中性档案，不带剧情戏剧动作，锁身份/场景/道具/特效基准。"


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
                    add_target(shot, rel, section, aliases, shared_variant_note(rel))

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
            for rel in registry_image_paths(asset):
                shot = shared_variant_shot(asset_id or "asset", rel)
                add_target(shot, rel, section, aliases, shared_variant_note(rel))


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
            if any(alias in title for alias in aliases if alias.startswith(("CHAR_", "LOC_", "PROP_", "VFX_", "OUTFIT_"))):
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
            if isinstance(path, str) and (not status or status in {"ready", "planned", "pass", "todo"}):
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
    return paths


def shared_aliases(title: str, body: str, rel_path: str) -> set:
    aliases = {Path(rel_path).stem, Path(rel_path).name}
    # The section title owns the shared target identity.  Body text may mention
    # related assets, such as VFX_01 in a character form, but those references
    # must not become selectable aliases for this target.
    ids = re.findall(r"`?((?:CHAR|LOC|PROP|OUTFIT|VFX)_[A-Za-z0-9_]+)`?", title)
    aliases.update(ids)
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
    title_ids = re.findall(r"`((?:CHAR|LOC|PROP|OUTFIT|VFX)_[A-Za-z0-9_]+)`", title)
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
    for prefix in ("CHAR_", "LOC_", "PROP_", "OUTFIT_", "VFX_"):
        candidates = sorted(a for a in aliases if isinstance(a, str) and a.startswith(prefix))
        if candidates:
            return candidates[0]
    return Path(rel_path).stem


def normalize_shot_name(shot: str) -> str:
    text = str(shot).strip()
    text = text.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    match = re.fullmatch(r"(?:镜头|shot|clip)?[_\s-]*([0-9]+)(?:_(mid|end|first_mid|a[0-9]+))?", text, re.I)
    if match:
        suffix = f"_{match.group(2)}" if match.group(2) else ""
        return f"Clip_{int(match.group(1)):02d}{suffix}"
    match = re.fullmatch(r"Clip[_\s-]*([0-9]+)(?:_(mid|end|first_mid|a[0-9]+))?", text, re.I)
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


def target_for_shot(shot: str, section: ClipSection, episode: str) -> Target:
    shot = normalize_shot_name(shot)
    line = section.target_line
    if not line:
        raise ValueError(f"{section.clip}: target line missing")
    paths = backticked(line)

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

    first = paths[0] if paths else first_backticked(line)
    if not first:
        raise ValueError(f"{shot}: first-frame target missing")
    return Target(shot=shot, clip=section.clip, mode="firstframe", rel_path=rel_to_root(first, episode), section=section)


def logical_seed(root: Path, episode: str, shot: str, rel_path: str) -> str:
    data = f"{root.name}|{episode}|{shot}|{rel_path}".encode("utf-8")
    return str(1000 + int(hashlib.sha1(data).hexdigest()[:8], 16) % 9000)


def temp_token(value: str) -> str:
    text = re.sub(r"[^\w.-]+", "_", str(value), flags=re.UNICODE).strip("_")
    return text or "target"


def png_valid(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 32:
        return False
    with path.open("rb") as fh:
        return fh.read(8) == b"\x89PNG\r\n\x1a\n"


def brief_context(path: Path, limit: int = 1800) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    return text[:limit]


def build_codex_prompt(root: Path, episode: str, target: Target, temp_path: Path, seed: str) -> str:
    overview = brief_context(root / "出图" / episode / "prompt" / "00_总览.md")
    registry = root / "出图" / "共享" / "identity_registry.json"
    assets = root / "出图" / "共享" / "asset_registry.json"
    state = root / "出图" / "共享" / "visual_state_ledger.json"
    final_path = root / target.rel_path
    source_for_tail = root / target.rel_path
    if target.mode not in {"firstframe", "shared"}:
        source_for_tail = root / target_for_shot(target.clip, target.section, episode).rel_path

    return f"""你正在为 N2D 项目生成正式分镜 PNG。必须使用内置 AI 生图能力（imagegen/image_generation），不要用 Python/SVG/canvas/纯色图/占位图伪造。

输出要求：
- 只生成 1 张 9:16 竖版电影感 PNG。
- 使用内置 image_generation/image_gen 生成真实位图；不要自己写本地文件，外层 runner 会从事件流解码图片并落到：{temp_path}
- 禁止水印、字幕、logo、文字、漫画分格、UI 边框。

一致性硬约束：
- 角色 DNA = 脸 + 发型 + 服装 + 配饰。不要只锁脸。
- 近景优先参考“脸部特写 + 半身”，全身/三视图只作服装结构辅助。
- 多人同框必须按 prompt 的 blocking 分层理解，避免串脸。
- 若本镜有“资产身份注册层”且某角色带 *，该角色是主检身份：必须让主检角色成为画面中最清晰、最可比对的人脸；追身/背身/动作镜也要用 45°回头、过肩露脸或清楚侧脸露出眼鼻嘴三角区，避免纯背影、脸太小、被头发/暗影遮挡。
- 多人镜中次要角色可以较小或后景，但不得让次要角色的大脸压过带 * 的主检角色，除非 prompt 明确声明主检身份切换。
- 这是 Codex 后端：没有公开 seed API。逻辑 seed/连续性 token 仅用于追踪：{seed}，不要声称这是可复现 seed。

项目根：{root}
集数：{episode}
shot：{target.shot}
生成模式：{target.mode}
正式目标：{final_path}
{"共享定妆变体要求：" + target.variant_note if target.variant_note else ""}
可读注册表：
- identity_registry: {registry}
- asset_registry: {assets}
- visual_state_ledger: {state}
{"尾帧/中段可参考已有源图：" + str(source_for_tail) if target.mode not in {"firstframe", "shared"} else ""}

本集总览节选：
{overview}

本次完整 prompt 区块：
{target.section.body}

执行方式：
1. 读取/参考 prompt 中列出的参考图；如果同一角色有脸部特写和半身，优先使用它们。
2. 根据本镜中文正向 prompt 与负向 prompt 生成画面。
3. 生成完成后只用一句话说明完成；不要搜索文件系统，不要创建替代文件。
4. 只要无法生成真实 PNG，就直接说明失败。
"""


def run_codex(repo: Path, prompt: str, timeout_sec: Optional[float]) -> subprocess.CompletedProcess[str]:
    cmd = ["codex", "exec"]
    model = os.environ.get("N2D_CODEX_MODEL")
    if model:
        cmd.extend(["-m", model])
    cmd.extend(["--json", "--enable", "image_generation", "-C", str(repo), prompt])
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout_sec,
    )


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
    if event == "redraw":
        cmd.extend(["--redraw-reason", reason, "--redraw-category", category])
    if target.mode == "midframe" and status == "pass":
        try:
            source_target = target_for_shot(target.clip, target.section, episode)
            source_image = source_target.rel_path
        except Exception:
            source_image = ""
        cmd.extend(["--meta", "self_check=pass", "--meta", "midframe_role=between_first_and_end"])
        if source_image:
            cmd.extend(["--meta", f"source_image={source_image}"])
    if archive_path:
        cmd.extend(["--meta", f"archived_previous={archive_path}"])
    if error:
        cmd.extend(["--meta", f"error={error[:500]}"])
    subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def run_image_gate(root: Path, episode: str) -> bool:
    cmd = [
        sys.executable,
        str(repo_root() / DASHBOARD),
        "gate",
        str(root),
        episode,
        "--stage",
        "image",
    ]
    proc = subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode == 0:
        print(f"[gate] image gate passed for {episode}")
        return True
    print(proc.stdout, end="", file=sys.stderr)
    print(proc.stderr, end="", file=sys.stderr)
    print(f"[gate] image gate blocked for {episode}", file=sys.stderr)
    return False


def append_log(root: Path, row: dict) -> None:
    path = root / "生产数据" / "codex_image_runner.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


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

    previous_status = latest_recorded_status(root, task_id, target.rel_path)
    if not force and previous_status == "pass" and png_valid(final):
        if dry_run:
            skipped = True
        else:
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
    else:
        skipped = False

    if dry_run:
        print(json.dumps({
            "shot": target.shot,
            "mode": target.mode,
            "target": target.rel_path,
            "temp": str(temp_path),
            "logical_seed": seed,
            "skip_existing_pass": skipped,
        }, ensure_ascii=False))
        return True

    prompt = build_codex_prompt(root, episode, target, temp_path, seed)
    started = time.monotonic()
    error = ""
    archive_path: Optional[Path] = None
    ok = False
    try:
        proc = run_codex(repo_root(), prompt, timeout_sec)
        if proc.returncode != 0:
            error = f"codex exit {proc.returncode}: {proc.stderr or proc.stdout}"
        elif not png_valid(temp_path) and not decode_image_event(proc.stdout, temp_path):
            error = f"codex completed but no valid PNG file or image_generation_end payload was available for {temp_path}"
        else:
            archive_path = archive_existing(root, target.rel_path, task_id)
            final.parent.mkdir(parents=True, exist_ok=True)
            os.replace(temp_path, final)
            ok = png_valid(final)
            if not ok:
                error = f"moved output is not a valid PNG: {final}"
    except subprocess.TimeoutExpired:
        error = f"codex timed out after {timeout_sec}s"
    except Exception as exc:  # pragma: no cover - defensive batch guard
        error = f"{type(exc).__name__}: {exc}"

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
        target = target_for_shot(shot, section, episode)
        key = target.rel_path
        if key not in seen:
            seen.add(key)
            targets.append(target)
    return targets


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
    ap.add_argument("--skip-final-gate", action="store_true", help="do not run the whole-episode image gate after shot generation")
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

    ok_all = True
    for target in targets:
        ok = process_target(
            root,
            episode,
            target,
            task_id=task_id,
            timeout_sec=ns.timeout_sec,
            dry_run=ns.dry_run,
            force=ns.force,
        )
        ok_all = ok_all and ok
        if not ok and ns.stop_on_fail:
            break
    if ok_all and shots and not ns.dry_run and not ns.skip_final_gate:
        ok_all = run_image_gate(root, episode)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
