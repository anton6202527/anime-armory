"""mv_check 机检单测（覆盖 stdlib 确定性路径；clip/成片 的 ffprobe 路径在真机 demo 跑）。
从脚本自身目录跑：
    cd skills/mv/mv-review/scripts && python -m pytest test_mv_check.py
或直接：
    python3 test_mv_check.py
"""
import os, json, wave, array, tempfile, shutil
import mv_check as mc

BLOCK, WARN = mc.BLOCK, mc.WARN


def write_wav(path, seconds=6, rate=8000):
    n = int(seconds * rate)
    a = array.array("h", [0] * n)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(a.tobytes())


LYRICS = """# 歌词

[verse1]
晨钟惊起一山霜
师父背影留云上

[chorus]
我仗剑下山闯人间
江湖那么大走最前
"""

LRC = "[00:01.00]我仗剑下山闯人间\n[00:03.00]江湖那么大走最前\n"

BEATGRID = {
    "song": "歌/song.wav", "duration": 6.0, "bpm": 120, "meter": 4,
    "beats": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
    "downbeats": [0.5, 2.5, 4.5],
}
STRUCTURE = ["verse1", "chorus"]


def make_mv(tmp, *, lyrics=LYRICS, lrc=LRC, beatgrid=None, meta=None,
            song=True, structure=STRUCTURE, progress="# 进度\n"):
    root = os.path.join(tmp, "曲")
    for d in ("词", "歌", "节拍", "字幕", "分镜", "出视频", "合规"):
        os.makedirs(os.path.join(root, d), exist_ok=True)
    open(os.path.join(root, "视觉蓝图.md"), "w").write("# 蓝图\n")
    open(os.path.join(root, "_进度.md"), "w", encoding="utf-8").write(progress)
    if lyrics is not None:
        open(os.path.join(root, "词", "lyrics.md"), "w", encoding="utf-8").write(lyrics)
    if lrc is not None:
        open(os.path.join(root, "字幕", "lyrics.lrc"), "w", encoding="utf-8").write(lrc)
    bg = BEATGRID if beatgrid is None else beatgrid
    if bg is not None:
        if bg == "CORRUPT":
            open(os.path.join(root, "节拍", "beatgrid.json"), "w").write("{not json")
        else:
            json.dump(bg, open(os.path.join(root, "节拍", "beatgrid.json"), "w"))
    if song:
        write_wav(os.path.join(root, "歌", "song.wav"))
    if meta is None:
        meta = {"title": "曲", "aspect": "9:16", "structure": structure,
                "has_song": True, "has_lyrics": True, "is_demo": True}
    json.dump(meta, open(os.path.join(root, "_meta.json"), "w", encoding="utf-8"))
    return root


