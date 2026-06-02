# 输出格式 + 中间产物结构

## 作品根目录

```
写小说/<原作名>-<配角名>外传/
├── _meta.json
├── _进度.md
├── 原作.txt                # 原作的纯文本副本（docx → txt 抽出，便于脚本/grep 扫描）
├── 设定/
│   ├── 角色卡.md
│   ├── 世界观.md
│   ├── 锚点表.json
│   └── 章纲.md
├── 章节/
│   └── 第NN章.md           # 一章一个 markdown，文件名零填充两位
└── 导出/
    ├── <书名>.txt
    ├── <书名>.docx
    ├── 大纲.md
    └── n2d-script/         # 可选，仅 --formats 含 n2d 时
        └── 小说/<书名>.docx
```

## `_meta.json`

```json
{
  "source_novel": "<原作绝对路径>",
  "source_title": "<原作名>",
  "spinoff_character": "<配角名>",
  "mode": "parallel|sequel|branch",
  "branch_point": "第N章 / null",
  "scale": "short|medium|long",
  "target_chapters": 30,
  "target_words_per_chapter": [5000, 8000],
  "person": "first|third-limited",
  "rights_status": "public-domain|user-owned|user-declared",
  "rights_declared_at": "YYYY-MM-DD / null",
  "outputs": ["txt", "docx", "outline", "n2d"],
  "title": "<第 3 步选定的书名 / null>",
  "title_chosen_at": "YYYY-MM-DD / null",
  "target_platform": "起点|晋江|抖音漫剧|番茄|红果|历史向|跨平台",
  "demo_chapters": 3,
  "demo_passed_at": "YYYY-MM-DD / null",
  "created_at": "YYYY-MM-DD"
}
```

`title` 在第 1 步 init 时是 null；第 3 步用户选定后由 Claude 写回。`export.py --title` 缺省读这个字段。

`demo_passed_at` 在第 5 步 Demo 通过后由 Claude 写回。用作 audit 痕迹和"是否允许进第 6 步"的硬开关。

## `_进度.md`

```markdown
# 进度

## 准备阶段
- [x] 项目骨架
- [x] 锚点表粗筛
- [ ] 锚点表精筛
- [ ] 角色卡
- [ ] 世界观卡
- [ ] 章纲（用户已确认）

## 写作阶段
| 章 | 标题 | 锚点 | 字数 | 状态 |
|---|---|---|---|---|
| 01 | ... | - | - | [ ] |
| 02 | ... | A01 | - | [ ] |
| ... | ... | ... | ... | ... |

## 回扫阶段
- [ ] 轻量扫描（第 1-5 章）
- [ ] 轻量扫描（第 6-10 章）
- ...
- [ ] 全量一致性扫描
- [ ] 锚点对齐验证

## 导出
- [ ] txt
- [ ] docx
- [ ] 大纲 md
- [ ] n2d-script 结构（可选）
```

## `章节/第NN章.md`

```markdown
# 第 N 章 《<标题>》

<!-- meta: anchors=[A01,A02] words=6231 written_at=YYYY-MM-DD -->

正文第一段…

正文第二段…
```

文件名 `第01章.md` ... `第99章.md`，零填充两位便于排序。

注释行 `<!-- meta: ... -->` 由 export.py 使用，渲染时丢弃。

## 导出 `<书名>.txt`

UTF-8。文件头 provenance 注释块（`#` 开头多行），与 novel-fetch 同款风格：

```
# spinoff_of: <原作名>
# spinoff_character: <配角名>
# mode: parallel|sequel|branch
# chapters: 32
# chars: 198420
# rights_status: public-domain|user-owned|user-declared
# generated: YYYY-MM-DD
# tool: novel-spinoff
```

然后空行，每章一行 `第N章 <标题>`，空行，正文段落。

## 导出 `<书名>.docx`

python-docx 生成。provenance 块在最前（普通段落）。每章标题 = Heading 1，正文逐段为普通段落。

## 导出 `大纲.md`

清版章纲，去掉中间产物的内部注释，留：
- 总体弧线
- 三幕分布
- 逐章 outline（一行一条）

给读者 / 给后续制作人员看的。

## 导出 `n2d-script/`

只铺一个最小结构：
```
n2d-script/
└── 小说/
    └── <书名>.docx        # 直接是上面的 docx 复制一份，命名遵循 n2d-script 约定
```

之后用户在该目录跑 n2d-script：
```bash
python3 .claude/skills/n2d-script/scripts/split_novel.py "写小说/<原作名>-<配角名>外传/导出/n2d-script/小说/<书名>.docx"
```

本 skill **不**自动启动 n2d-script——是不是要进入漫剧流水线由用户决定。
