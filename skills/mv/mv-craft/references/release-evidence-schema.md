# MV 发布证据契约

`release_decision.py` 只记录并复验真实平台操作，不伪装自动上传。正式顺序是 `compose → disclosure → provenance → review → release decision → handoff`；当前 review health 不通过时，发布决策不得进入 `ready_for_handoff`。

## Upload receipt schema v3

回执 `kind` 固定为 `mv_platform_upload_receipt`，`schema_version` 固定为 `3`。v2 和更早回执在正式发布中 fail-closed：需按当前真实上传资产重建 v3，不得只改版本号。

公共必填字段：

- `source`：`platform_api_response` 或 `platform_ui_export`。
- `platform` / `remote_asset_id` / `operator` / `uploaded_at` / `published_url`：平台、真实远端资产 ID、具名操作人、带时区的 ISO-8601 时间与真实作品 URL。
- `uploaded_asset`：实际上传字节的项目内相对 `path` 和当前 `sha256`。禁止绝对路径、`..` 越界、缺失文件或过期 hash。
- `provider_evidence`：平台原始 API JSON 或真实 UI PNG/JPEG/PDF 的项目内 `path+sha256`；不能指向回执自身。

`uploaded_asset` 还受机器标识方式约束：

- `machine_label_method=c2pa`：`uploaded_asset.path` 和 `sha256` 必须分别精确等于当前 `provenance.c2pa.output` 和 `provenance.c2pa.output_sha256`，且当前 signed output 文件 hash 仍一致。上传未签名的 `成片_MV.mp4` 不得声称使用该 C2PA 凭证。
- 其他方法：默认且正式要求绑定当前 `成片_MV.mp4` 及其 SHA-256。

### API 原始响应与完整回执示例

项目先保存原始 `合规/upload-response.json`：

```json
{
  "data": {
    "work_id": "7391234567899",
    "share_url": "https://www.douyin.com/video/7391234567899",
    "created_at": "2026-08-20T16:00:00+08:00"
  }
}
```

再写 v3 回执：

```json
{
  "schema_version": 3,
  "kind": "mv_platform_upload_receipt",
  "source": "platform_api_response",
  "platform": "抖音",
  "remote_asset_id": "7391234567899",
  "operator": "张三",
  "uploaded_at": "2026-08-20T16:00:00+08:00",
  "published_url": "https://www.douyin.com/video/7391234567899",
  "uploaded_asset": {
    "path": "成片_MV.mp4",
    "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  },
  "provider_evidence": {
    "path": "合规/upload-response.json",
    "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  },
  "provider_bindings": {
    "remote_asset_id": {"json_pointer": "/data/work_id"},
    "published_url": {"json_pointer": "/data/share_url"},
    "uploaded_at": {"json_pointer": "/data/created_at", "format": "iso8601"}
  }
}
```

验证器会从 `provider_evidence` 指向的当前原始 JSON 按 JSON Pointer **重新提取** remote ID、URL 和时间，再与回执声明对账；手填相同字段不能代替原始响应。该检查证明本地证据内部一致；如原始响应未有可独立验证的平台签名，它不单独证明平台真实性。

### UI 导出与完整回执示例

```json
{
  "schema_version": 3,
  "kind": "mv_platform_upload_receipt",
  "source": "platform_ui_export",
  "platform": "抖音",
  "remote_asset_id": "7391234567890",
  "operator": "张三",
  "uploaded_at": "2026-08-20T16:00:00+08:00",
  "published_url": "https://www.douyin.com/video/7391234567890",
  "uploaded_asset": {
    "path": "成片_MV.mp4",
    "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  },
  "provider_evidence": {
    "path": "合规/平台上传成功页.png",
    "sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
  },
  "ui_observation": {
    "reviewer": "张三",
    "notes": "已在上传成功页逐项核对作品 ID、URL 与发布状态",
    "observed_at": "2026-08-20T16:01:00+08:00",
    "remote_asset_id": "7391234567890",
    "published_url": "https://www.douyin.com/video/7391234567890"
  }
}
```

UI 回执是具名操作人对当前界面的**人证**，不是可密码学验证的平台机器证明；截图文件格式正确也不证明其内容真实。需要更强保证时，使用平台签名 API 回执或可独立核验的外部审批证据。

## C2PA 真实性边界

C2PA 可证明当前 signed asset 内某份 claim 的完整性、签名验证结果，以及在配置的 trust anchors / TSA 下的信任与时间戳状态。它不证明 claim 所述事实本身为真，不自动认证创作者现实身份或授权，也不证明该文件已被平台实际接收、发布或显示标识。因此 C2PA 不替代平台声明开关、可见标识、上传回执或独立权利核验。
