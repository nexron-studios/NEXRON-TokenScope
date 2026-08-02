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
  REPLAY_DELAY_MS,
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
 * Zwei Ebenen, die überblenden: Die neue lädt unsichtbar, erst wenn sie
 * bereit ist, wird umgeschaltet. Alle Clips gleichzeitig im DOM zu halten
 * wäre der einfachere Weg, aber ein verstecktes GIF animiert weiter – bei
 * gut zwanzig Clips je Anbieter hätte das den Kiosk beschäftigt.
 */
const layers = ref<Array<Clip | undefined>>([undefined, undefined])
const front = ref(0)

const current = ref<{ mood: Mood; clip: Clip }>()
let pending: { mood: Mood; clip: Clip } | undefined

const videos = new Map<number, HTMLVideoElement>()
const registerVideo = (index: number, element: HTMLVideoElement | null) => {
  if (element) videos.set(index, element)
  else videos.delete(index)
}

let played = 0
let timer: number | undefined

const clearTimer = () => {
  if (timer === undefined) return
  window.clearTimeout(timer)
  timer = undefined
}

const show = (mood: Mood, clip: Clip) => {
  clearTimer()
  pending = { mood, clip }
  layers.value[1 - front.value] = clip
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
 * Ein GIF meldet kein Ende, also wird seine Standzeit aus der bekannten
 * Laufzeit gerechnet. MP4s treibt stattdessen ihr `ended`-Ereignis weiter –
 * nur dort ist die Ruhe zwischen den Durchläufen überhaupt möglich.
 */
const beginDwell = () => {
  const clip = current.value?.clip
  if (!clip || clip.kind !== 'gif') return

  timer = window.setTimeout(
    () => advance(forced.value),
    LOOPS_PER_CLIP * clip.seconds * 1000,
  )
}

/** Die neue Ebene ist geladen – jetzt erst wird sie sichtbar. */
const onReady = (index: number) => {
  if (index === front.value || !pending) return

  front.value = index
  current.value = pending
  pending = undefined
  played = 0

  beginDwell()
}

/**
 * Lädt eine Ebene nicht, käme nie ein `onReady` und der Begleiter bliebe
 * für immer auf dem alten Bild stehen. Lieber die nächste Laune versuchen.
 */
const onFailed = (index: number) => {
  if (index === front.value) return
  pending = undefined
  layers.value[index] = undefined
  clearTimer()
  timer = window.setTimeout(() => advance(forced.value), 2_000)
}

const onEnded = (index: number) => {
  // Verspätete Ereignisse der abgelösten Ebene zählen nicht mit.
  if (index !== front.value) return

  played += 1

  if (played >= LOOPS_PER_CLIP) {
    advance(forced.value)
    return
  }

  clearTimer()
  timer = window.setTimeout(() => {
    timer = undefined
    const video = videos.get(index)
    if (!video) return
    video.currentTime = 0
    void video.play().catch(() => undefined)
  }, REPLAY_DELAY_MS)
}

/** Eine Störung kommt oder geht: sofort umschalten, ohne die Runde abzuwarten. */
watch(forced, (value) => advance(value))

onMounted(() => {
  if (!reduceMotion.value) advance(forced.value)
})

onBeforeUnmount(clearTimer)
</script>

<template>
  <div v-if="reel && !reduceMotion" class="mascot">
    <!-- Rein schmückend: Was der Clip andeutet, steht als Abzeichen, Hinweis
         und Zustandswort ohnehin im Text der Kachel. -->
    <div
      v-for="(clip, index) in layers"
      :key="index"
      class="layer"
      :class="{ on: index === front }"
    >
      <video
        v-if="clip?.kind === 'video'"
        :key="clip.src"
        :ref="(el) => registerVideo(index, el as HTMLVideoElement | null)"
        :src="clip.src"
        class="art blend"
        autoplay
        muted
        playsinline
        preload="auto"
        disablepictureinpicture
        aria-hidden="true"
        @canplay="onReady(index)"
        @ended="onEnded(index)"
        @error="onFailed(index)"
      />
      <img
        v-else-if="clip"
        :key="clip.src"
        :src="clip.src"
        class="art"
        alt=""
        aria-hidden="true"
        @load="onReady(index)"
        @error="onFailed(index)"
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
  opacity: 0;
  transition: opacity 220ms ease;
}

.layer.on {
  opacity: 1;
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
