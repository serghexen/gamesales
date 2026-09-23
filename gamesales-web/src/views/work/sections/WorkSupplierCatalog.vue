<template>
  <details class="supplier-current">
    <summary><span>Список ваучеров</span><span class="supplier-current__count">{{ rows.length }}</span><span v-if="newCount" class="supplier-current__badge">Новых: {{ newCount }}</span></summary>
    <div class="supplier-current__body">
      <div class="supplier-current__toolbar">
        <input v-model="search" class="input" type="search" placeholder="Услуга, номинал или ID" aria-label="Поиск сохранённых ваучеров">
        <div class="supplier-current__filters" aria-label="Фильтры позиций">
          <button v-for="choice in filters" :key="choice.key" type="button" :aria-pressed="filter === choice.key" @click="filter = choice.key">{{ choice.label }}</button>
        </div>
        <button type="button" class="account-refresh-btn" :disabled="loading" aria-label="Перечитать сохранённые позиции" @click="load"><span class="account-refresh-btn__content">↻</span></button>
      </div>
      <div class="supplier-current__meta">
        <span class="muted">{{ filtered.length }} позиций<span v-if="sync?.discovery_at"> · каталог обновлён {{ date(sync.discovery_at) }}</span></span>
        <button v-if="canReview && pendingPage.length" class="ghost" type="button" :disabled="saving" @click="review(pendingPage)">Отметить страницу просмотренной</button>
      </div>
      <p v-if="error || sync?.error" class="error" role="alert">{{ error || sync?.error }}</p>
      <div ref="tableViewport" class="supplier-current__table supplier-table-wrap" tabindex="0" role="region" aria-label="Список ваучеров">
        <table class="table table--compact table--supplier">
          <thead><tr><th>Услуга / номинал</th><th>Состояние</th><th class="numeric">Цена, ₽</th><th class="numeric">Свободно</th><th v-if="showReviewActions">Действия</th></tr></thead>
          <tbody>
            <tr v-if="!pageRows.length"><td :colspan="showReviewActions ? 5 : 4" class="muted">{{ loading ? 'Загрузка…' : 'Нет позиций по выбранному фильтру' }}</td></tr>
            <tr v-for="row in pageRows" :key="`${row.service_id}:${row.nominal_id}`">
              <td class="supplier-current__identity"><strong>{{ row.service_title }}</strong><div class="supplier-current__nominal"><span>{{ row.nominal_title }}</span><span class="supplier-current__ids muted">#{{ row.service_id }} / {{ row.nominal_id }}</span></div></td>
              <td class="supplier-current__state">
                <span class="supplier-current__status" :class="{ 'is-warning': row.status !== 'active' }">{{ status(row.status) }}</span>
                <small v-if="row.availability_note" class="supplier-current__reason">{{ row.availability_note }}</small>
                <small v-if="row.status !== 'active' && row.missing_count > 0 && row.last_seen_at" class="muted">Последний раз видели: {{ date(row.last_seen_at) }}</small>
                <small class="muted">{{ row.linked ? 'Связан с каталогом' : 'Не связан' }}</small>
                <small v-if="!row.reviewed_at" class="supplier-current__new">{{ row.review_reason === 'new' ? 'Новое' : 'Есть изменения' }}</small>
                <div v-if="row.change_notes.length" class="supplier-current__changes">
                  <small v-for="note in row.change_notes" :key="note">{{ note }}</small>
                  <small v-if="row.changes_detected_at" class="muted">Обнаружено: {{ date(row.changes_detected_at) }}</small>
                </div>
              </td>
              <td class="numeric"><strong>{{ money(row.price) }}</strong><small class="muted">{{ date(row.price_updated_at) }}</small><small v-if="row.price_error" class="error" :title="row.price_error">Ошибка обновления</small></td>
              <td class="numeric"><strong>{{ row.stock_count ?? '—' }}</strong><small class="muted">{{ date(row.stock_updated_at) }}</small><small v-if="row.stock_error" class="error" :title="row.stock_error">Ошибка обновления</small></td>
              <td v-if="showReviewActions"><button v-if="!row.reviewed_at" type="button" class="ghost" :disabled="saving" @click="review([row])">Просмотрено</button></td>
            </tr>
          </tbody>
        </table>
      </div>
      <nav v-if="pages > 1" class="supplier-current__pagination" aria-label="Страницы сохранённых позиций">
        <button class="ghost" type="button" :disabled="page <= 1" @click="page--">Назад</button><span>{{ page }} / {{ pages }}</span><button class="ghost" type="button" :disabled="page >= pages" @click="page++">Далее</button>
      </nav>
    </div>
  </details>
