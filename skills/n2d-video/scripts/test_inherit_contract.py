"""inherit_contract.py 回归测试——出图→出视频 视觉契约继承 Diff。

cd skills/n2d-video/scripts && python3 -m pytest test_inherit_contract.py
构造临时项目验证：一致→pass；轴线被改→block；视频缺字段→block；视频细化超集→pass；
色调漂移→warn 不拦；出图侧缺字段→提示不拦。格式按 demo
（创作区/制漫剧/本宫才是这皇宫最大的妖/出图/第1集/prompt/00_总览.md）的短标签 bullet 校准。
"""
import json
import os

import inherit_contract as ic

EP = "第1集"

# 出图侧契约（短标签，与 demo / gate.py --stage image 一致）
IMG_CONTRACT = """# 第1集 — 出图总览

## 本集视觉一致性契约
- 色调基线：冷青灰压暗；残烛暖金只照脸。
- 光位锚：冷宫寝殿=画左前 3000K 残烛暖主光；画右后冷月背光。
- 轴线：守床榻到门口横轴；沈念画左看画右，柳娘子画右看画左。
- 状态演进：沈念 Clip01-13 黑瞳常态；Clip14 起左腕疤裂暗金。
- 景别阶梯：LS建制 -> CU铜镜 -> MCU对峙 -> ECU金瞳。

## 其它段
- 无关内容
"""

# 视频侧逐字誊抄（长标签写法也应被认出）
VID_VERBATIM = """# 第1集 — 出视频总览

## 本集导演一致性契约
- 主色调：冷青灰压暗。
- 镜头语法：铺垫慢推。
- 轴线：守床榻到门口横轴。
- 剧情状态锁：金瞳不得提前。
- 场景状态：残烛常亮。

## 本集视觉一致性契约
- 色调基线：冷青灰压暗；残烛暖金只照脸。
- 场景光位锚：冷宫寝殿=画左前 3000K 残烛暖主光；画右后冷月背光。
- 场景轴线视线：守床榻到门口横轴；沈念画左看画右，柳娘子画右看画左。
- 角色状态演进：沈念 Clip01-13 黑瞳常态；Clip14 起左腕疤裂暗金。
- 景别阶梯：LS建制 → CU铜镜 → MCU对峙 → ECU金瞳。
"""


def _write_project(tmp_path, img_text, vid_text):
    root = tmp_path / "剧"
    for sub, text in (("出图", img_text), ("出视频", vid_text)):
        d = root / sub / EP / "prompt"
        d.mkdir(parents=True, exist_ok=True)
        (d / "00_总览.md").write_text(text, encoding="utf-8")
    return str(root)


def _report(root):
    p = os.path.join(root, "生产数据", f"contract_inheritance_{EP}.json")
    assert os.path.isfile(p), "必须落 JSON 报告"
    assert os.path.isfile(p[:-5] + ".md"), "必须落 MD 报告"
    return json.load(open(p, encoding="utf-8"))


