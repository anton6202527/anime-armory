#!/usr/bin/env python3
import json
import os
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import work_card_meta as wcm


def _write_meta(root: Path, **fields):
    meta = {"schema_version": 1, "kind": "n2d_project", "line": "n2d", "title": "T"}
    meta.update(fields)
    (root / "_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


def _tiny_png(path: Path) -> None:
    # Minimal valid 1x1 PNG.
    path.parent.mkdir(parents=True, exist_ok=True)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_chunk = struct.pack(">I", len(ihdr)) + b"IHDR" + ihdr + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr) & 0xFFFFFFFF)
    raw = b"\x00\xff\xff\xff"
    comp = zlib.compress(raw)
    idat_chunk = struct.pack(">I", len(comp)) + b"IDAT" + comp + struct.pack(">I", zlib.crc32(b"IDAT" + comp) & 0xFFFFFFFF)
    iend_chunk = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
    path.write_bytes(sig + ihdr_chunk + idat_chunk + iend_chunk)


def test_ensure_fields_write_if_absent(tmp_path):
    _write_meta(tmp_path)
    changed = wcm.ensure_work_card_fields(tmp_path)
    assert changed == {"synopsis": "", "cover": None}
    meta = wcm.load_meta(tmp_path)
    assert meta["synopsis"] == ""
    assert meta["cover"] is None


def test_ensure_does_not_clobber(tmp_path):
    _write_meta(tmp_path, synopsis="用户写的简介", cover="出图/封面/cover.png")
    changed = wcm.ensure_work_card_fields(tmp_path, synopsis="别的")
    assert changed == {}
    meta = wcm.load_meta(tmp_path)
    assert meta["synopsis"] == "用户写的简介"
    assert meta["cover"] == "出图/封面/cover.png"


def test_backfill_synopsis_from_dev_bible(tmp_path):
    _write_meta(tmp_path, synopsis="", cover=None)
    (tmp_path / "开发包").mkdir()
    (tmp_path / "开发包" / "series_bible.md").write_text(
        "# X\n\n## 一句话卖点\n穿越少女靠斩妖系统一路逆袭封神。\n\n## 目标受众\n待补\n",
        encoding="utf-8",
    )
    wrote, value = wcm.backfill_synopsis(tmp_path)
    assert wrote is True
    assert value == "穿越少女靠斩妖系统一路逆袭封神。"


def test_backfill_synopsis_falls_back_to_strategy(tmp_path):
    _write_meta(tmp_path, synopsis="待补", cover=None)
    (tmp_path / "开发包").mkdir()
    (tmp_path / "开发包" / "adaptation_strategy.json").write_text(
        json.dumps({"principles": ["保留底层逆袭、资源经营四个核心承诺"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    wrote, value = wcm.backfill_synopsis(tmp_path)
    assert wrote is True
    assert "核心承诺" in value


def test_backfill_synopsis_skips_placeholder_only(tmp_path):
    _write_meta(tmp_path, synopsis="", cover=None)
    (tmp_path / "开发包").mkdir()
    (tmp_path / "开发包" / "series_bible.md").write_text(
        "## 一句话卖点\n待补：观众为什么点开。\n", encoding="utf-8"
    )
    wrote, value = wcm.backfill_synopsis(tmp_path)
    assert wrote is False
    assert value == ""


def test_backfill_synopsis_does_not_overwrite_user(tmp_path):
    _write_meta(tmp_path, synopsis="用户的真实简介", cover=None)
    (tmp_path / "开发包").mkdir()
    (tmp_path / "开发包" / "series_bible.md").write_text(
        "## 一句话卖点\n候选卖点。\n", encoding="utf-8"
    )
    wrote, value = wcm.backfill_synopsis(tmp_path)
    assert wrote is False
    assert value == "用户的真实简介"


def test_synopsis_clipped_to_240(tmp_path):
    _write_meta(tmp_path, synopsis="", cover=None)
    (tmp_path / "开发包").mkdir()
    long = "很长的卖点" * 100
    (tmp_path / "开发包" / "series_bible.md").write_text(
        f"## 一句话卖点\n{long}\n", encoding="utf-8"
    )
    wrote, value = wcm.backfill_synopsis(tmp_path)
    assert wrote is True
    assert len(value) <= wcm.SYNOPSIS_MAX


def test_backfill_cover_valid_png(tmp_path):
    _write_meta(tmp_path, synopsis="", cover=None)
    _tiny_png(tmp_path / "出图" / "封面" / "cover.png")
    wrote, cover, reason = wcm.backfill_cover(tmp_path)
    assert wrote is True
    assert cover == "出图/封面/cover.png"
    assert reason == "backfilled"
    assert wcm.load_meta(tmp_path)["cover"] == "出图/封面/cover.png"


def test_backfill_cover_missing_png_keeps_null(tmp_path):
    _write_meta(tmp_path, synopsis="", cover=None)
    wrote, cover, reason = wcm.backfill_cover(tmp_path)
    assert wrote is False
    assert reason == "file_missing"
    assert wcm.load_meta(tmp_path)["cover"] is None


def test_backfill_cover_rejects_non_png(tmp_path):
    _write_meta(tmp_path, synopsis="", cover=None)
    p = tmp_path / "出图" / "封面" / "cover.png"
    p.parent.mkdir(parents=True)
    p.write_bytes(b"not a png")
    wrote, cover, reason = wcm.backfill_cover(tmp_path)
    assert wrote is False
    assert reason == "not_png"


def test_backfill_cover_rejects_escape(tmp_path):
    _write_meta(tmp_path, synopsis="", cover=None)
    wrote, cover, reason = wcm.backfill_cover(tmp_path, "../evil.png")
    assert wrote is False
    assert reason == "path_escapes_root"


def test_backfill_cover_does_not_clobber_existing(tmp_path):
    _write_meta(tmp_path, synopsis="", cover="出图/封面/old.png")
    _tiny_png(tmp_path / "出图" / "封面" / "cover.png")
    wrote, cover, reason = wcm.backfill_cover(tmp_path)
    assert wrote is False
    assert reason == "cover_already_set_keep"
    assert wcm.load_meta(tmp_path)["cover"] == "出图/封面/old.png"
