export function airpayCents(value) {
  // Считаем итоги в копейках и отклоняем неизвестные, отрицательные и неточные суммы.
  const text = String(value ?? '')
  if (!/^\d{1,9}(?:\.\d{1,2})?$/.test(text)) return null
  const [units, fraction = ''] = text.split('.')
  const cents = Number(units) * 100 + Number(fraction.padEnd(2, '0'))
  return cents > 0 ? cents : null
}

export function invoiceSelection(invoice, selected, amounts, readings) {
  // Итог включает только отмеченные услуги; ограничения и показания проверяем до подтверждения.
  const rows = []
  for (const index of selected) {
    const item = invoice?.services?.[index]
    const cents = airpayCents(amounts[index])
    if (!item?.subServiceId || !cents) return { error: 'Укажите сумму для каждой выбранной услуги.' }
    const min = airpayCents(item.data?.minSum)
    const max = airpayCents(item.data?.maxSum)
    if ((min && cents < min) || (max && cents > max)) return { error: 'Сумма услуги выходит за ограничения поставщика.' }
    if (item.data?.isMeter) {
      const reading = String(readings[index] ?? '')
      if (!/^\d+(?:\.\d+)?$/.test(reading) || !Number.isFinite(Number(reading)) || Number(reading) < Number(item.data?.prevCount || 0)) {
        return { error: 'Укажите показания не меньше предыдущих.' }
      }
    }
    rows.push({ title: item.subServiceName || item.subServiceId, cents, reading: item.data?.isMeter ? readings[index] : null })
  }
  if (!invoice?.invoiceId || !rows.length) return { error: 'Выберите квитанцию и хотя бы одну услугу.' }
  return { rows, cents: rows.reduce((sum, row) => sum + row.cents, 0) }
}
