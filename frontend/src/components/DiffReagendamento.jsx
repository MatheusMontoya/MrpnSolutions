import Icone from './Icone'
import { fmtBRLExato, fmtData, fmtDataCurta, fmtHoras } from '../format'

const IC_CRONO = ['M6 3v12', 'M18 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6z', 'M6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6z', 'M15 6a9 9 0 0 1-9 9']
const IC_ALOC = ['M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2', 'M9 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z', 'M19 8v6', 'M22 11h-6']
const IC_RECEITA = ['M12 1v22', 'M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6']

const MESES_LONGOS = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
const fmtMesLongo = (m) => {
  const [ano, mes] = m.split('-')
  return `${MESES_LONGOS[Number(mes) - 1]} ${ano}`
}

/** Título de seção com ícone (sentence-case, 15px). */
function Secao({ icone, titulo, children }) {
  return (
    <div>
      <h4 style={{
        display: 'flex', alignItems: 'center', gap: 8,
        fontSize: 15, fontWeight: 600, letterSpacing: '-0.01em', textTransform: 'none',
        color: 'var(--texto)', margin: '0 0 10px',
      }}>
        <span style={{ color: 'var(--texto-3)', lineHeight: 0 }}><Icone d={icone} size={18} /></span>
        {titulo}
      </h4>
      <div style={{ border: '1px solid var(--borda)', borderRadius: 'var(--raio-2)', overflow: 'hidden' }}>
        {children}
      </div>
    </div>
  )
}

/** Data antes → depois: mostra só o valor quando não muda; senão risca o antigo
 * e destaca o novo (azul quando é a fase realmente movida). */
const Datas = ({ antes, depois, azul }) =>
  antes === depois
    ? <span className="mono texto-2">{fmtData(antes)}</span>
    : (
      <>
        <span className="valor-antes mono">{fmtData(antes)}</span>
        <span className="diff-seta">→</span>
        <span className="mono" style={azul ? { color: 'var(--azul)', fontWeight: 600 } : { fontWeight: 600 }}>{fmtData(depois)}</span>
      </>
    )

const Periodo = ({ antes, depois }) => {
  const ra = `${fmtDataCurta(antes.data_inicio)}–${fmtDataCurta(antes.data_fim)}`
  const rd = `${fmtDataCurta(depois.data_inicio)}–${fmtDataCurta(depois.data_fim)}`
  return ra === rd
    ? <span className="mono texto-2" style={{ fontSize: 12.5 }}>{ra}</span>
    : (
      <span style={{ fontSize: 12.5, whiteSpace: 'nowrap' }}>
        <span className="valor-antes mono">{ra}</span>
        <span className="diff-seta">→</span>
        <span className="mono" style={{ fontWeight: 600 }}>{rd}</span>
      </span>
    )
}

/** Horas: total novo (antes → depois) + chip de variação (+/−/0h). */
const HorasCell = ({ antes, depois }) => {
  const d = Math.round((depois - antes) * 100) / 100
  const chipCls = d > 0 ? 'delta-chip delta-chip-pos' : d < 0 ? 'delta-chip delta-chip-neg' : 'delta-chip'
  const chipStyle = d === 0 ? { background: 'var(--superficie-variante)', color: 'var(--texto-3)' } : undefined
  return (
    <span style={{ whiteSpace: 'nowrap' }}>
      {antes === depois
        ? <span className="mono texto-2">{fmtHoras(antes)}</span>
        : (
          <>
            <span className="valor-antes mono">{fmtHoras(antes)}</span>
            <span className="diff-seta">→</span>
            <span className="mono" style={{ fontWeight: 600 }}>{fmtHoras(depois)}</span>
          </>
        )}
      <span className={chipCls} style={chipStyle}>{d > 0 ? '+' : ''}{fmtHoras(d)}</span>
    </span>
  )
}

const MoneyDiff = ({ antes, depois }) =>
  antes === depois
    ? <span className="mono texto-2">{fmtBRLExato(antes)}</span>
    : (
      <span style={{ whiteSpace: 'nowrap' }}>
        <span className="valor-antes mono">{fmtBRLExato(antes)}</span>
        <span className="diff-seta">→</span>
        <span className="mono" style={{ fontWeight: 600 }}>{fmtBRLExato(depois)}</span>
      </span>
    )

