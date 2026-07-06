import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent

CASES = [
    {
        "skill": "n2d-settings",
        "family": "n2d",
        "root_dir": "制漫剧",
        "initial": "- 制作模式：先出视频后配音\n",
        "key": "更新重制策略",
        "value": "严审刷新",
    },
    {
        "skill": "novel-settings",
        "family": "novel",
        "root_dir": "写小说",
        "initial": "- 小说生成工作流：默认单步\n",
        "key": "小说生成工作流",
        "value": "三步迭代",
    },
    {
        "skill": "comic-settings",
        "family": "comic",
        "root_dir": "画漫画",
        "initial": "- 漫画形态：条漫\n",
        "key": "漫画形态",
        "value": "页漫",
    },
    {
        "skill": "song-settings",
        "family": "song",
        "root_dir": "写歌",
        "initial": "- 歌曲用途：完整Demo\n",
        "key": "生成版数",
        "value": "4",
    },
    {
        "skill": "mv-settings",
        "family": "mv",
        "root_dir": "制MV",
        "initial": "- MV用途：歌曲Demo\n",
        "key": "MV规划粒度",
        "value": "精细",
    },
    {
        "skill": "ad-settings",
        "family": "ad",
        "root_dir": "拍广告",
        "initial": "- 广告类型：信息流短视频\n",
        "key": "主片时长",
        "value": "15s",
    },
]


def make_project(tmp_path: Path, case: dict) -> Path:
    repo = tmp_path / "repo"
    (repo / "skills").mkdir(parents=True, exist_ok=True)
    root = repo / case["root_dir"] / "测试设置项目"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text(
        "# 设置\n\n" + case["initial"] + "\n## 记录\n- 2026-07-06 初始设置\n",
        encoding="utf-8",
    )
    return root


def run_cli(skill: str, *args: str) -> subprocess.CompletedProcess[str]:
    script = REPO / "skills" / skill / "scripts" / "settings_cli.py"
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_settings_skills_are_line_local_and_manage_project_settings(tmp_path: Path) -> None:
    for case in CASES:
        root = make_project(tmp_path, case)

        set_proc = run_cli(case["skill"], "set", str(root), case["key"], case["value"], "--json")
        assert set_proc.returncode == 0, set_proc.stderr
        set_data = json.loads(set_proc.stdout)
        assert set_data["new"] == case["value"]

        audit_proc = run_cli(case["skill"], "audit", str(root), "--json")
        assert audit_proc.returncode == 0, audit_proc.stdout + audit_proc.stderr
        audit_data = json.loads(audit_proc.stdout)
        assert audit_data["family"] == case["family"]
        assert audit_data["settings"][case["key"]] == case["value"]

        sync_proc = run_cli(case["skill"], "sync-global", str(root), "--key", case["key"], "--json")
        assert sync_proc.returncode == 0, sync_proc.stderr
        sync_data = json.loads(sync_proc.stdout)
        global_path = Path(sync_data["global_settings"])
        assert global_path.is_file()
        assert f"- {case['key']}: {case['value']}" in global_path.read_text(encoding="utf-8")

        reset_proc = run_cli(case["skill"], "reset", str(root), case["key"], "--json")
        assert reset_proc.returncode == 0, reset_proc.stdout + reset_proc.stderr
        text = (root / "_设置.md").read_text(encoding="utf-8")
        assert f"{case['key']}：" not in text
        assert f"{case['key']}:" not in text
