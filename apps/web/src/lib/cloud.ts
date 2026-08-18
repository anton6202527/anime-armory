import type { PendingAttachment, WebWork } from "../types";

/**
 * Browser-side Supabase and asset clients are deliberately disabled.
 *
 * Auth is provided by the LabuTV BFF REST API. Profile/settings, user Skill
 * persistence, canvas sync, and asset control-plane operations remain local
 * until their own BFF resources are introduced. Legacy VITE_* values never
 * reopen a direct Browser -> Supabase/R2 boundary.
 */
export function isCloudConfigured(): boolean {
  return false;
}

export function isAuthConfigured(): boolean {
  return true;
}

export async function getSupabaseAccessToken(): Promise<string | null> {
  return null;
}

export type PersistCloudWorkResult =
  | { state: "local"; work: WebWork }
  | { state: "auth-required"; work: WebWork }
  | { state: "synced"; work: WebWork };

export async function persistWorkToCloud(
  work: WebWork,
  _pendingAttachments: PendingAttachment[],
): Promise<PersistCloudWorkResult> {
  return { state: "local", work: { ...work, cloudState: "local" } };
}
