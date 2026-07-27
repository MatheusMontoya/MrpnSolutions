import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MarcaCompleta } from '../components/Marca'
import { useSessao } from '../sessao'
import { api } from '../api'

// Login REAL: e-mail + senha contra /api/auth/login (pbkdf2 no backend).
// O token retornado vai em todas as chamadas via api.js (Authorization: Bearer).
//
// Layout: coluna única centrada, no padrão Stripe/ClickUp — marca pequena no
// topo, campo e botão na MESMA largura, nada de painel decorativo. A tela de
// entrada não precisa vender o produto para quem já é cliente; precisa sumir.

const DEMOS = [
  { rotulo: 'Gestor', email: 'gestor@psa.com' },
  { rotulo: 'Consultora', email: 'ana@psa.com' },
]
const SENHA_DEMO = 'psa123'

// O bloco de credenciais fica visível por padrão (é um ambiente de demonstração).
// Quando isto virar instância de cliente, basta VITE_DEMO=0 nas variáveis da
// Vercel: some da tela sem mexer em código.
const MOSTRAR_DEMO = import.meta.env.VITE_DEMO !== '0'

export default function Login() {
  const nav = useNavigate()
  const { entrar } = useSessao()
  const [form, setForm] = useState({ email: '', senha: '' })
  const [erro, setErro] = useState(null)
  const [ocupado, setOcupado] = useState(false)

  const onSubmit = async (e) => {
    e.preventDefault()
    setOcupado(true)
    setErro(null)
    try {
      const r = await api.post('/auth/login', form)
      entrar({ token: r.token, perfil: r.perfil, nome: r.nome, consultorId: r.consultor_id })
      nav(r.perfil === 'gestor' ? '/dashboard' : '/apontamento')
    } catch (err) {
      setErro(err.message)
      setOcupado(false)
    }
  }

  return (
    <div className="login">
      <main className="login-coluna">
        <div className="login-marca">
          <MarcaCompleta size={34} />
          <p className="login-assinatura">Tudo se encaixa. Entrega com controle.</p>
        </div>

        <div className="login-titulo">
          <h1>Bem-vindo de volta</h1>
          <p>Entre com seu e-mail e senha para continuar.</p>
        </div>

        <form className="login-form" onSubmit={onSubmit}>
          {erro && <div className="mensagem-erro">{erro}</div>}

          <div className="campo">
            <label htmlFor="login-email">E-mail</label>
            <input
              id="login-email"
              type="email"
              autoComplete="username"
              autoFocus
              required
              placeholder="voce@mrpn.com.br"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </div>

          <div className="campo">
            <label htmlFor="login-senha">Senha</label>
            <input
              id="login-senha"
              type="password"
              autoComplete="current-password"
              required
              placeholder="••••••••"
              value={form.senha}
              onChange={(e) => setForm({ ...form, senha: e.target.value })}
            />
            {/* não existe autoatendimento de senha: quem redefine é o gestor,
                em Configurações › Usuários. Dizer isso evita um link morto. */}
            <p className="campo-ajuda">Esqueceu a senha? O gestor da conta redefine em Configurações.</p>
          </div>

          <button
            type="submit"
            className="botao botao-primario botao-bloco"
            disabled={ocupado || !form.email || !form.senha}
          >
            {ocupado ? 'Entrando…' : 'Entrar'}
          </button>
        </form>

        {MOSTRAR_DEMO && (
        <div className="login-demo">
          <span className="login-demo-titulo">Ambiente de demonstração</span>
          <div className="login-demo-perfis">
            {DEMOS.map((d) => (
              <button
                key={d.email}
                type="button"
                className="login-credencial"
                onClick={() => setForm({ email: d.email, senha: SENHA_DEMO })}
              >
                <span className="quem">{d.rotulo}</span>
                <span className="conta">{d.email}</span>
              </button>
            ))}
          </div>
          <span className="login-demo-senha">Senha: {SENHA_DEMO}</span>
        </div>
        )}

        <p className="login-rodape">© 2026 MRPN Solutions · runrate.com.br</p>
      </main>
    </div>
  )
}
