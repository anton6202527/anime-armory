# -*- coding: utf-8 -*-
"""防降级宪章守卫测试：宪章里锁定的硬闸，不允许在 gate.py 里被静默降档。

三层锁：
  ① 源码内省——每个 locked code 必须仍以 finding("block", ...) 字面量存在于 gate.py；
  ② AST 内省——creative_axis_findings 只准经 _advisory_report_findings 消费侧车
     （编剧轴永不直接产 block）；
  ③ 功能验证——advisory 降档、新鲜度 block、占位 VO 分阶段等结构性纪律实际行为不变。
要合法降档：先改 consistency_charter.py 里那一行（带日期理由），再改 gate.py——
让本测试的红灯变成显式审计决策。
"""
import ast
import json
import re
import time
from pathlib import Path

import consistency_charter
import gate

GATE_SRC = Path(gate.__file__).read_text(encoding="utf-8")

# gate.py 里所有以字面量出现的 block finding code（容忍多行/条件表达式写法）。
_BLOCK_CODE_RE = re.compile(r'finding\(\s*"block",\s*f?"([A-Za-z0-9_{}]+)"', re.S)
# 条件表达式写法：finding("block", "X" if cond else "Y", ...) 的第二分支也算。
_BLOCK_COND_RE = re.compile(r'finding\(\s*"block",\s*"[A-Za-z0-9_]+"\s+if\s+[^,]+else\s+"([A-Za-z0-9_]+)"', re.S)


def _block_codes_in_source():
    codes = set(_BLOCK_CODE_RE.findall(GATE_SRC))
    codes |= set(_BLOCK_COND_RE.findall(GATE_SRC))
    return codes


def test_every_locked_code_still_blocks_in_source():
    """宪章锁定的每个 code 必须仍以 block 字面量存在——被删/被降档立即红灯。"""
    present = _block_codes_in_source()
    missing = []
    for row in consistency_charter.LOCKED_BLOCK_CODES:
        if row["code"] in present:
            continue
        # 声明了合法条件化的行（如 verifier_coverage_missing 按阶段分档）：
        # 严重度由功能测试锁定，这里只要求 code 本身仍存在于 gate.py。
        if row.get("may_be_conditional") and f'"{row["code"]}"' in GATE_SRC:
            continue
        missing.append(row["code"])
    assert not missing, (
        f"以下宪章锁定的硬闸 code 已不再以 finding(\"block\", ...) 形式存在于 gate.py：{missing}。"
        "若是有意降档/移除，请先修改 consistency_charter.py 对应行（附日期与理由）。")


def test_charter_rows_are_wellformed():
    for row in consistency_charter.LOCKED_BLOCK_CODES:
        assert row.get("code") and row.get("where") and row.get("rationale") and row.get("decided"), row
    for inv in consistency_charter.INVARIANTS:
        assert inv.get("id") and inv.get("statement") and inv.get("decided"), inv


def test_freshness_stale_still_blocks_in_source():
    """干净但过期的硬闸报告不是证据——{code}_stale 必须保持 block。"""
    assert re.search(r'finding\(\s*"block",\s*f"\{code\}_stale"', GATE_SRC), (
        "report_freshness_findings 的 {code}_stale 不再是 block；宪章 invariant "
        "freshness_blocks_hard_reports 被破坏")


def _function_def(name):
    tree = ast.parse(GATE_SRC)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"gate.py 缺函数 {name}")


def test_creative_axis_never_emits_block_directly():
    """编剧轴只准经 _advisory_report_findings 降档消费——AST 级锁定。"""
    fn = _function_def("creative_axis_findings")
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            callee = getattr(node.func, "id", getattr(node.func, "attr", ""))
            if callee == "finding" and node.args:
                first = node.args[0]
                assert not (isinstance(first, ast.Constant) and first.value == "block"), (
                    "creative_axis_findings 内出现直接 finding(\"block\", ...)：编剧轴永不硬挡付费")
            if callee == "extend" and node.args:
                inner = node.args[0]
                if isinstance(inner, ast.Call):
                    inner_name = getattr(inner.func, "id", getattr(inner.func, "attr", ""))
                    assert inner_name == "_advisory_report_findings", (
                        f"creative_axis_findings 引入了非 advisory 通道：{inner_name}")


# ── 功能验证：结构性纪律实际行为 ───────────────────────────────────────────────

def _write(root: Path, rel: str, value):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def test_advisory_sidecar_block_never_escalates(tmp_path):
    _write(tmp_path, "生产数据/ad_reference_plan.json",
           {"schema_version": 1, "summary": {"block": 9, "warn": 0, "info": 0}, "findings": []})
    severities = {f["severity"] for f in gate.reference_plan_findings(str(tmp_path))}
    assert "block" not in severities


def test_score_reject_stays_advisory(tmp_path):
    _write(tmp_path, "评分/ad_score.json", {"tier": "reject"})
    severities = {f["severity"] for f in gate.score_findings(str(tmp_path))}
    assert severities == {"warn"}


def test_voice_placeholder_stage_rule(tmp_path):
    _write(tmp_path, "配音/时长清单.json", {"has_placeholder": True})
    by_stage = {stage: gate.voice_findings(str(tmp_path), stage)[0]["severity"]
                for stage in ("image", "video", "compose")}
    assert by_stage == {"image": "warn", "video": "block", "compose": "block"}
    assert gate.voice_findings(str(tmp_path), "compose", allow_placeholder=True)[0]["severity"] == "warn"


def test_verifier_coverage_wired_fail_closed(tmp_path):
    """覆盖账本：compose 缺账本 = block（交付点 fail-closed）；账本有 block 也必须抬成 block。"""
    findings = gate.verifier_coverage_findings(str(tmp_path), "compose")
    assert any(f["code"] == "verifier_coverage_missing" and f["severity"] == "block" for f in findings)
    assert any(f["code"] == "verifier_coverage_missing" and f["severity"] == "warn"
               for f in gate.verifier_coverage_findings(str(tmp_path), "video"))
    _write(tmp_path, "生产数据/ad_verifier_coverage.json",
           {"schema_version": 1, "summary": {"block": 2, "warn": 0, "info": 0}, "findings": []})
    findings = gate.verifier_coverage_findings(str(tmp_path), "compose")
    assert any(f["code"] == "verifier_coverage_block" and f["severity"] == "block" for f in findings)
