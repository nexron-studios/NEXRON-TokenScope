<script setup lang="ts">
import { ref } from 'vue'
import { useSettings } from '@/composables/useSettings'
import type { ServiceId } from '@/services/usage.types'

const emit = defineEmits<{
  changed: []
}>()

const { settings, resetSettings, importUsage } = useSettings()
const importInput = ref<HTMLInputElement>()
const importMessage = ref<{ tone: 'success' | 'error'; text: string }>()
const resetPending = ref(false)

const services: Array<{ id: ServiceId; name: string; accent: string }> = [
  { id: 'chatgpt', name: 'ChatGPT', accent: 'bg-emerald-400' },
  { id: 'claude', name: 'Claude', accent: 'bg-violet-400' },
]

const handleImport = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  try {
    const parsed = JSON.parse(await file.text()) as unknown
    const count = importUsage(parsed as Parameters<typeof importUsage>[0])
    importMessage.value = {
      tone: 'success',
      text: `${count} Dienst${count === 1 ? '' : 'e'} lokal importiert. Mock-Daten wurden deaktiviert.`,
    }
    emit('changed')
  } catch (error) {
    importMessage.value = {
      tone: 'error',
      text:
        error instanceof Error
          ? error.message
          : 'Die JSON-Datei konnte nicht gelesen werden.',
    }
  } finally {
    input.value = ''
  }
}

const handleReset = () => {
  if (!resetPending.value) {
    resetPending.value = true
    return
  }

  resetSettings()
  resetPending.value = false
  importMessage.value = {
    tone: 'success',
    text: 'Alle lokalen Einstellungen und manuellen Werte wurden zurückgesetzt.',
  }
  emit('changed')
}
</script>

