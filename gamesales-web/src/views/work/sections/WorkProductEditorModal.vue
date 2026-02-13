<template>
  <teleport to="body">
    <div
      v-if="editProduct.open || showProductForm"
      class="work-page work-modal-root modal-backdrop"
      @click.self="closeProductModal"
    >
      <div
        :ref="modalRef"
        :class="['modal', editProduct.open ? 'modal--full' : 'modal--auto']"
        :style="modalStyle"
      >
        <!-- Шапка модалки: действия сохранить/создать/удалить/закрыть -->
        <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
          <h3>{{ editProduct.open ? (editProduct.title ? `Товар ${editProduct.title}` : 'Товар') : 'Новый товар' }}</h3>
          <div class="toolbar-actions">
            <button
              v-if="editProduct.open && productEditMode === 'edit'"
              class="btn btn--icon-plain"
              @click="updateProduct"
              :disabled="productLoading"
              aria-label="Сохранить изменения"
              title="Сохранить изменения"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 4h12l4 4v12H4z" />
                <path d="M7 4v6h8V4" />
                <path d="M7 20v-6h10v6" />
              </svg>
            </button>
            <button
              v-if="!editProduct.open"
              class="btn btn--icon-plain"
              @click="createProduct"
              :disabled="productLoading"
              aria-label="Добавить товар"
              title="Добавить товар"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 4h12l4 4v12H4z" />
                <path d="M7 4v6h8V4" />
                <path d="M7 20v-6h10v6" />
              </svg>
            </button>
            <button
              v-if="editProduct.open"
              class="btn btn--icon-plain btn--edit"
              type="button"
              aria-label="Редактировать"
              title="Редактировать"
              @click="productEditMode = 'edit'"
              :disabled="productEditMode === 'edit'"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 20h4l10-10-4-4L4 16v4Z" />
                <path d="M13 6l4 4" />
              </svg>
            </button>
            <button
              v-if="editProduct.open"
              class="btn btn--icon-plain btn--danger"
              type="button"
              aria-label="Удалить"
              title="Удалить"
              @click="archiveProduct"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 6h14M9 6V4h6v2M7 6l1 14h8l1-14" />
              </svg>
            </button>
            <button
              class="btn btn--icon-plain"
              type="button"
              aria-label="Закрыть"
              title="Закрыть"
              @click="closeProductModal"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 6l12 12M18 6l-12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div class="modal__body" :class="{ 'modal__body--locked': productLoading }">
          <div v-if="productLoading" class="modal__body-overlay">
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

          <!-- Редактирование существующего товара -->
          <div v-if="editProduct.open" class="form form--stack form--compact">
            <label class="field">
              <span class="label">Тип</span>
              <input v-if="productEditMode === 'view'" class="input" :value="editProduct.type_code || PRODUCT_TYPE_PRIMARY" readonly />
              <select v-else v-model="editProduct.type_code" class="input input--select">
                <option :value="PRODUCT_TYPE_PRIMARY">Игра</option>
                <option value="subscription">subscription</option>
              </select>
            </label>
            <div class="field field--full">
              <span class="label">Логотип</span>
              <div class="logo-upload">
                <div v-if="editProduct.logo_b64" class="logo-preview">
                  <img :src="productLogoSrc" alt="logo" />
                </div>
                <div v-else-if="productLogoLoading" class="logo-preview logo-preview--loading">
                  <span class="muted">Загрузка…</span>
                </div>
                <div class="logo-actions">
                  <input
                    class="input input--file"
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    @change="onProductLogoSelected"
                    :disabled="productEditMode === 'view'"
                  />
                  <span v-if="productLogoUploading" class="muted">Загрузка {{ productLogoProgress }}%</span>
                  <button
                    v-if="editProduct.logo_b64"
                    class="ghost ghost--small ghost--danger"
                    type="button"
                    @click="removeProductLogo"
                    :disabled="productEditMode === 'view'"
                  >
                    Удалить
                  </button>
                </div>
              </div>
            </div>
            <label class="field">
              <span class="label">Название</span>
              <input v-model.trim="editProduct.title" class="input" placeholder="Например, GTA V" :readonly="productEditMode === 'view'" />
            </label>
            <label class="field">
              <span class="label">Короткое название</span>
              <input v-model.trim="editProduct.short_title" class="input" placeholder="Например, GTA V" :readonly="productEditMode === 'view'" />
            </label>
            <label class="field">
              <span class="label">Ссылка</span>
              <input v-model.trim="editProduct.link" class="input" placeholder="https://..." :readonly="productEditMode === 'view'" />
            </label>
            <label class="field">
              <span class="label">Язык текста</span>
              <input v-model.trim="editProduct.text_lang" class="input" placeholder="RU/EN/..." :readonly="productEditMode === 'view'" />
            </label>
            <label class="field">
              <span class="label">Язык озвучки</span>
              <input v-model.trim="editProduct.audio_lang" class="input" placeholder="RU/EN/..." :readonly="productEditMode === 'view'" />
            </label>
            <label class="field">
              <span class="label">Поддержка VR</span>
              <input v-model.trim="editProduct.vr_support" class="input" placeholder="например: есть/нет" :readonly="productEditMode === 'view'" />
            </label>
            <label class="field">
              <span class="label">Провайдер подписки</span>
              <input v-model.trim="editProduct.provider" class="input" placeholder="например: sony" :readonly="productEditMode === 'view'" />
            </label>
            <label class="field">
              <span class="label">Период биллинга</span>
              <input v-model.trim="editProduct.billing_period" class="input" placeholder="month/year" :readonly="productEditMode === 'view'" />
            </label>
            <label class="field">
              <span class="label">Заметки по подписке</span>
              <input v-model.trim="editProduct.subscription_notes" class="input" placeholder="комментарий" :readonly="productEditMode === 'view'" />
            </label>
            <div class="field field--full">
              <span class="label">Платформы</span>
              <div class="check-list check-list--compact">
                <label v-for="p in platforms" :key="p.code" class="check-item">
                  <input type="checkbox" :value="p.code" v-model="editProduct.platform_codes" :disabled="productEditMode === 'view'" />
                  <span>{{ p.name }} ({{ p.code }})</span>
                </label>
              </div>
            </div>
            <label class="field">
              <span class="label">Регион</span>
              <input
                v-if="productEditMode === 'view'"
                class="input"
                :value="getRegionLabel(editProduct.region_code)"
                readonly
              />
              <select v-else v-model="editProduct.region_code" class="input input--select">
                <option value="">— не выбрано —</option>
                <option v-for="r in regions" :key="r.code" :value="r.code">
                  {{ r.name }} ({{ r.code }})
                </option>
              </select>
            </label>
            <div class="divider"></div>
            <div class="field field--full">
              <span class="label">Аккаунты по сделкам</span>
              <p v-if="productAccountsError" class="bad">{{ productAccountsError }}</p>
              <div v-if="productAccountsLoading" class="loader-wrap loader-wrap--compact">
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
              </div>
              <table v-else-if="pagedProductAccounts.length" class="table table--compact table--dense">
                <thead>
                  <tr>
                    <th class="sortable" @click="sortProductAccounts('login_full')">Аккаунт</th>
                    <th class="sortable" @click="sortProductAccounts('platform_code')">Платформа</th>
                    <th class="sortable cell--num" @click="sortProductAccounts('free_slots')">Свободно</th>
                    <th class="sortable cell--num" @click="sortProductAccounts('occupied_slots')">Занято</th>
                    <th class="cell--tight"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="a in pagedProductAccounts" :key="`${a.account_id}-${a.platform_code}`">
                    <td>{{ a.login_full || '—' }}</td>
                    <td>{{ (a.platform_code || '—').toUpperCase() }}</td>
                    <td class="cell--num">{{ a.free_slots ?? 0 }}</td>
                    <td class="cell--num">{{ a.occupied_slots ?? 0 }}</td>
                    <td class="cell--tight">
                      <button class="ghost ghost--small" type="button" @click="openAccountFromProduct(a.login_full)">
                        Открыть
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="muted">Сделок по товару пока нет.</p>
              <div v-if="productAccountsTotalPages > 1" class="pager">
                <button class="ghost" @click="prevProductAccountsPage" :disabled="productAccountsPage <= 1">
                  ← Назад
                </button>
                <span class="muted">Страница {{ productAccountsPage }} из {{ productAccountsTotalPages }}</span>
                <button class="ghost" @click="nextProductAccountsPage" :disabled="productAccountsPage >= productAccountsTotalPages">
                  Вперёд →
                </button>
              </div>
            </div>
            <div class="field field--full">
              <span class="label">Слоты по товару</span>
              <p v-if="productSlotAssignmentsError" class="bad">{{ productSlotAssignmentsError }}</p>
              <div v-if="productSlotAssignmentsLoading" class="loader-wrap loader-wrap--compact">
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
              </div>
              <table v-else-if="productSlotAssignments.length" class="table table--compact table--dense">
                <thead>
                  <tr>
                    <th>Аккаунт</th>
                    <th>Слот</th>
                    <th>Покупатель</th>
                    <th>Статус</th>
                    <th>Назначено</th>
                    <th>Снято</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="s in productSlotAssignments" :key="s.assignment_id">
                    <td>{{ s.account_login || s.account_id || '—' }}</td>
                    <td>{{ getSlotTypeLabel(s.slot_type_code) }}</td>
                    <td>{{ s.customer_nickname || '—' }}</td>
                    <td>{{ getSlotAssignmentStatus(s) }}</td>
                    <td>{{ formatDateTimeMinutes(s.assigned_at) }}</td>
                    <td>{{ s.released_at ? formatDateTimeMinutes(s.released_at) : '—' }}</td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="muted">Слотов по товару пока нет.</p>
            </div>
            <p v-if="productError" class="bad">{{ productError }}</p>
            <p v-if="productOk" class="ok">{{ productOk }}</p>
          </div>

          <!-- Создание нового товара -->
          <div v-else class="form form--stack form--compact">
            <div class="field field--full">
              <span class="label">Логотип</span>
              <p class="muted">Логотип можно загрузить после создания товара.</p>
            </div>
            <label class="field">
              <span class="label">Тип</span>
              <select v-model="newProduct.type_code" class="input input--select">
                <option :value="PRODUCT_TYPE_PRIMARY">Игра</option>
                <option value="subscription">subscription</option>
              </select>
            </label>
            <label class="field">
              <span class="label">Название</span>
              <input v-model.trim="newProduct.title" class="input" placeholder="Например, GTA V" />
            </label>
            <label class="field">
              <span class="label">Короткое название</span>
              <input v-model.trim="newProduct.short_title" class="input" placeholder="Например, GTA V" />
            </label>
            <label class="field">
              <span class="label">Ссылка</span>
              <input v-model.trim="newProduct.link" class="input" placeholder="https://..." />
            </label>
            <label class="field">
              <span class="label">Язык текста</span>
              <input v-model.trim="newProduct.text_lang" class="input" placeholder="RU/EN/..." />
            </label>
            <label class="field">
              <span class="label">Язык озвучки</span>
              <input v-model.trim="newProduct.audio_lang" class="input" placeholder="RU/EN/..." />
            </label>
            <label class="field">
              <span class="label">Поддержка VR</span>
              <input v-model.trim="newProduct.vr_support" class="input" placeholder="например: есть/нет" />
            </label>
            <label class="field">
              <span class="label">Провайдер подписки</span>
              <input v-model.trim="newProduct.provider" class="input" placeholder="например: sony" />
            </label>
            <label class="field">
              <span class="label">Период биллинга</span>
              <input v-model.trim="newProduct.billing_period" class="input" placeholder="month/year" />
            </label>
            <label class="field">
              <span class="label">Заметки по подписке</span>
              <input v-model.trim="newProduct.subscription_notes" class="input" placeholder="комментарий" />
            </label>
            <div class="field field--full">
              <span class="label">Платформы (опционально)</span>
              <div class="check-list check-list--compact">
                <label v-for="p in platforms" :key="p.code" class="check-item">
                  <input type="checkbox" :value="p.code" v-model="newProduct.platform_codes" />
                  <span>{{ p.name }} ({{ p.code }})</span>
                </label>
              </div>
            </div>
            <label class="field">
              <span class="label">Регион (опционально)</span>
              <select v-model="newProduct.region_code" class="input input--select">
                <option value="">— не выбрано —</option>
                <option v-for="r in regions" :key="r.code" :value="r.code">
                  {{ r.name }} ({{ r.code }})
                </option>
              </select>
            </label>
            <p v-if="productError" class="bad">{{ productError }}</p>
            <p v-if="productOk" class="ok">{{ productOk }}</p>
          </div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { reactive, toRefs } from 'vue'
import { PRODUCT_TYPE_PRIMARY } from '../domainUtils'

// Передаем один объект контекста, чтобы не раздувать длинный список props.
const props = defineProps({
  ctx: { type: Object, required: true },
})
const ctx = reactive(props.ctx)

const {
  editProduct,
  showProductForm,
  closeProductModal,
  modalRef,
  modalStyle,
  startModalDrag,
  productEditMode,
  updateProduct,
  productLoading,
  createProduct,
  archiveProduct,
  productLogoSrc,
  productLogoLoading,
  onProductLogoSelected,
  productLogoUploading,
  productLogoProgress,
  removeProductLogo,
  platforms,
  getRegionLabel,
  regions,
  productAccountsError,
  productAccountsLoading,
  pagedProductAccounts,
  sortProductAccounts,
  openAccountFromProduct,
  productAccountsTotalPages,
  productAccountsPage,
  prevProductAccountsPage,
  nextProductAccountsPage,
  productSlotAssignmentsError,
  productSlotAssignmentsLoading,
  productSlotAssignments,
  getSlotTypeLabel,
  getSlotAssignmentStatus,
  formatDateTimeMinutes,
  productError,
  productOk,
  newProduct,
} = toRefs(ctx)
</script>
