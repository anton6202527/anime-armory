from __future__ import annotations

import copy
import json
import os
import sys


COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

from n2d_thresholds import (  # noqa: E402
    BENCHMARK_RETENTION_SOURCE_KEY,
    BENCHMARK_SCHEMA_ERRORS_KEY,
    BENCHMARK_SCHEMA_VALID_KEY,
    load_benchmark,
    load_reference_benchmark,
    validate_retention_benchmark_schema,
)


def test_reference_retention_benchmark_schema_is_strict() -> None:
    errors = validate_retention_benchmark_schema(load_reference_benchmark())
    assert errors == []


def test_retention_benchmark_schema_requires_provenance() -> None:
    data = copy.deepcopy(load_reference_benchmark())
    del data["retention_benchmarks"]["provenance"]["creative_attention.first_3s_proposition_required"]

    errors = validate_retention_benchmark_schema(data)

    assert any("creative_attention.first_3s_proposition_required" in error for error in errors)


def test_validate_benchmark_cli_accepts_reference(tmp_path) -> None:
    # Smoke the script against a copied reference to catch path/import regressions.
    data = load_reference_benchmark()
    path = tmp_path / "industry_benchmark.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    script_dir = os.path.dirname(__file__)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    import validate_benchmark_schema  # noqa: E402

    assert validate_benchmark_schema.main([str(path)]) == 0


def test_invalid_project_retention_benchmark_does_not_override_reference(tmp_path) -> None:
    prod = tmp_path / "生产数据"
    prod.mkdir()
    (prod / "industry_benchmark.json").write_text(
        json.dumps({
            "retention_benchmarks": {
                "kind": "n2d_retention_benchmarks",
                "schema_version": 2,
                "proxy_thresholds": {"retention_hook_floor": 0.1},
            }
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    data = load_benchmark(str(tmp_path))

    assert data[BENCHMARK_SCHEMA_VALID_KEY] is False
    assert data[BENCHMARK_RETENTION_SOURCE_KEY] == "reference_after_invalid_project_override"
    assert data[BENCHMARK_SCHEMA_ERRORS_KEY]
    assert data["retention_benchmarks"]["proxy_thresholds"]["retention_hook_floor"] == 0.8
