from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("score.py")
spec = importlib.util.spec_from_file_location("n2d_score", SCRIPT)
score = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(score)


def sample_consistency() -> dict:
    return {
        "summary": {
            "by_dim": {
                "语义谱系(P0)": {"block": 0, "warn": 0, "ok": 1, "skipped": False},
                "状态百科(P1)": {"block": 0, "warn": 0, "ok": 1, "skipped": False},
                "多模态(P2)": {"block": 0, "warn": 0, "ok": 1, "skipped": False},
                "锚点门(N3)": {"block": 0, "warn": 0, "ok": 2, "skipped": False},
                "脸(G1)": {"block": 1, "warn": 0, "ok": 4, "skipped": False},
                "片内时序(N2)": {"block": 0, "warn": 1, "ok": 3, "skipped": False},
                "服装配色(N1)": {"block": 0, "warn": 1, "ok": 4, "skipped": False},
                "场景(O2)": {"block": 0, "warn": 0, "ok": 5, "skipped": False},
                "接缝接力": {"block": 0, "warn": 0, "ok": 2, "skipped": False},
                "风格(S1)": {"block": 0, "warn": 0, "ok": 5, "skipped": False},
                "糊/低质(N4)": {"block": 0, "warn": 0, "ok": 5, "skipped": False},
            }
        }
    }


def sample_visual() -> dict:
    return {
        "kind": "n2d_score_visual_checks",
        "sections": {
            "image_similarity": {
                "blocks": 0,
                "warnings": 1,
                "infos": 0,
                "skipped": False,
                "metrics": {"max_dhash_distance": 18},
                "evidence": ["Clip 2 接缝 dHash 距离 18 > 14"],
            },
            "subtitle_ocr": {
                "blocks": 1,
                "warnings": 0,
                "infos": 0,
                "skipped": False,
                "metrics": {"checked_cues": 6, "mismatches": 4},
                "evidence": ["OCR 不匹配 4/6"],
            },
            "av_duration": {
                "blocks": 0,
                "warnings": 1,
                "infos": 0,
                "skipped": False,
                "metrics": {"final_sec": 61.2, "voice_sec": 60.0},
                "evidence": ["成片 vs voice 时长差 1.20s"],
            },
            "lip_sync": {
                "blocks": 0,
                "warnings": 1,
                "infos": 0,
                "skipped": False,
                "metrics": {"mouth_visible_yes_hits": 2},
                "evidence": ["发现 2 处可见口型风险"],
            },
            "final_rhythm_density": {
                "blocks": 1,
                "warnings": 0,
                "infos": 0,
                "skipped": False,
                "metrics": {"hook_interval_sec": 35.0},
                "evidence": ["平均钩子间隔 35.0s > 30s"],
            },
        },
    }


def test_score_rollup_and_return_stage() -> None:
    mechanical = [
        {"sev": "🟡", "dim": "字幕", "loc": "cue#1", "msg": "单行过长"},
        {"sev": "🟢", "dim": "完整性", "loc": "第1集", "msg": "产物快照"},
        {"sev": "🟡", "dim": "节奏", "loc": "第1集", "msg": "集尾无 cliffhanger 标记"},
    ]
    result = score.score_episode(
        "/tmp/work",
        "第1集",
        consistency=sample_consistency(),
        mechanical=mechanical,
        dashboard_ep={"episode": "第1集", "final_pass_rate": 0.9, "recent_blockers": []},
        threshold=85,
    )

    dims = {item["key"]: item for item in result["dimensions"]}
    assert dims["character_consistency"]["status"] == "fail"
    assert dims["character_consistency"]["return_to_stage"] == "image"
    assert dims["subtitle_correctness"]["status"] == "warn"
    assert dims["rhythm_density"]["status"] == "warn"
    assert result["status"] == "fail"
    assert any(task["return_to_stage"] == "image" for task in result["auto_return_tasks"])


def test_visual_checks_affect_review_score_dimensions() -> None:
    result = score.score_episode(
        "/tmp/work",
        "第1集",
        consistency=sample_consistency(),
        mechanical=[],
        visual=sample_visual(),
        threshold=85,
    )

    dims = {item["key"]: item for item in result["dimensions"]}
    assert dims["scene_consistency"]["warnings"] == 1
    assert dims["subtitle_correctness"]["status"] == "fail"
    assert dims["audio_visual_sync"]["warnings"] == 2
    assert dims["rhythm_density"]["status"] == "fail"
    assert any("visual[subtitle_ocr]" in ev for ev in dims["subtitle_correctness"]["evidence"])


