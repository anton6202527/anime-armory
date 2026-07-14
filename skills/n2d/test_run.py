#!/usr/bin/env python3
"""n2d 编排器 run.py 测试。

从本目录跑：
    cd skills/n2d && python3 -m pytest test_run.py
"""
import os
import json
import sys
import subprocess
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import run  # noqa: E402
from skill_snapshot import artifact_fingerprint  # noqa: E402  (run.py 已把 _lib 入 sys.path)
from signoff_contract import new_manifest, profile_spec, record_approval, write_manifest  # noqa: E402


def _sign_profile(root, profile, ep="第1集"):
    spec = profile_spec(Path(root), profile, ep if profile != "p1" else "")
    payload = new_manifest(
        Path(root), artifact_scope=spec["artifact_scope"], episode=spec["episode"], author_id="automation:n2d",
        input_paths=spec["input_paths"], evidence_paths=spec["evidence_paths"], required_role_groups=spec["required_role_groups"],
    )
    roles = {
        "p1": ("director", "producer"),
        "table_read": ("director",),
        "p2": ("director", "producer"),
    }[profile]
    for role in roles:
        payload = record_approval(payload, Path(root), reviewer_id="user:fixture", reviewer_role=role, evidence_paths=spec["evidence_paths"])
    write_manifest(Path(root) / spec["signoff_path"], payload)


def _fresh_fp(root, files=()):
    """A real inputs_fingerprint that recomputes fresh (empty file set never drifts).

    image_qc/gate 报告必须带 inputs_fingerprint，下游护栏据此证「报告对应当前产物」；
    测试夹具用空文件集的真指纹保持 fresh，模拟一份新鲜报告。"""
    return artifact_fingerprint(root, list(files))

HEADER = ("| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 "
          "| 字幕中 | 字幕英 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 | 验收 |")
SEP = "|" + "---|" * 17


def make_work(cells, settings=None):
    """造一个临时作品根，cells = 第1集 的物料列（raw 起到 验收）。"""
    d = tempfile.mkdtemp()
    row = "| 第1集 | 1000 | " + " | ".join(cells) + " |"
    open(os.path.join(d, "_进度.md"), "w", encoding="utf-8").write(
        "# 进度\n\n" + HEADER + "\n" + SEP + "\n" + row + "\n")
    if settings:
        open(os.path.join(d, "_设置.md"), "w", encoding="utf-8").write(settings)
    return d


