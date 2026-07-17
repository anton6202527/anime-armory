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


def _lyrics_required(root, meta, stage=None):
    """Lyrics are conditional: instrumental/no-subtitle/no-lipsync MVs are valid."""
    if stage == "lyric_sync":
        return True
    settings = mv_utils.parse_settings(root)
    subtitle_mode = settings.get("字幕语言") or meta.get("subtitle_language") or "中文"
    lip_mode = settings.get("演唱口型") or meta.get("lip_sync_mode") or "仅正面演唱镜"
    return subtitle_mode != "无字幕" or lip_mode != "关闭"


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


def _staleness_errors(root, stage, meta):
    """Verify that a plan still describes its exact upstream creative truth."""
    if stage not in _COSTLY_STAGES:
        return []
    plan = _load_plan(root)
    if not plan:
        return []
    errs = []
    input_paths = {
        "song": mv_utils.find_song(root),
        "beatgrid": os.path.join(root, "节拍", "beatgrid.json"),
        "lyrics": os.path.join(root, "词", "lyrics.md"),
        "blueprint": os.path.join(root, "视觉蓝图.md"),
        "settings": os.path.join(root, "_设置.md"),
    }
    recorded_inputs = plan.get("inputs_sha256")
    if isinstance(recorded_inputs, dict):
        for key, path in input_paths.items():
            recorded = recorded_inputs.get(key)
            current = mv_utils.content_hash(path)
            if key == "lyrics" and not _lyrics_required(root, meta, stage) and not os.path.exists(path):
                if recorded not in (None, ""):
                    errs.append("clip_plan 记录了不存在的 lyrics 输入；重跑 mv-plan 清理旧收据")
                continue
            if not recorded:
                errs.append(f"clip_plan.inputs_sha256 缺 {key}；重跑 mv-plan 建立完整输入收据")
            elif current != recorded:
                errs.append(f"{key} 自 mv-plan 后已变化；重跑 mv-plan，不能让旧分镜消费新输入")
    elif not meta.get("is_demo"):
        errs.append("正式 clip_plan 缺 inputs_sha256 全输入收据；重跑 mv-plan 升级合同")

    # Legacy fields remain readable so demo/older projects receive precise
    # change detection while migrating to inputs_sha256.
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


def _beatgrid_contract(root, stage, meta, song):
    """Return deterministic errors/warnings for the music-timing truth source."""
    if stage not in {"plan", "image", "video_jobs", "compose"}:
        return [], []
    path = os.path.join(root, "节拍", "beatgrid.json")
    payload = mv_utils.load_json(path, {}) or {}
    if not payload:
        return [], []  # the common existence gate owns the missing-file message
    errors, warnings = [], []
    recorded_song = str(payload.get("source_audio_sha256") or "")
    current_song = mv_utils.content_hash(song)
    if recorded_song and current_song != recorded_song:
        errors.append("beatgrid 不是由当前 歌/song.* 生成（source_audio_sha256 不一致）；先重跑 mv-beat")
    elif not recorded_song:
        message = "beatgrid 缺 source_audio_sha256，不能证明节拍来自当前歌曲；重跑 mv-beat"
        (warnings if meta.get("is_demo") else errors).append(message)

    for key in ("beats", "downbeats"):
        values = payload.get(key) or []
        if not values:
            (warnings if meta.get("is_demo") else errors).append(f"beatgrid.{key} 为空")
            continue
        try:
            floats = [float(value) for value in values]
        except (TypeError, ValueError):
            errors.append(f"beatgrid.{key} 含非数值时间戳")
            continue
        if any(right <= left for left, right in zip(floats, floats[1:])):
            errors.append(f"beatgrid.{key} 必须严格递增")

    sections = payload.get("sections") or []
    if not meta.get("is_demo"):
        review = payload.get("timing_review") or {}
        if not payload.get("timing_verified"):
            errors.append("beatgrid timing_verified=false；正式项目需具名确认拍号、小节相位和完整段落边界")
        if not payload.get("downbeats_verified"):
            errors.append("beatgrid.downbeats_verified=false；正式卡点不能把自动 onset 相位当人工确认")
        if not payload.get("sections_verified") or not payload.get("sections_complete"):
            errors.append("beatgrid 段落边界未完整覆盖全曲并签收；补 _meta.section_timings 后重跑 mv-beat")
        if not review.get("accepted") or not str(review.get("reviewer") or "").strip():
            errors.append("beatgrid 缺具名 timing_review；用 mv-beat --confirm-timing --reviewer <name> 重跑")
        if not sections:
            errors.append("beatgrid.sections 为空；正式 mv-plan 不得按歌词字数伪造段落时长")

    measured = mv_utils.audio_duration(song) if song else None
    try:
        grid_duration = float(payload.get("duration"))
    except (TypeError, ValueError):
        grid_duration = None
    if measured and grid_duration is not None and abs(measured - grid_duration) > 0.25:
        errors.append(f"beatgrid.duration={grid_duration:.3f}s 与当前歌曲实测 {measured:.3f}s 不一致")
    return list(dict.fromkeys(errors)), list(dict.fromkeys(warnings))


