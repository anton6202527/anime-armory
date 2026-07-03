#!/usr/bin/env python3
"""gates/voice.py — 配音指纹/音色跨集/原生音画身份/口型条件族（监控 monkeypatch 的 timing 闸留在 gate.py）

按证据族从 gate.py 拆出的 check_ 闸（增量3）。从 gate_core 取共享基座，避免与 gate.py 循环导入；
gate.py `from gates.voice import *` 回灌，run()/按名自省助手照常解析；成员经校验 call-graph-closed。
"""
from gate_core import *  # noqa: F401,F403
from gate_core import (
    _native_voice_segments_errors,
)

def check_voiceover_fingerprint(root: str, ep: str) -> None:
    """配音定稿后 voiceover.txt 又被改词/插句/删句 → 时长清单/字幕/镜头时长全部过期。

    `validate_timings` 在 n2d-script 阶段2收尾抓这条失配链，但 image/video preflight 此前不复查指纹——
    定稿后裸改台词，下游照常据过期时长出图出视频导致音画错位。这里把同一指纹比对前移到付费阶段闸门。
    原生音画模式镜头时长不依赖配音时长清单，跳过。
    """
    if is_native_av_production(root):
        return
    vo_p = os.path.join(root, "脚本", ep, "voiceover.txt")
    if not os.path.isfile(vo_p):
        return  # 无 voiceover：上游问题，require_progress/其它检查覆盖
    meta_p = voice_meta_path(root, ep)
    if not meta_p:
        # 占位轨/旧产物无指纹 sidecar：仅当配音非占位时温和提示（占位由 check_placeholder_policy 管）
        if voice_is_placeholder(root, ep) is False:
            add(WARN, "配音", vo_p, "无 时长清单.meta.json（旧配音产物）——无法核对配音后 voiceover 是否被改，建议重跑 n2d-voice 生成指纹")
        return
    recorded = (load_json(meta_p) or {}).get("voiceover_fingerprint")
    current = voiceover_fingerprint(vo_p)
    if recorded and current and recorded != current:
        add(
            BLOCK,
            "配音",
            vo_p,
            "voiceover.txt 在配音后被改动（台词指纹失配）→ 时长清单/字幕/镜头时长已过期；重跑 n2d-voice 再回跑 n2d-script 阶段2，过 gate 再出图/出视频",
            return_to_stage="voice",
            rerun_scope="重跑 n2d-voice 生成新时长清单 → 回跑 finalize_storyboard 重定镜头时长/字幕 → 再出图出视频。",
            affected_artifacts=[
                f"合成/{ep}/配音/时长清单.json",
                f"脚本/{ep}/storyboard.json",
                f"脚本/{ep}/字幕中.srt",
            ],
        )

