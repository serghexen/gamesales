<template>
  <button ref="trigger" class="ghost" type="button" @click="openReport">Отчёт</button>
  <teleport to="body">
    <div v-if="open" class="work-page work-modal-root modal-backdrop voucher-report-backdrop" @click.self="closeReport" @keydown="onKey">
      <section ref="dialog" class="modal voucher-report" role="dialog" aria-modal="true" aria-labelledby="voucher-report-title" tabindex="-1">
        <header class="voucher-report__head">
          <h3 id="voucher-report-title">Отчёт по ваучерам</h3>
          <button class="ghost" type="button" :disabled="busy" aria-label="Закрыть отчёт" @click="closeReport">Закрыть</button>
        </header>
        <form @submit.prevent="download">
          <div class="voucher-report__dates">
            <label class="field"><span class="label">Дата с</span><input v-model="dateFrom" class="input" type="date" required :max="today" :disabled="busy" /></label>
            <label class="field"><span class="label">Дата по</span><input v-model="dateTo" class="input" type="date" required :max="today" :disabled="busy" /></label>
          </div>
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <p v-if="done" class="muted" role="status">Файл готов и передан для скачивания.</p>
          <button class="btn" type="submit" :disabled="busy" :aria-busy="busy">{{ busy ? 'Формируем отчёт…' : 'Выгрузить' }}</button>
        </form>
      </section>
    </div>
  </teleport>
</template>

<script setup>
import { nextTick, ref } from 'vue'
import { apiGetFile } from '../../../api/http'

const props = defineProps({ token: { type: String, default: '' } })
const open = ref(false)
const busy = ref(false)
const error = ref('')
const done = ref(false)
const dateFrom = ref('')
const dateTo = ref('')
const today = ref('')
const dialog = ref(null)
const trigger = ref(null)

async function openReport() {
  // Значения по умолчанию соответствуют текущему месяцу в Москве, независимо от зоны браузера.
  const parts = new Intl.DateTimeFormat('en', { timeZone: 'Europe/Moscow', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date())
  const part = type => parts.find(item => item.type === type).value
  today.value = `${part('year')}-${part('month')}-${part('day')}`
  if (!dateFrom.value) dateFrom.value = `${today.value.slice(0, 7)}-01`
  if (!dateTo.value) dateTo.value = today.value
  error.value = ''; done.value = false; open.value = true
  await nextTick()
  dialog.value?.querySelector('input')?.focus()
}

async function closeReport() {
  // Сохраняем введённые даты и возвращаем фокус к кнопке после закрытия окна.
  if (busy.value) return
  open.value = false
  await nextTick()
  trigger.value?.focus()
}

function onKey(event) {
  // Escape закрывает окно, а Tab не переводит фокус на скрытый под ним каталог.
  if (event.key === 'Escape') { event.preventDefault(); closeReport() }
  if (event.key !== 'Tab') return
  const nodes = [...dialog.value.querySelectorAll('button:not(:disabled), input:not(:disabled)')]
  const index = nodes.indexOf(document.activeElement)
  if (!nodes.length) { event.preventDefault(); dialog.value.focus(); return }
  if ((event.shiftKey && index <= 0) || (!event.shiftKey && (index < 0 || index === nodes.length - 1))) {
    event.preventDefault(); nodes[event.shiftKey ? nodes.length - 1 : 0].focus()
  }
}

async function download() {
  // Повторный клик не запускает вторую выгрузку; ошибки оставляют форму доступной для исправления.
  if (busy.value) return
  error.value = ''; done.value = false
  if (!dateFrom.value || !dateTo.value || dateFrom.value > dateTo.value || dateTo.value > today.value) {
    error.value = 'Укажите корректный диапазон дат до сегодняшнего дня'
    return
  }
  busy.value = true
  let url = ''
  try {
    const query = new URLSearchParams({ date_from: dateFrom.value, date_to: dateTo.value })
    const blob = await apiGetFile(`/integrations/interhub/voucher-sales/export?${query}`, { token: props.token })
    url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url; link.download = `voucher-sales-${dateFrom.value}-${dateTo.value}.xlsx`
    document.body.appendChild(link); link.click(); link.remove()
    done.value = true
  } catch (exception) {
    error.value = exception?.message || 'Не удалось сформировать отчёт'
  } finally {
    if (url) URL.revokeObjectURL(url)
    busy.value = false
  }
}
</script>

<style scoped>
.voucher-report-backdrop { z-index: 1100; align-items: center; padding: 16px; }
.work-page.work-modal-root .voucher-report { --ink: #f4f7ff; --muted: #b5bfd3; --input-bg: #0d1320; --input-border: #424b61; --ghost-text: #f4f7ff; --ghost-bg: #202838; --ghost-border: #424b61; width: min(540px, calc(100vw - 32px)); min-height: 0; height: auto; max-height: calc(100dvh - 32px); overflow: auto; padding: 24px; background: #101626; color: #f4f7ff; border: 1px solid #424b61; border-radius: 20px; }
.voucher-report__head { display: flex; justify-content: space-between; gap: 16px; align-items: center; margin-bottom: 24px; }
.voucher-report__head h3 { margin: 0; font-size: 22px; }
.voucher-report__dates { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.voucher-report input { color-scheme: dark; min-width: 0; }
.voucher-report p { margin: 16px 0; }
.voucher-report .error { color: #ffb4b4; }
@media (max-width: 480px) { .voucher-report__dates { grid-template-columns: 1fr; } }
</style>
