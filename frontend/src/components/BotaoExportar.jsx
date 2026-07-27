import { useState } from 'react'
import { baixarArquivo } from '../api'
import Icone from './Icone'

const IC_BAIXAR = ['M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4', 'M7 10l5 5 5-5', 'M12 15V3']

/** Baixa o CSV do recurso (`/api/export/{recurso}.csv`) — separador ';' e
 * BOM, pronto para o Excel pt-BR. Usa fetch autenticado (token no header). */
export default function BotaoExportar({ recurso, rotulo = 'Exportar CSV' }) {
  const [ocupado, setOcupado] = useState(false)

  const baixar = async () => {
    setOcupado(true)
    try {
      await baixarArquivo(`/export/${recurso}.csv`, `${recurso}.csv`)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <button
      type="button"
      className="botao botao-fantasma botao-pequeno"
      onClick={baixar}
      disabled={ocupado}
      title={`Baixar ${recurso}.csv (Excel)`}
    >
      <Icone d={IC_BAIXAR} size={14} /> {ocupado ? 'Baixando…' : rotulo}
    </button>
  )
}
