# 输出格式规范

两个文件内容一致，仅格式不同，均落 `artifacts/<书名>/小说/`。

## `<书名>.txt`（喂给 split_novel.py）
- UTF-8。
- 文件头：provenance 注释块（`#` 开头多行：source_url / fetched / chapters / chars / copyright）。
  `split_novel.py` 的 `strip_frontmatter` 会从首个 `第N章` 起算正文，自动跳过本块。
- 每章：一行 `第N章 标题`（N 为顺序号，**重新编号**，不沿用原站编号），空行，正文段落。
- 章节标题正则与 `n2d-script/scripts/split_novel.py` 的 `CHAPTER_RE` 对齐：
  `^\s*第\s*[0-9零一二三四五六七八九十百千两]+\s*[章回节卷]`。

## `<书名>.docx`（便于人读 / 导入飞书）
- python-docx 生成。
- provenance 块在最前（普通段落）。
- 每章标题 = Heading 1；正文逐段为普通段落。

## provenance 字段
| 字段 | 含义 |
|---|---|
| source_url | 抓取目录页/作品页 URL |
| fetched | 抓取日期（YYYY-MM-DD） |
| chapters | 章节数 |
| chars | 总字数（去换行） |
| copyright | 版权状态判定（公版来源自动；通用兜底记"用户声明有权使用"） |
