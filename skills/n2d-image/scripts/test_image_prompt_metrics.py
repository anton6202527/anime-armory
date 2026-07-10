from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("image_prompt_metrics.py")
spec = importlib.util.spec_from_file_location("image_prompt_metrics", SCRIPT)
metrics = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(metrics)


def _event(asset: str, variant: str, status: str, *, event: str = "generation", cost: float = 0.2) -> dict:
    return {
        "kind": "n2d_production_event",
        "version": 1,
        "episode": "第1集",
        "stage": "image",
        "event": event,
        "generation": {
            "asset": f"出图/第1集/图片/{asset}",
            "status": status,
            "redraw_reason": "手部失败" if event == "redraw" else "",
        },
        "cost": {"amount": cost, "unit": "USD"},
        "meta": {
            "prompt_compiler_version": "1",
            "prompt_profile_version": "2026-07-10.3",
            "prompt_profile": "codex_gpt_image_agent_brief",
            "backend": "codex",
            "model": "gpt-image-2",
            "prompt_task_type": "shot_keyframe",
            "compiled_estimated_text_tokens": "120",
            "compiled_prompt_chars": "420",
            "image_prompt_experiment_id": "EXP_compact",
            "image_prompt_variant": variant,
        },
    }


def _write_inputs(root: Path) -> None:
    events = [
        _event("A1.png", "A", "pass"),
        _event("A2.png", "A", "fail"),
        _event("A2.png", "A", "pass", event="redraw", cost=0.1),
        _event("B1.png", "B", "pass"),
        _event("B2.png", "B", "pass"),
    ]
    production = root / "生产数据"
    production.mkdir(parents=True)
    (production / "production_events.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in events),
        encoding="utf-8",
    )
    qc_dir = production / "image_qc" / "第1集"
    qc_dir.mkdir(parents=True)
    (qc_dir / "image_qc_第1集.json").write_text(json.dumps({
        "episode": "第1集",
        "checks": {
            "face": {"shots": [
                {"png": "图片/A1.png", "verdict": "block"},
                {"png": "图片/A2.png", "verdict": "ok"},
                {"png": "图片/B1.png", "verdict": "ok"},
                {"png": "图片/B2.png", "verdict": "ok"},
            ]},
            "human_anatomy": {"shots": [
                {"png": "图片/A1.png", "verdict": "ok"},
                {"png": "图片/A2.png", "verdict": "ok"},
                {"png": "图片/B1.png", "verdict": "block"},
                {"png": "图片/B2.png", "verdict": "ok"},
            ]},
        },
    }, ensure_ascii=False), encoding="utf-8")


def test_report_groups_real_attempt_qc_cost_and_tokens_by_variant(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    metrics.register_experiment(
        tmp_path,
        "EXP_compact",
        variants=["A", "B"],
        control="A",
        min_samples=2,
        hypothesis="compact profile improves first draw pass without face/hand regression",
    )

    report = metrics.build_report(tmp_path)
    cohorts = {row["variant"]: row for row in report["cohorts"]}

    assert report["summary"]["generation_attempts"] == 5
    assert report["summary"]["qc_join_coverage"] == 1.0
    assert cohorts["A"]["first_draw_pass_rate"] == 0.5
    assert cohorts["A"]["redraw_count"] == 1
    assert cohorts["A"]["identity_drift_rate"] == 0.5
    assert cohorts["A"]["cost_totals"] == {"USD": 0.5}
    assert cohorts["A"]["input_tokens"] == 360
    assert cohorts["B"]["first_draw_pass_rate"] == 1.0
    assert cohorts["B"]["hand_failure_rate"] == 0.5
    assert report["experiments"][0]["decision"] == "keep_control_safety_regression"


def test_report_write_and_experiment_validation(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    report = metrics.build_report(tmp_path)
    json_path, md_path = metrics.write_report(tmp_path, report)

    assert json_path.is_file() and md_path.is_file()
    assert "Compiler / Profile cohorts" in md_path.read_text(encoding="utf-8")
    try:
        metrics.register_experiment(
            tmp_path,
            "bad",
            variants=["A"],
            control="A",
            min_samples=1,
            hypothesis="invalid",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("one-variant experiment must be rejected")
