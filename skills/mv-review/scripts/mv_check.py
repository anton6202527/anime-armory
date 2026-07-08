#!/usr/bin/env python3
"""mv-review 机检 —— 对一支 MV 的产物做**确定性**质检（秒级、可复跑）。

覆盖确定性问题：
  卡点   —— beatgrid.json 可解析、BPM 合理(半/倍速嫌疑)、beats/downbeats 单调且在歌长内、
            beatgrid.duration vs 歌/song.* 时长一致。
  clip   —— (需 ffprobe) 每 clip 时长、clip 疑似等长(不卡点)、clip 总时长 ≈ 歌长。
  字幕   —— lyrics.lrc/karaoke.ass 占位未精修、时间单调/不重叠、时间越界(超歌长)、行数对账。
  规划   —— clip_plan/timeline/jobs manifest 可解析、clip 对账、timeline 总时长、selected video 对账。
  合成   —— (需 ffprobe) 成片存在、时长 ≈ 歌长、分辨率符 _meta.aspect、有音轨(MV 没声音=废)。
  合规   —— AI 视觉使用披露留痕。
  对账   —— 词/歌/beatgrid/出图/clip/成片 快照、_meta.has_song/has_lyrics vs 实际、段落数 vs structure。

**不覆盖**需要语义判断的维度（崩脸/场景漂移/画风/运镜服务节奏/卡点体感）——
那些走 references/checklist.md 的「人判」清单（崩脸并排读图）。输入歌的音质/词体检由项目外部来源保证，本脚本只查 MV 产物。

只用标准库；clip/成片 的时长·分辨率·音轨需 `ffprobe`，缺失时**显式标「跳过」**，绝不静默略过。
WAV 时长走标准库 wave，不依赖 ffprobe。

用法：
    python3 mv_check.py <制MV作品根> [--json] [--tol 2.0]
退出码：有 🔴 阻断级 → 1，否则 0。
"""
import sys, os, re, json, glob, wave, subprocess, shutil
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
MV_UTILS_PATH = os.path.join(REPO, "skills", "mv-craft", "scripts", "mv_utils.py")
PACING_PATH = os.path.join(REPO, "skills", "mv-craft", "scripts", "pacing.py")

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def load_mv_utils():
    return _load_module("mv_utils", MV_UTILS_PATH)

mv_utils = load_mv_utils()
pacing = _load_module("mv_pacing", PACING_PATH)   # 共享卡点/节奏/时长确定性引擎（与 mv-score 同源）

BLOCK, WARN, INFO = "🔴", "🟡", "🟢"
DUR_TOL = pacing.DUR_TOL    # 时长一致允许差（秒，或按 10% 取大）—— 单一真相源在 pacing.py
BPM_LO, BPM_HI = 50, 200   # 合理 BPM 区间（外则疑半/倍速）
EQUAL_CV = pacing.EQUAL_CV  # clip 时长极差/均值 低于此 → 疑似等长不卡点（同源 pacing.py）

findings = []  # (sev, dim, loc, msg)
def add(sev, dim, loc, msg): findings.append((sev, dim, loc, msg))

_HAVE_FFPROBE = None
def have_ffprobe():
    global _HAVE_FFPROBE
    if _HAVE_FFPROBE is None:
        _HAVE_FFPROBE = shutil.which("ffprobe") is not None
    return _HAVE_FFPROBE

