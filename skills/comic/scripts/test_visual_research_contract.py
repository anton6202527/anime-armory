#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import visual_research_contract as contract


def complete_contract() -> dict:
    return {
        "schema_version": 1,
        "kind": "comic_visual_research",
        "status": "complete",
        "scope": "北宋末年龙虎山与汴京，第1话洪太尉故事范围",
        "project_style_anchor_id": "STYLE_SONG_CINEMATIC",
        "sources": [
            {
                "source_id": "FILM_CCTV_1998",
                "title": "电视剧《水浒传》官方专页",
                "url": "https://example.gov.cn/film/shuihu",
                "provider": "官方播出机构",
                "accessed_at": "2026-07-14",
                "type": "film_tv_narrative",
                "usage_boundary": "research_only",
                "findings": ["群像叙事以阶层、道具与场面调度区分人物"],
            },
            {
                "source_id": "MUSEUM_SCROLL",
                "title": "北宋风俗画",
                "url": "https://museum.example.org/scroll",
                "provider": "国家博物馆",
                "accessed_at": "2026-07-14",
                "type": "museum_primary",
                "usage_boundary": "research_only",
                "findings": ["散点透视和人物尺度序列用于竖向步移景异"],
            },
            {
                "source_id": "INSTITUTION_COSTUME",
                "title": "宋代服饰藏品",
                "url": "https://institute.example.edu/costume",
                "provider": "权威文博机构",
                "accessed_at": "2026-07-14",
                "type": "institution_primary",
                "usage_boundary": "research_only",
                "findings": ["冠帽、领型与材质先服务身份和阶层可读性"],
            },
        ],
        "derived_style": {
            "summary": "宋画散点空间与电影级人物覆盖结合的低饱和彩色国漫",
            "decisions": [
                {
                    "dimension": "character",
                    "decision": "用脸型、体态和阶层道具区分角色，不追演员脸",
                    "evidence_source_ids": ["FILM_CCTV_1998", "INSTITUTION_COSTUME"],
                },
                {
                    "dimension": "composition",
                    "decision": "竖向长图用散点透视建立步移景异节奏",
                    "evidence_source_ids": ["MUSEUM_SCROLL"],
                },
                {
                    "dimension": "costume_class",
                    "decision": "领型、帽式与材质服务身份可读性，不照搬影视组合",
                    "evidence_source_ids": ["INSTITUTION_COSTUME"],
                },
            ],
            "do_not_copy": ["演员脸与剧照构图", "单一影视版本的整套服饰"],
        },
        "rights_rules": {
            "research_only": True,
            "no_actor_likeness_direct_anchor": True,
            "no_film_still_as_generation_reference": True,
            "no_specific_composition_replication": True,
            "no_costume_combination_replication": True,
            "only_licensed_or_open_assets_in_generation": True,
            "notes": ["只保存文本发现"],
        },
    }


def test_complete_contract_passes_strict_minimum() -> None:
    report = contract.validate_contract(complete_contract())
    assert report["valid"] is True
    assert report["strict_valid"] is True
    assert report["network_accessed"] is False
    assert report["counts"]["film_tv_narrative"] == 1
    assert report["counts"]["institutional_primary"] == 2


def test_validator_blocks_missing_mix_actor_rule_and_attachment() -> None:
    data = complete_contract()
    data["sources"] = data["sources"][:1]
    data["sources"][0]["image_path"] = "剧照.png"
    data["rights_rules"]["no_actor_likeness_direct_anchor"] = False
    report = contract.validate_contract(data)
    codes = {item["code"] for item in report["issues"]}
    assert report["valid"] is False
    assert "primary_references_insufficient" in codes
    assert "source_attachment_forbidden" in codes
    assert "rights_no_actor_likeness_direct_anchor_required" in codes


def test_scaffold_reads_stable_project_style_anchor_without_network(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    root.mkdir()
    (root / "_设置.md").write_text("# 设置\n- 风格锚: STYLE_SONG_CINEMATIC\n", encoding="utf-8")
    data = contract.default_contract(root)
    assert data["project_style_anchor_id"] == "STYLE_SONG_CINEMATIC"
    assert all(source["usage_boundary"] == "research_only" for source in data["sources"])
    assert all(not any(key in source for key in contract.FORBIDDEN_ATTACHMENT_KEYS) for source in data["sources"])


def test_cli_scaffold_never_overwrites_existing_contract(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    path = root / contract.CONTRACT_RELATIVE_PATH
    path.parent.mkdir(parents=True)
    original = complete_contract()
    path.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
    assert contract.main([str(root), "scaffold", "--write", "--json"]) == 0
    assert json.loads(path.read_text(encoding="utf-8")) == original
