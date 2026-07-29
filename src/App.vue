<script setup lang="ts">
import { computed, ref } from 'vue'
import { useEventListener } from '@vueuse/core'
import DashboardHeader from '@/components/DashboardHeader.vue'
import { useAIUsage } from '@/composables/useAIUsage'
import { useSettings } from '@/composables/useSettings'
import { useUsageRefresh } from '@/composables/useUsageRefresh'
import DashboardView from '@/views/DashboardView.vue'
import SettingsView from '@/views/SettingsView.vue'

const settingsOpen = ref(window.location.hash === '#settings')
const { settings } = useSettings()
const {
  visibleServices,
  loading,
  refreshError,
  isOnline,
  refresh,
} = useAIUsage(settings)

const autoRefresh = computed(() => settings.value.autoRefresh)
const refreshInterval = computed(() => settings.value.refreshIntervalSeconds)

const { isAutoRefreshActive } = useUsageRefresh({
  autoRefresh,
  intervalSeconds: refreshInterval,
  refresh,
})

const toggleSettings = () => {
  settingsOpen.value = !settingsOpen.value
  window.history.replaceState(
    null,
    '',
    settingsOpen.value
      ? `${window.location.pathname}${window.location.search}#settings`
      : `${window.location.pathname}${window.location.search}`,
  )
  if (!settingsOpen.value) void refresh()
}

useEventListener(window, 'hashchange', () => {
  settingsOpen.value = window.location.hash === '#settings'
})
</script>

<template>
  <div class="min-h-screen">
    <div class="mx-auto w-full max-w-[1120px] px-4 py-5 sm:px-6 sm:py-7 lg:px-8">
      <DashboardHeader
        :online="isOnline"
        :loading="loading"
        :settings-open="settingsOpen"
        @refresh="refresh"
        @toggle-settings="toggleSettings"
      />

      <Transition
        mode="out-in"
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="translate-y-1 opacity-0"
        enter-to-class="translate-y-0 opacity-100"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="translate-y-0 opacity-100"
        leave-to-class="-translate-y-1 opacity-0"
      >
        <SettingsView v-if="settingsOpen" @changed="refresh" />
        <DashboardView
          v-else
          :services="visibleServices"
          :compact="settings.compactView"
          :loading="loading"
          :refresh-error="refreshError"
          :auto-refresh-active="isAutoRefreshActive"
        />
      </Transition>
    </div>
  </div>
</template>
