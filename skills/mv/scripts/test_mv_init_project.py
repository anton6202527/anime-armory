from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_imported_song_uses_relative_receipt_and_bootstrap_catalog(tmp_path: Path) -> None:
    source = tmp_path / "outside" / "demo.wav"
    source.parent.mkdir()
    source.write_bytes(b"RIFF-demo-audio")
    root = tmp_path / "mv"
    script = Path(__file__).with_name("init_project.py")
    subprocess.run(
        [sys.executable, str(script), "--title", "测试MV", "--song", str(source), "--out", str(root)],
        check=True,
        capture_output=True,
        text=True,
    )
    meta = json.loads((root / "_meta.json").read_text(encoding="utf-8"))
    catalog = json.loads((root / "生产数据" / "artifact_catalog.json").read_text(encoding="utf-8"))
    assert meta["source_song"] == "歌/song.wav"
    assert meta["source_song_origin"]["original_name"] == "demo.wav"
    assert len(meta["source_song_origin"]["sha256"]) == 64
    assert str(tmp_path) not in json.dumps(meta, ensure_ascii=False)
    assert catalog["status"] == "bootstrap"
    assert catalog["project"]["project_id"] == meta["project_id"]
