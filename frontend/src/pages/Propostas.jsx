import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import BotaoExportar from '../components/BotaoExportar'
import Icone from '../components/Icone'
import Modal from '../components/Modal'
import { SkeletonPagina } from '../components/Skeleton'
import { fmtBRL, fmtData, fmtPct, iniciais } from '../format'

const IC_NOVA = ['M12 5v14', 'M5 12h14']
const IC_AVANCAR = ['M5 12h14', 'M12 5l7 7-7 7']
const IC_CONVERTER = ['M20 6 9 17l-5-5']

const COLUNAS = [
  ['qualificacao', 'Qualificação'],
  ['proposta', 'Proposta enviada'],
  ['negociacao', 'Negociação'],
  ['aprovada', 'Aprovada'],
]

export default function Propostas() {
  const nav = useNavigate()
  const [dados, setDados] = useState(null)
  const [erro, setErro] = useState(null)
  const [modalNova, setModalNova] = useState(false)
  const [params, setParams] = useSearchParams()
  // "+ Novo" da sidebar chega como ?novo=1 e ja abre o formulario
  useEffect(() => {
    if (params.get('novo')) {
      setModalNova(true)
      params.delete('novo')
      setParams(params, { replace: true })
    }
  }, [params, setParams])

  const [convertendo, setConvertendo] = useState(null) // proposta aprovada → modal data_inicio
  const [dataInicio, setDataInicio] = useState(new Date().toISOString().slice(0, 10))

  const carregar = useCallback(() => {
    api.get('/propostas').then(setDados).catch((e) => setErro(e.message))
  }, [])

  useEffect(carregar, [carregar])

  if (erro) return <div className="mensagem-erro">{erro}</div>
  if (!dados) return <SkeletonPagina kpis />

  const ativas = dados.propostas.filter((p) => !['perdida', 'convertida'].includes(p.estagio))
  const encerradas = dados.propostas.filter((p) => ['perdida', 'convertida'].includes(p.estagio))

  const avancar = async (p) => {
    try {
      await api.post(`/propostas/${p.id}/avancar`)
      carregar()
    } catch (e) { setErro(e.message) }
  }
  const marcarPerdida = async (p) => {
    if (!confirm(`Marcar "${p.nome}" como perdida?`)) return
    await api.patch(`/propostas/${p.id}`, { estagio: 'perdida' })
    carregar()
  }
  const converter = async () => {
    try {
      const r = await api.post(`/propostas/${convertendo.id}/converter`, { data_inicio: dataInicio })
      setConvertendo(null)
      nav(`/projetos/${r.projeto_id}`)
    } catch (e) { setErro(e.message) }
  }

  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <h1>Propostas</h1>
          <div className="descricao">Funil comercial — proposta aprovada vira projeto com as 6 fases Activate</div>
        </div>
        <div className="linha-flex">
          <BotaoExportar recurso="propostas" />
          <button className="botao botao-primario" onClick={() => setModalNova(true)}>
            <Icone d={IC_NOVA} size={15} /> Nova proposta
          </button>
        </div>
      </div>

      <div className="grid-kpi" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
        <div className="card kpi">
          <div className="rotulo">Funil ativo</div>
          <div className="valor">{fmtBRL(dados.funil_total)}</div>
          <div className="detalhe">{ativas.length} proposta(s) em andamento</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Funil ponderado</div>
          <div className="valor" style={{ color: 'var(--azul)' }}>{fmtBRL(dados.funil_ponderado)}</div>
          <div className="detalhe">valor × probabilidade</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Prontas para converter</div>
          <div className="valor" style={{ color: 'var(--verde)' }}>
            {ativas.filter((p) => p.estagio === 'aprovada').length}
          </div>
          <div className="detalhe">aprovadas aguardando virar projeto</div>
        </div>
      </div>

      <div className="kanban">
        {COLUNAS.map(([estagio, rotulo]) => {
          const cards = ativas.filter((p) => p.estagio === estagio)
          return (
            <div className="kanban-col" key={estagio}>
              <div className="titulo">
                {rotulo} <span className="contagem">({cards.length})</span>
              </div>
              {cards.length === 0 && <div className="vazio" style={{ padding: '14px 0', fontSize: 12 }}>—</div>}
              {cards.map((p) => (
                <div className="kanban-card" key={p.id}>
                  <div className="nome">{p.nome}</div>
                  <div className="linha-flex" style={{ gap: 6, marginTop: 4 }}>
                    <span className="avatar-consultor" style={{ width: 20, height: 20, fontSize: 8.5 }}>{iniciais(p.cliente)}</span>
                    <span className="texto-2" style={{ fontSize: 12 }}>{p.cliente}</span>
                  </div>
                  <div className="meta">
                    <span className="mono" style={{ fontWeight: 600 }}>{fmtBRL(p.valor_estimado)}</span>
                    <span className="linha-flex" style={{ gap: 4 }}>
                      {p.margem_estimada > 0 && (
                        <span className="badge badge-verde mono" title="Margem estimada pelo mix de senioridade">
                          {fmtPct(p.margem_estimada)}
                        </span>
                      )}
                      <span className="badge badge-cinza mono" title="Probabilidade de fechamento">{fmtPct(p.probabilidade)}</span>
                    </span>
                  </div>
                  <div className="texto-3 mono" style={{ fontSize: 11, marginTop: 4 }}>desde {fmtData(p.criada_em)}</div>
                  <div className="acoes">
                    {estagio === 'aprovada' ? (
                      <button className="botao botao-primario botao-pequeno" onClick={() => setConvertendo(p)}>
                        <Icone d={IC_CONVERTER} size={12} /> Converter em projeto
                      </button>
                    ) : (
                      <button className="botao botao-secundario botao-pequeno" onClick={() => avancar(p)}>
                        Avançar <Icone d={IC_AVANCAR} size={12} />
                      </button>
                    )}
                    <button className="botao botao-fantasma botao-pequeno" onClick={() => marcarPerdida(p)}>Perdida</button>
                  </div>
                </div>
              ))}
            </div>
          )
        })}
      </div>

      {encerradas.length > 0 && (
        <div className="card secao">
          <h2 className="card-titulo-secao">Histórico (perdidas e convertidas)</h2>
          <div className="card-corpo" style={{ paddingTop: 8 }}>
            <table className="tabela">
              <thead>
                <tr><th>Proposta</th><th>Cliente</th><th className="num">Valor</th><th>Desfecho</th><th>Decidida</th></tr>
              </thead>
              <tbody>
                {encerradas.map((p) => (
                  <tr key={p.id}>
                    <td>{p.nome}</td>
                    <td className="texto-2">{p.cliente}</td>
                    <td className="num">{fmtBRL(p.valor_estimado)}</td>
                    <td>
                      {p.estagio === 'convertida'
                        ? <Link className="link" to={`/projetos/${p.projeto_id}`}><span className="badge badge-verde">Convertida → projeto</span></Link>
                        : <span className="badge badge-vermelho">Perdida</span>}
                    </td>
                    <td className="mono texto-3">{p.decidida_em ? fmtData(p.decidida_em) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {modalNova && (
        <FormProposta onFechar={() => setModalNova(false)} onCriada={() => { setModalNova(false); carregar() }} />
      )}

      {convertendo && (
        <Modal titulo={`Converter em projeto — ${convertendo.nome}`} onFechar={() => setConvertendo(null)}
          rodape={<>
            <button className="botao botao-fantasma" onClick={() => setConvertendo(null)}>Cancelar</button>
            <button className="botao botao-primario" onClick={converter}>
              <Icone d={IC_CONVERTER} size={13} /> Criar projeto
            </button>
          </>}>
          <div className="campo">
            <label htmlFor="cv-inicio">Data de início do projeto *</label>
            <input id="cv-inicio" type="date" value={dataInicio} onChange={(e) => setDataInicio(e.target.value)} />
            <span className="ajuda">
              O projeto nasce com as 6 fases SAP Activate, entregas padrão e Quality Gates —
              cliente {convertendo.cliente}, {fmtBRL(convertendo.valor_estimado)} estimados.
            </span>
          </div>
        </Modal>
      )}
    </>
  )
}

function FormProposta({ onFechar, onCriada }) {
  const [clientes, setClientes] = useState([])
  const [cfg, setCfg] = useState(null) // taxas padrão por senioridade
  const [form, setForm] = useState({
    cliente_id: '', nome: '', descricao: '', escopo: '', premissas: '',
    horas_junior: '', horas_pleno: '', horas_senior: '',
    valor_estimado: '', probabilidade: 0.5, validade: '',
  })
  const [erro, setErro] = useState(null)

  useEffect(() => {
    api.get('/clientes').then((cs) => {
      setClientes(cs)
      setForm((f) => ({ ...f, cliente_id: f.cliente_id || cs[0]?.id || '' }))
    }).catch(() => {})
    api.get('/configuracoes').then(setCfg).catch(() => {})
  }, [])

  // prévia da precificação (o backend recalcula na gravação)
  const hj = Number(form.horas_junior || 0)
  const hp = Number(form.horas_pleno || 0)
  const hs = Number(form.horas_senior || 0)
  const totalHoras = hj + hp + hs
  const valorMix = cfg ? hj * cfg.taxa_junior + hp * cfg.taxa_pleno + hs * cfg.taxa_senior : 0

  const salvar = async (e) => {
    e.preventDefault()
    setErro(null)
    try {
      await api.post('/propostas', {
        cliente_id: Number(form.cliente_id),
        nome: form.nome,
        descricao: form.descricao,
        escopo: form.escopo,
        premissas: form.premissas,
        horas_junior: hj,
        horas_pleno: hp,
        horas_senior: hs,
        valor_estimado: Number(form.valor_estimado || 0),
        probabilidade: Number(form.probabilidade),
        validade: form.validade || null,
      })
      onCriada()
    } catch (err) { setErro(err.message) }
  }

  return (
    <Modal larga titulo="Nova proposta" onFechar={onFechar}
      rodape={<>
        <button className="botao botao-fantasma" onClick={onFechar}>Cancelar</button>
        <button className="botao botao-primario" type="submit" form="form-proposta" disabled={!form.nome || !form.cliente_id}>
          Criar no funil
        </button>
      </>}>
      <form id="form-proposta" onSubmit={salvar} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {erro && <div className="mensagem-erro">{erro}</div>}
        <div className="form-linha">
          <div className="campo" style={{ flex: 2 }}>
            <label htmlFor="pp-nome">Nome da proposta *</label>
            <input id="pp-nome" value={form.nome} autoFocus required
              onChange={(e) => setForm({ ...form, nome: e.target.value })}
              placeholder="Ex.: Implementação SAP IBP" />
          </div>
          <div className="campo" style={{ flex: 1 }}>
            <label htmlFor="pp-cliente">Cliente *</label>
            <select id="pp-cliente" value={form.cliente_id} onChange={(e) => setForm({ ...form, cliente_id: e.target.value })}>
              {clientes.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
          </div>
        </div>

        {/* precificação por mix de senioridade */}
        <div style={{ border: '1px solid var(--borda)', borderRadius: 'var(--raio-2)', padding: 14, background: 'var(--superficie-brilho)' }}>
          <div className="sub-secao" style={{ margin: '0 0 10px' }}>Precificação por mix de senioridade</div>
          <div className="form-linha">
            {[['junior', 'Júnior', 'horas_junior'], ['pleno', 'Pleno', 'horas_pleno'], ['senior', 'Sênior', 'horas_senior']].map(([k, rot, campo]) => (
              <div className="campo" key={k}>
                <label htmlFor={`pp-${k}`}>
                  Horas {rot}
                  {cfg && <span className="texto-3 mono" style={{ fontWeight: 400 }}> · {fmtBRL(cfg[`taxa_${k}`])}/h</span>}
                </label>
                <input id={`pp-${k}`} type="number" min="0" step="10" value={form[campo]}
                  onChange={(e) => setForm({ ...form, [campo]: e.target.value })} />
              </div>
            ))}
            <div className="campo" style={{ marginLeft: 'auto', textAlign: 'right' }}>
              <label>Valor calculado</label>
              <div className="mono" style={{ fontSize: 18, fontWeight: 600, color: 'var(--azul)', padding: '4px 0' }}>
                {totalHoras > 0 ? fmtBRL(valorMix) : '—'}
              </div>
              {totalHoras > 0 && <span className="ajuda">{totalHoras}h · margem estimada calculada ao salvar</span>}
            </div>
          </div>
          {totalHoras === 0 && (
            <div className="campo" style={{ marginTop: 8, maxWidth: 220 }}>
              <label htmlFor="pp-valor">Valor manual (R$)</label>
              <input id="pp-valor" type="number" min="0" step="1000" value={form.valor_estimado}
                onChange={(e) => setForm({ ...form, valor_estimado: e.target.value })} />
              <span className="ajuda">Sem mix de horas, informe o valor fechado.</span>
            </div>
          )}
        </div>

        <div className="form-linha">
          <div className="campo">
            <label htmlFor="pp-prob">Probabilidade</label>
            <select id="pp-prob" value={form.probabilidade} onChange={(e) => setForm({ ...form, probabilidade: e.target.value })}>
              {[0.1, 0.3, 0.5, 0.7, 0.9].map((p) => <option key={p} value={p}>{Math.round(p * 100)}%</option>)}
            </select>
          </div>
          <div className="campo">
            <label htmlFor="pp-val">Validade da proposta</label>
            <input id="pp-val" type="date" value={form.validade} onChange={(e) => setForm({ ...form, validade: e.target.value })} />
          </div>
        </div>
        <div className="form-linha">
          <div className="campo" style={{ flex: 1 }}>
            <label htmlFor="pp-escopo">Escopo</label>
            <textarea id="pp-escopo" rows={2} value={form.escopo}
              onChange={(e) => setForm({ ...form, escopo: e.target.value })}
              placeholder="O que está incluído…"
              style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit', fontSize: 13.5 }} />
          </div>
          <div className="campo" style={{ flex: 1 }}>
            <label htmlFor="pp-prem">Premissas</label>
            <textarea id="pp-prem" rows={2} value={form.premissas}
              onChange={(e) => setForm({ ...form, premissas: e.target.value })}
              placeholder="Condições assumidas…"
              style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit', fontSize: 13.5 }} />
          </div>
        </div>
        <div className="campo">
          <label htmlFor="pp-desc">Descrição</label>
          <textarea id="pp-desc" rows={2} value={form.descricao}
            onChange={(e) => setForm({ ...form, descricao: e.target.value })}
            style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit', fontSize: 14 }} />
        </div>
      </form>
    </Modal>
  )
}
