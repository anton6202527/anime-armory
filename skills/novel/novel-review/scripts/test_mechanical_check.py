"""novel-review 机检单测。从脚本自身目录跑：
    cd skills/novel/novel-review/scripts && python -m pytest test_mechanical_check.py

覆盖：纯函数（cjk_count / strip_quotes / build_shingles / body_of）+ 端到端 findings
（格式/字数/demo 豁免/章号缺重/标题对账/原文照搬开关）。
"""
import os, sys, json, subprocess, tempfile, shutil
import mechanical_check as mc

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "mechanical_check.py")

CLEAN = """# 第 1 章 《开端》
<!-- meta: demo=false -->
他推开门，屋里一片漆黑。
窗外的风卷着雪，远处传来钟声。
她说：「你终于来了。」
"""


def make_proj(tmp, chapters, *, outline=None, source=None, meta=None):
    """chapters: {filename: content}。"""
    root = os.path.join(tmp, "proj")
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    for fname, content in chapters.items():
        with open(os.path.join(root, "章节", fname), "w", encoding="utf-8") as f:
            f.write(content)
    if outline is not None:
        os.makedirs(os.path.join(root, "设定"), exist_ok=True)
        with open(os.path.join(root, "设定", "章纲.md"), "w", encoding="utf-8") as f:
            f.write(outline)
    if source is not None:
        with open(os.path.join(root, "原作.txt"), "w", encoding="utf-8") as f:
            f.write(source)
    if meta is not None:
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)
    return root


def run(root, *args):
    """跑机检，解析末尾 FINDINGS_JSON，返回 findings list。"""
    out = subprocess.run(
        [sys.executable, SCRIPT, root, *args],
        capture_output=True, text=True, cwd=HERE,
    )
    assert out.returncode == 0, out.stderr
    txt = out.stdout
    a = txt.index("<!-- FINDINGS_JSON") + len("<!-- FINDINGS_JSON")
    b = txt.index("FINDINGS_JSON -->")
    return json.loads(txt[a:b].strip())


def sev_dims(findings):
    return {(f["severity"], f["dim"]) for f in findings}


# ---------- 纯函数 ----------

def test_cjk_count_basic():
    assert mc.cjk_count("一二三") == 3
    assert mc.cjk_count("a1!，。") == 0  # 标点非 CJK 表意字


def test_strip_quotes_removes_paired_quote_content():
    # 引号内的"我"应被剥除，引号外的"我"保留
    s = "我走过去，她说「我等你很久了」，我笑了。"
    out = mc.strip_quotes(s)
    assert "等你很久" not in out
    assert out.count("我") == 2  # 引号外两个"我"


def test_build_shingles_window_and_membership():
    text = "甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥A B C"  # 含空白会被压掉
    sh = mc.build_shingles(text, n=24)
    stripped = "".join(text.split())
    # 任取一段连续 24 字必在 shingle 集合内（查重契约的基础）
    assert stripped[:24] in sh
    # 不足 24 字的文本 → 空集合
    assert mc.build_shingles("短", n=24) == set()


def test_chapter_sort_uses_numeric_order():
    paths = ["第10章.md", "第2章.md", "第01章.md"]
    ordered = sorted(paths, key=mc.chapter_sort_key)
    assert ordered == ["第01章.md", "第2章.md", "第10章.md"]


def test_body_of_strips_h1_and_meta():
    body = mc.body_of(CLEAN)
    assert "第 1 章" not in body
    assert "<!--" not in body
    assert "他推开门" in body


# ---------- 端到端 findings ----------

def test_clean_chapter_no_hard_findings():
    with tempfile.TemporaryDirectory() as t:
        root = make_proj(t, {"第1章_开端.md": CLEAN})
        f = run(root, "--min", "2", "--max", "200")
        assert all(x["severity"] != "🔴" for x in f), f
        assert all(x["dim"] != "字数" for x in f), f


def test_missing_h1_is_blocking():
    with tempfile.TemporaryDirectory() as t:
        bad = "第一章 开端\n<!-- m -->\n正文正文。\n"  # 没有 `# 第 N 章 《…》` 规范 H1
        root = make_proj(t, {"第1章.md": bad})
        f = run(root, "--min", "2", "--max", "200")
        assert ("🔴", "格式") in sev_dims(f), f


