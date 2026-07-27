const brl = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
const brlCents = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const numero = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 })

export const fmtBRL = (v) => brl.format(v ?? 0)
export const fmtBRLExato = (v) => brlCents.format(v ?? 0)
export const fmtHoras = (v) => `${numero.format(v ?? 0)}h`
export const fmtPct = (v) => `${Math.round((v ?? 0) * 100)}%`

const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']

// "2026-07" → "jul/26"
export const fmtMes = (m) => {
  const [ano, mes] = m.split('-')
  return `${MESES[Number(mes) - 1]}/${ano.slice(2)}`
}

// "2026-07-10" → "10/07/26" (sem fuso: trata como data local)
export const fmtData = (iso) => {
  const [ano, mes, dia] = iso.split('-')
  return `${dia}/${mes}/${ano.slice(2)}`
}

export const fmtDataCurta = (iso) => {
  const [, mes, dia] = iso.split('-')
  return `${dia}/${mes}`
}

const DIAS_SEMANA = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']
export const nomeDiaSemana = (idx) => DIAS_SEMANA[idx]

export const SENIORIDADE = { junior: 'Júnior', pleno: 'Pleno', senior: 'Sênior' }
export const STATUS_PROJETO = { ativo: 'Ativo', pausado: 'Pausado', encerrado: 'Encerrado' }

// Mapa canônico fase → classe de badge (mesma cor em todas as telas).
export const CORES_FASE = {
  Discover: 'badge-azul',
  Prepare: 'badge-azul',
  Explore: 'badge-azul',
  Realize: 'badge-laranja',
  Deploy: 'badge-azul',
  Run: 'badge-verde',
}
export const corFase = (nome) => CORES_FASE[nome] ?? 'badge-cinza'

// Iniciais das 2 primeiras palavras do nome — para avatares.
export const iniciais = (nome) =>
  (nome || '').split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase()

// Código de projeto derivado só para exibição (não existe no backend):
// "PRJ-{ano do início}-{id com 3 dígitos}", ex.: PRJ-2026-014.
export const codigoProjeto = (id, dataInicioIso) => {
  const ano = dataInicioIso ? dataInicioIso.slice(0, 4) : '----'
  return `PRJ-${ano}-${String(id).padStart(3, '0')}`
}
