import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import FalhaAoCarregar from '../components/FalhaAoCarregar'
import Icone from '../components/Icone'
import Modal from '../components/Modal'
import { SkeletonPagina } from '../components/Skeleton'
import { fmtBRL, fmtData, iniciais } from '../format'

const IC_NOVO = ['M12 5v14', 'M5 12h14']
const BADGE = {
  vigente: ['badge-verde', 'Vigente'],
  encerrado: ['badge-cinza', 'Encerrado'],
  cancelado: ['badge-vermelho', 'Cancelado'],
}

export default function Contratos() {
  const [dados, setDados] = useState(null)
  const [erro, setErro] = useState(null)
  const [modal, setModal] = useState(false)

  const carregar = useCallback(() => {
    api.get('/contratos').then(setDados).catch((e) => setErro(e.message))
  }, [])
  useEffect(carregar, [carregar])

  if (erro) return <FalhaAoCarregar erro={erro} aoTentarDeNovo={carregar} />
  if (!dados) return <SkeletonPagina />

  const mudarStatus = async (c, status) => {
    await api.patch(`/contratos/${c.id}`, { status })
    carregar()
  }

  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <h1>Contratos</h1>
          <div className="descricao">Vigência e situação — contratos a até 60 dias do fim entram no radar de renovação</div>
        </div>
        <button className="botao botao-primario" onClick={() => setModal(true)}>
          <Icone d={IC_NOVO} size={15} /> Novo contrato
        </button>
      </div>

      <div className="grid-kpi" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
        <div className="card kpi">
          <div className="rotulo">Contratos</div>
          <div className="valor">{dados.contratos.length}</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">A renovar (60 dias)</div>
          <div className="valor" style={{ color: dados.a_renovar ? 'var(--laranja)' : 'var(--texto)' }}>{dados.a_renovar}</div>
          <div className="detalhe">agir antes do vencimento</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Vencidos sem decisão</div>
          <div className="valor" style={{ color: dados.vencidos ? 'var(--vermelho)' : 'var(--texto)' }}>{dados.vencidos}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-corpo" style={{ paddingTop: 10 }}>
          {dados.contratos.length === 0 ? (
            <div className="vazio-ensina">
              <Icone d={['M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z', 'M14 2v6h6', 'M9 15l2 2 4-4']} size={28} strokeWidth={1.5} />
              <span className="titulo">Nenhum contrato cadastrado</span>
              <span className="dica">Registre a vigência dos contratos e o sistema avisa quando estiverem a 60 dias do fim.</span>
            </div>
          ) : (
            <table className="tabela">
              <thead>
                <tr>
                  <th>Contrato</th><th>Cliente</th><th>Vigência</th>
                  <th className="num">Valor</th><th>Situação</th><th></th>
                </tr>
              </thead>
              <tbody>
                {dados.contratos.map((c) => {
                  const [cls, rotulo] = BADGE[c.status] || BADGE.vigente
                  return (
                    <tr key={c.id}>
                      <td>
                        <strong style={{ fontWeight: 600 }}>{c.nome}</strong>
                        {c.observacoes && <div className="texto-3" style={{ fontSize: 12 }}>{c.observacoes}</div>}
                      </td>
                      <td>
                        <div className="linha-flex" style={{ gap: 6 }}>
                          <span className="avatar-consultor" style={{ width: 22, height: 22, fontSize: 10 }}>{iniciais(c.cliente)}</span>
                          <span className="texto-2">{c.cliente}</span>
                        </div>
                      </td>
                      <td className="mono" style={{ fontSize: 12.5 }}>
                        {fmtData(c.data_inicio)} – {fmtData(c.data_fim)}
                        {c.status === 'vigente' && !c.vencido && (
                          <div className="texto-3" style={{ fontSize: 11 }}>{c.dias_para_fim} dias restantes</div>
                        )}
                      </td>
                      <td className="num">{fmtBRL(c.valor)}</td>
                      <td>
                        <span className={`badge ${cls}`}>{rotulo}</span>
                        {c.a_renovar && <span className="badge badge-laranja" style={{ marginLeft: 6 }}>a renovar</span>}
                        {c.vencido && <span className="badge badge-vermelho" style={{ marginLeft: 6 }}>vencido</span>}
                      </td>
                      <td>
                        {c.status === 'vigente' && (
                          <div className="linha-flex" style={{ gap: 6, justifyContent: 'flex-end' }}>
                            <button className="botao botao-fantasma botao-pequeno" onClick={() => mudarStatus(c, 'encerrado')}>Encerrar</button>
                          </div>
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

      {modal && <FormContrato onFechar={() => setModal(false)} onCriado={() => { setModal(false); carregar() }} />}
    </>
  )
}

function FormContrato({ onFechar, onCriado }) {
  const hoje = new Date().toISOString().slice(0, 10)
  const [clientes, setClientes] = useState([])
  const [form, setForm] = useState({ cliente_id: '', nome: '', data_inicio: hoje, data_fim: hoje, valor: '', observacoes: '' })
  const [erro, setErro] = useState(null)

  useEffect(() => {
    api.get('/clientes').then((cs) => {
      setClientes(cs)
      setForm((f) => ({ ...f, cliente_id: f.cliente_id || cs[0]?.id || '' }))
    }).catch(() => {})
  }, [])

  const salvar = async (e) => {
    e.preventDefault()
    setErro(null)
    try {
      await api.post('/contratos', {
        cliente_id: Number(form.cliente_id),
        nome: form.nome,
        data_inicio: form.data_inicio,
        data_fim: form.data_fim,
        valor: Number(form.valor || 0),
        observacoes: form.observacoes,
      })
      onCriado()
    } catch (err) { setErro(err.message) }
  }

  return (
    <Modal titulo="Novo contrato" onFechar={onFechar}
      rodape={<>
        <button className="botao botao-fantasma" onClick={onFechar}>Cancelar</button>
        <button className="botao botao-primario" type="submit" form="form-contrato" disabled={!form.nome || !form.cliente_id}>Salvar</button>
      </>}>
      <form id="form-contrato" onSubmit={salvar} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {erro && <div className="mensagem-erro">{erro}</div>}
        <div className="campo">
          <label htmlFor="ct-nome">Nome do contrato *</label>
          <input id="ct-nome" value={form.nome} autoFocus required onChange={(e) => setForm({ ...form, nome: e.target.value })} />
        </div>
        <div className="form-linha">
          <div className="campo" style={{ flex: 1 }}>
            <label htmlFor="ct-cliente">Cliente *</label>
            <select id="ct-cliente" value={form.cliente_id} onChange={(e) => setForm({ ...form, cliente_id: e.target.value })}>
              {clientes.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
          </div>
          <div className="campo">
            <label htmlFor="ct-valor">Valor (R$)</label>
            <input id="ct-valor" type="number" min="0" step="1000" value={form.valor}
              onChange={(e) => setForm({ ...form, valor: e.target.value })} />
          </div>
        </div>
        <div className="form-linha">
          <div className="campo">
            <label htmlFor="ct-ini">Início da vigência *</label>
            <input id="ct-ini" type="date" value={form.data_inicio} onChange={(e) => setForm({ ...form, data_inicio: e.target.value })} required />
          </div>
          <div className="campo">
            <label htmlFor="ct-fim">Fim da vigência *</label>
            <input id="ct-fim" type="date" value={form.data_fim} min={form.data_inicio}
              onChange={(e) => setForm({ ...form, data_fim: e.target.value })} required />
          </div>
        </div>
        <div className="campo">
          <label htmlFor="ct-obs">Observações</label>
          <input id="ct-obs" value={form.observacoes} onChange={(e) => setForm({ ...form, observacoes: e.target.value })} />
        </div>
      </form>
    </Modal>
  )
}
