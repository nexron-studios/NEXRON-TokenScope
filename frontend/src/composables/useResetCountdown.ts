import { computed, toValue } from 'vue'
import { useNow } from '@vueuse/core'
import { useI18n } from '@/composables/useI18n'
import type { MaybeRefOrGetter } from 'vue'

/**
 * Zählt bis zum nächsten Reset eines Limitfensters herunter.
 * `null` und ungültige Zeitstempel sind erwartbare Zustände, weil die
 * Anbieter das Feld nicht garantiert liefern.
 */
export function useResetCountdown(
  resetAt: MaybeRefOrGetter<string | null | undefined>,
) {
  const now = useNow({ interval: 1_000 })
  const { locale, t } = useI18n()

  const target = computed(() => {
    const value = toValue(resetAt)
    if (!value) return undefined
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? undefined : date
  })

  const remainingMs = computed(() => {
    if (!target.value) return undefined
    return target.value.getTime() - now.value.getTime()
  })

  /** Kompakte Anzeige, z. B. `2:18 Std.` oder `3 T 5 Std.` */
  const countdown = computed(() => {
    const difference = remainingMs.value
    if (difference === undefined) return '–'
    if (difference <= 0) return t('unit.now')

    const totalMinutes = Math.ceil(difference / 60_000)
    const days = Math.floor(totalMinutes / 1_440)
    const hours = Math.floor((totalMinutes % 1_440) / 60)
    const minutes = totalMinutes % 60

    if (days > 0) return `${days} ${t('unit.dayShort')} ${hours} ${t('unit.hourShort')}`
    if (hours > 0) return `${hours}:${String(minutes).padStart(2, '0')} ${t('unit.hourShort')}`
    return `${minutes} ${t('unit.minuteShort')}`
  })

  const resetDate = computed(() =>
    target.value
      ? new Intl.DateTimeFormat(locale.value, {
          weekday: 'short',
          hour: '2-digit',
          minute: '2-digit',
        }).format(target.value)
      : undefined,
  )

  const isDue = computed(
    () => remainingMs.value !== undefined && remainingMs.value <= 0,
  )

  return { countdown, resetDate, isDue }
}
