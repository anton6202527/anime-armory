#!/usr/bin/env python3
"""Build a real fixed-layout EPUB 3 from Comic page images."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import escape
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import shutil
import subprocess
import uuid
import zipfile
from typing import Any, Mapping


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def load(path: Path) -> dict[str, Any]:
    try: value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError): return {}
    return value if isinstance(value, dict) else {}


def atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); os.replace(tmp, path)


def page_records(root: Path, chapter: str, manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    source = manifest.get("pages") or manifest.get("rendered") or []
    for index, row in enumerate(source, 1):
        if not isinstance(row, Mapping) or not row.get("path"): continue
        path = root / str(row["path"])
        if not path.is_file() or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}: continue
        size = row.get("size") if isinstance(row.get("size"), Mapping) else {}
        width, height = int(size.get("width") or row.get("width") or 0), int(size.get("height") or row.get("height") or 0)
        if not width or not height:
            try:
                from PIL import Image
                with Image.open(path) as image: width, height = image.size
            except (ImportError, OSError): width, height = 1440, 2048
        rows.append({"id": f"page_{index:03d}", "source": path, "rel": str(path.relative_to(root)), "width": width, "height": height})
    if not rows: raise ValueError(f"{chapter} export manifest has no page images")
    return rows


def build(root: Path, chapter: str, *, title: str, language: str, alt_map: Mapping[str, Any]) -> tuple[Path, list[dict[str, Any]]]:
    manifest_path = root / "排版" / chapter / "export_manifest.json"; manifest = load(manifest_path)
    pages = page_records(root, chapter, manifest)
    missing = [page["id"] for page in pages if not str(alt_map.get(page["id"]) or alt_map.get(page["rel"]) or "").strip()]
    if missing: raise ValueError("missing text alternatives: " + ",".join(missing))
    out = root / "排版" / chapter / "accessible" / f"{chapter}.epub"; out.parent.mkdir(parents=True, exist_ok=True)
    identifier = f"urn:uuid:{uuid.uuid4()}"; modified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest_items, spine, nav, xhtml, images = [], [], [], {}, {}
    for page in pages:
        ext = page["source"].suffix.lower().replace(".jpeg", ".jpg")
        image_href = f"images/{page['id']}{ext}"; page_href = f"pages/{page['id']}.xhtml"
        media = mimetypes.types_map.get(ext, "image/png").replace("image/jpg", "image/jpeg")
        manifest_items += [f'<item id="{page["id"]}" href="{page_href}" media-type="application/xhtml+xml"/>', f'<item id="img_{page["id"]}" href="{image_href}" media-type="{media}"/>']
        spine.append(f'<itemref idref="{page["id"]}"/>'); nav.append(f'<li><a href="{page_href}">{escape(page["id"])}</a></li>')
        alt = escape(str(alt_map.get(page["id"]) or alt_map.get(page["rel"]) or ""), quote=True)
        xhtml[page_href] = f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>{escape(title)} {escape(page['id'])}</title><meta name="viewport" content="width={page['width']},height={page['height']}"/><style>html,body{{margin:0;padding:0;width:100%;height:100%;}}img{{width:100%;height:100%;object-fit:contain;}}</style></head><body epub:type="bodymatter" xmlns:epub="http://www.idpf.org/2007/ops"><img src="../{image_href}" alt="{alt}"/></body></html>'''
        images[image_href] = page["source"].read_bytes()
    nav_doc = f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>{escape(title)}</title></head><body><nav epub:type="toc" id="toc"><ol>{''.join(nav)}</ol></nav><nav epub:type="landmarks"><ol><li><a epub:type="bodymatter" href="pages/page_001.xhtml">正文</a></li></ol></nav></body></html>'''
    opf = f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id" prefix="schema: http://schema.org/ rendition: http://www.idpf.org/vocab/rendition/#"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="pub-id">{identifier}</dc:identifier><dc:title>{escape(title)}</dc:title><dc:language>{escape(language)}</dc:language><meta property="dcterms:modified">{modified}</meta><meta property="rendition:layout">pre-paginated</meta><meta property="schema:accessMode">visual</meta><meta property="schema:accessMode">textual</meta><meta property="schema:accessModeSufficient">textual</meta><meta property="schema:accessibilityFeature">alternativeText</meta><meta property="schema:accessibilityFeature">readingOrder</meta><meta property="schema:accessibilityHazard">none</meta><meta property="schema:accessibilitySummary">Page images include reviewed text alternatives.</meta></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>{''.join(manifest_items)}</manifest><spine>{''.join(spine)}</spine></package>'''
    container = '''<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'''
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", container, compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("EPUB/package.opf", opf, compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("EPUB/nav.xhtml", nav_doc, compress_type=zipfile.ZIP_DEFLATED)
        for href, body in xhtml.items(): archive.writestr(f"EPUB/{href}", body, compress_type=zipfile.ZIP_DEFLATED)
        for href, body in images.items(): archive.writestr(f"EPUB/{href}", body, compress_type=zipfile.ZIP_DEFLATED)
    document = {"format": "epub", "path": str(out.relative_to(root)), "sha256": sha(out)}
    documents = [row for row in manifest.get("documents") or [] if not (isinstance(row, Mapping) and str(row.get("format") or "").lower() == "epub")]
    manifest["documents"] = documents + [document]; atomic(manifest_path, manifest)
    return out, pages


def external_validation(epub: Path) -> dict[str, Any]:
    results = {}
    for tool in ("epubcheck", "ace"):
        binary = shutil.which(tool)
        if not binary: results[tool] = {"status": "unavailable"}; continue
        proc = subprocess.run([binary, str(epub)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        results[tool] = {"status": "pass" if proc.returncode == 0 else "fail", "returncode": proc.returncode, "output": ((proc.stdout or "") + (proc.stderr or ""))[-4000:]}
    return results


def write_contract(root: Path, chapter: str, epub: Path, pages: list[Mapping[str, Any]], *, title: str, language: str, reviewer: str, reason: str) -> Path:
    if not reviewer.strip() or reviewer.startswith("delegate:") or not reason.strip(): raise ValueError("accessible alt attestation requires named non-delegate reviewer and reason")
    path = root / "排版" / chapter / "accessible_digital_contract.json"
    payload = {
        "schema_version": 1, "kind": "comic_accessible_digital_contract", "chapter": chapter,
        "artifact": {"path": str(epub.relative_to(root)), "sha256": sha(epub)},
        "rendering": {"rendition_layout": "pre-paginated"}, "reading_order": [page["id"] for page in pages],
        "text_alternatives": {"coverage": 1.0, "missing": [], "reviewer": reviewer, "reviewed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "reason": reason},
        "navigation": {"toc": True, "landmarks": ["bodymatter"]},
        "accessibility_metadata": {"title": title, "language": language, "access_modes": ["visual", "textual"], "access_mode_sufficient": [["textual"], ["visual", "textual"]], "accessibility_features": ["alternativeText", "readingOrder"], "accessibility_hazards": ["none"], "accessibility_summary": "逐页图像含经人工复核的文本替代。"},
        "provenance": {"standard": "EPUB Accessibility 1.1", "url": "https://www.w3.org/TR/epub-a11y-11/", "fixed_layout_guidance": "https://www.w3.org/TR/epub-fxl-a11y/", "verified_on": "2026-08-25"},
        "assurance": {"level": "workflow_readiness_human_attested", "not_conformance_certification": True},
        "external_validation": external_validation(epub),
    }
    atomic(path, payload); return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("project_root"); parser.add_argument("--chapter", default="第1话"); parser.add_argument("--title", default=""); parser.add_argument("--language", default="zh-Hans"); parser.add_argument("--alt-json", required=True); parser.add_argument("--reviewer", required=True); parser.add_argument("--reason", required=True); parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv); root = Path(args.project_root).expanduser().resolve(); alt = load(Path(args.alt_json)); title = args.title or f"{root.name} {args.chapter}"
    try: epub, pages = build(root, args.chapter, title=title, language=args.language, alt_map=alt); contract = write_contract(root, args.chapter, epub, pages, title=title, language=args.language, reviewer=args.reviewer, reason=args.reason)
    except ValueError as exc: print(f"[err] {exc}"); return 2
    result = {"epub": str(epub), "sha256": sha(epub), "contract": str(contract), "pages": len(pages)}; print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"epub={epub} pages={len(pages)}"); return 0


if __name__ == "__main__": raise SystemExit(main())
