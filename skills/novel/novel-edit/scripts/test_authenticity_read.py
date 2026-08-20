import json
import os
import tempfile

import authenticity_read as ar


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def test_absent_authenticity_read_is_optional_and_passes():
    with tempfile.TemporaryDirectory() as root:
        report = ar.check(root)
        assert report["applicable"] is False
        assert report["passed"] is True
        assert report["blocking"] == 0
        assert report["project_root"] == "."


def test_malformed_optional_record_warns_but_does_not_invent_a_required_gate():
    with tempfile.TemporaryDirectory() as root:
        report = ar.check(root, {"kind": "wrong"})
        assert report["required_for_release"] is False
        assert report["blocking"] == 0
        assert report["warnings"] == 1


def test_malformed_optional_json_file_warns_instead_of_crashing():
    with tempfile.TemporaryDirectory() as root:
        _write(os.path.join(root, ar.REL_JSON), "{not-json")
        report = ar.check(root)
        assert report["applicable"] is True
        assert report["required_for_release"] is False
        assert report["blocking"] == 0
        assert any(item["id"] == "AUTH-SCHEMA" for item in report["findings"])


def test_required_read_cannot_pass_without_scope_or_reviewer_identity():
    with tempfile.TemporaryDirectory() as root:
        payload = ar.scaffold(
            root,
            scopes=[],
            reader_id="",
            fit_statement="",
            required=True,
        )
        report = ar.check(root, payload)
        ids = {item["id"] for item in report["findings"]}
        assert report["passed"] is False
        assert {"AUTH-SCOPE-MISSING", "AUTH-REVIEWER-ID-MISSING", "AUTH-REVIEWER-FIT-MISSING"} <= ids


def test_required_read_blocks_until_completed_and_major_finding_decided():
    with tempfile.TemporaryDirectory() as root:
        _write(os.path.join(root, "章节", "第01章.md"), "正文版本一")
        payload = ar.scaffold(
            root,
            scopes=["移民家庭中的代际冲突"],
            reader_id="reader-01",
            fit_statement="熟悉相关社区语境；不代表整个群体",
            required=True,
        )
        item = ar.add_finding(
            payload,
            category="agency",
            severity="major",
            location="第1章第3场",
            observation="配角只承担教育主角的功能，缺少自身选择。",
            suggestion="补一个不以主角为中心的决定及后果。",
        )
        assert ar.check(root, payload)["blocking"] >= 1
        ar.resolve_finding(
            payload,
            item["id"],
            decision="adapted",
            author_note="补入配角拒绝调解并承担家庭压力的场景。",
            decided_by="author-a",
        )
        ar.complete_read(root, payload, summary="已复核目标场景和全稿人物能动性。")
        report = ar.check(root, payload)
        assert report["passed"] is True
        assert report["blocking"] == 0
        assert item["decided_by"] == "author-a"


def test_required_read_rejects_fake_closed_major_and_question_remains_open():
    with tempfile.TemporaryDirectory() as root:
        _write(os.path.join(root, "章节", "第01章.md"), "正文")
        payload = ar.scaffold(
            root,
            scopes=["目标场景"],
            reader_id="reader-a",
            fit_statement="熟悉目标语境",
            required=True,
        )
        item = ar.add_finding(
            payload,
            category="context",
            severity="major",
            location="第1章",
            observation="需要补足语境。",
        )
        ar.complete_read(root, payload, summary="完成审读。")
        item["status"] = "closed"
        report = ar.check(root, payload)
        assert any(item["id"] == "AUTH-MAJOR-DECISION-INCOMPLETE" for item in report["findings"])

        ar.resolve_finding(
            payload,
            "AUTH-001",
            decision="questioned",
            author_note="请审读者说明这一建议适用的地区范围。",
            decided_by="author-a",
        )
        assert payload["findings"][0]["status"] == "questioned"
        report = ar.check(root, payload)
        assert any(item["id"] == "AUTH-MAJOR-OPEN" for item in report["findings"])


def test_completed_required_read_becomes_stale_after_chapter_change():
    with tempfile.TemporaryDirectory() as root:
        chapter = os.path.join(root, "章节", "第01章.md")
        _write(chapter, "正文版本一")
        payload = ar.scaffold(
            root,
            scopes=["残障角色的日常经验"],
            reader_id="reader-02",
            fit_statement="与目标经验相符的审读顾问",
            required=True,
        )
        ar.complete_read(root, payload, summary="当前版本已审读。")
        _write(chapter, "正文版本二")
        report = ar.check(root, payload)
        assert report["passed"] is False
        assert any(item["id"] == "AUTH-SNAPSHOT-STALE" for item in report["findings"])


def test_completed_required_read_becomes_stale_after_new_chapter_is_added():
    with tempfile.TemporaryDirectory() as root:
        _write(os.path.join(root, "章节", "第01章.md"), "正文版本一")
        payload = ar.scaffold(
            root,
            scopes=["跨文化家庭场景"],
            reader_id="reader-04",
            fit_statement="熟悉本次目标语境的审读顾问",
            required=True,
        )
        ar.complete_read(root, payload, summary="已审读当前全部章节。")
        _write(os.path.join(root, "章节", "第02章.md"), "新增正文")
        report = ar.check(root, payload)
        assert report["passed"] is False
        assert any(item["id"] == "AUTH-SNAPSHOT-STALE" for item in report["findings"])


def test_cli_round_trip_writes_author_decision():
    with tempfile.TemporaryDirectory() as root:
        assert ar.main([
            "scaffold", root,
            "--scope", "宗教仪式场景",
            "--reader-id", "reader-03",
            "--fit", "熟悉该仪式的文化顾问",
        ]) == 0
        assert ar.main([
            "add", root,
            "--category", "context",
            "--severity", "consider",
            "--location", "第2章",
            "--observation", "仪式动作缺少角色所处地区的语境。",
        ]) == 0
        assert ar.main([
            "resolve", root,
            "--finding", "AUTH-001",
            "--decision", "declined",
            "--author-note", "本段为虚构宗教，前文已明确非现实仪式。",
            "--decided-by", "author-a",
        ]) == 0
        with open(os.path.join(root, ar.REL_JSON), encoding="utf-8") as handle:
            payload = json.load(handle)
        assert payload["findings"][0]["author_decision"] == "declined"
        assert payload["findings"][0]["decided_by"] == "author-a"
