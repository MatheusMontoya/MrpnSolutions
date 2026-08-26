import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import FalhaAoCarregar from '../components/FalhaAoCarregar'
import Modal from '../components/Modal'
import Icone from '../components/Icone'
import { SkeletonPagina } from '../components/Skeleton'
import EstadoVazio from '../components/EstadoVazio'
import { STATUS_PROJETO, fmtData, corFase, codigoProjeto } from '../format'

const badgeStatus = { ativo: 'badge-verde', pausado: 'badge-laranja', encerrado: 'badge-cinza' }
const POR_PAGINA = 8
const ICONE_ORG = ['M6 3v12', 'M18 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6z', 'M6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6z', 'M15 6a9 9 0 0 1-9 9']

const ICONE_BUSCA = ['M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0z', 'M21 21l-4.35-4.35']
const ICONE_FILTRO = ['M22 3H2l8 9.46V19l4 2v-8.54L22 3z']
const ICONE_ESQ = ['M15 18l-6-6 6-6']
const ICONE_DIR = ['M9 18l6-6-6-6']

// Barrinhas das 6 fases SAP Activate: concluídas cheias, atual meio-cheia, futuras vazias.
function TrilhaSegmentos({ fases, faseAtual }) {
  const atualIdx = fases.findIndex((f) => f.nome === faseAtual)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4, minWidth: 150 }}>
      {fases.map((f, i) => {
        const concluida = atualIdx === -1 ? true : i < atualIdx
        const atual = i === atualIdx
        return (
          <span key={f.id} title={f.nome} style={{
            flex: 1, height: 6, borderRadius: 99, display: 'block', overflow: 'hidden', position: 'relative',
            background: concluida ? 'var(--azul)' : atual ? 'var(--azul-claro)' : 'var(--borda)',
          }}>
            {atual && <span style={{ position: 'absolute', inset: 0, width: '50%', background: 'var(--azul)' }} />}
          </span>
        )
      })}
    </div>
  )
}