# 15 个物料列：raw 剧本改编 bgm 封面 配音 分镜设计 素材清单 字幕中 字幕英 出图prompt 出图 视频prompt 视频 成片 验收
ALL_DONE_TO = {
    "script_stage1": ["✅", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜"],
    "voice":         ["✅", "✅", "✅", "✅", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜"],
    "image_prompt":  ["✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜"],
    "image":         ["✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "0/10", "⬜", "⬜", "⬜", "⬜"],
    "video_prompt":  ["✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "⬜", "⬜", "⬜", "⬜"],
    "compose":       ["✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "⬜", "⬜"],
    "review":        ["✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "⬜"],
}


class _CP:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _write_clean_image_qc(root, ep="第1集"):
    out_dir = os.path.join(root, "生产数据", "image_qc", ep)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"image_qc_{ep}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"qc_environment": {"precision_level": "full"}, "summary": {"hard_blocks": 0, "verdict": "ok"},
                   "inputs_fingerprint": _fresh_fp(root)}, fh)


def _write_boundary_review(root, raw_text, decision="keep", notes="已复核双侧语义，保留当前边界。"):
    """用当前 boundary_audit 生成 v2 双侧合同，再模拟人审签收。"""
    os.makedirs(os.path.join(root, "脚本"), exist_ok=True)
    script = os.path.join(run.SKILLS_DIR, "n2d-script", "scripts", "boundary_review.py")
    subprocess.run([sys.executable, script, "draft", root, "--write"], check=True, capture_output=True, text=True)
    path = os.path.join(root, "脚本", "boundary_review.json")
    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)
    for row in payload.get("reviews") or []:
        row["decision"] = decision
        row["notes"] = notes
        row["reviewed_by"] = "user:fixture"
        row["reviewed_at"] = "2026-07-14T10:00:00+08:00"
        row["semantic_evidence"] = {
            "left": "左侧冲突已完成局部回报，悬念为刻意跨集延迟。",
            "right": "右侧开场立即承接同一人物、动作与观众问题。",
        }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def _write_confirmed_development_pack(root):
    base = os.path.join(root, "开发包")
    os.makedirs(base, exist_ok=True)
    for name in ("series_bible.md", "pilot_greenlight.md"):
        with open(os.path.join(base, name), "w", encoding="utf-8") as fh:
            fh.write("status: confirmed\n# 已填写\n已填写完整开发判断。\n")
    for name in ("adaptation_strategy.json", "season_arc.json", "production_feasibility.json"):
        with open(os.path.join(base, name), "w", encoding="utf-8") as fh:
            json.dump({"kind": "fixture", "status": "confirmed", "content": "已填写"}, fh, ensure_ascii=False)
    _sign_profile(root, "p1")


def _write_confirmed_director_pack(root, ep="第1集"):
    ep_dir = os.path.join(root, "脚本", ep)
    os.makedirs(ep_dir, exist_ok=True)
    payloads = {
        "director_beat_sheet.json": {"kind": "fixture", "status": "confirmed", "beats": [{"beat_id": "Beat_01", "dramatic_function": "冲突"}]},
        "axis_blocking_map.json": {
            "kind": "fixture",
            "status": "confirmed",
            "scene_axis_rules": [{"main_axis": "A-B"}],
            "shot_reverse_patterns": [{
                "pattern_id": "no_shot_reverse_in_fixture",
                "mode": "none_until_storyboard_uses_dialogue_shot_reverse",
                "applies_to": [],
            }],
        },
        "shot_progression_plan.json": {"kind": "fixture", "status": "confirmed", "progressions": [{"beat_id": "Beat_01", "camera_move": "缓慢推镜"}]},
        "transition_map.json": {"kind": "fixture", "status": "confirmed", "seams": [{
            "seam_id": "Seam_01", "from_beat": "Beat_01", "to_beat": "Beat_02",
            "transition_type": "eyeline", "seam_mode": "eyeline_cut",
            "seam_mode_source": "explicit",
            "seam_evidence": {"eyeline_source": "CHAR_A", "eyeline_target": "CHAR_B", "axis": "A-B axis"},
            "need_endframe": False,
        }]},
        "vertical_composition_plan.json": {"kind": "fixture", "status": "confirmed", "composition_rules": {"safe_zone": "bottom clear"}},
        "edit_rhythm_map.json": {"kind": "fixture", "status": "confirmed", "timeline": {"first_3s_hook": "visual conflict"}},
    }
    for name, data in payloads.items():
        with open(os.path.join(ep_dir, name), "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
    table_signoff = os.path.join(ep_dir, "table_read_signoff.json")
    if not os.path.exists(table_signoff):
        open(table_signoff, "w", encoding="utf-8").write('{"status":"fixture-upstream"}')
    _sign_profile(root, "p2", ep)


def _write_confirmed_preventive_contract(root, ep="第1集"):
    ep_dir = os.path.join(root, "脚本", ep)
    os.makedirs(ep_dir, exist_ok=True)
    with open(os.path.join(ep_dir, "preventive_contracts.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "kind": "n2d_preventive_contracts",
            "version": 1,
            "episode": ep,
            "status": "confirmed",
            "episode_promise": {
                "opening_hook": "开场危机到来。",
                "promise": "本集承诺查明令牌去向。",
                "obstacle": "对手阻挡。",
                "payoff_or_progress": "查到线索。",
                "cliffhanger": "门外传来脚步声。",
            },
            "shots": [],
            "reference_slots": {"characters": [], "assets": [], "scenes": []},
            "interaction_physics": [],
            "audio_timing": {
                "mode": "原生音画",
                "post_dub": {"fit_strategy": "n/a", "overflow_policy": "n/a"},
                "native_av_policy": {"lipsync_policy": "native", "subtitle_policy": "compose overlay", "voice_identity_policy": "native_voice_identity"},
                "dialogue_closeups": [],
            },
        }, fh, ensure_ascii=False)


def _write_confirmed_story_acceptance(root, ep="第1集", kind="table_read"):
    ep_dir = os.path.join(root, "脚本", ep)
    os.makedirs(ep_dir, exist_ok=True)
    json_name = "table_read_packet.json" if kind == "table_read" else "animatic_packet.json"
    md_name = "table_read_packet.md" if kind == "table_read" else "animatic_packet.md"
    if kind == "table_read":
        input_rels = [
            f"脚本/{ep}/voiceover.txt",
            f"合成/{ep}/配音/时长清单.json",
            f"生产数据/script_quality_contract_{ep}.json",
        ]
    else:
        input_rels = [
            f"脚本/{ep}/storyboard.json",
            f"脚本/{ep}/镜头时长.json",
            f"脚本/{ep}/字幕_中文.srt",
            f"合成/{ep}/配音/voice_zh.wav",
        ]
    payload = {
        "kind": "n2d_table_read_packet" if kind == "table_read" else "n2d_animatic_packet",
        "version": 1,
        "episode": ep,
        "status": "confirmed",
        "inputs_fingerprint": artifact_fingerprint(root, input_rels),
        "acceptance": {
            "reviewer": "fixture",
            "dialogue_voice_distinct": "accepted",
            "duration_risk_understood": "accepted",
        },
    }
    with open(os.path.join(ep_dir, json_name), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    with open(os.path.join(ep_dir, md_name), "w", encoding="utf-8") as fh:
        fh.write(f"---\nkind: {payload['kind']}\nstatus: confirmed\n---\n# confirmed\n")
    _sign_profile(root, kind, ep)


# ── 前沿解析 + stage key 反查（真实 fixture 文件）──────────────────────────────
def test_resolve_frontier_image():
    root = make_work(ALL_DONE_TO["image"])
    route = run.resolve_frontier(root)
    assert route["col"] == "出图"
    assert run.stage_key_of(route) == "image"


def test_resolve_frontier_voice():
    # 这里显式写入「配音先行」以固定 voice 前沿语义。
    root = make_work(ALL_DONE_TO["voice"], settings="# _设置\n- 制作模式: 配音先行\n")
    route = run.resolve_frontier(root)
    assert run.stage_key_of(route) == "voice"


def test_resolve_frontier_native_av_script_stage2_labels_timing_not_voice():
    root = make_work(ALL_DONE_TO["voice"], settings="# _设置\n- 制作模式: 原生音画\n")
    route = run.resolve_frontier(root)
    assert run.stage_key_of(route) == "script_stage2"
    assert "原生音画" in route["label"]
    assert "配音后" not in route["cmd"]
    assert "storyboard.json" in route["note"]


def test_next_action_missing_progress_returns_recovery_card():
    root = tempfile.mkdtemp()
    na = run.next_action(root, "第2集")
    assert na["stop_reason"] == "blocked_by_entry_check"
    assert na["action_card"]["block_reason"] == "missing_progress"
    assert "split_novel.py" in na["action_card"]["recovery_command"]


def test_decide_uses_mode_aware_route_command():
    root = make_work(ALL_DONE_TO["voice"], settings="# _设置\n- 制作模式: 原生音画\n")
    route = run.resolve_frontier(root)
    na = run.decide(root, route, "script_stage2", run.Probes())
    cmd = na["action_card"]["exact_command"]
    assert "原生音画脚本时长定稿" in cmd
    assert "配音后" not in cmd


def test_resolve_frontier_done():
    cells = ["✅"] * 15
    root = make_work(cells)
    assert run.resolve_frontier(root) is None


def test_video_done_is_default_done_without_compose_opt_in():
    root = make_work(ALL_DONE_TO["compose"])
    assert run.resolve_frontier(root) is None


def test_video_done_routes_to_compose_when_opted_in():
    root = make_work(ALL_DONE_TO["compose"], settings="# _设置\n- 制作模式: 配音先行\n- 合成阶段: 启用\n")
    route = run.resolve_frontier(root)
    assert route["col"] == "成片"
    assert run.stage_key_of(route) == "compose"


def test_resolve_frontier_review_after_compose():
    root = make_work(ALL_DONE_TO["review"])
    route = run.resolve_frontier(root)
    assert route["col"] == "验收"
    assert run.stage_key_of(route) == "review"


def test_old_progress_without_review_column_routes_to_review():
    d = tempfile.mkdtemp()
    old_header = ("| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 "
                  "| 字幕中 | 字幕英 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 |")
    old_sep = "|" + "---|" * 16
    row = "| 第1集 | 1000 | " + " | ".join(["✅"] * 14) + " |"
    open(os.path.join(d, "_进度.md"), "w", encoding="utf-8").write(
        "# 进度\n\n" + old_header + "\n" + old_sep + "\n" + row + "\n")
    route = run.resolve_frontier(d)
    assert route["col"] == "验收"
    assert route["missing_progress_column"] == "验收"


def test_next_action_done_after_review_signoff():
    cells = ["✅"] * 15
    root = make_work(cells)
    na = run.next_action(root, "第1集")
    assert na["stop_reason"] == "done"
    assert "clip_delivery_complete" in na["action_card"]["to_user"]


def test_production_mode_menu_defaults_to_hybrid_auto_routing():
    root = make_work(ALL_DONE_TO["script_stage1"])
    menu = run._menu(root, "制作模式")
    assert menu["options"][:4] == ["混合自动路由", "配音先行", "原生音画", "先出视频后配音"]
    assert menu["default_preselect"] == "混合自动路由"


def test_base_visual_style_menu_includes_reference_media_intake():
    root = make_work(ALL_DONE_TO["script_stage1"])
    menu = run._menu(root, "基础视觉风格")
    assert menu["options"][0] == "冷灰写实3D国风漫剧"
    assert menu["default_preselect"] == "冷灰写实3D国风漫剧"
    assert "真实3D人物质感 + 电影叙事镜头感" in menu["options"]
    assert "韩漫精致清透" in menu["options"]
    assert "纸片剪影 / 定格动画" in menu["options"]
    assert "参考图片/视频自动识别" in menu["options"]
    assert menu["transient_options"] == ["参考图片/视频自动识别"]
    assert menu["options"].index("参考图片/视频自动识别") < menu["options"].index("自定义")
    assert "不要把该临时入口本身写入 _设置.md" in menu["follow_up"]


def test_stage_key_of_voice_redirect():
    # 先出视频后配音模式下的 compose→voice 重定向特例
    route = {"ep": "第1集", "col": "成片", "label": "补真实配音", "skill": "n2d-voice"}
    assert run.stage_key_of(route) == "voice"


def test_stage_key_of_post_lipsync_redirect():
    route = {"ep": "第1集", "col": "成片", "label": "完成后期口型/表演 pass", "skill": "n2d-video"}
    assert run.stage_key_of(route) == "video"


def test_stage_key_redirect_uses_structured_field_not_display_label():
    route = {"ep": "第1集", "col": "成片", "label": "任意本地化标题", "skill": "n2d-compose", "redirect_stage_key": "voice"}
    assert run.stage_key_of(route) == "voice"


# ── 纯决策 decide()：stop 分类 + 优先级 ───────────────────────────────────────
def _route(stage_key, ep="第1集"):
    spec = run.stage_for_key(stage_key)
    return {"ep": ep, "col": spec["progress_columns"][0], "label": spec["label"], "skill": spec["owner"]}


def test_decide_agent_gen():
    root = make_work(ALL_DONE_TO["voice"])
    na = run.decide(root, _route("script_stage2"), "script_stage2", run.Probes())
    assert na["stop_reason"] == "needs_agent_gen"
    assert na["auto_continue"] is False


def test_decide_action_card_carries_supervisor_metadata():
    root = make_work(ALL_DONE_TO["voice"])
    na = run.decide(root, _route("video_prompt"), "video_prompt", run.Probes())
    assert na["action_contract"]["stage_key"] == "video_prompt"
    assert na["trace"]["trace_id"].startswith("tr_")
    assert na["action_card"]["specialist"]["name"] == "n2d-visual-agent"
    assert na["action_card"]["context_pack"]["relpath"].endswith("context_pack_第1集_video_prompt.json")
    assert na["action_card"]["creative_loop"]["relpath"].endswith("creative_loop_第1集_video_prompt.json")


def test_decide_payment_confirm_image_carries_granularity_menu():
    root = make_work(ALL_DONE_TO["image"])
    na = run.decide(root, _route("image"), "image", run.Probes())
    assert na["stop_reason"] == "needs_payment_confirm"
    assert na["action_card"]["menu"][0]["choice_point"] == "生成粒度"


def test_decide_video_first_voice_uses_rough_timing_without_payment_menu():
    root = make_work(ALL_DONE_TO["voice"], settings="- 制作模式: 先出视频后配音\n")
    na = run.decide(root, _route("voice"), "voice", run.Probes())
    assert na["stop_reason"] == "needs_stage_execution"
    assert "无 WAV 时间基准" in na["action_card"]["headline"]
    assert na["action_card"]["expected_writeback"] == "配音=⏳rough"
    assert na["action_card"]["recommended_backend"] == "纯文本估时（不调用 TTS）"
    assert "voice_preflight.py prepare" in na["action_card"]["exact_command"]
    assert "menu" not in na["action_card"]
    assert na["action_contract"]["stop_policy"] == "needs_stage_execution"
    assert na["action_contract"]["requires_human_approval"] is False


def test_decide_hybrid_voice_preflight_creates_no_wav_contract():
    root = make_work(ALL_DONE_TO["voice"], settings="- 制作模式: 混合自动路由\n")
    na = run.decide(root, _route("voice"), "voice", run.Probes())
    assert na["stop_reason"] == "needs_stage_execution"
    assert "选角先行" in na["action_card"]["headline"]
    assert "不生成整集占位/静音 WAV" in na["action_card"]["to_user"]


def test_decide_voice_first_payment_menu_is_backend():
    root = make_work(ALL_DONE_TO["voice"], settings="# _设置\n- 制作模式: 配音先行\n")
    na = run.decide(root, _route("voice"), "voice", run.Probes())
    assert na["stop_reason"] == "needs_payment_confirm"
    assert na["action_card"]["menu"][0]["choice_point"] == "配音后端"


def test_voice_first_compliance_gap_blocks_before_paid_tts():
    root = make_work(ALL_DONE_TO["voice"], settings="# _设置\n- 制作模式: 配音先行\n")
    na = run.decide(root, _route("voice"), "voice", run.Probes(compliance_gap=True))
    assert na["stop_reason"] == "needs_compliance"


def test_hybrid_text_only_voice_preflight_does_not_require_paid_compliance():
    root = make_work(ALL_DONE_TO["voice"], settings="# _设置\n- 制作模式: 混合自动路由\n")
    na = run.decide(root, _route("voice"), "voice", run.Probes(compliance_gap=True))
    assert na["stop_reason"] == "needs_stage_execution"


def test_all_returned_stop_reasons_are_registered():
    expected = {
        "needs_agent_gen", "needs_stage_execution", "needs_payment_confirm", "needs_choice",
        "needs_compliance", "needs_acceptance_signoff", "blocked_by_entry_check",
        "capability_evidence_required", "blocked_by_gate", "blocked_by_image_qc",
        "blocked_by_review_acceptance", "prework_failed", "env_missing", "auto_ran", "done",
        "unknown_stage",
    }
    assert set(run.STOP_REASONS) == expected


def test_decide_compose_payment_menu_is_bgm():
    root = make_work(ALL_DONE_TO["compose"])
    na = run.decide(root, _route("compose"), "compose", run.Probes())
    assert na["stop_reason"] == "needs_payment_confirm"
    assert na["action_card"]["menu"][0]["choice_point"] == "BGM来源"
    bundle = na["action_card"]["post_qc_bundle"]
    assert bundle["scope"] == "pre_compose_review"
    assert any("review_ui.py" in cmd and "--export-findings" in cmd for cmd in bundle["commands"])
    assert not any("release_verdict.py" in cmd for cmd in bundle["commands"])


def test_decide_review_requires_signoff_after_evidence_passes():
    root = make_work(ALL_DONE_TO["review"])
    na = run.decide(root, _route("review"), "review", run.Probes())
    assert na["stop_reason"] == "needs_acceptance_signoff"
    assert "验收" in na["action_card"]["exact_command"]
    commands = na["action_card"]["post_qc_bundle"]["commands"]
    assert any("progress.py audit-dag" in cmd for cmd in commands)
    assert any("production_breakdown.py" in cmd and "check --json" in cmd for cmd in commands)
    assert any("failure_taxonomy.py" in cmd and "--write" in cmd for cmd in commands)
    assert any("release_verdict.py" in cmd and "--write" in cmd for cmd in commands)


def test_review_acceptance_outputs_runs_episode_closeout(monkeypatch):
    root = make_work(ALL_DONE_TO["review"])
    calls = []

    def fake_run(cmd):
        calls.append(cmd)
        return _CP(0, json.dumps({"findings": [], "status": "pass"}, ensure_ascii=False), "")

    monkeypatch.setattr(run, "_run", fake_run)
    monkeypatch.setattr(run, "_review_acceptance_issue", lambda _root, _ep: None)

    probes = run.Probes()
    run._run_review_acceptance_outputs(root, "第1集", probes)

    names = [os.path.basename(cmd[1]) for cmd in calls]
    assert names[:2] == ["progress.py", "production_breakdown.py"]
    assert "failure_taxonomy.py" in names
    assert names[-1] == "release_verdict.py"
    assert not probes.review_acceptance_block


def test_review_acceptance_outputs_preserves_warn_status(monkeypatch):
    root = make_work(ALL_DONE_TO["review"])

    def fake_run(cmd):
        name = os.path.basename(cmd[1])
        status = "warn" if name == "creative_governance.py" else "pass"
        return _CP(0, json.dumps({"findings": [], "status": status}, ensure_ascii=False), "")

    monkeypatch.setattr(run, "_run", fake_run)
    monkeypatch.setattr(run, "_review_acceptance_issue", lambda _root, _ep: None)

    probes = run.Probes()
    run._run_review_acceptance_outputs(root, "第1集", probes)

    creative = next(row for row in probes.prework if row["step"] == "creative_governance")
    assert creative["status"] == "warn"
    assert not probes.review_acceptance_block


def test_action_card_includes_prework_status_summary():
    root = make_work(ALL_DONE_TO["review"])
    probes = run.Probes(prework=[
        {"step": "creative_governance", "status": "warn"},
        {"step": "release_verdict", "status": "pass"},
    ])

    na = run.decide(root, _route("review"), "review", probes)

    summary = na["action_card"]["prework_status_summary"]
    assert summary["counts"]["warn"] == 1
    assert summary["counts"]["pass"] == 1


def test_decide_compliance_blocks_paid_stage():
    root = make_work(ALL_DONE_TO["image"])
    na = run.decide(root, _route("image"), "image", run.Probes(compliance_gap=True))
    assert na["stop_reason"] == "needs_compliance"


def test_decide_entry_check_blocks_before_generation():
    root = make_work(ALL_DONE_TO["image"])
    p = run.Probes(entry_check_block="源文本已漂移")
    na = run.decide(root, _route("image"), "image", p)
    assert na["stop_reason"] == "blocked_by_entry_check"


def test_entry_check_block_includes_repair_preflight_command():
    root = make_work(ALL_DONE_TO["image"])
    msg = run._entry_check_block([{
        "step": "update_plan",
        "episode": "第1集",
        "status": "rebuild_needed",
        "plan": {"rebuild_needed": True, "plan_md": "生产数据/skill_update_plan_第1集.md"},
    }], "image", root)

    assert msg
    assert "repair_preflight.py" in msg
    assert root in msg
    assert "第1集" in msg
    assert "--stage image" in msg


def test_gather_probes_auto_runs_repair_preflight_for_entry_block(monkeypatch):
    root = make_work(ALL_DONE_TO["image"])
    calls = {"entry": 0, "repair": 0}

    def fake_entry_checks(*_args, **_kwargs):
        calls["entry"] += 1
        if calls["entry"] == 1:
            return [{
                "step": "update_plan",
                "episode": "第1集",
                "status": "rebuild_needed",
                "plan": {"rebuild_needed": True, "plan_md": "生产数据/skill_update_plan_第1集.md"},
            }]
        return []

    def fake_repair(p, *_args, **_kwargs):
        calls["repair"] += 1
        p.prework.append({"step": "repair_preflight", "status": "pass"})
        return "repair ok"

    monkeypatch.setattr(run, "entry_checks", fake_entry_checks)
    monkeypatch.setattr(run, "_run_repair_preflight_prework", fake_repair)
    monkeypatch.setattr(run, "_run", lambda *a, **k: _CP(0, '{"status":"pass","summary":{"pass":1}}', ""))

    probes = run.gather_probes(root, _route("image"), "image")

    assert calls["entry"] >= 2
    assert calls["repair"] == 1
    assert probes.entry_check_block is None
    assert any(row["step"] == "repair_preflight" for row in probes.prework)


def test_decide_capability_evidence_blocks_before_video():
    root = make_work(ALL_DONE_TO["video_prompt"])
    p = run.Probes(capability_block="conservative 能力档")
    na = run.decide(root, _route("video"), "video", p)
    assert na["stop_reason"] == "capability_evidence_required"


def test_decide_gate_block_passes_through_recovery():
    root = make_work(ALL_DONE_TO["image"])
    gate = {"stage": "image", "blocked": True, "return_to_stage": "image_prompt",
            "affected_artifacts": ["出图/第1集/图片"], "rerun_scope": "Clip_03",
            "findings_path": "/tmp/x.json"}
    na = run.decide(root, _route("image"), "image", run.Probes(gate=gate))
    assert na["stop_reason"] == "blocked_by_gate"
    assert na["gate"]["return_to_stage"] == "image_prompt"


def test_decide_image_qc_block_is_not_env_missing():
    root = make_work(ALL_DONE_TO["image"])
    p = run.Probes(image_qc_block="image_qc 仍有硬阻断")
    na = run.decide(root, _route("video"), "video", p)
    assert na["stop_reason"] == "blocked_by_image_qc"
    assert "image_qc" in na["action_card"]["headline"]
    assert "--prop-shape-report" in na["action_card"]["exact_command"]


def test_decide_env_missing_top_priority():
    # env 缺失 > image_qc 阻断 > gate 阻断 > 合规缺口：三者同时存在时 env 优先
    root = make_work(ALL_DONE_TO["image"])
    p = run.Probes(env_missing="Codex（down）",
                   image_qc_block="image_qc block",
                   gate={"stage": "image", "blocked": True},
                   compliance_gap=True)
    na = run.decide(root, _route("image"), "image", p)
    assert na["stop_reason"] == "env_missing"


def test_decide_prework_block_stops_before_agent_generation():
    root = make_work(ALL_DONE_TO["image_prompt"])
    p = run.Probes(prework_block="identity adapter matrix 刷新失败")
    na = run.decide(root, _route("image_prompt"), "image_prompt", p)
    assert na["stop_reason"] == "prework_failed"
    assert "不能把 warn/skip 当放行" in na["action_card"]["to_user"]


def test_decide_first_run_choice_package():
    root = make_work(ALL_DONE_TO["script_stage1"])
    p = run.Probes(pending_choices=["制作模式", "基础视觉风格"])
    na = run.decide(root, _route("script_stage1"), "script_stage1", p)
    assert na["stop_reason"] == "needs_choice"
    cps = [m["choice_point"] for m in na["action_card"]["menu"]]
    assert "制作模式" in cps and "基础视觉风格" in cps
    assert "生视频后端选择已后移到 n2d-video" in na["action_card"]["to_user"]


def test_gather_probes_blocks_script_stage1_on_unreviewed_boundary_risk():
    root = make_work(ALL_DONE_TO["script_stage1"], settings="- 制作模式: 原生音画\n- 基础视觉风格: 写实电影感\n")
    ep_dir = os.path.join(root, "脚本", "第1集")
    os.makedirs(ep_dir, exist_ok=True)
    open(os.path.join(ep_dir, "raw.txt"), "w", encoding="utf-8").write("她走进屋里。\n然后坐下。\n")

    probes = run.gather_probes(root, _route("script_stage1"), "script_stage1")

    assert probes.prework_block and "boundary_audit" in probes.prework_block
    assert any(pw["step"] == "boundary_audit" and pw["status"] == "block" for pw in probes.prework)


def test_gather_probes_does_not_block_short_episode_with_strong_hook():
    root = make_work(ALL_DONE_TO["script_stage1"], settings="- 制作模式: 原生音画\n- 基础视觉风格: 写实电影感\n")
    _write_confirmed_development_pack(root)
    ep_dir = os.path.join(root, "脚本", "第1集")
    os.makedirs(ep_dir, exist_ok=True)
    open(os.path.join(ep_dir, "raw.txt"), "w", encoding="utf-8").write("第一章\n她被逼到宫墙下。\n门外突然传来脚步声！\n")

    probes = run.gather_probes(root, _route("script_stage1"), "script_stage1")

    assert not probes.prework_block
    assert any(pw["step"] == "boundary_audit" and pw["status"] == "pass" for pw in probes.prework)


def test_gather_probes_blocks_legacy_markdown_boundary_review():
    root = make_work(ALL_DONE_TO["script_stage1"], settings="- 制作模式: 原生音画\n- 基础视觉风格: 写实电影感\n")
    ep_dir = os.path.join(root, "脚本", "第1集")
    os.makedirs(ep_dir, exist_ok=True)
    open(os.path.join(ep_dir, "raw.txt"), "w", encoding="utf-8").write("她走进屋里。\n然后坐下。\n")
    open(os.path.join(root, "脚本", "_拆集复核.md"), "w", encoding="utf-8").write("# 已复核\n")

    probes = run.gather_probes(root, _route("script_stage1"), "script_stage1")

    assert probes.prework_block and "boundary_review.py draft" in probes.prework_block
    assert any(pw["step"] == "boundary_audit" and pw["status"] == "block" for pw in probes.prework)


def test_gather_probes_allows_script_stage1_when_boundary_review_json_valid():
    root = make_work(ALL_DONE_TO["script_stage1"], settings="- 制作模式: 原生音画\n- 基础视觉风格: 写实电影感\n")
    _write_confirmed_development_pack(root)
    ep_dir = os.path.join(root, "脚本", "第1集")
    os.makedirs(ep_dir, exist_ok=True)
    raw = "她走进屋里。\n然后坐下。\n"
    open(os.path.join(ep_dir, "raw.txt"), "w", encoding="utf-8").write(raw)
    _write_boundary_review(root, raw)

    probes = run.gather_probes(root, _route("script_stage1"), "script_stage1")

    assert not probes.prework_block
    assert any(pw["step"] == "boundary_audit" and pw["status"] == "reviewed" for pw in probes.prework)


def test_gather_probes_blocks_script_stage1_without_confirmed_development_pack():
    root = make_work(
        ALL_DONE_TO["script_stage1"],
        settings="- 制作模式: 原生音画  # source=explicit_user\n- 基础视觉风格: 写实电影感  # source=explicit_user\n",
    )
    ep_dir = os.path.join(root, "脚本", "第1集")
    os.makedirs(ep_dir, exist_ok=True)
    open(os.path.join(ep_dir, "raw.txt"), "w", encoding="utf-8").write("第一章\n她被逼到宫墙下。\n门外突然传来脚步声！\n")

    probes = run.gather_probes(root, _route("script_stage1"), "script_stage1")

    assert probes.prework_block and "P-1 开发包" in probes.prework_block
    assert any(pw["step"] == "development_pack" and pw["status"] == "block" for pw in probes.prework)


def test_gather_probes_blocks_script_stage1_without_source_comprehension_contract():
    root = make_work(
        ALL_DONE_TO["script_stage1"],
        settings="- 制作模式: 原生音画  # source=explicit_user\n- 基础视觉风格: 写实电影感  # source=explicit_user\n",
    )
    novel_dir = os.path.join(root, "小说")
    os.makedirs(novel_dir, exist_ok=True)
    open(os.path.join(novel_dir, "测试剧.txt"), "w", encoding="utf-8").write(
        ("他说他已经知道了这件事。我们现在就去那个地方，可以吗？"
         "她笑着摇了摇头，说不是这样的。这个故事的开头其实很简单。") * 8
    )

    probes = run.gather_probes(root, _route("script_stage1"), "script_stage1")

    assert probes.prework_block and "源理解合同" in probes.prework_block
    assert any(pw["step"] == "source_comprehension_gate" and pw["status"] == "block" for pw in probes.prework)


def test_gather_probes_prioritizes_first_run_choices_before_development_pack():
    root = make_work(ALL_DONE_TO["script_stage1"])
    ep_dir = os.path.join(root, "脚本", "第1集")
    os.makedirs(ep_dir, exist_ok=True)
    open(os.path.join(ep_dir, "raw.txt"), "w", encoding="utf-8").write("第一章\n她被逼到宫墙下。\n门外突然传来脚步声！\n")

    probes = run.gather_probes(root, _route("script_stage1"), "script_stage1")
    na = run.decide(root, _route("script_stage1"), "script_stage1", probes)

    assert probes.pending_choices
    assert not probes.prework_block
    assert na["stop_reason"] == "needs_choice"


def test_gather_probes_blocks_script_stage2_without_confirmed_director_pack():
    root = make_work(ALL_DONE_TO["voice"], settings="- 制作模式: 原生音画\n- 基础视觉风格: 写实电影感\n")
    ep_dir = os.path.join(root, "脚本", "第1集")
    os.makedirs(ep_dir, exist_ok=True)
    open(os.path.join(ep_dir, "voiceover.txt"), "w", encoding="utf-8").write("她推门而入。\n他抬头看见令牌。\n")
    _write_confirmed_preventive_contract(root)

    probes = run.gather_probes(root, _route("script_stage2"), "script_stage2")
    na = run.decide(root, _route("script_stage2"), "script_stage2", probes)

    assert probes.prework_block and "围读验收包" in probes.prework_block
    assert any("P-2 导演排戏包" in row["message"] for row in probes.prework_blocks)
    assert any("P-2 导演排戏包" in row["message"] for row in na["action_card"]["prework_blocks"])
    assert any(pw["step"] == "director_blocking_pack" and pw["status"] == "block" for pw in probes.prework)
    assert os.path.exists(os.path.join(root, "脚本", "第1集", "director_beat_sheet.json"))


def test_gather_probes_blocks_script_stage2_without_episode_promise_contract():
    root = make_work(ALL_DONE_TO["voice"], settings="- 制作模式: 原生音画\n- 基础视觉风格: 写实电影感\n")
    ep_dir = os.path.join(root, "脚本", "第1集")
    os.makedirs(ep_dir, exist_ok=True)
    open(os.path.join(ep_dir, "voiceover.txt"), "w", encoding="utf-8").write("她推门而入。\n")
    _write_confirmed_director_pack(root)

    probes = run.gather_probes(root, _route("script_stage2"), "script_stage2")
    na = run.decide(root, _route("script_stage2"), "script_stage2", probes)

    assert probes.prework_block and "围读验收包" in probes.prework_block
    assert any("预防式合同" in row["message"] for row in probes.prework_blocks)
    assert any("预防式合同" in row["message"] for row in na["action_card"]["prework_blocks"])
    assert any(pw["step"] == "preventive_contracts" and pw["status"] == "block" for pw in probes.prework)
    assert os.path.exists(os.path.join(root, "脚本", "第1集", "preventive_contracts.json"))


def test_gather_probes_allows_script_stage2_with_confirmed_director_pack():
    root = make_work(ALL_DONE_TO["voice"], settings="- 制作模式: 原生音画\n- 基础视觉风格: 写实电影感\n")
    ep_dir = os.path.join(root, "脚本", "第1集")
    os.makedirs(ep_dir, exist_ok=True)
    open(os.path.join(ep_dir, "voiceover.txt"), "w", encoding="utf-8").write("她推门而入。\n他抬头看见令牌。\n")
    _write_confirmed_preventive_contract(root)
    _write_confirmed_director_pack(root)
    _write_confirmed_story_acceptance(root, kind="table_read")
    # P-2 input fingerprint includes the table-read signoff, so refresh its
    # approvals after that upstream packet is signed.
    _sign_profile(root, "p2", "第1集")

    probes = run.gather_probes(root, _route("script_stage2"), "script_stage2")

    assert not probes.prework_block
    assert any(pw["step"] == "director_blocking_pack" and pw["status"] == "pass" for pw in probes.prework)


def test_gather_probes_blocks_image_prompt_on_source_adaptation_audit(monkeypatch):
    root = make_work(ALL_DONE_TO["image_prompt"])

    def fake_run(cmd):
        if cmd[1].endswith("source_adaptation_audit.py"):
            return _CP(1, json.dumps({"findings": [{"severity": "warn", "message": "源文关键事件漏改"}]}, ensure_ascii=False), "")
        return _CP(0, '{"findings_path": ""}', "")

    monkeypatch.setattr(run, "_run", fake_run)
    probes = run.gather_probes(root, _route("image_prompt"), "image_prompt")

    assert probes.prework_block and "source_adaptation_audit" in probes.prework_block
    assert any(pw["step"] == "source_adaptation_audit" and pw["status"] == "block" for pw in probes.prework)


def test_gather_probes_blocks_image_prompt_on_beat_audit(monkeypatch):
    root = make_work(ALL_DONE_TO["image_prompt"])

    def fake_run(cmd):
        if cmd[1].endswith("source_adaptation_audit.py"):
            return _CP(0, json.dumps({"findings": []}), "")
        if cmd[1].endswith("beat_audit.py"):
            return _CP(1, json.dumps({"findings": [{"severity": "warn", "msg": "缺集尾钩"}]}, ensure_ascii=False), "")
        return _CP(0, '{"findings_path": ""}', "")

    monkeypatch.setattr(run, "_run", fake_run)
    probes = run.gather_probes(root, _route("image_prompt"), "image_prompt")

    assert probes.prework_block and "beat_audit" in probes.prework_block
    assert any(pw["step"] == "beat_audit" and pw["status"] == "block" for pw in probes.prework)


def test_gather_probes_blocks_image_prompt_on_series_retention_gate(monkeypatch):
    root = make_work(ALL_DONE_TO["image_prompt"])
    for i in range(1, 4):
        ep_dir = os.path.join(root, "脚本", f"第{i}集")
        os.makedirs(ep_dir, exist_ok=True)
        open(os.path.join(ep_dir, "voiceover.txt"), "w", encoding="utf-8").write(
            f"[镜头1·沈念·惊恐·快] 第{i}集危机来了！ ⚡钩子\n"
            f"[镜头2·沈念·痛快·快] 原来竟是真相。 💥爽点\n"
            f"[镜头3·沈念·阴狠·慢] 下一局才开始。 🪝集尾\n"
        )

    def fake_run(cmd):
        if cmd[1].endswith("beat_audit.py") and "--series" in cmd:
            return _CP(0, json.dumps({
                "duplicates": [["第1集", "第2集", 0.88]],
                "cold_open_chain_findings": [],
                "highlight_climax_findings": [],
            }, ensure_ascii=False), "")
        return _CP(0, json.dumps({"findings": []}, ensure_ascii=False), "")

    monkeypatch.setattr(run, "_run", fake_run)
    probes = run.gather_probes(root, _route("image_prompt"), "image_prompt")

    assert probes.prework_block and "series_retention_gate" in probes.prework_block
    assert any(pw["step"] == "series_retention_gate" and pw["status"] == "block" for pw in probes.prework)


def test_gather_probes_blocks_image_prompt_on_pilot_arc_gate_before_three_eps(monkeypatch):
    root = make_work(ALL_DONE_TO["image_prompt"])

    def fake_run(cmd):
        if cmd[1].endswith("story_integrity_audit.py") and "--strict" in cmd:
            return _CP(1, json.dumps({
                "findings": [{"severity": "warn", "message": "pilot_arc_contract 字段未填全"}],
            }, ensure_ascii=False), "")
        return _CP(0, json.dumps({"findings": []}, ensure_ascii=False), "")

    monkeypatch.setattr(run, "_run", fake_run)
    probes = run.gather_probes(root, _route("image_prompt"), "image_prompt")

    assert probes.prework_block and "pilot_arc_contract" in probes.prework_block
    assert any(pw["step"] == "pilot_arc_contract_gate" and pw["status"] == "block" for pw in probes.prework)


def test_gather_probes_blocks_image_prompt_on_spectacle_contract_audit(monkeypatch):
    root = make_work(ALL_DONE_TO["image_prompt"])

    def fake_run(cmd):
        if cmd[1].endswith("source_adaptation_audit.py") or cmd[1].endswith("beat_audit.py"):
            return _CP(0, json.dumps({"findings": []}), "")
        if cmd[1].endswith("spectacle_contract_audit.py"):
            return _CP(1, json.dumps({"findings": [{"severity": "must", "message": "缺 impact_frame"}]}, ensure_ascii=False), "")
        return _CP(0, '{"findings_path": ""}', "")

    monkeypatch.setattr(run, "_run", fake_run)
    probes = run.gather_probes(root, _route("image_prompt"), "image_prompt")

    assert probes.prework_block and "spectacle_contract_audit" in probes.prework_block
    assert any(pw["step"] == "spectacle_contract_audit" and pw["status"] == "block" for pw in probes.prework)


def test_gather_probes_blocks_image_prompt_on_production_breakdown(monkeypatch):
    root = make_work(ALL_DONE_TO["image_prompt"])

    def fake_run(cmd):
        if cmd[1].endswith("production_breakdown.py"):
            return _CP(1, json.dumps({
                "status": "block",
                "summary": {"required": 3, "pass": 1, "block": 2},
                "check_path": "生产数据/production_breakdown_check_第1集.json",
            }, ensure_ascii=False), "")
        return _CP(0, json.dumps({"findings": [], "summary": {"max_score": 0, "warn_or_higher": 0}}, ensure_ascii=False), "")

    monkeypatch.setattr(run, "_run", fake_run)
    probes = run.gather_probes(root, _route("image_prompt"), "image_prompt")

    assert probes.prework_block and "P-3 制片拆解包" in probes.prework_block
    assert any(pw["step"] == "production_breakdown" and pw["status"] == "block" for pw in probes.prework)


def test_gather_probes_image_prompt_passes_production_breakdown(monkeypatch):
    root = make_work(ALL_DONE_TO["image_prompt"])
    scripts = []

    def fake_run(cmd):
        scripts.append(os.path.basename(cmd[1]))
        if cmd[1].endswith("production_breakdown.py"):
            return _CP(0, json.dumps({
                "status": "pass",
                "summary": {"required": 3, "pass": 3, "block": 0},
                "check_path": "生产数据/production_breakdown_check_第1集.json",
            }, ensure_ascii=False), "")
        return _CP(0, json.dumps({"findings": [], "summary": {"max_score": 0, "warn_or_higher": 0}}, ensure_ascii=False), "")

    monkeypatch.setattr(run, "_run", fake_run)
    probes = run.gather_probes(root, _route("image_prompt"), "image_prompt")

    assert not probes.prework_block
    assert "production_breakdown.py" in scripts
    assert any(pw["step"] == "production_breakdown" and pw["status"] == "pass" for pw in probes.prework)


def test_gather_probes_records_shot_risk_warning_without_block(monkeypatch):
    root = make_work(ALL_DONE_TO["image_prompt"])

    def fake_run(cmd):
        if cmd[1].endswith("source_adaptation_audit.py") or cmd[1].endswith("beat_audit.py"):
            return _CP(0, json.dumps({"findings": []}), "")
        if cmd[1].endswith("shot_risk_audit.py"):
            return _CP(0, json.dumps({"summary": {"max_score": 8, "warn_or_higher": 1}}, ensure_ascii=False), "")
        return _CP(0, '{"findings_path": ""}', "")

    monkeypatch.setattr(run, "_run", fake_run)
    probes = run.gather_probes(root, _route("image_prompt"), "image_prompt")

    assert not probes.prework_block
    assert any(pw["step"] == "shot_risk_audit" and pw["status"] == "warn" for pw in probes.prework)


def test_gather_probes_image_prompt_writes_spectacle_plan_and_probe_pack(monkeypatch):
    root = make_work(ALL_DONE_TO["image_prompt"])
    scripts = []

    def fake_run(cmd):
        scripts.append(os.path.basename(cmd[1]))
        return _CP(0, json.dumps({"findings": [], "summary": {"max_score": 0, "warn_or_higher": 0}}, ensure_ascii=False), "")

    monkeypatch.setattr(run, "_run", fake_run)
    probes = run.gather_probes(root, _route("image_prompt"), "image_prompt")

    assert not probes.prework_block
    assert "spectacle_plan.py" in scripts
    assert "spectacle_probe_pack.py" in scripts


def test_pilot_action_carries_risk_candidates(monkeypatch):
    root = make_work(ALL_DONE_TO["image_prompt"])

    def fake_run(cmd):
        if cmd[1].endswith("shot_risk_audit.py"):
            return _CP(0, json.dumps({
                "pilot_candidates": [{
                    "id": "EP01_CLIP03",
                    "score": 9,
                    "tags": ["high_motion", "long_clip_8s"],
                    "recommendations": ["先补 `_mid`。"],
                }]
            }, ensure_ascii=False), "")
        return _CP(0, "", "")

    monkeypatch.setattr(run, "_run", fake_run)
    na = run.pilot_action(root, "第1集")

    assert na["frontier"]["stage_key"] == "pilot"
    assert na["action_card"]["pilot_clips"][0]["clip"] == "EP01_CLIP03"
    assert any("shot_risk_audit.py" in c for c in na["action_card"]["commands"])
    assert any("spectacle_probe_pack.py" in c for c in na["action_card"]["commands"])


def test_gather_probes_video_prompt_writes_spectacle_motion_plan(monkeypatch):
    root = make_work(ALL_DONE_TO["video_prompt"])
    _write_clean_image_qc(root)
    scripts = []

    def fake_run(cmd):
        scripts.append(os.path.basename(cmd[1]))
        return _CP(0, '{"findings_path": ""}', "")

    monkeypatch.setattr(run, "_run", fake_run)
    probes = run.gather_probes(root, _route("video_prompt"), "video_prompt")

    assert not probes.prework_block
    assert "router.py" in scripts
    assert "spectacle_plan.py" in scripts


def test_gather_probes_compose_writes_action_edit_cues(monkeypatch):
    root = make_work(ALL_DONE_TO["compose"])
    _write_clean_image_qc(root)
    scripts = []

    def fake_run(cmd):
        scripts.append(os.path.basename(cmd[1]))
        return _CP(0, '{"findings_path": ""}', "")

    monkeypatch.setattr(run, "_run", fake_run)
    probes = run.gather_probes(root, _route("compose"), "compose")

    assert not probes.prework_block
    assert "action_edit_cues.py" in scripts


# ── --auto 不越过花钱点（loop 逻辑，注入探针避免 subprocess）───────────────────
def test_auto_does_not_cross_payment_point(monkeypatch):
    root = make_work(ALL_DONE_TO["image"])
    monkeypatch.setattr(run, "gather_probes", lambda *a, **k: run.Probes())
    na = run.next_action(root, "第1集", auto=True)
    assert na["stop_reason"] == "needs_payment_confirm"  # 没有因 --auto 而跑过出图


def test_next_action_image_prompt_uses_prompt_preflight_gate(monkeypatch):
    root = make_work(ALL_DONE_TO["image_prompt"])
    gate_stages = []

    def fake_run(cmd):
        if cmd[1].endswith("dashboard.py"):
            gate_stages.append(cmd[cmd.index("--stage") + 1])
            return _CP(0, '{"findings_path": ""}', "")
        return _CP(0, "", "")

    monkeypatch.setattr(run, "_run", fake_run)
    na = run.next_action(root, "第1集")
    assert na["stop_reason"] == "needs_agent_gen"
    assert gate_stages == ["image_prompt_preflight"]


def test_next_action_image_uses_preflight_gate_before_pngs(monkeypatch):
    root = make_work(ALL_DONE_TO["image"])
    gate_stages = []

    def fake_run(cmd):
        if cmd[1].endswith("dashboard.py"):
            gate_stages.append(cmd[cmd.index("--stage") + 1])
            return _CP(0, '{"findings_path": ""}', "")
        return _CP(0, "", "")

    monkeypatch.setattr(run, "_run", fake_run)
    na = run.next_action(root, "第1集")
    assert na["stop_reason"] == "needs_payment_confirm"
    assert gate_stages == ["image_preflight"]


def test_next_action_image_uses_image_gate_after_pngs(monkeypatch):
    root = make_work(ALL_DONE_TO["image"])
    png = os.path.join(root, "出图", "第1集", "图片", "Clip_01.png")
    os.makedirs(os.path.dirname(png), exist_ok=True)
    with open(png, "wb") as fh:
        fh.write(b"png")
    gate_stages = []

    def fake_run(cmd):
        if cmd[1].endswith("dashboard.py"):
            gate_stages.append(cmd[cmd.index("--stage") + 1])
            return _CP(0, '{"findings_path": ""}', "")
        return _CP(0, "", "")

    monkeypatch.setattr(run, "_run", fake_run)
    na = run.next_action(root, "第1集")
    assert na["stop_reason"] == "needs_payment_confirm"
    assert gate_stages == ["image"]


def test_next_action_video_prompt_uses_prompt_preflight_gate(monkeypatch):
    root = make_work(ALL_DONE_TO["video_prompt"])
    _write_clean_image_qc(root)
    gate_stages = []

    def fake_run(cmd):
        if cmd[1].endswith("dashboard.py"):
            gate_stages.append(cmd[cmd.index("--stage") + 1])
            return _CP(0, '{"findings_path": ""}', "")
        return _CP(0, "", "")

    monkeypatch.setattr(run, "_run", fake_run)
    na = run.next_action(root, "第1集")
    assert na["stop_reason"] == "needs_agent_gen"
    assert gate_stages == ["video_prompt_preflight"]


def test_model_router_failure_is_prework_block(monkeypatch):
    root = make_work(ALL_DONE_TO["video_prompt"])
    _write_clean_image_qc(root)

    def fake_run(cmd):
        if cmd[1].endswith("router.py"):
            return _CP(2, "", "router failed")
        return _CP(0, '{"findings_path": ""}', "")

    monkeypatch.setattr(run, "_run", fake_run)
    probes = run.gather_probes(root, _route("video_prompt"), "video_prompt")
    assert probes.prework_block and "model_router" in probes.prework_block
    na = run.decide(root, _route("video_prompt"), "video_prompt", probes)
    assert na["stop_reason"] == "prework_failed"


def test_image_prompt_allows_identity_planned_reference_gaps(monkeypatch):
    root = make_work(ALL_DONE_TO["image_prompt"])

    def fake_run(cmd):
        if cmd[1].endswith("identity.py"):
            prod = os.path.join(root, "生产数据")
            os.makedirs(prod, exist_ok=True)
            with open(os.path.join(prod, "identity_adapter_matrix.json"), "w", encoding="utf-8") as fh:
                json.dump({
                    "kind": "n2d_identity_adapter_matrix",
                    "forms": [{
                        "character_id": "CHAR_A",
                        "form": "常态",
                        "gaps": [
                            "image.codex:reference_group_assets_missing",
                            "video.dreamina:reference_group_assets_missing",
                            "missing_reference:front",
                        ],
                    }],
                }, fh)
            return _CP(1, "wrote identity matrix", "")
        if cmd[1].endswith("dashboard.py"):
            return _CP(0, '{"findings_path": ""}', "")
        return _CP(0, "", "")

    monkeypatch.setattr(run, "_run", fake_run)
    probes = run.gather_probes(root, _route("image_prompt"), "image_prompt")
    assert probes.prework_block is None
    identity_step = next(item for item in probes.prework if item["step"] == "identity")
    assert identity_step["status"] == "warn"


def test_image_identity_planned_reference_gaps_defer_to_gate(monkeypatch):
    root = make_work(ALL_DONE_TO["image"])

    def fake_run(cmd):
        if cmd[1].endswith("identity.py"):
            prod = os.path.join(root, "生产数据")
            os.makedirs(prod, exist_ok=True)
            with open(os.path.join(prod, "identity_adapter_matrix.json"), "w", encoding="utf-8") as fh:
                json.dump({
                    "kind": "n2d_identity_adapter_matrix",
                    "forms": [{
                        "character_id": "CHAR_A",
                        "form": "常态",
                        "gaps": [
                            "image.codex:reference_group_assets_missing",
                            "missing_reference:front",
                        ],
                    }],
                }, fh)
            return _CP(1, "wrote identity matrix", "")
        if cmd[1].endswith("dashboard.py"):
            return _CP(1, '{"findings_path": ""}', "")
        return _CP(0, "", "")

    monkeypatch.setattr(run, "_run", fake_run)
    probes = run.gather_probes(root, _route("image"), "image")
    assert probes.prework_block is None
    identity_step = next(item for item in probes.prework if item["step"] == "identity")
    assert identity_step["status"] == "warn"
    na = run.decide(root, _route("image"), "image", probes)
    assert na["stop_reason"] == "blocked_by_gate"


def test_gate_exception_is_fail_closed(monkeypatch):
    root = make_work(ALL_DONE_TO["image"])

    def fake_run(cmd):
        if cmd[1].endswith("dashboard.py"):
            raise RuntimeError("gate crashed")
        return _CP(0, "", "")

    monkeypatch.setattr(run, "_run", fake_run)
    probes = run.gather_probes(root, _route("image"), "image")
    assert probes.gate and probes.gate["blocked"] is True
    na = run.decide(root, _route("image"), "image", probes)
    assert na["stop_reason"] == "blocked_by_gate"


def test_missing_dashboard_script_is_fail_closed(monkeypatch):
    # 缺 dashboard.py（损坏安装）≠ 可优雅降级依赖；受闸阶段绝不静默放行。
    root = make_work(ALL_DONE_TO["image"])
    real_exists = os.path.exists
    monkeypatch.setattr(run.os.path, "exists",
                        lambda p: False if str(p).endswith("dashboard.py") else real_exists(p))
    monkeypatch.setattr(run, "_run", lambda cmd: _CP(0, "", ""))
    probes = run.gather_probes(root, _route("image"), "image")
    assert probes.gate and probes.gate["blocked"] is True
    assert any(s["step"] == "gate" and s["status"] == "block" for s in probes.prework)


def test_missing_compliance_script_is_fail_closed(monkeypatch):
    # 合规是不可协商前置；compliance.py 缺失 → compliance_gap 记缺，付费档不放行。
    root = make_work(ALL_DONE_TO["image"])
    real_exists = os.path.exists
    monkeypatch.setattr(run.os.path, "exists",
                        lambda p: False if str(p).endswith("compliance.py") else real_exists(p))
    monkeypatch.setattr(run, "_run", lambda cmd: _CP(0, '{"findings_path": ""}', ""))
    probes = run.gather_probes(root, _route("image"), "image")
    assert probes.compliance_gap is True


def test_decide_is_pure_no_mutation():
    root = make_work(ALL_DONE_TO["image"])
    p = run.Probes()
    before = (p.env_missing, p.compliance_gap, list(p.pending_choices), list(p.prework))
    run.decide(root, _route("image"), "image", p)
    after = (p.env_missing, p.compliance_gap, list(p.pending_choices), list(p.prework))
    assert before == after


def test_image_qc_gate_issue_blocks_missing_report():
    root = make_work(ALL_DONE_TO["image"])
    issue = run._image_qc_gate_issue(root, "第1集")
    assert issue and "缺 image_qc 报告" in issue


def test_image_qc_gate_issue_blocks_non_full_precision():
    root = make_work(ALL_DONE_TO["image"])
    out_dir = os.path.join(root, "生产数据", "image_qc", "第1集")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "image_qc_第1集.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"qc_environment": {"precision_level": "none"}, "summary": {"hard_blocks": 0},
                   "inputs_fingerprint": _fresh_fp(root)}, fh)

    issue = run._image_qc_gate_issue(root, "第1集")
    assert issue and "精度为 none" in issue


def test_image_qc_gate_issue_passes_full_clean_report():
    root = make_work(ALL_DONE_TO["image"])
    out_dir = os.path.join(root, "生产数据", "image_qc", "第1集")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "image_qc_第1集.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"qc_environment": {"precision_level": "full"}, "summary": {"hard_blocks": 0, "verdict": "ok"},
                   "inputs_fingerprint": _fresh_fp(root)}, fh)

    assert run._image_qc_gate_issue(root, "第1集") is None


def test_image_qc_gate_issue_blocks_report_without_fingerprint():
    # 无 inputs_fingerprint 的旧报告不能证明对应当前像素 → fail-closed（镜像 dashboard 口径）。
    root = make_work(ALL_DONE_TO["image"])
    out_dir = os.path.join(root, "生产数据", "image_qc", "第1集")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "image_qc_第1集.json"), "w", encoding="utf-8") as fh:
        json.dump({"qc_environment": {"precision_level": "full"}, "summary": {"hard_blocks": 0, "verdict": "ok"}}, fh)
    issue = run._image_qc_gate_issue(root, "第1集")
    assert issue and "新鲜度=unknown" in issue


