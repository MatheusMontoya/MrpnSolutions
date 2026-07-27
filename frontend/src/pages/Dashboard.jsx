import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import GraficoBarras from '../components/GraficoBarras'
import Icone from '../components/Icone'
import { SkeletonPagina } from '../components/Skeleton'
import { SENIORIDADE, corFase, fmtBRL, fmtData, fmtHoras, fmtPct, iniciais } from '../format'

const IC_FAISCA = ['M13 2 3 14h9l-1 8 10-12h-9l1-8z']
const FASES = ['Discover', 'Prepare', 'Explore', 'Realize', 'Deploy', 'Run']

const badgeUtilizacao = {
  superalocado: ['badge-vermelho', 'Superalocado'],
  ocioso: ['badge-laranja', 'Ocioso'],
  ok: ['badge-verde', 'OK'],
}

const AZUL_SUAVE = 'var(--azul-fill-suave)'

export default function Dashboard() {
  const [dados, setDados] = useState(null)
  const [erro, setErro] = useState(null)
  const [atividades, setAtividades] = useState(null)

  useEffect(() => {
    api.get('/dashboard').then(setDados).catch((e) => setErro(e.message))
  }, [])

  useEffect(() => {
    api.get('/apontamentos/atividades?limite=10').then(setAtividades).catch(() => setAtividades([]))
  }, [])

  if (erro) return <div className="mensagem-erro">{erro}</div>
  if (!dados) return <SkeletonPagina kpis />

  const totalPrevisto = dados.receita_mensal.reduce((s, m) => s + m.prevista, 0)
  const totalRealizado = dados.receita_mensal.reduce((s, m) => s + m.realizada, 0)
  const margemPct = totalPrevisto > 0 ? dados.margem_prevista / totalPrevisto : 0
  const superalocados = dados.utilizacao_semana.filter((u) => u.status === 'superalocado').length
  const ociosos = dados.utilizacao_semana.filter((u) => u.status === 'ocioso').length

  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <h1>Visão geral</h1>
          <div className="descricao">
            Receita, margem e utilização da equipe — tudo calculado pelo motor de hora-homem
          </div>
        </div>
        <Link to="/copiloto" className="botao botao-secundario">
          <Icone d={IC_FAISCA} size={15} /> Ver insights do copiloto
        </Link>
      </div>

      <div className="grid-kpi">
        <div className="card kpi">
          <div className="rotulo">Receita prevista</div>
          <div className="valor">{fmtBRL(totalPrevisto)}</div>
          <div className="detalhe">Acumulado no período</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Receita realizada</div>
          <div className="valor">{fmtBRL(totalRealizado)}</div>
          <div className="detalhe">Até a data atual</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Margem prevista</div>
          {/* donut de margem vs meta — a leitura de "estamos no alvo?" em 1 olhada */}
          <div className="anel-linha" style={{ marginTop: 8 }}>
            <span
              className="anel"
              style={{
                '--anel-pct': Math.min(Math.round(margemPct * 100), 100),
                '--anel-cor': margemPct >= dados.meta_margem ? 'var(--verde)' : 'var(--laranja)',
              }}
              role="img"
              aria-label={`Margem de ${fmtPct(margemPct)} contra meta de ${fmtPct(dados.meta_margem)}`}
            >
              <span className="anel-valor">{Math.round(margemPct * 100)}%</span>
            </span>
            <span>
              <span className="valor" style={{ display: 'block', marginTop: 0 }}>{fmtBRL(dados.margem_prevista)}</span>
              <span className="detalhe">Meta: {fmtPct(dados.meta_margem)}</span>
            </span>
          </div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Alertas de alocação</div>
          <div className="kpi-duplo">
            <div className="metade">
              <span className="n" style={{ color: superalocados ? 'var(--vermelho)' : 'var(--texto)' }}>{superalocados}</span>
              <span className="r">Super</span>
            </div>
            <div className="divisor" />
            <div className="metade">
              <span className="n" style={{ color: ociosos ? 'var(--laranja)' : 'var(--texto)' }}>{ociosos}</span>
              <span className="r">Ocioso</span>
            </div>
          </div>
          <div className="detalhe">
            {dados.aprovacoes_pendentes > 0 || dados.pendencias_abertas > 0
              ? <>
                  {dados.aprovacoes_pendentes > 0 && <Link className="link" to="/aprovacoes" style={{ fontSize: 12 }}>{dados.aprovacoes_pendentes} aprovações</Link>}
                  {dados.aprovacoes_pendentes > 0 && dados.pendencias_abertas > 0 && ' · '}
                  {dados.pendencias_abertas > 0 && <Link className="link" to="/pendencias" style={{ fontSize: 12 }}>{dados.pendencias_abertas} pendências</Link>}
                </>
              : 'Ação requerida'}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-cabecalho">
          <h2 className="card-titulo-secao">Receita prevista vs realizada por mês</h2>
          <div className="grafico-legenda">
            <span className="item"><span className="quadrado" style={{ background: AZUL_SUAVE }} /> Prevista</span>
            <span className="item"><span className="quadrado" style={{ background: 'var(--azul)' }} /> Realizada</span>
          </div>
        </div>
        <div className="card-corpo">
          <GraficoBarras dados={dados.receita_mensal} mesCorrente={dados.hoje.slice(0, 7)} mostrarLegenda={false} />
        </div>
      </div>

      <div className="grid-2-igual secao">
        <div className="card">
          <h2 className="card-titulo-secao">Projetos ativos — fase Activate atual</h2>
          <div className="card-corpo" style={{ paddingTop: 10 }}>
            <table className="tabela">
              <thead>
                <tr>
                  <th>Projeto</th><th>Cliente</th><th>Fase (1-6)</th>
                </tr>
              </thead>
              <tbody>
                {dados.projetos_ativos.map((p) => (
                  <tr key={p.id}>
                    <td><Link className="link" to={`/projetos/${p.id}`}>{p.nome}</Link></td>
                    <td className="texto-2">{p.cliente}</td>
                    <td>
                      <span className="trilha-fases" aria-label={`Fase atual: ${p.fase_atual}`}
                        title={p.fase_atual}>
                        {FASES.map((f, i) => (
                          <span key={f} title={f}
                            className={`ponto${i < p.fase_atual_ordem ? ' feita' : ''}${i === p.fase_atual_ordem ? ' atual' : ''}`} />
                        ))}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-cabecalho">
            <h2 className="card-titulo-secao">Utilização na semana corrente</h2>
            <span className="texto-3" style={{ fontSize: 12 }}>semana de {fmtData(dados.semana_corrente)}</span>
          </div>
          <div className="card-corpo" style={{ paddingTop: 10 }}>
            <table className="tabela">
              <thead>
                <tr><th>Consultor</th><th>Carga</th><th>Status</th></tr>
              </thead>
              <tbody>
                {dados.utilizacao_semana.map((u) => {
                  const [cls, rotulo] = badgeUtilizacao[u.status]
                  const corBarra = u.status === 'superalocado' ? 'vermelho' : u.status === 'ocioso' ? 'laranja' : 'verde'
                  return (
                    <tr key={u.consultor_id}>
                      <td>
                        <div className="linha-flex" style={{ gap: 7 }}>
                          <span>{u.nome}{u.modulo_sap && <span className="texto-3"> ({u.modulo_sap})</span>}</span>
                          <span className="chip-senioridade">{SENIORIDADE[u.senioridade]}</span>
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <span className="mono" style={{ minWidth: 40 }}>{fmtHoras(u.horas)}</span>
                          <div className="barra" role="img" aria-label={`Utilização ${fmtPct(u.utilizacao)}`}
                            title={`${fmtPct(u.utilizacao)} da jornada`}>
                            <div className={`preenchido ${corBarra}`} style={{ width: `${Math.min(u.utilizacao, 1.25) / 1.25 * 100}%` }} />
                          </div>
                        </div>
                      </td>
                      <td><span className={`badge ${cls}`}>{rotulo}</span></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="card secao">
        <h2 className="card-titulo-secao">Atividades recentes</h2>
        <div className="card-corpo" style={{ paddingTop: 4 }}>
          {atividades && atividades.length === 0 && (
            <p className="texto-3" style={{ padding: '8px 0' }}>Nenhuma atividade descrita ainda.</p>
          )}
          {atividades && atividades.length > 0 && (
            <ul className="feed-atividades">
              {atividades.map((a) => (
                <li key={a.id} className="feed-item">
                  <span className="avatar-consultor" title={a.consultor}>{iniciais(a.consultor)}</span>
                  <div className="feed-conteudo">
                    <div className="feed-cabecalho">
                      <span className="feed-consultor">{a.consultor}</span>
                      <Link className="link" to={`/projetos/${a.projeto_id}`}>{a.projeto}</Link>
                      <span className={`badge ${corFase(a.fase)}`}>{a.fase}</span>
                      <span className="feed-meta">
                        <span className="mono">{fmtHoras(a.horas)}</span>
                        <span className="feed-sep">·</span>
                        <span>{fmtData(a.data)}</span>
                      </span>
                    </div>
                    <p className="feed-descricao">{a.descricao || <span className="texto-3">Sem descrição.</span>}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </>
  )
}
