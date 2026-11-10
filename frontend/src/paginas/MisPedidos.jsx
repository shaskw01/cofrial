import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { api } from '../api'
import { Aviso, Cargando, Estado } from '../componentes/Basicos'
import { fecha, fechaHora, pesos, unidad } from '../formato'

const PASOS = ['Recibido', 'En preparación', 'Despachado', 'Entregado']

/** Avance del pedido: los pasos SI son una secuencia, por eso van numerados. */
export function Avance({ estado }) {
  if (estado === 'Rechazado') return <Estado nombre="Rechazado" />
  const actual = PASOS.indexOf(estado)
  return (
    <ol className="flex flex-wrap gap-x-1 gap-y-2">
      {PASOS.map((paso, i) => (
        <li key={paso} className="flex items-center gap-1">
          <span
            className={`cifra flex h-6 w-6 items-center justify-center rounded-full text-sm font-semibold ${
              i <= actual ? 'bg-camara text-white' : 'border border-hielo text-pizarra'
            }`}
          >
            {i + 1}
          </span>
          <span className={`text-sm ${i === actual ? 'font-semibold' : i < actual ? '' : 'text-pizarra'}`}>{paso}</span>
          {i < PASOS.length - 1 && <span className={`mx-1 h-px w-5 ${i < actual ? 'bg-camara' : 'bg-hielo'}`} />}
        </li>
      ))}
    </ol>
  )
}

export function DetallePedido({ pedido }) {
  return (
    <table className="w-full text-left">
      <tbody>
        {pedido.detalles.map((d) => (
          <tr key={d.id_producto} className="border-t border-hielo">
            <td className="py-1.5 pr-3">{d.nombre}</td>
            <td className="cifra py-1.5 pr-3 text-right whitespace-nowrap">
              {d.cantidad} {unidad(d.unidad_medida, d.cantidad)} × {pesos(d.precio_unitario)}
            </td>
            <td className="cifra py-1.5 text-right font-semibold">{pesos(d.subtotal)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default function MisPedidos() {
  const { state } = useLocation()
  const [pedidos, setPedidos] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api('/mis-pedidos')
      .then(setPedidos)
      .catch((e) => setError(e.message))
  }, [])

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-4xl">Mis pedidos</h1>
      <div className="mt-5 space-y-4">
        {state?.creado && (
          <Aviso tipo="ok">
            Pedido N.º {state.creado} confirmado. Te avisaremos aquí cuando pase a preparación y despacho.
          </Aviso>
        )}
        <Aviso>{error}</Aviso>
        {!pedidos && !error && <Cargando />}
        {pedidos?.length === 0 && (
          <p className="text-pizarra">
            Todavía no has hecho pedidos. <Link to="/" className="font-semibold underline">Ir al catálogo</Link>
          </p>
        )}
        {pedidos?.map((p) => (
          <article key={p.id_pedido} className={`caja p-5 ${state?.creado === p.id_pedido ? 'border-fresco' : ''}`}>
            <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
              <h2 className="text-2xl">Pedido N.º {p.id_pedido}</h2>
              <p className="cifra text-2xl font-semibold">{pesos(p.total)}</p>
            </div>
            <p className="mt-1 text-sm text-pizarra">
              Hecho el {fechaHora(p.fecha_creacion)}. Entrega solicitada para el {fecha(p.fecha_entrega_solicitada)} en{' '}
              {p.direccion_entrega}.{p.numero_oc && ` Orden de compra ${p.numero_oc}.`}
            </p>
            <div className="mt-4">
              <Avance estado={p.estado} />
            </div>
            {p.despacho && (
              <p className="mt-3 text-sm">
                {p.despacho.fecha_entrega ? 'Viajó' : 'Viaja'} en el camión <strong>{p.despacho.camion_id}</strong>, salió de bodega el{' '}
                {fechaHora(p.despacho.fecha_salida)}
                {p.despacho.fecha_entrega && ` y se entregó el ${fechaHora(p.despacho.fecha_entrega)}`}.
              </p>
            )}
            <details className="mt-4">
              <summary className="font-semibold">Ver los {p.detalles.length} productos</summary>
              <div className="mt-2">
                <DetallePedido pedido={p} />
              </div>
            </details>
          </article>
        ))}
      </div>
    </div>
  )
}
