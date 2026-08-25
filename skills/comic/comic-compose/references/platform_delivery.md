# 平台图片、缩略图与真实预览签收

平台 profile 使用 `field_provenance`：每个宽度、格式、文件上限、缩略图或 preview viewport 都各自记录一手 URL、采集日、confidence 和 freshness；没有证据的字段不靠平台整体 `verified=true` 猜测。

## WEBTOON（官方资料核验至 2026-08-25）

- series square：1080×1080，JPG/PNG，低于 500KB（required）。
- series vertical：1080×1920，JPG/PNG，低于 700KB（required）。
- episode thumbnail：推荐 202×142，JPG/PNG，低于 500KB；尺寸偏差为 WARN，格式/上限仍是硬规格。
- 官方发布预览有 PC/Mobile 两个 viewport。

来源写在 `_lib/platform_profiles.py` 的字段级 provenance。episode 主内容上传尺寸没有当前一手字段时不编造。

公开候选还必须在 manifest 的 `platform_compliance.content_rating` 登记当前内容分级；episode thumbnail 文件名只使用英文字母和数字。来源分别是 WEBTOON 官方 2026-04-22 内容分级上传说明和 2026-03-18 文件规格说明，URL/采集日在 profile 字段级 provenance 内。

## Tapas

- episode images：940px 宽、无通用高度上限、PNG/JPG/GIF、低于 10MB；GIF 特例最大高度 1000px。
- episode thumbnail：300×300，PNG/JPG/GIF，低于 2MB。
- 官方发布说明要求同时检查 desktop/mobile readability。

## 登记真实缩略图

只登记已落盘、可解码并有 SHA 的文件：

```bash
python3 skills/comic/comic-compose/scripts/export_longstrip.py "$ROOT" --chapter 第1话 --render \
  --platform-asset series_square=排版/平台物料/series-square.png \
  --platform-asset series_vertical=排版/平台物料/series-vertical.png \
  --platform-asset episode=排版/平台物料/episode.png
```

缺资产会显式写入 `platform_assets_missing`；字段规格本身不算已生成缩略图。release 会重新解码、核尺寸/格式/字节数与 manifest SHA。

快看投稿 profile 还把官方 `1280px / 300dpi / RGB / PNG或JPG / 首话至少20格` 变成可执行字段。compose 只有在该 profile 下才给实际 PNG/JPG 写 300dpi 元数据；release 会重新打开文件读取 DPI 和 mode，不接受只在 manifest 写一个 `dpi: 300` 的声明。

## 绑定实际平台后台预览

WEBTOON/Tapas 等 `preview_viewports` 有一手证据的平台，公开交付需将实际后台 PC/mobile 截图放进作品根，再写收据：

```bash
python3 skills/comic/scripts/release_verdict.py "$ROOT" 第1话 \
  --accept-platform-preview --preview-source actual_platform_preview \
  --desktop-screenshot 生产数据/platform-preview/desktop.png \
  --mobile-screenshot 生产数据/platform-preview/mobile.png \
  --reviewer "发布编辑" --reason "平台后台双端预览通过"
```

收据会绑定当前 `export_manifest.json` SHA、全部交付物 SHA，以及 `pages/rendered/documents/platform_assets` 的有序 section/page/segment/role；只交换两张内容相同规格的图或顺序，旧预览和旧总发布签收也会失效。`local_simulation` 可留作内部排版检查，但不能通过公开平台 gate。快看邮箱投稿、MANGA Plus 等 profile 没有一手 PC/mobile preview 证据时不会虚构双端闸门；按实际投稿/上传流程人工复核。
