"""face_drift_risk 单测——评分纯函数 + 角色匹配 + 端到端 analyze。

cd skills/n2d-image/scripts && python3 -m pytest test_face_drift_risk.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("face_drift_risk.py")
spec = importlib.util.spec_from_file_location("face_drift_risk", SCRIPT)
fdr = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(fdr)


def test_is_closeup() -> None:
    assert fdr.is_closeup("ECU 面部特写")
    assert fdr.is_closeup("OTS 过肩反打")
    assert fdr.is_closeup("CU 50mm")
    assert not fdr.is_closeup("LS 35mm 慢推")
    assert not fdr.is_closeup("远景全景建制")


def test_has_strong_emotion() -> None:
    assert fdr.has_strong_emotion("沈念崩溃落泪")
    assert fdr.has_strong_emotion("暴怒嘶吼")
    assert not fdr.has_strong_emotion("沈念平静地走过")


def test_extreme_angle_tokens_maps_text_to_risky() -> None:
    risky = ["extreme_top", "extreme_low", "face_too_small", "deep_shadow"]
    assert fdr.extreme_angle_tokens("俯拍顶光", "", risky) == ["extreme_top"]
    assert "face_too_small" in fdr.extreme_angle_tokens("ELS 大全", "群像站位", risky)
    assert "deep_shadow" in fdr.extreme_angle_tokens("", "逆光剪影", risky)
    # risky 不含的项不命中（角色 angle_policy 没声明就不算高危）
    assert fdr.extreme_angle_tokens("俯拍", "", ["face_too_small"]) == []


def test_lock_tier() -> None:
    # Codex 默认：多图参考/图生图可用，但无持久主体 ID。
    assert fdr.lock_tier("codex", {"codex": {"status": "fallback_reference_group"}}, {"status": "not_needed"}) == "multi_reference"
    # Dreamina/即梦官方 CLI 可多参考，但无 n2d 持久主体 ID；不要误判 native。
    assert fdr.lock_tier("dreamina", {"dreamina": {"status": "registered"}}, {"status": "not_needed"}) == "multi_reference"
    # 可灵原生主体库 registered → native_subject。
    assert fdr.lock_tier("kling", {"kling": {"status": "registered"}}, {"status": "not_needed"}) == "native_subject"
    # 可灵但未注册 → native_unregistered，风险建议应提示先注册。
    assert fdr.lock_tier("kling", {"kling": {"status": "unregistered"}}, {}) == "native_unregistered"
    # LoRA ready 压倒一切 → lora
    assert fdr.lock_tier("codex", {"codex": {"status": "fallback_reference_group"}}, {"status": "ready"}) == "lora"


def test_three_quarter_ready_reads_atlas_and_reference_group() -> None:
    # base_views.three_quarter.status=ready → 就绪
    assert fdr.three_quarter_ready({"reference_atlas": {"base_views": {"three_quarter": {"status": "ready"}}}})
    # planned 不算就绪
    assert not fdr.three_quarter_ready({"reference_atlas": {"base_views": {"three_quarter": {"status": "planned"}}}})
    # reference_group 的结构化 planned 槽也不能因 dict 非空冒充 ready。
    assert not fdr.three_quarter_ready({
        "reference_group": {
            "three_quarter": {"path": "出图/共享/图片/定妆_X_45度.png", "status": "planned"}
        }
    })
    assert fdr.three_quarter_ready({
        "reference_group": {
            "three_quarter": {"path": "出图/共享/图片/定妆_X_45度.png", "status": "ready"}
        }
    })
    # atlas 没建但 reference_group 直接挂 45° 命名图（旧项目兼容）→ 就绪
    assert fdr.three_quarter_ready({"reference_group": {"three_quarter": "出图/共享/图片/定妆_X_45度.png"}})
    # 空路径不算
    assert not fdr.three_quarter_ready({"reference_group": {"three_quarter": ""}})
    # 啥都没有 → 未就绪
    assert not fdr.three_quarter_ready({})


def test_same_source_expression_ready_requires_non_neutral_ready_expression() -> None:
    assert not fdr.same_source_expression_ready({
        "reference_atlas": {"expression_refs": [
            {"path": "出图/共享/图片/定妆_沈念_常态_脸部特写.png", "status": "ready", "emotion": "中性"}
        ]}
    })
    assert fdr.same_source_expression_ready({
        "reference_atlas": {"expression_refs": [
            {"path": "出图/共享/图片/定妆_沈念_常态_表情_惊惶转冷静.png", "status": "ready", "emotion": "惊惶转冷静"}
        ]}
    })
    assert not fdr.same_source_expression_ready({
        "reference_group": {"expressions": [
            {"path": "出图/共享/图片/定妆_沈念_常态_表情_惊惶转冷静.png", "status": "planned", "emotion": "惊惶转冷静"}
        ]}
    })


def test_missing_3q_baseline() -> None:
    # core_full / recurring_standard 入镜即需要 3/4。
    assert fdr.missing_3q_baseline(appear=1, tq_ready=False)
    # 已备 ready → 不报
    assert not fdr.missing_3q_baseline(appear=6, tq_ready=True)
    # 未入镜 → 不报
    assert not fdr.missing_3q_baseline(appear=0, tq_ready=False)
    # named_minimal 普通镜不前置烧 3/4；近景/高危角度真正需要时才报。
    assert not fdr.missing_3q_baseline(appear=1, tq_ready=False, library_tier="named_minimal")
    assert fdr.missing_3q_baseline(
        appear=1, tq_ready=False, library_tier="named_minimal", shot_requires=True
    )


def test_analyze_flags_missing_3q_baseline(tmp_path: Path) -> None:
    root = tmp_path / "剧"
    (root / "出图" / "共享").mkdir(parents=True)
    (root / "脚本" / "第1集").mkdir(parents=True)
    (root / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({
        "characters": [{"id": "CHAR_01", "name": "沈念", "forms": [{
            "form": "常态", "asset_key": "沈念_常态",
            "identity_adapters": {"image": {"codex": {"status": "fallback_reference_group"}}},
            "reference_atlas": {"base_views": {"three_quarter": {"status": "planned"}}},
        }]}]
    }, ensure_ascii=False), encoding="utf-8")
    (root / "脚本" / "第1集" / "storyboard.json").write_text(json.dumps({
        "clips": [
            {"id": "Clip_01", "label": "沈念", "shots": [{"lens": "CU 85mm", "desc": "沈念 面部特写"}]},
            {"id": "Clip_02", "label": "沈念", "shots": [{"lens": "ECU", "desc": "沈念 反打"}]},
        ]
    }, ensure_ascii=False), encoding="utf-8")
    report = fdr.analyze(root, "第1集")
    shen = next(r for r in report["characters"] if r["character_id"] == "CHAR_01")
    assert "missing_3q_baseline" in shen["reference_gaps"]
    assert report["missing_3q_baseline"] == 1
    assert any("3/4 侧脸" in s and "角色库档位" in s for s in shen["suggestions"])


def test_score_reference_group_closeup_emotion_is_high() -> None:
    # multi_reference 底色 22 + 近景全占 30 + 大表情 3 镜(24) → high
    s = fdr.score_character({"appear": 4, "closeup": 4, "emotion": 3, "multi": 0, "angle": 0}, "multi_reference")
    assert s["band"] == "high"
    assert s["score"] >= fdr.BAND_HIGH
    assert s["drivers"][0]["points"] >= s["drivers"][-1]["points"]   # 已按贡献降序


def test_score_lora_low_signal_is_low() -> None:
    # LoRA 档（base 0）+ 极少高危信号 → low
    s = fdr.score_character({"appear": 5, "closeup": 1, "emotion": 0, "multi": 0, "angle": 0}, "lora")
    assert s["band"] == "low"


def test_score_native_midrange() -> None:
    s = fdr.score_character({"appear": 4, "closeup": 2, "emotion": 1, "multi": 0, "angle": 1}, "native_subject")
    assert s["band"] in {"medium", "high"}


def test_suggestions_align_with_expression_gate_and_image2image_first() -> None:
    scored = {"tier": "multi_reference", "band": "high"}
    sig = {"appear": 4, "closeup": 3, "emotion": 2, "multi": 2, "angle": 1}
    sug = fdr.suggestions_for("沈念", scored, sig, "CHAR_01", "常态", "/r/剧",
                              {"canonical": "dreamina", "label": "Dreamina/即梦官方 CLI"})
    joined = " ".join(sug)
    assert "expressions" in joined            # 对齐 ④ 表情库 gate
    assert "image2image / 多图参考链" in joined  # 本机 LoRA 慢速时默认回强参考链
    assert "LoRA 作为可选升档" in joined
    assert "多人同框" in joined
    assert "清空参考图" in joined              # Dreamina 的粘性参考框要单独提醒
    # 阈值化：单镜 multi（<2）不应触发"多人同框"样板话
    sug_thin = fdr.suggestions_for("沈念", scored, {"appear": 4, "closeup": 0, "emotion": 0, "multi": 1, "angle": 0},
                                   "CHAR_01", "常态")
    assert not any("多人同框" in s for s in sug_thin)
    # 低危角色（lora 档、无信号）→ 不强推 LoRA
    sug_low = fdr.suggestions_for("配角", {"tier": "lora", "band": "low"}, {"appear": 2}, "CHAR_X", "常态")
    assert not any("lora.py init" in s for s in sug_low)


def test_project_default_backend_keeps_nano_banana_separate(tmp_path: Path) -> None:
    root = tmp_path / "剧"
    root.mkdir()
    (root / "_设置.md").write_text("- 生图AI：Nano Banana\n", encoding="utf-8")
    assert fdr.project_default_backend(root) == "nano_banana"
    (root / "_设置.md").write_text("- 生图AI：Gemini\n", encoding="utf-8")
    assert fdr.project_default_backend(root) == "nano_banana"


def test_present_characters_matches_aliases() -> None:
    chars = [
        {"id": "CHAR_01", "aliases": {"沈念", "林婉儿"}},
        {"id": "CHAR_03", "aliases": {"柳娘子"}},
    ]
    present = fdr.present_characters("沈念抬手，柳娘子在画右冷笑", chars)
    assert {c["id"] for c in present} == {"CHAR_01", "CHAR_03"}
    assert fdr.present_characters("空镜，残烛摇曳", chars) == []


def _make_project(tmp_path: Path) -> Path:
    root = tmp_path / "剧"
    reg = root / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "identity_registry.json").write_text(json.dumps({"characters": [
        {"id": "CHAR_01", "name": "沈念 / 林婉儿", "forms": [{
            "form": "常态", "asset_key": "沈念_常态",
            "angle_policy": {"risky": ["face_too_small", "deep_shadow"]},
            "identity_adapters": {"image": {"codex": {"status": "fallback_reference_group"}},
                                  "lora": {"status": "not_needed"}},
        }]},
        {"id": "CHAR_03", "name": "柳娘子", "forms": [{
            "form": "人皮态", "asset_key": "柳娘子_人皮态",
            "angle_policy": {"risky": ["extreme_top"]},
            "identity_adapters": {"image": {"codex": {"status": "fallback_reference_group"}},
                                  "lora": {"status": "ready"}},
        }]},
    ]}, ensure_ascii=False), encoding="utf-8")
    (root / "_设置.md").write_text("- 生图AI：Codex\n", encoding="utf-8")
    sb = root / "脚本" / "第1集"
    sb.mkdir(parents=True)
    (sb / "storyboard.json").write_text(json.dumps({"clips": [
        {"id": "EP01_CLIP01", "label": "沈念崩溃", "scene": "冷宫/夜",
         "continuity": {"start_state": "沈念落泪", "end_state": "沈念失控"},
         "shots": [{"lens": "ECU 面部特写", "desc": "沈念崩溃落泪，柳娘子在画右冷笑"}]},
        {"id": "EP01_CLIP02", "label": "对峙", "scene": "冷宫",
         "shots": [{"lens": "CU 反打", "desc": "沈念怒视柳娘子"}]},
        {"id": "EP01_CLIP03", "label": "空镜", "scene": "庭院",
         "shots": [{"lens": "LS 远景", "desc": "残烛摇曳，无人物"}]},
    ]}, ensure_ascii=False), encoding="utf-8")
    return root


def test_analyze_end_to_end(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    rep = fdr.analyze(root, "第1集")
    assert rep["default_backend"] == "codex"
    by = {r["character_id"]: r for r in rep["characters"]}
    # 沈念：近景+大表情+多人同框，reference_group 底色 → high
    assert by["CHAR_01"]["band"] == "high"
    assert by["CHAR_01"]["signals"]["closeup"] == 2
    assert by["CHAR_01"]["signals"]["multi"] == 2   # CLIP01+CLIP02 都与柳娘子同框
    # 柳娘子：LoRA ready → 档位 lora，分被压低
    assert by["CHAR_03"]["tier"] == "lora"
    assert by["CHAR_03"]["score"] < by["CHAR_01"]["score"]
    # 排序：分高在前
    assert rep["characters"][0]["score"] >= rep["characters"][-1]["score"]


def test_analyze_blocks_core_high_risk_on_non_persistent_backend(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    reg = root / "出图" / "共享" / "identity_registry.json"
    data = json.loads(reg.read_text(encoding="utf-8"))
    data["characters"][0]["scope"] = "核心长线女主"
    reg.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    rep = fdr.analyze(root, "第1集")
    row = {r["character_id"]: r for r in rep["characters"]}["CHAR_01"]

    assert row["band"] == "block"
    assert "预测高危" in row["suggestions"][0]
    assert rep["blocking"] is True


def test_analyze_core_high_risk_project_memory_mitigates_predicted_block(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    reg = root / "出图" / "共享" / "identity_registry.json"
    data = json.loads(reg.read_text(encoding="utf-8"))
    data["characters"][0]["scope"] = "核心长线女主"
    reg.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    prompt_dir = root / "出图" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "01_分镜出图.md").write_text(
        "## Clip 01\n"
        "**参考图入参清单与预算**：backend=Codex；selected=[CHAR_01 front/face_anchor, CHAR_03 front/face_anchor]。\n"
        "**资产身份注册层**：`CHAR_01/常态`、`CHAR_03/人皮态`，从 identity_registry 继承 reference_group。\n"
        "**近景/反打身份锁定**：使用脸部特写与表情锚，尾帧 image2image 接力。\n"
        "**多人同框身份槽位**：LEFT_SLOT CHAR_01*；RIGHT_SLOT CHAR_03。\n"
        "**多人同框执行策略**：登记 `split_composite_required`，分别出图后分层合成。\n",
        encoding="utf-8",
    )

    rep = fdr.analyze(root, "第1集")
    row = {r["character_id"]: r for r in rep["characters"]}["CHAR_01"]

    assert row["band"] == "high"
    assert row["predicted_block_mitigated_by"] == "project_memory_reference_bundle"
    assert row["project_memory_mitigation"]["ready"] is True
    assert rep["blocking"] is False


def test_analyze_core_high_risk_expression_refs_mitigate_predicted_block(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    reg = root / "出图" / "共享" / "identity_registry.json"
    data = json.loads(reg.read_text(encoding="utf-8"))
    data["characters"][0]["scope"] = "核心长线女主"
    data["characters"][0]["forms"][0]["reference_atlas"] = {
        "expression_refs": [
            {"path": "出图/共享/图片/定妆_沈念_常态_表情_惊惶转冷静.png",
             "status": "ready", "emotion": "惊惶转冷静"}
        ]
    }
    reg.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    rep = fdr.analyze(root, "第1集")
    row = {r["character_id"]: r for r in rep["characters"]}["CHAR_01"]

    assert row["band"] == "high"
    assert row["predicted_block_mitigated_by"] == "same_source_expression_refs"
    assert rep["blocking"] is False


def test_run_writes_reports(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    rep = fdr.run(root, "第1集")
    assert Path(rep["json_path"]).is_file()
    assert Path(rep["markdown_path"]).is_file()
    assert "脸漂风险" in Path(rep["markdown_path"]).read_text(encoding="utf-8")


# ── ② 实测漂移回灌：identity_drift_report.json → block ──────────────────────────

def test_measured_block_reason_composes() -> None:
    reason = fdr.measured_block_reason(
        {"embedding_drift_high": 1, "spans": "第1集→第2集(掉0.2)", "total_block": 0})
    assert "质心漂移 high×1" in reason and "第1集→第2集" in reason
    reason2 = fdr.measured_block_reason(
        {"embedding_drift_high": 0, "total_block": 3, "first_bad_episode": "第2集"})
    assert "block 级脸漂 3 镜" in reason2 and "first=第2集" in reason2


def test_measured_drift_block_embedding_high() -> None:
    drift = {"available": True, "characters": {}, "embedding_drift": {
        "沈念": [{"episode_from": "第1集", "episode_to": "第2集", "drop": 0.2, "severity": "high"}]}}
    hit = fdr.measured_drift_block(drift, {"沈念", "沈念_常态"}, "沈念 / 林婉儿")
    assert hit and hit["embedding_drift_high"] == 1
    # warn 级（非 high）不命中
    drift_warn = {"available": True, "characters": {},
                  "embedding_drift": {"沈念": [{"severity": "medium"}]}}
    assert fdr.measured_drift_block(drift_warn, {"沈念"}, "沈念") is None


def test_measured_drift_block_total_block_and_alias_match() -> None:
    drift = {"available": True, "embedding_drift": {},
             "characters": {"柳娘子": {"total_block": 2, "first_bad_episode": "第3集"}}}
    # alias 对号（drift char == name）
    assert fdr.measured_drift_block(drift, {"柳娘子"}, "柳娘子")["total_block"] == 2
    # 对不上号 → None（别人的漂移不算到本角色头上）
    assert fdr.measured_drift_block(drift, {"沈念"}, "沈念") is None


def test_measured_drift_block_respects_available_flag() -> None:
    # available=False（无 insightface / 跳过机检）→ 一律 None，不假报
    drift = {"available": False, "embedding_drift": {
        "沈念": [{"severity": "high"}]}, "characters": {}}
    assert fdr.measured_drift_block(drift, {"沈念"}, "沈念") is None


def _write_drift_report(root: Path, payload: dict) -> None:
    out = root / "生产数据"
    out.mkdir(parents=True, exist_ok=True)
    (out / "identity_drift_report.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_analyze_escalates_to_block_on_measured_drift(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    _write_drift_report(root, {"available": True, "characters": {}, "embedding_drift": {
        "沈念": [{"episode_from": "第1集", "episode_to": "第2集", "drop": 0.2, "severity": "high"}]}})
    rep = fdr.analyze(root, "第1集")
    by = {r["character_id"]: r for r in rep["characters"]}
    # 沈念实测已漂 → block（盖过原本的 high 预测）
    assert by["CHAR_01"]["band"] == "block"
    assert by["CHAR_01"].get("measured_drift")
    assert rep["block"] == 1 and rep["blocking"] is True
    assert rep["prior_drift_available"] is True
    # block 排在最前
    assert rep["characters"][0]["character_id"] == "CHAR_01"
    # 第一条建议是实测漂移的硬处置
    assert "实测" in by["CHAR_01"]["suggestions"][0]


def test_analyze_no_drift_report_stays_predictive(tmp_path: Path) -> None:
    root = _make_project(tmp_path)  # 不写 identity_drift_report.json
    rep = fdr.analyze(root, "第1集")
    assert rep["block"] == 0 and rep["blocking"] is False
    assert rep["prior_drift_available"] is False
    assert {r["character_id"]: r for r in rep["characters"]}["CHAR_01"]["band"] == "high"


# ── 复现间隔回灌（B4：长间隔再登场 = EntityBench 2026 跨镜崩脸主因，出图前重锚） ──

def test_episode_num_parses_and_degrades() -> None:
    assert fdr._episode_num("第12集") == 12
    assert fdr._episode_num("序章") is None


def test_score_character_recurrence_gap_adds_points_and_driver() -> None:
    base = fdr.score_character({"appear": 3, "closeup": 0, "emotion": 0, "multi": 0, "angle": 0}, "multi_reference")
    reentry = fdr.score_character(
        {"appear": 3, "closeup": 0, "emotion": 0, "multi": 0, "angle": 0, "recurrence_gap": 3}, "multi_reference")
    assert reentry["score"] > base["score"]
    assert any("长间隔再登场" in d["factor"] for d in reentry["drivers"])
    # 缺席仅1集（< 阈值2）不加分
    short = fdr.score_character(
        {"appear": 3, "closeup": 0, "emotion": 0, "multi": 0, "angle": 0, "recurrence_gap": 1}, "multi_reference")
    assert short["score"] == base["score"]


def test_in_context_strong_credits_multi_reference_base_only() -> None:
    # C5/记功：strong-in-context 模型（GPT Image 2）在 multi_reference 档集内 base 减分（22→16）。
    plain = fdr.score_character({"appear": 3, "closeup": 0, "emotion": 0, "multi": 0, "angle": 0}, "multi_reference")
    strong = fdr.score_character(
        {"appear": 3, "closeup": 0, "emotion": 0, "multi": 0, "angle": 0}, "multi_reference", "strong")
    assert strong["score"] == plain["score"] - fdr.WEIGHTS["in_context_strong_credit"]
    assert any("in-context 记功" in d["factor"] and d["points"] < 0 for d in strong["drivers"])
    # 下限：记功后 base 永不低于 face_embedding(14) → 仍严格高于真脸嵌入锁档
    assert strong["score"] - 0 >= fdr.WEIGHTS["base_face_embedding"]
    # moderate / 空 → 不记功（dreamina/nano 等保守，旧行为不变）
    assert fdr.score_character(
        {"appear": 3, "closeup": 0, "emotion": 0, "multi": 0, "angle": 0}, "multi_reference", "moderate"
    )["score"] == plain["score"]


def test_in_context_credit_does_not_touch_cross_episode_or_other_tiers() -> None:
    # 跨集不放水：recurrence_gap 跨集项不受 in-context 记功影响（记功只抵 base）。
    re_plain = fdr.score_character(
        {"appear": 3, "closeup": 0, "emotion": 0, "multi": 0, "angle": 0, "recurrence_gap": 3}, "multi_reference")
    re_strong = fdr.score_character(
        {"appear": 3, "closeup": 0, "emotion": 0, "multi": 0, "angle": 0, "recurrence_gap": 3}, "multi_reference", "strong")
    assert re_plain["score"] - re_strong["score"] == fdr.WEIGHTS["in_context_strong_credit"]
    # 非 multi_reference 档（如 reference_group）即便 strong 也不记功——记功只针对无持久主体的多参考档
    rg_plain = fdr.score_character({"appear": 3, "closeup": 0, "emotion": 0, "multi": 0, "angle": 0}, "reference_group")
    rg_strong = fdr.score_character(
        {"appear": 3, "closeup": 0, "emotion": 0, "multi": 0, "angle": 0}, "reference_group", "strong")
    assert rg_strong["score"] == rg_plain["score"]


def test_codex_profile_is_model_led_not_channel_shell() -> None:
    # C5 贯通：执行真值表 IMAGE_IDENTITY_PROFILES 必须指认到模型名，不再用纯渠道壳。
    prof = fdr.backend_profile("codex")
    assert prof.get("model") == "GPT Image 2"
    assert prof.get("channel") == "Codex CLI"
    assert prof.get("in_context_consistency") == "strong"
    assert "GPT Image 2" in str(prof.get("label"))


def test_recurrence_reentry_risk_matches_alias_and_gap() -> None:
    drift = {"characters": {"沈念": {"episodes": {"第1集": {}, "第2集": {}}}}}
    # 本集第5集，上次出场第2集 → 缺席2集，命中
    hit = fdr.recurrence_reentry_risk(drift, {"沈念", "林婉儿"}, "林婉儿", "第5集")
    assert hit == {"last_episode": "第2集", "gap": 2, "current_episode": "第5集"}
    # 本集第3集，上次第2集 → 缺席0集，不命中
    assert fdr.recurrence_reentry_risk(drift, {"沈念"}, "沈念", "第3集") is None
    # 对不上号 → None
    assert fdr.recurrence_reentry_risk(drift, {"柳娘子"}, "柳娘子", "第9集") is None
    # 复现不依赖 insightface：available 缺省也能算
    assert fdr.recurrence_reentry_risk({"characters": {}}, set(), "x", "第9集") is None


def test_analyze_reentry_escalates_and_reanchors(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    # 第4集分镜：沈念单镜出场（无近景/表情/同框等其它高危信号，隔离复现因子）
    sb = root / "脚本" / "第4集"
    sb.mkdir(parents=True)
    (sb / "storyboard.json").write_text(json.dumps({"clips": [
        {"id": "EP04_CLIP01", "label": "沈念归来", "scene": "宫道",
         "shots": [{"lens": "MS 中景", "desc": "沈念缓步而来"}]},
    ]}, ensure_ascii=False), encoding="utf-8")
    # 已机检漂移报告：沈念仅在第1集出场 → 到第4集缺席2集
    (root / "生产数据").mkdir(parents=True)
    (root / "生产数据" / "identity_drift_report.json").write_text(json.dumps({
        "available": True, "characters": {"沈念": {"episodes": {"第1集": {}}}},
    }, ensure_ascii=False), encoding="utf-8")
    rep = fdr.analyze(root, "第4集")
    row = {r["character_id"]: r for r in rep["characters"]}["CHAR_01"]
    assert row["recurrence_reentry"] == {"last_episode": "第1集", "gap": 2, "current_episode": "第4集"}
    assert row["signals"]["recurrence_gap"] == 2
    assert rep["recurrence_reentries"] == 1
    assert "长间隔再登场" in row["suggestions"][0]  # 重锚建议置顶


# ── 含人共享资产镜脸漂诊断（治诊断侧盲区·#7 续） ──
def _mk_reg(tmp_path, assets):
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "asset_registry.json").write_text(
        json.dumps({"assets": assets}, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_assess_shared_asset_faceless_low_and_none_skipped(tmp_path):
    root = _mk_reg(tmp_path, [
        {"id": "WEAPON_H", "type": "weapon", "owner": "CHAR_J", "name": "戟",
         "reference_group": {"scale_reference": "图片/定妆_握持比例.png"}},   # faceless → low
        {"id": "WEAPON_PLAIN", "type": "weapon", "name": "纯武器美术"},        # none → skip
    ])
    sa = fdr.assess_shared_asset_face_risk(root, [])
    ids = {a["asset_id"]: a for a in sa["assets"]}
    assert ids["WEAPON_H"]["band"] == "low" and ids["WEAPON_H"]["face_policy"] == "faceless"
    assert "WEAPON_PLAIN" not in ids and sa["low"] == 1


def test_assess_shared_asset_face_locked_no_owner_high(tmp_path):
    root = _mk_reg(tmp_path, [{"id": "POSTER_BAD", "type": "poster", "name": "群像海报 人物"}])
    sa = fdr.assess_shared_asset_face_risk(root, [])
    a = [x for x in sa["assets"] if x["asset_id"] == "POSTER_BAD"][0]
    assert a["band"] == "high" and a["face_policy"] == "face_locked" and sa["high"] == 1


def test_assess_shared_asset_face_locked_with_anchor_medium(tmp_path):
    root = _mk_reg(tmp_path, [
        {"id": "WEAPON_ACT", "type": "weapon", "owner": "CHAR_J", "name": "持械动作参考",
         "reference_group": {"primary": "图片/定妆_WEAPON_ACT_动作_持.png"}}])
    chars = [{"id": "CHAR_J", "forms": [{"form": "常态",
              "reference_group": {"face": "出图/共享/图片/定妆_CHAR_J_脸.png"}}]}]
    sa = fdr.assess_shared_asset_face_risk(root, chars)
    a = [x for x in sa["assets"] if x["asset_id"] == "WEAPON_ACT"][0]
    assert a["band"] == "medium" and a["face_policy"] == "face_locked"


def test_analyze_includes_shared_asset_face_risk_key(tmp_path):
    root = _mk_reg(tmp_path, [{"id": "WEAPON_PLAIN", "type": "weapon", "name": "纯武器美术"}])
    rep = fdr.analyze(root, "第1集")
    assert "shared_asset_face_risk" in rep and rep["shared_asset_face_risk"]["available"] is True
