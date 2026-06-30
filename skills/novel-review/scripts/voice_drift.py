#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
voice_drift.py — 角色语感/口头禅漂移哨兵（确定性扫描，纯标准库 · advisory-only）

人设崩是网文头号痛点；笔灵/星月一类工具的卖点正是"口头禅 + 语感锁人设"。
`设定/角色语感.json` 被 novel-craft 注入写作包(draft_packets.py)，却没有任何东西回头**校验**
角色的口头禅是否还在、对白语感有没有跑偏。本哨兵补这一刀。

诚实声明（中文对白归属本就难，所以全程保守、只报建议级）：
  - extract_dialogue(text, name) 用**邻近 + 提示动词**启发式归属对白，不做共指消解，
    会漏（旁白转述的台词、连续对话省略说话人）也可能多（同窗口里别人的引号）。
  - 因此本检测器**不出阻断级**：语感是"软"约束，口头禅偶尔不出现不等于人设崩，
    只作为"请人复核"的候选信号（与 logic_sentry 的 location_jump 同一保守等级）。

设定/角色语感.json 形状（与 novel-craft/draft_packets.py 消费端对齐，**容错**两种写法）：
  规范形（craft 注入消费的字段）::
    {
      "沈砚": {
        "口头禅": ["哼", "本座说过"],            # 或 catchphrases
        "syntax_profile": {"avg_sentence_length": 8,
                           "short_sentence_ratio": .., "long_sentence_ratio": ..},
        "lexicon_anchor": [{"term": "本座"}, ...]
      }
    }
  宽松形（人手写、字段少）::
    {"沈砚": {"口头禅": ["哼"], "语气": "冷峭", "句长": "短"}}
  两种都吃：口头禅取 口头禅/catchphrases；句长 band 取 syntax_profile.avg_sentence_length
  （数值优先）否则 句长(短/中/长) 文字档。缺字段=跳过该维度，不臆造。

  python3 voice_drift.py <作品根> [--json]