def _write_image_qc(root, findings, fresh=True):
    """落一份 image_qc 报告（含 tone_light_contract 像素实测），供 #5 像素佐证消费。"""
    d = os.path.join(root, "生产数据", "image_qc", EP)
    os.makedirs(d, exist_ok=True)
    if fresh:
        fp = ic.artifact_fingerprint(root, [])  # 空文件集真指纹 = 永远 fresh
    else:
        fp = {"files": {"出图/第1集/图片/x.png": "deadbeef"}, "sha": "stale-sha-never-matches"}
    payload = {"kind": "n2d_image_qc", "inputs_fingerprint": fp,
               "tone_light_contract": {"findings": findings}}
    with open(os.path.join(d, f"image_qc_{EP}.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def test_pixel_contradiction_escalates_text_pass_to_warn(tmp_path):
    # #5：文本两侧全 pass，但 image_qc 实测首帧像素与申报色调矛盾 → 升档 warn（不再被文本 pass 掩盖）。
    root = _write_project(tmp_path, IMG_CONTRACT, VID_VERBATIM)
    _write_image_qc(root, [{"level": "warn", "code": "tone_warmth_contradiction",
                            "msg": "像素偏冷与暖契约相反"}])
    rc = ic.run(root, EP)
    rep = _report(root)
    assert rc == 0  # warn 不改退出码
    assert rep["verdict"] == "warn"
    assert rep["pixel_contract"]["fresh"] is True
    assert rep["pixel_contract"]["findings"]


def test_stale_image_qc_pixel_evidence_not_trusted(tmp_path):
    # #5 新鲜度护栏：image_qc 报告陈旧（出图后又重出）则不采纳旧像素证据，verdict 不被误升。
    root = _write_project(tmp_path, IMG_CONTRACT, VID_VERBATIM)
    _write_image_qc(root, [{"level": "warn", "code": "tone_warmth_contradiction", "msg": "x"}], fresh=False)
    ic.run(root, EP)
    rep = _report(root)
    assert rep["verdict"] == "pass"
    assert rep["pixel_contract"]["fresh"] is False
    assert not rep["pixel_contract"]["findings"]


def test_no_image_qc_report_is_clean_skip(tmp_path):
    # 无 image_qc 报告：像素佐证优雅跳过，不影响文本判定（pass 仍 pass）。
    root = _write_project(tmp_path, IMG_CONTRACT, VID_VERBATIM)
    assert ic.run(root, EP) == 0
    rep = _report(root)
    assert rep["verdict"] == "pass"
    assert rep["pixel_contract"]["available"] is False


def test_identical_contract_passes(tmp_path):
    # 逐字一致（标点/箭头/标签长短写差异归一化后不算漂移）→ exit 0 全 pass
    root = _write_project(tmp_path, IMG_CONTRACT, VID_VERBATIM)
    assert ic.run(root, EP) == 0
    rep = _report(root)
    assert rep["verdict"] == "pass"
    assert rep["summary"]["block"] == 0 and rep["summary"]["warn"] == 0
    assert {r["field"] for r in rep["fields"]} == set(ic.VISUAL_CONTRACT_FIELDS)


def test_axis_rewritten_blocks(tmp_path):
    # 轴线被誊抄改错（左右互换）→ block, exit 1
    vid = VID_VERBATIM.replace(
        "- 场景轴线视线：守床榻到门口横轴；沈念画左看画右，柳娘子画右看画左。",
        "- 场景轴线视线：守床榻到门口横轴；沈念画右看画左，柳娘子画左看画右。")
    root = _write_project(tmp_path, IMG_CONTRACT, vid)
    assert ic.run(root, EP) == 1
    rep = _report(root)
    assert rep["verdict"] == "block"
    axis = next(r for r in rep["fields"] if r["field"] == "场景轴线视线")
    assert axis["status"] == "block_drift" and axis["severity"] == "block"


def test_video_missing_field_blocks(tmp_path):
    # 视频侧契约丢了景别阶梯 → block, exit 1
    vid = "\n".join(ln for ln in VID_VERBATIM.splitlines() if not ln.startswith("- 景别阶梯"))
    root = _write_project(tmp_path, IMG_CONTRACT, vid)
    assert ic.run(root, EP) == 1
    rep = _report(root)
    ladder = next(r for r in rep["fields"] if r["field"] == "景别阶梯")
    assert ladder["status"] == "block_missing_in_video"


def test_video_missing_section_blocks(tmp_path):
    # 视频侧整节没誊抄（只有导演一致性契约，不可替代）→ 五字段全 block
    vid = VID_VERBATIM.split("## 本集视觉一致性契约")[0]
    root = _write_project(tmp_path, IMG_CONTRACT, vid)
    assert ic.run(root, EP) == 1
    rep = _report(root)
    assert all(r["severity"] == "block" for r in rep["fields"])


def test_video_refined_superset_passes(tmp_path):
    # 视频侧有意收紧/细化（包含出图侧原文 + 追加运动落地约束）→ pass_superset, exit 0
    vid = VID_VERBATIM.replace(
        "- 场景光位锚：冷宫寝殿=画左前 3000K 残烛暖主光；画右后冷月背光。",
        "- 场景光位锚：冷宫寝殿=画左前 3000K 残烛暖主光；画右后冷月背光。运镜中烛光只许摇曳不许改向，Clip14 后允许暗金补光。")
    root = _write_project(tmp_path, IMG_CONTRACT, vid)
    assert ic.run(root, EP) == 0
    rep = _report(root)
    anchor = next(r for r in rep["fields"] if r["field"] == "场景光位锚")
    assert anchor["status"] == "pass_superset" and rep["verdict"] == "pass"


def test_tone_drift_warns_not_blocks(tmp_path):
    # 色调基线改写（非光位/轴线）→ warn，exit 0 不拦
    vid = VID_VERBATIM.replace(
        "- 色调基线：冷青灰压暗；残烛暖金只照脸。",
        "- 色调基线：暖橙明亮基调，全程高调打光。")
    root = _write_project(tmp_path, IMG_CONTRACT, vid)
    assert ic.run(root, EP) == 0
    rep = _report(root)
    tone = next(r for r in rep["fields"] if r["field"] == "色调基线")
    assert tone["status"] == "warn_drift" and rep["verdict"] == "warn"


def test_state_progression_drift_blocks(tmp_path):
    # 角色状态演进被改写（提前泄露金瞳/伤）→ block, exit 1（2026-06 由 warn 升 block，剧情状态锁）
    vid = VID_VERBATIM.replace(
        "- 角色状态演进：沈念 Clip01-13 黑瞳常态；Clip14 起左腕疤裂暗金。",
        "- 角色状态演进：沈念 Clip01 起即金瞳暗金，全程左腕疤外露。")
    root = _write_project(tmp_path, IMG_CONTRACT, vid)
    assert ic.run(root, EP) == 1
    rep = _report(root)
    assert rep["verdict"] == "block"
    state = next(r for r in rep["fields"] if r["field"] == "角色状态演进")
    assert state["status"] == "block_drift" and state["severity"] == "block"


def test_state_progression_additive_leak_warns_not_passes(tmp_path):
    # 角色状态演进：视频侧含出图侧原文但**追加**了提前金瞳预兆（superset 却早泄状态）
    # → 不得 pass_superset，须 warn_drift 强制人工确认（exit 0 不拦，但醒目入账）
    vid = VID_VERBATIM.replace(
        "- 角色状态演进：沈念 Clip01-13 黑瞳常态；Clip14 起左腕疤裂暗金。",
        "- 角色状态演进：沈念 Clip01-13 黑瞳常态；Clip14 起左腕疤裂暗金；Clip05 闪现金瞳预兆。")
    root = _write_project(tmp_path, IMG_CONTRACT, vid)
    assert ic.run(root, EP) == 0          # warn 不拦
    rep = _report(root)
    assert rep["verdict"] == "warn"
    state = next(r for r in rep["fields"] if r["field"] == "角色状态演进")
    assert state["status"] == "warn_drift" and state["severity"] == "warn"


def test_light_anchor_additive_still_passes_superset(tmp_path):
    # 对照：场景光位锚追加收紧约束（含原文）→ 仍 pass_superset（光位是收紧型超集，安全放行）
    vid = VID_VERBATIM.replace(
        "- 场景光位锚：冷宫寝殿=画左前 3000K 残烛暖主光；画右后冷月背光。",
        "- 场景光位锚：冷宫寝殿=画左前 3000K 残烛暖主光；画右后冷月背光。运镜中烛光只许摇曳不许改向。")
    root = _write_project(tmp_path, IMG_CONTRACT, vid)
    assert ic.run(root, EP) == 0
    rep = _report(root)
    anchor = next(r for r in rep["fields"] if r["field"] == "场景光位锚")
    assert anchor["status"] == "pass_superset" and anchor["severity"] == "pass"


def test_upstream_missing_field_warns_not_blocks(tmp_path):
    # 出图侧本来就缺状态演进 → 提示但不拦（上游问题）；视频侧多写不构成 block
    img = "\n".join(ln for ln in IMG_CONTRACT.splitlines() if not ln.startswith("- 状态演进"))
    root = _write_project(tmp_path, img, VID_VERBATIM)
    assert ic.run(root, EP) == 0
    rep = _report(root)
    state = next(r for r in rep["fields"] if r["field"] == "角色状态演进")
    assert state["status"] == "upstream_missing" and state["severity"] == "warn"


def test_missing_files_precondition(tmp_path):
    # 任一侧 00_总览 不存在 → exit 2（前置缺失，区别于契约漂移）
    root = str(tmp_path / "空剧")
    os.makedirs(os.path.join(root, "出图", EP, "prompt"), exist_ok=True)
    assert ic.run(root, EP) == 2  # 两侧都缺（出图文件没写）
    open(os.path.join(root, "出图", EP, "prompt", "00_总览.md"), "w", encoding="utf-8").write(IMG_CONTRACT)
    assert ic.run(root, EP) == 2  # 只缺视频侧


# ── ①' generator↔parser 标签往返 sync（堵「字段标签一漂、该字段漂移机检静默失效」的 BLOCK 会漏洞） ──
# 背景：diff_contracts 逐 VISUAL_CONTRACT_FIELDS 比对，两侧都解析不出某字段时会被当成「两侧都缺」而
# 非「漂移」。若 generator 改了写进 00_总览.md 的标签措辞、而 parser 的 _FIELD_ALIASES 没跟上，该字段的
# 漂移检测就静默失效。下面把「generator 真实输出的两种标签风格 → parser 必须解析出全部 5 字段」钉成测试。

import n2d_contract_diff as cdiff  # noqa: E402  （inherit_contract 导入时已把 n2d/_lib 放进 sys.path）


def _parse_visual(text):
    sec = ic.extract_section(text)
    assert sec is not None, "必须能取到「本集视觉一致性契约」节"
    return ic.parse_contract_fields(sec)


def test_demo_shortlabel_generator_roundtrips_all_five_fields():
    # 出图侧 demo 短标签风格（光位锚/轴线/状态演进）必须往返解析出全部 5 个 canonical 字段且非空。
    fields = _parse_visual(IMG_CONTRACT)
    assert set(fields) == set(ic.VISUAL_CONTRACT_FIELDS), \
        f"短标签 generator 输出漏解析字段：{set(ic.VISUAL_CONTRACT_FIELDS) - set(fields)}（_FIELD_ALIASES 未跟上标签改写？）"
    assert all(fields[f].strip() for f in ic.VISUAL_CONTRACT_FIELDS), "解析出的字段值不得为空"


def test_video_longlabel_generator_roundtrips_all_five_fields():
    # 出视频侧长标签风格（场景光位锚/场景轴线视线/角色状态演进）同样必须往返解析出全部 5 字段。
    fields = _parse_visual(VID_VERBATIM)
    assert set(fields) == set(ic.VISUAL_CONTRACT_FIELDS), \
        f"长标签 generator 输出漏解析字段：{set(ic.VISUAL_CONTRACT_FIELDS) - set(fields)}"


def test_every_registered_alias_parses_to_its_canonical_field():
    # 别名表里登记的每个写法都必须真能被 _norm/_ALIAS_LOOKUP 认出（防「加了别名却没生效」）。
    for canon, aliases in cdiff._FIELD_ALIASES.items():
        for alias in aliases:
            parsed = ic.parse_contract_fields(f"- {alias}：占位值")
            assert parsed.get(canon) == "占位值", f"别名「{alias}」未解析回 canonical「{canon}」"


def test_block_and_no_superset_are_contract_field_subsets():
    # 与模块加载期断言同义，给一条可读的回归用例（字段重命名后 block 名单 typo 不至于无声降级）。
    assert set(cdiff.BLOCK_ON_DRIFT) <= set(ic.VISUAL_CONTRACT_FIELDS)
    assert set(cdiff.NO_AUTO_SUPERSET) <= set(ic.VISUAL_CONTRACT_FIELDS)


# ── ② 身份交接契约（出图首帧脸 → 出视频脸） ────────────────────────────────────

_ROUTES = json.dumps({"kind": "n2d_video_model_routes", "routes": [
    {"clip_id": "Clip_01", "identity_requirement": "reference_group"},
    {"clip_id": "Clip_02", "identity_requirement": "character_id_or_reference_group"},
    {"clip_id": "Clip_03", "identity_requirement": "none"},   # 空镜：不要求锁脸
]}, ensure_ascii=False)
_ROUTES_ONE = json.dumps({"kind": "n2d_video_model_routes", "routes": [
    {"clip_id": "Clip_01", "identity_requirement": "reference_group"},
]}, ensure_ascii=False)

_CLIP_LOCKED = """## Clip 01（时长 5.6s · 镜头 EP01_CLIP01）
**模型路由**：identity_requirement=reference_group。
**角色身份注册层**：CHAR_01/常态；参考组=出图/共享/图片/定妆_沈念_常态.png；reference_group=ready。

## Clip 02（时长 6.5s · 镜头 EP01_CLIP02）
**身份锁定约束**：CHAR_02/常态，character_id=KLG_001；脸部特写=定妆_柳娘子_脸部特写.png。

## Clip 03（时长 3.2s · 镜头 EP01_CLIP03）
空镜，无人物。
"""


def test_parse_named_character_routes_filters_none():
    named = ic.parse_named_character_routes(_ROUTES)
    assert [r["clip_id"] for r in named] == ["Clip_01", "Clip_02"]   # Clip_03 (none) 被过滤
    assert named[0]["clip_num"] == 1 and named[1]["clip_num"] == 2
    assert ic.parse_named_character_routes("{bad json") is None


def test_split_video_clip_blocks():
    blocks = ic.split_video_clip_blocks(_CLIP_LOCKED)
    assert set(blocks) == {1, 2, 3}
    assert "CHAR_01" in blocks[1]
    assert "空镜" in blocks[3]


def test_clip_block_locks_identity():
    assert ic.clip_block_locks_identity("**角色身份注册层**：CHAR_01/常态；定妆_沈念.png") is True
    assert ic.clip_block_locks_identity("identity lock: face_lock + reference_group") is True
    # 只喊锁身份没给锚 → False
    assert ic.clip_block_locks_identity("**身份锁定**：保持人物一致") is False
    # 有锚但没声明字段 → False
    assert ic.clip_block_locks_identity("镜头平移，背景定妆_冷宫.png") is False


def _write_with_video_prompts(tmp_path, routes=_ROUTES, clips=_CLIP_LOCKED):
    root = _write_project(tmp_path, IMG_CONTRACT, VID_VERBATIM)
    vp = os.path.join(root, "出视频", EP, "prompt")
    if routes is not None:
        open(os.path.join(vp, "video_model_routes.json"), "w", encoding="utf-8").write(routes)
    if clips is not None:
        open(os.path.join(vp, "01_clips.md"), "w", encoding="utf-8").write(clips)
    return root


def _write_storyboard(root, expression_span="大", need_endframe=True):
    d = os.path.join(root, "脚本", EP)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "storyboard.json"), "w", encoding="utf-8") as f:
        json.dump({
            "clips": [{
                "template": "dialogue_shot_reverse",
                "label": "CU 近景 大表情",
                "shots": [{"lens": "CU", "desc": "沈念从克制到暴怒"}],
                "continuity": {
                    "expression_span": expression_span,
                    "need_endframe": need_endframe,
                },
            }]
        }, f, ensure_ascii=False)


