import { Fragment, useMemo, useState } from 'react'
import { api } from '../api'
import { Aviso, Campo, Cargando, Estado, Modal } from '../componentes/Basicos'
import { useSesion } from '../contexto'
import { fecha, fechaHora, pesos } from '../formato'
import { DetallePedido } from '../paginas/MisPedidos'
import { Encabezado, useDatos } from './Panel'

const ESTADOS = ['Recibido', 'En preparación', 'Despachado', 'Entregado', 'Rechazado']

function Despachar({ pedido, onCerrar, onListo }) {
  const { datos: camiones, error: errorCamiones } = useDatos('/camiones', { params: { activo: 1 } })
  const [camion, setCamion] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  const enviar = async (e) => {
    e.preventDefault()
    setEnviando(true)
    try {
      await api(`/pedidos/${pedido.id_pedido}`, { method: 'PATCH', body: { estado: 'Despachado', camion_id: camion } })
      onListo(`Pedido N.º ${pedido.id_pedido} despachado en el camión ${camion}.`)
    } catch (err) {
      setError(err.message)
      setEnviando(false)
    }
  }

  return (
    <Modal titulo={`Despachar pedido N.º ${pedido.id_pedido}`} onCerrar={onCerrar}>
      <form onSubmit={enviar} className="space-y-4">
        <p className="text-pizarra">
          {pedido.cliente.nombre_razon_social}, entrega en {pedido.direccion_entrega}.
        </p>
        <Aviso>{error || errorCamiones}</Aviso>
        <Campo etiqueta="Camión" ayuda="Desde que sale de bodega, sus lecturas de temperatura quedan asociadas a este pedido.">
          <select className="campo" required value={camion} onChange={(e) => setCamion(e.target.value)}>
            <option value="">Elige un camión</option>
            {camiones?.map((c) => (
              <option key={c.camion_id} value={c.camion_id}>
                {c.camion_id}, patente {c.patente}, {c.capacidad_kg.toLocaleString('es-CL')} kg
                {c.despachos_activos > 0 ? ` (${c.despachos_activos} en ruta)` : ''}
              </option>
            ))}
          </select>
        </Campo>
        <button type="submit" className="boton boton-primario w-full" disabled={enviando || !camion}>
          {enviando ? 'Despachando…' : 'Despachar pedido'}
        </button>
      </form>
    </Modal>
  )
}

