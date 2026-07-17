#!/usr/bin/env python3
"""gates/backend.py — 后端连通/能力刷新·弱后端·漂移风险·skill新鲜度·LoRA例外·生图AI策略族（budget_cap 因 monkeypatch load_thresholds 留 gate.py）

按证据族从 gate.py 拆出的 check_ 闸（增量3）。从 gate_core 取共享基座，避免与 gate.py 循环导入；
gate.py `from gates.backend import *` 回灌，run()/按名自省助手照常解析；成员经校验 call-graph-closed。
"""
import glob

from gate_core import *  # noqa: F401,F403
from gate_core import (
    _CORE_SCOPE_RE,
    _ce_episode_number,
    _event_asset_rel,
    _event_clip_id,
    _event_generation,
    _event_status_pass,
    _image_backend_supports_native_subject,
    _image_event_provider,
    _is_lora_sidechain_event,
    _load_production_events,
    _long_running_subjectless_severity,
    _lora_exception_scope_path,
    _lora_scope_clips,
    _production_events_path,
    _run_drift_risk_script,
    _validate_lora_exception_scope,
)

PREFERRED_IMAGE_BACKENDS = {"codex", "openai"}
IMAGE_BACKEND_OVERRIDE_REL = os.path.join("合规", "image_backend_override.json")


def _image_backend_override_allows(root: str, canonical: str) -> bool:
    path = os.path.join(root, IMAGE_BACKEND_OVERRIDE_REL)
    try:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception:
        return False
    if not isinstance(payload, dict) or payload.get("approved") is not True:
        return False
    scope = str(payload.get("scope") or payload.get("stage") or "image").lower()
    if "image" not in scope and "生图" not in scope:
        return False
    raw_backend = str(
        payload.get("backend")
        or payload.get("canonical")
        or payload.get("image_backend")
        or ""
    ).strip()
    if raw_backend == canonical:
        return True
    signed_canon, signed_kind = classify_image_backend(raw_backend)
    return signed_kind == "approved" and signed_canon == canonical


def _signed_image_disaster_failover(root: str, ep: str, current_canonical: str) -> Dict[str, Any]:
    """Validate the narrow Codex→fallback disaster-handoff exception.

    A generic backend override only authorizes spend on a non-preferred
    backend; it must not silently legalize mixed episode output.  This helper
    additionally requires the one-way failover policy and a production-ledger
    handoff event, then rejects any successful bounce back to the old backend.
    """
    path = os.path.join(root, IMAGE_BACKEND_OVERRIDE_REL)
    try:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception:
        return {"active": False, "reason": "missing_or_invalid_override"}
    if not isinstance(payload, dict) or payload.get("approved") is not True:
        return {"active": False, "reason": "override_not_approved"}
    policy = payload.get("failover_policy") if isinstance(payload.get("failover_policy"), Mapping) else {}
    if str(policy.get("direction") or "").strip().lower() != "codex_to_dreamina_once":
        return {"active": False, "reason": "not_one_way_codex_dreamina"}
    if policy.get("no_backend_bounce") is not True:
        return {"active": False, "reason": "no_backend_bounce_not_locked"}
    signed_raw = str(payload.get("backend") or payload.get("canonical") or "").strip()
    signed_canon, signed_kind = classify_image_backend(signed_raw)
    if signed_kind != "approved" or signed_canon != current_canonical or current_canonical != "dreamina":
        return {"active": False, "reason": "signed_backend_not_current_dreamina"}

    events = _load_production_events(root)
    handoff_idx = 0
    trigger = ""
    for idx, event in enumerate(events, start=1):
        if str(event.get("episode") or "").strip() != ep or str(event.get("stage") or "").strip() != "image":
            continue
        meta = event.get("meta") if isinstance(event.get("meta"), Mapping) else {}
        from_canon = classify_image_backend(str(meta.get("handoff_from") or ""))[0]
        to_canon = classify_image_backend(str(meta.get("handoff_to") or ""))[0]
        event_trigger = str(meta.get("trigger") or "").strip().lower()
        if (
            from_canon == "codex"
            and to_canon == current_canonical
            and event_trigger in {"bounded_retries_exhausted", "codex_quota_or_credit_exhausted"}
            and str(meta.get("no_backend_bounce") or "").strip().lower() in {"true", "1", "yes"}
        ):
            handoff_idx = idx
            trigger = event_trigger
    if not handoff_idx:
        return {"active": False, "reason": "missing_handoff_event"}

    for idx, event in enumerate(events, start=1):
        if idx <= handoff_idx:
            continue
        if str(event.get("episode") or "").strip() != ep or str(event.get("stage") or "").strip() != "image":
            continue
        if str(event.get("event") or "").strip() not in {"generation", "redraw"}:
            continue
        generation = _event_generation(event)
        status = str(generation.get("status") or event.get("status") or "").strip().lower()
        if status == "fail":
            continue
        provider = _image_event_provider(event)
        if classify_image_backend(provider)[0] == "codex":
            return {"active": False, "reason": "backend_bounced_to_codex", "handoff_index": handoff_idx}
    return {
        "active": True,
        "from": "codex",
        "to": current_canonical,
        "trigger": trigger,
        "handoff_index": handoff_idx,
        "path": path,
    }


def _block_unsigned_non_preferred_backend(root: str, canonical: str, loc: str, raw: str) -> None:
    if not canonical or canonical in PREFERRED_IMAGE_BACKENDS:
        return
    if _image_backend_override_allows(root, canonical):
        return
    add(
        BLOCK,
        "生图AI一致性",
        loc,
        "全项目生图优先 Codex / GPT Image 2；非 Codex/OpenAI 图片后端必须先由用户明确签核，"
        f"并写 {IMAGE_BACKEND_OVERRIDE_REL} 后才能付费出图。当前：{raw}",
    )


