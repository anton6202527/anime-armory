import json
import os
import subprocess
import sys

import finalize_storyboard as F

_HERE = os.path.dirname(os.path.abspath(__file__))


def _write_manifest(root, ep, manifest):
    d = os.path.join(root, "合成", ep, "配音")
    os.makedirs(d, exist_ok=True)
    os.makedirs(os.path.join(root, "脚本", ep), exist_ok=True)
    json.dump(manifest, open(os.path.join(d, "时长清单.json"), "w", encoding="utf-8"),
              ensure_ascii=False)


def test_placeholder_gate_blocks_finalize(tmp_path):
    # 占位音色定稿会污染镜头时长 → finalize 必须拒绝（退出码 2），除非 FINALIZE_ALLOW_PLACEHOLDER=1
    # 本用例显式写入「配音先行」以固定占位闸门语义。
    root, ep = str(tmp_path), "第1集"
    _write_manifest(root, ep, [
        {"idx": 0, "镜头": "镜头1", "文本": "甲。", "时长": 2.0, "占位": True},
        {"idx": 1, "镜头": "镜头1", "文本": "乙。", "时长": 1.0},
    ])
    open(os.path.join(root, "_设置.md"), "w", encoding="utf-8").write("# _设置\n## 选择\n- 制作模式: 配音先行\n")
    cmd = [sys.executable, os.path.join(_HERE, "finalize_storyboard.py"), root, ep]
    blocked = subprocess.run(cmd, capture_output=True, text=True)
    assert blocked.returncode == 2 and "拒绝定稿" in blocked.stdout
    # 放行开关：产出镜头时长.json
    allowed = subprocess.run(cmd, capture_output=True, text=True,
                             env={**os.environ, "FINALIZE_ALLOW_PLACEHOLDER": "1"})
    assert allowed.returncode == 0
    assert os.path.exists(os.path.join(root, "脚本", ep, "镜头时长.json"))

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


def test_finalize_syncs_storyboard_clip_durations_from_voiceover_indices(tmp_path):
    root, ep = str(tmp_path), "第1集"
    _write_manifest(root, ep, [
        {"idx": 0, "镜头": "镜头1", "文本": "甲。", "时长": 2.0, "start": 0.0, "end": 2.0, "gap_after": 0.5},
        {"idx": 1, "镜头": "镜头2", "文本": "乙。", "时长": 3.0, "start": 2.5, "end": 5.5, "gap_after": 0.0},
    ])
    sb_p = os.path.join(root, "脚本", ep, "storyboard.json")
    json.dump({
        "total_duration": 99,
        "clips": [
            {"id": "EP01_CLIP01", "duration": 1, "voiceover_indices": [1]},
            {"id": "EP01_CLIP02", "duration": 1, "voiceover_indices": [2]},
        ],
    }, open(sb_p, "w", encoding="utf-8"), ensure_ascii=False)

    r = subprocess.run(
        [sys.executable, os.path.join(_HERE, "finalize_storyboard.py"), root, ep],
        capture_output=True,
        text=True,
    )

    assert r.returncode == 0, r.stdout + r.stderr
    sb = json.load(open(sb_p, encoding="utf-8"))
    assert sb["clips"][0]["duration"] == 2.5
    assert sb["clips"][1]["duration"] == 3.0
    assert sb["clips"][0]["start_sec"] == 0.0
    assert sb["clips"][0]["end_sec"] == 2.5
    assert sb["clips"][1]["start_sec"] == 2.5
    assert sb["clips"][1]["end_sec"] == 5.5
    assert sb["total_duration"] == 5.5
    assert "回填 2 个 Clip duration" in r.stdout
    assert "Clip start_sec/end_sec 时间轴" in r.stdout


def test_finalize_removes_stale_frame_paths_when_continuity_exempts_them(tmp_path):
    root, ep = str(tmp_path), "第1集"
    _write_manifest(root, ep, [
        {"idx": 0, "镜头": "镜头1", "文本": "甲。", "时长": 2.0, "start": 0.0, "end": 2.0, "gap_after": 0.0},
    ])
    sb_p = os.path.join(root, "脚本", ep, "storyboard.json")
    json.dump({
        "clips": [{
            "id": "EP01_CLIP01",
            "duration": 2,
            "voiceover_indices": [1],
            "midframe_png": "出图/第1集/图片/Clip01_mid.png",
            "endframe_png": "出图/第1集/图片/Clip01_end.png",
            "continuity": {
                "need_endframe": False,
                "midframe_exempt_reason": "短镜豁免",
            },
        }],
    }, open(sb_p, "w", encoding="utf-8"), ensure_ascii=False)

    r = subprocess.run(
        [sys.executable, os.path.join(_HERE, "finalize_storyboard.py"), root, ep],
        capture_output=True,
        text=True,
    )

    assert r.returncode == 0, r.stdout + r.stderr
    clip = json.load(open(sb_p, encoding="utf-8"))["clips"][0]
    assert "midframe_png" not in clip
    assert "endframe_png" not in clip
    assert "旧帧路径" in r.stdout


