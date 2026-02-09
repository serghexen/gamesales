export function createDeferredCall(name) {
  let impl = null

  // Привязывает реальную функцию, когда нужный модуль уже инициализирован.
  const set = (fn) => {
    impl = fn
  }

  // Безопасный вызов: до инициализации бросаем понятную ошибку.
  const call = (...args) => {
    if (!impl) throw new Error(`${name} is called before initialization`)
    return impl(...args)
  }

  return {
    set,
    call,
  }
}
