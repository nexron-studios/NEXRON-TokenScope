<script setup lang="ts">
import { computed } from 'vue'
import ProviderCard from '@/components/ProviderCard.vue'
import UsageHistoryChart from '@/components/UsageHistoryChart.vue'
import type { HistoryResponse, ProviderUsage } from '@/api/types'

const props = defineProps<{
  providers: ProviderUsage[]
  history?: HistoryResponse
  historyHours: number
  backendError?: string
  largeText: boolean
}>()

const visibleIds = computed(() => props.providers.map((provider) => provider.id))
</script>

<template>
  <main class="view">
    <p v-if="backendError" class="alert" role="alert">{{ backendError }}</p>

    <div v-if="providers.length" class="cards">
      <ProviderCard
        v-for="provider in providers"
        :key="provider.id"
        :provider="provider"
        :large="largeText"
      />
    </div>

    <p v-else class="alert muted">
      Kein Anbieter aktiv. In den Einstellungen wieder einschalten.
    </p>

    <UsageHistoryChart
      :history="history"
      :hours="historyHours"
      :visible-providers="visibleIds"
    />
  </main>
</template>

<style scoped>
.view {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 0.75rem;
  flex: 1;
  min-height: 0;
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(19rem, 1fr));
  gap: 0.75rem;
  min-height: 0;
}

.alert {
  border: 1px solid rgb(208 59 59 / 30%);
  border-radius: 0.9rem;
  background: rgb(208 59 59 / 10%);
  color: #f0a5a5;
  font-size: 0.8125rem;
  padding: 0.7rem 0.95rem;
}

.alert.muted {
  display: grid;
  place-items: center;
  border-color: rgb(255 255 255 / 8%);
  background: rgb(255 255 255 / 2%);
  color: #82828b;
}
</style>