def test_finalize_ignores_and_removes_placeholder_english_srt_for_zh_only(tmp_path):
    root, ep = str(tmp_path), "第1集"
    _write_manifest(root, ep, [
        {"idx": 0, "镜头": "镜头1", "文本": "甲。", "时长": 2.0, "start": 0.0, "end": 2.0, "gap_after": 0.0},
        {"idx": 1, "镜头": "镜头2", "文本": "乙。", "时长": 1.0, "start": 2.0, "end": 3.0, "gap_after": 0.0},
    ])
    en_path = os.path.join(root, "脚本", ep, "字幕_英文.srt")
    open(en_path, "w", encoding="utf-8").write(
        "1\n00:00:00,000 --> 00:00:03,000\n"
        "(TODO: English subtitles for overseas platforms — timed to the storyboard)\n"
    )

    r = subprocess.run(
        [sys.executable, os.path.join(_HERE, "finalize_storyboard.py"), root, ep],
        capture_output=True,
        text=True,
    )

    assert r.returncode == 0, r.stdout + r.stderr
    assert "(仅中文)" in r.stdout
    assert not os.path.exists(en_path)


def test_clean_punct():
    # 治 || 气口残留：。，→。、，，→，、行首逗号去掉（重跑 finalize 自动洗净字幕）
    assert F._clean_punct("走向。，慎重选择。") == "走向。慎重选择。"
    assert F._clean_punct("我，，你") == "我，你"
    assert F._clean_punct("，开头的句子") == "开头的句子"
    assert F._clean_punct("正常，一句话。") == "正常，一句话。"   # 合法标点不动


def test_clean_en():
    assert F._clean_en("Choose carefully .") == "Choose carefully."     # 标点前空格
    assert F._clean_en("shape  the  path") == "shape the path"          # 多空格
    assert F._clean_en("a,, b") == "a, b"                               # 叠逗号
    assert F._clean_en(", leading") == "leading"                       # 行首逗号
    assert F._clean_en("Mr. Smith, hello.") == "Mr. Smith, hello."      # 合法不动
    assert F._clean_en("(opening one eye) ...This kid") == "(opening one eye) ...This kid"  # 省略号前空格不动


