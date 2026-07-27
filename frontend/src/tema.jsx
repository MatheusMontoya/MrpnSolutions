import { createContext, useContext, useEffect, useState } from 'react'

/* Tema da interface: 'claro' (oficial/padrão), 'escuro' ou 'sistema' (segue o SO).
 * A escolha vive no localStorage e é aplicada como data-tema no <html>,
 * onde o bloco de tokens do CSS assume o resto. */
const Ctx = createContext(null)
const CHAVE = 'mrpn-tema'

const preferenciaDoSistema = () =>
  window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'escuro' : 'claro'

function carregar() {
  const salvo = localStorage.getItem(CHAVE)
  // CLARO é o tema oficial do produto: quem nunca escolheu vê o claro,
  // mesmo que o sistema operacional esteja no escuro.
  return ['claro', 'escuro', 'sistema'].includes(salvo) ? salvo : 'claro'
}

export function TemaProvider({ children }) {
  const [preferencia, setPreferencia] = useState(carregar)
  const [doSistema, setDoSistema] = useState(preferenciaDoSistema)

  // acompanha a troca de tema do SO enquanto a preferência for 'sistema'
  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-color-scheme: dark)')
    if (!mq) return
    const ouvir = (e) => setDoSistema(e.matches ? 'escuro' : 'claro')
    mq.addEventListener('change', ouvir)
    return () => mq.removeEventListener('change', ouvir)
  }, [])

  const efetivo = preferencia === 'sistema' ? doSistema : preferencia

  useEffect(() => {
    document.documentElement.dataset.tema = efetivo
    // a barra do navegador/PWA acompanha o chrome do app
    const meta = document.querySelector('meta[name="theme-color"]')
    if (meta) meta.setAttribute('content', efetivo === 'escuro' ? '#0a1020' : '#0b2154')
  }, [efetivo])

  const escolher = (nova) => {
    localStorage.setItem(CHAVE, nova)
    setPreferencia(nova)
  }

  return <Ctx.Provider value={{ preferencia, efetivo, escolher }}>{children}</Ctx.Provider>
}

export const useTema = () => useContext(Ctx)
