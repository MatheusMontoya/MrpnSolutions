import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import FalhaAoCarregar from '../components/FalhaAoCarregar'
import BotaoExportar from '../components/BotaoExportar'
import Icone from '../components/Icone'
import { SkeletonPagina } from '../components/Skeleton'
import { fmtBRL, fmtBRLExato, fmtData, fmtMes, fmtPct, iniciais } from '../format'

const IC_RECEBER = ['M20 6 9 17l-5-5']
// eixos usam a própria fonte da interface com figuras tabulares
const NUM = { fontFamily: 'var(--fonte)', fontVariantNumeric: 'tabular-nums' }

/** Financeiro gerencial: vista = fluxo | rentabilidade | pagar. */
export default function FinanceiroGerencial({ vista }) {
  const [dados, setDados] = useState(null)
  const [erro, setErro] = useState(null)

  const endpoint = { fluxo: '/financeiro/fluxo-caixa', rentabilidade: '/financeiro/rentabilidade', pagar: '/financeiro/contas-a-pagar' }[vista]

  const carregar = () => api.get(endpoint).then(setDados).catch((e) => setErro(e.message))
  useEffect(() => { setDados(null); carregar() }, [endpoint]) // eslint-disable-line react-hooks/exhaustive-deps

  if (erro) return <FalhaAoCarregar erro={erro} aoTentarDeNovo={carregar} />
  if (!dados) return <SkeletonPagina />

  if (vista === 'fluxo') return <Fluxo serie={dados.serie} />
  if (vista === 'rentabilidade') return <Rentabilidade ranking={dados.ranking} />
  return <ContasAPagar dados={dados} recarregar={carregar} />
}

/* ---------------- fluxo de caixa ---------------- */

