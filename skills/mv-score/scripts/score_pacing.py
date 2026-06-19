#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mv-score 的**确定性卡点前奏**——在调用生图/生视频烧积分前先机算节奏指标。

把"副歌快切爆发 / 主歌长镜叙事 / clip 不等长 / 总时长≈歌长 / 切点踩鼓点"这几条
MV 节奏铁律变成可量化的数字，喂给后续 LLM 语义评分，避免 LLM 凭感觉打卡点分。
与 mv-review/scripts/mv_check.py 共用同一引擎 mv-craft/scripts/pacing.py（单一真相源）。

读 分镜/clip_plan.json + 节拍/beatgrid.json + 歌长（找得到成品歌则量真长，否则用 beatgrid.duration），
输出机器预评分 JSON（四个指标 + 一个 0-10 的 pacing_score 供 LLM 参考 + 受影响 clip 回流清单）。

**pre-spend 真闸门**（借鉴 n2d-score 的 --threshold/--enqueue 闭环，但 mv 线自包含、判据全在本线内）：
给 --threshold 后，综合 pacing_score 或任一关键卡点维度低于阈值时 **exit 1**，在烧积分（出图/出视频）
前把平庸/不卡点的分镜挡下来，并打印「该退回哪个上游 stage」。同时产出 affected_clips 结构化清单
（clip_id + return_to_stage + reason），写进评分 JSON；可选 --enqueue 落一份 mv 自己的回流清单文件
（评分/回流清单.json，不引用 n2d-batch，人/工具皆可消费）。

受影响 clip → 源头 stage 映射（MV 专属）：
  - 卡点不准 / clip 边界偏离 downbeat / clip 时长偏离  → 回 mv-plan（重拆时长、对齐 beatgrid）
  - 视觉记忆点弱 / 蓝图问题（语义维度低）              → 回 mv-script（重梳视觉蓝图）
  - 崩脸 / 单曲视觉一致性差（语义维度低）              → 回 mv-image（重出图/锁身份）

用法：
    python3 score_pacing.py <制MV作品根> [--json] [--threshold <分>] [--enqueue]
                            [--dim 视觉记忆点=55 --dim 崩脸=40 ...]   # LLM 语义维度回灌（可选）
