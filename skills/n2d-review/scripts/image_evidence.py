#!/usr/bin/env python3
"""Deterministic PNG evidence validation used by n2d-review.

File extensions, magic bytes and dimensions alone are not proof that an image
is decodable.  This validator checks the complete PNG chunk stream, CRCs,
required chunk order, zlib payload and scanline layout using only stdlib.  It
does not judge image quality; it only prevents arbitrary bytes or a forged
IHDR/IEND shell from being accepted as visual evidence.
"""
from __future__ import annotations

import hashlib
import os
import struct
import tempfile
import zlib
from pathlib import Path
from typing import BinaryIO, Dict, Iterable, Iterator, List, Mapping, Sequence, Tuple


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
PNG_DECODED_PIXEL_FINGERPRINT_KIND = "sha256:n2d-canonical-rgba16be-v1"


class _PixelFingerprintError(ValueError):
    """Internal control flow carrying one stable, user-facing error code."""


def _fingerprint_error(code: str) -> _PixelFingerprintError:
    return _PixelFingerprintError(code)


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


def _pixel_chunks(
    path: Path,
) -> Tuple[Dict[str, int], List[bytes], bytes, bytes, List[str]]:
    """Read the pixel-relevant chunks after the structural validator passed."""
    info: Dict[str, int] = {}
    idat: List[bytes] = []
    palette = b""
    transparency = b""
    seen_plte = False
    seen_trns = False
    seen_idat = False
    errors: List[str] = []
    try:
        with path.open("rb") as fh:
            if fh.read(8) != PNG_SIGNATURE:
                return info, idat, palette, transparency, ["not_valid_png_container"]
            while True:
                raw_length = fh.read(4)
                if not raw_length:
                    break
                if len(raw_length) != 4:
                    return info, idat, palette, transparency, ["png_chunk_truncated"]
                length = struct.unpack(">I", raw_length)[0]
                kind = fh.read(4)
                payload = fh.read(length)
                crc = fh.read(4)
                if len(kind) != 4 or len(payload) != length or len(crc) != 4:
                    return info, idat, palette, transparency, ["png_chunk_truncated"]
                if kind == b"IHDR" and len(payload) == 13:
                    width, height, bit_depth, color_type, _compression, _filter, interlace = struct.unpack(
                        ">IIBBBBB", payload
                    )
                    info = {
                        "width": width,
                        "height": height,
                        "bit_depth": bit_depth,
                        "color_type": color_type,
                        "interlace": interlace,
                    }
                elif kind == b"PLTE":
                    if seen_plte:
                        errors.append("png_pixel_fingerprint_palette_duplicate")
                    seen_plte = True
                    palette = payload
                elif kind == b"tRNS":
                    if seen_trns:
                        errors.append("png_pixel_fingerprint_transparency_duplicate")
                    if seen_idat:
                        errors.append("png_pixel_fingerprint_transparency_after_idat")
                    if info.get("color_type") == 3 and not seen_plte:
                        errors.append("png_pixel_fingerprint_transparency_before_palette")
                    if not payload:
                        errors.append("png_pixel_fingerprint_transparency_invalid")
                    seen_trns = True
                    transparency = payload
                elif kind == b"IDAT":
                    seen_idat = True
                    idat.append(payload)
                elif kind == b"IEND":
                    break
    except OSError:
        errors.append("png_unreadable")
    return info, idat, palette, transparency, sorted(set(errors))


