#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plan and optionally mark ad delivery outputs from `_进度.md`.

`compose.sh` builds the master. This helper closes the delivery bookkeeping
loop: read the deliverable matrix, emit deterministic commands/expected paths,
and mark rows complete when files already exist.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

_CRAFT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ad-craft", "scripts"))
if _CRAFT not in sys.path:
    sys.path.insert(0, _CRAFT)
import contract  # noqa: E402
import platform_pack  # noqa: E402
import progress_set  # noqa: E402
import delivery_qc  # noqa: E402
import accessibility_qc  # noqa: E402
import provenance_qc  # noqa: E402
import rendered_text_qc  # noqa: E402

_VOICE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ad-voice"))
if _VOICE not in sys.path:
    sys.path.insert(0, _VOICE)
import asr_consistency  # noqa: E402


FIELDS = ("label", "duration", "aspect", "kind", "spec", "status", "path")


def _split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_separator(cells):
    return bool(cells) and all(set(c) <= set("-: ") for c in cells)


def parse_deliverables(text):
    rows = []
    in_matrix = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("## "):
            in_matrix = "交付版本矩阵" in s
            continue
        if not in_matrix or not s.startswith("|"):
            continue
        cells = _split_row(s)
        if len(cells) < 7 or cells[0] in ("交付件", "") or _is_separator(cells):
            continue
        rows.append(dict(zip(FIELDS, cells[:7])))
    return rows


def _safe_name(text):
    text = text.replace(":", "x")
    return re.sub(r"[^0-9A-Za-z_.\-\u4e00-\u9fff]+", "_", text).strip("_") or "variant"


def expected_relpath(row):
    kind = row["kind"]
    if kind == "master":
        return "合成/成片_主片.mp4"
    if kind == "cutdown":
        return f"合成/cutdown/成片_{_safe_name(row['duration'])}.mp4"
    if kind == "reframe":
        return f"合成/多比例/成片_{_safe_name(row['aspect'])}.mp4"
    return f"合成/ab/{_safe_name(row['label'])}.mp4"


def deliverable_id(row):
    if row["kind"] == "master":
        return "master"
    if row["kind"] == "cutdown":
        return "cut_" + row["duration"].lower()
    if row["kind"] == "reframe":
        return "reframe_" + row["aspect"].replace(":", "x")
    return _safe_name(row["label"])


def planned_command(row, root):
    quoted = json.dumps(root, ensure_ascii=False)
    out = expected_relpath(row)
    if row["kind"] == "master":
        settings = _parse_settings(os.path.join(root, "_设置.md"))
        sub_map = {"中文": "zh", "中英双语": "bilingual", "仅英文": "en", "无字幕": "none"}
        sub = sub_map.get(settings.get("字幕语言"), "zh")
        spec = row["spec"] if row["spec"] in contract.DELIVERY_PROFILE else settings.get("交付规格", "平台默认")
        return f"bash skills/ad/ad-compose/compose.sh {quoted} {row['aspect']} {sub} {json.dumps(spec, ensure_ascii=False)}"
    if row["kind"] == "cutdown":
        plan = os.path.join(root, "合成", "cutdown", f"plan_{_safe_name(row['duration'])}.json")
        outp = os.path.join(root, out)
        # --render 实际拼接产出 MP4（需 ffmpeg）；--json 同时落计划
        return (f"python3 skills/ad/ad-compose/cutdown.py {quoted} --target {row['duration']} "
                f"--aspect {row['aspect']} --render "
                f"--out {json.dumps(outp, ensure_ascii=False)} "
                f"--json {json.dumps(plan, ensure_ascii=False)}")
    if row["kind"] == "reframe":
        src = os.path.join(root, "合成", "成片_主片.mp4")
        outp = os.path.join(root, out)
        # reframe --render 实际跑 ffmpeg crop/pad 输出 MP4（主体偏置时补 --crop-x/--crop-y）
        return (f"python3 skills/ad/ad-compose/reframe.py --src 1920x1080 --target {row['aspect']} "
                f"--in {json.dumps(src, ensure_ascii=False)} --render "
                f"--out {json.dumps(outp, ensure_ascii=False)}")
    return f"# A/B 版本需操作者手工生成 → {out}"