</template>
<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { apiGet, apiPost } from '../../../api/http'
const props = defineProps({ token: { type: String, default: '' }, canReview: Boolean, refreshState: { type: String, default: '' } })
const rows = ref([]), sync = ref(null), loading = ref(false), saving = ref(false), error = ref('')
const search = ref(''), filter = ref('all'), page = ref(1)
const tableViewport = ref(null)
const filters = [{ key: 'all', label: 'Все' }, { key: 'new', label: 'Новые' }, { key: 'changed', label: 'Изменения' }, { key: 'unlinked', label: 'Не связаны' }, { key: 'unavailable', label: 'Недоступны' }]
const newCount = computed(() => rows.value.filter(row => !row.reviewed_at && row.review_reason === 'new').length)
const filtered = computed(() => {
  // Просмотр и связь независимы: отметка не скрывает несвязанный номинал из его фильтра.
  const query = search.value.trim().toLowerCase()
  return rows.value.filter(row => (!query || `${row.service_title} ${row.nominal_title} ${row.service_id} ${row.nominal_id}`.toLowerCase().includes(query)) &&
    (filter.value === 'all' || filter.value === 'new' && !row.reviewed_at && row.review_reason === 'new' ||
      filter.value === 'changed' && !row.reviewed_at && row.review_reason !== 'new' ||
      filter.value === 'unlinked' && !row.linked || filter.value === 'unavailable' && row.status !== 'active'))
})
const pages = computed(() => Math.max(1, Math.ceil(filtered.value.length / 25)))
const pageRows = computed(() => filtered.value.slice((page.value - 1) * 25, page.value * 25)
  .map(row => ({ ...row, change_notes: changeNotes(row), availability_note: availabilityNote(row) })))