def check_backend_reachable(root: str, ep: str) -> None:
    """付费出图前确认所选生图后端「能落 PNG」。

    SKILL.md 写了「确认能落 PNG 再开工」，但此前无确定性闸门兜底——后端不通（内网 502 /
    CLI 未登录 / 缺 API key）时照样进付费工位，要么白花钱碰壁，要么静默兜底换后端致漂移。
    探针口径走 adapter（image_backends），gate 不 hardcode 任何内网地址/CLI 细节：
      · down（探针确证不可达）→ BLOCK，且明确禁止静默兜底换后端；
      · unknown（无自动探针 / CLI 缺 / 已设 N2D_SKIP_BACKEND_PROBE）→ WARN，提示人工确认；
      · ok → 放行。
    """
    settings_loc = os.path.join(root, "_设置.md")
    setting = get_setting(root, "生图AI", "Codex").strip()
    status, detail = image_backends.probe_backend(setting)
    if status == "down":
        add(BLOCK, "生图后端连通性", settings_loc,
            f"生图后端「{setting}」探活不通：{detail}。出图是付费工位，不通就停——"
            "先修后端（验内网/重登 CLI/补 API key）再出图；禁止静默兜底换别的后端（会引入跨镜后端混用漂移）。",
            return_to_stage="image")
    elif status == "unknown":
        bypass = "（注意：N2D_SKIP_BACKEND_PROBE 已设置，探活被显式跳过）" \
            if os.environ.get("N2D_SKIP_BACKEND_PROBE") else ""
        add(WARN, "生图后端连通性", settings_loc,
            f"生图后端「{setting}」无法自动探活：{detail}{bypass}。出图前请人工确认它能落 PNG"
            "（如 curl 内网健康端点 / 确认即梦官方 CLI 已登录·会员有效 / 确认 API 额度），不通即停，勿静默兜底换后端。")

def check_video_backend_reachable(root: str, ep: str) -> None:
    """付费出视频前确认所选生视频后端「可达·能出片」（与图侧 check_backend_reachable 同口径）。

    出视频是付费工位；后端不通（内网 502 / 官方 CLI 未登录 / 缺凭据·会员·额度）时照样进工位 = 白花钱碰壁，
    或静默兜底换后端致跨镜后端混用漂移（C2 禁的「偷偷换路」，也会按错后端记错账）。探针走
    video_backend_adapter（canonical_backend + 健康端点 env），gate 不 hardcode 任何内网地址/CLI 细节：
      · down（探针确证不可达，如内网 502）→ BLOCK，且明确禁止静默兜底换后端；
      · unknown（无自动探针 / 渠道=人工 / 已设 N2D_SKIP_BACKEND_PROBE）→ WARN，提示人工确认；
      · ok → 放行。
    与既有 check_video_backend_api_refresh（只看「能力刷新证据」）互补：那条管「能力声明是否新」，
    这条管「后端此刻是否连得上」——付费前两道都要过。"""
    settings_loc = os.path.join(root, "_设置.md")
    channel = get_setting(root, "生视频渠道", "即梦/Dreamina").strip()
    status, detail = video_backend_adapter.probe_video_backend(channel)
    if status == "down":
        add(BLOCK, "生视频后端连通性", settings_loc,
            f"生视频后端「{channel}」探活不通：{detail}。出视频是付费工位，不通就停——"
            "先修后端（验内网健康端点 / 重登官方 CLI / 补 API key·会员·额度）再出视频；"
            "禁止静默兜底换别的后端（会引入跨镜后端混用漂移、记错账）。",
            return_to_stage="video_prompt")
    elif status == "unknown":
        bypass = "（注意：N2D_SKIP_BACKEND_PROBE 已设置，探活被显式跳过）" \
            if os.environ.get("N2D_SKIP_BACKEND_PROBE") else ""
        add(WARN, "生视频后端连通性", settings_loc,
            f"生视频后端「{channel}」无法自动探活：{detail}{bypass}。出视频前请人工确认它能出片"
            "（官方 CLI 已登录·会员有效 / API 额度可用 / 一次 dry-run），不通即停，勿静默兜底换后端。")

