# Image Prompt Compiler 规范

## 1. 两层合同

`n2d-image` 永远区分两种文本：

1. **完整生产合同**：保留导演意图、身份/资产真值、参考计划、检查清单、重抽预算、QC 与追溯字段，供人审、gate 和 runner 解析。
2. **后端编译请求**：只保留本张图会改变像素的目标、主体与槽位、单一冻结动作、构图、场景、光影、情绪、所选风格、参考附件角色、必要守卫、负向元素和真实请求参数。

完整合同不能直接提交；runner 也不能在 compiler 之后追加未入哈希的创作指令。内部路径、registry 名称、路由理由、预算和自检条目不得进入模型文本。

单一实现：`skills/n2d/_lib/image_prompt_compiler.py`。`image_prompt_pack.py` 在每个可执行 Markdown 块末尾嵌入人读预览；Codex 与 Dreamina runner 在执行时用具体 target、实际附件和参数重新编译。

## 2. 任务 profiles

| profile | 用途 | 核心边界 |
|---|---|---|
| `character_catalog` | 角色定妆/角度/表情板 | 中性档案，不继承剧情动作 |
| `scene_asset` | 场景/布局/光位板 | 空间、地标、材质、光位优先 |
| `prop_asset` | 道具/武器/VFX 资产板 | 单体拓扑、件数、尺度和中性背景 |
| `style_anchor` | 风格锚 | 只定义视觉语言，不建立人物身份 |
| `shot_keyframe` | 首帧/剧情关键帧 | 只定格一个可读动作瞬间 |
| `relay_edit` | 中段/尾帧/局部编辑 | `preserve + delta`；源帧几何优先 |
| `multi_subject` | 多主体同框 | 每主体独立附件、身份和画面槽位 |

角色板、场景、道具等 catalog profile 会自动丢弃误带进来的剧情动作；接力 profile 必须有 preserve 合同；手、脚、接地、近景脸和多人槽位只在命中相应风险时注入，不向所有图片堆通用解剖词。

## 3. 后端 profiles

当前 profile 覆盖 Codex、OpenAI、Dreamina、Seedream、Gemini、FLUX、Midjourney、Imagen、Stable Diffusion、Kling 与 generic。每个 profile声明：

- 首选语言与文本长度建议；
- 画幅应进参数还是可进文本；
- 负向策略：正文内自然约束、positive-only、独立 negative 字段或 `--no` 元素列表；
- 允许的请求参数字段。

FLUX 等 positive-only profile 不接收“不要/禁止/不得”式主 Prompt；高风险守卫会改写为正向结果。Imagen/Stable Diffusion 等把负向元素放独立字段；Midjourney 由执行适配层把该字段翻成参数。不要把一套“万能负向词”原样复制给所有后端。

## 4. 冲突与压缩优先级

1. 实际 `request_params.aspect_ratio` 高于 prompt 中遗留的画幅词；compiler 删除冲突画幅。
2. 当前 `storyboard.style_contract` / `_设置.md` 选择高于旧模板风格；不得默认写实国漫、3D、赛璐璐或其它未选择风格。
3. 真实附件及其 owner/role 高于文字里的泛化“参考图 1”。
4. `relay_edit.preserve` 高于动作增量；动作只改变明确 delta。
5. 更完整的同义约束高于短重复句；compiler 记录 `constraint_compression` 和 `compiler_decisions`。
6. 无法确定的冲突不静默猜测：lint/gate 阻断，回完整合同修正。

## 5. Gate 与执行回执

`image_preflight` / `image` gate 对每个剧情分镜编译块执行：

- kind/version/profile/backend/task 元数据完整性；
- 当前选择后端与编译后端一致；
- source contract 文本 SHA-256 未过期；
- compiled request SHA-256、画幅、参考图编号和负向策略合法；
- 提交文本不泄漏内部路径或完整生产合同。

共享角色、场景、道具、法宝和特效 prompt 同样检查对应任务 profile。

每次真实调用写：

```text
生产数据/compiled_image_requests/第N集/<target>.json             # latest
生产数据/compiled_image_requests/第N集/history/<target>_<backend>_<hash>.json
```

immutable history 回执保存实际提交文本、独立负向字段、请求参数、附件清单、附件完整 SHA-256，以及 source/execution/compiled/request params/reference inputs 的 SHA-256。生产事件引用 immutable 回执，避免后一次重抽覆盖前一次证据。

## 6. 真实 QC 指标与 A/B

先注册固定时域实验：

```bash
python3 skills/n2d-image/scripts/image_prompt_metrics.py register <作品根> EXP_image_compact \
  --variant A --variant B --control A --min-samples 30 \
  --hypothesis "B 在不增加身份漂移/手部失败的前提下提升首抽通过率"
```

执行每个已预分配资产时同时设置两个环境变量；缺一个会 fail-closed：

```bash
N2D_IMAGE_PROMPT_EXPERIMENT_ID=EXP_image_compact \
N2D_IMAGE_PROMPT_VARIANT=A \
<正常 n2d-image runner 命令>
```

汇总真实生产事件与最新 `image_qc`：

```bash
python3 skills/n2d-image/scripts/image_prompt_metrics.py report <作品根> --write
```

报告按 compiler version / profile version / profile / backend / model / experiment variant 统计首抽通过率、身份漂移率、手部失败率、重抽率、成本、输入 token 和 prompt 字符数。只有显式注册、每变体达到样本下限、Bonferroni 校正后首抽提升显著，且身份/手部安全指标不退化时，才给 `promote_candidate`；普通版本 cohort 只作观察，不宣称因果，也不自动改 profile。

Golden 回归真值：`skills/n2d/_lib/fixtures/image_prompt_compiler_golden.json`。修改 compiler/profile 时必须显式 bump `PROFILE_VERSION`、审阅所有后端输出后更新 fixture，不能只改哈希让测试变绿。
