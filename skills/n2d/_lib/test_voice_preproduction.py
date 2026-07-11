from __future__ import annotations

import json
from pathlib import Path

import voice_preproduction as vp


def _voiceover(root: Path) -> None:
    path = root / "脚本" / "第1集" / "voiceover.txt"
    path.parent.mkdir(parents=True)
    path.write_text(
        "[镜头1·旁白·克制] 夜色压下来。\n"
        "[镜头2·沈念·迟疑] 你真的看见了吗？\n",
        encoding="utf-8",
    )


def test_timing_estimate_creates_no_audio_contract(tmp_path: Path) -> None:
    _voiceover(tmp_path)
    payload = vp.build_timing_estimate(tmp_path, "1")
    assert payload["kind"] == vp.TIMING_KIND
    assert payload["audio_generated"] is False
    assert len(payload["lines"]) == 2
    assert all(row["audio_path"] == "" and row["时长"] > 0 for row in payload["lines"])
    assert payload["lines"][0]["line_type"] == "narration_or_offscreen"
    assert payload["lines"][1]["line_type"] == "character_dialogue"


def test_prepare_writes_casting_and_timing_without_wav(tmp_path: Path) -> None:
    _voiceover(tmp_path)
    result = vp.write_preproduction(tmp_path, "第1集")
    assert (tmp_path / result["outputs"]["casting"]).is_file()
    assert (tmp_path / result["outputs"]["timing"]).is_file()
    assert not list(tmp_path.rglob("*.wav"))
    assert result["casting"]["summary"]["pending_count"] == 2


def test_final_casting_requires_lock_identity_and_sample(tmp_path: Path) -> None:
    _voiceover(tmp_path)
    vp.write_preproduction(tmp_path, "第1集")
    casting = json.loads(vp.casting_path(tmp_path).read_text(encoding="utf-8"))
    blockers = vp.casting_blockers(casting, ["沈念"], purpose="final")
    assert any("status" in item for item in blockers)
    assert any("canonical_sample" in item for item in blockers)

    vp.lock_role(
        tmp_path, "沈念", backend="MiniMax", voice_id="synthetic_voice_01",
        approved_by="director:demo", canonical_sample="设定库/voices/沈念.wav",
    )
    casting = json.loads(vp.casting_path(tmp_path).read_text(encoding="utf-8"))
    assert vp.casting_blockers(casting, ["沈念"], purpose="final") == []


def test_clone_voice_lock_requires_authorization(tmp_path: Path) -> None:
    _voiceover(tmp_path)
    vp.write_preproduction(tmp_path, "第1集")
    vp.lock_role(
        tmp_path, "沈念", backend="CosyVoice zero-shot", voice_id="shen",
        approved_by="director:demo", canonical_sample="设定库/voices/沈念.wav",
        authorization="pending",
    )
    casting = json.loads(vp.casting_path(tmp_path).read_text(encoding="utf-8"))
    assert any("authorization" in item for item in vp.casting_blockers(casting, ["沈念"]))


def test_preparing_later_episode_preserves_existing_cast_roles(tmp_path: Path) -> None:
    _voiceover(tmp_path)
    vp.write_preproduction(tmp_path, "第1集")
    vp.lock_role(
        tmp_path, "沈念", backend="MiniMax", voice_id="synthetic_voice_01",
        approved_by="director:demo", canonical_sample="设定库/voices/沈念.wav",
    )
    second = tmp_path / "脚本" / "第2集" / "voiceover.txt"
    second.parent.mkdir(parents=True)
    second.write_text("[镜头1·新角色·镇定] 轮到我了。\n", encoding="utf-8")

    vp.write_preproduction(tmp_path, "第2集")
    casting = json.loads(vp.casting_path(tmp_path).read_text(encoding="utf-8"))
    roles = {row["role"]: row for row in casting["roles"]}

    assert set(roles) == {"旁白", "沈念", "新角色"}
    assert roles["沈念"]["status"] == "locked"
    assert roles["沈念"]["voice_id"] == "synthetic_voice_01"
    assert roles["沈念"]["episodes"] == ["第1集"]
    assert roles["新角色"]["episodes"] == ["第2集"]
