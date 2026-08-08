<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useMediaQuery, useNow } from '@vueuse/core'
import { useSettings } from '@/composables/useSettings'
import {
  ambientWeights,
  forcedMood,
  LOOPS_PER_CLIP,
  MASCOTS,
  pickClip,
  pickMood,
  remainingOfPrimary,
  severityOfPrimary,
} from '@/theme/mascot'
import type { Clip, Mood } from '@/theme/mascot'
import type { ProviderUsage } from '@/api/types'

const props = defineProps<{
  provider: ProviderUsage
  /** Das Frontend erreicht das eigene Backend nicht. */
  backendDown?: boolean
}>()

const { settings } = useSettings()

const reel = computed(() => MASCOTS[props.provider.id])
const available = computed(() => Object.keys(reel.value ?? {}) as Mood[])

/** Minutentakt genügt: Der Tagesrhythmus dreht sich an Stundengrenzen. */
const now = useNow({ interval: 60_000 })

/**
 * Ein GIF trägt seine Schleife in der Datei und lässt sich von außen nicht
 * anhalten. Wer weniger Bewegung will, bekommt deshalb gar keinen
 * Begleiter – ein eingefrorenes Standbild ist bei diesem Format nicht zu
 * haben.
 */
const reduceMotion = useMediaQuery('(prefers-reduced-motion: reduce)')

const forced = computed(() => forcedMood(props.provider, props.backendDown === true))

/**
 * Es bleibt absichtlich nur ein Medium im DOM. Zwei Ebenen für eine
 * Überblendung hielten pro Kachel zwei Videodecoder offen; zusammen mit der
 * zweiten Anbieter-Kachel konnte das besonders in WebViews einen der MP4s
 * anhalten. Der Zähler erzwingt trotzdem bei jeder Runde ein neues Element.
 */
interface Slot {
  clip: Clip
  token: number
}

const slot = ref<Slot>()
let token = 0

const current = ref<{ mood: Mood; clip: Clip }>()
let pending: { mood: Mood; clip: Clip; token: number } | undefined

let timer: number | undefined
let guard: number | undefined
let playbackGuard: number | undefined
let activeVideo: HTMLVideoElement | undefined

const clearTimer = () => {
  if (timer === undefined) return
  window.clearTimeout(timer)
  timer = undefined
}

const clearGuard = () => {
  if (guard === undefined) return
  window.clearTimeout(guard)
  guard = undefined
}

const clearPlaybackGuard = () => {
  if (playbackGuard === undefined) return
  window.clearTimeout(playbackGuard)
  playbackGuard = undefined
}

/**
 * Zwischen `show` und `onReady` hängt der Ablauf an einem einzigen Ereignis
 * des Browsers. Bleibt es aus – abgebrochener Ladevorgang, verschluckter
 * Fehler, eine Ebene, die gar nicht neu aufgebaut wurde –, liefe nichts
 * mehr an. Diese Reißleine würfelt dann einfach neu.
 */
const WATCHDOG_MS = 8_000
const PLAYBACK_STALL_MS = 5_000

const show = (mood: Mood, clip: Clip) => {
  clearTimer()
  clearGuard()
  clearPlaybackGuard()
  activeVideo?.pause()
  activeVideo = undefined

  token += 1
  pending = { mood, clip, token }
  slot.value = { clip, token }

  const requestedToken = token

  guard = window.setTimeout(() => {
    guard = undefined
    if (pending?.token !== requestedToken) return
    pending = undefined
    advance(forced.value)
  }, WATCHDOG_MS)
}

/** Würfelt die nächste Laune, oder bleibt bei der erzwungenen. */
const advance = (into?: Mood) => {
  const pools = reel.value
  if (!pools) return

  const mood =
    into ??
    pickMood(
      ambientWeights({
        hour: now.value.getHours(),
        nightMode: settings.value.nightMode,
        paused: !settings.value.autoRefresh,
        severity: severityOfPrimary(props.provider),
        remaining: remainingOfPrimary(props.provider),
        stale: props.provider.stale,
      }),
      available.value,
      current.value?.mood,
    )

  if (!mood) return

  const clip = pickClip(pools[mood] ?? [], current.value?.clip)
  if (clip) show(mood, clip)
}

/**
 * Der Wechsel hängt bewusst an der bekannten Laufzeit und nicht am
 * `ended`-Ereignis des Browsers. Das kann bei MP4s ausbleiben und würde den
 * Ablauf sonst dauerhaft anhalten. Die MP4 selbst schleift der Browser.
 */
const beginDwell = () => {
  const clip = current.value?.clip
  if (!clip) return

  timer = window.setTimeout(
    () => {
      timer = undefined
      advance(forced.value)
    },
    LOOPS_PER_CLIP * clip.seconds * 1000,
  )
}