_MULTI_ANCHOR_OK = """## Clip 01（时长 5.6s · 镜头 EP01_CLIP01）
**首帧**：`出图/第1集/图片/Clip_01.png`
**尾帧**：`出图/第1集/图片/Clip_01_end.png`
**角色身份注册层**：CHAR_01/常态；reference_group=出图/共享/图片/定妆_沈念_常态.png；character_id=KLG_001。
**近景/反打身份锁定**：脸型、五官比例、眼距、鼻梁、下颌保持不变；发型发髻与标志配饰保持；服装配色保持。
**表情锚**（起→止）：中性→怒目，引用 expressions/定妆_沈念_表情_怒目.png。
**表情幅度**：大。
**锁脸不锁情**：只动面部肌肉，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤 must hold。
"""


def test_multiframe_identity_contract_passes_when_reference_group_and_invariants_present(tmp_path):
    root = _write_with_video_prompts(tmp_path, routes=_ROUTES_ONE, clips=_MULTI_ANCHOR_OK)
    _write_storyboard(root)
    img_prompt = os.path.join(root, "出图", EP, "prompt", "01_分镜出图.md")
    open(img_prompt, "w", encoding="utf-8").write("## Clip 01\n**资产身份注册层**：CHAR_01/常态；reference_group。\n")
    assert ic.run(root, EP) == 0
    rep = _report(root)
    assert rep["identity_handoff"]["findings"] == []


