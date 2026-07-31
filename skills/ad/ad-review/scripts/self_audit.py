#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local static self-audit for the ad-* (拍广告) skill family.

This is the report-only 第0步 of `ad-review` 模式②（流程自审）. It does NOT
fetch market benchmarks and does NOT edit files; it checks that the ad
production line stays aligned around its own engineering / compliance
guardrails before the agent spends time on online 市场对标.

自包含：只查 ad 线自己的文件，不读取、不导入、不比较其它创作系列的任何脚本。
纯标准库。0 block / 0 warn 才建议进入联网市场对标。

用法：
    python3 skills/ad/ad-review/scripts/self_audit.py            # 人读 markdown
    python3 skills/ad/ad-review/scripts/self_audit.py --json     # 喂回 LLM 汇总
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


Finding = Dict[str, Any]


# 关键文档：生图后端白名单 / 选择点目录 / AI 披露应该在这些地方保持一致。
IMAGE_BACKEND_DOCS = (
    "skills/ad/ad-image/SKILL.md",
    "skills/ad/ad-craft/references/选择点与偏好.md",
)

# canonical key → 文档里允许出现的别名（命中任一即视为已覆盖）。
IMAGE_BACKEND_DOC_ALIASES = {
    "codex": ("Codex",),
    "openai": ("OpenAI", "gpt-image", "DALL"),
    "gemini": ("Nano Banana", "Gemini"),
    "seedream": ("Seedream",),
    "kling": ("可灵", "Kling", "主体库"),
    "sora": ("Sora", "Cameo"),
}


def repo_root_from_here() -> Path:
    # .../skills/ad/ad-review/scripts/self_audit.py → parents[4] == repo root
    return Path(__file__).resolve().parents[4]


def rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def add(findings: List[Finding], sev: str, dim: str, loc: str, msg: str, suggestion: str = "") -> None:
    findings.append({"sev": sev, "dim": dim, "loc": loc, "msg": msg, "suggestion": suggestion})


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def has_any(raw: str, aliases: Sequence[str]) -> bool:
    lowered = raw.lower()
    return any(alias.lower() in lowered for alias in aliases)


def load_contract(root: Path):
    """Import ad-craft/scripts/contract.py from THIS root (self-contained, flat module)."""
    path = root / "skills" / "ad" / "ad-craft" / "scripts" / "contract.py"
    if not path.is_file():
        return None, None
    # contract.py 是扁平自包含模块（无 facade、无 `from x import *`），直接按文件加载即可。
    # 用唯一私有模块名，避免污染调用方 sys.modules（多 root / pytest 套）。
    saved = sys.modules.pop("_ad_self_audit_contract", None)
    try:
        spec = importlib.util.spec_from_file_location("_ad_self_audit_contract", path)
        if spec is None or spec.loader is None:
            return None, "无法加载 contract.py"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, None
    except Exception as exc:  # pragma: no cover - defensive report path
        return None, str(exc)
    finally:
        sys.modules.pop("_ad_self_audit_contract", None)
        if saved is not None:
            sys.modules["_ad_self_audit_contract"] = saved


def iter_docs(root: Path) -> Iterable[Path]:
    """所有 ad 线文档（README 不归 ad 线管，不扫）。"""
    skill_root = root / "skills"
    seen = set()
    for pattern in ("ad/**/*.md", "ad-*/**/*.md"):
        for path in skill_root.glob(pattern):
            if path.is_file() and path not in seen:
                seen.add(path)
                yield path


# ── 检查项 ────────────────────────────────────────────────────────────────

