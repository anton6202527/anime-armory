from pathlib import Path
import importlib.util
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# 按文件路径 spec-load 并登记为唯一名，避免全套 pytest 里同名模块碰撞。
# 全文件用这个 supervisor 引用。
_spec = importlib.util.spec_from_file_location("n2d_supervisor_under_test", SCRIPT_DIR / "supervisor.py")
supervisor = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(supervisor)


def _progress(root: Path) -> None:
    (root / "_设置.md").write_text("- 制作模式: 原生音画\n- 基础视觉风格: 写实电影感\n", encoding="utf-8")
    (root / "_进度.md").write_text(
        "\n".join([
            "| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 | 验收 |",
            "|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
            "| 第1集 | 800 | ✅ | ✅ | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |",
        ]),
        encoding="utf-8",
    )


def test_dispatch_for_agent_generation_uses_script_specialist():
    next_action = {
        "frontier": {"ep": "第1集", "stage_key": "script_stage2"},
        "stop_reason": "needs_agent_gen",
        "action_card": {},
    }
    dispatch = supervisor.dispatch_for(next_action)
    assert dispatch["should_call_specialist"] is True
    assert dispatch["specialist"]["name"] == "n2d-script-agent"
    assert "execute paid generation" in dispatch["forbidden_operations"]


def test_build_plan_wraps_run_next(tmp_path: Path):
    _progress(tmp_path)
    plan = supervisor.build_plan(str(tmp_path), "第1集")
    assert plan["kind"] == "n2d_supervisor_plan"
    assert plan["summary"]["stage_key"] == "script_stage2"
    assert plan["dispatch"]["specialist"]["name"] == "n2d-script-agent"
    outputs = supervisor.write_plan(plan)
    assert Path(outputs["json"]).is_file()


def test_runtime_guardrails_five_failure_modes():
    d = {"forbidden_operations": ["execute paid generation"], "human_gate": {"required": False}}
    g = supervisor.runtime_guardrails(d, round_index=0, max_rounds=6)
    # 五类失效模式护栏字段齐
    for k in ("max_dispatch_rounds", "loop_budget_exhausted", "specialist_timeout_seconds",
              "outputs_require_gate_recheck", "carried_constraints", "constraints_fingerprint", "tool_use_policy"):
        assert k in g
    assert g["loop_budget_exhausted"] is False and g["outputs_require_gate_recheck"] is True
    # 无界循环：到顶 exhausted
    assert supervisor.runtime_guardrails(d, round_index=6, max_rounds=6)["loop_budget_exhausted"] is True
    # 上下文丢约束：约束变 → 指纹变（消费端可察觉）
    d2 = {"forbidden_operations": ["execute paid generation", "override gate"], "human_gate": {"required": False}}
    assert supervisor.runtime_guardrails(d2)["constraints_fingerprint"] != g["constraints_fingerprint"]


def test_build_plan_loop_ceiling_blocks_dispatch(tmp_path, monkeypatch):
    # 伪造 run.next_action 返回一个会派 specialist 的前沿，验证到顶后强制停派 + 升级。
    fake = {"frontier": {"stage_key": "image_prompt", "ep": "第1集"}, "stop_reason": "needs_agent_gen",
            "action_card": {}, "action_contract": {}}
    monkeypatch.setattr(supervisor, "_load_run_module",
                        lambda: type("M", (), {"next_action": staticmethod(lambda *a, **k: fake)}))
    ok = supervisor.build_plan(str(tmp_path), "第1集", round_index=0, max_rounds=6)
    assert ok["summary"]["should_call_specialist"] is True
    exhausted = supervisor.build_plan(str(tmp_path), "第1集", round_index=6, max_rounds=6)
    assert exhausted["summary"]["should_call_specialist"] is False
    assert "loop_escalation" in exhausted["dispatch"]


def _patch_agent_frontier(monkeypatch):
    fake = {"frontier": {"stage_key": "image_prompt", "ep": "第1集"}, "stop_reason": "needs_agent_gen",
            "action_card": {}, "action_contract": {}}
    monkeypatch.setattr(supervisor, "_load_run_module",
                        lambda: type("M", (), {"next_action": staticmethod(lambda *a, **k: fake)}))


def test_self_managed_rounds_climb_to_exhaustion_even_if_caller_lies(tmp_path, monkeypatch):
    # 调用方每轮都传 round_index=0（撒谎绕过预算）；持久计数仍单调爬升，到顶强制停派。
    _patch_agent_frontier(monkeypatch)
    results = [supervisor.build_plan(str(tmp_path), "第1集", round_index=0, max_rounds=3,
                                     track_rounds=True) for _ in range(4)]
    assert results[0]["summary"]["should_call_specialist"] is True
    assert results[0]["summary"]["round_index"] == 0
    # 第 4 次：持久轮数已达 3 → 耗尽、停派、升级
    assert results[-1]["summary"]["round_index"] >= 3
    assert results[-1]["summary"]["should_call_specialist"] is False
    assert "loop_escalation" in results[-1]["dispatch"]
    assert supervisor.round_state_path(str(tmp_path)).is_file()


def test_no_track_rounds_does_not_persist(tmp_path, monkeypatch):
    _patch_agent_frontier(monkeypatch)
    for _ in range(5):
        plan = supervisor.build_plan(str(tmp_path), "第1集", round_index=0, max_rounds=3, track_rounds=False)
    assert plan["summary"]["should_call_specialist"] is True  # 不累加 → 不会耗尽
    assert not supervisor.round_state_path(str(tmp_path)).is_file()


def test_constraints_fingerprint_echo_drift_blocks_dispatch(tmp_path, monkeypatch):
    _patch_agent_frontier(monkeypatch)
    base = supervisor.build_plan(str(tmp_path), "第1集", track_rounds=False)
    fp = base["dispatch"]["runtime_guardrails"]["constraints_fingerprint"]
    # 回带正确指纹 → 不漂移、可派发
    ok = supervisor.build_plan(str(tmp_path), "第1集", track_rounds=False, echo_fingerprint=fp)
    assert ok["summary"]["constraints_drift"] is False
    assert ok["summary"]["should_call_specialist"] is True
    # 回带错误指纹 → 判定上下文丢约束、停派
    drift = supervisor.build_plan(str(tmp_path), "第1集", track_rounds=False, echo_fingerprint="deadbeef")
    assert drift["summary"]["constraints_drift"] is True
    assert drift["summary"]["should_call_specialist"] is False
    assert "constraints_drift" in drift["dispatch"]
