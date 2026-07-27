const CHAVE_SESSAO = 'psa-sap-sessao'

function tokenAtual() {
  try {
    return JSON.parse(localStorage.getItem(CHAVE_SESSAO))?.token ?? null
  } catch {
    return null
  }
}

async function req(path, options = {}) {
  const token = tokenAtual()
  const res = await fetch(`/api${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...options,
  })
  // sessão expirada/revogada: limpa e volta ao login (exceto no próprio login)
  if (res.status === 401 && path !== '/auth/login') {
    localStorage.removeItem(CHAVE_SESSAO)
    if (!window.location.pathname.startsWith('/login')) {
      window.location.href = '/login'
    }
    throw new Error('Sessão expirada — entre novamente')
  }
  if (!res.ok) {
    let msg = `Erro ${res.status}`
    try {
      const body = await res.json()
      if (body.detail) msg = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch { /* mantém msg default */ }
    throw new Error(msg)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  get: (path) => req(path),
  post: (path, body) => req(path, { method: 'POST', body: JSON.stringify(body) }),
  patch: (path, body) => req(path, { method: 'PATCH', body: JSON.stringify(body) }),
  del: (path) => req(path, { method: 'DELETE' }),
}

/** Baixa um arquivo autenticado (o token vai no header — link direto não serve). */
export async function baixarArquivo(path, nomeArquivo) {
  const token = tokenAtual()
  const res = await fetch(`/api${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error(`Erro ${res.status} ao exportar`)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = nomeArquivo
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
