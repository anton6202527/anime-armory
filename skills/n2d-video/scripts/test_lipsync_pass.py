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


def test_read_setting_defaults_to_off(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n", encoding="utf-8")

    assert lp._read_setting(str(root), "第1集") == "关闭"


def test_read_setting_audio_policy_can_enable_lipsync(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text(
        "# _设置\n\n- 视频生成音频策略: 配音对齐口型\n",
        encoding="utf-8",
    )

    assert lp._read_setting(str(root), "第1集") == "配音对齐"


def test_read_setting_silent_policy_overrides_legacy_lipsync(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text(
        "# _设置\n\n- 视频生成音频策略: 无声视频流\n- 对口型: 配音对齐\n",
        encoding="utf-8",
    )

    assert lp._read_setting(str(root), "第1集") == "关闭"


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


def test_hybrid_base_video_contract_requires_post_pass_even_when_project_toggle_off():
    route = {
        "clip_id": "Clip_01",
        "shot_type": "dialogue_shot_reverse",
        "audio_strategy": "base_video_then_post_lipsync",
        "post_lipsync_required": True,
        "base_video_only": True,
    }
    assert lp.needs_post_pass(route, "关闭")
    selected = lp.select_post_pass_clips([route], "关闭")
    assert selected[0]["reason"] == "hybrid_base_video_contract"
    assert selected[0]["base_video_only"] is True


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


def test_lipsync_mode_dialogue_closeup_default():
    # 显式兼容档（对话近景）
    assert lp.lipsync_mode("对话近景") == "voice_conditioned_dialogue_closeup"
    assert lp.lipsync_mode("dialogue_closeup") == "voice_conditioned_dialogue_closeup"


def test_needs_post_pass_dialogue_closeup_default_is_scoped():
    # 对话近景兼容档：只兜对话近景说话镜，其余说话镜不进后期口型——成本有界。
    assert lp.needs_post_pass({"shot_type": "dialogue_shot_reverse", "mode": "image2video"}, "对话近景")
    assert lp.needs_post_pass({"mouth_visible": True, "mode": "image2video"}, "对话近景")
    # 已被后端口型处理 → 不重复后期
    assert not lp.needs_post_pass({"shot_type": "dialogue_shot_reverse", "mode": "voice_conditioned_lipsync"}, "对话近景")
    # 非对话近景说话镜（public_confrontation）→ 不进后期口型
    assert not lp.needs_post_pass({"shot_type": "public_confrontation", "mode": "image2video"}, "对话近景")


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


def test_output_receipt_hashes_applied_lipsync(tmp_path):
    output = tmp_path / "Clip_01_lipsync.mp4"
    output.write_bytes(b"verified-lipsync-output")

    receipt = lp._output_receipt(str(output))

    assert receipt["output_size"] == len(b"verified-lipsync-output")
    assert len(receipt["output_sha256"]) == 64
    assert receipt["completed_at"]


def test_audio_for_clip_maps_one_based_voiceover_to_zero_based_wav(tmp_path):
    voice = tmp_path / "合成" / "第1集" / "配音"
    voice.mkdir(parents=True)
    first = voice / "line_00.wav"
    first.write_bytes(b"audio")

    assert lp._audio_for_clip(str(tmp_path), "第1集", [1]) == [str(first)]
