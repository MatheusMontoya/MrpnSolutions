import { createContext, useContext, useEffect, useState } from 'react'

/* Densidade da barra lateral: 'expandida' (ícone + texto), 'recolhida' (só
 * ícone) ou 'auto' (segue a largura da janela). Espelha tema.jsx de propósito —
 * mesma forma de guardar, mesma forma de aplicar — porque é a mesma natureza de
 * coisa: preferência de interface que precisa sobreviver ao recarregar.
 *
 * Só o valor EFETIVO vai para o <html data-sidebar>, e é isso que permite ao
 * CSS ter um bloco só em vez de repetir as regras do trilho dentro da media
 * query. */
const Ctx = createContext(null)
const CHAVE = 'mrpn-sidebar'
const ESTREITA = '(max-width: 1180px)'

const cabeExpandida = () => !window.matchMedia?.(ESTREITA).matches

function carregar() {
  const salvo = localStorage.getItem(CHAVE)
  // 'auto' é o análogo do 'sistema' do tema: quem nunca tocou no puxador
  // continua vendo exatamente o comportamento de antes, inclusive reagindo a
  // redimensionar a janela.
  return ['expandida', 'recolhida', 'auto'].includes(salvo) ? salvo : 'auto'
}

export function SidebarProvider({ children }) {
  const [preferencia, setPreferencia] = useState(carregar)
  const [temEspaco, setTemEspaco] = useState(cabeExpandida)

  useEffect(() => {
    const mq = window.matchMedia?.(ESTREITA)
    if (!mq) return
    const ouvir = (e) => setTemEspaco(!e.matches)
    mq.addEventListener('change', ouvir)
    return () => mq.removeEventListener('change', ouvir)
  }, [])

  const efetiva = preferencia === 'auto'
    ? (temEspaco ? 'expandida' : 'recolhida')
    : preferencia

  useEffect(() => {
    document.documentElement.dataset.sidebar = efetiva
  }, [efetiva])

  // escrita antes do estado, como em tema.jsx: um useEffect de gravação
  // reescreveria a chave a cada remontagem do Shell (que desmonta no logout)
  const alternar = () => {
    const nova = efetiva === 'expandida' ? 'recolhida' : 'expandida'
    localStorage.setItem(CHAVE, nova)
    setPreferencia(nova)
  }

  return <Ctx.Provider value={{ efetiva, alternar }}>{children}</Ctx.Provider>
}

export const useSidebar = () => useContext(Ctx)
