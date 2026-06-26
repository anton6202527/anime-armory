from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("feedback.py")
spec = importlib.util.spec_from_file_location("n2d_feedback", SCRIPT)
feedback = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(feedback)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_storyboard(root: Path, episode: str, *, first: str, tail: str, duration: float = 30.0) -> None:
    clips = []
    for idx in range(1, 7):
        if idx == 1:
            text = first
            rhythm = "爽点·CU硬切"
            transition = "hard_cut"
        elif idx == 6:
            text = tail
            rhythm = "加速·碎切"
            transition = "action_cut"
        elif idx == 3:
            text = "系统面板突然弹出任务奖励未公开，形成信息增量。"
            rhythm = "加速·碎切"
            transition = "match_cut"
        else:
            text = f"中段铺垫镜头{idx}"
            rhythm = "铺垫·长镜"
            transition = "match_cut"
        clips.append({
            "id": f"EP{episode}_CLIP{idx:02d}",
            "label": f"Clip {idx}",
            "duration": duration / 6,
            "scene": "冷宫寝殿",
            "rhythm": rhythm,
            "continuity": {
                "start_state": text,
                "end_state": text,
                "transition": transition,
                "need_endframe": idx < 6,
            },
        })
    path = root / "脚本" / f"第{episode}集" / "storyboard.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"episode": int(episode), "total_duration": duration, "clips": clips}, ensure_ascii=False, indent=2), encoding="utf-8")


def _audit_codes(result: dict) -> set[str]:
    return {f.get("code") for f in (result.get("input_audit") or {}).get("findings") or []}


def test_first_episode_completion_below_floor_flagged(tmp_path: Path) -> None:
    # GAP-3：第1集完播低于 benchmark first_episode_completion_floor(0.75) → 单独报 warn。
    metrics = tmp_path / "生产数据" / "platform_metrics.csv"
    write_csv(metrics, [
        {"episode": "第1集", "plays": 1000, "retention_3s": 0.80, "completion_rate": 0.34, "follow_next_rate": 0.18},
        {"episode": "第2集", "plays": 1000, "retention_3s": 0.78, "completion_rate": 0.33, "follow_next_rate": 0.17},
    ])
    write_storyboard(tmp_path, "1", first="柳娘子端着赐死托盘压近，沈念惊醒。", tail="黑衣人举刀冲入门口。")
    write_storyboard(tmp_path, "2", first="太监拖走小禾，沈念眼神骤冷。", tail="追杀者拔剑逼近。")
    result = feedback.analyze_feedback(str(tmp_path), str(metrics), None, min_samples=2, min_lift=0.05)
    findings = (result.get("input_audit") or {}).get("findings") or []
    ep1 = [f for f in findings if f.get("code") == "first_episode_completion_below_floor"]
    assert ep1 and ep1[0]["episode"] == "第1集"
    # 第2集低完播不该触发首集地板（只判 ep1）。
    assert all(f.get("episode") != "第2集" for f in ep1)


def test_first_episode_completion_above_floor_not_flagged(tmp_path: Path) -> None:
    # GAP-3：第1集完播达标 → 不报。
    metrics = tmp_path / "生产数据" / "platform_metrics.csv"
    write_csv(metrics, [
        {"episode": "第1集", "plays": 1000, "retention_3s": 0.86, "completion_rate": 0.80, "follow_next_rate": 0.30},
        {"episode": "第2集", "plays": 1000, "retention_3s": 0.78, "completion_rate": 0.33, "follow_next_rate": 0.17},
    ])
    write_storyboard(tmp_path, "1", first="柳娘子端着赐死托盘压近，沈念惊醒。", tail="黑衣人举刀冲入门口。")
    write_storyboard(tmp_path, "2", first="太监拖走小禾，沈念眼神骤冷。", tail="追杀者拔剑逼近。")
    result = feedback.analyze_feedback(str(tmp_path), str(metrics), None, min_samples=2, min_lift=0.05)
    assert "first_episode_completion_below_floor" not in _audit_codes(result)