def test_wordcount_out_of_band():
    with tempfile.TemporaryDirectory() as t:
        root = make_proj(t, {"第1章_开端.md": CLEAN})
        f = run(root, "--min", "9000", "--max", "20000")  # 强制偏短
        assert ("🟡", "字数") in sev_dims(f), f


def test_wordcount_defaults_to_scale_metadata():
    with tempfile.TemporaryDirectory() as t:
        chapter = "# 第 1 章 《长篇》\n<!-- meta: demo=false -->\n" + ("风" * 4500) + "\n"
        root = make_proj(t, {"第1章.md": chapter}, meta={
            "schema_version": 1,
            "kind": "create",
            "scale": "long",
            "target_words_per_chapter": [5000, 8000],
        })
        f = run(root)
        assert ("🟡", "字数") not in sev_dims(f), f


def test_wordcount_defaults_to_target_words_without_scale():
    with tempfile.TemporaryDirectory() as t:
        chapter = "# 第 1 章 《中篇》\n<!-- meta: demo=false -->\n" + ("风" * 2600) + "\n"
        root = make_proj(t, {"第1章.md": chapter}, meta={
            "schema_version": 1,
            "kind": "expand",
            "target_words_per_chapter": [3000, 5000],
        })
        f = run(root)
        assert ("🟡", "字数") not in sev_dims(f), f


def test_wordcount_metadata_band_overrides_scale():
    with tempfile.TemporaryDirectory() as t:
        chapter = "# 第 1 章 《自定义》\n<!-- meta: demo=false -->\n" + ("风" * 900) + "\n"
        root = make_proj(t, {"第1章.md": chapter}, meta={
            "schema_version": 1,
            "kind": "create",
            "scale": "long",
            "target_wordcount_min_max": [800, 1800],
        })
        f = run(root)
        assert ("🟡", "字数") not in sev_dims(f), f


def test_demo_exempt_from_wordcount():
    with tempfile.TemporaryDirectory() as t:
        demo = CLEAN.replace("demo=false", "demo=true")
        root = make_proj(t, {"第1章_开端.md": demo})
        f = run(root, "--min", "9000", "--max", "20000")
        assert ("🟡", "字数") not in sev_dims(f), f


def test_chapter_gap_and_dup():
    with tempfile.TemporaryDirectory() as t:
        c = lambda n, ttl: f"# 第 {n} 章 《{ttl}》\n<!-- m -->\n正文。\n"
        # 章号 1,3 → 缺 2（🟡）；再放一个重复的 1（🔴）
        root = make_proj(t, {
            "第1章_a.md": c(1, "甲"),
            "第3章_c.md": c(3, "丙"),
            "第1章_dup.md": c(1, "甲二"),
        })
        f = run(root, "--min", "2", "--max", "200")
        dims = sev_dims(f)
        assert ("🟡", "章号") in dims, f
        assert ("🔴", "章号") in dims, f


def test_title_mismatch_vs_outline():
    with tempfile.TemporaryDirectory() as t:
        ch = "# 第 1 章 《错的标题》\n<!-- m -->\n正文。\n"
        outline = "# 章纲\n第 1 章 《正确标题》 —— 简介\n"
        root = make_proj(t, {"第1章.md": ch}, outline=outline)
        f = run(root, "--min", "2", "--max", "200")
        assert ("🟡", "标题") in sev_dims(f), f


def test_plagiarism_hit_and_toggle():
    src = "从前有座山山里有座庙庙里有个老和尚讲故事天黑了大家都睡了第二天太阳升起"
    with tempfile.TemporaryDirectory() as t:
        # 章节正文以原作前 24+ 字开头 → i=0 命中（查重契约：步进 6，偏移 0 必检）
        body = src[:30] + "，后面是原创内容继续写。"
        ch = f"# 第 1 章 《抄》\n<!-- m -->\n{body}\n"
        root = make_proj(t, {"第1章.md": ch}, source=src)
        f = run(root, "--min", "2", "--max", "500")
        assert ("🔴", "原文照搬") in sev_dims(f), f
        # 关闭查重 → 不报
        f2 = run(root, "--min", "2", "--max", "500", "--no-plagiarism")
        assert ("🔴", "原文照搬") not in sev_dims(f2), f2


