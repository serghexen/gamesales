<template>
  <section class="hero">
    <div>
      <h1 class="hero__title">Операции в реальном времени</h1>
      <p class="hero__text">
        Контролируй слоты, выдачи и платежи, а система сама покажет статус
        API и свежие данные по аккаунтам.
      </p>
    </div>
    <div class="hero__cards">
      <div class="mini">
        <div class="mini__label">API</div>
        <div class="mini__value" :class="{ bad: ctx.apiOk === false }">
          <span v-if="ctx.apiOk === null">не проверяли</span>
          <span v-else-if="ctx.apiOk">OK</span>
          <span v-else>ошибка</span>
        </div>
      </div>
      <div class="mini">
        <div class="mini__label">Запросы</div>
        <div class="mini__value">{{ ctx.loading ? '...' : '200/мин' }}</div>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  ctx: { type: Object, required: true },
})
</script>
