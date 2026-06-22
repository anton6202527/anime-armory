#!/usr/bin/env python3
"""角色/势力主题动机（leitmotif）登记表 + 确定性铺设规划——治「BGM 只有逐集情绪、没有跨集
角色主题」的盲区。

现状：BGM 只到「逐集情绪 + 张力 ducking」（n2d-compose/bgm + tension_mix）这一层——某角色/
某势力登场 N 集，却没有一条「听见就知道是他」的复现旋律（leitmotif，《指环王》《星战》的招牌
手法）。2026 实测：让生成式音乐**跨集维持同一段主题动机**极不稳——同一个名字喂同一段 prompt，
两集出来的动机能差出两首歌。唯一**跨后端可靠**的解法不是「每集重新生成动机」，而是**确定性复用**：
为每个角色/势力**一次性**登记一段动机音频，之后凡该角色有高光时刻，就把**同一段 clip** 原样铺进去。

铁律——登记一次、确定性复用：
  motif.json 登记 角色/势力 → 一段动机 clip（file + cue 类型 + gain）。
  plan_cues 读 时长清单（每句知道谁几秒到几秒在台上）→ 在该角色焦点 span 开头铺一记动机，
  且 min_gap 内不重复触发（避免动机刷屏）。同一段 clip 反复用——这就是确定性复用的核心。

登记表：<作品根>/设定库/motif.json
  {"沈念": {"file":"素材/motif/shen.wav","cue":"focus","gain":0.5,"faction":false},
   "东宫": {"file":"素材/motif/donggong.wav","cue":"faction","gain":0.4,"faction":true}}
  值也可是裸字符串（视作 file，cue/gain 取默认），与 voice_lexicon 容错风格一致。

纯函数（normalize/plan_cues/cue_filter_plan）无依赖、带 pytest。compose 仅在音乐总线一处接入：
把 cue_filter_plan 产的 adelay+volume 描述符 amix 进 BGM 总线（缺登记表 → 空规划 → 全程 no-op，
绝不影响既有合成）。

用法（独立巡检）：python3 motif_registry.py <作品根> 第N集 [--json] [--min-gap 8]
  读 motif.json + 合成/第N集/配音/时长清单.json → 打 角色 → 动机 file → 时刻 的 cue sheet。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence

DEFAULT_CUE = "focus"      # 未声明 cue 类型时的默认（焦点出场即铺）
DEFAULT_GAIN = 0.45        # 动机相对音量默认（压在台词之下、与 BGM 同量级）
DEFAULT_MIN_GAP = 8.0      # 同一动机两次触发的最小间隔秒，防动机刷屏


# ---------- 纯函数（无依赖 · pytest 覆盖） ----------

def normalize_motifs(raw: dict) -> Dict[str, dict]:
    """原始 json → {key: {file, cue, gain}}。容错：值可为 str（视作 file）或 dict。
    丢弃空 key / 空 file（无音频可铺的条目登记了也是 no-op）。纯函数·可测。"""
    out: Dict[str, dict] = {}
    for key, val in (raw or {}).items():
        k = str(key or "").strip()
        if not k:
            continue
        if isinstance(val, str):
            f = val.strip()
            entry = {"file": f, "cue": DEFAULT_CUE, "gain": DEFAULT_GAIN}
        elif isinstance(val, dict):
            f = str(val.get("file") or "").strip()
            cue = str(val.get("cue") or DEFAULT_CUE).strip() or DEFAULT_CUE
            gain = _as_float(val.get("gain"))
            entry = {"file": f, "cue": cue, "gain": DEFAULT_GAIN if gain is None else gain}
        else:
            continue
        if not entry["file"]:
            continue
        out[k] = entry
    return out


def _as_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _line_role(line: Any) -> str:
    """时长清单一句 → 角色名。兼容 '角色'（n2d 清单字段）/ 'role'。"""
    if not isinstance(line, dict):
        return ""
    return str(line.get("角色") or line.get("role") or "").strip()


def plan_cues(manifest: Sequence[Any], motifs: Dict[str, dict],
              min_gap: float = DEFAULT_MIN_GAP) -> List[Dict[str, Any]]:
    """时长清单 + 动机登记表 → 确定性 cue sheet。

    对每个登记了动机的角色，扫其在台上的 span（清单按 start 顺序），在焦点 span 开头铺一记动机；
    但同一动机若距上次触发不足 min_gap 秒则跳过（去重，防刷屏）。
    返回 [{key, file, at, gain, cue}]，按 at 升序。空登记表 / 空清单 → []。纯函数·可测。"""
    if not motifs or not manifest:
        return []
    # 按 start 排序遍历，使「焦点 span 开头」与去重判定都沿时间轴推进
    rows = []
    for ln in manifest:
        if not isinstance(ln, dict):
            continue
        role = _line_role(ln)
        if not role:
            continue
        start = _as_float(ln.get("start"))
        if start is None:
            continue
        rows.append((start, role))
    rows.sort(key=lambda r: r[0])

    # 角色 → 命中的动机 key（子串匹配：'沈念旁白' 命中登记的 '沈念'；长 key 优先，避免误吞）
    keys_longest = sorted(motifs.keys(), key=len, reverse=True)
    last_at: Dict[str, float] = {}
    cues: List[Dict[str, Any]] = []
    for start, role in rows:
        mkey = next((k for k in keys_longest if k in role), None)
        if mkey is None:
            continue
        prev = last_at.get(mkey)
        if prev is not None and (start - prev) < min_gap:
            continue   # 去重：同一动机 min_gap 内不重复触发
        m = motifs[mkey]
        cues.append({"key": mkey, "file": m["file"], "at": round(start, 3),
                     "gain": m["gain"], "cue": m["cue"]})
        last_at[mkey] = start
    cues.sort(key=lambda c: c["at"])
    return cues


def cue_filter_plan(cues: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """cue sheet → ffmpeg 友好描述符列表：[{file, adelay_ms, gain, key}]。
    adelay_ms = at*1000（动机延迟到该时刻入声），供 compose amix 进音乐总线。纯函数·可测。"""
    plan: List[Dict[str, Any]] = []
    for c in cues:
        at = _as_float(c.get("at")) or 0.0
        gain = _as_float(c.get("gain"))
        plan.append({"file": c.get("file", ""),
                     "adelay_ms": int(round(max(0.0, at) * 1000)),
                     "gain": DEFAULT_GAIN if gain is None else gain,
                     "key": c.get("key", "")})
    return plan


def build_overlay_args(in_video: str, out_video: str, plan: Sequence[Dict[str, Any]],
                       ffmpeg: str = "ffmpeg") -> Optional[List[str]]:
    """成片 + 动机 filter_plan → ffmpeg argv（视频流直 copy，仅音频 amix 进动机）。
    空规划 → None（compose 据此 no-op，$OUT 一字不动）。纯函数·可测（只构 argv 不跑）。"""
    if not plan:
        return None
    args = [ffmpeg, "-y", "-loglevel", "error", "-i", in_video]
    for p in plan:
        args += ["-i", p.get("file", "")]
    parts, labels = [], []
    for i, p in enumerate(plan, start=1):
        ms = int(p.get("adelay_ms", 0))
        g = _as_float(p.get("gain"))
        g = DEFAULT_GAIN if g is None else g
        parts.append(f"[{i}:a]adelay={ms}|{ms},volume={g}[m{i}]")
        labels.append(f"[m{i}]")
    # 基础音轨 [0:a] 与各动机 amix；normalize=0 不改原电平，duration=first 锁成片时长
    mix_inputs = "[0:a]" + "".join(labels)
    parts.append(f"{mix_inputs}amix=inputs={1 + len(plan)}:normalize=0:duration=first[a]")
    args += ["-filter_complex", ";".join(parts),
             "-map", "0:v", "-map", "[a]", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_video]
    return args


# ---------- IO ----------

def load_motifs(root: str) -> Dict[str, dict]:
    """读 <root>/设定库/motif.json；缺/坏 → {}（compose 据此 no-op，零副作用）。"""
    path = os.path.join(root, "设定库", "motif.json")
    try:
        return normalize_motifs(json.load(open(path, encoding="utf-8")))
    except Exception:
        return {}


def _load_manifest(root: str, ep: str) -> List[Any]:
    """读 <root>/合成/<ep>/配音/时长清单.json → 句列表。缺/坏 → []。
    清单可为裸列表或 {"lines":[...]} / {"items":[...]} 包裹。"""
    p = os.path.join(root, "合成", ep, "配音", "时长清单.json")
    try:
        data = json.load(open(p, encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("lines", "items", "清单", "entries"):
            v = data.get(k)
            if isinstance(v, list):
                return v
    return []


def analyze(root: str, ep: str, min_gap: float = DEFAULT_MIN_GAP) -> dict:
    motifs = load_motifs(root)
    manifest = _load_manifest(root, ep)
    res: dict = {"available": bool(motifs), "registered": len(motifs),
                 "cues": [], "filter_plan": [], "notes": []}
    if not motifs:
        res["notes"].append("无 设定库/motif.json——未登记角色/势力主题动机；BGM 仅逐集情绪，"
                            "无跨集复现旋律。建议为主角/主要势力各登记一段动机 clip（确定性复用）。")
        return res
    if not manifest:
        res["notes"].append(f"缺 合成/{ep}/配音/时长清单.json——只校登记表本体，无法定位本集角色在台时刻。"
                            "先跑 n2d-voice 出时长清单。")
        return res
    cues = plan_cues(manifest, motifs, min_gap)
    res["cues"] = cues
    res["filter_plan"] = cue_filter_plan(cues)
    if not cues:
        res["notes"].append("本集时长清单里无任何已登记动机的角色出场 → 无动机铺设（no-op）。")
    return res


def run_overlay(in_video: str, plan: Sequence[Dict[str, Any]], ffmpeg: str = "ffmpeg") -> bool:
    """把动机按 plan 铺进成片（原地：先写 .motif.tmp.mp4 再替换）。空规划/缺动机文件/ffmpeg 失败
    → False 且不动 in_video（compose 侧 || true 兜底，零回归）。"""
    import shutil
    import subprocess
    real = [p for p in plan if p.get("file") and os.path.isfile(p["file"])]
    if not real:
        return False
    args = build_overlay_args(in_video, in_video + ".motif.tmp.mp4", real,
                              shutil.which(ffmpeg) or ffmpeg)
    if not args:
        return False
    try:
        subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.replace(in_video + ".motif.tmp.mp4", in_video)
        return True
    except Exception:
        try:
            os.remove(in_video + ".motif.tmp.mp4")
        except OSError:
            pass
        return False


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="角色/势力主题动机登记表 + 确定性 cue 规划")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--min-gap", type=float, default=DEFAULT_MIN_GAP,
                    help=f"同一动机两次触发最小间隔秒（默认 {DEFAULT_MIN_GAP}，防动机刷屏）")
    ap.add_argument("--mix", metavar="成片.mp4",
                    help="把本集动机确定性铺进该成片（原地·视频流直copy只改音轨）；空规划=no-op")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode, ns.min_gap)
    if ns.mix:
        plan = res.get("filter_plan", [])
        # 动机文件相对作品根解析（motif.json 里 file 多为 素材/motif/xx.wav 相对路径）
        root = ns.root.rstrip("/")
        for p in plan:
            f = p.get("file", "")
            if f and not os.path.isabs(f):
                p["file"] = os.path.join(root, f)
        ok = run_overlay(ns.mix, plan) if plan else False
        print(f"主题动机铺设：{'已铺 ' + str(len(plan)) + ' 记 → ' + ns.mix if ok else '无可铺动机（no-op，成片不变）'}")
        return 0
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"=== 主题动机 cue sheet：{ns.root} {ns.episode}（已登记 {res['registered']} 段）===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    for c in res["cues"]:
        m, s = divmod(int(c["at"]), 60)
        print(f"  [{m:>2d}:{s:02d}] {c['key']} → {c['file']}  (gain {c['gain']:.2f} · {c['cue']})")
    if res["cues"]:
        print(f"\n共 {len(res['cues'])} 记动机铺设（同段 clip 确定性复用，跨集听感一致）。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
