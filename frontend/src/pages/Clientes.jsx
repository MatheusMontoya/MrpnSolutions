import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import Icone from '../components/Icone'
import Modal from '../components/Modal'
import { SkeletonPagina } from '../components/Skeleton'
import { fmtBRL, iniciais } from '../format'

const ICONE_BUSCA = ['M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0z', 'M21 21l-4.35-4.35']
const ICONE_NOVO = ['M12 5v14', 'M5 12h14']

// 3 pares [fundo, cor] escolhidos por hash simples do nome — cor estável por cliente.
const PARES_AVATAR = [
  { background: 'var(--azul-claro)', color: 'var(--azul-hover)' },
  { background: 'var(--laranja-fundo)', color: 'var(--laranja)' },
  { background: 'var(--verde-fundo)', color: 'var(--verde)' },
]
const corAvatar = (nome) => {
  let h = 0
  for (let i = 0; i < (nome || '').length; i++) h = (h + nome.charCodeAt(i)) % 997
  return PARES_AVATAR[h % PARES_AVATAR.length]
}

function AvatarCliente({ nome }) {
  const par = corAvatar(nome)
  return (
    <span className="avatar-consultor" style={{ background: par.background, color: par.color }}>
      {iniciais(nome)}
    </span>
  )
}

export default function Clientes() {
  const [clientes, setClientes] = useState(null)
  const [erro, setErro] = useState(null)
  const [busca, setBusca] = useState('')
  const [modalNovo, setModalNovo] = useState(false)

  const carregar = () => {
    api.get('/clientes').then(setClientes).catch((e) => setErro(e.message))
  }
  useEffect(carregar, [])

  const filtrados = useMemo(() => {
    if (!clientes) return []
    const q = busca.trim().toLowerCase()
    if (!q) return clientes
    return clientes.filter((c) => c.nome.toLowerCase().includes(q))
  }, [clientes, busca])

  if (erro) return <div className="mensagem-erro">{erro}</div>
  if (!clientes) return <SkeletonPagina />

  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <h1>Clientes</h1>
          <div className="descricao">Carteira de clientes e sua receita prevista e realizada</div>
        </div>
        <button className="botao botao-primario" onClick={() => setModalNovo(true)}>
          <Icone d={ICONE_NOVO} size={16} />
          Novo cliente
        </button>
      </div>

      <div style={{ position: 'relative', maxWidth: 360, marginBottom: 'var(--esp-4)' }}>
        <span style={{
          position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)',
          color: 'var(--texto-3)', display: 'flex', pointerEvents: 'none',
        }}>
          <Icone d={ICONE_BUSCA} size={16} />
        </span>
        <input
          className="campo-busca"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Buscar cliente..."
        />
      </div>

      <div className="card">
        <div style={{ overflowX: 'auto' }}>
          <table className="tabela">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Contato</th>
                <th className="num">Nº de projetos</th>
                <th className="num">Receita prevista total</th>
                <th className="num">Receita realizada</th>
              </tr>
            </thead>
            <tbody>
              {filtrados.map((c) => (
                <tr key={c.id}>
                  <td>
                    <div className="linha-flex" style={{ gap: 10 }}>
                      <AvatarCliente nome={c.nome} />
                      <Link className="link" to={`/clientes/${c.id}`}>{c.nome}</Link>
                    </div>
                  </td>
                  <td className="texto-2">{c.contato || '—'}</td>
                  <td className="num">{c.n_projetos}</td>
                  <td className="num">{fmtBRL(c.receita_prevista)}</td>
                  <td className="num" style={{ color: 'var(--verde)', fontWeight: 600 }}>
                    {fmtBRL(c.receita_realizada)}
                  </td>
                </tr>
              ))}
              {clientes.length === 0 && (
                <tr><td colSpan={5} className="vazio">Nenhum cliente. Cadastre o primeiro!</td></tr>
              )}
              {clientes.length > 0 && filtrados.length === 0 && (
                <tr><td colSpan={5} className="vazio">Nenhum cliente encontrado para “{busca}”.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {modalNovo && (
        <FormNovoCliente
          onFechar={() => setModalNovo(false)}
          onCriado={() => { setModalNovo(false); carregar() }}
        />
      )}
    </>
  )
}

function FormNovoCliente({ onFechar, onCriado }) {
  const [form, setForm] = useState({ nome: '', contato: '' })
  const [erro, setErro] = useState(null)
  const [salvando, setSalvando] = useState(false)

  const salvar = async (e) => {
    e.preventDefault()
    setSalvando(true)
    setErro(null)
    try {
      await api.post('/clientes', { nome: form.nome, contato: form.contato })
      onCriado()
    } catch (err) {
      setErro(err.message)
      setSalvando(false)
    }
  }

  return (
    <Modal titulo="Novo cliente" onFechar={onFechar}
      rodape={<>
        <button className="botao botao-fantasma" onClick={onFechar}>Cancelar</button>
        <button className="botao botao-primario" type="submit" form="form-cliente" disabled={salvando || !form.nome}>
          {salvando ? 'Salvando…' : 'Salvar'}
        </button>
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
