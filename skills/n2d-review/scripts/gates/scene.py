#!/usr/bin/env python3
"""gates/scene.py — 镜头空间/光学连续/景别/奇观序列/动作节拍预算族

按证据族从 gate.py 拆出的 check_ 闸（增量3）。从 gate_core 取共享基座，避免与 gate.py 循环导入；
gate.py `from gates.scene import *` 回灌，run()/按名自省助手照常解析；成员经校验 call-graph-closed。
"""
from gate_core import *  # noqa: F401,F403
from gate_core import (
    _OTS_RE,
    _PHYSICAL_SCALE_TOKENS,
    _SHOT_BLOCK_SPLIT_RE,
    _gate_make_clip_id,
    _registry_character_names,
    _registry_relative_scales,
)

def check_shot_scale_progression(root: str, ep: str) -> None:
    """景别阶梯机检：契约只校验「景别阶梯」字段存在（check_image_prompt_overview）；这里补对**实际镜序列**的机检——
    连续 >=3 镜同景别、且段内无反打/过肩（对白正反打是合法交替变化，豁免）= 景别阶梯单调、缺远近/机位变化 → warn。
    文本匹配较模糊（景别藏在 lens 串里），故 warn 不 block。"""
    sb = load_json(storyboard_path(root, ep))
    if not isinstance(sb, dict):
        return  # storyboard 缺失由 check_storyboard_contract 负责 BLOCK，这里不重复
    clips = sb.get("clips") or sb.get("shots") or []
    if not isinstance(clips, list) or len(clips) < SHOT_SCALE_MIN_RUN:
        return
    classes: List[Optional[str]] = []
    lens_texts: List[str] = []
    ids: List[str] = []
    for i, clip in enumerate(clips, 1):
        if not isinstance(clip, dict):
            classes.append(None); lens_texts.append(""); ids.append(f"Clip_{i:02d}"); continue
        # 新 schema 的 shots 可能是 int 列表（非 dict）；只读 dict 形 shot，并兜底 continuity.shot_size。
        lens = "；".join(str(s.get("lens", "")) for s in (clip.get("shots") or []) if isinstance(s, dict))
        cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
        scale_text = lens or str(clip.get("景别") or clip.get("shot_size") or cont.get("shot_size") or "")
        classes.append(shot_scale_class(scale_text))
        lens_texts.append(lens or scale_text)
        ids.append(str(clip.get("id") or clip.get("clip") or clip.get("shot") or f"Clip_{i:02d}"))
    for start, end, cls, length in monotonous_scale_runs(classes):
        if any(_OTS_RE.search(lens_texts[k]) for k in range(start, end + 1)):
            continue  # 对白正反打/过肩交替 = 合法景别变化，豁免
        loc = f"{ids[start]}→{ids[end]}"
        add(WARN, "景别阶梯", loc,
            f"连续 {length} 镜同景别 {cls}（{loc}）——景别阶梯单调、缺远近或机位变化；"
            "按导演意图穿插不同景别/机位（或确认为设计内的同景别段）。",
            return_to_stage="image")
    # 抽取健壮性（G）：lens 写了但抽不出景别分级的镜（如「中景偏特写」「平视带点压」这类非标准写法），
    # 景别阶梯机检对它们静默失效——把这些镜醒目报出来，提示规范 lens 写法，避免「全绿=都查过了」的错觉。
    unparsed = [ids[i] for i in range(len(classes)) if classes[i] is None and lens_texts[i].strip()]
    if len(unparsed) >= 2:
        sample = "、".join(unparsed[:6]) + ("…" if len(unparsed) > 6 else "")
        add(WARN, "景别阶梯", sample,
            f"{len(unparsed)} 个镜写了 lens 但抽不出景别分级（{sample}）——景别阶梯单调性机检对它们失效；"
            "把 lens 写成标准景别词（ELS/LS/MS/MCU/CU/ECU 或 大远景/远景/中景/中近景/特写/大特写）再机检。",
            return_to_stage="image")

def check_cinematic_optical_continuity(root: str, ep: str) -> None:
    """Validate that focal lengths match shot sizes to prevent perspective distortion."""
    pd = os.path.join(root, "出图", ep, "prompt")
    f = os.path.join(pd, "01_分镜出图.md")
    if not os.path.exists(f):
        return

    content = open(f, encoding="utf-8").read()
    shots = _SHOT_BLOCK_SPLIT_RE.split(content)

    # ECU/CU=85mm, MS=50mm, LS=35mm, ELS=24mm
    mapping = {
        "ECU": "85mm", "CU": "85mm",
        "MCU": "50mm", "MS": "50mm",
        "LS": "35mm", "ELS": "24mm"
    }

    for shot in shots:
        if not shot.strip(): continue

        shot_size_match = re.search(r"景别\((ELS|LS|MS|MCU|CU|ECU).*?\)", shot)
        if shot_size_match:
            size = shot_size_match.group(1)
            expected_focal = mapping.get(size)
            if expected_focal and expected_focal not in shot:
                add(WARN, "电影光学契约", f, f"镜头景别为 {size}，建议在 prompt 中显式锁定焦段为 {expected_focal} 以保透视一致")

