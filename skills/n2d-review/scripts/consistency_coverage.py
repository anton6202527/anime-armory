#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一致性「现实覆盖」账本 —— 治「跑了数据却没真执行一致性」的结构性根因。

背景（2026-06-28 审计 + SOTA 对标 SonarQube/MLOps fail-closed）：n2d 最强的一致性检测都是
**现实验证器**（脸 insightface / 场景 DINOv2 / 在场+几何 OWLv2 / 声纹 speaker-embedding / VLM canonical）。
它们的共同弱点：**后端缺失时优雅降级成 advisory**——而真实出片机器上重型 conda 环境常常没装。结果：
「跑数据」时最强的检测器全是**休眠**态，审计只记一句「缺 sidecar / 无后端」就放行。这正是 MLOps 的
silent-failure：catch 缺依赖→降级→继续。SonarQube 的铁律——「闸门只有在**确认扫描器真跑过**且红就
阻断时才算 enforcement」。

本模块把这条铁律落到 n2d：声明每个现实验证器是否**适用**（项目登记了它要查的数据）+ 是否**真跑过且
对得上当前像素**（fresh）。脸/声纹/VLM 已各有休眠阻断（fidelity-gate / native voice / precision），
本模块补**场景验证器**（DINOv2 嵌入 / resident 在场 / 门窗几何）这块此前静默降级的覆盖，并出统一覆盖
报告。判定是纯函数（有 pytest）；交付边界阻断 + 逃生口同走既有 degraded_qc_active / note_degraded_qc_waiver
单一 chokepoint（不另起逃生口）。

「适用 × 休眠 → 交付前阻断（可 N2D_ALLOW_DEGRADED_QC 计债放行）」——让「跑了却没执行」在交付处现形。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Mapping, Optional, Sequence

# 现实验证器规格（脸/声纹 已有独立休眠阻断——precision umbrella / native voice——不在此重复阻断）。
# 2026-07-26 扩容：原只track三个场景验证器；实证（那妖魔ep1 by_dim）VAP/O3V/COST 在 insightface
# 在场时可无声休眠交付（umbrella 只看 pillow+insightface，对 torch/CLIP/OWLv2/VLM 全盲）——
# 服装换了、佩刀丢了、外观漂了全都零信号。补进覆盖账本：适用 × 休眠 → 交付前阻断。
SCENE_VERIFIERS = (
    {"key": "scene_embedding", "label": "场景语义嵌入(DINOv2)",
     "sidecar": "生产数据/scene_embed_{ep}.json", "producer": "scene_embed.py",
     "applies": "has_loc", "ran": "embed_filled"},
    {"key": "resident_presence", "label": "场景常驻陈设在场(OWLv2)",
     "sidecar": "生产数据/resident_presence_{ep}.json", "producer": "resident_presence.py",
     "applies": "has_resident_assets", "ran": "detector_ran"},
    {"key": "scene_geometry", "label": "门窗几何核对(OWLv2)",
     "sidecar": "生产数据/scene_geometry_{ep}.json", "producer": "scene_geometry_conformance.py",
     "applies": "has_doors_windows", "ran": "detector_ran"},
    # ── 2026-07-26 新增：非场景轴的静默休眠者 ──
    # O3V：登记了持久道具/武器（PROP_/WEAPON_）就必须逐镜验在场——「断横刀被换成弯刀/佩刀凭空消失」
    # 此前无任何机检兜底（umbrella 与场景三件套都覆盖不到）。
    {"key": "object_presence", "label": "持久道具/武器在场(O3V/OWLv2)",
     "sidecar": "生产数据/object_presence_{ep}.json", "producer": "object_presence_runner.py",
     "applies": "has_persistent_objects", "ran": "adjudicated"},
    # VAP：有角色定妆就必须有整体外观并排判定（脸 umbrella 只看脸 embedding，看不到发型/服装/体型/
    # 气质综合漂移）。无 VLM CLI 时可由多模态 agent 按 pairs 逐对看图裁决回填（同 comic vlm_adjudicate 模式）。
    {"key": "appearance_judge", "label": "外观判官(VAP/VLM并排)",
     "sidecar": "生产数据/appearance_judge_{ep}.json", "producer": "appearance_judge_runner.py",
     "applies": "has_char", "ran": "adjudicated",
     "hint": "无 N2D_VLM_CMD 时由多模态 agent 按 manifest.pairs 逐对看图裁决：回填 findings（空=全过）并盖 adjudicated:true 戳"},
    # COST：有角色定妆就必须有服装独立核验（CLIP-I 裁衣不裁脸；换装保脸的漂移只有它能量化）。
    {"key": "costume_independent", "label": "服装独立(COST/CLIP-I)",
     "sidecar": "生产数据/costume_consistency_{ep}.json", "producer": "costume_consistency.py",
     "applies": "has_char", "ran": "available_true"},
)


# ── 纯逻辑（pytest 覆盖）────────────────────────────────────────────────────────

