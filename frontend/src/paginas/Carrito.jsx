import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { Aviso, Campo, Cantidad, Cargando } from '../componentes/Basicos'
import { EtiquetaZona } from '../componentes/Temperatura'
import { useCarrito, useCatalogo, useSesion } from '../contexto'
import { fechaISO, pesos, unidad } from '../formato'

const manana = () => fechaISO(new Date(Date.now() + 24 * 3600 * 1000))

export default function Carrito() {
  const { usuario, esCliente, esInterno } = useSesion()
  const { productos, cargando, recargar, tipoPrecio } = useCatalogo()
  const { items, fijar, vaciar } = useCarrito()
  const navegar = useNavigate()

  const [direccion, setDireccion] = useState('')
  const [fechaEntrega, setFechaEntrega] = useState(manana)
  const [numeroOc, setNumeroOc] = useState('')
  const [error, setError] = useState('')
  const [faltantes, setFaltantes] = useState([])
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    if (usuario?.direccion_despacho) setDireccion(usuario.direccion_despacho)
  }, [usuario?.direccion_despacho])

  const lineas = useMemo(
    () =>
      productos
        .filter((p) => items[p.id_producto])
        .map((p) => ({ ...p, cantidad: items[p.id_producto], subtotal: (p.precio || 0) * items[p.id_producto] })),
    [productos, items],
  )
  const total = lineas.reduce((s, l) => s + l.subtotal, 0)
  const esB2B = usuario?.tipo_cliente === 'B2B'

  const confirmar = async (e) => {
    e.preventDefault()
    setEnviando(true)
    setError('')
    setFaltantes([])
    try {
      const pedido = await api('/pedidos', {
        method: 'POST',
        body: {
          items: lineas.map((l) => ({ id_producto: l.id_producto, cantidad: l.cantidad })),
          fecha_entrega_solicitada: fechaEntrega,
          direccion_entrega: direccion,
          numero_oc: esB2B ? numeroOc : undefined,
        },
      })
      vaciar()
      recargar()
      navegar('/mis-pedidos', { state: { creado: pedido.id_pedido } })
    } catch (err) {
      if (err.status === 409 && err.data?.faltantes) {
        setFaltantes(err.data.faltantes)
        recargar()
      }
      setError(err.message)
      setEnviando(false)
    }
  }

  if (cargando) return <Cargando />

  if (lineas.length === 0) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-14">
        <h1 className="text-4xl">Tu carrito está vacío</h1>
        <p className="mt-2 text-pizarra">Agrega productos desde el catálogo para armar tu pedido.</p>
        <Link to="/" className="boton boton-primario mt-6">
          Ir al catálogo
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 lg:grid-cols-[1fr_22rem]">
      <section>
        <h1 className="text-4xl">Carrito</h1>
        <p className="mt-1 text-pizarra">
          {tipoPrecio === 'B2B' ? 'Precios de la lista institucional.' : 'Precios para público general.'}
        </p>
        <ul className="mt-6 divide-y divide-hielo border-y border-hielo">
          {lineas.map((l) => (
            <li key={l.id_producto} className="flex flex-wrap items-center gap-x-6 gap-y-3 py-4">
              <div className="min-w-48 flex-1">
                <p className="font-rotulo text-xl font-semibold">{l.nombre}</p>
                <EtiquetaZona categoria={l.categoria} />
                <p className="text-sm text-pizarra">
                  {pesos(l.precio)} / {unidad(l.unidad_medida)}
                </p>
              </div>
              <Cantidad
                valor={l.cantidad}
                max={l.stock_disponible}
                onCambiar={(n) => fijar(l.id_producto, n)}
                etiqueta={`Cantidad de ${l.nombre}`}
              />
              <p className="cifra w-28 text-right text-2xl font-semibold">{pesos(l.subtotal)}</p>
              <button
                type="button"
                className="text-sm font-semibold text-pizarra underline hover:text-ruptura"
                onClick={() => fijar(l.id_producto, 0)}
              >
                Quitar
              </button>
            </li>
          ))}
        </ul>
        {faltantes.length > 0 && (
          <div className="mt-4">
            <Aviso>
              <p className="font-semibold">No alcanza el stock para estos productos. Ajusta las cantidades:</p>
              <ul className="mt-1 list-disc pl-5">
                {faltantes.map((f) => (
                  <li key={f.id_producto}>
                    {f.nombre}: pediste {f.solicitado} y quedan {f.disponible}.
                  </li>
                ))}
              </ul>
            </Aviso>
          </div>
        )}
      </section>

      <aside className="caja self-start p-5">
        <div className="flex items-baseline justify-between">
          <h2 className="text-2xl">Total</h2>
          <p className="cifra text-4xl font-semibold">{pesos(total)}</p>
        </div>

        {!usuario && (
          <div className="mt-5">
            <p className="text-pizarra">Para confirmar el pedido necesitas ingresar con tu cuenta.</p>
            <Link to="/ingresar?volver=/carrito" className="boton boton-primario mt-3 w-full">
              Ingresar para comprar
            </Link>
          </div>
        )}
        {esInterno && (
          <p className="mt-5 text-pizarra">
            Estás con una cuenta interna. Los pedidos de la tienda se confirman con una cuenta de cliente.
          </p>
        )}
        {esCliente && (
          <form onSubmit={confirmar} className="mt-5 space-y-4">
            {faltantes.length === 0 && <Aviso>{error}</Aviso>}
            <Campo etiqueta="Dirección de entrega">
              <input
                className="campo"
                required
                maxLength={200}
                value={direccion}
                onChange={(e) => setDireccion(e.target.value)}
              />
            </Campo>
            <Campo etiqueta="Fecha de entrega">
              <input
                className="campo"
                type="date"
                required
                min={fechaISO(new Date())}
                value={fechaEntrega}
                onChange={(e) => setFechaEntrega(e.target.value)}
              />
            </Campo>
            {esB2B && (
              <Campo etiqueta="N.º de orden de compra" ayuda="La orden de compra de tu institución para este pedido.">
                <input
                  className="campo"
                  required
                  maxLength={30}
                  placeholder="Ej.: OC-2026-0042"
                  value={numeroOc}
                  onChange={(e) => setNumeroOc(e.target.value)}
                />
              </Campo>
            )}
            <button type="submit" className="boton boton-primario w-full" disabled={enviando}>
              {enviando ? 'Confirmando…' : 'Confirmar pedido'}
            </button>
          </form>
        )}
      </aside>
    </div>
  )
}