def _write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def make_alignment_report(root, *, accepted=True, route="named_listening_review"):
    """Build a current schema-v5 report using the producer's exact binding algorithm."""
    align = mc._load_alignment_module()
    ass_rel = "字幕/karaoke.ass"
    lrc_rel = "字幕/lyrics.lrc"
    master_rel = "歌/song.wav"
    with open(os.path.join(root, ass_rel), "w", encoding="utf-8") as handle:
        handle.write("[Events]\nDialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,晨钟惊起一山霜\n")
    inputs = {
        "词/lyrics.md": mc.mv_utils.content_hash(os.path.join(root, "词/lyrics.md")),
        master_rel: mc.mv_utils.content_hash(os.path.join(root, master_rel)),
    }
    outputs = {
        ass_rel: mc.mv_utils.content_hash(os.path.join(root, ass_rel)),
        lrc_rel: mc.mv_utils.content_hash(os.path.join(root, lrc_rel)),
    }
    binding_assets = {
        "master": {"path": master_rel, "sha256": inputs[master_rel]},
        "alignment_audio": {"path": master_rel, "sha256": inputs[master_rel]},
    }
    report = {
        "schema_version": 5,
        "kind": "mv_lyric_alignment_report",
        "audio": master_rel,
        "master_song": master_rel,
        "inputs_sha256": inputs,
        "outputs_sha256": outputs,
        "alignment_unit": "character",
        "coverage_metric": "text_character_mapping_ratio_not_acoustic_confidence",
        "character_coverage_ratio": 1.0,
        "lyric_lines": 4,
        "aligned_lines": 4,
        "lines": [
            {"line": index + 1, "start": float(index), "end": float(index + 1),
             "line_character_coverage": 1.0}
            for index in range(4)
        ],
        "timing_issues": [],
        "stem_master_timing": {
            "schema_version": 1,
            "status": "pass",
            "method": "same_master_file",
            "offset_seconds": 0.0,
            "drift_seconds": 0.0,
            "mapping": "identity",
            "bindings": binding_assets,
        },
        "warnings": [],
    }
    binding = align.acceptance_binding(root, report)
    if not accepted:
        report["acceptance"] = {
            "status": "pending", "accepted": False,
            "required_routes": ["singing_acoustic_evidence", "named_listening_review"],
            "required_binding": binding,
        }
        return report
    if route == "named_listening_review":
        manual = {
            "schema_version": 1,
            "kind": "named_full_listening_review",
            "accepted": True,
            "verdict": "pass",
            "scope": "full_song_line_by_line_against_master_and_alignment_audio",
            "reviewer": "王晓明",
            "notes": "逐行对照 master、对齐音频、ASS 与 LRC，offset/drift 边界通过",
            "binding": binding,
            "bound_inputs_sha256": dict(inputs),
            "bound_outputs_sha256": dict(outputs),
            "bound_report_preaccept_sha256": binding["report_preaccept_content_sha256"],
        }
        report["manual_review"] = manual
        report["acceptance"] = {
            "status": "accepted", "accepted": True, "route": route,
            "binding": binding,
            "evidence_content_sha256": align.stable_json_sha256(manual),
        }
    else:
        evidence = {
            "kind": "mv_singing_alignment_acoustic_evidence",
            "schema_version": 1,
            "model": {"name": "SingingAlign", "version": "1.0"},
            "singing_specific": True,
            "calibrated": True,
            "acceptance_eligible": True,
            "metric": "calibrated_phoneme_boundary_probability",
            "method": "SingingAlign@1.0:calibrated_phoneme_boundary_probability",
            "threshold": 0.9,
            "confidence": 0.96,
            "status": "pass",
            "binding": binding,
            "bound_inputs_sha256": dict(inputs),
            "bound_outputs_sha256": dict(outputs),
            "per_line": [
                {"line_index": index, "score": 0.96, "threshold": 0.9, "status": "pass"}
                for index in range(4)
            ],
        }
        report["acoustic_evidence"] = evidence
        report["acceptance"] = {
            "status": "accepted", "accepted": True, "route": route,
            "binding": binding,
            "evidence_content_sha256": align.stable_json_sha256(evidence),
        }
    return report


