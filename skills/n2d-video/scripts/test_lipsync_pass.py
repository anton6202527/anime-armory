"""lipsync_pass 纯规划逻辑单测（无重型依赖）。
cd skills/n2d-video/scripts && python -m pytest test_lipsync_pass.py
"""
import lipsync_pass as lp


# ---------- 设置 → 档 ----------

def test_lipsync_mode():
    assert lp.lipsync_mode("关闭") == "off"
    assert lp.lipsync_mode("") == "off"
    assert lp.lipsync_mode("off") == "off"
    assert lp.lipsync_mode("后期pass") == "post_pass"
    assert lp.lipsync_mode("后期 pass（MuseTalk）") == "post_pass"
    assert lp.lipsync_mode("配音对齐") == "voice_conditioned"


# ---------- 说话镜识别（多路兜底） ----------

def test_is_speech_route_multiple_signals():
    assert lp.is_speech_route({"mode": "voice_conditioned_lipsync"})
    assert lp.is_speech_route({"native_audio_policy": "native_speech"})
    assert lp.is_speech_route({"native_audio_policy": "lipsync_condition_only"})
    assert lp.is_speech_route({"shot_type": "dialogue_shot_reverse"})
    assert lp.is_speech_route({"shot_type": "reveal_reaction_chain"})
    assert lp.is_speech_route({"shot_type": "public_confrontation"})
    assert lp.is_speech_route({"shot_type": "relationship_turn"})
    assert lp.is_speech_route({"mouth_visible": True})
    assert not lp.is_speech_route({"shot_type": "empty_establishing"})
    assert not lp.is_speech_route({"mode": "image2video", "native_audio_policy": "none"})


# ---------- 是否需要后期 pass ----------

def test_needs_post_pass_off_never():
    assert not lp.needs_post_pass({"shot_type": "dialogue"}, "关闭")


def test_needs_post_pass_force_all_speech_on_post_pass():
    assert lp.needs_post_pass({"shot_type": "dialogue", "mode": "image2video"}, "后期pass")
    # voice_conditioned 的说话镜在 post_pass 档也强制本地后期
    assert lp.needs_post_pass({"shot_type": "dialogue", "mode": "voice_conditioned_lipsync"}, "后期pass")
    # 非说话镜不碰
    assert not lp.needs_post_pass({"shot_type": "empty_establishing"}, "后期pass")


def test_needs_post_pass_voice_conditioned_only_degrades_unhandled():
    # 已被后端音频参考口型处理 → 不重复后期
    assert not lp.needs_post_pass({"shot_type": "dialogue", "mode": "voice_conditioned_lipsync"}, "配音对齐")
    # 说话镜但没走 voice_conditioned（后端不支持）→ degrade 到后期
    assert lp.needs_post_pass({"shot_type": "dialogue", "mode": "image2video"}, "配音对齐")


def test_select_post_pass_clips():
    routes = [
        {"clip_id": "Clip_01", "shot_type": "dialogue", "mode": "image2video"},
        {"clip_id": "Clip_02", "shot_type": "empty_establishing", "mode": "text2video"},
        {"clip_id": "Clip_03", "shot_type": "dialogue", "mode": "voice_conditioned_lipsync"},
    ]
    # 配音对齐：只 Clip_01 degrade
    got = lp.select_post_pass_clips(routes, "配音对齐")
    assert [c["clip_id"] for c in got] == ["Clip_01"]
    assert got[0]["reason"] == "degrade_from_voice_conditioned"
    # 后期pass：所有说话镜（Clip_01 + Clip_03）
    got2 = lp.select_post_pass_clips(routes, "后期pass")
    assert [c["clip_id"] for c in got2] == ["Clip_01", "Clip_03"]
    assert all(c["reason"] == "forced_post_pass" for c in got2)
    # 关闭：空
    assert lp.select_post_pass_clips(routes, "关闭") == []


def test_select_skips_clip_without_id():
    routes = [{"shot_type": "dialogue", "mode": "image2video"}]
    assert lp.select_post_pass_clips(routes, "后期pass") == []


# ---------- 工具探针 / 选择 ----------

def test_probe_tools_env_over_path():
    environ = {"MUSETALK_CLI": "/opt/musetalk/run"}
    which = lambda name: "/usr/bin/" + name if name == "wav2lip" else None
    got = lp.probe_tools(environ, which)
    assert got["musetalk"] == "/opt/musetalk/run"   # env 优先
    assert got["wav2lip"] == "/usr/bin/wav2lip"      # PATH 兜底
    assert got["latentsync"] is None


def test_pick_tool_preference_order():
    assert lp.pick_tool({"latentsync": "/x", "musetalk": "/y"}) == "latentsync"
    assert lp.pick_tool({"latentsync": None, "musetalk": "/y", "wav2lip": "/z"}) == "musetalk"
    assert lp.pick_tool({"latentsync": None, "musetalk": None, "wav2lip": None}) is None


# ---------- 作业条目 ----------

def test_build_job_ready_vs_needs_input():
    clip = {"clip_id": "Clip_01", "shot_type": "dialogue", "reason": "forced_post_pass"}
    ready = lp.build_job(clip, "/v/Clip_01.mp4", ["/a/line_01.wav"], "/o/Clip_01_lipsync.mp4", "musetalk")
    assert ready["status"] == "ready"
    assert ready["audio"] == ["/a/line_01.wav"]
    no_audio = lp.build_job(clip, "/v/Clip_01.mp4", [], "/o/x.mp4", "musetalk")
    assert no_audio["status"] == "needs_input"
    no_tool = lp.build_job(clip, "/v/Clip_01.mp4", ["/a/line_01.wav"], "/o/x.mp4", None)
    assert no_tool["status"] == "needs_input"
