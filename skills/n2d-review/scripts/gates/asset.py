#!/usr/bin/env python3
"""gates/asset.py — 资产/服装/道具登记·共享图索引·分镜引用资产族

按证据族从 gate.py 拆出的 check_ 闸（增量3）。从 gate_core 取共享基座，避免与 gate.py 循环导入；
gate.py `from gates.asset import *` 回灌，run()/按名自省助手照常解析；成员经校验 call-graph-closed。
"""
from gate_core import *  # noqa: F401,F403
from gate_core import (
    _COSTUME_NON_FACE,
    _FINALIZE_ASSET_RE,
    _FINALIZE_CHAR_RE,
    _asset_has_any,
    _asset_must_not_have_terms,
    _costume_stem,
    _declares_evolution_derivation,
    _evolution_derived_forms,
    _field_is_missing,
    _finalize_evidence,
    _has_any,
    _has_halfbody_crop_rule,
    _has_positive_prompt_heading,
    _has_prop_structure_rule,
    _has_standard_character_turnaround,
    _headline,
    _identity_reference_exists,
    _identity_reference_item_path,
    _is_core_location_asset,
    _is_restricted_partial_prompt_section,
    _is_weapon_like_asset,
    _section_is_derived_form,
    _uses_halfbody_outfit_ref,
    _validate_scene_atlas,
    _validate_scene_dna,
    _validate_wardrobe_profile,
    _validate_weapon_profile,
    _weapon_profile,
)
from image_prompt_compiler import lint_compiled_section as lint_compiled_image_section  # noqa: E402

def check_costume_registry_reconcile(root: str) -> None:
    """定妆库 ↔ identity_registry 双向对账。

    face 机检按文件名 glob 发现定妆图、identity_registry 按登记的 reference_group 路径锁脸——两套各写各的，
    若 registry 登记 `定妆_X_人皮态.png` 但磁盘只有 `定妆_X.png`，崩脸机检可能测的根本不是 registry 锁的那张。
    本检查对账：① registry 登记但磁盘缺的参考；② 属于已登记角色、磁盘有却没进任何 reference_group 的定妆变体（orphan）。
    场景定妆（不属任何角色）天然不匹配角色 stem，不误报。
    """
    reg = load_json(identity_registry_path(root))
    if not isinstance(reg, dict):
        return  # 缺 registry：check_identity_registry 已把关
    registered_rel: set = set()
    for char in reg.get("characters") or []:
        for form in (char.get("forms") or []):
            rg = form.get("reference_group")
            if not isinstance(rg, dict):
                continue
            for val in rg.values():
                for v in (val if isinstance(val, list) else [val]):
                    rel = _identity_reference_item_path(v)
                    if rel:
                        registered_rel.add(rel)
    if not registered_rel:
        return
    registered_base = {os.path.basename(p) for p in registered_rel}
    char_stems = {_costume_stem(b) for b in registered_base}
    # ① registry 登记但磁盘缺（三视图/设定表/表情 不强求落盘）
    for rel in sorted(registered_rel):
        bn = os.path.basename(rel)
        if any(t in bn for t in _COSTUME_NON_FACE):
            continue
        if not os.path.isfile(os.path.join(root, rel)):
            add(WARN, "定妆对账", rel,
                f"identity_registry 登记的定妆参考 {rel} 磁盘缺失；补出该图或修 registry 路径，否则锁脸参考落空")
    # ② 已登记角色的 orphan 变体：磁盘有、属同一角色 stem、却没进 reference_group
    for p in sorted(glob.glob(os.path.join(shared_asset_path(root, "图片"), "定妆_*.png"))):
        bn = os.path.basename(p)
        if any(t in bn for t in _COSTUME_NON_FACE):
            continue
        if bn in registered_base:
            continue
        # 属已登记角色 = 文件名等于某角色 stem，或是其变体（stem_ 前缀）——任意变体后缀都能抓到
        if any(bn == stem + ".png" or bn.startswith(stem + "_") for stem in char_stems):
            add(WARN, "定妆对账", p,
                f"定妆图 {bn} 属已登记角色但未进 identity_registry 任何 reference_group；"
                f"face 机检会按文件名把它当参考、与 registry 锁的不是同一套 → 登记进 registry 或删除")

