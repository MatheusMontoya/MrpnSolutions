import { fmtDataCurta } from '../format'

const dia = 24 * 60 * 60 * 1000
const parse = (iso) => new Date(`${iso}T00:00:00`)

/** Linha do tempo horizontal das 6 fases Activate, em faixa única:
 * cada fase é um segmento proporcional à duração real; a fase atual fica azul
 * sólido com brilho e o marcador HOJE é vermelho (sem hachura). Clique numa
 * fase abre a edição da data-fim (onSelecionarFase). */
export default function Gantt({ fases, onSelecionarFase }) {
  if (!fases || fases.length === 0) return null

  const inicio = parse(fases[0].data_inicio_prevista)
  const fim = parse(fases[fases.length - 1].data_fim_prevista)
  const total = Math.max((fim - inicio) / dia, 1)
  const pct = (d) => (((parse(d) - inicio) / dia) / total) * 100
  const larguraPct = (a, b) => (((parse(b) - parse(a)) / dia + 1) / total) * 100

  const hoje = new Date()
  hoje.setHours(0, 0, 0, 0)
  const hojeDentro = hoje >= inicio && hoje <= fim
  const hojePct = ((hoje - inicio) / dia / total) * 100

  return (
    <div style={{ overflowX: 'auto' }}>
      <div style={{ position: 'relative', minWidth: 760, height: 64, paddingTop: 6 }}>
        {fases.map((f) => {
          const esq = pct(f.data_inicio_prevista)
          const larg = larguraPct(f.data_inicio_prevista, f.data_fim_prevista)
          return (
            <button
              key={f.id}
              type="button"
              className="fase-seg-btn"
              onClick={() => onSelecionarFase(f)}
              title={`${f.nome}: ${fmtDataCurta(f.data_inicio_prevista)} – ${fmtDataCurta(f.data_fim_prevista)} (clique para mover a data-fim)`}
              style={{
                position: 'absolute', top: 0, left: `${esq}%`, width: `${larg}%`,
                padding: '0 3px', background: 'none', border: 'none', cursor: 'pointer', textAlign: 'center',
              }}
            >
              <div style={{
                fontSize: 10, fontWeight: f.atual ? 700 : 600, textTransform: 'uppercase', letterSpacing: '0.05em',
                color: f.atual ? 'var(--azul)' : 'var(--texto-3)',
                whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginBottom: 6,
              }}>
                {f.nome}
              </div>
              <div style={{
                height: 8, borderRadius: 99,
                ...(f.atual
                  ? { background: 'var(--azul)', boxShadow: '0 0 8px rgba(0, 112, 242, 0.4)' }
                  : { background: 'var(--superficie-variante)', border: '1px solid var(--borda)' }),
              }} />
            </button>
          )
        })}

        {hojeDentro && (
          <div style={{
            position: 'absolute', top: 18, bottom: 14, left: `${hojePct}%`,
            width: 2, background: 'var(--vermelho)', transform: 'translateX(-1px)', zIndex: 3,
          }}>
            <span style={{
              position: 'absolute', top: -4, left: '50%', transform: 'translateX(-50%)',
              width: 8, height: 8, borderRadius: '50%', background: 'var(--vermelho)',
            }} />
            <span style={{
              position: 'absolute', top: 22, left: '50%', transform: 'translateX(-50%)',
              fontSize: 10.5, fontWeight: 650,
              color: 'var(--vermelho)', background: 'var(--superficie)', padding: '0 3px', whiteSpace: 'nowrap',
            }}>
              Hoje
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