def _timeline_contract_errors(root, stage, meta):
    if stage not in {"image", "video_jobs", "compose"}:
        return []
    plan = _load_plan(root)
    timeline = mv_utils.load_json(os.path.join(root, "分镜", "timeline_manifest.json"), {}) or {}
    if not plan or not timeline:
        return []
    errors = []
    p_rows = plan.get("clips") or []
    t_rows = timeline.get("clips") or []
    if [r.get("clip_id") for r in p_rows] != [r.get("clip_id") for r in t_rows]:
        errors.append("timeline_manifest 与 clip_plan 的 clip 顺序/集合不一致；重跑 mv-plan")
        return errors
    for left, right in zip(p_rows, t_rows):
        for key in ("start", "end", "duration"):
            try:
                if abs(float(left.get(key)) - float(right.get(key))) > 0.001:
                    errors.append(f"{right.get('clip_id')} timeline.{key} 与 clip_plan 不一致")
                    break
            except (TypeError, ValueError):
                errors.append(f"{right.get('clip_id')} timeline/clip_plan 缺有效 {key}")
                break
    source_hash = timeline.get("source_clip_plan_sha256")
    if not source_hash and not meta.get("is_demo"):
        errors.append("正式 timeline_manifest 缺 source_clip_plan_sha256；重跑 mv-plan")
    elif source_hash and source_hash != mv_utils.content_hash(os.path.join(root, "分镜", "clip_plan.json")):
        errors.append("timeline_manifest 未绑定当前 clip_plan；同步语义分镜后需刷新 timeline/OTIO")
    return list(dict.fromkeys(errors))


def _otio_contract_errors(root, stage, meta):
    if stage not in {"video_jobs", "compose"} or meta.get("is_demo"):
        return []
    otio_rel = "分镜/timeline.otio"
    receipt_rel = "生产数据/otio/otio_receipt.json"
    otio_path = os.path.join(root, otio_rel)
    receipt = mv_utils.load_json(os.path.join(root, receipt_rel), None)
    if not os.path.isfile(otio_path) or not isinstance(receipt, dict):
        return ["正式项目缺可编辑 OTIO + hash receipt；先跑 production_pack.py 或 export_otio.py"]
    timeline_path = os.path.join(root, "分镜", "timeline_manifest.json")
    beat_path = os.path.join(root, "节拍", "beatgrid.json")
    timeline = mv_utils.load_json(timeline_path, {}) or {}
    errors = []
    if receipt.get("otio_sha256") != mv_utils.content_hash(otio_path):
        errors.append("timeline.otio 与 otio_receipt 不一致；重跑 export_otio.py")
    if receipt.get("timeline_edit_sha256") != mv_utils.timeline_edit_hash(timeline):
        errors.append("timeline.otio 未反映当前剪辑决定；重跑 export_otio.py")
    recorded = receipt.get("inputs_sha256") or {}
    if recorded.get("分镜/timeline_manifest.json") != mv_utils.content_hash(timeline_path):
        errors.append("OTIO receipt 已过期：timeline_manifest 在导出后变化")
    if recorded.get("节拍/beatgrid.json") != mv_utils.content_hash(beat_path):
        errors.append("OTIO receipt 已过期：beatgrid 在导出后变化")
    if stage == "compose" and receipt.get("missing_media"):
        errors.append(f"OTIO 仍有 {len(receipt['missing_media'])} 个 missing media；全部挑版后重导 OTIO")
    return errors


