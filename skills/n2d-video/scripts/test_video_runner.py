from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


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


COMPILED_PROMPT_PACK = """# clips

## Clip 01（时长 4.0s · EP01_CLIP01 · 冷开）

**首帧**：`出图/第1集/图片/Clip_01.png`

### 视频 prompt（中文，旧包兼容块，不得优先提交）
```text
这是旧的冗长 prompt，包含路由、审计和执行配方。
```

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=1; profile_version=2026-07-10.1; profile=zh_motion_first; backend=dreamina; mode=image2video; language=zh; native_audio_policy=none; source_contract_sha256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```text
以已提交首帧为视觉真值。主动作：她缓慢抬眼。镜头：极缓推近，尾端固定。
```
"""


def test_parse_prompt_pack_prefers_compiled_submit_prompt(tmp_path: Path) -> None:
    prompt_dir = tmp_path / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "01_clips.md").write_text(COMPILED_PROMPT_PACK, encoding="utf-8")

    items = video_runner.parse_prompt_pack(tmp_path, "第1集", 1, 1)

    assert items[0]["prompt_source_kind"] == "compiled_submit_prompt"
    assert items[0]["prompt_compiler"]["backend"] == "dreamina"
    assert items[0]["prompt_text"].startswith("以已提交首帧为视觉真值")
    assert "旧的冗长" not in items[0]["prompt_text"]


def test_prepare_manifest_rejects_compiled_prompt_for_different_backend(tmp_path: Path) -> None:
    prompt_dir = tmp_path / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "01_clips.md").write_text(COMPILED_PROMPT_PACK, encoding="utf-8")
    image_dir = tmp_path / "出图" / "第1集" / "图片"
    image_dir.mkdir(parents=True)
    (image_dir / "Clip_01.png").write_bytes(b"png")

    with pytest.raises(ValueError, match="compiled prompt backend=dreamina"):
        video_runner.prepare_manifest(
            tmp_path,
            "第1集",
            1,
            1,
            backend="veo",
            resolution="720p",
            model_version="auto",
        )


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


def test_prepare_manifest_auto_uses_vip_and_720p_for_sufficient_budget(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("出视频规格：预算充足\n", encoding="utf-8")
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
        resolution="auto",
        model_version="auto",
    )

    assert manifest["video_budget_tier"] == "预算充足"
    assert manifest["video_resolution"] == "720p"
    assert manifest["model_version"] == "seedance2.0_vip"
    assert {item["model_version"] for item in manifest["items"]} == {"seedance2.0_vip"}


def test_prepare_manifest_auto_defaults_to_sufficient_budget_without_settings(tmp_path: Path) -> None:
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
        resolution="auto",
        model_version="auto",
    )

    assert manifest["video_budget_tier"] == "预算充足"
    assert manifest["video_resolution"] == "720p"
    assert manifest["model_version"] == "seedance2.0_vip"


def test_prepare_manifest_auto_keeps_explicit_1080p_resolution(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("出视频规格：预算充足\n视频分辨率：1080p\n", encoding="utf-8")
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
        resolution="auto",
        model_version="auto",
    )

    assert manifest["video_budget_tier"] == "预算充足"
    assert manifest["video_resolution"] == "1080p"
    assert manifest["model_version"] == "seedance2.0_vip"


def test_prepare_manifest_auto_uses_vip_for_high_value_clip_only(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("出视频规格：预算一般\n", encoding="utf-8")
    prompt_pack = """# clips

## Clip 01（时长 4s · EP01_CLIP01 · 普通反应）

**首帧**：`出图/第1集/图片/Clip_01.png`

### 视频 prompt（中文，目标=即梦）
```
人物运动：抬头；
镜头运动：慢推；
```

## Clip 02（时长 4s · EP01_CLIP02 · 🔑 爽点高光）

**首帧**：`出图/第1集/图片/Clip_02.png`

### 视频 prompt（中文，目标=即梦）
```
模型路由：quality_tier=high；
人物运动：一刀斩落；
镜头运动：快速跟推；
```
"""
    prompt_dir = tmp_path / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "01_clips.md").write_text(prompt_pack, encoding="utf-8")
    image_dir = tmp_path / "出图" / "第1集" / "图片"
    image_dir.mkdir(parents=True)
    (image_dir / "Clip_01.png").write_bytes(b"png")
    (image_dir / "Clip_02.png").write_bytes(b"png")

    manifest = video_runner.prepare_manifest(
        tmp_path,
        "第1集",
        1,
        2,
        backend="dreamina",
        resolution="auto",
        model_version="auto",
    )

    assert manifest["video_budget_tier"] == "预算一般"
    assert manifest["video_resolution"] == "720p"
    assert manifest["model_version"] == "seedance2.0fast"
    assert [item["model_version"] for item in manifest["items"]] == ["seedance2.0fast", "seedance2.0_vip"]
    assert manifest["items"][1]["model_version_reason"] == "high_value_clip_uses_vip"
    args = video_runner._dreamina_args(manifest["items"][1], {**manifest, "_root": str(tmp_path)})
    assert args[1] == "image2video"
    assert args[args.index("--model_version") + 1] == "seedance2.0_vip"