def test_native_av_builds_shots_from_storyboard_without_manifest(tmp_path):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "脚本", "第1集"), exist_ok=True)
    open(os.path.join(root, "_设置.md"), "w", encoding="utf-8").write("# _设置\n## 选择\n- 制作模式: 原生音画\n")
    json.dump({"clips": [{"id": "EP01_CLIP01", "duration": 7}, {"id": "EP01_CLIP02", "duration": 5.5}]},
              open(os.path.join(root, "脚本", "第1集", "storyboard.json"), "w", encoding="utf-8"), ensure_ascii=False)
    r = subprocess.run([sys.executable, os.path.join(_HERE, "finalize_storyboard.py"), root, "第1集"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr            # 无配音清单也不崩
    shots = json.load(open(os.path.join(root, "脚本", "第1集", "镜头时长.json"), encoding="utf-8"))
    assert shots == {"EP01_CLIP01": 7.0, "EP01_CLIP02": 5.5}  # 时长来自 storyboard 脚本规划


def test_native_av_finalize_writes_planned_zh_srt_from_storyboard(tmp_path):
    root, ep = str(tmp_path), "第1集"
    os.makedirs(os.path.join(root, "脚本", ep), exist_ok=True)
    open(os.path.join(root, "_设置.md"), "w", encoding="utf-8").write("# _设置\n## 选择\n- 制作模式: 原生音画\n")
    json.dump({
        "clips": [
            {"id": "EP01_CLIP01", "duration": 4, "subtitle_lines": ["毒酒已经送到唇边。", "这不是我的脸。"]},
            {"id": "EP01_CLIP02", "duration": 3, "voiceover_lines": ["我偏要活下去。"]},
        ]
    }, open(os.path.join(root, "脚本", ep, "storyboard.json"), "w", encoding="utf-8"), ensure_ascii=False)

    r = subprocess.run([sys.executable, os.path.join(_HERE, "finalize_storyboard.py"), root, ep],
                       capture_output=True, text=True)

    assert r.returncode == 0, r.stdout + r.stderr
    srt = open(os.path.join(root, "脚本", ep, "字幕_中文.srt"), encoding="utf-8").read()
    assert "00:00:00,000 --> 00:00:02,000" in srt
    assert "毒酒已经送到唇边。" in srt
    assert "00:00:04,000 --> 00:00:07,000" in srt
    assert "我偏要活下去。" in srt
    assert os.path.exists(os.path.join(root, "脚本", ep, "shot_intent.json"))


def test_build_from_storyboard_raises_on_missing_duration():
    # 缺 duration 的 clip 不静默丢成 0 长镜头——直接报错点名 clip（治"无时间预算出视频"）
    import pytest
    with pytest.raises(ValueError) as ei:
        F.build_from_storyboard([
            {"id": "EP01_CLIP01", "duration": 7},
            {"id": "EP01_CLIP02"},  # 缺 duration
        ])
    assert "EP01_CLIP02" in str(ei.value)


def test_native_av_finalize_fails_on_missing_clip_duration(tmp_path):
    # 原生音画定稿：storyboard 某 clip 缺 duration → finalize 退出码 2，点名 clip，不静默产 0 长镜头
    root, ep = str(tmp_path), "第1集"
    os.makedirs(os.path.join(root, "脚本", ep), exist_ok=True)
    open(os.path.join(root, "_设置.md"), "w", encoding="utf-8").write("# _设置\n## 选择\n- 制作模式: 原生音画\n")
    json.dump({"clips": [{"id": "EP01_CLIP01", "duration": 7}, {"id": "EP01_CLIP02"}]},
              open(os.path.join(root, "脚本", ep, "storyboard.json"), "w", encoding="utf-8"), ensure_ascii=False)
    r = subprocess.run([sys.executable, os.path.join(_HERE, "finalize_storyboard.py"), root, ep],
                       capture_output=True, text=True)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "EP01_CLIP02" in r.stdout
    assert not os.path.exists(os.path.join(root, "脚本", ep, "镜头时长.json"))


def test_non_native_still_requires_manifest(tmp_path):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "脚本", "第1集"), exist_ok=True)
    # 本用例显式写入「配音先行」以验证非原生音画仍要求配音清单。
    open(os.path.join(root, "_设置.md"), "w", encoding="utf-8").write("# _设置\n## 选择\n- 制作模式: 配音先行\n")
    r = subprocess.run([sys.executable, os.path.join(_HERE, "finalize_storyboard.py"), root, "第1集"],
                       capture_output=True, text=True)
    assert r.returncode == 2 and "缺 时长清单" in r.stdout      # 非原生音画仍要求配音清单


# ── G6: 投放→生成输入闭环（读端）creative_priors 注入 ─────────────────────────
def _write_priors(root, priors):
    d = os.path.join(root, "生产数据")
    os.makedirs(d, exist_ok=True)
    json.dump(priors, open(os.path.join(d, "creative_priors.json"), "w", encoding="utf-8"),
              ensure_ascii=False)


def test_load_creative_priors_noop_when_missing(tmp_path):
    # 缺文件 → None（向后兼容 no-op）
    assert F.load_creative_priors(str(tmp_path)) is None


def test_load_creative_priors_ignores_wrong_kind_and_empty(tmp_path):
    _write_priors(str(tmp_path), {"kind": "other", "priors": {"opening_variant": {"winner": "x"}}})
    assert F.load_creative_priors(str(tmp_path)) is None
    _write_priors(str(tmp_path), {"kind": "n2d_creative_priors", "priors": {}})
    assert F.load_creative_priors(str(tmp_path)) is None   # 文件在但无胜出维度 → 等同无先验


def test_creative_priors_evidence_shape(tmp_path):
    data = {"kind": "n2d_creative_priors", "generated_at": "2026-06-22T00:00:00+00:00",
            "priors": {"opening_variant": {"winner": "cold_open_first", "paired_lift": 0.18,
                                           "primary_metric": "retention_3s", "n": 2}}}
    sb = {"creative_variants_used": {"opening_variant": {"variant": "cold_open_first"}}}
    ev = F.creative_priors_evidence(data, sb)
    assert ev["source"] == "creative_priors.json"
    assert ev["priors_generated_at"] == "2026-06-22T00:00:00+00:00"
    assert ev["prior_metrics"]["opening_variant"]["winner"] == "cold_open_first"  # 元数据改名
    assert ev["decisions"]["opening_variant"]["status"] == "applied"  # storyboard 采用胜出→真 applied
    hint = F.creative_priors_hint(data, ev)
    assert "开场优先复用" in hint and "cold_open_first" in hint