function Fluxo({ serie }) {
  const ultimo = serie[serie.length - 1]
  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <h1>Fluxo de Caixa</h1>
          <div className="descricao">Entradas (faturas por competência) × saídas (custo das horas apontadas + despesas)</div>
        </div>
      </div>

      <div className="grid-kpi" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
        <div className="card kpi">
          <div className="rotulo">Entradas recebidas</div>
          <div className="valor" style={{ color: 'var(--verde)' }}>
            {fmtBRL(serie.reduce((s, m) => s + m.entrada_recebida, 0))}
          </div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Entradas projetadas</div>
          <div className="valor" style={{ color: 'var(--azul)' }}>
            {fmtBRL(serie.reduce((s, m) => s + m.entrada_projetada, 0))}
          </div>
          <div className="detalhe">emitidas + previstas</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Saldo acumulado projetado</div>
          <div className="valor" style={{ color: (ultimo?.acumulado ?? 0) >= 0 ? 'var(--verde)' : 'var(--vermelho)' }}>
            {fmtBRL(ultimo?.acumulado ?? 0)}
          </div>
          <div className="detalhe">até {ultimo ? fmtMes(ultimo.mes) : '—'}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-cabecalho">
          <h2 className="card-titulo-secao">Entradas × Saídas por mês</h2>
          <div className="grafico-legenda">
            <span className="item"><span className="quadrado" style={{ background: 'var(--verde)' }} /> Recebido</span>
            <span className="item"><span className="quadrado" style={{ background: 'var(--azul-fill-suave)' }} /> Projetado</span>
            <span className="item"><span className="quadrado" style={{ background: 'var(--laranja)' }} /> Saídas</span>
          </div>
        </div>
        <div className="card-corpo">
          <GraficoFluxo serie={serie} />
        </div>
      </div>

      <div className="card secao">
        <div className="card-corpo" style={{ paddingTop: 10 }}>
          <table className="tabela">
            <thead>
              <tr>
                <th>Mês</th><th className="num">Recebido</th><th className="num">Projetado</th>
                <th className="num">Saídas</th><th className="num">Resultado</th><th className="num">Acumulado</th>
              </tr>
            </thead>
            <tbody>
              {serie.map((m) => (
                <tr key={m.mes}>
                  <td className="mono" style={{ fontWeight: 600 }}>{fmtMes(m.mes)}</td>
                  <td className="num" style={{ color: 'var(--verde)' }}>{fmtBRLExato(m.entrada_recebida)}</td>
                  <td className="num texto-2">{fmtBRLExato(m.entrada_projetada)}</td>
                  <td className="num" style={{ color: 'var(--laranja)' }}>{fmtBRLExato(m.saida)}</td>
                  <td className="num" style={{ color: m.resultado >= 0 ? 'var(--verde)' : 'var(--vermelho)', fontWeight: 600 }}>
                    {fmtBRLExato(m.resultado)}
                  </td>
                  <td className="num" style={{ color: m.acumulado >= 0 ? 'var(--texto)' : 'var(--vermelho)' }}>
                    {fmtBRLExato(m.acumulado)}
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

function GraficoFluxo({ serie }) {
  if (!serie.length) return <div className="vazio">Sem movimentos ainda.</div>
  const largura = 1080
  const altura = 230
  const margem = { topo: 14, dir: 12, baixo: 26, esq: 56 }
  const w = largura - margem.esq - margem.dir
  const h = altura - margem.topo - margem.baixo
  const maximo = Math.max(...serie.map((m) => Math.max(m.entrada_recebida + m.entrada_projetada, m.saida)), 1)
  const teto = Math.ceil((maximo * 1.12) / 10000) * 10000
  const y = (v) => h - (v / teto) * h
  const grupoW = w / serie.length
  const barraW = Math.min(24, grupoW * 0.3)
  const compacto = (v) => (v >= 1000 ? `${Math.round(v / 1000)}k` : `${v}`)

  return (
    <svg viewBox={`0 0 ${largura} ${altura}`} style={{ width: '100%', display: 'block' }} role="img"
      aria-label="Fluxo de caixa mensal: entradas recebidas e projetadas versus saídas">
      <g transform={`translate(${margem.esq},${margem.topo})`}>
        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <line x1={0} x2={w} y1={y(f * teto)} y2={y(f * teto)} stroke="var(--borda)" />
            <text x={-8} y={y(f * teto) + 4} textAnchor="end" fontSize="10" fill="var(--texto-3)" style={NUM}>
              {compacto(f * teto)}
            </text>
          </g>
        ))}
        {serie.map((m, i) => {
          const cx = i * grupoW + grupoW / 2
          const hRec = h - y(m.entrada_recebida)
          const hProj = h - y(m.entrada_projetada)
          return (
            <g key={m.mes}>
              {/* entrada empilhada: recebido (verde) embaixo + projetado (azul claro) em cima */}
              <rect x={cx - barraW - 2} y={y(m.entrada_recebida)} width={barraW} height={hRec} rx="2" fill="var(--verde)">
                <title>{`${fmtMes(m.mes)} — recebido: ${fmtBRL(m.entrada_recebida)}`}</title>
              </rect>
              <rect x={cx - barraW - 2} y={y(m.entrada_recebida + m.entrada_projetada)} width={barraW} height={hProj} rx="2" fill="var(--azul-fill-suave)">
                <title>{`${fmtMes(m.mes)} — projetado: ${fmtBRL(m.entrada_projetada)}`}</title>
              </rect>
              <rect x={cx + 2} y={y(m.saida)} width={barraW} height={h - y(m.saida)} rx="2" fill="var(--laranja)">
                <title>{`${fmtMes(m.mes)} — saídas: ${fmtBRL(m.saida)}`}</title>
              </rect>
              <text x={cx} y={h + 16} textAnchor="middle" fontSize="10" fill="var(--texto-2)" style={NUM}>
                {fmtMes(m.mes)}
              </text>
            </g>
          )
        })}
      </g>
    </svg>
  )
}

/* ---------------- rentabilidade ---------------- */

function Rentabilidade({ ranking }) {
  const top = ranking.slice(0, 5)
  const bottom = ranking.length > 5 ? ranking.slice(-5).reverse() : []
  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <h1>Rentabilidade por Projeto</h1>
          <div className="descricao">Margem realizada = receita apontada − custo das horas − despesas do projeto</div>
        </div>
        <BotaoExportar recurso="rentabilidade" />
      </div>

      <div className="grid-2-igual">
        <TabelaRanking titulo="Mais rentáveis" itens={top} />
        <TabelaRanking titulo="Menos rentáveis" itens={bottom.length ? bottom : [...ranking].reverse().slice(0, 5)} />
      </div>
    </>
  )
}

