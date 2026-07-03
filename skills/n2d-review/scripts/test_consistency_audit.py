"""consistency_audit.summarize 纯函数单测（无依赖）。
cd skills/n2d-review/scripts && python -m pytest test_consistency_audit.py
"""
import consistency_audit as ca  # noqa: F401  （导入即把 n2d/_lib 放进 sys.path）
import n2d_schema


def test_gate_unaudited_dimensions_allowlist_locked():
    # #4：把「无 gate 机检 runner（空 audit_labels）」的维度钉成显式 allowlist，
    # 防未来新增维度漏配 audit_labels 而**静默**失去机检（schema 模块加载已断言，这里给可读回归）。
    empty = {k for k, v in n2d_schema.CONSISTENCY_DIMENSIONS.items() if not v.get("audit_labels")}
    assert empty == n2d_schema.GATE_UNAUDITED_DIMENSIONS
    # 2026-06：audio_visual_sync 已接入 音画同步(AV1)，rhythm_density 已接入 节奏密度(Rhythm)。
    assert n2d_schema.GATE_UNAUDITED_DIMENSIONS == frozenset()


def test_all_consistency_audit_sections_are_score_mapped():
    # 新增检测器必须进入 n2d_schema audit_labels，否则 gate 能看见但 n2d-score 不会扣分。
    expected = {
        "语义谱系(P0)", "状态百科(P1)", "多模态(P2)", "契约继承", "锚点门(N3)", "脸(G1)",
        "无脸崩坏(G1b)", "跨集脸漂(G5)",
        "服装配色(N1)", "发型(H1)", "辨识标记(MK1)", "片内时序(N2)", "场景(O2)", "风格(S1)", "接缝接力",
        "称谓口头禅(A1)", "字幕对齐(L1)", "糊/低质(N4)", "手部/解剖(N5)", "身高比例(R1)",
        "轴线视线(X1)", "天气时辰(W1)", "字幕安全区(L2)", "音画同步(AV1)", "空间站位(B1)",
        "节奏密度(Rhythm)", "物件常驻(O3)", "持有账本(POS)", "视线状态回读(X2)",
        "状态转场视频证据(ST1)", "交互接触(I1)", "结构化交互图谱(I2)", "物理事件图(PHY)",
        "视频证据完整性(EVID)", "实体记忆(EMB)", "成片统一(C1)",
        "成片时间线探针(FT1)", "生成配方(RCP)", "强配方Schema(RCP2)", "系列包装(PKG)",
        "台词语域(D1)", "场景平面(FP1)", "成本路由(K1)", "人审校准集(CAL)", "一致性探针包(PROBE)",
        "视频VLM判题(VLM1)", "视频语义一致(VSEM)", "多人对话音画(DAV)", "物理因果链(CG1)",
        "相机空间轨迹(CAM1)", "运动质量(MOT1)", "主体视频一致(S2V)",
        "高动态成片证据(SPECV)",
        # 2026-06 一致性加固第二批（extended_consistency）
        "系统面板(UI1)", "音乐母题(LM1)", "系列调色(GRD)", "环境声(AMB)",
        "跨集体型(R2)", "在场检测(O3V)", "外观判官(VAP)",
        # 第三批：图中文字 OCR 校验 + 译名一致
        "文字渲染(OCR1)", "译名一致(TX1)",
        # 镜头光学：景深/虚化一致
        "景深一致(DOF1)",
        # 特效颜色窜色 + 色温调色
        "特效窜色(VFXC)", "色温调色(GRADE1)",
        # D 档音频白区：配音情绪弧 / 口音方言 / 音乐衔接
        "配音情绪弧(VEA)", "口音方言(ACC)", "音乐衔接(BGM)",
        # 表情过锁 / copy-paste 冻脸（report-only·IPRO 减害）
        "表情过锁(EXP3)",
    }
    mapped = {
        label
        for spec in n2d_schema.CONSISTENCY_DIMENSIONS.values()
        for label in spec.get("audit_labels", ())
    }
    assert expected <= mapped


