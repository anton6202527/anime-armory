"""golden_set_bootstrap 纯逻辑单测 + 端到端标定链路冒烟。
cd skills/n2d/n2d-review/scripts && python3 -m pytest test_golden_set_bootstrap.py
"""
import json
import os

import golden_set_bootstrap as gb
import calibrate_thresholds as ct
import consistency_threshold_registry as reg


def _drift():
    # 角色 沈念：第1/2 集人审通过且 worst_score 高（pass 锚）；第3/4 集未通过且 block（fail 锚）。
    return {
        "characters": {
            "沈念": {"episodes": {
                "第1集": {"ok": 5, "block": 0, "worst_score": 0.71},
                "第2集": {"ok": 4, "block": 0, "worst_score": 0.68},
                "第3集": {"ok": 1, "block": 2, "worst_score": 0.32},
                "第4集": {"ok": 0, "block": 3, "worst_score": 0.28},
            }},
            "赵中流": {"episodes": {
                "第1集": {"ok": 3, "block": 0, "worst_score": 0.66},
                "第3集": {"ok": 0, "block": 1, "worst_score": 0.30},
            }},
        }
    }


def test_pass_anchors_only_from_accepted_clean_episodes():
    rows = gb.golden_rows_from_drift(_drift(), ["第1集", "第2集"], backend="GPT Image 2")
    passes = [r for r in rows if r["label"] == "pass"]
    fails = [r for r in rows if r["label"] == "fail"]
    # 通过集(1,2)无 block → 3 条 pass（沈念×2 + 赵中流×1）
    assert {(r["character"], r["episode"]) for r in passes} == {
        ("沈念", "第1集"), ("沈念", "第2集"), ("赵中流", "第1集")}
    # 未通过集(3,4)有 block → fail（沈念3/4 + 赵中流3）
    assert {(r["character"], r["episode"]) for r in fails} == {
        ("沈念", "第3集"), ("沈念", "第4集"), ("赵中流", "第3集")}
    assert all(r["backend"] == "GPT Image 2" for r in rows)


def test_no_accepted_episodes_yields_no_pass():
    rows = gb.golden_rows_from_drift(_drift(), [])
    assert [r for r in rows if r["label"] == "pass"] == []
    # 未通过集的 block 仍可作 fail 锚
    assert all(r["label"] == "fail" for r in rows)


def test_accepted_episode_with_block_is_neither():
    # 人审通过却机检 block（相左）→ 不当 pass 也不当 fail（留人工显式标）
    drift = {"characters": {"X": {"episodes": {"第1集": {"block": 2, "worst_score": 0.4}}}}}
    rows = gb.golden_rows_from_drift(drift, ["第1集"])
    assert rows == []


def test_merge_dedups_and_keeps_existing_first():
    existing = [{"dimension": "character_consistency", "backend": "any", "style": "any",
                 "label": "fail", "similarity": 0.30, "episode": "第3集", "character": "沈念",
                 "source": "manual"}]
    new = gb.golden_rows_from_drift(_drift(), ["第1集", "第2集"])
    merged = gb.merge_rows(existing, new)
    # 既有人工 fail 行保留且在前；不被自举重复
    assert merged[0]["source"] == "manual"
    keys = [gb._dedup_key(r) for r in merged]
    assert len(keys) == len(set(keys))


def test_end_to_end_bootstrap_calibrates_registry(tmp_path):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "生产数据"), exist_ok=True)
    with open(os.path.join(root, "生产数据", "identity_drift_report.json"), "w", encoding="utf-8") as fh:
        json.dump(_drift(), fh, ensure_ascii=False)
    # 自举金标行（直接喂逻辑，绕过 _进度.md 解析）
    rows = gb.golden_rows_from_drift(_drift(), ["第1集", "第2集"], backend="any")
    gb.write_golden_set(root, rows)
    # 链式标定：pass(0.66-0.71) 与 fail(0.28-0.32) 完全可分 → separable + 真 floor
    ct.write_calibration(root)
    cal = json.load(open(os.path.join(root, "生产数据", "consistency_threshold_calibration.json"), encoding="utf-8"))
    char_cal = [c for c in cal["calibrations"] if c["dimension"] == "character_consistency"]
    assert char_cal and char_cal[0]["status"] == "separable"
    floor = char_cal[0]["recommended_floor"]
    assert 0.32 < floor < 0.66, floor
    # registry 把该维度从 default_policy_only 升为 calibrated（带真 floor）
    registry = reg.build_registry(root)
    char_rows = [r for r in registry["rows"]
                 if r["dimension"] == "character_consistency" and r.get("evidence_status") == "calibrated"]
    assert char_rows and char_rows[0]["threshold_floor"] == floor


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
            except TypeError:
                import tempfile
                fn(tempfile.mkdtemp())
            print("ok", name)
