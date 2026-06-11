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


def test_genre_ledger_record_aggregates_metrics_and_roi(tmp_path):
    root = tmp_path / "制漫剧" / "某仙侠剧"
    root.mkdir(parents=True)
    (root / "_meta.json").write_text(
        json.dumps({"title": "某仙侠剧", "genre": "仙侠"}, ensure_ascii=False), encoding="utf-8"
    )
    rows = [
        {"episode": "第1集", "platform": "红果", "retention_3s": "0.6", "follow_next_rate": "0.34",
         "plays": "800000", "revenue": "12000", "spend": "8000"},
        {"episode": "第2集", "platform": "红果", "retention_3s": "0.5", "follow_next_rate": "0.30",
         "plays": "200000", "revenue": "2000", "spend": "2000"},
    ]
    record = feedback.build_genre_record(
        str(root), rows,
        genre=feedback.detect_genre(str(root), None),
        subgenres=feedback.detect_subgenres(str(root), "复仇"),
        platform=feedback.detect_platform_tag(rows, None),
    )
    assert record["kind"] == "genre_performance_record"
    assert record["genre"] == "仙侠"
    assert record["subgenres"] == ["复仇"]
    assert record["platform"] == "红果"
    assert record["metrics"]["plays"] == 1000000
    # 留存按播放量加权：(0.6*800000+0.5*200000)/1000000 = 0.58
    assert abs(record["metrics"]["retention_3s"] - 0.58) < 1e-6
    # ROI = 总营收/总花费 = 14000/10000 = 1.4
    assert abs(record["metrics"]["roi"] - 1.4) < 1e-6

    ledger = tmp_path / "生产战绩" / "genre_ledger.jsonl"
    # upsert：同 (work, genre, platform) 重 emit 替换旧快照，不堆重复行（否则 novel-score 重复加权）
    assert feedback.upsert_genre_ledger(str(ledger), record) is False  # 首次：无旧行可替
    assert feedback.upsert_genre_ledger(str(ledger), record) is True   # 再次：替换了旧快照
    lines = [l for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1  # 仍只一行

    # 不同主键（另一部剧）= 不同行，正常保留
    other = dict(record, work=str(tmp_path / "制漫剧" / "另一部仙侠剧"))
    assert feedback.upsert_genre_ledger(str(ledger), other) is False
    lines = [l for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2

    # 非法/外来行原样保留，不被静默丢
    with open(ledger, "a", encoding="utf-8") as fh:
        fh.write("not-json-foreign-line\n")
    feedback.upsert_genre_ledger(str(ledger), record)  # 再 upsert 一次
    text = ledger.read_text(encoding="utf-8")
    assert "not-json-foreign-line" in text
    assert len([l for l in text.splitlines() if l.strip()]) == 3  # 两剧 + 外来行


def test_genre_record_without_roi_omits_key(tmp_path):
    # 没有 roi/roas/回收比 也没有 revenue+spend → record.metrics 无 roi 键（cmd 据此发缺-ROI warn）
    root = tmp_path / "制漫剧" / "无ROI剧"
    root.mkdir(parents=True)
    (root / "_meta.json").write_text(json.dumps({"title": "无ROI剧", "genre": "仙侠"}, ensure_ascii=False), encoding="utf-8")
    rows = [{"episode": "第1集", "platform": "红果", "retention_3s": "0.6", "plays": "100000"}]
    record = feedback.build_genre_record(str(root), rows, genre="仙侠", subgenres=[], platform="红果")
    assert "roi" not in record["metrics"]
    assert record["metrics"]["plays"] == 100000


def test_metric_alias_resolution_ingests_chinese_export_columns(tmp_path):
    # 实时投放 API 导出的中文列名也能被摄取（投放适配器契约）。
    row = {"episode": "第1集", "3秒留存率": "0.62", "追更率": "0.33", "播放量": "500000"}
    assert abs(feedback.metric(row, "retention_3s") - 0.62) < 1e-6
    assert abs(feedback.metric(row, "follow_next_rate") - 0.33) < 1e-6
    assert feedback.row_weight(row) == 500000.0


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
    # kind 不对的文件被忽略
    (prod / "consistency_findings_bad.json").write_text('{"kind": "other"}', encoding="utf-8")

    reports = feedback.load_consistency_reports(str(root))
    assert len(reports) == 2

    rows = [
        {"episode": "第1集", "retention_15s": "0.4", "bounce_3s": "0.5", "plays": "100"},
        {"episode": "第2集", "retention_15s": "0.6", "bounce_3s": "0.2", "plays": "100"},
    ]
    result = feedback.analyze_consistency(reports, rows)
    assert result["worst_episode"] == "第1集"
    assert result["dim_totals"]["脸(G1)"] == {"block": 1, "warn": 2}
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
