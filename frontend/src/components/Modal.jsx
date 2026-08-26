import { useEffect, useRef } from 'react'
import Icone from './Icone'

/* Diálogo modal com foco preso dentro dele.
 *
 * Antes o modal só ouvia Escape: quem navega por teclado continuava tabulando
 * para os links da página ATRÁS do modal, preenchia campos que não estava
 * vendo, e ao fechar o foco voltava para o começo do documento. Três coisas
 * consertadas aqui — levar o foco para dentro ao abrir, prender o Tab no
 * diálogo, e devolver o foco ao elemento que abriu.
 */
export default function Modal({ titulo, larga, extraLarga, icone, classeExtra, onFechar, children, rodape }) {
  const caixa = useRef(null)
  const focoAnterior = useRef(null)

  // `onFechar` chega como arrow inline em quase toda chamada, ou seja: função
  // nova a cada render do pai. Com ela na lista de dependências, o efeito
  // desmontava e remontava a cada tecla digitada no formulário — e a cada volta
  // regravava `focoAnterior` com um elemento de DENTRO do modal, que some
  // quando ele fecha. Resultado: o foco ia parar no <body>. O ref desacopla a
  // identidade da função do ciclo de vida do efeito.
  const fechar = useRef(onFechar)
  fechar.current = onFechar

  // Capturado no RENDER, não no efeito. Vários formulários usam `autoFocus`, e
  // o React aplica isso no commit — antes dos efeitos. Quando o efeito rodava,
  // `document.activeElement` já era o campo de dentro do modal, então "voltar
  // para quem abriu" devolvia o foco a um elemento que sumia junto com o modal,
  // e o navegador jogava tudo no <body>.
  if (focoAnterior.current === null) {
    focoAnterior.current = document.activeElement
  }

  useEffect(() => {
    const focaveis = () => caixa.current?.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ) ?? []

    // O destino do foco é o primeiro CAMPO, não o primeiro focável: em ordem de
    // DOM o "×" de fechar vem antes de tudo, e abrir um formulário com o cursor
    // no botão de desistir é o contrário do que a pessoa veio fazer.
    const campo = caixa.current?.querySelector(
      'input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled])',
    )
    ;(campo ?? focaveis()[0] ?? caixa.current)?.focus?.()

    const tecla = (e) => {
      if (e.key === 'Escape') { fechar.current?.(); return }
      if (e.key !== 'Tab') return
      const lista = [...focaveis()]
      if (!lista.length) return
      const inicio = lista[0]
      const fim = lista[lista.length - 1]
      // circula dentro do diálogo em vez de escapar para a página de trás
      if (e.shiftKey && document.activeElement === inicio) {
        e.preventDefault()
        fim.focus()
      } else if (!e.shiftKey && document.activeElement === fim) {
        e.preventDefault()
        inicio.focus()
      }
    }

    document.addEventListener('keydown', tecla)
    return () => {
      document.removeEventListener('keydown', tecla)
      // Devolve o foco a quem abriu, mas DEPOIS que o DOM assentar: a limpeza
      // do efeito roda antes de o React remover os nós do modal, e o navegador
      // manda o foco para o <body> ao apagar o elemento que o detinha — o que
      // desfaria o nosso focus() se ele acontecesse agora.
      const anterior = focoAnterior.current
      setTimeout(() => {
        if (anterior?.isConnected) anterior.focus?.()
      }, 0)
    }
  }, [])

  const classe = `modal${extraLarga ? ' extra-larga' : larga ? ' larga' : ''}${classeExtra ? ` ${classeExtra}` : ''}`

  return (
    <div className="modal-fundo" onMouseDown={(e) => e.target === e.currentTarget && fechar.current?.()}>
      <div className={classe} role="dialog" aria-modal="true" aria-label={titulo} ref={caixa} tabIndex={-1}>
        <div className="modal-cabecalho">
          {icone && <span className="modal-icone-chip"><Icone d={icone} size={17} /></span>}
          <h3>{titulo}</h3>
          <span className="espacador" />
          <button className="fechar-x" onClick={() => fechar.current?.()} aria-label="Fechar">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
          </button>
        </div>
        <div className="modal-corpo">{children}</div>
        {rodape && <div className="modal-rodape">{rodape}</div>}
      </div>
    </div>
  )
}
