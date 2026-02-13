<template>
  <teleport to="body">
    <div
      v-if="showProductImport"
      class="work-page work-modal-root modal-backdrop"
      @click.self="closeProductImport"
    >
      <div :ref="modalRef" class="modal modal--auto" :style="modalStyle">
        <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
          <h3>Импорт товаров из файла</h3>
          <button
            class="btn btn--icon-plain"
            type="button"
            aria-label="Закрыть"
            title="Закрыть"
            @click="closeProductImport"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6 6l12 12M18 6l-12 12" />
            </svg>
          </button>
        </div>
        <div class="modal__body" :class="{ 'modal__body--locked': productImportLoading }">
          <div v-if="productImportLoading" class="modal__body-overlay">
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
            <button class="ghost" type="button" @click="downloadProductTemplate">
              Шаблон
            </button>
            <button class="ghost" type="button" @click="validateProductImport" :disabled="!productImportFile || productImportLoading">
              <span v-if="productImportLoading && productImportAction === 'validate'" class="spinner spinner--small"></span>
              Проверка
            </button>
            <button
              class="ghost"
              type="button"
              @click="uploadProductImport"
              :disabled="!productImportValidated || !productImportFile || productImportLoading"
              title="Загрузить"
              aria-label="Загрузить"
            >
              <span v-if="productImportLoading && productImportAction === 'upload'" class="spinner spinner--small"></span>
              Загрузить
            </button>
            <button
              v-if="productImportLoading && productImportJobId"
              class="ghost"
              type="button"
              @click="cancelProductImport"
              title="Отменить импорт"
              aria-label="Отменить импорт"
            >
              Отмена
            </button>
            <button v-if="productImportLoading" class="import-status" type="button" @click="scrollToImportDetails">
              <span v-if="productImportAction === 'validate'">Проверка…</span>
              <span v-else-if="productImportAction === 'cancel'">Отмена…</span>
              <span v-else-if="productImportAction === 'upload' && productImportProgress.total">Загрузка: {{ productImportProgress.current }} из {{ productImportProgress.total }}</span>
              <span v-else-if="productImportAction === 'upload'">Загрузка…</span>
            </button>
          </div>
          <div class="form form--stack form--compact">
            <label class="field field--full">
              <span class="label">Файл (xlsx/xls)</span>
              <input
                class="input input--file"
                type="file"
                accept=".xlsx,.xls"
                @change="onProductImportFile"
                :disabled="productImportLoading"
              />
            </label>
            <div :ref="importDetailsRef">
              <p v-if="productImportMessage" class="ok">{{ productImportMessage }}</p>
              <div v-if="productImportErrors.length || productImportWarnings.length" class="toolbar-actions import-actions">
                <button class="ghost" type="button" @click="downloadProductImportReport">
                  Скачать отчет
                </button>
              </div>
              <p v-if="productImportStats" class="muted">
                Итог: создано {{ productImportStats.created }}, обновлено {{ productImportStats.updated }}, пропущено {{ productImportStats.skipped }}, ошибок {{ productImportStats.failed }}, всего {{ productImportStats.total }}
              </p>
              <div v-if="productImportWarnings.length" class="import-errors">
                <p class="muted">Предупреждения: {{ productImportWarnings.length }}</p>
                <table class="table table--compact table--dense">
                  <thead>
                    <tr>
                      <th>Строка</th>
                      <th>Поле</th>
                      <th>Предупреждение</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(e, idx) in productImportWarnings" :key="`w-${idx}`">
                      <td>{{ e.row }}</td>
                      <td>{{ e.field }}</td>
                      <td>{{ e.message }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-if="productImportErrors.length" class="import-errors">
                <p class="bad">Ошибки: {{ productImportErrors.length }}</p>
                <table class="table table--compact table--dense">
                  <thead>
                    <tr>
                      <th>Строка</th>
                      <th>Поле</th>
                      <th>Ошибка</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(e, idx) in productImportErrors" :key="idx">
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
  showProductImport: { type: Boolean, required: true },
  closeProductImport: { type: Function, required: true },
  // Контейнер модалки появляется позже, поэтому до открытия здесь может быть null.
  modalRef: { type: [Object, null], default: null },
  modalStyle: { type: Object, required: true },
  startModalDrag: { type: Function, required: true },
  productImportLoading: { type: Boolean, required: true },
  downloadProductTemplate: { type: Function, required: true },
  validateProductImport: { type: Function, required: true },
  productImportFile: { type: [File, Object, null], default: null },
  productImportAction: { type: String, default: '' },
  uploadProductImport: { type: Function, required: true },
  productImportValidated: { type: Boolean, required: true },
  productImportJobId: { type: [Number, String, null], default: null },
  cancelProductImport: { type: Function, required: true },
  scrollToImportDetails: { type: Function, required: true },
  productImportProgress: { type: Object, required: true },
  onProductImportFile: { type: Function, required: true },
  // На первом рендере ref может быть null, это нормальное состояние.
  importDetailsRef: { type: [Object, null], default: null },
  productImportMessage: { type: String, default: '' },
  productImportErrors: { type: Array, required: true },
  productImportWarnings: { type: Array, required: true },
  downloadProductImportReport: { type: Function, required: true },
  productImportStats: { type: [Object, null], default: null },
})
</script>
