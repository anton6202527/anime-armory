#!/usr/bin/env python3
"""出图→出视频 逐镜「身份交接」「物料约束交接」继承校验（单一真值源）。

视觉契约五字段（n2d_contract_diff）管 episode 级色调/光位/轴线/状态/景别，**不含逐镜的脸和资产**。
本模块补两项逐镜契约级机检：

  - 身份交接（②）：命名角色镜（identity_requirement != none）的逐镜 video prompt 是否
    真锁了身份（声明 + 具体锚点 CHAR_xx/定妆_/reference_group/character_id/face_lock/…），
    同时检查多锚帧 Clip 是否把首/中/尾锚到同一 registry/reference_group，跨情绪近景是否使用
    expressions +「锁脸不锁情」契约，否则 block（首帧脸→视频脸无契约锚，出视频必脸漂）；
  - 物料约束交接（C）：出图逐镜绑定的 LOC/PROP/WEAPON/OUTFIT/VFX 资产，出视频对应镜不得丢失
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
CHAR_REF_RE = re.compile(r"\b(CHAR_[A-Za-z0-9_]+(?:/[^\s`，；、。*）)]+)?)")
FIRST_FRAME_RE = re.compile(r"\*\*首帧\*\*[^`]*`([^`]+\.png)`")
END_FRAME_RE = re.compile(r"\*\*尾帧\*\*[^`]*`([^`]+\.png)`")
MID_FRAME_RE = re.compile(r"\*\*(?:中段)?锚帧\s*\d*\*\*[^`]*`([^`]+\.png)`")
EXPR_SOURCE_RE = re.compile(r"expressions|表情参考|表情定妆|_expr|_表情_|expression reference", re.IGNORECASE)
LOCK_FACE_RE = re.compile(r"锁脸不锁情|lock face not emotion|face shape|facial proportions|脸型|五官比例|眼距|鼻梁|下颌|骨相", re.IGNORECASE)
FACE_INVARIANT_RE = re.compile(r"脸型|五官|眼距|鼻梁|下颌|骨相|发际线|痣疤|facial proportions|face shape", re.IGNORECASE)
HAIR_OR_ACCESSORY_RE = re.compile(r"发型|发髻|发色|标志配饰|配饰|signature", re.IGNORECASE)
OUTFIT_RE = re.compile(r"服装配色|服装|配色|costume palette|outfit", re.IGNORECASE)
NATIVE_BINDING_RE = re.compile(r"character_id|face_lock|reference[ _]controls|主体库|cameo|LoRA", re.IGNORECASE)
REFERENCE_GROUP_BINDING_RE = re.compile(
    r"(?:reference_group|参考组)\s*(?:=|:|：)\s*[^；;，。\n]+|"
    r"identity_registry\.reference_group\s*(?:=|:|：)\s*[^；;，。\n]+",
    re.IGNORECASE,
)
BIG_EXPRESSION_VALUES = {"大", "big", "large", "cross_emotion"}
CLOSEUP_MARKERS = (
    "CU", "ECU", "MCU", "BCU", "特写", "近景", "脸部", "面部",
    "反打", "正反打", "过肩", "OTS", "dialogue_shot_reverse", "dialogue_closeup",
)
# 高动作/落地/命中 beat 标记（G-V2·2026-06-24）：动作镜「首帧蓄势+尾帧落点」是仅次于身份锁的
# 第二强一致性杠杆，缺尾帧硬约束时后端易『假动/静态合理化』或动作不完成（2026 物理合规<30%）。
ACTION_BEAT_MARKERS = (
    "打斗", "交手", "对打", "厮杀", "格挡", "出拳", "挥拳", "挥剑", "挥刀", "拔剑", "劈", "斩",
    "砍", "刺", "踢", "腾空", "跃起", "飞身", "翻滚", "翻身", "纵身", "坠落", "跌落", "摔落",
    "坠地", "砸", "撞击", "冲撞", "扑向", "扑倒", "接住", "击中", "命中", "重击", "追逐", "追击",
    "疾驰", "奔袭", "爆炸", "炸开", "冲击波", "落地", "着地", "降落", "腾云", "驾雾", "御剑",
    "impact", "punch", "kick", "slash", "leap", "crash",
)
# 显式高动作强度声明（storyboard continuity 字段）。
HIGH_MOTION_VALUES = {"高", "大", "high", "violent", "large", "intense"}
# 逐镜资产 id（场景/道具/武器/服装/特效）。
ASSET_HANDOFF_ID_RE = re.compile(r"(?:LOC|PROP|WEAPON|OUTFIT|VFX)_[A-Za-z0-9_]+")
PNG_REF_RE = re.compile(r"`([^`]+\.png)`|([^\s`，,；;。)）]+\.png)")


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


def _png_refs(text: str) -> list[str]:
    """文本中的 PNG 路径引用。优先兼容 markdown 反引号路径，也容忍裸路径。"""
    refs = []
    for m in PNG_REF_RE.finditer(str(text or "")):
        ref = (m.group(1) or m.group(2) or "").strip()
        if ref:
            refs.append(ref)
    return refs


def _png_stem(path: str) -> str:
    """PNG 路径 → 文件 stem，用于 split relay 后按首帧回溯出图逻辑块。"""
    return os.path.splitext(os.path.basename(str(path or "").strip()))[0]


def _index_image_blocks_by_png_stem(img_blocks: dict[int, str]) -> dict[str, tuple[int, str]]:
    """出图块中 `**目标**` 的首/中/尾 PNG 都可作为视频物理段首帧来源。"""
    out = {}
    for num, block in img_blocks.items():
        for ref in _png_refs(block):
            stem = _png_stem(ref)
            if stem and stem not in out:
                out[stem] = (num, block)
    return out


def _source_image_block_for_video(
    video_num: int,
    video_block: str,
    img_blocks: dict[int, str],
    img_by_png_stem: dict[str, tuple[int, str]],
) -> tuple[int | None, str | None, str]:
    """视频物理 Clip → 出图逻辑 Clip。

    split relay 会把一个出图逻辑 Clip 拆成多个视频物理 Clip，例如视频 Clip_05/06
    都来自 `Clip03_外门遗孤*.png`。资产继承必须按真实首帧来源回溯，不能按物理
    Clip 编号硬对齐；旧项目没有首帧引用时才回退数字对齐。
    """
    refs = _frame_refs(video_block).get("first") or _png_refs(video_block)
    for ref in refs:
        stem = _png_stem(ref)
        if stem in img_by_png_stem:
            img_num, img_block = img_by_png_stem[stem]
            return img_num, img_block, f"firstframe:{stem}"
    if video_num in img_blocks:
        return video_num, img_blocks[video_num], "clip_number_fallback"
    return None, None, "unmatched"


def clip_block_locks_identity(block_text: str) -> bool:
    """命名角色镜的逐镜 video prompt 是否真锁了身份：既要有身份锁定声明，又要落到具体锚点
    （CHAR_xx / 定妆_ / reference_group / character_id / face_lock / 脸部特写 / 主体库 / cameo）。纯函数·可测。"""
    text = str(block_text or "")
    has_decl = any(m in text for m in IDENTITY_DECL_MARKERS)
    has_anchor = bool(IDENTITY_ANCHOR_RE.search(text))
    return has_decl and has_anchor


def _load_json(path: str):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _frame_refs(block_text: str) -> dict:
    """逐镜 video prompt 块里的首/中/尾锚帧引用。纯函数·可测。"""
    text = str(block_text or "")
    first = [m.group(1).strip() for m in FIRST_FRAME_RE.finditer(text)]
    mid = [m.group(1).strip() for m in MID_FRAME_RE.finditer(text)]
    end = [m.group(1).strip() for m in END_FRAME_RE.finditer(text)]
    return {"first": first, "mid": mid, "end": end, "all": first + mid + end}


def _char_refs(text: str) -> set:
    """文本里的显式角色身份绑定，归一掉 primary 星号等装饰。纯函数·可测。"""
    out = set()
    for raw in CHAR_REF_RE.findall(str(text or "")):
        item = raw.strip().strip("*`，；、。)")
        if item:
            out.add(item)
    return out


def _base_char(ref: str) -> str:
    return str(ref or "").split("/", 1)[0]


def _has_face_invariants(text: str) -> bool:
    """同一角色首/中/尾多锚帧必须锁住脸、发型/配饰、服装配色三组身份不变量。"""
    value = str(text or "")
    return bool(FACE_INVARIANT_RE.search(value) and HAIR_OR_ACCESSORY_RE.search(value) and OUTFIT_RE.search(value))


def _has_reference_group(text: str) -> bool:
    return bool(REFERENCE_GROUP_BINDING_RE.search(str(text or "")))


def _has_native_binding(text: str) -> bool:
    return bool(NATIVE_BINDING_RE.search(str(text or "")))


def _storyboard_clip_meta(root: str, ep: str) -> dict:
    """storyboard.json → {clip_num: {expression_span, closeup, need_endframe}}。缺文件返回空。

    `shot_intent.json` 里的 expression_span/need_endframe/motion_intensity 是 storyboard 快照投影，
    不是作者 override；生成/交接契约必须继续以 storyboard 为真值源，避免 gate 与生成侧读不同值。
    """
    path = os.path.join(root, "脚本", ep, "storyboard.json")
    data = _load_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("clips"), list):
        return {}
    out = {}
    for idx, clip in enumerate(data.get("clips") or [], 1):
        if not isinstance(clip, dict):
            continue
        cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
        blob = " ".join(str(clip.get(k) or "") for k in ("template", "label", "shot_type", "description"))
        for shot in clip.get("shots") or []:
            if isinstance(shot, dict):
                blob += " " + " ".join(str(shot.get(k) or "") for k in ("lens", "desc", "shot_size"))
        out[idx] = {
            "expression_span": str(cont.get("expression_span") or "").strip(),
            "need_endframe": cont.get("need_endframe") is True,
            "closeup": any(m in blob for m in CLOSEUP_MARKERS),
            "action_beat": _is_action_beat_blob(blob, cont),
            "motion_intensity": str(cont.get("motion_intensity") or "").strip(),
        }
    return out


def _overlay_shot_intent(root: str, ep: str, meta: dict) -> None:
    """Deprecated no-op.

    Kept only for older imports/tests.  Derived fields in `shot_intent.json` do not override storyboard.
    """
    return None


def _is_action_beat_blob(blob: str, cont: dict) -> bool:
    """从镜头描述 blob + continuity 判是否高动作/落地/命中 beat。纯函数·可测。"""
    if any(m in str(blob or "") for m in ACTION_BEAT_MARKERS):
        return True
    if cont.get("spectacle") is True or cont.get("action_beat") is True:
        return True
    return str(cont.get("motion_intensity") or "").strip().lower() in HIGH_MOTION_VALUES


def _check_multiframe_identity_contract(res: dict, clip_id: str, block: str, image_block: str = "") -> None:
    """首/中/尾多锚帧角色镜：同一角色必须走同一 registry/reference_group 身份契约。"""
    refs = _frame_refs(block)
    if len(refs["all"]) <= 1:
        return
    video_chars = _char_refs(block)
    image_chars = _char_refs(image_block)
    if not video_chars:
        res["findings"].append({
            "clip_id": clip_id,
            "severity": "block",
            "code": "identity_anchor_character_missing",
            "note": (f"{clip_id}：本 Clip 使用首/中/尾多锚帧 {refs['all']}，但逐镜 prompt 未写明确 `CHAR_xx/形态`。"
                     "多锚帧必须绑定同一 identity_registry 角色/形态，禁止只靠画面路径或中文姓名让后端猜同一张脸。"),
        })
        return
    if image_chars and not {_base_char(c) for c in image_chars}.issubset({_base_char(c) for c in video_chars}):
        res["findings"].append({
            "clip_id": clip_id,
            "severity": "block",
            "code": "identity_anchor_character_mismatch",
            "note": (f"{clip_id}：出图逐镜绑定角色 {sorted(image_chars)}，但出视频逐镜只绑定 {sorted(video_chars)}。"
                     "首/中/尾锚帧必须继承同一角色身份，不能在视频 prompt 里漏角色或换形态。"),
        })
    if not _has_reference_group(block):
        res["findings"].append({
            "clip_id": clip_id,
            "severity": "block",
            "code": "identity_anchor_reference_group_missing",
            "note": (f"{clip_id}：多锚帧角色 Clip 缺 `reference_group` 兜底。"
                     "即使目标后端支持 Character ID / Face Lock / reference controls，也必须把同一套 registry reference_group 作为首/中/尾同源身份锚，防止锚图脸不一致时被视频模型放大成片内脸漂。"),
        })
    if not _has_face_invariants(block):
        res["findings"].append({
            "clip_id": clip_id,
            "severity": "block",
            "code": "identity_anchor_invariants_missing",
            "note": (f"{clip_id}：多锚帧角色 Clip 未同时锁住脸型/五官比例、发型/配饰、服装配色。"
                     "首/中/尾锚图看起来各自合格也可能不是同一个人；视频 prompt 必须显式写这些不变量，做到锁脸不锁表演。"),
        })
    # 有原生绑定时它是加分项；没有时不单独 block，因为 reference_group + 双/多帧是合法 fallback。
    if not _has_native_binding(block):
        res["findings"].append({
            "clip_id": clip_id,
            "severity": "warn",
            "code": "identity_anchor_native_binding_absent",
            "note": (f"{clip_id}：多锚帧角色 Clip 未见 Character ID / Face Lock / reference controls / LoRA 等原生身份绑定。"
                     "若目标后端支持，应同时喂角色 ID；不支持时需限制表情/转头/运镜幅度，必要时降 MCU/侧脸/手部反应镜或拆 Clip。"),
        })


def _check_big_expression_contract(res: dict, clip_id: str, block: str, meta: dict) -> None:
    """大表情近景：必须同源 expressions + 首尾双帧 + 锁脸不锁情。"""
    if not meta or meta.get("expression_span") not in BIG_EXPRESSION_VALUES or not meta.get("closeup"):
        return
    refs = _frame_refs(block)
    if not refs["end"]:
        res["findings"].append({
            "clip_id": clip_id,
            "severity": "block",
            "code": "big_expression_endframe_missing",
            "note": (f"{clip_id}：storyboard 标记大表情近景，但视频 prompt 没有 `**尾帧**`。"
                     "大表情近景必须首=起表情、尾=止表情同源定妆/expressions，只做插值；单首帧自由生成会把脸型和五官比例带着重画。"),
        })
    if not EXPR_SOURCE_RE.search(block):
        res["findings"].append({
            "clip_id": clip_id,
            "severity": "block",
            "code": "big_expression_expressions_missing",
            "note": (f"{clip_id}：大表情近景缺同源 `expressions` / 表情参考 / 表情定妆引用。"
                     "止表情必须来自 identity_registry.reference_group.expressions 或同源表情定妆，不得让模型凭文字跨情绪改脸。"),
        })
    for marker in ("表情锚", "表情幅度"):
        if marker not in block:
            res["findings"].append({
                "clip_id": clip_id,
                "severity": "block",
                "code": "big_expression_field_missing",
                "note": f"{clip_id}：大表情近景缺 `{marker}` 字段；必须写起→止表情和幅度封顶，避免表情自由发挥成换脸。",
            })
    if not LOCK_FACE_RE.search(block):
        res["findings"].append({
            "clip_id": clip_id,
            "severity": "block",
            "code": "big_expression_lock_face_missing",
            "note": (f"{clip_id}：大表情近景缺「锁脸不锁情」/脸型五官比例不变的负向约束。"
                     "必须声明表情只动面部肌肉，脸型、眼距、鼻梁、下颌、发际线、痣疤保持不变。"),
        })


def _is_action_beat(meta: dict) -> bool:
    """该镜是否被 storyboard 判为高动作/落地/命中 beat。纯函数·可测。"""
    return bool(meta) and bool(meta.get("action_beat"))


def _check_action_beat_contract(res: dict, clip_id: str, block: str, meta: dict) -> None:
    """高动作/落地/命中 beat：首=蓄势、尾=落点的首尾帧硬约束是动作镜第二强一致性杠杆。

    缺尾帧时动作镜易『假动/静态合理化』或动作不完成（2026 物理合规<30%、可灵默认把激烈动作降慢动作、
    clip 末段易掉帧）。动作 beat 由关键词/强度启发式检出（比 expression_span 显式字段误报率高），
    故缺尾帧只 warn 交人判，不像大表情近景那样 block。大表情近景已强制尾帧，这里不重复报。
    """
    if not _is_action_beat(meta):
        return
    if meta.get("expression_span") in BIG_EXPRESSION_VALUES and meta.get("closeup"):
        return
    if not _frame_refs(block)["end"]:
        res["findings"].append({
            "clip_id": clip_id,
            "severity": "warn",
            "code": "action_beat_endframe_missing",
            "note": (f"{clip_id}：storyboard 标记高动作/落地/命中 beat，但视频 prompt 没有 `**尾帧**`。"
                     "动作镜易『假动/静态合理化』或动作不完成——建议补尾帧作落点（首=蓄势、尾=命中/落地/收招），"
                     "让支持首尾帧硬约束的后端插值出完整动作弧线，而非靠首帧自由外推。"),
        })


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
    img_blocks = {}
    img_path = os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")
    if os.path.isfile(img_path):
        img_blocks = split_video_clip_blocks(open(img_path, encoding="utf-8").read())
    clip_meta = _storyboard_clip_meta(root, ep)
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
            continue
        _check_multiframe_identity_contract(
            res,
            nr["clip_id"],
            blk,
            img_blocks.get(nr["clip_num"], ""),
        )
        _check_big_expression_contract(res, nr["clip_id"], blk, clip_meta.get(nr["clip_num"], {}))
        _check_action_beat_contract(res, nr["clip_id"], blk, clip_meta.get(nr["clip_num"], {}))
    return res


# ── 物料约束交接（C：场景/道具/武器/服装/特效的逐镜资产交接 Diff） ────────────────────────
# 视觉契约五字段在 episode 级管场景光位锚/轴线（已 block），但**逐镜**绑定的具体资产
# （LOC_xx 场景 / PROP_xx 道具 / WEAPON_xx 武器 / OUTFIT_xx 服装 / VFX_xx 特效）有没有从出图诚实交接到出视频，
# 此前无机检。出图逐镜 `资产引用注册层` 绑了 PROP_01，出视频该镜若把它丢了 → 该道具在视频侧无
# reference_group/constraints/drift_forbidden 锚 → 道具/特效跨镜漂移。本检查逐镜 Diff 资产 id 集合。
def extract_asset_ids(text: str) -> set:
    """逐镜块文本 → 资产 id 集合（LOC/PROP/WEAPON/OUTFIT/VFX_xx）。纯函数·可测。"""
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
    img_by_png_stem = _index_image_blocks_by_png_stem(img_blocks)
    id2name = asset_id_to_name(root)
    res["available"] = True
    matched_image_nums = set()
    for num in sorted(vid_blocks):
        clip_id = f"Clip_{num:02d}"
        source_num, source_block, source_reason = _source_image_block_for_video(
            num, vid_blocks[num], img_blocks, img_by_png_stem
        )
        if source_block is None:
            continue
        img_assets = extract_asset_ids(source_block)
        if not img_assets:
            continue
        matched_image_nums.add(source_num)
        res["checked"] += 1
        dropped = sorted(img_assets - extract_asset_ids(vid_blocks[num]))
        if dropped:
            # 资产 id 丢失（可能是有意的松引用，如记忆遮罩/转场只提名字）= warn，交人确认；
            # 不 block（不像人脸交接那样必然崩），但每个丢失都要醒目入账，避免执行端默默取不到 constraints。
            names = "、".join(f"{aid}({id2name.get(aid, '?')})" for aid in dropped)
            source_note = f"；source=Clip_{source_num:02d}({source_reason})" if source_num else ""
            res["findings"].append({
                "clip_id": clip_id, "severity": "warn", "code": "asset_handoff_dropped",
                "note": (f"{clip_id}：出图绑定的资产 {names} 在出视频逐镜 prompt 丢了 id"
                         f"{source_note}"
                         "——执行端取不到其 reference_group/constraints/drift_forbidden，若非有意松引用，"
                         "补回 LOC/PROP/WEAPON/VFX_xx 让结构/颜色/光位锚自动继承（防场景/道具/武器/特效跨镜漂移）。"),
            })
    for num in sorted(img_blocks):
        if num in matched_image_nums:
            continue
        img_assets = extract_asset_ids(img_blocks[num])
        if not img_assets:
            continue
        if num in vid_blocks:
            continue
        # 整个逐镜 prompt 缺失（结构性、高精度）= block，同 identity_clip_prompt_missing。
        clip_id = f"Clip_{num:02d}"
        res["findings"].append({
            "clip_id": clip_id, "severity": "block", "code": "asset_clip_prompt_missing",
            "note": (f"{clip_id}：出图绑定资产 {sorted(img_assets)}，但 01_clips.md 无对应逐镜 prompt"
                     "——资产在视频侧无锚，易场景/道具/特效漂移。"),
        })
    return res
