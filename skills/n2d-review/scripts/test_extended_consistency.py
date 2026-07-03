"""extended_consistency 检查器单测（纯函数·建临时作品树）。
cd skills/n2d-review/scripts && python -m pytest test_extended_consistency.py
"""
import json
import os

import extended_consistency as ec


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False)


def _storyboard(tmp_path, ep, clips):
    _write(os.path.join(str(tmp_path), "脚本", ep, "storyboard.json"), {"clips": clips})


def test_ui_hud_warns_when_panel_shot_but_no_registry(tmp_path):
    _storyboard(tmp_path, "第1集", [
        {"id": "Clip_01", "desc": "沈念召出系统面板，血条与等级框亮起"},
        {"id": "Clip_02", "desc": "宫墙下对话"},
    ])
    res = ec.check_ui_hud(str(tmp_path), "第1集")
    assert res["available"] is True
    assert any(f["verdict"] == "warn" and "ui_asset_registry" in f["message"] for f in res["findings"])


def test_ui_hud_checks_system_state_monotonicity(tmp_path):
    _storyboard(tmp_path, "第2集", [
        {"id": "Clip_01", "desc": "系统面板 UI_LEVEL 显示等级与经验"},
    ])
    _write(os.path.join(str(tmp_path), "设定库", "ui_asset_registry.json"),
           {"assets": [{"id": "UI_LEVEL", "frame": "金框", "palette": "蓝金", "font": "Noto", "layout": "左上"}]})
    _write(os.path.join(str(tmp_path), "设定库", "system_state_ledger.json"),
           {"states": [
               {"episode": "第1集", "clip": "Clip_01", "metric": "level", "value": 5},
               {"episode": "第2集", "clip": "Clip_01", "metric": "level", "value": 4},
           ]})
    res = ec.check_ui_hud(str(tmp_path), "第2集")
    assert any("从 5 降到 4" in f["message"] for f in res["findings"])


def test_ui_hud_noop_without_panel_shots(tmp_path):
    _storyboard(tmp_path, "第1集", [{"id": "Clip_01", "desc": "宫墙下对话"}])
    res = ec.check_ui_hud(str(tmp_path), "第1集")
    assert res["available"] is True and res["findings"] == []


def test_leitmotif_warns_without_registry_when_music_signal(tmp_path):
    _storyboard(tmp_path, "第1集", [
        {"id": "Clip_01", "desc": "CHAR_shen 登场", "bgm": "主角主题"},
        {"id": "Clip_02", "desc": "CHAR_liu 出现"},
    ])
    res = ec.check_leitmotif(str(tmp_path), "第1集")
    assert any("leitmotif_registry" in f["message"] for f in res["findings"])


def test_leitmotif_detects_motif_cross_use(tmp_path):
    _storyboard(tmp_path, "第1集", [
        {"id": "Clip_01", "desc": "CHAR_shen 登场", "bgm": "CHAR_shen 配 MOTIF_villain"},
    ])
    _write(os.path.join(str(tmp_path), "设定库", "leitmotif_registry.json"),
           {"motifs": [{"id": "MOTIF_hero", "subject": "CHAR_shen"},
                       {"id": "MOTIF_villain", "subject": "CHAR_liu"}]})
    res = ec.check_leitmotif(str(tmp_path), "第1集")
    assert any("母题串用" in f["message"] for f in res["findings"])


def test_leitmotif_requires_reusable_audio_asset(tmp_path):
    _storyboard(tmp_path, "第1集", [
        {"id": "Clip_01", "desc": "CHAR_shen 登场", "bgm": "CHAR_shen 配 MOTIF_hero"},
    ])
    _write(os.path.join(str(tmp_path), "设定库", "leitmotif_registry.json"),
           {"motifs": [{"id": "MOTIF_hero", "subject": "CHAR_shen"}]})
    res = ec.check_leitmotif(str(tmp_path), "第1集")
    msgs = " ".join(f["message"] for f in res["findings"])
    assert "缺 file/audio/clip" in msgs
    assert "缺 audio_sha256" in msgs


def test_body_proportion_flags_missing_lock_for_long_line(tmp_path):
    _write(os.path.join(str(tmp_path), "出图", "共享", "identity_registry.json"),
           {"characters": {"CHAR_shen": {"core": True, "character_dna": {"face": "杏眼"}}}})
    _storyboard(tmp_path, "第1集", [{"id": "Clip_01", "desc": "CHAR_shen 登场"}])
    res = ec.check_body_proportion(str(tmp_path), "第1集")
    assert any("缺 character_dna.身形" in f["message"] for f in res["findings"])


