#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""draft_packets.py contract tests.

Can run without pytest:
    python3 skills/novel/novel-craft/scripts/test_draft_packets.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT_PACKETS = os.path.join(HERE, "draft_packets.py")


def make_project(root, *, demo=True):
    os.makedirs(os.path.join(root, "设定"), exist_ok=True)
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "kind": "create",
            "title": "测试新书",
            "purpose": "传统小说",
            "rights_status": "original",
            "outputs": ["txt"],
            "scale": "medium",
            "target_chapters": 5,
            "target_words_per_chapter": [3000, 5000],
            "demo_chapters": 2,
            "person": "third-limited",
            "target_platform": "番茄",
        }, f, ensure_ascii=False)
    for name in ("创作蓝图.md", "设定圣经.md", "角色卡.md", "世界观.md"):
        with open(os.path.join(root, "设定", name), "w", encoding="utf-8") as f:
            f.write(f"# {name}\n测试内容。\n")
    with open(os.path.join(root, "设定", "读者契约.md"), "w", encoding="utf-8") as f:
        f.write("# 读者契约\n核心题旨：代价换来的力量是否值得。\n")
    with open(os.path.join(root, "设定", "章纲.md"), "w", encoding="utf-8") as f:
        f.write("# 章纲\n- 第 01 章 《开局》 — 主角登场\n- 第 03 章 《转折》 — 发现代价\n")
    with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
        f.write("# 第1章 开局\n<!-- meta: demo=true -->\n上一章内容。\n")
    if demo:
        with open(os.path.join(root, "审稿", "demo_gate.json"), "w", encoding="utf-8") as f:
            json.dump({
                "schema_version": 1,
                "kind": "novel_demo_gate",
                "status": "passed",
                "style_anchor": {"source_chapter": "第01章", "summary": "短句强钩子"},
                "reader_promises": ["主角会付出代价"],
                "setting_constraints": ["能力不能无限用"],
                "banned_drift": ["不要流水账"],
                "reader_contract": {
                    "theme": "力量必须付出代价",
                    "dramatic_question": "主角是否愿意为守护他人承受反噬",
                    "must_answer": ["代价能否被承担"],
                    "reader_promises": ["代价会逐步升级"],
                    "aesthetic_register": "短句、有压迫感、动作细节强",
                    "delight_engine": ["每章让能力代价更尖锐"],
                    "banned_drift": ["不要写成无脑升级"],
                },
            }, f, ensure_ascii=False)


def make_kind_project(root, kind):
    os.makedirs(os.path.join(root, "设定"), exist_ok=True)
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "kind": kind,
            "title": "测试项目",
            "purpose": "漫剧源书",
            "rights_status": "user-declared",
            "outputs": ["txt"],
            "scale": "short",
            "target_chapters": 3,
            "target_words_per_chapter": [1000, 1500],
            "demo_chapters": 1,
            "target_platform": "红果",
        }, f, ensure_ascii=False)
    with open(os.path.join(root, "审稿", "demo_gate.json"), "w", encoding="utf-8") as f:
        json.dump({"schema_version": 1, "kind": "novel_demo_gate", "status": "passed"}, f, ensure_ascii=False)
    with open(os.path.join(root, "设定", "读者契约.md"), "w", encoding="utf-8") as f:
        f.write("# 读者契约\n核心题旨：代价换来的力量是否值得。\n")
    with open(os.path.join(root, "设定", "章纲.md"), "w", encoding="utf-8") as f:
        f.write("# 章纲\n- 第 02 章 《推进》 — 推进主线\n")
    with open(os.path.join(root, "原作.txt"), "w", encoding="utf-8") as f:
        f.write("第1章 原作\n原作内容。\n")
    for rel in (
        "设定/创作蓝图.md",
        "设定/设定圣经.md",
        "设定/角色卡.md",
        "设定/世界观.md",
        "设定/改动spec.md",
        "设定/新设定.md",
        "设定/锚点表.json",
        "设定/人物.md",
        "设定/主线骨架.json",
        "设定/末章状态.md",
        "设定/作者口吻.md",
        "设定/续写方向.md",
        "设定/事件骨架.json",
        "设定/章节映射.md",
    ):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {rel}\n")


