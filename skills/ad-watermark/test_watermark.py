from pathlib import Path
from types import SimpleNamespace

import watermark


def _args(tmp_path: Path, out: Path) -> SimpleNamespace:
    return SimpleNamespace(
        inp=str(tmp_path / "in.mp4"),
        out=str(out),
        mode="ai",
        text=None,
        desc=None,
        logo=None,
        pos=None,
        opacity=1.0,
        scale=0.12,
        fontscale=0.030,
        descscale=0.62,
        margin=0.02,
        meta=None,
    )


def test_do_video_uses_unique_temp_overlay_and_creates_output_parent(tmp_path, monkeypatch):
    saved = []
    commands = []

    class FakeOverlay:
        def save(self, path):
            saved.append(path)
            Path(path).write_text("overlay", encoding="utf-8")

    def fake_run(cmd, check):
        i_positions = [i for i, item in enumerate(cmd) if item == "-i"]
        badge = Path(cmd[i_positions[1] + 1])
        assert badge.exists()
        commands.append(cmd)

    monkeypatch.setattr(watermark, "probe_wh", lambda _p: (1280, 720))
    monkeypatch.setattr(watermark, "build_overlay", lambda _w, _h, _a: FakeOverlay())
    monkeypatch.setattr(watermark.subprocess, "run", fake_run)

    out_dir = tmp_path / "new-output-dir"
    watermark.do_video(_args(tmp_path, out_dir / "a.mp4"))
    watermark.do_video(_args(tmp_path, out_dir / "b.mp4"))

    assert out_dir.is_dir()
    assert len(saved) == 2
    assert saved[0] != saved[1]
    assert all(not Path(path).exists() for path in saved)
    assert len(commands) == 2


def test_brand_watermark_can_read_defaults_from_project_settings(tmp_path):
    work = tmp_path / "repo" / "制漫剧" / "测试剧"
    work.mkdir(parents=True)
    (work / "_设置.md").write_text(
        "- 水印：品牌\n"
        "- 水印文字：@测试账号\n"
        "- 水印位置：br\n"
        "- 水印透明度：80%\n"
        "- 水印大小：12%\n",
        encoding="utf-8",
    )

    args = SimpleNamespace(
        settings_root=str(work),
        mode=None,
        text=None,
        logo=None,
        pos=None,
        opacity=None,
        scale=None,
        fontscale=None,
        descscale=None,
        margin=None,
    )

    resolved = watermark._finalize_defaults(watermark._apply_settings_defaults(args))

    assert resolved.mode == "brand"
    assert resolved.text == "@测试账号"
    assert resolved.pos == "br"
    assert resolved.opacity == 0.8
    assert resolved.scale == 0.12
