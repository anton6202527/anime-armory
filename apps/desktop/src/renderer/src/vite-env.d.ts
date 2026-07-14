/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ANIME_ARMORY_REPO?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
