import finalize_storyboard as F

def test_build_legacy_manifest_reconstructs_timeline():
    # 旧 manifest（无 start/end）：按 gap 模型重建，末句不留拍
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
    # 镜头占屏=台词+其后留拍：镜头1=(2+0.5)+(1+0.5)=4.0；镜头2=3+0(末句不留拍)=3.0；∑=7.0==末句end
    assert abs(shots["镜头1"]-4.0)<1e-6
    assert abs(shots["镜头2"]-3.0)<1e-6
    assert abs(shots["镜头1"]+shots["镜头2"]-7.0)<1e-6

def test_build_uses_real_timeline_when_present():
    # 新 manifest：直接消费 render_voice 写入的 start/end/gap_after（钩子句留拍不一致）
    manifest=[
        {"idx":0,"镜头":"镜头1","文本":"甲。","时长":2.0,"start":0.0,"end":2.0,"gap_after":0.6,"钩子":"hook"},
        {"idx":1,"镜头":"镜头1","文本":"乙。","时长":1.0,"start":2.6,"end":3.6,"gap_after":1.0,"钩子":"end"},
        {"idx":2,"镜头":"镜头2","文本":"丙。","时长":3.0,"start":4.6,"end":7.6,"gap_after":0.0,"钩子":""},
    ]
    zh_srt, _, shots = F.build(manifest, ["A.","B.","C."])
    # 字幕用真实 start/end，不再用常数 gap 重建
    assert "00:00:02,600 --> 00:00:03,600" in zh_srt
    assert "00:00:04,600 --> 00:00:07,600" in zh_srt
    # 镜头1=(2+0.6)+(1+1.0)=4.6；镜头2=3+0=3.0；∑=7.6==末句end（==voice.wav 时长）
    assert abs(shots["镜头1"]-4.6)<1e-6
    assert abs(shots["镜头2"]-3.0)<1e-6
    assert abs(shots["镜头1"]+shots["镜头2"]-7.6)<1e-6
