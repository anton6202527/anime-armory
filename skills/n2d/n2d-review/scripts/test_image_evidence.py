from __future__ import annotations

import hashlib
import struct
import zlib
from pathlib import Path

from image_evidence import png_decoded_pixel_fingerprint, png_evidence_errors


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


def _paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    distances = (abs(estimate - left), abs(estimate - up), abs(estimate - upper_left))
    return (left, up, upper_left)[distances.index(min(distances))]


def _filtered(row: bytes, previous: bytes, filter_type: int, bpp: int) -> bytes:
    encoded = bytearray(len(row))
    for index, value in enumerate(row):
        left = row[index - bpp] if index >= bpp else 0
        up = previous[index] if previous else 0
        upper_left = previous[index - bpp] if previous and index >= bpp else 0
        predictor = {
            0: 0,
            1: left,
            2: up,
            3: (left + up) // 2,
            4: _paeth(left, up, upper_left),
        }[filter_type]
        encoded[index] = (value - predictor) & 0xFF
    return bytes(encoded)


def _packed_samples(samples: list[int], bit_depth: int) -> bytes:
    if bit_depth == 8:
        return bytes(samples)
    if bit_depth == 16:
        return struct.pack(f">{len(samples)}H", *samples)
    out = bytearray((len(samples) * bit_depth + 7) // 8)
    for index, sample in enumerate(samples):
        bit_offset = index * bit_depth
        out[bit_offset // 8] |= sample << (8 - bit_depth - (bit_offset % 8))
    return bytes(out)


def _solid_row(width: int, color_type: int, bit_depth: int) -> bytes:
    maximum = (1 << bit_depth) - 1
    pixel = {
        0: [0],
        2: [0, 0, 0],
        3: [0],
        4: [0, maximum],
        6: [0, 0, 0, maximum],
    }[color_type]
    return _packed_samples(pixel * width, bit_depth)


def _solid_png(
    *,
    width: int,
    height: int,
    color_type: int,
    bit_depth: int,
    filter_type: int = 0,
    compression_level: int = 6,
    metadata: bool = False,
    interlace: int = 0,
) -> bytes:
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
    bpp = max(1, (channels * bit_depth + 7) // 8)
    raw = bytearray()
    passes = ((0, 0, 1, 1),) if not interlace else (
        (0, 0, 8, 8),
        (4, 0, 8, 8),
        (0, 4, 4, 8),
        (2, 0, 4, 4),
        (0, 2, 2, 4),
        (1, 0, 2, 2),
        (0, 1, 1, 2),
    )
    for x0, y0, dx, dy in passes:
        pass_width = (width - x0 + dx - 1) // dx if width > x0 else 0
        pass_height = (height - y0 + dy - 1) // dy if height > y0 else 0
        if not pass_width or not pass_height:
            continue
        row = _solid_row(pass_width, color_type, bit_depth)
        previous = b""
        for _ in range(pass_height):
            raw.extend(bytes((filter_type,)) + _filtered(row, previous, filter_type, bpp))
            previous = row
    chunks = [
        _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, bit_depth, color_type, 0, 0, interlace))
    ]
    if color_type == 3:
        chunks.append(_chunk(b"PLTE", b"\0\0\0"))
    if metadata:
        chunks.append(_chunk(b"tEXt", b"audit-note\0different metadata"))
    chunks.extend(
        (
            _chunk(b"IDAT", zlib.compress(bytes(raw), compression_level)),
            _chunk(b"IEND", b""),
        )
    )
    return b"\x89PNG\r\n\x1a\n" + b"".join(chunks)


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


def test_decoded_pixel_fingerprint_ignores_compression_filter_and_metadata(
    tmp_path: Path,
) -> None:
    plain = tmp_path / "plain.png"
    reencoded = tmp_path / "reencoded.png"
    plain.write_bytes(
        _solid_png(
            width=17,
            height=11,
            color_type=2,
            bit_depth=8,
            filter_type=0,
            compression_level=1,
        )
    )
    reencoded.write_bytes(
        _solid_png(
            width=17,
            height=11,
            color_type=2,
            bit_depth=8,
            filter_type=4,
            compression_level=9,
            metadata=True,
        )
    )

    plain_fp, plain_errors = png_decoded_pixel_fingerprint(plain, min_width=1, min_height=1)
    reencoded_fp, reencoded_errors = png_decoded_pixel_fingerprint(
        reencoded, min_width=1, min_height=1
    )

    assert hashlib.sha256(plain.read_bytes()).digest() != hashlib.sha256(reencoded.read_bytes()).digest()
    assert plain_errors == reencoded_errors == []
    assert plain_fp and plain_fp == reencoded_fp


def test_decoded_pixel_fingerprint_supports_all_legal_color_depth_pairs(
    tmp_path: Path,
) -> None:
    legal = {
        0: (1, 2, 4, 8, 16),
        2: (8, 16),
        3: (1, 2, 4, 8),
        4: (8, 16),
        6: (8, 16),
    }
    fingerprints = set()
    for color_type, bit_depths in legal.items():
        for bit_depth in bit_depths:
            path = tmp_path / f"ct{color_type}_bd{bit_depth}.png"
            path.write_bytes(
                _solid_png(
                    width=9,
                    height=3,
                    color_type=color_type,
                    bit_depth=bit_depth,
                    filter_type=1,
                )
            )
            fingerprint, errors = png_decoded_pixel_fingerprint(
                path, min_width=1, min_height=1
            )
            assert errors == [], (color_type, bit_depth, errors)
            assert fingerprint
            fingerprints.add(fingerprint)
    # Every fixture decodes to the same opaque-black RGBA16 pixels.
    assert len(fingerprints) == 1


def test_adam7_and_noninterlaced_encodings_share_pixel_fingerprint(tmp_path: Path) -> None:
    plain = tmp_path / "plain.png"
    adam7 = tmp_path / "adam7.png"
    plain.write_bytes(
        _solid_png(width=17, height=11, color_type=6, bit_depth=16, interlace=0)
    )
    adam7.write_bytes(
        _solid_png(width=17, height=11, color_type=6, bit_depth=16, interlace=1)
    )

    plain_fp, plain_errors = png_decoded_pixel_fingerprint(plain, min_width=1, min_height=1)
    adam7_fp, adam7_errors = png_decoded_pixel_fingerprint(adam7, min_width=1, min_height=1)

    assert plain_errors == adam7_errors == []
    assert plain_fp and plain_fp == adam7_fp


def test_pixel_fingerprint_rejects_transparency_chunk_order_ambiguity(
    tmp_path: Path,
) -> None:
    after_idat = tmp_path / "trns_after_idat.png"
    after_idat.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(b"\0\0"))
        + _chunk(b"tRNS", b"\0\0")
        + _chunk(b"IEND", b"")
    )
    before_palette = tmp_path / "trns_before_palette.png"
    before_palette.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 1, 3, 0, 0, 0))
        + _chunk(b"tRNS", b"\xff")
        + _chunk(b"PLTE", b"\0\0\0")
        + _chunk(b"IDAT", zlib.compress(b"\0\0"))
        + _chunk(b"IEND", b"")
    )

    after_fp, after_errors = png_decoded_pixel_fingerprint(
        after_idat, min_width=1, min_height=1
    )
    before_fp, before_errors = png_decoded_pixel_fingerprint(
        before_palette, min_width=1, min_height=1
    )

    assert not after_fp
    assert "png_pixel_fingerprint_transparency_after_idat" in after_errors
    assert not before_fp
    assert "png_pixel_fingerprint_transparency_before_palette" in before_errors