def check_long_running_weak_backend(root: str, ep: str) -> None:
    """image_preflight：长线剧用「无持久主体 ID」后端逐镜参考图派生时，核心/常驻角色必须有身份锁。

    跨集脸漂真因=单张定妆照只是板式、每镜重画脸逐集累积(见 n2d-image 与 references/模型矩阵.md)；
    production 到第3集仍无 native subject / face_embedding / LoRA 等执行层锁，不能只停留在 WARN；
    demo/探索只提示升档，保留快速小样速度。"""
    setting = get_setting(root, "生图AI", "Codex").strip()
    canon, _kind = classify_image_backend(setting)
    try:
        cur = _ce_episode_number(ep) or 0
    except Exception:
        cur = 0
    ep_count = len({os.path.basename(os.path.dirname(p))
                    for p in glob.glob(os.path.join(root, "脚本", "*", "storyboard.json"))})
    if not long_running_weak_backend_advice(canon or "", cur, ep_count):
        return
    sev = _long_running_subjectless_severity(root, ep)
    suffix = (
        "production 长线第3集起这不是建议项，会跨集累积脸漂；"
        if sev == BLOCK else
        "demo/探索阶段先按 WARN 暴露，不阻断快速小样；进入 production 或批量出图前必须补锁；"
    )
    missing, has_core = core_forms_without_image_identity_lock(root, canon or setting)
    if missing:
        shown = "、".join(missing[:8]) + ("…" if len(missing) > 8 else "")
        lock_notes = identity_lock_gap_notes(root, canon or setting)
        lock_note = ("当前执行锁状态：" + "；".join(lock_notes[:8]) + "。") if lock_notes else ""
        add(
            sev,
            "生图AI一致性",
            f"生图AI={setting}",
            f"长线剧（{ep}）仍用无持久主体后端（{canon or setting}）逐镜参考图派生，且核心/常驻角色缺 native subject / Face Lock / face_embedding / LoRA / 已登记 image2image 强参考链：{shown}。"
            f"{lock_note}"
            f"{suffix}请先注册原生主体、启用 face_embedding，完成可用于当前后端的 LoRA，或登记 image2image_reference_chain（真实图片入参 + reference_manifest + full QC）后再付费出图。"
            + IMAGE_IDENTITY_LOCK_RECOMMENDATION,
            return_to_stage="image",
        )
        return
    if not has_core:
        add(sev, "生图AI一致性", f"生图AI={setting}",
            f"长线剧（{ep}）仍用无持久主体后端（{canon or setting}）逐镜参考图派生，但 registry 未标出核心/常驻角色；"
            "请先把核心/常驻角色 scope/tier 写入 identity_registry，并为这些角色注册 native subject / Face Lock / face_embedding / LoRA，或登记 image2image_reference_chain 强参考链；"
            f"否则无法判断谁必须升档，长距离复现会把脸漂累积到后续集。{suffix}"
            + IMAGE_IDENTITY_LOCK_RECOMMENDATION,
            return_to_stage="image")

def check_drift_risk_advisories(root: str, ep: str) -> None:
    """image_preflight 专属：自动跑 face/asset drift_risk 预案，把 high/medium 内联进同一份预检报告。

    动机（E1·让 agent 跑得更顺）：脸漂/物料漂移预案此前是两个独立、要 agent **记得手动跑**的脚本，
    输出又各自落单独 JSON——agent 跑一次 gate 拿 block、还得另记两条 advisory。这里把它们折进
    image_preflight：一个入口 = 阻断 + 预案一次拿齐。advisory only（WARN/INFO），绝不阻断出图。"""
    for script_name, human in (("face_drift_risk.py", "脸漂"), ("asset_drift_risk.py", "物料漂移")):
        report = _run_drift_risk_script(script_name, root, ep)
        if report is None:
            add(INFO, "漂移预案", ep,
                f"{human}风险预案未能自动生成（缺 storyboard/registry 或脚本不可用）——"
                f"出图前可手动跑 skills/n2d-image/scripts/{script_name} 看预案。")
            continue
        rows = drift_advisory_findings(report)
        if not rows:
            add(INFO, "漂移预案", ep, f"{human}风险预案：本集无 high/医 medium 角色/物料（🟢 全低危）。")
            continue
        for sev, dim, loc, msg in rows:
            # 实测漂移=真 BLOCK（return_to_stage=image，须先处置再出图）；预测档仍 advisory
            if sev == BLOCK:
                add(sev, dim, loc, msg, return_to_stage="image")
            else:
                add(sev, dim, loc, msg, advisory=True)

def check_drift_report_freshness(root: str, ep: str) -> None:
    """measured-drift BLOCK 环的新鲜度闸：报告缺/陈旧时不让其静默退化成 advisory。

    动机（堵静默退化洞）：跨集脸漂的实测 BLOCK 依赖 生产数据/identity_drift_report.json，而该报告只由
    `identity.py --write` 手动生成、gate 只读不刷（drift_advisory_findings / measured_drift_block）。漏跑/陈旧 →
    上一集已漂的脸蒙混过本集。这里把『历史已出图集是否都被报告覆盖』钉成闸：present-but-stale=BLOCK
    （最危险，留 N2D_ALLOW_DEGRADED_QC=1 逃生口·留痕自负），缺失/未实测=WARN（不硬拦无 insightface 的默认产线）。"""
    cur = _ce_episode_number(ep) or 0
    prior_imaged = [e for e in imaged_episodes(root)
                    if 0 < (_ce_episode_number(e) or 0) < cur] if cur else []
    report = load_json(os.path.join(root, "生产数据", "identity_drift_report.json"))
    if not isinstance(report, dict):
        report = {}
    # 内容级新鲜度：算每个历史出图集当前 PNG 集合指纹，与报告记录的比对（图重出过=报告陈旧）。
    current_fps = {e: episode_png_fingerprint(root, e) for e in prior_imaged}
    for sev, msg in drift_report_freshness(prior_imaged, report, current_fps):
        if sev == BLOCK:
            if os.environ.get("N2D_ALLOW_DEGRADED_QC") == "1":
                add(WARN, "脸漂报告新鲜度", ep, msg + "（已显式 N2D_ALLOW_DEGRADED_QC 放行·自负其责）")
                note_degraded_qc_waiver("脸漂报告新鲜度", ep, str(ep), "脸漂实测报告缺/陈旧被降级放行")
            else:
                add(BLOCK, "脸漂报告新鲜度", ep, msg, return_to_stage="image")
        else:
            add(sev, "脸漂报告新鲜度", ep, msg, advisory=True)

