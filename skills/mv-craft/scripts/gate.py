#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic gates for MV stages."""
import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import mv_utils


def _settings_mode(root, meta):
    settings = mv_utils.parse_settings(root)
    return meta.get("song_timing") or settings.get("歌曲输入时序") or "先传音乐"


def _has_rough_blueprint(root):
    text = mv_utils.read_text(os.path.join(root, "视觉蓝图.md"))
    return "rough（待成品歌/beatgrid 复核）" in text or "状态：rough" in text


# 付费 / 不可逆阶段：进入前必须确认输入歌曲版权（音乐媒介的核心合规闸）。
_COSTLY_STAGES = {"image", "video_jobs", "compose"}
_UNRESOLVED_RIGHTS = {"", "unknown", "未知", "未定", "未确认", "未声明", "待确认"}


def _song_rights_status(root, meta):
    settings = mv_utils.parse_settings(root)
    return (meta.get("song_rights_status")
            or settings.get("输入歌权利")
            or settings.get("权利来源")
            or "").strip()


def _rights_errors(root, stage, meta):
    """音乐媒介合规：付费视觉生产前必须确认歌曲版权 + 翻唱/克隆授权。
    按 CLAUDE.md，合规/不可逆点每次都查（不因记过一次就永久放行 unknown）。"""
    if stage not in _COSTLY_STAGES:
        return []
    manifest = mv_utils.load_json(os.path.join(root, "合规", "rights_manifest.json"), None)
    if not meta.get("is_demo"):
        if not isinstance(manifest, dict):
            return ["正式项目缺 合规/rights_manifest.json；需记录歌曲、视觉参考、真人肖像、品牌、场地和编舞权利状态"]
        allowed = {"owned", "public_domain", "licensed", "authorized", "cleared", "not_applicable"}
        assertions = manifest.get("assertions") or {}
        missing = [key for key in ("song", "visual_reference", "likeness", "brand", "location", "choreography")
                   if assertions.get(key) not in allowed]
        if missing:
            return [f"rights_manifest 未解决：{', '.join(missing)}"]
    rights = _song_rights_status(root, meta)
    low = rights.lower()
    if low in _UNRESOLVED_RIGHTS:
        return ["输入歌曲版权状态未确认（song_rights_status）；进入出图/出视频/合成等付费不可逆阶段前，"
                "先确认歌曲为自有/公版/已授权（init 传 --song-rights-status 或在 _设置.md 记录）。"
                "翻唱与真人嗓音克隆需另有授权。"]
    if any(k in low for k in ("cover", "翻唱")) and not (meta.get("cover_authorized") or meta.get("翻唱授权")):
        return ["输入歌曲为翻唱/cover，但缺翻唱授权留痕（_meta.cover_authorized）；"
                "付费视觉生产前补授权，或改用自有/公版歌。"]
    if any(k in low for k in ("clone", "克隆")) and not (meta.get("voice_clone_authorized") or meta.get("声音克隆授权")):
        return ["输入歌曲使用克隆嗓音，但缺声音克隆授权留痕（_meta.voice_clone_authorized）；付费生产前补授权。"]
    return []


def _staleness_errors(root, stage):
    """后配歌曲招牌路径的工程化闸：clip_plan 记录了它依据的 beatgrid/song 内容快照，
    若之后换歌或重测卡点（hash 变了），下游付费阶段硬报，逼用户先重跑 mv-plan。
    旧 plan 没有 hash 字段时跳过（向后兼容，不误报）。"""
    if stage not in _COSTLY_STAGES:
        return []
    plan = _load_plan(root)
    if not plan:
        return []
    errs = []
    rec_bg = plan.get("beatgrid_hash")
    if rec_bg:
        cur_bg = mv_utils.content_hash(os.path.join(root, "节拍", "beatgrid.json"))
        if cur_bg and cur_bg != rec_bg:
            errs.append("节拍/beatgrid.json 自 mv-plan 之后已变（换歌/重测卡点）；"
                        "先重跑 mv-plan，否则 clip 时长/卡点与新节拍不符。")
    rec_song = plan.get("song_hash")
    if rec_song:
        cur_song = mv_utils.content_hash(mv_utils.find_song(root))
        if cur_song and cur_song != rec_song:
            errs.append("歌/song.* 自 mv-plan 之后已变（后配歌曲定稿/换歌）；先重跑 mv-beat + mv-plan。")
    return errs


