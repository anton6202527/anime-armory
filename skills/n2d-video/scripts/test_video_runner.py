from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("video_runner.py")
spec = importlib.util.spec_from_file_location("video_runner", SCRIPT)
video_runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(video_runner)


PROMPT_PACK = """# clips

## Clip 06（时长 4.760s · 镜头 EP01_CLIP06）

**首帧**：`出图/第1集/图片/Clip_06_小禾撞门.png`

### 视频 prompt（中文，目标=即梦）
```
continuity:
  start_state: A
  action: B
  end_state: C
人物运动：小禾撞门；
镜头运动：固定；
```

## Clip 07（时长 6.080s · 镜头 EP01_CLIP07）

**首帧**：`出图/第1集/图片/Clip_07_催命酒到门前.png`

### 视频 prompt（中文，目标=即梦）
```
continuity:
  start_state: D
  action: E
  end_state: F
人物运动：托盘入画；
镜头运动：慢推；
```
"""


def test_prepare_manifest_uses_stable_prompt_files(tmp_path: Path) -> None:
    prompt_dir = tmp_path / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "01_clips.md").write_text(PROMPT_PACK, encoding="utf-8")
    image_dir = tmp_path / "出图" / "第1集" / "图片"
    image_dir.mkdir(parents=True)
    (image_dir / "Clip_06_小禾撞门.png").write_bytes(b"png")
    (image_dir / "Clip_07_催命酒到门前.png").write_bytes(b"png")

    manifest = video_runner.prepare_manifest(
        tmp_path,
        "第1集",
        6,
        7,
        backend="dreamina",
        resolution="720p",
        model_version="3.0",
    )

    assert manifest["kind"] == "n2d_video_batch"
    assert manifest["batch_id"] == "06_07"
    assert [item["clip"] for item in manifest["items"]] == ["Clip_06", "Clip_07"]
    assert [item["target"] for item in manifest["items"]] == ["Clip_06_小禾撞门.mp4", "Clip_07_催命酒到门前.mp4"]
    assert manifest["items"][0]["submit_duration"] == 5
    assert manifest["items"][1]["submit_duration"] == 7
    prompt_file = Path(manifest["items"][0]["prompt_file"])
    assert prompt_file.is_file()
    assert "/private/tmp" not in str(prompt_file)
    assert prompt_file.read_text(encoding="utf-8").startswith("continuity:")
    assert (tmp_path / "生产数据" / "video_batch_第1集_06_07.json").is_file()


def test_prepare_manifest_targets_use_physical_clip_number_not_mid_source_name(tmp_path: Path) -> None:
    prompt_pack = """# clips

## Clip 01（时长 8.5s · EP01_CLIP01 · 黑殿审问上）

**首帧**：`出图/第1集/图片/Clip01_黑殿审问.png`

### 视频 prompt（中文，目标=即梦）
```
人物运动：审问开始；
镜头运动：慢推；
```

## Clip 02（时长 8.5s · EP01_CLIP02 · 黑殿审问下）

**首帧**：`出图/第1集/图片/Clip01_黑殿审问_mid.png`

### 视频 prompt（中文，目标=即梦）
```
人物运动：灵根回答；
镜头运动：反打；
```
"""
    prompt_dir = tmp_path / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "01_clips.md").write_text(prompt_pack, encoding="utf-8")
    image_dir = tmp_path / "出图" / "第1集" / "图片"
    image_dir.mkdir(parents=True)
    (image_dir / "Clip01_黑殿审问.png").write_bytes(b"png")
    (image_dir / "Clip01_黑殿审问_mid.png").write_bytes(b"png")

    manifest = video_runner.prepare_manifest(
        tmp_path,
        "第1集",
        1,
        2,
        backend="dreamina",
        resolution="720p",
        model_version="3.0",
    )

    assert [item["target"] for item in manifest["items"]] == [
        "Clip_01_黑殿审问上.mp4",
        "Clip_02_黑殿审问下.mp4",
    ]
    assert [Path(item["prompt_file"]).name for item in manifest["items"]] == [
        "Clip_01_黑殿审问上.prompt.txt",
        "Clip_02_黑殿审问下.prompt.txt",
    ]