def _pacing_receipt_errors(root, stage, meta):
    if stage not in {"image", "video_jobs"} or meta.get("is_demo"):
        return []
    rel = "评分/pacing_prescore.json"
    report = mv_utils.load_json(os.path.join(root, rel), None)
    if not isinstance(report, dict):
        return ["正式付费生产前缺 pacing_prescore；先跑 mv-score 的确定性节奏检查（可不设主观阈值）"]
    required = ("分镜/clip_plan.json", "节拍/beatgrid.json")
    recorded = report.get("inputs_sha256") or {}
    errors = []
    for input_rel in required:
        if recorded.get(input_rel) != mv_utils.content_hash(os.path.join(root, input_rel)):
            errors.append(f"pacing_prescore 已过期：{input_rel} 变化；重跑 mv-score")
    song = mv_utils.find_song(root)
    if song:
        song_rel = mv_utils.relpath(root, song)
        if recorded.get(song_rel) != mv_utils.content_hash(song):
            errors.append("pacing_prescore 已过期：当前歌曲变化；重跑 mv-score")
    if report.get("threshold") is not None and report.get("blocked"):
        errors.append("pacing_prescore 按项目显式阈值判定 blocked；先按 return_to_stages 回流")
    return errors


def _alignment_contract_errors(root, stage, meta):
    if stage not in {"video_jobs", "compose"} or meta.get("is_demo"):
        return []
    settings = mv_utils.parse_settings(root)
    plan = _load_plan(root)
    vocal_performance = any(
        str(clip.get("action_family") or "") == "performance_vocal" or clip.get("vocal_lyrics")
        for clip in plan.get("clips", []) if isinstance(clip, dict)
    )
    lip_mode = settings.get("演唱口型") or "仅正面演唱镜"
    subtitle_mode = settings.get("字幕语言") or "中文"
    required = (stage == "video_jobs" and vocal_performance and lip_mode != "关闭") or (
        stage == "compose" and subtitle_mode != "无字幕"
    )
    if not required:
        return []
    report = mv_utils.load_json(os.path.join(root, "字幕", "alignment_report.json"), None)
    if not isinstance(report, dict):
        purpose = "演唱口型镜" if stage == "video_jobs" else "正式字幕"
        return [f"{purpose} 缺歌词强制对齐收据；先跑 mv-lyric-sync"]
    errors = []
    recorded = report.get("inputs_sha256") or {}
    lyrics_rel = "词/lyrics.md"
    if recorded.get(lyrics_rel) != mv_utils.content_hash(os.path.join(root, lyrics_rel)):
        errors.append("alignment_report 已过期：lyrics.md 变化；重跑 mv-lyric-sync")
    song = mv_utils.find_song(root)
    if song:
        song_rel = mv_utils.relpath(root, song)
        if recorded.get(song_rel) != mv_utils.content_hash(song):
            errors.append("alignment_report 已过期：主歌轨变化；重跑 mv-lyric-sync")
    automatic_pass = (
        int(report.get("aligned_lines") or 0) == int(report.get("lyric_lines") or -1)
        and float(report.get("character_coverage_ratio", report.get("alignment_confidence") or 0)) >= 0.9
        and not report.get("timing_issues")
    )
    manual = report.get("manual_review") or {}
    manual_pass = bool(
        manual.get("accepted")
        and str(manual.get("reviewer") or "").strip()
        and str(manual.get("notes") or "").strip()
    )
    if manual_pass and manual.get("bound_inputs_sha256") != recorded:
        manual_pass = False
    if not automatic_pass and not manual_pass:
        errors.append("歌词时间轴未达到完整行/90% 字符覆盖且无具名逐行听审说明")
    for rel in ("字幕/karaoke.ass", "字幕/lyrics.lrc"):
        if stage == "compose" and not os.path.isfile(os.path.join(root, rel)):
            errors.append(f"正式字幕模式缺 {rel}")
    return errors


