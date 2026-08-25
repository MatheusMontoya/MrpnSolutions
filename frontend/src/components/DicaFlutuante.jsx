import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'

/* Balão com o nome da seção, para quando a barra está só com ícones.
 *
 * Por que em portal e não um ::after no próprio item: .sidebar-nav tem
 * overflow-y: auto, e no CSS quando um eixo é auto o outro deixa de ser
 * visible — um pseudo-elemento seria cortado na borda da barra. Renderizar
 * fora, em position: fixed, com a posição medida do item, é imune a isso.
 *
 * Um balão só para a barra inteira: os eventos são delegados no <aside>, então
 * não há um listener por item nem estado que cresça com o número de telas.
 */
export default function DicaFlutuante({ alvo }) {
  const [posicao, setPosicao] = useState(null)

  useEffect(() => {
    if (!alvo) { setPosicao(null); return }
    const r = alvo.getBoundingClientRect()
    // ancora na borda da BARRA, não na do item: o item tem o padding do nav
    // dentro dele, e usar a borda dele faria o balão encostar/sobrepor a barra
    const barra = alvo.closest('.sidebar')?.getBoundingClientRect()
    setPosicao({
      topo: r.top + r.height / 2,
      esquerda: (barra ? barra.right : r.right) + 10,
    })
  }, [alvo])

  if (!alvo || !posicao) return null
  const texto = alvo.dataset.dica
  if (!texto) return null

  return createPortal(
    <span
      className="dica-flutuante"
      role="tooltip"
      style={{ top: posicao.topo, left: posicao.esquerda }}
    >
      {texto}
    </span>,
    document.body,
  )
}