def _validate_pixel_chunks(
    info: Mapping[str, int],
    palette: bytes,
    transparency: bytes,
) -> List[str]:
    """Validate PLTE/tRNS semantics needed for deterministic RGBA decoding."""
    errors: List[str] = []
    color_type = info.get("color_type", -1)
    bit_depth = info.get("bit_depth", 0)
    palette_entries = len(palette) // 3
    if palette and (len(palette) % 3 or not 1 <= palette_entries <= 256):
        errors.append("png_pixel_fingerprint_palette_invalid")
    if color_type in {0, 4} and palette:
        errors.append("png_pixel_fingerprint_palette_forbidden_for_grayscale")
    if color_type == 3:
        if not palette:
            errors.append("png_palette_missing")
        elif palette_entries > (1 << bit_depth):
            errors.append("png_pixel_fingerprint_palette_exceeds_bit_depth")
    if transparency:
        if color_type == 0:
            if len(transparency) != 2:
                errors.append("png_pixel_fingerprint_transparency_invalid")
            elif struct.unpack(">H", transparency)[0] >= (1 << bit_depth):
                errors.append("png_pixel_fingerprint_transparency_sample_out_of_range")
        elif color_type == 2:
            if len(transparency) != 6:
                errors.append("png_pixel_fingerprint_transparency_invalid")
            elif any(value >= (1 << bit_depth) for value in struct.unpack(">HHH", transparency)):
                errors.append("png_pixel_fingerprint_transparency_sample_out_of_range")
        elif color_type == 3:
            if not palette or len(transparency) > palette_entries:
                errors.append("png_pixel_fingerprint_transparency_invalid")
        else:
            errors.append("png_pixel_fingerprint_transparency_forbidden_for_alpha_mode")
    return sorted(set(errors))


def _iter_decompressed(idat_chunks: Sequence[bytes]) -> Iterator[bytes]:
    stream = zlib.decompressobj()
    for compressed in idat_chunks:
        pending = compressed
        while pending:
            decoded = stream.decompress(pending, 1024 * 1024)
            if decoded:
                yield decoded
            pending = stream.unconsumed_tail
        if stream.unused_data:
            raise _fingerprint_error("png_zlib_trailing_stream")
    tail = stream.flush()
    if tail:
        yield tail
    if not stream.eof:
        raise _fingerprint_error("png_idat_zlib_incomplete")


class _DecodedReader:
    """Small bounded buffer over the streaming IDAT decompressor."""

    def __init__(self, chunks: Iterator[bytes]) -> None:
        self._chunks = chunks
        self._buffer = bytearray()
        self._offset = 0
        self._ended = False

    def _compact(self) -> None:
        if self._offset:
            del self._buffer[: self._offset]
            self._offset = 0

    def read_exact(self, size: int) -> bytes:
        if size < 0:
            raise _fingerprint_error("png_pixel_fingerprint_decode_failed")
        while len(self._buffer) - self._offset < size and not self._ended:
            try:
                self._buffer.extend(next(self._chunks))
            except StopIteration:
                self._ended = True
        if len(self._buffer) - self._offset < size:
            raise _fingerprint_error("png_pixel_fingerprint_scanline_incomplete")
        end = self._offset + size
        value = bytes(self._buffer[self._offset:end])
        self._offset = end
        if self._offset > 1024 * 1024:
            self._compact()
        return value

    def require_eof(self) -> None:
        while not self._ended:
            try:
                self._buffer.extend(next(self._chunks))
            except StopIteration:
                self._ended = True
        if len(self._buffer) != self._offset:
            raise _fingerprint_error("png_pixel_fingerprint_scanline_extra")


def _paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    dl = abs(estimate - left)
    du = abs(estimate - up)
    dul = abs(estimate - upper_left)
    if dl <= du and dl <= dul:
        return left
    return up if du <= dul else upper_left


def _unfilter_row(filter_type: int, raw: bytes, previous: bytes, bpp: int) -> bytes:
    if filter_type not in {0, 1, 2, 3, 4}:
        raise _fingerprint_error("png_filter_type_invalid")
    if filter_type == 0:
        return raw
    out = bytearray(len(raw))
    for index, value in enumerate(raw):
        left = out[index - bpp] if index >= bpp else 0
        up = previous[index] if previous else 0
        upper_left = previous[index - bpp] if previous and index >= bpp else 0
        if filter_type == 1:
            predictor = left
        elif filter_type == 2:
            predictor = up
        elif filter_type == 3:
            predictor = (left + up) // 2
        else:
            predictor = _paeth(left, up, upper_left)
        out[index] = (value + predictor) & 0xFF
    return bytes(out)


