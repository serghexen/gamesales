<template>
  <!-- Общая обертка тела модалки сделки с оверлеями загрузки -->
  <div class="modal__body" :class="{ 'modal__body--locked': isLocked }">
    <div v-if="isLoading" class="modal__body-overlay">
      <div class="loader-wrap loader-wrap--compact">
        <div class="newtons-cradle" aria-label="Loading" role="img">
          <div class="newtons-cradle__dot"></div>
          <div class="newtons-cradle__dot"></div>
          <div class="newtons-cradle__dot"></div>
          <div class="newtons-cradle__dot"></div>
        </div>
        <p class="muted">Загрузка…</p>
      </div>
    </div>

    <div v-else-if="isQuickBusy" class="modal__body-overlay">
      <div class="modal__body-overlay-content">
        <span class="spinner"></span>
        <span class="muted">{{ quickBusyLabel }}</span>
      </div>
    </div>

    <slot />
  </div>
</template>

<script setup>
import { reactive, toRefs } from 'vue'

const props = defineProps({
  ctx: { type: Object, required: true },
})
const ctx = reactive(props.ctx)

const {
  isLocked,
  isLoading,
  isQuickBusy,
  quickBusyLabel,
} = toRefs(ctx)
</script>