def check_asset_reference_registry(
    root: str,
    require_reference_assets: bool = False,
    required_asset_ids: Optional[set] = None,
) -> None:
    """Validate reusable non-character scene/prop/outfit/vfx asset registry."""
    p = asset_registry_path(root)
    data = load_json(p)
    if not isinstance(data, dict):
        add(BLOCK, "资产引用注册层", p, "缺少或无法解析 asset_registry.json；关键场景/道具/武器/服装/VFX 必须升级为 LOC_/PROP_/WEAPON_/OUTFIT_/VFX_ 资产引用注册层")
        return
    if data.get("kind") != ASSET_REFERENCE_REGISTRY_KIND:
        add(BLOCK, "资产引用注册层", p, f"kind 必须是 {ASSET_REFERENCE_REGISTRY_KIND}")
    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        add(BLOCK, "资产引用注册层", p, "assets[] 缺失或为空；关键场景/道具/武器/服装/VFX 必须登记")
        return

    seen_ids = set()
    for idx, asset in enumerate(assets, 1):
        loc = f"{p} asset#{idx}"
        if not isinstance(asset, dict):
            add(BLOCK, "资产引用注册层", loc, "asset 必须是对象")
            continue
        for key in ASSET_REFERENCE_REQUIRED_FIELDS:
            if _field_is_missing(asset, key):
                add(BLOCK, "资产引用注册层", loc, f"asset 缺字段：{key}")

        asset_id = str(asset.get("id", "")).strip()
        asset_type = str(asset.get("type", "")).strip().lower()
        strict_references = required_asset_ids is None or asset_id in required_asset_ids
        if asset_id:
            if asset_id in seen_ids:
                add(BLOCK, "资产引用注册层", loc, f"重复 asset id：{asset_id}")
            seen_ids.add(asset_id)
        expected_prefix = ASSET_REFERENCE_TYPE_PREFIX.get(asset_type)
        if asset_type and not expected_prefix:
            add(BLOCK, "资产引用注册层", loc, f"未知 type「{asset_type}」；允许：{', '.join(sorted(ASSET_REFERENCE_TYPE_PREFIX))}")
        elif expected_prefix and asset_id:
            prefixes = expected_prefix if isinstance(expected_prefix, tuple) else (expected_prefix,)
            if not asset_id.startswith(prefixes):
                add(BLOCK, "资产引用注册层", loc, f"type={asset_type} 的 id 必须以 {' / '.join(prefixes)} 开头")

        if asset_type in {"outfit", "costume"}:
            _validate_wardrobe_profile(asset.get("outfit_profile"), loc, field_name="outfit_profile")

        if asset_type in ASSET_WEAPON_TYPES:
            _validate_weapon_profile(asset, loc, required=True)
        elif asset_type == "prop" and _is_weapon_like_asset(asset):
            # 铁律 B11（2026-06-27）：武器型道具的 weapon_profile demo 也必需（不随 profile 降级）。
            _validate_weapon_profile(asset, loc, required=True)
        elif asset_type in {"vfx", "effect"} and _is_weapon_like_asset(asset):
            profile, _profile_name = _weapon_profile(asset)
            if profile:
                _validate_weapon_profile(asset, loc, required=False)
            else:
                add(
                    WARN,
                    "主角装备库",
                    loc,
                    "该 VFX/法术资产看起来承担武器/法宝识别功能；若它是实体武器或主角本命法宝，请拆成 "
                    "WEAPON_xx 实体资产 + VFX_xx 光效表现，并在角色 signature_equipment 中绑定。",
                )

        # 深度一致性检查：道具生命周期与所有权
        if asset_type == "prop":
            for key in ASSET_PROP_REQUIRED_FIELDS:
                if _field_is_missing(asset, key):
                    add(BLOCK, "资产引用注册层", loc, f"关键道具资产缺生命周期字段：{key}")

        # 深度一致性检查：场景空间布局
        if asset_type in ("scene", "location"):
            for key in ASSET_SCENE_REQUIRED_FIELDS:
                if _field_is_missing(asset, key):
                    add(BLOCK, "资产引用注册层", loc, f"反复场景资产缺空间布局字段：{key}")
            _validate_scene_dna(asset, loc)
            # 铁律 B11（2026-06-27）：核心/高频场景的空间发布字段 demo 也必需（不随 profile 降级）。
            if _is_core_location_asset(asset):
                missing = [aliases[0] for aliases in ASSET_SCENE_RELEASE_FIELD_GROUPS if not _asset_has_any(asset, aliases)]
                if missing:
                    add(
                        BLOCK,
                        "空间/场面调度一致性",
                        loc,
                        "核心/高频 LOC 缺空间发布字段：" + ", ".join(missing) +
                        "；请补平面图、门窗方向、轴线规则和左右站位/screen_direction 规则，避免多集同场景门窗/站位/越轴漂移。",
                        return_to_stage="script_stage2",
                    )
                _validate_scene_atlas(asset, loc)

        reference_group = asset.get("reference_group")
        if not isinstance(reference_group, dict):
            add(BLOCK, "资产引用注册层", loc, "reference_group 必须是对象，至少含 primary")
        else:
            primary = _identity_reference_item_path(reference_group.get("primary"))
            if not primary:
                add(BLOCK, "资产引用注册层", loc, "reference_group.primary 缺失或为空")
            elif require_reference_assets and strict_references and not _identity_reference_exists(root, primary):
                add(BLOCK, "资产引用注册层", os.path.join(root, primary) if not os.path.isabs(primary) else primary, "reference_group.primary 路径不存在")
            alternates = reference_group.get("alternates", [])
            if alternates is not None and not isinstance(alternates, list):
                add(BLOCK, "资产引用注册层", loc, "reference_group.alternates 必须是列表")
            for rel in alternates or []:
                rel_s = _identity_reference_item_path(rel)
                if not rel_s:
                    add(BLOCK, "资产引用注册层", loc, "reference_group.alternates 存在空路径")
                elif require_reference_assets and strict_references and not _identity_reference_exists(root, rel_s):
                    add(BLOCK, "资产引用注册层", os.path.join(root, rel_s) if not os.path.isabs(rel_s) else rel_s, "reference_group.alternates 路径不存在")

        constraints = asset.get("constraints")
        if not isinstance(constraints, dict) or not constraints:
            add(BLOCK, "资产引用注册层", loc, "constraints 必须是非空对象；不能只登记名字 and 图片")
        else:
            if asset_type in {"scene", "location"}:
                if not any(k in constraints for k in ("layout", "axis", "light_anchor", "structure")):
                    add(BLOCK, "资产引用注册层", loc, "场景资产 constraints 必须锁 layout/axis/light_anchor/structure 至少一项")
                if not (constraints.get("lighting_signature") or asset.get("lighting_signature")):
                    add(WARN, "资产引用注册层", loc, "建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变")

            if asset_type in {"prop", *ASSET_WEAPON_TYPES} and "structure" not in constraints:
                add(BLOCK, "资产引用注册层", loc, "道具/武器资产 constraints 必须锁 structure，避免壶嘴/刀刃/剑柄/剑鞘/镜面等部件幻觉")
            name_blob = f"{asset.get('name', '')}\n{json.dumps(constraints, ensure_ascii=False)}"
            if asset_type == "prop" and _has_any(name_blob, ("铜镜", "赐死", "托盘", "毒酒", "碎瓷", "匕首", "白绫")) and not _has_any(name_blob, (
                "单镜面", "唯一", "数量", "件数", "短颈圆口", "无侧嘴", "无斜嘴", "无双口", "一柄一刃", "同一只",
            )):
                add(BLOCK, "资产引用注册层", loc, "关键道具 constraints 未写结构唯一性；铜镜/托盘/毒酒/碎瓷必须锁数量与部件")
            must_not_terms = _asset_must_not_have_terms(asset)
            if asset_type == "prop" and _has_any(name_blob, ("毒酒", "酒瓶", "瓷瓶", "药瓶", "瓶", "酒盏", "赐死")):
                no_spout_terms = ("壶嘴", "侧嘴", "斜嘴", "喷口", "茶壶嘴", "出水口", "嘴")
                if not any(term in must_not_terms for term in no_spout_terms):
                    add(
                        BLOCK,
                        "资产引用注册层",
                        loc,
                        "瓶/酒/药类关键道具必须在 constraints.must_not_have（或 asset.must_not_have）登记"
                        "壶嘴/侧嘴/喷口/出水口等禁形，避免把酒瓶生成茶壶嘴。",
                    )
            if "must_not_have" in constraints or "must_not_have" in asset:
                if not must_not_terms:
                    add(BLOCK, "资产引用注册层", loc, "must_not_have 必须是非空字符串/列表，不能留空")

        drift_forbidden = asset.get("drift_forbidden")
        if not isinstance(drift_forbidden, list) or not drift_forbidden:
            add(BLOCK, "资产引用注册层", loc, "drift_forbidden 必须是非空列表")

