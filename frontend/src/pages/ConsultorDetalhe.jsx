import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import EstadoVazio from '../components/EstadoVazio'
import Icone from '../components/Icone'
import { SkeletonPagina } from '../components/Skeleton'
import { SENIORIDADE, corFase, fmtBRL, fmtBRLExato, fmtData, fmtHoras, fmtPct, iniciais } from '../format'

const IC_SETA_ESQ = ['M19 12H5', 'M12 19l-7-7 7-7']
const IC_MODULO = [
  'M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z',
  'M3.27 6.96 12 12.01l8.73-5.05',
  'M12 22.08V12',
]
const IC_PIZZA = ['M21.21 15.89A10 10 0 1 1 8 2.83', 'M22 12A10 10 0 0 0 12 2v10z']
const IC_RELOGIO = ['M12 22a10 10 0 1 1 0-20 10 10 0 0 1 0 20z', 'M12 6v6l4 2']
const IC_RECEITA = ['M2 5h20a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z', 'M1 10h22', 'M6 15h4']
const IC_MARGEM = ['M18 20V10', 'M12 20V4', 'M6 20v-6']
const IC_VAZIO = ['M9 17H7A5 5 0 0 1 7 7h2', 'M15 7h2a5 5 0 0 1 0 10h-2', 'M8 12h8']

// Avatar de iniciais com cor por hash do nome (mesma convenção do app).
const PARES = [
  { fundo: 'var(--azul-claro)', cor: 'var(--azul-hover)' },
  { fundo: 'var(--laranja-fundo)', cor: 'var(--laranja)' },
  { fundo: 'var(--verde-fundo)', cor: 'var(--verde)' },
]
const parCor = (nome) => {
  let h = 0
  for (const ch of nome || '') h = (h * 31 + ch.charCodeAt(0)) >>> 0
  return PARES[h % PARES.length]
}

