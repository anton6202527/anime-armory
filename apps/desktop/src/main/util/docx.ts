import yauzl from 'yauzl'

const OUTPUT_CAP = 2 * 1024 * 1024

/** Entries carrying document text, in reading order preference. */
const TEXT_PARTS = /^word\/(document\.xml|header\d*\.xml|footer\d*\.xml|footnotes\.xml|endnotes\.xml)$/

function decodeEntities(s: string): string {
  return s
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&#x([0-9a-fA-F]+);/g, (_, h) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(parseInt(d, 10)))
    .replace(/&amp;/g, '&')
}

/** Extract plain text from WordprocessingML by scanning w:t/a:t/m:t runs. */
function extractXmlText(xml: string): string {
  let out = ''
  const re = /<(\/?)(w:p|w:tr|w:tab|w:br|w:cr|(?:[wam]):t)(\s[^>]*)?(\/?)>|([^<]+)/g
  let inText = false
  let m: RegExpExecArray | null
  while ((m = re.exec(xml)) !== null) {
    if (out.length > OUTPUT_CAP) break
    const [, close, tag, , selfClose, text] = m
    if (text !== undefined) {
      if (inText) out += decodeEntities(text)
      continue
    }
    if (tag === 'w:tab' ) { out += '\t'; continue }
    if (tag === 'w:br' || tag === 'w:cr') { out += '\n'; continue }
    if (tag === 'w:p' || tag === 'w:tr') {
      if (close) out += '\n'
      continue
    }
    // a text run tag (w:t / a:t / m:t)
    if (selfClose) continue
    inText = !close
  }
  return out.slice(0, OUTPUT_CAP)
}

export function readDocxText(absPath: string): Promise<string> {
  return new Promise((resolve, reject) => {
    yauzl.open(absPath, { lazyEntries: true }, (err, zip) => {
      if (err || !zip) {
        reject(new Error('无法打开 docx 文件'))
        return
      }
      const parts = new Map<string, string>()
      zip.on('entry', (entry) => {
        if (!TEXT_PARTS.test(entry.fileName)) {
          zip.readEntry()
          return
        }
        zip.openReadStream(entry, (streamErr, stream) => {
          if (streamErr || !stream) {
            zip.readEntry()
            return
          }
          const chunks: Buffer[] = []
          stream.on('data', (c: Buffer) => chunks.push(c))
          stream.on('end', () => {
            parts.set(entry.fileName, Buffer.concat(chunks).toString('utf8'))
            zip.readEntry()
          })
          stream.on('error', () => zip.readEntry())
        })
      })
      zip.on('end', () => {
        const order = [...parts.keys()].sort((a, b) =>
          a === 'word/document.xml' ? -1 : b === 'word/document.xml' ? 1 : a.localeCompare(b),
        )
        const text = order.map((k) => extractXmlText(parts.get(k) ?? '')).join('\n')
        resolve(text.slice(0, OUTPUT_CAP))
      })
      zip.on('error', () => reject(new Error('docx 解析失败')))
      zip.readEntry()
    })
  })
}
