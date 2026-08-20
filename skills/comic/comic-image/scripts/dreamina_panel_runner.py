#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 Dreamina 官方 CLI 为 comic panel_jobs.json 连续生成逐格 PNG。"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import codex_panel_runner as shared  # noqa: E402


# Keep the runner label identical to comic-settings/build_panel_jobs.  The
# official CLI calls the service Dreamina; using the adjacent product name
# "Seedream" here made valid Dreamina 5.0 job packs fail the backend guard
# before submission.
DREAMINA_MODEL = "Dreamina 5.0"
DREAMINA_CHANNEL = "Dreamina/即梦官方 CLI"
# 实机附件上限的唯一真值在 comic/_lib/image_backend_adapter；此处只解引用，不再双写数字。
DREAMINA_REFERENCE_LIMIT = shared.resolve_capabilities(
    DREAMINA_MODEL, DREAMINA_CHANNEL
).executable_attachment_limit
DREAMINA_RATIOS = {
    "21:9": 21 / 9,
    "16:9": 16 / 9,
    "3:2": 3 / 2,
    "4:3": 4 / 3,
    "1:1": 1.0,
    "3:4": 3 / 4,
    "2:3": 2 / 3,
    "9:16": 9 / 16,
}


def dreamina_version() -> str:
    proc = subprocess.run(
        ["dreamina", "--version"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return (proc.stdout or proc.stderr or "dreamina unknown").strip().splitlines()[0]


def nearest_supported_ratio(size: dict[str, int]) -> str:
    width = max(1, int(size.get("width") or 1))
    height = max(1, int(size.get("height") or 1))
    target = width / height
    return min(DREAMINA_RATIOS, key=lambda key: abs(math.log(target / DREAMINA_RATIOS[key])))


def reference_role_label(record: dict[str, str]) -> str:
    role = str(record.get("role") or "").lower()
    ref_id = str(record.get("id") or "")
    if role == "composite_views" or record.get("composite"):
        part_count = len(record.get("parts") or []) or "多"
        return (
            f"同一主体（{ref_id}）的 {part_count} 视图拼板参考：网格内全部分格都是这同一个主体的"
            "不同视角/表情，绝不当成多个人物；据此保持该主体的脸、发型与服装完全一致"
        )
    if role == "style" or ref_id.startswith("STYLE_"):
        return "仅继承线条、色彩、光影与材质语言的画风参考"
    if role in {"front", "face", "three_quarter", "side", "back", "outfit"} or ref_id.startswith("CHAR_"):
        return f"角色身份/服装参考（{ref_id}，不得与其他角色串脸串衣）"
    if ref_id.startswith(("MON_", "BEAST_", "ANIMAL_")):
        return f"生物/动物身份与体型参考（{ref_id}，不得画成同类里的另一物种）"
    if role == "location" or ref_id.startswith("LOC_"):
        return f"场景结构、材质与光位参考（{ref_id}）"
    if role == "prop" or ref_id.startswith(("PROP_", "WEAPON_")):
        return f"道具结构与材质参考（{ref_id}）"
    return f"视觉参考（{ref_id}）"


def build_prompt(
    job: dict[str, Any],
    reference_records: list[dict[str, str]],
    ratio: str,
    correction: str = "",
) -> str:
    shared.validate_compiled_job(job, expected_backend=DREAMINA_MODEL)
    size = job.get("size") if isinstance(job.get("size"), dict) else {}
    width = int(size.get("width") or 1296)
    height = int(size.get("height") or 1040)
    mapping = "\n".join(
        f"- 输入图 {index}：{reference_role_label(record)}"
        for index, record in enumerate(reference_records, start=1)
    )
    submit_prompt = shared.safety_shape_visual_prompt(str(job.get("submit_prompt") or ""))
    negative_prompt = shared.safety_shape_visual_prompt(str(job.get("negative_prompt") or ""))
    negative = f"\n独立负向约束：{negative_prompt}" if negative_prompt else ""
    corrective = f"\n本次纠偏重抽要求：{correction.strip()}" if correction.strip() else ""
    return f"""请依据输入参考图生成一张单格、铺满画布的无字漫画完成稿。

最终交付尺寸为 {width}x{height}；本次服务端使用最接近的 {ratio} 画幅。所有关键人物、脸、手脚、道具和动作接触点必须落在中央安全区，四边预留至少 12% 可裁切余量。

输入图职责：
{mapping or "- 无参考图；仅执行下面的可见画面合同。"}

模型提交 prompt：
{submit_prompt}{negative}{corrective}

补充执行约束：
1. 输入图只按上述职责继承；画风图不得复制其中人物、服装、物件、场景布局或构图。
2. 同一 ID 的多张图是同一主体的不同视图；不同 ID 绝不合并、换脸、串衣或复制成双胞胎。
3. 只生成一个完整面板，不要内部多格、拼贴、边框、截图 UI、对白气泡、旁白框、空白文字框、可读文字、乱码、Logo 或水印。
4. 只允许非血腥奇幻表现：静止剪影、破损衣物、黑色墨气、暗红布片、烟尘和冲击线；禁止可见伤口、穿刺、体液、残肢或痛苦特写。
5. 人体最多两条手臂两只手；手、腕、前臂、肘、肩连接自然，脚和鞋不能画成手；武器与手、地面和命中点不得穿模。
"""


def concise_visual_fact(job: dict[str, Any]) -> str:
    """从已哈希提交词提取不改剧情的核心可见事实。"""
    text = str(job.get("submit_prompt") or "").strip()
    match = re.search(r"画面事实[：:]\s*(.+?)(?:\s+构图与表演[：:]|\s+画风与稿层[：:]|$)", text)
    if match:
        return match.group(1).strip(" ；;。")
    return text[:600].strip()


def build_concise_recovery_prompt(
    job: dict[str, Any],
    reference_records: list[dict[str, str]],
    ratio: str,
    correction: str = "",
    fact_override: str = "",
) -> str:
    """构建同后端超时/最终失败时的精简执行包装，不改已哈希生产合同。"""
    shared.validate_compiled_job(job, expected_backend=DREAMINA_MODEL)
    size = job.get("size") if isinstance(job.get("size"), dict) else {}
    width = int(size.get("width") or 1296)
    height = int(size.get("height") or 1040)
    mapping = "\n".join(
        f"- 输入图 {index}：{reference_role_label(record)}"
        for index, record in enumerate(reference_records, start=1)
    )
    identities: list[str] = []
    for binding in job.get("character_bindings") or []:
        if not isinstance(binding, dict):
            continue
        resolved = binding.get("resolved_contracts") if isinstance(binding.get("resolved_contracts"), dict) else {}
        outfit = resolved.get("outfit") if isinstance(resolved.get("outfit"), dict) else {}
        state = resolved.get("state") if isinstance(resolved.get("state"), dict) else {}
        label = str(binding.get("display_name") or binding.get("character_id") or "角色")
        parts = [label]
        if outfit.get("name"):
            parts.append(str(outfit["name"]))
        if state.get("name"):
            parts.append(str(state["name"]))
        identities.append(" / ".join(parts))
    identity_line = "；".join(identities) or "按输入角色参考锁定身份"
    corrective = f"\n本次纠偏：{correction.strip()}" if correction.strip() else ""
    fact = fact_override.strip() or concise_visual_fact(job)
    return f"""生成一张单格、铺满画布、无字的彩色漫画完成稿。

核心画面事实：{fact}
人物状态：{identity_line}
画风：宋画工笔淡彩与写实国漫结合，低饱和矿物色，清晰有压力变化的墨线，电影动机光，粗粝北宋市井质感。
构图：服务端使用 {ratio}，关键人物、脸、手脚、道具和动作接触点全部放在中央安全区，四边预留 12% 裁切余量；最终裁为 {width}x{height}。

输入图职责：
{mapping or "- 无参考图；严格执行核心画面事实。"}

保持同一角色的脸型、眼型、发际线、发髻、体型和服装主色；不同角色绝不串脸、串衣或合并。场景图只继承空间、材质和光位，风格图只继承线条、色彩与光影。{corrective}

只生成一个完整面板。禁止内部多格、拼贴、边框、对白气泡、旁白框、空白文字框、可读文字、乱码、日文、Logo、水印、现代物件、额外肢体、手脚混淆、穿模和无来源发光。
"""


def submit_id_from(text: str) -> str:
    patterns = (
        r'"submit_id"\s*:\s*"([^"]+)"',
        r"submit[_ ]?id\s*[=:]\s*([A-Za-z0-9._-]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1)
    return ""


def downloaded_images(directory: Path) -> list[Path]:
    candidates: list[Path] = []
    for suffix in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        candidates.extend(directory.rglob(suffix))
    return sorted(candidates, key=lambda path: (path.stat().st_mtime, path.stat().st_size), reverse=True)


def materialize_png(source: Path, target: Path) -> bool:
    try:
        from PIL import Image
    except ImportError:
        return False
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source) as image:
            image.convert("RGB").save(target, "PNG")
    except (OSError, ValueError):
        return False
    return shared.png_valid(target)


def normalize_panel(source: Path, target: Path, size: dict[str, int]) -> dict[str, Any]:
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise RuntimeError("Dreamina panel normalization requires Pillow") from exc
    width = int(size.get("width") or 0)
    height = int(size.get("height") or 0)
    if width <= 0 or height <= 0:
        raise ValueError(f"invalid target panel size: {size}")
    with Image.open(source) as image:
        rgb = image.convert("RGB")
        raw_size = rgb.size
        normalized = ImageOps.fit(
            rgb,
            (width, height),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        normalized.save(target, "PNG")
    return {
        "mode": "center_crop_after_safe_margin_prompt",
        "source_size": {"width": raw_size[0], "height": raw_size[1]},
        "target_size": {"width": width, "height": height},
        "normalization_scale": round(max(width / max(raw_size[0], 1), height / max(raw_size[1], 1)), 6),
        "upscaled": max(width / max(raw_size[0], 1), height / max(raw_size[1], 1)) > 1.0,
    }


def run_dreamina(
    prompt: str,
    image_paths: list[Path],
    raw_output: Path,
    *,
    ratio: str,
    model_version: str,
    resolution_type: str,
    timeout_sec: int,
    poll_sec: int,
) -> tuple[bool, str, str]:
    with tempfile.TemporaryDirectory(prefix="comic-dreamina-download-") as tmp:
        download_dir = Path(tmp)
        cmd = [
            "dreamina",
            "image2image",
            "--images",
            ",".join(str(path) for path in image_paths),
            "--prompt",
            prompt,
            "--ratio",
            ratio,
            "--model_version",
            model_version,
            "--resolution_type",
            resolution_type,
            "--poll",
            str(max(0, min(poll_sec, timeout_sec))),
        ]
        started = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired:
            return False, "", f"dreamina image2image timed out after {timeout_sec}s"
        combined = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
        if proc.returncode != 0:
            return False, "", f"dreamina image2image exit {proc.returncode}: {combined[-4000:]}"
        submit_id = submit_id_from(combined)
        if not submit_id:
            return False, "", f"dreamina output did not include submit_id: {combined[-2000:]}"

        hard_error_tokens = ("unauthorized", "forbidden", "invalid parameter", "insufficient", "余额不足")
        last_output = ""
        while time.monotonic() - started < timeout_sec:
            try:
                query = subprocess.run(
                    [
                        "dreamina",
                        "query_result",
                        "--submit_id",
                        submit_id,
                        "--download_dir",
                        str(download_dir),
                    ],
                    stdin=subprocess.DEVNULL,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=min(60, max(10, timeout_sec)),
                )
            except subprocess.TimeoutExpired:
                last_output = "dreamina query_result timed out"
                time.sleep(2)
                continue
            last_output = "\n".join(part for part in (query.stdout, query.stderr) if part)
            candidates = downloaded_images(download_dir)
            if query.returncode == 0 and candidates:
                if materialize_png(candidates[0], raw_output):
                    return True, submit_id, ""
                return False, submit_id, f"downloaded result could not be converted to PNG: {candidates[0]}"
            lowered = last_output.lower()
            if any(token in lowered for token in hard_error_tokens):
                return False, submit_id, f"dreamina query_result hard failure: {last_output[-4000:]}"
            time.sleep(3)
        return False, submit_id, f"dreamina result not ready within {timeout_sec}s: {last_output[-2000:]}"


def write_reference_manifest(
    root: Path,
    chapter: str,
    panel_id: str,
    records: list[dict[str, str]],
    omitted: list[dict[str, str]],
    limit: int,
) -> Path:
    path = root / "生产数据" / "dreamina_reference_bundles" / chapter / f"{panel_id}.json"
    payload = {
        "schema_version": 1,
        "kind": "comic_dreamina_reference_bundle",
        "chapter": chapter,
        "panel_id": panel_id,
        "reference_input_mode": "dreamina_image2image_images",
        "reference_attachment_limit": limit,
        "cli_image_input_count": len(records),
        "references": [
            {key: value for key, value in record.items() if key != "abs_path"}
            for record in records
        ],
        "omitted_attachment_count": len(omitted),
        "omitted_attachments": [
            {
                "id": record.get("id", ""),
                "path": record.get("path", ""),
                "reason": "dreamina_image2image_reference_limit; textual_contract_retained",
            }
            for record in omitted
        ],
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    shared.write_json(path, payload)
    return path


def unrepresented_required_ids(
    selected: list[dict[str, str]],
    omitted: list[dict[str, str]],
) -> set[str]:
    """Return required contracts that have no executable image at all.

    Multiple views of one subject share an ID. If at least one view survives
    Dreamina's attachment limit, omitting extra views is a disclosed fidelity
    reduction, not a missing critical contract.
    """
    selected_ids = {str(record.get("id") or "") for record in selected}
    return {
        str(record.get("id") or "")
        for record in omitted
        if record.get("required")
        and str(record.get("id") or "")
        and str(record.get("id") or "") not in selected_ids
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="用 Dreamina 官方 CLI 生成 comic panel PNG")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--targets", default="", help="逗号分隔 panel_id；默认全部未完成")
    parser.add_argument("--limit", type=int, default=0, help="最多生成多少张；0 表示不限")
    parser.add_argument("--max-attempts", type=int, default=1)
    parser.add_argument("--reference-limit", type=int, default=DREAMINA_REFERENCE_LIMIT)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--timeout-sec", type=int, default=600)
    parser.add_argument("--poll-sec", type=int, default=120)
    parser.add_argument("--model-version", default="5.0")
    parser.add_argument(
        "--resolution-type",
        choices=("2k", "4k"),
        default="4k",
        help="服务端原生分辨率档；comic 默认请求当前 CLI 已暴露的最高档 4k，CLI 能力变化时须先核验 --help",
    )
    parser.add_argument(
        "--correction",
        default="",
        help="仅用于已目检失败目标格的执行层纠偏补充；不改写已哈希剧情/画面合同，prompt 快照会留痕",
    )
    parser.add_argument(
        "--concise-recovery",
        action="store_true",
        help="同一 Dreamina 后端连续超时/最终失败时，仅提交核心画面事实、身份/服装/场景锚与安全约束的精简执行包装",
    )
    parser.add_argument(
        "--recovery-fact",
        default="",
        help="仅配合 --concise-recovery：对触发服务端失败的核心画面事实做等义、中性、可视化改写；不得改变角色、动作结果或场景",
    )
    parser.add_argument(
        "--recheck-existing",
        action="store_true",
        help="只复核并恢复现有 panel PNG 的状态，不归档、不调用 Dreamina，也不消耗新的生成尝试",
    )
    parser.add_argument(
        "--accept-reviewed",
        action="store_true",
        help="对唯一当前 panel 写入 SHA 绑定签收；pass 或启发式 warn 可用，确定性 block 不可用",
    )
    parser.add_argument("--reviewer", default="", help="--accept-reviewed 必填：实际查看 contact sheet 的审核人")
    parser.add_argument("--review-notes", default="", help="--accept-reviewed 必填：逐轴目检结论与理由")
    parser.add_argument(
        "--skip-gate",
        action="store_true",
        help="仅复用绑定当前完整输入与 panel_jobs SHA 的已授权非 block receipt；不能用 waiver 绕过 preflight",
    )
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    jobs_path = root / "出图" / args.chapter / "prompt" / "panel_jobs.json"
    if not jobs_path.is_file():
        print(f"[err] missing panel jobs: {jobs_path}", file=sys.stderr)
        return 2
    data = shared.load_json(jobs_path)
    if (
        str(data.get("model") or "") != DREAMINA_MODEL
        or str(data.get("channel") or "") != DREAMINA_CHANNEL
    ):
        print(
            f"[err] panel jobs backend mismatch: {data.get('model')} / {data.get('channel')}; "
            "先用 comic-settings 切换并重建 panel_jobs",
            file=sys.stderr,
        )
        return 2
    targets = {item.strip() for item in args.targets.split(",") if item.strip()}
    if args.accept_reviewed:
        if args.recheck_existing or args.force:
            print("[err] --accept-reviewed 不能与 --recheck-existing/--force 同用", file=sys.stderr)
            return 2
        if len(targets) != 1:
            print("[err] --accept-reviewed 每次必须且只能 --targets 一个 panel", file=sys.stderr)
            return 2
        panel_id = next(iter(targets))
        try:
            accepted = shared.accept_panel_review(
                root,
                args.chapter,
                data,
                jobs_path,
                panel_id,
                args.reviewer,
                args.review_notes,
            )
        except ValueError as exc:
            print(f"[err] {exc}", file=sys.stderr)
            return 3
        if shared.all_ready(root, data.get("jobs") or []):
            shared.update_stage(
                root,
                args.chapter,
                "出图",
                "✅",
                evidence=f"生产数据/panel_qc/{args.chapter}",
                actor="comic-image.panel_acceptance",
            )
        print(f"[accepted] {panel_id} sha256={accepted['artifact_sha256']}", flush=True)
        return 0
    if args.recheck_existing and len(targets) != 1:
        print("[err] --recheck-existing 每次必须且只能 --targets 一个 panel", file=sys.stderr)
        return 2

    all_jobs = [job for job in data.get("jobs") or [] if isinstance(job, dict)]
    barrier, barrier_status = shared.first_sequence_barrier(root, all_jobs)
    if barrier is None:
        if not args.force:
            print("[ok] no pending jobs")
            return 0
    elif not args.recheck_existing:
        barrier_id = str(barrier.get("panel_id") or "")
        if args.force:
            if len(targets) != 1:
                print("[err] --force 在逐图双闸模式下每次必须且只能 --targets 一个 panel", file=sys.stderr)
                return 2
            forced_id = next(iter(targets))
            forced_index = next((i for i, row in enumerate(all_jobs) if str(row.get("panel_id") or "") == forced_id), -1)
            if forced_index < 0:
                print(f"[err] unknown target: {forced_id}", file=sys.stderr)
                return 2
            prior_unaccepted = [
                str(row.get("panel_id") or "")
                for row in all_jobs[:forced_index]
                if not shared.panel_acceptance_status(root, row).get("accepted")
            ]
            if prior_unaccepted:
                print(f"[err] 不能重抽 {forced_id}：此前图片尚未 accepted：{prior_unaccepted[0]}", file=sys.stderr)
                return 3
        else:
            if targets and barrier_id not in targets:
                print(f"[err] 逐图顺序闸要求先处理 {barrier_id}，不能越过它生成后续格", file=sys.stderr)
                return 3
            barrier_rel = str(barrier.get("result_path") or "").strip()
            if barrier_rel and shared.png_valid(shared.resolve_path(root, barrier_rel)):
                print(
                    f"[review-required] {barrier_id} 尚未 accepted（{barrier_status.get('reason')}）；"
                    f"先查看 panel_qc contact sheet，再用 --accept-reviewed --targets {barrier_id}，"
                    "启发式 warn 可具名带警告签收，确定性 block 才须修复/重抽。",
                    file=sys.stderr,
                )
                return 4

    if not args.recheck_existing:
        if args.skip_gate:
            receipt_status = shared.validate_gate_receipt(root, args.chapter, jobs_path)
            if receipt_status.get("status") != "current_pass":
                print("[err] --skip-gate 只允许复用绑定当前完整输入的已授权非 block receipt；不接受 waiver", file=sys.stderr)
                return 2
            print(f"[ok] --skip-gate 复用当前已授权 receipt：{receipt_status['path']}", flush=True)
        else:
            rc = shared.run_preflight_gate(root, args.chapter)
            if rc != 0:
                return rc
        if not shutil.which("dreamina"):
            print("[err] dreamina not found in PATH", file=sys.stderr)
            return 2

    jobs = shared.selected_jobs(data.get("jobs") or [], targets, args.limit, args.force or args.recheck_existing)
    if not jobs:
        print("[ok] no pending jobs")
        return 0
    missing = {
        str(job.get("panel_id")): shared.missing_reference_ids(root, job)
        for job in jobs
    }
    missing = {panel_id: refs for panel_id, refs in missing.items() if refs}
    if missing:
        for panel_id, refs in missing.items():
            print(f"[err] {panel_id} missing accepted shared references: {', '.join(refs)}", file=sys.stderr)
        return 2

    max_attempts = max(1, int(args.max_attempts))
    reference_limit = max(1, min(DREAMINA_REFERENCE_LIMIT, int(args.reference_limit)))
    backend_version = dreamina_version() if not args.recheck_existing else str(data.get("backend_version") or "")
    panel_dir = root / "出图" / args.chapter / "panels"
    candidate_root = root / "出图" / args.chapter / "candidates"
    failures = 0
    qc_blocked = 0

    for index, job in enumerate(jobs, start=1):
        panel_id = str(job.get("panel_id") or "")
        final = panel_dir / f"{panel_id}.png"
        archived_existing = ""
        should_archive_existing = (
            shared.png_valid(final)
            and not args.recheck_existing
            and (
                args.force
                or job.get("status") != "ready"
                or job.get("model") != DREAMINA_MODEL
                or job.get("source") != DREAMINA_CHANNEL
            )
        )
        all_records = shared.collect_reference_images(root, job)
        all_records, composite_disclosure = shared.reference_composite.compact_records_with_composites(
            root, all_records, reference_limit
        )
        for note in composite_disclosure.get("notes") or []:
            print(f"[warn] {panel_id} composite: {note}", flush=True)
        if composite_disclosure.get("applied"):
            sheets = ", ".join(
                f"{item['id']}({item['part_count']}视图)" for item in composite_disclosure["composites"]
            )
            print(f"[info] {panel_id} 多视图折叠为拼板参考：{sheets}", flush=True)
        records, omitted = shared.select_reference_attachments(all_records, reference_limit)
        missing_required_ids = unrepresented_required_ids(records, omitted)
        selected_subjects = {
            str(record.get("id") or "")
            for record in records
            if str(record.get("id") or "").startswith(("CHAR_", "MON_", "BEAST_", "ANIMAL_"))
        }
        required_subjects = {
            str(binding.get("character_id") or "")
            for binding in job.get("character_bindings") or []
            if isinstance(binding, dict)
        }
        missing_subjects = required_subjects - selected_subjects
        if missing_required_ids or missing_subjects:
            failures += 1
            job["status"] = "failed"
            missing_contracts = sorted(missing_required_ids | missing_subjects)
            job["error"] = (
                "executable reference budget cannot carry all critical contracts: "
                + ", ".join(missing_contracts)
            )
            shared.write_json(jobs_path, data)
            print(f"[fail] {panel_id}: {job['error']}", file=sys.stderr, flush=True)
            return 1

        reference_manifest = write_reference_manifest(
            root, args.chapter, panel_id, records, omitted, reference_limit
        )
        if args.recheck_existing:
            if not shared.png_valid(final):
                failures += 1
                job["status"] = "failed"
                job["error"] = f"existing panel PNG missing or invalid: {shared.rel_to_root(root, final)}"
                shared.write_json(jobs_path, data)
                print(f"[fail] {panel_id}: {job['error']}", file=sys.stderr, flush=True)
                continue
            post_qc = shared.post_qc_panel(
                root,
                args.chapter,
                job,
                final,
                records,
                omitted,
                adjacent_paths=shared.previous_accepted_panel_paths(root, all_jobs, panel_id),
            )
            post_qc_verdict = str(post_qc.get("verdict") or "block")
            checked_at = dt.datetime.now().isoformat(timespec="seconds")
            job.update(
                {
                    "status": shared.status_after_post_qc(post_qc),
                    "result_path": shared.rel_to_root(root, final),
                    "artifact_sha256": shared.file_sha256(final),
                    "reference_manifest": shared.rel_to_root(root, reference_manifest),
                    "reference_input_count": len(records),
                    "post_qc": post_qc,
                    "rechecked_at": checked_at,
                }
            )
            job.pop("error", None)
            if shared.panel_acceptance_status(root, job).get("accepted"):
                job["status"] = "ready"
            shared.append_event(
                root,
                {
                    "ts": checked_at,
                    "panel_id": panel_id,
                    "status": job["status"],
                    "backend": str(job.get("source") or DREAMINA_CHANNEL),
                    "model": str(job.get("model") or DREAMINA_MODEL),
                    "path": job["result_path"],
                    "sha256": job["artifact_sha256"],
                    "operation": "recheck_existing_without_generation",
                    "reference_manifest": job["reference_manifest"],
                    "reference_input_count": len(records),
                    "post_qc_verdict": post_qc_verdict,
                },
            )
            shared.write_json(jobs_path, data)
            print(
                f"[recheck] {panel_id} -> {job['result_path']} "
                f"(post_qc={post_qc_verdict}, status={job['status']})",
                flush=True,
            )
            return 0 if job["status"] == "ready" else (4 if post_qc_verdict in {"pass", "warn"} else 3)

        ratio = nearest_supported_ratio(job.get("size") or {})
        prompt_mode = "concise_recovery" if args.concise_recovery else "compiled_full"
        if args.concise_recovery:
            prompt = build_concise_recovery_prompt(
                job,
                records,
                ratio,
                correction=args.correction,
                fact_override=args.recovery_fact,
            )
        else:
            prompt = build_prompt(job, records, ratio, correction=args.correction)
        prompt_path = root / "出图" / args.chapter / "prompt" / "dreamina" / f"{panel_id}.txt"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt.rstrip() + "\n", encoding="utf-8")
        image_paths = [Path(record["abs_path"]) for record in records]
        started = time.monotonic()
        last_error = ""
        print(
            f"[start] {panel_id} ({index}/{len(jobs)}) ratio={ratio} refs={len(records)}",
            flush=True,
        )

        for attempt in range(1, max_attempts + 1):
            stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
            raw_path = candidate_root / panel_id / f"{stamp}_attempt{attempt}_dreamina_raw.png"
            success, submit_id, error = run_dreamina(
                prompt,
                image_paths,
                raw_path,
                ratio=ratio,
                model_version=args.model_version,
                resolution_type=args.resolution_type,
                timeout_sec=max(60, int(args.timeout_sec)),
                poll_sec=max(0, int(args.poll_sec)),
            )
            if not success:
                last_error = error
                shared.append_event(
                    root,
                    {
                        "ts": dt.datetime.now().isoformat(timespec="seconds"),
                        "panel_id": panel_id,
                        "status": "attempt_failed",
                        "backend": DREAMINA_CHANNEL,
                        "model": DREAMINA_MODEL,
                        "attempt": attempt,
                        "max_attempts": max_attempts,
                        "submit_id": submit_id,
                        "reference_manifest": shared.rel_to_root(root, reference_manifest),
                        "reference_input_count": len(records),
                        "error": error,
                        "duration_sec": round(time.monotonic() - started, 2),
                    },
                )
                print(f"[retry] {panel_id} attempt {attempt}/{max_attempts}: {error}", file=sys.stderr, flush=True)
                continue

            if should_archive_existing and not archived_existing:
                archived_existing = shared.archive_existing(
                    final, candidate_root / panel_id, "previous_backend_or_take"
                )
            normalization = normalize_panel(raw_path, final, job.get("size") or {})
            raw_size = normalization.get("source_size") or {}
            job["master_path"] = shared.rel_to_root(root, raw_path)
            job["resolution_provenance"] = {
                "requested_resolution_tier": args.resolution_type,
                "maximum_verified": args.resolution_type == "4k",
                "native_size": raw_size,
                "native_sha256": shared.file_sha256(raw_path),
                "master_path": shared.rel_to_root(root, raw_path),
                "derivative_size": normalization.get("target_size") or {},
                "normalization_scale": normalization.get("normalization_scale"),
                "upscaled": bool(normalization.get("upscaled")),
            }
            post_qc = shared.post_qc_panel(
                root,
                args.chapter,
                job,
                final,
                records,
                omitted,
                adjacent_paths=shared.previous_accepted_panel_paths(root, all_jobs, panel_id),
            )
            post_qc_verdict = str(post_qc.get("verdict") or "block")
            generated_at = dt.datetime.now().isoformat(timespec="seconds")
            status = shared.status_after_post_qc(post_qc)
            history = job.get("history") if isinstance(job.get("history"), list) else []
            if archived_existing:
                history.append({"kind": "archived_previous", "path": archived_existing})
            job.update(
                {
                    "status": status,
                    "result_path": shared.rel_to_root(root, final),
                    "source": DREAMINA_CHANNEL,
                    "model": DREAMINA_MODEL,
                    "model_version": args.model_version,
                    "generated_at": generated_at,
                    "backend_version": backend_version,
                    "artifact_sha256": shared.file_sha256(final),
                    "attempt": attempt,
                    "submit_id": submit_id,
                    "service_ratio": ratio,
                    "resolution_type": args.resolution_type,
                    "reference_input_mode": "dreamina_image2image_images",
                    "reference_input_count": len(records),
                    "reference_manifest": shared.rel_to_root(root, reference_manifest),
                    "prompt_snapshot": shared.rel_to_root(root, prompt_path),
                    "prompt_snapshot_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                    "execution_prompt_mode": prompt_mode,
                    "raw_candidate_path": shared.rel_to_root(root, raw_path),
                    "canvas_normalization": normalization,
                    "generated_from_contract_sha256": str(job.get("source_contract_sha256") or ""),
                    "generated_from_submit_prompt_sha256": str(job.get("submit_prompt_sha256") or ""),
                    "generated_from_execution_input_sha256": str(job.get("execution_input_sha256") or ""),
                    "post_qc": post_qc,
                }
            )
            if history:
                job["history"] = history[-10:]
            job.pop("error", None)
            shared.append_event(
                root,
                {
                    "ts": generated_at,
                    "panel_id": panel_id,
                    "status": status,
                    "backend": DREAMINA_CHANNEL,
                    "model": DREAMINA_MODEL,
                    "path": job["result_path"],
                    "raw_candidate_path": job["raw_candidate_path"],
                    "sha256": job["artifact_sha256"],
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "submit_id": submit_id,
                    "service_ratio": ratio,
                    "reference_manifest": job["reference_manifest"],
                    "reference_input_count": len(records),
                    "post_qc_verdict": post_qc_verdict,
                    "execution_prompt_mode": prompt_mode,
                    "duration_sec": round(time.monotonic() - started, 2),
                    "backend_version": backend_version,
                },
            )
            shared.write_json(jobs_path, data)
            if post_qc_verdict in {"pass", "warn"}:
                warning_note = (
                    f"；须在 review notes 中处置 warning codes={','.join(item['code'] for item in shared.warning_findings(post_qc))}"
                    if post_qc_verdict == "warn"
                    else ""
                )
                print(
                    f"[review-required] {panel_id} -> {job['result_path']}; machine post-QC={post_qc_verdict}，"
                    f"查看 {post_qc['visual_review_packet']['contact_sheet_path']} 后逐图签收{warning_note}；"
                    "未签收前不会生成下一张。",
                    file=sys.stderr,
                    flush=True,
                )
                return 4
            print(
                f"[qc-{post_qc_verdict}] {panel_id} -> {job['result_path']}; "
                "确定性 block 不可人工豁免，必须修复并 --force 重抽",
                file=sys.stderr,
                flush=True,
            )
            return 3
        else:
            failures += 1
            job["status"] = "failed"
            job["error"] = last_error or "generation failed"
            shared.write_json(jobs_path, data)
            print(f"[fail] {panel_id}: {job['error']}", file=sys.stderr, flush=True)
            return 1

    if shared.all_ready(root, data.get("jobs") or []):
        shared.update_stage(
            root,
            args.chapter,
            "出图",
            "✅",
            evidence=f"出图/{args.chapter}/prompt/panel_jobs.json",
            actor="comic-image.dreamina_panel_runner",
        )
    if qc_blocked:
        return 3
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
