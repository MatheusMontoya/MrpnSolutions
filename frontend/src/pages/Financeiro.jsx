import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import BotaoExportar from '../components/BotaoExportar'
import Icone from '../components/Icone'
import { SkeletonPagina } from '../components/Skeleton'
import { fmtBRL, fmtBRLExato, fmtData, fmtMes } from '../format'

const IC_GERAR = ['M23 4v6h-6', 'M1 20v-6h6', 'M3.51 9a9 9 0 0 1 14.85-3.36L23 10', 'M1 14l4.64 4.36A9 9 0 0 0 20.49 15']
const IC_EMITIR = ['M22 2 11 13', 'M22 2 15 22l-4-9-9-4 20-7z']
const IC_RECEBER = ['M20 6 9 17l-5-5']

const BADGE = {
  prevista: ['badge-cinza', 'Prevista'],
  emitida: ['badge-azul', 'Emitida'],
  recebida: ['badge-verde', 'Recebida'],
  cancelada: ['badge-vermelho', 'Cancelada'],
}

/** Financeiro: aba "faturamento" (plano completo) ou "receber" (emitidas em aberto). */
export default function Financeiro({ aba = 'faturamento' }) {
  const receber = aba === 'receber'
  const [dados, setDados] = useState(null)
  const [projetos, setProjetos] = useState([])
  const [projetoId, setProjetoId] = useState('') // '' = todos
  const [erro, setErro] = useState(null)

  const carregar = useCallback(() => {
    const q = projetoId ? `?projeto_id=${projetoId}` : ''
    api.get(`/faturas${q}`).then(setDados).catch((e) => setErro(e.message))
  }, [projetoId])

  useEffect(() => {
    carregar()
    api.get('/projetos').then(setProjetos).catch(() => {})
  }, [carregar])

  if (erro) return <div className="mensagem-erro">{erro}</div>
  if (!dados) return <SkeletonPagina kpis />

  const faturas = receber
    ? dados.faturas.filter((f) => f.status === 'emitida')
    : dados.faturas.filter((f) => f.status !== 'cancelada')

  const gerarPlano = async () => {
    try {
      await api.post(`/projetos/${projetoId}/faturas/gerar`, {})
      carregar()
    } catch (e) { setErro(e.message) }
  }
  const mudarStatus = async (f, status) => {
    try {
      await api.patch(`/faturas/${f.id}`, { status })
      carregar()
    } catch (e) { setErro(e.message) }
  }

  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <h1>{receber ? 'Contas a Receber' : 'Cronograma de Faturamento'}</h1>
          <div className="descricao">
            {receber
              ? 'Faturas emitidas em aberto — acompanhe vencimentos e baixe os recebimentos'
              : 'Plano de faturas gerado da receita prevista do motor hora-homem, mês a mês'}
          </div>
        </div>
        <div className="linha-flex">
          <BotaoExportar recurso="faturas" />
          <div className="campo" style={{ minWidth: 220 }}>
            <select value={projetoId} onChange={(e) => setProjetoId(e.target.value)} aria-label="Filtrar por projeto">
              <option value="">Todos os projetos</option>
              {projetos.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
            </select>
          </div>
          {!receber && projetoId && (
            <button className="botao botao-primario" onClick={gerarPlano}
              title="Cria/atualiza as faturas previstas a partir da receita mensal prevista (emitidas e recebidas são preservadas)">
              <Icone d={IC_GERAR} size={14} /> Gerar plano
            </button>
          )}
        </div>
      </div>

      <div className="grid-kpi">
        <div className="card kpi">
          <div className="rotulo">Previsto (a faturar)</div>
          <div className="valor">{fmtBRL(dados.total_previsto)}</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Emitido (em aberto)</div>
          <div className="valor" style={{ color: 'var(--azul)' }}>{fmtBRL(dados.total_emitido)}</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Recebido</div>
          <div className="valor" style={{ color: 'var(--verde)' }}>{fmtBRL(dados.total_recebido)}</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Vencido</div>
          <div className="valor" style={{ color: dados.total_vencido > 0 ? 'var(--vermelho)' : 'var(--texto)' }}>
            {fmtBRL(dados.total_vencido)}
          </div>
          <div className="detalhe">{dados.total_vencido > 0 ? 'cobrança necessária' : 'nada vencido'}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-corpo" style={{ paddingTop: 10 }}>
          {faturas.length === 0 ? (
            <div className="vazio-ensina">
              <Icone d={IC_EMITIR} size={28} strokeWidth={1.5} />
              <span className="titulo">{receber ? 'Nenhuma fatura em aberto' : 'Nenhuma fatura ainda'}</span>
              <span className="dica">
                {receber
                  ? 'Faturas emitidas aparecem aqui até o recebimento.'
                  : 'Selecione um projeto e clique em “Gerar plano” — as faturas nascem da receita prevista mês a mês.'}
              </span>
            </div>
          ) : (
            <table className="tabela">
              <thead>
                <tr>
                  <th>Competência</th><th>Projeto</th><th>Cliente</th>
                  <th className="num">Valor</th><th>Status</th><th>Nº</th>
                  <th>{receber ? 'Vencimento' : 'Emissão / Vencimento'}</th><th></th>
                </tr>
              </thead>
              <tbody>
                {faturas.map((f) => {
                  const [cls, rotulo] = BADGE[f.status] || BADGE.prevista
                  return (
                    <tr key={f.id}>
                      <td className="mono" style={{ fontWeight: 600 }}>{fmtMes(f.competencia.slice(0, 7))}</td>
                      <td><Link className="link" to={`/projetos/${f.projeto_id}`}>{f.projeto}</Link></td>
                      <td className="texto-2">{f.cliente}</td>
                      <td className="num">{fmtBRLExato(f.valor)}</td>
                      <td>
                        <span className={`badge ${cls}`}>{rotulo}</span>
                        {f.vencida && <span className="badge badge-vermelho" style={{ marginLeft: 6 }}>vencida há {f.dias_vencida}d</span>}
                      </td>
                      <td className="mono texto-3" style={{ fontSize: 12 }}>{f.numero || '—'}</td>
                      <td className="mono texto-2" style={{ fontSize: 12 }}>
                        {receber
                          ? (f.data_vencimento ? fmtData(f.data_vencimento) : '—')
                          : `${f.data_emissao ? fmtData(f.data_emissao) : '—'} / ${f.data_vencimento ? fmtData(f.data_vencimento) : '—'}`}
                      </td>
                      <td>
                        <div className="linha-flex" style={{ gap: 6, justifyContent: 'flex-end' }}>
                          {f.status === 'prevista' && (
                            <button className="botao botao-secundario botao-pequeno" onClick={() => mudarStatus(f, 'emitida')}>
                              <Icone d={IC_EMITIR} size={12} /> Emitir
                            </button>
                          )}
                          {f.status === 'emitida' && (
                            <button className="botao botao-primario botao-pequeno" onClick={() => mudarStatus(f, 'recebida')}>
                              <Icone d={IC_RECEBER} size={12} /> Receber
                            </button>
                          )}
                          {(f.status === 'prevista' || f.status === 'emitida') && !receber && (
                            <button className="botao botao-fantasma botao-pequeno" onClick={() => mudarStatus(f, 'cancelada')}>
                              Cancelar
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  )
}
