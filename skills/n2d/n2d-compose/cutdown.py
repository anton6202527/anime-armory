#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""n2d 多时长 cutdown 重剪规划 + 渲染：从一集成片母带的 storyboard 选镜，剪成更短交付件
（如 60s 正片 → 30s/15s 信息流引流版）。

**语境差异（vendored fork·参照同仓另一条创作线的成熟重剪实现·不跨线 import）**：
  n2d 是漫剧/短剧——cutdown 优先保留的骨架是**钩子 / 爽点 / 反转 / 集尾 cliffhanger**
  （引流版要留住人 + 留断点逼追更），而不是带货那种「产品 / CTA」骨架。镜头优先级读 n2d storyboard.json
  每 Clip 的 `rhythm`（张力词：爽点/爆发/反转/高潮/钩子/集尾…，与 tension_mix.py 同源词表）
  与 `钩子` 字段（hook/climax/end）。集尾 cliffhanger 是漫剧 cutdown 的硬骨架：短版也必须以
  断点收尾，否则丢了追更钩。

**镜头时长来源是 `脚本/<集>/镜头时长.json`（分镜定稿闸门 finalize_storyboard 产物）**——n2d 里它是
  `{镜头/clip_key: 秒}` 的**字典**（与参照实现的列表 schema 不同，这是关键适配点）。storyboard 里的
  `duration` 可能是脚本规划值/0 占位，定稿时长才是权威。任一保留镜时长解析不出来 → block，拒绝出计划。

`--render` 模式：按计划 trim/concat 出视频/<集>/视频/ 对应 clip，filter-concat 归一拼接成 MP4
  （需要 ffmpeg；无 ffmpeg 时只出计划）。自包含纯标准库 + pytest。

用法：
    python3 cutdown.py <作品根> 第1集 --target 15s --json 合成/交付/第1集/plan_15s.json
    python3 cutdown.py <作品根> 第1集 --target 15s --render
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

# rhythm 张力词（rhythm 含此子串即命中）→ cutdown 保留优先级。数字越大越先保留。
# 漫剧引流版骨架：钩子/爽点/反转/高潮/集尾 cliffhanger 必保，铺垫/留白/细节可砍。
# 词表与 tension_mix.py 的 RHYTHM_GAIN 同源（本线自定义·不进共享常量）。
RHYTHM_PRIORITY = (
    # (子串, 优先级)，按命中先后取第一个匹配
    ("集尾", 96), ("cliffhanger", 96), ("断点", 95),
    ("反转", 94), ("爽点", 92), ("爆发", 92), ("高潮", 92), ("觉醒", 90),
    ("钩子", 88), ("hook", 88),
    ("危机", 70), ("对峙", 68), ("压迫", 66), ("加速", 66),
    ("反应", 55), ("反压", 58), ("定场", 52), ("反差", 60),
    ("铺垫", 38), ("悬念", 45), ("细节", 35), ("留白", 32), ("定格", 32), ("过渡", 30),
)

# `钩子` 字段（hook/climax/end）→ 优先级（与 rhythm 取较大者）。集尾 end 视作 cliffhanger 骨架。
HOOK_FIELD_PRIORITY = {
    "end": 96, "集尾": 96, "cliffhanger": 96,
    "climax": 92, "高潮": 92,
    "hook": 88, "钩子": 88,
}

# 必保镜阈值：>= 此优先级的镜（钩子/爽点/反转/集尾）不可被砍。
MUST_KEEP_PRIORITY = 85.0
DEFAULT_PRIORITY = 50.0


def shot_id(clip):
    """n2d clip 的稳定标识：优先 镜头/id/label/clip_id/shot_id。"""
    return clip.get("镜头") or clip.get("id") or clip.get("label") \
        or clip.get("clip_id") or clip.get("shot_id")


