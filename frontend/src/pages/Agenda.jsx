import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import Icone from '../components/Icone'
import { SkeletonPagina } from '../components/Skeleton'
import { fmtHoras } from '../format'
import { useSessao } from '../sessao'

const IC_ESQ = ['M15 18l-6-6 6-6']
const IC_DIR = ['M9 18l6-6-6-6']

const TIPOS_AUSENCIA = { ferias: 'Férias', folga: 'Folga', afastamento: 'Afastamento', treinamento: 'Treinamento' }
const DIAS_SEMANA = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']

const mesISO = (d) => d.toISOString().slice(0, 7)

/** Agenda mensal do consultor: alocações por dia (h), ausências aprovadas,
 * feriados do calendário corporativo e horas apontadas. O consultor vê a
 * própria; o gestor escolhe quem ver. */
export default function Agenda() {
  const { sessao } = useSessao()
  const ehConsultor = sessao?.perfil === 'consultor'
  const [consultores, setConsultores] = useState([])
  const [consultorId, setConsultorId] = useState(ehConsultor ? sessao.consultorId : null)
  const [mes, setMes] = useState(mesISO(new Date()))
  const [agenda, setAgenda] = useState(null)
  const [erro, setErro] = useState(null)

  useEffect(() => {
    if (ehConsultor) return
    api.get('/consultores').then((cs) => {
      setConsultores(cs)
      setConsultorId((atual) => atual ?? cs[0]?.id ?? null)
    }).catch((e) => setErro(e.message))
  }, [ehConsultor])

  const carregar = useCallback(() => {
    if (!consultorId) return
    api.get(`/consultores/${consultorId}/agenda?mes=${mes}`).then(setAgenda).catch((e) => setErro(e.message))
  }, [consultorId, mes])

  useEffect(carregar, [carregar])

  const mudarMes = (delta) => {
    const [ano, m] = mes.split('-').map(Number)
    const d = new Date(ano, m - 1 + delta, 1)
    setMes(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`)
  }

  const rotuloMes = () => {
    const [ano, m] = mes.split('-').map(Number)
    return new Date(ano, m - 1, 1).toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
  }

  if (erro) return <div className="mensagem-erro">{erro}</div>
  if (!agenda) return <SkeletonPagina />

  // preenche o vazio antes do dia 1 (calendário começa na segunda)
  const primeiroDiaSemana = agenda.dias[0]?.dia_semana ?? 0

  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <h1>Agenda</h1>
          <div className="descricao">
            Alocações, ausências e feriados por dia — {ehConsultor ? 'sua agenda do mês' : 'agenda mensal da equipe'}
          </div>
        </div>
        <div className="linha-flex" style={{ alignItems: 'center', gap: 10 }}>
          {!ehConsultor && (
            <div className="campo" style={{ minWidth: 200 }}>
              <select value={consultorId ?? ''} aria-label="Consultor"
                onChange={(e) => setConsultorId(Number(e.target.value))}>
                {consultores.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
              </select>
            </div>
          )}
          <div className="linha-flex" style={{ gap: 4 }}>
            <button className="botao botao-fantasma botao-pequeno" aria-label="Mês anterior" onClick={() => mudarMes(-1)}>
              <Icone d={IC_ESQ} size={15} />
            </button>
            <span style={{ minWidth: 150, textAlign: 'center', fontWeight: 600, textTransform: 'capitalize' }}>{rotuloMes()}</span>
            <button className="botao botao-fantasma botao-pequeno" aria-label="Próximo mês" onClick={() => mudarMes(1)}>
              <Icone d={IC_DIR} size={15} />
            </button>
          </div>
        </div>
      </div>

      <div className="grid-kpi" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <div className="card kpi">
          <div className="rotulo">Dias úteis</div>
          <div className="valor">{agenda.totais.dias_uteis}</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Horas alocadas</div>
          <div className="valor">{fmtHoras(agenda.totais.horas_alocadas)}</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Horas apontadas</div>
          <div className="valor">{fmtHoras(agenda.totais.horas_apontadas)}</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Dias ausente</div>
          <div className="valor" style={{ color: agenda.totais.dias_ausente ? 'var(--laranja)' : 'var(--texto)' }}>
            {agenda.totais.dias_ausente}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-corpo">
          <div className="agenda-grade">
            {DIAS_SEMANA.map((d) => <div key={d} className="agenda-cabecalho">{d}</div>)}
            {Array.from({ length: primeiroDiaSemana }, (_, i) => <div key={`v${i}`} className="agenda-dia vazio" />)}
            {agenda.dias.map((d) => {
              const numero = Number(d.data.slice(8))
              return (
                <div key={d.data} className={`agenda-dia${d.util ? '' : ' nao-util'}${d.hoje ? ' hoje' : ''}`}>
                  <div className="agenda-dia-topo">
                    <span className="numero mono">{numero}</span>
                    {d.horas_apontadas > 0 && (
                      <span className="badge badge-azul mono" style={{ fontSize: 10 }}>{fmtHoras(d.horas_apontadas)}</span>
                    )}
                  </div>
                  {d.feriado && <div className="agenda-item feriado" title={d.feriado}>🎉 {d.feriado}</div>}
                  {d.ausencia && <div className="agenda-item ausencia">{TIPOS_AUSENCIA[d.ausencia] || d.ausencia}</div>}
                  {!d.ausencia && d.alocacoes.map((a, i) => (
                    <div key={i} className="agenda-item alocacao" title={`${a.projeto} · ${a.fase}`}>
                      <span className="truncar">{a.projeto}</span>
                      <span className="mono" style={{ flexShrink: 0 }}>{a.horas_dia}h</span>
                    </div>
                  ))}
                </div>
              )
            })}
          </div>
          <div className="texto-3" style={{ fontSize: 12, marginTop: 10 }}>
            Horas por dia = horas/semana da alocação ÷ 5, nos dias úteis do período. Ausências aprovadas zeram o dia; feriados vêm das Configurações.
          </div>
        </div>
      </div>
    </>
  )
}