def test_noface_violation_rows_recovers_expected_character_shots():
    # A4：应在场具名角色却 noface → warn（不再静默丢弃）；合法无脸镜不报。
    fr = {"available": True, "shots": [
        {"png": "Clip_01.png", "verdict": "noface", "chars": ["沈念"]},
        {"png": "Clip_02.png", "verdict": "noface", "chars": []},
        {"png": "Clip_03.png", "verdict": "ok", "chars": ["沈念"]},
    ]}
    rows = ca.noface_violation_rows("第1集", fr)
    assert [r["png"] for r in rows] == ["Clip_01.png"]
    assert rows[0]["verdict"] == "warn"


def test_cross_episode_face_rows_flags_systematic_decline(tmp_path):
    import os
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "生产数据"), exist_ok=True)
    # A3：ep1 基线 0.80，ep2 掉到 0.60（掉幅 0.20 ≥ block 阈）→ block 行。
    ca.cross_episode_face_rows(root, "第1集", {"available": True, "characters": {"沈念": {"ep_mean_score": 0.80}}})
    rows = ca.cross_episode_face_rows(root, "第2集", {"available": True, "characters": {"沈念": {"ep_mean_score": 0.60}}})
    assert any(r["verdict"] == "block" and "沈念" in r["shot"] for r in rows)
    # 单集不报（只有一集历史）。
    one = ca.cross_episode_face_rows(str(tmp_path / "solo"), "第1集",
                                     {"available": True, "characters": {"沈念": {"ep_mean_score": 0.80}}})
    assert one == []


def test_probe_advanced_metrics_missing_does_not_flip_degraded(monkeypatch):
    import importlib.util as ilu
    present = {"insightface", "PIL"}  # 假装脸/像素依赖齐，torch 缺
    monkeypatch.setattr(ilu, "find_spec", lambda name: object() if name in present else None)
    caps = ca.probe_capabilities()
    assert caps["pillow"] and caps["insightface"] and caps["torch"] is False
    # torch(DINOv2) 缺只进 advisory notes，绝不把精度判定打成 degraded（否则误触 production BLOCK）。
    assert caps["degraded"] is False
    assert any("DINOv2" in n for n in caps["notes"])
    assert caps.get("advanced_metrics_missing")


def test_summarize_counts_and_total_block():
    sections = {
        "脸(G1)": {"skipped": False, "verdicts": ["ok", "ok", "block", "warn"]},
        "服装配色(N1)": {"skipped": False, "verdicts": ["ok", "block"]},
        "片内时序(N2)": {"skipped": True, "verdicts": []},
    }
    s = ca.summarize(sections)
    assert s["total_block"] == 2
    assert s["by_dim"]["脸(G1)"] == {"block": 1, "warn": 1, "ok": 2, "n": 4, "skipped": False}
    assert s["by_dim"]["服装配色(N1)"]["block"] == 1
    assert s["by_dim"]["片内时序(N2)"]["skipped"] is True
    assert s["by_dim"]["片内时序(N2)"]["n"] == 0


def test_summarize_empty():
    s = ca.summarize({})
    assert s["total_block"] == 0 and s["by_dim"] == {}


def test_exit_code_for_production_blocks_degraded_precision():
    summary = {"total_block": 0, "precision_level": "degraded"}
    assert ca.exit_code_for(summary, profile="demo") == 0
    assert ca.exit_code_for(summary, profile="production") == 1


def test_section_details_keep_return_scope():
    sec = ca.section_from_result(
        dim="状态百科(P1)",
        result={"alerts": [{"verdict": "warn", "shot": 3, "message": "漏写左颊新伤"}], "notes": []},
        detail_key="alerts",
        skipped=False,
        ep="第1集",
        stage="image",
        default_artifacts=("出图/第1集/prompt/01_分镜出图.md",),
    )
    assert sec["verdicts"] == ["warn"]
    assert sec["details"][0]["affected_shots"] == ["Clip_03"]
    assert "出图/第1集/prompt/01_分镜出图.md" in sec["details"][0]["affected_artifacts"]


