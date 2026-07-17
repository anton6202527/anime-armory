# -*- coding: utf-8 -*-
"""广告文案质量机检（copy_quality_audit）单测。

盯的是两条「写错就全线不可用」的领域纪律，以及 advisory 底线：
  ① **品牌名/slogan/CTA/法律声明重复不许误报**——广告里那是刻意曝光手法；
  ② **已被 ad_law_check 命中的行不许再报套话**——同一句话响两遍，文案就开始无视告警；
  ③ 本检永不产 block（Creative heuristics stay advisory）。
"""
import json

import copy_quality_audit as cqa


def _write(root, rel, value):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        path.write_text(value, encoding="utf-8")
    else:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _brief(root, **mand):
    m = {"slogan": "元气一整天", "cta": "立即购买", "legal_lines": ["广告"]}
    m.update(mand)
    return _write(root, "需求/brief.json", {"mandatories": m})


def _registry(root, name="星盒"):
    return _write(root, "设定库/asset_registry.json",
                  {"brand": {"id": "BRAND_01", "name": name, "text_logo": "STARBOX",
                             "slogan": "元气一整天", "primary_hex": "#2E9E97"}})


def _codes(report):
    return [f["code"] for f in report["findings"]]


def _by_code(report, code):
    return [f for f in report["findings"] if f["code"] == code]


# ── ① 生死线：品牌名/slogan/CTA 重复不误报 ──────────────────────────────────

def test_brand_and_slogan_repetition_is_not_flagged(tmp_path):
    """slogan/品牌名/CTA 在片中反复出现 = 提升 recall 的刻意设计，不是冗余。"""
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt",
           "星盒，元气一整天。\n"
           "星盒，元气一整天。\n"
           "星盒，元气一整天，立即购买。\n"
           "立即购买。\n")

    report = cqa.build(tmp_path)

    assert "redundant_vo_pair" not in _codes(report)
    assert "repeated_usp_mention" not in _codes(report)
    assert report["summary"]["warn"] == 0


def test_identical_non_brand_lines_are_still_flagged(tmp_path):
    """豁免不是免死金牌：抠掉品牌片段后仍雷同的普通 VO 照报（否则召回塌陷）。"""
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt",
           "星盒让每个清晨都不再手忙脚乱地找早餐。\n"
           "让每个清晨都不再手忙脚乱地找早餐，星盒。\n")

    hits = _by_code(cqa.build(tmp_path), "redundant_vo_pair")

    assert len(hits) == 1
    assert hits[0]["severity"] == "warn"
    assert "第 1 行" in hits[0]["msg"] and "第 2 行" in hits[0]["msg"]


def test_mask_exempt_strips_phrases_not_whole_line():
    """抠片段而非整行豁免——夹带品牌名的普通句子仍参与比对。"""
    assert cqa.mask_exempt("星盒，元气一整天", ["星盒", "元气一整天"]) == ""
    assert cqa.mask_exempt("星盒让清晨更简单", ["星盒"]) == "让清晨更简单"


def test_exempt_phrases_sourced_from_brief_and_registry():
    brief = {"mandatories": {"slogan": "元气一整天", "cta": "立即购买", "legal_lines": ["广告", "图片仅供参考"]}}
    registry = {"brand": {"name": "星盒", "text_logo": "STARBOX", "slogan": "元气一整天"}}

    phrases = cqa.exempt_phrases(brief, registry)

    assert {cqa.clean(p) for p in phrases} == {"元气一整天", "立即购买", "广告", "图片仅供参考",
                                              "星盒", "STARBOX"}
    # 长的排前面：先抠长语，避免短语把长语拆成碎片
    assert len(cqa.clean(phrases[0])) >= len(cqa.clean(phrases[-1]))


def test_missing_exempt_sources_is_info_not_silent(tmp_path):
    """没有 brief/registry 时坦白说明「可能把品牌重复误报为冗余」，不装作可信。"""
    _write(tmp_path, "脚本/voiceover.txt", "早安。\n")

    hits = _by_code(cqa.build(tmp_path), "exempt_list_unavailable")

    assert len(hits) == 1 and hits[0]["severity"] == "info"


# ── ② 生死线：与 ad_law_check 去重 ──────────────────────────────────────────