退出码：clip_plan/beatgrid 缺失或损坏 → 2；--threshold 下被拦截 → 1；否则 0。
"""
import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PACING_PATH = os.path.join(REPO, "skills", "mv-craft", "scripts", "pacing.py")
MV_UTILS_PATH = os.path.join(REPO, "skills", "mv-craft", "scripts", "mv_utils.py")


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pacing = _load_module("mv_pacing", PACING_PATH)
mv_utils = _load_module("mv_utils", MV_UTILS_PATH)


def resolve_song_len(root, beatgrid):
    """优先量真实歌长；找不到成品歌则退回 beatgrid.duration。"""
    song = mv_utils.find_song(root)
    if song:
        d = mv_utils.audio_duration(song)
        if d:
            return float(d), "measured"
    bd = beatgrid.get("duration")
    if isinstance(bd, (int, float)) and bd > 0:
        return float(bd), "beatgrid"
    return None, "none"


def pacing_score(report):
    """把四个指标折成一个 0-10 的参考分（LLM 仍是终判，这只是机器先验）。

    满分 10：等长不嫌疑 + 总时长对账过 + 切点高对齐 + 副歌密度≥主歌。
    任一指标因缺样本无法判（None）则该项不扣分、记 unknown。
    """
    score = 10.0
    notes = []
    eq = report["equal_length"]
    if eq["suspicious"]:
        score -= 3.0
        notes.append("clip 近等长，疑不卡点(-3)")
    dur = report["duration"]
    if dur["mismatch"]:
        score -= 2.0
        notes.append("规划总时长与歌长差大(-2)")
    align = report["downbeat_alignment"]
    if align["ratio"] is not None:
        if align["ratio"] < 0.5:
            score -= 2.0
            notes.append(f"切点踩鼓点率低({align['ratio']:.0%})(-2)")
        elif align["ratio"] < 0.75:
            score -= 1.0
            notes.append(f"切点踩鼓点率中等({align['ratio']:.0%})(-1)")
    dens = report["chorus_verse_density"]
    if dens["ok"] is False:
        score -= 2.0
        notes.append("副歌未比主歌快切(-2)")
    elif dens["ok"] is None:
        notes.append("副歌/主歌密度样本不足，未判")
    score = max(0.0, round(score, 2))
    return score, notes


# ---------------------------------------------------------------------------
# pre-spend 闸门：纯函数（无 IO、无副作用、可测）
# ---------------------------------------------------------------------------
# MV 专属：受影响 clip 的成因 → 该退回哪个上游 stage。
# 卡点/时长 → mv-plan（重拆时长、对齐 beatgrid）；蓝图/记忆点 → mv-script；视觉一致性/崩脸 → mv-image。
PACING_RETURN_STAGE = "mv-plan"
STAGE_BY_REASON = {
    "off_downbeat": "mv-plan",
    "duration_outlier": "mv-plan",
    "equal_length": "mv-plan",
}

# LLM 语义维度名（含同义词）→ 回流 stage。维度低分由 --dim 回灌进来，判据集中在此一处。
SEMANTIC_DIM_STAGE = {
    "mv-script": ("视觉记忆点", "visual hook", "visual_hook", "蓝图", "情感共鸣",
                  "emotional", "记忆点", "想象力", "action"),
    "mv-image": ("崩脸", "视觉一致性", "consistency", "换脸", "换画风",
                 "身份", "identity", "single-song", "single_song"),
}

# pacing_score(0-10) 与综合阈值(可能是 0-100 制)对齐：闸门按 0-100 口径判，pacing 折算成 *10。
PACING_SCORE_MAX = 10.0


def normalize_threshold(threshold):
    """阈值口径归一：用户可能传 0-10（贴 pacing_score）或 0-100（贴综合分）。
    >10 视为百分制，否则视为十分制并 *10 归到百分制，返回 0-100 阈值。"""
    if threshold is None:
        return None
    t = float(threshold)
    return t if t > 10 else t * 10.0


def pacing_score_pct(pacing_score):
    """把 0-10 的 pacing_score 折成 0-100，便于和综合阈值同口径比较。"""
    return round(float(pacing_score) / PACING_SCORE_MAX * 100.0, 2)


def map_semantic_dim_stage(dim_name):
    """LLM 语义维度名 → 回流 stage（mv-script / mv-image），命不中返回 None。"""
    hay = str(dim_name or "").lower()
    for stage, keys in SEMANTIC_DIM_STAGE.items():
        if any(str(k).lower() in hay for k in keys):
            return stage
    return None


def pacing_affected_clips(clip_plan, beatgrid, report):
    """从确定性 report 推出**该回 mv-plan 的具体 clip**（卡点不准 / 时长离群）。

    - off_downbeat：clip 起止边界没踩在任何 downbeat ±tol 内 → 该 clip 切点不卡。
    - duration_outlier：clip 时长偏离 clip 中位时长过多（>40%）→ 时长该重拆。
    每个命中 clip 产 {clip_id, return_to_stage, reason, detail}。纯函数，可测。
    """
    clips = (clip_plan or {}).get("clips") or []
    grid = sorted(
        float(t) for t in ((beatgrid or {}).get("downbeats") or (beatgrid or {}).get("beats") or [])
        if isinstance(t, (int, float))
    )
    tol = report.get("downbeat_alignment", {}).get("tol", 0.15)
    durs = [float(c.get("duration") or 0) for c in clips if isinstance(c.get("duration"), (int, float)) and float(c.get("duration") or 0) > 0]
    med = sorted(durs)[len(durs) // 2] if durs else None
    out = []
    for idx, c in enumerate(clips):
        cid = str(c.get("clip_id") or f"Clip_{idx + 1:03d}")
        reasons = []
        # 切点对齐：只在有 downbeat 网格、且 clip 有边界时判
        if grid:
            for key in ("start", "end"):
                v = c.get(key)
                if not isinstance(v, (int, float)):
                    continue
                if float(v) <= 0.01:
                    continue  # 整曲起点不算切点
                if min(abs(float(v) - g) for g in grid) > tol:
                    reasons.append(("off_downbeat", f"{key}={v} 未踩 downbeat(±{tol}s)"))
                    break
        # 时长离群：偏离中位 >40%
        if med and med > 0:
            d = float(c.get("duration") or 0)
            if d > 0 and abs(d - med) / med > 0.4:
                reasons.append(("duration_outlier", f"duration={d} 偏离中位 {med}s >40%"))
        for reason, detail in reasons:
            out.append({
                "clip_id": cid,
                "return_to_stage": STAGE_BY_REASON.get(reason, PACING_RETURN_STAGE),
                "reason": reason,
                "detail": detail,
            })
    return out


def semantic_affected_clips(low_dims, clip_ids=None):
    """LLM 回灌的低分语义维度 → 回流 clip 清单。

    low_dims: [{"dim": "视觉记忆点", "score": 55, "clips": ["Clip_003"]}...]（clips 可缺）。
    维度低分但没点名具体 clip 时，return_to_stage 仍给出、clip_id 记 "*"（整段重做）。
    纯函数，可测。
    """
    out = []
    for d in low_dims or []:
        if not isinstance(d, dict):
            continue
        name = d.get("dim") or d.get("name") or ""
        stage = map_semantic_dim_stage(name)
        if not stage:
            continue
        clips = d.get("clips") or clip_ids or ["*"]
        for cid in clips:
            out.append({
                "clip_id": str(cid),
                "return_to_stage": stage,
                "reason": "low_semantic_dim",
                "detail": f"{name} 维度低分（{d.get('score')}）",
            })
    return out


def low_semantic_dims(dim_scores, threshold_pct):
    """把 --dim 回灌的 {维度名: 分} 过滤出低于阈值(百分制)的，标准化为 affected 用的 list。"""
    out = []
    for name, score in (dim_scores or {}).items():
        try:
            s = float(score)
        except (TypeError, ValueError):
            continue
        if threshold_pct is not None and s < threshold_pct:
            out.append({"dim": name, "score": s})
    return out


def decide_block(pacing_score, report, low_dims, threshold):
    """是否 pre-spend 拦截 + 该回哪些 stage。纯函数。

    拦截条件（threshold 给定时任一成立）：
      - pacing_score 折百分制 < 阈值；
      - 任一关键卡点维度硬命门（疑等长不卡点 / 总时长差大 / 踩鼓点率 <0.5 / 副歌未比主歌快）；
      - 有低于阈值的 LLM 语义维度（视觉记忆点 / 崩脸 …）。
    返回 (blocked: bool, return_stages: sorted[str], reasons: list[str])。
    threshold=None → 永不拦截（blocked=False），保持旧"建议性"行为。
    """
    thr = normalize_threshold(threshold)
    reasons = []
    stages = set()
    if thr is None:
        return False, [], reasons
    if pacing_score_pct(pacing_score) < thr:
        reasons.append(f"pacing_score {pacing_score}/10 折算 {pacing_score_pct(pacing_score)} < 阈值 {thr}")
        stages.add(PACING_RETURN_STAGE)
    # 关键卡点维度的硬命门（与 pacing_score 扣分点同源，但独立触发回流）
    eq = report.get("equal_length", {})
    if eq.get("suspicious"):
        reasons.append("clip 近等长，疑不卡点")
        stages.add(PACING_RETURN_STAGE)
    if report.get("duration", {}).get("mismatch"):
        reasons.append("规划总时长与歌长差大")
        stages.add(PACING_RETURN_STAGE)
    al = report.get("downbeat_alignment", {})
    if al.get("ratio") is not None and al["ratio"] < 0.5:
        reasons.append(f"切点踩鼓点率低({al['ratio']})")
        stages.add(PACING_RETURN_STAGE)
    if report.get("chorus_verse_density", {}).get("ok") is False:
        reasons.append("副歌未比主歌快切")
        stages.add(PACING_RETURN_STAGE)
    for d in low_dims or []:
        stage = map_semantic_dim_stage(d.get("dim"))
        if stage:
            reasons.append(f"{d.get('dim')} 维度低分({d.get('score')})→ {stage}")
            stages.add(stage)
    return (len(reasons) > 0), sorted(stages), reasons


def build_payload(root, threshold=None, dim_scores=None):
    plan_path = os.path.join(root, "分镜", "clip_plan.json")
    bg_path = os.path.join(root, "节拍", "beatgrid.json")
    if not os.path.exists(plan_path):
        raise SystemExit(f"[err] 缺 分镜/clip_plan.json（先跑 mv-plan）：{plan_path}")
    if not os.path.exists(bg_path):
        raise SystemExit(f"[err] 缺 节拍/beatgrid.json（先跑 mv-beat）：{bg_path}")
    clip_plan = mv_utils.load_json(plan_path)
    beatgrid = mv_utils.load_json(bg_path)
    if not isinstance(clip_plan, dict) or not isinstance(beatgrid, dict):
        raise SystemExit("[err] clip_plan/beatgrid 解析失败（非 JSON 对象）")
    song_len, song_src = resolve_song_len(root, beatgrid)
    report = pacing.pacing_report(clip_plan, beatgrid, song_len)
    score, notes = pacing_score(report)

    thr_pct = normalize_threshold(threshold)
    low_dims = low_semantic_dims(dim_scores, thr_pct)
    blocked, return_stages, block_reasons = decide_block(score, report, low_dims, threshold)
    affected = pacing_affected_clips(clip_plan, beatgrid, report) + semantic_affected_clips(low_dims)

    return {
        "schema_version": 2,
        "kind": "mv_pacing_prescore",
        "project_root": root,
        "song_len": round(song_len, 3) if song_len else None,
        "song_len_source": song_src,
        "engine": "mv-craft/scripts/pacing.py",
        "metrics": report,
        "pacing_score": score,
        "pacing_score_pct": pacing_score_pct(score),
        "pacing_notes": notes,
        "threshold": threshold,
        "threshold_pct": thr_pct,
        "blocked": blocked,
        "return_to_stages": return_stages,
        "block_reasons": block_reasons,
        "affected_clips": affected,
        "note": "机器先验 + pre-spend 闸门：threshold 下 blocked=true 即在出图/出视频前拦截；"
                "affected_clips 标注每个 clip 该回哪个上游 stage（mv-plan/mv-script/mv-image）。",
    }


def write_enqueue(root, payload):
    """落一份 mv 自己的回流清单（不引用 n2d-batch）：按 stage 聚合受影响 clip，人/工具皆可消费。"""
    by_stage = {}
    for item in payload.get("affected_clips", []):
        stage = item["return_to_stage"]
        bucket = by_stage.setdefault(stage, {"return_to_stage": stage, "clips": [], "reasons": []})
        if item["clip_id"] not in [c["clip_id"] for c in bucket["clips"]]:
            bucket["clips"].append({"clip_id": item["clip_id"], "reason": item["reason"], "detail": item.get("detail", "")})
        if item["reason"] not in bucket["reasons"]:
            bucket["reasons"].append(item["reason"])
    queue = {
        "schema_version": 1,
        "kind": "mv_score_rework_queue",
        "project_root": root,
        "blocked": payload.get("blocked", False),
        "threshold": payload.get("threshold"),
        "block_reasons": payload.get("block_reasons", []),
        "tasks": sorted(by_stage.values(), key=lambda t: t["return_to_stage"]),
        "note": "mv-score pre-spend 闸门回流清单：每个 task 是一个上游 stage + 该重做的 clip 列表。"
                "mv 自有格式，不依赖 n2d-batch；按 return_to_stage 重跑对应 mv-* skill。",
    }
    out = os.path.join(root, "评分", "回流清单.json")
    mv_utils.write_json(out, queue)
    return out, queue


def _parse_dim(values):
    """--dim 视觉记忆点=55 → {"视觉记忆点": 55.0}（LLM 语义维度回灌，可选）。"""
    out = {}
    for v in values or []:
        if "=" not in v:
            continue
        name, _, score = v.partition("=")
        try:
            out[name.strip()] = float(score.strip())
        except ValueError:
            continue
    return out


def main():
    ap = argparse.ArgumentParser(description="mv-score 确定性卡点前奏 + pre-spend 真闸门")
    ap.add_argument("root", help="制MV/<曲名>/ 作品根")
    ap.add_argument("--json", action="store_true", help="只打印机器预评分 JSON")
    ap.add_argument("--threshold", type=float, default=None,
                    help="pre-spend 闸门阈值；综合/关键卡点维度低于此则 exit 1。"
                         "≤10 视为十分制（贴 pacing_score），>10 视为百分制（贴综合分）")
    ap.add_argument("--dim", action="append", default=[], metavar="维度名=分",
                    help="回灌 LLM 语义维度分（视觉记忆点/崩脸/视觉一致性…），可多次；低于阈值则触发回 mv-script/mv-image")
    ap.add_argument("--enqueue", action="store_true",
                    help="把受影响 clip 按 stage 聚合，落 评分/回流清单.json（mv 自有格式，不依赖 n2d-batch）")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)
    dim_scores = _parse_dim(args.dim)
    payload = build_payload(root, threshold=args.threshold, dim_scores=dim_scores)
    out_dir = os.path.join(root, "评分")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "pacing_prescore.json")
    mv_utils.write_json(out, payload)
    queue_out = None
    if args.enqueue:
        queue_out, _ = write_enqueue(root, payload)
    exit_code = 1 if payload.get("blocked") else 0
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        sys.exit(exit_code)
    m = payload["metrics"]
    print(f"\n=== mv-score 卡点前奏（机检）：{root} ===")
    print(f"歌长基准 {payload['song_len']}s（{payload['song_len_source']}） · clip {m['clip_count']} 个")
    eq = m["equal_length"]
    print(f"  等长检测   cv={eq['cv']} 阈值<{eq['threshold']} → {'疑等长不卡点' if eq['suspicious'] else 'ok'}")
    dur = m["duration"]
    print(f"  总时长对账 规划{dur['planned_total']}s vs 歌{dur['song_len']}s diff={dur['diff']} → {'差大' if dur['mismatch'] else 'ok'}")
    al = m["downbeat_alignment"]
    print(f"  踩鼓点率   {al['aligned']}/{al['boundaries']} 切点对齐 → {al['ratio'] if al['ratio'] is not None else '无样本'}")
    dn = m["chorus_verse_density"]
    print(f"  副歌vs主歌 密度对比={dn['contrast']}（副歌{dn['chorus_density']} / 主歌{dn['verse_density']}）→ {dn['ok']}")
    print(f"机器预评分 pacing_score = {payload['pacing_score']}/10（折算 {payload['pacing_score_pct']}/100）")
    for n in payload["pacing_notes"]:
        print(f"  · {n}")
    print(f"\n→ {out}")
    if payload.get("threshold") is not None:
        print(f"\n=== pre-spend 闸门（阈值 {payload['threshold']} → {payload['threshold_pct']}/100）===")
        if payload["blocked"]:
            print(f"  ❌ 拦截（exit 1）：在出图/出视频烧积分前挡下，请先回流：{ '、'.join(payload['return_to_stages']) }")
            for r in payload["block_reasons"]:
                print(f"     · {r}")
            if payload["affected_clips"]:
                print("  受影响 clip → 源头 stage：")
                for c in payload["affected_clips"][:20]:
                    print(f"     · {c['clip_id']} → {c['return_to_stage']}（{c['reason']}：{c['detail']}）")
        else:
            print("  ✅ 放行（exit 0）：未触发闸门，可推进出图/出视频。")
    else:
        print("（无 --threshold：机器先验/建议性，不阻断；交给 LLM 在卡点维度上作量化依据）")
    if queue_out:
        print(f"\n→ 回流清单：{queue_out}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
