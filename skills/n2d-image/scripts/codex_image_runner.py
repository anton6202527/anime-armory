#!/usr/bin/env python3
"""Generate n2d episode images through Codex's image_generation feature.

This is the Codex backend adapter used by N2D_IMAGE_COMMAND.  It keeps the
batch wrapper backend-agnostic while giving Codex a real PNG-producing path:

1. Parse the episode prompt pack.
2. Ask ``codex exec --enable image_generation`` to generate one target image.
3. Require a valid PNG at a temporary path.
4. Archive the old target, move the new PNG into place, and record dashboard
   telemetry including the seed downgrade status.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence


PROMPT_REL = Path("出图") / "{episode}" / "prompt" / "01_分镜出图.md"
DASHBOARD = Path("skills") / "n2d-dashboard" / "scripts" / "dashboard.py"
SOURCE = "skills/n2d-image/scripts/codex_image_runner.py"


@dataclass
class ClipSection:
    clip: str
    title: str
    body: str
    target_line: str


@dataclass
class Target:
    shot: str
    clip: str
    mode: str
    rel_path: str
    section: ClipSection


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def normalize_episode(value: str) -> str:
    text = str(value).strip()
    if re.fullmatch(r"\d+", text):
        return f"第{text}集"
    return text


def split_csv(value: str) -> List[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def rel_to_root(path: str, episode: str) -> str:
    text = path.strip().strip("`")
    if not text:
        return text
    if text.startswith("出图/"):
        return text
    if "/" in text:
        return text
    return str(Path("出图") / episode / "图片" / text)


def first_backticked(text: str) -> Optional[str]:
    match = re.search(r"`([^`]+)`", text)
    return match.group(1) if match else None


def backticked(text: str) -> List[str]:
    return re.findall(r"`([^`]+)`", text)


def load_sections(root: Path, episode: str) -> List[ClipSection]:
    prompt_path = root / str(PROMPT_REL).format(episode=episode)
    if not prompt_path.is_file():
        raise FileNotFoundError(f"prompt pack not found: {prompt_path}")
    text = prompt_path.read_text(encoding="utf-8")
    headers = list(re.finditer(r"^##\s+(Clip\s+\d+)[^\n]*$", text, re.M))
    sections: List[ClipSection] = []
    for index, header in enumerate(headers):
        start = header.start()
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        body = text[start:end].strip()
        title = header.group(0).strip()
        clip_num = re.search(r"Clip\s+(\d+)", header.group(1))
        if not clip_num:
            continue
        clip = f"Clip_{int(clip_num.group(1)):02d}"
        target_match = re.search(r"^\*\*目标\*\*：([^\n]+)$", body, re.M)
        target_line = target_match.group(1).strip() if target_match else ""
        sections.append(ClipSection(clip=clip, title=title, body=body, target_line=target_line))
    return sections


def section_for(sections: Sequence[ClipSection], shot: str) -> ClipSection:
    match = re.search(r"Clip_(\d+)", shot)
    if not match:
        raise ValueError(f"invalid shot name: {shot}")
    clip = f"Clip_{int(match.group(1)):02d}"
    for section in sections:
        if section.clip == clip:
            return section
    raise ValueError(f"no prompt section found for {shot}")


def target_for_shot(shot: str, section: ClipSection, episode: str) -> Target:
    line = section.target_line
    if not line:
        raise ValueError(f"{section.clip}: target line missing")

    if shot.endswith("_end"):
        tail = re.search(r"尾帧[^：]*：([^；\n]+)", line)
        if not tail:
            raise ValueError(f"{shot}: tail-frame target missing")
        path = first_backticked(tail.group(1))
        if not path:
            raise ValueError(f"{shot}: tail-frame target is not a file path ({tail.group(1).strip()})")
        return Target(shot=shot, clip=section.clip, mode="tailframe", rel_path=rel_to_root(path, episode), section=section)

    anchor_suffix = re.search(r"_(first_(?:mid|a\d+))$", shot)
    if anchor_suffix:
        wanted = f"{shot}.png"
        anchors = re.search(r"中锚：([^；\n]+)", line)
        for item in backticked(anchors.group(1) if anchors else ""):
            if Path(item).name == wanted:
                return Target(shot=shot, clip=section.clip, mode="midframe", rel_path=rel_to_root(item, episode), section=section)
        raise ValueError(f"{shot}: mid/anchor target missing")

    first = first_backticked(line)
    if not first:
        raise ValueError(f"{shot}: first-frame target missing")
    return Target(shot=shot, clip=section.clip, mode="firstframe", rel_path=rel_to_root(first, episode), section=section)


def logical_seed(root: Path, episode: str, shot: str, rel_path: str) -> str:
    data = f"{root.name}|{episode}|{shot}|{rel_path}".encode("utf-8")
    return str(1000 + int(hashlib.sha1(data).hexdigest()[:8], 16) % 9000)


def png_valid(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 32:
        return False
    with path.open("rb") as fh:
        return fh.read(8) == b"\x89PNG\r\n\x1a\n"


def brief_context(path: Path, limit: int = 1800) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    return text[:limit]


def build_codex_prompt(root: Path, episode: str, target: Target, temp_path: Path, seed: str) -> str:
    overview = brief_context(root / "出图" / episode / "prompt" / "00_总览.md")
    registry = root / "出图" / "共享" / "identity_registry.json"
    assets = root / "出图" / "共享" / "asset_registry.json"
    state = root / "出图" / "共享" / "visual_state_ledger.json"
    final_path = root / target.rel_path
    source_for_tail = root / target.rel_path
    if target.mode != "firstframe":
        source_for_tail = root / target_for_shot(target.clip, target.section, episode).rel_path

    return f"""你正在为 N2D 项目生成正式分镜 PNG。必须使用内置 AI 生图能力（imagegen/image_generation），不要用 Python/SVG/canvas/纯色图/占位图伪造。