class DraftPacketsTest(unittest.TestCase):
    def test_generates_packet_and_state_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            got = subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True, check=True,
            )
            packet = os.path.join(tmp, "写作任务", "第03章.md")
            ledger = os.path.join(tmp, "审稿", "state_ledger.json")
            self.assertIn("[ok] 写作任务包", got.stdout)
            self.assertTrue(os.path.exists(packet))
            self.assertTrue(os.path.exists(ledger))
            self.assertTrue(os.path.exists(os.path.join(tmp, "审稿", "state_ledger.lock")))
            self.assertFalse([name for name in os.listdir(os.path.join(tmp, "审稿")) if ".tmp." in name])
            with open(packet, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("第 03 章写作任务包", text)
            self.assertIn("小说用途：传统小说", text)
            self.assertIn("建议篇幅：3000-5000 字", text)
            self.assertIn("发现代价", text)
            self.assertIn("题旨与读者契约", text)
            self.assertIn("力量必须付出代价", text)
            self.assertIn("代价换来的力量是否值得", text)
            self.assertIn("状态增量模板", text)
            self.assertIn("reader_contract_progress", text)

    def test_settings_purpose_fills_packet_when_meta_missing_purpose(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            meta_path = os.path.join(tmp, "_meta.json")
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
            meta.pop("purpose", None)
            meta["draft_mode"] = "稳妥初稿"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False)
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n- 小说用途：漫剧源书\n")
            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3", "--step", "full"],
                capture_output=True, text=True, check=True,
            )
            packet = os.path.join(tmp, "写作任务", "第03章.md")
            with open(packet, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("小说用途：漫剧源书", text)
            self.assertIn("小说生成模式：漫剧源书", text)

    def test_auto_uses_trio_for_commercial_serial(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n- 小说生成模式：商业连载\n")
            got = subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True, check=True,
            )
            task_dir = os.path.join(tmp, "写作任务")
            self.assertIn("三步迭代顺序", got.stdout)
            self.assertTrue(os.path.exists(os.path.join(task_dir, "第03章_architect.md")))
            self.assertTrue(os.path.exists(os.path.join(task_dir, "第03章_ghostwriter.md")))
            self.assertTrue(os.path.exists(os.path.join(task_dir, "第03章_editor.md")))
            self.assertFalse(os.path.exists(os.path.join(task_dir, "第03章.md")))

    def test_auto_uses_trio_from_project_purpose_without_mode_setting(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            meta_path = os.path.join(tmp, "_meta.json")
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
            meta["draft_mode"] = "稳妥初稿"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False)
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n- 小说用途：漫剧源书\n")
            got = subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True, check=True,
            )
            task_dir = os.path.join(tmp, "写作任务")
            self.assertIn("三步迭代顺序", got.stdout)
            self.assertTrue(os.path.exists(os.path.join(task_dir, "第03章_architect.md")))
            self.assertTrue(os.path.exists(os.path.join(task_dir, "第03章_ghostwriter.md")))
            self.assertTrue(os.path.exists(os.path.join(task_dir, "第03章_editor.md")))
            self.assertFalse(os.path.exists(os.path.join(task_dir, "第03章.md")))

    def test_auto_uses_trio_for_long_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            meta_path = os.path.join(tmp, "_meta.json")
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
            meta["scale"] = "long"
            meta["target_chapters"] = 80
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False)
            got = subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True, check=True,
            )
            task_dir = os.path.join(tmp, "写作任务")
            self.assertIn("三步迭代顺序", got.stdout)
            self.assertTrue(os.path.exists(os.path.join(task_dir, "第03章_architect.md")))
            with open(os.path.join(task_dir, "第03章_architect.md"), encoding="utf-8") as f:
                text = f.read()
            self.assertIn("小说生成工作流：三步迭代（长篇/商业自动）", text)

    def test_explicit_default_single_overrides_long_trio_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            meta_path = os.path.join(tmp, "_meta.json")
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
            meta["scale"] = "long"
            meta["target_chapters"] = 80
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False)
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n- 小说生成工作流：默认单步\n")
            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True, check=True,
            )
            task_dir = os.path.join(tmp, "写作任务")
            self.assertTrue(os.path.exists(os.path.join(task_dir, "第03章.md")))
            self.assertFalse(os.path.exists(os.path.join(task_dir, "第03章_architect.md")))

    def test_explicit_full_overrides_trio_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n- 小说生成模式：漫剧源书\n")
            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3", "--step", "full"],
                capture_output=True, text=True, check=True,
            )
            task_dir = os.path.join(tmp, "写作任务")
            self.assertTrue(os.path.exists(os.path.join(task_dir, "第03章.md")))
            self.assertFalse(os.path.exists(os.path.join(task_dir, "第03章_architect.md")))

    def test_live_check_workflow_adds_post_write_loop(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n- 小说生成工作流：边写边自检\n- 小批回扫间隔：3章\n")
            got = subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True, check=True,
            )
            packet = os.path.join(tmp, "写作任务", "第03章.md")
            with open(packet, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("小说生成工作流：边写边自检", text)
            self.assertIn("边写边自检闭环", text)
            self.assertIn("skills/novel/scripts/post_write.py", text)
            self.assertIn("小批回扫修正点", text)
            self.assertIn("--range 1-3", text)
            self.assertIn("已选择 边写边自检", got.stdout)
            self.assertIn("每 3 章跑一次 novel-review", got.stdout)

    def test_action_scene_checklist_is_injected_from_outline(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            with open(os.path.join(tmp, "设定", "章纲.md"), "a", encoding="utf-8") as f:
                f.write("\n- 第 04 章 《巷战追杀》 — 主角被追杀，屋脊追逐中临阵突破并反杀\n")
            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "4"],
                capture_output=True, text=True, check=True,
            )
            packet = os.path.join(tmp, "写作任务", "第04章.md")
            with open(packet, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("`skills/novel/novel-craft/references/action-scenes.md`", text)
            self.assertIn("专项场景写作清单", text)
            self.assertIn("打斗/战斗", text)
            self.assertIn("追逐/逃亡", text)
            self.assertIn("升级/突破", text)
            self.assertIn("距离如何变化", text)
            self.assertIn("power_system_registry", text)
            self.assertIn("必须写入 `state_delta`", text)

    def test_research_pack_is_injected_for_applicable_chapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            os.makedirs(os.path.join(tmp, "资料"), exist_ok=True)
            research_index = {
                "schema_version": 1,
                "kind": "novel_research_sources",
                "packs": [{
                    "topic": "急诊抢救",
                    "topic_slug": "急诊抢救",
                    "domain": "medical",
                    "risk_level": "high",
                    "status": "ready",
                    "pack_path": "资料/专业资料包_急诊抢救.md",
                    "applicable_chapters": [3],
                    "keywords": ["急诊"],
                    "claims": [{"id": "FACT-001", "claim": "先评估生命体征", "source_ids": ["SRC-001"]}],
                    "uncertain_items": ["不同地区急救流程可能不同"],
                    "forbidden_items": ["不要写成无人分诊直接开刀"],
                }],
            }
            with open(os.path.join(tmp, "资料", "research_sources.json"), "w", encoding="utf-8") as f:
                json.dump(research_index, f, ensure_ascii=False)
            with open(os.path.join(tmp, "资料", "专业资料包_急诊抢救.md"), "w", encoding="utf-8") as f:
                f.write("# 专业资料包：急诊抢救\n")

            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True, check=True,
            )
            packet = os.path.join(tmp, "写作任务", "第03章.md")
            with open(packet, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("`资料/专业资料包_急诊抢救.md`", text)
            self.assertIn("专业资料包（自动命中）", text)
            self.assertIn("急诊抢救", text)
            self.assertIn("不要写成无人分诊直接开刀", text)

    def test_scene_usage_is_injected_for_chapter(self):
        # research_scene_usage.json 的 per-scene dramatic_use/forbidden_use 必须到达写章包——
        # 此前它产出后只被状态/存在性检查读过，从未注入写作端（数据流断点，2026-07 修）。
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            os.makedirs(os.path.join(tmp, "资料"), exist_ok=True)
            usage = {
                "schema_version": 1,
                "kind": "novel_research_scene_usage",
                "usages": [
                    {"pack_topic": "急诊抢救", "claim_id": "FACT-001",
                     "claim": "先评估生命体征再处置", "chapter": 3,
                     "scene_ids": ["S3-1"],
                     "dramatic_use": "让主角在混乱中先探颈动脉，与家属的催促形成冲突",
                     "forbidden_use": "不得写成跳过分诊直接开刀",
                     "uncertainty": ""},
                    {"pack_topic": "急诊抢救", "claim_id": "FACT-002",
                     "claim": "别章事实", "chapter": 9, "scene_ids": [],
                     "dramatic_use": "无关本章", "forbidden_use": ""},
                ],
            }
            with open(os.path.join(tmp, "资料", "research_scene_usage.json"), "w", encoding="utf-8") as f:
                json.dump(usage, f, ensure_ascii=False)

            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True, check=True,
            )
            packet = os.path.join(tmp, "写作任务", "第03章.md")
            with open(packet, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("本章专业事实用法（scene usage·自动命中）", text)
            self.assertIn("先探颈动脉", text)
            self.assertIn("不得写成跳过分诊直接开刀", text)
            self.assertIn("`资料/research_scene_usage.json`", text)
            self.assertNotIn("别章事实", text)   # 非本章条目不注入

    def test_ai_tic_ledger_is_injected_from_mechanical_findings(self):
        # 本书 AI 腔账单：既往 mechanical_findings 的机械文风惯犯必须回灌下一章任务包——
        # 检测在下游（审稿轮）而习惯在上游（写作轮），跨项目实证这类问题降 polish 后没人修。
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            os.makedirs(os.path.join(tmp, "审稿"), exist_ok=True)
            findings = {
                "schema_version": 1, "kind": "novel_mechanical_findings",
                "findings": [
                    {"chapter": 1, "severity": "🟢", "dim": "AI腔",
                     "msg": "排比三连段落偏多（6 段疑似），AI 习惯性排比——精简至必要修辞", "evidence": ""},
                    {"chapter": 2, "severity": "🟢", "dim": "AI腔",
                     "msg": "排比三连段落偏多（4 段疑似），AI 习惯性排比——精简至必要修辞", "evidence": ""},
                    {"chapter": 2, "severity": "🟢", "dim": "重复",
                     "msg": "破折号「——」过多（5.5/千字），AI 习惯用破折号代替逗号", "evidence": ""},
                    {"chapter": 1, "severity": "🟡", "dim": "字数",
                     "msg": "字数 800 低于下限", "evidence": ""},   # 非 AI 腔项不入账单
                ],
            }
            with open(os.path.join(tmp, "审稿", "mechanical_findings.json"), "w", encoding="utf-8") as f:
                json.dump(findings, f, ensure_ascii=False)

            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True, check=True,
            )
            packet = os.path.join(tmp, "写作任务", "第03章.md")
            with open(packet, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("本书 AI 腔账单", text)
            self.assertIn("排比三连", text)
            self.assertIn("破折号", text)
            self.assertNotIn("低于下限", text.split("本书 AI 腔账单")[1][:600])  # 非 AI 腔项不进账单

    def test_observation_packet_is_injected_for_chapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            os.makedirs(os.path.join(tmp, "写作任务"), exist_ok=True)
            with open(os.path.join(tmp, "写作任务", "观察素材_第03章.md"), "w", encoding="utf-8") as f:
                f.write("# 观察素材\n- 老旧楼道里，声控灯慢半拍亮起，灰尘在光柱里浮动。\n")

            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True, check=True,
            )
            packet = os.path.join(tmp, "写作任务", "第03章.md")
            with open(packet, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("`写作任务/观察素材_第03章.md`", text)
            self.assertIn("生活观察素材（逐章精选）", text)
            self.assertIn("声控灯慢半拍亮起", text)

    def test_aesthetic_bank_is_injected_as_transfer_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            with open(os.path.join(tmp, "设定", "aesthetic_bank.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "schema_version": 1,
                    "kind": "novel_aesthetic_bank",
                    "samples": [{
                        "sample_id": "AES-001",
                        "source_title": "项目Demo第1章",
                        "source_rights": "project-demo",
                        "dimensions": ["opening", "prose"],
                        "why_it_works": "用一个带羞耻感的动作先立人物困境。",
                        "transfer_rule": "先写行动中的人，再让环境细节折射处境。",
                        "anti_copy_note": "只迁移机制，不复用原句。",
                    }],
                }, f, ensure_ascii=False)

            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True, check=True,
            )
            packet = os.path.join(tmp, "写作任务", "第03章.md")
            with open(packet, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("`设定/aesthetic_bank.json`", text)
            self.assertIn("正向审美样本（迁移规则）", text)
            self.assertIn("先写行动中的人", text)
            self.assertIn("用一个带羞耻感的动作", text)

    def test_novelty_sample_prioritized_even_when_not_first(self):
        import draft_packets as dp
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "设定"))
            samples = [{"sample_id": f"AES-{i}", "source_title": f"工艺{i}",
                        "dimensions": ["prose"], "why_it_works": "x", "transfer_rule": "y"}
                       for i in range(5)]
            samples.append({"sample_id": "AES-NOV", "source_title": "新颖样本",
                            "dimensions": ["novelty"], "why_it_works": "设定新",
                            "why_it_is_new": "把金手指设成诅咒", "transfer_rule": "代价先行"})
            with open(os.path.join(tmp, "设定", "aesthetic_bank.json"), "w", encoding="utf-8") as f:
                json.dump({"kind": "novel_aesthetic_bank", "samples": samples}, f, ensure_ascii=False)
            sec, _refs = dp.aesthetic_bank_section(tmp)
            self.assertIn("AES-NOV", sec)          # 第6个样本仍被优先注入
            self.assertIn("🌟新颖度样本", sec)
            self.assertIn("把金手指设成诅咒", sec)  # why_it_is_new 渲染

    def test_reveal_confrontation_relationship_checklists_are_injected(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            with open(os.path.join(tmp, "设定", "章纲.md"), "a", encoding="utf-8") as f:
                f.write(
                    "\n- 第 05 章 《公堂掉马》 — 女主当众拿出血书证据链揭穿内鬼真实身份，"
                    "逼问皇叔背叛真相，男女主误会爆发后决裂却仍互相救场\n"
                )
            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "5"],
                capture_output=True, text=True, check=True,
            )
            packet = os.path.join(tmp, "写作任务", "第05章.md")
            with open(packet, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("`skills/novel/novel-craft/references/reveal-scenes.md`", text)
            self.assertIn("`skills/novel/novel-craft/references/confrontation-scenes.md`", text)
            self.assertIn("`skills/novel/novel-craft/references/relationship-scenes.md`", text)
            self.assertIn("揭示场景写作清单", text)
            self.assertIn("身份曝光/掉马", text)
            self.assertIn("真相揭示/证据揭穿", text)
            self.assertIn("对质/智斗场景写作清单", text)
            self.assertIn("公开对质/当众打脸", text)
            self.assertIn("审讯/逼问", text)
            self.assertIn("关系情绪场景写作清单", text)
            self.assertIn("决裂/误会爆发", text)
            self.assertIn("和解/救赎/互相救场", text)
            self.assertIn("关系温度", text)
            self.assertIn("必须写入 `state_delta`", text)

    def test_female_fiction_checklist_injected_for_romance_genre(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            meta_path = os.path.join(tmp, "_meta.json")
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
            meta["genre"] = "现代言情·先婚后爱"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False)
            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True, check=True,
            )
            packet = os.path.join(tmp, "写作任务", "第03章.md")
            with open(packet, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("女频情感写作清单", text)
            self.assertIn("`skills/novel/novel-craft/references/女频情感.md`", text)
            self.assertIn("情绪写颗粒度", text)
            self.assertIn("CP 关系温度只进不退", text)

    def test_female_fiction_checklist_gated_by_platform_setting(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n- 题材：豪门宫斗\n")
            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True, check=True,
            )
            packet = os.path.join(tmp, "写作任务", "第03章.md")
            with open(packet, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("女频情感写作清单", text)

    def test_female_fiction_checklist_absent_for_non_romance(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)  # default: 番茄 / 传统小说 / 无 genre
            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True, check=True,
            )
            packet = os.path.join(tmp, "写作任务", "第03章.md")
            with open(packet, encoding="utf-8") as f:
                text = f.read()
            self.assertNotIn("女频情感写作清单", text)
            self.assertNotIn("`skills/novel/novel-craft/references/女频情感.md`", text)

    def test_cast_arc_injected_when_arc_file_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            with open(os.path.join(tmp, "设定", "章纲.md"), "a", encoding="utf-8") as f:
                f.write("\n- 第 04 章 《林越的抉择》 — 林越被迫向同伴求助\n")
            with open(os.path.join(tmp, "设定", "角色弧光.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "schema_version": 1,
                    "characters": {
                        "林越": {
                            "role": "protagonist",
                            "function": "主角/复仇者",
                            "want": "夺回家族",
                            "need": "学会信任",
                            "lie": "强者不需要任何人",
                            "distinct_tag": "沉默，用刀不用话",
                            "arc_stages": [
                                {"by_chapter": 3, "stage": "固守谎言"},
                                {"by_chapter": 25, "stage": "谎言动摇：被迫依赖同伴"},
                            ],
                        }
                    },
                }, f, ensure_ascii=False)
            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "4"],
                capture_output=True, text=True, check=True,
            )
            with open(os.path.join(tmp, "写作任务", "第04章.md"), encoding="utf-8") as f:
                text = f.read()
            self.assertIn("在场角色弧光", text)
            self.assertIn("林越", text)
            self.assertIn("辨识度锚", text)
            # 第4章已过 by_chapter=3，应落到下一阶段 by_chapter=25
            self.assertIn("谎言动摇：被迫依赖同伴", text)
            self.assertIn("`skills/novel/novel-craft/references/群像与角色弧光.md`", text)

    def test_cast_distinctiveness_reminder_when_three_plus_on_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            with open(os.path.join(tmp, "设定", "章纲.md"), "a", encoding="utf-8") as f:
                f.write("\n- 第 04 章 《三方会谈》 — 林越、苏晚、赵狞三人当面摊牌\n")
            with open(os.path.join(tmp, "设定", "角色语感.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "林越": {"syntax_profile": {}, "lexicon_anchor": []},
                    "苏晚": {"syntax_profile": {}, "lexicon_anchor": []},
                    "赵狞": {"syntax_profile": {}, "lexicon_anchor": []},
                }, f, ensure_ascii=False)
            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "4"],
                capture_output=True, text=True, check=True,
            )
            with open(os.path.join(tmp, "写作任务", "第04章.md"), encoding="utf-8") as f:
                text = f.read()
            self.assertIn("群像辨识度提醒", text)
            self.assertIn("只有他会做的反应", text)

    def test_cast_arc_absent_when_no_file_and_few_chars(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)  # 默认 第03章 beat="发现代价"，无角色名、无弧光文件
            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True, check=True,
            )
            with open(os.path.join(tmp, "写作任务", "第03章.md"), encoding="utf-8") as f:
                text = f.read()
            self.assertNotIn("在场角色弧光", text)
            self.assertNotIn("群像辨识度提醒", text)

    def test_ledger_excerpt_is_canonical_focused(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            # 预置一个含逐章 blob 的账本：注入应给 canonical 状态、丢逐章大 blob
            with open(os.path.join(tmp, "审稿", "state_ledger.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "schema_version": 1, "kind": "novel_state_ledger",
                    "characters": {}, "setting_facts": ["金手指有代价_铁律X"],
                    "open_threads": [], "resolved_threads": [],
                    "chapter_deltas": {
                        "chapter_01": {"summary": {"notes": "逐章大blob唯一串_ZZZ"}},
                        "chapter_02": {"summary": {"notes": "another"}},
                    },
                }, f, ensure_ascii=False)
            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True, check=True,
            )
            with open(os.path.join(tmp, "写作任务", "第03章.md"), encoding="utf-8") as f:
                text = f.read()
            self.assertIn("金手指有代价_铁律X", text)      # canonical 设定事实保留
            self.assertIn("chapter_deltas_count", text)     # 逐章只给计数
            self.assertNotIn("逐章大blob唯一串_ZZZ", text)  # 不灌逐章 blob

    def test_blocks_without_demo_gate_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp, demo=False)
            got = subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("demo_gate.json", got.stderr)

    def test_blocks_without_reader_contract_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            os.remove(os.path.join(tmp, "设定", "读者契约.md"))
            got = subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("读者契约.md", got.stderr)

    def test_allow_missing_reader_contract_records_waiver(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            os.remove(os.path.join(tmp, "设定", "读者契约.md"))
            got = subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3", "--allow-missing-reader-contract"],
                capture_output=True, text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)

    def test_allow_missing_demo_records_waiver(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp, demo=False)
            got = subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3", "--allow-missing-demo"],
                capture_output=True, text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)
            packet = os.path.join(tmp, "写作任务", "第03章.md")
            with open(packet, encoding="utf-8") as f:
                packet_text = f.read()
            self.assertIn("显式豁免", packet_text)
            self.assertIn("missing_demo_gate", packet_text)
            waiver_log = os.path.join(tmp, "审稿", "waiver_log.jsonl")
            self.assertTrue(os.path.exists(waiver_log))
            with open(os.path.join(tmp, "审稿", "state_ledger.json"), encoding="utf-8") as f:
                ledger = json.load(f)
            self.assertEqual(ledger["waivers"][0]["type"], "missing_demo_gate")

    def test_next_skips_demo_chapters_and_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            with open(os.path.join(tmp, "章节", "第03章.md"), "w", encoding="utf-8") as f:
                f.write("# 第3章 转折\n正文。\n")
            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--next"],
                capture_output=True, text=True, check=True,
            )
            self.assertTrue(os.path.exists(os.path.join(tmp, "写作任务", "第04章.md")))

    def test_source_paths_follow_project_kind(self):
        cases = {
            "rewrite": (["设定/改动spec.md", "设定/新设定.md"], ["设定/创作蓝图.md", "设定/设定圣经.md"]),
            "spinoff": (["设定/锚点表.json", "原作.txt"], ["设定/创作蓝图.md", "设定/新设定.md"]),
            "continue": (["设定/末章状态.md", "设定/作者口吻.md", "设定/续写方向.md"], ["设定/创作蓝图.md"]),
            "expand": (["设定/事件骨架.json", "设定/章节映射.md"], ["设定/创作蓝图.md", "设定/新设定.md"]),
            "condense": (["设定/主线骨架.json", "设定/章节映射.md"], ["设定/创作蓝图.md", "设定/新设定.md"]),
        }
        for kind, (must_have, must_not_have) in cases.items():
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                make_kind_project(tmp, kind)
                got = subprocess.run(
                    [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "2", "--stdout"],
                    capture_output=True, text=True, check=True,
                )
                for path in must_have:
                    self.assertIn(f"`{path}`", got.stdout)
                self.assertIn("`设定/读者契约.md`", got.stdout)
                for path in must_not_have:
                    self.assertNotIn(f"`{path}`", got.stdout)
                self.assertIn("python3 skills/novel/novel-review/scripts/mechanical_check.py", got.stdout)


