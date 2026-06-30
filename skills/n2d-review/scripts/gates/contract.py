#!/usr/bin/env python3
"""gates/contract.py — 视觉契约/分镜契约/跨集契约族：出图→出视频契约继承、storyboard 契约、跨集风格/角色定义契约

按证据族从 gate.py 拆出的 check_ 闸（增量3）。从 gate_core 取共享基座(add/常量/无状态助手)，
避免与 gate.py 循环导入。gate.py `from gates.contract import *` 回灌，run()/按名自省助手照常解析。
本族成员经校验为 call-graph-free（不调用其它 check_、也不被其它 check_ 调用），可独立迁移。
"""
from gate_core import *  # noqa: F401,F403  共享基座（add/findings/常量/无状态助手）
from gate_core import (  # import* 默认漏的下划线私有助手，按需显式带上（保守全量）
    _ce_core_scene_names,
    _ce_episode_number,
    _ce_overview_rel,
    _ce_prior_episode,
    _ce_scene_names,
    _check_midframe_generation_self_check,
    _clip_blob,
    _clip_is_closeup,
    _cross_episode_diff,
    _earliest_storyboard_ep,
    _field_is_missing,
    _first_template_keyword_hit,
    _possession_ledger_exists,
    _possession_mentions_core_asset,
    _reference_plan_application_status,
    _reference_plan_requirement,
    _director_plan_application_status,
    _route_allows_no_firstframe,
    _tone_base,
)

def check_contract_inheritance(root: str, ep: str) -> None:
    """像素层视觉契约 出图→出视频 继承 Diff，逐字段机检（光位锚/轴线视线漂移=BLOCK）。

    这是唯一能抓「人工誊抄改写轴线/光位」的机检；此前只存在于 inherit_contract.py 的裸命令、
    游离在 gate 退出码之外，导致 `dashboard.py gate --stage video` 通过 ≠ 契约继承成立。
    接进 video_preflight/video gate 后，视频侧改写/丢失像素层五字段会被硬拦，并消费 contract_inheritance 维度的回退坐标。
    """
    img_p = os.path.join(root, "出图", ep, "prompt", "00_总览.md")
    vid_p = os.path.join(root, "出视频", ep, "prompt", "00_总览.md")
    if not os.path.isfile(img_p):
        return  # 出图总览缺：上游问题，image_preflight/image gate 负责，不在此重复 BLOCK
    if not os.path.isfile(vid_p):
        return  # 视频总览缺：check_video_prompt_overview 已 BLOCK，避免重复报
    dim = CONSISTENCY_DIMENSIONS["contract_inheritance"]
    for r in diff_contracts(open(img_p, encoding="utf-8").read(), open(vid_p, encoding="utf-8").read()):
        if r["severity"] == "block":
            add(
                BLOCK,
                "契约继承",
                vid_p,
                f"视觉契约继承漂移[{r['field']}]：{r['note']}（出图侧原文：{r['image_text'] or '缺'}）",
                return_to_stage=dim["return_to_stage"],
                rerun_scope=dim["scope"],
                affected_artifacts=[f"出视频/{ep}/prompt/00_总览.md"],
            )
        elif r["status"] == "warn_drift":
            add(WARN, "契约继承", vid_p, f"视觉契约继承提示[{r['field']}]：{r['note']}（出图侧：{r['image_text'] or '缺'}）")

def check_asset_handoff_inheritance(root: str, ep: str) -> None:
    """逐镜物料约束 出图→出视频 继承（LOC/PROP/WEAPON/OUTFIT/VFX）：出图绑定的资产在出视频对应镜
    丢失=block/warn。视觉契约五字段管 episode 级光位/轴线，本检查补**逐镜**资产锚。

    此前只在 inherit_contract.py 裸命令里跑，游离在 gate 退出码之外——`dashboard.py gate --stage video`
    通过 ≠ 资产逐镜交接成立。接进 video gate 后，出图逐镜 prompt 绑的道具/特效在视频侧被丢会被收口。
    （身份交接逐镜锁则由 check_route_identity_readiness / 近景身份锁负责，不在此重复报。）
    """
    res = check_asset_handoff(root, ep)
    if not res.get("available"):
        return  # 上游逐镜 prompt 未到位：image/video 各自 stage gate 负责，不在此重复 BLOCK
    dim = CONSISTENCY_DIMENSIONS["contract_inheritance"]
    vid_rel = res.get("video_clips_file", os.path.join("出视频", ep, "prompt", "01_clips.md"))
    vid_p = os.path.join(root, vid_rel)
    for f in res.get("findings", []):
        if f.get("severity") == "block":
            add(
                BLOCK,
                "契约继承",
                vid_p,
                f"资产逐镜交接[{f.get('code')}]：{f.get('note')}",
                return_to_stage=dim["return_to_stage"],
                rerun_scope=dim["scope"],
                affected_artifacts=[vid_rel],
            )
        else:
            add(WARN, "契约继承", vid_p, f"资产逐镜交接[{f.get('code')}]：{f.get('note')}")

