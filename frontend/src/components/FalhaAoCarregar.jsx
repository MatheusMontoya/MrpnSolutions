import Icone from './Icone'

const IC = {
  alerta: ['M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z',
           'M12 9v4', 'M12 17h.01'],
  recarregar: ['M3 12a9 9 0 1 0 3-6.7L3 8', 'M3 3v5h5'],
}

/** Falha de carregamento com caminho de volta.
 *
 * Antes, 20 páginas faziam `if (erro) return <div className="mensagem-erro">`:
 * a tela inteira sumia, sem menu, sem botão, e a única saída era F5. Um erro de
 * rede momentâneo custava a navegação inteira ao usuário.
 */
export default function FalhaAoCarregar({ erro, aoTentarDeNovo }) {
  return (
    <div className="falha-carregar" role="alert">
      <span className="falha-icone" aria-hidden="true">
        <Icone d={IC.alerta} size={22} />
      </span>
      <h2>Não foi possível carregar</h2>
      <p className="texto-2">{erro || 'A resposta do servidor não chegou.'}</p>
      <div className="linha-flex" style={{ gap: 8, marginTop: 4 }}>
        {aoTentarDeNovo && (
          <button className="botao botao-primario" onClick={aoTentarDeNovo}>
            <Icone d={IC.recarregar} size={15} /> Tentar de novo
          </button>
        )}
        <button className="botao botao-fantasma" onClick={() => window.location.reload()}>
          Recarregar a página
        </button>
      </div>
      <p className="texto-3" style={{ fontSize: 12.5, marginTop: 10 }}>
        Se continuar, o servidor pode estar fora do ar. O menu à esquerda continua
        funcionando — dá para seguir por outra tela.
      </p>
    </div>
  )
}