def test_auto_return_tasks_group_details():
    sections = {
        "状态百科(P1)": {
            "return_to_stage": "image",
            "rerun_scope": "修状态锁",
            "details": [{
                "verdict": "warn",
                "message": "漏写状态",
                "affected_shots": ["Clip_03"],
                "affected_artifacts": ["出图/第1集/prompt/01_分镜出图.md"],
            }],
        }
    }
    tasks = ca.build_auto_return_tasks(sections)
    assert tasks[0]["return_to_stage"] == "image"
    assert tasks[0]["affected_shots"] == ["Clip_03"]
    assert "定位镜头：Clip_03" in tasks[0]["scope"]


def test_findings_payload_and_export(tmp_path):
    """结构化外发：payload 带契约 kind；export 落 生产数据/consistency_findings_<集>.json。"""
    import json

    res = {
        "root": str(tmp_path),
        "episode": "第1集",
        "summary": {"by_dim": {"脸(G1)": {"block": 1, "warn": 0, "ok": 0, "skipped": False}}, "total_block": 1},
        "sections": {},
        "findings": [{"dim": "脸(G1)", "sev": "block", "loc": "Clip_02", "msg": "崩脸", "return_to_stage": "image"}],
        "auto_return_tasks": [{
            "return_to_stage": "image",
            "scope": "脸(G1) 返修；定位镜头：Clip_02",
            "affected_artifacts": ["出图/第1集/图片/Clip_02.png"],
            "affected_shots": ["Clip_02"],
        }],
    }
    payload = ca.findings_payload(res)
    assert payload["kind"] == "n2d_consistency_findings"
    assert payload["episode"] == "第1集"
    assert payload["findings"][0]["return_to_stage"] == "image"
    assert payload["auto_return_tasks"][0]["affected_shots"] == ["Clip_02"]

    path = ca.export_findings(str(tmp_path), "第1集", res)
    data = json.loads(open(path, encoding="utf-8").read())
    assert data["kind"] == "n2d_consistency_findings"
    assert data["auto_return_tasks"][0]["scope"].startswith("脸(G1)")
    assert path.endswith("consistency_findings_第1集.json")
    ledger_path = tmp_path / "生产数据" / "consistency_ledger_第1集.json"
    assert ledger_path.exists()
    assert json.loads(ledger_path.read_text(encoding="utf-8"))["kind"] == "n2d_consistency_ledger"


def test_contract_inheritance_result_becomes_video_prompt_task(tmp_path):
    ep = "第1集"
    img = tmp_path / "出图" / ep / "prompt" / "00_总览.md"
    vid = tmp_path / "出视频" / ep / "prompt" / "00_总览.md"
    img.parent.mkdir(parents=True)
    vid.parent.mkdir(parents=True)
    img.write_text(
        "\n".join([
            "## 本集视觉一致性契约",
            "- 色调基线：冷青",
            "- 场景光位锚：左侧烛火",
            "- 场景轴线视线：沈念画左，柳娘子画右",
            "- 角色状态演进：无",
            "- 景别阶梯：中近景",
        ]),
        encoding="utf-8",
    )
    vid.write_text(
        "\n".join([
            "## 本集视觉一致性契约",
            "- 色调基线：冷青",
            "- 场景光位锚：右侧月光",
            "- 场景轴线视线：沈念画右，柳娘子画左",
            "- 角色状态演进：无",
            "- 景别阶梯：中近景",
        ]),
        encoding="utf-8",
    )
    res = ca.contract_inheritance_result(str(tmp_path), ep)
    sec = ca.section_from_result(
        dim="契约继承",
        result=res,
        detail_key="fields",
        skipped=not res.get("available"),
        ep=ep,
        stage="video_prompt",
        default_artifacts=(f"出图/{ep}/prompt/00_总览.md", f"出视频/{ep}/prompt/00_总览.md"),
    )
    tasks = ca.build_auto_return_tasks({"契约继承": sec})
    assert any(v == "block" for v in sec["verdicts"])
    assert tasks[0]["return_to_stage"] == "video_prompt"
    assert "出视频/第1集/prompt/00_总览.md" in tasks[0]["affected_artifacts"]