def test_feedback_finds_opening_and_cliffhanger_winners(tmp_path: Path) -> None:
    metrics = tmp_path / "生产数据" / "platform_metrics.csv"
    features = tmp_path / "生产数据" / "creative_features.csv"
    write_csv(
        metrics,
        [
            {"episode": "第1集", "plays": 1000, "retention_3s": 0.80, "retention_15s": 0.55, "completion_rate": 0.34, "follow_next_rate": 0.18, "bounce_3s": 0.10},
            {"episode": "第2集", "plays": 1000, "retention_3s": 0.78, "retention_15s": 0.53, "completion_rate": 0.33, "follow_next_rate": 0.17, "bounce_3s": 0.12},
            {"episode": "第3集", "plays": 1000, "retention_3s": 0.48, "retention_15s": 0.27, "completion_rate": 0.15, "follow_next_rate": 0.07, "bounce_3s": 0.35},
            {"episode": "第4集", "plays": 1000, "retention_3s": 0.50, "retention_15s": 0.29, "completion_rate": 0.17, "follow_next_rate": 0.08, "bounce_3s": 0.34},
        ],
    )
    write_csv(
        features,
        [
            {"episode": "第1集", "opening_type": "cold_conflict", "cliffhanger_type": "crisis_suspend", "shot_density_per_min": 24, "hook_interval_sec": 15},
            {"episode": "第2集", "opening_type": "cold_conflict", "cliffhanger_type": "crisis_suspend", "shot_density_per_min": 26, "hook_interval_sec": 16},
            {"episode": "第3集", "opening_type": "slow_lore", "cliffhanger_type": "resolved_clean", "shot_density_per_min": 42, "hook_interval_sec": 28},
            {"episode": "第4集", "opening_type": "slow_lore", "cliffhanger_type": "resolved_clean", "shot_density_per_min": 44, "hook_interval_sec": 30},
        ],
    )

    result = feedback.analyze_feedback(str(tmp_path), str(metrics), str(features), min_samples=2, min_lift=0.05)

    assert result["analyses"]["opening_retention"]["best"]["name"] == "cold_conflict"
    assert result["analyses"]["cliffhanger_follow"]["best"]["name"] == "crisis_suspend"
    assert result["analyses"]["shot_density_bounce"]["worst"]["name"] == ">=40/m 过密"
    assert any("cold_conflict" in item for item in result["recommendations"])


def test_feedback_auto_extracts_creative_features_from_storyboard(tmp_path: Path) -> None:
    metrics = tmp_path / "生产数据" / "platform_metrics.csv"
    write_csv(
        metrics,
        [
            {"episode": "第1集", "plays": 1000, "retention_3s": 0.80, "retention_15s": 0.55, "completion_rate": 0.34, "follow_next_rate": 0.18},
            {"episode": "第2集", "plays": 1000, "retention_3s": 0.78, "retention_15s": 0.53, "completion_rate": 0.33, "follow_next_rate": 0.17},
        ],
    )
    write_storyboard(tmp_path, "1", first="柳娘子端着赐死托盘压近，沈念在阴影里惊醒。", tail="黑衣人举刀冲入门口，沈念被围住。")
    write_storyboard(tmp_path, "2", first="太监抓住小禾衣领拖走，沈念眼神骤冷。", tail="追杀者拔剑逼近，门外血光压入。")

    result = feedback.analyze_feedback(str(tmp_path), str(metrics), None, min_samples=2, min_lift=0.05)

    assert result["source"]["features"] == "storyboard:auto"
    assert result["feature_extraction"]["mode"] == "storyboard_auto"
    assert result["analyses"]["opening_retention"]["best"]["name"] == "cold_conflict"
    assert result["analyses"]["cliffhanger_follow"]["best"]["name"] == "crisis_suspend"
    assert result["analyses"]["hook_interval_retention"]["groups"][0]["name"] != "unknown"