def _row_samples(row: bytes, bit_depth: int, sample_count: int) -> List[int]:
    if bit_depth == 8:
        if len(row) < sample_count:
            raise _fingerprint_error("png_pixel_fingerprint_scanline_incomplete")
        return list(row[:sample_count])
    if bit_depth == 16:
        required = sample_count * 2
        if len(row) < required:
            raise _fingerprint_error("png_pixel_fingerprint_scanline_incomplete")
        return list(struct.unpack(f">{sample_count}H", row[:required]))
    mask = (1 << bit_depth) - 1
    samples: List[int] = []
    for index in range(sample_count):
        bit_offset = index * bit_depth
        byte_index = bit_offset // 8
        shift = 8 - bit_depth - (bit_offset % 8)
        if byte_index >= len(row) or shift < 0:
            raise _fingerprint_error("png_pixel_fingerprint_scanline_incomplete")
        samples.append((row[byte_index] >> shift) & mask)
    return samples


def _scale_16(value: int, bit_depth: int) -> int:
    return (value * 65535) // ((1 << bit_depth) - 1)


def _canonical_row(
    row: bytes,
    *,
    pixel_count: int,
    bit_depth: int,
    color_type: int,
    palette: bytes,
    transparency: bytes,
) -> bytes:
    channels = SAMPLES_PER_PIXEL[color_type]
    # The production path is overwhelmingly 8-bit RGB/RGBA.  Strided
    # bytearray assignments stay in C and avoid a Python struct.pack loop for
    # every pixel while preserving the exact same RGBA16 comparison domain.
    if not transparency and bit_depth in {8, 16} and color_type != 3:
        out = bytearray(pixel_count * 8)
        opaque = b"\xff" * pixel_count
        if bit_depth == 8:
            if color_type == 0:
                gray = row[:pixel_count]
                for offset in (0, 2, 4):
                    out[offset::8] = gray
                    out[offset + 1::8] = gray
                out[6::8] = opaque
                out[7::8] = opaque
            elif color_type == 2:
                for target, source in ((0, 0), (2, 1), (4, 2)):
                    channel = row[source : pixel_count * 3 : 3]
                    out[target::8] = channel
                    out[target + 1::8] = channel
                out[6::8] = opaque
                out[7::8] = opaque
            elif color_type == 4:
                gray = row[0 : pixel_count * 2 : 2]
                alpha = row[1 : pixel_count * 2 : 2]
                for offset in (0, 2, 4):
                    out[offset::8] = gray
                    out[offset + 1::8] = gray
                out[6::8] = alpha
                out[7::8] = alpha
            else:
                for target, source in ((0, 0), (2, 1), (4, 2), (6, 3)):
                    channel = row[source : pixel_count * 4 : 4]
                    out[target::8] = channel
                    out[target + 1::8] = channel
            return bytes(out)
        if color_type == 6:
            return row[: pixel_count * 8]
        if color_type == 0:
            for offset in (0, 2, 4):
                out[offset::8] = row[0 : pixel_count * 2 : 2]
                out[offset + 1::8] = row[1 : pixel_count * 2 : 2]
            out[6::8] = opaque
            out[7::8] = opaque
        elif color_type == 2:
            for target, source in ((0, 0), (2, 2), (4, 4)):
                out[target::8] = row[source : pixel_count * 6 : 6]
                out[target + 1::8] = row[source + 1 : pixel_count * 6 : 6]
            out[6::8] = opaque
            out[7::8] = opaque
        else:
            for offset in (0, 2, 4):
                out[offset::8] = row[0 : pixel_count * 4 : 4]
                out[offset + 1::8] = row[1 : pixel_count * 4 : 4]
            out[6::8] = row[2 : pixel_count * 4 : 4]
            out[7::8] = row[3 : pixel_count * 4 : 4]
        return bytes(out)
    samples = _row_samples(row, bit_depth, pixel_count * channels)
    palette_entries = [
        (palette[index] * 257, palette[index + 1] * 257, palette[index + 2] * 257)
        for index in range(0, len(palette), 3)
    ]
    palette_alpha = list(transparency) if color_type == 3 else []
    transparent_gray = struct.unpack(">H", transparency)[0] if color_type == 0 and transparency else None
    transparent_rgb = struct.unpack(">HHH", transparency) if color_type == 2 and transparency else None
    out = bytearray(pixel_count * 8)
    for pixel in range(pixel_count):
        offset = pixel * channels
        values = samples[offset : offset + channels]
        if color_type == 0:
            raw_gray = values[0]
            gray = _scale_16(raw_gray, bit_depth)
            rgba = (gray, gray, gray, 0 if raw_gray == transparent_gray else 65535)
        elif color_type == 2:
            raw_rgb = tuple(values)
            rgba = tuple(_scale_16(value, bit_depth) for value in raw_rgb) + (
                0 if raw_rgb == transparent_rgb else 65535,
            )
        elif color_type == 3:
            index = values[0]
            if index >= len(palette_entries):
                raise _fingerprint_error("png_pixel_fingerprint_palette_index_out_of_range")
            rgba = palette_entries[index] + (
                (palette_alpha[index] if index < len(palette_alpha) else 255) * 257,
            )
        elif color_type == 4:
            gray = _scale_16(values[0], bit_depth)
            rgba = (gray, gray, gray, _scale_16(values[1], bit_depth))
        else:
            rgba = tuple(_scale_16(value, bit_depth) for value in values)
        struct.pack_into(">HHHH", out, pixel * 8, *rgba)
    return bytes(out)


