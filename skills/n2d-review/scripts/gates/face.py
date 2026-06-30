#!/usr/bin/env python3
"""gates/face.py — 人物视觉身份一致性族：脸/身份/表情/锚点/角色后端锁（崩脸·跨镜换脸·表情漂的承重硬闸多在此）

按证据族从 gate.py 拆出的 check_ 闸（增量3）。从 gate_core 取共享基座(add/常量/无状态助手)，
避免与 gate.py 循环导入。gate.py `from gates.face import *` 回灌，run()/按名自省助手照常解析。
本族成员经校验为 call-graph-free（不调用其它 check_、也不被其它 check_ 调用），可独立迁移。
"""
from gate_core import *  # noqa: F401,F403  共享基座（add/findings/常量/无状态助手）
from gate_core import (  # import* 默认漏的下划线私有助手，按需显式带上（保守全量）
    _CORE_SCOPES,
    _CORE_SCOPE_RE,
    _NON_NATIVE_BINDINGS,
    _clip_character_ids,
    _clip_is_closeup,
    _episode_big_expression_closeup_clips,
    _field_is_missing,
    _form_anchor_relpath,
    _identity_expression_path,
    _identity_ready_reference_list_paths,
    _identity_reference_exists,
    _identity_reference_item_path,
    _identity_reference_item_ready,
    _identity_reference_matches_asset_key,
    _image_form_has_identity_lock,
    _is_restricted_partial_form,
    _performance_signature_present,
    _production_events_path,
    _prohibited_face_patch_outputs,
    _route_clip_character_refs,
    _sha256_file,
    _styleid_release_gate_required,
    _styleid_release_signoff_path,
    _styleid_structured_signoff_ok,
    _validate_character_asset_bundle,
    _validate_character_dna,
    _validate_generation_control,
    _validate_identity_adapter_map,
    _validate_identity_lora,
    _validate_reference_atlas,
    _validate_same_source_makeup_derivation,
    _validate_signature_equipment,
    _validate_wardrobe_profile,
    _video_route_backend_roles,
)

def check_input_frame_qc(root: str, ep: str) -> None:
    """出视频前置（省最贵那一步的钱）：图生视频是 n2d 最贵工位，image2video 会**忠实把首帧缺陷动起来**——
    崩脸的首帧 → 崩脸的片。所以付费出视频前先确认输入首帧已过出图落档机检 `image_qc`。
    读持久化结果（`生产数据/image_qc/<ep>/image_qc_<ep>.json`），**不重跑像素引擎**（每 Clip 提交都重跑太贵）：
      · `summary.hard_blocks>0`（崩脸 / 接缝断 / 降级精度近景 / 非法 CHAR）→ BLOCK，回 n2d-image 修复 + 重跑 QC；
      · 无 image_qc 结果 / 旧版 image_qc 无角色脸覆盖结果 → BLOCK；
      · `qc_environment.precision_level!=full` → BLOCK（降级精度不得进入 video）；
      · 角色脸定妆比对覆盖缺口 → BLOCK；
      · image_qc 结果早于最新 PNG（出图后改过帧没重验）→ BLOCK。"""
    png_dir = os.path.join(root, "出图", ep, "图片")
    pngs = glob.glob(os.path.join(png_dir, "*.png"))
    if not pngs:
        return  # check_image_assets 已 BLOCK「本集没有分镜 PNG」
    qc_path = os.path.join(root, "生产数据", "image_qc", ep, f"image_qc_{ep}.json")
    prohibited = _prohibited_face_patch_outputs(root, ep)
    if prohibited:
        sample = "、".join(p["png"] for p in prohibited[:5])
        more = f" 等 {len(prohibited)} 张" if len(prohibited) > 5 else ""
        add(BLOCK, "出图落档QC", _production_events_path(root),
            f"{PROHIBITED_FACE_PATCH_LABEL}：发现 {len(prohibited)} 张最新 image 落档事件来自本地贴脸/换脸/裁脸贴回画面"
            f"（{sample}{more}）。embedding 分数只是证据，不是目标；不能为了过脸部 embedding QC 把定妆脸盖到镜头上。"
            "这些图不能进 video，必须回 n2d-image 用真实重抽或官方 image2image 派生替换，并重跑 image_qc。",
            return_to_stage="image")
        return
    qc = load_json(qc_path)
    if not isinstance(qc, dict):
        add(BLOCK, "出图落档QC", qc_path,
            "出视频前未见 image_qc 落档机检结果——输入首帧的崩脸/降级精度近景未经核验。"
            "先跑 `dashboard gate --stage image`（或 `image_qc.py`）再出视频，别花图生视频的钱动画一张未验首帧。",
            return_to_stage="image")
        return
    hard = int((qc.get("summary") or {}).get("hard_blocks") or 0)
    if hard > 0:
        add(BLOCK, "出图落档QC", qc_path,
            f"输入首帧 image_qc 仍有 {hard} 项硬阻断（崩脸/接缝断/降级精度近景/非法 CHAR）——"
            "图生视频会忠实把这些缺陷动起来，是最贵工位上的纯浪费。先回 n2d-image 修复并重跑 image_qc 再出视频。",
            return_to_stage="image")
        return
    coverage = qc.get("face_reference_coverage")
    if not isinstance(coverage, dict):
        add(BLOCK, "出图落档QC", qc_path,
            "输入首帧 image_qc 是旧版结果，缺 `face_reference_coverage` 逐镜角色脸定妆比对覆盖证据。"
            "重跑 image_qc，确认每张已落档角色 PNG 都逐张对定妆/身份主参考过 full QC 后再出视频。",
            return_to_stage="image")
        return
    env = qc.get("qc_environment") or {}
    precision = str(env.get("precision_level") or "")
    if precision != "full":
        add(BLOCK, "出图落档QC", qc_path,
            f"输入首帧 image_qc 精度为 `{precision or 'unknown'}`，不是 full——"
            "含角色镜头图必须用 full 精度脸部参考比对后才能进 video；补 insightface/onnxruntime/buffalo_l 后重跑 image_qc。",
            return_to_stage="image")
        return
    missing = coverage.get("missing") or []
    if coverage.get("verdict") == "block" or missing:
        add(BLOCK, "出图落档QC", qc_path,
            f"角色脸定妆比对覆盖未过：{len(missing)} 张已落档角色图缺 full 比对/未通过比对。"
            "这是进入 video 的硬闸门；回 n2d-image 补检、重抽或修复后重跑 image_qc。",
            return_to_stage="image")
        return
    try:
        if max(os.path.getmtime(p) for p in pngs) > os.path.getmtime(qc_path) + 1:
            add(BLOCK, "出图落档QC", qc_path,
                "输入首帧晚于上次 image_qc（出图后改过帧未重验）——出视频前先重跑 image_qc，避免动画一张未验首帧。",
                return_to_stage="image")
            return
    except OSError:
        pass
    if fingerprint_is_fresh is None:
        add(BLOCK, "出图落档QC", qc_path,
            "无法加载 image_qc 输入指纹校验器（skill_snapshot.fingerprint_is_fresh）——"
            "不能确认该 QC 报告对应当前 prompt/registry/PNG；修复环境并重跑 image_qc。",
            return_to_stage="image")
        return
    fresh = fingerprint_is_fresh(qc.get("inputs_fingerprint"), root)  # type: ignore[misc]
    if fresh is None:
        add(BLOCK, "出图落档QC", qc_path,
            "输入首帧 image_qc 缺 `inputs_fingerprint`（旧版或手写报告），无法证明报告对应当前 prompt/registry/PNG。"
            "重跑 image_qc 生成带输入指纹的报告后再出视频。",
            return_to_stage="image")
        return
    if fresh is False:
        add(BLOCK, "出图落档QC", qc_path,
            "输入首帧 image_qc 的 `inputs_fingerprint` 与当前文件失配（prompt、registry 或 PNG 已变）。"
            "当前结论作废；出视频前先重跑 image_qc。",
            return_to_stage="image")
        return
    # 防伪造：freshness 只证明「报告声明的那批文件没变」，不证明「真把全部 PNG 都验了」——一份手写/陈旧
    # 报告可以只声明 1 张图、算对那张 sha 就过 freshness。这里独立枚举 出图/<ep>/图片/ 的真实 PNG，核对
    # image_qc 指纹是否覆盖每一张实际落档图（按文件名）；有真实 PNG 不在报告核验范围 = 这张根本没被机检 → BLOCK。
    recorded = qc.get("inputs_fingerprint") or {}
    declared_png = {os.path.basename(k) for k in (recorded.get("files") or {}) if str(k).endswith(".png")}
    uncovered = sorted({os.path.basename(p) for p in pngs} - declared_png)
    if uncovered:
        sample = "、".join(uncovered[:5]) + (f" 等 {len(uncovered)} 张" if len(uncovered) > 5 else "")
        add(BLOCK, "出图落档QC", qc_path,
            f"image_qc 指纹只覆盖了报告声明的子集，{len(uncovered)} 张实际落档 PNG 不在核验范围（{sample}）——"
            "这是手写/伪造/陈旧报告的典型特征：声明少量文件算对 sha 就想过 freshness，但这些图根本没被机检过。"
            "重跑 image_qc，让 `inputs_fingerprint` 覆盖 出图/<ep>/图片/ 的全部 PNG 后再出视频。",
            return_to_stage="image")
        return

