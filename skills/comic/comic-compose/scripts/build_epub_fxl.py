#!/usr/bin/env python3
"""Build a real fixed-layout EPUB 3 from Comic page images."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
from html import escape
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from typing import Any, Mapping
from xml.etree import ElementTree


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def load(path: Path) -> dict[str, Any]:
    try: value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError): return {}
    return value if isinstance(value, dict) else {}


def atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        handle.flush(); os.fsync(handle.fileno())
    os.replace(tmp, path)
    try:
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(directory_fd)
        finally: os.close(directory_fd)
    except OSError:
        pass


def validate_attestation(reviewer: str, reason: str) -> None:
    if not reviewer.strip() or reviewer.startswith("delegate:") or not reason.strip():
        raise ValueError("accessible alt attestation requires named non-delegate reviewer and reason")


def page_progression(root: Path, chapter: str, manifest: Mapping[str, Any]) -> str:
    layout = load(root / "排版" / chapter / "layout.json")
    raw = str(layout.get("reading_direction") or manifest.get("reading_direction") or "").strip().lower()
    return "rtl" if raw in {"rtl", "right-to-left", "从右到左"} else "ltr"


@contextmanager
def accessible_lock(root: Path, chapter: str):
    path = root / "排版" / chapter / ".accessible_delivery.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try: yield
        finally: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


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


def _page_semantic(page: Mapping[str, Any], alt_map: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize legacy alt strings and the panel/dialogue semantic schema."""
    raw = alt_map.get(str(page["id"]))
    if raw is None: raw = alt_map.get(str(page["rel"]))
    if isinstance(raw, str): raw = {"alt": raw}
    if not isinstance(raw, Mapping):
        raise ValueError(f"missing text alternative: {page['id']}")
    alt = str(raw.get("alt") or "").strip()
    if not alt: raise ValueError(f"missing text alternative: {page['id']}")
    panels, seen = [], set()
    for index, value in enumerate(raw.get("panels") or [], 1):
        if not isinstance(value, Mapping): raise ValueError(f"{page['id']} panel {index} must be an object")
        panel_id = str(value.get("panel_id") or value.get("id") or "").strip()
        if not panel_id or panel_id in seen: raise ValueError(f"{page['id']} has missing/duplicate panel_id")
        seen.add(panel_id)
        dialogue = []
        for line_index, line in enumerate(value.get("dialogue") or [], 1):
            if not isinstance(line, Mapping): raise ValueError(f"{page['id']}/{panel_id} dialogue {line_index} must be an object")
            text = str(line.get("text") or "").strip()
            if not text: raise ValueError(f"{page['id']}/{panel_id} dialogue {line_index} has no text")
            speaker = str(line.get("speaker") or "").strip()
            dialogue.append({"speaker": speaker, "text": text})
        panels.append({
            "panel_id": panel_id,
            "description": str(value.get("description") or "").strip(),
            "dialogue": dialogue,
            "narration": [str(item).strip() for item in value.get("narration") or [] if str(item).strip()],
            "sfx": [str(item).strip() for item in value.get("sfx") or [] if str(item).strip()],
        })
    requested_order = [str(item) for item in raw.get("reading_order") or []]
    if requested_order:
        if len(requested_order) != len(set(requested_order)) or set(requested_order) != seen:
            raise ValueError(f"{page['id']} reading_order must contain every panel_id exactly once")
        by_id = {row["panel_id"]: row for row in panels}; panels = [by_id[item] for item in requested_order]
    return {"alt": alt, "long_description": str(raw.get("long_description") or "").strip(), "panels": panels}