def test_body_proportion_flags_antonym_conflict(tmp_path):
    _write(os.path.join(str(tmp_path), "出图", "共享", "identity_registry.json"),
           {"characters": {"CHAR_shen": {"appears_in": ["第1集", "第2集"],
                                         "character_dna": {"body": "身形纤细清瘦"}}}})
    _storyboard(tmp_path, "第1集", [{"id": "Clip_01", "desc": "CHAR_shen 魁梧壮硕地站着"}])
    res = ec.check_body_proportion(str(tmp_path), "第1集")
    assert any("跨集体型漂移嫌疑" in f["message"] for f in res["findings"])


def test_object_presence_sidecar_read(tmp_path):
    _write(os.path.join(str(tmp_path), "生产数据", "object_presence_第1集.json"),
           {"kind": "n2d_object_presence",
            "findings": [{"shot": "Clip_03", "asset": "PROP_jade", "expected": True, "present": False}]})
    res = ec.check_object_presence_visual(str(tmp_path), "第1集")
    assert res["available"] is True
    assert res["findings"][0]["verdict"] == "block"
    assert "object permanence" in res["findings"][0]["message"]


def test_object_presence_skips_without_sidecar(tmp_path):
    res = ec.check_object_presence_visual(str(tmp_path), "第1集")
    assert res["available"] is False and res["findings"] == []


def test_appearance_judge_sidecar_read(tmp_path):
    _write(os.path.join(str(tmp_path), "生产数据", "appearance_judge_第1集.json"),
           {"kind": "n2d_appearance_judge",
            "findings": [{"shot": "Clip_05", "character": "CHAR_shen", "verdict": "warn", "similarity": 0.61}]})
    res = ec.check_appearance_judge(str(tmp_path), "第1集")
    assert res["findings"][0]["verdict"] == "warn"
    assert "0.61" in res["findings"][0]["message"]


def test_text_render_warns_on_undeclared_text_shot(tmp_path):
    _storyboard(tmp_path, "第1集", [
        {"id": "Clip_01", "desc": "系统面板浮现，显示等级与属性"},
    ])
    res = ec.check_text_render(str(tmp_path), "第1集")
    assert res["available"] is True
    assert any("未声明预期文字" in f["message"] for f in res["findings"])


def test_text_render_reads_sidecar_findings(tmp_path):
    _storyboard(tmp_path, "第1集", [{"id": "Clip_01", "desc": "系统面板"}])
    _write(os.path.join(str(tmp_path), "生产数据", "text_render_第1集.json"),
           {"kind": "n2d_text_render",
            "findings": [{"shot": "Clip_02", "verdict": "block", "expected": "等级 3",
                          "ocr_text": "等级 8", "similarity": 0.5}]})
    res = ec.check_text_render(str(tmp_path), "第1集")
    assert res["findings"][0]["verdict"] == "block"
    assert "等级 8" in res["findings"][0]["message"]


def test_text_render_noop_without_text_shots(tmp_path):
    _storyboard(tmp_path, "第1集", [{"id": "Clip_01", "desc": "宫墙下对话"}])
    res = ec.check_text_render(str(tmp_path), "第1集")
    assert res["findings"] == []


def test_translation_terms_flags_drifted_name(tmp_path):
    os.makedirs(os.path.join(str(tmp_path), "脚本", "第1集"), exist_ok=True)
    open(os.path.join(str(tmp_path), "脚本", "第1集", "voiceover.txt"), "w", encoding="utf-8").write("沈念走进青云宗")
    open(os.path.join(str(tmp_path), "脚本", "第1集", "字幕_英文.srt"), "w", encoding="utf-8").write("Shen Nian enters the Azure Sect")
    _write(os.path.join(str(tmp_path), "设定库", "translation_glossary.json"),
           {"terms": [{"cn": "青云宗", "en": "Qingyun Sect"}]})
    res = ec.check_translation_terms(str(tmp_path), "第1集")
    assert res["available"] is True
    assert any("译名漂移" in f["message"] for f in res["findings"])


def test_translation_terms_flags_chinese_canonical_variant(tmp_path):
    os.makedirs(os.path.join(str(tmp_path), "脚本", "第1集"), exist_ok=True)
    open(os.path.join(str(tmp_path), "脚本", "第1集", "voiceover.txt"), "w", encoding="utf-8").write("她发动青云剑法第一式。")
    _write(os.path.join(str(tmp_path), "设定库", "terminology_glossary.json"),
           {"terms": [{"cn": "青云剑诀", "aliases": ["青云剑法"], "forbidden": ["青云剑术"]}]})
    res = ec.check_translation_terms(str(tmp_path), "第1集")
    assert res["available"] is True
    assert any("术语别名" in f["message"] for f in res["findings"])


