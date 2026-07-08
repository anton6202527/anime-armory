#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import array
import json
import math
import os
import tempfile
import wave

import lyric_prosody_check
import melody_chord_packet
import reference_pack
import release_pack
import rights_metadata
import song_brief
import song_workflow


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
        assert os.path.exists(os.path.join(root, "歌", "song_form.json"))


def test_rights_release_and_workflow():
    with tempfile.TemporaryDirectory() as root:
        make_project(root)
        write_wav(os.path.join(root, "歌", "song.wav"))
        write_json(os.path.join(root, "歌", "takes_manifest.json"), {
            "kind": "song_take_manifest",
            "selected_take": "take_01",
            "takes": [{"take_id": "take_01", "status": "selected", "audio_path": "歌/takes/take_01.wav"}],
        })
        write_json(os.path.join(root, "歌", "take_review.json"), {"kind": "song_take_review"})
        write_json(os.path.join(root, "混音", "master_check.json"), {"kind": "song_master_check", "passed": True})
        write_json(os.path.join(root, "合规", "ai_usage.json"), {"kind": "song_ai_usage", "audio_mode": "AI-generated", "lyrics_mode": "AI-assisted", "human_contribution": "人工改词挑版"})
        args = type("Args", (), {
            "title": "", "alternate_title": [], "rights_status": "original",
            "contributor": ["作者A|songwriter|100|ASCAP||"], "performer": ["虚拟歌手"], "producer": ["制作人A"],
            "label": "", "isrc": "USABC2500001", "iswc": "", "pro_status": "not_registered",
            "mlc_status": "not_registered", "soundexchange_status": "not_registered",
            "sample_clearance_status": "not_applicable", "cover_license_status": "not_applicable",
            "voice_authorization_status": "synthetic_or_own", "notes": "",
        })()
        rights = rights_metadata.build_metadata(root, args)
        rights_check = rights_metadata.check_metadata(rights)
        assert rights_check["passed"]
        rights_metadata.write_outputs(root, rights, rights_check)

        pack = release_pack.build_pack(root, "v1", "distribution")
        assert pack["release_ready"]
        release_pack.write_pack(root, pack)

        workflow = song_workflow.build_workflow(root)
        assert workflow["kind"] == "song_workflow"
        assert any(step["key"] == "release_pack" for step in workflow["steps"])