def check_identity_handoff_inheritance(root: str, ep: str) -> None:
    """逐镜身份 出图→出视频 继承：命名角色镜必须锁身份；多锚帧角色 Clip 必须同源
    reference_group / expressions；大表情近景必须锁脸不锁情。

    之前 gate 只通过 video prompt 字段做散点检查，完整身份交接检查只在 inherit_contract.py 裸命令中
    出现。接进 video gate 后，真正提交生视频前会统一阻断“首/中/尾锚图不是同一张脸”的流程漏洞。
    """
    res = check_identity_handoff(root, ep)
    if not res.get("available"):
        return
    dim = CONSISTENCY_DIMENSIONS["contract_inheritance"]
    vid_rel = res.get("clips_file", os.path.join("出视频", ep, "prompt", "01_clips.md"))
    vid_p = os.path.join(root, vid_rel)
    for f in res.get("findings", []):
        if f.get("severity") == "block":
            add(
                BLOCK,
                "契约继承",
                vid_p,
                f"身份逐镜交接[{f.get('code')}]：{f.get('note')}",
                return_to_stage=dim["return_to_stage"],
                rerun_scope=dim["scope"],
                affected_artifacts=[vid_rel],
            )
        else:
            add(WARN, "契约继承", vid_p, f"身份逐镜交接[{f.get('code')}]：{f.get('note')}")

