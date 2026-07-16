#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import research_pack


def _project():
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    os.makedirs(os.path.join(root, "设定"), exist_ok=True)
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "测试书", "purpose": "商业连载", "target_platform": "番茄"}, f, ensure_ascii=False)
    with open(os.path.join(root, "设定", "章纲.md"), "w", encoding="utf-8") as f:
        f.write("- 第 03 章 《急诊夜》 — 主角在医院急诊协助抢救\n")
    return root


def test_scaffold_writes_pack_and_check_passes():
    root = _project()
    args = type("Args", (), {
        "topic": "急诊抢救",
        "domain": "medical",
        "chapters": "3",
        "risk": "high",
        "status": "ready",
        "freshness_days": 90,
        "keyword": ["急诊"],
        "source": ["国家急诊指南|2026-01-02|official|high|https://example.test/er|测试来源"],
        "claim": ["急诊分诊先评估生命体征|SRC-001|high|3|写抢救流程前置判断||不得写成先问私情"],
        "uncertain": [],
        "forbidden": ["不要把急诊写成无人分诊直接手术"],
    })()
    result = research_pack.scaffold(os.path.abspath(root), args)
    assert os.path.exists(result["pack_path"])
    assert os.path.exists(os.path.join(root, "资料", "research_sources.json"))

    report = research_pack.check_project(root, chapter=3, write=True)
    assert report["blocking"] == 0
    assert report["packs_checked"][0]["topic"] == "急诊抢救"
    assert os.path.exists(os.path.join(root, "审稿", "research_fact_support.json"))
    with open(os.path.join(root, "资料", "research_sources.json"), encoding="utf-8") as f:
        index = json.load(f)
    source = index["packs"][0]["sources"][0]
    assert set(source["evaluation"]) >= {"currency", "relevance", "authority", "accuracy", "purpose"}


def test_check_blocks_high_risk_chapter_without_ready_pack():
    root = _project()
    with open(os.path.join(root, "章节", "第03章.md"), "w", encoding="utf-8") as f:
        f.write("# 第3章 急诊夜\n医生在医院急诊进行抢救和用药。\n")
    report = research_pack.check_project(root, chapter=3, write=False)
    assert report["blocking"] >= 1
    assert any(item["type"] == "missing_research_pack" for item in report["alerts"])


def test_research_needs_writes_missing_and_ready_domains():
    root = _project()
    with open(os.path.join(root, "章节", "第03章.md"), "w", encoding="utf-8") as f:
        f.write("# 第3章 急诊夜\n医生在医院急诊进行抢救和用药。\n")

    needs = research_pack.build_research_needs(root, chapter=3, write=True)
    assert needs["blocking_count"] >= 1
    assert any(item["domain"] == "medical" for item in needs["needs"])
    assert os.path.exists(os.path.join(root, "资料", "research_needs.json"))
    assert os.path.exists(os.path.join(root, "资料", "research_needs.md"))

    args = type("Args", (), {
        "topic": "急诊抢救",
        "domain": "medical",
        "chapters": "3",
        "risk": "high",
        "status": "ready",
        "freshness_days": 90,
        "keyword": ["急诊"],
        "source": ["国家急诊指南|2026-01-02|official|high|https://example.test/er|测试来源"],
        "claim": ["急诊分诊先评估生命体征|SRC-001|high|3|写抢救流程前置判断||不得写成先问私情"],
        "uncertain": [],
        "forbidden": [],
    })()
    research_pack.scaffold(os.path.abspath(root), args)
    covered = research_pack.build_research_needs(root, chapter=3, write=False)
    medical = next(item for item in covered["needs"] if item["domain"] == "medical")
    assert medical["severity"] == "ready"


def test_research_jobs_turn_needs_into_actionable_tasks():
    root = _project()
    with open(os.path.join(root, "章节", "第03章.md"), "w", encoding="utf-8") as f:
        f.write("# 第3章 急诊夜\n医生在医院急诊进行抢救和用药。\n")

    jobs = research_pack.build_research_jobs(root, chapter=3, write=True)
    assert jobs["kind"] == "novel_research_jobs"
    assert jobs["blocking_count"] >= 1
    assert any(job["domain"] == "medical" and job["status"] == "open" for job in jobs["jobs"])
    assert "scaffold" in jobs["jobs"][0]["suggested_command"]
    assert os.path.exists(os.path.join(root, "资料", "research_needs.json"))
    assert os.path.exists(os.path.join(root, "资料", "research_jobs.json"))
    assert os.path.exists(os.path.join(root, "资料", "research_jobs.md"))


