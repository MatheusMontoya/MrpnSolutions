import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import Icone from '../components/Icone'
import Modal from '../components/Modal'
import { SkeletonPagina } from '../components/Skeleton'
import { SENIORIDADE, fmtBRLExato, fmtDataCurta, fmtPct } from '../format'

const classeUtilizacao = (u) => {
  if (u.status === 'ausente') return 'u-ausente'
  if (u.horas === 0) return 'u-vazia'
  if (u.status === 'superalocado') return 'u-super'
  if (u.status === 'ocioso') return 'u-ocioso'
  return 'u-ok'
}

/** Gráfico Demanda × Capacidade da empresa (SVG puro, barras agrupadas). */
function GraficoDemandaCapacidade({ serie }) {
  if (!serie || serie.length === 0) return null
  const largura = 1080
  const altura = 200
  const margem = { topo: 16, dir: 12, baixo: 26, esq: 44 }
  const w = largura - margem.esq - margem.dir
  const h = altura - margem.topo - margem.baixo
  const maximo = Math.max(...serie.map((s) => Math.max(s.demanda, s.capacidade)), 1)
  const teto = Math.ceil((maximo * 1.12) / 50) * 50
  const y = (v) => h - (v / teto) * h
  const grupoW = w / serie.length
  const barraW = Math.min(22, grupoW * 0.3)
  // eixos usam a própria fonte da interface com figuras tabulares
const NUM = { fontFamily: 'var(--fonte)', fontVariantNumeric: 'tabular-nums' }

  return (
    <svg viewBox={`0 0 ${largura} ${altura}`} style={{ width: '100%', display: 'block' }} role="img"
      aria-label="Demanda de horas alocadas versus capacidade da equipe, por semana">
      <g transform={`translate(${margem.esq},${margem.topo})`}>
        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <line x1={0} x2={w} y1={y(f * teto)} y2={y(f * teto)} stroke="var(--borda)" />
            <text x={-8} y={y(f * teto) + 4} textAnchor="end" fontSize="10" fill="var(--texto-3)" style={NUM}>
              {Math.round(f * teto)}h
            </text>
          </g>
        ))}
        {serie.map((s, i) => {
          const cx = i * grupoW + grupoW / 2
          return (
            <g key={s.semana}>
              {s.corrente && <rect x={i * grupoW} y={0} width={grupoW} height={h} fill="#f6f9fd" />}
              <rect x={cx - barraW - 2} y={y(s.capacidade)} width={barraW} height={h - y(s.capacidade)} rx="2" fill="var(--azul-fill-suave)">
                <title>{`Semana de ${fmtDataCurta(s.semana)} — capacidade: ${s.capacidade}h`}</title>
              </rect>
              <rect x={cx + 2} y={y(s.demanda)} width={barraW} height={h - y(s.demanda)} rx="2"
                fill={s.gargalo ? 'var(--vermelho)' : 'var(--azul)'}>
                <title>{`Semana de ${fmtDataCurta(s.semana)} — demanda: ${s.demanda}h${s.gargalo ? ' (acima da capacidade!)' : ''}`}</title>
              </rect>
              <text x={cx} y={h + 16} textAnchor="middle" fontSize="10" fill="var(--texto-2)" style={NUM}>
                {fmtDataCurta(s.semana)}
              </text>
            </g>
          )
        })}
      </g>
    </svg>
  )
}

// Legenda das faixas de utilização (mesma ordem/cores do heatmap).
const FAIXAS = [
  { rotulo: '> 100% superalocado', fundo: 'var(--vermelho-fundo)', cor: 'var(--vermelho)' },
  { rotulo: '60–100% saudável', fundo: 'var(--verde-fundo)', cor: 'var(--verde)' },
  { rotulo: '< 60% ocioso', fundo: 'var(--laranja-fundo)', cor: 'var(--laranja)' },
]

const ICONE_NOVO_CONSULTOR = [
  'M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2',
  'M8.5 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8',
  'M20 8v6',
  'M23 11h-6',
]

function LegendaFaixa({ rotulo, fundo, cor }) {
  return (
    <span
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        background: fundo, color: cor,
        padding: '3px 9px', borderRadius: 5,
        fontSize: 12, fontWeight: 600,
        whiteSpace: 'nowrap',
      }}
    >
      <span style={{ width: 7, height: 7, borderRadius: '50%', background: cor }} />
      {rotulo}
    </span>
  )
}