def make_current_review_chain(tmp, *, c2pa=None):
    """Create a minimal chain; receipt-unit tests stub authoritative stage health."""
    root = make_mv(tmp)
    settings_path = os.path.join(root, "_设置.md")
    with open(settings_path, "w", encoding="utf-8") as handle:
        handle.write(
            "# 设置\n\n"
            "- AI视觉使用披露：AI-generated\n"
            "- 发行目标平台：抖音\n"
            "- 生图模型：GPT Image 2\n"
            "- 生图渠道：Codex\n"
            "- 生视频模型：Seedance 2.0\n"
            "- 生视频渠道：即梦/Dreamina\n"
            "- MV一致性增强：共享定妆+锚点\n"
            "- 出视频规格：预算一般\n"
            "- 演唱口型：关闭\n"
            "- 合成画幅：9:16\n"
            "- 字幕语言：中文\n"
        )
    final = os.path.join(root, "成片_MV.mp4")
    master = os.path.join(root, "成片_MV_master.mov")
    with open(final, "wb") as handle:
        handle.write(b"current-final")
    with open(master, "wb") as handle:
        handle.write(b"current-master")

    runtime = mc.contract.runtime_state_from_settings(mc.mv_utils.parse_settings(root))
    ai_rel = "合规/ai_usage.json"
    ai = {
        "schema_version": 2,
        "kind": "mv_ai_usage",
        "complete": True,
        "visual_mode": runtime["ai_visual_usage"],
        "video_mode": runtime["ai_visual_usage"],
        "publish_target": runtime["publish_target"],
        "image_model": runtime["image_model"],
        "image_channel": runtime["image_channel"],
        "video_model": runtime["video_model"],
        "video_channel": runtime["video_channel"],
        "inputs_sha256": {
            "_设置.md": mc.mv_utils.content_hash(settings_path),
            "_meta.json": mc.mv_utils.content_hash(os.path.join(root, "_meta.json")),
        },
    }
    _write_json(os.path.join(root, ai_rel), ai)
    qc_rel = "生产数据/delivery_qc/delivery_qc.json"
    qc = {
        "schema_version": 1,
        "kind": "mv_delivery_qc",
        "summary": {"hard_blocks": 0},
        "inputs_sha256": {
            "成片_MV.mp4": mc.mv_utils.content_hash(final),
            "成片_MV_master.mov": mc.mv_utils.content_hash(master),
        },
    }
    _write_json(os.path.join(root, qc_rel), qc)
    c2pa_status = c2pa or {
        "requested": False,
        "embedded": False,
        "structurally_valid": False,
        "signature_valid": False,
        "trust_checked": False,
        "trusted": False,
        "timestamp_validated": False,
        "timestamp_trusted": False,
        "timestamped": False,
        "timestamp_exception_allowed": False,
        "certificate_profile": None,
    }
    provenance = {
        "schema_version": 2,
        "kind": "mv_provenance",
        "complete": True,
        "assets": [
            {"path": "成片_MV.mp4", "sha256": mc.mv_utils.content_hash(final)},
            {"path": "成片_MV_master.mov", "sha256": mc.mv_utils.content_hash(master)},
            {"path": ai_rel, "sha256": mc.mv_utils.content_hash(os.path.join(root, ai_rel))},
        ],
        "inputs_sha256": {ai_rel: mc.mv_utils.content_hash(os.path.join(root, ai_rel))},
        "ai_usage": ai,
        "ai_usage_sha256": mc.mv_utils.content_hash(os.path.join(root, ai_rel)),
        "c2pa": c2pa_status,
    }
    _write_json(os.path.join(root, "合规/provenance.json"), provenance)
    return root


class _HealthyCompletionFixture:
    """Explicit unit-test seam; production receipt writes load real completion."""

    def stage_health(self, _root, stage):
        return {"stage": stage, "ok": True, "errors": [], "warnings": []}


def _with_quiet_machine_checks(callback, *, completion_fixture=None):
    old_run = mc.run_checks
    old_print = mc._print_findings
    old_mark = mc._mark_review_complete
    old_completion = mc._COMPLETION_MODULE
    try:
        mc.run_checks = lambda _root: list(mc.findings)
        mc._print_findings = lambda _root, _json: None
        mc._mark_review_complete = lambda _root: None
        mc._COMPLETION_MODULE = completion_fixture or _HealthyCompletionFixture()
        return callback()
    finally:
        mc.run_checks = old_run
        mc._print_findings = old_print
        mc._mark_review_complete = old_mark
        mc._COMPLETION_MODULE = old_completion


def run(root):
    mc.findings.clear()
    meta = mc.load_json_safe(os.path.join(root, "_meta.json"))
    songlen = mc.mv_utils.wav_duration(os.path.join(root, "歌", "song.wav"))
    mc.check_completeness(root)
    ll = mc.check_lyrics_and_meta(root, meta)
    mc.check_beatgrid(root, songlen)
    mc.check_plan_manifests(root, songlen)
    mc.check_video_jobs(root)
    mc.check_image_acceptance(root)
    mc.check_clips(root, songlen)
    mc.check_subtitles(root, songlen, ll)
    mc.check_alignment_report(root)
    mc.check_final(root, meta, songlen)
    mc.check_ai_usage(root)
    return list(mc.findings)


def has(f, sev=None, dim=None, sub=None):
    return any((sev is None or s == sev) and (dim is None or d == dim)
               and (sub is None or sub in m) for s, d, l, m in f)


def test_clean_no_block():
    tmp = tempfile.mkdtemp()
    try:
        assert not [x for x in run(make_mv(tmp)) if x[0] == BLOCK], run(make_mv(tmp))
    finally:
        shutil.rmtree(tmp)


def test_beatgrid_corrupt_blocks():
    tmp = tempfile.mkdtemp()
    try:
        assert has(run(make_mv(tmp, beatgrid="CORRUPT")), BLOCK, "卡点")
    finally:
        shutil.rmtree(tmp)


