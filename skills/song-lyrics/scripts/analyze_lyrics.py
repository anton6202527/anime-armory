#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze lyrics for structural symmetry, rhyme schemes, and singability.

This provides deterministic feedback to LLMs and users during the song-lyrics stage.
"""
import argparse
import json
import os
import re
import sys
try:
    import pypinyin
    HAS_PYPINYIN = True
except ImportError:
    HAS_PYPINYIN = False

SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
# Count Chinese characters and alphanumerics, ignoring punctuation
COUNT_RE = re.compile(r"[0-9A-Za-z一-鿿぀-ヿ]")


def line_chars(s):
    return len(COUNT_RE.findall(s))


def extract_last_word(line):
    # Strip punctuation from the end
    clean = re.sub(r"[^\w\s一-鿿぀-ヿ]+$", "", line.strip())
    if not clean:
        return ""
    # For Chinese, usually the last character is enough for rhyme
    # For English, it would be the last word. We'll take the last segment.
    match = re.search(r"([0-9A-Za-z]+|[一-鿿぀-ヿ])$", clean)
    return match.group(1) if match else clean[-1]


def get_rhyme_vowel(char):
    if not HAS_PYPINYIN or not re.match(r"[一-鿿]", char):
        return char # Fallback to identity if not Chinese or no pypinyin
    
    # Get pinyin without tone
    pys = pypinyin.pinyin(char, style=pypinyin.Style.NORMAL)
    if not pys:
        return char
    py = pys[0][0]
    
    # Simplified vowel extraction (finals)
    vowels = ["ang", "eng", "ing", "ong", "an", "en", "in", "un", "ao", "ou", "ai", "ei", "ui", "ao", "ou", "iu", "ie", "ve", "er", "a", "o", "e", "i", "u", "v"]
    for v in vowels:
        if py.endswith(v):
            return v
    return py[-1] if py else char


def analyze(text):
    sections = []
    current_section = None
    
    for line_num, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#") or s.startswith(">"):
            continue
            
        sec_match = SECTION_RE.match(s)
        if sec_match:
            current_section = {
                "tag": sec_match.group(1).lower(),
                "raw_tag": sec_match.group(0),
                "lines": [],
                "line_nums": []
            }
            sections.append(current_section)
        elif current_section is not None:
            if not s.startswith("（") and not s.startswith("("): # Ignore stage directions
                current_section["lines"].append(s)
                current_section["line_nums"].append(line_num)
    
    findings = []
    
    # 1. Structure Symmetry (Verse 1 vs Verse 2)
    verses = [sec for sec in sections if "verse" in sec["tag"]]
    if len(verses) >= 2:
        v1, v2 = verses[0], verses[1]
        v1_counts = [line_chars(l) for l in v1["lines"]]
        v2_counts = [line_chars(l) for l in v2["lines"]]
        
        if len(v1_counts) != len(v2_counts):
            findings.append({
                "type": "symmetry",
                "severity": "warning",
                "message": f"结构不对称：{v1['raw_tag']} 有 {len(v1_counts)} 行，但 {v2['raw_tag']} 有 {len(v2_counts)} 行。流行乐通常要求主歌行数一致以便套用相同旋律。"
            })
        else:
            diffs = [abs(c1 - c2) for c1, c2 in zip(v1_counts, v2_counts)]
            if any(d > 3 for d in diffs):
                findings.append({
                    "type": "symmetry",
                    "severity": "warning",
                    "message": f"字数不对称：{v1['raw_tag']} 与 {v2['raw_tag']} 对应行字数差异过大 (字数对比: {v1_counts} vs {v2_counts})。会导致第二段主歌难以套用第一段的旋律。"
                })

    # 2. Section Analysis & Rhyme
    for sec in sections:
        counts = [line_chars(l) for l in sec["lines"]]
        if not counts:
            continue
            
        # Extreme variance within a section
        spread = max(counts) - min(counts)
        if spread > 6:
            findings.append({
                "type": "singability",
                "severity": "warning",
                "location": sec["raw_tag"],
                "message": f"同段落行字数差异过大 (极差 {spread}，字数序列: {counts})。长短句混杂会破坏节奏，难以谱曲和演唱。"
            })
            
        # Rhyme analysis
        rhymes = []
        for line in sec["lines"]:
            last = extract_last_word(line)
            rhymes.append(get_rhyme_vowel(last))
            
        sec["rhymes"] = rhymes
        
        # Simple evaluation of rhyme consistency (are there repeating patterns?)
        if len(rhymes) >= 4:
            unique_rhymes = len(set(rhymes))
            if unique_rhymes == len(rhymes):
                findings.append({
                    "type": "rhyme",
                    "severity": "info",
                    "location": sec["raw_tag"],
                    "message": f"似乎没有明显的押韵 (句尾音节: {rhymes})。建议在偶数行或句尾使用相同的韵脚增强可记忆性。"
                })

    return {
        "sections": sections,
        "findings": findings
    }


def main():
    ap = argparse.ArgumentParser(description="分析歌词结构、对称性和押韵")
    ap.add_argument("project_root")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    lyrics_path = os.path.join(root, "词", "lyrics.md")
    
    if not os.path.exists(lyrics_path):
        print(f"[err] 找不到歌词文件：{lyrics_path}", file=sys.stderr)
        sys.exit(2)

    text = open(lyrics_path, encoding="utf-8").read()
    result = analyze(text)
    
    print(f"# 歌词深度分析报告\n")
    if not HAS_PYPINYIN:
        print("> 提示：未安装 pypinyin，押韵分析退化为基于结尾单字的简单比对。\n> 运行 `pip install pypinyin` 获取更准的拼音韵脚分析。\n")
        
    if not result["findings"]:
        print("✅ 未发现明显的结构或字数失衡问题。")
    else:
        print("## 问题与建议\n")
        for f in result["findings"]:
            loc = f.get("location", "全局")
            icon = "🔴" if f["severity"] == "error" else "🟡" if f["severity"] == "warning" else "🔵"
            print(f"- {icon} [{loc}] {f['message']}")
            
    print("\n## 段落扫描概览\n")
    for sec in result["sections"]:
        counts = [line_chars(l) for l in sec["lines"]]
        rhymes = sec.get("rhymes", [])
        print(f"- **{sec['raw_tag']}**: {len(sec['lines'])} 行")
        print(f"  - 字数序列: {counts}")
        print(f"  - 尾音序列: {rhymes}")

if __name__ == "__main__":
    main()