def check_reference_plan_applied(root: str, ep: str) -> None:
    """逐镜参考规划（reference_planner.py）→ 落实对账。

    跨集脸漂的处方在 `生产数据/reference_plan_第N集.json`（无持久主体 ID 后端按每镜变化量该补哪些参考/控制网/升档）。
    本检查在 image_preflight 把该 plan 的**行动项**surfaced 到付费闸门，提醒人审落进 01_分镜出图.md，
    避免"规划了却忘了补"。核心长线角色缺 plan 直接 BLOCK；普通角色镜缺 plan 只 WARN。
    与 image_qc 的 no_expression_lib_ref 互补：前者 pre-gen 选参考，后者 post-gen 验落档。
    """
    # 铁律（2026-06-27 用户裁决）：BLOCK 不随 profile 降级，demo 与 production 同标准。
    # 8f2e4c3f/c9d37df5 把它降成 production-only 已恢复（见 docs/skill-design-principles.md B11 + consistency_charter）。
    plan_path = os.path.join(root, "生产数据", f"reference_plan_{ep}.json")
    plan = load_json(plan_path)
    if not isinstance(plan, dict) or plan.get("kind") != "n2d_reference_plan":
        sev, reason = _reference_plan_requirement(root, ep)
        if sev:
            add(
                sev,
                "参考规划落实",
                plan_path,
                f"缺逐镜参考规划 reference_plan_{ep}.json（{reason}）。"
                f"{'付费出图前必须先跑' if sev == BLOCK else '建议先跑'} "
                f"`python3 skills/n2d-image/scripts/reference_planner.py <作品根> {ep}`，"
                "把每镜该喂的脸锚/表情/侧背/服装/场景/道具/控制网/升档建议落实到 "
                f"`出图/{ep}/prompt/01_分镜出图.md`；否则很容易只写了规则但实际未传对参考。",
                return_to_stage="image",
            )
        return
    summary = plan.get("summary") or {}
    actions = summary.get("action_required") or []
    if not actions:
        return
    applied_ok, applied_path, applied_reason = _reference_plan_application_status(root, ep, plan_path, len(actions))
    if applied_ok:
        add(
            INFO,
            "参考规划落实",
            applied_path,
            f"reference_plan_{ep}.json 的 {len(actions)} 条行动项已有结构化落实证据，且 plan/prompt SHA 与当前文件一致。",
            return_to_stage="image",
        )
        return
    weak = summary.get("weak_backend_large_delta_clips") or 0
    reg = summary.get("chars_need_native_registration") or []
    lora = summary.get("chars_need_lora") or []
    clips = sorted({str(a.get("clip")) for a in actions if a.get("clip")})
    shown = "、".join(clips[:8]) + ("…" if len(clips) > 8 else "")
    tail = ""
    if reg:
        tail += f" 待注册原生主体：{'、'.join(reg)}。"
    if lora:
        tail += f" 建议升 LoRA：{'、'.join(lora)}。"
    sev = BLOCK if (weak or reg or lora) else WARN  # 铁律：不随 profile 降级，demo 同标准
    add(
        sev,
        "参考规划落实",
        plan_path,
        f"逐镜参考规划有 {len(actions)} 条行动项未确认落实（无持久主体 ID 后端×大变化镜 {weak} 镜）："
        f"镜头 {shown}。请按 reference_plan_{ep}.md 把补拍/多样参考/控制网/升档落进 "
        f"出图/{ep}/prompt/01_分镜出图.md 后再付费出图；不能让参考规划停在侧车文件里。"
        f"若已完成人审落实，请写结构化 `{os.path.relpath(applied_path, root)}`（kind={REFERENCE_PLAN_APPLICATION_KIND}, "
        "accepted=true, reviewer, plan_sha256, prompt_path, prompt_sha256, applied_action_count, applied_evidence）。"
        f"当前落实证据状态：{applied_reason}。{tail}",
        return_to_stage="image",
    )

DIRECTOR_CAMERA_PLAN_KIND = "n2d_director_camera_plan"
_DIRECTOR_IMAGE_VOCAB = ("起幅", "运动余量", "构图防呆", "导演意图", "镜头/机位")
_DIRECTOR_VIDEO_VOCAB = ("起幅", "落幅", "镜头运动", "运动精修", "动态细节", "导演意图")


def _director_plan_peak_clips(clips: Sequence[Any]) -> List[str]:
    """director_camera_plan clips 里命中 KEY_SCENE_MARKERS（高潮/关键/钩子/反转/爆点）的镜 id。

    复用 gate 的 KEY_SCENE_MARKERS（与其它「核心场景→BLOCK」闸同源），不另立 PEAK 词表避免漂离。"""
    peak: List[str] = []
    for c in clips:
        if not isinstance(c, dict):
            continue
        blob = " ".join(str(c.get(k) or "") for k in ("clip_id", "rhythm", "template", "shot_size"))
        rec = c.get("recommended")
        if isinstance(rec, dict):
            blob += " " + str(rec.get("reason") or "")
        if any(str(m).lower() in blob.lower() for m in KEY_SCENE_MARKERS):
            peak.append(str(c.get("clip_id") or ""))
    return peak