# ── G1↔EXP1 调和：像素确认大表情形变 → G1 脸 block 降 warn（破除「奖励面瘫」掣肘）──
def test_clip_num_parsing():
    assert ca._clip_num("图片/Clip_05_face.png") == 5
    assert ca._clip_num("Clip5") == 5
    assert ca._clip_num("镜12") == 12
    assert ca._clip_num("8") == 8
    assert ca._clip_num("") is None
    assert ca._clip_num(None) is None


def test_expression_confirmed_clips_only_real_motion():
    expr = {"findings": [
        {"shot": "Clip_03", "verdict": "ok", "mouth_change": 0.45, "eye_change": 2.0},   # 嘴大动 → 收
        {"shot": "Clip_04", "verdict": "ok", "mouth_change": 0.05, "eye_change": 0.10},  # 两者皆低于阈值 → 不收
        {"shot": "Clip_05", "verdict": "warn", "mouth_change": 0.02, "eye_change": 0.1},  # 声称大却没动 → 绝不收
        {"shot": "Clip_06", "verdict": "ok", "note": "无尾帧"},                            # 占位无形变 → 不收
        {"shot": "Clip_07", "verdict": "ok", "mouth_change": 0.10, "eye_change": 0.40},   # 眼睑大动 → 收
    ]}
    got = ca.expression_confirmed_clips(expr)
    assert got == {3, 7}


def test_reconcile_face_with_expression_downgrades_only_confirmed_blocks():
    face = {"shots": [
        {"png": "图片/Clip_03_a.png", "verdict": "block"},   # 在确认集 → 降 warn
        {"png": "图片/Clip_09_a.png", "verdict": "block"},   # 不在确认集 → 保持 block（真崩脸）
        {"png": "图片/Clip_03_b.png", "verdict": "ok"},      # 非 block → 不动
    ]}
    n = ca.reconcile_face_with_expression(face, {3})
    assert n == 1
    s0 = face["shots"][0]
    assert s0["verdict"] == "warn" and s0["abs_verdict"] == "block" and s0["expression_span_expected"] is True
    assert face["shots"][1]["verdict"] == "block"   # 未确认的崩脸不放过
    assert face["shots"][2]["verdict"] == "ok"
    # 空确认集（无 insightface）→ 完全不动
    face2 = {"shots": [{"png": "图片/Clip_03_a.png", "verdict": "block"}]}
    assert ca.reconcile_face_with_expression(face2, set()) == 0
    assert face2["shots"][0]["verdict"] == "block"


# ── EXP3 表情过锁 / copy-paste 冻脸（report-only·IPRO 减害）──────────────────────

def test_overlock_signal_a_systemic_flat_warns():
    # ≥2 个「声称大但像素零形变」镜 → 系统性过锁 WARN（带实测 Δ 才算）
    expr = {"available": True, "findings": [
        {"shot": "Clip_01", "verdict": "warn", "mouth_change": 0.01, "eye_change": 0.2},
        {"shot": "Clip_03", "verdict": "warn", "mouth_change": 0.00, "eye_change": 0.1},
        {"shot": "Clip_05", "verdict": "ok", "mouth_change": 0.40, "eye_change": 2.0},
        {"shot": "Clip_07", "verdict": "warn", "note": "无尾帧"},  # 无实测 Δ → 不计
    ]}
    rows = ca.expression_overlock_findings(expr, {"available": False}, {})
    warns = [r for r in rows if r["verdict"] == "warn"]
    assert len(warns) == 1
    assert "系统性" in warns[0]["message"] and "Clip_01" in warns[0]["message"]