def _load_plan(root):
    return mv_utils.load_json(os.path.join(root, "分镜", "clip_plan.json"), {}) or {}


def _image_qc_path(root):
    return os.path.join(root, "生产数据", "image_qc", "image_qc.json")


def _image_qc_errors_warnings(root, stage):
    if stage not in {"video_jobs", "compose"}:
        return [], []
    path = _image_qc_path(root)
    report = mv_utils.load_json(path, None)
    if not isinstance(report, dict):
        return [f"缺 mv-image 出图落档机检报告：{path}；先跑 `python3 skills/mv-image/scripts/image_qc.py <作品根>`"], []
    summary = report.get("summary") or {}
    env = report.get("qc_environment") or {}
    errors = []
    warnings = []
    try:
        hard = int(summary.get("hard_blocks") or 0)
    except (TypeError, ValueError):
        return [f"mv-image image_qc 报告格式异常：summary.hard_blocks 缺失或不是整数（{path}）"], []
    if hard:
        errors.append(f"mv-image image_qc 仍有 hard block={hard}（主角脸崩/图损坏/禁用本地贴脸产物）；先回 mv-image 修复重跑")
    precision = str(env.get("precision_level") or "").strip()
    manual_ok = bool(report.get("manual_review_accepted") or env.get("manual_review_accepted"))
    if precision != "full" and not manual_ok:
        errors.append(f"mv-image image_qc 机检精度为 {precision or 'unknown'}，未达到 full；正式进 mv-video 前需补依赖重跑，"
                      "或在报告中人工留痕 manual_review_accepted=true 后再继续")
    elif precision != "full" and manual_ok:
        warnings.append(f"mv-image image_qc 机检精度为 {precision or 'unknown'}，但已有人工复核放行留痕")
    try:
        advisory = int(summary.get("advisory") or 0)
    except (TypeError, ValueError):
        advisory = 0
    if advisory or summary.get("verdict") == "review":
        warnings.append(f"mv-image image_qc 有非阻断初筛项 advisory={advisory}，进入视频前请确认主色/锚点/参考输入已复核")

    plan = _load_plan(root)
    try:
        qc_mtime = os.path.getmtime(path)
    except OSError:
        qc_mtime = 0
    stale = []
    for clip in plan.get("clips", []):
        if not isinstance(clip, dict):
            continue
        rels = [clip.get("image_path")]
        if clip.get("need_end_frame"):
            rels.append(clip.get("end_frame_path"))
        for rel in rels:
            if not rel:
                continue
            full = os.path.join(root, rel)
            try:
                if os.path.getmtime(full) > qc_mtime:
                    stale.append(str(rel))
            except OSError:
                continue
    if stale:
        errors.append(f"mv-image image_qc 已过期：{len(stale)} 张图片晚于 QC 报告，例：{stale[0]}；重跑 image_qc")
    return errors, warnings