def check_voice_cross_episode(root: str, ep: str) -> None:
    """声纹/音色键跨集一致性，在 image gate 渲染前自动落地（此前只在手动 identity.py --write 时打印、不拦）。

    三层信号，按确定性分级：
    - **voicemap 对账失配 → BLOCK**：本集某角色实际用的音色键 ≠ 设定库/voicemap.json 注册键＝确定性配置
      矛盾（你登记 A 却用了 B），出图/出视频前必须修，否则跨集换脸又换声。占位/应急轨与未登记角色已被
      voice_consistency 排除，不会误判。
    - **音色键跨集漂移 → WARN**：同角色相邻集音色键变了（可能是有意——附身/苍老/闪回换嗓，故只告警交人确认；
      若真是错且 voicemap 在册，上面的 BLOCK 已强制修）。
    - **声纹 embedding 跨集漂移**：resemblyzer/speechbrain 量同角色逐句余弦相似度。**band=bad（实测跌破
      自标定 floor）且 floor 真标定过 → BLOCK**（音色侧 ArcFace，与脸 G5 对称——实测硬漂不再当启发式埋没）；
      borderline(band=warn) / floor 未标定（单句欠采样）→ WARN 交人判。后端可缺（未装则 available=false，
      静默跳过、绝不报假漂移；原生音画的缺后端阻断在 check_native_voice_identity）；native 组在此跳过。

    全部 try/except 包住：声纹/对账是 advisory 增强，任何数据/后端异常都不该让 gate 崩或误拦正片。
    """
    # ① + ② 音色键 / voicemap（确定性，纯 stdlib，几乎不会异常）
    try:
        report = vcons.build_report(root)
    except Exception:
        report = None
    if isinstance(report, dict):
        man_rel = f"合成/{ep}/配音/时长清单.json"
        for m in report.get("voicemap_mismatches", []):
            if str(m.get("episode")) != ep:
                continue
            add(BLOCK, "跨集音色", f"voicemap:{m.get('character')}",
                f"角色「{m.get('character')}」实际音色键 {m.get('voice_key_used')} ≠ voicemap 注册键 "
                f"{m.get('voice_key_registered')}：跨集会换声穿帮，按注册音色重配（n2d-voice）后再出图。",
                return_to_stage="voice", rerun_scope=m.get("scope", ""),
                affected_shots=m.get("affected_shots", []),
                affected_artifacts=[man_rel, "设定库/voicemap.json"])
        for d in report.get("drifts", []):
            if str(d.get("episode_to")) != ep or d.get("episode_from") == d.get("episode_to"):
                continue  # 只看真·跨集漂移；同集内换键由其它链覆盖
            add(WARN, "跨集音色", f"voice_key:{d.get('character')}",
                f"角色「{d.get('character')}」音色键自 {d.get('episode_from')} 的 {d.get('voice_from')} 漂为 "
                f"{d.get('voice_to')}：确认是否有意（附身/苍老/闪回换嗓），否则回 n2d-voice 对齐前集音色。",
                return_to_stage="voice", rerun_scope=d.get("scope", ""),
                affected_shots=d.get("affected_shots", []),
                affected_artifacts=[man_rel, "设定库/voicemap.json"])
    # ③ 声纹 embedding（speaker-embedding 实测·后端可缺）
    # 这是音色侧的 ArcFace：band=bad（逐句余弦实测跌破**自标定** floor）= 真音色硬漂，与脸 G5 对称应
    # BLOCK，不再一刀切当启发式降 WARN（旧设计把实测硬漂埋没了）。calibrated=False（单句/欠采样、用兜底
    # floor）或 borderline(band=warn) → 仍 WARN 交人判，不在弱证据上硬拦。native_av 声线由
    # check_native_voice_identity 专管，这里跳过 |native: 组避免双报。后端缺(available=False)则整段跳过
    # （配音先行有 voicemap BLOCK 兜底确定性配置漂；原生音画的缺后端阻断在 check_native_voice_identity）。
    try:
        vp = vprint.analyze(root, ep)
    except Exception:
        vp = None
    if isinstance(vp, dict) and vp.get("available"):
        man = str(vp.get("manifest") or "")
        for label, group in sorted((vp.get("groups") or {}).items()):
            if not isinstance(group, dict) or "|native:" in str(label):
                continue
            sev = vprint._severity_for_group(group)
            if sev not in {"block", "warn"}:
                continue
            lines = group.get("lines") if isinstance(group.get("lines"), list) else []
            bad = sum(1 for ln in lines if isinstance(ln, dict) and ln.get("band") == "bad")
            warn = sum(1 for ln in lines if isinstance(ln, dict) and ln.get("band") == "warn")
            if sev == "block" and group.get("floor_calibrated") is True:
                add(BLOCK, "跨集声纹", f"voice_print:{label}",
                    f"声纹实测「{label}」音色硬漂：{bad} 句余弦跌破自标定 floor={group.get('floor')}"
                    f"（mode={vp.get('mode')}）——同角色跨集换声穿帮（音色侧 ArcFace，与脸 G5 对称）。"
                    "回 n2d-voice 按注册音色重配受影响台词后重测。",
                    return_to_stage="voice",
                    rerun_scope="声纹余弦跌破自标定 floor 的硬漂；回 n2d-voice 重配受影响角色台词后重测。",
                    affected_artifacts=[man] if man else [])
            else:
                # borderline / floor 未标定：弱证据，WARN 交人判（confidence=heuristic 防日后误升硬闸）。
                add(WARN, "跨集声纹", f"voice_print:{label}",
                    f"声纹机检「{label}」音色漂移：bad={bad} warn={warn}（floor={group.get('floor')} "
                    f"calibrated={group.get('floor_calibrated')} mode={vp.get('mode')}）：核对是否同一音色，必要时回 n2d-voice 重配。",
                    return_to_stage="voice",
                    rerun_scope="声纹余弦跌破校准 floor；回 n2d-voice 重配受影响角色台词后重测。",
                    confidence="heuristic",
                    affected_artifacts=[man] if man else [])

