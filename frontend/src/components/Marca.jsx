/* Símbolo RunRate — "Everything fits".
 *
 * Quatro peças em bracket formam um quadrado: PESSOAS (topo), PROCESSOS
 * (esquerda), FINANÇAS (direita) e ENTREGA (base). O quadrante superior-direito
 * é sempre o azul elétrico da marca; os outros três acompanham a superfície
 * (grafite no claro, branco sobre fundo escuro).
 */

// bracket do quadrante superior-esquerdo; os demais são rotações de 90°
const BRACKET =
  'M1.5 5 A3.5 3.5 0 0 1 5 1.5 H9.9 A1.1 1.1 0 0 1 11 2.6 V4.9 A1.1 1.1 0 0 1 9.9 6 ' +
  'H7.1 A1.1 1.1 0 0 0 6 7.1 V9.9 A1.1 1.1 0 0 1 4.9 11 H2.6 A1.1 1.1 0 0 1 1.5 9.9 Z'

export default function Marca({ size = 28, variante = 'cor', title }) {
  // 'cor' acompanha a tinta do tema (grafite no claro, quase-branco no escuro,
  // onde o próprio #1E2430 vira a superfície e sumiria); 'branco' é para
  // fundos escuros fixos, como o hero do login.
  const base = variante === 'branco' ? '#ffffff' : 'var(--texto, #1e2430)'
  const azul = 'var(--azul, #0a78f0)'

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      role={title ? 'img' : 'presentation'}
      aria-label={title}
      aria-hidden={title ? undefined : 'true'}
      focusable="false"
    >
      {/* PESSOAS · superior-esquerdo */}
      <path d={BRACKET} fill={base} />
      {/* FINANÇAS · superior-direito — a peça que fecha o encaixe */}
      <path d={BRACKET} fill={azul} transform="rotate(90 12 12)" />
      {/* ENTREGA · inferior-direito */}
      <path d={BRACKET} fill={base} transform="rotate(180 12 12)" />
      {/* PROCESSOS · inferior-esquerdo */}
      <path d={BRACKET} fill={base} transform="rotate(270 12 12)" />
    </svg>
  )
}

/** Assinatura completa: símbolo + nome + endosso da casa. */
export function MarcaCompleta({ size = 30, variante = 'cor', endosso = true }) {
  return (
    <span className={`marca-assinatura${variante === 'branco' ? ' na-escura' : ''}`}>
      <Marca size={size} variante={variante} />
      <span className="marca-texto">
        <span className="marca-nome">RunRate</span>
        {endosso && <span className="marca-endosso">by MRPN Solutions</span>}
      </span>
    </span>
  )
}
