from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import media_artifact


HERE = Path(__file__).resolve().parent


def _run(args: list[str], *, timeout: int = 60) -> None:
    proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    assert proc.returncode == 0, proc.stderr


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="real media smoke requires ffmpeg and ffprobe",
)
def test_compose_shell_promotes_real_tiny_media_with_current_receipt(tmp_path: Path) -> None:
    """Exercise the shell path, full decode QC and atomic promotion with real media."""
    episode = "第1集"
    video_dir = tmp_path / "出视频" / episode / "视频"
    script_dir = tmp_path / "脚本" / episode
    compose_dir = tmp_path / "合成" / episode
    video_dir.mkdir(parents=True)
    script_dir.mkdir(parents=True)
    compose_dir.mkdir(parents=True)

    source = video_dir / "Clip_01.mp4"
    _run([
        "ffmpeg", "-nostdin", "-y", "-v", "error",
        "-f", "lavfi", "-i", "testsrc2=s=160x90:r=24:d=1.2",
        "-an", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709:range=limited",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-color_range", "tv", "-movflags", "+faststart", str(source),
    ])
    bgm = tmp_path / "licensed_test_bgm.wav"
    _run([
        "ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "lavfi", "-i",
        "sine=frequency=440:sample_rate=48000:duration=2", "-ar", "48000", "-ac", "2", str(bgm),
    ])

    (tmp_path / "_设置.md").write_text(
        "- BGM来源: 本地授权\n- 视频原生音轨: 丢弃\n- AI显式角标: 关闭\n",
        encoding="utf-8",
    )
    (script_dir / "storyboard.json").write_text(json.dumps({
        "episode": episode,
        "clips": [{
            "id": "Clip_01",
            "duration": 1.0,
            "speed_mode": "trim",
            "video_out": source.relative_to(tmp_path).as_posix(),
        }],
    }, ensure_ascii=False), encoding="utf-8")
    (compose_dir / "bgm_contract.json").write_text(json.dumps({
        "kind": "n2d_bgm_contract",
        "version": 1,
        "episode": episode,
        "status": "confirmed",
        "strategy": "licensed_file",
        "source": {
            "file": bgm.relative_to(tmp_path).as_posix(),
            "model": "",
            "channel": "local-test",
            "license_or_rights_ref": "test fixture generated in-process",
        },
        "cues": [{"id": "BGM_01", "intent": "steady test tone", "start_sec": 0, "end_sec": 1}],
        "mix": {"ducking": True, "tension_envelope": False, "target_gain_db": -12},
    }, ensure_ascii=False), encoding="utf-8")

    env = os.environ.copy()
    env.update({
        "MASTER_WIDTH": "160",
        "MASTER_HEIGHT": "90",
        "MASTER_FPS": "24",
        "VIDEO_PRESET": "ultrafast",
        "VIDEO_CRF": "30",
        "J_CUT_SEC": "0",
        "N2D_AI_LABEL_MODE": "关闭",
        "N2D_UPDATE_PROGRESS": "0",
    })
    proc = subprocess.run(
        ["bash", str(HERE / "compose.sh"), str(tmp_path), episode, "zh"],
        cwd=HERE,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"

    master = compose_dir / f"成片_{episode}_zh.mp4"
    current = media_artifact.current_receipt(tmp_path, episode, master)
    assert current["status"] == "pass", current
    assert not (compose_dir / ".render.lock").exists()
    timeline = json.loads(
        (tmp_path / "生产数据" / f"final_timeline_probe_{episode}.json").read_text(encoding="utf-8")
    )
    assert timeline["status"] == "pass", timeline
    assert timeline["version"] == 2
    assert timeline["segments"][0]["source_sha256"] == media_artifact.sha256_file(source)