def test_multiframe_identity_contract_blocks_missing_reference_group(tmp_path):
    clips = _MULTI_ANCHOR_OK.replace("；reference_group=出图/共享/图片/定妆_沈念_常态.png", "")
    root = _write_with_video_prompts(tmp_path, routes=_ROUTES_ONE, clips=clips)
    assert ic.run(root, EP) == 1
    rep = _report(root)
    codes = {f["code"] for f in rep["identity_handoff"]["findings"]}
    assert "identity_anchor_reference_group_missing" in codes


def test_multiframe_identity_contract_blocks_reference_group_keyword_without_binding(tmp_path):
    clips = _MULTI_ANCHOR_OK.replace(
        "reference_group=出图/共享/图片/定妆_沈念_常态.png",
        "reference_group 保持一致",
    )
    root = _write_with_video_prompts(tmp_path, routes=_ROUTES_ONE, clips=clips)
    assert ic.run(root, EP) == 1
    rep = _report(root)
    codes = {f["code"] for f in rep["identity_handoff"]["findings"]}
    assert "identity_anchor_reference_group_missing" in codes


def test_multiframe_identity_contract_blocks_character_mismatch(tmp_path):
    root = _write_with_video_prompts(tmp_path, routes=_ROUTES_ONE, clips=_MULTI_ANCHOR_OK.replace("CHAR_01/常态", "CHAR_02/常态"))
    img_prompt = os.path.join(root, "出图", EP, "prompt", "01_分镜出图.md")
    open(img_prompt, "w", encoding="utf-8").write("## Clip 01\n**资产身份注册层**：CHAR_01/常态；reference_group。\n")
    assert ic.run(root, EP) == 1
    rep = _report(root)
    codes = {f["code"] for f in rep["identity_handoff"]["findings"]}
    assert "identity_anchor_character_mismatch" in codes


