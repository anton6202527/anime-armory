#!/usr/bin/env python3
"""Build compact five-frame contact sheets for animated camera references."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "infrastructure" / "r2" / "reference-assets.json"
CELL_SIZE = (220, 150)
FRAME_COUNT = 5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Directory containing the 23 animated WebPs")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def sampled_indices(frame_count: int, wanted: int = FRAME_COUNT) -> list[int]:
    if frame_count <= 1:
        return [0] * wanted
    return [round(index * (frame_count - 1) / (wanted - 1)) for index in range(wanted)]


def frame_at(image: Image.Image, index: int) -> Image.Image:
    image.seek(index)
    frame = image.convert("RGBA")
    background = Image.new("RGBA", frame.size, (31, 31, 31, 255))
    background.alpha_composite(frame)
    return background.convert("RGB")


def build_sheet(source: Path, destination: Path) -> None:
    with Image.open(source) as image:
        frame_total = int(getattr(image, "n_frames", 1) or 1)
        indices = sampled_indices(frame_total)
        sheet = Image.new("RGB", (CELL_SIZE[0] * FRAME_COUNT, CELL_SIZE[1] + 22), (31, 31, 31))
        draw = ImageDraw.Draw(sheet)
        for slot, frame_index in enumerate(indices):
            frame = ImageOps.contain(frame_at(image, frame_index), CELL_SIZE, Image.Resampling.LANCZOS)
            left = slot * CELL_SIZE[0] + (CELL_SIZE[0] - frame.width) // 2
            top = 22 + (CELL_SIZE[1] - frame.height) // 2
            sheet.paste(frame, (left, top))
            draw.text((slot * CELL_SIZE[0] + 8, 5), f"{slot + 1}/{FRAME_COUNT}", fill=(220, 220, 220))
            if slot < FRAME_COUNT - 1:
                draw.text(((slot + 1) * CELL_SIZE[0] - 13, 5), ">", fill=(78, 201, 176))
        destination.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(destination, format="JPEG", quality=82, optimize=True, progressive=True)


def main() -> None:
    args = parse_args()
    source_dir = args.source.expanduser().resolve()
    if not source_dir.is_dir():
        raise SystemExit(f"source directory not found: {source_dir}")
    config = json.loads(args.config.resolve().read_text(encoding="utf-8"))
    manifest_paths = [ROOT / value for value in config.get("manifest_paths", [])]
    if not manifest_paths:
        raise SystemExit("reference asset config has no manifest_paths")

    source_files = sorted(source_dir.glob("*.webp"), key=lambda path: path.name)
    if len(source_files) != 23:
        raise SystemExit(f"expected 23 camera WebPs, found {len(source_files)} in {source_dir}")

    canonical_dir = manifest_paths[0].parent
    canonical_outputs: list[Path] = []
    for source in source_files:
        destination = canonical_dir / "_contact" / f"{source.stem}.jpg"
        build_sheet(source, destination)
        canonical_outputs.append(destination)
        print(f"[camera-contact] {source.name} -> {destination.relative_to(ROOT)}")

    for manifest_path in manifest_paths[1:]:
        destination_dir = manifest_path.parent / "_contact"
        destination_dir.mkdir(parents=True, exist_ok=True)
        for source in canonical_outputs:
            shutil.copy2(source, destination_dir / source.name)

    print(f"[camera-contact] wrote {len(source_files)} sheets to each of {len(manifest_paths)} lines")


if __name__ == "__main__":
    main()