def _semantic_markup(page: Mapping[str, Any]) -> tuple[str, dict[str, int]]:
    semantic = page["semantic"]
    parts = [f'<section id="transcript-{escape(str(page["id"]), quote=True)}" class="sr-only" aria-label="Page transcript">']
    if semantic["long_description"]:
        parts.append(f'<p class="long-description">{escape(semantic["long_description"])}</p>')
    parts.append('<ol class="panel-transcript">')
    dialogue_count = speaker_count = description_count = 0
    for panel in semantic["panels"]:
        panel_id = escape(panel["panel_id"], quote=True)
        parts.append(f'<li id="semantic-{panel_id}"><section aria-labelledby="heading-{panel_id}">')
        parts.append(f'<h2 id="heading-{panel_id}">Panel {escape(panel["panel_id"])}</h2>')
        if panel["description"]:
            parts.append(f'<p class="panel-description">{escape(panel["description"])}</p>'); description_count += 1
        for line in panel["dialogue"]:
            dialogue_count += 1; speaker = str(line["speaker"])
            if speaker:
                speaker_count += 1
                parts.append(f'<p class="dialogue"><span class="speaker">{escape(speaker)}:</span> {escape(line["text"])}</p>')
            else:
                parts.append(f'<p class="dialogue">{escape(line["text"])}</p>')
        for narration in panel["narration"]: parts.append(f'<p class="narration"><span class="label">Narration:</span> {escape(narration)}</p>')
        for sfx in panel["sfx"]: parts.append(f'<p class="sfx"><span class="label">SFX:</span> {escape(sfx)}</p>')
        parts.append('</section></li>')
    parts.append('</ol></section>')
    return "".join(parts), {"dialogue": dialogue_count, "speaker": speaker_count, "descriptions": description_count}


def _validate_epub(path: Path, expected_pages: int) -> dict[str, Any]:
    """Internal structural validation before promotion; not conformance certification."""
    try:
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None: raise ValueError("EPUB CRC validation failed")
            entries = archive.infolist()
            if not entries or entries[0].filename != "mimetype" or entries[0].compress_type != zipfile.ZIP_STORED:
                raise ValueError("EPUB mimetype must be the first uncompressed entry")
            if archive.read("mimetype") != b"application/epub+zip": raise ValueError("invalid EPUB mimetype")
            required = {"META-INF/container.xml", "EPUB/package.opf", "EPUB/nav.xhtml"}
            if not required.issubset(archive.namelist()): raise ValueError("EPUB is missing required package files")
            xml_entries = [name for name in archive.namelist() if name.endswith((".xml", ".opf", ".xhtml"))]
            for name in xml_entries: ElementTree.fromstring(archive.read(name))
            pages = [name for name in archive.namelist() if name.startswith("EPUB/pages/") and name.endswith(".xhtml")]
            images = [name for name in archive.namelist() if name.startswith("EPUB/images/")]
            if len(pages) != expected_pages or len(images) != expected_pages:
                raise ValueError("EPUB page/image count does not match export manifest")
    except (OSError, KeyError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        raise ValueError(f"invalid staged EPUB: {exc}") from exc
    return {"status": "pass", "validator": "comic_internal_epub_structure_v1", "pages": expected_pages}


def _zip_write(archive: zipfile.ZipFile, name: str, body: str | bytes, *, stored: bool = False) -> None:
    """Write deterministic ZIP members so unchanged inputs keep one hash."""
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, body.encode("utf-8") if isinstance(body, str) else body)


