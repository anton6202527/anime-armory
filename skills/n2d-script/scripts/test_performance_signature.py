#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import performance_signature as ps  # noqa: E402


def _write_registry(root: Path) -> None:
    shared = root / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "identity_registry.json").write_text(json.dumps({
        "characters": [
            {
                "id": "CHAR_01",
                "name": "沈念",
                "scope": "全篇主角",
                "forms": [{"form": "常态"}],
            },
            {
                "id": "CHAR_02",
                "name": "路人",
                "scope": "单集",
                "forms": [{
                    "form": "常服",
                    "performance_signature": {
                        "micro_expression": "浅笑",
                        "gaze": "回避",
                        "stance": "缩肩",
                        "habitual_gesture": "攥袖",
                        "speech_rhythm": "短句",
                        "action_style": "小步",
                    },
                }],
            },
        ]
    }, ensure_ascii=False), encoding="utf-8")


def test_performance_signature_reports_core_missing_fields(tmp_path: Path) -> None:
    _write_registry(tmp_path)

    report = ps.analyze(tmp_path)

    assert report["kind"] == ps.KIND
    missing = report["rows"][0]["missing_fields"]
    assert set(missing) == set(ps.FIELDS)
    assert any(f["code"] == "core_form_missing_performance_signature" for f in report["findings"])


def test_performance_signature_writes_scaffold(tmp_path: Path) -> None:
    _write_registry(tmp_path)
    report = ps.analyze(tmp_path)
    jp, mp = ps.write_outputs(tmp_path, report)

    assert jp.exists()
    assert mp.exists()
    assert "micro_expression" in mp.read_text(encoding="utf-8")
