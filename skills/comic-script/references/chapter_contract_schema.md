# split_blueprint / chapter contract v2

`脚本/split_blueprint.json` 是全书候选边界与逐话交接合同。格数、页数和字数只能写成软容量意图，不能据此劈断冲突、转折或兑现。

```json
{
  "kind": "comic_split_blueprint",
  "version": 2,
  "status": "confirmed",
  "policy": "剧情闭环优先；budget 只作软容量与产能估算",
  "chapters": [
    {
      "chapter": "第1话",
      "chapter_type": "serial",
      "format_profile": "vertical_serial",
      "source_mode": "adapted",
      "source_spans": [
        {
          "span_id": "SPAN_001",
          "source_path": "源本/story.md",
          "start": "第一章",
          "end": "第二章"
        }
      ],
      "reader_promise": "读者本话会看到主角第一次反击",
      "core_conflict": "主角要救人，但出口被封锁",
      "turning_point": "主角发现封锁者正是旧友",
      "payoff": "用先前埋下的机关撕开出口",
      "ending_mode": "decision",
      "budget": {"unit": "panels", "target": 42, "soft_range": [32, 54]},
      "entry_state": {"CHAR_001": {"injury": "none"}, "PROP_KEY": {"owner": "CHAR_001"}},
      "continuity_delta": [
        {"entity_id": "CHAR_001", "field": "injury", "from": "none", "to": "left_arm_cut", "panel_id": "P032", "reason": "格斗中被刀划伤"},
        {"entity_id": "PROP_KEY", "field": "owner", "from": "CHAR_001", "to": "CHAR_002", "panel_id": "P040", "reason": "旧友抢走钥匙"}
      ],
      "exit_state": {"CHAR_001": {"injury": "left_arm_cut"}, "PROP_KEY": {"owner": "CHAR_002"}},
      "status": "confirmed"
    }
  ]
}
```

## 精确枚举

- `chapter_type`: `serial | one_shot | gag | bridge | epilogue`。
- `format_profile`: `vertical_serial | paged_rtl | paged_ltr | yonkoma | custom`。
- `source_mode`: `adapted | original`。原创话次可令 `source_spans=[]`；改编话次必须至少声明一个 span。
- `ending_mode`: `cliffhanger | reveal | decision | emotional_aftershock | closure_with_new_promise | gag_payoff | complete_closure | transition`。完结短篇和四格不强制 cliffhanger。
- `status`: `draft | review | confirmed | locked`。

## source_spans

- 区间是包含首尾的闭区间，支持阿拉伯数字和中文数字：`第2章`、`第十二回`、`第二十话`、`第三节`。
- `start` 与 `end` 的单位必须一致；跨区间如 `第一回` 到 `第三回` 会消费三回全文。
- 无标题的单文件可写 `{"source_path":"源本/梗概.txt","whole_file":true}`。
- 多话之间有缺口、重叠或倒叙复用时，必须在后一个 span 写非空 `coverage_exception` 说明删改、延后或复用原因；不得静默遗漏。
- `source_semantics.json` 记录每个源文件 SHA、实际命中的源单位和完整 segment coverage。源文件或本话合同 SHA 改变后报告会 stale，必须 `--force` 重建并重审。

## 连载状态

`serial / bridge / epilogue` 必须提供非空 `entry_state / continuity_delta / exit_state`。`entry_state` / `exit_state` 是按稳定 ID 组织的状态 object；`continuity_delta` 是 transition 数组，每项必须有 `entity_id / field / from / to / panel_id / reason`，使伤势、服装、知识、关系、道具持有人/损坏和场景时间变化都能回到可见证据格。`one_shot / gag` 可选。

## budget

只允许 `target` 和 `soft_range`。`hard_min / hard_max` 属非法合同字段。平台投稿快照、周更产能和高潮格序只能产生 WARN；最终边界服从本话完整冲突、转折/兑现和可承接的退出状态。

## v1 迁移

旧 `source_range / ending_hook_candidate / estimated_panels` 仍可被 report-only 工具识别为 legacy，但 `check --strict` 不会放行。迁移时：

1. 把自然语言 `source_range` 拆成真实文件路径与结构化 `source_spans`；
2. 将 `estimated_panels` 移入 `budget.target`，并补软区间；
3. 把结尾意图归一到 `ending_mode`；
4. 补齐 promise/conflict/turn/payoff 和长线三段状态；
5. 每话置 `confirmed` 后，对三件套当前 SHA 重新签收。
