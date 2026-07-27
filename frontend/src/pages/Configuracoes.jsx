import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import Icone from '../components/Icone'
import Modal from '../components/Modal'
import { SkeletonPagina } from '../components/Skeleton'
import { corFase, fmtBRLExato } from '../format'
import { useTema } from '../tema'

const ICONES = {
  voltar: ['M19 12H5', 'M12 19l-7-7 7-7'],
  perfil: ['M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2', 'M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8'],
  faturamento: ['M2 5h20a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z', 'M1 10h22'],
  taxas: ['M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z', 'M7 7h.01'],
  preferencias: [
    'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
    'M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z',
  ],
  upload: [
    'M16 16l-4-4-4 4', 'M12 12v9',
    'M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3',
  ],
  check: ['M20 6L9 17l-5-5'],
  ia: ['M12 8V4H8', 'M4 8h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2z', 'M2 14h2', 'M20 14h2', 'M15 13v2', 'M9 13v2'],
  olho: ['M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z', 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z'],
}

const SECOES = [
  { id: 'perfil', rotulo: 'Perfil', icone: ICONES.perfil },
  { id: 'faturamento', rotulo: 'Faturamento', icone: ICONES.faturamento },
  { id: 'taxas', rotulo: 'Taxas', icone: ICONES.taxas },
  { id: 'aparencia', rotulo: 'Aparência', icone: ICONES.preferencias },
  { id: 'preferencias', rotulo: 'Preferências', icone: ICONES.preferencias },
  { id: 'feriados', rotulo: 'Feriados', icone: ICONES.preferencias },
  { id: 'modelos', rotulo: 'Modelos de projeto', icone: ICONES.faturamento },
  { id: 'copiloto', rotulo: 'Copiloto IA', icone: ICONES.ia },
  { id: 'usuarios', rotulo: 'Usuários', icone: ICONES.perfil },
  { id: 'auditoria', rotulo: 'Auditoria', icone: ICONES.preferencias },
]

const OPCOES_MODELO_IA = [
  { valor: 'claude-sonnet-5', rotulo: 'Claude Sonnet 5 (recomendado)' },
  { valor: 'claude-opus-4-8', rotulo: 'Claude Opus 4.8 (mais capaz)' },
  { valor: 'claude-haiku-4-5-20251001', rotulo: 'Claude Haiku 4.5 (mais rápido)' },
]

const OPCOES_FORMATO_DATA = [
  { valor: 'DD/MM/AAAA', rotulo: 'DD/MM/AAAA (pt-BR)' },
  { valor: 'MM/DD/AAAA', rotulo: 'MM/DD/AAAA (en-US)' },
  { valor: 'AAAA-MM-DD', rotulo: 'AAAA-MM-DD (ISO)' },
]
const OPCOES_MOEDA = [
  { valor: 'BRL', rotulo: 'Real (R$)' },
  { valor: 'USD', rotulo: 'Dólar (US$)' },
  { valor: 'EUR', rotulo: 'Euro (€)' },
]
const OPCOES_FUSO = [
  { valor: 'America/Sao_Paulo', rotulo: '(GMT-03:00) Brasília' },
  { valor: 'America/Manaus', rotulo: '(GMT-04:00) Manaus' },
  { valor: 'America/Noronha', rotulo: '(GMT-02:00) Fernando de Noronha' },
  { valor: 'UTC', rotulo: '(GMT+00:00) UTC' },
]

const TAXAS = [
  { chave: 'taxa_junior', rotulo: 'Júnior' },
  { chave: 'taxa_pleno', rotulo: 'Pleno' },
  { chave: 'taxa_senior', rotulo: 'Sênior' },
]

// Feedback verde efêmero exibido ao lado do botão "Salvar" de cada seção.
function Feedback({ estado }) {
  if (!estado) return null
  const ok = estado.tipo === 'ok'
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      fontSize: 12.5, fontWeight: 600,
      color: ok ? 'var(--verde)' : 'var(--vermelho)',
    }}>
      {ok && <Icone d={ICONES.check} size={14} strokeWidth={2.5} />}
      {estado.msg}
    </span>
  )
}

function CabecalhoSecao({ titulo, descricao, botao, secaoId, salvando, feedback, onSalvar }) {
  return (
    <div className="card-cabecalho">
      <div>
        <h2 className="card-titulo-secao">{titulo}</h2>
        <p className="texto-2" style={{ margin: '3px 0 0', fontSize: 13 }}>{descricao}</p>
      </div>
      <div className="linha-flex" style={{ gap: 12 }}>
        <Feedback estado={feedback} />
        <button
          className={`botao ${secaoId === 'perfil' ? 'botao-primario' : 'botao-secundario'}`}
          onClick={onSalvar}
          disabled={salvando}
        >
          {salvando ? 'Salvando…' : botao}
        </button>
      </div>
    </div>
  )
}

