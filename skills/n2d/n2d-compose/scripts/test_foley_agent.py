#!/usr/bin/env python3
"""foley_agent 纯函数单测。从脚本自身目录跑：
    cd skills/n2d/n2d-compose/scripts && python -m pytest test_foley_agent.py
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import foley_agent as fa  # noqa: E402


def test_extract_ambience_spans_clip():
    ev = fa.extract_sfx_events({"id": "C1", "duration": 4.0, "prompt": "大雨倾盆，雷声"}, 10.0)
    weather = [e for e in ev if e["tag"] == "weather"][0]
    assert weather["kind"] == "ambience"
    assert weather["start"] == 10.0 and weather["duration"] == 4.0 and weather["aligned"] == "span"


def test_extract_impact_estimated_midpoint():
    ev = fa.extract_sfx_events({"id": "C2", "duration": 4.0, "prompt": "拔剑出鞘"}, 0.0)
    sword = [e for e in ev if e["tag"] == "sword_whoosh"][0]
    assert sword["kind"] == "impact"
    assert sword["start"] == 2.0 and sword["aligned"] == "estimated"  # 中点估计


def test_extract_impact_explicit_action_time():
    ev = fa.extract_sfx_events({"id": "C3", "duration": 6.0, "action_at": 1.5, "prompt": "关门"}, 10.0)
    door = [e for e in ev if e["tag"] == "door"][0]
    assert door["start"] == 11.5 and door["aligned"] == "explicit"


def test_extract_no_keywords_no_events():
    assert fa.extract_sfx_events({"id": "C4", "duration": 3.0, "prompt": "她静静坐着"}, 0.0) == []


def test_extract_dedups_same_tag():
    ev = fa.extract_sfx_events({"id": "C5", "duration": 2.0, "prompt": "剑光 武器 挥舞"}, 0.0)
    assert sum(1 for e in ev if e["tag"] == "sword_whoosh") == 1


def test_build_plan_accumulates_timeline():
    clips = [
        {"id": "C1", "duration": 3.0, "prompt": "脚步声"},
        {"id": "C2", "duration": 4.0, "prompt": "拔剑"},
    ]
    plan = fa.build_foley_plan(clips)
    foot = [e for e in plan if e["tag"] == "footsteps"][0]
    sword = [e for e in plan if e["tag"] == "sword_whoosh"][0]
    assert foot["start"] == 0.0          # 第一 clip 起点
    assert sword["start"] == 3.0 + 2.0   # 第二 clip 起点(3.0) + 中点(2.0)


def test_total_duration():
    assert fa.total_duration([{"duration": 3.0}, {"duration": 2.5}, {"duration": "bad"}]) == 5.5


def test_load_backend_none_without_env(monkeypatch):
    monkeypatch.delenv("N2D_FOLEY_CMD", raising=False)
    assert fa.load_foley_backend() is None


def test_load_backend_returns_callable_with_env(monkeypatch):
    monkeypatch.setenv("N2D_FOLEY_CMD", "echo {plan} {out} {duration}")
    assert callable(fa.load_foley_backend())


def test_load_backend_requires_out_placeholder(monkeypatch):
    monkeypatch.setenv("N2D_FOLEY_CMD", "echo no placeholders")
    assert fa.load_foley_backend() is None  # 缺 {out} → 不构造（防误用）


# ── P1：打斗 SFX 踩真·命中/撞点秒（治"落 clip 中点估计、对不上画面命中"） ──
def test_impact_seconds_from_impact_frame():
    clip = {"duration": 6.0, "template_contract": {"impact_frame": "命中 1.8s 狰狞峰"}}
    assert fa.impact_seconds_from_clip(clip, 6.0) == [1.8]


def test_impact_seconds_from_collision_and_anchors():
    clip = {"duration": 8.0,
            "template_contract": {"collision_or_apex_frame": "撞点 3.2s 白闪"},
            "continuity": {"anchors": [{"use": "keyframe", "at_sec": 3.2},
                                       {"use": "keyframe", "at_sec": 6.0},
                                       {"use": "split", "at_sec": 5.0}]}}
    assert fa.impact_seconds_from_clip(clip, 8.0) == [3.2, 6.0]  # split 不算·去重


def test_impact_seconds_post_cue_needs_hit_keyword():
    # post_cue_points 含命中关键词 + 秒 → 取；纯运镜 cue 不取。
    clip = {"duration": 10.0, "template_contract": {
        "post_cue_points": ["charge at 1s", "hit_stop 命中 4.5s", "推镜 2s"]}}
    assert fa.impact_seconds_from_clip(clip, 10.0) == [4.5]


def test_impact_seconds_out_of_bounds_dropped():
    clip = {"duration": 5.0, "template_contract": {"impact_frame": "命中 9s"}}  # 超时长
    assert fa.impact_seconds_from_clip(clip, 5.0) == []


def test_extract_sfx_events_aligns_to_apex_not_midpoint():
    clip = {"id": "C1", "duration": 6.0, "prompt": "挥剑命中",
            "template_contract": {"impact_frame": "命中 1.8s"}}
    ev = [e for e in fa.extract_sfx_events(clip, 10.0) if e["kind"] == "impact"]
    assert ev and all(e["aligned"] == "apex" for e in ev)
    assert all(e["start"] == 11.8 for e in ev)  # clip_start 10 + 命中 1.8（非中点 13.0）


def test_extract_sfx_events_multi_hit_one_per_apex():
    clip = {"id": "C1", "duration": 10.0, "prompt": "连环格挡命中",
            "continuity": {"anchors": [{"use": "keyframe", "at_sec": 2.0},
                                       {"use": "keyframe", "at_sec": 7.0}]}}
    sword = [e for e in fa.extract_sfx_events(clip, 0.0) if e["tag"] == "sword_whoosh"]
    assert sorted(e["start"] for e in sword) == [2.0, 7.0]  # 每个命中各一击
    assert all(e["aligned"] == "apex" for e in sword)


# ── 2026-06-30：原生音画后端去双层 foley_render_policy ──
def test_policy_suppress_when_native_av_backend_audio_preserved():
    # 原生音画后端 + clip 音轨保留 → 抑制 compose foley（避免双层打击声）
    p = fa.foley_render_policy(clip_audio_preserved=True, backend_native_av=True)
    assert p["mode"] == "suppress" and "backend_native_av" in p["reason"]


def test_policy_full_when_clip_audio_discarded():
    # clip 原生音轨被丢弃 → compose foley 是唯一 SFX 源，必须 full（即便后端原生音画）
    p = fa.foley_render_policy(clip_audio_preserved=False, backend_native_av=True)
    assert p["mode"] == "full" and "discarded" in p["reason"]


def test_policy_full_for_silent_backend():
    # 普通静默后端（即梦等）+ 保留 → full（维持现状，compose 提供 SFX）
    p = fa.foley_render_policy(clip_audio_preserved=True, backend_native_av=False)
    assert p["mode"] == "full" and "silent_backend" in p["reason"]


def test_policy_force_overrides_suppression():
    # FORCE_COMPOSE_FOLEY=1 → 永远 full（原生 foley 不满意时人工补）
    p = fa.foley_render_policy(clip_audio_preserved=True, backend_native_av=True, force_compose_foley=True)
    assert p["mode"] == "full" and "forced" in p["reason"]


def test_policy_strategy_force_overrides_suppression():
    p = fa.foley_render_policy(
        clip_audio_preserved=True,
        backend_native_av=True,
        foley_strategy="强制叠加",
    )
    assert p["mode"] == "full" and "forced" in p["reason"]


def test_policy_strategy_disabled_suppresses():
    p = fa.foley_render_policy(
        clip_audio_preserved=False,
        backend_native_av=False,
        foley_strategy="关闭",
    )
    assert p["mode"] == "suppress" and "disabled" in p["reason"]


def test_policy_unknown_backend_falls_back_to_intent():
    # 后端能力未知 → 回退用制作模式意图：原生音画意图 + 保留 → suppress；否则 full
    p_intent = fa.foley_render_policy(clip_audio_preserved=True, backend_native_av=None,
                                      native_av_mode_intended=True)
    assert p_intent["mode"] == "suppress" and "native_av_mode_intended" in p_intent["reason"]
    p_none = fa.foley_render_policy(clip_audio_preserved=True, backend_native_av=None,
                                    native_av_mode_intended=False)
    assert p_none["mode"] == "full"


def test_policy_default_standalone_is_full(monkeypatch, tmp_path):
    # 无 env 信号、无 _设置.md（默认丢弃·非原生音画）→ 向后兼容 full（不误抑制现有产线）
    for k in ("FORCE_COMPOSE_FOLEY", "N2D_FOLEY_CLIP_AUDIO_PRESERVED", "N2D_FOLEY_NATIVE_AV_INTENDED"):
        monkeypatch.delenv(k, raising=False)
    assert fa._resolve_foley_policy(str(tmp_path))["mode"] == "full"


def test_resolve_policy_env_preserved_with_intent_suppresses(monkeypatch, tmp_path):
    # compose.sh 传入的 env 信号优先：保留 + 原生音画意图（后端能力未知）→ suppress
    monkeypatch.delenv("FORCE_COMPOSE_FOLEY", raising=False)
    monkeypatch.setenv("N2D_FOLEY_CLIP_AUDIO_PRESERVED", "1")
    monkeypatch.setenv("N2D_FOLEY_NATIVE_AV_INTENDED", "1")
    assert fa._resolve_foley_policy(str(tmp_path))["mode"] == "suppress"


def test_resolve_backend_native_av_reads_episode_routes(tmp_path):
    routes_dir = tmp_path / "出视频" / "第1集" / "prompt"
    routes_dir.mkdir(parents=True)
    (routes_dir / "video_model_routes.json").write_text(
        '{"routes":[{"clip_id":"Clip_01","primary_backend":"Veo 3.1","native_audio_policy":"native_speech","mode":"native_av"}]}',
        encoding="utf-8",
    )
    assert fa._resolve_backend_native_av(str(tmp_path), "第1集") is True


def test_write_foley_evidence_creates_production_sidecar(tmp_path):
    root = str(tmp_path)
    plan_path = os.path.join(root, "合成", "第1集", "_work", "foley_plan.json")
    out_wav = os.path.join(root, "合成", "第1集", "_work", "foley_mix.wav")
    payload = fa.build_foley_evidence(
        root,
        "第1集",
        [{"tag": "footsteps", "start": 0.0}],
        plan_path,
        out_wav,
        3.0,
        {"mode": "full", "reason": "silent_backend"},
        render_status="silent_placeholder",
        backend_configured=False,
        backend_used=False,
    )

    rel = fa.write_foley_evidence(root, "第1集", payload)

    assert rel == os.path.join("生产数据", "foley_第1集.json")
    data = json.loads((tmp_path / rel).read_text(encoding="utf-8"))
    assert data["kind"] == "n2d_foley_evidence"
    assert data["status"] == "silent_placeholder"
