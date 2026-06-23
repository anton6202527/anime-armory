#!/usr/bin/env python3
"""辨识标记一致性机检（MK1·疤痕/胎记/纹身/异瞳/痣/义体 等"载剧情"辨识标记的持久性）。

2026 实战缺口：脸/发型/服装都锁住了，**辨识标记**仍会跨镜/跨集悄悄漂——左腕旧疤这一镜有、下一镜
没了；天生异瞳忽蓝忽黑；认亲胎记换了位置。这类标记往往**载剧情**（认亲/战损/血统/禁术印记），
丢一次既崩脸又崩剧情，比换件衣服严重得多。face/outfit/hair 三个机检都不专门盯它。

机制（纯文本/结构·零重依赖·永不降级跳过）：
  identity_registry 的每个角色形态可登记 `identity_marks[]`，每条标记带：
    type(疤痕/胎记/纹身/瞳色/痣/义体…) · region(部位) · side(left/right/center) · color ·
    persistence("permanent" 或 {"acquired_at":"第N集"}) · plot_load(是否载剧情) · keywords(机检搜索词)
  对本集每个镜头：语料 = storyboard 镜头文本 ⊕ `出图/<集>/prompt/01_分镜出图.md` 对应 Clip 段。
  对该镜在场角色的每条标记：
    - 永久标记 / 已获得标记（本集 ≥ acquired_at）：标记词未出现在语料 → 🟡warn（疑似漂移/丢失，
      或本镜被遮挡，人核对后补回 prompt）。
    - 未获得标记（本集 < acquired_at）：标记词却出现在语料 → 🔴block（时间线穿帮：标记早于获得集出现）。

诚实边界：这是**文本/结构**机检，查的是"标记有没有写进分镜/出图 prompt"，不是像素级"图里有没有
这道疤"。永久标记缺失只报 warn（可能合理遮挡），靠人判并排看；像素/VLM 在场核验（OWLv2/外观判官）
是后续增强档（见 references）。无 identity_marks 登记 → available=False 优雅跳过，不假报。

用法：python3 marks_consistency.py <作品根> 第N集 [--json]
纯 stdlib；纯函数（标记归一/搜索词/Clip 段映射/判定）带 pytest 覆盖。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple


# ── 纯函数（无依赖·可测） ──────────────────────────────────────────────────────

def episode_num(ep: str) -> Optional[int]:
    """从 '第N集' 抽集号；抽不到 → None。"""
    m = re.search(r"(\d+)", str(ep or ""))
    return int(m.group(1)) if m else None


def split_aliases(*texts: str) -> Set[str]:
    """名字/asset_key/id 切成别名集（≥2 字才留，避免单字误命中）。"""
    out: Set[str] = set()
    for t in texts:
        for part in re.split(r"[/／、,，|\s]+", str(t or "")):
            p = part.strip()
            if len(p) >= 2:
                out.add(p)
    return out


def normalize_mark(raw: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """单条 identity_marks 归一。无 type/region 又无 keywords/mark_id → 无法机检，返回 None。

    persistence 归一为 ('permanent', None) 或 ('acquired', acquired_episode_num)；
    acquired_at 写 '第N集' 或纯数字均可，解析不出集号 → 退化按 permanent（有总比漏好）。"""
    if not isinstance(raw, Mapping):
        return None
    mark_id = str(raw.get("mark_id") or raw.get("id") or "").strip()
    mtype = str(raw.get("type") or "").strip()
    region = str(raw.get("region") or "").strip()
    color = str(raw.get("color") or "").strip()
    side = str(raw.get("side") or "").strip()
    keywords = [str(k).strip() for k in (raw.get("keywords") or []) if str(k).strip()]
    pers_raw = raw.get("persistence", "permanent")
    persistence, acquired_ep = "permanent", None
    if isinstance(pers_raw, Mapping):
        n = episode_num(str(pers_raw.get("acquired_at") or ""))
        if n is None and isinstance(pers_raw.get("acquired_at"), (int, float)):
            n = int(pers_raw["acquired_at"])
        if n is not None:
            persistence, acquired_ep = "acquired", n
    elif isinstance(pers_raw, str) and pers_raw.strip() and pers_raw.strip() != "permanent":
        n = episode_num(pers_raw)
        if n is not None:
            persistence, acquired_ep = "acquired", n
    mark = {
        "mark_id": mark_id, "type": mtype, "region": region, "side": side, "color": color,
        "persistence": persistence, "acquired_ep": acquired_ep,
        "plot_load": bool(raw.get("plot_load", False)), "keywords": keywords,
        "detect_phrase": str(raw.get("detect_phrase") or "").strip(),  # 像素在场检测用（OWLv2，英文最准）
    }
    if not mark_tokens(mark):
        return None
    return mark


def mark_tokens(mark: Mapping[str, Any]) -> Set[str]:
    """该标记的机检搜索词：显式 keywords ∪ 部位+类型组合 ∪ 类型 ∪ 部位 ∪ 颜色 ∪ mark_id 去前缀。
    全部 ≥2 字（单字如"疤"易误命中，剔除）。纯函数·可测。"""
    toks: Set[str] = set(k for k in (mark.get("keywords") or []) if len(str(k)) >= 2)
    region = str(mark.get("region") or "").strip()
    mtype = str(mark.get("type") or "").strip()
    color = str(mark.get("color") or "").strip()
    if region and mtype:
        toks.add(region + mtype)
    for v in (mtype, region, color):
        if len(v) >= 2:
            toks.add(v)
    mid = str(mark.get("mark_id") or "").strip()
    if mid.upper().startswith("MARK_"):
        mid = mid[5:]
    for part in re.split(r"[_\-\s]+", mid):
        if len(part) >= 2 and not part.isdigit():
            toks.add(part)
    return toks


def text_has_mark(text: str, mark: Mapping[str, Any]) -> bool:
    """语料文本里是否提到该标记（任一搜索词命中）。"""
    t = str(text or "")
    return any(tok in t for tok in mark_tokens(mark))


def collect_character_marks(registry: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """identity_registry → [{aliases, char_name, char_id, form, marks:[normalized]}]，只收有可机检标记的形态。"""
    out: List[Dict[str, Any]] = []
    for ch in (registry.get("characters") or []):
        if not isinstance(ch, Mapping):
            continue
        cid = str(ch.get("id") or "").strip()
        cname = str(ch.get("name") or "").strip()
        for form in (ch.get("forms") or []):
            if not isinstance(form, Mapping):
                continue
            marks = [m for m in (normalize_mark(r) for r in (form.get("identity_marks") or [])) if m]
            if not marks:
                continue
            aliases = split_aliases(cname, form.get("asset_key") or "", cid)
            if cid:
                aliases.add(cid)
            out.append({
                "aliases": aliases, "char_name": cname or cid, "char_id": cid,
                "form": str(form.get("form") or "常态"), "marks": marks,
            })
    return out


def clip_storyboard_text(clip: Mapping[str, Any]) -> str:
    """storyboard 单 clip 的可搜索文本（label/scene/continuity/各 shot desc）。"""
    parts: List[str] = [str(clip.get("label") or ""), str(clip.get("scene") or "")]
    cont = clip.get("continuity") or {}
    if isinstance(cont, Mapping):
        parts += [str(cont.get("start_state") or ""), str(cont.get("end_state") or "")]
    for s in (clip.get("shots") or []):
        if isinstance(s, Mapping):
            parts += [str(s.get("desc") or ""), str(s.get("video_prompt") or "")]
    return " ".join(parts)


def split_prompt_sections(md_text: str) -> List[Tuple[Optional[str], str]]:
    """01_分镜出图.md 按 '## Clip' 切段 → [(clip_id_or_None, 段文本)]。
    clip_id 从段内 'EPxx_CLIPyy' token 抽；抽不到留 None（交调用方按序号兜底）。纯函数·可测。"""
    if not md_text:
        return []
    blocks: List[Tuple[Optional[str], str]] = []
    chunks = re.split(r"(?m)^##\s+Clip\b", md_text)
    for chunk in chunks[1:]:  # chunks[0] 是首个 ## Clip 之前的前言
        m = re.search(r"(EP\d+_CLIP\d+)", chunk)
        blocks.append((m.group(1) if m else None, chunk))
    return blocks


def section_for_clip(clip_id: str, clip_index: int,
                     sections: Sequence[Tuple[Optional[str], str]]) -> str:
    """某 clip 的出图 prompt 段：先按 clip_id 精确命中，否则按序号兜底（## Clip N = 第 N 段）。"""
    cid = str(clip_id or "").strip()
    if cid:
        for sec_id, text in sections:
            if sec_id == cid:
                return text
    if 0 <= clip_index < len(sections):
        return sections[clip_index][1]
    return ""