def check_skill_freshness(root: str, ep: str, stage: str) -> None:
    """花钱出图/出视频**前**的「物料新鲜度」预检：自上次基线后，生产本阶段输入物料的 skill 改了吗？

    动机（本次审计闭合的缺口）：skill 漂移检测（git-free SHA256 内容快照基线，存于
    `生产数据/skill_update_snapshot.json`）此前**只在用户手动跑 `n2d-update` 时**才发生；而真正花钱的
    `image_preflight`/`video_preflight` 预检从不查它——于是 skill 升级后，旧物料可能已过期，却照样烧钱
    生成。这里把同一套检测下沉到预检：命中生产输入物料漂移即 **BLOCK** 并路由回 n2d-update/repair_preflight
    评估精确重制范围；横切/QC/gate-only 改动仍只 INFO。只读不写（不在 gate 里落基线，避免副作用）。

    判定为 skill 粒度的粗判（偏向"花钱前先去查"），精确的文件→阶段/artifact-vs-gate-only 裁决由
    `n2d-update/update_plan.py` 给出。二者共享同一份观测白名单常量（skill_freshness 单一来源）。
    """
    if skill_freshness is None:
        return
    until_key = skill_freshness.until_key_for_gate_stage(stage)
    if not until_key:
        return
    try:
        res = skill_freshness.assess(root, until_key)
    except Exception as exc:  # 体检失败不影响主预检
        add(INFO, "物料新鲜度", ep,
            f"skill 漂移体检不可用（不影响其它闸）：{type(exc).__name__}: {exc}", advisory=True)
        return
    status = res.get("status")
    record_cmd = f'python3 skills/n2d-update/scripts/update_plan.py record "{root}" {ep}'
    check_cmd = f'python3 skills/n2d-update/scripts/update_plan.py check "{root}" {ep}'
    if status == "no_baseline":
        # 无基线 = 无可比对对象：保持静默，不在每个无基线作品的预检里反复 nag。
        # 开启漂移检测的方式（先跑一次 `n2d-update record`）记在 n2d-update/SKILL.md，不污染 gate 输出。
        del record_cmd
        return
    if status == "no_baseline_legacy":
        add(INFO, "物料新鲜度", ep,
            "skill 基线为旧版格式（无内容快照·不可比对）：请重新 "
            f"`{record_cmd}` 建立内容基线，恢复物料过期检测。", advisory=True)
        return
    if status != "drift":
        return  # fresh：无声通过
    bootstrap_note = (
        "（注：当前基线为自动建立的临时 bootstrap，看不到更早 skill 版本的差异；"
        "确认现有产物可接受后请 `record` 固化）" if res.get("bootstrap") else ""
    )
    material = res.get("material_skills") or []
    changed = res.get("changed_skills") or []
    if material:
        repair_cmd = (
            f'python3 skills/n2d/scripts/repair_preflight.py "{root}" {ep} '
            f"--stage {until_key} --write-missing"
        )
        add(BLOCK, "物料新鲜度", ep,
            f"前期物料可能已过期：{', '.join(material)} 自上次 skill 基线后有改动，"
            f"可能影响本阶段（{until_key}）的输入物料。出图/出视频是花钱且不可逆的步骤——"
            f"先跑 `{check_cmd}` 评估哪些物料需重制；统一修复/预检入口：`{repair_cmd}`。"
            f"完成重制或确认接受现状后再 `{record_cmd}` 固化新基线。{bootstrap_note}",
            return_to_stage="update_plan",
            recovery_command=repair_cmd,
            advisory=False,
            evidence_family="freshness")
    elif changed:
        add(INFO, "物料新鲜度", ep,
            f"skill 有改动但仅限横切/QC/gate 层（{', '.join(changed)}），不影响本阶段输入物料；"
            f"如需可跑 `{check_cmd}` 复核。{bootstrap_note}", advisory=True)

