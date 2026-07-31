#!/usr/bin/env python3
"""字幕对齐(L1) —— 双语字幕「短语边界 / 阅读速度 / 译文完整性」机检。

补 `mechanical_check.py` 的盲区：它已查 中英 **条数** 一致、时间码对账、单行溢出、
脏标点，但**不查每条 cue 的中↔英是否真的对应**——条数对齐≠语义对齐。海外投放双语
字幕是 n2d 核心目标，字幕断句错位 / 漏译 / 读太快直接掉留存。本检测器逐 cue 抓：

  · 漏译/空译        —— 某语种该 cue 为空或英文整条仍是中文（block）
  · 断句粒度不一致    —— 中文 1 句被英文拆成 2 句（或反之）= 短语边界错位（warn）
  · 长度比离群        —— 中英字数比偏离**本集中位**（自标定 band）→ 疑似漏译/过译/截断（warn）
  · 阅读速度过快      —— cps 超行业可读上限（中文 9 / 英文 21 cps，Netflix 计时文本口径）→ 看不完（warn）

纯函数（断句计数 / 字数 / cps / 自标定 band / 逐 cue 判级）无依赖、带 pytest。
SRT 路径与 mechanical_check 同源：`脚本/<集>/字幕_{中文,英文}.srt`。
缺任一 SRT → available=False 优雅跳过（未到分镜设计阶段则正常）。

成片烧录后 OCR 回测（编码/换行把字幕压糊）是可选后续——见 `ocr_available()`，缺 OCR 库时
显式标跳过、绝不臆造，由人判兜或装库后单独跑。

用法：python3 subtitle_align.py <作品根> 第N集 [--json]
退出码：有任一 block → 1，否则 0。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Sequence, Tuple

# 阅读速度上限（字符/秒）——人眼可读是**绝对**约束（不像视觉漂移需自标定），按 Netflix
# 计时文本风格指南：简体中文 9 cps、英文成人 ~17–21 cps。取 21 留余量，超即太快看不完。
ZH_CPS_MAX = 9.0
EN_CPS_MAX = 21.0
# 长度比离群带：本集中位 × [1/K, K]，自标定（中英字数比因题材/句式天然波动，绝对阈值会误杀）。
RATIO_BAND_K = 2.4
RATIO_MIN_SAMPLES = 5  # 样本不足 median 不稳，跳过离群判（仍做漏译/断句/cps）

_CJK = re.compile(r"[一-鿿㐀-䶿豈-﫿]")
_TERMINATORS = re.compile(r"[。．\.!！?？…]+")  # 连续终止符算一句边界


def contains_cjk(text: str) -> bool:
    return bool(_CJK.search(text or ""))


def zh_char_len(text: str) -> int:
    """中文「字数」：去空白/换行后的可见字符数（标点也算占位，影响阅读节奏）。"""
    return len(re.sub(r"\s+", "", text or ""))


def en_char_len(text: str) -> int:
    """英文字符数：折叠多空格为单空格后计长（贴近实际阅读量）。"""
    return len(re.sub(r"\s+", " ", (text or "").strip()))


def count_sentences(text: str) -> int:
    """句子数 = 终止符簇数；末尾无终止符的残句也记 1。纯文本启发式，足够抓断句粒度错位。"""
    body = (text or "").replace("\n", " ").strip()
    if not body:
        return 0
    hits = _TERMINATORS.findall(body)
    n = len(hits)
    # 末尾还有非终止符残留（如 "你好。世界" → 2；"你好。世界。" → 2）
    tail = _TERMINATORS.sub("\x00", body).split("\x00")[-1].strip()
    if tail:
        n += 1
    return max(n, 1)


def reading_cps(chars: int, dur: Optional[float]) -> Optional[float]:
    if not dur or dur <= 0 or chars <= 0:
        return None
    return chars / dur


def ratio_band(ratios: Sequence[float], k: float = RATIO_BAND_K) -> Optional[Tuple[float, float, float]]:
    """中英长度比的自标定带：返回 (lo, median, hi)；样本不足返回 None。"""
    vals = sorted(r for r in ratios if r and r > 0)
    if len(vals) < RATIO_MIN_SAMPLES:
        return None
    mid = vals[len(vals) // 2] if len(vals) % 2 else (vals[len(vals) // 2 - 1] + vals[len(vals) // 2]) / 2
    if mid <= 0:
        return None
    return (mid / k, mid, mid * k)


def pair_verdict(zh_text: str, en_text: str, dur: Optional[float],
                 band: Optional[Tuple[float, float, float]]) -> List[Dict]:
    """单条 cue 的中↔英对齐判级 → 0..n 条 finding（每条 {verdict, message, dim}）。纯函数。"""
    out: List[Dict] = []
    zt, et = (zh_text or "").strip(), (en_text or "").strip()
    zlen, elen = zh_char_len(zt), en_char_len(et)

    # 漏译 / 空译（block）——条数对齐但某侧空，或英文整条仍是中文
    if zt and not et:
        out.append({"verdict": "block", "dim": "漏译", "message": "缺英文翻译（中文非空、英文为空）"})
        return out
    if et and not zt:
        out.append({"verdict": "block", "dim": "漏译", "message": "缺中文字幕（英文非空、中文为空）"})
        return out
    if et and contains_cjk(et):
        out.append({"verdict": "block", "dim": "漏译",
                    "message": f"英文字幕仍含中文未翻译：{et[:24]}"})

    # 断句粒度不一致（warn）——短语边界错位：一侧并句/拆句
    zs, es = count_sentences(zt), count_sentences(et)
    if zs and es and zs != es and max(zs, es) >= 2:
        out.append({"verdict": "warn", "dim": "断句",
                    "message": f"中英断句粒度不一致（中 {zs} 句/英 {es} 句）——短语边界错位，"
                               f"删/并镜未同步两侧会逐条偏"})

    # 长度比离群（warn）——疑似漏译/过译/截断
    if band and zlen > 0 and elen > 0:
        lo, mid, hi = band
        r = elen / zlen
        if r < lo or r > hi:
            out.append({"verdict": "warn", "dim": "长度比",
                        "message": f"中英长度比 {r:.2f} 偏离本集中位 {mid:.2f}（带 {lo:.2f}~{hi:.2f}）"
                                   f"——疑似漏译/过译/截断"})

    # 阅读速度过快（warn）——看不完直接掉留存
    zcps = reading_cps(zlen, dur)
    if zcps and zcps > ZH_CPS_MAX:
        out.append({"verdict": "warn", "dim": "阅读速度",
                    "message": f"中文 {zcps:.1f} 字/秒 >{ZH_CPS_MAX:.0f}（cue {dur:.2f}s 太短）——读不完"})
    ecps = reading_cps(elen, dur)
    if ecps and ecps > EN_CPS_MAX:
        out.append({"verdict": "warn", "dim": "阅读速度",
                    "message": f"英文 {ecps:.1f} 字符/秒 >{EN_CPS_MAX:.0f}——读不完"})
    return out


# ---- SRT 解析（与 mechanical_check 同格式；inline 保持本检测器零依赖、可单测）----

def _tc_to_sec(tc: str) -> float:
    h, m, rest = tc.strip().split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(path: str) -> Optional[List[Dict]]:
    if not os.path.exists(path):
        return None
    raw = open(path, encoding="utf-8").read().strip()
    cues: List[Dict] = []
    for block in re.split(r"\n\s*\n", raw):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        ti = next((i for i, ln in enumerate(lines) if "-->" in ln), None)
        if ti is None or ti + 1 >= len(lines):
            continue
        try:
            a, z = lines[ti].split("-->")
            cues.append({"start": _tc_to_sec(a), "end": _tc_to_sec(z),
                         "text": "\n".join(lines[ti + 1:])})
        except ValueError:
            continue
    return cues


def ocr_available() -> bool:
    """成片烧录后 OCR 回测的可选依赖探测（缺则人判兜，绝不臆造）。"""
    for mod in ("pytesseract", "easyocr"):
        try:
            __import__(mod)
            return True
        except Exception:
            continue
    return False


def analyze(root: str, ep: str) -> Dict:
    zh_path = os.path.join(root, "脚本", ep, "字幕_中文.srt")
    en_path = os.path.join(root, "脚本", ep, "字幕_英文.srt")
    zh = parse_srt(zh_path)
    en = parse_srt(en_path)
    notes: List[str] = []
    if zh is None or en is None:
        miss = [p for p, c in ((zh_path, zh), (en_path, en)) if c is None]
        return {"available": False, "rows": [], "notes":
                [f"字幕对齐跳过：缺 {'、'.join(os.path.relpath(m, root) for m in miss)}（未到分镜设计/仅单语则正常）"]}
    if len(zh) != len(en):
        notes.append(f"中英 cue 数不一致（中{len(zh)}/英{len(en)}）——mechanical_check 已 block；"
                     f"此处按前 {min(len(zh), len(en))} 条尽力对齐")

    pairs = list(zip(zh, en))
    ratios = [en_char_len(e["text"]) / zh_char_len(z["text"])
              for z, e in pairs if zh_char_len(z["text"]) > 0 and en_char_len(e["text"]) > 0]
    band = ratio_band(ratios)
    if band is None and pairs:
        notes.append(f"长度比离群判跳过：有效样本 {len(ratios)} < {RATIO_MIN_SAMPLES}（median 不稳）")

    rows: List[Dict] = []
    for i, (z, e) in enumerate(pairs, 1):
        dur = max(0.0, float(e.get("end", 0)) - float(e.get("start", 0)))
        for f in pair_verdict(z["text"], e["text"], dur or None, band):
            rows.append({"verdict": f["verdict"], "heading": f"cue#{i}",
                         "loc": f"字幕 cue#{i}", "message": f"[{f['dim']}] {f['message']}",
                         "zh": z["text"][:30], "en": e["text"][:40]})
    if not ocr_available():
        notes.append("成片烧录后 OCR 回测跳过（未装 pytesseract/easyocr）——编码压糊/换行错位暂由人判兜")
    return {"available": True, "rows": rows, "notes": notes,
            "median_ratio": band[1] if band else None}


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="双语字幕短语边界/阅读速度/译文完整性机检")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 1 if any(r["verdict"] == "block" for r in res["rows"]) else 0
    print(f"=== 字幕对齐(L1)：{ns.root} {ns.episode} ===")
    if not res["available"]:
        for n in res["notes"]:
            print(f"  · {n}")
        return 0
    nb = sum(1 for r in res["rows"] if r["verdict"] == "block")
    nw = sum(1 for r in res["rows"] if r["verdict"] == "warn")
    print(f"🔴 {nb} · 🟡 {nw}（中位长度比 {res.get('median_ratio')}）\n")
    for r in res["rows"]:
        sev = "🔴" if r["verdict"] == "block" else "🟡"
        print(f"{sev} {r['loc']}: {r['message']}")
        print(f"     中『{r['zh']}』 / 英『{r['en']}』")
    for n in res["notes"]:
        print(f"  · {n}")
    return 1 if nb else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