def check_identity_registry(
    root: str,
    require_reference_assets: bool = False,
    required_character_ids: Optional[set] = None,
    required_identity_refs: Optional[set] = None,
) -> None:
    """Validate the role identity registry shared by image/video/review stages."""
    p = identity_registry_path(root)
    data = load_json(p)
    if not isinstance(data, dict):
        add(BLOCK, "资产身份注册层", p, "缺少或无法解析 identity_registry.json；共享定妆必须升级为角色身份注册层")
        return
    if data.get("kind") not in (None, IDENTITY_REGISTRY_KIND, "n2d_asset_identity_registry"):
        add(BLOCK, "资产身份注册层", p, f"kind 必须是 {IDENTITY_REGISTRY_KIND}")
    chars = data.get("characters")
    if not isinstance(chars, list) or not chars:
        add(BLOCK, "资产身份注册层", p, "characters[] 缺失或为空；明确角色/形态必须登记")
        return

    seen_ids = set()
    for ci, char in enumerate(chars, 1):
        loc = f"{p} character#{ci}"
        if not isinstance(char, dict):
            add(BLOCK, "资产身份注册层", loc, "character 必须是对象")
            continue
        for key in ("id", "name", "scope", "forms"):
            if _field_is_missing(char, key):
                add(BLOCK, "资产身份注册层", loc, f"character 缺字段：{key}")
        char_id = str(char.get("id", "")).strip()
        if char_id:
            if char_id in seen_ids:
                add(BLOCK, "资产身份注册层", loc, f"重复 character id：{char_id}")
            seen_ids.add(char_id)

        _validate_character_asset_bundle(root, char, loc)

        char_strict_references = required_character_ids is None or char_id in required_character_ids
        refs_for_char = {
            str(ref)
            for ref in (required_identity_refs or set())
            if str(ref) == char_id or str(ref).startswith(f"{char_id}/")
        }
        has_form_refs_for_char = any("/" in ref for ref in refs_for_char)
        strict_all_forms_for_char = (
            required_identity_refs is None
            or (char_id in refs_for_char and not has_form_refs_for_char)
            or not refs_for_char
        )

        forms = char.get("forms")
        if not isinstance(forms, list) or not forms:
            add(BLOCK, "资产身份注册层", loc, "forms[] 缺失或为空；常态/变体必须分别登记")
            continue
        form_count = len(forms)
        for fi, form in enumerate(forms, 1):
            floc = f"{loc} form#{fi}"
            if not isinstance(form, dict):
                add(BLOCK, "资产身份注册层", floc, "form 必须是对象")
                continue
            for key in IDENTITY_FORM_FIELDS:
                if _field_is_missing(form, key):
                    add(BLOCK, "资产身份注册层", floc, f"form 缺字段：{key}")

            _validate_character_dna(form.get("character_dna"), floc)
            # 铁律 B11（2026-06-27 用户裁决）：核心/长线角色表演指纹 demo 也强制——
            # 不随 profile（demo/production）降级，demo 与 production 同标准。
            if (
                _CORE_SCOPE_RE.search(f"{char.get('tier') or ''} {char.get('scope') or ''}")
                and not _performance_signature_present(char, form)
            ):
                add(
                    BLOCK,
                    "角色表演一致性",
                    f"{floc} performance_signature",
                    "核心/长线角色缺 performance_signature；请登记微表情、惯用动作、站姿、说话节奏、眼神反应等表演指纹，"
                    "否则脸像一致但角色表演会跨集漂。",
                    return_to_stage="image",
                )
            # 铁律 B11：标志配饰一致性 demo 也校验（不随 profile 降级）。
            _validate_signature_equipment(char, form, floc)
            if "wardrobe_profile" in form:
                _validate_wardrobe_profile(form.get("wardrobe_profile"), floc)

            reference_group = form.get("reference_group")
            restricted_partial = _is_restricted_partial_form(char, form)
            form_name = str(form.get("form") or "").strip()
            form_ref = f"{char_id}/{form_name}" if char_id and form_name else char_id
            strict_references = char_strict_references and (
                strict_all_forms_for_char or form_ref in refs_for_char
            )
            _validate_reference_atlas(
                root,
                form,
                floc,
                strict_references,
                require_reference_assets,
                restricted_partial=restricted_partial,
            )
            if not isinstance(reference_group, dict):
                add(BLOCK, "资产身份注册层", floc, "reference_group 必须是对象")
            else:
                asset_key = str(form.get("asset_key") or "").strip()
                # Legacy single-form baseline characters may use `定妆_<角色>.png`.
                # Multi-form or named variant forms must advertise the exact asset_key.
                enforce_asset_key_filename = form_count > 1 or form_name not in {"常态", "局部参考", "局部参考（暂不正脸）"}
                if restricted_partial:
                    partial_keys = ("hand", "silhouette")
                    if strict_references and not any(not _field_is_missing(reference_group, key) for key in partial_keys):
                        add(BLOCK, "资产身份注册层", floc, "restricted_partial reference_group 至少需要 hand 或 silhouette 局部参考路径")
                    for key in partial_keys:
                        if _field_is_missing(reference_group, key):
                            continue
                        item = reference_group.get(key)
                        rel = _identity_reference_item_path(item)
                        if strict_references and not _identity_reference_item_ready(item):
                            add(BLOCK, "资产身份注册层", floc,
                                f"restricted_partial reference_group.{key} 必须为 ready 且有路径；planned/空路径不能放行。")
                            continue
                        if require_reference_assets and strict_references and not _identity_reference_exists(root, rel):
                            add(BLOCK, "资产身份注册层", os.path.join(root, rel) if not os.path.isabs(rel) else rel, f"reference_group.{key} 路径不存在")
                else:
                    for key in REQUIRED_CHARACTER_MAKEUP_REFERENCE_GROUP_FIELDS:
                        if _field_is_missing(reference_group, key):
                            if strict_references:
                                add(BLOCK, "资产身份注册层", floc, f"reference_group 缺核心路径：{key}")
                            continue
                        item = reference_group.get(key)
                        rel = _identity_reference_item_path(item)
                        if strict_references and not _identity_reference_item_ready(item):
                            add(BLOCK, "资产身份注册层", floc,
                                f"reference_group.{key} 必须为 ready 且有路径；planned/空路径只能表示待补，不能放行。"
                                "三视图人审拼版不能替代正/45°/侧/背等拆分参考。")
                            continue
                        if asset_key and enforce_asset_key_filename and not _identity_reference_matches_asset_key(asset_key, rel):
                            add(BLOCK, "资产身份注册层", floc,
                                f"reference_group.{key} 路径 `{rel}` 未包含 asset_key={asset_key}；"
                                "服饰/形态变体必须独立定妆，禁止复用其它服饰形态参考")
                        if require_reference_assets and strict_references and not _identity_reference_exists(root, rel):
                            add(BLOCK, "资产身份注册层", os.path.join(root, rel) if not os.path.isabs(rel) else rel, f"reference_group.{key} 路径不存在")
                        _validate_same_source_makeup_derivation(
                            root, item, key, floc, strict_references, require_reference_assets
                        )
                    body_keys = [key for key in CHARACTER_MAKEUP_BODY_REFERENCE_FIELDS if not _field_is_missing(reference_group, key)]
                    if not body_keys:
                        if strict_references:
                            add(BLOCK, "资产身份注册层", floc,
                                "reference_group 缺核心路径：half_body_or_full_body；基础定妆包必须有半身或全身服装参考。")
                    else:
                        body_key = body_keys[0]
                        body_item = reference_group.get(body_key)
                        body_rel = _identity_reference_item_path(body_item)
                        if strict_references and not _identity_reference_item_ready(body_item):
                            add(BLOCK, "资产身份注册层", floc,
                                f"reference_group.{body_key} 必须为 ready 且有路径；planned 服装参考不能放行。")
                        elif asset_key and enforce_asset_key_filename and not _identity_reference_matches_asset_key(asset_key, body_rel):
                            add(BLOCK, "资产身份注册层", floc,
                                f"reference_group.{body_key} 路径 `{body_rel}` 未包含 asset_key={asset_key}；"
                                "服饰/形态变体必须独立定妆，禁止复用其它服饰形态参考")
                        elif require_reference_assets and strict_references and not _identity_reference_exists(root, body_rel):
                            add(BLOCK, "资产身份注册层", os.path.join(root, body_rel) if not os.path.isabs(body_rel) else body_rel, f"reference_group.{body_key} 路径不存在")
                        _validate_same_source_makeup_derivation(
                            root, body_item, body_key, floc, strict_references, require_reference_assets
                        )
                face_anchor_refs = reference_group.get("face_anchor_refs", [])
                expressions = reference_group.get("expressions", [])
                if face_anchor_refs is not None and not isinstance(face_anchor_refs, list):
                    add(BLOCK, "资产身份注册层", floc, "reference_group.face_anchor_refs 必须是列表")
                    face_anchor_refs = []
                if expressions is not None and not isinstance(expressions, list):
                    add(BLOCK, "资产身份注册层", floc, "reference_group.expressions 必须是列表")
                    expressions = []
                face_anchor_paths = [p for p in _identity_ready_reference_list_paths(face_anchor_refs) if p]
                expression_paths = [p for p in _identity_ready_reference_list_paths(expressions) if p]
                if not restricted_partial and strict_references and not (face_anchor_paths or expression_paths):
                    add(BLOCK, "资产身份注册层", floc,
                        "reference_group 至少需要一个同源脸部特写/表情参考：优先写 face_anchor_refs，"
                        "也兼容 expressions；所有人物（含短线/功能角色）都按主角基础定妆包标准执行。")
                for face_ref in face_anchor_refs or []:
                    rel = _identity_reference_item_path(face_ref)
                    if not rel:
                        add(BLOCK, "资产身份注册层", floc,
                            "reference_group.face_anchor_refs 存在空路径；可用字符串路径或 {label/emotion, path} 对象")
                        continue
                    if strict_references and not _identity_reference_item_ready(face_ref):
                        add(BLOCK, "资产身份注册层", floc,
                            "reference_group.face_anchor_refs 必须为 ready 且有路径；planned 脸部特写不能放行。")
                    if require_reference_assets and strict_references and not _identity_reference_exists(root, rel):
                        add(BLOCK, "资产身份注册层", os.path.join(root, rel) if not os.path.isabs(rel) else rel, "reference_group.face_anchor_refs 路径不存在")
                    if asset_key and asset_key not in os.path.basename(rel):
                        add(BLOCK, "资产身份注册层", floc, f"reference_group.face_anchor_refs 跨角色/形态污染：{rel} 不属于 asset_key={asset_key}")
                    _validate_same_source_makeup_derivation(
                        root, face_ref, "face_anchor_refs", floc, strict_references, require_reference_assets
                    )
                for expr in expressions or []:
                    rel = _identity_expression_path(expr)
                    if not rel:
                        add(BLOCK, "资产身份注册层", floc,
                            "reference_group.expressions 存在空路径；可用字符串路径或 {emotion, path} 对象")
                        continue
                    if strict_references and not _identity_reference_item_ready(expr):
                        add(BLOCK, "资产身份注册层", floc,
                            "reference_group.expressions 必须为 ready 且有路径；planned 表情/脸锚不能放行。")
                    if require_reference_assets and strict_references and not _identity_reference_exists(root, rel):
                        add(BLOCK, "资产身份注册层", os.path.join(root, rel) if not os.path.isabs(rel) else rel, "reference_group.expressions 路径不存在")
                    if asset_key and asset_key not in os.path.basename(rel):
                        add(BLOCK, "资产身份注册层", floc, f"reference_group.expressions 跨角色/形态污染：{rel} 不属于 asset_key={asset_key}")

            adapters = form.get("identity_adapters")
            if not isinstance(adapters, dict):
                add(BLOCK, "资产身份注册层", floc, "identity_adapters 必须是对象")
            else:
                for section in IDENTITY_ADAPTER_SECTIONS:
                    _validate_identity_adapter_map(adapters.get(section), floc, section)
                _validate_identity_lora(adapters.get("lora"), floc, root)

            _validate_generation_control(form.get("generation_control"), floc)

            angle_policy = form.get("angle_policy")
            if not isinstance(angle_policy, dict):
                add(BLOCK, "资产身份注册层", floc, "angle_policy 必须是对象")
            else:
                for key in IDENTITY_ANGLE_FIELDS:
                    if _field_is_missing(angle_policy, key):
                        add(BLOCK, "资产身份注册层", floc, f"angle_policy 缺字段：{key}")

            drift_forbidden = form.get("drift_forbidden")
            if not isinstance(drift_forbidden, list) or not drift_forbidden:
                add(BLOCK, "资产身份注册层", floc, "drift_forbidden 必须是非空列表")

