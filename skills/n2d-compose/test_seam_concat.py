"""从本目录跑：cd skills/n2d-compose && python -m pytest test_seam_concat.py"""
import json

import seam_concat as s


def test_classify_explicit():
    assert s.classify_seam("硬切")[0] == "cut"
    assert s.classify_seam("微溶解")[0] == "dissolve"
    assert s.classify_seam("缺空镜")[0] == "warn"
    assert s.classify_seam("eyeline cut")[0] == "cut"
    assert s.classify_seam("dissolve")[0] == "dissolve"


def test_classify_jump_and_intended_hard():
    assert s.classify_seam("跳变")[0] == "dissolve"            # 跳变默认溶解兜底
    assert s.classify_seam("跳变", ctx="爽点")[0] == "cut"      # 有意冲击点不溶解
    assert s.classify_seam("反转硬切")[0] == "cut"


def test_classify_fallback():
    assert s.classify_seam("", fallback="cut")[0] == "cut"
    assert s.classify_seam("", fallback="微溶解")[0] == "dissolve"
    assert s.classify_seam("", fallback="报警")[0] == "warn"
    # 兜底=溶解但有意冲击点 → 硬切
    assert s.classify_seam("", ctx="反转", fallback="微溶解")[0] == "cut"


def test_build_plan_counts_and_runs():
    trans = ["硬切", "微溶解", "缺空镜", "硬切"]  # 5 clip, 4 seam
    plan = s.build_plan(5, trans, [""] * 4, "cut")
    assert plan["used_storyboard"] is False  # len(trans)=4 != 5 → 不匹配
    # 用匹配的 5 项
    trans5 = ["硬切", "微溶解", "缺空镜", "硬切", "硬切"]
    plan = s.build_plan(5, trans5, [""] * 5, "cut")
    assert plan["used_storyboard"] is True
    assert plan["dissolve_count"] == 1
    assert plan["warn_count"] == 1
    runs = s.group_runs(plan["seams"], 5)
    assert runs == [[0, 1], [2, 3, 4]]  # 在溶解接缝(1→2)切开；warn 接缝(2→3)留在 run 内


def test_no_storyboard_all_cut_single_run():
    plan = s.build_plan(4, [], [], "cut")
    assert plan["dissolve_count"] == 0
    runs = s.group_runs(plan["seams"], 4)
    assert runs == [[0, 1, 2, 3]]  # 单 run → 等价 concat -c copy


def test_xfade_offsets_and_filter():
    assert s.xfade_offsets([5, 4, 3], 0.25) == [4.75, 8.5]
    filt, final = s.build_xfade_filter([5, 4, 3], 0.25)
    assert final == "vout"
    assert "xfade=transition=fade:duration=0.25:offset=4.75" in filt
    assert "offset=8.5" in filt
    # 单段无 xfade
    assert s.build_xfade_filter([5], 0.25) == ("", "0:v")


def test_parse_list_file(tmp_path):
    lst = tmp_path / "list.txt"
    lst.write_text("file '/a/b c0.mp4'\nfile '/a/b c1.mp4'\n", encoding="utf-8")
    assert s.parse_list_file(str(lst)) == ["/a/b c0.mp4", "/a/b c1.mp4"]


def test_plan_only_cli_no_ffmpeg(tmp_path):
    lst = tmp_path / "list.txt"
    lst.write_text("".join(f"file '{tmp_path}/c{i}.mp4'\n" for i in range(3)), encoding="utf-8")
    sb = tmp_path / "storyboard.json"
    sb.write_text(json.dumps({"clips": [
        {"id": "C1", "continuity": {"transition": "硬切"}},
        {"id": "C2", "continuity": {"transition": "微溶解"}},
        {"id": "C3", "continuity": {"transition": "硬切"}},
    ]}, ensure_ascii=False), encoding="utf-8")
    rc = s.main(["--list", str(lst), "--out", str(tmp_path / "concat.mp4"),
                 "--storyboard", str(sb), "--report", str(tmp_path / "rep.md"), "--plan-only"])
    assert rc == 0
    assert (tmp_path / "rep.md").is_file()
