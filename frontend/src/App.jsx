import { useEffect, useMemo, useRef, useState } from 'react'
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { api } from './api'
import Icone from './components/Icone'
import { MarcaCompleta } from './components/Marca'
import MenuUsuario from './components/MenuUsuario'
import { iniciais } from './format'
import { useSessao } from './sessao'
import Agenda from './pages/Agenda'
import Apontamento from './pages/Apontamento'
import Aprovacoes from './pages/Aprovacoes'
import Ausencias from './pages/Ausencias'
import ClienteDetalhe from './pages/ClienteDetalhe'
import Clientes from './pages/Clientes'
import Configuracoes from './pages/Configuracoes'
import ConsultorDetalhe from './pages/ConsultorDetalhe'
import Consultores from './pages/Consultores'
import Contratos from './pages/Contratos'
import Copiloto from './pages/Copiloto'
import Dashboard from './pages/Dashboard'
import Despesas from './pages/Despesas'
import Financeiro from './pages/Financeiro'
import FinanceiroGerencial from './pages/FinanceiroGerencial'
import Login from './pages/Login'
import Medicoes from './pages/Medicoes'
import Pendencias from './pages/Pendencias'
import ProjetoDetalhe from './pages/ProjetoDetalhe'
import Projetos from './pages/Projetos'
import Propostas from './pages/Propostas'
import QuadroAgil from './pages/QuadroAgil'