测试：cd skills/novel-review/scripts && python3 -m pytest test_voice_drift.py
"""
import os
import re
import sys
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILLS = os.path.abspath(os.path.join(_HERE, "..", ".."))
_WIKI = os.path.join(_SKILLS, "novel-wiki", "scripts")
if _WIKI not in sys.path:
    sys.path.insert(0, _WIKI)
try:  # 复用 wiki 的章节迭代（fill_missing_numbers=True，与 logic_sentry 同源）
    from wiki_builder import list_chapters
except Exception:  # pragma: no cover - 优雅降级
    list_chapters = None

# 说话提示动词：引号紧邻这些字之一才认定为"某角色说的话"。保守取常见的一批。
# 刻意不收单字"答"/"问"——它们极易撞旁白(回答/没有回答/疑问/学问)造成误归；
# 用复合形(回道/应道/反问/质问)代替。同理"说"/"道"靠复合或邻接颜面控制误报。
SPEECH_VERBS = ["说", "道", "喝道", "冷笑", "笑道", "叹道", "怒道",
                "低语", "喃", "喊", "嘀咕", "回道", "应道", "反问", "质问", "厉声", "轻声"]
# 引号对（中文「」『』 + 中英双引号）。每对 (开, 闭)。
QUOTE_PAIRS = [("「", "」"), ("『", "』"), ("“", "”"), ('"', '"')]
# 名字↔引号的邻近窗口（字符）：名字须落在引号前 ATTR_BEFORE 字内，或引号后 ATTR_AFTER 字内。
ATTR_BEFORE = 14
ATTR_AFTER = 12
# 句长 band：观测句均长偏离登记 band 超过此比例(±)才报（建议级）。语感软，给宽容。
SENT_LEN_TOLERANCE = 0.5
# 文字句长档 → 代表字数（仅在无数值 avg_sentence_length 时用作粗 band）。
TEXTUAL_LEN_BAND = {"短": 8.0, "中": 16.0, "长": 28.0}
# 角色至少说够这么多句，才对其口头禅缺席下"消失"判断（话太少不足以判，宁缺毋滥）。
MIN_LINES_FOR_BAND = 3
_SENT_SPLIT = re.compile(r"[。！？!?]+")


def _as_list(value):
    """容错：None→[]，标量→[str]，列表→[str,...]（丢空串）。与 logic_sentry 同语义。"""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    s = str(value).strip()
    return [s] if s else []


def _find_quotes(text):
    """返回 [(start_of_open, end_after_close, inner_text)]，非贪婪、不跨同类型嵌套。"""
    spans = []
    for open_q, close_q in QUOTE_PAIRS:
        i = 0
        n = len(text)
        while True:
            a = text.find(open_q, i)
            if a < 0:
                break
            # 直引号开=闭，从 a+1 找下一个；非对称引号正常找闭。
            b = text.find(close_q, a + 1)
            if b < 0:
                break
            inner = text[a + len(open_q):b]
            if inner.strip():
                spans.append((a, b + len(close_q), inner.strip()))
            i = b + len(close_q)
    spans.sort(key=lambda s: s[0])
    return spans


def extract_dialogue(text, name):
    """抽取 `name` 在 text 里说的台词引文列表（启发式归属）。

    启发式：对每段引号「…」/"…"，若其**前 ATTR_BEFORE 字**或**后 ATTR_AFTER 字**窗口里
    同时出现「name」与某个说话提示动词(说/道/问/喝道/冷笑…)，就把该引文判为此角色所说。
    覆盖两种常见语序——
        沈砚冷笑道：「哼。」          （名字+动词 在引号前）
        「哼。」沈砚冷笑了一声        （名字+动词 在引号后）
    局限（已知会漏/会多，故全检测器只出建议级）：
      * 不做共指/代词消解——"他冷笑道"不会归到 name；
      * 连续对话里省略说话人的后续引号会漏；
      * 若窗口里恰好另有他人名+动词，可能误归（窗口收得很窄以压制）。
    """
    if not name or not text:
        return []
    out = []
    for a, end, inner in _find_quotes(text):
        before = text[max(0, a - ATTR_BEFORE):a]
        after = text[end:end + ATTR_AFTER]
        # 名字与动词必须落在**同一侧**窗口，避免"前窗有名字、后窗才有动词"这种跨引号拼凑。
        name_before, verb_before = name in before, any(v in before for v in SPEECH_VERBS)
        name_after, verb_after = name in after, any(v in after for v in SPEECH_VERBS)
        if (name_before and verb_before) or (name_after and verb_after):
            out.append(inner)
    return out


def catchphrase_coverage(dialogue_lines, catchphrases):
    """{口头禅: 在该角色全部台词里的出现次数}。catchphrases 容错成 list。"""
    phrases = _as_list(catchphrases)
    joined = "\n".join(dialogue_lines or [])
    cov = {}
    for ph in phrases:
        # count 不重叠子串计数；空短语跳过。
        cov[ph] = joined.count(ph) if ph else 0
    return cov


def avg_sentence_len(dialogue_lines):
    """台词按 。！？!? 切句后的平均句长（字数）。无句→0.0。"""
    joined = "".join(dialogue_lines or [])
    if not joined:
        return 0.0
    sents = [s.strip() for s in _SENT_SPLIT.split(joined) if s.strip()]
    if not sents:
        # 没有终止标点但有内容：整体算一句。
        return float(len(joined))
    return round(sum(len(s) for s in sents) / len(sents), 2)


def _registered_len_band(profile):
    """从 profile 取登记句长基准(字数)：syntax_profile.avg_sentence_length 优先，
    否则 句长(短/中/长) 文字档映射。取不到→None（跳过句长维度）。"""
    sp = profile.get("syntax_profile") if isinstance(profile, dict) else None
    if isinstance(sp, dict):
        v = sp.get("avg_sentence_length")
        try:
            if v is not None:
                return float(v)
        except (TypeError, ValueError):
            pass
    band = (profile or {}).get("句长") or (profile or {}).get("sentence_band")
    if isinstance(band, str):
        for key, val in TEXTUAL_LEN_BAND.items():
            if key in band:
                return val
    return None


def voice_drift_band(registered_profile, observed):
    """对单个角色的语感对账，返回 alerts 列表（建议级，可能空）。纯函数·可测。

    registered_profile：该角色的 设定/角色语感.json 条目（dict）。
    observed：{"name","line_count","coverage":{phrase:count},"avg_len":float}。

    规则（全建议级，理由见模块 docstring：语感软，不出阻断）：
      (a) 口头禅消失——某登记口头禅在该角色台词里 0 次出现，**且**该角色确实说够了话
          (line_count >= MIN_LINES_FOR_BAND)。话太少不判（不足以认定"消失"）。
      (b) 句均长偏移——观测句均长相对登记 band 偏离 > SENT_LEN_TOLERANCE，且说够了话。
    """
    profile = registered_profile or {}
    name = observed.get("name", "?")
    line_count = int(observed.get("line_count", 0) or 0)
    coverage = observed.get("coverage", {}) or {}
    alerts = []

    spoke_enough = line_count >= MIN_LINES_FOR_BAND
    if spoke_enough:
        for phrase, count in coverage.items():
            if count == 0:
                alerts.append({
                    "type": "catchphrase_dropped", "entity": name, "severity": "建议级",
                    "chapter": observed.get("chapter"),
                    "phrase": phrase, "line_count": line_count,
                    "evidence": f"{name} 本窗口共 {line_count} 句台词，登记口头禅「{phrase}」0 次出现",
                    "auto": True,
                    "note": (f"角色「{name}」的登记口头禅「{phrase}」在其对白中消失（说了 {line_count} 句却一次没用）"
                             "——口头禅是人设锚点，请人判：是否人设漂移/该角色这段确实不该说它"),
                })

    band = _registered_len_band(profile)
    avg_len = float(observed.get("avg_len", 0.0) or 0.0)
    if spoke_enough and band and band > 0 and avg_len > 0:
        deviation = abs(avg_len - band) / band
        if deviation > SENT_LEN_TOLERANCE:
            direction = "更长" if avg_len > band else "更短"
            alerts.append({
                "type": "voice_drift", "entity": name, "severity": "建议级",
                "chapter": observed.get("chapter"),
                "registered_len": round(band, 2), "observed_len": round(avg_len, 2),
                "deviation": round(deviation, 2), "line_count": line_count,
                "evidence": f"{name} 台词句均长 {avg_len:g} 字 vs 登记 {band:g} 字（偏离 {deviation:.0%}，{direction}）",
                "auto": True,
                "note": (f"角色「{name}」对白句均长偏离登记语感 band 较大（{direction}）"
                         "——语感软约束，仅建议人判：是否情绪场景导致的合理变化"),
            })
    return alerts


def _catchphrases_of(profile):
    """从角色 profile 取口头禅列表：口头禅 / catchphrases 任一。"""
    if not isinstance(profile, dict):
        return []
    return _as_list(profile.get("口头禅") or profile.get("catchphrases"))


def analyze(project, window=None):
    """跨章聚合每个登记角色的台词，跑 band，返回 {"alerts":[...], "characters":{...}}。

    window：章节范围 (lo, hi)（含）；None=全书。
    设定/角色语感.json 缺失→优雅跳过，返回带 skipped 说明的结果（不臆造、留痕）。
    """
    voice_path = os.path.join(project, "设定", "角色语感.json")
    if not os.path.isfile(voice_path):
        return {"alerts": [], "characters": {},
                "skipped": f"无 {voice_path}——先在 novel-craft 建立角色语感画像，本检测器跳过"}
    try:
        with open(voice_path, "r", encoding="utf-8") as f:
            voices = json.load(f)
    except Exception as e:  # pragma: no cover - 坏 json 优雅跳过
        return {"alerts": [], "characters": {}, "skipped": f"角色语感.json 解析失败：{e}"}
    if not isinstance(voices, dict) or not voices:
        return {"alerts": [], "characters": {}, "skipped": "角色语感.json 为空或非对象"}

    if list_chapters is None:
        return {"alerts": [], "characters": {}, "skipped": "无法导入 wiki_builder.list_chapters"}

    # 跨章聚合每个角色的台词。
    agg = {name: [] for name in voices}
    for idx, _, text in list_chapters(project):
        if window and not (window[0] <= idx <= window[1]):
            continue
        for name in voices:
            agg[name].extend(extract_dialogue(text, name))

    alerts = []
    characters = {}
    for name, profile in voices.items():
        lines = agg.get(name, [])
        phrases = _catchphrases_of(profile)
        coverage = catchphrase_coverage(lines, phrases)
        avg_len = avg_sentence_len(lines)
        observed = {"name": name, "line_count": len(lines),
                    "coverage": coverage, "avg_len": avg_len, "chapter": None}
        char_alerts = voice_drift_band(profile, observed)
        alerts.extend(char_alerts)
        characters[name] = {
            "line_count": len(lines),
            "catchphrases": phrases,
            "coverage": coverage,
            "avg_sentence_len": avg_len,
            "registered_len_band": _registered_len_band(profile),
            "alerts": len(char_alerts),
        }
    return {"alerts": alerts, "characters": characters}


def main(argv=None):
    p = argparse.ArgumentParser(description="角色语感/口头禅漂移哨兵（advisory-only）")
    p.add_argument("project_path")
    p.add_argument("--json", action="store_true", help="把完整结果打到 stdout")
    p.add_argument("--from", dest="lo", type=int, default=None, help="窗口起始章号")
    p.add_argument("--to", dest="hi", type=int, default=None, help="窗口结束章号")
    args = p.parse_args(argv)

    window = None
    if args.lo is not None or args.hi is not None:
        window = (args.lo or 0, args.hi if args.hi is not None else 10 ** 9)

    result = analyze(args.project_path, window=window)

    out_dir = os.path.join(args.project_path, "审稿")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "voice_findings.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result.get("skipped"):
        print(f"⏭️ 角色语感漂移：跳过（{result['skipped']}）→ {out_path}")
    else:
        alerts = result["alerts"]
        if alerts:
            print(f"⚠️ 角色语感漂移：{len(alerts)} 条建议级候选 → {out_path}")
            for a in alerts:
                print(f"  [{a['severity']}] {a['type']} · {a['entity']} · {a['evidence']}")
        else:
            print(f"✅ 角色语感漂移：0 候选 → {out_path}")
    # advisory-only：永远 exit 0（语感软，不硬挡 post_write）。
    return 0


if __name__ == "__main__":
    sys.exit(main())
