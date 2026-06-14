from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("self_audit.py")
spec = importlib.util.spec_from_file_location("self_audit", SCRIPT)
self_audit = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(self_audit)


def _minimal_repo(root: Path) -> None:
    (root / "skills" / "n2d").mkdir(parents=True)
    (root / "skills" / "n2d-progress").mkdir(parents=True)
    (root / "skills" / "n2d-dashboard" / "references").mkdir(parents=True)
    (root / "skills" / "n2d-image").mkdir(parents=True)
    (root / "skills" / "n2d" / "progress.py").write_text(
        "def progress_lock(): pass\n"
        "def atomic_write_text():\n"
        "    os.replace('a', 'b')\n",
        encoding="utf-8",
    )
    (root / "skills" / "n2d-progress" / "scan.py").write_text(
        "def coverage_status(): pass\n"
        "def episode_coverage(): pass\n"
        "score_ = 'score_*.json'\n"
        "review_ui_ = 'review_ui_*.html'\n",
        encoding="utf-8",
    )
    (root / "skills" / "n2d-dashboard" / "references" / "industry_benchmark.json").write_text(
        '{"collected":"2026-06","sources":[],"one_pass_rate":0.9,"redraw_rate":0.1}\n',
        encoding="utf-8",
    )
    (root / "skills" / "n2d-image" / "SKILL.md").write_text(
        "python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image\n",
        encoding="utf-8",
    )


def _write_minimal_contract(root: Path) -> None:
    (root / "skills" / "n2d" / "_lib").mkdir(parents=True, exist_ok=True)
    (root / "skills" / "n2d" / "_lib" / "n2d_contract.py").write_text(
        "APPROVED_IMAGE_BACKENDS = {\n"
        "  'codex': {'label': 'Codex'},\n"
        "  'openai': {'label': '官方 OpenAI gpt-image / DALL·E'},\n"
        "  'dreamina': {'label': 'Dreamina/即梦官方 CLI'},\n"
        "}\n",
        encoding="utf-8",
    )


def _write_facade_contract(root: Path) -> None:
    """镜像真实 n2d_contract.py 的 facade 形态：本体不直接定义符号，而是
    `from n2d_const import *`（绝对，需 _lib 在 sys.path）失败回退到相对导入。
    扁平 stub 永远导入成功，测不出 load_contract 漏加 sys.path 的 bug——这个
    fixture 才能复现生产里的 `attempted relative import with no known parent package`。"""
    lib = root / "skills" / "n2d" / "_lib"
    lib.mkdir(parents=True, exist_ok=True)
    (lib / "n2d_const.py").write_text(
        "APPROVED_IMAGE_BACKENDS = {\n"
        "  'codex': {'label': 'Codex'},\n"
        "  'openai': {'label': '官方 OpenAI gpt-image / DALL·E'},\n"
        "  'dreamina': {'label': 'Dreamina/即梦官方 CLI'},\n"
        "}\n",
        encoding="utf-8",
    )
    (lib / "n2d_contract.py").write_text(
        "try:\n"
        "    from n2d_const import *\n"
        "except ImportError:\n"
        "    from .n2d_const import *\n",
        encoding="utf-8",
    )


def test_self_audit_loads_facade_contract_without_engine_error(tmp_path: Path) -> None:
    """回归 F1：facade 形态 contract 必须能被 load_contract 导入，
    不得报 `自审引擎错误` block（否则模式② 第0步自锁）。"""
    _minimal_repo(tmp_path)
    _write_facade_contract(tmp_path)
    (tmp_path / "skills" / "n2d-image" / "SKILL.md").write_text(
        "生图AI 可选 Codex、OpenAI/gpt-image、Dreamina/即梦官方 CLI；同视频AI 是禁用旧值。\n"
        "python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image\n",
        encoding="utf-8",
    )
    report = self_audit.audit(tmp_path)
    assert not [f for f in report["findings"] if f["dim"] == "自审引擎错误"]
    assert report["counts"]["block"] == 0
    # 白名单一致性检查依赖 contract 成功导入——确认它真的跑了而非被跳过
    backend = [f for f in report["findings"] if f["dim"] == "生图后端白名单"]
    assert backend and backend[0]["sev"] == "info"


def test_self_audit_passes_minimal_aligned_repo(tmp_path: Path) -> None:
    _minimal_repo(tmp_path)
    report = self_audit.audit(tmp_path)
    assert report["counts"]["block"] == 0
    assert not [f for f in report["findings"] if f["dim"] == "gate 单入口" and f["sev"] == "warn"]


def test_self_audit_flags_bare_production_gate(tmp_path: Path) -> None:
    _minimal_repo(tmp_path)
    (tmp_path / "skills" / "n2d-image" / "SKILL.md").write_text(
        "python3 skills/n2d-review/scripts/gate.py <作品根> 第N集 --stage image\n",
        encoding="utf-8",
    )
    report = self_audit.audit(tmp_path)
    matches = [f for f in report["findings"] if f["dim"] == "gate 单入口"]
    assert matches and matches[0]["sev"] == "warn"


def test_self_audit_flags_image_backend_doc_drift(tmp_path: Path) -> None:
    _minimal_repo(tmp_path)
    _write_minimal_contract(tmp_path)
    (tmp_path / "skills" / "n2d-image" / "SKILL.md").write_text(
        "生图AI 可选 Codex 和 Dreamina/即梦官方 CLI。\n",
        encoding="utf-8",
    )
    report = self_audit.audit(tmp_path)
    matches = [f for f in report["findings"] if f["dim"] == "生图后端白名单"]
    assert matches and matches[0]["sev"] == "warn"
    assert "OpenAI" in matches[0]["loc"]


def test_self_audit_accepts_image_backend_docs_aligned(tmp_path: Path) -> None:
    _minimal_repo(tmp_path)
    _write_minimal_contract(tmp_path)
    (tmp_path / "skills" / "n2d-image" / "SKILL.md").write_text(
        "生图AI 可选 Codex、OpenAI/gpt-image、Dreamina/即梦官方 CLI；同视频AI 是禁用旧值。\n",
        encoding="utf-8",
    )
    report = self_audit.audit(tmp_path)
    matches = [f for f in report["findings"] if f["dim"] == "生图后端白名单"]
    assert matches and matches[0]["sev"] == "info"