def check_director_camera_plan_consumption(root: str, ep: str) -> None:
    """导演运镜计划（director_camera_plan.py）→ 落实对账（消费收据）。

    sidecar `生产数据/director_camera_plan_<ep>.json` 把每镜运镜意图拆成可注入的 image/video_prompt_injection；
    但此前靠「下游约定消费」无强制——规划好却没落进 prompt，那一镜就回平光摆拍/运动失焦
    （memory「规划好却没落成片」反模式·与 combat-punch 渲染教训同根）。本检查在出图/出视频付费前，
    核对 prompt 包是否出现导演运镜词汇证据：含高潮/关键镜(KEY_SCENE_MARKERS)且零证据=BLOCK，普通镜=WARN，
    有证据=INFO。sidecar 缺省（没跑 director_camera_plan）则不强制，与 check_reference_plan_applied 一致。

    两档收据（Tier A 精确优先·Tier B 烟雾回退）：
      - Tier A 逐镜精确：存在 SHA 绑定 plan+prompt 的结构化签收档 `director_camera_plan_applied_<ep>.json`
        （fresh）时，按 `scopes[].applied_clip_ids` 逐镜判落实——未签收镜里高潮/关键镜=BLOCK、普通镜=WARN。
        plan 或 prompt 变更→SHA 不符→该 scope 回退 Tier B，stale 签收不能蒙混放行。
      - Tier B 文档级烟雾：无签收档时核对整包是否出现导演运镜词汇（flat MD 无法可靠按 clip 切分），
        含高潮/关键镜且零词汇=BLOCK、普通镜=WARN，并提示落结构化签收档升精确归属。
    """
    sidecar = os.path.join(root, "生产数据", f"director_camera_plan_{ep}.json")
    plan = load_json(sidecar)
    if not isinstance(plan, dict) or plan.get("kind") != DIRECTOR_CAMERA_PLAN_KIND:
        return
    clips = plan.get("clips") or []
    if not clips:
        return
    all_ids = [str((c or {}).get("clip_id") or "") for c in clips if isinstance(c, dict)]
    peak_clips = [c for c in _director_plan_peak_clips(clips) if c]
    peak_set = set(peak_clips)
    # Tier A 逐镜精确签收（升级版）：SHA 绑定 plan + 每 scope prompt 的结构化 applied 档；fresh 才采信。
    application = _director_plan_application_status(root, ep, sidecar)

    def _precise_check(scope: str, prompt_path: str, stage: str, applied_ids: set) -> None:
        missing = [cid for cid in all_ids if cid and cid not in applied_ids]
        if not missing:
            add(INFO, "导演运镜落实", prompt_path,
                f"director_camera_plan_{ep}.json（{len(all_ids)} 镜）的{scope}运镜注入已逐镜签收落实"
                f"（director_camera_plan_applied_{ep}.json·SHA 绑定 plan+prompt）。",
                return_to_stage=stage)
            return
        peak_missing = [cid for cid in missing if cid in peak_set]
        sev = BLOCK if peak_missing else WARN
        shown = "、".join(missing[:8]) + ("…" if len(missing) > 8 else "")
        tail = (f"；其中高潮/关键镜 {'、'.join(peak_missing[:8])} → 付费前 BLOCK" if peak_missing else "（均普通镜 WARN）")
        add(sev, "导演运镜落实", prompt_path,
            f"逐镜签收档显示 {len(missing)} 镜的{scope}运镜注入未落实：{shown}{tail}。"
            f"请把 director_camera_plan_{ep}.md 对应镜的 {scope}_prompt_injection 抄进 prompt，"
            f"并把镜号补进 director_camera_plan_applied_{ep}.json 的 {scope} scope.applied_clip_ids（plan/prompt 变更需重签）。",
            return_to_stage=stage)

    def _smoke_check(prompt_path: str, prompt_rel: str, vocab: Sequence[str], scope: str, stage: str) -> None:
        try:
            text = open(prompt_path, encoding="utf-8").read()
        except OSError:
            return
        hits = [v for v in vocab if v in text]
        if hits:
            add(INFO, "导演运镜落实", prompt_path,
                f"director_camera_plan_{ep}.json（{len(all_ids)} 镜）的{scope}运镜词汇已现身 prompt 包"
                f"（命中 {len(hits)}/{len(vocab)}：{'、'.join(hits)}）——文档级已消费。"
                f"要逐镜精确归属请落 director_camera_plan_applied_{ep}.json（结构化签收）。",
                return_to_stage=stage)
            return
        sev = BLOCK if peak_clips else WARN
        shown = ("、".join(peak_clips[:8]) + ("…" if len(peak_clips) > 8 else "")) if peak_clips else ""
        tail = (f"；含高潮/关键镜 {shown} → 付费前 BLOCK" if peak_clips else "（普通镜 WARN）")
        add(sev, "导演运镜落实", prompt_path,
            f"导演运镜计划 director_camera_plan_{ep}.json 有 {len(all_ids)} 镜，但 {prompt_rel} 里找不到任何"
            f"{scope}运镜注入词汇（{'、'.join(vocab)}）——规划好却没落进 prompt，那些镜会回到平光摆拍/运动失焦。"
            f"请按 director_camera_plan_{ep}.md 把 {scope} prompt 注入（{scope}_prompt_injection）抄进 {prompt_rel}{tail}。"
            "（文档级烟雾收据·不做逐镜精确归属；逐镜精确请落结构化签收档。）",
            return_to_stage=stage)

    def _consume_check(prompt_rel: str, vocab: Sequence[str], scope: str) -> None:
        prompt_path = os.path.join(root, prompt_rel)
        stage = "image" if scope == "出图" else "video"
        if not os.path.isfile(prompt_path):
            return  # 该 prompt 包还没产出：上游阶段负责，不在此 BLOCK
        scope_app = application.get("scopes", {}).get(scope) if application.get("accepted") else None
        if isinstance(scope_app, dict) and scope_app.get("fresh"):
            _precise_check(scope, prompt_path, stage, scope_app.get("applied_ids") or set())  # Tier A 精确
            return
        _smoke_check(prompt_path, prompt_rel, vocab, scope, stage)  # Tier B 烟雾回退

    _consume_check(os.path.join("出图", ep, "prompt", "01_分镜出图.md"), _DIRECTOR_IMAGE_VOCAB, "出图")
    _consume_check(os.path.join("出视频", ep, "prompt", "01_clips.md"), _DIRECTOR_VIDEO_VOCAB, "出视频")


