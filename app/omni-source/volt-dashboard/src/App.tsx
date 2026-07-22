import { BrowserRouter, Route, Routes } from 'react-router'
import { MotionConfig } from 'framer-motion'
import QueryProvider from './lib/query-provider'
import { CatalogProvider } from './lib/catalog-context'
import Layout from './components/Layout'
import Home from './pages/Home'

export default function App() {
  return (
    <QueryProvider>
      <CatalogProvider>
        <MotionConfig reducedMotion="user">
          <BrowserRouter>
            <Layout>
              <Routes>
                <Route path="/" element={<Home />} />
              </Routes>
            </Layout>
          </BrowserRouter>
        </MotionConfig>
      </CatalogProvider>
    </QueryProvider>
  )
}