def _parse_settings(path):
    out = {}
    try:
        raw = open(path, encoding="utf-8").read()
    except OSError:
        return out
    for line in raw.splitlines():
        m = re.match(r"\s*[-*]?\s*([^:：#]+)[:：]\s*([^#]+)", line)
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
    return out


def build_plan(root, progress_text):
    root = os.path.abspath(root)
    try:
        brief = json.loads(Path(root, "需求", "brief.json").read_text(encoding="utf-8"))
    except Exception:
        brief = {}
    custom_profiles = brief.get("delivery_profiles") if isinstance(brief.get("delivery_profiles"), dict) else {}
    delivery_pack = platform_pack.build_pack(Path(root))
    placement_specs = delivery_pack.get("placement_specs") or {}
    delivery_mapping = delivery_pack.get("deliverable_placements") or {}
    legacy_constraints = [dict(spec, platform=platform)
                          for platform, spec in (delivery_pack.get("specs") or {}).items()]
    rows = parse_deliverables(progress_text)
    items = []
    for row in rows:
        did = deliverable_id(row)
        targets = delivery_mapping.get(did) or delivery_mapping.get(row["label"]) or []
        if isinstance(targets, str):
            targets = [targets]
        mapping_error = ""
        if placement_specs:
            if not targets and len(placement_specs) == 1:
                targets = [next(iter(placement_specs))]
            unknown = [key for key in targets if key not in placement_specs]
            if not targets:
                mapping_error = f"交付件 {did} 未映射实际 placement"
            elif unknown:
                mapping_error = f"交付件 {did} 含未知 placement: {', '.join(unknown)}"
            platform_constraints = [dict(placement_specs[key], placement_key=key)
                                    for key in targets if key in placement_specs]
        else:
            platform_constraints = legacy_constraints
        rel = expected_relpath(row)
        abs_path = os.path.join(root, rel)
        spec = row["spec"] if row["spec"] in contract.DELIVERY_PROFILE else "平台默认"
        profile_error = ""
        try:
            profile = contract.resolve_delivery_profile(spec, custom_profiles.get("自定义"))
        except ValueError as exc:
            profile_error = str(exc)
            profile = {"loudness_lufs": None, "true_peak_db": None,
                       "authority": "invalid_project_override", "source": profile_error}
        items.append({
            "deliverable_id": did,
            "label": row["label"],
            "kind": row["kind"],
            "duration": row["duration"],
            "aspect": row["aspect"],
            "spec": row["spec"],
            "expected_path": rel,
            "exists": os.path.isfile(abs_path),
            "command": planned_command(row, root),
            "loudness_lufs": profile["loudness_lufs"],
            "true_peak_db": profile["true_peak_db"],
            "delivery_profile": profile,
            "delivery_profile_error": profile_error,
            "technical_profile": contract.house_master_profile(),
            "target_placements": list(targets),
            "placement_mapping_error": mapping_error,
            "platform_constraints": platform_constraints,
        })
    return {"schema_version": 3, "kind": "ad_delivery_plan", "project_root": root,
            "platform_pack_summary": delivery_pack.get("summary") or {},
            "summary": {"block": sum(bool(item.get("placement_mapping_error")) for item in items)},
            "deliverables": items}


def mark_existing(root, progress_text, plan, qc_report=None):
    out = progress_text
    passed = {i.get("deliverable_id") for i in (qc_report or {}).get("items", []) if i.get("passed")}
    for item in plan["deliverables"]:
        if not item["exists"] or item["deliverable_id"] not in passed:
            continue
        out = progress_set.set_deliverable_text(
            out,
            item["deliverable_id"],
            "✅",
            item["expected_path"],
            item["spec"],
            f"交付件完成：{item['label']}",
        )
    return out