class RecentSeamAndForeshadowTest(unittest.TestCase):
    def _project(self, tmp, chapters):
        os.makedirs(os.path.join(tmp, "章节"), exist_ok=True)
        os.makedirs(os.path.join(tmp, "设定"), exist_ok=True)
        for i in range(1, chapters + 1):
            with open(os.path.join(tmp, "章节", f"第{i:02d}章.md"), "w", encoding="utf-8") as f:
                f.write(f"# 第{i}章\n" + f"第{i}章结尾发生关键事件{i}。" * 30)

    def test_recent_chapters_excerpt_covers_n_minus_2_and_3(self):
        import draft_packets as dp
        with tempfile.TemporaryDirectory() as tmp:
            self._project(tmp, 6)
            ex = dp.recent_chapters_excerpt(tmp, 6)
            self.assertIn("第05章", ex)   # N-1 全尾
            self.assertIn("第04章", ex)   # N-2 短尾（此前是黑洞）
            self.assertIn("第03章", ex)   # N-3 短尾
            self.assertNotIn("第02章", ex)  # near=3 之外不注入

    def test_foreshadow_ledger_injected_due_and_overdue(self):
        import draft_packets as dp
        with tempfile.TemporaryDirectory() as tmp:
            self._project(tmp, 10)
            json.dump({"kind": "novel_foreshadowing_ledger", "seeds": [
                {"id": "SEED_001", "description": "半块断剑", "status": "pending",
                 "confirmed": True, "expected_payoff_chapter": 8, "importance": "high",
                 "linked_entities": ["沈念", "断剑"]},
                {"id": "SEED_002", "description": "旧账早该收", "status": "pending",
                 "confirmed": True, "expected_payoff_chapter": 2, "importance": "medium"},
                {"id": "SEED_003", "description": "未确认候选", "status": "pending",
                 "confirmed": False, "expected_payoff_chapter": 10},
                {"id": "SEED_004", "description": "已回收", "status": "resolved",
                 "confirmed": True, "expected_payoff_chapter": 9},
            ]}, open(os.path.join(tmp, "设定", "foreshadowing_ledger.json"), "w", encoding="utf-8"),
                ensure_ascii=False)
            sec = dp.foreshadow_section_for_chapter(tmp, 10)
            self.assertIn("SEED_001", sec)          # 预期第8章±5 覆盖第10章 → due
            self.assertIn("SEED_002", sec)          # 第10 > 2+5 → overdue
            self.assertIn("超期", sec)
            self.assertNotIn("SEED_003", sec)       # 未确认不注入
            self.assertNotIn("SEED_004", sec)       # 已回收不注入

    def test_foreshadow_section_empty_without_ledger(self):
        import draft_packets as dp
        with tempfile.TemporaryDirectory() as tmp:
            self._project(tmp, 3)
            self.assertEqual(dp.foreshadow_section_for_chapter(tmp, 3), "")

    def _remind_ledger(self, tmp, description="半块断剑", entities=("断剑",)):
        json.dump({"kind": "novel_foreshadowing_ledger", "seeds": [
            {"id": "SEED_R01", "description": description, "status": "pending",
             "confirmed": True, "planted_chapter": 1, "expected_payoff_chapter": 30,
             "importance": "high", "linked_entities": list(entities)},
        ]}, open(os.path.join(tmp, "设定", "foreshadowing_ledger.json"), "w", encoding="utf-8"),
            ensure_ascii=False)

    def test_foreshadow_remind_bucket_flags_long_silent_seed(self):
        # 埋于第1章、预期第30章收，写第12章时中段正文零复现 → 该补提醒（rule of three 写作端）
        import draft_packets as dp
        with tempfile.TemporaryDirectory() as tmp:
            self._project(tmp, 11)
            self._remind_ledger(tmp)
            sec = dp.foreshadow_section_for_chapter(tmp, 12)
            self.assertIn("SEED_R01", sec)
            self.assertIn("零复现", sec)

    def test_foreshadow_remind_quiet_when_mentioned_midway(self):
        import draft_packets as dp
        with tempfile.TemporaryDirectory() as tmp:
            self._project(tmp, 11)
            with open(os.path.join(tmp, "章节", "第05章.md"), "a", encoding="utf-8") as f:
                f.write("\n他又摸了摸腰间的断剑。")
            self._remind_ledger(tmp)
            self.assertEqual(dp.foreshadow_section_for_chapter(tmp, 12), "")

    def test_foreshadow_remind_quiet_below_remind_every(self):
        # 埋下未满提醒周期（默认 8 章）→ 不催
        import draft_packets as dp
        with tempfile.TemporaryDirectory() as tmp:
            self._project(tmp, 5)
            self._remind_ledger(tmp)
            self.assertEqual(dp.foreshadow_section_for_chapter(tmp, 6), "")


