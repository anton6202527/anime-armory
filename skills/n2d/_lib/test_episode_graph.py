from __future__ import annotations

import json
from pathlib import Path

import episode_graph
import n2d_blocking


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_episode_graph_connects_story_route_job_media_proxy_master_release(tmp_path: Path) -> None:
    ep = "第1集"
    _write(tmp_path / "脚本" / ep / "storyboard.json", {"clips": [{"id": "Clip_01", "duration": 2.0}]})
    _write(tmp_path / "出视频" / ep / "prompt" / "video_model_routes.json", {"routes": [{
        "clip_id": "Clip_01", "primary_backend": "seedance", "route_executable": True,
        "execution_adapter": {"state": "automated_ready"},
    }]})
    media = tmp_path / "出视频" / ep / "视频" / "Clip_01.mp4"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"video")
    _write(tmp_path / "生产数据" / f"video_batch_{ep}_01_01.json", {
        "items": [{"clip": "Clip_01", "target_path": str(media), "status": "accepted", "submit_id": "j1"}],
    })
    proxy_media = tmp_path / "合成" / ep / "_proxy" / "actual_rough_cut.mp4"
    proxy_media.parent.mkdir(parents=True)
    proxy_media.write_bytes(b"proxy")
    _write(tmp_path / "生产数据" / f"post_video_proxy_{ep}.json", {
        "status": "ready", "output": f"合成/{ep}/_proxy/actual_rough_cut.mp4",
        "timeline": [{"source": f"出视频/{ep}/视频/Clip_01.mp4"}],
    })
    master = tmp_path / "合成" / ep / "master.mp4"
    master.write_bytes(b"master")
    _write(tmp_path / "生产数据" / f"release_verdict_{ep}.json", {"status": "internal-only", "profile": "internal"})

    payload = episode_graph.build(tmp_path, ep)

    assert payload["status"] == "pass"
    assert payload["summary"] == {
        "nodes": 8, "edges": 8, "story_clips": 1, "routes": 1,
        "video_media": 1, "masters": 1, "lineage_gaps": 0, "clip_roots": 1,
    }
    relations = {row["relation"] for row in payload["edges"]}
    assert {"routed_by", "executed_as", "produced", "included_in", "assembled_into", "assessed_by"} <= relations
    assert len(payload["graph_hash"]) == 64
    assert len(payload["artifact_root_sha256"]) == 64
    assert len(payload["root_sha256"]) == 64
    assert len(payload["clip_roots"]["Clip_01"]) == 64
    assert all(len(row["content_sha256"]) == 64 for row in payload["nodes"])
    assert all(len(row["lineage_sha256"]) == 64 for row in payload["nodes"])


def test_episode_graph_diff_localizes_change_to_downstream_clip(tmp_path: Path) -> None:
    ep = "第1集"
    storyboard = tmp_path / "脚本" / ep / "storyboard.json"
    _write(storyboard, {"clips": [{"id": "Clip_01", "duration": 2.0}, {"id": "Clip_02", "duration": 3.0}]})
    before = episode_graph.build(tmp_path, ep)

    _write(storyboard, {"clips": [{"id": "Clip_01", "duration": 2.0}, {"id": "Clip_02", "duration": 4.0}]})
    after = episode_graph.build(tmp_path, ep)
    change = episode_graph.diff_graphs(before, after)

    assert "clip:Clip_02" in change["direct_changed_nodes"]
    assert "Clip_02" in change["affected_clips"]
    assert "Clip_01" not in change["affected_clips"]
    assert before["clip_roots"]["Clip_01"] == after["clip_roots"]["Clip_01"]
    assert before["clip_roots"]["Clip_02"] != after["clip_roots"]["Clip_02"]


def test_write_records_change_set_without_changing_canonical_root(tmp_path: Path) -> None:
    ep = "第1集"
    storyboard = tmp_path / "脚本" / ep / "storyboard.json"
    _write(storyboard, {"clips": [{"id": "Clip_01", "duration": 2.0}]})
    first = episode_graph.build(tmp_path, ep)
    episode_graph.write(tmp_path, ep, first)
    _write(storyboard, {"clips": [{"id": "Clip_01", "duration": 2.5}]})
    second = episode_graph.build(tmp_path, ep)
    episode_graph.write(tmp_path, ep, second)

    written = json.loads(episode_graph.graph_path(tmp_path, ep).read_text(encoding="utf-8"))
    assert written["root_sha256"] == second["root_sha256"]
    assert "clip:Clip_01" in written["change_set"]["direct_changed_nodes"]


def test_blocking_bundle_normalizes_gate_without_becoming_a_gate(tmp_path: Path) -> None:
    bundle = n2d_blocking.build({
        "frontier": {"ep": "第1集", "stage_key": "video", "owner": "n2d-video"},
        "stop_reason": "blocked_by_gate",
        "action_card": {"headline": "先修复", "to_user": "接缝不合格", "exact_command": "repair"},
        "gate": {"blocked": True, "stage": "video_preflight", "return_to_stage": "image"},
    }, graph={"graph_hash": "abc", "status": "warn", "summary": {"lineage_gaps": 2}})

    paths = n2d_blocking.write(tmp_path, bundle)

    assert bundle["category"] == "contract_or_gate"
    assert bundle["blocked"] is True
    assert bundle["repair_commands"] == ["repair"]
    assert bundle["episode_graph"]["lineage_gaps"] == 2
    assert Path(paths["json"]).is_file()
