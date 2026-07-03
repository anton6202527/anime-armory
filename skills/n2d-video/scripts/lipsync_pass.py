#!/usr/bin/env python3
"""对口型「后期 pass」落地器（补 SKILL 里 MuseTalk/Wav2Lip/LatentSync 只有文字建议、无执行入口的缺口）。

n2d 的 `对口型` 选择点有三档：
  关闭(默认) / 配音对齐(voice_conditioned·后端音频参考口型) / 后期pass(本地工具把口型对到配音轨)。
**配音对齐**主路径已工程化（model-router 把说话镜路由成 `mode=voice_conditioned_lipsync`，后端吃
`line_NN.wav` 作口型条件）。但**后期pass**这一回退档此前落不了地——选了也没有脚本可跑。本脚本补这条：

  plan：读 `_设置.md 对口型` + `出视频/<集>/prompt/video_model_routes.json`，挑出需要后期对口型的
        说话镜，按 clip 配对其驱动音轨（`合成/<集>/配音/line_NN.wav`，由 storyboard 的 clip→台词行
        映射解析），生成 `出视频/<集>/control/lipsync_jobs.json` 作业清单 + 工具可用性探针 + 指引。
  --apply：检测到本地 MuseTalk/LatentSync/Wav2Lip 可用时逐 clip 调用（CLI 路径由环境变量给，
           本仓不内置重型权重）；都不可用则只落清单 + 打印手工指引，绝不静默跳过。

设计同 motion_control：纯规划逻辑（挑镜/配对/选工具）无依赖、带 pytest；重型 CLI 调用 env 门控、
不可用就降级成清单，不臆造成功。**铁律**：模型只对口型，**不接管声音**——成片音轨仍是 voice-first
克隆配音轨（与 voice_conditioned 一致，避免双人声）。

用法：
  python3 lipsync_pass.py <作品根> 第N集            # 规划（默认 report-only，写 lipsync_jobs.json）
  python3 lipsync_pass.py <作品根> 第N集 --json
  python3 lipsync_pass.py <作品根> 第N集 --apply     # 工具可用则执行，否则降级清单
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

OFF_VALUES = ("关闭", "off", "none", "无", "")
POST_PASS_VALUES = ("后期pass", "后期", "post", "post_pass", "musetalk", "wav2lip", "latentsync")
# 「对话近景」保留为显式兼容档：仅对话近景说话镜走配音对齐口型；与 model-router 同义，
# 这里只读 route 自带信号，不反向 import router。非原生音画新默认是关闭/无声视频流。
DIALOGUE_CLOSEUP_DEFAULT_VALUES = ("对话近景", "对话近景默认", "dialogue_closeup", "dialogue_closeup_default")
SILENT_VIDEO_FLOW_VALUES = ("无声视频流", "静音视频流", "无声", "静音", "video_only", "silent_video", "no_audio")
LIPSYNC_VIDEO_FLOW_VALUES = ("配音对齐口型", "音频参考口型", "voice_conditioned_lipsync", "lipsync", "lip_sync")
DIALOGUE_CLOSEUP_SHOT_TYPES = ("dialogue_shot_reverse", "dialogue_closeup")
# 说话镜判据（与 model-router 同义，但本脚本只读 route 自带信号，不反向 import 形成耦合）
SPEECH_SHOT_TYPES = (
    "dialogue", "dialogue_shot_reverse", "reveal_reaction_chain",
    "public_confrontation", "relationship_turn", "speech", "closeup_speaking",
    "reaction", "monologue", "talking_head",
)
SPEECH_AUDIO_POLICIES = ("native_speech", "lipsync_condition_only")
# 后期对口型工具优先序（2026-06 快照·能力会变，以 n2d/references/模型矩阵.md「音画联合」为准）：
# LatentSync 身份保持最好(扩散)、MuseTalk 近实时画质均衡、Wav2Lip 同步精度最稳但糊。
TOOL_PREFERENCE = ("latentsync", "musetalk", "wav2lip")
TOOL_ENV = {"latentsync": "LATENTSYNC_CLI", "musetalk": "MUSETALK_CLI", "wav2lip": "WAV2LIP_CLI"}


# ---------- 纯规划逻辑（无依赖 · pytest 覆盖） ----------

def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def lipsync_mode(setting: Any) -> str:
    """`对口型` 设置 → 规范档：off / voice_conditioned_dialogue_closeup / voice_conditioned / post_pass。"""
    s = str(setting or "").strip()
    if _norm(s) in OFF_VALUES or s in OFF_VALUES:
        return "off"
    if any(tok in s.lower() for tok in POST_PASS_VALUES) or "后期" in s:
        return "post_pass"
    if _norm(s) in [v.lower() for v in DIALOGUE_CLOSEUP_DEFAULT_VALUES] or s in DIALOGUE_CLOSEUP_DEFAULT_VALUES:
        return "voice_conditioned_dialogue_closeup"
    return "voice_conditioned"


def _is_dialogue_closeup_route(route: Mapping[str, Any]) -> bool:
    """该 route 是否对话近景说话镜（口型最该兜的情形）：对话 shot_type 或 mouth_visible。"""
    if _norm(route.get("shot_type")) in DIALOGUE_CLOSEUP_SHOT_TYPES:
        return True
    return bool(route.get("mouth_visible") or route.get("speech"))


def is_speech_route(route: Mapping[str, Any]) -> bool:
    """该 route 是否说话镜（需要口型）。只读 route 自带信号，多路兜底。"""
    if _norm(route.get("mode")) == "voice_conditioned_lipsync":
        return True
    if _norm(route.get("native_audio_policy")) in SPEECH_AUDIO_POLICIES:
        return True
    if _norm(route.get("shot_type")) in SPEECH_SHOT_TYPES:
        return True
    return bool(route.get("mouth_visible") or route.get("speech"))


def needs_post_pass(route: Mapping[str, Any], setting: Any) -> bool:
    """该 route 是否需要**后期** lipsync pass：
    - off：从不需要。
    - post_pass：所有说话镜强制走本地后期工具。
    - voice_conditioned：仅当说话镜没被路由到后端音频参考口型（mode≠voice_conditioned_lipsync）时，
      作为 degrade 回退到后期 pass；已 voice_conditioned 的交给后端，不重复后期。"""
    mode = lipsync_mode(setting)
    if mode == "off":
        return False
    if mode == "voice_conditioned_dialogue_closeup":
        # 对话近景兼容档：只兜对话近景说话镜的 degrade，其余说话镜不进后期对口型。
        if not _is_dialogue_closeup_route(route):
            return False
        return _norm(route.get("mode")) != "voice_conditioned_lipsync"
    if not is_speech_route(route):
        return False
    if mode == "post_pass":
        return True
    return _norm(route.get("mode")) != "voice_conditioned_lipsync"


def select_post_pass_clips(routes: Sequence[Mapping[str, Any]], setting: Any) -> List[Dict[str, Any]]:
    """从 routes 选出需要后期对口型的 clip（带 clip_id / shot_type / 为何入选）。纯函数·可测。"""
    out: List[Dict[str, Any]] = []
    for r in routes:
        if not isinstance(r, Mapping) or not needs_post_pass(r, setting):
            continue
        out.append({
            "clip_id": str(r.get("clip_id") or r.get("id") or ""),
            "shot_type": str(r.get("shot_type") or ""),
            "reason": ("forced_post_pass" if lipsync_mode(setting) == "post_pass"
                       else "degrade_from_voice_conditioned"),
        })
    return [c for c in out if c["clip_id"]]


def probe_tools(environ: Mapping[str, str], which: Callable[[str], Optional[str]]) -> Dict[str, Optional[str]]:
    """探测本地后期对口型工具：优先 env 指定的 CLI 路径，否则 PATH 上找同名命令。
    返回 {tool: 路径或None}。纯逻辑（环境/which 注入）·可测。"""
    found: Dict[str, Optional[str]] = {}
    for tool in TOOL_PREFERENCE:
        env_key = TOOL_ENV[tool]
        path = environ.get(env_key)
        if path:
            found[tool] = path
            continue
        found[tool] = which(tool)
    return found


def pick_tool(available: Mapping[str, Optional[str]],
              preference: Sequence[str] = TOOL_PREFERENCE) -> Optional[str]:
    """按优先序选第一个可用工具名；都不可用返回 None。纯函数·可测。"""
    for tool in preference:
        if available.get(tool):
            return tool
    return None


def build_job(clip: Mapping[str, Any], video_path: str, audio_paths: Sequence[str],
              out_path: str, tool: Optional[str]) -> Dict[str, Any]:
    """单 clip 后期对口型作业条目（纯字典构造·可测）。"""
    return {
        "clip_id": clip.get("clip_id"),
        "shot_type": clip.get("shot_type"),
        "reason": clip.get("reason"),
        "video": video_path,
        "audio": list(audio_paths),
        "output": out_path,
        "tool": tool,
        "status": "ready" if (video_path and audio_paths and tool) else "needs_input",
    }


# ---------- IO / 编排（重型 CLI env 门控·不可用降级清单） ----------

def _read_setting(root: str, ep: str) -> str:
    """读 `_设置.md` 的视频生成音频策略 + 对口型；失败回默认关闭/无声视频流。"""
    try:
        common = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
        if common not in sys.path:
            sys.path.insert(0, common)
        from n2d_settings import load_settings  # type: ignore
        settings = load_settings(root)
        audio_policy = str(settings.get("视频生成音频策略", "") or "").strip()
        lip = str(settings.get("对口型", "") or "").strip()
        if audio_policy and (_norm(audio_policy) in SILENT_VIDEO_FLOW_VALUES or audio_policy in SILENT_VIDEO_FLOW_VALUES):
            return "关闭"
        if audio_policy and (_norm(audio_policy) in LIPSYNC_VIDEO_FLOW_VALUES or audio_policy in LIPSYNC_VIDEO_FLOW_VALUES):
            return lip or "配音对齐"
        return lip or "关闭"
    except Exception:
        return "关闭"


def _load_routes(root: str, ep: str) -> List[Dict[str, Any]]:
    p = os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json")
    if not os.path.isfile(p):
        return []
    try:
        plan = json.load(open(p, encoding="utf-8"))
        return list(plan.get("routes") or [])
    except Exception:
        return []


def _clip_line_indices(root: str, ep: str) -> Dict[str, List[int]]:
    """从 storyboard.json 解析 clip_id → 台词行号列表（驱动音轨配对用）。缺/异常返回空。"""
    p = os.path.join(root, "脚本", ep, "storyboard.json")
    out: Dict[str, List[int]] = {}
    if not os.path.isfile(p):
        return out
    try:
        sb = json.load(open(p, encoding="utf-8"))
    except Exception:
        return out
    for clip in sb.get("clips", []) or []:
        cid = str(clip.get("id") or clip.get("clip_id") or "")
        if not cid:
            continue
        lines = clip.get("lines") or clip.get("line_indices") or clip.get("voiceover_lines") or []
        idx = [int(x) for x in lines if isinstance(x, (int, float)) or str(x).isdigit()]
        if idx:
            out[cid] = idx
    return out


def _audio_for_clip(root: str, ep: str, line_idx: Sequence[int]) -> List[str]:
    """clip 台词行 → 合成/<集>/配音/line_NN.wav（存在才纳入；split 后配音在 合成 侧）。"""
    voice_dir = os.path.join(root, "合成", ep, "配音")
    paths = []
    for i in line_idx:
        cand = os.path.join(voice_dir, f"line_{i:02d}.wav")
        if os.path.isfile(cand):
            paths.append(cand)
    return paths


def plan(root: str, ep: str) -> Dict[str, Any]:
    setting = _read_setting(root, ep)
    mode = lipsync_mode(setting)
    routes = _load_routes(root, ep)
    selected = select_post_pass_clips(routes, setting)
    tools = probe_tools(os.environ, shutil.which)
    tool = pick_tool(tools)
    line_map = _clip_line_indices(root, ep)

    jobs: List[Dict[str, Any]] = []
    notes: List[str] = []
    for c in selected:
        cid = c["clip_id"]
        vid_dir = os.path.join(root, "出视频", ep, "视频")
        video = ""
        if os.path.isdir(vid_dir):
            for fn in sorted(os.listdir(vid_dir)):
                if cid in fn and fn.lower().endswith((".mp4", ".mov")):
                    video = os.path.join(vid_dir, fn); break
        audio = _audio_for_clip(root, ep, line_map.get(cid, []))
        out_dir = os.path.join(root, "出视频", ep, "视频_lipsync")
        out_path = os.path.join(out_dir, f"{cid}_lipsync.mp4")
        job = build_job(c, video, audio, out_path, tool)
        if not audio:
            job.setdefault("warnings", []).append("未解析到驱动音轨：补 storyboard clip→台词行映射，或人工指定 line_NN.wav")
        if not video:
            job.setdefault("warnings", []).append("未找到该 clip 的视频文件：先出视频")
        jobs.append(job)

    if mode == "off":
        notes.append("`对口型=关闭`：无需后期对口型；正面大特写说话镜建议分镜阶段用侧脸/背身/空镜配旁白规避。")
    elif mode == "voice_conditioned" and not selected:
        notes.append("`对口型=配音对齐`：说话镜已由后端音频参考口型处理，无 degrade 到后期的 clip。")
    elif mode == "voice_conditioned_dialogue_closeup" and not selected:
        notes.append("`对口型=对话近景`：对话近景说话镜已由后端音频参考口型处理；非对话近景说话镜不进口型路由（成本有界）。")
    if selected and not tool:
        notes.append("未检测到本地后期对口型工具——设 LATENTSYNC_CLI / MUSETALK_CLI / WAV2LIP_CLI 指向已装 CLI "
                     "（重型权重在 conda env，不入本仓）；当前只落清单，按清单手工对口型。")
    return {
        "kind": "n2d_lipsync_jobs",
        "version": 1,
        "root": root,
        "episode": ep,
        "setting": setting,
        "mode": mode,
        "tools_available": tools,
        "chosen_tool": tool,
        "jobs": jobs,
        "notes": notes,
    }


def write_plan(root: str, ep: str, res: Dict[str, Any]) -> str:
    out_dir = os.path.join(root, "出视频", ep, "control")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "lipsync_jobs.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return path


def _apply_job(job: Mapping[str, Any], tool: str, tool_path: str) -> int:
    """调用本地对口型 CLI（约定接口：<cli> --video V --audio A --output O）。
    不同工具实参可能不同——以各自 wrapper 为准；这里给统一最小约定，env 指向的 CLI 自行适配。"""
    import subprocess
    audio = (job.get("audio") or [None])[0]
    if not (job.get("video") and audio and job.get("output")):
        return 1
    os.makedirs(os.path.dirname(job["output"]), exist_ok=True)
    cmd = [tool_path, "--video", job["video"], "--audio", audio, "--output", job["output"]]
    print(f"  → {tool}: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--apply", action="store_true", help="工具可用则逐 clip 执行对口型；否则降级清单")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = ns.root.rstrip("/")
    res = plan(root, ns.episode)
    if os.path.isdir(root):
        res["jobs_path"] = os.path.relpath(write_plan(root, ns.episode, res), root)

    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"=== 对口型后期 pass 规划：{root} {ns.episode}（对口型={res['setting']} → {res['mode']}）===")
        for n in res["notes"]:
            print("ℹ️ " + n)
        for j in res["jobs"]:
            mark = "✅" if j["status"] == "ready" else "⏳"
            print(f"{mark} {j['clip_id']}（{j['shot_type']}·{j['reason']}）→ {j['status']}")
            for w in j.get("warnings", []):
                print(f"    ⚠️ {w}")
        print(f"\n说话镜需后期对口型 {len(res['jobs'])} 个；工具：{res['chosen_tool'] or '无（降级清单）'}")

    if ns.apply:
        tool = res["chosen_tool"]
        if not tool:
            print("✋ 无可用本地对口型工具，未执行——按 lipsync_jobs.json 手工对口型，或设置 *_CLI 环境变量。",
                  file=sys.stderr)
            return 0
        tool_path = res["tools_available"][tool]
        fails = 0
        for j in res["jobs"]:
            if j["status"] != "ready":
                continue
            if _apply_job(j, tool, tool_path) != 0:
                fails += 1
        return 1 if fails else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
