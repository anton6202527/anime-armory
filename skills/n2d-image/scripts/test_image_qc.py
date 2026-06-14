"""image_qc 单测——纯函数 + lint + registry 合法性 + 汇总。

从本目录跑：
  cd skills/n2d-image/scripts && python3 -m pytest test_image_qc.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("image_qc.py")
spec = importlib.util.spec_from_file_location("image_qc", SCRIPT)
image_qc = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(image_qc)


def test_worst_verdict_severity_order() -> None:
    assert image_qc.worst_verdict([]) == "ok"
    assert image_qc.worst_verdict(["ok", "warn", "ok"]) == "warn"
    assert image_qc.worst_verdict(["warn", "block"]) == "block"
    assert image_qc.worst_verdict(["ok", "noface"]) == "noface"   # noface 重于 ok 轻于 warn
    assert image_qc.worst_verdict(["noface", "warn"]) == "warn"


def test_count_verdicts_tallies_by_field() -> None:
    rows = [{"verdict": "block"}, {"verdict": "warn"}, {"verdict": "warn"},
            {"verdict": "ok"}, {"verdict": "noface"}, {"no_verdict": 1}]
    assert image_qc.count_verdicts(rows) == {"block": 1, "warn": 2, "noface": 1, "ok": 1}
    assert image_qc.count_verdicts([]) == {"block": 0, "warn": 0, "noface": 0, "ok": 0}


def test_split_shot_blocks() -> None:
    md = "前言\n## Clip 01 起\n参考图\n## Clip 02 承\n身份\n尾"
    blocks = image_qc.split_shot_blocks(md)
    assert [b["label"] for b in blocks] == ["Clip 01 起", "Clip 02 承"]
    assert "参考图" in blocks[0]["body"]
    assert "前言" not in blocks[0]["body"]   # 标题前的内容不计入任何镜块


def test_load_registry_ids(tmp_path: Path) -> None:
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "identity_registry.json").write_text(json.dumps({
        "characters": [
            {"id": "CHAR_01", "forms": [{"form": "常态"}, {"form": "觉醒态"}]},
            {"id": "CHAR_03", "forms": [{"form": "人皮态"}]},
            {"id": "CHAR_SHEN", "forms": [{"form": "受难"}]},
        ]
    }, ensure_ascii=False), encoding="utf-8")
    ids = image_qc.load_registry_ids(tmp_path)
    assert ids == {
        "CHAR_01", "CHAR_01/常态", "CHAR_01/觉醒态",
        "CHAR_03", "CHAR_03/人皮态",
        "CHAR_SHEN", "CHAR_SHEN/受难",
    }
    # 缺 registry → None（lint 跳过合法性，不误报）
    assert image_qc.load_registry_ids(tmp_path / "nope") is None


def _char_block(label: str, *, ref=True, eyeline=True, anchor=True, lock=True, char_id="CHAR_01/常态") -> dict:
    body = []
    if ref:
        body.append("**参考图**（多图参考派生铁律）:\n- `出图/共享/图片/定妆_沈念_常态.png`（强度 0.8）")
    if eyeline:
        body.append("**视线方向**：画左看画右")
    body.append(f"**资产身份注册层**：`{char_id}`；从 identity_registry 继承 reference_group。")
    if anchor:
        body.append("锚点句：沈念：凤眼薄唇")
    if lock:
        body.append("身份锁定句：保持与参考图①的人脸一致。")
    return {"label": label, "body": "\n".join(body)}


def _registry_forms_for_tail_handoff() -> list:
    return [
        {
            "id": "CHAR_01",
            "form": "常态",
            "key": "CHAR_01/常态",
            "asset_key": "沈念_常态",
            "display": "沈念_常态",
            "strong_aliases": {"CHAR_01", "CHAR_01/常态", "沈念_常态", "定妆_沈念_常态"},
            "weak_aliases": {"沈念", "林婉儿"},
        },
        {
            "id": "CHAR_03",
            "form": "人皮态",
            "key": "CHAR_03/人皮态",
            "asset_key": "柳娘子_人皮态",
            "display": "柳娘子_人皮态",
            "strong_aliases": {
                "CHAR_03",
                "CHAR_03/人皮态",
                "柳娘子_人皮态",
                "定妆_柳娘子_人皮态",
                "定妆_柳娘子_人皮态_脸部特写",
            },
            "weak_aliases": {"柳娘子"},
        },
    ]


def _tail_handoff_block(tail_lock: str = "") -> dict:
    blk = _char_block("Clip 12 轻笑与失控")
    blk["body"] += "\n".join([
        "",
        "**专项镜头模板**：dialogue_shot_reverse；柳娘子笑意失控作为下一镜入点。",
        "**近景/反打身份锁定**：尾帧出现柳娘子近景反应时，必须锁中年圆润脸。",
        "**尾帧接力生成方式**：以 `Clip_12_沈念轻笑.png` 为母图，只改柳娘子反应。",
        tail_lock,
    ])
    return blk


def test_lint_flags_unknown_char_id() -> None:
    valid = {"CHAR_01", "CHAR_01/常态"}
    blk = _char_block("Clip 05", char_id="CHAR_99/常态")
    findings = image_qc.lint_shot_block(blk, valid)
    codes = {f["code"] for f in findings}
    assert "unknown_char_id" in codes
    assert any(f["level"] == "block" for f in findings if f["code"] == "unknown_char_id")


def test_lint_passes_clean_char_block() -> None:
    valid = {"CHAR_01", "CHAR_01/常态"}
    findings = image_qc.lint_shot_block(_char_block("Clip 02"), valid)
    assert findings == []   # 参考图/视线/锚点句/身份锁定句/合法ID 齐 → 无 finding


def test_character_shot_manifest_extracts_target_png() -> None:
    blk = _char_block("Clip 02 冷开场")
    blk["body"] = "**目标存档**：`出图/第1集/图片/Clip_02_冷开场.png`\n" + blk["body"]
    manifest = image_qc.character_shot_manifest(blk)
    assert manifest["shot"] == "Clip_02"
    assert manifest["png"] == "出图/第1集/图片/Clip_02_冷开场.png"
    assert manifest["identity_refs"] == ["CHAR_01/常态"]


def test_character_shot_manifest_skips_no_face_asset_only_shot() -> None:
    blk = {
        "label": "Clip 16 毒酒碎裂",
        "body": (
            "**目标**：`出图/第1集/图片/Clip_16_毒酒碎裂.png`\n"
            "**参考图**：`出图/共享/图片/定妆_冷宫寝殿.png`；"
            "`出图/共享/图片/定妆_毒酒碎瓷.png`\n"
            "**资产身份注册层**：从 `出图/共享/identity_registry.json` 继承；"
            "无人物或人物不露脸：以场景/道具锚为主。\n"
            "**资产引用注册层**：`LOC_01`；`PROP_03`。"
        ),
    }
    assert image_qc.character_shot_manifest(blk) is None


def test_character_shot_manifest_skips_explicit_no_face_coverage_shot() -> None:
    blk = _char_block("Clip 14 左腕特写", char_id="CHAR_01/觉醒态")
    blk["body"] += "\n**脸部覆盖豁免**：本镜是手腕特写，无可比对人脸；身份由袖口和相邻镜头连续性锁定。"
    assert image_qc.character_shot_manifest(blk) is None


def test_lint_accepts_semantic_char_ids_and_primary_marker() -> None:
    valid = {"CHAR_SHEN", "CHAR_SHEN/受难", "CHAR_LIU"}
    assert image_qc.lint_shot_block(_char_block("Clip 02", char_id="CHAR_SHEN/受难"), valid) == []
    assert image_qc.lint_shot_block(_char_block("Clip 03", char_id="CHAR_SHEN/受难*"), valid) == []
    assert image_qc.lint_shot_block(_char_block("Clip 04", char_id="CHAR_LIU*"), valid) == []


def test_lint_flags_unknown_semantic_char_id() -> None:
    valid = {"CHAR_SHEN", "CHAR_SHEN/受难"}
    blk = _char_block("Clip 05", char_id="CHAR_WANG/常态")
    findings = image_qc.lint_shot_block(blk, valid)
    assert any(f["code"] == "unknown_char_id" and "CHAR_WANG" in f["msg"] for f in findings)


def test_lint_flags_missing_reference_block() -> None:
    valid = {"CHAR_01", "CHAR_01/常态"}
    blk = _char_block("Clip 07", ref=False)
    findings = image_qc.lint_shot_block(blk, valid)
    assert any(f["code"] == "no_reference_block" and f["level"] == "block" for f in findings)


def test_lint_warns_missing_fields() -> None:
    valid = {"CHAR_01", "CHAR_01/常态"}
    blk = _char_block("Clip 09", eyeline=False, anchor=False, lock=False)
    codes = {f["code"]: f["level"] for f in image_qc.lint_shot_block(blk, valid)}
    assert codes.get("no_eyeline") == "warn"
    assert codes.get("no_anchor_phrase") == "warn"
    assert codes.get("no_identity_lock_phrase") == "warn"


def test_lint_skips_non_character_shot() -> None:
    # 纯空镜：无身份注册层、无定妆引用 → 不强求身份字段
    blk = {"label": "Clip 11 空镜", "body": "**视线方向**：无人物；画面重心按横轴。\n纯风/雾/残烛空镜。"}
    assert image_qc.lint_shot_block(blk, {"CHAR_01"}) == []


def test_lint_id_check_skipped_when_registry_missing() -> None:
    # valid_ids=None（registry 缺）→ 不做 ID 合法性，但其它字段照查
    blk = _char_block("Clip 03", char_id="CHAR_99/常态")
    codes = {f["code"] for f in image_qc.lint_shot_block(blk, None)}
    assert "unknown_char_id" not in codes


def test_lint_blocks_tail_identity_handoff_without_tail_prompt() -> None:
    valid = {"CHAR_01", "CHAR_01/常态", "CHAR_03", "CHAR_03/人皮态"}
    findings = image_qc.lint_shot_block(_tail_handoff_block(), valid, _registry_forms_for_tail_handoff())
    codes = {f["code"]: f["level"] for f in findings}
    assert codes.get("tail_identity_handoff_missing_prompt") == "block"


def test_lint_blocks_tail_identity_handoff_without_target_reference() -> None:
    valid = {"CHAR_01", "CHAR_01/常态", "CHAR_03", "CHAR_03/人皮态"}
    blk = _tail_handoff_block("**尾帧专用重抽提示**：锁柳娘子身份，不要美化成通用古装脸。")
    findings = image_qc.lint_shot_block(blk, valid, _registry_forms_for_tail_handoff())
    codes = {f["code"]: f["level"] for f in findings}
    assert codes.get("tail_identity_handoff_unlocked") == "block"


def test_lint_passes_tail_identity_handoff_with_target_reference() -> None:
    valid = {"CHAR_01", "CHAR_01/常态", "CHAR_03", "CHAR_03/人皮态"}
    blk = _tail_handoff_block(
        "**尾帧专用重抽提示（2026-06-13）**：`Clip_12_end.png` 是柳娘子失控入点；"
        "以 `CHAR_03/人皮态`、`定妆_柳娘子_人皮态_脸部特写.png` 锁目标身份。"
    )
    findings = image_qc.lint_shot_block(blk, valid, _registry_forms_for_tail_handoff())
    assert not any(f["code"].startswith("tail_identity_handoff_") for f in findings)


def test_lint_blocks_tail_without_image2image_relay() -> None:
    # 同角色尾帧：声明了接力尾帧素材，但没写 image2image 锁脸 → 纯文生图兜底脸漂 → hard block
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 30 转身")
    blk["body"] += "\n**目标**：`出图/第1集/图片/Clip_30.png` + 接力尾帧 `Clip_30_end.png`"
    codes = {f["code"]: f["level"] for f in image_qc.lint_shot_block(blk, valid)}
    assert codes.get("tail_relay_not_image2image") == "block"


def test_lint_passes_tail_with_image2image_relay() -> None:
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 31 转身")
    blk["body"] += ("\n**尾帧接力生成方式**：以 `Clip_31.png` 图生图为母图，只改表情。"
                    "接力尾帧 `Clip_31_end.png`")
    findings = image_qc.lint_shot_block(blk, valid)
    assert not any(f["code"] == "tail_relay_not_image2image" for f in findings)


def test_lint_tail_relay_allows_negated_text2image_phrase() -> None:
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 31 转身")
    blk["body"] += (
        "\n**参考图**（多图参考派生铁律：禁纯文生图）"
        "\n**尾帧接力生成方式**：以 `Clip_31.png` 图生图为母图，只改表情，"
        "不得纯文生图。接力尾帧 `Clip_31_end.png`"
    )
    findings = image_qc.lint_shot_block(blk, valid)
    assert not any(f["code"] == "tail_relay_not_image2image" for f in findings)


def test_lint_tail_relay_blocks_unnegated_text2image_fallback() -> None:
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 31 转身")
    blk["body"] += (
        "\n**尾帧接力生成方式**：以 `Clip_31.png` 图生图为母图，只改表情，"
        "失败时纯文生图兜底。接力尾帧 `Clip_31_end.png`"
    )
    codes = {f["code"]: f["level"] for f in image_qc.lint_shot_block(blk, valid)}
    assert codes.get("tail_relay_not_image2image") == "block"


def test_lint_no_tail_relay_finding_when_shot_has_no_tail() -> None:
    # 没有尾帧的普通角色镜不应被尾帧锁脸铁律误伤
    valid = {"CHAR_01/常态"}
    findings = image_qc.lint_shot_block(_char_block("Clip 32"), valid)
    assert not any(f["code"] == "tail_relay_not_image2image" for f in findings)


def test_lint_skips_tail_identity_handoff_when_tail_declared_none() -> None:
    valid = {"CHAR_01", "CHAR_01/常态", "CHAR_03", "CHAR_03/人皮态"}
    blk = _char_block("Clip 20 集尾", char_id="CHAR_01/觉醒态")
    blk["body"] += "\n".join([
        "",
        "**目标**：`出图/第1集/图片/Clip_20.png`；尾帧：`无`",
        "**近景/反打身份锁定**：本镜沈念为主，柳娘子在右后景反应仍需引用 `定妆_柳娘子_人皮态_脸部特写.png`。",
        "**尾帧接力生成方式**：本镜若生成柳娘子反应尾帧/变体，只改后景反应，不重画柳娘子脸。",
    ])
    findings = image_qc.lint_shot_block(blk, valid, _registry_forms_for_tail_handoff())
    assert not any(f["code"].startswith("tail_identity_handoff_") for f in findings)


def test_lint_warns_closeup_strong_emotion_without_expression_lib() -> None:
    # 近景 + 强情绪角色镜，未引表情库/脸部特写 → warn（表情镜脸漂风险）
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 40 痛哭")
    blk["body"] += "\n**景别**：ECU 面部特写\n**情绪**：崩溃落泪、面部扭曲"
    codes = {f["code"]: f["level"] for f in image_qc.lint_shot_block(blk, valid)}
    assert codes.get("no_expression_lib_ref") == "warn"


def test_lint_passes_closeup_emotion_with_expression_lib_ref() -> None:
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 41 痛哭")
    blk["body"] += ("\n**景别**：ECU 面部特写\n**情绪**：崩溃落泪"
                    "\n表情库：引用 `定妆_沈念_常态_脸部特写.png` 同源表情，首尾双帧只插值。")
    findings = image_qc.lint_shot_block(blk, valid)
    assert not any(f["code"] == "no_expression_lib_ref" for f in findings)


def test_lint_no_expression_gate_when_not_closeup() -> None:
    # 远景大表情：景别不近 → 不触发表情库 gate
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 42 远景")
    blk["body"] += "\n**景别**：远景 LS 全身\n**情绪**：崩溃落泪"
    assert not any(f["code"] == "no_expression_lib_ref" for f in image_qc.lint_shot_block(blk, valid))


def test_lint_no_expression_gate_when_neutral_closeup() -> None:
    # 近景但中性表情 → 不强求表情库
    valid = {"CHAR_01/常态"}
    blk = _char_block("Clip 43 近景中性")
    blk["body"] += "\n**景别**：CU 近景\n**情绪**：平静、无明显表情"
    assert not any(f["code"] == "no_expression_lib_ref" for f in image_qc.lint_shot_block(blk, valid))


def test_lint_expression_gate_skips_non_character_shot() -> None:
    # 空镜即便写了近景+情绪词也不触发（非角色镜先被 is_char_shot 挡掉）
    blk = {"label": "Clip 44 空镜", "body": "**景别**：ECU 特写\n残烛痛苦地摇曳，无人物。"}
    assert image_qc.lint_shot_block(blk, {"CHAR_01"}) == []


# ── A 资产 id lint 对称化 ───────────────────────────────────────────────────────

def _asset_index() -> dict:
    return {
        "ids": {"LOC_01", "PROP_01", "VFX_01"},
        "name_to_id": {"冷宫寝殿": "LOC_01", "斑驳铜镜": "PROP_01", "暗金妖力脉冲": "VFX_01"},
        "prefix_of": {"LOC_01": "LOC_", "PROP_01": "PROP_", "VFX_01": "VFX_"},
    }


def test_load_asset_index(tmp_path: Path) -> None:
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "asset_registry.json").write_text(json.dumps({"assets": [
        {"id": "LOC_01", "type": "scene", "name": "冷宫寝殿",
         "reference_group": {"primary": "出图/共享/图片/定妆_冷宫寝殿.png"}},
        {"id": "PROP_01", "type": "prop", "name": "斑驳铜镜",
         "reference_group": {"primary": "出图/共享/图片/定妆_斑驳铜镜.png"}},
    ]}, ensure_ascii=False), encoding="utf-8")
    idx = image_qc.load_asset_index(tmp_path)
    assert idx["ids"] == {"LOC_01", "PROP_01"}
    assert idx["name_to_id"]["冷宫寝殿"] == "LOC_01"
    assert idx["name_to_id"]["斑驳铜镜"] == "PROP_01"   # 由 name 与 reference_group stem 双路映射
    assert idx["prefix_of"]["PROP_01"] == "PROP_"
    assert image_qc.load_asset_index(tmp_path / "nope") is None


def test_lint_flags_unknown_asset_id() -> None:
    blk = {"label": "Clip 05 道具", "body": "**资产引用注册层**：`PROP_99`；从 asset_registry 取参考。"}
    findings = image_qc.lint_shot_block(blk, None, None, _asset_index())
    codes = {f["code"]: f["level"] for f in findings}
    assert codes.get("unknown_asset_id") == "block"


def test_lint_warns_asset_ref_without_id() -> None:
    # 用了 定妆_斑驳铜镜（已登记 PROP_01）却没绑 PROP_01 → warn
    blk = {"label": "Clip 06 铜镜", "body": "**参考图**：`出图/共享/图片/定妆_斑驳铜镜.png`（道具定妆）"}
    findings = image_qc.lint_shot_block(blk, None, None, _asset_index())
    codes = {f["code"]: f["level"] for f in findings}
    assert codes.get("asset_ref_without_id") == "warn"


def test_lint_asset_binding_clean_when_id_present() -> None:
    blk = {"label": "Clip 07", "body": "**参考图**：`定妆_斑驳铜镜.png`；资产引用注册层：`PROP_01`。"}
    findings = image_qc.lint_shot_block(blk, None, None, _asset_index())
    assert not any(f["code"] in ("unknown_asset_id", "asset_ref_without_id") for f in findings)


def test_lint_asset_runs_on_pure_scene_shot() -> None:
    # 纯场景镜（非角色镜）也要跑资产 lint，不被 is_char_shot 早返回挡掉
    blk = {"label": "Clip 08 空镜", "body": "纯场景空镜，用了 `定妆_冷宫寝殿.png` 但没写 LOC 绑定。"}
    findings = image_qc.lint_shot_block(blk, {"CHAR_01"}, None, _asset_index())
    assert any(f["code"] == "asset_ref_without_id" for f in findings)


def test_lint_asset_skipped_when_no_registry() -> None:
    blk = {"label": "Clip 09", "body": "`PROP_99` 与 `定妆_斑驳铜镜.png`"}
    assert image_qc.lint_shot_block(blk, None, None, None) == []   # asset_index=None → 跳过


def test_unknown_asset_id_is_hard_lint() -> None:
    assert "unknown_asset_id" in image_qc.HARD_LINT_CODES


# ── B 道具/特效漂移进落档 ──────────────────────────────────────────────────────

def test_summarize_multimodal_is_advisory() -> None:
    payload = {"checks": {"multimodal": {"available": True, "shots": [
        {"verdict": "block"}, {"verdict": "warn"}]}}, "lint": {"available": True, "findings": []}}
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 0          # 道具/特效初筛即便 block 也只算人判
    assert s["advisory"] == 2
    assert s["verdict"] == "review"


def test_to_findings_emits_multimodal_warn() -> None:
    payload = {"checks": {"multimodal": {"shots": [
        {"png": "图片/Clip_05.png", "verdict": "block", "asset": "PROP_01"}]}},
        "lint": {"findings": []}}
    fnds = image_qc.to_findings(payload)
    mm = [f for f in fnds if f["dim"] == "asset_consistency"]
    assert len(mm) == 1 and mm[0]["sev"] == "warn" and "PROP_01" in mm[0]["msg"]


# ── D 场景/道具/特效漂移人审拼图 ───────────────────────────────────────────────

def test_asset_review_targets_scene_and_multimodal() -> None:
    payload = {"checks": {
        "scene": {"shots": [{"png": "图片/Clip_03.png", "scene": "冷宫寝殿.png", "verdict": "warn"},
                            {"png": "图片/Clip_04.png", "scene": "冷宫寝殿.png", "verdict": "ok"}]},
        "multimodal": {"shots": [{"png": "图片/Clip_07.png", "asset": "PROP_01", "verdict": "block"}]},
    }}
    pm = {"冷宫寝殿": "出图/共享/图片/定妆_冷宫寝殿.png", "PROP_01": "出图/共享/图片/定妆_斑驳铜镜.png"}
    targets = image_qc.asset_review_targets(payload, Path("/r/剧"), "第1集", pm)
    kinds = {(t["kind"], t["shot"]) for t in targets}
    assert ("scene", "Clip_03") in kinds        # warn 进队列
    assert ("asset", "Clip_07") in kinds        # multimodal block 进队列
    assert not any(t["shot"] == "Clip_04" for t in targets)   # ok 不进
    scene_t = next(t for t in targets if t["kind"] == "scene")
    assert scene_t["ref"] == "出图/共享/图片/定妆_冷宫寝殿.png"
    assert scene_t["png_abs"] == "/r/剧/出图/第1集/图片/Clip_03.png"
    assert scene_t["stitch"].endswith("生产数据/image_qc/第1集/asset_review/scene_Clip_03_compare.png")


def test_asset_review_targets_empty_when_clean() -> None:
    payload = {"checks": {"scene": {"shots": [{"png": "a.png", "scene": "x.png", "verdict": "ok"}]},
                          "multimodal": {"shots": []}}}
    assert image_qc.asset_review_targets(payload, Path("/r"), "第1集", {}) == []


def test_resolve_asset_ref_falls_back(tmp_path: Path) -> None:
    # primary_map 命中优先
    pm = {"斑驳铜镜": "出图/共享/图片/定妆_斑驳铜镜.png"}
    assert image_qc._resolve_asset_ref(tmp_path, pm, "斑驳铜镜.png") == "出图/共享/图片/定妆_斑驳铜镜.png"
    # 不命中且无文件 → None
    assert image_qc._resolve_asset_ref(tmp_path, {}, "不存在的资产") is None


def test_lifecycle_regression_is_hard_lint() -> None:
    # F：资产状态回退作为 lint 硬码项，summarize 当 hard
    payload = {"checks": {}, "lint": {"available": True, "findings": [
        {"level": "block", "code": "lifecycle_regression", "msg": "PROP_03：状态回退"}]}}
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 1
    assert s["verdict"] == "block"
    assert "lifecycle_regression" in image_qc.HARD_LINT_CODES


def test_summarize_hard_vs_advisory() -> None:
    payload = {
        "checks": {
            "face": {"available": True, "shots": [{"verdict": "block"}, {"verdict": "ok"}]},   # hard 1
            "outfit": {"available": True, "shots": [{"verdict": "block"}, {"verdict": "warn"}]},  # advisory 2（初筛）
            "scene": {"available": True, "shots": []},
            "seam": {"available": True, "seams": [{"verdict": "warn"}]},                         # advisory 1
            "anchors": {"available": True, "anchors": [{"char": "x", "verdict": "block"}]},      # advisory 1
        },
        "lint": {"available": True, "findings": [
            {"level": "block", "code": "unknown_char_id"},   # hard 1
            {"level": "warn", "code": "no_eyeline"},          # advisory 1
        ]},
    }
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 2    # face block + lint unknown_char_id
    assert s["advisory"] == 5       # outfit block+warn + seam warn + anchors block + lint warn
    assert s["verdict"] == "block"


def test_summarize_outfit_block_alone_is_review_not_block() -> None:
    # 服装/场景初筛即便报 block，也只算 review（人判），不强制重抽
    payload = {"checks": {"outfit": {"available": True, "shots": [{"verdict": "block"}]}},
               "lint": {"available": True, "findings": []}}
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 0
    assert s["verdict"] == "review"


def test_summarize_clean_is_ok() -> None:
    payload = {"checks": {"face": {"available": True, "shots": [{"verdict": "ok"}]}},
               "lint": {"available": True, "findings": []}}
    assert image_qc.summarize(payload)["verdict"] == "ok"


def test_summarize_pillow_fallback_degrades_to_review() -> None:
    payload = {"checks": {"face": {"available": True, "mode": "pillow_fallback",
                                   "shots": [{"verdict": "ok", "degraded_face": True, "closeup": False}]}},
               "lint": {"available": True, "findings": []}}
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 0
    assert s["degraded"] is True
    assert s["verdict"] == "review"


def test_summarize_unavailable_visual_checks_degrades_to_review() -> None:
    payload = {
        "checks": {
            "face": {"available": False, "notes": ["缺 Pillow/insightface"]},
            "outfit": {"available": False, "notes": ["缺 Pillow"]},
            "seam": {"notes": ["未装 Pillow——接缝机检跳过"]},
        },
        "lint": {"available": True, "findings": []},
    }
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 0
    assert s["advisory"] == 0
    assert s["verdict"] == "review"
    assert s["degraded"] is True
    assert s["unavailable_visual_checks"] == ["face", "outfit", "seam"]


def test_qc_environment_reports_precision_and_stage_jump() -> None:
    full = {
        "checks": {"face": {"available": True, "mode": "insightface", "shots": []},
                   "outfit": {"available": True, "shots": []},
                   "scene": {"available": True, "shots": []},
                   "seam": {"available": True, "seams": []}},
        "summary": {"verdict": "ok"},
    }
    env = image_qc.qc_environment(full)
    assert env["precision_level"] == "full"
    assert env["jump_to_stage"] == "video"
    assert env["recommended_install"] == ""

    full_review = {
        "checks": {"face": {"available": True, "mode": "insightface", "shots": []},
                   "outfit": {"available": True, "shots": [{"verdict": "warn"}]},
                   "scene": {"available": True, "shots": []},
                   "seam": {"available": True, "seams": []}},
        "summary": {"verdict": "review", "hard_blocks": 0, "advisory": 1},
    }
    env = image_qc.qc_environment(full_review)
    assert env["precision_level"] == "full"
    assert env["jump_to_stage"] == "video"
    assert "非阻断初筛" in env["jump_reason"]

    degraded = {
        "checks": {"face": {"available": True, "mode": "pillow_fallback", "shots": []}},
        "summary": {"verdict": "ok"},
    }
    env = image_qc.qc_environment(degraded)
    assert env["precision_level"] == "degraded"
    assert env["jump_to_stage"] == "image"
    assert "insightface" in " ".join(env["missing_or_degraded"])
    assert "facefusion" in env["recommended_install"]

    none = {
        "checks": {
            "face": {"available": False, "notes": ["缺 Pillow"]},
            "outfit": {"available": False, "notes": ["缺 Pillow"]},
            "scene": {"available": False, "notes": ["缺 Pillow"]},
            "seam": {"available": False, "notes": ["缺 Pillow"]},
        },
        "summary": {"verdict": "review"},
    }
    env = image_qc.qc_environment(none)
    assert env["precision_level"] == "none"
    assert env["jump_to_stage"] == "image_qc_setup"


def test_summarize_seam_block_is_hard() -> None:
    # 接缝接力 block = 真接力断（seam_analyze 已对设计切镜降 info）→ 与崩脸同级 hard，gate 硬拦
    payload = {"checks": {"seam": {"available": True, "seams": [{"verdict": "block"}, {"verdict": "warn"}]}},
               "lint": {"available": True, "findings": []}}
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 1   # seam block
    assert s["advisory"] == 1      # seam warn
    assert s["verdict"] == "block"


def test_to_findings_emits_seam_block_as_block() -> None:
    payload = {"checks": {"seam": {"available": True, "seams": [
        {"verdict": "block", "tail": "镜头05_end.png", "next_first": "镜头06.png", "dist": 33}]}},
        "lint": {"findings": []}}
    findings = image_qc.to_findings(payload)
    seam_f = [f for f in findings if "接缝" in f["msg"]]
    assert seam_f and seam_f[0]["sev"] == "block"


def test_degraded_closeup_face_is_hard_block_but_non_closeup_is_review() -> None:
    # 降级精度（pillow_fallback）：近景脸无法验同人 → hard block；远景脸仍只 review
    payload = {
        "checks": {"face": {"available": True, "mode": "pillow_fallback", "shots": [
            {"png": "镜头03.png", "verdict": "ok", "degraded_face": True, "closeup": True},
            {"png": "镜头08.png", "verdict": "ok", "degraded_face": True, "closeup": False},
        ]}},
        "lint": {"findings": []},
    }
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 1   # only the closeup shot
    assert s["verdict"] == "block"
    findings = image_qc.to_findings(payload)
    deg = [f for f in findings if "降级精度近景" in f["msg"]]
    assert len(deg) == 1 and deg[0]["sev"] == "block" and "镜头03" in deg[0]["loc"]


def test_face_review_targets_for_degraded_closeup() -> None:
    # 降级近景脸 → 人审拼图目标：ref=定妆主参考，stitch 落 生产数据/image_qc/<ep>/face_review。
    payload = {
        "checks": {"face": {"available": True, "mode": "pillow_fallback", "shots": [
            {"png": "图片/Clip_12_脸.png", "chars": ["沈念_常态"], "verdict": "ok",
             "degraded_face": True, "closeup": True},
            {"png": "图片/Clip_08.png", "chars": ["沈念_常态"], "verdict": "ok",
             "degraded_face": True, "closeup": False},   # 远景 → 不进队列
        ]}},
    }
    targets = image_qc.face_review_targets(payload, Path("/r/剧"), "第1集")
    assert len(targets) == 1
    t = targets[0]
    assert t["shot"] == "Clip_12"
    assert t["char"] == "沈念_常态"
    assert t["ref"] == "出图/共享/图片/定妆_沈念_常态.png"
    assert t["png_abs"] == "/r/剧/出图/第1集/图片/Clip_12_脸.png"
    assert t["stitch"].endswith("生产数据/image_qc/第1集/face_review/Clip_12_compare.png")


def test_face_review_targets_empty_when_full_precision() -> None:
    # full（insightface）模式无 degraded_face → 队列为空
    payload = {"checks": {"face": {"mode": "insightface", "shots": [
        {"png": "图片/Clip_03.png", "chars": ["沈念"], "verdict": "ok"}]}}}
    assert image_qc.face_review_targets(payload, Path("/r"), "第1集") == []


def test_stitch_for_png_lookup() -> None:
    payload = {"face_human_review": [
        {"png": "图片/Clip_12_脸.png", "stitch": "/r/生产数据/.../Clip_12_compare.png", "stitched": True},
        {"png": "图片/Clip_13.png", "stitch": "/r/.../Clip_13_compare.png", "stitched": False},
    ]}
    assert image_qc._stitch_for_png(payload, "图片/Clip_12_脸.png").endswith("Clip_12_compare.png")
    assert image_qc._stitch_for_png(payload, "图片/Clip_13.png") is None   # 未成功生成 → None
    assert image_qc._stitch_for_png(payload, "图片/none.png") is None


def test_to_findings_degraded_closeup_appends_stitch_path() -> None:
    payload = {
        "checks": {"face": {"available": True, "mode": "pillow_fallback", "shots": [
            {"png": "图片/Clip_12_脸.png", "verdict": "ok", "degraded_face": True, "closeup": True}]}},
        "lint": {"findings": []},
        "face_human_review": [
            {"png": "图片/Clip_12_脸.png", "stitch": "生产数据/image_qc/第1集/face_review/Clip_12_compare.png",
             "stitched": True}],
    }
    findings = image_qc.to_findings(payload)
    deg = [f for f in findings if "降级精度近景" in f["msg"]]
    assert len(deg) == 1
    assert "人审并排图" in deg[0]["msg"] and "Clip_12_compare.png" in deg[0]["msg"]


def _coverage_payload(verdict: str = "ok") -> dict:
    return {
        "checks": {"face": {"available": True, "mode": "insightface", "shots": [
            {"png": "图片/Clip_02_冷开场.png", "verdict": verdict, "chars": ["沈念"]},
        ]}},
        "lint": {"available": True, "findings": [], "character_shots": [
            {"label": "Clip 02 冷开场", "shot": "Clip_02",
             "png": "出图/第1集/图片/Clip_02_冷开场.png", "identity_refs": ["CHAR_01/常态"]},
        ]},
    }


def test_face_reference_coverage_requires_full_face_row_for_landed_character_png(tmp_path: Path) -> None:
    png = tmp_path / "出图" / "第1集" / "图片" / "Clip_02_冷开场.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"x")
    payload = _coverage_payload()
    payload["checks"]["face"]["shots"] = []
    coverage = image_qc.face_reference_coverage(payload, tmp_path, "第1集")
    assert coverage["verdict"] == "block"
    assert coverage["missing"][0]["reason"] == "no_face_comparison"

    payload["face_reference_coverage"] = coverage
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 1
    assert s["verdict"] == "block"


def test_face_reference_coverage_blocks_warn_face_match(tmp_path: Path) -> None:
    png = tmp_path / "出图" / "第1集" / "图片" / "Clip_02_冷开场.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"x")
    payload = _coverage_payload("warn")
    coverage = image_qc.face_reference_coverage(payload, tmp_path, "第1集")
    assert coverage["verdict"] == "block"
    assert coverage["missing"][0]["reason"] == "face_verdict_warn"

    payload["face_reference_coverage"] = coverage
    findings = image_qc.to_findings(payload)
    strict = [f for f in findings if "角色脸定妆比对覆盖缺口" in f["msg"]]
    assert len(strict) == 1 and strict[0]["sev"] == "block"


def test_face_reference_coverage_passes_full_ok_match(tmp_path: Path) -> None:
    png = tmp_path / "出图" / "第1集" / "图片" / "Clip_02_冷开场.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"x")
    coverage = image_qc.face_reference_coverage(_coverage_payload("ok"), tmp_path, "第1集")
    assert coverage["verdict"] == "ok"
    assert coverage["required"] == 1
    assert coverage["covered"] == 1
    assert coverage["missing"] == []


def test_face_reference_coverage_does_not_block_prompt_before_png(tmp_path: Path) -> None:
    coverage = image_qc.face_reference_coverage(_coverage_payload("ok"), tmp_path, "第1集")
    assert coverage["verdict"] == "ok"
    assert coverage["required"] == 0
    assert len(coverage["pending"]) == 1


def test_to_regen_list_includes_face_reference_coverage_missing() -> None:
    payload = {
        "checks": {},
        "lint": {"findings": []},
        "face_reference_coverage": {"missing": [
            {"label": "Clip 02 冷开场", "shot": "Clip_02", "png": "图片/Clip_02_冷开场.png",
             "reason": "no_face_comparison"}
        ]},
    }
    regen = image_qc.to_regen_list(payload)
    assert len(regen) == 1
    assert regen[0]["shot"] == "Clip_02"
    assert "脸部定妆比对覆盖:no_face_comparison" in regen[0]["reasons"]


def test_to_findings_maps_severity_and_dims() -> None:
    payload = {
        "checks": {
            "face": {"shots": [{"png": "镜头3.png", "verdict": "block"}, {"png": "镜头4.png", "verdict": "ok"}]},
            "outfit": {"shots": [{"png": "镜头5.png", "verdict": "block"}]},   # 初筛 → warn
            "scene": {"shots": [{"png": "镜头6.png", "verdict": "warn", "kind": "光色"}]},
            "seam": {"seams": [{"tail": "镜头7_end.png", "next_first": "镜头8.png", "dist": 40, "verdict": "warn"}]},
            "anchors": {"anchors": [{"char": "沈念", "verdict": "block"}]},     # 初筛 → warn
        },
        "lint": {"findings": [
            {"level": "block", "code": "unknown_char_id", "msg": "Clip 9：非法 CHAR_99"},
            {"level": "warn", "code": "no_eyeline", "msg": "Clip 9：缺视线"},
        ]},
    }
    fnds = image_qc.to_findings(payload)
    by_sev = {(f["dim"], f["sev"]) for f in fnds}
    assert ("character_consistency", "block") in by_sev      # 崩脸 hard
    assert ("outfit_consistency", "warn") in by_sev          # 服装初筛降 warn
    assert ("scene_consistency", "warn") in by_sev           # 场景/接缝初筛
    assert ("image_prompt_lint", "block") in by_sev          # 非法 ID hard
    assert ("image_prompt_lint", "warn") in by_sev           # 漏视线 warn
    # face 的 ok 行不进 findings；服装 block 不会变成 block sev
    assert not any(f["dim"] == "outfit_consistency" and f["sev"] == "block" for f in fnds)
    assert all(f["return_to_stage"] == "image" for f in fnds)


def test_to_findings_reports_unavailable_visual_checks() -> None:
    payload = {
        "checks": {
            "face": {"available": False, "notes": ["face_consistency 不可用"]},
            "scene": {"available": False, "notes": ["scene_consistency 不可用"]},
        },
        "lint": {"findings": []},
    }
    fnds = image_qc.to_findings(payload)
    assert len(fnds) == 2
    assert all(f["sev"] == "warn" for f in fnds)
    assert any(f["dim"] == "character_consistency" and "未执行" in f["msg"] for f in fnds)
    assert any(f["dim"] == "scene_consistency" and "未执行" in f["msg"] for f in fnds)


def test_to_findings_empty_when_clean() -> None:
    payload = {"checks": {"face": {"shots": [{"png": "a.png", "verdict": "ok"}]}},
               "lint": {"findings": []}}
    assert image_qc.to_findings(payload) == []


def test_shot_key_extracts_clip_number() -> None:
    assert image_qc._shot_key("图片/Clip_18_铜镜金瞳.png") == "Clip_18"
    assert image_qc._shot_key("Clip 09：角色镜缺参考图") == "Clip_09"
    assert image_qc._shot_key("镜头7_end.png") == "Clip_07"
    assert image_qc._shot_key(None) is None
    assert image_qc._shot_key("空镜.png") == "空镜.png"   # 提不出镜号 → 退回文件名


def test_to_regen_list_only_unusable_shots() -> None:
    payload = {
        "checks": {
            "face": {"shots": [{"png": "图片/Clip_03_脸.png", "verdict": "block"},   # 崩脸 → 重生成
                               {"png": "图片/Clip_04_脸.png", "verdict": "ok"}]},
            "outfit": {"shots": [{"png": "图片/Clip_18_金瞳.png", "verdict": "block"},  # 校准后服装漂 → 重生成
                                 {"png": "图片/Clip_02_旧疤.png", "verdict": "warn"}]},  # warn → 能用，保留
            "scene": {"shots": [{"png": "图片/Clip_05.png", "verdict": "warn"}]},        # 场景初筛 warn → 保留
            "seam": {"seams": [{"tail": "图片/Clip_07_end.png", "verdict": "block"}]},   # 接缝断 → 重生成
        },
        "lint": {"findings": [
            {"level": "block", "code": "unknown_char_id", "msg": "Clip 09：非法 CHAR_99"},  # 硬伤 → 重生成
            {"level": "block", "code": "no_eyeline", "msg": "Clip 11：缺视线"},             # 非硬码 → 不进
            {"level": "warn", "code": "no_anchor_phrase", "msg": "Clip 12：缺锚点"},
        ]},
    }
    regen = image_qc.to_regen_list(payload)
    shots = {r["shot"] for r in regen}
    assert shots == {"Clip_03", "Clip_18", "Clip_07", "Clip_09"}  # 崩脸/服装漂/接缝断/非法ID
    assert "Clip_04" not in shots and "Clip_02" not in shots      # ok/warn 能用就用，不重生成
    assert "Clip_05" not in shots and "Clip_11" not in shots
    # reasons 留痕
    c18 = next(r for r in regen if r["shot"] == "Clip_18")
    assert "服装漂 N1(校准后)" in c18["reasons"]
    assert c18["png"] == "图片/Clip_18_金瞳.png"


def test_to_strict_regen_list_includes_review_findings() -> None:
    payload = {
        "checks": {
            "face": {"shots": [{"png": "图片/Clip_03_脸.png", "verdict": "warn"}]},
            "outfit": {"shots": [{"png": "图片/Clip_18_金瞳.png", "verdict": "warn"}]},
            "scene": {"shots": [{"png": "图片/Clip_05.png", "verdict": "warn"}]},
            "seam": {"seams": [{"tail": "图片/Clip_07_end.png", "verdict": "warn"}]},
        },
        "lint": {"findings": [
            {"level": "warn", "code": "no_eyeline", "msg": "Clip 11：缺视线"},
            {"level": "warn", "code": "no_anchor_phrase", "msg": "Clip 12：缺锚点"},
        ]},
    }
    regen = image_qc.to_strict_regen_list(payload)
    shots = {r["shot"] for r in regen}
    assert shots == {"Clip_03", "Clip_18", "Clip_05", "Clip_07", "Clip_11", "Clip_12"}
    assert any("strict:prompt:no_eyeline" in r["reasons"] for r in regen if r["shot"] == "Clip_11")


def test_to_regen_list_empty_when_only_advisory() -> None:
    payload = {"checks": {"outfit": {"shots": [{"png": "a.png", "verdict": "warn"}]},
                          "scene": {"shots": [{"png": "b.png", "verdict": "warn"}]}},
               "lint": {"findings": [{"level": "warn", "code": "no_eyeline", "msg": "Clip 1"}]}}
    assert image_qc.to_regen_list(payload) == []   # 全是能用项 → 不重生成任何镜


# --- P2-A：disk-scoped 兜底——lint 漏分类的有脸镜列为 advisory，不静默漏检 ---
def test_coverage_flags_unclassified_face_shot(tmp_path: Path) -> None:
    # character_shots 空（lint 漏判），但 face 在某 PNG 检出人脸 → 应列 unclassified（非阻断）
    payload = {
        "lint": {"available": True, "character_shots": []},
        "checks": {"face": {"available": True, "mode": "insightface",
                            "shots": [{"png": "图片/Clip_05.png", "verdict": "ok"}]}},
    }
    cov = image_qc.face_reference_coverage(payload, tmp_path, "第1集")
    assert cov["required"] == 0
    assert cov["verdict"] == "ok"  # 无硬缺口
    uncl = cov["unclassified"]
    assert len(uncl) == 1
    assert uncl[0]["reason"] == "unclassified_face_shot"
    # summarize：advisory，不进 hard_blocks
    payload["face_reference_coverage"] = cov
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 0
    assert s["advisory"] >= 1


def test_coverage_ignores_noface_and_degraded(tmp_path: Path) -> None:
    # noface（场景/无脸镜）不应被当作漏分类角色镜
    payload = {
        "lint": {"available": True, "character_shots": []},
        "checks": {"face": {"available": True, "mode": "insightface",
                            "shots": [{"png": "图片/bg_01.png", "verdict": "noface"}]}},
    }
    cov = image_qc.face_reference_coverage(payload, tmp_path, "第1集")
    assert cov["unclassified"] == []
    # 降级精度（pillow_fallback）下不信任「检出人脸」，不产 unclassified（避免误报）
    payload_deg = {
        "lint": {"available": True, "character_shots": []},
        "checks": {"face": {"available": True, "mode": "pillow_fallback",
                            "shots": [{"png": "图片/Clip_05.png", "verdict": "ok"}]}},
    }
    cov_deg = image_qc.face_reference_coverage(payload_deg, tmp_path, "第1集")
    assert cov_deg["unclassified"] == []


# ── C3 多主体空间绑定 ──────────────────────────────────────────────────────
def test_multi_subject_spatial_binding_warns_without_blocking():
    body = "**资产身份注册层**：`CHAR_01/常态` 与 `CHAR_03/常态` 同框对峙。"
    out = image_qc._lint_multi_subject_spatial_binding("镜头5", body, ["CHAR_01/常态", "CHAR_03/常态"])
    assert len(out) == 1 and out[0]["code"] == "multi_person_no_spatial_binding" and out[0]["level"] == "warn"


def test_multi_subject_spatial_binding_ok_with_blocking_or_positions():
    refs = ["CHAR_01", "CHAR_03"]
    assert image_qc._lint_multi_subject_spatial_binding("镜头5", "blocking=沈念画左，柳娘子画右", refs) == []
    assert image_qc._lint_multi_subject_spatial_binding("镜头5", "沈念在画左，柳娘子在画右对峙", refs) == []
    # 单人镜不触发
    assert image_qc._lint_multi_subject_spatial_binding("镜头1", "CHAR_01 独自", ["CHAR_01/常态"]) == []


# ── C4 多角度参考喂养 ──────────────────────────────────────────────────────
def test_native_multiref_underfed_info_when_group_underused():
    body = "**参考图**：\n- `定妆_沈念.png`（正脸主参考）"
    out = image_qc._lint_native_multiref_coverage("镜头1", body, ["CHAR_01/常态"], {"CHAR_01": 4})
    assert len(out) == 1 and out[0]["code"] == "native_multiref_underfed" and out[0]["level"] == "info"


def test_native_multiref_ok_when_enough_or_no_group():
    body3 = "`定妆_沈念.png` `定妆_沈念_侧.png` `定妆_沈念_背.png`"
    assert image_qc._lint_native_multiref_coverage("镜头1", body3, ["CHAR_01"], {"CHAR_01": 4}) == []
    # 没有多角度组（avail<3）→ 不提
    assert image_qc._lint_native_multiref_coverage("镜头1", "`定妆_沈念.png`", ["CHAR_01"], {"CHAR_01": 1}) == []
    # 无 form_ref_counts → 不提
    assert image_qc._lint_native_multiref_coverage("镜头1", "`定妆_沈念.png`", ["CHAR_01"], None) == []


def test_registry_ref_counts_takes_max_per_char():
    forms = [{"id": "CHAR_01", "ref_count": 2}, {"id": "CHAR_01", "ref_count": 4}, {"id": "CHAR_02", "ref_count": 1}]
    assert image_qc.registry_ref_counts(forms) == {"CHAR_01": 4, "CHAR_02": 1}
