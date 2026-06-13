#!/usr/bin/env python3
# 时长清单逐句条目构造 + 音色键解析（独立模块·带单测，render_voice 主流程不可安全 import）。
# 一角一色跨集对账契约：voicemap.json 是角色→音色注册表，manifest 每句记 voice_key
# （契约 n2d_contract.VOICE_KEY_FIELD = 该句实际应用的音色键），n2d-identity 的
# voice_consistency.py 跨集对账出 voice_drift_report；老清单缺该字段按 insufficient_data 跳过。
import os
import sys

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'n2d', '_lib'))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import VOICE_KEY_FIELD, VOICE_KEY_LEGACY_FIELD, VOICE_KEY_PLACEHOLDER_SUFFIX  # noqa: E402

# 占位后端（macOS say 应急轨）的 voice_key 标记后缀：记「所用占位声音名#placeholder」，
# 既留痕实际发声又显式声明这不是 voicemap 注册音色——对账方据此识别需重配音。
PLACEHOLDER_SUFFIX = VOICE_KEY_PLACEHOLDER_SUFFIX


def vm_match(role, voicemap):
    """角色名 → voicemap.json 条目（子串匹配，与 render_voice 历史行为一致）。无匹配返回 None。"""
    for sub, cfg in (voicemap or {}).items():
        if sub and sub in role:
            return cfg
    return None


def role_key(role, voicemap):
    """角色名 → 音色键（音色槽，跨集应稳定）。优先 voicemap 绑定，缺则内置(demo)子串归类。
    注意 '沈念旁白' 走 SHEN(沈念内心)，纯 '旁白' 才走 NARR(旁白)。"""
    vm = vm_match(role, voicemap)
    if vm and vm.get('key'):
        return vm['key']
    if '系统' in role:
        return 'SYS'
    if '柳娘子' in role:
        return 'LIU'
    if '小禾' in role:
        return 'XIAOHE'
    if '太监' in role:
        return 'TAIJIAN'
    if '妖' in role:
        return 'YAO'
    if role == '旁白':
        return 'NARR'
    return 'SHEN'   # 沈念旁白 / 沈念 / 默认


def voice_key_for(role, voicemap, real_backend, placeholder_voice='Tingting'):
    """该句实际应用的 voice_key：真后端（零样本克隆/MiniMax/火山）= voicemap 音色键；
    占位后端（macOS say）没有走 voicemap 选音，记 `say:<声音名>#placeholder` 留痕。"""
    if real_backend:
        return role_key(role, voicemap)
    return f'say:{placeholder_voice}{PLACEHOLDER_SUFFIX}'


def manifest_entry(idx, shot, role, emo, hook, text, dur, start, end, gap, line_wav,
                   voicemap, real_backend, voice_id, emo_applied, is_placeholder,
                   placeholder_voice='Tingting'):
    """时长清单.json 单句条目（字段形状的单一出口，render_voice 与单测同源）。
    音色键=音色槽(legacy 中文字段，保留兼容)；voice_key=契约标准字段（n2d-identity 消费）。"""
    entry = {
        "idx": idx, "镜头": shot, "角色": role, "情绪": emo, "钩子": hook, "文本": text,
        "时长": round(dur, 3), "start": round(start, 3), "end": round(end, 3),
        "gap_after": round(gap, 3), "line_wav": line_wav,
        VOICE_KEY_LEGACY_FIELD: role_key(role, voicemap),
        VOICE_KEY_FIELD: voice_key_for(role, voicemap, real_backend, placeholder_voice),
        "voice_id": voice_id, "情绪_已应用": emo_applied,
    }
    if is_placeholder:
        entry["占位"] = True
    return entry