def test_law_flagged_line_is_not_double_reported(tmp_path):
    """该行已经有一条广告法告警了 → 本脚本不再对它报套话。"""
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt", "顶级匠心，卓越非凡的尊享体验。\n")
    _write(tmp_path, "脚本/广告法机检报告.json", {
        "region": "中国大陆", "disabled": False,
        "summary": {"block": 0, "warn": 1},
        "findings": [{"severity": "warn", "term": "顶级", "category": "绝对化用语待证",
                      "file": "脚本/voiceover.txt", "line": 1, "snippet": "顶级匠心"}],
    })

    report = cqa.build(tmp_path)

    assert "empty_adjective_stack" not in _codes(report)


def test_same_line_flagged_when_no_law_report(tmp_path):
    """对照：没有广告法报告时同一行照报——证明上一条是去重，不是压根没检出。"""
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt", "顶级匠心，卓越非凡的尊享体验。\n")

    hits = _by_code(cqa.build(tmp_path), "empty_adjective_stack")

    assert len(hits) == 1
    assert hits[0]["severity"] == "warn"


def test_law_findings_from_other_files_do_not_suppress(tmp_path):
    """广告法报告里 广告脚本.md 的第 1 行 ≠ voiceover.txt 的第 1 行，行号不同源，不许误抑制。"""
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt", "匠心卓越，非凡尊享。\n")
    _write(tmp_path, "脚本/广告法机检报告.json", {
        "findings": [{"severity": "warn", "term": "最好", "file": "脚本/广告脚本.md", "line": 1}],
    })

    assert "empty_adjective_stack" in _codes(cqa.build(tmp_path))


def test_law_flagged_lines_parser():
    report = {"findings": [
        {"file": "脚本/voiceover.txt", "line": 3},
        {"file": "/abs/path/脚本/voiceover.txt", "line": 5},
        {"file": "脚本/storyboard.json", "line": 7},   # 别的文件 → 不收
        {"file": "脚本/voiceover.txt", "line": "x"},   # 脏数据 → 跳过不崩
    ]}

    assert cqa.law_flagged_lines(report) == {3, 5}
    assert cqa.law_flagged_lines(None) == set()


def test_empty_adjective_list_excludes_law_terms():
    """静态去重：套话词表刻意不收 ad_law_check 已覆盖的绝对化用语。"""
    law_terms = {"顶级", "顶尖", "极致", "极品", "终极", "最佳", "最好", "唯一",
                 "独一无二", "独家", "首选", "领先", "无与伦比", "万能"}

    assert law_terms.isdisjoint(set(cqa.EMPTY_ADJECTIVES))


# ── 同义 VO 对 ───────────────────────────────────────────────────────────────

def test_synonymous_vo_pair_detected(tmp_path):
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt",
           "每天早上一盒，让你整个上午都精神饱满。\n"
           "画面：城市清晨的街道。\n"
           "每天早上一盒，让你整个上午都精力充沛。\n")

    hits = _by_code(cqa.build(tmp_path), "redundant_vo_pair")

    assert len(hits) == 1
    assert hits[0]["lines"] if "lines" in hits[0] else True
    assert "第 1 行" in hits[0]["msg"] and "第 3 行" in hits[0]["msg"]
    assert hits[0]["severity"] == "warn"   # 高相似也只 warn：advisory


def test_short_lines_do_not_pair(tmp_path):
    """短句相似度噪声大（『来一盒』『来一杯』），不比。"""
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt", "来一盒。\n来一盒。\n")

    assert "redundant_vo_pair" not in _codes(cqa.build(tmp_path))


def test_repeated_usp_mention_detected(tmp_path):
    """同一卖点短语在 ≥3 句复现 = 30s 里浪费秒数。"""
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt",
           "零糖零卡，喝着没负担。\n"
           "上班路上来一盒，零糖零卡刚刚好。\n"
           "加班到深夜，零糖零卡也安心。\n")

    hits = _by_code(cqa.build(tmp_path), "repeated_usp_mention")

    assert len(hits) >= 1
    assert any("零糖零卡" in f["msg"] for f in hits)
    assert all(f["severity"] == "warn" for f in hits)


