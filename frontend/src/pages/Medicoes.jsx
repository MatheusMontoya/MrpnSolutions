import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import Icone from '../components/Icone'
import Modal from '../components/Modal'
import { SkeletonPagina } from '../components/Skeleton'
import { SENIORIDADE, corFase, fmtBRLExato, fmtData, fmtHoras, fmtMes } from '../format'

const IC_GERAR = ['M12 5v14', 'M5 12h14']
const IC_CHECK = ['M20 6 9 17l-5-5']
const IC_X = ['M18 6 6 18', 'M6 6l12 12']

const BADGE_STATUS = {
  gerada: ['badge-laranja', 'Aguardando aceite'],
  aceita: ['badge-verde', 'Aceita · faturada'],
  contestada: ['badge-vermelho', 'Contestada'],
}

/** Medição mensal: relatório de horas que o cliente aceita ANTES da fatura.
 * Aceite emite a fatura (substituindo a prevista do mês); contestação
 * devolve para correção dos apontamentos. */
export default function Medicoes() {
  const [dados, setDados] = useState(null)
  const [projetos, setProjetos] = useState([])
  const [erro, setErro] = useState(null)
  const [gerando, setGerando] = useState({ projeto_id: '', mes: '' })
  const [detalhe, setDetalhe] = useState(null) // medição aberta no modal
  const [contestando, setContestando] = useState(null)
  const [motivo, setMotivo] = useState('')

  const carregar = useCallback(() => {
    api.get('/medicoes').then(setDados).catch((e) => setErro(e.message))
    api.get('/projetos').then((d) => setProjetos(d.projetos ?? d)).catch(() => {})
  }, [])

  useEffect(carregar, [carregar])

  if (erro && !dados) return <div className="mensagem-erro">{erro}</div>
  if (!dados) return <SkeletonPagina />

  const gerar = async () => {
    setErro(null)
    try {
      const m = await api.post(`/projetos/${gerando.projeto_id}/medicoes`, {
        competencia: `${gerando.mes}-01`,
      })
      setGerando({ projeto_id: '', mes: '' })
      setDetalhe(m) // já abre o relatório gerado
      carregar()
    } catch (e) { setErro(e.message) }
  }

  const abrirDetalhe = async (m) => {
    try {
      setDetalhe(await api.get(`/medicoes/${m.id}`))
    } catch (e) { setErro(e.message) }
  }

  const aceitar = async (m) => {
    setErro(null)
    try {
      await api.post(`/medicoes/${m.id}/aceitar`, { numero: '' })
      setDetalhe(null)
      carregar()
    } catch (e) { setErro(e.message) }
  }

  const contestar = async () => {
    setErro(null)
    try {
      await api.post(`/medicoes/${contestando.id}/contestar`, { observacoes: motivo })
      setContestando(null)
      setMotivo('')
      setDetalhe(null)
      carregar()
    } catch (e) { setErro(e.message) }
  }

  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <h1>Medições</h1>
          <div className="descricao">Relatório de horas do mês para aceite do cliente — aceite emite a fatura; contestação devolve para correção</div>
        </div>
        <div className="linha-flex" style={{ alignItems: 'flex-end' }}>
          <div className="campo" style={{ minWidth: 220 }}>
            <select value={gerando.projeto_id} aria-label="Projeto da medição"
              onChange={(e) => setGerando({ ...gerando, projeto_id: e.target.value })}>
              <option value="">Projeto…</option>
              {projetos.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
            </select>
          </div>
          <div className="campo">
            <input type="month" value={gerando.mes} aria-label="Competência da medição"
              onChange={(e) => setGerando({ ...gerando, mes: e.target.value })} />
          </div>
          <button className="botao botao-primario" disabled={!gerando.projeto_id || !gerando.mes} onClick={gerar}>
            <Icone d={IC_GERAR} size={14} /> Gerar medição
          </button>
        </div>
      </div>

      {erro && <div className="mensagem-erro">{erro}</div>}

      <div className="grid-kpi" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
        <div className="card kpi">
          <div className="rotulo">Aguardando aceite</div>
          <div className="valor" style={{ color: dados.aguardando_aceite ? 'var(--laranja)' : 'var(--texto)' }}>{dados.aguardando_aceite}</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Aceitas (faturadas)</div>
          <div className="valor">{dados.medicoes.filter((m) => m.status === 'aceita').length}</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Total medido</div>
          <div className="valor">{fmtBRLExato(dados.medicoes.reduce((s, m) => s + (m.status !== 'contestada' ? m.total_valor : 0), 0))}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-corpo" style={{ paddingTop: 10 }}>
          {dados.medicoes.length === 0 ? (
            <div className="vazio-ensina">
              <Icone d={IC_CHECK} size={28} strokeWidth={1.5} />
              <span className="titulo">Nenhuma medição gerada</span>
              <span className="dica">Escolha o projeto e o mês acima — a medição consolida as horas apontadas × taxa para o cliente aceitar antes de faturar.</span>
            </div>
          ) : (
            <table className="tabela">
              <thead>
                <tr><th>Competência</th><th>Projeto</th><th>Cliente</th><th className="num">Horas</th><th className="num">Valor</th><th>Status</th><th /></tr>
              </thead>
              <tbody>
                {dados.medicoes.map((m) => {
                  const [cls, rot] = BADGE_STATUS[m.status] || BADGE_STATUS.gerada
                  return (
                    <tr key={m.id}>
                      <td className="mono">{fmtMes(m.competencia)}</td>
                      <td>{m.projeto}</td>
                      <td className="texto-2">{m.cliente}</td>
                      <td className="num">{fmtHoras(m.total_horas)}</td>
                      <td className="num" style={{ fontWeight: 600 }}>{fmtBRLExato(m.total_valor)}</td>
                      <td><span className={`badge ${cls}`}>{rot}</span></td>
                      <td className="num">
                        <div className="linha-flex" style={{ gap: 6, justifyContent: 'flex-end' }}>
                          <button className="botao botao-fantasma botao-pequeno" onClick={() => abrirDetalhe(m)}>Relatório</button>
                          {m.status === 'gerada' && (
                            <>
                              <button className="botao botao-secundario botao-pequeno" style={{ color: 'var(--vermelho)', borderColor: '#f2c7cb' }}
                                onClick={() => { setContestando(m); setMotivo('') }}>
                                <Icone d={IC_X} size={12} /> Contestar
                              </button>
                              <button className="botao botao-primario botao-pequeno" onClick={() => aceitar(m)}>
                                <Icone d={IC_CHECK} size={12} /> Aceite do cliente
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {detalhe && (
        <Modal extraLarga classeExtra="modal-imprimivel"
          titulo={`Medição ${fmtMes(detalhe.competencia)} — ${detalhe.projeto}`}
          onFechar={() => setDetalhe(null)}
          rodape={<>
            <button className="botao botao-fantasma" onClick={() => setDetalhe(null)}>Fechar</button>
            {detalhe.status === 'gerada' && (
              <>
                <button className="botao botao-secundario" style={{ color: 'var(--vermelho)', borderColor: '#f2c7cb' }}
                  onClick={() => { setContestando(detalhe); setMotivo('') }}>
                  Contestar
                </button>
                <button className="botao botao-primario" onClick={() => aceitar(detalhe)}>
                  Registrar aceite do cliente
                </button>
              </>
            )}
            <button className="botao botao-secundario" onClick={() => window.print()}>Imprimir / PDF</button>
          </>}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="linha-flex" style={{ gap: 10, flexWrap: 'wrap' }}>
              <span className="texto-2">{detalhe.cliente}</span>
              <span className={`badge ${(BADGE_STATUS[detalhe.status] || [])[0]}`}>{(BADGE_STATUS[detalhe.status] || [])[1]}</span>
              <span className="espacador" />
              <span className="texto-3" style={{ fontSize: 12 }}>gerada em {fmtData(detalhe.criada_em)}</span>
            </div>
            {detalhe.observacoes && (
              <div className="mensagem-erro" style={{ margin: 0 }}>Contestação: {detalhe.observacoes}</div>
            )}
            <table className="tabela">
              <thead>
                <tr><th>Consultor</th><th>Fase</th><th className="num">Taxa (R$/h)</th><th className="num">Horas</th><th className="num">Valor</th></tr>
              </thead>
              <tbody>
                {(detalhe.linhas || []).map((l, i) => (
                  <tr key={i}>
                    <td>{l.consultor} <span className="texto-3" style={{ fontSize: 12 }}>({SENIORIDADE[l.senioridade] || l.senioridade})</span></td>
                    <td><span className={`badge ${corFase(l.fase)}`}>{l.fase}</span></td>
                    <td className="num">{fmtBRLExato(l.taxa_hora)}</td>
                    <td className="num">{fmtHoras(l.horas)}</td>
                    <td className="num" style={{ fontWeight: 600 }}>{fmtBRLExato(l.valor)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={3} style={{ fontWeight: 700 }}>Total</td>
                  <td className="num" style={{ fontWeight: 700 }}>{fmtHoras(detalhe.total_horas)}</td>
                  <td className="num" style={{ fontWeight: 700 }}>{fmtBRLExato(detalhe.total_valor)}</td>
                </tr>
              </tfoot>
            </table>
            <div className="texto-3" style={{ fontSize: 12 }}>
              O aceite emite a fatura da competência (vencimento em 30 dias) e substitui a fatura prevista do plano, se houver.
            </div>
          </div>
        </Modal>
      )}

      {contestando && (
        <Modal titulo={`Contestar medição — ${contestando.projeto} · ${fmtMes(contestando.competencia)}`}
          onFechar={() => setContestando(null)}
          rodape={<>
            <button className="botao botao-fantasma" onClick={() => setContestando(null)}>Cancelar</button>
            <button className="botao botao-primario" disabled={!motivo.trim()} onClick={contestar}>
              Registrar contestação
            </button>
          </>}>
          <div className="campo">
            <label htmlFor="med-motivo">O que o cliente questionou? *</label>
            <textarea id="med-motivo" rows={4} value={motivo} autoFocus
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="Ex.: horas de 05/07 não reconhecidas; taxa do consultor X divergente do contrato…"
              style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit', fontSize: 14 }} />
            <span className="ajuda">Corrija os apontamentos e gere uma nova medição da mesma competência.</span>
          </div>
        </Modal>
      )}
    </>
  )
}