def _semantic_prompt_errors(root, stage, meta):
    if stage not in {"image", "video_jobs"} or meta.get("is_demo"):
        return []
    plan_path = os.path.join(root, "分镜", "clip_plan.json")
    plan = _load_plan(root)
    receipt = mv_utils.load_json(os.path.join(root, "分镜", "semantic_prompts.json"), None)
    if not isinstance(receipt, dict):
        return ["正式出图前缺语义分镜消费收据；用 compose_prompts.py 注入覆盖全部 clips 的具体画面/动作"]
    errors = []
    if int(receipt.get("updated_clips") or 0) != len(plan.get("clips") or []):
        errors.append("semantic_prompts 未覆盖全部 clip；正式项目不得用通用占位动作直接出图")
    if receipt.get("result_clip_plan_sha256") != mv_utils.content_hash(plan_path):
        errors.append("semantic_prompts 收据未绑定当前 clip_plan；重新注入或签收语义分镜")
    recorded = receipt.get("inputs_sha256") or {}
    for key, rel in (("lyrics", "词/lyrics.md"), ("blueprint", "视觉蓝图.md")):
        if recorded.get(key) != mv_utils.content_hash(os.path.join(root, rel)):
            errors.append(f"semantic_prompts 已过期：{rel} 变化")
    return errors


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
    # 降级放行必须具名并绑定报告 hash（与 video_qc semantic_review 同强度）：
    # 裸布尔留痕无法证明「人看的就是这份报告」，报告一重跑绑定即失效。
    manual = report.get("manual_review") or {}
    manual_ok = False
    manual_note = ""
    if manual.get("accepted") and str(manual.get("reviewer") or "").strip():
        stripped = {k: v for k, v in report.items()
                    if k not in ("manual_review", "json_path", "markdown_path")}
        manual_ok = manual.get("bound_report_sha256") == mv_utils.json_hash(stripped)
        if not manual_ok:
            manual_note = "（已有 manual_review 但绑定 hash 与当前报告不符——报告重跑后需重新放行）"
    elif report.get("manual_review_accepted") or env.get("manual_review_accepted"):
        manual_note = "（旧式 manual_review_accepted 布尔留痕不再放行——无法证明复核对应当前报告）"
    if precision != "full" and not manual_ok:
        errors.append(f"mv-image image_qc 机检精度为 {precision or 'unknown'}，未达到 full{manual_note}；"
                      "正式进 mv-video 前需补依赖重跑，或逐图人工复核后用 "
                      "`image_qc.py <作品根> --accept-degraded --reviewer <name> --notes <说明>` 具名绑定放行")
    elif precision != "full" and manual_ok:
        warnings.append(f"mv-image image_qc 机检精度为 {precision or 'unknown'}，"
                        f"已有具名人工放行（reviewer={manual.get('reviewer')}，绑定当前报告）")
    try:
        advisory = int(summary.get("advisory") or 0)
    except (TypeError, ValueError):
        advisory = 0
    if advisory or summary.get("verdict") == "review":
        warnings.append(f"mv-image image_qc 有非阻断初筛项 advisory={advisory}，进入视频前请确认主色/锚点/参考输入已复核")
    meta = mv_utils.load_json(os.path.join(root, "_meta.json"), {}) or {}
    provenance = report.get("generation_provenance") or {}
    if not meta.get("is_demo") and not provenance.get("complete"):
        errors.append("正式出图缺逐资产 model+channel+prompt+asset hash 生成收据，或项目内混用生图模型/渠道；先补 production_events 再重跑 image_qc")

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


def _identity_readiness(root, stage, meta):
    """主角定妆包 readiness 闸（参照 n2d image_preflight 对核心角色缺锚直接 BLOCK）。

    此前定妆包不全只在 mv-review 汇总为 warn，付费 gate 不拦——定妆不 ready 时
    image_qc 的脸检 floor 无法自标定，出视频后主角漂移无人拦。image 期共享定妆
    本身尚在产出 → 只 warn 提醒先做定妆；video_jobs（正式）→ error。"""
    if stage not in {"image", "video_jobs"}:
        return [], []
    formal_block = stage == "video_jobs" and not meta.get("is_demo")
    registry = mv_utils.load_json(os.path.join(root, "设定", "identity_registry.json"), None)
    if not isinstance(registry, dict):
        msg = ("缺 设定/identity_registry.json（身份/参考真值）；"
               "先跑 `python3 skills/mv-craft/scripts/identity_registry.py <作品根>`")
        return ([msg], []) if formal_block else ([], [msg])
    lead_id = registry.get("lead_id")
    lead = next((row for row in registry.get("identities") or []
                 if isinstance(row, dict) and row.get("id") == lead_id), None)
    if not isinstance(lead, dict):
        return [], ["identity_registry 缺主角身份行（lead_id 未命中 identities）；重跑 identity_registry.py"]
    groups = {g.get("id"): g for g in registry.get("reference_groups") or [] if isinstance(g, dict)}
    group = groups.get(lead.get("reference_group")) or {}
    existing = [p for p in group.get("paths") or [] if p and os.path.exists(os.path.join(root, str(p)))]
    if group.get("status") == "ready" and len(existing) >= 3:
        return [], []
    msg = (f"主角『{lead.get('display_name') or lead_id}』定妆包未 ready"
           f"（现存参考 {len(existing)} 张，需≥3：正面/侧脸或三分之二/全身…）；"
           "先补共享定妆再批量出图——定妆不全时脸机检 floor 无法自标定，出视频后漂移无人拦")
    return ([msg], []) if formal_block else ([], [msg])


