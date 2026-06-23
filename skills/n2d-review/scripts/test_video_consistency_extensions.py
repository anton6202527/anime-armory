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


def test_video_vlm_report_blocks_failed_judgement(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(
        tmp_path / "生产数据" / f"video_vlm_consistency_{ep}.json",
        {"judgements": [{"clip": "Clip_03", "question": "主角是否仍拿着玉簪", "match": False, "confidence": 0.86}]},
    )
    res = vvlm.analyze(str(tmp_path), ep)
    assert res["available"] is True
    assert any(row["verdict"] == "block" and row.get("affected_shots") == ["Clip_03"] for row in res["findings"])


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


def test_motion_quality_high_action_requires_posterior_curves(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(
        tmp_path / "生产数据" / f"motion_quality_{ep}.json",
        {"shots": [{"clip": "Clip_01", "shot_type": "fight_exchange", "expected_motion": "打斗命中"}]},
    )
    res = mot.analyze(str(tmp_path), ep)
    assert any("高动作后验报告缺字段" in row["message"] and "speed_curve" in row["message"] for row in res["findings"])


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
