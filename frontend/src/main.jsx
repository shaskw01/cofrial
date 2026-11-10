import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './index.css'
import { Cargando } from './componentes/Basicos'
import { Proveedores, inicioSegunRol, useSesion } from './contexto'
import Carrito from './paginas/Carrito'
import Ayuda from './paginas/Ayuda'
import Catalogo from './paginas/Catalogo'
import Ingresar from './paginas/Ingresar'
import MisPedidos from './paginas/MisPedidos'
import Tienda from './paginas/Tienda'
import Clientes from './panel/Clientes'
import Dashboard from './panel/Dashboard'
import Flota from './panel/Flota'
import Panel, { SECCIONES, SoloRoles } from './panel/Panel'
import Pedidos from './panel/Pedidos'
import Pipeline from './panel/Pipeline'
import Prospectos from './panel/Prospectos'
import Requerimientos from './panel/Requerimientos'

const PAGINAS = {
  dashboard: Dashboard,
  requerimientos: Requerimientos,
  pedidos: Pedidos, pipeline: Pipeline, clientes: Clientes, prospectos: Prospectos,
  flota: Flota,
}

function SoloCliente({ children }) {
  const { usuario, cargando, esCliente } = useSesion()
  if (cargando) return <Cargando />
  if (!usuario) return <Navigate to="/ingresar?volver=/mis-pedidos" replace />
  return esCliente ? children : <Navigate to={inicioSegunRol(usuario)} replace />
}

function InicioPanel() {
  const { usuario } = useSesion()
  return <Navigate to={inicioSegunRol(usuario)} replace />
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Proveedores>
        <Routes>
          <Route element={<Tienda />}>
            <Route index element={<Catalogo />} />
            <Route path="carrito" element={<Carrito />} />
            <Route path="ingresar" element={<Ingresar />} />
            <Route path="ayuda" element={<Ayuda />} />
            <Route
              path="mis-pedidos"
              element={
                <SoloCliente>
                  <MisPedidos />
                </SoloCliente>
              }
            />
          </Route>
          <Route path="panel" element={<Panel />}>
            <Route index element={<InicioPanel />} />
            {SECCIONES.map(({ ruta, roles }) => {
              const Pagina = PAGINAS[ruta]
              return (
                <Route
                  key={ruta}
                  path={ruta}
                  element={
                    <SoloRoles roles={roles}>
                      <Pagina />
                    </SoloRoles>
                  }
                />
              )
            })}
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Proveedores>
    </BrowserRouter>
  </StrictMode>,
)
