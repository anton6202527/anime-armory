#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""场景生成侧锁「执行」层 —— 把 scene_reference_planner 的建议变成可跑的 job pack + 闭合注册环。

scene_reference_planner 只**规划/建议**（tier=backend_subject 或 suggest_scene_lora）；本模块是
**执行**侧——和角色 n2d-lora 同范式（不藏云训练在按钮后，产可审计 manifest），但作用于 LOC 场景：

  * `job   <root> --loc-id LOC_X`：产**场景 LoRA 训练 job pack**（dataset=该场景定妆/布局图/多视角 plates，
    trigger 词，训练配置，status=candidate）→ `生产数据/scene_lock/LOC_X/{dataset_manifest,train_job,card}.json`。
    真正的训练在流程外由用户跑（同角色 LoRA），本层只产可审计计划。
  * `subject <root> --loc-id LOC_X --backend kling`：产**后端主体库注册** payload（把场景当 subject 喂
    Kling 主体库 / Seedream 多参考，让后端自己锁场景——最接近 Character ID 的免训练档）。
  * `register <root> --loc-id LOC_X --kind scene_lora|scene_subject --status registered`：把锁状态**写回**
    asset_registry 的 LOC 资产，闭合环——planner 下次读到 scene_lora.status=registered 就把 tier 升到
    scene_lora、停止重复建议（生成侧锁真正生效，不再只是建议）。

dataset 复用 scene_reference_planner.plan_scene_refs（单一真值，不另抄一份参考集）。纯逻辑（job/payload
构建）有 pytest；写盘 + 改 registry 加锁串行（与 n2d-lora 同 registry 文件，避免并发交错）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_reference_planner as srp  # 复用参考集 + tier 判定（单一真值）

SCENE_LOCK_DIR = "生产数据/scene_lock"
SCENE_LORA_JOB_KIND = "n2d_scene_lora_job"
SCENE_SUBJECT_KIND = "n2d_scene_subject_registration"
_LORA_STATUSES = ("candidate", "dataset_ready", "training", "ready", "registered")
_LOCK_KINDS = ("scene_lora", "scene_subject")


# ── 纯逻辑（pytest 覆盖）────────────────────────────────────────────────────────

def _slug(text: str) -> str:
    s = re.sub(r"[^0-9A-Za-z一-鿿]+", "_", str(text or "")).strip("_").lower()
    return s or "loc"


def scene_trigger(loc_id: str) -> str:
    """场景 LoRA 触发词（确定性·可测）。"""
    return f"{_slug(loc_id)}_scene_v1"


def build_scene_lora_job(loc_asset: Mapping[str, Any]) -> Dict[str, Any]:
    """场景 LoRA 训练 job pack（纯函数）。dataset = plan_scene_refs 的真实参考槽（定妆/布局图/多视角）。"""
    loc_id = str(loc_asset.get("id") or "")
    refs = [r for r in srp.plan_scene_refs(loc_asset) if r.get("ref") and not r.get("planned")]
    dataset = [{"slot": r["slot"], "path": r["ref"], "reason": r["reason"]} for r in refs]
    return {
        "kind": SCENE_LORA_JOB_KIND,
        "loc_id": loc_id,
        "trigger": scene_trigger(loc_id),
        "status": "candidate" if dataset else "dataset_incomplete",
        "dataset": dataset,
        "dataset_count": len(dataset),
        "training": {
            "base_model_hint": "SDXL/Flux 场景 LoRA（按生图后端家族选）",
            "recommended_steps": 1200,
            "note": "场景 LoRA 锁建筑/材质/布局几何；人物清空（empty plate）以免把角色烤进场景。",
        },
        "register_ready_requires": ["训练产物 .safetensors", "≥1 张定妆/布局图 plate 在 dataset"],
        "note": "真正训练在流程外跑（同角色 LoRA）；本 pack 仅可审计计划。dataset 不足时先补场景定妆/布局图/多视角。",
    }


def build_subject_registration(loc_asset: Mapping[str, Any], backend: str) -> Dict[str, Any]:
    """后端主体库注册 payload（纯函数）——把场景当 subject 喂后端，让它自己锁场景（免训练中间档）。"""
    loc_id = str(loc_asset.get("id") or "")
    refs = [r for r in srp.plan_scene_refs(loc_asset) if r.get("ref") and not r.get("planned")]
    return {
        "kind": SCENE_SUBJECT_KIND,
        "loc_id": loc_id,
        "backend": backend,
        "subject_name": f"scene_{_slug(loc_id)}",
        "reference_images": [r["ref"] for r in refs],
        "reference_count": len(refs),
        "note": ("把该场景注册为后端 subject（Kling 主体库 / Seedream 多参考 / Nano Banana 参考），"
                 "之后该 LOC 的镜在后端侧带 subject id 出图——后端自己锁场景，最接近 Character ID。"
                 "注册后跑 register --kind scene_subject --status registered 闭合环。"),
    }