export default function Pedidos() {
  const { usuario } = useSesion()
  const puedeGestionar = ['administrador', 'despachador'].includes(usuario.rol)
  const { datos: pedidos, error, recargar } = useDatos('/pedidos', { cadaMs: 15000 })
  const [estado, setEstado] = useState('Recibido')
  const [abierto, setAbierto] = useState(null)
  const [despachando, setDespachando] = useState(null)
  const [aviso, setAviso] = useState(null)

  const conteo = useMemo(() => {
    const c = Object.fromEntries(ESTADOS.map((e) => [e, 0]))
    for (const p of pedidos || []) c[p.estado] += 1
    return c
  }, [pedidos])
  const visibles = (pedidos || []).filter((p) => p.estado === estado)

  const cambiar = async (pedido, nuevo) => {
    if (nuevo === 'Rechazado' && !window.confirm(`¿Rechazar el pedido N.º ${pedido.id_pedido}? No se puede deshacer.`)) return
    try {
      await api(`/pedidos/${pedido.id_pedido}`, { method: 'PATCH', body: { estado: nuevo } })
      setAviso({ tipo: 'ok', texto: `Pedido N.º ${pedido.id_pedido}: ${nuevo.toLowerCase()}.` })
      recargar()
    } catch (e) {
      setAviso({ tipo: 'error', texto: e.message })
    }
  }

  const acciones = (p) => {
    if (!puedeGestionar) return null
    const rechazar = (
      <button type="button" className="boton boton-peligro boton-chico" onClick={() => cambiar(p, 'Rechazado')}>
        Rechazar
      </button>
    )
    if (p.estado === 'Recibido')
      return (
        <>
          <button type="button" className="boton boton-primario boton-chico" onClick={() => cambiar(p, 'En preparación')}>
            Pasar a preparación
          </button>
          {rechazar}
        </>
      )
    if (p.estado === 'En preparación')
      return (
        <>
          <button type="button" className="boton boton-primario boton-chico" onClick={() => setDespachando(p)}>
            Despachar
          </button>
          {rechazar}
        </>
      )
    if (p.estado === 'Despachado')
      return (
        <>
          <button type="button" className="boton boton-primario boton-chico" onClick={() => cambiar(p, 'Entregado')}>
            Marcar entregado
          </button>
          {rechazar}
        </>
      )
    return null
  }

  return (
    <>
      <Encabezado
        titulo="Pedidos"
        detalle={puedeGestionar ? 'Prepara, despacha y cierra los pedidos.' : 'Seguimiento de los pedidos de tus clientes.'}
      />
      <div className="mb-4 space-y-3">
        <Aviso>{error}</Aviso>
        {aviso && (
          <Aviso tipo={aviso.tipo} onCerrar={() => setAviso(null)}>
            {aviso.texto}
          </Aviso>
        )}
      </div>

      <div className="flex gap-1 overflow-x-auto overflow-y-hidden border-b border-hielo" role="tablist" aria-label="Estado del pedido">
        {ESTADOS.map((e) => (
          <button
            key={e}
            type="button"
            role="tab"
            aria-selected={estado === e}
            onClick={() => setEstado(e)}
            className={`-mb-px border-b-[3px] px-3 py-2 font-semibold whitespace-nowrap ${
              estado === e ? 'border-camara text-camara' : 'border-transparent text-pizarra hover:text-camara'
            }`}
          >
            {e} <span className="cifra ml-1 text-pizarra">{conteo[e]}</span>
          </button>
        ))}
      </div>

      {!pedidos && !error ? (
        <Cargando />
      ) : visibles.length === 0 ? (
        <p className="py-10 text-pizarra">No hay pedidos en «{estado}».</p>
      ) : (
        <div className="caja mt-4 overflow-x-auto">
          <table className="w-full min-w-[46rem] text-left">
            <thead className="text-sm text-pizarra">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Pedido</th>
                <th className="px-4 py-2.5 font-semibold">Cliente</th>
                <th className="px-4 py-2.5 font-semibold">Canal</th>
                <th className="px-4 py-2.5 font-semibold">Entrega</th>
                <th className="px-4 py-2.5 text-right font-semibold">Total</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {visibles.map((p) => (
                <Fragment key={p.id_pedido}>
                  <tr className="border-t border-hielo align-top">
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        className="cifra text-xl font-semibold underline decoration-hielo underline-offset-4 hover:decoration-camara"
                        aria-expanded={abierto === p.id_pedido}
                        onClick={() => setAbierto(abierto === p.id_pedido ? null : p.id_pedido)}
                      >
                        N.º {p.id_pedido}
                      </button>
                      <p className="text-sm text-pizarra">{fechaHora(p.fecha_creacion)}</p>
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-semibold">{p.cliente.nombre_razon_social}</p>
                      <p className="text-sm text-pizarra">
                        {p.cliente.tipo === 'B2B' ? 'Institucional' : 'Persona'}
                        {p.numero_oc && `, OC ${p.numero_oc}`}
                      </p>
                    </td>
                    <td className="px-4 py-3">{p.canal === 'web' ? 'Tienda web' : 'Vendedor'}</td>
                    <td className="px-4 py-3">
                      <p>{fecha(p.fecha_entrega_solicitada)}</p>
                      {p.despacho && <p className="text-sm text-pizarra">Camión {p.despacho.camion_id}</p>}
                    </td>
                    <td className="cifra px-4 py-3 text-right text-xl font-semibold">{pesos(p.total)}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap justify-end gap-2">{acciones(p)}</div>
                    </td>
                  </tr>
                  {abierto === p.id_pedido && (
                    <tr className="bg-escarcha/60">
                      <td colSpan={6} className="px-4 py-3">
                        <p className="mb-2 text-sm">
                          <Estado nombre={p.estado} /> <span className="ml-2">Entrega en {p.direccion_entrega}.</span>
                          {p.despacho && (
                            <span>
                              {' '}
                              Salió de bodega el {fechaHora(p.despacho.fecha_salida)}
                              {p.despacho.fecha_entrega && `, entregado el ${fechaHora(p.despacho.fecha_entrega)}`}.
                            </span>
                          )}
                        </p>
                        <DetallePedido pedido={p} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {despachando && (
        <Despachar
          pedido={despachando}
          onCerrar={() => setDespachando(null)}
          onListo={(texto) => {
            setDespachando(null)
            setAviso({ tipo: 'ok', texto })
            recargar()
          }}
        />
      )}
    </>
  )
}