def applies(applies_key: str, loc_assets: Sequence[Mapping[str, Any]]) -> bool:
    """该验证器是否适用于本项目（= 项目登记了它要查的数据，纯函数）。

    没登记数据就不要求（不强求无核心场景的项目装 DINOv2）；登记了就必须验（你声明了就得兑现）。
    入参实为「资产全表」（asset_registry assets + identity_registry characters 归一），场景键内部过滤 LOC_。"""
    ids = [str(a.get("id") or "") for a in loc_assets if isinstance(a, Mapping)]
    locs = [a for a in loc_assets if isinstance(a, Mapping) and str(a.get("id") or "").startswith("LOC_")]
    if applies_key == "has_loc":
        return len(locs) > 0
    if applies_key == "has_resident_assets":
        return any(((a.get("scene_dna") or {}).get("resident_assets")) for a in locs
                   if isinstance(a.get("scene_dna"), Mapping))
    if applies_key == "has_doors_windows":
        return any(((a.get("constraints") or {}).get("doors_windows")
                    or (a.get("constraints") or {}).get("floor_plan")) for a in locs
                   if isinstance(a.get("constraints"), Mapping))
    if applies_key == "has_persistent_objects":
        return any(i.startswith(("PROP_", "WEAPON_")) for i in ids)
    if applies_key == "has_char":
        return any(i.startswith("CHAR_") for i in ids)
    return False


def ran_fresh(ran_key: str, sidecar: Optional[Mapping[str, Any]]) -> bool:
    """该验证器是否**真跑过**（后端真出活，非 probe-only 占位；纯函数）。

    缺 sidecar / 后端没跑 → False（休眠）。embed_filled：任一镜真填了 embedding；detector_ran：真调过后端。"""
    if not isinstance(sidecar, Mapping):
        return False
    if ran_key == "detector_ran":
        return bool(sidecar.get("detector_ran"))
    if ran_key == "embed_filled":
        return any(isinstance(p, Mapping) and isinstance(p.get("embedding"), list) and p.get("embedding")
                   for p in (sidecar.get("probes") or []))
    if ran_key == "adjudicated":
        # manifest 无后端时也带 findings:[] 占位（不能拿键存在当裁决证据）。真裁决过的证据（任一）：
        # ① 逐 probe 路径盖的 detector/judge 戳；② batch/agent 回填后盖的 adjudicated 戳；
        # ③ findings 非空（有问题=肯定裁过）。pairs/probes 为空=本集无待判对象，不算休眠。
        if sidecar.get("adjudicated") or sidecar.get("detector") or sidecar.get("judge"):
            return True
        if isinstance(sidecar.get("findings"), list) and sidecar.get("findings"):
            return True
        items = sidecar.get("pairs") if "pairs" in sidecar else sidecar.get("probes")
        return isinstance(items, list) and not items
    if ran_key == "available_true":
        return sidecar.get("available") is True
    return False


def coverage_summary(rows: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    """覆盖率汇总：applicable / ran_fresh / dormant（休眠=适用但没真跑）。纯函数。"""
    applicable = [r for r in rows if r.get("applicable")]
    fresh = [r for r in applicable if r.get("ran_fresh")]
    return {"applicable": len(applicable), "ran_fresh": len(fresh),
            "dormant": len(applicable) - len(fresh), "total": len(rows)}


# ── I/O ────────────────────────────────────────────────────────────────────────

def _load_loc_assets(root: str) -> List[Mapping[str, Any]]:
    """资产全表：asset_registry.assets（LOC_/PROP_/WEAPON_/VFX_…）+ identity_registry.characters
    （CHAR_·归一成 {id: …}）。名字沿用历史（原来只喂场景键）；applies() 各键自行过滤。"""
    out: List[Mapping[str, Any]] = []
    try:
        from n2d_contract import asset_registry_path
        path = asset_registry_path(root)
    except Exception:
        path = os.path.join(root, "出图", "共享", "asset_registry.json")
    if os.path.isfile(path):
        try:
            data = json.load(open(path, encoding="utf-8"))
            out.extend(a for a in data.get("assets", []) if isinstance(a, Mapping))
        except Exception:
            pass
    ident = os.path.join(root, "出图", "共享", "identity_registry.json")
    if os.path.isfile(ident):
        try:
            reg = json.load(open(ident, encoding="utf-8"))
            for c in reg.get("characters", []) or []:
                if isinstance(c, Mapping):
                    cid = str(c.get("character_id") or c.get("id") or "")
                    if cid:
                        out.append({"id": cid, **{k: v for k, v in c.items() if k != "id"}})
        except Exception:
            pass
    return out


def _read_sidecar(root: str, rel: str) -> Optional[Mapping[str, Any]]:
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        return None
    try:
        data = json.load(open(path, encoding="utf-8"))
        return data if isinstance(data, Mapping) else None
    except Exception:
        return None


def scene_coverage_rows(root: str, ep: str) -> List[Dict[str, Any]]:
    """逐场景验证器状态：{key,label,applicable,ran_fresh,dormant,sidecar,producer}。"""
    locs = _load_loc_assets(root)
    rows: List[Dict[str, Any]] = []
    for spec in SCENE_VERIFIERS:
        rel = spec["sidecar"].format(ep=ep)
        ap = applies(spec["applies"], locs)
        fresh = ran_fresh(spec["ran"], _read_sidecar(root, rel)) if ap else False
        rows.append({
            "key": spec["key"], "label": spec["label"],
            "applicable": ap, "ran_fresh": fresh, "dormant": ap and not fresh,
            "sidecar": rel, "producer": spec["producer"],
            **({"hint": spec["hint"]} if spec.get("hint") else {}),
        })
    return rows