def test_research_job_update_preserves_status_across_regeneration():
    root = _project()
    with open(os.path.join(root, "章节", "第03章.md"), "w", encoding="utf-8") as f:
        f.write("# 第3章 急诊夜\n医生在医院急诊进行抢救和用药。\n")
    jobs = research_pack.build_research_jobs(root, chapter=3, write=True)
    job_id = jobs["jobs"][0]["id"]

    updated = research_pack.update_research_job(
        root,
        job_id,
        status="in_progress",
        assignee="researcher-a",
        source_count=2,
        notes="正在核验急诊指南。",
    )
    assert updated["status"] == "in_progress"
    assert updated["assignee"] == "researcher-a"
    assert updated["source_count"] == 2

    regenerated = research_pack.build_research_jobs(root, chapter=3, write=True)
    same = next(job for job in regenerated["jobs"] if job["id"] == job_id)
    assert same["status"] == "in_progress"
    assert same["assignee"] == "researcher-a"
    assert same["source_count"] == 2


def test_required_domain_blocks_even_without_keyword_hit():
    root = _project()
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "测试书", "research_required_domains": ["legal"]}, f, ensure_ascii=False)

    report = research_pack.check_project(root, write=False)
    assert report["required_domains"] == ["legal"]
    assert report["blocking"] >= 1
    assert any(item["type"] == "missing_required_research_pack" for item in report["alerts"])


