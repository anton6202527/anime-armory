from __future__ import annotations

import importlib.util
import json
import struct
import subprocess
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("cover_pack", HERE / "cover_pack.py")
cover_pack = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cover_pack)

INIT = HERE.parent.parent / "scripts" / "init_project.py"


def _make_project(tmp_path: Path) -> Path:
    root = tmp_path / "mv"
    subprocess.run(
        [sys.executable, str(INIT), "--title", "夜航", "--visual-style", "电影叙事",
         "--out", str(root)],
        check=True, capture_output=True, text=True,
    )
    return root


def _write_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def chunk(typ: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\xff\xff")
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                     + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


def test_init_writes_synopsis_and_null_cover(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    meta = json.loads((root / "_meta.json").read_text(encoding="utf-8"))
    assert meta["cover"] is None
    assert isinstance(meta["synopsis"], str) and meta["synopsis"]
    assert "夜航" in meta["synopsis"] and "电影叙事" in meta["synopsis"]
    assert (root / "出图" / "封面" / "prompt").is_dir()
    assert (root / "出图" / "封面" / "图片").is_dir()


def test_pack_produces_prompt_job_and_keeps_cover_null(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    rc = cover_pack.main(["pack", str(root)])
    assert rc == 0
    prompt = root / "出图" / "封面" / "prompt" / "cover_prompt.md"
    job_path = root / "出图" / "封面" / "cover_job.json"
    assert prompt.is_file()
    assert job_path.is_file()
    job = json.loads(job_path.read_text(encoding="utf-8"))
    assert job["generation"]["provider_called"] is False
    # C5: concrete model name is the generator; channel listed separately.
    assert job["generation"]["model"] == "GPT Image 2"
    assert job["generation"]["channel"] == "Codex"
    assert "GPT Image 2" in prompt.read_text(encoding="utf-8")
    # cover stays null on a pure job-pack-only run
    meta = json.loads((root / "_meta.json").read_text(encoding="utf-8"))
    assert meta["cover"] is None
    # progress pack row flipped, rendered row not
    prog_lines = (root / "_进度.md").read_text(encoding="utf-8").splitlines()
    pack_row = next(l for l in prog_lines if "封面 prompt/job 包" in l)
    rendered_row = next(l for l in prog_lines if "封面已渲染" in l)
    assert pack_row.strip().startswith("- [x]")
    assert rendered_row.strip().startswith("- [ ]")


def test_set_cover_backfills_relative_path(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    cover_pack.main(["pack", str(root)])
    png = root / "出图" / "封面" / "图片" / "cover.png"
    _write_png(png)
    rc = cover_pack.main(["set-cover", str(root)])
    assert rc == 0
    meta = json.loads((root / "_meta.json").read_text(encoding="utf-8"))
    assert meta["cover"] == "出图/封面/图片/cover.png"
    assert str(tmp_path) not in json.dumps(meta, ensure_ascii=False)
    prog = (root / "_进度.md").read_text(encoding="utf-8")
    assert "[ ] 封面" not in prog  # both rows flipped


def test_set_cover_without_png_keeps_null(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    cover_pack.main(["pack", str(root)])
    rc = cover_pack.main(["set-cover", str(root)])
    assert rc == 2
    meta = json.loads((root / "_meta.json").read_text(encoding="utf-8"))
    assert meta["cover"] is None


def test_set_cover_does_not_clobber_user_cover(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    meta = json.loads((root / "_meta.json").read_text(encoding="utf-8"))
    meta["cover"] = "出图/封面/图片/user_choice.png"
    (root / "_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    png = root / "出图" / "封面" / "图片" / "cover.png"
    _write_png(png)
    rc = cover_pack.main(["set-cover", str(root)])
    assert rc == 0
    meta2 = json.loads((root / "_meta.json").read_text(encoding="utf-8"))
    assert meta2["cover"] == "出图/封面/图片/user_choice.png"  # not clobbered
    # --force overrides
    cover_pack.main(["set-cover", str(root), "--force"])
    meta3 = json.loads((root / "_meta.json").read_text(encoding="utf-8"))
    assert meta3["cover"] == "出图/封面/图片/cover.png"
