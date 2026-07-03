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

# 自一致投票（self-consistency）：默认 1 次（零行为变化）；≥3 次时取多数票定 match、留痕分歧度。
# 2026 VLM-as-judge 最佳实践——单次判定不可靠，多次采样聚合提稳。视频侧 VLM1
# (n2d-review/video_vlm_consistency._vote_disagreement) 早已消费 sidecar 投票元数据；
# 这里把同口径补到图侧 ④VLM 语义判定（独立线·不跨 skill import，复制同公式）。
try:
    VLM_VOTES = max(1, int(os.environ.get("N2D_VLM_VOTES", "1")))
except (TypeError, ValueError):
    VLM_VOTES = 1
try:
    VLM_VOTE_DISAGREE_FLOOR = float(os.environ.get("N2D_VLM_VOTE_DISAGREE", "0.34"))
except (TypeError, ValueError):
    VLM_VOTE_DISAGREE_FLOOR = 0.34

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


def vote_disagreement(verdicts: Sequence[Mapping[str, Any]]) -> float:
    """自一致投票分歧度 = 1 − 多数票占比（与视频侧 VLM1 `_vote_disagreement` 同口径）。
    有效票 <3 → 0.0（样本太小不算分歧）。纯函数·可测。"""
    matches = [bool(v.get("match")) for v in verdicts if isinstance(v, Mapping) and "match" in v]
    if len(matches) < 3:
        return 0.0
    majority = max(matches.count(True), matches.count(False))
    return 1.0 - majority / len(matches)


def aggregate_votes(verdicts: Sequence[Optional[Mapping[str, Any]]]) -> Optional[Dict[str, Any]]:
    """多次自一致采样的 verdict 列表 → 单条聚合 verdict（多数票定 match·分歧度留痕）。纯函数·可测。

    - 判定失败(None)的票剔除；全失败 → None；
    - 单票 → 原样返回（votes=1 时零行为变化，不带 vote_disagreement 键）；
    - 平票偏向 match=True（保守不误伤）；confidence 取与多数一致票的均值；
    - mismatches 取所有 match=False 票的并集（最全信息）；reason 取多数侧首条非空。"""
    valid = [v for v in verdicts if isinstance(v, Mapping) and "match" in v]
    if not valid:
        return None
    if len(valid) == 1:
        return dict(valid[0])
    matches = [bool(v.get("match")) for v in valid]
    majority_match = matches.count(True) >= matches.count(False)
    agree = [v for v in valid if bool(v.get("match")) == majority_match] or valid
    confs = [float(v.get("confidence") or 0.0) for v in agree]
    conf = max(0.0, min(1.0, sum(confs) / len(confs)))
    mismatches: List[str] = []
    for v in valid:
        if not bool(v.get("match")):
            for m in v.get("mismatches") or []:
                if str(m) not in mismatches:
                    mismatches.append(str(m))
    reason = next((str(v.get("reason")) for v in agree if str(v.get("reason") or "").strip()), "")
    return {
        "match": majority_match,
        "confidence": conf,
        "mismatches": mismatches[:10],
        "reason": reason,
        "vote_disagreement": round(vote_disagreement(valid), 3),
        "n_votes": len(valid),
    }


def judge_verdict(judge: Judge, abspath: str, canonical: str, kind: str,
                  votes: int = VLM_VOTES) -> Optional[Dict[str, Any]]:
    """调 VLM judge `votes` 次并聚合（votes=1 → 等价单次 parse_verdict·零行为变化）。best-effort I/O。"""
    n = max(1, int(votes))
    parsed: List[Optional[Dict[str, Any]]] = []
    for _ in range(n):
        try:
            parsed.append(parse_verdict(judge(abspath, canonical, kind)))
        except Exception:
            parsed.append(None)
    return aggregate_votes(parsed)