def test_translation_terms_warns_without_glossary(tmp_path):
    os.makedirs(os.path.join(str(tmp_path), "脚本", "第1集"), exist_ok=True)
    open(os.path.join(str(tmp_path), "脚本", "第1集", "字幕_英文.srt"), "w", encoding="utf-8").write("Hello world")
    res = ec.check_translation_terms(str(tmp_path), "第1集")
    assert any("translation_glossary" in f["message"] for f in res["findings"])


def test_translation_terms_skips_without_en_subtitle(tmp_path):
    res = ec.check_translation_terms(str(tmp_path), "第1集")
    assert res["available"] is False and res["findings"] == []


def test_analyze_returns_all_sections(tmp_path):
    _storyboard(tmp_path, "第1集", [{"id": "Clip_01", "desc": "宫墙"}])
    res = ec.analyze(str(tmp_path), "第1集")
    assert set(res["sections"]) == {lbl for lbl, _ in ec.SECTION_BUILDERS}


# ---------- EXP1 表情/情绪连续性 ----------

def test_emotions_in_buckets():
    assert ec._emotions_in("她崩溃落泪") == {"悲"}
    assert ec._emotions_in("他怒吼着大笑") == {"怒", "喜"}
    assert ec._emotions_in("眼里有受宠若惊的单纯") == {"喜"}
    assert ec._emotions_in("空镜远山") == set()


def test_expression_consumes_sidecar(tmp_path):
    _write(os.path.join(str(tmp_path), "生产数据", "expression_第1集.json"), {
        "kind": "n2d_expression",
        "findings": [{"shot": "Clip_03", "character": "CHAR_01", "verdict": "warn",
                      "scripted_emotion": "悲", "observed_expression": "微笑"}],
    })
    res = ec.check_expression_continuity(str(tmp_path), "第1集")
    assert res["available"] is True
    assert any("CHAR_01" in f["message"] and f["verdict"] == "warn" for f in res["findings"])


def test_expression_first_pass_flags_emotional_closeup_without_ref(tmp_path):
    _storyboard(tmp_path, "第1集", [
        {"id": "Clip_01", "desc": "近景：沈念 CHAR_01 崩溃落泪"},               # 情绪近景无表情参考 → warn
        {"id": "Clip_02", "desc": "特写：沈念 CHAR_01 莞尔一笑 表情参考已附"},   # 有 ref；但与前镜情绪硬跳
    ])
    res = ec.check_expression_continuity(str(tmp_path), "第1集")
    assert res["available"] is True
    msgs = " ".join(f["message"] for f in res["findings"])
    assert "未声明表情参考" in msgs
    assert "情绪硬跳" in msgs


def test_expression_ignores_forbidden_and_offscreen_character_ids(tmp_path):
    _storyboard(tmp_path, "第1集", [
        {
            "id": "Clip_01",
            "description": "近景：张老大 CHAR_ZHANG_LAODA 莞尔一笑",
            "character_ids": ["CHAR_ZHANG_LAODA"],
            "entity_schedule": {
                "characters": ["CHAR_ZHANG_LAODA"],
                "forbidden_presence": ["CHAR_HE_PINGSHENG", "CHAR_HAN_LAOSAN"],
            },
        },
        {
            "id": "Clip_02",
            "description": "特写：贺平生 CHAR_HE_PINGSHENG 眼里有受宠若惊的单纯",
            "character_ids": ["CHAR_HE_PINGSHENG"],
            "entity_schedule": {
                "characters": ["CHAR_HE_PINGSHENG"],
                "forbidden_presence": ["CHAR_ZHANG_LAODA", "CHAR_HAN_LAOSAN"],
            },
            "continuity": {"offscreen_presence": ["CHAR_ZHANG_LAODA"]},
        },
    ])
    res = ec.check_expression_continuity(str(tmp_path), "第1集")

    assert not any("CHAR_ZHANG_LAODA" in f["message"] and "情绪硬跳" in f["message"] for f in res["findings"])
    assert not any("CHAR_HAN_LAOSAN" in f["message"] for f in res["findings"])


def test_expression_skips_without_storyboard(tmp_path):
    res = ec.check_expression_continuity(str(tmp_path), "第1集")
    assert res["available"] is False and res["findings"] == []


# ---------- SP1 伏笔兑现 ----------

def test_ep_num_parse():
    assert ec._ep_num("第3集") == 3 and ec._ep_num("ep12") == 12 and ec._ep_num("x") is None