def test_feedback_compares_same_episode_ab_variants(tmp_path: Path) -> None:
    metrics = tmp_path / "生产数据" / "platform_metrics.csv"
    features = tmp_path / "生产数据" / "creative_features.csv"
    write_csv(
        metrics,
        [
            {"episode": "第1集", "platform": "douyin", "ab_test_id": "EP01_launch", "variant_id": "A", "plays": 1000, "ctr": 0.061, "retention_3s": 0.82, "retention_15s": 0.57, "completion_rate": 0.35, "follow_next_rate": 0.21},
            {"episode": "第1集", "platform": "douyin", "ab_test_id": "EP01_launch", "variant_id": "B", "plays": 1000, "ctr": 0.050, "retention_3s": 0.62, "retention_15s": 0.40, "completion_rate": 0.24, "follow_next_rate": 0.10},
            {"episode": "第2集", "platform": "douyin", "ab_test_id": "EP02_launch", "variant_id": "A", "plays": 1000, "ctr": 0.059, "retention_3s": 0.80, "retention_15s": 0.55, "completion_rate": 0.34, "follow_next_rate": 0.20},
            {"episode": "第2集", "platform": "douyin", "ab_test_id": "EP02_launch", "variant_id": "B", "plays": 1000, "ctr": 0.052, "retention_3s": 0.64, "retention_15s": 0.42, "completion_rate": 0.25, "follow_next_rate": 0.11},
        ],
    )
    write_csv(
        features,
        [
            {"episode": "第1集", "ab_test_id": "EP01_launch", "variant_id": "A", "opening_type": "cold_conflict", "opening_variant": "cold_open_first", "cover_variant": "face_closeup", "cliffhanger_type": "crisis_suspend", "cliffhanger_cut_variant": "hard_cut_before_reveal", "title_variant": "她刚重生就被赐死", "shot_density_per_min": 24, "hook_interval_sec": 15},
            {"episode": "第1集", "ab_test_id": "EP01_launch", "variant_id": "B", "opening_type": "system_hook", "opening_variant": "system_panel_first", "cover_variant": "crisis_tableau", "cliffhanger_type": "truth_half_reveal", "cliffhanger_cut_variant": "truth_half_reveal", "title_variant": "系统第十七弹赐死局", "shot_density_per_min": 24, "hook_interval_sec": 15},
            {"episode": "第2集", "ab_test_id": "EP02_launch", "variant_id": "A", "opening_type": "cold_conflict", "opening_variant": "cold_open_first", "cover_variant": "face_closeup", "cliffhanger_type": "crisis_suspend", "cliffhanger_cut_variant": "hard_cut_before_reveal", "title_variant": "她刚重生就被赐死", "shot_density_per_min": 24, "hook_interval_sec": 15},
            {"episode": "第2集", "ab_test_id": "EP02_launch", "variant_id": "B", "opening_type": "system_hook", "opening_variant": "system_panel_first", "cover_variant": "crisis_tableau", "cliffhanger_type": "truth_half_reveal", "cliffhanger_cut_variant": "truth_half_reveal", "title_variant": "系统第十七弹赐死局", "shot_density_per_min": 24, "hook_interval_sec": 15},
        ],
    )

    result = feedback.analyze_feedback(str(tmp_path), str(metrics), str(features), min_samples=2, min_lift=0.05)

    assert result["analyses"]["ab_opening_retention"]["best"]["name"] == "cold_open_first"
    assert result["analyses"]["ab_cover_retention"]["best"]["name"] == "face_closeup"
    assert result["analyses"]["ab_cliffhanger_follow"]["best"]["name"] == "hard_cut_before_reveal"
    assert result["analyses"]["ab_title_retention"]["best"]["name"] == "她刚重生就被赐死"
    assert result["analyses"]["ab_opening_retention"]["best"]["paired_lift"] > 0
    assert any("A/B 开场" in item for item in result["recommendations"])


def test_write_auto_creative_features(tmp_path: Path) -> None:
    write_storyboard(tmp_path, "1", first="淡青系统面板骤然亮起，任务第十七弹出。", tail="奖励未公开被放大，真相只露出一半。")
    rows = feedback.extract_storyboard_features(str(tmp_path))
    out = tmp_path / "生产数据" / "creative_features.auto.json"

    feedback.write_creative_features(str(out), rows)
    data = json.loads(out.read_text(encoding="utf-8"))

    assert data[0]["opening_type"] == "system_hook"
    assert data[0]["cliffhanger_type"] == "truth_half_reveal"
    assert data[0]["creative_features_source"] == "storyboard_auto"


