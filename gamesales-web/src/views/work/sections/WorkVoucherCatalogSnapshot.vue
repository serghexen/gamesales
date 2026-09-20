<template>
  <div class="catalog-snapshot" :class="{ 'is-compact': compact }">
    <span class="catalog-snapshot__label muted">{{ kind === 'price' ? 'Закупочная цена' : 'Остаток, шт.' }}</span>
    <strong class="voucher-catalog__number">{{ value }}</strong>
    <template v-if="offer">
      <span v-if="!compact" class="catalog-snapshot__date muted">{{ updated }}</span>
      <span v-if="problem" class="catalog-snapshot__problem bad" :title="problemDetail">{{ problem }}</span>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ offer: { type: Object, default: null }, kind: { type: String, required: true }, compact: Boolean, now: { type: Number, required: true } })
const value = computed(() => {
  // Нулевые цена и остаток отличаются от отсутствующего снимка.
  if (props.kind === 'stock') return props.offer?.stock_count ?? '—'
  return props.offer?.price == null ? '—' : new Intl.NumberFormat('ru-RU', {
    style: 'currency', currency: props.offer.currency,
  }).format(Number(props.offer.price))
})
const updated = computed(() => date(props.offer?.[`${props.kind}_updated_at`]))
const problem = computed(() => {
  // Ошибки и устаревшие данные заметны даже в свёрнутой строке номинала.
  if (!props.offer) return ''
  const error = props.offer[`${props.kind}_error`]
  if (error) return error
  const timestamp = props.offer[`${props.kind}_updated_at`]
  const hours = props.kind === 'price' ? 26 : 2
  return timestamp && props.now - new Date(timestamp).getTime() > hours * 3600000
    ? props.kind === 'price' ? 'Цена требует обновления' : 'Остаток требует обновления' : ''
})
const problemDetail = computed(() => {
  // Полный текст и время последней проверки доступны при наведении на короткое сообщение.
  return props.offer?.[`${props.kind}_error`]
    ? `${problem.value} · Проверка ${date(props.offer[`${props.kind}_checked_at`])}` : problem.value
})

function date(value) {
  // Даты снимков показываем по Москве независимо от часового пояса браузера.
  return value ? new Intl.DateTimeFormat('ru-RU', { dateStyle: 'short', timeStyle: 'short', timeZone: 'Europe/Moscow' }).format(new Date(value)) : 'Ещё не получено'
}
</script>

<style scoped>
.catalog-snapshot { display: grid; align-content: start; justify-items: end; gap: 4px; min-width: 0; text-align: right; }
.voucher-catalog__number { font-size: 13px; font-weight: 600; font-variant-numeric: tabular-nums; white-space: nowrap; }
.catalog-snapshot__label, .catalog-snapshot__date, .catalog-snapshot__problem { font-size: 11px; line-height: 1.4; }
.catalog-snapshot:not(.is-compact) .catalog-snapshot__label { display: none; }
.catalog-snapshot__date { font-variant-numeric: tabular-nums; }
.catalog-snapshot__problem { max-width: 100%; overflow-wrap: anywhere; }
.is-compact .catalog-snapshot__problem { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
@media (max-width: 760px) { .catalog-snapshot:not(.is-compact) .catalog-snapshot__label { display: block; } }
</style>
