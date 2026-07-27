import { useState } from 'react'
import { fmtBRL, fmtMes } from '../format'

const AZUL = 'var(--azul)'
const AZUL_SUAVE = 'var(--azul-fill-suave)' // barra "prevista"
// eixos usam a própria fonte da interface com figuras tabulares
const NUM = { fontFamily: 'var(--fonte)', fontVariantNumeric: 'tabular-nums' }

/** Gráfico de barras agrupadas (prevista vs realizada por mês) em SVG puro.
 * mesCorrente ("YYYY-MM") recebe um fundo sutil para ancorar a leitura.
 * mostrarLegenda=false quando a legenda é renderizada no cabeçalho do card. */
export default function GraficoBarras({ dados, altura = 260, mesCorrente, mostrarLegenda = true }) {
  const [hover, setHover] = useState(null)

  if (!dados || dados.length === 0) {
    return <div className="vazio">Sem dados de receita ainda.</div>
  }

  const largura = 1080
  const margem = { topo: 18, direita: 12, baixo: 30, esquerda: 66 }
  const w = largura - margem.esquerda - margem.direita
  const h = altura - margem.topo - margem.baixo

  const maximo = Math.max(...dados.map((d) => Math.max(d.prevista, d.realizada)), 1)
  // teto "redondo" com ~12% de folga p/ a barra mais alta não encostar no topo
  const passo = Math.pow(10, Math.floor(Math.log10(maximo)))
  const teto = Math.ceil((maximo * 1.12) / passo) * passo
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * teto)

  const grupoW = w / dados.length
  const barraW = Math.min(26, grupoW * 0.32)
  const y = (v) => h - (v / teto) * h

  const compacto = (v) =>
    v >= 1_000_000 ? `${(v / 1_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mi`
      : v >= 1000 ? `${Math.round(v / 1000)} mil` : `${v}`

  return (
    <div>
      {mostrarLegenda && (
        <div className="grafico-legenda no-topo">
          <span className="item"><span className="quadrado" style={{ background: AZUL_SUAVE }} /> Receita prevista</span>
          <span className="item"><span className="quadrado" style={{ background: AZUL }} /> Receita realizada</span>
        </div>
      )}
      <svg
        viewBox={`0 0 ${largura} ${altura}`}
        style={{ width: '100%', display: 'block' }}
        role="img"
        aria-label={`Receita prevista vs realizada por mês, de ${fmtMes(dados[0].mes)} a ${fmtMes(dados[dados.length - 1].mes)}`}
      >
        <g transform={`translate(${margem.esquerda},${margem.topo})`}>
          {ticks.map((t) => (
            <g key={t}>
              <line x1={0} x2={w} y1={y(t)} y2={y(t)} stroke="var(--borda)" strokeWidth="1" />
              <text x={-10} y={y(t) + 4} textAnchor="end" fontSize="10.5" fill="var(--texto-3)" style={NUM}>
                {compacto(t)}
              </text>
            </g>
          ))}
          {dados.map((d, i) => {
            const cx = i * grupoW + grupoW / 2
            const emHover = hover === i
            const corrente = d.mes === mesCorrente
            return (
              <g
                key={d.mes}
                onMouseEnter={() => setHover(i)}
                onMouseLeave={() => setHover(null)}
              >
                <rect x={i * grupoW} y={0} width={grupoW} height={h}
                  fill={emHover ? 'var(--superficie-variante)' : corrente ? 'var(--superficie-baixa)' : 'transparent'} />
                {corrente && (
                  <text x={cx} y={-6} textAnchor="middle" fontSize="10" fontWeight="700" fill="var(--azul)">
                    mês atual
                  </text>
                )}
                <rect x={cx - barraW - 2} y={y(d.prevista)} width={barraW} height={h - y(d.prevista)} rx="2" fill={AZUL_SUAVE}>
                  <title>{`${fmtMes(d.mes)} — prevista: ${fmtBRL(d.prevista)}`}</title>
                </rect>
                <rect x={cx + 2} y={y(d.realizada)} width={barraW} height={h - y(d.realizada)} rx="2" fill={AZUL}>
                  <title>{`${fmtMes(d.mes)} — realizada: ${fmtBRL(d.realizada)}`}</title>
                </rect>
                <text x={cx} y={h + 18} textAnchor="middle" fontSize="11" fill="var(--texto-2)" style={NUM}>
                  {fmtMes(d.mes)}
                </text>
              </g>
            )
          })}
          {hover !== null && (
            <g pointerEvents="none">
              <rect
                x={Math.min(hover * grupoW + grupoW / 2 - 85, w - 180)}
                y={4} width={180} height={54} rx="6"
                fill="var(--chrome)" opacity="0.96"
              />
              <text x={Math.min(hover * grupoW + grupoW / 2 - 75, w - 170)} y={24} fontSize="12" fontWeight="700" fill="#fff">
                {fmtMes(dados[hover].mes)}
              </text>
              <text x={Math.min(hover * grupoW + grupoW / 2 - 75, w - 170)} y={44} fontSize="11.5" fill="var(--azul-borda)">
                {`Prev ${fmtBRL(dados[hover].prevista)} · Real ${fmtBRL(dados[hover].realizada)}`}
              </text>
            </g>
          )}
        </g>
      </svg>
    </div>
  )
}