def test_image_qc_gate_issue_blocks_stale_report():
    # QC 后产物又变（指纹失配）→ 旧绿不算数。
    root = make_work(ALL_DONE_TO["image"])
    out_dir = os.path.join(root, "生产数据", "image_qc", "第1集")
    os.makedirs(out_dir, exist_ok=True)
    tracked = "出图/第1集/图片/01.png"
    abs_png = os.path.join(root, tracked)
    os.makedirs(os.path.dirname(abs_png), exist_ok=True)
    with open(abs_png, "wb") as fh:
        fh.write(b"PNG-A")
    fp = _fresh_fp(root, [tracked])
    with open(os.path.join(out_dir, "image_qc_第1集.json"), "w", encoding="utf-8") as fh:
        json.dump({"qc_environment": {"precision_level": "full"}, "summary": {"hard_blocks": 0, "verdict": "ok"},
                   "inputs_fingerprint": fp}, fh)
    # Redraw the PNG → fingerprint no longer matches.
    with open(abs_png, "wb") as fh:
        fh.write(b"PNG-B-REDRAWN")
    issue = run._image_qc_gate_issue(root, "第1集")
    assert issue and "新鲜度=stale" in issue


def test_enter_action_includes_entry_checks(monkeypatch):
    root = make_work(ALL_DONE_TO["image"])
    monkeypatch.setattr(run, "entry_checks", lambda root, ep=None, stage_key=None, preview=False: [{"step": "source_check", "status": "clean"}])
    monkeypatch.setattr(run, "gather_probes", lambda *a, **k: run.Probes())
    na = run.enter_action(root, "第1集")
    assert na["entry_checks"][0]["step"] == "source_check"
    assert na["stop_reason"] == "needs_payment_confirm"