export default function Projetos() {
  const [projetos, setProjetos] = useState(null)
  const [clientes, setClientes] = useState([])
  const [erro, setErro] = useState(null)
  const [modalProjeto, setModalProjeto] = useState(false)
  const [modalCliente, setModalCliente] = useState(false)
  const [busca, setBusca] = useState('')
  const [status, setStatus] = useState('todos')
  const [pagina, setPagina] = useState(1)
  const [params, setParams] = useSearchParams()

  // "+ Novo → Novo projeto" (sidebar) chega como ?novo=1 e já abre o formulário
  useEffect(() => {
    if (params.get('novo')) {
      setModalProjeto(true)
      params.delete('novo')
      setParams(params, { replace: true })
    }
  }, [params, setParams])

  const carregar = () => {
    api.get('/projetos').then(setProjetos).catch((e) => setErro(e.message))
    api.get('/clientes').then(setClientes).catch(() => {})
  }
  useEffect(carregar, [])

  const filtrados = useMemo(() => {
    if (!projetos) return []
    const q = busca.trim().toLowerCase()
    return projetos.filter((p) => {
      if (status !== 'todos' && p.status !== status) return false
      if (!q) return true
      return p.nome.toLowerCase().includes(q) || (p.cliente || '').toLowerCase().includes(q)
    })
  }, [projetos, busca, status])

  // contadores por status para os filtros da barra de ferramentas
  const contagens = useMemo(() => {
    const base = { todos: projetos?.length ?? 0, ativo: 0, pausado: 0, encerrado: 0 }
    for (const p of projetos ?? []) base[p.status] = (base[p.status] ?? 0) + 1
    return base
  }, [projetos])

  const totalPaginas = Math.max(1, Math.ceil(filtrados.length / POR_PAGINA))
  const paginaAtual = Math.min(pagina, totalPaginas)
  const inicio = (paginaAtual - 1) * POR_PAGINA
  const visiveis = filtrados.slice(inicio, inicio + POR_PAGINA)

  if (erro) return <FalhaAoCarregar erro={erro} aoTentarDeNovo={carregar} />
  if (!projetos) return <SkeletonPagina />

  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <h1>Projetos</h1>
          <div className="descricao">Todo projeto nasce com as 6 fases SAP Activate geradas automaticamente</div>
        </div>
        <div className="linha-flex">
          <button className="botao botao-secundario" onClick={() => setModalCliente(true)}>Novo cliente</button>
          <button className="botao botao-primario" onClick={() => setModalProjeto(true)}>Novo projeto</button>
        </div>
      </div>

      {projetos.length === 0 ? (
        <EstadoVazio
          icone={ICONE_ORG}
          titulo="Nenhum projeto cadastrado"
          descricao="Inicie seu primeiro projeto estruturado. O sistema irá gerar automaticamente as 6 fases do SAP Activate (Discover, Prepare, Explore, Realize, Deploy, Run) para controle de alocação."
          acao={<button className="botao botao-primario" onClick={() => setModalProjeto(true)}>+ Criar primeiro projeto</button>}
        />
      ) : (
      <>
      {/* barra de ferramentas: busca + filtros com contagem (padrão Productive) */}
      <div className="toolbar">
        <div className="busca-global" style={{ maxWidth: 300 }}>
          <span className="busca-icone" aria-hidden="true"><Icone d={ICONE_BUSCA} size={16} /></span>
          <input
            type="search"
            value={busca}
            onChange={(e) => { setBusca(e.target.value); setPagina(1) }}
            placeholder="Buscar projeto ou cliente…"
            aria-label="Buscar projeto ou cliente"
          />
        </div>
        <span className="separador" aria-hidden="true" />
        {[['todos', 'Todos'], ['ativo', 'Ativos'], ['pausado', 'Pausados'], ['encerrado', 'Encerrados']].map(([valor, rotulo]) => (
          <button
            key={valor}
            type="button"
            className={`toolbar-chip${status === valor ? ' ativo' : ''}`}
            aria-pressed={status === valor}
            onClick={() => { setStatus(valor); setPagina(1) }}
          >
            {rotulo}
            <span className="contagem">{contagens[valor] ?? 0}</span>
          </button>
        ))}
        <span className="espacador" />
        <span className="texto-3" style={{ fontSize: 12.5 }}>
          {filtrados.length} de {projetos.length}
        </span>
      </div>

      <div className="card">
        <div style={{ overflowX: 'auto' }}>
          <table className="tabela">
            <thead>
              <tr>
                <th>Projeto</th><th>Cliente</th><th>Início</th><th>Status</th><th>Fase atual</th><th>Fases SAP Activate</th>
              </tr>
            </thead>
            <tbody>
              {visiveis.map((p) => (
                <tr key={p.id}>
                  <td>
                    <Link className="link" to={`/projetos/${p.id}`} style={{ fontWeight: 600 }}>{p.nome}</Link>
                    <div className="texto-3 mono" style={{ fontSize: 11.5, marginTop: 2 }}>
                      ID: {codigoProjeto(p.id, p.data_inicio)}
                    </div>
                  </td>
                  <td className="texto-2">{p.cliente}</td>
                  <td className="mono">{fmtData(p.data_inicio)}</td>
                  <td>
                    <span className={`badge ${badgeStatus[p.status]}`}>
                      <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'currentColor' }} />
                      {STATUS_PROJETO[p.status]}
                    </span>
                  </td>
                  <td>{p.fase_atual && <span className={`badge ${corFase(p.fase_atual)}`}>{p.fase_atual}</span>}</td>
                  <td><TrilhaSegmentos fases={p.fases} faseAtual={p.fase_atual} /></td>
                </tr>
              ))}
              {visiveis.length === 0 && (
                <tr><td colSpan={6} className="vazio">Nenhum projeto encontrado para “{busca}”.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* rodapé: contagem + paginação client-side */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '12px 20px', borderTop: '1px solid var(--borda)',
        }}>
          <span className="texto-3" style={{ fontSize: 12 }}>
            Mostrando {filtrados.length ? inicio + 1 : 0} a {inicio + visiveis.length} de {filtrados.length} projetos
          </span>
          <div style={{ display: 'flex', gap: 4 }}>
            <button className="icone-botao" type="button" title="Página anterior"
              disabled={paginaAtual <= 1} onClick={() => setPagina(paginaAtual - 1)}
              style={{ opacity: paginaAtual <= 1 ? 0.4 : 1 }}>
              <Icone d={ICONE_ESQ} size={18} />
            </button>
            <button className="icone-botao" type="button" title="Próxima página"
              disabled={paginaAtual >= totalPaginas} onClick={() => setPagina(paginaAtual + 1)}
              style={{ opacity: paginaAtual >= totalPaginas ? 0.4 : 1 }}>
              <Icone d={ICONE_DIR} size={18} />
            </button>
          </div>
        </div>
      </div>
      </>
      )}

      {modalProjeto && (
        <FormNovoProjeto
          clientes={clientes}
          onFechar={() => setModalProjeto(false)}
          onCriado={() => { setModalProjeto(false); carregar() }}
        />
      )}
      {modalCliente && (
        <FormNovoCliente
          onFechar={() => setModalCliente(false)}
          onCriado={() => { setModalCliente(false); carregar() }}
        />
      )}
    </>
  )
}

