# coding: utf-8
"""cd skills/novel-wiki/scripts && python3 -m pytest test_alias_scaffold.py"""
import os
import json
import tempfile

import alias_scaffold as als
import graph_sentry as gs


def _mk(root, rel, text):
    os.makedirs(os.path.join(root, os.path.dirname(rel)), exist_ok=True)
    with open(os.path.join(root, rel), "w", encoding="utf-8") as f:
        f.write(text)


def test_parse_card_aliases_blocks():
    with tempfile.TemporaryDirectory() as root:
        _mk(root, "设定/角色卡.md",
            "### 沈念\n- 身份：女主\n- 封号：林贵妃、贵妃娘娘\n\n### 萧决\n- 别称：摄政王\n")
        out = als.parse_card_aliases(root)
        assert set(out["沈念"]) == {"林贵妃", "贵妃娘娘"}
        assert out["萧决"] == ["摄政王"]


def test_scaffold_writes_draft_and_no_overwrite():
    with tempfile.TemporaryDirectory() as root:
        _mk(root, "设定/角色卡.md", "### 沈念\n- 封号：林贵妃\n")
        res = als.scaffold(root)
        assert res["written"] and res["status"] == "draft"
        data = json.load(open(os.path.join(root, "设定", "角色别名.json"), encoding="utf-8"))
        assert data["status"] == "draft"
        assert data["character_aliases"]["林贵妃"] == "沈念"
        # 二次调用不覆盖
        res2 = als.scaffold(root)
        assert res2["written"] is False
        # --force 重建
        assert als.scaffold(root, force=True)["written"] is True


def test_curated_alias_only_when_confirmed():
    with tempfile.TemporaryDirectory() as root:
        _mk(root, "设定/角色别名.json", json.dumps(
            {"status": "draft", "character_aliases": {"林贵妃": "沈念"}}, ensure_ascii=False))
        assert gs.load_curated_alias_map(root) == {}   # draft 不喂硬闸
        _mk(root, "设定/角色别名.json", json.dumps(
            {"status": "confirmed", "character_aliases": {"林贵妃": "沈念"}}, ensure_ascii=False))
        m = gs.load_curated_alias_map(root)
        assert m["林贵妃"] == "沈念" and m["沈念"] == "沈念"


def test_confirmed_alias_closes_lifecycle_gate_hole():
    # 死亡记在本名「沈念」、复现记在封号「林贵妃」→ 无别名表漏判；确认别名表后硬闸抓到。
    with tempfile.TemporaryDirectory() as root:
        ledger = {"chapter_deltas": {
            "第10章": {"character_changes": [{"name": "沈念", "event": "death"}]},
            "第20章": {"character_changes": [{"name": "林贵妃", "event": "appear"}]},
        }}
        _mk(root, "审稿/state_ledger.json", json.dumps(ledger, ensure_ascii=False))
        # 无别名表：两 key 分离，漏判
        assert gs.detect_lifecycle_conflicts(ledger) == []
        # 确认别名表 → resolved_alias_map 归一 → 抓到复活矛盾
        _mk(root, "设定/角色别名.json", json.dumps(
            {"status": "confirmed", "character_aliases": {"林贵妃": "沈念"}}, ensure_ascii=False))
        amap = gs.resolved_alias_map(root, ledger)
        conflicts = gs.detect_lifecycle_conflicts(ledger, alias_map=amap)
        assert len(conflicts) == 1
        assert conflicts[0]["type"] == "deceased_ledger_reactivation"
        assert conflicts[0]["entity"] == "沈念"


def test_scaffold_empty_project_graceful():
    with tempfile.TemporaryDirectory() as root:
        res = als.scaffold(root)
        assert res["written"] and res["candidate_aliases"] == 0


def test_cooccurrence_clusters_are_draft_only_candidates():
    with tempfile.TemporaryDirectory() as root:
        _mk(root, "设定/角色卡.md", "### 沈念\n- 身份：女主\n\n### 萧决\n- 身份：男主\n")
        _mk(root, "章节/第01章.md",
            "# 第01章\n沈念独自站在廊下，林贵妃抬手扶住玉簪。\n"
            "沈念听见脚步声，林贵妃没有回头。\n"
            "沈念合上窗，林贵妃把密信藏进袖中。\n")
        clusters = als.cooccurrence_clusters(root)
        assert clusters
        c = clusters[0]
        assert c["suggested_canonical"] == "沈念"
        assert "林贵妃" in c["members"]
        res = als.scaffold(root)
        assert res["written"]
        data = json.load(open(os.path.join(root, "设定", "角色别名.json"), encoding="utf-8"))
        assert data["candidate_clusters"]
        # 共现候选不自动进入 flat 硬闸映射，仍需人确认后手动并入。
        assert "林贵妃" not in data["character_aliases"]