def test_update_guide_replaces_marker_block(tmp_path: Path) -> None:
    guide = tmp_path / "导演节奏.md"
    guide.write_text(
        "\n".join(
            [
                "# 导演节奏",
                feedback.START_MARKER,
                "旧快照",
                feedback.END_MARKER,
                "尾部",
            ]
        ),
        encoding="utf-8",
    )
    result = {
        "generated_at": "2026-06-08T00:00:00+00:00",
        "sample_count": 4,
        "min_samples": 2,
        "recommendations": ["开场优先复用 `cold_conflict`。"],
        "analyses": {
            "opening_retention": {"best": {"name": "cold_conflict", "retention_3s": 0.79, "lift": 0.15, "n": 2}},
            "cliffhanger_follow": {"best": None},
            "shot_density_bounce": {"worst": {"name": ">=40/m 过密", "bounce_3s": 0.35, "lift": 0.12, "n": 2}},
            "hook_interval_retention": {"worst": None},
        },
    }

    feedback.update_director_guide(str(guide), result)
    text = guide.read_text(encoding="utf-8")

    assert "旧快照" not in text
    assert "cold_conflict" in text
    assert "尾部" in text


def test_metric_alias_resolution_ingests_chinese_export_columns(tmp_path):
    # 实时投放 API 导出的中文列名也能被摄取（投放适配器契约）。
    row = {
        "episode": "第1集",
        "3秒留存率": "0.62",
        "6秒留存率": "0.54",
        "播放到50%": "0.31",
        "人均观看集数": "1.8",
        "付费解锁率": "0.08",
        "付费点秒": "38",
        "D7留存": "0.11",
        "追更率": "0.33",
        "播放量": "500000",
    }
    assert abs(feedback.metric(row, "retention_3s") - 0.62) < 1e-6
    assert abs(feedback.metric(row, "retention_6s") - 0.54) < 1e-6
    assert abs(feedback.metric(row, "retention_50_pct") - 0.31) < 1e-6
    assert abs(feedback.metric(row, "avg_episodes_per_user") - 1.8) < 1e-6
    assert abs(feedback.metric(row, "unlock_or_subscribe_rate") - 0.08) < 1e-6
    assert abs(feedback.metric(row, "paywall_position_sec") - 38.0) < 1e-6
    assert abs(feedback.metric(row, "d7_retention") - 0.11) < 1e-6
    assert abs(feedback.metric(row, "follow_next_rate") - 0.33) < 1e-6
    assert feedback.row_weight(row) == 500000.0


def test_feedback_analyzes_paywall_and_continue_path(tmp_path: Path) -> None:
    metrics = tmp_path / "生产数据" / "platform_metrics.csv"
    features = tmp_path / "生产数据" / "creative_features.csv"
    write_csv(
        metrics,
        [
            {"episode": "第1集", "plays": 1000, "retention_3s": 0.80, "retention_15s": 0.55, "completion_rate": 0.34, "follow_next_rate": 0.22, "unlock_or_subscribe_rate": 0.18, "paywall_position_sec": 38, "continue_path": "next_button_sticky"},
            {"episode": "第2集", "plays": 1000, "retention_3s": 0.78, "retention_15s": 0.53, "completion_rate": 0.33, "follow_next_rate": 0.20, "unlock_or_subscribe_rate": 0.16, "paywall_position_sec": 41, "continue_path": "next_button_sticky"},
            {"episode": "第3集", "plays": 1000, "retention_3s": 0.63, "retention_15s": 0.40, "completion_rate": 0.24, "follow_next_rate": 0.09, "unlock_or_subscribe_rate": 0.05, "paywall_position_sec": 8, "continue_path": "end_card_only"},
            {"episode": "第4集", "plays": 1000, "retention_3s": 0.64, "retention_15s": 0.42, "completion_rate": 0.25, "follow_next_rate": 0.10, "unlock_or_subscribe_rate": 0.06, "paywall_position_sec": 10, "continue_path": "end_card_only"},
        ],
    )
    write_csv(
        features,
        [
            {"episode": "第1集", "opening_type": "cold_conflict", "cliffhanger_type": "crisis_suspend", "shot_density_per_min": 24, "hook_interval_sec": 15},
            {"episode": "第2集", "opening_type": "cold_conflict", "cliffhanger_type": "crisis_suspend", "shot_density_per_min": 26, "hook_interval_sec": 16},
            {"episode": "第3集", "opening_type": "system_hook", "cliffhanger_type": "truth_half_reveal", "shot_density_per_min": 24, "hook_interval_sec": 15},
            {"episode": "第4集", "opening_type": "system_hook", "cliffhanger_type": "truth_half_reveal", "shot_density_per_min": 24, "hook_interval_sec": 15},
        ],
    )

    result = feedback.analyze_feedback(str(tmp_path), str(metrics), str(features), min_samples=2, min_lift=0.05)

    assert result["analyses"]["paywall_unlock"]["best"]["name"] == "16-45s 前中段卡点"
    assert result["analyses"]["continue_path_follow"]["best"]["name"] == "next_button_sticky"
    assert any("付费/解锁卡点" in item for item in result["recommendations"])
    assert any("追更路径" in item for item in result["recommendations"])


