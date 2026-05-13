<template>
  <teleport to="body">
    <div
      v-if="showSlotImport"
      class="work-page work-modal-root modal-backdrop"
      @click.self="closeSlotImport"
    >
      <div :ref="modalRef" class="modal modal--auto" :style="modalStyle">
        <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
          <h3>Импорт слотов из файла</h3>
          <button
            class="btn btn--icon-plain"
            type="button"
            aria-label="Закрыть"
            title="Закрыть"
            @click="closeSlotImport"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6 6l12 12M18 6l-12 12" />
            </svg>
          </button>
        </div>
        <div class="modal__body" :class="{ 'modal__body--locked': slotImportLoading }">
          <div v-if="slotImportLoading" class="modal__body-overlay">
            <div class="loader-wrap loader-wrap--compact">
              <div class="newtons-cradle" aria-label="Loading" role="img">
                <div class="newtons-cradle__dot"></div>
                <div class="newtons-cradle__dot"></div>
                <div class="newtons-cradle__dot"></div>
                <div class="newtons-cradle__dot"></div>
              </div>
              <p class="muted">Обработка…</p>
            </div>
          </div>
          <div class="toolbar-actions import-actions import-actions--fixed">
            <button class="ghost" type="button" @click="validateSlotImport" :disabled="!slotImportFile || slotImportLoading">
              <span v-if="slotImportLoading" class="spinner spinner--small"></span>
              Проверка
            </button>
            <button
              class="ghost"
              type="button"
              @click="uploadSlotImport"
              :disabled="!slotImportValidated || !slotImportFile || slotImportLoading"
              title="Загрузить"
              aria-label="Загрузить"
            >
              <span v-if="slotImportLoading && slotImportAction === 'upload'" class="spinner spinner--small"></span>
              Загрузить
            </button>
            <button class="ghost" type="button" @click="cleanSlotImport" :disabled="!slotImportFile || slotImportLoading">
              <span v-if="slotImportLoading" class="spinner spinner--small"></span>
              Очистить файл
            </button>
            <button
              v-if="slotImportLoading && slotImportJobId"
              class="ghost"
              type="button"
              @click="cancelSlotImport"
              title="Отменить проверку"
              aria-label="Отменить проверку"
            >
              Отмена
            </button>
            <button v-if="slotImportLoading && slotImportJobId" class="import-status" type="button">
              <span v-if="slotImportAction === 'validate' && slotImportProgress.total">Проверка: {{ slotImportProgress.current }} из {{ slotImportProgress.total }}</span>
              <span v-else-if="slotImportAction === 'upload' && slotImportProgress.total">Загрузка: {{ slotImportProgress.current }} из {{ slotImportProgress.total }}</span>
              <span v-else-if="slotImportAction === 'upload'">Загрузка…</span>
              <span v-else-if="slotImportAction === 'cancel'">Отмена…</span>
              <span v-else-if="slotImportAction === 'validate'">Проверка…</span>
            </button>
          </div>
          <div class="form form--stack form--compact">
            <label class="field field--full">
              <span class="label">Файл (xlsx/xls)</span>
              <input
                class="input input--file"
                type="file"
                accept=".xlsx,.xls"
                @change="onSlotImportFile"
                :disabled="slotImportLoading"
              />
            </label>
            <label class="field">
              <span class="label">Проверять первые N строк</span>
              <input
                v-model.number="slotImportLimitModel"
                class="input"
                type="number"
                min="1"
                placeholder="Например, 10"
                :disabled="slotImportLoading"
              />
            </label>
            <div v-if="slotImportErrors.length || slotImportWarnings.length" class="toolbar-actions import-actions">
              <button class="ghost" type="button" @click="downloadSlotImportReport">
                Скачать отчет
              </button>
            </div>
            <p v-if="slotImportValidated" class="muted">
              Итог: строк к загрузке {{ slotImportTotal }}, предупреждений {{ slotImportWarnings.length }}, ошибок {{ slotImportErrors.length }}
            </p>
            <p v-if="slotImportStats" class="muted">
              Итог загрузки: создано {{ slotImportStats.created }}, снято {{ slotImportStats.released }}, пропущено {{ slotImportStats.skipped }}, ошибок {{ slotImportStats.failed }}, всего {{ slotImportStats.total }}
            </p>
            <div v-if="slotImportWarnings.length" class="import-errors">
              <p class="muted">Предупреждения: {{ slotImportWarnings.length }}</p>
              <table class="table table--compact table--dense">
                <thead>
                  <tr>
                    <th>Строка</th>
                    <th>Почта</th>
                    <th>Поле</th>
                    <th>Значение</th>
                    <th>Предупреждение</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(e, idx) in slotImportWarnings" :key="`sw-${idx}`">
                    <td>{{ e.row }}</td>
                    <td>{{ e.account || '—' }}</td>
                    <td>{{ e.field }}</td>
                    <td>{{ e.value || '—' }}</td>
                    <td>{{ e.message }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="slotImportErrors.length" class="import-errors">
              <p class="bad">Ошибки: {{ slotImportErrors.length }}</p>
              <table class="table table--compact table--dense">
                <thead>
                  <tr>
                    <th>Строка</th>
                    <th>Поле</th>
                    <th>Значение</th>
                    <th>Ошибка</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(e, idx) in slotImportErrors" :key="`se-${idx}`">
                    <td>{{ e.row }}</td>
                    <td>{{ e.field }}</td>
                    <td>{{ e.value || '—' }}</td>
                    <td>{{ e.message }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p v-if="slotImportMessage" class="ok">{{ slotImportMessage }}</p>
            <p v-if="slotImportError" class="bad">{{ slotImportError }}</p>
            <p class="muted">Будут удалены строки, где в колонке «Статус» указано «свободен» (любой регистр) или пусто.</p>
          </div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps([
  'showSlotImport',
  'closeSlotImport',
  'modalRef',
  'modalStyle',
  'startModalDrag',
  'slotImportLoading',
  'validateSlotImport',
  'slotImportFile',
  'uploadSlotImport',
  'slotImportValidated',
  'slotImportAction',
  'cleanSlotImport',
  'slotImportJobId',
  'cancelSlotImport',
  'slotImportProgress',
  'onSlotImportFile',
  'slotImportLimit',
  'setSlotImportLimit',
  'slotImportErrors',
  'slotImportWarnings',
  'downloadSlotImportReport',
  'slotImportTotal',
  'slotImportStats',
  'slotImportMessage',
  'slotImportError',
])

const slotImportLimitModel = computed({
  get: () => props.slotImportLimit,
  set: (value) => props.setSlotImportLimit(value),
})
</script>
