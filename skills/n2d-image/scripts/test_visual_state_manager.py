"""从本目录跑：cd skills/n2d-image/scripts && python -m pytest test_visual_state_manager.py

visual_state_manager 是 n2d-image 的【状态演进】层（受伤/战损/获得法宝随集累积），
与 identity_registry 的【身份锁定】层互补。这里覆盖账本读写/增删去重 + prompt 注入幂等。
"""
import json
import os

from visual_state_manager import (
    apply_updates,
    get_ledger_path,
    init_ledger,
    inject_into_prompts,
)
from n2d_contract import VISUAL_STATE_LEDGER_KIND, product_kind


def _add(char, mod_id, desc="伤", control="prompt_tag", ep="第2集"):
    return {"character_name": char, "action": "add", "modifier": {
        "id": mod_id, "description": desc, "control_type": control,
        "mask_prompt": "x", "added_in": ep, "active": True}}


def test_init_ledger_uses_contract_kind(tmp_path):
    ledger = init_ledger(str(tmp_path))
    assert ledger["kind"] == VISUAL_STATE_LEDGER_KIND   # kind 来自契约单一真值源
    assert os.path.isfile(get_ledger_path(str(tmp_path)))


def test_product_kind_registered_with_boundary():
    spec = product_kind(VISUAL_STATE_LEDGER_KIND)
    assert spec and spec["owner"] == "n2d-image"
    # 边界必须点明与 identity_registry 的分工（定性的核心）
    assert "identity_registry" in spec["boundary"]
    assert "状态" in spec["layer"]


def test_apply_add_then_dedup_update(tmp_path):
    root = str(tmp_path)
    apply_updates(root, {"updates": [_add("沈念", "left_arm_bandage", "左臂绷带")]})
    led = apply_updates(root, {"updates": [_add("沈念", "left_arm_bandage", "左臂带血绷带")]})
    mods = led["characters"]["沈念"]["modifiers"]
    assert len(mods) == 1                          # 同 id 不重复追加
    assert mods[0]["description"] == "左臂带血绷带"   # 而是就地更新


def test_apply_remove(tmp_path):
    root = str(tmp_path)
    apply_updates(root, {"updates": [_add("柳娘子", "clean_dress")]})
    led = apply_updates(root, {"updates": [
        {"character_name": "柳娘子", "action": "remove", "modifier_id": "clean_dress"}]})
    assert led["characters"]["柳娘子"]["modifiers"] == []


def test_inject_is_idempotent(tmp_path):
    root = str(tmp_path)
    apply_updates(root, {"updates": [_add("沈念", "scar", "脸上疤痕")]})
    pf = os.path.join(root, "出图", "第2集", "prompt", "01_分镜出图.md")
    os.makedirs(os.path.dirname(pf), exist_ok=True)
    open(pf, "w", encoding="utf-8").write("## 镜头1\n目标：沈念 站在门口\n正文\n")
    assert inject_into_prompts(root, "2") == 1      # 首次注入
    after_first = open(pf, encoding="utf-8").read()
    assert "视觉状态锁" in after_first
    assert inject_into_prompts(root, "2") == 0      # 再注入不重复
    assert open(pf, encoding="utf-8").read() == after_first
