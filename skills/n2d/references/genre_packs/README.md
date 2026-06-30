# n2d Genre Packs

Genre pack 是题材层契约，不是核心状态机。核心 n2d 只读取这些 JSON 来补充：

- 典型高风险场景
- 分镜/视频动作契约字段
- 出图/出视频 QC 重点
- 风格绑定建议与降级方案

新增题材时复制一个 pack，保持 `kind=n2d_genre_pack`、`version=1`，再跑：

```bash
python3 skills/n2d/scripts/genre_packs.py validate --all
```

