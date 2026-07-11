import n2d_logic as logic


def test_mixed_auto_routing_is_default_and_normalizes_aliases():
    assert logic.PRODUCTION_MODE_DEFAULT == "混合自动路由"
    for raw in ("混合自动路由", "按镜头路由", "hybrid", "mixed per-shot"):
        assert logic.normalize_production_mode(raw) == "混合自动路由"
    assert logic.production_mode_keys()[0] == "混合自动路由"


def test_normalize_production_mode_maps_post_dub_aliases_to_video_first():
    for raw in ("后配音", "后期配音", "后期配音线", "无声视频", "silent video", "video first"):
        assert logic.normalize_production_mode(raw) == "先出视频后配音"


def test_normalize_production_mode_keeps_voice_first_aliases():
    for raw in ("配音先行", "voice first", "tts first"):
        assert logic.normalize_production_mode(raw) == "配音先行"
