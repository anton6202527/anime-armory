import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import settings_cli as cli  # noqa: E402


def make_project(tmp_path: Path) -> Path:
    root = tmp_path / "repo" / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (tmp_path / "repo" / "skills").mkdir()
    (root / "_设置.md").write_text(
        "\n".join([
            "# 设置",
            "",
            "- **制作模式**：先出视频后配音",
            "- **更新重制策略**：最小",
            "",
            "## 记录",
            "- 2026-06-01 初始设置",
        ]) + "\n",
        encoding="utf-8",
    )
    return root


def test_set_preserves_bold_key_and_appends_record(tmp_path: Path, capsys) -> None:
    root = make_project(tmp_path)

    rc = cli.main(["set", str(root), "更新重制策略", "保图刷新", "--json"])

    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["old"] == "最小"
    assert out["new"] == "严审刷新"
    text = (root / "_设置.md").read_text(encoding="utf-8")
    assert "- **更新重制策略**：严审刷新" in text
    assert "设置 更新重制策略 = 严审刷新" in text


def test_audit_flags_invalid_values(tmp_path: Path, capsys) -> None:
    root = make_project(tmp_path)
    (root / "_设置.md").write_text("- 更新重制策略：坏值\n", encoding="utf-8")

    rc = cli.main(["audit", str(root), "--json"])

    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["errors"] == 1
    assert out["rows"][0]["level"] == "error"


def test_set_force_allows_experimental_value(tmp_path: Path) -> None:
    root = make_project(tmp_path)

    rc = cli.main(["set", str(root), "生视频模型", "未来模型X", "--force", "--no-record"])

    assert rc == 0
    assert "- 生视频模型：未来模型X" in (root / "_设置.md").read_text(encoding="utf-8")


def test_compliance_usage_alias_normalizes_to_internal_only(tmp_path: Path, capsys) -> None:
    root = make_project(tmp_path)

    rc = cli.main(["set", str(root), "合规用途", "demo学习使用", "--json"])

    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["new"] == "internal_only"
    assert "- 合规用途：internal_only" in (root / "_设置.md").read_text(encoding="utf-8")


def test_image2image_reference_chain_setting_is_valid(tmp_path: Path, capsys) -> None:
    root = make_project(tmp_path)
    (root / "_设置.md").write_text(
        "- 一致性增强(LoRA)：本机慢速不等待，优先 image2image/多图参考链\n",
        encoding="utf-8",
    )

    rc = cli.main(["audit", str(root), "--json"])

    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["errors"] == 0


def test_reset_removes_setting(tmp_path: Path, capsys) -> None:
    root = make_project(tmp_path)

    rc = cli.main(["reset", str(root), "更新重制策略", "--json"])

    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["old"] == "最小"
    text = (root / "_设置.md").read_text(encoding="utf-8")
    assert "更新重制策略**：" not in text
    assert "重置选项 更新重制策略" in text


def test_sync_global_all_writes_repo_default(tmp_path: Path, capsys) -> None:
    root = make_project(tmp_path)

    rc = cli.main(["sync-global", str(root), "--all", "--json"])

    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    global_path = Path(out["global_settings"])
    assert global_path.name == "创作偏好-默认.md"
    text = global_path.read_text(encoding="utf-8")
    assert "- 制作模式: 先出视频后配音" in text
    assert "- 更新重制策略: 最小" in text


def test_audit_warns_legacy_video_ai_and_model_channel_confusion(tmp_path: Path, capsys) -> None:
    root = make_project(tmp_path)
    (root / "_设置.md").write_text(
        "\n".join([
            "- 项目规模: 多集长线",
            "- 生图模型: Codex",
            "- 生图AI: GPT Image 2",
            "- 生视频AI: 即梦",
        ]) + "\n",
        encoding="utf-8",
    )

    rc = cli.main(["audit", str(root), "--json"])

    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    messages = "\n".join(row["message"] for row in out["rows"])
    assert "生图模型 must name the generator model" in messages
    assert "生图AI is the channel/access path" in messages
    assert "legacy field is present without the split 生视频模型 + 生视频渠道 pair" in messages


def test_audit_warns_long_running_without_native_subject_backend(tmp_path: Path, capsys) -> None:
    root = make_project(tmp_path)
    for ep in ("第1集", "第2集", "第3集"):
        d = root / "脚本" / ep
        d.mkdir(parents=True)
        (d / "storyboard.json").write_text("{}", encoding="utf-8")
    (root / "_设置.md").write_text("- 生图AI: Codex\n", encoding="utf-8")

    rc = cli.main(["audit", str(root), "--json"])

    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    messages = "\n".join(row["message"] for row in out["rows"])
    assert "persistent subject/character-id evidence" in messages
    assert "record 项目规模=多集长线" in messages