def check_ad_law_single_entry(root: Path, findings: List[Finding]) -> None:
    """广告法机检单入口：ad_law_check.py 是唯一机检入口，且下游 gate/review 真在消费它的报告。

    block 触发条件：① 机检脚本不存在；② gate.py 或 review.py 任一不消费 `广告法机检报告.json`
    （= 有旁路，广告法这条 ad 线核心硬闸门被绕过）。
    """
    checker = root / "skills" / "ad" / "ad-script" / "ad_law_check.py"
    if not checker.is_file():
        add(findings, "block", "广告法机检单入口", rel(root, checker),
            "广告法机检脚本不存在——ad 线核心硬闸门缺失。",
            "恢复 skills/ad/ad-script/ad_law_check.py（绝对化/医疗/化妆品/金融教育/促销/房地产词库）。")
        return
    report_token = "广告法机检报告.json"
    consumers = {
        "ad-craft/scripts/gate.py": root / "skills" / "ad" / "ad-craft" / "scripts" / "gate.py",
        "ad-review/scripts/review.py": root / "skills" / "ad" / "ad-review" / "scripts" / "review.py",
    }
    bypassed = [label for label, path in consumers.items() if report_token not in text(path)]
    if bypassed:
        add(findings, "block", "广告法机检单入口", ", ".join(bypassed),
            f"下游闸门未消费 {report_token}，广告法机检存在旁路：{', '.join(bypassed)}。",
            "让 gate（image/video/compose 前）与 review（投放前 M0）都读 广告法机检报告.json 的 summary.block。")
    else:
        add(findings, "info", "广告法机检单入口", "skills/ad/ad-script/ad_law_check.py",
            "广告法机检脚本存在，gate 与 review 均消费其报告，无旁路。")


def check_delivery_specs_external(root: Path, findings: List[Finding]) -> None:
    """cutdown/多比例/LUFS 交付规格必须外置在 contract，不能散落硬编码在各 stage。

    block：contract 缺关键交付规格契约（DELIVERY_PROFILE/loudness_lufs/CUTDOWN_PLANS/MULTI_ASPECT_RATIOS）。
    warn：ad-compose 脚本里出现裸 LUFS 数字字面量（疑似绕开 contract.DELIVERY_PROFILE 自己写死响度）。
    """
    contract, error = load_contract(root)
    cpath = root / "skills" / "ad" / "ad-craft" / "scripts" / "contract.py"
    if error:
        add(findings, "block", "自审引擎错误", rel(root, cpath),
            f"无法导入 ad-craft contract.py（自审工具故障，非作品问题）：{error}")
        return
    if contract is None:
        add(findings, "info", "交付规格外置", rel(root, cpath), "未找到 ad-craft contract.py，跳过交付规格外置检查。")
        return
    profile = getattr(contract, "DELIVERY_PROFILE", None)
    missing = []
    if not isinstance(profile, dict) or not profile:
        missing.append("DELIVERY_PROFILE")
    elif not all("loudness_lufs" in v for v in profile.values() if isinstance(v, dict)):
        missing.append("DELIVERY_PROFILE.loudness_lufs")
    if not getattr(contract, "CUTDOWN_PLANS", None):
        missing.append("CUTDOWN_PLANS")
    if not getattr(contract, "MULTI_ASPECT_RATIOS", None):
        missing.append("MULTI_ASPECT_RATIOS")
    if not callable(getattr(contract, "default_deliverables", None)):
        missing.append("default_deliverables()")
    if missing:
        add(findings, "block", "交付规格外置", rel(root, cpath),
            f"contract 缺交付规格契约：{', '.join(missing)}。",
            "把 cutdown 方案 / 多比例 / LUFS 响度·安全框集中在 ad-craft contract，stage 只消费。")
        return

    # ad-compose 不得自己写死响度数字（应从 contract.delivery_profile 取）。
    compose_dir = root / "skills" / "ad" / "ad-compose"
    # 只抓疑似写死目标值（负数）；容差说明如 ±1.5 LUFS 不算目标重复定义。
    lufs_re = re.compile(r"-\d{1,2}(?:\.\d+)?\s*lufs", re.I)
    offenders = []
    if compose_dir.is_dir():
        for path in compose_dir.glob("**/*.py"):
            if "test" in path.name:
                continue
            for idx, line in enumerate(text(path).splitlines(), start=1):
                if "delivery_profile" in line or "DELIVERY_PROFILE" in line:
                    continue
                if lufs_re.search(line):
                    offenders.append(f"{rel(root, path)}:{idx}")
    if offenders:
        add(findings, "warn", "交付规格外置", ", ".join(offenders[:6]),
            f"ad-compose 疑似硬编码 LUFS 响度（应从 contract.delivery_profile 取）：{len(offenders)} 处。",
            "改成读 ad-craft contract.delivery_profile(交付规格)，不要在 stage 里写死 -16 LUFS 之类的数字。")
    else:
        add(findings, "info", "交付规格外置", "skills/ad/ad-craft/scripts/contract.py",
            "cutdown/多比例/LUFS 交付规格集中在 contract，ad-compose 未发现硬编码响度。")