const IC = {
  dashboard: ['M3 3h7v9H3z', 'M14 3h7v5h-7z', 'M14 12h7v9h-7z', 'M3 16h7v5H3z'],
  faisca: ['M13 2 3 14h9l-1 8 10-12h-9l1-8z'],
  proposta: ['M22 2 11 13', 'M22 2 15 22l-4-9-9-4 20-7z'],
  contrato: ['M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z', 'M14 2v6h6', 'M8 13h8', 'M8 17h5'],
  cliente: ['M4 7h16a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1z', 'M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2'],
  projetos: ['M8 6h13', 'M8 12h13', 'M8 18h13', 'M3 6h.01', 'M3 12h.01', 'M3 18h.01'],
  alerta: ['M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z', 'M12 9v4', 'M12 17h.01'],
  equipe: ['M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2', 'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z', 'M23 21v-2a4 4 0 0 0-3-3.87', 'M16 3.13a4 4 0 0 1 0 7.75'],
  calendario: ['M5 4h14a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z', 'M16 2v4', 'M8 2v4', 'M3 10h18'],
  aprovar: ['M22 11.08V12a10 10 0 1 1-5.93-9.14', 'M22 4 12 14.01l-3-3'],
  relogio: ['M12 8v4l3 3', 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z'],
  cartao: ['M2 5h20a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z', 'M1 10h22'],
  ausencia: ['M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z', 'M12 1v2', 'M12 21v2', 'M4.2 4.2l1.4 1.4', 'M18.4 18.4l1.4 1.4', 'M1 12h2', 'M21 12h2', 'M4.2 19.8l1.4-1.4', 'M18.4 5.6l1.4-1.4'],
  fatura: ['M6 2h9l5 5v15a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z', 'M15 2v5h5', 'M9 13h6', 'M9 17h4'],
  medicao: ['M9 2h6a1 1 0 0 1 1 1v2H8V3a1 1 0 0 1 1-1z', 'M8 5H6a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2', 'M9 14l2 2 4-4'],
  receber: ['M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z', 'M8 12l4 4 4-4', 'M12 8v8'],
  pagar: ['M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z', 'M16 12l-4-4-4 4', 'M12 16V8'],
  fluxo: ['M22 12h-4l-3 9L9 3l-3 9H2'],
  grafico: ['M12 20V10', 'M18 20V4', 'M6 20v-4'],
  sino: ['M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9', 'M13.73 21a2 2 0 0 1-3.46 0'],
  engrenagem: ['M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z', 'M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z'],
  sair: ['M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4', 'M16 17l5-5-5-5', 'M21 12H9'],
  lupa: ['M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z', 'M21 21l-4.35-4.35'],
  mais: ['M12 5v14', 'M5 12h14'],
  menu: ['M3 6h18', 'M3 12h18', 'M3 18h18'],
  x: ['M18 6 6 18', 'M6 6l12 12'],
}

/* Navegação global na SIDEBAR, agrupada por domínio (padrão Productive/ClickUp):
 * todos os destinos ficam visíveis de uma vez, sem esconder nada atrás de abas. */
const ROTULO_PERFIL = { ceo: 'CEO', rh: 'RH', consultor: 'Consultor' }

const GRUPOS_CEO = [
  { rotulo: 'Visão geral', itens: [
    { rotulo: 'Dashboard', para: '/dashboard', icone: IC.dashboard },
    { rotulo: 'Copiloto', para: '/copiloto', icone: IC.faisca },
  ] },
  { rotulo: 'Comercial', itens: [
    { rotulo: 'Propostas', para: '/propostas', icone: IC.proposta },
    { rotulo: 'Contratos', para: '/contratos', icone: IC.contrato },
    { rotulo: 'Clientes', para: '/clientes', icone: IC.cliente },
  ] },
  { rotulo: 'Projetos', itens: [
    { rotulo: 'Projetos', para: '/projetos', icone: IC.projetos },
    { rotulo: 'Pendências', para: '/pendencias', icone: IC.alerta },
  ] },
  { rotulo: 'Equipe', itens: [
    { rotulo: 'Consultores', para: '/consultores', icone: IC.equipe },
    { rotulo: 'Agenda', para: '/agenda', icone: IC.calendario },
    { rotulo: 'Aprovações', para: '/aprovacoes', icone: IC.aprovar, contador: 'pendentes' },
    { rotulo: 'Apontamento', para: '/apontamento', icone: IC.relogio },
    { rotulo: 'Despesas', para: '/despesas', icone: IC.cartao },
    { rotulo: 'Ausências', para: '/ausencias', icone: IC.ausencia },
  ] },
  { rotulo: 'Financeiro', itens: [
    { rotulo: 'Faturamento', para: '/financeiro', icone: IC.fatura },
    { rotulo: 'Medições', para: '/medicoes', icone: IC.medicao },
    { rotulo: 'Contas a receber', para: '/contas-a-receber', icone: IC.receber },
    { rotulo: 'Contas a pagar', para: '/contas-a-pagar', icone: IC.pagar },
    { rotulo: 'Fluxo de caixa', para: '/fluxo-de-caixa', icone: IC.fluxo },
    { rotulo: 'Rentabilidade', para: '/rentabilidade', icone: IC.grafico },
  ] },
]

/* RH: gestão de pessoas — aprova horas/despesas/ausências/alocações e cuida
 * da equipe. Sem financeiro, comercial nem projetos: isso é visão do CEO. */
const GRUPOS_RH = [
  { rotulo: 'Equipe', itens: [
    { rotulo: 'Aprovações', para: '/aprovacoes', icone: IC.aprovar, contador: 'pendentes' },
    { rotulo: 'Consultores', para: '/consultores', icone: IC.equipe },
    { rotulo: 'Agenda', para: '/agenda', icone: IC.calendario },
    { rotulo: 'Apontamento', para: '/apontamento', icone: IC.relogio },
    { rotulo: 'Despesas', para: '/despesas', icone: IC.cartao },
    { rotulo: 'Ausências', para: '/ausencias', icone: IC.ausencia },
  ] },
]

const GRUPOS_CONSULTOR = [
  { rotulo: 'Meu espaço', itens: [
    { rotulo: 'Apontamento', para: '/apontamento', icone: IC.relogio },
    { rotulo: 'Agenda', para: '/agenda', icone: IC.calendario },
    { rotulo: 'Despesas', para: '/despesas', icone: IC.cartao },
    { rotulo: 'Ausências', para: '/ausencias', icone: IC.ausencia },
  ] },
]

/* Ações rápidas do botão "+ Novo": levam à tela COM o formulário aberto
 * (?novo=1), então o rótulo entrega exatamente o que promete. */
const ACOES_CEO = [
  { rotulo: 'Novo projeto', para: '/projetos?novo=1', icone: IC.projetos },
  { rotulo: 'Nova proposta', para: '/propostas?novo=1', icone: IC.proposta },
  { rotulo: 'Nova despesa', para: '/despesas?novo=1', icone: IC.cartao },
  { rotulo: 'Lançar horas', para: '/apontamento', icone: IC.relogio },
]
const ACOES_RH = [
  { rotulo: 'Nova despesa', para: '/despesas?novo=1', icone: IC.cartao },
]
const ACOES_CONSULTOR = [
  { rotulo: 'Lançar horas', para: '/apontamento', icone: IC.relogio },
  { rotulo: 'Nova despesa', para: '/despesas?novo=1', icone: IC.cartao },
  { rotulo: 'Pedir ausência', para: '/ausencias', icone: IC.ausencia },
]

export default function App() {
  const { sessao } = useSessao()
  return (
    <Routes>
      <Route path="/login" element={sessao ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/*" element={sessao ? <Shell /> : <Navigate to="/login" replace />} />
    </Routes>
  )
}

function Shell() {
  const { sessao, sair } = useSessao()
  const nav = useNavigate()
  const location = useLocation()
  const consultor = sessao.perfil === 'consultor'
  const rh = sessao.perfil === 'rh'
  const [pendentes, setPendentes] = useState(0)
  const [gaveta, setGaveta] = useState(false) // sidebar como gaveta no mobile

  const grupos = consultor ? GRUPOS_CONSULTOR : rh ? GRUPOS_RH : GRUPOS_CEO
  const acoes = consultor ? ACOES_CONSULTOR : rh ? ACOES_RH : ACOES_CEO

  useEffect(() => {
    if (consultor) return
    api.get('/aprovacoes').then((d) => setPendentes(d.total_pendente)).catch(() => {})
  }, [consultor, location.pathname])

  // trocar de rota fecha a gaveta
  useEffect(() => { setGaveta(false) }, [location.pathname])

  const contadores = { pendentes }

  const logout = () => {
    sair()
    nav('/login', { replace: true })
  }

  return (
    <div className={`app${gaveta ? ' gaveta-aberta' : ''}`}>
      <div className="gaveta-fundo" onClick={() => setGaveta(false)} aria-hidden="true" />

      <aside className="sidebar">
        <div className="sidebar-topo">
          <div className="sidebar-marca">
            <MarcaCompleta size={30} />
          </div>
          <button className="icone-botao so-mobile" type="button" aria-label="Fechar menu" onClick={() => setGaveta(false)}>
            <Icone d={IC.x} size={18} />
          </button>
        </div>

        <MenuNovo acoes={acoes} />

        <nav className="sidebar-nav" aria-label="Navegação principal">
          {grupos.map((g) => (
            <div className="sidebar-grupo" key={g.rotulo}>
              <div className="sidebar-grupo-rotulo">{g.rotulo}</div>
              {g.itens.map((item) => (
                <NavLink
                  key={item.para}
                  to={item.para}
                  title={item.rotulo}
                  className={({ isActive }) => `sidebar-item${isActive ? ' ativo' : ''}`}
                >
                  <Icone d={item.icone} size={17} />
                  <span className="rotulo">{item.rotulo}</span>
                  {item.contador && contadores[item.contador] > 0 && (
                    <span className="sidebar-contador">{contadores[item.contador]}</span>
                  )}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-rodape">
          {!consultor && (
            <NavLink to="/configuracoes" className={({ isActive }) => `sidebar-item${isActive ? ' ativo' : ''}`} title="Configurações">
              <Icone d={IC.engrenagem} size={17} />
              <span className="rotulo">Configurações</span>
            </NavLink>
          )}
          <div className="sidebar-usuario">
            <span className="avatar" aria-hidden="true">{iniciais(sessao?.nome) || 'MS'}</span>
            <span className="quem">
              <span className="nome">{sessao?.nome}</span>
              <span className="perfil">{ROTULO_PERFIL[sessao.perfil] ?? sessao.perfil}</span>
            </span>
            <button className="icone-botao" type="button" title="Sair" aria-label="Sair" onClick={logout}>
              <Icone d={IC.sair} size={16} />
            </button>
          </div>
        </div>
      </aside>

      <div className="app-principal">
        <header className="app-topbar">
          <button className="icone-botao so-mobile" type="button" aria-label="Abrir menu" onClick={() => setGaveta(true)}>
            <Icone d={IC.menu} size={19} />
          </button>
          <BuscaDestinos grupos={grupos} />
          <div className="app-topbar-acoes">
            <button className="icone-botao" type="button" aria-label="Notificações" title="Notificações">
              <Icone d={IC.sino} size={18} />
              {pendentes > 0 && <span className="ponto-notif" aria-hidden="true" />}
            </button>
            <MenuUsuario />
          </div>
        </header>

        <main className="conteudo">
          <div className="conteudo-interno">
            {consultor ? (
              <Routes>
                <Route path="/apontamento" element={<Apontamento />} />
                <Route path="/agenda" element={<Agenda />} />
                <Route path="/despesas" element={<Despesas />} />
                <Route path="/ausencias" element={<Ausencias />} />
                <Route path="*" element={<Navigate to="/apontamento" replace />} />
              </Routes>
            ) : rh ? (
              <Routes>
                <Route path="/" element={<Navigate to="/aprovacoes" replace />} />
                <Route path="/aprovacoes" element={<Aprovacoes />} />
                <Route path="/consultores" element={<Consultores />} />
                <Route path="/consultores/:id" element={<ConsultorDetalhe />} />
                <Route path="/agenda" element={<Agenda />} />
                <Route path="/apontamento" element={<Apontamento />} />
                <Route path="/despesas" element={<Despesas />} />
                <Route path="/ausencias" element={<Ausencias />} />
                <Route path="*" element={<Navigate to="/aprovacoes" replace />} />
              </Routes>
            ) : (
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/copiloto" element={<Copiloto />} />
                <Route path="/propostas" element={<Propostas />} />
                <Route path="/projetos" element={<Projetos />} />
                <Route path="/projetos/:id" element={<ProjetoDetalhe />} />
                <Route path="/projetos/:id/agil" element={<QuadroAgil />} />
                <Route path="/consultores" element={<Consultores />} />
                <Route path="/agenda" element={<Agenda />} />
                <Route path="/consultores/:id" element={<ConsultorDetalhe />} />
                <Route path="/clientes" element={<Clientes />} />
                <Route path="/clientes/:id" element={<ClienteDetalhe />} />
                <Route path="/aprovacoes" element={<Aprovacoes />} />
                <Route path="/pendencias" element={<Pendencias />} />
                <Route path="/apontamento" element={<Apontamento />} />
                <Route path="/despesas" element={<Despesas />} />
                <Route path="/ausencias" element={<Ausencias />} />
                <Route path="/contratos" element={<Contratos />} />
                <Route path="/medicoes" element={<Medicoes />} />
                <Route path="/financeiro" element={<Financeiro aba="faturamento" />} />
                <Route path="/contas-a-receber" element={<Financeiro aba="receber" />} />
                <Route path="/contas-a-pagar" element={<FinanceiroGerencial key="pagar" vista="pagar" />} />
                <Route path="/fluxo-de-caixa" element={<FinanceiroGerencial key="fluxo" vista="fluxo" />} />
                <Route path="/rentabilidade" element={<FinanceiroGerencial key="rentabilidade" vista="rentabilidade" />} />
                <Route path="/configuracoes" element={<Configuracoes />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

/** Botão de ação primário da sidebar (o "+ Add" do Productive) com as
 * criações mais frequentes — cada item abre o formulário na tela de destino. */
function MenuNovo({ acoes }) {
  const nav = useNavigate()
  const [aberto, setAberto] = useState(false)
  const caixa = useRef(null)

  useEffect(() => {
    if (!aberto) return
    const fora = (e) => { if (!caixa.current?.contains(e.target)) setAberto(false) }
    const tecla = (e) => { if (e.key === 'Escape') setAberto(false) }
    document.addEventListener('mousedown', fora)
    document.addEventListener('keydown', tecla)
    return () => {
      document.removeEventListener('mousedown', fora)
      document.removeEventListener('keydown', tecla)
    }
  }, [aberto])

  return (
    <div className="menu-novo" ref={caixa}>
      <button
        className="botao botao-primario botao-bloco"
        type="button"
        aria-expanded={aberto}
        aria-haspopup="menu"
        onClick={() => setAberto((v) => !v)}
      >
        <Icone d={IC.mais} size={16} strokeWidth={2.5} />
        <span className="rotulo">Novo</span>
      </button>
      {aberto && (
        <div className="menu-flutuante" role="menu">
          {acoes.map((a) => (
            <button
              key={a.para}
              role="menuitem"
              type="button"
              className="menu-item"
              onClick={() => { setAberto(false); nav(a.para) }}
            >
              <Icone d={a.icone} size={15} /> {a.rotulo}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

/** Busca de destinos ("ir para") — filtra a navegação e salta para a tela.
 * Enter vai no primeiro resultado; ↑/↓ percorrem; Esc fecha. */
function BuscaDestinos({ grupos }) {
  const nav = useNavigate()
  const [termo, setTermo] = useState('')
  const [aberto, setAberto] = useState(false)
  const [indice, setIndice] = useState(0)
  const caixa = useRef(null)

  const destinos = useMemo(
    () => grupos.flatMap((g) => g.itens.map((i) => ({ ...i, grupo: g.rotulo }))),
    [grupos],
  )
  // sem regex de diacriticos: filtra as marcas combinantes por code point
  const normalizar = (s) => [...s.normalize('NFD')]
    .filter((c) => { const n = c.charCodeAt(0); return n < 0x300 || n > 0x36f })
    .join('').toLowerCase()
  const achados = useMemo(() => {
    const t = normalizar(termo.trim())
    if (!t) return destinos.slice(0, 6)
    return destinos.filter((d) => normalizar(`${d.rotulo} ${d.grupo}`).includes(t)).slice(0, 7)
  }, [termo, destinos])

  useEffect(() => {
    if (!aberto) return
    const fora = (e) => { if (!caixa.current?.contains(e.target)) setAberto(false) }
    document.addEventListener('mousedown', fora)
    return () => document.removeEventListener('mousedown', fora)
  }, [aberto])

  const ir = (d) => {
    if (!d) return
    setAberto(false)
    setTermo('')
    nav(d.para)
  }

  const teclado = (e) => {
    if (e.key === 'Escape') { setAberto(false); e.currentTarget.blur() }
    else if (e.key === 'ArrowDown') { e.preventDefault(); setIndice((i) => Math.min(i + 1, achados.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setIndice((i) => Math.max(i - 1, 0)) }
    else if (e.key === 'Enter') { e.preventDefault(); ir(achados[indice]) }
  }

  return (
    <div className="busca-global" ref={caixa}>
      <span className="busca-icone" aria-hidden="true"><Icone d={IC.lupa} size={16} /></span>
      <input
        type="search"
        value={termo}
        placeholder="Buscar tela…"
        aria-label="Buscar tela"
        onChange={(e) => { setTermo(e.target.value); setIndice(0); setAberto(true) }}
        onFocus={() => setAberto(true)}
        onKeyDown={teclado}
      />
      {aberto && achados.length > 0 && (
        <div className="menu-flutuante busca-resultados" role="listbox">
          {achados.map((d, i) => (
            <button
              key={d.para}
              type="button"
              role="option"
              aria-selected={i === indice}
              className={`menu-item${i === indice ? ' marcado' : ''}`}
              onMouseEnter={() => setIndice(i)}
              onClick={() => ir(d)}
            >
              <Icone d={d.icone} size={15} /> {d.rotulo}
              <span className="menu-item-meta">{d.grupo}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
