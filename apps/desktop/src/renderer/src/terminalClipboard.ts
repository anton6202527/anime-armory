export interface TerminalSelectionSource {
  hasSelection(): boolean
  getSelection(): string
}

/** Copy the exact current terminal selection, leaving focus and highlighting untouched. */
export function copySelectedTerminalText(
  source: TerminalSelectionSource,
  writeText: (text: string) => void,
): boolean {
  if (!source.hasSelection()) return false
  const selection = source.getSelection()
  if (!selection) return false

  try {
    writeText(selection)
    return true
  } catch {
    return false
  }
}
