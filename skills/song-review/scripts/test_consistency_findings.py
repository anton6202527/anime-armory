from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_module():
    path = Path(__file__).with_name("consistency_findings.py")
    spec = importlib.util.spec_from_file_location("song_consistency_findings", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_song_consistency_flags_take_mismatch_and_master_block(tmp_path: Path) -> None:
    mod = load_module()
    root = tmp_path
    (root / "歌").mkdir(parents=True)
    (root / "歌" / "song.wav").write_bytes(b"wav")
    write_json(root / "词" / "lyric_prosody.json", {"blocking": 0, "warnings": 0})
    write_json(root / "歌" / "song_form.json", {"sections": [{"section": "verse1"}]})
    write_json(root / "歌" / "takes_manifest.json", {
        "selected_take": "take_02",
        "takes": [{"take_id": "take_01"}, {"take_id": "take_02"}],
    })
    write_json(root / "歌" / "take_review.json", {"review_count": 2, "recommended_take": "take_01"})
    write_json(root / "混音" / "master_check.json", {"passed": False, "blocking": 1, "warnings": 0})
    write_json(root / "合规" / "ai_usage.json", {"audio_mode": "AI-generated"})
    write_json(root / "合规" / "rights_metadata.json", {"rights_status": "original"})

    report = mod.build_report(str(root))

    assert report["kind"] == "song_consistency_findings"
    assert report["summary"]["block"] == 1
    assert any(f["code"] == "selected_differs_from_review" for f in report["findings"])
