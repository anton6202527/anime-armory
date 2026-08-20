#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多时长 cutdown 重剪规划 + 渲染：从主片 storyboard 选镜，剪成更短交付件（30s→15s→6s）。

广告 cutdown 不是机械截断，而是按镜头优先级保留"钩子 + 产品 + CTA"骨架，砍铺垫。
本脚本按每镜 `cutdown_priority`（或 section 默认权重）选镜：必保镜（priority>=85）先入，
其余按优先级补到剩余预算，凑到目标时长 ±容差，出 cutdown 计划 JSON（哪些镜留、预计时长）。

**镜头时长来源是 `脚本/镜头时长.json`（分镜定稿闸门产物）**，而非 storyboard 里可能为 0
的占位 duration——骨架 storyboard 的 0s 时长会误判成 0.00s「通过」。任一保留镜时长解析
不出来 → 出 block 错误，拒绝出计划。

`--render` 模式：按计划从已完成混音/字幕/包装的主片 trim/concat，产出实际 MP4
（保留完整音轨且不重复追加 end card；需要 ffmpeg，无 ffmpeg 时只出计划）。自包含纯标准库 + 单测。

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


def shot_claim_ids(shot):
    raw = shot.get("claim_ids") or []
    if isinstance(raw, str):
        raw = [raw]
    return {str(v).strip() for v in raw if str(v).strip()}


