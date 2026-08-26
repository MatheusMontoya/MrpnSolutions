import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api'
import FalhaAoCarregar from '../components/FalhaAoCarregar'
import BotaoExportar from '../components/BotaoExportar'
import Icone from '../components/Icone'
import Modal from '../components/Modal'
import { SkeletonPagina } from '../components/Skeleton'
import { fmtBRLExato, fmtData } from '../format'
import { useSessao } from '../sessao'
import { confirmarE } from '../avisos'

const TIPOS = {
  deslocamento: 'Deslocamento',
  alimentacao: 'Alimentação',
  hospedagem: 'Hospedagem',
  quilometragem: 'Quilometragem',
  outros: 'Outros',
}
const BADGE_STATUS = {
  pendente: ['badge-cinza', 'Pendente'],
  aprovada: ['badge-azul', 'Aprovada'],
  recusada: ['badge-vermelho', 'Recusada'],
  reembolsada: ['badge-verde', 'Reembolsada'],
}
const IC_NOVA = ['M12 5v14', 'M5 12h14']

export default function Despesas() {
  const { sessao } = useSessao()
  const ehConsultor = sessao?.perfil === 'consultor'

  const [despesas, setDespesas] = useState(null)
  const [projetos, setProjetos] = useState([])
  const [taxaKm, setTaxaKm] = useState(1.2)
  const [erro, setErro] = useState(null)
  const [modal, setModal] = useState(false)
  const [params, setParams] = useSearchParams()
  // "+ Novo" da sidebar chega como ?novo=1 e ja abre o formulario
  useEffect(() => {
    if (params.get('novo')) {
      setModal(true)
      params.delete('novo')
      setParams(params, { replace: true })
    }
  }, [params, setParams])


  const carregar = useCallback(() => {
    const q = ehConsultor ? `?consultor_id=${sessao.consultorId}` : ''
    api.get(`/despesas${q}`).then(setDespesas).catch((e) => setErro(e.message))
  }, [ehConsultor, sessao?.consultorId])

  useEffect(() => {
    carregar()
    api.get('/projetos').then(setProjetos).catch(() => {})
    api.get('/configuracoes').then((c) => setTaxaKm(c.taxa_km)).catch(() => {})
  }, [carregar])

  if (erro) return <FalhaAoCarregar erro={erro} aoTentarDeNovo={carregar} />
  if (!despesas) return <SkeletonPagina />

  const totalPendente = despesas.filter((d) => d.status === 'pendente').reduce((s, d) => s + d.valor, 0)
  const totalAReceber = despesas.filter((d) => d.status === 'aprovada').reduce((s, d) => s + d.valor, 0)
  const totalReembolsado = despesas.filter((d) => d.status === 'reembolsada').reduce((s, d) => s + d.valor, 0)

  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <h1>Despesas</h1>
          <div className="descricao">
            {ehConsultor
              ? 'Suas despesas de projeto — reembolso após aprovação do gestor'
              : 'Despesas de projeto de toda a equipe (decisões na fila de Aprovações)'}
          </div>
        </div>
        <div className="linha-flex">
          {!ehConsultor && <BotaoExportar recurso="despesas" />}
          <button className="botao botao-primario" onClick={() => setModal(true)}>
            <Icone d={IC_NOVA} size={15} /> Nova despesa
          </button>
        </div>
      </div>

      <div className="grid-kpi" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
        <div className="card kpi">
          <div className="rotulo">Aguardando aprovação</div>
          <div className="valor">{fmtBRLExato(totalPendente)}</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Aprovadas — a reembolsar</div>
          <div className="valor" style={{ color: 'var(--azul)' }}>{fmtBRLExato(totalAReceber)}</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Reembolsadas</div>
          <div className="valor" style={{ color: 'var(--verde)' }}>{fmtBRLExato(totalReembolsado)}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-corpo" style={{ paddingTop: 10 }}>
          {despesas.length === 0 ? (
            <div className="vazio-ensina">
              <Icone d={['M2 5h20a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z', 'M1 10h22']} size={28} strokeWidth={1.5} />
              <span className="titulo">Nenhuma despesa lançada</span>
              <span className="dica">Registre deslocamentos, alimentação, hospedagem ou km rodado por projeto — após aprovado, o valor entra na fila de reembolso.</span>
            </div>
          ) : (
            <table className="tabela">
              <thead>
                <tr>
                  <th>Data</th>
                  {!ehConsultor && <th>Consultor</th>}
                  <th>Projeto</th><th>Tipo</th><th>Descrição</th>
                  <th className="num">Valor</th><th>Status</th><th></th>
                </tr>
              </thead>
              <tbody>
                {despesas.map((d) => {
                  const [cls, rotulo] = BADGE_STATUS[d.status] || BADGE_STATUS.pendente
                  return (
                    <tr key={d.id}>
                      <td className="mono">{fmtData(d.data)}</td>
                      {!ehConsultor && <td>{d.consultor}</td>}
                      <td className="texto-2">{d.projeto}</td>
                      <td>
                        {TIPOS[d.tipo] || d.tipo}
                        {d.km ? <span className="texto-3 mono" style={{ fontSize: 11.5 }}> · {d.km} km</span> : null}
                      </td>
                      <td className="texto-2">{d.descricao || '—'}</td>
                      <td className="num">{fmtBRLExato(d.valor)}</td>
                      <td>
                        <span className={`badge ${cls}`}>{rotulo}</span>
                        {d.comentario_gestor && <div className="texto-3" style={{ fontSize: 11.5, marginTop: 2 }}>“{d.comentario_gestor}”</div>}
                      </td>
                      <td>
                        {d.status === 'pendente' && (
                          <button className="botao botao-fantasma botao-pequeno"
                            onClick={() => confirmarE(
                              `Remover a despesa de ${fmtBRLExato(d.valor)}? Não há como desfazer.`,
                              async () => { await api.del(`/despesas/${d.id}`); carregar() },
                              { sucesso: 'Despesa removida.' },
                            )}>
                            Remover
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
        <FormDespesa
          projetos={projetos}
          taxaKm={taxaKm}
          consultorId={ehConsultor ? sessao.consultorId : null}
          onFechar={() => setModal(false)}
          onCriada={() => { setModal(false); carregar() }}
        />
      )}
    </>
  )
}

function FormDespesa({ projetos, taxaKm, consultorId, onFechar, onCriada }) {
  const hoje = new Date().toISOString().slice(0, 10)
  const [consultores, setConsultores] = useState([])
  const [form, setForm] = useState({
    consultor_id: consultorId ?? '',
    projeto_id: projetos[0]?.id ?? '',
    data: hoje,
    tipo: 'deslocamento',
    descricao: '',
    valor: '',
    km: '',
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

  const ehKm = form.tipo === 'quilometragem'
  const valorKm = ehKm && form.km ? Number(form.km) * taxaKm : 0

  const salvar = async (e) => {
    e.preventDefault()
    setErro(null)
    try {
      await api.post('/despesas', {
        consultor_id: Number(form.consultor_id),
        projeto_id: Number(form.projeto_id),
        data: form.data,
        tipo: form.tipo,
        descricao: form.descricao,
        valor: ehKm ? null : Number(form.valor),
        km: ehKm ? Number(form.km) : null,
      })
      onCriada()
    } catch (err) {
      setErro(err.message)
    }
  }

  return (
    <Modal titulo="Nova despesa" onFechar={onFechar}
      rodape={<>
        <button className="botao botao-fantasma" onClick={onFechar}>Cancelar</button>
        <button className="botao botao-primario" type="submit" form="form-despesa"
          disabled={!form.projeto_id || (ehKm ? !form.km : !form.valor)}>
          Lançar despesa
        </button>
      </>}>
      <form id="form-despesa" onSubmit={salvar} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {erro && <div className="mensagem-erro">{erro}</div>}
        {consultorId == null && (
          <div className="campo">
            <label htmlFor="dp-consultor">Consultor *</label>
            <select id="dp-consultor" value={form.consultor_id} onChange={(e) => setForm({ ...form, consultor_id: e.target.value })}>
              {consultores.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
          </div>
        )}
        <div className="form-linha">
          <div className="campo" style={{ flex: 1 }}>
            <label htmlFor="dp-projeto">Projeto *</label>
            <select id="dp-projeto" value={form.projeto_id} onChange={(e) => setForm({ ...form, projeto_id: e.target.value })}>
              {projetos.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
            </select>
          </div>
          <div className="campo">
            <label htmlFor="dp-data">Data *</label>
            <input id="dp-data" type="date" value={form.data} onChange={(e) => setForm({ ...form, data: e.target.value })} required />
          </div>
        </div>
        <div className="form-linha">
          <div className="campo" style={{ flex: 1 }}>
            <label htmlFor="dp-tipo">Tipo *</label>
            <select id="dp-tipo" value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
              {Object.entries(TIPOS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          {ehKm ? (
            <div className="campo">
              <label htmlFor="dp-km">Km rodados *</label>
              <input id="dp-km" type="number" min="1" step="1" value={form.km}
                onChange={(e) => setForm({ ...form, km: e.target.value })} required />
              <span className="ajuda">
                {form.km ? `${form.km} km × ${fmtBRLExato(taxaKm)}/km = ${fmtBRLExato(valorKm)}` : `Taxa vigente: ${fmtBRLExato(taxaKm)}/km`}
              </span>
            </div>
          ) : (
            <div className="campo">
              <label htmlFor="dp-valor">Valor (R$) *</label>
              <input id="dp-valor" type="number" min="0.01" step="0.01" value={form.valor}
                onChange={(e) => setForm({ ...form, valor: e.target.value })} required />
            </div>
          )}
        </div>
        <div className="campo">
          <label htmlFor="dp-desc">Descrição</label>
          <input id="dp-desc" value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })}
            placeholder="Ex.: visita ao cliente, hotel do workshop…" />
        </div>
      </form>
    </Modal>
  )
}