def test_bpm_out_of_range_warns():
    tmp = tempfile.mkdtemp()
    try:
        bg = dict(BEATGRID, bpm=300)
        assert has(run(make_mv(tmp, beatgrid=bg)), WARN, sub="半速/倍速")
    finally:
        shutil.rmtree(tmp)


def test_beats_non_monotonic_warns():
    tmp = tempfile.mkdtemp()
    try:
        bg = dict(BEATGRID, beats=[0.5, 0.4, 1.0])
        assert has(run(make_mv(tmp, beatgrid=bg)), BLOCK, sub="递增")
    finally:
        shutil.rmtree(tmp)


def test_beatgrid_duration_mismatch_warns():
    tmp = tempfile.mkdtemp()
    try:
        bg = dict(BEATGRID, duration=30.0)   # 歌只有 6s
        assert has(run(make_mv(tmp, beatgrid=bg)), BLOCK, "卡点", "歌长")
    finally:
        shutil.rmtree(tmp)


def test_subtitle_placeholder_blocks():
    tmp = tempfile.mkdtemp()
    try:
        assert has(run(make_mv(tmp, lrc="[00:01.00]（待填这句）\n")), BLOCK, "字幕")
    finally:
        shutil.rmtree(tmp)


def test_subtitle_out_of_range_warns():
    tmp = tempfile.mkdtemp()
    try:
        assert has(run(make_mv(tmp, lrc="[00:01.00]行一\n[00:59.00]越界行\n")), WARN, "字幕", "越界")
    finally:
        shutil.rmtree(tmp)


def test_subtitle_disorder_warns():
    tmp = tempfile.mkdtemp()
    try:
        assert has(run(make_mv(tmp, lrc="[00:03.00]后\n[00:01.00]前\n")), WARN, "字幕")
    finally:
        shutil.rmtree(tmp)


def test_lyrics_placeholder_blocks():
    tmp = tempfile.mkdtemp()
    try:
        ly = LYRICS.replace("江湖那么大走最前", "TODO 这句副歌")
        assert has(run(make_mv(tmp, lyrics=ly)), BLOCK)
    finally:
        shutil.rmtree(tmp)


def test_structure_mismatch_warns():
    tmp = tempfile.mkdtemp()
    try:
        assert has(run(make_mv(tmp, structure=["intro", "verse1", "chorus", "outro"])), WARN, sub="structure")
    finally:
        shutil.rmtree(tmp)


def test_delivery_receipts_invalidate_when_final_changes():
    tmp = tempfile.mkdtemp()
    try:
        root = make_mv(tmp)
        final = os.path.join(root, "成片_MV.mp4")
        master = os.path.join(root, "成片_MV_master.mov")
        open(final, "wb").write(b"final-v1")
        open(master, "wb").write(b"master-v1")
        song_rel = "歌/song.wav"
        inputs = {
            "成片_MV.mp4": mc.mv_utils.content_hash(final),
            "成片_MV_master.mov": mc.mv_utils.content_hash(master),
            song_rel: mc.mv_utils.content_hash(os.path.join(root, song_rel)),
        }
        qc_path = os.path.join(root, "生产数据", "delivery_qc", "delivery_qc.json")
        os.makedirs(os.path.dirname(qc_path), exist_ok=True)
        json.dump({"summary": {"hard_blocks": 0}, "inputs_sha256": inputs}, open(qc_path, "w"))
        provenance_path = os.path.join(root, "合规", "provenance.json")
        json.dump({"assets": [
            {"path": "成片_MV.mp4", "sha256": inputs["成片_MV.mp4"]},
            {"path": "成片_MV_master.mov", "sha256": inputs["成片_MV_master.mov"]},
        ]}, open(provenance_path, "w"))
        mc.findings.clear()
        mc.check_delivery_artifacts(root)
        assert not [row for row in mc.findings if row[0] == BLOCK]

        open(final, "wb").write(b"final-v2")
        mc.findings.clear()
        mc.check_delivery_artifacts(root)
        assert has(list(mc.findings), BLOCK, "交付", "过期")
    finally:
        shutil.rmtree(tmp)