def disclosure_claim_ids(shot):
    raw = shot.get("disclosures") or []
    if isinstance(raw, dict):
        raw = [raw]
    return {
        str(row.get("claim_id") or "").strip()
        for row in raw if isinstance(row, dict) and str(row.get("claim_id") or "").strip()
    }


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

    # 3) claim 与披露是原子交付：保留宣称镜却砍掉来源/适用条件/免责，会把合规主片
    # 机械剪成误导性 cutdown。按 claim_id 自动补回最近的披露镜；不存在或无时长则 block。
    duration_by_index = {i: d for i, _, d in indexed}
    disclosure_candidates = {}
    for i, sh, _ in indexed:
        for cid in disclosure_claim_ids(sh):
            disclosure_candidates.setdefault(cid, []).append(i)
    changed = True
    while changed:
        changed = False
        selected_claims = set().union(*(shot_claim_ids(shots[i]) for i in chosen)) if chosen else set()
        selected_disclosures = set().union(*(disclosure_claim_ids(shots[i]) for i in chosen)) if chosen else set()
        for cid in sorted(selected_claims - selected_disclosures):
            candidates = disclosure_candidates.get(cid) or []
            if not candidates:
                findings.append({
                    "severity": "block", "kind": "cutdown_claim_disclosure_missing",
                    "msg": f"cutdown 保留了 claim {cid}，但主分镜没有对应 disclosures[].claim_id；不得输出无披露版本",
                })
                continue
            # 选距任一已选宣称镜最近的一镜；同屏披露自然距离为 0。
            claim_positions = [i for i in chosen if cid in shot_claim_ids(shots[i])]
            pick = min(candidates, key=lambda i: min(abs(i - p) for p in claim_positions))
            if duration_by_index.get(pick) is None:
                findings.append({
                    "severity": "block", "kind": "cutdown_disclosure_duration_missing",
                    "msg": f"claim {cid} 的披露镜 {shot_id(shots[pick]) or '#%d' % pick} 缺权威时长；无法安全重剪",
                })
                continue
            if pick not in chosen:
                chosen.add(pick)
                changed = True

    kept = [shots[i] for i in sorted(chosen)]
    total = round(sum(duration_by_index[i] or 0 for i in chosen), 3)
    if any(f["severity"] == "block" for f in findings):
        return kept, total, findings

    if total > target_seconds + tol and any(disclosure_claim_ids(shots[i]) for i in chosen):
        findings.append({
            "severity": "warn", "kind": "cutdown_claim_bundle_overflow",
            "msg": f"补回 claim 披露后 cutdown={total:.2f}s，超过目标 {target_seconds:.0f}s；需重写宣称/披露或压缩其它镜，不能删披露",
        })

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
    """从已完成主片按镜头时间段重剪，保留其 VO/音乐/字幕/法律文字。"""
    ff = _ffmpeg()
    if not ff:
        return False, "无 ffmpeg：跳过渲染（计划已出，可在带 ffmpeg 的机器上 --render）", None
    master = os.path.join(root, "合成", "成片_主片.mp4")
    if not os.path.isfile(master):
        return False, "缺 合成/成片_主片.mp4；cutdown 必须从已混音/字幕/响度归一主片重剪", None
    out_path = out_path or os.path.join(root, "合成", "cutdown", f"成片_{safe_label(target_label)}.mp4")
    work = os.path.join(root, "合成", "cutdown", "_work")
    os.makedirs(work, exist_ok=True)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    sb = load_json(os.path.join(root, "脚本", "storyboard.json"), {}) or {}
    all_shots = sb.get("shots") or sb.get("clips") or []
    dmap = duration_map_from_finalize(load_json(os.path.join(root, "脚本", "镜头时长.json"), {}) or {})
    spans = {}
    cursor = 0.0
    for _, sh, dur in resolve_durations(all_shots, dmap):
        if dur is None:
            return False, f"镜头 {shot_id(sh)} 缺权威时长，无法从主片精确重剪音画", None
        spans[str(shot_id(sh))] = (cursor, cursor + dur)
        cursor += dur
    chosen_spans = [spans.get(str(shot_id(sh))) for sh in kept]
    if not chosen_spans or any(x is None for x in chosen_spans):
        return False, "cutdown 选镜无法映射到主片时间段", None

    probe = subprocess.run([shutil.which("ffprobe") or "ffprobe", "-v", "error", "-select_streams", "a",
                            "-show_entries", "stream=index", "-of", "csv=p=0", master],
                           capture_output=True, text=True)
    has_audio = probe.returncode == 0 and bool(probe.stdout.strip())
    render_profile = load_json(os.path.join(root, "生产数据", "render_profile.json"), {}) or {}
    master_profile = render_profile.get("master_render") if isinstance(render_profile.get("master_render"), dict) else {}
    if not master_profile.get("width") or not master_profile.get("height") or not master_profile.get("fps"):
        return False, "缺统一 生产数据/render_profile.json；先重建交付计划/主片，不能用隐含 1920x1080@30 默认值", None
    profile_aspect = str(master_profile.get("aspect") or "")
    if profile_aspect and profile_aspect != aspect:
        return False, f"cutdown 比例 {aspect} 与 render_profile 母版比例 {profile_aspect} 不一致；跨比例请先走 placement adaptation，再按获准模式制作", None
    ow, oh = int(master_profile["width"]), int(master_profile["height"])
    fps = float(master_profile["fps"])
    args = [ff, "-y", "-i", master]
    n = len(chosen_spans)
    pre = []
    for k, (start, end) in enumerate(chosen_spans):
        pre.append(f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS,"
                   f"scale={ow}:{oh}:force_original_aspect_ratio=decrease,"
                   f"pad={ow}:{oh}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps={fps:g}[v{k}]")
        if has_audio:
            pre.append(f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{k}]")
    concat_in = "".join(f"[v{k}]" for k in range(n))
    if has_audio:
        concat_in = "".join(f"[v{k}][a{k}]" for k in range(n))
        fc = ";".join(pre) + f";{concat_in}concat=n={n}:v=1:a=1[outv][outa]"
        args += ["-filter_complex", fc, "-map", "[outv]", "-map", "[outa]",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p",
                 "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
                 "-c:a", "aac", "-ar", "48000", out_path]
    else:
        fc = ";".join(pre) + f";{concat_in}concat=n={n}:v=1:a=0[outv]"
        args += ["-filter_complex", fc, "-map", "[outv]",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p",
                 "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv", out_path]
    rc = subprocess.run(args, capture_output=True, text=True)
    if rc.returncode != 0:
        return False, f"cutdown 渲染失败：{rc.stderr[-600:]}", None
    return True, f"cutdown 成片：{out_path}", out_path


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
    sys.exit(1 if args.render and render_result and not render_result["ok"] else 0)


if __name__ == "__main__":
    main()