def test_paywall_promise_alignment_validates_ledger_ids(tmp_path: Path) -> None:
    metrics = tmp_path / "生产数据" / "platform_metrics.csv"
    write_csv(
        metrics,
        [
            {"episode": "第1集", "plays": 1000, "retention_3s": 0.80, "retention_6s": 0.70, "retention_15s": 0.55, "completion_rate": 0.34, "follow_next_rate": 0.22, "unlock_or_subscribe_rate": 0.18, "paywall_position_sec": 38, "paywall_after_promise_id": "OPEN_01", "continue_path": "next_button_sticky"},
            {"episode": "第2集", "plays": 1000, "retention_3s": 0.60, "retention_6s": 0.50, "retention_15s": 0.36, "completion_rate": 0.20, "follow_next_rate": 0.08, "unlock_or_subscribe_rate": 0.04, "paywall_position_sec": 12, "paywall_after_promise_id": "MISSING_01", "continue_path": "end_card_only"},
        ],
    )
    for ep, hook in (("1", "OPEN_01"), ("2", "OPEN_02")):
        write_storyboard(tmp_path, ep, first="门外刀影压进画面，沈念惊醒。", tail="黑衣人举刀冲入门口。")
        path = tmp_path / "脚本" / f"第{ep}集" / "storyboard.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["retention_promise_ledger"] = [
            {
                "hook_id": hook,
                "promise_type": "opening_hook",
                "opened_at": "Clip_01",
                "promise": "门外是谁",
                "payoff_due": "Clip_03",
                "payoff_status": "paid",
                "payoff_clip": "Clip_03",
                "payoff_evidence": "Clip_03 揭示刺客身份",
            }
        ]
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    result = feedback.analyze_feedback(str(tmp_path), str(metrics), None, min_samples=1, min_lift=0.01)
    alignment = result["analyses"]["paywall_promise_alignment"]

    assert any(group["name"] == "aligned" and group["n"] == 1 for group in alignment["groups"])
    assert any(item["code"] == "paywall_unknown_promise_id" for item in alignment["findings"])
    assert any(item["code"] == "paywall_unknown_promise_id" for item in result["input_audit"]["findings"])


def test_input_audit_reports_missing_required_and_paid_fields(tmp_path: Path) -> None:
    metrics = tmp_path / "生产数据" / "platform_metrics.csv"
    write_csv(
        metrics,
        [
            {"episode": "第1集", "plays": 1000, "retention_3s": 0.80, "unlock_or_subscribe_rate": 0.12, "paywall_position_sec": 30},
        ],
    )
    write_storyboard(tmp_path, "1", first="门外刀影压进画面，沈念惊醒。", tail="黑衣人举刀冲入门口。")

    result = feedback.analyze_feedback(str(tmp_path), str(metrics), None, min_samples=1, min_lift=0.01)
    findings = result["input_audit"]["findings"]

    assert any(item["code"] == "missing_required_metric" and item.get("metric") == "retention_6s" for item in findings)
    assert any(item["code"] == "missing_paid_retention_field" and item.get("field") == "paywall_after_promise_id" for item in findings)


