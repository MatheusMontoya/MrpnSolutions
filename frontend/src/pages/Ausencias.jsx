import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import FalhaAoCarregar from '../components/FalhaAoCarregar'
import Icone from '../components/Icone'
import Modal from '../components/Modal'
import { SkeletonPagina } from '../components/Skeleton'
import { fmtData } from '../format'
import { useSessao } from '../sessao'
import { confirmarE } from '../avisos'

const TIPOS = {
  ferias: 'Férias',
  folga: 'Folga',
  afastamento: 'Afastamento',
  treinamento: 'Treinamento',
}
const BADGE_STATUS = {
  pendente: ['badge-cinza', 'Aguardando aprovação'],
  aprovada: ['badge-verde', 'Aprovada'],
  recusada: ['badge-vermelho', 'Recusada'],
}
const IC_NOVA = ['M12 5v14', 'M5 12h14']

export default function Ausencias() {
  const { sessao } = useSessao()
  const ehConsultor = sessao?.perfil === 'consultor'

  const [ausencias, setAusencias] = useState(null)
  const [erro, setErro] = useState(null)
  const [modal, setModal] = useState(false)

  const carregar = useCallback(() => {
    const q = ehConsultor ? `?consultor_id=${sessao.consultorId}` : ''
    api.get(`/ausencias${q}`).then(setAusencias).catch((e) => setErro(e.message))
  }, [ehConsultor, sessao?.consultorId])

  useEffect(carregar, [carregar])

  if (erro) return <FalhaAoCarregar erro={erro} aoTentarDeNovo={carregar} />
  if (!ausencias) return <SkeletonPagina />

  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <h1>Ausências</h1>
          <div className="descricao">
            Férias, folgas e afastamentos — quando aprovadas, reduzem a capacidade da semana no mapa de utilização
          </div>
        </div>
        <button className="botao botao-primario" onClick={() => setModal(true)}>
          <Icone d={IC_NOVA} size={15} /> Solicitar ausência
        </button>
      </div>

      <div className="card">
        <div className="card-corpo" style={{ paddingTop: 10 }}>
          {ausencias.length === 0 ? (
            <div className="vazio-ensina">
              <Icone d={['M5 4h14a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z', 'M16 2v4', 'M8 2v4', 'M3 10h18']} size={28} strokeWidth={1.5} />
              <span className="titulo">Nenhuma ausência registrada</span>
              <span className="dica">Solicite férias, folga ou afastamento — o gestor aprova e a capacidade da equipe é ajustada automaticamente.</span>
            </div>
          ) : (
            <table className="tabela">
              <thead>
                <tr>
                  {!ehConsultor && <th>Consultor</th>}
                  <th>Tipo</th><th>Período</th><th>Motivo</th><th>Status</th><th></th>
                </tr>
              </thead>
              <tbody>
                {ausencias.map((a) => {
                  const [cls, rotulo] = BADGE_STATUS[a.status] || BADGE_STATUS.pendente
                  return (
                    <tr key={a.id}>
                      {!ehConsultor && <td>{a.consultor}</td>}
                      <td>{TIPOS[a.tipo] || a.tipo}</td>
                      <td className="mono">{fmtData(a.data_inicio)} – {fmtData(a.data_fim)}</td>
                      <td className="texto-2">{a.motivo || '—'}</td>
                      <td>
                        <span className={`badge ${cls}`}>{rotulo}</span>
                        {a.comentario_gestor && <div className="texto-3" style={{ fontSize: 11.5, marginTop: 2 }}>“{a.comentario_gestor}”</div>}
                      </td>
                      <td>
                        {a.status === 'pendente' && (
                          <button className="botao botao-fantasma botao-pequeno"
                            onClick={() => confirmarE(
                              `Cancelar o pedido de ${TIPOS[a.tipo] || a.tipo} de ${fmtData(a.data_inicio)} a ${fmtData(a.data_fim)}?`,
                              async () => { await api.del(`/ausencias/${a.id}`); carregar() },
                              { sucesso: 'Pedido cancelado.' },
                            )}>
                            Cancelar
                          </button>
                        )}
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
        <FormAusencia
          consultorId={ehConsultor ? sessao.consultorId : null}
          onFechar={() => setModal(false)}
          onCriada={() => { setModal(false); carregar() }}
        />
      )}
    </>
  )
}

function FormAusencia({ consultorId, onFechar, onCriada }) {
  const hoje = new Date().toISOString().slice(0, 10)
  const [consultores, setConsultores] = useState([])
  const [form, setForm] = useState({
    consultor_id: consultorId ?? '',
    tipo: 'ferias',
    data_inicio: hoje,
    data_fim: hoje,
    motivo: '',
  })
  const [erro, setErro] = useState(null)

  useEffect(() => {
    if (consultorId == null) {
      api.get('/consultores').then((cs) => {
        setConsultores(cs)
        setForm((f) => ({ ...f, consultor_id: f.consultor_id || cs[0]?.id || '' }))
      }).catch(() => {})
    }
  }, [consultorId])

  const salvar = async (e) => {
    e.preventDefault()
    setErro(null)
    try {
      await api.post('/ausencias', { ...form, consultor_id: Number(form.consultor_id) })
      onCriada()
    } catch (err) {
      setErro(err.message)
    }
  }

  return (
    <Modal titulo="Solicitar ausência" onFechar={onFechar}
      rodape={<>
        <button className="botao botao-fantasma" onClick={onFechar}>Cancelar</button>
        <button className="botao botao-primario" type="submit" form="form-ausencia">Solicitar</button>
      </>}>
      <form id="form-ausencia" onSubmit={salvar} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {erro && <div className="mensagem-erro">{erro}</div>}
        {consultorId == null && (
          <div className="campo">
            <label htmlFor="au-consultor">Consultor *</label>
            <select id="au-consultor" value={form.consultor_id} onChange={(e) => setForm({ ...form, consultor_id: e.target.value })}>
              {consultores.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
          </div>
        )}
        <div className="campo">
          <label htmlFor="au-tipo">Tipo *</label>
          <select id="au-tipo" value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
            {Object.entries(TIPOS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <div className="form-linha">
          <div className="campo">
            <label htmlFor="au-inicio">Início *</label>
            <input id="au-inicio" type="date" value={form.data_inicio}
              onChange={(e) => setForm({ ...form, data_inicio: e.target.value })} required />
          </div>
          <div className="campo">
            <label htmlFor="au-fim">Fim *</label>
            <input id="au-fim" type="date" value={form.data_fim} min={form.data_inicio}
              onChange={(e) => setForm({ ...form, data_fim: e.target.value })} required />
          </div>
        </div>
        <div className="campo">
          <label htmlFor="au-motivo">Motivo</label>
          <input id="au-motivo" value={form.motivo} onChange={(e) => setForm({ ...form, motivo: e.target.value })}
            placeholder="Ex.: férias programadas, compensação…" />
        </div>
      </form>
    </Modal>
  )
}
