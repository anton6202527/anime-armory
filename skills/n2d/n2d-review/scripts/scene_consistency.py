#!/usr/bin/env python3
"""场景/环境一致性机检（O2）——补最后一条仍只人判的视觉轴。

2026 环境一致性已是"expected"，但脸/服装/片内都有机检了，场景还只靠人判"场景漂移"。
本脚本对**同一场景的多个镜头**做结构一致性：用 dHash（感知哈希）量两两结构距离，
**自标定**——同场景镜头互相结构应相近，离群者(远高于本组中位距离)= 该镜背景画歪了。
不直接比 `定妆_<场景>.png`（场景镜有前景人物、与空场景定妆天然差很大，比组内更稳）。

依赖 Pillow（缺则优雅跳过）。纯数学（dhash_bits/hamming/is_outlier/median）无依赖、带 pytest。

用法：python3 scene_consistency.py <作品根> 第N集 [--factor 1.8] [--floor 12] [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from typing import Dict, List, Optional, Sequence, Tuple, Any

import face_consistency as fc  # 复用 cosine（光色指纹相似度）
from n2d_contract import asset_registry_path # 导入契约路径
from pillow_compat import pixel_data

DEFAULT_FACTOR = 1.8   # 镜头平均结构距离 > 组中位 * factor → 离群
DEFAULT_FLOOR = 12     # 且绝对汉明距 > floor（64 位里差这么多才算真漂，避免小组误杀）
TONE_FACTOR = 2.2      # 光色距离 > 组中位 * factor → 光位/色调离群（比结构更宽，光色波动天然大些）
TONE_FLOOR = 0.06      # 且绝对光色距离(1-cos) > floor，避免小组误杀
TONE_BINS = 10

_SCENE_WORDS = ("场景", "战场", "荒野", "官道", "村口", "村道", "山洞", "花田", "破院", "山道", "偏厅",
                "大殿", "洞府", "山谷", "谷", "宫", "殿", "庭", "院", "厅", "房", "室", "林", "桥",
                "街", "城", "府", "门外", "广场")


# ---------- 纯数学（无依赖 · pytest 覆盖） ----------

def dhash_bits(gray: Sequence[Sequence[float]]) -> List[int]:
    """行内相邻比较的差分感知哈希位串：每行 左<右 记 1。HxW → H*(W-1) 位。"""
    bits: List[int] = []
    for row in gray:
        for x in range(len(row) - 1):
            bits.append(1 if row[x] < row[x + 1] else 0)
    return bits


def hamming(a: Sequence[int], b: Sequence[int]) -> int:
    """等长位串汉明距；长度不等取较短长度比较（容错）。"""
    return sum(1 for p, q in zip(a, b) if p != q)


def median(xs: Sequence[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    m = n // 2
    return s[m] if n % 2 else (s[m - 1] + s[m]) / 2.0


def is_outlier(value: float, group_median: float, factor: float = DEFAULT_FACTOR,
               floor: float = DEFAULT_FLOOR) -> bool:
    """离群 = 同时 超组中位*factor 且 超绝对 floor。"""
    return value > group_median * factor and value > floor


def majority_bits(bitlists: Sequence[Sequence[int]]) -> List[int]:
    """多条等长 dHash 位串 → 逐位多数票原型（纯函数·可测）。

    把一个场景所有镜的结构 dHash 压成一个「该场景的结构原型」，供**跨集**结构漂移比对：
    SCNX 的色调直方图只看颜色——同色调但家具挪位/构图朝向变了它看不出；结构原型补这一刀。
    空输入→[]；位长不一时以首条长度为准（容错截断）。"""
    lists = [list(b) for b in bitlists if b]
    if not lists:
        return []
    n = len(lists[0])
    half = len(lists) / 2.0
    return [1 if sum(1 for b in lists if i < len(b) and b[i]) > half else 0 for i in range(n)]


def scene_struct_prototypes(root: str, ep: str) -> Dict[str, List[int]]:
    """本集每个场景的结构原型 dHash（该场景所有镜 dHash 的逐位多数票）。

    供跨集结构漂移累积（生产数据/scene_struct_ep_means.json）——治"同房间隔几集被重新布置/朝向画反/
    构图大改"这类**色调没动、结构变了**的漂移（SCNX 色调直方图看不出）。缺 Pillow/无场景镜 → 空 dict。"""
    if not _probe_pillow():
        return {}
    smap = _scene_of_shot(root, ep)
    groups: Dict[str, List[List[int]]] = {}
    for png, scene in smap.items():
        h = _dhash_image(os.path.join(root, "出图", ep, png))
        if h:
            groups.setdefault(scene, []).append(h)
    return {scene: majority_bits(hs) for scene, hs in groups.items() if hs}

