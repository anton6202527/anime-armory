#!/usr/bin/env python3
"""音画同步机检（AV1·口型↔配音偏移）——关掉「audio_visual_sync 零机检」缺口。

背景：`audio_visual_sync` 维度此前在 n2d_schema 里被显式登记为「无机检 runner」，
封堵理由写的是「无 SyncNet / 声轨重叠检测器」。2026 这个前提已过时——
`joonson/syncnet_python`、字节 `bytedance/LatentSync`、以及基于 Meta PE-AV 的
SyncNet 重实现 / `AVSyncNet`（shift-invariant、稳定化同步损失）都可用。本脚本把
口型↔配音的 **音视频偏移（AV offset）** 落成可疑→人判的初筛门，补齐这一维度的机检。

诚实边界（与 X1/L2 同级·advisory）：
  风格化漫剧的嘴型 + SyncNet 在非正脸/遮挡/弱置信时本就不稳，故本检测器 **advisory**——
  审计路径里 `verdict` 一律封顶到 `warn`（绝不把噪声检测器的误判升成 🔴 阻断 gate）；
  真实测得的严重档另存 `severity_measured`，只喂 n2d-score 机器分（score 不是 gate 退出码）。
  低置信镜判 `inconclusive`（SyncNet 拿不准的镜不罚分），漏报优先于误报。

运行精度分档（同 consistency_audit 的诚实根信号）：
  无 ffmpeg / 无 SyncNet 后端且无外部偏移报告 → available=False，整维交人判（不臆造分）。
  有外部 SyncNet 偏移报告（`生产数据/score_inputs/<集>_syncnet_raw.json` 或
  `生产数据/syncnet_raw_<集>.json`）→ 直接消费实测偏移。**生产端是 `lipsync_measure.py`**
  （SyncNet 桥接·在 facefusion 环境跑成片→逐 Clip 偏移→写本报告）；本消费端永远轻量可测。
  本机有 SyncNet 模块 + ffmpeg → 尝试就地抽脸轨跑（需 out-of-repo 模型权重，缺权重则降级留痕）。

落地产物：main() 会把汇总写 `生产数据/lipsync_<集>.json`（blocks/warnings/infos/evidence/metrics），
n2d-score 的 check_lip_sync 走 load_existing_report(("lip_sync","lipsync","syncnet")) 自动消费，
把启发式（仅数 mouth_visible 关键词）升级为实测偏移分。

纯数学部分（offset_ms / sync_band）无依赖、带 pytest。

用法：python3 lipsync_consistency.py <作品根> 第N集 [--fps 25] [--warn-ms 80] [--block-ms 200]
                                              [--conf-floor 2.0] [--json] [--no-write-report]
退出码：有任一 advisory warn → 0（advisory 不阻断）；纯无法检查 → 0（交人判，不臆造）。
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import os
import shutil
import sys
from typing import Any, Dict, List, Optional, Sequence

# 偏移分档默认阈值（文档化可调；SyncNet AV offset 以帧计，按 fps 折成毫秒判级）：
DEFAULT_FPS = 25.0
DEFAULT_WARN_MS = 80.0     # |偏移| ≥ 80ms（≈2帧@25fps）→ 可感不同步，warn
DEFAULT_BLOCK_MS = 200.0   # |偏移| ≥ 200ms（≈5帧@25fps）→ 严重不同步，severity_measured=block
DEFAULT_CONF_FLOOR = 2.0   # SyncNet AV 置信 < 此 → inconclusive（检测器拿不准，不罚分）
# 「过同步」上界：真人成片 SyncNet AV 置信(LSE-C 同族)约 7-8（LatentSync≈8.9 已是上限）。
# 显著高于此 = 嘴被驱动得比真人还狠(over-driven)，观感生硬(uncanny mouth)。"higher Sync-C = better"
# 是 2026 已证伪的陷阱——offset≈0 但置信爆表的镜，旧逻辑判 ok 漏掉。advisory·人听辨·绝不阻断。
DEFAULT_OVERSYNC_CEIL = 9.0

# 说话镜关键词（与 n2d_const dialogue_closeup / mouth_detect 同源口径，尽力而为筛说话镜）：
SPEAKING_MARKERS = (
    "mouth_visible=yes", "口型", "嘴部", "正面说话", "张口", "说话特写", "近景说话",
    "lip-sync", "lip sync", "mouth", "台词", "对白", "开口",
)


# ---------- 纯数学（无依赖 · pytest 覆盖） ----------

def offset_ms(offset_frames: float, fps: float = DEFAULT_FPS) -> float:
    """AV offset（帧）→ 绝对毫秒。fps≤0 时退回默认 fps（避免除零）。纯函数·可测。"""
    f = fps if fps and fps > 0 else DEFAULT_FPS
    return abs(float(offset_frames)) / f * 1000.0


def sync_band(offset_frames: float, confidence: float, fps: float = DEFAULT_FPS,
              warn_ms: float = DEFAULT_WARN_MS, block_ms: float = DEFAULT_BLOCK_MS,
              conf_floor: float = DEFAULT_CONF_FLOOR) -> str:
    """口型↔配音偏移定档（实测严重档，未封顶）：
      置信 < conf_floor              → 'inconclusive'（SyncNet 拿不准，非正脸/遮挡常见，不罚分）；
      |偏移ms| ≥ block_ms            → 'block'（严重不同步）；
      |偏移ms| ≥ warn_ms             → 'warn'（可感不同步）；
      其余                            → 'ok'。
    这是 severity_measured 的口径（喂 n2d-score）；审计路径会把 block 降级封顶到 warn。纯函数·可测。"""
    if confidence < conf_floor:
        return "inconclusive"
    ms = offset_ms(offset_frames, fps)
    if ms >= block_ms:
        return "block"
    if ms >= warn_ms:
        return "warn"
    return "ok"


def oversync_band(confidence: float, ceiling: float = DEFAULT_OVERSYNC_CEIL) -> str:
    """口型「过同步」上界检测：SyncNet/LSE-C 置信显著高于真人 GT 带(~7-8) → 嘴动得比人狠 → uncanny。
    与 |offset| 严重档正交（偏移可为 0 却过同步）。返回 'over_sync'（≥ceiling）/'ok'。advisory·纯函数·可测。"""
    try:
        return "over_sync" if float(confidence) >= ceiling else "ok"
    except (TypeError, ValueError):
        return "ok"


def advisory_verdict(measured: str) -> str:
    """审计路径封顶：把实测严重档降成 advisory verdict——block→warn（噪声检测器绝不硬阻断 gate），
    inconclusive→ok（不入 findings）。纯函数·可测。"""
    if measured == "block":
        return "warn"
    if measured == "inconclusive":
        return "ok"
    return measured


def offset_remediation(measured: str) -> Optional[Dict[str, Any]]:
    """口型偏移修复阶梯（cheap-fix-first）——补 AV1「测了偏移却不告诉怎么便宜修」的缺口。

    2026 后期对口型（LatentSync 保身份最好 / MuseTalk 近实时 / Wav2Lip 同步稳）已成熟，
    `n2d-video/scripts/lipsync_pass.py --apply` 能逐 clip 修口型而**不重出整 clip**——比回
    video_prompt 重渲染便宜一个量级。故 AV1 检出偏移时，修复阶梯**先 pass 后重出**。

    severity_measured ∈ {warn, block} → 返回 {return_to_stage, rerun_scope, remediation}；
    ok/inconclusive（没测到真偏移）→ None（不乱给修法）。纯函数·可测。"""
    if measured not in ("warn", "block"):
        return None
    return {
        "return_to_stage": "video",
        "rerun_scope": (
            "口型↔配音偏移修复（cheap-fix-first）：①先跑 "
            "python3 skills/n2d/n2d-video/scripts/lipsync_pass.py <作品根> <集> --apply "
            "做后期对口型（LatentSync 优先·保漫剧脸身份，不重出整 clip，最省）；"
            "②修复 pass 也救不回（无可用本地工具 / 嘴型已严重错）才回 n2d-video 用"
            "首尾双帧 + 口型同步后端（Kling/Veo）重出该 clip（贵）。"
        ),
        "remediation": [
            {"step": 1, "action": "lipsync_pass", "cost": "cheap",
             "cmd": "python3 skills/n2d/n2d-video/scripts/lipsync_pass.py <作品根> <集> --apply"},
            {"step": 2, "action": "regenerate_clip", "cost": "expensive",
             "note": "首尾双帧 + 口型同步后端重出整 clip，仅当后期修复救不回"},
        ],
    }


# ---------- 能力探针 ----------

def _probe_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _probe_syncnet() -> Optional[str]:
    """返回可用的 SyncNet/口型同步后端模块名（缺则 None）。重活权重在 out-of-repo conda 环境。"""
    for mod in ("syncnet_python", "syncnet", "latentsync", "avsyncnet"):
        try:
            if importlib.util.find_spec(mod) is not None:
                return mod
        except Exception:
            continue
    return None


# ---------- 输入读取（尽力而为·缺则空） ----------

def _read_json(path: str) -> Optional[dict]:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def load_external_offsets(root: str, ep: str) -> Optional[dict]:
    """消费外部 SyncNet 偏移报告（推荐路径：重活在 conda 环境跑完喂回）。
    认两个位置，结构：{"clips":[{"clip":"Clip_03","offset_frames":3,"confidence":4.1}, ...], "fps":25}。"""
    for path in (
        os.path.join(root, "生产数据", "score_inputs", f"{ep}_syncnet_raw.json"),
        os.path.join(root, "生产数据", f"syncnet_raw_{ep}.json"),
    ):
        data = _read_json(path)
        if data and isinstance(data.get("clips"), list):
            return data
    return None


def _prompt_text(root: str, ep: str) -> str:
    """出视频 prompt 文本（判说话镜尽力而为）。"""
    chunks: List[str] = []
    for rel in (
        os.path.join("出视频", ep, "prompt", "00_总览.md"),
        os.path.join("出视频", ep, "prompt"),
    ):
        path = os.path.join(root, rel)
        if os.path.isfile(path):
            try:
                chunks.append(open(path, encoding="utf-8").read())
            except Exception:
                pass
        elif os.path.isdir(path):
            for f in sorted(glob.glob(os.path.join(path, "*.md"))):
                try:
                    chunks.append(open(f, encoding="utf-8").read())
                except Exception:
                    pass
    return "\n".join(chunks)


def is_speaking_clip(text: str) -> bool:
    """文本里命中任一说话标记 → 说话镜（口型↔配音偏移才有意义）。纯函数·可测。"""
    low = (text or "").lower()
    return any(m.lower() in low for m in SPEAKING_MARKERS)


# ---------- 编排 ----------

def _band_rows(clips: Sequence[dict], fps: float, warn_ms: float, block_ms: float,
               conf_floor: float, oversync_ceiling: float = DEFAULT_OVERSYNC_CEIL) -> List[dict]:
    """实测偏移 clips → 逐镜定档行（advisory verdict + severity_measured + 过同步上界 advisory）。"""
    rows: List[dict] = []
    for c in clips:
        if not isinstance(c, dict):
            continue
        off = c.get("offset_frames")
        conf = c.get("confidence")
        if off is None or conf is None:
            continue
        clip_fps = float(c.get("fps") or fps)
        measured = sync_band(float(off), float(conf), clip_fps, warn_ms, block_ms, conf_floor)
        verdict = advisory_verdict(measured)
        # 过同步上界与 offset 严重档正交：低置信(inconclusive)时不谈过同步（置信本就不可信）
        over = oversync_band(float(conf), oversync_ceiling) if measured != "inconclusive" else "ok"
        if verdict == "ok" and measured == "ok" and over == "ok":
            continue  # 同步良好且未过同步，不入清单
        rem = offset_remediation(measured)
        if over == "over_sync" and verdict == "ok":
            verdict = "warn"  # 偏移没问题但过同步 → 升为 advisory warn 让其进清单
        row = {
            "clip": str(c.get("clip") or c.get("id") or "?"),
            "offset_frames": round(float(off), 2),
            "offset_ms": round(offset_ms(float(off), clip_fps), 1),
            "confidence": round(float(conf), 2),
            "severity_measured": measured,
            "verdict": verdict,
            "message": (
                f"口型↔配音偏移 {offset_ms(float(off), clip_fps):.0f}ms"
                + ("（SyncNet 低置信·拿不准，交人判）" if measured == "inconclusive"
                   else "（疑似严重不同步）" if measured == "block" else "")
                + (f"；口型『过同步』(置信 {float(conf):.1f} ≥ {oversync_ceiling:.0f}，高于真人GT带~7-8)"
                   "——嘴可能被驱动得比真人还狠(uncanny)，人听辨是否生硬，必要时换不那么激进的口型后端/降低同步强度"
                   if over == "over_sync" else "")
                + ("　修复优先：先跑 lipsync_pass 后期对口型（省），救不回再重出 clip" if rem else "")
            ),
        }
        if over == "over_sync":
            row["oversync"] = True
        if rem:
            row.update(rem)  # cheap-fix-first：return_to_stage=video + rerun_scope + remediation 阶梯
        rows.append(row)
    return rows


def analyze(root: str, ep: str, fps: float = DEFAULT_FPS, warn_ms: float = DEFAULT_WARN_MS,
            block_ms: float = DEFAULT_BLOCK_MS, conf_floor: float = DEFAULT_CONF_FLOOR,
            oversync_ceiling: float = DEFAULT_OVERSYNC_CEIL) -> dict:
    res: dict = {"available": False, "mode": None, "precision": "none",
                 "shots": [], "notes": []}

    external = load_external_offsets(root, ep)
    if external:
        rows = _band_rows(external.get("clips", []),
                          float(external.get("fps") or fps), warn_ms, block_ms, conf_floor,
                          oversync_ceiling)
        res.update(available=True, mode="external_syncnet", precision="full", shots=rows)
        res["notes"].append("消费外部 SyncNet 偏移报告（实测）。")
        return res

    backend = _probe_syncnet()
    has_ffmpeg = _probe_ffmpeg()
    if backend and has_ffmpeg:
        # 本机有后端：就地抽脸轨跑需 out-of-repo 模型权重（见 CLAUDE.md 重活在 conda 环境）。
        # 这里不内联重活，避免无权重时假跑——明确引导用外部报告路径喂回，保持诚实降级。
        res.update(available=False, mode=f"{backend}_present", precision="none")
        res["notes"].append(
            f"检测到 {backend} 模块但本脚本不内联跑重活（需 out-of-repo 模型权重）——"
            f"跑生产端桥接：conda run -n facefusion python lipsync_measure.py <作品根> {ep}"
            f"（自动写 生产数据/syncnet_raw_{ep}.json）再复跑本检测器消费。")
        return res

    missing = []
    if not has_ffmpeg:
        missing.append("ffmpeg/ffprobe")
    if not backend:
        missing.append("SyncNet/LatentSync 后端")
    res["notes"].append(
        f"音画同步机检已跳过（缺 {'、'.join(missing)} 且无外部偏移报告）——"
        "口型↔配音偏移暂由人判（看说话镜口型是否随台词、对白起止是否压上嘴形）。"
        f"接入：conda 环境跑 SyncNet 后喂 生产数据/syncnet_raw_{ep}.json。")
    return res


def to_score_report(res: dict) -> dict:
    """analyze 结果 → n2d-score check_lip_sync 可消费的报告（blocks/warnings/infos/evidence/metrics）。
    blocks 用 severity_measured（机器分要看真实严重档）；不可检查时全 0 + skip 证据。纯函数·可测。"""
    shots = res.get("shots", [])
    blocks = sum(1 for s in shots if s.get("severity_measured") == "block")
    warns = sum(1 for s in shots if s.get("severity_measured") == "warn")
    inconcl = sum(1 for s in shots if s.get("severity_measured") == "inconclusive")
    oversync = sum(1 for s in shots if s.get("oversync"))
    evidence: List[str] = []
    if not res.get("available"):
        evidence.extend(res.get("notes", []))
    else:
        for s in shots[:12]:
            evidence.append(f"{s['clip']}: {s['message']}")
        if not shots:
            evidence.append("说话镜口型↔配音偏移机检通过（无可感不同步）。")
    return {
        "blocks": blocks,
        "warnings": warns,
        "infos": 1 if res.get("available") and not shots else 0,
        "evidence": evidence,
        "metrics": {
            "mode": res.get("mode"),
            "precision": res.get("precision"),
            "measured_block": blocks,
            "measured_warn": warns,
            "inconclusive": inconcl,
            "oversync": oversync,
            "checked_clips": len(shots),
        },
    }


def write_score_report(root: str, ep: str, res: dict) -> str:
    """写 生产数据/lipsync_<集>.json，供 n2d-score load_existing_report 自动消费。"""
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"lipsync_{ep}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(to_score_report(res), fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return path


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--fps", type=float, default=DEFAULT_FPS)
    ap.add_argument("--warn-ms", type=float, default=DEFAULT_WARN_MS)
    ap.add_argument("--block-ms", type=float, default=DEFAULT_BLOCK_MS)
    ap.add_argument("--conf-floor", type=float, default=DEFAULT_CONF_FLOOR)
    ap.add_argument("--oversync-ceiling", type=float, default=DEFAULT_OVERSYNC_CEIL,
                    help="SyncNet 置信『过同步』上界（高于真人GT带~7-8 = 嘴动得比人狠·uncanny·advisory）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-write-report", action="store_true",
                    help="不写 生产数据/lipsync_<集>.json（默认会写，供 n2d-score 消费）")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode, ns.fps, ns.warn_ms, ns.block_ms, ns.conf_floor,
                  ns.oversync_ceiling)
    if not ns.no_write_report and os.path.isdir(ns.root):
        write_score_report(ns.root.rstrip("/"), ns.episode, res)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"=== 音画同步机检（AV1·口型↔配音偏移·advisory）：{ns.root} {ns.episode} ===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    if not res["available"]:
        return 0
    icon = {"warn": "⚠️口型偏移", "ok": "·低置信"}
    for s in res["shots"]:
        print(f"{icon.get(s['verdict'], '·')} {s['clip']}: {s['message']}")
    measured_block = sum(1 for s in res["shots"] if s.get("severity_measured") == "block")
    print(f"\n实测严重不同步 {measured_block} · advisory 标出 {len(res['shots'])} 镜"
          f"（advisory 不阻断 gate；严重档喂 n2d-score）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