def check_storyboard_contract(root: str, ep: str, require_frame_assets: bool = True) -> Optional[dict]:
    data = load_storyboard(root, ep)
    if not data:
        return None
    clips = data["clips"]
    policy = data.get("policy")
    if not isinstance(policy, dict) or policy.get("tailframe_default") is not True:
        add(BLOCK, "故事板", storyboard_path(root, ep), "storyboard.json 缺 policy.tailframe_default=true；首尾双帧接力必须作为默认契约")
    prev_end = None
    routes_file = os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json")
    routes_map = {}
    if os.path.exists(routes_file):
        try:
            with open(routes_file, encoding="utf-8") as f:
                r_data = json.load(f)
                if isinstance(r_data.get("routes"), list):
                    for item in r_data["routes"]:
                        if not isinstance(item, Mapping):
                            continue
                        for key in (item.get("id"), item.get("clip_id")):
                            if key:
                                routes_map[str(key)] = item
        except Exception:
            pass

    for i, clip in enumerate(clips, 1):
        loc = f"{storyboard_path(root, ep)} clip#{i}"
        cid = clip.get("id", f"EP{data.get('episode', '01')}_CLIP{i:02d}")
        route = routes_map.get(str(cid)) or routes_map.get(f"Clip_{i:02d}") or {}
        allows_no_firstframe = _route_allows_no_firstframe(route)

        first_png = clip.get("firstframe_png")
        if require_frame_assets and not first_png and not allows_no_firstframe:
            add(BLOCK, "首帧", loc, "缺 firstframe_png")
        elif first_png and require_frame_assets:
            first_full = first_png if os.path.isabs(first_png) else os.path.join(root, first_png)
            if not os.path.exists(first_full):
                add(BLOCK, "首帧", first_full, "firstframe_png 不存在")
        cont = clip.get("continuity")
        if not isinstance(cont, dict):
            add(BLOCK, "故事板", loc, "缺 continuity 块")
            continue
        for key in ("start_state", "end_state", "transition", "need_endframe"):
            if key not in cont:
                add(BLOCK, "故事板", loc, f"continuity 缺字段：{key}")
        if prev_end and cont.get("start_state") != prev_end:
            add(BLOCK, "故事板", loc, "start_state 未原样继承上一 Clip 的 end_state")
        prev_end = cont.get("end_state")
        
        # --- 新增：工业级专项镜头增强模板契约验证 ---
        template_contract = clip.get("template_contract")
        if isinstance(template_contract, dict):
            if template_contract.get("pose_reference_required"):
                pose_path = clip.get("pose_image_path")
                if not pose_path:
                    add(BLOCK, "空间硬控", loc, f"该 {clip.get('template')} 模板具有 pose_reference_required: true 约束，必须配置 pose_image_path。")
                elif require_frame_assets:
                    pose_full = pose_path if os.path.isabs(pose_path) else os.path.join(root, pose_path)
                    if not os.path.exists(pose_full):
                        add(BLOCK, "空间硬控", pose_full, "配置的 pose_image_path 骨架/深度参考图文件不存在。")
            
            if template_contract.get("regional_construct_required"):
                # Ensure multiple subjects are defined properly or split_composite is flagged
                chars = clip.get("character_ids", [])
                if isinstance(chars, list) and len(chars) > 1:
                    exec_strategy = clip.get("execution_strategy", "")
                    if "regional_construct" not in exec_strategy and "split_composite" not in exec_strategy and "native_subject_slots" not in exec_strategy:
                        add(BLOCK, "分区合成", loc, f"该 {clip.get('template')} 模板具有 regional_construct_required: true 约束，检测到同框多角色，请在 execution_strategy 中明确保底合成策略以防串脸。")

            if template_contract.get("impact_frame_sync"):
                # Only check if midframe is properly prepared as an impact frame anchor
                anchors = cont.get("anchors", [])
                if "mid_impact" not in anchors and not cont.get("midframe"):
                    add(WARN, "击中帧验证", loc, f"该 {clip.get('template')} 模板包含 impact_frame_sync，但未在 continuity 规划中段光效爆发帧 (mid_impact / midframe)。")
        # ---------------------------------------------
        
        # 近景/特写/反打镜必须声明 expression_span——把「跨情绪近景首尾双帧」闸门从 opt-in 收成强制。
        # 没标 span 的大表情近景正是脸被表情带着重画的头号根因；不能靠作者记得打标签，否则双帧保护
        # 恰好在最该保护的未标镜上静默 no-op。远景/空镜由 _clip_is_closeup 收口、不误伤。
        if _clip_is_closeup(clip):
            span = cont.get("expression_span")
            if span in (None, ""):
                add(BLOCK, "表情一致性", loc,
                    "近景/特写/反打镜必须声明 continuity.expression_span（微/中/大）——跨情绪近景是脸随表情"
                    f"漂移的头号根因，不可 opt-in。按起止情绪（{cont.get('start_state')!r}→{cont.get('end_state')!r}）"
                    "补标；大表情(大)须配首尾双帧 need_endframe=true。",
                    return_to_stage="script_stage2")
            elif span not in EXPRESSION_SPAN_VALUES:
                add(BLOCK, "表情一致性", loc,
                    f"continuity.expression_span={span!r} 非法；必须是 {'/'.join(EXPRESSION_SPAN_VALUES)} 之一。",
                    return_to_stage="script_stage2")
        is_high_motion = str(clip.get("template") or "") in HIGH_MOTION_TEMPLATES
        # 高速运动镜首尾双帧不可豁免：快速运动靠首+尾两帧把两端钉死、模型只补中间，是控高动态一致性的
        # 关键手段（与表情近景的 need_endframe 不同关注点——那是脸随表情漂，这是肢体大动作漂）。这类镜
        # 不论是否末镜、都不接受 endframe_exempt_reason，是 i<len 默认闸 + 表情近景闸之外的第三条触发。
        if is_high_motion and cont.get("need_endframe") is not True:
            add(BLOCK, "尾帧", loc,
                f"高速运动镜(template={clip.get('template')})必须 need_endframe=true，且不可用 endframe_exempt_reason 豁免——"
                "快速运动靠首+尾帧钉住两端、模型只补中间是控一致性关键；末镜同样要求。",
                return_to_stage="script_stage2")
        elif i < len(clips) and cont.get("need_endframe") is not True:
            exempt = cont.get("endframe_exempt_reason")
            if not exempt:
                add(BLOCK, "尾帧", loc, "非最终 Clip 默认必须 need_endframe=true；若豁免需填写 endframe_exempt_reason")
            elif len(str(exempt).strip()) < ENDFRAME_EXEMPT_REASON_MIN_CHARS:
                add(BLOCK, "尾帧", loc,
                    f"endframe_exempt_reason 过短（{str(exempt).strip()!r}）——豁免首尾双帧必须写明实质理由"
                    "（如「极短镜<3s 无表情变化」），不接受占位/单字。")
        if cont.get("need_endframe") is True and require_frame_assets:
            end_png = cont.get("endframe_png")
            if not end_png:
                add(BLOCK, "尾帧", loc, "need_endframe=true 但未填写 endframe_png")
            else:
                full = end_png if os.path.isabs(end_png) else os.path.join(root, end_png)
                if not os.path.exists(full):
                    add(BLOCK, "尾帧", full, "need_endframe=true 但尾帧 PNG 不存在")
        # 中段锚帧：声明了 midframe/anchors 就必须是完整可执行契约。
        # 执行成本由后端能力决定（native multiframe / split relay / qc reference），但锚帧 PNG、
        # 时间点和理由缺一不放行，避免生成了 `_mid` 却在视频阶段被静默忽略。
        # midframe = 单锚帧手写糖（_mid）；anchors = 通用 N 锚帧链（_a1.._aN，anchor_planner 写）。
        mid = cont.get("midframe")
        anchors = cont.get("anchors")
        # 缺中段锚帧的 severity 按"路由后端能否真正消费中帧"分级
        # （charter ENFORCEMENT_DECISIONS: three_frame_graduated_severity·2026-06-27，取代 44af5704 的
        # 对所有后端无条件 BLOCK）：
        #   · 后端能消费中帧（原生多帧/首尾拆段接力·backend_supports_three_plus_frames=True，如即梦智能
        #     多帧/可灵首尾档）→ BLOCK：缺中帧=成片直接退化。
        #   · 真 first-frame-only，或后端未选/未知（中帧消费不了、仅作 QC/参考）→ WARN：中帧仍是默认应产
        #     图片资产（WARN≠豁免，anchor_planner 照样默认补齐），但「是否为不可消费的中帧花这笔出图钱」
        #     交作者按 cost 决定，不硬拦无谓花钱。SOTA(2026)：原生 3 关键帧极罕见（仅即梦智能多帧/Pika）。
        # severity **纯按后端能力**，不看 policy.midframe_default——后者是 anchor_planner 默认流程写的
        # "中帧已规划"标记（正常流程恒 true），不是"在弱后端也强制 BLOCK"的作者意图；用它当闸会让 WARN
        # 路径在正常流程里永不触发（回退成 44af5704 的一刀切）。
        if mid is None and anchors is None and not cont.get("midframe_exempt_reason"):
            mid_consumable = backend_supports_three_plus_frames((policy or {}).get("video_backend"))
            production = consistency_release_profile(root, "video_preflight", ep) == "production"
            production_action_block = production and is_high_motion
            sev = BLOCK if (mid_consumable or production_action_block) else WARN
            backend_note = (
                "路由后端可原生多帧/首尾拆段接力消费中帧，缺中帧=成片退化，必须补"
                if mid_consumable else
                "production 高运动镜必须补中段锚帧/锚点；动作镜没有中段姿态锚，肢体、受击点和道具轨迹会跨帧漂移"
                if production_action_block else
                "路由后端 first-frame-only 或未选定，中帧此时消费不了、仅作 QC/参考——"
                "是否为此出图由作者按 cost 决定（WARN 不豁免：中帧仍是默认图片资产）"
            )
            add(sev, "中段锚帧", loc,
                "三帧契约（首帧+中段锚帧+尾帧）：每镜应声明 continuity.midframe/anchors，"
                "或写 midframe_exempt_reason（极短镜<3s豁免）；"
                f"跑 anchor_planner.py --default-midframe --write 自动补齐。{backend_note}。")
        if mid is not None and anchors is not None:
            add(BLOCK, "中段锚帧", loc, "continuity.midframe 与 continuity.anchors 不能同时声明（语义歧义）；单锚帧用 midframe 或一项 anchors，二选一")
            continue
        if mid is not None:
            if not isinstance(mid, dict):
                add(BLOCK, "中段锚帧", loc, "continuity.midframe 必须是 object（midframe_png/split_at_sec/reason）")
                continue
            anchors = [{**mid, "_fields": ("midframe_png", "split_at_sec", "reason")}]
        if anchors is not None:
            if not isinstance(anchors, list) or not anchors:
                add(BLOCK, "中段锚帧", loc, "continuity.anchors 必须是非空 list（每项 anchor_png/at_sec/reason）")
                continue
            duration = clip.get("duration")
            prev_at = 0.0
            for k, a in enumerate(anchors, 1):
                if not isinstance(a, dict):
                    add(BLOCK, "中段锚帧", loc, f"anchors[{k}] 必须是 object（anchor_png/at_sec/reason）")
                    continue
                png_key, at_key, reason_key = a.get("_fields", ("anchor_png", "at_sec", "reason"))
                for label, key in (("锚帧 PNG", png_key), ("锚点秒数", at_key), ("锚帧理由", reason_key)):
                    if a.get(key) in (None, ""):
                        add(BLOCK, "中段锚帧", loc, f"锚帧 {k} 缺字段：{key}（中段锚帧契约必须写明{label}；执行时会按后端能力走原生多帧、拆段接力或 QC/reference）")
                at = a.get(at_key)
                if at not in (None, ""):
                    if isinstance(at, bool) or not isinstance(at, (int, float)):
                        add(BLOCK, "中段锚帧", loc, f"锚帧 {k} 的 {at_key} 必须是数字：{at!r}")
                    else:
                        if isinstance(duration, (int, float)) and not (0 < at < duration):
                            add(BLOCK, "中段锚帧", loc, f"锚帧 {k} 的 {at_key}={at} 必须落在 (0, duration={duration}) 内，各段还须 ≥ 目标后端最短时长")
                        if at <= prev_at:
                            add(BLOCK, "中段锚帧", loc, f"锚帧 {k} 的 {at_key}={at} 必须严格递增（前一锚点 {prev_at}）")
                        prev_at = at if at > prev_at else prev_at
                png = a.get(png_key)
                if png and require_frame_assets:
                    full = png if os.path.isabs(png) else os.path.join(root, png)
                    if not os.path.exists(full):
                        add(BLOCK, "中段锚帧", full, f"声明了锚帧 {k} 但锚帧 PNG 不存在")
                    else:
                        _check_midframe_generation_self_check(root, ep, str(png), loc, k)
    return data

