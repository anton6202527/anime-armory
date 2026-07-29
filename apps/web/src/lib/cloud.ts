import type { SupabaseClient } from "@supabase/supabase-js";
import type { DraftAttachment, PendingAttachment, WebWork } from "../types";

interface CloudConfig {
  supabaseUrl: string;
  publishableKey: string;
  assetApiUrl: string;
}

type SupabaseBrowserConfig = Omit<CloudConfig, "assetApiUrl">;

function supabaseConfig(): SupabaseBrowserConfig | null {
  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL?.trim();
  const publishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim();
  if (!supabaseUrl || !publishableKey) return null;
  return { supabaseUrl, publishableKey };
}

function cloudConfig(): CloudConfig | null {
  const supabase = supabaseConfig();
  const assetApiUrl = import.meta.env.VITE_ASSET_API_URL?.trim();
  if (!supabase || !assetApiUrl) return null;
  return { ...supabase, assetApiUrl };
}

let supabaseClientPromise: Promise<SupabaseClient | null> | null = null;

export async function getSupabaseClient(): Promise<SupabaseClient | null> {
  const config = supabaseConfig();
  if (!config) return null;
  supabaseClientPromise ??= import("@supabase/supabase-js").then(({ createClient }) =>
    createClient(config.supabaseUrl, config.publishableKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    }),
  );
  return supabaseClientPromise;
}

export function isCloudConfigured() {
  return cloudConfig() !== null;
}

export function isAuthConfigured() {
  return supabaseConfig() !== null;
}

export async function getSupabaseAccessToken(): Promise<string | null> {
  const client = await getSupabaseClient();
  if (!client) return null;
  const { data, error } = await client.auth.getSession();
  if (error) throw error;
  return data.session?.access_token ?? null;
}

function safeRelativeName(name: string) {
  return name.replace(/[\\/]/g, "_").replace(/^\.+/, "") || "unnamed";
}

export type PersistCloudWorkResult =
  | { state: "local"; work: WebWork }
  | { state: "auth-required"; work: WebWork }
  | { state: "synced"; work: WebWork };

export async function persistWorkToCloud(
  work: WebWork,
  pendingAttachments: PendingAttachment[],
): Promise<PersistCloudWorkResult> {
  const config = cloudConfig();
  if (!config) return { state: "local", work: { ...work, cloudState: "local" } };

  const accessToken = await getSupabaseAccessToken();
  if (!accessToken) {
    return { state: "auth-required", work: { ...work, cloudState: "auth-required" } };
  }

  const { AssetApiClient } = await import("@anime-armory/cloud-client");
  const client = new AssetApiClient({
    endpoint: config.assetApiUrl,
    getAccessToken: async () => getSupabaseAccessToken(),
  });
  const { project } = await client.ensureProject(work.id, work.name);
  const uploaded = new Map<string, DraftAttachment>();

  for (const pending of pendingAttachments) {
    const asset = await client.uploadAsset({
      projectId: project.id,
      relativePath: `源本/${pending.id}/${safeRelativeName(pending.name)}`,
      source: pending.file,
    });
    uploaded.set(pending.id, {
      id: pending.id,
      name: pending.name,
      size: pending.size,
      type: pending.type,
      assetId: asset.id,
    });
  }

  return {
    state: "synced",
    work: {
      ...work,
      cloudProjectId: project.id,
      cloudState: "synced",
      attachments: work.attachments.map((attachment) => uploaded.get(attachment.id) ?? attachment),
    },
  };
}
