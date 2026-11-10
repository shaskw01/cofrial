import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, NavLink, Navigate, Outlet, useLocation } from 'react-router-dom'
import { api } from '../api'
import { Cargando, Logo } from '../componentes/Basicos'
import { inicioSegunRol, useSesion } from '../contexto'

// Que ve cada rol (CLAUDE.md): vendedor = CRM; despachador = pedidos, despachos y flota; administrador = todo.
export const SECCIONES = [
  { ruta: 'dashboard', nombre: 'Dashboard', roles: ['administrador'] },
  { ruta: 'pedidos', nombre: 'Pedidos', roles: ['administrador', 'vendedor', 'despachador'] },
  { ruta: 'pipeline', nombre: 'Pipeline comercial', roles: ['administrador', 'vendedor'] },
  { ruta: 'clientes', nombre: 'Clientes', roles: ['administrador', 'vendedor'] },
  { ruta: 'prospectos', nombre: 'Prospectos', roles: ['administrador', 'vendedor'] },
  { ruta: 'requerimientos', nombre: 'Requerimientos', roles: ['administrador', 'vendedor'] },
  { ruta: 'flota', nombre: 'Flota', roles: ['administrador', 'despachador'] },
]

const NOMBRE_ROL = { administrador: 'Administración', vendedor: 'Ventas', despachador: 'Despacho' }

/** Carga datos de la API; `cadaMs` los vuelve a pedir solos (flota, pedidos). */
export function useDatos(ruta, { params, cadaMs } = {}) {
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')
  const clave = JSON.stringify(params || {})
  const vigente = useRef(0)

  const recargar = useCallback(async () => {
    const turno = ++vigente.current
    try {
      const r = await api(ruta, { params: JSON.parse(clave) })
      if (turno === vigente.current) {
        setDatos(r)
        setError('')
      }
    } catch (e) {
      if (turno === vigente.current) setError(e.message)
    }
  }, [ruta, clave])

  useEffect(() => {
    recargar()
    if (!cadaMs) return undefined
    const id = setInterval(recargar, cadaMs)
    return () => clearInterval(id)
  }, [recargar, cadaMs])

  return { datos, error, recargar }
}

export function Encabezado({ titulo, children, detalle }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-4xl">{titulo}</h1>
        {detalle && <p className="mt-1 text-pizarra">{detalle}</p>}
      </div>
      <div className="flex flex-wrap items-center gap-2">{children}</div>
    </div>
  )
}

export function SoloRoles({ roles, children }) {
  const { usuario } = useSesion()
  if (!roles.includes(usuario.rol)) return <Navigate to={inicioSegunRol(usuario)} replace />
  return children
}

export default function Panel() {
  const { usuario, cargando, salir, esInterno } = useSesion()
  const { pathname } = useLocation()

  if (cargando) return <Cargando />
  if (!usuario) return <Navigate to={`/ingresar?volver=${pathname}`} replace />
  if (!esInterno) return <Navigate to="/" replace />

  const secciones = SECCIONES.filter((s) => s.roles.includes(usuario.rol))
  return (
    <div className="min-h-screen md:grid md:grid-cols-[14rem_1fr]">
      <aside className="flex flex-col bg-camara text-white md:sticky md:top-0 md:h-screen">
        <div className="px-4 pt-5 pb-3">
          <Link to="/" aria-label="Cofrial, ir a la tienda">
            <Logo claro />
          </Link>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-2 pb-2 md:flex-col md:overflow-visible">
          {secciones.map((s) => (
            <NavLink
              key={s.ruta}
              to={`/panel/${s.ruta}`}
              className={({ isActive }) =>
                `rounded px-3 py-2 font-semibold whitespace-nowrap ${
                  isActive ? 'bg-white text-camara' : 'text-white/75 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              {s.nombre}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto hidden border-t border-white/15 px-4 py-4 text-sm md:block">
          <p className="font-semibold">{usuario.nombre}</p>
          <p className="text-white/60">{NOMBRE_ROL[usuario.rol]}</p>
          <div className="mt-3 flex flex-col items-start gap-1.5">
            <Link to="/" className="text-white/75 underline hover:text-white">
              Ver la tienda
            </Link>
            <button type="button" onClick={salir} className="text-white/75 underline hover:text-white">
              Cerrar sesión
            </button>
          </div>
        </div>
      </aside>

      <div className="min-w-0">
        <div className="flex items-center justify-between border-b border-hielo bg-white px-4 py-2 text-sm md:hidden">
          <span>
            {usuario.nombre}, {NOMBRE_ROL[usuario.rol]}
          </span>
          <button type="button" onClick={salir} className="font-semibold underline">
            Cerrar sesión
          </button>
        </div>
        <main className="px-4 py-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