# ── prework 并行化（P0-2）：_run_report_only_prework 顺序保持 + skip 行为不变 ──────
def _write_script(d, name, exit_code):
    path = os.path.join(d, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"import sys\nprint('ran {name}')\nsys.exit({exit_code})\n")
    return path


def test_report_only_prework_preserves_order_and_skip():
    d = tempfile.mkdtemp()
    ok = _write_script(d, "ok.py", 0)
    warn = _write_script(d, "warn.py", 1)
    missing = os.path.join(d, "does_not_exist.py")
    commands = [
        ("step_ok", ok, []),
        ("step_missing", missing, []),
        ("step_warn", warn, []),
    ]
    p = run.Probes()
    run._run_report_only_prework(p, commands)
    # 顺序与 commands 一致（并行执行但按声明序回填）
    assert [e["step"] for e in p.prework] == ["step_ok", "step_missing", "step_warn"]
    by_step = {e["step"]: e for e in p.prework}
    assert by_step["step_ok"]["status"] == "pass"
    assert by_step["step_missing"]["status"] == "skip"
    assert by_step["step_warn"]["status"] == "warn"
    # report-only：从不阻断
    assert p.prework_block is None


def test_report_only_prework_runs_serially_without_cache_module(monkeypatch):
    # 缓存模块不可用时 _prework_run 退化为顺序串行，结果仍正确
    monkeypatch.setattr(run, "_run_cached_parallel", None)
    d = tempfile.mkdtemp()
    ok = _write_script(d, "ok.py", 0)
    p = run.Probes()
    run._run_report_only_prework(p, [("only", ok, [])])
    assert p.prework[0]["status"] == "pass"