def check_referenced_assets_finalized(root: str, ep: str) -> None:
    """付费出图前置·机器可读 finalize 闸门（被引用即必需机器证据）：

    - 引用了显式标 `self_check_passed=false` 的脏定妆/资产 → BLOCK（脏锚点下游每镜继承）。
    - **被引用即必需**：一旦项目启用了 finalize/锚点追踪（任一 form/asset 登记过 `self_check_passed` 或 `anchor_sha`），
      本集逐镜引用的、且确属本 registry 的共享定妆/资产，**必须**有机器可读落档证据（self_check_passed=true 或 anchor_sha）；
      仅靠人读 ✅ 或干脆没登记 = 自断言/漏登记，**缺证据即 BLOCK**——堵住「给一部分置 true、其余留空就静默放行」的洞。

    **adoption-gated**：完全没启用追踪的项目（现有作品/先出视频 demo，registry 无任何 self_check_passed/anchor_sha）
    → 跳过，保持 00_索引 人读 ✅ 的既有流程，不突然阻断。"""
    all_keys, evidence, dirty = _finalize_evidence(root)
    if not (evidence or dirty):
        return  # 未启用机器 finalize/锚点追踪：向后兼容，不强加
    shots_md = os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")
    try:
        text = open(shots_md, encoding="utf-8").read()
    except Exception:
        return  # 逐镜 prompt 未写：check_image_prompt_overview 等各自负责
    referenced_chars = set(_FINALIZE_CHAR_RE.findall(text))
    explicit_char_bases = {r.split("/", 1)[0] for r in referenced_chars if "/" in r}
    referenced_chars = {
        r for r in referenced_chars
        if "/" in r or r not in explicit_char_bases
    }
    referenced = referenced_chars | set(_FINALIZE_ASSET_RE.findall(text))

    def _resolve(rid: str, pool: set) -> bool:
        base = rid.split("/")[0]
        if rid in pool:
            return True
        # 裸 CHAR_xx 引用 → 命中其任一形态键
        return rid == base and any(k == base or k.startswith(base + "/") for k in pool)

    dirty_refs: List[str] = []
    missing_refs: List[str] = []
    for rid in sorted(referenced):
        if not _resolve(rid, all_keys):
            continue  # 不属本 registry（typo/未登记类型）→ unknown_char_id/unknown_asset_id 等别的检查负责
        if _resolve(rid, dirty):
            dirty_refs.append(rid)
        elif not _resolve(rid, evidence):
            missing_refs.append(rid)
    for rid in dirty_refs:
        add(BLOCK, "共享定妆", shots_md,
            f"本集逐镜引用了未过落档自检的共享定妆/资产 `{rid}`（registry `self_check_passed=false`）——"
            "脏定妆是锚点，脸/结构漂了下游每镜继承；先过自检并把该项置 true（或人工复核后 `image_qc --mark-finalized`），再付费出图。")
    for rid in missing_refs:
        add(BLOCK, "共享定妆", shots_md,
            f"项目已启用 finalize 追踪，但本集引用的共享定妆/资产 `{rid}` 没有任何机器可读落档证据"
            "（既无 `self_check_passed=true` 也无 `anchor_sha`）——被引用即必需机器证据：人读 ✅/没登记都不算数，"
            "先过落档自检 `image_qc --mark-finalized`（角色 form 默认顺带钉 `anchor_sha` 机器证据）再付费出图。")

