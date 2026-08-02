import { severityOf } from '@/theme/brands'
import type { Severity } from '@/theme/brands'
import type { ProviderId, ProviderStatus, ProviderUsage } from '@/api/types'

/**
 * Situationen, die der Begleiter darstellen kann. Jede führt auf einen Topf
 * von Clips – so wiederholt sich in derselben Lage nicht dauernd dasselbe
 * Bild.
 */
export type Mood =
  | 'offline'
  | 'throttled'
  | 'strained'
  | 'working'
  | 'idle'
  | 'playful'
  | 'resting'

/** Wie oft derselbe Clip läuft, bevor neu gewürfelt wird. */
export const LOOPS_PER_CLIP = 3

/**
 * Ruhe zwischen zwei Durchläufen. Gilt nur für MP4s: Ein GIF trägt seine
 * Schleife in der Datei und lässt sich von außen nicht anhalten.
 */
export const REPLAY_DELAY_MS = 350

export interface Clip {
  src: string
  /**
   * Laufzeit eines Durchlaufs. Ein GIF meldet dem Browser weder Dauer noch
   * Ende, deshalb steht sie hier – gemessen aus den Bildverzögerungen der
   * Datei. Bei MP4s zählt stattdessen das `ended`-Ereignis.
   */
  seconds: number
  kind: 'gif' | 'video'
}

/** `[Datei, Laufzeit in Sekunden]` – Datei ausgetauscht heißt Laufzeit prüfen. */
type Entry = readonly [file: string, seconds: number]

/**
 * Vite löst das Muster zur Bauzeit auf. Ein Eintrag, der auf eine gelöschte
 * Datei zeigt, fällt beim Auflösen still heraus – der Ordner darf also
 * weiter kuratiert werden, ohne dass die Kachel bricht.
 */
const FILES = import.meta.glob('../assets/animations/**/*.{gif,mp4}', {
  eager: true,
  import: 'default',
  query: '?url',
}) as Record<string, string>

type MascotFolder = 'clawd' | 'cloudling'

function resolve(folder: MascotFolder, entries: readonly Entry[]): Clip[] {
  const clips: Clip[] = []

  for (const [file, seconds] of entries) {
    const match = Object.entries(FILES).find(([path]) =>
      path.endsWith(`/${folder}/${file}`),
    )
    if (!match) continue
    clips.push({
      src: match[1],
      seconds,
      kind: file.endsWith('.mp4') ? 'video' : 'gif',
    })
  }

  return clips
}

type Reel = Partial<Record<Mood, Clip[]>>

function reelOf(
  folder: MascotFolder,
  entries: Record<Mood, readonly Entry[]>,
): Reel {
  const reel: Reel = {}

  for (const mood of Object.keys(entries) as Mood[]) {
    const clips = resolve(folder, entries[mood])
    if (clips.length) reel[mood] = clips
  }

  return reel
}

/** Claude: die Clawd-Sprites plus die selbst gebauten MP4s. */
const CLAWD: Record<Mood, readonly Entry[]> = {
  offline: [
    ['clawd-error.gif', 2.99],
    ['clawd-disconnected.gif', 5.76],
    ['clawd-mini-alert.gif', 4.47],
    ['clawd_apidown.mp4', 3.2],
  ],
  throttled: [
    ['clawd-dizzy.gif', 3.84],
    ['clawd-react-annoyed.gif', 3.47],
    ['clawd-sweeping.gif', 1.44],
    ['clawd_coffee.mp4', 3.2],
  ],
  strained: [
    ['clawd-carrying.gif', 1.92],
    ['clawd-sweeping.gif', 1.44],
    ['clawd-notification.gif', 3.87],
    ['clawd-working-confused.gif', 5.87],
    ['clawd-working-overheated.gif', 2.88],
    ['clawd-working-pushing.gif', 1.92],
    ['clawd_coffee.mp4', 3.2],
  ],
  working: [
    ['clawd-typing.gif', 1.44],
    ['clawd-building.gif', 0.96],
    ['clawd-debugger.gif', 2.88],
    ['clawd-conducting.gif', 1.92],
    ['clawd-working-beacon.gif', 1.92],
    ['clawd-working-wizard.gif', 2.88],
    ['mini-crab-typing.gif', 35],
    ['clawd_coding.mp4', 3.2],
  ],
  idle: [
    ['clawd-idle.gif', 3.19],
    ['clawd-idle-reading.gif', 3.99],
    ['clawd-idle-living.gif', 15.6],
    ['clawd-thinking.gif', 3.84],
    ['clawd-bubble.gif', 4.47],
    ['clawd-mini-idle.gif', 4.99],
    ['clawd-mini-peek.gif', 3.47],
    ['clawd-static-base.gif', 0.99],
  ],
  playful: [
    ['clawd-happy.gif', 1.92],
    ['clawd-mini-happy.gif', 2.99],
    ['clawd-juggling.gif', 1.12],
    ['clawd-headphones-groove.gif', 3.19],
    ['clawd-react-double-jump.gif', 3.47],
    ['clawd-crab-walking.gif', 3.84],
    ['clawd-mini-clawd.gif', 3.84],
    ['clawd-mini-crabwalk.gif', 2.99],
    ['clawd-mini-enter.gif', 3.47],
  ],
  resting: [
    ['clawd-sleeping.gif', 5.76],
    ['clawd-going-away.gif', 2.93],
    ['clawd-mini-idle.gif', 4.99],
    ['clawd_sleep.mp4', 3.2],
  ],
}

