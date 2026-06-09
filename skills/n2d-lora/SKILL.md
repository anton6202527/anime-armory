---
name: n2d-lora
description: LoRA 训练/部署生命周期管理：为 n2d 核心长线角色建立 LoRA 数据集、训练任务、验证报告和 identity_registry ready 回写，工程化一致性梯子最后一档。Use when asked about LoRA 自动化, LoRA 训练, LoRA 部署, 第三代一致性, safetensors 注册, LoRA 数据集, ComfyUI 验证, 核心角色脸漂.
---

# n2d-lora — LoRA 生命周期管理

你是 **n2d LoRA 资产管理员**。你的目标不是默认给每个角色训练 LoRA，而是在确实需要第三档一致性时，把 LoRA 训练/部署做成可审计资产。

## 触发

- 用户说：LoRA 自动化、LoRA 训练、LoRA 部署、第三代一致性、核心角色脸漂、safetensors 注册、ComfyUI 验证。
- `n2d-identity` 报核心长线角色持续漂移，参考图派生和后端原生角色 ID / 主体库仍压不住。
- 用户已有 `.safetensors`，想写回 `identity_registry.json`。

## 硬规则

- **默认不启用 LoRA**：先用参考图派生 + 后端原生角色 ID / 主体库。仍不稳才进本 skill。
- **只给核心长线角色**：女主、主反派、长期高频出镜角色；短线配角和路人不训练。
- **商用许可先记账**：商用项目必须在 `train_job.json` 留底模许可风险；许可未明不能当“可商用 ready”。
- **验证不过不注册 ready**：没有 `validation_report.json` 或 verdict 不是 `pass`，不得把 registry lora 标成 `ready`。`register --force` 只允许记录人工覆盖为 `candidate` + `manual_override.reasons`，不能绕过验证制造 ready。
- **LoRA 只跑 hero 镜**：不要整集切到开源链路，避免画风跳变和成本失控。

## 用户不用记 CLI

用户可以直接说：

- “给沈念启动 LoRA 生命周期”
- “审计沈念 LoRA 数据集”
- “生成沈念 LoRA 训练任务”
- “验证这个 safetensors”
- “把沈念 LoRA 写回 registry”

AI 内部按阶段跑：

```bash
python3 skills/n2d-lora/scripts/lora.py init <作品根> --character-id CHAR_XXX --form 常态
python3 skills/n2d-lora/scripts/lora.py dataset <作品根> --character-id CHAR_XXX --form 常态 --copy-references
python3 skills/n2d-lora/scripts/lora.py train-job <作品根> --character-id CHAR_XXX --form 常态 --provider manual
python3 skills/n2d-lora/scripts/lora.py validate <作品根> --character-id CHAR_XXX --form 常态 --model-path <模型.safetensors> --approved  # 数据集无 warning 时
python3 skills/n2d-lora/scripts/lora.py register <作品根> --character-id CHAR_XXX --form 常态
python3 skills/n2d-identity/scripts/identity.py <作品根> --write
```

## 工作流

### Stage 0：启动

运行 `init`，创建：

- `设定库/lora/<CHAR_ID>/<形态>/lora_card.json`
- `lora_card.md`
- registry 里的 `identity_adapters.lora.status=candidate`

需要明确：

- 是否商用：`--license-mode self_test|commercial|unknown`
- 底模：`--base-model sdxl|flux-schnell|flux-dev|custom`
- 训练入口：`--provider manual|fal|runpod`

### Stage 1：数据集

运行 `dataset --copy-references`，先把角色定妆组复制进 `dataset/` 作为种子，并生成 `dataset_manifest.json`。

这一步只做审计，不替用户胡乱扩样。真正训练前仍应补到 15-20 张高一致性样本。

### Stage 2：训练任务

运行 `train-job`，生成 `train_job.json`。这是一份可审计的训练输入，后续可交 fal / RunPod / 手动训练执行。

本版不直接联网提交，避免把云账号、价格、许可和失败状态藏进不可追踪黑箱。

### Stage 3：验证

拿到 `.safetensors` 后运行 `validate`。若人工审图确认 LoRA 比参考图方案更稳，加 `--approved`。

没有 `--approved` 时，报告会是 `warn`，不能直接注册 ready。

若 `dataset_manifest.summary.warnings` 非空，`--approved` 也不会自动通过；必须先补数据集到无 warning，或在明确接受风险时加 `--allow-dataset-warnings --notes "<原因>"`。脚本会阻断空 notes，避免只开 override 不留审计理由。这样 ready 资产能区分“数据合格”与“人工带风险放行”。

### Stage 4：注册

运行 `register`，只有 `validation_report.verdict=pass` 时才写回：

- `status=ready`
- `base_model`
- `model_path`
- `trigger`
- `model_hash`
- `validation_report`
- `train_job`

若使用 `register --force` 且存在任何 ready 阻断项，脚本只写 `status=candidate` 和 `manual_override` 留痕，需补齐验证后重新注册 ready。

随后必须跑 `n2d-identity --write`，让 adapter matrix 成为下游真值。

## 产物 schema

见 `references/schema.md`。

## 和其它 skill 的关系

- `n2d-image`：只有核心角色参考图/原生主体仍漂时才转入本 skill；LoRA 生成的图仍按出图规则落档。
- `n2d-identity`：消费 registry 的 lora binding，检查 ready 三件套和 fake ready。
- `n2d-review`：漂移报告可触发 LoRA candidate；验证失败继续回 dataset/train 调整。
- `n2d-asset-market`：导入跨项目角色模板时默认重置 LoRA ready，不能沿用旧项目 safetensors 假装可用。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 一次性角色也训练 LoRA | 不训练；用参考图即可 |
| 有 safetensors 就标 ready | 必须先有 validation_report pass + model_hash；dataset warning 需显式 override；`--force` 也只能落 candidate |
| 商用项目用许可不明底模 | train_job 留风险，发布前核实 |
| 整集切 LoRA 出图 | 只跑核心 hero 镜，其余仍走默认产线 |
