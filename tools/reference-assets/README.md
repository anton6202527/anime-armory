# Reference asset publishing

Repository maintenance scripts for heavy, optional visual references. Runtime
workflow code must not import this directory: every creative line keeps its own
manifest and downloader so it remains independently distributable.

Camera-movement animations are published once under immutable, content-addressed
R2 keys. Each line keeps its structured manifest, lightweight first-frame preview,
and five-frame contact sheet locally. The original animation is fetched only when
someone explicitly needs to inspect motion cadence.

```bash
# Build five-frame local contact sheets before removing source WebPs.
python3 tools/reference-assets/scripts/build_camera_contact_sheets.py \
  --source /path/to/camera-webps

# Build catalog and update the four self-contained manifests (no upload).
node tools/reference-assets/scripts/publish_camera_moves_r2.mjs \
  --source /path/to/camera-webps --write-manifests

# Upload immutable objects, then publish catalog last.
node tools/reference-assets/scripts/publish_camera_moves_r2.mjs \
  --source /path/to/camera-webps --write-manifests --publish
```

Publishing uses the authenticated Wrangler session. Public redistribution rights
must already be confirmed in `infrastructure/r2/reference-assets.json`; the script
refuses to publish without that declaration.
