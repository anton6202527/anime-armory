# Applications

The runnable products in this monorepo live under `apps/`:

- `desktop`: the current Electron client.
- `backend`: the loopback Web BFF / AI service plus Supabase migrations, RLS policies, and Edge Functions.
- `web`: the LabuTV browser Hub and production canvas.

Shared runtime-neutral code belongs in `packages/`. Browser clients may use `contracts` and `cloud-client`; server-only `data-access` and `object-store` code must stay behind the backend boundary.

## Canvas production contract

Electron and Web share the product direction of a production canvas, but they are separate implementations rather than one persisted contract. Electron currently uses `anime_armory_canvas_production_state` v2, `content_hash`, and `canvas.final_product/v1`; Web uses `app-script-workbench/v3` and `content_sha256`. Each episode/workflow instance must expose only one authoritative frontier and one completion verdict, with canonical SHA-256 bindings for its authoritative artifacts.

Web currently exposes editable shots, assets, prompts, and batch-video entry; result write-back, per-image acceptance, master composition/QC, and final-acceptance UI remain incomplete. Electron has a native final-product flow, but its current `desktop_user` reviewer is a local placeholder rather than an authenticated named identity. Accordingly, neither client should claim strong named-human completion through UI until its receipt boundary is closed. The repository's canonical independent skill IDs remain `app-script-workbench`, `app-character-turnaround`, `app-first-frame-video`, and `app-audio-video`; pre-`app-` names are migration aliases only.
