#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""behavioral_signals.py — 合成视角行为产物的中性表面比较层。

输入仍兼容：

* ``评分/reader_predictions_第NN章.json``：合成阅读视角对下一章的短预测；
* ``评分/reader_survey_第NN章.json``：合成视角填写的 bored/confused/
  disbelief/favorite/annoying/recall 问卷骨架。

本脚本只报告可复算事实：预测之间的 char-2gram 表面差异、预测与下一章开头的
最大字面重合、问卷中被标注的句段，以及 recall 文本与上一章的字面重合。它不把
这些数值命名为“悬念值/意外度/留存”，不从多数合成角色推断真实人群，也不生成
“弃书风险/OOC/信息事故/必须反转”等创作约束。所有产物均为 synthetic、
context-only，只能转成回正文核对的问题。

用法：
    python3 behavioral_signals.py <作品根> [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from typing import Any

_HERE = os.path.dirname(os.path.abspath(__file__))
_WIKI = os.path.abspath(os.path.join(_HERE, "..", "..", "novel-wiki", "scripts"))
if _WIKI not in sys.path:
    sys.path.insert(0, _WIKI)
try:
    from wiki_builder import list_chapters
except Exception:
    def list_chapters(project, *a, **k):  # type: ignore
        return []


PREDICTIONS_GLOB = os.path.join("评分", "reader_predictions_第*章.json")
SURVEY_GLOB = os.path.join("评分", "reader_survey_第*章.json")
MIN_PREDICTIONS_FOR_PAIRWISE = 2
ACTUAL_HEAD_CHARS = int(os.environ.get("NOVEL_BEHAV_ACTUAL_HEAD", "1200"))
NGRAM = 2
PROVENANCE = "synthetic-surface-comparison·uncalibrated·context-only"

_NOISE_RE = re.compile(r"[\s，。！？、；：…—\-\|,.!?;:\"'“”‘’()（）\[\]【】《》]+")


def clean(text: Any) -> str:
    return _NOISE_RE.sub("", str(text or ""))


def shingles(text: Any, n: int = NGRAM) -> set[str]:
    cleaned = clean(text)
    if len(cleaned) < n:
        return {cleaned} if cleaned else set()
    return {cleaned[idx:idx + n] for idx in range(len(cleaned) - n + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    return intersection / (len(a) + len(b) - intersection) if intersection else 0.0


def pairwise_surface_difference(predictions: list[str]) -> float | None:
    """预测文本两两 ``1-Jaccard`` 均值；只表示字面差异，不表示悬念。"""
    sets = [shingles(item) for item in predictions if clean(item)]
    if len(sets) < MIN_PREDICTIONS_FOR_PAIRWISE:
        return None
    values = [
        1.0 - jaccard(sets[left], sets[right])
        for left in range(len(sets))
        for right in range(left + 1, len(sets))
    ]
    return round(sum(values) / len(values), 3) if values else None


def max_next_chapter_surface_overlap(predictions: list[str], actual_text: str | None) -> float | None:
    """任一预测被下一章开头覆盖的最大 2-gram 比率；重合不等于陈词滥调。"""
    actual = shingles(str(actual_text or "")[:ACTUAL_HEAD_CHARS])
    if not actual:
        return None
    overlaps = []
    for prediction in predictions:
        tokens = shingles(prediction)
        if tokens:
            overlaps.append(len(tokens & actual) / len(tokens))
    return round(max(overlaps), 3) if overlaps else None


def recall_surface_overlap(recall_text: str, previous_text: str | None) -> float | None:
    """recall 文本被上一章覆盖的 2-gram 比率；不能据此推断记忆或留存。"""
    recall_tokens = shingles(recall_text)
    previous_tokens = shingles(str(previous_text or ""))
    if not recall_tokens or not previous_tokens:
        return None
    return round(len(recall_tokens & previous_tokens) / len(recall_tokens), 3)


def _perspective_id(row: dict[str, Any]) -> str:
    return str(row.get("perspective") or row.get("persona") or "unknown").strip() or "unknown"


def _prediction_rows(payload: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    for item in payload.get("predictions") or []:
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            perspective = _perspective_id(item)
        else:
            text = str(item or "").strip()
            perspective = "unknown"
        if text:
            rows.append({"perspective": perspective, "text": text})
    return rows


def _field_span(value: Any) -> str | None:
    if isinstance(value, dict):
        text = str(value.get("span") or value.get("note") or "").strip()
        return text or None
    text = str(value or "").strip()
    return text or None


def _character_answer(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    name = str(value.get("name") or "").strip()
    reason = str(value.get("reason") or "").strip()
    if not name and not reason:
        return None
    return {"name": name, "reason": reason}


def _survey_responses(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for raw in payload.get("responses") or []:
        if not isinstance(raw, dict):
            continue
        disbelief = raw.get("disbelief")
        characters = []
        if isinstance(disbelief, dict):
            characters = [
                str(item).strip() for item in disbelief.get("characters") or []
                if str(item).strip()
            ]
        rows.append({
            "perspective": _perspective_id(raw),
            "bored": _field_span(raw.get("bored")),
            "confused": _field_span(raw.get("confused")),
            "disbelief": _field_span(disbelief),
            "disbelief_characters": characters,
            "favorite_character": _character_answer(raw.get("favorite_character")),
            "annoying_character": _character_answer(raw.get("annoying_character")),
            "recall": str(raw.get("recall") or "").strip(),
        })
    return rows


def _question(kind: str, chapter: int, question: str, *, evidence: Any = None) -> dict[str, Any]:
    return {
        "type": kind,
        "chapter": chapter,
        "question": question,
        "evidence": evidence,
        "evidence_type": "synthetic_probe",
        "decision_authority": "context_only",
        "automatic_action": None,
    }


def _analyze_surveys(project: str, chapters: dict[int, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = []
    questions = []
    for path in sorted(glob.glob(os.path.join(project, SURVEY_GLOB))):
        try:
            with open(path, encoding="utf-8") as f:
                payload = json.load(f)
        except (OSError, ValueError):
            continue
        try:
            chapter = int(payload.get("chapter"))
        except (TypeError, ValueError):
            continue
        responses = _survey_responses(payload)
        if not responses:
            continue
        bored = [
            {"perspective": row["perspective"], "span": row["bored"]}
            for row in responses if row["bored"]
        ]
        confused = [
            {"perspective": row["perspective"], "span": row["confused"]}
            for row in responses if row["confused"]
        ]
        disbelief = [
            {
                "perspective": row["perspective"],
                "span": row["disbelief"],
                "characters": row["disbelief_characters"],
            }
            for row in responses if row["disbelief"]
        ]
        recalls = {
            row["perspective"]: recall_surface_overlap(row["recall"], chapters.get(chapter - 1))
            for row in responses if row["recall"]
        }
        recalls = {key: value for key, value in recalls.items() if value is not None}
        favorites = [
            {"perspective": row["perspective"], **row["favorite_character"]}
            for row in responses if row["favorite_character"]
        ]
        annoying = [
            {"perspective": row["perspective"], **row["annoying_character"]}
            for row in responses if row["annoying_character"]
        ]
        row = {
            "chapter": chapter,
            "response_count": len(responses),
            "annotations": {
                "bored": bored,
                "confused": confused,
                "disbelief": disbelief,
                "favorite_character": favorites,
                "annoying_character": annoying,
            },
            "recall_previous_chapter_surface_overlap": recalls or None,
            "interpretation": "synthetic_annotations_and_literal_overlap_only",
        }
        rows.append(row)
        if bored:
            questions.append(_question(
                "review_bored_annotations", chapter,
                "这些合成视角标注的走神句段是否真的存在目标停滞、无效重复或阅读意图上的必要停顿？须回正文判断，不因标注数量自动删改。",
                evidence=bored[:6],
            ))
        if confused:
            questions.append(_question(
                "review_confused_annotations", chapter,
                "这些困惑标注来自指代/时序/知情面缺口，还是作品有意延迟信息？须引用上下文核对。",
                evidence=confused[:6],
            ))
        if disbelief:
            questions.append(_question(
                "review_disbelief_annotations", chapter,
                "标注句段与人物既有动机、状态账或叙事视角是否存在可证矛盾？合成视角的不信不自动等于 OOC。",
                evidence=disbelief[:6],
            ))
        if recalls:
            questions.append(_question(
                "review_recall_surface_overlap", chapter - 1,
                "recall 与上一章的字面重合差异来自同义改写、选择性概括、专名遗漏还是事实错记？该比率不能推断真实记忆或留存。",
                evidence=recalls,
            ))
    return rows, questions


def analyze(project: str) -> dict[str, Any]:
    paths = sorted(glob.glob(os.path.join(project, PREDICTIONS_GLOB)))
    has_survey = bool(glob.glob(os.path.join(project, SURVEY_GLOB)))
    if not paths and not has_survey:
        return {
            "ran": False,
            "skipped": (
                "无 评分/reader_predictions_第NN章.json 或 reader_survey_第NN章.json——"
                "合成视角完成预测/问卷后可生成 context-only 表面比较"
            ),
        }

    chapters = {chapter_id: text for chapter_id, _path, text in list_chapters(project)}
    prediction_rows = []
    questions = []
    for path in paths:
        try:
            with open(path, encoding="utf-8") as f:
                payload = json.load(f)
        except (OSError, ValueError):
            continue
        try:
            chapter = int(payload.get("chapter"))
        except (TypeError, ValueError):
            continue
        predictions = _prediction_rows(payload)
        texts = [item["text"] for item in predictions]
        difference = pairwise_surface_difference(texts)
        overlap = max_next_chapter_surface_overlap(texts, chapters.get(chapter + 1))
        row = {
            "chapter": chapter,
            "prediction_count": len(predictions),
            "pairwise_surface_difference": difference,
            "next_chapter_max_surface_overlap": overlap,
            "next_chapter_available": (chapter + 1) in chapters,
            "insufficient_for_pairwise": len(predictions) < MIN_PREDICTIONS_FOR_PAIRWISE,
            "prediction_examples": predictions[:8],
            "interpretation": "literal_2gram_comparison_only",
        }
        prediction_rows.append(row)
        if predictions:
            questions.append(_question(
                "review_prediction_surface_difference", chapter,
                "这些预测在剧情方向上真的相同/不同，还是只因措辞造成表面差异？它们覆盖了上一章哪些显性承诺？",
                evidence={"pairwise_surface_difference": difference, "examples": predictions[:6]},
            ))
        if overlap is not None:
            questions.append(_question(
                "review_prediction_next_chapter_overlap", chapter + 1,
                "预测与下一章的重合是有效伏笔兑现、类型承诺、偶然同词还是过度明示？重合本身不等于陈词滥调，也不要求强行反转。",
                evidence={"max_surface_overlap": overlap, "source_prediction_chapter": chapter},
            ))

    survey_rows, survey_questions = _analyze_surveys(project, chapters)
    questions.extend(survey_questions)
    return {
        "schema_version": 2,
        "kind": "novel_synthetic_behavior_probe",
        "ran": True,
        "evidence_type": "synthetic_probe",
        "validation_status": "unvalidated",
        "decision_authority": "context_only",
        "numeric_score_eligible": False,
        "automatic_constraint_eligible": False,
        "measurement": {
            "ngram": NGRAM,
            "actual_head_chars": ACTUAL_HEAD_CHARS,
            "min_predictions_for_pairwise": MIN_PREDICTIONS_FOR_PAIRWISE,
            "provenance": PROVENANCE,
            "note": "数值只描述字面差异/重合；无优劣方向、无阈值、无群体推断。",
        },
        "prediction_chapters": prediction_rows,
        "survey_chapters": survey_rows,
        "questions": questions,
        "question_count": len(questions),
        "alerts": [],
        "alerts_policy": "deprecated_always_empty_no_automatic_creative_constraints",
        "blocking": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="合成视角行为产物的中性表面比较（context-only）")
    parser.add_argument("project_path")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = analyze(args.project_path)
    if result.get("ran"):
        output = os.path.join(args.project_path, "评分", "behavioral_signals.json")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not result.get("ran"):
        print("ℹ️ " + result.get("skipped", "skipped"))
        return 0
    print(
        f"ℹ️ 合成行为表面比较：{len(result['prediction_chapters'])} 个预测点，"
        f"{len(result['survey_chapters'])} 个问卷点，{result['question_count']} 个正文复核问题"
    )
    print("  所有结果均为 context-only，不生成悬念/意外/留存结论，也不自动约束创作。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