def test_formal_final_requires_ai_usage_receipt():
    tmp = tempfile.mkdtemp()
    try:
        root = make_mv(tmp, meta={"title": "曲", "aspect": "9:16", "structure": STRUCTURE,
                                  "has_song": True, "has_lyrics": True, "is_demo": False})
        open(os.path.join(root, "成片_MV.mp4"), "wb").write(b"final")
        mc.findings.clear()
        mc.check_ai_usage(root)
        assert has(list(mc.findings), BLOCK, "合规", "AI 视觉使用披露")
    finally:
        shutil.rmtree(tmp)


def test_meta_has_song_stale_warns():
    tmp = tempfile.mkdtemp()
    try:
        meta = {"title": "曲", "aspect": "9:16", "structure": STRUCTURE, "has_song": False, "has_lyrics": True}
        assert has(run(make_mv(tmp, meta=meta)), WARN, sub="has_song" if False else "未更新")
    finally:
        shutil.rmtree(tmp)


def test_missing_final_with_compose_progress_warns():
    tmp = tempfile.mkdtemp()
    try:
        f = run(make_mv(tmp, progress="# 进度\nmv-compose 已合成成片\n"))
        assert has(f, WARN, "音画")
    finally:
        shutil.rmtree(tmp)


def test_duplicate_plan_clip_id_blocks():
    tmp = tempfile.mkdtemp()
    try:
        root = make_mv(tmp)
        plan = {
            "clips": [
                {"clip_id": "Clip_001", "start": 0.0, "end": 3.0, "duration": 3.0},
                {"clip_id": "Clip_001", "start": 3.0, "end": 6.0, "duration": 3.0},
            ]
        }
        json.dump(plan, open(os.path.join(root, "分镜", "clip_plan.json"), "w", encoding="utf-8"), ensure_ascii=False)
        assert has(run(root), BLOCK, "规划", "clip_id 重复")
    finally:
        shutil.rmtree(tmp)


def test_timeline_missing_selected_video_warns():
    tmp = tempfile.mkdtemp()
    try:
        root = make_mv(tmp)
        plan = {"clips": [{"clip_id": "Clip_001", "start": 0.0, "end": 6.0, "duration": 6.0}]}
        timeline = {"clips": [{"clip_id": "Clip_001", "video_path": "出视频/视频/Clip_001.mp4"}]}
        json.dump(plan, open(os.path.join(root, "分镜", "clip_plan.json"), "w", encoding="utf-8"), ensure_ascii=False)
        json.dump(timeline, open(os.path.join(root, "分镜", "timeline_manifest.json"), "w", encoding="utf-8"), ensure_ascii=False)
        assert has(run(root), WARN, "规划", "video_path 尚不存在")
    finally:
        shutil.rmtree(tmp)


def test_selected_video_job_missing_clip_blocks():
    tmp = tempfile.mkdtemp()
    try:
        root = make_mv(tmp)
        manifest = {
            "jobs": [{
                "clip_id": "Clip_001",
                "selected_take": "take_01",
                "selected_video_path": "出视频/视频/Clip_001.mp4",
            }]
        }
        json.dump(manifest, open(os.path.join(root, "出视频", "jobs_manifest.json"), "w", encoding="utf-8"), ensure_ascii=False)
        assert has(run(root), BLOCK, "规划", "selected_take 已选但成品 clip 不存在")
    finally:
        shutil.rmtree(tmp)


def test_alignment_report_warnings_surface():
    tmp = tempfile.mkdtemp()
    try:
        root = make_mv(tmp)
        report = {"lyric_lines": 2, "aligned_lines": 1, "unused_word_segments": 3, "warnings": ["歌词与演唱疑似不一致"]}
        json.dump(report, open(os.path.join(root, "字幕", "alignment_report.json"), "w", encoding="utf-8"), ensure_ascii=False)
        assert has(run(root), WARN, "字幕", "歌词与演唱疑似不一致")
    finally:
        shutil.rmtree(tmp)


def test_formal_subtitles_missing_schema_v5_alignment_report_block():
    tmp = tempfile.mkdtemp()
    try:
        root = make_mv(tmp, meta={
            "title": "曲", "aspect": "9:16", "structure": STRUCTURE,
            "has_song": True, "has_lyrics": True, "is_demo": False,
        })
        with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as handle:
            handle.write("# 设置\n\n- 字幕语言：中文\n- 演唱口型：关闭\n")
        mc.findings.clear()
        mc.check_alignment_report(root)
        assert has(mc.findings, BLOCK, "字幕", "缺当前 schema v5")
    finally:
        shutil.rmtree(tmp)