def test_missing_data_is_not_silent_pass() -> None:
    result = score.score_episode("/tmp/work", "1", threshold=85)

    assert result["episode"] == "第1集"
    assert result["total_score"] == 70
    assert result["status"] == "fail"
    assert all(item["status"] == "insufficient_data" for item in result["dimensions"])
    assert result["auto_return_tasks"] == []
    assert result["data_collection_tasks"]


def test_auto_return_extracts_shot_and_artifact_scope() -> None:
    result = score.score_episode(
        "/tmp/work",
        "第1集",
        mechanical=[
            {
                "sev": "block",
                "dim": "衔接",
                "loc": "Clip_03",
                "msg": "尾帧接不上 出图/第1集/图片/Clip_03.png",
            }
        ],
        threshold=85,
    )

    task = next(item for item in result["auto_return_tasks"] if item["return_to_stage"] == "image")
    assert "Clip_03" in task["affected_shots"]
    assert "出图/第1集/图片/Clip_03.png" in task["affected_artifacts"]
    assert "定位镜头：Clip_03" in task["scope"]


def write_progress(root: Path) -> None:
    (root / "_进度.md").write_text(
        "\n".join(
            [
                "| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 |",
                "|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
                "| 第1集 | 800 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ |",
            ]
        ),
        encoding="utf-8",
    )


def test_enqueue_low_writes_batch_queue(tmp_path: Path) -> None:
    write_progress(tmp_path)
    result = score.score_episode(
        str(tmp_path),
        "第1集",
        consistency=sample_consistency(),
        mechanical=[],
        threshold=85,
    )

    queue = score.enqueue_low(result, max_concurrency=1, max_retries=1, budget=None, budget_unit=None)

    assert queue is not None
    assert (tmp_path / "生产数据" / "batch_queue.json").is_file()
    tasks = queue["tasks"]
    assert any(task["stage_key"] == "image" for task in tasks)
    assert all(task["reason"] == "rerun" for task in tasks)


def test_enqueue_low_does_not_queue_missing_data(tmp_path: Path) -> None:
    result = score.score_episode(str(tmp_path), "第1集", threshold=85)

    queue = score.enqueue_low(result, max_concurrency=1, max_retries=1, budget=None, budget_unit=None)

    assert queue is None
    assert not (tmp_path / "生产数据" / "batch_queue.json").exists()


def _all_ok_consistency() -> dict:
    keys = ["语义谱系(P0)", "状态百科(P1)", "多模态(P2)", "契约继承", "锚点门(N3)", "脸(G1)", "片内时序(N2)", "服装配色(N1)", "场景(O2)", "接缝接力", "风格(S1)", "糊/低质(N4)"]
    return {"summary": {"by_dim": {k: {"block": 0, "warn": 0, "ok": 5, "skipped": False} for k in keys}}}


def test_p0_p1_p2_have_dedicated_score_dimensions() -> None:
    consistency = {
        "summary": {
            "by_dim": {
                "语义谱系(P0)": {"block": 0, "warn": 1, "ok": 0, "skipped": False},
                "状态百科(P1)": {"block": 1, "warn": 0, "ok": 0, "skipped": False},
                "多模态(P2)": {"block": 0, "warn": 1, "ok": 0, "skipped": False},
            }
        },
        "sections": {
            "状态百科(P1)": {
                "details": [{
                    "verdict": "block",
                    "message": "提前泄露",
                    "affected_shots": ["Clip_03"],
                    "affected_artifacts": ["出图/第1集/prompt/01_分镜出图.md"],
                }]
            }
        },
    }
    res = score.score_episode("/tmp/w", "第1集", consistency=consistency, threshold=85)
    dims = {item["key"]: item for item in res["dimensions"]}
    assert dims["semantic_continuity"]["warnings"] == 1
    assert dims["state_continuity"]["status"] == "fail"
    assert dims["multimodal_continuity"]["warnings"] == 1
    assert any("Clip_03" in task["affected_shots"] for task in res["auto_return_tasks"])


