from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path


def _load(name: str):
    script = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, script)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


contract_trace = _load("contract_trace")
pilot_risk_sampler = _load("pilot_risk_sampler")
stop_loss = _load("stop_loss")
audience_experience = _load("audience_experience")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _write_bytes(path: Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def test_contract_trace_requires_source_id_to_reach_prompt_and_artifact(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(tmp_path / "设定库" / "source_comprehension.json", {
        "kind": "n2d_source_comprehension",
        "status": "confirmed",
        "understanding_contract": {
            "episode_promise_basis": [{"trace_id": "SRC_PROMISE_001", "promise": "找出内鬼"}],
            "character_motives": [],
            "causality_chain": [],
            "foreshadowing_ledger": [],
        },
    })
    _write_json(tmp_path / "脚本" / ep / "preventive_contracts.json", {
        "episode_promise": {"source_trace_ids": ["SRC_PROMISE_001"]},
        "shots": [{"clip_id": "Clip_01", "source_trace_ids": ["SRC_PROMISE_001"]}],
    })
    _write_json(tmp_path / "脚本" / ep / "storyboard.json", {"clips": [{"clip_id": "Clip_01", "source_trace_ids": ["SRC_PROMISE_001"]}]})
    (tmp_path / "出图" / ep / "prompt").mkdir(parents=True)
    (tmp_path / "出图" / ep / "prompt" / "01.md").write_text("SRC_PROMISE_001 Clip_01", encoding="utf-8")
    _write_bytes(tmp_path / "出图" / ep / "图片" / "Clip01.png", b"clip")

    assert contract_trace.build_report(tmp_path, ep)["status"] == "pass"

    (tmp_path / "出图" / ep / "prompt" / "01.md").write_text("missing trace", encoding="utf-8")
    blocked = contract_trace.build_report(tmp_path, ep)
    assert blocked["status"] == "blocked"
    assert "prompt_or_generation_recipe" in blocked["findings"][0]["message"]


def test_mini_pilot_blocks_high_risk_clip_until_evidence_manifest(tmp_path: Path) -> None:
    ep = "第2集"
    _write_json(tmp_path / "脚本" / ep / "storyboard.json", {
        "clips": [{
            "clip_id": "Clip_01",
            "description": "CHAR_A 和 CHAR_B 近景拥抱并说话，首尾帧接缝敏感。",
            "character_ids": ["CHAR_A", "CHAR_B"],
            "dialogue_indices": [1],
        }]
    })
    report = pilot_risk_sampler.build_report(tmp_path, ep)
    assert report["status"] == "blocked"
    assert report["summary"]["risk_clips"] == 1

    video_hash = _write_bytes(tmp_path / "出视频" / ep / "Clip01.mp4", b"mini")
    _write_json(tmp_path / "生产数据" / "mini_qc.json", {"status": "pass"})
    _write_json(tmp_path / "生产数据" / f"mini_pilot_acceptance_{ep}.json", {
        "kind": "n2d_mini_pilot_acceptance",
        "status": "accepted",
        "reviewer": "human-qc",
        "risk_selection": {"method": "risk sampler"},
        "coverage": ["face", "action", "lipsync", "seam"],
        "clips": [{"clip_id": "Clip_01", "artifact_path": f"出视频/{ep}/Clip01.mp4", "artifact_sha256": video_hash, "qc_report": "生产数据/mini_qc.json"}],
    })
    assert pilot_risk_sampler.build_report(tmp_path, ep)["status"] == "pass"


def test_stop_loss_triggers_on_high_redraw_rate(tmp_path: Path) -> None:
    prod = tmp_path / "生产数据"
    prod.mkdir()
    lines = []
    for i in range(10):
        row = {"event": "generation", "id": i}
        if i < 5:
            row["redraw_reason"] = "face drift"
        lines.append(json.dumps(row, ensure_ascii=False))
    (prod / "production_events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload = stop_loss.build_report(tmp_path)

    assert payload["status"] == "critical"
    assert any(v["metric"] == "redraw_rate" for v in payload["violations"])


def test_audience_experience_blocks_missing_opening_hook(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(tmp_path / "脚本" / ep / "storyboard.json", {
        "clips": [
            {"clip_id": "Clip_01", "duration": 3, "dramatic_function": "人物走路"},
            {"clip_id": "Clip_02", "duration": 3, "dramatic_function": "兑现承诺，发现令牌"},
        ]
    })
    _write_json(tmp_path / "脚本" / ep / "preventive_contracts.json", {
        "episode_promise": {"promise": "找令牌", "payoff_or_progress": "找到线索", "cliffhanger": "门外出现新危机"}
    })

    payload = audience_experience.build_report(tmp_path, ep)

    assert payload["status"] == "blocked"
    assert any(f["code"] == "missing_opening_hook" for f in payload["findings"])
