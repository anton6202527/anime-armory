# LabuTV Web

The LabuTV browser client provides a Skill Hub and a multimodal workflow canvas. The Hub supports Skill discovery, attachment input, text/image/video/audio model selection, generation-mode configuration, email accounts, personal Skills, favorites, and light/dark appearance. Dark appearance is the default. The canvas prefers the Electron app's secure local AI Agent bridge when available and falls back to the cloud Agent API.

## Interface principle

Keep the interface deliberately simple: use the fewest elements that still communicate the task clearly. Prefer spacing, typography, and restrained color changes over separator lines, nested borders, decorative containers, or permanently visible controls. Interaction feedback should normally use one thin boundary or one subtle shadow rather than stacked effects.

## Local development

```bash
cp apps/web/.env.example apps/web/.env.local
npm run dev --workspace @anime-armory/web
```

Copy `.env.example` to `.env.local` and fill only the public Supabase URL, publishable key, asset Edge Function URL, and Agent API URL. Provider API keys, Supabase service-role secrets, R2 credentials, billing rules, and token balances must remain server-side. Without cloud configuration the canvas uses a clearly labelled local demo adapter so that product work can continue before the multimodal provider is selected.

Email registration and personal Skill storage use the schema in `apps/backend/supabase/migrations/202607290001_web_user_skills.sql`. Apply the migrations to the target Supabase project and enable the Email provider in Authentication settings. Only the Supabase publishable key belongs in `apps/web/.env.local`; never paste the service-role key into the Web app.

When cloud configuration and a Supabase login session are both available, creating a work calls the existing `assets` Edge Function to create its Supabase project record and upload selected source files directly to Cloudflare R2 through short-lived signed URLs. Without a login session the work remains a local draft and is marked “登录后云同步”.

The intended production flow is:

1. The browser creates a cloud project and uploads selected source files through signed URLs.
2. The browser submits an agent job to the LabuTV backend.
3. The backend authorizes the member, reserves tokens, invokes the configured multimodal model, records usage, and publishes generated assets.
4. The canvas polls or subscribes to job and asset updates.

Canvas pages use a stable, shareable URL shape:

```text
/canvas?guideSource=skill&spaceId=<account-or-team-space>&projectId=<stable-client-project-key>
```

The Web client still accepts legacy `/work/<projectId>` links and replaces them
with the canonical canvas URL. Canvas nodes, edges, viewport, display settings,
activity, and Agent run history are stored locally first and then upserted to
`project_canvases` after the cloud project is ready. Apply
`202607300001_web_canvas_documents.sql` before enabling this sync in production.
Large source and generated files are not embedded in the canvas JSON; they keep
using authenticated asset metadata in Supabase and signed object transfer to R2.

Supabase remains the authority for identity, project membership, jobs, asset metadata, and the future membership/token ledger. R2 remains the authority for source documents and generated image, audio, video, export, and manifest bytes.

## Local model bridge

Canvas text and image nodes prefer the Electron loopback bridge at `127.0.0.1:43117`. The first model request opens a native Electron confirmation dialog; an approved browser origin receives a temporary session token. When the desktop bridge is absent during local `vite` development, the client falls back to a same-origin Vite middleware that talks to the local cli-proxy-api from Node. Web Agent jobs continue through `VITE_AGENT_API_URL` or demo mode—neither model path exposes local Agent CLIs, files, Shell commands, caller-selected filesystem paths, the upstream URL, or its API key.

Local development origins are allowed by default. Additional production Web origins must be explicitly listed in the Electron environment variable `ANIME_ARMORY_WEB_ORIGINS` as a comma-separated list.

After pairing, canvas text and image nodes discover the desktop-side GPT model allowlist through `GET /v1/canvas/models` and generate through `POST /v1/canvas/generate`. The Vite fallback exposes equivalent same-origin development-only routes, rejects non-loopback/cross-origin calls, limits request sizes, concurrency and request rate, and keeps all provider configuration in the server process. It reads `CLI_PROXY_API_URL`/`CLI_PROXY_API_KEY` or the compatible `CUSTOM_OPENAI_BASE_URL`/`CUSTOM_OPENAI_API_KEY` pair from `apps/web/.env.local`; on macOS with the default local URL it can also read the first key from `/opt/homebrew/etc/cliproxyapi.conf`. Never add a `VITE_` prefix to model secrets.

Text generation prefers the Responses API and falls back to Chat Completions only when cli-proxy-api explicitly reports that Responses is unsupported. Image generation uses the Images API. The Web client never connects to port `8317` and never receives either API-key spelling. An older desktop bridge is reported as `bridge_unsupported`, while missing proxy configuration is reported as `proxy_unavailable`, so the UI can distinguish setup problems from a failed generation.