def test_multiframe_asset_only_clip_does_not_require_character_anchor(tmp_path):
    routes = json.dumps({"kind": "n2d_video_model_routes", "routes": [
        {"clip_id": "Clip_01", "identity_requirement": "character_id_or_reference_group"},
    ]}, ensure_ascii=False)
    clips = """## Clip 01（时长 5.6s · 空镜道具）
**首帧**：`出图/第1集/图片/Clip_01.png`
**尾帧**：`出图/第1集/图片/Clip_01_end.png`
**身份锁定**：无人物/道具空镜；character_id=none；reference_group=asset_registry.reference_group；face_lock=not_applicable。
**资产约束**：LOC_01、PROP_01。
"""
    root = _write_with_video_prompts(tmp_path, routes=routes, clips=clips)
    img_prompt = os.path.join(root, "出图", EP, "prompt", "01_分镜出图.md")
    open(img_prompt, "w", encoding="utf-8").write("## Clip 01\n**资产引用注册层**：LOC_01、PROP_01。\n")

    assert ic.run(root, EP) == 0
    rep = _report(root)
    assert rep["identity_handoff"]["findings"] == []


def _write_action_storyboard(root):
    d = os.path.join(root, "脚本", EP)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "storyboard.json"), "w", encoding="utf-8") as f:
        json.dump({"clips": [{
            "template": "spectacle_fight",
            "label": "MS 打斗 落地",
            "shots": [{"lens": "MS", "desc": "沈念腾空跃起劈砍后落地"}],
            "continuity": {"expression_span": "中", "need_endframe": False},
        }]}, f, ensure_ascii=False)


