<template>
  <!-- Все модалки справочников собраны в одном месте -->
  <teleport to="body">
    <div
      v-if="showDomainForm || editDomain.open"
      class="work-page work-modal-root modal-backdrop"
      @click.self="closeDomainModal"
    >
      <div :ref="modalRef" class="modal modal--auto" :style="modalStyle">
        <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
          <h3>{{ editDomain.open ? (domainEditMode === 'edit' ? 'Редактирование домена' : 'Домен') : 'Новый домен' }}</h3>
          <div class="toolbar-actions">
            <button
              v-if="editDomain.open && domainEditMode === 'edit'"
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save"
              @click="saveEditDomain"
              :disabled="catalogsLoading"
              aria-label="Сохранить"
              title="Сохранить"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 4h12l4 4v12H4z" />
                <path d="M7 4v6h8V4" />
                <path d="M7 20v-6h10v6" />
              </svg>
            </button>
            <button
              v-if="editDomain.open"
              class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--edit"
              type="button"
              aria-label="Редактировать"
              title="Редактировать"
              @click="domainEditMode = 'edit'"
              :disabled="domainEditMode === 'edit'"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 20h4l10-10-4-4L4 16v4Z" />
                <path d="M13 6l4 4" />
              </svg>
            </button>
            <button
              v-if="editDomain.open"
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--delete"
              type="button"
              aria-label="Удалить"
              title="Удалить"
              @click="deleteDomain(editDomain.original)"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 6h14M9 6V4h6v2M7 6l1 14h8l1-14" />
              </svg>
            </button>
            <button
              v-else
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save"
              @click="createDomain"
              :disabled="catalogsLoading"
              aria-label="Добавить домен"
              title="Добавить домен"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 4h12l4 4v12H4z" />
                <path d="M7 4v6h8V4" />
                <path d="M7 20v-6h10v6" />
              </svg>
            </button>
            <button
              class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close"
              type="button"
              aria-label="Закрыть"
              title="Закрыть"
              @click="closeDomainModal"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 6l12 12M18 6l-12 12" />
              </svg>
            </button>
          </div>
        </div>
        <div class="modal__body" :class="{ 'modal__body--locked': catalogsLoading }">
          <div v-if="catalogsLoading" class="modal__body-overlay">
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
          <div v-if="editDomain.open" class="form form--stack form--compact">
            <label class="field">
              <span class="label">Домен</span>
              <input v-model.trim="editDomain.name" class="input" placeholder="example.com" :readonly="domainEditMode === 'view'" />
            </label>
            <div class="toolbar-actions"></div>
          </div>
          <div v-else class="form form--stack form--compact">
            <label class="field">
              <span class="label">Новый домен</span>
              <input v-model.trim="newDomain" class="input" placeholder="example.com" />
            </label>
          </div>
        </div>
      </div>
    </div>
  </teleport>

  <teleport to="body">
    <div
      v-if="showSourceForm || editSource.open"
      class="work-page work-modal-root modal-backdrop"
      @click.self="closeSourceModal"
    >
      <div :ref="modalRef" class="modal modal--auto" :style="modalStyle">
        <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
          <h3>{{ editSource.open ? (sourceEditMode === 'edit' ? 'Редактирование источника' : 'Источник') : 'Новый источник' }}</h3>
          <div class="toolbar-actions">
            <button
              v-if="editSource.open && sourceEditMode === 'edit'"
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save"
              @click="saveEditSource"
              :disabled="catalogsLoading"
              aria-label="Сохранить"
              title="Сохранить"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 4h12l4 4v12H4z" />
                <path d="M7 4v6h8V4" />
                <path d="M7 20v-6h10v6" />
              </svg>
            </button>
            <button
              v-if="editSource.open"
              class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--edit"
              type="button"
              aria-label="Редактировать"
              title="Редактировать"
              @click="sourceEditMode = 'edit'"
              :disabled="sourceEditMode === 'edit'"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 20h4l10-10-4-4L4 16v4Z" />
                <path d="M13 6l4 4" />
              </svg>
            </button>
            <button
              v-if="editSource.open"
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--delete"
              type="button"
              aria-label="Удалить"
              title="Удалить"
              @click="deleteSource(editSource.source_id)"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 6h14M9 6V4h6v2M7 6l1 14h8l1-14" />
              </svg>
            </button>
            <button
              v-else
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save"
              @click="createSource"
              :disabled="catalogsLoading"
              aria-label="Добавить источник"
              title="Добавить источник"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 4h12l4 4v12H4z" />
                <path d="M7 4v6h8V4" />
                <path d="M7 20v-6h10v6" />
              </svg>
            </button>
            <button
              class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close"
              type="button"
              aria-label="Закрыть"
              title="Закрыть"
              @click="closeSourceModal"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 6l12 12M18 6l-12 12" />
              </svg>
            </button>
          </div>
        </div>
        <div class="modal__body" :class="{ 'modal__body--locked': catalogsLoading }">
          <div v-if="catalogsLoading" class="modal__body-overlay">
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
          <div v-if="editSource.open" class="form form--stack form--compact">
            <label class="field">
              <span class="label">Код</span>
              <input v-model.trim="editSource.code" class="input" :readonly="sourceEditMode === 'view'" />
            </label>
            <label class="field">
              <span class="label">Название</span>
              <input v-model.trim="editSource.name" class="input" :readonly="sourceEditMode === 'view'" />
            </label>
            <div class="toolbar-actions"></div>
          </div>
          <div v-else class="form form--stack form--compact">
            <label class="field">
              <span class="label">Источник (код)</span>
              <input v-model.trim="newSource.code" class="input" placeholder="tg" />
            </label>
            <label class="field">
              <span class="label">Источник (название)</span>
              <input v-model.trim="newSource.name" class="input" placeholder="Telegram" />
            </label>
          </div>
        </div>
      </div>
    </div>
  </teleport>

  <teleport to="body">
    <div
      v-if="showMessengerForm || editMessenger.open"
      class="work-page work-modal-root modal-backdrop"
      @click.self="closeMessengerModal"
    >
      <div :ref="modalRef" class="modal modal--auto" :style="modalStyle">
        <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
          <h3>{{ editMessenger.open ? (messengerEditMode === 'edit' ? 'Редактирование мессенджера' : 'Мессенджер') : 'Новый мессенджер' }}</h3>
          <div class="toolbar-actions">
            <button
              v-if="editMessenger.open && messengerEditMode === 'edit'"
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save"
              @click="saveEditMessenger"
              :disabled="catalogsLoading"
              aria-label="Сохранить"
              title="Сохранить"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 4h12l4 4v12H4z" />
                <path d="M7 4v6h8V4" />
                <path d="M7 20v-6h10v6" />
              </svg>
            </button>
            <button
              v-if="editMessenger.open"
              class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--edit"
              type="button"
              aria-label="Редактировать"
              title="Редактировать"
              @click="messengerEditMode = 'edit'"
              :disabled="messengerEditMode === 'edit'"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 20h4l10-10-4-4L4 16v4Z" />
                <path d="M13 6l4 4" />
              </svg>
            </button>
            <button
              v-if="editMessenger.open"
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--delete"
              type="button"
              aria-label="Удалить"
              title="Удалить"
              @click="deleteMessenger(editMessenger.messenger_id)"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 6h14M9 6V4h6v2M7 6l1 14h8l1-14" />
              </svg>
            </button>
            <button
              v-else
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save"
              @click="createMessenger"
              :disabled="catalogsLoading"
              aria-label="Добавить мессенджер"
              title="Добавить мессенджер"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 4h12l4 4v12H4z" />
                <path d="M7 4v6h8V4" />
                <path d="M7 20v-6h10v6" />
              </svg>
            </button>
            <button
              class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close"
              type="button"
              aria-label="Закрыть"
              title="Закрыть"
              @click="closeMessengerModal"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 6l12 12M18 6l-12 12" />
              </svg>
            </button>
          </div>
        </div>
        <div class="modal__body" :class="{ 'modal__body--locked': catalogsLoading }">
          <div v-if="catalogsLoading" class="modal__body-overlay">
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
          <div v-if="editMessenger.open" class="form form--stack form--compact">
            <label class="field">
              <span class="label">Код</span>
              <input v-model.trim="editMessenger.code" class="input" :readonly="messengerEditMode === 'view'" />
            </label>
            <label class="field">
              <span class="label">Название</span>
              <input v-model.trim="editMessenger.name" class="input" :readonly="messengerEditMode === 'view'" />
            </label>
            <div class="toolbar-actions"></div>
          </div>
          <div v-else class="form form--stack form--compact">
            <label class="field">
              <span class="label">Мессенджер (код)</span>
              <input v-model.trim="newMessenger.code" class="input" placeholder="wa" />
            </label>
            <label class="field">
              <span class="label">Мессенджер (название)</span>
              <input v-model.trim="newMessenger.name" class="input" placeholder="WhatsApp" />
            </label>
          </div>
        </div>
      </div>
    </div>
  </teleport>

  <teleport to="body">
    <div
      v-if="showPlatformForm || editPlatform.open"
      class="work-page work-modal-root modal-backdrop"
      @click.self="closePlatformModal"
    >
      <div :ref="modalRef" class="modal modal--auto" :style="modalStyle">
        <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
          <h3>{{ editPlatform.open ? (platformEditMode === 'edit' ? 'Редактирование платформы' : 'Платформа') : 'Новая платформа' }}</h3>
          <div class="toolbar-actions">
            <button
              v-if="editPlatform.open && platformEditMode === 'edit'"
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save"
              @click="saveEditPlatform"
              :disabled="catalogsLoading"
              aria-label="Сохранить"
              title="Сохранить"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 4h12l4 4v12H4z" />
                <path d="M7 4v6h8V4" />
                <path d="M7 20v-6h10v6" />
              </svg>
            </button>
            <button
              v-if="editPlatform.open"
              class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--edit"
              type="button"
              aria-label="Редактировать"
              title="Редактировать"
              @click="platformEditMode = 'edit'"
              :disabled="platformEditMode === 'edit'"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 20h4l10-10-4-4L4 16v4Z" />
                <path d="M13 6l4 4" />
              </svg>
            </button>
            <button
              v-if="editPlatform.open"
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--delete"
              type="button"
              aria-label="Удалить"
              title="Удалить"
              @click="deletePlatform(editPlatform.code)"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 6h14M9 6V4h6v2M7 6l1 14h8l1-14" />
              </svg>
            </button>
            <button
              v-else
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save"
              @click="createPlatform"
              :disabled="catalogsLoading"
              aria-label="Добавить платформу"
              title="Добавить платформу"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 4h12l4 4v12H4z" />
                <path d="M7 4v6h8V4" />
                <path d="M7 20v-6h10v6" />
              </svg>
            </button>
            <button
              class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close"
              type="button"
              aria-label="Закрыть"
              title="Закрыть"
              @click="closePlatformModal"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 6l12 12M18 6l-12 12" />
              </svg>
            </button>
          </div>
        </div>
        <div class="modal__body" :class="{ 'modal__body--locked': catalogsLoading }">
          <div v-if="catalogsLoading" class="modal__body-overlay">
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
          <div v-if="editPlatform.open" class="form form--stack form--compact">
            <label class="field">
              <span class="label">Код</span>
              <input v-model.trim="editPlatform.code" class="input" disabled />
            </label>
            <label class="field">
              <span class="label">Название</span>
              <input v-model.trim="editPlatform.name" class="input" :readonly="platformEditMode === 'view'" />
            </label>
            <label class="field">
              <span class="label">Слотов на аккаунт</span>
              <input v-model.number="editPlatform.slot_capacity" class="input" type="number" min="0" :readonly="platformEditMode === 'view'" />
            </label>
            <div class="toolbar-actions"></div>
          </div>
          <div v-else class="form form--stack form--compact">
            <label class="field">
              <span class="label">Платформа (код)</span>
              <input v-model.trim="newPlatform.code" class="input" placeholder="steam" />
            </label>
            <label class="field">
              <span class="label">Платформа (название)</span>
              <input v-model.trim="newPlatform.name" class="input" placeholder="Steam" />
            </label>
            <label class="field">
              <span class="label">Слотов на аккаунт</span>
              <input v-model.number="newPlatform.slot_capacity" class="input" type="number" min="0" />
            </label>
          </div>
        </div>
      </div>
    </div>
  </teleport>

  <teleport to="body">
    <div
      v-if="showRegionForm || editRegion.open"
      class="work-page work-modal-root modal-backdrop"
      @click.self="closeRegionModal"
    >
      <div :ref="modalRef" class="modal modal--auto" :style="modalStyle">
        <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
          <h3>{{ editRegion.open ? (regionEditMode === 'edit' ? 'Редактирование региона' : 'Регион') : 'Новый регион' }}</h3>
          <div class="toolbar-actions">
            <button
              v-if="editRegion.open && regionEditMode === 'edit'"
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save"
              @click="saveEditRegion"
              :disabled="catalogsLoading"
              aria-label="Сохранить"
              title="Сохранить"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 4h12l4 4v12H4z" />
                <path d="M7 4v6h8V4" />
                <path d="M7 20v-6h10v6" />
              </svg>
            </button>
            <button
              v-if="editRegion.open"
              class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--edit"
              type="button"
              aria-label="Редактировать"
              title="Редактировать"
              @click="regionEditMode = 'edit'"
              :disabled="regionEditMode === 'edit'"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 20h4l10-10-4-4L4 16v4Z" />
                <path d="M13 6l4 4" />
              </svg>
            </button>
            <button
              v-if="editRegion.open"
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--delete"
              type="button"
              aria-label="Удалить"
              title="Удалить"
              @click="deleteRegion(editRegion.code)"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 6h14M9 6V4h6v2M7 6l1 14h8l1-14" />
              </svg>
            </button>
            <button
              v-else
              class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save"
              @click="createRegion"
              :disabled="catalogsLoading"
              aria-label="Добавить регион"
              title="Добавить регион"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 4h12l4 4v12H4z" />
                <path d="M7 4v6h8V4" />
                <path d="M7 20v-6h10v6" />
              </svg>
            </button>
            <button
              class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close"
              type="button"
              aria-label="Закрыть"
              title="Закрыть"
              @click="closeRegionModal"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 6l12 12M18 6l-12 12" />
              </svg>
            </button>
          </div>
        </div>
        <div class="modal__body" :class="{ 'modal__body--locked': catalogsLoading }">
          <div v-if="catalogsLoading" class="modal__body-overlay">
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
          <div v-if="editRegion.open" class="form form--stack form--compact">
            <label class="field">
              <span class="label">Код</span>
              <input v-model.trim="editRegion.code" class="input" disabled />
            </label>
            <label class="field">
              <span class="label">Название</span>
              <input v-model.trim="editRegion.name" class="input" :readonly="regionEditMode === 'view'" />
            </label>
            <label v-if="isAdmin" class="field">
              <span class="label">Коэф. закупа (RUB)</span>
              <input v-model.number="editRegion.purchase_cost_rate" class="input" type="number" step="0.0001" min="0" :readonly="regionEditMode === 'view'" />
            </label>
            <div class="toolbar-actions"></div>
          </div>
          <div v-else class="form form--stack form--compact">
            <label class="field">
              <span class="label">Регион (код)</span>
              <input v-model.trim="newRegion.code" class="input" placeholder="RU" />
            </label>
            <label class="field">
              <span class="label">Регион (название)</span>
              <input v-model.trim="newRegion.name" class="input" placeholder="Russia" />
            </label>
            <label v-if="isAdmin" class="field">
              <span class="label">Коэф. закупа (RUB)</span>
              <input v-model.number="newRegion.purchase_cost_rate" class="input" type="number" step="0.0001" min="0" />
            </label>
          </div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { reactive, toRefs } from 'vue'

// Передаем один объект, чтобы не держать десятки отдельных props.
const props = defineProps({
  ctx: { type: Object, required: true },
})
const ctx = reactive(props.ctx)

const {
  showDomainForm,
  editDomain,
  closeDomainModal,
  modalRef,
  modalStyle,
  startModalDrag,
  domainEditMode,
  saveEditDomain,
  catalogsLoading,
  deleteDomain,
  createDomain,
  newDomain,
  showSourceForm,
  editSource,
  closeSourceModal,
  sourceEditMode,
  saveEditSource,
  deleteSource,
  createSource,
  newSource,
  showMessengerForm,
  editMessenger,
  closeMessengerModal,
  messengerEditMode,
  saveEditMessenger,
  deleteMessenger,
  createMessenger,
  newMessenger,
  showPlatformForm,
  editPlatform,
  closePlatformModal,
  platformEditMode,
  saveEditPlatform,
  deletePlatform,
  createPlatform,
  newPlatform,
  showRegionForm,
  editRegion,
  closeRegionModal,
  regionEditMode,
  saveEditRegion,
  deleteRegion,
  createRegion,
  newRegion,
  isAdmin,
} = toRefs(ctx)
</script>
