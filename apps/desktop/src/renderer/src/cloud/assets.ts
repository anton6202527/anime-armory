import { AssetApiClient, type AssetApiClientOptions } from '@anime-armory/cloud-client'

export interface DesktopCloudConfig {
  supabaseUrl: string
  supabasePublishableKey: string
  assetApiUrl: string
}

export type DesktopCloudCapability =
  | { enabled: true; config: DesktopCloudConfig }
  | { enabled: false; missing: Array<keyof DesktopCloudConfig> }

function normalizedUrl(value: string | undefined): string | null {
  if (!value?.trim()) return null
  try {
    const url = new URL(value.trim())
    if (url.protocol !== 'https:' && url.hostname !== 'localhost' && url.hostname !== '127.0.0.1') {
      return null
    }
    return url.toString().replace(/\/$/, '')
  } catch {
    return null
  }
}

/**
 * Detects optional cloud configuration without changing the desktop app's
 * local-first startup path. No server or R2 credentials belong here.
 */
export function desktopCloudCapability(env: ImportMetaEnv = import.meta.env): DesktopCloudCapability {
  const supabaseUrl = normalizedUrl(env.VITE_SUPABASE_URL)
  const supabasePublishableKey = env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim() || null
  const explicitAssetApiUrl = normalizedUrl(env.VITE_ASSET_API_URL)
  const assetApiUrl = explicitAssetApiUrl ?? (supabaseUrl ? `${supabaseUrl}/functions/v1/assets` : null)
  const missing: Array<keyof DesktopCloudConfig> = []

  if (!supabaseUrl) missing.push('supabaseUrl')
  if (!supabasePublishableKey) missing.push('supabasePublishableKey')
  if (!assetApiUrl) missing.push('assetApiUrl')
  if (!supabaseUrl || !supabasePublishableKey || !assetApiUrl) {
    return { enabled: false, missing }
  }

  return {
    enabled: true,
    config: { supabaseUrl, supabasePublishableKey, assetApiUrl },
  }
}

/**
 * Authentication remains a separate concern: the future login UI supplies
 * the current Supabase access token through this callback. The transport is
 * deliberately required instead of falling back to renderer fetch: packaged
 * file:// pages have an opaque origin, so cloud traffic must cross a narrowly
 * allowlisted main/preload IPC boundary rather than weakening CSP/CORS for
 * the unsafe `null` origin.
 */
export function createDesktopAssetClient(
  config: DesktopCloudConfig,
  getAccessToken: AssetApiClientOptions['getAccessToken'],
  fetchThroughMainProcess: typeof globalThis.fetch,
): AssetApiClient {
  return new AssetApiClient({
    endpoint: config.assetApiUrl,
    getAccessToken,
    fetch: fetchThroughMainProcess,
  })
}