def test_plagiarism_skips_import_or_canonical_source_projects():
    src = "从前有座山山里有座庙庙里有个老和尚讲故事天黑了大家都睡了第二天太阳升起"
    body = src[:30] + "，后面是同源拆章正文。"
    ch = f"# 第 1 章 《同源》\n<!-- m -->\n{body}\n"
    with tempfile.TemporaryDirectory() as t:
        root = make_proj(t, {"第1章.md": ch}, source=src, meta={"kind": "import"})
        f = run(root, "--min", "2", "--max", "500")
        assert ("🔴", "原文照搬") not in sev_dims(f), f
    with tempfile.TemporaryDirectory() as t:
        root = make_proj(t, {"第1章.md": ch}, source=src, meta={
            "kind": "rewrite",
            "review": {"plagiarism_check": "skip_canonical_source"},
        })
        f = run(root, "--min", "2", "--max", "500")
        assert ("🔴", "原文照搬") not in sev_dims(f), f


def test_plagiarism_still_runs_for_derivative_projects_by_default():
    src = "从前有座山山里有座庙庙里有个老和尚讲故事天黑了大家都睡了第二天太阳升起"
    body = src[:30] + "，后面是原创内容继续写。"
    ch = f"# 第 1 章 《抄》\n<!-- m -->\n{body}\n"
    with tempfile.TemporaryDirectory() as t:
        root = make_proj(t, {"第1章.md": ch}, source=src, meta={"kind": "rewrite"})
        f = run(root, "--min", "2", "--max", "500")
        assert ("🔴", "原文照搬") in sev_dims(f), f


def test_json_out_writes_machine_payload():
    with tempfile.TemporaryDirectory() as t:
        root = make_proj(t, {"第1章_开端.md": CLEAN})
        out_path = os.path.join(t, "mechanical_findings.json")
        f = run(root, "--min", "9000", "--max", "20000", "--json-out", out_path)
        assert os.path.exists(out_path)
        with open(out_path, encoding="utf-8") as fp:
            payload = json.load(fp)
        assert payload["schema_version"] == 1
        assert payload["kind"] == "novel_mechanical_findings"
        assert payload["findings"] == f
        assert payload["counts"]["🟡"] >= 1
        assert payload["wordcount_band"] == [9000, 20000]
        assert "cli_min" in payload["wordcount_band_source"]


def test_range_filters_chapters_and_records_scope():
    with tempfile.TemporaryDirectory() as t:
        c1 = "# 第 1 章 《一》\n<!-- m -->\n正文。\n"
        c2 = "第二章 二\n<!-- m -->\n正文。\n"
        c3 = "# 第 3 章 《三》\n<!-- m -->\n正文。\n"
        root = make_proj(t, {"第1章.md": c1, "第2章.md": c2, "第3章.md": c3})
        out_path = os.path.join(t, "range_findings.json")
        f = run(root, "--range", "1-1", "--min", "2", "--max", "200", "--json-out", out_path)
        assert not any(x["chapter"] == 2 for x in f), f
        with open(out_path, encoding="utf-8") as fp:
            payload = json.load(fp)
        assert payload["chapter_range"] == [1, 1]


# ── AI 腔/同质化启发式（advisory）──
def test_ai_tell_flags_expository_connectors():
    body = "他走进房间。综上所述，这一切都是命中注定。众所周知，他不会回头。"
    out = mc.ai_tell_scan(body)
    assert any(sev == "🟡" and "议论文式连接词" in msg for sev, msg, ev in out)


def test_ai_tell_clean_narrative_is_silent():
    body = "他推开门，屋里一片漆黑。窗外的风卷着雪，远处传来钟声。她说，你终于来了。"
    assert mc.ai_tell_scan(body) == []


def test_ai_tell_cliche_density_is_green_nudge():
    # 多条万能金句堆在短正文里 → 千字密度高 → 🟢 nudge（不阻断）
    body = "命运的齿轮开始转动，仿佛整个世界都静止了，空气仿佛凝固，时间仿佛静止。"
    out = mc.ai_tell_scan(body, cliche_per_k=2.0)
    assert any(sev == "🟢" and "万能金句" in msg for sev, msg, ev in out)
    assert all(sev != "🔴" for sev, msg, ev in out)  # 容错铁律：绝不 🔴


def test_burstiness_too_few_sentences_returns_none():
    cv, n = mc.sentence_burstiness("他走了。她笑了。")
    assert cv is None and n == 2


