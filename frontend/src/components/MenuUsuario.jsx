import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Icone from './Icone'
import { iniciais } from '../format'
import { useSessao } from '../sessao'
import { useTema } from '../tema'

const IC = {
  engrenagem: ['M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z', 'M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z'],
  sair: ['M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4', 'M16 17l5-5-5-5', 'M21 12H9'],
}

const TEMAS = [
  { id: 'claro', rotulo: 'Claro' },
  { id: 'escuro', rotulo: 'Escuro' },
  { id: 'sistema', rotulo: 'Sistema' },
]

/** Menu da conta: identidade, tema em 1 clique, configurações e saída.
 * Antes o avatar não fazia nada — agora é o acesso rápido de sempre. */
export default function MenuUsuario() {
  const { sessao, sair } = useSessao()
  const { preferencia, efetivo, escolher } = useTema()
  const nav = useNavigate()
  const [aberto, setAberto] = useState(false)
  const caixa = useRef(null)
  const gatilho = useRef(null)

  useEffect(() => {
    if (!aberto) return
    const fora = (e) => { if (!caixa.current?.contains(e.target)) setAberto(false) }
    const tecla = (e) => {
      if (e.key === 'Escape') { setAberto(false); gatilho.current?.focus() }
    }
    document.addEventListener('mousedown', fora)
    document.addEventListener('keydown', tecla)
    return () => {
      document.removeEventListener('mousedown', fora)
      document.removeEventListener('keydown', tecla)
    }
  }, [aberto])

  const consultor = sessao?.perfil === 'consultor'
  const ROTULOS = { ceo: 'CEO', rh: 'RH', consultor: 'Consultor' }

  return (
    <div className="menu-usuario-raiz" ref={caixa}>
      <button
        ref={gatilho}
        type="button"
        className="avatar-botao"
        aria-haspopup="menu"
        aria-expanded={aberto}
        aria-label={`Conta de ${sessao?.nome}`}
        onClick={() => setAberto((v) => !v)}
      >
        {iniciais(sessao?.nome) || 'RR'}
      </button>

      {aberto && (
        <div className="menu-flutuante menu-usuario" role="menu">
          <div className="menu-usuario-topo">
            <span className="avatar" aria-hidden="true">{iniciais(sessao?.nome) || 'RR'}</span>
            <span className="quem">
              <span className="nome">{sessao?.nome}</span>
              <span className="perfil">{ROTULOS[sessao?.perfil] ?? sessao?.perfil}</span>
            </span>
          </div>

          <div className="menu-usuario-tema">
            <span className="rotulo-tema">
              Tema
              {preferencia === 'sistema' && <span className="texto-3"> · seguindo o sistema ({efetivo})</span>}
            </span>
            <div className="segmentado" role="group" aria-label="Tema da interface">
              {TEMAS.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  aria-pressed={preferencia === t.id}
                  onClick={() => escolher(t.id)}
                >
                  {t.rotulo}
                </button>
              ))}
            </div>
          </div>

          {sessao?.perfil === 'ceo' && (
            <button
              role="menuitem"
              type="button"
              className="menu-item"
              onClick={() => { setAberto(false); nav('/configuracoes') }}
            >
              <Icone d={IC.engrenagem} size={15} /> Configurações
            </button>
          )}
          <button
            role="menuitem"
            type="button"
            className="menu-item"
            onClick={() => { setAberto(false); sair(); nav('/login', { replace: true }) }}
          >
            <Icone d={IC.sair} size={15} /> Sair da conta
          </button>
        </div>
      )}
    </div>
  )
}