def check_identity_adapter_matrix(root: str) -> None:
    p = identity_adapter_matrix_path(root)
    data = load_json(p)
    if not isinstance(data, dict):
        add(BLOCK, "资产身份闭环", p, "缺少或无法解析 identity_adapter_matrix.json；先运行 `python3 skills/n2d-identity/scripts/identity.py <作品根> --write`")
        return
    if data.get("kind") != IDENTITY_ADAPTER_MATRIX_KIND:
        add(BLOCK, "资产身份闭环", p, f"kind 必须是 {IDENTITY_ADAPTER_MATRIX_KIND}")
    forms = data.get("forms")
    if not isinstance(forms, list) or not forms:
        add(BLOCK, "资产身份闭环", p, "forms[] 为空；identity_registry 没有展开成可执行后端 binding")
        return
    for idx, form in enumerate(forms, 1):
        loc = f"{p} form#{idx}"
        if not isinstance(form, dict):
            add(BLOCK, "资产身份闭环", loc, "form 必须是对象")
            continue
        for key in ("character_id", "form", "reference_group", "image_bindings", "video_bindings", "lora_binding"):
            if _field_is_missing(form, key):
                add(BLOCK, "资产身份闭环", loc, f"adapter matrix form 缺字段：{key}")
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    matrix_fp = str(summary.get("anchor_fingerprint") or "").strip()
    registry = load_json(identity_registry_path(root))
    if not isinstance(registry, dict):
        add(BLOCK, "资产身份闭环", identity_registry_path(root), "无法解析 identity_registry.json；matrix 无法证明相对当前身份库新鲜")
        return
    try:
        from identity import registry_anchor_fingerprint  # type: ignore
        current_fp = registry_anchor_fingerprint(registry)
    except Exception as exc:
        add(BLOCK, "资产身份闭环", p, f"无法计算当前 identity_registry anchor_fingerprint：{type(exc).__name__}: {exc}")
        return
    if not matrix_fp:
        add(BLOCK, "资产身份闭环", p, "identity_adapter_matrix.summary 缺 anchor_fingerprint；请重跑 `python3 skills/n2d-identity/scripts/identity.py <作品根> --write`")
    elif matrix_fp != current_fp:
        add(
            BLOCK,
            "资产身份闭环",
            p,
            "identity_adapter_matrix 已过期：summary.anchor_fingerprint 与当前 identity_registry 不一致；"
            "共享定妆/锚点被改后必须重跑 `python3 skills/n2d-identity/scripts/identity.py <作品根> --write`。",
        )

def _form_has_expression_library(form: Mapping[str, Any]) -> bool:
    rg = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
    expressions = rg.get("expressions") if isinstance(rg, Mapping) else []
    if _identity_ready_reference_list_paths(expressions):
        return True
    anchors = form.get("expression_anchors")
    if isinstance(anchors, list):
        for item in anchors:
            if isinstance(item, Mapping):
                rel = str(item.get("path") or "").strip()
                if rel and item.get("self_check_passed") is not False:
                    return True
            elif str(item or "").strip():
                return True
    return False