def test_report_only_cache_rebuilds_deleted_output_path_sidecar(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    script = tmp_path / "writer.py"
    script.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "root = Path(sys.argv[1])\n"
        "count = root / 'count.txt'\n"
        "n = int(count.read_text() or '0') + 1 if count.exists() else 1\n"
        "count.write_text(str(n))\n"
        "out = root / '生产数据' / 'identity_eval_pack.json'\n"
        "out.parent.mkdir(parents=True, exist_ok=True)\n"
        "out.write_text('{}')\n"
        "print(json.dumps({'output_path': str(out)}))\n",
        encoding="utf-8",
    )
    cache = run._PreworkCache(str(root), "第1集", "cache-rebuild", "fp")
    p1 = run.Probes()
    run._run_report_only_prework(
        p1,
        [("identity_eval_pack", str(script), [str(root)])],
        cache=cache,
    )
    cache.save()
    sidecar = root / "生产数据" / "identity_eval_pack.json"
    assert sidecar.exists() and (root / "count.txt").read_text() == "1"

    sidecar.unlink()
    cache2 = run._PreworkCache(str(root), "第1集", "cache-rebuild", "fp")
    p2 = run.Probes()
    run._run_report_only_prework(
        p2,
        [("identity_eval_pack", str(script), [str(root)])],
        cache=cache2,
    )

    assert sidecar.exists()
    assert (root / "count.txt").read_text() == "2"


