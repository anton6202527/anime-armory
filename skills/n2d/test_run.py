#!/usr/bin/env python3
"""n2d 编排器 run.py 测试。

从本目录跑：
    cd skills/n2d && python3 -m pytest test_run.py
"""
import os
import json
import sys
import tempfile
import hashlib

sys.path.insert(0, os.path.dirname(__file__))
import run  # noqa: E402

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
    "image_prompt":  ["✅", "✅", "✅", "✅", "⬜", "✅", "✅", "✅", "✅", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜"],
    "image":         ["✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "0/10", "⬜", "⬜", "⬜", "⬜"],
    "video_prompt":  ["✅", "✅", "✅", "✅", "⬜", "✅", "✅", "✅", "✅", "✅", "✅", "⬜", "⬜", "⬜", "⬜"],
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
        json.dump({"qc_environment": {"precision_level": "full"}, "summary": {"hard_blocks": 0, "verdict": "ok"}}, fh)


def _write_boundary_review(root, raw_text, decision="accept_risk", notes="已复核，保留短集并补强 voiceover。"):
    os.makedirs(os.path.join(root, "脚本"), exist_ok=True)
    path = os.path.join(root, "脚本", "boundary_review.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({
            "kind": "n2d_boundary_review",
            "version": 1,
            "reviews": [{
                "episode": "第1集",
                "raw_rel": "脚本/第1集/raw.txt",
                "raw_sha256": hashlib.sha256(raw_text.strip().encode("utf-8")).hexdigest(),
                "risk_flags": ["弱钩待判"],
                "decision": decision,
                "notes": notes,
            }],
        }, fh, ensure_ascii=False)


# ── 前沿解析 + stage key 反查（真实 fixture 文件）──────────────────────────────
def test_resolve_frontier_image():
    root = make_work(ALL_DONE_TO["image"])
    route = run.resolve_frontier(root)
    assert route["col"] == "出图"
    assert run.stage_key_of(route) == "image"


def test_resolve_frontier_voice():
    # 默认现为「原生音画」（路由跳过 n2d-voice），显式选「配音先行」以验证 voice 前沿。
    root = make_work(ALL_DONE_TO["voice"], settings="# _设置\n- 制作模式: 配音先行\n")
    route = run.resolve_frontier(root)
    assert run.stage_key_of(route) == "voice"


def test_resolve_frontier_native_av_script_stage2_labels_timing_not_voice():
    root = make_work(ALL_DONE_TO["voice"])
    route = run.resolve_frontier(root)
    assert run.stage_key_of(route) == "script_stage2"
    assert "原生音画" in route["label"]
    assert "配音后" not in route["cmd"]
    assert "storyboard.json" in route["note"]


def test_decide_uses_mode_aware_route_command():
    root = make_work(ALL_DONE_TO["voice"])
    route = run.resolve_frontier(root)
    na = run.decide(root, route, "script_stage2", run.Probes())
    cmd = na["action_card"]["exact_command"]
    assert "原生音画脚本时长定稿" in cmd
    assert "配音后" not in cmd


def test_resolve_frontier_done():
    cells = ["✅"] * 15
    root = make_work(cells)
    assert run.resolve_frontier(root) is None


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
    assert "已完成验收" in na["action_card"]["headline"]


def test_production_mode_menu_defaults_to_shortest_path():
    root = make_work(ALL_DONE_TO["script_stage1"])
    menu = run._menu(root, "制作模式")
    assert menu["options"][:3] == ["原生音画", "配音先行", "先出视频后配音"]
    assert menu["default_preselect"] == "原生音画"


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


# ── 纯决策 decide()：stop 分类 + 优先级 ───────────────────────────────────────
def _route(stage_key, ep="第1集"):
    spec = run.stage_for_key(stage_key)
    return {"ep": ep, "col": spec["progress_columns"][0], "label": spec["label"], "skill": spec["owner"]}


def test_decide_agent_gen():
    root = make_work(ALL_DONE_TO["voice"])
    na = run.decide(root, _route("script_stage2"), "script_stage2", run.Probes())
    assert na["stop_reason"] == "needs_agent_gen"
    assert na["auto_continue"] is False


def test_decide_payment_confirm_image_carries_granularity_menu():
    root = make_work(ALL_DONE_TO["image"])
    na = run.decide(root, _route("image"), "image", run.Probes())
    assert na["stop_reason"] == "needs_payment_confirm"
    assert na["action_card"]["menu"][0]["choice_point"] == "生成粒度"


def test_decide_voice_payment_menu_is_backend():
    root = make_work(ALL_DONE_TO["voice"])
    na = run.decide(root, _route("voice"), "voice", run.Probes())
    assert na["stop_reason"] == "needs_payment_confirm"
    assert na["action_card"]["menu"][0]["choice_point"] == "配音后端"


def test_decide_compose_payment_menu_is_bgm():
    root = make_work(ALL_DONE_TO["compose"])
    na = run.decide(root, _route("compose"), "compose", run.Probes())
    assert na["stop_reason"] == "needs_payment_confirm"
    assert na["action_card"]["menu"][0]["choice_point"] == "BGM来源"
    bundle = na["action_card"]["post_qc_bundle"]
    assert bundle["scope"] == "pre_compose_review"
    assert any("review_ui.py" in cmd and "--export-findings" in cmd for cmd in bundle["commands"])


def test_decide_review_requires_signoff_after_evidence_passes():
    root = make_work(ALL_DONE_TO["review"])
    na = run.decide(root, _route("review"), "review", run.Probes())
    assert na["stop_reason"] == "needs_acceptance_signoff"
    assert "验收" in na["action_card"]["exact_command"]


def test_decide_compliance_blocks_paid_stage():
    root = make_work(ALL_DONE_TO["image"])
    na = run.decide(root, _route("image"), "image", run.Probes(compliance_gap=True))
    assert na["stop_reason"] == "needs_compliance"


def test_decide_entry_check_blocks_before_generation():
    root = make_work(ALL_DONE_TO["image"])
    p = run.Probes(entry_check_block="源文本已漂移")
    na = run.decide(root, _route("image"), "image", p)
    assert na["stop_reason"] == "blocked_by_entry_check"


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
    ep_dir = os.path.join(root, "脚本", "第1集")
    os.makedirs(ep_dir, exist_ok=True)
    raw = "她走进屋里。\n然后坐下。\n"
    open(os.path.join(ep_dir, "raw.txt"), "w", encoding="utf-8").write(raw)
    _write_boundary_review(root, raw)

    probes = run.gather_probes(root, _route("script_stage1"), "script_stage1")

    assert not probes.prework_block
    assert any(pw["step"] == "boundary_audit" and pw["status"] == "reviewed" for pw in probes.prework)


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
        json.dump({"qc_environment": {"precision_level": "none"}, "summary": {"hard_blocks": 0}}, fh)

    issue = run._image_qc_gate_issue(root, "第1集")
    assert issue and "精度为 none" in issue


def test_image_qc_gate_issue_passes_full_clean_report():
    root = make_work(ALL_DONE_TO["image"])
    out_dir = os.path.join(root, "生产数据", "image_qc", "第1集")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "image_qc_第1集.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"qc_environment": {"precision_level": "full"}, "summary": {"hard_blocks": 0, "verdict": "ok"}}, fh)

    assert run._image_qc_gate_issue(root, "第1集") is None


def test_enter_action_includes_entry_checks(monkeypatch):
    root = make_work(ALL_DONE_TO["image"])
    monkeypatch.setattr(run, "entry_checks", lambda root, ep=None: [{"step": "source_check", "status": "clean"}])
    monkeypatch.setattr(run, "gather_probes", lambda *a, **k: run.Probes())
    na = run.enter_action(root, "第1集")
    assert na["entry_checks"][0]["step"] == "source_check"
    assert na["stop_reason"] == "needs_payment_confirm"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