_CLIP_ACTION_NO_END = """## Clip 01（时长 5.6s · 镜头 EP01_CLIP01）
**首帧**：`出图/第1集/图片/Clip_01.png`
**角色身份注册层**：CHAR_01/常态；参考组=出图/共享/图片/定妆_沈念_常态.png；reference_group=ready。
"""


def test_action_beat_without_endframe_warns_not_blocks(tmp_path):
    root = _write_with_video_prompts(tmp_path, routes=_ROUTES_ONE, clips=_CLIP_ACTION_NO_END)
    _write_action_storyboard(root)
    assert ic.run(root, EP) == 0   # warn 不阻断
    rep = _report(root)
    codes = {f["code"] for f in rep["identity_handoff"]["findings"]}
    assert "action_beat_endframe_missing" in codes


def test_action_beat_with_endframe_no_finding(tmp_path):
    clips = _CLIP_ACTION_NO_END.replace(
        "**首帧**：`出图/第1集/图片/Clip_01.png`",
        "**尾帧**：`出图/第1集/图片/Clip_01_end.png`")
    root = _write_with_video_prompts(tmp_path, routes=_ROUTES_ONE, clips=clips)
    _write_action_storyboard(root)
    assert ic.run(root, EP) == 0
    rep = _report(root)
    codes = {f["code"] for f in rep["identity_handoff"]["findings"]}
    assert "action_beat_endframe_missing" not in codes


def test_big_expression_closeup_requires_expressions_and_expression_fields(tmp_path):
    clips = _MULTI_ANCHOR_OK.replace(
        "**表情锚**（起→止）：中性→怒目，引用 expressions/定妆_沈念_表情_怒目.png。\n"
        "**表情幅度**：大。\n",
        "",
    )
    root = _write_with_video_prompts(tmp_path, routes=_ROUTES_ONE, clips=clips)
    _write_storyboard(root)
    assert ic.run(root, EP) == 1
    rep = _report(root)
    codes = {f["code"] for f in rep["identity_handoff"]["findings"]}
    assert "big_expression_expressions_missing" in codes
    assert "big_expression_field_missing" in codes


def test_big_expression_closeup_expression_field_without_source_still_blocks(tmp_path):
    clips = _MULTI_ANCHOR_OK.replace(
        "**表情锚**（起→止）：中性→怒目，引用 expressions/定妆_沈念_表情_怒目.png。",
        "**表情锚**（起→止）：中性→怒目。")
    root = _write_with_video_prompts(tmp_path, routes=_ROUTES_ONE, clips=clips)
    _write_storyboard(root)
    assert ic.run(root, EP) == 1
    rep = _report(root)
    codes = {f["code"] for f in rep["identity_handoff"]["findings"]}
    assert "big_expression_expressions_missing" in codes


def test_identity_handoff_passes_when_all_clips_lock(tmp_path):
    root = _write_with_video_prompts(tmp_path)
    assert ic.run(root, EP) == 0
    rep = _report(root)
    assert rep["verdict"] == "pass"
    assert rep["identity_handoff"]["available"] is True
    assert rep["identity_handoff"]["checked"] == 2          # 只核验命名角色镜
    assert rep["identity_handoff"]["findings"] == []


