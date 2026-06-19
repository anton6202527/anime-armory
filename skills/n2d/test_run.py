#!/usr/bin/env python3
"""n2d 编排器 run.py 测试。

从本目录跑：
    cd skills/n2d && python3 -m pytest test_run.py
"""
import os
import json
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
import run  # noqa: E402

HEADER = ("| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 "
          "| 字幕中 | 字幕英 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 |")
SEP = "|" + "---|" * 16


def make_work(cells, settings=None):
    """造一个临时作品根，cells = 第1集 的 14 个物料列（raw 起到 成片）。"""
    d = tempfile.mkdtemp()
    row = "| 第1集 | 1000 | " + " | ".join(cells) + " |"
    open(os.path.join(d, "_进度.md"), "w", encoding="utf-8").write(
        "# 进度\n\n" + HEADER + "\n" + SEP + "\n" + row + "\n")
    if settings:
        open(os.path.join(d, "_设置.md"), "w", encoding="utf-8").write(settings)
    return d


# 14 个物料列：raw 剧本改编 bgm 封面 配音 分镜设计 素材清单 字幕中 字幕英 出图prompt 出图 视频prompt 视频 成片
ALL_DONE_TO = {
    "script_stage1": ["✅", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜"],
    "voice":         ["✅", "✅", "✅", "✅", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜"],
    "image":         ["✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "0/10", "⬜", "⬜", "⬜"],
    "compose":       ["✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅", "⬜"],
}


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
    cells = ["✅"] * 14
    root = make_work(cells)
    assert run.resolve_frontier(root) is None


def test_production_mode_menu_defaults_to_shortest_path():
    root = make_work(ALL_DONE_TO["script_stage1"])
    menu = run._menu(root, "制作模式")
    assert menu["options"][:3] == ["原生音画", "配音先行", "先出视频后配音"]
    assert menu["default_preselect"] == "原生音画"


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


def test_decide_compliance_blocks_paid_stage():
    root = make_work(ALL_DONE_TO["image"])
    na = run.decide(root, _route("image"), "image", run.Probes(compliance_gap=True))
    assert na["stop_reason"] == "needs_compliance"


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


def test_decide_first_run_choice_package():
    root = make_work(ALL_DONE_TO["script_stage1"])
    p = run.Probes(pending_choices=["制作模式", "生视频模型"])
    na = run.decide(root, _route("script_stage1"), "script_stage1", p)
    assert na["stop_reason"] == "needs_choice"
    cps = [m["choice_point"] for m in na["action_card"]["menu"]]
    assert "制作模式" in cps and "生视频模型" in cps


# ── --auto 不越过花钱点（loop 逻辑，注入探针避免 subprocess）───────────────────
def test_auto_does_not_cross_payment_point(monkeypatch):
    root = make_work(ALL_DONE_TO["image"])
    monkeypatch.setattr(run, "gather_probes", lambda *a, **k: run.Probes())
    na = run.next_action(root, "第1集", auto=True)
    assert na["stop_reason"] == "needs_payment_confirm"  # 没有因 --auto 而跑过出图


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
