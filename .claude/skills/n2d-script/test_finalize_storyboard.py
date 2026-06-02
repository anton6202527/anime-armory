import finalize_storyboard as F

def test_build_srt_and_shots():
    manifest=[
        {"idx":0,"镜头":"镜头1","角色":"沈念","文本":"甲。","时长":2.0},
        {"idx":1,"镜头":"镜头1","角色":"沈念","文本":"乙。","时长":1.0},
        {"idx":2,"镜头":"镜头2","角色":"柳娘子","文本":"丙。","时长":3.0},
    ]
    en=["A.","B.","C."]
    zh_srt, en_srt, shots = F.build(manifest, en, gap=0.5)
    # 3 cues, back-to-back with 0.5s gaps: c0 0-2, c1 2.5-3.5, c2 4-7
    assert "00:00:00,000 --> 00:00:02,000" in zh_srt
    assert "甲。" in zh_srt
    assert "00:00:02,500 --> 00:00:03,500" in zh_srt
    assert "00:00:04,000 --> 00:00:07,000" in zh_srt
    assert "A." in en_srt and "C." in en_srt
    assert "00:00:04,000 --> 00:00:07,000" in en_srt  # same timecodes
    # shot durations: 镜头1 = 2+1 +gap = 3.5 ; 镜头2 = 3 +gap = 3.5
    assert abs(shots["镜头1"]-3.5)<1e-6
    assert abs(shots["镜头2"]-3.5)<1e-6