def evaluate_clip_marks(corpus: str, present_chars: Sequence[Mapping[str, Any]],
                        ep_n: Optional[int], clip_id: str) -> List[Dict[str, Any]]:
    """单镜判定 → shot 行列表（verdict ok/warn/block）。纯函数·可测。

    永久 / 已获得标记缺失 → warn；未获得标记提前出现 → block（时间线穿帮）。"""
    rows: List[Dict[str, Any]] = []
    for entry in present_chars:
        for mark in entry.get("marks") or []:
            acq = mark.get("acquired_ep")
            not_yet = (mark.get("persistence") == "acquired" and ep_n is not None
                       and acq is not None and ep_n < acq)
            present = text_has_mark(corpus, mark)
            desc = _mark_desc(mark)
            base = {"shot": clip_id, "char": entry.get("char_name"), "mark": mark.get("mark_id") or desc}
            if not_yet:
                if present:
                    rows.append({**base, "verdict": "block",
                                 "message": f"{clip_id}：辨识标记『{desc}』在获得集第{acq}集之前就出现"
                                            f"（角色 {entry.get('char_name')}）——时间线穿帮，删除该标记或核对获得集。"})
                else:
                    rows.append({**base, "verdict": "ok"})
                continue
            # 永久 or 已获得：应当出现
            if present:
                rows.append({**base, "verdict": "ok"})
            else:
                load = "（载剧情）" if mark.get("plot_load") else ""
                rows.append({**base, "verdict": "warn",
                             "message": f"{clip_id}：角色 {entry.get('char_name')} 的辨识标记『{desc}』{load}"
                                        f"未在该镜 storyboard/出图prompt 中出现——疑似漂移/丢失，"
                                        f"核对后补回 prompt，或确认本镜该部位被遮挡/不入画。"})
    return rows