def test_identity_handoff_blocks_unlocked_named_clip(tmp_path):
    # Clip 02 改成只喊锁身份没给锚 → block，整体 verdict=block, exit 1
    clips = _CLIP_LOCKED.replace(
        "**身份锁定约束**：CHAR_02/常态，character_id=KLG_001；脸部特写=定妆_柳娘子_脸部特写.png。",
        "**演出**：柳娘子入画反应，保持人物一致。")
    root = _write_with_video_prompts(tmp_path, clips=clips)
    assert ic.run(root, EP) == 1
    rep = _report(root)
    assert rep["verdict"] == "block"
    codes = {f["code"] for f in rep["identity_handoff"]["findings"]}
    assert "identity_lock_missing" in codes


def test_identity_handoff_blocks_missing_clip_prompt(tmp_path):
    # routes 里有 Clip_02 命名角色镜，但 01_clips.md 没写 Clip 02 块 → block
    clips = "## Clip 01（…）\n**角色身份注册层**：CHAR_01；定妆_沈念.png\n"
    root = _write_with_video_prompts(tmp_path, clips=clips)
    assert ic.run(root, EP) == 1
    rep = _report(root)
    codes = {f["code"] for f in rep["identity_handoff"]["findings"]}
    assert "identity_clip_prompt_missing" in codes


def test_identity_handoff_skipped_when_routes_absent(tmp_path):
    # 没有 video_model_routes.json（旧项目/未跑 router）→ 不拦，verdict 仍由视觉契约决定
    root = _write_project(tmp_path, IMG_CONTRACT, VID_VERBATIM)
    assert ic.run(root, EP) == 0
    rep = _report(root)
    assert rep["identity_handoff"]["available"] is False
    assert rep["identity_handoff"]["findings"] == []


# ── C 物料约束继承（场景/道具/特效逐镜交接 Diff） ───────────────────────────────

_IMG_CLIPS = """## Clip 01 EP01_CLIP01
**资产引用注册层**：`LOC_01` 冷宫寝殿；`PROP_01` 斑驳铜镜；锁 layout/axis/light_anchor。

## Clip 02 EP01_CLIP02
**资产引用注册层**：`LOC_01` 冷宫寝殿；`VFX_01` 暗金妖力脉冲；锁颜色拖尾。

## Clip 03 EP01_CLIP03
空镜，无注册资产。
"""

_VID_CLIPS_OK = """## Clip 01 EP01_CLIP01
**场面调度**：资产=LOC_01 冷宫寝殿 + PROP_01 斑驳铜镜；轴线不变。

## Clip 02 EP01_CLIP02
**场面调度**：资产=LOC_01 冷宫寝殿 + VFX_01 暗金妖力脉冲。

## Clip 03 EP01_CLIP03
空镜。
"""


def _write_clip_prompts(tmp_path, img_clips=_IMG_CLIPS, vid_clips=_VID_CLIPS_OK):
    root = _write_project(tmp_path, IMG_CONTRACT, VID_VERBATIM)
    (tmp_path / "剧" / "出图" / EP / "prompt" / "01_分镜出图.md").write_text(img_clips, encoding="utf-8")
    (tmp_path / "剧" / "出视频" / EP / "prompt" / "01_clips.md").write_text(vid_clips, encoding="utf-8")
    return root


def test_extract_asset_ids():
    ids = ic.extract_asset_ids("资产=LOC_01 冷宫 + PROP_01 铜镜；WEAPON_01 霜纹长剑；VFX_01 脉冲；OUTFIT_02 战袍")
    assert ids == {"LOC_01", "PROP_01", "WEAPON_01", "VFX_01", "OUTFIT_02"}
    assert ic.extract_asset_ids("LOC_HOUSHAN_QIANTAN + PROP_SHUI_TONG") == {"LOC_HOUSHAN_QIANTAN", "PROP_SHUI_TONG"}
    assert ic.extract_asset_ids("无注册资产的空镜") == set()


def test_asset_handoff_passes_when_assets_preserved(tmp_path):
    root = _write_clip_prompts(tmp_path)
    assert ic.run(root, EP) == 0
    rep = _report(root)
    assert rep["asset_handoff"]["available"] is True
    assert rep["asset_handoff"]["checked"] == 2          # Clip 01/02 带资产；Clip 03 空镜不计
    assert rep["asset_handoff"]["findings"] == []