def test_report_only_warn_result_is_never_cached_even_with_artifact(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    artifact = root / "warn.json"
    script = tmp_path / "warn_writer.py"
    script.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "p = Path(sys.argv[1]) / 'warn.json'\n"
        "p.write_text('{}')\n"
        "print(json.dumps({'output_path': str(p)}))\n"
        "raise SystemExit(2)\n",
        encoding="utf-8",
    )
    cache = run._PreworkCache(str(root), "第1集", "warn-not-cached", "fp")
    p = run.Probes()
    run._run_report_only_prework(p, [("warn", str(script), [str(root)])], cache=cache)
    cache.save()

    assert artifact.exists()
    assert run._PreworkCache(str(root), "第1集", "warn-not-cached", "fp").get("warn") is None


def test_report_only_exit_zero_with_structured_warn_is_not_cached(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    script = tmp_path / "structured_warn.py"
    script.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "p = Path(sys.argv[1]) / 'stale-sidecar.json'\n"
        "p.write_text('{}')\n"
        "print(json.dumps({'status':'warn','output_path':str(p)}))\n",
        encoding="utf-8",
    )
    cache = run._PreworkCache(str(root), "第1集", "structured-warn", "fp")
    p = run.Probes()
    run._run_report_only_prework(p, [("warn", str(script), [str(root)])], cache=cache)
    cache.save()

    assert p.prework[0]["status"] == "warn"
    assert run._PreworkCache(str(root), "第1集", "structured-warn", "fp").get("warn") is None


def test_report_only_cache_ignores_output_paths_outside_project_root(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    inside = root / "inside.json"
    outside = tmp_path / "outside.json"
    inside.write_text("{}", encoding="utf-8")
    outside.write_text("{}", encoding="utf-8")

    found = run._cache_artifact_paths(
        str(root),
        json.dumps({"output_path": str(outside), "report_path": str(inside)}),
    )

    assert found == [str(inside.resolve())]


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
