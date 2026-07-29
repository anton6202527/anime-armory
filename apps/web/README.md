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

Supabase remains the authority for identity, project membership, jobs, asset metadata, and the future membership/token ledger. R2 remains the authority for source documents and generated image, audio, video, export, and manifest bytes.

## Local AI Agent bridge

When the Electron app is running, the Web canvas probes its loopback-only bridge at `127.0.0.1:43117`. If Codex CLI, Claude Code, or OpenCode is installed, the Web canvas prefers that local Agent over the cloud API. The first task opens a native Electron confirmation dialog; an approved browser tab receives a temporary session token, and selected source files are copied into the generated local work directory before the CLI starts.

The bridge accepts structured work, file, and prompt requests only. It does not accept shell commands or caller-selected filesystem paths. Local development origins are allowed by default. Additional production Web origins must be explicitly listed in the Electron environment variable `ANIME_ARMORY_WEB_ORIGINS` as a comma-separated list.
