#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import array
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from datetime import date, timedelta
from pathlib import Path

import lyric_prosody_check
import master_delivery
import melody_chord_packet
import reference_pack
import release_pack
import release_metadata
import rights_metadata
import song_brief
import song_workflow


_VERDICT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "release_verdict.py"
_VERDICT_SPEC = importlib.util.spec_from_file_location("song_release_verdict_test", _VERDICT_PATH)
assert _VERDICT_SPEC is not None and _VERDICT_SPEC.loader is not None
song_release_verdict = importlib.util.module_from_spec(_VERDICT_SPEC)
_VERDICT_SPEC.loader.exec_module(song_release_verdict)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write_wav(path, seconds=1.0, rate=44100):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = array.array("h")
    for i in range(int(seconds * rate)):
        value = int(12000 * math.sin(2 * math.pi * 220 * i / rate))
        data.extend([value, value])
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data.tobytes())


def make_project(root):
    write_json(os.path.join(root, "_meta.json"), {
        "title": "测试歌",
        "genre": "流行",
        "theme": "分别后重新出发",
        "target_platform": "抖音",
        "target_duration_seconds": 60,
        "key": "C",
        "bpm": "100",
        "rights_status": "original",
        "vocal_source": "synthetic",
        "author": "作者A",
    })
    write_text(os.path.join(root, "_设置.md"), "# 设置\n")
    write_text(os.path.join(root, "_进度.md"), "# 进度\n")
    write_text(os.path.join(root, "词", "lyrics.md"), """# 歌词

[verse1]
我把昨天装进行李
一个人走向晨曦

[chorus]
重新出发重新出发
风会替我回答
重新出发重新出发
把眼泪开成花
""")


def test_brief_reference_prosody_and_form_write():
    with tempfile.TemporaryDirectory() as root:
        make_project(root)
        args = type("Args", (), {
            "title": "", "use_case": "", "target_platform": "", "target_listener": "短视频流行听众",
            "core_promise": "分别后重新出发", "emotional_arc": "", "sonic_identity": "bright pop",
            "hook_deadline_seconds": 8, "reference_boundaries": "", "success_metric": ["8秒内出hook"],
        })()
        brief = song_brief.build_brief(root, args)
        check = song_brief.check_brief(brief)
        assert check["passed"]
        song_brief.write_outputs(root, brief, check)

        ref_args = type("Args", (), {"reference": ["参考歌|某歌手|https://example.test|能量曲线|不得复制旋律"], "boundary": [], "notes": ""})()
        pack = reference_pack.build_pack(root, ref_args)
        ref_check = reference_pack.check_pack(pack)
        assert ref_check["passed"]
        reference_pack.write_outputs(root, pack, ref_check)

        prosody = lyric_prosody_check.check(root)
        assert prosody["passed"]
        lyric_prosody_check.write_report(root, prosody)

        form_args = type("Args", (), {"key": "", "bpm": "", "progression": "", "verse_progression": "", "notes": ""})()
        packet = melody_chord_packet.build_packet(root, form_args)
        melody_chord_packet.write_packet(root, packet)
        assert melody_chord_packet.check_packet(packet)["passed"]
        assert "待作曲确认" in packet["sections"][0]["chord_progression"]
        assert os.path.exists(os.path.join(root, "歌", "song_form.json"))


def test_through_composed_lyrics_do_not_require_chorus():
    with tempfile.TemporaryDirectory() as root:
        make_project(root)
        meta_path = os.path.join(root, "_meta.json")
        meta = json.load(open(meta_path, encoding="utf-8"))
        meta["song_form_type"] = "through_composed"
        write_json(meta_path, meta)
        write_text(os.path.join(root, "词", "lyrics.md"), "[verse1]\n一路向北\n\n[bridge]\n不再回头\n")
        report = lyric_prosody_check.check(root)
        assert report["passed"]
        assert report["profile"]["chorus_required"] is False