def _video_report_errors(root, stage):
    if stage != "compose":
        return []
    reports = (
        ("生产数据/video_inherit_contract/inherit_contract.json",
         ("分镜/clip_plan.json", "出视频/jobs_manifest.json", "设定/identity_registry.json", "分镜/reference_plan.json")),
        ("生产数据/video_qc/video_qc.json", ("分镜/clip_plan.json", "分镜/timeline_manifest.json")),
    )
    errors = []
    for report_rel, required_inputs in reports:
        report = mv_utils.load_json(os.path.join(root, report_rel), None)
        if not isinstance(report, dict):
            errors.append(f"缺或损坏 {report_rel}；全部视频挑版后重跑 mv-video 对应检查")
            continue
        summary = report.get("summary") or {}
        if int(summary.get("hard_blocks") or 0):
            errors.append(f"{report_rel} 仍有 hard_blocks={summary.get('hard_blocks')}")
        recorded = report.get("inputs_sha256") or {}
        for rel in required_inputs:
            current = mv_utils.content_hash(os.path.join(root, rel))
            if not current or recorded.get(rel) != current:
                errors.append(f"{report_rel} 已过期：{rel} 与报告 hash 不一致；重跑对应检查")
                break
        if report_rel.endswith("video_qc.json"):
            video_hashes = report.get("selected_video_sha256") or {}
            if not video_hashes:
                errors.append(f"{report_rel} 缺 selected_video_sha256，不能证明检查对应当前视频")
            for rel, recorded_hash in video_hashes.items():
                if mv_utils.content_hash(os.path.join(root, rel)) != recorded_hash:
                    errors.append(f"{report_rel} 已过期：选中视频 {rel} 已变化")
                    break
            meta = mv_utils.load_json(os.path.join(root, "_meta.json"), {}) or {}
            if not meta.get("is_demo") and not (report.get("semantic_review") or {}).get("accepted"):
                errors.append("正式项目缺视频语义人工签收：逐镜/接缝复核后运行 video_qc.py --accept-semantic --reviewer <name>")
    return errors


def _picture_lock_errors(root, stage, meta):
    if stage not in {"video_jobs", "compose"} or meta.get("is_demo"):
        return []
    path = os.path.join(root, "制片", "picture_lock.json")
    payload = mv_utils.load_json(path, None)
    if not isinstance(payload, dict) or not payload.get("accepted"):
        return ["正式项目缺已签收 picture lock；先 render_animatic.py，再 picture_lock.py --reviewer <name>"]
    errors = []
    recorded_inputs = payload.get("inputs_sha256") or {}
    plan = _load_plan(root)
    required = {"分镜/clip_plan.json", "节拍/beatgrid.json", "分镜/animatic.mp4", "生产数据/image_qc/image_qc.json"}
    song = mv_utils.find_song(root)
    if song:
        required.add(mv_utils.relpath(root, song))
    required.update(c.get("image_path") for c in plan.get("clips", []) if c.get("image_path"))
    omitted = [rel for rel in required if rel not in recorded_inputs]
    if omitted:
        errors.append(f"picture lock 输入不完整，未绑定：{omitted[0]}")
    for rel, recorded in recorded_inputs.items():
        if mv_utils.content_hash(os.path.join(root, rel)) != recorded:
            errors.append(f"picture lock 已过期：{rel} 已变化；重渲 animatic 并重新签收")
            break
    return errors


