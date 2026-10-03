import api from './api.js'

export async function fetchMe() {
  try {
    const res = await api.get('/api/me')
    if (!res.data?.ok || typeof res.data.username !== 'string' || !res.data.username) {
      return null
    }
    return {
      username: res.data.username,
      loggedInAt: res.data.loggedInAt || '',
    }
  } catch {
    return null
  }
}

export async function logout() {
  await api.post('/api/logout')
}
