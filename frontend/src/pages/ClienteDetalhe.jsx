import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import FalhaAoCarregar from '../components/FalhaAoCarregar'
import Icone from '../components/Icone'
import { SkeletonPagina } from '../components/Skeleton'
import { STATUS_PROJETO, corFase, fmtBRL, fmtData, fmtPct, iniciais } from '../format'

const IC_SETA_ESQ = ['M19 12H5', 'M12 19l-7-7 7-7']
const IC_CHEVRON = ['M9 18l6-6-6-6']
const IC_EDITAR = ['M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7', 'M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z']
const IC_TENDENCIA = ['M23 6l-9.5 9.5-5-5L1 18', 'M17 6h6v6']

// dot + rótulo por status do projeto (mesma semântica das demais telas)
const STATUS_COR = { ativo: 'var(--verde)', pausado: 'var(--laranja)', encerrado: 'var(--texto-3)' }

// cor do avatar por hash simples do nome — 3 pares fixos
const PARES_AVATAR = [
  { fundo: 'var(--azul-claro)', cor: 'var(--azul-hover)' },
  { fundo: 'var(--laranja-fundo)', cor: 'var(--laranja)' },
  { fundo: 'var(--verde-fundo)', cor: 'var(--verde)' },
]
const parAvatar = (nome) => {
  let h = 0
  for (const ch of nome || '') h = (h * 31 + ch.charCodeAt(0)) >>> 0
  return PARES_AVATAR[h % PARES_AVATAR.length]
}

export default function ClienteDetalhe() {
  const { id } = useParams()
  const [cliente, setCliente] = useState(null)
  const [erro, setErro] = useState(null)

  useEffect(() => {
    api.get(`/clientes/${id}`).then(setCliente).catch((e) => setErro(e.message))
  }, [id])

  if (erro) return <FalhaAoCarregar erro={erro} aoTentarDeNovo={() => window.location.reload()} />
  if (!cliente) return <SkeletonPagina />

  const par = parAvatar(cliente.nome)

  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <div className="texto-3 linha-flex" style={{ fontSize: 12.5, gap: 6, marginBottom: 12 }}>
            <Link to="/clientes" className="link linha-flex" style={{ gap: 5 }}>
              <Icone d={IC_SETA_ESQ} size={14} strokeWidth={2} />
              Clientes
            </Link>
            <Icone d={IC_CHEVRON} size={13} strokeWidth={2} />
            <span>Detalhes</span>
          </div>
          <div className="linha-flex" style={{ gap: 14 }}>
            <span
              className="avatar-consultor"
              style={{ width: 44, height: 44, borderRadius: 10, fontSize: 15, background: par.fundo, color: par.cor }}
            >
              {iniciais(cliente.nome)}
            </span>
            <h1>{cliente.nome}</h1>
          </div>
          <div className="descricao" style={{ marginTop: 8 }}>
            Contato Principal: {cliente.contato}
          </div>
        </div>
        <button className="botao botao-secundario">
          <Icone d={IC_EDITAR} size={15} />
          Editar
        </button>
      </div>

      <div className="grid-kpi">
        <div className="card kpi">
          <div className="rotulo">Projetos ativos</div>
          <div className="valor">{cliente.projetos_ativos}</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Receita prevista</div>
          <div className="valor">{fmtBRL(cliente.receita_prevista)}</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Receita realizada</div>
          <div className="valor linha-flex" style={{ gap: 6, color: 'var(--verde)' }}>
            {fmtBRL(cliente.receita_realizada)}
            <Icone d={IC_TENDENCIA} size={16} strokeWidth={2} />
          </div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Margem</div>
          <div className="valor" style={{ color: 'var(--azul)' }}>{fmtPct(cliente.margem_pct)}</div>
        </div>
      </div>

      <div className="card">
        <h2 className="card-titulo-secao">Projetos em Andamento</h2>
        <div className="card-corpo" style={{ paddingTop: 14 }}>
          <table className="tabela">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Fase SAP Activate</th>
                <th>Início</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {cliente.projetos.map((p) => (
                <tr key={p.id}>
                  <td>
                    <Link to={`/projetos/${p.id}`} className="link" style={{ color: 'var(--texto)' }}>
                      {p.nome}
                    </Link>
                  </td>
                  <td>
                    <span className={`badge ${corFase(p.fase_atual)}`}>
                      {p.fase_atual}
                    </span>
                  </td>
                  <td className="mono texto-2" style={{ fontSize: 12.5 }}>{fmtData(p.data_inicio)}</td>
                  <td>
                    <span className="linha-flex" style={{ gap: 7, color: STATUS_COR[p.status] || 'var(--texto-3)' }}>
                      <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'currentColor' }} />
                      {STATUS_PROJETO[p.status]}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
