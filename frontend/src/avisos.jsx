import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'

/* Retorno de ação — o aviso curto que aparece depois de salvar, remover ou falhar.
 *
 * Existe porque as ações da tela eram mudas: `await api.del(...)` sem try/catch
 * significava que um 403 ou uma queda de rede simplesmente não faziam nada, e o
 * usuário ficava clicando no mesmo botão achando que o clique não pegou.
 *
 * É um singleton de módulo, não um contexto: qualquer arquivo chama
 * `avisar.erro(msg)` sem que a página precise receber prop nenhuma.
 */
let proximoId = 1
const ouvintes = new Set()
let fila = []

function emitir(texto, tipo, duracao) {
  const id = proximoId++
  fila = [...fila, { id, texto, tipo }]
  ouvintes.forEach((f) => f(fila))
  setTimeout(() => {
    fila = fila.filter((a) => a.id !== id)
    ouvintes.forEach((f) => f(fila))
  }, duracao)
  return id
}

export const avisar = {
  ok: (texto) => emitir(texto, 'ok', 3500),
  // o erro fica bem mais tempo: é o que a pessoa precisa ler e, às vezes, copiar
  erro: (texto) => emitir(String(texto?.message || texto || 'Algo deu errado'), 'erro', 8000),
}

/** Executa uma ação de escrita mostrando a falha em vez de engoli-la. */
export async function comAviso(acao, { sucesso } = {}) {
  try {
    const r = await acao()
    if (sucesso) avisar.ok(sucesso)
    return r
  } catch (e) {
    avisar.erro(e)
    return undefined
  }
}

/** Pergunta antes e só então executa. Para dinheiro e para o que não tem desfazer. */
export async function confirmarE(pergunta, acao, opcoes) {
  if (!window.confirm(pergunta)) return undefined
  return comAviso(acao, opcoes)
}

export default function Avisos() {
  const [lista, setLista] = useState(fila)

  useEffect(() => {
    ouvintes.add(setLista)
    return () => { ouvintes.delete(setLista) }
  }, [])

  if (!lista.length) return null

  return createPortal(
    <div className="avisos" role="status" aria-live="polite">
      {lista.map((a) => (
        <div key={a.id} className={`aviso aviso-${a.tipo}`}>
          <span className="aviso-marca" aria-hidden="true" />
          <span>{a.texto}</span>
        </div>
      ))}
    </div>,
    document.body,
  )
}
