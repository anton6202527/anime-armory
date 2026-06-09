#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Visual State Manager for n2d-image pipeline.

Converts narrative text state changes (e.g., injuries, damaged clothing, new items)
into persistent visual control units (e.g., Inpainting Masks, extra prompt tags)
that are automatically injected into image prompts for subsequent episodes.
"""
import argparse
import json
import os
import re
import sys
from datetime import date

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "common"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import VISUAL_STATE_LEDGER_KIND, shared_asset_path  # noqa: E402  产物 kind 单一真值源


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def get_ledger_path(root):
    return shared_asset_path(root, "visual_state_ledger.json")


def init_ledger(root):
    path = get_ledger_path(root)
    if os.path.exists(path):
        return load_json(path)
    
    ledger = {
        "schema_version": 1,
        "kind": VISUAL_STATE_LEDGER_KIND,
        "updated_at": date.today().isoformat(),
        "characters": {},
        "global_environment": []
    }
    write_json(path, ledger)
    return ledger


def parse_novel_ledger(root):
    """Attempt to read the novel pipeline's state_ledger.json and extract visual cues."""
    # Assuming novel path might be parallel or passed, but for now we look in a standard location
    # Or we can just prompt the LLM to do the extraction.
    novel_ledger_path = os.path.join(root, "小说", "审稿", "state_ledger.json")
    if not os.path.exists(novel_ledger_path):
        # Fallback to local prompt-based injection
        return None
    return load_json(novel_ledger_path)


def generate_audit_prompt(ledger, novel_ledger):
    novel_summary = "无关联的小说账本"
    if novel_ledger:
        novel_summary = json.dumps(novel_ledger.get("characters", {}), ensure_ascii=False, indent=2)[:1500]

    return f"""# 视觉状态账本（Visual State Ledger）同步任务

请根据最新的剧情状态（如文字版账本中的受伤、获得法宝、衣服破损等），更新角色的【视觉状态锁】。

## 当前文字版剧情状态参考
```json
{novel_summary}
```

## 当前视觉状态账本
```json
{json.dumps(ledger.get('characters', {}), ensure_ascii=False, indent=2)}
```

## 任务要求
文字描述的“左臂受伤”如果只写在 Prompt 里，AI 每次画的位置都会变。因此，我们需要将其转化为【视觉控制单元】。
请分析剧情状态，输出需要新增或失效的视觉修饰符（Modifiers）。

支持的 `control_type`：
1. `prompt_tag` (普通的提示词追加，如 "dirt on face")
2. `inpainting_mask` (局部重绘遮罩，如 "blood-stained bandage on left arm"，适合精确定位伤口/破损)
3. `lora` (挂载特定的物品或战损版 LoRA)

输出 JSON 格式：
{{
  "updates": [
    {{
      "character_name": "沈念",
      "action": "add",
      "modifier": {{
        "id": "left_arm_bandage",
        "description": "左臂缠着带血的绷带",
        "control_type": "inpainting_mask",
        "mask_prompt": "blood-stained bandage on left arm",
        "added_in": "第2集",
        "active": true
      }}
    }},
    {{
      "character_name": "柳娘子",
      "action": "remove",
      "modifier_id": "clean_dress"
    }}
  ]
}}
"""


def apply_updates(root, updates):
    ledger = init_ledger(root)
    
    for update in updates.get("updates", []):
        char_name = update.get("character_name")
        action = update.get("action")
        
        if char_name not in ledger["characters"]:
            ledger["characters"][char_name] = {"modifiers": []}
            
        if action == "add":
            modifier = update.get("modifier")
            # Avoid duplicates
            existing = next((m for m in ledger["characters"][char_name]["modifiers"] if m["id"] == modifier["id"]), None)
            if existing:
                existing.update(modifier)
            else:
                ledger["characters"][char_name]["modifiers"].append(modifier)
        elif action == "remove":
            mod_id = update.get("modifier_id")
            ledger["characters"][char_name]["modifiers"] = [
                m for m in ledger["characters"][char_name]["modifiers"] if m["id"] != mod_id
            ]
            
    ledger["updated_at"] = date.today().isoformat()
    write_json(get_ledger_path(root), ledger)
    return ledger


