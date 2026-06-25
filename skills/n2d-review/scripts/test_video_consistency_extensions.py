import json
from pathlib import Path

import camera_trajectory_consistency as cam
import causal_event_consistency as causal
import dialogue_av_consistency as dav
import motion_quality_consistency as mot
import subject_video_consistency as s2v
import video_eval_runner as runner
import video_semantic_consistency as vsem
import video_vlm_consistency as vvlm


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_video_vlm_failed_judgement_is_advisory_not_autoreject(tmp_path: Path) -> None:
    # G-V4：VLM 自报失配（哪怕高置信）只作 advisory warn——单独不可 auto-reject；终判走确定性层/交付 gate。
    ep = "第1集"
    _write_json(
        tmp_path / "生产数据" / f"video_vlm_consistency_{ep}.json",
        {"judgements": [{"clip": "Clip_03", "question": "主角是否仍拿着玉簪", "match": False, "confidence": 0.86}]},
    )
    res = vvlm.analyze(str(tmp_path), ep)
    assert res["available"] is True
    row = next(r for r in res["findings"] if r.get("affected_shots") == ["Clip_03"])
    assert row["verdict"] == "warn"            # block 被钉死为 advisory
    assert row["vlm_raw_verdict"] == "block"   # 原判定保留供溯源/gate 升级
    assert not any(r["verdict"] == "block" for r in res["findings"])


def test_video_vlm_triage_severity_caps_block() -> None:
    assert vvlm.triage_severity("block") == "warn"
    assert vvlm.triage_severity("warn") == "warn"
    assert vvlm.triage_severity("info") == "info"


