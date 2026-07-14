import { createClient } from '@supabase/supabase-js'

import { AssetApiClient, type AssetUploadSource } from '@anime-armory/cloud-client'
import { R2ObjectStore, r2ConfigFromEnv } from '@anime-armory/object-store'

function requiredEnv(name: string): string {
  const value = process.env[name]?.trim()
  if (!value) throw new Error(`${name} is required`)
  return value
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

function isNotFound(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false
  const value = error as { name?: string; $metadata?: { httpStatusCode?: number } }
  return value.name === 'NotFound' ||
    value.name === 'NoSuchKey' ||
    value.$metadata?.httpStatusCode === 404
}

async function main(): Promise<void> {
  const supabaseUrl = requiredEnv('SUPABASE_URL')
  const publishableKey = requiredEnv('SUPABASE_PUBLISHABLE_KEY')
  const secretKey = requiredEnv('SUPABASE_SECRET_KEY')
  const assetApiUrl = requiredEnv('ASSET_API_URL')
  const objectStore = new R2ObjectStore(r2ConfigFromEnv(process.env))

  const admin = createClient(supabaseUrl, secretKey, {
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
  })
  const userClient = createClient(supabaseUrl, publishableKey, {
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
  })

  const testId = crypto.randomUUID()
  const email = `anime-armory-e2e-${testId}@example.com`
  const password = `Aa9-${crypto.randomUUID()}!`
  let userId: string | null = null
  let projectId: string | null = null
  let result: Record<string, unknown> | null = null
  let failure: unknown = null
  const objectKeys = new Set<string>()

  try {
    const { data: createdUser, error: createUserError } = await admin.auth.admin.createUser({
      email,
      password,
      email_confirm: true,
      user_metadata: { display_name: 'Cloud E2E' },
    })
    if (createUserError || !createdUser.user) {
      throw new Error(`create test user: ${createUserError?.message ?? 'missing user'}`)
    }
    userId = createdUser.user.id

    const { data: signedIn, error: signInError } = await userClient.auth.signInWithPassword({
      email,
      password,
    })
    if (signInError || !signedIn.session) {
      throw new Error(`sign in test user: ${signInError?.message ?? 'missing session'}`)
    }

    const { data: accountId, error: accountError } = await userClient.rpc('current_account_id')
    if (accountError || typeof accountId !== 'string' || accountId !== userId) {
      throw new Error(`resolve application account: ${accountError?.message ?? 'identity mismatch'}`)
    }

    const assetClient = new AssetApiClient({
      endpoint: assetApiUrl,
      getAccessToken: async () => signedIn.session.access_token,
    })
    const clientKey = crypto.randomUUID()
    const ensuredProject = await assetClient.ensureProject(clientKey, 'Cloud E2E')
    projectId = ensuredProject.project.id
    const listedProjects = await assetClient.listProjects()
    if (!listedProjects.projects.some((project) => project.id === projectId && project.clientKey === clientKey)) {
      throw new Error('created project is missing from the authenticated project list')
    }

    const bytes = new TextEncoder().encode('anime-armory authenticated cloud e2e')
    const source: AssetUploadSource = {
      name: 'cloud-e2e.txt',
      type: 'text/plain',
      size: bytes.byteLength,
      slice(start = 0, end = bytes.byteLength, contentType = 'text/plain') {
        return new Blob([bytes.slice(start, end)], { type: contentType })
      },
    }
    const asset = await assetClient.uploadAsset({
      projectId,
      relativePath: 'cloud-e2e.txt',
      source,
    })
    if (asset.status !== 'ready') throw new Error(`asset finished as ${asset.status}`)
    const listedAssets = await assetClient.listAssets(projectId)
    if (!listedAssets.assets.some((item) => item.id === asset.id && item.relativePath === 'cloud-e2e.txt')) {
      throw new Error('uploaded asset is missing from the project asset list')
    }

    objectKeys.add(asset.object.key)
    const stagedKey = `_uploads/${projectId}/${asset.id}`
    objectKeys.add(stagedKey)

    const download = await assetClient.createDownloadUrl(asset.id)
    const downloaded = await fetch(download.download.url, {
      method: download.download.method,
      headers: download.download.headers,
    })
    if (!downloaded.ok) throw new Error(`signed download returned HTTP ${downloaded.status}`)
    const downloadedBytes = new Uint8Array(await downloaded.arrayBuffer())
    if (
      downloadedBytes.length !== bytes.length ||
      downloadedBytes.some((value, index) => value !== bytes[index])
    ) {
      throw new Error('downloaded content differs from uploaded content')
    }

    const { data: visibleAsset, error: visibleAssetError } = await userClient
      .from('assets')
      .select('id,status,object_key')
      .eq('id', asset.id)
      .single()
    if (visibleAssetError || visibleAsset?.status !== 'ready') {
      throw new Error(`RLS asset read: ${visibleAssetError?.message ?? 'asset is not ready'}`)
    }

    const finalObject = await objectStore.headObject(asset.object.key)
    if (finalObject.sizeBytes !== bytes.byteLength || finalObject.metadata['asset-id'] !== asset.id) {
      throw new Error('final R2 object metadata mismatch')
    }
    let stagedObjectDeleted = false
    try {
      await objectStore.headObject(stagedKey)
    } catch (error) {
      if (!isNotFound(error)) throw error
      stagedObjectDeleted = true
    }
    if (!stagedObjectDeleted) throw new Error('staged upload was not deleted after promotion')

    result = {
      authenticatedCloudE2E: 'ok',
      assetStatus: asset.status,
      bytes: bytes.byteLength,
      rlsRead: true,
      projectDiscovery: true,
      assetDiscovery: true,
      stagedObjectDeleted,
      downloadStatus: downloaded.status,
    }
  } catch (error) {
    failure = error
  }

  const cleanupErrors: string[] = []
  if (projectId) {
    const { data: assets, error } = await admin
      .from('assets')
      .select('id,object_key')
      .eq('project_id', projectId)
    if (error) {
      cleanupErrors.push(`list cleanup assets: ${error.message}`)
    } else {
      for (const asset of assets ?? []) {
        objectKeys.add(asset.object_key as string)
        objectKeys.add(`_uploads/${projectId}/${asset.id as string}`)
      }
    }
  }
  for (const key of objectKeys) {
    try {
      await objectStore.deleteObject(key)
    } catch (error) {
      cleanupErrors.push(`delete test object: ${errorMessage(error)}`)
    }
  }
  if (projectId) {
    const { error } = await admin.from('projects').delete().eq('id', projectId)
    if (error) cleanupErrors.push(`delete test project: ${error.message}`)
  }
  if (userId) {
    const identityDelete = await admin
      .from('account_identities')
      .delete()
      .eq('provider', 'supabase')
      .eq('provider_subject', userId)
    if (identityDelete.error) cleanupErrors.push(`delete test identity: ${identityDelete.error.message}`)

    const accountDelete = await admin.from('accounts').delete().eq('id', userId)
    if (accountDelete.error) cleanupErrors.push(`delete test account: ${accountDelete.error.message}`)

    const userDelete = await admin.auth.admin.deleteUser(userId)
    if (userDelete.error) cleanupErrors.push(`delete test auth user: ${userDelete.error.message}`)
  }

  if (failure) throw failure
  if (cleanupErrors.length) throw new Error(`E2E cleanup failed: ${cleanupErrors.join('; ')}`)
  console.log(JSON.stringify({ ...result, cleanup: 'ok' }))
}

void main().catch((error) => {
  console.error(errorMessage(error))
  process.exitCode = 1
})
