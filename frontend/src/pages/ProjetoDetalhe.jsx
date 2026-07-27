import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import DiffReagendamento from '../components/DiffReagendamento'
import Gantt from '../components/Gantt'
import Icone from '../components/Icone'
import Modal from '../components/Modal'
import { SkeletonPagina } from '../components/Skeleton'
import { SENIORIDADE, STATUS_PROJETO, corFase, fmtBRL, fmtBRLExato, fmtData, fmtHoras, fmtPct, iniciais } from '../format'
import { useSessao } from '../sessao'
import { BADGE_STATUS_PENDENCIA, FormPendencia, PRIORIDADES } from './Pendencias'

const IC_CHECK_MINI = ['M20 6 9 17l-5-5']
const IC_MAIS = ['M12 5v14', 'M5 12h14']
const IC_X_MINI = ['M18 6 6 18', 'M6 6l12 12']

/** Cor do chip do gate: verde = aprovado; vermelho = item vermelho; laranja = em avaliação. */
const chipDoGate = (gate) => {
  if (!gate || gate.total === 0) return null
  if (gate.aprovado) return ['badge-verde', `Gate ${gate.verde}/${gate.total} ✓`]
  if (gate.vermelho > 0) return ['badge-vermelho', `Gate ${gate.verde}/${gate.total}`]
  if (gate.verde + gate.amarelo > 0) return ['badge-laranja', `Gate ${gate.verde}/${gate.total}`]
  return ['badge-cinza', `Gate 0/${gate.total}`]
}

const IC_CALENDAR = ['M8 2v4', 'M16 2v4', 'M3 10h18', 'M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z']
const IC_REFRESH = ['M23 4v6h-6', 'M1 20v-6h6', 'M3.51 9a9 9 0 0 1 14.85-3.36L23 10', 'M1 14l4.64 4.36A9 9 0 0 0 20.49 15']
const IC_CHECK = ['M20 6 9 17l-5-5']

const STATUS_BADGE = { ativo: 'badge-verde', pausado: 'badge-laranja', encerrado: 'badge-cinza' }
const MARGEM_VERDE = 0.35 // limiar de exibição: margem saudável em verde

const avatarStyle = {
  width: 26, height: 26, borderRadius: 6, flexShrink: 0,
  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
  background: 'var(--azul-claro)', color: 'var(--azul-hover)',
  fontFamily: 'var(--fonte)', fontSize: 10, fontWeight: 600, letterSpacing: '0.02em',
}