def _decoded_passes(
    reader: _DecodedReader,
    *,
    width: int,
    height: int,
    bit_depth: int,
    color_type: int,
    interlace: int,
    palette: bytes,
    transparency: bytes,
) -> Iterator[Tuple[int, int, int, int, int, bytes]]:
    """Yield x0/y0/dx/dy/pass-row-index/canonical RGBA16 rows."""
    passes = ((0, 0, 1, 1),) if interlace == 0 else ADAM7
    bits_per_pixel = SAMPLES_PER_PIXEL[color_type] * bit_depth
    filter_bpp = max(1, _ceil_div(bits_per_pixel, 8))
    for x0, y0, dx, dy in passes:
        pass_width = _ceil_div(width - x0, dx) if width > x0 else 0
        pass_height = _ceil_div(height - y0, dy) if height > y0 else 0
        if not pass_width or not pass_height:
            continue
        row_bytes = _ceil_div(pass_width * bits_per_pixel, 8)
        previous = b""
        for pass_row in range(pass_height):
            filter_type = reader.read_exact(1)[0]
            encoded = reader.read_exact(row_bytes)
            decoded = _unfilter_row(filter_type, encoded, previous, filter_bpp)
            previous = decoded
            yield (
                x0,
                y0,
                dx,
                dy,
                pass_row,
                _canonical_row(
                    decoded,
                    pixel_count=pass_width,
                    bit_depth=bit_depth,
                    color_type=color_type,
                    palette=palette,
                    transparency=transparency,
                ),
            )


def _fingerprint_noninterlaced(
    digest: "hashlib._Hash",
    rows: Iterator[Tuple[int, int, int, int, int, bytes]],
) -> None:
    for _x0, _y0, _dx, _dy, _pass_row, canonical in rows:
        digest.update(canonical)


