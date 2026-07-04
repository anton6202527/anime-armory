#!/usr/bin/env python3
"""帧插值「后期 pass」落地器（P1b·补 n2d-video 唯一明显能力空缺：流水线内无任何插帧）。

现状：n2d-video 的 fps 提升与平滑**完全依赖后端原生 multiframe / 首尾帧焊接**，流水线里没有任何
RIFE/FILM 式插帧后处理（唯一后处理是 `lipsync_pass`）。两个真实用途此前无落点：
  (a) **只能首帧/首尾帧的后端**（Seedance 直连 / Sora / Runway / Pika）出的镜运动不够稠 → 事后补帧，
      把它们也拉到接近三帧多关键帧的平滑度；
  (b) **fps 提帧**（24→48/60，或 `出视频规格` 升档）——后端只出 24fps 时本地提帧补足交付帧率。

设计同 `lipsync_pass` / `motion_control`：
  plan（默认 report-only）：扫 `出视频/<集>/视频/*.mp4`，ffprobe 探源 fps（无 ffprobe 则标 unknown），
        读 `出视频规格` 目标 fps（或 --target-fps），结合 `video_model_routes.json` 后端能力判定每个 clip
        是否该插帧（源 fps < 目标 fps，或 first-frame-only 后端镜补运动平滑），写
        `出视频/<集>/control/interp_jobs.json` 作业清单 + 工具可用性探针 + 手工指引。
  --apply：检测到本地插帧后端可用（`N2D_INTERP_CMD` 命令模板，或 RIFE/FILM CLI 经 env，或 ffmpeg
        minterpolate 兜底）时逐 clip 执行，产 `视频/<clip>_interp.mp4`；都不可用 → 只落清单 + 打印手工
        指引，**绝不静默跳过/不臆造成功**。

铁律：插帧**只补帧不改内容/不改声音**（成片音轨仍走 voice-first 配音轨）；插出的帧是合成中间帧，
若后端原生多关键帧已够稠（≥3帧契约已满足且 fps 达标）则**不插**（避免过度平滑的「肥皂剧感」）。

纯规划逻辑（fps 解析/是否需插/输出命名/挑镜）无依赖、带 pytest；重型 CLI 调用 env 门控、降级成清单。

用法：
  python3 interp_pass.py <作品根> 第N集                  # 规划（report-only，写 interp_jobs.json）
  python3 interp_pass.py <作品根> 第N集 --json
  python3 interp_pass.py <作品根> 第N集 --target-fps 48
  python3 interp_pass.py <作品根> 第N集 --apply           # 工具可用则执行，否则降级清单
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

_LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)
try:
    from n2d_platform_profiles import backend_supports_three_plus_frames, normalize_video_backend
except Exception:  # pragma: no cover - 异常布局兜底
    def backend_supports_three_plus_frames(backend, channel=None):  # type: ignore
        return True

    def normalize_video_backend(v, default="dreamina"):  # type: ignore
        return str(v or default)

# 目标 fps 默认：`出视频规格` 三档（预算充足 30 / 一般 24-30 / 不够 24）。插帧默认目标取 30
# （交付常用），可经 --target-fps / `出视频规格` 覆盖。低于此且差距显著(≥1.2×)的镜才值得插。
DEFAULT_TARGET_FPS = 30.0
# 源 fps 与目标差距阈值：<目标/1.2 才插（24→30 是 1.25× 值得；29.97→30 不值得）。
INTERP_RATIO_FLOOR = 1.2
SPEC_TARGET_FPS = {"预算充足": 30.0, "预算一般": 30.0, "预算不够": 24.0}


# ── 纯函数（无依赖·可测） ──────────────────────────────────────────────────────

def parse_fps(raw: Any) -> Optional[float]:
    """ffprobe r_frame_rate（如 "30000/1001" / "24/1" / "25"）→ float；解析不出 → None。纯函数·可测。"""
    s = str(raw or "").strip()
    if not s or s in ("0/0", "N/A"):
        return None
    try:
        if "/" in s:
            num, den = s.split("/", 1)
            den_f = float(den)
            return float(num) / den_f if den_f else None
        return float(s)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def needs_interpolation(source_fps: Optional[float], target_fps: float,
                        first_frame_only: bool, ratio_floor: float = INTERP_RATIO_FLOOR
                        ) -> Tuple[bool, str]:
    """该 clip 是否值得插帧 + 理由（纯函数·可测）。

    - 源 fps 已知且 < target/ratio_floor → 插（fps 提帧）；
    - first-frame-only 后端 且 源 fps 未知/不足 → 插（补运动平滑，这类后端运动稠度先天弱）；
    - 源 fps 已达标 → 不插（避免过度平滑）；源未知且非弱后端 → 不插（不臆造，标 unknown 交人判）。"""
    if source_fps is not None and source_fps < target_fps / ratio_floor:
        return True, f"源 fps {source_fps:.3g} < 目标 {target_fps:.3g}/{ratio_floor}（fps 提帧）"
    if first_frame_only:
        if source_fps is None:
            return True, "first-frame-only 后端镜：源 fps 未知，补运动平滑（这类后端运动稠度先天弱）"
        if source_fps < target_fps:
            return True, f"first-frame-only 后端镜：源 fps {source_fps:.3g} < 目标 {target_fps:.3g}，补平滑"
        return False, f"first-frame-only 但源 fps {source_fps:.3g} 已达标，不插"
    if source_fps is None:
        return False, "源 fps 未知且非弱后端：标 unknown 交人判，不臆造插帧"
    return False, f"源 fps {source_fps:.3g} 已达标，不插（避免过度平滑肥皂剧感）"


def interp_output_name(video_rel: str) -> str:
    """clip mp4 → 插帧产物名（同目录 `_interp.mp4`）。纯函数·可测。"""
    if video_rel.lower().endswith(".mp4"):
        return video_rel[:-4] + "_interp.mp4"
    return video_rel + "_interp.mp4"


def _route_backend_map(routes: Sequence[Mapping[str, Any]]) -> Dict[str, str]:
    """clip_id → primary_backend（规范名）。纯函数·可测。"""
    out: Dict[str, str] = {}
    for r in routes or []:
        if not isinstance(r, Mapping):
            continue
        cid = str(r.get("clip_id") or r.get("id") or "").strip()
        if cid:
            out[cid] = normalize_video_backend(r.get("primary_backend") or "")
    return out


def clip_id_from_filename(name: str) -> str:
    """视频文件名 → clip_id（取 `Clip_NN` 段；取不到回退去扩展名的基名）。纯函数·可测。"""
    import re
    m = re.search(r"(?i)clip[_\s-]*0*(\d+)", name)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    return os.path.splitext(os.path.basename(name))[0]


def build_job(clip_id: str, video_rel: str, source_fps: Optional[float], target_fps: float,
              backend: str, first_frame_only: bool, reason: str) -> Dict[str, Any]:
    """单 clip 插帧作业条目（纯字典构造·可测）。"""
    return {
        "clip_id": clip_id,
        "video": video_rel,
        "output": interp_output_name(video_rel),
        "source_fps": source_fps,
        "target_fps": target_fps,
        "backend": backend,
        "first_frame_only": first_frame_only,
        "reason": reason,
    }


# ── I/O + 后端探针（best-effort） ──────────────────────────────────────────────

def _ffprobe_fps(video_abspath: str) -> Optional[float]:
    """ffprobe 探 r_frame_rate；无 ffprobe / 失败 → None（不阻断，标 unknown）。"""
    if not _which("ffprobe"):
        return None
    try:
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=r_frame_rate", "-of", "default=nokey=1:noprint_wrappers=1", video_abspath],
            capture_output=True, text=True, timeout=30)
    except Exception:
        return None
    return parse_fps(res.stdout) if res.returncode == 0 else None


def _which(cmd: str) -> bool:
    import shutil
    return shutil.which(cmd) is not None


def _ffmpeg_has_minterpolate() -> bool:
    """本机 ffmpeg 是否带 minterpolate 滤镜（本仓 ffmpeg 为精简构建，可能没有）。"""
    if not _which("ffmpeg"):
        return False
    try:
        res = subprocess.run(["ffmpeg", "-hide_banner", "-filters"],
                             capture_output=True, text=True, timeout=30)
    except Exception:
        return False
    return "minterpolate" in (res.stdout or "")


def probe_backends() -> Dict[str, Any]:
    """插帧后端可用性探针（不执行，只报）。优先序：N2D_INTERP_CMD > RIFE/FILM(env) > ffmpeg minterpolate。"""
    cmd_tmpl = os.environ.get("N2D_INTERP_CMD", "").strip()
    rife = os.environ.get("N2D_RIFE_CMD", "").strip()
    film = os.environ.get("N2D_FILM_CMD", "").strip()
    minterp = _ffmpeg_has_minterpolate()
    available = bool(cmd_tmpl) or bool(rife) or bool(film) or minterp
    chosen = ("N2D_INTERP_CMD" if cmd_tmpl else "RIFE" if rife else "FILM" if film
              else "ffmpeg_minterpolate" if minterp else None)
    return {"available": available, "chosen": chosen,
            "N2D_INTERP_CMD": bool(cmd_tmpl), "rife": bool(rife), "film": bool(film),
            "ffmpeg_minterpolate": minterp}


def _load_routes(root: str, ep: str) -> List[Dict[str, Any]]:
    p = os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json")
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    routes = data.get("routes") if isinstance(data, dict) else data
    return [r for r in (routes or []) if isinstance(r, dict)]


def _get_setting(root: str, key: str, default: str = "") -> str:
    try:
        from n2d_settings import get_setting  # type: ignore
        return str(get_setting(root, key, default) or default)
    except Exception:
        try:
            import re
            text = open(os.path.join(root, "_设置.md"), encoding="utf-8").read()
            m = re.search(rf"{re.escape(key)}[：:]\s*([^\n（(]+)", text)
            return m.group(1).strip() if m else default
        except Exception:
            return default


def target_fps_from_spec(root: str, override: Optional[float]) -> float:
    """目标 fps：--target-fps 优先；否则按 `出视频规格` 档；都没有 → DEFAULT_TARGET_FPS。"""
    if override:
        return float(override)
    spec = _get_setting(root, "出视频规格", "预算充足").strip()
    for k, v in SPEC_TARGET_FPS.items():
        if k in spec:
            return v
    return DEFAULT_TARGET_FPS


def plan_episode(root: str, ep: str, target_fps_override: Optional[float] = None,
                 only_clip: Optional[str] = None) -> Dict[str, Any]:
    target_fps = target_fps_from_spec(root, target_fps_override)
    routes = _load_routes(root, ep)
    backend_map = _route_backend_map(routes)
    vid_dir = os.path.join(root, "出视频", ep, "视频")
    jobs: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    notes: List[str] = []
    if not os.path.isdir(vid_dir):
        notes.append(f"缺 {vid_dir}——先出视频再跑插帧后处理。")
        return {"kind": "n2d_interp_plan", "episode": ep, "target_fps": target_fps,
                "jobs": [], "skipped": [], "backends": probe_backends(), "notes": notes}
    files = sorted(f for f in os.listdir(vid_dir)
                   if f.lower().endswith(".mp4") and not f.lower().endswith("_interp.mp4"))
    for fn in files:
        cid = clip_id_from_filename(fn)
        if only_clip and cid != only_clip:
            continue
        video_rel = os.path.join("出视频", ep, "视频", fn)
        backend = backend_map.get(cid, "")
        first_frame_only = bool(backend) and not backend_supports_three_plus_frames(backend)
        source_fps = _ffprobe_fps(os.path.join(vid_dir, fn))
        need, reason = needs_interpolation(source_fps, target_fps, first_frame_only)
        if need:
            jobs.append(build_job(cid, video_rel, source_fps, target_fps, backend,
                                  first_frame_only, reason))
        else:
            skipped.append({"clip_id": cid, "video": video_rel, "source_fps": source_fps,
                            "reason": reason})
    return {"kind": "n2d_interp_plan", "episode": ep, "target_fps": target_fps,
            "jobs": jobs, "skipped": skipped, "backends": probe_backends(), "notes": notes}


def _run_interp_cmd(job: Mapping[str, Any], root: str) -> Tuple[bool, str]:
    """按可用后端对单 clip 插帧。返回 (ok, detail)。重型 CLI env 门控，不可用返回 (False, 原因)。"""
    backends = probe_backends()
    if not backends["available"]:
        return False, "无可用插帧后端"
    src = os.path.join(root, job["video"])
    dst = os.path.join(root, job["output"])
    target = job["target_fps"]
    cmd_tmpl = os.environ.get("N2D_INTERP_CMD", "").strip()
    if cmd_tmpl:
        cmd = (cmd_tmpl.replace("{input}", shlex.quote(src)).replace("{output}", shlex.quote(dst))
               .replace("{fps}", str(target)))
        run_str = cmd
    elif os.environ.get("N2D_RIFE_CMD", "").strip() or os.environ.get("N2D_FILM_CMD", "").strip():
        tmpl = os.environ.get("N2D_RIFE_CMD") or os.environ.get("N2D_FILM_CMD")
        run_str = (tmpl.replace("{input}", shlex.quote(src)).replace("{output}", shlex.quote(dst))
                   .replace("{fps}", str(target)))
    else:  # ffmpeg minterpolate 兜底
        run_str = (f"ffmpeg -y -i {shlex.quote(src)} "
                   f"-vf \"minterpolate=fps={target}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir\" "
                   f"{shlex.quote(dst)}")
    try:
        res = subprocess.run(run_str, shell=True, capture_output=True, text=True, timeout=1800)
    except Exception as exc:
        return False, f"插帧命令异常：{type(exc).__name__}: {exc}"
    if res.returncode != 0:
        return False, f"插帧命令失败（rc={res.returncode}）：{(res.stderr or '')[-200:]}"
    if not os.path.exists(dst):
        return False, "插帧命令返回 0 但无输出文件"
    return True, f"→ {job['output']}（via {backends['chosen']}）"


def write_jobs(root: str, ep: str, plan: Mapping[str, Any]) -> str:
    out_dir = os.path.join(root, "出视频", ep, "control")
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, "interp_jobs.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--target-fps", type=float, default=None, help="目标 fps（覆盖 出视频规格 档）")
    ap.add_argument("--clip", default=None, help="只规划/执行指定 clip_id（如 Clip_03）")
    ap.add_argument("--apply", action="store_true", help="工具可用则逐 clip 执行插帧，否则降级清单")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = os.path.abspath(os.path.expanduser(ns.root))
    plan = plan_episode(root, ns.episode, ns.target_fps, ns.clip)
    jobs_path = write_jobs(root, ns.episode, plan)
    plan["jobs_path"] = jobs_path
    applied: List[Dict[str, Any]] = []
    if ns.apply:
        for job in plan["jobs"]:
            ok, detail = _run_interp_cmd(job, root)
            applied.append({"clip_id": job["clip_id"], "ok": ok, "detail": detail})
        plan["applied"] = applied
    if ns.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    b = plan["backends"]
    print(f"帧插值规划（{ns.episode}·目标 {plan['target_fps']:g}fps）：{len(plan['jobs'])} 镜待插 · "
          f"{len(plan['skipped'])} 镜不需 · 后端 {'可用:' + str(b['chosen']) if b['available'] else '不可用'}")
    for j in plan["jobs"]:
        print(f"  插 {j['clip_id']}（{j['reason']}）→ {j['output']}")
    if ns.apply:
        for a in applied:
            print(f"  {'✅' if a['ok'] else '⛔'} {a['clip_id']}：{a['detail']}")
    elif plan["jobs"] and not b["available"]:
        print("ℹ️ 无插帧后端：已落 interp_jobs.json 清单。配置 N2D_INTERP_CMD（占位 {input}{output}{fps}）/"
              "N2D_RIFE_CMD/N2D_FILM_CMD，或装带 minterpolate 的 ffmpeg 后 --apply。")
    for n in plan["notes"]:
        print("ℹ️ " + n)
    print(f"→ {jobs_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
