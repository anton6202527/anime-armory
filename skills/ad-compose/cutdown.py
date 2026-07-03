#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多时长 cutdown 重剪规划 + 渲染：从主片 storyboard 选镜，剪成更短交付件（30s→15s→6s）。

广告 cutdown 不是机械截断，而是按镜头优先级保留"钩子 + 产品 + CTA"骨架，砍铺垫。
本脚本按每镜 `cutdown_priority`（或 section 默认权重）选镜：必保镜（priority>=85）先入，
其余按优先级补到剩余预算，凑到目标时长 ±容差，出 cutdown 计划 JSON（哪些镜留、预计时长）。

**镜头时长来源是 `脚本/镜头时长.json`（分镜定稿闸门产物）**，而非 storyboard 里可能为 0
的占位 duration——骨架 storyboard 的 0s 时长会误判成 0.00s「通过」。任一保留镜时长解析
不出来 → 出 block 错误，拒绝出计划。

`--render` 模式：按计划 trim/concat 主片对应片段、再追加 end card，产出实际 MP4
（需要 ffmpeg；无 ffmpeg 时只出计划）。自包含纯标准库 + 单测。

用法：
    python3 cutdown.py <作品根> --target 15s --json 合成/cutdown/plan_15s.json
    python3 cutdown.py <作品根> --target 15s --render            # 实际产出 MP4
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

# section 默认保留优先级（数字越大越先保留）。CTA/产品/钩子是 cutdown 骨架。
SECTION_PRIORITY = {
    "CTA": 100, "品牌包装": 100, "endcard": 100,
    "产品": 90, "方案": 88, "hero": 90,
    "钩子": 85,
    "证据": 60, "记忆点": 60,
    "痛点": 40, "情境": 38,
}

# 必保镜阈值：>= 此优先级的镜（钩子/产品/CTA）不可被砍。
MUST_KEEP_PRIORITY = 85.0


def shot_priority(shot):
    if "cutdown_priority" in shot:
        return float(shot["cutdown_priority"])
    section = str(shot.get("section", ""))
    for key, pri in SECTION_PRIORITY.items():
        if key in section:
            return pri
    return 50.0


def parse_seconds(label):
    """'30s' / '15' / '1:30' / ' 6 S ' → float 秒。"""
    s = str(label).strip().lower().replace("s", "").strip()
    if ":" in s:
        m, sec = s.split(":", 1)
        return int(m.strip()) * 60 + float(sec.strip())
    return float(s)


def shot_id(shot):
    return shot.get("shot_id") or shot.get("clip_id")


def resolve_durations(shots, duration_map):
    """逐镜解析时长：优先用权威 duration_map（镜头时长.json，shot_id→秒），
    回退 storyboard 自带 duration/时长。返回 [(idx, shot, dur_or_None)]。
    dur 为 None 表示该镜时长不可解析（缺/0/非数）。"""
    out = []
    for i, sh in enumerate(shots):
        sid = shot_id(sh)
        dur = None
        if sid is not None and sid in duration_map:
            dur = duration_map[sid]
        else:
            raw = sh.get("duration", sh.get("时长"))
            try:
                d = float(raw) if raw is not None else 0.0
            except (TypeError, ValueError):
                d = 0.0
            dur = d if d > 0 else None
        out.append((i, sh, dur))
    return out


