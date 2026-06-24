#!/usr/bin/env python3
"""扩展一致性检查器（2026-06 一致性加固第二批）。

补齐主审计此前没有的几类一致性维度。每个检查器纯标准库、缺契约/缺登记优雅降级（先 WARN
不硬阻断），重模型证据走可插拔 sidecar（缺则跳过、交人判）：

* UI1  系统面板/HUD 一致性 —— 穿越系统流的系统面板/血条/等级框/属性条是 n2d 招牌题材元素，
        但此前只作"桥段注入"，不是被锁定的资产；跨集 UI 视觉 + 图中中文文字极易漂。
        读 设定库/ui_asset_registry.json（面板定妆底图 + 边框/配色/字体/版式锁），
        对 storyboard 里的面板镜核对是否绑定登记 UI 资产。
* LM1  音乐母题/leitmotif 一致性 —— 声音侧的 voice_key 类比：角色/情绪主题动机跨集复现且不串用。
        读 设定库/leitmotif_registry.json（subject→motif）。
* GRD  系列调色 —— 剧级 LUT/白平衡/对比基线锁（tone_light 只管片内像素冷暖，缺剧级锁逐集观感漂）。
        读 设定库/series_grade.json + 合成产物的 applied 证据。
* AMB  环境声 —— 每场环境声床跨镜/跨集一致（reverb_profile 管混响，不管环境底噪连续性）。
        读 设定库/ambient_map.json（LOC→ambient bed）。
* R2   跨集体型 —— 此前只有脸有跨集质心漂移，身材/体型无跨集追踪。
        读 出图/共享/identity_registry.json 的 character_dna.身形 锁，对本集 prompt 体型描述做对立词冲突检。
* O3V  在场检测（视觉级对象持久性）—— 关掉"物件常驻只有契约文本、无视觉在场检测"的 backlog。
        读可选 sidecar 生产数据/object_presence_<集>.json（owlv2/grounding-DINO/VLM runner 产出）。
* VAP  外观判官（VLM-Appearance）—— ArcFace 测身份 embedding 之外，补"人眼可感外观相似度"的模型判官，
        在 insightface 降级（无库/侧背脸）时补盲区。读可选 sidecar 生产数据/appearance_judge_<集>.json。
* EXP1 表情/情绪连续性 —— 脸/发/服 DNA 锁住后的下一前沿（performance consistency）：该镜表情贴不贴
        脚本情绪 + 跨镜同角色表情不 OOC 跳变。优先读 expression 判官 sidecar；缺则纯文本 first-pass。
* SP1  伏笔兑现（setup→payoff 跨集闭环）—— P0/P1 管状态跨集，本检查管"叙事坑"跨集：直接给小说文件、
        不经上游小说创作线时漫剧侧无叙事连续性兜底。读 设定库/setup_payoff_ledger.json 校验坑没填/兑现早于种下。

返回结构与 production_consistency.analyze 同构：{"sections": {label: {available, findings, notes}}}。
被 consistency_audit.run() 统一调起并外发到 consistency_findings。

用法：python3 extended_consistency.py <作品根> 第N集 [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from typing import Any, Dict, List, Mapping, Optional, Tuple

import production_consistency as pc  # 复用 storyboard/prompt/registry/产物读取与 _row（同一 skill 内）

# ── 可选 sidecar 契约 kind（重模型 runner 产出，主审计只读）──────────────────────
OBJECT_PRESENCE_KIND = "n2d_object_presence"
APPEARANCE_JUDGE_KIND = "n2d_appearance_judge"

# UI/HUD 镜头识别词（穿越系统流题材元素）
UI_KEYWORDS = (
    "系统面板", "系统提示", "状态栏", "属性面板", "属性条", "血条", "血量条", "经验条",
    "等级框", "技能栏", "背包", "签到", "抽奖", "任务面板", "HUD", "界面元素", "弹窗",
    "system panel", "status panel", "UI面板", "面板浮现", "面板亮起",
)
# 图中需渲染中文文字的元素（AI 生图文字最不稳）
TEXT_IN_IMAGE_KEYWORDS = ("牌匾", "匾额", "招牌", "对联", "横幅", "卷轴文字", "书页文字", "界面文字", "面板文字")
UI_ASSET_RE = re.compile(r"\bUI_[\w\-一-鿿]+\b")

# 体型/身形对立词组（跨集冲突机检；同组内出现互斥词=漂移嫌疑）
BODY_ANTONYMS: Tuple[Tuple[str, ...], ...] = (
    ("纤细", "瘦弱", "清瘦", "苗条", "单薄"),
    ("魁梧", "壮硕", "高大", "健壮", "魁伟", "膀大腰圆"),
    ("矮小", "矮", "娇小"),
    ("高挑", "颀长", "修长"),
    ("丰腴", "丰满", "微胖", "圆润"),
)


def _load_json(path: str) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _registry(root: str, *rels: str) -> Any:
    for rel in rels:
        data = _load_json(os.path.join(root, rel))
        if data is not None:
            return data
    return None


def _identity_registry(root: str) -> Optional[dict]:
    data = _registry(root, os.path.join("出图", "共享", "identity_registry.json"),
                      os.path.join("出图", "common", "identity_registry.json"))
    return data if isinstance(data, dict) else None


def _clip_iter(root: str, ep: str):
    sb, clips = pc._storyboard(root, ep)
    prompts = pc._prompt_sections(root, ep)
    for idx, clip in enumerate(clips, 1):
        label = pc._clip_label(clip, idx)
        text = pc._clip_text(clip, label, prompts)
        yield clip, label, text
    return


# ── UI1 系统面板/HUD ──────────────────────────────────────────────────────────
def _system_state_ledger(root: str, ep: str) -> Tuple[Optional[dict], str]:
    for rel in (
        os.path.join("生产数据", f"system_state_ledger_{ep}.json"),
        os.path.join("设定库", "system_state_ledger.json"),
        os.path.join("设定库", "system_progression.json"),
    ):
        data = _load_json(os.path.join(root, rel))
        if isinstance(data, dict):
            return data, rel
    return None, os.path.join("设定库", "system_state_ledger.json")


def _system_state_rows(data: Any) -> List[dict]:
    if isinstance(data, dict):
        raw = data.get("states") or data.get("rows") or data.get("items") or data.get("metrics") or []
        if isinstance(raw, dict):
            rows = []
            for key, value in raw.items():
                if isinstance(value, list):
                    rows.extend({**(item if isinstance(item, dict) else {}), "metric": key} for item in value)
                elif isinstance(value, dict):
                    rows.append({"metric": key, **value})
            raw = rows
    else:
        raw = data
    return [x for x in pc._as_list(raw) if isinstance(x, dict)]


def _state_metric(row: Mapping[str, Any]) -> str:
    return str(row.get("metric") or row.get("key") or row.get("name") or row.get("stat") or row.get("属性") or "").strip()


def _state_value(row: Mapping[str, Any]) -> Optional[float]:
    for key in ("value", "number", "level", "rank", "score", "数值", "等级"):
        try:
            value = row.get(key)
            if value not in (None, ""):
                return float(value)
        except Exception:
            continue
    return None


def _state_order(row: Mapping[str, Any]) -> Tuple[int, int, str]:
    ep_n = _ep_num(str(row.get("episode") or row.get("ep") or "")) or 10**9
    clip_n = pc._clip_index(str(row.get("clip") or row.get("clip_id") or row.get("shot") or ""))
    return ep_n, clip_n, str(row.get("timecode") or "")


def _system_state_findings(data: Mapping[str, Any], rel: str) -> List[dict]:
    findings: List[dict] = []
    rows = _system_state_rows(data)
    by_metric: Dict[str, List[dict]] = {}
    for row in rows:
        metric = _state_metric(row)
        if metric:
            by_metric.setdefault(metric, []).append(row)
    for metric, metric_rows in by_metric.items():
        prev: Optional[dict] = None
        for row in sorted(metric_rows, key=_state_order):
            cur = _state_value(row)
            prv = _state_value(prev) if prev else None
            if cur is not None and prv is not None and cur < prv and not (
                row.get("rollback_reason") or row.get("decrease_reason") or row.get("剧情降级原因")
            ):
                findings.append(pc._row(
                    "warn",
                    f"系统数值 {metric} 从 {prv:g} 降到 {cur:g}，但缺 rollback_reason/decrease_reason；成长值/等级显示疑似回退。",
                    stage="script_stage2",
                    shot=str(row.get("clip") or row.get("shot") or ""),
                    artifacts=[rel],
                ))
            prev = row
    return findings


def check_ui_hud(root: str, ep: str) -> dict:
    sb, clips = pc._storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    if not clips:
        res["notes"].append("缺 storyboard clips[]，系统面板/HUD 检查跳过。")
        return res
    reg = _registry(root, os.path.join("设定库", "ui_asset_registry.json"),
                    os.path.join("出图", "共享", "ui_asset_registry.json"))
    reg_assets = {}
    if isinstance(reg, dict):
        for a in (reg.get("assets") or reg.get("ui_assets") or []):
            if isinstance(a, dict):
                aid = str(a.get("id") or a.get("ui_id") or "").strip()
                if aid:
                    reg_assets[aid] = a

    panel_shots: List[Tuple[str, str]] = []  # (label, kind)
    for _clip, label, text in _clip_iter(root, ep):
        low = text.lower()
        is_panel = any(k.lower() in low for k in UI_KEYWORDS)
        has_text = any(k in text for k in TEXT_IN_IMAGE_KEYWORDS)
        if is_panel or has_text:
            panel_shots.append((label, "panel" if is_panel else "text_in_image"))

    if not panel_shots:
        res["notes"].append("本集未检出系统面板/HUD/图中文字镜头，UI 一致性无可评项。")
        return res

    numeric_panel = [
        label for label, _kind in panel_shots
        if re.search(r"(等级|经验|成长值|属性|战力|积分|余额|血量|HP|MP|level|exp|score)", next((t for _c, lb, t in _clip_iter(root, ep) if lb == label), ""), re.I)
    ]
    ledger, ledger_rel = _system_state_ledger(root, ep)
    if numeric_panel and ledger is None:
        res["findings"].append(pc._row(
            "warn",
            f"检出 {len(numeric_panel)} 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核。",
            stage="script_stage2",
            artifacts=[ledger_rel, f"脚本/{ep}/storyboard.json"],
        ))
    elif isinstance(ledger, dict):
        res["findings"].extend(_system_state_findings(ledger, ledger_rel))

    res["notes"].append(f"检出 {len(panel_shots)} 个 UI/HUD/图中文字镜头。")
    if not reg_assets:
        res["findings"].append(pc._row(
            "warn",
            f"检出 {len(panel_shots)} 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——"
            "系统面板/血条/等级框跨集易漂、面板中文渲染不稳；建库锁面板定妆底图（边框/配色/字体/版式）并 image2image 只换数值区。",
            stage="image", shot=panel_shots[0][0],
            artifacts=["设定库/ui_asset_registry.json", f"脚本/{ep}/storyboard.json"],
        ))
        return res

    # 注册表存在：① 面板镜是否绑定登记 UI 资产；② 登记资产锁字段是否齐全（跨集稳定的前提）。
    required_locks = ("frame", "palette", "font", "layout")
    for aid, a in reg_assets.items():
        blob = pc._json_text(a)
        missing = [k for k in required_locks if k not in a and {
            "frame": "边框", "palette": "配色", "font": "字体", "layout": "版式"}[k] not in blob]
        if missing:
            res["findings"].append(pc._row(
                "warn",
                f"UI 资产 {aid} 缺锁字段：{'、'.join(missing)}——跨集面板复用前补齐边框/配色/字体/版式锁。",
                stage="image", artifacts=[f"设定库/ui_asset_registry.json#{aid}"],
            ))
    for label, kind in panel_shots:
        bound = UI_ASSET_RE.findall(label) or []
        # 在镜头文本里找 UI_ 绑定
        text_for_label = next((t for _c, lb, t in _clip_iter(root, ep) if lb == label), "")
        bound = UI_ASSET_RE.findall(text_for_label)
        if not bound:
            res["findings"].append(pc._row(
                "warn",
                f"{label} 是 {kind} 镜头但未绑定登记 UI 资产（UI_*）——绑定 ui_asset_registry 的面板定妆，保证跨集同一套视觉。",
                stage="image", shot=label, artifacts=[f"出图/{ep}/prompt/01_分镜出图.md"],
            ))
        elif any(b not in reg_assets for b in bound):
            unknown = [b for b in bound if b not in reg_assets]
            res["findings"].append(pc._row(
                "warn",
                f"{label} 绑定了未登记 UI 资产 {('、'.join(unknown))}——补进 ui_asset_registry 或改绑已登记面板。",
                stage="image", shot=label, artifacts=["设定库/ui_asset_registry.json"],
            ))
    return res


# ── LM1 音乐母题/leitmotif ────────────────────────────────────────────────────
def _bgm_cue_text(clip: Mapping[str, Any]) -> str:
    parts = []
    for key in ("bgm", "music", "配乐", "音乐", "leitmotif", "motif", "score"):
        v = clip.get(key)
        if v:
            parts.append(pc._json_text(v) if not isinstance(v, str) else v)
    return " ".join(parts)


def check_leitmotif(root: str, ep: str) -> dict:
    sb, clips = pc._storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    if sb is None:
        res["notes"].append("缺 storyboard，音乐母题检查跳过。")
        return res
    reg = _registry(root, os.path.join("设定库", "leitmotif_registry.json"))
    # subject(角色/情绪主题) → motif_id 映射
    subject_motif: Dict[str, str] = {}
    if isinstance(reg, dict):
        for m in (reg.get("motifs") or reg.get("leitmotifs") or []):
            if not isinstance(m, dict):
                continue
            mid = str(m.get("id") or m.get("motif_id") or "").strip()
            for subj in pc._as_list(m.get("subject") or m.get("subjects") or m.get("character") or m.get("characters")):
                s = str(subj or "").strip()
                if s and mid:
                    subject_motif.setdefault(s, mid)

    # 本集出现的 bgm cue 主体（角色 CHAR_/情绪主题词）
    cues: List[Tuple[str, str]] = []  # (label, cue_text)
    chars_seen = set()
    for clip, label, text in _clip_iter(root, ep):
        cue = _bgm_cue_text(clip)
        if cue:
            cues.append((label, cue))
        chars_seen.update(pc._char_ids(text))

    has_music_signal = bool(cues) or len(chars_seen) >= 2
    if not has_music_signal:
        res["notes"].append("本集 storyboard 无 bgm cue、角色稀少，音乐母题无可评项。")
        return res

    if not isinstance(reg, dict) or not subject_motif:
        res["findings"].append(pc._row(
            "warn",
            "本集有配乐/多角色但缺 设定库/leitmotif_registry.json——"
            "建议像 voice_key 一样为主要角色/情绪主题登记主题动机（subject→motif），保证跨集 BGM 母题可复现不串用。",
            stage="script_stage1", artifacts=["设定库/leitmotif_registry.json", f"脚本/{ep}/storyboard.json"],
        ))
        return res

    # 注册表存在：检 cue 引用的 motif 是否与登记一致（同一 subject 不应在本集映射到 ≠ 登记的 motif）
    motif_id_re = re.compile(r"\b(?:MOTIF|LM)_[\w\-一-鿿]+\b")
    motifs = reg.get("motifs") or reg.get("leitmotifs") or []
    for motif in motifs:
        if not isinstance(motif, dict):
            continue
        mid = str(motif.get("id") or motif.get("motif_id") or "").strip()
        media = str(motif.get("file") or motif.get("audio") or motif.get("clip") or motif.get("path") or "").strip()
        if not media:
            res["findings"].append(pc._row(
                "warn",
                f"音乐母题 {mid or '(unknown)'} 缺 file/audio/clip；生成式 BGM 只写描述无法保证跨集复现。",
                stage="script_stage1",
                artifacts=["设定库/leitmotif_registry.json"],
            ))
        elif not pc._artifact_exists(root, media):
            res["findings"].append(pc._row(
                "warn",
                f"音乐母题 {mid or '(unknown)'} 引用音频不存在：{media}。",
                stage="compose",
                artifacts=["设定库/leitmotif_registry.json", media],
            ))
        if not (motif.get("audio_sha256") or motif.get("hash") or motif.get("cue") or motif.get("start_time")):
            res["findings"].append(pc._row(
                "warn",
                f"音乐母题 {mid or '(unknown)'} 缺 audio_sha256/hash/cue；无法确认 compose 复用的是同一段动机。",
                stage="compose",
                artifacts=["设定库/leitmotif_registry.json"],
            ))
    for label, cue in cues:
        ids_in_cue = motif_id_re.findall(cue)
        subjects_in_cue = pc._char_ids(cue)
        for subj in subjects_in_cue:
            expected = subject_motif.get(subj)
            if expected and ids_in_cue and expected not in ids_in_cue:
                res["findings"].append(pc._row(
                    "warn",
                    f"{label}：角色 {subj} 的配乐用了 {('、'.join(ids_in_cue))}，与 leitmotif_registry 登记的 {expected} 不符（母题串用）。",
                    stage="compose", shot=label, artifacts=["设定库/leitmotif_registry.json", f"合成/{ep}"],
                ))
    res["notes"].append(f"leitmotif_registry 已登记 {len(subject_motif)} 个主体动机。")
    return res


# ── GRD 系列调色（剧级 LUT/白平衡/对比基线）──────────────────────────────────
def check_series_grade(root: str, ep: str) -> dict:
    finals = pc._final_cuts(root, ep)
    res = {"available": bool(finals), "findings": [], "notes": []}
    if not finals:
        res["notes"].append("本集未出成片，系列调色检查跳过（compose 后复跑）。")
        return res
    grade = _registry(root, os.path.join("设定库", "series_grade.json"))
    if not isinstance(grade, dict):
        res["findings"].append(pc._row(
            "warn",
            "成片已出但缺 设定库/series_grade.json——剧级调色锁（LUT/白平衡/对比/饱和基线）缺位，逐集观感色温/对比易漂；"
            "tone_light_contract 只焊片内像素，补一份剧级 grade 让 compose 统一套用。",
            stage="compose", artifacts=["设定库/series_grade.json", f"合成/{ep}"],
        ))
        return res
    locks = ("lut", "white_balance", "contrast", "saturation", "白平衡", "对比", "饱和", "色调")
    blob = pc._json_text(grade)
    if not any(k in grade or k in blob for k in locks):
        res["findings"].append(pc._row(
            "warn",
            "series_grade.json 存在但未声明 LUT/白平衡/对比/饱和任一基线——补齐剧级调色锁字段。",
            stage="compose", artifacts=["设定库/series_grade.json"],
        ))
    # 每集 applied 证据：合成/<集>/grade_applied.json 或成片 meta 声明套用
    applied = _registry(root, os.path.join("合成", ep, "grade_applied.json"))
    if not isinstance(applied, dict):
        res["findings"].append(pc._row(
            "warn",
            f"{ep} 成片缺 合成/{ep}/grade_applied.json 套用证据——compose 应留痕本集套用了哪版剧级调色，便于跨集对账。",
            stage="compose", artifacts=[f"合成/{ep}/grade_applied.json"],
        ))
    else:
        res["notes"].append("series_grade 已声明且本集留有套用证据。")
    return res


# ── AMB 环境声 ────────────────────────────────────────────────────────────────
def check_ambient(root: str, ep: str) -> dict:
    sb, clips = pc._storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    if not clips:
        res["notes"].append("缺 storyboard clips[]，环境声检查跳过。")
        return res
    amap = _registry(root, os.path.join("设定库", "ambient_map.json"))
    locs_in_ep: Dict[str, List[str]] = {}
    clip_ambient: Dict[str, str] = {}
    for clip, label, text in _clip_iter(root, ep):
        loc = pc._loc_of(clip, text)
        if loc:
            locs_in_ep.setdefault(loc, []).append(label)
        amb = str(clip.get("ambient") or clip.get("环境声") or "").strip()
        if amb:
            clip_ambient[label] = amb

    if not locs_in_ep:
        res["notes"].append("本集无可识别场景 LOC，环境声无可评项。")
        return res

    if not isinstance(amap, dict):
        res["findings"].append(pc._row(
            "warn",
            f"本集涉 {len(locs_in_ep)} 个场景但缺 设定库/ambient_map.json——"
            "reverb_profile 只管每场混响，环境底噪（雨/集市/宫廷）跨镜跨集连续性无锁；建 LOC→ambient bed 映射。",
            stage="compose", artifacts=["设定库/ambient_map.json", f"脚本/{ep}/storyboard.json"],
        ))
        return res

    declared = amap.get("scenes") or amap.get("locations") or amap
    declared_keys = set(declared.keys()) if isinstance(declared, dict) else set()
    only_at_compose = bool(pc._final_cuts(root, ep))
    for loc, labels in locs_in_ep.items():
        if loc not in declared_keys:
            res["findings"].append(pc._row(
                "warn" if only_at_compose else "warn",
                f"场景 {loc}（{len(labels)} 镜）在 ambient_map.json 无登记环境声床——补一条 {loc}→ambient bed。",
                stage="compose", shot=labels[0], artifacts=["设定库/ambient_map.json"],
            ))
    # 同 LOC 内 storyboard 显式 ambient 互相冲突
    for loc, labels in locs_in_ep.items():
        ambs = {clip_ambient[l] for l in labels if l in clip_ambient}
        if len(ambs) > 1:
            res["findings"].append(pc._row(
                "warn",
                f"场景 {loc} 内各镜声明了不一致的环境声：{('、'.join(sorted(ambs)))}——同场景环境床应一致或显式标注转场原因。",
                stage="compose", shot=labels[0], artifacts=[f"脚本/{ep}/storyboard.json"],
            ))
    return res


# ── R2 跨集体型 ───────────────────────────────────────────────────────────────
def _body_lock_of(entry: Mapping[str, Any]) -> str:
    dna = entry.get("character_dna") or entry.get("dna") or {}
    if isinstance(dna, dict):
        for k in ("body", "身形", "体型", "build", "physique", "proportion"):
            v = dna.get(k)
            if v:
                return pc._json_text(v) if not isinstance(v, str) else v
    for k in ("body", "身形", "体型"):
        v = entry.get(k)
        if v:
            return str(v)
    return ""


def _antonym_group(text: str) -> Optional[int]:
    for i, group in enumerate(BODY_ANTONYMS):
        if any(w in text for w in group):
            return i
    return None


def check_body_proportion(root: str, ep: str) -> dict:
    reg = _identity_registry(root)
    res = {"available": reg is not None, "findings": [], "notes": []}
    if reg is None:
        res["notes"].append("缺 出图/共享/identity_registry.json，跨集体型检查跳过。")
        return res
    chars = reg.get("characters") or reg.get("identities") or {}
    if isinstance(chars, dict):
        char_items = list(chars.items())
    else:
        char_items = [(str(c.get("id") or c.get("char_id") or i), c) for i, c in enumerate(chars) if isinstance(c, dict)]

    # 本集 prompt 文本（按角色聚合体型描述）
    ep_text_by_char: Dict[str, str] = {}
    for clip, label, text in _clip_iter(root, ep):
        for cid in pc._char_ids(text):
            ep_text_by_char[cid] = ep_text_by_char.get(cid, "") + " " + text

    long_line = 0
    locked = 0
    for cid, entry in char_items:
        if not isinstance(entry, dict):
            continue
        cid = str(cid)
        forms = entry.get("forms")
        body = _body_lock_of(entry)
        if not body and isinstance(forms, list):
            for f in forms:
                if isinstance(f, dict):
                    body = body or _body_lock_of(f)
        appears = entry.get("appears_in") or entry.get("episodes") or []
        is_long = (isinstance(appears, list) and len(appears) >= 2) or bool(entry.get("core")) or bool(entry.get("long_line"))
        if is_long:
            long_line += 1
        if body:
            locked += 1
            # 本集 prompt 体型描述 vs 登记锁的对立词冲突
            ep_text = ep_text_by_char.get(cid, "")
            lock_grp = _antonym_group(body)
            ep_grp = _antonym_group(ep_text)
            if lock_grp is not None and ep_grp is not None and lock_grp != ep_grp:
                res["findings"].append(pc._row(
                    "warn",
                    f"角色 {cid} 登记体型锁含「{BODY_ANTONYMS[lock_grp][0]}」类，但本集 prompt 体型描述偏「{BODY_ANTONYMS[ep_grp][0]}」类——跨集体型漂移嫌疑。",
                    stage="image", artifacts=["出图/共享/identity_registry.json", f"出图/{ep}/prompt/01_分镜出图.md"],
                ))
        elif is_long:
            res["findings"].append(pc._row(
                "warn",
                f"长线角色 {cid} 缺 character_dna.身形/体型 跨集锁——此前只有脸有跨集漂移追踪，补体型锁防逐集变高/变胖。",
                stage="image", artifacts=[f"出图/共享/identity_registry.json#{cid}"],
            ))
    res["notes"].append(f"角色 {len(char_items)} 个，长线 {long_line}，已锁体型 {locked}。")
    return res


# ── O3V 在场检测 / VAP 外观判官（可插拔 sidecar 读取）──────────────────────────
def _read_sidecar(root: str, ep: str, kind: str, *rels: str) -> Optional[dict]:
    for rel in rels:
        data = _load_json(os.path.join(root, rel))
        if isinstance(data, dict) and (data.get("kind") == kind or not data.get("kind")):
            return data
    return None


def check_object_presence_visual(root: str, ep: str) -> dict:
    """O3V：读可选 object_presence sidecar（owlv2/grounding-DINO/VLM 在场检测 runner 产出）。
    缺则跳过——O3 物件常驻仍由 production_consistency 的契约文本检 + 人判兜底。"""
    data = _read_sidecar(root, ep, OBJECT_PRESENCE_KIND,
                         os.path.join("生产数据", f"object_presence_{ep}.json"),
                         os.path.join("出图", ep, "object_presence.json"))
    res = {"available": data is not None, "findings": [], "notes": []}
    if data is None:
        res["notes"].append("缺 object_presence sidecar（可选视觉在场检测 runner）；O3 物件常驻由契约文本 + 人判兜底。")
        return res
    for f in data.get("findings") or data.get("shots") or []:
        if not isinstance(f, dict):
            continue
        present = f.get("present")
        expected = f.get("expected")
        sev = str(f.get("severity") or "").lower()
        shot = str(f.get("shot") or f.get("clip") or "")
        asset = str(f.get("asset") or f.get("object") or "")
        if expected is True and present is False:
            res["findings"].append(pc._row(
                sev if sev in ("block", "warn") else "block",
                f"{shot}：登记常驻对象 {asset} 视觉检测缺席（object permanence 违例）。",
                stage="image", shot=shot, artifacts=[f"出图/{ep}/图片"]))
        elif expected is False and present is True:
            res["findings"].append(pc._row(
                sev if sev in ("block", "warn") else "warn",
                f"{shot}：本不应在场的对象 {asset} 出现（应已消失/被遮挡后未恢复）。",
                stage="image", shot=shot, artifacts=[f"出图/{ep}/图片"]))
        elif sev in ("block", "warn"):
            res["findings"].append(pc._row(sev, f"{shot}：{asset} 在场异常（{f.get('message') or ''}）",
                                            stage="image", shot=shot, artifacts=[f"出图/{ep}/图片"]))
    return res


def check_appearance_judge(root: str, ep: str) -> dict:
    """VAP：读可选 VLM-Appearance 判官 sidecar（跨镜同角色外观相似度，补 ArcFace 盲区）。缺则跳过。"""
    data = _read_sidecar(root, ep, APPEARANCE_JUDGE_KIND,
                         os.path.join("生产数据", f"appearance_judge_{ep}.json"),
                         os.path.join("出图", ep, "appearance_judge.json"))
    res = {"available": data is not None, "findings": [], "notes": []}
    if data is None:
        res["notes"].append("缺 appearance_judge sidecar（可选 VLM-Appearance 判官）；脸一致以 ArcFace G1 为准。")
        return res
    for f in data.get("findings") or data.get("shots") or []:
        if not isinstance(f, dict):
            continue
        verdict = str(f.get("verdict") or f.get("severity") or "").lower()
        if verdict not in ("block", "warn"):
            continue
        shot = str(f.get("shot") or f.get("clip") or "")
        char = str(f.get("character") or f.get("char") or "")
        sim = f.get("similarity")
        msg = f.get("message") or f"角色 {char} 外观判官相似度偏低"
        if sim is not None:
            msg = f"{msg}（相似度 {sim}）"
        res["findings"].append(pc._row(verdict, f"{shot}：{msg}", stage="image", shot=shot,
                                        artifacts=[f"出图/{ep}/图片"]))
    return res


TEXT_RENDER_KIND = "n2d_text_render"


def _expected_text_for(text: str, ui_assets: Dict[str, dict]) -> str:
    """从镜头文本/绑定的 UI 资产 text_template 取该镜应渲染的预期文字（供 OCR 校验对照）。"""
    for aid in UI_ASSET_RE.findall(text):
        a = ui_assets.get(aid)
        if isinstance(a, dict) and (a.get("text_template") or a.get("text")):
            return str(a.get("text_template") or a.get("text"))
    # storyboard clip 显式声明的图中文字字段
    m = re.search(r'(?:图中文字|界面文字|牌匾文字|on_image_text|render_text)["：:\s]+([^\n"，。；]+)', text)
    return m.group(1).strip() if m else ""


def check_text_render(root: str, ep: str) -> dict:
    """OCR1：图中文字渲染校验。读可选 text_render sidecar（OCR runner 实读图中文字 vs 预期）；
    缺 sidecar 时做 first-pass——检出文字镜但无声明预期文字（OCR 无对照基准）→ WARN 提示声明。

    AI 生图的中文字渲染（系统面板数值/牌匾/卷轴）是 2026 仍未解的弱项，必须实读校验而非假设画对。"""
    sb, clips = pc._storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    # ① sidecar 实读结果（OCR runner 产出）
    data = _read_sidecar(root, ep, TEXT_RENDER_KIND,
                         os.path.join("生产数据", f"text_render_{ep}.json"),
                         os.path.join("出图", ep, "text_render.json"))
    if data is not None:
        res["available"] = True
        for f in data.get("findings") or []:
            if not isinstance(f, dict):
                continue
            verdict = str(f.get("verdict") or f.get("severity") or "").lower()
            if verdict not in ("block", "warn"):
                continue
            shot = str(f.get("shot") or f.get("clip") or "")
            exp = f.get("expected") or ""
            got = f.get("ocr_text") or ""
            sim = f.get("similarity")
            msg = f.get("message") or f"图中文字渲染与预期不符：预期「{exp}」OCR 实读「{got}」"
            if sim is not None:
                msg = f"{msg}（相似度 {sim}）"
            res["findings"].append(pc._row(verdict, f"{shot}：{msg}", stage="image", shot=shot,
                                            artifacts=[f"出图/{ep}/图片"]))
        return res
    # ② first-pass：无 sidecar 时，检文字镜是否声明了可校验的预期文字
    if not clips:
        res["notes"].append("缺 storyboard 或 text_render sidecar，图中文字校验跳过。")
        return res
    reg = _registry(root, os.path.join("设定库", "ui_asset_registry.json"),
                    os.path.join("出图", "共享", "ui_asset_registry.json"))
    ui_assets = {}
    if isinstance(reg, dict):
        for a in (reg.get("assets") or reg.get("ui_assets") or []):
            if isinstance(a, dict) and a.get("id"):
                ui_assets[str(a["id"])] = a
    text_shots, undeclared = 0, 0
    for _clip, label, text in _clip_iter(root, ep):
        low = text.lower()
        if not (any(k.lower() in low for k in UI_KEYWORDS) or any(k in text for k in TEXT_IN_IMAGE_KEYWORDS)):
            continue
        text_shots += 1
        if not _expected_text_for(text, ui_assets):
            undeclared += 1
            res["findings"].append(pc._row(
                "warn",
                f"{label} 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头"
                "「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。",
                stage="image", shot=label, artifacts=[f"出图/{ep}/prompt/01_分镜出图.md"]))
    if text_shots:
        res["notes"].append(f"检出 {text_shots} 个图中文字镜（{undeclared} 个缺预期文字）；缺 text_render sidecar，"
                            "跑 text_render_runner + OCR 后端实读校验。")
    else:
        res["notes"].append("本集未检出图中文字镜，OCR 校验无可评项。")
    return res


# ── TX1 译名一致（专有名词/称谓跨集 EN 译法统一·纯标准库）──────────────────────
def _read_text(root: str, *rels: str) -> str:
    parts = []
    for rel in rels:
        t = pc._read(os.path.join(root, rel))
        if t:
            parts.append(t)
    return "\n".join(parts)


def check_translation_terms(root: str, ep: str) -> dict:
    """TX1：专有名词/称谓/技能等级的中文 canonical 与 EN 译名跨集一致。

    读 `translation_glossary.json` / `terminology_glossary.json`：
    - `{terms:[{cn,en,aliases,forbidden}]}` 或 `{cn: en}`；
    - 中文 voiceover/SRT 出现 forbidden/alias 而 canonical 缺席 → WARN；
    - 英文字幕未用 canonical en → WARN。
    """
    res = {"available": False, "findings": [], "notes": []}
    cn_text = _read_text(root, os.path.join("脚本", ep, "voiceover.txt"),
                         os.path.join("脚本", ep, "字幕_中文.srt"),
                         os.path.join("脚本", ep, "subtitles_zh.srt"))
    en_text = _read_text(root, os.path.join("脚本", ep, "字幕_英文.srt"),
                         os.path.join("脚本", ep, "字幕_双语.srt"),
                         os.path.join("脚本", ep, "subtitles_en.srt"))
    glossary = _registry(root, os.path.join("设定库", "translation_glossary.json"),
                         os.path.join("设定库", "terminology_glossary.json"),
                         os.path.join("设定库", "term_glossary.json"))
    pairs: List[Tuple[str, str]] = []
    term_rows: List[dict] = []
    seen_cn: Dict[str, set] = {}
    if isinstance(glossary, dict):
        raw = glossary.get("terms")
        if isinstance(raw, list):
            for t in raw:
                if isinstance(t, dict) and t.get("cn") and t.get("en"):
                    pairs.append((str(t["cn"]), str(t["en"])))
                    term_rows.append(t)
                elif isinstance(t, dict) and (t.get("cn") or t.get("canonical") or t.get("canonical_cn")):
                    term_rows.append(t)
        else:
            for cn, en in glossary.items():
                if cn not in ("kind", "version") and isinstance(en, str):
                    pairs.append((str(cn), en))
                    term_rows.append({"cn": str(cn), "en": en})
    if not term_rows and not pairs:
        if not en_text:
            res["notes"].append("本集无 EN 字幕且无术语表，译名/术语一致检查跳过。")
            return res
        res["available"] = True
        res["findings"].append(pc._row(
            "warn",
            "有 EN 字幕但缺 translation_glossary/terminology_glossary——专有名词/称谓/技能/等级跨集易出多种写法；"
            "从角色卡/称谓表种一份 canonical 术语表锁死中英文写法。",
            stage="script_stage2", artifacts=["设定库/translation_glossary.json", f"脚本/{ep}/字幕_英文.srt"]))
        return res
    res["available"] = True
    # glossary 自身一个 cn 映射到多个 en → 冲突
    for cn, en in pairs:
        seen_cn.setdefault(cn, set()).add(en)
    for cn, ens in seen_cn.items():
        if len(ens) > 1:
            res["findings"].append(pc._row(
                "warn", f"glossary 自身冲突：「{cn}」登记了多个译名 {sorted(ens)}——收敛成唯一 canonical。",
                stage="script_stage2", artifacts=["设定库/translation_glossary.json"]))
    # 中文 canonical / forbidden / alias 检查
    for row in term_rows:
        canonical = str(row.get("cn") or row.get("canonical_cn") or row.get("canonical") or row.get("term") or "").strip()
        aliases = [str(x).strip() for x in pc._as_list(row.get("aliases") or row.get("alias") or row.get("variants")) if str(x).strip()]
        forbidden = [str(x).strip() for x in pc._as_list(row.get("forbidden") or row.get("forbidden_cn") or row.get("禁用")) if str(x).strip()]
        for token in forbidden:
            if token and token in cn_text:
                res["findings"].append(pc._row(
                    "warn",
                    f"本集中文文本出现术语禁用写法「{token}」，应统一为「{canonical or '(canonical missing)'}」。",
                    stage="script_stage2",
                    artifacts=["设定库/translation_glossary.json", f"脚本/{ep}/voiceover.txt"],
                ))
        for alias in aliases:
            if alias and canonical and alias in cn_text and canonical not in cn_text:
                res["findings"].append(pc._row(
                    "warn",
                    f"本集使用术语别名「{alias}」但未使用 canonical「{canonical}」；人名/技能名/等级名跨集写法可能漂移。",
                    stage="script_stage2",
                    artifacts=["设定库/translation_glossary.json", f"脚本/{ep}/voiceover.txt"],
                ))
    # 本集 cn 出现但 EN 字幕未用约定译名
    en_low = en_text.lower()
    if en_text:
        for cn, en in pairs:
            if cn and cn in cn_text and en and en.lower() not in en_low:
                res["findings"].append(pc._row(
                    "warn",
                    f"本集台词出现「{cn}」但 EN 字幕未见约定译名「{en}」——译名漂移，统一为 glossary canonical。",
                    stage="script_stage2", shot="",
                    artifacts=[f"脚本/{ep}/字幕_英文.srt", "设定库/translation_glossary.json"]))
    else:
        if pairs:
            res["notes"].append("glossary 已登记 EN canonical，但本集无 EN 字幕；仅完成中文术语 canonical 检查。")
    res["notes"].append(f"glossary 登记术语 {len(term_rows) or len(pairs)} 条；中文 canonical 与 EN 译名已按可用文本核对。")
    return res


# ── EXP1 表情/情绪连续性（脸锁住之后的下一前沿·折进判官 checklist）──────────────
EXPRESSION_KIND = "n2d_expression"
# 粗情绪桶（关键词 → 桶）：跨镜硬跳/贴不贴脚本节拍的最小可判粒度，不做细粒度情感分析。
EMOTION_BUCKETS = {
    "悲": ("哭", "泪", "落泪", "悲", "哀", "啜泣", "崩溃", "凄"),
    "怒": ("怒", "愤", "咆哮", "暴怒", "怒吼", "瞪", "咬牙", "震怒"),
    "喜": ("笑", "喜", "欢", "雀跃", "窃喜", "莞尔", "大笑", "喜悦"),
    "惊": ("惊", "愕", "震惊", "错愕", "骇", "瞠目", "目瞪"),
    "惧": ("惧", "怕", "恐", "颤抖", "战栗", "畏"),
    "冷": ("冷漠", "面无表情", "淡漠", "漠然", "无波", "冷峻"),
}
CLOSEUP_MARKERS = ("近景", "特写", "大特写", "脸部", "面部", "CU", "close-up", "closeup", "面庞", "眼神特写")
EXPRESSION_REF_MARKERS = ("表情参考", "expressions", "表情库", "微表情", "expression_ref", "表情锚")


def _emotions_in(text: str) -> set:
    """文本命中的粗情绪桶集合（纯函数·可测）。"""
    return {bucket for bucket, kws in EMOTION_BUCKETS.items() if any(k in text for k in kws)}


def check_expression_continuity(root: str, ep: str) -> dict:
    """EXP1：表情/情绪连续性——脸/发/服 DNA 锁住后的下一前沿（performance consistency）。

    ① 有 expression sidecar（`生产数据/expression_<集>.json`·VLM/VAP 判官产出「该镜表情是否贴脚本
       情绪 + 跨镜同角色表情不 OOC 跳变」）→ 直接消费 verdict（这是「折进判官 checklist」的落点）；
    ② 无 sidecar 时 first-pass（纯文本·advisory）：
       - 情绪近景镜但 prompt 未声明表情参考 → WARN（跨镜表情无锚点，OOC 跳变高发，补 expressions 参考）；
       - 相邻镜同角色脚本情绪硬跳（喜↔悲/怒↔喜…）→ WARN（确认有节拍依据，否则表演穿帮）。
    纯标准库，缺 storyboard 优雅跳过。"""
    # ① sidecar 实判优先（fold into judge）
    data = _read_sidecar(root, ep, EXPRESSION_KIND,
                         os.path.join("生产数据", f"expression_{ep}.json"),
                         os.path.join("出图", ep, "expression.json"))
    if data is not None:
        res = {"available": True, "findings": [], "notes": []}
        for f in data.get("findings") or data.get("shots") or []:
            if not isinstance(f, dict):
                continue
            verdict = str(f.get("verdict") or f.get("severity") or "").lower()
            if verdict not in ("block", "warn"):
                continue
            shot = str(f.get("shot") or f.get("clip") or "")
            char = str(f.get("character") or f.get("char") or "")
            exp = f.get("expected") or f.get("scripted_emotion") or ""
            got = f.get("observed") or f.get("observed_expression") or ""
            msg = f.get("message") or f"角色 {char} 表情与脚本情绪不符（脚本「{exp}」观测「{got}」）"
            res["findings"].append(pc._row(verdict, f"{shot}：{msg}", stage="image", shot=shot,
                                            artifacts=[f"出图/{ep}/图片"]))
        res["notes"].append("消费 expression 判官 sidecar（表情贴脚本 + 跨镜不 OOC）。")
        return res
    # ② first-pass（纯文本·advisory）
    sb, clips = pc._storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    if not clips:
        res["notes"].append("缺 storyboard 或 expression sidecar，表情连续性检查跳过（跑表情判官写 expression sidecar 可实判）。")
        return res
    prev_by_char: Dict[str, set] = {}
    emo_shots = 0
    for _clip, label, text in _clip_iter(root, ep):
        emos = _emotions_in(text)
        is_closeup = any(m.lower() in text.lower() for m in CLOSEUP_MARKERS)
        has_ref = any(m.lower() in text.lower() for m in EXPRESSION_REF_MARKERS)
        chars = pc._char_ids(text)
        if emos and is_closeup:
            emo_shots += 1
            if not has_ref:
                res["findings"].append(pc._row(
                    "warn",
                    f"{label} 情绪近景（{'/'.join(sorted(emos))}）但未声明表情参考——跨镜同角色表情易 OOC 跳变；"
                    "补 expressions 表情参考（同源脸 × 该情绪）或跑表情判官实判。",
                    stage="image", shot=label, artifacts=[f"出图/{ep}/prompt/01_分镜出图.md"]))
        # 相邻镜同角色情绪硬跳
        for cid in chars:
            prev = prev_by_char.get(cid)
            if prev and emos and not (prev & emos) and prev != emos:
                res["findings"].append(pc._row(
                    "warn",
                    f"{label}：角色 {cid} 相邻镜情绪硬跳（{'/'.join(sorted(prev))}→{'/'.join(sorted(emos))}）"
                    "——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。",
                    stage="script_stage2", shot=label, artifacts=[f"脚本/{ep}/storyboard.json"]))
            if emos:
                prev_by_char[cid] = emos
    if emo_shots:
        res["notes"].append(f"检出 {emo_shots} 个情绪近景镜；缺 expression sidecar，深度表情贴合由表情判官/人判兜底。")
    else:
        res["notes"].append("本集未检出情绪近景镜，表情连续性无可评项。")
    return res


# ── SP1 伏笔兑现（setup→payoff 跨集兑现·补漫剧侧叙事连续性兜底）──────────────────
def _ep_num(ep: str) -> Optional[int]:
    """'第3集' / 'ep3' / '3' → 3；解析不出 → None。纯函数·可测。"""
    m = re.search(r"\d+", str(ep or ""))
    return int(m.group()) if m else None


FORESHADOW_MARKERS = ("伏笔", "悬念", "埋下", "留下疑问", "未解", "成谜", "卖关子", "cliffhanger", "钩子", "悬而未决")


def check_setup_payoff(root: str, ep: str) -> dict:
    """SP1：伏笔种下→兑现 跨集闭环——补「直接给小说文件、不经上游小说创作线时，漫剧侧无叙事连续性兜底」。

    P0/P1+state_ledger 管语义/视觉「状态」跨集；本检查管「叙事坑」跨集：读
    `设定库/setup_payoff_ledger.json`（`{pairs:[{id,setup_ep,payoff_ep,desc,status}]}` 或 `{setups:[...]}`），
    校验整账：① 兑现早于种下（payoff_ep<setup_ep）② 坑没填（setup 有但 payoff_ep 空且非 status=ongoing）
    ③ 兑现镜的种下集缺失 ④ id 重复。缺账但本集检出伏笔/悬念钩 → WARN 建账。纯标准库。"""
    res = {"available": False, "findings": [], "notes": []}
    cur = _ep_num(ep)
    ledger = _registry(root, os.path.join("设定库", "setup_payoff_ledger.json"))
    if not isinstance(ledger, dict):
        # 缺账：本集有伏笔钩才提醒建账（不无脑刷）
        cn_text = _read_text(root, os.path.join("脚本", ep, "voiceover.txt"),
                             os.path.join("脚本", ep, "字幕_中文.srt"))
        sb, _clips = pc._storyboard(root, ep)
        hay = cn_text + "\n" + (json.dumps(sb, ensure_ascii=False) if sb else "")
        if any(m in hay for m in FORESHADOW_MARKERS):
            res["available"] = True
            res["findings"].append(pc._row(
                "warn",
                "本集检出伏笔/悬念钩但缺 设定库/setup_payoff_ledger.json——长篇跨集易断坑（种下不兑现/兑现早于"
                "种下）。直接给小说文件、不经上游小说创作线时漫剧侧无叙事连续性兜底；跑 n2d-script 的 setup_payoff_ledger.py "
                "建账并锁每个伏笔的兑现集。",
                stage="script_stage2", artifacts=["设定库/setup_payoff_ledger.json", f"脚本/{ep}/voiceover.txt"]))
        else:
            res["notes"].append("缺 setup_payoff_ledger.json 且本集无明显伏笔钩，伏笔兑现检查跳过。")
        return res
    res["available"] = True
    pairs = ledger.get("pairs") or ledger.get("setups") or []
    seen_ids: Dict[str, int] = {}
    for p in pairs:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id") or p.get("desc") or "?")
        desc = str(p.get("desc") or pid)
        s_ep = _ep_num(str(p.get("setup_ep") or p.get("setup") or ""))
        p_ep = _ep_num(str(p.get("payoff_ep") or p.get("payoff") or ""))
        status = str(p.get("status") or "").lower()
        seen_ids[pid] = seen_ids.get(pid, 0) + 1
        if s_ep is not None and p_ep is not None and p_ep < s_ep:
            res["findings"].append(pc._row(
                "warn", f"伏笔「{desc}」兑现早于种下（payoff 第{p_ep}集 < setup 第{s_ep}集）——逻辑倒置，核对集序。",
                stage="script_stage2", artifacts=["设定库/setup_payoff_ledger.json"]))
        if s_ep is not None and p_ep is None and status not in ("ongoing", "open", "planned", "进行中"):
            res["findings"].append(pc._row(
                "warn", f"伏笔「{desc}」（第{s_ep}集种下）无兑现集（坑没填）——补 payoff_ep 或标 status=ongoing。",
                stage="script_stage2", artifacts=["设定库/setup_payoff_ledger.json"]))
        if p_ep is not None and s_ep is None:
            res["findings"].append(pc._row(
                "warn", f"伏笔「{desc}」有兑现集（第{p_ep}集）却无种下集——补 setup_ep，否则兑现来得突兀。",
                stage="script_stage2", artifacts=["设定库/setup_payoff_ledger.json"]))
        # 本集相关提示
        if cur is not None and p_ep == cur and s_ep is not None:
            res["notes"].append(f"本集兑现伏笔「{desc}」（第{s_ep}集种下）——确认兑现镜已落实。")
    for pid, n in seen_ids.items():
        if n > 1:
            res["findings"].append(pc._row(
                "warn", f"setup_payoff_ledger 重复 id「{pid}」（{n} 次）——收敛成唯一条目。",
                stage="script_stage2", artifacts=["设定库/setup_payoff_ledger.json"]))
    res["notes"].append(f"setup_payoff_ledger 登记 {len(pairs)} 条伏笔；整账已校验。")
    return res


_NS_LINE_RE = re.compile(r"^\[镜头(\d+)·([^·\]]+)·([^·\]]+?)(?:·([^·\]]+))?\]\s*(.*)$")
_NS_MOVE_RE = re.compile(r"(前往|赶往|出发|动身|启程|赶赴|回到|来到|抵达|进了|赶回|奔向|赶去|离开|踏上)")


def _ns_lines(text: str) -> List[Tuple[str, str]]:
    rows: List[Tuple[str, str]] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _NS_LINE_RE.match(line)
        rows.append((m.group(2).strip(), (m.group(5) or "").strip()) if m else ("", line))
    return rows


def check_narrative_state(root: str, ep: str) -> dict:
    """NS1：叙事状态（知识/位置/关系）跨集一致性——补「视觉 state_ledger 不管知识/位置/关系」的洞。

    读 `设定库/narrative_state_ledger.json`（n2d-script narrative_state_audit.py 产），对**已声明填全**的
    条目做确定性校验：① 知识倒流（声明第K集才知道，但更早集该角色已提及该 keyword）；② 位置瞬移
    （同角色相邻有声明的集换了地点、两集都无转场词）。缺账但本集有知识/位置标记 → WARN 建账。
    独立线·复制不 import（与 n2d-script 同口径）。纯标准库。"""
    res: dict = {"available": False, "findings": [], "notes": []}
    ledger = _registry(root, os.path.join("设定库", "narrative_state_ledger.json"))
    # 收集全剧各集 voiceover（跨集校验需要）
    ep_texts: Dict[int, str] = {}
    for path in glob.glob(os.path.join(root, "脚本", "第*集", "voiceover.txt")):
        n = _ep_num(os.path.basename(os.path.dirname(path)))
        if n is not None:
            ep_texts[n] = _read_text(root, os.path.relpath(path, root))
    if not isinstance(ledger, dict):
        cur_txt = _read_text(root, os.path.join("脚本", ep, "voiceover.txt"))
        if re.search(r"(知道了|得知|才知道|这才明白|原来|发现|前往|赶往|抵达|回到)", cur_txt):
            res["available"] = True
            res["findings"].append(pc._row(
                "warn",
                "本集有知识/位置叙事但缺 设定库/narrative_state_ledger.json——跨集易出『知道得太早/位置瞬移』"
                "硬伤。跑 n2d-script 的 narrative_state_audit.py --write 建账，填 character/keyword/known_from_ep。",
                stage="script_stage1", artifacts=["设定库/narrative_state_ledger.json", f"脚本/{ep}/voiceover.txt"]))
        else:
            res["notes"].append("缺 narrative_state_ledger.json 且本集无明显知识/位置标记，叙事状态检查跳过。")
        return res
    res["available"] = True
    # ① 知识倒流
    for k in ledger.get("knowledge") or []:
        if not isinstance(k, dict):
            continue
        char, kw = str(k.get("character") or "").strip(), str(k.get("keyword") or "").strip()
        kn = _ep_num(str(k.get("known_from_ep") or ""))
        if not (char and kw and kn is not None):
            continue
        for n, txt in ep_texts.items():
            if n >= kn:
                continue
            if any(kw in body and (role == char or char in body) for role, body in _ns_lines(txt)):
                res["findings"].append(pc._row(
                    "warn", f"知识倒流：「{k.get('fact') or kw}」声明第{kn}集才知道，但第{n}集 {char} 已提及「{kw}」"
                            "——核对谁在第几集知道什么。",
                    stage="script_stage1", artifacts=["设定库/narrative_state_ledger.json"]))
                break
    # ② 位置瞬移
    by_char: Dict[str, List[dict]] = {}
    for loc in ledger.get("locations") or []:
        if isinstance(loc, dict) and str(loc.get("character") or "").strip() \
                and _ep_num(str(loc.get("ep") or "")) is not None and loc.get("place"):
            by_char.setdefault(str(loc["character"]).strip(), []).append(loc)
    for char, locs in by_char.items():
        locs = sorted(locs, key=lambda x: _ep_num(str(x["ep"])))
        for a, b in zip(locs, locs[1:]):
            if a["place"] == b["place"]:
                continue
            txt_a = ep_texts.get(_ep_num(str(a["ep"])), "")
            txt_b = ep_texts.get(_ep_num(str(b["ep"])), "")
            if _NS_MOVE_RE.search(txt_a) or _NS_MOVE_RE.search(txt_b):
                continue
            res["findings"].append(pc._row(
                "warn", f"位置瞬移：{char} {a['ep']}在「{a['place']}」、{b['ep']}在「{b['place']}」，两集都无转场"
                        "——补过场或确认是否漏写。",
                stage="script_stage1", artifacts=["设定库/narrative_state_ledger.json"]))
    res["notes"].append(f"narrative_state_ledger 登记 知识 {len(ledger.get('knowledge') or [])}/"
                        f"位置 {len(ledger.get('locations') or [])}/关系 {len(ledger.get('relationships') or [])} 条；已校验。")
    return res


SECTION_BUILDERS = (
    ("系统面板(UI1)", check_ui_hud),
    ("音乐母题(LM1)", check_leitmotif),
    ("系列调色(GRD)", check_series_grade),
    ("环境声(AMB)", check_ambient),
    ("跨集体型(R2)", check_body_proportion),
    ("在场检测(O3V)", check_object_presence_visual),
    ("外观判官(VAP)", check_appearance_judge),
    ("文字渲染(OCR1)", check_text_render),
    ("译名一致(TX1)", check_translation_terms),
    ("表情连续(EXP1)", check_expression_continuity),
    ("伏笔兑现(SP1)", check_setup_payoff),
    ("叙事状态(NS1)", check_narrative_state),
)

# 每段的回流 stage + 定位产物（供 consistency_audit 归一 affected_artifacts）
SECTION_META: Dict[str, dict] = {
    "系统面板(UI1)": {"stage": "image", "artifacts": ("脚本/{ep}/storyboard.json", "设定库/ui_asset_registry.json", "出图/{ep}/prompt/01_分镜出图.md")},
    "音乐母题(LM1)": {"stage": "script_stage1", "artifacts": ("脚本/{ep}/storyboard.json", "设定库/leitmotif_registry.json")},
    "系列调色(GRD)": {"stage": "compose", "artifacts": ("设定库/series_grade.json", "合成/{ep}/grade_applied.json")},
    "环境声(AMB)": {"stage": "compose", "artifacts": ("设定库/ambient_map.json", "脚本/{ep}/storyboard.json")},
    "跨集体型(R2)": {"stage": "image", "artifacts": ("出图/共享/identity_registry.json", "出图/{ep}/prompt/01_分镜出图.md")},
    "在场检测(O3V)": {"stage": "image", "artifacts": ("生产数据/object_presence_{ep}.json", "出图/{ep}/图片")},
    "外观判官(VAP)": {"stage": "image", "artifacts": ("生产数据/appearance_judge_{ep}.json", "出图/{ep}/图片")},
    "文字渲染(OCR1)": {"stage": "image", "artifacts": ("生产数据/text_render_{ep}.json", "设定库/ui_asset_registry.json", "出图/{ep}/图片")},
    "译名一致(TX1)": {"stage": "script_stage2", "artifacts": ("设定库/translation_glossary.json", "脚本/{ep}/字幕_英文.srt")},
    "表情连续(EXP1)": {"stage": "image", "artifacts": ("生产数据/expression_{ep}.json", "脚本/{ep}/storyboard.json", "出图/{ep}/prompt/01_分镜出图.md")},
    "伏笔兑现(SP1)": {"stage": "script_stage2", "artifacts": ("设定库/setup_payoff_ledger.json", "脚本/{ep}/voiceover.txt")},
    "叙事状态(NS1)": {"stage": "script_stage1", "artifacts": ("设定库/narrative_state_ledger.json", "脚本/{ep}/voiceover.txt")},
}


def analyze(root: str, ep: str) -> dict:
    sections: Dict[str, dict] = {}
    for label, builder in SECTION_BUILDERS:
        try:
            sections[label] = builder(root, ep)
        except Exception as exc:  # 单段失败不拖垮整批
            sections[label] = {"available": False, "findings": [], "notes": [f"{label} 检查异常（忽略）：{exc}"]}
    return {"sections": sections}


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="扩展一致性检查器（UI/leitmotif/调色/环境声/跨集体型/在场/外观/表情/伏笔兑现/叙事状态）")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    block = 0
    for label, sec in res["sections"].items():
        vs = [f.get("verdict") for f in sec.get("findings", [])]
        b = sum(1 for v in vs if v == "block")
        w = sum(1 for v in vs if v == "warn")
        block += b
        st = "（跳过）" if not sec.get("available") and not sec.get("findings") else f"🔴{b} 🟡{w}"
        print(f"{label:<14} {st}")
        for note in sec.get("notes", []):
            print(f"    · {note}")
        for f in sec.get("findings", [])[:4]:
            print(f"    {f.get('verdict')}: {f.get('message')}")
    return 1 if block else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