def apply_lock_status(loc_asset: Dict[str, Any], kind: str, status: str) -> Dict[str, Any]:
    """把锁状态写进 LOC 资产副本（纯函数·可测）。kind ∈ scene_lora|scene_subject。"""
    if kind not in _LOCK_KINDS:
        raise ValueError(f"kind 必须是 {_LOCK_KINDS}")
    out = dict(loc_asset)
    cur = dict(out.get(kind) or {}) if isinstance(out.get(kind), Mapping) else {}
    cur["status"] = status
    out[kind] = cur
    return out


# ── I/O driver ─────────────────────────────────────────────────────────────────

def _registry_path(root: str) -> str:
    try:
        from n2d_contract import asset_registry_path
        return asset_registry_path(root)
    except Exception:
        return os.path.join(root, "出图", "共享", "asset_registry.json")


def _load_loc(root: str, loc_id: str) -> Optional[Mapping[str, Any]]:
    path = _registry_path(root)
    if not os.path.isfile(path):
        return None
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:
        return None
    for a in data.get("assets", []):
        if isinstance(a, Mapping) and str(a.get("id")) == loc_id:
            return a
    return None


def _write(root: str, loc_id: str, name: str, payload: Mapping[str, Any]) -> str:
    out_dir = os.path.join(root, SCENE_LOCK_DIR, loc_id)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)
    return path


def cmd_job(root: str, loc_id: str) -> int:
    loc = _load_loc(root, loc_id)
    if not loc:
        print(f"⛔ 找不到 LOC 资产 {loc_id}（asset_registry）", file=sys.stderr)
        return 2
    job = build_scene_lora_job(loc)
    path = _write(root, loc_id, "scene_lora_job.json", job)
    print(f"✓ 场景 LoRA job pack（{job['status']}·dataset {job['dataset_count']} 张）→ {path}")
    if job["status"] != "candidate":
        print("  ⚠️ dataset 不足：先补该场景定妆/布局图/多视角 plate（reference_group.primary/spatial_map + scene_atlas）。")
    return 0


def cmd_subject(root: str, loc_id: str, backend: str) -> int:
    loc = _load_loc(root, loc_id)
    if not loc:
        print(f"⛔ 找不到 LOC 资产 {loc_id}", file=sys.stderr)
        return 2
    payload = build_subject_registration(loc, backend)
    path = _write(root, loc_id, f"scene_subject_{_slug(backend)}.json", payload)
    print(f"✓ 后端主体库注册 payload（{backend}·{payload['reference_count']} 参考图）→ {path}")
    return 0


def cmd_register(root: str, loc_id: str, kind: str, status: str) -> int:
    path = _registry_path(root)
    if not os.path.isfile(path):
        print(f"⛔ 缺 asset_registry：{path}", file=sys.stderr)
        return 2
    try:
        from progress import progress_lock  # 复用项目级写锁（与 n2d-lora/registry 串行）
    except Exception:
        progress_lock = None
    def _do() -> int:
        data = json.load(open(path, encoding="utf-8"))
        hit = False
        for i, a in enumerate(data.get("assets", [])):
            if isinstance(a, Mapping) and str(a.get("id")) == loc_id:
                data["assets"][i] = apply_lock_status(a, kind, status)
                hit = True
                break
        if not hit:
            print(f"⛔ 找不到 LOC 资产 {loc_id}", file=sys.stderr)
            return 2
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
        print(f"✓ 已写回 {loc_id}.{kind}.status={status}（planner 下次将据此升档/停止重复建议）")
        return 0
    if progress_lock is not None:
        with progress_lock(root):
            return _do()
    return _do()


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="场景生成侧锁执行层（LoRA job / 主体库注册 / 状态回写）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pj = sub.add_parser("job", help="产场景 LoRA 训练 job pack")
    pj.add_argument("root"); pj.add_argument("--loc-id", required=True)
    ps = sub.add_parser("subject", help="产后端主体库注册 payload")
    ps.add_argument("root"); ps.add_argument("--loc-id", required=True)
    ps.add_argument("--backend", default="kling")
    pr = sub.add_parser("register", help="把锁状态写回 registry 闭合环")
    pr.add_argument("root"); pr.add_argument("--loc-id", required=True)
    pr.add_argument("--kind", choices=_LOCK_KINDS, required=True)
    pr.add_argument("--status", choices=_LORA_STATUSES, default="registered")
    ns = ap.parse_args(argv)
    root = ns.root.rstrip("/")
    if ns.cmd == "job":
        return cmd_job(root, ns.loc_id)
    if ns.cmd == "subject":
        return cmd_subject(root, ns.loc_id, ns.backend)
    if ns.cmd == "register":
        return cmd_register(root, ns.loc_id, ns.kind, ns.status)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