def test_contract_inheritance_has_dedicated_score_dimension() -> None:
    consistency = {
        "summary": {
            "by_dim": {
                "契约继承": {"block": 1, "warn": 0, "ok": 0, "skipped": False},
            }
        },
        "sections": {
            "契约继承": {
                "details": [{
                    "verdict": "block",
                    "message": "场景轴线视线漂移",
                    "affected_artifacts": ["出视频/第1集/prompt/00_总览.md"],
                }]
            }
        },
    }
    res = score.score_episode("/tmp/w", "第1集", consistency=consistency, threshold=85)
    dim = next(item for item in res["dimensions"] if item["key"] == "contract_inheritance")
    assert dim["status"] == "fail"
    assert dim["return_to_stage"] == "video_prompt"
    assert any(task["return_to_stage"] == "video_prompt" for task in res["auto_return_tasks"])


def _all_ok_visual() -> dict:
    # 覆盖 consistency 没碰的 subtitle/audio_visual/rhythm 三维，使健康集真为 pass=100
    return {"sections": {k: {"blocks": 0, "warnings": 0, "infos": 0, "skipped": False}
                         for k in ("image_similarity", "subtitle_ocr", "av_duration", "lip_sync", "final_rhythm_density")}}


def _all_ok_voice_print() -> dict:
    return {"available": True, "mode": "fake", "groups": {"沈念|SHEN": {"lines": [{"band": "ok"}], "floor": 0.72}}}


def test_unmapped_block_does_not_silently_pass() -> None:
    # 健康集（七维全过=100）+ 一个无法归维的 block（水印/完整性）→ 不能 pass，必须 warn + 分诊
    base = score.score_episode(
        "/tmp/w", "第1集", consistency=_all_ok_consistency(), visual=_all_ok_visual(),
        voice_print=_all_ok_voice_print(), mechanical=[], threshold=85)
    assert base["status"] == "pass" and base["total_score"] == 100

    res = score.score_episode(
        "/tmp/w", "第1集", consistency=_all_ok_consistency(), visual=_all_ok_visual(),
        voice_print=_all_ok_voice_print(),
        mechanical=[{"sev": "🔴", "dim": "水印", "loc": "成片", "msg": "缺 AI 可见标识"}],
        threshold=85,
    )
    assert res["status"] == "warn"          # 关键：不再静默放行
    assert [u["dim"] for u in res["unmapped_findings"]] == ["水印"]
    assert any(t.get("action") == "triage_unmapped" for t in res["data_collection_tasks"])


def test_unmapped_low_severity_only_records_not_escalates() -> None:
    # 未归维的 warn/info 只留痕，不把健康集拉下 pass
    res = score.score_episode(
        "/tmp/w", "第1集", consistency=_all_ok_consistency(), visual=_all_ok_visual(),
        voice_print=_all_ok_voice_print(),
        mechanical=[{"sev": "🟡", "dim": "视频", "loc": "Clip_02", "msg": "生成耗时偏高"}],
        threshold=85,
    )
    assert res["status"] == "pass"
    assert [u["dim"] for u in res["unmapped_findings"]] == ["视频"]
    assert any(t.get("action") == "triage_unmapped_low" for t in res["data_collection_tasks"])


def test_dashboard_unmapped_blocker_is_surfaced() -> None:
    res = score.score_episode(
        "/tmp/w", "第1集", consistency=_all_ok_consistency(), visual=_all_ok_visual(),
        voice_print=_all_ok_voice_print(),
        dashboard_ep={"episode": "第1集", "final_pass_rate": 0.95,
                      "recent_blockers": [{"stage": "compose", "dim": "水印", "loc": "成片", "msg": "AI标识缺失"}]},
        threshold=85,
    )
    assert res["status"] == "warn"
    assert any(u["source"] == "dashboard" and u["dim"] == "水印" for u in res["unmapped_findings"])


