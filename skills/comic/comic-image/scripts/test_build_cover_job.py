from pathlib import Path
import importlib.util
import json
import struct
import zlib


MODULE_PATH = Path(__file__).with_name("build_cover_job.py")
SPEC = importlib.util.spec_from_file_location("comic_build_cover_job", MODULE_PATH)
assert SPEC and SPEC.loader
cover = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cover)


def _png(width: int, height: int) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"\x00" + b"\x00\x00\x00" * width
    idat = zlib.compress(raw * height)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _scaffold(root: Path, *, synopsis: str = "少女被迫变身，斩妖除魔") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "设定库").mkdir(parents=True, exist_ok=True)
    (root / "出图" / "共享").mkdir(parents=True, exist_ok=True)
    (root / "_设置.md").write_text(
        "# 设置\n- 生图模型: GPT Image 2\n- 生图渠道: Codex CLI\n- 基础视觉风格: 彩色国漫条漫\n- 风格锚: 冷色赛博\n- 文字语言: 中文\n",
        encoding="utf-8",
    )
    (root / "_meta.json").write_text(
        json.dumps({"kind": "comic_project", "title": "测试漫画", "synopsis": synopsis, "cover": None}, ensure_ascii=False),
        encoding="utf-8",
    )
    (root / "_进度.md").write_text(
        "# 进度\n\n## 作品封面\n- [ ] 竖版封面 prompt/job 包（出图/封面/prompt/cover_job.json）\n- [ ] 竖版封面 PNG 渲染并回填 _meta.json cover\n",
        encoding="utf-8",
    )
    registry = {
        "schema_version": 2,
        "kind": "comic_identity_registry",
        "style_contract": "统一冷色调、粗线条国漫",
        "assets": {
            "CHAR_HERO": {"type": "character", "display_name": "主角", "anchor_path": "出图/共享/图片/CHAR_HERO__anchor.png"},
        },
    }
    (root / "出图" / "共享" / "identity_registry.json").write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    anchor = root / "出图" / "共享" / "图片" / "CHAR_HERO__anchor.png"
    anchor.parent.mkdir(parents=True, exist_ok=True)
    anchor.write_bytes(_png(64, 64))


def test_build_job_is_portrait_and_names_concrete_model(tmp_path: Path) -> None:
    root = tmp_path / "作品"
    _scaffold(root)
    assert cover.do_build(root) == 0
    job = json.loads((root / cover.COVER_JOB_REL).read_text(encoding="utf-8"))
    assert job["orientation"] == "portrait"
    assert job["size"]["height"] > job["size"]["width"]
    # C5: 生成者是具体模型名，渠道分列。
    assert job["生成模型"] == "GPT Image 2"
    assert job["生成渠道"] == "Codex CLI"
    assert job["status"] == "planned" and job["result_path"] == ""
    # 同源角色定妆参考进入封面包。
    assert any(ref["id"] == "CHAR_HERO" for ref in job["references"])
    assert "少女被迫变身" in job["prompt"]
    # C4/B4: build 不渲染、不动 cover。
    meta = json.loads((root / "_meta.json").read_text(encoding="utf-8"))
    assert meta["cover"] is None
    # B5 进度回写 job 包一步。
    progress = (root / "_进度.md").read_text(encoding="utf-8")
    assert "- [x] 竖版封面 prompt/job 包" in progress


def test_backfill_rejects_landscape_and_accepts_portrait(tmp_path: Path) -> None:
    root = tmp_path / "作品"
    _scaffold(root)
    cover.do_build(root)

    landscape = root / "出图" / "封面" / "wide.png"
    landscape.parent.mkdir(parents=True, exist_ok=True)
    landscape.write_bytes(_png(2560, 1440))
    assert cover.do_backfill(root, landscape) == 2
    assert json.loads((root / "_meta.json").read_text(encoding="utf-8"))["cover"] is None

    portrait = root / "出图" / "封面" / "cover.png"
    portrait.write_bytes(_png(1440, 2560))
    assert cover.do_backfill(root, portrait) == 0
    meta = json.loads((root / "_meta.json").read_text(encoding="utf-8"))
    assert meta["cover"] == "出图/封面/cover.png"
    progress = (root / "_进度.md").read_text(encoding="utf-8")
    assert "- [x] 竖版封面 PNG 渲染并回填" in progress


def test_do_build_backfills_empty_synopsis_from_bible(tmp_path: Path) -> None:
    root = tmp_path / "作品"
    _scaffold(root, synopsis="")
    (root / "设定库" / "story_bible.md").write_text(
        "# 故事圣经\n\n## 一句话核心\n- 少女被迫变身，斩妖除魔\n\n## 角色\n- x\n",
        encoding="utf-8",
    )
    assert cover.do_build(root) == 0
    meta = json.loads((root / "_meta.json").read_text(encoding="utf-8"))
    assert meta["synopsis"] == "少女被迫变身，斩妖除魔"


def test_do_build_keeps_user_synopsis(tmp_path: Path) -> None:
    root = tmp_path / "作品"
    _scaffold(root, synopsis="用户手写简介")
    (root / "设定库" / "story_bible.md").write_text(
        "# 故事圣经\n\n## 一句话核心\n- 机器抽取的核心\n",
        encoding="utf-8",
    )
    assert cover.do_build(root) == 0
    meta = json.loads((root / "_meta.json").read_text(encoding="utf-8"))
    assert meta["synopsis"] == "用户手写简介"


def test_backfill_rejects_non_png(tmp_path: Path) -> None:
    root = tmp_path / "作品"
    _scaffold(root)
    fake = root / "出图" / "封面" / "cover.png"
    fake.parent.mkdir(parents=True, exist_ok=True)
    fake.write_bytes(b"not a png")
    assert cover.do_backfill(root, fake) == 2
    assert json.loads((root / "_meta.json").read_text(encoding="utf-8"))["cover"] is None