def test_schema_v5_named_listening_acceptance_is_current_and_coverage_is_not_confidence():
    tmp = tempfile.mkdtemp()
    try:
        root = make_mv(tmp)
        _write_json(os.path.join(root, "字幕/alignment_report.json"), make_alignment_report(root))
        mc.findings.clear()
        mc.check_alignment_report(root)
        assert not any(row[0] == BLOCK for row in mc.findings), mc.findings
        info = next(row[3] for row in mc.findings if "character_coverage_ratio" in row[3])
        assert "不是声学置信度" in info
    finally:
        shutil.rmtree(tmp)


def test_pending_or_legacy_confidence_alignment_report_blocks():
    tmp = tempfile.mkdtemp()
    try:
        root = make_mv(tmp)
        report = make_alignment_report(root, accepted=False)
        report["alignment_confidence"] = 0.99
        _write_json(os.path.join(root, "字幕/alignment_report.json"), report)
        mc.findings.clear()
        mc.check_alignment_report(root)
        assert has(mc.findings, BLOCK, "字幕", "禁止 alignment_confidence")
        assert has(mc.findings, BLOCK, "字幕", "尚未正式接受")
    finally:
        shutil.rmtree(tmp)


def test_acoustic_route_requires_calibrated_singing_eligible_evidence():
    tmp = tempfile.mkdtemp()
    try:
        root = make_mv(tmp)
        report = make_alignment_report(root, route="singing_acoustic_evidence")
        report["acoustic_evidence"]["acceptance_eligible"] = False
        align = mc._load_alignment_module()
        report["acceptance"]["evidence_content_sha256"] = align.stable_json_sha256(report["acoustic_evidence"])
        _write_json(os.path.join(root, "字幕/alignment_report.json"), report)
        mc.findings.clear()
        mc.check_alignment_report(root)
        assert has(mc.findings, BLOCK, "字幕", "acceptance_eligible=true")
    finally:
        shutil.rmtree(tmp)


def test_acoustic_route_must_bind_current_inputs_and_outputs():
    tmp = tempfile.mkdtemp()
    try:
        root = make_mv(tmp)
        report = make_alignment_report(root, route="singing_acoustic_evidence")
        report["acoustic_evidence"]["bound_outputs_sha256"] = {}
        align = mc._load_alignment_module()
        report["acceptance"]["evidence_content_sha256"] = align.stable_json_sha256(report["acoustic_evidence"])
        _write_json(os.path.join(root, "字幕/alignment_report.json"), report)
        mc.findings.clear()
        mc.check_alignment_report(root)
        assert has(mc.findings, BLOCK, "字幕", "未绑定当前 inputs/outputs")
    finally:
        shutil.rmtree(tmp)


def test_stem_alignment_requires_named_or_automatic_offset_and_drift():
    tmp = tempfile.mkdtemp()
    try:
        root = make_mv(tmp)
        stem_rel = "歌/vocals.wav"
        write_wav(os.path.join(root, stem_rel), seconds=5)
        report = make_alignment_report(root, accepted=False)
        report["audio"] = stem_rel
        report["inputs_sha256"][stem_rel] = mc.mv_utils.content_hash(os.path.join(root, stem_rel))
        report["stem_master_timing"] = {
            "schema_version": 1, "status": "pass", "method": "named_offset_drift_declaration",
            "reviewer": "音频工程师", "notes": "已看 DAW 标记但漏填数值",
            "bindings": {
                "master": {"path": "歌/song.wav", "sha256": report["inputs_sha256"]["歌/song.wav"]},
                "alignment_audio": {"path": stem_rel, "sha256": report["inputs_sha256"][stem_rel]},
            },
        }
        report["acceptance"]["required_binding"] = mc._load_alignment_module().acceptance_binding(root, report)
        _write_json(os.path.join(root, "字幕/alignment_report.json"), report)
        mc.findings.clear()
        mc.check_alignment_report(root)
        assert has(mc.findings, BLOCK, "字幕", "offset/drift")
    finally:
        shutil.rmtree(tmp)