function FormNovoProjeto({ clientes, onFechar, onCriado }) {
  const hoje = new Date().toISOString().slice(0, 10)
  const [form, setForm] = useState({ nome: '', cliente_id: clientes[0]?.id ?? '', data_inicio: hoje, modelo_id: '' })
  const [modelos, setModelos] = useState([])
  const [erro, setErro] = useState(null)
  const [salvando, setSalvando] = useState(false)

  useEffect(() => {
    api.get('/modelos').then((ms) => {
      setModelos(ms)
      const padrao = ms.find((m) => m.padrao)
      if (padrao) setForm((f) => ({ ...f, modelo_id: String(padrao.id) }))
    }).catch(() => {})
  }, [])

  const salvar = async (e) => {
    e.preventDefault()
    setSalvando(true)
    setErro(null)
    try {
      await api.post('/projetos', {
        ...form,
        cliente_id: Number(form.cliente_id),
        modelo_id: form.modelo_id ? Number(form.modelo_id) : null,
      })
      onCriado()
    } catch (err) {
      setErro(err.message)
      setSalvando(false)
    }
  }

  return (
    <Modal titulo="Novo projeto" onFechar={onFechar}
      rodape={<>
        <button className="botao botao-fantasma" onClick={onFechar}>Cancelar</button>
        <button className="botao botao-primario" type="submit" form="form-projeto" disabled={salvando || !form.nome || !form.cliente_id}>
          {salvando ? 'Criando…' : 'Criar projeto'}
        </button>
      </>}>
      <form id="form-projeto" onSubmit={salvar} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {erro && <div className="mensagem-erro">{erro}</div>}
        <div className="campo">
          <label htmlFor="np-nome">Nome do projeto *</label>
          <input id="np-nome" value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} autoFocus required />
        </div>
        <div className="campo">
          <label htmlFor="np-cliente">Cliente *</label>
          <select id="np-cliente" value={form.cliente_id} onChange={(e) => setForm({ ...form, cliente_id: e.target.value })} required>
            {clientes.length === 0 && <option value="">— cadastre um cliente antes —</option>}
            {clientes.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
          </select>
        </div>
        <div className="campo">
          <label htmlFor="np-inicio">Data de início *</label>
          <input id="np-inicio" type="date" value={form.data_inicio} onChange={(e) => setForm({ ...form, data_inicio: e.target.value })} required />
          <span className="ajuda">As 6 fases Activate (Discover → Run) serão geradas automaticamente a partir desta data, com durações padrão editáveis.</span>
        </div>
        {modelos.length > 0 && (
          <div className="campo">
            <label htmlFor="np-modelo">Modelo de projeto</label>
            <select id="np-modelo" value={form.modelo_id} onChange={(e) => setForm({ ...form, modelo_id: e.target.value })}>
              {modelos.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.nome} · {m.total_atividades} entregas / {m.total_gates} itens de gate
                </option>
              ))}
            </select>
            <span className="ajuda">Define as entregas e o Quality Gate de cada fase. Gerencie os modelos em Configurações.</span>
          </div>
        )}
      </form>
    </Modal>
  )
}

function FormNovoCliente({ onFechar, onCriado }) {
  const [form, setForm] = useState({ nome: '', contato: '' })
  const [erro, setErro] = useState(null)

  const salvar = async (e) => {
    e.preventDefault()
    try {
      await api.post('/clientes', form)
      onCriado()
    } catch (err) {
      setErro(err.message)
    }
  }

  return (
    <Modal titulo="Novo cliente" onFechar={onFechar}
      rodape={<>
        <button className="botao botao-fantasma" onClick={onFechar}>Cancelar</button>
        <button className="botao botao-primario" type="submit" form="form-cliente" disabled={!form.nome}>Salvar</button>
      </>}>
      <form id="form-cliente" onSubmit={salvar} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {erro && <div className="mensagem-erro">{erro}</div>}
        <div className="campo">
          <label htmlFor="nc-nome">Nome *</label>
          <input id="nc-nome" value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} autoFocus required />
        </div>
        <div className="campo">
          <label htmlFor="nc-contato">Contato</label>
          <input id="nc-contato" value={form.contato} onChange={(e) => setForm({ ...form, contato: e.target.value })} placeholder="nome — e-mail" />
        </div>
      </form>
    </Modal>
  )
}
