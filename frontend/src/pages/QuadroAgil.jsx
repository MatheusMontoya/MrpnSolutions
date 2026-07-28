import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import Icone from '../components/Icone'
import Modal from '../components/Modal'
import { SkeletonPagina } from '../components/Skeleton'
import { corFase, fmtData, fmtHoras, fmtPct, iniciais } from '../format'

const IC = {
  voltar: ['M19 12H5', 'M12 19l-7-7 7-7'],
  raio: ['M13 2 3 14h9l-1 8 10-12h-9l1-8z'],
  mais: ['M12 5v14', 'M5 12h14'],
  seta_dir: ['M5 12h14', 'M12 5l7 7-7 7'],
  seta_esq: ['M19 12H5', 'M12 19l-7-7 7-7'],
  check: ['M20 6 9 17l-5-5'],
  reabrir: ['M3 12a9 9 0 1 0 3-6.7L3 8', 'M3 3v5h5'],
  devolver: ['M12 3v10', 'M8 9l4 4 4-4', 'M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2'],
}

/* Ação de avançar por coluna: rótulo explícito em vez de seta nua, para o
 * cartão dizer PARA ONDE o clique leva. Cabe em uma linha na largura da coluna. */
const AVANCAR = {
  pendente: ['em_andamento', 'Iniciar', 'seta_dir'],
  em_andamento: ['concluida', 'Concluir', 'check'],
}

const COLUNAS = [
  ['pendente', 'A fazer'],
  ['em_andamento', 'Em andamento'],
  ['concluida', 'Concluída'],
]

const BADGE_SPRINT = {
  planejada: ['badge-cinza', 'Planejada'],
  ativa: ['badge-verde', 'Ativa'],
  encerrada: ['badge-azul', 'Encerrada'],
}

/** Modo ágil/híbrido: o cronograma Activate manda no prazo e na receita; a
 * sprint organiza o dia a dia — backlog (entregas das fases) → kanban. */