def check_image_backend_docs(root: Path, findings: List[Finding]) -> None:
    """生图后端白名单文档一致性：ad-image / 选择点目录 必须覆盖 AD_APPROVED_IMAGE_BACKENDS，
    且不得把 AD_FORBIDDEN_IMAGE_BACKENDS（即梦/Dreamina 逆向）当成可选放行后端。"""
    contract, error = load_contract(root)
    cpath = root / "skills" / "ad" / "ad-craft" / "scripts" / "contract.py"
    if error:
        add(findings, "block", "自审引擎错误", rel(root, cpath),
            f"无法导入 ad-craft contract.py（自审工具故障，非作品问题）：{error}")
        return
    if contract is None:
        add(findings, "info", "生图后端白名单", rel(root, cpath), "未找到 ad-craft contract.py，跳过白名单文档一致性检查。")
        return
    approved = getattr(contract, "AD_APPROVED_IMAGE_BACKENDS", None)
    if not isinstance(approved, dict) or not approved:
        add(findings, "warn", "生图后端白名单", rel(root, cpath), "AD_APPROVED_IMAGE_BACKENDS 缺失或为空。")
        return
    forbidden = tuple(getattr(contract, "AD_FORBIDDEN_IMAGE_BACKENDS", ()) or ())

    missing_docs: List[str] = []
    forbidden_promoted: List[str] = []
    allow_forbidden_ctx = re.compile(r"(禁|阻断|逆向|未授权|不得|forbidden|拦|旧值|降级|移除|改成|忽略)", re.I)
    for rel_doc in IMAGE_BACKEND_DOCS:
        doc_path = root / rel_doc
        if not doc_path.is_file():
            continue
        raw = text(doc_path)
        miss = []
        for key, spec in approved.items():
            aliases = list(IMAGE_BACKEND_DOC_ALIASES.get(str(key), (str(key),)))
            label = str(spec.get("label") or "")
            if label:
                aliases.append(label.split("/")[0].split("（")[0].split("(")[0].strip())
            if not has_any(raw, [a for a in aliases if a]):
                miss.append(str(spec.get("label") or key))
        if miss:
            missing_docs.append(f"{rel_doc} 缺 {', '.join(miss)}")
        # forbidden 后端若出现在 **生图** 语境且未带「禁用/逆向」语境的行 = 疑似被当成可选生图后端放行。
        # 注意：即梦/Dreamina 同时是合法的「生视频渠道」候选，那一行不算违规——只看生图上下文行。
        image_ctx = re.compile(r"(生图|出图|image|定妆|首帧|hero|kv)", re.I)
        for idx, line in enumerate(raw.splitlines(), start=1):
            low = line.lower()
            if not image_ctx.search(line):
                continue
            for bad in forbidden:
                if bad and bad.lower() in low and not allow_forbidden_ctx.search(line):
                    forbidden_promoted.append(f"{rel_doc}:{idx}（{bad}）")
                    break

    if missing_docs or forbidden_promoted:
        locs = missing_docs[:4]
        if forbidden_promoted:
            locs.append("疑似放行逆向后端: " + ", ".join(forbidden_promoted[:6]))
        add(findings, "warn", "生图后端白名单", "; ".join(locs),
            "生图后端文档与 AD_APPROVED_IMAGE_BACKENDS 不一致，可能重新制造后端口径分叉。",
            "从 ad-craft contract.AD_APPROVED_IMAGE_BACKENDS 刷新 ad-image 说明 + 选择点目录；"
            "即梦/Dreamina 逆向只能作禁用语境出现。")
    else:
        add(findings, "info", "生图后端白名单", "skills/ad/ad-craft/scripts/contract.py",
            "关键文档已覆盖 AD_APPROVED_IMAGE_BACKENDS，未把逆向后端当作可选放行。")