def check_image_ai_policy(root: str, ep: str) -> None:
    """`生图模型` 是生成轴，`生图AI/生图渠道` 是访问入口。

    全项目图片阶段默认 Codex/OpenAI；非 Codex/OpenAI 官方后端只作用户签核例外。本检查：
      - Codex/OpenAI：放行；
      - 非 Codex/OpenAI 官方白名单后端：缺 `<作品根>/合规/image_backend_override.json` 时 BLOCK；
      - 未授权出图路径（同视频AI 含糊口径、第三方逆向 CLI/web 自动化）：BLOCK（安全 invariant）；
      - 未知后端：WARN（提示先确认是官方 API）；
      - 同项目/同集出现 ≥2 个不同官方后端：BLOCK（混用）。
    合规闸门（角色/声音克隆授权）由 check_compliance_manifest 负责，与本检查无关。
    """
    settings_loc = os.path.join(root, "_设置.md")
    used: set = set()  # 在用的官方后端 canonical 集合，用于混用检测

    setting = get_setting(root, "生图AI", "Codex").strip()
    canon, kind = classify_image_backend(setting)
    disaster_failover = _signed_image_disaster_failover(root, ep, canon if kind == "approved" else "")
    if kind == "forbidden":
        add(
            BLOCK,
            "生图AI一致性",
            settings_loc,
            f"生图AI「{setting}」是未授权/含糊出图路径（同视频AI、第三方逆向 CLI 或 web 自动化），违反安全闸门，永不放行。"
            "请显式改用官方生图模型/渠道：Codex/OpenAI、Dreamina/即梦官方 CLI、Seedream（官方 API）、可灵主体库、Nano Banana。Sora Cameo 仅旧项目/manual。",
        )
    elif kind == "unknown":
        add(
            WARN,
            "生图AI一致性",
            settings_loc,
            f"生图AI「{setting}」不在已知官方后端清单内。请先确认它是【官方 API】再用；"
            "已知官方后端：" + "、".join(cfg["label"] for cfg in APPROVED_IMAGE_BACKENDS.values()) + "。",
        )
    else:
        used.add(canon)
        _block_unsigned_non_preferred_backend(root, canon, settings_loc, setting)

    prompt_paths = [
        os.path.join(root, "出图", ep, "prompt", "00_总览.md"),
        os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md"),
        shared_asset_path(root, "prompt", "角色定妆.md"),
        shared_asset_path(root, "prompt", "场景定妆.md"),
        shared_asset_path(root, "prompt", "道具定妆.md"),
        shared_asset_path(root, "prompt", "法宝定妆.md"),
        shared_asset_path(root, "prompt", "特效定妆.md"),
    ]
    backend_decl_re = re.compile(
        r"(?:生图AI|图像后端|图片后端|image backend|image model)\s*[:：]\s*([^\n\r`|]+)",
        re.I,
    )
    forbidden_call_re = re.compile(r"(同视频AI|非官方|第三方|逆向|web\s*自动化).{0,24}(?:生图|出图|image generation|text2image|image2image)", re.I)
    for path in prompt_paths:
        if not os.path.isfile(path):
            continue
        text = open(path, encoding="utf-8").read()
        if forbidden_call_re.search(text):
            add(
                BLOCK,
                "生图AI一致性",
                path,
                "prompt 出现同视频AI/非官方/第三方逆向/web 自动化出图口径；属未授权或含糊出图路径，必须移除。官方 Dreamina CLI 请显式写 “Dreamina/即梦”。",
            )
        for m in backend_decl_re.finditer(text):
            pc, pk = classify_image_backend(m.group(1))
            if pk == "forbidden":
                add(
                    BLOCK,
                "生图AI一致性",
                path,
                f"prompt 标注未授权/含糊出图后端「{m.group(1).strip()}」；请改用官方生图模型/渠道（Codex/OpenAI/Dreamina/Seedream/可灵/Nano Banana；Sora 仅旧项目/manual）。",
                )
            elif pk == "approved":
                used.add(pc)
                _block_unsigned_non_preferred_backend(root, pc, path, m.group(1).strip())

    missing_event_providers: List[str] = []
    event_path = _production_events_path(root)
    latest_success_events: Dict[str, Tuple[int, Dict[str, Any]]] = {}
    unkeyed_success_events: List[Tuple[int, Dict[str, Any], str]] = []
    for idx, event in enumerate(_load_production_events(root), start=1):
        if str(event.get("episode") or "").strip() != ep:
            continue
        if str(event.get("stage") or "").strip() != "image":
            continue
        if str(event.get("event") or "").strip() not in {"generation", "redraw"}:
            continue
        generation = _event_generation(event)
        status = str(generation.get("status") or event.get("status") or "").strip().lower()
        if status == "fail":
            continue
        asset = _event_asset_rel(root, event) or str(generation.get("asset") or "")
        if asset:
            latest_success_events[asset] = (idx, event)
        else:
            unkeyed_success_events.append((idx, event, asset))

    # 只以同一 asset 的最新成功落档事件判定后端混用。旧的 pass 会被后续 redraw/generation
    # 覆盖，否则一次全量迁移后端会被历史账本误判成“跨镜混用”。
    event_checks = sorted(
        [(idx, event, asset) for asset, (idx, event) in latest_success_events.items()] + unkeyed_success_events,
        key=lambda item: item[0],
    )
    for idx, event, asset in event_checks:
        provider = _image_event_provider(event)
        if not provider:
            missing_event_providers.append(f"line {idx}: {asset or '(no asset)'}")
            continue
        if _is_lora_sidechain_event(provider, event):
            continue
        pc, pk = classify_image_backend(provider)
        if pk == "forbidden":
            add(
                BLOCK,
                "生图AI一致性",
                event_path,
                f"production_events 第{idx}行记录了未授权/含糊出图 provider「{provider}」；真实落档事件不得使用第三方逆向/web 自动化/同视频AI 口径。",
            )
        elif pk == "unknown":
            add(
                WARN,
                "生图AI一致性",
                event_path,
                f"production_events 第{idx}行 provider「{provider}」不在官方后端清单内；请确认其为官方 API/CLI，并补充后端适配。",
            )
        else:
            used.add(pc)
            _block_unsigned_non_preferred_backend(root, pc, event_path, provider)
    if missing_event_providers:
        add(
            BLOCK,
            "生图AI一致性",
            event_path,
            "成功/待验收的 image generation/redraw 事件缺 provider，无法证明本集未混用后端："
            + "；".join(missing_event_providers[:8])
            + ("；..." if len(missing_event_providers) > 8 else "")
            + "。请用 dashboard record --provider 补录或重跑生成 adapter。",
        )

    failover_pair = {str(disaster_failover.get("from") or ""), str(disaster_failover.get("to") or "")}
    failover_pair.discard("")
    failover_mixing_allowed = bool(disaster_failover.get("active")) and used.issubset(failover_pair)
    if len(used) >= 2 and not failover_mixing_allowed:
        add(
            BLOCK,
            "生图AI一致性",
            settings_loc,
            f"同项目/同集混用多个生图模型/渠道（{'、'.join(sorted(used))}）；混用会让同角色脸型/服装/画风跨镜漂移。"
            "请把 _设置.md 与所有 prompt 统一到同一组生图模型/渠道后再出图。",
        )
    elif len(used) >= 2 and failover_mixing_allowed:
        add(
            INFO,
            "生图AI一致性",
            str(disaster_failover.get("path") or settings_loc),
            "已验证一次性 Codex→Dreamina 灾备切换：已验收旧图可保留，handoff 后未发现回弹 Codex；"
            "所有未生成/待重抽图片必须继续统一使用 Dreamina，并逐张执行 full image_qc + 实际像素目视。",
            advisory=True,
        )

    # 基线「验现实」reconcile（坑 D）：check_image_backend_baseline 只比对 _设置.md 声明 vs 锁定基线，
    # 都是声明；这里把**真实落档事件**实际用的后端 canonical（`used`，已去重到每 asset 最新成功）对账
    # 锁定基线 canonical。声明没改、却把整集悄悄换成另一个（单一·官方·不混用）后端 → 上面的混用闸和
    # 声明对账都抓不到，唯独真实事件能戳穿。两侧都过 classify_image_backend 归一，词表一致避免误报。
    baseline_status = image_backend_adapter.image_backend_baseline_status(root)
    baseline_sel = baseline_status.get("baseline") if isinstance(baseline_status.get("baseline"), Mapping) else {}
    baseline_canon = classify_image_backend(
        str((baseline_sel or {}).get("access") or (baseline_sel or {}).get("backend") or "")
    )[0]
    if baseline_canon:
        drifted = sorted(c for c in used if c and c != baseline_canon)
        old_failover_only = (
            bool(disaster_failover.get("active"))
            and baseline_canon == str(disaster_failover.get("to") or "")
            and set(drifted).issubset({str(disaster_failover.get("from") or "")})
        )
        if drifted and not old_failover_only:
            add(
                BLOCK,
                "生图后端基线",
                event_path,
                f"production_events 显示本集实际出图后端（{'、'.join(drifted)}）与项目锁定基线（{baseline_canon}）不一致——"
                "基线对账只比 _设置.md 声明，这里比**真实落档事件**：声明没改但实际换了后端=视觉 DNA 漂移、跨集脸/画风裂。"
                "请把生成统一回基线后端重出，或先跑 `n2d-update media` 形成重制计划 + `record-baseline --force` 更新基线。",
                return_to_stage="image",
            )
        elif drifted and old_failover_only:
            add(
                INFO,
                "生图后端基线",
                event_path,
                "锁定基线已更新为 Dreamina；账本中的 Codex 成功事件均早于已签 handoff，作为已验收历史图保留，"
                "不视为灾备后的后端回弹。",
                advisory=True,
            )

    # 主体库硬闸（一致性梯子第②档）：所选后端**支持原生角色主体/Character ID**（seedream/可灵等）
    # 而核心长线角色还停在 unregistered 时，付费出图前 BLOCK。注册一次按 ID 跨镜跨集引用，比每张重喂
    # 参考图更稳更省，是压住跨集脸漂的省钱前置。Codex/OpenAI 等无持久主体的后端不触发
    # （default_status=fallback_reference_group → 自动回退参考图派生，不打扰短线/无持久主体 ID 路线）。"不靠想起来"：
    # 靠 registry adapter 状态机检，不靠人脑记。
    if kind == "approved" and _image_backend_supports_native_subject(canon):
        reg = load_json(identity_registry_path(root))
        if isinstance(reg, dict):
            label = next(
                (cfg["label"] for cfg in APPROVED_IMAGE_BACKENDS.values() if cfg.get("canonical") == canon),
                canon,
            )
            pending: List[str] = []
            for char in reg.get("characters", []) or []:
                if not isinstance(char, dict):
                    continue
                if not _CORE_SCOPE_RE.search(str(char.get("scope") or "")):
                    continue  # 默认最小化：短线配角/单元妖不前置高档，只 nudge 核心长线角
                for form in char.get("forms", []) or []:
                    if not isinstance(form, dict):
                        continue
                    img = (form.get("identity_adapters") or {}).get("image") or {}
                    entry = img.get(canon)
                    status = entry.get("status") if isinstance(entry, dict) else entry
                    if status not in ("registered", "ready"):
                        pending.append(f"{char.get('id')}/{form.get('form')}")
            if pending:
                shown = "、".join(pending[:8]) + ("…" if len(pending) > 8 else "")
                add(
                    BLOCK,
                    "原生主体注册",
                    settings_loc,
                    f"生图AI「{label}」支持原生角色主体/Character ID（一致性梯子第②档），但核心长线角色尚未注册："
                    f"{shown}。注册一次后按 ID 跨镜跨集引用，比每张重喂参考图更稳更省，能压住跨集脸漂。"
                    f"请在该后端控制台用已过自检的定妆三视图注册主体，把返回的 ID/句柄写进 identity_registry "
                    f"对应 forms[].identity_adapters.image.{canon}（status→registered + id/handle），再跑 "
                    "`python3 skills/n2d-identity/scripts/identity.py <作品根> --write` 刷新 adapter matrix。"
                    "（Codex/OpenAI 等无持久主体的后端不触发本硬闸，自动回退参考图派生；"
                    "核心长线角色若选择支持主体库的后端，则先注册再付费出图）",
                )