export default function ProjetoDetalhe() {
  const { id } = useParams()
  const [projeto, setProjeto] = useState(null)
  const [erro, setErro] = useState(null)
  const [faseEmEdicao, setFaseEmEdicao] = useState(null) // fase p/ reagendar
  const [faseAlocando, setFaseAlocando] = useState(null) // fase p/ nova alocação
  const [consultores, setConsultores] = useState([])
  const [pendencias, setPendencias] = useState([])
  const [modalPendencia, setModalPendencia] = useState(false)
  const [riscos, setRiscos] = useState([])
  const [mudancas, setMudancas] = useState([])
  const [modalRisco, setModalRisco] = useState(false)
  const [modalMudanca, setModalMudanca] = useState(false)
  const [report, setReport] = useState(null) // status report aberto no modal
  const [modalEncerrar, setModalEncerrar] = useState(false)
  const [evm, setEvm] = useState(null) // valor agregado (SPI/CPI)
  const [tap, setTap] = useState(null) // termo de abertura aberto no modal
  const [faseSolicitando, setFaseSolicitando] = useState(null) // fase p/ solicitar alocação

  const carregar = useCallback(() => {
    api.get(`/projetos/${id}`).then(setProjeto).catch((e) => setErro(e.message))
    api.get(`/pendencias?projeto_id=${id}`).then(setPendencias).catch(() => {})
    api.get(`/riscos?projeto_id=${id}`).then(setRiscos).catch(() => {})
    api.get(`/mudancas?projeto_id=${id}`).then(setMudancas).catch(() => {})
    api.get(`/projetos/${id}/evm`).then(setEvm).catch(() => {})
  }, [id])

  const abrirReport = async () => {
    try {
      setReport(await api.get(`/projetos/${id}/status-report`))
    } catch (e) { setErro(e.message) }
  }

  const abrirTap = async () => {
    try {
      setTap(await api.get(`/projetos/${id}/tap`))
    } catch (e) { setErro(e.message) }
  }

  useEffect(() => {
    carregar()
    api.get('/consultores').then(setConsultores).catch(() => {})
  }, [carregar])

  if (erro) return <div className="mensagem-erro">{erro}</div>
  if (!projeto) return <SkeletonPagina />

  const faseAtual = projeto.fases.find((f) => f.atual) || projeto.fases[0]

  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <div className="migalhas">
            <Link to="/projetos">Projetos</Link>
            <Icone d={['M9 18l6-6-6-6']} size={13} strokeWidth={2} />
            <span>{projeto.cliente}</span>
          </div>
          <div className="linha-flex" style={{ gap: 12, flexWrap: 'wrap' }}>
            <h1>{projeto.nome}</h1>
            <PilhaEquipe fases={projeto.fases} />
            <span className={`badge ${STATUS_BADGE[projeto.status] || 'badge-cinza'}`}>
              {STATUS_PROJETO[projeto.status]}
            </span>
            {projeto.fase_atual && (
              <span className={`badge ${corFase(projeto.fase_atual)}`}>
                {projeto.fase_atual}
              </span>
            )}
          </div>
          <div className="descricao">
            Início {fmtData(projeto.data_inicio)}
            {projeto.encerrado_em && <> · encerrado em {fmtData(projeto.encerrado_em)}</>}
          </div>
          <div className="linha-flex" style={{ gap: 8, marginTop: 10 }}>
            <Link to={`/projetos/${id}/agil`} className="botao botao-secundario botao-pequeno">
              Quadro Ágil
            </Link>
            <button className="botao botao-secundario botao-pequeno" onClick={abrirTap}>
              TAP
            </button>
            <button className="botao botao-secundario botao-pequeno" onClick={abrirReport}>
              Status Report
            </button>
            {projeto.status !== 'encerrado' && (
              <button className="botao botao-fantasma botao-pequeno" onClick={() => setModalEncerrar(true)}>
                Encerrar projeto
              </button>
            )}
          </div>
        </div>
        <div className="grid-kpi" style={{ margin: 0, gridTemplateColumns: 'repeat(2, minmax(170px, auto))' }}>
          <div className="card kpi">
            <div className="rotulo">Receita prevista</div>
            <div className="valor">{fmtBRL(projeto.receita_prevista_total)}</div>
          </div>
          <div className="card kpi">
            <div className="rotulo">Receita realizada</div>
            <div className="valor">{fmtBRL(projeto.receita_realizada_total)}</div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-cabecalho">
          <h2 className="card-titulo">Linha do tempo — SAP Activate</h2>
          <div className="linha-flex" style={{ gap: 8 }}>
            <button className="botao botao-secundario botao-pequeno" onClick={() => setFaseEmEdicao(faseAtual)}>
              Mover data-fim
            </button>
            <button className="botao botao-secundario botao-pequeno" onClick={() => setFaseSolicitando(faseAtual)}
              title="Pedido que passa pela fila de aprovações com análise de conflitos">
              Solicitar alocação
            </button>
            <button className="botao botao-primario botao-pequeno" onClick={() => setFaseAlocando(faseAtual)}>
              Alocar consultor
            </button>
          </div>
        </div>
        <div className="card-corpo">
          <Gantt fases={projeto.fases} onSelecionarFase={setFaseEmEdicao} />
          <div className="texto-3" style={{ fontSize: 12, marginTop: 10 }}>
            Clique numa fase para mover a data-fim — o recálculo em cascata mostra o diff antes de aplicar.
          </div>
        </div>
      </div>

      {evm && <CardEVM evm={evm} />}

      <CardOrcamento projetoId={id} />

      {projeto.fases.map((fase) => {
        const horasPrev = fase.alocacoes.reduce((s, a) => s + a.horas_previstas, 0)
        const horasReal = fase.alocacoes.reduce((s, a) => s + a.horas_realizadas, 0)
        const receitaPrev = fase.alocacoes.reduce((s, a) => s + a.receita_prevista, 0)
        const margemPrev = fase.alocacoes.reduce((s, a) => s + a.margem_prevista, 0)
        const margemPct = receitaPrev > 0 ? margemPrev / receitaPrev : 0
        const n = fase.alocacoes.length
        return (
          <div className="card secao" key={fase.id}>
            <div className="card-cabecalho">
              <h2 className="card-titulo" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {fase.atual && <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--azul)', display: 'inline-block' }} />}
                {fase.atual ? `Fase atual: ${fase.nome}` : fase.nome}
                {(() => {
                  const chip = chipDoGate(fase.gate)
                  return chip ? <span className={`badge ${chip[0]}`} title="Quality Gate: itens verdes / total">{chip[1]}</span> : null
                })()}
                {fase.atividades?.length > 0 && (
                  <span className="badge badge-cinza mono" title="Entregas concluídas / total">
                    {fase.atividades.filter((a) => a.status === 'concluida').length}/{fase.atividades.length} entregas
                  </span>
                )}
                {fase.desvio_baseline_dias !== 0 && (
                  <span className={`badge ${fase.desvio_baseline_dias > 0 ? 'badge-vermelho' : 'badge-verde'} mono`}
                    title={`Fim previsto vs linha de base original (${fase.baseline_fim ? fmtData(fase.baseline_fim) : '—'})`}>
                    {fase.desvio_baseline_dias > 0 ? '+' : ''}{fase.desvio_baseline_dias}d vs baseline
                  </span>
                )}
              </h2>
              <div className="linha-flex" style={{ gap: 10 }}>
                <span className="texto-3 mono" style={{ fontSize: 12 }}>
                  {n} {n === 1 ? 'consultor alocado' : 'consultores alocados'}
                </span>
                <button className="botao botao-secundario botao-pequeno" onClick={() => setFaseEmEdicao(fase)}>
                  Mover data-fim
                </button>
                <button className="botao botao-primario botao-pequeno" onClick={() => setFaseAlocando(fase)}>
                  Alocar consultor
                </button>
              </div>
            </div>
            <div className="card-corpo" style={{ paddingTop: 12 }}>
              {n === 0 ? (
                <div className="vazio-ensina">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M19 8v6" /><path d="M22 11h-6" />
                  </svg>
                  <span className="titulo">Nenhum consultor alocado em {fase.nome}</span>
                  <span className="dica">
                    Sem alocação, esta fase não gera receita prevista. Use “Alocar consultor” acima —
                    a taxa hora-venda nasce da tabela do consultor e pode ser negociada por projeto.
                  </span>
                </div>
              ) : (
                <table className="tabela">
                  <thead>
                    <tr>
                      <th>Consultor</th><th>Período</th><th className="num">h/semana</th>
                      <th className="num">Taxa venda</th><th className="num">Horas prev.</th>
                      <th className="num">Horas real.</th><th className="num">Receita prev.</th>
                      <th className="num">Margem prev.</th><th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {fase.alocacoes.map((a) => {
                      const abaixo = a.horas_realizadas < a.horas_previstas
                      const mPct = a.receita_prevista > 0 ? a.margem_prevista / a.receita_prevista : 0
                      return (
                        <tr key={a.id}>
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                              <span style={avatarStyle}>{iniciais(a.consultor)}</span>
                              <div>
                                <div style={{ fontWeight: 500, color: 'var(--texto)' }}>{a.consultor}</div>
                                <div className="texto-3" style={{ fontSize: 11 }}>
                                  {SENIORIDADE[a.senioridade]}{a.modulo_sap ? ` · ${a.modulo_sap}` : ''}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td className="mono texto-2" style={{ fontSize: 12.5 }}>{fmtData(a.data_inicio)} – {fmtData(a.data_fim)}</td>
                          <td className="num mono">{fmtHoras(a.horas_semana)}</td>
                          <td className="num mono">
                            {fmtBRLExato(a.taxa_hora_venda)}
                            {a.taxa_negociada && <span className="badge badge-laranja" style={{ marginLeft: 6, fontSize: 10 }}>negociada</span>}
                          </td>
                          <td className="num mono">{fmtHoras(a.horas_previstas)}</td>
                          <td className="num mono" style={abaixo ? { color: 'var(--vermelho)' } : undefined}>{fmtHoras(a.horas_realizadas)}</td>
                          <td className="num mono">{fmtBRLExato(a.receita_prevista)}</td>
                          <td className="num mono" style={{ color: mPct >= MARGEM_VERDE ? 'var(--verde)' : 'var(--texto)' }}>{fmtPct(mPct)}</td>
                          <td>
                            <button className="botao botao-fantasma botao-pequeno" title="Remover alocação"
                              onClick={async () => {
                                if (confirm(`Remover alocação de ${a.consultor} em ${fase.nome}? Os apontamentos lançados nela também serão removidos.`)) {
                                  await api.del(`/alocacoes/${a.id}`)
                                  carregar()
                                }
                              }}>
                              Remover
                            </button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colSpan={4} style={{ textAlign: 'right', fontSize: 12.5, fontWeight: 600, color: 'var(--texto-2)' }}>
                        Totais fase {fase.nome}
                      </td>
                      <td className="num mono">{fmtHoras(horasPrev)}</td>
                      <td className="num mono">{fmtHoras(horasReal)}</td>
                      <td className="num mono">{fmtBRLExato(receitaPrev)}</td>
                      <td className="num mono" style={{ color: margemPct >= MARGEM_VERDE ? 'var(--verde)' : 'var(--texto)' }}>{fmtPct(margemPct)}</td>
                      <td></td>
                    </tr>
                  </tfoot>
                </table>
              )}

              <SecaoAtividades fase={fase} consultores={consultores} onMudou={carregar} />
              <SecaoGate fase={fase} onMudou={carregar} />
            </div>
          </div>
        )
      })}

      {/* ---- pendências do projeto ---- */}
      <div className="card secao">
        <div className="card-cabecalho">
          <h2 className="card-titulo-secao">Pendências do projeto</h2>
          <button className="botao botao-secundario botao-pequeno" onClick={() => setModalPendencia(true)}>
            <Icone d={IC_MAIS} size={13} /> Nova pendência
          </button>
        </div>
        <div className="card-corpo" style={{ paddingTop: 8 }}>
          {pendencias.length === 0 ? (
            <div className="vazio">Nenhuma pendência registrada neste projeto.</div>
          ) : (
            <table className="tabela">
              <thead>
                <tr><th>Pendência</th><th>Fase</th><th>Responsável</th><th>Prioridade</th><th>Status</th><th></th></tr>
              </thead>
              <tbody>
                {pendencias.map((p) => {
                  const [clsP, rotP] = PRIORIDADES[p.prioridade] || PRIORIDADES.media
                  const [clsS, rotS] = BADGE_STATUS_PENDENCIA[p.status] || BADGE_STATUS_PENDENCIA.aberta
                  return (
                    <tr key={p.id}>
                      <td>
                        <strong style={{ fontWeight: 600 }}>{p.titulo}</strong>
                        {p.descricao && <div className="texto-3" style={{ fontSize: 12 }}>{p.descricao}</div>}
                      </td>
                      <td className="texto-2">{p.fase || '—'}</td>
                      <td className="texto-2">{p.responsavel || '—'}</td>
                      <td><span className={clsP} style={{ fontWeight: 600, fontSize: 12.5 }}>● {rotP}</span></td>
                      <td><span className={`badge ${clsS}`}>{rotS}</span></td>
                      <td>
                        {p.status !== 'resolvida' && (
                          <button className="botao botao-fantasma botao-pequeno"
                            onClick={async () => { await api.patch(`/pendencias/${p.id}`, { status: 'resolvida' }); carregar() }}>
                            <Icone d={IC_CHECK_MINI} size={12} /> Resolver
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* ---- riscos e mudanças (governança) ---- */}
      <div className="grid-2-igual secao">
        <div className="card">
          <div className="card-cabecalho">
            <h2 className="card-titulo-secao">Riscos</h2>
            <button className="botao botao-secundario botao-pequeno" onClick={() => setModalRisco(true)}>
              <Icone d={IC_MAIS} size={13} /> Novo risco
            </button>
          </div>
          <div className="card-corpo" style={{ paddingTop: 8 }}>
            {riscos.length === 0 ? (
              <div className="vazio">Nenhum risco mapeado.</div>
            ) : (
              <table className="tabela">
                <thead>
                  <tr><th>Risco</th><th>P×I</th><th>Severidade</th><th>Status</th><th></th></tr>
                </thead>
                <tbody>
                  {riscos.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <strong style={{ fontWeight: 600 }}>{r.titulo}</strong>
                        {r.resposta && <div className="texto-3" style={{ fontSize: 11.5 }}>Resposta: {r.resposta}</div>}
                      </td>
                      <td className="mono texto-2" style={{ fontSize: 12 }}>{r.probabilidade[0].toUpperCase()}×{r.impacto[0].toUpperCase()}</td>
                      <td>
                        <span className={`badge ${r.severidade === 'critica' ? 'badge-vermelho' : r.severidade === 'moderada' ? 'badge-laranja' : 'badge-cinza'}`}>
                          {r.severidade}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${r.status === 'aberto' ? 'badge-azul' : r.status === 'mitigado' ? 'badge-verde' : 'badge-vermelho'}`}>
                          {r.status}
                        </span>
                      </td>
                      <td>
                        {r.status === 'aberto' && (
                          <button className="botao botao-fantasma botao-pequeno"
                            onClick={async () => { await api.patch(`/riscos/${r.id}`, { status: 'mitigado' }); carregar() }}>
                            Mitigar
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-cabecalho">
            <h2 className="card-titulo-secao">Mudanças (CR)</h2>
            <button className="botao botao-secundario botao-pequeno" onClick={() => setModalMudanca(true)}>
              <Icone d={IC_MAIS} size={13} /> Nova CR
            </button>
          </div>
          <div className="card-corpo" style={{ paddingTop: 8 }}>
            {mudancas.length === 0 ? (
              <div className="vazio">Nenhuma solicitação de mudança.</div>
            ) : (
              <table className="tabela">
                <thead>
                  <tr><th>Mudança</th><th className="num">Horas</th><th className="num">Valor</th><th>Status</th><th></th></tr>
                </thead>
                <tbody>
                  {mudancas.map((m) => (
                    <tr key={m.id}>
                      <td>
                        <strong style={{ fontWeight: 600 }}>{m.titulo}</strong>
                        {m.descricao && <div className="texto-3" style={{ fontSize: 11.5 }}>{m.descricao}</div>}
                      </td>
                      <td className="num">{fmtHoras(m.impacto_horas)}</td>
                      <td className="num">{fmtBRLExato(m.impacto_valor)}</td>
                      <td>
                        <span className={`badge ${m.status === 'aberta' ? 'badge-azul' : m.status === 'aprovada' ? 'badge-verde' : 'badge-vermelho'}`}>
                          {m.status}
                        </span>
                      </td>
                      <td>
                        {m.status === 'aberta' && (
                          <div className="linha-flex" style={{ gap: 4, justifyContent: 'flex-end' }}>
                            <button className="botao botao-secundario botao-pequeno"
                              onClick={async () => { await api.patch(`/mudancas/${m.id}/decidir`, { status: 'aprovada' }); carregar() }}>
                              Aprovar
                            </button>
                            <button className="botao botao-fantasma botao-pequeno"
                              onClick={async () => { await api.patch(`/mudancas/${m.id}/decidir`, { status: 'rejeitada' }); carregar() }}>
                              Rejeitar
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {modalPendencia && (
        <FormPendencia projetoId={projeto.id} fases={projeto.fases}
          onFechar={() => setModalPendencia(false)}
          onCriada={() => { setModalPendencia(false); carregar() }} />
      )}

      {modalRisco && (
        <FormRisco projetoId={projeto.id} onFechar={() => setModalRisco(false)}
          onCriado={() => { setModalRisco(false); carregar() }} />
      )}
      {modalMudanca && (
        <FormMudanca projetoId={projeto.id} onFechar={() => setModalMudanca(false)}
          onCriada={() => { setModalMudanca(false); carregar() }} />
      )}
      {report && <ModalStatusReport report={report} onFechar={() => setReport(null)} />}
      {modalEncerrar && (
        <ModalEncerrar projeto={projeto} onFechar={() => setModalEncerrar(false)}
          onEncerrado={() => { setModalEncerrar(false); carregar() }} />
      )}

      {faseEmEdicao && (
        <ModalReagendar fase={faseEmEdicao} onFechar={() => setFaseEmEdicao(null)}
          onAplicado={() => { setFaseEmEdicao(null); carregar() }} />
      )}
      {faseAlocando && (
        <ModalAlocar fase={faseAlocando} consultores={consultores}
          onFechar={() => setFaseAlocando(null)}
          onCriado={() => { setFaseAlocando(null); carregar() }} />
      )}
      {tap && <ModalTAP tap={tap} onFechar={() => setTap(null)} />}
      {faseSolicitando && (
        <ModalSolicitarAlocacao fase={faseSolicitando} fases={projeto.fases} consultores={consultores}
          onFechar={() => setFaseSolicitando(null)}
          onCriada={() => setFaseSolicitando(null)} />
      )}
    </>
  )
}

/** Entregas/atividades da fase: status em 3 estágios, responsável e CRUD inline. */
/** Equipe do projeto em pilha de avatares (+N) — quem está nele, num relance. */
function PilhaEquipe({ fases }) {
  const nomes = [...new Set(
    fases.flatMap((f) => f.alocacoes.map((a) => a.consultor)).filter(Boolean),
  )]
  if (nomes.length === 0) return null
  const mostrados = nomes.slice(0, 4)
  const resto = nomes.length - mostrados.length
  return (
    <span className="pilha-avatares" title={nomes.join(' · ')}>
      {mostrados.map((n) => <span key={n}>{iniciais(n)}</span>)}
      {resto > 0 && <span className="resto">+{resto}</span>}
    </span>
  )
}

const CATEGORIAS_MANUAIS = [
  ['terceiros', 'Terceiros / subcontratação'],
  ['licencas', 'Licenças / software'],
  ['outros', 'Outros custos'],
]

/** Orçado × realizado por rubrica: horas e despesas vêm do motor (realizado
 * automático); terceiros/licenças/outros são lançados pelo gestor. */
function CardOrcamento({ projetoId }) {
  const [orc, setOrc] = useState(null)
  const [erro, setErro] = useState(null)
  const [editando, setEditando] = useState(null) // {id, campo} em edição inline
  const [valorEdicao, setValorEdicao] = useState('')
  const [novaRubrica, setNovaRubrica] = useState(null) // form aberto

  const carregar = useCallback(() => {
    api.get(`/projetos/${projetoId}/orcamento`).then(setOrc).catch((e) => setErro(e.message))
  }, [projetoId])

  useEffect(carregar, [carregar])

  if (erro) return null
  if (!orc) return null

  const salvarEdicao = async () => {
    const { id, campo } = editando
    try {
      await api.patch(`/orcamento/itens/${id}`, { [campo]: Number(valorEdicao) })
      setEditando(null)
      carregar()
    } catch (e) { setErro(e.message) }
  }

  const adicionarRubrica = async (e) => {
    e.preventDefault()
    try {
      await api.post(`/projetos/${projetoId}/orcamento/itens`, {
        categoria: novaRubrica.categoria,
        descricao: novaRubrica.descricao,
        valor_orcado: Number(novaRubrica.valor_orcado) || 0,
        valor_realizado: Number(novaRubrica.valor_realizado) || 0,
      })
      setNovaRubrica(null)
      carregar()
    } catch (err) { setErro(err.message) }
  }

  const remover = async (item) => {
    await api.del(`/orcamento/itens/${item.id}`)
    carregar()
  }

  const corConsumo = (c) => c == null ? 'var(--texto-3)' : c > 1 ? 'var(--vermelho)' : c > 0.85 ? 'var(--laranja)' : 'var(--verde)'

  const celulaEditavel = (item, campo, valor, editavel) => {
    if (!editavel) return <span className="mono">{fmtBRLExato(valor)}</span>
    if (editando?.id === item.id && editando?.campo === campo) {
      return (
        <input className="mono" type="number" autoFocus value={valorEdicao}
          onChange={(e) => setValorEdicao(e.target.value)}
          onBlur={salvarEdicao}
          onKeyDown={(e) => { if (e.key === 'Enter') salvarEdicao(); if (e.key === 'Escape') setEditando(null) }}
          style={{ width: 110, textAlign: 'right', padding: '4px 6px' }} />
      )
    }
    return (
      <button type="button" className="mono" title="Clique para editar"
        onClick={() => { setEditando({ id: item.id, campo }); setValorEdicao(String(valor)) }}
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', font: 'inherit', textDecoration: 'underline dotted', textUnderlineOffset: 3 }}>
        {fmtBRLExato(valor)}
      </button>
    )
  }

  return (
    <div className="card">
      <div className="card-cabecalho">
        <h2 className="card-titulo">Orçado × Realizado</h2>
        <div className="linha-flex" style={{ gap: 10 }}>
          {orc.consumo != null && (
            <span className="badge mono" style={{ background: 'transparent', border: '1px solid var(--borda-forte)', color: corConsumo(orc.consumo) }}>
              {fmtPct(orc.consumo)} consumido
            </span>
          )}
          <button className="botao botao-secundario botao-pequeno"
            onClick={() => setNovaRubrica({ categoria: 'terceiros', descricao: '', valor_orcado: '', valor_realizado: '' })}>
            Nova rubrica
          </button>
        </div>
      </div>
      <div className="card-corpo" style={{ paddingTop: 6 }}>
        <table className="tabela">
          <thead>
            <tr><th>Rubrica</th><th className="num">Orçado</th><th className="num">Realizado</th><th style={{ width: 160 }}>Consumo</th><th /></tr>
          </thead>
          <tbody>
            {orc.itens.map((i) => (
              <tr key={i.id}>
                <td>
                  {i.rotulo}
                  {i.descricao && <span className="texto-3" style={{ fontSize: 12 }}> — {i.descricao}</span>}
                  {i.automatica && <span className="badge badge-cinza" style={{ marginLeft: 6, fontSize: 10 }}>motor</span>}
                </td>
                <td className="num">{celulaEditavel(i, 'valor_orcado', i.orcado, true)}</td>
                <td className="num">{celulaEditavel(i, 'valor_realizado', i.realizado, !i.automatica)}</td>
                <td>
                  <div className="linha-flex" style={{ gap: 8 }}>
                    <div style={{ flex: 1, height: 6, borderRadius: 99, background: 'var(--borda)', overflow: 'hidden' }}>
                      <div style={{
                        width: `${Math.min((i.consumo ?? 0) * 100, 100)}%`, height: '100%',
                        background: corConsumo(i.consumo), borderRadius: 99,
                      }} />
                    </div>
                    <span className="mono texto-3" style={{ fontSize: 11.5, minWidth: 42, textAlign: 'right' }}>
                      {i.consumo == null ? '—' : fmtPct(i.consumo)}
                    </span>
                  </div>
                </td>
                <td className="num">
                  {!i.automatica && (
                    <button type="button" className="fechar-x" title="Remover rubrica" onClick={() => remover(i)}>
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td style={{ fontWeight: 700 }}>Total</td>
              <td className="num mono" style={{ fontWeight: 700 }}>{fmtBRLExato(orc.total_orcado)}</td>
              <td className="num mono" style={{ fontWeight: 700 }}>{fmtBRLExato(orc.total_realizado)}</td>
              <td colSpan={2} className="texto-3" style={{ fontSize: 12 }}>
                saldo <span className="mono" style={{ fontWeight: 600, color: orc.saldo < 0 ? 'var(--vermelho)' : 'var(--verde)' }}>{fmtBRLExato(orc.saldo)}</span>
              </td>
            </tr>
          </tfoot>
        </table>

        {novaRubrica && (
          <form onSubmit={adicionarRubrica} className="form-linha" style={{ marginTop: 12, alignItems: 'flex-end' }}>
            <div className="campo">
              <label htmlFor="orc-cat">Categoria</label>
              <select id="orc-cat" value={novaRubrica.categoria}
                onChange={(e) => setNovaRubrica({ ...novaRubrica, categoria: e.target.value })}>
                {CATEGORIAS_MANUAIS.map(([v, r]) => <option key={v} value={v}>{r}</option>)}
              </select>
            </div>
            <div className="campo" style={{ flex: 1 }}>
              <label htmlFor="orc-desc">Descrição</label>
              <input id="orc-desc" value={novaRubrica.descricao} required placeholder="Ex.: consultoria de segurança"
                onChange={(e) => setNovaRubrica({ ...novaRubrica, descricao: e.target.value })} />
            </div>
            <div className="campo">
              <label htmlFor="orc-orcado">Orçado (R$)</label>
              <input id="orc-orcado" className="mono" type="number" min="0" step="0.01" value={novaRubrica.valor_orcado}
                onChange={(e) => setNovaRubrica({ ...novaRubrica, valor_orcado: e.target.value })} />
            </div>
            <div className="campo">
              <label htmlFor="orc-real">Realizado (R$)</label>
              <input id="orc-real" className="mono" type="number" min="0" step="0.01" value={novaRubrica.valor_realizado}
                onChange={(e) => setNovaRubrica({ ...novaRubrica, valor_realizado: e.target.value })} />
            </div>
            <button className="botao botao-primario" type="submit">Adicionar</button>
            <button className="botao botao-fantasma" type="button" onClick={() => setNovaRubrica(null)}>Cancelar</button>
          </form>
        )}
      </div>
    </div>
  )
}

/** Valor agregado (EVM): SPI (ritmo) e CPI (custo) calculados pelo motor —
 * PV/EV/AC a custo, EAC = BAC/CPI. Sem dados de custo ainda, não renderiza índices. */
function CardEVM({ evm }) {
  const medidor = (valor, rotulo, dica) => {
    const cor = valor == null ? 'var(--texto-3)'
      : valor >= 1 ? 'var(--verde)'
      : valor >= 0.9 ? 'var(--laranja)'
      : 'var(--vermelho)'
    const pct = valor == null ? 0 : Math.max(0, Math.min(valor / 1.2, 1))
    return (
      <div className="evm-medidor" title={dica}>
        <div className="evm-valor mono" style={{ color: cor }}>
          {valor == null ? '—' : valor.toFixed(2)}
        </div>
        <div className="evm-arco">
          <span style={{ width: `${pct * 100}%`, background: cor }} />
        </div>
        <div className="evm-rotulo">{rotulo}</div>
      </div>
    )
  }
  return (
    <div className="card">
      <div className="card-cabecalho">
        <h2 className="card-titulo">Valor agregado (EVM)</h2>
        <span className="texto-3" style={{ fontSize: 12 }}>
          referência {fmtData(evm.data_referencia)} · valores a custo
        </span>
      </div>
      <div className="card-corpo">
        <div className="evm-grade">
          {medidor(evm.spi, 'SPI · ritmo', 'EV ÷ PV — abaixo de 1: entregando menos do que o planejado até hoje')}
          {medidor(evm.cpi, 'CPI · custo', 'EV ÷ AC — abaixo de 1: gastando mais do que o valor entregue')}
          <div className="evm-tabela">
            {[
              ['PV — planejado até hoje', evm.pv],
              ['EV — valor agregado', evm.ev],
              ['AC — custo real', evm.ac],
              ['BAC — orçamento total', evm.bac],
              ['EAC — projeção no término', evm.eac],
            ].map(([rotulo, v]) => (
              <div key={rotulo} className="evm-linha">
                <span className="texto-2">{rotulo}</span>
                <span className="mono">{v == null ? '—' : fmtBRL(v)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function SecaoAtividades({ fase, consultores, onMudou }) {
  const [novo, setNovo] = useState('')
  const CICLO = { pendente: 'em_andamento', em_andamento: 'concluida', concluida: 'pendente' }
  const ROTULO = { pendente: 'Pendente', em_andamento: 'Em andamento', concluida: 'Concluída' }

  const mudarStatus = async (a) => {
    await api.patch(`/atividades/${a.id}`, { status: CICLO[a.status] })
    onMudou()
  }
  const mudarResponsavel = async (a, valor) => {
    await api.patch(`/atividades/${a.id}`, { responsavel_id: valor ? Number(valor) : null })
    onMudou()
  }
  const adicionar = async (e) => {
    e.preventDefault()
    if (!novo.trim()) return
    await api.post('/atividades', { fase_id: fase.id, titulo: novo.trim() })
    setNovo('')
    onMudou()
  }
  const remover = async (a) => {
    await api.del(`/atividades/${a.id}`)
    onMudou()
  }

  const concluidas = (fase.atividades || []).filter((a) => a.status === 'concluida').length

  return (
    <div>
      <div className="sub-secao">
        Entregas da fase <span className="contagem">({concluidas}/{fase.atividades?.length || 0})</span>
      </div>
      <ul className="lista-atividades">
        {(fase.atividades || []).map((a) => (
          <li key={a.id}>
            <button
              type="button"
              className={`atv-status ${a.status}`}
              onClick={() => mudarStatus(a)}
              title={`${ROTULO[a.status]} — clique para avançar`}
              aria-label={`Status de "${a.titulo}": ${ROTULO[a.status]}. Clique para avançar.`}
            >
              {a.status === 'concluida' ? <Icone d={IC_CHECK_MINI} size={11} strokeWidth={3} /> : a.status === 'em_andamento' ? '·' : ''}
            </button>
            <span className={a.status === 'concluida' ? 'concluida-titulo' : ''} style={{ flex: 1, fontSize: 13.5 }}>
              {a.titulo}
            </span>
            <select
              value={a.responsavel_id ?? ''}
              onChange={(e) => mudarResponsavel(a, e.target.value)}
              title="Responsável pela entrega"
              aria-label={`Responsável pela entrega: ${a.titulo}`}
              style={{
                fontFamily: 'inherit', fontSize: 12, padding: '3px 6px',
                border: '1px solid var(--borda)', borderRadius: 'var(--raio-1)',
                background: 'var(--superficie)', color: a.responsavel_id ? 'var(--texto)' : 'var(--texto-3)',
                maxWidth: 150,
              }}
            >
              <option value="">— responsável —</option>
              {consultores.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
            <button type="button" className="fechar-x" title="Remover entrega" aria-label={`Remover ${a.titulo}`}
              onClick={() => remover(a)}>
              <Icone d={IC_X_MINI} size={13} />
            </button>
          </li>
        ))}
      </ul>
      <form onSubmit={adicionar} className="linha-flex" style={{ gap: 8, marginTop: 8 }}>
        <input
          value={novo}
          onChange={(e) => setNovo(e.target.value)}
          placeholder="Nova entrega desta fase…"
          aria-label={`Nova entrega da fase ${fase.nome}`}
          style={{
            flex: 1, fontFamily: 'inherit', fontSize: 13,
            padding: '6px 10px', border: '1px solid var(--borda-forte)',
            borderRadius: 'var(--raio-1)', background: 'var(--superficie)',
          }}
        />
        <button className="botao botao-secundario botao-pequeno" type="submit" disabled={!novo.trim()}>
          <Icone d={IC_MAIS} size={12} /> Adicionar
        </button>
      </form>
    </div>
  )
}

/** Quality Gate da fase (PQG do Activate): semáforo por item + plano de ação. */
function SecaoGate({ fase, onMudou }) {
  const gate = fase.gate
  if (!gate || gate.total === 0) return null

  const setStatus = async (item, status) => {
    // clicar no status já ativo volta para "não verificado"
    await api.patch(`/gates/${item.id}`, { status: item.status === status ? 'nao_verificado' : status })
    onMudou()
  }
  const salvarPlano = async (item, texto) => {
    if (texto === item.plano_acao) return
    await api.patch(`/gates/${item.id}`, { plano_acao: texto })
    onMudou()
  }

  return (
    <div>
      <div className="sub-secao">
        Quality Gate
        <span className="contagem">({gate.verde}/{gate.total} verdes)</span>
        {gate.aprovado && <span className="badge badge-verde">Gate aprovado — fase pode ser concluída</span>}
        {gate.vermelho > 0 && <span className="badge badge-vermelho">{gate.vermelho} item(ns) em vermelho</span>}
      </div>
      <ul className="lista-atividades">
        {gate.itens.map((item) => (
          <li key={item.id} style={{ alignItems: 'flex-start' }}>
            <span className="mono texto-3" style={{ fontSize: 11, paddingTop: 3, minWidth: 52 }}>{item.codigo}</span>
            <div style={{ flex: 1 }}>
              <span style={{ fontSize: 13.5 }} title={item.risco}>{item.pergunta}</span>
              {(item.status === 'amarelo' || item.status === 'vermelho') && (
                <input
                  defaultValue={item.plano_acao}
                  key={`${item.id}|${item.plano_acao}`}
                  onBlur={(e) => salvarPlano(item, e.target.value)}
                  placeholder="Plano de ação para destravar este item…"
                  aria-label={`Plano de ação de ${item.codigo}`}
                  style={{
                    display: 'block', width: '100%', marginTop: 5,
                    fontFamily: 'inherit', fontSize: 12.5, padding: '5px 8px',
                    border: '1px dashed var(--borda-forte)', borderRadius: 'var(--raio-1)',
                    background: 'var(--superficie-brilho)',
                  }}
                />
              )}
            </div>
            <span className="semaforo" role="group" aria-label={`Semáforo de ${item.codigo}`}>
              <button type="button" className={`s-verde${item.status === 'verde' ? ' ativo' : ''}`}
                title="Verde — critério atendido" onClick={() => setStatus(item, 'verde')} />
              <button type="button" className={`s-amarelo${item.status === 'amarelo' ? ' ativo' : ''}`}
                title="Amarelo — atenção / plano de ação" onClick={() => setStatus(item, 'amarelo')} />
              <button type="button" className={`s-vermelho${item.status === 'vermelho' ? ' ativo' : ''}`}
                title="Vermelho — bloqueia a fase" onClick={() => setStatus(item, 'vermelho')} />
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Novo risco: matriz probabilidade × impacto + plano de resposta. */
function FormRisco({ projetoId, onFechar, onCriado }) {
  const [form, setForm] = useState({ titulo: '', probabilidade: 'medio', impacto: 'medio', resposta: '' })
  const [erro, setErro] = useState(null)
  const GRAUS_P = [['baixo', 'Baixa'], ['medio', 'Média'], ['alto', 'Alta']]
  const GRAUS_I = [['baixo', 'Baixo'], ['medio', 'Médio'], ['alto', 'Alto']]

  const salvar = async (e) => {
    e.preventDefault()
    setErro(null)
    try {
      await api.post('/riscos', { projeto_id: projetoId, ...form })
      onCriado()
    } catch (err) { setErro(err.message) }
  }

  return (
    <Modal titulo="Novo risco" onFechar={onFechar}
      rodape={<>
        <button className="botao botao-fantasma" onClick={onFechar}>Cancelar</button>
        <button className="botao botao-primario" type="submit" form="form-risco" disabled={!form.titulo}>Registrar</button>
      </>}>
      <form id="form-risco" onSubmit={salvar} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {erro && <div className="mensagem-erro">{erro}</div>}
        <div className="campo">
          <label htmlFor="rs-titulo">Risco *</label>
          <input id="rs-titulo" value={form.titulo} autoFocus required
            onChange={(e) => setForm({ ...form, titulo: e.target.value })}
            placeholder="Ex.: indisponibilidade do time do cliente no UAT" />
        </div>
        <div className="form-linha">
          <div className="campo">
            <label htmlFor="rs-prob">Probabilidade</label>
            <select id="rs-prob" value={form.probabilidade} onChange={(e) => setForm({ ...form, probabilidade: e.target.value })}>
              {GRAUS_P.map(([v, r]) => <option key={v} value={v}>{r}</option>)}
            </select>
          </div>
          <div className="campo">
            <label htmlFor="rs-imp">Impacto</label>
            <select id="rs-imp" value={form.impacto} onChange={(e) => setForm({ ...form, impacto: e.target.value })}>
              {GRAUS_I.map(([v, r]) => <option key={v} value={v}>{r}</option>)}
            </select>
          </div>
        </div>
        <div className="campo">
          <label htmlFor="rs-resp">Plano de resposta</label>
          <textarea id="rs-resp" rows={3} value={form.resposta}
            onChange={(e) => setForm({ ...form, resposta: e.target.value })}
            placeholder="Como mitigar ou contingenciar…"
            style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit', fontSize: 14 }} />
        </div>
      </form>
    </Modal>
  )
}

/** Nova solicitação de mudança (CR) com impacto em horas e valor. */
function FormMudanca({ projetoId, onFechar, onCriada }) {
  const [form, setForm] = useState({ titulo: '', descricao: '', impacto_horas: '', impacto_valor: '' })
  const [erro, setErro] = useState(null)

  const salvar = async (e) => {
    e.preventDefault()
    setErro(null)
    try {
      await api.post('/mudancas', {
        projeto_id: projetoId,
        titulo: form.titulo,
        descricao: form.descricao,
        impacto_horas: Number(form.impacto_horas || 0),
        impacto_valor: Number(form.impacto_valor || 0),
      })
      onCriada()
    } catch (err) { setErro(err.message) }
  }

  return (
    <Modal titulo="Nova solicitação de mudança" onFechar={onFechar}
      rodape={<>
        <button className="botao botao-fantasma" onClick={onFechar}>Cancelar</button>
        <button className="botao botao-primario" type="submit" form="form-cr" disabled={!form.titulo}>Registrar CR</button>
      </>}>
      <form id="form-cr" onSubmit={salvar} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {erro && <div className="mensagem-erro">{erro}</div>}
        <div className="campo">
          <label htmlFor="cr-titulo">Mudança solicitada *</label>
          <input id="cr-titulo" value={form.titulo} autoFocus required
            onChange={(e) => setForm({ ...form, titulo: e.target.value })} />
        </div>
        <div className="form-linha">
          <div className="campo">
            <label htmlFor="cr-horas">Impacto em horas</label>
            <input id="cr-horas" type="number" min="0" step="4" value={form.impacto_horas}
              onChange={(e) => setForm({ ...form, impacto_horas: e.target.value })} />
          </div>
          <div className="campo">
            <label htmlFor="cr-valor">Impacto em valor (R$)</label>
            <input id="cr-valor" type="number" min="0" step="100" value={form.impacto_valor}
              onChange={(e) => setForm({ ...form, impacto_valor: e.target.value })} />
          </div>
        </div>
        <div className="campo">
          <label htmlFor="cr-desc">Descrição</label>
          <textarea id="cr-desc" rows={3} value={form.descricao}
            onChange={(e) => setForm({ ...form, descricao: e.target.value })}
            style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit', fontSize: 14 }} />
        </div>
      </form>
    </Modal>
  )
}

/** Status report consolidado — gerado dos dados do sistema; imprimível. */
/** TAP — Termo de Abertura do Projeto, imprimível. Escopo/valores vêm da
 * proposta convertida; cronograma é a LINHA DE BASE (compromisso original). */
function ModalTAP({ tap, onFechar }) {
  return (
    <Modal extraLarga classeExtra="modal-imprimivel"
      titulo={`Termo de Abertura — ${tap.projeto}`}
      onFechar={onFechar}
      rodape={<>
        <button className="botao botao-fantasma" onClick={onFechar}>Fechar</button>
        <button className="botao botao-primario" onClick={() => window.print()}>Imprimir / PDF</button>
      </>}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
        <div className="linha-flex" style={{ gap: 10, flexWrap: 'wrap' }}>
          <span className="texto-2">{tap.cliente}</span>
          {tap.proposta && <span className="badge badge-azul">origem: {tap.proposta}</span>}
          <span className="espacador" />
          <span className="texto-3" style={{ fontSize: 12 }}>gerado em {fmtData(tap.gerado_em)}</span>
        </div>

        <div className="grid-kpi" style={{ margin: 0 }}>
          <div className="card kpi">
            <div className="rotulo">Valor estimado</div>
            <div className="valor">{fmtBRL(tap.valor_estimado)}</div>
          </div>
          <div className="card kpi">
            <div className="rotulo">Horas estimadas</div>
            <div className="valor">{fmtHoras(tap.horas_estimadas)}</div>
          </div>
          <div className="card kpi">
            <div className="rotulo">Início</div>
            <div className="valor" style={{ fontSize: 20 }}>{fmtData(tap.data_inicio)}</div>
          </div>
          <div className="card kpi">
            <div className="rotulo">Término previsto</div>
            <div className="valor" style={{ fontSize: 20 }}>{tap.termino_previsto ? fmtData(tap.termino_previsto) : '—'}</div>
          </div>
        </div>

        <div className="grid-2-igual" style={{ gap: 16 }}>
          <div>
            <h4>Escopo</h4>
            <p className="texto-2" style={{ fontSize: 13.5, whiteSpace: 'pre-wrap' }}>
              {tap.escopo || <span className="texto-3">Sem proposta vinculada — descreva o escopo na proposta de origem.</span>}
            </p>
          </div>
          <div>
            <h4>Premissas</h4>
            <p className="texto-2" style={{ fontSize: 13.5, whiteSpace: 'pre-wrap' }}>
              {tap.premissas || <span className="texto-3">—</span>}
            </p>
          </div>
        </div>

        <div>
          <h4>Cronograma (linha de base) — {tap.metodologia}</h4>
          <table className="tabela">
            <thead><tr><th>Fase</th><th>Início</th><th>Fim</th></tr></thead>
            <tbody>
              {tap.fases_baseline.map((f) => (
                <tr key={f.nome}>
                  <td><span className={`badge ${corFase(f.nome)}`}>{f.nome}</span></td>
                  <td className="mono" style={{ fontSize: 12.5 }}>{fmtData(f.inicio)}</td>
                  <td className="mono" style={{ fontSize: 12.5 }}>{fmtData(f.fim)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div>
          <h4>Equipe alocada</h4>
          {tap.equipe.length === 0 ? (
            <div className="texto-3" style={{ fontSize: 13 }}>Nenhum consultor alocado ainda.</div>
          ) : (
            <table className="tabela">
              <thead><tr><th>Consultor</th><th>Módulo</th><th>Fase</th><th className="num">h/sem</th><th>Período</th></tr></thead>
              <tbody>
                {tap.equipe.map((m, i) => (
                  <tr key={i}>
                    <td>{m.consultor} <span className="texto-3" style={{ fontSize: 12 }}>({SENIORIDADE[m.senioridade] || m.senioridade})</span></td>
                    <td>{m.modulo_sap || '—'}</td>
                    <td><span className={`badge ${corFase(m.fase)}`}>{m.fase}</span></td>
                    <td className="num">{fmtHoras(m.horas_semana)}</td>
                    <td className="mono" style={{ fontSize: 12 }}>{m.periodo}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {tap.riscos_iniciais.length > 0 && (
          <div>
            <h4>Riscos identificados</h4>
            <ul className="lista-atividades">
              {tap.riscos_iniciais.map((r) => (
                <li key={r.id}>
                  <span style={{ flex: 1 }}>{r.titulo}</span>
                  <span className={`badge ${r.severidade === 'critica' ? 'badge-vermelho' : r.severidade === 'moderada' ? 'badge-laranja' : 'badge-cinza'}`}>
                    {r.severidade}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Modal>
  )
}

/** Pedido de alocação que passa pela fila de aprovações — com prévia de
 * conflitos calculada pelo motor ANTES de submeter. */
function ModalSolicitarAlocacao({ fase, fases, consultores, onFechar, onCriada }) {
  const { sessao } = useSessao()
  const [form, setForm] = useState({
    consultor_id: consultores[0]?.id ?? '',
    fase_id: fase.id,
    data_inicio: fase.data_inicio_prevista,
    data_fim: fase.data_fim_prevista,
    horas_semana: 20,
    taxa_hora_venda: '',
    justificativa: '',
  })
  const [previa, setPrevia] = useState(null)
  const [erro, setErro] = useState(null)
  const [ocupado, setOcupado] = useState(false)

  useEffect(() => {
    if (!form.consultor_id || !form.data_inicio || !form.data_fim || !(form.horas_semana > 0)) {
      setPrevia(null)
      return
    }
    let cancelado = false
    api.post('/solicitacoes-alocacao/previa-conflitos', {
      consultor_id: Number(form.consultor_id),
      data_inicio: form.data_inicio,
      data_fim: form.data_fim,
      horas_semana: Number(form.horas_semana),
    }).then((r) => { if (!cancelado) setPrevia(r) }).catch(() => {})
    return () => { cancelado = true }
  }, [form.consultor_id, form.data_inicio, form.data_fim, form.horas_semana])

  const enviar = async () => {
    setOcupado(true)
    setErro(null)
    try {
      await api.post('/solicitacoes-alocacao', {
        consultor_id: Number(form.consultor_id),
        fase_id: Number(form.fase_id),
        data_inicio: form.data_inicio,
        data_fim: form.data_fim,
        horas_semana: Number(form.horas_semana),
        taxa_hora_venda: form.taxa_hora_venda === '' ? null : Number(form.taxa_hora_venda),
        justificativa: form.justificativa,
        solicitante: sessao?.nome ?? '',
      })
      onCriada()
    } catch (e) {
      setErro(e.message)
      setOcupado(false)
    }
  }

  const set = (chave, valor) => setForm((f) => ({ ...f, [chave]: valor }))

  return (
    <Modal larga titulo="Solicitar alocação" onFechar={onFechar}
      rodape={<>
        <button className="botao botao-fantasma" onClick={onFechar}>Cancelar</button>
        <button className="botao botao-primario" disabled={ocupado || !form.consultor_id} onClick={enviar}>
          {ocupado ? 'Enviando…' : 'Enviar para aprovação'}
        </button>
      </>}>
      {erro && <div className="mensagem-erro">{erro}</div>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div className="form-linha">
          <div className="campo" style={{ flex: 2 }}>
            <label htmlFor="sol-consultor">Consultor</label>
            <select id="sol-consultor" value={form.consultor_id} onChange={(e) => set('consultor_id', e.target.value)}>
              {consultores.map((c) => (
                <option key={c.id} value={c.id}>{c.nome} · {SENIORIDADE[c.senioridade] || c.senioridade}</option>
              ))}
            </select>
          </div>
          <div className="campo" style={{ flex: 1 }}>
            <label htmlFor="sol-fase">Fase</label>
            <select id="sol-fase" value={form.fase_id} onChange={(e) => set('fase_id', e.target.value)}>
              {fases.map((f) => <option key={f.id} value={f.id}>{f.nome}</option>)}
            </select>
          </div>
        </div>
        <div className="form-linha">
          <div className="campo">
            <label htmlFor="sol-inicio">Início</label>
            <input id="sol-inicio" type="date" value={form.data_inicio} onChange={(e) => set('data_inicio', e.target.value)} />
          </div>
          <div className="campo">
            <label htmlFor="sol-fim">Fim</label>
            <input id="sol-fim" type="date" value={form.data_fim} onChange={(e) => set('data_fim', e.target.value)} />
          </div>
          <div className="campo">
            <label htmlFor="sol-horas">Horas/semana</label>
            <input id="sol-horas" className="mono" type="number" min="1" max="60" value={form.horas_semana}
              onChange={(e) => set('horas_semana', e.target.value)} />
          </div>
          <div className="campo">
            <label htmlFor="sol-taxa">Taxa (R$/h)</label>
            <input id="sol-taxa" className="mono" type="number" min="0" step="0.01" placeholder="padrão do consultor"
              value={form.taxa_hora_venda} onChange={(e) => set('taxa_hora_venda', e.target.value)} />
          </div>
        </div>
        <div className="campo">
          <label htmlFor="sol-justificativa">Justificativa</label>
          <textarea id="sol-justificativa" rows={2} value={form.justificativa}
            onChange={(e) => set('justificativa', e.target.value)}
            placeholder="Por que este consultor, nesta fase, neste período?"
            style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit', fontSize: 14 }} />
        </div>

        {previa && (
          <div className="previa-conflitos" style={{
            border: '1px solid', borderRadius: 'var(--raio-2)', padding: '10px 14px',
            borderColor: previa.conflito ? '#f2c7cb' : 'var(--borda)',
            background: previa.conflito ? 'var(--vermelho-fundo)' : 'var(--superficie)',
          }}>
            {previa.conflito ? (
              <>
                <strong style={{ color: 'var(--vermelho)', fontSize: 13 }}>⚠ Conflito detectado</strong>
                <div className="texto-2" style={{ fontSize: 12.5, marginTop: 4 }}>
                  {previa.semanas.length > 0 && (
                    <>Excede a capacidade em {previa.semanas.length} semana(s) — pico de +{Math.max(...previa.semanas.map((w) => w.excesso))}h na semana de {fmtData(previa.semanas[0].semana)}. </>
                  )}
                  {previa.ausencias.length > 0 && <>Há ausência aprovada dentro do período. </>}
                  O pedido pode ser enviado mesmo assim — o gestor decide com essa informação.
                </div>
              </>
            ) : (
              <span className="texto-2" style={{ fontSize: 12.5, color: 'var(--verde)', fontWeight: 600 }}>
                ✓ Sem conflitos: o consultor tem capacidade no período.
              </span>
            )}
          </div>
        )}
      </div>
    </Modal>
  )
}

function ModalStatusReport({ report, onFechar }) {
  return (
    <Modal extraLarga classeExtra="modal-imprimivel"
      titulo={`Status Report — ${report.projeto}`}
      onFechar={onFechar}
      rodape={<>
        <button className="botao botao-fantasma" onClick={onFechar}>Fechar</button>
        <button className="botao botao-primario" onClick={() => window.print()}>Imprimir / PDF</button>
      </>}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
        <div className="linha-flex" style={{ gap: 10, flexWrap: 'wrap' }}>
          <span className="texto-2">{report.cliente}</span>
          <span className="badge badge-azul">{report.fase_atual}</span>
          {report.desvio_baseline_dias > 0
            ? <span className="badge badge-vermelho mono">+{report.desvio_baseline_dias}d vs baseline</span>
            : <span className="badge badge-verde">no prazo da baseline</span>}
          <span className="espacador" />
          <span className="texto-3" style={{ fontSize: 12 }}>gerado em {fmtData(report.gerado_em)}</span>
        </div>

        <div className="grid-kpi" style={{ margin: 0 }}>
          <div className="card kpi">
            <div className="rotulo">Receita prevista</div>
            <div className="valor">{fmtBRL(report.receita_prevista)}</div>
          </div>
          <div className="card kpi">
            <div className="rotulo">Receita realizada</div>
            <div className="valor">{fmtBRL(report.receita_realizada)}</div>
          </div>
          <div className="card kpi">
            <div className="rotulo">Horas real / prev</div>
            <div className="valor">{fmtHoras(report.horas_realizadas)} <span className="texto-3" style={{ fontSize: 14 }}>/ {fmtHoras(report.horas_previstas)}</span></div>
          </div>
          <div className="card kpi">
            <div className="rotulo">Pendências abertas</div>
            <div className="valor" style={{ color: report.pendencias_abertas ? 'var(--laranja)' : 'var(--texto)' }}>{report.pendencias_abertas}</div>
          </div>
        </div>

        <div>
          <h4>Fases</h4>
          <table className="tabela">
            <thead>
              <tr><th>Fase</th><th>Período previsto</th><th className="num">Desvio</th><th className="num">Entregas</th><th>Gate</th></tr>
            </thead>
            <tbody>
              {report.fases.map((f) => (
                <tr key={f.nome}>
                  <td style={{ fontWeight: f.atual ? 700 : 400 }}>{f.nome}{f.atual ? ' ◂' : ''}</td>
                  <td className="mono" style={{ fontSize: 12.5 }}>{fmtData(f.inicio)} – {fmtData(f.fim)}</td>
                  <td className="num" style={{ color: f.desvio_baseline_dias > 0 ? 'var(--vermelho)' : 'var(--texto-3)' }}>
                    {f.desvio_baseline_dias > 0 ? `+${f.desvio_baseline_dias}d` : '—'}
                  </td>
                  <td className="num">{f.entregas}</td>
                  <td>
                    <span className={`badge ${f.gate.aprovado ? 'badge-verde' : f.gate.vermelho > 0 ? 'badge-vermelho' : 'badge-cinza'}`}>
                      {f.gate.verde}/{f.gate.total}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {report.riscos_abertos.length > 0 && (
          <div>
            <h4>Riscos abertos</h4>
            <ul className="lista-atividades">
              {report.riscos_abertos.map((r) => (
                <li key={r.id}>
                  <span className={`badge ${r.severidade === 'critica' ? 'badge-vermelho' : r.severidade === 'moderada' ? 'badge-laranja' : 'badge-cinza'}`}>{r.severidade}</span>
                  <span style={{ flex: 1 }}>{r.titulo}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {report.mudancas_abertas.length > 0 && (
          <div>
            <h4>Mudanças aguardando decisão</h4>
            <ul className="lista-atividades">
              {report.mudancas_abertas.map((m) => (
                <li key={m.id}>
                  <span style={{ flex: 1 }}>{m.titulo}</span>
                  <span className="mono texto-2">{fmtHoras(m.impacto_horas)} · {fmtBRLExato(m.impacto_valor)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {report.licoes_aprendidas && (
          <div>
            <h4>Lições aprendidas</h4>
            <p className="texto-2" style={{ margin: 0, fontSize: 13.5 }}>{report.licoes_aprendidas}</p>
          </div>
        )}
      </div>
    </Modal>
  )
}

/** Encerramento formal: registra lições aprendidas e fecha o projeto. */
function ModalEncerrar({ projeto, onFechar, onEncerrado }) {
  const [licoes, setLicoes] = useState('')
  const [erro, setErro] = useState(null)

  const encerrar = async () => {
    setErro(null)
    try {
      await api.post(`/projetos/${projeto.id}/encerrar`, { licoes_aprendidas: licoes })
      onEncerrado()
    } catch (e) { setErro(e.message) }
  }

  const gatesAbertos = projeto.fases.filter((f) => f.gate && f.gate.total > 0 && !f.gate.aprovado).length

  return (
    <Modal titulo={`Encerrar projeto — ${projeto.nome}`} onFechar={onFechar}
      rodape={<>
        <button className="botao botao-fantasma" onClick={onFechar}>Cancelar</button>
        <button className="botao botao-primario" onClick={encerrar}>Encerrar formalmente</button>
      </>}>
      {erro && <div className="mensagem-erro">{erro}</div>}
      {gatesAbertos > 0 && (
        <div className="mensagem-erro" style={{ background: 'var(--laranja-fundo)', color: 'var(--laranja)', borderColor: '#f5d3b3' }}>
          Atenção: {gatesAbertos} fase(s) ainda sem Quality Gate verde. O encerramento fica registrado mesmo assim.
        </div>
      )}
      <div className="campo">
        <label htmlFor="enc-licoes">Lições aprendidas</label>
        <textarea id="enc-licoes" rows={5} value={licoes} autoFocus
          onChange={(e) => setLicoes(e.target.value)}
          placeholder="O que funcionou, o que faria diferente, recomendações para os próximos projetos…"
          style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit', fontSize: 14 }} />
        <span className="ajuda">Entram no Status Report, que serve como termo de encerramento.</span>
      </div>
    </Modal>
  )
}

/** Edição da data-fim de uma fase: simula, mostra o diff antes→depois e só
 * aplica a cascata após confirmação. */
function ModalReagendar({ fase, onFechar, onAplicado }) {
  const [novaData, setNovaData] = useState(fase.data_fim_prevista)
  const [diff, setDiff] = useState(null)
  const [erro, setErro] = useState(null)
  const [ocupado, setOcupado] = useState(false)

  const simular = async () => {
    setOcupado(true)
    setErro(null)
    try {
      setDiff(await api.post(`/fases/${fase.id}/reagendar`, { nova_data_fim: novaData, aplicar: false }))
    } catch (e) {
      setErro(e.message)
      setDiff(null)
    } finally {
      setOcupado(false)
    }
  }

  const aplicar = async () => {
    setOcupado(true)
    setErro(null)
    try {
      await api.post(`/fases/${fase.id}/reagendar`, { nova_data_fim: novaData, aplicar: true })
      onAplicado()
    } catch (e) {
      setErro(e.message)
      setOcupado(false)
    }
  }

  return (
    <Modal extraLarga icone={IC_CALENDAR} titulo={`Mover data-fim — fase ${fase.nome}`} onFechar={onFechar}
      rodape={<>
        <button className="botao botao-fantasma" onClick={onFechar}>Cancelar</button>
        <button className="botao botao-primario" onClick={aplicar}
          disabled={ocupado || !diff || diff.delta_dias === 0}>
          <Icone d={IC_CHECK} size={16} />
          Aplicar recálculo em cascata
        </button>
      </>}>
      {erro && <div className="mensagem-erro">{erro}</div>}
      <div style={{
        border: '1px solid var(--borda)', borderRadius: 'var(--raio-2)', background: 'var(--superficie-brilho)',
        padding: 16, display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'flex-end', marginBottom: 24,
      }}>
        <div className="campo" style={{ flex: 1, minWidth: 190 }}>
          <label htmlFor="rg-fim">Data-fim atual ({fase.nome})</label>
          <input id="rg-fim" value={fmtData(fase.data_fim_prevista)} disabled />
        </div>
        <div className="campo" style={{ flex: 1, minWidth: 190 }}>
          <label htmlFor="rg-nova">Nova data-fim</label>
          <input id="rg-nova" type="date" value={novaData} min={fase.data_inicio_prevista}
            onChange={(e) => { setNovaData(e.target.value); setDiff(null) }} />
        </div>
        <button className="botao botao-secundario" onClick={simular} disabled={ocupado || !novaData}>
          <Icone d={IC_REFRESH} size={16} />
          {ocupado ? 'Calculando…' : 'Simular impacto'}
        </button>
      </div>
      {diff
        ? <DiffReagendamento diff={diff} />
        : <div className="vazio">Escolha a nova data-fim e clique em “Simular impacto” para ver o impacto antes → depois.</div>}
    </Modal>
  )
}

function ModalAlocar({ fase, consultores, onFechar, onCriado }) {
  const [form, setForm] = useState({
    consultor_id: consultores[0]?.id ?? '',
    horas_semana: 20,
    taxa_hora_venda: consultores[0]?.taxa_hora_venda ?? 0,
    data_inicio: fase.data_inicio_prevista,
    data_fim: fase.data_fim_prevista,
  })
  const [erro, setErro] = useState(null)

  const aoTrocarConsultor = (idStr) => {
    const c = consultores.find((x) => x.id === Number(idStr))
    setForm({ ...form, consultor_id: idStr, taxa_hora_venda: c ? c.taxa_hora_venda : form.taxa_hora_venda })
  }

  const salvar = async (e) => {
    e.preventDefault()
    setErro(null)
    try {
      await api.post('/alocacoes', {
        consultor_id: Number(form.consultor_id),
        fase_id: fase.id,
        data_inicio: form.data_inicio,
        data_fim: form.data_fim,
        horas_semana: Number(form.horas_semana),
        taxa_hora_venda: Number(form.taxa_hora_venda),
      })
      onCriado()
    } catch (err) {
      setErro(err.message)
    }
  }

  const consultorSel = consultores.find((x) => x.id === Number(form.consultor_id))

  return (
    <Modal titulo={`Alocar consultor — fase ${fase.nome}`} onFechar={onFechar}
      rodape={<>
        <button className="botao botao-fantasma" onClick={onFechar}>Cancelar</button>
        <button className="botao botao-primario" type="submit" form="form-alocacao" disabled={!form.consultor_id}>Alocar</button>
      </>}>
      <form id="form-alocacao" onSubmit={salvar} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {erro && <div className="mensagem-erro">{erro}</div>}
        <div className="campo">
          <label htmlFor="al-consultor">Consultor *</label>
          <select id="al-consultor" value={form.consultor_id} onChange={(e) => aoTrocarConsultor(e.target.value)}>
            {consultores.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome} ({SENIORIDADE[c.senioridade]} — tabela {fmtBRLExato(c.taxa_hora_venda)}/h)
              </option>
            ))}
          </select>
        </div>
        <div className="form-linha">
          <div className="campo">
            <label htmlFor="al-horas">Horas por semana *</label>
            <input id="al-horas" type="number" min="1" max="60" step="1" value={form.horas_semana}
              onChange={(e) => setForm({ ...form, horas_semana: e.target.value })} required />
          </div>
          <div className="campo">
            <label htmlFor="al-taxa">Taxa hora-venda (R$) *</label>
            <input id="al-taxa" type="number" min="0" step="0.01" value={form.taxa_hora_venda}
              onChange={(e) => setForm({ ...form, taxa_hora_venda: e.target.value })} required />
            {consultorSel && Number(form.taxa_hora_venda) !== consultorSel.taxa_hora_venda && (
              <span className="ajuda" style={{ color: 'var(--laranja)' }}>
                Taxa negociada — difere da tabela do consultor ({fmtBRLExato(consultorSel.taxa_hora_venda)}/h).
              </span>
            )}
          </div>
        </div>
        <div className="form-linha">
          <div className="campo">
            <label htmlFor="al-inicio">Início da alocação *</label>
            <input id="al-inicio" type="date" value={form.data_inicio}
              onChange={(e) => setForm({ ...form, data_inicio: e.target.value })} required />
          </div>
          <div className="campo">
            <label htmlFor="al-fim">Fim da alocação *</label>
            <input id="al-fim" type="date" value={form.data_fim} min={form.data_inicio}
              onChange={(e) => setForm({ ...form, data_fim: e.target.value })} required />
          </div>
        </div>
        <span className="ajuda">Default: o período previsto da fase. Receita prevista = horas previstas × taxa hora-venda da alocação.</span>
      </form>
    </Modal>
  )
}