def test_rights_release_and_workflow():
    with tempfile.TemporaryDirectory() as root:
        make_project(root)
        write_wav(os.path.join(root, "歌", "song.wav"))
        os.makedirs(os.path.join(root, "混音"), exist_ok=True)
        shutil.copy2(os.path.join(root, "歌", "song.wav"), os.path.join(root, "混音", "pre_master.wav"))
        write_json(os.path.join(root, "歌", "takes_manifest.json"), {
            "kind": "song_take_manifest",
            "selected_take": "take_01",
            "selection_receipt": {"song_audio_sha256": hashlib.sha256(open(os.path.join(root, "歌", "song.wav"), "rb").read()).hexdigest()},
            "takes": [{"take_id": "take_01", "status": "selected", "audio_path": "歌/takes/take_01.wav"}],
        })
        write_json(os.path.join(root, "歌", "take_review.json"), {"kind": "song_take_review"})
        write_json(os.path.join(root, "评审", "quality_gate_select.json"), {
            "kind": "song_quality_gate", "stage": "select", "take_id": "take_01",
            "passed": True, "passed_without_waiver": True,
        })
        write_json(os.path.join(root, "合规", "ai_usage.json"), {"kind": "song_ai_usage", "audio_mode": "AI-generated", "lyrics_mode": "AI-assisted", "human_contribution": "人工改词挑版"})
        args = type("Args", (), {
            "title": "", "alternate_title": [], "rights_status": "original",
            "contributor": ["作者A|songwriter|100|ASCAP||"], "performer": ["虚拟歌手"], "producer": ["制作人A"],
            "label": "", "isrc": "USABC2500001", "iswc": "", "pro_status": "not_registered",
            "version_title": "Original", "main_artist": "虚拟歌手", "duration_seconds": 1,
            "recording_type": "audio", "publication_year": 2026,
            "mlc_status": "not_registered", "soundexchange_status": "not_registered",
            "derivative_type": "original", "composition_authorization_status": "not_applicable",
            "sample_usage_status": "none", "sample_clearance_status": "not_applicable",
            "cover_license_status": "not_applicable", "voice_authorization_status": "synthetic", "notes": "",
        })()
        rights = rights_metadata.build_metadata(root, args)
        rights_check = rights_metadata.check_metadata(rights)
        assert rights_check["passed"]
        rights_metadata.write_outputs(root, rights, rights_check)

        pre_master = os.path.join(root, "混音", "pre_master.wav")
        write_json(os.path.join(root, "混音", "mix_signoff.json"), {
            "kind": "song_mix_performance_signoff", "passed": True, "reviewer": "母带工程师甲",
            "audio": {"path": "混音/pre_master.wav", "sha256": hashlib.sha256(open(pre_master, "rb").read()).hexdigest()},
        })
        release_args = type("Args", (), {
            "release_title": "测试歌", "title": "", "version_title": "Original",
            "artist": ["虚拟歌手|main_artist"], "language": "zh", "genre": "流行", "explicit": "clean",
            "release_date": (date.today() + timedelta(days=14)).isoformat(), "territory": ["worldwide"],
            "label": "Test Label", "p_line": "2026 Test Label", "c_line": "2026 作者A",
            "upc_ean": "", "cover_art": "导出/cover.jpg",
        })()
        release_meta = release_metadata.build(root, release_args)
        release_meta_check = release_metadata.check(release_meta)
        assert release_meta_check["passed"]
        release_metadata.write_outputs(root, release_meta, release_meta_check)
        os.makedirs(os.path.join(root, "导出"), exist_ok=True)
        with open(os.path.join(root, "导出", "cover.jpg"), "wb") as f:
            f.write(b"test-cover")

        master_delivery.build(root)
        master_check = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "song-review", "scripts", "master_check.py"))
        subprocess.run([sys.executable, master_check, root, "--platform", "streaming", "--write"], check=True, capture_output=True, text=True)

        pack = release_pack.build_pack(root, "v1", "distribution")
        assert pack["release_ready"]
        release_pack.write_pack(root, pack)

        workflow = song_workflow.build_workflow(root)
        assert workflow["kind"] == "song_workflow"
        assert any(step["key"] == "release_pack" for step in workflow["steps"])
        assert workflow["release_verdict"]["status"] == "ready_for_acceptance"

        accepted = song_release_verdict.accept(Path(root))
        assert accepted["complete"] is True
        assert accepted["inputs"]["cover_art"]["sha256"]
        accepted_digest = accepted["release_digest"]
        workflow = song_workflow.build_workflow(root)
        assert workflow["release_verdict"]["complete"] is True

        # Rewriting only volatile diagnostics must not manufacture a new
        # business state/hash.  The logical release-pack SHA is authoritative.
        pack_path = os.path.join(root, "导出", "release_pack.json")
        rewritten_pack = json.load(open(pack_path, encoding="utf-8"))
        rewritten_pack["generated_at"] = "2099-01-01T00:00:00+00:00"
        rewritten_pack["project_root"] = "/different/checkout/same-project"
        write_json(pack_path, rewritten_pack)
        clock_only = song_release_verdict.build_verdict(Path(root))
        assert clock_only["complete"] is True
        assert clock_only["release_digest"] == accepted_digest
        assert clock_only["inputs"]["release_pack"]["logical_sha256"]

        with open(os.path.join(root, "导出", "master.wav"), "ab") as f:
            f.write(b"changed-current-master")
        stale = song_release_verdict.build_verdict(Path(root))
        assert stale["complete"] is False
        assert stale["release_digest"] != accepted_digest
        assert stale["acceptance"]["current"] is False