def check_image_model_channel_split(root: Path, findings: List[Finding]) -> None:
    """C5: generation identity is a concrete model; channel is a separate access path."""
    contract, error = load_contract(root)
    cpath = root / "skills" / "ad" / "ad-craft" / "scripts" / "contract.py"
    if error or contract is None:
        add(findings, "block", "生图模型/渠道分列", rel(root, cpath),
            f"无法核验生图路由契约：{error or 'contract missing'}")
        return
    choices = getattr(contract, "CHOICE_POINTS", {}) or {}
    defaults = getattr(contract, "DEFAULT_SETTINGS", {}) or {}
    missing = []
    if "生图模型" not in choices or "生图渠道" not in choices:
        missing.append("CHOICE_POINTS 生图模型/生图渠道")
    if not defaults.get("生图模型") or not defaults.get("生图渠道"):
        missing.append("DEFAULT_SETTINGS 生图模型/生图渠道")
    init_text = text(root / "skills" / "ad" / "scripts" / "init_project.py")
    gate_text = text(root / "skills" / "ad" / "ad-craft" / "scripts" / "gate.py")
    if not all(token in init_text for token in ("image_model", "image_channel")):
        missing.append("init_project image_model/image_channel")
    if not all(token in gate_text for token in ("classify_image_model", "classify_image_channel", "image_output_route_missing")):
        missing.append("gate model/channel provenance")
    if missing:
        add(findings, "block", "生图模型/渠道分列", ", ".join(missing),
            "生图生成者仍可能退化成 agent/厂商/渠道壳，违反具体模型指代与可审计路由。",
            "新项目分列 生图模型+生图渠道；每个已落图 job 同时记录 model/channel，旧 生图AI 只作迁移。")
    else:
        add(findings, "info", "生图模型/渠道分列", "skills/ad/ad-craft/scripts/contract.py",
            "生图模型与访问渠道已分列，init 与落图 gate 均消费。")


def check_ai_usage_disclosure(root: Path, findings: List[Finding]) -> None:
    """AI 使用披露文档一致性：ai_usage.py 存在，且 AI_VISUAL_USAGE_MODES 各模式在披露脚本里被引用。"""
    contract, error = load_contract(root)
    cpath = root / "skills" / "ad" / "ad-craft" / "scripts" / "contract.py"
    if error:
        add(findings, "block", "自审引擎错误", rel(root, cpath),
            f"无法导入 ad-craft contract.py（自审工具故障，非作品问题）：{error}")
        return
    usage_py = root / "skills" / "ad" / "ad-craft" / "scripts" / "ai_usage.py"
    if not usage_py.is_file():
        add(findings, "block", "AI披露一致性", rel(root, usage_py),
            "AI 使用/授权披露脚本不存在——投放前 review 的留痕项会永远缺失。",
            "恢复 skills/ad/ad-craft/scripts/ai_usage.py（写 合规/ai_usage.json）。")
        return
    modes = tuple(getattr(contract, "AI_VISUAL_USAGE_MODES", ()) or ()) if contract else ()
    raw = text(usage_py)
    if modes and "AI_VISUAL_USAGE_MODES" not in raw:
        add(findings, "warn", "AI披露一致性", rel(root, usage_py),
            "ai_usage.py 未引用 contract.AI_VISUAL_USAGE_MODES，披露模式可能与契约分叉。",
            "ai_usage.py 的 visual-mode/video-mode 选项应直接 import contract.AI_VISUAL_USAGE_MODES。")
    else:
        add(findings, "info", "AI披露一致性", rel(root, usage_py),
            "AI 披露脚本存在，且与 contract.AI_VISUAL_USAGE_MODES 对齐。")