def check_common_image_prompts(root: str) -> None:
    prompt_dir = shared_asset_path(root, "prompt")
    if not os.path.isdir(prompt_dir):
        add(BLOCK, "共享定妆", prompt_dir, "缺共享定妆 prompt 目录")
        return
    derived_forms = _evolution_derived_forms(root)
    selection = image_backend_adapter.current_image_backend_selection(root)
    expected_backend = selection.get("backend") or selection.get("access")
    allowed_tasks_by_file = {
        "角色定妆.md": ("character_catalog", "style_anchor"),
        "场景定妆.md": ("scene_asset",),
        "道具定妆.md": ("prop_asset",),
        "法宝定妆.md": ("prop_asset",),
        "特效定妆.md": ("prop_asset",),
    }
    for filename in ("角色定妆.md", "场景定妆.md", "道具定妆.md", "法宝定妆.md", "特效定妆.md"):
        p = os.path.join(prompt_dir, filename)
        if not os.path.isfile(p):
            continue
        text = open(p, encoding="utf-8").read()
        sections = re.findall(r"(?ms)^##\s+.*?(?=^##\s+|\Z)", text)
        for i, sec in enumerate(sections, 1):
            name = _headline(sec, f"{filename} block#{i}")
            loc = f"{p} {name}"
            compiled_audit = lint_compiled_image_section(
                sec,
                expected_backend=expected_backend,
                allowed_tasks=allowed_tasks_by_file.get(filename),
            )
            for code in compiled_audit.get("errors") or []:
                add(
                    BLOCK,
                    "image prompt compiler",
                    loc,
                    f"共享资产编译图片请求结构错误：{code}。请重新运行 n2d-image image_prompt_pack.py，完整合同不得直接提交。",
                    return_to_stage="image_prompt",
                )
            for code in compiled_audit.get("warnings") or []:
                add(WARN, "image prompt compiler", loc, f"共享资产编译图片请求可进一步精简：{code}")
            if "目标存档" not in sec:
                add(BLOCK, "共享定妆", loc, "缺目标存档；共享资产无法归档追踪")
            if not _has_positive_prompt_heading(sec, "中文"):
                add(BLOCK, "共享定妆", loc, "缺正向 prompt（中文）")
            if not _has_positive_prompt_heading(sec, "英文"):
                add(BLOCK, "共享定妆", loc, "缺正向 prompt（英文）")
            if "负向 prompt" not in sec:
                add(BLOCK, "共享定妆", loc, "缺负向 prompt")
            if "检查清单（定妆自查" not in sec:
                add(BLOCK, "共享定妆", loc, "缺定妆提交前检查清单")
            if "自检（生成后逐张过" not in sec and "**自检**" not in sec:
                add(BLOCK, "共享定妆", loc, "缺生成后落档自检段")
            if filename == "道具定妆.md" and not _has_prop_structure_rule(sec):
                add(BLOCK, "道具结构", loc, "道具定妆缺关键道具结构唯一性闸门；需锁唯一圆口/短颈、无侧嘴/斜嘴/双口/额外开口、多刃/多镜面/件数错等，避免道具结构幻觉")
            if filename == "角色定妆.md":
                if "身份注册" not in sec and "identity_registry" not in sec:
                    add(BLOCK, "资产身份注册层", loc, "角色定妆缺身份注册字段；必须指向 `出图/共享/identity_registry.json` 对应 characters[].forms[]")
                restricted_partial = _is_restricted_partial_prompt_section(sec)
                if not restricted_partial:
                    if "角色定妆组" not in sec:
                        add(BLOCK, "角色一致性", loc, "角色定妆缺定妆组说明；人物角色不能只靠单张正脸")
                    if not _has_standard_character_turnaround(sec):
                        add(BLOCK, "角色定妆基础包", loc,
                            "人物定妆基础包必须写齐：正面主参考 + 45°参考 + 侧面参考 + 背面参考 + 半身/全身服装参考 + "
                            "脸部特写/同源表情参考 + `定妆_<角色>_三视图.png` 人审拼版。"
                            "完整表情组、动作参考、主体库/LoRA 是风险升档项，不替代基础包。")
                if _uses_halfbody_outfit_ref(sec) and not _has_halfbody_crop_rule(sec):
                    add(BLOCK, "服装参考", loc, "半身服装参考必须写明：`定妆_<角色>_半身.png` 从已通过自检的正面主参考裁切并放大/重采样回项目所选画幅；人物主体居中、头身中线接近画面中线、左右留白基本均衡；不得新抽半身导致脸漂，也不得用白底/浅灰底/空白补下半截")
                if "锚点" not in sec:
                    add(BLOCK, "角色一致性", loc, "角色定妆缺锚点字段；下游每镜无锚可拼")
                # E 跨集成长派生形态：新境界/换装升级 form 的定妆必须从锚定/上一形态 image2image 派生，
                # 不得纯文生图重抽一张新脸——否则"同一个人变强"变成"换演员"，且下游每镜会忠实继承这张错脸。
                for df in derived_forms:
                    if _section_is_derived_form(sec, df) and not _declares_evolution_derivation(sec, df["anchor_form"]):
                        add(BLOCK, "跨集成长一致性", loc,
                            f"成长派生形态 `{df['char_name']}/{df['form']}` 的定妆未声明从锚定形态"
                            f"`{df['anchor_form']}` 的正脸/脸部特写 image2image 派生（evolution_profile 渐进升级）。"
                            "纯文生图重抽新脸=同一个人被换成另一张脸，下游每镜还会忠实继承错脸。"
                            "请写明：以 `定妆_<角色>_<锚定形态>` 正脸/脸部特写为母图做 image2image 派生，"
                            "只升级服装/法宝/气场/VFX，锁 identity_invariants（脸型/五官比例/发际线/标志疤痣）。",
                            return_to_stage="image")
                        break