def test_overlock_signal_a_single_flat_no_warn():
    expr = {"available": True, "findings": [
        {"shot": "Clip_01", "verdict": "warn", "mouth_change": 0.01, "eye_change": 0.2},
    ]}
    rows = ca.expression_overlock_findings(expr, {"available": False}, {})
    assert not [r for r in rows if r["verdict"] == "warn"]  # 单镜归 EXP1，不重复


def test_overlock_signal_b_copypaste_fingerprint_info():
    # 宽情绪角色脸跨镜余弦近乎恒定 → INFO copy-paste 指纹
    face = {"available": True, "shots": [
        {"char": "CHAR_01", "score": 0.991, "verdict": "ok"},
        {"char": "CHAR_01", "score": 0.992, "verdict": "ok"},
        {"char": "CHAR_01", "score": 0.990, "verdict": "ok"},
    ]}
    char_emo = {"CHAR_01": {"emotions": {"悲", "怒", "喜"}, "closeups": 3}}
    rows = ca.expression_overlock_findings({"available": True, "findings": []}, face, char_emo)
    infos = [r for r in rows if r["verdict"] == "info"]
    assert len(infos) == 1 and "copy-paste" in infos[0]["message"]


def test_overlock_signal_b_natural_variation_no_flag():
    # 有自然散度的脸（spread≥阈值）→ 不判过锁
    face = {"available": True, "shots": [
        {"char": "CHAR_01", "score": 0.99, "verdict": "ok"},
        {"char": "CHAR_01", "score": 0.95, "verdict": "ok"},
        {"char": "CHAR_01", "score": 0.93, "verdict": "ok"},
    ]}
    char_emo = {"CHAR_01": {"emotions": {"悲", "怒", "喜"}, "closeups": 3}}
    rows = ca.expression_overlock_findings({"available": True, "findings": []}, face, char_emo)
    assert not [r for r in rows if r["verdict"] == "info"]


def test_overlock_signal_c_text_fallback_info():
    # 无像素也无脸数据 → 宽情绪角色文本兜底 INFO
    char_emo = {"CHAR_01": {"emotions": {"悲", "怒", "喜", "惊"}, "closeups": 4}}
    rows = ca.expression_overlock_findings({"available": False}, {"available": False}, char_emo)
    infos = [r for r in rows if r["verdict"] == "info"]
    assert len(infos) == 1 and "过锁风险" in infos[0]["message"]


def test_overlock_never_blocks():
    # 任何信号都不得产出 block（report-only 铁律）
    expr = {"available": True, "findings": [
        {"shot": f"Clip_{i}", "verdict": "warn", "mouth_change": 0.0, "eye_change": 0.0}
        for i in range(5)]}
    face = {"available": True, "shots": [
        {"char": "CHAR_01", "score": 0.99, "verdict": "ok"} for _ in range(4)]}
    char_emo = {"CHAR_01": {"emotions": {"悲", "怒", "喜"}, "closeups": 4}}
    rows = ca.expression_overlock_findings(expr, face, char_emo)
    assert rows and not any(r["verdict"] == "block" for r in rows)


# ── P3：曾经 report-only 的 EXP2/MG1/ASP 现接入 audit→gate（不再只落 ledger）──