def verdict_finding(name: str, kind: str, png: str, verdict: Optional[Mapping[str, Any]],
                    is_key: bool, block_floor: float = VLM_BLOCK_FLOOR,
                    vote_disagree_floor: float = VLM_VOTE_DISAGREE_FLOOR) -> Optional[Dict[str, str]]:
    """verdict × 是否关键资产 → finding（纯函数·可测）。

    - 关键 × match=False × confidence≥floor × 投票分歧<floor → block `vlm_semantic_mismatch`；
    - match=False 但（非关键 / 置信度不足 / **投票分歧高**） → warn `vlm_semantic_review`；
    - match=True / verdict=None → None。

    自一致投票分歧高（judge 自己都拿不准）时**绝不硬挡**，降级人判——与视频侧 VLM1 同纪律。"""
    if not verdict or verdict.get("match"):
        return None
    conf = float(verdict.get("confidence") or 0.0)
    disagree = float(verdict.get("vote_disagreement") or 0.0)
    mis = "、".join(verdict.get("mismatches") or []) or (verdict.get("reason") or "未列明")
    kindlabel = "角色" if kind == "character" else "资产"
    base = {"png": png, "name": name, "confidence": round(conf, 4)}
    if verdict.get("vote_disagreement") is not None:
        base["vote_disagreement"] = round(disagree, 4)
    if is_key and conf >= block_floor and disagree < vote_disagree_floor:
        return {**base, "level": "block", "code": "vlm_semantic_mismatch",
                "msg": (f"{kindlabel}「{name}」VLM 判定语义崩设定（conf={conf:.2f}≥{block_floor}）：{mis}。"
                        f"本镜 {png}——指纹/embedding 可能过但违反 canonical 设定，关键资产硬挡，重出。")}
    note = ""
    if is_key and conf >= block_floor and disagree >= vote_disagree_floor:
        note = (f"（VLM 自一致投票分歧 {disagree:.2f}≥{vote_disagree_floor}：judge 自身不稳，"
                f"本可硬挡但降级人判，换 judge 或加采样复判）")
    return {**base, "level": "warn", "code": "vlm_semantic_review",
            "msg": (f"{kindlabel}「{name}」VLM 疑似不符（conf={conf:.2f}）：{mis}。本镜 {png}——人判是否真漂。{note}")}


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


def merge_shot_canonical(mask: Dict[str, Dict[str, Any]], png: str, matched: bool, conf: float) -> None:
    """累积逐镜 canonical 通过表（纯函数·可测）：一张图判过多个资产，**任一不符即整镜 fail**
    （fidelity-gate 取最严：一镜里有任何崩设定的实体，这镜就不该进一致性均值）。"""
    rel = str(png or "").strip()
    if not rel:
        return
    cur = mask.get(rel)
    if cur is None:
        mask[rel] = {"canonical_pass": bool(matched), "confidence": round(float(conf), 4)}
        return
    cur["canonical_pass"] = bool(cur["canonical_pass"]) and bool(matched)
    cur["confidence"] = max(float(cur.get("confidence") or 0.0), round(float(conf), 4))


def evaluate_pairs(pairs: Sequence[Mapping[str, Any]], canon_map: Mapping[str, Dict[str, str]],
                   judge: Judge, shot_abspath: Callable[[str], str],
                   block_floor: float = VLM_BLOCK_FLOOR, votes: int = VLM_VOTES,
                   vote_disagree_floor: float = VLM_VOTE_DISAGREE_FLOOR) -> Dict[str, Any]:
    """逐对 (canonical ↔ 本镜) 调 VLM judge → findings（注入 stub 可测）。
    同时产逐镜 canonical 通过表 shot_canonical（G3 fidelity-gate 用：face/语义一致性聚合前先剔崩设定镜）。
    votes≥3 时每对自一致采样多次取多数票，分歧高的判题降级人判（不硬挡）。"""
    findings: List[Dict[str, str]] = []
    shot_canonical: Dict[str, Dict[str, Any]] = {}
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
            cache[ckey] = judge_verdict(judge, abspath, entry["canonical"], entry["kind"], votes)
        verdict = cache[ckey]
        if verdict is None:
            continue
        judged += 1
        merge_shot_canonical(shot_canonical, str(png_rel),
                             bool(verdict.get("match")), float(verdict.get("confidence") or 0.0))
        fnd = verdict_finding(str(p.get("name")), entry["kind"], str(png_rel), verdict,
                              is_key=True, block_floor=block_floor,
                              vote_disagree_floor=vote_disagree_floor)
        if fnd:
            findings.append(fnd)
    block = sum(1 for f in findings if f["level"] == "block")
    return {"available": True, "judged": judged, "block_floor": block_floor, "votes": int(votes),
            "block": block, "findings": findings, "shot_canonical": shot_canonical}


# ── VLM 后端（best-effort·opt-in·不 hardcode 厂商） ───────────────────────────

def _n2dvlm_env_exists() -> bool:
    """本机是否有 n2dvlm conda 环境（直接探 envs/n2dvlm 目录，不跑 conda 以免慢/副作用）。"""
    bases = []
    cp = os.environ.get("CONDA_PREFIX")
    if cp:
        bases += [cp, os.path.dirname(os.path.dirname(cp))]
    bases += ["/opt/homebrew/Caskroom/miniforge/base",
              os.path.expanduser("~/miniforge3"), os.path.expanduser("~/miniconda3"),
              os.path.expanduser("~/anaconda3")]
    return any(b and os.path.isdir(os.path.join(b, "envs", "n2dvlm")) for b in bases)


