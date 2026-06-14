#!/usr/bin/env python3
"""出图→出视频 逐镜「身份交接」「物料约束交接」继承校验（单一真值源）。

视觉契约五字段（n2d_contract_diff）管 episode 级色调/光位/轴线/状态/景别，**不含逐镜的脸和资产**。
本模块补两项逐镜契约级机检：

  - 身份交接（②）：命名角色镜（identity_requirement != none）的逐镜 video prompt 是否
    真锁了身份（声明 + 具体锚点 CHAR_xx/定妆_/reference_group/character_id/face_lock/…），
    否则 block（首帧脸→视频脸无契约锚，出视频必脸漂）；
  - 物料约束交接（C）：出图逐镜绑定的 LOC/PROP/OUTFIT/VFX 资产，出视频对应镜不得丢失
    （整镜 prompt 缺失=block；仅 id 丢失=warn，交人确认是否有意松引用）。

提到 `n2d/_lib` 作单一真值源，与 n2d_contract_diff 同因：让 n2d-review/gate.py 能在 common 层
直接调用这两项校验，而非反向 import n2d-video；inherit_contract.py 与 gate.py 都从这里取。

纯 stdlib，所有解析函数纯函数·可测；check_* 仅做文件 IO + 组装 finding。
"""
from __future__ import annotations

import json
import os
import re

# ── 身份交接 ──────────────────────────────────────────────────────────────────
ROUTE_IDENTITY_NONE = "none"
# 逐镜 video prompt 里「声明了身份锁定」的字段名（中/英两套写法都认）。
IDENTITY_DECL_MARKERS = ("身份锁定", "身份注册层", "identity lock", "identity adapter", "identity_requirement")
# 声明必须落到可执行锚点，不能只是空喊「锁身份」。
IDENTITY_ANCHOR_RE = re.compile(
    r"CHAR_[A-Za-z0-9_]+|定妆_|reference_group|character_id|face_lock|reference[ _]controls|脸部特写|主体库|cameo",
    re.IGNORECASE,
)
# 逐镜资产 id（场景/道具/服装/特效）。
ASSET_HANDOFF_ID_RE = re.compile(r"(?:LOC|PROP|OUTFIT|VFX)_[A-Za-z0-9]+")


def _clip_num(text: str):
    """从 'Clip_03' / '## Clip 03（…' / 'EP01_CLIP03' 提镜号 → int；提不出 → None。纯函数·可测。"""
    m = re.search(r"(\d+)", str(text or ""))
    return int(m.group(1)) if m else None


def parse_named_character_routes(routes_json_text: str):
    """video_model_routes.json 文本 → 命名角色镜路由 [{clip_id, clip_num, identity_requirement}]。

    只保留 identity_requirement != none 的镜（= 有命名角色、需要锁脸）；解析失败返回 None。纯函数·可测。
    """
    try:
        data = json.loads(routes_json_text)
    except Exception:
        return None
    out = []
    for r in data.get("routes") or []:
        if not isinstance(r, dict):
            continue
        req = str(r.get("identity_requirement") or ROUTE_IDENTITY_NONE).strip()
        if req == ROUTE_IDENTITY_NONE or not req:
            continue
        cid = str(r.get("clip_id") or "").strip()
        out.append({"clip_id": cid, "clip_num": _clip_num(cid), "identity_requirement": req})
    return out


def split_video_clip_blocks(clips_md: str):
    """01_clips.md → {clip_num: block_text}，按 '## Clip NN' 标题切。纯函数·可测。"""
    blocks = {}
    cur_num = None
    cur = []
    for line in str(clips_md or "").splitlines():
        if line.startswith("## ") and ("Clip" in line or "clip" in line):
            if cur_num is not None:
                blocks[cur_num] = "\n".join(cur)
            cur_num = _clip_num(line)
            cur = [line]
        elif cur_num is not None:
            cur.append(line)
    if cur_num is not None:
        blocks[cur_num] = "\n".join(cur)
    return blocks


def clip_block_locks_identity(block_text: str) -> bool:
    """命名角色镜的逐镜 video prompt 是否真锁了身份：既要有身份锁定声明，又要落到具体锚点
    （CHAR_xx / 定妆_ / reference_group / character_id / face_lock / 脸部特写 / 主体库 / cameo）。纯函数·可测。"""
    text = str(block_text or "")
    has_decl = any(m in text for m in IDENTITY_DECL_MARKERS)
    has_anchor = bool(IDENTITY_ANCHOR_RE.search(text))
    return has_decl and has_anchor


