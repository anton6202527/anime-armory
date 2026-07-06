from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("preventive_contracts.py")
spec = importlib.util.spec_from_file_location("preventive_contracts", SCRIPT)
preventive_contracts = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(preventive_contracts)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _write_bytes(path: Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return preventive_contracts.sha256_file(path)


def _storyboard(root: Path, episode: str = "第1集") -> None:
    _write_json(root / "脚本" / episode / "storyboard.json", {
        "kind": "n2d_storyboard",
        "version": 1,
        "clips": [{
            "clip_id": "Clip_01",
            "description": "CHAR_A 握住 PROP_SWORD 与 CHAR_B 近距离对峙，并说出台词。",
            "character_ids": ["CHAR_A", "CHAR_B"],
            "prop_ids": ["PROP_SWORD"],
            "dialogue_indices": [1],
            "dramatic_function": "兑现本集承诺并抬高阻碍",
            "editing_intent": "用近景反打切到集尾钩",
        }],
    })


def _confirmed_contract(root: Path, episode: str = "第1集") -> None:
    char_a_hash = _write_bytes(root / "出图" / "共享" / "CHAR_A_front.png", b"char a")
    char_b_hash = _write_bytes(root / "出图" / "共享" / "CHAR_B_front.png", b"char b")
    sword_hash = _write_bytes(root / "出图" / "共享" / "PROP_SWORD_front.png", b"sword")
    _write_json(root / "脚本" / episode / "preventive_contracts.json", {
        "kind": "n2d_preventive_contracts",
        "version": 1,
        "episode": episode,
        "status": "confirmed",
        "episode_promise": {
            "opening_hook": "她发现令牌失踪。",
            "promise": "本集承诺找出内鬼。",
            "obstacle": "同伴阻拦且敌人逼近。",
            "payoff_or_progress": "确认令牌在 CHAR_B 手里。",
            "cliffhanger": "CHAR_B 举剑指向她。",
        },
        "shots": [{
            "clip_id": "Clip_01",
            "dramatic_function": "兑现本集承诺并抬高阻碍",
            "editing_intent": "用近景反打切到集尾钩",
        }],
        "reference_slots": {
            "characters": [
                {"id": "CHAR_A", "reference_slots": [{"slot": "front", "path": "出图/共享/CHAR_A_front.png", "sha256": char_a_hash}], "identity_strategy": "same-source multi-view lock"},
                {"id": "CHAR_B", "reference_slots": [{"slot": "front", "path": "出图/共享/CHAR_B_front.png", "sha256": char_b_hash}], "identity_strategy": "same-source multi-view lock"},
            ],
            "assets": [
                {"id": "PROP_SWORD", "reference_slots": [{"slot": "front", "path": "出图/共享/PROP_SWORD_front.png", "sha256": sword_hash}], "lock_strategy": "shape constraints"},
            ],
            "scenes": [],
        },
        "interaction_physics": [{
            "clip_id": "Clip_01",
            "action_decomposition": ["CHAR_A 抬手", "CHAR_A 握住剑柄", "CHAR_B 后撤"],
            "contact_points": ["CHAR_A right hand -> PROP_SWORD hilt"],
            "screen_positions": ["CHAR_A left foreground", "CHAR_B right midground"],
            "degrade_plan": "拆成手部特写 + 反打",
        }],
        "audio_timing": {
            "mode": "先出视频后配音",
            "post_dub": {"fit_strategy": "fit voice to locked clip duration", "overflow_policy": "overflow returns to video"},
            "native_av_policy": {"lipsync_policy": "none", "subtitle_policy": "compose overlay", "voice_identity_policy": "n2d-voice"},
            "dialogue_closeups": [{
                "clip_id": "Clip_01",
                "timing_source": "voiceover index 1 estimated slot",
                "mouth_policy": "mouth visible but final lipsync in compose",
                "subtitle_policy": "compose overlay",
                "voice_or_native_policy": "post_dub voice",
            }],
        },
    })


def test_episode_promise_gate_scaffolds_and_blocks_draft(tmp_path: Path) -> None:
    report = preventive_contracts.build_report(tmp_path, "第1集", stage="script_stage2", write_missing=True)

    assert report["status"] == "blocked"
    assert report["scaffolded"] is True
    assert (tmp_path / "脚本" / "第1集" / "preventive_contracts.json").is_file()
    assert any(f["gate"] == "episode_promise_gate" for f in report["findings"])


def test_reference_scaffold_derives_slots_from_registries(tmp_path: Path) -> None:
    _storyboard(tmp_path)
    char_hash = _write_bytes(tmp_path / "出图" / "共享" / "CHAR_A_front.png", b"char a")
    char_b_hash = _write_bytes(tmp_path / "出图" / "共享" / "CHAR_B_front.png", b"char b")
    sword_hash = _write_bytes(tmp_path / "出图" / "共享" / "PROP_SWORD_front.png", b"sword")
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", {
        "characters": [
            {
                "id": "CHAR_A",
                "forms": [{
                    "form": "常态",
                    "reference_group": {"front": {"path": "出图/共享/CHAR_A_front.png", "status": "ready"}},
                    "identity_adapters": {"image": {"codex": {"mode": "reference_group"}}},
                }],
            },
            {
                "id": "CHAR_B",
                "forms": [{
                    "form": "常态",
                    "reference_group": {"front": {"path": "出图/共享/CHAR_B_front.png", "status": "ready"}},
                    "identity_adapters": {"image": {"codex": {"mode": "reference_group"}}},
                }],
            },
        ],
    })
    _write_json(tmp_path / "出图" / "共享" / "asset_registry.json", {
        "assets": [{
            "id": "PROP_SWORD",
            "type": "prop",
            "reference_group": {"primary": {"path": "出图/共享/PROP_SWORD_front.png", "status": "ready"}},
            "constraints": {"structure": "single straight sword"},
        }],
    })

    report = preventive_contracts.build_report(tmp_path, "第1集", stage="image", write_missing=True)
    contract_path = tmp_path / "脚本" / "第1集" / "preventive_contracts.json"
    data = json.loads(contract_path.read_text(encoding="utf-8"))

    assert report["status"] == "blocked"
    char = next(row for row in data["reference_slots"]["characters"] if row["id"] == "CHAR_A")
    char_b = next(row for row in data["reference_slots"]["characters"] if row["id"] == "CHAR_B")
    asset = next(row for row in data["reference_slots"]["assets"] if row["id"] == "PROP_SWORD")
    assert char["reference_slots"][0]["sha256"] == char_hash
    assert char_b["reference_slots"][0]["sha256"] == char_b_hash
    assert asset["reference_slots"][0]["sha256"] == sword_hash
    assert char["identity_strategy"]
    assert asset["lock_strategy"]

    data["status"] = "confirmed"
    _write_json(contract_path, data)
    confirmed = preventive_contracts.build_report(tmp_path, "第1集", stage="image")

    assert confirmed["status"] == "pass"


