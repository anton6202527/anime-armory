#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pytest for ad-review 模式② 第0步本地静态自审。

cd skills/ad/ad-review/scripts && python3 -m pytest -q test_self_audit.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("self_audit.py")
spec = importlib.util.spec_from_file_location("ad_self_audit", SCRIPT)
self_audit = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(self_audit)


# ── 最小对齐仓库 fixture（0 block/0 warn） ───────────────────────────────────

_CONTRACT_PY = """\
DELIVERY_PROFILE = {
    "平台默认": {"loudness_lufs": -16.0, "true_peak_db": -1.0},
    "广电TVC":  {"loudness_lufs": -23.0, "true_peak_db": -1.0},
}
CUTDOWN_PLANS = ("主片+15s+6s", "主片+15s", "仅主片", "自定义")
MULTI_ASPECT_RATIOS = ("16:9", "9:16", "4:5", "1:1")
AI_VISUAL_USAGE_MODES = ("AI-generated", "AI-assisted", "未使用AI视觉")
AD_APPROVED_IMAGE_BACKENDS = {
    "codex":    {"label": "GPT Image 2"},
    "openai":   {"label": "GPT Image 2"},
    "gemini":   {"label": "Nano Banana Pro (Gemini 3 Pro Image)"},
    "seedream": {"label": "Seedream 4.5"},
    "kling":    {"label": "Kling Image 3.0"},
    "sora":     {"label": "Sora 2"},
}
AD_FORBIDDEN_IMAGE_BACKENDS = ("dreamina", "即梦", "同视频ai")
CHOICE_POINTS = {
    "广告类型": (),
    "生图模型": (),
    "生图渠道": (),
    "AI视觉使用披露": (),
}
DEFAULT_SETTINGS = {"生图模型": "GPT Image 2", "生图渠道": "Codex CLI"}
def default_deliverables(*a, **k):
    return []
"""

_CATALOG_OK = """\
# 拍广告 · 选择点与偏好约定
## 选择点目录
- `广告类型`: TVC | 信息流短视频
- `生图模型`: GPT Image 2 | Seedream 4.5 | Nano Banana Pro (Gemini 3 Pro Image) | Kling Image 3.0 | Sora 2
- `生图渠道`: Codex CLI | OpenAI Images API | BytePlus ModelArk API | Google Gemini API | Kling API | OpenAI Sora
- `AI视觉使用披露`: AI-generated | AI-assisted
- `生视频渠道`: 即梦/Dreamina | 可灵/Kling   （渠道用于实际调用哪个产品/API）
"""

_IMAGE_SKILL_OK = """\
## 生图后端治理
生图模型默认 GPT Image 2；放行 Seedream 4.5、Kling Image 3.0、Nano Banana Pro/Gemini、Sora 2。
生图渠道默认 Codex CLI；模型与渠道分列。
禁第三方逆向出图（即梦/Dreamina 逆向 forbidden）。
"""


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _aligned_repo(root: Path) -> None:
    _write(root / "skills" / "ad" / "ad-craft" / "scripts" / "contract.py", _CONTRACT_PY)
    _write(root / "skills" / "ad" / "ad-craft" / "scripts" / "ai_usage.py",
           "from contract import AI_VISUAL_USAGE_MODES\n")
    _write(root / "skills" / "ad" / "ad-craft" / "references" / "选择点与偏好.md", _CATALOG_OK)
    _write(root / "skills" / "ad" / "ad-script" / "ad_law_check.py", "# 广告法机检\n")
    _write(root / "skills" / "ad" / "ad-craft" / "scripts" / "gate.py",
           '广告法机检报告 = "脚本/广告法机检报告.json"\n'
           'classify_image_model = classify_image_channel = image_output_route_missing = True\n')
    _write(root / "skills" / "ad" / "scripts" / "init_project.py",
           'meta = {"image_model": "GPT Image 2", "image_channel": "Codex CLI"}\n')
    _write(root / "skills" / "ad" / "ad-review" / "scripts" / "review.py",
           'ad_law = "脚本/广告法机检报告.json"\n')
    _write(root / "skills" / "ad" / "ad-image" / "SKILL.md", _IMAGE_SKILL_OK)
    # ad-compose stage 不写死 LUFS（响度走 contract）。
    _write(root / "skills" / "ad" / "ad-compose" / "deliver.py",
           "from contract import delivery_profile\n")


def test_clean_repo_zero_block_zero_warn(tmp_path: Path) -> None:
    _aligned_repo(tmp_path)
    report = self_audit.audit(tmp_path)
    assert report["counts"]["block"] == 0, report["findings"]
    assert report["counts"]["warn"] == 0, report["findings"]
    assert report["ready_for_market_scan"] is True


