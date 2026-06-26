"""candidate_select 纯排序/选片单测。
cd skills/n2d-image/scripts && python -m pytest test_candidate_select.py
"""
import candidate_select as cs


def _c(name, **kw):
    return dict(path=f"/x/{name}.png", candidate=name, **kw)


def test_hard_fail_disqualified_and_sinks():
    cands = [_c("a", face_consistency=0.9, qc_hard_fail=True),
             _c("b", face_consistency=0.6)]
    r = cs.select_best(cands)
    assert r["picked"]["candidate"] == "b"          # 崩脸的 a 即便 face 高也淘汰
    assert r["disqualified"] == 1 and r["survivors"] == 1


def test_all_hard_fail_triggers_reroll():
    cands = [_c("a", qc_hard_fail=True), _c("b", qc_hard_fail=True)]
    r = cs.select_best(cands)
    assert r["picked"] is None and r["reroll_needed"] and "硬伤" in r["reason"]


def test_best_below_identity_floor_triggers_reroll():
    cands = [_c("a", face_consistency=0.40), _c("b", face_consistency=0.38)]
    r = cs.select_best(cands, identity_floor=0.45)
    assert r["picked"]["candidate"] == "a" and r["reroll_needed"]  # 最好的也崩脸


def test_deterministic_rank_by_face_then_quality():
    cands = [_c("a", face_consistency=0.7, sharpness=0.2),
             _c("b", face_consistency=0.8, sharpness=0.1),
             _c("c", face_consistency=0.7, sharpness=0.9)]
    r = cs.select_best(cands)
    assert r["picked"]["candidate"] == "b"          # face 余弦主信号
    assert [x["candidate"] for x in r["ranked"]][0] == "b"


def test_vlm_ranker_is_pairwise_not_absolute():
    # VLM 偏好 c（即便 c 确定性分不是最高）——验证 VLM 当 ranker 用、能覆盖确定性次序
    cands = [_c("a", face_consistency=0.7), _c("b", face_consistency=0.72), _c("c", face_consistency=0.71)]
    def compare(x, y):
        # c 永远赢；其余看 face
        if x["candidate"] == "c":
            return "a"
        if y["candidate"] == "c":
            return "b"
        return "a" if x["face_consistency"] >= y["face_consistency"] else "b"
    r = cs.select_best(cands, vlm_compare=compare)
    assert r["method"] == "vlm_ranker" and r["picked"]["candidate"] == "c"


def test_vlm_tie_falls_back_to_deterministic():
    cands = [_c("a", face_consistency=0.6, composition=0.1), _c("b", face_consistency=0.6, composition=0.9)]
    r = cs.select_best(cands, vlm_compare=lambda x, y: "tie")
    assert r["picked"]["candidate"] == "b"          # 平局→确定性分高者（b 构图分高）


def test_empty_candidates_reroll():
    r = cs.select_best([])
    assert r["picked"] is None and r["reroll_needed"]


def test_champion_is_n_minus_1_comparisons():
    calls = []
    cands = [_c(n, face_consistency=0.6) for n in "abcd"]
    def compare(x, y):
        calls.append((x["candidate"], y["candidate"]))
        return "a"
    cs.select_best(cands, vlm_compare=compare)
    assert len(calls) == 3                           # 单淘汰 = N-1 次