def build(
    root: Path,
    chapter: str,
    *,
    title: str,
    language: str,
    alt_map: Mapping[str, Any],
    output_path: Path | None = None,
    artifact_path: Path | None = None,
    manifest_output_path: Path | None = None,
    progression_direction: str = "",
) -> tuple[Path, list[dict[str, Any]]]:
    manifest_path = root / "排版" / chapter / "export_manifest.json"; manifest = load(manifest_path)
    pages = page_records(root, chapter, manifest)
    for page in pages: page["semantic"] = _page_semantic(page, alt_map)
    final_out = root / "排版" / chapter / "accessible" / f"{chapter}.epub"
    out = (output_path or final_out).resolve(); out.parent.mkdir(parents=True, exist_ok=True)
    artifact = (artifact_path or out).resolve()
    progression = progression_direction or page_progression(root, chapter, manifest)
    if progression not in {"ltr", "rtl"}: raise ValueError("page progression must be ltr or rtl")
    publication_fingerprint = hashlib.sha256(json.dumps({
        "title": title, "language": language, "page_progression_direction": progression,
        "pages": [{"id": page["id"], "rel": page["rel"], "sha256": sha(page["source"]), "semantic": page["semantic"]} for page in pages],
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    identifier = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, 'comic-epub:' + publication_fingerprint)}"
    candidate_modified = str(manifest.get("generated_at") or manifest.get("updated_at") or "")
    modified = candidate_modified if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", candidate_modified) else "2000-01-01T00:00:00Z"
    manifest_items, spine, nav, xhtml, images = [], [], [], {}, {}
    semantic_totals = {"panels": 0, "dialogue": 0, "speaker": 0, "descriptions": 0, "long_descriptions": 0}
    for page in pages:
        ext = page["source"].suffix.lower().replace(".jpeg", ".jpg")
        image_href = f"images/{page['id']}{ext}"; page_href = f"pages/{page['id']}.xhtml"
        media = mimetypes.types_map.get(ext, "image/png").replace("image/jpg", "image/jpeg")
        manifest_items += [f'<item id="{page["id"]}" href="{page_href}" media-type="application/xhtml+xml"/>', f'<item id="img_{page["id"]}" href="{image_href}" media-type="{media}"/>']
        spine.append(f'<itemref idref="{page["id"]}"/>'); nav.append(f'<li><a href="{page_href}">{escape(page["id"])}</a></li>')
        alt = escape(page["semantic"]["alt"], quote=True)
        transcript, counts = _semantic_markup(page)
        semantic_totals["panels"] += len(page["semantic"]["panels"])
        semantic_totals["dialogue"] += counts["dialogue"]; semantic_totals["speaker"] += counts["speaker"]
        semantic_totals["descriptions"] += counts["descriptions"]
        semantic_totals["long_descriptions"] += int(bool(page["semantic"]["long_description"]))
        xhtml[page_href] = f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>{escape(title)} {escape(page['id'])}</title><meta name="viewport" content="width={page['width']},height={page['height']}"/><style>html,body{{margin:0;padding:0;width:100%;height:100%;}}img{{width:100%;height:100%;object-fit:contain;}}.sr-only{{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:normal;border:0;}}</style></head><body epub:type="bodymatter" xmlns:epub="http://www.idpf.org/2007/ops"><img src="../{image_href}" alt="{alt}" aria-describedby="transcript-{escape(page['id'], quote=True)}"/>{transcript}</body></html>'''
        images[image_href] = page["source"].read_bytes()
    nav_doc = f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>{escape(title)}</title></head><body><nav epub:type="toc" id="toc"><ol>{''.join(nav)}</ol></nav><nav epub:type="landmarks"><ol><li><a epub:type="bodymatter" href="pages/page_001.xhtml">正文</a></li></ol></nav></body></html>'''
    extra_features = '<meta property="schema:accessibilityFeature">longDescription</meta><meta property="schema:accessibilityFeature">structuralNavigation</meta>' if semantic_totals["panels"] or semantic_totals["long_descriptions"] else ''
    opf = f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id" prefix="schema: http://schema.org/ rendition: http://www.idpf.org/vocab/rendition/#"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="pub-id">{identifier}</dc:identifier><dc:title>{escape(title)}</dc:title><dc:language>{escape(language)}</dc:language><meta property="dcterms:modified">{modified}</meta><meta property="rendition:layout">pre-paginated</meta><meta property="schema:accessMode">visual</meta><meta property="schema:accessMode">textual</meta><meta property="schema:accessModeSufficient">visual,textual</meta><meta property="schema:accessibilityFeature">alternativeText</meta><meta property="schema:accessibilityFeature">readingOrder</meta>{extra_features}<meta property="schema:accessibilityHazard">none</meta><meta property="schema:accessibilitySummary">Page images include reviewed alternatives and an ordered semantic transcript when supplied.</meta></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>{''.join(manifest_items)}</manifest><spine page-progression-direction="{progression}">{''.join(spine)}</spine></package>'''
    container = '''<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'''
    pending = out.with_name(f".{out.name}.pending.{os.getpid()}")
    with zipfile.ZipFile(pending, "w") as archive:
        _zip_write(archive, "mimetype", "application/epub+zip", stored=True)
        _zip_write(archive, "META-INF/container.xml", container)
        _zip_write(archive, "EPUB/package.opf", opf)
        _zip_write(archive, "EPUB/nav.xhtml", nav_doc)
        for href, body in xhtml.items(): _zip_write(archive, f"EPUB/{href}", body)
        for href, body in images.items(): _zip_write(archive, f"EPUB/{href}", body)
    internal_validation = _validate_epub(pending, len(pages)); os.replace(pending, out)
    document = {"format": "epub", "path": str(artifact.relative_to(root)), "sha256": sha(out), "page_progression_direction": progression}
    documents = [row for row in manifest.get("documents") or [] if not (isinstance(row, Mapping) and str(row.get("format") or "").lower() == "epub")]
    document["internal_validation"] = internal_validation
    document["publication_input_sha256"] = publication_fingerprint
    document["semantic_transcript_sha256"] = hashlib.sha256(json.dumps([page["semantic"] for page in pages], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    document["semantic_coverage"] = semantic_totals
    manifest["documents"] = documents + [document]; atomic(manifest_output_path or manifest_path, manifest)
    return out, pages


def external_validation(epub: Path) -> dict[str, Any]:
    results = {}
    for tool in ("epubcheck", "ace"):
        binary = shutil.which(tool)
        if not binary: results[tool] = {"status": "unavailable"}; continue
        try:
            proc = subprocess.run([binary, str(epub)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            results[tool] = {"status": "pass" if proc.returncode == 0 else "fail", "returncode": proc.returncode, "output": ((proc.stdout or "") + (proc.stderr or ""))[-4000:]}
        except OSError as exc:
            results[tool] = {"status": "error", "error": str(exc)}
    return results


def write_contract(
    root: Path,
    chapter: str,
    epub: Path,
    pages: list[Mapping[str, Any]],
    *,
    title: str,
    language: str,
    reviewer: str,
    reason: str,
    artifact_path: Path | None = None,
    output_path: Path | None = None,
    progression_direction: str = "ltr",
) -> Path:
    validate_attestation(reviewer, reason)
    path = output_path or root / "排版" / chapter / "accessible_digital_contract.json"
    artifact = (artifact_path or epub).resolve()
    semantics = [dict(page.get("semantic") or {}) for page in pages]
    panel_count = sum(len(item.get("panels") or []) for item in semantics)
    dialogue = [line for item in semantics for panel in item.get("panels") or [] for line in panel.get("dialogue") or []]
    descriptions = sum(bool(item.get("long_description")) for item in semantics) + sum(bool(panel.get("description")) for item in semantics for panel in item.get("panels") or [])
    payload = {
        "schema_version": 2, "kind": "comic_accessible_digital_contract", "chapter": chapter,
        "artifact": {"path": str(artifact.relative_to(root)), "sha256": sha(epub)},
        "rendering": {"rendition_layout": "pre-paginated", "page_progression_direction": progression_direction}, "reading_order": [page["id"] for page in pages],
        "text_alternatives": {"coverage": 1.0, "missing": [], "reviewer": reviewer, "reviewed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "reason": reason},
        "semantic_transcript": {
            "sha256": hashlib.sha256(json.dumps(semantics, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
            "pages": len(pages), "panels": panel_count, "dialogue_lines": len(dialogue),
            "speaker_attribution_coverage": (sum(bool(line.get("speaker")) for line in dialogue) / len(dialogue)) if dialogue else 1.0,
            "extended_descriptions": descriptions,
            "programmatic_order": [panel["panel_id"] for item in semantics for panel in item.get("panels") or []],
        },
        "navigation": {"toc": True, "landmarks": ["bodymatter"]},
        "accessibility_metadata": {"title": title, "language": language, "access_modes": ["visual", "textual"], "access_mode_sufficient": [["visual", "textual"]], "accessibility_features": ["alternativeText", "readingOrder", "longDescription", "structuralNavigation"] if panel_count or descriptions else ["alternativeText", "readingOrder"], "accessibility_hazards": ["none"], "accessibility_summary": "逐页图像含经人工复核的替代文本；提供时同时含按视觉顺序排列的分格、对白、叙述与音效语义稿。"},
        "provenance": {"formal_baseline": {"standard": "EPUB Accessibility 1.1", "url": "https://www.w3.org/TR/epub-a11y-11/"}, "candidate_tracking": {"standard": "EPUB Accessibility 1.2 Candidate Recommendation", "url": "https://www.w3.org/TR/2026/CR-epub-a11y-12-20260721/", "not_claimed_as_formal_baseline": True}, "fixed_layout_guidance": "https://www.w3.org/TR/epub-fxl-a11y/", "verified_on": "2026-08-26"},
        "assurance": {"level": "workflow_readiness_human_attested", "not_conformance_certification": True},
        "external_validation": external_validation(epub),
    }
    atomic(path, payload); return path


def _transaction_paths(root: Path, chapter: str) -> tuple[Path, Path]:
    chapter_dir = root / "排版" / chapter
    return chapter_dir, chapter_dir / ".accessible_promotion.json"


def _safe_transaction_path(root: Path, raw: str) -> Path:
    if not str(raw or "").strip(): raise ValueError("accessible transaction path is empty")
    path = (root / raw).resolve()
    try: path.relative_to(root.resolve())
    except ValueError as exc: raise ValueError("accessible transaction path escaped project root") from exc
    if path == root.resolve(): raise ValueError("accessible transaction path cannot be project root")
    return path


def _cleanup_accessible_transaction(root: Path, journal: Mapping[str, Any], journal_path: Path) -> None:
    for row in journal.get("entries") or []:
        if not isinstance(row, Mapping): continue
        backup = _safe_transaction_path(root, str(row.get("backup") or ""))
        if backup.is_file(): backup.unlink()
    backup_dir = _safe_transaction_path(root, str(journal.get("backup_dir") or ""))
    stage_dir = _safe_transaction_path(root, str(journal.get("stage_dir") or ""))
    if backup_dir.parent.name != ".accessible_backups" or not stage_dir.name.startswith(".accessible_staging_"):
        raise ValueError("accessible cleanup paths do not match transaction-owned directories")
    for folder in (backup_dir, stage_dir):
        if folder.is_dir(): shutil.rmtree(folder)
    journal_path.unlink(missing_ok=True)


def recover_accessible_promotion(root: Path, chapter: str) -> bool:
    """Commit cleanup or CAS-safe rollback after an interrupted group promotion."""
    _chapter_dir, journal_path = _transaction_paths(root, chapter)
    journal = load(journal_path)
    if not journal:
        return False
    if journal.get("kind") != "comic_accessible_delivery_transaction":
        raise ValueError("unknown accessible promotion journal")
    entries = [row for row in journal.get("entries") or [] if isinstance(row, Mapping)]
    if not entries: raise ValueError("accessible promotion journal has no entries")
    all_promoted = all(
        sha(_safe_transaction_path(root, str(row.get("target") or ""))) == str(row.get("expected_sha256") or "")
        for row in entries
    )
    if all_promoted:
        _cleanup_accessible_transaction(root, journal, journal_path)
        return True
    conflicts = []
    for row in reversed(entries):
        target = _safe_transaction_path(root, str(row.get("target") or ""))
        backup = _safe_transaction_path(root, str(row.get("backup") or ""))
        expected = str(row.get("expected_sha256") or "")
        old = str(row.get("old_sha256") or "")
        current = sha(target)
        if current and current not in {expected, old}:
            conflicts.append(str(row.get("target") or "")); continue
        if current == expected:
            target.unlink()
        if backup.is_file():
            target.parent.mkdir(parents=True, exist_ok=True); os.replace(backup, target)
        elif not old:
            target.unlink(missing_ok=True)
    if conflicts:
        raise ValueError("accessible recovery CAS conflict; preserved newer files: " + ",".join(conflicts))
    _cleanup_accessible_transaction(root, journal, journal_path)
    return True


def _promote_accessible_group(root: Path, chapter: str, stage_dir: Path, entries: list[tuple[Path, Path]]) -> None:
    chapter_dir, journal_path = _transaction_paths(root, chapter)
    transaction_id = hashlib.sha256("|".join(sha(source) for source, _target in entries).encode("utf-8")).hexdigest()[:20]
    backup_dir = chapter_dir / ".accessible_backups" / transaction_id
    backup_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, (source, target) in enumerate(entries):
        rows.append({
            "source": str(source.relative_to(root)), "target": str(target.relative_to(root)),
            "backup": str((backup_dir / f"{index:02d}_{target.name}").relative_to(root)),
            "old_sha256": sha(target), "expected_sha256": sha(source),
        })
    journal: dict[str, Any] = {
        "schema_version": 1, "kind": "comic_accessible_delivery_transaction", "status": "prepared",
        "transaction_id": transaction_id, "stage_dir": str(stage_dir.relative_to(root)),
        "backup_dir": str(backup_dir.relative_to(root)), "entries": rows, "promoted": [],
    }
    atomic(journal_path, journal)
    try:
        for row in rows:
            source = _safe_transaction_path(root, row["source"]); target = _safe_transaction_path(root, row["target"])
            backup = _safe_transaction_path(root, row["backup"]); target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_file(): os.replace(target, backup)
            os.replace(source, target)
            if sha(target) != row["expected_sha256"]: raise ValueError(f"promoted SHA mismatch: {row['target']}")
            journal["promoted"].append(row["target"]); atomic(journal_path, journal)
        journal["status"] = "committed"; atomic(journal_path, journal)
        _cleanup_accessible_transaction(root, journal, journal_path)
    except BaseException:
        recover_accessible_promotion(root, chapter)
        raise


def build_delivery_transaction(
    root: Path,
    chapter: str,
    *,
    title: str,
    language: str,
    alt_map: Mapping[str, Any],
    reviewer: str,
    reason: str,
) -> tuple[Path, list[dict[str, Any]], Path]:
    """Stage EPUB + contract + manifest, then switch the manifest last."""
    validate_attestation(reviewer, reason)
    chapter_dir, _journal_path = _transaction_paths(root, chapter)
    with accessible_lock(root, chapter):
        recover_accessible_promotion(root, chapter)
        stage_dir = Path(tempfile.mkdtemp(prefix=".accessible_staging_", dir=str(chapter_dir)))
        final_epub = chapter_dir / "accessible" / f"{chapter}.epub"
        final_contract = chapter_dir / "accessible_digital_contract.json"
        final_manifest = chapter_dir / "export_manifest.json"
        staged_epub = stage_dir / f"{chapter}.epub"
        staged_contract = stage_dir / "accessible_digital_contract.json"
        staged_manifest = stage_dir / "export_manifest.json"
        progression = page_progression(root, chapter, load(final_manifest))
        try:
            epub, pages = build(
                root, chapter, title=title, language=language, alt_map=alt_map,
                output_path=staged_epub, artifact_path=final_epub,
                manifest_output_path=staged_manifest, progression_direction=progression,
            )
            contract = write_contract(
                root, chapter, epub, pages, title=title, language=language,
                reviewer=reviewer, reason=reason, artifact_path=final_epub,
                output_path=staged_contract, progression_direction=progression,
            )
            staged_manifest_payload = load(staged_manifest)
            document = next((row for row in staged_manifest_payload.get("documents") or [] if isinstance(row, Mapping) and row.get("format") == "epub"), {})
            if document.get("sha256") != sha(staged_epub) or load(staged_contract).get("artifact", {}).get("sha256") != sha(staged_epub):
                raise ValueError("staged EPUB/manifest/contract SHA binding mismatch")
            _promote_accessible_group(root, chapter, stage_dir, [
                (staged_epub, final_epub),
                (staged_contract, final_contract),
                (staged_manifest, final_manifest),
            ])
            return final_epub, pages, final_contract
        except BaseException:
            if stage_dir.is_dir(): shutil.rmtree(stage_dir)
            raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("project_root"); parser.add_argument("--chapter", default="第1话"); parser.add_argument("--title", default=""); parser.add_argument("--language", default="zh-Hans"); parser.add_argument("--alt-json", required=True); parser.add_argument("--reviewer", required=True); parser.add_argument("--reason", required=True); parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv); root = Path(args.project_root).expanduser().resolve(); alt = load(Path(args.alt_json)); title = args.title or f"{root.name} {args.chapter}"
    try: epub, pages, contract = build_delivery_transaction(root, args.chapter, title=title, language=args.language, alt_map=alt, reviewer=args.reviewer, reason=args.reason)
    except ValueError as exc: print(f"[err] {exc}"); return 2
    result = {"epub": str(epub), "sha256": sha(epub), "contract": str(contract), "pages": len(pages)}; print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"epub={epub} pages={len(pages)}"); return 0


if __name__ == "__main__": raise SystemExit(main())
