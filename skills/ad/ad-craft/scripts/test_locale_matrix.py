import json
from pathlib import Path

import locale_matrix as lm


def _project(tmp_path: Path):
    root = tmp_path / "ad"
    for rel, content in {
        "脚本/voiceover.txt": "现在购买",
        "脚本/字幕_zh.srt": "1\n00:00:00,000 --> 00:00:01,000\n现在购买\n",
        "证据/zh-typography.md": "具名排版复核",
    }.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    plan = {"deliverables": [{"deliverable_id": "master", "status": "rendered"}]}
    matrix = {
        "schema_version": 1,
        "kind": "ad_locale_matrix",
        "default_locale": "zh-CN",
        "locales": {"zh-CN": {
            "language": "zh-CN", "jurisdictions": ["中国大陆"], "currency": "CNY",
            "unit_system": "metric", "cta": "现在购买", "legal_lines": ["广告"],
            "voiceover_path": "脚本/voiceover.txt", "subtitle_path": "脚本/字幕_zh.srt",
            "translation_review": {"status": "source_language"},
            "typography_review": {"status": "approved", "approved_by": "设计甲",
                                    "evidence": "证据/zh-typography.md"},
        }},
        "deliverable_locales": {"master": ["zh-CN"]},
    }
    path = root / "合规" / "locale_matrix.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(matrix, ensure_ascii=False), encoding="utf-8")
    return root, plan, matrix


def test_locale_matrix_binds_copy_media_layout_and_delivery(tmp_path):
    root, plan, matrix = _project(tmp_path)
    report = lm.validate(root, matrix, plan)
    assert report["summary"]["block"] == 0
    assert report["locales"]["zh-CN"]["files"]["subtitle_path"]["sha256"]
    assert report["deliverable_locales"] == {"master": ["zh-CN"]}


def test_locale_matrix_blocks_pending_currency_and_unmapped_variant(tmp_path):
    root, plan, matrix = _project(tmp_path)
    matrix["locales"]["zh-CN"]["currency"] = "待补"
    matrix["deliverable_locales"] = {}
    report = lm.validate(root, matrix, plan)
    codes = {row["code"] for row in report["findings"]}
    assert {"locale_fields_missing", "deliverable_locale_missing"} <= codes


def test_default_locale_cannot_drift_from_approved_brief_cta(tmp_path):
    root, plan, matrix = _project(tmp_path)
    (root / "需求").mkdir()
    (root / "需求" / "brief.json").write_text(json.dumps({
        "mandatories": {"cta": "立即注册", "legal_lines": ["广告"]}
    }, ensure_ascii=False), encoding="utf-8")
    report = lm.validate(root, matrix, plan)
    assert any(row["code"] == "source_locale_cta_mismatch" for row in report["findings"])
