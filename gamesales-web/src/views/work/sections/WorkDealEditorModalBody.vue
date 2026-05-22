<template>
  <!-- Общая обертка тела модалки сделки с оверлеями загрузки -->
  <div class="modal__body" :class="{ 'modal__body--locked': isLocked }">
    <div v-if="isLoading" class="modal__body-overlay">
      <div class="loader-wrap loader-wrap--compact">
        <div aria-label="Orange and tan hamster running in a metal wheel" role="img" class="wheel-and-hamster wheel-and-hamster--mini">
          <div class="wheel"></div>
          <div class="hamster">
            <div class="hamster__body">
              <div class="hamster__head">
                <div class="hamster__ear"></div>
                <div class="hamster__eye"></div>
                <div class="hamster__nose"></div>
              </div>
              <div class="hamster__limb hamster__limb--fr"></div>
              <div class="hamster__limb hamster__limb--fl"></div>
              <div class="hamster__limb hamster__limb--br"></div>
              <div class="hamster__limb hamster__limb--bl"></div>
              <div class="hamster__tail"></div>
            </div>
          </div>
          <div class="spoke"></div>
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