def check_production_core_identity_lock(root: str, ep: str, stage: str = "image_preflight") -> None:
    """production 核心长线角色不能只靠 prompt + 单张定妆。

    基础 reference_group 由 check_identity_registry 负责；这里补执行层硬闸：
    核心/长线 form 必须同时具备表情库，以及 native subject / face_embedding / LoRA 三选一。
    """
    if consistency_release_profile(root, stage, ep) != "production":
        return
    reg = load_json(identity_registry_path(root))
    if not isinstance(reg, dict):
        return
    setting = get_setting(root, "生图AI", "Codex").strip()
    canon, _kind = classify_image_backend(setting)
    missing_lock: List[str] = []
    missing_expr: List[str] = []
    for char in reg.get("characters", []) or []:
        if not isinstance(char, dict):
            continue
        if not _CORE_SCOPE_RE.search(f"{char.get('tier') or ''} {char.get('scope') or ''}"):
            continue
        cid = str(char.get("id") or "").strip()
        name = str(char.get("name") or cid or "?").strip()
        for form in char.get("forms", []) or []:
            if not isinstance(form, dict):
                continue
            form_name = str(form.get("form") or "").strip()
            label = f"{name}({cid}/{form_name})" if form_name else f"{name}({cid})"
            if not _form_has_expression_library(form):
                missing_expr.append(label)
            if not _image_form_has_identity_lock(form, canon or setting):
                missing_lock.append(label)
    if missing_expr:
        shown = "、".join(missing_expr[:8]) + ("…" if len(missing_expr) > 8 else "")
        add(
            BLOCK,
            "核心角色一致性",
            identity_registry_path(root),
            f"production 核心/长线角色缺表情库：{shown}。长线漫剧不能只靠 prompt + 单张定妆；"
            "至少补 reference_group.expressions 或 expression_anchors，并落自检/锚点后再出图。",
            return_to_stage="image",
        )
    if missing_lock:
        shown = "、".join(missing_lock[:8]) + ("…" if len(missing_lock) > 8 else "")
        add(
            BLOCK,
            "核心角色一致性",
            identity_registry_path(root),
            f"production 核心/长线角色缺执行层身份锁：{shown}。必须三选一："
            "原生 subject/character_id、face_embedding/Face Lock、或可用于当前生图后端的 LoRA；"
            "reference_group 只是基础资产，不等于跨集锁脸。",
            return_to_stage="image",
        )

def check_route_identity_readiness(root: str, ep: str) -> None:
    """换后端丢锁机检：出视频路由用到的 primary/fallback 后端 × identity_adapter_matrix 的角色锁脸能力对账。

    n2d-model-router 选后端时不读 matrix——一个在后端 A 原生注册了 character_id 的角色，若某 clip 被路由到
    后端 B（B 上只有 reference_group 兜底甚至无绑定），锁脸力骤降却无任何机检。本检查在出视频闸门前置对账：
    - 角色在 matrix 有「原生锁」(ready 且 binding 非 reference_group 族)，但路由用到的某 primary/fallback 后端在该角色上
      只有 reference_group 兜底 → 换后端丢原生锁（核心角色 BLOCK / 其余 WARN）；该后端连兜底都没有 → 必丢锁 BLOCK；
    - 全 reference_group 兜底（无任何原生锁，如当前 demo）= 后端间一致，不报（没有原生锁可丢，避免噪声）。
    """
    routes_data = load_json(os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json"))
    matrix_p = identity_adapter_matrix_path(root)
    matrix = load_json(matrix_p)
    if not isinstance(routes_data, dict) or not isinstance(matrix, dict):
        return  # 缺路由/矩阵：check_video_model_routes / check_identity_adapter_matrix 各自把关
    routes = routes_data.get("routes")
    forms = matrix.get("forms")
    if not isinstance(routes, list) or not isinstance(forms, list):
        return
    used_roles: List[Tuple[str, str, str, Tuple[Tuple[str, str], ...]]] = []
    for r in routes:
        if not isinstance(r, dict):
            continue
        clip_id = str(r.get("clip_id") or "?")
        refs = tuple(
            (str(ref.get("character_id") or ""), str(ref.get("form") or ""))
            for ref in _route_clip_character_refs(r)
        )
        for role, backend in _video_route_backend_roles(r, allow_empty_fallback=False):
            if backend:
                used_roles.append((clip_id, role, backend, refs))
    seen_used: set[Tuple[str, str, str, Tuple[Tuple[str, str], ...]]] = set()
    used_roles = [item for item in used_roles if not (item in seen_used or seen_used.add(item))]
    if not used_roles:
        return
    for form in forms:
        if not isinstance(form, dict):
            continue
        form_cid = str(form.get("character_id") or form.get("id") or "").strip()
        form_name = str(form.get("form") or form.get("form_name") or "").strip()
        vb = form.get("video_bindings") if isinstance(form.get("video_bindings"), dict) else {}
        native = sorted(b for b, v in vb.items()
                        if isinstance(v, dict) and v.get("ready")
                        and str(v.get("binding") or "") not in _NON_NATIVE_BINDINGS)
        if not native:
            continue  # 无原生锁 → 全兜底，后端间一致，无锁可丢
        name = form.get("character_name") or form.get("character_id") or "?"
        sev = BLOCK if str(form.get("scope") or "").strip() in _CORE_SCOPES else WARN
        for clip_id, role, b, refs in used_roles:
            if refs:
                matched = False
                for cid, ref_form in refs:
                    if cid != form_cid:
                        continue
                    if ref_form and form_name and ref_form != form_name:
                        continue
                    matched = True
                    break
                if not matched:
                    continue
            if b in native:
                continue
            v = vb.get(b)
            role_note = "fallback" if role == "fallback" else "primary"
            if not (isinstance(v, dict) and v.get("ready")):
                add(BLOCK, "换后端丢锁", matrix_p,
                    f"角色「{name}」已在 {native} 原生锁脸，但 {clip_id} 的 {role_note} 后端 {b} 无可用身份绑定（连 reference_group 兜底都没有）→ 必丢锁；改路由到 {native} 或先在 {b} 注册该角色身份",
                    return_to_stage="video_prompt",
                    rerun_scope=f"重跑 n2d-model-router 把涉及「{name}」的 clip primary/fallback 都约束到 {native}，或在 {b} 注册 character_id/face_lock 后再出视频。",
                    affected_artifacts=[f"出视频/{ep}/prompt/video_model_routes.json", "生产数据/identity_adapter_matrix.json"])
            elif str(v.get("binding") or "") in _NON_NATIVE_BINDINGS:
                add(sev, "换后端丢锁", matrix_p,
                    f"角色「{name}」已在 {native} 原生锁脸，但 {clip_id} 的 {role_note} 后端 {b} 仅 reference_group 兜底 = 换后端丢原生锁、锁脸力下降；核心角色 primary 与 fallback 都应改路由或在 {b} 注册原生身份",
                    return_to_stage="video_prompt",
                    rerun_scope=f"重跑 n2d-model-router 让「{name}」的 clip primary/fallback 优先用 {native}，或在 {b} 注册原生身份；不能让失败重试时 fallback 偷偷掉锁。",
                    affected_artifacts=[f"出视频/{ep}/prompt/video_model_routes.json"])

def check_stylized_face_encoder_policy(root: str, ep: str = "", stage: str = "") -> None:
    """风格化项目应把脸一致性机检切到 StyleID；缺权重时标降级 KPI。"""
    style = get_setting(root, "基础视觉风格", "")
    encoder = get_setting(root, "脸一致性机检后端", "arcface")
    model_ref = (
        get_setting(root, "N2D_STYLEID_MODEL", "")
        or get_setting(root, "StyleID模型", "")
        or get_setting(root, "StyleID model", "")
    )
    policy_env = dict(os.environ)
    if str(model_ref or "").strip():
        policy_env["N2D_STYLEID_MODEL"] = str(model_ref).strip()
    policy = face_encoder_policy(style, encoder, policy_env)
    if not (policy.get("stylized") or policy.get("requested_styleid")):
        return
    if policy.get("status") == "ready":
        return
    settings_loc = os.path.join(root, "_设置.md")
    model_status = str(policy.get("model_status") or "missing")
    model_path = str(policy.get("model_path") or "")
    if policy.get("requested_styleid"):
        if model_status == "missing":
            detail = "未配置"
        elif model_status == "download_disabled":
            detail = f"指向 Hugging Face 模型 `{model_path}`，但 N2D_ALLOW_MODEL_DOWNLOAD=0 禁止下载"
        elif model_status == "unapproved_remote":
            detail = f"指向未登记的远端模型：{model_path}"
        else:
            detail = f"路径不存在：{model_path}"
        msg = (
            f"基础视觉风格「{style}」已选择脸一致性机检后端=styleid，但 N2D_STYLEID_MODEL {detail}；"
            "StyleID 不可用时会回退 arcface_fallback，本集 character_consistency_kpi 标为降级档。"
        )
    else:
        msg = (
            f"基础视觉风格「{style}」属于风格化/漫剧脸，当前脸一致性机检后端={policy.get('encoder') or encoder}；"
            "建议项目级设置 `脸一致性机检后端: styleid` 并配置 N2D_STYLEID_MODEL。未配置前，"
            "角色脸一致性 KPI 按降级档处理，近景结果需提高人审权重。"
        )
    release_required, reason = _styleid_release_gate_required(root, ep, stage)
    if release_required and not _styleid_structured_signoff_ok(root, ep):
        signoff_rel = os.path.relpath(_styleid_release_signoff_path(root, ep), root)
        add(
            BLOCK,
            "风格化脸机检",
            settings_loc,
            f"{msg} 当前已触发发布闸门（{reason}）：缺可用 N2D_STYLEID_MODEL 时不得进入正式投放/高近景角色镜。"
            f"若确认接受降级，需写结构化 {signoff_rel}（kind=n2d_styleid_release_signoff, "
            "accepted=true, reviewer, reason, expires_at）后复跑。",
            return_to_stage="image",
        )
        return
    if release_required:
        msg += " 已检测到结构化 StyleID 降级签收；仍建议在投放前补 N2D_STYLEID_MODEL 并重跑 full QC。"
    add(WARN, "风格化脸机检", settings_loc, msg, return_to_stage="review")

def check_character_backend_pin(root: str, ep: str) -> None:
    """一角一后端跨集钉：核心长线 form 若登记 `backend_pin` 后本集换生图后端 → BLOCK，其余 WARN。

    同一角色跨集换后端本身是脸漂源（不同模型脸的先验不同），
    无持久主体 ID 后端尤甚。**纯 opt-in**：未登记 backend_pin 跳过。"""
    reg = load_json(identity_registry_path(root))
    if not isinstance(reg, dict):
        return
    cur_canon, _ = classify_image_backend(get_setting(root, "生图AI", "Codex").strip())
    reg_path = identity_registry_path(root)
    for c in (reg.get("characters") or []):
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "").strip()
        for fm in (c.get("forms") or []):
            if not isinstance(fm, dict):
                continue
            pin = str(fm.get("backend_pin") or "").strip()
            if not pin:
                continue
            pin_canon, _ = classify_image_backend(pin)
            if pin_canon == cur_canon:
                continue
            form_name = str(fm.get("form") or "").strip()
            label = f"{cid}/{form_name}" if form_name else (cid or "?")
            is_core = bool(_CORE_SCOPE_RE.search(f"{c.get('tier') or ''} {c.get('scope') or ''}"))
            sev = BLOCK if is_core else WARN
            add(sev, "角色一致性", reg_path,
                f"角色 `{label}` 身份钉在出图后端 `{pin_canon}`，本集项目 生图AI=`{cur_canon}`——"
                "同一角色跨集换后端本身是脸漂源（不同模型脸的先验不同），无持久主体 ID 后端尤甚。"
                "要么切回原后端出本集，要么先把该角色升原生主体库/LoRA 再换；确认有意更换则更新 backend_pin。",
                return_to_stage="image")