def check_storyboard_visual_contract(root: str, ep: str) -> None:
    """storyboard.json must seed the visual contract at the script stage.

    Axis/eyeline, scene light position, character-state progression and the
    shot-size ladder are director decisions made when the storyboard is cut.
    They must live in storyboard.json's `visual_contract` so n2d-image inherits
    them instead of re-inventing them — the single upstream source of truth for
    everything later baked into first-frame pixels.
    """
    p = storyboard_path(root, ep)
    data = load_json(p)
    if not isinstance(data, dict):
        return  # storyboard 缺失/损坏由 check_storyboard_contract 报，避免重复
    vc = data.get("visual_contract")
    if not isinstance(vc, dict):
        add(BLOCK, "契约继承", p, "storyboard.json 缺 visual_contract 种子块；轴线/光位/状态/景别是分镜设计阶段的导演决策，须在此写死供出图继承（回 n2d-script 补 visual_contract）")
        return
    for key in VISUAL_CONTRACT_FIELDS:
        if key not in vc:
            add(BLOCK, "契约继承", p, f"storyboard.json visual_contract 缺字段：{key}")

def check_storyboard_style_contract(root: str, ep: str) -> None:
    """storyboard.json must seed the chosen base visual style contract.

    The style choice belongs in user settings/global_style, not in skill code.
    The contract turns that choice into repeatable constraints so image/video
    prompts inherit one source instead of appending generic style adjectives.
    """
    p = storyboard_path(root, ep)
    data = load_json(p)
    if not isinstance(data, dict):
        return
    sc = data.get("style_contract")
    legacy = False
    fields = STYLE_CONTRACT_FIELDS
    if not isinstance(sc, dict):
        sc = data.get("cinematic_contract")
        legacy = isinstance(sc, dict)
        fields = CINEMATIC_CONTRACT_FIELDS
    if not isinstance(sc, dict):
        add(BLOCK, "基础视觉风格契约", p, "storyboard.json 缺 style_contract 种子块；基础视觉风格必须来自 `_设置.md`/global_style，并在分镜设计阶段写成结构化契约供出图/出视频继承")
        return
    key_name = "cinematic_contract" if legacy else "style_contract"
    for key in fields:
        if key not in sc:
            add(BLOCK, "基础视觉风格契约", p, f"storyboard.json {key_name} 缺字段：{key}")
    # ⑥ 软校验：风格名 应与选择点「基础视觉风格」同源（项目选二次元、契约却写写实=矛盾，gate 只查在场会漏）
    if not legacy:
        chosen = str(get_setting(root, "基础视觉风格", "")).strip()
        name = str(sc.get("风格名", "")).strip()
        if chosen and name and chosen not in name and name not in chosen:
            add(WARN, "风格一致性", p,
                f"style_contract.风格名「{name}」与 _设置.md 基础视觉风格「{chosen}」不一致——风格真值应同源；核对是否选错风格或契约写偏")

