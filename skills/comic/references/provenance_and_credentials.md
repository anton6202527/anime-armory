# 资产 provenance 与 C2PA Content Credentials

`skills/comic/scripts/asset_provenance.py` 的 append-only ledger 记录当前资产 SHA、生成/编辑动作、模型/渠道、参考输入、人类贡献与权利依据。hash chain 证明账本是否被改写；它本身不是 C2PA 签名。

```bash
python3 skills/comic/scripts/asset_provenance.py append "$ROOT" 排版/第1话/pages/page_001.png \
  --action composed --human-contribution "分镜、排版与嵌字" --rights-basis self_owned
python3 skills/comic/scripts/asset_provenance.py verify "$ROOT"
```

`sidecar` 只写 `c2pa_status=not_signed` 的披露 JSON，文案明确说明不是 Content Credential。不得改字段把它冒充签名。

## 真正签名

只有项目注册可执行 signer+validator adapter 后才可签名：

```json
{
  "adapters": [{
    "id": "studio-signer",
    "protocol": "comic_c2pa_sign_v1",
    "command": ["/absolute/path/to/signer", "--request", "{request}", "--output", "{output}", "--receipt", "{receipt}"]
  }]
}
```

```bash
python3 skills/comic/scripts/asset_provenance.py sign "$ROOT" 排版/第1话/pages/page_001.png \
  --adapter-id studio-signer
```

流程固定为：

1. 当前 source SHA 必须已有 provenance event。
2. adapter 把 C2PA manifest 嵌入新 derivative，不允许覆盖 source。
3. adapter 的 validator receipt 必须返回 `signature_valid=true`、`manifest_embedded=true`，并精确绑定 source SHA 与 signed asset SHA。
4. 验证通过后才原子提升 signed derivative，写 `生产数据/c2pa_receipts/<signed-sha>.json`，再向 hash-chain ledger 追加 `c2pa_status=signed` 事件。
5. `verify-signature --receipt ...` 会复核当前 signed bytes 与 validator receipt SHA。任一字节变化即失效。

当前合同跟踪 C2PA 2.4。没有 adapter、证书、私钥或真实验证器时，正确结果始终是 `not_signed`；工作流不得代造证书、泄漏私钥，或把签名能力当成所有发布渠道的无条件硬门槛。