def test_submit_duration_has_dreamina_floor() -> None:
    assert video_runner.submit_duration(2.1) == 4
    assert video_runner.submit_duration(4.0) == 4
    assert video_runner.submit_duration(4.1) == 5


def test_attach_multiframe_submit_duration_uses_native_timeline(tmp_path: Path) -> None:
    image_dir = tmp_path / "出图" / "第1集" / "图片"
    image_dir.mkdir(parents=True)
    rels = [
        "出图/第1集/图片/Clip03_first.png",
        "出图/第1集/图片/Clip03_a1.png",
        "出图/第1集/图片/Clip03_a2.png",
        "出图/第1集/图片/Clip03_a3.png",
        "出图/第1集/图片/Clip03_a4.png",
        "出图/第1集/图片/Clip03_end.png",
    ]
    for rel in rels:
        (tmp_path / rel).write_bytes(b"png")

    item = {
        "clip": "Clip_03",
        "image_rel": rels[0],
        "image": str(tmp_path / rels[0]),
        "end_image_rel": rels[-1],
        "end_image": str(tmp_path / rels[-1]),
        "story_duration": 24.832,
        "submit_duration": 15,
    }

    assert video_runner.attach_multiframe(
        tmp_path,
        item,
        "人物运动：握刀抬眼；",
        {
            3: {
                "times": [4.91, 9.81, 14.72, 19.62],
                "images": rels[1:-1],
                "uses": ["split", "split", "split", "split"],
                "hints": ["a1", "a2", "a3", "a4"],
                "duration": 24.832,
                "end_state": "停在尾帧",
            }
        },
    )

    assert item["mode_backend"] == "multiframe2video"
    assert item["multiframe_segment_durations"] == [4.91, 4.9, 4.91, 4.9, 5.212]
    assert item["submit_duration"] == 24.832


