#!/usr/bin/env python3
"""Shared utilities for parsing and summarizing consistency/gate findings."""
import glob
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

def finding_counts(data: Any) -> Tuple[int, int, List[str]]:
    """Return (block, warn, sample_messages) for consistency/gate findings payloads.

    Supports both current severity/dimension/message rows and older sev/dim/msg rows.
    """
    block = warn = 0
    summary = data.get("summary") if isinstance(data, dict) else None
    if isinstance(summary, dict):
        sev_data = summary.get("severity") or summary
        if isinstance(sev_data, dict):
            block = int(sev_data.get("block") or sev_data.get("total_block") or 0)
            warn = int(sev_data.get("warn") or sev_data.get("total_warn") or 0)

    rows = data.get("findings") if isinstance(data, dict) else None
    block_samples = []
    warn_samples = []
    if isinstance(rows, list):
        f_block = f_warn = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            sev = str(row.get("severity") or row.get("sev") or "").lower()
            if row.get("resolved") is True:
                continue
                
            msg = row.get("message") or row.get("msg")
            if not msg:
                dim = row.get("dimension") or row.get("dim") or ""
                loc = row.get("loc") or row.get("png") or row.get("char") or ""
                msg = f"{dim}: {loc}" if dim and loc else (dim or loc or "")
            
            if sev == "block":
                f_block += 1
                if msg and len(block_samples) < 3:
                    block_samples.append(str(msg))
            elif sev == "warn":
                f_warn += 1
                if msg and len(warn_samples) < 3:
                    warn_samples.append(str(msg))
                    
        # Use findings count if summary is missing or empty
        if block == 0 and warn == 0:
            block, warn = f_block, f_warn
            
    # Prioritize block samples
    samples = (block_samples + warn_samples)[:3]
    return block, warn, samples


def findings_status(root: str, ep: str, progress_mtime: float = 0) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Summarize active/stale findings for one episode.

    If progress_mtime is provided, findings files older than that are marked as stale.
    """
    active = {"block": 0, "warn": 0, "files": 0, "samples": []}
    stale = {"block": 0, "warn": 0, "files": 0}
    
    # We look for all findings files for this episode in the production data directory.
    # Note: caller should ensure 'ep' is normalized.
    search_dir = os.path.join(root, "生产数据")
    if not os.path.isdir(search_dir):
        return active, stale

    found_files = glob.glob(os.path.join(search_dir, f"*findings*{ep}.json"))
    # Sort files to ensure deterministic behavior (e.g. gate_findings before consistency)
    found_files.sort()

    all_block_samples = []
    all_warn_samples = []

    for path in found_files:
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        
        b, w, samples = finding_counts(data)
        if b <= 0 and w <= 0:
            continue
            
        bucket = stale if progress_mtime > 0 and os.path.getmtime(path) < progress_mtime else active
        bucket["block"] += b
        bucket["warn"] += w
        bucket["files"] += 1
        
        if bucket is active:
            # samples from finding_counts are already prioritized and limited to 3
            # We split them back to block/warn if we wanted perfect prioritization, 
            # but since finding_counts already returns 3 best ones, we just collect them.
            if b > 0:
                all_block_samples.extend(samples)
            else:
                all_warn_samples.extend(samples)
            
    if all_block_samples:
        active["samples"] = all_block_samples[:2]
    else:
        active["samples"] = all_warn_samples[:2]

    return active, stale


_REVIEW_DATE_RE = re.compile(r"生成时间[:：]\s*([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2})")


def review_report_status(root: str, ep: str, ref_mtime: float = 0) -> Optional[Dict[str, Any]]:
    """Locate the human QA report (`_质检_<ep>.md`, else whole-work `_质检_全片.md`) for one episode.

    Read-only existence/date/staleness — does NOT parse severity from the free-form
    markdown body (that comes from the deterministic findings/score JSON instead).
    Returns None when no report exists. `stale` mirrors findings_status: if ref_mtime
    is given and the report predates it, the products changed after the review.
    """
    candidates = [
        (os.path.join(root, f"_质检_{ep}.md"), "本集"),
        (os.path.join(root, "_质检_全片.md"), "全片"),
    ]
    for path, scope in candidates:
        if not os.path.isfile(path):
            continue
        mtime = os.path.getmtime(path)
        date = ""
        try:
            with open(path, encoding="utf-8") as fh:
                head = fh.read(2000)
            m = _REVIEW_DATE_RE.search(head)
            if m:
                date = m.group(1)
        except OSError:
            pass
        return {
            "name": os.path.basename(path),
            "scope": scope,
            "date": date,
            "mtime": mtime,
            "stale": bool(ref_mtime > 0 and mtime < ref_mtime),
        }
    return None


def score_status(root: str, ep: str) -> Optional[Dict[str, Any]]:
    """Read the deterministic score verdict (`生产数据/score_<ep>.json`) for one episode.

    Returns {total, threshold, status, mtime} or None. `status` is "pass"/"fail" as
    written by n2d-score; surfaces the verdict, not just whether score ran.
    """
    path = os.path.join(root, "生产数据", f"score_{ep}.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    return {
        "total": data.get("total_score"),
        "threshold": data.get("threshold"),
        "status": data.get("status"),
        "mtime": os.path.getmtime(path),
    }