def inject_into_prompts(root, episode):
    ledger = load_json(get_ledger_path(root), {})
    if not ledger.get("characters"):
        return 0
        
    prompt_file = os.path.join(root, "出图", f"第{episode}集", "prompt", "01_分镜出图.md")
    if not os.path.exists(prompt_file):
        print(f"[err] 找不到出图 prompt 文件：{prompt_file}", file=sys.stderr)
        return 0
        
    content = open(prompt_file, encoding="utf-8").read()
    updated = False
    
    for char_name, data in ledger["characters"].items():
        active_mods = [m for m in data.get("modifiers", []) if m.get("active")]
        if not active_mods:
            continue
            
        # Compile the visual injection text
        injection_lines = [f"\n> 👁️ **视觉状态锁 ({char_name})**:"]
        for mod in active_mods:
            if mod["control_type"] == "inpainting_mask":
                injection_lines.append(f"> - 局部重绘 (Inpainting): {mod['description']} [Mask Prompt: `{mod.get('mask_prompt', '')}`]")
            elif mod["control_type"] == "prompt_tag":
                injection_lines.append(f"> - 提示词追加: {mod['description']} [Tag: `{mod.get('mask_prompt', '')}`]")
            elif mod["control_type"] == "lora":
                injection_lines.append(f"> - LoRA 挂载: {mod['description']} [Trigger: `{mod.get('mask_prompt', '')}`]")
                
        injection_text = "\n".join(injection_lines) + "\n"
        
        # Simple injection: find where the character is mentioned in the prompt and append the state lock if not already there.
        # This is a naive regex matching the character name in a heading or objective line.
        pattern = re.compile(rf"(目标：.*{re.escape(char_name)}.*?\n)", re.IGNORECASE)
        
        def replacer(match):
            nonlocal updated
            # If already injected, skip
            if "👁️ **视觉状态锁" in content[match.end():match.end()+200]:
                return match.group(0)
            updated = True
            return match.group(0) + injection_text

        content = pattern.sub(replacer, content)
        
    if updated:
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[ok] 已将视觉状态锁注入到 {prompt_file}")
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser(description="视觉状态账本管理器：将文字状态转化为图像生成的持续控制单元")
    ap.add_argument("project_root")
    ap.add_argument("--audit", action="store_true", help="生成与剧情对账的 Prompt")
    ap.add_argument("--apply-mock", help="应用包含 visual modifiers 的 JSON 文件")
    ap.add_argument("--inject", help="指定集号（如：1），将账本状态注入该集的出图 prompt 中")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)

    ledger = init_ledger(root)

    if args.audit:
        novel_ledger = parse_novel_ledger(root)
        prompt = generate_audit_prompt(ledger, novel_ledger)
        print("--- LLM VISUAL STATE SYNC PROMPT ---")
        print(prompt)
        print("--- END PROMPT ---")
        print("\n[info] 请根据上述 prompt 获取 JSON，并用 --apply-mock 注入。")
        
    elif args.apply_mock:
        updates = load_json(args.apply_mock)
        if not updates:
            print(f"[err] 无法读取 {args.apply_mock}", file=sys.stderr)
            sys.exit(2)
        apply_updates(root, updates)
        print(f"[ok] 视觉状态账本已更新 -> {get_ledger_path(root)}")
        
    elif args.inject:
        num_str = re.search(r"\d+", args.inject)
        if not num_str:
            print("[err] 集号格式错误", file=sys.stderr)
            sys.exit(2)
        episode = num_str.group(0)
        res = inject_into_prompts(root, episode)
        if res == 0:
            print("[info] 无需注入或无可用的视觉状态。")


if __name__ == "__main__":
    main()