def check_storyboard_possession_gate(root: str, ep: str) -> None:
    """Storyboard 前置 POS：检测到关键道具持有/交接时，要求账本前移到分镜层。"""
    data = load_json(storyboard_path(root, ep))
    if not isinstance(data, dict):
        return
    clips = data.get("clips") or data.get("shots") or []
    if not isinstance(clips, list):
        return
    mentions: List[str] = []
    transfer_mentions: List[str] = []
    for idx, clip in enumerate(clips, start=1):
        if not isinstance(clip, Mapping):
            continue
        text = json.dumps(clip, ensure_ascii=False)
        props = PROP_ID_ANY_RE.findall(text)
        if not props:
            continue
        if any(w.lower() in text.lower() for w in POSSESSION_WORDS + POSSESSION_TRANSFER_WORDS):
            label = str(clip.get("id") or clip.get("clip_id") or clip.get("label") or f"Clip_{idx:02d}")
            shown = f"{label}:{'/'.join(sorted(set(props)))}"
            mentions.append(shown)
            if any(w.lower() in text.lower() for w in POSSESSION_TRANSFER_WORDS):
                transfer_mentions.append(shown)
            elif _possession_mentions_core_asset(text, props):
                transfer_mentions.append(shown)
    if not mentions or _possession_ledger_exists(root, ep):
        return
    target = os.path.join(root, "生产数据", f"possession_ledger_{ep}.json")
    shown = "、".join((transfer_mentions or mentions)[:8]) + ("…" if len(transfer_mentions or mentions) > 8 else "")
    if transfer_mentions:
        add(
            BLOCK,
            "持有账本(POS)",
            storyboard_path(root, ep),
            f"storyboard 已出现核心道具/武器/证物/法宝的持有、交接、丢失或拾取（{shown}），但缺 possession_ledger；"
            f"请先在 {target} 记录 clip、asset、holder、action，避免道具跨镜瞬移。",
            return_to_stage="script_stage2",
        )
    else:
        add(
            WARN,
            "持有账本(POS)",
            storyboard_path(root, ep),
            f"storyboard 已出现关键道具持有关系（{shown}），建议前置 possession_ledger 到分镜 gate；跨镜持有、破损、丢失别只靠 prompt 文本记忆。",
            return_to_stage="script_stage2",
        )