def test_submit_duration_has_dreamina_floor() -> None:
    assert video_runner.submit_duration(2.1) == 4
    assert video_runner.submit_duration(4.0) == 4
    assert video_runner.submit_duration(4.1) == 5


def test_dreamina_args_appends_dialogue_fact_contract(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("人物运动：张老大追问；\n声音约束：native_speech；", encoding="utf-8")
    contract_dir = tmp_path / "生产数据"
    contract_dir.mkdir()
    (contract_dir / "dialogue_fact_contract_第1集.json").write_text(
        """{
  "kind": "n2d_dialogue_fact_contract",
  "episode": "第1集",
  "clips": [{
    "clip": "Clip_02",
    "allowed_voiceover_indices": [4, 5],
    "allowed_narration_indices": [],
    "allowed_character_dialogue_indices": [4, 5],
    "allowed_dialogue": [
      {"index": 4, "role": "张老大", "text": "什么灵根？"},
      {"index": 5, "role": "贺平生", "text": "五行灵根。"}
    ],
    "allowed_character_dialogue": [
      {"index": 4, "role": "张老大", "text": "什么灵根？"},
      {"index": 5, "role": "贺平生", "text": "五行灵根。"}
    ],
    "allowed_narration": [],
    "screen_text_lines": [
      {"text": "十四岁 · 五行灵根", "render_policy": "compose_overlay_only", "purpose": "静音身份钩子"}
    ]
  }],
  "facts": [{
    "character": "贺平生",
    "key": "age",
    "canonical": "十四岁",
    "forbidden_values": ["15岁", "16岁"]
  }]
}""",
        encoding="utf-8",
    )

    args = video_runner._dreamina_args(
        {
            "clip": "Clip_02",
            "target": "Clip_02.mp4",
            "image": str(tmp_path / "first.png"),
            "prompt_file": str(prompt),
            "submit_duration": 4,
        },
        {"episode": "第1集", "_root": str(tmp_path)},
    )

    assert args[1] == "multimodal2video"
    assert args[args.index("--model_version") + 1] == "seedance2.0_vip"
    submitted_prompt = args[args.index("--prompt") + 1]
    assert "对白事实锁" in submitted_prompt
    assert "什么灵根？" in submitted_prompt
    assert "十四岁 · 五行灵根" in submitted_prompt
    assert "compose_stage_only" in submitted_prompt
    assert "video_model_must_not_generate_narration_voice" in submitted_prompt
    assert "不要在视频画面里烤字" in submitted_prompt
    assert "15岁" in submitted_prompt


def test_dreamina_args_blocks_native_speech_without_dialogue_fact_contract(tmp_path: Path) -> None:
    import pytest

    prompt = tmp_path / "prompt.txt"
    prompt.write_text("原生音画约束：台词+口型由原生音画后端生成；", encoding="utf-8")

    with pytest.raises(RuntimeError) as exc:
        video_runner._dreamina_args(
            {
                "clip": "Clip_02",
                "target": "Clip_02.mp4",
                "image": str(tmp_path / "first.png"),
                "prompt_file": str(prompt),
                "submit_duration": 4,
            },
            {"episode": "第1集", "_root": str(tmp_path)},
        )

    msg = str(exc.value)
    assert "dialogue fact contract missing before paid video submit" in msg
    assert "dialogue_fact_guard.py" in msg


def test_dreamina_args_blocks_native_speech_when_contract_has_no_character_dialogue(tmp_path: Path) -> None:
    import pytest

    prompt = tmp_path / "prompt.txt"
    prompt.write_text(
        "模型路由约束：mode=native_av，native_audio_policy=native_speech；\n"
        "原生音画约束：台词、口型由原生音画后端生成；",
        encoding="utf-8",
    )
    contract_dir = tmp_path / "生产数据"
    contract_dir.mkdir()
    (contract_dir / "dialogue_fact_contract_第1集.json").write_text(
        """{
  "kind": "n2d_dialogue_fact_contract",
  "episode": "第1集",
  "clips": [{
    "clip": "Clip_03",
    "allowed_voiceover_indices": [7, 8],
    "allowed_narration_indices": [7, 8],
    "allowed_character_dialogue_indices": [],
    "allowed_character_dialogue": [],
    "allowed_narration": [
      {"index": 7, "role": "旁白", "text": "五行俱全，却无人愿收。"}
    ],
    "screen_text_lines": [
      {"text": "五行俱全，却无人愿收", "render_policy": "compose_overlay_only"}
    ]
  }],
  "facts": []
}""",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError) as exc:
        video_runner._dreamina_args(
            {
                "clip": "Clip_03",
                "target": "Clip_03.mp4",
                "image": str(tmp_path / "first.png"),
                "prompt_file": str(prompt),
                "submit_duration": 4,
            },
            {"episode": "第1集", "_root": str(tmp_path)},
        )

    msg = str(exc.value)
    assert "native_speech route has no allowed character dialogue" in msg
    assert "narration belongs to compose" in msg


def test_acceptance_recipe_meta_does_not_enforce_submit_only_native_speech_guard(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.txt"
    prompt.write_text(
        "模型路由约束：mode=native_av，native_audio_policy=native_speech；\n"
        "原生音画约束：台词、口型由原生音画后端生成；",
        encoding="utf-8",
    )
    first = tmp_path / "first.png"
    first.write_bytes(b"first")
    contract_dir = tmp_path / "生产数据"
    contract_dir.mkdir()
    (contract_dir / "dialogue_fact_contract_第1集.json").write_text(
        """{
  "kind": "n2d_dialogue_fact_contract",
  "episode": "第1集",
  "clips": [{
    "clip": "Clip_03",
    "allowed_voiceover_indices": [7],
    "allowed_narration_indices": [7],
    "allowed_character_dialogue_indices": [],
    "allowed_character_dialogue": [],
    "allowed_narration": [
      {"index": 7, "role": "旁白", "text": "五行俱全，却无人愿收。"}
    ],
    "screen_text_lines": []
  }],
  "facts": []
}""",
        encoding="utf-8",
    )

    meta = video_runner.acceptance_recipe_meta(
        tmp_path,
        "第1集",
        {
            "clip": "Clip_03",
            "image": str(first),
            "prompt_file": str(prompt),
            "cost_provider": "dreamina",
            "submit_id": "sid123",
        },
        {"episode": "第1集", "backend": "dreamina", "model_version": "3.0", "video_resolution": "720p"},
    )

    assert meta["submit_id"] == "sid123"
    assert meta["prompt_sha256"]


def test_dreamina_args_allows_non_native_prompt_without_dialogue_fact_contract(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("人物运动：抬头；\n镜头运动：慢推；", encoding="utf-8")

    args = video_runner._dreamina_args(
        {
            "clip": "Clip_02",
            "target": "Clip_02.mp4",
            "image": str(tmp_path / "first.png"),
            "prompt_file": str(prompt),
            "submit_duration": 4,
        },
        {"episode": "第1集", "_root": str(tmp_path)},
    )

    submitted_prompt = args[args.index("--prompt") + 1]
    assert "对白事实锁" not in submitted_prompt


def test_prepare_manifest_marks_native_speech_for_multimodal(tmp_path: Path) -> None:
    prompt_pack = """# clips

## Clip 01（时长 4s · EP01_CLIP01 · 说话）

**首帧**：`出图/第1集/图片/Clip_01.png`

### 视频 prompt（中文，目标=即梦）
```
模型路由约束：mode=native_av; native_audio_policy=native_speech;
声音约束：台词+口型由原生音画后端生成；
```
"""
    prompt_dir = tmp_path / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "01_clips.md").write_text(prompt_pack, encoding="utf-8")
    image_dir = tmp_path / "出图" / "第1集" / "图片"
    image_dir.mkdir(parents=True)
    (image_dir / "Clip_01.png").write_bytes(b"png")

    manifest = video_runner.prepare_manifest(
        tmp_path,
        "第1集",
        1,
        1,
        backend="dreamina",
        resolution="720p",
        model_version="3.0",
    )

    item = manifest["items"][0]
    assert item["require_audio"] is True
    assert item["force_multimodal"] is True


def test_prepare_manifest_does_not_mark_no_native_speech_for_multimodal(tmp_path: Path) -> None:
    prompt_pack = """# clips

## Clip 01（时长 4s · EP01_CLIP01 · 静音）

**首帧**：`出图/第1集/图片/Clip_01.png`

### 视频 prompt（中文，目标=即梦）
```
模型路由约束：mode=image2video; native_audio_policy=no_native_speech;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；若平台强出声音，后期丢弃。
```
"""
    prompt_dir = tmp_path / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "01_clips.md").write_text(prompt_pack, encoding="utf-8")
    image_dir = tmp_path / "出图" / "第1集" / "图片"
    image_dir.mkdir(parents=True)
    (image_dir / "Clip_01.png").write_bytes(b"png")

    manifest = video_runner.prepare_manifest(
        tmp_path,
        "第1集",
        1,
        1,
        backend="dreamina",
        resolution="720p",
        model_version="3.0",
    )

    item = manifest["items"][0]
    assert "require_audio" not in item
    assert "force_multimodal" not in item


def test_submit_clip_runs_video_preflight_before_backend(monkeypatch, tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("人物运动：抬眼；\n镜头运动：慢推；", encoding="utf-8")
    manifest_file = tmp_path / "manifest.json"
    video_runner.atomic_write_json(
        manifest_file,
        {
            "episode": "第1集",
            "items": [
                {
                    "clip": "Clip_01",
                    "target": "Clip_01.mp4",
                    "image": str(tmp_path / "first.png"),
                    "prompt_file": str(prompt),
                    "submit_duration": 4,
                    "status": "prepared",
                }
            ],
        },
    )
    preflight_calls = []

    def fake_preflight(root, episode, stage="video_preflight"):
        preflight_calls.append((root, episode, stage))

    class Proc:
        returncode = 0
        stdout = '{"submit_id":"abc123","gen_status":"processing"}'
        stderr = ""

    monkeypatch.setattr(video_runner, "run_preflight_gate", fake_preflight)
    monkeypatch.setattr(video_runner, "run_identity_handoff_guard", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(video_runner, "verify_cli_contract", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(video_runner.subprocess, "run", lambda *args, **kwargs: Proc())

    result = video_runner.submit_clip(tmp_path, manifest_file, "Clip_01")

    assert preflight_calls == [(tmp_path, "第1集", "video_preflight")]
    assert result["submit_id"] == "abc123"
    assert result["status"] == "submitted"


def test_resolve_video_backend_dreamina_and_aliases():
    for raw in ("dreamina", "即梦", "Jimeng", None, ""):
        key, adapter = video_runner.resolve_video_backend({"backend": raw} if raw is not None else {})
        assert key == "dreamina"
        assert adapter["provider"] == "dreamina"
        assert adapter["submit_args"] is video_runner._dreamina_args


def test_resolve_video_backend_unsupported_reports_gap_not_silent_switch():
    import pytest

    with pytest.raises(RuntimeError) as exc:
        video_runner.resolve_video_backend({"backend": "kling"})
    msg = str(exc.value)
    assert "kling" in msg and "不偷偷换路" in msg  # C2: stop & report, never substitute dreamina


def test_resolve_video_backend_manual_points_to_accept():
    import pytest

    with pytest.raises(RuntimeError) as exc:
        video_runner.resolve_video_backend({"backend": "manual"})
    assert "accept" in str(exc.value)


def test_submit_clip_unsupported_backend_never_calls_a_cli(monkeypatch, tmp_path: Path):
    import pytest

    manifest_file = tmp_path / "manifest.json"
    video_runner.atomic_write_json(
        manifest_file,
        {"episode": "第1集", "backend": "veo",
         "items": [{"clip": "Clip_01", "target": "Clip_01.mp4", "image": str(tmp_path / "f.png"),
                    "prompt_file": str(tmp_path / "p.txt"), "submit_duration": 4, "status": "prepared"}]},
    )

    def boom(*_a, **_k):  # any subprocess call = silent switch leaked through
        raise AssertionError("must not invoke any backend CLI for an unsupported backend")

    monkeypatch.setattr(video_runner.subprocess, "run", boom)
    # even dry_run resolves the backend first, so it fails fast without building dreamina argv
    with pytest.raises(RuntimeError):
        video_runner.submit_clip(tmp_path, manifest_file, "Clip_01", dry_run=True)


def test_qc_override_payload_marks_false_positive_sample():
    p = video_runner.qc_override_payload("Clip_02", {"seam_blocks": 1, "seam_warns": 2})
    assert p["qa"]["outcome"] == "human_override_false_positive"
    assert p["qa"]["seam_blocks"] == 1 and p["qa"]["seam_warns"] == 2
    assert p["meta"]["clip"] == "Clip_02"
    assert video_runner.qc_override_payload("x", {})["qa"]["seam_blocks"] == 0


def test_acceptance_recipe_meta_has_release_gate_fields(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("人物运动：抬眼；\n镜头运动：慢推；", encoding="utf-8")
    first = tmp_path / "first.png"
    end = tmp_path / "end.png"
    first.write_bytes(b"first")
    end.write_bytes(b"end")
    routes = tmp_path / "出视频" / "第1集" / "prompt" / "video_model_routes.json"
    routes.parent.mkdir(parents=True)
    routes.write_text('{"routes":[]}', encoding="utf-8")
    cap = tmp_path / "生产数据" / "video_backend_capabilities" / "seedance__via_dreamina.json"
    cap.parent.mkdir(parents=True)
    cap.write_text('{"backend":"seedance"}', encoding="utf-8")

    meta = video_runner.acceptance_recipe_meta(
        tmp_path,
        "第1集",
        {
            "clip": "Clip_01",
            "image": str(first),
            "end_image": str(end),
            "prompt_file": str(prompt),
            "frame_control_mode": "multi_keyframe",
            "anchor_consumption_mode": "first_last",
            "cost_provider": "dreamina",
            "submit_id": "sid123",
        },
        {"episode": "第1集", "backend": "dreamina", "model_version": "3.0", "video_resolution": "720p"},
    )

    required = {
        "provider",
        "model",
        "channel",
        "route_hash",
        "capability_evidence_id",
        "recipe_hash",
        "prompt_sha256",
        "reference_bundle_sha256",
        "backend_version",
        "quality_tier",
        "actual_image_inputs",
        "seed_effective",
        "effective_seed",
        "seed_support",
    }
    assert required <= set(meta)
    assert meta["actual_image_inputs"] == ["first.png", "end.png"]
    assert meta["seed_effective"] is False
    assert meta["seed_support"] == "unsupported_or_unknown"


def test_acceptance_recipe_meta_resolves_root_prefixed_relative_target(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "创作区" / "制漫剧" / "测试剧"
    target = root / "出视频" / "第1集" / "视频" / "Clip_08.mp4"
    target.parent.mkdir(parents=True)
    payload = b"accepted-video"
    target.write_bytes(payload)
    prompt = root / "prompt.txt"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text("人物运动：抬眼；\n镜头运动：慢推；", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    root_prefixed_rel = str(target.relative_to(tmp_path))

    meta = video_runner.acceptance_recipe_meta(
        root,
        "第1集",
        {
            "clip": "Clip_08",
            "target_path": root_prefixed_rel,
            "prompt_file": str(prompt),
            "cost_provider": "dreamina",
        },
        {"episode": "第1集", "backend": "dreamina", "model_version": "3.0", "video_resolution": "720p"},
    )

    assert video_runner._rel_path(root, root_prefixed_rel) == "出视频/第1集/视频/Clip_08.mp4"
    assert meta["artifact_sha256"] == hashlib.sha256(payload).hexdigest()


def test_accept_clip_updates_native_av_sidecar(monkeypatch, tmp_path: Path) -> None:
    video = tmp_path / "出视频" / "第1集" / "视频" / "Clip_01.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"mp4")
    manifest_file = tmp_path / "manifest.json"
    video_runner.atomic_write_json(
        manifest_file,
        {
            "episode": "第1集",
            "items": [{"clip": "Clip_01", "target": "Clip_01.mp4", "status": "downloaded"}],
        },
    )
    calls = []

    def fake_run_qc(root, episode, clips, qc_range, **_kwargs):
        return {
            "clips": [{"has_audio": True}],
            "machine_summary": {"seam_blocks": 0, "intra_blocks": 0, "anchor_blocks": 0},
            "json_path": "qc.json",
            "markdown_path": "qc.md",
        }

    def fake_sidecar(root, episode, item, target, qc_clip):
        calls.append((root, episode, item["clip"], target, qc_clip))
        return {"status": "updated", "physics_path": "生产数据/native_av_physics_第1集.json"}

    monkeypatch.setattr(video_runner.video_qc, "run_qc", fake_run_qc)
    monkeypatch.setattr(video_runner.native_av_sidecar, "update_sidecars", fake_sidecar)

    item = video_runner.accept_clip(tmp_path, manifest_file, "Clip_01", no_record=True, no_progress=True)

    assert calls and calls[0][1:4] == ("第1集", "Clip_01", video)
    assert item["native_av_sidecar"]["status"] == "updated"
    saved = video_runner.load_json(manifest_file)
    assert saved["items"][0]["native_av_sidecar"]["physics_path"].endswith("native_av_physics_第1集.json")


def test_query_clip_replaces_stale_existing_target(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "出视频" / "第1集" / "视频" / "Clip_01.mp4"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"stub")
    manifest_file = tmp_path / "manifest.json"
    video_runner.atomic_write_json(
        manifest_file,
        {
            "episode": "第1集",
            "items": [
                {
                    "clip": "Clip_01",
                    "target": "Clip_01.mp4",
                    "status": "submitted",
                    "submit_id": "sid123",
                }
            ],
        },
    )

    def fake_resolve(_manifest):
        return "dreamina", {"query_args": lambda _sid, out_dir: ["dreamina", "query_result", str(out_dir)]}

    class Proc:
        returncode = 0
        stdout = '{"gen_status":"success"}'
        stderr = ""

    def fake_run(args, **_kwargs):
        download_dir = Path(args[-1])
        download_dir.mkdir(parents=True, exist_ok=True)
        (download_dir / "fresh.mp4").write_bytes(b"fresh-video" * 1024)
        return Proc()

    monkeypatch.setattr(video_runner, "resolve_video_backend", fake_resolve)
    monkeypatch.setattr(video_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(video_runner, "_valid_downloaded_mp4", lambda _path: True)

    item = video_runner.query_clip(tmp_path, manifest_file, "Clip_01")

    assert item["status"] == "downloaded"
    assert target.read_bytes().startswith(b"fresh-video")
    assert target.stat().st_size >= 4096


def test_query_clip_accepts_valid_download_when_cli_times_out(monkeypatch, tmp_path: Path) -> None:
    manifest_file = tmp_path / "manifest.json"
    video_runner.atomic_write_json(
        manifest_file,
        {
            "episode": "第1集",
            "items": [
                {
                    "clip": "Clip_01",
                    "target": "Clip_01.mp4",
                    "status": "submitted",
                    "submit_id": "sid123",
                }
            ],
        },
    )

    def fake_resolve(_manifest):
        return "dreamina", {"query_args": lambda _sid, out_dir: ["dreamina", "query_result", str(out_dir)]}

    class Proc:
        returncode = 1
        stdout = ""
        stderr = "download video 1: write file: context deadline exceeded"

    def fake_run(args, **_kwargs):
        download_dir = Path(args[-1])
        download_dir.mkdir(parents=True, exist_ok=True)
        (download_dir / "sid123_video_1.mp4").write_bytes(b"fresh-video" * 1024)
        return Proc()

    monkeypatch.setattr(video_runner, "resolve_video_backend", fake_resolve)
    monkeypatch.setattr(video_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(video_runner, "_valid_downloaded_mp4", lambda _path: True)

    item = video_runner.query_clip(tmp_path, manifest_file, "Clip_01")

    target = tmp_path / "出视频" / "第1集" / "视频" / "Clip_01.mp4"
    assert item["status"] == "downloaded"
    assert "context deadline exceeded" in item["query_warning"]
    assert target.exists()


def test_query_clip_does_not_move_stale_download_when_generation_pending(monkeypatch, tmp_path: Path) -> None:
    download_dir = tmp_path / "出视频" / "第1集" / "视频" / "_downloads"
    download_dir.mkdir(parents=True)
    stale = download_dir / "other_video_1.mp4"
    stale.write_bytes(b"stale-video" * 1024)
    manifest_file = tmp_path / "manifest.json"
    video_runner.atomic_write_json(
        manifest_file,
        {
            "episode": "第1集",
            "items": [
                {
                    "clip": "Clip_01",
                    "target": "Clip_01.mp4",
                    "status": "submitted",
                    "submit_id": "sid123",
                }
            ],
        },
    )

    def fake_resolve(_manifest):
        return "dreamina", {"query_args": lambda _sid, out_dir: ["dreamina", "query_result", str(out_dir)]}

    class Proc:
        returncode = 0
        stdout = '{"gen_status":"querying","queue_info":{"queue_status":"Generating"}}'
        stderr = ""

    monkeypatch.setattr(video_runner, "resolve_video_backend", fake_resolve)
    monkeypatch.setattr(video_runner.subprocess, "run", lambda *args, **kwargs: Proc())

    item = video_runner.query_clip(tmp_path, manifest_file, "Clip_01")

    assert item["status"] == "queried"
    assert stale.exists()
    assert not (tmp_path / "出视频" / "第1集" / "视频" / "Clip_01.mp4").exists()


def test_valid_downloaded_mp4_rejects_end_decode_failure(monkeypatch, tmp_path: Path) -> None:
    video = tmp_path / "broken_tail.mp4"
    video.write_bytes(b"x" * 8192)

    class Proc:
        def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(args, **_kwargs):
        if args[0] == "ffprobe":
            return Proc(0, "8.0\n")
        if args[0] == "ffmpeg":
            return Proc(1, "", "Invalid NAL unit size")
        raise AssertionError(args)

    monkeypatch.setattr(video_runner.subprocess, "run", fake_run)

    assert video_runner._valid_downloaded_mp4(video) is False


def test_submit_clip_skip_preflight_records_waiver(monkeypatch, tmp_path: Path) -> None:
    # H2：--skip-preflight 不再静默旁路 video_preflight——必须记 dashboard waiver 留痕。
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("人物运动：抬眼；\n镜头运动：慢推；", encoding="utf-8")
    manifest_file = tmp_path / "manifest.json"
    video_runner.atomic_write_json(manifest_file, {
        "episode": "第1集",
        "items": [{"clip": "Clip_01", "target": "Clip_01.mp4", "image": str(tmp_path / "first.png"),
                   "prompt_file": str(prompt), "submit_duration": 4, "status": "prepared"}],
    })

    class Proc:
        returncode = 0
        stdout = '{"submit_id":"abc123","gen_status":"processing"}'
        stderr = ""

    preflight_calls = []
    waiver_calls = []
    monkeypatch.setattr(video_runner, "run_preflight_gate",
                        lambda *a, **k: preflight_calls.append(a))
    monkeypatch.setattr(video_runner, "run_identity_handoff_guard", lambda *a, **k: None)
    monkeypatch.setattr(video_runner, "verify_cli_contract", lambda *a, **k: None)
    monkeypatch.setattr(video_runner, "record_waiver",
                        lambda root, ep, stage, waiver, reason: waiver_calls.append((ep, stage, waiver)))
    monkeypatch.setattr(video_runner.subprocess, "run", lambda *a, **k: Proc())

    video_runner.submit_clip(tmp_path, manifest_file, "Clip_01", skip_preflight=True)

    assert preflight_calls == []                                  # preflight 确实被跳过
    assert waiver_calls == [("第1集", "video_preflight", "skip-preflight")]  # 但留了痕