def _project_has_image_outputs(root: str) -> bool:
    patterns = (
        os.path.join(root, "出图", "*", "图片", "*.png"),
        os.path.join(root, "出图", "*", "候选", "*", "*.png"),
    )
    return any(glob.glob(pattern) for pattern in patterns)

def check_image_backend_baseline(root: str, ep: str, stage: str = "image_preflight") -> None:
    """生产项目必须锁定单一生图后端基线；换后端前先做重制计划。

    角色一致性不是逐镜 prompt 能兜住的，整部剧的生图模型/渠道就是视觉 DNA 的一部分。
    baseline 缺失时，production 不允许进入付费出图；baseline 漂移且已有图产物时，必须先跑
    n2d-update 形成已出集重制/保留计划，不能静默继续用新后端生成。
    """
    status = image_backend_adapter.image_backend_baseline_status(root)
    profile = consistency_release_profile(root, stage, ep)
    path = status.get("path") or os.path.join(root, "生产数据", "image_backend_baseline.json")
    record_cmd = f'python3 skills/n2d/_lib/image_backend_adapter.py record-baseline "{root}"'
    if status.get("status") == "missing":
        sev = BLOCK if profile == "production" else WARN
        add(
            sev,
            "生图后端基线",
            str(path),
            f"本项目尚未锁定生图后端基线。production 必须每部剧固定一组生图模型/渠道；"
            f"先确认当前 _设置.md 的 `生图AI/生图模型` 后执行 `{record_cmd}`，再进入付费出图。",
            return_to_stage="image",
        )
        return
    if status.get("status") == "invalid":
        add(BLOCK, "生图后端基线", str(path),
            f"生图后端基线不可用：{status.get('message') or 'invalid'}；请修复或重新 record-baseline。",
            return_to_stage="image")
        return
    if status.get("status") != "changed":
        return
    fields = "、".join(str(v) for v in (status.get("changed_fields") or []))
    baseline = status.get("baseline") if isinstance(status.get("baseline"), Mapping) else {}
    current = status.get("current") if isinstance(status.get("current"), Mapping) else {}
    produced = _project_has_image_outputs(root)
    sev = BLOCK if (profile == "production" or produced) else WARN
    tail = (
        "项目已有出图/候选 PNG；换后端会把角色脸、服装材质、场景先验一起换掉。"
        "请先用 n2d-update media 生成已出集/已出镜重制计划，确认哪些集要随新基线重出，"
        "再用 `record-baseline --force` 更新基线。"
        if produced else
        "当前尚未检测到出图产物；若这是有意切换，请 `record-baseline --force` 更新基线后再跑。"
    )
    add(
        sev,
        "生图后端基线",
        str(path),
        f"当前生图后端选择与项目基线不一致（字段：{fields or 'unknown'}；"
        f"baseline={baseline.get('backend')}/{baseline.get('image_model')}，"
        f"current={current.get('backend')}/{current.get('image_model')}）。{tail}",
        return_to_stage="image",
    )

