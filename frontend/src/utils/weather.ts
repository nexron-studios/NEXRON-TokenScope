/**
 * Übersetzt den WMO-Wettercode in eine handvoll Lagen, die sich unterscheiden
 * lassen sollen. Der Code kennt 28 Abstufungen; auf einer Kopfzeile von
 * wenigen Zentimetern sind davon elf sichtbar – „leichter" und „mäßiger"
 * Regen bekommen dasselbe Symbol.
 *
 * Bewusst ohne Vue-Import: Welches Symbol eine Lage bekommt, entscheidet die
 * Komponente, damit diese Zuordnung für sich testbar bleibt.
 */

export const weatherKindList = [
  'clear',
  'mostly-clear',
  'cloudy',
  'overcast',
  'fog',
  'drizzle',
  'rain',
  'freezing',
  'snow',
  'thunder',
  'hail',
] as const

export type WeatherKind = (typeof weatherKindList)[number]

/** Gefrierender Niesel, gefrierender Regen und Reifnebel – die Glättemacher. */
const ICY_CODES = new Set([48, 56, 57, 66, 67])

const CODE_KINDS: ReadonlyArray<readonly [readonly number[], WeatherKind]> = [
  [[0], 'clear'],
  [[1], 'mostly-clear'],
  [[2], 'cloudy'],
  [[3], 'overcast'],
  [[45, 48], 'fog'],
  [[51, 53, 55], 'drizzle'],
  [[56, 57, 66, 67], 'freezing'],
  [[61, 63, 65, 80, 81, 82], 'rain'],
  [[71, 73, 75, 77, 85, 86], 'snow'],
  [[95], 'thunder'],
  [[96, 99], 'hail'],
]

export const weatherKind = (code: number): WeatherKind => {
  const match = CODE_KINDS.find(([codes]) => codes.includes(code))
  return match ? match[1] : 'cloudy'
}

/**
 * Ob vor Glätte gewarnt werden soll. Neben den eindeutigen Codes zählt auch
 * Nässe knapp über null: Die Fahrbahn ist kälter als die Luft, und genau
 * dieser Fall steht in keinem Wettercode.
 */
const WET_KINDS: ReadonlySet<WeatherKind> = new Set(['drizzle', 'rain', 'fog'])
const WET_FROST_CEILING = 3

export const isIcy = (code: number, temperature: number): boolean => {
  if (ICY_CODES.has(code)) return true
  if (weatherKind(code) === 'snow') return true
  return WET_KINDS.has(weatherKind(code)) && temperature <= WET_FROST_CEILING
}

/** Ganze Grad – Nachkommastellen sind auf der Kopfzeile nur Unruhe. */
export const formatTemperature = (locale: string, value: number): string =>
  `${new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(value)}°`