def check_shared_image_index(root: str, ep: str) -> None:
    overview = os.path.join(root, "出图", ep, "prompt", "00_总览.md")
    index = shared_asset_path(root, "prompt", "00_索引.md")
    if not os.path.isfile(overview):
        add(BLOCK, "出图", overview, "缺本集出图总览")
        return
    if not os.path.isfile(index):
        add(BLOCK, "出图", index, "缺共享定妆索引")
        return
    common_dir = shared_asset_dir(root)
    index_text = open(index, encoding="utf-8").read()
    for ln in index_text.splitlines():
        if not ln.strip().startswith("|") or "✅" not in ln:
            continue
        paths = re.findall(r"`([^`]+\.png)`", ln)
        for rel in paths:
            if os.path.isabs(rel):
                full = rel
            else:
                # 路径可能是「作品根相对」(出图/共享/图片/定妆_X.png) 或「共享目录相对」(定妆_X.png)；两种都试
                cand_root = os.path.join(root, rel)
                cand_common = os.path.join(common_dir, rel)
                if os.path.exists(cand_root):
                    full = cand_root
                elif rel.startswith("_") and glob.glob(os.path.join(common_dir, f"*{rel}")):
                    continue
                else:
                    full = cand_common
            if not os.path.exists(full):
                add(BLOCK, "共享定妆", index, f"索引标 ✅ 但 PNG 不存在：{rel}")
    overview_text = open(overview, encoding="utf-8").read()
    missing = []
    in_table = False
    for ln in overview_text.splitlines():
        if ln.startswith("## 共享定妆就绪状态"):
            in_table = True
            continue
        if in_table and ln.startswith("## "):
            break
        if in_table and ln.strip().startswith("|") and "⬜" in ln:
            missing.append(ln.strip())
    if missing:
        add(BLOCK, "共享定妆", overview, f"本集引用的共享定妆仍有未完成项：{missing[0][:120]}")

def check_image_assets(root: str, ep: str) -> None:
    if not progress_fraction_done(root, ep, "出图"):
        add(BLOCK, "出图", os.path.join(root, "_进度.md"), "出图列未满，不能进入出视频")
    png_dir = os.path.join(root, "出图", ep, "图片")
    pngs = glob.glob(os.path.join(png_dir, "*.png"))
    if not pngs:
        add(BLOCK, "出图", png_dir, "本集没有分镜 PNG")

__all__ = [
    'check_costume_registry_reconcile',
    'check_asset_reference_registry',
    'check_referenced_assets_finalized',
    'check_common_image_prompts',
    'check_shared_image_index',
    'check_image_assets',
]
