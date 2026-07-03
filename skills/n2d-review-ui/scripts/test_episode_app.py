from __future__ import annotations

import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("episode_app", HERE / "episode_app.py")
episode_app = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(episode_app)


def write(path: Path, data: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def make_work(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    write(
        root / "_进度.md",
        "\n".join([
            "| 集 | 字数 | raw | 剧本改编 | 配音 | 分镜设计 | 出图 | 成片 | 验收 |",
            "|---|---|---|---|---|---|---|---|---|",
            "| 第1集 | 800 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⬜ |",
            "| 第2集 | 700 | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |",
        ]),
    )
    storyboard = {
        "title": "测试剧_第1集",
        "total_duration": 7,
        "clips": [{
            "id": "EP01_CLIP01",
            "label": "开场",
            "duration": 7,
            "scene": "雨夜门口",
            "firstframe_png": "出图/第1集/图片/Clip01.png",
            "video_out": "出视频/第1集/视频/Clip_01.mp4",
        }],
    }
    write(root / "脚本" / "第1集" / "storyboard.json", json.dumps(storyboard, ensure_ascii=False))
    write(root / "出图" / "第1集" / "图片" / "Clip01.png")
    write(root / "出视频" / "第1集" / "视频" / "Clip_01.mp4")
    score = {
        "kind": "n2d_score",
        "episode": "第1集",
        "total_score": 64,
        "threshold": 85,
        "status": "fail",
        "dimensions": [{
            "label": "场景一致性",
            "status": "fail",
            "score": 42,
            "evidence": ["Clip_01 场景光位漂移"],
        }],
        "auto_return_tasks": [{"return_to_stage": "image", "scope": "重出 Clip_01"}],
    }
    write(root / "生产数据" / "score_第1集.json", json.dumps(score, ensure_ascii=False))
    gate = {
        "kind": "n2d_consistency_findings",
        "episode": "第1集",
        "gate_stage": "review",
        "summary": {"total": 1},
        "findings": [{
            "sev": "warn",
            "dim": "人物在场链",
            "loc": "storyboard clip#1",
            "msg": "入场解释不足",
            "return_to_stage": "script_stage2",
            "affected_shots": ["EP01_CLIP01"],
            "affected_artifacts": ["脚本/第1集/storyboard.json"],
        }],
        "auto_return_tasks": [{"return_to_stage": "script_stage2", "scope": "补 entry_exit"}],
    }
    write(root / "生产数据" / "gate_findings_review_第1集.json", json.dumps(gate, ensure_ascii=False))
    dashboard = {
        "kind": "n2d_production_dashboard",
        "episodes": [{
            "episode": "第1集",
            "cost_totals": {"credits": 12},
            "duration_hms": "3m10s",
            "runtime_hms": "7s",
            "event_count": 5,
            "generation_attempts": 2,
            "generation_pass_rate": 0.5,
            "final_pass_rate": 0.0,
            "one_pass_rate": 0.5,
            "redraw_count": 1,
            "redraw_rate": 0.5,
            "qa_blockers": 1,
            "qa_warnings": 2,
            "stages": {"image": {"generation_attempts": 2, "generation_passes": 1, "qa_blockers": 1, "qa_warnings": 1, "redraw_count": 1, "duration_sec": 190}},
        }],
    }
    write(root / "生产数据" / "dashboard.json", json.dumps(dashboard, ensure_ascii=False))


def test_episode_workspace_aggregates_per_episode_data(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    make_work(root)

    manifest = episode_app.build_episode_workspace(root, "第1集")

    assert manifest["kind"] == "n2d_episode_workspace"
    assert manifest["episode"] == "第1集"
    assert manifest["metrics"]["cost_text"] == "12 credits"
    assert manifest["metrics"]["score"] == 64
    assert manifest["clip_summary"]["total"] == 1
    assert manifest["issues"]["severity"]["block"] >= 1  # score fail becomes review_ui finding
    assert any(g["return_to_stage"] == "script_stage2" for g in manifest["issues"]["groups"])
    assert any(t["source"] == "score" for t in manifest["return_tasks"])
    assert any(e["label"] == "机器评分" and e["exists"] for e in manifest["evidence"])


def test_episode_index_and_outputs(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    make_work(root)

    paths = episode_app.write_episode(root, "第1集")
    index_path = episode_app.write_index(root)
    index = json.loads(Path(index_path).read_text(encoding="utf-8"))

    assert Path(paths["json"]).is_file()
    assert Path(paths["html"]).is_file()
    assert index["kind"] == "n2d_episode_index"
    assert len(index["episodes"]) == 2
    assert index["episodes"][0]["episode_app"]["exists"] is True
    assert "工作台" in Path(paths["html"]).read_text(encoding="utf-8")


def test_write_all_generates_every_episode_workspace(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    make_work(root)

    result = episode_app.write_all(root)

    assert Path(result["index"]).is_file()
    assert len(result["episodes"]) == 2
    assert (root / "生产数据" / "episode_app_第1集.html").is_file()
    assert (root / "生产数据" / "episode_app_第2集.html").is_file()