def check(root, stage):
    errors = []
    warnings = []
    meta = mv_utils.load_json(os.path.join(root, "_meta.json"), {}) or {}
    mode = _settings_mode(root, meta)
    song = mv_utils.find_song(root)
    lyrics = os.path.join(root, "词", "lyrics.md")
    beatgrid = os.path.join(root, "节拍", "beatgrid.json")
    blueprint = os.path.join(root, "视觉蓝图.md")
    clip_plan = os.path.join(root, "分镜", "clip_plan.json")
    timeline = os.path.join(root, "分镜", "timeline_manifest.json")

    if stage in {"beat", "plan", "image", "video_jobs", "lyric_sync", "compose"} and not song:
        errors.append("缺 歌/song.*，请先补入最终成品歌")
    if stage in {"plan", "image", "video_jobs", "lyric_sync", "compose"} and not os.path.exists(lyrics):
        errors.append("缺 词/lyrics.md")
    if stage in {"plan", "image", "video_jobs", "compose"} and not os.path.exists(beatgrid):
        errors.append("缺 节拍/beatgrid.json，先跑 mv-beat")
    if stage in {"plan", "image", "video_jobs", "compose"} and os.path.exists(beatgrid):
        beat_payload = mv_utils.load_json(beatgrid, {}) or {}
        if not beat_payload.get("timing_verified") and not meta.get("is_demo"):
            errors.append("beatgrid 的拍号/小节相位/段落边界尚未人工确认（timing_verified=false）；"
                          "正式项目请校正 section_timings，并用 mv-beat --downbeat-phase N --confirm-timing 重跑")
    if stage in {"script_review", "plan", "image", "video_jobs"} and not os.path.exists(blueprint):
        errors.append("缺 视觉蓝图.md")
    if stage in {"plan", "image", "video_jobs", "compose"} and _has_rough_blueprint(root):
        errors.append("视觉蓝图仍是 rough，正式产物阶段前先用 mv-script 复核")
    if stage in {"image", "video_jobs", "compose"} and not os.path.exists(clip_plan):
        errors.append("缺 分镜/clip_plan.json，先跑 mv-plan")
    if stage == "compose" and not os.path.exists(timeline):
        errors.append("缺 分镜/timeline_manifest.json，compose 默认不按目录猜顺序")

    if stage == "video_jobs" and os.path.exists(clip_plan):
        plan = _load_plan(root)
        missing = []
        for clip in plan.get("clips", []):
            image_path = clip.get("image_path")
            if image_path and not os.path.exists(os.path.join(root, image_path)):
                missing.append(f"{clip.get('clip_id')}:{image_path}")
        if missing:
            errors.append(f"缺 {len(missing)} 个首帧 PNG，先跑 mv-image；例：{missing[0]}")

    qc_errors, qc_warnings = _image_qc_errors_warnings(root, stage)
    errors.extend(qc_errors)
    warnings.extend(qc_warnings)
    errors.extend(_video_report_errors(root, stage))
    errors.extend(_picture_lock_errors(root, stage, meta))

    if stage == "compose" and os.path.exists(timeline):
        data = mv_utils.load_json(timeline, {}) or {}
        missing = []
        for clip in data.get("clips", []):
            video_path = clip.get("video_path")
            if not video_path or not os.path.exists(os.path.join(root, video_path)):
                missing.append(clip.get("clip_id") or video_path or "unknown")
        if missing:
            errors.append(f"timeline 有 {len(missing)} 个 clip 未选中视频，例：{missing[0]}")
        # 交叉核对挑版台账：timeline 仅按"文件存在"判选中，绕过 --select 手动丢入的 clip
        # 会冒充已选中且无 take/分记录。jobs_manifest 在时给出告警（不硬挡手动工作流）。
        jobs = (mv_utils.load_json(os.path.join(root, "出视频", "jobs_manifest.json"), {}) or {}).get("jobs") or []
        if jobs:
            selected_ids = {j.get("clip_id") for j in jobs if j.get("selected_take")}
            unverified = [
                clip.get("clip_id") for clip in data.get("clips", [])
                if clip.get("video_path")
                and os.path.exists(os.path.join(root, clip["video_path"]))
                and clip.get("clip_id") not in selected_ids
            ]
            if unverified:
                warnings.append(
                    f"{len(unverified)} 个 clip 有成片视频但 jobs_manifest 无挑版记录"
                    f"（可能绕过 --select 手动放入）：{unverified[0]}…；确认来源/质量已经过挑版。")

    errors.extend(_rights_errors(root, stage, meta))
    errors.extend(_staleness_errors(root, stage))

    if stage == "lyric_sync" and os.path.exists(lyrics):
        lines = [
            x.strip() for x in mv_utils.read_text(lyrics).splitlines()
            if x.strip() and not x.strip().startswith("#") and not mv_utils.SECTION_RE.match(x.strip())
        ]
        if not lines:
            errors.append("词/lyrics.md 没有可对齐歌词行")

    return errors, warnings


def main():
    ap = argparse.ArgumentParser(description="检查制MV阶段前置 gate")
    ap.add_argument("project_root")
    ap.add_argument("stage")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    errors, warnings = check(root, args.stage)
    for msg in warnings:
        print(f"[warn] {msg}")
    if errors:
        for msg in errors:
            print(f"[err] {msg}", file=sys.stderr)
        return 1
    print(f"[ok] gate pass: {args.stage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
