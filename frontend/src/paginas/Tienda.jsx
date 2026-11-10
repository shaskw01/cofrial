import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { Logo } from '../componentes/Basicos'
import { inicioSegunRol, useCarrito, useCatalogo, useSesion } from '../contexto'

function SelectorPerfil() {
  const { usuario, esInterno } = useSesion()
  const { tipoPrecio, setTipoVista } = useCatalogo()
  const navegar = useNavigate()

  if (usuario?.rol === 'cliente') {
    return (
      <p className="text-sm text-pizarra">
        {usuario.tipo_cliente === 'B2B' ? 'Lista de precios institucional' : 'Precios público general'}
        <span className="block font-semibold text-camara">{usuario.nombre}</span>
      </p>
    )
  }

  const elegir = (tipo) => {
    if (esInterno) setTipoVista(tipo)
    else if (tipo === 'B2B') navegar('/ingresar?perfil=institucion')
  }
  const opcion = (tipo, texto) => (
    <button
      type="button"
      aria-pressed={tipoPrecio === tipo}
      onClick={() => elegir(tipo)}
      className={`rounded-[3px] px-3 py-1.5 text-sm font-semibold ${
        tipoPrecio === tipo ? 'bg-camara text-white' : 'text-pizarra hover:text-camara'
      }`}
    >
      {texto}
    </button>
  )
  return (
    <div className="inline-flex rounded border border-hielo bg-white p-0.5" role="group" aria-label="Perfil de compra">
      {opcion('B2C', 'Persona')}
      {opcion('B2B', 'Empresa o institución')}
    </div>
  )
}

export default function Tienda() {
  const { usuario, salir, esInterno, esCliente } = useSesion()
  const { lineas } = useCarrito()
  const enlace = ({ isActive }) =>
    `py-1 font-semibold ${isActive ? 'text-camara underline decoration-2 underline-offset-8' : 'text-pizarra hover:text-camara'}`

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-hielo bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3">
          <Link to="/" aria-label="Cofrial, ir al catálogo">
            <Logo />
          </Link>
          <SelectorPerfil />
          <nav className="ml-auto flex flex-wrap items-center gap-x-5 gap-y-2">
            <NavLink to="/" end className={enlace}>
              Catálogo
            </NavLink>
            {esCliente && (
              <NavLink to="/mis-pedidos" className={enlace}>
                Mis pedidos
              </NavLink>
            )}
            {esInterno && (
              <NavLink to={inicioSegunRol(usuario)} className={enlace}>
                Panel interno
              </NavLink>
            )}
            {usuario ? (
              <button type="button" onClick={salir} className="py-1 font-semibold text-pizarra hover:text-camara">
                Cerrar sesión
              </button>
            ) : (
              <NavLink to="/ingresar" className={enlace}>
                Ingresar
              </NavLink>
            )}
            <Link to="/carrito" className="boton boton-primario">
              Carrito
              <span className="cifra rounded-sm bg-white/15 px-1.5 text-base">{lineas}</span>
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-hielo bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap justify-between gap-2 px-4 py-5 text-sm text-pizarra">
          <span>Cofrial SpA, distribución en cadena de frío. Temuco, La Araucanía.</span>
          <span>Prototipo académico, Transformación Digital, INACAP Temuco.</span>
        </div>
      </footer>
    </div>
  )
}
