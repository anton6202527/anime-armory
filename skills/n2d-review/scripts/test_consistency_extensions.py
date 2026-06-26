import json

import audio_space_consistency as asc
import consistency_dependency_graph as cdg
import expression_state_consistency as esc
import intentional_discontinuity as dis
import motion_grammar_consistency as mgc


def test_dependency_graph_tracks_entity_to_final_media(tmp_path):
    ep = "第1集"
    (tmp_path / "脚本" / ep).mkdir(parents=True)
    (tmp_path / "出图" / "共享").mkdir(parents=True)
    (tmp_path / "出图" / ep / "图片").mkdir(parents=True)
    (tmp_path / "出视频" / ep / "prompt").mkdir(parents=True)
    (tmp_path / "出视频" / ep / "视频").mkdir(parents=True)
    (tmp_path / "合成" / ep).mkdir(parents=True)
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({
        "characters": [{"id": "CHAR_01", "name": "沈念"}]
    }, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "脚本" / ep / "storyboard.json").write_text(json.dumps({
        "clips": [{"id": "Clip 1", "character_ids": ["CHAR_01"], "template": "dialogue_closeup"}]
    }, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "出视频" / ep / "prompt" / "video_model_routes.json").write_text(json.dumps({
        "routes": [{"clip_id": "Clip_01", "primary_backend": "kling", "fallback_backends": ["seedance"]}]
    }, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "出图" / ep / "图片" / "Clip_01.png").write_bytes(b"x")
    (tmp_path / "出视频" / ep / "视频" / "Clip_01.mp4").write_bytes(b"x")
    (tmp_path / "合成" / ep / f"成片_{ep}_zh.mp4").write_bytes(b"x")

    graph = cdg.build_graph(tmp_path, ep, changed=["CHAR_01"])

    assert graph["summary"]["clips"] == 1
    assert "clip:Clip_01" in graph["impact_plan"]["impacted_nodes"]
    assert any(n.startswith("final:") for n in graph["impact_plan"]["impacted_media"])


def test_intentional_discontinuity_signoff_annotates_matching_finding():
    manifest = {
        "kind": "n2d_intentional_discontinuity_manifest",
        "accepted": [{
            "clip_id": "Clip_03",
            "dimension": "轴线视线(X1)",
            "reason": "梦境闪回用反轴制造错位感",
            "signoff": "reviewer",
        }],
    }
    findings = [{"severity": "block", "loc": "Clip_03", "dimension": "轴线视线(X1)", "message": "反轴"}]

    audit = dis.validate_manifest(manifest)
    annotated = dis.annotate_findings(findings, manifest)

    assert audit["status"] == "pass"
    assert annotated[0]["intentional_discontinuity_signed_off"] is True
    assert annotated[0]["severity"] == "info"


def test_motion_grammar_checks_route_contract():
    report = mgc.check_routes(
        [{"clip_id": "Clip_01", "shot_type": "fight_exchange", "primary_backend": "dreamina", "risk_flags": []}],
        {"shot_types": {"fight_exchange": {"allowed_backends": ["kling"], "required_risk_flags": ["high_speed_motion"]}}},
    )

    assert report["counts"]["warn"] == 2
    assert all(f["dimension"] == "运动语法(MG1)" for f in report["findings"])


def test_audio_space_requires_native_voice_evidence():
    report = asc.check(
        [{"clip_id": "Clip_01", "native_audio_policy": "native_speech"}],
        {},
        {},
    )

    assert report["counts"]["warn"] == 1
    assert report["findings"][0]["dimension"] == "原生声纹(NV1)"


def test_expression_state_blocks_identity_invariant_delta():
    storyboard = {
        "clips": [{
            "id": "Clip_01",
            "character_ids": ["CHAR_01"],
            "continuity": {"state_delta": {"face_shape": "changed"}},
        }]
    }
    characters = {"CHAR_01": {"identity_invariants": ["face_shape"], "allowed_state_deltas": []}}

    report = esc.check_storyboard(storyboard, characters)

    assert report["status"] == "blocked"
    assert report["findings"][0]["dimension"] == "状态化表情(EXP2)"