def test_reference_gate_uses_registry_when_confirmed_contract_rows_have_empty_slots(tmp_path: Path) -> None:
    _write_json(tmp_path / "脚本" / "第1集" / "storyboard.json", {
        "clips": [{
            "clip_id": "Clip_01",
            "description": "CHAR_A 站在 PROP_SWORD 旁。",
            "character_ids": ["CHAR_A"],
            "prop_ids": ["PROP_SWORD"],
        }],
    })
    char_hash = _write_bytes(tmp_path / "出图" / "共享" / "CHAR_A_front.png", b"char a")
    sword_hash = _write_bytes(tmp_path / "出图" / "共享" / "PROP_SWORD_front.png", b"sword")
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", {
        "characters": [{
            "id": "CHAR_A",
            "forms": [{
                "form": "常态",
                "reference_group": {"front": {"path": "出图/共享/CHAR_A_front.png", "sha256": char_hash}},
                "identity_adapters": {"image": {"codex": {"mode": "reference_group"}}},
            }],
        }],
    })
    _write_json(tmp_path / "出图" / "共享" / "asset_registry.json", {
        "assets": [{
            "id": "PROP_SWORD",
            "type": "prop",
            "reference_group": {"primary": {"path": "出图/共享/PROP_SWORD_front.png", "sha256": sword_hash}},
            "constraints": {"structure": "single straight sword"},
        }],
    })
    _write_json(tmp_path / "脚本" / "第1集" / "preventive_contracts.json", {
        "kind": "n2d_preventive_contracts",
        "version": 1,
        "episode": "第1集",
        "status": "confirmed",
        "reference_slots": {
            "characters": [{"id": "CHAR_A", "reference_slots": [], "identity_strategy": ""}],
            "assets": [{"id": "PROP_SWORD", "reference_slots": [], "lock_strategy": ""}],
            "scenes": [],
        },
    })

    report = preventive_contracts.build_report(tmp_path, "第1集", stage="image")

    assert report["status"] == "pass"


