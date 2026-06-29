#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import golden_calibration


def test_golden_calibration_fixture_projects_pass():
    report = golden_calibration.run_calibration()
    assert report["passed"] is True
    assert report["case_count"] == 3
    assert report["failure_count"] == 0
    by_name = {item["name"]: item for item in report["results"]}
    assert by_name["original_legacy_missing_kind"]["project_kind"] == "create"
    assert by_name["short_drama_score_review_retrieval"]["retrieval"]["passed"] is True