def check_choice_point_catalog(root: Path, findings: List[Finding]) -> None:
    """_设置.md 选择点目录 vs contract.CHOICE_POINTS：每个选择点键都应在 选择点与偏好.md 出现。"""
    contract, error = load_contract(root)
    cpath = root / "skills" / "ad" / "ad-craft" / "scripts" / "contract.py"
    if error:
        add(findings, "block", "自审引擎错误", rel(root, cpath),
            f"无法导入 ad-craft contract.py（自审工具故障，非作品问题）：{error}")
        return
    if contract is None:
        add(findings, "info", "选择点对齐", rel(root, cpath), "未找到 contract.py，跳过选择点目录对齐检查。")
        return
    choice_points = getattr(contract, "CHOICE_POINTS", None)
    if not isinstance(choice_points, dict) or not choice_points:
        add(findings, "warn", "选择点对齐", rel(root, cpath), "CHOICE_POINTS 缺失或为空。")
        return
    catalog = root / "skills" / "ad" / "ad-craft" / "references" / "选择点与偏好.md"
    raw = text(catalog)
    if not raw:
        add(findings, "warn", "选择点对齐", rel(root, catalog),
            "选择点目录文档不存在，无法核对 CHOICE_POINTS 是否都暴露给用户。",
            "补 skills/ad/ad-craft/references/选择点与偏好.md，列全 CHOICE_POINTS 的键 + 缺省。")
        return
    missing = [key for key in choice_points if key not in raw]
    if missing:
        add(findings, "warn", "选择点对齐", rel(root, catalog),
            f"CHOICE_POINTS 有 {len(missing)} 个键未出现在选择点目录：{', '.join(missing)}。",
            "在 选择点与偏好.md 的「选择点目录」补齐这些键，让用户可见可改；选择点必须可读不可硬编码。")
    else:
        add(findings, "info", "选择点对齐", rel(root, catalog),
            "contract.CHOICE_POINTS 全部出现在选择点目录文档里。")


def check_paid_runner_gates(root: Path, findings: List[Finding]) -> None:
    """付费执行器本身必须调用 gate，不能只靠 SKILL.md 提醒。"""
    runners = {
        "skills/ad/ad-image/scripts/render_dreamina.py": "enforce_gate",
        "skills/ad/ad-video/scripts/render_dreamina.py": "enforce_gate",
        "skills/ad/ad-compose/compose.sh": "gate.py",
    }
    present = 0
    for relpath, token in runners.items():
        path = root / relpath
        if not path.is_file():
            continue
        present += 1
        if token not in text(path):
            add(findings, "block", "付费执行器 gate", relpath,
                f"正式执行器未包含 {token}，可绕过花钱/不可逆闸门。",
                "在 runner/compose 入口直接执行 ad-craft gate，失败即停止。")
    if present and not any(f["dim"] == "付费执行器 gate" and f["sev"] == "block" for f in findings):
        add(findings, "info", "付费执行器 gate", "ad image/video/compose runners",
            "现有正式执行器均在代码入口调用 gate。")


def check_demo_literals(root: Path, findings: List[Finding]) -> None:
    """样例品牌不能泄漏到非测试生产 prompt/runner。"""
    offenders = []
    for base in (root / "skills" / "ad" / "ad-image", root / "skills" / "ad" / "ad-video"):
        if not base.is_dir():
            continue
        for path in base.glob("**/*"):
            if not path.is_file() or path.suffix not in {".py", ".md"} or path.name.startswith("test_"):
                continue
            if re.search(r"STARBOX|Starbox|星盒", text(path)):
                offenders.append(rel(root, path))
    if offenders:
        add(findings, "block", "模板去样例化", ", ".join(offenders[:8]),
            "样例品牌字面量泄漏到生产出图/视频代码或文档，会污染其它行业项目。",
            "改为读取 brief/asset_registry；样例只允许存在 test fixture。")
    elif any((root / "skills" / x).is_dir() for x in ("ad-image", "ad-video")):
        add(findings, "info", "模板去样例化", "skills/ad/ad-image + skills/ad/ad-video",
            "非测试生产文件未发现 STARBOX/Starbox/星盒样例字面量。")