def check_native_voice_identity(root: str, ep: str, stage: str) -> None:
    if not is_native_av_production(root):
        return
    required = native_voice_identity_required(root, ep, stage)
    segments_path = native_voice_identity_path(root, ep)
    data = load_json(segments_path)
    if not isinstance(data, dict):
        sev = BLOCK if required else WARN
        add(
            sev,
            "原生音画声线一致性",
            segments_path,
            "缺 native voice identity 片段清单：原生音画说话镜的角色声线不走 n2d-voice 时长清单，"
            "需要从 clip 原生音轨切出逐角色台词 wav，写 `kind=n2d_native_voice_identity_segments`、"
            "segments[].character_id/speaker_key/wav，然后跑 "
            "`python3 skills/n2d-identity/scripts/voice_print_consistency.py <作品根> 第N集`。"
            + (" review/付费交付前不放行。" if required else " draft 可先继续，但 review 会阻断。"),
            return_to_stage="compose" if required else "review",
        )
        return
    errors = _native_voice_segments_errors(root, ep, data)
    if errors:
        add(
            BLOCK if required else WARN,
            "原生音画声线一致性",
            segments_path,
            "native voice identity 片段清单不完整：" + "；".join(errors),
            return_to_stage="compose" if required else "review",
        )
        return
    try:
        report = vprint.analyze(root, ep)
    except Exception as exc:
        add(BLOCK if required else WARN, "原生音画声线一致性", native_voice_print_report_path(root, ep),
            f"声纹分析失败：{type(exc).__name__}: {str(exc)[:120]}", return_to_stage="compose")
        return
    native_meta = report.get("native_voice_identity") if isinstance(report, Mapping) else {}
    if not isinstance(native_meta, Mapping) or native_meta.get("status") != "ok":
        add(
            BLOCK if required else WARN,
            "原生音画声线一致性",
            segments_path,
            f"native voice identity 未进入声纹分析：status={native_meta.get('status') if isinstance(native_meta, Mapping) else 'missing'}",
            return_to_stage="compose" if required else "review",
        )
        return
    if not report.get("available"):
        allow_degraded = os.environ.get("N2D_ALLOW_DEGRADED_QC") == "1"
        if allow_degraded and required:
            note_degraded_qc_waiver("原生音画声线一致性", ep, native_voice_print_report_path(root, ep),
                                    "声纹后端不可用·声线一致性降级放行")
        sev = WARN if allow_degraded else (BLOCK if required else WARN)
        add(
            sev,
            "原生音画声线一致性",
            native_voice_print_report_path(root, ep),
            f"native voice identity 片段已登记，但声纹后端不可用：mode={report.get('mode')} precision={report.get('precision')}。"
            + (" 已用 N2D_ALLOW_DEGRADED_QC 放行，需人审声线。" if allow_degraded else " 安装 resemblyzer/speechbrain 后重跑，或显式 N2D_ALLOW_DEGRADED_QC=1 留痕放行。"),
            return_to_stage="compose" if required else "review",
        )
        return
    for label, group in sorted((report.get("groups") or {}).items()):
        if not isinstance(group, Mapping) or "|native:" not in str(label):
            continue
        sev = vprint._severity_for_group(group)
        if sev not in {"block", "warn"}:
            continue
        # band=bad 且 floor 真标定过 = 实测音色硬漂。原生音画无 voicemap 兜底，声纹是唯一跨集声线证据，
        # 故 required（review/付费交付）时 BLOCK——与脸 G5 对称（音色侧 ArcFace）；draft/borderline/
        # 未标定 → WARN。这是有意分级：缺后端在上面已 block；这里是「后端跑了、实测到硬漂」的正证据。
        hard = sev == "block" and group.get("floor_calibrated") is True
        add(BLOCK if (hard and required) else WARN, "原生音画声线一致性", f"native_voice:{label}",
            f"原生音画声纹机检「{label}」{'实测音色硬漂' if hard else '出现漂移信号'}"
            f"（severity={sev}, floor={group.get('floor')}, calibrated={group.get('floor_calibrated')}）。"
            "核对同一角色跨镜/跨集是否换声；必要时回 video 重新生成 native_speech 或改配音先行。",
            return_to_stage="video")

def check_voice_conditioned_lipsync_policy(root: str, ep: str, storyboard: Dict[str, object]) -> None:
    """配音条件口型 (lipsync_condition_only) 校验：音轨必须丢弃原生，必须有 voice-first 轨。"""
    clips = storyboard.get("clips") or []
    lp_clips = [c for c in clips if isinstance(c, dict) and c.get("native_audio_policy") == "lipsync_condition_only"]
    if not lp_clips:
        return

    # lipsync_condition_only 模式下，模型音频只作口型参考，合成时必须丢弃
    policy = native_audio_policy(root)
    mode = native_audio_policy_mode(policy)
    if mode != NATIVE_AUDIO_DISCARD:
        add(BLOCK, "口型同步", os.path.join(root, "_设置.md"),
            f"检测到 {len(lp_clips)} 个 lipsync_condition_only 镜（后端音频参考口型），合成时必须「丢弃」模型原生音频，"
            f"否则会与主配音轨重叠。当前设置：视频原生音轨={policy}。")
    
    if not voice_track_exists(root, ep):
        add(BLOCK, "口型同步", os.path.join(root, "合成", ep, "配音"),
            f"检测到 {len(lp_clips)} 个配音条件口型镜，但未检测到主配音轨 (voice_zh.wav)；该模式依赖配音驱动口型，请先 n2d-voice。")

__all__ = [
    'check_voiceover_fingerprint',
    'check_voice_cross_episode',
    'check_native_voice_identity',
    'check_voice_conditioned_lipsync_policy',
]