const pendingPage = computed(() => pageRows.value.filter(row => !row.reviewed_at))
const showReviewActions = computed(() => props.canReview && pendingPage.value.length > 0)
watch([search, filter], () => { page.value = 1 })
watch(pages, count => { page.value = Math.min(page.value, count) })
watch([page, search, filter], async () => {
  // Новая страница или фильтр открываются с первой строки внутри списка.
  await nextTick()
  if (tableViewport.value) tableViewport.value.scrollTop = 0
})
watch(() => props.refreshState, state => { if (state === 'completed') load() })
function date(value) {
  // Даты одного снимка одинаково отображаются независимо от часового пояса браузера.
  return value ? new Date(value).toLocaleString('ru-RU', { timeZone: 'Europe/Moscow', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'
}
function money(value) {
  // Неизвестная цена не выглядит нулевой или бесплатной.
  return value == null ? '—' : Number(value).toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function status(value) {
  // Подозрительное исчезновение показываем до окончательного подтверждения вторым обходом.
  return { active: 'Доступен', suspect: 'Требует проверки', unavailable: 'Недоступен' }[value] || value
}
function availabilityNote(row) {
  // Причина доступности остаётся видимой и после отметки «Просмотрено»; остаток на неё не влияет.
  if (row.status === 'active') return ''
  if (row.missing_count > 0 || row.availability_reason === 'missing' || row.status === 'suspect') {
    return row.status === 'suspect'
      ? 'Не найден в каталоге. Ждём повторной проверки.'
      : `Не найден в каталоге.${row.missing_count > 0 ? ` Проверок подряд: ${row.missing_count}.` : ''}`
  }
  return `${availabilityReasonName(row.availability_reason)}.`
}
function availabilityReasonName(reason) {
  // Одинаковые формулировки связывают текущую причину с её прежним значением.
  return { missing: 'Не найден в каталоге', service_disabled: 'Поставщик отключил услугу', nominal_disabled: 'Поставщик отключил номинал' }[reason]
    || 'Позиция отключена поставщиком'
}
function changeNotes(row) {
  // Сравниваем текущие поля с одним снимком до непросмотренных изменений, не создавая историю опросов.
  if (row.reviewed_at || row.review_reason === 'new') return []
  const before = row.review_before || {}
  if (!Object.keys(before).length) {
    return row.review_reason === 'missing' ? [] : ['Изменились название или доступность; прежние значения не сохранены.']
  }
  const notes = []
  for (const [field, label] of [['service_title', 'Услуга'], ['nominal_title', 'Номинал']]) {
    if (before[field] != null && before[field] !== row[field]) notes.push(`${label}: «${before[field]}» → «${row[field]}»`)
  }
  if (before.status && before.status !== row.status) notes.push(`Доступность: ${status(before.status)} → ${status(row.status)}`)
  if (before.availability_reason !== undefined && before.availability_reason !== row.availability_reason && before.status === row.status) {
    notes.push(`Причина: ${availabilityReasonName(before.availability_reason)} → ${availabilityReasonName(row.availability_reason)}`)
  }
  return notes.length ? notes : ['Данные менялись и вернулись к прежним значениям.']
}
async function load() {
  // Кнопка перечитывает БД; сетевой опрос поставщика здесь никогда не запускается.
  if (!props.token || loading.value) return
  loading.value = true; error.value = ''
  try {
    const result = await apiGet('/integrations/interhub/catalog/current', { token: props.token })
    rows.value = (result.items || []).filter(row => row.service_type === 'VOUCHER')
    sync.value = result.sync
  } catch (err) { error.value = err.message || 'Не удалось загрузить позиции' }
  finally { loading.value = false }
}
async function review(selected) {
  // Передаём только явно показанные строки и их версии, не отмечаем неизвестные новые позиции.
  if (saving.value) return
  saving.value = true; error.value = ''
  try {
    await apiPost('/integrations/interhub/catalog/review', selected.map(({ service_id, nominal_id, review_revision }) => ({ service_id, nominal_id, review_revision })), { token: props.token })
    await load()
  } catch (err) { error.value = err.message || 'Не удалось сохранить отметку' }
  finally { saving.value = false }
}
onMounted(load)
</script>
<style scoped>
.supplier-current { margin: 0 0 16px; border: 1px solid rgba(255,255,255,.13); border-radius: 14px; background: rgba(9,15,29,.35); }
.supplier-current summary { padding: 12px 16px; cursor: pointer; font-size: 14px; font-weight: 700; }
.supplier-current__count, .supplier-current__badge { margin-left: 12px; padding: 4px 9px; border-radius: 7px; font-size: 12px; background: rgba(255,255,255,.05); }
.supplier-current__badge, .supplier-current__new { color: #53d5b6; }
.supplier-current__body { padding: 0 14px 12px; }
.supplier-current__toolbar, .supplier-current__meta, .supplier-current__pagination { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.supplier-current__toolbar > input { flex:1 1 220px; min-width:180px; max-width:360px; height:36px; min-height:36px; padding:7px 10px; font:inherit; font-size:12px; }
.supplier-current__filters { display:flex; flex-wrap:wrap; gap:4px; }
.supplier-current__filters button { font:inherit; font-size:12px; padding:6px 8px; background:transparent; color:inherit; border:1px solid transparent; border-radius:8px; cursor:pointer; }
.supplier-current__filters button[aria-pressed=true] { background:rgba(83,213,182,.12); border-color:rgba(83,213,182,.3); color:#53d5b6; }
.supplier-current__meta { justify-content:space-between; margin:8px 0; font-size:11px; }
.supplier-current__table { max-height:min(360px, 45vh); scrollbar-gutter:stable; }
.supplier-current__table .table thead th { position:sticky; top:0; z-index:1; }
.supplier-current small { display:block; font-size:11px; margin-top:2px; }
.supplier-current .numeric { text-align:right; white-space:nowrap; font-variant-numeric:tabular-nums; }
.supplier-current .ghost { font:inherit; font-size:12px; padding:7px 12px; min-height:32px; white-space:nowrap; }
.supplier-current__status { color:#b9c3d4; }
.supplier-current__status.is-warning { color:#f2ba73; }
.supplier-current__state { min-width:210px; }
.supplier-current__reason { color:#f2ba73; max-width:340px; white-space:normal; }
.supplier-current__changes { margin-top:5px; padding-left:8px; border-left:2px solid rgba(83,213,182,.3); max-width:340px; overflow-wrap:anywhere; white-space:normal; }
.supplier-current__pagination { justify-content:flex-end; margin-top:8px; font-size:12px; }
.supplier-current .account-refresh-btn { width:36px; height:36px; flex-shrink:0; }
.supplier-current summary:focus-visible, .supplier-current__table:focus-visible { outline:2px solid #53d5b6; outline-offset:3px; }
.supplier-current__nominal { display:flex; flex-wrap:wrap; gap:3px 10px; margin-top:2px; }
.supplier-current__ids { font-size:10px; align-self:center; white-space:nowrap; }
.supplier-current__identity { min-width:210px; }
.supplier-current__identity > strong { font-weight:600; }
@media (max-width:760px) {
  .supplier-current__toolbar > input { max-width:none; }
  .supplier-current__filters { order:3; width:100%; }
  .supplier-current__table { max-height:40vh; }
  .supplier-current__meta .ghost { white-space:normal; text-align:left; }
}
</style>