def check_release_order_and_evidence(root: Path, findings: List[Finding]) -> None:
    contract, error = load_contract(root)
    if error or contract is None:
        return
    table = getattr(contract, "AD_STAGE_TABLE", None)
    if isinstance(table, list):
        keys = [row.get("key") for row in table if isinstance(row, dict)]
        if "handoff" in keys and "review" in keys and keys.index("handoff") > keys.index("review"):
            add(findings, "block", "发布阶段顺序", "skills/ad/ad-craft/scripts/contract.py",
                "review 发生在 handoff/compliance 之前，最终审查无法消费发布合规证据。",
                "阶段顺序改为 compose → handoff/compliance → review → feedback。")
        elif "handoff" in keys and "review" in keys:
            add(findings, "info", "发布阶段顺序", "skills/ad/ad-craft/scripts/contract.py",
                "handoff/compliance 位于最终 review 之前。")
    manifest = root / "skills" / "ad" / "ad-craft" / "scripts" / "compliance_manifest.py"
    producer = root / "skills" / "ad" / "ad-craft" / "scripts" / "producer_pack.py"
    if manifest.is_file() and producer.is_file():
        required = ("evidence_type", "evidence_file", "method", "evidence_date", "territory", "approved_by",
                    "source_name", "source_locator", "applicable_scope", "validity", "display_disclosure",
                    "issuer_qualification", "representativeness")
        missing = [token for token in required if token not in text(producer)]
        if missing:
            add(findings, "block", "claim证据结构", rel(root, producer),
                "claim 证据缺结构化字段：" + ", ".join(missing),
                "claim 必须按证据类型记录来源、方法/资质/样本、条件、范围、有效期、披露文案和批准人。")
        else:
            add(findings, "info", "claim证据结构", rel(root, producer),
                "claim 依据与发布 compliance manifest 均已机器化。")
        rights_required = ("RIGHTS_STATUSES", "media_scope", "valid_from", "valid_until", "license_expired")
        rights_missing = [token for token in rights_required if token not in text(producer)]
        if rights_missing:
            add(findings, "block", "授权证据结构", rel(root, producer),
                "授权合同缺结构化字段/期限闸：" + ", ".join(rights_missing),
                "真人/音乐/字体/素材逐项记录状态、证据、地域、媒介范围、期限和批准人。")
        else:
            add(findings, "info", "授权证据结构", rel(root, producer),
                "授权状态、证据文件、地域/媒介范围与期限已机器化。")


