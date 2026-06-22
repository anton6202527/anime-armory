#!/usr/bin/env python3
"""Video VLM judgement reader for rendered-video consistency.

Heavy VLM calls are intentionally external. This checker consumes sidecar JSON
reports such as:

  生产数据/video_vlm_consistency_<ep>.json
  出视频/<ep>/video_vlm_consistency.json

Rows may use `verdict/severity/status`, or boolean fields like `match=false`.
"""
from __future__ import annotations

import os
from typing import Any, List, Mapping

from video_consistency_common import boolish_false, finding, load_first_json, rows_from, verdict_from


REPORT_RELS = (
    os.path.join("生产数据", "video_vlm_consistency_{ep}.json"),
    os.path.join("生产数据", "video_vlm_judgements_{ep}.json"),
    os.path.join("生产数据", "video_vlm_judgments_{ep}.json"),
    os.path.join("出视频", "{ep}", "video_vlm_consistency.json"),
    os.path.join("出视频", "{ep}", "vlm_consistency.json"),
    os.path.join("合成", "{ep}", "video_vlm_consistency.json"),
)


def _confidence(row: dict) -> float:
    for key in ("confidence", "score", "mismatch_confidence"):
        try:
            return float(row.get(key))
        except (TypeError, ValueError):
            continue
    return 1.0


def _message(row: dict) -> str:
    return str(
        row.get("message")
        or row.get("reason")
        or row.get("question")
        or row.get("check")
        or row.get("claim")
        or "视频 VLM 判题未通过"
    )


def _meta_value(data: Any, row: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if row.get(key) not in (None, "", [], {}):
            return row.get(key)
    if isinstance(data, Mapping):
        meta = data.get("judge") if isinstance(data.get("judge"), Mapping) else data
        for key in keys:
            if meta.get(key) not in (None, "", [], {}):
                return meta.get(key)
    return None


def _vote_disagreement(row: Mapping[str, Any]) -> float:
    votes = row.get("self_consistency_votes") or row.get("votes")
    if not isinstance(votes, list) or len(votes) < 3:
        return 0.0
    verdicts = [str(v.get("verdict") if isinstance(v, Mapping) else v).strip().lower() for v in votes]
    verdicts = [v for v in verdicts if v]
    if not verdicts:
        return 0.0
    majority = max(verdicts.count(v) for v in set(verdicts))
    return 1.0 - majority / len(verdicts)


def _schema_findings(data: Any, rel: str, rows: List[dict]) -> List[dict]:
    findings: List[dict] = []
    if not rows:
        return findings
    required = (
        ("judge_model", "VLM 判题报告缺 judge_model，后续无法比较 judge 漂移或复现分数。"),
        ("rubric_version", "VLM 判题报告缺 rubric_version，无法确认判题标准是否同版。"),
        ("frame_sample_manifest", "VLM 判题报告缺 frame_sample_manifest，无法复核抽帧覆盖。"),
        ("question_chain", "VLM 判题报告缺 question_chain，未记录多步问题链/CoQ 证据。"),
    )
    for key, message in required:
        if _meta_value(data, {}, key) in (None, "", [], {}):
            findings.append(finding("warn", message, stage="review", artifacts=(rel,)))
    for row in rows:
        shot = row.get("clip") or row.get("shot") or row.get("clip_id")
        if _vote_disagreement(row) >= 0.34:
            findings.append(finding(
                "warn",
                "VLM 自一致投票分歧较高；该判题需人工复核或换 judge 复判。",
                shot=shot,
                stage="review",
                artifacts=(rel,),
                vote_disagreement=round(_vote_disagreement(row), 3),
            ))
        if boolish_false(row.get("frame_coverage_ok")):
            findings.append(finding(
                "warn",
                "VLM 判题抽帧覆盖不足，可能漏掉中段漂移/动作结果。",
                shot=shot,
                stage="review",
                artifacts=(rel,),
            ))
    return findings


def analyze(root: str, ep: str) -> dict:
    data, rel = load_first_json(root, tuple(r.format(ep=ep) for r in REPORT_RELS))
    if data is None:
        return {
            "available": False,
            "findings": [],
            "notes": ["未找到 video_vlm_consistency sidecar；VLM/LMM 成片判题跳过。"],
        }

    findings: List[dict] = []
    rows = rows_from(data, ("findings", "judgements", "judgments", "checks", "items", "results"))
    findings.extend(_schema_findings(data, rel, rows))
    for row in rows:
        verdict = verdict_from(row)
        if not verdict and boolish_false(row.get("match")):
            verdict = "block" if _confidence(row) >= 0.75 else "warn"
        if not verdict and boolish_false(row.get("passes")):
            verdict = "warn"
        if verdict in {"block", "warn"}:
            findings.append(finding(
                verdict,
                _message(row),
                shot=row.get("clip") or row.get("shot") or row.get("clip_id"),
                stage=str(row.get("return_to_stage") or row.get("stage") or "video"),
                artifacts=(rel,),
                question=row.get("question"),
                expected=row.get("expected"),
                observed=row.get("observed"),
                confidence=row.get("confidence"),
            ))

    if isinstance(data, dict) and data.get("overall_verdict") in {"block", "warn"} and not findings:
        findings.append(finding(str(data.get("overall_verdict")), str(data.get("summary") or "视频 VLM 总判定未通过"), artifacts=(rel,)))

    return {"available": True, "findings": findings, "notes": []}


if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ns = ap.parse_args()
    print(json.dumps(analyze(ns.root, ns.episode), ensure_ascii=False, indent=2))