# --- 新增: 击中帧物理光影突变验证 ---
def verify_impact_frames(root: str, ep: str) -> List[Dict[str, Any]]:
    """扫描拥有 impact_frame_sync 契约的击中帧，验证其亮度和饱和度是否产生爆发式离群。"""
    if not _probe_pillow():
        return []
    import json
    from PIL import Image
    import os
    
    findings = []
    storyboard_path = os.path.join(root, "脚本", ep, "storyboard.json")
    if not os.path.exists(storyboard_path):
        return []
        
    try:
        with open(storyboard_path, 'r', encoding='utf-8') as f:
            sb = json.load(f)
    except Exception:
        return []
        
    for i, clip in enumerate(sb.get("clips", [])):
        contract = clip.get("template_contract", {})
        if not isinstance(contract, dict):
            continue
        if contract.get("impact_frame_sync"):
            clip_id = clip.get("id", f"Clip_{i+1:02d}")
            # Locate mid_impact frame
            mid_frame_path = os.path.join(root, "出视频", ep, "图片", f"{clip_id}_mid.png")
            first_frame_path = os.path.join(root, "出视频", ep, "图片", f"{clip_id}.png")
            
            if os.path.exists(mid_frame_path) and os.path.exists(first_frame_path):
                try:
                    # Luma extraction for primitive brightness surge detection
                    mid_img = Image.open(mid_frame_path).convert("L")
                    first_img = Image.open(first_frame_path).convert("L")
                    
                    mid_stat = sum(list(pixel_data(mid_img))) / (mid_img.width * mid_img.height)
                    first_stat = sum(list(pixel_data(first_img))) / (first_img.width * first_img.height)
                    
                    # Impact requires > 15% brightness surge representing spell/flash impact
                    if mid_stat < first_stat * 1.15:
                        findings.append({
                            "type": "impact_physics_failure",
                            "clip": clip_id,
                            "severity": "warn",
                            "message": f"击中帧(mid-frame)缺少物理光效反馈。检测到光照激增低于 15%，打击感软弱，请重绘爆发光影。",
                            "expected_surge": "> 15%",
                            "actual_surge": f"{(mid_stat/first_stat - 1)*100:.1f}%"
                        })
                except Exception:
                    pass
    return findings
# ----------------------------------


# ---------- 资产注册层集成 (Q28·结构唯一性) ----------