def check_stage_acceptance_architecture(root: Path, findings: List[Finding]) -> None:
    """每阶段必须有同一套可执行标准；不能靠进度表自由手填 ✅。"""
    contract, error = load_contract(root)
    cpath = root / "skills" / "ad" / "ad-craft" / "scripts" / "contract.py"
    if error or contract is None:
        return
    table = getattr(contract, "AD_STAGE_TABLE", None)
    if not isinstance(table, list) or not table:
        # 兼容 self_audit 的极简 fixture / 旧仓：其它检查仍可独立运行。
        add(findings, "info", "逐阶段验收", rel(root, cpath), "未声明 AD_STAGE_TABLE，跳过逐阶段验收架构检查。")
        return
    keys = [row.get("key") for row in table if isinstance(row, dict) and row.get("key")]
    criteria = getattr(contract, "STAGE_CRITERIA", None)
    allowed = {"deterministic", "official", "house", "human", "heuristic"}
    missing = []
    malformed = []
    for key in keys:
        rows = criteria.get(key) if isinstance(criteria, dict) else None
        if not rows:
            missing.append(key)
            continue
        if any(not isinstance(row, dict) or not row.get("id") or row.get("evidence") not in allowed
               or not row.get("standard") or not row.get("authority") or not row.get("threshold")
               or not row.get("on_fail") for row in rows):
            malformed.append(key)
    if missing or malformed:
        add(findings, "block", "逐阶段验收", rel(root, cpath),
            f"阶段标准缺失={missing or '无'}，证据类型/依据/阈值/回退异常={malformed or '无'}。",
            "为每阶段补 STAGE_CRITERIA 的 evidence/authority/standard/threshold/on_fail。")
        return

    required_files = (
        "skills/ad/ad-craft/scripts/stage_acceptance.py",
        "skills/ad/ad-review/scripts/human_signoff.py",
        "skills/ad/ad-feedback/scripts/experiment_plan.py",
    )
    absent = [path for path in required_files if not (root / path).is_file()]
    consumers = {
        "skills/ad/ad-craft/scripts/progress_set.py": "stage_acceptance.py",
        "skills/ad/ad-image/scripts/render_dreamina.py": "stage_acceptance.py",
        "skills/ad/ad-video/scripts/render_dreamina.py": "stage_acceptance.py",
        "skills/ad/ad-compose/compose.sh": "stage_acceptance.py",
    }
    bypassed = [path for path, token in consumers.items()
                if (root / path).is_file() and token not in text(root / path)]
    profiles = getattr(contract, "DELIVERY_PROFILE", {})
    profile_bad = [name for name, row in profiles.items()
                   if not isinstance(row, dict) or not row.get("authority") or not row.get("source")]
    if not callable(getattr(contract, "resolve_delivery_profile", None)):
        profile_bad.append("resolve_delivery_profile()")
    if not isinstance(getattr(contract, "HOUSE_MASTER_PROFILE", None), dict):
        profile_bad.append("HOUSE_MASTER_PROFILE")
    if absent or bypassed or profile_bad:
        add(findings, "block", "逐阶段验收", ", ".join(absent + bypassed) or rel(root, cpath),
            f"验收脚本缺失={absent or '无'}；完成/付费入口旁路={bypassed or '无'}；交付标准无权威来源={profile_bad or '无'}。",
            "恢复统一 stage_acceptance；进度 ✅ 与 image/video/compose 入口必须消费；每个 delivery profile 标 authority/source。")
    else:
        add(findings, "info", "逐阶段验收", "skills/ad/ad-craft/scripts/stage_acceptance.py",
            f"{len(keys)} 个阶段均有带证据类型的标准；手工完成和付费入口无验收旁路，人工签收/实验预注册已落地。")


