import { computed, ref } from 'vue'
import { describe, expect, it } from 'vitest'
import { buildResponsibleUserOptions } from '../responsibleUsers'

describe('responsible user options', () => {
  it('keeps an employee visible after promotion from manager to admin', () => {
    // Фильтр и форма получают один справочник, который не теряет имя после смены роли.
    const users = ref([{ name: 'Валерия', role: 'manager' }])
    const options = computed(() => buildResponsibleUserOptions(users.value))
    expect(options.value).toEqual(['Валерия'])
    users.value[0].role = 'admin'
    expect(options.value).toEqual(['Валерия'])
  })

  it.each([false, true])('includes admins and preserves owner visibility: %s', (canViewOwner) => {
    // Доступность имени администратора не открывает владельца обычным сотрудникам.
    const users = [
      { name: 'Оператор', role: 'operator' },
      { name: 'Валерия', role: ' ADMIN ' },
      { name: 'Владелец', role: 'owner' },
    ]
    expect(buildResponsibleUserOptions(users, { canViewOwner })).toEqual(
      canViewOwner ? ['Оператор', 'Валерия', 'Владелец'] : ['Оператор', 'Валерия'],
    )
  })

  it('keeps name normalization, deduplication and the current-user fallback', () => {
    // Текущий сотрудник остаётся доступен при неполном справочнике без дублей имени.
    expect(buildResponsibleUserOptions([
      { name: ' Валерия ', role: 'admin' },
      { name: 'валерия', role: 'manager' },
      { name: '', role: 'admin' },
    ], { currentUserName: 'Александр' })).toEqual(['Валерия', 'Александр'])
  })
})
