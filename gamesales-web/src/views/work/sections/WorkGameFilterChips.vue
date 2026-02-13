<template>
  <div v-if="activeProductChips.length" class="chip-row">
    <button class="chip chip--reset" type="button" @click="resetProductFilter('all')">
      Сбросить все
    </button>
    <span v-for="chip in activeProductChips" :key="chip.key" class="chip">
      <span class="chip__label">{{ chip.label }}:</span>
      <span class="chip__value">{{ chip.value }}</span>
      <button
        class="chip__clear"
        type="button"
        aria-label="Сбросить фильтр"
        title="Сбросить фильтр"
        @click="resetProductFilter(chip.key)"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M6 6l12 12M18 6l-12 12" />
        </svg>
      </button>
    </span>
  </div>
</template>

<script setup>
defineProps({
  activeProductChips: { type: Array, required: true },
  resetProductFilter: { type: Function, required: true },
})
</script>
