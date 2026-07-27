import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import Icone from '../components/Icone'
import { SkeletonPagina } from '../components/Skeleton'

const IC = {
  faisca: ['M12 3v3', 'M18.36 5.64l-2.12 2.12', 'M21 12h-3', 'M18.36 18.36l-2.12-2.12', 'M12 18v3', 'M7.76 16.24l-2.12 2.12', 'M6 12H3', 'M7.76 7.76 5.64 5.64', 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z'],
  alerta: ['M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z', 'M12 9v4', 'M12 17h.01'],
  info: ['M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z', 'M12 16v-4', 'M12 8h.01'],
  enviar: ['M22 2 11 13', 'M22 2 15 22l-4-9-9-4 20-7z'],
  seta: ['M5 12h14', 'M12 5l7 7-7 7'],
  robo: ['M12 8V4H8', 'M4 8h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2z', 'M2 14h2', 'M20 14h2', 'M15 13v2', 'M9 13v2'],
}

const SEVERIDADE = {
  critico: { rotulo: 'Crítico', cor: 'var(--vermelho)', icone: IC.alerta },
  atencao: { rotulo: 'Atenção', cor: 'var(--laranja)', icone: IC.alerta },
  info: { rotulo: 'Info', cor: 'var(--azul)', icone: IC.info },
}

const SUGESTOES = [
  'Como está a cobrança?',
  'Temos gargalos de capacidade?',
  'Quais projetos estão atrasados vs baseline?',
  'Como está o funil de propostas?',
]

export default function Copiloto() {
  const [dados, setDados] = useState(null)
  const [status, setStatus] = useState(null)
  const [erro, setErro] = useState(null)
  const [conversa, setConversa] = useState([]) // {autor:'eu'|'ia', texto, generativa}
  const [pergunta, setPergunta] = useState('')
  const [pensando, setPensando] = useState(false)
  const fimRef = useRef(null)

  useEffect(() => {
    Promise.all([api.get('/copiloto/insights'), api.get('/copiloto/status')])
      .then(([i, s]) => { setDados(i); setStatus(s) })
      .catch((e) => setErro(e.message))
  }, [])

  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [conversa, pensando])

  const enviar = async (texto) => {
    const p = (texto ?? pergunta).trim()
    if (!p || pensando) return
    setPergunta('')
    setConversa((c) => [...c, { autor: 'eu', texto: p }])
    setPensando(true)
    try {
      const r = await api.post('/copiloto/perguntar', { pergunta: p })
      setConversa((c) => [...c, { autor: 'ia', texto: r.resposta, generativa: r.ia_generativa }])
    } catch (e) {
      setConversa((c) => [...c, { autor: 'ia', texto: `Erro: ${e.message}` }])
    } finally {
      setPensando(false)
    }
  }

  if (erro) return <div className="mensagem-erro">{erro}</div>
  if (!dados || !status) return <SkeletonPagina />

  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <h1 className="linha-flex" style={{ gap: 10 }}>
            <Icone d={IC.faisca} size={22} /> Copiloto
          </h1>
          <p className="texto-2" style={{ margin: '4px 0 0', fontSize: 13.5 }}>
            Insights gerados pelo motor determinístico — a IA interpreta, nunca calcula.
          </p>
        </div>
        <span className={`badge ${status.ia_ativa ? 'badge-verde' : ''}`} title={status.ia_ativa ? `Modelo: ${status.modelo}` : 'Configure a chave da API Anthropic em Configurações'}>
          <Icone d={IC.robo} size={13} /> {status.ia_ativa ? `IA generativa ativa · ${status.modelo}` : 'Modo determinístico'}
        </span>
      </div>

      <div className="copiloto-layout">
        {/* ---------- coluna de insights ---------- */}
        <section className="card">
          <div className="card-cabecalho">
            <h2 className="card-titulo-secao">
              Insights de hoje
              {dados.criticos > 0 && <span className="badge badge-vermelho" style={{ marginLeft: 8 }}>{dados.criticos} crítico{dados.criticos > 1 ? 's' : ''}</span>}
            </h2>
            <span className="texto-3" style={{ fontSize: 12.5 }}>{dados.total} alerta{dados.total !== 1 ? 's' : ''}</span>
          </div>
          <div className="card-corpo" style={{ paddingTop: 4 }}>
            {dados.insights.length === 0 ? (
              <div className="vazio">Nenhum alerta ativo — operação saudável. 🎉</div>
            ) : (
              <ul className="lista-insights">
                {dados.insights.map((i, idx) => {
                  const sev = SEVERIDADE[i.severidade] ?? SEVERIDADE.info
                  return (
                    <li key={idx} className="insight-item" style={{ '--cor-insight': sev.cor }}>
                      <span className="insight-icone"><Icone d={sev.icone} size={15} /></span>
                      <div className="insight-corpo">
                        <div className="insight-titulo">{i.titulo}</div>
                        <div className="insight-detalhe">{i.detalhe}</div>
                      </div>
                      {i.link && (
                        <Link to={i.link} className="botao botao-fantasma botao-pequeno" title="Abrir tela relacionada">
                          <Icone d={IC.seta} size={14} />
                        </Link>
                      )}
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        </section>

        {/* ---------- coluna do chat ---------- */}
        <section className="card copiloto-chat">
          <div className="card-cabecalho">
            <h2 className="card-titulo-secao">Pergunte ao copiloto</h2>
          </div>
          <div className="chat-mensagens">
            {conversa.length === 0 && (
              <div className="chat-vazio">
                <Icone d={IC.faisca} size={26} strokeWidth={1.5} />
                <p className="texto-2" style={{ fontSize: 13.5, margin: '10px 0 14px' }}>
                  Pergunte sobre cobrança, capacidade, prazos, riscos ou o funil comercial.
                </p>
                <div className="chat-sugestoes">
                  {SUGESTOES.map((s) => (
                    <button key={s} type="button" className="chip-sugestao" onClick={() => enviar(s)}>{s}</button>
                  ))}
                </div>
              </div>
            )}
            {conversa.map((m, idx) => (
              <div key={idx} className={`chat-balao ${m.autor === 'eu' ? 'eu' : 'ia'}`}>
                {m.texto}
                {m.autor === 'ia' && m.generativa && (
                  <span className="chat-origem">IA generativa</span>
                )}
              </div>
            ))}
            {pensando && <div className="chat-balao ia pensando">Analisando o motor…</div>}
            <div ref={fimRef} />
          </div>
          <form
            className="chat-entrada"
            onSubmit={(e) => { e.preventDefault(); enviar() }}
          >
            <input
              value={pergunta}
              placeholder="Ex.: onde estamos perdendo margem?"
              onChange={(e) => setPergunta(e.target.value)}
              aria-label="Pergunta ao copiloto"
            />
            <button className="botao botao-primario" type="submit" disabled={!pergunta.trim() || pensando}>
              <Icone d={IC.enviar} size={15} /> Perguntar
            </button>
          </form>
        </section>
      </div>
    </>
  )
}
