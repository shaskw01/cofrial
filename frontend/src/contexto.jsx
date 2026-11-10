import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, guardarToken, hayToken } from './api'

// ------------------------------------------------------------------ sesion
const SesionCtx = createContext(null)
export const useSesion = () => useContext(SesionCtx)

export const ROLES_INTERNOS = ['administrador', 'vendedor', 'despachador']

export function inicioSegunRol(usuario) {
  if (!usuario || usuario.rol === 'cliente') return '/'
  if (usuario.rol === 'administrador') return '/panel/dashboard'
  return usuario.rol === 'vendedor' ? '/panel/pipeline' : '/panel/pedidos'
}

function SesionProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [cargando, setCargando] = useState(hayToken())

  useEffect(() => {
    if (hayToken()) {
      api('/auth/me')
        .then(setUsuario)
        .catch(() => setUsuario(null))
        .finally(() => setCargando(false))
    }
    const vencida = () => setUsuario(null)
    window.addEventListener('cofrial:sesion-vencida', vencida)
    return () => window.removeEventListener('cofrial:sesion-vencida', vencida)
  }, [])

  const ingresar = useCallback(async (email, password) => {
    const r = await api('/auth/login', { method: 'POST', body: { email, password } })
    guardarToken(r.access)
    setUsuario(r.usuario)
    return r.usuario
  }, [])

  const salir = useCallback(() => {
    guardarToken(null)
    setUsuario(null)
  }, [])

  const valor = useMemo(() => {
    const esInterno = Boolean(usuario) && ROLES_INTERNOS.includes(usuario.rol)
    return { usuario, cargando, ingresar, salir, esInterno, esCliente: usuario?.rol === 'cliente' }
  }, [usuario, cargando, ingresar, salir])
  return <SesionCtx.Provider value={valor}>{children}</SesionCtx.Provider>
}

// ------------------------------------------------------------------ catalogo
const CatalogoCtx = createContext(null)
export const useCatalogo = () => useContext(CatalogoCtx)

function CatalogoProvider({ children }) {
  const { usuario, cargando: cargandoSesion, esInterno } = useSesion()
  const [productos, setProductos] = useState([])
  const [categorias, setCategorias] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  // Solo el personal interno puede alternar la lista de precios que esta mirando
  const [tipoVista, setTipoVista] = useState('B2C')

  const recargar = useCallback(async () => {
    try {
      const [prods, cats] = await Promise.all([
        api('/productos', { params: { tipo: esInterno ? tipoVista : undefined } }),
        api('/categorias'),
      ])
      setProductos(prods)
      setCategorias(cats)
      setError('')
    } catch (e) {
      setError(e.message)
    } finally {
      setCargando(false)
    }
  }, [esInterno, tipoVista])

  useEffect(() => {
    if (!cargandoSesion) recargar()
  }, [cargandoSesion, usuario?.id_usuario, recargar])

  const tipoPrecio = usuario?.tipo_cliente || (esInterno ? tipoVista : 'B2C')
  const valor = useMemo(
    () => ({ productos, categorias, cargando, error, recargar, tipoPrecio, tipoVista, setTipoVista }),
    [productos, categorias, cargando, error, recargar, tipoPrecio, tipoVista],
  )
  return <CatalogoCtx.Provider value={valor}>{children}</CatalogoCtx.Provider>
}

// ------------------------------------------------------------------ carrito
const CarritoCtx = createContext(null)
export const useCarrito = () => useContext(CarritoCtx)
const CLAVE_CARRITO = 'cofrial_carrito'

function CarritoProvider({ children }) {
  // { [id_producto]: cantidad }. Los precios no se guardan: salen siempre del catalogo vigente.
  const [items, setItems] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(CLAVE_CARRITO)) || {}
    } catch {
      return {}
    }
  })

  useEffect(() => {
    localStorage.setItem(CLAVE_CARRITO, JSON.stringify(items))
  }, [items])

  const fijar = useCallback((id, cantidad) => {
    setItems((previo) => {
      const nuevo = { ...previo }
      if (cantidad > 0) nuevo[id] = cantidad
      else delete nuevo[id]
      return nuevo
    })
  }, [])
  const vaciar = useCallback(() => setItems({}), [])

  const valor = useMemo(
    () => ({ items, fijar, vaciar, lineas: Object.keys(items).length }),
    [items, fijar, vaciar],
  )
  return <CarritoCtx.Provider value={valor}>{children}</CarritoCtx.Provider>
}

export function Proveedores({ children }) {
  return (
    <SesionProvider>
      <CatalogoProvider>
        <CarritoProvider>{children}</CarritoProvider>
      </CatalogoProvider>
    </SesionProvider>
  )
}