/** Codex: die Cloudling-Sprites. */
const CLOUDLING: Record<Mood, readonly Entry[]> = {
  offline: [
    ['cloudling-error.gif', 4.99],
    ['cloudling-mini-alert.gif', 2.59],
    ['cloudling-attention.gif', 3.59],
  ],
  throttled: [
    ['cloudling-sweeping.gif', 5.47],
    ['cloudling-mini-crabwalk.gif', 2.99],
  ],
  strained: [
    ['cloudling-carrying.gif', 2.99],
    ['cloudling-sweeping.gif', 5.47],
    ['cloudling-notification.gif', 2.59],
  ],
  working: [
    ['cloudling-typing.gif', 2.99],
    ['cloudling-building.gif', 2.99],
    ['cloudling-mini-working.gif', 2.99],
    ['cloudling-conducting.gif', 2.99],
  ],
  idle: [
    ['cloudling-idle.gif', 3.19],
    ['cloudling-idle-reading.gif', 4.99],
    ['cloudling-thinking.gif', 2.99],
    ['cloudling-mini-idle.gif', 4.99],
    ['cloudling-mini-peek.gif', 1.47],
  ],
  playful: [
    ['cloudling-mini-happy.gif', 3.59],
    ['cloudling-juggling.gif', 2.99],
    ['cloudling-mini-crabwalk.gif', 2.99],
  ],
  resting: [
    ['cloudling-sleeping.gif', 2.99],
    ['cloudling-mini-sleep.gif', 2.99],
  ],
}

/** Nur Anbieter mit hinterlegten Clips bekommen einen Begleiter. */
export const MASCOTS: Partial<Record<ProviderId, Reel>> = {
  claude: reelOf('clawd', CLAWD),
  codex: reelOf('cloudling', CLOUDLING),
}

const OFFLINE: ReadonlySet<ProviderStatus> = new Set([
  'auth_missing',
  'auth_expired',
  'unauthorized',
  'unreachable',
  'unexpected_shape',
  'error',
  'disabled',
])

/**
 * Lagen, in denen der Clip die Statusanzeige *ist* und nicht Stimmung. Hier
 * wird weder gewürfelt noch auf die drei Durchläufe gewartet: Geht das
 * Backend weg, wechselt das Bild sofort.
 *
 * Bewusst nur Störungen, die von selbst vergehen. Ein knappes Kontingent
 * gehört nicht dazu: Es hält stundenlang an, und ein stundenlang
 * festgenagelter Clip liest sich als Fehler statt als Zustand. `strained`
 * wirkt deshalb weiter unten als Gewicht.
 */
export function forcedMood(
  provider: ProviderUsage,
  backendDown: boolean,
): Mood | undefined {
  if (backendDown || OFFLINE.has(provider.status)) return 'offline'
  if (provider.status === 'rate_limited') return 'throttled'
  return undefined
}

export function severityOfPrimary(provider: ProviderUsage): Severity {
  const primary = provider.windows.find((window) => window.primary) ?? provider.windows[0]
  return primary ? severityOf(primary.remaining_percent) : 'ok'
}

/** Restkontingent des Hauptfensters – bestimmt die Spiellaune. */
export function remainingOfPrimary(provider: ProviderUsage): number {
  const primary = provider.windows.find((window) => window.primary) ?? provider.windows[0]
  return primary ? primary.remaining_percent : 100
}

export type Weights = Partial<Record<Mood, number>>

type Slot = { until: number } & Record<'working' | 'idle' | 'playful' | 'resting', number>

/** Auch der Auffangwert für Stunden jenseits der Tabelle. */
const LATE_NIGHT: Slot = { until: 24, working: 2, idle: 2, playful: 1, resting: 7 }

/**
 * Tagesrhythmus als Grundstimmung. `offline` und `throttled` fehlen hier
 * bewusst – sie gehören zum Störfall und wären als Laune eine
 * Falschmeldung.
 */