def test_mv_check_never_treats_degraded_manual_image_review_as_b14_pass():
    tmp = tempfile.mkdtemp()
    try:
        root = make_mv(tmp)
        _write_json(os.path.join(root, "分镜/clip_plan.json"), {
            "clips": [{"clip_id": "Clip_001", "image_path": "出图/Clip_001.png"}],
        })
        _write_json(os.path.join(root, "生产数据/image_qc/image_qc.json"), {
            "kind": "mv_image_qc",
            "version": 3,
            "summary": {"hard_blocks": 0, "verdict": "review"},
            "qc_environment": {"precision_level": "degraded"},
            "manual_review": {"accepted": True, "reviewer": "审图人"},
        })
        mc.findings.clear()
        mc.check_image_acceptance(root)
        assert has(mc.findings, BLOCK, "一致性", "--accept-degraded")
        assert has(mc.findings, BLOCK, "一致性", "缺权威 image_acceptance ledger")
        assert not has(mc.findings, WARN, "一致性", "人工放行")
    finally:
        shutil.rmtree(tmp)


def test_default_cli_is_read_only_even_when_receipt_exists():
    tmp = tempfile.mkdtemp()
    try:
        root = make_current_review_chain(tmp)
        receipt = os.path.join(root, mc.REVIEW_RECEIPT_REL)
        os.makedirs(os.path.dirname(receipt), exist_ok=True)
        with open(receipt, "wb") as handle:
            handle.write(b"existing-review-receipt")
        before = open(receipt, "rb").read()
        code = _with_quiet_machine_checks(lambda: mc.main([root]))
        assert code == 0
        assert open(receipt, "rb").read() == before
    finally:
        shutil.rmtree(tmp)


def test_write_receipt_requires_named_human_and_notes():
    tmp = tempfile.mkdtemp()
    try:
        root = make_current_review_chain(tmp)
        code = _with_quiet_machine_checks(lambda: mc.main([
            root, "--write-receipt", "--reviewer", "Codex Agent", "--notes", "待填",
        ]))
        assert code == 1
        assert not os.path.exists(os.path.join(root, mc.REVIEW_RECEIPT_REL))
    finally:
        shutil.rmtree(tmp)


def test_explicit_current_chain_writes_hash_bound_review_receipt():
    tmp = tempfile.mkdtemp()
    try:
        root = make_current_review_chain(tmp)
        code = _with_quiet_machine_checks(lambda: mc.main([
            root, "--write-receipt", "--reviewer", "王晓明",
            "--notes", "已逐项完成画面、卡点、字幕与合规复核，同意当前版本交付。",
        ]))
        assert code == 0
        receipt_path = os.path.join(root, mc.REVIEW_RECEIPT_REL)
        receipt = json.load(open(receipt_path, encoding="utf-8"))
        assert receipt["kind"] == "mv_review_receipt"
        assert receipt["accepted"] is True
        assert receipt["human_signoff"]["reviewer"] == "王晓明"
        assert receipt["human_signoff"]["accepted"] is True
        assert receipt["machine_review"]["hard_blocks"] == 0
        assert tuple(receipt["inputs_sha256"]) == mc.REVIEW_INPUTS
        for rel, digest in receipt["inputs_sha256"].items():
            assert digest == mc.mv_utils.content_hash(os.path.join(root, rel))
    finally:
        shutil.rmtree(tmp)


def test_receipt_write_rechecks_entered_completion_stage_health():
    tmp = tempfile.mkdtemp()
    try:
        root = make_current_review_chain(tmp)
        calls = []

        class RejectStaleVideo:
            def stage_health(self, _root, stage):
                calls.append(stage)
                if stage == "video":
                    return {"stage": stage, "ok": False,
                            "errors": ["fixture selected video hash stale"], "warnings": []}
                return {"stage": stage, "ok": True, "errors": [], "warnings": []}

        code = _with_quiet_machine_checks(lambda: mc.main([
            root, "--write-receipt", "--reviewer", "王晓明",
            "--notes", "已完成当前成片人工复核。",
        ]), completion_fixture=RejectStaleVideo())
        assert code == 1
        assert set(calls) == {"compose", "disclosure", "provenance", "image", "video_jobs", "video"}
        assert has(list(mc.findings), BLOCK, "审片收据", "completion.video")
        assert not os.path.exists(os.path.join(root, mc.REVIEW_RECEIPT_REL))
    finally:
        shutil.rmtree(tmp)


