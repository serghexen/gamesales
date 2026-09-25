import { apiGet } from '../../api/http'

export async function resolveAirpayJob(response, { token, active = () => true, progress = () => {} } = {}) {
  // Опрос читает только сохранённое задание; ни pay, ни check при чтении не повторяются.
  const deadline = Date.now() + 120000
  let value = response
  while (value?.job) {
    const job = value.job
    progress(job)
    if (job.state === 'succeeded') return job.result
    if (job.state === 'failed') throw Object.assign(new Error(job.error || 'Действие Airpay прервано'), { status: job.error_status })
    await new Promise(resolve => setTimeout(resolve, 1000))
    if (!active()) throw Object.assign(new Error('Просмотр закрыт; результат сохранится в истории'), { cancelled: true })
    const remaining = deadline - Date.now()
    if (remaining <= 0) throw new Error('Ожидание затянулось. Обновите покупку позже или проверьте очередь в истории; задание не отменено.')
    let timer
    try {
      // Долгий GET тоже ограничен: потеря связи не должна навсегда блокировать окно.
      value = await Promise.race([
        apiGet(`/integrations/airpay/jobs/${encodeURIComponent(job.job_id)}`, { token }),
        new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('Нет ответа очереди. Обновите сохранённую покупку; задание не отменено.')), Math.min(15000, remaining)) }),
      ])
    } finally { clearTimeout(timer) }
  }
  return value
}
