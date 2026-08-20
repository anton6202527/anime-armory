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
    python3 mv_check.py <制MV作品根> --write-receipt --reviewer <真实姓名> --notes <审片结论>

默认严格只读。只有显式 ``--write-receipt`` 且机器无阻断，并由 completion 复算
compose / disclosure / provenance 及已进入的 image / video_jobs / video 健康度均无错误时，
才写具名 ``生产数据/review/review_receipt.json``。
退出码：有 🔴 阻断级 → 1，否则 0。
"""
import argparse
from datetime import datetime
import sys, os, re, json, glob, wave, subprocess, shutil
import importlib.util
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
MV_UTILS_PATH = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "mv_utils.py")
PACING_PATH = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "pacing.py")
CONTRACT_PATH = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "contract.py")
COMPLETION_PATH = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "completion.py")
ALIGNMENT_PATH = os.path.join(REPO, "skills", "mv", "mv-lyric-sync", "scripts", "align.py")
IMAGE_RECEIPTS_PATH = os.path.join(REPO, "skills", "mv", "mv-image", "scripts", "image_receipts.py")

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def load_mv_utils():
    return _load_module("mv_utils", MV_UTILS_PATH)

mv_utils = load_mv_utils()
pacing = _load_module("mv_pacing", PACING_PATH)   # 共享卡点/节奏/时长确定性引擎（与 mv-score 同源）
contract = _load_module("mv_review_contract", CONTRACT_PATH)
_ALIGNMENT_MODULE = None
_IMAGE_RECEIPTS_MODULE = None
_COMPLETION_MODULE = None


def _load_alignment_module():
    """Load the producer's schema validator so review cannot drift from schema v5."""
    global _ALIGNMENT_MODULE
    if _ALIGNMENT_MODULE is None:
        _ALIGNMENT_MODULE = _load_module("mv_review_alignment_schema", ALIGNMENT_PATH)
    return _ALIGNMENT_MODULE


def _load_image_receipts():
    """Load the authoritative B14 ledger auditor (read-only in mv-review)."""
    global _IMAGE_RECEIPTS_MODULE
    if _IMAGE_RECEIPTS_MODULE is None:
        _IMAGE_RECEIPTS_MODULE = _load_module("mv_review_image_receipts", IMAGE_RECEIPTS_PATH)
    return _IMAGE_RECEIPTS_MODULE


def _load_completion_module():
    """Load the authoritative stage-health controller only when sign-off needs it."""
    global _COMPLETION_MODULE
    if _COMPLETION_MODULE is None:
        craft_scripts = os.path.dirname(COMPLETION_PATH)
        if craft_scripts not in sys.path:
            sys.path.insert(0, craft_scripts)
        _COMPLETION_MODULE = _load_module("mv_completion_from_review", COMPLETION_PATH)
    return _COMPLETION_MODULE

BLOCK, WARN, INFO = "🔴", "🟡", "🟢"
DUR_TOL = pacing.DUR_TOL    # 时长一致允许差（秒，或按 10% 取大）—— 单一真相源在 pacing.py
BPM_LO, BPM_HI = 50, 200   # 合理 BPM 区间（外则疑半/倍速）
EQUAL_CV = pacing.EQUAL_CV  # clip 时长极差/均值 低于此 → 疑似等长不卡点（同源 pacing.py）

findings = []  # (sev, dim, loc, msg)
def add(sev, dim, loc, msg): findings.append((sev, dim, loc, msg))