def shot_priority(clip):
    """按 cutdown_priority（显式覆盖）> rhythm 张力词 > 钩子字段 > 默认，取最大者。纯函数。"""
    if "cutdown_priority" in clip:
        try:
            return float(clip["cutdown_priority"])
        except (TypeError, ValueError):
            pass
    best = DEFAULT_PRIORITY
    matched = False
    rhythm = str(clip.get("rhythm") or "")
    for key, pri in RHYTHM_PRIORITY:
        if key in rhythm:
            best = max(best, pri) if matched else pri
            matched = True
            break  # 取第一个命中的张力词（词表已按强弱排序）
    hook = str(clip.get("钩子") or clip.get("hook") or "").strip().lower()
    for key, pri in HOOK_FIELD_PRIORITY.items():
        if key.lower() in hook and hook:
            best = max(best, pri)
            break
    return best


def parse_seconds(label):
    """'15s' / '15' / '1:30' / ' 6 S ' → float 秒。"""
    s = str(label).strip().lower().replace("s", "").strip()
    if ":" in s:
        m, sec = s.split(":", 1)
        return int(m.strip()) * 60 + float(sec.strip())
    return float(s)


def safe_label(label):
    return str(label).strip().lower().replace(" ", "").replace(":", "x") or "var"


def duration_map_from_finalize(finalize_json):
    """`脚本/<集>/镜头时长.json` → {clip_key: 秒}（仅取 >0）。

    n2d 里 finalize_storyboard 把它写成 **字典** `{镜头/clip_key: 秒}`（配音先行=镜头键，
    原生音画=clip id 键）。同时容忍参照实现的列表 schema（`{shots:[{shot_id,duration}]}` / `[..]`），
    向后兼容也好测。"""
    if not finalize_json:
        return {}
    out = {}
    if isinstance(finalize_json, dict) and "shots" in finalize_json \
            and isinstance(finalize_json["shots"], list):
        finalize_json = finalize_json["shots"]
    if isinstance(finalize_json, dict):
        for key, raw in finalize_json.items():
            try:
                d = float(raw)
            except (TypeError, ValueError):
                continue
            if d > 0:
                out[str(key)] = d
        return out
    # 列表 schema
    for sh in finalize_json or []:
        if not isinstance(sh, dict):
            continue
        sid = sh.get("镜头") or sh.get("shot_id") or sh.get("id") or sh.get("clip_id")
        try:
            d = float(sh.get("duration", sh.get("时长", 0)) or 0)
        except (TypeError, ValueError):
            d = 0.0
        if sid is not None and d > 0:
            out[str(sid)] = d
    return out


def resolve_durations(clips, duration_map):
    """逐镜解析时长：优先用权威 duration_map（镜头时长.json），回退 storyboard 自带 duration。
    返回 [(idx, clip, dur_or_None)]。dur 为 None = 该镜时长不可解析（缺/0/非数）。纯函数。"""
    out = []
    for i, cl in enumerate(clips):
        sid = shot_id(cl)
        dur = None
        if sid is not None and str(sid) in duration_map:
            dur = duration_map[str(sid)]
        else:
            raw = cl.get("duration", cl.get("时长", cl.get("duration_sec")))
            try:
                d = float(raw) if raw is not None else 0.0
            except (TypeError, ValueError):
                d = 0.0
            dur = d if d > 0 else None
        out.append((i, cl, dur))
    return out


