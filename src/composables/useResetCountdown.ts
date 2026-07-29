import { computed, toValue } from 'vue'
import { useNow } from '@vueuse/core'
import type { MaybeRefOrGetter } from 'vue'

export function useResetCountdown(resetAt: MaybeRefOrGetter<string | undefined>) {
  const now = useNow({ interval: 1_000 })

  const countdown = computed(() => {
    const value = toValue(resetAt)
    if (!value) return 'Kein Reset hinterlegt'

    const target = new Date(value).getTime()
    if (!Number.isFinite(target)) return 'Reset-Zeit ungültig'

    const difference = target - now.value.getTime()
    if (difference <= 0) return 'Reset fällig'

    const totalMinutes = Math.ceil(difference / 60_000)
    const days = Math.floor(totalMinutes / 1_440)
    const hours = Math.floor((totalMinutes % 1_440) / 60)
    const minutes = totalMinutes % 60

    if (days > 0) return `Reset in ${days} T ${hours} Std.`
    if (hours > 0) return `Reset in ${hours} Std. ${minutes} Min.`
    return `Reset in ${minutes} Min.`
  })

  const resetDate = computed(() => {
    const value = toValue(resetAt)
    if (!value) return undefined

    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return undefined

    return new Intl.DateTimeFormat('de-DE', {
      weekday: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  })

  return { countdown, resetDate }
}