def test_consistency_findings_ingestion(tmp_path):
    """一致性回灌：读 consistency_findings_*.json 出维度计数/最严重集，并排留存指标；无文件优雅跳过。"""
    root = tmp_path
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    # 两集 findings：第1集 1 block + 2 warn（脸），第2集 1 warn（场景）
    (prod / "consistency_findings_第1集.json").write_text(json.dumps({
        "kind": "n2d_consistency_findings", "version": 1, "episode": "第1集",
        "summary": {"by_dim": {"脸(G1)": {"block": 1, "warn": 2}, "场景(O2)": {"block": 0, "warn": 0}}},
        "findings": [],
    }, ensure_ascii=False), encoding="utf-8")
    (prod / "consistency_findings_第2集.json").write_text(json.dumps({
        "kind": "n2d_consistency_findings", "version": 1, "episode": "第2集",
        "summary": {"by_dim": {"场景(O2)": {"block": 0, "warn": 1}}},
        "findings": [],
    }, ensure_ascii=False), encoding="utf-8")
    # review-ui 导出的 findings 也应被读取；即便没有 summary.by_dim，也从 findings[] 反算。
    (prod / "review_ui_findings_第3集.json").write_text(json.dumps({
        "kind": "n2d_consistency_findings", "version": 1, "episode": "第3集",
        "summary": {"severity": {"block": 0, "warn": 1}},
        "findings": [{"dim": "角色一致性", "sev": "warn", "msg": "服装漂移"}],
    }, ensure_ascii=False), encoding="utf-8")
    # kind 不对的文件被忽略
    (prod / "consistency_findings_bad.json").write_text('{"kind": "other"}', encoding="utf-8")

    reports = feedback.load_consistency_reports(str(root))
    assert len(reports) == 3

    rows = [
        {"episode": "第1集", "retention_15s": "0.4", "bounce_3s": "0.5", "plays": "100"},
        {"episode": "第2集", "retention_15s": "0.6", "bounce_3s": "0.2", "plays": "100"},
        {"episode": "第3集", "retention_15s": "0.7", "bounce_3s": "0.1", "plays": "100"},
    ]
    result = feedback.analyze_consistency(reports, rows)
    assert result["worst_episode"] == "第1集"
    assert result["dim_totals"]["脸(G1)"] == {"block": 1, "warn": 2}
    assert result["dim_totals"]["角色一致性"] == {"block": 0, "warn": 1}
    ep1 = next(e for e in result["episodes"] if e["episode"] == "第1集")
    assert ep1["top_dim"] == "脸(G1)" and ep1["retention_15s"] == 0.4

    # 渲染含「一致性问题 Top」节
    fb = {
        "sample_count": 0, "min_samples": 2, "generated_at": "t", "recommendations": [],
        "feature_extraction": {}, "source": {"features": "x"},
        "analyses": {k: {"name": k, "groups": []} for k in (
            "opening_retention", "cliffhanger_follow", "shot_density_bounce", "hook_interval_retention",
            "ab_opening_retention", "ab_cover_retention", "ab_cliffhanger_follow", "ab_title_retention")},
        "consistency": result,
    }
    md = feedback.render_markdown(fb)
    assert "一致性问题 Top" in md and "第1集" in md

    # 无 findings 文件 → None，渲染不出该节
    empty_root = tmp_path / "empty"
    (empty_root / "生产数据").mkdir(parents=True)
    assert feedback.analyze_consistency(feedback.load_consistency_reports(str(empty_root)), []) is None


# ── G6: 投放→生成输入闭环 creative_priors 写端 ────────────────────────────────
def _ab_analyses_with_winner():
    """构造一份含显著胜出的 A/B analyses（仿 analyze_paired_ab 输出形状）。"""
    return {
        "ab_opening_retention": {
            "best": {"name": "cold_open_first", "paired_lift": 0.18, "n": 2, "plays": 2000,
                     "retention_3s": 0.82, "episodes": ["第1集", "第2集"]},
        },
        "ab_cliffhanger_follow": {
            "best": {"name": "hard_cut_before_reveal", "paired_lift": 0.09, "n": 2, "plays": 2000,
                     "follow_next_rate": 0.21, "episodes": ["第1集", "第2集"]},
        },
        "ab_cover_retention": {"best": None},          # 无胜出 → 缺省
        "ab_title_retention": {                        # lift 不足 → 缺省
            "best": {"name": "弱标题", "paired_lift": 0.01, "n": 3, "retention_3s": 0.5},
        },
    }