const BY_HOUR: ReadonlyArray<Slot> = [
  { until: 6, working: 1, idle: 2, playful: 0, resting: 9 }, // tiefe Nacht
  { until: 10, working: 4, idle: 4, playful: 2, resting: 2 }, // Morgen
  { until: 13, working: 9, idle: 3, playful: 1, resting: 0 }, // Vormittag
  { until: 15, working: 4, idle: 4, playful: 3, resting: 1 }, // Mittagspause
  { until: 19, working: 9, idle: 3, playful: 2, resting: 0 }, // Nachmittag
  { until: 22, working: 4, idle: 4, playful: 4, resting: 1 }, // Abend
  LATE_NIGHT,
]

export interface MoodContext {
  /** Stunde 0–23 der lokalen Zeit. */
  hour: number
  /** Nachtmodus der Einstellungen. */
  nightMode: boolean
  /** Automatische Aktualisierung ist aus – es passiert gerade nichts. */
  paused: boolean
  /** Zustand des Hauptfensters. */
  severity: Severity
  /** Restkontingent des Hauptfensters in Prozent. */
  remaining: number
  /** Werte stammen aus dem letzten geglückten Abruf. */
  stale: boolean
}

/**
 * Die Tageszeit gibt den Grundton, die Lage der Kachel verschiebt ihn:
 * knappes Kontingent schickt den Begleiter ans Aufräumen, reichlich freies
 * ins Spielen, ein gedimmter oder pausierter Kiosk ins Bett.
 */
export function ambientWeights(context: MoodContext): Weights {
  const slot = BY_HOUR.find((entry) => context.hour < entry.until) ?? LATE_NIGHT

  const weights: Weights = {
    working: slot.working,
    idle: slot.idle,
    playful: slot.playful,
    resting: slot.resting,
    strained: 0,
  }

  const scale = (mood: Mood, factor: number) => {
    weights[mood] = (weights[mood] ?? 0) * factor
  }

  if (context.severity === 'critical') {
    // Fast leer: überwiegend Sparbetrieb, aber nicht ausschließlich. Nachts
    // darf er weiter schlafen – das Fenster füllt sich erst zum Reset.
    weights.strained = 12
    scale('working', 0.15)
    scale('playful', 0)
  } else if (context.severity === 'warning') {
    weights.strained = 4
    scale('working', 0.6)
    scale('playful', 0.3)
  } else if (context.remaining >= 70) {
    // Reichlich Luft: Es darf gealbert werden.
    scale('playful', 2)
  }

  if (context.stale) scale('idle', 1.5)

  if (context.paused) {
    weights.resting = (weights.resting ?? 0) * 2 + 1
    scale('idle', 1.5)
    scale('working', 0.5)
  }

  if (context.nightMode) {
    weights.resting = (weights.resting ?? 0) * 4 + 2
    scale('working', 0.4)
    scale('playful', 0.2)
  }

  return weights
}

/**
 * Wie stark die zuletzt gespielte Laune beim nächsten Zug benachteiligt
 * wird. Ein harter Ausschluss wäre falsch: Sobald nur zwei Launen Gewicht
 * haben, ließe er stur abwechseln und die Gewichte wären wirkungslos.
 */
const REPEAT_DAMPING = 0.25

/**
 * Gewichtete Ziehung mit Dämpfung der Vorrunde. `available` sind die
 * Launen, für die es überhaupt Clips gibt.
 */
export function pickMood(
  weights: Weights,
  available: readonly Mood[],
  previous?: Mood,
): Mood | undefined {
  const usable = available
    .map((mood): [Mood, number] => {
      const weight = weights[mood] ?? 0
      return [mood, mood === previous ? weight * REPEAT_DAMPING : weight]
    })
    .filter(([, weight]) => weight > 0)

  if (!usable.length) return available[0]

  const total = usable.reduce((sum, [, weight]) => sum + weight, 0)
  let ticket = Math.random() * total
  let last: Mood | undefined

  for (const [mood, weight] of usable) {
    ticket -= weight
    if (ticket <= 0) return mood
    last = mood
  }

  // Nur erreichbar, wenn Rundungsfehler das letzte Los verschluckt haben.
  return last
}

/** Gleichverteilt aus dem Topf, aber nie derselbe Clip zweimal am Stück. */
export function pickClip(clips: readonly Clip[], previous?: Clip): Clip | undefined {
  if (!clips.length) return undefined

  const fresh = clips.filter((clip) => clip.src !== previous?.src)
  const pool = fresh.length ? fresh : clips

  return pool[Math.floor(Math.random() * pool.length)]
}
