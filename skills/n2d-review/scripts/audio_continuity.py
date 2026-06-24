#!/usr/bin/env python3
"""音频连续性机检（D 档·配音情绪弧 VEA + 口音方言 ACC + 音乐衔接 BGM）——补音频侧"白区"。

2026 深搜结论：音频侧连续性 QA 几乎没有 benchmark（除联合生成），是可领跑的空白。本 skill 不做音频
分析（重音频环境常缺），改做**文本/结构**机检——查"配音意图有没有写对/锁住"，落点在产配音前的源头：

  VEA 配音情绪弧：读 voiceover.txt 逐句 `[镜头N·角色·情绪·语速] 台词`——
    ① 台词含强情绪内容(哭喊/怒吼/求饶/崩溃…)但情绪标注归 neutral/平淡 → warn（配音会念平，情绪没跟上画面）；
    ② 句子缺情绪标注 → warn（无方向→后端默认 neutral 平念）。情绪标注驱动 MiniMax/火山逐句表演（见 render_voice）。
  ACC 口音方言：voicemap 可登记每角色 `accent`/`口音`/`方言`——同一 voice_key 被多角色用却口音冲突 → warn；
    已锁口音的角色 → 出验收提醒（口音是否全程一致须人听辨，无音频分析不臆断）。
  BGM 音乐衔接：读 bgm.txt 相邻配乐段的速度词（加速/急 ↔ 抽空/慢/缓），无过渡硬接 → warn（调性/速度whiplash）。

诚实边界：全 advisory（warn）。台词强情绪用关键词近似、BGM 用 prose 速度词启发，命中只作"可疑→人听辨"初筛。
缺 voiceover.txt → available=False 优雅跳过。纯函数（解析/情绪归类/各 findings）无依赖、带 pytest。

用法：python3 audio_continuity.py <作品根> 第N集 [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

# voiceover.txt 行格式（与 n2d-script beat_audit / n2d-voice render_voice 同源；本 skill 自留不跨 import）。
LINE_RE = re.compile(r"^\[镜头(\d+)·([^·\]]+)·([^·\]]+?)(?:·([^·\]]+))?\]\s*(.*)$")
# 规范情绪关键词归类（vendored 自 render_voice.classify_emo）。
_STRONG_CLASSES = ("angry", "fearful", "sad")
# 台词内容里的强情绪标记（比情绪描述词更宽：覆盖喊/求/恨/杀/血等剧情强词）。
STRONG_LINE_MARKERS = (
    "哭", "泣", "嚎", "嘶吼", "咆哮", "怒吼", "尖叫", "惨叫", "崩溃", "绝望", "悲恸", "痛苦",
    "救命", "求求", "饶命", "饶了", "住手", "放开", "不要", "滚", "恨", "杀", "血债", "偿命",
    "狂喜", "大笑", "狂笑", "颤抖", "发抖", "惊恐", "震惊",
)
# BGM 速度词（快 vs 慢两极），相邻段两极硬接=whiplash。
_FAST_WORDS = ("加速", "急促", "急", "快", "重击", "炸", "高潮", "密集鼓点", "狂", "升调")
_SLOW_WORDS = ("抽空", "几乎无", "留白", "慢", "缓", "舒缓", "空灵", "停顿", "悬停", "静", "降调", "弱")
_TRANSITION_WORDS = ("渐", "过渡", "推向", "转入", "递进", "铺", "拉起", "收", "落")


# ── 纯函数（无依赖·可测） ──────────────────────────────────────────────────────

def classify_emo(desc: str) -> str:
    """情绪描述/台词 → 规范情绪类（angry/fearful/sad/happy/serious/neutral）。vendored·纯函数·可测。"""
    d = str(desc or "")
    if re.search(r"愤怒|怒|质问|逼问|斥|吼|暴|咆", d):
        return "angry"
    if re.search(r"惊恐|惊|恐|怕|慌|颤", d):
        return "fearful"
    if re.search(r"悲|哀|哭|泣|痛|绝望|心碎|呜咽", d):
        return "sad"
    if re.search(r"喜|笑|窃喜|得意|欣|甜|雀跃", d):
        return "happy"
    if re.search(r"冷冽|冷|阴狠|狠|讥|嘲|森|淡漠", d):
        return "serious"
    return "neutral"


def parse_voiceover(text: str) -> List[Dict[str, Any]]:
    """voiceover.txt → [{shot, role, emotion, line}]。只取 `[镜头N·…]` 行。纯函数·可测。"""
    out: List[Dict[str, Any]] = []
    for raw in str(text or "").splitlines():
        m = LINE_RE.match(raw.strip())
        if not m:
            continue
        out.append({"shot": int(m.group(1)), "role": m.group(2).strip(),
                    "emotion": (m.group(3) or "").strip(), "line": (m.group(5) or "").strip()})
    return out


def line_is_strong(line: str) -> bool:
    """台词内容是否含强情绪（关键词近似）。纯函数·可测。"""
    t = str(line or "")
    return any(k in t for k in STRONG_LINE_MARKERS) or classify_emo(t) in _STRONG_CLASSES


def vea_findings(lines: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """配音情绪弧 findings：台词强情绪×标注平淡 / 缺标注。纯函数·可测。"""
    rows: List[Dict[str, Any]] = []
    for ln in lines:
        shot, role, emo, text = ln.get("shot"), ln.get("role"), ln.get("emotion", ""), ln.get("line", "")
        loc = f"镜头{shot}"
        if not emo:
            rows.append({"shot": loc, "role": role, "verdict": "warn",
                         "message": f"{loc}·{role}：台词缺情绪标注——配音后端默认平念(neutral)，"
                                    f"补 `[镜头{shot}·{role}·情绪]` 让念白带表演。"})
            continue
        if line_is_strong(text) and classify_emo(emo) == "neutral":
            rows.append({"shot": loc, "role": role, "verdict": "warn",
                         "message": f"{loc}·{role}：台词含强情绪但配音标注「{emo}」归平淡(neutral)——"
                                    f"配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。"})
    return rows


def accent_findings(voicemap: Optional[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """口音/方言 findings：同 voice_key 多角色口音冲突 → warn；已锁口音 → 验收提醒(info)。纯函数·可测。"""
    rows: List[Dict[str, Any]] = []
    if not isinstance(voicemap, Mapping):
        return rows
    chars = voicemap.get("characters") if isinstance(voicemap.get("characters"), Mapping) else voicemap
    if not isinstance(chars, Mapping):
        return rows
    by_key: Dict[str, set] = {}
    for name, cfg in chars.items():
        if not isinstance(cfg, Mapping):
            continue
        accent = str(cfg.get("accent") or cfg.get("口音") or cfg.get("方言") or "").strip()
        if not accent:
            continue
        key = str(cfg.get("voice_key") or cfg.get("key") or cfg.get("音色键") or name).strip()
        by_key.setdefault(key, set()).add(accent)
        rows.append({"shot": str(name), "role": str(name), "verdict": "info",
                     "message": f"角色 {name} 已锁口音/方言「{accent}」：配音/验收时人听辨是否全程一致"
                                f"（无音频分析，不臆断）。"})
    for key, accents in by_key.items():
        if len(accents) > 1:
            rows.append({"shot": f"voice_key={key}", "verdict": "warn",
                         "message": f"voice_key「{key}」被登记了冲突口音 {sorted(accents)}——"
                                    f"同一音色槽口音应唯一，核对 voicemap.json。"})
    return rows


def _norm_shot(v: Any) -> Optional[int]:
    m = re.search(r"(\d+)", str(v if v is not None else ""))
    return int(m.group(1)) if m else None


def _strong_designed(emo: str, line: str) -> bool:
    """设计态是否强情绪（高唤醒）：台词内容强 或 标注归 怒/惊/悲/喜。"""
    return line_is_strong(line) or classify_emo(emo) in _STRONG_CLASSES or classify_emo(emo) == "happy"


def emotion_audio_findings(lines: Sequence[Mapping[str, Any]],
                           flow: Optional[Sequence[Mapping[str, Any]]]) -> List[Dict[str, Any]]:
    """设计情绪 × 配音声学能量 reconcile（治"强情绪台词却配音念得平"）。

    flow = `合成/{集}/配音/emotion_flow.json` 段列表 `[{shot, energy:{energy_score}, emotion_applied}]`。
    判：设计为强情绪的镜，其配音声学能量落在本集**底四分位** → warn（情绪没演出来）。
    诚实边界：energy 是 ffmpeg 音量代理(非语义)，故 ① 能量分布太平(占位/say)直接跳过不臆断；
    ② 样本 <4 不判分位；③ 全 advisory(warn)，命中=可疑→人听辨。纯函数·可测。"""
    rows: List[Dict[str, Any]] = []
    if not isinstance(flow, (list, tuple)):
        return rows
    by_shot: Dict[int, float] = {}
    energies: List[float] = []
    for seg in flow:
        if not isinstance(seg, Mapping):
            continue
        e = seg.get("energy")
        score = e.get("energy_score") if isinstance(e, Mapping) else None
        if not isinstance(score, (int, float)):
            continue
        energies.append(float(score))
        sh = _norm_shot(seg.get("shot"))
        if sh is not None:
            by_shot[sh] = float(score)
    if len(energies) < 4:
        return rows
    if max(energies) - min(energies) < 0.05:
        return rows  # 能量几乎无起伏（占位/say 或恒响）——无法区分，不臆断
    q1 = sorted(energies)[len(energies) // 4]
    line_by_shot = {_norm_shot(ln.get("shot")): ln for ln in lines}
    for sh, score in sorted(by_shot.items()):
        ln = line_by_shot.get(sh)
        if not ln:
            continue
        emo, text = str(ln.get("emotion") or ""), str(ln.get("line") or "")
        if _strong_designed(emo, text) and score <= q1:
            rows.append({"shot": f"镜头{sh}", "role": ln.get("role"), "verdict": "warn",
                         "message": f"镜头{sh}·{ln.get('role')}：设计为强情绪（{emo or '台词强情绪'}）但配音声学能量垫底"
                                    f"（energy {score:.2f} ≤ 本集 Q1 {q1:.2f}）——情绪没演出来，重配/调表演语速，或确认是克制反差。"})
    return rows


def _bgm_cue_lines(text: str) -> List[str]:
    """bgm.txt → 配乐段要点行（以 - 起的 bullet）。纯函数·可测。"""
    out: List[str] = []
    for raw in str(text or "").splitlines():
        s = raw.strip()
        if s.startswith(("-", "*", "•")):
            out.append(s.lstrip("-*• ").strip())
    return out


def _tempo_of(cue: str) -> Optional[str]:
    fast = any(w in cue for w in _FAST_WORDS)
    slow = any(w in cue for w in _SLOW_WORDS)
    if fast and not slow:
        return "fast"
    if slow and not fast:
        return "slow"
    return None


def bgm_findings(bgm_text: str) -> List[Dict[str, Any]]:
    """音乐衔接 findings：相邻配乐段速度两极硬接(快↔慢)且无过渡词 → warn。纯函数·可测。"""
    cues = _bgm_cue_lines(bgm_text)
    rows: List[Dict[str, Any]] = []
    prev_t = None
    prev_cue = ""
    for cue in cues:
        t = _tempo_of(cue)
        if prev_t and t and {prev_t, t} == {"fast", "slow"}:
            if not any(w in cue or w in prev_cue for w in _TRANSITION_WORDS):
                rows.append({"shot": "BGM", "verdict": "warn",
                             "message": f"配乐相邻段速度两极硬接（{prev_t}→{t}）且无过渡："
                                        f"「{prev_cue[:18]}」→「{cue[:18]}」；调性/速度whiplash，"
                                        f"加渐变过渡或确认是卡点切。"})
        if t:
            prev_t, prev_cue = t, cue
    return rows


# ── 装载 + 编排（best-effort I/O） ─────────────────────────────────────────────

def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _load_voicemap(root: Path) -> Optional[dict]:
    try:
        data = json.loads((root / "设定库" / "voicemap.json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _load_emotion_flow(root: Path, ep: str) -> Optional[list]:
    """读 n2d-voice 产的 emotion_flow.json（声学能量曲线）。缺则 None（优雅跳过）。"""
    for cand in (root / "合成" / ep / "配音" / "emotion_flow.json",
                 root / "配音" / ep / "emotion_flow.json"):
        try:
            data = json.loads(cand.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            continue
    return None


def _voiceover_path(root: Path, ep: str) -> Path:
    for cand in (root / "脚本" / ep / "voiceover.txt", root / "配音" / ep / "voiceover.txt"):
        if cand.is_file():
            return cand
    return root / "脚本" / ep / "voiceover.txt"


def analyze(root: str, ep: str) -> Dict[str, Any]:
    rootp = Path(root)
    vo_text = _read(_voiceover_path(rootp, ep))
    if not vo_text.strip():
        return {"available": False, "vea": [], "acc": [], "bgm": [],
                "notes": [f"{ep} 无 voiceover.txt——音频连续性机检跳过（先跑 n2d-script 配音文案）。"]}
    lines = parse_voiceover(vo_text)
    vea = vea_findings(lines)
    acc = accent_findings(_load_voicemap(rootp))
    bgm_text = _read(rootp / "脚本" / ep / "bgm.txt") or _read(rootp / "脚本" / ep / f"bgm_{ep}.txt")
    bgm = bgm_findings(bgm_text)
    flow = _load_emotion_flow(rootp, ep)
    vea_audio = emotion_audio_findings(lines, flow)
    notes: List[str] = []
    if not _load_voicemap(rootp):
        notes.append("无 设定库/voicemap.json——口音方言(ACC)检跳过（可在 voicemap 角色加 accent 字段锁口音）。")
    if not bgm_text.strip():
        notes.append("无 bgm.txt——音乐衔接(BGM)检跳过。")
    if flow is None:
        notes.append("无 emotion_flow.json——设计情绪×配音能量 reconcile 跳过（先跑 n2d-voice 配音生成）。")
    return {"available": True, "vea": vea, "vea_audio": vea_audio, "acc": acc, "bgm": bgm, "notes": notes}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="音频连续性机检（VEA/ACC/BGM）")
    ap.add_argument("root")
    ap.add_argument("ep")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    rep = analyze(args.root, args.ep)
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0
    if not rep.get("available"):
        print("· " + "；".join(rep.get("notes", []) or ["跳过"]))
        return 0
    def _warns(rows):
        return [r for r in rows if r.get("verdict") == "warn"]
    print(f"# 音频连续性：情绪弧 {len(_warns(rep['vea']))} · 情绪×能量 {len(_warns(rep.get('vea_audio', [])))} · "
          f"口音 {len(_warns(rep['acc']))} · 音乐衔接 {len(_warns(rep['bgm']))}")
    for r in _warns(rep["vea"]) + _warns(rep.get("vea_audio", [])) + _warns(rep["acc"]) + _warns(rep["bgm"]):
        print(f"🟡 {r.get('message')}")
    for n in rep.get("notes", []):
        print(f"· {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
