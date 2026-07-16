#!/usr/bin/env python3
"""post_write.py — novel 管线“写完一章”后的自动化 Hook。

执行以下操作：
1. 校验章节正文与状态增量文件都已落盘。
2. 运行状态账本对账、百科更新、逻辑哨兵、力量体系机检。
3. 全部硬闸通过且状态账本合并后，才更新 _进度.md：将该章的“正文初稿”标记为 ✅。

用法：
  python3 post_write.py <作品根> --chapter <章号> --conclusion <审稿/state_verify_第NN章.json>
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
_CRAFT = os.path.abspath(os.path.join(_HERE, "..", "..", "novel-craft", "scripts"))
for _p in (_LIB, _CRAFT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from project_io import find_chapter_file, load_project_settings
try:
    import provenance as _provenance  # 写后闭环留痕：让 artifact_graph 的 stale 检测对章节/账本真正生效（F1）
except Exception:  # pragma: no cover - provenance 缺失不得阻断写后闭环
    _provenance = None

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def die(message, code=1):
    print(f"[err] {message}", file=sys.stderr)
    sys.exit(code)

def run_step(label, cmd, *, check=True):
    """跑一个写后自检子步骤；check=True 时失败给出干净的 blocker 提示而非裸 traceback。

    返回子进程 returncode。硬闸失败（returncode!=0 且 check）走 die()，明确指出是哪一步、
    如何回流，避免 CalledProcessError 直接抛栈把真正的 blocker 淹没。"""
    try:
        proc = subprocess.run(cmd)
    except OSError as exc:  # 脚本缺失/不可执行等
        die(f"写后自检步骤「{label}」无法启动：{exc}")
    if check and proc.returncode != 0:
        die(f"写后自检未通过：「{label}」返回非零（{proc.returncode}）。"
            f"这是硬闸——请按上面的报告修正本章后重跑 post_write；未通过前不会合并账本、不会标 ✅。",
            code=proc.returncode)
    return proc.returncode

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
    p.add_argument("--conclusion", default=None,
                   help="LLM 对账结论 JSON（至少含 chapter/status=ok/notes）；给了就在哨兵通过后自动合并状态账本，"
                        "再标进度 ✅——让「进度✅」与「账本已合并」同生共死，避免后续 review/export 报 STATE-LEDGER-MISSING。"
                        "缺 hash 由脚本按当前正文自动盖章（--stamp-hashes）。")
    p.add_argument("--no-merge", action="store_true",
                   help="只跑哨兵+审计、不合并账本（仅在你确知要稍后手动合并时用）")
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
    run_step("读者契约自检", [sys.executable, rc_script, root, "--chapter", str(ch_num)])

    # 2. 状态账本对账 (Audit)
    print(f"🔄 正在运行状态账本对账 (Audit)...")
    reconcile_script = os.path.join(_HERE, "..", "..", "novel-craft", "scripts", "reconcile_ledger.py")
    run_step("状态账本对账", [sys.executable, reconcile_script, root, "--chapter", str(ch_num), "--audit"])

    # 3. 增量更新百科
    print(f"🔄 正在提取百科事实...")
    wiki_script = os.path.join(_HERE, "..", "..", "novel-wiki", "scripts", "wiki_builder.py")
    run_step("百科事实提取", [sys.executable, wiki_script, root, "--chapter", str(ch_num)])

    # 4. 逻辑哨兵
    print(f"🔄 正在运行逻辑哨兵...")
    sentry_script = os.path.join(_HERE, "..", "..", "novel-wiki", "scripts", "logic_sentry.py")
    run_step("逻辑哨兵", [sys.executable, sentry_script, root, "--chapter", str(ch_num)])

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
        run_step("力量体系自检", ps_cmd)

        # 5b. 反派/威胁战力 scaling 自检（反向战力崩坏：威胁缺位/反派突兀膨胀）——advisory（exit 恒 0，不硬挡）。
        #     无 registry / 无反派标注时引擎自身优雅跳过，非力量题材零成本。
        print("🔄 正在运行反派战力 scaling 自检（威胁缺位/反派突兀膨胀）...")
        as_script = os.path.join(_HERE, "..", "..", "novel-wiki", "scripts", "antagonist_scaling.py")
        subprocess.run([sys.executable, as_script, root], check=False)

    # 5c. 时间线/事件顺序校验（年份倒流=建议级；设定/timeline.json 事件乱序=阻断级硬挡）。
    #     无 timeline.json 时只做保守的时间倒流提示（exit 0）；有台账且乱序才非零退出硬挡。
    print("🔄 正在运行时间线/事件顺序校验...")
    tl_script = os.path.join(_HERE, "..", "..", "novel-wiki", "scripts", "timeline_check.py")
    run_step("时间线/事件顺序校验", [sys.executable, tl_script, root])

    # 6. 状态账本合并：给了对账结论就在标进度前自动合并，让「进度✅」与「账本已合并」同生共死。
    #     这是修掉「audit 完就标✅但忘了 merge → review/export 报 STATE-LEDGER-MISSING」的关键。
    merged = False
    if args.conclusion and not args.no_merge:
        concl = os.path.abspath(args.conclusion)
        if not os.path.exists(concl):
            die(f"找不到对账结论文件：{concl}。请把上面审计 Prompt 的核对结论存成 JSON 再重跑。")
        print(f"🔄 正在按对账结论合并状态账本：{concl}")
        run_step("状态账本合并", [
            sys.executable, reconcile_script, root, "--chapter", str(ch_num),
            "--merge", "--verified", concl, "--stamp-hashes",
        ])
        merged = True

    if not merged:
        print(f"\n✅ {ch_padded} 哨兵已过；但状态账本【尚未合并】，本次不会标记正文初稿 ✅。")
        if args.no_merge:
            print("  [mode] --no-merge：仅做自检/审计，按约定不更新 _进度.md。")
            return
        print(f"  ⚠️ 未合并账本，后续 review/export 会报 STATE-LEDGER-MISSING 阻断。")
        print(f"  [下一步] 把上面审计 Prompt 的核对结论存成 JSON（至少 {{\"chapter\":{ch_num},\"status\":\"ok\",\"notes\":\"...\"}}，hash 可不填），然后重跑：")
        print(f"    python3 skills/novel/scripts/post_write.py \"{root}\" --chapter {ch} --conclusion <结论.json>")
        sys.exit(2)

    # 7. 所有硬闸通过且账本合并后再更新进度，避免检查失败或未合并账本时留下假阳性。
    print(f"🔄 正在更新进度：{ch_padded} 正文初稿 ✅")
    prog_script = os.path.join(_HERE, "..", "progress.py")
    run_step("更新进度", [sys.executable, prog_script, "set", root, ch_padded, "正文初稿", "✅"])

    # 8. 写后闭环留痕（F1）：给章节正文 + state_ledger + state_delta/verify 记一条 provenance 事件。
    #    此前 post_write 全程无 provenance，artifact_graph 的 stale 检测对这些最高价值产物永久 no-op；
    #    现在写后即留痕，dashboard 的 stale 面板与 lineage 才对逐章生产真正生效。留痕失败绝不阻断已完成的写后闭环。
    if _provenance is not None:
        try:
            ledger_path = os.path.join(root, "审稿", "state_ledger.json")
            verify_path = os.path.abspath(args.conclusion) if args.conclusion else None
            outputs = [p for p in (chapter_path, ledger_path) if p and os.path.exists(p)]
            inputs = [p for p in (delta_path, verify_path) if p and os.path.exists(p)]
            _provenance.append_event(
                root,
                event_type="chapter_post_write",
                tool="novel/scripts/post_write.py",
                inputs=inputs,
                outputs=outputs,
                metadata={"chapter": ch_num, "merged": True},
            )
        except Exception as exc:  # pragma: no cover - 留痕失败不影响写后闭环结果
            print(f"  [warn] provenance 留痕失败（不影响本章写后闭环）：{exc}", file=sys.stderr)

    print(f"\n✅ 任务完成！{ch_padded} 状态账本已合并，已准备好进入 Review 阶段。")

if __name__ == "__main__":
    main()
