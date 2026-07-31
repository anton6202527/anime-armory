import json
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asr_consistency as ac  # noqa: E402


def _project(tmp_path: Path):
    root = tmp_path / "ad"
    for rel, content in {
        "脚本/voiceover.txt": "山岚咖啡仅需99元，立即购买。广告。",
        "脚本/字幕_zh.srt": "1\n00:00:00,000 --> 00:00:02,000\n山岚咖啡仅需99元，立即购买。广告。\n",
        "配音/asr/vo.txt": "山岚咖啡仅需99元，立即购买。广告。",
        "合成/asr/master.txt": "山岚咖啡仅需99元，立即购买。广告。",
    }.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (root / "配音" / "vo.wav").write_bytes(b"vo")
    (root / "合成" / "成片_主片.mp4").write_bytes(b"master")
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    (root / "合成" / "asr_receipts.json").write_text(json.dumps({
        "schema_version": 1, "kind": "ad_asr_receipts", "receipts": {
            "vo": {"media_sha256": sha(root / "配音" / "vo.wav"),
                   "transcript_sha256": sha(root / "配音" / "asr" / "vo.txt"),
                   "engine": "whisper-large-v3", "checked_at": "2026-07-11"},
            "master": {"media_sha256": sha(root / "合成" / "成片_主片.mp4"),
                       "transcript_sha256": sha(root / "合成" / "asr" / "master.txt"),
                       "engine": "whisper-large-v3", "checked_at": "2026-07-11"},
        }}), encoding="utf-8")
    (root / "需求").mkdir()
    (root / "需求" / "brief.json").write_text(json.dumps({
        "claims": [{"id": "claim_01", "claim": "山岚咖啡仅需99元"}],
        "mandatories": {"cta": "立即购买", "legal_lines": ["广告"]},
    }, ensure_ascii=False), encoding="utf-8")
    return root


def test_asr_four_way_exact_critical_copy_passes(tmp_path):
    root = _project(tmp_path)
    report = ac.build(root)
    assert report["summary"]["block"] == 0
    assert {row["kind"] for row in report["critical_terms"]} >= {"number_or_price", "cta", "claim", "legal"}
    assert all(term["present"] for result in report["comparisons"].values()
               for term in result["critical_terms"])


def test_asr_price_change_blocks_even_when_rest_is_similar(tmp_path):
    root = _project(tmp_path)
    (root / "合成" / "asr" / "master.txt").write_text("山岚咖啡仅需199元，立即购买。广告。", encoding="utf-8")
    report = ac.build(root)
    assert report["comparisons"]["master"]["numeric_tokens_exact"] is False
    price = next(row for row in report["comparisons"]["master"]["critical_terms"]
                 if row["kind"] == "number_or_price")
    assert price["present"] is False
    assert any(row["code"] == "critical_numeric_set_mismatch" for row in report["findings"])
    assert any(row["code"] == "asr_receipt_invalid" for row in report["findings"])
