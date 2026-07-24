#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""反向防瞎编机检（source fabrication·advisory）——参照同仓成熟视频线
source_adaptation_audit --check-fabrication 的漫画重实现，不跨线 import。

为什么存在：source_semantics_gate 只查 source→panel 的**前向覆盖**（源文段落漏没漏），
entity_presence_audit 只查「提到已登记实体绑没绑」；没有任何脚本查**反向**——
分格脚本里出现、源文没有、也没有任何有账登记的专名/称谓（凭空多出一个人物/
门派/法宝），改编越自由越容易发生，读者与后续话次却会把它当既定设定。

只认可确定性最高的两类信号（高召回低误报代理·与视频线同口径）：
  ① 专名括注：【…】《…》；
  ② 称谓复合词：X娘娘/X长老/X宗主/X道长…（1-4 个汉字前缀 + 称谓后缀）。
裸人名不查——中文无分词、无模型必误伤。

授权来源（命中任一即不算瞎编）：
  A. 源文：源本/*.txt 全文 + 各格 source_excerpt（已审源段语义）→ 有出处，不报；
  B. 实体注册表 display_name/aliases → 有账改编实体，info（adaptation_new_term_accounted）；
  C. 设定库/story_bible.md、开发包/*.json|md → 立项期有账设定，info；
  其余 → warn（fabricated_entity_candidate）：确认是源文别名/合并小角色（去注册表或
  开发包登记），还是应删除。

诚实边界：本检治「凭空引入命名设定」，不治情节瞎编（那要人审）；称谓表按古典/仙侠
语料扩充过，题材外新称谓要自行续表。report-only：进 gate 后 must→warn，不阻断。

用法（与本线其它 advisory 机检同签名）：
  python3 source_fabrication_audit.py <作品根> 第N话 [--write] [--json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Set

VERSION = 1
KIND = "comic_source_fabrication_audit"

# 读者实际读到的字段（对白/旁白/嵌字目标）；description 是画面承诺——瞎编实体会被画出来，
# 同样纳入。craft 纯技术字段（spatial_layout/lighting_anchor 等）不查，避免误报。
READER_FIELDS = ("text_target", "dialogue", "narration")
VISUAL_FIELDS = ("description",)

BRACKET_RE = re.compile(r"(【[^】]{2,40}】|《[^》]{2,40}》)")
# 称谓后缀：视频线原表 + 古典/志怪语料常见（聊斋/公案/仙侠）。
TITLE_SUFFIXES = (
    "娘娘", "王爷", "师尊", "陛下", "公主", "太子", "小姐", "少爷", "夫人", "长老",
    "师兄", "师姐", "宗主", "皇后", "贵妃", "将军", "侍卫", "掌门",
    "道长", "真人", "上人", "居士", "员外", "相公", "郎君", "妈妈", "婆婆", "仙子",
)
TITLE_RE = re.compile(r"([一-鿿]{1,4}(?:" + "|".join(TITLE_SUFFIXES) + r"))")
# 前缀是虚词/连接词碎片 → 不是专名（"要是夫人""就是长老"）。
TITLE_FALSE_PREFIX_FRAGMENTS = {
    "要是", "就是", "不是", "还是", "若是", "可是", "但是", "叫", "让", "被", "把", "给",
    "向", "对", "跟", "同", "和", "在", "从", "到", "为", "替", "请", "问", "说", "喊",
    "看", "听", "见", "以为",
}
# 泛指前缀 → 不是特定人物（"一位夫人""那个道长"）。
TITLE_GENERIC_PREFIXES = {"一个", "这个", "那个", "那位", "这位", "某个", "某位", "几位", "诸位", "一位"}
FAB_LEADING_CONNECTIVES = set("是这那有叫让被把请问说喊看听见和跟同对向从到为替给过与共携随邀迎拜访")
# 前缀含体助词/结构助词 → 是动词短语不是专名（"果然成了将军""做了夫人"）。
PREFIX_PARTICLES = set("了的地得着")
STOP_TERMS = {"系统", "面板", "任务", "奖励", "提示", "宿主", "警告", "检测"}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def normalize_chapter(value: str) -> str:
    value = str(value or "").strip()
    return value if value.startswith("第") else f"第{value}话"


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def entity_core(term: str) -> str:
    core = term.strip("【】《》").strip()
    while len(core) > 2 and core[0] in FAB_LEADING_CONNECTIVES:
        core = core[1:]
    return core


def title_terms(text: str) -> List[str]:
    out: List[str] = []
    for m in TITLE_RE.finditer(text or ""):
        term = m.group(1)
        prefix = term
        for suffix in TITLE_SUFFIXES:
            if term.endswith(suffix):
                prefix = term[: -len(suffix)]
                break
        if not prefix or prefix in TITLE_GENERIC_PREFIXES:
            continue
        if any(prefix.endswith(frag) or prefix == frag for frag in TITLE_FALSE_PREFIX_FRAGMENTS):
            continue
        if any(ch in PREFIX_PARTICLES for ch in prefix):
            continue
        out.append(term)
    return out


def important_terms(text: str) -> List[str]:
    seen: Set[str] = set()
    terms: List[str] = []
    for m in BRACKET_RE.finditer(text or ""):
        term = m.group(1).strip()
        if term and term not in seen:
            seen.add(term)
            terms.append(term)
    for term in title_terms(text or ""):
        if term not in seen:
            seen.add(term)
            terms.append(term)
    return terms


def source_corpus(root: Path, panels: Sequence[Mapping[str, Any]]) -> str:
    chunks: List[str] = []
    source_dir = root / "源本"
    if source_dir.is_dir():
        for path in sorted(source_dir.glob("*.txt")):
            try:
                chunks.append(path.read_text(encoding="utf-8"))
            except OSError:
                continue
    for panel in panels:
        excerpt = str(panel.get("source_excerpt") or "")
        if excerpt:
            chunks.append(excerpt)
    return "\n".join(chunks)


def registry_name_corpus(root: Path) -> str:
    registry = load_json(root / "出图" / "共享" / "identity_registry.json", {}) or {}
    assets = registry.get("assets") if isinstance(registry.get("assets"), Mapping) else {}
    names: List[str] = []
    for asset in assets.values():
        if not isinstance(asset, Mapping):
            continue
        for key in ("display_name", "name"):
            value = str(asset.get(key) or "").strip()
            if value:
                names.append(value)
        for alias in asset.get("aliases") or []:
            value = str(alias).strip()
            if value:
                names.append(value)
    return "\n".join(names)


def ledger_corpus(root: Path) -> str:
    chunks: List[str] = []
    bible = root / "设定库" / "story_bible.md"
    if bible.is_file():
        try:
            chunks.append(bible.read_text(encoding="utf-8"))
        except OSError:
            pass
    pack_dir = root / "开发包"
    if pack_dir.is_dir():
        for path in sorted(pack_dir.iterdir()):
            if path.suffix.lower() in (".json", ".md") and path.is_file():
                try:
                    chunks.append(path.read_text(encoding="utf-8"))
                except OSError:
                    continue
    return "\n".join(chunks)


def audit(root: Path, chapter: str) -> Dict[str, Any]:
    chapter = normalize_chapter(chapter)
    script_payload = load_json(root / "脚本" / chapter / "panel_script.json", {}) or {}
    panels = [p for p in script_payload.get("panels") or [] if isinstance(p, Mapping)]
    findings: List[Dict[str, Any]] = []
    checked_terms = 0
    if panels:
        source = source_corpus(root, panels)
        registry_names = registry_name_corpus(root)
        ledger = ledger_corpus(root)
        reported: Set[str] = set()
        for panel in panels:
            panel_id = str(panel.get("panel_id") or "")
            for field_group, fields in (("reader", READER_FIELDS), ("visual", VISUAL_FIELDS)):
                for field in fields:
                    text = str(panel.get(field) or "")
                    if not text:
                        continue
                    for term in important_terms(text):
                        core = entity_core(term)
                        if len(core) < 2 or core in STOP_TERMS or core in reported:
                            continue
                        if term in source or core in source:
                            continue  # 源文有出处
                        reported.add(core)
                        checked_terms += 1
                        if core in registry_names:
                            findings.append({
                                "severity": "info", "code": "adaptation_new_term_accounted",
                                "panel_id": panel_id, "term": core, "field": field,
                                "message": f"{panel_id} {field} 出现源文没有的专名/称谓「{core}」，但实体注册表已登记——按有账改编处理。",
                            })
                            continue
                        if core in ledger:
                            findings.append({
                                "severity": "info", "code": "adaptation_new_term_accounted",
                                "panel_id": panel_id, "term": core, "field": field,
                                "message": f"{panel_id} {field} 出现源文没有的专名/称谓「{core}」，但 story_bible/开发包已登记——按有账改编处理。",
                            })
                            continue
                        where = "读者文本" if field_group == "reader" else "画面描述（会被画出来）"
                        findings.append({
                            "severity": "warn", "code": "fabricated_entity_candidate",
                            "panel_id": panel_id, "term": core, "field": field,
                            "message": f"{panel_id} {where}出现源文没有、也无有账登记的专名/称谓「{core}」——疑似瞎编/自造设定；"
                                       "确认是源文别名/合并小角色（去实体注册表或开发包登记），还是应删除。",
                        })
    warn_count = sum(1 for f in findings if f["severity"] == "warn")
    info_count = sum(1 for f in findings if f["severity"] == "info")
    return {
        "schema_version": VERSION,
        "kind": KIND,
        "chapter": chapter,
        "created_at": now_iso(),
        "summary": {
            "panels": len(panels),
            "terms_flagged": checked_terms,
            "warn": warn_count,
            "info": info_count,
            "must": 0,
        },
        "findings": findings,
    }


def render_md(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        f"# 反向防瞎编机检 · {report.get('chapter')}",
        "",
        f"- 格 {summary.get('panels', 0)} · 新专名/称谓 {summary.get('terms_flagged', 0)}"
        f" · warn {summary.get('warn', 0)} · info {summary.get('info', 0)}",
        "",
        "## Findings",
        "",
    ]
    findings = report.get("findings") or []
    if not findings:
        lines.append("- ✅ 分格脚本未出现源文之外、无账登记的专名/称谓。")
    for item in findings:
        lines.append(f"- [{item.get('severity')}] {item.get('message')}")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project_root")
    parser.add_argument("chapter")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.project_root).expanduser().resolve()
    report = audit(root, args.chapter)
    if args.write:
        out_dir = root / "生产数据"
        out_dir.mkdir(parents=True, exist_ok=True)
        chapter = report["chapter"]
        (out_dir / f"{KIND}_{chapter}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out_dir / f"{KIND}_{chapter}.md").write_text(render_md(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        summary = report["summary"]
        print(f"source_fabrication_audit: panels={summary['panels']} warn={summary['warn']} info={summary['info']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