def check_storyboard_special_templates(root: str, ep: str) -> None:
    """Complex shots must be declared through reusable storyboard templates.

    The expensive image/video stages should inherit a structured action/blocking
    contract instead of asking the model to invent fights, chases, reverse shots
    or crowd staging from prose every time.
    """
    p = storyboard_path(root, ep)
    data = load_json(p)
    if not isinstance(data, dict):
        return
    clips = data.get("clips")
    if not isinstance(clips, list):
        return
    for i, clip in enumerate(clips, 1):
        if not isinstance(clip, dict):
            continue
        loc = f"{p} clip#{i}"
        template_id = str(clip.get("template", "")).strip()
        contract = clip.get("template_contract")
        blob = _clip_blob(clip)
        keyword_template = _first_template_keyword_hit(blob)

        if not template_id:
            if keyword_template:
                add(
                    BLOCK,
                    "专项镜头模板",
                    loc,
                    f"复杂镜头疑似「{keyword_template}」，但缺 template/template_contract；回 n2d-script 按 references/专项镜头模板库.md 套模板，不要从零写 prompt",
                )
            elif isinstance(contract, dict):
                add(BLOCK, "专项镜头模板", loc, "有 template_contract 但缺 template；两者必须成对出现")
            continue

        if template_id not in SPECIAL_SHOT_TEMPLATE_FIELDS:
            add(
                BLOCK,
                "专项镜头模板",
                loc,
                f"未知 template「{template_id}」；只能使用 {', '.join(SPECIAL_SHOT_TEMPLATE_FIELDS.keys())}",
            )
            continue
        if not isinstance(contract, dict):
            add(BLOCK, "专项镜头模板", loc, f"template={template_id} 但缺 template_contract 结构块")
            continue
        if str(contract.get("template_id", "")).strip() != template_id:
            add(BLOCK, "专项镜头模板", loc, f"template_contract.template_id 必须等于 template「{template_id}」")
        for key in SPECIAL_SHOT_TEMPLATE_FIELDS[template_id]:
            if _field_is_missing(contract, key):
                add(BLOCK, "专项镜头模板", loc, f"template={template_id} 的 template_contract 缺字段：{key}")

def check_cross_episode_style(root: str, ep: str) -> None:
    """跨集色调/风格基线：以打样集为基准比对本集 色调基线基调 + 风格名。

    集级 visual_contract/style_contract 各自自洽、inherit 各自 pass，整部却可能画风跳（第5集冷青灰、第6集暖橙）。
    色调基线允许逐集细化，但其【基调首句】应跨集恒定；风格名应完全一致。漂移→WARN（以打样集为准或确认有意改）。
    """
    base_ep = _earliest_storyboard_ep(root)
    if not base_ep or base_ep == ep:
        return
    # 直接读 JSON（只需契约块，不触发 load_storyboard 的 clips[] 硬校验与副作用 BLOCK）
    base, cur = load_json(storyboard_path(root, base_ep)), load_json(storyboard_path(root, ep))
    if not isinstance(base, dict) or not isinstance(cur, dict):
        return
    p = storyboard_path(root, ep)
    base_tone = _tone_base((base.get("visual_contract") or {}).get("色调基线"))
    cur_tone = _tone_base((cur.get("visual_contract") or {}).get("色调基线"))
    if base_tone and cur_tone and base_tone != cur_tone:
        add(WARN, "跨集色调", p,
            f"本集色调基线基调「{cur_tone}」与打样集 {base_ep}「{base_tone}」不一致——色调可逐集细化但基调应跨集恒定；"
            f"以打样集为准或确认有意改（防整部画风跳）", return_to_stage="script_stage2")
    base_name = str((base.get("style_contract") or {}).get("风格名", "")).strip()
    cur_name = str((cur.get("style_contract") or {}).get("风格名", "")).strip()
    if base_name and cur_name and base_name != cur_name:
        add(WARN, "跨集风格", p,
            f"本集风格名「{cur_name}」与打样集 {base_ep}「{base_name}」不一致——基础视觉风格应跨集统一；核对是否选错风格",
            return_to_stage="script_stage2")

