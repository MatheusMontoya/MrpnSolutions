import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
// Fonte self-hosted (bundlada pelo Vite, sem CDN em runtime).
// Figtree: humanista de bojos circulares — o registro arredondado dos SaaS de
// referência (ClickUp/Productive) sem perder densidade de ferramenta. Família
// única: os números usam as figuras tabulares dela, sem monoespaçado nem reserva.
import '@fontsource-variable/figtree'
import App from './App'
import { SessaoProvider } from './sessao'
import { TemaProvider } from './tema'
import './styles.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <TemaProvider>
        <SessaoProvider>
          <App />
        </SessaoProvider>
      </TemaProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