def plan_cutdown(shots, target_seconds, tol=0.6, duration_map=None):
    """按优先级选镜重剪到 ≈目标时长。返回 (kept, total, findings)。

    算法（修复贪心不健全 + 0s 假通过）：
      1. 用权威 `镜头时长.json`（duration_map）作为时长源；缺则回退 storyboard duration。
      2. 必保镜（priority>=MUST_KEEP）**先**进 chosen 并累计预算，再用剩余预算贪心补可选镜。
      3. 任一保留镜时长不可解析 → block 错误，返回空 kept（拒绝出计划）。
      4. 必保镜单独已超 target+tol → overflow 提示（缩单镜/加速），仍保留全部必保镜。
    保序输出（按原 storyboard 顺序）。"""
    duration_map = duration_map or {}
    indexed = resolve_durations(shots, duration_map)
    findings = []

    # 必保 / 可选 分组
    must = [(i, sh, d) for (i, sh, d) in indexed if shot_priority(sh) >= MUST_KEEP_PRIORITY]
    optional = [(i, sh, d) for (i, sh, d) in indexed if shot_priority(sh) < MUST_KEEP_PRIORITY]

    # 时长不可解析 → block。先查必保镜（必进），再查"会被纳入"的可选镜在补镜时单独处理。
    unresolved_must = [shot_id(sh) or f"#{i}" for (i, sh, d) in must if d is None]
    if unresolved_must:
        findings.append({
            "severity": "block", "kind": "cutdown_missing_duration",
            "msg": f"必保镜 {', '.join(str(x) for x in unresolved_must)} 时长无法解析"
                   f"（脚本/镜头时长.json 缺该镜或为 0）；拒绝出计划，请先跑 finalize_storyboard.py 出实测时长",
        })
        return [], 0.0, findings

    # 1) 必保镜先入并累计
    chosen = set(i for (i, _, _) in must)
    total = sum(d for (_, _, d) in must)

    # 2) 剩余预算按优先级降序补可选镜（保序由最终输出保证）
    optional_ranked = sorted(optional, key=lambda x: (-shot_priority(x[1]), x[0]))
    for i, sh, d in optional_ranked:
        if d is None:
            # 可选镜时长缺失：跳过它（不纳入），并提示——而非误算 0
            findings.append({
                "severity": "warn", "kind": "cutdown_optional_no_duration",
                "msg": f"可选镜 {shot_id(sh) or '#%d' % i} 无实测时长，已跳过（不计入 cutdown）",
            })
            continue
        if total + d <= target_seconds + tol:
            chosen.add(i)
            total += d

    kept = [shots[i] for i in sorted(chosen)]
    total = round(total, 3)

    must_total = round(sum(d for (_, _, d) in must), 3)
    if must_total > target_seconds + tol:
        findings.append({
            "severity": "warn", "kind": "cutdown_overflow",
            "msg": f"必保镜（钩子/产品/CTA）合计 {must_total:.2f}s 已超目标 {target_seconds:.0f}s"
                   f"（+{must_total - target_seconds:.2f}s），需逐镜缩时长 / 加速 / 合并镜，不能再砍骨架",
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
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def duration_map_from_finalize(finalize_json):
    """镜头时长.json（{shots:[{shot_id,duration}]} 或 [..]）→ {shot_id: 秒}（仅取 >0）。"""
    if not finalize_json:
        return {}
    shots = finalize_json.get("shots") if isinstance(finalize_json, dict) else finalize_json
    out = {}
    for sh in shots or []:
        sid = sh.get("shot_id") or sh.get("clip_id")
        try:
            d = float(sh.get("duration", sh.get("时长", 0)) or 0)
        except (TypeError, ValueError):
            d = 0.0
        if sid is not None and d > 0:
            out[sid] = d
    return out


def safe_label(label):
    return str(label).strip().lower().replace(" ", "").replace(":", "x") or "var"


# ── 渲染（需要 ffmpeg；纯计算逻辑见上，渲染只做 I/O） ──────────────────────────

def _ffmpeg():
    return shutil.which("ffmpeg")


def _clip_path_for_shot(clip_dir, sid, index):
    """按 shot_id 或序号在 clip_dir 找对应 clip。返回路径或 None。
    约定：clip 文件名含 shot_id（如 S1.mp4 / 镜头_S1_xxx.mp4），否则按排序序号回退。"""
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


def render_cutdown(root, kept, total, target_label, out_path=None, aspect="16:9"):
    """按 kept 计划，从 出视频/分镜/视频/ 取对应 clip，filter-concat 归一拼接，
    再追加 end card（若 合成/_work/endcard.png 存在），产出 MP4。
    返回 (ok, msg, out_path)。无 ffmpeg → (False, 提示, None)。"""
    ff = _ffmpeg()
    if not ff:
        return False, "无 ffmpeg：跳过渲染（计划已出，可在带 ffmpeg 的机器上 --render）", None
    clip_dir = os.path.join(root, "出视频", "分镜", "视频")
    out_path = out_path or os.path.join(root, "合成", "cutdown", f"成片_{safe_label(target_label)}.mp4")
    work = os.path.join(root, "合成", "cutdown", "_work")
    os.makedirs(work, exist_ok=True)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    inputs = []
    missing = []
    for idx, sh in enumerate(kept):
        sid = shot_id(sh)
        # kept 的 idx 不是原 storyboard idx；按 shot_id 优先匹配
        p = _clip_path_for_shot(clip_dir, sid, idx)
        if p is None:
            missing.append(sid or f"#{idx}")
        else:
            inputs.append(p)
    if missing:
        return False, f"缺 clip：{', '.join(str(m) for m in missing)}（出视频/分镜/视频/ 内未找到对应文件）", None
    if not inputs:
        return False, "无可拼接 clip", None

    endcard = os.path.join(root, "合成", "_work", "endcard.png")
    endcard_mp4 = None
    if os.path.isfile(endcard):
        endcard_mp4 = os.path.join(work, "_endcard.mp4")
        ow, oh = _aspect_size(aspect)
        rc = subprocess.run([ff, "-y", "-loop", "1", "-t", "2.5", "-i", endcard,
                             "-vf", f"scale={ow}:{oh}:force_original_aspect_ratio=decrease,"
                                    f"pad={ow}:{oh}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=30",
                             "-c:v", "libx264", "-pix_fmt", "yuv420p", endcard_mp4],
                            capture_output=True, text=True)
        if rc.returncode != 0:
            return False, f"end card 转视频失败：{rc.stderr[-400:]}", None
        inputs.append(endcard_mp4)

    # 异构 clip 用 filter-concat 归一（scale/fps/setsar），不用 -c copy（会静默产出损坏）
    ow, oh = _aspect_size(aspect)
    args = [ff, "-y"]
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
             "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path]
    rc = subprocess.run(args, capture_output=True, text=True)
    if rc.returncode != 0:
        return False, f"cutdown 渲染失败：{rc.stderr[-600:]}", None
    return True, f"cutdown 成片：{out_path}", out_path


def _aspect_size(aspect, out_long=1920):
    a, _, b = aspect.replace("x", ":").partition(":")
    try:
        av = float(a) / float(b)
    except (ValueError, ZeroDivisionError):
        av = 16 / 9
    if av >= 1:
        ow, oh = out_long, round(out_long / av)
    else:
        oh, ow = out_long, round(out_long * av)
    return ow - ow % 2, oh - oh % 2


def main():
    ap = argparse.ArgumentParser(description="多时长 cutdown 重剪规划 + 渲染")
    ap.add_argument("project_root")
    ap.add_argument("--target", required=True, help="目标时长，如 15s / 6s / 1:30")
    ap.add_argument("--json", default=None)
    ap.add_argument("--render", action="store_true", help="按计划实际拼接产出 MP4（需 ffmpeg）")
    ap.add_argument("--aspect", default="16:9", help="渲染输出比例（end card / 归一画幅）")
    ap.add_argument("--out", default=None, help="渲染输出 MP4 路径（默认 合成/cutdown/成片_<dur>.mp4）")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    sb = load_json(os.path.join(root, "脚本", "storyboard.json"), {}) or {}
    shots = sb.get("shots") or sb.get("clips") or []
    finalize = load_json(os.path.join(root, "脚本", "镜头时长.json"), {})
    dmap = duration_map_from_finalize(finalize)
    target = parse_seconds(args.target)
    kept, total, findings = plan_cutdown(shots, target, duration_map=dmap)

    blocked = any(f["severity"] in ("block", "error") for f in findings)
    payload = {"schema_version": 1, "kind": "ad_cutdown_plan", "target_seconds": target,
               "total_seconds": total,
               "kept_shots": [shot_id(s) for s in kept],
               "blocked": blocked,
               "findings": findings}

    render_result = None
    if args.render and not blocked:
        ok, msg, outp = render_cutdown(root, kept, total, args.target, args.out, args.aspect)
        render_result = {"ok": ok, "msg": msg, "out": outp}
        payload["render"] = render_result

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    if blocked:
        print(f"# cutdown {args.target}  🔴 拒绝出计划（时长源缺失）")
        for fnd in findings:
            print(("🔴" if fnd["severity"] in ("block", "error") else "🟡") + " " + fnd["msg"])
        sys.exit(1)

    print(f"# cutdown {args.target}  保留 {len(kept)} 镜  预计 {total:.2f}s")
    print("  保留：" + ", ".join(str(x) for x in payload["kept_shots"]))
    for fnd in findings:
        print(("🔴" if fnd["severity"] in ("block", "error") else "🟡") + " " + fnd["msg"])
    if render_result:
        print(("[ok] " if render_result["ok"] else "[skip] ") + render_result["msg"])
    elif args.render and blocked:
        print("[skip] 计划被阻断，未渲染")
    sys.exit(0)


if __name__ == "__main__":
    main()
