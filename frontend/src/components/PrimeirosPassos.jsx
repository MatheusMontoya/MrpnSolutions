import { Link } from 'react-router-dom'
import Icone from './Icone'

const IC_OK = ['M20 6 9 17l-5-5']

/* Ordem em que o produto depende de cada coisa. Não é uma lista de features:
 * sem consultor não há taxa, sem taxa não há receita, sem alocação o motor não
 * tem o que calcular — e é por isso que o dashboard nasce zerado. */
const PASSOS = [
  {
    chave: 'consultores',
    titulo: 'Cadastre a equipe',
    porque: 'A taxa de custo e a de venda de cada consultor são a base de toda receita e margem.',
    para: '/consultores?novo=1',
    rotulo: 'Cadastrar consultor',
  },
  {
    chave: 'clientes',
    titulo: 'Cadastre o cliente',
    porque: 'Todo projeto pertence a um cliente — é por ele que o faturamento é agrupado.',
    para: '/clientes?novo=1',
    rotulo: 'Cadastrar cliente',
  },
  {
    chave: 'projetos',
    titulo: 'Crie o projeto',
    porque: 'As seis fases do SAP Activate já vêm montadas, com entregas e quality gates.',
    para: '/projetos?novo=1',
    rotulo: 'Criar projeto',
  },
  {
    chave: 'alocacoes',
    titulo: 'Aloque o consultor na fase',
    porque: 'É a alocação que informa horas/semana e taxa — daqui sai a receita prevista.',
    para: '/projetos',
    rotulo: 'Abrir projetos',
  },
  {
    chave: 'apontamentos',
    titulo: 'Registre as horas da semana',
    porque: 'Hora aprovada vira medição, medição vira nota. É o ciclo que fecha o mês.',
    para: '/apontamento',
    rotulo: 'Abrir apontamento',
  },
]

/** Roteiro de primeiro uso: substitui o painel de zeros enquanto não há dado.
 *
 * O sistema entra em produção vazio, e o dashboard vazio é honesto mas mudo —
 * mostra R$ 0,00 em seis cartões e nenhuma instrução sobre o que fazer.
 */
export default function PrimeirosPassos({ contagem }) {
  const feitos = PASSOS.filter((p) => (contagem[p.chave] ?? 0) > 0).length
  const proximo = PASSOS.find((p) => (contagem[p.chave] ?? 0) === 0)

  return (
    <div className="card primeiros-passos">
      <div className="pp-cabecalho">
        <div>
          <h2 className="card-titulo">Comece por aqui</h2>
          <p className="texto-2" style={{ margin: '4px 0 0', fontSize: 13.5 }}>
            O RunRate calcula tudo a partir do que você cadastra. Ainda não há dado
            suficiente para os números acima — siga esta ordem.
          </p>
        </div>
        <span className="pp-contador">{feitos} de {PASSOS.length}</span>
      </div>

      <ol className="pp-lista">
        {PASSOS.map((passo, i) => {
          const feito = (contagem[passo.chave] ?? 0) > 0
          const atual = passo === proximo
          return (
            <li key={passo.chave} className={`pp-item${feito ? ' feito' : ''}${atual ? ' atual' : ''}`}>
              <span className="pp-marca" aria-hidden="true">
                {feito ? <Icone d={IC_OK} size={13} strokeWidth={2.5} /> : i + 1}
              </span>
              <div className="pp-texto">
                <strong>{passo.titulo}</strong>
                <span className="texto-2">{passo.porque}</span>
              </div>
              {feito ? (
                /* tinta 2, não 3: "2 cadastrados" é a confirmação de que o
                   passo foi cumprido — informação, não enfeite */
                <span className="pp-estado texto-2">
                  {contagem[passo.chave]} cadastrado{contagem[passo.chave] > 1 ? 's' : ''}
                </span>
              ) : (
                <Link
                  to={passo.para}
                  className={`botao botao-pequeno ${atual ? 'botao-primario' : 'botao-secundario'}`}
                >
                  {passo.rotulo}
                </Link>
              )}
            </li>
          )
        })}
      </ol>

      <p className="pp-rodape texto-3">
        Falta dar acesso ao time? Os logins ficam em{' '}
        <Link className="link" to="/configuracoes">Configurações → Usuários</Link>.
      </p>
    </div>
  )
}
