<template>
  <section class="panel panel--wide">
    <div class="panel__body">
      <div class="toolbar-actions">
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
        <button class="btn" :disabled="ctx.managersLoadLoading" @click="ctx.refreshManagersWorkload">
          {{ ctx.managersLoadLoading ? 'Обновляем…' : 'Обновить менеджеров' }}
        </button>
      </div>

      <div class="panel panel--soft">
        <div class="panel__head panel__head--tight">
          <h3>Менеджеры в работе</h3>
          <div class="muted">Онлайн: {{ ctx.managersLoadOnlineCount || 0 }}</div>
        </div>
        <div class="panel__body">
          <p class="muted">Актуально на {{ ctx.managersLoadDate || 'сегодня' }} ({{ ctx.managersLoadTimezone || 'Europe/Moscow' }})</p>
          <p v-if="ctx.managersLoadError" class="bad">{{ ctx.managersLoadError }}</p>
          <p v-else-if="ctx.managersLoadLoading" class="muted">Обновляем список менеджеров…</p>
          <p v-else-if="!ctx.managersLoadItems.length" class="muted">Сейчас нет менеджеров онлайн.</p>
          <table v-else class="table table--compact table--dense">
            <thead>
              <tr>
                <th>Менеджер (имя)</th>
                <th>В работе</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in ctx.managersLoadItems" :key="item.username">
                <td>{{ item.username }}<span v-if="item.name"> ({{ item.name }})</span></td>
                <td>{{ Number(item.pending_count || 0) }} заявок</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  ctx: { type: Object, required: true },
})
</script>
