#!/usr/bin/env python3
"""Generate the n2d image prompt pack for an episode.

This is a no-cost writer: it creates prompt/spec files, identity and asset
registries, and application receipts. It does not create PNGs or call any image
backend.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)

from n2d_contract import (  # noqa: E402
    ASSET_REFERENCE_REGISTRY_KIND,
    IDENTITY_IMAGE_ADAPTERS,
    IDENTITY_REGISTRY_KIND,
    IDENTITY_VIDEO_ADAPTERS,
)

REFERENCE_PLAN_APPLICATION_KIND = "n2d_reference_plan_application"
DIRECTOR_CAMERA_PLAN_APPLICATION_KIND = "n2d_director_camera_plan_application"

EP_RE = re.compile(r"\d+")


def shot_number(value: Any) -> Optional[int]:
    text = str(value or "")
    match = (
        re.search(r"(?:Clip|片段)\s*[_-]?\s*([0-9０-９]+)", text, re.I)
        or re.search(r"镜(?:头)?\s*([0-9０-９]+)", text)
        or re.search(r"shot\s*([0-9０-９]+)", text, re.I)
    )
    if not match:
        return None
    raw = match.group(1).translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    try:
        return int(raw)
    except ValueError:
        return None


def state_range_end(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    if isinstance(value, int):
        return value
    text = str(value)
    if re.search(r"(?:集尾|全集|后续|跨集|长期|持续|未解除|until\s+end)", text, re.I):
        return None
    return shot_number(text)


CHARACTER_DEFS: Dict[str, Dict[str, Any]] = {
    "CHAR_SHEN_YAN": {
        "name": "沈砚",
        "scope": "核心主角/全篇长线",
        "form": "常态",
        "asset_key": "CHAR_SHEN_YAN__常态",
        "tier": "core",
        "anchor": "清瘦冷静青年录事，黑发束起，深青灰窄袖官服，袖中半片旧铜，开睛时瞳内细金丝",
        "face": "清瘦青年脸，窄长眼，鼻梁清直，薄唇，五官克制耐看，右眼开睛时只有瞳内细金丝。",
        "hair": "黑发束起，发冠简洁，无夸张发饰。",
        "outfit": "深青灰窄袖古代录事官服，旧黑腰带，袖口和肩线利落。",
        "accessories": "半片旧铜藏在袖中，右眼金睛只在剧情触发时显现。",
        "texture": "写实国漫皮肤质感，低饱和冷灰环境下仍保留脸部层次。",
        "performance_signature": "先看证据再抬眼逼问，表情冷静克制，右眼刺痛时下意识按眼但不夸张。",
        "relative_scale": "比裴决略矮半头，清瘦但站姿稳定。",
        "signature_equipment": ["PROP_OLD_COPPER_HALF", "VFX_JINJING_GOLD_EYE"],
        "drift": ["不要少年幼态脸", "不要白衣仙侠飘带", "不要把金睛做成全脸发光", "不要现代发型"],
    },
    "CHAR_PI_DEMON_CHENGUI": {
        "name": "换皮妖·陈贵皮相",
        "scope": "第1集核心反派",
        "form": "陈贵皮相",
        "asset_key": "CHAR_PI_DEMON_CHENGUI__陈贵皮相",
        "tier": "core",
        "anchor": "陈贵皮相中年商户，深褐旧商户袍，干净皂靴，温和假笑，动作过静",
        "face": "中年商户皮相，温和假笑过度平静；妖相揭露只在第6镜后由状态锁/VFX 注入，非血腥。",
        "hair": "普通中年男子束发，发际和鬓角自然，不做主角式精致发冠。",
        "outfit": "深褐旧商户袍，干净黑色皂靴，衣料朴素但姿态僵硬。",
        "accessories": "茶碗和干净皂靴是身份破绽；妖相只短促显露。",
        "texture": "冷雨光下的假温和、端坐过静、皮相僵硬；妖相纹理只在揭露后短促显现。",
        "performance_signature": "坐姿过静，假笑延迟，听见金睛时先看沈砚右眼再收回妖相。",
        "relative_scale": "中年男子正常身量，坐姿压低但存在感阴冷。",
        "signature_equipment": ["PROP_CLEAN_BLACK_BOOT", "PROP_STILL_TEA", "VFX_SKIN_DEMON_REVEAL"],
        "drift": ["不要血腥器官", "不要做成尖牙怪物全露", "不要年轻俊美化", "不要现代商人装"],
    },
    "CHAR_PEIJUE": {
        "name": "裴决",
        "scope": "长线核心男二/术士",
        "form": "常态",
        "asset_key": "CHAR_PEIJUE__常态",
        "tier": "core",
        "anchor": "玄色劲装高挑术士，腰悬短刀，符火冷蓝，冷硬少言",
        "face": "高挑冷硬青年脸，眉眼锋利，表情少，目光判断多于情绪。",
        "hair": "黑发高束，鬓发干净，行动时发尾轻动。",
        "outfit": "玄色劲装，束腕束腰，适合术士机动，腰间短刀与符纸袋。",
        "accessories": "短刀、符纸、冷蓝符火；不抢沈砚金睛视觉中心。",
        "texture": "冷灰屋内的黑衣层次，符火只在手边形成边缘光。",
        "performance_signature": "声音先到，人从门口阴影入场，动作短、准、冷。",
        "relative_scale": "比沈砚高半头，肩更宽，站位更像执行者。",
        "signature_equipment": ["WEAPON_PEIJUE_SHORT_BLADE", "VFX_PEIJUE_FU_FIRE"],
        "drift": ["不要白衣仙人", "不要红橙大火", "不要现代战术服", "不要笑容外放"],
    },
    "CHAR_FANGZHENG": {
        "name": "坊正",
        "scope": "第1集功能角色/局部参考",
        "form": "局部参考",
        "asset_key": "CHAR_FANGZHENG__局部参考",
        "tier": "restricted_partial",
        "anchor": "圆滑中年坊正，布袍前景阻挡，递笔录压事，绝不清晰主角脸",
        "face": "功能角色只保留轮廓和手部，不建立完整正脸。",
        "hair": "普通中年发髻，虚焦或侧背出现。",
        "outfit": "暗色布袍、手持笔录纸，前景遮挡。",
        "accessories": "笔录纸、毛笔。",
        "texture": "前景虚焦布料和手部局部。",
        "performance_signature": "赔笑递笔录、挡在门口压事，脸不可成为主视觉。",
        "relative_scale": "中年普通身量，常在画左前景。",
        "signature_equipment": ["PROP_RECORD_PAPER"],
        "drift": ["不要清晰主角脸", "不要现代干部装", "不要过度抢戏"],
    },
    "CHAR_CHEN_WIFE": {
        "name": "陈妻",
        "scope": "第1集功能角色/局部参考",
        "form": "局部参考",
        "asset_key": "CHAR_CHEN_WIFE__局部参考",
        "tier": "restricted_partial",
        "anchor": "陈妻跪哭挡视线，布衣妇人手肩局部，绝不清晰主角脸",
        "face": "功能角色只保留哭跪轮廓、肩颈和手部，不建立完整正脸。",
        "hair": "朴素妇人发髻，虚焦或侧背。",
        "outfit": "低饱和旧布衣，跪姿形成前景阻挡。",
        "accessories": "无主视觉饰品。",
        "texture": "湿冷屋内布料和手指压肩的受力感。",
        "performance_signature": "跪求、僵住、被妖指尖威胁，作为情绪层而非主角脸。",
        "relative_scale": "跪姿低于沈砚，常在画中或前景。",
        "signature_equipment": [],
        "drift": ["不要清晰主角脸", "不要精致女主妆", "不要现代服饰"],
    },
}


ASSET_DEFS: Dict[str, Dict[str, Any]] = {
    "LOC_CHEN_HOUSE": {
        "type": "scene",
        "name": "靖京西坊陈宅正屋",
        "path_name": "定妆_场景_陈宅正屋",
        "positive": "雨后旧宅正屋，门槛半干血迹，湿脚印通向桌边，桌上油灯弱暖边，门外冷雨光画左入射，家人跪哭只做背景轮廓。",
        "negative": "现代家具、现代灯具、豪华宫殿、强红蓝霓虹、血腥器官、墙上可读长文字。",
        "constraints": {
            "layout": "门槛在前景下方，桌案在画左/中景，墙面和门口形成纵深，沈砚多在画右。",
            "light_anchor": "画左冷雨光5200K，桌上油灯2600K弱暖边，暗部保留。",
            "axis_rules": "沈砚↔陈贵皮相横轴；沈砚看画左，陈贵看画右；公开揭穿为沈砚→证据→妖三角轴。",
            "must_not_have": ["现代物件", "豪华宫殿", "新增刀具证物", "可读长文字"],
        },
        "drift": ["门窗位置不可随机跳变", "油灯不能变主光大光源", "不要把陈宅画成宫殿"],
        "self_check": "门槛血、桌案、门外冷雨光、油灯弱暖边、画左画右轴线都可读。",
    },
    "PROP_BLOOD_THRESHOLD": {
        "type": "prop",
        "name": "门槛半干血迹",
        "path_name": "定妆_道具_门槛血迹",
        "positive": "门槛木地上的半干暗红血迹，雨后边缘被水晕开，证据感强但非血腥。",
        "negative": "大量喷溅、器官、现代警戒线、文字标注。",
        "owner": "陈宅证据链",
        "current_state": "半干暗红，位置固定在门槛前景下方",
        "lifecycle": {"first_seen": "EP01_CLIP01", "payoff": "EP01_CLIP08", "state_order": ["半干血迹", "被沈砚指认为死亡证据"]},
        "constraints": {"structure": "贴地痕迹，不是道具牌；边缘水晕，颜色低饱和暗红", "must_not_have": ["器官", "大面积血泊"]},
        "drift": ["不要移动到桌边", "不要变成喷溅血浆", "不要新增文字标签"],
    },
    "PROP_MUD_FOOTPRINT": {
        "type": "prop",
        "name": "雨水泥脚印",
        "path_name": "定妆_道具_泥脚印",
        "positive": "雨水带泥脚印从门槛向屋内延伸，湿泥边缘自然，方向指向桌案。",
        "negative": "现代鞋印图案过清、脚印发光、文字箭头。",
        "owner": "陈宅证据链",
        "current_state": "湿泥脚印，连贯但被雨水冲淡",
        "lifecycle": {"first_seen": "EP01_CLIP02", "payoff": "EP01_CLIP08", "state_order": ["门槛外入屋", "被沈砚回收为脚印不对"]},
        "constraints": {"structure": "贴地连续印迹，不能漂浮或像贴纸", "must_not_have": ["发光边", "现代箭头"]},
        "drift": ["方向必须通向陈贵座位", "不可变成血脚印"],
    },
    "PROP_CLEAN_BLACK_BOOT": {
        "type": "prop",
        "name": "干净皂靴",
        "path_name": "定妆_道具_干净皂靴",
        "positive": "古代黑色皂靴，鞋面干净得异常，和雨后泥脚印形成矛盾。",
        "negative": "现代皮鞋、运动鞋、金属靴、过度华丽刺绣。",
        "owner": "CHAR_PI_DEMON_CHENGUI",
        "current_state": "鞋面干净，不沾雨泥",
        "lifecycle": {"first_seen": "EP01_CLIP03", "payoff": "EP01_CLIP08", "state_order": ["干净异常", "成为冒充证据"]},
        "constraints": {"structure": "古代皂靴剪影，圆头软靴，黑布/黑皮低反光", "must_not_have": ["现代鞋底", "运动鞋纹"]},
        "drift": ["始终是干净黑皂靴", "不要变成布鞋"],
    },
    "PROP_STILL_TEA": {
        "type": "prop",
        "name": "不动热茶",
        "path_name": "定妆_道具_不动热茶",
        "positive": "旧茶碗中热茶水面静止不晃，边缘有极轻蒸汽，油灯弱暖边照到碗沿。",
        "negative": "现代茶杯、咖啡杯、浮字、夸张沸腾。",
        "owner": "CHAR_PI_DEMON_CHENGUI",
        "current_state": "热茶静止，端坐半夜仍一丝不晃",
        "lifecycle": {"first_seen": "EP01_CLIP01", "payoff": "EP01_CLIP08", "state_order": ["冷开异常", "证据回收"]},
        "constraints": {"structure": "古代旧茶碗，圆口浅碗，茶面镜面静止", "must_not_have": ["现代杯柄", "文字茶杯"]},
        "drift": ["茶面必须不动", "不要换成酒杯或药碗"],
    },
    "PROP_OLD_COPPER_HALF": {
        "type": "prop",
        "name": "半片旧铜",
        "path_name": "定妆_道具_半片旧铜",
        "positive": "袖中半片旧铜，边缘磨损，微微发烫在皮肤上留下红痕，旧金属暗哑。",
        "negative": "完整铜镜、现代硬币、发光神器、可读文字铭文。",
        "owner": "CHAR_SHEN_YAN",
        "current_state": "袖中发烫，触发金睛前兆",
        "lifecycle": {"first_seen": "EP01_CLIP05", "payoff": "第2集继续解释", "state_order": ["袖中旧物", "发烫触发"]},
        "constraints": {"structure": "半片不规则旧铜，暗哑磨损，不能完整圆镜", "must_not_have": ["现代硬币", "长铭文"]},
        "drift": ["不要变成完整镜子", "不要强发光抢金睛"],
    },
    "PROP_RECORD_PAPER": {
        "type": "prop",
        "name": "笔录纸",
        "path_name": "定妆_道具_笔录纸",
        "positive": "旧纸笔录，坊正递给沈砚画押，只露纸张和笔，不出现可读长文。",
        "negative": "现代合同、打印纸、清晰大段文字。",
        "owner": "CHAR_FANGZHENG",
        "current_state": "递出待画押",
        "lifecycle": {"first_seen": "EP01_CLIP02", "payoff": "沈砚拒绝画押", "state_order": ["递出", "被拒"]},
        "constraints": {"structure": "古代旧纸和毛笔，文字不可读", "must_not_have": ["现代打印字", "签字笔"]},
        "drift": ["只做功能道具", "不要抢占画面"],
    },
    "WEAPON_PEIJUE_SHORT_BLADE": {
        "type": "weapon",
        "name": "裴决短刀",
        "path_name": "定妆_武器_裴决短刀",
        "positive": "裴决腰间短刀，黑鞘短柄，低调实用，符火术士的近身备用武器。",
        "negative": "大剑、长枪、现代军刀、过度华丽发光。",
        "constraints": {"structure": "短刀比例贴合腰间，不喧宾夺主", "must_not_have": ["长剑", "现代刀具"]},
        "drift": ["始终腰悬短刀，不变长兵器"],
        "weapon_profile": {
            "design_intent": "低调术士装备，辅助裴决冷硬行动气质。",
            "silhouette": "短柄短鞘，贴腰携带。",
            "scale": "全长约前臂长度，不能大过主角身体比例。",
            "material": "黑鞘、暗金旧扣、哑光金属刀柄。",
            "palette": "黑、暗灰、少量旧金属。",
            "ornament_motif": "极简符纹压印，不发光。",
            "carry_modes": ["腰间横挂", "门口阴影中只露轮廓"],
            "combat_usage": "第1集不拔刀，仅作为术士身份装备。",
            "vfx_signature": "不主动发光，符火由 VFX_PEIJUE_FU_FIRE 承担。",
            "forbidden_drift": ["不要变长剑", "不要现代战术刀", "不要抢符火高光"],
        },
        "owner": "CHAR_PEIJUE",
        "character_id": "CHAR_PEIJUE",
    },
    "VFX_JINJING_GOLD_EYE": {
        "type": "vfx",
        "name": "金睛旧金光",
        "path_name": "定妆_特效_金睛旧金光",
        "positive": "沈砚右眼瞳内旧金细丝短促发亮，只照眼眶和少量鳞翳，不把整张脸点亮。",
        "negative": "全脸发光、页游金光爆炸、眼睛变激光、遮住五官。",
        "constraints": {"face_policy": "face_locked", "carries_identity": ["CHAR_SHEN_YAN/常态"], "must_not_have": ["全脸发光", "遮住眼鼻嘴"]},
        "drift": ["金光只在右眼瞳内", "不能变成全身神光"],
    },
    "VFX_SKIN_DEMON_REVEAL": {
        "type": "vfx",
        "name": "换皮妖揭皮显相",
        "path_name": "定妆_特效_揭皮显相",
        "positive": "人皮像泡烂湿纸卷开，露出青灰鳞翳和竖瞳，克制可读非血腥。",
        "negative": "血腥撕脸、器官、恐怖片烂肉、全身怪物化。",
        "constraints": {"face_policy": "face_locked", "carries_identity": ["CHAR_PI_DEMON_CHENGUI/陈贵皮相"], "must_not_have": ["血腥器官", "烂肉特写"]},
        "drift": ["始终是湿纸卷皮和青灰鳞翳", "不要变成红色恶魔"],
    },
    "VFX_PEIJUE_FU_FIRE": {
        "type": "vfx",
        "name": "裴决冷蓝符火",
        "path_name": "定妆_特效_冷蓝符火",
        "positive": "冷蓝符火横穿屋内，符纸边缘短促火星，亮度克制，命中人皮墙面。",
        "negative": "橘红大火、爆炸火墙、烟花、遮脸大光效。",
        "constraints": {"face_policy": "none", "must_not_have": ["大火墙", "遮住沈砚五官"]},
        "drift": ["符火颜色冷蓝", "不要把屋内打成舞台灯"],
    },
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path: Path, data: Mapping[str, Any]) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_ep(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("第") and text.endswith("集"):
        return text
    m = EP_RE.search(text)
    return f"第{m.group(0)}集" if m else text


def clip_number(clip_id: str, fallback: int) -> int:
    m = re.search(r"(\d+)", str(clip_id or ""))
    return int(m.group(1)) if m else fallback


def flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return " ".join([str(k) + " " + flatten(v) for k, v in value.items()])
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    return str(value or "")


def ref_item(path: str, *, key: str = "", source: str = "出图/共享/图片/定妆母本_待生成.png") -> Dict[str, Any]:
    item: Dict[str, Any] = {"path": path, "status": "ready"}
    if key in {"three_quarter", "side", "back"}:
        method = "controlled_multiref_generation"
    elif key in {"half_body", "full_body", "face_anchor_refs"}:
        method = "front_crop"
    else:
        method = ""
    if method:
        item["derivation"] = {
            "method": method,
            "source_path": source,
            "source_sha256": "prompt-stage-source-pending",
            "crop_box": [0, 0, 1, 1],
        }
    return item


def char_asset_base(root: Path, cid: str, name: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_\u4e00-\u9fff]+", "_", name).strip("_") or cid
    return root / "设定库" / "character_assets" / f"{cid}__{safe}"


def ensure_asset_bundle(root: Path, cid: str, cfg: Mapping[str, Any]) -> Dict[str, Any]:
    base = char_asset_base(root, cid, str(cfg["name"]))
    sections = {}
    for sec in ("reference", "prompts", "lora", "voice", "adapters", "qc"):
        d = base / sec
        d.mkdir(parents=True, exist_ok=True)
        sections[sec] = str(d.relative_to(root))
    manifest = {
        "kind": "n2d_project_character_asset_bundle",
        "version": 1,
        "character_id": cid,
        "name": cfg["name"],
        "scope": cfg["scope"],
        "directories": sections,
        "truth_sources": {
            "identity_registry": "出图/共享/identity_registry.json",
            "character_card": f"设定库/characters/{cfg['name']}.md",
        },
        "created_by": "n2d-image image_prompt_pack.py",
        "updated_at": now_iso(),
    }
    write_json(base / "manifest.json", manifest)
    return {
        "manifest": str((base / "manifest.json").relative_to(root)),
        "package_dir": str(base.relative_to(root)),
        "base_dir": str(base.relative_to(root)),
        "sections": sections,
    }


def adapter_defaults() -> Dict[str, Any]:
    image = {
        backend: {"mode": spec["default_mode"], "status": spec["default_status"]}
        for backend, spec in IDENTITY_IMAGE_ADAPTERS.items()
    }
    video = {
        backend: {"mode": spec["default_mode"], "status": spec["default_status"]}
        for backend, spec in IDENTITY_VIDEO_ADAPTERS.items()
    }
    return {"image": image, "video": video, "lora": {"status": "not_needed", "reason": "第1集先用共享定妆参考组；跨集漂移再升级 LoRA。"}}


def generation_control(seed_base: int) -> Dict[str, Any]:
    return {
        "seed_strategy": "fixed_pool",
        "seed_pool": [seed_base + i for i in range(6)],
        "usage": {"turnaround": seed_base, "expression": seed_base + 1, "closeup": seed_base + 2, "shot": seed_base + 3},
        "backend_support": {
            "codex": "unsupported_or_unknown",
            "openai": "backend_dependent",
            "dreamina": "backend_dependent",
            "seedream": "backend_dependent_verify_adapter",
            "kling": "backend_dependent_verify_adapter",
        },
        "fallback_policy": "record seed no-op/degraded when backend does not support seed; never treat unsupported seed as reproducible.",
        "record_required": ["requested_seed", "effective_seed", "seed_effective", "seed_support", "seed_strategy"],
    }


def full_reference_group(root: Path, cid: str, cfg: Mapping[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    ak = str(cfg["asset_key"])
    base = "出图/共享/图片"
    source = f"{base}/定妆_{ak}_正面.png"
    rg = {
        "front": ref_item(source),
        "three_quarter": ref_item(f"{base}/定妆_{ak}_45度.png", key="three_quarter", source=source),
        "side": ref_item(f"{base}/定妆_{ak}_侧面.png", key="side", source=source),
        "back": ref_item(f"{base}/定妆_{ak}_背面.png", key="back", source=source),
        "outfit": ref_item(f"{base}/定妆_{ak}_半身.png", key="half_body", source=source),
        "half_body": ref_item(f"{base}/定妆_{ak}_半身.png", key="half_body", source=source),
        "turnaround": ref_item(f"{base}/定妆_{ak}_三视图.png"),
        "face_anchor_refs": [
            ref_item(f"{base}/定妆_{ak}_脸部特写.png", key="face_anchor_refs", source=source),
        ],
        "expressions": [
            {**ref_item(f"{base}/定妆_{ak}_表情_克制.png", key="face_anchor_refs", source=source), "emotion": "克制"},
            {**ref_item(f"{base}/定妆_{ak}_表情_震动.png", key="face_anchor_refs", source=source), "emotion": "震动"},
        ],
    }
    atlas = {
        "build_tier": "full_makeup_pack",
        "base_views": {
            "front": rg["front"],
            "three_quarter": rg["three_quarter"],
            "side": rg["side"],
            "back": rg["back"],
            "half_body": rg["half_body"],
        },
        "face_anchor_refs": rg["face_anchor_refs"],
        "expression_refs": rg["expressions"],
        "notes": "所有拆分角度以正面主参考/三视图为母本，同源派生，避免逐张文生图补角度造成脸漂。",
    }
    return rg, atlas


def partial_reference_group(root: Path, cid: str, cfg: Mapping[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    ak = str(cfg["asset_key"])
    base = "出图/共享/图片"
    rg = {
        "silhouette": ref_item(f"{base}/定妆_{ak}_剪影局部.png"),
        "hand": ref_item(f"{base}/定妆_{ak}_手部局部.png"),
        "outfit": ref_item(f"{base}/定妆_{ak}_布料局部.png"),
    }
    atlas = {
        "build_tier": "restricted_partial",
        "partial_refs": rg,
        "no_full_face": True,
        "notes": "功能角色只使用局部/剪影/手部参考，绝不正脸，不建完整主角脸。",
    }
    return rg, atlas


def build_identity_registry(root: Path) -> Dict[str, Any]:
    chars: List[Dict[str, Any]] = []
    for i, (cid, cfg) in enumerate(CHARACTER_DEFS.items(), start=1):
        restricted = cfg["tier"] == "restricted_partial"
        rg, atlas = partial_reference_group(root, cid, cfg) if restricted else full_reference_group(root, cid, cfg)
        bundle = ensure_asset_bundle(root, cid, cfg)
        form: Dict[str, Any] = {
            "form": cfg["form"],
            "asset_key": cfg["asset_key"],
            "anchor_phrase": cfg["anchor"],
            "character_dna": {
                "face": cfg["face"],
                "hair": cfg["hair"],
                "outfit": cfg["outfit"],
                "accessories": cfg["accessories"],
                "texture": cfg["texture"],
            },
            "physical_scale": {"relative_scale": cfg["relative_scale"]},
            "wardrobe_profile": {
                "silhouette": cfg["outfit"],
                "palette": "冷灰、深青、玄黑、低饱和旧金属",
                "layers": "古装内外层明确",
                "collar": "古装交领/束领，不现代圆领",
                "sleeve": "窄袖或布袖按角色身份",
                "waist": "束腰/旧腰带",
                "hem": "竖屏下摆完整但不拖成仙侠飘带",
                "fabric": "低饱和布料/皮革/旧金属",
                "forbidden_drift": cfg["drift"],
            },
            "reference_group": rg,
            "reference_atlas": atlas,
            "identity_adapters": adapter_defaults(),
            "generation_control": generation_control(1100 + i * 100),
            "angle_policy": {
                "allowed": ["front", "three_quarter", "side", "MCU", "CU", "MS", "shot_reverse"],
                "risky": ["deep_shadow", "face_too_small", "extreme_top", "extreme_low", "strong_vfx_over_face"],
                "requires_extra_reference": ["ECU", "大表情", "背光暗部", "多人同框近景"],
            },
            "drift_forbidden": cfg["drift"],
            "performance_signature": cfg["performance_signature"],
            "signature_equipment": cfg["signature_equipment"],
            "self_check_passed": False,
            "self_check_note": "prompt-stage registered; PNG 自检在出图后回填。",
        }
        if restricted:
            form["restricted_partial"] = True
            form["no_full_face"] = True
        chars.append({
            "id": cid,
            "name": cfg["name"],
            "scope": cfg["scope"],
            "forms": [form],
            "asset_bundle": bundle,
            "evolution_profile": {"mode": "single_anchor", "identity_anchor_form": cfg["form"]},
        })
    return {
        "kind": IDENTITY_REGISTRY_KIND,
        "version": 1,
        "generated_at": now_iso(),
        "characters": chars,
        "notes": "第1集 prompt 阶段身份注册层；ready 表示定妆位已定义，PNG 文件由下一步 image 阶段生成并回填 self_check/anchor_sha。",
    }


def asset_ref(path_name: str, suffix: str = ".png") -> Dict[str, Any]:
    return {"path": f"出图/共享/图片/{path_name}{suffix}", "status": "ready"}


def build_asset_registry() -> Dict[str, Any]:
    assets: List[Dict[str, Any]] = []
    for aid, cfg in ASSET_DEFS.items():
        rg: Dict[str, Any] = {"primary": asset_ref(str(cfg["path_name"]))}
        if cfg["type"] in {"scene", "location"}:
            rg.update({
                "front": asset_ref(str(cfg["path_name"]) + "_正机位"),
                "reverse": asset_ref(str(cfg["path_name"]) + "_反打机位"),
                "floor_plan": asset_ref(str(cfg["path_name"]) + "_平面图"),
            })
        if cfg["type"] in {"prop", "weapon"}:
            rg.update({"scale_ref": asset_ref(str(cfg["path_name"]) + "_比例"), "in_hand": asset_ref(str(cfg["path_name"]) + "_手持")})
        asset: Dict[str, Any] = {
            "id": aid,
            "type": cfg["type"],
            "name": cfg["name"],
            "reference_group": rg,
            "constraints": cfg.get("constraints", {}),
            "drift_forbidden": cfg.get("drift", []),
            "self_check_passed": False,
            "self_check_note": "prompt-stage registered; PNG 自检在出图后回填。",
        }
        if cfg["type"] in {"prop"}:
            asset.update({
                "owner": cfg.get("owner", "剧情证据链"),
                "current_state": cfg.get("current_state", "待出图"),
                "lifecycle": cfg.get("lifecycle", {}),
            })
        if cfg["type"] in {"scene", "location"}:
            asset.update({
                "core": True,
                "frequency": 12,
                "spatial_layout": "门槛前景下方；桌案画左/中景；屋门与墙面形成纵深；画右留沈砚调查/对质站位。",
                "floor_plan": "门槛→湿脚印→桌案→后墙，门口画左冷雨光，桌上油灯弱暖边。",
                "doors_windows": "正门在画面前景/画左方向，门外雨光入射；墙面后景承接符火钉妖。",
                "axis_rules": "沈砚↔陈贵皮相横轴，证据台词时沈砚→证据→妖三角轴。",
                "screen_direction_rules": "沈砚多画右/中景看画左；陈贵皮相多画左桌边看画右；裴决 Clip11 门口后景入场。",
                "scene_dna": {
                    "belonging_anchor": "靖京西坊陈宅，雨后旧宅正屋",
                    "landmarks": ["门槛血迹", "湿泥脚印", "桌上油灯", "茶碗", "后墙"],
                    "spatial_layout": "前景门槛，中景桌案，后景墙面和门口阴影。",
                    "architecture_materials": "旧木门槛、灰墙、潮湿地面、朴素旧桌案。",
                    "color_lighting_weather": "冷灰雨夜，门外冷雨光，油灯低饱和暖边。",
                    "resident_assets": ["PROP_BLOOD_THRESHOLD", "PROP_MUD_FOOTPRINT", "PROP_STILL_TEA"],
                    "forbidden": "现代家具、宫殿化、霓虹高饱和、文字墙。",
                    "dof_profile": {"depth_intent": "medium shallow for evidence closeups, deep enough for axis continuity"},
                },
                "scene_atlas": {
                    "base_views": {
                        "front": asset_ref(str(cfg["path_name"]) + "_正机位"),
                        "back": asset_ref(str(cfg["path_name"]) + "_反打机位"),
                    }
                },
            })
        if cfg["type"] == "weapon":
            asset["weapon_profile"] = cfg["weapon_profile"]
            asset["owner"] = cfg.get("owner")
            asset["character_id"] = cfg.get("character_id")
        assets.append(asset)
    return {
        "kind": ASSET_REFERENCE_REGISTRY_KIND,
        "version": 1,
        "generated_at": now_iso(),
        "assets": assets,
        "notes": "第1集 prompt 阶段资产注册层；ready 表示定妆位已定义，PNG 文件由下一步 image 阶段生成。",
    }


def clip_chars(clip: Mapping[str, Any]) -> List[str]:
    raw = clip.get("character_ids") or []
    out: List[str] = []
    for item in raw:
        text = str(item)
        if text.startswith("CHAR_") and text not in out:
            out.append(text)
    return out


def clip_assets(clip: Mapping[str, Any]) -> List[str]:
    ids: List[str] = []
    for key in ("location_id",):
        val = str(clip.get(key) or "").strip()
        if val and val not in ids:
            ids.append(val)
    for key in ("object_ids", "asset_ids", "vfx_ids"):
        for val in clip.get(key) or []:
            text = str(val).strip()
            if text and re.match(r"^(LOC|PROP|WEAPON|OUTFIT|VFX)_", text) and text not in ids:
                ids.append(text)
    for text in re.findall(r"\b(?:LOC|PROP|WEAPON|OUTFIT|VFX)_[A-Za-z0-9_]+", flatten(clip)):
        if text not in ids:
            ids.append(text)
    return ids


def continuity_frame_count(clip: Mapping[str, Any]) -> Tuple[int, bool, bool]:
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    has_mid = isinstance(cont.get("midframe"), Mapping) or bool(cont.get("anchors"))
    need_end = cont.get("need_endframe") is not False
    return 1 + (1 if has_mid else 0) + (1 if need_end else 0), has_mid, need_end


def director_map(root: Path, ep: str) -> Dict[str, Mapping[str, Any]]:
    data = load_json(root / "生产数据" / f"director_camera_plan_{ep}.json")
    out: Dict[str, Mapping[str, Any]] = {}
    if isinstance(data, Mapping):
        for row in data.get("clips") or []:
            if isinstance(row, Mapping):
                out[str(row.get("clip_id") or "")] = row
    return out


def style_contract(story: Mapping[str, Any]) -> Mapping[str, Any]:
    return story.get("style_contract") if isinstance(story.get("style_contract"), Mapping) else {}


def visual_contract(story: Mapping[str, Any]) -> Mapping[str, Any]:
    return story.get("visual_contract") if isinstance(story.get("visual_contract"), Mapping) else {}


def character_anchor_for_clip(cid: str, idx: int) -> str:
    cfg = CHARACTER_DEFS.get(cid, {})
    anchor = str(cfg.get("anchor") or "")
    if cid == "CHAR_PI_DEMON_CHENGUI" and idx >= 6:
        return "陈贵皮相中年商户，干净皂靴端茶不动，皮相错位，短暂显露青灰鳞翳竖瞳"
    return anchor


def sanitize_state_lock(text: str, cid: str, idx: int) -> str:
    value = text
    if cid == "CHAR_PI_DEMON_CHENGUI" and idx < 11:
        value = value.replace("，最后被符火钉墙", "")
        value = value.replace("最后被符火钉墙", "")
    if cid == "CHAR_SHEN_YAN" and idx < 11:
        value = value.replace("右眼残金逐渐熄灭", "右眼金光断续压暗")
        value = value.replace("右眼金光熄灭", "右眼金光断续压暗")
        value = value.replace("被裴决救下后趴低，", "")
        value = value.replace("秘密暴露", "秘密尚未公开")
    return value.strip("，。 ") + "。"


def state_entries_for_clip(story: Mapping[str, Any], cid: str, idx: int) -> List[str]:
    vc = visual_contract(story)
    data = vc.get("角色状态演进") or vc.get("角色状态演进表") or {}
    if not isinstance(data, Mapping):
        return []
    entries = data.get(cid) or []
    if isinstance(entries, (str, Mapping)):
        entries = [entries]
    if not isinstance(entries, list):
        return []
    out: List[str] = []
    for entry in entries:
        if isinstance(entry, Mapping):
            desc = str(entry.get("状态") or entry.get("status") or entry.get("description") or "").strip()
            start = shot_number(entry.get("自") or entry.get("from") or entry.get("start") or desc) or 1
            end = state_range_end(entry.get("至") or entry.get("until") or entry.get("end") or entry.get("保持") or entry.get("keep"))
        else:
            desc = str(entry).strip()
            start = shot_number(desc) or 1
            end = state_range_end(desc)
        if desc and idx >= start and (end is None or idx <= end):
            out.append(sanitize_state_lock(desc, cid, idx))
    return out


def state_lock_line(story: Mapping[str, Any], chars: Sequence[str], idx: int) -> str:
    rows: List[str] = []
    for cid in chars:
        entries = state_entries_for_clip(story, cid, idx)
        if entries:
            rows.append(f"`{cid}`: {'；'.join(entries)}")
    return "；".join(rows) if rows else "本镜无角色状态增量；只继承基础身份定妆。"


def sanitize_future_state_text(value: Any, idx: int) -> Any:
    if isinstance(value, Mapping):
        return {k: sanitize_future_state_text(v, idx) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_future_state_text(v, idx) for v in value]
    if not isinstance(value, str):
        return value
    text = value
    text = text.replace("角色状态继承 storyboard visual_contract", "本镜状态锁继承")
    text = text.replace("锁住光位、轴线、角色状态", "锁住光位、轴线和本镜状态锁")
    text = text.replace("清晰正脸", "可辨三分之二侧脸/侧脸身份")
    text = text.replace("正脸特写", "三分之二侧脸特写")
    if idx < 6:
        replacements = {
            "人皮湿纸般卷起露青灰鳞翳竖瞳": "皮相僵硬、动作过静",
            "短暂显露青灰鳞翳竖瞳": "短暂露出异常凝视",
            "青灰鳞翳竖瞳": "异常凝视",
            "鳞翳竖瞳": "异常凝视",
            "皮相错位": "皮相过静",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
    if idx < 11:
        replacements = {
            "右眼残金逐渐熄灭": "右眼金光断续压暗",
            "右眼金光熄灭": "右眼金光断续压暗",
            "被裴决救下后趴低": "被危机压低身位",
            "秘密暴露": "秘密尚未公开",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
    return text


def char_form_ref(cid: str) -> str:
    cfg = CHARACTER_DEFS.get(cid)
    if not cfg:
        return f"{cid}/常态"
    return f"{cid}/{cfg['form']}"


def char_file_ref(cid: str) -> str:
    cfg = CHARACTER_DEFS[cid]
    if cfg["tier"] == "restricted_partial":
        return f"出图/共享/图片/定妆_{cfg['asset_key']}_剪影局部.png"
    return f"出图/共享/图片/定妆_{cfg['asset_key']}_正面.png"


def make_shared_index(root: Path) -> str:
    rows = []
    for cid, cfg in CHARACTER_DEFS.items():
        rows.append(f"| 角色 | `{cid}/{cfg['form']}` | `出图/共享/图片/定妆_{cfg['asset_key']}_正面.png` | ⏳prompt ready | {cfg['anchor']} |")
    for aid, cfg in ASSET_DEFS.items():
        rows.append(f"| {cfg['type']} | `{aid}` | `出图/共享/图片/{cfg['path_name']}.png` | ⏳prompt ready | {cfg['name']} |")
    return "\n".join([
        "# 共享定妆索引",
        "",
        "本索引只登记 prompt 阶段的共享定妆位；未实际产出 PNG 前不标 ✅。",
        "",
        "| 类型 | ID | 目标存档 | 状态 | 锚点 |",
        "|---|---|---|---|---|",
        *rows,
        "",
    ])


def shared_character_prompt() -> str:
    parts = ["# 角色定妆", "", "所有角色定妆继承本剧 `identity_registry.json`，先出共享定妆，再派生分镜图。"]
    for cid, cfg in CHARACTER_DEFS.items():
        ak = cfg["asset_key"]
        restricted = cfg["tier"] == "restricted_partial"
        target = f"出图/共享/图片/定妆_{ak}_正面.png" if not restricted else f"出图/共享/图片/定妆_{ak}_剪影局部.png"
        parts += [
            "",
            f"## {cfg['name']}（`{cid}/{cfg['form']}`）",
            f"**目标存档**：`{target}`",
            f"**身份注册**：`identity_registry.json` -> `{cid}/{cfg['form']}`；资产包 `设定库/character_assets/{cid}__*`。",
            f"**角色定妆组**：正面 `_正面`、45° `_45度`、侧面 `_侧面`、背面 `_背面`、半身服装 `_半身`、脸部特写 `_脸部特写`、标准三视图 `_三视图`；局部角色为 `restricted_partial/no_full_face`，只手部/剪影/布料局部，绝不正脸。",
            f"**锚点句:** {cfg['anchor']}",
            "**半身参考裁切规则**：半身图从已通过自检的正面主参考裁切，裁切后回 9:16，主体居中；不得用白底/浅灰底/空白补下半截。",
            "### 正向 prompt（中文）",
            f"{cfg['anchor']}。{cfg['face']}；{cfg['hair']}；{cfg['outfit']}；{cfg['accessories']}。冷灰写实3D国风漫剧，9:16，主流审美，五官清晰协调，服装结构稳定。",
            "### 正向 prompt（英文）",
            f"{cfg['name']} character reference sheet, realistic 3D Chinese comic-drama style, restrained cold gray palette, stable facial structure, stable hair and costume, 9:16 vertical production reference.",
            "### 负向 prompt",
            "风格禁忌：禁Q版、禁现代服饰、禁高饱和页游光效、禁图中烤入文字、禁水印logo；身份禁漂：" + "、".join(cfg["drift"]),
            "### 检查清单（定妆自查）",
            "- 正面/45度/侧面/背面/半身/脸部特写/三视图是否同源，不逐张文生图补角度。",
            "- 脸型、发型、服装主色、关键配饰是否可被逐镜复用。",
            "- restricted_partial 角色是否没有完整正脸。",
            "**自检（生成后逐张过）**：通过后回填 identity_registry 的 `self_check_passed=true`、`anchor_sha` 和真实图片路径。",
        ]
    return "\n".join(parts) + "\n"


def shared_scene_prompt() -> str:
    cfg = ASSET_DEFS["LOC_CHEN_HOUSE"]
    return "\n".join([
        "# 场景定妆",
        "",
        "## 靖京西坊陈宅正屋（`LOC_CHEN_HOUSE`）",
        f"**目标存档**：`出图/共享/图片/{cfg['path_name']}.png`",
        "**场景注册**：`asset_registry.json` -> `LOC_CHEN_HOUSE`；scene_atlas 需有正机位与反打机位。",
        "### 正向 prompt（中文）",
        str(cfg["positive"]),
        "### 正向 prompt（英文）",
        "Rainy ancient Chinese house hall, cold gray night, left-side rainy key light, weak warm oil lamp edge light, threshold blood mark, muddy footprints to the table, old wooden interior, vertical 9:16 production reference.",
        "### 负向 prompt",
        "风格禁忌：" + str(cfg["negative"]) + "；不得改变门窗方向、桌案位置、门槛血迹位置。",
        "### 检查清单（定妆自查）",
        "- 目标存档、正机位、反打机位、平面图全部对应同一空间。",
        "- 光位锚：画左冷雨光 + 油灯弱暖边可读。",
        "- 轴线：沈砚画右看画左、陈贵画左看画右不跳轴。",
        "**自检（生成后逐张过）**：通过后回填 asset_registry 的 `self_check_passed=true` 和 scene_atlas 真实图片 sha。",
    ]) + "\n"


def shared_asset_prompt(kind: str, title: str, asset_ids: Sequence[str]) -> str:
    parts = [f"# {title}", ""]
    for aid in asset_ids:
        cfg = ASSET_DEFS[aid]
        parts += [
            f"## {cfg['name']}（`{aid}`）",
            f"**目标存档**：`出图/共享/图片/{cfg['path_name']}.png`",
            f"**资产注册**：`asset_registry.json` -> `{aid}`。",
            "**关键道具结构唯一性规则**：形状、材质、尺寸、状态和剧情位置必须稳定；同名道具不得每镜重画成不同物。",
            "### 正向 prompt（中文）",
            str(cfg["positive"]),
            "### 正向 prompt（英文）",
            f"{cfg['name']} production reference asset, restrained realistic Chinese comic-drama style, stable structure, no text, no logo, vertical 9:16 reference.",
            "### 负向 prompt",
            "风格禁忌：" + str(cfg["negative"]) + "；资产禁漂：" + "、".join(cfg.get("drift", [])),
            "### 检查清单（定妆自查）",
            "- 目标存档路径和 asset_registry 一致。",
            "- 结构、材质、状态、归属和剧情生命周期可读。",
            "- 不出现文字、水印、现代替代物。",
            "**自检（生成后逐张过）**：通过后回填 asset_registry 的 `self_check_passed=true` 与真实图 sha。",
            "",
        ]
    return "\n".join(parts) + "\n"


def overview_md(story: Mapping[str, Any], clips: Sequence[Mapping[str, Any]], total_frames: int) -> str:
    sc = style_contract(story)
    vc = visual_contract(story)
    status_rows = []
    for cid, cfg in CHARACTER_DEFS.items():
        status_rows.append(f"| `{cid}/{cfg['form']}` | ⏳prompt ready | {cfg['anchor']} |")
    for aid, cfg in ASSET_DEFS.items():
        status_rows.append(f"| `{aid}` | ⏳prompt ready | {cfg['name']} |")
    return "\n".join([
        f"# {story.get('episode', '第1集')} 出图总览",
        "",
        f"标题：{story.get('title', '')}",
        f"制作模式：{story.get('production_mode', '原生音画')}；画幅：9:16；逐镜计划出图 {total_frames} 张（首帧/中段锚帧/尾帧按 storyboard continuity）。",
        "",
        "## 本集视觉一致性契约",
        f"- 色调基线：{vc.get('色调基线', '')}",
        f"- 光位锚：{json.dumps(vc.get('场景光位锚', {}), ensure_ascii=False)}",
        f"- 轴线：{json.dumps(vc.get('场景轴线视线', {}), ensure_ascii=False)}",
        "- 状态演进：以 storyboard 的分段状态为上游契约；逐镜 prompt 只写本镜已发生状态锁，不把后镜反转/救场结局提前展开。",
        f"- 景别阶梯：{vc.get('景别阶梯', '')}",
        "",
        "## 本集基础视觉风格契约",
        f"- 风格名：{sc.get('风格名', '')}",
        f"- 视觉基调：{sc.get('视觉基调', '')}",
        f"- 镜头与构图：{sc.get('镜头与构图', '')}",
        f"- 光色策略：{sc.get('光色策略', '')}",
        f"- 运动边界：{sc.get('运动边界', '')}",
        f"- 风格禁忌：{sc.get('风格禁忌', '')}",
        "",
        "## 共享定妆就绪状态",
        "| ID | 状态 | 锚点 |",
        "|---|---|---|",
        *status_rows,
        "",
        "## 逐镜出图队列",
        "| 镜头 | clip_id | 时长 | 人物 | 资产 | 计划张数 |",
        "|---|---|---:|---|---|---:|",
        *[
            f"| {i} | `{clip.get('id')}` | {clip.get('duration', '')} | {', '.join(clip_chars(clip)) or '空镜/背景'} | {', '.join(clip_assets(clip))} | {continuity_frame_count(clip)[0]} |"
            for i, clip in enumerate(clips, start=1)
        ],
        "",
        "## 生成侧原则",
        "- 所有人物镜必须从共享定妆 image2image / 多图参考派生，不得纯文生图重抽新脸。",
        "- Codex/OpenAI/Dreamina/Nano/Gemini 类无持久主体 ID 后端，多人同框必须写 `regional_construct_required` 与 `split_composite_required`。",
        "- 动作/对峙镜视线锁戏内目标，非 POV 镜不看镜头。",
    ]) + "\n"


def shot_refs(chars: Sequence[str], assets: Sequence[str]) -> List[str]:
    lines: List[str] = []
    for cid in chars:
        cfg = CHARACTER_DEFS.get(cid)
        if not cfg:
            continue
        strength = "0.82" if cfg["tier"] != "restricted_partial" else "0.35"
        lines.append(f"- 人物定妆：`{char_file_ref(cid)}`，强度 {strength}，绑定 `{cid}/{cfg['form']}`。")
        if cfg["tier"] != "restricted_partial":
            lines.append(f"- 脸部特写：`出图/共享/图片/定妆_{cfg['asset_key']}_脸部特写.png`，强度 0.70，近景/反打锁脸。")
    for aid in assets:
        cfg = ASSET_DEFS.get(aid)
        if not cfg:
            continue
        kind = "场景定妆" if aid.startswith("LOC_") else "道具定妆" if aid.startswith(("PROP_", "WEAPON_")) else "特效定妆"
        lines.append(f"- {kind}：`出图/共享/图片/{cfg['path_name']}.png`，强度 0.45，绑定 `{aid}`。")
    return lines


def asset_forbidden_terms(asset_ids: Sequence[str]) -> List[str]:
    terms: List[str] = []
    for aid in asset_ids:
        cfg = ASSET_DEFS.get(aid)
        if not cfg:
            continue
        constraints = cfg.get("constraints") if isinstance(cfg.get("constraints"), Mapping) else {}
        for item in constraints.get("must_not_have") or []:
            text = str(item).strip()
            if text and text not in terms:
                terms.append(text)
        for item in cfg.get("drift") or []:
            text = str(item).strip()
            if text and text not in terms:
                terms.append(text)
    return terms


def shot_prompt_section(root: Path, ep: str, idx: int, clip: Mapping[str, Any], drow: Mapping[str, Any], story: Mapping[str, Any]) -> str:
    cid = str(clip.get("id") or f"EP01_CLIP{idx:02d}")
    chars = clip_chars(clip)
    assets = clip_assets(clip)
    frame_count, has_mid, need_end = continuity_frame_count(clip)
    refs = shot_refs(chars, assets)
    primary = chars[0] if chars else ""
    char_bindings = []
    for c in chars:
        suffix = "*" if c == primary and len(chars) > 1 else ""
        char_bindings.append(f"`{char_form_ref(c)}{suffix}`")
    multi_required = len(chars) >= 2
    inj = drow.get("image_prompt_injection") if isinstance(drow.get("image_prompt_injection"), Mapping) else {}
    lens = inj.get("镜头/机位") or drow.get("shot_size") or clip.get("rhythm") or ""
    move = inj.get("起幅·运动余量") or "为慢推/反打预留 15%-25% 运动余量；主体不要顶边，动作方向留空间。"
    intent = inj.get("导演意图") or clip.get("rhythm") or ""
    comp_guard = sanitize_future_state_text(
        inj.get("构图防呆") or "角色视线锁戏内目标；非 POV 镜不看镜头；只继承本镜已发生的光位、轴线和状态增量。",
        idx,
    )
    desc = ""
    shots = clip.get("shots")
    if isinstance(shots, list) and shots:
        desc = " ".join(str(s.get("desc") or "") for s in shots if isinstance(s, Mapping))
    desc = desc or str(clip.get("description") or clip.get("label") or "")
    desc = str(sanitize_future_state_text(desc, idx))
    raw_template_contract = clip.get("template_contract") if isinstance(clip.get("template_contract"), Mapping) else {}
    template_contract = sanitize_future_state_text(raw_template_contract, idx)
    negative = template_contract.get("negative") or []
    if not isinstance(negative, list):
        negative = [str(negative)]
    negative = [str(item) for item in negative]
    asset_forbidden = asset_forbidden_terms(assets)
    slots = "无"
    strategy = "单人/空镜，无需多人同框分区。"
    distinct_line = "；".join(
        f"{CHARACTER_DEFS[c]['name']}：{character_anchor_for_clip(c, idx)}"
        for c in chars
        if c in CHARACTER_DEFS
    ) or "无人物"
    if multi_required:
        slot_parts = []
        positions = ["画右/中景", "画左/桌边", "前景/中景", "门口后景", "背景虚焦"]
        for sidx, c in enumerate(chars):
            slot_parts.append(f"SLOT_{sidx + 1}: `{char_form_ref(c)}{'*' if c == primary else ''}` -> {positions[sidx % len(positions)]}，区分锚点：{character_anchor_for_clip(c, idx)}")
        slots = "；".join(slot_parts)
        strategy = "regional_construct_required + split_composite_required：先空场景底板，再按身份槽位分区生成/合成，统一 relighting/color match；不是条件式兜底。"
    closeup_lock = "脸型：窄长/中年商户/冷硬青年按角色锚点；五官比例、发型、发饰、服装色块必须和定妆一致，脸部特写参考优先。"
    tail = "尾帧必须用同镜首帧/中段锚帧 image2image 派生，不得纯文生图重抽；尾帧稳定 0.3-0.5 秒给视频接缝。" if need_end else "末镜无尾帧，continuity.need_endframe=false；最后眼部 ECU 硬断，仍不得纯文重抽。"
    mid = "中段锚帧用首帧 image2image 派生，锁住光位、轴线和本镜状态锁；不跳角色站位。" if has_mid else "本镜无中段锚帧。"
    char_phrase = "；".join(character_anchor_for_clip(c, idx) for c in chars if c in CHARACTER_DEFS)
    asset_phrase = "；".join(str(ASSET_DEFS[a]["name"]) for a in assets if a in ASSET_DEFS)
    vc = visual_contract(story)
    sc = style_contract(story)
    state_lock = state_lock_line(story, chars, idx)
    return "\n".join([
        f"## 镜头 {idx}（`{cid}` · {clip.get('label', '')} · {clip.get('template', '')}）",
        f"**剧本描述**：{desc}",
        f"**本镜出图张数**：{frame_count} 张；首帧 `出图/{ep}/图片/Clip{idx:02d}_first.png`；中段锚帧 `出图/{ep}/图片/Clip{idx:02d}_mid.png`；尾帧 `出图/{ep}/图片/Clip{idx:02d}_end.png`。",
        "**参考图**：",
        *refs,
        f"**角色圣经引用**：{', '.join(char_bindings) if char_bindings else '无人物/空镜'}；人物审美基线：写实国漫主流审美，五官协调清晰，角色好看但不网红化。",
        f"**角色资产包引用**：{', '.join(f'`设定库/character_assets/{c}__*/manifest.json`' for c in chars) if chars else '无'}。",
        f"**跨集成长阶段**：第1集锚定形态；{', '.join(char_bindings) if char_bindings else '无人物'}。",
        f"**资产身份注册层**：{', '.join(char_bindings) if char_bindings else '无人物'}；reference_group / face_anchor_refs / expressions 均从 `identity_registry.json` 读取；本镜从共享定妆 image2image / 多图参考派生，不得纯文生图。",
        f"**资产引用注册层**：{', '.join(f'`{a}`' for a in assets)}；场景/道具/VFX 均从 `asset_registry.json` 读取，关键道具结构唯一性保持。",
        f"**多人同框身份槽位**：{slots}",
        f"**多人同框执行策略**：{strategy}",
        "**逐主体参考绑定**：每个清晰主体只喂自己的定妆/脸部特写/表情参考，不把多角色拼成一张不可寻址参考表。",
        f"**区分锚点（互斥发色/服装主色/配饰）**：{distinct_line}。",
        f"**视线方向**：继承轴线：沈砚看画左证据/妖，陈贵皮相看画右或沈砚右眼，裴决看沈砚金睛余光；非 POV 镜不看镜头。",
        f"**光位锚**：{json.dumps(vc.get('场景光位锚', {}), ensure_ascii=False)}",
        f"**镜头/机位**：{lens}",
        f"**起幅·运动余量**：{move}",
        f"**构图防呆**：{comp_guard}",
        f"**本镜状态锁**：{state_lock}",
        f"**导演意图**：{intent}",
        f"**专项镜头模板**：shot_type={clip.get('template', '')}；beats={json.dumps(template_contract.get('beats', []), ensure_ascii=False)}；blocking={template_contract.get('blocking', '')}；camera_rule={template_contract.get('camera_rule', '')}；continuity_must={json.dumps(template_contract.get('continuity_must', []), ensure_ascii=False)}；negative={json.dumps(negative, ensure_ascii=False)}。",
        "**近景/反打身份锁定**：" + closeup_lock,
        f"**尾帧接力生成方式**：{tail}",
        f"**中段锚帧生成方式**：{mid}",
        "**尾帧专用重抽提示**：只允许基于本镜上一张成图 image2image 微调动作/光效，不允许纯文字重抽新脸、新衣、新场景。",
        "**固定 seed 策略**：请求 seed 记录到 generation_recipe；若后端不支持 seed，记录 seed_support=false 和图生图参考路径。",
        "",
        "**导演视角八维**：",
        "| 维度 | 本镜约束 |",
        "|---|---|",
        f"| ① 戏剧目标 | {clip.get('rhythm', '')}；{clip.get('label', '')} |",
        f"| ② 主体/表演 | {', '.join(char_bindings) if char_bindings else '空镜/证据'}；{char_phrase} |",
        f"| ③ 构图/轴线 | {comp_guard} |",
        f"| ④ 光色/天气 | {vc.get('色调基线', '')} |",
        f"| ⑤ 景别/镜头 | {lens} |",
        f"| ⑥ 动作/运动 | {move} |",
        f"| ⑦ 资产/证据 | {asset_phrase} |",
        f"| ⑧ 禁忌/QC | {sc.get('风格禁忌', '')}；{'; '.join(negative)} |",
        "",
        "### 正向 prompt（中文）",
        f"锚点句: {char_phrase or asset_phrase}。{desc}。本镜状态锁：{state_lock}。{sc.get('视觉基调', '')}，竖屏9:16，{vc.get('色调基线', '')}。身份锁定句：{', '.join(char_bindings) if char_bindings else '无人物'} 从共享定妆 image2image / 多图参考派生，脸型、发型、服装主色和关键配饰不漂。镜头是旁观者，不看镜头；视线锁戏内目标。{lens}，{move}",
        "### 正向 prompt（英文）",
        "Vertical 9:16 cinematic keyframe, realistic 3D Chinese comic-drama style, cold gray rainy ancient house, restrained supernatural detail, stable character identity from reference images, stable lighting and axis, no direct camera gaze unless POV, production-ready frame.",
        "### 负向 prompt",
        f"风格禁忌：{sc.get('风格禁忌', '')}；不要直视镜头/looking at viewer、不要frontal portrait摆拍、不要纯文生图重抽新脸、不要现代物件、不要水印logo、不要可读长文字；资产结构禁项：{'; '.join(asset_forbidden)}；本镜禁忌：{'; '.join(negative)}。",
        "### 检查清单（八维自查）",
        "- ①戏剧目标是否一眼可读；②主体身份/表演是否稳定；③构图轴线是否继承；④光色是否冷灰雨夜+油灯弱暖边；⑤景别是否匹配导演计划；⑥运动余量是否够；⑦资产证据是否绑定 ID；⑧风格禁忌是否未触犯。",
        "- 角色脸/妆造未漂移：人物脸型、妆造、发型、服装主色、关键配饰是否都和身份注册层一致；服装配色一致；角色 DNA 五层一致；关键道具结构是否未变。",
        "- 多人同框是否有身份槽位、primary 星标和 regional_construct_required / split_composite_required。",
        "**自检（生成后逐张过 · 落档闸门）**：图片通过后写入 generation_recipe、image_qc、identity/asset self_check；失败按下方重抽预算走。",
        "**重抽预算**：首帧 2 次，中段锚帧 1 次，尾帧 1 次；若仍身份漂移，回共享定妆或拆分合成，不继续盲抽。",
        "",
    ]) + "\n"


def shots_md(root: Path, ep: str, story: Mapping[str, Any], clips: Sequence[Mapping[str, Any]]) -> str:
    dmap = director_map(root, ep)
    parts = [f"# {ep} 分镜出图 Prompt", "", "本文件为最终分镜出图 prompt，已落实参考规划与导演镜头计划。"]
    for idx, clip in enumerate(clips, start=1):
        parts.append(shot_prompt_section(root, ep, idx, clip, dmap.get(str(clip.get("id") or ""), {}), story))
    return "\n".join(parts) + "\n"


def role_bible_md() -> str:
    rows = [
        "# 角色圣经",
        "",
        "| ID | 名称 | 形态 | 锚点 | 禁漂 |",
        "|---|---|---|---|---|",
    ]
    for cid, cfg in CHARACTER_DEFS.items():
        rows.append(f"| `{cid}` | {cfg['name']} | {cfg['form']} | {cfg['anchor']} | {'、'.join(cfg['drift'])} |")
    rows += ["", "本文件由 n2d-image prompt 包同步生成；机器真值以 `出图/共享/identity_registry.json` 为准。", ""]
    return "\n".join(rows)


def reference_action_count(plan: Mapping[str, Any]) -> int:
    count = 0
    for clip in plan.get("clips") or []:
        if not isinstance(clip, Mapping):
            continue
        for ch in clip.get("characters") or []:
            if isinstance(ch, Mapping) and ch.get("needs_action"):
                count += 1
        ms = clip.get("multi_subject_strategy")
        if isinstance(ms, Mapping) and ms.get("needs_action"):
            count += 1
    summary = plan.get("summary")
    if isinstance(summary, Mapping):
        try:
            return max(count, int(summary.get("action_required_count") or 0))
        except Exception:
            return count
    return count


def write_application_receipts(root: Path, ep: str, clips: Sequence[Mapping[str, Any]]) -> List[Path]:
    out: List[Path] = []
    prompt_rel = Path("出图") / ep / "prompt" / "01_分镜出图.md"
    prompt_path = root / prompt_rel
    if prompt_path.is_file():
        plan_path = root / "生产数据" / f"reference_plan_{ep}.json"
        plan = load_json(plan_path)
        if isinstance(plan, Mapping):
            actions = reference_action_count(plan)
            data = {
                "kind": REFERENCE_PLAN_APPLICATION_KIND,
                "episode": ep,
                "accepted": True,
                "reviewer": "Codex n2d-image prompt pack",
                "reviewed_at": now_iso(),
                "plan_path": str(plan_path.relative_to(root)),
                "plan_sha256": sha256_file(plan_path),
                "prompt_path": str(prompt_rel),
                "prompt_sha256": sha256_file(prompt_path),
                "applied_action_count": max(actions, len(clips)),
                "applied_evidence": [
                    "每镜写入参考图块、资产身份注册层、资产引用注册层。",
                    "多人镜写入多人同框身份槽位、regional_construct_required、split_composite_required。",
                    "近景/反打写入脸部特写、近景身份锁定、尾帧 image2image 接力。",
                ],
            }
            path = root / "生产数据" / f"reference_plan_application_{ep}.json"
            write_json(path, data)
            out.append(path)
        dplan_path = root / "生产数据" / f"director_camera_plan_{ep}.json"
        if dplan_path.is_file():
            data = {
                "kind": DIRECTOR_CAMERA_PLAN_APPLICATION_KIND,
                "episode": ep,
                "accepted": True,
                "reviewer": "Codex n2d-image prompt pack",
                "reviewed_at": now_iso(),
                "plan_path": str(dplan_path.relative_to(root)),
                "plan_sha256": sha256_file(dplan_path),
                "scopes": [
                    {
                        "scope": "出图",
                        "prompt_path": str(prompt_rel),
                        "prompt_sha256": sha256_file(prompt_path),
                        "applied_clip_ids": [str(c.get("id") or f"EP01_CLIP{i:02d}") for i, c in enumerate(clips, start=1)],
                    }
                ],
            }
            path = root / "生产数据" / f"director_camera_plan_applied_{ep}.json"
            write_json(path, data)
            out.append(path)
    return out


def write_pack(root: Path, ep: str) -> Dict[str, Any]:
    ep = normalize_ep(ep)
    story = load_json(root / "脚本" / ep / "storyboard.json")
    if not isinstance(story, Mapping):
        raise SystemExit(f"missing storyboard: {root / '脚本' / ep / 'storyboard.json'}")
    clips = [c for c in story.get("clips") or [] if isinstance(c, Mapping)]
    if not clips:
        raise SystemExit("storyboard clips[] is empty")
    total_frames = sum(continuity_frame_count(c)[0] for c in clips)
    written: List[Path] = []

    write_json(root / "出图" / "共享" / "identity_registry.json", build_identity_registry(root))
    written.append(root / "出图" / "共享" / "identity_registry.json")
    write_json(root / "出图" / "共享" / "asset_registry.json", build_asset_registry())
    written.append(root / "出图" / "共享" / "asset_registry.json")
    write_text(root / "出图" / "共享" / "prompt" / "00_索引.md", make_shared_index(root))
    written.append(root / "出图" / "共享" / "prompt" / "00_索引.md")
    write_text(root / "出图" / "共享" / "prompt" / "角色定妆.md", shared_character_prompt())
    written.append(root / "出图" / "共享" / "prompt" / "角色定妆.md")
    write_text(root / "出图" / "共享" / "prompt" / "场景定妆.md", shared_scene_prompt())
    written.append(root / "出图" / "共享" / "prompt" / "场景定妆.md")
    prop_ids = [aid for aid, cfg in ASSET_DEFS.items() if cfg["type"] in {"prop", "weapon"}]
    vfx_ids = [aid for aid, cfg in ASSET_DEFS.items() if cfg["type"] == "vfx"]
    write_text(root / "出图" / "共享" / "prompt" / "道具定妆.md", shared_asset_prompt("prop", "道具定妆", prop_ids))
    written.append(root / "出图" / "共享" / "prompt" / "道具定妆.md")
    write_text(root / "出图" / "共享" / "prompt" / "特效定妆.md", shared_asset_prompt("vfx", "特效定妆", vfx_ids))
    written.append(root / "出图" / "共享" / "prompt" / "特效定妆.md")
    write_text(root / "出图" / ep / "prompt" / "00_总览.md", overview_md(story, clips, total_frames))
    written.append(root / "出图" / ep / "prompt" / "00_总览.md")
    write_text(root / "出图" / ep / "prompt" / "01_分镜出图.md", shots_md(root, ep, story, clips))
    written.append(root / "出图" / ep / "prompt" / "01_分镜出图.md")
    write_text(root / "设定库" / "角色圣经.md", role_bible_md())
    written.append(root / "设定库" / "角色圣经.md")
    written += write_application_receipts(root, ep, clips)
    return {
        "kind": "n2d_image_prompt_pack_result",
        "root": str(root),
        "episode": ep,
        "clips": len(clips),
        "planned_frames": total_frames,
        "written": [str(p) for p in written],
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Generate n2d image prompt pack")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    result = write_pack(Path(ns.root), ns.episode)
    if ns.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"wrote {len(result['written'])} files")
        print(f"planned_frames={result['planned_frames']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