def check_physical_scale_audit(root: str, ep: str) -> None:
    """Validate relative heights in multi-character shots.

    同框 ≥2 个 identity_registry 角色 → 两级对账（均 WARN，report-only，不加硬闸）：
    ① 该镜里有角色在 registry 声明了 `physical_scale.relative_scale`（相对身量），但本镜 prompt
       既没写它、也没任何身高/仰俯视关系词 → 声明了却没注入，提示把 relative_scale 写进镜头 prompt；
    ② 没人声明 relative_scale，且镜里没有任何高矮/仰俯视关系词 → 维持原通用提醒（建议补相对身量）。
    只对账 relative_scale（绝对 height_cm/体重是写作元数据，不进 prompt）。角色名/相对身量都从 registry 取，不写死 demo 名。"""
    pd = os.path.join(root, "出图", ep, "prompt")
    f = os.path.join(pd, "01_分镜出图.md")
    if not os.path.exists(f):
        return

    names = _registry_character_names(root)
    if len(names) < 2:
        return  # 不足两名可识别角色：无从判定同框，跳过（不臆造）
    rel_scales = _registry_relative_scales(root)

    content = open(f, encoding="utf-8").read()
    shots = _SHOT_BLOCK_SPLIT_RE.split(content)

    for shot in shots:
        if not shot.strip(): continue
        # 取镜内「目标：…」行（出图块标注同框人物处）；无该行则全块兜底扫名字。
        target_lines = re.findall(r"目标：[^\n]*", shot)
        scope = "\n".join(target_lines) if target_lines else shot
        present = {n for n in names if n in scope}
        if len(present) < 2:
            continue
        who = "、".join(sorted(present))
        has_scale_cue = any(k in shot for k in _PHYSICAL_SCALE_TOKENS)
        # ① 声明了 relative_scale 却没注入：本镜里有人声明、但 prompt 没出现其相对身量串、也没任何关系词
        declared = {n: rel_scales[n] for n in present if rel_scales.get(n)}
        missing_inject = {n: rs for n, rs in declared.items() if rs not in shot}
        if missing_inject and not has_scale_cue:
            detail = "；".join(f"{n}「{rs}」" for n, rs in sorted(missing_inject.items()))
            add(WARN, "物理尺寸对账", f,
                f"多人同框镜头（{who}）中 {detail} 在 registry 声明了相对身量(relative_scale)，"
                "但本镜 prompt 未写入——把声明的相对身量写进镜头 prompt，防同框比例穿帮（绝对身高数字不必写）。")
            continue
        # ② 无人声明 relative_scale 且镜里没有任何关系词：维持原通用提醒
        if not declared and not has_scale_cue:
            add(WARN, "物理尺寸对账", f,
                f"检测到多人同框镜头（{who}），建议显式写明人物之间的【相对身量/身高比例差】或【仰俯视关系】，防同框比例穿帮"
                "（可在 registry 角色 physical_scale.relative_scale 固化，以某角色为标尺）。")

def check_spectacle_sequence_plan(root: str, ep: str) -> None:
    """Require a sequence-level continuity ledger for spectacle clips before video."""
    data = load_json(storyboard_path(root, ep))
    if not isinstance(data, dict):
        return
    clips = data.get("clips") or []
    if not isinstance(clips, list):
        return
    required: Dict[str, str] = {}
    for idx, clip in enumerate(clips, 1):
        if not isinstance(clip, Mapping):
            continue
        kind = infer_spectacle_type(clip)
        if kind:
            required[_gate_make_clip_id(clip, idx)] = kind
    if not required:
        return

    rel = os.path.join("生产数据", f"spectacle_sequence_plan_{ep}.json")
    path = os.path.join(root, rel)
    plan = load_json(path)
    story_rel = os.path.relpath(storyboard_path(root, ep), root)
    if not isinstance(plan, dict):
        add(
            BLOCK,
            "高动态序列总账",
            path,
            f"storyboard 含高动态/大场景 Clip（{', '.join(required)}），但缺 {rel}；"
            "先生成跨 Clip 动作/空间/资产连续性总账，再进视频付费链路。",
            return_to_stage="script_stage2",
            affected_shots=list(required),
            affected_artifacts=[story_rel, rel],
            rerun_scope="运行 python3 skills/n2d-script/scripts/spectacle_sequence_plan.py <作品根> <集> --write 后重跑 video gate。",
        )
        return
    if str(plan.get("kind") or "") != SPECTACLE_SEQUENCE_PLAN_KIND:
        add(
            BLOCK,
            "高动态序列总账",
            path,
            f"spectacle_sequence_plan kind 必须是 {SPECTACLE_SEQUENCE_PLAN_KIND}。",
            return_to_stage="script_stage2",
            affected_artifacts=[rel],
        )
        return
    sequences = plan.get("sequences")
    if not isinstance(sequences, list) or not sequences:
        add(
            BLOCK,
            "高动态序列总账",
            path,
            "spectacle_sequence_plan 缺 sequences[]；不能用空总账放行高动态/大场景视频。",
            return_to_stage="script_stage2",
            affected_shots=list(required),
            affected_artifacts=[rel],
        )
        return
    covered = {
        str(cid)
        for seq in sequences if isinstance(seq, Mapping)
        for cid in (seq.get("clip_order") or [])
    }
    missing = [cid for cid in required if cid not in covered]
    if missing:
        add(
            BLOCK,
            "高动态序列总账",
            path,
            f"spectacle_sequence_plan 未覆盖 storyboard 高动态 Clip：{', '.join(missing)}；"
            "每条打斗/追逐/腾云/大场景都必须进入 sequence_id、handoff_state、path_lock 与引用策略。",
            return_to_stage="script_stage2",
            affected_shots=missing,
            affected_artifacts=[rel, story_rel],
            rerun_scope="重跑 spectacle_sequence_plan.py --write，并检查 clip_order 是否覆盖最新 storyboard。",
        )

