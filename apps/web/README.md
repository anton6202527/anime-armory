# LabuTV Web

LabuTV Web is the browser UI for the Skill Hub and multimodal production canvas. Its AI/Skill path has one server boundary: every AI generation, Skill execution, Skill source read, and Skill work-file upload goes to the LabuTV backend REST API. It never calls cliproxy, an Electron bridge, a local Agent CLI, or a model provider API directly.

```text
Browser  ->  VITE_API_BASE_URL (/api)  ->  LabuTV backend (:43118)  ->  cliproxy (:8317)
```

Provider keys, unrestricted filesystem paths, model routing, billing rules, and execution privileges remain in the backend process. No model or infrastructure secret may use a `VITE_` environment variable.

Browser-side Supabase and asset clients are disabled even if old `VITE_SUPABASE_*` / `VITE_ASSET_API_URL` values remain in a developer's `.env.local`. Email authentication now uses the BFF `/v1/auth/*` resources and HttpOnly cookies; profile/settings and cloud-sync remain local until their own BFF resources exist. The target and remaining work are tracked in [`../../docs/web-app-architecture.md`](../../docs/web-app-architecture.md).

## Local development

Copy the single browser setting and start the backend before Vite:

```bash
cp apps/web/.env.example apps/web/.env.local
npm run dev:backend
npm run dev --workspace @anime-armory/web
```

The default `VITE_API_BASE_URL=/api` is same-origin. Vite proxies only `/api` to `http://127.0.0.1:43118`; it contains no model middleware and reads no model credentials. Configure cliproxy and Supabase in `apps/backend/.env.local`, not `apps/web/.env.local`. The authentication variables are `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY`.

Before opening the canvas, verify the backend and cliproxy are ready:

```bash
curl http://127.0.0.1:43118/api/v1/health/ready
```

If the readiness check fails, the UI enters a clearly labelled demo/unavailable mode and does not create a fake queued task.

The client can be configured with a deployed API prefix, for example:

```dotenv
VITE_API_BASE_URL=https://api.example.com/api
```

The current Node service is intentionally loopback-only. A deployed backend must first add trusted proxy handling, HTTPS, product authentication, tenant authorization, and an explicit Web-origin policy.

## Canvas production contract

The canvas is intended to become a production workbench for secondary creation and iteration through a final master, not an intermediate-artifact viewer. Its canonical independent skill IDs are `app-script-workbench`, `app-character-turnaround`, `app-first-frame-video`, and `app-audio-video`; older IDs are explicit migration aliases only.

The current Web model implements `app-script-workbench/v3` with one `state`, one canonical `content_sha256`, and one completion definition. The current UI exposes editable shots, assets, prompts, and batch-video entry, but it does not yet close result write-back, per-image acceptance, master composition/QC, or final-acceptance receipt entry. Those fields are target/runtime contracts, not a claim that today's UI can complete them. Backend task success and delegated evidence may establish `machine_complete` only; B14 current-pixel receipts and final acceptance remain human boundaries once their UI is connected.

## REST boundary

The Web client currently consumes these backend routes relative to `VITE_API_BASE_URL`:

- `GET /v1/health/ready`
- `GET /v1/auth/session`
- `POST /v1/auth/access`
- `POST /v1/auth/sign-out`
- `GET /v1/ai/models`
- `POST /v1/ai/generations`
- `PUT /v1/works/:workId/files/:fileId`
- `POST /v1/skill-runs`
- `GET /v1/skill-runs/:runId`
- `GET /v1/skills/:skillId/sources`
- `GET /v1/skills/:skillId/source?path=...`

Each Skill submission includes an explicit `skillId`, work identity, selected model, execution mode, Skill definition when applicable, contextual IDs, attachment IDs, and a per-submission idempotency key. Polling reads the existing run and never resubmits it.

Successful runs may return normalized artifacts as `{ id, kind, name, mimeType?, size?, text?, url?, base64?, assetId? }`, where `kind` is `text`, `image`, `video`, or `audio`. The canvas converts these machine outputs into result nodes; a successful run does not make them human-accepted or complete. Large binary outputs should normally use an authenticated `assetId` or short-lived URL rather than inline base64.

## Verification

```bash
npm run typecheck --workspace @anime-armory/web
npm run build --workspace @anime-armory/web
```

## Interface principle

Keep the interface deliberately simple: use the fewest elements that still communicate the task clearly. Prefer spacing, typography, and restrained color changes over nested borders, decorative containers, or permanently visible controls.
