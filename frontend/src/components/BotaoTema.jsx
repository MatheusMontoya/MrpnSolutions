import Icone from './Icone'
import { useTema } from '../tema'

const IC = {
  sol: ['M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z', 'M12 1v2', 'M12 21v2', 'M4.2 4.2l1.4 1.4',
        'M18.4 18.4l1.4 1.4', 'M1 12h2', 'M21 12h2', 'M4.2 19.8l1.4-1.4', 'M18.4 5.6l1.4-1.4'],
  lua: ['M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z'],
}

/** Alterna claro/escuro em um clique, na topbar.
 *
 * O controle de três estados (Claro/Escuro/Sistema) já existia no menu do
 * avatar, mas ninguém abre um menu de conta procurando tema — a prova é que o
 * dono do produto concluiu que "só existia o modo escuro". Descoberta se
 * resolve com presença, não com mais opções: aqui fica o caso comum, e o menu
 * segue guardando o 'Sistema' para quem quiser.
 */
export default function BotaoTema() {
  const { efetivo, escolher } = useTema()
  const vaiPara = efetivo === 'escuro' ? 'claro' : 'escuro'

  return (
    <button
      className="icone-botao"
      type="button"
      onClick={() => escolher(vaiPara)}
      aria-label={`Mudar para o tema ${vaiPara}`}
      title={`Tema ${vaiPara}`}
    >
      <Icone d={efetivo === 'escuro' ? IC.sol : IC.lua} size={17} />
    </button>
  )
}