def test_ai_tell_flags_uniform_sentence_length():
    # 12 句、每句严格 8 字 → 句长方差为 0 → CV=0 → 🟡 burstiness 低
    body = "。".join(["甲乙丙丁戊己庚辛"] * 12) + "。"
    out = mc.ai_tell_scan(body)
    assert any(sev == "🟡" and "burstiness" in msg for sev, msg, ev in out)
    assert all(sev != "🔴" for sev, msg, ev in out)


def test_ai_tell_varied_sentence_length_no_burstiness_flag():
    # 长短句交错（人类叙事）→ CV 高 → 不报 burstiness
    body = ("门开了。他站在那里，雪光从他背后斜斜地铺进来，把半张脸切成明暗两块，"
            "谁也看不清他在想什么。她退了一步。又一步。再说话时声音已经发抖，"
            "可她还是把那句憋了三年的话一个字一个字地砸了出来，仿佛要把整座宅子都掀翻。走。")
    out = mc.ai_tell_scan(body)
    assert not any("burstiness" in msg for sev, msg, ev in out)


def test_ai_tell_wired_into_findings_and_toggle(tmp_path):
    chapters = {"第1章.md": "# 第 1 章 《题》\n<!-- meta: demo=false -->\n"
                + "他停下脚步。综上所述，命运的齿轮已然转动。" * 30}
    root = make_proj(str(tmp_path), chapters)
    subprocess.run([sys.executable, SCRIPT, root, "--json-out", os.path.join(root, "f.json")],
                   capture_output=True, text=True)
    payload = json.load(open(os.path.join(root, "f.json"), encoding="utf-8"))
    assert any(x["dim"] == "AI腔" for x in payload["findings"])
    # --no-ai-tell 关闭
    subprocess.run([sys.executable, SCRIPT, root, "--no-ai-tell",
                    "--json-out", os.path.join(root, "f2.json")], capture_output=True, text=True)
    payload2 = json.load(open(os.path.join(root, "f2.json"), encoding="utf-8"))
    assert not any(x["dim"] == "AI腔" for x in payload2["findings"])


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__]))


# ── 术语抽取卫生：剥 markdown / 拒句子片段（防术语表噪声回归）─────────────────
def test_term_like_rejects_markup_and_fragments():
    # 干净名词术语 → 收
    for ok in ("烈阳花", "枯木真人", "人族双璧", "九龙", "王敦密码"):
        assert mc._term_like(ok), ok
    # 带 markdown / 复选框 / 标点 / 句子片段 / 短语 → 拒
    for bad in ("**护短第一**", "[ ] 2. 家世父母师承", "九龙气运/九九天劫",
                "好男不跟女斗，我闭嘴", "得逞后现身；互赠功德",
                "心结一·枯木真人", "气运即金手指即催命符",
                "meta", "目标平台", "-manual-evidence"):
        assert not mc._term_like(bad), bad


def test_strip_md_unwraps_term_body():
    assert mc._strip_md("- **烈阳花**") == "烈阳花"
    assert mc._strip_md("[ ] 2. 家世") == "家世"
    assert mc._strip_md("3、枯木真人") == "枯木真人"


def test_extract_terms_skips_setting_noise(tmp_path):
    root = tmp_path / "proj"
    (root / "设定").mkdir(parents=True)
    (root / "设定" / "角色卡.md").write_text(
        "# 角色卡 — 王敦\n"
        "## 性格底色\n"
        "- **护短第一**：见师弟被踩就插手\n"
        "## 留白清单\n"
        "- [ ] 1. 灵药谷之前的人生：怎么沦落的\n"
        "## 说话习惯\n"
        "- 「好男不跟女斗，我闭嘴，我闭嘴……」(412章)\n"
        "## 关系\n"
        "- 贺平生：火灵力极纯的师弟\n",
        encoding="utf-8")
    (root / "设定" / "世界观.md").write_text(
        "# 世界观\n## 术语表\n| 规范词 | 说明 |\n|---|---|\n| 烈阳花 | 二品火灵药 |\n"
        "| 目标平台 | 红果 |\n| -manual-evidence | 占位 |\n| meta | 配置 |\n",
        encoding="utf-8")
    terms = set(mc.extract_terms_from_settings(str(root)))
    assert "烈阳花" in terms          # 真术语保留
    assert "贺平生" in terms          # 名词术语保留
    # 噪声全部剔除
    for junk in ("好男不跟女斗，我闭嘴，我闭嘴……", "[ ] 1. 灵药谷之前的人生",
                 "**护短第一**", "灵药谷之前的人生", "目标平台", "manual-evidence", "meta"):
        assert junk not in terms, junk