def test_asset_handoff_warns_dropped_asset(tmp_path):
    # 出视频 Clip 02 把 VFX_01 丢了 id → warn（可能有意松引用），exit 0 不拦但醒目入账
    vid = _VID_CLIPS_OK.replace("资产=LOC_01 冷宫寝殿 + VFX_01 暗金妖力脉冲。", "资产=LOC_01 冷宫寝殿。")
    root = _write_clip_prompts(tmp_path, vid_clips=vid)
    assert ic.run(root, EP) == 0
    rep = _report(root)
    assert rep["verdict"] == "warn"
    f = next(f for f in rep["asset_handoff"]["findings"] if f["code"] == "asset_handoff_dropped")
    assert "VFX_01" in f["note"] and f["clip_id"] == "Clip_02" and f["severity"] == "warn"


def test_asset_handoff_blocks_missing_clip(tmp_path):
    # 出视频缺 Clip 02 整块 → asset_clip_prompt_missing block
    vid = "## Clip 01 EP01_CLIP01\n资产=LOC_01 + PROP_01\n"
    root = _write_clip_prompts(tmp_path, vid_clips=vid)
    assert ic.run(root, EP) == 1
    codes = {f["code"] for f in _report(root)["asset_handoff"]["findings"]}
    assert "asset_clip_prompt_missing" in codes


def test_asset_handoff_uses_firstframe_source_for_split_video_clips(tmp_path):
    # 出视频物理 Clip_05/09 可能来自出图逻辑 Clip03/Clip05；资产继承应按首帧来源，不按物理编号硬对齐。
    img = """## Clip 03 外门遗孤
**目标**：`出图/第1集/图片/Clip03_外门遗孤.png` `出图/第1集/图片/Clip03_外门遗孤_mid.png`
**资产引用注册层**：`LOC_WAIMEN_JIUYUAN`

## Clip 05 夜挑五趟
**目标**：`出图/第1集/图片/Clip05_夜挑五趟.png` `出图/第1集/图片/Clip05_夜挑五趟_mid.png`
**资产引用注册层**：`LOC_HOUSHAN_QIANTAN`、`PROP_SHUI_TONG`
"""
    vid = """## Clip 05（外门遗孤上）
**首帧**：`出图/第1集/图片/Clip03_外门遗孤.png`
**涉及资产**：LOC_WAIMEN_JIUYUAN

## Clip 09（夜挑五趟上）
**首帧**：`出图/第1集/图片/Clip05_夜挑五趟.png`
**涉及资产**：LOC_HOUSHAN_QIANTAN, PROP_SHUI_TONG
"""
    root = _write_clip_prompts(tmp_path, img_clips=img, vid_clips=vid)
    assert ic.run(root, EP) == 0
    rep = _report(root)
    assert rep["asset_handoff"]["checked"] == 2
    assert rep["asset_handoff"]["findings"] == []


def test_asset_handoff_skipped_when_clip_files_absent(tmp_path):
    # 旧项目无逐镜文件 → 不拦
    root = _write_project(tmp_path, IMG_CONTRACT, VID_VERBATIM)
    assert ic.run(root, EP) == 0
    assert _report(root)["asset_handoff"]["available"] is False


# ── 电影光学契约：镜头焦段 img→video 继承（A2·opt-in·warn-only） ──────────────

def test_diff_cinematic_focal_mismatch_warns():
    img = "## 本集真实电影感契约\n- 镜头焦段：85mm 长焦浅景深\n- 摄影基调：写实\n"
    vid = "## 本集真实电影感契约\n- 镜头焦段：24mm 广角\n- 摄影基调：写实\n"
    rows = ic.diff_cinematic_focal(img, vid)
    assert len(rows) == 1 and rows[0]["field"] == "镜头焦段" and rows[0]["severity"] == "warn"


def test_diff_cinematic_focal_match_passes_and_superset():
    img = "## 本集真实电影感契约\n- 镜头焦段：85mm 长焦\n"
    assert ic.diff_cinematic_focal(img, img)[0]["severity"] == "pass"
    # 视频侧细化（含原文）→ pass 超集
    vid = "## 本集真实电影感契约\n- 镜头焦段：85mm 长焦 浅景深奶油虚化\n"
    assert ic.diff_cinematic_focal(img, vid)[0]["severity"] == "pass"


def test_diff_cinematic_focal_absent_is_skipped():
    # 任一侧无真实电影感契约/焦段字段 → 不报（焦段 opt-in 不强求）
    img = "## 本集真实电影感契约\n- 镜头焦段：85mm\n"
    assert ic.diff_cinematic_focal(img, "## 本集基础视觉风格契约\n- 风格名：国漫\n") == []
    assert ic.diff_cinematic_focal("无契约文本", "无契约文本") == []