def _auto_vlm_cmd() -> str:
    """N2D_VLM_CMD 未设时的本机默认：仓库 bundle 的 mlxvlm 单图后端 + n2dvlm 环境都在 → 自动接上。

    缺适配器/环境 → 返回 ""（load_judge 退回 None，优雅降级，CI/裸机零影响）。仍可被显式
    N2D_VLM_CMD 覆盖、或 N2D_VLM_CMD=off 关闭。详见 n2d-review/references/vlm_backend.md。"""
    adapter = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "..", "n2d-review", "scripts", "backends", "vlm_cmd_mlxvlm.py"))
    if os.path.isfile(adapter) and _n2dvlm_env_exists():
        return f"conda run -n n2dvlm python {shlex.quote(adapter)} --image {{image}} --prompt {{prompt}}"
    return ""


def load_judge() -> Optional[Judge]:
    """构造 VLM judge：显式 `N2D_VLM_CMD` 命令模板优先；未设时自动接本机 bundle 的 mlxvlm 后端
    （`_auto_vlm_cmd`，n2dvlm 环境在才接）；都没有 → None（整段跳过，不阻断默认产线）。

    命令模板用 {image} {prompt} 占位（prompt 经 shell-quote 注入），stdout 应回判定 JSON。
    例：export N2D_VLM_CMD='python3 ~/bin/vlm_judge.py --image {image} --prompt {prompt}'
    厂商无关：包装 Claude/OpenAI 视觉 API、本地 Qwen-VL/InternVL CLI 均可。`N2D_VLM_CMD=off` 强制关。"""
    tmpl = os.environ.get("N2D_VLM_CMD", "").strip()
    if tmpl.lower() in ("off", "none", "disabled", "0"):
        return None
    if not tmpl:
        tmpl = _auto_vlm_cmd()
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
            judge: Optional[Judge] = None, block_floor: float = VLM_BLOCK_FLOOR,
            votes: int = VLM_VOTES, vote_disagree_floor: float = VLM_VOTE_DISAGREE_FLOOR) -> Dict[str, Any]:
    """image_qc 集成入口：抽 (canonical↔镜) 对跑 VLM 判定。judge=None → 尝试自动加载。
    无 VLM 后端 → available=False（advisory 跳过，绝不阻断默认产线）。
    votes 由 `N2D_VLM_VOTES` 控（默认 1）：≥3 时每镜自一致采样多次取多数票、分歧高的降级人判。"""
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
    return evaluate_pairs(pairs, canon_map, j, shot_abspath, block_floor, votes, vote_disagree_floor)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true",
                    help="落档逐镜 canonical 通过表 → 生产数据/vlm_canonical_<集>.json，供 G3 fidelity-gate 消费")
    ns = ap.parse_args(argv)
    root = Path(ns.root).expanduser().resolve()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import image_qc  # type: ignore
    payload = image_qc.run_qc(root, ns.episode)
    res = analyze(root, ns.episode, payload)
    if ns.write:
        out = root / "生产数据" / f"vlm_canonical_{ns.episode}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        shot_canonical = res.get("shot_canonical", {})
        # 盖输入指纹：canonical 通过表必须证明「对应当前这批图」。fidelity-gate 据此判 stale——
        # 若 vlm_verify 后图片又重出，旧 canonical 不能再用脸分数糊弄终验（present-but-stale=BLOCK）。
        inputs_fingerprint = None
        try:
            _lib = str(Path(__file__).resolve().parent.parent.parent / "n2d" / "_lib")
            if _lib not in sys.path:
                sys.path.insert(0, _lib)
            from skill_snapshot import artifact_fingerprint  # n2d/_lib（gate 同源）
            inputs_fingerprint = artifact_fingerprint(str(root), list(shot_canonical.keys()))
        except Exception:
            inputs_fingerprint = None
        out.write_text(json.dumps({
            "kind": "n2d_vlm_canonical",
            "episode": ns.episode,
            "available": bool(res.get("available")),
            "shot_canonical": shot_canonical,
            "inputs_fingerprint": inputs_fingerprint,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✓ canonical 通过表已落档：{out}")
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if not res.get("available"):
        print("⏭ VLM 语义判定跳过：" + "；".join(res.get("notes", [])))
        return 0
    print(f"VLM 语义判定（{ns.episode}）：判 {res['judged']} 镜 · floor {res['block_floor']} · "
          f"投票 {res.get('votes', 1)}× · {res['block']} block / {len(res['findings'])} 条")
    for f in res["findings"]:
        print(f"  [{f['level']}] {f['msg']}")
    return 2 if res.get("block") else 0


if __name__ == "__main__":
    raise SystemExit(main())