def test_submit_blocks_unsplit_story_clip_over_hard_cap(tmp_path: Path) -> None:
    import pytest

    prompt = tmp_path / "prompt.txt"
    prompt.write_text("人物运动：缓慢走过官道；", encoding="utf-8")
    manifest = tmp_path / "video_batch_第1集_01_01.json"
    manifest.write_text(json.dumps({
        "episode": "第1集",
        "backend": "dreamina",
        "items": [{
            "clip": "Clip_01",
            "target": "Clip_01.mp4",
            "image": str(tmp_path / "first.png"),
            "prompt_file": str(prompt),
            "story_duration": 33.0,
            "submit_duration": 15,
            "status": "prepared",
        }],
    }, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(RuntimeError) as exc:
        video_runner.submit_clip(tmp_path, manifest, "Clip_01", dry_run=True)

    assert "exceeds hard single video_shot cap" in str(exc.value)
    assert "physical 4-8s video_shot parts" in str(exc.value)


def test_prepare_splits_long_story_clip_into_physical_parts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(video_runner, "video_backend_frame_control", lambda *_a, **_k: {
        "mode": "multi_keyframe",
        "supports_last_frame": True,
        "supports_native_mid_anchors": True,
    })
    monkeypatch.setattr(video_runner, "anchor_consumption_plan", lambda *_a, **_k: {
        "consumption_mode": "native_multiframe",
        "supports_last_frame": True,
        "supports_native_mid_anchors": True,
        "consumes_endframe": True,
        "consumes_mid_anchors_natively": True,
    })

    prompt_dir = tmp_path / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    prompt_dir.joinpath("01_clips.md").write_text(
        """## Clip 01（时长 18.000s · 长剧情段）

**首帧**：`出图/第1集/图片/Clip01_first.png`
**尾帧**：`出图/第1集/图片/Clip01_end.png`

### 视频 prompt（中文，目标=即梦）
```
人物运动：从首帧动作接到尾帧落幅。
```
""",
        encoding="utf-8",
    )
    image_dir = tmp_path / "出图" / "第1集" / "图片"
    image_dir.mkdir(parents=True)
    for name in ("Clip01_first.png", "Clip01_a1.png", "Clip01_a2.png", "Clip01_end.png"):
        (image_dir / name).write_bytes(b"png")
    sb_dir = tmp_path / "脚本" / "第1集"
    sb_dir.mkdir(parents=True)
    sb_dir.joinpath("storyboard.json").write_text(json.dumps({
        "clips": [{
            "id": "Clip_01",
            "duration": 18.0,
            "template_contract": {"beats": ["起", "承", "落"]},
            "continuity": {
                "end_state": "停在尾帧",
                "anchors": [
                    {"at_sec": 6.0, "anchor_png": "出图/第1集/图片/Clip01_a1.png"},
                    {"at_sec": 12.0, "anchor_png": "出图/第1集/图片/Clip01_a2.png"},
                ],
            },
        }],
    }, ensure_ascii=False), encoding="utf-8")

    manifest = video_runner.prepare_manifest(
        tmp_path, "第1集", 1, 1, backend="dreamina",
        resolution="auto", model_version="auto", force=True,
    )

    clips = [item["clip"] for item in manifest["items"]]
    assert clips == ["Clip_01_part1", "Clip_01_part2", "Clip_01_part3"]
    assert all(item["story_duration"] == 6.0 for item in manifest["items"])
    assert all(item["video_shot_segment"]["parent_story_clip"] == "Clip_01" for item in manifest["items"])


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


def test_dreamina_args_normalizes_legacy_model_for_two_frame_multimodal(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.txt"
    first = tmp_path / "first.png"
    last = tmp_path / "last.png"
    prompt.write_text("人物运动：抬头；\n镜头运动：慢推；", encoding="utf-8")
    first.write_bytes(b"first")
    last.write_bytes(b"last")

    args = video_runner._dreamina_args(
        {
            "clip": "Clip_02",
            "target": "Clip_02.mp4",
            "image": str(first),
            "end_image": str(last),
            "prompt_file": str(prompt),
            "submit_duration": 4,
        },
        {
            "episode": "第1集",
            "_root": str(tmp_path),
            "model_version": "3.0",
            "video_resolution": "720p",
        },
    )

    assert args[1] == "multimodal2video"
    assert args[args.index("--model_version") + 1] == "seedance2.0_vip"


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


def test_prepare_manifest_ignores_conditional_native_speech_wording_for_silent_clip(tmp_path: Path) -> None:
    prompt_pack = """# clips

## Clip 01（时长 4s · EP01_CLIP01 · 静音）

**首帧**：`出图/第1集/图片/Clip_01.png`

### 视频 prompt（中文，目标=即梦）
```
模型路由约束：mode=image2video; native_audio_policy=none;
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
禁止：非 native_speech 镜不要生成原生人声；
声音约束：无对白、无旁白、不要生成原生人声；
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


def test_qc_block_payload_records_blocking_identity_qc() -> None:
    p = video_runner.qc_block_payload({
        "clip": "Clip_03",
        "target": "Clip_03.mp4",
        "fail_reason": "dense identity warn",
        "qc_json": "qc.json",
        "qc_machine": {"intra_warns": 1, "anchor_warns": 3},
    })

    assert p["qa"]["severity"] == "block"
    assert p["qa"]["outcome"] == "qc_blocked"
    assert p["qa"]["intra_warns"] == 1
    assert p["meta"]["clip"] == "Clip_03"


def test_acceptance_recipe_meta_has_release_gate_fields(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("人物运动：抬眼；\n镜头运动：慢推；", encoding="utf-8")
    first = tmp_path / "first.png"
    end = tmp_path / "end.png"
    first.write_bytes(b"first")
    end.write_bytes(b"end")
    routes = tmp_path / "出视频" / "第1集" / "prompt" / "video_model_routes.json"
    routes.parent.mkdir(parents=True)
    routes.write_text(json.dumps({
        "routes": [{
            "clip_id": "Clip_01",
            "mode": "image2video",
            "execution_recipe": {
                "post_video_qc": {
                    "identity_qc_required": True,
                    "dense_face_watch_required": True,
                    "required_reports": ["video_qc", "temporal_consistency", "video_face_drift_watch"],
                    "acceptance_policy": "block_clear_wrong_closeup_face",
                }
            },
        }]
    }, ensure_ascii=False), encoding="utf-8")
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
        "route_execution_recipe_hash",
        "post_video_qc",
        "seed_effective",
        "effective_seed",
        "seed_support",
    }
    assert required <= set(meta)
    assert meta["actual_image_inputs"] == ["first.png", "end.png"]
    assert meta["route_execution_recipe_hash"]
    assert meta["post_video_qc"]["identity_qc_required"] is True
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


def test_count_formal_clips_collapses_split_relay_parts(tmp_path: Path) -> None:
    video_dir = tmp_path / "出视频" / "第1集" / "视频"
    video_dir.mkdir(parents=True)
    for name in [
        "Clip_01_开场.mp4",
        "Clip_02_接力_part1.mp4",
        "Clip_02_接力_part2.mp4",
        "Clip_03_noaudio.mp4",
    ]:
        (video_dir / name).write_bytes(b"stub")

    assert video_runner.count_formal_clips(tmp_path, "第1集") == 2


def test_silent_video_policy_strips_audio_to_formal_asset(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "出视频" / "第1集" / "视频" / "Clip_07_part1.mp4"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"raw-audio-video")
    item = {"clip": "Clip_07_part1", "target": target.name}

    monkeypatch.setattr(video_runner.shutil, "which", lambda name: f"/fake/{name}")
    monkeypatch.setattr(video_runner, "_valid_downloaded_mp4", lambda path: Path(path).is_file())
    monkeypatch.setattr(video_runner, "_video_has_audio_stream", lambda path: Path(path).name == target.name)

    class Proc:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, **_kwargs):
        Path(cmd[-1]).write_bytes(b"silent-video-only")
        return Proc()

    monkeypatch.setattr(video_runner.subprocess, "run", fake_run)

    changed = video_runner._enforce_silent_video_stream(tmp_path, "第1集", target, item, {"episode": "第1集"})

    assert changed is True
    assert target.read_bytes() == b"silent-video-only"
    assert item["audio_policy_enforced"] == "stripped_to_silent_stream"
    assert (tmp_path / "生产数据" / "video_raw_with_audio" / "第1集" / target.name).read_bytes() == b"raw-audio-video"


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


def test_accept_clip_blocks_dense_identity_without_intra_qc(monkeypatch, tmp_path: Path) -> None:
    video = tmp_path / "出视频" / "第1集" / "视频" / "Clip_01.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"mp4")
    routes = tmp_path / "出视频" / "第1集" / "prompt" / "video_model_routes.json"
    routes.parent.mkdir(parents=True)
    routes.write_text(json.dumps({
        "routes": [{
            "clip_id": "Clip_01",
            "execution_recipe": {
                "post_video_qc": {
                    "identity_qc_required": True,
                    "dense_face_watch_required": True,
                    "required_reports": ["video_qc", "temporal_consistency", "video_face_drift_watch"],
                    "acceptance_policy": "block_clear_wrong_closeup_face",
                }
            },
        }]
    }, ensure_ascii=False), encoding="utf-8")
    manifest_file = tmp_path / "manifest.json"
    video_runner.atomic_write_json(
        manifest_file,
        {
            "episode": "第1集",
            "items": [{"clip": "Clip_01", "target": "Clip_01.mp4", "status": "downloaded"}],
        },
    )

    def fake_run_qc(root, episode, clips, qc_range, **_kwargs):
        return {
            "clips": [{"has_audio": False}],
            "machine_summary": {"seam_blocks": 0, "intra_blocks": 0, "intra_checked": 0, "anchor_blocks": 0},
            "json_path": "qc.json",
            "markdown_path": "qc.md",
        }

    monkeypatch.setattr(video_runner.video_qc, "run_qc", fake_run_qc)

    with pytest.raises(RuntimeError, match="dense_face_watch"):
        video_runner.accept_clip(tmp_path, manifest_file, "Clip_01", no_record=True, no_progress=True)

    saved = video_runner.load_json(manifest_file)
    assert saved["items"][0]["status"] == "qc_blocked"


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
    monkeypatch.setattr(video_runner, "_video_has_audio_stream", lambda _path: False)

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
    monkeypatch.setattr(video_runner, "_video_has_audio_stream", lambda _path: False)

    item = video_runner.query_clip(tmp_path, manifest_file, "Clip_01")

    target = tmp_path / "出视频" / "第1集" / "视频" / "Clip_01.mp4"
    assert item["status"] == "downloaded"
    assert "context deadline exceeded" in item["query_warning"]
    assert target.exists()


def test_query_clip_recovers_existing_target_after_manifest_race(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "出视频" / "第1集" / "视频" / "Clip_01.mp4"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"existing-video" * 1024)
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

    monkeypatch.setattr(video_runner, "resolve_video_backend", fake_resolve)
    monkeypatch.setattr(video_runner.subprocess, "run", lambda *_args, **_kwargs: Proc())
    monkeypatch.setattr(video_runner, "_valid_downloaded_mp4", lambda _path: True)

    item = video_runner.query_clip(tmp_path, manifest_file, "Clip_01")

    assert item["status"] == "downloaded_existing_target"
    assert item["target_path"] == str(target)


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