def check_anchor_fingerprints(root: str, ep: str) -> None:
    """共享定妆锚点指纹钉死（治跨集脸漂的结构根因之一）：identity_registry 的 form 若显式登记
    `anchor_sha`（opt-in），就校验磁盘上 front 定妆图当前 sha256 == 注册值。锚点被悄改/丢失 =
    下游每镜（含跨集每一集）继承换脸 → BLOCK。

    **纯 opt-in**：未登记 `anchor_sha` 的 form = 未启用钉死 → 跳过（向后兼容，现有作品/先出视频
    demo 不被突然阻断）。写入口：`image_qc.py <root> --pin-anchor CHAR_xx/形态`。"""
    reg = load_json(identity_registry_path(root))
    if not isinstance(reg, dict):
        return
    reg_path = identity_registry_path(root)
    pinned: List[Tuple[str, str, str]] = []  # (label, expected_sha, rel_path)
    for c in (reg.get("characters") or []):
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "").strip()
        for fm in (c.get("forms") or []):
            if not isinstance(fm, dict):
                continue
            exp = str(fm.get("anchor_sha") or "").strip()
            if not exp:
                continue
            form_name = str(fm.get("form") or "").strip()
            label = f"{cid}/{form_name}" if form_name else (cid or "?")
            pinned.append((label, exp, _form_anchor_relpath(fm)))
    if not pinned:
        return
    for label, exp, rel in pinned:
        full = os.path.join(root, rel) if rel else ""
        if not rel or not os.path.isfile(full):
            add(BLOCK, "共享定妆", reg_path,
                f"定妆锚点 `{label}` 已登记 anchor_sha 但 front 定妆图缺失"
                f"（{rel or 'reference_group 未填 front'}）——锚点丢失，下游每镜无母图可派生，跨集必漂；"
                "补回原锚点定妆图，或重新 `image_qc --pin-anchor`。")
            continue
        actual = _sha256_file(full)
        if actual != exp:
            add(BLOCK, "共享定妆", reg_path,
                f"定妆锚点 `{label}` 被改动：磁盘 sha256 与 registry `anchor_sha` 不一致"
                f"（pinned={exp[:12]}… actual={(actual or 'none')[:12]}…）——锚点一漂，所有引用它的集都继承换脸。"
                "若为有意更新：重出依赖镜后用 `image_qc --pin-anchor` 重新钉死；否则恢复原锚点定妆图。")

