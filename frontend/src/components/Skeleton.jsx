/** Skeleton de carregamento — evita spinner no meio do conteúdo e layout shift. */
export function Bloco({ altura = 120, largura = '100%', style }) {
  return <div className="skeleton" style={{ height: altura, width: largura, ...style }} aria-hidden="true" />
}

export function SkeletonPagina({ kpis = false }) {
  return (
    <div className="skeleton-pagina" role="status" aria-label="Carregando">
      <Bloco altura={30} largura={280} />
      {kpis && (
        <div className="skeleton-kpis">
          <Bloco altura={86} /><Bloco altura={86} /><Bloco altura={86} /><Bloco altura={86} />
        </div>
      )}
      <Bloco altura={300} />
      <Bloco altura={220} />
    </div>
  )
}
