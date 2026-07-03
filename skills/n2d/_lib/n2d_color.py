#!/usr/bin/env python3
"""n2d 暖冷/品绿色彩度量单一真值源（image 色调契约 + review 调色一致性共用同一公式）。

此前「暖冷」有两套**不可比**公式：image 侧 tone_light_contract 用线性 R−B（亮度相关），
review 侧 color_grade_consistency 用 log(R/B)（亮度无关）——同一帧两边数值不可比、阈值无法互转。
本模块统一成 log 比值（亮度无关、对应色温），两侧都从这里取公式：
  · image 侧 tone_light_contract：整集中位数 vs 契约意图（**绝对**·暖/冷/中性，阈值=neutral 区半宽）。
  · review 侧 color_grade_consistency：每镜 vs 同场景中位（**相对**·横跳，阈值=允许偏离）。
两者度量同一个量（本模块），只是比较对象/阈值语义不同——口径一致、可互相参照。

+1 平滑避免 log(0)。纯函数·无依赖·可测。
"""
from __future__ import annotations

import math


def warmth_log_ratio(r: float, g: float, b: float) -> float:
    """暖冷 = log((R+1)/(B+1))：暖(琥珀)>0、冷(蓝)<0。亮度无关（比值），对应色温高低。"""
    return math.log((float(r) + 1.0) / (float(b) + 1.0))


def tint_log_ratio(r: float, g: float, b: float) -> float:
    """品绿 tint = log((G+1)/sqrt((R+1)(B+1)))：偏绿>0、偏品红<0。"""
    r1, g1, b1 = float(r) + 1.0, float(g) + 1.0, float(b) + 1.0
    return math.log(g1 / math.sqrt(r1 * b1))


def grade_proxy(r: float, g: float, b: float) -> tuple:
    """通道均值 → (暖冷, 品绿) log 比值对。"""
    return warmth_log_ratio(r, g, b), tint_log_ratio(r, g, b)
