import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import FalhaAoCarregar from '../components/FalhaAoCarregar'
import Icone from '../components/Icone'
import Modal from '../components/Modal'
import { SkeletonPagina } from '../components/Skeleton'
import { corFase, fmtBRLExato, fmtData, fmtHoras, iniciais } from '../format'
import { comAviso } from '../avisos'

const IC_CHECK = ['M20 6 9 17l-5-5']
const IC_X = ['M18 6 6 18', 'M6 6l12 12']
const IC_CHEVRON = ['M6 9l6 6 6-6']
const IC_RELOGIO = ['M12 8v4l3 3', 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z']
const IC_CAL = ['M5 4h14a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z', 'M16 2v4', 'M8 2v4', 'M3 10h18']
const IC_CARTAO = ['M2 5h20a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z', 'M1 10h22']
const IC_EQUIPE = ['M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2', 'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z', 'M23 21v-2a4 4 0 0 0-3-3.87', 'M16 3.13a4 4 0 0 1 0 7.75']
const IC_ALERTA = ['M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z', 'M12 9v4', 'M12 17h.01']

const TIPOS_AUSENCIA = { ferias: 'Férias', folga: 'Folga', afastamento: 'Afastamento', treinamento: 'Treinamento' }
const TIPOS_DESPESA = { deslocamento: 'Deslocamento', alimentacao: 'Alimentação', hospedagem: 'Hospedagem', quilometragem: 'Quilometragem', outros: 'Outros' }

export default function Aprovacoes() {
  const [fila, setFila] = useState(null)
  const [erro, setErro] = useState(null)
  const [expandido, setExpandido] = useState(null) // id do envio aberto
  const [reprovando, setReprovando] = useState(null) // envio em reprovação (modal)
  const [comentario, setComentario] = useState('')
  const [expandidoSol, setExpandidoSol] = useState(null) // solicitação com conflito aberto
  const [recusandoSol, setRecusandoSol] = useState(null) // solicitação em recusa (modal)

  const carregar = useCallback(() => {
    api.get('/aprovacoes').then(setFila).catch((e) => setErro(e.message))
  }, [])

  useEffect(carregar, [carregar])

  if (erro) return <FalhaAoCarregar erro={erro} aoTentarDeNovo={carregar} />
  if (!fila) return <SkeletonPagina />

  // A falha vai para o aviso, NUNCA para setErro: aqui a tela já tem a fila
  // carregada, e trocar tudo por uma página de erro faria o gestor perder a
  // lista inteira porque uma aprovação não passou.
  const decidirEnvio = (id, status, coment = '') => comAviso(
    async () => {
      await api.patch(`/aprovacoes/envios/${id}/decidir`, { status, comentario_gestor: coment })
      setReprovando(null)
      setComentario('')
      carregar()
    },
    { sucesso: status === 'aprovada' ? 'Horas aprovadas.' : 'Horas devolvidas para correção.' },
  )
  const decidirAusencia = (id, status) => comAviso(
    async () => { await api.patch(`/ausencias/${id}/decidir`, { status }); carregar() },
    { sucesso: status === 'aprovada' ? 'Ausência aprovada.' : 'Ausência recusada.' },
  )
  const decidirDespesa = (id, status) => comAviso(
    async () => { await api.patch(`/despesas/${id}/decidir`, { status }); carregar() },
    { sucesso: status === 'aprovada' ? 'Reembolso aprovado.' : 'Reembolso recusado.' },
  )
  const decidirSolicitacao = (id, status, coment = '') => comAviso(
    async () => {
      await api.patch(`/solicitacoes-alocacao/${id}/decidir`, { status, comentario_gestor: coment })
      setRecusandoSol(null)
      setComentario('')
      carregar()
    },
    { sucesso: status === 'aprovada' ? 'Solicitação aprovada.' : 'Solicitação recusada.' },
  )

  const vazio = fila.total_pendente === 0 && fila.reembolsos_pendentes.length === 0

  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <h1>Aprovações</h1>
          <div className="descricao">
            {fila.total_pendente > 0
              ? `${fila.total_pendente} ${fila.total_pendente === 1 ? 'item aguardando' : 'itens aguardando'} sua decisão`
              : 'Nada aguardando decisão'}
          </div>
        </div>
      </div>

      {vazio && (
        <div className="card">
          <div className="vazio-ensina">
            <Icone d={IC_CHECK} size={28} strokeWidth={1.5} />
            <span className="titulo">Tudo em dia!</span>
            <span className="dica">Semanas de horas, ausências e despesas enviadas pela equipe aparecem aqui para aprovar ou reprovar.</span>
          </div>
        </div>
      )}

      {/* ---- semanas de horas ---- */}
      {fila.envios.length > 0 && (
        <div className="secao">
          <div className="sub-secao"><Icone d={IC_RELOGIO} size={14} /> Semanas de horas <span className="contagem">({fila.envios.length})</span></div>
          {fila.envios.map((e) => (
            <div className="fila-item" key={e.id}>
              <div className="cabeca">
                <span className="avatar-consultor">{iniciais(e.consultor)}</span>
                <strong>{e.consultor}</strong>
                <span className="texto-2">semana de {fmtData(e.semana)}</span>
                <span className="badge badge-azul mono">{fmtHoras(e.total_horas)}</span>
                {e.enviado_em && <span className="texto-3" style={{ fontSize: 12 }}>enviada em {fmtData(e.enviado_em)}</span>}
                <div className="acoes">
                  <button className="botao botao-fantasma botao-pequeno" onClick={() => setExpandido(expandido === e.id ? null : e.id)}>
                    <Icone d={IC_CHEVRON} size={13} /> {expandido === e.id ? 'Ocultar' : 'Detalhar'}
                  </button>
                  <button className="botao botao-secundario botao-pequeno" style={{ color: 'var(--vermelho)', borderColor: '#f2c7cb' }}
                    onClick={() => { setReprovando(e); setComentario('') }}>
                    <Icone d={IC_X} size={13} /> Reprovar
                  </button>
                  <button className="botao botao-primario botao-pequeno" onClick={() => decidirEnvio(e.id, 'aprovada')}>
                    <Icone d={IC_CHECK} size={13} /> Aprovar
                  </button>
                </div>
              </div>
              {expandido === e.id && (
                <div className="fila-detalhe">
                  <table className="tabela">
                    <thead>
                      <tr><th>Dia</th><th>Projeto</th><th>Fase</th><th className="num">Horas</th><th>O que foi feito</th></tr>
                    </thead>
                    <tbody>
                      {e.lancamentos.map((l, i) => (
                        <tr key={i}>
                          <td className="mono">{fmtData(l.data)}</td>
                          <td>{l.projeto}</td>
                          <td><span className={`badge ${corFase(l.fase)}`}>{l.fase}</span></td>
                          <td className="num">{fmtHoras(l.horas)}</td>
                          <td className="texto-2">{l.descricao || <span className="texto-3">—</span>}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ---- solicitações de alocação ---- */}
      {fila.solicitacoes_alocacao?.length > 0 && (
        <div className="secao">
          <div className="sub-secao"><Icone d={IC_EQUIPE} size={14} /> Solicitações de alocação <span className="contagem">({fila.solicitacoes_alocacao.length})</span></div>
          {fila.solicitacoes_alocacao.map((s) => (
            <div className="fila-item" key={s.id}>
              <div className="cabeca">
                <span className="avatar-consultor">{iniciais(s.consultor)}</span>
                <strong>{s.consultor}</strong>
                <span className="texto-2">{s.projeto}</span>
                <span className={`badge ${corFase(s.fase)}`}>{s.fase}</span>
                <span className="mono texto-2">{fmtData(s.data_inicio)} – {fmtData(s.data_fim)}</span>
                <span className="badge badge-azul mono">{fmtHoras(s.horas_semana)}/sem</span>
                {s.conflitos?.conflito ? (
                  <span className="badge badge-vermelho" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    <Icone d={IC_ALERTA} size={11} /> Conflito
                  </span>
                ) : (
                  <span className="badge badge-verde">Sem conflito</span>
                )}
                <div className="acoes">
                  {(s.conflitos?.conflito || s.conflitos?.sobreposicoes?.length > 0) && (
                    <button className="botao botao-fantasma botao-pequeno" onClick={() => setExpandidoSol(expandidoSol === s.id ? null : s.id)}>
                      <Icone d={IC_CHEVRON} size={13} /> {expandidoSol === s.id ? 'Ocultar' : 'Detalhar'}
                    </button>
                  )}
                  <button className="botao botao-secundario botao-pequeno" style={{ color: 'var(--vermelho)', borderColor: '#f2c7cb' }}
                    onClick={() => { setRecusandoSol(s); setComentario('') }}>
                    <Icone d={IC_X} size={13} /> Recusar
                  </button>
                  <button className="botao botao-primario botao-pequeno" onClick={() => decidirSolicitacao(s.id, 'aprovada')}>
                    <Icone d={IC_CHECK} size={13} /> Aprovar e alocar
                  </button>
                </div>
              </div>
              {s.justificativa && (
                <div className="texto-3" style={{ fontSize: 12.5, padding: '0 14px 10px 52px' }}>
                  “{s.justificativa}” — {s.solicitante || 'sem solicitante'}
                </div>
              )}
              {expandidoSol === s.id && s.conflitos && (
                <div className="fila-detalhe">
                  {s.conflitos.semanas.length > 0 && (
                    <table className="tabela" style={{ marginBottom: s.conflitos.sobreposicoes.length ? 10 : 0 }}>
                      <thead>
                        <tr><th>Semana</th><th className="num">Já alocado</th><th className="num">Pedido</th><th className="num">Capacidade</th><th className="num">Excesso</th></tr>
                      </thead>
                      <tbody>
                        {s.conflitos.semanas.map((w) => (
                          <tr key={w.semana}>
                            <td className="mono">{fmtData(w.semana)}</td>
                            <td className="num">{fmtHoras(w.horas_existentes)}</td>
                            <td className="num">{fmtHoras(w.horas_pedido)}</td>
                            <td className="num">{fmtHoras(w.capacidade)}</td>
                            <td className="num" style={{ color: 'var(--vermelho)', fontWeight: 600 }}>+{fmtHoras(w.excesso)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                  {s.conflitos.ausencias.length > 0 && (
                    <div className="texto-2" style={{ fontSize: 12.5, marginBottom: 8 }}>
                      <strong style={{ color: 'var(--vermelho)' }}>Ausência aprovada no período:</strong>{' '}
                      {s.conflitos.ausencias.map((x) => `${TIPOS_AUSENCIA[x.tipo] || x.tipo} ${fmtData(x.data_inicio)}–${fmtData(x.data_fim)} (${x.dias_uteis} dia(s) útil(eis))`).join(' · ')}
                    </div>
                  )}
                  {s.conflitos.sobreposicoes.length > 0 && (
                    <div className="texto-3" style={{ fontSize: 12.5 }}>
                      Alocações no período: {s.conflitos.sobreposicoes.map((o) => `${o.projeto} · ${o.fase} (${o.horas_semana}h/sem)`).join(' · ')}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ---- ausências ---- */}
      {fila.ausencias.length > 0 && (
        <div className="secao">
          <div className="sub-secao"><Icone d={IC_CAL} size={14} /> Ausências <span className="contagem">({fila.ausencias.length})</span></div>
          {fila.ausencias.map((a) => (
            <div className="fila-item" key={a.id}>
              <div className="cabeca">
                <span className="avatar-consultor">{iniciais(a.consultor)}</span>
                <strong>{a.consultor}</strong>
                <span className="badge badge-cinza">{TIPOS_AUSENCIA[a.tipo] || a.tipo}</span>
                <span className="mono texto-2">{fmtData(a.data_inicio)} – {fmtData(a.data_fim)}</span>
                {a.motivo && <span className="texto-3" style={{ fontSize: 12.5 }}>“{a.motivo}”</span>}
                <div className="acoes">
                  <button className="botao botao-secundario botao-pequeno" style={{ color: 'var(--vermelho)', borderColor: '#f2c7cb' }}
                    onClick={() => decidirAusencia(a.id, 'recusada')}>
                    <Icone d={IC_X} size={13} /> Recusar
                  </button>
                  <button className="botao botao-primario botao-pequeno" onClick={() => decidirAusencia(a.id, 'aprovada')}>
                    <Icone d={IC_CHECK} size={13} /> Aprovar
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ---- despesas ---- */}
      {fila.despesas.length > 0 && (
        <div className="secao">
          <div className="sub-secao"><Icone d={IC_CARTAO} size={14} /> Despesas <span className="contagem">({fila.despesas.length})</span></div>
          {fila.despesas.map((d) => (
            <div className="fila-item" key={d.id}>
              <div className="cabeca">
                <span className="avatar-consultor">{iniciais(d.consultor)}</span>
                <strong>{d.consultor}</strong>
                <span className="texto-2">{d.projeto}</span>
                <span className="badge badge-cinza">{TIPOS_DESPESA[d.tipo] || d.tipo}{d.km ? ` · ${d.km} km` : ''}</span>
                <span className="mono" style={{ fontWeight: 600 }}>{fmtBRLExato(d.valor)}</span>
                {d.descricao && <span className="texto-3" style={{ fontSize: 12.5 }}>“{d.descricao}”</span>}
                <div className="acoes">
                  <button className="botao botao-secundario botao-pequeno" style={{ color: 'var(--vermelho)', borderColor: '#f2c7cb' }}
                    onClick={() => decidirDespesa(d.id, 'recusada')}>
                    <Icone d={IC_X} size={13} /> Recusar
                  </button>
                  <button className="botao botao-primario botao-pequeno" onClick={() => decidirDespesa(d.id, 'aprovada')}>
                    <Icone d={IC_CHECK} size={13} /> Aprovar
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ---- reembolsos (despesas já aprovadas) ---- */}
      {fila.reembolsos_pendentes.length > 0 && (
        <div className="secao">
          <div className="sub-secao"><Icone d={IC_CARTAO} size={14} /> Aguardando reembolso <span className="contagem">({fila.reembolsos_pendentes.length})</span></div>
          {fila.reembolsos_pendentes.map((d) => (
            <div className="fila-item" key={d.id}>
              <div className="cabeca">
                <span className="avatar-consultor">{iniciais(d.consultor)}</span>
                <strong>{d.consultor}</strong>
                <span className="texto-2">{d.projeto}</span>
                <span className="mono" style={{ fontWeight: 600 }}>{fmtBRLExato(d.valor)}</span>
                <div className="acoes">
                  <button className="botao botao-primario botao-pequeno" onClick={() => decidirDespesa(d.id, 'reembolsada')}>
                    <Icone d={IC_CHECK} size={13} /> Marcar reembolsada
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ---- modal de recusa de solicitação (comentário obrigatório) ---- */}
      {recusandoSol && (
        <Modal titulo={`Recusar solicitação — ${recusandoSol.consultor} em ${recusandoSol.projeto}`}
          onFechar={() => setRecusandoSol(null)}
          rodape={<>
            <button className="botao botao-fantasma" onClick={() => setRecusandoSol(null)}>Cancelar</button>
            <button className="botao botao-primario" disabled={!comentario.trim()}
              onClick={() => decidirSolicitacao(recusandoSol.id, 'recusada', comentario)}>
              Recusar solicitação
            </button>
          </>}>
          <div className="campo">
            <label htmlFor="rec-sol-coment">Motivo da recusa *</label>
            <textarea id="rec-sol-coment" rows={4} value={comentario} autoFocus
              onChange={(e) => setComentario(e.target.value)}
              placeholder="Ex.: consultor comprometido com o go-live do outro projeto nesse período…"
              style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit', fontSize: 14 }} />
            <span className="ajuda">O motivo fica registrado na solicitação para o solicitante.</span>
          </div>
        </Modal>
      )}

      {/* ---- modal de reprovação (comentário obrigatório) ---- */}
      {reprovando && (
        <Modal titulo={`Reprovar semana — ${reprovando.consultor} · ${fmtData(reprovando.semana)}`}
          onFechar={() => setReprovando(null)}
          rodape={<>
            <button className="botao botao-fantasma" onClick={() => setReprovando(null)}>Cancelar</button>
            <button className="botao botao-primario" disabled={!comentario.trim()}
              onClick={() => decidirEnvio(reprovando.id, 'reprovada', comentario)}>
              Reprovar e devolver
            </button>
          </>}>
          <div className="campo">
            <label htmlFor="rep-coment">O que precisa ser corrigido? *</label>
            <textarea id="rep-coment" rows={4} value={comentario} autoFocus
              onChange={(e) => setComentario(e.target.value)}
              placeholder="Ex.: faltou lançar a sexta-feira; descreva a atividade de quarta…"
              style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit', fontSize: 14 }} />
            <span className="ajuda">O comentário vai para o consultor, que corrige e reenvia a semana.</span>
          </div>
        </Modal>
      )}
    </>
  )
}
