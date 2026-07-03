from urllib.parse import parse_qs, urlparse

from gptsovits_adapter import endpoint_candidates, official_gptsovits_url


def _query(url):
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


def test_gptsovits_candidates_include_official_api_fallback():
    urls = endpoint_candidates(
        "GPT-SoVITS",
        "http://127.0.0.1:9880",
        "一句测试台词。",
        "/tmp/ref.wav",
        "参考文本。",
        speed=3.5,
    )
    assert [kind for kind, _url in urls] == ["official_gptsovits", "cosy_style"]
    assert urls[1][1].startswith("http://127.0.0.1:9880/inference_zero_shot?")

    official = urls[0][1]
    assert official.startswith("http://127.0.0.1:9880/?")
    q = _query(official)
    assert q["refer_wav_path"] == "/tmp/ref.wav"
    assert q["prompt_text"] == "参考文本。"
    assert q["prompt_language"] == "zh"
    assert q["text"] == "一句测试台词。"
    assert q["text_language"] == "zh"
    assert q["speed"] == "3.5"


def test_official_gptsovits_strips_compat_endpoint_suffix():
    url = official_gptsovits_url(
        "http://127.0.0.1:9880/inference_zero_shot",
        "hello",
        None,
        None,
        text_language="en",
        speed=2.0,
    )
    assert url.startswith("http://127.0.0.1:9880/?")
    assert _query(url)["text_language"] == "en"
    assert _query(url)["speed"] == "2.0"


def test_gptsovits_explicit_compat_url_keeps_compat_first():
    urls = endpoint_candidates(
        "GPT-SoVITS",
        "http://127.0.0.1:9880/inference_zero_shot",
        "一句测试台词。",
        "/tmp/ref.wav",
        "参考文本。",
    )
    assert [kind for kind, _url in urls] == ["cosy_style", "official_gptsovits"]
