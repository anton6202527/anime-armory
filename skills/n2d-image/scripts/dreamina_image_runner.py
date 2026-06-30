#!/usr/bin/env python3
"""Generate n2d episode images through the official Dreamina CLI.

This backend is for projects that cannot use Codex's text-only image path for
high-risk character shots.  It reuses the prompt/target/reference resolution
from ``codex_image_runner.py`` but submits real local reference images to
``dreamina image2image``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import codex_image_runner as base


SOURCE = "skills/n2d-image/scripts/dreamina_image_runner.py"
LOG_REL = Path("生产数据") / "dreamina_image_runner.jsonl"
MAX_REFERENCES = 10


def _field(body: str, label: str) -> str:
    m = re.search(rf"^\*\*{re.escape(label)}\*\*：([^\n]+)$", body, re.M)
    if not m:
        m = re.search(rf"^{re.escape(label)}：([^\n]+)$", body, re.M)
    return m.group(1).strip() if m else ""


def build_dreamina_prompt(root: Path, episode: str, target: base.Target) -> str:
    body = target.section.body
    # 画幅与风格都不写死：画幅走 _设置.md「画幅」选择点；风格继承 storyboard.json 的 style_contract，
    # 与 Codex 后端同一真值源——避免「同一部剧换渠道就换画风」（宪法 C4「标准不绑后端」）。
    style = base.style_contract_phrase(root, episode)
    parts = [
        f"{base.aspect_phrase(base.aspect_ratio(root))}，电影级光影。",
        style,
        _field(body, "正向 prompt（中文）"),
        _field(body, "锚点句"),
        _field(body, "状态锁"),
        _field(body, "近景/反打身份锁定"),
        _field(body, "视线方向"),
        _field(body, "光位锚"),
        _field(body, "关键道具结构唯一性闸门"),
    ]
    # 视线防呆 + 对撞构图：与 Codex 后端同源注入（单一真值源 codex_image_runner→n2d_const）。
    # 此前即梦后端只誊抄作者手写字段——作者漏写视线防呆，打斗镜就被渲染成正对镜头/肖像摆拍/自拍
    # （正脸定妆锚又把脸怼向镜头）。非 POV 镜统一补旁观者视线锁；POV/破第四墙/对观众压迫特写自动豁免。
    gaze_neg = base.camera_gaze_negatives_for(body)
    if gaze_neg:
        parts.append(
            "镜头为旁观者视角：角色不看镜头、不与镜头对视/eye contact，视线锁场内目标"
            "（对手 / 武器来路 / 命中点 / 对话对象 / 所视之物）；身份可辨用三分之二侧脸 / 侧脸 / 过肩 / 45°回头，"
            "不正对镜头肖像摆拍。打斗动作镜动作优先于脸。"
        )
    clash = base.weapon_clash_compose_for(body)
    if clash:
        parts.append(clash)
    # 打斗/法术/动作高潮镜：注入「经费在燃烧」视觉盛宴保底层（与 Codex 后端同源·单一真值源 n2d_const）。
    # 传本剧风格句 → cel/ink/flat 风格自动换变体，避免给赛璐璐/水墨/Q版剧硬塞写实体积光与 motion blur。
    richness = base.combat_spectacle_richness_for(body, style)
    if richness:
        parts.append(richness)
    parts.append(_field(body, "负向 prompt"))
    if gaze_neg:
        parts.append("负向：" + gaze_neg + "——不得直视镜头 / 正对镜头摆拍 / 自拍感。")
    parts.append("只输出一张正式剧情帧；禁止文字、水印、logo、漫画分格、UI边框；角色脸/妆造不得漂移，服装配色一致。")
    if target.mode == "midframe":
        parts.append("这是同 Clip 中段锚帧：以上一张首帧图生图为母图，只改中段动作/表情，不重画脸。")
    elif target.mode == "tailframe":
        parts.append("这是同 Clip 尾帧：以上一张首帧或中段锚帧图生图为母图，只改尾态动作/表情，不重画脸。")
    return "\n".join(p for p in parts if p)


def _reference_block(body: str) -> str:
    m = re.search(r"(?ms)(?:\*\*)?参考图(?:\*\*)?.*?(?=^###\s+|^\*\*导演视角八维\*\*|^##\s+|\Z)", body)
    return m.group(0) if m else ""


def prompt_reference_paths(root: Path, target: base.Target, episode: str) -> List[Path]:
    paths: List[Path] = []
    seen: set[Path] = set()

    def add(rel: str) -> None:
        text = rel.strip().strip("`")
        if not text.startswith("出图/"):
            return
        path = root / text
        if path in seen or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            return
        if not path.is_file():
            return
        seen.add(path)
        paths.append(path)

    if target.mode != "firstframe":
        try:
            source = root / base.target_for_shot(target.clip, target.section, episode).rel_path
            if source.is_file():
                seen.add(source)
                paths.append(source)
        except Exception:
            pass

    block = _reference_block(target.section.body)
    for raw in base.backticked(block):
        add(raw)

    # Always merge the registry-resolved bundle (not only when prose is empty):
    # a hand-written 参考图 block listing any one placeholder image must NOT
    # suppress the carried-identity face anchors — that was the Dreamina-side
    # replica of the 定妆 face-drift bug. Character (carried-identity) face anchors
    # are prepended so they survive the MAX_REFERENCES cap; everything else appends.
    bundle = base.reference_bundle_for_target(root, episode, target)
    face_first: List[Path] = []
    for item in bundle.get("items") or []:
        if str(item.get("kind")) != "character":
            continue
        for rel in item.get("paths") or []:
            p = root / str(rel)
            if p.is_file() and p not in seen and p not in face_first:
                face_first.append(p)
    paths = face_first + [p for p in paths if p not in face_first]
    for item in bundle.get("items") or []:
        if str(item.get("kind")) == "character":
            continue
        for rel in item.get("paths") or []:
            add(str(rel))

    return paths[:MAX_REFERENCES]


def submit_id_from(text: str) -> str:
    patterns = [
        r'"submit_id"\s*:\s*"([^"]+)"',
        r"submit_id\s*[=:]\s*([A-Za-z0-9._-]+)",
        r"submit id\s*[=:]\s*([A-Za-z0-9._-]+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(1)
    return ""


def image_candidates(path: Path) -> List[Path]:
    if not path.is_dir():
        return []
    candidates: List[Path] = []
    for suffix in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        candidates.extend(path.rglob(suffix))
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates


def materialize_png(src: Path, out_path: Path) -> bool:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".png":
        shutil.copy2(src, out_path)
        return base.png_valid(out_path)
    proc = subprocess.run(
        ["sips", "-s", "format", "png", str(src), "--out", str(out_path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.returncode == 0 and base.png_valid(out_path)


def run_dreamina(
    target: base.Target,
    *,
    root: Path,
    episode: str,
    temp_path: Path,
    timeout_sec: Optional[float],
    poll_sec: int,
    model_version: str,
    resolution_type: str,
) -> tuple[bool, str, str, List[Path]]:
    refs = prompt_reference_paths(root, target, episode)
    if not refs:
        return False, "", "no ready reference images resolved for Dreamina image2image", refs
    prompt = build_dreamina_prompt(root, episode, target)
    ratio = base.aspect_ratio(root)
    download_dir = temp_path.parent / f"{temp_path.stem}_download"
    if download_dir.exists():
        shutil.rmtree(download_dir)
    download_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "dreamina",
        "image2image",
        "--images",
        ",".join(str(p) for p in refs),
        "--prompt",
        prompt,
        "--ratio",
        ratio,
        "--poll",
        str(max(0, min(poll_sec, int(timeout_sec or poll_sec)))),
    ]
    if model_version:
        cmd.extend(["--model_version", model_version])
    if resolution_type:
        cmd.extend(["--resolution_type", resolution_type])
    proc = subprocess.run(
        cmd,
        stdin=subprocess.DEVNULL,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout_sec,
    )
    combined = "\n".join(p for p in (proc.stdout, proc.stderr) if p)
    if proc.returncode != 0:
        return False, "", f"dreamina image2image exit {proc.returncode}: {combined}", refs
    sid = submit_id_from(combined)
    if not sid:
        return False, "", f"dreamina output did not include submit_id: {combined[:1000]}", refs
    query = subprocess.run(
        ["dreamina", "query_result", "--submit_id", sid, "--download_dir", str(download_dir)],
        stdin=subprocess.DEVNULL,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout_sec,
    )
    qout = "\n".join(p for p in (query.stdout, query.stderr) if p)
    if query.returncode != 0:
        return False, sid, f"dreamina query_result exit {query.returncode}: {qout}", refs
    candidates = image_candidates(download_dir)
    if not candidates:
        return False, sid, f"dreamina query_result downloaded no image files: {qout[:1000]}", refs
    if not materialize_png(candidates[0], temp_path):
        return False, sid, f"downloaded result is not a valid PNG and conversion failed: {candidates[0]}", refs
    return True, sid, "", refs


def archive_existing(root: Path, rel_path: str, task_id: str) -> Optional[Path]:
    final = root / rel_path
    if not final.exists():
        return None
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = root / "废料" / "出图" / rel_path.replace("出图/", "").rsplit("/", 1)[0] / f"dreamina_rerun_{task_id}_{stamp}"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / final.name
    shutil.copy2(final, archive_path)
    return archive_path


def append_log(root: Path, row: dict) -> None:
    path = root / LOG_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def record_event(
    root: Path,
    episode: str,
    target: base.Target,
    *,
    status: str,
    duration_sec: float,
    task_id: str,
    seed: str,
    temp_path: Path,
    submit_id: str,
    refs: List[Path],
    archive_path: Optional[Path],
    error: str = "",
) -> None:
    event = "redraw" if archive_path or os.environ.get("N2D_REASON") == "rerun" else "generation"
    cmd = [
        sys.executable,
        str(base.repo_root() / base.DASHBOARD),
        "record",
        str(root),
        "--episode",
        episode,
        "--stage",
        "image",
        "--event",
        event,
        "--asset",
        target.rel_path,
        "--status",
        status,
        "--provider",
        "Dreamina",
        "--duration-sec",
        f"{duration_sec:.3f}",
        "--unit",
        "credits",
        "--meta",
        f"mode=dreamina_image2image_{target.mode}",
        "--meta",
        f"task={task_id}",
        "--meta",
        f"shot={target.shot}",
        "--meta",
        f"submit_id={submit_id}",
        "--meta",
        f"requested_seed={seed}",
        "--meta",
        "effective_seed=",
        "--meta",
        "seed_effective=false",
        "--meta",
        "seed_support=unsupported_or_unknown",
        "--meta",
        "seed_strategy=fixed_pool",
        "--meta",
        f"reference_count={len(refs)}",
        "--meta",
        f"temp_output={temp_path}",
        "--meta",
        f"source={SOURCE}",
    ]
    for ref in refs[:MAX_REFERENCES]:
        try:
            rel = ref.relative_to(root)
        except ValueError:
            rel = ref
        cmd.extend(["--meta", f"reference={rel}"])
    if archive_path:
        cmd.extend(["--redraw-reason", f"{task_id} Dreamina image2image 真实参考图重出 {target.shot}", "--redraw-category", "backend_migration"])
        cmd.extend(["--meta", f"archived_previous={archive_path}"])
    if error:
        cmd.extend(["--meta", f"error={error[:500]}"])
    subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def latest_recorded_status(root: Path, task_id: str, rel_path: str) -> str:
    path = root / "生产数据" / "production_events.jsonl"
    if not path.is_file():
        return ""
    status = ""
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("stage") != "image":
                continue
            generation = event.get("generation")
            meta = event.get("meta")
            if not isinstance(generation, dict) or not isinstance(meta, dict):
                continue
            if generation.get("asset") == rel_path and str(meta.get("task") or "") == task_id:
                status = str(generation.get("status") or "")
    return status.lower()


def process_target(
    root: Path,
    episode: str,
    target: base.Target,
    *,
    task_id: str,
    timeout_sec: Optional[float],
    poll_sec: int,
    model_version: str,
    resolution_type: str,
    dry_run: bool,
    force: bool,
) -> bool:
    seed = base.logical_seed(root, episode, target.shot, target.rel_path)
    final = root / target.rel_path
    temp_dir = Path(tempfile.gettempdir()) / "n2d_dreamina_image_runner" / (task_id or "manual")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{episode}_{base.temp_token(target.shot)}_{Path(target.rel_path).stem}.png"
    previous_status = latest_recorded_status(root, task_id, target.rel_path)
    refs = prompt_reference_paths(root, target, episode)
    if dry_run:
        print(json.dumps({
            "shot": target.shot,
            "mode": target.mode,
            "target": target.rel_path,
            "references": [str(p) for p in refs],
            "reference_count": len(refs),
            "logical_seed": seed,
            "skip_existing_pass": (not force and previous_status == "pass" and base.png_valid(final)),
        }, ensure_ascii=False))
        return True
    if not force and previous_status == "pass" and base.png_valid(final):
        print(f"[skip] {target.shot} already has Dreamina pass record for {task_id}: {target.rel_path}")
        return True

    # Pre-spend interlock (same as the Codex backend): a plate that depicts a
    # character must attach a real face anchor, else it renders a new drifting face.
    bundle = base.reference_bundle_for_target(root, episode, target)
    attached_rel: List[str] = []
    for p in refs:
        try:
            attached_rel.append(str(p.relative_to(root)))
        except ValueError:
            attached_rel.append(str(p))
    if (
        base.carried_identity_unanchored(bundle, attached_rel)
        and os.environ.get("N2D_ALLOW_UNANCHORED_IDENTITY_PLATE") != "1"
    ):
        carried = "、".join(str(c) for c in bundle.get("carried_identity") or [])
        print(
            f"[fail] {target.shot}: 本图声明承载角色身份（carries_identity={carried}），"
            "但没有任何角色脸锚作为 Dreamina image2image 参考传入——会另画一张新脸（定妆脸漂成因）。"
            "请把承载角色的脸部特写/正面参考置 ready，或设 N2D_ALLOW_UNANCHORED_IDENTITY_PLATE=1 显式豁免。",
            file=sys.stderr,
        )
        base.log_unanchored_friction(root, episode, target.shot, bundle.get("carried_identity"), "Dreamina")
        return False

    started = time.monotonic()
    archive_path: Optional[Path] = None
    submit_id = ""
    error = ""
    ok = False
    try:
        if temp_path.exists():
            temp_path.unlink()
        ok, submit_id, error, refs = run_dreamina(
            target,
            root=root,
            episode=episode,
            temp_path=temp_path,
            timeout_sec=timeout_sec,
            poll_sec=poll_sec,
            model_version=model_version,
            resolution_type=resolution_type,
        )
        if ok:
            archive_path = archive_existing(root, target.rel_path, task_id)
            final.parent.mkdir(parents=True, exist_ok=True)
            os.replace(temp_path, final)
            ok = base.png_valid(final)
            if not ok:
                error = f"moved Dreamina output is not a valid PNG: {final}"
    except subprocess.TimeoutExpired:
        error = f"dreamina timed out after {timeout_sec}s"
    except Exception as exc:  # pragma: no cover
        error = f"{type(exc).__name__}: {exc}"

    duration = time.monotonic() - started
    record_event(
        root,
        episode,
        target,
        status="pass" if ok else "fail",
        duration_sec=duration,
        task_id=task_id,
        seed=seed,
        temp_path=temp_path,
        submit_id=submit_id,
        refs=refs,
        archive_path=archive_path,
        error=error,
    )
    append_log(root, {
        "ts": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "episode": episode,
        "shot": target.shot,
        "mode": target.mode,
        "target": target.rel_path,
        "status": "pass" if ok else "fail",
        "duration_sec": round(duration, 3),
        "submit_id": submit_id,
        "reference_count": len(refs),
        "logical_seed": seed,
        "seed_effective": False,
        "error": error[:1000],
    })
    if ok:
        print(f"[pass] {target.shot} -> {target.rel_path} ({submit_id})")
    else:
        print(f"[fail] {target.shot}: {error}", file=sys.stderr)
    return ok


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Dreamina official CLI image2image adapter for n2d image tasks")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--shots", default=os.environ.get("N2D_AFFECTED_SHOTS", ""))
    ap.add_argument("--max-shots", type=int)
    ap.add_argument("--timeout-sec", type=float, default=float(os.environ.get("N2D_DREAMINA_IMAGE_TIMEOUT", "900")))
    ap.add_argument("--poll-sec", type=int, default=int(os.environ.get("N2D_DREAMINA_IMAGE_POLL", "300")))
    ap.add_argument("--model-version", default=os.environ.get("N2D_DREAMINA_IMAGE_MODEL", "5.0"))
    ap.add_argument("--resolution-type", default=os.environ.get("N2D_DREAMINA_IMAGE_RESOLUTION", "2k"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stop-on-fail", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skip-image-qc", action="store_true")
    ap.add_argument("--skip-final-gate", action="store_true")
    ap.add_argument("--skip-preflight", action="store_true", help="skip the pre-spend image_preflight gate (logs a dashboard waiver)")
    return ap


def main(argv: Sequence[str]) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root).resolve()
    episode = base.normalize_episode(ns.episode)
    shots = base.split_csv(ns.shots)
    if not shots:
        raise SystemExit("--shots or N2D_AFFECTED_SHOTS is required")
    if ns.max_shots is not None:
        shots = shots[: ns.max_shots]
    targets = base.build_targets(root, episode, shots)
    if not targets:
        raise SystemExit("no targets resolved")
    task_id = os.environ.get("N2D_TASK_ID") or f"dreamina-{episode}"

    # Non-waivable ordering lock shared with codex_image_runner: --skip-preflight
    # cannot spend on Clip PNGs before the episode shared library is complete.
    if not ns.dry_run and not base.enforce_shared_first_interlock(root, episode):
        return 1

    # Pre-spend interlock: 生成前先跑 image_preflight 硬闸门，block 即拒绝生成不花钱；
    # 逃生口 --skip-preflight 留痕成 dashboard waiver（与 codex_image_runner 同源）。
    if not ns.dry_run:
        if ns.skip_preflight:
            base.record_waiver(root, episode, "image_preflight", "skip-preflight",
                               "operator passed --skip-preflight; pre-spend image_preflight gate not run")
        elif not base.run_image_gate(root, episode, stage="image_preflight"):
            print("[gate] image_preflight blocked — refusing to spend on generation; fix upstream or pass --skip-preflight", file=sys.stderr)
            return 1

    ok_all = True
    for target in targets:
        ok = process_target(
            root,
            episode,
            target,
            task_id=task_id,
            timeout_sec=ns.timeout_sec,
            poll_sec=ns.poll_sec,
            model_version=ns.model_version,
            resolution_type=ns.resolution_type,
            dry_run=ns.dry_run,
            force=ns.force,
        )
        if ok and not ns.dry_run and not ns.skip_image_qc:
            ok = base.run_target_image_qc(root, episode, target)
        ok_all = ok_all and ok
        if not ok and ns.stop_on_fail:
            break
    if ns.skip_image_qc and not ns.dry_run:
        base.record_waiver(root, episode, "image", "skip-image-qc",
                           "operator passed --skip-image-qc; per-target landed-frame QC not run")
    if ok_all and not ns.dry_run:
        if ns.skip_final_gate:
            base.record_waiver(root, episode, "image", "skip-final-gate",
                               "operator passed --skip-final-gate; whole-episode image gate not run")
        else:
            ok_all = base.run_image_gate(root, episode)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