export default function QuadroAgil() {
  const { id } = useParams()
  const [quadro, setQuadro] = useState(null)
  const [erro, setErro] = useState(null)
  const [sprintSel, setSprintSel] = useState(null) // id da sprint em foco
  const [modalNova, setModalNova] = useState(false)

  const carregar = useCallback(() => {
    api.get(`/projetos/${id}/agil`).then((q) => {
      setQuadro(q)
      setSprintSel((atual) => atual ?? q.sprint_ativa_id ?? q.sprints[q.sprints.length - 1]?.id ?? null)
    }).catch((e) => setErro(e.message))
  }, [id])

  useEffect(carregar, [carregar])

  if (erro) return <div className="mensagem-erro">{erro}</div>
  if (!quadro) return <SkeletonPagina />

  const sprint = quadro.sprints.find((s) => s.id === sprintSel) ?? null
  const sprintAberta = sprint && sprint.status !== 'encerrada'

  const moverStatus = async (a, status) => {
    try {
      await api.patch(`/atividades/${a.id}`, { status })
      carregar()
    } catch (e) { setErro(e.message) }
  }
  const moverSprint = async (a, sprintId) => {
    try {
      await api.patch(`/atividades/${a.id}/sprint`, { sprint_id: sprintId })
      carregar()
    } catch (e) { setErro(e.message) }
  }
  const iniciar = async (s) => {
    try {
      await api.post(`/sprints/${s.id}/iniciar`, {})
      carregar()
    } catch (e) { setErro(e.message) }
  }
  const encerrar = async (s) => {
    try {
      const r = await api.post(`/sprints/${s.id}/encerrar`, {})
      setErro(null)
      carregar()
      if (r.carry_over > 0) {
        window.alert(`Sprint encerrada — ${r.carry_over} atividade(s) voltou(aram) ao backlog (carry-over).`)
      }
    } catch (e) { setErro(e.message) }
  }

  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <div className="texto-3 linha-flex" style={{ fontSize: 12.5, gap: 6, marginBottom: 6 }}>
            <Link to={`/projetos/${id}`} className="link">{quadro.projeto}</Link>
            <Icone d={['M9 18l6-6-6-6']} size={13} strokeWidth={2} />
            <span>Modo ágil</span>
          </div>
          <h1 className="linha-flex" style={{ gap: 10 }}>
            <Icone d={IC.raio} size={21} /> Quadro Ágil
          </h1>
          <div className="descricao">
            O cronograma Activate manda no prazo e na receita — a sprint organiza a execução das entregas
          </div>
        </div>
        <button className="botao botao-primario" onClick={() => setModalNova(true)}>
          <Icone d={IC.mais} size={15} /> Nova sprint
        </button>
      </div>

      {/* ---- faixa de sprints ---- */}
      <div className="linha-flex" style={{ gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
        {quadro.sprints.length === 0 && (
          <span className="texto-3" style={{ fontSize: 13 }}>Nenhuma sprint ainda — crie a primeira e puxe entregas do backlog.</span>
        )}
        {quadro.sprints.map((s) => {
          const [cls, rot] = BADGE_SPRINT[s.status]
          return (
            <button key={s.id} type="button"
              className={`sprint-chip${sprintSel === s.id ? ' ativa' : ''}`}
              onClick={() => setSprintSel(s.id)}>
              <strong>{s.nome}</strong>
              <span className={`badge ${cls}`}>{rot}</span>
              <span className="mono texto-2" style={{ fontSize: 11 }}>
                {s.concluidas}/{s.total}
              </span>
            </button>
          )
        })}
      </div>

      <div className="agil-layout">
        {/* ---- kanban da sprint selecionada ---- */}
        <section className="card" style={{ minWidth: 0 }}>
          {sprint ? (
            <>
              <div className="card-cabecalho" style={{ flexWrap: 'wrap', gap: 10 }}>
                <div>
                  <h2 className="card-titulo">{sprint.nome}</h2>
                  <div className="texto-3" style={{ fontSize: 12.5, marginTop: 2 }}>
                    {fmtData(sprint.data_inicio)} – {fmtData(sprint.data_fim)}
                    {sprint.meta && <> · meta: <em>{sprint.meta}</em></>}
                  </div>
                </div>
                <div className="linha-flex" style={{ gap: 10 }}>
                  <span className="badge mono" title="Horas apontadas no período da sprint">
                    {fmtHoras(sprint.horas_no_periodo)} no período
                  </span>
                  <span className="badge badge-azul mono">{fmtPct(sprint.progresso)} concluído</span>
                  {sprint.status === 'encerrada' && sprint.carry_over > 0 && (
                    <span className="badge badge-laranja mono" title="Atividades devolvidas ao backlog no encerramento">
                      {sprint.carry_over} carry-over
                    </span>
                  )}
                  {sprint.status === 'planejada' && (
                    <button className="botao botao-primario botao-pequeno" onClick={() => iniciar(sprint)}>Iniciar sprint</button>
                  )}
                  {sprint.status === 'ativa' && (
                    <button className="botao botao-secundario botao-pequeno" onClick={() => encerrar(sprint)}>Encerrar sprint</button>
                  )}
                </div>
              </div>
              <div className="card-corpo">
                <div className="kanban" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                  {COLUNAS.map(([status, rotulo]) => {
                    const cartoes = sprint.atividades.filter((a) => a.status === status)
                    return (
                      <div className="kanban-col" key={status}>
                        <div className="titulo">{rotulo} <span className="contagem">{cartoes.length}</span></div>
                        {cartoes.map((a) => (
                          <div className="kanban-card" key={a.id}>
                            <div className="nome">{a.titulo}</div>
                            <div className="meta">
                              <span className={`badge ${corFase(a.fase)}`}>{a.fase}</span>
                              {a.responsavel && (
                                <span className="avatar-consultor" title={a.responsavel}>{iniciais(a.responsavel)}</span>
                              )}
                            </div>
                            {sprintAberta && (
                              <div className="acoes">
                                {status === 'concluida' ? (
                                  <button className="botao botao-fantasma botao-pequeno"
                                    onClick={() => moverStatus(a, 'em_andamento')}>
                                    <Icone d={IC.reabrir} size={12} /> Reabrir
                                  </button>
                                ) : (
                                  <>
                                    {status === 'em_andamento' && (
                                      <button className="botao botao-fantasma botao-pequeno icone-so"
                                        aria-label="Voltar para A fazer" title="Voltar para A fazer"
                                        onClick={() => moverStatus(a, 'pendente')}>
                                        <Icone d={IC.seta_esq} size={12} />
                                      </button>
                                    )}
                                    <button className="botao botao-secundario botao-pequeno"
                                      onClick={() => moverStatus(a, AVANCAR[status][0])}>
                                      <Icone d={IC[AVANCAR[status][2]]} size={12} /> {AVANCAR[status][1]}
                                    </button>
                                  </>
                                )}
                                <button className="botao botao-fantasma botao-pequeno icone-so"
                                  aria-label="Devolver ao backlog" title="Devolver ao backlog"
                                  onClick={() => moverSprint(a, null)}>
                                  <Icone d={IC.devolver} size={12} />
                                </button>
                              </div>
                            )}
                          </div>
                        ))}
                        {cartoes.length === 0 && <div className="texto-3" style={{ fontSize: 12, padding: '6px 4px' }}>—</div>}
                      </div>
                    )
                  })}
                </div>
              </div>
            </>
          ) : (
            <div className="vazio-ensina" style={{ padding: 40 }}>
              <Icone d={IC.raio} size={28} strokeWidth={1.5} />
              <span className="titulo">Crie a primeira sprint</span>
              <span className="dica">Defina o período e a meta; depois puxe entregas do backlog para o quadro.</span>
            </div>
          )}
        </section>

        {/* ---- backlog ---- */}
        <section className="card">
          <div className="card-cabecalho">
            <h2 className="card-titulo-secao">Backlog</h2>
            <span className="texto-3" style={{ fontSize: 12 }}>{quadro.backlog.length} entrega(s)</span>
          </div>
          <div className="card-corpo" style={{ maxHeight: 560, overflowY: 'auto', paddingTop: 4 }}>
            {quadro.backlog.length === 0 ? (
              <div className="vazio">Backlog vazio — todas as entregas estão em sprints ou concluídas.</div>
            ) : (
              <ul className="lista-atividades">
                {quadro.backlog.map((a) => (
                  <li key={a.id}>
                    <span className={`badge ${corFase(a.fase)}`} style={{ flexShrink: 0 }}>{a.fase}</span>
                    <span style={{ flex: 1, fontSize: 13 }}>{a.titulo}</span>
                    {sprint && sprintAberta && (
                      <button className="botao botao-secundario botao-pequeno" title={`Puxar para ${sprint.nome}`}
                        onClick={() => moverSprint(a, sprint.id)}>
                        <Icone d={IC.seta_dir} size={12} /> Puxar
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </div>

      {modalNova && (
        <ModalNovaSprint projetoId={id} proximoNumero={(quadro.sprints[quadro.sprints.length - 1]?.numero ?? 0) + 1}
          onFechar={() => setModalNova(false)}
          onCriada={(s) => { setModalNova(false); setSprintSel(s.id); carregar() }} />
      )}
    </>
  )
}

function ModalNovaSprint({ projetoId, proximoNumero, onFechar, onCriada }) {
  const hoje = new Date().toISOString().slice(0, 10)
  const em2semanas = new Date(Date.now() + 11 * 86400000).toISOString().slice(0, 10)
  const [form, setForm] = useState({ nome: '', meta: '', data_inicio: hoje, data_fim: em2semanas })
  const [erro, setErro] = useState(null)

  const criar = async (e) => {
    e.preventDefault()
    setErro(null)
    try {
      const s = await api.post(`/projetos/${projetoId}/sprints`, form)
      onCriada(s)
    } catch (err) { setErro(err.message) }
  }

  return (
    <Modal titulo={`Nova sprint (Sprint ${proximoNumero})`} onFechar={onFechar}
      rodape={<>
        <button className="botao botao-fantasma" onClick={onFechar}>Cancelar</button>
        <button className="botao botao-primario" type="submit" form="form-sprint">Criar sprint</button>
      </>}>
      <form id="form-sprint" onSubmit={criar} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {erro && <div className="mensagem-erro">{erro}</div>}
        <div className="campo">
          <label htmlFor="sp-nome">Nome (opcional)</label>
          <input id="sp-nome" value={form.nome} placeholder={`Sprint ${proximoNumero}`}
            onChange={(e) => setForm({ ...form, nome: e.target.value })} />
        </div>
        <div className="campo">
          <label htmlFor="sp-meta">Meta da sprint</label>
          <input id="sp-meta" value={form.meta} placeholder="Ex.: fechar integração MM→FI com testes unitários"
            onChange={(e) => setForm({ ...form, meta: e.target.value })} />
        </div>
        <div className="form-linha">
          <div className="campo">
            <label htmlFor="sp-inicio">Início</label>
            <input id="sp-inicio" type="date" value={form.data_inicio} required
              onChange={(e) => setForm({ ...form, data_inicio: e.target.value })} />
          </div>
          <div className="campo">
            <label htmlFor="sp-fim">Fim</label>
            <input id="sp-fim" type="date" value={form.data_fim} required
              onChange={(e) => setForm({ ...form, data_fim: e.target.value })} />
          </div>
        </div>
      </form>
    </Modal>
  )
}