def test_exp2_block_reaches_audit_findings(tmp_path):
    """storyboard state_delta 改 identity_invariant 又没进 allowed_state_deltas →
    EXP2 block 必须出现在 consistency_audit 的 findings（证明孤儿已进闸）。"""
    import json, os
    root = str(tmp_path)
    shared = os.path.join(root, "出图", "共享")
    ep_dir = os.path.join(root, "脚本", "第1集")
    os.makedirs(shared); os.makedirs(ep_dir)
    json.dump({"characters": [
        {"id": "CHAR_01", "name": "沈念", "identity_invariants": ["eye_color"], "allowed_state_deltas": []}
    ]}, open(os.path.join(shared, "identity_registry.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({"clips": [
        {"id": "Clip_01", "character_ids": ["CHAR_01"],
         "continuity": {"state_delta": {"eye_color": "蓝→红"}}}
    ]}, open(os.path.join(ep_dir, "storyboard.json"), "w", encoding="utf-8"), ensure_ascii=False)
    rep = ca.exstate.run(root, "第1集")
    assert any(f["severity"] == "block" and "EXP2" in f["dimension"] for f in rep["findings"])
    # 段已注册进 schema audit_labels（角色身份维度），不会被 score 漏扣
    import n2d_schema
    mapped = {lbl for spec in n2d_schema.CONSISTENCY_DIMENSIONS.values() for lbl in spec.get("audit_labels", ())}
    assert "状态化表情(EXP2)" in mapped
    assert "运动语法(MG1)" in mapped
    assert "声音空间(ASP)" in mapped


# ───────────────────────────────────────────────────────────────────────────
# 证据等级账本 evidence_grade（#3）：proof_type 可见化 + advanced tier 的 under_proven
# 运行：cd skills/n2d-review/scripts && python -m pytest test_consistency_audit.py -k evidence_grade
# ───────────────────────────────────────────────────────────────────────────
def test_evidence_grade_torch_missing_marks_s2v_under_proven():
    sections = {"主体视频一致(S2V)": {"skipped": False, "verdicts": ["ok"]}}
    eg = ca.evidence_grade(sections, {"pillow": True, "insightface": True, "torch": False})
    rec = eg["by_dim"]["主体视频一致(S2V)"]
    assert rec["tier"] == "advanced" and rec["actual"] == "structured" and rec["achievable"] == "embedding"
    assert rec["under_proven"] is True
    assert "主体视频一致(S2V)" in eg["under_proven"]


def test_evidence_grade_torch_present_s2v_at_grade():
    sections = {"主体视频一致(S2V)": {"skipped": False, "verdicts": ["ok"]}}
    eg = ca.evidence_grade(sections, {"pillow": True, "insightface": True, "torch": True})
    assert eg["by_dim"]["主体视频一致(S2V)"]["actual"] == "embedding"
    assert eg["under_proven"] == []


def test_evidence_grade_skipped_no_content_not_under_proven():
    # S2V 无视频内容（出图阶段）→ 不可适用，不 PENDING（避免无内容误报）
    sections = {"主体视频一致(S2V)": {"skipped": True}}
    eg = ca.evidence_grade(sections, {"pillow": True, "insightface": True, "torch": False})
    assert eg["by_dim"]["主体视频一致(S2V)"]["applicable"] is False
    assert eg["under_proven"] == []


def test_evidence_grade_pixel_tier_degraded_is_visible_not_double_blocked():
    # insightface 缺 → 脸只到 declared（可见），但 pixel tier 不计 under_proven（全局 precision 闸处置）
    sections = {"脸(G1)": {"skipped": False, "precision": "degraded", "verdicts": ["ok"]}}
    eg = ca.evidence_grade(sections, {"pillow": True, "insightface": False, "torch": True})
    rec = eg["by_dim"]["脸(G1)"]
    assert rec["tier"] == "pixel" and rec["actual"] == "declared" and rec["achievable"] == "embedding"
    assert rec["under_proven"] is False
    assert eg["weakest"] == "declared"  # 最弱级仍诚实反映降级


def test_evidence_grade_pixel_full_and_structured_ok():
    sections = {
        "脸(G1)": {"skipped": False, "precision": "full", "verdicts": ["ok"]},
        "称谓口头禅(A1)": {"skipped": False, "verdicts": ["ok"]},
    }
    eg = ca.evidence_grade(sections, {"pillow": True, "insightface": True, "torch": True})
    assert eg["by_dim"]["脸(G1)"]["actual"] == "embedding"
    assert eg["by_dim"]["称谓口头禅(A1)"]["actual"] == "structured"
    assert eg["under_proven"] == []