# ---------- 跨章重复率 / 机械文风（缺口#1） ----------

def test_adjacent_chapter_jaccard_identical_vs_distinct():
    a = "他推开门屋里一片漆黑窗外的风卷着雪远处传来钟声她说你终于来了"
    assert mc.adjacent_chapter_jaccard(a, a) == 1.0           # 逐字相同 → 1.0
    b = "完全不一样的另一段文字讲述清晨阳光洒满整片金色的麦田少年奔跑"
    assert mc.adjacent_chapter_jaccard(a, b) < 0.05           # 互异 → 近 0
    assert mc.adjacent_chapter_jaccard("短", "短") == 0.0     # 短于窗口 → 0


def test_cross_chapter_repetition_flags_near_duplicate():
    shared = "林夜推开斑驳的铁门走进废弃工厂霉味混着铁锈扑面而来他握紧手中的探测仪屏幕幽幽地亮着"
    chapters = [
        (1, shared + "今天他在东侧角落发现了第一块碎片。"),
        (2, shared + "今天他在西侧管道找到了第二块碎片。"),  # 大段复述上一章
    ]
    findings, summary = mc.cross_chapter_repetition(chapters)
    dims = {(sev, dim) for _, sev, dim, _, _ in findings}
    assert ("🟡", "跨章重复") in dims
    assert summary["adjacent_max_jaccard"] >= mc.REP_ADJ_JACCARD_YELLOW


def test_cross_chapter_repetition_mechanical_opener():
    opener = "清晨第一缕阳光照进窗棂的时候林夜已经醒了"
    chapters = [(n, opener + f"，这是第{n}天的开始，他做了不同的事情情节甲乙丙{n}。") for n in (1, 2, 3, 4)]
    findings, summary = mc.cross_chapter_repetition(chapters)
    dims = {(sev, dim) for _, sev, dim, _, _ in findings}
    assert ("🟡", "机械开篇") in dims
    assert summary["mechanical_opener_groups"] >= 1


def test_cross_chapter_repetition_sentence_reuse():
    line = "系统冰冷的声音在脑海中响起宿主请完成今日任务否则将受到惩罚"
    chapters = [(n, f"第{n}章发生了独特的事件甲乙丙丁戊己{n}。{line}。然后他继续前行探索未知。") for n in (1, 2, 3)]
    findings, summary = mc.cross_chapter_repetition(chapters)
    dims = {(sev, dim) for _, sev, dim, _, _ in findings}
    assert ("🟡", "机械句复用") in dims
    assert summary["repeated_sentences"] >= 1


def test_cross_chapter_clean_is_silent():
    chapters = [
        (1, "他推开门屋里一片漆黑窗外的风卷着雪远处传来钟声。"),
        (2, "清晨阳光洒满整片金色麦田少年沿着田埂奔跑笑声飞扬。"),
        (3, "深夜的码头汽笛长鸣货轮缓缓驶离港口灯火渐远。"),
    ]
    findings, summary = mc.cross_chapter_repetition(chapters)
    assert findings == []
    assert summary["adjacent_max_jaccard"] < mc.REP_ADJ_JACCARD_GREEN


def _body(n, text):
    return f"# 第 {n} 章 《章{n}》\n<!-- meta: demo=true -->\n{text}\n"


def test_repetition_wired_into_findings_and_toggle(tmp_path):
    shared = "林夜推开斑驳的铁门走进废弃工厂霉味混着铁锈扑面而来他握紧探测仪屏幕幽幽亮着"
    root = make_proj(str(tmp_path), {
        "第1章.md": _body(1, shared + "他在东侧发现第一块碎片甲乙丙。"),
        "第2章.md": _body(2, shared + "他在西侧找到第二块碎片丁戊己。"),
    })
    findings = run(root)
    assert ("🟡", "跨章重复") in sev_dims(findings)
    # --no-repetition 关闭
    findings_off = run(root, "--no-repetition")
    assert ("🟡", "跨章重复") not in sev_dims(findings_off)