def test_video_vlm_schema_warns_missing_judge_metadata(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(
        tmp_path / "生产数据" / f"video_vlm_consistency_{ep}.json",
        {"checks": [{"clip": "Clip_01", "verdict": "pass", "self_consistency_votes": ["pass", "fail", "pass"]}]},
    )
    res = vvlm.analyze(str(tmp_path), ep)
    messages = "\n".join(row["message"] for row in res["findings"])
    assert "judge_model" in messages
    assert "question_chain" in messages


def test_video_semantic_report_bands_subject_similarity(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(
        tmp_path / "生产数据" / f"video_semantic_consistency_{ep}.json",
        {"segments": [{"clip": "Clip_02", "subject_similarity": 0.41, "background_similarity": 0.50}]},
    )
    res = vsem.analyze(str(tmp_path), ep)
    assert any(row["verdict"] == "block" and row["subject_similarity"] == 0.41 for row in res["findings"])


def test_video_semantic_missing_sidecar_marks_required_evidence(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(tmp_path / "脚本" / ep / "storyboard.json", {"clips": [{"id": "Clip_01", "action": "沈念入殿"}]})
    video = tmp_path / "出视频" / ep / "视频" / "Clip_01.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"")
    res = vsem.analyze(str(tmp_path), ep)
    assert res["available"] is True
    row = res["findings"][0]
    assert row["evidence_missing"] is True
    assert row["required_evidence"] == "video_semantic_consistency"


def test_dialogue_av_requires_report_for_native_multi_speaker_final(tmp_path: Path) -> None:
    ep = "第1集"
    voice = tmp_path / "脚本" / ep / "voiceover.txt"
    voice.parent.mkdir(parents=True)
    voice.write_text("沈念：你来了。\n柳娘子：我一直在。\n", encoding="utf-8")
    _write_json(
        tmp_path / "生产数据" / "video_model_routes.json",
        {"routes": [{"clip_id": "Clip_01", "primary_backend": "NativeAV", "native_audio": True}]},
    )
    video = tmp_path / "合成" / ep / "成片.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"")
    res = dav.analyze(str(tmp_path), ep)
    assert res["available"] is True
    assert "dialogue_av_alignment" in res["findings"][0]["message"]


def test_dialogue_av_blocks_turn_taking_and_hallucinated_speaker(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(
        tmp_path / "生产数据" / f"dialogue_av_alignment_{ep}.json",
        {"turns": [{"turn_id": "Clip_01", "turn_taking_ok": False, "hallucinated_speaker": "旁白幽灵"}]},
    )
    res = dav.analyze(str(tmp_path), ep)
    assert any(row["verdict"] == "block" and "turn-taking" in row["message"] for row in res["findings"])
    assert any("幻觉说话人" in row["message"] for row in res["findings"])


def test_causal_event_warns_missing_graph_when_risky_video_exists(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(
        tmp_path / "脚本" / ep / "storyboard.json",
        {"clips": [{"id": "Clip_01", "action": "沈念击中烛台，烛台摔碎后火焰熄灭"}]},
    )
    video = tmp_path / "出视频" / ep / "视频" / "Clip_01.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"")
    res = causal.analyze(str(tmp_path), ep)
    assert res["available"] is True
    assert any("causal_event_graph" in row["message"] for row in res["findings"])


def test_causal_event_rule_library_blocks_failed_physics(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(
        tmp_path / "生产数据" / f"causal_event_graph_{ep}.json",
        {"events": [{
            "id": "e1",
            "clip": "Clip_02",
            "cause": "沈念击中铜镜",
            "effect": "铜镜碎裂",
            "evidence_frames": ["Clip_02_0004.png"],
            "physical_rule": "collision",
            "physics_pass": False,
        }]},
    )
    res = causal.analyze(str(tmp_path), ep)
    assert any(row["verdict"] == "block" and "违反物理规则" in row["message"] for row in res["findings"])


def test_camera_trajectory_report_blocks_axis_flip(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(
        tmp_path / "生产数据" / f"camera_trajectory_probe_{ep}.json",
        {"shots": [{"clip": "Clip_04", "axis_flip": True, "trajectory_error": 0.41}]},
    )
    res = cam.analyze(str(tmp_path), ep)
    assert any(row["verdict"] == "block" and "越轴" in row["message"] for row in res["findings"])


def test_camera_trajectory_missing_sidecar_marks_required_evidence(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(tmp_path / "脚本" / ep / "storyboard.json", {"clips": [{"id": "Clip_01", "camera": "推镜跟拍"}]})
    video = tmp_path / "出视频" / ep / "视频" / "Clip_01.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"")
    res = cam.analyze(str(tmp_path), ep)
    row = res["findings"][0]
    assert row["evidence_missing"] is True
    assert row["required_evidence"] == "camera_trajectory_probe"


def test_motion_quality_high_action_requires_posterior_curves(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(
        tmp_path / "生产数据" / f"motion_quality_{ep}.json",
        {"shots": [{"clip": "Clip_01", "shot_type": "fight_exchange", "expected_motion": "打斗命中"}]},
    )
    res = mot.analyze(str(tmp_path), ep)
    assert any("高动作后验报告缺字段" in row["message"] and "speed_curve" in row["message"] for row in res["findings"])


def test_motion_quality_missing_sidecar_marks_required_evidence(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(tmp_path / "脚本" / ep / "storyboard.json", {"clips": [{"id": "Clip_01", "action": "沈念挥剑命中"}]})
    video = tmp_path / "出视频" / ep / "视频" / "Clip_01.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"")
    res = mot.analyze(str(tmp_path), ep)
    row = res["findings"][0]
    assert row["evidence_missing"] is True
    assert row["required_evidence"] == "motion_quality"


def test_motion_quality_high_action_posterior_curves_pass(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(
        tmp_path / "生产数据" / f"motion_quality_{ep}.json",
        {"shots": [{
            "clip": "Clip_01",
            "shot_type": "fight_exchange",
            "expected_motion": "打斗命中",
            "speed_curve": "起手0.2→命中0.8→收势0.3",
            "spatial_path": "画左到画右半步",
            "impact_frame": "00:00:02.100",
            "motion_smoothness": 0.9,
            "dynamic_degree": 0.4,
            "freeze_ratio": 0.02,
            "jerk_score": 0.1,
            "action_completion": 0.9,
        }]},
    )
    res = mot.analyze(str(tmp_path), ep)
    assert not any("高动作后验报告缺字段" in row["message"] for row in res["findings"])


def test_motion_quality_report_catches_freeze_and_low_smoothness(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(
        tmp_path / "生产数据" / f"motion_quality_{ep}.json",
        {"shots": [{"clip": "Clip_05", "motion_smoothness": 0.32, "freeze_ratio": 0.50}]},
    )
    res = mot.analyze(str(tmp_path), ep)
    assert any("运动平滑度" in row["message"] for row in res["findings"])
    assert any(row["verdict"] == "block" and "冻结帧" in row["message"] for row in res["findings"])


def test_subject_video_report_blocks_multi_subject_swap(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(
        tmp_path / "生产数据" / f"subject_video_consistency_{ep}.json",
        {"subjects": [{"clip": "Clip_06", "subject": "CHAR_沈念", "multi_subject_swap": True}]},
    )
    res = s2v.analyze(str(tmp_path), ep)
    assert any(row["verdict"] == "block" and "串换" in row["message"] for row in res["findings"])


def test_subject_video_missing_sidecar_marks_required_evidence(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", {"characters": [{"id": "CHAR_A"}]})
    video = tmp_path / "出视频" / ep / "视频" / "Clip_01.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"")
    res = s2v.analyze(str(tmp_path), ep)
    row = res["findings"][0]
    assert row["evidence_missing"] is True
    assert row["required_evidence"] == "subject_video_consistency"


def test_video_eval_runner_builds_manifest_with_risk_questions(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(
        tmp_path / "脚本" / ep / "storyboard.json",
        {"clips": [{"id": "Clip_01", "action": "沈念挥剑击中铜镜，镜头跟拍推进", "dialogue": "沈念：别动"}]},
    )
    video = tmp_path / "出视频" / ep / "视频" / "Clip_01.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"")
    manifest = runner.build_manifest(str(tmp_path), ep)
    kinds = set(manifest["tasks"][0]["risk_kinds"])
    assert {"subject", "scene", "action", "physics", "dialogue", "camera"} <= kinds
    assert manifest["sidecar_targets"]["motion"].endswith(f"motion_quality_{ep}.json")
    assert manifest["sidecar_targets"]["physical_event"].endswith(f"physical_event_graph_{ep}.json")


# ── #4 动作 beat 豁免：高动态镜主体形变属预期 → subject_fidelity 硬 block 降 warn ──
def test_relax_action_fidelity_pure() -> None:
    assert s2v.relax_action_fidelity("block", True) == "warn"   # 动作镜 → 降
    assert s2v.relax_action_fidelity("block", False) == "block" # 静态镜 → 保持
    assert s2v.relax_action_fidelity("warn", True) == "warn"    # 非 block 不动


def test_is_action_row_signals() -> None:
    assert s2v._is_action_row({"high_motion": True}) is True
    assert s2v._is_action_row({"action_beat": "yes"}) is True
    assert s2v._is_action_row({"motion_intensity": 0.8}) is True
    assert s2v._is_action_row({"motion_intensity": 0.2}) is False
    assert s2v._is_action_row({"subject_fidelity": 0.4}) is False


def test_high_motion_clips_from_storyboard(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(
        tmp_path / "脚本" / ep / "storyboard.json",
        {"clips": [
            {"id": "Clip_01", "shot_description": "沈念静坐窗前喝茶"},                 # 无动作
            {"id": "Clip_06", "shot_description": "沈念挥剑劈砍，剑气命中铜镜爆裂"},   # 攻击+命中 → 动作 beat
        ]},
    )
    hm = s2v._high_motion_clips(str(tmp_path), ep)
    assert 6 in hm and 1 not in hm


def test_subject_fidelity_block_relaxed_on_action_clip(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(
        tmp_path / "脚本" / ep / "storyboard.json",
        {"clips": [
            {"id": "Clip_06", "shot_description": "沈念挥剑劈砍命中铜镜爆裂"},  # 动作 beat
            {"id": "Clip_07", "shot_description": "沈念静立"},                  # 静态
        ]},
    )
    # 两镜同样低 subject_fidelity=0.40（<0.45 硬 block 线）
    _write_json(
        tmp_path / "生产数据" / f"subject_video_consistency_{ep}.json",
        {"subjects": [
            {"clip": "Clip_06", "subject": "CHAR_沈念", "subject_fidelity": 0.40},
            {"clip": "Clip_07", "subject": "CHAR_沈念", "subject_fidelity": 0.40},
        ]},
    )
    res = s2v.analyze(str(tmp_path), ep)
    by_shot = {r.get("shot"): r for r in res["findings"] if "subject_fidelity" in r}
    assert by_shot["Clip_06"]["verdict"] == "warn"                       # 动作镜降 warn
    assert by_shot["Clip_06"].get("action_beat_relaxed") is True
    assert by_shot["Clip_07"]["verdict"] == "block"                      # 静态镜仍 block（真崩主体）