export default function Configuracoes() {
  const navigate = useNavigate()
  const [salvo, setSalvo] = useState(null) // baseline persistido
  const [form, setForm] = useState(null) // edição corrente
  const [erro, setErro] = useState(null)
  const [ativo, setAtivo] = useState('perfil')
  const [salvando, setSalvando] = useState(null) // id da seção em salvamento
  const [feedback, setFeedback] = useState({}) // { secaoId: {tipo, msg} }

  const refs = {
    perfil: useRef(null),
    faturamento: useRef(null),
    taxas: useRef(null),
    aparencia: useRef(null),
    preferencias: useRef(null),
    feriados: useRef(null),
    modelos: useRef(null),
    copiloto: useRef(null),
    usuarios: useRef(null),
    auditoria: useRef(null),
  }

  useEffect(() => {
    api.get('/configuracoes')
      .then((d) => { setSalvo(d); setForm(d) })
      .catch((e) => setErro(e.message))
  }, [])

  // Marca ativo na sub-nav conforme a seção visível durante o scroll.
  useEffect(() => {
    if (!form) return
    const obs = new IntersectionObserver(
      (entradas) => {
        const visivel = entradas
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0]
        if (visivel) setAtivo(visivel.target.dataset.secao)
      },
      { rootMargin: '-96px 0px -55% 0px', threshold: 0 },
    )
    Object.values(refs).forEach((r) => r.current && obs.observe(r.current))
    return () => obs.disconnect()
  }, [form])

  const irPara = (id) => {
    setAtivo(id)
    refs[id].current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const setCampo = (chave, valor) => setForm((f) => ({ ...f, [chave]: valor }))

  const salvarSecao = async (secaoId, chaves) => {
    const alterados = {}
    for (const c of chaves) {
      if (form[c] !== salvo[c]) alterados[c] = form[c]
    }
    if (Object.keys(alterados).length === 0) {
      mostrarFeedback(secaoId, 'ok', 'Sem alterações')
      return
    }
    setSalvando(secaoId)
    try {
      await api.patch('/configuracoes', alterados)
      setSalvo((s) => ({ ...s, ...alterados }))
      mostrarFeedback(secaoId, 'ok', 'Salvo')
    } catch (e) {
      mostrarFeedback(secaoId, 'erro', e.message)
    } finally {
      setSalvando(null)
    }
  }

  const mostrarFeedback = (secaoId, tipo, msg) => {
    setFeedback((f) => ({ ...f, [secaoId]: { tipo, msg } }))
    setTimeout(() => {
      setFeedback((f) => {
        const prox = { ...f }
        delete prox[secaoId]
        return prox
      })
    }, 3200)
  }

  if (erro) return <div className="mensagem-erro">{erro}</div>
  if (!form) return <SkeletonPagina />

  const pct = (v) => Math.round((v ?? 0) * 100)
  const setPct = (chave, valorTexto) => setCampo(chave, Number(valorTexto) / 100)

  return (
    <>
      <div className="pagina-cabecalho">
        <div className="linha-flex" style={{ gap: 14 }}>
          <button className="botao botao-fantasma botao-pequeno" onClick={() => navigate(-1)}>
            <Icone d={ICONES.voltar} size={16} />
            Voltar
          </button>
          <h1>Configurações</h1>
        </div>
      </div>

      <div className="config-layout">
        <nav className="config-subnav" aria-label="Seções de configuração">
          {SECOES.map((s) => (
            <button
              key={s.id}
              className={ativo === s.id ? 'ativo' : ''}
              onClick={() => irPara(s.id)}
            >
              <Icone d={s.icone} size={17} />
              {s.rotulo}
            </button>
          ))}
        </nav>

        <div className="config-secoes">
          {/* ============ Perfil da Empresa ============ */}
          <section className="card" ref={refs.perfil} data-secao="perfil">
            <CabecalhoSecao
              titulo="Perfil da Empresa"
              descricao="Gerencie a identidade visual e dados cadastrais da consultoria."
              botao="Salvar Perfil"
              secaoId="perfil"
              salvando={salvando === 'perfil'}
              feedback={feedback.perfil}
              onSalvar={() => salvarSecao('perfil', ['nome_consultoria', 'cnpj'])}
            />
            <div className="card-corpo">
              <div className="grid-2-igual" style={{ alignItems: 'start' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  <div className="campo">
                    <label htmlFor="cfg-nome">Nome da consultoria</label>
                    <input
                      id="cfg-nome"
                      value={form.nome_consultoria ?? ''}
                      onChange={(e) => setCampo('nome_consultoria', e.target.value)}
                    />
                  </div>
                  <div className="campo">
                    <label htmlFor="cfg-cnpj">CNPJ</label>
                    <input
                      id="cfg-cnpj"
                      className="mono"
                      value={form.cnpj ?? ''}
                      onChange={(e) => setCampo('cnpj', e.target.value)}
                    />
                  </div>
                </div>
                <div className="campo">
                  <label>Logo da empresa</label>
                  <div className="dropzone">
                    <Icone d={ICONES.upload} size={30} strokeWidth={1.75} />
                    <div style={{ color: 'var(--texto-2)', fontSize: 13.5 }}>
                      Arraste uma imagem ou clique para selecionar
                    </div>
                    <div className="texto-3" style={{ fontSize: 12 }}>
                      PNG, JPG até 2MB. Recomendado 400x400px.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* ============ Parâmetros de Faturamento ============ */}
          <section className="card" ref={refs.faturamento} data-secao="faturamento">
            <CabecalhoSecao
              titulo="Parâmetros de Faturamento"
              descricao="Configure as jornadas padrão e limiares de alerta de alocação."
              botao="Salvar Parâmetros"
              secaoId="faturamento"
              salvando={salvando === 'faturamento'}
              feedback={feedback.faturamento}
              onSalvar={() => salvarSecao('faturamento', ['jornada_semanal', 'limiar_super', 'limiar_ocioso'])}
            />
            <div className="card-corpo">
              <div className="grid-2-igual" style={{ alignItems: 'stretch' }}>
                <div className="caixa-parametro">
                  <div className="rotulo">Jornada padrão</div>
                  <div className="campo">
                    <label htmlFor="cfg-jornada">Horas semanais base</label>
                    <div className="input-sufixo">
                      <input
                        id="cfg-jornada"
                        className="mono"
                        type="number"
                        min="0"
                        step="1"
                        value={form.jornada_semanal ?? ''}
                        onChange={(e) => setCampo('jornada_semanal', Number(e.target.value))}
                      />
                      <span className="sufixo">h/sem</span>
                    </div>
                    <span className="ajuda">Utilizado como base 100% de alocação.</span>
                  </div>
                </div>

                <div className="caixa-parametro">
                  <div className="rotulo">Limiares de utilização</div>
                  <div className="form-linha" style={{ alignItems: 'flex-start' }}>
                    <div className="campo" style={{ flex: 1 }}>
                      <label htmlFor="cfg-super" style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--vermelho)' }} />
                        <span style={{ color: 'var(--vermelho)' }}>Superalocado</span>
                      </label>
                      <div className="campo-afixo">
                        <span className="afixo" style={{ position: 'absolute', left: 12, color: 'var(--texto-3)', fontSize: 13 }}>&gt;</span>
                        <input
                          id="cfg-super"
                          className="mono"
                          type="number"
                          min="0"
                          value={pct(form.limiar_super)}
                          onChange={(e) => setPct('limiar_super', e.target.value)}
                        />
                        <span className="afixo afixo-dir" style={{ position: 'absolute', right: 12, color: 'var(--texto-3)', fontSize: 13 }}>%</span>
                      </div>
                    </div>
                    <div className="campo" style={{ flex: 1 }}>
                      <label htmlFor="cfg-ocioso" style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--laranja)' }} />
                        <span style={{ color: 'var(--laranja)' }}>Ocioso</span>
                      </label>
                      <div className="campo-afixo">
                        <span className="afixo" style={{ position: 'absolute', left: 12, color: 'var(--texto-3)', fontSize: 13 }}>&lt;</span>
                        <input
                          id="cfg-ocioso"
                          className="mono"
                          type="number"
                          min="0"
                          value={pct(form.limiar_ocioso)}
                          onChange={(e) => setPct('limiar_ocioso', e.target.value)}
                        />
                        <span className="afixo afixo-dir" style={{ position: 'absolute', right: 12, color: 'var(--texto-3)', fontSize: 13 }}>%</span>
                      </div>
                    </div>
                  </div>
                  <div className="barra" style={{ marginTop: 14, display: 'flex', height: 6, borderRadius: 99, overflow: 'hidden' }}>
                    <span style={{ flex: pct(form.limiar_ocioso), background: 'var(--laranja)' }} />
                    <span style={{ flex: Math.max(pct(form.limiar_super) - pct(form.limiar_ocioso), 1), background: 'var(--verde)' }} />
                    <span style={{ flex: 12, background: 'var(--vermelho)' }} />
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* ============ Taxas Padrão por Senioridade ============ */}
          <section className="card" ref={refs.taxas} data-secao="taxas">
            <CabecalhoSecao
              titulo="Taxas Padrão por Senioridade"
              descricao="Valores base para novos projetos. Podem ser sobrescritos por projeto."
              botao="Salvar Taxas"
              secaoId="taxas"
              salvando={salvando === 'taxas'}
              feedback={feedback.taxas}
              onSalvar={() => salvarSecao('taxas', ['taxa_junior', 'taxa_pleno', 'taxa_senior'])}
            />
            <div className="card-corpo" style={{ paddingLeft: 0, paddingRight: 0 }}>
              <table className="tabela">
                <thead>
                  <tr>
                    <th style={{ paddingLeft: 20 }}>Senioridade</th>
                    <th style={{ textAlign: 'center' }}>Taxa hora (R$)</th>
                    <th className="num" style={{ paddingRight: 20 }}>Taxa diária estimada (8h)</th>
                  </tr>
                </thead>
                <tbody>
                  {TAXAS.map((t) => (
                    <tr key={t.chave}>
                      <td style={{ paddingLeft: 20 }}>{t.rotulo}</td>
                      <td style={{ textAlign: 'center' }}>
                        <input
                          className="mono"
                          type="number"
                          min="0"
                          step="0.01"
                          aria-label={`Taxa hora ${t.rotulo}`}
                          value={form[t.chave] ?? ''}
                          onChange={(e) => setCampo(t.chave, Number(e.target.value))}
                          style={{
                            width: 140, textAlign: 'center',
                            padding: '8px 10px',
                            border: '1px dashed var(--borda-forte)',
                            borderRadius: 'var(--raio-1)',
                            background: 'var(--superficie)',
                            color: 'var(--texto)',
                            fontVariantNumeric: 'tabular-nums',
                          }}
                        />
                      </td>
                      <td className="num texto-3" style={{ paddingRight: 20 }}>
                        {fmtBRLExato((Number(form[t.chave]) || 0) * 8)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* ============ Aparência (tema) ============ */}
          <section className="card" ref={refs.aparencia} data-secao="aparencia">
            <SecaoAparencia />
          </section>

          {/* ============ Preferências Regionais ============ */}
          <section className="card" ref={refs.preferencias} data-secao="preferencias">
            <CabecalhoSecao
              titulo="Preferências Regionais"
              descricao="Formatos de exibição para datas, números e moedas."
              botao="Salvar Preferências"
              secaoId="preferencias"
              salvando={salvando === 'preferencias'}
              feedback={feedback.preferencias}
              onSalvar={() => salvarSecao('preferencias', ['formato_data', 'moeda', 'fuso'])}
            />
            <div className="card-corpo">
              <div className="form-linha" style={{ alignItems: 'stretch' }}>
                <div className="campo" style={{ flex: 1 }}>
                  <label htmlFor="cfg-formato">Formato de data</label>
                  <select
                    id="cfg-formato"
                    value={form.formato_data ?? ''}
                    onChange={(e) => setCampo('formato_data', e.target.value)}
                  >
                    {OPCOES_FORMATO_DATA.map((o) => <option key={o.valor} value={o.valor}>{o.rotulo}</option>)}
                  </select>
                </div>
                <div className="campo" style={{ flex: 1 }}>
                  <label htmlFor="cfg-moeda">Moeda base</label>
                  <select
                    id="cfg-moeda"
                    value={form.moeda ?? ''}
                    onChange={(e) => setCampo('moeda', e.target.value)}
                  >
                    {OPCOES_MOEDA.map((o) => <option key={o.valor} value={o.valor}>{o.rotulo}</option>)}
                  </select>
                </div>
                <div className="campo" style={{ flex: 1 }}>
                  <label htmlFor="cfg-fuso">Fuso horário padrão</label>
                  <select
                    id="cfg-fuso"
                    value={form.fuso ?? ''}
                    onChange={(e) => setCampo('fuso', e.target.value)}
                  >
                    {OPCOES_FUSO.map((o) => <option key={o.valor} value={o.valor}>{o.rotulo}</option>)}
                  </select>
                </div>
              </div>
            </div>
          </section>

          {/* ============ Feriados (calendário corporativo) ============ */}
          <section className="card" ref={refs.feriados} data-secao="feriados">
            <SecaoFeriados />
          </section>

          {/* ============ Modelos de projeto ============ */}
          <section className="card" ref={refs.modelos} data-secao="modelos">
            <SecaoModelos />
          </section>

          {/* ============ Copiloto IA (plugável) ============ */}
          <section className="card" ref={refs.copiloto} data-secao="copiloto">
            <CabecalhoSecao
              titulo="Copiloto IA"
              descricao="Sem chave, o copiloto usa os insights determinísticos do motor. Cole a chave da API Anthropic para ativar as respostas em linguagem natural."
              botao="Salvar Copiloto"
              secaoId="copiloto"
              salvando={salvando === 'copiloto'}
              feedback={feedback.copiloto}
              onSalvar={() => salvarSecao('copiloto', ['anthropic_api_key', 'modelo_ia'])}
            />
            <div className="card-corpo">
              <div className="form-linha" style={{ alignItems: 'flex-end' }}>
                <div className="campo" style={{ flex: 2 }}>
                  <label htmlFor="cfg-chave-ia">Chave da API Anthropic</label>
                  <input
                    id="cfg-chave-ia"
                    className="mono"
                    type="password"
                    placeholder="sk-ant-…"
                    autoComplete="off"
                    value={form.anthropic_api_key ?? ''}
                    onChange={(e) => setCampo('anthropic_api_key', e.target.value)}
                  />
                  <span className="ajuda">
                    Obtida em console.anthropic.com. Fica no banco local; deixe em branco para desativar a IA generativa.
                  </span>
                </div>
                <div className="campo" style={{ flex: 1 }}>
                  <label htmlFor="cfg-modelo-ia">Modelo</label>
                  <select
                    id="cfg-modelo-ia"
                    value={form.modelo_ia ?? 'claude-sonnet-5'}
                    onChange={(e) => setCampo('modelo_ia', e.target.value)}
                  >
                    {OPCOES_MODELO_IA.map((o) => <option key={o.valor} value={o.valor}>{o.rotulo}</option>)}
                  </select>
                </div>
              </div>
              <div className="linha-flex" style={{ gap: 8, marginTop: 12 }}>
                <span className={`badge ${(form.anthropic_api_key ?? '').trim() ? 'badge-verde' : ''}`}>
                  {(form.anthropic_api_key ?? '').trim() ? 'IA generativa será ativada ao salvar' : 'Modo determinístico (sem chave)'}
                </span>
                <span className="texto-3" style={{ fontSize: 12 }}>
                  Os cálculos continuam 100% no motor determinístico — a IA só interpreta e recomenda.
                </span>
              </div>
            </div>
          </section>

          {/* ============ Usuários (RBAC) ============ */}
          <section className="card" ref={refs.usuarios} data-secao="usuarios">
            <SecaoUsuarios />
          </section>

          {/* ============ Auditoria ============ */}
          <section className="card" ref={refs.auditoria} data-secao="auditoria">
            <SecaoAuditoria />
          </section>
        </div>
      </div>
    </>
  )
}

/** Tema da interface. Três opções com amostra visual (em vez do interruptor
 * sol/lua): Claro, Escuro e Sistema — esta última segue o SO em tempo real. */
function SecaoAparencia() {
  const { preferencia, efetivo, escolher } = useTema()

  const OPCOES = [
    { id: 'claro', rotulo: 'Claro', cores: ['#ffffff', '#f5f8ff'] },
    { id: 'escuro', rotulo: 'Escuro', cores: ['#141d33', '#0d1424'] },
    { id: 'sistema', rotulo: 'Sistema', cores: ['#ffffff', '#0d1424'] },
  ]

  return (
    <>
      <div className="card-cabecalho" style={{ paddingBottom: 6 }}>
        <div>
          <h2 className="card-titulo-secao" style={{ padding: 0 }}>Aparência</h2>
          <div className="texto-3" style={{ fontSize: 12.5, marginTop: 2 }}>
            Vale para este navegador. “Sistema” acompanha a preferência do seu computador
            {preferencia === 'sistema' && ` (agora: ${efetivo})`}.
          </div>
        </div>
      </div>
      <div className="card-corpo">
        <div className="tema-opcoes" role="group" aria-label="Tema da interface">
          {OPCOES.map((o) => (
            <button
              key={o.id}
              type="button"
              className="tema-opcao"
              aria-pressed={preferencia === o.id}
              onClick={() => escolher(o.id)}
            >
              <span className="tema-amostra" aria-hidden="true">
                <span className="lado" style={{ background: o.cores[0] }} />
                <span className="lado" style={{ background: o.cores[1] }} />
              </span>
              <span className="rotulo">{o.rotulo}</span>
            </button>
          ))}
        </div>
      </div>
    </>
  )
}

/** Usuários do sistema: gestor cria contas, vincula consultores, redefine
 * senha e desativa acesso (a sessão viva morre junto). */
function SecaoUsuarios() {
  const [usuarios, setUsuarios] = useState(null)
  const [consultores, setConsultores] = useState([])
  const [novo, setNovo] = useState(null)
  const [erro, setErro] = useState(null)

  const carregar = () => {
    api.get('/usuarios').then(setUsuarios).catch((e) => setErro(e.message))
    api.get('/consultores').then(setConsultores).catch(() => {})
  }
  useEffect(() => { carregar() }, [])

  const criar = async (e) => {
    e.preventDefault()
    setErro(null)
    try {
      await api.post('/usuarios', {
        ...novo,
        consultor_id: novo.perfil === 'consultor' ? Number(novo.consultor_id) : null,
      })
      setNovo(null)
      carregar()
    } catch (err) { setErro(err.message) }
  }

  const alternarAtivo = async (u) => {
    setErro(null)
    try {
      await api.patch(`/usuarios/${u.id}`, { ativo: !u.ativo })
      carregar()
    } catch (err) { setErro(err.message) }
  }

  const redefinirSenha = async (u) => {
    const senha = window.prompt(`Nova senha para ${u.nome} (mín. 6 caracteres):`)
    if (!senha) return
    setErro(null)
    try {
      await api.patch(`/usuarios/${u.id}`, { senha })
    } catch (err) { setErro(err.message) }
  }

  return (
    <>
      <div className="card-cabecalho" style={{ paddingBottom: 6 }}>
        <div>
          <h2 className="card-titulo-secao" style={{ padding: 0 }}>Usuários</h2>
          <div className="texto-3" style={{ fontSize: 12.5, marginTop: 2 }}>
            Contas com senha real. Gestor vê tudo; consultor entra no próprio espaço (horas, despesas, ausências, agenda).
          </div>
        </div>
        <button className="botao botao-secundario" onClick={() => setNovo({ email: '', nome: '', senha: '', perfil: 'consultor', consultor_id: consultores[0]?.id ?? '' })}>
          Novo usuário
        </button>
      </div>
      <div className="card-corpo">
        {erro && <div className="mensagem-erro">{erro}</div>}
        {novo && (
          <form onSubmit={criar} className="form-linha" style={{ marginBottom: 14, alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div className="campo" style={{ flex: 1, minWidth: 160 }}>
              <label htmlFor="usu-nome">Nome</label>
              <input id="usu-nome" value={novo.nome} required autoFocus onChange={(e) => setNovo({ ...novo, nome: e.target.value })} />
            </div>
            <div className="campo" style={{ flex: 1, minWidth: 180 }}>
              <label htmlFor="usu-email">E-mail</label>
              <input id="usu-email" type="email" value={novo.email} required onChange={(e) => setNovo({ ...novo, email: e.target.value })} />
            </div>
            <div className="campo" style={{ minWidth: 130 }}>
              <label htmlFor="usu-senha">Senha</label>
              <input id="usu-senha" type="password" value={novo.senha} required minLength={6} autoComplete="new-password"
                onChange={(e) => setNovo({ ...novo, senha: e.target.value })} />
            </div>
            <div className="campo">
              <label htmlFor="usu-perfil">Perfil</label>
              <select id="usu-perfil" value={novo.perfil} onChange={(e) => setNovo({ ...novo, perfil: e.target.value })}>
                <option value="consultor">Consultor</option>
                <option value="gestor">Gestor</option>
              </select>
            </div>
            {novo.perfil === 'consultor' && (
              <div className="campo" style={{ minWidth: 170 }}>
                <label htmlFor="usu-consultor">Consultor vinculado</label>
                <select id="usu-consultor" value={novo.consultor_id} onChange={(e) => setNovo({ ...novo, consultor_id: e.target.value })}>
                  {consultores.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
                </select>
              </div>
            )}
            <button className="botao botao-primario" type="submit">Criar</button>
            <button className="botao botao-fantasma" type="button" onClick={() => setNovo(null)}>Cancelar</button>
          </form>
        )}
        {usuarios === null ? null : (
          <table className="tabela">
            <thead>
              <tr><th>Nome</th><th>E-mail</th><th>Perfil</th><th>Vinculado a</th><th>Status</th><th /></tr>
            </thead>
            <tbody>
              {usuarios.map((u) => (
                <tr key={u.id} style={{ opacity: u.ativo ? 1 : 0.55 }}>
                  <td>{u.nome}</td>
                  <td className="mono" style={{ fontSize: 12.5 }}>{u.email}</td>
                  <td><span className={`badge ${u.perfil === 'gestor' ? 'badge-azul' : 'badge-cinza'}`}>{u.perfil}</span></td>
                  <td className="texto-2">{u.consultor || '—'}</td>
                  <td>
                    <span className={`badge ${u.ativo ? 'badge-verde' : 'badge-vermelho'}`}>{u.ativo ? 'ativo' : 'desativado'}</span>
                  </td>
                  <td className="num">
                    <div className="linha-flex" style={{ gap: 6, justifyContent: 'flex-end' }}>
                      <button className="botao botao-fantasma botao-pequeno" onClick={() => redefinirSenha(u)}>Redefinir senha</button>
                      <button className="botao botao-fantasma botao-pequeno" onClick={() => alternarAtivo(u)}>
                        {u.ativo ? 'Desativar' : 'Reativar'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  )
}

/** Trilha de auditoria: toda mutação da API (quem, quando, o quê, resultado),
 * gravada por middleware — nada depende de lembrar de logar. */
function SecaoAuditoria() {
  const [eventos, setEventos] = useState(null)
  const [erro, setErro] = useState(null)

  useEffect(() => {
    api.get('/auditoria?limite=60').then(setEventos).catch((e) => setErro(e.message))
  }, [])

  const fmtQuando = (iso) => {
    const [data, hora] = iso.split('T')
    const [ano, mes, dia] = data.split('-')
    return `${dia}/${mes}/${ano} ${hora}`
  }

  return (
    <>
      <div className="card-cabecalho" style={{ paddingBottom: 6 }}>
        <div>
          <h2 className="card-titulo-secao" style={{ padding: 0 }}>Auditoria</h2>
          <div className="texto-3" style={{ fontSize: 12.5, marginTop: 2 }}>
            Toda mutação da API (criar, alterar, excluir) fica registrada: quem fez, quando, onde e o resultado.
          </div>
        </div>
      </div>
      <div className="card-corpo" style={{ maxHeight: 420, overflowY: 'auto' }}>
        {erro && <div className="mensagem-erro">{erro}</div>}
        {eventos === null ? null : eventos.length === 0 ? (
          <div className="vazio">Nenhum evento ainda — as próximas alterações aparecem aqui.</div>
        ) : (
          <table className="tabela">
            <thead>
              <tr><th>Quando</th><th>Usuário</th><th>Ação</th><th className="num">Status</th></tr>
            </thead>
            <tbody>
              {eventos.map((e) => (
                <tr key={e.id}>
                  <td className="mono" style={{ fontSize: 12 }}>{fmtQuando(e.quando)}</td>
                  <td>{e.usuario || <span className="texto-3">—</span>}
                    {e.perfil && <span className="texto-3" style={{ fontSize: 11 }}> ({e.perfil.replace('PerfilUsuario.', '')})</span>}
                  </td>
                  <td className="mono" style={{ fontSize: 12 }}>
                    <span className={`badge ${e.metodo === 'DELETE' ? 'badge-vermelho' : e.metodo === 'POST' ? 'badge-azul' : 'badge-cinza'}`} style={{ marginRight: 6 }}>{e.metodo}</span>
                    {e.caminho}
                  </td>
                  <td className="num mono" style={{ color: e.status < 400 ? 'var(--verde)' : 'var(--vermelho)' }}>{e.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  )
}

/** Modelos de projeto: as 6 fases Activate são fixas; o modelo define as
 * ENTREGAS e o QUALITY GATE de cada fase por tipo de trabalho. Novos modelos
 * nascem como cópia de um existente e são editados item a item. */
function SecaoModelos() {
  const [modelos, setModelos] = useState(null)
  const [novo, setNovo] = useState(null) // {nome, copiar_de}
  const [editando, setEditando] = useState(null) // detalhe do modelo no modal
  const [erro, setErro] = useState(null)

  const carregar = () => api.get('/modelos').then(setModelos).catch((e) => setErro(e.message))
  useEffect(() => { carregar() }, [])

  const criar = async (e) => {
    e.preventDefault()
    setErro(null)
    try {
      const detalhe = await api.post('/modelos', {
        nome: novo.nome,
        copiar_de: novo.copiar_de ? Number(novo.copiar_de) : null,
      })
      setNovo(null)
      setEditando(detalhe) // já abre para personalizar
      carregar()
    } catch (err) { setErro(err.message) }
  }

  const remover = async (m) => {
    setErro(null)
    try {
      await api.del(`/modelos/${m.id}`)
      carregar()
    } catch (err) { setErro(err.message) }
  }

  return (
    <>
      <div className="card-cabecalho" style={{ paddingBottom: 6 }}>
        <div>
          <h2 className="card-titulo-secao" style={{ padding: 0 }}>Modelos de projeto</h2>
          <div className="texto-3" style={{ fontSize: 12.5, marginTop: 2 }}>
            As 6 fases Activate são fixas — o modelo define as entregas e o Quality Gate de cada fase (implantação, rollout, AMS…).
          </div>
        </div>
        <button className="botao botao-secundario" onClick={() => setNovo({ nome: '', copiar_de: '' })}>
          Novo modelo
        </button>
      </div>
      <div className="card-corpo">
        {erro && <div className="mensagem-erro">{erro}</div>}
        {novo && (
          <form onSubmit={criar} className="form-linha" style={{ marginBottom: 14, alignItems: 'flex-end' }}>
            <div className="campo" style={{ flex: 1 }}>
              <label htmlFor="mod-nome">Nome do modelo</label>
              <input id="mod-nome" value={novo.nome} required autoFocus placeholder="Ex.: AMS / Sustentação"
                onChange={(e) => setNovo({ ...novo, nome: e.target.value })} />
            </div>
            <div className="campo" style={{ minWidth: 220 }}>
              <label htmlFor="mod-copiar">Começar como cópia de</label>
              <select id="mod-copiar" value={novo.copiar_de}
                onChange={(e) => setNovo({ ...novo, copiar_de: e.target.value })}>
                <option value="">Modelo padrão</option>
                {(modelos || []).filter((m) => !m.padrao).map((m) => <option key={m.id} value={m.id}>{m.nome}</option>)}
              </select>
            </div>
            <button className="botao botao-primario" type="submit" disabled={!novo.nome.trim()}>Criar e editar</button>
            <button className="botao botao-fantasma" type="button" onClick={() => setNovo(null)}>Cancelar</button>
          </form>
        )}
        {modelos === null ? null : (
          <ul className="lista-atividades">
            {modelos.map((m) => (
              <li key={m.id}>
                <span style={{ flex: 1 }}>
                  <strong>{m.nome}</strong>
                  {m.padrao && <span className="badge badge-azul" style={{ marginLeft: 8 }}>padrão</span>}
                  {m.descricao && <span className="texto-3" style={{ fontSize: 12, display: 'block' }}>{m.descricao}</span>}
                </span>
                <span className="texto-3 mono" style={{ fontSize: 12 }}>
                  {m.total_atividades} entregas · {m.total_gates} gates
                  {m.projetos_usando > 0 && ` · ${m.projetos_usando} projeto(s)`}
                </span>
                <button className="botao botao-fantasma botao-pequeno" type="button"
                  onClick={async () => setEditando(await api.get(`/modelos/${m.id}`))}>
                  Editar
                </button>
                {!m.padrao && m.projetos_usando === 0 && (
                  <button type="button" className="fechar-x" title="Remover modelo" onClick={() => remover(m)}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {editando && (
        <ModalEditorModelo modelo={editando} onFechar={() => { setEditando(null); carregar() }} />
      )}
    </>
  )
}

/** Editor do modelo: por fase, adicionar/remover entregas e itens de gate. */
function ModalEditorModelo({ modelo, onFechar }) {
  const [detalhe, setDetalhe] = useState(modelo)
  const [faseAberta, setFaseAberta] = useState(modelo.fases?.[0]?.nome ?? 'Discover')
  const [novaEntrega, setNovaEntrega] = useState('')
  const [novoGate, setNovoGate] = useState({ codigo: '', pergunta: '' })
  const [erro, setErro] = useState(null)

  const recarregar = async () => setDetalhe(await api.get(`/modelos/${detalhe.id}`))
  const fase = detalhe.fases.find((f) => f.nome === faseAberta)

  const addEntrega = async (e) => {
    e.preventDefault()
    setErro(null)
    try {
      await api.post(`/modelos/${detalhe.id}/atividades`, { fase: faseAberta, titulo: novaEntrega })
      setNovaEntrega('')
      recarregar()
    } catch (err) { setErro(err.message) }
  }
  const delEntrega = async (a) => { await api.del(`/modelos/atividades/${a.id}`); recarregar() }
  const addGate = async (e) => {
    e.preventDefault()
    setErro(null)
    try {
      await api.post(`/modelos/${detalhe.id}/gates`, { fase: faseAberta, ...novoGate })
      setNovoGate({ codigo: '', pergunta: '' })
      recarregar()
    } catch (err) { setErro(err.message) }
  }
  const delGate = async (g) => { await api.del(`/modelos/gates/${g.id}`); recarregar() }

  return (
    <Modal extraLarga titulo={`Modelo — ${detalhe.nome}`} onFechar={onFechar}
      rodape={<button className="botao botao-primario" onClick={onFechar}>Concluir</button>}>
      {erro && <div className="mensagem-erro">{erro}</div>}
      <div className="linha-flex" style={{ gap: 6, flexWrap: 'wrap', marginBottom: 14 }}>
        {detalhe.fases.map((f) => (
          <button key={f.nome} type="button"
            className={`botao botao-pequeno ${faseAberta === f.nome ? 'botao-primario' : 'botao-fantasma'}`}
            onClick={() => setFaseAberta(f.nome)}>
            {f.nome} <span className="mono" style={{ fontSize: 11 }}>({f.atividades.length}/{f.gates.length})</span>
          </button>
        ))}
      </div>

      {fase && (
        <div className="grid-2-igual" style={{ gap: 18, alignItems: 'start' }}>
          <div>
            <h4 style={{ margin: '0 0 8px' }}>Entregas de <span className={`badge ${corFase(fase.nome)}`}>{fase.nome}</span></h4>
            <ul className="lista-atividades">
              {fase.atividades.map((a) => (
                <li key={a.id}>
                  <span style={{ flex: 1, fontSize: 13 }}>{a.titulo}</span>
                  <button type="button" className="fechar-x" title="Remover" onClick={() => delEntrega(a)}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
                  </button>
                </li>
              ))}
              {fase.atividades.length === 0 && <li className="texto-3" style={{ fontSize: 12.5 }}>Nenhuma entrega nesta fase.</li>}
            </ul>
            <form onSubmit={addEntrega} className="linha-flex" style={{ gap: 8, marginTop: 10 }}>
              <input value={novaEntrega} required placeholder="Nova entrega…" style={{ flex: 1 }}
                onChange={(e) => setNovaEntrega(e.target.value)} />
              <button className="botao botao-secundario botao-pequeno" type="submit" disabled={!novaEntrega.trim()}>Adicionar</button>
            </form>
          </div>

          <div>
            <h4 style={{ margin: '0 0 8px' }}>Quality Gate</h4>
            <ul className="lista-atividades">
              {fase.gates.map((g) => (
                <li key={g.id}>
                  <span className="mono" style={{ fontSize: 11.5, minWidth: 58 }}>{g.codigo}</span>
                  <span style={{ flex: 1, fontSize: 13 }}>{g.pergunta}</span>
                  <button type="button" className="fechar-x" title="Remover" onClick={() => delGate(g)}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
                  </button>
                </li>
              ))}
              {fase.gates.length === 0 && <li className="texto-3" style={{ fontSize: 12.5 }}>Nenhum item de gate nesta fase.</li>}
            </ul>
            <form onSubmit={addGate} className="linha-flex" style={{ gap: 8, marginTop: 10 }}>
              <input value={novoGate.codigo} required placeholder="COD-01" className="mono" style={{ width: 90 }}
                onChange={(e) => setNovoGate({ ...novoGate, codigo: e.target.value })} />
              <input value={novoGate.pergunta} required placeholder="Pergunta do checklist…" style={{ flex: 1 }}
                onChange={(e) => setNovoGate({ ...novoGate, pergunta: e.target.value })} />
              <button className="botao botao-secundario botao-pequeno" type="submit"
                disabled={!novoGate.codigo.trim() || !novoGate.pergunta.trim()}>Adicionar</button>
            </form>
          </div>
        </div>
      )}
    </Modal>
  )
}

/** Feriados do calendário corporativo — dias NÃO úteis para o motor inteiro
 * (receita, capacidade, faturas, cascata). Recarregado no backend ao salvar. */
function SecaoFeriados() {
  const [feriados, setFeriados] = useState(null)
  const [novo, setNovo] = useState({ data: '', nome: '' })
  const [erro, setErro] = useState(null)

  const carregar = () => api.get('/configuracoes/feriados').then(setFeriados).catch((e) => setErro(e.message))
  useEffect(() => { carregar() }, [])

  const adicionar = async (e) => {
    e.preventDefault()
    setErro(null)
    try {
      await api.post('/configuracoes/feriados', novo)
      setNovo({ data: '', nome: '' })
      carregar()
    } catch (err) { setErro(err.message) }
  }
  const remover = async (f) => {
    await api.del(`/configuracoes/feriados/${f.id}`)
    carregar()
  }

  const fmtDia = (iso) => {
    const [ano, mes, dia] = iso.split('-')
    return `${dia}/${mes}/${ano}`
  }

  return (
    <>
      <div className="card-cabecalho" style={{ paddingBottom: 6 }}>
        <div>
          <h2 className="card-titulo-secao" style={{ padding: 0 }}>Feriados</h2>
          <div className="texto-3" style={{ fontSize: 12.5, marginTop: 2 }}>
            Dias não úteis para TODO o motor: receita prevista, capacidade, faturas e recálculo em cascata.
          </div>
        </div>
      </div>
      <div className="card-corpo">
        {erro && <div className="mensagem-erro">{erro}</div>}
        <form onSubmit={adicionar} className="form-linha" style={{ marginBottom: 14 }}>
          <div className="campo">
            <label htmlFor="fer-data">Data</label>
            <input id="fer-data" type="date" value={novo.data} required
              onChange={(e) => setNovo({ ...novo, data: e.target.value })} />
          </div>
          <div className="campo" style={{ flex: 1 }}>
            <label htmlFor="fer-nome">Nome</label>
            <input id="fer-nome" value={novo.nome} required placeholder="Ex.: Independência do Brasil"
              onChange={(e) => setNovo({ ...novo, nome: e.target.value })} />
          </div>
          <button className="botao botao-secundario" type="submit" disabled={!novo.data || !novo.nome}>
            Adicionar feriado
          </button>
        </form>
        {feriados === null ? null : feriados.length === 0 ? (
          <div className="vazio">Nenhum feriado cadastrado — todos os dias de semana contam como úteis.</div>
        ) : (
          <ul className="lista-atividades">
            {feriados.map((f) => (
              <li key={f.id}>
                <span className="mono" style={{ minWidth: 90, fontWeight: 600 }}>{fmtDia(f.data)}</span>
                <span style={{ flex: 1 }}>{f.nome}</span>
                <button type="button" className="fechar-x" title="Remover feriado" onClick={() => remover(f)}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  )
}
