import { createContext, useContext, useState } from 'react'
import { api } from './api'

/* Sessão autenticada: guarda o TOKEN da API (Authorization: Bearer em toda
 * chamada, via api.js) + perfil/nome/consultorId para a UI. Persistida em
 * localStorage para sobreviver a refresh; sair() revoga o token no servidor. */
const Ctx = createContext(null)
const CHAVE = 'psa-sap-sessao'

function carregar() {
  try {
    const s = JSON.parse(localStorage.getItem(CHAVE)) || null
    return s?.token ? s : null // sessões antigas (sem token) não valem mais
  } catch {
    return null
  }
}

export function SessaoProvider({ children }) {
  const [sessao, setSessao] = useState(carregar)

  const entrar = (nova) => {
    localStorage.setItem(CHAVE, JSON.stringify(nova))
    setSessao(nova)
  }
  const sair = () => {
    api.post('/auth/logout', {}).catch(() => {}) // revoga no servidor; falha não bloqueia
    localStorage.removeItem(CHAVE)
    setSessao(null)
  }

  return <Ctx.Provider value={{ sessao, entrar, sair }}>{children}</Ctx.Provider>
}

// { token, perfil: 'ceo'|'rh'|'consultor', nome: string, consultorId: number|null }
export const useSessao = () => useContext(Ctx)