def test_reference_gate_resolves_slash_form_ids_from_registry(tmp_path: Path) -> None:
    _write_json(tmp_path / "脚本" / "第1集" / "storyboard.json", {
        "clips": [{
            "clip_id": "Clip_01",
            "description": "CHAR_A/战损态 先倒地，随后 CHAR_A/觉醒态 睁眼。",
            "character_ids": ["CHAR_A/战损态", "CHAR_A/觉醒态"],
        }],
    })
    char_hash = _write_bytes(tmp_path / "出图" / "共享" / "CHAR_A_front.png", b"char a")
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", {
        "characters": [{
            "id": "CHAR_A",
            "forms": [{
                "form": "战损态",
                "reference_group": {"front": {"path": "出图/共享/CHAR_A_front.png", "sha256": char_hash}},
                "identity_adapters": {"image": {"codex": {"mode": "reference_group"}}},
            }],
        }],
    })
    _write_json(tmp_path / "出图" / "共享" / "asset_registry.json", {"assets": []})
    _write_json(tmp_path / "脚本" / "第1集" / "preventive_contracts.json", {
        "kind": "n2d_preventive_contracts",
        "version": 1,
        "episode": "第1集",
        "status": "confirmed",
        "reference_slots": {"characters": [], "assets": [], "scenes": []},
    })

    report = preventive_contracts.build_report(tmp_path, "第1集", stage="image")

    assert report["status"] == "pass"


def test_confirmed_reference_slots_allow_double_underscore_asset_names(tmp_path: Path) -> None:
    _storyboard(tmp_path)
    char_hash = _write_bytes(tmp_path / "出图" / "共享" / "定妆_CHAR_A__常态_正面.png", b"char a")
    char_b_hash = _write_bytes(tmp_path / "出图" / "共享" / "定妆_CHAR_B__常态_正面.png", b"char b")
    sword_hash = _write_bytes(tmp_path / "出图" / "共享" / "PROP_SWORD_front.png", b"sword")
    _write_json(tmp_path / "脚本" / "第1集" / "preventive_contracts.json", {
        "kind": "n2d_preventive_contracts",
        "version": 1,
        "episode": "第1集",
        "status": "confirmed",
        "reference_slots": {
            "characters": [
                {"id": "CHAR_A", "reference_slots": [{"slot": "front", "path": "出图/共享/定妆_CHAR_A__常态_正面.png", "sha256": char_hash}], "identity_strategy": "same-source lock"},
                {"id": "CHAR_B", "reference_slots": [{"slot": "front", "path": "出图/共享/定妆_CHAR_B__常态_正面.png", "sha256": char_b_hash}], "identity_strategy": "same-source lock"},
            ],
            "assets": [
                {"id": "PROP_SWORD", "reference_slots": [{"slot": "front", "path": "出图/共享/PROP_SWORD_front.png", "sha256": sword_hash}], "lock_strategy": "shape constraints"},
            ],
            "scenes": [],
        },
    })

    report = preventive_contracts.build_report(tmp_path, "第1集", stage="image")

    assert report["status"] == "pass"


def test_shot_intent_gate_blocks_missing_clip_intent(tmp_path: Path) -> None:
    _write_json(tmp_path / "脚本" / "第1集" / "storyboard.json", {
        "clips": [{"clip_id": "Clip_01", "description": "她推门。"}],
    })
    _write_json(tmp_path / "脚本" / "第1集" / "preventive_contracts.json", {
        "kind": "n2d_preventive_contracts",
        "version": 1,
        "episode": "第1集",
        "status": "confirmed",
        "shots": [{"clip_id": "Clip_01"}],
    })
    report = preventive_contracts.build_report(tmp_path, "第1集", stage="image_prompt")

    assert report["status"] == "blocked"
    assert "shot_intent_gate" in {f["gate"] for f in report["findings"]}


def test_shot_intent_gate_accepts_ep_clip_ids_and_legacy_edit_intent(tmp_path: Path) -> None:
    _write_json(tmp_path / "脚本" / "第3集" / "storyboard.json", {
        "clips": [{
            "id": "EP03_CLIP01",
            "description": "她站在月色荒野。",
        }],
    })
    contract = {
        "status": "confirmed",
        "shots": [{
            "clip_id": "EP03_CLIP01",
            "dramatic_function": "承接上一集尾声并抬出欠命账",
            "edit_intent": "先读环境再切手部动作，形成冷开压力",
        }],
    }
    findings: list[dict] = []

    preventive_contracts.check_shot_intent(tmp_path, "第3集", contract, findings)

    assert findings == []