def check_action_beat_budget(root: str, ep: str, stage: str = "video") -> None:
    """一镜一主导动作 + 单拍可读时长（Veo「一 clip 一动作」+ 打斗拆 2–3 拍）。

    高动态镜最常见崩法：把整段攻防(攻击+格挡+反击+命中)塞进一条 clip——物理引擎会乱、命中帧读不出。
    按动作节拍类别数 + 单拍时长预算给拆镜信号，把它挡在最贵的出视频之前。
    「单 Clip 时长超后端上限」已由 risk_flags long_duration 闸守，这里只补「节拍塞太满」这层。
    """
    data = load_json(storyboard_path(root, ep))
    if not isinstance(data, dict):
        return
    clips = data.get("clips") or []
    if not isinstance(clips, list):
        return
    story_rel = os.path.relpath(storyboard_path(root, ep), root)
    # 铁律 B11（2026-06-27）：一镜塞完整攻防回合 demo 也 BLOCK，不随 profile 降级。
    for idx, clip in enumerate(clips, 1):
        if not isinstance(clip, Mapping):
            continue
        kind = infer_spectacle_type(clip)
        if kind not in ACTION_CHOREOGRAPHY_SHOT_TYPES:
            continue
        clip_id = _gate_make_clip_id(clip, idx)
        cats = action_beat_categories(json.dumps(clip, ensure_ascii=False))
        try:
            dur = float(clip.get("duration") or 0)
        except (TypeError, ValueError):
            dur = 0.0
        beats = beat_decomposition(kind)
        beat_names = "/".join(b["beat"] for b in beats) or "起手/命中/反应"
        # ① 一镜塞了完整攻防回合（跨越 ≥3 个互斥节拍类别）→ 必须拆 beat。production 升 BLOCK。
        if len(cats) >= ACTION_BEAT_CATEGORY_SPLIT_THRESHOLD:
            add(
                BLOCK,
                "动作节拍预算",
                story_rel,
                f"{clip_id}({kind}) 一镜跨越 {len(cats)} 个动作节拍类别（{', '.join(cats)}）——"
                f"把完整攻防回合塞进一条 clip，模型物理易乱、命中帧读不出。按 beat 拆成 {beat_names} 各一镜"
                "（一镜一主导动作，相机从简）。",
                return_to_stage="script_stage2",
                affected_shots=[clip_id],
                affected_artifacts=[story_rel],
                rerun_scope="按 spectacle_sequence_plan 的 beat_decomposition 拆镜，回 n2d-script 阶段2 重切 storyboard，再跑 video gate。",
            )
            continue
        # ② 单拍时长不足：多个节拍挤进过短时长，命中帧/受力方向来不及读清（启发式·WARN）。
        if dur > 0 and len(cats) >= 2 and dur / len(cats) < MIN_ACTION_BEAT_SECONDS:
            add(
                WARN,
                "动作节拍预算",
                story_rel,
                f"{clip_id}({kind}) 时长 {dur:g}s 内塞了 {len(cats)} 个动作节拍（{', '.join(cats)}），"
                f"单拍均不足 {MIN_ACTION_BEAT_SECONDS:g}s——命中帧/受力方向来不及读清。延长该镜或拆成 {beat_names}。",
                return_to_stage="script_stage2",
                affected_shots=[clip_id],
                affected_artifacts=[story_rel],
            )

__all__ = [
    'check_shot_scale_progression',
    'check_cinematic_optical_continuity',
    'check_physical_scale_audit',
    'check_spectacle_sequence_plan',
    'check_action_beat_budget',
]