def main():
    ap = argparse.ArgumentParser(description="拍广告交付矩阵计划/回写")
    ap.add_argument("project_root")
    ap.add_argument("--json", default=None, help="输出 delivery_plan.json；默认 合成/delivery_plan.json")
    ap.add_argument("--mark-existing", action="store_true", help="发现输出文件存在时回写 _进度.md 对应交付件 ✅")
    ap.add_argument("--run-asr", action="store_true", help="调用可用的 whisper CLI 生成实际 VO/母版 transcript")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    progress_path = os.path.join(root, "_进度.md")
    if not os.path.isfile(progress_path):
        print(f"[err] 缺 _进度.md：{progress_path}", file=sys.stderr)
        sys.exit(2)
    with open(progress_path, encoding="utf-8") as f:
        progress_text = f.read()
    plan = build_plan(root, progress_text)
    # 所有下游 QC 必须读取本次计划，不能意外消费磁盘上的旧 delivery_plan。
    json_path = args.json or os.path.join(root, "合成", "delivery_plan.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    qc_report = delivery_qc.build_report(Path(root), plan)
    qc_path = os.path.join(root, "合成", "delivery_qc.json")
    os.makedirs(os.path.dirname(qc_path), exist_ok=True)
    with open(qc_path, "w", encoding="utf-8") as f:
        json.dump(qc_report, f, ensure_ascii=False, indent=2)
    rendered_text_report = rendered_text_qc.build(Path(root))
    rendered_text_path = os.path.join(root, "合成", "rendered_text_qc.json")
    with open(rendered_text_path, "w", encoding="utf-8") as f:
        json.dump(rendered_text_report, f, ensure_ascii=False, indent=2)
    asr_report = asr_consistency.build(Path(root), run_asr=args.run_asr)
    asr_path = os.path.join(root, "合成", "asr_consistency.json")
    with open(asr_path, "w", encoding="utf-8") as f:
        json.dump(asr_report, f, ensure_ascii=False, indent=2)
    provenance_report = provenance_qc.build(Path(root))
    provenance_path = os.path.join(root, "合规", "provenance_qc.json")
    os.makedirs(os.path.dirname(provenance_path), exist_ok=True)
    with open(provenance_path, "w", encoding="utf-8") as f:
        json.dump(provenance_report, f, ensure_ascii=False, indent=2)
    accessibility_report = accessibility_qc.build_report(Path(root), plan)
    accessibility_path = os.path.join(root, "合成", "accessibility_qc.json")
    with open(accessibility_path, "w", encoding="utf-8") as f:
        json.dump(accessibility_report, f, ensure_ascii=False, indent=2)
    final_reports = (qc_report, rendered_text_report, asr_report, provenance_report, accessibility_report)
    all_final_qc_clean = all(int(((report.get("summary") or {}).get("block")) or 0) == 0
                             for report in final_reports)
    if args.mark_existing and all_final_qc_clean:
        with open(progress_path, "w", encoding="utf-8") as f:
            f.write(mark_existing(root, progress_text, plan, qc_report))
    elif args.mark_existing:
        print("[skip] 最终媒体 QC 尚有 block，未回写交付件 ✅", file=sys.stderr)
    print(f"# ad delivery plan  rows={len(plan['deliverables'])}")
    for item in plan["deliverables"]:
        flag = "✅" if item["exists"] else "⬜"
        print(f"{flag} {item['label']} -> {item['expected_path']}")
    print(f"[ok] {json_path}")
    print(f"[ok] {qc_path} block={qc_report['summary']['block']}")
    print(f"[ok] {accessibility_path} block={accessibility_report['summary']['block']} "
          f"warn={accessibility_report['summary']['warn']}")
    print(f"[ok] {rendered_text_path} block={rendered_text_report['summary']['block']} "
          f"warn={rendered_text_report['summary']['warn']}")
    print(f"[ok] {asr_path} block={asr_report['summary']['block']} warn={asr_report['summary']['warn']}")
    print(f"[ok] {provenance_path} block={provenance_report['summary']['block']}")
    return 1 if not all_final_qc_clean else 0


if __name__ == "__main__":
    raise SystemExit(main())
