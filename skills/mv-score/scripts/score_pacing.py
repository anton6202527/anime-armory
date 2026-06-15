#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mv-score 的**确定性卡点前奏**——在调用生图/生视频烧积分前先机算节奏指标。

把"副歌快切爆发 / 主歌长镜叙事 / clip 不等长 / 总时长≈歌长 / 切点踩鼓点"这几条
MV 节奏铁律变成可量化的数字，喂给后续 LLM 语义评分，避免 LLM 凭感觉打卡点分。
与 mv-review/scripts/mv_check.py 共用同一引擎 mv-craft/scripts/pacing.py（单一真相源）。

读 分镜/clip_plan.json + 节拍/beatgrid.json + 歌长（找得到成品歌则量真长，否则用 beatgrid.duration），
输出机器预评分 JSON（四个指标 + 一个 0-10 的 pacing_score 供 LLM 参考，不替代 LLM 终判）。

用法：
    python3 score_pacing.py <制MV作品根> [--json]
退出码：clip_plan/beatgrid 缺失或损坏 → 2；否则 0（机检前奏不阻断，只供 LLM 判读）。
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


def build_payload(root):
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
    return {
        "schema_version": 1,
        "kind": "mv_pacing_prescore",
        "project_root": root,
        "song_len": round(song_len, 3) if song_len else None,
        "song_len_source": song_src,
        "engine": "mv-craft/scripts/pacing.py",
        "metrics": report,
        "pacing_score": score,
        "pacing_notes": notes,
        "note": "机器先验，喂给 mv-score 的 LLM 语义评分作卡点/节奏维度依据，不替代 LLM 终判。",
    }


def main():
    ap = argparse.ArgumentParser(description="mv-score 确定性卡点前奏（机器预评分）")
    ap.add_argument("root", help="制MV/<曲名>/ 作品根")
    ap.add_argument("--json", action="store_true", help="只打印机器预评分 JSON")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)
    payload = build_payload(root)
    out_dir = os.path.join(root, "评分")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "pacing_prescore.json")
    mv_utils.write_json(out, payload)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
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
    print(f"机器预评分 pacing_score = {payload['pacing_score']}/10")
    for n in payload["pacing_notes"]:
        print(f"  · {n}")
    print(f"\n→ {out}")
    print("（这是机器先验；交给 mv-score 的 LLM 在卡点/节奏维度上作量化依据，不替代语义终判）")


if __name__ == "__main__":
    main()
