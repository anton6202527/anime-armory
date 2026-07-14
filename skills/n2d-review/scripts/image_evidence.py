#!/usr/bin/env python3
"""Deterministic PNG evidence validation used by n2d-review.

File extensions, magic bytes and dimensions alone are not proof that an image
is decodable.  This validator checks the complete PNG chunk stream, CRCs,
required chunk order, zlib payload and scanline layout using only stdlib.  It
does not judge image quality; it only prevents arbitrary bytes or a forged
IHDR/IEND shell from being accepted as visual evidence.
"""
from __future__ import annotations

import os
import struct
import zlib
from pathlib import Path
from typing import Iterable, List, Tuple


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_PIXELS = 100_000_000
VALID_BIT_DEPTHS = {
    0: {1, 2, 4, 8, 16},
    2: {8, 16},
    3: {1, 2, 4, 8},
    4: {8, 16},
    6: {8, 16},
}
SAMPLES_PER_PIXEL = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
ADAM7 = (
    (0, 0, 8, 8),
    (4, 0, 8, 8),
    (0, 4, 4, 8),
    (2, 0, 4, 4),
    (0, 2, 2, 4),
    (1, 0, 2, 2),
    (0, 1, 1, 2),
)


def _ceil_div(value: int, divisor: int) -> int:
    return (value + divisor - 1) // divisor


def _pass_rows(
    width: int,
    height: int,
    bit_depth: int,
    color_type: int,
    interlace: int,
) -> List[Tuple[int, int]]:
    bits_per_pixel = SAMPLES_PER_PIXEL[color_type] * bit_depth
    if interlace == 0:
        return [(_ceil_div(width * bits_per_pixel, 8), height)]
    rows: List[Tuple[int, int]] = []
    for x0, y0, dx, dy in ADAM7:
        pass_width = _ceil_div(width - x0, dx) if width > x0 else 0
        pass_height = _ceil_div(height - y0, dy) if height > y0 else 0
        if pass_width and pass_height:
            rows.append((_ceil_div(pass_width * bits_per_pixel, 8), pass_height))
    return rows


class _ScanlineValidator:
    def __init__(self, rows: Iterable[Tuple[int, int]]) -> None:
        self._passes = list(rows)
        self._pass_index = 0
        self._payload_size = 0
        self._rows_left = 0
        self._position = 0
        self.errors: List[str] = []
        self._advance_pass()

    def _advance_pass(self) -> None:
        while self._pass_index < len(self._passes):
            self._payload_size, self._rows_left = self._passes[self._pass_index]
            self._pass_index += 1
            if self._rows_left > 0:
                return
        self._payload_size = 0
        self._rows_left = 0

    @property
    def complete(self) -> bool:
        return self._rows_left == 0 and self._pass_index >= len(self._passes) and self._position == 0

    def feed(self, raw: bytes) -> None:
        offset = 0
        while offset < len(raw):
            if self._rows_left == 0:
                self.errors.append("png_scanline_data_extra")
                return
            if self._position == 0:
                if raw[offset] > 4:
                    self.errors.append("png_filter_type_invalid")
                offset += 1
                self._position = 1
                if offset >= len(raw):
                    continue
            row_total = self._payload_size + 1
            take = min(row_total - self._position, len(raw) - offset)
            offset += take
            self._position += take
            if self._position == row_total:
                self._position = 0
                self._rows_left -= 1
                if self._rows_left == 0:
                    self._advance_pass()


def _decompression_errors(
    idat_chunks: Iterable[bytes],
    *,
    width: int,
    height: int,
    bit_depth: int,
    color_type: int,
    interlace: int,
) -> List[str]:
    validator = _ScanlineValidator(_pass_rows(width, height, bit_depth, color_type, interlace))
    stream = zlib.decompressobj()
    errors: List[str] = []
    try:
        for compressed in idat_chunks:
            pending = compressed
            while pending:
                decoded = stream.decompress(pending, 1024 * 1024)
                validator.feed(decoded)
                pending = stream.unconsumed_tail
                if not pending:
                    break
            if stream.unused_data:
                errors.append("png_zlib_trailing_stream")
                break
        validator.feed(stream.flush())
    except zlib.error:
        errors.append("png_idat_zlib_invalid")
    if not errors and not stream.eof:
        errors.append("png_idat_zlib_incomplete")
    if not validator.complete:
        errors.append("png_scanline_data_incomplete")
    errors.extend(validator.errors)
    return errors


