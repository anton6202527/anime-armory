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
        "服装配色(N1)", "发型(H1)", "片内时序(N2)", "场景(O2)", "风格(S1)", "接缝接力",
        "称谓口头禅(A1)", "字幕对齐(L1)", "糊/低质(N4)", "手部/解剖(N5)", "身高比例(R1)",
        "轴线视线(X1)", "天气时辰(W1)", "字幕安全区(L2)", "音画同步(AV1)", "空间站位(B1)",
        "节奏密度(Rhythm)",
    }
    mapped = {
        label
        for spec in n2d_schema.CONSISTENCY_DIMENSIONS.values()
        for label in spec.get("audit_labels", ())
    }
    assert expected <= mapped


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
