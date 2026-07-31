# novel-spinoff 输出结构

`novel-spinoff` 只产小说项目文件，不生成外部生产线交接目录。

```text
创作区/写小说/<原作名>-<配角名>外传/
├── _meta.json
├── _设置.md
├── _进度.md
├── 原作.txt
├── 设定/
│   ├── 角色卡.md
│   ├── 世界观.md
│   ├── 锚点表.json
│   ├── 书名候选.md
│   └── 章纲.md
├── 章节/
│   └── 第NN章.md
└── 导出/
    ├── <书名>.txt
    ├── <书名>.docx
    └── 大纲.md
```

`_meta.json.outputs` 只能包含 `txt`、`docx`、`outline`。导出统一调用：

```bash
python3 skills/novel/novel-craft/scripts/export.py "<作品根>" --formats txt,docx,outline
```