def check_identity_handoff(root: str, ep: str) -> dict:
    """对每个命名角色镜核验逐镜 video prompt 写了身份锁定 + 具体锚点（②）。

    缺 routes / 缺 01_clips.md → available=False、无 finding（上游未到位，不在本检查拦，
    由 router/video 阶段各自的 gate 负责）；只在两文件都在时做硬核验。
    """
    routes_rel = os.path.join("出视频", ep, "prompt", "video_model_routes.json")
    clips_rel = os.path.join("出视频", ep, "prompt", "01_clips.md")
    routes_path = os.path.join(root, routes_rel)
    clips_path = os.path.join(root, clips_rel)
    res = {"available": False, "findings": [], "checked": 0, "notes": [],
           "routes_file": routes_rel, "clips_file": clips_rel}
    if not os.path.isfile(routes_path):
        res["notes"].append("无 video_model_routes.json——跳过身份交接校验（先跑 n2d-model-router）。")
        return res
    named = parse_named_character_routes(open(routes_path, encoding="utf-8").read())
    if named is None:
        res["notes"].append("video_model_routes.json 解析失败——跳过身份交接校验。")
        return res
    if not os.path.isfile(clips_path):
        res["notes"].append("无 01_clips.md——跳过身份交接校验（先跑 n2d-video 阶段A 写逐镜 prompt）。")
        return res
    blocks = split_video_clip_blocks(open(clips_path, encoding="utf-8").read())
    res["available"] = True
    for nr in named:
        res["checked"] += 1
        blk = blocks.get(nr["clip_num"])
        if blk is None:
            res["findings"].append({
                "clip_id": nr["clip_id"], "severity": "block", "code": "identity_clip_prompt_missing",
                "note": (f"{nr['clip_id']}：identity_requirement={nr['identity_requirement']} 命名角色镜，"
                         "但 01_clips.md 无对应逐镜 prompt——脸交接无锚，出视频必脸漂。"),
            })
            continue
        if not clip_block_locks_identity(blk):
            res["findings"].append({
                "clip_id": nr["clip_id"], "severity": "block", "code": "identity_lock_missing",
                "note": (f"{nr['clip_id']}：identity_requirement={nr['identity_requirement']}，但逐镜 prompt 未锁身份"
                         "（缺『身份锁定/身份注册层』声明或缺具体锚 CHAR_xx/定妆_/reference_group/character_id/face_lock/脸部特写）"
                         "——出图首帧脸→出视频脸无契约锚，易脸漂。"),
            })
    return res


# ── 物料约束交接（C：场景/道具/服装/特效的逐镜资产交接 Diff） ────────────────────────
# 视觉契约五字段在 episode 级管场景光位锚/轴线（已 block），但**逐镜**绑定的具体资产
# （LOC_xx 场景 / PROP_xx 道具 / OUTFIT_xx 服装 / VFX_xx 特效）有没有从出图诚实交接到出视频，
# 此前无机检。出图逐镜 `资产引用注册层` 绑了 PROP_01，出视频该镜若把它丢了 → 该道具在视频侧无
# reference_group/constraints/drift_forbidden 锚 → 道具/特效跨镜漂移。本检查逐镜 Diff 资产 id 集合。
def extract_asset_ids(text: str) -> set:
    """逐镜块文本 → 资产 id 集合（LOC/PROP/OUTFIT/VFX_xx）。纯函数·可测。"""
    return set(ASSET_HANDOFF_ID_RE.findall(str(text or "")))


def asset_id_to_name(root: str) -> dict:
    """asset_registry.json → {asset_id: name}，用于区分『id 丢但名字还在』(warn) 与『整个资产没了』(block)。"""
    try:
        data = json.loads(open(os.path.join(root, "出图", "共享", "asset_registry.json"), encoding="utf-8").read())
    except Exception:
        return {}
    out = {}
    for a in (data.get("assets") or []):
        aid = str(a.get("id") or "").strip()
        name = str(a.get("name") or "").strip()
        if aid and name:
            out[aid] = name
    return out


def check_asset_handoff(root: str, ep: str) -> dict:
    """逐镜资产约束继承 Diff（C）：出图 01_分镜出图.md 绑定的资产，出视频 01_clips.md 对应镜不得丢失。

    缺任一逐镜文件 → available=False、无 finding（上游未到位，各自 gate 负责）。
    """
    img_rel = os.path.join("出图", ep, "prompt", "01_分镜出图.md")
    vid_rel = os.path.join("出视频", ep, "prompt", "01_clips.md")
    img_path = os.path.join(root, img_rel)
    vid_path = os.path.join(root, vid_rel)
    res = {"available": False, "findings": [], "checked": 0, "notes": [],
           "image_clips_file": img_rel, "video_clips_file": vid_rel}
    if not os.path.isfile(img_path):
        res["notes"].append("无 出图/01_分镜出图.md——跳过资产约束继承校验。")
        return res
    if not os.path.isfile(vid_path):
        res["notes"].append("无 出视频/01_clips.md——跳过资产约束继承校验（先跑 n2d-video 阶段A）。")
        return res
    img_blocks = split_video_clip_blocks(open(img_path, encoding="utf-8").read())
    vid_blocks = split_video_clip_blocks(open(vid_path, encoding="utf-8").read())
    id2name = asset_id_to_name(root)
    res["available"] = True
    for num in sorted(img_blocks):
        img_assets = extract_asset_ids(img_blocks[num])
        if not img_assets:
            continue
        res["checked"] += 1
        clip_id = f"Clip_{num:02d}"
        vblk = vid_blocks.get(num)
        if vblk is None:
            # 整个逐镜 prompt 缺失（结构性、高精度）= block，同 identity_clip_prompt_missing。
            res["findings"].append({
                "clip_id": clip_id, "severity": "block", "code": "asset_clip_prompt_missing",
                "note": (f"{clip_id}：出图绑定资产 {sorted(img_assets)}，但 01_clips.md 无对应逐镜 prompt"
                         "——资产在视频侧无锚，易场景/道具/特效漂移。"),
            })
            continue
        dropped = sorted(img_assets - extract_asset_ids(vblk))
        if dropped:
            # 资产 id 丢失（可能是有意的松引用，如记忆遮罩/转场只提名字）= warn，交人确认；
            # 不 block（不像人脸交接那样必然崩），但每个丢失都要醒目入账，避免执行端默默取不到 constraints。
            names = "、".join(f"{aid}({id2name.get(aid, '?')})" for aid in dropped)
            res["findings"].append({
                "clip_id": clip_id, "severity": "warn", "code": "asset_handoff_dropped",
                "note": (f"{clip_id}：出图绑定的资产 {names} 在出视频逐镜 prompt 丢了 id"
                         "——执行端取不到其 reference_group/constraints/drift_forbidden，若非有意松引用，"
                         "补回 LOC/PROP/VFX_xx 让结构/颜色/光位锚自动继承（防场景/道具/特效跨镜漂移）。"),
            })
    return res
