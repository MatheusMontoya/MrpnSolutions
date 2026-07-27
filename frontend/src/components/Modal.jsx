import { useEffect } from 'react'
import Icone from './Icone'

export default function Modal({ titulo, larga, extraLarga, icone, classeExtra, onFechar, children, rodape }) {
  useEffect(() => {
    const esc = (e) => e.key === 'Escape' && onFechar()
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onFechar])

  const classe = `modal${extraLarga ? ' extra-larga' : larga ? ' larga' : ''}${classeExtra ? ` ${classeExtra}` : ''}`

  return (
    <div className="modal-fundo" onMouseDown={(e) => e.target === e.currentTarget && onFechar()}>
      <div className={classe} role="dialog" aria-modal="true" aria-label={titulo}>
        <div className="modal-cabecalho">
          {icone && <span className="modal-icone-chip"><Icone d={icone} size={17} /></span>}
          <h3>{titulo}</h3>
          <span className="espacador" />
          <button className="fechar-x" onClick={onFechar} aria-label="Fechar">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
          </button>
        </div>
        <div className="modal-corpo">{children}</div>
        {rodape && <div className="modal-rodape">{rodape}</div>}
      </div>
    </div>
  )
}
