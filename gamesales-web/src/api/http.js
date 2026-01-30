const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function parseError(res, fallback) {
  try {
    const data = await res.json()
    if (data?.detail) return String(data.detail)
  } catch {
    // ignore parse errors
  }
  return fallback
}

export async function apiGet(path, { token } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
  if (!res.ok) {
    throw new Error(await parseError(res, `GET ${path} failed: ${res.status}`))
  }
  return res.json()
}

export async function apiPost(path, body, { token } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    throw new Error(await parseError(res, `POST ${path} failed: ${res.status}`))
  }
  return res.json()
}

export async function apiDelete(path, { token } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
  if (!res.ok) {
    throw new Error(await parseError(res, `DELETE ${path} failed: ${res.status}`))
  }
  return res.json()
}

export async function apiPut(path, body, { token } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    throw new Error(await parseError(res, `PUT ${path} failed: ${res.status}`))
  }
  return res.json()
}
