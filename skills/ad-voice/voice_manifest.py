#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""时长清单逐句条目构造 + 音色键解析（独立模块·带单测，render_voice 主流程可安全 import）。

广告版 VO 配音对账：voicemap.json 是 角色/旁白 → 音色注册表，时长清单每句记 voice_key
（实际应用音色键），ad-review(二期) 跨镜对账音色一致。占位后端（macOS say）记
`say:<声音名>#placeholder` 留痕，识别需重配音。自包含，不 import ad-craft。
"""

PLACEHOLDER_SUFFIX = "#placeholder"


def vm_match(role, voicemap):
    """角色/旁白名 → voicemap.json 条目（子串匹配）。无匹配返回 None。"""
    for sub, cfg in (voicemap or {}).items():
        if sub and sub in role:
            return cfg
    return None


def role_key(role, voicemap):
    """角色/旁白名 → 音色键（音色槽，跨镜应稳定）。优先 voicemap 绑定，缺则内置归类。"""
    vm = vm_match(role, voicemap)
    if vm and vm.get("key"):
        return vm["key"]
    if "旁白" in role or "VO" in role.upper():
        return "VO"
    if "男" in role:
        return "MALE"
    if "女" in role:
        return "FEMALE"
    return "VO"


def voice_key_for(role, voicemap, real_backend, placeholder_voice="Tingting"):
    """该句实际应用的 voice_key：真后端=voicemap 音色键；占位后端=say:<声音名>#placeholder。"""
    if real_backend:
        return role_key(role, voicemap)
    return f"say:{placeholder_voice}{PLACEHOLDER_SUFFIX}"


def manifest_entry(idx, role, text, dur, start, end, gap, line_wav,
                   voicemap, real_backend, is_placeholder, placeholder_voice="Tingting"):
    """时长清单.json 单句条目（字段形状单一出口，render_voice 与单测同源）。"""
    entry = {
        "idx": idx, "角色": role, "文本": text,
        "时长": round(dur, 3), "start": round(start, 3), "end": round(end, 3),
        "gap_after": round(gap, 3), "line_wav": line_wav,
        "音色键": role_key(role, voicemap),
        "voice_key": voice_key_for(role, voicemap, real_backend, placeholder_voice),
    }
    if is_placeholder:
        entry["占位"] = True
    return entry


def parse_voiceover(text):
    """voiceover.txt → [(role, line)]。支持 '旁白：…' / '角色：…' 前缀，无前缀归 旁白。"""
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for sep in ("：", ":"):
            if sep in line:
                role, _, body = line.partition(sep)
                if len(role) <= 12 and body.strip():
                    out.append((role.strip(), body.strip()))
                    break
        else:
            out.append(("旁白", line))
    return out