def _mark_desc(mark: Mapping[str, Any]) -> str:
    bits = [str(mark.get("color") or ""), str(mark.get("region") or ""), str(mark.get("type") or "")]
    label = "".join(b for b in bits if b).strip()
    return label or str(mark.get("mark_id") or "标记")


# ── 装载 + 编排（best-effort I/O） ─────────────────────────────────────────────

def _load_json(path: Path) -> Optional[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _present(corpus: str, char_marks: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    return [c for c in char_marks if any(a in corpus for a in c.get("aliases") or set())]


def presence_sidecar_shots(sidecar: Optional[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """marks_presence_<集>.json 的像素缺席 findings → MK1 shot 行（verdict=warn）。

    像素证据（OWLv2 等）对小标记/侧脸/遮挡噪声大，**缺席≠一定丢**，故一律 warn（不硬 block），
    与文本档互补。无 sidecar / 无 findings → []。纯函数·可测。"""
    if not isinstance(sidecar, Mapping):
        return []
    rows: List[Dict[str, Any]] = []
    for f in sidecar.get("findings") or []:
        if not isinstance(f, Mapping) or f.get("present"):
            continue
        shot = str(f.get("shot") or "")
        mark = str(f.get("asset") or "标记")
        conf = f.get("confidence")
        ctxt = f"（置信 {conf}）" if conf is not None else ""
        rows.append({"shot": shot, "char": f.get("char"), "mark": mark, "verdict": "warn",
                     "message": f"{shot}：辨识标记『{mark}』像素在场检测未在该帧检出{ctxt}——"
                                f"图里可能真丢了（也可能被遮挡/侧脸/标记过小漏检），人核对该帧。"})
    return rows


def analyze(root: str, ep: str) -> Dict[str, Any]:
    rootp = Path(root)
    registry = _load_json(rootp / "出图" / "共享" / "identity_registry.json")
    if not registry:
        return {"available": False, "shots": [],
                "notes": ["identity_registry.json 缺失/无效——辨识标记机检跳过。"]}
    char_marks = collect_character_marks(registry)
    if not char_marks:
        return {"available": False, "shots": [],
                "notes": ["无角色登记 identity_marks——辨识标记机检跳过。"
                          "（若有疤痕/胎记/纹身/异瞳等载剧情标记，在 identity_registry 的 forms[].identity_marks 登记后启用）"]}
    sb = _load_json(rootp / "脚本" / ep / "storyboard.json")
    clips = (sb or {}).get("clips") or (sb or {}).get("shots") or []
    if not clips:
        return {"available": False, "shots": [],
                "notes": [f"{ep} storyboard.json 缺失/无 clips——先跑 n2d-script 分镜设计再机检辨识标记。"]}
    prompt_md = ""
    try:
        prompt_md = (rootp / "出图" / ep / "prompt" / "01_分镜出图.md").read_text(encoding="utf-8")
    except Exception:
        pass
    sections = split_prompt_sections(prompt_md)
    ep_n = episode_num(ep)
    shots: List[Dict[str, Any]] = []
    notes: List[str] = []
    if not prompt_md:
        notes.append("缺 出图/{}/prompt/01_分镜出图.md——仅按 storyboard 文本机检（出图 prompt 的标记锁未纳入，精度降级）。".format(ep))
    for idx, clip in enumerate(clips):
        if not isinstance(clip, Mapping):
            continue
        clip_id = str(clip.get("id") or clip.get("label") or f"Clip{idx+1:02d}")
        corpus = clip_storyboard_text(clip) + " " + section_for_clip(str(clip.get("id") or ""), idx, sections)
        present = _present(corpus, char_marks)
        shots.extend(evaluate_clip_marks(corpus, present, ep_n, clip_id))
    # 可选：像素在场 sidecar（marks_presence_runner 产；无则纯文本档，不假报）
    sidecar = _load_json(rootp / "生产数据" / f"marks_presence_{ep}.json")
    pixel_shots = presence_sidecar_shots(sidecar)
    if pixel_shots:
        shots.extend(pixel_shots)
        notes.append(f"已合并像素在场 sidecar：{len(pixel_shots)} 处标记像素未检出（warn·人核对）。")
    return {"available": True, "shots": shots, "notes": notes}


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="辨识标记一致性机检（MK1）")
    ap.add_argument("root")
    ap.add_argument("ep")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    report = analyze(args.root, args.ep)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if not report.get("available"):
        print("· " + "；".join(report.get("notes", []) or ["跳过"]))
        return 0
    blocks = [s for s in report["shots"] if s.get("verdict") == "block"]
    warns = [s for s in report["shots"] if s.get("verdict") == "warn"]
    print(f"# 辨识标记一致性（MK1）：🔴穿帮 {len(blocks)} · 🟡疑似漂移/丢失 {len(warns)}")
    for s in blocks + warns:
        icon = "🔴" if s.get("verdict") == "block" else "🟡"
        print(f"{icon} {s.get('message')}")
    for n in report.get("notes", []):
        print(f"· {n}")
    return 2 if blocks else 0


if __name__ == "__main__":
    sys.exit(main())
