/**
 * Modell-IDs lesbar machen. Die Logs führen `claude-opus-4-5-20251101` oder
 * `gpt-5-codex`; in einer Kachel steht besser „Opus 4.5“.
 *
 * Bewusst tolerant: Was nicht in eines der bekannten Muster fällt, geht
 * unverändert durch. Ein unbekanntes Modell soll auffallen, nicht in einer
 * hübschen, aber falschen Bezeichnung verschwinden – die rohe ID steht in der
 * Oberfläche zusätzlich im `title`.
 */

const FAMILIES: Record<string, string> = {
  opus: 'Opus',
  sonnet: 'Sonnet',
  haiku: 'Haiku',
  fable: 'Fable',
}

/** `4-5` → `4.5`, `5` → `5`. */
const version = (parts: string[]) => parts.join('.')

const isNumber = (part: string) => /^\d+(\.\d+)*$/.test(part)

export function modelLabel(raw: string): string {
  const id = raw.trim().toLowerCase()
  if (!id) return raw

  // Claude schreibt lokal erzeugte Nachrichten ohne echtes Modell.
  if (id === '<synthetic>') return 'Synthetisch'
  if (id === 'unbekannt') return 'Unbekannt'

  // Datumsstempel am Ende tragen nichts zur Unterscheidung bei.
  const parts = id.replace(/-\d{8}$/, '').split('-')

  if (parts[0] === 'claude') {
    // Die Familie stand mal vor, mal hinter der Versionsnummer
    // (`claude-3-5-sonnet` gegen `claude-sonnet-4-5`) – deshalb wird gesucht,
    // nicht an einer festen Stelle gelesen.
    const family = parts.map((part) => FAMILIES[part]).find(Boolean)
    const digits = parts.slice(1).filter(isNumber)
    if (family) return digits.length ? `${family} ${version(digits)}` : family
  }

  const family = parts[0] ?? ''
  if (family === 'gpt' || family === 'o3' || family === 'o4') {
    const rest = parts.slice(1)
    const digits: string[] = []
    while (rest.length && isNumber(rest[0] ?? '')) digits.push(rest.shift() ?? '')
    const head = family === 'gpt' ? `GPT-${version(digits)}` : family.toUpperCase()
    const tail = rest.map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(' ')
    return tail ? `${head} ${tail}` : head
  }

  return raw
}
