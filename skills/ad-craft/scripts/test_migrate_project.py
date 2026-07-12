import json
from pathlib import Path

import migrate_project as mp


def _project(tmp_path: Path):
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "_设置.md").write_text("# 设置\n\n- 生图AI: Codex\n- 广告目标: 转化行动\n- 发行地区: 中国大陆\n", encoding="utf-8")
    (root / "需求").mkdir()
    (root / "需求" / "brief.json").write_text(json.dumps({
        "schema_version": 1, "brand": "星盒", "product": "手账 App", "usp": ["整理灵感"],
        "audience": "创作者", "claims": ["整理灵感"],
        "rights": {"talent": "未使用真人", "music": "待补", "fonts": "待补", "assets": "待补"},
    }, ensure_ascii=False), encoding="utf-8")
    (root / "合成").mkdir()
    (root / "合成" / "delivery_plan.json").write_text(json.dumps({"deliverables": [
        {"deliverable_id": "master", "status": "planned", "expected_path": "合成/成片_主片.mp4"}
    ]}), encoding="utf-8")
    (root / "_进度.md").write_text("""# 星盒

## 阶段进度

| 阶段 | 状态 | 产物 | 备注 |
|---|---|---|---|
| 客户需求立项 | ✅ | 需求/brief.json | 旧流程完成 |
| 创意策划 | ✅ | 创意/concept.md | 旧流程完成 |

## 交付版本矩阵

| 交付件 | 时长 | 比例 | 类型 | 交付规格 | 状态 | 成片路径 |
|---|---|---|---|---|---|---|
| 主片 | 30s | 9:16 | master | 平台默认 | ⬜ | 合成/成片_主片.mp4 |
| 15s cutdown | 15s | 9:16 | cutdown | 平台默认 | ⬜ | 合成/cutdown/成片_15s.mp4 |
""", encoding="utf-8")
    return root


def test_migration_is_dry_run_by_default_and_write_is_backed_up(tmp_path):
    root = _project(tmp_path)
    before = (root / "_设置.md").read_text(encoding="utf-8")
    dry = mp.run(root, write=False)
    assert dry["mode"] == "dry_run"
    assert (root / "_设置.md").read_text(encoding="utf-8") == before
    assert not (root / "生产数据" / "migration_report.json").exists()

    report = mp.run(root, write=True)
    settings = (root / "_设置.md").read_text(encoding="utf-8")
    brief = json.loads((root / "需求" / "brief.json").read_text(encoding="utf-8"))
    progress = (root / "_进度.md").read_text(encoding="utf-8")
    assert "生图模型: GPT Image 2" in settings and "生图渠道: Codex CLI" in settings
    assert brief["schema_version"] == 2
    assert brief["measurement"] == {"primary_kpi": "待补", "conversion_event": "待补"}
    assert "| 客户需求立项 | ✅ |" not in progress
    assert "| 创意策划 | ✅ |" not in progress
    assert report["backup"]
    assert (root / report["backup"] / "original" / "_设置.md").is_file()
    assert (root / "合规" / "locale_matrix.json").is_file()
    locale = json.loads((root / "合规" / "locale_matrix.json").read_text(encoding="utf-8"))
    assert set(locale["deliverable_locales"]) >= {"master", "cut_15s"}
    assert (root / "生产数据" / "artifact_dependency_graph.json").is_file()
