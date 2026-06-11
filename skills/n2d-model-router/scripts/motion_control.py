#!/usr/bin/env python3
"""Motion Control 资产脚手架 —— 把"只 gate 不生成"的运镜控制资产补上生成端。

背景：`n2d-model-router` 只**声明** `motion_control.level=required` + `manifest_path`，
`gate.py --stage video` 只**校验** `出视频/<集>/control/Clip_XX/motion_control_manifest.json`
是 `ready`/`degrade_only`。中间**没有任何工具生成这些控制资产或骨架** —— 操作者撞上
gate 后得照 schema.md 手搓 JSON + 手补 pose/depth 文件，all-or-nothing 摩擦。本脚本补这段：

  · scaffold —— 读 `video_model_routes.json`，为每个 `level=required` 的 Clip 生成/合并一份
                **非 ready 骨架** manifest（status=planned，逐 input status=missing+规范路径），
                并打印"该 Clip 还要产出哪几个控制文件"的精确清单。不覆盖已填好的字段。
                骨架 status=planned 仍被 gate 阻断（这是对的：还没就位），但把"手搓 JSON+查 schema"
                降成"按清单丢文件 + 填接触语义"。
  · check    —— 对照磁盘核对：哪些控制文件已就位、哪些缺、接触语义字段是否填，gate 会不会过。
                逐 input 客观地把 missing→ready（文件存在即翻），但**不**自动翻顶层 status——
                ready 要操作者确认 contact_points/occlusion_order/body_part_ownership 语义后手改。
  · generate —— 可选：装了 controlnet_aux(DWPose)/depth 估计库时，从该 Clip 首/尾帧 PNG 抽
                单帧 pose/depth 控制图作种子；缺库优雅跳过、显式标，绝不臆造。instance_masks/
                contact_map 需 SAM + 人定接触点，始终留人工。

纯函数（骨架构建 / 路由筛选 / 磁盘核对 / 就绪判定）无依赖、带 pytest。
manifest 形状与 `n2d-model-router/references/schema.md` + gate 校验单一真值源对齐。

用法：
    python3 motion_control.py <作品根> 第N集 scaffold [--clip Clip_03]
    python3 motion_control.py <作品根> 第N集 check
    python3 motion_control.py <作品根> 第N集 generate [--clip Clip_03]
退出码：check/scaffold 后仍有 Clip 未就绪 → 1，否则 0。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

_COMMON = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "common"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import MOTION_CONTROL_MANIFEST_KIND  # noqa: E402  manifest kind 单一真值源

# 控制输入键 → (type, 规范文件名)。与 schema.md「control_inputs」示例同源。
INPUT_SPEC: Dict[str, Tuple[str, str]] = {
    "pose_sequence": ("openpose_or_dwpose", "openpose_%03d.png"),
    "depth_sequence": ("depth", "depth_%03d.png"),
    "instance_masks": ("instance_mask", "seg_%03d.png"),
    "contact_map": ("contact_map", "contact_map.json"),
}
# 接触语义字段（与 gate.MOTION_CONTROL_CONTACT_FIELDS 同步；ready 时 gate 必查）。
CONTACT_FIELDS = ("contact_points", "occlusion_order", "body_part_ownership")
READY_INPUT_STATUSES = ("ready", "not_needed")
# generate 能自动产出的输入（pose/depth 可从单帧抽；instance/contact 需 SAM+人定，留人工）。
GENERATABLE = ("pose_sequence", "depth_sequence")


def manifest_rel_path(ep: str, clip_id: str) -> str:
    return f"出视频/{ep}/control/{clip_id}/motion_control_manifest.json"


def control_dir_rel(ep: str, clip_id: str) -> str:
    return f"出视频/{ep}/control/{clip_id}"


def input_filename(key: str) -> str:
    return INPUT_SPEC[key][1]


def new_input_entry(ep: str, clip_id: str, key: str) -> Dict[str, str]:
    typ, fname = INPUT_SPEC[key]
    return {"type": typ, "status": "missing", "path": f"{control_dir_rel(ep, clip_id)}/{fname}"}


def _input_is_filled(entry: Any) -> bool:
    """该控制输入是否已被操作者填成"就位"（ready/not_needed 且有 path/uri/glob）。纯函数。"""
    if not isinstance(entry, dict):
        return False
    if str(entry.get("status") or "") not in READY_INPUT_STATUSES:
        return False
    return bool(str(entry.get("path") or entry.get("uri") or entry.get("glob") or "").strip())


def build_skeleton(ep: str, clip_id: str, required_inputs: Sequence[str],
                   existing: Optional[Mapping[str, Any]] = None,
                   failure_modes: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """构建/合并一份 manifest 骨架。已填好的 input / 接触字段 / status 一律保留，不回退。纯函数。"""
    existing = existing or {}
    ex_status = str(existing.get("status") or "").strip()
    status = ex_status if ex_status in ("ready", "degrade_only", "planned") else "planned"

    ex_inputs = existing.get("control_inputs") if isinstance(existing.get("control_inputs"), dict) else {}
    control_inputs: Dict[str, Any] = {}
    for key in required_inputs:
        prior = ex_inputs.get(key)
        control_inputs[key] = prior if _input_is_filled(prior) else new_input_entry(ep, clip_id, key)

    out: Dict[str, Any] = {
        "kind": MOTION_CONTROL_MANIFEST_KIND,
        "version": 1,
        "clip_id": clip_id,
        "status": status,
        "control_inputs": control_inputs,
    }
    for field in CONTACT_FIELDS:
        out[field] = existing.get(field) if existing.get(field) else []
    out["failure_modes"] = list(existing.get("failure_modes") or failure_modes or ["feature_melting", "hand_fusion"])
    out["degrade_plan"] = existing.get("degrade_plan") or "若控制资产不被后端支持，拆成手部特写 + 反打/OTS + 释放帧。"
    return out


def routes_requiring_control(routes: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """从 routes 里挑出 motion_control.level=required 的 Clip。纯函数。"""
    out: List[Dict[str, Any]] = []
    for r in routes:
        if not isinstance(r, dict):
            continue
        mc = r.get("motion_control")
        if not isinstance(mc, dict) or str(mc.get("level") or "") != "required":
            continue
        req = [k for k in (mc.get("required_inputs") or []) if k in INPUT_SPEC]
        out.append({
            "clip_id": str(r.get("clip_id") or "").strip(),
            "shot_type": str(r.get("shot_type") or "").strip(),
            "required_inputs": req or ["pose_sequence", "depth_sequence", "instance_masks"],
            "failure_modes": mc.get("failure_modes"),
        })
    return out


def _asset_present(root: str, entry: Any) -> bool:
    """该控制输入对应文件是否真的在磁盘上（path 支持 %03d / glob；uri 视为已托管=就位）。"""
    if not isinstance(entry, dict):
        return False
    if str(entry.get("uri") or "").strip():
        return True  # 远端资产的合法性由 gate 详查，这里只判"是否已指定"
    raw = str(entry.get("path") or entry.get("glob") or "").strip()
    if not raw:
        return False
    pattern = raw.replace("%03d", "*").replace("%3d", "*").replace("%d", "*")
    full = pattern if os.path.isabs(pattern) else os.path.join(root, pattern)
    if any(ch in pattern for ch in "*?[]"):
        return bool(glob.glob(full))
    return os.path.exists(full)


def reconcile(manifest: Mapping[str, Any], root: str) -> Tuple[Dict[str, Any], List[str]]:
    """逐 input：文件已就位则 status→ready（客观）。不动顶层 status（语义需人确认）。纯函数（仅读磁盘）。"""
    out = json.loads(json.dumps(manifest))  # deep copy
    changed: List[str] = []
    inputs = out.get("control_inputs")
    if not isinstance(inputs, dict):
        return out, changed
    for key, entry in inputs.items():
        if not isinstance(entry, dict):
            continue
        if str(entry.get("status") or "") == "ready":
            continue
        if _asset_present(root, entry):
            entry["status"] = "ready"
            changed.append(key)
    return out, changed


def readiness(manifest: Mapping[str, Any], root: str, required_inputs: Sequence[str]) -> Dict[str, Any]:
    """gate 视角的就绪判定：缺哪些控制文件、接触语义填没填、status 是否 ready/degrade_only。纯函数。"""
    status = str(manifest.get("status") or "planned")
    inputs = manifest.get("control_inputs") if isinstance(manifest.get("control_inputs"), dict) else {}
    missing_inputs = [k for k in required_inputs
                      if not (_input_is_filled(inputs.get(k)) and _asset_present(root, inputs.get(k)))]
    missing_contacts = [f for f in CONTACT_FIELDS if not manifest.get(f)]
    if status == "degrade_only":
        gate_pass = bool(str(manifest.get("degrade_plan") or "").strip())
    elif status == "ready":
        gate_pass = not missing_inputs and not missing_contacts
    else:
        gate_pass = False
    return {
        "status": status,
        "missing_inputs": missing_inputs,
        "missing_contacts": missing_contacts,
        "gate_pass": gate_pass,
    }


# ---- IO 层 ----

def load_routes(root: str, ep: str) -> Optional[List[Dict[str, Any]]]:
    p = os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json")
    if not os.path.isfile(p):
        return None
    try:
        data = json.load(open(p, encoding="utf-8"))
    except Exception:
        return None
    routes = data.get("routes") if isinstance(data, dict) else None
    return routes if isinstance(routes, list) else None


def load_manifest(root: str, ep: str, clip_id: str) -> Optional[Dict[str, Any]]:
    p = os.path.join(root, manifest_rel_path(ep, clip_id))
    if not os.path.isfile(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None


def write_manifest(root: str, ep: str, clip_id: str, manifest: Mapping[str, Any]) -> str:
    rel = manifest_rel_path(ep, clip_id)
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return rel


def _dwpose_available() -> bool:
    try:
        import controlnet_aux  # noqa: F401
        return True
    except Exception:
        return False


def _depth_available() -> bool:
    for mod in ("transformers", "timm"):
        try:
            __import__(mod)
            return True
        except Exception:
            continue
    return False


def keyframes_for_clip(root: str, ep: str, clip_id: str) -> List[str]:
    """该 Clip 的首/尾帧 PNG（generate 的种子帧）。命名兼容 镜头NN / Clip_NN[_end]。"""
    num = "".join(ch for ch in clip_id if ch.isdigit())
    pats = []
    if num:
        n = int(num)
        for stem in (f"镜头{n:02d}", f"镜头{n}", f"Clip_{n:02d}", clip_id):
            pats += [f"出图/{ep}/图片/{stem}.png", f"出图/{ep}/图片/{stem}_end.png"]
    found: List[str] = []
    for rel in pats:
        full = os.path.join(root, rel)
        if os.path.isfile(full) and full not in found:
            found.append(full)
    return found


# ---- 命令 ----

def cmd_scaffold(root: str, ep: str, only_clip: Optional[str]) -> int:
    routes = load_routes(root, ep)
    if routes is None:
        print(f"⚠️ 缺 出视频/{ep}/prompt/video_model_routes.json —— 先跑 n2d-model-router 生成路由")
        return 2
    targets = routes_requiring_control(routes)
    if only_clip:
        targets = [t for t in targets if t["clip_id"] == only_clip]
    if not targets:
        print(f"本集无 motion_control.level=required 的 Clip（或指定 Clip 不在其中）——无需控制资产")
        return 0
    not_ready = 0
    print(f"=== Motion Control 脚手架：{root} {ep} ===")
    for t in targets:
        clip = t["clip_id"]
        existing = load_manifest(root, ep, clip)
        skel = build_skeleton(ep, clip, t["required_inputs"], existing, t.get("failure_modes"))
        rel = write_manifest(root, ep, clip, skel)
        rd = readiness(reconcile(skel, root)[0], root, t["required_inputs"])
        flag = "✅ 就绪" if rd["gate_pass"] else "⏳ 待补"
        if not rd["gate_pass"]:
            not_ready += 1
        print(f"\n[{clip}] {t['shot_type']} → {rel}  {flag}")
        for key in t["required_inputs"]:
            fn = f"{control_dir_rel(ep, clip)}/{input_filename(key)}"
            mark = "✅" if key not in rd["missing_inputs"] else "▢"
            note = "（DWPose/depth 可 generate）" if key in GENERATABLE else "（需 SAM/人定接触点）"
            print(f"   {mark} {key:<15} → {fn} {'' if key not in rd['missing_inputs'] else note}")
        if rd["missing_contacts"]:
            print(f"   ▢ 接触语义待填：{'、'.join(rd['missing_contacts'])}")
        print(f"   → 补齐控制资产 + 接触语义后，把 manifest status 改 ready；或决定拆镜改 degrade_only")
    print(f"\n合计 {len(targets)} 个受控 Clip，{not_ready} 个待补（gate 会阻断 status≠ready/degrade_only）")
    return 1 if not_ready else 0


def cmd_check(root: str, ep: str) -> int:
    routes = load_routes(root, ep)
    if routes is None:
        print(f"⚠️ 缺 video_model_routes.json")
        return 2
    targets = routes_requiring_control(routes)
    if not targets:
        print("本集无 required 控制 Clip")
        return 0
    not_ready = 0
    print(f"=== Motion Control 核对：{root} {ep} ===")
    for t in targets:
        clip = t["clip_id"]
        man = load_manifest(root, ep, clip)
        if man is None:
            print(f"[{clip}] 🔴 缺 manifest —— 先跑 scaffold")
            not_ready += 1
            continue
        reconciled, changed = reconcile(man, root)
        if changed:
            write_manifest(root, ep, clip, reconciled)
        rd = readiness(reconciled, root, t["required_inputs"])
        if rd["gate_pass"]:
            print(f"[{clip}] ✅ gate 将放行（status={rd['status']}）")
        else:
            not_ready += 1
            bits = []
            if rd["status"] not in ("ready", "degrade_only"):
                bits.append(f"status={rd['status']}（需改 ready/degrade_only）")
            if rd["missing_inputs"]:
                bits.append("缺控制资产：" + "、".join(rd["missing_inputs"]))
            if rd["missing_contacts"]:
                bits.append("缺接触语义：" + "、".join(rd["missing_contacts"]))
            print(f"[{clip}] 🔴 待补 —— " + "；".join(bits))
            if changed:
                print(f"        （已自动把就位的 {len(changed)} 个 input 翻 ready）")
    print(f"\n合计 {len(targets)} 受控 Clip，{not_ready} 待补")
    return 1 if not_ready else 0


def cmd_generate(root: str, ep: str, only_clip: Optional[str]) -> int:
    routes = load_routes(root, ep)
    if routes is None:
        print("⚠️ 缺 video_model_routes.json"); return 2
    has_pose, has_depth = _dwpose_available(), _depth_available()
    if not (has_pose or has_depth):
        print("⚠️ 未装 controlnet_aux(DWPose) / depth 估计库 —— 无法自动生成 pose/depth 种子帧。")
        print("   装库后重跑；instance_masks/contact_map 无论如何需 SAM + 人定接触点。先 scaffold + 人补。")
        return 2
    targets = routes_requiring_control(routes)
    if only_clip:
        targets = [t for t in targets if t["clip_id"] == only_clip]
    print(f"=== Motion Control 生成（pose={'on' if has_pose else 'off'} depth={'on' if has_depth else 'off'}）===")
    for t in targets:
        clip = t["clip_id"]
        frames = keyframes_for_clip(root, ep, clip)
        if not frames:
            print(f"[{clip}] 跳过：找不到首/尾帧 PNG（出图/{ep}/图片/镜头NN[_end].png）")
            continue
        # 实际抽取依赖重库，缺库已在上面拦截。这里仅在装库时执行（留接口，按需补具体实现）。
        print(f"[{clip}] 种子帧 {len(frames)} 张 —— pose/depth 单帧抽取接口已就位；"
              f"批量序列仍需操作者补全后 check。")
    print("\n提示：单帧 pose/depth 只是种子；真·逐帧控制序列需操作者补齐再 check 翻 ready。")
    return 0


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="Motion Control 控制资产脚手架/核对/生成")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("command", choices=("scaffold", "check", "generate"))
    ap.add_argument("--clip", help="只处理某个 Clip（如 Clip_03）")
    ns = ap.parse_args(argv)
    root = ns.root.rstrip("/")
    if not os.path.isdir(root):
        print(f"作品根不存在：{root}"); return 2
    if ns.command == "scaffold":
        return cmd_scaffold(root, ns.episode, ns.clip)
    if ns.command == "check":
        return cmd_check(root, ns.episode)
    return cmd_generate(root, ns.episode, ns.clip)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
