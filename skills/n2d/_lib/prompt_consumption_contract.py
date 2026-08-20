#!/usr/bin/env python3
"""Producer-owned canonical fingerprints for image/video prompt consumption."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from content_fingerprint import build_content_fingerprint, fingerprint_issues as generic_fingerprint_issues


PROMPT_FILES = {
    "image_prompt": ("出图/{episode}/prompt/00_总览.md", "出图/{episode}/prompt/01_分镜出图.md"),
    "video_prompt": ("出视频/{episode}/prompt/00_总览.md", "出视频/{episode}/prompt/01_clips.md"),
}


def source_patterns(scope: str, episode: str) -> list[str]:
    common = [
        f"脚本/{episode}/storyboard.json",
        f"脚本/{episode}/continuity_chain.json",
        f"脚本/{episode}/shot_reverse_contract.json",
        f"生产数据/script_quality_contract_{episode}.json",
        f"生产数据/director_camera_plan_{episode}.json",
        f"生产数据/reference_plan_{episode}.json",
    ]
    if scope == "image_prompt":
        extra = [
            "_设置.md",
            f"脚本/{episode}/素材清单.md",
            f"生产数据/production_mode_route_{episode}.json",
            "设定库/global_style.md",
            "设定库/source_comprehension.json",
            "设定库/characters/**/*",
            "设定库/locations/**/*",
            "设定库/参考资料/视觉参考/**/*",
            "角色库/**/*",
            "出图/共享/identity_registry.json",
            "出图/共享/asset_registry.json",
            "出图/共享/style_anchor_registry.json",
            "出图/共享/图片/*",
        ]
    elif scope == "video_prompt":
        extra = [
            "_设置.md",
            f"生产数据/production_mode_route_{episode}.json",
            f"生产数据/mouth_visible_audit_{episode}.json",
            f"出视频/{episode}/prompt/video_model_routes.json",
            "出图/共享/identity_registry.json",
            "出图/共享/asset_registry.json",
            f"出图/{episode}/prompt/00_总览.md",
        ]
    else:
        raise ValueError(f"unsupported prompt consumption scope: {scope}")
    prompts = [value.format(episode=episode) for value in PROMPT_FILES[scope]]
    return list(dict.fromkeys(common + extra + prompts))


def build_fingerprint(root: str | Path, episode: str, scope: str) -> Dict[str, Any]:
    return build_content_fingerprint(
        root,
        scope=f"{scope}_consumption",
        source_patterns=source_patterns(scope, episode),
        values={"episode": episode, "scope": scope},
    )


def fingerprint_issues(root: str | Path, episode: str, scope: str, recorded: Any) -> list[str]:
    issues = generic_fingerprint_issues(root, recorded)
    expected = build_fingerprint(root, episode, scope)
    if not isinstance(recorded, Mapping) or str(recorded.get("sha256") or "") != expected["sha256"]:
        issues.append("input_fingerprint_not_exact_prompt_consumption_contract")
    return list(dict.fromkeys(issues))