def _demo_flag_warnings(root, stage, meta):
    """demo 自证护栏：is_demo=true 会短路几乎所有正式一致性闸，但该标记写在 _meta.json
    无人复核。若项目已出现正式生产痕迹，提示复核标记（advisory，不拦）。"""
    if not meta.get("is_demo") or stage not in _COSTLY_STAGES:
        return []
    evidence = []
    lock = mv_utils.load_json(os.path.join(root, "制片", "picture_lock.json"), {}) or {}
    if lock.get("accepted"):
        evidence.append("picture_lock 已签收")
    jobs = (mv_utils.load_json(os.path.join(root, "出视频", "jobs_manifest.json"), {}) or {}).get("jobs") or []
    if any(isinstance(j, dict) and j.get("selected_take") for j in jobs):
        evidence.append("jobs_manifest 已有挑版记录")
    qc = mv_utils.load_json(_image_qc_path(root), {}) or {}
    if (qc.get("generation_provenance") or {}).get("complete"):
        evidence.append("出图生成收据完整")
    if evidence:
        return [f"_meta.is_demo=true 但已有正式生产痕迹（{'；'.join(evidence)}）——demo 标记会短路正式一致性闸；"
                "若已转正式，先跑 formal_readiness.py 评估并把 _meta.is_demo 置 false"]
    return []