const armPlaybackGuard = (slotToken: number, video: HTMLVideoElement) => {
  clearPlaybackGuard()
  playbackGuard = window.setTimeout(() => {
    playbackGuard = undefined
    if (slot.value?.token !== slotToken || video !== activeVideo) return

    // Browser halten Medien in Hintergrund-Tabs absichtlich an. Dort nicht
    // unnötig neu laden; nach dem Sichtbarwerden kommen wieder timeupdates.
    if (document.hidden) {
      armPlaybackGuard(slotToken, video)
      return
    }

    advance(forced.value)
  }, PLAYBACK_STALL_MS)
}

/** Das neue Medium ist geladen und übernimmt seine Runde. */
const onReady = (slotToken: number, event: Event) => {
  if (slot.value?.token !== slotToken || pending?.token !== slotToken) return

  clearGuard()
  clearPlaybackGuard()
  current.value = { mood: pending.mood, clip: pending.clip }
  pending = undefined

  const element = event.currentTarget
  activeVideo = element instanceof HTMLVideoElement ? element : undefined
  if (activeVideo) {
    armPlaybackGuard(slotToken, activeVideo)
    // `autoplay` reicht normalerweise. Der explizite Aufruf fängt auch
    // Browser ab, die erst nach `canplay` zuverlässig starten.
    void activeVideo.play().catch(() => undefined)
  }

  beginDwell()
}

/** Jeder echte Fortschritt verlängert die Reißleine für den sichtbaren MP4. */
const onProgress = (slotToken: number, event: Event) => {
  const element = event.currentTarget
  if (
    slot.value?.token !== slotToken ||
    !(element instanceof HTMLVideoElement) ||
    element !== activeVideo
  ) {
    return
  }

  armPlaybackGuard(slotToken, element)
}

/**
 * Lädt eine Ebene nicht, käme nie ein `onReady` und der Begleiter bliebe
 * für immer auf dem alten Bild stehen. Lieber die nächste Laune versuchen.
 */
const onFailed = (slotToken: number) => {
  if (slot.value?.token !== slotToken) return

  clearGuard()
  clearPlaybackGuard()
  activeVideo?.pause()
  activeVideo = undefined
  pending = undefined
  slot.value = undefined
  clearTimer()
  timer = window.setTimeout(() => advance(forced.value), 2_000)
}

/** Eine Störung kommt oder geht: sofort umschalten, ohne die Runde abzuwarten. */
watch(forced, (value) => advance(value))

onMounted(() => {
  if (!reduceMotion.value) advance(forced.value)
})

onBeforeUnmount(() => {
  clearTimer()
  clearGuard()
  clearPlaybackGuard()
  activeVideo?.pause()
})
</script>

<template>
  <div v-if="reel && !reduceMotion" class="mascot">
    <!-- Rein schmückend: Was der Clip andeutet, steht als Abzeichen, Hinweis
         und Zustandswort ohnehin im Text der Kachel. -->
    <div class="layer">
      <video
        v-if="slot?.clip.kind === 'video'"
        :key="slot.token"
        :src="slot.clip.src"
        class="art blend"
        autoplay
        loop
        muted
        playsinline
        preload="auto"
        disablepictureinpicture
        aria-hidden="true"
        @canplay="onReady(slot.token, $event)"
        @timeupdate="onProgress(slot.token, $event)"
        @error="onFailed(slot.token)"
      />
      <img
        v-else-if="slot"
        :key="slot.token"
        :src="slot.clip.src"
        class="art"
        alt=""
        aria-hidden="true"
        @load="onReady(slot.token, $event)"
        @error="onFailed(slot.token)"
      />
    </div>
  </div>
</template>

<style scoped>
/*
 * Starre Kantenlänge neben der Meterspalte. Die Ebenen liegen absolut
 * darin, damit weder Ladezustand noch Eigenmaße eines Clips die Zeilenhöhe
 * beeinflussen können.
 */
.mascot {
  position: relative;
  width: 5.5rem;
  height: 5.5rem;
  flex: none;
}

.layer {
  position: absolute;
  inset: 0;
}

.art {
  width: 100%;
  height: 100%;
  object-fit: contain;
  /* Pixelkunst: Beim Skalieren dürfen die Kanten nicht verwaschen. */
  image-rendering: pixelated;
  pointer-events: none;
}

/* Nur die MP4s liegen auf schwarzer Fläche. `screen` rechnet reines Schwarz
   gegen die Kachel weg. Die GIFs sind transparent - dort würde dieselbe
   Rechnung die dunklen Pixel der Figur ausbleichen. */
.art.blend {
  mix-blend-mode: screen;
}
</style>
