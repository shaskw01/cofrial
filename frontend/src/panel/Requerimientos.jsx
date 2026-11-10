import { useState } from 'react'
import { Aviso, Cargando } from '../componentes/Basicos'
import { fechaHora } from '../formato'
import { Encabezado, useDatos } from './Panel'

export const NOMBRE_CATEGORIA = {
  reclamo_temperatura: 'Reclamo por temperatura',
  reclamo_entrega: 'Reclamo por entrega',
  consulta_pedido: 'Consulta por un pedido',
  cotizacion: 'Solicitud de cotización',
  otro: 'Otro tema',
  sin_clasificar: 'Sin clasificar',
}

const ESTILO_PRIORIDAD = {
  alta: 'bg-ruptura text-white',
  media: 'bg-ambar-suave text-ambar',
  baja: 'bg-glaciar-suave text-glaciar',
}

export function Prioridad({ valor }) {
  return (
    <span
      className={`inline-block rounded-sm px-2 py-0.5 text-sm font-semibold whitespace-nowrap ${
        ESTILO_PRIORIDAD[valor] || 'bg-escarcha text-pizarra'
      }`}
    >
      {valor ? `Prioridad ${valor}` : 'Sin prioridad'}
    </span>
  )
}

/** Separa el texto guardado en interacciones.detalle en mensaje, resumen y respuesta sugerida. */
function partes(detalle) {
  const [cabeza, resto = ''] = detalle.split('\n---\n')
  const linea = (prefijo) =>
    resto
      .split('\n')
      .find((l) => l.startsWith(prefijo))
      ?.slice(prefijo.length)
  return {
    mensaje: cabeza.replace('Mensaje web del cliente: ', ''),
    resumen: linea('Resumen: '),
    respuesta: linea('Respuesta sugerida: '),
  }
}

const FILTROS = [
  ['', 'Todos'],
  ['alta', 'Prioridad alta'],
  ['sin', 'Sin clasificar'],
]

export default function Requerimientos() {
  const { datos, error } = useDatos('/interacciones', { params: { web: 1 }, cadaMs: 10000 })
  const [filtro, setFiltro] = useState('')

  const visibles = (datos || []).filter((i) => {
    if (filtro === 'alta') return i.clasificacion?.prioridad === 'alta'
    if (filtro === 'sin') return i.clasificacion?.categoria === 'sin_clasificar'
    return true
  })

  return (
    <>
      <Encabezado
        titulo="Requerimientos de clientes"
        detalle="Mensajes del formulario de ayuda de la tienda, clasificados por la IA al llegar."
      >
        <div className="inline-flex rounded border border-hielo bg-white p-0.5" role="group" aria-label="Filtrar requerimientos">
          {FILTROS.map(([valor, nombre]) => (
            <button
              key={valor}
              type="button"
              aria-pressed={filtro === valor}
              onClick={() => setFiltro(valor)}
              className={`rounded-[3px] px-3 py-1.5 text-sm font-semibold ${
                filtro === valor ? 'bg-camara text-white' : 'text-pizarra hover:text-camara'
              }`}
            >
              {nombre}
            </button>
          ))}
        </div>
      </Encabezado>

      <Aviso>{error}</Aviso>
      {!datos && !error && <Cargando />}
      {datos && visibles.length === 0 && (
        <p className="py-10 text-pizarra">
          {datos.length === 0
            ? 'Todavía no llegan mensajes. Aparecerán aquí cuando un cliente escriba desde «Ayuda» en la tienda.'
            : 'Ningún requerimiento coincide con el filtro.'}
        </p>
      )}

      <ul className="space-y-3">
        {visibles.map((i) => {
          const p = partes(i.detalle)
          const c = i.clasificacion || {}
          return (
            <li
              key={i.id_interaccion}
              className={`caja border-l-4 p-4 ${c.prioridad === 'alta' ? 'border-l-ruptura' : 'border-l-hielo'}`}
            >
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <Prioridad valor={c.prioridad} />
                <h2 className="text-xl">{NOMBRE_CATEGORIA[c.categoria] || c.categoria}</h2>
                <span className="ml-auto text-sm text-pizarra">
                  {i.cliente_nombre}, {fechaHora(i.fecha)}
                </span>
              </div>
              <blockquote className="mt-2 border-l-2 border-hielo pl-3 whitespace-pre-line">{p.mensaje}</blockquote>
              {p.resumen && (
                <p className="mt-2 text-sm">
                  <span className="font-semibold">Resumen de la IA:</span> {p.resumen}
                </p>
              )}
              {p.respuesta && (
                <p className="mt-1 text-sm">
                  <span className="font-semibold">Respuesta sugerida:</span> {p.respuesta}
                </p>
              )}
              {c.categoria === 'sin_clasificar' && (
                <p className="mt-2 text-sm text-pizarra">
                  La IA no estaba disponible cuando llegó este mensaje. Revísalo y clasifícalo a mano.
                </p>
              )}
            </li>
          )
        })}
      </ul>
    </>
  )
}