def plan_cutdown(clips, target_seconds, tol=0.6, duration_map=None):
    """按 rhythm/钩子 优先级选镜重剪到 ≈目标时长。返回 (kept, total, findings)。纯函数。

    算法（同重剪骨架，词表换 n2d 漫剧语境）：
      1. 用权威 `镜头时长.json`（duration_map）作时长源；缺则回退 storyboard duration。
      2. 必保镜（priority>=MUST_KEEP：钩子/爽点/反转/集尾）**先**进 chosen 并累计预算，
         再用剩余预算贪心补可选镜（铺垫/留白/细节…）。
      3. 任一必保镜时长不可解析 → block，返回空 kept（拒绝出计划，防 0s 假通过）。
      4. 必保镜单独已超 target+tol → overflow 提示（缩单镜/加速），仍保留全部必保镜。
    保序输出（按原 storyboard 顺序，保叙事连贯）。"""
    duration_map = duration_map or {}
    indexed = resolve_durations(clips, duration_map)
    findings = []

    must = [(i, cl, d) for (i, cl, d) in indexed if shot_priority(cl) >= MUST_KEEP_PRIORITY]
    optional = [(i, cl, d) for (i, cl, d) in indexed if shot_priority(cl) < MUST_KEEP_PRIORITY]

    unresolved_must = [shot_id(cl) or f"#{i}" for (i, cl, d) in must if d is None]
    if unresolved_must:
        findings.append({
            "severity": "block", "kind": "cutdown_missing_duration",
            "msg": f"必保镜 {', '.join(str(x) for x in unresolved_must)} 时长无法解析"
                   f"（脚本/<集>/镜头时长.json 缺该镜或为 0）；拒绝出计划，"
                   f"请先跑 n2d-script finalize_storyboard.py 出实测/定稿时长",
        })
        return [], 0.0, findings

    chosen = set(i for (i, _, _) in must)
    total = sum(d for (_, _, d) in must)

    optional_ranked = sorted(optional, key=lambda x: (-shot_priority(x[1]), x[0]))
    for i, cl, d in optional_ranked:
        if d is None:
            findings.append({
                "severity": "warn", "kind": "cutdown_optional_no_duration",
                "msg": f"可选镜 {shot_id(cl) or '#%d' % i} 无定稿时长，已跳过（不计入 cutdown）",
            })
            continue
        if total + d <= target_seconds + tol:
            chosen.add(i)
            total += d

    kept = [clips[i] for i in sorted(chosen)]
    total = round(total, 3)

    must_total = round(sum(d for (_, _, d) in must), 3)
    if must_total > target_seconds + tol:
        findings.append({
            "severity": "warn", "kind": "cutdown_overflow",
            "msg": f"必保镜（钩子/爽点/反转/集尾）合计 {must_total:.2f}s 已超目标 {target_seconds:.0f}s"
                   f"（+{must_total - target_seconds:.2f}s）；需逐镜缩时长/加速/合并镜，不能再砍骨架",
        })
    elif total > target_seconds + tol:
        findings.append({
            "severity": "warn", "kind": "cutdown_overflow",
            "msg": f"选镜后 {total:.2f}s 超目标 {target_seconds:.0f}s，需再压可选镜或缩单镜时长",
        })
    if total < target_seconds - tol:
        findings.append({
            "severity": "warn", "kind": "cutdown_underflow",
            "msg": f"只凑到 {total:.2f}s < 目标 {target_seconds:.0f}s，可加镜或放慢节奏",
        })
    return kept, total, findings


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


# ── 渲染（需要 ffmpeg；纯计算逻辑见上，渲染只做 I/O） ──────────────────────────

def _ffmpeg():
    return shutil.which("ffmpeg")


def _clip_path_for_shot(clip_dir, sid, index):
    """按 shot_id 或序号在 clip_dir 找对应 clip。约定：clip 文件名含 clip id（如 EP01_CLIP01_xxx.mp4），
    否则按排序序号回退。返回路径或 None。"""
    if not os.path.isdir(clip_dir):
        return None
    files = sorted(f for f in os.listdir(clip_dir) if f.lower().endswith(".mp4"))
    if sid:
        for f in files:
            stem = os.path.splitext(f)[0]
            if stem == str(sid) or str(sid) in stem:
                return os.path.join(clip_dir, f)
    if 0 <= index < len(files):
        return os.path.join(clip_dir, files[index])
    return None


def _aspect_size(aspect, out_long=1920):
    a, _, b = aspect.replace("x", ":").partition(":")
    try:
        av = float(a) / float(b)
    except (ValueError, ZeroDivisionError):
        av = 9 / 16  # n2d 默认竖屏
    if av >= 1:
        ow, oh = out_long, round(out_long / av)
    else:
        oh, ow = out_long, round(out_long * av)
    return ow - ow % 2, oh - oh % 2


