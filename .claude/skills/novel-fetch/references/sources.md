# 取书来源清单

## 公版 / 开放授权来源（优先）

| 来源 | 适配器 | 适用 | URL 形态 |
|---|---|---|---|
| Project Gutenberg | `gutenberg`（gutendex API） | 英文公版经典 | `https://www.gutenberg.org/ebooks/<id>` |
| 中文维基文库 Wikisource | `wikisource`（MediaWiki action=parse） | 中文公版（四大名著、鲁迅等已过版权期作品） | `https://zh.wikisource.org/wiki/<篇名>` |
| 其它公开站 | `generic`（trafilatura→readability→bs4） | 用户声明有权使用的任意目录页 | 任意章节目录页 URL |

### Gutenberg
- 经 `https://gutendex.com/books/<id>` 取元数据 → 选 `text/plain` 链接下载 → 按 `Chapter N` 切章。

### Wikisource（中文维基文库）
- v1 支持**单页作品**（一个 `/wiki/<篇名>` 页面 = 一章）。多卷作品请对每卷分页 URL 各跑一次，或用 `generic`。
- 经 `…/w/api.php?action=parse&prop=text&page=<篇名>` 取渲染 HTML → 正文提取。

## 付费墙 / 反爬黑名单（直接拒抓）

起点 qidian.com、番茄 fanqienovel.com、晋江 jjwxc.net、纵横 zongheng.com、17K、红袖 hongxiu.com、阅文 yuewen.com、刺猬猫 ciweimao.com、飞卢 faloo.com、小说阅读网 readnovel.com 等。

这些站受版权保护且有反爬/付费墙——本工具不抓、不规避。

## 通用兜底注意
- 非公版 URL 需 `--i-have-rights` 声明授权。
- 成功率因站结构而异；脚本逐章报告状态，失败章节 body 为空，可手动补。
- 部分系统上 trafilatura 还需额外安装 `lxml_html_clean` 包——若 `pip install trafilatura` 后仍报 `lxml.html.clean` ImportError，执行 `pip install lxml_html_clean` 即可。
- 已知限制：通用兜底逐章顺序抓取、章节间无延时；对章节很多的作品，密集请求可能触发目标站软封锁，必要时手动分批或自行加节流。
