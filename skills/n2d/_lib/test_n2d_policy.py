"""n2d_policy 策略激活判定测试。

历史 bug（2026-07 标准审计发现）：`identity_failure_escalation` 只查
`identity_escalation` 键 / `identity_failure_escalation` flag，而 router 升锁实际写的
risk_flag 是 `identity_escalated`——最高优先级策略对真实升锁 route 永远 inactive。
本测试钉死"router 真实产出的 flag 能激活策略"。

运行：cd skills/n2d/_lib && python -m pytest test_n2d_policy.py
"""
from n2d_policy import route_policy_resolution, _policy_active


def test_identity_escalated_flag_activates_escalation_policy():
    route = {"clip_id": "Clip_03", "risk_flags": ["identity_escalated"], "locked_backend": "kling"}
    assert _policy_active(route, {}, "identity_failure_escalation") is True
    res = route_policy_resolution(route)
    active = [d["policy"] for d in res["decisions"] if d["active"]]
    assert "identity_failure_escalation" in active


def test_escalation_policy_inactive_without_flags():
    route = {"clip_id": "Clip_01", "risk_flags": ["mouth_visible"]}
    assert _policy_active(route, {}, "identity_failure_escalation") is False


def test_legacy_keys_still_activate():
    assert _policy_active({"identity_escalation": True}, {}, "identity_failure_escalation") is True
    assert _policy_active({"risk_flags": ["identity_failure_escalation"]}, {}, "identity_failure_escalation") is True