def test_setup_payoff_validates_ledger(tmp_path):
    _write(os.path.join(str(tmp_path), "设定库", "setup_payoff_ledger.json"), {
        "pairs": [
            {"id": "玉佩身世", "setup_ep": "第5集", "payoff_ep": "第2集", "desc": "玉佩身世"},  # 兑现早于种下
            {"id": "断坑", "setup_ep": "第1集", "payoff_ep": "", "desc": "神秘黑衣人"},          # 坑没填
            {"id": "孤儿兑现", "payoff_ep": "第3集", "desc": "突兀兑现"},                         # 缺种下集
        ],
    })
    res = ec.check_setup_payoff(str(tmp_path), "第3集")
    assert res["available"] is True
    msgs = " ".join(f["message"] for f in res["findings"])
    assert "兑现早于种下" in msgs and "坑没填" in msgs and "无种下集" in msgs


def test_setup_payoff_warns_when_hook_but_no_ledger(tmp_path):
    os.makedirs(os.path.join(str(tmp_path), "脚本", "第1集"), exist_ok=True)
    open(os.path.join(str(tmp_path), "脚本", "第1集", "voiceover.txt"), "w",
         encoding="utf-8").write("他留下一句意味深长的话，埋下伏笔。")
    res = ec.check_setup_payoff(str(tmp_path), "第1集")
    assert res["available"] is True
    assert any("setup_payoff_ledger" in f["message"] for f in res["findings"])


def test_setup_payoff_skips_when_no_ledger_no_hook(tmp_path):
    os.makedirs(os.path.join(str(tmp_path), "脚本", "第1集"), exist_ok=True)
    open(os.path.join(str(tmp_path), "脚本", "第1集", "voiceover.txt"), "w",
         encoding="utf-8").write("平静的一天，没什么特别。")
    res = ec.check_setup_payoff(str(tmp_path), "第1集")
    assert res["available"] is False and res["findings"] == []


def _vo(tmp_path, ep, text):
    p = os.path.join(str(tmp_path), "脚本", ep, "voiceover.txt")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(text)


def test_narrative_state_warns_without_ledger(tmp_path):
    _vo(tmp_path, "第1集", "[镜头1·沈念·震惊·快] 她这才知道真相。")
    res = ec.check_narrative_state(str(tmp_path), "第1集")
    assert res["available"] and any(r["verdict"] == "warn" for r in res["findings"])


def test_narrative_state_knowledge_premature(tmp_path):
    _vo(tmp_path, "第3集", "[镜头1·沈念·冷冽·快] 我早晚揪出真凶。")
    _vo(tmp_path, "第5集", "[镜头1·沈念·震惊·快] 原来真凶是他。")
    _write(os.path.join(str(tmp_path), "设定库", "narrative_state_ledger.json"),
           {"kind": "n2d_narrative_state_ledger", "knowledge": [
               {"character": "沈念", "keyword": "真凶", "known_from_ep": "第5集", "fact": "真凶身份"}],
            "locations": [], "relationships": []})
    res = ec.check_narrative_state(str(tmp_path), "第5集")
    assert any("知识倒流" in r["message"] for r in res["findings"])


def test_narrative_state_location_jump(tmp_path):
    _vo(tmp_path, "第3集", "[镜头1·沈念·平静·慢] 在京城闲坐。")
    _vo(tmp_path, "第4集", "[镜头1·沈念·平静·慢] 身处南山。")
    _write(os.path.join(str(tmp_path), "设定库", "narrative_state_ledger.json"),
           {"kind": "n2d_narrative_state_ledger", "knowledge": [],
            "locations": [{"character": "沈念", "ep": "第3集", "place": "京城"},
                          {"character": "沈念", "ep": "第4集", "place": "南山"}], "relationships": []})
    res = ec.check_narrative_state(str(tmp_path), "第4集")
    assert any("位置瞬移" in r["message"] for r in res["findings"])


def test_narrative_state_clean_when_consistent(tmp_path):
    _vo(tmp_path, "第3集", "[镜头1·沈念·平静·慢] 在京城。她决定前往南山。")
    _vo(tmp_path, "第4集", "[镜头1·沈念·平静·慢] 身处南山。")
    _write(os.path.join(str(tmp_path), "设定库", "narrative_state_ledger.json"),
           {"kind": "n2d_narrative_state_ledger", "knowledge": [],
            "locations": [{"character": "沈念", "ep": "第3集", "place": "京城"},
                          {"character": "沈念", "ep": "第4集", "place": "南山"}], "relationships": []})
    res = ec.check_narrative_state(str(tmp_path), "第4集")
    assert not any(r["verdict"] == "warn" for r in res["findings"])
