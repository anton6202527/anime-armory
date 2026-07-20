#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mv-plan 打样探针矩阵（mini-pilot · report-only · 全量出图前最后一个免费决策点）。

MV 全曲 16-64 个 clip，一旦风格/脸/卡点体感有问题，全量出图后返工=整曲重烧积分。
本脚本在全量出图前，从 `分镜/clip_plan.json`（+ 可选的 drift_risk / shot_variety 报告）
挑 3-5 个**代表性 clip** 出打样计划：先只出这几个镜的首帧图（必要时短视频样），
人工确认「脸像不像、风格对不对、副歌爆点体感够不够」再全量（参照兄弟线 episode_probe_matrix）。

探针类别（每类至多一镜，开场镜保底）：
  opening_probe        开场镜——前 3 秒钩子，风格/身份第一印象；
  chorus_peak_probe    副歌/爽点 key 镜——全曲记忆点，运镜与энергия必须成立；
  identity_probe       漂移风险最高的镜（drift_risk high 优先；缺报告则近景+强情绪兜底）——脸最容易崩的地方先验证；
  motion_probe         运动幅度最大的镜——后端动作能力/首尾帧衔接先验证；
  state_change_probe   换装/换景首镜——重锚点，参考锚挂法先验证。

产物：`生产数据/pilot_matrix/pilot_matrix.{json,md}`，纯计划、不花钱、不自动出图。
gate 在 image 期对正式大盘（clip 多）只提示「建议先打样」，永不 block。
用法：python3 pilot_matrix.py <制MV作品根> [--limit N] [--write] [--json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from typing import Any
from datetime import date

VERSION = 1
KIND = "mv_pilot_matrix"

CHORUS_RE = re.compile(r"chorus|副歌|drop|hook|refrain|高潮|climax", re.IGNORECASE)
CLOSEUP_RE = re.compile(r"大?特写|近景|closeup|close-?up|\bE?CU\b|face|脸部|面部", re.IGNORECASE)
EMOTION_RE = re.compile(r"哭|泪|嘶吼|怒|吼|崩溃|狂喜|大笑|尖叫|颤抖|绝望|痛苦|挣扎|爆发|scream|cry|sob|rage", re.IGNORECASE)
DYNAMIC_CAM_RE = re.compile(r"甩|环绕|旋转|冲|穿越|跟拍|手持|变焦|zoom|whip|orbit|dolly|crash|fly|穿梭|升降", re.IGNORECASE)

DEFAULT_LIMIT = 5


def _sha256(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def _norm(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def _sd(clip: dict[str, Any]) -> dict[str, Any]:
    sd = clip.get("shot_design")
    return sd if isinstance(sd, dict) else {}


def _location_key(clip: dict[str, Any]) -> str:
    sd = _sd(clip)
    return _norm(sd.get("location_id") or sd.get("setup_group") or sd.get("location_name") or clip.get("section"))


def _identity_state(clip: dict[str, Any]) -> str:
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
    return _norm(cont.get("identity_state") or cont.get("wardrobe_state"))


def _is_chorusish(clip: dict[str, Any]) -> bool:
    if _norm(clip.get("beat_role")) == "key":
        return True
    return bool(CHORUS_RE.search(str(clip.get("section") or "")))


def _blob(clip: dict[str, Any]) -> str:
    parts = [str(clip.get(k) or "") for k in ("desc", "description", "action", "action_peak", "performance")]
    sd = _sd(clip)
    parts += [str(sd.get(k) or "") for k in ("shot_size", "angle", "camera_movement", "lens_feel")]
    return " ".join(p for p in parts if p)


def load_drift_tiers(root: str) -> dict[str, dict[str, Any]]:
    report = load_json(os.path.join(root, "生产数据", "drift_risk", "drift_risk.json"))
    if not isinstance(report, dict):
        return {}
    return {str(row.get("clip_id")): row for row in report.get("clips") or [] if isinstance(row, dict)}


PROBE_ACCEPTANCE = {
    "opening_probe": ["主角与蓝图身份锚一致", "风格/主色贴 global_style", "前 3 秒画面自身有钩"],
    "chorus_peak_probe": ["运镜有能量、非静帧", "构图可作全曲记忆点", "与 beatgrid 副歌段能量匹配"],
    "identity_probe": ["近景/大表情下脸不崩（与定妆并排比对）", "image_qc 脸检 ok", "禁漂项未破"],
    "motion_probe": ["动作在后端能力内、无肢体崩坏", "首帧→尾帧衔接可读", "运动模糊/变形可接受"],
    "state_change_probe": ["换装/换景后仍是同一人", "新状态与蓝图状态变体一致", "参考锚挂法可复制到同状态其余镜"],
}


def select_probes(clips: list[dict[str, Any]], drift_by_id: dict[str, dict[str, Any]],
                  limit: int = DEFAULT_LIMIT) -> list[dict[str, Any]]:
    """挑代表镜（纯函数）：每类至多一镜，开场保底，去重后截断 limit。"""
    probes: list[dict[str, Any]] = []

    def _cid(clip: dict[str, Any]) -> str:
        return str(clip.get("clip_id"))

    def _add(clip: dict[str, Any] | None, reason: str, why: str) -> None:
        if clip is None:
            return
        cid = _cid(clip)
        for row in probes:
            if row["clip_id"] == cid:
                if reason not in row["reasons"]:
                    row["reasons"].append(reason)
                    row["why"] += f"；{why}"
                return
        probes.append({
            "clip_id": cid,
            "section": str(clip.get("section") or ""),
            "reasons": [reason],
            "why": why,
            "image_probe": "先只出本镜首帧（+必要尾帧），跑 image_qc 与人工并排比对后再全量。",
            "video_probe": "若本镜代表的类别有动作/衔接疑虑，用默认后端出 1 条短样验证后再批量。",
            "acceptance": list(PROBE_ACCEPTANCE.get(reason, [])),
        })

    if clips:
        _add(clips[0], "opening_probe", "开场镜=风格与身份第一印象，前 3 秒钩子")

    chorus = next((c for c in clips if _is_chorusish(c)), None)
    _add(chorus, "chorus_peak_probe", "副歌/爽点 key 镜=全曲记忆点")

    # identity_probe：drift_risk high 中分数最高者；缺报告→近景+强情绪兜底。
    risky = [(drift_by_id.get(_cid(c), {}), c) for c in clips]
    highs = [(row, c) for row, c in risky if row.get("tier") == "high"]
    if highs:
        _add(max(highs, key=lambda rc: rc[0].get("score") or 0)[1],
             "identity_probe", "drift_risk 预测漂移风险最高")
    else:
        fallback = next((c for c in clips
                         if CLOSEUP_RE.search(str(_sd(c).get("shot_size") or ""))
                         and EMOTION_RE.search(_blob(c))), None)
        _add(fallback, "identity_probe", "近景+强情绪镜=脸最易崩处（无 drift_risk 报告时的兜底选择）")

    motion = next((c for c in clips if DYNAMIC_CAM_RE.search(_blob(c))), None)
    _add(motion, "motion_probe", "运动幅度最大镜=后端动作能力先验证")

    prev_state, prev_loc = "", ""
    for index, clip in enumerate(clips):
        state, loc = _identity_state(clip), _location_key(clip)
        changed = (state and prev_state and state != prev_state) or (loc and prev_loc and loc != prev_loc)
        if index > 0 and changed:
            _add(clip, "state_change_probe", "首个换装/换景镜=重锚点挂法先验证")
            break
        prev_state, prev_loc = state or prev_state, loc or prev_loc

    return probes[:max(1, limit)]


def build_matrix(root: str, limit: int = DEFAULT_LIMIT) -> dict[str, Any]:
    root = os.path.abspath(root)
    plan_rel = "分镜/clip_plan.json"
    plan_path = os.path.join(root, plan_rel)
    plan = load_json(plan_path)
    notes: list[str] = []
    clips = [c for c in ((plan or {}).get("clips") or []) if isinstance(c, dict)] if isinstance(plan, dict) else []
    if not clips:
        notes.append("缺 clip_plan 或无 clips——先跑 mv-plan 再生成打样矩阵。")
    drift_by_id = load_drift_tiers(root)
    if clips and not drift_by_id:
        notes.append("未见 drift_risk 报告——identity_probe 用近景+强情绪兜底；"
                     "建议先跑 `python3 skills/mv-image/scripts/drift_risk.py <作品根> --write`。")
    probes = select_probes(clips, drift_by_id, limit=limit)
    return {
        "schema_version": VERSION,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "engine": "mv-plan/scripts/pilot_matrix.py",
        "inputs_sha256": {plan_rel: _sha256(plan_path)},
        "clip_count": len(clips),
        "probes": probes,
        "summary": {"probes": len(probes), "clips_checked": len(clips)},
        "notes": notes + ["report-only：打样矩阵不改时长/切点，不自动出图；"
                          "打样通过后再进 mv-image 全量。"],
    }


def render_markdown(matrix: dict[str, Any]) -> str:
    lines = [
        "# MV 打样探针矩阵（全量出图前 · report-only）",
        "",
        f"- generated_at: {matrix.get('generated_at')}",
        f"- clip_count: {matrix.get('clip_count')}   probes: {matrix.get('summary', {}).get('probes')}",
        "",
        "| Clip | Reasons | Why | 验收 |",
        "|---|---|---|---|",
    ]
    for p in matrix.get("probes") or []:
        lines.append(f"| {p.get('clip_id')} | {'、'.join(p.get('reasons') or [])} | {p.get('why')} | "
                     f"{'；'.join(p.get('acceptance') or [])} |")
    lines.append("")
    for note in matrix.get("notes") or []:
        lines.append(f"- [note] {note}")
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(root: str, matrix: dict[str, Any]) -> tuple[str, str]:
    out_dir = os.path.join(root, "生产数据", "pilot_matrix")
    json_path = os.path.join(out_dir, "pilot_matrix.json")
    md_path = os.path.join(out_dir, "pilot_matrix.md")
    write_json(json_path, matrix)
    write_text(md_path, render_markdown(matrix))
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="MV 打样探针矩阵（report-only）")
    ap.add_argument("project_root")
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    ap.add_argument("--write", action="store_true", help="落盘 生产数据/pilot_matrix/pilot_matrix.{json,md}")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.project_root):
        print(f"[err] 找不到作品根：{args.project_root}")
        return 2
    matrix = build_matrix(args.project_root, limit=args.limit)
    if args.write:
        json_path, md_path = write_outputs(matrix["project_root"], matrix)
        print(f"[ok] pilot matrix JSON → {json_path}")
        print(f"[ok] pilot matrix MD   → {md_path}")
    if args.json:
        print(json.dumps(matrix, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(matrix))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
