#!/usr/bin/env python3
"""场景空间声学/混响——治「配音先行的对白轨毫无空间感：洞穴/大殿/旷野/寝殿一律干声」。

为什么需要：原生音画模式里「空间声学」只是视频后端的一个**文本契约字段**，可由后端在
原生生成台词时表达混响；但 n2d 的主力是**配音先行**，对白轨 voice_zh.wav 是 render_voice
逐句 TTS + gap 拼接出来的——这条轨**完全没有空间声学**：一句台词无论发生在密道、冷宫大殿
还是御花园，听感都是同一种贴脸干声，极其出戏。混响是空间最强的听觉线索，缺它则音画割裂。

做法——给每个声学空间类一条 ffmpeg 混响片段，按「该句所在场景」逐句注入 render_voice 既有的
逐句 FX 链（那条 `fx` 串，系统音机械感 FX 就走同一处）：
  fx = line_reverb(scene, TABLE) + (系统音FX or "")   # 二者皆以尾逗号收口，串接进 loudnorm 前

预设（声学空间类 → aecho 片段）。本机 ffmpeg 是裁剪版**无 afir/areverb**，故一律用 aecho
（卷积/反馈混响插件可能缺，aecho 几乎必带）。aecho=in_gain:out_gain:delays:decays：
  dry     默认·无混响（""）         —— 贴脸/画外音/无场景信息时的安全态
  room    小空间(寝殿/书房)轻早反射  aecho=0.7:0.5:18:0.25
  hall    大殿/厅堂·明显回声         aecho=0.8:0.85:60:0.4
  cave    洞穴/密道·长尾多次反射     aecho=0.8:0.9:120|180:0.5|0.3
  outdoor 旷野/庭院·极弱早反射       aecho=0.6:0.3:12:0.12

覆盖注册表（可选）：<作品根>/设定库/声学表.json
  {"冷宫大殿":"hall", "密道":"cave", "御花园":"outdoor", "寝殿":"room"}
  键=场景名或其子串，值=预设键；按**最长子串**匹配（"冷宫大殿" 先于 "大殿"），让具体场景压过泛类。
  键写后端无关的中文场景名即可；不写 → 该场景落 dry。

铁律·零回归（CRITICAL SAFETY）：
  缺 设定库/声学表.json（或坏）→ load 返回空表 → 每句 line_reverb(...) 恒为 ""（dry），
  render_voice 的 fx 链与今天**逐字节一致**，对白轨不发生任何变化。混响是 opt-in 增益，
  只有用户显式建表声明哪个场景对应哪类空间，才会有混响下到声学层。

纯函数核心（normalize/preset_for_scene/reverb_filter/line_reverb）无依赖、带 pytest。

用法（独立巡检）：python3 reverb_profile.py <作品根> 第N集 [--json]
  读 声学表.json + 时长清单.json，逐句把场景映到预设，列出哪句吃哪类混响（无表=全 dry）。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from typing import Dict, List

# 声学空间类 → ffmpeg aecho 片段（dry=无混响）。aecho 在裁剪版 ffmpeg 也几乎必带，故不用 afir/areverb。
PRESETS: Dict[str, str] = {
    "dry": "",
    "room": "aecho=0.7:0.5:18:0.25",
    "hall": "aecho=0.8:0.85:60:0.4",
    "cave": "aecho=0.8:0.9:120|180:0.5|0.3",
    "outdoor": "aecho=0.6:0.3:12:0.12",
}
DEFAULT_PRESET = "dry"


# ---------- 纯函数（无依赖 · pytest 覆盖） ----------

def normalize_acoustic_table(raw: dict) -> Dict[str, str]:
    """原始 json → {场景子串: 预设键}。容错：键/值 strip 成 str，丢空键、空值。
    未知预设键保留原样（reverb_filter 再当 dry 处理，不在此静默吞掉，便于巡检报错配）。纯函数·可测。"""
    out: Dict[str, str] = {}
    for scene, preset in (raw or {}).items():
        s = str(scene or "").strip()
        p = str(preset or "").strip()
        if not s or not p:
            continue
        out[s] = p
    return out


def preset_for_scene(scene_name: str, table: Dict[str, str], default: str = DEFAULT_PRESET) -> str:
    """场景名 → 预设键，按**最长子串**匹配（"冷宫大殿" 压过 "大殿"）。
    场景名空 / 表空 / 无任一键命中 → default（默认 dry）。纯函数·可测。"""
    s = scene_name or ""
    if not s or not table:
        return default
    best_key = ""
    for sub in table:
        if sub and sub in s and len(sub) > len(best_key):
            best_key = sub
    return table[best_key] if best_key else default


def reverb_filter(preset_key: str) -> str:
    """预设键 → ffmpeg 混响片段。dry/未知键 → ""；非空时**以尾逗号收口**，
    好直接前插进 render_voice 既有的 `fx` 串（与 SYS_AUDIO_FX 同样以逗号结尾的约定一致）。纯函数·可测。"""
    frag = PRESETS.get(preset_key or "", "")
    return (frag + ",") if frag else ""


def line_reverb(scene_name: str, table: Dict[str, str], default: str = DEFAULT_PRESET) -> str:
    """便捷口：场景名 + 声学表 → 可直接前插 fx 链的混响片段（含尾逗号，dry/缺表="")。纯函数·可测。"""
    return reverb_filter(preset_for_scene(scene_name, table, default))


# ---------- IO ----------

def load_acoustic_table(root: str) -> Dict[str, str]:
    """读 <root>/设定库/声学表.json；缺/坏 → {}（→ 每句 dry = 今日行为，零回归）。"""
    path = os.path.join(root, "设定库", "声学表.json")
    try:
        return normalize_acoustic_table(json.load(open(path, encoding="utf-8")))
    except Exception:
        return {}


def _shot_scene_index(root: str, ep: str) -> Dict[str, str]:
    """best-effort：从 出图/<ep>/prompt/01_分镜出图.md 抽 {镜头号/CLIP号 → 场景串}。
    场景串取自镜头标题（## 镜头 N · EPxxCLIPnn <标题>）+ 紧随其后的「光位锚」（常含真实场景名，
    如『冷宫寝殿…』）。解析不到任何镜头 → {}（上层据此把该句留空场景=dry 并记 note）。"""
    md = os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")
    if not os.path.isfile(md):
        return {}
    try:
        txt = open(md, encoding="utf-8").read()
    except Exception:
        return {}
    idx: Dict[str, str] = {}
    # 以镜头标题切块；块内首个「光位锚」行并入场景串（光位锚常点名真实场景，如『冷宫寝殿』）
    blocks = re.split(r"(?m)^##\s*镜头\s*", txt)
    for blk in blocks[1:]:
        head = blk.splitlines()[0].strip() if blk.strip() else ""
        if not head:
            continue
        scene = head  # 形如 "1 · EP01_CLIP01 冷开场·铜镜错脸"
        m = re.search(r"光位锚[^：:]*[：:]\s*([^\n]+)", blk)
        if m:
            scene = scene + " " + m.group(1).strip()
        # 该块的可索引键：数字镜头号("镜头1"/"1") 与 CLIP 号(EP01_CLIP01 / CLIP01)
        hm = re.match(r"(\d+)", head)
        if hm:
            idx[hm.group(1)] = scene
            idx["镜头" + hm.group(1)] = scene
        for cm in re.finditer(r"(EP\d+_CLIP\d+|CLIP\d+)", head):
            idx[cm.group(1)] = scene
    return idx


def _resolve_scene(shot: str, shot_scene: Dict[str, str]) -> str:
    """时长清单条目的「镜头」值（如 '镜头1' / 'EP01_CLIP01' / '1'）→ 场景串。解析不到返回 ""。"""
    s = (shot or "").strip()
    if not s:
        return ""
    if s in shot_scene:
        return shot_scene[s]
    for token in re.findall(r"EP\d+_CLIP\d+|CLIP\d+|\d+", s):
        if token in shot_scene:
            return shot_scene[token]
    return ""


def _load_manifest(root: str, ep: str) -> List[dict]:
    p = os.path.join(root, "合成", ep, "配音", "时长清单.json")
    try:
        data = json.load(open(p, encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def analyze(root: str, ep: str) -> dict:
    table = load_acoustic_table(root)
    res: dict = {"available": bool(table), "presets": sorted(PRESETS),
                 "table": table, "lines": [], "notes": []}
    if not table:
        res["notes"].append("无 设定库/声学表.json——对白轨全程干声(dry)，与今日逐字节一致(零回归)。"
                            "建场景→空间类映射(如 {\"冷宫大殿\":\"hall\",\"密道\":\"cave\"}) 即可逐句注入混响。")
    manifest = _load_manifest(root, ep)
    if not manifest:
        res["notes"].append(f"缺 合成/{ep}/配音/时长清单.json——只校声学表本体，未逐句映场景。先跑 n2d-voice。")
        return res
    shot_scene = _shot_scene_index(root, ep)
    if not shot_scene:
        res["notes"].append(f"未能从 出图/{ep}/prompt/01_分镜出图.md 解析镜头→场景——本集逐句场景留空=dry(诚实降级)。")
    n_dry = 0
    for entry in manifest:
        shot = str(entry.get("镜头", "") or "")
        scene = _resolve_scene(shot, shot_scene)
        preset = preset_for_scene(scene, table) if scene else DEFAULT_PRESET
        if preset == DEFAULT_PRESET:
            n_dry += 1
        res["lines"].append({"shot": shot, "scene": scene, "preset": preset})
    res["dry_lines"] = n_dry
    return res


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    table_n = len(res.get("table") or {})
    print(f"=== 场景空间声学/混响（对白轨）：{ns.root} {ns.episode}（声学表 {table_n} 条）===")
    for note in res["notes"]:
        print("ℹ️ " + note)
    if res["lines"]:
        wet = [l for l in res["lines"] if l["preset"] != DEFAULT_PRESET]
        print(f"逐句：{len(res['lines'])} 句 · 加混响 {len(wet)} · 干声 {res.get('dry_lines', 0)}")
        for l in res["lines"]:
            tag = l["preset"] if l["preset"] != DEFAULT_PRESET else "dry"
            print(f"  {l['shot'] or '?':<14} [{tag}] {l['scene'] or '(场景未解析→dry)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
