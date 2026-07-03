from typing import Any, Dict, Sequence

_MODEL_FAMILIES: Dict[str, Sequence[str]] = {
    "openai": ("gpt", "openai", "dall-e", "dalle", "sora", "chatgpt", "o1-", "o3-", "o4-"),
    "google": ("gemini", "veo", "imagen", "bard"),
    "anthropic": ("claude", "opus", "sonnet", "haiku"),
    "bytedance": ("seedream", "seedance", "doubao", "jimeng", "dreamina", "即梦", "豆包"),
    "kuaishou": ("kling", "kolors", "keling", "可灵"),
    "alibaba": ("wanx", "wan2", "万相", "qwen", "tongyi", "通义"),
    "minimax": ("minimax", "hailuo", "海螺", "abab"),
    "tencent": ("hunyuan", "混元"),
    "baidu": ("ernie", "文心"),
}

def model_family(name: Any) -> str:
    low = str(name or "").strip().lower()
    if not low:
        return ""
    for family, markers in _MODEL_FAMILIES.items():
        if any(marker in low for marker in markers):
            return family
    return ""

