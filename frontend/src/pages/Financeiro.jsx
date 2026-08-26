import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import FalhaAoCarregar from '../components/FalhaAoCarregar'
import BotaoExportar from '../components/BotaoExportar'
import Icone from '../components/Icone'
import { SkeletonPagina } from '../components/Skeleton'
import { fmtBRL, fmtBRLExato, fmtData, fmtMes } from '../format'
import { comAviso, confirmarE } from '../avisos'

const IC_GERAR = ['M23 4v6h-6', 'M1 20v-6h6', 'M3.51 9a9 9 0 0 1 14.85-3.36L23 10', 'M1 14l4.64 4.36A9 9 0 0 0 20.49 15']
const IC_EMITIR = ['M22 2 11 13', 'M22 2 15 22l-4-9-9-4 20-7z']
const IC_RECEBER = ['M20 6 9 17l-5-5']

const BADGE = {
  prevista: ['badge-cinza', 'Prevista'],
  emitida: ['badge-azul', 'Emitida'],
  recebida: ['badge-verde', 'Recebida'],
  cancelada: ['badge-vermelho', 'Cancelada'],
}

/** Financeiro: aba "faturamento" (plano completo) ou "receber" (emitidas em aberto). */
export default function Financeiro({ aba = 'faturamento' }) {
  const receber = aba === 'receber'
  const [dados, setDados] = useState(null)
  const [projetos, setProjetos] = useState([])
  const [projetoId, setProjetoId] = useState('') // '' = todos
  const [erro, setErro] = useState(null)
  const [editandoNF, setEditandoNF] = useState(null) // { id, valor }

  const carregar = useCallback(() => {
    const q = projetoId ? `?projeto_id=${projetoId}` : ''
    api.get(`/faturas${q}`).then(setDados).catch((e) => setErro(e.message))
  }, [projetoId])

  useEffect(() => {
    carregar()
    api.get('/projetos').then(setProjetos).catch(() => {})
  }, [carregar])

  if (erro) return <FalhaAoCarregar erro={erro} aoTentarDeNovo={carregar} />
  if (!dados) return <SkeletonPagina kpis />

  const faturas = receber
    ? dados.faturas.filter((f) => f.status === 'emitida')
    : dados.faturas.filter((f) => f.status !== 'cancelada')

  const gerarPlano = () => comAviso(
    async () => { await api.post(`/projetos/${projetoId}/faturas/gerar`, {}); carregar() },
    { sucesso: 'Plano de faturas atualizado.' },
  )
  // o número da nota chega do sistema fiscal DEPOIS da emissão: é edição
  // solta, sem confirmação — errar aqui se corrige digitando de novo
  const salvarNumero = (f, numero) => comAviso(
    async () => {
      if ((numero || '').trim() !== (f.numero || '')) {
        await api.patch(`/faturas/${f.id}`, { numero })
        carregar()
      }
      setEditandoNF(null)
    },
  )

  // emitir e receber movimentam dinheiro e não têm desfazer na tela
  const mudarStatus = (f, status) => {
    const pergunta = {
      emitida: `Emitir a fatura de ${fmtBRLExato(f.valor)} de ${f.projeto}?`,
      recebida: `Dar baixa no recebimento de ${fmtBRLExato(f.valor)} de ${f.projeto}?`,
      cancelada: `Cancelar a fatura de ${fmtBRLExato(f.valor)}?`,
    }[status]
    const executar = async () => { await api.patch(`/faturas/${f.id}`, { status }); carregar() }
    const opcoes = { sucesso: `Fatura marcada como ${status}.` }
    return pergunta ? confirmarE(pergunta, executar, opcoes) : comAviso(executar, opcoes)
  }

  return (
    <>
      <div className="pagina-cabecalho">
        <div>
          <h1>{receber ? 'Contas a Receber' : 'Cronograma de Faturamento'}</h1>
          <div className="descricao">
            {receber
              ? 'Faturas emitidas em aberto — acompanhe vencimentos e baixe os recebimentos'
              : 'Plano de faturas gerado da receita prevista do motor hora-homem, mês a mês'}
          </div>
        </div>
        <div className="linha-flex">
          <BotaoExportar recurso="faturas" />
          <div className="campo" style={{ minWidth: 220 }}>
            <select value={projetoId} onChange={(e) => setProjetoId(e.target.value)} aria-label="Filtrar por projeto">
              <option value="">Todos os projetos</option>
              {projetos.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
            </select>
          </div>
          {!receber && projetoId && (
            <button className="botao botao-primario" onClick={gerarPlano}
              title="Cria/atualiza as faturas previstas a partir da receita mensal prevista (emitidas e recebidas são preservadas)">
              <Icone d={IC_GERAR} size={14} /> Gerar plano
            </button>
          )}
        </div>
      </div>

      <div className="grid-kpi">
        <div className="card kpi">
          <div className="rotulo">Previsto (a faturar)</div>
          <div className="valor">{fmtBRL(dados.total_previsto)}</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Emitido (em aberto)</div>
          <div className="valor" style={{ color: 'var(--azul)' }}>{fmtBRL(dados.total_emitido)}</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Recebido</div>
          <div className="valor" style={{ color: 'var(--verde)' }}>{fmtBRL(dados.total_recebido)}</div>
        </div>
        <div className="card kpi">
          <div className="rotulo">Vencido</div>
          <div className="valor" style={{ color: dados.total_vencido > 0 ? 'var(--vermelho)' : 'var(--texto)' }}>
            {fmtBRL(dados.total_vencido)}
          </div>
          <div className="detalhe">{dados.total_vencido > 0 ? 'cobrança necessária' : 'nada vencido'}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-corpo" style={{ paddingTop: 10 }}>
          {faturas.length === 0 ? (
            <div className="vazio-ensina">
              <Icone d={IC_EMITIR} size={28} strokeWidth={1.5} />
              <span className="titulo">{receber ? 'Nenhuma fatura em aberto' : 'Nenhuma fatura ainda'}</span>
              <span className="dica">
                {receber
                  ? 'Faturas emitidas aparecem aqui até o recebimento.'
                  : 'Selecione um projeto e clique em “Gerar plano” — as faturas nascem da receita prevista mês a mês.'}
              </span>
            </div>
          ) : (
            <table className="tabela">
              <thead>
                <tr>
                  <th>Competência</th><th>Projeto</th><th>Cliente</th>
                  <th className="num">Valor</th><th>Status</th><th>Nº</th>
                  <th>{receber ? 'Vencimento' : 'Emissão / Vencimento'}</th><th></th>
                </tr>
              </thead>
              <tbody>
                {faturas.map((f) => {
                  const [cls, rotulo] = BADGE[f.status] || BADGE.prevista
                  return (
                    <tr key={f.id}>
                      <td className="mono" style={{ fontWeight: 600 }}>{fmtMes(f.competencia.slice(0, 7))}</td>
                      <td><Link className="link" to={`/projetos/${f.projeto_id}`}>{f.projeto}</Link></td>
                      <td className="texto-2">{f.cliente}</td>
                      <td className="num">{fmtBRLExato(f.valor)}</td>
                      <td>
                        <span className={`badge ${cls}`}>{rotulo}</span>
                        {f.vencida && <span className="badge badge-vermelho" style={{ marginLeft: 6 }}>vencida há {f.dias_vencida}d</span>}
                      </td>
                      <td className="mono" style={{ fontSize: 12 }}>
                        <NumeroNota
                          fatura={f}
                          editando={editandoNF?.id === f.id ? editandoNF.valor : null}
                          aoAbrir={() => setEditandoNF({ id: f.id, valor: f.numero || '' })}
                          aoDigitar={(v) => setEditandoNF({ id: f.id, valor: v })}
                          aoCancelar={() => setEditandoNF(null)}
                          aoSalvar={() => salvarNumero(f, editandoNF?.valor ?? '')}
                        />
                      </td>
                      <td className="mono texto-2" style={{ fontSize: 12 }}>
                        {receber
                          ? (f.data_vencimento ? fmtData(f.data_vencimento) : '—')
                          : `${f.data_emissao ? fmtData(f.data_emissao) : '—'} / ${f.data_vencimento ? fmtData(f.data_vencimento) : '—'}`}
                      </td>
                      <td>
                        <div className="linha-flex" style={{ gap: 6, justifyContent: 'flex-end' }}>
                          {f.status === 'prevista' && (
                            <button className="botao botao-secundario botao-pequeno" onClick={() => mudarStatus(f, 'emitida')}>
                              <Icone d={IC_EMITIR} size={12} /> Emitir
                            </button>
                          )}
                          {f.status === 'emitida' && (
                            <button className="botao botao-primario botao-pequeno" onClick={() => mudarStatus(f, 'recebida')}>
                              <Icone d={IC_RECEBER} size={12} /> Receber
                            </button>
                          )}
                          {(f.status === 'prevista' || f.status === 'emitida') && !receber && (
                            <button className="botao botao-fantasma botao-pequeno" onClick={() => mudarStatus(f, 'cancelada')}>
                              Cancelar
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
    </>
  )
}

/* Número da nota fiscal: texto até clicar, campo depois.
 *
 * A coluna existia desde sempre e mostrava "—" para todo mundo, porque o único
 * momento em que a API aceitava o número era o instante da emissão — e nessa
 * hora a nota ainda nem saiu do sistema fiscal. */
function NumeroNota({ fatura, editando, aoAbrir, aoDigitar, aoCancelar, aoSalvar }) {
  // fatura prevista ainda não tem nota: não há o que preencher
  if (fatura.status === 'prevista' || fatura.status === 'cancelada') {
    return <span className="texto-3">—</span>
  }
  if (editando === null) {
    return (
      <button type="button" className="celula-editavel" onClick={aoAbrir}
        title="Clique para informar o número da nota">
        {fatura.numero || <span className="texto-3">informar</span>}
      </button>
    )
  }
  return (
    <input
      className="entrada-celula"
      autoFocus
      value={editando}
      aria-label={`Número da nota da fatura de ${fatura.projeto}`}
      placeholder="000000"
      onChange={(e) => aoDigitar(e.target.value)}
      onBlur={aoSalvar}
      onKeyDown={(e) => {
        if (e.key === 'Enter') { e.preventDefault(); e.currentTarget.blur() }
        else if (e.key === 'Escape') { aoCancelar() }
      }}
    />
  )
}