<template>
  <main class="mt-7">
    <div class="mb-5">
      <p class="label">Lokal gespeichert</p>
      <h2 class="mt-1 text-xl font-semibold tracking-tight">Einstellungen</h2>
      <p class="mt-1 max-w-2xl text-xs leading-5 text-slate-500">
        Alle Werte bleiben im Local Storage dieses Browsers. Es werden keine Zugangsdaten gespeichert.
      </p>
    </div>

    <div class="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
      <section class="surface rounded-2xl p-5">
        <h3 class="text-sm font-semibold">Dashboard</h3>

        <div class="mt-5 space-y-5">
          <label class="flex cursor-pointer items-center justify-between gap-4">
            <span>
              <span class="block text-xs font-medium text-slate-200">Automatisch aktualisieren</span>
              <span class="mt-0.5 block text-[11px] text-slate-500">Im Hintergrund bei sichtbarem Fenster</span>
            </span>
            <input v-model="settings.autoRefresh" type="checkbox" class="peer sr-only" />
            <span class="relative h-6 w-11 shrink-0 rounded-full bg-white/10 transition peer-checked:bg-mint-400/70 after:absolute after:left-1 after:top-1 after:size-4 after:rounded-full after:bg-white after:transition-transform peer-checked:after:translate-x-5" />
          </label>

          <label class="block">
            <span class="label">Intervall</span>
            <select
              v-model.number="settings.refreshIntervalSeconds"
              class="field mt-2"
              :disabled="!settings.autoRefresh"
            >
              <option :value="30">30 Sekunden</option>
              <option :value="60">1 Minute</option>
              <option :value="300">5 Minuten</option>
              <option :value="900">15 Minuten</option>
            </select>
          </label>

          <label class="flex cursor-pointer items-center justify-between gap-4">
            <span>
              <span class="block text-xs font-medium text-slate-200">Mock-Daten</span>
              <span class="mt-0.5 block text-[11px] text-slate-500">Eindeutig als Demo gekennzeichnet</span>
            </span>
            <input v-model="settings.mockEnabled" type="checkbox" class="peer sr-only" />
            <span class="relative h-6 w-11 shrink-0 rounded-full bg-white/10 transition peer-checked:bg-violet-400/70 after:absolute after:left-1 after:top-1 after:size-4 after:rounded-full after:bg-white after:transition-transform peer-checked:after:translate-x-5" />
          </label>

          <label class="flex cursor-pointer items-center justify-between gap-4">
            <span>
              <span class="block text-xs font-medium text-slate-200">Kompakte Ansicht</span>
              <span class="mt-0.5 block text-[11px] text-slate-500">Reduzierte Abstände in den Karten</span>
            </span>
            <input v-model="settings.compactView" type="checkbox" class="peer sr-only" />
            <span class="relative h-6 w-11 shrink-0 rounded-full bg-white/10 transition peer-checked:bg-mint-400/70 after:absolute after:left-1 after:top-1 after:size-4 after:rounded-full after:bg-white after:transition-transform peer-checked:after:translate-x-5" />
          </label>

          <div>
            <p class="label">Angezeigte Dienste</p>
            <div class="mt-3 flex gap-2">
              <label
                v-for="service in services"
                :key="service.id"
                class="flex flex-1 cursor-pointer items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.025] px-3 py-2.5 text-xs text-slate-300"
              >
                <input
                  v-model="settings.enabledServices[service.id]"
                  type="checkbox"
                  class="size-3.5 accent-emerald-400"
                />
                <span class="size-1.5 rounded-full" :class="service.accent" />
                {{ service.name }}
              </label>
            </div>
          </div>
        </div>
      </section>

      <section class="surface rounded-2xl p-5">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h3 class="text-sm font-semibold">Manuelle Nutzungswerte</h3>
            <p class="mt-1 text-[11px] leading-4 text-slate-500">
              Sichtbar, sobald Mock-Daten deaktiviert sind.
            </p>
          </div>
          <button
            type="button"
            class="shrink-0 rounded-lg border border-white/10 bg-white/[0.035] px-3 py-2 text-[11px] font-medium text-slate-300 transition hover:bg-white/[0.07]"
            @click="importInput?.click()"
          >
            JSON importieren
          </button>
          <input
            ref="importInput"
            type="file"
            accept="application/json,.json"
            class="hidden"
            @change="handleImport"
          />
        </div>

        <div class="mt-5 grid gap-5 sm:grid-cols-2">
          <fieldset
            v-for="service in services"
            :key="service.id"
            class="rounded-xl border border-white/[0.07] bg-black/10 p-4"
          >
            <legend class="px-1 text-xs font-semibold text-slate-200">
              <span class="mr-2 inline-block size-1.5 rounded-full align-middle" :class="service.accent" />
              {{ service.name }}
            </legend>

            <div class="mt-2 space-y-3">
              <label class="block">
                <span class="label">Tarif</span>
                <input
                  v-model.trim="settings.manualValues[service.id].plan"
                  class="field mt-1.5"
                  type="text"
                  placeholder="z. B. Plus"
                />
              </label>

              <label class="block">
                <span class="label">Verfügbar in %</span>
                <input
                  v-model.number="settings.manualValues[service.id].remainingPercentage"
                  class="field mt-1.5"
                  type="number"
                  inputmode="decimal"
                  min="0"
                  max="100"
                  placeholder="0–100"
                />
              </label>

              <label class="block">
                <span class="label">Nächster Reset</span>
                <input
                  v-model="settings.manualValues[service.id].resetAt"
                  class="field mt-1.5 text-xs"
                  type="datetime-local"
                />
              </label>

              <label class="block">
                <span class="label">Zusatztext</span>
                <input
                  v-model.trim="settings.manualValues[service.id].usageText"
                  class="field mt-1.5"
                  type="text"
                  placeholder="optional"
                />
              </label>
            </div>
          </fieldset>
        </div>
      </section>
    </div>

    <div
      v-if="importMessage"
      class="mt-4 rounded-xl border px-4 py-3 text-xs"
      :class="
        importMessage.tone === 'success'
          ? 'border-emerald-400/15 bg-emerald-400/[0.07] text-emerald-200'
          : 'border-rose-400/15 bg-rose-400/[0.07] text-rose-200'
      "
      role="status"
    >
      {{ importMessage.text }}
    </div>

    <div class="mt-4 flex items-center justify-between gap-4 rounded-xl border border-white/[0.06] px-4 py-3">
      <p class="text-[11px] text-slate-600">
        Reset entfernt nur die unter <code class="text-slate-500">ai-usage-monitor:settings</code> gespeicherten Daten.
      </p>
      <button
        type="button"
        class="shrink-0 rounded-lg border px-3 py-2 text-[11px] font-medium transition"
        :class="
          resetPending
            ? 'border-rose-400/30 bg-rose-400/10 text-rose-200'
            : 'border-white/10 text-slate-400 hover:border-rose-400/20 hover:text-rose-300'
        "
        @click="handleReset"
        @blur="resetPending = false"
      >
        {{ resetPending ? 'Wirklich zurücksetzen?' : 'Lokale Daten zurücksetzen' }}
      </button>
    </div>
  </main>
</template>
