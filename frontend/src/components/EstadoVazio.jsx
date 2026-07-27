import Icone from './Icone'

/** Estado vazio composto (ícone em círculo, título, descrição, ação). */
export default function EstadoVazio({ icone, titulo, descricao, acao, barras = true }) {
  return (
    <div className="card estado-vazio">
      <div className="ev-icone"><Icone d={icone} size={26} strokeWidth={1.75} /></div>
      <h3 className="ev-titulo">{titulo}</h3>
      <p className="ev-descricao">{descricao}</p>
      {barras && (
        <div className="ev-barras" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, i) => <span key={i} />)}
        </div>
      )}
      {acao && <div className="ev-acao">{acao}</div>}
    </div>
  )
}
