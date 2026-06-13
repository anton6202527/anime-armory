#!/usr/bin/env python3
"""语义谱系 Diff（P0）——检查 n2d 下游是否继承上游契约。

现有一致性机检主要看"生成结果是否漂"；本脚本前移一层，检查：

  raw/voiceover → storyboard.json → 出图 prompt → 出视频 prompt

下游 prompt 如果没有继承上游的角色、场景、状态、风格、模板、continuity 关键项，
即使还没出图/出视频，也已经埋下漂移风险。算法只做确定性文本谱系 diff：
把上游结构化字段抽成关键词集合，再算下游文本覆盖率；缺素材时显式跳过。

用法：
  python3 semantic_continuity.py <作品根> 第N集 [--json] [--write]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from n2d_contract import production_dir  # noqa: E402  生产数据目录单一真值源

KIND = "n2d_semantic_continuity_report"
VERSION = 1

STOP_TERMS = {
    "本集", "本镜", "镜头", "画面", "角色", "场景", "人物", "状态", "保持", "继承",
    "默认", "开始", "结束", "进入", "退出", "不要", "禁止", "普通", "高细节",
    "竖版", "画幅", "一致", "一致性", "契约", "字段", "下游", "上游",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def read_text(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    try:
        return open(path, encoding="utf-8").read()
    except OSError:
        return ""


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.isfile(path):
        return None
    try:
        data = json.load(open(path, encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def storyboard_path(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", ep, "storyboard.json")


def image_overview_path(root: str, ep: str) -> str:
    return os.path.join(root, "出图", ep, "prompt", "00_总览.md")


def image_shots_path(root: str, ep: str) -> str:
    return os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")


def video_overview_path(root: str, ep: str) -> str:
    return os.path.join(root, "出视频", ep, "prompt", "00_总览.md")


def video_clips_path(root: str, ep: str) -> str:
    return os.path.join(root, "出视频", ep, "prompt", "01_clips.md")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", (text or "")).lower()


def flatten_strings(value: Any) -> List[str]:
    out: List[str] = []
    if value is None:
        return out
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, (int, float, bool)):
        out.append(str(value))
    elif isinstance(value, dict):
        for k, v in value.items():
            out.extend(flatten_strings(k))
            out.extend(flatten_strings(v))
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            out.extend(flatten_strings(item))
    return out


def salient_terms(value: Any, *, limit: int = 60) -> List[str]:
    """从结构化字段里抽可比对关键词。

    不做语义分词，优先保留人名/地名/状态短语/ASCII 控制词，避免引入重依赖。
    """
    terms: List[str] = []
    for raw in flatten_strings(value):
        raw = raw.strip()
        if not raw:
            continue
        # 保留 backend / enum / snake_case 这类机器契约词。
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_:-]{2,}", raw):
            terms.append(token.lower())
        # 中文短语按常见分隔符切；长句再从关键状态词附近切短。
        chunks = re.split(r"[，。；;、,\s/｜|→:：()（）\[\]【】{}<>《》\"'“”‘’]+", raw)
        for ch in chunks:
            ch = ch.strip(" -·\t\r\n")
            if not ch or ch in STOP_TERMS:
                continue
            if re.fullmatch(r"\d+(?:\.\d+)?", ch):
                continue
            if len(ch) > 18:
                # 长句过于脆弱，取里面更稳定的中文名词/状态片段。
                sub = re.findall(r"[\u4e00-\u9fff]{2,8}", ch)
                terms.extend(t for t in sub if t not in STOP_TERMS)
            elif len(ch) >= 2:
                terms.append(ch)
    seen = set()
    uniq: List[str] = []
    for t in terms:
        key = normalize_text(t)
        if len(key) < 2 or key in seen or t in STOP_TERMS:
            continue
        seen.add(key)
        uniq.append(t)
        if len(uniq) >= limit:
            break
    return uniq


SEMANTIC_ALIASES: Tuple[Tuple[str, str], ...] = (
    ("左颊", "左脸"),
    ("右颊", "右脸"),
    ("脸颊", "面颊"),
    ("新伤", "伤痕"),
    ("伤口", "伤痕"),
    ("金瞳", "金色眼睛"),
    ("红瞳", "红色眼睛"),
    ("黑袍", "黑衣"),
    ("白绫", "白布"),
)


def term_variants(term: str) -> List[str]:
    variants = [term]
    for a, b in SEMANTIC_ALIASES:
        next_items: List[str] = []
        for item in variants:
            if a in item:
                next_items.append(item.replace(a, b))
            if b in item:
                next_items.append(item.replace(b, a))
        variants.extend(next_items)
    out: List[str] = []
    seen = set()
    for item in variants:
        key = normalize_text(item)
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    return out


def cjk_shingles(text: str, n: int = 2) -> List[str]:
    chars = "".join(re.findall(r"[\u4e00-\u9fff]", text or ""))
    if len(chars) < n:
        return [chars] if chars else []
    return [chars[i:i + n] for i in range(len(chars) - n + 1)]


def approx_contains(term: str, target_text: str) -> bool:
    """轻量语义匹配：精确/同义别名/中文 bigram 重叠。

    这不是大模型 embedding，但比纯子串更稳：能覆盖“左颊/左脸”这类生产里常见改写，
    同时保持无依赖、可复现，适合放在 gate 前置。
    """
    nt = normalize_text(target_text)
    for variant in term_variants(term):
        key = normalize_text(variant)
        if key and key in nt:
            return True
        shingles = set(cjk_shingles(key))
        if len(shingles) >= 3:
            target_shingles = set(cjk_shingles(nt))
            overlap = len(shingles & target_shingles) / max(1, len(shingles))
            if overlap >= 0.67:
                return True
    return False


def coverage(required: Sequence[str], text: str) -> Tuple[float, List[str]]:
    req = [t for t in required if normalize_text(t)]
    if not req:
        return 1.0, []
    missing = [t for t in req if not approx_contains(t, text)]
    return (len(req) - len(missing)) / len(req), missing


def split_md_blocks(text: str) -> List[Dict[str, str]]:
    blocks: List[Dict[str, str]] = []
    cur_head: Optional[str] = None
    cur_lines: List[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if cur_head is not None:
                blocks.append({"heading": cur_head, "body": "\n".join(cur_lines)})
            cur_head = line[3:].strip()
            cur_lines = [line]
        elif cur_head is not None:
            cur_lines.append(line)
    if cur_head is not None:
        blocks.append({"heading": cur_head, "body": "\n".join(cur_lines)})
    return blocks


def clip_number(value: Any, fallback: int) -> int:
    text = str(value or "")
    m = re.search(r"CLIP\s*0*(\d+)", text, re.I) or re.search(r"Clip\s*0*(\d+)", text, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"片段\s*0*(\d+)", text)
    return int(m.group(1)) if m else fallback


def block_for_clip(blocks: Sequence[Dict[str, str]], idx: int, clip_id: str = "") -> str:
    needles = {f"clip{idx}", f"clip {idx}", f"clip_{idx:02d}", f"clip{idx:02d}", f"片段{idx}"}
    if clip_id:
        needles.add(normalize_text(clip_id))
    for blk in blocks:
        head = normalize_text(blk.get("heading", ""))
        if any(n in head for n in needles):
            return blk.get("body", "")
    return blocks[idx - 1]["body"] if 0 < idx <= len(blocks) else ""


def voiceover_signals(text: str) -> Dict[str, List[str]]:
    roles: List[str] = []
    hooks: List[str] = []
    for line in text.splitlines():
        m = re.match(r"\s*\[镜头[^·\]]+·([^·\]]+)", line)
        if m and m.group(1) not in roles:
            roles.append(m.group(1))
        for tag in ("钩子", "爽点", "集尾"):
            if tag in line and tag not in hooks:
                hooks.append(tag)
    return {"roles": roles, "hooks": hooks}


def finding(source: str, target: str, message: str, verdict: str,
            required: Sequence[str] = (), missing: Sequence[str] = (), cov: Optional[float] = None) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "source": source,
        "target": target,
        "message": message,
        "verdict": verdict,
    }
    if required:
        row["required_terms"] = list(required)
    if missing:
        row["missing_terms"] = list(missing)[:20]
    if cov is not None:
        row["coverage"] = round(cov, 3)
    return row


def check_term_flow(source: str, target: str, terms: Sequence[str], target_text: str,
                    min_coverage: float, verdict: str, message: str) -> Optional[Dict[str, Any]]:
    if not terms:
        return None
    cov, missing = coverage(terms, target_text)
    if cov < min_coverage:
        return finding(source, target, message, verdict, terms, missing, cov)
    return None


def analyze(root: str, ep: str) -> Dict[str, Any]:
    root = root.rstrip("/")
    notes: List[str] = []
    findings: List[Dict[str, Any]] = []
    sb = load_json(storyboard_path(root, ep))
    if not sb:
        return {
            "kind": KIND,
            "version": VERSION,
            "root": root,
            "episode": ep,
            "available": False,
            "findings": [],
            "verdicts": [],
            "notes": [f"缺 {storyboard_path(root, ep)}，语义谱系 Diff 跳过。"],
        }

    voice = read_text(os.path.join(root, "脚本", ep, "voiceover.txt"))
    image_overview = read_text(image_overview_path(root, ep))
    image_shots = read_text(image_shots_path(root, ep))
    video_overview = read_text(video_overview_path(root, ep))
    video_clips = read_text(video_clips_path(root, ep))
    video_blocks = split_md_blocks(video_clips)
    storyboard_text = json.dumps(sb, ensure_ascii=False)

    if voice:
        sig = voiceover_signals(voice)
        for role in sig["roles"]:
            if role not in storyboard_text:
                findings.append(finding("voiceover.txt", "storyboard.json", f"配音角色 `{role}` 未进入 storyboard。", "warn", [role], [role], 0.0))
        for hook in sig["hooks"]:
            if hook not in storyboard_text:
                findings.append(finding("voiceover.txt", "storyboard.json", f"`{hook}` 留存标记未进入 storyboard 节奏/导演意图。", "warn", [hook], [hook], 0.0))

    if image_overview:
        vc_terms = salient_terms(sb.get("visual_contract", {}))
        row = check_term_flow("storyboard.visual_contract", "出图/00_总览.md", vc_terms, image_overview, 0.35, "warn", "出图总览未充分继承视觉契约。")
        if row:
            findings.append(row)
        sc_terms = salient_terms(sb.get("style_contract") or sb.get("cinematic_contract") or {})
        row = check_term_flow("storyboard.style_contract", "出图/00_总览.md", sc_terms, image_overview, 0.35, "warn", "出图总览未充分继承基础视觉风格契约。")
        if row:
            findings.append(row)
    else:
        notes.append("缺出图 00_总览.md，暂不验证 storyboard→image 契约继承。")

    if video_overview:
        overview_terms = salient_terms({
            "visual_contract": sb.get("visual_contract", {}),
            "style_contract": sb.get("style_contract") or sb.get("cinematic_contract") or {},
        })
        row = check_term_flow("storyboard contracts", "出视频/00_总览.md", overview_terms, video_overview, 0.25, "warn", "出视频总览未充分继承 storyboard 契约。")
        if row:
            findings.append(row)
    else:
        notes.append("缺出视频 00_总览.md，暂不验证 storyboard→video 总览继承。")

    clips = [c for c in sb.get("clips", []) if isinstance(c, dict)]
    if clips and video_blocks:
        for i, clip in enumerate(clips, start=1):
            idx = clip_number(clip.get("id") or clip.get("label"), i)
            target_text = block_for_clip(video_blocks, idx, str(clip.get("id") or ""))
            if not target_text:
                findings.append(finding("storyboard.clips[]", "出视频/01_clips.md", f"找不到 Clip {idx} 的视频 prompt 块。", "warn"))
                continue
            continuity = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
            c_terms = salient_terms({
                "scene": clip.get("scene"),
                "rhythm": clip.get("rhythm"),
                "continuity": continuity,
            }, limit=36)
            row = check_term_flow(f"storyboard.clip[{idx}].continuity", f"video Clip {idx}", c_terms, target_text, 0.30, "warn", "视频 Clip 未充分继承 continuity/场景/节奏。")
            if row:
                findings.append(row)
            tmpl = clip.get("template_contract") if isinstance(clip.get("template_contract"), dict) else {}
            if tmpl:
                t_terms = salient_terms(tmpl, limit=36)
                row = check_term_flow(f"storyboard.clip[{idx}].template_contract", f"video Clip {idx}", t_terms, target_text, 0.35, "warn", "复杂镜视频 prompt 未充分继承专项模板契约。")
                if row:
                    findings.append(row)
    elif clips:
        notes.append("缺出视频 01_clips.md，暂不验证逐 Clip 视频继承。")

    if image_shots:
        all_clip_terms = salient_terms([
            {"scene": c.get("scene"), "template": c.get("template"), "template_contract": c.get("template_contract")}
            for c in clips
        ], limit=80)
        row = check_term_flow("storyboard.clips[]", "出图/01_分镜出图.md", all_clip_terms, image_shots, 0.25, "warn", "出图分镜 prompt 未充分继承 clip 场景/模板语义。")
        if row:
            findings.append(row)
    elif clips:
        notes.append("缺出图 01_分镜出图.md，暂不验证 storyboard→image 分镜继承。")

    verdicts = [f["verdict"] for f in findings]
    return {
        "kind": KIND,
        "version": VERSION,
        "generated_at": now_iso(),
        "root": root,
        "episode": ep,
        "available": True,
        "findings": findings,
        "verdicts": verdicts,
        "notes": notes,
        "summary": {
            "block": sum(1 for v in verdicts if v == "block"),
            "warn": sum(1 for v in verdicts if v == "warn"),
            "ok": 0 if findings else 1,
        },
    }


def write_report(root: str, ep: str, data: Dict[str, Any]) -> str:
    safe_ep = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", ep)
    out = os.path.join(production_dir(root), f"semantic_continuity_{safe_ep}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    return out


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root, ns.episode)
    if ns.write:
        path = write_report(ns.root.rstrip("/"), ns.episode, res)
        res["written"] = path
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"=== 语义谱系 Diff（P0）：{ns.root} {ns.episode} ===")
        for note in res.get("notes", []):
            print("ℹ️ " + note)
        icon = {"block": "⛔", "warn": "⚠️", "ok": "✅"}
        for f in res.get("findings", []):
            miss = "、".join(f.get("missing_terms", [])[:6])
            suffix = f"；缺：{miss}" if miss else ""
            print(f"{icon.get(f['verdict'], '·')} {f['source']} → {f['target']}：{f['message']}{suffix}")
        if not res.get("findings"):
            print("✅ 下游语义继承未发现明显缺口。")
    return 1 if any(v == "block" for v in res.get("verdicts", [])) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