def test_check_flags_incomplete_ready_pack():
    root = _project()
    os.makedirs(os.path.join(root, "资料"), exist_ok=True)
    payload = {
        "schema_version": 1,
        "kind": "novel_research_sources",
        "packs": [{
            "topic": "法律庭审",
            "topic_slug": "法律庭审",
            "domain": "legal",
            "risk_level": "high",
            "status": "ready",
            "pack_path": "资料/专业资料包_法律庭审.md",
            "applicable_chapters": ["all"],
            "keywords": ["法院"],
            "updated_at": "2026-01-01",
            "freshness_days": 90,
            "sources": [{"id": "SRC-001", "title": "无日期来源", "reliability": ""}],
            "claims": [{"id": "FACT-001", "claim": "庭审需要证据质证", "source_ids": [], "confidence": "high"}],
        }],
    }
    with open(os.path.join(root, "资料", "research_sources.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    with open(os.path.join(root, "章节", "第04章.md"), "w", encoding="utf-8") as f:
        f.write("# 第4章 法院\n律师在法院出示证据。\n")

    report = research_pack.check_project(root, chapter=4, write=False)
    types = {item["type"] for item in report["alerts"]}
    assert "source_missing_date" in types
    assert "source_missing_reliability" in types
    assert "claim_missing_source" in types
    assert report["blocking"] >= 3


def test_check_blocks_high_risk_pack_missing_updated_at():
    root = _project()
    os.makedirs(os.path.join(root, "资料"), exist_ok=True)
    with open(os.path.join(root, "资料", "专业资料包_金融风控.md"), "w", encoding="utf-8") as f:
        f.write("# 专业资料包：金融风控\n")
    payload = {
        "schema_version": 1,
        "kind": "novel_research_sources",
        "packs": [{
            "topic": "金融风控",
            "topic_slug": "金融风控",
            "domain": "finance",
            "risk_level": "high",
            "status": "ready",
            "pack_path": "资料/专业资料包_金融风控.md",
            "applicable_chapters": ["all"],
            "keywords": ["风控"],
            "freshness_days": 90,
            "sources": [{
                "id": "SRC-001",
                "title": "金融监管规则",
                "published_date": "2026-01-01",
                "accessed_date": "2026-01-02",
                "reliability": "high",
            }],
            "claims": [{
                "id": "FACT-001",
                "claim": "风控流程需要留痕",
                "source_ids": ["SRC-001"],
                "confidence": "high",
                "applicable_chapters": ["all"],
            }],
        }],
    }
    with open(os.path.join(root, "资料", "research_sources.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    report = research_pack.check_project(root, write=False)
    assert report["blocking"] >= 1
    assert any(item["type"] == "pack_missing_updated_at" for item in report["alerts"])


def test_refresh_audit_writes_project_plan_and_high_risk_tasks():
    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "创作区", "写小说", "项目A")
        os.makedirs(os.path.join(root, "资料"), exist_ok=True)
        with open(os.path.join(root, "资料", "专业资料包_急诊抢救.md"), "w", encoding="utf-8") as f:
            f.write("# 专业资料包：急诊抢救\n")
        payload = {
            "schema_version": 1,
            "kind": "novel_research_sources",
            "packs": [{
                "topic": "急诊抢救",
                "topic_slug": "急诊抢救",
                "domain": "medical",
                "risk_level": "high",
                "status": "ready",
                "pack_path": "资料/专业资料包_急诊抢救.md",
                "applicable_chapters": ["all"],
                "keywords": ["急诊", "抢救"],
                "updated_at": "2025-01-01",
                "freshness_days": 30,
                "sources": [{
                    "id": "SRC-001",
                    "title": "急诊指南",
                    "published_date": "2025-01-01",
                    "accessed_date": "2025-01-02",
                    "reliability": "high",
                }],
                "claims": [{
                    "id": "FACT-001",
                    "claim": "急诊分诊先评估生命体征",
                    "source_ids": ["SRC-001"],
                    "confidence": "high",
                    "applicable_chapters": ["all"],
                }],
            }],
        }
        with open(os.path.join(root, "资料", "research_sources.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)

        audit = research_pack.refresh_audit(tmp, write=True)
        plan_path = os.path.join(root, "资料", "research_refresh_plan.md")
        assert audit["project_count"] == 1
        assert audit["blocking"] == 1
        assert audit["high_risk_tasks"][0]["topic"] == "急诊抢救"
        assert os.path.exists(plan_path)
        text = open(plan_path, encoding="utf-8").read()
        assert "需实时深搜任务清单" in text
        assert "急诊抢救" in text


def test_scene_usage_maps_claims_to_scene_cards():
    root = _project()
    with open(os.path.join(root, "设定", "scene_cards.json"), "w", encoding="utf-8") as f:
        json.dump({
            "kind": "novel_scene_cards",
            "scenes": [{"id": "SC003-01", "chapter": 3, "scene_no": 1}],
        }, f, ensure_ascii=False)
    args = type("Args", (), {
        "topic": "急诊分诊",
        "domain": "medical",
        "chapters": "3",
        "risk": "high",
        "status": "ready",
        "freshness_days": 90,
        "keyword": ["急诊"],
        "source": ["急诊指南|2026-01-01|official|high|https://example.test|说明"],
        "claim": ["分诊先看生命体征|SRC-001|high|3|让护士阻止主角插队|不同医院流程可能不同|不要写成医生随意定生死"],
        "uncertain": [],
        "forbidden": [],
    })()
    research_pack.scaffold(os.path.abspath(root), args)
    report = research_pack.build_scene_usage(root, write=True)
    assert report["usage_count"] == 1
    usage = report["usages"][0]
    assert usage["scene_ids"] == ["SC003-01"]
    assert usage["dramatic_use"] == "让护士阻止主角插队"
    assert os.path.exists(os.path.join(root, "资料", "research_scene_usage.json"))


def test_pack_depth_gaps_flags_shallow_high_risk_pack():
    # 只覆盖"诊断"一个子面的医疗包 → 报出用药/操作/法律边界缺口（建议级，不硬阻断）。
    shallow = {
        "topic": "心梗处置", "domain": "medical", "status": "ready", "risk_level": "high",
        "sources": [{"id": "S1", "title": "t", "published_date": "2026-01-01",
                     "reliability": "high",
                     "evaluation": {a: "ok" for a in research_pack.SOURCE_EVALUATION_AXES}}],
        "claims": [{"id": "F1", "claim": "心梗的症状与诊断", "source_ids": ["S1"],
                    "confidence": "high", "applicable_chapters": "1-3"}],
        "updated_at": "2026-07-01",
    }
    gaps = research_pack.pack_depth_gaps(shallow)
    assert "用药/剂量" in gaps and "操作/流程" in gaps and "法律/伦理边界" in gaps
    from pathlib import Path
    findings = research_pack.validate_pack(Path("/tmp"), shallow)
    depth = [f for f in findings if f["type"] == "pack_depth_insufficient"]
    assert depth and depth[0]["severity"] == "建议级"


def test_pack_depth_gaps_empty_when_all_subtopics_covered():
    deep = {
        "topic": "急救", "domain": "medical", "status": "ready",
        "claims": [
            {"id": "F1", "claim": "诊断与鉴别"},
            {"id": "F2", "claim": "给药剂量与禁忌"},
            {"id": "F3", "claim": "急救操作流程"},
            {"id": "F4", "claim": "知情同意的法律边界"},
        ],
    }
    assert research_pack.pack_depth_gaps(deep) == []


def test_pack_depth_gaps_empty_for_unknown_domain():
    assert research_pack.pack_depth_gaps({"domain": "自定义奇幻", "claims": [{"claim": "x"}]}) == []


def test_scan_amateur_pitfalls_keyword_and_cooccurrence():
    hits = research_pack.scan_amateur_pitfalls("唐朝将军吃辣椒炒肉。", {"history": ["历史"]})
    assert any(h["evidence"] == "辣椒" and h["severity"] == "建议级" for h in hits)
    assert research_pack.scan_amateur_pitfalls("民事纠纷法院下令逮捕。", {"legal": ["民事"]})
    assert research_pack.scan_amateur_pitfalls("只是民事纠纷。", {"legal": ["民事"]}) == []


def test_scan_unsupported_professional_details():
    packs = [{"domain": "medical", "status": "ready", "claims": [{"claim": "心梗诊断要点"}]}]
    out = research_pack.scan_unsupported_professional_details(
        "医生用麻醉和ICU抢救，做出诊断。", packs, {"medical": ["麻醉", "ICU", "诊断"]})
    assert out and "麻醉" in out[0]["evidence"] and "诊断" not in out[0]["evidence"]
    assert research_pack.scan_unsupported_professional_details(
        "麻醉。", [{"domain": "medical", "status": "draft"}], {"medical": ["麻醉"]}) == []


def test_domain_freshness_default_applies_when_unset():
    # 平台包默认 30 天、历史包默认 1825 天；显式 freshness_days 优先。
    assert research_pack.pack_freshness({"domain": "platform", "updated_at": "2020-01-01"})["freshness_days"] == 30
    assert research_pack.pack_freshness({"domain": "history", "updated_at": "2020-01-01"})["freshness_days"] == 1825
    assert research_pack.pack_freshness({"domain": "platform", "freshness_days": 200, "updated_at": "2020-01-01"})["freshness_days"] == 200
    assert research_pack.domain_freshness_default("unlisted") == research_pack.DEFAULT_FRESHNESS_DAYS


def test_high_confidence_needs_authority_or_corroboration():
    import pathlib
    pack = {
        "topic": "T", "domain": "medical", "status": "ready", "pack_path": "资料/x.md",
        "applicable_chapters": ["all"], "updated_at": research_pack.today(), "freshness_days": 90,
        "sources": [{"id": "SRC-1", "title": "某论坛帖", "accessed_date": "2026-07-01", "reliability": "low",
                     "evaluation": {a: "ok" for a in research_pack.SOURCE_EVALUATION_AXES}}],
        "claims": [{"id": "FACT-1", "claim": "某高置信断言", "source_ids": ["SRC-1"], "confidence": "high",
                    "applicable_chapters": ["all"]}],
    }
    codes = [f["type"] for f in research_pack.validate_pack(pathlib.Path("/tmp"), pack)]
    assert "claim_confidence_unbacked" in codes
    # 换成 high 可信度来源后不再报
    pack["sources"][0]["reliability"] = "high"
    codes2 = [f["type"] for f in research_pack.validate_pack(pathlib.Path("/tmp"), pack)]
    assert "claim_confidence_unbacked" not in codes2


def test_new_domain_pitfalls_present_and_match():
    for dom in ("religion", "overseas", "technology", "career", "platform"):
        assert dom in research_pack.DOMAIN_PITFALLS and research_pack.DOMAIN_PITFALLS[dom]
    hits = research_pack.scan_amateur_pitfalls("他在美国警局出示身份证，警察愣了一下。", {"overseas": []})
    assert any("身份证" in h["evidence"] for h in hits)
