export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

function makeHttpError(message, status) {
  const err = new Error(message)
  err.status = status
  return err
}

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
    throw makeHttpError(await parseError(res, `GET ${path} failed: ${res.status}`), res.status)
  }
  if (res.status === 204) return null
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
    throw makeHttpError(await parseError(res, `POST ${path} failed: ${res.status}`), res.status)
  }
  if (res.status === 204) return null
  return res.json()
}

export async function apiDelete(path, { token } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
  if (!res.ok) {
    throw makeHttpError(await parseError(res, `DELETE ${path} failed: ${res.status}`), res.status)
  }
  if (res.status === 204) return null
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
    throw makeHttpError(await parseError(res, `PUT ${path} failed: ${res.status}`), res.status)
  }
  if (res.status === 204) return null
  return res.json()
}

export async function apiPostForm(path, formData, { token } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  })
  if (!res.ok) {
    throw makeHttpError(await parseError(res, `POST ${path} failed: ${res.status}`), res.status)
  }
  if (res.status === 204) return null
  return res.json()
}

export async function apiGetFile(path, { token } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
  if (!res.ok) {
    throw makeHttpError(await parseError(res, `GET ${path} failed: ${res.status}`), res.status)
  }
  return res.blob()
}

export function apiPostFormWithProgress(path, formData, { token, onProgress } = {}) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE}${path}`, true)
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    }
    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable) return
      const percent = Math.round((event.loaded / event.total) * 100)
      if (onProgress) onProgress(percent)
    }
    xhr.onload = () => {
      if (xhr.status < 200 || xhr.status >= 300) {
        try {
          const data = JSON.parse(xhr.responseText)
          reject(makeHttpError(data?.detail || `POST ${path} failed: ${xhr.status}`, xhr.status))
        } catch {
          reject(makeHttpError(`POST ${path} failed: ${xhr.status}`, xhr.status))
        }
        return
      }
      if (xhr.status === 204) {
        resolve(null)
        return
      }
      try {
        resolve(JSON.parse(xhr.responseText))
      } catch {
        resolve({})
      }
    }
    xhr.onerror = () => reject(makeHttpError(`POST ${path} failed: network error`, 0))
    xhr.send(formData)
  })
}