def test_real_completion_rejects_legacy_delivery_qc_schema_one():
    tmp = tempfile.mkdtemp()
    old_completion = mc._COMPLETION_MODULE
    try:
        root = make_current_review_chain(tmp)
        assert json.load(open(
            os.path.join(root, "生产数据/delivery_qc/delivery_qc.json"), encoding="utf-8"
        ))["schema_version"] == 1
        mc._COMPLETION_MODULE = None
        errors = mc.review_receipt_prerequisite_errors(root)
        assert any(
            message.startswith("completion.compose:") and "schema v3" in message
            for message in errors
        ), errors
    finally:
        mc._COMPLETION_MODULE = old_completion
        shutil.rmtree(tmp)


def test_stale_delivery_chain_refuses_review_receipt():
    tmp = tempfile.mkdtemp()
    try:
        root = make_current_review_chain(tmp)
        with open(os.path.join(root, "成片_MV.mp4"), "wb") as handle:
            handle.write(b"changed-after-qc")
        code = _with_quiet_machine_checks(lambda: mc.main([
            root, "--write-receipt", "--reviewer", "王晓明",
            "--notes", "已完成当前成片人工复核。",
        ]))
        assert code == 1
        assert not os.path.exists(os.path.join(root, mc.REVIEW_RECEIPT_REL))
        assert has(list(mc.findings), BLOCK, "审片收据", "delivery_qc")
        assert has(list(mc.findings), BLOCK, "审片收据", "provenance")
    finally:
        shutil.rmtree(tmp)


def test_c2pa_dimensions_do_not_collapse_signature_trust_test_timestamp():
    tmp = tempfile.mkdtemp()
    try:
        root = make_mv(tmp)
        signed_rel = "成片_MV.c2pa.mp4"
        signed = os.path.join(root, signed_rel)
        with open(signed, "wb") as handle:
            handle.write(b"signed")
        provenance = {"c2pa": {
            "requested": True,
            "embedded": True,
            "structurally_valid": True,
            "signature_valid": True,
            "trust_checked": True,
            "trusted": True,
            "timestamp_validated": False,
            "timestamp_trusted": False,
            "timestamped": False,
            "timestamp_exception_allowed": True,
            "certificate_profile": "production",
            "output": signed_rel,
            "output_sha256": mc.mv_utils.content_hash(signed),
        }}
        status = mc.c2pa_status_dimensions(provenance)
        assert status["structurally_valid"] is True
        assert status["signature_valid"] is True
        assert status["trusted"] is True
        assert status["test_certificate"] is False
        assert status["timestamped"] is False
        assert mc.c2pa_release_errors(root, provenance) == []
        mc.findings.clear()
        mc.check_c2pa_status(root, provenance)
        assert has(list(mc.findings), WARN, "C2PA", "exception=True")
        assert has(list(mc.findings), mc.INFO, "C2PA", "不能替代目标平台")

        provenance["c2pa"]["timestamp_exception_allowed"] = False
        errors = mc.c2pa_release_errors(root, provenance)
        assert any("可信 TSA 时间戳" in message for message in errors)
        provenance["c2pa"]["timestamp_exception_allowed"] = True

        provenance["c2pa"]["certificate_profile"] = "test_untrusted"
        provenance["c2pa"]["trusted"] = False
        errors = mc.c2pa_release_errors(root, provenance)
        assert any("test certificate" in message for message in errors)
        assert any("信任链" in message for message in errors)
        mc.findings.clear()
        mc.check_c2pa_status(root, provenance)
        assert has(list(mc.findings), BLOCK, "C2PA", "test_untrusted")
        assert has(list(mc.findings), BLOCK, "C2PA", "trusted=false")
    finally:
        shutil.rmtree(tmp)


def test_c2pa_never_substitutes_platform_ai_disclosure():
    tmp = tempfile.mkdtemp()
    try:
        root = make_current_review_chain(tmp)
        os.unlink(os.path.join(root, "合规", "ai_usage.json"))
        errors = mc.review_receipt_prerequisite_errors(root)
        assert any("缺 合规/ai_usage.json" in message for message in errors)
        assert any("provenance assets 已过期：合规/ai_usage.json" in message for message in errors)
    finally:
        shutil.rmtree(tmp)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
    print(f"ok - {len(tests)} tests")


if __name__ == "__main__":
    main()