def _keyshot_plan_path(root: str, ep: str) -> str:
    return os.path.join(root, "生产数据", f"keyshot_candidate_plan_{ep}.json")

def _load_or_preview_keyshot_plan(root: str, ep: str) -> Tuple[Optional[Dict[str, Any]], str, bool]:
    path = _keyshot_plan_path(root, ep)
    data = load_json(path)
    if isinstance(data, dict):
        return data, path, True
    script = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "n2d-image", "scripts", "keyshot_candidates.py"))
    if not os.path.isfile(script):
        return None, path, False
    try:
        proc = subprocess.run(
            [sys.executable, script, root, ep, "--json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=120,
        )
        payload = json.loads(proc.stdout or "{}")
        return (payload if isinstance(payload, dict) else None), path, False
    except Exception:
        return None, path, False

def _candidate_selection_path(root: str, ep: str) -> str:
    return os.path.join(root, "生产数据", f"candidate_selection_{ep}.json")

def _candidate_pngs(root: str, ep: str, clip: str) -> List[str]:
    return sorted(glob.glob(os.path.join(root, "出图", ep, "候选", clip, "*.png")))

def _candidate_pick_exists(root: str, ep: str, clip: str, picked: Mapping[str, object]) -> bool:
    """Verify that candidate_selection picked a real candidate image, not just a JSON token."""
    candidates: List[str] = []
    for key in ("path", "rel"):
        value = str(picked.get(key) or "").strip()
        if not value:
            continue
        if os.path.isabs(value):
            candidates.append(value)
        else:
            candidates.append(os.path.join(root, value))
            candidates.append(value)
    name = str(picked.get("candidate") or "").strip()
    if name:
        candidates.append(os.path.join(root, "出图", ep, "候选", clip, name))
        candidates.append(os.path.join(root, "出图", ep, "候选", clip, f"{name}.png"))
    return any(os.path.isfile(path) for path in candidates)

def check_keyshot_candidate_plan(root: str, ep: str, stage: str = "image_preflight") -> None:
    """production 关键镜默认 best-of-N：预检要有 K>=3 计划，出图后要有候选选片报告。"""
    profile = consistency_release_profile(root, stage, ep)
    plan, plan_path, persisted = _load_or_preview_keyshot_plan(root, ep)
    if not isinstance(plan, dict):
        return
    keyshots = [row for row in (plan.get("keyshots") or []) if isinstance(row, dict)]
    if not keyshots:
        return
    sev = BLOCK if profile == "production" else WARN
    write_cmd = f'python3 skills/n2d-image/scripts/keyshot_candidates.py "{root}" {ep} --write'
    if not persisted:
        add(
            sev,
            "关键镜候选",
            plan_path,
            f"检测到 {len(keyshots)} 个关键镜，但缺 keyshot_candidate_plan_{ep}.json。"
            f"production 关键镜不得一张不崩就过；先跑 `{write_cmd}` 固化 best-of-N 计划（普通关键镜 K>=3，"
            "动作/强情绪/多人同框自动升档，名场面封面级）。",
            return_to_stage="image",
        )
        if sev == BLOCK:
            return
    too_low = [
        f"{row.get('clip')}=K{row.get('candidate_count')}"
        for row in keyshots
        if int(row.get("candidate_count") or 0) < 3
    ]
    if too_low:
        add(
            sev,
            "关键镜候选",
            plan_path,
            "关键镜候选数低于 production 地板 K=3：" + "、".join(too_low[:8]) +
            "。修改/重跑 keyshot_candidates.py，不能让关键镜单抽落档。",
            return_to_stage="image",
        )
    if gate_family(stage) != "image" or stage == "image_preflight":
        return
    if profile != "production":
        return
    sel_path = _candidate_selection_path(root, ep)
    selection = load_json(sel_path)
    if not isinstance(selection, dict) or selection.get("kind") != "n2d_candidate_selection":
        add(
            BLOCK,
            "关键镜候选",
            sel_path,
            f"production 出图后缺 candidate_selection_{ep}.json；关键镜必须经过 best-of-N 选优而不是单张通过。"
            f"生成候选后跑 `python3 skills/n2d-image/scripts/candidate_select.py \"{root}\" {ep} --apply`。",
            return_to_stage="image",
        )
        return
    rows = {str(row.get("clip") or ""): row for row in (selection.get("rows") or []) if isinstance(row, dict)}
    missing: List[str] = []
    weak: List[str] = []
    reroll: List[str] = []
    missing_files: List[str] = []
    for row in keyshots:
        clip = str(row.get("clip") or "").strip()
        if not clip:
            continue
        picked = rows.get(clip)
        if not isinstance(picked, dict):
            missing.append(clip)
            continue
        if int(picked.get("candidate_count") or 0) < 3:
            weak.append(f"{clip}=K{picked.get('candidate_count')}")
        actual_pngs = _candidate_pngs(root, ep, clip)
        if len(actual_pngs) < 3:
            weak.append(f"{clip}=actual{len(actual_pngs)}")
        if picked.get("reroll_needed") or not picked.get("picked"):
            reroll.append(clip)
        elif not _candidate_pick_exists(root, ep, clip, picked.get("picked") or {}):
            missing_files.append(clip)
    if missing or weak or reroll or missing_files:
        bits = []
        if missing:
            bits.append("缺选片行 " + "、".join(missing[:8]))
        if weak:
            bits.append("候选不足 " + "、".join(weak[:8]))
        if reroll:
            bits.append("需重抽/未终选 " + "、".join(reroll[:8]))
        if missing_files:
            bits.append("终选候选文件不存在 " + "、".join(missing_files[:8]))
        add(
            BLOCK,
            "关键镜候选",
            sel_path,
            "关键镜 best-of-N 未闭环：" + "；".join(bits) +
            "。补候选、重跑 candidate_select.py，直到每个关键镜都有 K>=3 的终选或明确重抽处方。",
            return_to_stage="image",
        )

def check_lora_exception_scope(root: str, ep: str) -> None:
    """LoRA hero-shot exception must be explicit, narrow, and consumed by image gates.

    The normal image policy keeps one project image model/channel. A LoRA sidechain
    is allowed only for declared hero clips, with style bridge and QC requirements.
    """
    path = _lora_exception_scope_path(root, ep)
    scope = load_json(path)
    lora_events: List[Tuple[int, str, str]] = []
    for idx, event in enumerate(_load_production_events(root), start=1):
        if str(event.get("episode") or "").strip() != ep:
            continue
        if str(event.get("stage") or "").strip() != "image":
            continue
        if str(event.get("event") or "").strip() not in {"generation", "redraw"}:
            continue
        if not _event_status_pass(event):
            continue
        provider = _image_event_provider(event)
        if not _is_lora_sidechain_event(provider, event):
            continue
        asset = _event_asset_rel(root, event) or ""
        lora_events.append((idx, _event_clip_id(event, asset), asset))

    if not isinstance(scope, Mapping):
        if lora_events:
            shown = "；".join(
                f"line {idx}: {clip or '(clip缺失)'} {asset or ''}".strip()
                for idx, clip, asset in lora_events[:8]
            )
            add(
                BLOCK,
                "LoRA例外范围",
                path,
                "检测到 LoRA/ComfyUI/Flux/SDXL 等非项目主生图链路事件，但缺 "
                f"lora_exception_scope_{ep}.json；LoRA 只能用于明确 hero shots，不能伪装成整集换生图模型。"
                f"事件：{shown}",
                return_to_stage="image",
            )
        return

    blocks = _validate_lora_exception_scope(scope, ep)
    if blocks:
        add(
            BLOCK,
            "LoRA例外范围",
            path,
            "LoRA 例外范围 manifest 无效：" + "；".join(blocks) +
            "。必须声明 hero_shots_only、not_a_project_model_switch=true、clips、style_bridge 和 QC 要求。",
            return_to_stage="image",
        )
        return

    clips = _lora_scope_clips(scope)
    for idx, clip, asset in lora_events:
        if not clip or clip not in clips:
            add(
                BLOCK,
                "LoRA例外范围",
                f"{_production_events_path(root)}:line {idx}",
                f"LoRA sidechain 事件不在 lora_exception_scope_{ep}.json 的 hero shot clips 内："
                f"clip={clip or '缺失'} asset={asset or '缺失'}。"
                "要么补 scope 覆盖该 hero 镜，要么回项目主生图模型重出；不得把 LoRA 扩成隐式整集换模型。",
                return_to_stage="image",
            )

__all__ = [
    'check_backend_reachable',
    'check_video_backend_reachable',
    'check_long_running_weak_backend',
    'check_drift_risk_advisories',
    'check_drift_report_freshness',
    'check_skill_freshness',
    'check_image_ai_policy',
    'check_image_backend_baseline',
    'check_keyshot_candidate_plan',
    'check_lora_exception_scope',
]
