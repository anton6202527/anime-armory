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
        {"episode": "第1集", "ab_test_id": "EP01_opening", "variant_id": "A", "plays": 80, "retention_3s": 0.7},
        {"episode": "第1集", "ab_test_id": "EP01_opening", "variant_id": "B", "plays": 80, "retention_3s": 0.6},
    ])

    payload = experiments.audit_metrics(str(tmp_path), metrics)
    experiments.write_audit(str(tmp_path), payload)

    assert payload["status"] == "pass"
    assert (tmp_path / "生产数据" / "creative_experiment_audit.json").is_file()


def test_missing_experiment_definition_fails_audit(tmp_path: Path) -> None:
    metrics = tmp_path / "metrics.csv"
    _write_metrics(metrics, [
        {"episode": "第1集", "ab_test_id": "EP01_unknown", "variant_id": "A", "plays": 100},
    ])

    payload = experiments.audit_metrics(str(tmp_path), metrics)

    assert payload["status"] == "fail"
    assert payload["missing_experiment_definitions"] == ["EP01_unknown"]
