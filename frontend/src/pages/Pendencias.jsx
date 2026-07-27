import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import BotaoExportar from '../components/BotaoExportar'
import Icone from '../components/Icone'
import Modal from '../components/Modal'
import { SkeletonPagina } from '../components/Skeleton'
import { fmtData } from '../format'

const IC_NOVA = ['M12 5v14', 'M5 12h14']
const IC_CHECK = ['M20 6 9 17l-5-5']
export const PRIORIDADES = { alta: ['prio-alta', 'Alta'], media: ['prio-media', 'Média'], baixa: ['prio-baixa', 'Baixa'] }
export const BADGE_STATUS_PENDENCIA = {
  aberta: ['badge-vermelho', 'Aberta'],
  em_andamento: ['badge-azul', 'Em andamento'],
  resolvida: ['badge-verde', 'Resolvida'],
}

export default function Pendencias() {
  const [pendencias, setPendencias] = useState(null)
  const [erro, setErro] = useState(null)
  const [filtro, setFiltro] = useState('abertas') // abertas | todas
  const [modal, setModal] = useState(false)

  const carregar = useCallback(() => {
    api.get('/pendencias').then(setPendencias).catch((e) => setErro(e.message))
  }, [])

  useEffect(carregar, [carregar])

  if (erro) return <div className="mensagem-erro">{erro}</div>
  if (!pendencias) return <SkeletonPagina />

  const visiveis = filtro === 'abertas' ? pendencias.filter((p) => p.status !== 'resolvida') : pendencias

  const resolver = async (p) => {
    await api.patch(`/pendencias/${p.id}`, { status: 'resolvida' })
    carregar()
  }
  const iniciar = async (p) => {
    await api.patch(`/pendencias/${p.id}`, { status: 'em_andamento' })
    carregar()
  }

  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <h1>Pendências</h1>
          <div className="descricao">Ocorrências dos projetos: registro, responsável e acompanhamento até a resolução</div>
        </div>
        <div className="linha-flex">
          <BotaoExportar recurso="pendencias" />
          <div className="linha-flex" style={{ gap: 4, border: '1px solid var(--borda-forte)', borderRadius: 'var(--raio-2)', padding: 3 }}>
            <button className={`botao botao-pequeno ${filtro === 'abertas' ? 'botao-primario' : 'botao-fantasma'}`} onClick={() => setFiltro('abertas')}>Em aberto</button>
            <button className={`botao botao-pequeno ${filtro === 'todas' ? 'botao-primario' : 'botao-fantasma'}`} onClick={() => setFiltro('todas')}>Todas</button>
          </div>
          <button className="botao botao-primario" onClick={() => setModal(true)}>
            <Icone d={IC_NOVA} size={15} /> Nova pendência
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-corpo" style={{ paddingTop: 10 }}>
          {visiveis.length === 0 ? (
            <div className="vazio-ensina">
              <Icone d={IC_CHECK} size={28} strokeWidth={1.5} />
              <span className="titulo">{filtro === 'abertas' ? 'Nenhuma pendência em aberto' : 'Nenhuma pendência registrada'}</span>
              <span className="dica">Registre ocorrências dos projetos (bloqueios, riscos materializados, ações) e acompanhe até a resolução.</span>
            </div>
          ) : (
            <table className="tabela">
              <thead>
                <tr>
                  <th>Pendência</th><th>Projeto</th><th>Fase</th><th>Responsável</th>
                  <th>Prioridade</th><th>Status</th><th>Criada</th><th></th>
                </tr>
              </thead>
              <tbody>
                {visiveis.map((p) => {
                  const [clsP, rotP] = PRIORIDADES[p.prioridade] || PRIORIDADES.media
                  const [clsS, rotS] = BADGE_STATUS_PENDENCIA[p.status] || BADGE_STATUS_PENDENCIA.aberta
                  return (
                    <tr key={p.id}>
                      <td>
                        <strong style={{ fontWeight: 600 }}>{p.titulo}</strong>
                        {p.descricao && <div className="texto-3" style={{ fontSize: 12 }}>{p.descricao}</div>}
                      </td>
                      <td><Link className="link" to={`/projetos/${p.projeto_id}`}>{p.projeto}</Link></td>
                      <td className="texto-2">{p.fase || '—'}</td>
                      <td className="texto-2">{p.responsavel || '—'}</td>
                      <td><span className={clsP} style={{ fontWeight: 600, fontSize: 12.5 }}>● {rotP}</span></td>
                      <td><span className={`badge ${clsS}`}>{rotS}</span></td>
                      <td className="mono texto-3" style={{ fontSize: 12 }}>{fmtData(p.criada_em)}</td>
                      <td>
                        <div className="linha-flex" style={{ gap: 6, justifyContent: 'flex-end' }}>
                          {p.status === 'aberta' && (
                            <button className="botao botao-fantasma botao-pequeno" onClick={() => iniciar(p)}>Iniciar</button>
                          )}
                          {p.status !== 'resolvida' && (
                            <button className="botao botao-secundario botao-pequeno" onClick={() => resolver(p)}>
                              <Icone d={IC_CHECK} size={12} /> Resolver
                            </button>
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

      {modal && (
        <FormPendencia onFechar={() => setModal(false)} onCriada={() => { setModal(false); carregar() }} />
      )}
    </>
  )
}

export function FormPendencia({ projetoId, fases, onFechar, onCriada }) {
  const [projetos, setProjetos] = useState([])
  const [consultores, setConsultores] = useState([])
  const [form, setForm] = useState({
    projeto_id: projetoId ?? '',
    fase_id: '',
    titulo: '',
    descricao: '',
    responsavel_id: '',
    prioridade: 'media',
  })
  const [erro, setErro] = useState(null)

  useEffect(() => {
    if (projetoId == null) {
      api.get('/projetos').then((ps) => {
        setProjetos(ps)
        setForm((f) => ({ ...f, projeto_id: f.projeto_id || ps[0]?.id || '' }))
      }).catch(() => {})
    }
    api.get('/consultores').then(setConsultores).catch(() => {})
  }, [projetoId])

  const salvar = async (e) => {
    e.preventDefault()
    setErro(null)
    try {
      await api.post('/pendencias', {
        projeto_id: Number(form.projeto_id),
        fase_id: form.fase_id ? Number(form.fase_id) : null,
        titulo: form.titulo,
        descricao: form.descricao,
        responsavel_id: form.responsavel_id ? Number(form.responsavel_id) : null,
        prioridade: form.prioridade,
      })
      onCriada()
    } catch (err) {
      setErro(err.message)
    }
  }

  return (
    <Modal titulo="Nova pendência" onFechar={onFechar}
      rodape={<>
        <button className="botao botao-fantasma" onClick={onFechar}>Cancelar</button>
        <button className="botao botao-primario" type="submit" form="form-pendencia" disabled={!form.titulo || !form.projeto_id}>
          Registrar
        </button>
      </>}>
      <form id="form-pendencia" onSubmit={salvar} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {erro && <div className="mensagem-erro">{erro}</div>}
        <div className="campo">
          <label htmlFor="pd-titulo">Título *</label>
          <input id="pd-titulo" value={form.titulo} autoFocus required
            onChange={(e) => setForm({ ...form, titulo: e.target.value })}
            placeholder="Ex.: ambiente QAS instável para o teste integrado" />
        </div>
        <div className="form-linha">
          {projetoId == null && (
            <div className="campo" style={{ flex: 1 }}>
              <label htmlFor="pd-projeto">Projeto *</label>
              <select id="pd-projeto" value={form.projeto_id} onChange={(e) => setForm({ ...form, projeto_id: e.target.value, fase_id: '' })}>
                {projetos.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
              </select>
            </div>
          )}
          {fases && (
            <div className="campo" style={{ flex: 1 }}>
              <label htmlFor="pd-fase">Fase</label>
              <select id="pd-fase" value={form.fase_id} onChange={(e) => setForm({ ...form, fase_id: e.target.value })}>
                <option value="">— sem fase específica —</option>
                {fases.map((f) => <option key={f.id} value={f.id}>{f.nome}</option>)}
              </select>
            </div>
          )}
          <div className="campo">
            <label htmlFor="pd-prio">Prioridade</label>
            <select id="pd-prio" value={form.prioridade} onChange={(e) => setForm({ ...form, prioridade: e.target.value })}>
              <option value="alta">Alta</option>
              <option value="media">Média</option>
              <option value="baixa">Baixa</option>
            </select>
          </div>
        </div>
        <div className="campo">
          <label htmlFor="pd-resp">Responsável</label>
          <select id="pd-resp" value={form.responsavel_id} onChange={(e) => setForm({ ...form, responsavel_id: e.target.value })}>
            <option value="">— definir depois —</option>
            {consultores.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
          </select>
        </div>
        <div className="campo">
          <label htmlFor="pd-desc">Descrição</label>
          <textarea id="pd-desc" rows={3} value={form.descricao}
            onChange={(e) => setForm({ ...form, descricao: e.target.value })}
            style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit', fontSize: 14 }} />
        </div>
      </form>
    </Modal>
  )
}
