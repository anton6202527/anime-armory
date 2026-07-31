"""scene_batch 单测——场景键 / 连续分组 / 是否成组 / 作业构造 / plan_episode 集成。

cd skills/n2d/n2d-image/scripts && python3 -m pytest test_scene_batch.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("scene_batch.py")
spec = importlib.util.spec_from_file_location("scene_batch", SCRIPT)
sb = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(sb)


def test_clip_scene_key():
    assert sb.clip_scene_key({"loc": "LOC_01"}) == "LOC_01"
    assert sb.clip_scene_key({"scene": "冷宫寝殿 LOC_02 夜"}) == "LOC_02"  # 文本里的 LOC_xx 优先
    assert sb.clip_scene_key({"scene": "御 花园"}) == "御花园"  # 归一化空白
    assert sb.clip_scene_key({}) == ""


def test_group_consecutive_breaks_on_scene_change():
    clips = [
        {"id": "Clip 1", "scene": "LOC_01"},
        {"id": "Clip 2", "scene": "LOC_01"},
        {"id": "Clip 3", "scene": "LOC_02"},  # 切场景 → 断组
        {"id": "Clip 4", "scene": "LOC_01"},  # 回 LOC_01 但不连续 → 新组
    ]
    groups = sb.group_consecutive_by_scene(clips)
    assert [g["scene_key"] for g in groups] == ["LOC_01", "LOC_02", "LOC_01"]
    assert [len(g["members"]) for g in groups] == [2, 1, 1]


def test_should_batch():
    assert sb.should_batch({"scene_key": "LOC_01", "members": [1, 2]}) is True
    assert sb.should_batch({"scene_key": "LOC_01", "members": [1]}) is False  # 单镜不成组
    assert sb.should_batch({"scene_key": "", "members": [1, 2]}) is False     # 空键不可门控
    assert sb.should_batch({"scene_key": "LOC_01", "members": [1, 2]}, min_group=3) is False


def test_build_batch_job():
    group = {"scene_key": "LOC_01", "members": [
        {"clip_id": "Clip_01", "index": 1, "firstframe_png": "出图/第1集/图片/Clip_01.png"},
        {"clip_id": "Clip_02", "index": 2, "firstframe_png": "出图/第1集/图片/Clip_02.png"}]}
    job = sb.build_batch_job(group, scene_name="冷宫寝殿")
    assert job["mode"] == "scene_coherent_batch" and job["size"] == 2
    assert job["clip_ids"] == ["Clip_01", "Clip_02"] and job["scene_name"] == "冷宫寝殿"
    assert "shared_seed" in job["shared_locks"]


def test_plan_episode_default_path(tmp_path):
    root = tmp_path / "作品"
    sbdir = root / "脚本" / "第1集"
    sbdir.mkdir(parents=True)
    (sbdir / "storyboard.json").write_text(json.dumps({"clips": [
        {"id": "Clip 1", "scene": "LOC_01", "firstframe_png": "出图/第1集/图片/Clip_01.png"},
        {"id": "Clip 2", "scene": "LOC_01", "firstframe_png": "出图/第1集/图片/Clip_02.png"},
        {"id": "Clip 3", "scene": "LOC_02"},
    ]}, ensure_ascii=False), encoding="utf-8")
    shared = root / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "asset_registry.json").write_text(json.dumps({"assets": [
        {"id": "LOC_01", "name": "冷宫寝殿"}, {"id": "LOC_02", "name": "御花园"}]}, ensure_ascii=False),
        encoding="utf-8")
    plan = sb.plan_episode(str(root), "第1集")
    assert len(plan["batches"]) == 1  # LOC_01 连续 2 镜 → 默认成 batch
    assert plan["batches"][0]["scene_name"] == "冷宫寝殿"
    assert plan["batched_clips"] == 2
    assert len(plan["solo"]) == 1 and plan["solo"][0]["clip_id"] == "Clip_03"  # LOC_02 单镜独立


def test_plan_episode_missing_storyboard(tmp_path):
    plan = sb.plan_episode(str(tmp_path / "作品"), "第1集")
    assert plan["batches"] == [] and any("storyboard" in n or "n2d-script" in n for n in plan["notes"])