def test_reference_physics_and_audio_gates_pass_with_confirmed_contract(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("- 制作模式: 先出视频后配音\n", encoding="utf-8")
    _storyboard(tmp_path)
    _confirmed_contract(tmp_path)

    image = preventive_contracts.build_report(tmp_path, "第1集", stage="image")
    video = preventive_contracts.build_report(tmp_path, "第1集", stage="video_prompt")
    compose = preventive_contracts.build_report(tmp_path, "第1集", stage="compose")

    assert image["status"] == "pass"
    assert video["status"] == "pass"
    assert compose["status"] == "pass"


def test_write_missing_enriches_empty_confirmed_video_contract_from_storyboard(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text(
        "- 制作模式: 先出视频后配音\n"
        "- 视频生成音频策略: 无声视频流\n"
        "- 对口型: 关闭\n"
        "- 视频原生音轨: 丢弃\n",
        encoding="utf-8",
    )
    _write_json(tmp_path / "脚本" / "第1集" / "storyboard.json", {
        "kind": "n2d_storyboard",
        "version": 1,
        "clips": [{
            "clip_id": "Clip_01",
            "duration": 6.2,
            "description": "CHAR_A 握住 PROP_SWORD 与 CHAR_B 近距离对峙，并说出台词。",
            "character_ids": ["CHAR_A", "CHAR_B"],
            "prop_ids": ["PROP_SWORD"],
            "dialogue_indices": [1],
            "voiceover_indices": [1],
            "continuity": {
                "start_state": "CHAR_A 抬手逼近。",
                "end_state": "CHAR_B 后撤半步。",
                "entry_exit": "CHAR_A 画左入画，CHAR_B 画右后撤。",
            },
            "character_slots": [
                {"character_id": "CHAR_A", "screen_position": "画左前景"},
                {"character_id": "CHAR_B", "screen_position": "画右中景"},
            ],
            "template_contract": {
                "template_id": "duel_contact",
                "beats": ["CHAR_A 抬手", "握住剑柄", "CHAR_B 后撤"],
                "blocking": "CHAR_A 画左前景，CHAR_B 画右中景。",
                "contact_points": ["CHAR_A right hand -> PROP_SWORD hilt"],
                "vfx_asset": "VFX_剑气",
                "effect_cause": "握剑动作触发剑气亮起。",
                "degrade_plan": "拆为手部特写 + CHAR_B 反打。",
            },
        }],
    })
    _write_json(tmp_path / "脚本" / "第1集" / "preventive_contracts.json", {
        "kind": "n2d_preventive_contracts",
        "version": 1,
        "episode": "第1集",
        "status": "confirmed",
        "interaction_physics": [{
            "clip_id": "Clip_01",
            "action_decomposition": [],
            "contact_points": [],
            "screen_positions": [],
            "vfx_layers": [],
            "degrade_plan": "",
        }],
        "audio_timing": {
            "mode": "先出视频后配音",
            "post_dub": {"fit_strategy": "", "overflow_policy": ""},
            "native_av_policy": {"lipsync_policy": "", "subtitle_policy": "", "voice_identity_policy": ""},
            "dialogue_closeups": [{
                "clip_id": "Clip_01",
                "timing_source": "",
                "mouth_policy": "",
                "subtitle_policy": "",
                "voice_or_native_policy": "",
            }],
        },
    })

    report = preventive_contracts.build_report(tmp_path, "第1集", stage="video_prompt", write_missing=True)
    data = json.loads((tmp_path / "脚本" / "第1集" / "preventive_contracts.json").read_text(encoding="utf-8"))
    row = data["interaction_physics"][0]
    audio_row = data["audio_timing"]["dialogue_closeups"][0]

    assert report["status"] == "pass"
    assert row["action_decomposition"]
    assert row["contact_points"] == ["CHAR_A right hand -> PROP_SWORD hilt"]
    assert row["screen_positions"]
    assert row["vfx_layers"]
    assert row["degrade_plan"] == "拆为手部特写 + CHAR_B 反打。"
    assert "无声视频流" in audio_row["mouth_policy"]
    assert "no_native_speech" in audio_row["mouth_policy"]
    assert "compose_overlay_only" in audio_row["subtitle_policy"]
    assert data["audio_timing"]["post_dub"]["fit_strategy"]


def test_single_present_character_with_offscreen_state_does_not_need_screen_positions(tmp_path: Path) -> None:
    _write_json(tmp_path / "脚本" / "第1集" / "storyboard.json", {
        "clips": [{
            "id": "Clip_01",
            "label": "搜物求生",
            "character_ids": ["CHAR_A"],
            "scene": "CHAR_A 拿起水囊，CHAR_B 只在画外记忆中。",
            "entity_schedule": {
                "characters": ["CHAR_A"],
                "required_presence": ["CHAR_A"],
                "offscreen_presence": ["CHAR_B"],
                "knowledge_state": {"CHAR_B": ["未在场"]},
            },
        }],
    })
    clip = json.loads((tmp_path / "脚本" / "第1集" / "storyboard.json").read_text(encoding="utf-8"))["clips"][0]
    contract = {
        "kind": "n2d_preventive_contracts",
        "version": 1,
        "episode": "第1集",
        "status": "confirmed",
        "interaction_physics": [{
            "clip_id": "Clip_01",
            "action_decomposition": ["CHAR_A 拿起水囊"],
            "degrade_plan": "动作不稳时拆为手部特写。",
        }],
    }
    findings = []

    preventive_contracts.check_interaction_physics(tmp_path, "第1集", contract, findings)

    assert preventive_contracts.chars_from_clip(clip) == ["CHAR_A"]
    assert not findings


def test_pilot_release_gate_blocks_first_episode_without_acceptance(tmp_path: Path) -> None:
    report = preventive_contracts.build_report(tmp_path, "第1集", stage="review")

    assert report["status"] == "blocked"
    assert report["findings"][0]["gate"] == "pilot_release_gate"


def test_reference_gate_blocks_semantic_slots_without_artifacts(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("- 制作模式: 先出视频后配音\n", encoding="utf-8")
    _storyboard(tmp_path)
    _confirmed_contract(tmp_path)
    path = tmp_path / "脚本" / "第1集" / "preventive_contracts.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["reference_slots"]["characters"][0]["reference_slots"] = ["front", "side"]
    _write_json(path, data)

    report = preventive_contracts.build_report(tmp_path, "第1集", stage="image")

    assert report["status"] == "blocked"
    assert any("真实产物" in f["message"] for f in report["findings"])


def test_confirmed_reference_slots_allow_double_underscore_asset_names(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("- 制作模式: 先出视频后配音\n", encoding="utf-8")
    _write_json(tmp_path / "脚本" / "第1集" / "storyboard.json", {
        "clips": [{"clip_id": "Clip_01", "character_ids": ["CHAR_A"]}],
    })
    asset = tmp_path / "出图" / "共享" / "图片" / "定妆_CHAR_A__常态_脸部特写.png"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"png-a")
    _write_json(tmp_path / "脚本" / "第1集" / "preventive_contracts.json", {
        "kind": "n2d_preventive_contracts",
        "version": 1,
        "episode": "第1集",
        "status": "confirmed",
        "reference_slots": {
            "characters": [{
                "id": "CHAR_A",
                "reference_slots": [{"slot": "face", "path": "出图/共享/图片/定妆_CHAR_A__常态_脸部特写.png", "sha256": preventive_contracts.sha256_file(asset)}],
                "identity_strategy": {"mode": "reference_group"},
            }],
            "assets": [],
        },
    })

    report = preventive_contracts.build_report(tmp_path, "第1集", stage="image")

    assert report["status"] == "pass"


def test_asset_id_parser_ignores_generic_vfx_only_prose() -> None:
    ids = preventive_contracts.asset_ids_from_clip({
        "clip_id": "Clip_01",
        "object_ids": ["VFX_虎山神摹影"],
        "notes": "Defines VFX-only contact so the model does not invent hand wrestling.",
    })

    assert "VFX_虎山神摹影" in ids
    assert "VFX_only" not in ids


def test_pilot_release_gate_requires_evidence_manifest(tmp_path: Path) -> None:
    _write_json(tmp_path / "生产数据" / "pilot_acceptance_第1集.json", {
        "status": "accepted",
        "reviewer": "human-qc",
        "risk_selection": {"method": "风险排序"},
        "clips": [{"clip_id": "Clip_01"}, {"clip_id": "Clip_02"}],
        "coverage": ["face", "scene", "action", "lipsync", "seam", "routing"],
        "checks": {"face": "pass", "scene": "pass", "action": "pass", "lipsync": "pass", "seam": "pass", "routing": "pass"},
    })

    report = preventive_contracts.build_report(tmp_path, "第1集", stage="review")

    assert report["status"] == "blocked"
    assert any("artifact_path" in f["message"] for f in report["findings"])
