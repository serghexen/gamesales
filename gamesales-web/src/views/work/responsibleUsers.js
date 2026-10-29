export function buildResponsibleUserOptions(users, { canViewOwner = false, currentUserName = '' } = {}) {
  // Повышение до администратора не убирает сотрудника из ответственных; владельца показываем по прежнему правилу.
  const seen = new Set()
  const options = []
  const pushName = (rawName, roleCode = '') => {
    // Убираем пустые имена и повторы, сохраняя привычный порядок справочника.
    const name = String(rawName || '').trim()
    const role = String(roleCode || '').trim().toLowerCase()
    const key = name.toLowerCase()
    if (!name || seen.has(key) || (!canViewOwner && role === 'owner')) return
    seen.add(key)
    options.push(name)
  }
  for (const user of users) pushName(user?.name, user?.role)
  pushName(currentUserName)
  return options
}