def render_cutdown(root, ep, kept, target_label, out_path=None, aspect="9:16"):
    """按 kept 计划，从 出视频/<集>/视频/ 取对应 clip，filter-concat 归一拼接，产出 MP4。
    返回 (ok, msg, out_path)。无 ffmpeg → (False, 提示, None)。"""
    ff = _ffmpeg()
    if not ff:
        return False, "无 ffmpeg：跳过渲染（计划已出，可在带 ffmpeg 的机器上 --render）", None
    clip_dir = os.path.join(root, "出视频", ep, "视频")
    out_path = out_path or os.path.join(root, "合成", "交付", ep, f"成片_{safe_label(target_label)}.mp4")
    work = os.path.join(root, "合成", "交付", ep, "_work")
    os.makedirs(work, exist_ok=True)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    inputs = []
    missing = []
    for idx, cl in enumerate(kept):
        sid = shot_id(cl)
        p = _clip_path_for_shot(clip_dir, sid, idx)
        if p is None:
            missing.append(sid or f"#{idx}")
        else:
            inputs.append(p)
    if missing:
        return False, f"缺 clip：{', '.join(str(m) for m in missing)}（出视频/{ep}/视频/ 内未找到对应文件）", None
    if not inputs:
        return False, "无可拼接 clip", None

    ow, oh = _aspect_size(aspect)
    args = [ff, "-y", "-loglevel", "error"]
    for p in inputs:
        args += ["-i", p]
    n = len(inputs)
    pre = []
    for k in range(n):
        pre.append(f"[{k}:v]scale={ow}:{oh}:force_original_aspect_ratio=decrease,"
                   f"pad={ow}:{oh}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=30[v{k}]")
    concat_in = "".join(f"[v{k}]" for k in range(n))
    fc = ";".join(pre) + f";{concat_in}concat=n={n}:v=1:a=0[outv]"
    args += ["-filter_complex", fc, "-map", "[outv]",
             "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
             out_path]
    rc = subprocess.run(args, capture_output=True, text=True)
    if rc.returncode != 0:
        return False, f"cutdown 渲染失败：{rc.stderr[-600:]}", None
    return True, f"cutdown 成片：{out_path}", out_path


def main():
    ap = argparse.ArgumentParser(description="n2d 多时长 cutdown 重剪规划 + 渲染")
    ap.add_argument("project_root")
    ap.add_argument("episode", help="第N集")
    ap.add_argument("--target", required=True, help="目标时长，如 15s / 30s / 1:30")
    ap.add_argument("--json", default=None)
    ap.add_argument("--render", action="store_true", help="按计划实际拼接产出 MP4（需 ffmpeg）")
    ap.add_argument("--aspect", default="9:16", help="渲染输出比例（归一画幅，默认竖屏 9:16）")
    ap.add_argument("--out", default=None, help="渲染输出 MP4 路径（默认 合成/交付/<集>/成片_<dur>.mp4）")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    ep = args.episode
    sb = load_json(os.path.join(root, "脚本", ep, "storyboard.json"), {}) or {}
    clips = sb.get("clips") or sb.get("shots") or []
    finalize = load_json(os.path.join(root, "脚本", ep, "镜头时长.json"), {})
    dmap = duration_map_from_finalize(finalize)
    target = parse_seconds(args.target)
    kept, total, findings = plan_cutdown(clips, target, duration_map=dmap)

    blocked = any(f["severity"] in ("block", "error") for f in findings)
    payload = {"schema_version": 1, "kind": "n2d_cutdown_plan", "episode": ep,
               "target_seconds": target, "total_seconds": total,
               "kept_shots": [shot_id(s) for s in kept],
               "blocked": blocked, "findings": findings}

    render_result = None
    if args.render and not blocked:
        ok, msg, outp = render_cutdown(root, ep, kept, args.target, args.out, args.aspect)
        render_result = {"ok": ok, "msg": msg, "out": outp}
        payload["render"] = render_result

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    if blocked:
        print(f"# cutdown {ep} {args.target}  🔴 拒绝出计划（时长源缺失）")
        for fnd in findings:
            print(("🔴" if fnd["severity"] in ("block", "error") else "🟡") + " " + fnd["msg"])
        sys.exit(1)

    print(f"# cutdown {ep} {args.target}  保留 {len(kept)} 镜  预计 {total:.2f}s")
    print("  保留：" + ", ".join(str(x) for x in payload["kept_shots"]))
    for fnd in findings:
        print(("🔴" if fnd["severity"] in ("block", "error") else "🟡") + " " + fnd["msg"])
    if render_result:
        print(("[ok] " if render_result["ok"] else "[skip] ") + render_result["msg"])
    sys.exit(0)


if __name__ == "__main__":
    main()
