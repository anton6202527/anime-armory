/** FNV-1a 64-bit over bytes; returned as a hex string (JSON-safe). */
export function fnv1a64(buf: Buffer): string {
  let hash = 0xcbf29ce484222325n
  const prime = 0x100000001b3n
  const mask = 0xffffffffffffffffn
  for (let i = 0; i < buf.length; i++) {
    hash ^= BigInt(buf[i])
    hash = (hash * prime) & mask
  }
  return hash.toString(16)
}

/** Small stable string hash for cache keys (hex, 16 chars max). */
export function hashPathKey(input: string): string {
  return fnv1a64(Buffer.from(input, 'utf8')).padStart(16, '0')
}