def check_final_release_evidence_architecture(root: Path, findings: List[Finding]) -> None:
    """P0/P1 final-file evidence must be executable, connected and regression-tested."""
    contract, error = load_contract(root)
    if error or contract is None or not getattr(contract, "AD_STAGE_TABLE", None):
        add(findings, "info", "最终交付证据链", "skills/ad/ad-craft/scripts/contract.py",
            "旧版/极简契约未声明阶段表，跳过最终交付证据链架构检查。")
        return
    required = (
        "skills/ad/ad-craft/scripts/migrate_project.py",
        "skills/ad/ad-craft/scripts/locale_matrix.py",
        "skills/ad/ad-craft/scripts/release_variant_manifest.py",
        "skills/ad/ad-craft/scripts/dependency_graph.py",
        "skills/ad/ad-compose/rendered_text_qc.py",
        "skills/ad/ad-compose/provenance_qc.py",
        "skills/ad/ad-voice/asr_consistency.py",
        "skills/ad/ad-review/scripts/final_media_consistency.py",
        "skills/ad/ad-craft/scripts/test_golden_project.py",
    )
    absent = [path for path in required if not (root / path).is_file()]
    consumers = {
        "skills/ad/ad-compose/deliver.py": ("rendered_text_qc", "asr_consistency", "provenance_qc", "accessibility_qc"),
        "skills/ad/ad-craft/scripts/compliance_manifest.py": ("locale_matrix", "release_variant_manifest", "provenance_qc"),
        "skills/ad/ad-craft/scripts/progress_set.py": ("dependency_graph.accept_stage",),
        "skills/ad/ad-review/scripts/consistency_findings.py": ("final_media_consistency",),
        "skills/ad/ad-review/scripts/human_signoff.py": ("final_contact_sheets", "evidence_sha256"),
    }
    bypassed = []
    for path, tokens in consumers.items():
        raw = text(root / path)
        if not raw or any(token not in raw for token in tokens):
            bypassed.append(path)
    criteria = getattr(contract, "STAGE_CRITERIA", {}) or {}
    criterion_ids = {str(row.get("id")) for rows in criteria.values() for row in (rows or []) if isinstance(row, dict)}
    required_criteria = {"rendered_text_delivery", "asr_delivery", "locale_release", "variant_release",
                         "provenance_release", "dependency_lineage"}
    missing_criteria = sorted(required_criteria - criterion_ids)
    if absent or bypassed or missing_criteria:
        add(findings, "block", "最终交付证据链", ", ".join(absent + bypassed) or "skills/ad/ad-craft/scripts/contract.py",
            f"脚本缺失={absent or '无'}；调度旁路={bypassed or '无'}；阶段标准缺失={missing_criteria or '无'}。",
            "恢复 migration/locale/release variant/final pixel/ASR/provenance/contact sheet/dependency graph，"
            "并让 deliver/compliance/review/progress 与 golden project 测试实际消费。")
    else:
        add(findings, "info", "最终交付证据链", "skills/ad/ad-craft/scripts/test_golden_project.py",
            "旧项目迁移、locale、逐交付 SHA、最终像素、ASR、实际 provenance、contact sheet 与依赖哈希图均已接入且有全阶段 golden 回归。")


# ── 编排 + 渲染 ──────────────────────────────────────────────────────────────

def audit(root: Path) -> Dict[str, Any]:
    root = root.resolve()
    findings: List[Finding] = []
    check_ad_law_single_entry(root, findings)
    check_delivery_specs_external(root, findings)
    check_image_backend_docs(root, findings)
    check_image_model_channel_split(root, findings)
    check_ai_usage_disclosure(root, findings)
    check_choice_point_catalog(root, findings)
    check_paid_runner_gates(root, findings)
    check_demo_literals(root, findings)
    check_release_order_and_evidence(root, findings)
    check_stage_acceptance_architecture(root, findings)
    check_final_release_evidence_architecture(root, findings)
    counts = {sev: sum(1 for item in findings if item["sev"] == sev) for sev in ("block", "warn", "info")}
    return {
        "kind": "ad_self_audit",
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "root": str(root),
        "counts": counts,
        "findings": findings,
        "ready_for_market_scan": counts["block"] == 0 and counts["warn"] == 0,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    ready = "是 ✅（可进入联网市场对标）" if report["ready_for_market_scan"] else "否（先修 block/warn）"
    lines = [
        "# 拍广告 流程自审（本地静态）",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- 仓库：`{report['root']}`",
        f"- 统计：block {report['counts']['block']} · warn {report['counts']['warn']} · info {report['counts']['info']}",
        f"- 进入市场对标：{ready}",
        "",
        "| sev | 维度 | 位置 | 问题 | 建议 |",
        "|---|---|---|---|---|",
    ]
    for item in report["findings"]:
        lines.append(
            "| {sev} | {dim} | `{loc}` | {msg} | {suggestion} |".format(
                sev=item["sev"], dim=item["dim"], loc=item["loc"],
                msg=str(item["msg"]).replace("|", "/"),
                suggestion=str(item.get("suggestion") or "").replace("|", "/"),
            )
        )
    return "\n".join(lines) + "\n"


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Report-only local self-audit for ad-* skills (模式② 第0步)")
    ap.add_argument("--root", default=str(repo_root_from_here()), help="repo root")
    ap.add_argument("--json", action="store_true", help="print JSON report")
    return ap


def main(argv: Sequence[str]) -> int:
    ns = parser().parse_args(argv)
    report = audit(Path(ns.root))
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report), end="")
    return 1 if report["counts"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