def test_repeated_usp_ignores_brand_phrases(tmp_path):
    """品牌名在 5 句里出现 5 次 ≠ 卖点复读。"""
    _brief(tmp_path)
    _registry(tmp_path, name="元气星盒")
    _write(tmp_path, "脚本/voiceover.txt",
           "元气星盒陪你上班。\n元气星盒陪你健身。\n元气星盒陪你加班。\n元气星盒陪你回家。\n")

    hits = _by_code(cqa.build(tmp_path), "repeated_usp_mention")

    assert not any("元气星盒" in f["msg"] for f in hits)


# ── 套话堆砌 ─────────────────────────────────────────────────────────────────

def test_empty_adjective_stack_detected(tmp_path):
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt", "匠心工艺，卓越品质，尊享非凡人生。\n")

    hits = _by_code(cqa.build(tmp_path), "empty_adjective_stack")

    assert len(hits) == 1
    assert hits[0]["severity"] == "warn"
    assert "第 1 行" in hits[0]["msg"]


def test_single_adjective_is_not_a_stack(tmp_path):
    """一个形容词不是堆砌——广告本来就要有情绪，别把正常文案打死。"""
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt", "用心做好每一盒早餐。\n")

    assert "empty_adjective_stack" not in _codes(cqa.build(tmp_path))


def test_adjectives_with_evidence_downgrade_to_info(tmp_path):
    """同行有数字实证 → 形容词有支撑，降 info（广告 VO 直给卖点是对的，不是缺陷）。"""
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt", "匠心工艺，卓越品质，18 道工序 72 小时慢发酵。\n")

    hits = _by_code(cqa.build(tmp_path), "empty_adjective_stack")

    assert len(hits) == 1
    assert hits[0]["severity"] == "info"


def test_plain_usp_copy_is_not_flagged(tmp_path):
    """领域差异：广告 VO 直给卖点是**好文案**，不该报『信息直给』。"""
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt",
           "0 糖 0 卡，一盒只有 35 大卡。\n"
           "冷萃 8 小时，口感更清爽。\n"
           "星盒，元气一整天，立即购买。\n")

    report = cqa.build(tmp_path)

    assert report["summary"]["warn"] == 0


# ── VO 密度 ──────────────────────────────────────────────────────────────────

def test_vo_density_high_warns_with_measured_seconds(tmp_path):
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt", "早上一盒星盒立刻出门赶地铁上班开会不迟到也不饿肚子精神一整天。\n")
    _write(tmp_path, "脚本/镜头时长.json", {"kind": "ad_storyboard_finalize",
                                          "vo_seconds": 2.0, "vo_placeholder": False})

    hits = _by_code(cqa.build(tmp_path), "vo_density_high")

    assert len(hits) == 1
    assert hits[0]["severity"] == "warn"
    assert "内部启发式" in hits[0]["msg"]  # 不冒充法定数值


def test_vo_density_downgrades_on_placeholder_vo(tmp_path):
    """占位配音的时长是估算值——结论不可当证据 → info。"""
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt", "早上一盒星盒立刻出门赶地铁上班开会不迟到也不饿肚子精神一整天。\n")
    _write(tmp_path, "脚本/镜头时长.json", {"vo_seconds": 2.0, "vo_placeholder": True})

    hits = _by_code(cqa.build(tmp_path), "vo_density_high")

    assert len(hits) == 1
    assert hits[0]["severity"] == "info"
    assert "占位" in hits[0]["msg"]


def test_vo_density_falls_back_to_duration_list(tmp_path):
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt", "早安。\n")
    _write(tmp_path, "配音/时长清单.json", {"has_placeholder": False,
                                         "lines": [{"idx": 1, "seconds": 1.5, "gap_after": 0.5}]})

    seconds, placeholder = cqa.load_vo_seconds(tmp_path)

    assert seconds == 2.0
    assert placeholder is False


def test_vo_density_unavailable_is_info(tmp_path):
    """没有实测时长 → insufficient_data，不臆造「念得完」。"""
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt", "早安。\n")

    hits = _by_code(cqa.build(tmp_path), "vo_density_unavailable")

    assert len(hits) == 1 and hits[0]["severity"] == "info"


def test_vo_density_pure_function():
    lines = [{"line": 1, "text": "早安，星盒。"}]  # 标点不占念的时间 → clean 后 4 字

    assert cqa.vo_density(lines, 1.0) == 4.0
    assert cqa.vo_density(lines, 2.0) == 2.0
    assert cqa.vo_density(lines, 0) is None
    assert cqa.vo_density(lines, None) is None