def check_core_anchor_pinning(root: str, ep: str) -> None:
    """核心长线角色未启用锚点钉死的前置提醒（advisory·WARN）。

    `check_anchor_fingerprints` 是纯 opt-in：没登记 `anchor_sha` 的 form 直接跳过——意味着一张被多集
    引用的锁脸定妆图，若在 `n2d-update media` 重刷或重生成时被换掉，下游每一集静默继承新脸而无任何机检
    （`check_referenced_assets_finalized` 只信 self_check_passed 标志、不验像素）。这里补「该钉没钉」的信号：
    对**本集引用到的核心长线角色**（scope/tier 命中贯穿全篇/主角/主反派等），若其 form 一个都没登记
    `anchor_sha` → **BLOCK**，必须 `image_qc --pin-anchor` 钉死后再付费出图。只对核心角色报（短线配角/
    单元妖不前置高档，对齐 n2d-image「ROI 驱动」），单条 rollup 不刷屏。

    铁律（2026-06-27 用户裁决）：治脸漂根因的锚点钉死对核心长线角色**默认开**、demo 不降标准——此前
    "纯 WARN 不 BLOCK 向后兼容" 已恢复为 BLOCK（见 docs/skill-design-principles.md B11 + consistency_charter）。"""
    data = load_json(identity_registry_path(root))
    if not isinstance(data, dict):
        return
    chars = data.get("characters")
    if isinstance(chars, dict):
        chars = list(chars.values())
    if not isinstance(chars, list) or not chars:
        return
    referenced_ids, _ = episode_registry_reference_ids(root, ep)
    if not referenced_ids:
        return  # 本集还没引用任何登记角色（如出图前早期）——不前置提醒
    unpinned: List[str] = []
    for c in chars:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "").strip()
        if cid not in referenced_ids:
            continue
        scope = f"{c.get('tier') or ''} {c.get('scope') or ''}"
        if not _CORE_SCOPE_RE.search(scope):
            continue  # 仅核心长线角色前置高档
        forms = c.get("forms") if isinstance(c.get("forms"), list) else []
        if any(str((fm or {}).get("anchor_sha") or "").strip() for fm in forms if isinstance(fm, dict)):
            continue  # 已有任一 form 钉死
        names = [n.strip() for n in str(c.get("name") or "").replace("／", "/").split("/") if n.strip()]
        unpinned.append(f"{names[0] if names else cid}({cid})")
    if unpinned:
        add(BLOCK, "锚点钉死", identity_registry_path(root),
            f"核心长线角色未启用定妆锚点钉死：{('、'.join(unpinned))}——这些脸被多集引用，"
            "重刷/重生成定妆若换脸则下游每集静默继承（anchor_sha 未登记 = check_anchor_fingerprints 跳过）。"
            "对其 front 定妆图 `image_qc --pin-anchor CHAR_xx/形态` 钉死后再付费出图，"
            "重制后用 n2d-update media 复核跨集引用集。",
            return_to_stage="image")

def check_expression_anchors(root: str, ep: str) -> None:
    """表情库跨集共享锁定（治"第2集的怒和第5集的怒各画各的"）：form 若显式登记 `expression_anchors`
    （opt-in，每条 `{emotion, path, self_check_passed?, anchor_sha?}`），则该情绪锚必须存在、过自检、未被悄改——
    否则跨集同情绪近景就没有同源母图可派生 → BLOCK。

    **纯 opt-in**：未登记 `expression_anchors` 的 form 跳过（向后兼容）。
    写入口：`image_qc.py <root> --finalize-expr CHAR_xx/形态/情绪`（落自检真值 + 钉 sha）。"""
    reg = load_json(identity_registry_path(root))
    if not isinstance(reg, dict):
        return
    reg_path = identity_registry_path(root)
    for c in (reg.get("characters") or []):
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "").strip()
        for fm in (c.get("forms") or []):
            if not isinstance(fm, dict):
                continue
            anchors = fm.get("expression_anchors")
            if not isinstance(anchors, list):
                continue
            form_name = str(fm.get("form") or "").strip()
            for a in anchors:
                if not isinstance(a, dict):
                    continue
                emotion = str(a.get("emotion") or "?").strip()
                rel = str(a.get("path") or "").strip()
                label = f"{cid}/{form_name}#{emotion}" if form_name else f"{cid}#{emotion}"
                full = os.path.join(root, rel) if rel else ""
                if not rel or not os.path.isfile(full):
                    add(BLOCK, "共享定妆", reg_path,
                        f"表情锚 `{label}` 已登记但图缺失（{rel or '未填 path'}）——跨集同情绪近景无同源母图，"
                        "各集各画各的=情绪一致性崩；补出该情绪脸部特写并 `image_qc --finalize-expr`。")
                    continue
                if a.get("self_check_passed") is False:
                    add(BLOCK, "共享定妆", reg_path,
                        f"表情锚 `{label}` 未过落档自检（self_check_passed=false）——脏情绪锚是跨集同情绪近景的源头；"
                        "先过自检并 `image_qc --finalize-expr` 再付费出图。")
                    continue
                exp = str(a.get("anchor_sha") or "").strip()
                if exp:
                    actual = _sha256_file(full)
                    if actual != exp:
                        add(BLOCK, "共享定妆", reg_path,
                            f"表情锚 `{label}` 被改动：磁盘 sha256 与登记 `anchor_sha` 不一致——一漂则所有引用集同情绪近景换脸；"
                            "有意更新就重出依赖镜后 `image_qc --finalize-expr` 重钉，否则恢复原图。")

