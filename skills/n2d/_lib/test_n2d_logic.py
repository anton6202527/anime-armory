import n2d_logic as logic


def test_normalize_production_mode_maps_post_dub_aliases_to_video_first():
    for raw in ("后配音", "后期配音", "后期配音线", "无声视频", "silent video", "video first"):
        assert logic.normalize_production_mode(raw) == "先出视频后配音"


def test_normalize_production_mode_keeps_voice_first_aliases():
    for raw in ("配音先行", "voice first", "tts first"):
        assert logic.normalize_production_mode(raw) == "配音先行"