class PredictedPlotSectionTest(unittest.TestCase):
    def _write_predictions(self, tmp, chapter, preds):
        os.makedirs(os.path.join(tmp, "评分"), exist_ok=True)
        json.dump({"schema_version": 1, "kind": "novel_reader_predictions",
                   "chapter": chapter, "predictions": preds},
                  open(os.path.join(tmp, "评分", f"reader_predictions_第{chapter:02d}章.json"),
                       "w", encoding="utf-8"), ensure_ascii=False)

    def test_injects_prev_chapter_predictions_as_negative_constraint(self):
        import draft_packets as dp
        with tempfile.TemporaryDirectory() as tmp:
            self._write_predictions(tmp, 9, [
                {"persona": "rookie", "text": "主角会当场反杀"},
                {"persona": "veteran", "text": "长老出手救场"},
            ])
            sec = dp.predicted_plot_section(tmp, 10)
            self.assertIn("已猜到的走向", sec)
            self.assertIn("主角会当场反杀", sec)
            self.assertIn("[veteran]", sec)

    def test_quiet_without_predictions_or_for_stale_chapter(self):
        import draft_packets as dp
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(dp.predicted_plot_section(tmp, 10), "")
            # 只有更早章的预测（对象是已写完的旧章）→ 不注入
            self._write_predictions(tmp, 5, [{"persona": "rookie", "text": "旧预测"}])
            self.assertEqual(dp.predicted_plot_section(tmp, 10), "")

    def test_quiet_when_predictions_empty_or_malformed(self):
        import draft_packets as dp
        with tempfile.TemporaryDirectory() as tmp:
            self._write_predictions(tmp, 9, [])
            self.assertEqual(dp.predicted_plot_section(tmp, 10), "")
            self._write_predictions(tmp, 9, [{"persona": "rookie"}, "怪东西"])
            self.assertEqual(dp.predicted_plot_section(tmp, 10), "")


if __name__ == "__main__":
    unittest.main()