REVIEW_RECEIPT_REL = "生产数据/review/review_receipt.json"
REVIEW_INPUTS = (
    "成片_MV.mp4",
    "成片_MV_master.mov",
    "生产数据/delivery_qc/delivery_qc.json",
    "合规/provenance.json",
    "合规/ai_usage.json",
)

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
    meta = mv_utils.load_json(os.path.join(root, "_meta.json"), {}) or {}
    song = mv_utils.find_song(root)
    recorded_song = bg.get("source_audio_sha256")
    if recorded_song and recorded_song != mv_utils.content_hash(song):
        add(BLOCK, "卡点", "beatgrid.json", "source_audio_sha256 与当前歌曲不一致；节拍证据已失效")
    elif not recorded_song and not meta.get("is_demo"):
        add(BLOCK, "卡点", "beatgrid.json", "正式项目缺 source_audio_sha256，不能证明节拍来自当前歌曲")
    if not meta.get("is_demo"):
        if not bg.get("downbeats_verified") or not bg.get("sections_verified") or not bg.get("sections_complete"):
            add(BLOCK, "卡点", "beatgrid.json", "正式项目小节首/段落边界未完整具名签收")
    if isinstance(bpm, (int, float)) and not (BPM_LO <= bpm <= BPM_HI):
        add(WARN, "卡点", "beatgrid.json", f"BPM={bpm} 在 [{BPM_LO},{BPM_HI}] 外，疑半速/倍速——听一下校正")
    dur = bg.get("duration")
    for key in ("beats", "downbeats"):
        arr = bg.get(key) or []
        if not arr:
            add(BLOCK if not meta.get("is_demo") else WARN, "卡点", "beatgrid.json", f"{key} 为空")
            continue
        if any(arr[i] <= arr[i - 1] for i in range(1, len(arr))):
            add(BLOCK, "卡点", "beatgrid.json", f"{key} 非严格递增（时间戳乱序）")
        if dur and arr[-1] > dur + 0.5:
            add(WARN, "卡点", "beatgrid.json", f"{key} 末值 {arr[-1]:.2f} 超出 duration {dur:.2f}")
    if dur and songlen and abs(dur - songlen) > tol(songlen):
        add(BLOCK, "卡点", "beatgrid.json",
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
        meta = mv_utils.load_json(os.path.join(root, "_meta.json"), {}) or {}
        runtime = contract.runtime_state_from_settings(mv_utils.parse_settings(root))
        formal_alignment_required = bool(
            not meta.get("is_demo")
            and (
                runtime.get("subtitle_language") != "无字幕"
                or runtime.get("lip_sync_mode") != "关闭"
            )
        )
        has_subtitle_output = bool(
            os.path.exists(os.path.join(root, "字幕", "lyrics.lrc"))
            or os.path.exists(os.path.join(root, "字幕", "karaoke.ass"))
        )
        if formal_alignment_required:
            add(BLOCK, "字幕", "字幕/alignment_report.json",
                "正式字幕/演唱口型缺当前 schema v5 对齐报告；不能进入正式审片签收")
        elif has_subtitle_output:
            add(WARN, "字幕", "字幕/alignment_report.json",
                "有字幕但缺对齐报告——建议重跑新版 mv-lyric-sync 便于 QA")
        return
    report = load_json_safe(path)
    if report is None:
        add(BLOCK, "字幕", "字幕/alignment_report.json", "对齐报告损坏不可解析")
        return
    warnings = report.get("warnings") or []
    for warning in warnings:
        add(WARN, "字幕", "字幕/alignment_report.json", f"对齐报告提示：{warning}")
    errors = []
    if report.get("kind") != "mv_lyric_alignment_report" or report.get("schema_version") != 5:
        errors.append("alignment_report 必须是当前 schema v5 mv_lyric_alignment_report")
    if "alignment_confidence" in report:
        errors.append("schema v5 禁止 alignment_confidence；character_coverage_ratio 只表示文本覆盖")
    if report.get("coverage_metric") != "text_character_mapping_ratio_not_acoustic_confidence":
        errors.append("schema v5 必须明确字符覆盖率不是声学置信度")
    acceptance = report.get("acceptance") or {}
    if acceptance.get("status") != "accepted" or acceptance.get("accepted") is not True:
        errors.append("alignment_report 尚未正式接受；pending/旧报告不能进入正式验收")
    try:
        alignment = _load_alignment_module()
        errors.extend(alignment.acceptance_errors(root, report))
        gate = alignment.mv_gate
        if report.get("alignment_unit") != "character":
            errors.append("alignment_report 不是字符级强制对齐")
        errors.extend(gate._alignment_stem_timing_errors(root, report))
        expected_binding = gate._alignment_acceptance_binding(root, report)
        if acceptance.get("binding") != expected_binding:
            errors.append("alignment_report 尚未以当前 master/stem/lyrics/ASS/LRC/report binding 正式接受")
        route = acceptance.get("route")
        if route == "singing_acoustic_evidence":
            lyric_lines = report.get("lyric_lines")
            if isinstance(lyric_lines, bool) or not isinstance(lyric_lines, int):
                lyric_lines = 0
            if not gate._alignment_acoustic_valid(report, expected_binding, lyric_lines):
                errors.append("singing acoustic evidence 未校准、非 singing-specific、不可正式验收、"
                              "未逐行覆盖或未绑定当前 inputs/outputs")
        elif route == "named_listening_review":
            manual = report.get("manual_review") or {}
            manual_current = bool(
                manual.get("accepted") is True
                and manual.get("kind") == "named_full_listening_review"
                and manual.get("verdict") == "pass"
                and gate._valid_named_reviewer(manual.get("reviewer"))
                and str(manual.get("notes") or "").strip()
                and manual.get("bound_inputs_sha256") == report.get("inputs_sha256")
                and manual.get("bound_outputs_sha256") == report.get("outputs_sha256")
                and manual.get("binding") == expected_binding
                and manual.get("bound_report_preaccept_sha256")
                == expected_binding.get("report_preaccept_content_sha256")
            )
            if not manual_current:
                errors.append("具名逐行 listening review 未绑定当前 inputs/outputs/report 前置内容")
    except Exception as exc:
        errors.append(f"schema v5 验收复算失败：{exc}")
    for message in dict.fromkeys(str(item) for item in errors if str(item).strip()):
        add(BLOCK, "字幕", "字幕/alignment_report.json", message)
    coverage = report.get("character_coverage_ratio")
    add(INFO, "字幕", "字幕/alignment_report.json",
        f"对齐快照：{report.get('aligned_lines', 0)}/{report.get('lyric_lines', 0)} 行 · "
        f"character_coverage_ratio={coverage}（仅文本字符映射覆盖率，不是声学置信度） · "
        f"acceptance={((report.get('acceptance') or {}).get('status') or 'missing')}")


def check_image_acceptance(root):
    """Recompute B14 from current pixels, full image QC and the authoritative ledger."""
    plan_path = os.path.join(root, "分镜", "clip_plan.json")
    qc_rel = "生产数据/image_qc/image_qc.json"
    ledger_rel = "生产数据/image_acceptance/image_acceptance.json"
    qc_path = os.path.join(root, qc_rel)
    ledger_path = os.path.join(root, ledger_rel)
    if not (os.path.exists(plan_path) or os.path.exists(qc_path) or os.path.exists(ledger_path)):
        return
    qc = load_json_safe(qc_path) if os.path.exists(qc_path) else None
    if not isinstance(qc, dict) or qc.get("kind") != "mv_image_qc":
        add(BLOCK, "一致性", qc_rel, "缺或损坏当前 mv_image_qc 聚合报告；B14 不接受降级人工替代")
        qc = {}
    version = qc.get("version", qc.get("schema_version"))
    try:
        version_ok = not isinstance(version, bool) and int(version) >= 3
    except (TypeError, ValueError):
        version_ok = False
    if not version_ok:
        add(BLOCK, "一致性", qc_rel, "image_qc 必须是当前 v3+ 聚合报告")
    summary = qc.get("summary") or {}
    if summary.get("hard_blocks") != 0 or summary.get("verdict") != "ok":
        add(BLOCK, "一致性", qc_rel,
            f"image_qc 未以 full/ok 通过：verdict={summary.get('verdict')!r} · hard_blocks={summary.get('hard_blocks')!r}")
    precision = (qc.get("qc_environment") or {}).get("precision_level")
    if precision != "full":
        add(BLOCK, "一致性", qc_rel,
            f"image_qc precision_level={precision!r}；degraded/manual_review/--accept-degraded 均不能放行 B14")
    assets_sha = qc.get("assets_sha256") or {}
    if not isinstance(assets_sha, dict) or not assets_sha:
        add(BLOCK, "一致性", qc_rel, "image_qc 缺 assets_sha256，不能证明检查的是当前像素")
        assets_sha = {}
    for rel, recorded in assets_sha.items():
        if mv_utils.content_hash(os.path.join(root, str(rel))) != recorded:
            add(BLOCK, "一致性", qc_rel, f"image_qc 当前像素绑定已过期：{rel}")
    provenance = qc.get("generation_provenance") or {}
    if provenance.get("complete") is not True or (provenance.get("summary") or {}).get("block") != 0:
        add(BLOCK, "一致性", qc_rel, "image_qc generation_provenance 必须 complete 且 block=0")
    if not os.path.isfile(ledger_path):
        add(BLOCK, "一致性", ledger_rel, "缺权威 image_acceptance ledger；旧 image_qc/manual_review 不能证明逐图验收")
        return
    ledger = load_json_safe(ledger_path)
    if not isinstance(ledger, dict) or ledger.get("kind") != "mv_image_acceptance_ledger":
        add(BLOCK, "一致性", ledger_rel, "image_acceptance ledger kind/schema 损坏")
        return
    try:
        audit = _load_image_receipts().audit_ledger(Path(root), ledger=ledger)
    except Exception as exc:
        add(BLOCK, "一致性", ledger_rel, f"image_acceptance ledger 无法按当前像素复算：{exc}")
        return
    rows = audit.get("rows") or []
    audit_summary = audit.get("summary") or {}
    if audit_summary.get("all_current_accepted") is not True:
        add(BLOCK, "一致性", ledger_rel,
            f"B14 未完成：accepted={audit_summary.get('accepted', 0)}/{audit_summary.get('expected', 0)} · "
            f"stale={audit_summary.get('stale', 0)}")
    for row in rows:
        if row.get("status") != "accepted":
            add(BLOCK, "一致性", ledger_rel,
                f"逐图验收失效：{row.get('asset')} ({','.join(str(x) for x in row.get('findings') or []) or 'unknown'})")
    audited_assets = {str(row.get("asset")) for row in rows if row.get("asset")}
    if set(map(str, assets_sha)) != audited_assets:
        add(BLOCK, "一致性", qc_rel, "image_qc 资产全集与 image_acceptance 动态审计全集不一致")
    if (audit_summary.get("all_current_accepted") is True and precision == "full"
            and summary.get("verdict") == "ok" and summary.get("hard_blocks") == 0
            and set(map(str, assets_sha)) == audited_assets):
        add(INFO, "一致性", ledger_rel,
            f"B14 当前像素逐图验收有效：{audit_summary.get('accepted', 0)}/{audit_summary.get('expected', 0)}")


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
        take = next((row for row in job.get("takes", []) if row.get("take_id") == job.get("selected_take")), {})
        score = take.get("score") or {}
        missing_scores = [key for key in ("motion", "identity", "beat_fit", "clarity") if not isinstance(score.get(key), (int, float))]
        if missing_scores and not take.get("selection_waiver"):
            add(BLOCK, "规划", path, f"{job.get('clip_id')} 已挑版但缺评分：{', '.join(missing_scores)}")


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
        variety = mv_utils.load_json(os.path.join(root, "生产数据", "shot_variety", "shot_variety.json"), {}) or {}
        if variety:
            vs = variety.get("summary") or {}
            vwarn = int(vs.get("warn") or 0)
            if vwarn:
                codes = sorted({str(f.get("code")) for f in (variety.get("findings") or []) if f.get("severity") == "warn"})
                add(WARN, "一致性", "shot_variety.json",
                    f"视觉多样性事前机检 advisory={vwarn}（{'/'.join(codes) or 'n/a'}）——同构图反复/景别单调/副歌静镜/场景滞留/缺参考锚，回 mv-plan 调分镜")
            else:
                add(INFO, "一致性", "shot_variety.json", f"视觉多样性事前机检无重复/单调项（clips={vs.get('clips_checked')}）")
        elif not (meta or {}).get("is_demo"):
            add(INFO, "一致性", "shot_variety.json", "未跑视觉多样性事前机检（shot_variety_audit）——出图前建议补跑，拦同构图反复/副歌静镜")
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
                severity = INFO if (meta or {}).get("is_demo") else BLOCK
                add(severity, "一致性", label, f"缺 {kind} 报告——运行 mv-video/scripts/{'inherit_contract.py' if 'inherit' in label else 'video_qc.py'}")
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
            stale = [rel for rel, recorded in (payload.get("inputs_sha256") or {}).items()
                     if mv_utils.content_hash(os.path.join(root, rel)) != recorded]
            if stale:
                add(BLOCK, "一致性", label, f"{kind} 报告已过期，输入已变化：{stale[0]}")
            if kind == "视频QC":
                stale_video = [rel for rel, recorded in (payload.get("selected_video_sha256") or {}).items()
                               if mv_utils.content_hash(os.path.join(root, rel)) != recorded]
                if stale_video:
                    add(BLOCK, "一致性", label, f"视频 QC 未绑定当前选中视频：{stale_video[0]}")
            if kind == "视频QC" and not (meta or {}).get("is_demo"):
                semantic = payload.get("semantic_review") or {}
                if not semantic.get("accepted"):
                    add(BLOCK, "一致性", label, "正式项目视频语义人工复核尚未签收")
                elif semantic.get("bound_video_sha256") != (payload.get("selected_video_sha256") or {}):
                    add(BLOCK, "一致性", label, "视频语义签收未绑定当前 selected video hashes")
                seam_hash = mv_utils.json_hash([
                    seam.get("seam_contract") or {} for seam in payload.get("seams") or []
                ])
                if semantic.get("accepted") and semantic.get("bound_seam_contract_sha256") != seam_hash:
                    add(BLOCK, "一致性", label, "视频语义签收未绑定当前接缝分类合同")


def check_production_pack(root, meta):
    plan_exists = os.path.exists(os.path.join(root, "分镜", "clip_plan.json"))
    if not plan_exists:
        return
    expected = [
        ("分镜/animatic_manifest.json", "animatic manifest"),
        ("分镜/animatic.mp4", "reviewable animatic"),
        ("分镜/timeline.otio", "OpenTimelineIO timeline"),
        ("生产数据/otio/otio_receipt.json", "OTIO hash receipt"),
        ("制片/shot_list.json", "shot list"),
        ("制片/setup_schedule.md", "setup schedule"),
        ("制片/take_log.csv", "take log"),
        ("制片/picture_lock_color_checklist.md", "picture lock/color checklist"),
        ("制片/finishing_delivery_checklist.md", "finishing/delivery checklist"),
        ("制片/picture_lock.json", "signed picture lock"),
    ]
    missing = [rel for rel, _label in expected if not os.path.exists(os.path.join(root, rel))]
    if missing:
        sev = INFO if (meta or {}).get("is_demo") else BLOCK
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
        else:
            add(BLOCK, "正式版", "formal_readiness.json", "正式项目缺 formal readiness 报告")
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
        add(BLOCK, "正式版", "formal_readiness.json", msg)
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


def c2pa_status_dimensions(provenance):
    """Return C2PA dimensions without collapsing valid/trusted/timestamped.

    A structurally valid claim may still be signed with a test certificate,
    untrusted, or missing a timestamp.  Keeping these booleans separate avoids
    presenting "c2patool returned 0" as production trust.
    """
    c2pa = (provenance or {}).get("c2pa") or {}
    profile = str(c2pa.get("certificate_profile") or "")
    return {
        "requested": c2pa.get("requested") is True,
        "embedded": c2pa.get("embedded") is True,
        "structurally_valid": c2pa.get("structurally_valid") is True,
        "signature_valid": c2pa.get("signature_valid") is True,
        "trust_checked": c2pa.get("trust_checked") is True,
        "trusted": c2pa.get("trusted") is True,
        "test_certificate": profile.lower().startswith("test"),
        "certificate_profile": profile or None,
        "timestamp_validated": c2pa.get("timestamp_validated") is True,
        "timestamp_trusted": c2pa.get("timestamp_trusted") is True,
        "timestamped": c2pa.get("timestamped") is True,
        "timestamp_exception_allowed": c2pa.get("timestamp_exception_allowed") is True,
        "output": c2pa.get("output"),
        "output_sha256": c2pa.get("output_sha256"),
    }


def c2pa_release_errors(root, provenance):
    """Hard failures when C2PA was explicitly requested for this delivery."""
    status = c2pa_status_dimensions(provenance)
    if not status["requested"]:
        return []
    errors = []
    for key, label in (
        ("embedded", "未嵌入 signed asset"),
        ("structurally_valid", "结构校验未通过"),
        ("signature_valid", "签名校验未通过"),
    ):
        if not status[key]:
            errors.append(f"C2PA {label}")
    if status["test_certificate"]:
        errors.append("C2PA 使用 test certificate，只能开发验证，不能作为生产可信凭证")
    if not status["trust_checked"]:
        errors.append("C2PA 未执行 trust anchors 校验，不能声称 trusted")
    elif not status["trusted"]:
        errors.append("C2PA 签名未获信任链验证")
    if status["timestamped"] != status["timestamp_trusted"]:
        errors.append("C2PA timestamped 与 timestamp_trusted 不一致")
    if status["timestamp_trusted"] and not status["timestamp_validated"]:
        errors.append("C2PA timestamp_trusted=true 但缺 timestamp_validated 证据")
    if not status["timestamp_trusted"] and not status["timestamp_exception_allowed"]:
        errors.append("C2PA 缺可信 TSA 时间戳，且未记录显式 no-timestamp 例外")
    output = str(status.get("output") or "")
    if not output:
        errors.append("C2PA requested 但 provenance 未记录 signed output")
    else:
        output_path = os.path.abspath(os.path.join(root, output))
        try:
            inside = os.path.commonpath((os.path.abspath(root), output_path)) == os.path.abspath(root)
        except ValueError:
            inside = False
        current = mv_utils.content_hash(output_path) if inside else ""
        if not inside:
            errors.append("C2PA signed output 指向作品根之外")
        elif not current or current != status.get("output_sha256"):
            errors.append("C2PA signed output 不存在或当前 SHA-256 与验证记录不符")
    return errors


def check_c2pa_status(root, provenance):
    status = c2pa_status_dimensions(provenance)
    if not status["requested"]:
        add(INFO, "C2PA", "合规/provenance.json", "C2PA 未请求（可选）；平台 AI 披露仍由 ai_usage 独立检查")
        return status
    add(INFO if status["embedded"] else BLOCK, "C2PA", "embedded",
        f"embedded={status['embedded']}")
    add(INFO if status["structurally_valid"] else BLOCK, "C2PA", "structural",
        f"structurally_valid={status['structurally_valid']}")
    add(INFO if status["signature_valid"] else BLOCK, "C2PA", "signature",
        f"signature_valid={status['signature_valid']}")
    if status["test_certificate"]:
        add(BLOCK, "C2PA", "certificate_profile",
            "certificate_profile=test_untrusted；仅开发验证，绝不等于 production trusted")
    else:
        add(INFO, "C2PA", "certificate_profile",
            f"certificate_profile={status['certificate_profile'] or 'not_recorded'} · test_certificate=false")
    if not status["trust_checked"]:
        add(BLOCK, "C2PA", "trust", "trust_checked=false；未核 trust anchors，不能声称 trusted")
    elif not status["trusted"]:
        add(BLOCK, "C2PA", "trust", "trusted=false；签名有效也不等于发布方可信")
    else:
        add(INFO, "C2PA", "trust", "trust_checked=true · trusted=true")
    timestamp_ok = status["timestamp_validated"] and status["timestamp_trusted"] and status["timestamped"]
    timestamp_severity = INFO if timestamp_ok else (WARN if status["timestamp_exception_allowed"] else BLOCK)
    add(timestamp_severity, "C2PA", "timestamp",
        f"validated={status['timestamp_validated']} · trusted={status['timestamp_trusted']} · "
        f"exception={status['timestamp_exception_allowed']}"
        + ("" if timestamp_ok else "；普通 signature_info.time 不等于可信 TSA 时间戳"))
    for message in c2pa_release_errors(root, provenance):
        # The dimension-specific messages above own structural/signature/trust.
        if "signed output" in message:
            add(BLOCK, "C2PA", "signed_output", message)
    add(INFO, "C2PA", "披露边界",
        "C2PA/Content Credentials 不能替代目标平台的 AI 内容声明；ai_usage 与平台开关仍须独立有效")
    return status


def check_delivery_artifacts(root):
    final = os.path.join(root, "成片_MV.mp4")
    if not os.path.exists(final):
        return
    master = os.path.join(root, "成片_MV_master.mov")
    if not os.path.exists(master):
        add(BLOCK, "交付", "成片_MV_master.mov", "缺可回溯的高质量 mezzanine master")
    qc_path = os.path.join(root, "生产数据", "delivery_qc", "delivery_qc.json")
    qc = load_json_safe(qc_path)
    if qc is None:
        add(BLOCK, "交付", "生产数据/delivery_qc/delivery_qc.json", "缺交付编码/音频/色彩 QC")
    elif int((qc.get("summary") or {}).get("hard_blocks") or 0):
        add(BLOCK, "交付", "生产数据/delivery_qc/delivery_qc.json", "delivery QC 仍有 hard block")
    elif isinstance(qc, dict):
        recorded = qc.get("inputs_sha256") or {}
        required = ["成片_MV.mp4"]
        if os.path.exists(master):
            required.append("成片_MV_master.mov")
        song = mv_utils.find_song(root)
        if song:
            required.append(mv_utils.relpath(root, song))
        stale = [rel for rel in required if recorded.get(rel) != mv_utils.content_hash(os.path.join(root, rel))]
        if stale:
            add(BLOCK, "交付", "生产数据/delivery_qc/delivery_qc.json",
                f"delivery QC 已过期或未绑定当前文件：{stale[0]}")
    provenance_path = os.path.join(root, "合规", "provenance.json")
    provenance = load_json_safe(provenance_path)
    if provenance is None:
        add(BLOCK, "交付", "合规/provenance.json", "缺全链路 hash provenance")
    else:
        assets = {row.get("path"): row.get("sha256") for row in provenance.get("assets") or []}
        rel = "成片_MV.mp4"
        if assets.get(rel) != mv_utils.content_hash(final):
            add(BLOCK, "交付", provenance_path, "provenance 未绑定当前最终 MP4")
        if os.path.exists(master) and assets.get("成片_MV_master.mov") != mv_utils.content_hash(master):
            add(BLOCK, "交付", provenance_path, "provenance 未绑定当前 mezzanine master")
        check_c2pa_status(root, provenance)


def check_ai_usage(root):
    finals = glob.glob(os.path.join(root, "成片_*.mp4")) + glob.glob(os.path.join(root, "成片*.mp4"))
    path = os.path.join(root, "合规", "ai_usage.json")
    meta = mv_utils.load_json(os.path.join(root, "_meta.json"), {}) or {}
    formal = not meta.get("is_demo")
    if not finals:
        return
    if not os.path.exists(path):
        add(BLOCK if formal else WARN, "合规", "合规/ai_usage.json",
            "已有成片但缺 AI 视觉使用披露——发布/交平台前跑 mv-craft/scripts/ai_usage.py")
        return
    payload = load_json_safe(path)
    if payload is None:
        add(BLOCK, "合规", "合规/ai_usage.json", "AI 使用披露 JSON 损坏不可解析")
        return
    mode = payload.get("visual_mode")
    if mode not in ("AI-generated", "AI-assisted", "未使用AI视觉"):
        add(BLOCK if formal else WARN, "合规", "合规/ai_usage.json", f"visual_mode 不在约定枚举内：{mode}")
    else:
        add(INFO, "合规", "合规/ai_usage.json", f"AI 视觉使用披露：visual_mode={mode}")


def _read_json_for_receipt(root, rel, errors):
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        errors.append(f"缺 {rel}")
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{rel} 不可解析：{exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{rel} 顶层必须是 JSON object")
        return None
    return payload


def _binding_errors(root, recorded, *, label, required=()):
    """Validate every recorded binding plus an explicit required subset."""
    if not isinstance(recorded, dict):
        return [f"{label} 缺 inputs_sha256"]
    errors = []
    for rel in required:
        current = mv_utils.content_hash(os.path.join(root, rel))
        if not current:
            errors.append(f"{label} 必需输入不存在：{rel}")
        elif recorded.get(rel) != current:
            errors.append(f"{label} 未绑定当前 {rel}")
    for rel, digest in recorded.items():
        rel = str(rel)
        path = os.path.abspath(os.path.join(root, rel))
        try:
            inside = os.path.commonpath((os.path.abspath(root), path)) == os.path.abspath(root)
        except ValueError:
            inside = False
        if not inside:
            errors.append(f"{label} 含作品根外绑定：{rel}")
            continue
        current = mv_utils.content_hash(path)
        if not current or current != digest:
            errors.append(f"{label} 已过期：{rel}")
    return errors


def review_receipt_prerequisite_errors(root):
    """Return every reason the current delivery cannot receive human sign-off.

    This re-audits source receipts at write time.  It intentionally does not
    trust an earlier mv_check result or a cached summary.
    """
    errors = []
    for rel in REVIEW_INPUTS:
        if not os.path.isfile(os.path.join(root, rel)):
            errors.append(f"审片收据必需输入不存在：{rel}")

    qc = _read_json_for_receipt(
        root, "生产数据/delivery_qc/delivery_qc.json", errors,
    )
    if qc is not None:
        if qc.get("kind") != "mv_delivery_qc":
            errors.append("delivery_qc kind 不是 mv_delivery_qc")
        hard_blocks = (qc.get("summary") or {}).get("hard_blocks")
        if isinstance(hard_blocks, bool) or not isinstance(hard_blocks, (int, float)):
            errors.append("delivery_qc.summary.hard_blocks 缺失或不是数值")
        elif hard_blocks != 0:
            errors.append(f"delivery_qc 仍有 hard_blocks={hard_blocks}")
        errors.extend(_binding_errors(
            root, qc.get("inputs_sha256"), label="delivery_qc",
            required=("成片_MV.mp4", "成片_MV_master.mov"),
        ))

    ai_rel = "合规/ai_usage.json"
    ai_usage = _read_json_for_receipt(root, ai_rel, errors)
    if ai_usage is not None:
        if ai_usage.get("kind") != "mv_ai_usage" or ai_usage.get("complete") is not True:
            errors.append("ai_usage 不是 complete mv_ai_usage")
        mode = ai_usage.get("visual_mode")
        video_mode = ai_usage.get("video_mode")
        if mode not in contract.AI_VISUAL_USAGE_MODES:
            errors.append(f"ai_usage.visual_mode 无效：{mode}")
        if video_mode not in contract.AI_VISUAL_USAGE_MODES:
            errors.append(f"ai_usage.video_mode 无效：{video_mode}")
        errors.extend(_binding_errors(
            root, ai_usage.get("inputs_sha256"), label="ai_usage",
            required=("_设置.md", "_meta.json"),
        ))
        runtime = contract.runtime_state_from_settings(mv_utils.parse_settings(root))
        expected = {
            "visual_mode": runtime["ai_visual_usage"],
            "publish_target": runtime["publish_target"],
            "image_model": runtime["image_model"],
            "image_channel": runtime["image_channel"],
            "video_model": runtime["video_model"],
            "video_channel": runtime["video_channel"],
        }
        for key, value in expected.items():
            if ai_usage.get(key) != value:
                errors.append(
                    f"ai_usage.{key}={ai_usage.get(key)!r} 与当前 _设置.md={value!r} 不一致"
                )
        if runtime["publish_target"] in ("", "未定"):
            errors.append("_设置.md 的发行目标平台仍为未定")

    provenance = _read_json_for_receipt(root, "合规/provenance.json", errors)
    if provenance is not None:
        if provenance.get("kind") != "mv_provenance" or provenance.get("complete") is not True:
            errors.append("provenance 不是 complete mv_provenance")
        errors.extend(_binding_errors(
            root, provenance.get("inputs_sha256"), label="provenance",
        ))
        assets = {
            str(row.get("path")): row.get("sha256")
            for row in (provenance.get("assets") or []) if isinstance(row, dict)
        }
        errors.extend(_binding_errors(
            root, assets, label="provenance assets",
            required=("成片_MV.mp4", "成片_MV_master.mov", ai_rel),
        ))
        current_ai_hash = mv_utils.content_hash(os.path.join(root, ai_rel))
        if provenance.get("ai_usage_sha256") != current_ai_hash:
            errors.append("provenance.ai_usage_sha256 未绑定当前 ai_usage")
        if ai_usage is not None and provenance.get("ai_usage") != ai_usage:
            errors.append("provenance 内嵌的 ai_usage 快照与当前披露不一致")
        errors.extend(c2pa_release_errors(root, provenance))

    # A review receipt is a release-bearing acceptance record, so it must not
    # reimplement a weaker copy of the stage schemas.  Reuse completion's
    # authoritative health validators at the instant of sign-off.  The three
    # delivery stages are unconditional; a downstream delivery artifact proves
    # that image/video production has already been entered, so those stages are
    # also re-audited instead of being silently treated as optional.
    try:
        completion = _load_completion_module()
    except Exception as exc:
        errors.append(f"无法加载 completion 权威健康检查：{type(exc).__name__}: {exc}")
    else:
        health_stages = ["compose", "disclosure", "provenance"]
        downstream_markers = REVIEW_INPUTS + (
            "生产数据/review/review_receipt.json",
            "合规/release_decision.json",
        )
        entered_delivery = any(os.path.exists(os.path.join(root, rel)) for rel in downstream_markers)
        stage_markers = {
            "image": (
                "生产数据/image_qc/image_qc.json",
                "生产数据/image_acceptance/image_acceptance.json",
                "出图",
            ),
            "video_jobs": (
                "出视频/jobs_manifest.json", "出视频/receipts", "出视频/cut_maps",
            ),
            "video": (
                "生产数据/video_qc/video_qc.json",
                "生产数据/video_inherit_contract/inherit_contract.json",
                "出视频/视频",
            ),
        }
        for stage, markers in stage_markers.items():
            if entered_delivery or any(os.path.exists(os.path.join(root, rel)) for rel in markers):
                health_stages.append(stage)
        for stage in health_stages:
            try:
                health = completion.stage_health(root, stage)
            except Exception as exc:
                errors.append(f"completion.{stage} 健康检查异常：{type(exc).__name__}: {exc}")
                continue
            if not isinstance(health, dict):
                errors.append(f"completion.{stage} 健康检查返回无效 payload")
                continue
            stage_errors = health.get("errors") or []
            if not isinstance(stage_errors, list):
                errors.append(f"completion.{stage}.errors 不是 list")
                continue
            errors.extend(f"completion.{stage}: {message}" for message in stage_errors)
            if health.get("ok") is not True and not stage_errors:
                errors.append(f"completion.{stage}: ok=false 且未给出错误原因")
    return list(dict.fromkeys(errors))


_REVIEWER_PLACEHOLDER = re.compile(
    r"^(?:<.*>|ai|unknown|待填|待定|匿名)$|(?:codex|chatgpt|claude|agent|bot|机器人|自动化)",
    re.IGNORECASE,
)


def validate_human_signoff(reviewer, notes):
    errors = []
    reviewer = str(reviewer or "").strip()
    notes = str(notes or "").strip()
    if len(reviewer) < 2 or _REVIEWER_PLACEHOLDER.search(reviewer):
        errors.append("--reviewer 必须是真实具名复核人，不能是占位符或 AI/agent")
    if not notes or mv_utils.PLACEHOLDER.search(notes):
        errors.append("--notes 必须非空且是完成的人审结论")
    return reviewer, notes, errors


def write_review_receipt(root, reviewer, notes):
    """Write the hash-bound receipt; caller must have run all guards."""
    reviewed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    inputs = {
        rel: mv_utils.content_hash(os.path.join(root, rel)) for rel in REVIEW_INPUTS
    }
    provenance = mv_utils.load_json(os.path.join(root, "合规", "provenance.json"), {}) or {}
    machine_findings = [
        {"sev": s, "dim": d, "loc": l, "msg": m}
        for s, d, l, m in findings
    ]
    payload = {
        "schema_version": 1,
        "kind": "mv_review_receipt",
        "accepted": True,
        "reviewed_at": reviewed_at,
        "inputs_sha256": inputs,
        "machine_review": {
            "hard_blocks": 0,
            "warnings": sum(1 for row in findings if row[0] == WARN),
            "infos": sum(1 for row in findings if row[0] == INFO),
            "findings": machine_findings,
            "findings_sha256": mv_utils.json_hash(machine_findings),
            "c2pa": c2pa_status_dimensions(provenance),
        },
        "human_signoff": {
            "accepted": True,
            "reviewer": reviewer,
            "notes": notes,
            "reviewed_at": reviewed_at,
            "confirmation": {
                "kind": "explicit_current_delivery_acceptance",
                "accepted_current_delivery": True,
            },
        },
    }
    out = os.path.join(root, REVIEW_RECEIPT_REL)
    mv_utils.write_json(out, payload)
    return out


def _mark_review_complete(root):
    """Let the central completion controller own progress mutation."""
    completion = _load_completion_module()
    completion.mark_stage_complete(root, "review")


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


def run_checks(root):
    """Run the full deterministic review without mutating the project."""
    meta = load_json_safe(os.path.join(root, "_meta.json"))
    song_path = mv_utils.find_song(root)
    songlen = mv_utils.audio_duration(song_path) if song_path else None

    check_completeness(root)
    lyric_lines = check_lyrics_and_meta(root, meta)
    check_beatgrid(root, songlen)
    check_plan_manifests(root, songlen)
    check_video_jobs(root)
    check_consistency_artifacts(root, meta)
    check_image_acceptance(root)
    check_production_pack(root, meta)
    check_formal_readiness(root, meta)
    check_clips(root, songlen)
    check_subtitles(root, songlen, lyric_lines)
    check_alignment_report(root)
    check_final(root, meta, songlen)
    check_delivery_artifacts(root)
    check_ai_usage(root)
    if songlen:
        add(INFO, "音画", mv_utils.relpath(root, song_path), f"歌长基准：{songlen:.2f}s")
    return list(findings)


def _print_findings(root, as_json):
    if as_json:
        print(json.dumps([{"sev": s, "dim": d, "loc": l, "msg": m}
                          for s, d, l, m in findings], ensure_ascii=False, indent=2))
        return
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


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="MV 确定性机检；默认只读，显式参数才能写具名 review receipt",
    )
    parser.add_argument("project_root")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--tol", type=float, default=pacing.DUR_TOL)
    parser.add_argument("--write-receipt", action="store_true")
    parser.add_argument("--reviewer", default="")
    parser.add_argument("--notes", default="")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"作品根不存在：{root}", file=sys.stderr)
        return 2
    if not args.write_receipt and (args.reviewer or args.notes):
        print("[err] --reviewer/--notes 仅与显式 --write-receipt 同用", file=sys.stderr)
        return 2

    global DUR_TOL
    DUR_TOL = args.tol
    findings.clear()
    reviewer = notes = ""
    if args.write_receipt:
        reviewer, notes, signoff_errors = validate_human_signoff(args.reviewer, args.notes)
        if signoff_errors:
            for message in signoff_errors:
                add(BLOCK, "审片收据", "human_signoff", message)

    run_checks(root)
    if args.write_receipt:
        for message in review_receipt_prerequisite_errors(root):
            add(BLOCK, "审片收据", REVIEW_RECEIPT_REL, message)

    has_blocks = any(row[0] == BLOCK for row in findings)
    receipt_path = ""
    if args.write_receipt and not has_blocks:
        receipt_path = write_review_receipt(root, reviewer, notes)
        try:
            _mark_review_complete(root)
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            # The receipt stays valid for standalone/legacy projects whose
            # progress table has not yet adopted the current stage contract.
            print(f"[warn] 审片收据已写，但进度表未更新：{exc}", file=sys.stderr)

    _print_findings(root, args.json)
    if receipt_path:
        print(f"[ok] 具名审片收据 → {receipt_path}", file=sys.stderr)
    elif args.write_receipt:
        print("[block] 未写审片收据：机检或当前证据链存在阻断", file=sys.stderr)
    return 1 if has_blocks else 0


if __name__ == "__main__":
    raise SystemExit(main())
