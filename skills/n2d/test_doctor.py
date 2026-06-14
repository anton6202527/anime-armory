"""doctor 纯逻辑单测（无需 insightface/ffmpeg）。
cd skills/n2d && python -m pytest test_doctor.py
"""
import doctor


def test_face_qc_precision_full():
    assert doctor.face_qc_precision({"insightface": True, "onnxruntime": True}) == "full"


def test_face_qc_precision_degraded_pillow_or_cv2():
    assert doctor.face_qc_precision({"insightface": False, "PIL": True}) == "degraded"
    assert doctor.face_qc_precision({"cv2": True}) == "degraded"
    # insightface 单缺 onnxruntime → 仍降级（不是 full）
    assert doctor.face_qc_precision({"insightface": True, "onnxruntime": False, "PIL": True}) == "degraded"


def test_face_qc_precision_none():
    assert doctor.face_qc_precision({}) == "none"
    assert doctor.face_qc_precision({"insightface": False, "onnxruntime": False}) == "none"


def test_precision_lines_flags_degraded_face_and_say_only():
    probes = {
        "libs": {"insightface": False, "onnxruntime": False, "cv2": False, "PIL": True},
        "cli": {"ffmpeg": True, "ffprobe": True, "say": True},
        "voice": {"say": True, "heavy_env": False},
        "image_backend": {"name": "Codex", "status": "down", "detail": "HTTP 502"},
        "video_backend": {"name": "Seedance 2.0", "mode": "first_last", "max_frames": 2, "verified": "doc"},
    }
    lines = "\n".join(doctor.precision_lines(probes))
    assert "近景" in lines and "人审" in lines          # 降级 → 近景转人审
    assert "重配真音色" in lines                          # say 占位提醒
    assert "Codex" in lines and "down" in lines          # 后端 down 浮现
    assert "禁止静默兜底换后端" in lines


def test_precision_lines_full_path_clean():
    probes = {
        "libs": {"insightface": True, "onnxruntime": True, "PIL": True},
        "cli": {"ffmpeg": True, "ffprobe": True, "say": True},
        "voice": {"say": True, "heavy_env": True},
        "image_backend": {"name": "Codex", "status": "ok", "detail": ""},
        "video_backend": None,
    }
    lines = "\n".join(doctor.precision_lines(probes))
    assert "full 精度" in lines
    assert "正式配音" in lines