export default function Consultores() {
  const [dados, setDados] = useState(null)
  const [capacidade, setCapacidade] = useState(null)
  const [erro, setErro] = useState(null)
  const [modalNovo, setModalNovo] = useState(false)

  const carregar = () => {
    api.get('/consultores/utilizacao?semanas=12').then(setDados).catch((e) => setErro(e.message))
    api.get('/consultores/capacidade?semanas=12').then(setCapacidade).catch(() => {})
  }
  useEffect(carregar, [])

  if (erro) return <div className="mensagem-erro">{erro}</div>
  if (!dados) return <SkeletonPagina />

  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <h1>Consultores</h1>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 10 }}>
            {FAIXAS.map((f) => <LegendaFaixa key={f.rotulo} {...f} />)}
          </div>
        </div>
        <button className="botao botao-secundario" onClick={() => setModalNovo(true)}>
          <Icone d={ICONE_NOVO_CONSULTOR} size={16} />
          Novo consultor
        </button>
      </div>

      {capacidade && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-cabecalho">
            <h2 className="card-titulo-secao">Demanda × Capacidade da equipe</h2>
            <div className="grafico-legenda">
              <span className="item"><span className="quadrado" style={{ background: 'var(--azul-fill-suave)' }} /> Capacidade</span>
              <span className="item"><span className="quadrado" style={{ background: 'var(--azul)' }} /> Demanda</span>
              <span className="item"><span className="quadrado" style={{ background: 'var(--vermelho)' }} /> Gargalo</span>
            </div>
          </div>
          <div className="card-corpo">
            <GraficoDemandaCapacidade serie={capacidade.serie} />
            {capacidade.serie.some((s) => s.gargalo) && (
              <div className="texto-2" style={{ fontSize: 12.5, marginTop: 6 }}>
                ⚠ Semana(s) com demanda acima da capacidade — considere redistribuir alocações ou rever ausências.
              </div>
            )}
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-corpo" style={{ overflowX: 'auto', padding: 0 }}>
          <table className="heatmap" style={{ minWidth: 1060 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', paddingLeft: 16 }}>Consultor &amp; Nível</th>
                <th style={{ textAlign: 'right', paddingRight: 16 }}>Custo / Venda</th>
                {dados.semanas.map((s, i) => {
                  const corrente = dados.consultores[0]?.semanas[i]?.corrente
                  return (
                    <th key={s} className={corrente ? 'col-corrente' : ''}
                      title={`Semana de ${s}${corrente ? ' — semana corrente' : ''}`}>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                        <span style={{ fontSize: 9, letterSpacing: '0.12em', textTransform: 'uppercase', color: corrente ? 'var(--azul)' : 'var(--texto-3)' }}>
                          {corrente ? 'Atual' : 'Semana'}
                        </span>
                        <span className="mono" style={{ fontSize: 12, fontWeight: corrente ? 700 : 500, color: corrente ? 'var(--azul)' : 'var(--texto)' }}>
                          {fmtDataCurta(s)}
                        </span>
                      </div>
                    </th>
                  )
                })}
                <th style={{ textAlign: 'center' }}>Média</th>
              </tr>
            </thead>
            <tbody>
              {dados.consultores.map((c) => (
                <tr key={c.consultor_id}>
                  <td className="consultor-nome" style={{ paddingLeft: 16 }}>
                    <Link to={`/consultores/${c.consultor_id}`} className="link">{c.nome}</Link>
                    <div className="texto-3" style={{ fontSize: 11, fontWeight: 400, marginTop: 2 }}>
                      {SENIORIDADE[c.senioridade]}{c.modulo_sap ? ` · SAP ${c.modulo_sap}` : ''}
                    </div>
                  </td>
                  <td style={{ textAlign: 'right', paddingRight: 16, whiteSpace: 'nowrap' }} className="mono">
                    <div style={{ fontSize: 13, color: 'var(--texto)' }}>{fmtBRLExato(c.taxa_hora_custo)}</div>
                    <div style={{ fontSize: 11, color: 'var(--texto-3)', marginTop: 2 }}>{fmtBRLExato(c.taxa_hora_venda)}</div>
                  </td>
                  {c.semanas.map((s) => (
                    <td key={s.semana}>
                      <div
                        className={`celula ${classeUtilizacao(s)}${s.corrente ? ' semana-corrente' : ''}`}
                        title={s.status === 'ausente'
                          ? `Semana de ${s.semana}: ausência aprovada (capacidade ${s.capacidade ?? 0}h)`
                          : `Semana de ${s.semana}: ${s.horas}h alocadas (${fmtPct(s.utilizacao)} de ${s.capacidade ?? 40}h)${s.corrente ? ' — semana corrente' : ''}`}
                      >
                        {s.status === 'ausente' ? 'AUS' : s.horas > 0 ? fmtPct(s.utilizacao) : '·'}
                      </div>
                    </td>
                  ))}
                  <td className="mono" style={{ textAlign: 'center', paddingLeft: 8, paddingRight: 12, fontWeight: 600 }}>
                    {fmtPct(c.semanas.reduce((soma, s) => soma + s.utilizacao, 0) / c.semanas.length)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {modalNovo && (
        <FormNovoConsultor onFechar={() => setModalNovo(false)}
          onCriado={() => { setModalNovo(false); carregar() }} />
      )}
    </>
  )
}

function FormNovoConsultor({ onFechar, onCriado }) {
  const [form, setForm] = useState({ nome: '', senioridade: 'pleno', modulo_sap: 'FI/CO', skills: '', taxa_hora_custo: 80, taxa_hora_venda: 180 })
  const [erro, setErro] = useState(null)

  const salvar = async (e) => {
    e.preventDefault()
    try {
      await api.post('/consultores', {
        ...form,
        taxa_hora_custo: Number(form.taxa_hora_custo),
        taxa_hora_venda: Number(form.taxa_hora_venda),
      })
      onCriado()
    } catch (err) {
      setErro(err.message)
    }
  }

  return (
    <Modal titulo="Novo consultor" onFechar={onFechar}
      rodape={<>
        <button className="botao botao-fantasma" onClick={onFechar}>Cancelar</button>
        <button className="botao botao-primario" type="submit" form="form-consultor" disabled={!form.nome}>Salvar</button>
      </>}>
      <form id="form-consultor" onSubmit={salvar} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {erro && <div className="mensagem-erro">{erro}</div>}
        <div className="campo">
          <label htmlFor="ns-nome">Nome *</label>
          <input id="ns-nome" value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} autoFocus required />
        </div>
        <div className="form-linha">
          <div className="campo">
            <label htmlFor="ns-sen">Senioridade *</label>
            <select id="ns-sen" value={form.senioridade} onChange={(e) => setForm({ ...form, senioridade: e.target.value })}>
              <option value="junior">Júnior</option>
              <option value="pleno">Pleno</option>
              <option value="senior">Sênior</option>
            </select>
          </div>
          <div className="campo">
            <label htmlFor="ns-mod">Módulo SAP</label>
            <select id="ns-mod" value={form.modulo_sap} onChange={(e) => setForm({ ...form, modulo_sap: e.target.value })}>
              {['FI/CO', 'MM', 'SD', 'PP', 'ABAP', 'BASIS'].map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
        </div>
        <div className="form-linha">
          <div className="campo" style={{ flex: 1 }}>
            <label htmlFor="ns-skills">Competências (separadas por vírgula)</label>
            <input id="ns-skills" value={form.skills} placeholder="Ex.: S/4HANA Finance, Fiori, CDS Views"
              onChange={(e) => setForm({ ...form, skills: e.target.value })} />
          </div>
          <div className="campo">
            <label htmlFor="ns-custo">Taxa hora-custo (R$) *</label>
            <input id="ns-custo" type="number" min="0" step="0.01" value={form.taxa_hora_custo}
              onChange={(e) => setForm({ ...form, taxa_hora_custo: e.target.value })} required />
          </div>
          <div className="campo">
            <label htmlFor="ns-venda">Taxa hora-venda (R$) *</label>
            <input id="ns-venda" type="number" min="0" step="0.01" value={form.taxa_hora_venda}
              onChange={(e) => setForm({ ...form, taxa_hora_venda: e.target.value })} required />
          </div>
        </div>
      </form>
    </Modal>
  )
}