function TabelaRanking({ titulo, itens }) {
  return (
    <div className="card">
      <h2 className="card-titulo-secao">{titulo}</h2>
      <div className="card-corpo" style={{ paddingTop: 8 }}>
        <table className="tabela">
          <thead>
            <tr><th>Projeto</th><th className="num">Receita</th><th className="num">Custo+Desp.</th><th className="num">Margem</th></tr>
          </thead>
          <tbody>
            {itens.map((r) => (
              <tr key={r.projeto_id}>
                <td>
                  <Link className="link" to={`/projetos/${r.projeto_id}`}>{r.projeto}</Link>
                  <div className="texto-3" style={{ fontSize: 11.5 }}>{r.cliente}</div>
                </td>
                <td className="num">{fmtBRL(r.receita_realizada)}</td>
                <td className="num texto-2">{fmtBRL(r.custo_horas + r.despesas)}</td>
                <td className="num" style={{ color: r.margem >= 0 ? 'var(--verde)' : 'var(--vermelho)', fontWeight: 600 }}>
                  {fmtBRL(r.margem)} <span className="texto-3">({fmtPct(r.margem_pct)})</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ---------------- contas a pagar ---------------- */

function ContasAPagar({ dados, recarregar }) {
  const reembolsar = async (d) => {
    await api.patch(`/despesas/${d.id}/decidir`, { status: 'reembolsada' })
    recarregar()
  }
  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <h1>Contas a Pagar</h1>
          <div className="descricao">Reembolsos devidos aos consultores (despesas aprovadas aguardando pagamento)</div>
        </div>
      </div>

      <div className="grid-kpi" style={{ gridTemplateColumns: `repeat(${Math.min(1 + dados.por_consultor.length, 4)}, 1fr)` }}>
        <div className="card kpi">
          <div className="rotulo">Total a pagar</div>
          <div className="valor" style={{ color: dados.total > 0 ? 'var(--laranja)' : 'var(--texto)' }}>{fmtBRLExato(dados.total)}</div>
        </div>
        {dados.por_consultor.slice(0, 3).map((c) => (
          <div className="card kpi" key={c.consultor}>
            <div className="rotulo">{c.consultor}</div>
            <div className="valor">{fmtBRLExato(c.total)}</div>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="card-corpo" style={{ paddingTop: 10 }}>
          {dados.despesas.length === 0 ? (
            <div className="vazio-ensina">
              <Icone d={IC_RECEBER} size={28} strokeWidth={1.5} />
              <span className="titulo">Nenhum reembolso pendente</span>
              <span className="dica">Despesas aprovadas na fila de Aprovações aparecem aqui até serem reembolsadas.</span>
            </div>
          ) : (
            <table className="tabela">
              <thead>
                <tr><th>Consultor</th><th>Projeto</th><th>Data</th><th>Descrição</th><th className="num">Valor</th><th></th></tr>
              </thead>
              <tbody>
                {dados.despesas.map((d) => (
                  <tr key={d.id}>
                    <td>
                      <div className="linha-flex" style={{ gap: 8 }}>
                        <span className="avatar-consultor">{iniciais(d.consultor)}</span>
                        {d.consultor}
                      </div>
                    </td>
                    <td className="texto-2">{d.projeto}</td>
                    <td className="mono">{fmtData(d.data)}</td>
                    <td className="texto-2">{d.descricao || '—'}</td>
                    <td className="num" style={{ fontWeight: 600 }}>{fmtBRLExato(d.valor)}</td>
                    <td>
                      <button className="botao botao-primario botao-pequeno" onClick={() => reembolsar(d)}>
                        <Icone d={IC_RECEBER} size={12} /> Reembolsar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  )
}
