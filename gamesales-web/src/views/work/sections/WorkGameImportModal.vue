<template>
  <teleport to="body">
    <div
      v-if="showGameImport"
      class="work-page work-modal-root modal-backdrop"
      @click.self="closeGameImport"
    >
      <div :ref="modalRef" class="modal modal--auto" :style="modalStyle">
        <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
          <h3>Импорт игр из файла</h3>
          <button
            class="btn btn--icon-plain"
            type="button"
            aria-label="Закрыть"
            title="Закрыть"
            @click="closeGameImport"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6 6l12 12M18 6l-12 12" />
            </svg>
          </button>
        </div>
        <div class="modal__body" :class="{ 'modal__body--locked': gameImportLoading }">
          <div v-if="gameImportLoading" class="modal__body-overlay">
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
          <div class="toolbar-actions import-actions import-actions--fixed">
            <button class="ghost" type="button" @click="downloadGameTemplate">
              Шаблон
            </button>
            <button class="ghost" type="button" @click="validateGameImport" :disabled="!gameImportFile || gameImportLoading">
              <span v-if="gameImportLoading && gameImportAction === 'validate'" class="spinner spinner--small"></span>
              Проверка
            </button>
            <button
              class="ghost"
              type="button"
              @click="uploadGameImport"
              :disabled="!gameImportValidated || !gameImportFile || gameImportLoading"
              title="Загрузить"
              aria-label="Загрузить"
            >
              <span v-if="gameImportLoading && gameImportAction === 'upload'" class="spinner spinner--small"></span>
              Загрузить
            </button>
            <button
              v-if="gameImportLoading && gameImportJobId"
              class="ghost"
              type="button"
              @click="cancelGameImport"
              title="Отменить импорт"
              aria-label="Отменить импорт"
            >
              Отмена
            </button>
            <button v-if="gameImportLoading" class="import-status" type="button" @click="scrollToImportDetails">
              <span v-if="gameImportAction === 'validate'">Проверка…</span>
              <span v-else-if="gameImportAction === 'cancel'">Отмена…</span>
              <span v-else-if="gameImportAction === 'upload' && gameImportProgress.total">Загрузка: {{ gameImportProgress.current }} из {{ gameImportProgress.total }}</span>
              <span v-else-if="gameImportAction === 'upload'">Загрузка…</span>
            </button>
          </div>
          <div class="form form--stack form--compact">
            <label class="field field--full">
              <span class="label">Файл (xlsx/xls)</span>
              <input
                class="input input--file"
                type="file"
                accept=".xlsx,.xls"
                @change="onGameImportFile"
                :disabled="gameImportLoading"
              />
            </label>
            <div :ref="importDetailsRef">
              <p v-if="gameImportMessage" class="ok">{{ gameImportMessage }}</p>
              <div v-if="gameImportErrors.length || gameImportWarnings.length" class="toolbar-actions import-actions">
                <button class="ghost" type="button" @click="downloadGameImportReport">
                  Скачать отчет
                </button>
              </div>
              <p v-if="gameImportStats" class="muted">
                Итог: создано {{ gameImportStats.created }}, обновлено {{ gameImportStats.updated }}, пропущено {{ gameImportStats.skipped }}, ошибок {{ gameImportStats.failed }}, всего {{ gameImportStats.total }}
              </p>
              <div v-if="gameImportWarnings.length" class="import-errors">
                <p class="muted">Предупреждения: {{ gameImportWarnings.length }}</p>
                <table class="table table--compact table--dense">
                  <thead>
                    <tr>
                      <th>Строка</th>
                      <th>Поле</th>
                      <th>Предупреждение</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(e, idx) in gameImportWarnings" :key="`w-${idx}`">
                      <td>{{ e.row }}</td>
                      <td>{{ e.field }}</td>
                      <td>{{ e.message }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-if="gameImportErrors.length" class="import-errors">
                <p class="bad">Ошибки: {{ gameImportErrors.length }}</p>
                <table class="table table--compact table--dense">
                  <thead>
                    <tr>
                      <th>Строка</th>
                      <th>Поле</th>
                      <th>Ошибка</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(e, idx) in gameImportErrors" :key="idx">
                      <td>{{ e.row }}</td>
                      <td>{{ e.field }}</td>
                      <td>{{ e.message }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
defineProps({
  showGameImport: { type: Boolean, required: true },
  closeGameImport: { type: Function, required: true },
  modalRef: { type: Object, required: true },
  modalStyle: { type: Object, required: true },
  startModalDrag: { type: Function, required: true },
  gameImportLoading: { type: Boolean, required: true },
  downloadGameTemplate: { type: Function, required: true },
  validateGameImport: { type: Function, required: true },
  gameImportFile: { type: [File, Object, null], default: null },
  gameImportAction: { type: String, default: '' },
  uploadGameImport: { type: Function, required: true },
  gameImportValidated: { type: Boolean, required: true },
  gameImportJobId: { type: [Number, String, null], default: null },
  cancelGameImport: { type: Function, required: true },
  scrollToImportDetails: { type: Function, required: true },
  gameImportProgress: { type: Object, required: true },
  onGameImportFile: { type: Function, required: true },
  importDetailsRef: { type: Object, required: true },
  gameImportMessage: { type: String, default: '' },
  gameImportErrors: { type: Array, required: true },
  gameImportWarnings: { type: Array, required: true },
  downloadGameImportReport: { type: Function, required: true },
  gameImportStats: { type: [Object, null], default: null },
})
</script>
