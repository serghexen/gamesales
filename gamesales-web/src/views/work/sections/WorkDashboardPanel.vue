<template>
  <section class="panel panel--wide">
    <div class="panel__body">
      <div class="status">
        <div class="dot" :class="{ ok: ctx.apiOk, bad: ctx.apiOk === false }"></div>
        <span>
          <span v-if="ctx.apiOk === null">не проверяли</span>
          <span v-else-if="ctx.apiOk">OK</span>
          <span v-else>ошибка</span>
        </span>
      </div>
      <button class="btn" :disabled="ctx.loading" @click="ctx.checkApi">
        {{ ctx.loading ? 'Проверяем…' : 'Проверить API' }}
      </button>
    </div>
  </section>
</template>

<script setup>
defineProps({
  ctx: { type: Object, required: true },
})
</script>