def probe_duration(path):
    d = mv_utils.ffprobe_json(path, "-show_entries", "format=duration")
    try:
        return float(d.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        return None


def probe_video(path):
    """返回 (duration, w, h, has_audio) 或 None。"""
    d = mv_utils.ffprobe_json(path, "-show_entries", "format=duration", "-show_streams")
    streams = d.get("streams", [])
    if not streams:
        return None
    dur = None
    try:
        dur = float(d.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        pass
    w = h = None
    has_audio = False
    for s in streams:
        if s.get("codec_type") == "video" and w is None:
            w, h = s.get("width"), s.get("height")
        if s.get("codec_type") == "audio":
            has_audio = True
    return dur, w, h, has_audio


def tol(songlen):
    # 复用 pacing.duration_tol；DUR_TOL 可被 --tol 覆盖，故显式透传当前值
    return pacing.duration_tol(songlen, base_tol=DUR_TOL)


def check_completeness(root):
    for f in ("视觉蓝图.md", "_进度.md", "_meta.json"):
        if not os.path.exists(os.path.join(root, f)):
            add(WARN, "完整性", f, "缺文件")


def load_json_safe(path):
    try:
        return mv_utils.load_json(path)
    except Exception as e:
        add(BLOCK, "完整性", path, f"JSON 解析/加载失败：{e}")
        return None

def check_beatgrid(root, songlen):
    p = os.path.join(root, "节拍", "beatgrid.json")
    if not os.path.exists(p):
        add(WARN, "卡点", "节拍/beatgrid.json", "缺 beatgrid（未卡点则正常；无卡点 MV 节奏会平）")
        return None
    bg = load_json_safe(p)
    if bg is None:
        add(BLOCK, "卡点", "节拍/beatgrid.json", "beatgrid 损坏不可解析")
        return None
    bpm = bg.get("bpm")
    if isinstance(bpm, (int, float)) and not (BPM_LO <= bpm <= BPM_HI):
        add(WARN, "卡点", "beatgrid.json", f"BPM={bpm} 在 [{BPM_LO},{BPM_HI}] 外，疑半速/倍速——听一下校正")
    dur = bg.get("duration")
    for key in ("beats", "downbeats"):
        arr = bg.get(key) or []
        if not arr:
            add(WARN, "卡点", "beatgrid.json", f"{key} 为空")
            continue
        if any(arr[i] <= arr[i - 1] for i in range(1, len(arr))):
            add(WARN, "卡点", "beatgrid.json", f"{key} 非严格递增（时间戳乱序）")
        if dur and arr[-1] > dur + 0.5:
            add(WARN, "卡点", "beatgrid.json", f"{key} 末值 {arr[-1]:.2f} 超出 duration {dur:.2f}")
    if dur and songlen and abs(dur - songlen) > tol(songlen):
        add(WARN, "卡点", "beatgrid.json",
            f"beatgrid.duration {dur:.2f}s 与 歌长 {songlen:.2f}s 差大——歌换过却没重跑 mv-beat？")
    add(INFO, "卡点", "beatgrid.json",
        f"快照：BPM {bpm} · beats {len(bg.get('beats') or [])} · downbeats {len(bg.get('downbeats') or [])}")
    return bg


def check_clips(root, songlen):
    clips = sorted(glob.glob(os.path.join(root, "出视频", "视频", "*.mp4")))
    if not clips:
        add(INFO, "完整性", "出视频/视频", "无 clip（未出视频则正常）")
        return 0
    if not have_ffprobe():
        add(INFO, "卡点", "出视频/视频",
            f"clip 时长/卡点分析已跳过（未装 ffprobe）——{len(clips)} 个 clip 待 ffprobe 量时长。"
            "卡点体感暂由人判清单覆盖")
        return len(clips)
    durs = []
    for c in clips:
        d = probe_duration(c)
        if d:
            durs.append(d)
    # 等长检测复用 pacing.equal_length_cv（与 mv-score 同一引擎）；durs 来自 ffprobe，包成 clip_plan 形喂入
    cv, suspicious, n = pacing.equal_length_cv({"clips": [{"duration": d} for d in durs]})
    if suspicious:
        add(WARN, "卡点", "出视频/视频",
            f"{n} 个 clip 时长几乎一致（极差/均值={cv:.3f}）——疑似等长不卡点（MV 命门，回 mv-video 按 beatgrid 重定 clip 时长）")
    total = sum(durs)
    if songlen and abs(total - songlen) > tol(songlen):
        add(WARN, "卡点", "出视频/视频",
            f"clip 总时长 {total:.1f}s 与 歌长 {songlen:.1f}s 差大——回 mv-video 调 clip 或补空镜")
    add(INFO, "卡点", "出视频/视频", f"快照：{len(clips)} clip · 总时长 {total:.1f}s")
    return len(clips)


def _parse_lrc(path, lines_out):
    rx = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")
    for raw in open(path, encoding="utf-8"):
        if mv_utils.PLACEHOLDER.search(raw):
            add(BLOCK, "字幕", os.path.basename(path), f"字幕占位未精修：{raw.strip()[:30]}…")
        ts = rx.findall(raw)
        text = rx.sub("", raw).strip()
        for m, s in ts:
            lines_out.append((int(m) * 60 + float(s), None, text))


def _parse_ass(path, lines_out):
    for raw in open(path, encoding="utf-8"):
        if not raw.startswith("Dialogue:"):
            continue
        parts = raw.split(",", 9)
        if len(parts) < 10:
            continue
        try:
            st, en = mv_utils.parse_ass_time(parts[1].strip()), mv_utils.parse_ass_time(parts[2].strip())
        except Exception:
            continue
        text = re.sub(r"\{[^}]*\}", "", parts[9]).strip()
        if mv_utils.PLACEHOLDER.search(text):
            add(BLOCK, "字幕", os.path.basename(path), f"字幕占位未精修：{text[:30]}…")
        lines_out.append((st, en, text))


def check_subtitles(root, songlen, lyric_lines):
    lrc = os.path.join(root, "字幕", "lyrics.lrc")
    ass = os.path.join(root, "字幕", "karaoke.ass")
    lines = []
    src = None
    if os.path.exists(ass):
        _parse_ass(ass, lines); src = "karaoke.ass"
    elif os.path.exists(lrc):
        _parse_lrc(lrc, lines); src = "lyrics.lrc"
    else:
        add(INFO, "完整性", "字幕", "无卡拉OK字幕（未做字幕则正常）")
        return
    if not lines:
        add(WARN, "字幕", src, "未解析到字幕行")
        return
    # 单调
    for i in range(1, len(lines)):
        if lines[i][0] < lines[i - 1][0] - 0.05:
            add(WARN, "字幕", f"{src} 第{i+1}行", "起始时间早于上一行（乱序）")
        if lines[i - 1][1] and lines[i][0] < lines[i - 1][1] - 0.05:
            add(WARN, "字幕", f"{src} 第{i+1}行", "与上一行时间重叠")
    # 越界
    if songlen:
        for i, (st, en, _t) in enumerate(lines, 1):
            if st > songlen + 0.5 or (en and en > songlen + 0.5):
                add(WARN, "字幕", f"{src} 第{i}行", f"时间戳 {st:.1f}s 越界（超歌长 {songlen:.1f}s）")
    # 行数对账。demo/excerpt 可由 alignment_report 显式声明范围，避免 20s 样片被当作全曲漏行。
    report = mv_utils.load_json(os.path.join(root, "字幕", "alignment_report.json"), {}) or {}
    scope = str(report.get("scope") or "").lower()
    is_excerpt = scope in {"demo_excerpt", "excerpt", "sample"}
    if lyric_lines and abs(len(lines) - lyric_lines) > max(2, 0.3 * lyric_lines):
        if is_excerpt:
            add(INFO, "字幕", src, f"字幕行数({len(lines)}) 覆盖片段版；alignment_report.scope={scope}")
        else:
            add(WARN, "字幕", src, f"字幕行数({len(lines)}) 与 词行数({lyric_lines}) 差大——对齐可能漏/串行")
    add(INFO, "字幕", src, f"快照：{len(lines)} 行")


def check_alignment_report(root):
    path = os.path.join(root, "字幕", "alignment_report.json")
    if not os.path.exists(path):
        if os.path.exists(os.path.join(root, "字幕", "lyrics.lrc")) or os.path.exists(os.path.join(root, "字幕", "karaoke.ass")):
            add(WARN, "字幕", "字幕/alignment_report.json", "有字幕但缺对齐报告——建议重跑新版 mv-lyric-sync 便于 QA")
        return
    report = load_json_safe(path)
    if report is None:
        add(BLOCK, "字幕", "字幕/alignment_report.json", "对齐报告损坏不可解析")
        return
    warnings = report.get("warnings") or []
    for warning in warnings:
        add(WARN, "字幕", "字幕/alignment_report.json", f"对齐报告提示：{warning}")
    add(INFO, "字幕", "字幕/alignment_report.json",
        f"对齐快照：{report.get('aligned_lines', 0)}/{report.get('lyric_lines', 0)} 行 · unused={report.get('unused_word_segments', 0)}")


def check_plan_manifests(root, songlen):
    plan_path = os.path.join(root, "分镜", "clip_plan.json")
    timeline_path = os.path.join(root, "分镜", "timeline_manifest.json")
    if not os.path.exists(plan_path):
        add(WARN, "规划", "分镜/clip_plan.json", "缺 clip plan——建议先跑 mv-plan/scripts/plan_clips.py，避免出图/出视频/合成各自猜时间线")
        return
    plan = load_json_safe(plan_path)
    if plan is None:
        add(BLOCK, "规划", "分镜/clip_plan.json", "clip_plan 损坏不可解析")
        return
    clips = plan.get("clips") or []
    if not clips:
        add(WARN, "规划", "分镜/clip_plan.json", "clip_plan 里没有 clips")
        return
    plan_ids = [c.get("clip_id") for c in clips]
    if len(plan_ids) != len(set(plan_ids)):
        add(BLOCK, "规划", "分镜/clip_plan.json", "clip_id 重复")
    # 总时长 vs 歌长复用 pacing.planned_duration_vs_song（与 mv-score 同一引擎）
    total, _song, _diff, mismatch = pacing.planned_duration_vs_song(plan, songlen)
    if mismatch:
        add(WARN, "规划", "分镜/clip_plan.json", f"clip_plan 总时长 {total:.1f}s 与 歌长 {songlen:.1f}s 差大")
    add(INFO, "规划", "分镜/clip_plan.json", f"快照：{len(clips)} clips · 总时长 {total:.1f}s")
    if not os.path.exists(timeline_path):
        add(WARN, "规划", "分镜/timeline_manifest.json", "缺 timeline manifest——mv-compose 默认会阻断；需回 mv-plan/mv-video 补 timeline")
        return
    timeline = load_json_safe(timeline_path)
    if timeline is None:
        add(BLOCK, "规划", "分镜/timeline_manifest.json", "timeline_manifest 损坏不可解析")
        return
    tids = [c.get("clip_id") for c in (timeline.get("clips") or [])]
    if set(tids) != set(plan_ids):
        add(WARN, "规划", "分镜/timeline_manifest.json", "timeline clip_id 与 clip_plan 不一致")
    missing_video = [c.get("video_path") for c in (timeline.get("clips") or []) if c.get("video_path") and not os.path.exists(os.path.join(root, c["video_path"]))]
    if missing_video:
        add(WARN, "规划", "分镜/timeline_manifest.json", f"timeline 有 {len(missing_video)} 个 video_path 尚不存在（未出视频/未挑版则正常）")


def check_video_jobs(root):
    path = os.path.join(root, "出视频", "jobs_manifest.json")
    clips_exist = bool(glob.glob(os.path.join(root, "出视频", "视频", "*.mp4")))
    if not os.path.exists(path):
        if clips_exist:
            add(WARN, "规划", "出视频/jobs_manifest.json", "已有视频 clip 但缺 video jobs manifest——建议用 video_jobs.py 登记来源/挑版")
        return
    manifest = load_json_safe(path)
    if manifest is None:
        add(BLOCK, "规划", "出视频/jobs_manifest.json", "jobs_manifest 损坏不可解析")
        return
    jobs = manifest.get("jobs") or []
    selected = [j for j in jobs if j.get("selected_take")]
    add(INFO, "规划", "出视频/jobs_manifest.json", f"视频任务快照：{len(jobs)} jobs · 已选 {len(selected)}")
    for job in selected:
        p = job.get("selected_video_path")
        if p and not os.path.exists(os.path.join(root, p)):
            add(BLOCK, "规划", p, f"{job.get('clip_id')} selected_take 已选但成品 clip 不存在")


def check_consistency_artifacts(root, meta=None):
    identity_path = os.path.join(root, "设定", "identity_registry.json")
    asset_path = os.path.join(root, "设定", "asset_registry.json")
    reference_path = os.path.join(root, "分镜", "reference_plan.json")
    requirements_path = os.path.join(root, "设定", "reference_requirements.json")
    plan_exists = os.path.exists(os.path.join(root, "分镜", "clip_plan.json"))
    if plan_exists:
        for path, label in (
            (identity_path, "设定/identity_registry.json"),
            (asset_path, "设定/asset_registry.json"),
            (reference_path, "分镜/reference_plan.json"),
            (requirements_path, "设定/reference_requirements.json"),
        ):
            if not os.path.exists(path):
                add(WARN, "一致性", label, "缺身份/资产/参考注册产物——建议跑 mv-craft/scripts/identity_registry.py")
                continue
            payload = load_json_safe(path)
            if payload is None:
                add(BLOCK, "一致性", label, "JSON 损坏不可解析")
        identity = mv_utils.load_json(identity_path, {}) or {}
        refs = mv_utils.load_json(reference_path, {}) or {}
        if identity:
            groups = identity.get("reference_groups") or []
            ready = sum(1 for g in groups if g.get("status") == "ready")
            add(INFO, "一致性", "identity_registry.json", f"身份参考组：{ready}/{len(groups)} ready")
        if refs:
            rows = refs.get("clips") or []
            ready = sum(1 for r in rows if r.get("status") == "ready")
            add(INFO, "一致性", "reference_plan.json", f"clip 参考计划：{ready}/{len(rows)} ready")
        requirements = mv_utils.load_json(requirements_path, {}) or {}
        if requirements:
            rows = requirements.get("requirements") or []
            ready = sum(1 for r in rows if r.get("status") == "ready")
            partial = sum(1 for r in rows if r.get("status") == "partial")
            text_only = sum(1 for r in rows if r.get("status") == "text_only")
            planned = sum(1 for r in rows if r.get("status") == "planned")
            missing = [r for r in rows if r.get("status") != "ready"]
            critical_missing = [r for r in missing if r.get("type") in {"identity", "prop", "vfx"}]
            add(INFO, "一致性", "reference_requirements.json",
                f"正式参考图覆盖：ready={ready}/{len(rows)} · partial={partial} · text_only={text_only} · planned={planned}")
            if critical_missing and not (meta or {}).get("is_demo"):
                names = ", ".join(str(r.get("target_id")) for r in critical_missing[:6])
                add(WARN, "一致性", "reference_requirements.json", f"正式项目关键参考图未齐：{names}")

    inherit_path = os.path.join(root, "生产数据", "video_inherit_contract", "inherit_contract.json")
    video_qc_path = os.path.join(root, "生产数据", "video_qc", "video_qc.json")
    videos_exist = bool(glob.glob(os.path.join(root, "出视频", "视频", "*.mp4")))
    if videos_exist or os.path.exists(os.path.join(root, "出视频", "jobs_manifest.json")):
        for path, label, kind in (
            (inherit_path, "生产数据/video_inherit_contract/inherit_contract.json", "继承合约"),
            (video_qc_path, "生产数据/video_qc/video_qc.json", "视频QC"),
        ):
            if not os.path.exists(path):
                add(WARN, "一致性", label, f"缺 {kind} 报告——建议跑 mv-video/scripts/{'inherit_contract.py' if 'inherit' in label else 'video_qc.py'}")
                continue
            payload = load_json_safe(path)
            if payload is None:
                add(BLOCK, "一致性", label, f"{kind} JSON 损坏不可解析")
                continue
            summary = payload.get("summary") or {}
            verdict = summary.get("verdict")
            hard = int(summary.get("hard_blocks") or 0)
            warn = int(summary.get("warnings") or 0)
            if hard:
                add(BLOCK, "一致性", label, f"{kind} hard_blocks={hard}")
            elif warn:
                add(WARN, "一致性", label, f"{kind} verdict={verdict} warnings={warn}")
            else:
                add(INFO, "一致性", label, f"{kind} verdict={verdict}")


def check_production_pack(root, meta):
    plan_exists = os.path.exists(os.path.join(root, "分镜", "clip_plan.json"))
    if not plan_exists:
        return
    expected = [
        ("分镜/animatic_manifest.json", "animatic manifest"),
        ("制片/shot_list.json", "shot list"),
        ("制片/setup_schedule.md", "setup schedule"),
        ("制片/take_log.csv", "take log"),
        ("制片/picture_lock_color_checklist.md", "picture lock/color checklist"),
    ]
    missing = [rel for rel, _label in expected if not os.path.exists(os.path.join(root, rel))]
    if missing:
        sev = INFO if (meta or {}).get("is_demo") else WARN
        add(sev, "制片", "production_pack", f"传统制片包缺 {len(missing)} 项：{', '.join(missing)}")
        return
    shot_list = load_json_safe(os.path.join(root, "制片", "shot_list.json"))
    animatic = load_json_safe(os.path.join(root, "分镜", "animatic_manifest.json"))
    if shot_list is None or animatic is None:
        return
    shots = shot_list.get("shots") if isinstance(shot_list, dict) else shot_list
    anim_clips = animatic.get("clips") if isinstance(animatic, dict) else []
    add(INFO, "制片", "production_pack",
        f"传统制片包已齐：shot_list={len(shots or [])} · animatic={len(anim_clips or [])} clips")


def check_formal_readiness(root, meta):
    path = os.path.join(root, "生产数据", "formal_readiness", "formal_readiness.json")
    if not os.path.exists(path):
        if meta and meta.get("is_demo"):
            add(INFO, "正式版", "formal_readiness.json", "当前为 demo；可跑 mv-craft/scripts/formal_readiness.py 生成正式版缺口清单")
        return
    payload = load_json_safe(path)
    if payload is None:
        add(BLOCK, "正式版", "formal_readiness.json", "正式版 readiness JSON 损坏不可解析")
        return
    summary = payload.get("summary") or {}
    status = summary.get("status")
    blockers = int(summary.get("blockers") or 0)
    warnings = int(summary.get("warnings") or 0)
    msg = f"formal readiness status={status} · blockers={blockers} · warnings={warnings}"
    if status == "blocked" and not (meta or {}).get("is_demo"):
        add(WARN, "正式版", "formal_readiness.json", msg)
    else:
        add(INFO, "正式版", "formal_readiness.json", msg)


def check_final(root, meta, songlen):
    finals = glob.glob(os.path.join(root, "成片_*.mp4")) + glob.glob(os.path.join(root, "成片*.mp4"))
    finals = sorted(set(finals))
    composed = bool(re.search(r"成片|合成|mv-compose", open(os.path.join(root, "_进度.md"), encoding="utf-8").read())) \
        if os.path.exists(os.path.join(root, "_进度.md")) else False
    if not finals:
        add(WARN if composed else INFO, "音画", "成片_MV.mp4",
            "缺成片" + ("（进度标已合成却找不到成片）" if composed else "（未合成则正常）"))
        return
    final = finals[0]
    if not have_ffprobe():
        add(INFO, "音画", os.path.basename(final),
            "成片 时长/画幅/音轨检查已跳过（未装 ffprobe）——成片存在但未量化")
        return
    info = probe_video(final)
    if info is None:
        add(BLOCK, "音画", os.path.basename(final), "成片不可解析/损坏")
        return
    dur, w, h, has_audio = info
    if not has_audio:
        add(BLOCK, "音画", os.path.basename(final), "成片无音轨——MV 没声音=废，回 mv-compose 重铺 歌/song.* 主音轨")
    if dur and songlen and abs(dur - songlen) > tol(songlen):
        add(WARN, "音画", os.path.basename(final), f"成片时长 {dur:.1f}s 与 歌长 {songlen:.1f}s 差大")
    # 画幅
    aspect = (meta or {}).get("aspect")
    if aspect and w and h:
        m = re.match(r"(\d+)\s*[:：]\s*(\d+)", str(aspect))
        if m:
            exp = int(m.group(1)) / int(m.group(2))
            act = w / h
            if abs(exp - act) / exp > 0.05:
                add(WARN, "音画", os.path.basename(final),
                    f"成片画幅 {w}x{h}(≈{act:.3f}) 与 _meta.aspect {aspect}(≈{exp:.3f}) 不符")
    add(INFO, "音画", os.path.basename(final),
        f"快照：{dur:.1f}s · {w}x{h} · {'有音轨' if has_audio else '无音轨'}")


def check_ai_usage(root):
    finals = glob.glob(os.path.join(root, "成片_*.mp4")) + glob.glob(os.path.join(root, "成片*.mp4"))
    path = os.path.join(root, "合规", "ai_usage.json")
    if not finals:
        return
    if not os.path.exists(path):
        add(WARN, "合规", "合规/ai_usage.json",
            "已有成片但缺 AI 视觉使用披露——发布/交平台前跑 mv-craft/scripts/ai_usage.py")
        return
    payload = load_json_safe(path)
    if payload is None:
        add(BLOCK, "合规", "合规/ai_usage.json", "AI 使用披露 JSON 损坏不可解析")
        return
    mode = payload.get("visual_mode")
    if mode not in ("AI-generated", "AI-assisted", "未使用AI视觉"):
        add(WARN, "合规", "合规/ai_usage.json", f"visual_mode 不在约定枚举内：{mode}")
    else:
        add(INFO, "合规", "合规/ai_usage.json", f"AI 视觉使用披露：visual_mode={mode}")


def check_lyrics_and_meta(root, meta):
    # 词占位 + 段落数 vs structure
    ly = os.path.join(root, "词", "lyrics.md")
    lyric_lines = 0
    if os.path.exists(ly):
        sec = 0
        for raw in open(ly, encoding="utf-8"):
            if mv_utils.PLACEHOLDER.search(raw):
                add(BLOCK, "字幕", "词/lyrics.md", f"歌词占位未精修：{raw.strip()[:30]}…")
            s = raw.strip()
            if re.match(r"^\[[^\]]+\]$", s):
                sec += 1
            elif s and not s.startswith("#") and not s.startswith(">") and not re.match(r"^[（(].*[）)]$", s):
                lyric_lines += 1
        if meta and isinstance(meta.get("structure"), list) and sec and sec != len(meta["structure"]):
            add(WARN, "完整性", "词/lyrics.md",
                f"段落数({sec}) ≠ _meta.structure({len(meta['structure'])})")
    # has_song / has_lyrics 对账
    if meta is not None:
        song_exists = any(os.path.exists(os.path.join(root, "歌", f"song{e}")) for e in (".wav", ".mp3", ".flac", ".m4a"))
        if meta.get("has_song") is False and song_exists:
            add(WARN, "完整性", "_meta.has_song", "标 false 但 歌/song.* 已就位（meta 未更新）")
        if meta.get("has_song") is True and not song_exists:
            add(WARN, "完整性", "_meta.has_song", "标 true 但找不到 歌/song.*")
        if meta.get("has_lyrics") is False and os.path.exists(ly):
            add(WARN, "完整性", "_meta.has_lyrics", "标 false 但 词/lyrics.md 已就位（meta 未更新）")
    return lyric_lines


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = [a for a in sys.argv[1:] if a.startswith("--")]
    if len(args) < 1:
        print("用法：python3 mv_check.py <制MV作品根> [--json] [--tol 2.0]"); sys.exit(2)
    root = args[0]
    global DUR_TOL
    DUR_TOL = next((float(o.split("=")[1]) for o in opts if o.startswith("--tol=")), DUR_TOL)
    if not os.path.isdir(root):
        print(f"作品根不存在：{root}"); sys.exit(2)

    meta = load_json_safe(os.path.join(root, "_meta.json"))
    song_path = mv_utils.find_song(root)
    songlen = mv_utils.audio_duration(song_path) if song_path else None

    check_completeness(root)
    lyric_lines = check_lyrics_and_meta(root, meta)
    check_beatgrid(root, songlen)
    check_plan_manifests(root, songlen)
    check_video_jobs(root)
    check_consistency_artifacts(root, meta)
    check_production_pack(root, meta)
    check_formal_readiness(root, meta)
    check_clips(root, songlen)
    check_subtitles(root, songlen, lyric_lines)
    check_alignment_report(root)
    check_final(root, meta, songlen)
    check_ai_usage(root)
    if songlen:
        add(INFO, "音画", mv_utils.relpath(root, song_path), f"歌长基准：{songlen:.2f}s")

    if "--json" in opts:
        print(json.dumps([{"sev": s, "dim": d, "loc": l, "msg": m}
                          for s, d, l, m in findings], ensure_ascii=False, indent=2))
    else:
        order = {BLOCK: 0, WARN: 1, INFO: 2}
        nb = sum(1 for f in findings if f[0] == BLOCK)
        nw = sum(1 for f in findings if f[0] == WARN)
        ni = sum(1 for f in findings if f[0] == INFO)
        print(f"\n=== mv-review 机检：{root} ===")
        print(f"🔴 阻断 {nb} · 🟡 建议 {nw} · 🟢 信息 {ni}"
              + ("" if have_ffprobe() else "　（未装 ffprobe：clip/成片 时长·画幅·音轨 = 跳过）") + "\n")
        for s, d, l, m in sorted(findings, key=lambda f: order[f[0]]):
            print(f"{s} [{d}] {l}: {m}")
        print("\n（语义维度——崩脸/场景漂移/画风/运镜服务节奏/卡点体感——见 references/checklist.md 人判清单）")
    sys.exit(1 if any(f[0] == BLOCK for f in findings) else 0)


if __name__ == "__main__":
    main()
