<template>
  <section class="panel panel--wide">
    <div class="panel__head">
      <div>
        <h2>Профиль</h2>
        <p class="muted">Сменить пароль текущего пользователя.</p>
      </div>
      <div class="toolbar-actions">
        <button
          v-if="ctx.isAdmin"
          class="btn btn--icon btn--glow btn--glow-add"
          title="Пользователи"
          aria-label="Пользователи"
          @click="ctx.setActiveTab('users')"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M16 11a4 4 0 1 0-4-4 4 4 0 0 0 4 4Z" />
            <path d="M8 11a3 3 0 1 0-3-3 3 3 0 0 0 3 3Z" />
            <path d="M2 20a6 6 0 0 1 12 0" />
            <path d="M14 20a5 5 0 0 1 8 0" />
          </svg>
        </button>
        <button
          class="btn btn--icon btn--glow btn--glow-eye"
          title="Сменить пароль"
          aria-label="Сменить пароль"
          @click="ctx.openPwdModal"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M7 10a5 5 0 0 1 10 0v4a5 5 0 0 1-10 0v-4Z" />
            <path d="M9 10V8a3 3 0 0 1 6 0v2" />
          </svg>
        </button>
      </div>
    </div>
    <div class="panel__body">
      <p class="muted">Нажмите иконку, чтобы открыть форму смены пароля.</p>
      <teleport to="body">
        <div v-if="ctx.showPwdForm" class="work-page work-modal-root modal-backdrop" @click.self="ctx.closePwdModal">
          <div :ref="ctx.modalRef" class="modal modal--auto" :style="ctx.modalStyle">
            <div class="panel__head panel__head--tight modal__head" @mousedown="ctx.startModalDrag">
              <h3>Смена пароля</h3>
              <button
                class="btn btn--icon-plain"
                type="button"
                aria-label="Закрыть"
                title="Закрыть"
                @click="ctx.closePwdModal"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M6 6l12 12M18 6l-12 12" />
                </svg>
              </button>
            </div>
            <div class="modal__body" :class="{ 'modal__body--locked': ctx.pwdLoading }">
              <div v-if="ctx.pwdLoading" class="modal__body-overlay">
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
              <div class="form form--stack form--compact">
                <label class="field">
                  <span class="label">Текущий пароль</span>
                  <input v-model="ctx.pwdForm.current" class="input" type="password" />
                </label>
                <label class="field">
                  <span class="label">Новый пароль</span>
                  <input v-model="ctx.pwdForm.next" class="input" type="password" />
                </label>
                <label class="field">
                  <span class="label">Повторите пароль</span>
                  <input v-model="ctx.pwdForm.next2" class="input" type="password" />
                </label>
                <p v-if="ctx.pwdError" class="bad">{{ ctx.pwdError }}</p>
                <p v-if="ctx.pwdOk" class="ok">Пароль обновлён</p>
                <div class="toolbar-actions import-actions">
                  <button
                    class="btn btn--icon-plain"
                    :disabled="ctx.pwdLoading"
                    aria-label="Сохранить"
                    title="Сохранить"
                    @click="ctx.changePassword"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M4 4h12l4 4v12H4z" />
                      <path d="M7 4v6h8V4" />
                      <path d="M7 20v-6h10v6" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </teleport>
    </div>
  </section>
</template>

<script setup>
defineProps({
  ctx: { type: Object, required: true },
})
</script>