def test_finalize_emits_priors_evidence_native_av(tmp_path):
    # 原生音画定稿成功路径：有 creative_priors.json → 落 applied_creative_priors.json + 打提示
    root, ep = str(tmp_path), "第1集"
    os.makedirs(os.path.join(root, "脚本", ep), exist_ok=True)
    open(os.path.join(root, "_设置.md"), "w", encoding="utf-8").write(
        "# _设置\n## 选择\n- 制作模式: 原生音画\n")
    json.dump({"clips": [{"id": "EP01_CLIP01", "duration": 7}]},
              open(os.path.join(root, "脚本", ep, "storyboard.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    _write_priors(root, {"kind": "n2d_creative_priors", "generated_at": "2026-06-22T00:00:00+00:00",
                         "priors": {"opening_variant": {"winner": "cold_open_first", "paired_lift": 0.18,
                                                        "primary_metric": "retention_3s", "n": 2}}})
    r = subprocess.run([sys.executable, os.path.join(_HERE, "finalize_storyboard.py"), root, ep],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "投放回灌先验" in r.stdout and "cold_open_first" in r.stdout
    ev_path = os.path.join(root, "脚本", ep, "applied_creative_priors.json")
    assert os.path.exists(ev_path)
    ev = json.load(open(ev_path, encoding="utf-8"))
    assert ev["prior_metrics"]["opening_variant"]["winner"] == "cold_open_first"
    # storyboard 未声明 creative_variants_used → pending（不再无脑 applied·F2 修真闭环）
    assert ev["decisions"]["opening_variant"]["status"] == "pending"
    assert "待决策" in r.stdout


def test_finalize_noop_without_priors_native_av(tmp_path):
    # 缺先验文件 → 不打提示、不落证据（向后兼容）
    root, ep = str(tmp_path), "第1集"
    os.makedirs(os.path.join(root, "脚本", ep), exist_ok=True)
    open(os.path.join(root, "_设置.md"), "w", encoding="utf-8").write(
        "# _设置\n## 选择\n- 制作模式: 原生音画\n")
    json.dump({"clips": [{"id": "EP01_CLIP01", "duration": 7}]},
              open(os.path.join(root, "脚本", ep, "storyboard.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    r = subprocess.run([sys.executable, os.path.join(_HERE, "finalize_storyboard.py"), root, ep],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "投放回灌先验" not in r.stdout
    assert not os.path.exists(os.path.join(root, "脚本", ep, "applied_creative_priors.json"))


# --- F2: creative priors 真验证采纳（非橡皮图章·2026-06-26）---

def _priors(winner="cold_open_first"):
    return {"kind": "n2d_creative_priors", "generated_at": "2026-06-20",
            "priors": {"opening_variant": {"winner": winner, "paired_lift": 0.12,
                                           "primary_metric": "retention_3s", "n": 6}}}


def test_evidence_applied_when_storyboard_adopts_winner():
    sb = {"creative_variants_used": {"opening_variant": {"variant": "cold_open_first"}}}
    ev = F.creative_priors_evidence(_priors(), sb)
    d = ev["decisions"]["opening_variant"]
    assert d["status"] == "applied" and d["verified"] is True
    assert "applied_creative_priors" not in ev  # 元数据已改名 prior_metrics，不再触发 legacy 自动盖章
    assert "prior_metrics" in ev


def test_evidence_rejected_when_other_variant_with_reason():
    sb = {"creative_variants_used": {"opening_variant": {"variant": "in_media_res", "reason": "本集走悬疑冷场更贴题材"}}}
    ev = F.creative_priors_evidence(_priors(), sb)
    d = ev["decisions"]["opening_variant"]
    assert d["status"] == "rejected" and d["rejected_reason"].startswith("本集走悬疑")


def test_evidence_pending_when_other_variant_without_reason():
    sb = {"creative_variants_used": {"opening_variant": {"variant": "in_media_res"}}}
    ev = F.creative_priors_evidence(_priors(), sb)
    assert ev["decisions"]["opening_variant"]["status"] == "pending"


def test_evidence_pending_when_no_declaration_not_rubber_stamped():
    # 核心：未声明 → pending（不再无脑 applied）→ beat_audit --strict 会拦
    ev = F.creative_priors_evidence(_priors(), sb=None)
    d = ev["decisions"]["opening_variant"]
    assert d["status"] == "pending" and d["verified"] is False


def test_adopted_variant_parsing():
    sb = {"creative_variants_used": {"a": {"variant": "x", "reason": "r"}, "b": "y"}}
    assert F._adopted_variant(sb, "a") == ("x", "r")
    assert F._adopted_variant(sb, "b") == ("y", "")
    assert F._adopted_variant(sb, "missing") == (None, "")
    assert F._adopted_variant(None, "a") == (None, "")
