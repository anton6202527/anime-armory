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
            "- **制作模式**：配音先行",
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
    assert "- 制作模式: 配音先行" in text
    assert "- 更新重制策略: 最小" in text