const DeltaChip = ({ v }) => {
  if (Math.abs(v) < 0.005) {
    return <span className="delta-chip" style={{ margin: 0, background: 'var(--superficie-variante)', color: 'var(--texto-3)' }}>—</span>
  }
  const cls = v > 0 ? 'delta-chip delta-chip-pos' : 'delta-chip delta-chip-neg'
  return <span className={cls} style={{ margin: 0 }}>{v > 0 ? '+' : ''}{fmtBRLExato(v)}</span>
}

/** Diff "antes → depois" produzido pelo motor de recálculo em cascata. */
export default function DiffReagendamento({ diff }) {
  const fasesAlteradas = diff.fases.filter((f) => f.alterada)
  const deltaTotal = diff.receita_total.depois - diff.receita_total.antes

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 26 }}>
      <Secao icone={IC_CRONO} titulo="Impacto no Cronograma (Fases Subsequentes)">
        {fasesAlteradas.length === 0
          ? <div className="vazio">Nenhuma fase alterada.</div>
          : (
            <table className="tabela">
              <thead>
                <tr>
                  <th style={{ width: '34%' }}>Fase</th>
                  <th>Início (antes → depois)</th>
                  <th>Fim (antes → depois)</th>
                </tr>
              </thead>
              <tbody>
                {fasesAlteradas.map((f) => {
                  const movida = f.nome === diff.fase_nome
                  return (
                    <tr key={f.id}>
                      <td>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                          <span style={{
                            width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                            ...(movida ? { background: 'var(--laranja)' } : { border: '1.5px solid var(--borda-forte)' }),
                          }} />
                          <strong style={{ fontWeight: 600 }}>{f.nome}</strong>
                        </span>
                      </td>
                      <td><Datas antes={f.antes.data_inicio_prevista} depois={f.depois.data_inicio_prevista} azul={movida} /></td>
                      <td><Datas antes={f.antes.data_fim_prevista} depois={f.depois.data_fim_prevista} azul={movida} /></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
      </Secao>

      <Secao icone={IC_ALOC} titulo="Alocações Deslocadas">
        {diff.alocacoes.length === 0
          ? <div className="vazio">Nenhuma alocação afetada.</div>
          : (
            <table className="tabela">
              <thead>
                <tr>
                  <th>Consultor</th>
                  <th>Fase</th>
                  <th>Período (antes → depois)</th>
                  <th className="num">Horas</th>
                  <th className="num">Receita (antes → depois)</th>
                </tr>
              </thead>
              <tbody>
                {diff.alocacoes.map((a) => (
                  <tr key={a.id}>
                    <td style={{ fontWeight: 500 }}>{a.consultor}</td>
                    <td className="texto-2">{a.fase}</td>
                    <td><Periodo antes={a.antes} depois={a.depois} /></td>
                    <td className="num"><HorasCell antes={a.antes.horas_previstas} depois={a.depois.horas_previstas} /></td>
                    <td className="num"><MoneyDiff antes={a.antes.receita_prevista} depois={a.depois.receita_prevista} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
      </Secao>

      <Secao icone={IC_RECEITA} titulo="Receita Mensal do Projeto">
        <table className="tabela">
          <thead>
            <tr>
              <th>Mês</th>
              <th className="num">Antes</th>
              <th className="num">Depois</th>
              <th className="num">Δ Variação</th>
            </tr>
          </thead>
          <tbody>
            {diff.receita_mensal.map((m) => (
              <tr key={m.mes}>
                <td className="texto-2">{fmtMesLongo(m.mes)}</td>
                <td className="num mono texto-2">{fmtBRLExato(m.antes)}</td>
                <td className="num mono">{fmtBRLExato(m.depois)}</td>
                <td className="num"><DeltaChip v={m.delta} /></td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--texto-2)' }}>Total do projeto</td>
              <td className="num mono texto-2">{fmtBRLExato(diff.receita_total.antes)}</td>
              <td className="num mono">{fmtBRLExato(diff.receita_total.depois)}</td>
              <td className="num">
                <span className={deltaTotal >= 0 ? 'delta-positivo' : 'delta-negativo'}>
                  {deltaTotal >= 0 ? '+ ' : '− '}{fmtBRLExato(Math.abs(deltaTotal))}
                </span>
              </td>
            </tr>
          </tfoot>
        </table>
      </Secao>
    </div>
  )
}