def png_evidence_errors(
    path: str | os.PathLike[str],
    *,
    min_width: int = 512,
    min_height: int = 512,
) -> List[str]:
    """Return deterministic error codes; an empty list means structurally valid."""
    candidate = Path(path)
    try:
        file_size = candidate.stat().st_size
        if file_size > MAX_FILE_BYTES:
            return ["png_file_too_large"]
        fh = candidate.open("rb")
    except OSError:
        return ["png_unreadable"]

    errors: List[str] = []
    width = height = bit_depth = color_type = interlace = 0
    seen_ihdr = seen_plte = seen_idat = seen_iend = False
    idat_ended = False
    idat_chunks: List[bytes] = []
    chunk_index = 0
    with fh:
        if fh.read(8) != PNG_SIGNATURE:
            return ["not_valid_png_container"]
        while True:
            raw_length = fh.read(4)
            if not raw_length:
                break
            if len(raw_length) != 4:
                errors.append("png_chunk_truncated")
                break
            length = struct.unpack(">I", raw_length)[0]
            chunk_type = fh.read(4)
            payload = fh.read(length)
            raw_crc = fh.read(4)
            if len(chunk_type) != 4 or len(payload) != length or len(raw_crc) != 4:
                errors.append("png_chunk_truncated")
                break
            try:
                chunk_name = chunk_type.decode("ascii")
            except UnicodeDecodeError:
                chunk_name = "????"
                errors.append("png_chunk_type_invalid")
            expected_crc = zlib.crc32(chunk_type)
            expected_crc = zlib.crc32(payload, expected_crc) & 0xFFFFFFFF
            if struct.unpack(">I", raw_crc)[0] != expected_crc:
                errors.append(f"png_crc_mismatch:{chunk_name}")

            if chunk_index == 0 and chunk_type != b"IHDR":
                errors.append("png_ihdr_not_first")
            if chunk_type == b"IHDR":
                if seen_ihdr or length != 13:
                    errors.append("png_ihdr_invalid")
                else:
                    seen_ihdr = True
                    width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                        ">IIBBBBB", payload
                    )
                    if width <= 0 or height <= 0 or width * height > MAX_PIXELS:
                        errors.append("png_dimensions_invalid")
                    if color_type not in VALID_BIT_DEPTHS or bit_depth not in VALID_BIT_DEPTHS.get(color_type, set()):
                        errors.append("png_color_mode_invalid")
                    if compression != 0 or filter_method != 0 or interlace not in {0, 1}:
                        errors.append("png_ihdr_method_invalid")
            elif chunk_type == b"PLTE":
                if seen_idat or length == 0 or length % 3 or length > 768:
                    errors.append("png_plte_invalid")
                seen_plte = True
                if seen_idat:
                    idat_ended = True
            elif chunk_type == b"IDAT":
                if not seen_ihdr or idat_ended:
                    errors.append("png_idat_order_invalid")
                seen_idat = True
                idat_chunks.append(payload)
            elif chunk_type == b"IEND":
                if length != 0 or not seen_idat:
                    errors.append("png_iend_invalid")
                seen_iend = True
                if fh.read(1):
                    errors.append("png_trailing_bytes")
                break
            else:
                if seen_idat:
                    idat_ended = True
                if chunk_type and 65 <= chunk_type[0] <= 90:
                    errors.append(f"png_unknown_critical_chunk:{chunk_name}")
            chunk_index += 1

    if not seen_ihdr or not seen_idat or not seen_iend:
        errors.append("not_valid_png_container")
    if color_type == 3 and not seen_plte:
        errors.append("png_palette_missing")
    if seen_ihdr and (width < min_width or height < min_height):
        errors.append(f"png_dimensions_too_small={width}x{height}")
    if (
        seen_ihdr
        and seen_idat
        and color_type in VALID_BIT_DEPTHS
        and bit_depth in VALID_BIT_DEPTHS[color_type]
        and interlace in {0, 1}
    ):
        errors.extend(
            _decompression_errors(
                idat_chunks,
                width=width,
                height=height,
                bit_depth=bit_depth,
                color_type=color_type,
                interlace=interlace,
            )
        )
    return sorted(set(errors))