输出要求：
- 只生成 1 张 9:16 竖版电影感 PNG。
- 先生成到临时文件：{temp_path}
- 生成后必须确认这个临时文件存在且是 PNG。不要直接覆盖正式文件。
- 禁止水印、字幕、logo、文字、漫画分格、UI 边框。

一致性硬约束：
- 角色 DNA = 脸 + 发型 + 服装 + 配饰。不要只锁脸。
- 近景优先参考“脸部特写 + 半身”，全身/三视图只作服装结构辅助。
- 多人同框必须按 prompt 的 blocking 分层理解，避免串脸。
- 这是 Codex 后端：没有公开 seed API。逻辑 seed/连续性 token 仅用于追踪：{seed}，不要声称这是可复现 seed。

项目根：{root}
集数：{episode}
shot：{target.shot}
生成模式：{target.mode}
正式目标：{final_path}
可读注册表：
- identity_registry: {registry}
- asset_registry: {assets}
- visual_state_ledger: {state}
{"尾帧/中段可参考已有源图：" + str(source_for_tail) if target.mode != "firstframe" else ""}

本集总览节选：
{overview}

本镜完整 prompt 区块：
{target.section.body}

执行方式：
1. 读取/参考 prompt 中列出的参考图；如果同一角色有脸部特写和半身，优先使用它们。
2. 根据本镜中文正向 prompt 与负向 prompt 生成画面。
3. 把最终 PNG 保存/复制到临时文件路径：{temp_path}
4. 只要无法生成真实 PNG，就不要创建任何替代文件，直接说明失败。
"""


def run_codex(repo: Path, prompt: str, timeout_sec: Optional[float]) -> subprocess.CompletedProcess[str]:
    cmd = ["codex", "exec", "--enable", "image_generation", "-C", str(repo), prompt]
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout_sec,
    )


def archive_existing(root: Path, rel_path: str, task_id: str) -> Optional[Path]:
    final = root / rel_path
    if not final.exists():
        return None
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = root / "废料" / "出图" / rel_path.replace("出图/", "").rsplit("/", 1)[0] / f"codex_rerun_{task_id}_{stamp}"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / final.name
    shutil.copy2(final, archive_path)
    return archive_path


def record_event(
    root: Path,
    episode: str,
    target: Target,
    *,
    status: str,
    duration_sec: float,
    task_id: str,
    seed: str,
    temp_path: Path,
    archive_path: Optional[Path] = None,
    error: str = "",
) -> None:
    event = "redraw" if os.environ.get("N2D_REASON") == "rerun" else "generation"
    reason = f"{task_id or 'codex-image'} Codex image_generation 真实重出 {target.shot}，禁止本地贴脸修复"
    category = "face_consistency" if event == "redraw" else ""
    cmd = [
        sys.executable,
        str(repo_root() / DASHBOARD),
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
        "Codex",
        "--duration-sec",
        f"{duration_sec:.3f}",
        "--unit",
        "credits",
        "--meta",
        f"mode=codex_exec_image_generation_{target.mode}",
        "--meta",
        f"task={task_id}",
        "--meta",
        f"shot={target.shot}",
        "--meta",
        f"logical_seed={seed}",
        "--meta",
        "seed_effective=unsupported",
        "--meta",
        "seed_degrade=codex_exec_no_seed_api",
        "--meta",
        f"temp_output={temp_path}",
        "--meta",
        f"source={SOURCE}",
    ]
    if event == "redraw":
        cmd.extend(["--redraw-reason", reason, "--redraw-category", category])
    if archive_path:
        cmd.extend(["--meta", f"archived_previous={archive_path}"])
    if error:
        cmd.extend(["--meta", f"error={error[:500]}"])
    subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def append_log(root: Path, row: dict) -> None:
    path = root / "生产数据" / "codex_image_runner.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def latest_recorded_status(root: Path, task_id: str, rel_path: str) -> str:
    path = root / "生产数据" / "production_events.jsonl"
    if not path.is_file():
        return ""
    status = ""
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
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
    target: Target,
    *,
    task_id: str,
    timeout_sec: Optional[float],
    dry_run: bool,
    force: bool,
) -> bool:
    seed = logical_seed(root, episode, target.shot, target.rel_path)
    final = root / target.rel_path
    temp_dir = Path(tempfile.gettempdir()) / "n2d_codex_image_runner" / (task_id or "manual")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{episode}_{target.shot}_{Path(target.rel_path).stem}.png"
    if temp_path.exists():
        temp_path.unlink()

    previous_status = latest_recorded_status(root, task_id, target.rel_path)
    if not force and previous_status == "pass" and png_valid(final):
        if dry_run:
            skipped = True
        else:
            print(f"[skip] {target.shot} already has pass record for {task_id}: {target.rel_path}")
            append_log(root, {
                "ts": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
                "episode": episode,
                "shot": target.shot,
                "mode": target.mode,
                "target": target.rel_path,
                "status": "skip_pass_recorded",
                "logical_seed": seed,
                "seed_effective": "unsupported",
            })
            return True
    else:
        skipped = False

    if dry_run:
        print(json.dumps({
            "shot": target.shot,
            "mode": target.mode,
            "target": target.rel_path,
            "temp": str(temp_path),
            "logical_seed": seed,
            "skip_existing_pass": skipped,
        }, ensure_ascii=False))
        return True

    prompt = build_codex_prompt(root, episode, target, temp_path, seed)
    started = time.monotonic()
    error = ""
    archive_path: Optional[Path] = None
    ok = False
    try:
        proc = run_codex(repo_root(), prompt, timeout_sec)
        if proc.returncode != 0:
            error = f"codex exit {proc.returncode}: {proc.stderr or proc.stdout}"
        elif not png_valid(temp_path):
            error = f"codex completed but valid PNG missing at {temp_path}"
        else:
            archive_path = archive_existing(root, target.rel_path, task_id)
            final.parent.mkdir(parents=True, exist_ok=True)
            os.replace(temp_path, final)
            ok = png_valid(final)
            if not ok:
                error = f"moved output is not a valid PNG: {final}"
    except subprocess.TimeoutExpired:
        error = f"codex timed out after {timeout_sec}s"
    except Exception as exc:  # pragma: no cover - defensive batch guard
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
        "logical_seed": seed,
        "seed_effective": "unsupported",
        "archive": str(archive_path) if archive_path else "",
        "error": error[:1000],
    })
    if ok:
        print(f"[pass] {target.shot} -> {target.rel_path}")
    else:
        print(f"[fail] {target.shot}: {error}", file=sys.stderr)
    return ok


def build_targets(root: Path, episode: str, shots: Iterable[str]) -> List[Target]:
    sections = load_sections(root, episode)
    targets: List[Target] = []
    seen = set()
    for shot in shots:
        section = section_for(sections, shot)
        target = target_for_shot(shot, section, episode)
        key = target.rel_path
        if key not in seen:
            seen.add(key)
            targets.append(target)
    return targets


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Codex image_generation adapter for n2d image tasks")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--shots", default=os.environ.get("N2D_AFFECTED_SHOTS", ""))
    ap.add_argument("--max-shots", type=int)
    ap.add_argument("--timeout-sec", type=float, default=float(os.environ.get("N2D_CODEX_IMAGE_TIMEOUT", "900")))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stop-on-fail", action="store_true")
    ap.add_argument("--force", action="store_true", help="regenerate even when this task already has a pass event for the asset")
    return ap


def main(argv: Sequence[str]) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root).resolve()
    episode = normalize_episode(ns.episode)
    shots = split_csv(ns.shots)
    if not shots:
        raise SystemExit("--shots or N2D_AFFECTED_SHOTS is required")
    if ns.max_shots is not None:
        shots = shots[: ns.max_shots]
    task_id = os.environ.get("N2D_TASK_ID") or f"manual-{episode}"
    targets = build_targets(root, episode, shots)
    if not targets:
        raise SystemExit("no targets resolved")

    ok_all = True
    for target in targets:
        ok = process_target(
            root,
            episode,
            target,
            task_id=task_id,
            timeout_sec=ns.timeout_sec,
            dry_run=ns.dry_run,
            force=ns.force,
        )
        ok_all = ok_all and ok
        if not ok and ns.stop_on_fail:
            break
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