def _shot_variety_warnings(root, stage):
    """视觉多样性/构图冗余 事前机检（advisory · 出图前）。永不制造 block——只把 warn 抬进报告。

    出图（image）是最便宜的拦截点：clip_plan 已定、还没花积分出图/出视频。此层照『advisory 绝不
    造假 block』约定，全部落 warnings。"""
    if stage not in {"image", "video_jobs"}:
        return []
    clip_plan = os.path.join(root, "分镜", "clip_plan.json")
    if not os.path.exists(clip_plan):
        return []
    path = os.path.join(root, "生产数据", "shot_variety", "shot_variety.json")
    report = mv_utils.load_json(path, None)
    if not isinstance(report, dict):
        return ["未跑视觉多样性事前机检；出图前建议 `python3 skills/mv-review/scripts/shot_variety_audit.py <作品根> --write`"
                "（查同构图反复/景别单调/副歌静镜/场景滞留/大变化镜头缺参考锚）"]
    warnings = []
    recorded = (report.get("inputs_sha256") or {}).get("分镜/clip_plan.json")
    if recorded and recorded != mv_utils.content_hash(clip_plan):
        warnings.append("视觉多样性机检已过期：clip_plan 变化后未重跑 shot_variety_audit")
    summary = report.get("summary") or {}
    try:
        warn = int(summary.get("warn") or 0)
    except (TypeError, ValueError):
        warn = 0
    if warn:
        codes = sorted({str(f.get("code")) for f in (report.get("findings") or [])
                        if f.get("severity") == "warn"})
        warnings.append(f"视觉多样性事前机检有 {warn} 条 advisory（{'/'.join(codes) or 'n/a'}）——"
                        "出图前回 mv-plan 换景别/机位/运镜/场景/补参考，别把同构图撑满全曲")
    return warnings


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
            semantic = report.get("semantic_review") or {}
            if not meta.get("is_demo") and not semantic.get("accepted"):
                errors.append("正式项目缺视频语义人工签收：逐镜/接缝复核后运行 video_qc.py --accept-semantic --reviewer <name>")
            elif semantic.get("accepted"):
                if semantic.get("bound_video_sha256") != video_hashes:
                    errors.append("视频语义签收未绑定当前 selected_video_sha256；重跑 video_qc 具名签收")
                seam_hash = mv_utils.json_hash([
                    seam.get("seam_contract") or {} for seam in report.get("seams") or []
                ])
                if semantic.get("bound_seam_contract_sha256") != seam_hash:
                    errors.append("视频语义签收未绑定当前接缝分类合同；重跑 video_qc 逐缝签收")
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
    timeline = mv_utils.load_json(os.path.join(root, "分镜", "timeline_manifest.json"), {}) or {}
    editorial_hash = mv_utils.timeline_edit_hash(timeline)
    if payload.get("editorial_timeline_sha256") != editorial_hash:
        errors.append("picture lock 已过期：镜头顺序/切点/时长/接缝意图发生变化；重渲 animatic 并重新签收")
    if payload.get("otio_timeline_sha256") != editorial_hash:
        errors.append("picture lock 未绑定同一 OTIO 编辑合同；重导 OTIO、重渲 animatic 并重新签收")
    required = {
        "分镜/clip_plan.json", "节拍/beatgrid.json", "分镜/animatic.mp4",
        "生产数据/animatic/animatic.json", "生产数据/image_qc/image_qc.json",
        "评分/pacing_prescore.json", "分镜/semantic_prompts.json",
    }
    song = mv_utils.find_song(root)
    if song:
        required.add(mv_utils.relpath(root, song))
    for clip in plan.get("clips", []):
        for key in ("image_path", "image_prompt_path", "video_prompt_path"):
            if clip.get(key):
                required.add(clip[key])
        if clip.get("need_end_frame") and clip.get("end_frame_path"):
            required.add(clip["end_frame_path"])
    settings = mv_utils.parse_settings(root)
    vocal_performance = any(
        clip.get("action_family") == "performance_vocal" or clip.get("vocal_lyrics")
        for clip in plan.get("clips", []) if isinstance(clip, dict)
    )
    if settings.get("字幕语言", "中文") != "无字幕" or (
        vocal_performance and settings.get("演唱口型", "仅正面演唱镜") != "关闭"
    ):
        required.add("字幕/alignment_report.json")
    for optional in ("视觉蓝图.md", "词/lyrics.md", "分镜/semantic_prompts.json"):
        if os.path.exists(os.path.join(root, optional)):
            required.add(optional)
    omitted = [rel for rel in required if rel not in recorded_inputs]
    if omitted:
        errors.append(f"picture lock 输入不完整，未绑定：{omitted[0]}")
    for rel, recorded in recorded_inputs.items():
        if mv_utils.content_hash(os.path.join(root, rel)) != recorded:
            errors.append(f"picture lock 已过期：{rel} 已变化；重渲 animatic 并重新签收")
            break
    animatic_report = mv_utils.load_json(os.path.join(root, "生产数据", "animatic", "animatic.json"), {}) or {}
    if animatic_report.get("output_sha256") != mv_utils.content_hash(os.path.join(root, "分镜", "animatic.mp4")):
        errors.append("animatic 报告未绑定当前 分镜/animatic.mp4；重跑 render_animatic.py")
    if animatic_report.get("timeline_edit_sha256") != editorial_hash:
        errors.append("animatic 不是当前编辑时间线的预演；重跑 render_animatic.py")
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
    if (stage in {"plan", "image", "video_jobs", "lyric_sync", "compose"}
            and _lyrics_required(root, meta, stage) and not os.path.exists(lyrics)):
        errors.append("缺 词/lyrics.md")
    if stage in {"plan", "image", "video_jobs", "compose"} and not os.path.exists(beatgrid):
        errors.append("缺 节拍/beatgrid.json，先跑 mv-beat")
    beat_errors, beat_warnings = _beatgrid_contract(root, stage, meta, song)
    errors.extend(beat_errors)
    warnings.extend(beat_warnings)
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
    identity_errors, identity_warnings = _identity_readiness(root, stage, meta)
    errors.extend(identity_errors)
    warnings.extend(identity_warnings)
    warnings.extend(_demo_flag_warnings(root, stage, meta))
    warnings.extend(_shot_variety_warnings(root, stage))
    errors.extend(_video_report_errors(root, stage))
    errors.extend(_picture_lock_errors(root, stage, meta))
    errors.extend(_timeline_contract_errors(root, stage, meta))
    errors.extend(_otio_contract_errors(root, stage, meta))
    errors.extend(_pacing_receipt_errors(root, stage, meta))
    errors.extend(_alignment_contract_errors(root, stage, meta))
    errors.extend(_semantic_prompt_errors(root, stage, meta))

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
        # 会冒充已选中且无 take/分记录。demo 可提醒，正式交付必须登记/评分/挑版。
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
                message = (
                    f"{len(unverified)} 个 clip 有成片视频但 jobs_manifest 无挑版记录"
                    f"（可能绕过 --select 手动放入）：{unverified[0]}…；先登记、具名评分并挑版。"
                )
                (warnings if meta.get("is_demo") else errors).append(message)

    errors.extend(_rights_errors(root, stage, meta))
    errors.extend(_staleness_errors(root, stage, meta))

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