def check_expression_span_frame_contract(root: str, ep: str) -> None:
    """出视频前置（脸被表情带着重画的头号根因·机检闸门）：跨情绪近景必须走首尾双帧只插值工艺。

    `prompt_format.md`「近景大表情变化类 Clip」铁律：表情跨度=大（平静→爆哭/隐忍→暴怒）的 CU/MCU/反打镜
    若靠单首帧让模型自由生成中间表情，脸型/五官比例会随表情拉伸漂移、剪起来像换了个人。此前
    `表情跨度` 只活在总览风险表里、是人读自检——gate 看不见、拦不住。本检查把它结构化（storyboard
    `continuity.expression_span` ∈ {微,中,大}）后机检：

      · expression_span 值非法（非 微/中/大）→ BLOCK（typo 防呆）；
      · expression_span=大 且镜为近景/特写/反打 → 必须 need_endframe=true（有止表情尾帧可插值），
        否则 BLOCK——单首帧扛不住跨情绪表情；
      · expression_span=大 但镜非近景 → WARN（远景大表情风险低，或景别标错，提示复核）。

    纯 opt-in：`continuity.expression_span` 缺失=未启用追踪→跳过（现有 demo/未标镜不误伤），与
    `self_check_passed`、`midframe_default` 同款门控。路由后端能否真消费这条尾帧（frames2video/
    multiframe）由 `check_route_frame_capability` 对高风险镜升 BLOCK 兜，本检查不重复报。"""
    data = load_json(storyboard_path(root, ep))
    if not isinstance(data, dict) or not isinstance(data.get("clips"), list):
        return  # storyboard 缺失/损坏由 check_storyboard_contract 负责
    for i, clip in enumerate(data["clips"], 1):
        if not isinstance(clip, dict):
            continue
        cont = clip.get("continuity")
        if not isinstance(cont, dict):
            continue
        span = cont.get("expression_span")
        if span in (None, ""):
            continue  # opt-in：未声明=不追踪
        loc = f"{storyboard_path(root, ep)} clip#{i}"
        if span not in EXPRESSION_SPAN_VALUES:
            add(BLOCK, "表情一致性", loc,
                f"continuity.expression_span={span!r} 非法；必须是 {'/'.join(EXPRESSION_SPAN_VALUES)} 之一"
                "（大=跨情绪如 平静→爆哭/隐忍→暴怒）。")
            continue
        if span != EXPRESSION_SPAN_BIG:
            continue
        if not _clip_is_closeup(clip):
            add(WARN, "表情一致性", loc,
                "expression_span=大 但本镜景别未识别为近景/特写/反打——跨情绪大表情通常是脸戏；"
                "若确为远景/空镜风险较低，否则复核景别或下调跨度档。", return_to_stage="script_stage2")
            continue
        if cont.get("need_endframe") is not True:
            add(BLOCK, "表情一致性", loc,
                "expression_span=大 的近景/特写/反打镜必须 need_endframe=true 走「首尾双帧只插值」"
                "（首=起表情、尾=止表情同源定妆，mode=frames2video，让模型只插值表情肌肉、不自由重画脸）；"
                "缺尾帧=单首帧硬扛跨情绪表情=脸型/五官比例随表情漂移。补 endframe_png（止表情定妆，"
                "如 `镜头N_expr_end.png` 或 reference_group.expressions 对应情绪图）或用 MCU/OTS/侧脸保真实现后下调跨度档。",
                return_to_stage="image")

def check_core_expression_anchor_coverage(root: str, ep: str) -> None:
    """表情库覆盖闸（把表情锚提到与脸锚同级·付费出视频前强制回连表情库）。

    脸锚有两层防线：`check_anchor_fingerprints`（登记后校漂·BLOCK）+ `check_core_anchor_pinning`
    （核心长线角色「该钉没钉」前置提醒·WARN）。表情锚此前只有前者（`check_expression_anchors`
    登记后校漂），缺「该建没建」的前置闸——于是「第2集的怒和第5集的怒各画各的」只能靠人自觉建库。
    本检查补齐缺失的那层，并在「大表情近景 + 核心长线角色 + 即将付费出视频」这一**确定跨集情绪漂移**
    场景把档位从 WARN 升到 BLOCK（对齐 carries_identity 的 spend 闸思路）：

      · 本集存在跨情绪大表情近景镜（expression_span=大 + 近景/特写/反打），且这些镜引用了某**核心
        长线角色**（_CORE_SCOPE_RE 命中 tier/scope），而该角色在 identity_registry 的所有 form 的
        `expression_anchors` 皆空（=没建表情库）→ BLOCK：必须先建表情库并把镜头尾帧回连到表情锚。

    纯 opt-in：本集没有任何 expression_span=大 的镜（现有 demo/未标镜）= 项目未启用表情跨度追踪 → 跳过，
    与 `check_expression_span_frame_contract`、anchor_sha 全家门控一致。非核心/单元角色不前置 BLOCK
    （对齐 n2d-image「ROI 驱动」，避免误伤一次性配角）。登记后表情锚是否被悄改/未过自检由
    `check_expression_anchors` 负责，本检查只补「核心角色大表情近景但表情库为空」这一覆盖缺口，不重复报。"""
    big_clips = _episode_big_expression_closeup_clips(root, ep)
    if not big_clips:
        return  # opt-in：本集无大表情近景=未启用追踪
    reg = load_json(identity_registry_path(root))
    if not isinstance(reg, dict):
        return
    chars = reg.get("characters")
    if isinstance(chars, dict):
        chars = list(chars.values())
    if not isinstance(chars, list):
        return
    core_info: Dict[str, Dict[str, Any]] = {}  # cid -> {name, has_expr}
    for c in chars:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "").strip()
        if not cid or not _CORE_SCOPE_RE.search(f"{c.get('tier') or ''} {c.get('scope') or ''}"):
            continue  # 仅核心长线角色前置高档
        has_expr = any(
            isinstance(fm, dict) and isinstance(fm.get("expression_anchors"), list) and fm.get("expression_anchors")
            for fm in (c.get("forms") or [])
        )
        names = [n.strip() for n in str(c.get("name") or "").replace("／", "/").split("/") if n.strip()]
        core_info[cid] = {"name": names[0] if names else cid, "has_expr": has_expr}
    if not core_info:
        return
    missing: Dict[str, List[int]] = {}  # cid -> [clip 序号]
    for idx, clip in big_clips:
        for cid in _clip_character_ids(clip):
            info = core_info.get(cid)
            if info and not info["has_expr"]:
                missing.setdefault(cid, []).append(idx)
    reg_path = identity_registry_path(root)
    for cid, clip_idxs in sorted(missing.items()):
        info = core_info[cid]
        shown = "、".join(f"clip#{n}" for n in clip_idxs[:8])
        add(BLOCK, "表情一致性", reg_path,
            f"核心长线角色 `{info['name']}({cid})` 出现在本集跨情绪大表情近景镜（{shown}）但未建表情库"
            "（identity_registry 该角色所有 form 的 expression_anchors 皆空）——跨集同情绪近景将各画各的、"
            "情绪一致性崩（脸随表情重画的最贵漂移）。先为该情绪出脸部特写定妆并 "
            "`python3 skills/n2d-image/scripts/image_qc.py <作品根> --finalize-expr CHAR_xx/形态/情绪` "
            "落档钉锚，再把这些镜的止表情尾帧回连到表情锚（reference_group.expressions/expression_anchors 同源派生），"
            "让所有集同情绪近景从同一锚 image2image 派生后再付费出视频。",
            return_to_stage="image")

__all__ = [
    'check_input_frame_qc',
    'check_identity_handoff_inheritance',
    'check_identity_registry',
    'check_identity_adapter_matrix',
    'check_production_core_identity_lock',
    'check_route_identity_readiness',
    'check_stylized_face_encoder_policy',
    'check_character_backend_pin',
    'check_anchor_fingerprints',
    'check_core_anchor_pinning',
    'check_expression_anchors',
    'check_expression_span_frame_contract',
    'check_core_expression_anchor_coverage',
]
