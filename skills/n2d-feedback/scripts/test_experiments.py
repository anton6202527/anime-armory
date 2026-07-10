from __future__ import annotations

import csv
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("experiments.py")
spec = importlib.util.spec_from_file_location("experiments", SCRIPT)
experiments = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(experiments)


def _write_metrics(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_registered_experiment_passes_audit(tmp_path: Path) -> None:
    data = experiments.upsert_experiment(
        str(tmp_path),
        "EP01_opening",
        episode="第1集",
        hypothesis="冷开场提升3秒留存",
        variants=[
            {"variant_id": "A", "description": "cold open"},
            {"variant_id": "B", "description": "system panel"},
        ],
        primary_metric="retention_3s",
        min_samples=100,
    )
    experiments.save_experiments(str(tmp_path), data)
    metrics = tmp_path / "metrics.csv"
    _write_metrics(metrics, [
        {"episode": "第1集", "ab_test_id": "EP01_opening", "variant_id": "A", "plays": 120, "retention_3s": 0.7},
        {"episode": "第1集", "ab_test_id": "EP01_opening", "variant_id": "B", "plays": 120, "retention_3s": 0.6},
    ])

    payload = experiments.audit_metrics(str(tmp_path), metrics)
    experiments.write_audit(str(tmp_path), payload)

    assert payload["status"] == "pass"
    assert payload["analyses"][0]["variant_metrics"]["A"]["ci95"]
    assert (tmp_path / "生产数据" / "creative_experiment_audit.json").is_file()


def test_missing_experiment_definition_fails_audit(tmp_path: Path) -> None:
    metrics = tmp_path / "metrics.csv"
    _write_metrics(metrics, [
        {"episode": "第1集", "ab_test_id": "EP01_unknown", "variant_id": "A", "plays": 100},
    ])

    payload = experiments.audit_metrics(str(tmp_path), metrics)

    assert payload["status"] == "fail"
    assert payload["missing_experiment_definitions"] == ["EP01_unknown"]


def test_min_samples_are_required_per_variant_not_summed(tmp_path: Path) -> None:
    data = experiments.upsert_experiment(
        str(tmp_path), "EXP", episode="第1集", hypothesis="x",
        variants=[{"variant_id": "A", "description": "a"}, {"variant_id": "B", "description": "b"}],
        primary_metric="retention_3s", min_samples=100,
    )
    experiments.save_experiments(str(tmp_path), data)
    metrics = tmp_path / "metrics.csv"
    _write_metrics(metrics, [
        {"ab_test_id": "EXP", "variant_id": "A", "plays": 150, "retention_3s": 0.5},
        {"ab_test_id": "EXP", "variant_id": "B", "plays": 60, "retention_3s": 0.8},
    ])
    payload = experiments.audit_metrics(str(tmp_path), metrics)
    assert payload["status"] == "observe"
    assert payload["underpowered"][0]["variant_id"] == "B"


def test_significant_lift_promotes_candidate_after_correction(tmp_path: Path) -> None:
    data = experiments.upsert_experiment(
        str(tmp_path), "EXP", episode="第1集", hypothesis="x",
        variants=[{"variant_id": "A", "description": "control"}, {"variant_id": "B", "description": "candidate"}],
        primary_metric="retention_3s", min_samples=500,
    )
    experiments.save_experiments(str(tmp_path), data)
    metrics = tmp_path / "metrics.csv"
    _write_metrics(metrics, [
        {"ab_test_id": "EXP", "variant_id": "A", "plays": 1000, "retention_3s": 0.50},
        {"ab_test_id": "EXP", "variant_id": "B", "plays": 1000, "retention_3s": 0.65},
    ])
    payload = experiments.audit_metrics(str(tmp_path), metrics)
    analysis = payload["analyses"][0]
    assert payload["status"] == "pass"
    assert analysis["decision"] == "promote_variant" and analysis["winner"] == "B"
    assert analysis["comparisons"][0]["significant"] is True


def test_sequential_peeking_without_alpha_spending_is_observe(tmp_path: Path) -> None:
    data = experiments.upsert_experiment(
        str(tmp_path), "EXP", episode="第1集", hypothesis="x",
        variants=[{"variant_id": "A", "description": "a"}, {"variant_id": "B", "description": "b"}],
        primary_metric="retention_3s", min_samples=100,
    )
    experiments.save_experiments(str(tmp_path), data)
    metrics = tmp_path / "metrics.csv"
    _write_metrics(metrics, [
        {"ab_test_id": "EXP", "variant_id": "A", "plays": 100, "retention_3s": 0.5, "look_index": 1},
        {"ab_test_id": "EXP", "variant_id": "A", "plays": 100, "retention_3s": 0.5, "look_index": 2},
        {"ab_test_id": "EXP", "variant_id": "B", "plays": 100, "retention_3s": 0.6, "look_index": 1},
        {"ab_test_id": "EXP", "variant_id": "B", "plays": 100, "retention_3s": 0.6, "look_index": 2},
    ])
    payload = experiments.audit_metrics(str(tmp_path), metrics)
    assert payload["status"] == "observe"
    assert payload["analysis_warnings"][0]["code"] == "sequential_peeking_without_alpha_spending"
