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


def test_precision_lines_reports_deferred_video_backend():
    probes = {
        "libs": {"insightface": True, "onnxruntime": True, "PIL": True},
        "cli": {"ffmpeg": True, "ffprobe": True},
        "voice": {"say": True, "heavy_env": True},
        "image_backend": None,
        "video_backend": {"deferred": True, "route": "自动按镜头路由"},
    }
    lines = "\n".join(doctor.precision_lines(probes))
    assert "生视频后端：未固定" in lines
    assert "后移到 n2d-video" in lines


def test_precision_lines_flags_stylized_styleid_degraded():
    probes = {
        "libs": {"insightface": True, "onnxruntime": True, "PIL": True},
        "cli": {"ffmpeg": True, "ffprobe": True},
        "voice": {"say": True, "heavy_env": True},
        "image_backend": None,
        "video_backend": None,
        "face_encoder": {
            "style": "二次元赛璐璐",
            "stylized": True,
            "encoder": "arcface",
            "status": "degraded",
            "model_status": "missing",
            "model_path": "",
        },
    }
    lines = "\n".join(doctor.precision_lines(probes))
    assert "N2D_STYLEID_MODEL" in lines
    assert "降级档" in lines


def test_probe_face_encoder_styleid_ready(tmp_path, monkeypatch):
    model = tmp_path / "styleid.ckpt"
    model.write_text("stub", encoding="utf-8")
    monkeypatch.setenv("N2D_STYLEID_MODEL", str(model))
    (tmp_path / "_设置.md").write_text(
        "- 基础视觉风格: 水墨国风\n"
        "- 脸一致性机检后端: styleid\n",
        encoding="utf-8",
    )
    result = doctor.probe_face_encoder(str(tmp_path))
    assert result and result["status"] == "ready"
    assert result["stylized"] is True


def test_probe_video_backend_defers_auto_route(tmp_path):
    (tmp_path / "_设置.md").write_text("- 视频模型路由: 自动按镜头路由\n", encoding="utf-8")
    result = doctor.probe_video_backend(str(tmp_path))
    assert result and result["deferred"] is True


def test_probe_video_backend_checks_fixed_route(tmp_path):
    (tmp_path / "_设置.md").write_text(
        "- 视频模型路由: 固定生视频模型\n"
        "- 生视频模型: Seedance 2.0\n"
        "- 生视频渠道: 即梦/Dreamina\n",
        encoding="utf-8",
    )
    result = doctor.probe_video_backend(str(tmp_path))
    assert result and not result.get("deferred")
    assert result["name"] == "Seedance 2.0"
    assert result["mode"] != "unknown"