def _load_asset_registry(root: str) -> Dict[str, Dict[str, Any]]:
    """加载资产注册层，返回 {asset_id: {constraints, drift_forbidden, name}}。"""
    path = asset_registry_path(root)
    if not os.path.isfile(path):
        return {}
    try:
        data = json.load(open(path, encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("assets"), list):
            return {}
        return {a["id"]: a for a in data["assets"] if isinstance(a, dict) and "id" in a}
    except Exception:
        return {}


def _match_asset_id(scene_name: str, registry: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """根据场景定妆名（如 "定妆_沈府大殿"）匹配资产 ID（如 "LOC_沈府大殿"）。"""
    base_name = scene_name.replace(".png", "")
    for prefix in ("场景_", "地点_", "定妆_场景_", "定妆_"):
        if base_name.startswith(prefix):
            base_name = base_name[len(prefix):]
    # 1) 精确匹配
    if base_name in registry:
        return base_name
    # 2) 补齐前缀匹配
    for prefix in ("LOC_", "PROP_", "OUTFIT_", "VFX_"):
        candidate = prefix + base_name
        if candidate in registry:
            return candidate
    # 3) 模糊匹配
    for aid, asset in registry.items():
        name = str(asset.get("name", ""))
        if base_name in aid or base_name in name or (name and name in base_name):
            return aid
    return None


# ---------- 图像（需 Pillow） ----------

def _dhash_image(path: str) -> Optional[List[int]]:
    try:
        from PIL import Image  # type: ignore
        im = Image.open(path).convert("L").resize((9, 8))
        w, h = im.size
        px = list(pixel_data(im))
        gray = [[float(px[y * w + x]) for x in range(w)] for y in range(h)]
        return dhash_bits(gray)  # 8*(9-1)=64 位
    except Exception:
        return None


def _probe_pillow() -> bool:
    try:
        import PIL  # noqa
        return True
    except Exception:
        return False


def _tone_fp(path: str, bins: int = TONE_BINS) -> Optional[List[float]]:
    """光位/色调指纹：明度直方图（主光强度·高调低调）+ 饱和度加权色相直方图（场景色调）。
    同一场景跨镜应一致——某镜光打错方向/色温跳/调色跳 → 该指纹离群（光位锚的可机检代理）。"""
    try:
        from PIL import Image  # type: ignore
        im = Image.open(path).convert("RGB"); im.thumbnail((96, 96))
        hsv = im.convert("HSV"); px = list(pixel_data(hsv))
        vh = [0.0] * bins; hh = [0.0] * bins; tot = 0.0
        for h, s, v in px:
            vi = min(int(v / 256 * bins), bins - 1); vh[vi] += 1.0
            w = (s / 255.0) * (v / 255.0)
            if w > 0:
                hi = min(int(h / 256 * bins), bins - 1); hh[hi] += w; tot += w
        n = len(px) or 1
        vh = [x / n for x in vh]
        hh = [x / tot for x in hh] if tot > 0 else hh
        return vh + hh
    except Exception:
        return None


def _scene_of_shot(root: str, ep: str) -> Dict[str, str]:
    """每镜 PNG → 它引用的场景定妆名。

    兼容两类 prompt：
    - 旧版：参考图里只有 `定妆_<场景名>.png`；
    - 新版：目标落档写 `出图/第N集/图片/ClipXX_*.png`，场景参考图绑定 `LOC_*`。
    """
    p = os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")
    out: Dict[str, str] = {}
    if not os.path.isfile(p):
        return out
    registry = _load_asset_registry(root)
    for blk in re.split(r"(?m)(?=^## )", open(p, encoding="utf-8").read()):
        if not blk.strip().startswith("## "):
            continue
        pngs = []
        for mt in re.finditer(rf"出图/{re.escape(ep)}/([^`』\s，,）)]+\.png)", blk):
            png = mt.group(1)
            if png.startswith("图片/") and png not in pngs:
                pngs.append(png)
        if not pngs:
            mt = re.search(r"出图/[^/]+/([^`』\s]+\.png)", blk)
            if mt:
                pngs = [mt.group(1)]
        if not pngs:
            continue
        m = re.search(r"(?ms)(?:\*\*)?参考图(?:\*\*)?.*?(?=^###\s+|^##\s+|\Z)", blk)
        refs = m.group(0) if m else ""
        scene = ""
        loc = re.search(r"绑定\s+`?(LOC_[A-Za-z0-9_\-]+)`?", refs) or re.search(r"`(LOC_[A-Za-z0-9_\-]+)`", blk)
        if loc:
            asset = registry.get(loc.group(1)) or {}
            scene = str(asset.get("name") or loc.group(1))
        if not scene:
            scenes = []
            for s in re.findall(r"定妆_([^`\s，。、,）)]+)", refs):
                clean = s.replace(".png", "")
                for prefix in ("场景_", "地点_"):
                    if clean.startswith(prefix):
                        clean = clean[len(prefix):]
                if any(w in clean for w in _SCENE_WORDS):
                    scenes.append(clean)
            if scenes:
                scene = scenes[0]
        if scene:
            for png in pngs:
                out[png] = scene
    return out


def scene_tone_means(root: str, ep: str) -> Dict[str, List[float]]:
    """本集每个场景的平均光位/色调指纹（_tone_fp 在该场景所有镜上的逐维均值）。

    供**跨集**场景漂移累积（生产数据/scene_ep_means.json）——治"每集内部一致、却跨集慢慢变样"的
    场景漂：脸有 G5 跨集漂移机检，场景轴此前完全没有（intra-episode dHash 只看集内）。色调均值比
    structural dhash 更稳（场景镜有前景人物，色调对前景没那么敏感）。缺 Pillow/无场景镜 → 空 dict。纯读盘。"""
    if not _probe_pillow():
        return {}
    smap = _scene_of_shot(root, ep)
    groups: Dict[str, List[List[float]]] = {}
    for png, scene in smap.items():
        fp = _tone_fp(os.path.join(root, "出图", ep, png))
        if fp:
            groups.setdefault(scene, []).append(fp)
    out: Dict[str, List[float]] = {}
    for scene, fps in groups.items():
        n = len(fps)
        dim = len(fps[0])
        out[scene] = [round(sum(f[i] for f in fps) / n, 6) for i in range(dim)]
    return out


def _mean_hue_sat(path: str) -> Optional[Tuple[float, float]]:
    """图像饱和度加权平均色相(0-360°·圆周均值) + 平均饱和度(0-1)。供 lighting_signature 数值核对。
    暗/灰像素色相不可靠 → 色相用 sat*val 加权圆周均值；饱和度用全图均值（对齐 saturation_range
    "整体低饱和"语义）。全灰 → 色相返回 0（无意义，调用方据饱和判定）。需 Pillow。"""
    try:
        from PIL import Image  # type: ignore
        im = Image.open(path).convert("RGB"); im.thumbnail((96, 96))
        px = list(pixel_data(im.convert("HSV")))
    except Exception:
        return None
    if not px:
        return None
    import math
    sx = sy = wsum = ssum = 0.0
    for h, s, v in px:
        sat = s / 255.0
        ssum += sat
        w = sat * (v / 255.0)
        if w > 0:
            ang = (h / 255.0) * 2 * math.pi
            sx += w * math.cos(ang); sy += w * math.sin(ang); wsum += w
    mean_sat = ssum / len(px)
    if wsum <= 0:
        return (0.0, round(mean_sat, 4))
    hue_deg = (math.degrees(math.atan2(sy, sx)) + 360.0) % 360.0
    return (round(hue_deg, 1), round(mean_sat, 4))


def hue_circular_dist(a: float, b: float) -> float:
    """两色相角(0-360°)的圆周距离(0-180)。纯函数·可测。"""
    d = abs(float(a) - float(b)) % 360.0
    return round(min(d, 360.0 - d), 1)


def lighting_signature_rows(root: str, ep: str, hue_tol: float = 40.0, sat_margin: float = 0.08) -> List[dict]:
    """场景 constraints.lighting_signature 数值强制（接活死 schema）：逐镜实测色相/饱和度 vs 注册值。

    此前 mean_hue/saturation_range/key_light_direction 是写了没人读的死字段（_tone_fp 自比组内中位，
    从不对注册数值核对）。这里逐镜测：色相圆周偏离注册 mean_hue > hue_tol，或平均饱和度落在
    saturation_range±margin 外 → warn（色温/调色与登记的场景光照签名矛盾）。只对**登记了 lighting_signature**
    的场景生效。前景人物会带色相噪声 → tol 取宽 + warn 级（不硬阻断·数值化但不沙化）。需 Pillow。"""
    if not _probe_pillow():
        return []
    registry = _load_asset_registry(root)
    smap = _scene_of_shot(root, ep)
    rows: List[dict] = []
    for png, scene in sorted(smap.items()):
        aid = _match_asset_id(scene, registry)
        asset = registry.get(aid) if aid else None
        sig = ((asset or {}).get("constraints") or {}).get("lighting_signature") if isinstance(asset, dict) else None
        if not isinstance(sig, dict):
            continue
        meas = _mean_hue_sat(os.path.join(root, "出图", ep, png))
        if meas is None:
            continue
        hue, sat = meas
        bad: List[str] = []
        tgt_hue = sig.get("mean_hue")
        if isinstance(tgt_hue, (int, float)):
            dist = hue_circular_dist(hue, float(tgt_hue))
            if dist > hue_tol:
                bad.append(f"色相 {hue}° 偏离登记 mean_hue {tgt_hue}°（差 {dist}°>容差 {hue_tol}°）")
        rng = sig.get("saturation_range")
        if isinstance(rng, (list, tuple)) and len(rng) == 2:
            try:
                lo, hi = float(rng[0]), float(rng[1])
                if sat < lo - sat_margin or sat > hi + sat_margin:
                    bad.append(f"饱和度 {sat} 出登记区间 [{lo},{hi}]±{sat_margin}")
            except (TypeError, ValueError):
                pass
        if bad:
            rows.append({"png": png, "scene": scene, "verdict": "warn",
                         "msg": (f"场景[{scene}] 光照签名数值矛盾：" + "；".join(bad)
                                 + "——对齐场景定妆光色，或确认是否 allowed_variations 内的合理变化。"),
                         "measured_hue": hue, "measured_sat": sat})
    return rows


def analyze(root: str, ep: str, factor: float = DEFAULT_FACTOR, floor: float = DEFAULT_FLOOR) -> dict:
    res: dict = {"available": _probe_pillow(), "groups": {}, "shots": [], "notes": [], "impact_physics": []}
    if not res["available"]:
        res["notes"].append("场景一致性机检已跳过（未装 Pillow）——背景漂移暂由人判并排读图。")
        return res
        
    # --- 新增: 触发击中帧光影验证 ---
    res["impact_physics"] = verify_impact_frames(root, ep)
    
    smap = _scene_of_shot(root, ep)
    registry = _load_asset_registry(root)
    # 按场景分组
    groups: Dict[str, List[str]] = {}
    for png, scene in smap.items():
        full = os.path.join(root, "出图", ep, png)
        if os.path.exists(full):
            groups.setdefault(scene, []).append(png)
    for scene, pngs in sorted(groups.items()):
        hashes = {p: _dhash_image(os.path.join(root, "出图", ep, p)) for p in pngs}
        hashes = {p: h for p, h in hashes.items() if h is not None}
        
        # 查找资产注册层约束
        asset_id = _match_asset_id(scene, registry)
        asset = registry.get(asset_id) if asset_id else None
        constraints = asset.get("constraints") if asset else None
        
        group_summary: Dict[str, Any] = {"shots": len(hashes)}
        if constraints:
            group_summary["registered_id"] = asset_id
            group_summary["constraints"] = constraints
            for ck, cv in constraints.items():
                res["notes"].append(f"场景[{scene}] 已注册{ck}：{cv}。验收时请重点核对。")

        if len(hashes) < 3:   # 组太小，统计不稳，跳过（少于3镜无法定离群）
            group_summary["skipped"] = "组<3镜"
            res["groups"][scene] = group_summary
            continue
        
        # 每镜对组内其他镜的平均汉明距
        names = list(hashes)
        avg = {}
        for p in names:
            ds = [hamming(hashes[p], hashes[q]) for q in names if q != p]
            avg[p] = sum(ds) / len(ds)
        gmed = median(list(avg.values()))
        group_summary["median_dist"] = round(gmed, 1)
        res["groups"][scene] = group_summary
        for p in names:
            if is_outlier(avg[p], gmed, factor, floor):
                res["shots"].append({"png": p, "scene": scene, "kind": "结构", "avg_dist": round(avg[p], 1),
                                     "group_median": round(gmed, 1), "verdict": "warn"})
        # ③ 光位/色调离群（同场景跨镜光打错/色调跳——光位锚的可机检代理）
        tfps = {p: _tone_fp(os.path.join(root, "出图", ep, p)) for p in names}
        tfps = {p: f for p, f in tfps.items() if f is not None}
        if len(tfps) >= 3:
            tnames = list(tfps)
            tavg = {p: sum(1.0 - fc.cosine(tfps[p], tfps[q]) for q in tnames if q != p) / (len(tnames) - 1)
                    for p in tnames}
            tmed = median(list(tavg.values()))
            for p in tnames:
                if is_outlier(tavg[p], tmed, TONE_FACTOR, TONE_FLOOR):
                    res["shots"].append({"png": p, "scene": scene, "kind": "光色", "avg_dist": round(tavg[p], 3),
                                         "group_median": round(tmed, 3), "verdict": "warn"})
    return res


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--factor", type=float, default=DEFAULT_FACTOR)
    ap.add_argument("--floor", type=float, default=DEFAULT_FLOOR)
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode, ns.factor, ns.floor)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"=== 场景/环境一致性机检（同场景结构离群·自标定）：{ns.root} {ns.episode} ===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    for s in res["shots"]:
        if s.get("kind") == "光色":
            print(f"⚠️ {s['png']} · 场景[{s['scene']}] 光色离群 dist {s['avg_dist']} ≫ 组中位 {s['group_median']}（疑光位/色调跳：光打错向/色温跳/调色跳）")
        else:
            print(f"⚠️ {s['png']} · 场景[{s['scene']}] 结构离群 dist {s['avg_dist']} ≫ 组中位 {s['group_median']}（疑背景漂移）")
    nstruct = sum(1 for s in res["shots"] if s.get("kind") != "光色")
    ntone = sum(1 for s in res["shots"] if s.get("kind") == "光色")
    print(f"\n场景漂移疑似 🟡 结构 {nstruct} · 光色 {ntone} · 共 {len(res['groups'])} 个场景组")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
