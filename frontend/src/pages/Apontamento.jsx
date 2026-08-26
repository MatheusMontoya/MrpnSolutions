import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import FalhaAoCarregar from '../components/FalhaAoCarregar'
import BotaoExportar from '../components/BotaoExportar'
import Icone from '../components/Icone'
import Modal from '../components/Modal'
import { Bloco } from '../components/Skeleton'
import { corFase, fmtData, fmtDataCurta, fmtHoras, nomeDiaSemana } from '../format'
import { useSessao } from '../sessao'
import { avisar, confirmarE } from '../avisos'

const somaLinha = (linha) => Object.values(linha.horas_por_dia).reduce((s, h) => s + h, 0)

// exibição: 1 casa fixa, pt-BR ("47,9" / "40,0" / "0,0")
const fmtNum = (v) => (v ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

const CAL = ['M5 4h14a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z', 'M16 2v4', 'M8 2v4', 'M3 10h18']
const CHEVRON_ESQ = ['M15 18l-6-6 6-6']
const CHEVRON_DIR = ['M9 18l6-6-6-6']
const RAIO = ['M13 2L3 14h9l-1 8 10-12h-9l1-8z']
const BALAO = ['M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z']
const ENVIAR = ['M22 2 11 13', 'M22 2 15 22l-4-9-9-4 20-7z']
const CADEADO = ['M5 11h14a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2z', 'M7 11V7a5 5 0 0 1 10 0v4']

// status do envio da semana → badge + rótulo
const STATUS_ENVIO = {
  enviada: ['badge-azul', 'Enviada — aguardando aprovação'],
  aprovada: ['badge-verde', 'Semana aprovada'],
  reprovada: ['badge-vermelho', 'Reprovada — corrija e reenvie'],
}

const navBtnStyle = {
  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
  width: 32, height: 32, border: 'none', background: 'transparent',
  color: 'var(--texto-2)', cursor: 'pointer', borderRadius: 'var(--raio-1)',
}
const eyebrowStyle = {
  fontSize: 11.5, fontWeight: 600, color: 'var(--texto-2)',
}

export default function Apontamento() {
  const { sessao } = useSessao()
  const ehConsultor = sessao?.perfil === 'consultor'

  const [consultores, setConsultores] = useState([])
  // consultor logado fica travado no próprio id; gestor escolhe no seletor
  const [consultorId, setConsultorId] = useState(ehConsultor ? sessao.consultorId : null)
  const [semanaRef, setSemanaRef] = useState(null) // "YYYY-MM-DD" (qualquer dia da semana)
  const [grade, setGrade] = useState(null)
  const [erro, setErro] = useState(null)
  const [salvos, setSalvos] = useState({}) // "alocId|data" → true (feedback visual)
  const [balao, setBalao] = useState(null) // { alocacao_id, data, projeto, horas } | null
  const [textoBalao, setTextoBalao] = useState('')
  const [salvandoBalao, setSalvandoBalao] = useState(false)

  useEffect(() => {
    api.get('/consultores').then((cs) => {
      setConsultores(cs)
      // gestor cai no primeiro consultor; consultor já está travado no próprio id
      if (!ehConsultor && cs.length > 0) setConsultorId((atual) => atual ?? cs[0].id)
    }).catch((e) => setErro(e.message))
  }, [ehConsultor])

  const carregar = useCallback(() => {
    if (!consultorId) return
    const q = semanaRef ? `&inicio=${semanaRef}` : ''
    api.get(`/apontamentos/semana?consultor_id=${consultorId}${q}`)
      .then(setGrade)
      .catch((e) => setErro(e.message))
  }, [consultorId, semanaRef])

  useEffect(carregar, [carregar])

  const mudarSemana = (dias) => {
    // A semana de destino sai do estado LOCAL, não de `grade.semana`.
    // `grade` só muda quando a resposta do servidor chega: dois cliques rápidos
    // em "próxima" liam os dois a mesma semana antiga e avançavam uma só.
    setSemanaRef((atual) => {
      const base = new Date(`${atual ?? grade.semana}T00:00:00`)
      base.setDate(base.getDate() + dias)
      return base.toISOString().slice(0, 10)
    })
  }

  const lancar = async (alocacaoId, data, valor) => {
    const horas = valor === '' ? 0 : Number(valor)
    if (Number.isNaN(horas) || horas < 0 || horas > 24) return
    try {
      await api.post('/apontamentos', { alocacao_id: alocacaoId, data, horas })
      setSalvos((s) => ({ ...s, [`${alocacaoId}|${data}`]: true }))
      setTimeout(() => setSalvos((s) => ({ ...s, [`${alocacaoId}|${data}`]: false })), 1600)
      // atualiza o estado local sem recarregar tudo
      setGrade((g) => ({
        ...g,
        alocacoes: g.alocacoes.map((l) =>
          l.alocacao_id === alocacaoId
            ? { ...l, horas_por_dia: { ...l.horas_por_dia, [data]: horas } }
            : l,
        ),
      }))
    } catch (e) {
      // a grade inteira na tela não pode sumir porque UMA célula não salvou —
      // e a célula precisa voltar ao valor real, não ficar com o que foi digitado
      avisar.erro(e)
      carregar()
    }
  }

  /** Preenche os dias úteis vazios da semana com horas_semana/5 (o previsto). */
  const preencherPrevisto = async (linha) => {
    const horasDia = Math.round((linha.horas_semana / 5) * 10) / 10
    const lancamentos = grade.dias.filter((d, i) =>
      i < 5 && d >= linha.data_inicio && d <= linha.data_fim && !(linha.horas_por_dia[d] > 0),
    )
    for (const d of lancamentos) {
      await lancar(linha.alocacao_id, d, String(horasDia))
    }
  }

  const abrirBalao = (linha, data) => {
    setTextoBalao(linha.descricao_por_dia?.[data] || '')
    setBalao({ alocacao_id: linha.alocacao_id, data, projeto: linha.projeto, horas: linha.horas_por_dia[data] || 0 })
  }

  const salvarDescricao = async () => {
    if (!balao) return
    setSalvandoBalao(true)
    try {
      // envia as horas ATUAIS daquele dia + a descrição → preserva as horas, grava o texto
      await api.post('/apontamentos', { alocacao_id: balao.alocacao_id, data: balao.data, horas: balao.horas, descricao: textoBalao })
      setGrade((g) => ({
        ...g,
        alocacoes: g.alocacoes.map((l) =>
          l.alocacao_id === balao.alocacao_id
            ? { ...l, descricao_por_dia: { ...(l.descricao_por_dia || {}), [balao.data]: textoBalao } }
            : l,
        ),
      }))
      setBalao(null)
    } catch (e) {
      avisar.erro(e)
    } finally {
      setSalvandoBalao(false)
    }
  }

  const enviarSemana = () => confirmarE(
    'Enviar a semana para aprovação? As horas ficam travadas para edição até o gestor decidir.',
    async () => {
      await api.post('/apontamentos/semana/enviar', { consultor_id: consultorId, semana: grade.semana })
      carregar()
    },
    { sucesso: 'Semana enviada para aprovação.' },
  )

  if (erro) return <FalhaAoCarregar erro={erro} aoTentarDeNovo={carregar} />

  const totalSemana = grade ? grade.alocacoes.reduce((s, l) => s + somaLinha(l), 0) : 0
  const totalPorDia = grade
    ? grade.dias.map((d) => grade.alocacoes.reduce((s, l) => s + (l.horas_por_dia[d] || 0), 0))
    : []
  // semana enviada/aprovada não aceita mais edição (o backend também bloqueia)
  const bloqueada = !!grade?.envio && ['enviada', 'aprovada'].includes(grade.envio.status)
  const statusEnvio = grade?.envio ? STATUS_ENVIO[grade.envio.status] : null

  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <h1>Apontamento de horas</h1>
          <div className="descricao">Lançamento manual de horas realizadas por dia — salva ao sair do campo</div>
        </div>
        {!ehConsultor && <BotaoExportar recurso="apontamentos" />}
      </div>

      {/* ---- controles: consultor · navegação de semana · total ---- */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div
          className="card-corpo"
          style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 20, flexWrap: 'wrap' }}
        >
          <div className="campo" style={{ minWidth: 240 }}>
            <label htmlFor="ap-consultor" style={eyebrowStyle}>Consultor</label>
            {ehConsultor ? (
              <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--texto)', padding: '6px 0' }}>{sessao.nome}</div>
            ) : (
              <select id="ap-consultor" value={consultorId ?? ''} onChange={(e) => { setConsultorId(Number(e.target.value)); setSemanaRef(null) }}>
                {consultores.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
              </select>
            )}
          </div>

          {grade && (
            <div className="linha-flex" style={{ gap: 8 }}>
              <div
                style={{
                  display: 'flex', alignItems: 'center',
                  border: '1px solid var(--borda-forte)', borderRadius: 'var(--raio-1)',
                  background: 'var(--superficie)', padding: 2,
                }}
              >
                <button type="button" style={navBtnStyle} onClick={() => mudarSemana(-7)} aria-label="Semana anterior">
                  <Icone d={CHEVRON_ESQ} size={18} />
                </button>
                <div
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '0 12px', margin: '0 2px',
                    borderLeft: '1px solid var(--borda)', borderRight: '1px solid var(--borda)',
                  }}
                >
                  <span style={{ color: 'var(--texto-2)', display: 'inline-flex' }}><Icone d={CAL} size={15} /></span>
                  <strong className="mono" style={{ fontSize: 13.5, whiteSpace: 'nowrap' }}>Semana de {fmtData(grade.semana)}</strong>
                </div>
                <button type="button" style={navBtnStyle} onClick={() => mudarSemana(7)} aria-label="Próxima semana">
                  <Icone d={CHEVRON_DIR} size={18} />
                </button>
              </div>
              <button className="botao botao-fantasma botao-pequeno" onClick={() => setSemanaRef(null)}>Semana atual</button>
            </div>
          )}

          {grade && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 5 }}>
              <span style={eyebrowStyle}>Total da semana</span>
              <div
                style={{
                  display: 'inline-flex', alignItems: 'baseline', gap: 4,
                  background: 'var(--azul-claro)', border: '1px solid var(--azul-borda)',
                  borderRadius: 'var(--raio-1)', padding: '6px 14px', color: 'var(--azul-ativo)',
                }}
              >
                <span className="mono" style={{ fontSize: 20, fontWeight: 600, lineHeight: 1 }}>{fmtNum(totalSemana)}</span>
                <span className="mono" style={{ fontSize: 13, opacity: 0.7 }}>h</span>
              </div>
            </div>
          )}
        </div>

        {/* ---- situação da semana: status do envio + ação ---- */}
        {grade && (
          <div
            className="linha-flex"
            style={{ padding: '12px 20px', borderTop: '1px solid var(--borda)', gap: 12, flexWrap: 'wrap' }}
          >
            {statusEnvio
              ? <span className={`badge ${statusEnvio[0]}`}><Icone d={bloqueada ? CADEADO : BALAO} size={12} /> {statusEnvio[1]}</span>
              : <span className="badge badge-cinza">Rascunho — horas ainda não enviadas</span>}
            {grade.envio?.status === 'reprovada' && grade.envio.comentario_gestor && (
              <span className="texto-2" style={{ fontSize: 12.5 }}>
                Gestor: “{grade.envio.comentario_gestor}”
              </span>
            )}
            <span className="espacador" />
            {!bloqueada && (
              <button
                className="botao botao-primario botao-pequeno"
                onClick={enviarSemana}
                disabled={totalSemana <= 0}
                title={totalSemana <= 0 ? 'Lance horas antes de enviar' : 'Envia a semana para aprovação do gestor e bloqueia a edição'}
              >
                <Icone d={ENVIAR} size={13} />
                {grade.envio?.status === 'reprovada' ? 'Reenviar semana' : 'Enviar semana para aprovação'}
              </button>
            )}
          </div>
        )}
      </div>

      {/* ---- grade de apontamento ---- */}
      <div className="card">
        {!grade ? (
          <div className="card-corpo"><Bloco altura={180} /></div>
        ) : grade.alocacoes.length === 0 ? (
          <div className="card-corpo">
            <div className="vazio-ensina">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" />
              </svg>
              <span className="titulo">Nenhuma alocação ativa para {grade.consultor} nesta semana</span>
              <span className="dica">
                Horas são lançadas contra alocações. Aloque este consultor numa fase de projeto
                (tela Projetos → Alocar consultor) e a linha aparece aqui automaticamente.
              </span>
            </div>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="tabela grade-apontamento" style={{ minWidth: 860 }}>
              <thead>
                <tr style={{ background: 'var(--superficie-brilho)' }}>
                  <th style={{ width: '32%' }}>Alocação</th>
                  {grade.dias.map((d, i) => (
                    <th key={d} className={`num${i >= 5 ? ' fim-de-semana' : ''}`} style={{ minWidth: 72 }}>
                      {nomeDiaSemana(i)}<br />
                      <span className="texto-3" style={{ fontWeight: 400, fontSize: 10.5 }}>{fmtDataCurta(d)}</span>
                    </th>
                  ))}
                  <th className="num" style={{ background: 'var(--superficie-baixa)', borderLeft: '1px solid var(--borda)', color: 'var(--texto)' }}>Total</th>
                </tr>
              </thead>
              <tbody>
                {grade.alocacoes.map((linha) => (
                  <tr key={linha.alocacao_id}>
                    <td>
                      <strong style={{ fontWeight: 600 }}>{linha.projeto}</strong>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 5 }}>
                        <span className={`badge ${corFase(linha.fase)}`}>{linha.fase}</span>
                        <span className="texto-3 mono" style={{ fontSize: 11.5 }}>Previsto: {fmtHoras(linha.horas_semana)}/sem</span>
                        {!bloqueada && (
                          <button
                            className="botao botao-fantasma botao-pequeno"
                            style={{ padding: '2px 8px' }}
                            title={`Preenche os dias úteis vazios com ${fmtHoras(linha.horas_semana / 5)}/dia (o previsto da alocação)`}
                            onClick={() => preencherPrevisto(linha)}
                          >
                            <Icone d={RAIO} size={13} /> Preencher previsto
                          </button>
                        )}
                      </div>
                    </td>
                    {grade.dias.map((d, i) => {
                      const foraDoPeriodo = d < linha.data_inicio || d > linha.data_fim
                      const fimDeSemana = i >= 5
                      const horasDia = linha.horas_por_dia[d] || 0
                      const temDescricao = !!(linha.descricao_por_dia?.[d] || '').trim()
                      return (
                        <td key={d} className={`num${fimDeSemana ? ' fim-de-semana' : ''}`}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 4 }}>
                            <input
                              type="number" min="0" max="24" step="0.5"
                              aria-label={`Horas de ${linha.projeto} / ${linha.fase} em ${fmtData(d)}`}
                              defaultValue={linha.horas_por_dia[d] || ''}
                              key={`${linha.alocacao_id}|${d}|${linha.horas_por_dia[d]}`}
                              disabled={foraDoPeriodo || bloqueada}
                              title={foraDoPeriodo ? 'Fora do período da alocação' : bloqueada ? 'Semana enviada — edição bloqueada' : undefined}
                              className={salvos[`${linha.alocacao_id}|${d}`] ? 'salvo' : ''}
                              onBlur={(e) => {
                                const atual = linha.horas_por_dia[d] || 0
                                const novo = e.target.value === '' ? 0 : Number(e.target.value)
                                if (novo !== atual) lancar(linha.alocacao_id, d, e.target.value)
                              }}
                            />
                            {horasDia > 0 && (
                              <button
                                type="button"
                                onClick={() => abrirBalao(linha, d)}
                                aria-label={`${temDescricao ? 'Editar' : 'Adicionar'} descrição de ${fmtData(d)}`}
                                title={temDescricao ? (linha.descricao_por_dia?.[d] || '') : 'O que foi feito neste dia?'}
                                style={{
                                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                                  width: 22, height: 22, flexShrink: 0, cursor: 'pointer',
                                  borderRadius: 'var(--raio-1)', padding: 0,
                                  border: `1px solid ${temDescricao ? 'var(--azul-borda)' : 'var(--borda-forte)'}`,
                                  background: temDescricao ? 'var(--azul)' : 'transparent',
                                  color: temDescricao ? '#fff' : 'var(--texto-3)',
                                }}
                              >
                                <Icone d={BALAO} size={13} />
                              </button>
                            )}
                          </div>
                        </td>
                      )
                    })}
                    <td className="num mono" style={{ background: 'var(--superficie-baixa)', borderLeft: '1px solid var(--borda)' }}>
                      <strong>{fmtNum(somaLinha(linha))}</strong>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td style={{ textAlign: 'right', fontSize: 12.5, fontWeight: 600, color: 'var(--texto-2)' }}>Total do dia</td>
                  {totalPorDia.map((t, i) => (
                    <td key={grade.dias[i]} className={`num mono${i >= 5 ? ' fim-de-semana' : ''}`}>
                      <span style={t > 8 ? { color: 'var(--vermelho)' } : t === 0 ? { color: 'var(--texto-3)' } : undefined}>
                        {fmtNum(t)}
                      </span>
                    </td>
                  ))}
                  <td className="num mono" style={{ background: 'var(--azul-claro)', borderLeft: '1px solid var(--borda)', color: 'var(--azul-ativo)', fontSize: 15 }}>
                    <strong>{fmtNum(totalSemana)}</strong>
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>

      {balao && (
        <Modal
          titulo={`O que foi feito — ${balao.projeto} · ${fmtData(balao.data)}`}
          icone={BALAO}
          onFechar={() => setBalao(null)}
          rodape={
            bloqueada ? (
              <button className="botao botao-secundario" onClick={() => setBalao(null)}>Fechar</button>
            ) : (
              <>
                <button className="botao botao-secundario" onClick={() => setBalao(null)} disabled={salvandoBalao}>Cancelar</button>
                <button className="botao botao-primario" onClick={salvarDescricao} disabled={salvandoBalao}>
                  {salvandoBalao ? 'Salvando…' : 'Salvar'}
                </button>
              </>
            )
          }
        >
          <div className="campo">
            <label htmlFor="balao-descricao" style={eyebrowStyle}>Descrição do dia ({fmtHoras(balao.horas)})</label>
            <textarea
              id="balao-descricao"
              value={textoBalao}
              onChange={(e) => setTextoBalao(e.target.value)}
              rows={5}
              autoFocus
              disabled={bloqueada}
              placeholder="Descreva as atividades realizadas nessas horas…"
              style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit', fontSize: 14 }}
            />
          </div>
        </Modal>
      )}
    </>
  )
}
