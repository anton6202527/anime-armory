# 现场摩擦信号 —— n2d 自我优化闭环

让产线在**跑数据的过程中**把"这个 skill 该改"的瞬间自动记下来，由流程自审（mode②）消费进差距清单。把"检测"植入每个 skill、把"变更"收口到 review + 治理门——检测便宜且遍布，变更有意、过门、可测。

## 三段闭环

```
[生产者] 任意 n2d skill 撞到缺陷/被迫降级/与基准对不上
   └─ log_friction(work_root, skill, what, ...)  ← 一行，纯 stdlib，失败静默
        ↓  追加一条 JSON
[落点] 作品根/生产数据/优化信号.jsonl            ← per-work 生产数据（非自审报告）
        ↓  只读
[消费者] n2d-review 流程自审  self_audit.py --work <作品根>
   └─ 逐 (skill, 种类) 簇并进「差距清单」：loc=该改哪个 skill、severity 透传、proposed=改法
        ↓  人确认
[变更] 改源头 skill → bash tools/run_all_checks.sh 绿 → 落 main
```

为什么不是"边跑边自己改 skill"：可复现性 + 治理门 + 后台 factory 自动 commit 三条铁律都反对生产途中自改（见 `docs/skill-design-principles.md`、CLAUDE.md）。所以**生产只采集，变更走 review + 门**。

## 生产者：在任意 skill 埋一行

模块：`skills/n2d/_lib/n2d_friction.py`（纯 stdlib，零跨模块依赖，可被任意 skill 一行引入）。

```python
# 脚本顶部（_lib 已在 sys.path 时）——防御式导入，采集绝不拖垮生产：
try:
    from n2d_friction import log_friction
except Exception:
    def log_friction(*a, **k): return None

# 撞到该改的瞬间（缺陷 / 不得不绕的 workaround / 与基准对不上 / 意外）：
log_friction(
    ROOT, 'n2d-voice',                      # work_root, 撞问题的 skill 名（=消费端 loc）
    '12/12 句静音占位（CosyVoice 未起服务）',  # what：一句话现象（必填）
    kind='workaround',                       # defect/workaround/mismatch/surprise/suggestion
    stage='配音', episode=EP,                 # 更细定位（「哪段」）
    evidence='合成/第1集/配音/_占位说明.md',   # 证据路径/镜号/链接
    proposed='缺真实后端时早探活并提示安装',    # 建议改法（=消费端 suggestion）
    severity='warn',                         # info/warn/block（透传给 finding sev）
)
```

规则：
- **必填只有三个**：`work_root, skill, what`；其一为空 = 静默 no-op。
- **绝不抛**：任何异常吞掉返回 `None`——采集永远不能拖垮正在跑的生产（C4 降级不加锁）。
- `severity='block'` 的现场信号会让 `self_audit` 退出码=1，可进 CI/批量门当硬闸。
- 已接的真实埋点：`skills/n2d-voice/render_voice.py` 占位降级分支。新埋点照抄上面一行即可，**无需登记**（不是 detector，不进 detector_inventory；加脚本不触发 README F1）。

## 落点

`<作品根>/生产数据/优化信号.jsonl`，每行一条 `{"kind":"n2d_friction_signal",...}`。属 per-work 生产数据，**不是** `skills/` 下的自审报告——保住 mode② "不归档自审报告" 的宪法立场（`_流程自审_*.md` 仍 gitignore）。

## 消费者

```bash
python3 skills/n2d-review/scripts/self_audit.py --work <作品根>          # markdown 差距清单
python3 skills/n2d-review/scripts/self_audit.py --work <作品根> --json   # 机器消费
```

不传 `--work` = 仍是纯仓库级静态自审（现场信号不参与，零行为变化）。`audit(root, work_root)` / `read_friction` / `summarize_friction` 都是纯函数，回归测试见 `scripts/test_self_audit_friction.py` + `skills/n2d/_lib/test_n2d_friction.py`。

## 何时记 vs 不记

- ✅ 记：后端/依赖缺失被迫降级；不得不写的 workaround；产出与导演/基准对不上但当前 skill 没拦住；同一坑反复踩。
- ❌ 不记：纯内容问题（那是 mode① 作品质检）；一次性环境噪音；已知且已在 Q&A/SKILL 记过的设计权衡。