def test_repetition_summary_in_json_payload(tmp_path):
    root = make_proj(str(tmp_path), {
        "第1章.md": _body(1, "他推开门屋里一片漆黑窗外的风卷着雪远处传来钟声。"),
        "第2章.md": _body(2, "清晨阳光洒满金色麦田少年沿着田埂奔跑笑声飞扬不停。"),
    })
    out_json = os.path.join(str(tmp_path), "out.json")
    r = subprocess.run([sys.executable, SCRIPT, root, "--json-out", out_json],
                       capture_output=True, text=True, cwd=HERE)
    assert r.returncode == 0, r.stderr
    with open(out_json, encoding="utf-8") as f:
        payload = json.load(f)
    assert payload["repetition"] is not None
    assert "adjacent_max_jaccard" in payload["repetition"]
    assert "sentence_start_token_groups" in payload["repetition"]
    assert "short_sentence_templates" in payload["repetition"]
    assert "chapter_compression_ratios" in payload["repetition"]
    assert "distinct_4" in payload["repetition"]
    assert payload["repetition"]["thresholds_provenance"].startswith("internal-heuristic")


# ---------- 已确认实体表作术语权威源（缺口#2） ----------

def _write_alias(root, data):
    os.makedirs(os.path.join(root, "设定"), exist_ok=True)
    with open(os.path.join(root, "设定", "角色别名.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def test_load_confirmed_entity_terms_three_shapes(tmp_path):
    # ① character_aliases {别名:规范名}
    root = make_proj(str(tmp_path), {"第1章.md": CLEAN})
    _write_alias(root, {"status": "confirmed", "character_aliases": {"剑帝": "墨衣", "老祖": "墨衣"}})
    assert mc.load_confirmed_entity_terms(root) == {"剑帝", "老祖", "墨衣"}
    # ② characters[].aliases
    _write_alias(root, {"status": "confirmed",
                        "characters": [{"name": "苏离", "aliases": ["阿离", "离姐"]}]})
    assert mc.load_confirmed_entity_terms(root) == {"苏离", "阿离", "离姐"}
    # ③ aliases {规范名:[别名]}
    _write_alias(root, {"status": "confirmed", "aliases": {"林夜": ["夜枭"]}})
    assert mc.load_confirmed_entity_terms(root) == {"林夜", "夜枭"}


def test_confirmed_entity_terms_ignored_when_draft_or_missing(tmp_path):
    root = make_proj(str(tmp_path), {"第1章.md": CLEAN})
    assert mc.load_confirmed_entity_terms(root) == set()          # 缺文件
    _write_alias(root, {"status": "draft", "character_aliases": {"剑帝": "墨衣"}})
    assert mc.load_confirmed_entity_terms(root) == set()          # draft 不采信


def test_confirmed_entity_is_authoritative_even_when_regex_would_reject(tmp_path):
    # 含中点的合法专名「夜·影」会被 _term_like 正则剔除，但确认表应权威采信并进术语矩阵
    assert mc._term_like("夜·影") is False                        # 正则会拒
    ch = "# 第 1 章 《会面》\n<!-- meta: demo=true -->\n夜·影站在屋顶，墨衣抬头看他。\n"
    root = make_proj(str(tmp_path), {"第1章.md": ch})
    _write_alias(root, {"status": "confirmed", "character_aliases": {"夜·影": "墨衣"}})
    out_json = os.path.join(str(tmp_path), "out.json")
    r = subprocess.run([sys.executable, SCRIPT, root, "--json-out", out_json],
                       capture_output=True, text=True, cwd=HERE)
    assert r.returncode == 0, r.stderr
    with open(out_json, encoding="utf-8") as f:
        payload = json.load(f)
    assert "夜·影" in payload["terms_source"]["confirmed_entities"]
    # 术语矩阵真统计了这个权威专名（第1章出现 1 次）
    assert payload["term_matrix"]["1"]["夜·影"] == 1


def test_no_auto_terms_also_skips_confirmed_entities(tmp_path):
    root = make_proj(str(tmp_path), {"第1章.md": CLEAN})
    _write_alias(root, {"status": "confirmed", "character_aliases": {"剑帝": "墨衣"}})
    out_json = os.path.join(str(tmp_path), "out.json")
    r = subprocess.run([sys.executable, SCRIPT, root, "--no-auto-terms", "--json-out", out_json],
                       capture_output=True, text=True, cwd=HERE)
    assert r.returncode == 0, r.stderr
    with open(out_json, encoding="utf-8") as f:
        payload = json.load(f)
    assert payload["terms_source"]["confirmed_entities"] == []