def test_mapped_findings_still_route_normally() -> None:
    # 回归：能归维的 finding 仍按维度计分，不进 unmapped
    res = score.score_episode(
        "/tmp/w", "第1集", consistency=_all_ok_consistency(), visual=_all_ok_visual(),
        voice_print=_all_ok_voice_print(),
        mechanical=[{"sev": "🔴", "dim": "字幕", "loc": "cue#1", "msg": "时间码越界"}],
        threshold=85,
    )
    assert res["unmapped_findings"] == []
    dims = {item["key"]: item for item in res["dimensions"]}
    assert dims["subtitle_correctness"]["status"] == "fail"


def _drift(characters: dict, *, available: bool = True, episodes=("第1集", "第2集", "第3集")) -> dict:
    return {"available": available, "episodes": list(episodes), "characters": characters}


def test_identity_drift_flags_cross_episode_regression():
    # 沈念早集稳（第2集 ok>0、block=0），第3集开始崩 → 跨集回归，记 warn 到角色一致性
    dims = {k: score.empty_dimension(k) for k in score.DIMENSIONS}
    drift = _drift({
        "沈念": {"episodes": {"第2集": {"ok": 4, "block": 0, "warn": 0},
                              "第3集": {"ok": 1, "block": 2, "warn": 0}},
                 "first_bad_episode": "第3集"},
    })
    score.apply_identity_drift(dims, drift, "第3集")
    cc = dims["character_consistency"]
    assert cc["warnings"] == 1                  # warn 级，不是 block（片内崩脸已由脸(G1)计，避免双重扣分）
    assert cc["blocks"] == 0
    assert any("跨集漂移" in ev for ev in cc["evidence"])


def test_identity_drift_no_signal_when_bad_from_the_start():
    # 角色从第2集就崩（没有"早集稳"）→ 不是跨集回归，跨集层不另加分（交给片内脸(G1)）
    dims = {k: score.empty_dimension(k) for k in score.DIMENSIONS}
    drift = _drift({
        "妖": {"episodes": {"第2集": {"ok": 0, "block": 3, "warn": 0},
                            "第3集": {"ok": 0, "block": 3, "warn": 0}},
               "first_bad_episode": "第2集"},
    })
    score.apply_identity_drift(dims, drift, "第3集")
    assert dims["character_consistency"]["warnings"] == 0


def test_identity_drift_unavailable_marks_skipped_not_pass():
    # 机检不可用（无 insightface / registry）→ 显式标 skipped，不臆造通过
    dims = {k: score.empty_dimension(k) for k in score.DIMENSIONS}
    score.apply_identity_drift(dims, _drift({}, available=False), "第3集")
    cc = dims["character_consistency"]
    assert cc["skipped"] is True
    assert any("跨集漂移机检不可用" in ev for ev in cc["evidence"])


def test_identity_drift_single_episode_window_is_noop():
    dims = {k: score.empty_dimension(k) for k in score.DIMENSIONS}
    score.apply_identity_drift(dims, _drift({"沈念": {"episodes": {"第1集": {"block": 2}}}}, episodes=("第1集",)), "第1集")
    assert dims["character_consistency"]["warnings"] == 0
    assert dims["character_consistency"]["skipped"] is True  # 未被任何信号翻成 not-skipped


def test_pass_rate_floor_none_no_warning():
    dims = {k: score.empty_dimension(k) for k in score.DIMENSIONS}
    score.apply_dashboard(dims, {"final_pass_rate": 0.5}, None)  # floor=None → 不告警(对齐 dashboard 默认)
    assert dims["character_consistency"]["warnings"] == 0


def test_pass_rate_floor_set_warns_below():
    dims = {k: score.empty_dimension(k) for k in score.DIMENSIONS}
    score.apply_dashboard(dims, {"final_pass_rate": 0.5}, 0.8)
    assert dims["character_consistency"]["warnings"] >= 1


def test_resolve_pass_rate_floor_reads_dashboard_thresholds(tmp_path):
    pdir = tmp_path / "生产数据"; pdir.mkdir(parents=True)
    (pdir / "alert_thresholds.json").write_text('{"final_pass_rate_floor": 0.8}', encoding="utf-8")
    assert score.resolve_pass_rate_floor(str(tmp_path), None) == 0.8       # 同 dashboard 同源
    assert score.resolve_pass_rate_floor(str(tmp_path), 0.6) == 0.6        # 显式参数优先
    assert score.resolve_pass_rate_floor(str(tmp_path / "none"), None) is None  # 无配置→None
