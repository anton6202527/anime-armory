/** Text decoding mirroring the Rust reader: BOM UTF-8/16, heuristic UTF-16, GB18030. */

export function looksBinary(buf: Buffer): boolean {
  const probe = buf.subarray(0, Math.min(buf.length, 8192))
  return probe.includes(0)
}

function decodeUtf16(buf: Buffer, littleEndian: boolean): string {
  const dec = new TextDecoder(littleEndian ? 'utf-16le' : 'utf-16be', { fatal: false })
  return dec.decode(buf)
}

/** Heuristic: does the buffer look like BOM-less UTF-16 text? */
function sniffUtf16(buf: Buffer): 'le' | 'be' | null {
  const n = Math.min(buf.length, 4096)
  if (n < 4 || n % 2 !== 0) return null
  let evenZeros = 0
  let oddZeros = 0
  for (let i = 0; i < n; i++) {
    if (buf[i] === 0) {
      if (i % 2 === 0) evenZeros++
      else oddZeros++
    }
  }
  const half = n / 2
  if (oddZeros > half * 0.3 && evenZeros < half * 0.05) return 'le'
  if (evenZeros > half * 0.3 && oddZeros < half * 0.05) return 'be'
  return null
}

export function decodeTextBuffer(buf: Buffer): string {
  // BOM detection
  if (buf.length >= 3 && buf[0] === 0xef && buf[1] === 0xbb && buf[2] === 0xbf) {
    return buf.subarray(3).toString('utf8')
  }
  if (buf.length >= 2 && buf[0] === 0xff && buf[1] === 0xfe) {
    return decodeUtf16(buf.subarray(2), true)
  }
  if (buf.length >= 2 && buf[0] === 0xfe && buf[1] === 0xff) {
    return decodeUtf16(buf.subarray(2), false)
  }
  // strict UTF-8
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(buf)
  } catch {
    // fall through
  }
  const utf16 = sniffUtf16(buf)
  if (utf16) return decodeUtf16(buf, utf16 === 'le')
  // GB18030 (superset of GBK/GB2312) — Node ships full ICU
  try {
    return new TextDecoder('gb18030', { fatal: false }).decode(buf)
  } catch {
    return buf.toString('utf8')
  }
}