export default function ConsultorDetalhe() {
  const { id } = useParams()
  const [c, setC] = useState(null)
  const [erro, setErro] = useState(null)

  useEffect(() => {
    api.get(`/consultores/${id}/painel`).then(setC).catch((e) => setErro(e.message))
  }, [id])

  if (erro) return <div className="mensagem-erro">{erro}</div>
  if (!c) return <SkeletonPagina kpis />

  const par = parCor(c.nome)
  const kpis = [
    { icone: IC_PIZZA, rotulo: 'Utilização média', valor: fmtPct(c.utilizacao_media), detalhe: 'Últimas 12 semanas' },
    { icone: IC_RELOGIO, rotulo: 'Horas apontadas', valor: fmtHoras(c.horas_mes), detalhe: 'Mês atual' },
    { icone: IC_RECEITA, rotulo: 'Receita gerada', valor: fmtBRL(c.receita_mes), detalhe: 'Mês atual', cor: 'var(--azul)' },
    { icone: IC_MARGEM, rotulo: 'Margem', valor: fmtPct(c.margem_mes), detalhe: 'Mês atual', cor: 'var(--verde)' },
  ]

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <Link to="/consultores" className="link linha-flex" style={{ gap: 6, fontSize: 13 }}>
          <Icone d={IC_SETA_ESQ} size={15} strokeWidth={2} />
          Voltar para Consultores
        </Link>
      </div>

      <div className="card">
        <div className="card-corpo" style={{ display: 'flex', alignItems: 'flex-start', gap: 20, flexWrap: 'wrap' }}>
          <div
            style={{
              width: 64, height: 64, borderRadius: 'var(--raio-2)', flexShrink: 0,
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              background: par.fundo, color: par.cor,
              fontFamily: 'var(--fonte)', fontSize: 22, fontWeight: 600, letterSpacing: '0.02em',
            }}
          >
            {iniciais(c.nome)}
          </div>

          <div style={{ flex: 1, minWidth: 220 }}>
            <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, letterSpacing: '-0.01em' }}>{c.nome}</h1>
            <div className="linha-flex" style={{ gap: 12, marginTop: 10, flexWrap: 'wrap' }}>
              <span className="badge badge-azul">{SENIORIDADE[c.senioridade] || c.senioridade}</span>
              {c.modulo_sap && (
                <span className="texto-2 linha-flex" style={{ gap: 6, fontSize: 13 }}>
                  <Icone d={IC_MODULO} size={15} strokeWidth={1.75} />
                  Módulo {c.modulo_sap}
                </span>
              )}
            </div>
            {c.skills && (
              <div className="linha-flex" style={{ gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                {c.skills.split(',').map((s) => s.trim()).filter(Boolean).map((s) => (
                  <span key={s} className="chip-senioridade">{s}</span>
                ))}
              </div>
            )}
          </div>

          <div className="linha-flex" style={{ gap: 40, alignItems: 'flex-start', flexShrink: 0 }}>
            <div style={{ textAlign: 'right' }}>
              <div className="texto-3" style={{ fontSize: 12.5, fontWeight: 600 }}>
                Custo (hora)
              </div>
              <div className="mono" style={{ fontSize: 20, fontWeight: 500, marginTop: 6, fontVariantNumeric: 'tabular-nums' }}>
                {fmtBRLExato(c.taxa_hora_custo)}
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div className="texto-3" style={{ fontSize: 12.5, fontWeight: 600 }}>
                Venda (hora)
              </div>
              <div className="mono" style={{ fontSize: 20, fontWeight: 500, marginTop: 6, fontVariantNumeric: 'tabular-nums', color: 'var(--azul)' }}>
                {fmtBRLExato(c.taxa_hora_venda)}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid-kpi secao">
        {kpis.map((k) => (
          <div className="card kpi" key={k.rotulo}>
            <div className="rotulo linha-flex" style={{ gap: 7 }}>
              <Icone d={k.icone} size={15} strokeWidth={2} />
              {k.rotulo}
            </div>
            <div className="valor" style={{ fontSize: 28, lineHeight: '32px', color: k.cor }}>{k.valor}</div>
            <div className="detalhe">{k.detalhe}</div>
          </div>
        ))}
      </div>

      <div className="card secao">
        <div className="card-cabecalho">
          <h2 className="card-titulo-secao">Alocações ativas</h2>
          <span className="texto-3 mono" style={{ fontSize: 12 }}>
            {c.alocacoes_ativas.length} {c.alocacoes_ativas.length === 1 ? 'alocação' : 'alocações'}
          </span>
        </div>
        <div className="card-corpo" style={{ paddingTop: 12 }}>
          {c.alocacoes_ativas.length === 0 ? (
            <EstadoVazio
              icone={IC_VAZIO}
              titulo="Nenhuma alocação ativa"
              descricao="Este consultor não está alocado em nenhuma fase no momento. Aloque-o a partir da tela de um projeto para gerar receita prevista."
              barras={false}
            />
          ) : (
            <table className="tabela">
              <thead>
                <tr>
                  <th>Projeto</th>
                  <th>Fase</th>
                  <th>Período</th>
                  <th className="num">h/semana</th>
                  <th className="num">Taxa venda</th>
                  <th className="num">Horas prev.</th>
                  <th className="num">Horas real.</th>
                </tr>
              </thead>
              <tbody>
                {c.alocacoes_ativas.map((a) => {
                  const abaixo = a.horas_realizadas < a.horas_previstas
                  return (
                    <tr key={a.alocacao_id}>
                      <td>
                        <Link className="link" to={`/projetos/${a.projeto_id}`}>{a.projeto}</Link>
                      </td>
                      <td>
                        <span className={`badge ${corFase(a.fase)}`} style={{ textTransform: 'uppercase' }}>{a.fase}</span>
                      </td>
                      <td className="mono texto-2" style={{ fontSize: 12.5 }}>{fmtData(a.data_inicio)} – {fmtData(a.data_fim)}</td>
                      <td className="num mono">{fmtHoras(a.horas_semana)}</td>
                      <td className="num mono">{fmtBRLExato(a.taxa_hora_venda)}</td>
                      <td className="num mono">{fmtHoras(a.horas_previstas)}</td>
                      <td className="num mono" style={abaixo ? { color: 'var(--vermelho)' } : undefined}>{fmtHoras(a.horas_realizadas)}</td>
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