def _fingerprint_adam7(
    digest: "hashlib._Hash",
    rows: Iterator[Tuple[int, int, int, int, int, bytes]],
    *,
    width: int,
    height: int,
) -> None:
    """Spool pass rows, then merge them into canonical final row-major order."""
    pass_files: Dict[Tuple[int, int, int, int], BinaryIO] = {}
    try:
        for x0, y0, dx, dy, _pass_row, canonical in rows:
            key = (x0, y0, dx, dy)
            handle = pass_files.get(key)
            if handle is None:
                handle = tempfile.TemporaryFile(mode="w+b")
                pass_files[key] = handle
            handle.write(canonical)
        for handle in pass_files.values():
            handle.flush()
        for y in range(height):
            final_row = bytearray(width * 8)
            pixels_written = 0
            for x0, y0, dx, dy in ADAM7:
                if y < y0 or (y - y0) % dy:
                    continue
                pass_width = _ceil_div(width - x0, dx) if width > x0 else 0
                pass_height = _ceil_div(height - y0, dy) if height > y0 else 0
                if not pass_width or not pass_height:
                    continue
                handle = pass_files.get((x0, y0, dx, dy))
                if handle is None:
                    raise _fingerprint_error("png_pixel_fingerprint_adam7_pass_missing")
                pass_row = (y - y0) // dy
                handle.seek(pass_row * pass_width * 8)
                canonical = handle.read(pass_width * 8)
                if len(canonical) != pass_width * 8:
                    raise _fingerprint_error("png_pixel_fingerprint_adam7_pass_incomplete")
                for index in range(pass_width):
                    x = x0 + index * dx
                    final_row[x * 8 : x * 8 + 8] = canonical[index * 8 : index * 8 + 8]
                    pixels_written += 1
            if pixels_written != width:
                raise _fingerprint_error("png_pixel_fingerprint_adam7_coverage_invalid")
            digest.update(final_row)
    except OSError as exc:
        raise _fingerprint_error("png_pixel_fingerprint_tempfile_error") from exc
    finally:
        for handle in pass_files.values():
            handle.close()


def png_decoded_pixel_fingerprint(
    path: str | os.PathLike[str],
    *,
    min_width: int = 512,
    min_height: int = 512,
) -> Tuple[str, List[str]]:
    """Return a compression/metadata-independent SHA-256 over decoded pixels.

    Pixels are normalized to row-major RGBA16 big-endian samples, so every
    legal PNG color type/bit depth and Adam7/non-interlaced encoding shares one
    comparison domain.  The empty fingerprint is always accompanied by at
    least one explicit error; callers must treat that result as a hard failure.
    """
    candidate = Path(path)
    structural_errors = png_evidence_errors(
        candidate,
        min_width=min_width,
        min_height=min_height,
    )
    if structural_errors:
        return "", structural_errors
    info, idat, palette, transparency, chunk_errors = _pixel_chunks(candidate)
    semantic_errors = chunk_errors + _validate_pixel_chunks(info, palette, transparency)
    if semantic_errors:
        return "", sorted(set(semantic_errors))
    try:
        width = info["width"]
        height = info["height"]
        bit_depth = info["bit_depth"]
        color_type = info["color_type"]
        interlace = info["interlace"]
        digest = hashlib.sha256()
        digest.update(PNG_DECODED_PIXEL_FINGERPRINT_KIND.encode("ascii") + b"\0")
        digest.update(struct.pack(">II", width, height))
        reader = _DecodedReader(_iter_decompressed(idat))
        rows = _decoded_passes(
            reader,
            width=width,
            height=height,
            bit_depth=bit_depth,
            color_type=color_type,
            interlace=interlace,
            palette=palette,
            transparency=transparency,
        )
        if interlace == 0:
            _fingerprint_noninterlaced(digest, rows)
        else:
            _fingerprint_adam7(digest, rows, width=width, height=height)
        reader.require_eof()
        return digest.hexdigest(), []
    except _PixelFingerprintError as exc:
        return "", [str(exc) or "png_pixel_fingerprint_decode_failed"]
    except (KeyError, MemoryError, OSError, struct.error, ValueError, zlib.error):
        return "", ["png_pixel_fingerprint_decode_failed"]