# ───────────────────────────────────────────────────────────────────────────
# 跨集场景漂移 SCNX（#5）：场景轴此前无跨集机检（脸有 G5），补色调指纹累积比对
# 运行：cd skills/n2d-review/scripts && python -m pytest test_consistency_audit.py -k scene_drift
# ───────────────────────────────────────────────────────────────────────────
def test_scene_hist_l1_basic():
    assert ca.scene_hist_l1([0.5, 0.5], [0.5, 0.5]) == 0.0
    assert ca.scene_hist_l1([1.0, 0.0], [0.0, 1.0]) == 2.0
    assert ca.scene_hist_l1([0.5], [0.5, 0.5]) == 0.0  # 长度不一→0（不误判）


def test_scene_drift_stable_scene_no_rows():
    means = {"第1集": {"大殿": [0.5, 0.5]}, "第2集": {"大殿": [0.5, 0.5]}}
    assert ca.scene_drift_rows(means, "第2集") == []


def test_scene_drift_non_core_warns():
    means = {"第1集": {"大殿": [1.0, 0.0]}, "第2集": {"大殿": [0.0, 1.0]}}
    rows = ca.scene_drift_rows(means, "第2集")
    assert len(rows) == 1 and rows[0]["verdict"] == "warn" and "大殿" in rows[0]["shot"]


def test_scene_drift_core_scene_blocks():
    means = {"第1集": {"大殿": [1.0, 0.0]}, "第2集": {"大殿": [0.0, 1.0]}}
    rows = ca.scene_drift_rows(means, "第2集", core_scenes=["大殿"])
    assert len(rows) == 1 and rows[0]["verdict"] == "block"


def test_scene_drift_first_episode_no_prior_no_rows():
    means = {"第1集": {"大殿": [1.0, 0.0]}}
    assert ca.scene_drift_rows(means, "第1集") == []


# ── 跨集场景结构漂移（dHash 原型·补色调看不出的布局/朝向变化）──────────────────
def test_scene_struct_drift_stable_no_rows():
    protos = {"第1集": {"殿": [0] * 64}, "第2集": {"殿": [0] * 64}}
    assert ca.scene_struct_drift_rows(protos, "第2集") == []


def test_scene_struct_drift_non_core_warns():
    # 30/64 位翻转（>warn 18，<core block 26 但非 core）→ warn
    protos = {"第1集": {"殿": [0] * 64}, "第2集": {"殿": [1] * 30 + [0] * 34}}
    rows = ca.scene_struct_drift_rows(protos, "第2集")
    assert len(rows) == 1 and rows[0]["verdict"] == "warn" and "结构漂移" in rows[0]["msg"]


def test_scene_struct_drift_core_scene_blocks():
    protos = {"第1集": {"殿": [0] * 64}, "第2集": {"殿": [0] * 64}, "第3集": {"殿": [1] * 30 + [0] * 34}}
    rows = ca.scene_struct_drift_rows(protos, "第3集", core_scenes=["殿"])
    assert len(rows) == 1 and rows[0]["verdict"] == "block" and "跨3集结构" in rows[0]["shot"]


def test_scene_struct_drift_below_warn_no_rows():
    protos = {"第1集": {"殿": [0] * 64}, "第2集": {"殿": [1] * 5 + [0] * 59}}  # 仅 5 位 < warn 18
    assert ca.scene_struct_drift_rows(protos, "第2集") == []


def test_scene_drift_baseline_is_mean_of_priors():
    # 前两集基线均值=[0.5,0.5]，第3集=[0.5,0.5] → L1=0，无行（基线是历史均值非仅上一集）
    means = {"第1集": {"S": [1.0, 0.0]}, "第2集": {"S": [0.0, 1.0]}, "第3集": {"S": [0.5, 0.5]}}
    assert ca.scene_drift_rows(means, "第3集") == []
