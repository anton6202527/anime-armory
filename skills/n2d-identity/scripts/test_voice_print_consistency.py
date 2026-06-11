"""音色声纹一致性——纯数学 + 优雅降级回归测试（不需要音频后端）。

cd skills/n2d-identity/scripts && python3 -m pytest test_voice_print_consistency.py
"""
import json
import os

import voice_print_consistency as vp


def test_cosine_identical_and_orthogonal():
    assert vp.cosine([1, 0, 0], [1, 0, 0]) == 1.0
    assert abs(vp.cosine([1, 0], [0, 1])) < 1e-9
    assert vp.cosine([0, 0], [1, 1]) == 0.0  # 零向量保护


def test_calibrate_floor_median_minus_drift_margin():
    assert vp.calibrate_floor([]) == vp.FALLBACK_FLOOR                       # 样本不足→保守回退
    assert vp.calibrate_floor([0.9]) == vp.FALLBACK_FLOOR                    # 单句→保守回退
    # 中位数 − 容许跌幅（鲁棒于离群）：median([0.9,0.9,0.9])=0.9 → 0.9-0.18
    assert abs(vp.calibrate_floor([0.9, 0.9, 0.9]) - (0.9 - vp.DRIFT_MARGIN)) < 1e-9
    # 一个离群句不把地板拖到 0：median([0.95,0.95,0.2])=0.95 → 仍 0.95-0.18
    assert abs(vp.calibrate_floor([0.95, 0.95, 0.2]) - (0.95 - vp.DRIFT_MARGIN)) < 1e-9


def test_band_thresholds():
    assert vp.band(0.80, 0.75) == "ok"
    assert vp.band(0.72, 0.75, margin=0.06) == "warn"   # 地板带内
    assert vp.band(0.50, 0.75, margin=0.06) == "bad"    # 低于地板-margin


def test_analyze_group_consistent_no_drift():
    embs = [[1.0, 0.0, 0.0], [0.99, 0.01, 0.0], [0.98, 0.0, 0.02]]
    res = vp.analyze_group(embs)
    assert res["floor_calibrated"] and res["drift_count"] == 0


def test_analyze_group_flags_outlier_drift():
    # 三句同人 + 一句明显另一把嗓子（正交）→ 至少一句 bad
    embs = [[1.0, 0.0], [0.99, 0.01], [1.0, 0.0], [0.0, 1.0]]
    res = vp.analyze_group(embs)
    assert res["drift_count"] >= 1
    assert any(l["band"] == "bad" for l in res["lines"])


def test_analyze_group_single_sample_not_calibrated():
    res = vp.analyze_group([[1.0, 0.0]])
    assert res["floor_calibrated"] is False and res["drift_count"] == 0


def test_analyze_groups_aggregates_drift():
    groups = {
        "沈念|SHEN": [[1.0, 0.0], [0.99, 0.0], [0.0, 1.0]],
        "小禾|HE": [[1.0, 0.0], [0.98, 0.02]],
    }
    agg = vp.analyze_groups(groups)
    assert agg["total_drift"] >= 1 and set(agg["groups"]) == set(groups)


def test_analyze_no_manifest_degrades(tmp_path):
    rep = vp.analyze(str(tmp_path), "第1集")
    assert rep["available"] is False and rep["mode"] == "no_audio"
    assert rep["precision"] == vp.INSUFFICIENT_PRECISION


def test_collect_wav_groups_skips_placeholder(tmp_path):
    d = tmp_path / "合成" / "第1集" / "配音"
    d.mkdir(parents=True)
    for name in ("line_00.wav", "line_01.wav"):
        (d / name).write_bytes(b"RIFF")  # 占位文件，存在即可（不需真音频）
    manifest = [
        {"角色": "沈念", "音色键": "SHEN", "line_wav": "line_00.wav", "占位": False},
        {"角色": "沈念", "音色键": "SHEN", "line_wav": "line_01.wav", "占位": True},  # 占位轨跳过
    ]
    (d / "时长清单.json").write_text(json.dumps(manifest), encoding="utf-8")
    groups, meta = vp.collect_wav_groups(str(tmp_path), "第1集")
    assert groups == {"沈念|SHEN": [str(d / "line_00.wav")]}
    assert meta["status"] == "ok"


def test_analyze_without_backend_degrades_gracefully(tmp_path, monkeypatch):
    # 有可用 wav，但本机无声纹后端 → no_speaker_backend + insufficient_precision（不假报）
    d = tmp_path / "合成" / "第1集" / "配音"
    d.mkdir(parents=True)
    (d / "line_00.wav").write_bytes(b"RIFF")
    (d / "line_01.wav").write_bytes(b"RIFF")
    (d / "时长清单.json").write_text(json.dumps([
        {"角色": "沈念", "音色键": "SHEN", "line_wav": "line_00.wav"},
        {"角色": "沈念", "音色键": "SHEN", "line_wav": "line_01.wav"},
    ]), encoding="utf-8")
    monkeypatch.setattr(vp, "load_speaker_encoder", lambda: (None, None))
    rep = vp.analyze(str(tmp_path), "第1集")
    assert rep["available"] is False and rep["mode"] == "no_speaker_backend"
    assert rep["precision"] == vp.INSUFFICIENT_PRECISION


def test_findings_payload_exports_voice_consistency():
    rep = {
        "kind": vp.VOICE_PRINT_REPORT_KIND,
        "episode": "第1集",
        "available": True,
        "mode": "fake",
        "manifest": "合成/第1集/配音/时长清单.json",
        "groups": {
            "沈念|SHEN": {
                "floor": 0.72,
                "lines": [
                    {"idx": 0, "score": 0.9, "band": "ok"},
                    {"idx": 1, "score": 0.4, "band": "bad"},
                ],
            }
        },
    }
    payload = vp.findings_payload("/work", "第1集", rep)
    assert payload["kind"] == "n2d_consistency_findings"
    assert payload["findings"][0]["dim_key"] == "voice_consistency"
    assert payload["findings"][0]["return_to_stage"] == "voice"
    assert payload["auto_return_tasks"][0]["dimensions"] == ["voice_consistency"]
