<template>
            <teleport to="body">
              <div
                v-if="showAccountImport"
                class="work-page work-modal-root modal-backdrop"
                @click.self="closeAccountImport"
              >
                <div :ref="modalRef" class="modal modal--auto" :style="modalStyle">
                  <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
                    <h3>Импорт аккаунтов из файла</h3>
                    <button
                      class="btn btn--icon-plain"
                      type="button"
                      aria-label="Закрыть"
                      title="Закрыть"
                      @click="closeAccountImport"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M6 6l12 12M18 6l-12 12" />
                      </svg>
                    </button>
                  </div>
                  <div class="modal__body" :class="{ 'modal__body--locked': accountImportLoading }">
                    <div v-if="accountImportLoading" class="modal__body-overlay">
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
                      <button class="ghost" type="button" @click="downloadAccountTemplate">
                        Шаблон
                      </button>
                      <button class="ghost" type="button" @click="downloadAccountImportExport" :disabled="accountImportLoading">
                        Экспорт
                      </button>
                      <button class="ghost" type="button" @click="validateAccountSlotsCheck" :disabled="!accountImportFile || accountImportLoading">
                        Проверка слотов
                      </button>
                      <button class="ghost" type="button" @click="validateAccountDealsCheck" :disabled="!accountImportFile || accountImportLoading">
                        Проверка сделок
                      </button>
                      <button class="ghost" type="button" @click="fillAccountDealsOrderNumbers" :disabled="!accountImportFile || accountImportLoading">
                        Залить заявки
                      </button>
                      <button class="ghost" type="button" @click="validateAccountImport" :disabled="!accountImportFile || accountImportLoading">
                        <span v-if="accountImportLoading && accountImportAction === 'validate'" class="spinner spinner--small"></span>
                        Проверка
                      </button>
                      <button
                        class="ghost"
                        type="button"
                        @click="uploadAccountImport"
                        :disabled="!accountImportValidated || !accountImportFile || accountImportLoading"
                        title="Загрузить"
                        aria-label="Загрузить"
                      >
                        <span v-if="accountImportLoading && accountImportAction === 'upload'" class="spinner spinner--small"></span>
                        Загрузить
                      </button>
                      <button
                        v-if="accountImportLoading && accountImportJobId"
                        class="ghost"
                        type="button"
                        @click="cancelAccountImport"
                        title="Отменить импорт"
                        aria-label="Отменить импорт"
                      >
                        Отмена
                      </button>
                      <button v-if="accountImportLoading" class="import-status" type="button" @click="scrollToAccountImportDetails">
                        <span v-if="accountImportAction === 'validate'">Проверка…</span>
                        <span v-else-if="accountImportAction === 'cancel'">Отмена…</span>
                        <span v-else-if="accountImportAction === 'upload' && accountImportProgress.total">Загрузка: {{ accountImportProgress.current }} из {{ accountImportProgress.total }}</span>
                        <span v-else-if="accountImportAction === 'upload'">Загрузка…</span>
                      </button>
                    </div>
                    <div class="form form--stack form--compact">
                      <label class="field field--full">
                        <span class="label">Файл (xlsx/xls)</span>
                        <input
                          class="input input--file"
                          type="file"
                          accept=".xlsx,.xls"
                          @change="onAccountImportFile"
                          :disabled="accountImportLoading"
                        />
                      </label>
                      <div :ref="accountImportDetailsRef">
                        <p v-if="accountImportMessage" class="ok">{{ accountImportMessage }}</p>
                      <div v-if="accountImportErrors.length || accountImportWarnings.length" class="toolbar-actions import-actions">
                        <button class="ghost" type="button" @click="downloadAccountImportReport">
                          Скачать отчет
                        </button>
                      </div>
                      <p v-if="accountImportStats" class="muted">
                        Итог: создано {{ accountImportStats.created }}, обновлено {{ accountImportStats.updated }}, пропущено {{ accountImportStats.skipped }}, ошибок {{ accountImportStats.failed }}, всего {{ accountImportStats.total }}
                      </p>
                      <div v-if="accountImportStats?.details" class="import-errors">
                        <p class="muted">
                          Создано: {{ accountImportStats.details.created.accounts_from_bindings_sheet }} — аккаунтов (лист Аккаунты), {{ accountImportStats.details.created.accounts_from_mail_sheets }} — аккаунтов (листы Почты*), {{ accountImportStats.details.created.subscription_terms }} — сроков подписок
                        </p>
                        <p class="muted">
                          Обновлено: {{ accountImportStats.details.updated.game_bindings }} — привязок игр, {{ accountImportStats.details.updated.accounts_from_mail_sheets }} — существующих аккаунтов (листы Почты*), {{ accountImportStats.details.updated.subscription_terms }} — существующих сроков подписок
                        </p>
                        <p class="muted">
                          Пропущено: {{ accountImportStats.details.skipped.binding_rows }} — строки листа Аккаунты, {{ accountImportStats.details.skipped.mail_rows }} — строки листов Почты*, {{ accountImportStats.details.skipped.subscription_rows }} — строки листов ПЛЮС/EA PLAY
                        </p>
                        <p class="muted">
                          Дополнительно: создано базовых товаров подписки {{ accountImportStats.details.meta.subscription_products_created }}
                        </p>
                      </div>
                      <div v-if="accountImportWarnings.length" class="import-errors">
                        <p class="muted">Предупреждения: {{ accountImportWarnings.length }}</p>
                        <table class="table table--compact table--dense">
                          <thead>
                            <tr>
                              <th>Строка</th>
                              <th>Поле</th>
                              <th>Значение</th>
                              <th>Предупреждение</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr v-for="(e, idx) in accountImportWarnings" :key="`aw-${idx}`">
                              <td>{{ e.row }}</td>
                              <td>{{ e.field }}</td>
                              <td>{{ e.value || '—' }}</td>
                              <td>{{ e.message }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                      <div v-if="accountImportErrors.length" class="import-errors">
                        <p class="bad">Ошибки: {{ accountImportErrors.length }}</p>
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
                            <tr v-for="(e, idx) in accountImportErrors" :key="`ae-${idx}`">
                              <td>{{ e.row }}</td>
                              <td>{{ e.field }}</td>
                              <td>{{ e.value || '—' }}</td>
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
defineProps([
  'showAccountImport',
  'closeAccountImport',
  'modalRef',
  'modalStyle',
  'startModalDrag',
  'accountImportLoading',
  'downloadAccountTemplate',
  'downloadAccountImportExport',
  'validateAccountSlotsCheck',
  'validateAccountDealsCheck',
  'fillAccountDealsOrderNumbers',
  'validateAccountImport',
  'accountImportFile',
  'accountImportAction',
  'uploadAccountImport',
  'accountImportValidated',
  'accountImportJobId',
  'cancelAccountImport',
  'scrollToAccountImportDetails',
  'accountImportProgress',
  'onAccountImportFile',
  'accountImportDetailsRef',
  'accountImportMessage',
  'accountImportErrors',
  'accountImportWarnings',
  'downloadAccountImportReport',
  'accountImportStats',
])
</script>
