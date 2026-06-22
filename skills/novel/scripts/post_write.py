#!/usr/bin/env python3
"""post_write.py — novel 管线“写完一章”后的自动化 Hook。

执行以下操作：
1. 校验章节正文与状态增量文件都已落盘。
2. 运行状态账本对账、百科更新、逻辑哨兵、力量体系机检。
3. 全部硬闸通过后，才更新 _进度.md：将该章的“正文初稿”标记为 ✅。

用法：
  python3 post_write.py <作品根> --chapter <章号>
"""
import os
import sys
import argparse
import subprocess
import json
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILLS = os.path.abspath(os.path.join(_HERE, "..", ".."))
_LIB = os.path.abspath(os.path.join(_HERE, "..", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from project_io import find_chapter_file, load_project_settings

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def die(message, code=1):
    print(f"[err] {message}", file=sys.stderr)
    sys.exit(code)

def load_required_delta(path, ch_num):
    if not os.path.exists(path):
        die(f"缺失状态增量文件：{path}。请先填写本章 state_delta，再重跑 post_write。")
    try:
        payload = load_json(path)
    except json.JSONDecodeError as exc:
        die(f"状态增量 JSON 不合法：{path}: {exc}")
    if not isinstance(payload, dict):
        die(f"状态增量必须是 JSON object：{path}")
    if payload.get("chapter") is not None:
        try:
            got = int(payload.get("chapter"))
        except (TypeError, ValueError):
            die(f"状态增量 chapter 必须是数字：{path}")
        if got != ch_num:
            die(f"状态增量章节不匹配：delta chapter={got}, requested={ch_num}")
    return payload

def main():
    p = argparse.ArgumentParser(description="novel 写后自动化 Hook")
    p.add_argument("root")
    p.add_argument("--chapter", required=True, help="刚刚写完的章号")
    args = p.parse_args()

    root = os.path.abspath(args.root)
    ch = args.chapter # e.g. "第01章"
    
    m = re.search(r"(\d+)", ch)
    if not m:
        die(f"无法从章号识别数字: {ch}")
    ch_num = int(m.group(1))
    ch_padded = f"第{ch_num:02d}章"

    settings = load_project_settings(root)

    try:
        chapter_path = find_chapter_file(root, ch_num)
    except FileNotFoundError as exc:
        die(str(exc))

    delta_path = os.path.join(root, "审稿", f"state_delta_{ch_padded}.json")
    load_required_delta(delta_path, ch_num)
    print(f"🔎 已确认章节正文：{chapter_path}")
    print(f"🔎 已确认状态增量：{delta_path}")

    # 1. 读者契约逐章硬闸：防止长篇只推进事件、不推进题旨/承诺/文学质感。
    print(f"🔄 正在运行读者契约自检...")
    rc_script = os.path.join(_HERE, "..", "..", "novel-review", "scripts", "reader_contract_sentry.py")
    subprocess.run([sys.executable, rc_script, root, "--chapter", str(ch_num)], check=True)

    # 2. 状态账本对账 (Audit)
    print(f"🔄 正在运行状态账本对账 (Audit)...")
    reconcile_script = os.path.join(_HERE, "..", "..", "novel-craft", "scripts", "reconcile_ledger.py")
    subprocess.run([sys.executable, reconcile_script, root, "--chapter", str(ch_num), "--audit"], check=True)

    # 3. 增量更新百科
    print(f"🔄 正在提取百科事实...")
    wiki_script = os.path.join(_HERE, "..", "..", "novel-wiki", "scripts", "wiki_builder.py")
    subprocess.run([sys.executable, wiki_script, root, "--chapter", str(ch_num)], check=True)

    # 4. 逻辑哨兵
    print(f"🔄 正在运行逻辑哨兵...")
    sentry_script = os.path.join(_HERE, "..", "..", "novel-wiki", "scripts", "logic_sentry.py")
    subprocess.run([sys.executable, sentry_script, root, "--chapter", str(ch_num)], check=True)

    # 5. 力量体系自检（穿越/系统流/修仙：等级·成长值·战力逐章一致性）
    #     受 `力量体系自检` 选择点控制（关闭→跳过；仅建议→全降建议级）。无 power_system_registry.json
    #     时引擎自身优雅跳过，所以非力量题材项目这里几乎零成本。退档/未知境界=阻断级，写章后第一时间抓住。
    ps_mode = str(settings.get("力量体系自检", "开启") or "开启")
    if "关闭" not in ps_mode:
        print(f"🔄 正在运行力量体系自检（等级/成长值/战力一致性）...")
        ps_script = os.path.join(_HERE, "..", "..", "novel-wiki", "scripts", "power_system.py")
        ps_cmd = [sys.executable, ps_script, root]
        if "仅建议" in ps_mode:
            ps_cmd.append("--advisory")
        subprocess.run(ps_cmd, check=True)

        # 5b. 反派/威胁战力 scaling 自检（反向战力崩坏：威胁缺位/反派突兀膨胀）——advisory（exit 恒 0，不硬挡）。
        #     无 registry / 无反派标注时引擎自身优雅跳过，非力量题材零成本。
        print("🔄 正在运行反派战力 scaling 自检（威胁缺位/反派突兀膨胀）...")
        as_script = os.path.join(_HERE, "..", "..", "novel-wiki", "scripts", "antagonist_scaling.py")
        subprocess.run([sys.executable, as_script, root], check=False)

    # 5c. 时间线/事件顺序校验（年份倒流=建议级；设定/timeline.json 事件乱序=阻断级硬挡）。
    #     无 timeline.json 时只做保守的时间倒流提示（exit 0）；有台账且乱序才非零退出硬挡。
    print("🔄 正在运行时间线/事件顺序校验...")
    tl_script = os.path.join(_HERE, "..", "..", "novel-wiki", "scripts", "timeline_check.py")
    subprocess.run([sys.executable, tl_script, root], check=True)

    # 6. 所有硬闸通过后再更新进度，避免检查失败时留下假阳性。
    print(f"🔄 正在更新进度：{ch_padded} 正文初稿 ✅")
    prog_script = os.path.join(_HERE, "..", "progress.py")
    subprocess.run([sys.executable, prog_script, "set", root, ch_padded, "正文初稿", "✅"], check=True)

    print(f"\n✅ 任务完成！{ch_padded} 已准备好进入 Review 阶段。")
    print(f"  [下一步] 请核对对账 Prompt，保存核对结论 JSON 后合并账本：")
    print(f"  python3 skills/novel-craft/scripts/reconcile_ledger.py \"{root}\" --chapter {ch_num} --merge --verified <结论.json>")

if __name__ == "__main__":
    main()
