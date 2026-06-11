"""voice_text.clean_text + voice_manifest 回归测试——①锁住「气口标记 || / 钩子 emoji」清洗，
防 `。，` / `，，` 脏标点回流到 时长清单.json 文本 与字幕（治历史 bug）；
②锁住 时长清单 逐句条目含契约字段 voice_key（一角一色跨集对账数据源，n2d-identity 消费）。
cd skills/n2d-voice && python -m pytest test_render_voice.py
（clean_text/manifest_entry 已独立到 voice_text.py / voice_manifest.py，render_voice 主流程不可安全 import 故不直接测它。）
"""
import voice_text as rv
import voice_manifest as vmf
from voice_manifest import VOICE_KEY_FIELD


def test_pause_after_sentence_end_no_comma():
    # 。|| → 。（不留 「。，」）
    assert rv.clean_text("走向。|| 慎重选择。") == "走向。慎重选择。"
    assert rv.clean_text("人就只能猜。|| 猜不到的，就没法要。") == "人就只能猜。猜不到的，就没法要。"


def test_pause_after_comma_collapses():
    # ，|| → ，（不留 「，，」/多余空格）
    assert rv.clean_text("谁害的我，|| 我让她十倍奉还。") == "谁害的我，我让她十倍奉还。"
    assert rv.clean_text("这条命，|| 我自己说了算。") == "这条命，我自己说了算。"


def test_pause_plain_becomes_comma():
    # 裸气口（前面无标点）→ 逗号
    assert rv.clean_text("这不是 || 我的寝室") == "这不是，我的寝室"


def test_hook_markers_stripped():
    assert rv.clean_text("这条命，我说了算。  🪝集尾") == "这条命，我说了算。"
    assert rv.clean_text("我让她十倍奉还。  💥爽点") == "我让她十倍奉还。"
    assert rv.clean_text("粗麻、霉味。  ⚡钩子") == "粗麻、霉味。"


def test_no_leading_comma_or_double_space():
    assert rv.clean_text("|| 我自己说了算。") == "我自己说了算。"
    assert rv.clean_text("甲，乙，丙") == "甲，乙，丙"   # 合法多逗号不误collapse


# ── voice_manifest：音色键解析 + 逐句 voice_key 留痕 ──────────────────────

def test_role_key_voicemap_binding_wins():
    # voicemap 绑定优先于内置子串归类；缺 voicemap 时回退内置(demo)映射
    voicemap = {"柳娘子": {"key": "LIU_V2", "mm": "female-chengshu"}}
    assert vmf.role_key("柳娘子", voicemap) == "LIU_V2"
    assert vmf.role_key("柳娘子", {}) == "LIU"
    assert vmf.role_key("旁白", {}) == "NARR"
    assert vmf.role_key("沈念旁白", {}) == "SHEN"   # 沈念内心独白≠旁白，历史规则别回退
    assert vmf.role_key("系统", {}) == "SYS"


def test_voice_key_real_backend_uses_voicemap_key():
    # 真后端（零样本/MiniMax/火山）：voice_key=实际应用的 voicemap 音色键
    assert vmf.voice_key_for("柳娘子", {"柳娘子": {"key": "LIU_V2"}}, real_backend=True) == "LIU_V2"
    assert vmf.voice_key_for("小禾", {}, real_backend=True) == "XIAOHE"


def test_voice_key_placeholder_backend_marked():
    # 占位后端（macOS say）：记所用占位声音名并带 #placeholder 标记，不冒充 voicemap 音色
    key = vmf.voice_key_for("柳娘子", {"柳娘子": {"key": "LIU_V2"}}, real_backend=False)
    assert key == "say:Tingting" + vmf.PLACEHOLDER_SUFFIX
    assert key.endswith("#placeholder")


def _entries(real_backend):
    # 模拟 render_voice 的 manifest 构造路径（同一函数 manifest_entry，写端单一出口）
    items = [("沈念", "这不是我的脸。", "serious", 1.0, ""), ("旁白", "冷宫深处。", "neutral", 1.0, "hook")]
    voicemap = {"沈念": {"key": "SHEN"}}
    return [vmf.manifest_entry(i, f"镜头{i+1}", role, emo, hook, text, 1.5, i * 2.0, i * 2.0 + 1.5, 0.4,
                               f"line_{i:02d}.wav", voicemap, real_backend,
                               "MiniMax:female-yujie" if real_backend else "say:Tingting", "neutral",
                               is_placeholder=not real_backend)
            for i, (role, text, emo, _spd, hook) in enumerate(items)]


def test_manifest_entries_contain_voice_key_real_backend():
    # 生成的清单逐句含契约字段 voice_key（=voicemap 音色键），legacy 中文「音色键」保留兼容
    for e in _entries(real_backend=True):
        assert e[VOICE_KEY_FIELD] and e[VOICE_KEY_FIELD] == e["音色键"]
        assert "占位" not in e
    assert _entries(True)[0][VOICE_KEY_FIELD] == "SHEN"
    assert _entries(True)[1][VOICE_KEY_FIELD] == "NARR"


def test_manifest_entries_contain_voice_key_placeholder_backend():
    # say 占位轨：逐句 voice_key=say:Tingting#placeholder + 占位:true，对账方可识别需重配音
    for e in _entries(real_backend=False):
        assert e[VOICE_KEY_FIELD] == "say:Tingting#placeholder"
        assert e["占位"] is True
        assert e["音色键"]   # 音色槽仍留痕（角色本应绑哪个键）