def test_choice_point_catalog_drift_warns(tmp_path: Path) -> None:
    """CHOICE_POINTS 有键漏在选择点目录 → 选择点对齐 warn（纯函数级判定）。"""
    _aligned_repo(tmp_path)
    # 从目录里删掉 AI视觉使用披露 这一行
    catalog = tmp_path / "skills" / "ad" / "ad-craft" / "references" / "选择点与偏好.md"
    catalog.write_text(_CATALOG_OK.replace("- `AI视觉使用披露`: AI-generated | AI-assisted\n", ""),
                       encoding="utf-8")
    findings = []
    self_audit.check_choice_point_catalog(tmp_path, findings)
    hits = [f for f in findings if f["dim"] == "选择点对齐"]
    assert hits and hits[0]["sev"] == "warn"
    assert "AI视觉使用披露" in hits[0]["msg"]


def test_ad_law_bypass_blocks(tmp_path: Path) -> None:
    """下游 review 不消费广告法机检报告（旁路）→ 广告法机检单入口 block。"""
    _aligned_repo(tmp_path)
    (tmp_path / "skills" / "ad" / "ad-review" / "scripts" / "review.py").write_text(
        "# 不读广告法机检报告\n", encoding="utf-8")
    report = self_audit.audit(tmp_path)
    hits = [f for f in report["findings"] if f["dim"] == "广告法机检单入口"]
    assert hits and hits[0]["sev"] == "block"
    assert report["counts"]["block"] >= 1


def test_image_backend_doc_drift_warns(tmp_path: Path) -> None:
    """ad-image SKILL 漏写某放行后端 → 生图后端白名单 warn。"""
    _aligned_repo(tmp_path)
    (tmp_path / "skills" / "ad" / "ad-image" / "SKILL.md").write_text(
        "生图模型默认 GPT Image 2。生图渠道默认 Codex CLI。禁逆向出图（即梦/Dreamina forbidden）。\n", encoding="utf-8")
    findings = []
    self_audit.check_image_backend_docs(tmp_path, findings)
    hits = [f for f in findings if f["dim"] == "生图后端白名单"]
    assert hits and hits[0]["sev"] == "warn"


def test_video_channel_dreamina_not_flagged(tmp_path: Path) -> None:
    """即梦/Dreamina 作为合法生视频渠道出现，不应被当成放行的生图后端（防误报）。"""
    _aligned_repo(tmp_path)
    findings = []
    self_audit.check_image_backend_docs(tmp_path, findings)
    hits = [f for f in findings if f["dim"] == "生图后端白名单"]
    # 目录里有「生视频渠道: 即梦/Dreamina」一行，但生图白名单仍应判 info（无放行误报）。
    assert hits and hits[0]["sev"] == "info"


def test_image_model_channel_split_missing_blocks(tmp_path: Path) -> None:
    _aligned_repo(tmp_path)
    contract = tmp_path / "skills" / "ad" / "ad-craft" / "scripts" / "contract.py"
    contract.write_text(contract.read_text(encoding="utf-8").replace('"生图模型": (),\n    "生图渠道": (),',
                                                                    '"生图AI": (),'), encoding="utf-8")
    findings = []
    self_audit.check_image_model_channel_split(tmp_path, findings)
    assert any(f["dim"] == "生图模型/渠道分列" and f["sev"] == "block" for f in findings)


def test_compose_hardcoded_lufs_warns(tmp_path: Path) -> None:
    """ad-compose 自己写死 LUFS 响度（绕开 contract）→ 交付规格外置 warn。"""
    _aligned_repo(tmp_path)
    (tmp_path / "skills" / "ad" / "ad-compose" / "deliver.py").write_text(
        "TARGET = -16.0  # loudnorm I=-16 LUFS\n", encoding="utf-8")
    findings = []
    self_audit.check_delivery_specs_external(tmp_path, findings)
    hits = [f for f in findings if f["dim"] == "交付规格外置"]
    assert hits and hits[0]["sev"] == "warn"


def test_stage_table_without_executable_acceptance_blocks(tmp_path: Path) -> None:
    _aligned_repo(tmp_path)
    contract = tmp_path / "skills" / "ad" / "ad-craft" / "scripts" / "contract.py"
    contract.write_text(contract.read_text(encoding="utf-8") + """
AD_STAGE_TABLE = [{"key": "brief"}]
STAGE_CRITERIA = {"brief": ({"id": "brief_required", "evidence": "deterministic", "standard": "brief complete"},)}
""", encoding="utf-8")
    findings = []
    self_audit.check_stage_acceptance_architecture(tmp_path, findings)
    hits = [f for f in findings if f["dim"] == "逐阶段验收"]
    assert hits and hits[0]["sev"] == "block"
