"""novel-review 机检单测。从脚本自身目录跑：
    cd skills/novel-review/scripts && python -m pytest test_mechanical_check.py

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


def make_proj(tmp, chapters, *, outline=None, source=None):
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


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__]))
