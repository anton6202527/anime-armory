#!/usr/bin/env python3
"""④ VLM 语义判定（描述 ↔ 渲染图）——在指纹/调色板/embedding cosine 之上加一路「读图判设定」。

**为什么**：image_qc 现有一致性检查是**几何/指纹**（insightface 脸 G1、Pillow 发型 H1、调色板服装 N1/
场景 O2/道具 P2、dHash），semantic_drift 再加一路 **embedding cosine**（DINO/CLIP/DreamSim）。这些都答
「像不像参考图」，**答不了「符不符合设定描述」**：月白窄袖被画成月白交领（剪裁变）、左腕核心识别疤丢了、
素布发带变金步摇——embedding/调色板都可能过，但**语义上崩了设定**。2026 同主体评测基准（SAM3 抽角色轨迹 +
MLLM verifier 核对角色描述）正是用 **VLM-as-judge** 补这一层。本模块把「角色/资产的 canonical 设定描述
（character_dna / scene_dna / anchor_phrase）↔ 本镜渲染图」交给 VLM 判：是否吻合、缺哪几项、置信度。

判定 → 严重度（与 image_qc 升 hard 对齐）：
  - **关键注册资产/角色** × VLM 判不符 × 置信度≥block_floor → `vlm_semantic_mismatch`（**block**·既成语义崩设定）；
  - 置信度不足 / 非关键 → `vlm_semantic_review`（warn·人判）；
  - 吻合 / 判定失败(None) → 不加噪。

依赖是 **opt-in**：VLM 后端是选择点，经 `N2D_VLM_CMD` 注入一条命令模板（占位 {image} {prompt}，stdout 回
JSON `{"match":bool,"confidence":0-1,"mismatches":[...],"reason":"..."}`），缺则 `available=False`、整段
跳过，**绝不阻断默认无依赖产线**（与 semantic_drift 同纪律）。后端本身不 hardcode 厂商：本机可指向
Claude/OpenAI 视觉 API 包装脚本、本地 Qwen-VL CLI 或任何能读图判文的命令。纯函数（prompt 构造/verdict 解析/
严重度判定）有 pytest 覆盖；judge 调用是 best-effort I/O。

block_floor 经 `N2D_VLM_BLOCK_FLOOR` 覆盖（默认 0.6，按真实渲染集×所选 VLM 标定，与 semantic_drift floor 同理）。

用法：python3 vlm_verify.py <作品根> <第N集> [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

try:
    VLM_BLOCK_FLOOR = float(os.environ.get("N2D_VLM_BLOCK_FLOOR", "0.6"))
except (TypeError, ValueError):
    VLM_BLOCK_FLOOR = 0.6

# judge: (abspath, canonical_text, kind) → verdict dict 或 None（判定失败/后端不可用单图）
Judge = Callable[[str, str, str], Optional[Dict[str, Any]]]

_DNA_ORDER = ("face", "hair", "outfit", "accessories", "texture")


# ── 纯函数（无依赖·可测） ──────────────────────────────────────────────────────

def build_judge_prompt(name: str, kind: str, canonical: str) -> str:
    """构造给 VLM 的判定 prompt（纯函数·可测）。要求 VLM 只回 JSON，逐项核对设定，别脑补。"""
    role = "角色" if kind == "character" else "场景/道具/服装/特效资产"
    return (
        f"你是漫剧一致性审片员。下面是{role}「{name}」的设定档（canonical 设定，唯一真值）：\n"
        f"{canonical.strip()}\n\n"
        "请只依据图像判断这张渲染图是否**符合上述设定**，逐项核对（角色：脸型/五官/发型/服装剪裁与颜色/"
        "标志配饰/识别特征；资产：地标/空间布局/材质/颜色）。不要脑补设定里没写的东西，只判已写项是否被违反。\n"
        "只输出一个 JSON 对象，不要任何多余文字：\n"
        '{"match": true/false, "confidence": 0.0-1.0, "mismatches": ["缺左腕疤", "窄袖→交领"], "reason": "一句话"}\n'
        "match=true 表示设定关键项都对得上；mismatches 列出被违反的具体项（match=true 时为空数组）。"
    )


def parse_verdict(raw: Any) -> Optional[Dict[str, Any]]:
    """把 VLM 原始返回（str/dict）解析成规范 verdict；解析不出 → None（不假报）。纯函数·可测。

    返回 {match:bool, confidence:float∈[0,1], mismatches:[str], reason:str}。"""
    data: Any = raw
    if isinstance(raw, str):
        s = raw.strip()
        # 容忍 ```json fence``` 和前后噪声：截取第一个 { 到最后一个 }
        if "{" in s and "}" in s:
            s = s[s.index("{"): s.rindex("}") + 1]
        try:
            data = json.loads(s)
        except Exception:
            return None
    if not isinstance(data, Mapping) or "match" not in data:
        return None
    try:
        conf = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(1.0, conf))
    mis = data.get("mismatches") or []
    if not isinstance(mis, (list, tuple)):
        mis = [str(mis)]
    return {
        "match": bool(data.get("match")),
        "confidence": conf,
        "mismatches": [str(m) for m in mis][:10],
        "reason": str(data.get("reason") or "").strip(),
    }


def verdict_finding(name: str, kind: str, png: str, verdict: Optional[Mapping[str, Any]],
                    is_key: bool, block_floor: float = VLM_BLOCK_FLOOR) -> Optional[Dict[str, str]]:
    """verdict × 是否关键资产 → finding（纯函数·可测）。

    - 关键 × match=False × confidence≥floor → block `vlm_semantic_mismatch`；
    - match=False 但（非关键 或 置信度不足） → warn `vlm_semantic_review`；
    - match=True / verdict=None → None。"""
    if not verdict or verdict.get("match"):
        return None
    conf = float(verdict.get("confidence") or 0.0)
    mis = "、".join(verdict.get("mismatches") or []) or (verdict.get("reason") or "未列明")
    kindlabel = "角色" if kind == "character" else "资产"
    if is_key and conf >= block_floor:
        return {"level": "block", "code": "vlm_semantic_mismatch",
                "msg": (f"{kindlabel}「{name}」VLM 判定语义崩设定（conf={conf:.2f}≥{block_floor}）：{mis}。"
                        f"本镜 {png}——指纹/embedding 可能过但违反 canonical 设定，关键资产硬挡，重出。")}
    return {"level": "warn", "code": "vlm_semantic_review",
            "msg": (f"{kindlabel}「{name}」VLM 疑似不符（conf={conf:.2f}）：{mis}。本镜 {png}——人判是否真漂。")}


def _join_dna(dna: Mapping[str, Any]) -> str:
    parts: List[str] = []
    for k in _DNA_ORDER:
        v = str(dna.get(k) or "").strip()
        if v:
            parts.append(f"{k}: {v}")
    for k, v in dna.items():
        if k in _DNA_ORDER:
            continue
        sv = str(v if not isinstance(v, (list, tuple)) else "、".join(str(x) for x in v)).strip()
        if sv:
            parts.append(f"{k}: {sv}")
    return "；".join(parts)


def canonical_from_character(ch: Mapping[str, Any], form: Mapping[str, Any]) -> str:
    """角色 canonical 设定文本（character_dna + anchor_phrase）。纯函数·可测。"""
    dna = form.get("character_dna") if isinstance(form.get("character_dna"), Mapping) else {}
    text = _join_dna(dna)
    anchor = str(form.get("anchor_phrase") or "").strip()
    if anchor:
        text = (text + "；" if text else "") + f"anchor: {anchor}"
    return text


def canonical_from_asset(asset: Mapping[str, Any]) -> str:
    """资产 canonical 设定文本（name + *_dna）。纯函数·可测。"""
    name = str(asset.get("name") or "").strip()
    dna = {}
    for k, v in asset.items():
        if k.endswith("_dna") and isinstance(v, Mapping):
            dna = v
            break
    body = _join_dna(dna) if dna else ""
    return f"{name}；{body}" if body else name


# ── 数据装载（best-effort I/O） ────────────────────────────────────────────────

def load_canonical_map(root: Path) -> Dict[str, Dict[str, str]]:
    """{别名/名/id/asset_key → {kind, canonical}}——注册角色(identity_registry)+注册资产(asset_registry)。

    注册的角色/资产即为「关键资产」(is_key=True)，VLM 判不符可升 block。"""
    out: Dict[str, Dict[str, str]] = {}

    def _add(key: str, kind: str, canonical: str) -> None:
        k = str(key or "").strip()
        if len(k) >= 2 and canonical.strip():
            out.setdefault(k, {"kind": kind, "canonical": canonical})

    try:
        idr = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))
        for ch in idr.get("characters") or []:
            if not isinstance(ch, Mapping):
                continue
            for f in ch.get("forms") or []:
                if not isinstance(f, Mapping):
                    continue
                canon = canonical_from_character(ch, f)
                _add(ch.get("name") or "", "character", canon)
                _add(f.get("asset_key") or "", "character", canon)
                _add(ch.get("id") or "", "character", canon)
    except Exception:
        pass

    try:
        asr = json.loads((root / "出图" / "共享" / "asset_registry.json").read_text(encoding="utf-8"))
        for a in asr.get("assets") or []:
            if not isinstance(a, Mapping):
                continue
            canon = canonical_from_asset(a)
            _add(a.get("name") or "", "asset", canon)
            _add(a.get("id") or "", "asset", canon)
    except Exception:
        pass
    return out


def _pairs_from_payload(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """从 image_qc payload 抽 (name_hint, png) 全镜对——face/hair/outfit/scene/multimodal 各层均纳入。
    全镜（不止 block/warn），因为 VLM 的价值正是抓指纹没报的语义崩。纯函数·可测。"""
    checks = payload.get("checks", {}) or {}
    out: List[Dict[str, Any]] = []
    layers = (
        ("face", ("name", "char", "character", "group")),
        ("hair", ("name", "char", "character", "group")),
        ("outfit", ("name", "char", "character", "group", "asset")),
        ("scene", ("scene", "group", "asset")),
        ("multimodal", ("asset", "group", "scene")),
    )
    for layer, name_keys in layers:
        for s in (checks.get(layer) or {}).get("shots", []):
            if not isinstance(s, Mapping) or not s.get("png"):
                continue
            hint = next((str(s.get(k) or "").strip() for k in name_keys if str(s.get(k) or "").strip()), "")
            if hint:
                out.append({"name": hint, "png": s.get("png")})
    # 去重 (name,png)，避免多层重复判同一张
    seen = set()
    uniq: List[Dict[str, Any]] = []
    for p in out:
        key = (p["name"], p["png"])
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    return uniq


def resolve_canonical(name_hint: str, canon_map: Mapping[str, Dict[str, str]]) -> Optional[Dict[str, str]]:
    """name_hint → canonical（精确优先，再子串双向匹配）。纯函数·可测。"""
    h = str(name_hint or "").strip()
    if not h:
        return None
    if h in canon_map:
        return canon_map[h]
    for key, val in canon_map.items():
        if key in h or h in key:
            return val
    return None


def evaluate_pairs(pairs: Sequence[Mapping[str, Any]], canon_map: Mapping[str, Dict[str, str]],
                   judge: Judge, shot_abspath: Callable[[str], str],
                   block_floor: float = VLM_BLOCK_FLOOR) -> Dict[str, Any]:
    """逐对 (canonical ↔ 本镜) 调 VLM judge → findings（注入 stub 可测）。"""
    findings: List[Dict[str, str]] = []
    judged = 0
    cache: Dict[str, Optional[Dict[str, Any]]] = {}
    for p in pairs:
        entry = resolve_canonical(str(p.get("name") or ""), canon_map)
        png_rel = p.get("png")
        if not entry or not png_rel:
            continue
        abspath = shot_abspath(str(png_rel))
        ckey = f"{abspath}::{entry['canonical']}"
        if ckey not in cache:
            try:
                cache[ckey] = parse_verdict(judge(abspath, entry["canonical"], entry["kind"]))
            except Exception:
                cache[ckey] = None
        verdict = cache[ckey]
        if verdict is None:
            continue
        judged += 1
        fnd = verdict_finding(str(p.get("name")), entry["kind"], str(png_rel), verdict,
                              is_key=True, block_floor=block_floor)
        if fnd:
            findings.append(fnd)
    block = sum(1 for f in findings if f["level"] == "block")
    return {"available": True, "judged": judged, "block_floor": block_floor,
            "block": block, "findings": findings}


# ── VLM 后端（best-effort·opt-in·不 hardcode 厂商） ───────────────────────────

def load_judge() -> Optional[Judge]:
    """从 `N2D_VLM_CMD` 命令模板构造 judge；未配置 → None（整段跳过，不阻断默认产线）。

    命令模板用 {image} {prompt} 占位（prompt 经 shell-quote 注入），stdout 应回判定 JSON。
    例：export N2D_VLM_CMD='python3 ~/bin/vlm_judge.py --image {image} --prompt {prompt}'
    厂商无关：包装 Claude/OpenAI 视觉 API、本地 Qwen-VL/InternVL CLI 均可。"""
    tmpl = os.environ.get("N2D_VLM_CMD", "").strip()
    if not tmpl or "{image}" not in tmpl:
        return None

    def _judge(image: str, canonical: str, kind: str) -> Optional[Dict[str, Any]]:
        prompt = build_judge_prompt("", kind, canonical) if "{prompt}" in tmpl else ""
        cmd = tmpl.replace("{image}", shlex.quote(image))
        if "{prompt}" in cmd:
            cmd = cmd.replace("{prompt}", shlex.quote(prompt))
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
        except Exception:
            return None
        if res.returncode != 0:
            return None
        return parse_verdict(res.stdout)

    return _judge


def analyze(root: Path, ep: str, payload: Mapping[str, Any],
            judge: Optional[Judge] = None, block_floor: float = VLM_BLOCK_FLOOR) -> Dict[str, Any]:
    """image_qc 集成入口：抽 (canonical↔镜) 对跑 VLM 判定。judge=None → 尝试自动加载。
    无 VLM 后端 → available=False（advisory 跳过，绝不阻断默认产线）。"""
    j = judge if judge is not None else load_judge()
    if j is None:
        return {"available": False, "judged": 0,
                "notes": ["VLM 后端不可用——VLM 语义判定跳过（配置 N2D_VLM_CMD 后复检；厂商无关）。"],
                "findings": []}
    canon_map = load_canonical_map(root)
    if not canon_map:
        return {"available": True, "judged": 0,
                "notes": ["identity_registry/asset_registry 无可判定的 canonical 设定。"], "findings": []}
    pairs = _pairs_from_payload(payload)
    shot_abspath = lambda rel: str(Path(root) / "出图" / ep / rel)  # noqa: E731
    return evaluate_pairs(pairs, canon_map, j, shot_abspath, block_floor)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).expanduser().resolve()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import image_qc  # type: ignore
    payload = image_qc.run_qc(root, ns.episode)
    res = analyze(root, ns.episode, payload)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if not res.get("available"):
        print("⏭ VLM 语义判定跳过：" + "；".join(res.get("notes", [])))
        return 0
    print(f"VLM 语义判定（{ns.episode}）：判 {res['judged']} 镜 · floor {res['block_floor']} · "
          f"{res['block']} block / {len(res['findings'])} 条")
    for f in res["findings"]:
        print(f"  [{f['level']}] {f['msg']}")
    return 2 if res.get("block") else 0


if __name__ == "__main__":
    raise SystemExit(main())