def test_build_creative_priors_picks_significant_winners():
    analyses = _ab_analyses_with_winner()
    priors = feedback.build_creative_priors(analyses, min_lift=0.05, min_samples=2)

    assert priors["kind"] == "n2d_creative_priors"
    assert priors["generated_at"]  # 采集时间占位非空
    p = priors["priors"]
    # 开场 + 集尾断点达标 → 写；封面无胜出、标题 lift 不足 → 不写。
    assert p["opening_variant"]["winner"] == "cold_open_first"
    assert p["opening_variant"]["paired_lift"] == 0.18
    assert p["opening_variant"]["n"] == 2
    assert p["cliffhanger_cut_variant"]["winner"] == "hard_cut_before_reveal"
    assert "cover_variant" not in p
    assert "title_variant" not in p


def test_build_creative_priors_includes_paywall_and_continue_path():
    analyses = {
        "paywall_unlock": {
            "best": {"name": "16-45s 前中段卡点", "lift": 0.08, "n": 3, "plays": 3000,
                     "unlock_or_subscribe_rate": 0.18, "episodes": ["第1集", "第2集", "第3集"]},
        },
        "continue_path_follow": {
            "best": {"name": "next_button_sticky", "lift": 0.06, "n": 3, "plays": 3000,
                     "follow_next_rate": 0.22, "episodes": ["第1集", "第2集", "第3集"]},
        },
    }

    priors = feedback.build_creative_priors(analyses, min_lift=0.05, min_samples=2)
    p = priors["priors"]

    assert p["paywall_position_bucket"]["winner"] == "16-45s 前中段卡点"
    assert p["paywall_position_bucket"]["lift"] == 0.08
    assert p["continue_path"]["winner"] == "next_button_sticky"
    assert p["continue_path"]["primary_metric"] == "follow_next_rate"


def test_build_creative_priors_skips_when_samples_insufficient():
    analyses = _ab_analyses_with_winner()
    # 抬高样本阈值：开场 n=2 < 3 → 跳过；断点 n=2 < 3 → 跳过。
    priors = feedback.build_creative_priors(analyses, min_lift=0.05, min_samples=3)
    assert priors["priors"] == {}


def test_build_creative_priors_no_op_when_no_ab_data():
    # 完全没有 A/B best（best=None 或键缺）→ 空先验（下游 no-op，不臆造）。
    analyses = {k: {"best": None} for k in (
        "ab_opening_retention", "ab_cliffhanger_follow", "ab_cover_retention", "ab_title_retention")}
    priors = feedback.build_creative_priors(analyses, min_lift=0.05, min_samples=2)
    assert priors["priors"] == {}
    assert priors["kind"] == "n2d_creative_priors"


def test_write_priors_round_trips_to_production_dir(tmp_path):
    priors = feedback.build_creative_priors(_ab_analyses_with_winner(), min_lift=0.05, min_samples=2)
    path = feedback.write_creative_priors(str(tmp_path), priors)
    assert path.endswith("生产数据/creative_priors.json")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    assert data["priors"]["opening_variant"]["winner"] == "cold_open_first"


# ── T11: feedback 一致性写回信号 ─────────────────────────────────────────────
def test_consistency_priority_signal_on_block_and_low_retention():
    import feedback as fb
    reports = [{"kind": fb.CONSISTENCY_FINDINGS_KIND, "episode": "第1集",
                "findings": [{"sev": "block", "dim": "角色一致性", "msg": "崩脸"}]}]
    rows = [{"episode": "第1集", "retention_15s": 0.30}]   # 留存低
    res = fb.analyze_consistency(reports, rows)
    sigs = res["priority_signals"]
    assert sigs and sigs[0]["episode"] == "第1集" and sigs[0]["signal"] == "prioritize_rework"
    assert sigs[0]["top_dim"] == "角色一致性"


def test_consistency_no_signal_when_retention_ok():
    import feedback as fb
    reports = [{"kind": fb.CONSISTENCY_FINDINGS_KIND, "episode": "第1集",
                "findings": [{"sev": "block", "dim": "角色一致性", "msg": "崩脸"}]}]
    rows = [{"episode": "第1集", "retention_15s": 0.80}]   # 留存好 → 不触发
    res = fb.analyze_consistency(reports, rows)
    assert res["priority_signals"] == []