# ── VO 解析器（广告是逐句纯文本，无 [镜头N·角色] 前缀） ──────────────────────

def test_parse_voiceover_keeps_original_line_numbers():
    """行号必须是**原始**行号——要与广告法报告的 line 对齐去重。"""
    rows = cqa.parse_voiceover("# 注释\n\n早安。\n\n再来一盒。\n")

    assert [r["line"] for r in rows] == [3, 5]
    assert [r["text"] for r in rows] == ["早安。", "再来一盒。"]


def test_parse_voiceover_strips_optional_prefixes():
    rows = cqa.parse_voiceover("旁白：早安。\nVO: 再来一盒。\n0-3s：镜头一的旁白。\n1. 第四句。\n")

    assert [r["text"] for r in rows] == ["早安。", "再来一盒。", "镜头一的旁白。", "第四句。"]


# ── 降级 & 契约形状 & advisory ───────────────────────────────────────────────

def test_missing_voiceover_degrades_without_crash(tmp_path):
    report = cqa.build(tmp_path)

    assert report["available"] is False
    assert _codes(report) == ["voiceover_missing"]
    assert report["findings"][0]["severity"] == "warn"
    assert report["summary"]["block"] == 0


def test_nonexistent_root_is_rc0(tmp_path, capsys):
    assert cqa.main([str(tmp_path / "nonexistent")]) == 0
    capsys.readouterr()


def test_never_blocks_even_on_worst_copy(tmp_path):
    """advisory 底线：脆弱启发式无权硬阻断（ad-craft/gate.py:519）。"""
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt",
           "匠心卓越，尊享非凡。\n"
           "匠心卓越，尊享非凡的品质。\n"
           "奢华精致，惊艳震撼。\n")
    _write(tmp_path, "脚本/镜头时长.json", {"vo_seconds": 0.5, "vo_placeholder": False})

    report = cqa.build(tmp_path)

    assert report["summary"]["warn"] > 0
    assert report["summary"]["block"] == 0
    assert all(f["severity"] != "block" for f in report["findings"])


def test_build_contract_shape(tmp_path):
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt", "0 糖 0 卡，一天一盒。\n")

    report = cqa.build(tmp_path)

    assert report["schema_version"] == 1
    assert report["kind"] == "ad_copy_quality_audit"
    assert isinstance(report["available"], bool)
    assert set(report["summary"]) >= {"block", "warn", "info"}
    for f in report["findings"]:
        assert set(f) == {"severity", "code", "msg"}   # gate 消费 msg，不是 message
        assert f["severity"] in {"warn", "info"}
    assert report["thresholds"]["provenance"] == "internal-heuristic·confidence=low"


# ── CLI ──────────────────────────────────────────────────────────────────────

def test_strict_exit_code(tmp_path, capsys):
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt", "匠心工艺，卓越品质，尊享非凡人生。\n")

    assert cqa.main([str(tmp_path)]) == 0             # 默认 advisory，不拦
    assert cqa.main([str(tmp_path), "--strict"]) == 1  # --strict 只影响退出码
    capsys.readouterr()


def test_strict_rc0_on_clean_copy(tmp_path, capsys):
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt", "0 糖 0 卡，一盒 35 大卡。\n")
    _write(tmp_path, "脚本/镜头时长.json", {"vo_seconds": 5.0, "vo_placeholder": False})

    assert cqa.main([str(tmp_path), "--strict"]) == 0
    capsys.readouterr()


def test_write_emits_json_and_md(tmp_path, capsys):
    _brief(tmp_path)
    _registry(tmp_path)
    _write(tmp_path, "脚本/voiceover.txt", "0 糖 0 卡，一天一盒。\n")

    cqa.main([str(tmp_path), "--write"])
    capsys.readouterr()

    out = tmp_path / "生产数据" / "ad_copy_quality_audit.json"
    assert json.loads(out.read_text(encoding="utf-8"))["kind"] == "ad_copy_quality_audit"
    assert "广告文案质量机检" in out.with_suffix(".md").read_text(encoding="utf-8")
    assert not list((tmp_path / "生产数据").glob("*.tmp"))  # 原子写不留临时文件
