#!/usr/bin/env python3
"""Static guardrails for the formal-vs-preview compose boundary."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave

import pytest


SCRIPT = Path(__file__).with_name("mv_compose.sh")


def test_fallback_can_only_write_preview() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'OUT="$ROOT/预览/fallback_preview.mp4"' in text
    assert "fallback 只产预览" in text
    assert 'if [ "$ALLOW_FALLBACK" = "1" ]; then' in text
    assert "fallback 预览完成" in text


def test_formal_compose_cannot_silently_cut_song() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "-shortest" not in text
    assert "tpad=stop_mode=clone" in text
    assert 'trim=duration=${SDUR}' in text
    assert 'python3 "$CRAFT_DIR/gate.py" "$ROOT" compose' in text


def test_internal_edit_pipeline_stays_mezzanine_until_delivery_derivative() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    before_delivery = text.split('echo "=== [4/6]', 1)[0]
    assert "prores_ks" in before_delivery
    assert "yuv422p10le" in before_delivery
    assert "libx264" not in before_delivery


def test_formal_delivery_runs_qc_then_defers_final_provenance_until_disclosure() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'delivery_qc.py" "$ROOT" "$OUT" --master "$MASTER"' in text
    assert 'provenance.py" "$ROOT" --final "$OUT" --master "$MASTER"' not in text
    assert "先生成 AI 使用披露，再生成最终 provenance" in text
    assert 'progress_set.py" "$ROOT" compose' in text


def test_compose_uses_locked_aspect_fps_and_fails_closed_for_required_subtitles() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'settings.get("合成画幅")' in text
    assert 'settings.get("字幕语言")' in text
    assert '.get("rate")' in text
    assert "正式合成不得静默交付无字幕版" in text
    assert 'color_input_manifest.py" "$ROOT"' in text


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="ffmpeg unavailable")
def test_fallback_integration_outputs_preview_only() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        video_dir = root / "出视频" / "视频"
        song_dir = root / "歌"
        video_dir.mkdir(parents=True)
        song_dir.mkdir(parents=True)
        clip = video_dir / "Clip_001.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi",
            "-i", "color=c=blue:s=320x180:r=24:d=0.25",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(clip),
        ], check=True)
        with wave.open(str(song_dir / "song.wav"), "wb") as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2)
            wav.setframerate(48000)
            wav.writeframes(b"\0\0" * 2 * 12000)
        subprocess.run([
            "bash", str(SCRIPT), str(root), "16:9", "--allow-fallback",
        ], check=True, capture_output=True, text=True)
        assert (root / "预览" / "fallback_preview.mp4").is_file()
        assert not (root / "成片_MV.mp4").exists()
        assert not (root / "成片_MV_master.mov").exists()
