export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

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
    throw new Error(await parseError(res, `POST ${path} failed: ${res.status}`))
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
    throw new Error(await parseError(res, `DELETE ${path} failed: ${res.status}`))
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
    throw new Error(await parseError(res, `PUT ${path} failed: ${res.status}`))
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
    throw new Error(await parseError(res, `POST ${path} failed: ${res.status}`))
  }
  if (res.status === 204) return null
  return res.json()
}

export async function apiGetFile(path, { token } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
  if (!res.ok) {
    throw new Error(await parseError(res, `GET ${path} failed: ${res.status}`))
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
          reject(new Error(data?.detail || `POST ${path} failed: ${xhr.status}`))
        } catch {
          reject(new Error(`POST ${path} failed: ${xhr.status}`))
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
    xhr.onerror = () => reject(new Error(`POST ${path} failed: network error`))
    xhr.send(formData)
  })
}
