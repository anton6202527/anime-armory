from __future__ import annotations

import struct
import zlib
from pathlib import Path

from image_evidence import png_evidence_errors


def _chunk(kind: bytes, payload: bytes, *, corrupt_crc: bool = False) -> bytes:
    body = kind + payload
    crc = zlib.crc32(body) & 0xFFFFFFFF
    if corrupt_crc:
        crc ^= 1
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", crc)


def _rgb_png(width: int = 512, height: int = 512) -> bytes:
    raw = b"".join(b"\0" + b"\x20\x40\x60" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(raw))
        + _chunk(b"IEND", b"")
    )


def test_valid_decodable_png_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "valid.png"
    path.write_bytes(_rgb_png())

    assert png_evidence_errors(path) == []


def test_forged_ihdr_iend_shell_without_pixels_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "shell.png"
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", 512, 512, 8, 2, 0, 0, 0))
        + _chunk(b"IEND", b"")
    )

    errors = png_evidence_errors(path)
    assert "not_valid_png_container" in errors
    assert "png_iend_invalid" in errors


def test_crc_and_zlib_payload_are_both_verified(tmp_path: Path) -> None:
    crc_path = tmp_path / "crc.png"
    data = _rgb_png()
    idat_at = data.index(b"IDAT")
    payload_length = struct.unpack(">I", data[idat_at - 4:idat_at])[0]
    crc_at = idat_at + 4 + payload_length
    corrupted = bytearray(data)
    corrupted[crc_at + 3] ^= 1
    crc_path.write_bytes(corrupted)
    assert any(code.startswith("png_crc_mismatch:IDAT") for code in png_evidence_errors(crc_path))

    zlib_path = tmp_path / "zlib.png"
    zlib_path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", 512, 512, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", b"not-a-zlib-stream")
        + _chunk(b"IEND", b"")
    )
    assert "png_idat_zlib_invalid" in png_evidence_errors(zlib_path)


def test_scanline_length_and_filter_byte_are_verified(tmp_path: Path) -> None:
    short_path = tmp_path / "short.png"
    short_path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", 512, 512, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(b"\0pixels"))
        + _chunk(b"IEND", b"")
    )
    assert "png_scanline_data_incomplete" in png_evidence_errors(short_path)

    bad_filter = bytearray(b"".join(b"\0" + b"\0\0\0" * 512 for _ in range(512)))
    bad_filter[0] = 5
    filter_path = tmp_path / "filter.png"
    filter_path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", 512, 512, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(bytes(bad_filter)))
        + _chunk(b"IEND", b"")
    )
    assert "png_filter_type_invalid" in png_evidence_errors(filter_path)