def check_cross_episode_character_definition(root: str, ep: str) -> None:
    """跨集「角色文字定义」漂移信号（advisory·WARN）：本集是否在悄悄重新派生角色而非复用定妆锚。

    identity_registry 是跨集共享的单一真值源（一部一份），但**每集的出图总览/prompt 文字**是手/AI
    现写的，可能把已建卡角色重描成与锚定相矛盾的样子（换发色/换装/换配饰）——这类文字漂移在出图前
    此前零机检（只有渲染后人脸 embedding 可能抓到，且发型/服装人脸检测看不见）。

    本检查保守取信号、不误伤：对 registry 里每个有 `forms[].anchor_phrase`（锚定相）的角色，若其名字/别名
    或 CHAR_id 在本集出图总览里**被引用**，却**一个锚定相描述符都没出现**（凤眼薄唇/乌黑.../月白粗布旧宫装…
    按 `·` 切的 token 全缺）→ WARN：可能跨集重新派生，请核对发型/瞳色/服装/配饰与定妆库一致。只要总览引用了
    锚定相里任一描述符即放行（低误报）。纯 WARN 不 BLOCK——文字矛盾判定本身模糊，先把"零信号"补成"有信号"。
    """
    data = load_json(identity_registry_path(root))
    if not isinstance(data, dict):
        return  # 定妆库未建（如出图前早期）——跳过
    chars = data.get("characters")
    if isinstance(chars, dict):
        chars = list(chars.values())
    if not isinstance(chars, list) or not chars:
        return
    overview_path = os.path.join(root, _ce_overview_rel(ep))
    if not os.path.isfile(overview_path):
        return  # 本集出图总览未生成——跳过，不误报
    try:
        overview = open(overview_path, encoding="utf-8").read()
    except OSError:
        return
    for c in chars:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "").strip()
        names = [n.strip() for n in str(c.get("name") or "").replace("／", "/").split("/") if n.strip()]
        referenced = (cid and cid in overview) or any(n in overview for n in names)
        if not referenced:
            continue
        forms = c.get("forms") if isinstance(c.get("forms"), list) else []
        anchor = str((forms[0] if forms else {}).get("anchor_phrase") or "").strip()
        if not anchor:
            continue  # 无锚定相可比
        tokens = [t.strip() for t in anchor.replace("，", "·").replace(",", "·").split("·") if len(t.strip()) >= ANCHOR_TOKEN_MIN_CHARS]
        if tokens and not any(t in overview for t in tokens):
            label = names[0] if names else cid
            add(WARN, "跨集角色定义", overview_path,
                f"本集出图总览引用了角色「{label}」({cid})，却未出现其 identity_registry 锚定相任一描述符"
                f"（{anchor}）——可能跨集重新派生而非复用定妆。请核对本集发型/瞳色/服装/配饰与定妆库一致，"
                "并在总览引用锚定相（或角色参考图）以防跨集悄悄变样。",
                return_to_stage="image")

def check_cross_episode_contract(root: str, ep: str) -> None:
    """跨集视觉契约方向反转（advisory·WARN）：同一地点跨集光位左右/轴线走向翻 = 越轴/光跳穿帮。

    `check_contract_inheritance` 管**同集内**出图↔出视频逐字一致；`check_cross_episode_style` 管整部色调/
    风格名恒定。本检查补第三类跨集穿帮——读本集与**前一可比集**的 `出图/第N集/prompt/00_总览.md` 视觉契约，
    只在 asset_registry 的 LOC 地点**两集都出现且方向反转**时报（地点共现门控压噪音）。纯启发式，**只 WARN
    不 BLOCK**（同 cross_episode_contract.py 设计）；过去靠人手动跑那个脚本→几乎没人跑，现在并进 gate 自动落地。
    """
    cur_rel = _ce_overview_rel(ep)
    cur_path = os.path.join(root, cur_rel)
    if not os.path.isfile(cur_path):
        return  # 本集出图总览未生成（如 image_preflight 早于出图）——跳过，不误报
    prev_ep = _ce_prior_episode(root, ep)
    if not prev_ep:
        return  # 首集无前集可比
    # 乱序/跳集生产：prior_episode 取的是"最近一个有出图总览的前集"，可能跨过缺总览的中间集。
    # 跨过缺口的对比会让"已覆盖"悄悄变成"跨集没逐集比过"——留个 WARN 信号，别静默跳。
    cur_n = _ce_episode_number(ep)
    prev_n = _ce_episode_number(prev_ep)
    if cur_n is not None and prev_n is not None and prev_n < cur_n - 1:
        add(WARN, "跨集契约", cur_path,
            f"跨集视觉契约对比跨过了缺失的中间集：本集（{ep}）只与 {prev_ep} 比对，"
            f"第 {prev_n + 1}–{cur_n - 1} 集 的出图总览缺失、未参与逐集核对。"
            "按集顺序补齐中间集总览后再核对跨集光位/轴线一致性。")
    prev_path = os.path.join(root, _ce_overview_rel(prev_ep))
    if not os.path.isfile(prev_path):
        return  # 防御：prior_episode 已保证存在
    try:
        prev_text = open(prev_path, encoding="utf-8").read()
        cur_text = open(cur_path, encoding="utf-8").read()
    except OSError:
        return
    diff = _cross_episode_diff(prev_text, cur_text, _ce_scene_names(root), prev_ep=prev_ep, cur_ep=ep,
                               core_scenes=_ce_core_scene_names(root))
    for w in diff.get("warnings", []):
        # P2b：核心主场景（asset_registry 显式标 core）跨集光位/轴线反转升 BLOCK；其余仍 WARN（启发式·人判）。
        sev = BLOCK if w.get("level") == "block" else WARN
        add(sev, "跨集光位轴线", f"{cur_path}（vs {prev_ep}）", w.get("note", ""),
            return_to_stage="image", scene=w.get("scene", ""), kind=w.get("kind", ""),
            rerun_scope="同地点跨集光位/轴线翻=越轴/光跳穿帮；确认是否有意（反打/换机位），否则回 n2d-image 对齐前集 00_总览 视觉契约。",
            affected_artifacts=[cur_rel, _ce_overview_rel(prev_ep), "出图/共享/asset_registry.json"])

__all__ = [
    'check_contract_inheritance',
    'check_asset_handoff_inheritance',
    'check_reference_plan_applied',
    'check_director_camera_plan_consumption',
    'check_storyboard_contract',
    'check_storyboard_visual_contract',
    'check_storyboard_style_contract',
    'check_storyboard_possession_gate',
    'check_storyboard_special_templates',
    'check_cross_episode_style',
    'check_cross_episode_character_definition',
    'check_cross_episode_contract',
]
